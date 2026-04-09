"""
阿里云实时语音识别 WebSocket 客户端
文档: https://help.aliyun.com/document_detail/84428.html
"""

import asyncio
import hashlib
import hmac
import json
import time
import uuid
import base64
from collections.abc import AsyncGenerator
from urllib.parse import quote

import httpx
import websockets

# Token cache: (token, expire_time)
_token_cache: tuple[str, float] | None = None
_token_lock = asyncio.Lock()


async def _get_token(access_key_id: str, access_key_secret: str) -> str:
    """获取阿里云 NLS Token，带缓存（有效期内复用）"""
    global _token_cache

    async with _token_lock:
        # Reuse if still valid (with 60s buffer)
        if _token_cache and time.time() < _token_cache[1] - 60:
            return _token_cache[0]

        url = "https://nls-meta.cn-shanghai.aliyuncs.com/"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        nonce = str(uuid.uuid4()).replace("-", "")

        params = {
            "AccessKeyId": access_key_id,
            "Action": "CreateToken",
            "Format": "JSON",
            "RegionId": "cn-shanghai",
            "SignatureMethod": "HMAC-SHA1",
            "SignatureNonce": nonce,
            "SignatureVersion": "1.0",
            "Timestamp": timestamp,
            "Version": "2019-02-28",
        }

        sorted_params = sorted(params.items())
        query_string = "&".join(
            f"{quote(k, safe='')}={quote(str(v), safe='')}"
            for k, v in sorted_params
        )
        string_to_sign = f"GET&%2F&{quote(query_string, safe='')}"

        key = (access_key_secret + "&").encode("utf-8")
        signature = base64.b64encode(
            hmac.new(key, string_to_sign.encode("utf-8"), hashlib.sha1).digest()
        ).decode("utf-8")

        params["Signature"] = signature
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            token = data["Token"]["Id"]
            expire_time = data["Token"]["ExpireTime"]  # unix timestamp
            _token_cache = (token, float(expire_time))
            print(f"[AliyunASR] new token acquired, expires at {expire_time}", flush=True)
            return token


class AliyunASRClient:
    """
    阿里云实时语音识别 WebSocket 客户端
    一个实例对应一次识别会话
    """

    WS_URL = "wss://nls-gateway-cn-shanghai.aliyuncs.com/ws/v1"

    def __init__(self, access_key_id: str, access_key_secret: str, app_key: str):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.app_key = app_key
        self._ws = None
        self._token = None
        self._task_id = None

    async def __aenter__(self):
        self._token = await _get_token(self.access_key_id, self.access_key_secret)
        self._task_id = str(uuid.uuid4()).replace("-", "")
        url = f"{self.WS_URL}?token={self._token}"
        print(f"[AliyunASR] connecting, task_id={self._task_id}", flush=True)
        self._ws = await websockets.connect(url)

        # Send StartTranscription directive
        start_msg = {
            "header": {
                "message_id": str(uuid.uuid4()).replace("-", ""),
                "task_id": self._task_id,
                "namespace": "SpeechTranscriber",
                "name": "StartTranscription",
                "appkey": self.app_key,
            },
            "payload": {
                "format": "pcm",
                "sample_rate": 16000,
                "enable_intermediate_result": True,
                "enable_punctuation_prediction": True,
                "enable_inverse_text_normalization": True,
            },
        }
        await self._ws.send(json.dumps(start_msg))

        # Wait for TranscriptionStarted
        resp = json.loads(await self._ws.recv())
        print(f"[AliyunASR] start response: {resp}", flush=True)
        if resp["header"]["name"] not in ("TranscriptionStarted",):
            raise RuntimeError(f"阿里云 ASR 启动失败: {resp}")

        return self

    async def __aexit__(self, *_):
        if self._ws:
            try:
                stop_msg = {
                    "header": {
                        "message_id": str(uuid.uuid4()).replace("-", ""),
                        "task_id": self._task_id,
                        "namespace": "SpeechTranscriber",
                        "name": "StopTranscription",
                        "appkey": self.app_key,
                    },
                    "payload": {},
                }
                await self._ws.send(json.dumps(stop_msg))
            except Exception:
                pass
            await self._ws.close()

    async def send_audio(self, chunk: bytes) -> None:
        await self._ws.send(chunk)

    async def send_end(self) -> None:
        await self.__aexit__(None, None, None)

    async def receive_results(self) -> AsyncGenerator[tuple[str, bool], None]:
        """Yield (text, is_final) until transcription completes."""
        async for raw in self._ws:
            msg = json.loads(raw)
            name = msg["header"]["name"]
            payload = msg.get("payload", {})

            if name == "TranscriptionResultChanged":
                # Interim result
                text = payload.get("result", "")
                if text:
                    yield text, False

            elif name == "SentenceEnd":
                # Final result for a sentence
                text = payload.get("result", "")
                if text:
                    yield text, True

            elif name == "TranscriptionCompleted":
                return

            elif name in ("TaskFailed",):
                raise RuntimeError(f"阿里云 ASR 错误: {msg}")
