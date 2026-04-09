from functools import lru_cache

from elasticsearch import AsyncElasticsearch
from openai import AsyncOpenAI

from backend.core.config import settings


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


async def embed(text: str) -> list[float]:
    client = _get_embed_client()
    resp = await client.embeddings.create(
        model=settings.dashscope_embedding_model,
        input=text,
    )
    return resp.data[0].embedding


async def hybrid_search(query: str, top_k: int = 5) -> list[str]:
    """
    Returns text snippets with hybrid score >= es_score_threshold.
    Returns [] if ES unavailable or nothing passes threshold (triggers DeepSeek direct fallback).
    """
    try:
        vector = await embed(query)
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

        resp = await es.search(index=settings.es_index, body=body)
        hits = resp["hits"]["hits"]
        return [
            h["_source"]["text"]
            for h in hits
            if h["_score"] >= settings.es_score_threshold
        ]
    except Exception:
        # ES unavailable or embedding failed — fall back to DeepSeek direct answer
        return []
