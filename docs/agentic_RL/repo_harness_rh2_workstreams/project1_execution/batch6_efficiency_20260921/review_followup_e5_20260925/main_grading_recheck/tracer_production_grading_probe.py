"""E5 Production Tracer: CPU-only check of the miles wrapper and report consumer.

Runs the repository's Rh2MilesGenerateFn class body, _append_event writer, and
run_report consumer. The expensive rollout/canonicalize/identity collaborators
are explicit stubs; this is a wrapper-transport check, not a rollout simulation.
All written evidence stays beside this script with the tracer_ prefix.
"""
from __future__ import annotations

import ast
import asyncio
import importlib.util
import json
import sys
import time
import types
from pathlib import Path
from types import SimpleNamespace as NS

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/src/repoharness2").is_dir())
SRC = ROOT / "rh2/src/repoharness2"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def extract(path, name, namespace):
    node = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == name)
    tree = ast.Module(body=ast.parse("from __future__ import annotations").body + [node], type_ignores=[])
    exec(compile(ast.fix_missing_locations(tree), str(path), "exec"), namespace)
    return namespace[name]


# Package bootstrap only: the report and its two dependencies are pure Python.
for name, path in [("repoharness2", SRC), ("repoharness2.adapters", SRC / "adapters"),
                   ("repoharness2.adapters.miles", SRC / "adapters/miles")]:
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module
report = load("repoharness2.adapters.miles.run_report", SRC / "adapters/miles/run_report.py")
from repoharness2.adapters.miles.forward_profile import derive_from_tokens

# Only the optional return-type import inside the real wrapper is substituted.
base_types = types.ModuleType("miles.rollout.base_types")
base_types.GenerateFnOutput = lambda **kw: NS(**kw)
sys.modules[base_types.__name__] = base_types
counts = {"rollout_calls": 0, "record_event_calls": 0}


async def core_stub(args, sample, sampling_params, evaluation=False):
    counts["rollout_calls"] += 1
    grading = NS(outcome="resolved" if sample.reward == 1 else "unresolved",
                 failure_category=None if sample.reward == 1 else "tests_failed",
                 reward=sample.reward, timings=None)
    args.rh2_orchestrator.audits.append(NS(
        trajectory_id=sample.session_id, finalized=NS(grading_report=grading,
        eligibility_report=NS(eligibility_class="valid_for_training"), group_repair_signal=NS(degraded=False)),
        steps=[], timeline_dicts=lambda: [], timing_summary=lambda: {}, harness_exit_code=0,
        failure_records=[], cleanup_failures=[]))
    return [NS(reward=sample.reward)]


real_record = extract(SRC / "adapters/slime/bringup.py", "record_event", {"json": json, "time": time})
control_path = HERE / "tracer_control_bringup_events.jsonl"
control_path.write_text("")


def record_event_stub(**kw):
    counts["record_event_calls"] += 1
    real_record(service, **kw)


noop = lambda *a, **kw: None
namespace = {
    "rh2_custom_generate": core_stub,
    "canonicalize_group": lambda raw, **kw: raw,
    "mint_attempt_identity": lambda *a, **kw: NS(),
    "_assert_group_admission_filter_wired": noop,
    "stamp_identity_on_outputs": noop,
    "_verify_termination_facts_binding": noop,
    "_verify_admission_binding": noop,
}
wrapper = extract(SRC / "adapters/miles/generate_fn.py", "Rh2MilesGenerateFn", namespace)
args = NS(rh2_orchestrator=NS(config=NS(execution_mode="fa_formal"), audits=[]))
service = NS(record_event=record_event_stub, orchestrator=args.rh2_orchestrator,
             registry=NS(weight_versions={}, stats={}), events_path=control_path)


async def exercise():
    outputs = []
    for reward in (1.0, 0.0):
        outputs.append(await wrapper()(NS(args=args, sample=NS(reward=reward, session_id=f"miles-{reward}"), sampling_params={}, evaluation=False)))
    return outputs


outputs = asyncio.run(exercise())
miles_counts = dict(counts)
assert not control_path.read_text(), "The real miles wrapper unexpectedly reached the grading writer"


async def get_service(args):
    return service


# Positive control: the legacy bringup wrapper really reaches the same writer.
legacy = extract(SRC / "adapters/slime/bringup.py", "generate",
                 {"BringupService": NS(get=get_service), "rh2_custom_generate": core_stub, "time": time})


async def exercise_control():
    for reward in (1.0, 0.0):
        await legacy(args, NS(reward=reward, session_id=f"legacy-{reward}"), {}, evaluation=False)


asyncio.run(exercise_control())
control_bringup = [json.loads(line) for line in control_path.read_text().splitlines()]
writer = extract(SRC / "adapters/slime/bringup.py", "_append_event", {"json": json, "time": time})
events_path = HERE / "tracer_production_bringup_events.jsonl"
events_path.write_text("")
writer(NS(events_path=events_path), {"event": "shutdown_started", "inflight": 0})
writer(NS(events_path=events_path), {"event": "shutdown_completed", "ok": True, "first_cause": None, "residue": {}})
bringup = [json.loads(line) for line in events_path.read_text().splitlines()]

# Synthetic one-hour event span isolates the grading numerator; the event field
# names are the real miles emitter schema. No time measurement is claimed.
events = [
    {"event": "group_consumed", "run_id": "trace", "ts_unix": 1000.0, "sample_indices": [0, 1]},
    {"event": "weight_publish", "run_id": "trace", "ts_unix": 4600.0, "rollout_id": 0},
]
manifest = {"run_id": "trace", "forward_profile": derive_from_tokens([]), "topology": {"actor_gpus": 6, "rollout_gpus": 2}}


def rates(rows):
    return report.build_run_report(events=events, audits=[], bringup=rows, manifests=[manifest])["facets"]["throughput_and_resources"]["hourly_rates"]


before, after, control = rates([]), rates(bringup), rates(control_bringup)
result = {
    "scope": "real wrapper body + shutdown event writer + report consumer; rollout/canonicalize/identity are stubs; synthetic 1-hour denominator",
    "miles_wrapper_calls": miles_counts,
    "after_legacy_control_calls": counts,
    "returned_rewards": [o.samples[0].reward for o in outputs],
    "bringup_rows": bringup,
    "before_shutdown_effective_gradings": before["effective_gradings"],
    "after_shutdown_effective_gradings": after["effective_gradings"],
    "after_shutdown_gradings_not_effective": after["gradings_not_effective"],
    "after_shutdown_reasons": after["reasons"],
    "legacy_control_effective_gradings": control["effective_gradings"],
}
assert miles_counts == {"rollout_calls": 2, "record_event_calls": 0}
assert counts == {"rollout_calls": 4, "record_event_calls": 2}
assert before["effective_gradings"] is None
assert after["effective_gradings"]["total"] == {"count": 0, "per_hour": 0.0, "per_gpu_hour": 0.0}
assert after["gradings_not_effective"]["rows_without_session_id"] == 2
assert control["effective_gradings"]["total"] == {"count": 2, "per_hour": 2.0, "per_gpu_hour": 0.25}
assert control["effective_gradings"]["resolved"]["count"] == 1
assert control["effective_gradings"]["trusted_zero"]["count"] == 1
(HERE / "tracer_production_grading_probe.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(result, indent=2, ensure_ascii=False))
