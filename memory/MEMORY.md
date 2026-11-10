# 项目记忆

## 项目

- [2026-10-17] 项目目标：做出一个完整的 agent 系统，主要诉求是"炫技"（展示技术亮点），运行环境 Python 3.12 + conda env pypi
- 项目名 `pypi_mini_agent`，定位：参照 B站UP主「小单说AI」的 `TheSyart/claude-agent-examples`，用 Python **手写**一个 mini agent，不依赖 LangChain / LlamaIndex 等框架（核心循环自己实现，方便展示原理）
- [2026-10-20] 架构双层：①终端 REPL（`python agent_main.py`）②Web 版（FastAPI WebSocket 后端 + Vue 3 前端），共用同一套 `src/agent_loop.py`

## 技术栈

- 后端：Python 3.12（`E:\anaconda\envs\pypi\python.exe`），OpenAI SDK（走 **DeepSeek** 的 Responses API 兼容层）、FastAPI + uvicorn、python-dotenv、chromadb
- 前端：Vue 3 + TypeScript + Vite + Pinia + vue-router，Node 18+（推荐 20+）
- 前端**不需要** conda 环境，在普通终端跑；后端需要 `conda activate pypi`

## 运行方式

- 后端：`uvicorn src.server.ws_server:app --reload --port 8000`
- 前端：`cd frontend && npm run dev`（http://localhost:5173）
- 终端版：`python agent_main.py`
- 需要开两个终端，前端终端不要 conda activate

## 环境约束（踩过的坑）

- [2026-10-20] 工具链里 `conda` 命令调不动（不在命令白名单），但 `run_command` 每次都是全新进程，不会保留 activate 状态 → **一律用绝对路径 `E:\anaconda\envs\pypi\python.exe` 调 python**
- `where python` 首位就是 pypi 环境，说明默认已在目标环境中
- 敏感信息放项目根目录 `.env`（`DEEPSEEK_API_KEY`、`BOCHA_API_KEY`），不进 git

## 代码结构

- `agent_main.py`：终端入口
- `src/agent_loop.py`：核心 agent 循环（多轮对话 + 工具调用循环 + 推理过程收集）
- `src/memory/`：`memory_manager.py`（读写 MEMORY.md/USER.md）、`history_compact.py`（history 压缩）、`memory_RAG.py`（RAG 记忆检索）
- `src/server/ws_server.py`：FastAPI WebSocket 服务
- `src/tools/agent_tools/`：11 个工具，一文件一工具 —— run_command / read_file / write_file / edit_file / get_weather / fetch_webpage / get_current_time / web_search / save_memory / update_todos / webpage_subagent
- `memory/`：`MEMORY.md`（长期记忆）、`USER.md`（用户画像）、`history.jsonl`（原始对话流水）、`date_memory/`
- `frontend/src/`：`views/ChatView.vue`（聊天页）、`stores/agent.ts`（WS 状态）、`router/`

## 技术决策

- [2026-10-20] 记忆三级：`history.jsonl` 原始流水 → history 压缩（`/compact` 手动 / `exit` 自动）→ `MEMORY.md` + `USER.md` 长期记忆，每轮拼进 `instructions`
- [2026-10-20] 子代理（`webpage_subagent`）设计原则：**独立上下文**（中间过程不进主 history，只回摘要）+ **权限最小化**（只给 web_search / fetch_webpage，不能 run_command、不能递归）+ `MAX_ROUNDS=5` + 失败可降级由主 agent 补做
- [2026-10-20] todolist 用「全量覆盖」语义（模型传完整列表），同一时刻只允许一个 `in_progress`，任务结束 `clear_todos()` 不跨对话污染
- `write_file` 覆盖前自动备份 `.bak` + 原子写；`edit_file` 用 old_string 唯一匹配防误改

## 已知待办

- `run_command` 白名单需拆分校验，防 `&&` / `|` 绕过；非字母开头命令要防崩
- 子代理失败的重试 / 降级策略
- 前端目前只有 ChatView，功能较薄
