TOOL_SCHEMA = {
    "type": "function",
    "name": "read_file",
    "description": (
        "读取文本文件内容。适用于查看源码、配置、文档等文本文件。"
        "自动检测编码（UTF-8/GBK），避免中文乱码。"
        "对于二进制文件（图片、exe 等）不适用。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "文件路径，可以是相对路径（相对当前工作目录）或绝对路径。",
            },
            "max_chars": {
                "type": "integer",
                "description": "最多返回的字符数，默认 10000。大文件会被截断。",
                "default": 10000,
            },
        },
        "required": ["path"],
    },
}

import os

def read_file(path: str, max_chars: int = 10000, encoding: str = "auto") -> str:
    """
    读取文本文件内容。

    Args:
        path: 文件路径（绝对或相对当前工作目录）
        max_chars: 最多返回字符数，防止超大文件撑爆上下文
        encoding: "auto" 自动检测 / "utf-8" / "gbk" 等
    """
    # 路径规范化
    path = os.path.abspath(os.path.expanduser(path))

    if not os.path.exists(path):
        return f"错误：文件不存在 {path}"
    if not os.path.isfile(path):
        return f"错误：不是文件 {path}"

    # 编码策略：UTF-8 → GBK → 带 replace 兜底
    encodings = (
        ["utf-8", "gbk", "gb18030", "latin-1"]
        if encoding == "auto"
        else [encoding]
    )

    content = None
    used_encoding = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                content = f.read()
            used_encoding = enc
            break
        except UnicodeDecodeError:
            continue
        except Exception as e:
            return f"错误：读取失败 {e}"

    if content is None:
        # 全都失败，用 replace 兜底
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        used_encoding = "utf-8 (replace)"

    # 截断
    truncated = len(content) > max_chars
    if truncated:
        content = content[:max_chars]

    header = f"[文件: {path} | 编码: {used_encoding}"
    if truncated:
        header += f" | 已截断至 {max_chars} 字符"
    header += "]\n"

    return header + content