# write_file.py
import os
import shutil
import tempfile

TOOL_SCHEMA = {
    "type": "function",
    "name": "write_file",
    "description": (
        "写入文本内容到文件。如果文件不存在则创建，存在则覆盖（或追加）。"
        "自动使用 UTF-8 编码。"
        "覆盖已有文件时会自动备份到 .bak。"
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

    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
    except Exception as e:
        return f"错误：创建目录失败 {type(e).__name__}: {e}"

    # 追加模式：直接在原文件末尾追加，无需备份/原子写
    if append:
        try:
            need_newline = False
            if os.path.exists(path) and os.path.getsize(path) > 0:
                with open(path, "rb") as f:
                    f.seek(-1, os.SEEK_END)
                    need_newline = f.read(1) != b"\n"

            with open(path, "a", encoding="utf-8", newline="") as f:
                if need_newline:
                    f.write("\n")
                f.write(content)

            return f"成功：追加 {len(content)} 字符到 {path}"
        except Exception as e:
            return f"错误：追加失败 {type(e).__name__}: {e}"

    # 覆盖模式：先备份旧文件，再原子写新内容
    backup_note = ""
    if os.path.exists(path):
        backup = path + ".bak"
        try:
            shutil.copy2(path, backup)
            backup_note = f"，已备份到 {backup}"
        except Exception as e:
            return f"错误：备份失败，已中止写入 {type(e).__name__}: {e}"

    # 原子写：写临时文件 → os.replace 替换
    tmp_fd = None
    tmp_path = None
    try:
        parent = os.path.dirname(path) or "."
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=parent, prefix=".write_", suffix=".tmp"
        )
        with os.fdopen(tmp_fd, "w", encoding="utf-8", newline="") as f:
            tmp_fd = None          # fdopen 接管后，异常时不再手动 close
            f.write(content)

        os.replace(tmp_path, path)
        tmp_path = None            # replace 成功后，临时文件已不存在

        return f"成功：写入 {len(content)} 字符到 {path}{backup_note}"
    except Exception as e:
        return f"错误：写入失败 {type(e).__name__}: {e}{backup_note}"
    finally:
        # 清理残留临时文件
        if tmp_fd is not None:
            try:
                os.close(tmp_fd)
            except OSError:
                pass
        if tmp_path is not None and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass