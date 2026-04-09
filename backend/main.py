from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.routers import asr, chat
from backend.routers.session import router as session_router
from backend.routers.kb import router as kb_router
from backend.services.aliyun_asr_client import _get_token

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(asr.router, tags=["asr"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(session_router)
app.include_router(kb_router)


@app.on_event("startup")
async def startup():
    """预热阿里云 ASR Token"""
    try:
        await _get_token(settings.aliyun_access_key_id, settings.aliyun_access_key_secret)
    except Exception as e:
        print(f"[startup] ASR token warmup failed: {e}", flush=True)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.app_name}


@app.websocket("/ws/test")
async def ws_test(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            msg = await websocket.receive_text()
            await websocket.send_text(f"echo: {msg}")
    except WebSocketDisconnect:
        pass
