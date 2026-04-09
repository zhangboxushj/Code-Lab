import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.services.llm_client import LLMClient
from backend.services.retriever import hybrid_search
from backend.services.session_manager import get_session, update_session

router = APIRouter()
_llm = LLMClient()


@router.get("/chat/classify")
async def classify_intent(text: str):
    """判断文本是面试问题还是闲聊"""
    is_question = await _llm.is_interview_question(text)
    return {"is_question": is_question}


@router.get("/chat/stream")
async def chat_stream(session_id: str, message: str):
    session = await get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    history = session["history"]
    docs = await hybrid_search(message)
    source = "kb" if docs else "direct"

    async def _generate():
        full_response: list[str] = []
        async for chunk in _llm.stream_answer(message, history, docs or None):
            full_response.append(chunk)
            yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"

        await update_session(session_id, "user", message)
        await update_session(session_id, "assistant", "".join(full_response))

        yield f"data: {json.dumps({'type': 'done', 'source': source})}\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream")
