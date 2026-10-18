# update_todos.py

TODOS: list[dict] = []
VALID_STATUS = {"pending", "in_progress", "completed"}
STATUS_ICON = {"pending": "[ ]", "in_progress": "[~]", "completed": "[x]"}


TOOL_SCHEMA = {
    "type": "function",
    "name": "update_todos",
    "description": (
        "创建或更新当前任务的 todolist。"
        "传入完整 todos 数组（全量覆盖，不是增量修改）。"
        "多步骤任务先拆解成清晰列表，执行中推进状态："
        "开始某步前改为 in_progress，完成后改为 completed。"
        "同一时间至多一个 in_progress。"
        "简单问答（单步）不必用本工具。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "todos": {
                "type": "array",
                "description": "完整的 todo 列表，按执行顺序排列",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "序号，从 1 开始",
                        },
                        "content": {
                            "type": "string",
                            "description": "这一步要做什么",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed"],
                            "description": "任务状态",
                        },
                    },
                    "required": ["id", "content", "status"],
                },
            },
        },
        "required": ["todos"],
    },
}


def render_todos(todos: list) -> str:
    """把任务列表格式化成文本"""
    if not todos:
        return "(当前无待办事项)"
    lines = []
    for t in todos:
        icon = STATUS_ICON.get(t.get("status", "pending"), "[?]")
        lines.append(f"  {icon} {t.get('id')}. {t.get('content', '')}")
    return "\n".join(lines)


def update_todos(todos: list) -> str:
    """更新任务列表，返回格式化文本"""
    global TODOS

    cleaned = []
    for i, t in enumerate(todos, start=1):
        content = (t.get("content") or "").strip()
        if not content:
            continue
        status = t.get("status", "pending")
        if status not in VALID_STATUS:
            status = "pending"
        cleaned.append({
            "id": t.get("id", i),
            "content": content,
            "status": status,
        })

    in_progress = [t for t in cleaned if t["status"] == "in_progress"]
    if len(in_progress) > 1:
        return "错误：同一时间只能有一个 in_progress 任务，请重新规划。"

    TODOS = cleaned
    done = sum(1 for t in TODOS if t["status"] == "completed")
    return (
        f"todos 已更新：总 {len(TODOS)} 条，"
        f"完成 {done}，进行中 {len(in_progress)}\n\n"
        f"{render_todos(TODOS)}"
    )


def get_todos() -> list:
    """供 agent_loop 读取当前任务列表"""
    return TODOS


def clear_todos():
    """清空任务列表"""
    global TODOS
    TODOS = []