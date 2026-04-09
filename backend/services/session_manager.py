"""
Session manager — SQLite3 持久化（aiosqlite 全异步）
数据库文件: backend/data/sessions.db
表结构:
  sessions(session_id, name, created_at)
  messages(id, session_id, role, content, created_at)
"""
import json
import os
import uuid
from typing import Any

import aiosqlite

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sessions.db")


def _db() -> aiosqlite.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return aiosqlite.connect(DB_PATH)


async def init_db() -> None:
    """建表，启动时调用一次"""
    async with _db() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                name       TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            )
        """)
        await db.commit()


async def create_session() -> str:
    session_id = str(uuid.uuid4())
    async with _db() as db:
        await db.execute(
            "INSERT INTO sessions (session_id, name) VALUES (?, ?)",
            (session_id, ""),
        )
        await db.commit()
    return session_id


async def get_session(session_id: str) -> dict[str, Any] | None:
    async with _db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT session_id, name FROM sessions WHERE session_id = ?",
            (session_id,),
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None

        async with db.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ) as cur:
            msgs = await cur.fetchall()

    return {
        "name": row["name"],
        "history": [{"role": m["role"], "content": m["content"]} for m in msgs],
    }


async def set_session_name(session_id: str, name: str) -> bool:
    async with _db() as db:
        cur = await db.execute(
            "UPDATE sessions SET name = ? WHERE session_id = ?",
            (name, session_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def update_session(session_id: str, role: str, content: str, max_turns: int = 20) -> None:
    async with _db() as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        await db.commit()

        async with db.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE session_id = ?",
            (session_id,),
        ) as cur:
            row = await cur.fetchone()
            count = row["cnt"]

        if count > max_turns * 2:
            excess = count - max_turns * 2
            await db.execute("""
                DELETE FROM messages WHERE id IN (
                    SELECT id FROM messages WHERE session_id = ?
                    ORDER BY id ASC LIMIT ?
                )
            """, (session_id, excess))
            await db.commit()


async def delete_session(session_id: str) -> bool:
    async with _db() as db:
        await db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cur = await db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        await db.commit()
        return cur.rowcount > 0


async def list_sessions() -> list[dict[str, str]]:
    async with _db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT session_id, name FROM sessions ORDER BY created_at DESC"
        ) as cur:
            rows = await cur.fetchall()
    return [{"session_id": r["session_id"], "name": r["name"]} for r in rows]
