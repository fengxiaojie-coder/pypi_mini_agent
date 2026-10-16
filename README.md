# pypi_mini_agent

仿照 B站UP主 小单说AI [TheSyart/claude-agent-examples](https://github.com/TheSyart/claude-agent-examples) 用 Python 手写一个 mini agent。

## 已完成功能

### 基本 agent 功能

- Responses API 多轮对话
- 工具调用循环
- 本地 history 维护
- 推理过程收集与打印
- history.jsonl 原始对话流水

### 工具

1. **执行 cmd 命令** —— `run_command`
2. **读取文件** —— `read_file`
3. **写入文件** —— `write_file`
4. **查询天气** —— `get_weather`

## 下一步

### 记忆系统管理

对应参考项目 `step07_memory_system.py`。

| 文件 | 作用 |
|---|---|
| `memory/YYYY-MM-DD.md` | 情景记忆 |
| `memory/MEMORY.md` | 长期核心记忆，每轮注入 prompt |
| `templates/USER.md` | 用户画像和稳定偏好 |
| `templates/agent/compact_prompt.md` | 压缩旧对话的提示词模板 |

代码只在文件缺失时创建默认内容，不覆盖已有记忆。