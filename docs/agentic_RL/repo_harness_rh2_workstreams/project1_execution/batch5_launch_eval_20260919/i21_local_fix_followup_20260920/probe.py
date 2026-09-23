"""LR1 / LR2 窄复核：复用原审查的真实控制流探针，不覆盖历史证据。

CPU only；不执行完整 CLI、Ray、Docker、权重加载或 GPU。外部副作用沿用原替身。
"""
from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/src/repoharness2").is_dir())
PACKAGE = Path(__file__).resolve().parent.parent


def module_at(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


old = module_at("prior_local_review", PACKAGE / "i21_i22_local_completion_review_20260920/probe.py")
original_args = old.eval_args


def args_for(**overrides):
    return original_args(**{"rollout_global_dataset": False, "prompt_data": None,
                            "sglang_load_format": "auto", **overrides})


def precheck(args, *, eval_only=True):
    from repoharness2.adapters.slime.eval_wiring import EvalWiringError, validate_eval_wiring

    try:
        wiring = validate_eval_wiring(
            args, execution_mode="fa_formal", eval_only=eval_only, eval_prepared_dir="/prep/eval",
            eval_host_grading_path="/private/host.json", eval_host_grading_sha256="sha256:" + "a" * 64,
            environ=dict(os.environ),
        )
    except EvalWiringError as exc:
        return {"enabled": False, "error": exc.reason_code}
    return {"enabled": wiring.enabled, "eval_only": wiring.eval_only, "error": None}


def data_source(args):
    from miles.rollout import data_source as ds
    from miles.utils.data import Dataset

    assert ds.Dataset is Dataset
    vars(args).update(chat_template_path=None, dump_details=None, rollout_max_prompt_len=None,
                      input_key="prompt", multimodal_keys=None, label_key="label", metadata_key="metadata",
                      tool_key=None, apply_chat_template=False, apply_chat_template_kwargs={},
                      rollout_seed=1, rollout_shuffle=False, buffer_filter_path=None)
    with patch.object(ds, "load_tokenizer", lambda *a, **kw: NS()), patch.object(ds, "load_processor", lambda *a, **kw: None):
        try:
            source = ds.RolloutDataSourceWithBuffer(args)
            return {"error": None, "dataset_is_none": source.dataset is None}
        except Exception as exc:
            return {"error": type(exc).__name__, "message": str(exc)}


def model_source_transport(directory):
    from repoharness2.adapters.miles.eval_report import summarize_eval_samples
    from repoharness2.adapters.miles.run_report import build_run_report
    from repoharness2.adapters.slime.bringup import write_execution_audit_record
    from repoharness2.adapters.slime.eval_result import derive_eval_attempt_result
    from repoharness2.adapters.slime.generate import RolloutAudit

    audit = RolloutAudit(trajectory_id="eval-lr2-d0-p0_m0", task_id="task-0")
    audit.session_id = audit.trajectory_id
    audit.physical_attempt_id = audit.trajectory_id + "#p1-aaaaaaaa"
    audit.evaluation = True
    audit.configured_hf_checkpoint = "/ckpt/hf_step_20"
    audit.eval_dispatch = dict(eval_point_id="lr2", eval_rollout_id=0, target_weight_version=None,
                               dataset="review", dataset_index=0, prompt_index=0, sample_slot=0,
                               n_samples_per_eval_prompt=1, num_prompts=1)
    audit.outcome_v2 = dict(termination_kind="completed", completion_class="present_complete",
                           turn_weight_versions=["0"], current_version_at_finalize="0")
    grading = NS(outcome="resolved", failure_category=None, reward=1.0, report_id="rpt-lr2",
                 grader_version="fixture", timings=None)
    audit.finalized = NS(grading_report=grading, eligibility_report=NS(report_id="elig-lr2"),
                         group_repair_signal=NS(degraded=False))
    path = directory / "audit.jsonl"
    write_execution_audit_record(None, audit, path, model_name="fixture-model")
    row = json.loads(path.read_text())
    row["_bundle"] = 0
    payload = derive_eval_attempt_result(audit, model_name="fixture-model")
    assert row["evaluation"] == payload
    assert "engine_model_path" not in payload
    summary = summarize_eval_samples([NS(metadata={"rh2_eval_result": payload})], planned_task_ids=["task-0"])
    assert summary["complete"] and summary["binding"] == "unverified"
    event = dict(event="eval_point", ts_unix=1.0, host="fixture", pid=1, run_id="r1", _bundle=0,
                 rollout_id=0, dataset="review", **summary)
    facet = build_run_report(events=[event], audits=[row])["facets"]["evaluation"]
    expected = [audit.configured_hf_checkpoint]
    assert summary["configured_hf_checkpoints"] == expected
    assert facet["by_eval_point"]["lr2"]["configured_hf_checkpoints"] == expected
    assert facet["eval_point_events"][0]["configured_hf_checkpoints"] == expected
    assert facet["points_binding"] == {"unverified": 1}
    return {"audit_payload_equal": True, "payload_configured_hf_checkpoint": payload["configured_hf_checkpoint"],
            "summary_configured_hf_checkpoints": expected, "complete": summary["complete"],
            "binding": summary["binding"], "run_report": facet}


def main():
    sys.path[:0] = [str(ROOT / "rh2/tests/adapters_miles"), str(ROOT / "rh2/tests")]
    fixtures = module_at("lr_followup_fixtures", ROOT / "rh2/tests/adapters_miles/conftest.py")
    fixture = fixtures._vendor_slime_world.__wrapped__()
    next(fixture)
    world = fixtures._World()
    world.install_sglang_stub()
    old.eval_args, old.precheck = args_for, precheck

    result = {"scope": "CPU 反例复放与报告运输；非完整 CLI / 设备验证"}
    with patch.dict(os.environ, {"MILES_SGLANG_DUMMY_LOAD": "0"}):
        shape = args_for()
        result["single_positive_shape"] = {"data_source": data_source(shape), "events": asyncio.run(old.drive(shape)),
                                            "precheck": precheck(shape)}
        positive = result["single_positive_shape"]
        assert positive["data_source"] == {"error": None, "dataset_is_none": True}
        assert [r["op"] for r in positive["events"]] == ["update_weights_call_noop", "eval", "dispose"]
        assert positive["precheck"]["error"] is None

        for name, over, reason in (
            ("non_fully_async", {"fully_async": False}, "eval_only_requires_fully_async_driver"),
            ("skip_initial_eval", {"skip_eval_before_train": True}, "eval_only_initial_eval_skipped"),
        ):
            shape = args_for(**over)
            result[name] = {"precheck": precheck(shape), "raw_driver_events": asyncio.run(old.drive(shape))}
            assert result[name]["precheck"]["error"] == reason
        assert "training_generate" in [r["op"] for r in result["non_fully_async"]["raw_driver_events"]]
        assert "eval" not in [r["op"] for r in result["skip_initial_eval"]["raw_driver_events"]]

        shape = args_for(rollout_global_dataset=True)
        result["default_data_source_no_training_file"] = {"precheck": precheck(shape), "data_source": data_source(shape)}
        assert result["default_data_source_no_training_file"]["precheck"]["error"] == "eval_only_global_dataset_without_prompt_data"
        assert result["default_data_source_no_training_file"]["data_source"]["error"] == "TypeError"

        result["effective_engine_configs"] = [old.engine_config_case(), old.engine_config_case(dummy_env=True),
                                              old.engine_config_case(dummy_cli=True), old.engine_config_case(override_path="/ckpt/other")]
        normal, env_dummy, cli_dummy, group = result["effective_engine_configs"]
        assert normal["precheck"]["enabled"] and normal["effective_load_format"] == "auto"
        for row in (env_dummy, cli_dummy):
            assert row["precheck"]["error"] == "eval_only_dummy_weight_load"
            assert row["effective_load_format"] == "dummy" and row["engine_model_path"] == row["configured_checkpoint"]
        assert group["precheck"]["enabled"] and group["engine_model_path"] != group["configured_checkpoint"]
        group["boundary"] = "首版不支持；预检不拦拓扑覆盖，GPU 清单 A3 逐引擎检查"
        result["training_eval_dummy_unrestricted"] = precheck(args_for(fully_async=False, sglang_load_format="dummy"), eval_only=False)
        assert result["training_eval_dummy_unrestricted"]["enabled"]
        with tempfile.TemporaryDirectory(prefix="i21-lr2-") as temp:
            result["model_source_transport"] = model_source_transport(Path(temp))

    for relative in (
        "rh2/src/repoharness2/adapters/slime/eval_wiring.py", "rh2/src/repoharness2/adapters/slime/generate.py",
        "rh2/src/repoharness2/adapters/slime/eval_result.py", "rh2/src/repoharness2/adapters/slime/bringup.py",
        "rh2/src/repoharness2/adapters/miles/eval_report.py", "rh2/src/repoharness2/adapters/miles/run_report.py",
        "reference/miles-rh2-integration/miles/rollout/data_source.py", "reference/miles-rh2-integration/miles/utils/data.py",
        "rh2/tests/adapters_miles/test_i21_eval_only_driver.py", "rh2/tests/adapters/test_i21_eval_wiring.py",
    ):
        old.record(ROOT / relative)
    result["source_sha256"] = old.SOURCES
    result["prior_probe_sha256"] = hashlib.sha256((PACKAGE / "i21_i22_local_completion_review_20260920/probe.py").read_bytes()).hexdigest()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
