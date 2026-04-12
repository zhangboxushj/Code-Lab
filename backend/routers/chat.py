import json
import logging
import re
import time
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.services.llm_client import LLMClient
from backend.services.retriever import hybrid_search
from backend.services.session_manager import (
    append_question, get_session, update_context,
)

router = APIRouter()
_llm = LLMClient()
logger = logging.getLogger(__name__)

_PRONOUN_RE = re.compile(
    r"它|这个|那个|这种|那种|这块|这里|这方面|这部分"
    r"|你刚才|刚才|刚说的|你说的|你提到的|你讲的"
    r"|上面|前面|之前|该|此"
    r"|其中|其他|另外那个|那种情况"
    r"|怎么理解|能展开|能细说"
)


def _needs_rewrite(text: str) -> bool:
    return bool(_PRONOUN_RE.search(text))


@router.get("/chat/classify")
async def classify_intent(text: str):
    """判断文本是面试问题还是闲聊"""
    is_question = await _llm.is_interview_question(text)
    return {"is_question": is_question}


@router.get("/chat/stream")
async def chat_stream(session_id: str, message: str):
    trace_id = uuid.uuid4().hex[:8]
    t_start = time.perf_counter()

    # ── 1. 会话 + 历史加载 ──────────────────────────────────────────────
    t0 = time.perf_counter()
    session = await get_session(session_id)
    history_load_cost_ms = int((time.perf_counter() - t0) * 1000)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    history = session["history"]
    history_message_count = len(history)
    history_chars = sum(len(m.get("content", "")) for m in history)

    # ── 2. Query rewrite（条件触发）─────────────────────────────────────
    search_query = message
    query_rewrite_cost_ms = 0
    if history and _needs_rewrite(message):
        t0 = time.perf_counter()
        search_query = await _llm.rewrite_query(message, history)
        query_rewrite_cost_ms = int((time.perf_counter() - t0) * 1000)

    # ── 3. 混合检索 ──────────────────────────────────────────────────────
    docs, retrieval_timing = await hybrid_search(search_query)
    source = "kb" if docs else "direct"

    # ── 4. 记录问题（非阻塞）───────────────────────────────────────────
    await append_question(session_id, message)

    # ── 5. LLM 流式生成 ──────────────────────────────────────────────────
    llm_timing: dict = {
        "prompt_build_cost_ms": 0,
        "prompt_chars": 0,
        "context_chars": 0,
        "llm_first_token_cost_ms": 0,
        "llm_generate_cost_ms": 0,
    }

    async def _generate():
        full_response: list[str] = []
        sse_first_sent = False
        t_stream_start = time.perf_counter()

        async for chunk in _llm.stream_answer(
            message, history, docs or None, timing=llm_timing
        ):
            full_response.append(chunk)
            payload = json.dumps({"type": "chunk", "text": chunk})
            if not sse_first_sent:
                sse_first_sent = True
            yield f"data: {payload}\n\n"

        sse_stream_cost_ms = int((time.perf_counter() - t_stream_start) * 1000)

        # ── 6. 收尾落库 ────────────────────────────────────────────────
        t0 = time.perf_counter()
        await update_context(session_id, "user", message)
        await update_context(session_id, "assistant", "".join(full_response))
        response_finalize_cost_ms = int((time.perf_counter() - t0) * 1000)

        total_cost_ms = int((time.perf_counter() - t_start) * 1000)
        elapsed_ms = llm_timing["llm_first_token_cost_ms"] + llm_timing["llm_generate_cost_ms"]

        # 用户感知首字延迟 = 检索前置耗时 + LLM 首 token 耗时
        time_to_first_token_ms = (
            query_rewrite_cost_ms
            + retrieval_timing["embedding_cost_ms"]
            + retrieval_timing["es_search_cost_ms"]
            + llm_timing["llm_first_token_cost_ms"]
        )

        # ── 7. 结构化耗时日志 ──────────────────────────────────────────
        timing_log = {
            "trace_id": trace_id,
            "session_id": session_id,
            "query": message[:120],
            "query_length": len(message),
            "source": source,
            # 输入规模
            "history_message_count": history_message_count,
            "history_chars": history_chars,
            "selected_chunk_count": len(docs),
            "context_chars": llm_timing["context_chars"],
            "prompt_chars": llm_timing["prompt_chars"],
            # 命中状态
            "cache_hit": retrieval_timing["cache_hit"],
            "es_available": retrieval_timing["es_available"],
            "candidate_count": retrieval_timing["candidate_count"],
            "returned_count": retrieval_timing["returned_count"],
            # 分阶段耗时
            "history_load_cost_ms": history_load_cost_ms,
            "query_rewrite_cost_ms": query_rewrite_cost_ms,
            "embedding_cost_ms": retrieval_timing["embedding_cost_ms"],
            "es_search_cost_ms": retrieval_timing["es_search_cost_ms"],
            "prompt_build_cost_ms": llm_timing["prompt_build_cost_ms"],
            "llm_first_token_cost_ms": llm_timing["llm_first_token_cost_ms"],
            "llm_generate_cost_ms": llm_timing["llm_generate_cost_ms"],
            "sse_stream_cost_ms": sse_stream_cost_ms,
            "response_finalize_cost_ms": response_finalize_cost_ms,
            # 汇总
            "time_to_first_token_ms": time_to_first_token_ms,
            "total_cost_ms": total_cost_ms,
        }
        logger.info("TIMING %s", json.dumps(timing_log, ensure_ascii=False))

        yield f"data: {json.dumps({'type': 'done', 'source': source, 'elapsed_ms': elapsed_ms})}\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream")
