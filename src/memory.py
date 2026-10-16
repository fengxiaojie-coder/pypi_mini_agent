#memory.py
import json
import os
from datetime import datetime
from pathlib import Path


# 获取memory目录
PROJECT_ROOT = Path(__file__).parent.parent
MEMORY_DIR = PROJECT_ROOT / "memory"
HISTORY_FILE = MEMORY_DIR / "history.jsonl"

class MemoryManager:
    def __init__(self, history_file: Path = HISTORY_FILE):
        self.history_file = history_file
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

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
        for r in records:
            role = r.get("role")

            if role in ("user", "assistant"):
                api_input.append({
                    "role": role,
                    "content": r.get("content", ""),
                })

            elif role == "tool_call":
                api_input.append({
                    "type": "function_call",
                    "name": r.get("tool_name"),
                    "arguments": r.get("arguments"),
                    "call_id": r.get("call_id"),
                })

            elif role == "tool_result":
                api_input.append({
                    "type": "function_call_output",
                    "call_id": r.get("call_id"),
                    "output": r.get("content", ""),
                })

        return api_input