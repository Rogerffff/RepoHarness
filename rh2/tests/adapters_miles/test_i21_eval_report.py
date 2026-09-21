"""I21（第五组）：评测点聚合——分母分开、按唯一成员集合核对完整性、模型绑定单列。

Codex I21 审查 R1/R2：`reward=None` 进 miles 默认聚合会在样本指标里 `sum([None])` 崩，且 `eval/<name>`
会把缺失计成 0 分；rollout_id 不是唯一评测调用标识，"全部单一版本"也不等于绑定正确。
"""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest


def _payload(pi, slot, *, cls="graded", outcome="resolved", point="0123abcd4567", target="7", versions=("7",),
             n=2, prompts=2, reason=None, category=None, attempt=None):
    return {
        "schema_id": "rh2.eval_attempt_result.v1",
        "eval": {"eval_point_id": point, "eval_rollout_id": 0, "target_weight_version": target, "dataset": "swe_dev",
                 "dataset_index": 0, "prompt_index": pi, "sample_slot": slot, "n_samples_per_eval_prompt": n, "num_prompts": prompts},
        "task_id": f"task-{pi}", "physical_attempt_id": attempt or f"eval-{point}-d0-p{pi}_m{slot}#p1-aaaaaaaa",
        "result_class": cls, "task_outcome": outcome if cls == "graded" else None,
        "reward": (1.0 if outcome == "resolved" else 0.0) if cls == "graded" else None,
        "grading_failure_category": category, "unavailable_reason": reason, "termination_kind": "completed",
        "turn_weight_versions": list(versions), "model_name": "Qwen/Qwen3-4B", "configured_hf_checkpoint": "/ckpt/hf_step_20",
    }


def _sample(payload):
    return NS(metadata={"rh2_eval_result": payload} if payload is not None else {}, reward=None if payload is None else payload["reward"])


PACKAGE = ["task-0", "task-1"]  # 评测题包 prompts.jsonl 逐行的 task_id（既定题目集合）


def test_three_result_classes_are_counted_apart_with_two_explicit_denominators(world):
    from repoharness2.adapters.miles.eval_report import summarize_eval_samples

    samples = [
        _sample(_payload(0, 0)),
        _sample(_payload(0, 1, outcome="unresolved", category="tests_failed")),
        _sample(_payload(1, 0, cls="reward_unavailable", reason="grading:infra_failure", versions=())),
        _sample(_payload(1, 1, cls="execution_missing", reason="sandbox_crash", versions=())),
    ]
    s = summarize_eval_samples(samples, planned_task_ids=PACKAGE)
    assert (s["planned"], s["received"], s["graded"], s["resolved"], s["unresolved"]) == (4, 4, 2, 1, 1)
    assert (s["reward_unavailable"], s["execution_missing"]) == (1, 1)
    assert s["resolved_rate_graded"] == 0.5 and s["resolved_rate_planned"] == 0.25  # 缺失不被改写成答错，也不被悄悄丢掉
    assert s["unavailable_reasons"] == {"grading:infra_failure": 1, "sandbox_crash": 1}
    assert s["grading_failure_categories"] == {"tests_failed": 1}
    assert s["complete"] is False and s["missing_members"] == []  # 成员齐全，但有评不了分 / 没跑成 → 评测点不完整
    rows = {(r["prompt_index"], r["sample_slot"]): r for r in s["attempts"]}
    assert rows[(1, 1)]["result_class"] == "execution_missing" and rows[(0, 1)]["grading_failure_category"] == "tests_failed"


def test_completeness_checks_the_unique_member_set_not_the_total(world):
    from repoharness2.adapters.miles.eval_report import summarize_eval_samples

    full = [_sample(_payload(pi, slot)) for pi in range(2) for slot in range(2)]
    s = summarize_eval_samples(full, planned_task_ids=PACKAGE)
    assert s["complete"] is True and s["planned_source"] == "eval_package" and s["prompts_not_loaded"] == 0
    assert s["configured_hf_checkpoints"] == ["/ckpt/hf_step_20"] and s["model_names"] == ["Qwen/Qwen3-4B"]

    # 重复一个成员 + 漏掉另一个：总数仍是 4，但成员集合不对
    swapped = [*full[:3], _sample(_payload(0, 0, attempt="eval-x-d0-p0_m0#p1-bbbbbbbb"))]
    s = summarize_eval_samples(swapped, planned_task_ids=PACKAGE)
    assert s["received"] == 4 and s["complete"] is False
    assert s["missing_members"] == [{"task_id": "task-1", "sample_slot": 1}] and s["duplicate_members"] == [{"task_id": "task-0", "sample_slot": 0}]

    # 同一 attempt 的多片叶只算一条结果
    dup_rows = [*full, _sample(_payload(0, 0))]
    s = summarize_eval_samples(dup_rows, planned_task_ids=PACKAGE)
    assert s["received"] == 4 and s["duplicate_attempt_rows"] == 1 and s["complete"] is True

    # 缺载荷的样本、两个评测点混在一次聚合里、宿主事实前后不一致 → 都不是完整评测点
    assert summarize_eval_samples([*full, _sample(None)], planned_task_ids=PACKAGE)["payload_missing"] == 1
    assert summarize_eval_samples([*full, _sample(None)], planned_task_ids=PACKAGE)["complete"] is False
    mixed = [*full[:3], _sample(_payload(1, 1, point="ffffffff0002"))]
    assert summarize_eval_samples(mixed, planned_task_ids=PACKAGE)["mixed_eval_points"] is True
    assert summarize_eval_samples(mixed, planned_task_ids=PACKAGE)["complete"] is False
    inconsistent = [*full[:3], _sample(_payload(1, 1, prompts=3))]
    assert summarize_eval_samples(inconsistent, planned_task_ids=PACKAGE)["host_facts_inconsistent"] is True
    empty = summarize_eval_samples([], planned_task_ids=PACKAGE)
    assert empty["complete"] is False and empty["resolved_rate_planned"] is None  # 连每题样本数都不知道：不推造分母

    # 拿不到题包（计划集合未知）：只有宿主"加载后"的数目，成员齐全也不声称完整
    unknown = summarize_eval_samples(full)
    assert unknown["planned_source"] == "host_loaded_prompts" and unknown["planned"] == 4 and unknown["complete"] is False
    assert unknown["missing_members"] == [] and unknown["prompts_not_loaded"] is None


def test_prompts_dropped_by_the_loader_stay_in_the_denominator(world):
    """Codex I21 实施复核 IR2：题包两题，miles 加载器按长度过滤掉长题、把幸存题重排成 prompt_index=0、
    宿主 num_prompts=1。按存活样本反推会得到"计划一题、完成一题、完整"；既定题目集合必须来自题包。"""

    from repoharness2.adapters.miles.eval_report import summarize_eval_samples

    survivor = _sample(_payload(0, 0, n=1, prompts=1))  # 幸存的是 task-0；宿主事实已是过滤后的口径
    call = {"eval_point_id": "0123abcd4567", "eval_rollout_id": 0, "target_weight_version": "7", "dataset": "swe_dev",
            "dataset_index": 0, "n_samples_per_eval_prompt": 1, "num_prompts": 1, "dispatched": 1}
    s = summarize_eval_samples([survivor], call=call, planned_task_ids=PACKAGE)
    assert (s["planned"], s["received"], s["resolved"]) == (2, 1, 1)
    assert s["complete"] is False and s["missing_members"] == [{"task_id": "task-1", "sample_slot": 0}]
    assert s["planned_prompts"] == 2 and s["host_loaded_prompts"] == 1 and s["prompts_not_loaded"] == 1
    assert s["resolved_rate_planned"] == 0.5 and s["resolved_rate_graded"] == 1.0  # 长题留在分母里
    assert s["binding"] == "verified"  # 绑定与完整性是两件事

    # 全部被过滤：零样本，靠调用级宿主事实仍有唯一评测点；未完成、绑定未知、没有任何 0 分
    gone = summarize_eval_samples([], call={**call, "num_prompts": 0, "dispatched": 0}, planned_task_ids=PACKAGE)
    assert gone["eval_point_ids"] == ["0123abcd4567"] and (gone["planned"], gone["received"], gone["graded"]) == (2, 0, 0)
    assert gone["complete"] is False and gone["binding"] == "unverified" and gone["prompts_not_loaded"] == 2
    assert gone["resolved_rate_graded"] is None and gone["resolved_rate_planned"] == 0.0 and gone["unresolved"] == 0
    assert [m["task_id"] for m in gone["missing_members"]] == PACKAGE


@pytest.mark.parametrize(
    ("kw", "binding"),
    [
        ({}, "verified"),
        ({"versions": ("6",)}, "mismatch"),                # 全部单一版本，但不是目标版本——单一不等于绑定正确
        ({"versions": ("6", "7")}, "mismatch"),
        ({"target": None}, "unverified"),                   # 宿主没给目标版本（独立作业 / 首次发布前）
        ({"versions": ()}, "unverified"),                   # 评了分却没有版本事实
    ],
)
def test_model_binding_verdict(world, kw, binding):
    from repoharness2.adapters.miles.eval_report import summarize_eval_samples

    s = summarize_eval_samples([_sample(_payload(pi, slot, **kw)) for pi in range(2) for slot in range(2)], planned_task_ids=PACKAGE)
    assert s["binding"] == binding
    assert s["complete"] is True  # 完整性与绑定是两件事，分别给出


def _package_args(tmp_path, task_ids=PACKAGE, name="swe_dev"):
    import json

    path = tmp_path / "prompts.jsonl"
    path.write_text("".join(json.dumps({"prompt": "p", "label": tid, "metadata": {"task_id": tid}}) + "\n" for tid in task_ids), encoding="utf-8")
    return NS(eval_datasets=[NS(name=name, path=str(path), metadata_key="metadata")], metadata_key="metadata")


def test_hook_takes_over_logging_only_for_rh2_eval_payloads(world, monkeypatch, tmp_path):
    from repoharness2.adapters.miles import eval_report as er

    events, tracked = [], []
    monkeypatch.setattr(er, "_emit_event", lambda kind, **f: events.append((kind, f)) or True)
    monkeypatch.setattr(er, "_log_tracking", lambda args, rollout_id, metrics: tracked.append((rollout_id, metrics)))
    args = _package_args(tmp_path)

    # 非 RH2 formal 评测（s1_compat 占位：有样本、没有载荷）→ 不接管，miles 默认日志照旧
    assert er.log_eval_rollout_data(3, args, {"swe_dev": {"samples": [NS(metadata={}, reward=1.0)]}}, None) is False
    assert events == [] and tracked == []

    samples = [_sample(_payload(0, 0, n=1, prompts=2)), _sample(_payload(1, 0, n=1, prompts=2, cls="reward_unavailable", reason="grading:infra_failure", versions=()))]
    assert er.log_eval_rollout_data(3, args, {"swe_dev": {"samples": samples, "rewards": [1.0, None]}}, {"eval/lag_steps": 0}) is True
    ((kind, fields),) = events
    assert kind == "eval_point" and fields["rollout_id"] == 3 and fields["dataset"] == "swe_dev"
    assert fields["eval_point_ids"] == ["0123abcd4567"] and fields["complete"] is False and fields["reward_unavailable"] == 1
    ((rollout_id, metrics),) = tracked
    assert rollout_id == 3 and metrics["eval/lag_steps"] == 0
    assert metrics["eval/swe_dev/planned"] == 2 and metrics["eval/swe_dev/graded"] == 1
    assert metrics["eval/swe_dev/resolved_rate_graded"] == 1.0 and metrics["eval/swe_dev/resolved_rate_planned"] == 0.5
    assert metrics["eval/swe_dev/complete"] == 0 and "eval/swe_dev" not in metrics  # 不产出含糊的单一准确率
    assert fields["planned_source"] == "eval_package" and metrics["eval/swe_dev/missing_members"] == 0


def test_hook_takes_over_an_empty_eval_call_instead_of_letting_the_default_logger_divide_by_zero(world, monkeypatch, tmp_path):
    """IR2 全部过滤：零样本时此前返回 False → miles 默认日志对空列表除零 → 共享引擎形态下停训练驱动。"""

    from repoharness2.adapters.miles import eval_report as er

    events, tracked = [], []
    monkeypatch.setattr(er, "_emit_event", lambda kind, **f: events.append((kind, f)) or True)
    monkeypatch.setattr(er, "_log_tracking", lambda args, rollout_id, metrics: tracked.append(metrics))
    call = {"eval_point_id": "0123abcd4567", "eval_rollout_id": 4, "target_weight_version": "9", "dataset": "swe_dev",
            "dataset_index": 0, "n_samples_per_eval_prompt": 1, "num_prompts": 0, "dispatched": 0}
    data = {"swe_dev": {"rewards": [], "truncated": [], "samples": [], "rh2_eval_call": call}}
    assert er.log_eval_rollout_data(4, _package_args(tmp_path), data, None) is True
    ((_, fields),) = events
    assert fields["eval_point_ids"] == ["0123abcd4567"] and fields["planned"] == 2 and fields["received"] == 0
    assert fields["complete"] is False and fields["binding"] == "unverified" and fields["prompts_not_loaded"] == 2
    (metrics,) = tracked
    assert metrics["eval/swe_dev/missing_members"] == 2 and "eval/swe_dev/resolved_rate_graded" not in metrics

    # 题包文件读不到 → 计划集合未知：仍不崩、不声称完整
    events.clear()
    assert er.log_eval_rollout_data(4, NS(eval_datasets=[NS(name="swe_dev", path=str(tmp_path / "missing.jsonl"))]), data, None) is True
    assert events[0][1]["planned_source"] == "host_loaded_prompts" and events[0][1]["complete"] is False
    assert er.planned_task_ids_for(_package_args(tmp_path), "other") is None
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"prompt": "p", "metadata": {}}\n', encoding="utf-8")
    assert er.planned_task_ids_for(NS(eval_datasets=[NS(name="swe_dev", path=str(bad))]), "swe_dev") is None  # 不是 prepared 产物形状


def test_all_missing_point_has_no_graded_rate_and_never_a_zero_score(world):
    from repoharness2.adapters.miles.eval_report import eval_point_metrics, summarize_eval_samples

    s = summarize_eval_samples([_sample(_payload(pi, 0, n=1, cls="execution_missing", reason="harness_crash", versions=())) for pi in range(2)], planned_task_ids=PACKAGE)
    assert s["graded"] == 0 and s["resolved_rate_graded"] is None and s["resolved_rate_planned"] == 0.0
    metrics = eval_point_metrics("swe_dev", s)
    assert "eval/swe_dev/resolved_rate_graded" not in metrics and metrics["eval/swe_dev/execution_missing"] == 2
