"""R2E 修订后的离线工具边界；仅写本审查目录和 runs/r2e_t0_review_20260924。"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
RUNS = ROOT / "runs/r2e_t0_review_20260924"
PYTHON = ROOT / "rh2/.venv/bin/python"


def check_r13() -> list[dict]:
    path = ROOT / "rh2/scripts/r2e_env/apply_r13.py"
    spec = importlib.util.spec_from_file_location("review_r13", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    results = []
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        cases = [
            ("no_explicit", {}, "unknown"),
            ("open_issue", {"state_if_r13_passes": "environment_qualified", "open_items": ["dev_blocking"]}, "unknown"),
            ("explicit_clear", {"state_if_r13_passes": "environment_qualified", "open_items": []}, "environment_qualified"),
        ]
        for name, extra, expected in cases:
            d = t / name
            d.mkdir()
            (d / "screening_record.json").write_text(json.dumps({
                "checks": {"R13": {"status": "unknown"}},
                "disposition": {"state": "unknown", "pending_checks": ["R13"], **extra},
            }))
            (d / "facts.json").write_text(json.dumps({"auto_checks": {
                "R13_repeat_noop": {"status": "pass", "evidence_refs": ["probe"]},
                "R13_repeat_gold": {"status": "pass", "evidence_refs": ["probe"]},
            }}))
        with contextlib.redirect_stdout(io.StringIO()):
            assert mod.main(["--tasks-dir", str(t), "--by", "Codex isolated probe"]) == 0
        for name, _, expected in cases:
            rec = json.loads((t / name / "screening_record.json").read_text())
            assert rec["disposition"]["state"] == expected
            assert rec["checks"]["R13"]["status"] == "pass"
            results.append({"case": name, "state": expected, "pass": True})
    return results


def old_ledger() -> list[dict]:
    ids = ("coveragepy__016af5f6", "datalad__58ba5165", "numpy__43e333e2")
    rows = []
    for kind in ("noop", "gold"):
        src = ROOT / f"runs/r2e_rf_20260923/remote/ledger_r2e_all_{kind}_local_local.jsonl"
        for line in src.read_text().splitlines():
            row = json.loads(line)
            if row["instance_id"].startswith(ids):
                assert Path(row["log"]["path"]).is_file()
                rows.append(row)
    assert len(rows) == 6
    path = RUNS / "original_r_f_six_rows.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    output = RUNS / "current_tool_old_ledger"
    cmd = [str(PYTHON), "scripts/reconcile_r2e.py", "--repo-root", str(ROOT), "--ledger", str(path),
           "--m3-root", str(ROOT / "runs/env_overnight_20260916/M3"), "--out", str(output)]
    proc = subprocess.run(cmd, cwd=ROOT / "rh2", text=True, capture_output=True, check=False)
    (RUNS / "historical_cli.txt").write_text(proc.stdout + proc.stderr)
    assert proc.returncode == 0, proc.stderr
    result = json.loads((output / "reconcile.json").read_text())
    return [{"task": x["instance_id"], "kind": x["kind"], "source_run_reward": x["rh2_report"]["reward"],
             "assigned_material_revisions": x["material_revisions"], "hidden_tests_revised": x["hidden_tests_revised"],
             "reference_reward_with_current_expected": sorted({c["reference_prime_reward"] for c in x["comparisons"]}),
             "reference_ledger_consistent": x["reference_ledger_consistent"], "agree": x["agree"]} for x in result]


def order_tests() -> list[dict]:
    target = "tests/contract_slime_async/test_dp_schedule_differential.py"
    previous = "tests/envpack/test_reconcile_r2e.py"
    # 不修改维护测试：只在独立子进程加载这个临时 plugin，验证恢复脚本导入前 sys.path 是否足够。
    plugin = '''
import sys
import pytest

class RestorePath:
    @pytest.hookimpl(hookwrapper=True)
    def pytest_fixture_setup(self, fixturedef, request):
        saved = list(sys.path)
        yield
        if fixturedef.argname == "reconcile":
            fixturedef.addfinalizer(lambda: sys.path.__setitem__(slice(None), saved))

raise SystemExit(pytest.main(sys.argv[1:], plugins=[RestorePath()]))
'''
    cases = [
        ("pair_current", [str(PYTHON), "-m", "pytest", "-q", "--tb=short", previous, target]),
        ("pair_without_two_new_revision_tests", [str(PYTHON), "-m", "pytest", "-q", "--tb=short", previous, target,
         "-k", "not expected_revised and not source_expected_reversal"]),
        ("pair_restore_import_path", [str(PYTHON), "-c", plugin, "-q", "--tb=short", previous, target]),
    ]
    results = []
    for name, cmd in cases:
        p = subprocess.run(cmd, cwd=ROOT / "rh2", text=True, capture_output=True, check=False)
        text = p.stdout + p.stderr
        (RUNS / f"{name}.txt").write_text(text)
        results.append({"case": name, "exit_code": p.returncode,
                        "last_lines": text.strip().splitlines()[-3:]})
    assert results[0]["exit_code"] == results[1]["exit_code"] == 1
    assert results[2]["exit_code"] == 0
    return results


def main() -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    result = {"r13": check_r13(), "historical_ledger_with_current_tool": old_ledger(), "test_import_order": order_tests()}
    (OUT / "tool_boundaries.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
