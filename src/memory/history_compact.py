# history_compact.py

import json
from datetime import datetime

COMPACT_PROMPT = """
你是一个历史记录压缩助手，你的任务是将用户和助手之间的对话历史进行压缩，以便在不丢失关键信息的情况下减少占用的空间。
请遵循以下规则进行压缩：
1. 保留核心内容（用户说了什么、做了什么决策、有哪些待办）
2. 不要保留寒暄、重复内容、工具调用的技术细节
3. 输出纯文本，200 字以内
4. 不要输出 JSON，直接返回摘要文本
"""

def compact_jsonl(memory_manager, client, keep_recent: int = 10) -> str:
    """
    压缩 memory_manager.history_file：
    - 旧记录 → 一条 assistant 摘要（content 带 [此前对话摘要] 前缀）
    - 保留最近 keep_recent 条

    Args:
        memory_manager: MemoryManager 实例（提供 history_file）
        client: OpenAI client
        keep_recent: 保留最近 N 条

    Returns:
        摘要文本，失败或无需压缩返回 ""
    """
    history_file = memory_manager.history_file

    if not history_file.exists():
        return ""

    # 读全量
    records = []
    with open(history_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    if len(records) <= keep_recent:
        return ""

    old = records[:-keep_recent]
    recent = records[-keep_recent:]

    old_text = _to_text(old)
    if not old_text.strip():
        return ""

    # 调模型压缩
    try:
        resp = client.responses.create(
            model="deepseek-flash",
            max_output_tokens=500,
            instructions=COMPACT_PROMPT,
            input=old_text,
        )
        summary = resp.output_text.strip()
    except Exception as e:
        print(f"[compact_jsonl 失败] {e}")
        return ""

    # 重写
    with open(history_file, "w", encoding="utf-8") as f:
        summary_record = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "role": "assistant",
            "content": f"[此前对话摘要] {summary}",
            "covers": {
                "count": len(old),
                "from": old[0].get("timestamp") if old else None,
                "to": old[-1].get("timestamp") if old else None,
            },
        }
        f.write(json.dumps(summary_record, ensure_ascii=False) + "\n")
        for r in recent:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    return summary


def _to_text(records) -> str:
    """把 jsonl 记录转成文本（供压缩用）"""
    lines = []
    for r in records:
        role = r.get("role")
        content = r.get("content") or ""

        if role == "user":
            lines.append(f"用户: {content}")
        elif role == "assistant":
            lines.append(f"助手: {content}")
        elif role == "tool_call":
            lines.append(f"[调用工具 {r.get('tool_name')}，参数 {r.get('arguments')}]")
        elif role == "tool_result":
            lines.append(f"[工具返回: {content[:200]}]")
    return "\n".join(lines)