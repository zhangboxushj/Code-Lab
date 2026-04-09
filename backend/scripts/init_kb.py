"""
知识库初始化脚本 - 按标题切片策略
用法: python backend/scripts/init_kb.py

切片策略:
- 以 #### 标题为切分单位，每个标题+内容为一个 chunk
- 超过 800 字的 chunk 按代码块边界二次切分
- 保证每个 chunk 语义完整（一个问题=一个或多个 chunk）
"""

import asyncio
import os
import re
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from elasticsearch import AsyncElasticsearch
from openai import AsyncOpenAI

from backend.core.config import settings

KB_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge_base")
MAX_CHUNK_SIZE = 800


def _get_es() -> AsyncElasticsearch:
    kwargs: dict = {"hosts": [settings.es_url]}
    if settings.es_username:
        kwargs["basic_auth"] = (settings.es_username, settings.es_password)
    return AsyncElasticsearch(**kwargs)


def _get_embed_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_base_url,
    )


def chunk_by_header(text: str) -> list[dict]:
    """
    按 #### 标题切分，超长 chunk 按代码块边界二次切分。
    返回 [{"title": str, "content": str}]
    """
    # 按 #### 标题分割
    sections = re.split(r'(?=^####\s)', text, flags=re.MULTILINE)
    chunks = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # 提取标题
        title_match = re.match(r'^####\s+(.+)', section)
        title = title_match.group(1).strip() if title_match else "无标题"

        if len(section) <= MAX_CHUNK_SIZE:
            chunks.append({"title": title, "content": section})
        else:
            # 超长：按 ``` 代码块边界切分
            parts = re.split(r'(```[\s\S]*?```)', section)
            current = ""
            for part in parts:
                if not part.strip():
                    continue
                if len(current) + len(part) <= MAX_CHUNK_SIZE:
                    current += "\n" + part
                else:
                    if current.strip():
                        chunks.append({"title": title, "content": f"#### {title}\n{current.strip()}"})
                    current = part
            if current.strip():
                chunks.append({"title": title, "content": f"#### {title}\n{current.strip()}"})

    return chunks


INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "id":        {"type": "keyword"},
            "title":     {"type": "text"},
            "text":      {"type": "text"},
            "embedding": {"type": "dense_vector", "dims": 1536, "index": True, "similarity": "cosine"},
            "source":    {"type": "keyword"},
            "metadata":  {"type": "object"},
        }
    },
    "settings": {
        "index": {
            "refresh_interval": "1s",
            "number_of_shards": 1,
            "number_of_replicas": 0,
        }
    },
}


async def create_index(es: AsyncElasticsearch) -> None:
    exists = await es.indices.exists(index=settings.es_index)
    if exists:
        print(f"删除旧索引 {settings.es_index}...")
        await es.indices.delete(index=settings.es_index)
    await es.indices.create(
        index=settings.es_index,
        mappings=INDEX_MAPPING["mappings"],
        settings=INDEX_MAPPING["settings"],
    )
    print(f"索引 {settings.es_index} 创建成功")


async def embed_batch(client: AsyncOpenAI, texts: list[str]) -> list[list[float]]:
    # Hard-truncate to 1800 chars to stay within dashscope 2048 token limit
    texts = [t[:1800] for t in texts]
    resp = await client.embeddings.create(
        model=settings.dashscope_embedding_model,
        input=texts,
    )
    return [item.embedding for item in resp.data]


async def ingest_file(
    es: AsyncElasticsearch,
    embed_client: AsyncOpenAI,
    filepath: str,
) -> int:
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    filename = os.path.basename(filepath)
    chunks = chunk_by_header(content)
    print(f"  {filename}: {len(chunks)} 个片段")

    batch_size = 10
    total = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [c["content"] for c in batch]
        vectors = await embed_batch(embed_client, texts)

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
                "metadata": {"filename": filename},
            })

        await es.bulk(operations=ops, refresh=True)
        total += len(batch)
        print(f"    已写入 {total}/{len(chunks)}")

    return total


async def main():
    es = _get_es()
    embed_client = _get_embed_client()

    print("=== 初始化知识库索引（按标题切片策略）===")
    await create_index(es)

    files = [
        os.path.join(KB_DIR, f)
        for f in os.listdir(KB_DIR)
        if f.endswith((".txt", ".md"))
    ]

    if not files:
        print(f"\n{KB_DIR} 目录下没有 .txt 或 .md 文件")
        await es.close()
        return

    print(f"\n找到 {len(files)} 个文件，开始导入...")
    total = 0
    for fp in files:
        total += await ingest_file(es, embed_client, fp)

    print(f"\n✓ 导入完成，共写入 {total} 个片段")
    await es.close()


if __name__ == "__main__":
    asyncio.run(main())
