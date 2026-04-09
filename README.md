# 面试助手 AI Interview Assistant

实时语音/文字面试辅助工具，支持 ASR 转录、知识库检索、DeepSeek 流式回答。

---

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + uvicorn (全异步) |
| 前端 | React 18 + TypeScript + Vite |
| ASR | 阿里云 NLS 实时语音识别 |
| LLM | DeepSeek Chat (流式 SSE) |
| 向量检索 | Elasticsearch 8 + 阿里云 dashscope Embedding |

---

## 环境要求

- Python 3.11+
- Node.js 18+
- Elasticsearch 8.x（必须，用于知识库向量检索）
- SQLite3（内置于 Python，无需单独安装）

---

## SQLite 会话数据库

SQLite3 是 Python 标准库内置模块，**无需安装任何额外软件**。

数据库文件会在首次启动后端时自动创建于：

```
backend/data/sessions.db
```

存储内容：
- 所有会话记录（session_id、名称、创建时间）
- 每条对话的完整历史消息

**重启后端后，历史会话和对话记录完整保留。**

如需清空所有会话数据，直接删除该文件即可：

```bash
rm backend/data/sessions.db
```

---

## 安装 Elasticsearch

### 方式一：Docker（推荐）

```bash
docker run -d \
  --name es8 \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
  elasticsearch:8.13.0
```

验证是否启动成功：

```bash
curl http://localhost:9200
```

返回包含 `"tagline": "You Know, for Search"` 即为成功。

### 方式二：本地安装

#### Windows / Mac
1. 访问 [https://www.elastic.co/downloads/elasticsearch](https://www.elastic.co/downloads/elasticsearch) 下载 8.x 版本
2. 解压后进入目录，编辑 `config/elasticsearch.yml`，添加：
   ```yaml
   xpack.security.enabled: false
   ```
3. 启动：
   ```bash
   # Mac/Linux
   ./bin/elasticsearch
   # Windows
   bin\elasticsearch.bat
   ```

#### Linux（apt / yum）

**Ubuntu / Debian：**
```bash
# 导入 GPG key
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo gpg --dearmor -o /usr/share/keyrings/elasticsearch-keyring.gpg

# 添加源
echo "deb [signed-by=/usr/share/keyrings/elasticsearch-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list

# 安装
sudo apt update && sudo apt install -y elasticsearch

# 禁用安全认证（开发环境）
sudo sed -i 's/xpack.security.enabled: true/xpack.security.enabled: false/' /etc/elasticsearch/elasticsearch.yml
# 若文件中没有该行，手动追加
echo "xpack.security.enabled: false" | sudo tee -a /etc/elasticsearch/elasticsearch.yml

# 启动并设置开机自启
sudo systemctl daemon-reload
sudo systemctl enable elasticsearch
sudo systemctl start elasticsearch
```

**CentOS / RHEL：**
```bash
# 添加 yum 源
sudo rpm --import https://artifacts.elastic.co/GPG-KEY-elasticsearch
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

### 已安装 ES 后如何启动

**Docker 方式**（容器已存在，重启即可）：
```bash
docker start es8
```

**本地安装方式**（每次重新进入解压目录执行）：
```bash
# Linux/Mac
cd /path/to/elasticsearch-8.x.x
./bin/elasticsearch

# Windows
cd C:\path\to\elasticsearch-8.x.x
bin\elasticsearch.bat
```

> 建议将 ES 启动命令加入系统服务或开机自启，避免每次手动启动。

> ES 默认监听 `http://localhost:9200`，与 `.env` 中 `ES_URL` 保持一致即可。

---

## 快速启动

### 1. 克隆项目

```bash
git clone <repo-url>
cd Interview_Assistant
```

### 2. 获取 API Key

#### DeepSeek API Key

1. 访问 [https://platform.deepseek.com](https://platform.deepseek.com) 注册账号
2. 进入「API Keys」页面，点击「创建 API Key」
3. 复制生成的 Key，填入 `DEEPSEEK_API_KEY`

#### 阿里云 AccessKey（ASR + Embedding 共用）

1. 访问 [https://ram.console.aliyun.com](https://ram.console.aliyun.com) 登录阿里云控制台
2. 左侧菜单选择「用户」→「创建用户」，勾选「OpenAPI 调用访问」
3. 创建完成后保存 `AccessKey ID` 和 `AccessKey Secret`（只显示一次）
4. 为该用户授权：`AliyunNLSFullAccess`（ASR）和 `AliyunDashScopeFullAccess`（Embedding）

#### 阿里云 NLS AppKey（语音识别）

1. 访问 [https://nls-portal.console.aliyun.com](https://nls-portal.console.aliyun.com)
2. 点击「创建项目」，开通「实时语音识别」服务
3. 进入项目详情，复制 `AppKey` 填入 `ALIYUN_NLS_APP_KEY`

#### 阿里云 dashscope API Key（Embedding + Qwen3 兜底）

1. 访问 [https://dashscope.console.aliyun.com](https://dashscope.console.aliyun.com)
2. 左侧菜单「API-KEY 管理」→「创建新的 API-KEY」
3. 复制 Key 分别填入 `DASHSCOPE_API_KEY` 和 `QWEN3_API_KEY`（可以用同一个 Key）

> `DASHSCOPE_API_KEY` 和阿里云 `AccessKey` 是两套不同的认证体系：AccessKey 用于调用 NLS ASR，dashscope Key 用于调用 Embedding 和 Qwen3 接口。

---

### 3. 配置环境变量

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，填入以下 Key：

```env
# DeepSeek
DEEPSEEK_API_KEY=your_deepseek_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# 阿里云 ASR (NLS)
ALIYUN_ACCESS_KEY_ID=your_access_key_id
ALIYUN_ACCESS_KEY_SECRET=your_access_key_secret
ALIYUN_NLS_APP_KEY=your_nls_app_key

# 阿里云 dashscope Embedding
DASHSCOPE_API_KEY=your_dashscope_key_here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v2

# Qwen3 兜底 LLM（DeepSeek 不可用时自动切换）
QWEN3_API_KEY=your_dashscope_key_here
QWEN3_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN3_MODEL=qwen3-14b

# Elasticsearch（必须）
ES_URL=http://localhost:9200
ES_INDEX=interview_kb
ES_USERNAME=
ES_PASSWORD=
ES_SCORE_THRESHOLD=0.85
```

### 4. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

> 推荐使用 conda 或 venv 隔离环境：
> ```bash
> conda create -n interview python=3.11
> conda activate interview
> pip install -r requirements.txt
> ```

### 5. 安装前端依赖

```bash
cd frontend
npm install
```

### 6. 启动后端

在项目根目录执行：

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
```

启动成功后会看到：

```
[AliyunASR] new token acquired, expires at ...
INFO: Uvicorn running on http://0.0.0.0:8001
```

### 7. 启动前端

新开一个终端，在 `frontend/` 目录执行：

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
5. 左侧可切换历史会话，点击 × 删除会话

---

## 知识库管理

1. 点击左侧「**知识库管理**」展开面板
2. 拖拽或点击上传 `.md` / `.txt` 文件
3. 文件会自动分块并写入 Elasticsearch
4. 点击文件右侧 × 可删除

---

## 初始化知识库（可选）

如果已有 `.md` 文件想批量导入：

```bash
cd backend
python scripts/init_kb.py
```

---

## 目录结构

```
Interview_Assistant/
├── backend/
│   ├── core/               # 配置 (config.py)
│   ├── routers/            # API 路由 (asr, chat, session, kb)
│   ├── services/
│   │   ├── prompts.py      # 所有 LLM 提示词常量
│   │   ├── llm_client.py   # LLM 客户端 (DeepSeek 优先, Qwen3 兜底)
│   │   ├── aliyun_asr_client.py  # 阿里云 NLS ASR
│   │   ├── corrector.py    # ASR 纠错封装
│   │   ├── retriever.py    # ES 混合检索
│   │   └── session_manager.py   # SQLite 会话持久化
│   ├── scripts/            # 知识库初始化脚本
│   ├── knowledge_base/     # 上传的文档存储目录
│   ├── data/               # SQLite 数据库 (自动创建)
│   ├── main.py
│   ├── requirements.txt
│   ├── .env                # 环境变量 (不提交)
│   └── .env.example        # 环境变量模板
└── frontend/
    ├── src/
    │   ├── api/            # 所有 HTTP/SSE 调用
    │   ├── components/     # UI 组件
    │   ├── hooks/          # React Hooks
    │   ├── styles/         # CSS 变量 + 主题
    │   └── types/          # TypeScript 类型定义
    ├── package.json
    └── vite.config.ts
```
