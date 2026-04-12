"""
Knowledge base router — file upload, listing, deletion.

Chunking strategy (three-level, for Markdown):
  1. Split by Markdown headers (# / ## / ### / ####)
  2. Protect atomic units: fenced code blocks, tables, Q&A pairs, lists
  3. Recursively split oversized text blocks by paragraph → sentence → char
"""
import asyncio
import logging
import os
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from backend.services.retriever import _get_es, _get_embed_client, embed as retriever_embed
from backend.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/kb", tags=["kb"])

KB_DIR = Path(__file__).parent.parent / "knowledge_base"

# ---------------------------------------------------------------------------
# Chunking constants
# ---------------------------------------------------------------------------

CHUNK_TARGET = 700          # target chars per chunk
CHUNK_OVERLAP = 100         # overlap chars between consecutive chunks
MAX_EMBED_CHARS = 1800      # DashScope embedding token limit (~2048 tokens)
EMBED_BATCH_SIZE = 10       # docs per embedding API call

# Regex patterns
_HEADER_RE = re.compile(r"^(#{1,4})\s+(.+)", re.MULTILINE)
_CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```")
_TABLE_ROW_RE = re.compile(r"^\|.+\|", re.MULTILINE)
_QA_RE = re.compile(r"(^|\n)\s*(Q[:：]|问[:：]|A[:：]|答[:：])")
_LIST_RE = re.compile(r"(^|\n)\s*(第[一二三四五六七八九十]|[①②③④⑤]|\d+\.|[-*])\s")
_SENTENCE_ENDS = re.compile(r"[。！？.!?；;]+")


# ---------------------------------------------------------------------------
# Content-type detection
# ---------------------------------------------------------------------------

def _detect_content_type(text: str) -> str:
    if _CODE_BLOCK_RE.search(text):
        return "code"
    if _QA_RE.search(text):
        return "qa"
    if _TABLE_ROW_RE.search(text):
        return "table"
    if _LIST_RE.search(text):
        return "list"
    if re.search(r"(区别|对比|优缺点|vs\b|VS\b)", text):
        return "comparison"
    return "text"


# ---------------------------------------------------------------------------
# Overlap helper
# ---------------------------------------------------------------------------

def _tail_overlap(text: str, n: int = CHUNK_OVERLAP) -> str:
    """Return the last `n` chars of `text`, trimmed to a sentence boundary."""
    if len(text) <= n:
        return text
    tail = text[-n:]
    # try to start from a sentence end so overlap begins at a clean boundary
    match = _SENTENCE_ENDS.search(tail)
    return tail[match.end():] if match else tail


# ---------------------------------------------------------------------------
# Recursive text splitter (no external deps)
# ---------------------------------------------------------------------------

def _split_text(text: str, title: str) -> list[str]:
    """
    Split `text` into chunks ≤ CHUNK_TARGET chars.
    Priority: paragraph → sentence → hard char cut.
    Each chunk is prefixed with the section title for retrieval context.
    Consecutive chunks share an overlap tail from the previous chunk.
    """
    prefix = f"【{title}】" if title else ""

    # Separate code blocks from prose so they are never split internally
    segments: list[tuple[str, bool]] = []   # (text, is_code)
    last = 0
    for m in _CODE_BLOCK_RE.finditer(text):
        if m.start() > last:
            segments.append((text[last:m.start()], False))
        segments.append((m.group(), True))
        last = m.end()
    if last < len(text):
        segments.append((text[last:], False))

    chunks: list[str] = []
    carry = ""   # overlap tail from previous chunk

    for seg, is_code in segments:
        seg = seg.strip()
        if not seg:
            continue

        if is_code:
            # Code block: emit as-is (possibly oversized, but never split)
            content = f"{prefix}\n{carry}\n{seg}".strip() if carry else f"{prefix}\n{seg}".strip()
            chunks.append(content)
            carry = _tail_overlap(seg)
            continue

        # Split prose by paragraphs first
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", seg) if p.strip()]
        current = carry

        for para in paragraphs:
            if len(current) + len(para) + 1 <= CHUNK_TARGET:
                current = (current + "\n" + para).strip()
            else:
                # Flush current chunk
                if current:
                    chunks.append(f"{prefix}\n{current}".strip())
                    carry = _tail_overlap(current)

                if len(para) <= CHUNK_TARGET:
                    current = (carry + "\n" + para).strip()
                else:
                    # Para itself is too long — split by sentence
                    sentences = _SENTENCE_ENDS.split(para)
                    current = carry
                    for sent in sentences:
                        sent = sent.strip()
                        if not sent:
                            continue
                        if len(current) + len(sent) + 1 <= CHUNK_TARGET:
                            current = (current + sent).strip()
                        else:
                            if current:
                                chunks.append(f"{prefix}\n{current}".strip())
                                carry = _tail_overlap(current)
                            # Hard cut if single sentence exceeds target
                            if len(sent) > CHUNK_TARGET:
                                for i in range(0, len(sent), CHUNK_TARGET - CHUNK_OVERLAP):
                                    chunks.append(f"{prefix}\n{sent[i:i + CHUNK_TARGET]}".strip())
                                carry = _tail_overlap(sent)
                                current = carry
                            else:
                                current = (carry + sent).strip()

        if current and current != carry:
            chunks.append(f"{prefix}\n{current}".strip())
            carry = _tail_overlap(current)

    return [c for c in chunks if len(c.strip()) > 20]


# ---------------------------------------------------------------------------
# Header-aware Markdown splitter
# ---------------------------------------------------------------------------

def _chunk_markdown(text: str) -> list[dict]:
    """
    Split Markdown into chunks using header boundaries as primary split points.
    Returns list of {"title": str, "content": str}.
    """
    # Find all header positions
    headers = list(_HEADER_RE.finditer(text))
    if not headers:
        return _chunk_plain(text)

    sections: list[tuple[str, str]] = []   # (title, body)
    for i, h in enumerate(headers):
        title = h.group(2).strip()
        body_start = h.end()
        body_end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        body = text[body_start:body_end].strip()
        sections.append((title, body))

    chunks: list[dict] = []
    for title, body in sections:
        if not body:
            continue
        content_type = _detect_content_type(body)

        # Q&A, table, list: try to keep whole if within 2× target
        if content_type in ("qa", "table", "list") and len(body) <= CHUNK_TARGET * 2:
            chunks.append({"title": title, "content": f"【{title}】\n{body}"})
            continue

        # Split into sub-chunks
        for sub in _split_text(body, title):
            chunks.append({"title": title, "content": sub})

    return chunks or _chunk_plain(text)


# ---------------------------------------------------------------------------
# Plain text fallback (for .txt files)
# ---------------------------------------------------------------------------

def _chunk_plain(text: str) -> list[dict]:
    """Fixed-size chunking with overlap for non-Markdown files."""
    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = min(start + CHUNK_TARGET, len(text))
        content = text[start:end].strip()
        if len(content) > 20:
            chunks.append({"title": f"片段{idx + 1}", "content": content})
            idx += 1
        start += CHUNK_TARGET - CHUNK_OVERLAP
    return chunks


# ---------------------------------------------------------------------------
# Async embed + index
# ---------------------------------------------------------------------------

async def _embed_and_index(chunks: list[dict], filename: str) -> int:
    """Embed chunks in batches and bulk-index into ES. Returns total indexed."""
    import backend.services.retriever as retriever_mod

    es = _get_es()
    total = 0

    # Ensure local model is loaded before batch processing
    if not retriever_mod._local_model_failed and retriever_mod._local_model is None:
        await asyncio.get_running_loop().run_in_executor(None, retriever_mod._load_local_model)

    def _encode_batch(texts: list[str]) -> list[list[float]]:
        return retriever_mod._local_model.encode(texts, normalize_embeddings=True).tolist()

    for i in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[i:i + EMBED_BATCH_SIZE]
        texts = [c["content"][:MAX_EMBED_CHARS] for c in batch]

        # Use local model if available, else fall back to DashScope API
        if not retriever_mod._local_model_failed and retriever_mod._local_model is not None:
            vectors = await asyncio.get_running_loop().run_in_executor(None, _encode_batch, texts)
        else:
            embed_client = _get_embed_client()
            resp = await embed_client.embeddings.create(
                model=settings.dashscope_embedding_model,
                input=texts,
            )
            vectors = [item.embedding for item in resp.data]

        ops: list[dict] = []
        for chunk, vector in zip(batch, vectors):
            doc_id = str(uuid.uuid4())
            ops.append({"index": {"_index": settings.es_index, "_id": doc_id}})
            ops.append({
                "id": doc_id,
                "title": chunk["title"],
                "text": chunk["content"],
                "embedding": vector,
                "source": "kb",
                "metadata": {"filename": filename},
            })

        await es.bulk(operations=ops, refresh=True)
        total += len(batch)

    return total


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_kb_file(file: UploadFile = File(...)):
    """Upload a .md or .txt file to the knowledge base."""
    if not file.filename.endswith((".md", ".txt")):
        raise HTTPException(status_code=400, detail="只支持 .md 和 .txt 文件")

    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("gbk", errors="ignore")

    chunks = _chunk_markdown(text) if file.filename.endswith(".md") else _chunk_plain(text)
    if not chunks:
        raise HTTPException(status_code=400, detail="文件内容为空或无法解析")

    # Persist file
    KB_DIR.mkdir(parents=True, exist_ok=True)
    (KB_DIR / file.filename).write_text(text, encoding="utf-8")

    total = await _embed_and_index(chunks, file.filename)
    return JSONResponse({"filename": file.filename, "chunks": total, "status": "ok"})


@router.get("/list")
async def list_kb_files():
    """List files currently in the knowledge base directory."""
    KB_DIR.mkdir(parents=True, exist_ok=True)
    files = [f.name for f in KB_DIR.iterdir() if f.suffix in (".md", ".txt")]
    return {"files": files}


@router.delete("/file/{filename}")
async def delete_kb_file(filename: str):
    """Delete a file from the knowledge base and remove its ES documents."""
    es = _get_es()
    await es.delete_by_query(
        index=settings.es_index,
        body={"query": {"term": {"metadata.filename": filename}}},
        refresh=True,
    )
    path = KB_DIR / filename
    if path.exists():
        path.unlink()
    return {"deleted": filename}
