# AI 面试助手 — Phase 规划

## Phase 1 — 基础框架搭建 & 运行验证

**后端**
- FastAPI 项目初始化，目录结构搭建
- 健康检查接口 `GET /health`
- CORS 配置（允许前端跨域）
- 基础 session 管理骨架（内存 dict）
- WebSocket 基础连接测试端点 `WS /ws/test`
- 依赖管理 `requirements.txt`

**前端**
- React + TypeScript 项目初始化（Vite）
- 基础路由结构
- WebSocket hook 骨架 `useWebSocket.ts`
- 联通后端健康检查，页面显示"服务正常"
- 依赖管理 `package.json`

**验收标准**：前后端均能启动，前端能 ping 通后端 `/health`，WebSocket 能建立连接并收发消息。

---

## Phase 2 — 前端 UI 研发

**布局**
- 整体三区布局：顶部状态栏 / 左侧字幕区 / 右侧答案区
- 顶部：会话状态指示、录音开关按钮、session 信息
- 左侧 `Transcript` 组件：实时字幕流，逐句追加，当前句高亮
- 右侧 `AnswerPanel` 组件：流式答案渲染（SSE 逐字显示）、来源标注（知识库 or 在线搜索）

**交互细节**
- 录音按钮：开始/停止状态切换
- 字幕区：ASR 中间结果用灰色，最终结果用白色
- 答案区：Markdown 渲染支持（代码块、列表）
- 加载状态：检索中 / 生成中 loading 指示

**验收标准**：UI 静态 mock 数据下完整渲染，交互状态正常切换，无需真实接口。

---

## Phase 3 — 后端接口研发

按依赖顺序逐个实现：

**3.1 ASR 链路**
- 讯飞 ASR WebSocket 客户端封装 `asr_client.py`
- 后端 WebSocket 端点 `WS /ws/asr`：接收前端音频块 → 转发 ASR → 增量文本推回前端
- M2 纠错：ASR 句子完整后送 DeepSeek 纠错

**3.2 检索层**
- ES 连接配置，索引初始化脚本
- 知识库文档导入工具（支持 txt/md/pdf）
- 向量化（Embedding 模型选型）
- 混合检索服务 `retriever.py`，阈值 0.85
- 在线搜索兜底 `web_search.py`（Tavily API）

**3.3 生成层**
- DeepSeek 客户端封装 `generator.py`
- RAG Prompt 模板（面试答题角色）
- SSE 流式输出端点 `GET /chat/stream`
- 会话上下文注入（最近 N 轮）

**3.4 会话管理**
- `session_manager.py`：创建/获取/更新/销毁 session
- 上下文窗口管理（超出 N 轮自动裁剪）
- `POST /session/create`、`DELETE /session/{id}`

**验收标准**：每个接口单独可测（Postman / pytest），ASR → 纠错 → 检索 → 生成全链路后端跑通。

---

## Phase 4 — 前后端联调

**联调顺序**
1. WebSocket ASR 链路：前端音频 → 后端 → ASR → 字幕实时显示
2. 纠错结果回显：最终句子纠错后更新字幕
3. 检索 + 生成：纠错句触发检索，SSE 答案流式渲染到右侧面板
4. 会话连贯性：多轮追问场景验证上下文记忆

**端到端验收场景**
- 说出"LoRA 微调中 rank 和 alpha 参数怎么设置"
- 左侧字幕实时出现，纠错后定稿
- 右侧答案流式输出，标注来源
- 追问"对模型效果有什么影响"，系统理解上下文正确回答
