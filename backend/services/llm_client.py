"""LLM client with DeepSeek as primary and Qwen3 as fallback."""
import json
import logging
import time
from collections.abc import AsyncGenerator

import httpx

from backend.core.config import settings
from backend.services.prompts import (
    CLASSIFY_PROMPT,
    CORRECT_TRANSCRIPT_PROMPT,
    INTENT_PROMPT,
    INTRO_PROMPT,
    RAG_TEMPLATE,
    REWRITE_QUERY_PROMPT,
    SCENE_PROMPT,
    SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self) -> None:
        self._deepseek = httpx.AsyncClient(
            base_url=settings.deepseek_base_url,
            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            timeout=60,
        )
        self._qwen = httpx.AsyncClient(
            base_url=settings.qwen3_base_url,
            headers={"Authorization": f"Bearer {settings.qwen3_api_key}"},
            timeout=60,
            proxy=None,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _post(self, payload: dict) -> dict:
        """Non-streaming POST: DeepSeek first, Qwen3 fallback."""
        try:
            resp = await self._deepseek.post(
                "/chat/completions",
                json={"model": "deepseek-chat", **payload},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning("DeepSeek non-stream failed, falling back to Qwen3: %s", e)

        resp = await self._qwen.post(
            "/chat/completions",
            json={"model": settings.qwen3_model, "enable_thinking": False, **payload},
        )
        resp.raise_for_status()
        return resp.json()

    async def _stream(
        self, messages: list[dict], timing: dict | None = None
    ) -> AsyncGenerator[str, None]:
        """Streaming POST: DeepSeek first, Qwen3 fallback.
        If timing dict provided, fills llm_first_token_cost_ms and llm_generate_cost_ms.
        """
        t_request = time.perf_counter()
        first_token_recorded = False

        async def _iter_lines(resp_stream) -> AsyncGenerator[str, None]:
            nonlocal first_token_recorded
            async for line in resp_stream.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    return
                delta = json.loads(payload)["choices"][0]["delta"].get("content", "")
                if delta:
                    if timing is not None and not first_token_recorded:
                        timing["llm_first_token_cost_ms"] = int(
                            (time.perf_counter() - t_request) * 1000
                        )
                        first_token_recorded = True
                    yield delta

        try:
            async with self._deepseek.stream(
                "POST",
                "/chat/completions",
                json={"model": "deepseek-chat", "messages": messages, "stream": True},
            ) as resp:
                resp.raise_for_status()
                async for chunk in _iter_lines(resp):
                    yield chunk
            if timing is not None:
                timing["llm_generate_cost_ms"] = int(
                    (time.perf_counter() - t_request) * 1000
                ) - timing.get("llm_first_token_cost_ms", 0)
            return
        except Exception as e:
            logger.warning("DeepSeek stream failed, falling back to Qwen3: %s", e)
            # reset timing for fallback
            first_token_recorded = False
            t_request = time.perf_counter()

        async with self._qwen.stream(
            "POST",
            "/chat/completions",
            json={
                "model": settings.qwen3_model,
                "messages": messages,
                "stream": True,
                "enable_thinking": False,
            },
        ) as resp:
            resp.raise_for_status()
            async for chunk in _iter_lines(resp):
                yield chunk
        if timing is not None:
            timing["llm_generate_cost_ms"] = int(
                (time.perf_counter() - t_request) * 1000
            ) - timing.get("llm_first_token_cost_ms", 0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def classify_question(self, question: str) -> str:
        """Return 'intro' or 'scene' based on question type."""
        data = await self._post({
            "messages": [{"role": "user", "content": CLASSIFY_PROMPT.format(question=question)}],
            "stream": False,
            "max_tokens": 10,
        })
        result = data["choices"][0]["message"]["content"].strip()
        return "scene" if "场景" in result else "intro"

    async def is_interview_question(self, text: str) -> bool:
        """Return True if text is an interview question, False if small talk."""
        data = await self._post({
            "messages": [{"role": "user", "content": INTENT_PROMPT.format(text=text)}],
            "stream": False,
            "max_tokens": 5,
        })
        return "面试问题" in data["choices"][0]["message"]["content"].strip()

    async def correct_transcript(self, raw_text: str) -> str:
        """Fix ASR recognition errors in AI/ML domain text."""
        data = await self._post({
            "messages": [{"role": "user", "content": CORRECT_TRANSCRIPT_PROMPT.format(raw_text=raw_text)}],
            "stream": False,
        })
        return data["choices"][0]["message"]["content"].strip()

    async def stream_answer(
        self,
        question: str,
        history: list[dict],
        context_docs: list[str] | None = None,
        timing: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream answer chunks. Uses RAG template if docs provided, else classifies question type.
        If timing dict provided, fills prompt_build_cost_ms, llm_first_token_cost_ms,
        llm_generate_cost_ms, prompt_chars, context_chars.
        """
        t_prompt = time.perf_counter()

        if context_docs:
            context_text = "\n\n".join(context_docs)
            user_content = RAG_TEMPLATE.format(
                context=context_text,
                question=question,
            )
        else:
            context_text = ""
            q_type = await self.classify_question(question)
            user_content = SCENE_PROMPT.format(question=question) if q_type == "scene" else INTRO_PROMPT.format(question=question)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history, {"role": "user", "content": user_content}]

        if timing is not None:
            timing["prompt_build_cost_ms"] = int((time.perf_counter() - t_prompt) * 1000)
            timing["prompt_chars"] = sum(len(m["content"]) for m in messages)
            timing["context_chars"] = len(context_text)

        async for chunk in self._stream(messages, timing=timing):
            yield chunk

    async def rewrite_query(self, question: str, history: list[dict]) -> str:
        """Rewrite a follow-up question into a standalone search query."""
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history[-4:])
        data = await self._post({
            "messages": [{"role": "user", "content": REWRITE_QUERY_PROMPT.format(
                history=history_text, question=question
            )}],
            "stream": False,
            "max_tokens": 100,
        })
        return data["choices"][0]["message"]["content"].strip()

    async def aclose(self) -> None:
        await self._deepseek.aclose()
        await self._qwen.aclose()
