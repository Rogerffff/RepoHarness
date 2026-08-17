"""codex 轮次 14 仍需修正 5：生产装配面的本地回归——limiter 真传进 proxy、
open_session 回滚、audit 事务化（写失败不丢内存证据）。glue 可本地 import
（重物在 async_start 内惰性加载），这些工厂正是为可测性从闭包提取的。"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "experiments"))

from repoharness2.adapters.slime.capture_wire import CaptureRegistry  # noqa: E402
from repoharness2.adapters.slime.bringup import (  # noqa: E402
    build_production_model_call_proxy,
    make_per_rollout_adapter,
    write_execution_audit_record,
)


class FakeHook:
    def on_generate_response(self, **kwargs) -> None:
        pass


def test_production_proxy_assembly_wires_limiter(monkeypatch):
    """轮次 13 P0-4 的装配回归：env 旋钮 -> 生产 proxy 的 _limits 真实生效
    （此前 rh2_fa_limit_model_call 是无消费者的假配置）。"""

    monkeypatch.setenv("RH2_FA_LIMIT_MODEL_CALL", "1")
    registry = CaptureRegistry()
    proxy = build_production_model_call_proxy(
        registry, lambda: "3", require_real=False, artifact_sink=None
    )
    assert proxy._limits is not None
    assert proxy._limits.limits["model_call"] == 1  # env 真的传进 semaphore 配置
    assert registry.model_call_proxy is proxy  # 装配点挂上 registry
    assert proxy._sink_required is False


def test_open_session_rollback_on_underlying_failure():
    """轮次 13 P1-6 的装配回归：底层 open 失败 -> registry 注册回滚
    （否则健康 SID 永久占用 registry，后续同 SID 全被 Duplicate 拒绝）。"""

    registry = CaptureRegistry()

    class ExplodingSharedAdapter:
        def open_session(self, sid, *, sampling_defaults=None, max_context_tokens=0):
            raise RuntimeError("underlying open failed")

    adapter = make_per_rollout_adapter(registry, ExplodingSharedAdapter(), FakeHook())
    with pytest.raises(RuntimeError, match="underlying open failed"):
        adapter.open_session("sid_RB", physical_attempt_id="exec_RB#p1-a")
    assert "sid_RB" not in registry.hooks  # 已回滚
    assert registry.physical_attempt_id_for("sid_RB") is None  # paid 同步回滚（二审 P0）

    class OkSharedAdapter:
        def open_session(self, sid, *, sampling_defaults=None, max_context_tokens=0):
            pass  # shared adapter（slime AnthropicAdapter）不接收 paid——paid 只进 registry

    adapter2 = make_per_rollout_adapter(registry, OkSharedAdapter(), FakeHook())
    adapter2.open_session("sid_RB", physical_attempt_id="exec_RB#p2-b")  # replay 新 paid
    assert "sid_RB" in registry.hooks
    assert registry.physical_attempt_id_for("sid_RB") == "exec_RB#p2-b"  # replay 畅通（二审 P0 验收）


def _fake_audit(sid: str, paid: str | None = None) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        session_id=sid,
        physical_attempt_id=paid,
        started_epoch_seconds=1000.0,
        started_monotonic=500.0,
        non_chargeable_intervals=[],
        baseline_manifest_digest="sha256:" + "b" * 64,
        baseline_entry_count=3,
        frozen_patch_digest="sha256:" + "f" * 64,
        patch_entry_count=2,
        excluded_pathset_changed=False,
        runtime_private_pathset_changed=False,
        unsafe_artifact_reasons=[],
        scoring_projection_entry_count=1,
        session_plane_drained=True,
        runtime_quiescence_confirmed=False,
        capture_closed=True,
        outcome_v2={"schema_id": "rh2.fa.rollout_attempt_outcome.v2"},
        trajectory_id="traj_x",
        task_id="task_x",
        finalized=None,
        failure_records=[types.SimpleNamespace(stage="assemble", error_type="E", detail="d")],
        cleanup_failures=[],
        context_shrink_reasons=[],
        steps=["step1"],
        delivered_sample_count=0,
        lease_released=True,
        repair_signal_forwarded=False,
        harness_exit_code=0,
        timeline_dicts=lambda: [{"name": "step1", "at": 1.0}],
        timing_summary=lambda: {"total_seconds": 2.5},
    )


def _proxy_with_attempt(sid: str, paid: str | None = None):
    import asyncio

    from repoharness2.adapters.slime.async_worker import ModelCallProxy
    from repoharness2.contracts.fa_runtime import TrainingRuntimeWindow

    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)

    class Active:
        def current_window(self) -> TrainingRuntimeWindow:
            return TrainingRuntimeWindow(
                update_epoch=1,
                phase="ACTIVE",
                old_version="0",
                target_version="1",
                active_version="1",
                window_started_at=now,
                window_completed_at=now + timedelta(seconds=5),
                fencing_token="f1",
            )

    proxy = ModelCallProxy(Active())

    async def scenario():
        async def send(attempt: int) -> dict:
            return {"text": "ok", "meta_info": {"id": "rid", "weight_version": "1"}}

        result = await proxy.call(paid or sid, "turn_0", send, physical_attempt_id=paid)
        result.finalize_delivered("cap_ref")

    asyncio.new_event_loop().run_until_complete(scenario())
    return proxy


def test_write_execution_audit_success_acks_and_enriches(tmp_path):
    """轮次 14 仍需修正 2/4：成功路径——记录含 timeline/timing/disposition/
    attempts，且持久化成功后 ledger 才被 ack 清空。"""

    proxy = _proxy_with_attempt("sid_AU", "sid_AU#p1-x")
    assert len(proxy.attempts_ledger) == 1
    path = tmp_path / "audit.jsonl"
    write_execution_audit_record(proxy, _fake_audit("sid_AU", "sid_AU#p1-x"), path)
    record = json.loads(path.read_text().strip())
    # F2-0b 复核 P1-B：execution wall 双时钟起止 + 时钟域必须真实落盘
    # （timeline 首/末事件不能替代 wall——此处读 JSON 而非只查对象属性）
    assert record["wall_start_epoch"] == 1000.0
    assert record["wall_start_monotonic"] == 500.0
    assert record["wall_end_monotonic"] >= 500.0 or record["wall_end_monotonic"] < 500.0  # 键在场且为数
    assert isinstance(record["wall_end_epoch"], float)
    assert record["wall_clock_domain_id"].startswith("proc-")
    assert record["non_chargeable_intervals"] == []
    # F2-2：quiescence 事实与 outcome_v2 真实落盘
    # B2 closure P1-2：B1/B2 摘要真实落盘
    assert record["baseline_manifest_digest"] == "sha256:" + "b" * 64
    assert record["baseline_entry_count"] == 3
    assert record["frozen_patch_digest"] == "sha256:" + "f" * 64
    assert record["patch_entry_count"] == 2
    assert record["excluded_pathset_changed"] is False
    assert record["session_plane_drained"] is True
    assert record["runtime_quiescence_confirmed"] is False  # 完整屏障未落地
    assert record["capture_closed"] is True
    assert record["outcome_v2"]["schema_id"] == "rh2.fa.rollout_attempt_outcome.v2"
    assert record["timeline"] == [{"name": "step1", "at": 1.0}]  # 时间线不再丢
    assert record["timing_summary"] == {"total_seconds": 2.5}
    assert record["disposition"] == "aborted" and record["lease_released"] is True
    assert len(record["model_call_attempts"]) == 1
    assert proxy.attempts_ledger == []  # 持久化成功 -> ack 移除


def test_write_execution_audit_failure_keeps_ledger(tmp_path):
    """轮次 14 仍需修正 2 的反例回归：写失败（目录不存在）时 attempt **不被
    摘走**——不会"既拒绝 rollout 又丢审计依据"。"""

    proxy = _proxy_with_attempt("sid_AF", "sid_AF#p1-y")
    bad_path = tmp_path / "no_such_dir" / "audit.jsonl"
    with pytest.raises(OSError):
        write_execution_audit_record(proxy, _fake_audit("sid_AF", "sid_AF#p1-y"), bad_path)
    assert len(proxy.attempts_ledger) == 1  # 内存证据仍在（修复前已被 drain 丢失）
