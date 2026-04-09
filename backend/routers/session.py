from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from backend.services.session_manager import (
    create_session, delete_session, get_questions,
    get_session, list_sessions, set_session_name,
)

router = APIRouter(prefix="/api/session", tags=["session"])


class NameBody(BaseModel):
    name: str


@router.get("")
async def get_all_sessions():
    return {"sessions": await list_sessions()}


@router.post("")
async def new_session():
    session_id = await create_session()
    return {"session_id": session_id}


@router.patch("/{session_id}/name")
async def rename_session(session_id: str, body: NameBody):
    ok = await set_session_name(session_id, body.name)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "name": body.name}


@router.get("/{session_id}")
async def get_session_history(session_id: str):
    session = await get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "name": session["name"], "history": session["history"]}


@router.delete("/{session_id}")
async def remove_session(session_id: str):
    deleted = await delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": session_id}


@router.get("/{session_id}/export")
async def export_questions(session_id: str):
    """Export all interview questions from this session as a Markdown file."""
    questions = await get_questions(session_id)
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found for this session")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [f"# 面试题汇总\n\n**导出日期：** {today}\n"]
    for i, q in enumerate(questions, 1):
        lines.append(f"\n## Q{i}. {q}\n\n**答案：**\n\n---")

    content = "\n".join(lines)
    filename = f"interview_questions_{today}.md"
    return Response(
        content=content.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
