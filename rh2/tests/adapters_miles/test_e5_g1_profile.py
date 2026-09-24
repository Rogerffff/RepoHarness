"""E5（第六组 I24；Codex 复核 §4 第 2 条）：G1 judge 按启动证据区分诊断 / 效率档。

oracle：
- 档位只来自 run_manifest.json 的 forward_profile（launch P12 从最终参数推导），judge 按同一函数重算核对；块缺失 =
  MISSING（INCOMPLETE），块被改写 / unsupported = FAIL。
- 诊断档：原判定不变——缺 logprob_compare 仍是 MISSING。
- 效率档：logprob 两项记 NOT_APPLICABLE（unavailable_by_configuration）；R3 消费链仍逐 rank 要求 fill / 每 step 的
  train_step 消费 / exhausted，只免 logprob_forward 一环；出现对拍或 logprob_forward 消费 = 配置与运行矛盾（FAIL）；
  总判定最多 NOT_APPLICABLE，不给 G1 PASS，judge 退出码非零。
事件夹具复用 g1_acceptance 自带的生成器（与 --self-test 同源），效率档夹具按生产 producer 不发那两类事件。
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

_G1_PATH = Path(__file__).resolve().parents[2] / "experiments" / "miles_gpu_spike" / "g1_acceptance.py"
_spec = importlib.util.spec_from_file_location("g1_acceptance_e5_under_test", _G1_PATH)
g1 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = g1
_spec.loader.exec_module(g1)


def _judge(ev: Path) -> tuple[dict, int]:
    ns = argparse.Namespace(evidence_dir=str(ev), thresholds=str(_G1_PATH.parent / "thresholds.md"), r3="on",
                            custom_config=str(_G1_PATH.parent / "custom_config.yaml"), out=str(ev / "verdict.json"))
    with contextlib.redirect_stdout(io.StringIO()):
        rc = g1.cmd_judge(ns)
    return json.loads((ev / "verdict.json").read_text()), rc


def _status(verdict: dict) -> dict[str, str]:
    return {c["check"]: c["status"] for c in verdict["checks"]}


def test_diagnostic_profile_keeps_the_g1_verdict_and_exit_code(tmp_path):
    verdict, rc = _judge(g1._selftest_evidence(tmp_path))
    assert (verdict["overall"], rc, verdict["forward_profile"], verdict["g1_parity"]) == ("PASS", 0, "diagnostic", "applicable")
    status = _status(verdict)
    assert status["forward_profile_evidence"] == "PASS"
    assert status["logprob_same_version_mean_abs_diff_max"] == status["logprob_alignment_and_coverage"] == "PASS"


def test_diagnostic_profile_missing_logprob_compare_is_still_missing_evidence(tmp_path):
    verdict, rc = _judge(g1._selftest_evidence(tmp_path, mutate="drop_logprob_compare"))
    assert verdict["overall"] == "INCOMPLETE" and rc == 1
    status = _status(verdict)
    assert status["logprob_same_version_mean_abs_diff_max"] == status["logprob_alignment_and_coverage"] == "MISSING_EVIDENCE"


def test_efficiency_profile_is_not_applicable_never_pass(tmp_path):
    verdict, rc = _judge(g1._selftest_evidence(tmp_path, profile="efficiency"))
    assert (verdict["overall"], rc, verdict["forward_profile"], verdict["g1_parity"]) == ("NOT_APPLICABLE", 1, "efficiency", "not_applicable")
    status = _status(verdict)
    assert status["forward_profile_evidence"] == "NOT_APPLICABLE"
    assert status["logprob_same_version_mean_abs_diff_max"] == status["logprob_alignment_and_coverage"] == "NOT_APPLICABLE"
    details = {c["check"]: c["detail"] for c in verdict["checks"]}
    assert details["logprob_alignment_and_coverage"].startswith("unavailable_by_configuration")
    # 训练 replay 链照常检查：fill / 每 step 消费 / 耗尽，只免 logprob 前向消费
    assert status["routing_replay_trainer_consumption"] == "PASS" and "logprob 前向消费按配置不可用" in details["routing_replay_trainer_consumption"]
    assert "交叉校验按配置不可用" in details["weight_version_spans_coverage"]
    assert not [c for c in verdict["checks"] if c["status"] in ("FAIL", "MISSING_EVIDENCE")]


@pytest.mark.parametrize(
    ("mutate", "check"),
    [
        ("eff_logprob_compare_present", "logprob_same_version_mean_abs_diff_max"),
        ("eff_logprob_compare_present", "logprob_alignment_and_coverage"),
        ("eff_logprob_forward_consume_present", "routing_replay_trainer_consumption"),
        ("replay_missing_rank_step", "routing_replay_trainer_consumption"),
        ("replay_not_exhausted", "routing_replay_trainer_consumption"),
        ("replay_zero_pops", "routing_replay_trainer_consumption"),
    ],
)
def test_efficiency_profile_still_requires_training_replay_and_flags_contradictions(tmp_path, mutate, check):
    verdict, rc = _judge(g1._selftest_evidence(tmp_path, mutate=mutate, profile="efficiency"))
    assert _status(verdict)[check] == "FAIL" and verdict["overall"] == "FAIL" and rc == 1


def test_efficiency_profile_without_replay_events_is_incomplete(tmp_path):
    verdict, _ = _judge(g1._selftest_evidence(tmp_path, mutate="drop_replay_events", profile="efficiency"))
    assert verdict["overall"] == "INCOMPLETE" and _status(verdict)["routing_replay_trainer_consumption"] == "MISSING_EVIDENCE"


@pytest.mark.parametrize(
    ("mutate", "status", "overall"),
    [
        ("manifest_missing_forward_profile", "MISSING_EVIDENCE", "INCOMPLETE"),
        ("manifest_forward_profile_unsupported", "FAIL", "FAIL"),
        ("manifest_forward_profile_tampered", "FAIL", "FAIL"),
    ],
)
def test_forward_profile_evidence_missing_unsupported_or_rewritten(tmp_path, mutate, status, overall):
    verdict, rc = _judge(g1._selftest_evidence(tmp_path, mutate=mutate))
    assert _status(verdict)["forward_profile_evidence"] == status and verdict["overall"] == overall and rc == 1
    if mutate == "manifest_forward_profile_tampered":
        assert "recorded_block_inconsistent" in {c["check"]: c["detail"] for c in verdict["checks"]}["forward_profile_evidence"]


def test_collect_report_no_longer_calls_absent_compare_plain_missing_evidence(tmp_path):
    ev = g1._selftest_evidence(tmp_path, profile="efficiency")
    report = json.loads((ev / "collected" / "collect_report.json").read_text())
    (line,) = [m for m in report["missing"] if m.startswith("logprob_compare")]
    assert "效率档 = 按配置不产生" in line and "forward_profile" in line
    assert report["event_counts"].get("logprob_compare", 0) == 0
