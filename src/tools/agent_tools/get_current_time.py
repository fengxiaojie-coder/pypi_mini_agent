#get_current_time.py
import datetime

TOOL_SCHEMA = {
    "type": "function",
    "name": "get_current_time",
    "description": "获取当前北京时间，返回格式为 YYYY-MM-DD HH:MM:SS",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

def get_current_time():
    tz = datetime.timezone(datetime.timedelta(hours=8))  # 设置为北京时间（UTC+8）
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")