"""L7 判别用例 · iterative__dvc-2126

F2P 的断言是正则 `Binary: (True|False)`，硬编码字面量就能过（P2P=0）。
题面要的是"报告当前是否为打包二进制"，所以正确实现必须真的去问 `dvc.utils.is_binary()`。

三态预期：base 失败（根本没有 Binary 行）、gold 通过、
fake 失败（`dvc.command.version` 模块里没有 `is_binary` 这个名字，monkeypatch 直接 AttributeError）。
"""
import logging
import re

import pytest


def test_l7_binary_line_reflects_is_binary(caplog, monkeypatch):
    import dvc.command.version as version_mod
    from dvc.main import main

    # raising=True：gold 才会有这个名字；base / fake 会在这里就 AttributeError
    monkeypatch.setattr(version_mod, "is_binary", lambda: True, raising=True)
    with caplog.at_level(logging.INFO, logger="dvc"):
        assert main(["version"]) == 0
    assert re.search(r"Binary: True", caplog.text), caplog.text
