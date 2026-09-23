"""I21 IR1–IR3 修复独立复核。保留旧探针不动；本文件验证带真实题包的日志运输。

从 rh2/ 运行，RH2_MILES_PATH 指向 miles-rh2-integration。CPU，设备替身同上一轮。
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import importlib.util
import json
import logging
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
from unittest.mock import patch
import uuid

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/src/repoharness2").is_dir())
PREVIOUS = Path(__file__).resolve().parent.parent / "i21_implementation_review_20260920/probe.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


old = load_module("i21_previous_probe", PREVIOUS)


def outer_logger(args, data, er):
    """真实 miles 日志函数 → 真实 RH2 钩子，args 带评测题包；只替换外部日志输出。"""
    events, tracking = [], []
    env = dict(logger=logging.getLogger("i21-followup"), load_function=lambda _: er.log_eval_rollout_data,
               compute_rollout_step=lambda *a: 0, tracking=NS(log=lambda *a, **kw: None),
               dict_add_prefix=lambda d, p: {p + k: v for k, v in d.items()},
               _compute_metrics_from_samples=lambda *a: {})
    old.load_nodes("reference/miles-rh2-integration/miles/ray/rollout/metrics.py", ("log_eval_rollout_data",), env)
    with patch.object(er, "_emit_event", lambda kind, **f: events.append({"event": kind, **f})), \
         patch.object(er, "_log_tracking", lambda *a: tracking.append(a[2])):
        result = env["log_eval_rollout_data"](0, args, data)
    assert result is None and len(events) == len(data) and len(tracking) == 1
    return events, tracking[0]


async def package_eval(world, directory, *, lengths, n=1, unavailable_second=False, unreadable_plan=False):
    from miles.utils.data import Dataset
    from miles.utils.eval_config import EvalDatasetConfig
    from repoharness2.adapters.miles import eval_report as er
    from repoharness2.adapters.miles.identity import mint_eval_attempt_identity
    from repoharness2.adapters.slime.eval_wiring import EVAL_REPORT_HOOK_PATH, validate_eval_wiring
    from test_i21_eval_entry import _load_face, prepare_synthetic

    fx = prepare_synthetic(directory)
    face = _load_face(fx)
    planned_ids = [json.loads(line)["metadata"]["task_id"] for line in fx.prompts_path.read_text().splitlines() if line.strip()]
    assert len(planned_ids) == len(face.task_ids()) == 2
    cfg = EvalDatasetConfig(name="review", path=str(fx.prompts_path), input_key="prompt", label_key="label",
                            metadata_key="metadata", n_samples_per_eval_prompt=n, temperature=1.0,
                            top_p=1.0, top_k=-1, max_response_len=128)
    args = NS(group_rm=False, eval_datasets=[cfg], hf_checkpoint="fixture", apply_chat_template=False,
              chat_template_path=None, eval_reward_key=None, reward_key=None, sglang_enable_deterministic_inference=False,
              eval_max_prompt_len=10, multimodal_keys=None, apply_chat_template_kwargs={}, eval_interval=1,
              custom_eval_rollout_log_function_path=EVAL_REPORT_HOOK_PATH, log_passrate=False)
    wiring = validate_eval_wiring(args, execution_mode="fa_formal", eval_only=False,
                                 eval_prepared_dir=str(fx.prepared_dir), eval_host_grading_path=str(fx.host_path),
                                 eval_host_grading_sha256=fx.manifest.host_grading_artifact_sha256)
    assert wiring.enabled

    async def generate(state, sample, sampling_params, evaluation):
        identity = mint_eval_attempt_identity(sample)
        unavailable = unavailable_second and sample.metadata["task_id"] == planned_ids[1]
        sample.reward = None if unavailable else 1.0
        sample.response = ""
        sample.status = world.MS.Status.ABORTED if unavailable else world.MS.Status.COMPLETED
        sample.metadata["rh2_eval_result"] = {
            "physical_attempt_id": identity["rh2_physical_attempt_id"], "eval": sample.metadata["rh2_eval_dispatch"],
            "task_id": sample.metadata["task_id"], "result_class": "reward_unavailable" if unavailable else "graded",
            "task_outcome": None if unavailable else "resolved", "reward": sample.reward,
            "unavailable_reason": "grading:infra_failure" if unavailable else None, "turn_weight_versions": ["7"],
        }
        return sample

    def tokenizer(texts, **kw):
        return {"input_ids": [[0] * lengths[i] for i, _ in enumerate(texts)]}

    namespace = dict(asyncio=asyncio, copy=copy, uuid=uuid, logger=logging.getLogger("i21-followup"), tqdm=old.Progress,
                     as_completed_async=old.completed, generate_and_rm=generate, Dataset=Dataset, Sample=world.MS,
                     compute_sampling_params=lambda *a, **kw: kw, policy_uses_routing_key=lambda _: False,
                     load_tokenizer=lambda *a, **kw: tokenizer, load_processor=lambda *a, **kw: None,
                     RH2_EVAL_DISPATCH_METADATA_KEY="rh2_eval_dispatch", RH2_EVAL_CALL_RESULT_KEY="rh2_eval_call")
    old.load_nodes("reference/miles-rh2-integration/miles/rollout/inference_rollout/inference_rollout_eval.py",
                   ("run_eval_datasets", "eval_rollout_single_dataset"), namespace)
    data = await namespace["run_eval_datasets"](NS(args=args), {}, rollout_id=0, weight_version="7")
    call = data["review"]["rh2_eval_call"]
    # 不改写已经验证的题包；只在这个故障场景给日志消费端提供一个不存在的路径。
    if unreadable_plan:
        args = copy.copy(args)
        args.eval_datasets = [NS(name="review", path=str(directory / "absent.jsonl"), metadata_key="metadata")]
    events, tracking = outer_logger(args, data, er)
    summary = events[0]
    loaded = sum(length <= 10 for length in lengths)
    assert summary["eval_point_ids"] == [call["eval_point_id"]]
    assert call["num_prompts"] == loaded and call["dispatched"] == loaded * n
    assert summary["received"] == loaded * n
    assert summary["unresolved"] == 0
    assert summary["planned_source"] == ("host_loaded_prompts" if unreadable_plan else "eval_package")
    assert summary["complete"] is (loaded == 2 and not unavailable_second and not unreadable_plan)
    assert summary["binding"] == ("verified" if loaded else "unverified")
    assert "eval/review" not in tracking
    if unreadable_plan:
        assert summary["prompts_not_loaded"] is None
    else:
        expected_missing = [{"task_id": planned_ids[i], "sample_slot": slot}
                            for i, length in enumerate(lengths) if length > 10 for slot in range(n)]
        assert sorted(summary["missing_members"], key=str) == sorted(expected_missing, key=str)
        assert summary["planned"] == 2 * n and summary["prompts_not_loaded"] == 2 - loaded
    if not loaded:
        assert data["review"]["rewards"] == []
        assert summary["graded"] == 0 and summary["resolved_rate_graded"] is None
        assert "eval/review/resolved_rate_graded" not in tracking
        assert summary["resolved_rate_planned"] == 0.0  # 计划完成比例下界，不是模型准确率或伪造样本 reward
    if unavailable_second:
        assert data["review"]["rewards"] == [1.0, None]
        assert summary["reward_unavailable"] == 1 and summary["resolved_rate_planned"] == 0.5
    return {"lengths": lengths, "call": call, "summary": summary, "rewards": data["review"]["rewards"],
            "tracking": tracking, "logging_error": None}


def regrade_cases():
    from repoharness2.adapters.miles.run_report import build_run_report

    def event(run, trajectory, op):
        return {"event": "grading_regrade", "run_id": run, "_bundle": run, "trajectory_id": trajectory,
                "op": op, "category": "daemon_connect", "attempt": 1}

    def audit(run, trajectory, evaluation):
        # audit 的 run 归属来自同一个输入 bundle 中的事件；不由随手加入的 run_id 字段决定。
        row = {"_bundle": run, "trajectory_id": trajectory}
        if evaluation:
            row["evaluation"] = {"eval": {"eval_point_id": "0123abcd4567", "dataset": "review", "eval_rollout_id": 0},
                                 "result_class": "graded", "task_outcome": "resolved"}
        return row

    events = [event("r1", "train", "exec"), event("r1", "eval", "run"), event("r1", "missing", "inspect")]
    audits = [audit("r1", "train", False), audit("r1", "eval", True)]
    report = build_run_report(events=events, audits=audits, run_id="r1")
    train = report["facets"]["execution_and_loss"]["grading_regrades"]
    evaluated = report["facets"]["evaluation"]["grading_regrades"]
    assert train["events"] == evaluated["events"] == train["unattributed_events"] == 1

    # 同一 trajectory 名在另一个 run 中属于评测，不得串到本 run 的训练事件。
    cross = build_run_report(events=[event("r1", "same", "exec"), event("r2", "same", "run")],
                             audits=[audit("r1", "same", False), audit("r2", "same", True)], run_id="r1")
    assert cross["facets"]["execution_and_loss"]["grading_regrades"]["events"] == 1
    assert cross["facets"]["evaluation"]["grading_regrades"]["events"] == 0
    return {"training": train, "evaluation": evaluated,
            "cross_run_training": cross["facets"]["execution_and_loss"]["grading_regrades"],
            "cross_run_evaluation": cross["facets"]["evaluation"]["grading_regrades"]}


def main():
    sys.path[:0] = [str(ROOT / "rh2/tests/adapters_miles"), str(ROOT / "rh2/tests"), str(ROOT / "rh2/tests/adapters")]
    fixtures = load_module("i21_followup_fixtures", ROOT / "rh2/tests/adapters_miles/conftest.py")
    fixture = fixtures._vendor_slime_world.__wrapped__()
    next(fixture)
    world = fixtures._World()
    world.install_sglang_stub()
    result = {"scope": "CPU；真实 prepared/加载过滤/派发函数体/RH2 编排/canonicalize/外层日志；设备为替身"}
    with tempfile.TemporaryDirectory(prefix="i21-fix-review-") as directory:
        directory = Path(directory)
        for name, train_p, unsafe in (("unsafe_top_p_equal", 1.0, True), ("unsafe_top_p_different", .95, True),
                                     ("graded_top_p_different", .95, False)):
            observed = asyncio.run(old.unsafe_delivery(world, directory / name, train_p, unsafe=unsafe))
            assert observed["error"] is None and observed["live_assignments"] == 0
            assert observed["reward"] == (None if unsafe else 1.0)
            assert observed["grading_calls"] == (0 if unsafe else 1)
            assert observed["result_class"] == ("reward_unavailable" if unsafe else "graded")
            result[name] = observed
        cases = (
            ("unfiltered", {"lengths": (1, 1)}),
            ("one_filtered", {"lengths": (1, 100)}),
            ("all_filtered", {"lengths": (20, 100)}),
            ("first_filtered_two_slots", {"lengths": (100, 1), "n": 2}),
            ("unreadable_plan", {"lengths": (1, 100), "unreadable_plan": True}),
            ("mixed_reward", {"lengths": (1, 1), "unavailable_second": True}),
        )
        for name, options in cases:
            result[name] = asyncio.run(package_eval(world, directory / name, **options))
        assert len({result[name]["call"]["eval_point_id"] for name, _ in cases}) == len(cases)
        result["eval_only_regrade"] = old.regrade_report()
        assert result["eval_only_regrade"]["train_grading_regrades"]["events"] == 0
        result["mixed_regrades"] = regrade_cases()
    for relative in json.loads(PREVIOUS.with_name("results.json").read_text())["source_sha256"]:
        old.SOURCES[relative] = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    result["source_sha256"] = old.SOURCES
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
