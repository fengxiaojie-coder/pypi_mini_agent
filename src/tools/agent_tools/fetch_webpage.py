# fetch_webpage.py
"""抓取网页内容并转为纯文本"""

import html as html_mod
import re
import urllib.error
import urllib.request


TOOL_SCHEMA = {
    "type": "function",
    "name": "fetch_webpage",
    "description": (
        "抓取**已知 URL** 的网页内容并转为纯文本。"
        "适用于查阅文档、文章、API 说明等。"
        "**不要用本工具抓搜索引擎结果页**（如 bing.com/search、baidu.com/s），"
        "搜索请用 web_search 工具。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "网页 URL，如 https://example.com",
            },
            "max_chars": {
                "type": "integer",
                "description": "最多返回字符数，默认 8000。大页面会被截断。",
                "default": 2000,
            },
        },
        "required": ["url"],
    },
}


def fetch_webpage(url: str, max_chars: int = 2000) -> str:
    """抓取网页并提取纯文本。"""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"

        # 解码（先声明编码，失败退回 utf-8 replace）
        try:
            html = raw.decode(charset, errors="replace")
        except LookupError:
            html = raw.decode("utf-8", errors="replace")

        # 去除 script / style / 注释
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S | re.I)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.S | re.I)
        html = re.sub(r"<!--.*?-->", "", html, flags=re.S)

        # 去除标签，保留文本
        text = re.sub(r"<[^>]+>", " ", html)

        # 解码 HTML 实体（&amp; &lt; 等）
        text = html_mod.unescape(text)

        # 压缩空白
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text).strip()

        # 截断
        truncated = len(text) > max_chars
        if truncated:
            text = text[:max_chars]

        header = f"[URL: {url}"
        if truncated:
            header += f" | 已截断至 {max_chars} 字符"
        header += "]\n"

        return header + text

    except urllib.error.HTTPError as e:
        return f"错误：HTTP {e.code} {e.reason}"
    except urllib.error.URLError as e:
        return f"错误：网络请求失败 {e.reason}"
    except Exception as e:
        return f"错误：{type(e).__name__}: {e}"