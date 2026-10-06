"""I21 实施独立探针；只读生产代码，使用作者的设备替身及原函数 AST，不运行 Docker/GPU。"""
from __future__ import annotations

import ast
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
SOURCES = {}


def load_nodes(relative, names, namespace):
    path = ROOT / relative
    content = path.read_bytes()
    SOURCES[relative] = hashlib.sha256(content).hexdigest()
    tree = ast.parse(content)
    nodes = [n for n in tree.body if getattr(n, "name", None) in names]
    assert len(nodes) == len(names)
    future = ast.parse("from __future__ import annotations").body
    exec(compile(ast.fix_missing_locations(ast.Module(body=future + nodes, type_ignores=[])), str(path), "exec"), namespace)


class Progress:
    def __init__(self, *a, **kw): pass
    def update(self, *a): pass
    def close(self): pass


async def completed(tasks):
    for future in asyncio.as_completed(tasks):
        yield await future


def outer_logger(data, er):
    events, tracking = [], []
    args = NS(custom_eval_rollout_log_function_path="rh2", log_passrate=False)
    env = dict(logger=logging.getLogger("review"), load_function=lambda _: er.log_eval_rollout_data,
               compute_rollout_step=lambda *a: 0, tracking=NS(log=lambda *a, **kw: None),
               dict_add_prefix=lambda d, p: {p + k: v for k, v in d.items()},
               _compute_metrics_from_samples=lambda *a: {})
    load_nodes("reference/miles-rh2-integration/miles/ray/rollout/metrics.py", ("log_eval_rollout_data",), env)
    with patch.object(er, "_emit_event", lambda kind, **f: events.append({"event": kind, **f})), \
         patch.object(er, "_log_tracking", lambda *a: tracking.append(a[2])):
        try:
            env["log_eval_rollout_data"](0, args, data)
            error = None
        except Exception as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
    return {"error": error, "events": events, "tracking": tracking}


async def filtered_eval(world, directory, max_length, short_length=1):
    from miles.utils.data import Dataset
    from miles.utils.eval_config import EvalDatasetConfig
    from repoharness2.adapters.miles import eval_report as er
    from repoharness2.adapters.miles.identity import mint_eval_attempt_identity
    from repoharness2.adapters.slime.eval_wiring import EVAL_REPORT_HOOK_PATH, validate_eval_wiring
    from test_i21_eval_entry import _load_face, prepare_synthetic

    fx = prepare_synthetic(directory)
    face = _load_face(fx)  # 真 prepared 产物、digest 核对；同一文件交给 miles Dataset
    cfg = EvalDatasetConfig(name="review", path=str(fx.prompts_path), input_key="prompt", label_key="label",
                            metadata_key="metadata", n_samples_per_eval_prompt=1, temperature=1.0,
                            top_p=1.0, top_k=-1, max_response_len=128)
    args = NS(group_rm=False, eval_datasets=[cfg], hf_checkpoint="fixture", apply_chat_template=False,
              chat_template_path=None, eval_reward_key=None, reward_key=None, sglang_enable_deterministic_inference=False,
              eval_max_prompt_len=max_length, multimodal_keys=None, apply_chat_template_kwargs={}, eval_interval=1,
              custom_eval_rollout_log_function_path=EVAL_REPORT_HOOK_PATH)
    wiring = validate_eval_wiring(args, execution_mode="fa_formal", eval_only=False,
                                 eval_prepared_dir=str(fx.prepared_dir), eval_host_grading_path=str(fx.host_path),
                                 eval_host_grading_sha256=fx.manifest.host_grading_artifact_sha256)

    async def generate(state, sample, sampling_params, evaluation):
        identity = mint_eval_attempt_identity(sample)
        sample.reward = 1.0
        sample.response = ""
        sample.status = world.MS.Status.COMPLETED
        sample.metadata["rh2_eval_result"] = {
            "physical_attempt_id": identity["rh2_physical_attempt_id"], "eval": sample.metadata["rh2_eval_dispatch"],
            "task_id": sample.metadata["task_id"], "result_class": "graded", "task_outcome": "resolved",
            "reward": 1.0, "turn_weight_versions": ["7"],
        }
        return sample

    # 模型不运行；假 tokenizer 让两道题长度分别为 1 与 100，用真实 Dataset 过滤。
    tokenizer = lambda texts, **kw: {"input_ids": [[0] * (short_length if i == 0 else 100) for i, _ in enumerate(texts)]}
    env = dict(asyncio=asyncio, copy=copy, uuid=uuid, logger=logging.getLogger("review"), tqdm=Progress,
               as_completed_async=completed, generate_and_rm=generate, Dataset=Dataset, Sample=world.MS,
               compute_sampling_params=lambda *a, **kw: kw, policy_uses_routing_key=lambda _: False,
               load_tokenizer=lambda *a, **kw: tokenizer, load_processor=lambda *a, **kw: None,
               RH2_EVAL_DISPATCH_METADATA_KEY="rh2_eval_dispatch")
    load_nodes("reference/miles-rh2-integration/miles/rollout/inference_rollout/inference_rollout_eval.py",
               ("run_eval_datasets", "eval_rollout_single_dataset"), env)
    data = await env["run_eval_datasets"](NS(args=args), {}, rollout_id=0, weight_version="7")
    summary = er.summarize_eval_samples(data["review"]["samples"])
    logged = outer_logger(data, er)
    return {"prepared_tasks": len(face.task_ids()), "precheck_enabled": wiring.enabled,
            "filter_limit": max_length, "planned": summary["planned"], "received": summary["received"],
            "complete": summary["complete"], "binding": summary["binding"],
            "resolved_rate_planned": summary["resolved_rate_planned"],
            "logging_error": logged["error"], "eval_point_events": len(logged["events"])}


async def unsafe_delivery(world, directory, train_top_p, *, unsafe=True):
    from repoharness2.adapters.miles import generate_fn as gf
    from repoharness2.adapters.slime.patch_exporter import PatchExportError
    from test_i21_eval_entry import _chain, _eval_samples, _gi, _load_face, _registry, prepare_synthetic

    fx = prepare_synthetic(directory)
    registry, face_for = _registry(None, _load_face(fx))
    chain = _chain(world, registry=registry, face_for=face_for)
    # 作者夹具的 leaf_factory 固定 group_index=0；真 vendor 从 base_sample 复制。这里对齐真接口，
    # 避免 eval 的 group_index=None 被这个替身误报为身份错配。
    original_factory = chain.orchestrator._adapter_factory

    def adapter_factory(*args):
        adapter = original_factory(*args)
        original_finish = adapter.finish_session

        async def finish(sid, *, base_sample, **kwargs):
            leaves = await original_finish(sid, base_sample=base_sample, **kwargs)
            for leaf in leaves:
                leaf.index, leaf.group_index = base_sample.index, base_sample.group_index
            return leaves
        adapter.finish_session = finish
        return adapter
    chain.orchestrator._adapter_factory = adapter_factory
    sample = _eval_samples(fx)[0]
    args = NS(rh2_orchestrator=chain.orchestrator, rh2_attempt_assignments=registry,
              rollout_top_p=train_top_p, rh2_engine_sampling_mask=True)
    dispatch = _gi(args, sample, evaluation=True)
    assert dispatch.sampling_params["top_p"] == 1.0  # 合法的独立 eval 采样配方
    from contextlib import nullcontext
    exporter = patch("repoharness2.adapters.slime.patch_exporter.export_frozen_patch",
                     side_effect=PatchExportError("unsupported_object_in_patch", "fixture FIFO",
                                                 object_path="src/fifo", object_type="fifo")) if unsafe else nullcontext()
    with patch.object(gf, "_eval_host_stamp_supported", lambda: True), exporter:
        try:
            output = await world.Rh2MilesGenerateFn()(dispatch)
            leaf = output.samples[0]
            result = {"error": None, "status": leaf.status.value, "reward": leaf.reward,
                      "result_class": leaf.metadata["rh2_eval_result"]["result_class"]}
        except Exception as exc:
            result = {"error": type(exc).__name__, "reason_code": getattr(exc, "reason_code", None), "message": str(exc)}
    result.update(train_top_p=train_top_p, eval_top_p=1.0, unsafe=unsafe,
                  unsafe_audit_reasons=chain.orchestrator.audits[0].unsafe_artifact_reasons,
                  grading_calls=len(chain.grading_calls), live_assignments=len(registry))
    return result


def regrade_report():
    from repoharness2.adapters.miles.run_report import build_run_report
    event = {"event": "grading_regrade", "run_id": "review", "trajectory_id": "eval-0123abcd4567-d0-p0_m0",
             "op": "container_start", "category": "daemon_connect", "attempt": 1, "_bundle": 0}
    audit = {"trajectory_id": event["trajectory_id"], "_bundle": 0, "evaluation": {
        "eval": {"eval_point_id": "0123abcd4567", "eval_rollout_id": 0, "dataset": "review"},
        "result_class": "graded", "task_outcome": "resolved"}}
    report = build_run_report(events=[event], audits=[audit])
    return {"train_audits": report["audit_rows"], "eval_audits": report["eval_audit_rows"],
            "train_grading_regrades": report["facets"]["execution_and_loss"]["grading_regrades"]}


def main():
    sys.path[:0] = [str(ROOT / "rh2/tests/adapters_miles"), str(ROOT / "rh2/tests"), str(ROOT / "rh2/tests/adapters")]
    spec = importlib.util.spec_from_file_location("review_conftest", ROOT / "rh2/tests/adapters_miles/conftest.py")
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    fixture = fixtures._vendor_slime_world.__wrapped__()
    next(fixture)
    world = fixtures._World()
    world.install_sglang_stub()
    with tempfile.TemporaryDirectory(prefix="i21-review-") as directory:
        directory = Path(directory)
        result = {"scope": "CPU；真 Dataset / 派发函数体 / RH2 编排和 canonicalize；tokenizer、Docker、harness、引擎为替身"}
        for name, limit, short_length in (("unfiltered", None, 1), ("one_filtered", 10, 1), ("all_filtered", 10, 20)):
            result[name] = asyncio.run(filtered_eval(world, directory / name, limit, short_length))
        for name, train_p, unsafe in (("unsafe_top_p_equal", 1.0, True), ("unsafe_top_p_different", .95, True),
                                     ("graded_top_p_different", .95, False)):
            result[name] = asyncio.run(unsafe_delivery(world, directory / name, train_p, unsafe=unsafe))
        result["eval_regrade_report"] = regrade_report()
    for relative in ("rh2/src/repoharness2/adapters/miles/generate_fn.py", "rh2/src/repoharness2/adapters/miles/canonicalize.py",
                     "rh2/src/repoharness2/adapters/slime/generate.py", "rh2/src/repoharness2/adapters/slime/bringup.py",
                     "rh2/src/repoharness2/adapters/slime/eval_result.py", "rh2/src/repoharness2/adapters/miles/eval_report.py",
                     "rh2/src/repoharness2/adapters/slime/eval_wiring.py", "rh2/src/repoharness2/adapters/miles/run_report.py",
                     "rh2/src/repoharness2/adapters/miles/drop_events.py", "rh2/src/repoharness2/adapters/miles/identity.py",
                     "reference/miles-rh2-integration/miles/utils/data.py"):
        SOURCES[relative] = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    result["source_sha256"] = SOURCES
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
