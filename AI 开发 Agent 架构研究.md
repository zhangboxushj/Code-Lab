# **全自动 AI 开发 Agent 的核心架构设计与工程实现深度研究报告**

## **第一部分：自主开发 Agent 的完整架构图**

在当前软件工程演进的范式中，全自动 AI 开发 Agent 代表了从“辅助编码”向“自主工程”跨越的核心里程碑。该架构的设计目标是实现从自然语言需求到工业级可运行代码的闭环转化。本架构的核心理念在于将大语言模型（LLM）的逻辑推理能力与确定性的软件工程工具链深度耦合，形成一个能够自我演进、自我纠错的动态系统。

### **架构总图**

代码段

graph TD  
    User(\[用户自然语言需求\]) \--\> ReqAnalyzer  
      
    subgraph "Main Loop \- 智能编排主循环"  
        ReqAnalyzer \--\> Planner\[任务规划器 Global Planner\]  
        Planner \--\> TaskStore  
        TaskStore \--\> Executor{执行器分发 Executor}  
          
        subgraph "Executor \- 沙盒执行环境"  
            Executor \--\> ToolRegistry  
            ToolRegistry \--\> SearchEngine\[代码检索引擎\]  
            ToolRegistry \--\> FileEditor\[结构化文件编辑器\]  
            ToolRegistry \--\> ShellRuntime  
        end  
          
        Executor \--\> Verifier\[多维验证器 Verifier\]  
          
        subgraph "Self-Healing \- 自愈闭环"  
            Verifier \-- 验证失败 \--\> ErrorAnalyzer\[错误根因分析器\]  
            ErrorAnalyzer \--\> FixGen\[修复方案生成器\]  
            FixGen \--\> Executor  
        end  
          
        Verifier \-- 验证成功 \--\> TaskUpdate\[任务状态更新\]  
        TaskUpdate \--\> TaskStore  
    end  
      
    subgraph "Context Engine \- 上下文智能引擎"  
        RepoMap \-.-\> Planner  
        Compaction\[上下文压缩流水线\] \-.-\> Executor  
        StateHistory\[(事件溯源日志)\] \-.-\> MainLoop  
    end  
      
    TaskStore \-- 计划全部完成 \--\> Deliverer\[交付准备与总结\]  
    Deliverer \--\> FinalProduct(\[可运行代码产物\])

    style Self-Healing fill:\#f9f,stroke:\#333,stroke-width:2px  
    style Main Loop fill:\#bbf,stroke:\#333,stroke-width:2px

### **组件职责说明**

全自动 Agent 的效能由以下核心组件共同决定：

1. **需求解析器 (Requirement Analyzer)**：这是系统的入口点。它的职责并非简单地传递文本，而是进行实体提取与意图对齐。它将模糊的自然语言转化为包含功能模块（Modules）、受影响文件（Files）、期望函数签名（Signatures）及约束条件（Constraints）的结构化 JSON。  
2. **任务规划器 (Global Planner)**：基于层次任务网络（HTN）或思维树（ToT）算法，将结构化需求拆解为具有依赖关系的原子任务序列 1。任务被存储在具有状态感知的任务库（Task Store）中。  
3. **执行器 (Executor) 与工具注册表 (Tool Registry)**：执行器根据当前任务调取相应工具。工具注册表采用 OpenHands 的 Action-Observation 模式，确保每一次原子操作（如写文件、运行命令）都有对应的观察结果回传 3。  
4. **多维验证器 (Verifier)**：集成 Linter 静态检查、编译器反馈以及单元测试。验证器是驱动自愈循环的唯一信号源。  
5. **上下文智能引擎 (Context Engine)**：借鉴 Aider 的 Repo Map 技术，构建基于 AST 的代码符号索引，为 LLM 提供跨文件的语义视野，同时利用压缩流水线（Compaction Pipeline）管理 Token 预算 4。

### **数据流与控制流解释**

当用户输入需求后，**需求解析器**首先被调用，它通过与现有代码库的元数据（Repo Map）对比，确定开发任务的技术栈和影响范围。**规划器**随后产出任务列表并存入 **Task Store**。**执行器**通过消费这些任务，依次调用工具层进行编码。

代码编写完成后，控制流进入**验证器**。若验证失败，信号被路由至**自愈模块**，错误日志与上下文被重新打包发送给 LLM 生成修复指令。若验证通过，**Task Store** 更新状态并触发下一个子任务。当所有任务标记为“已完成”且通过最终集成测试时，Agent 终止执行并向用户提交成果总结。若在自愈循环中达到重试阈值（如 5 次）或遇到环境崩溃（如 OOM），Agent 会执行回滚操作并输出故障报告 5。

### **一次典型需求执行的时序图**

代码段

sequenceDiagram  
    participant U as 用户  
    participant R as 需求解析/规划器  
    participant C as 上下文/代码库  
    participant E as 执行/自愈层  
    participant T as 验证/测试环境

    U-\>\>R: 输入：“修改 API 以支持 JWT 校验”  
    R-\>\>C: 获取项目 Repo Map 与 Auth 逻辑  
    C--\>\>R: 返回 symbols 和依赖树  
    R-\>\>R: 生成步骤：1.安装依赖 2.写中间件 3.修改路由  
    R-\>\>E: 执行步骤 1 & 2  
    E-\>\>C: 写入 middleware/jwt.py  
    E-\>\>T: 运行 pytest  
    T--\>\>E: 报错：ImportError (Missing pyjwt)  
    Note over E: 触发自愈循环  
    E-\>\>E: 分析报错 \-\> 识别缺失包  
    E-\>\>C: 执行 pip install pyjwt 并更新 requirements.txt  
    E-\>\>T: 重新运行测试  
    T--\>\>E: 测试通过  
    E--\>\>U: 完成交付，附带修改清单

## ---

**第二部分：完整 Skills 清单**

全自动开发 Agent 必须具备全栈式的工程能力。以下 Skills 清单涵盖了感知、规划、执行、验证和交付的每一个环节。

| 阶段 | Skill 名称 | 功能描述 | 输入参数 | 输出内容 | 底层实现 | 优先级 |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **感知** | search\_repo\_map | 检索代码库全局符号及引用关系 | query (符号名) | 匹配位置及定义摘要 | ctags / tree-sitter 4 | P0 |
| **感知** | grep\_code | 在代码库中进行高性能正则搜索 | pattern, path | 匹配行及上下文 | ripgrep 7 | P0 |
| **感知** | list\_files | 递归列出目录结构，支持忽略模式 | path, ignore\_git | 文件树 JSON | find / os.walk | P0 |
| **感知** | get\_ast\_outline | 解析单个文件的类、函数及变量大纲 | file\_path | 符号树及行号 | tree-sitter / ast 库 | P1 |
| **感知** | read\_environment | 识别当前项目的框架、语言及依赖版本 | 无 | 环境报告 | package.json / venv 扫描 | P1 |
| **规划** | decompose\_task | 将需求拆解为有序的原子操作序列 | requirement | 任务列表 (JSON) | LLM Reasoning 1 | P0 |
| **规划** | prioritize\_tasks | 基于依赖图确定任务执行顺序 | task\_list | 排序后的任务流 | 拓扑排序算法 | P1 |
| **执行** | read\_file | 读取文件内容，支持大文件切片 | path, range | 文本内容 | io.open 8 | P0 |
| **执行** | write\_file | 创建新文件或覆盖已有文件 | path, content | 写入状态 | fs.writeFile | P0 |
| **执行** | edit\_file\_diff | 基于 SEARCH/REPLACE 块进行精确编辑 | diff\_block | 修改确认 | Aider Diff 引擎 9 | P0 |
| **执行** | run\_shell | 在受限沙盒中执行终端命令 | command | stdout, stderr, code | Docker Exec 3 | P0 |
| **执行** | git\_operation | 执行 commit, checkout, diff 等操作 | action, args | Git 输出 | git 命令行 | P1 |
| **执行** | apply\_patch | 应用标准 Unified Diff 补丁文件 | patch\_text | 应用结果 | patch 实用程序 10 | P1 |
| **验证** | run\_linter | 运行静态检查以识别语法错误 | path | 诊断信息列表 | eslint / flake8 11 | P0 |
| **验证** | run\_unit\_tests | 运行项目中定义的单元测试 | test\_path | 通过率及失败日志 | pytest / jest 12 | P0 |
| **验证** | type\_check | 验证类型定义的一致性 | project\_root | 类型错误报告 | tsc / mypy 13 | P1 |
| **验证** | verify\_fix | 针对特定报错验证修复是否生效 | error\_id | Boolean 状态 | 自定义断言逻辑 | P1 |
| **自愈** | analyze\_stack\_trace | 解析运行时堆栈并定位故障文件 | log | 故障点 (File:Line) | 正则解析 \+ LLM 14 | P0 |
| **自愈** | suggest\_repair | 生成修复代码逻辑 | context, error | 补丁建议 | LLM Code Repair | P0 |
| **自愈** | rollback\_state | 在连续修复失败时回滚至安全点 | target\_commit | 恢复确认 | git reset \--hard | P1 |
| **交付** | generate\_readme | 自动生成项目的更新说明及用法 | diff\_history | Markdown 文本 | LLM Summarizer 15 | P1 |
| **交付** | summarize\_tokens | 统计并报告本次开发任务的成本 | usage\_log | 费用报告 | 计费接口集成 16 | P2 |

### **关键 Skill 补充说明**

1. **edit\_file\_diff (P0)**：这是全自动 Agent 的核心竞争力。直接重写文件会消耗大量 Token 且容易丢失原有逻辑，通过 SEARCH/REPLACE 这种局部匹配模式，可以确保 Agent 像人类一样进行细粒度修改，显著提高在超大文件中的操作成功率 9。  
2. **search\_repo\_map (P0)**：基于 AST 构建的 Repo Map 不仅仅是文件名列表，它记录了“谁调用了谁”。当 Agent 修改一个函数签名时，它通过此 Skill 能够立即感知到所有需要同步修改的调用点，这是实现多文件协同修改的基础 4。

## ---

**第三部分：各组件深度解析**

### **1\. 需求理解：从模糊到结构化的桥梁**

Agent 的第一步是消除自然语言的二义性。研究表明，单纯的思维链（CoT）在处理复杂工程时容易发生“幻觉偏离”。目前工业界的最佳实践是采用 **ReAct (Reason \+ Act)** 架构。

* **最佳实践 (Claude Code)**：在理解阶段，Agent 不急于编写代码，而是先调用 ls\_dir 和 grep 工具进行“勘察”。通过观察结果来修正其对需求的初步假设。例如，如果用户要求“修改登录逻辑”，Agent 会先搜索 auth, login, session 等关键词，确定项目使用的是 OAuth 还是 JWT，从而在不询问用户的前提下推断技术细节 5。  
* **权衡**：  
  * **思维树 (ToT)**：适合解决逻辑陷阱，但计算成本极高。  
  * **ReAct**：适合工程实践，通过外部工具的实时反馈实现“环境对齐”。  
* **提示词模板**：

  "你是一个资深架构师。请分析以下需求：{{user\_prompt}}。

  1. 请列出你认为会受到影响的文件。  
  2. 请列出你目前缺失的技术细节（如所用库的版本）。  
  3. 请先调用交互式工具搜索这些信息，然后再给出最终的结构化任务计划。"

### **2\. 代码库上下文获取：心智模型的构建**

对于拥有数万行代码的项目，如何将核心逻辑呈现给 LLM 是架构成败的关键。

* **最佳实践 (Aider / AutoCodeRover)**：采用 **Repo Map** 和 **AST 遍历**。Aider 使用 tree-sitter 为整个代码库生成符号地图，仅保留类定义和函数签名，并将这些信息压缩后放入 Context。这比传统的向量检索（RAG）更有效，因为 RAG 往往会丢失代码的层级关系 4。  
* **读取模式**：建议采用“相关性优先”的递归读取。首先读取 Repo Map，然后根据搜索结果读取直接相关的文件，接着根据导入关系（Imports）拉取上游接口定义。这种方法能将上下文消耗降低 90% 以上 17。

### **3\. 规划与任务拆解：原子性与依赖管理**

全自动 Agent 必须具备将宏大目标拆解为可执行微任务的能力。

* **最佳实践 (Devin / OpenHands)**：采用**边做边规划 (Incremental Planning)**。初始规划仅产出高层里程碑，具体的原子任务在执行过程中动态生成。  
* **任务粒度**：函数级是最佳平衡点。文件级粒度太大，容易导致生成超时；行级粒度太小，会导致主循环步数过多而崩溃。  
* **方案对比**：  
  * **一次性生成完整计划**：适合简单任务，但在复杂场景下一旦第一步出错，后续计划全部作废。  
  * **层次任务网络 (HTN)**：通过递归分解，将任务表示为非本原任务到本原操作的映射，目前是工业界实现高度自主性的主流方案 2。

### **4\. 代码生成与编辑：从“生成”到“重构”**

Agent 对已有代码的修改比创建新项目更具挑战性。

* **最佳实践 (SWE-Agent)**：提出 **Agent-Computer Interface (ACI)**。它不让 LLM 直接操作编辑器，而是提供一组简化的命令，如 scroll\_up, replace\_lines。实验证明，将文件内容限制在 100 行的滑动窗口内展示，可以极大提升 LLM 定位 Bug 的准确度 11。  
* **编辑策略**：优先选择 **Diff 模式**。  
  * **Whole Write**：简单但昂贵，且容易误删用户代码。  
  * **Diff/Patch**：精确、节省 Token，且符合版本控制逻辑。

### **5\. 验证与自愈循环：Agent 的免疫系统**

这是全自动系统的核心逻辑。自愈不仅仅是“重试”，而是基于反馈的逻辑修正。

* **最佳实践 (Devin / AutoCodeRover)**：集成 **光谱故障定位 (SBFL)**。当测试失败时，系统不仅提供错误日志，还通过分析代码路径找出最可能的错误行。  
* **自愈提示词构造**：必须包含“错误信息”、“故障代码段”以及“周边依赖代码”。  
* **自愈模式**：  
  1. **静态自愈**：Lint 失败 ![][image1] 修正语法。  
  2. **动态自愈**：测试失败 ![][image1] 修改逻辑。  
  3. **环境自愈**：编译失败 ![][image1] 更新配置或安装依赖。  
* **重试策略**：通常建议最大重试 3-5 次。若仍失败，应触发“回退至上一个成功任务点”并寻求重规划 5。

### **6\. 主控循环架构：自主权的编排器**

主循环是 Agent 的大脑，负责决定下一步动作。

* **最佳实践 (LangGraph)**：将循环建模为**状态机 (State Machine)**。  
  * **状态管理**：使用 Pydantic 维护一个不可变的、版本化的状态库，记录每一步的 Action 和 Observation 22。  
  * **控制逻辑**：主循环应具备“暂停”和“干预”接口。在安全护栏方面，对于高风险命令（如 rm \-rf 或大范围重构），应引入 AskUser 工具作为最终保险 7。

## ---

**第四部分：现有系统对比分析**

| 维度 | Claude Code | OpenHands | Aider | SWE-Agent | AutoCodeRover |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **核心循环** | ReAct Query Loop (Async) | Event-driven State Machine | Chat-based Loop | ReAct with ACI | Two-stage Retrieval-Patch |
| **规划方式** | 动态子任务委派 18 | 显式计划节点 3 | 交互式意图确认 | 实时反馈调整 | 结构化逻辑推演 |
| **代码搜索** | 多层级 Grep \+ LS 7 | 工作空间集成检索 | **Repo Map (AST)** 4 | 简化 Shell 命令 | **程序结构感知搜索** 19 |
| **编辑策略** | 语义 Edit 工具 | Action 模式修改 | **SEARCH/REPLACE 块** | 100 行窗口编辑 | AST 定位补丁生成 |
| **错误恢复** | 5 层压缩 \+ 3 次重试 | 异常事件监听与回退 | Linter 反馈重试 | 强制 Lint 守卫 11 | 基于测试的重试循环 |
| **上下文管理** | **Compaction Pipeline** | 内存冷热分离 | 动态 Token 预算管理 | 极简 ACI 界面 | 两阶段上下文提取 |

**深度洞见：**

1. **Claude Code** 的核心优势在于其**上下文压缩流水线**。它通过五个阶段（Budget Reduction, Snip, Microcompact, Context Collapse, Auto-Compact）动态处理长对话，解决了 Agent 长时间运行后出现的“记忆衰减”问题 5。  
2. **Aider** 证明了即便没有复杂的规划器，只要具备高质量的 **Repo Map** 和高效的 **Diff 协议**，Agent 也能处理复杂的多文件任务 4。  
3. **SWE-Agent** 通过 ACI 理论强调：AI 不需要完整的 Linux Shell，太多的自由反而会增加出错率。提供受限、精确的工具接口是提升自主性的捷径 11。

## ---

**第五部分：MVP 架构推荐**

基于调研结论，为开发者推荐一套可在本地运行、低成本且高可靠的 MVP 架构。

### **1\. 控制循环模式：ReAct \+ LangGraph**

推荐采用基于 **LangGraph** 的有向图结构。将 Agent 的行为拆分为 Plan, Act, Reflect 三个节点。这种模式允许系统在验证失败时，逻辑清晰地回溯到 Act 甚至重新执行 Plan 24。

### **2\. 最小工具集 (P0 项)**

* **感知**：ls \-R, grep, 以及基于 tree-sitter 的简单类名提取器。  
* **执行**：read\_file, write\_file, 以及 bash\_executor（运行于 Docker）。  
* **编辑**：实现 Aider 的 SEARCH/REPLACE 块解析器。  
* **验证**：集成 git-lint 和项目原生的测试运行器（如 pytest）。

### **3\. 自愈循环实现方案**

**实现逻辑**：

1. 捕获工具执行的 stderr。  
2. 若报错内容包含语法错误（SyntaxError），直接将错误行及周边 5 行代码发送给 LLM。  
3. 若报错为逻辑失败（测试未通过），则需发送：**当前任务描述 \+ 失败测试用例 \+ 相关源码 \+ 错误 Traceback**。  
4. **循环限制**：设置 MAX\_RETRIES \= 3。单次任务连续失败 3 次后，强制暂停并请求人类介入。

### **4\. 每次 LLM 调用应包含的上下文结构**

为确保 LLM 决策的稳定性，每次 Prompt 应遵循以下层次结构：

* **System Prompt (10%)**：定义 Agent 的身份、可用的工具及其输出格式。  
* **Repo Map (20%)**：项目的全局符号索引，让 LLM 知道可以调用哪些现成的工具函数。  
* **Execution History (30%)**：最近 3 步的操作记录及其结果（Action & Observation）。  
* **Active Context (40%)**：当前正在修改的文件片段、相关的报错信息。

## ---

**第六部分：已知挑战与风险**

即使是目前最顶级的系统（如 Devin 或 Claude Code），在全自动闭环中仍面临以下未决挑战：

1. **上下文腐烂 (Context Rot)**：随着步骤增多，Context 会被大量的 ls 和 grep 输出占满。虽然有压缩算法，但压缩过程本身也会丢失微小但关键的细节（如某个变量的隐式类型） 16。  
2. **不确定性的蝴蝶效应**：在第一步的一个微小重构错误，可能在第十步导致全局集成测试失败。由于 LLM 的非确定性，传统的 Debug 手段难以定位这种跨越多个推理步骤的根因。  
3. **无限自愈循环**：Agent 有时会进入“修复 A 导致 B 坏，修复 B 导致 A 坏”的逻辑死结。目前的系统大多只能通过简单的计数器来终止，缺乏对“循环逻辑”的语义识别能力 27。  
4. **安全护栏与自主性的博弈**：全自动意味着 Agent 拥有执行 rm \-rf 或向外网发送代码的能力。如何在不破坏 Agent 连贯性的前提下，实现毫秒级的实时权限校验（Permission Gating），仍是工程实现的难点 5。  
5. **非标准环境的脆弱性**：现有系统在高度标准化的 Web 项目中表现优异，但在涉及复杂 C++ 编译链、硬件交互或老旧遗留代码（Legacy Code）时，其成功率会大幅下降。

---

**结语**：

构建全自动 AI 开发 Agent 的核心不在于寻找一个“完美的模型”，而在于构建一个**具备强反馈、高容错能力的工程框架**。通过将 LLM 放置在由感知地图（Repo Map）、结构化编辑（Diff）和多维验证（Verifier）组成的受控环境中，我们能够最大限度地发挥生成式 AI 的潜力，同时将其不确定性约束在可控的工程范围之内。

#### **引用的著作**

1. Hierarchical task network \- Wikipedia, 访问时间为 四月 23, 2026， [https://en.wikipedia.org/wiki/Hierarchical\_task\_network](https://en.wikipedia.org/wiki/Hierarchical_task_network)  
2. Hierarchical Task Network (HTN) Planning in AI \- GeeksforGeeks, 访问时间为 四月 23, 2026， [https://www.geeksforgeeks.org/artificial-intelligence/hierarchical-task-network-htn-planning-in-ai/](https://www.geeksforgeeks.org/artificial-intelligence/hierarchical-task-network-htn-planning-in-ai/)  
3. Overview \- OpenHands Docs, 访问时间为 四月 23, 2026， [https://docs.openhands.dev/sdk/arch/overview](https://docs.openhands.dev/sdk/arch/overview)  
4. Repository map | aider, 访问时间为 四月 23, 2026， [https://aider.chat/docs/repomap.html](https://aider.chat/docs/repomap.html)  
5. VILA-Lab/Dive-into-Claude-Code \- GitHub, 访问时间为 四月 23, 2026， [https://github.com/VILA-Lab/Dive-into-Claude-Code](https://github.com/VILA-Lab/Dive-into-Claude-Code)  
6. The Self-Healing Agent Pattern: How to Build AI Systems That Recover From Failure Automatically \- DEV Community, 访问时间为 四月 23, 2026， [https://dev.to/the\_bookmaster/the-self-healing-agent-pattern-how-to-build-ai-systems-that-recover-from-failure-automatically-3945](https://dev.to/the_bookmaster/the-self-healing-agent-pattern-how-to-build-ai-systems-that-recover-from-failure-automatically-3945)  
7. How the agent loop works \- Claude Code Docs, 访问时间为 四月 23, 2026， [https://code.claude.com/docs/en/agent-sdk/agent-loop](https://code.claude.com/docs/en/agent-sdk/agent-loop)  
8. Junior to Agent Architect: Mastering Anthropic's Claude SDK From Scratch \- Towards AI, 访问时间为 四月 23, 2026， [https://pub.towardsai.net/junior-to-agent-architect-mastering-anthropics-claude-sdk-from-scratch-daa39c6964bf](https://pub.towardsai.net/junior-to-agent-architect-mastering-anthropics-claude-sdk-from-scratch-daa39c6964bf)  
9. Edit formats \- Aider, 访问时间为 四月 23, 2026， [https://aider.chat/docs/more/edit-formats.html](https://aider.chat/docs/more/edit-formats.html)  
10. Unified diffs make GPT-4 Turbo 3X less lazy \- Aider, 访问时间为 四月 23, 2026， [https://aider.chat/docs/unified-diffs.html](https://aider.chat/docs/unified-diffs.html)  
11. SWE-agent: Agent-Computer Interfaces Enable ... \- NIPS papers, 访问时间为 四月 23, 2026， [https://proceedings.neurips.cc/paper\_files/paper/2024/file/5a7c947568c1b1328ccc5230172e1e7c-Paper-Conference.pdf](https://proceedings.neurips.cc/paper_files/paper/2024/file/5a7c947568c1b1328ccc5230172e1e7c-Paper-Conference.pdf)  
12. The 6 Types of AI Self-Healing in Test Automation | QA Wolf, 访问时间为 四月 23, 2026， [https://www.qawolf.com/blog/self-healing-test-automation-types](https://www.qawolf.com/blog/self-healing-test-automation-types)  
13. Coding Agents 101: The Art of Actually Getting Things Done \- Devin, 访问时间为 四月 23, 2026， [https://devin.ai/agents101](https://devin.ai/agents101)  
14. How to Build a Self-Healing AI Agent Pipeline: A Complete Guide \- DEV Community, 访问时间为 四月 23, 2026， [https://dev.to/miso\_clawpod/how-to-build-a-self-healing-ai-agent-pipeline-a-complete-guide-95b](https://dev.to/miso_clawpod/how-to-build-a-self-healing-ai-agent-pipeline-a-complete-guide-95b)  
15. Part 2 \- Devin: Autonomous AI for Modernization \- WWT, 访问时间为 四月 23, 2026， [https://www.wwt.com/blog/part-2-devin-autonomous-ai-for-modernization](https://www.wwt.com/blog/part-2-devin-autonomous-ai-for-modernization)  
16. Compaction \- Claude API Docs, 访问时间为 四月 23, 2026， [https://platform.claude.com/docs/en/build-with-claude/compaction](https://platform.claude.com/docs/en/build-with-claude/compaction)  
17. Understanding AI Coding Agents Through Aider's Architecture \- Simran's Writing Room, 访问时间为 四月 23, 2026， [https://simranchawla.com/understanding-ai-coding-agents-through-aiders-architecture/](https://simranchawla.com/understanding-ai-coding-agents-through-aiders-architecture/)  
18. Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems \- arXiv, 访问时间为 四月 23, 2026， [https://arxiv.org/html/2604.14228v1](https://arxiv.org/html/2604.14228v1)  
19. AutoCodeRover: Autonomous Program Improvement \- arXiv, 访问时间为 四月 23, 2026， [https://arxiv.org/html/2404.05427v1](https://arxiv.org/html/2404.05427v1)  
20. Hierarchical Task Network (HTN) Planning (HTN) \- Agentic Design Patterns, 访问时间为 四月 23, 2026， [https://agentic-design.ai/patterns/planning-execution/hierarchical-task-network-planning](https://agentic-design.ai/patterns/planning-execution/hierarchical-task-network-planning)  
21. SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering \- alphaXiv, 访问时间为 四月 23, 2026， [https://www.alphaxiv.org/overview/2405.15793](https://www.alphaxiv.org/overview/2405.15793)  
22. Design Principles \- OpenHands Docs, 访问时间为 四月 23, 2026， [https://docs.openhands.dev/sdk/arch/design](https://docs.openhands.dev/sdk/arch/design)  
23. Tool System & MCP \- OpenHands Docs, 访问时间为 四月 23, 2026， [https://docs.openhands.dev/sdk/arch/tool-system](https://docs.openhands.dev/sdk/arch/tool-system)  
24. Mastering LangGraph: The Backbone of Stateful Multi-Agent AI | by Mukesh Kumar Shah, 访问时间为 四月 23, 2026， [https://pub.towardsai.net/mastering-langgraph-the-backbone-of-stateful-multi-agent-ai-0424500a510b](https://pub.towardsai.net/mastering-langgraph-the-backbone-of-stateful-multi-agent-ai-0424500a510b)  
25. How to Build LangGraph Agents Hands-On Tutorial \- DataCamp, 访问时间为 四月 23, 2026， [https://www.datacamp.com/tutorial/langgraph-agents](https://www.datacamp.com/tutorial/langgraph-agents)  
26. How to Use the /compact Command in Claude Code to Prevent Context Rot | MindStudio, 访问时间为 四月 23, 2026， [https://www.mindstudio.ai/blog/claude-code-compact-command-context-management](https://www.mindstudio.ai/blog/claude-code-compact-command-context-management)  
27. Self-healing code \- Dr.Tiya Vaj, 访问时间为 四月 23, 2026， [https://vtiya.medium.com/self-healing-code-f0db56447aeb](https://vtiya.medium.com/self-healing-code-f0db56447aeb)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAYCAYAAAAYl8YPAAAAXElEQVR4XmNgGAWjYIQABXQBSkArugAlgB+Ig9AFKQEXgVgeXZBcwA3Ei4FYBl1iGhDPIgMvAOJfQNzHgASoahg5AGTYdnRBcsEVBipFgAsQC6ILkguommhHMgAAbC0a/+RrKe8AAAAASUVORK5CYII=>