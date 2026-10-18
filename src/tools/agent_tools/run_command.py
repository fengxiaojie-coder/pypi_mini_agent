#un_command.py
import subprocess
import re

TOOL_SCHEMA = {
    "type" : "function",
    "name" : "run_command",
    "description" : "通过该工具，在当前目录运行命令",
    "parameters" :  {
        "type" : "object",
        "properties" : {
            "command" : {
                "type":"string",
                "description": """在 Windows cmd.exe 中执行命令。
                可用命令:dir, cd, type, echo, ...
                不要用 ls、pwd、cat 等 Linux 命令，
                也不要用 PowerShell cmdlet。"""
            }
        },
        "required" : ["command"]
    }
}

ALLOWED_COMMANDS = {
    # 目录 / 路径
    "dir",
    "cd",
    "chdir",
    "tree",
    "where",

    # 文件内容 / 操作
    "type",
    "copy",
    "move",
    "del",
    "ren",
    "mkdir",
    "md",
    "rd",
    "rmdir",

    # 输出
    "echo",
    "set",

    # 信息查询
    "ver",
    "whoami",
    "hostname",
    "systeminfo",
    "tasklist",

    # 其他常用
    "find",
    "findstr",
    "more",
    "cls",
    "python",
    "python3",
    "py",
    "pytest",
    "git",
}

def run_command(command:str) -> str:
    cmd_name = re.match(r"[\w-]+", command.strip()).group() if command.strip() else ""
    print(f"正在尝试执行命令{command}")
    if cmd_name not in ALLOWED_COMMANDS:
        return f"该命令不可执行：{command}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout or result.stderr or "命令执行成功，但无输出"
    except Exception as e:
        return f"命令执行错误：{e}"