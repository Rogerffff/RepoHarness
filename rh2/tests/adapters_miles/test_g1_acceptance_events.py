"""租前终审 B1/B2 修复验收：g1_acceptance 结构化事件 collect→judge 全链。

对应 codex_prerental_final_recheck.md 的修复验收条款：

- B1：collect 消费 miles 结构化事件（不再日志正则、无"校准位"None 字段）；
  代表性事件目录全链 PASS；删除任一必要事件类别 → 总判定 INCOMPLETE。
- B2：judge 的 applied oracle 用独立 ``optimizer_step_applied`` 事实（NORMAL
  枚举不计入），并与 Adam/scheduler 前后计数交叉验证；``current_version``
  来自 trainer 的 train_rollout 事实（不取 behavior weight_versions 末位）；
  正控组必须被某个真实 applied optimizer step 消费。
- 生产 emitter 同源性（integration base 专属）：直接调用 miles
  ``rh2_event_log.emit`` 产出事件文件，喂给 collect，证明生产 schema 与
  消费端联结逻辑同源，不存在"测试自造 schema、生产另一套"的缝。

事件生成复用 g1_acceptance 自带的代表性 fixture 生成器（_selftest_write_events），
它就是 --self-test 用的同一生成器——单一事实源，避免测试与 self-test 两套样例。
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
from pathlib import Path

import pytest

_G1_PATH = (
    Path(__file__).resolve().parents[2] / "experiments" / "miles_gpu_spike" / "g1_acceptance.py"
)
_spec = importlib.util.spec_from_file_location("g1_acceptance_under_test", _G1_PATH)
g1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g1)


def _collect(events_dir: Path, out_dir: Path) -> dict:
    ns = argparse.Namespace(
        events_dir=str(events_dir), dmon_csv=None, gpu_mem_total_mb=None, out_dir=str(out_dir)
    )
    with contextlib.redirect_stdout(io.StringIO()):
        g1.cmd_collect(ns)
    return json.loads((out_dir / "collect_report.json").read_text())


def _judge(ev: Path, r3: str = "on") -> dict:
    ns = argparse.Namespace(
        evidence_dir=str(ev),
        thresholds=str(_G1_PATH.parent / "thresholds.md"),
        r3=r3,
        custom_config=str(_G1_PATH.parent / "custom_config.yaml"),
        out=str(ev / "verdict.json"),
    )
    with contextlib.redirect_stdout(io.StringIO()):
        g1.cmd_judge(ns)
    return json.loads((ev / "verdict.json").read_text())


def _full_chain(tmp_path: Path, mutate: str = "") -> dict:
    events = tmp_path / "events"
    ev = tmp_path / "evidence"
    g1._selftest_write_events(events, mutate=mutate)
    _collect(events, ev)
    # 探针文件由 launch.sh post-run 产出；这里按其契约直接落盘。
    res = json.loads((ev / "resource_summary.json").read_text())
    res.setdefault("gpu_mem_peak_frac", None)
    if res["gpu_mem_peak_frac"] is None:
        res["gpu_mem_peak_frac"] = 0.9
    (ev / "resource_summary.json").write_text(json.dumps(res))
    (ev / "shutdown_probe.json").write_text('{"orphan_workers": 0, "unfinalized_deliveries": 0}')
    (ev / "checkpoint_probe.json").write_text('{"saved": true, "reloaded": true, "deleted": true}')
    return _judge(ev)


def _failed(verdict: dict) -> set[str]:
    return {c["check"] for c in verdict["checks"] if c["status"] == "FAIL"}


def test_representative_events_full_chain_pass(tmp_path):
    """B1 验收正例：代表性事件目录 collect→judge 全链 PASS，且判定项里没有
    任何 MISSING_EVIDENCE（= 不存在留给租期现场回填的校准位）。"""
    verdict = _full_chain(tmp_path)
    not_pass = [(c["check"], c["status"], c["detail"]) for c in verdict["checks"] if c["status"] != "PASS"]
    assert verdict["overall"] == "PASS", f"非 PASS 项：{not_pass}"


@pytest.mark.parametrize(
    "drop",
    [
        "drop_train_step",
        "drop_train_step_consumed",
        "drop_train_rollout",
        "drop_rollout_group",
        "drop_rollout_workers",
        "drop_logprob_compare",
        "drop_eval_smoke",
        "drop_actor_identity",
        "drop_publish_facts",
    ],
)
def test_delete_any_required_event_kind_yields_incomplete(tmp_path, drop):
    """B1 验收反例：删掉任一必要事件类别，总判定必须 INCOMPLETE（缺证据
    fail-closed，不允许假绿也不允许误报 FAIL 掩盖缺失）。"""
    verdict = _full_chain(tmp_path, mutate=drop)
    assert verdict["overall"] == "INCOMPLETE", (
        f"{drop} 应 INCOMPLETE，得 {verdict['overall']}: "
        + str([(c["check"], c["status"]) for c in verdict["checks"] if c["status"] != "PASS"])
    )


def test_normal_enum_is_not_applied_evidence(tmp_path):
    """B2 复现修复：outcome=NORMAL 但 optimizer_step_applied=False（found-inf/
    debug 型）不得计入 applied step——规模项必须 FAIL 而不是被枚举名判绿。"""
    verdict = _full_chain(tmp_path, mutate="normal_not_applied")
    assert "g1_min_applied_optimizer_steps" in _failed(verdict)


def test_applied_requires_optimizer_counter_progress(tmp_path):
    """B2 交叉验证：声称 applied 的 step 若 Adam step 计数没有 +1，独立计数
    事实与 applied 布尔矛盾，必须 FAIL optimizer_step_progress_consistent。"""
    verdict = _full_chain(tmp_path, mutate="counter_mismatch")
    assert "optimizer_step_progress_consistent" in _failed(verdict)


def test_current_version_from_trainer_fact_not_behavior_tail(tmp_path):
    """B2 复现修复：behavior weight_versions=["1","3"] 而 trainer current=1 时，
    sample_records.current_version 必须取 train_rollout 的 trainer 事实（1），
    behavior_version 取逐 turn 最旧数值版本（1）——不得再取列表末位 3。"""
    events = tmp_path / "events"
    ev = tmp_path / "evidence"
    g1._selftest_write_events(events, mutate="stale_behavior")
    _collect(events, ev)
    rows = [
        r
        for r in g1.read_jsonl(ev / "sample_records.jsonl")
        if r.get("behavior_versions") == ["1", "3"]
    ]
    assert rows, "fixture 应包含 behavior=[1,3] 的样本"
    assert all(r["current_version"] == 1 for r in rows)
    assert all(r["behavior_version"] == 1 for r in rows)


def test_positive_control_must_be_consumed_by_applied_step(tmp_path):
    """B2 验收：正控组 reward 有方差但其样本只进了 SKIPPED_ZERO_SIGNAL step
    （没有驱动任何真实 optimizer 更新）→ 消费判定必须 FAIL。"""
    verdict = _full_chain(tmp_path, mutate="pc_not_applied")
    assert "positive_control_consumed_by_applied_step" in _failed(verdict)


def test_zero_variance_group_reaching_applied_step_fails(tmp_path):
    """拒绝面守恒：零方差组绕过 filter 混进训练批并被 applied step 消费时，
    zero_variance_groups_must_not_train 必须 FAIL。"""
    verdict = _full_chain(tmp_path, mutate="zero_var_trained")
    assert "zero_variance_groups_must_not_train" in _failed(verdict)


def test_actor_identity_mismatch_fails(tmp_path):
    """B3 判定面：任一 actor 的 miles tree digest 与其余/钉死值不一致 → FAIL。"""
    verdict = _full_chain(tmp_path, mutate="identity_mismatch")
    assert "integration_tree_identity" in _failed(verdict)


# ---------------------------------------------------------------------------
# 生产 emitter 同源性（integration base：真实 miles.utils.rh2_event_log）
# ---------------------------------------------------------------------------


@pytest.mark.integration_base
def test_producer_emitter_schema_consumed_by_collect(tmp_path, monkeypatch, world):
    """用 miles 生产模块真函数 emit 事件（含 enabled 门控与文件命名约定），
    喂给 collect：step/rollout/publish 联结字段必须逐一落到 step_records。
    这钉住"生产写什么、collect 读什么"是同一份 schema。"""
    from miles.utils import rh2_event_log

    events_dir = tmp_path / "events"
    monkeypatch.setenv(rh2_event_log.EVENT_DIR_ENV, str(events_dir))
    assert rh2_event_log.enabled()

    rh2_event_log.emit("actor_identity", role="megatron_train_actor", miles_file="/x/miles/__init__.py",
                       tree_digest="ab" * 32, expected_tree_digest="ab" * 32)
    rh2_event_log.emit("train_rollout", rollout_id=0, trainer_current_version=1)
    rh2_event_log.emit("rollout_workers", rollout_id=0, worker_ids=["train/e0"], weight_version=1)
    rh2_event_log.emit("rollout_group", rollout_id=0, group_index=0, instance_id="django__django-11099",
                       sample_indices=[0, 1], rewards=[1.0, 0.0], behavior_versions=[["1"], ["1"]],
                       statuses=["Status.COMPLETED"] * 2, response_lengths=[8, 8],
                       routing_tape=[None, None])
    rh2_event_log.emit("logprob_compare", rollout_id=0, dp_rank=0, trainer_current_version=1,
                       entries=[{"sample_index": 0, "same_version": True, "mean_abs_diff": 0.01,
                                 "num_tokens": 8, "length_mismatch": False}])
    rh2_event_log.emit("train_step_consumed", rollout_id=0, step_id=0, dp_rank=0, rank=0,
                       sample_indices=[0, 1], num_tokens=16)
    rh2_event_log.emit("train_step", rollout_id=0, step_id=0, attempt=0, outcome="NORMAL",
                       optimizer_step_applied=True, adam_step_before=0, adam_step_after=1,
                       scheduler_steps_before=0, scheduler_steps_after=32, grad_norm=0.5,
                       duration_seconds=1.0, rank=0, dp_rank=0, is_pp_last_stage=True,
                       metrics={"dis_accepted_tokens": 10.0, "dis_rejected_tokens": 2.0,
                                "dis_microbatch_provenance_tokens": 12.0})
    rh2_event_log.emit("weight_update", rollout_id=0, version_before=1, version_after=2,
                       duration_seconds=3.0)
    rh2_event_log.emit("eval_smoke", rollout_id=0, ok=True, num_metrics=1)

    files = list(events_dir.glob("rh2_events_*.jsonl"))
    assert files, "生产 emitter 应按 rh2_events_<host>_<pid>.jsonl 命名落盘"

    ev = tmp_path / "evidence"
    report = _collect(events_dir, ev)
    assert report["step_rows"] == 1 and report["sample_rows"] == 2
    assert not report["conflicts"]
    [step] = g1.read_jsonl(ev / "step_records.jsonl")
    assert step["outcome"] == "NORMAL"
    assert step["optimizer_step_applied"] is True
    assert step["adam_step_after"] == 1 and step["scheduler_steps_after"] == 32
    assert step["weight_version_before"] == 1 and step["weight_version_after"] == 2
    assert step["queue_consumed_sample_ids"] == ["0", "1"]
    assert step["worker_ids"] == ["train/e0"]
    assert step["dis_accepted_tokens"] == 10.0
    rows = g1.read_jsonl(ev / "sample_records.jsonl")
    assert {r["sample_id"] for r in rows} == {"0", "1"}
    assert all(r["current_version"] == 1 for r in rows)
    ident = json.loads((ev / "actor_identity.json").read_text())
    assert ident["consistent"] is True
    assert json.loads((ev / "eval_smoke.json").read_text()) == {"ran": True, "ok": True}


@pytest.mark.integration_base
def test_producer_identity_assertion_stops_on_digest_mismatch(monkeypatch, world):
    """B3 worker 侧钉死：RH2_EXPECTED_MILES_TREE_DIGEST 与实际 miles tree
    digest 不一致时，assert_and_emit_identity 必须 raise（actor 启动即停），
    一致时不抛。digest 为真实树内容哈希（与 launch preflight 同函数）。"""
    from miles.utils import rh2_event_log

    monkeypatch.delenv(rh2_event_log.EVENT_DIR_ENV, raising=False)
    real = rh2_event_log.miles_tree_digest()
    assert re_hex64(real)
    monkeypatch.setenv(rh2_event_log.EXPECTED_TREE_DIGEST_ENV, real)
    rh2_event_log.assert_and_emit_identity("unit_test_role")  # 一致：不抛
    monkeypatch.setenv(rh2_event_log.EXPECTED_TREE_DIGEST_ENV, "0" * 64)
    with pytest.raises(RuntimeError, match="identity mismatch"):
        rh2_event_log.assert_and_emit_identity("unit_test_role")


def re_hex64(s: str) -> bool:
    return isinstance(s, str) and len(s) == 64 and all(c in "0123456789abcdef" for c in s)
