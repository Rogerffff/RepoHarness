"""I19/I20 聚焦复核：真实生产序列化函数到离线报告的 CPU 接缝探针。

只在临时目录写输入，不修改源码。需要 rh2 虚拟环境；输出表示反例是否复现，
不是训练或报告正确性验收。Ray / Megatron 相关函数从当前源码原样提取 AST，
仅替换事件落盘与分布式查询；未运行真实 CC、Docker、GPU 或分布式训练。
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/pyproject.toml").is_file())
sys.path.insert(0, str(ROOT / "reference/miles-rh2-integration"))
sys.path.insert(0, str(ROOT / "rh2/src"))

from repoharness2.adapters.miles.run_report import build_run_report, load_run_inputs
from repoharness2.adapters.slime.bringup import (
    BringupService,
    write_execution_audit_record,
)
from repoharness2.adapters.slime.generate import RolloutAudit


def extract(relative, name, namespace):
    """执行源码中的指定函数；不手写一份生产序列化逻辑。"""
    path = ROOT / relative
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    unit = ast.Module(body=ast.parse("from __future__ import annotations").body + [node], type_ignores=[])
    # 仅运行上面列出的仓库源码函数，避免为 CPU 探针加载 Ray / Megatron；不读取外部代码。
    exec(compile(ast.fix_missing_locations(unit), str(path), "exec"), namespace)  # noqa: S102
    return namespace[name]


def make_audit(directory, sid):
    directory.mkdir(parents=True)
    audit = RolloutAudit(trajectory_id=sid, task_id="task-" + sid)
    audit.session_id = sid
    audit.physical_attempt_id = "attempt-" + sid
    audit.lifecycle_timing.set("test", 40.0)
    audit.lifecycle_timing.set("sandbox_container_start", 3.5)
    audit.lifecycle_timing.grading_queue_depth_at_enqueue = 7
    grading = NS(outcome="resolved", failure_category=None, reward=1.0, timings=None)
    audit.finalized = NS(
        grading_report=grading,
        eligibility_report=NS(report_id="report-" + sid, eligibility_class="valid_for_training"),
        group_repair_signal=NS(degraded=False),
    )
    write_execution_audit_record(None, audit, directory / "fa_execution_audit.jsonl")
    service = NS(
        orchestrator=NS(audits=[audit]),
        registry=NS(weight_versions={}, stats={}),
        events_path=directory / "bringup_events.jsonl",
    )
    BringupService.record_event(
        service, args=None,
        sample=NS(session_id=sid, index=10, group_index=0, metadata={"instance_id": audit.task_id}),
        result=[], wall_seconds=50.0,
    )
    return audit


def report_from_paths(paths, run_id=None):
    inputs = load_run_inputs(paths)
    return build_run_report(events=inputs["events"], audits=inputs["audits"], run_id=run_id), inputs


def actual_group_events(indices, rewards):
    rows = []
    namespace = {
        "hashlib": hashlib,
        "rh2_event_log": NS(emit=lambda event, **fields: rows.append(dict(event=event, run_id="r1", **fields))),
    }
    extract("reference/miles-rh2-integration/miles/ray/rollout/train_data_conversion.py", "compute_leaf_ordinals", namespace)
    emit = extract("reference/miles-rh2-integration/miles/ray/rollout/rollout_manager.py", "_emit_rollout_evidence", namespace)
    leaves = [NS(
        index=index, rollout_id=index, group_index=0,
        metadata={"instance_id": "task-1"}, get_reward_value=lambda args, reward=reward: reward,
        rollout_routed_experts=None, weight_versions=["5"], tokens=[1, 2],
        status=NS(value="completed"), response_length=1,
    ) for index, reward in zip(indices, rewards, strict=True)]
    emit(NS(servers={}, weight_version=5, args=NS()), 0, [leaves])
    # buffer 的真实成员身份口径同样保留重复 index；此处仅提供对应的终局事件。
    rows.append({"event": "group_consumed", "run_id": "r1", "sample_indices": indices, "group_index": 0})
    return rows


def actual_step_events():
    rows = []
    current_run = ["r1"]
    namespace = {
        "torch": NS(distributed=NS(is_available=lambda: False)),
        "mpu": NS(is_pipeline_last_stage=lambda **kwargs: True),
        "rh2_event_log": NS(emit=lambda event, **fields: rows.append(dict(event=event, run_id=current_run[0], **fields))),
    }
    emit = extract("reference/miles-rh2-integration/miles/backends/megatron_utils/model.py", "_emit_train_step_event", namespace)
    for run, mean in (("r1", 2.0), ("r2", 5.0)):
        current_run[0] = run
        emit(NS(effective_dp=NS(rank=0)), rollout_id=0, step_id=0, attempt=0,
             outcome=NS(name="NORMAL"), optimizer_step_applied=True,
             counts_before=(0, 0), counts_after=(1, 8), grad_norm=1.0,
             duration_seconds=1.0, zero_signal_scan_seconds=0.01,
             loss_reduced={"dis_accepted_tokens": mean}, num_rollouts=8)
        rows.append({"event": "train_step_consumed", "run_id": run, "rollout_id": 0, "step_id": 0,
                     "sample_indices": [10], "leaf_ordinals": [0], "rank": 0, "dp_rank": 0})
    return rows


def tp_copy_probe():
    """只模拟既有 TP 副本的发射基数；不模拟或声称验证 GPU collective。"""
    import torch
    from miles.utils.logprob_compare import masked_compare_entries

    rows = []
    dp = [0]
    namespace = {
        "rh2_event_log": NS(enabled=lambda: True,
                            emit=lambda event, **fields: rows.append(dict(event=event, run_id="r1", **fields))),
        "get_parallel_state": lambda: NS(effective_dp=NS(rank=dp[0])),
        "masked_compare_entries": masked_compare_entries,
    }
    emit_dis = extract("rh2/src/repoharness2/adapters/miles/faithful_dis_loss.py", "_emit_sample_dis_accounting", namespace)
    emit_compare = extract("reference/miles-rh2-integration/miles/backends/megatron_utils/actor.py", "_emit_logprob_compare", namespace)
    for rank, sid, accepted, provenance in ((0, 10, 3, 5), (1, 11, 7, 11)):
        dp[0] = rank
        for _tp_rank in range(2):
            emit_dis({"sample_indices": [sid], "leaf_ordinals": [0]}, per_sample_counts=[(accepted, provenance)])
            emit_compare(NS(weight_updater=NS(weight_version=5)), 0, {
                "sample_indices": [sid], "leaf_ordinals": [0],
                "log_probs": [torch.full((provenance,), -1.0)],
                "rollout_log_probs": [torch.full((provenance,), -1.2)],
                "loss_masks": [[1] * provenance], "weight_versions": [["5"]],
            })
    facets = build_run_report(events=rows, audits=[])["facets"]
    dis = facets["dis_and_support"]["sample_dis_accounting"]
    compare = facets["staleness_and_alignment"]["logprob_compare"]["same_version"]
    return {
        "condition": "TP=2, DP=2；当前默认 TP=1 不触发",
        "actual_accepted_tokens": dis["accepted_tokens_sum"], "expected_accepted_tokens": 10,
        "actual_provenance_tokens": dis["provenance_tokens_sum"], "expected_provenance_tokens": 16,
        "actual_compared_action_tokens": compare["comparable_action_tokens"], "expected_compared_action_tokens": 16,
        "reproduced": dis["accepted_tokens_sum"] == 20 and compare["comparable_action_tokens"] == 32,
    }


def main():
    result = {}
    with tempfile.TemporaryDirectory(prefix="rh2-i20-review-") as temp:
        directory = Path(temp)
        make_audit(directory / "r1", "s-1")
        report, inputs = report_from_paths([directory / "r1"])
        facets = report["facets"]
        lifecycle = facets["throughput_and_resources"]["lifecycle_segments_seconds"]
        real_lifecycle = inputs["audits"][0]["timing_summary"]["lifecycle_timing"]
        result["R1_lifecycle"] = {
            "producer_test_seconds": real_lifecycle["segments_seconds"]["test"],
            "producer_container_start_seconds": real_lifecycle["segments_seconds"]["sandbox_container_start"],
            "actual_test_summary": lifecycle.get("test"),
            "actual_queue_depth_reported_as_seconds": lifecycle["grading_queue_depth_at_enqueue"]["sum"],
            "reproduced": "test" not in lifecycle and lifecycle["grading_queue_depth_at_enqueue"]["sum"] == 7,
        }
        event = json.loads((directory / "r1/bringup_events.jsonl").read_text())
        result["R2_grading"] = {
            "actual_producer_grading": event["grading"],
            "audit_has_grading": "grading" in inputs["audits"][0],
            "reported_attempts_without_grading": facets["execution_and_loss"]["attempts_without_grading"],
            "reported_grading_summary": facets["reward_and_distribution"]["audit_grading"],
            "expected_attempts_without_grading": 0,
            "reproduced": facets["execution_and_loss"]["attempts_without_grading"] == 1,
        }
        make_audit(directory / "r2", "s-2")
        for event_row in actual_step_events():
            file = directory / event_row["run_id"] / "rh2_events_probe.jsonl"
            with file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event_row) + "\n")
        combined, _ = report_from_paths([directory])
        scoped, _ = report_from_paths([directory], run_id="r2")
        c = combined["facets"]
        s = scoped["facets"]
        actual_total = c["dis_and_support"]["totals_restored"]["dis_accepted_tokens"]
        result["R4_runs"] = {
            "actual_steps": c["optimizer_and_publish"]["train_steps"]["steps"],
            "expected_steps": 2,
            "actual_accepted_tokens": actual_total,
            "expected_accepted_tokens": 56,
            "scoped_r2_accepted_tokens_positive_control": s["dis_and_support"]["totals_restored"]["dis_accepted_tokens"],
            "scoped_r2_audits": s["execution_and_loss"]["attempts_audited"],
            "expected_scoped_r2_audits": 1,
            "reproduced": actual_total == 16 and s["execution_and_loss"]["attempts_audited"] == 2,
        }
    events = actual_group_events([10, 10, 10, 11], [0, 0, 0, 1])
    fanout = build_run_report(events=events, audits=[])["facets"]["reward_and_distribution"]["rollout_groups"]
    control = build_run_report(events=actual_group_events([10, 11], [0, 1]), audits=[])["facets"]["reward_and_distribution"]["rollout_groups"]
    observed = fanout["consumed_member_rewards"]
    result["R3_fanout_reward"] = {
        "producer_group_event": next(row for row in events if row["event"] == "rollout_group"),
        "actual_member_count": observed["count"],
        "expected_member_count": 2,
        "actual_reward_mean": observed["sum"] / observed["count"],
        "expected_reward_mean": 0.5,
        "actual_advantage_signs": fanout["advantage_sign_approximation"],
        "expected_positive_negative_zero": [1, 1, 0],
        "group_join_unmatched_positive_control": fanout["groups_not_matched_to_consumed_event"],
        "single_row_member_count_positive_control": control["consumed_member_rewards"]["count"],
        "reproduced": observed["count"] == 4 and fanout["advantage_sign_approximation"]["negative"] == 3,
    }
    result["R5_conditional_tp_copies"] = tp_copy_probe()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    assert all(case["reproduced"] for case in result.values()), "当前源码未复现至少一个审查反例；应重新核验，不代表修复失败。"


if __name__ == "__main__":
    main()
