import os
import uuid
import tempfile

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from backend.services.retriever import embed, _get_es
from backend.core.config import settings

router = APIRouter(prefix="/api/kb", tags=["kb"])

KB_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge_base")
CHUNK_SIZE = 400
MAX_EMBED_CHARS = 1800  # dashscope limit ~2048 tokens, ~1800 chars to be safe


def _chunk_by_header(text: str) -> list[dict]:
    import re
    sections = re.split(r'(?=^####\s)', text, flags=re.MULTILINE)
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        title_match = re.match(r'^####\s+(.+)', section)
        title = title_match.group(1).strip() if title_match else "无标题"
        if len(section) <= CHUNK_SIZE:
            chunks.append({"title": title, "content": section})
        else:
            parts = re.split(r'(```[\s\S]*?```)', section)
            current = ""
            for part in parts:
                if not part.strip():
                    continue
                if len(current) + len(part) <= CHUNK_SIZE:
                    current += "\n" + part
                else:
                    if current.strip():
                        chunks.append({"title": title, "content": f"#### {title}\n{current.strip()}"})
                    current = part
            if current.strip():
                chunks.append({"title": title, "content": f"#### {title}\n{current.strip()}"})
    return chunks


def _chunk_fixed(text: str, size: int = 400) -> list[dict]:
    """Fallback: fixed-size chunking for non-markdown files."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        content = text[start:end].strip()
        if len(content) > 20:
            chunks.append({"title": f"片段{len(chunks)+1}", "content": content})
        start += size - 50
    return chunks


@router.post("/upload")
async def upload_kb_file(file: UploadFile = File(...)):
    """上传 .md 或 .txt 文件到知识库"""
    if not file.filename.endswith((".md", ".txt")):
        raise HTTPException(status_code=400, detail="只支持 .md 和 .txt 文件")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("gbk", errors="ignore")

    # Choose chunking strategy
    if file.filename.endswith(".md"):
        chunks = _chunk_by_header(text)
        if len(chunks) <= 1:
            chunks = _chunk_fixed(text)
    else:
        chunks = _chunk_fixed(text)

    if not chunks:
        raise HTTPException(status_code=400, detail="文件内容为空或无法解析")

    # Save to knowledge_base dir
    os.makedirs(KB_DIR, exist_ok=True)
    save_path = os.path.join(KB_DIR, file.filename)
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(text)

    # Embed and index into ES
    es = _get_es()
    batch_size = 10
    total = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [c["content"][:MAX_EMBED_CHARS] for c in batch]

        # Embed batch
        from openai import AsyncOpenAI
        from backend.services.retriever import _get_embed_client
        embed_client = _get_embed_client()
        resp = await embed_client.embeddings.create(
            model=settings.dashscope_embedding_model,
            input=texts,
        )
        vectors = [item.embedding for item in resp.data]

        ops = []
        for chunk, vector in zip(batch, vectors):
            doc_id = str(uuid.uuid4())
            ops.append({"index": {"_index": settings.es_index, "_id": doc_id}})
            ops.append({
                "id": doc_id,
                "title": chunk["title"],
                "text": chunk["content"],
                "embedding": vector,
                "source": "kb",
                "metadata": {"filename": file.filename},
            })

        await es.bulk(operations=ops, refresh=True)
        total += len(batch)

    return JSONResponse({"filename": file.filename, "chunks": total, "status": "ok"})


@router.get("/list")
async def list_kb_files():
    """列出知识库中的文件"""
    os.makedirs(KB_DIR, exist_ok=True)
    files = [
        f for f in os.listdir(KB_DIR)
        if f.endswith((".md", ".txt"))
    ]
    return {"files": files}


@router.delete("/file/{filename}")
async def delete_kb_file(filename: str):
    """从知识库删除文件（同时删除 ES 中对应的文档）"""
    es = _get_es()

    # Delete from ES by filename metadata
    await es.delete_by_query(
        index=settings.es_index,
        body={"query": {"term": {"metadata.filename": filename}}},
        refresh=True,
    )

    # Delete local file
    file_path = os.path.join(KB_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    return {"deleted": filename}
