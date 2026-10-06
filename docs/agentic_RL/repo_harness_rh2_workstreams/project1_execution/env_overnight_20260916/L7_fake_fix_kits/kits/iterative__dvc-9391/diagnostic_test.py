"""L7 判别用例 · iterative__dvc-9391

题面的诉求是 `--rev` 可重复：`--rev a --rev b` 应得到 `["a", "b"]`。
5 条 F2P 无一传两个 `--rev`，所以 `type=lambda s: [s]` 这种"把单值包成列表"的假修复满分。

三态预期：base 失败（rev 是字符串 "b"）、gold 通过、fake 失败（rev 是 ["b"]，后者覆盖前者）。
"""
import argparse

from dvc.commands.experiments import add_rev_selection_flags


def _parser():
    p = argparse.ArgumentParser()
    add_rev_selection_flags(p, "Show")
    return p


def test_l7_rev_is_repeatable():
    ns = _parser().parse_args(["--rev", "a", "--rev", "b"])
    assert ns.rev == ["a", "b"]


def test_l7_single_rev_is_still_a_list():
    ns = _parser().parse_args(["--rev", "a"])
    assert ns.rev == ["a"]
