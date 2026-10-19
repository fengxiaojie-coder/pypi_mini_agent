# src/tools/agent_tools/webpage_subagent.py
"""网页调研子代理：搜索 → 抓取 → 整理"""

import json
import os

from openai import OpenAI


TOOL_SCHEMA = {
    "type": "function",
    "name": "webpage_subagent",
    "description": (
        "派子代理做**多网页调研**：搜索多个关键词、抓取多个页面、对比整理。"
        "**只在以下场景使用**："
        "1. 需要对比多个来源的信息"
        "2. 单个网页内容不够，需要抓 2 个以上页面"
        "3. 需要从网页里提取事实并整理成结构化摘要"
        "**以下场景不要用**："
        "- 简单的单次搜索（直接用 web_search）"
        "- 抓一个已知 URL（直接用 fetch_webpage）"
        "一个子代理只调研一个维度。多维度调研请派多个子代理，不要把所有问题塞给一个。"
        "主 agent 只收到最终摘要，中间过程不污染当前对话。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "调研主题或问题，如'宁国苏果超市门店信息'",
            },
        },
        "required": ["query"],
    },
}


SUBAGENT_PROMPT = """你是一个网页调研助手。
你的任务：用 web_search 搜索关键词，用 fetch_webpage 抓取相关页面，整理出结构化信息。

规则：
1. 先搜索，看结果摘要，再决定抓哪几个页面（不要全抓，最多 3 个）
2. 每个页面 max_chars 控制在 3000，只抓关键部分
3. 整理成：关键事实 / 来源链接 / 不确定的地方
4. 不要编造，查不到就说查不到
5. 使用中文回复

完成后直接给出整理结果，不要寒暄。"""


SUBAGENT_TOOL_NAMES = {"web_search", "fetch_webpage"}
MAX_ROUNDS = 10
MAX_OUTPUT_TOKENS = 4000


def webpage_subagent(query: str) -> str:
    task = (
        f"请调研以下主题，用 web_search 搜索、用 fetch_webpage 抓取相关页面，"
        f"整理成结构化信息：\n\n{query}"
    )
    return _run_subagent(task)


def _get_subagent_tools():
    """延迟获取子代理工具，避免循环 import"""
    from src.tools.agent_tools import TOOL_SCHEMAS, TOOL_REGISTRY
    tools = [s for s in TOOL_SCHEMAS if s["name"] in SUBAGENT_TOOL_NAMES]
    registry = {
        name: fn for name, fn in TOOL_REGISTRY.items()
        if name in SUBAGENT_TOOL_NAMES
    }
    return tools, registry


def _run_subagent(task: str) -> str:
    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
    )

    tools, registry = _get_subagent_tools()
    if not tools:
        return "错误：子代理工具未找到（web_search / fetch_webpage 可能未注册）"

    history = [{"role": "user", "content": task}]

    for _ in range(MAX_ROUNDS):
        try:
            response = client.responses.create(
                model="deepseek-flash",
                max_output_tokens=MAX_OUTPUT_TOKENS,
                instructions=SUBAGENT_PROMPT,
                tools=tools,
                input=history,
            )
        except Exception as e:
            return f"子代理调用失败：{type(e).__name__}: {e}"

        function_calls = [i for i in response.output if i.type == "function_call"]
        if not function_calls:
            return response.output_text or "子代理完成，但无输出"

        tool_outputs = []
        for call in function_calls:
            try:
                tool = registry.get(call.name)      # ← 用子代理的 registry
                if tool is None:
                    result = f"子代理不允许调用工具 {call.name}"
                else:
                    args = json.loads(call.arguments)
                    result = str(tool(**args))
            except Exception as e:
                result = f"工具执行失败：{type(e).__name__}: {e}"

            tool_outputs.append({
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": result,
            })

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
                    history.append({"role": "assistant", "content": text})

        for out in tool_outputs:
            history.append({
                "type": "function_call_output",
                "call_id": out["call_id"],
                "output": out["output"],
            })

    return f"子代理达到最大轮数 {MAX_ROUNDS}，未完成"