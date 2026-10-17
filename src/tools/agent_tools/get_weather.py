# get_weather.py
import urllib.request
import urllib.parse
import json

TOOL_SCHEMA = {
    "type": "function",
    "name": "get_weather",
    "description": (
        "查询指定城市的实时天气。"
        "支持中文城市名（如 北京、上海）或英文（Beijing）。"
        "返回天气描述、气温、体感温度、湿度、风速风向。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "城市名称，如 '北京'、'上海'、'Beijing'",
            },
            "format": {
                "type": "string",
                "enum": ["brief", "full"],
                "description": "brief 返回一行摘要，full 返回详细数据，默认 brief",
                "default": "brief",
            },
        },
        "required": ["city"],
    },
}

def get_weather(city: str, format: str = "brief") -> str:
    """
    查询指定城市的天气。

    Args:
        city: 城市名，中文或英文，如 "北京" / "Beijing"
        format: "brief" 简洁 / "full" 详细
    """
    try:
        # wttr.in 免费天气接口，中文用 ?lang=zh
        encoded = urllib.parse.quote(city)
        if format == "brief":
            # format=3 只返回一行摘要
            url = f"https://wttr.in/{encoded}?format=3&lang=zh"
        else:
            # format=j1 返回 JSON 详细数据
            url = f"https://wttr.in/{encoded}?format=j1&lang=zh"

        req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8")

        if format == "brief":
            return data.strip()

        # 解析 JSON，提取关键字段
        j = json.loads(data)
        current = j["current_condition"][0]
        area = j["nearest_area"][0]

        city_name = area["areaName"][0]["value"]
        country = area["country"][0]["value"]
        desc = current["lang_zh"][0]["value"] if "lang_zh" in current else current["weatherDesc"][0]["value"]
        temp = current["temp_C"]
        feels = current["FeelsLikeC"]
        humidity = current["humidity"]
        wind = current["windspeedKmph"]
        wind_dir = current["winddir16Point"]

        return (
            f"【{city_name}, {country}】\n"
            f"天气：{desc}\n"
            f"气温：{temp}°C（体感 {feels}°C）\n"
            f"湿度：{humidity}%\n"
            f"风速：{wind} km/h，风向 {wind_dir}"
        )

    except urllib.error.URLError as e:
        return f"错误：网络请求失败 {e}"
    except json.JSONDecodeError:
        return f"错误：天气数据解析失败"
    except KeyError as e:
        return f"错误：城市 '{city}' 未找到或数据格式异常 {e}"
    except Exception as e:
        return f"错误：{type(e).__name__}: {e}"