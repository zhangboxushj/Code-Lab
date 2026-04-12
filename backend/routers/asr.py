import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.config import settings
from backend.services.aliyun_asr_client import AliyunASRClient
from backend.services.llm_client import LLMClient

router = APIRouter()
logger = logging.getLogger(__name__)
_llm = LLMClient()


@router.websocket("/ws/asr")
async def asr_endpoint(websocket: WebSocket, session_id: str = ""):
    await websocket.accept()

    try:
        async with AliyunASRClient(
            settings.aliyun_access_key_id,
            settings.aliyun_access_key_secret,
            settings.aliyun_asr_app_key,
        ) as asr:
            await websocket.send_json({"type": "ready"})

            first_audio_received = asyncio.Event()

            async def _receive_audio():
                try:
                    while True:
                        message = await websocket.receive()
                        if "bytes" in message and message["bytes"]:
                            await asr.send_audio(message["bytes"])
                            first_audio_received.set()
                        elif "text" in message:
                            break
                except WebSocketDisconnect:
                    await asr.send_end()

            async def _forward_results():
                await asyncio.wait_for(first_audio_received.wait(), timeout=10.0)
                async for text, is_final in asr.receive_results():
                    if is_final:
                        corrected = await _llm.correct_transcript(text)
                        await websocket.send_json(
                            {"type": "transcript", "text": corrected, "is_final": True}
                        )
                    else:
                        await websocket.send_json(
                            {"type": "transcript", "text": text, "is_final": False}
                        )

            await asyncio.gather(_receive_audio(), _forward_results())

    except Exception:
        logger.exception("ASR endpoint error")
        try:
            await websocket.send_json({"type": "error", "text": "ASR error"})
        except Exception:
            pass
