# src/server/ws_server.py
"""WebSocket 后端：把 agent 的对话结果推给前端"""

import asyncio
import json
import sys
import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agent_loop import init_agent

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
logger = logging.getLogger("ws")


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()

    loop = asyncio.get_running_loop()

    def send_event(event: dict):
        """同步函数：线程里调用，调度到事件循环发送"""
        logger.info(f"send: {event}")
        asyncio.run_coroutine_threadsafe(
            ws.send_text(json.dumps(event, ensure_ascii=False)),
            loop,
        )

    agent = init_agent(send_event=send_event)

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            user_input = msg.get("content", "")

            if not user_input.strip():
                continue
            if user_input == "exit":
                break

            await asyncio.to_thread(agent.run, user_input)
            await ws.send_text(json.dumps({"type": "done"}))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_text(json.dumps(
                {"type": "error", "message": f"{type(e).__name__}: {e}"},
                ensure_ascii=False,
            ))
        except Exception:
            pass