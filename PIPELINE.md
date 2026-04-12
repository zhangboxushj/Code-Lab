# 项目运行流程详解

从用户发起一个问题，到屏幕上出现流式回答，整个链路经过以下几个阶段。

---

## 总览

```
用户输入（语音 / 文字）
        ↓
  [输入处理层]
  语音 → ASR → LLM纠错   /   文字直接传入
        ↓
  [ASR断句合并层]
  静默窗口1.5s合并碎片片段 + 并行classifyText
        ↓
  [检索层]
  Query Rewrite（条件触发）→ bge-m3 Embedding → ES混合检索（BM25 + kNN）
        ↓
  [生成层]
  问题分类 → 选择Prompt → DeepSeek流式生成（Qwen3兜底）
        ↓
  [输出层]
  SSE流 → 前端逐token渲染
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
- 等待后端返回 `{"type":"ready"}` 信号后才开始发送音频
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
  → final 结果送入 LLM 纠错
```

**Token 缓存机制**：阿里云 NLS 需要先用 AccessKey 换取临时 Token，有效期 24 小时。系统在启动时预热获取 Token，后续请求直接复用。

**LLM 纠错**：调用 DeepSeek 对 final 识别结果做一次单轮纠错，内置 AI/ML 领域术语对照表（RAG、LoRA、Transformer、Milvus 等），只返回纠正后的文本。

---

## 三、ASR 断句合并（前端）

阿里云 ASR 按句子边界触发 `is_final`，长问题会被切成多个片段。`useMockInterview.ts` 实现静默窗口合并：

```
收到 final 片段
  → 追加到 pendingFragments
  → 立刻发起 classifyText（并行，不等窗口）
  → 重置 1.5s 静默计时器

1.5s 内无新片段
  → flushFragments 触发
  → 若 classifyText 已返回 → 直接用结果（净增耗时 ≈ 0）
  → 若未返回 → 等待返回后触发

1.5s 内来了新片段
  → 取消上次 classifyText
  → 合并文本重新发起 classifyText
  → 重置计时器
```

**效果**：长问题被正确合并为完整语句后再触发回答，同时 classifyText 与静默窗口并行执行，用户感知延迟不增加。

---

## 四、知识库检索

```
question
  → 代词检测（它/这个/你刚才/上面/前面...）
  → 若含代词 AND history 非空：
      → Query Rewrite（LLM改写为独立查询，max_tokens=100）
  → bge-m3 本地 Embedding（CUDA加速，~20ms）
  → ES 混合检索
      ├── BM25 全文检索（match query）
      └── kNN 向量检索（cosine similarity，dims=1024）
  → 过滤 score < 1.0 的结果
  → 返回 top-3 文本片段，总字符上限 8000
```

**Embedding 模型**：本地部署 `BAAI/bge-m3`（1024维），首次启动自动从 HuggingFace 下载（~2.2 GB），后续从本地缓存加载。有 GPU 时自动使用 CUDA，无 GPU 降级到 CPU。

**混合检索原理**：ES 8.x 在同一请求中同时执行 `query`（BM25）和 `knn`，两路结果内部融合排序，兼顾关键词精确匹配和语义相似度。

**检索失败降级**：若 ES 不可用或 Embedding 失败，`hybrid_search` 返回空列表，后续自动走直接回答路径。

---

## 五、知识库文档切片

文档上传时（`/api/kb/upload`）进行切片，切片结果存入 ES。

### 5.1 Markdown 文件（三级切片策略）

```
原始 .md 文件
  → 按 # / ## / ### / #### 标题分割
  → 检测每个 section 的内容类型：
      code / qa / table / list / comparison / text
  → Q&A、表格、列表：若 ≤ 1400 字符，整体保留
  → 其他：递归切分
      ├── 按段落（\n\n）切分
      ├── 段落过长 → 按句子切分
      └── 单句过长 → 硬截断
  → 每块目标 700 字符，相邻块重叠 100 字符
  → 每块前缀【标题】，便于检索时定位来源
  → 硬截断至 1800 字符（Embedding 上限保护）
```

### 5.2 纯文本文件（固定大小切片）

```
原始 .txt 文件
  → 每 700 字符切一块
  → 相邻块重叠 100 字符
  → 过滤长度 < 20 字符的碎片
```

### 5.3 写入 ES

```
chunks（批次=10）
  → bge-m3 本地 Embedding（批量编码）
  → ES bulk 写入
      字段：id, title, text, embedding(1024d), source, metadata.filename
```

---

## 六、LLM 生成

### 6.1 有知识库命中（RAG 路径）

```
context_docs（检索到的文本片段，最多3条，总计≤8000字符）
  → 拼接为 context 字符串
  → 填入 RAG_TEMPLATE
  → 加入 session history（上下文记忆）
  → DeepSeek stream=True 流式生成
```

### 6.2 无知识库命中（直接回答路径）

```
question
  → 问题分类（DeepSeek，max_tokens=10）
      "介绍型"：询问概念/原理/区别
      "场景型"：给出业务场景要求设计方案
  → 选择对应 Prompt 模板：
      介绍型 → INTRO_PROMPT（500字以内，1.2.3.格式）
      场景型 → SCENE_PROMPT（两套技术方案，列出工具/包/库）
  → 加入 session history
  → DeepSeek stream=True 流式生成
```

### 6.3 DeepSeek → Qwen3 自动兜底

```
DeepSeek 流式请求
  → 若失败（网络错误/限流/超时）
  → 自动切换 Qwen3-14b（dashscope）
  → 重置计时，继续流式输出
```

### 6.4 上下文记忆（滑动窗口）

每次问答完成后，`update_context` 将 `user` 和 `assistant` 消息写入 Redis List，维持最近 **6 条消息（3轮对话）** 的滑动窗口，TTL 2 小时。每条消息截断至 500 字符（可通过 `REDIS_CONTEXT_MSG_MAX_CHARS` 配置）。

---

## 七、流式输出（SSE）

```
DeepSeek SSE 流
  → 后端逐 token yield
      data: {"type": "chunk", "text": "..."}
  → 最后发送
      data: {"type": "done", "source": "kb" | "direct", "elapsed_ms": 1234}
  → 前端 fetch ReadableStream 读取
  → 逐 token append 到 QACard.answer
  → 前端记录 performance.now() 首字延迟
```

---

## 八、会话管理

```
createSession() → POST /api/session → 返回 session_id
  ↓
第一个问题发出后 → PATCH /api/session/{id}/name（以问题前30字命名）
  ↓
每轮问答：
  ├── append_question(session_id, question)    → Redis List session:{id}:questions（TTL 7d）
  ├── update_context(session_id, "user", ...)  → Redis List session:{id}:context（滑动窗口，TTL 2h）
  └── update_context(session_id, "assistant", ...)
  ↓
list_sessions() → pipeline 批量读取所有 session meta（单次 Redis 往返）
  ↓
删除会话 → DELETE /api/session/{id} → pipeline 清除所有相关 key
  ↓
导出面试题 → GET /api/session/{id}/export → 读取 questions list → 生成 .md 文件下载
```

### Redis Key 设计

| Key | 类型 | 内容 | TTL |
|-----|------|------|-----|
| `session:list` | Set | 所有 session_id | 永久 |
| `session:{id}:meta` | Hash | name, created_at | 永久 |
| `session:{id}:context` | List | 最近 6 条消息（3轮） | 2h（滑动刷新） |
| `session:{id}:questions` | List | 全量问题文本 | 7d |

---

## 九、完整时序图

```
用户          前端(useMockInterview)    后端 ASR       后端 Chat        bge-m3/DeepSeek    Redis        ES
 |                   |                     |               |                  |               |            |
 |--说话----------→ |                     |               |                  |               |            |
 |                   |--PCM音频(WS)------→|               |                  |               |            |
 |                   |                     |--NLS识别----→ |                  |               |            |
 |                   |                     |←-interim/final|                  |               |            |
 |                   |                     |--LLM纠错----→ |                  |               |            |
 |                   |←--transcript--------|               |                  |               |            |
 |                   |                     |               |                  |               |            |
 |                   |[静默窗口1.5s]        |               |                  |               |            |
 |                   |[并行classifyText]------------------→|                  |               |            |
 |                   |←--is_question----------------------------------|        |               |            |
 |                   |                     |               |                  |               |            |
 |                   |--GET /chat/stream(question)-------→ |                  |               |            |
 |                   |                     |               |--get_session()→  |               |←-context---|
 |                   |                     |               |--代词检测         |               |            |
 |                   |                     |               |--rewrite_query→  |               |            |
 |                   |                     |               |←-rewritten_q-----|               |            |
 |                   |                     |               |--bge-m3 embed--→ |               |            |
 |                   |                     |               |←-vector----------|               |            |
 |                   |                     |               |--ES混合检索--------------------------------→  |
 |                   |                     |               |←-docs-----------------------------------------|
 |                   |                     |               |--stream_answer→  |               |            |
 |                   |                     |               |←-SSE chunks------|               |            |
 |                   |←--SSE chunk-----------------------------|               |               |            |
 |←--渲染----------|                     |               |                  |               |            |
 |                   |                     |               |--update_context→ |←-LPUSH/LTRIM--|            |
```
