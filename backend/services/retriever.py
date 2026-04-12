"""
Retriever — hybrid search (BM25 + vector) over Elasticsearch.

Embedding backend (priority order):
  1. Local bge-m3 via FlagEmbedding (GPU if available, else CPU)
  2. DashScope API fallback (if local model fails to load)

On first run the local model is downloaded automatically from HuggingFace
(~2.2 GB). Subsequent starts load from the local cache instantly.
"""
import asyncio
import logging
import time
from functools import lru_cache

from elasticsearch import AsyncElasticsearch
from openai import AsyncOpenAI

from backend.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-process embedding cache (avoids re-embedding identical queries)
# ---------------------------------------------------------------------------
_EMBED_CACHE: dict[str, list[float]] = {}
_EMBED_CACHE_MAX = 256

# ---------------------------------------------------------------------------
# Local bge-m3 model (lazy-loaded on first embed call)
# ---------------------------------------------------------------------------
_local_model = None          # BGEM3FlagModel instance, None until loaded
_local_model_failed = False  # True if load failed; fall back to API


def _load_local_model():
    """
    Load bge-m3 into memory. Called once from an executor thread so it does
    not block the event loop. Automatically selects CUDA if available.
    """
    global _local_model, _local_model_failed
    try:
        import torch
        from sentence_transformers import SentenceTransformer

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("[Embedding] loading BAAI/bge-m3 on %s (first run downloads ~2.2 GB)", device)
        _local_model = SentenceTransformer("BAAI/bge-m3", device=device, local_files_only=True)
        logger.info("[Embedding] bge-m3 ready on %s", device)
    except Exception as e:
        _local_model_failed = True
        logger.warning("[Embedding] local model load failed, falling back to DashScope API: %s", e)


def _encode_local(text: str) -> list[float]:
    """Run bge-m3 inference synchronously (called inside executor thread)."""
    return _local_model.encode(text, normalize_embeddings=True).tolist()


# ---------------------------------------------------------------------------
# ES + DashScope API clients
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_es() -> AsyncElasticsearch:
    kwargs: dict = {"hosts": [settings.es_url]}
    if settings.es_username:
        kwargs["basic_auth"] = (settings.es_username, settings.es_password)
    return AsyncElasticsearch(**kwargs)


@lru_cache(maxsize=1)
def _get_embed_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_base_url,
    )


# ---------------------------------------------------------------------------
# Public embed function
# ---------------------------------------------------------------------------

async def embed(text: str) -> tuple[list[float], int]:
    """
    Return (vector, cost_ms).
    cost_ms is 0 on cache hit.
    Uses local bge-m3 when available, falls back to DashScope API.
    """
    global _local_model, _local_model_failed

    if text in _EMBED_CACHE:
        return _EMBED_CACHE[text], 0

    t0 = time.perf_counter()

    # ── Local model path ────────────────────────────────────────────────────
    if not _local_model_failed:
        # Load model on first call (runs in thread to avoid blocking event loop)
        if _local_model is None:
            await asyncio.get_running_loop().run_in_executor(None, _load_local_model)

        if _local_model is not None:
            vector = await asyncio.get_running_loop().run_in_executor(
                None, _encode_local, text
            )
            cost_ms = int((time.perf_counter() - t0) * 1000)
            _cache_vector(text, vector)
            return vector, cost_ms

    # ── DashScope API fallback ───────────────────────────────────────────────
    client = _get_embed_client()
    resp = await client.embeddings.create(
        model=settings.dashscope_embedding_model,
        input=text,
    )
    cost_ms = int((time.perf_counter() - t0) * 1000)
    vector = resp.data[0].embedding
    _cache_vector(text, vector)
    return vector, cost_ms


def _cache_vector(text: str, vector: list[float]) -> None:
    if len(_EMBED_CACHE) >= _EMBED_CACHE_MAX:
        _EMBED_CACHE.pop(next(iter(_EMBED_CACHE)))
    _EMBED_CACHE[text] = vector


# ---------------------------------------------------------------------------
# Hybrid search
# ---------------------------------------------------------------------------

async def hybrid_search(query: str, top_k: int = 5) -> tuple[list[str], dict]:
    """
    Returns (text_snippets, timing_dict).

    timing_dict keys:
        embedding_cost_ms   — vector generation time (0 if cache hit)
        es_search_cost_ms   — ES round-trip time
        candidate_count     — raw hits from ES before threshold filter
        returned_count      — hits that passed score threshold
        es_available        — False if ES is down / embedding failed
        cache_hit           — True if embedding was served from cache
    """
    RESULT_TOP_K = 3
    MAX_CONTEXT_CHARS = 8000

    timing: dict = {
        "embedding_cost_ms": 0,
        "es_search_cost_ms": 0,
        "candidate_count": 0,
        "returned_count": 0,
        "es_available": True,
        "cache_hit": False,
    }
    try:
        timing["cache_hit"] = query in _EMBED_CACHE
        vector, embed_ms = await embed(query)
        timing["embedding_cost_ms"] = embed_ms

        es = _get_es()
        body = {
            "size": top_k,
            "query": {
                "bool": {
                    "should": [
                        {"match": {"text": query}},
                    ]
                }
            },
            "knn": {
                "field": "embedding",
                "query_vector": vector,
                "k": top_k,
                "num_candidates": top_k * 10,
            },
            "_source": ["text"],
        }

        t_es = time.perf_counter()
        resp = await es.search(index=settings.es_index, body=body)
        timing["es_search_cost_ms"] = int((time.perf_counter() - t_es) * 1000)

        hits = resp["hits"]["hits"]
        timing["candidate_count"] = len(hits)

        # Filter by score threshold, take top RESULT_TOP_K, cap total chars
        passed = [
            h["_source"]["text"]
            for h in hits
            if h["_score"] is not None and h["_score"] >= settings.es_score_threshold
        ][:RESULT_TOP_K]

        results: list[str] = []
        total_chars = 0
        for doc in passed:
            if total_chars + len(doc) > MAX_CONTEXT_CHARS:
                break
            results.append(doc)
            total_chars += len(doc)

        timing["returned_count"] = len(results)
        return results, timing

    except Exception:
        timing["es_available"] = False
        return [], timing
