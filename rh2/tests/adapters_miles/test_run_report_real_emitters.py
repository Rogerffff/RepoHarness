"""I20（Codex 09-11 复核 R3/R4）：用 fork **原函数**（AST 提取执行，避开 Ray / Megatron 导入）产生 rollout_group 与
train_step 事件，喂给真实报告工具——成员归并与 run 去重必须对真实 emitter 形状成立。integration_base：读取集成树源码。"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

pytestmark = pytest.mark.integration_base


def _extract(path: Path, name: str, namespace: dict):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    unit = ast.Module(body=ast.parse("from __future__ import annotations").body + [node], type_ignores=[])
    exec(compile(ast.fix_missing_locations(unit), str(path), "exec"), namespace)  # noqa: S102 —— 只执行仓库内的指定函数
    return namespace[name]


def _miles_root() -> Path:
    import miles

    return Path(miles.__file__).resolve().parent


def _real_rollout_group_rows(indices, rewards, *, run="r1"):
    rows: list[dict] = []
    namespace = {"hashlib": hashlib, "rh2_event_log": NS(emit=lambda event, **fields: rows.append(dict(event=event, run_id=run, _bundle=0, **fields)))}
    _extract(_miles_root() / "ray/rollout/train_data_conversion.py", "compute_leaf_ordinals", namespace)
    emit = _extract(_miles_root() / "ray/rollout/rollout_manager.py", "_emit_rollout_evidence", namespace)
    leaves = [NS(index=index, rollout_id=index, group_index=0, metadata={"instance_id": "task-1"},
                 get_reward_value=lambda args, reward=reward: reward, rollout_routed_experts=None, weight_versions=["5"],
                 tokens=[1, 2], status=NS(value="completed"), response_length=1)
              for index, reward in zip(indices, rewards, strict=True)]
    emit(NS(servers={}, weight_version=5, args=NS()), 0, [leaves])
    rows.append({"event": "group_consumed", "run_id": run, "_bundle": 0, "sample_indices": list(indices), "group_index": 0})
    return rows


def _real_train_step_rows(spec):
    rows: list[dict] = []
    current = {"run": None, "bundle": 0}
    namespace = {"torch": NS(distributed=NS(is_available=lambda: False)), "mpu": NS(is_pipeline_last_stage=lambda **kw: True),
                 "rh2_event_log": NS(emit=lambda event, **fields: rows.append(dict(event=event, run_id=current["run"], _bundle=current["bundle"], **fields)))}
    emit = _extract(_miles_root() / "backends/megatron_utils/model.py", "_emit_train_step_event", namespace)
    for run, bundle, mean in spec:
        current.update(run=run, bundle=bundle)
        emit(NS(effective_dp=NS(rank=0)), rollout_id=0, step_id=0, attempt=0, outcome=NS(name="NORMAL"), optimizer_step_applied=True,
             counts_before=(0, 0), counts_after=(1, 8), grad_norm=1.0, duration_seconds=1.0, zero_signal_scan_seconds=0.01,
             loss_reduced={"dis_accepted_tokens": mean}, num_rollouts=8)
    return rows


def test_real_emitter_fanout_rows_merge_into_two_members(world):
    from repoharness2.adapters.miles.run_report import build_run_report

    rows = _real_rollout_group_rows([10, 10, 10, 11], [0.0, 0.0, 0.0, 1.0])
    (group_row,) = [r for r in rows if r["event"] == "rollout_group"]
    assert group_row["sample_indices"] == [10, 10, 10, 11] and group_row["leaf_ordinals"] == [0, 1, 2, 0]  # 真实 emitter 形状
    dg = build_run_report(events=rows, audits=[])["facets"]["reward_and_distribution"]["delivered_groups"]
    assert dg["members"] == 2 and dg["training_rows"] == 4 and dg["member_rewards"]["sum"] == 1.0 and dg["member_rewards"]["count"] == 2
    assert dg["advantage_sign_approximation"] == {"positive": 1, "negative": 1, "zero": 0, "note": dg["advantage_sign_approximation"]["note"]}
    assert dg["groups_not_matched_to_consumed_event"] == 0
    control = build_run_report(events=_real_rollout_group_rows([10, 11], [0.0, 1.0]), audits=[])["facets"]["reward_and_distribution"]["delivered_groups"]
    assert control["members"] == 2 and control["member_rewards"] == dg["member_rewards"]  # 正控（各一行）与分行同成员统计


def test_real_emitter_same_step_id_in_two_runs_stays_two_steps(world):
    from repoharness2.adapters.miles.run_report import build_run_report

    rows = _real_train_step_rows([("r1", 0, 2.0), ("r2", 1, 5.0)])
    assert all(r["metrics"] == {"dis_accepted_tokens": r["metrics"]["dis_accepted_tokens"]} for r in rows) and len(rows) == 2
    combined = build_run_report(events=rows, audits=[])
    assert combined["multi_run"] is True
    totals = {rid: sub["facets"]["dis_and_support"]["totals_restored"]["dis_accepted_tokens"] for rid, sub in combined["per_run"].items()}
    assert totals == {"r1": 16.0, "r2": 40.0}  # 2×8 与 5×8，不是合并成 1 step / 16
    scoped = build_run_report(events=rows, audits=[], run_id="r2")
    assert scoped["facets"]["dis_and_support"]["totals_restored"]["dis_accepted_tokens"] == 40.0 and scoped["facets"]["dis_and_support"]["steps_seen"] == 1
