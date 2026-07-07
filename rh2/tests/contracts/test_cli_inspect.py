"""cli.py（inspect-rh2-artifact）的单测：四步流程与退出码约定。"""

import json

import pytest
from contract_samples import (
    VALID_SAMPLE_FACTORIES,
    valid_anti_cheat_finding,
    valid_eligibility_report,
    valid_trajectory_projection,
)

from repoharness2.cli import (
    EXIT_FORBIDDEN_MARKER,
    EXIT_IO_ERROR,
    EXIT_OK,
    EXIT_UNKNOWN_SCHEMA,
    EXIT_VALIDATION_FAILED,
    main,
)


def _write(tmp_path, name, payload) -> str:
    path = tmp_path / name
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return str(path)


def test_valid_artifact_exits_zero(tmp_path, capsys):
    path = _write(tmp_path, "elig.json", valid_eligibility_report())
    assert main([path]) == EXIT_OK
    assert "OK" in capsys.readouterr().out


@pytest.mark.parametrize("schema_id", sorted(VALID_SAMPLE_FACTORIES))
def test_every_valid_sample_passes_cli(tmp_path, schema_id):
    path = _write(tmp_path, "artifact.json", VALID_SAMPLE_FACTORIES[schema_id]())
    assert main([path]) == EXIT_OK


def test_missing_schema_id_exits_two(tmp_path):
    payload = valid_eligibility_report()
    del payload["schema_id"]
    path = _write(tmp_path, "no_schema.json", payload)
    assert main([path]) == EXIT_UNKNOWN_SCHEMA


def test_unregistered_schema_id_exits_two(tmp_path):
    payload = valid_eligibility_report()
    payload["schema_id"] = "rh2.mystery.v9"
    path = _write(tmp_path, "unknown.json", payload)
    assert main([path]) == EXIT_UNKNOWN_SCHEMA


def test_expect_schema_mismatch_exits_two(tmp_path):
    path = _write(tmp_path, "elig.json", valid_eligibility_report())
    assert main([path, "--expect-schema", "rh2.trajectory_projection.v1"]) == EXIT_UNKNOWN_SCHEMA


def test_validation_failure_exits_three(tmp_path):
    payload = valid_eligibility_report()
    payload["facts_digest"] = "sha256:" + "0" * 64  # digest 互检失败
    path = _write(tmp_path, "bad_digest.json", payload)
    assert main([path]) == EXIT_VALIDATION_FAILED


def test_unknown_field_exits_three(tmp_path):
    payload = valid_eligibility_report()
    payload["smuggled_field"] = "x"
    path = _write(tmp_path, "extra_field.json", payload)
    assert main([path]) == EXIT_VALIDATION_FAILED


def test_forbidden_marker_in_public_artifact_exits_four(tmp_path, capsys):
    """点名非法样例：public 侧视图含 forbidden marker -> 退出码 4。"""

    payload = valid_trajectory_projection()
    payload["source_object_ref"] = "trace_with_test_patch_leak"
    path = _write(tmp_path, "leaky.json", payload)
    assert main([path]) == EXIT_FORBIDDEN_MARKER
    assert "test_patch" in capsys.readouterr().err


def test_private_audit_artifact_exempt_from_marker_scan(tmp_path):
    """finding 描述作弊时天然会提到私有名词：默认豁免，强制扫描时命中。"""

    payload = valid_anti_cheat_finding()
    payload["description"] = "agent attempted to cat /grading/test_patch.diff (blocked)"
    path = _write(tmp_path, "finding.json", payload)
    assert main([path]) == EXIT_OK
    assert main([path, "--force-marker-scan"]) == EXIT_FORBIDDEN_MARKER


def test_malformed_json_exits_five(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    assert main([str(path)]) == EXIT_IO_ERROR


def test_missing_file_exits_five(tmp_path):
    assert main([str(tmp_path / "nope.json")]) == EXIT_IO_ERROR
