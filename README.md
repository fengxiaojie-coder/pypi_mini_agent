# pypi_mini_agent

仿照 B站UP主 小单说AI [TheSyart/claude-agent-examples](https://github.com/TheSyart/claude-agent-examples) 用 Python 手写一个 mini agent。

## 环境准备

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

## 项目运行

```bash
conda activate pypi
python agent_main.py
```

## 已完成功能

### 基本 agent 功能

- Responses API 多轮对话
- 工具调用循环
- 本地 history 维护
- 推理过程收集与打印
- history.jsonl 原始对话流水
- 跨会话恢复历史（`load_as_context`）
- history 压缩（`/compact` 手动、`exit` 自动）

### 工具

1. **执行 cmd 命令** —— `run_command`
2. **读取文件** —— `read_file`
3. **写入文件** —— `write_file`（覆盖前自动备份 `.bak`，原子写）
4. **精确编辑文件** —— `edit_file`（`old_string` → `new_string`，要求唯一匹配）
5. **查询天气** —— `get_weather`
6. **抓取网页** —— `fetch_webpage`
7. **获取当前时间** —— `get_current_time`
8. **网页搜索** —— `web_search`（博查 Web Search API）
9. **保存记忆** —— `save_memory`（写入 `MEMORY.md` / `USER.md`）
10. **任务规划** —— `update_todos`（todolist，逐步推进状态）
11. **网页调研子代理** —— `webpage_subagent`（独立上下文，搜索+抓取+整理）

### 记忆系统

| 文件 | 作用 |
|---|---|
| `memory/history.jsonl` | 原始对话流水 |
| `memory/MEMORY.md` | 长期核心记忆 |
| `memory/USER.md` | 用户画像和稳定偏好 |

- `MEMORY.md` / `USER.md` 每轮拼进 `instructions`，跨会话生效
- `save_memory` 工具让 agent 自己写长期记忆（`type=user` / `type=memory`，按 section 插入、去重、带日期）
- 手动编辑 md 也生效，最可靠

### 任务规划（todolist）

- `update_todos` 工具：模型传完整列表（全量覆盖），状态 `pending` / `in_progress` / `completed`
- 同一时间只允许一个 `in_progress`，多个会报错
- 任务列表每轮注入 `instructions`，模型能看到当前进度
- `PROMPT_SETTING` 里规定：3 步以上任务先建列表，逐步推进状态
- 任务全部完成或达到 `MAX_CONTINUE` 上限时 `clear_todos()`，不跨对话污染

### 子代理（webpage_subagent）

- **独立上下文**：子代理有自己的 `history`，中间调了什么工具、抓了多少页面，主 agent 看不到，只收最终摘要
- **工具权限最小化**：子代理只拿到 `web_search` 和 `fetch_webpage` 两个工具，不能 `run_command`、`write_file`、不能递归派子代理
- **Prompt 写死**：子代理是“网页调研助手”，规则固定（最多抓 3 个页面、整理成 关键事实/来源链接/不确定的地方）
- **轮数上限**：`MAX_ROUNDS = 5`，防止子代理无限循环
- **失败兜底**：子代理超轮失败时，主 agent 可以自己补做（代价是中间过程进主 history）
- **适用场景**：多网页调研、多来源对比、需要整理成结构化摘要。简单搜索直接用 `web_search`，不要走子代理

## 下一步

### 工具健壮性

- `run_command` 白名单拆分校验（防 `&&` / `|` 绕过），非字母开头命令防崩溃

### 子代理完善

- 子代理失败时的重试/降级策略