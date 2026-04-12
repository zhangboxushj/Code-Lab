# 面试助手 AI Interview Assistant

实时语音/文字面试辅助工具，支持 ASR 语音转录、知识库检索增强、DeepSeek 流式回答，帮助候选人在面试中快速获取专业答案。

---

## 目录

- [技术栈](#技术栈)
- [依赖安装](#依赖安装)
- [Embedding 模型说明](#embedding-模型说明)
- [获取 API Key](#获取-api-key)
- [配置环境变量](#配置环境变量)
- [安装项目依赖](#安装项目依赖)
- [启动项目](#启动项目)
- [使用流程](#使用流程)
- [知识库管理](#知识库管理)
- [目录结构](#目录结构)

---

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + uvicorn（全异步） |
| 前端 | React 18 + TypeScript + Vite |
| 会话缓存 | Redis（滑动窗口上下文 + 问题历史） |
| ASR | 阿里云 NLS 实时语音识别 |
| LLM | DeepSeek Chat（流式 SSE），Qwen3 兜底 |
| Embedding | 本地 BAAI/bge-m3（GPU 优先，自动下载） |
| 向量检索 | Elasticsearch 8（BM25 + kNN 混合搜索） |

---

## 依赖安装

> 请按顺序完成以下所有依赖的安装，再进行项目配置和启动。

### 1. Node.js

前端运行环境，要求 **18.x 或以上**。

**Windows / Mac：**

访问 [https://nodejs.org](https://nodejs.org)，下载 LTS 版本安装包，按向导安装。

```bash
node -v   # 应输出 v18.x.x 或更高
npm -v
```

**Linux（Ubuntu / Debian）：**

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
sudo apt install -y nodejs
```

---

### 2. Python

后端运行环境，要求 **3.11 或以上**。

```bash
python --version   # 应输出 Python 3.11.x 或更高
```

推荐使用 conda 管理虚拟环境：

```bash
conda create -n interview python=3.11
conda activate interview
```

---

### 3. Redis

用于会话上下文缓存（滑动窗口 3 轮，TTL 2h）和面试题历史存储（TTL 7d）。

**Docker（推荐）：**

```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
docker exec -it redis redis-cli ping   # 返回 PONG 即成功
```

**Windows 本地：**

访问 [https://github.com/tporadowski/redis/releases](https://github.com/tporadowski/redis/releases) 下载 `.msi` 安装包。

**Linux（Ubuntu）：**

```bash
sudo apt install -y redis-server
sudo systemctl start redis-server
redis-cli ping
```

---

### 4. Elasticsearch

用于知识库向量检索，要求 **8.x 版本**。

**Docker（推荐）：**

```bash
docker run -d \
  --name es8 \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
  elasticsearch:8.13.0
```

验证：

```bash
curl http://localhost:9200
# 返回包含 "tagline": "You Know, for Search" 即成功
```

**Linux（Ubuntu）：**

```bash
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo gpg --dearmor -o /usr/share/keyrings/elasticsearch-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/elasticsearch-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list
sudo apt update && sudo apt install -y elasticsearch
echo "xpack.security.enabled: false" | sudo tee -a /etc/elasticsearch/elasticsearch.yml
sudo systemctl enable elasticsearch && sudo systemctl start elasticsearch
```

---

## Embedding 模型说明

本项目使用 **BAAI/bge-m3** 作为本地 Embedding 模型（约 2.2 GB），无需调用外部 API。

**首次启动时会自动从 HuggingFace 下载模型**，下载完成后缓存到本地，后续启动直接加载，无需重复下载。

- 有 NVIDIA GPU（推荐）：自动使用 CUDA 加速，Embedding 耗时约 20ms
- 仅 CPU：自动降级到 CPU 推理，耗时约 200-500ms

**GPU 用户需安装 CUDA 版 PyTorch：**

```bash
# CUDA 12.4（根据你的 CUDA 版本选择）
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

# CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# 仅 CPU
pip install torch torchvision
```

> 如果网络无法访问 HuggingFace，可手动下载模型后放到 `~/.cache/huggingface/hub/` 目录，或设置镜像：
> ```bash
> export HF_ENDPOINT=https://hf-mirror.com
> ```

---

## 获取 API Key

### DeepSeek API Key

1. 访问 [https://platform.deepseek.com](https://platform.deepseek.com) 注册账号
2. 进入「API Keys」页面，点击「创建 API Key」
3. 复制生成的 Key，填入 `DEEPSEEK_API_KEY`

### 阿里云 AccessKey（ASR 语音识别）

1. 访问 [https://ram.console.aliyun.com](https://ram.console.aliyun.com)
2. 「用户」→「创建用户」，勾选「OpenAPI 调用访问」
3. 保存 `AccessKey ID` 和 `AccessKey Secret`（**只显示一次**）
4. 为该用户授权：`AliyunNLSFullAccess`

### 阿里云 NLS AppKey

1. 访问 [https://nls-portal.console.aliyun.com](https://nls-portal.console.aliyun.com)
2. 「创建项目」，开通「实时语音识别」服务
3. 复制项目 `AppKey` 填入 `ALIYUN_ASR_APP_KEY`

### 阿里云 dashscope API Key（Qwen3 兜底 LLM）

1. 访问 [https://dashscope.console.aliyun.com](https://dashscope.console.aliyun.com)
2. 「API-KEY 管理」→「创建新的 API-KEY」
3. 填入 `QWEN3_API_KEY`

> Embedding 使用本地模型，不需要 dashscope key。

---

## 配置环境变量

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，填入所有 Key：

```env
# DeepSeek（主 LLM）
DEEPSEEK_API_KEY=your_deepseek_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# 阿里云 ASR (NLS)
ALIYUN_ACCESS_KEY_ID=your_access_key_id
ALIYUN_ACCESS_KEY_SECRET=your_access_key_secret
ALIYUN_ASR_APP_KEY=your_nls_app_key

# Qwen3 兜底 LLM（DeepSeek 不可用时自动切换）
QWEN3_API_KEY=your_dashscope_key_here
QWEN3_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN3_MODEL=qwen3-14b

# Elasticsearch
ES_URL=http://localhost:9200
ES_INDEX=interview_kb
ES_USERNAME=
ES_PASSWORD=
ES_SCORE_THRESHOLD=1.0

# Redis
REDIS_URL=redis://localhost:6379/0
```

---

## 安装项目依赖

### 后端依赖

```bash
pip install -r backend/requirements.txt
```

> 安装前请先按照 [Embedding 模型说明](#embedding-模型说明) 安装对应版本的 PyTorch。

### 前端依赖

```bash
cd frontend
npm install
```

---

## 启动项目

> 启动前请确认 Redis 和 Elasticsearch 均已运行。

### 启动后端

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
```

**首次启动**会自动下载 bge-m3 模型（约 2.2 GB），下载完成后输出：

```
[Embedding] loading BAAI/bge-m3 on cuda
[startup] Embedding model warmed up
INFO: Application startup complete.
```

后续启动直接从本地缓存加载，约 15 秒完成预热。

### 启动前端

```bash
cd frontend
npm run dev
```

浏览器访问 [http://localhost:5173](http://localhost:5173)

---

## 使用流程

1. 打开页面，点击左侧「**发起新会话**」
2. 选择输入模式：
   - **录音模式**：点击「开始录音」，对着麦克风说出面试问题
   - **打字模式**：在底部输入框输入问题，按 Enter 或点击「发送」
3. AI 自动检索知识库并流式生成回答
4. 会话名称自动以第一个问题命名
5. 鼠标悬停会话，点击 **↓** 导出本次所有面试题为 `.md` 文件，点击 **×** 删除会话

---

## 知识库管理

1. 点击左侧「**知识库管理**」展开面板
2. 拖拽或点击上传 `.md` / `.txt` 文件
3. 文件会自动分块并写入 Elasticsearch（使用本地 bge-m3 生成向量）
4. 点击文件右侧 × 可删除

批量导入已有文件：

```bash
python backend/scripts/init_kb.py
```

---

## 目录结构

```
Interview_Assistant/
├── backend/
│   ├── core/
│   │   └── config.py             # Pydantic 配置（读取 .env）
│   ├── routers/
│   │   ├── asr.py                # WebSocket /ws/asr（阿里云 NLS）
│   │   ├── chat.py               # GET /api/chat/stream（SSE 流式回答）
│   │   ├── session.py            # /api/session CRUD + 导出
│   │   └── kb.py                 # /api/kb 知识库上传/删除
│   ├── services/
│   │   ├── prompts.py            # 所有 LLM 提示词常量
│   │   ├── llm_client.py         # LLM 客户端（DeepSeek 优先，Qwen3 兜底）
│   │   ├── aliyun_asr_client.py  # 阿里云 NLS ASR 客户端
│   │   ├── retriever.py          # ES 混合检索 + 本地 bge-m3 Embedding
│   │   └── session_manager.py    # Redis 会话持久化
│   ├── scripts/
│   │   └── init_kb.py            # 知识库批量初始化脚本
│   ├── knowledge_base/           # 上传的文档存储目录
│   ├── main.py                   # FastAPI 入口
│   ├── requirements.txt
│   ├── .env                      # 环境变量（不提交 git）
│   └── .env.example              # 环境变量模板
└── frontend/
    ├── src/
    │   ├── api/index.ts          # 所有 HTTP/SSE 调用
    │   ├── components/           # UI 组件
    │   ├── hooks/                # React Hooks
    │   ├── styles/               # CSS 变量 + 主题
    │   └── types/                # TypeScript 类型定义
    ├── index.html
    ├── package.json
    └── vite.config.ts
```
