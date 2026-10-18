#__init__.py
"""自动发现 tools 目录下所有工具，汇总成 schema 列表和函数注册表"""

import importlib
import pkgutil
from pathlib import Path


def _discover_tools():
    schemas = []
    registry = {}

    tools_dir = Path(__file__).parent

    package_name = __name__
    if package_name == "__main__":
        package_name = tools_dir.name

    for info in pkgutil.iter_modules([str(tools_dir)]):
        if info.name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f".{info.name}", package=package_name)
        except Exception as e:
            print(f"[警告] 工具模块 {info.name} 导入失败，已跳过：{type(e).__name__}: {e}")
            continue

        mod = importlib.import_module(f".{info.name}", package=__name__)
        if hasattr(mod, "TOOL_SCHEMA"):
            schema = mod.TOOL_SCHEMA
            schemas.append(schema)
            name = schema.get("name")
            fn = getattr(mod, name, None)
            if callable(fn):
                registry[name] = fn
            else:
                print(f"[警告] {info.name}.py 声明了工具 {name} 但没有同名函数")
        # 把模块里所有可调用函数（排除私有/下划线开头）注册进去
        for attr_name in dir(mod):
            if attr_name.startswith("_"):
                continue
            attr = getattr(mod, attr_name)
            if callable(attr) and attr_name != "TOOL_SCHEMA":
                registry[attr_name] = attr

    return schemas, registry


TOOL_SCHEMAS, TOOL_REGISTRY = _discover_tools()