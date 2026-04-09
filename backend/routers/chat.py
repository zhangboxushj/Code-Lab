import json
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.services.llm_client import LLMClient
from backend.services.retriever import hybrid_search
from backend.services.session_manager import (
    append_question, get_session, update_context,
)

router = APIRouter()
_llm = LLMClient()

_PRONOUN_RE = re.compile(r"它|这个|那个|这种|那种|你刚才|上面|前面|之前|该|此")


def _needs_rewrite(text: str) -> bool:
    return bool(_PRONOUN_RE.search(text))


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

    # Conditional query rewriting for follow-up questions
    search_query = message
    if history and _needs_rewrite(message):
        search_query = await _llm.rewrite_query(message, history)

    docs = await hybrid_search(search_query)
    source = "kb" if docs else "direct"

    # Record question immediately (non-blocking concern handled by Redis pipeline)
    await append_question(session_id, message)

    async def _generate():
        full_response: list[str] = []
        async for chunk in _llm.stream_answer(message, history, docs or None):
            full_response.append(chunk)
            yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"

        await update_context(session_id, "user", message)
        await update_context(session_id, "assistant", "".join(full_response))

        yield f"data: {json.dumps({'type': 'done', 'source': source})}\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream")
