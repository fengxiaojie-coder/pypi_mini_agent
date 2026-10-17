#memory.py
import json
import os
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
MEMORY_DIR = PROJECT_ROOT / "memory"
HISTORY_FILE = MEMORY_DIR / "history.jsonl"
MEMORY_MD = MEMORY_DIR / "MEMORY.md"
USER_MD = MEMORY_DIR / "USER.md"

DEFAULT_MEMORY = """# 长期记忆

## 项目

## 技术决策

## 踩过的坑

## 待办
"""

DEFAULT_USER = """# 用户画像

## 基本信息

## 偏好

## 技术栈
"""

class MemoryManager:
    def __init__(self, history_file: Path = HISTORY_FILE):
        self.history_file = history_file
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.memory_md = MEMORY_MD
        self.user_md = USER_MD
        self._ensure_file(self.memory_md, DEFAULT_MEMORY)
        self._ensure_file(self.user_md, DEFAULT_USER)

    def _ensure_file(self, path: Path, default: str):
        if not path.exists():
            path.write_text(default, encoding="utf-8")

    def save_message(self, role: str,  content: str, extra: dict = None):
        """
        保存消息到历史记录文件中。

        Args:
            role: 消息角色
            content: 消息内容
        """
        message = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
        }
        if extra:
            message.update(extra)
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(message, ensure_ascii=False) + "\n")

    def save_user_message(self, content: str):
        self.save_message("user", content)

    def save_assistant_message(self, content: str):
        self.save_message("assistant", content)

    def save_tool_call(self, tool_name: str, arguments: str, call_id: str):
        self.save_message("tool_call", "", extra={
            "tool_name": tool_name,
            "arguments": arguments,
            "call_id": call_id
        })

    def save_tool_output(self, tool_name: str, output: str, call_id: str):
        self.save_message("tool_result", output, extra={
            "tool_name": tool_name,
            "call_id": call_id
        })

    def load_memory_md(self) -> str:
        return self.memory_md.read_text(encoding="utf-8") if self.memory_md.exists() else ""

    def load_user_md(self) -> str:
        return self.user_md.read_text(encoding="utf-8") if self.user_md.exists() else ""

    def append_memory(self, text: str, section: str = None) -> str:
        return self._append_to_md(self.memory_md, text, section)

    def append_user_profile(self, text: str, section: str = None) -> str:
        return self._append_to_md(self.user_md, text, section)

    def _append_to_md(self, path: Path, text: str, section: str = None) -> str:
        content = path.read_text(encoding="utf-8")

        # 去重
        if text.strip() in content:
            return f"已存在：{text}"

        line = f"- [{datetime.now().strftime('%Y-%m-%d')}] {text}\n"

        if section:
            marker = f"## {section}"
            if marker in content:
                idx = content.index(marker) + len(marker)
                rest = content[idx:]
                next_h2 = rest.find("\n## ")
                if next_h2 == -1:
                    new_content = content.rstrip() + "\n" + line
                else:
                    insert_at = idx + next_h2
                    new_content = content[:insert_at] + "\n" + line + content[insert_at:]
            else:
                new_content = content.rstrip() + f"\n\n## {section}\n\n{line}"
        else:
            new_content = content.rstrip() + "\n" + line

        path.write_text(new_content, encoding="utf-8")
        return f"已保存：{text}"

    def load_history(self, limit: int = 20):
        """
        加载历史记录。

        Returns:
            List[dict]: 历史消息列表，每条消息为一个字典，包含 timestamp、role 和 content。
        """
        if not self.history_file.exists():
            return []

        record = []
        with open(self.history_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        message = json.loads(line)
                        record.append(message)
                    except json.JSONDecodeError:
                        continue
        return record[-limit:]

    def load_as_context(self, limit: int = 20):
        """
        加载最近的对话记录，转成 Responses API 的 input 格式。

        Args:
            limit: 最多加载最近 N 条

        Returns:
            list[dict]: 可直接作为 client.responses.create(input=...) 的参数
        """
        records = self.load_history(limit=limit)
        return self._to_api_format(records)

    def _to_api_format(self, records):
        """把 memory 记录转成 API input 格式"""
        api_input = []

        # tool_call和tool_result需要配对，确保顺序正确
        pending_calls = set()
        for r in records:
            role = r.get("role")

            if role in ("user", "assistant"):
                api_input.append({
                    "role": role,
                    "content": r.get("content", ""),
                })

            elif role == "tool_call":
                call_id = r.get("call_id")
                if not call_id:
                    continue
                pending_calls.add(r.get("call_id"))
                api_input.append({
                    "type": "function_call",
                    "name": r.get("tool_name"),
                    "arguments": r.get("arguments"),
                    "call_id": r.get("call_id"),
                })

            elif role == "tool_result":
                # 确保有对应的 tool_call
                call_id = r.get("call_id")
                if not call_id:
                    continue
                if call_id not in pending_calls:      # ← 孤立 output，跳过
                    continue
                pending_calls.discard(call_id)
                api_input.append({
                    "type": "function_call_output",
                    "call_id": r.get("call_id"),
                    "output": r.get("content", ""),
                })
        final = []
        for item in api_input:
            if item.get("type") == "function_call_output":
                # 如果前一个不是 tool_call，则跳过
                if not final or final[-1].get("type") != "function_call":
                    continue
            final.append(item)

        return final

    def clear_history(self):
        """清空历史记录文件"""
        if self.history_file.exists():
            self.history_file.unlink()