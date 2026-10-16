#agent_loop.py
import os
import json
from openai import OpenAI
from src.tools import TOOL_SCHEMAS, TOOL_REGISTRY
from src.memory import MemoryManager

PROMPT_SETTING = """
宁城北来应渐雪，你是宁北雪,我的agent编程助手。
我需要你调用工具来解决实际问题。
使用中文回复。
调用工具时，参数必须是合法的 JSON 对象，不要输出 XML 标签。
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
            break

        history.append({"role":"user", "content":user_input})
        memory_manager.save_user_message(user_input)

        answer = None
        response = client.responses.create(
            model="deepseek-flash",
            # model="deepseek-v4-pro", #怎么半天就没钱了，😭
            max_output_tokens=1000,
            instructions=PROMPT_SETTING,
            tools=TOOL_SCHEMAS,
            input=history
        )

        print("【推理过程】")

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
                    memory_manager.save_assistant_message(text)                                 # ← 新增
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
                model="deepseek-v4-pro",
                max_output_tokens=1000,
                instructions=PROMPT_SETTING,
                tools=TOOL_SCHEMAS,
                input=history,
            )

        # 遍历输出项
        for item in answer.output:
            if item.type == "message":
                # 打印最终答案
                print("【最终答案】")
                print(item.content[0].text)