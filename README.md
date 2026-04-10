# 面试助手 AI Interview Assistant

实时语音/文字面试辅助工具，支持 ASR 语音转录、知识库检索增强、DeepSeek 流式回答，帮助候选人在面试中快速获取专业答案。

---

## 目录

- [技术栈](#技术栈)
- [依赖安装](#依赖安装)
  - [1. Node.js](#1-nodejs)
  - [2. Python](#2-python)
  - [3. Redis](#3-redis)
  - [4. Elasticsearch](#4-elasticsearch)
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
| 向量检索 | Elasticsearch 8 + 阿里云 dashscope Embedding |

---

## 依赖安装

> **请按顺序完成以下所有依赖的安装，再进行项目配置和启动。**

### 1. Node.js

前端运行环境，要求 **18.x 或以上**。

**Windows / Mac：**

访问 [https://nodejs.org](https://nodejs.org)，下载 LTS 版本安装包，按向导安装。

安装完成后验证：

```bash
node -v   # 应输出 v18.x.x 或更高
npm -v    # 应输出 9.x.x 或更高
```

**Linux（Ubuntu / Debian）：**

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
sudo apt install -y nodejs
node -v
```

**Linux（CentOS / RHEL）：**

```bash
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo yum install -y nodejs
node -v
```

---

### 2. Python

后端运行环境，要求 **3.11 或以上**。

**Windows / Mac：**

访问 [https://www.python.org/downloads](https://www.python.org/downloads)，下载 3.11+ 安装包。

> Windows 安装时勾选 **「Add Python to PATH」**。

安装完成后验证：

```bash
python --version   # 应输出 Python 3.11.x 或更高
pip --version
```

**Linux（Ubuntu / Debian）：**

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip
python3.11 --version
```

**推荐使用 conda 管理虚拟环境（可选）：**

```bash
conda create -n interview python=3.11
conda activate interview
```

---

### 3. Redis

用于会话上下文缓存（滑动窗口 3 轮，TTL 2h）和面试题历史存储（TTL 7d）。

#### Docker 安装（推荐）

```bash
docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:7-alpine
```

验证：

```bash
docker exec -it redis redis-cli ping
# 返回 PONG 即成功
```

#### Windows 本地安装

访问 [https://github.com/tporadowski/redis/releases](https://github.com/tporadowski/redis/releases)，下载最新 `.msi` 安装包，按向导安装。

安装后启动服务：

```bash
redis-server
```

#### Linux（Ubuntu / Debian）

```bash
sudo apt update
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
redis-cli ping   # 返回 PONG 即成功
```

#### Linux（CentOS / RHEL）

```bash
sudo yum install -y epel-release
sudo yum install -y redis
sudo systemctl enable redis
sudo systemctl start redis
redis-cli ping
```

#### 开启持久化（推荐，防止重启丢数据）

编辑 Redis 配置文件（通常在 `/etc/redis/redis.conf` 或 Redis 安装目录下）：

```conf
# 开启 AOF 持久化
appendonly yes
appendfsync everysec
```

重启 Redis 生效：

```bash
sudo systemctl restart redis-server
```

---

### 4. Elasticsearch

用于知识库向量检索（BM25 + kNN 混合搜索），要求 **8.x 版本**。

#### Docker 安装（推荐）

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

#### Windows / Mac 本地安装

1. 访问 [https://www.elastic.co/downloads/elasticsearch](https://www.elastic.co/downloads/elasticsearch) 下载 8.x 版本
2. 解压后进入目录，编辑 `config/elasticsearch.yml`，添加：
   ```yaml
   xpack.security.enabled: false
   ```
3. 启动：
   ```bash
   # Mac / Linux
   ./bin/elasticsearch

   # Windows
   bin\elasticsearch.bat
   ```

#### Linux（Ubuntu / Debian）

```bash
# 导入 GPG key
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo gpg --dearmor -o /usr/share/keyrings/elasticsearch-keyring.gpg

# 添加源
echo "deb [signed-by=/usr/share/keyrings/elasticsearch-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list

# 安装
sudo apt update && sudo apt install -y elasticsearch

# 禁用安全认证（开发环境）
echo "xpack.security.enabled: false" | sudo tee -a /etc/elasticsearch/elasticsearch.yml

# 启动并设置开机自启
sudo systemctl daemon-reload
sudo systemctl enable elasticsearch
sudo systemctl start elasticsearch
```

#### Linux（CentOS / RHEL）

```bash
# 导入 GPG key
sudo rpm --import https://artifacts.elastic.co/GPG-KEY-elasticsearch

# 添加 yum 源
cat <<EOF | sudo tee /etc/yum.repos.d/elasticsearch.repo
[elasticsearch]
name=Elasticsearch repository for 8.x packages
baseurl=https://artifacts.elastic.co/packages/8.x/yum
gpgcheck=1
gpgkey=https://artifacts.elastic.co/GPG-KEY-elasticsearch
enabled=1
autorefresh=1
type=rpm-md
EOF

# 安装
sudo yum install -y elasticsearch

# 禁用安全认证
echo "xpack.security.enabled: false" | sudo tee -a /etc/elasticsearch/elasticsearch.yml

# 启动并设置开机自启
sudo systemctl daemon-reload
sudo systemctl enable elasticsearch
sudo systemctl start elasticsearch
```

验证：

```bash
curl http://localhost:9200
```

#### 已安装后如何启动

```bash
# Docker 方式（容器已存在）
docker start es8

# Linux systemd
sudo systemctl start elasticsearch

# Windows / Mac 本地安装
./bin/elasticsearch        # Mac/Linux
bin\elasticsearch.bat      # Windows
```

---

## 获取 API Key

### DeepSeek API Key

1. 访问 [https://platform.deepseek.com](https://platform.deepseek.com) 注册账号
2. 进入「API Keys」页面，点击「创建 API Key」
3. 复制生成的 Key，填入 `DEEPSEEK_API_KEY`

### 阿里云 AccessKey（ASR 语音识别用）

1. 访问 [https://ram.console.aliyun.com](https://ram.console.aliyun.com) 登录阿里云控制台
2. 左侧菜单「用户」→「创建用户」，勾选「OpenAPI 调用访问」
3. 创建完成后保存 `AccessKey ID` 和 `AccessKey Secret`（**只显示一次**）
4. 为该用户授权：`AliyunNLSFullAccess`

### 阿里云 NLS AppKey（语音识别项目 Key）

1. 访问 [https://nls-portal.console.aliyun.com](https://nls-portal.console.aliyun.com)
2. 点击「创建项目」，开通「实时语音识别」服务
3. 进入项目详情，复制 `AppKey` 填入 `ALIYUN_ASR_APP_KEY`

### 阿里云 dashscope API Key（Embedding + Qwen3 兜底）

1. 访问 [https://dashscope.console.aliyun.com](https://dashscope.console.aliyun.com)
2. 左侧菜单「API-KEY 管理」→「创建新的 API-KEY」
3. 复制 Key 分别填入 `DASHSCOPE_API_KEY` 和 `QWEN3_API_KEY`（可以用同一个 Key）

> `DASHSCOPE_API_KEY` 和阿里云 `AccessKey` 是两套不同的认证体系：AccessKey 用于调用 NLS ASR，dashscope Key 用于调用 Embedding 和 Qwen3 接口。

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

# 阿里云 dashscope Embedding
DASHSCOPE_API_KEY=your_dashscope_key_here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v2

# Qwen3 兜底 LLM（DeepSeek 不可用时自动切换）
QWEN3_API_KEY=your_dashscope_key_here
QWEN3_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN3_MODEL=qwen3-14b

# Elasticsearch
ES_URL=http://localhost:9200
ES_INDEX=interview_kb
ES_USERNAME=
ES_PASSWORD=
ES_SCORE_THRESHOLD=0.85

# Redis
REDIS_URL=redis://localhost:6379/0
```

---

## 安装项目依赖

### 后端依赖

```bash
# 在项目根目录执行
pip install -r backend/requirements.txt
```

依赖清单：

| 包 | 版本 | 用途 |
|---|---|---|
| fastapi | 0.111.0 | Web 框架 |
| uvicorn[standard] | 0.29.0 | ASGI 服务器 |
| websockets | 12.0 | WebSocket 支持 |
| python-dotenv | 1.0.1 | 环境变量加载 |
| pydantic-settings | 2.2.1 | 配置管理 |
| httpx | 0.27.0 | 异步 HTTP 客户端 |
| elasticsearch[async] | 8.13.0 | ES 客户端 |
| openai | 1.30.0 | OpenAI 兼容接口 |
| redis[asyncio] | 5.0.4 | Redis 异步客户端 |

### 前端依赖

```bash
cd frontend
npm install
```

---

## 启动项目

> 启动前请确认 Redis 和 Elasticsearch 均已运行。

### 启动后端

在项目根目录执行：

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
```

启动成功后会看到：

```
[startup] ASR token warmup ...
INFO: Uvicorn running on http://0.0.0.0:8001
```

### 启动前端

新开一个终端：

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
3. 文件会自动分块并写入 Elasticsearch
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
│   │   ├── corrector.py          # ASR 纠错封装
│   │   ├── retriever.py          # ES 混合检索（BM25 + kNN）
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
