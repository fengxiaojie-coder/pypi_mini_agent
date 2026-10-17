# src/tools/edit_file.py
"""编辑文本文件：把 old_string 替换成 new_string"""

import os
import shutil

TOOL_SCHEMA = {
    "type": "function",
    "name": "edit_file",
    "description": (
        "编辑文本文件：把文件里的 old_string 精确替换成 new_string。"
        "old_string 必须在文件里唯一出现，否则报错，避免误改。"
        "用于精确修改源码、配置、文档等文本文件。"
        "二进制文件（图片、exe）不适用。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "文件路径，绝对或相对当前工作目录",
            },
            "old_string": {
                "type": "string",
                "description": (
                    "要被替换的原文，必须在文件里唯一出现。"
                    "包含足够上下文（前后几行），确保唯一。"
                ),
            },
            "new_string": {
                "type": "string",
                "description": "替换后的新文本",
            },
        },
        "required": ["path", "old_string", "new_string"],
    },
}


def edit_file(path: str, old_string: str, new_string: str) -> str:
    """
    把文件里的 old_string 替换成 new_string。

    Args:
        path: 文件路径
        old_string: 要被替换的原文，必须唯一
        new_string: 替换后的新文本

    Returns:
        操作结果信息
    """
    path = os.path.abspath(os.path.expanduser(path))

    if not os.path.exists(path):
        return f"错误：文件不存在 {path}"
    if not os.path.isfile(path):
        return f"错误：不是文件 {path}"

    # 读文件（自动检测编码）
    content, encoding = _read_with_encoding(path)
    if content is None:
        return f"错误：无法读取 {path}，编码检测失败"

    # 检查 old_string 存在且唯一
        # 检查 old_string 存在且唯一
    if old_string not in content:
        return f"错误：文件里找不到 old_string。请检查原文是否完全一致（包括空格、换行）。"

    count = content.count(old_string)
    if count > 1:
        # 列出所有出现行号
        positions = []
        idx = -1
        for _ in range(count):
            idx = content.find(old_string, idx + 1)
            line_no = content[:idx].count("\n") + 1
            positions.append(line_no)

        positions_str = "、".join(str(p) for p in positions)
        return (
            f"错误：old_string 出现 {count} 次（第 {positions_str} 行），不唯一。"
            f"请提供更多上下文（前后几行），确保唯一匹配。"
        )

    # 替换
    new_content = content.replace(old_string, new_string, 1)

    # 备份
    backup = path + ".bak"
    try:
        shutil.copy2(path, backup)
    except Exception as e:
        return f"错误：备份失败 {type(e).__name__}: {e}"

    # 写回（用检测到的编码）
    try:
        with open(path, "w", encoding=encoding) as f:
            f.write(new_content)
    except Exception as e:
        return f"错误：写入失败 {type(e).__name__}: {e}（备份在 {backup}）"

    return f"成功编辑 {path}（编码 {encoding}），已备份到 {backup}"


def _read_with_encoding(path: str) -> tuple[str | None, str]:
    """读文件，自动检测编码。返回 (内容, 编码)。"""
    for enc in ["utf-8", "gbk", "gb18030", "latin-1"]:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read(), enc
        except UnicodeDecodeError:
            continue
    return None, "utf-8"