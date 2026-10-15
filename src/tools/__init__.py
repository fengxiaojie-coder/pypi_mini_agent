"""自动发现 tools 目录下所有工具，汇总成 schema 列表和函数注册表"""

import importlib
import pkgutil
from pathlib import Path


def _discover_tools():
    schemas = []
    registry = {}

    tools_dir = Path(__file__).parent
    for info in pkgutil.iter_modules([str(tools_dir)]):
        if info.name == "__init__":
            continue
        mod = importlib.import_module(f".{info.name}", package=__name__)
        if hasattr(mod, "TOOL_SCHEMA"):
            schemas.append(mod.TOOL_SCHEMA)
        # 把模块里所有可调用函数（排除私有/下划线开头）注册进去
        for attr_name in dir(mod):
            if attr_name.startswith("_"):
                continue
            attr = getattr(mod, attr_name)
            if callable(attr) and attr_name != "TOOL_SCHEMA":
                registry[attr_name] = attr

    return schemas, registry


TOOL_SCHEMAS, TOOL_REGISTRY = _discover_tools()