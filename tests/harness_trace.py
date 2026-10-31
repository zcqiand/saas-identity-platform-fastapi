"""pytest trace 适配器：@pytest.mark.fn -> suite 契约的 .state/trace.json。

由 tests/conftest.py 命名导入挂载（hook 随导入进 conftest 命名空间供 pytest
发现——pytest_plugins 在非根 conftest 已被 pytest 禁）。5.126 拆分重构：本文件
是 harness 机器件进 sync_always；tests/conftest.py 是仓专属 fixtures，仓自有。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "fn(id, ...): 该测试验证的功能子项 ID，如 @pytest.mark.fn('M01.F01.I01')"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """TRACE_MAP=1 时把 fn marker 映射写 trace.json——suite 契约二唯一产出通道
    （harness.load_trace 只跑 trace_cmd，写入靠本钩子）。"""
    if os.environ.get("TRACE_MAP") != "1":
        return
    entries = []
    for item in items:
        fns: list[str] = []
        for marker in item.iter_markers(name="fn"):
            fns.extend(str(a) for a in marker.args)
        inert = any(item.get_closest_marker(n) is not None for n in ("skip", "skipif", "xfail"))
        entries.append(
            {"test": item.nodeid, "fns": [] if inert else sorted(set(fns)), "inert": inert}
        )
    out = Path(str(config.rootpath)) / ".state" / "trace.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"schema": 1, "tests": entries}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
