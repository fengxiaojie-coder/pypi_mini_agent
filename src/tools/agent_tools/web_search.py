# src/tools/web_search.py
"""博查 Web Search API"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "type": "function",
    "name": "web_search",
    "description": (
        "搜索关键词，返回相关网页的标题、链接、摘要和发布时间。"
        "适用于查实时信息、新闻、资料。"
        "不要用 fetch_webpage 抓搜索引擎结果页。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "count": {"type": "integer", "description": "返回结果数，默认 5", "default": 5},
        },
        "required": ["query"],
    },
}


def web_search(query: str, count: int = 5) -> str:
    api_key = os.environ.get("BOCHA_API_KEY")
    if not api_key:
        return "错误：未设置 BOCHA_API_KEY 环境变量"

    url = "https://api.bocha.cn/v1/web-search"
    payload = {
        "query": query,
        "count": count,
        "summary": True,          # 返回长文本摘要，不是短 snippet
        "freshness": "noLimit",   # 不限时间，搜索算法自动优化
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return f"搜索失败：{type(e).__name__}: {e}"

    if data.get("code") != 200:
        return f"搜索失败：{data.get('msg', '未知错误')}"

    pages = data.get("data", {}).get("webPages", {}).get("value", [])
    if not pages:
        return f"未找到「{query}」的结果"

    lines = []
    for p in pages[:count]:
        title = p.get("name", "")
        url_ = p.get("url", "")
        # 优先用 summary（长摘要），没有则用 snippet
        desc = p.get("summary") or p.get("snippet", "")
        site = p.get("siteName", "")
        date = p.get("datePublished", "")
        lines.append(
            f"- **{title}**\n"
            f"  {url_}\n"
            f"  {desc[:300]}\n"
            f"  来源：{site} | {date}"
        )
    return "\n\n".join(lines)