# 软件架构文档 — 抖音博主创作助手

## 架构全景图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BROWSER (SPA)                                  │
│                        static/index.html (~1400 lines)                      │
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────────┐    ┌──────────────────┐  │
│  │   PANEL LEFT     │    │     PANEL CENTER     │    │   PANEL RIGHT    │  │
│  │   (330px)        │    │      (flex:1)        │    │    (310px)       │  │
│  │                  │    │                      │    │                  │  │
│  │  🏷 Header Brand │    │  🔄 Workflow Bar     │    │  📊 Report       │  │
│  │  抖音创作助手     │    │  🎯→🔥→✍️→🔍          │    │  Placeholder     │  │
│  │                  │    │                      │    │                  │  │
│  │  📝 Blog Input   │    │  ┌─────────────────┐ │    │  (future:        │  │
│  │  🎬 Topic Hint   │    │  │ Agent Card 1    │ │    │   analytics,     │  │
│  │  🎭 Templates    │    │  │ 🎯 Strategist   │ │    │   export)        │  │
│  │  🏷 Keywords     │    │  │ direction UI    │ │    │                  │  │
│  │  💡 Topic Reuse  │    │  │ output preview  │ │    │                  │  │
│  │                  │    │  └─────────────────┘ │    │                  │  │
│  │  [✦ 开始创作]    │    │  ┌─────────────────┐ │    │                  │  │
│  │  [⏹ 停止]       │    │  │ Agent Card 2    │ │    │                  │  │
│  │                  │    │  │ 🔥 Planner      │ │    │                  │  │
│  │  📋 History      │    │  │ direction UI    │ │    │                  │  │
│  │  (scrollable)    │    │  │ topic chips     │ │    │                  │  │
│  │                  │    │  └─────────────────┘ │    │                  │  │
│  │                  │    │  ┌─────────────────┐ │    │                  │  │
│  │                  │    │  │ Agent Card 3    │ │    │                  │  │
│  │                  │    │  │ ✍️ Writer       │ │    │                  │  │
│  │                  │    │  │ topic select    │ │    │                  │  │
│  │                  │    │  │ script preview  │ │    │                  │  │
│  │                  │    │  └─────────────────┘ │    │                  │  │
│  │                  │    │  ┌─────────────────┐ │    │                  │  │
│  │                  │    │  │ Agent Card 4    │ │    │                  │  │
│  │                  │    │  │ 🔍 Reviewer     │ │    │                  │  │
│  │                  │    │  │ auto-run, score │ │    │                  │  │
│  │                  │    │  └─────────────────┘ │    │                  │  │
│  │                  │    │  ┌─────────────────┐ │    │                  │  │
│  │                  │    │  │ Final Card      │ │    │                  │  │
│  │                  │    │  │ ✅ 最终脚本     │ │    │                  │  │
│  │                  │    │  └─────────────────┘ │    │                  │  │
│  └──────────────────┘    └──────────────────────┘    └──────────────────┘  │
│         ↕                        ↕                          ↕               │
│    resize-handle            resize-handle                                 │
│   (col-resize, localStorage 持久化宽度)                                    │
└─────────────────────────────────────────────────────────────────────────────┘
          │  POST /api/run-step          │  GET /api/directions
          │  POST /api/run               │  GET /
          │  (SSE: text/event-stream)    │  (HTML)
          ▼                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FASTAPI SERVER (:7861)                            │
│                            src/main.py                                      │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        ROUTE HANDLERS                                │   │
│  │                                                                      │   │
│  │  GET  /              → index.html (static HTML)                      │   │
│  │  GET  /api/directions → STRATEGIST_DIRECTIONS + PLANNER_DIRECTIONS   │   │
│  │  POST /api/run       → SSE: 全自动 4-agent 流水线 (legacy)           │   │
│  │  POST /api/run-step  → SSE: 单步 agent 执行 (step-by-step)           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                    ┌───────────────┴───────────────┐                       │
│                    ▼                               ▼                        │
│       ┌──────────────────────┐      ┌──────────────────────────┐          │
│       │   RunRequest Model   │      │    StepRequest Model      │          │
│       │   - user_input       │      │    - user_input           │          │
│       │   - selected_topic   │      │    - step (strategist/    │          │
│       │   - template         │      │      planner/writer/      │          │
│       └──────────────────────┘      │      reviewer)            │          │
│                                      │    - direction            │          │
│                                      │    - strategist_output    │          │
│                                      │    - planner_output       │          │
│                                      │    - writer_output        │          │
│                                      │    - selected_topic       │          │
│                                      │    - template             │          │
│                                      └──────────────────────────┘          │
│                                    │                                        │
│                    ┌───────────────┴───────────────┐                       │
│                    ▼                               ▼                        │
│       ┌──────────────────────┐      ┌──────────────────────────┐          │
│       │   Background Thread  │      │   Background Thread       │          │
│       │   run_blogger_crew() │      │   run_*_step()            │          │
│       │   → asyncio.Queue    │      │   → asyncio.Queue         │          │
│       └──────────┬───────────┘      └──────────┬───────────────┘          │
│                  │                              │                           │
│                  ▼                              ▼                           │
│       ┌──────────────────────┐      ┌──────────────────────────┐          │
│       │   StreamingResponse  │      │   StreamingResponse       │          │
│       │   (SSE event stream) │      │   (SSE event stream)      │          │
│       └──────────────────────┘      └──────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          │  Python function calls
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CREW ORCHESTRATION LAYER                           │
│                            src/crew.py                                      │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     TEMPLATES & DIRECTIONS                           │   │
│  │  TEMPLATES: 教程/vlog/测评/口播                                      │   │
│  │  STRATEGIST_DIRECTIONS:  情感共鸣/知识干货/娱乐搞笑/种草带货/观点输出   │   │
│  │  PLANNER_DIRECTIONS:     热点借势/痛点解决/反差对比/教程拆解/故事叙事   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │                 FULL PIPELINE (legacy)                             │      │
│  │  run_blogger_crew(user_input, topic, template, callback) → dict    │      │
│  │                                                                    │      │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐       │      │
│  │  │Strategist│──▶│ Planner  │──▶│  Writer  │──▶│ Reviewer │       │      │
│  │  │  Task 0  │   │  Task 1  │   │  Task 2  │   │  Task 3  │       │      │
│  │  └──────────┘   └──────────┘   └──────────┘   └──────────┘       │      │
│  │                                                    │              │      │
│  │                                    ┌───────────────┘              │      │
│  │                                    ▼                              │      │
│  │                          ┌─────────────────┐                      │      │
│  │                          │ REVISION LOOP    │ (max 2 rounds)       │      │
│  │                          │ Score ≤ 6?       │                      │      │
│  │                          │ Writer→Reviewer  │                      │      │
│  │                          └─────────────────┘                      │      │
│  └────────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │                 STEP-BY-STEP (new)                                 │      │
│  │                                                                    │      │
│  │  run_strategist_step(user_input, template, direction, callback)   │      │
│  │  run_planner_step(user_input, strategist_output, direction, cb)   │      │
│  │  run_writer_step(user_input, strategist_output, topic, cb)        │      │
│  │  run_reviewer_step(user_input, strategist_output, topic,          │      │
│  │                     writer_output, cb)                            │      │
│  │                                                                    │      │
│  │  Each function:                                                    │      │
│  │  1. load_config() → LLM(deepseek/{model}, api_key, T, max_tokens) │      │
│  │  2. create_agents(llm) → single agent[ index ]                    │      │
│  │  3. Task(description with {direction}, expected_output, agent)    │      │
│  │  4. Crew(agents=[one], tasks=[one], Process.sequential)           │      │
│  │  5. crew.kickoff(inputs={direction, ...})                         │      │
│  │  6. Emit "working" → "done" via progress_callback                 │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │                 HELPERS                                            │      │
│  │  _emit(cb, name, stage, output, step, extra)  — 标准事件发射       │      │
│  │  _run_single(agent, task, inputs, cb, name, step) → str           │      │
│  │  _safe_output(task) → str                   — 安全提取 task 输出   │      │
│  │  _parse_review_score(text) → (score, is_pass)                     │      │
│  │  _parse_planner_topics(text) → list[str]    — 提取选题标题         │      │
│  │  MAX_REVISION_ROUNDS = 2                                           │      │
│  └──────────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AGENT DEFINITIONS                                   │
│                            src/agents.py                                     │
│                                                                             │
│  create_agents(llm) → [strategist, planner, writer, reviewer]               │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  AGENT               ROLE              GOAL                          │  │
│  │  ─────────────────────────────────────────────────────────────────── │  │
│  │  🎯 strategist   内容策略分析师     生成博主画像卡                    │  │
│  │                    (10年MCN经验)     受众+调性+竞争力+方向             │  │
│  │                                                                       │  │
│  │  🔥 planner      爆款选题策划师     策划3个爆款选题                   │  │
│  │                    (100+百万播放)    标题+角度+爆点分析                │  │
│  │                                                                       │  │
│  │  ✍️ writer       短视频脚本写手     撰写完整拍摄脚本                   │  │
│  │                    (文字驱动画面)    钩子+分镜+结尾+标题               │  │
│  │                                                                       │  │
│  │  🔍 reviewer     内容质量审核员     5维评分审核脚本                   │  │
│  │                    (严格不防水)      钩子/节奏/情绪/转化/人设          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  All agents: allow_delegation=False, verbose=True                           │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          TASK DEFINITIONS                                    │
│                            src/tasks.py                                      │
│                                                                             │
│  create_tasks(agents) → [task_0, task_1, task_2, task_3]                   │
│  create_revision_tasks(writer, reviewer) → [revise_write, revise_review]   │
│                                                                             │
│  Tasks use {placeholder} templates:                                         │
│    {user_input} {strategist_output} {selected_topic} {writer_output}        │
│    (step-by-step mode also uses {direction})                                │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CONFIGURATION                                       │
│                            src/config.py                                     │
│                                                                             │
│  .env ──▶ load_dotenv() ──▶ LLM_CONFIG ──▶ load_config() → dict            │
│                                      │                                       │
│                        ┌─────────────┴─────────────┐                        │
│                        │  model:  "deepseek-chat"  │                        │
│                        │  temperature:  0.7        │                        │
│                        │  max_tokens:   2000       │                        │
│                        └───────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL API                                        │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │                    DeepSeek API                                │          │
│  │  https://api.deepseek.com/v1/chat/completions                 │          │
│  │                                                               │          │
│  │  ← deepseek-chat (via LiteLLM adapter in CrewAI LLM class)   │          │
│  └──────────────────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 数据流

### 逐步工作流 (Step-by-Step)

```
用户输入 → [选择模板] → 点击"开始创作"
  │
  ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: STRATEGIST                                               │
│  前端: showDirectionUI('strategist')                              │
│        → 5个方向芯片 (情感共鸣/知识干货/...)                       │
│        → 用户选择 → 点击"确认"                                    │
│        → runStepSSE('strategist', direction)                      │
│        → POST /api/run-step {step:"strategist", direction, ...}   │
│        → SSE: working → done → complete                           │
│        → 卡片展开显示输出                                         │
│        → auto-advance → advanceToStep('planner')                 │
└──────────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: PLANNER                                                  │
│  前端: showDirectionUI('planner')                                 │
│        → 5个方向芯片 (热点借势/痛点解决/...)                       │
│        → 用户选择 → 点击"确认"                                    │
│        → runStepSSE('planner', direction)                         │
│        → POST /api/run-step {step:"planner", direction,           │
│                              strategist_output, ...}              │
│        → SSE: working → done (with topics[] event) → complete     │
│        → 卡片展开 + 选题列表                                      │
│        → auto-advance → advanceToStep('writer')                  │
└──────────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 3: WRITER                                                   │
│  前端: showDirectionUI('writer') → topic chips from planner       │
│        → 用户选择选题 → 点击"确认"                                 │
│        → runStepSSE('writer', topic)                              │
│        → POST /api/run-step {step:"writer", selected_topic, ...}  │
│        → SSE: working → done → complete                           │
│        → 卡片展开显示完整脚本                                     │
│        → auto-advance → advanceToStep('reviewer')                │
└──────────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 4: REVIEWER (自动执行)                                      │
│        → runStepSSE('reviewer', '') — 无需用户选择               │
│        → POST /api/run-step {step:"reviewer", writer_output, ...} │
│        → SSE: working → done → complete                           │
│        → 显示评分 + PASS/REVISE                                   │
│        → auto-advance → finishWorkflow()                         │
└──────────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────────┐
│ FINISH: final card "✅ 全部完成 — 最终脚本"                       │
│   + 历史记录保存到 localStorage                                   │
│   + 按钮恢复可用                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### SSE 事件协议

```
event: data: {"agent":"🎯 内容策略分析师","stage":"working","output":"","step":1}
event: data: {"agent":"🎯 内容策略分析师","stage":"done","output":"...","step":1,"elapsed_ms":3421}
event: data: {"agent":"","stage":"complete","output":"","step":-1}
```

| stage | 含义 |
|---|---|
| `working` | Agent 开始工作，前端显示加载动画 |
| `done` | Agent 完成，前端展示输出内容 |
| `topics` | Planner 专属：携带提取的选题列表 |
| `complete` | 单步完成，触发 auto-advance |
| `pass` | Reviewer 通过 (score ≥ 7) |
| `revising` | 修改轮次中 |
| `final` | 全流程结束 |
| `error` | 异常终止 |

## 文件结构

```
agaent/
├── .env                        # API Key (gitignored)
├── .env.example                # API Key 模板
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口 + SSE 端点
│   ├── crew.py                 # Crew 编排 + 步进函数 + 辅助函数
│   ├── agents.py               # Agent 定义 (4 个 Agent)
│   ├── tasks.py                # Task 定义 + 修改任务对
│   └── config.py               # LLM 配置加载
├── static/
│   └── index.html              # 单页前端 (~1400 行 HTML/CSS/JS)
├── tests/
│   ├── __init__.py
│   ├── test_agents.py          # Agent 创建测试
│   ├── test_tasks.py           # Task 创建测试
│   ├── test_config.py          # 配置加载测试
│   ├── test_crew.py            # Crew 编排函数测试
│   └── test_e2e.py             # 端到端集成测试
├── TECH_STACK.md               # 技术栈文档 (本文件)
└── ARCHITECTURE.md             # 架构文档
```

## 关键设计决策

1. **无状态 API**：后端不在内存中保存中间结果，前端在每个 step 请求中携带之前全部输出 (`strategist_output`, `planner_output` 等)，服务可随时重启而不丢失状态。

2. **线程安全的 SSE**：CrewAI 在 `daemon=True` 的后台线程中运行，通过 `asyncio.Queue` + `loop.call_soon_threadsafe` 将事件推送到异步事件循环，避免阻塞。

3. **单 Agent Crew**：步进模式下每个 step 创建独立的 `Crew(agents=[one], tasks=[one])`，而非复用。这保证了每次调用的隔离性和方向参数的正确注入。

4. **前端状态机**：`currentStep` + `workflowActive` + `currentSignal` 三个变量管理逐步工作流状态，`AbortController` 支持中途停止。

5. **毛玻璃设计语言**：全界面使用 `backdrop-filter: blur()` + 半透明背景 + CSS 自定义属性实现亮/暗双主题，零外部 UI 库依赖。
