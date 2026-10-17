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
3. **写入文件** —— `write_file`
4. **精确编辑文件** —— `edit_file`（`old_string` → `new_string`）
5. **查询天气** —— `get_weather`
6. **抓取网页** —— `fetch_webpage`
7. **获取当前时间** —— `get_current_time`
8. **网页搜索** —— `web_search`（博查 Web Search API）
9. **保存记忆** —— `save_memory`（写入 `MEMORY.md` / `USER.md`）

### 记忆系统

| 文件 | 作用 |
|---|---|
| `memory/history.jsonl` | 原始对话流水 |
| `memory/MEMORY.md` | 长期核心记忆 |
| `memory/USER.md` | 用户画像和稳定偏好 |

- `MEMORY.md` / `USER.md` 每轮拼进 `instructions`，跨会话生效
- `save_memory` 工具让 agent 自己写长期记忆（`type=user` / `type=memory`，按 section 插入、去重、带日期）
- 手动编辑 md 也生效，最可靠

## 下一步

agent的任务规划