#agent_loop.py
import os
import json
from openai import OpenAI
from src.tools.agent_tools import TOOL_SCHEMAS, TOOL_REGISTRY
from src.memory.memory_manager import MemoryManager
from src.memory.history_compact import compact_jsonl
from src.tools.agent_tools.update_todos import get_todos, update_todos, render_todos, clear_todos

PROMPT_SETTING = """
宁城北来应渐雪，你是宁北雪,我的agent编程助手。
我需要你调用工具来解决实际问题。
使用中文回复。
调用工具时，参数必须是合法的 JSON 对象，不要输出 XML 标签。
回复时参考下方的「长期记忆」「用户画像」「当前任务」。

【任务规划规则】
1. 需要多个步骤才能完成的任务（3 步以上），先调 update_todos 拆成清晰列表。
2. 执行时按顺序推进：开始某步前改为 in_progress，完成后改为 completed，再开始下一项。
3. 同一时间只允许一个 in_progress。
4. 简单问答（单步）不必建 todolist。
"""

def agent_loop():
    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
    )
    memory_manager = MemoryManager()

    history = memory_manager.load_as_context(limit=20) # 回复会话

    if history:
        print(f"[已恢复 {len(history)} 条历史]")

    while True:
        user_input = input("你:")
        if user_input == "exit":
            print("退出 agent_loop")
            print("[开始压缩历史记录]")
            summary = compact_jsonl(memory_manager, client, keep_recent=10)
            if summary:
                print("[历史记录已压缩]")
                print("【压缩摘要】")
                print(summary)
            else:
                print("[无需压缩历史记录]")
            break
        elif user_input == "/compact":
            print("[开始压缩历史记录]")
            summary = compact_jsonl(memory_manager, client, keep_recent=10)
            if summary:
                print("[历史记录已压缩]")
                print("【压缩摘要】")
                print(summary)
                history = memory_manager.load_as_context(limit=20) # 回复会话
                print(f"[已重载 {len(history)} 条历史]")
            else:
                print("[无需压缩历史记录]")
            continue

        elif user_input == "clear":
            print("[清空历史记录]")
            memory_manager.clear_history()
            history = []
            continue

        history.append({"role":"user", "content":user_input})
        memory_manager.save_user_message(user_input)

        answer = None
        response = client.responses.create(
            model="deepseek-flash",
            # model="deepseek-v4-pro", #怎么半天就没钱了，😭
            max_output_tokens=8000,
            instructions = build_instructions(memory_manager),
            tools=TOOL_SCHEMAS,
            input=history
        )

        print("【推理过程】")

        answer = tool_use(client, memory_manager, history, response)

        # 遍历输出项
        for item in answer.output:
            if item.type == "message":
                # 打印最终答案
                print("【最终答案】")
                print(item.content[0].text)

def tool_use(client, memory_manager, history, response):
    """
    处理工具调用的循环，直到模型不再调用工具为止。
    """
    todo_max_continue = 10  # 最大连续工具调用次数，防止无限循环
    todo_continue_count = 0

    while True:
        for item in response.output:
            if item.type == "reasoning":
                for s in item.summary:
                    print(s.text[:500])
                for c in getattr(item, "content", []) or []:
                    if getattr(c, "type", None) == "reasoning_text":
                        print(c.text[:500])

        function_calls = [item for item in response.output if item.type == "function_call"]

        if not function_calls:
            answer = response
            text = response.output_text or ""
            if text:
                history.append({"role": "assistant", "content": text})
                memory_manager.save_assistant_message(text)

            todos = get_todos()
            unfinished = [t for t in todos if t["status"] != "completed"]
            if unfinished and todo_continue_count < todo_max_continue:
                todo_continue_count += 1
                print(f"\n[计划未完成，继续执行 ({todo_continue_count}/{todo_max_continue})]")
                print(render_todos(todos))
                print()

                reminder = {
                    "role": "user",
                    "content": (
                        "任务尚未完成，以下项仍未办妥，请继续执行并按规则更新 todolist：\n"
                        + render_todos(todos)
                    ),
                }
                history.append(reminder)
                memory_manager.save_user_message(reminder["content"])

                response = client.responses.create(
                    model="deepseek-flash",
                    max_output_tokens=8000,
                    instructions=build_instructions(memory_manager),
                    tools=TOOL_SCHEMAS,
                    input=history,
                )
                continue

            # 全部完成或达到上限
            if todos:
                if unfinished:
                    print(f"\n[达到最大续跑次数 {todo_max_continue}，停止]")
                else:
                    print("\n[计划全部完成]")
                print(render_todos(todos))
                print()
                clear_todos()

            answer = response
            break

        tool_outputs = []
        for call in function_calls:
            try:
                tool = TOOL_REGISTRY.get(call.name)
                if tool is None:
                    result = f"当前agent不存在此工具{call.name}"
                else:
                    args = json.loads(call.arguments)
                    result = str(tool(**args))      # ← 按 schema 解包
            except Exception as e:
                result = f"工具执行失败：{type(e).__name__}: {e}"

            tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": result,
                })
            memory_manager.save_tool_call(call.name, call.arguments, call.call_id)
            memory_manager.save_tool_output(call.name, result, call.call_id)

            #history 记录工具调用
        for item in response.output:
            if item.type == "function_call":
                history.append({
                        "type": "function_call",
                        "name": item.name,
                        "arguments": item.arguments,
                        "call_id": item.call_id,
                    })
            elif item.type == "message":
                text = "".join(
                        c.text for c in item.content
                        if getattr(c, "type", None) == "output_text"
                    )
                if text:
                    history.append({
                            "role": "assistant",
                            "content": text,
                        })
        for out in tool_outputs:
            history.append({
                    "type": "function_call_output",
                    "call_id": out["call_id"],
                    "output": out["output"],
                })

        response = client.responses.create(
                model="deepseek-flash",
                max_output_tokens=8000,
                instructions = build_instructions(memory_manager),
                tools=TOOL_SCHEMAS,
                input=history,
            )
    return answer

def build_instructions(memory_manager) -> str:
    """
        构建给模型的 instructions，包含基础设置、长期记忆和用户画像。
    """
    parts = [PROMPT_SETTING]

    memory = memory_manager.load_memory_md().strip()
    user = memory_manager.load_user_md().strip()

    if memory:
        parts.append(f"\n## 长期记忆\n{memory}")
    if user:
        parts.append(f"\n## 用户画像\n{user}")

    todos = get_todos()
    if todos:
        todos_text = render_todos(todos)
        parts.append(f"\n## 当前任务清单\n{todos_text}")

    return "\n".join(parts)