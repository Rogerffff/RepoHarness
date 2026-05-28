"""Build Stage 16G.2C run_episode projection linkage evidence."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if SRC_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, SRC_ROOT.as_posix())

from repo_harness.config import load_run_config  # noqa: E402
from repo_harness.evaluation.episode_projection import write_run_episode_compat_projection  # noqa: E402
from repo_harness.evaluation.episode_runner import (  # noqa: E402
    _debug_tool_observation_tokens,
    _episode_request_from_spec,
    _final_verifier_factory,
    _opaque_run_config_ref,
    _opaque_task_ref,
    _resolved_verifier_plan,
)
from repo_harness.execution import EpisodeExecutionSpecBuilder  # noqa: E402
from repo_harness.rl import RepoHarnessRuntime, RepoHarnessRuntimeOptions  # noqa: E402
from repo_harness.rl.gateway import LLMGatewayRequest, LLMGatewayResponse  # noqa: E402
from repo_harness.schema_base import stable_hash  # noqa: E402
from repo_harness.stage16g2_file_surface import (  # noqa: E402
    DEFAULT_STAGE16G2_DIR,
    STAGE16G2C_SOURCE_DIGEST_FILES,
    build_stage16g2c_acceptance_summary,
    scan_stage16g2c_public_files,
)
from repo_harness.tasks import load_task  # noqa: E402
from repo_harness.workspace import DependencyState, RunWorkspace, create_workspace_adapter  # noqa: E402


FORBIDDEN_MODEL_VISIBLE_MARKERS = ("audit_ref", "gold_patch", "test_patch", "FAIL_TO_PASS", "PASS_TO_PASS")
RAW_HYGIENE_FIELDS = {
    "raw_patch_sha256",
    "raw_diff_sha256",
    "raw_patch_ref",
    "raw_diff_ref",
    "raw_patch_nonempty",
    "raw_patch_visibility",
    "final_patch_ref",
    "final_diff_ref",
}


def _hash_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> str:
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return _sha256_file(path)


class Stage16G2CScriptedGateway:
    """Deterministic LLMGateway used to exercise real tool calls through run_episode."""

    def __init__(self) -> None:
        self.call_count = 0

    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        self.call_count += 1
        if self.call_count == 1:
            tool_calls = [
                {
                    "tool_call_id": "stage16g2c_write_helper",
                    "tool_name": "write_file",
                    "arguments": {
                        "path": "pkg/helpers.py",
                        "content": (
                            "def normalize(name: str) -> str:\n"
                            "    return \" \".join(name.split()).title()\n"
                        ),
                        "mode": "create",
                    },
                    "turn": request.turn,
                },
                {
                    "tool_call_id": "stage16g2c_apply_patch_batch",
                    "tool_name": "apply_patch",
                    "arguments": {
                        "operations": [
                            {
                                "op": "replace_text",
                                "path": "pkg/calc.py",
                                "old_text": "def divide(a, b):\n    return a / b\n",
                                "new_text": (
                                    "def divide(a, b):\n"
                                    "    if b == 0:\n"
                                    "        raise ValueError(\"division by zero\")\n"
                                    "    return a / b\n"
                                ),
                                "expected_content_hash": _hash_text(
                                    "def divide(a, b):\n    return a / b\n"
                                ),
                            },
                            {
                                "op": "delete_file",
                                "path": "legacy.py",
                                "expected_content_hash": _hash_text("LEGACY = True\n"),
                                "reason": "Remove obsolete legacy marker after structured projection migration.",
                            },
                            {
                                "op": "move_file",
                                "source_path": "old_name.py",
                                "target_path": "pkg/renamed.py",
                                "expected_source_hash": _hash_text('VALUE = "old"\n'),
                                "reason": "Move public constant into package namespace.",
                            },
                            {"op": "mkdir", "path": "docs/generated"},
                            {
                                "op": "write_file",
                                "path": "docs/generated/notes.md",
                                "content": "Stage 16G.2C public projection probe.\n",
                                "mode": "create",
                            },
                        ]
                    },
                    "turn": request.turn,
                },
            ]
            return LLMGatewayResponse(
                route=request.route,
                inference_backend=request.inference_backend,
                model_call_id=request.model_call_id,
                assistant_message={"role": "assistant", "content": None, "tool_calls": tool_calls},
                tool_calls=tool_calls,
                prompt_ids=[11, 12],
                output_token_ids=[101, 102],
                output_logprobs=[-0.01, -0.01],
                response_mask=[1, 1],
                stop_reason="tool_calls",
                token_source="stage16g2c_scripted_gateway",
                usage={"input_tokens": 2, "output_tokens": 2},
                duration_ms=0,
                extra_fields={},
            )
        return LLMGatewayResponse(
            route=request.route,
            inference_backend=request.inference_backend,
            model_call_id=request.model_call_id,
            assistant_message={"role": "assistant", "content": "Implemented structured file changes."},
            tool_calls=[],
            prompt_ids=[21],
            output_token_ids=[201, 202, 203],
            output_logprobs=[-0.01, -0.01, -0.01],
            response_mask=[1, 1, 1],
            stop_reason="stop",
            token_source="stage16g2c_scripted_gateway",
            usage={"input_tokens": 1, "output_tokens": 3},
            duration_ms=0,
            extra_fields={},
        )


def _write_probe_fixture(root: Path) -> tuple[Path, Path]:
    fixture_root = root / "fixtures"
    repo = fixture_root / "repos" / "stage16g2c_projection_repo"
    tasks = fixture_root / "tasks"
    configs = fixture_root / "run_configs"
    for path in (repo / "pkg", repo / "tests", tasks, configs):
        path.mkdir(parents=True, exist_ok=True)
    (repo / "pkg" / "calc.py").write_text("def divide(a, b):\n    return a / b\n", encoding="utf-8")
    (repo / "legacy.py").write_text("LEGACY = True\n", encoding="utf-8")
    (repo / "old_name.py").write_text('VALUE = "old"\n', encoding="utf-8")
    (repo / "pyproject.toml").write_text('[tool.pytest.ini_options]\npythonpath = ["."]\n', encoding="utf-8")
    (repo / "tests" / "test_calc.py").write_text(
        "\n".join(
            [
                "from pkg.calc import divide",
                "from pkg.helpers import normalize",
                "from pkg.renamed import VALUE",
                "",
                "def test_divide_zero():",
                "    try:",
                "        divide(1, 0)",
                "    except ValueError as exc:",
                "        assert str(exc) == \"division by zero\"",
                "    else:",
                "        raise AssertionError(\"expected ValueError\")",
                "",
                "def test_helper():",
                "    assert normalize(\"  ada lovelace  \") == \"Ada Lovelace\"",
                "",
                "def test_renamed():",
                "    assert VALUE == \"old\"",
                "",
            ]
        ),
        encoding="utf-8",
    )
    task = {
        "id": "stage16g2c_projection_task",
        "task_version": "stage16g2c_projection_task_v0",
        "dataset_name": "repo_harness_micro",
        "source_kind": "micro_repo_fixture",
        "dataset_split": "dev",
        "created_at": "2026-05-28",
        "repo": "../repos/stage16g2c_projection_repo",
        "base_commit": "fixture",
        "issue": "Exercise Stage 16G.2C structured file tools and projection linkage.",
        "setup_command": None,
        "test_command": "pytest -q",
        "timeouts": {
            "setup_timeout_sec": 60,
            "test_timeout_sec": 30,
            "agent_timeout_sec": 120,
            "final_verifier_timeout_sec": 60,
        },
        "environment": {
            "execution_image": "python:3.12-slim",
            "python_version": "3.12",
            "node_version": None,
            "package_manager": "pip",
            "lockfile_hashes": [],
            "setup_cache_key_inputs": ["pyproject.toml"],
            "required_system_packages": [],
            "setup_network_policy": "deny",
        },
        "expected_files": ["pkg/calc.py", "pkg/helpers.py", "pkg/renamed.py"],
        "fail_to_pass_tests": [
            "tests/test_calc.py::test_divide_zero",
            "tests/test_calc.py::test_helper",
            "tests/test_calc.py::test_renamed",
        ],
        "pass_to_pass_tests": [],
        "visibility": {
            "issue": "model_visible",
            "expected_files": "model_visible",
            "fail_to_pass_tests": "verifier_only",
            "pass_to_pass_tests": "verifier_only",
            "gold_patch": "hidden_reference",
        },
        "decontamination": {
            "status": "manual_checked",
            "known_public_solution": False,
            "source_url": None,
            "overlap_check_notes": "Stage 16G.2C synthetic projection fixture.",
        },
        "declared_setup_mutations": [],
        "generated_files": [],
        "tags": ["stage16g2c", "structured-file-tools"],
    }
    task_path = tasks / "stage16g2c_projection_task.yaml"
    task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")
    config = {
        "run_id_prefix": "stage16g2c",
        "tasks": [task_path.as_posix()],
        "model": {"provider": "mock", "model_id": "stage16g2c-scripted-gateway"},
        "runtime": {
            "scaffold_id": "simple_react",
            "execution_mode": "local_process",
            "permission_mode": "auto",
            "test_feedback_policy": "public_only",
            "feedback_tests_passed_policy": "require_model_final",
            "max_turns": 4,
            "max_tool_calls": 6,
            "max_test_runs": 1,
        },
        "workspace": {
            "output_dir": (root / "runs").as_posix(),
            "keep_workspace": True,
            "default_command_timeout_sec": 60,
            "max_tool_output_chars": 8000,
            "network_policy": "deny_agent_run",
        },
    }
    config_path = configs / "stage16g2c_projection_config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return task_path, config_path


def _run_stage16g2c_probe(temp_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    task_path, config_path = _write_probe_fixture(temp_root)
    loaded = load_task(task_path)
    config = load_run_config(config_path, output_dir=temp_root / "runs")
    run_id = "stage16g2c_projection_probe"
    run_dir = Path(config.workspace.output_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    adapter = create_workspace_adapter(config=config, run_id=run_id, run_dir=run_dir)
    source_checkout = adapter.create_source_checkout(loaded.runnable_task)
    resolved_verifier_plan = _resolved_verifier_plan(loaded, run_id)
    workspace = RunWorkspace(
        run_id=run_id,
        workspace_path=source_checkout.as_posix(),
        repo_base_commit=loaded.runnable_task.base_commit,
        execution_mode=config.runtime.execution_mode,
        artifact_dir=(run_dir / "artifacts").as_posix(),
        dependency_state=DependencyState(),
    )
    spec = EpisodeExecutionSpecBuilder().build_spec_from_loaded_task(
        task=loaded.runnable_task,
        workspace=workspace,
        run_config=config,
        resolved_verifier_plan=resolved_verifier_plan,
        run_id=run_id,
        task_ref=_opaque_task_ref(loaded),
        run_config_ref=_opaque_run_config_ref(config),
    )
    request = _episode_request_from_spec(
        spec=spec,
        task=loaded.runnable_task,
        loaded_task=loaded,
        route="mock",
        config=config,
        run_mode="training_fast",
    )
    runtime = RepoHarnessRuntime(
        RepoHarnessRuntimeOptions(
            config_path=config_path,
            output_dir=temp_root / "runs",
            runtime_execution_mode="real_episode",
            executor_max_workers=1,
            episode_timeout_seconds=120,
            real_episode_source_resolver=lambda _request: source_checkout,
            real_episode_final_verifier_factory=_final_verifier_factory(
                resolved_verifier_plan=resolved_verifier_plan,
            ),
            tool_observation_token_projector=lambda content: _debug_tool_observation_tokens(content),
        )
    )
    result = asyncio.run(
        runtime.run_episode(
            request,
            llm_gateway=Stage16G2CScriptedGateway(),
            execution_spec=spec,
        )
    )
    projection = write_run_episode_compat_projection(
        run_dir=run_dir,
        task=loaded.runnable_task,
        request=request,
        execution_spec=spec,
        result=result,
        provider_route="mock",
    )
    projection_dir = projection.projection_dir
    manifest = _read_json(projection_dir / "compat_projection_manifest.json")
    route = _read_json(projection_dir / "provider_route_qualification.json")
    training_view_projection = _read_json(projection_dir / "training_view_projection.json")
    generation_projection = _read_json(projection_dir / "generation_records_projection.json")
    verifier = _read_json(projection_dir / "verifier_summary.json")
    hygiene = _read_json(projection_dir / "final_patch_hygiene_report.json")
    patch_text = (projection_dir / "final.patch").read_text(encoding="utf-8")
    diff_text = (projection_dir / "final.diff").read_text(encoding="utf-8")
    source_patch_text = (run_dir / "final.patch").read_text(encoding="utf-8")
    source_diff_text = (run_dir / "final.diff").read_text(encoding="utf-8")
    operation_kinds, tool_names, tool_statuses = _tool_event_facts(run_dir)
    patch_facts = _patch_changed_file_facts(patch_text)
    forbidden_marker_scan = _prepared_messages_forbidden_marker_scan(run_dir)
    tool_spans = [span for span in result.training_view.response_spans if span.source_type == "tool_observation"]
    probe = {
        "schema_version": "stage16g2c.run_episode_projection_probe_report.v1",
        "status": "passed",
        "run_episode_invocation": "RepoHarnessRuntime.run_episode(real_episode)",
        "projection_writer": "write_run_episode_compat_projection",
        "projection_created_from_run_episode": manifest.get("projection_created_from_run_episode"),
        "projection_complete": projection.validation_report.get("projection_complete"),
        "result_status": result.status,
        "result_status_reason": result.status_reason,
        "final_verifier_accepted": bool((verifier.get("verifier_summary") or {}).get("accepted")),
        "tool_names_observed": sorted(tool_names),
        "tool_result_statuses": tool_statuses,
        "operation_kinds_observed": sorted(operation_kinds),
        "final_patch_sha256": manifest.get("final_patch_sha256"),
        "final_diff_sha256": manifest.get("final_diff_sha256"),
        "final_patch_changed_file_facts": patch_facts,
        "training_projection": {
            "training_view_projection_schema_version": training_view_projection.get("schema_version"),
            "response_token_count": training_view_projection.get("response_token_count"),
            "response_mask_count": training_view_projection.get("response_mask_count"),
            "response_span_count": training_view_projection.get("response_span_count"),
            "generation_record_count": generation_projection.get("record_count"),
            "tool_observation_span_count": len(tool_spans),
            "tool_observation_spans_response_mask_zero": all(
                span.response_mask_value == 0 for span in tool_spans
            ),
            "tool_output_response_mask_zero_count": result.training_view.response_mask.count(0),
            "assistant_response_mask_one_count": result.training_view.response_mask.count(1),
            "online_rl_eligible": training_view_projection.get("online_rl_eligible"),
            "invalid_for_training": training_view_projection.get("invalid_for_training"),
            "invalid_for_online_rl": training_view_projection.get("invalid_for_online_rl"),
        },
        "provider_route_qualification": {
            "provider_route": route.get("provider_route"),
            "llm_gateway_route": route.get("llm_gateway_route"),
            "formal_online_rl_eligible": route.get("formal_online_rl_eligible"),
            "policy_loss_candidate": route.get("policy_loss_candidate"),
            "qualification_reason": route.get("qualification_reason"),
        },
        "forbidden_model_visible_marker_scan_passed": forbidden_marker_scan["passed"],
        "forbidden_model_visible_marker_findings": forbidden_marker_scan["findings"],
        "public_safe_digest_only": True,
    }
    linkage = {
        "schema_version": "stage16g2c.projection_linkage_report.v1",
        "status": "passed",
        "compat_projection_file_count": len(manifest.get("projection_file_digests", {})),
        "compat_projection_validation_error_count": projection.validation_report.get("error_count"),
        "manifest_final_patch_sha256_matches_projection": manifest.get("final_patch_sha256") == _hash_text(patch_text),
        "manifest_final_diff_sha256_matches_projection": manifest.get("final_diff_sha256") == _hash_text(diff_text),
        "hygiene_cleaned_patch_sha256_matches_manifest": hygiene.get("cleaned_patch_sha256")
        == manifest.get("final_patch_sha256"),
        "hygiene_cleaned_diff_sha256_matches_manifest": hygiene.get("cleaned_diff_sha256")
        == manifest.get("final_diff_sha256"),
        "source_and_compat_final_patch_match": source_patch_text == patch_text,
        "source_and_compat_final_diff_match": source_diff_text == diff_text,
        "public_hygiene_report_contains_raw_fields": bool(RAW_HYGIENE_FIELDS & set(hygiene)),
        "patch_hygiene_status": hygiene.get("status"),
        "patch_hygiene_filtered_file_count": hygiene.get("filtered_file_count"),
        "patch_hygiene_flagged_file_count": hygiene.get("flagged_file_count"),
        "compat_projection_public_safe": projection.validation_report.get("projection_complete") is True,
        "projection_source_result_digest_present": isinstance(
            manifest.get("projection_source_result_digest"), str
        ),
        "projection_source_training_view_digest_present": isinstance(
            manifest.get("projection_source_training_view_digest"), str
        ),
        "raw_artifact_private_by_omission": True,
    }
    return probe, linkage


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _tool_event_facts(run_dir: Path) -> tuple[set[str], set[str], dict[str, str]]:
    operation_kinds: set[str] = set()
    tool_names: set[str] = set()
    statuses: dict[str, str] = {}
    for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("event_type") != "tool_completed":
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        tool_name = data.get("effective_tool_name") or data.get("tool_name")
        if isinstance(tool_name, str) and tool_name in {"write_file", "apply_patch"}:
            tool_names.add(tool_name)
            statuses[tool_name] = str(data.get("status"))
            typed = data.get("typed") if isinstance(data.get("typed"), dict) else {}
            facts = typed.get("operation_facts") if isinstance(typed.get("operation_facts"), list) else []
            for fact in facts:
                if isinstance(fact, dict) and isinstance(fact.get("op"), str):
                    operation_kinds.add(fact["op"])
    return operation_kinds, tool_names, statuses


def _patch_changed_file_facts(patch_text: str) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in patch_text.splitlines():
        if line.startswith("diff --git "):
            if current is not None:
                entries.append(current)
            parts = line.split()
            old_path = parts[2][2:] if len(parts) > 2 and parts[2].startswith("a/") else ""
            new_path = parts[3][2:] if len(parts) > 3 and parts[3].startswith("b/") else old_path
            current = {"old_path": old_path, "new_path": new_path, "status": "modified"}
        elif current is not None and line.startswith("new file mode"):
            current["status"] = "added"
        elif current is not None and line.startswith("deleted file mode"):
            current["status"] = "deleted"
        elif current is not None and line.startswith("rename from "):
            current["old_path"] = line.removeprefix("rename from ")
            current["status"] = "renamed"
        elif current is not None and line.startswith("rename to "):
            current["new_path"] = line.removeprefix("rename to ")
            current["status"] = "renamed"
    if current is not None:
        entries.append(current)
    changed_paths = sorted(
        {
            path
            for entry in entries
            for path in (entry.get("old_path"), entry.get("new_path"))
            if isinstance(path, str) and path
        }
    )
    return {
        "entry_count": len(entries),
        "added_count": sum(1 for entry in entries if entry.get("status") == "added"),
        "modified_count": sum(1 for entry in entries if entry.get("status") == "modified"),
        "deleted_count": sum(1 for entry in entries if entry.get("status") == "deleted"),
        "renamed_count": sum(1 for entry in entries if entry.get("status") == "renamed"),
        "changed_paths": changed_paths,
        "entries": entries,
    }


def _prepared_messages_forbidden_marker_scan(run_dir: Path) -> dict[str, Any]:
    findings = []
    for path in sorted((run_dir / "artifacts").glob("*prepared_messages.json")):
        text = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_MODEL_VISIBLE_MARKERS:
            if marker in text:
                findings.append({"artifact_kind": "prepared_messages", "marker": marker})
    return {"passed": not findings, "findings": findings}


def build_reports() -> tuple[dict[str, Any], dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="stage16g2c-projection-") as temp_dir:
        return _run_stage16g2c_probe(Path(temp_dir))


def write_stage16g2c_reports(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    probe_report, linkage_report = build_reports()
    reports = {
        "stage16g2c_run_episode_projection_probe_report.json": probe_report,
        "stage16g2c_projection_linkage_report.json": linkage_report,
    }
    digests = {
        filename: _write_json(output_dir / filename, payload)
        for filename, payload in reports.items()
    }
    path_scan = scan_stage16g2c_public_files(output_dir)
    reports["stage16g2c_path_leak_scan_report.json"] = path_scan
    digests["stage16g2c_path_leak_scan_report.json"] = _write_json(
        output_dir / "stage16g2c_path_leak_scan_report.json", path_scan
    )
    summary = build_stage16g2c_acceptance_summary(reports=reports, digests=digests)
    digests["stage16g2c_acceptance_summary.json"] = _write_json(
        output_dir / "stage16g2c_acceptance_summary.json", summary
    )
    path_scan = scan_stage16g2c_public_files(output_dir)
    reports["stage16g2c_path_leak_scan_report.json"] = path_scan
    digests["stage16g2c_path_leak_scan_report.json"] = _write_json(
        output_dir / "stage16g2c_path_leak_scan_report.json", path_scan
    )
    summary = build_stage16g2c_acceptance_summary(reports=reports, digests=digests)
    digests["stage16g2c_acceptance_summary.json"] = _write_json(
        output_dir / "stage16g2c_acceptance_summary.json", summary
    )
    return digests


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=DEFAULT_STAGE16G2_DIR.as_posix())
    args = parser.parse_args(argv)
    digests = write_stage16g2c_reports(Path(args.output_dir))
    print(
        json.dumps(
            {
                "status": "passed",
                "output_dir": args.output_dir,
                "digests": digests,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
