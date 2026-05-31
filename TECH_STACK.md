# 技术栈总览 — 抖音博主创作助手

## 运行环境

| 层 | 技术 | 版本/说明 |
|---|---|---|
| 语言 | Python | 3.10+ |
| 包管理 | pip + venv | 虚拟环境隔离 |
| 运行时 | uvicorn | ASGI 服务器，端口 7861 |

## 后端框架

| 组件 | 库 | 用途 |
|---|---|---|
| Web 框架 | **FastAPI** | REST API + SSE 流式响应 |
| 数据校验 | **Pydantic** (BaseModel) | 请求体模型 (RunRequest / StepRequest) |
| 跨线程通信 | **asyncio.Queue** + `loop.call_soon_threadsafe` | 工作线程 → SSE 事件流 |
| 并发模型 | **threading.Thread** (daemon) | CrewAI 在后台线程执行，不阻塞事件循环 |

## AI Agent 框架

| 组件 | 库 | 说明 |
|---|---|---|
| Agent 编排 | **CrewAI 1.14.6** | Agent / Task / Crew / Process.sequential |
| LLM 适配 | **LiteLLM** (via `crewai.LLM`) | 统一接口调用 DeepSeek |
| 模型 | **DeepSeek Chat** (`deepseek-chat`) | 温度 0.7，最大 2000 tokens |
| Tracing 抑制 | `set_suppress_tracing_messages(True)` | 禁用首次运行的交互式提示 |

## 前端

| 层 | 技术 | 说明 |
|---|---|---|
| 页面 | 纯 **HTML5** 单页 (SPA) | `static/index.html`，~1400 行 |
| 样式 | 纯 **CSS3** (无框架) | CSS 自定义属性、暗色/亮色主题、Glassmorphism 毛玻璃 |
| 脚本 | 原生 **JavaScript** (ES6+) | Fetch API + SSE (EventSource 替代：手动 ReadableStream 解析) |
| 图标 | **Emoji** | 纯文本图标，零依赖 |
| 字体 | Georgia / system-ui / PingFang SC | 系统字体栈 |

## 存储与配置

| 组件 | 方案 | 说明 |
|---|---|---|
| 环境变量 | **python-dotenv** → `.env` | `DEEPSEEK_API_KEY` |
| 前端持久化 | **localStorage** | 历史记录 (最多10条)、面板宽度 |
| 配置中心 | `src/config.py` → `LLM_CONFIG` 字典 | model / temperature / max_tokens |

## 测试

| 组件 | 库 | 文件 |
|---|---|---|
| 测试框架 | **pytest** | `tests/` (23 个用例) |
| 覆盖范围 | 单元 + 集成 + E2E | test_agents / test_tasks / test_config / test_crew / test_e2e |

## 关键依赖

```
fastapi
uvicorn
crewai==1.14.6
pydantic
python-dotenv
pytest
```
