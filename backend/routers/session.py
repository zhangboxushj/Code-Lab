from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.session_manager import (
    create_session, delete_session, get_session,
    list_sessions, set_session_name,
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
