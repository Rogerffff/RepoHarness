"""FA-0.7：slime fully_async 表面契约测试（F6 纪律扩展到异步面）。

背景：本地 venv 无 torch，slime 模块不可 import——本文件用**源码级结构断言**
钉住我们依赖/规避的上游行为（pin `e848052a`）。它们不是行为测试，抓的是
"升级 pin 后这些承重事实是否还成立"：任何一条失配都意味着 FA-1/FA-3 的
对应设计假设需要重审，禁止只改测试放行。

每条断言都注明依赖它的 FA 设计点。reference/slime 不在本地（浅 checkout）
时整文件 skip——没有被测物就没有契约可验。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_SLIME = Path(__file__).resolve().parents[3] / "reference" / "slime" / "slime"

pytestmark = pytest.mark.skipif(
    not _SLIME.exists(), reason="reference/slime 不在本地，表面契约无被测物"
)


def _read(relpath: str) -> str:
    path = _SLIME / relpath
    assert path.exists(), f"上游文件消失：{relpath}（升级破坏了表面契约，重审 FA 设计）"
    return path.read_text(encoding="utf-8")


def test_done_cb_swallows_task_exceptions_n1():
    """N1（升级设计 §4）：task 异常只 log 后 return，样本静默泄漏。

    FA-1 第 2 条的修复对象——上游若已自行修复（异常样本回队/记账），
    本断言失配，FA-1 应改为复用上游机制而不是自建。
    """

    text = _read("rollout/fully_async_rollout.py")
    cb = text[text.index("def _make_done_cb") :]
    swallow = re.search(
        r"except Exception.*?logger\.exception\(.*?\)\s*\n\s*return", cb, re.DOTALL
    )
    assert swallow, "done_cb 的异常吞没形态变了——N1 泄漏面需要重新核实"


def test_aborted_group_requeues_whole_group():
    """stock 语义：任一成员 ABORTED -> 整组原样回 data_buffer。

    D-FA-3 的 proxy 内部重生成让我们的路径**不产生** slime 级 ABORTED 样本，
    因此不依赖该回队；但它的存在意味着谁若把我们的 fan-out 形状喂回 stock
    路径，会撞上下一条的组长断言——两条一起钉。
    """

    text = _read("rollout/fully_async_rollout.py")
    assert "Sample.Status.ABORTED for s in result" in text
    assert "add_samples([result])" in text


def test_add_samples_asserts_group_length():
    """data_buffer.add_samples 断言每组长度 == n_samples_per_prompt。

    FA-1 第 2 条"不依赖 stock ABORTED 回队"的物理依据：fan-out 组（≠n）
    连回队都做不到；FA-2 的组级过滤不变量（N5）同源。
    """

    text = _read("rollout/data_source.py")
    assert re.search(r"len\(samples\[i\]\)\s*==\s*self\.args\.n_samples_per_prompt", text)


def test_output_queue_put_is_blocking():
    """N2：output_queue.put 是阻塞式（无 timeout/put_nowait）——FA-1 反压设计的对象。"""

    text = _read("rollout/fully_async_rollout.py")
    cb = text[text.index("def _make_done_cb") :]
    put_call = re.search(r"output_queue\.put\(([^)]*)\)", cb)
    assert put_call, "output_queue.put 调用消失"
    assert "timeout" not in put_call.group(1) and "block=False" not in put_call.group(1)


def test_consumer_key_sort_exists():
    """消费侧 `_key` 排序（P3 J4c 崩溃点，fan-out 嵌套形状 TypeError）。

    FA-1 第 4 条三视图交付的回归锚点：我们交付给 slime 的形状必须让
    `_key` 可用（J4c 诊断补丁随 FA-1 正式方案废弃）。
    """

    text = _read("rollout/fully_async_rollout.py")
    assert "def _key" in text


def test_pause_and_continue_generation_endpoints():
    """权重更新窗口的引擎端点（D-FA-3 proxy 窗口判定的物理事实源）。"""

    text = _read("backends/sglang_utils/sglang_engine.py")
    assert "/pause_generation" in text
    assert "/continue_generation" in text


def test_sample_weight_version_plumbing_exists():
    """slime Sample 侧的 meta_info.weight_version 记账存在（FA-0.3 真实版本管道
    的上游对应物；消失说明上游改了版本透传形态，capture 提取点需重审）。"""

    text = _read("utils/types.py")
    assert "weight_version" in text


def test_slime_checkout_matches_pin():
    """pin 守卫（codex FA-0 审查测试项）：reference/slime 在场时 HEAD 必须是
    e848052a——升级必须显式走"改 pin + 重跑本文件全部断言"，不许静默漂移。
    仓库缺席仍走文件级 skip（inspect-rh2-fa 建账后升级为 fail）。"""

    import subprocess

    head = subprocess.run(
        ["git", "-C", str(_SLIME.parent), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    ).stdout.strip()
    assert head.startswith("e848052a"), (
        f"reference/slime HEAD={head[:12]} 偏离 pin e848052a——"
        "本文件的全部源码断言基于该 pin，升级前先重审 FA 设计假设。"
    )
