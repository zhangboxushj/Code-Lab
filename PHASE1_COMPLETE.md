# Phase 1 完成记录

## 完成时间
2026-04-08

## 验收状态
基础框架搭建完毕，前后端可启动并联通。

## 目录结构
```
Assistant_Interview/
├── backend/
│   ├── main.py                    # FastAPI 入口，/health, /ws/test, /api/session
│   ├── requirements.txt           # fastapi, uvicorn, websockets, pydantic-settings, httpx
│   ├── .env.example               # 环境变量模板
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py              # pydantic-settings 配置（DeepSeek + 讯飞 key）
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── asr.py                 # WS /ws/asr 骨架
│   │   └── chat.py                # POST /api/chat 骨架
│   └── services/
│       ├── __init__.py
│       ├── session_manager.py     # 内存 session CRUD，支持上下文裁剪
│       ├── asr_client.py          # 讯飞 ASR 客户端骨架
│       └── generator.py           # DeepSeek 客户端骨架
└── frontend/
    ├── index.html
    ├── package.json               # React 18 + Vite + react-router-dom
    ├── tsconfig.json
    ├── vite.config.ts             # proxy /api, /health → localhost:8000
    └── src/
        ├── main.tsx
        ├── App.tsx                # 三区布局骨架
        ├── components/
        │   ├── StatusBar.tsx      # 轮询 /health，显示服务状态
        │   ├── Transcript.tsx     # WebSocket 连接测试，echo ping
        │   └── AnswerPanel.tsx    # 占位组件
        └── hooks/
            ├── useWebSocket.ts    # WebSocket hook（连接/收发/状态）
            └── useSession.ts      # session 创建 hook
```

## 启动方式

### 后端（从项目根目录运行）
```bash
cd d:/Artificial_Intelligence/code/Assistant_Interview
conda activate ruminate   # 或你的 Python 环境
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
uvicorn backend.main:app --reload --port 8000
```

### 前端
```bash
cd d:/Artificial_Intelligence/code/Assistant_Interview/frontend
npm install
npm run dev
```

## 验收标准
- `GET http://localhost:8000/health` → `{"status":"ok"}`
- `WS ws://localhost:8000/ws/test` → echo 任意文本
- 前端 `http://localhost:5173` → 显示"后端状态: 服务正常"，点击"发送 ping"收到 `echo: ping`

## Phase 2 待办
- 前端完整 UI（三区布局、录音按钮、实时字幕、流式答案面板）
- Markdown 渲染、加载状态、来源标注
