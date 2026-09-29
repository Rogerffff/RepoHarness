"""`scripts/screening_facts.py`（环境筛查只读汇总工具）的回归测试。

分两层：

1. 纯函数层（不依赖任何证据文件）：事实信封校验、官方状态口径规约、逐 ID 桶还原、
   安装段线索抽取。这些断言钉住的是**口径**，改了要有明确理由。
2. e1 真机样例层：用 `runs/swe_grading_wiring_20260915/e1/` 的账本、eval 日志、sidecar、
   冻结工件跑一次完整汇总，断言与 `e1_report_20260915.md` / `e1_codex_review_20260916.md`
   里的数字一致。**证据文件不在本机时整层 skip**（证据目录是 git-ignore 的）。
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "rh2" / "scripts" / "screening_facts.py"

_spec = importlib.util.spec_from_file_location("screening_facts_under_test", _SCRIPT)
assert _spec is not None and _spec.loader is not None
screening_facts = importlib.util.module_from_spec(_spec)
sys.modules["screening_facts_under_test"] = screening_facts
# 脚本导入时把 rh2/src 插到 sys.path 首位；收集期就还原，免得污染其它测试的导入（例 reference/slime 的差分测试会
# 按被污染的路径取到 vendored slime；Codex 09-24 批次二复核 F1 同类问题）。repoharness2 已装在 venv 里，还原后仍可导入。
_saved_sys_path = list(sys.path)
try:
    _spec.loader.exec_module(screening_facts)
finally:
    sys.path[:] = _saved_sys_path

# ---- e1 证据位置（都在 git-ignore 的 runs/ 与冻结 ingest 下）----
_E1 = _REPO_ROOT / "runs" / "swe_grading_wiring_20260915" / "e1"
_LEDGERS = [_E1 / "ledger_e1.jsonl", _E1 / "ledger_e1_pandas.jsonl"]
_EVAL_LOGS = _E1 / "eval_logs"
_ARTIFACTS = _E1 / "artifacts"
_BUNDLES = (
    _REPO_ROOT / "docs" / "agentic_RL" / "repo_harness_rh2_workstreams" / "s2" / "ingest"
    / "grading_bundles_v2_v0.jsonl"
)
_ORACLE = [
    _REPO_ROOT / "runs" / "env_probe_stage1_20260910" / "ledger" / "stage1_offline.jsonl",
    _REPO_ROOT / "runs" / "env_probe_stage1_20260910" / "ledger" / "stage1_continuation_20260911" / "stage1_offline.jsonl",
]

_REQUIRED = [*_LEDGERS, _EVAL_LOGS, _ARTIFACTS, _BUNDLES]
_HAVE_E1 = all(path.exists() for path in _REQUIRED)
_e1_only = pytest.mark.skipif(not _HAVE_E1, reason=f"缺 e1 样例证据（{_E1}）；本层只在有真机证据的机器上跑")


# --------------------------------------------------------------------------- 纯函数层


def test_fact_envelope_defaults_and_validation() -> None:
    assert screening_facts.fact(1, "static") == {"value": 1, "source": "static", "status": "observed"}
    assert screening_facts.fact(None, "static")["status"] == "missing"
    # False / 0 是取到的值，不能因为 falsy 就判 missing
    assert screening_facts.fact(False, "host_observation")["status"] == "observed"
    assert screening_facts.fact(0, "host_observation")["status"] == "observed"
    assert screening_facts.fact(None, "oracle", status="not_applicable")["status"] == "not_applicable"
    with pytest.raises(ValueError):
        screening_facts.fact(1, "guesswork")
    with pytest.raises(ValueError):
        screening_facts.fact(1, "static", status="probably")


def test_bucket_of_status_follows_official_semantics() -> None:
    # swebench 4.1.0 `test_passed`：PASSED/XFAIL 计通过；SKIPPED 不进成功/失败任何一桶；其余计失败。
    assert screening_facts.bucket_of_status("PASSED") == "passed"
    assert screening_facts.bucket_of_status("XFAIL") == "passed"
    assert screening_facts.bucket_of_status("SKIPPED") == "skipped"
    assert screening_facts.bucket_of_status("FAILED") == "failed"
    assert screening_facts.bucket_of_status("ERROR") == "failed"
    assert screening_facts.bucket_of_status("ERROR:") == "failed"  # 阶段一 status_map 里出现过的带冒号变体
    assert screening_facts.bucket_of_status(None) == "missing"  # 缺席官方计失败，但本表单独标 missing


def test_rh2_buckets_rebuilds_per_id_table() -> None:
    verdict = SimpleNamespace(
        f2p_success=["t::a"], f2p_failure=["t::b"],
        p2p_success=["t::c"], p2p_failure=["t::d", "t::e"],
        reference_missing=["t::d"], reference_skipped=["t::f"],
    )
    table = screening_facts.rh2_buckets(verdict, ["t::a", "t::b"], ["t::c", "t::d", "t::e", "t::f"])
    assert table == {
        "t::a": "passed", "t::b": "failed", "t::c": "passed",
        "t::d": "missing",  # 缺席优先于"在 failure 桶里"，保留成因
        "t::e": "failed", "t::f": "skipped",
    }


def test_install_segment_evidence_reads_last_command_and_errors() -> None:
    log = "\n".join([
        "+ echo RH2_PHASE_START=install",
        "RH2_PHASE_START=install",
        "+ python -m pip install -e .",
        "      ERROR: No matching distribution found for setuptools>=40.6.2",
        "+ python -m pip install pytest",
        "+ hash -r",
        "+ RH2_INSTALL_RC=0",
        "+ echo RH2_INSTALL_RC=0",
        "RH2_INSTALL_RC=0",
        "+ echo RH2_PHASE_END=install",
        "RH2_PHASE_END=install",
        "ERROR: 段外的错误行不算进安装段",
    ])
    evidence = screening_facts.install_segment_evidence(log)
    # 段末退出码属于 `hash -r`，不属于失败的 `pip install -e .`
    assert evidence["last_command"] == "hash -r"
    assert evidence["error_lines"] == ["ERROR: No matching distribution found for setuptools>=40.6.2"]
    assert screening_facts.install_segment_evidence("没有标记的日志") == {"last_command": None, "error_lines": []}


def test_walk_facts_collapses_list_indices() -> None:
    tree = {"a": screening_facts.fact(1, "static"), "b": [screening_facts.fact(None, "oracle")]}
    assert dict(screening_facts.walk_facts(tree)).keys() == {"a", "b[]"}


# --------------------------------------------------------------------------- e1 样例层


@pytest.fixture(scope="module")
def e1_facts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, dict]:
    if not _HAVE_E1:
        pytest.skip("缺 e1 样例证据")
    out_dir = tmp_path_factory.mktemp("facts_e1")
    ns = screening_facts.parse_args([
        *sum([["--ledger", str(p)] for p in _LEDGERS], []),
        "--eval-log-dir", str(_EVAL_LOGS),
        "--artifacts-dir", str(_ARTIFACTS),
        "--grading-bundles", str(_BUNDLES),
        *sum([["--oracle-ledger", str(p)] for p in _ORACLE if p.is_file()], []),
        "--out-dir", str(out_dir),
    ])
    summary = screening_facts.run(ns)
    facts = {
        path.parent.name: json.loads(path.read_text(encoding="utf-8"))
        for path in out_dir.glob("*/facts.json")
    }
    facts["__summary__"] = summary
    facts["__out_dir__"] = str(out_dir)  # type: ignore[assignment]
    return facts


def _value(node: dict) -> object:
    return node["value"]


def _run_of(facts: dict, kind: str, ledger_name: str) -> dict:
    hits = [
        run for run in facts["runs"]
        if _value(run["run_ref"]["candidate_kind"]) == kind
        and Path(str(_value(run["run_ref"]["ledger_path"]))).name == ledger_name
    ]
    assert len(hits) == 1, f"{kind}/{ledger_name} 命中 {len(hits)} 条"
    return hits[0]


@_e1_only
def test_e1_shape_and_outputs(e1_facts: dict) -> None:
    summary = e1_facts["__summary__"]
    assert summary["tasks"] == 4 and summary["runs"] == 10  # 主批 8 行 + pandas 复跑 2 行
    out_dir = Path(str(e1_facts["__out_dir__"]))
    assert (out_dir / "reconcile.md").is_file() and (out_dir / "summary.json").is_file()
    assert summary["grading_bundles_loaded"] == 216
    assert summary["grading_bundles_rejected"] == []
    assert summary["ledger_rows_with_unknown_schema"] == []


@_e1_only
def test_e1_inputs_are_not_modified(tmp_path: Path) -> None:
    """只读工具：再跑一次之后，所有输入文件的 (大小, mtime) 快照必须逐字节相同。"""

    watched = sorted(
        [*_LEDGERS, _BUNDLES, *_EVAL_LOGS.rglob("*"), *_ARTIFACTS.rglob("*")],
        key=str,
    )

    def snapshot() -> dict[str, tuple[int, float]]:
        return {str(p): (p.stat().st_size, p.stat().st_mtime) for p in watched if p.is_file()}

    before = snapshot()
    ns = screening_facts.parse_args([
        *sum([["--ledger", str(p)] for p in _LEDGERS], []),
        "--eval-log-dir", str(_EVAL_LOGS),
        "--artifacts-dir", str(_ARTIFACTS),
        "--grading-bundles", str(_BUNDLES),
        "--out-dir", str(tmp_path / "out"),
    ])
    screening_facts.run(ns)
    assert snapshot() == before
    # 输出只落在 --out-dir 里
    assert {p.name for p in (tmp_path / "out").iterdir()} >= {"reconcile.md", "summary.json"}


@_e1_only
def test_e1_mypy_matches_report(e1_facts: dict) -> None:
    facts = e1_facts["python__mypy-12741"]
    assert _value(facts["reference"]["f2p_total"]) == 1 and _value(facts["reference"]["p2p_total"]) == 1

    noop = _run_of(facts, "noop", "ledger_e1.jsonl")
    gold = _run_of(facts, "gold", "ledger_e1.jsonl")
    assert (_value(noop["scoring"]["outcome"]), _value(noop["scoring"]["reward"])) == ("unresolved", 0.0)
    assert (_value(gold["scoring"]["outcome"]), _value(gold["scoring"]["reward"])) == ("resolved", 1.0)
    assert (_value(noop["scoring"]["f2p_pass"]), _value(noop["scoring"]["f2p_total"])) == (0, 1)
    assert (_value(gold["scoring"]["f2p_pass"]), _value(gold["scoring"]["f2p_total"])) == (1, 1)
    assert _value(noop["parser"]["num_parsed_tests"]) == 2

    # e1_codex_review_20260916.md §4.2：安装段末命令是 `hash -r`，rc=0 不证明可编辑安装成功。
    for run in (noop, gold):
        segment = run["candidate_segment"]
        assert _value(segment["install_rc_last_command"]) == 0
        assert _value(segment["install_segment_last_command"]) == "hash -r"
        assert _value(segment["install_segment_error_line_count"]) == 2
        assert any("setuptools" in line for line in _value(segment["install_segment_error_lines"]))


@_e1_only
def test_e1_pandas_gold_matches_report(e1_facts: dict) -> None:
    """e1_report_20260915.md §5：F2P 16/16、P2P 失败 3/1020、解析 1037、参考缺席 3、版本串带 .dirty。"""

    facts = e1_facts["pandas-dev__pandas-48106"]
    gold = _run_of(facts, "gold", "ledger_e1_pandas.jsonl")
    scoring, parser = gold["scoring"], gold["parser"]
    assert (_value(scoring["outcome"]), _value(scoring["reward"])) == ("unresolved", 0.0)
    assert (_value(scoring["f2p_pass"]), _value(scoring["f2p_total"])) == (16, 16)
    assert (_value(scoring["p2p_fail"]), _value(scoring["p2p_total"])) == (3, 1020)
    assert _value(parser["num_parsed_tests"]) == 1037
    assert _value(parser["num_parsed_outside_segment"]) == 1
    assert _value(parser["reference_missing_count"]) == 3
    assert all("test_contains_raise_error_if_period_index_is_in_multi_index" in case
               for case in _value(parser["reference_missing"]))
    assert ".dirty" in str(_value(gold["observation"]["pkg_version"]))
    # 两侧缺同三个 ID → 逐 ID 无差异（codex 复核结论）
    assert _value(gold["per_id_status"]["diff_count"]) == 0


@_e1_only
def test_e1_offline_reparse_agrees_with_grader(e1_facts: dict) -> None:
    """离线重解析必须与当时 grader 写的 sidecar 诊断和账本计数逐字段一致。"""

    checked = 0
    for key, facts in e1_facts.items():
        if key.startswith("__"):
            continue
        for run in facts["runs"]:
            parser = run["parser"]
            if not _value(parser["available"]) or _value(parser["apply_ok"]) is not True:
                continue
            assert _value(parser["matches_sidecar_verdict"]) is True, run["run_ref"]
            assert _value(parser["matches_ledger_report_counts"]) is True, run["run_ref"]
            assert _value(run["log"]["sha256_verified"]) is True, run["run_ref"]
            checked += 1
    assert checked == 7  # e1 里真正跑到测试并出报告的 7 次（其余 3 次是 infra 失败）


@_e1_only
def test_e1_per_id_status_has_no_oracle_diff_for_graded_runs(e1_facts: dict) -> None:
    """跑到测试的运行，逐参考 ID 状态与阶段一 oracle 无差异（含 pandas 的 3 个缺席 ID）。"""

    if not any(p.is_file() for p in _ORACLE):
        pytest.skip("缺阶段一 oracle 账本")
    compared = 0
    for key, facts in e1_facts.items():
        if key.startswith("__"):
            continue
        for run in facts["runs"]:
            if _value(run["parser"].get("apply_ok")) is not True:
                continue
            per_id = run["per_id_status"]
            if _value(per_id["diff_count"]) is None:
                continue
            assert _value(per_id["diff_count"]) == 0, (run["run_ref"], _value(per_id["diffs"])[:3])
            compared += 1
    assert compared == 7


@_e1_only
def test_e1_infra_failures_are_marked_missing_not_failed(e1_facts: dict) -> None:
    """3 次 infra 失败（pandas 主批两次 + metacopy 前 noop 复跑）不得被当成"测试失败"。"""

    facts = e1_facts["pandas-dev__pandas-48106"]
    failed = [r for r in facts["runs"] if _value(r["scoring"]["outcome"]) == "failed_to_grade"]
    assert len(failed) == 3
    for run in failed:
        assert _value(run["scoring"]["reward"]) is None
        assert _value(run["scoring"]["f2p_total"]) is None
        assert _value(run["parser"]["apply_ok"]) is False
        assert _value(run["parser"]["num_parsed_tests"]) == 0
        assert _value(run["scoring"]["infra_failure_detail"])  # 归因文字在账本里


def test_ledger_fact_distinguishes_absent_key_from_null_value() -> None:
    row = {"present": 1, "explicit_null": None}
    assert screening_facts.ledger_fact(row, "present", "host_observation")["status"] == "observed"
    # 键在场但为 null = 本次确实没有这个事实
    assert screening_facts.ledger_fact(row, "explicit_null", "host_observation")["status"] == "not_applicable"
    # 键根本不在 = 产出账本的 driver 版本更旧（schema 漂移），不能当成"没有这个事实"
    absent = screening_facts.ledger_fact(row, "never_written", "host_observation")
    assert absent["status"] == "missing" and "driver 版本" in absent["note"]


@_e1_only
def test_e1_ledger_schema_drift_is_visible(e1_facts: dict) -> None:
    """e1 账本的 schema_id 仍是 v1，但缺当前 driver 源码会写的若干键——缺项清单要看得见这一点。"""

    facts = e1_facts["python__mypy-12741"]
    run = _run_of(facts, "noop", "ledger_e1.jsonl")
    keys = set(_value(run["run_ref"]["ledger_row_keys"]))
    assert "schema_id" in keys and "report" in keys
    for absent_key in ("baseline_policy_version", "omitted_cache_count",
                       "candidate_test_like_paths", "candidate_touched_conftest_or_fixture"):
        assert absent_key not in keys
    assert _value(run["candidate"]["baseline_policy_version"]) is None
    assert run["candidate"]["baseline_policy_version"]["status"] == "missing"
    assert run["observation"]["candidate_test_like_paths"]["status"] == "missing"
    # 对照：键在场且为 null 的字段标 not_applicable，不混进缺项
    assert run["candidate"]["stage_error"]["status"] == "not_applicable"


@_e1_only
def test_e1_degrades_gracefully_when_repoharness2_import_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """并发编辑 rh2/src 时 import 可能临时抛 SyntaxError：本工具必须降级而不是崩。

    降级后仍产出账本/sidecar/工件/oracle 侧事实，只把离线重解析与逐 ID 对账标成
    `parser_unavailable` 并写清原因。
    """

    monkeypatch.setattr(screening_facts, "parse_eval_log_v2", None)
    monkeypatch.setattr(screening_facts, "PrivateGradingBundleV2", None)
    monkeypatch.setattr(
        screening_facts, "PARSER_IMPORT_ERROR",
        "SyntaxError: invalid syntax (contracts/grading.py, line 317)",
    )
    ns = screening_facts.parse_args([
        *sum([["--ledger", str(p)] for p in _LEDGERS], []),
        "--eval-log-dir", str(_EVAL_LOGS),
        "--artifacts-dir", str(_ARTIFACTS),
        "--grading-bundles", str(_BUNDLES),
        *sum([["--oracle-ledger", str(p)] for p in _ORACLE if p.is_file()], []),
        "--out-dir", str(tmp_path / "out"),
    ])
    summary = screening_facts.run(ns)
    assert summary["tasks"] == 4 and summary["runs"] == 10
    assert summary["parser_available"] is False
    assert summary["grading_bundles_schema_validated"] is False
    assert summary["grading_bundles_loaded"] == 216  # 降级视图照样读出 216 条参考清单

    facts = json.loads((tmp_path / "out" / "python__mypy-12741" / "facts.json").read_text(encoding="utf-8"))
    run = _run_of(facts, "gold", "ledger_e1.jsonl")
    assert _value(run["parser"]["available"]) is False
    assert "parser_unavailable" in run["parser"]["available"]["note"]
    assert "line 317" in run["parser"]["available"]["note"]  # 原因写清，不是笼统的"失败"
    # 不依赖 parser 的字段照常在场
    assert _value(run["scoring"]["outcome"]) == "resolved"
    assert _value(run["log"]["sha256_verified"]) is True
    assert _value(run["candidate_segment"]["install_segment_last_command"]) == "hash -r"
    assert _value(facts["reference"]["f2p_total"]) == 1
    assert _value(facts["oracle"]["gold"]["official_verdict"]) == "RESOLVED_FULL"
    # 逐 ID 对账不可用，且明确标出来，不冒充"无差异"
    assert _value(run["per_id_status"]["available"]) is False
    assert _value(run["per_id_status"]["diff_count"]) is None
