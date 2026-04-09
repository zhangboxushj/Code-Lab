# 项目运行流程详解

从用户发起一个问题，到屏幕上出现流式回答，整个链路经过以下几个阶段。

---

## 总览

```
用户输入（语音 / 文字）
        ↓
  [输入处理层]
  语音 → ASR → 纠错   /   文字直接传入
        ↓
  [检索层]
  Query → Embedding → ES 混合检索（BM25 + kNN）
        ↓
  [生成层]
  问题分类 → 选择 Prompt → DeepSeek 流式生成
        ↓
  [输出层]
  SSE 流 → 前端逐 token 渲染
```

---

## 一、用户输入

### 1.1 语音模式

```
麦克风 PCM 音频
  → ScriptProcessorNode（bufferSize=2048）采集
  → Int16 PCM 转换
  → WebSocket /ws/asr 发送二进制帧
```

前端 `useASR.ts` 负责：
- 调用 `getUserMedia` 获取麦克风权限
- 建立 WebSocket 连接到后端 `/ws/asr`
- 等待后端返回 `{"type":"ready"}` 信号后才开始发送音频（防止 ASR 连接未就绪就收到数据）
- 用 `ScriptProcessorNode` 以 16kHz 采样率捕获 PCM，转为 Int16 后发送

### 1.2 文字模式

用户在输入框输入问题，按 Enter 或点击「发送」，直接调用 `sendTextQuestion()`，跳过 ASR 流程，直接进入检索层。

---

## 二、ASR 语音识别（语音模式专属）

```
后端 /ws/asr
  → AliyunASRClient 建立 NLS WebSocket
  → 获取阿里云 Token（24h 缓存）
  → 发送 StartTranscription 指令
  → 转发 PCM 音频帧
  → 接收识别结果（interim / final）
  → final 结果送入纠错模块
```

**Token 缓存机制**：阿里云 NLS 需要先用 AccessKey 换取临时 Token，有效期 24 小时。系统在启动时预热获取 Token，后续请求直接复用，避免每次请求都调用换 Token 接口。

**纠错模块**（`corrector.py` → `generator.py:correct_transcript`）：
- 调用 DeepSeek 对 final 识别结果做一次单轮纠错
- 内置 AI/ML 领域术语对照表（RAG、LoRA、Transformer、Milvus 等）
- 只返回纠正后的文本，不改变句子结构

纠错后的文本作为最终 `question` 传入检索层。

---

## 三、知识库检索

```
question
  → dashscope text-embedding-v2（1536维向量）
  → ES 混合检索
      ├── BM25 全文检索（match query）
      └── kNN 向量检索（cosine similarity）
  → 过滤 score < 0.85 的结果
  → 返回 top-5 文本片段
```

**混合检索原理**：ES 8.x 支持在同一请求中同时执行 `query`（BM25）和 `knn`，两路结果由 ES 内部做 RRF（Reciprocal Rank Fusion）融合排序，兼顾关键词精确匹配和语义相似度。

**阈值过滤**：只有 `_score >= 0.85` 的文档才会被采用。低于阈值说明知识库中没有相关内容，系统自动降级为 DeepSeek 直接回答。

**检索失败降级**：若 ES 不可用或 Embedding 调用失败，`hybrid_search` 返回空列表 `[]`，后续流程自动走直接回答路径。

---

## 四、知识库文档切片

文档上传时（`/api/kb/upload`）进行切片，切片结果存入 ES。

### 4.1 Markdown 文件（按标题切片）

```
原始 .md 文件
  → 按 #### 标题分割（re.split）
  → 每个 section 作为一个候选 chunk
  → 若 section 长度 > 400 字符：
      → 按代码块（```...```）进一步拆分
      → 滑动拼接，每块不超过 400 字符
  → 每块硬截断至 1800 字符（Embedding API 上限保护）
```

示例：
```markdown
#### RAG 和 GraphRAG 的区别
RAG 是...（400字以内 → 单独一块）

#### 大模型微调方法
LoRA 原理...（超过400字 → 按代码块拆分为多块）
```

### 4.2 纯文本文件（固定大小切片）

```
原始 .txt 文件
  → 每 400 字符切一块
  → 相邻块重叠 50 字符（保留上下文连续性）
  → 过滤长度 < 20 字符的碎片
```

### 4.3 写入 ES

```
chunks（批次=10）
  → dashscope Embedding（批量）
  → ES bulk 写入
      字段：id, title, text, embedding(1536d), source, metadata.filename
```

---

## 五、LLM 生成

### 5.1 有知识库命中（RAG 路径）

```
context_docs（检索到的文本片段）
  → 拼接为 context 字符串
  → 填入 RAG_TEMPLATE：
      "以下是从知识库检索到的相关内容：{context}
       请根据以上内容回答：{question}"
  → 加入 session history（上下文记忆）
  → DeepSeek stream=True 流式生成
```

### 5.2 无知识库命中（直接回答路径）

```
question
  → 问题分类（单独调用 DeepSeek，max_tokens=10）
      "介绍型"：询问概念/原理/区别
      "场景型"：给出业务场景要求设计方案
  → 选择对应 Prompt 模板：
      介绍型 → INTRO_PROMPT（500字以内，1.2.3.格式，含核心架构）
      场景型 → SCENE_PROMPT（两套技术方案，列出工具/包/库）
  → 加入 session history
  → DeepSeek stream=True 流式生成
```

### 5.3 上下文记忆

每次问答完成后，`update_session` 将 `user` 和 `assistant` 消息追加到 session history，下次请求时一并传给 DeepSeek，实现多轮对话记忆。history 最多保留 40 条消息（20轮对话），超出后滚动丢弃最早的记录。

---

## 六、流式输出（SSE）

```
DeepSeek SSE 流
  → 后端逐 token yield
      data: {"type": "chunk", "text": "..."}
  → 最后发送
      data: {"type": "done", "source": "kb" | "direct"}
  → 前端 fetch ReadableStream 读取
  → 逐 token append 到 QACard.answer
  → ReactMarkdown 实时渲染
```

前端不自动滚动到底部，用户可以自由浏览历史回答。

---

## 七、会话管理

```
createSession() → POST /api/session → 返回 session_id
  ↓
第一个问题发出后 → PATCH /api/session/{id}/name（以问题前30字命名）
  ↓
每轮问答 → update_session(role="user/assistant", content=...)
  ↓
切换会话 → 前端重置 qaCards / utterances / firstQuestionFired
  ↓
删除会话 → DELETE /api/session/{id}
```

会话数据存储在后端内存中（`_sessions` dict），服务重启后清空。

---

## 八、完整时序图

```
用户          前端              后端 ASR          后端 Chat         DeepSeek
 |             |                   |                  |                |
 |--说话-----→|                   |                  |                |
 |             |--PCM音频(WS)----→|                  |                |
 |             |                   |--NLS识别------→ |                |
 |             |                   |←--interim/final--|                |
 |             |                   |--纠错(DeepSeek)→|                |
 |             |←--transcript------|                  |                |
 |             |                   |                  |                |
 |             |--GET /chat/stream(question)--------→|                |
 |             |                   |                  |--Embedding---→|
 |             |                   |                  |←--vector------|
 |             |                   |                  |--ES混合检索    |
 |             |                   |                  |--分类/RAG---→ |
 |             |                   |                  |←--stream chunk-|
 |             |←--SSE chunk--------------------------------|         |
 |←--渲染-----|                   |                  |                |
```
