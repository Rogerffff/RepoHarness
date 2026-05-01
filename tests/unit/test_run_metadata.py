from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_harness.config import RunConfig
from repo_harness.evaluation import BaselineResult
from repo_harness.run_metadata.fingerprint import (
    build_local_environment_fingerprint,
    compute_source_tree_hash,
)
from repo_harness.run_metadata.tool_snapshot import write_tool_schema_snapshot
from repo_harness.run_metadata.writer import (
    build_run_config_facts,
    build_run_metadata,
    write_run_config_facts,
    write_run_metadata,
)
from repo_harness.tasks import TaskDefinition
from repo_harness.trajectory import RunRecorder
from repo_harness.workspace import DependencyState

from tests.unit.test_task_schema import valid_task_payload


def test_source_tree_hash_excludes_git_and_cache_dirs(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (source / ".git").mkdir()
    (source / ".git" / "HEAD").write_text("ignored\n", encoding="utf-8")
    first = compute_source_tree_hash(source)

    (source / ".git" / "HEAD").write_text("changed but ignored\n", encoding="utf-8")
    (source / "__pycache__").mkdir()
    (source / "__pycache__" / "app.pyc").write_bytes(b"ignored")
    second = compute_source_tree_hash(source)

    assert first == second


def test_run_config_facts_and_metadata_are_written_as_root_fact_files(tmp_path: Path):
    run_dir = tmp_path / "run_001"
    task = TaskDefinition.model_validate(valid_task_payload())
    source = tmp_path / "source"
    source.mkdir()
    (source / "calculator.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")

    with RunRecorder("run_001", run_dir, task_id=task.id) as recorder:
        _, _, tool_protocol = write_tool_schema_snapshot(recorder)
        dependency_state_ref = recorder.write_json_artifact(
            "dependency_state",
            DependencyState().model_dump(mode="json"),
            {"budget_policy": "preserve_json"},
        )
        fingerprint = build_local_environment_fingerprint(
            task_definition=task,
            source_checkout=source,
            dependency_state=DependencyState(),
            dependency_state_ref=dependency_state_ref,
            command_timeout_sec=120,
            network_policy="deny_agent_run",
        )
        facts = build_run_config_facts(
            run_id="run_001",
            task_definition=task,
            config=RunConfig(),
            tool_protocol=tool_protocol,
            environment_fingerprint=fingerprint,
        )
        facts_ref = write_run_config_facts(run_dir, facts)
        (run_dir / "metrics.json").write_text(
            json.dumps(
                {
                    "run_outcome": "success",
                    "final_verifier_status": "accepted",
                    "task_success": True,
                    "turn_count": 1,
                    "tool_call_count": 1,
                    "test_run_count": 1,
                    "interaction_efficiency": {"final_verifier_mode": "strict_patch_replay"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (run_dir / "verifier.json").write_text(
            json.dumps({"verifier_stage": "final", "accepted": True}) + "\n",
            encoding="utf-8",
        )
        (run_dir / "reward.json").write_text(
            json.dumps({"final_reward": 1.0}) + "\n",
            encoding="utf-8",
        )
        (run_dir / "final.patch").write_text("diff --git a/app.py b/app.py\n", encoding="utf-8")
        metadata = build_run_metadata(
            run_dir=run_dir,
            run_id="run_001",
            task_id=task.id,
            run_config_facts_ref=facts_ref,
            tool_protocol=tool_protocol,
            baseline=BaselineResult(task_id=task.id, status="valid"),
            run_outcome="success",
            final_verifier_status="accepted",
            agent_stop_reason="feedback_tests_passed",
            final_verifier_mode="strict_patch_replay",
        )
        metadata_ref = write_run_metadata(run_dir, metadata)

    facts_payload = json.loads((run_dir / "run_config_facts.json").read_text(encoding="utf-8"))
    metadata_payload = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "artifacts.json").read_text(encoding="utf-8"))
    manifest_paths = {artifact["relative_path"] for artifact in manifest["artifacts"]}

    assert facts_ref.relative_path == "run_config_facts.json"
    assert metadata_ref.relative_path == "run_metadata.json"
    assert facts_payload["run_id"] == "run_001"
    assert facts_payload["tool_protocol"]["tool_schema_snapshot_ref"]["artifact_id"]
    assert metadata_payload["run_config_facts_ref"]["sha256"] == facts_ref.sha256
    assert metadata_payload["tool_protocol"]["tool_schema_snapshot_ref"]["artifact_id"]
    assert metadata_payload["export_readiness"]["training_export_ready"] is True
    assert any(artifact["kind"] == "tool_schema_snapshot" for artifact in manifest["artifacts"])
    assert "run_config_facts.json" not in manifest_paths
    assert "run_metadata.json" not in manifest_paths


def test_run_config_facts_are_immutable_root_facts(tmp_path: Path):
    run_dir = tmp_path / "run_001"
    task = TaskDefinition.model_validate(valid_task_payload())
    source = tmp_path / "source"
    source.mkdir()
    (source / "demo.py").write_text("x = 1\n", encoding="utf-8")
    with RunRecorder("run_001", run_dir, task_id=task.id) as recorder:
        _, _, tool_protocol = write_tool_schema_snapshot(recorder)
        dependency_state_ref = recorder.write_json_artifact(
            "dependency_state",
            DependencyState().model_dump(mode="json"),
            {"budget_policy": "preserve_json"},
        )
        fingerprint = build_local_environment_fingerprint(
            task_definition=task,
            source_checkout=source,
            dependency_state=DependencyState(),
            dependency_state_ref=dependency_state_ref,
            command_timeout_sec=120,
            network_policy="deny_agent_run",
        )
        facts = build_run_config_facts(
            run_id="run_001",
            task_definition=task,
            config=RunConfig(),
            tool_protocol=tool_protocol,
            environment_fingerprint=fingerprint,
        )
        write_run_config_facts(run_dir, facts)
        with pytest.raises(FileExistsError):
            write_run_config_facts(run_dir, facts)


def test_environment_fingerprint_records_setup_and_dependency_refs(tmp_path: Path):
    run_dir = tmp_path / "run_001"
    task = TaskDefinition.model_validate(valid_task_payload())
    source = tmp_path / "source"
    source.mkdir()
    (source / "demo.py").write_text("x = 1\n", encoding="utf-8")
    with RunRecorder("run_001", run_dir, task_id=task.id) as recorder:
        dependency_state_ref = recorder.write_json_artifact(
            "dependency_state",
            DependencyState().model_dump(mode="json"),
            {"budget_policy": "preserve_json"},
        )
        setup_ref = recorder.write_artifact("setup_stdout", "setup ok")
        fingerprint = build_local_environment_fingerprint(
            task_definition=task,
            source_checkout=source,
            dependency_state=DependencyState(),
            dependency_state_ref=dependency_state_ref,
            setup_artifact_hash=setup_ref.sha256,
            command_timeout_sec=120,
            network_policy="deny_agent_run",
        )

    execution = fingerprint.workspace_execution
    assert execution.dependency_state_ref == dependency_state_ref
    assert execution.setup_artifact_hash == setup_ref.sha256
