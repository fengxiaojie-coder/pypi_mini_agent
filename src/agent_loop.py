# agent_loop.py
import os
import json

from openai import OpenAI

from src.tools.agent_tools import TOOL_SCHEMAS, TOOL_REGISTRY
from src.memory.memory_manager import MemoryManager
from src.memory.history_compact import compact_jsonl
from src.tools.agent_tools.update_todos import (
    get_todos, render_todos, clear_todos,
)


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

MODEL = "deepseek-flash"
MAX_OUTPUT_TOKENS = 8000
TODO_MAX_CONTINUE = 10


def build_instructions(memory_manager) -> str:
    """拼 system prompt：基础 + 长期记忆 + 用户画像 + 当前任务"""
    parts = [PROMPT_SETTING]

    memory = memory_manager.load_memory_md().strip()
    user = memory_manager.load_user_md().strip()

    if memory:
        parts.append(f"\n## 长期记忆\n{memory}")
    if user:
        parts.append(f"\n## 用户画像\n{user}")

    todos = get_todos()
    if todos:
        parts.append(f"\n## 当前任务清单\n{render_todos(todos)}")

    return "\n".join(parts)


def _default_send_event(event: dict):
    """终端默认：把事件打印出来"""
    t = event.get("type")
    if t == "assistant_message":
        print(f"\n【最终答案】\n{event.get('content', '')}")
    elif t == "tool_call":
        print(f"[调用工具] {event.get('name')}")
    elif t == "tool_result":
        out = event.get("output", "")
        print(f"[工具结果] {out[:200]}")
    elif t == "reasoning":
        print(f"[推理] {event.get('content', '')}")
    elif t == "todos_update":
        todos = event.get("todos") or []
        if todos:
            print(f"[任务列表]\n{render_todos(todos)}")
        else:
            print("[任务列表] 已清空")
    elif t == "error":
        print(f"[错误] {event.get('message')}")


class AgentSession:
    """一个对话会话，支持把事件推给前端"""

    def __init__(self, send_event=None):
        self.send_event = send_event or _default_send_event
        self.client = OpenAI(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url="https://api.deepseek.com",
        )
        self.memory_manager = MemoryManager()
        self.history = self.memory_manager.load_as_context(limit=20)

    # ---------- 对外入口 ----------

    def run(self, user_input: str):
        """跑一轮对话（同步）"""
        if not user_input.strip():
            return

        # 特殊命令
        if user_input == "/compact":
            self._compact(reload=True)
            return
        if user_input == "clear":
            self._clear()
            return
        if user_input == "exit":
            self._compact(reload=False)
            return

        self.history.append({"role": "user", "content": user_input})
        self.memory_manager.save_user_message(user_input)

        response = self.client.responses.create(
            model=MODEL,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            instructions=build_instructions(self.memory_manager),
            tools=TOOL_SCHEMAS,
            input=self.history,
        )

        answer = self._tool_use(response)

        for item in answer.output:
            if item.type == "message":
                text = item.content[0].text
                self.send_event({"type": "assistant_message", "content": text})

    # ---------- 内部逻辑 ----------

    def _tool_use(self, response):
        """工具调用循环，直到模型不再调工具"""
        todo_continue_count = 0

        while True:
            # 推理过程
            for item in response.output:
                if item.type == "reasoning":
                    for s in getattr(item, "summary", []) or []:
                        self.send_event({"type": "reasoning", "content": s.text[:500]})
                    for c in getattr(item, "content", []) or []:
                        if getattr(c, "type", None) == "reasoning_text":
                            self.send_event({"type": "reasoning", "content": c.text[:500]})

            function_calls = [
                i for i in response.output if i.type == "function_call"
            ]

            # 没有工具调用 = 本轮结束
            if not function_calls:
                text = response.output_text or ""
                if text:
                    self.history.append({"role": "assistant", "content": text})
                    self.memory_manager.save_assistant_message(text)

                # todolist 续跑
                todos = get_todos()
                unfinished = [t for t in todos if t["status"] != "completed"]

                if unfinished and todo_continue_count < TODO_MAX_CONTINUE:
                    todo_continue_count += 1
                    self.send_event({"type": "todos_update", "todos": todos})
                    self.send_event({
                        "type": "info",
                        "content": f"计划未完成，继续执行 ({todo_continue_count}/{TODO_MAX_CONTINUE})",
                    })

                    reminder = {
                        "role": "user",
                        "content": (
                            "任务尚未完成，以下项仍未办妥，请继续执行并按规则更新 todolist：\n"
                            + render_todos(todos)
                        ),
                    }
                    self.history.append(reminder)
                    self.memory_manager.save_user_message(reminder["content"])

                    response = self.client.responses.create(
                        model=MODEL,
                        max_output_tokens=MAX_OUTPUT_TOKENS,
                        instructions=build_instructions(self.memory_manager),
                        tools=TOOL_SCHEMAS,
                        input=self.history,
                    )
                    continue

                if todos:
                    if unfinished:
                        self.send_event({
                            "type": "info",
                            "content": f"达到最大续跑次数 {TODO_MAX_CONTINUE}，停止",
                        })
                    else:
                        self.send_event({"type": "info", "content": "计划全部完成"})
                    self.send_event({"type": "todos_update", "todos": []})
                    clear_todos()

                return response

            # 执行工具
            tool_outputs = []
            for call in function_calls:
                self.send_event({"type": "tool_call", "name": call.name})
                try:
                    tool = TOOL_REGISTRY.get(call.name)
                    if tool is None:
                        result = f"当前agent不存在此工具{call.name}"
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
                self.memory_manager.save_tool_call(call.name, call.arguments, call.call_id)
                self.memory_manager.save_tool_output(call.name, result, call.call_id)
                self.send_event({
                    "type": "tool_result",
                    "call_id": call.call_id,
                    "output": result[:300],
                })

            # 记 history（模型本轮输出 + 工具结果）
            for item in response.output:
                if item.type == "function_call":
                    self.history.append({
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
                        self.history.append({"role": "assistant", "content": text})

            for out in tool_outputs:
                self.history.append({
                    "type": "function_call_output",
                    "call_id": out["call_id"],
                    "output": out["output"],
                })

            response = self.client.responses.create(
                model=MODEL,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                instructions=build_instructions(self.memory_manager),
                tools=TOOL_SCHEMAS,
                input=self.history,
            )

    # ---------- 特殊命令 ----------

    def _compact(self, reload: bool = True):
        self.send_event({"type": "info", "content": "开始压缩历史记录"})
        summary = compact_jsonl(self.memory_manager, self.client, keep_recent=10)
        if summary:
            self.send_event({"type": "info", "content": "历史记录已压缩"})
            self.send_event({"type": "summary", "content": summary})
            if reload:
                self.history = self.memory_manager.load_as_context(limit=20)
                self.send_event({
                    "type": "info",
                    "content": f"已重载 {len(self.history)} 条历史",
                })
        else:
            self.send_event({"type": "info", "content": "无需压缩历史记录"})

    def _clear(self):
        self.send_event({"type": "info", "content": "清空历史记录"})
        self.memory_manager.clear_history()
        self.history = []
        clear_todos()


def init_agent(send_event=None):
    """给 WebSocket 用的入口"""
    return AgentSession(send_event=send_event)


def agent_loop():
    """终端 REPL 入口，复用 AgentSession"""
    session = AgentSession(send_event=_default_send_event)

    if session.history:
        print(f"[已恢复 {len(session.history)} 条历史]")

    while True:
        try:
            user_input = input("你:")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_input == "exit":
            session._compact(reload=False)
            print("退出 agent_loop")
            break

        try:
            session.run(user_input)
        except Exception as e:
            print(f"[错误] {type(e).__name__}: {e}")