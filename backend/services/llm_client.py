"""LLM client with DeepSeek as primary and Qwen3 as fallback."""
import json
import logging
from collections.abc import AsyncGenerator

import httpx

from backend.core.config import settings
from backend.services.prompts import (
    CLASSIFY_PROMPT,
    CORRECT_TRANSCRIPT_PROMPT,
    INTENT_PROMPT,
    INTRO_PROMPT,
    RAG_TEMPLATE,
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

    async def _stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        """Streaming POST: DeepSeek first, Qwen3 fallback."""
        try:
            async with self._deepseek.stream(
                "POST",
                "/chat/completions",
                json={"model": "deepseek-chat", "messages": messages, "stream": True},
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        return
                    delta = json.loads(payload)["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta
            return
        except Exception as e:
            logger.warning("DeepSeek stream failed, falling back to Qwen3: %s", e)

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
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    return
                delta = json.loads(payload)["choices"][0]["delta"].get("content", "")
                if delta:
                    yield delta

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
    ) -> AsyncGenerator[str, None]:
        """Stream answer chunks. Uses RAG template if docs provided, else classifies question type."""
        if context_docs:
            user_content = RAG_TEMPLATE.format(
                context="\n\n".join(context_docs),
                question=question,
            )
        else:
            q_type = await self.classify_question(question)
            user_content = SCENE_PROMPT.format(question=question) if q_type == "scene" else INTRO_PROMPT.format(question=question)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history, {"role": "user", "content": user_content}]
        async for chunk in self._stream(messages):
            yield chunk

    async def aclose(self) -> None:
        await self._deepseek.aclose()
        await self._qwen.aclose()
