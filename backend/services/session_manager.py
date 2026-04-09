"""
Session manager — Redis 持久化
Key 设计：
  session:list                  → Set，存所有 session_id
  session:{id}:meta             → Hash，存 name / created_at
  session:{id}:context          → List，最近 3 轮对话（6条），TTL 2h
  session:{id}:questions        → List，全量问题文本，TTL 7d
"""
import json
import uuid
from datetime import datetime

import redis.asyncio as aioredis

from backend.core.config import settings

# ---------------------------------------------------------------------------
# Connection pool (module-level singleton)
# ---------------------------------------------------------------------------

_pool: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _pool


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------

def _meta_key(sid: str) -> str:
    return f"session:{sid}:meta"

def _context_key(sid: str) -> str:
    return f"session:{sid}:context"

def _questions_key(sid: str) -> str:
    return f"session:{sid}:questions"

SESSION_LIST_KEY = "session:list"
MAX_CONTEXT_MESSAGES = 6   # 3 轮 × 2 条


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def create_session() -> str:
    r = get_redis()
    sid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    async with r.pipeline() as pipe:
        pipe.hset(_meta_key(sid), mapping={"name": "", "created_at": now})
        pipe.expire(_meta_key(sid), settings.redis_questions_ttl)
        pipe.sadd(SESSION_LIST_KEY, sid)
        await pipe.execute()
    return sid


async def get_session(session_id: str) -> dict | None:
    r = get_redis()
    meta = await r.hgetall(_meta_key(session_id))
    if not meta:
        return None
    raw = await r.lrange(_context_key(session_id), 0, -1)
    history = [json.loads(m) for m in raw]
    return {"name": meta.get("name", ""), "history": history}


async def set_session_name(session_id: str, name: str) -> bool:
    r = get_redis()
    if not await r.exists(_meta_key(session_id)):
        return False
    await r.hset(_meta_key(session_id), "name", name)
    return True


async def update_context(session_id: str, role: str, content: str) -> None:
    """Append message to sliding context window (max 3 rounds = 6 messages)."""
    r = get_redis()
    msg = json.dumps({"role": role, "content": content[:500]}, ensure_ascii=False)
    async with r.pipeline() as pipe:
        pipe.rpush(_context_key(session_id), msg)
        pipe.ltrim(_context_key(session_id), -MAX_CONTEXT_MESSAGES, -1)
        pipe.expire(_context_key(session_id), settings.redis_context_ttl)
        await pipe.execute()


async def append_question(session_id: str, question: str) -> None:
    """Append question to the full question list (TTL 7d)."""
    r = get_redis()
    async with r.pipeline() as pipe:
        pipe.rpush(_questions_key(session_id), question)
        pipe.expire(_questions_key(session_id), settings.redis_questions_ttl)
        await pipe.execute()


async def get_questions(session_id: str) -> list[str]:
    """Return all questions for this session."""
    r = get_redis()
    return await r.lrange(_questions_key(session_id), 0, -1)


async def delete_session(session_id: str) -> bool:
    r = get_redis()
    if not await r.exists(_meta_key(session_id)):
        return False
    async with r.pipeline() as pipe:
        pipe.delete(_meta_key(session_id))
        pipe.delete(_context_key(session_id))
        pipe.delete(_questions_key(session_id))
        pipe.srem(SESSION_LIST_KEY, session_id)
        await pipe.execute()
    return True


async def list_sessions() -> list[dict]:
    r = get_redis()
    sids = await r.smembers(SESSION_LIST_KEY)
    if not sids:
        return []

    sessions = []
    for sid in sids:
        meta = await r.hgetall(_meta_key(sid))
        if meta:
            sessions.append({
                "session_id": sid,
                "name": meta.get("name", ""),
                "created_at": meta.get("created_at", ""),
            })

    # Sort by created_at descending
    sessions.sort(key=lambda s: s["created_at"], reverse=True)
    return sessions
