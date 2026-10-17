# src/tools/save_memory.py
"""保存长期记忆或用户画像"""

from src.memory.memory_manager import MemoryManager

_mm = MemoryManager()

TOOL_SCHEMA = {
    "type": "function",
    "name": "save_memory",
    "description": (
        "保存长期记忆或用户画像。"
        "当用户透露稳定信息时调用："
        "- type=user：用户偏好、身份、习惯（如'喜欢吃西瓜'）"
        "- type=memory：项目决策、技术约束、环境（如'项目用 conda'）"
        "不要保存临时信息（如'今天天气不错'）。"
        "写之前可先 read_file 读现有内容，避免重复。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["user", "memory"],
                "description": "user 用户相关 / memory 项目相关",
            },
            "text": {
                "type": "string",
                "description": "要保存的内容，一句话",
            },
            "section": {
                "type": "string",
                "description": "分组名，如 偏好、技术栈、项目、技术决策",
            },
        },
        "required": ["type", "text"],
    },
}


def save_memory(type: str, text: str, section: str = None) -> str:
    if type == "user":
        return _mm.append_user_profile(text, section)
    elif type == "memory":
        return _mm.append_memory(text, section)
    return f"错误：未知 type {type}"