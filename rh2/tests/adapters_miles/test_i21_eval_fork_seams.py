"""I21（第五组）：集成分支 patch 0018 的真实接缝——用 fork **原函数**（AST 提取执行，避开 Ray / sglang /
transformers 导入）验证宿主侧评测派发事实、共享引擎 eval 的暂停/恢复与窗口事件、目标权重版本透传。
integration_base：读取集成树源码（lane B）；lane A（stock pin 树）没有这些接缝，formal 评测在那里直接拒绝。
"""

from __future__ import annotations

import ast
import asyncio
import copy
import logging
import uuid
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

pytestmark = pytest.mark.integration_base


def _miles_root() -> Path:
    import miles

    return Path(miles.__file__).resolve().parent


def _extract(path: Path, names: tuple[str, ...], namespace: dict, *, cls: str | None = None) -> dict:
    """把指定函数 / 方法节点原样编译进 namespace（方法按普通函数取出，第一个参数仍是 self）。"""

    tree = ast.parse(path.read_text(encoding="utf-8"))
    scope = tree.body if cls is None else next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls).body
    nodes = [n for n in scope if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    assert {n.name for n in nodes} == set(names), f"{path.name}: 找不到 {set(names) - {n.name for n in nodes}}"
    unit = ast.Module(body=ast.parse("from __future__ import annotations").body + nodes, type_ignores=[])
    exec(compile(ast.fix_missing_locations(unit), str(path), "exec"), namespace)  # noqa: S102 —— 只执行仓库内指定函数
    return namespace


def _module_constants(path: Path) -> dict:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Constant):
            out[node.targets[0].id] = node.value.value
    return out


class _Tqdm:
    def __init__(self, *a, **k): ...
    def update(self, n): ...
    def close(self): ...


async def _as_completed_async(tasks):
    for fut in asyncio.as_completed(tasks):
        yield await fut


def _eval_runner(world, *, prompts: int, n: int, row_metadata: dict | None = None, dataset_name: str = "swe dev"):
    from miles.utils.eval_config import EvalDatasetConfig

    seen: list = []

    async def generate_and_rm(state, sample, sampling_params, evaluation):
        assert evaluation is True
        seen.append(sample)
        sample.reward = 1.0
        return sample

    namespace = {
        "asyncio": asyncio, "copy": copy, "uuid": uuid, "logger": logging.getLogger("i21-test"), "tqdm": _Tqdm,
        "as_completed_async": _as_completed_async, "generate_and_rm": generate_and_rm,
        "compute_sampling_params": lambda args, **kw: {"temperature": 1.0},
        "policy_uses_routing_key": lambda args: False, "Sample": world.MS,
        "load_tokenizer": None, "load_processor": None, "Dataset": None,
        "RH2_EVAL_DISPATCH_METADATA_KEY": "rh2_eval_dispatch", "RH2_EVAL_CALL_RESULT_KEY": "rh2_eval_call",
    }
    src = _miles_root() / "rollout/inference_rollout/inference_rollout_eval.py"
    _extract(src, ("run_eval_datasets", "eval_rollout_single_dataset"), namespace)
    cfg = EvalDatasetConfig(name=dataset_name, path="/data/eval/prompts.jsonl", n_samples_per_eval_prompt=n, metadata_key="metadata")
    args = NS(group_rm=False, eval_datasets=[cfg], hf_checkpoint="ckpt", apply_chat_template=False, chat_template_path=None,
              eval_reward_key=None, reward_key=None, sglang_enable_deterministic_inference=False)
    rows = [world.mk_miles_input(index=None, group_index=None) for _ in range(prompts)]
    for i, row in enumerate(rows):
        row.metadata = {"task_id": f"task-{i}", **(row_metadata or {})}
        row.response = ""
    cache = {cfg.cache_key + ("ckpt", False, None): NS(samples=rows)}
    return namespace["run_eval_datasets"], NS(args=args), cache, seen


def test_integration_tree_declares_the_host_stamp_marker(world):
    constants = _module_constants(_miles_root() / "rollout/inference_rollout/inference_rollout_eval.py")
    assert constants["RH2_EVAL_DISPATCH_HOST_STAMP"] is True
    assert constants["RH2_EVAL_DISPATCH_METADATA_KEY"] == "rh2_eval_dispatch"  # 与 rh2 identity.EVAL_DISPATCH_METADATA_KEY 同键
    assert constants["RH2_EVAL_CALL_RESULT_KEY"] == "rh2_eval_call"  # patch 0019：与 rh2 eval_report.EVAL_CALL_RESULT_KEY 同键
    from repoharness2.adapters.miles import eval_report as er
    from repoharness2.adapters.miles import identity as idm

    assert idm.EVAL_DISPATCH_METADATA_KEY == constants["RH2_EVAL_DISPATCH_METADATA_KEY"]
    assert er.EVAL_CALL_RESULT_KEY == constants["RH2_EVAL_CALL_RESULT_KEY"]


async def test_real_eval_runner_stamps_host_facts_that_override_dataset_supplied_ones(world):
    from repoharness2.adapters.miles import identity as idm

    forged = {"rh2_eval_dispatch": {"eval_point_id": "deadbeefdead", "prompt_index": 99}}  # 数据集 JSON 自报，必须被覆盖
    run, state, cache, seen = _eval_runner(world, prompts=2, n=2, row_metadata=forged)
    data = await run(state, cache, rollout_id=0, weight_version="7", hf_dir=None)
    assert list(data) == ["swe dev"] and len(data["swe dev"]["samples"]) == 4
    call = data["swe dev"]["rh2_eval_call"]  # 调用级事实：没有任何样本存活时评测点身份的唯一来源
    assert call["num_prompts"] == 2 and call["dispatched"] == 4 and call["n_samples_per_eval_prompt"] == 2
    assert call["eval_rollout_id"] == 0 and call["target_weight_version"] == "7" and call["dataset"] == "swe dev"
    facts = [s.metadata["rh2_eval_dispatch"] for s in sorted(seen, key=lambda s: s.index)]
    points = {f["eval_point_id"] for f in facts}
    assert points == {call["eval_point_id"]}
    assert len(points) == 1 and "deadbeefdead" not in points  # 一次调用一个评测点，宿主生成
    assert [(f["prompt_index"], f["sample_slot"]) for f in facts] == [(0, 0), (0, 1), (1, 0), (1, 1)]
    assert all(f["eval_rollout_id"] == 0 and f["target_weight_version"] == "7" and f["dataset"] == "swe dev"
               and f["dataset_index"] == 0 and f["n_samples_per_eval_prompt"] == 2 and f["num_prompts"] == 2 for f in facts)
    assert all(s.metadata["task_id"].startswith("task-") and s.group_index is None for s in seen)  # 任务键保留；没有训练组事实

    # rh2 消费者直接认这份事实：四个样本四个不同的评测身份
    executions = {idm.mint_eval_attempt_identity(s)[idm.EXECUTION_ID_KEY] for s in seen}
    assert len(executions) == 4 and all(e.startswith(f"eval-{next(iter(points))}-d0-p") for e in executions)

    # 同一 rollout_id 的第二次调用（训练前 r0 vs 第 0 步之后 r0）= 另一个评测点
    run2, state2, cache2, seen2 = _eval_runner(world, prompts=2, n=2)
    await run2(state2, cache2, rollout_id=0, weight_version="8")
    assert {s.metadata["rh2_eval_dispatch"]["eval_point_id"] for s in seen2}.isdisjoint(points)
    # 旧调用形状（不传派发事实）仍可用：rollout_id / 目标版本如实为 None
    run3, state3, cache3, seen3 = _eval_runner(world, prompts=1, n=1)
    await run3(state3, cache3)
    assert seen3[0].metadata["rh2_eval_dispatch"]["eval_rollout_id"] is None and seen3[0].metadata["rh2_eval_dispatch"]["target_weight_version"] is None


class _FakeGroupTask:
    """在飞训练组 task 的替身（真实对象是 asyncio.Task：可哈希、有 done()）。"""

    def __init__(self, done: bool) -> None:
        self._done = done

    def done(self) -> bool:
        return self._done


def _call_eval_harness(*, active_done: tuple[bool, ...], fail: bool):
    events, calls = [], []

    async def run_eval_datasets(state, cache, **kw):
        calls.append({"state": state, **kw, "paused": not owner._producer_resumed.is_set()})
        if fail:
            raise RuntimeError("eval wiring exploded")
        return {"swe_dev": {"rewards": [1.0]}}

    namespace = {
        "run_eval_datasets": run_eval_datasets, "RolloutFnEvalOutput": lambda data: NS(data=data), "logger": logging.getLogger("i21-test"),
        "rh2_event_log": NS(enabled=lambda: True, emit=lambda kind, **f: events.append((kind, f)), EVAL_WINDOW_EVENT="eval_window"),
    }
    _extract(_miles_root() / "rollout/fully_async_rollout.py", ("_call_eval", "_emit_eval_window"), namespace, cls="FullyAsyncRolloutFn")
    owner = NS(state="train-state", _eval_prompt_dataset_cache={}, _producer_resumed=asyncio.Event(),
               _active_groups={_FakeGroupTask(d) for d in active_done})
    owner._producer_resumed.set()
    owner._emit_eval_window = lambda *a, **k: namespace["_emit_eval_window"](owner, *a, **k)
    return namespace["_call_eval"], owner, events, calls


async def test_shared_engine_eval_pauses_new_submissions_only_and_records_the_window(world):
    call_eval, owner, events, calls = _call_eval_harness(active_done=(False, False, True), fail=False)
    out = await call_eval(owner, NS(generate_state=None, rollout_id=20, weight_version="20", hf_dir=None))
    assert out.data == {"swe_dev": {"rewards": [1.0]}}
    (call,) = calls
    assert call["paused"] is True and call["state"] == "train-state"  # eval 期间 producer 处于暂停
    assert (call["rollout_id"], call["weight_version"], call["hf_dir"]) == (20, "20", None)  # 派发事实透传给 eval runner
    assert owner._producer_resumed.is_set()  # 结束后恢复
    assert events == [
        ("eval_window", {"rollout_id": 20, "phase": "start", "active_groups": 2, "ok": None}),  # 在飞组没有被排空
        ("eval_window", {"rollout_id": 20, "phase": "end", "active_groups": 2, "ok": True}),
    ]


async def test_shared_engine_eval_failure_resumes_the_producer_and_propagates(world):
    call_eval, owner, events, _ = _call_eval_harness(active_done=(False,), fail=True)
    with pytest.raises(RuntimeError, match="eval wiring exploded"):  # 不降级成 skip：run-fatal / 接线错误照常停驱动
        await call_eval(owner, NS(generate_state=None, rollout_id=5, weight_version=None, hf_dir=None))
    assert owner._producer_resumed.is_set()
    assert [e[1]["phase"] for e in events] == ["start", "end"] and events[1][1]["ok"] is False


async def test_dedicated_state_eval_passes_facts_without_touching_the_producer(world):
    call_eval, owner, events, calls = _call_eval_harness(active_done=(), fail=False)
    await call_eval(owner, NS(generate_state="fleet-state", rollout_id=7, weight_version="7", hf_dir="/ckpt/step_7"))
    assert calls[0]["state"] == "fleet-state" and calls[0]["paused"] is False and calls[0]["hf_dir"] == "/ckpt/step_7"
    assert events == []  # 窗口事件只属于共享引擎形态


async def test_rollout_manager_shared_branch_reports_the_published_version_as_the_eval_target(world):
    world.install_sglang_stub()
    from miles.rollout.base_types import RolloutFnEvalInput

    seen_inputs, emitted = [], []

    class _Timer:
        def __init__(self, name): ...
        def __enter__(self): return self
        def __exit__(self, *exc): return False

    namespace = {
        "asyncio": asyncio, "timer": _Timer, "RolloutFnEvalInput": RolloutFnEvalInput,
        "call_rollout_function": lambda fn, eval_input: (seen_inputs.append(eval_input), NS(data={"d": {}}, metrics=None))[1],
        "call_rollout_fn": None, "save_debug_rollout_data": lambda *a, **k: None,
        "log_eval_rollout_data": lambda *a, **k: None,  # rh2 钩子接管时 miles 聚合返回 None
        "rh2_event_log": NS(emit=lambda kind, **f: emitted.append((kind, f))),
    }
    _extract(_miles_root() / "ray/rollout/rollout_manager.py", ("eval",), namespace, cls="RolloutManager")
    for version, expected in ((7, "7"), (None, None)):
        manager = NS(args=NS(debug_train_only=False, eval_uses_snapshots=False), _health_monitoring_resume=lambda: None,
                     use_legacy_rollout_v1=False, eval_generate_rollout=object(), weight_version=version, _metric_checker=None)
        await namespace["eval"](manager, 3)
        assert seen_inputs[-1].rollout_id == 3 and seen_inputs[-1].weight_version == expected and seen_inputs[-1].evaluation is True
    assert [kind for kind, _ in emitted] == ["eval_smoke", "eval_smoke"] and emitted[0][1]["num_metrics"] == 0


@pytest.mark.parametrize(
    ("lengths", "loaded", "received", "complete", "missing"),
    [
        ((1, 1), 2, 2, True, []),                       # 不过滤：两题都评
        ((1, 100), 1, 1, False, ["TID2"]),              # 长题被加载器过滤：不得报成"计划一题、完成一题、完整"
        ((20, 100), 0, 0, False, ["TID1", "TID2"]),     # 全部过滤：零样本，不崩、不回落默认日志、没有 0 分
    ],
)
async def test_prompts_filtered_at_dataset_load_never_shrink_the_planned_eval_set(world, tmp_path, monkeypatch, lengths, loaded, received, complete, missing):
    """Codex I21 实施复核 IR2（真实 `Dataset` + `filter_long_prompt` + 真实 eval 派发函数体 + 真实 rh2 钩子）：
    题包两题、`--eval-max-prompt-len 10`，假 tokenizer 只控制两题的长度。"""

    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from w1b_synthetic_tasks import TID1, TID2, prepare_synthetic

    from miles.utils.data import Dataset
    from miles.utils.eval_config import EvalDatasetConfig
    from repoharness2.adapters.miles import eval_report as er
    from repoharness2.adapters.miles import identity as idm

    fx = prepare_synthetic(tmp_path / "evalpkg")
    ids = {"TID1": TID1, "TID2": TID2}

    async def generate_and_rm(state, sample, sampling_params, evaluation):
        minted = idm.mint_eval_attempt_identity(sample)  # 真实 rh2 铸造：认宿主事实
        sample.metadata["rh2_eval_result"] = {
            "schema_id": "rh2.eval_attempt_result.v1", "eval": dict(sample.metadata["rh2_eval_dispatch"]),
            "task_id": sample.metadata["task_id"], "physical_attempt_id": minted[idm.ATTEMPT_ID_KEY],
            "result_class": "graded", "task_outcome": "resolved", "reward": 1.0, "turn_weight_versions": ["7"],
        }
        sample.reward = 1.0
        return sample

    def tokenizer(texts, **kw):
        return {"input_ids": [[0] * lengths[i] for i, _ in enumerate(texts)]}

    namespace = {
        "asyncio": asyncio, "copy": copy, "uuid": uuid, "logger": logging.getLogger("i21-test"), "tqdm": _Tqdm,
        "as_completed_async": _as_completed_async, "generate_and_rm": generate_and_rm,
        "compute_sampling_params": lambda args, **kw: {"temperature": 1.0}, "policy_uses_routing_key": lambda args: False,
        "Sample": world.MS, "Dataset": Dataset, "load_tokenizer": lambda *a, **k: tokenizer, "load_processor": lambda *a, **k: None,
        "RH2_EVAL_DISPATCH_METADATA_KEY": "rh2_eval_dispatch", "RH2_EVAL_CALL_RESULT_KEY": "rh2_eval_call",
    }
    _extract(_miles_root() / "rollout/inference_rollout/inference_rollout_eval.py", ("run_eval_datasets", "eval_rollout_single_dataset"), namespace)
    cfg = EvalDatasetConfig(name="swe_dev", path=str(fx.prompts_path), n_samples_per_eval_prompt=1, input_key="prompt",
                            label_key="label", metadata_key="metadata")
    args = NS(group_rm=False, eval_datasets=[cfg], hf_checkpoint="ckpt", apply_chat_template=False, chat_template_path=None,
              eval_reward_key=None, reward_key=None, sglang_enable_deterministic_inference=False, eval_max_prompt_len=10,
              multimodal_keys=None, apply_chat_template_kwargs={}, metadata_key="metadata")

    data = await namespace["run_eval_datasets"](NS(args=args), {}, rollout_id=0, weight_version="7")

    assert data["swe_dev"]["rh2_eval_call"]["num_prompts"] == loaded and len(data["swe_dev"]["samples"]) == received
    events = []
    monkeypatch.setattr(er, "_emit_event", lambda kind, **f: events.append(f) or True)
    monkeypatch.setattr(er, "_log_tracking", lambda *a, **k: None)
    assert er.log_eval_rollout_data(0, args, data, None) is True  # 零样本也由 rh2 钩子接管（默认日志会除零）
    (summary,) = events
    assert summary["planned_source"] == "eval_package" and summary["planned"] == 2 and summary["received"] == received
    assert summary["complete"] is complete and [m["task_id"] for m in summary["missing_members"]] == [ids[m] for m in missing]
    assert summary["prompts_not_loaded"] == 2 - loaded and summary["eval_point_ids"] == [data["swe_dev"]["rh2_eval_call"]["eval_point_id"]]
    assert summary["resolved_rate_planned"] == received / 2 and summary["unresolved"] == 0  # 长题留在分母里，但没有被记成答错
    assert summary["binding"] == ("verified" if received else "unverified")
