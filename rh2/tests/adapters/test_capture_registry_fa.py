"""FA-1 follow-up 3 测试（codex 轮次 8）：CaptureRegistry 的 FIFO / 两阶段
finalize / 逐 attempt rid 记账，以及不需要真 slime 的纯逻辑面。

wire 主体（call_sglang_generate 替换）需要真 slime + SGLang，留 FA-5；这里
测的是 registry 的暂存/提交/销毁语义——P0-1（finalize 移到 commit）、P0-6
（FIFO 不覆盖）的正确性权威。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "experiments"))

from s1_7a_bringup.capture_wire import CaptureRegistry, PendingTurn  # noqa: E402


class FakeHook:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def on_generate_response(self, *, prompt_token_ids, sampling_params, response) -> None:
        self.calls.append({"prompt": list(prompt_token_ids), "response": response})


class FakeProxyResult:
    """ProxyCallResult 的两阶段接口替身（finalize/abandon 幂等）。"""

    def __init__(self, attempt_id: str) -> None:
        self.attempt_id = attempt_id
        self.state = "pending"

    def finalize_delivered(self, ref: str) -> None:
        if self.state != "pending":
            raise ValueError(f"{self.attempt_id} 已 {self.state}")
        self.state = f"finalized:{ref}"

    def abandon_delivered(self, reason: str) -> None:
        if self.state != "pending":
            raise ValueError(f"{self.attempt_id} 已 {self.state}")
        self.state = f"abandoned:{reason}"


def _turn(rid: str, version: str = "1", proxy=None) -> PendingTurn:
    return PendingTurn(
        prompt_ids=[1, 2, 3],
        capture_params={"top_p": 0.95},
        raw_response={"meta_info": {"id": rid}},
        weight_version=version,
        request_id=rid,
        proxy_result=proxy,
    )


def test_finalize_happens_at_commit_not_stage():
    """P0-1：stage 不 finalize（CC 尚未收到 SSE）；commit 成功才 finalize。"""

    registry = CaptureRegistry()
    hook = FakeHook()
    registry.register("sid_A", hook)
    proxy = FakeProxyResult("sid_A/t1_a1")
    registry.stage("sid_A", _turn("rid_1", proxy=proxy))
    assert proxy.state == "pending"  # stage 后仍未交付定案
    registry.commit("sid_A")
    assert proxy.state.startswith("finalized:capture:sid_A:rid_1")  # 真实 request_id
    assert len(hook.calls) == 1


def test_unregister_abandons_uncommitted_draft():
    """P0-1：会话销毁时未 commit 的暂存 = CC 没收到——abandon，不是虚假 delivered。"""

    registry = CaptureRegistry()
    registry.register("sid_B", FakeHook())
    proxy = FakeProxyResult("sid_B/t1_a1")
    registry.stage("sid_B", _turn("rid_x", proxy=proxy))
    registry.unregister("sid_B")
    assert proxy.state.startswith("abandoned:session_unregistered_before_commit")
    assert registry.session_deadlines.get("sid_B") is None  # 会话状态清理（有界）


def test_fifo_no_silent_overwrite_on_concurrent_stage():
    """P0-6：同 session 并发暂存改 FIFO——不再静默覆盖丢数据；commit 按序弹。"""

    registry = CaptureRegistry()
    hook = FakeHook()
    registry.register("sid_C", hook)
    p1, p2 = FakeProxyResult("a1"), FakeProxyResult("a2")
    registry.stage("sid_C", _turn("rid_1", version="1", proxy=p1))
    registry.stage("sid_C", _turn("rid_2", version="2", proxy=p2))  # 上轮未 commit 又来
    assert registry.stats["concurrent_overlap_seen"] == 1
    assert registry.stats["dropped_uncommitted"] == 0  # 关键：没丢数据
    registry.commit("sid_C")
    registry.commit("sid_C")
    assert len(hook.calls) == 2  # 两轮都进了树
    assert registry.weight_versions["sid_C"] == ["1", "2"]  # FIFO 顺序
    assert p1.state.startswith("finalized:") and p2.state.startswith("finalized:")


def test_commit_without_pending_is_noop():
    registry = CaptureRegistry()
    registry.register("sid_D", FakeHook())
    registry.commit("sid_D")  # 无暂存不炸
    assert registry.stats["committed"] == 0


def test_double_commit_does_not_refinalize():
    """重复 commit（防御）：第二次无暂存可弹，不重复 finalize。"""

    registry = CaptureRegistry()
    registry.register("sid_E", FakeHook())
    proxy = FakeProxyResult("a1")
    registry.stage("sid_E", _turn("rid_1", proxy=proxy))
    registry.commit("sid_E")
    first = proxy.state
    registry.commit("sid_E")  # 第二次无暂存
    assert proxy.state == first  # 未被再次触碰


def test_session_deadline_starts_on_first_call_and_is_bounded():
    registry = CaptureRegistry()
    registry.default_session_budget_seconds = 600.0
    d1 = registry.session_deadline("sid_F")
    d2 = registry.session_deadline("sid_F")
    assert d1 == d2  # 同会话稳定
    assert registry.session_deadline(None) is None
    registry.register("sid_F", FakeHook())
    registry.unregister("sid_F")
    assert "sid_F" not in registry.session_deadlines  # 销毁即清理（有界增长修复）
