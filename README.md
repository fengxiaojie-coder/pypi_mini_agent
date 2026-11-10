# pypi_mini_agent 项目文档

## 一、项目介绍

这是一个从零手写的 AI Agent 项目，没有依赖 LangChain、AutoGPT 这类现成框架，所有核心组件（Agent 主循环、工具系统、记忆系统、任务规划、子代理）都是自己实现的。项目的目标不是封装一个生产级框架，而是把 Agent 的关键零件拆开，理解“一个能调用工具、记住用户、规划任务、派生子代理的 Agent 到底是怎么跑起来的”。

项目参考了 B 站 UP 主“小单说 AI”的 `claude-agent-examples` 教学项目，在此基础上做了工程化扩展：加了 Web 前端、子代理、记忆 RAG、todolist 自动续跑等能力，并针对 Windows 环境做了工具健壮性处理。

**技术栈**：Python 3.12、DeepSeek Responses API、FastAPI + WebSocket、Vue 3 + Pinia + TypeScript、ChromaDB、博查 Web Search API

**核心亮点**：

- **手写 Agent 循环**：不依赖框架，自己实现工具调用循环、history 管理、工具结果回填、推理过程收集
- **11 个工具**：命令执行、文件读写编辑、网页抓取、网页搜索、天气查询、记忆保存、任务规划、网页调研子代理
- **分层记忆系统**：`MEMORY.md` / `USER.md` 长期记忆 + `history.jsonl` 对话流水 + 记忆 RAG
- **记忆 RAG**：按 `- ` 列表项切块，Chroma 本地向量化；≤10 条全量注入，>10 条走向量检索 top-5；零额外 Key，懒加载单例，失败退回全量
- **任务规划**：`update_todos` 工具驱动，模型逐步推进状态，未完成时自动续跑，完成后清空
- **子代理**：`webpage_subagent` 独立上下文做多网页调研，工具权限最小化，主 agent 只收摘要
- **Web 可视化**：Vue 3 + FastAPI WebSocket，对话页 + 监控页，工具调用、todolist、子代理进度实时可见
- **工具健壮性**：`write_file` 备份 + 原子写、`edit_file` 唯一匹配、`read_file` 编码自动检测、`run_command` 白名单

## 二、环境准备

```bash
conda create -n pypi python=3.12
conda activate pypi
pip install -r requirements.txt
```

`.env` 文件（放在项目根目录，不要提交到 git）：

```
DEEPSEEK_API_KEY=sk-你的DeepSeekKey
BOCHA_API_KEY=sk-你的博查Key
```

首次运行前，预下载 Chroma 的 embedding 模型（避免首次对话卡住）：

```bash
python -c "from chromadb.utils import embedding_functions; embedding_functions.DefaultEmbeddingFunction()"
```

## 三、项目运行

### 终端版

```bash
conda activate pypi
python agent_main.py
```

### Web 版（需要开两个终端）

**终端 1（后端）**：

```bash
conda activate pypi
uvicorn src.server.ws_server:app --reload --port 8000
```

**终端 2（前端，不需要 conda）**：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:5173/chat`。

## 四、已完成功能

### 4.1 基本 agent 功能

- Responses API 多轮对话
- 工具调用循环
- 本地 history 维护
- 推理过程收集与打印
- history.jsonl 原始对话流水
- 跨会话恢复历史（`load_as_context`）
- history 压缩（`/compact` 手动、`exit` 自动）

### 4.2 工具（11 个）

1. **执行 cmd 命令** —— `run_command`
2. **读取文件** —— `read_file`（自动检测编码）
3. **写入文件** —— `write_file`（覆盖前自动备份 `.bak`，原子写）
4. **精确编辑文件** —— `edit_file`（`old_string` → `new_string`，要求唯一匹配）
5. **查询天气** —— `get_weather`
6. **抓取网页** —— `fetch_webpage`
7. **获取当前时间** —— `get_current_time`
8. **网页搜索** —— `web_search`（博查 Web Search API）
9. **保存记忆** —— `save_memory`（写入 `MEMORY.md` / `USER.md`）
10. **任务规划** —— `update_todos`（todolist，逐步推进状态）
11. **网页调研子代理** —— `webpage_subagent`（独立上下文，搜索+抓取+整理）

### 4.3 记忆系统

| 文件 | 作用 |
|---|---|
| `memory/history.jsonl` | 原始对话流水 |
| `memory/MEMORY.md` | 长期核心记忆 |
| `memory/USER.md` | 用户画像和稳定偏好 |

- `save_memory` 工具让 agent 自己写长期记忆（按 section 插入、去重、带日期）
- 手动编辑 md 也生效，最可靠

### 4.4 记忆 RAG（分层注入）

- **小量全量，大量检索**：记忆条数 ≤ 10 时，`MEMORY.md` / `USER.md` 全量拼进 `instructions`；超过 10 条时，走 Chroma 向量检索，只注入 top-5 相关片段
- **切块策略**：按 `- ` 列表项切，每条记忆一个 chunk，带 `##` 章节名（如 `[饮食偏好] 喜欢吃西瓜`）
- **零额外 Key**：用 Chroma 自带的本地 embedding（`all-MiniLM-L6-v2`），不依赖 OpenAI 或其他 embedding API
- **懒加载单例**：`MemoryRAG` 第一次走 RAG 分支时才创建，5 条记忆时完全不碰 Chroma，启动不卡
- **失败兜底**：RAG 创建或检索失败时，`try/except` 退回全量注入，不让对话崩
- **设计取舍**：不是无脑上 RAG——记忆量小时全量注入更稳，避免 RAG 漏掉相关记忆；记忆增长后才切向量检索，控制 token 成本

### 4.5 任务规划（todolist）

- `update_todos` 工具：模型传完整列表（全量覆盖），状态 `pending` / `in_progress` / `completed`
- 同一时间只允许一个 `in_progress`
- 任务列表每轮注入 `instructions`，模型能看到当前进度
- 3 步以上任务先建列表，逐步推进，完成后 `clear_todos()`
- 未完成时自动续跑，`MAX_CONTINUE` 防死循环

### 4.6 子代理（webpage_subagent）

- **独立上下文**：子代理有自己的 `history`，中间过程主 agent 看不到，只收最终摘要
- **工具权限最小化**：只给 `web_search` 和 `fetch_webpage`，不能 `run_command`、`write_file`、不能递归派子代理
- **Prompt 写死**：网页调研助手，最多抓 3 个页面，整理成结构化摘要
- **轮数上限**：`MAX_ROUNDS = 5`
- **失败兜底**：超轮失败时主 agent 可自己补做
- **适用场景**：多网页调研、多来源对比；简单搜索直接用 `web_search`

### 4.7 Web 可视化

- Vue 3 + Pinia + TypeScript 前端，FastAPI + WebSocket 后端
- 对话页 + 监控页，工具调用、todolist、子代理进度实时推送
- 每个 WebSocket 连接一个独立 `AgentSession`，多标签页互不干扰

## 五、下一步

### 5.1 工具健壮性

- `run_command` 白名单拆分校验（防 `&&` / `|` 绕过），非字母开头命令防崩溃

### 5.2 子代理完善

- 子代理失败时的重试/降级策略

### 5.3 RAG 扩展

- `read_paper` 工具（PDF 解析 + BM25 检索），和 Memory RAG 分工：Memory 管长期状态，RAG 管单次任务的文档知识