# write_tool.py
import os

TOOL_SCHEMA = {
    "type": "function",
    "name": "write_file",
    "description": (
        "写入文本内容到文件。如果文件不存在则创建，存在则覆盖（或追加）。"
        "自动使用 UTF-8 编码。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "文件路径，可以是相对路径（相对当前工作目录）或绝对路径。",
            },
            "content": {
                "type": "string",
                "description": "要写入的文本内容。",
            },
            "append": {
                "type": "boolean",
                "description": "true 追加到文件末尾，false 覆盖。默认 false。",
                "default": False,
            },
        },
        "required": ["path", "content"],
    },
}


def write_file(path: str, content: str, append: bool = False) -> str:
    """
    写入文本到文件。

    Args:
        path: 文件路径
        content: 要写入的文本
        append: True 追加 / False 覆盖
    """
    path = os.path.abspath(os.path.expanduser(path))
    mode = "a" if append else "w"

    try:
        # 如果路径包含目录，自动创建
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(path, mode, encoding="utf-8") as f:
            f.write(content)

        action = "追加" if append else "写入"
        return f"成功：{action} {len(content)} 字符到 {path}"
    except Exception as e:
        return f"错误：写入失败 {type(e).__name__}: {e}"