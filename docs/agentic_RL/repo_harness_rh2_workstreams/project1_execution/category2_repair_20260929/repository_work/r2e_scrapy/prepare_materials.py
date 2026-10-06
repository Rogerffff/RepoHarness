"""Scrapy a95a 的离线材料准备与既有证据核对；不启动 Docker 或评分作业。"""

from __future__ import annotations

import ast
import copy
import difflib
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "rh2/src"))

from repoharness2.envpack import ingest_r2e_subset as ingest
from repoharness2.envpack.bundles_v2 import r2e_hidden_tests_tree_digest
from repoharness2.envpack.r2e_parsers import normalize_status_map, parse_log_pytest, prime_calculate_reward

IID = "scrapy__a95a338eeada7275a5289cf036136610ebaf07eb"
EXEC = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution"
OLD = EXEC / "r2e_lifecycle_20260929/results" / IID
PRIVATE = ROOT / "runs/r2e_static_prep_20260924/v3/private" / IID
PUBLIC = ROOT / "runs/r2e_static_prep_20260924/v3/public" / IID
OWNER = "01a0fd64-a083-76d2-95e6-81e7e07c3b44"


def digest(data: bytes | str) -> str:
    return "sha256:" + hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def save(path: Path, data: bytes | str | dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, (dict, list)):
        data = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_bytes(data.encode() if isinstance(data, str) else data)


def apply_edits(text: str, edits: list[dict]) -> str:
    for edit in edits:
        assert text.count(edit["old"]) == 1, "替换目标不唯一"
        text = text.replace(edit["old"], edit["new"], 1)
    return text


def warning_count(filter_category: type[Warning], emitted_category: type[Warning]) -> int:
    # 模拟 runner 的 ignore 和测试 setUp；不执行 Scrapy、pytest 或候选补丁。
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        warnings.simplefilter("always", filter_category)
        with warnings.catch_warnings(record=True) as caught:
            warnings.warn("generator callback returns a value", emitted_category)
        return len(caught)


def local_warning_scope_check() -> dict:
    """只验证记录块进入/退出时的过滤器范围，不执行项目代码。"""
    outside = []
    inside = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        baseline = list(warnings.filters)
        with warnings.catch_warnings(record=True) as outer:
            warnings.warn("unrelated before block", RuntimeWarning)
            for category in (UserWarning, RuntimeWarning):
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always", Warning)
                    warnings.warn("generator callback returns a value", category)
                inside.append(len(caught))
                assert warnings.filters == baseline
            warnings.warn("unrelated after block", RuntimeWarning)
            outside = list(outer)
        try:
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always", Warning)
                raise AssertionError("模拟断言失败")
        except AssertionError:
            pass
        assert warnings.filters == baseline
    assert inside == [1, 1] and outside == []
    return {"inside_UserWarning": inside[0], "inside_RuntimeWarning": inside[1],
            "outside_recorded": len(outside), "filters_restored_after_block_and_exception": True,
            "limitation": "记录块内部的无关警告仍会影响原条数断言，须在目标运行日志中核对。"}


def main() -> None:
    draft = json.loads((OLD / "revision_draft.json").read_text())
    trusted = ingest.load_trusted_r2e_ingest_outputs(ROOT)
    rows, _ = ingest.load_r2e_rows(ROOT, trusted.pins)
    row = next(x for x in rows if x["repo_name"] == "scrapy" and x["commit_hash"] == IID.split("__")[1])
    fact = trusted.image_facts[row["commit_hash"]]
    assert IID not in trusted.revisions, "本题已正式登记：先核新版本，不继续生成旧父版请求"
    source_codes = json.loads(row["execution_result_content"])["test_file_codes"]
    assert source_codes == [(PRIVATE / "hidden_tests/test_1.py").read_text()]
    parent = source_codes[0]
    assert digest(parent) == draft["parent_material"]["hidden_test_file_sha256"]
    assert digest(row["expected_output_json"]) == draft["parent_material"]["expected_output_sha256"]
    assert r2e_hidden_tests_tree_digest(fact.hidden_files) == draft["parent_material"]["hidden_tests_tree_sha256"]
    assert fact.run_tests_sh_sha256 == draft["parent_material"]["run_tests_sh_sha256"]

    checked_files = {}
    for name, expected in {**draft["trial_inputs"], **draft["trial_sha256"]}.items():
        path = OLD / name
        assert digest(path.read_bytes()) == expected, name
        checked_files[rel(path)] = expected
    for candidate, expected in draft["candidate_patch_sha256"].items():
        path = PRIVATE / "gold.patch" if candidate == "gold" else OLD / f"cands/scrapy_a95a_{candidate}.patch"
        assert digest(path.read_bytes()) == expected, candidate
        checked_files[rel(path)] = expected

    rev2_edits = draft["revisions"][0]["edits"]
    assert json.loads((OLD / "trials/inputs/draft_a95a_r1r2_v2.json").read_text())["revisions"] == draft["revisions"]
    rev2 = apply_edits(parent, rev2_edits)
    assert digest(rev2) == draft["revised_hidden_test_sha256"]
    rev2_files = dict(fact.hidden_files)
    rev2_files["test_1.py"] = digest(rev2)
    assert r2e_hidden_tests_tree_digest(rev2_files.items()) == draft["revised_hidden_tests_tree_sha256"]

    expected_edits = [
        {"old": f'"{key}": "FAILED"', "new": f'"{key}": "PASSED"'}
        for key in draft["expected_change"]["changed"]
    ]
    expected_text = apply_edits(row["expected_output_json"], expected_edits)
    expected = json.loads(expected_text)
    assert expected == draft["expected_after"]
    assert expected_text == (OLD / "trials/inputs/expected_after_a95a.json").read_text()
    trials = []
    for path in sorted((OLD / "trials").glob("rev2_*.json")):
        x = json.loads(path.read_text())
        candidate = path.stem.removeprefix("rev2_").split("_")[0]
        want = draft["acceptance"][candidate]
        observed = normalize_status_map(parse_log_pytest(x["log_tail"]))
        failed = sorted(key for key, value in observed.items() if expected[key] != value)
        assert set(observed) == set(expected) and observed == x["observed"]
        assert failed == sorted(want["expected_fail_keys"])
        assert prime_calculate_reward(x["log_tail"], expected_text) == want["expected_score"]
        assert x["task"] == IID and x["image"] == draft["trial_image"]["image_id"]
        assert x["recipe_id"] == draft["trial_image"]["recipe_id"]
        assert x["kind"] == "trial_not_formal_grading" and x["markers"]
        assert x["log_tail"].count(">>>>> Start Test Output") == 1
        assert x["log_tail"].count(">>>>> End Test Output") == 1
        assert "collected 5 items" in x["log_tail"]
        assert "RH2_TRIAL_EDITS_APPLIED=1" in x["edits_apply"]
        assert not x["missing"] and not x["extra"]
        assert x["match"] == (not failed)
        if candidate != "noop":
            assert "RH2_APPLY_RC=0" in x["apply"]
        positions = sorted(set(map(int, re.findall(r"/testbed/r2e_tests/test_1.py:(\d+):", x["log_tail"]))))
        trials.append({"path": rel(path), "candidate": candidate, "score_recomputed": want["expected_score"],
                       "mismatched_keys": failed, "failure_lines": positions, "scope": "historical_trial_only"})
    assert len(trials) == 9

    warning_check = {
        "scope": "local_standard_library_only_not_target_grading",
        "python": sys.version.split()[0],
        "rev2_UserWarning": warning_count(UserWarning, UserWarning),
        "rev2_RuntimeWarning": warning_count(UserWarning, RuntimeWarning),
        "proposed_UserWarning": warning_count(Warning, UserWarning),
        "proposed_RuntimeWarning": warning_count(Warning, RuntimeWarning),
    }
    assert list(warning_check.values())[-4:] == [1, 0, 1, 1]
    rev3_edits = copy.deepcopy(rev2_edits)
    rev3_edits[0]["new"] = rev3_edits[0]["new"].replace("warnings.simplefilter(\"always\", UserWarning)",
                                                          "warnings.simplefilter(\"always\", Warning)")
    rev3_edits[0]["new"] = rev3_edits[0]["new"].replace(
        "# so the UserWarnings recorded below were never visible; re-enable them per test.",
        "# 按测试恢复警告记录；公开断言不限定警告类别。")
    rev3 = apply_edits(parent, rev3_edits)
    # 记录块局部恢复：不新增 setUp，不改变块外 warning 策略；每个原测试方法唯一替换。
    parent_tree = ast.parse(parent)
    parent_class = next(n for n in parent_tree.body if isinstance(n, ast.ClassDef) and n.name == "UtilsMiscPy3TestCase")
    parent_lines = parent.splitlines(True)
    catch_line = "        with warnings.catch_warnings(record=True) as w:\n"
    rev4_edits = []
    record_blocks = 0
    for method in parent_class.body:
        if not isinstance(method, ast.FunctionDef):
            continue
        old_method = "".join(parent_lines[method.lineno - 1:method.end_lineno])
        count = old_method.count(catch_line)
        if count:
            new_method = old_method.replace(catch_line, catch_line + "            warnings.simplefilter(\"always\", Warning)\n")
            rev4_edits.append({"old": old_method, "new": new_method})
            record_blocks += count
    assert record_blocks == 22 and len(rev4_edits) == 4
    rev4_edits.append(copy.deepcopy(rev2_edits[1]))
    rev4 = apply_edits(parent, rev4_edits)
    assert "def setUp(" not in rev4
    assert rev4.count('warnings.simplefilter("always", Warning)') == 22
    rev2_partial = next(n for n in ast.parse(rev2).body if isinstance(n, ast.ClassDef)).body[-1]
    rev4_partial = next(n for n in ast.parse(rev4).body if isinstance(n, ast.ClassDef)).body[-1]
    assert ast.dump(rev2_partial) == ast.dump(rev4_partial)
    class StripWarningSupport(ast.NodeTransformer):
        def visit_ClassDef(self, node):
            node.body = [n for n in node.body if not isinstance(n, ast.FunctionDef) or n.name != "setUp"]
            return self.generic_visit(node)

        def visit_Expr(self, node):
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "simplefilter":
                return None
            return node

    assert ast.dump(StripWarningSupport().visit(ast.parse(rev2))) == ast.dump(StripWarningSupport().visit(ast.parse(rev4)))
    warning_check["rev4_record_block_scope"] = local_warning_scope_check()
    for name, text in [("rev2", rev2), ("rev3", rev3), ("rev4", rev4)]:
        tree = ast.parse(text)
        test_class = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "UtilsMiscPy3TestCase")
        keys = {f"UtilsMiscPy3TestCase.{n.name}" for n in test_class.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}
        assert keys == set(expected)
        save(OUT / f"materials/{name}/r2e_tests/test_1.py", text)
    save(OUT / "materials/expected_output.json", expected_text)
    save(OUT / "materials/rev2_to_rev3.diff", "".join(difflib.unified_diff(rev2.splitlines(True), rev3.splitlines(True),
                                                                         fromfile="rev2/test_1.py", tofile="rev3/test_1.py")))
    save(OUT / "materials/rev2_to_rev4.diff", "".join(difflib.unified_diff(rev2.splitlines(True), rev4.splitlines(True),
                                                                         fromfile="rev2/test_1.py", tofile="rev4/test_1.py")))

    # 准备一个类别变化对照：继承 C1 的目标行为，仅改变 warning 类别；正式语义资格待非作者核查。
    with tempfile.TemporaryDirectory(prefix="scrapy-a95a-offline-") as scratch:
        temp = Path(scratch)
        target = temp / "scrapy/utils/misc.py"
        target.parent.mkdir(parents=True)
        target.write_bytes((PUBLIC / "worktree/scrapy/utils/misc.py").read_bytes())
        subprocess.run(["git", "apply", "--check", str(OLD / "cands/scrapy_a95a_C1.patch")], cwd=temp, check=True, capture_output=True)
        subprocess.run(["git", "apply", str(OLD / "cands/scrapy_a95a_C1.patch")], cwd=temp, check=True, capture_output=True)
        c1_text = target.read_text()
        ast.parse(c1_text)
        assert c1_text.count("                stacklevel=2,\n") == 1
        assert c1_text.count("            stacklevel=2,\n") == 2
        category_text = re.sub(r"(?m)^([ ]+)stacklevel=2,$", r"\1category=RuntimeWarning,\n\1stacklevel=2,", c1_text)
        assert category_text.count("category=RuntimeWarning") == 2
        ast.parse(category_text)
        category_patch = "diff --git a/scrapy/utils/misc.py b/scrapy/utils/misc.py\n" + "".join(
            difflib.unified_diff((PUBLIC / "worktree/scrapy/utils/misc.py").read_text().splitlines(True),
                                 category_text.splitlines(True), fromfile="a/scrapy/utils/misc.py", tofile="b/scrapy/utils/misc.py"))
        target.write_bytes((PUBLIC / "worktree/scrapy/utils/misc.py").read_bytes())
        patch = temp / "category.patch"
        patch.write_text(category_patch)
        subprocess.run(["git", "apply", "--check", str(patch)], cwd=temp, check=True, capture_output=True)
        save(OUT / "candidates/C1_RuntimeWarning.patch", category_patch)

    entries = []
    for kind, target, edits, before, after, revised_file, change, reason in [
        ("hidden_test_text_replace", "test_1.py", rev4_edits, digest(parent), digest(rev4),
         f"docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/files/{IID}/r2e_tests/test_1.py", None,
         "R-c 保留 rev2 的三条 partial 断言；R-a 仅在已有22个记录块内部恢复 Warning 记录，不新增 setUp 或 UserWarning 类别限制。"),
        ("expected_text_replace", "expected_output_json", expected_edits, digest(row["expected_output_json"]),
         digest(expected_text), None, draft["expected_change"], "两条已有公开警告测试恢复执行，期望 FAILED→PASSED；五键及顺序不变。"),
    ]:
        entries.append({"revision_id": None, "instance_id": IID, "kind": kind, "target": target,
                        "edits": edits, "sha256_before": before, "sha256_after": after, "revised_file": revised_file,
                        "expected_change": change, "decision_ref": "统一标准 v1 §5 / §9 D4；题级草案待非作者复核与正式验收",
                        "reason": reason, "evidence": [rel(OLD / "revision_plan.md"), rel(OUT / "preparation.md")]})
    # 仅在内存中赋临时编号验证现有 parser；不占用正式编号，也不发布 pins。
    preview = copy.deepcopy(entries)
    for number, entry in enumerate(preview, start=998):
        entry["revision_id"] = f"r2e-mr-{number:03d}"
    revs = ingest.parse_r2e_material_revisions({"schema_id": ingest.R2E_MATERIAL_REVISIONS_SCHEMA_ID, "revisions": preview})[IID]
    assert ingest.apply_expected_revisions(IID, row["expected_output_json"], revs) == expected_text
    effective_files = ingest.apply_hidden_test_revisions(IID, fact.hidden_files, {"test_1.py": parent}, revs)
    assert dict(effective_files)["test_1.py"] == digest(rev4)
    review = (OUT / "review_rev4_20261003.md").read_text()
    assert digest(rev4).removeprefix("sha256:") in review, "材料变更后先核新差异，不能沿用旧审查状态"
    matrix = [{"candidate": k, "patch": None if k == "noop" else rel(PRIVATE / "gold.patch") if k == "gold"
               else rel(OLD / f"cands/scrapy_a95a_{k}.patch"), "repeats": 1,
               "expected_score": v["expected_score"], "expected_fail_keys": v["expected_fail_keys"]}
              for k, v in draft["acceptance"].items()]
    matrix.append({"candidate": "C1_RuntimeWarning", "patch": rel(OUT / "candidates/C1_RuntimeWarning.patch"),
                   "repeats": 1, "expected_score": 1, "expected_fail_keys": [],
                   "semantic_review": "non_author_static_no_blocker_runtime_pending",
                   "purpose": "检验类别变化是否被 rev2 误拒，及记录块局部恢复稿是否保留公开条数／文案行为。"})
    save(OUT / "acceptance_matrix.json", {"instance_id": IID, "scope": "expected_not_run",
                                          "historical_rev2_runs": 9, "current_revision": "rev4_record_blocks", "current_planned_runs": 8,
                                          "rows": matrix, "unchanged_key_count": 5,
                                          "paired_diagnostic_not_in_current_count": {
                                              "candidate": "C1_RuntimeWarning", "material": "rev2", "repeats": 1,
                                              "expected_score": 0,
                                              "expected_fail_keys": draft["acceptance"]["C2b"]["expected_fail_keys"],
                                              "purpose": "需要目标环境直接确认误拒时，与 rev4 类别对照配对；不复跑旧九方试跑。"},
                                          "repeat_policy": "旧C1/noop重复试跑已齐；新固定版本先覆盖8个唯一候选，异常或稳定性疑点才补重复。",
                                          "requirements": ["冻结材料/镜像/入口版本", "完整日志、候选 apply 与五键核对",
                                                           "C1 为正对照，原 gold 保留负对照", "分列旧试跑、正式评分与类别对照"]})
    commands = json.loads((OLD / "commands.json").read_text())
    selected = [x for x in commands if x["id"] in {"env_python_scrapy", "repro_issue_example", "pytest_generator_return_tests"}]
    for command in selected:
        if command["id"] == "repro_issue_example":
            command["expect"] = "zero"
            command["purpose"] = "仅在 C1 验收容器内：文件形式复现应打印 False，退出码0；不使用 python -c 定义待检查生成器。"
    save(OUT / "devcheck_commands.json", selected)
    request = {"scope": "private_preparation_not_published", "as_of": "2026-10-03", "instance_id": IID,
               "owner_thread_id": OWNER, "prepared_revision": "rev4_record_blocks_draft",
               "shared_publisher": {"thread_id": "01a08bd3-b639-7c71-a1ee-f3f4d05b3a0e", "name": "负责处理分类二的明确问题"},
               "shared_revision_ids": "publisher_to_assign_do_not_reuse_064",
               "entries_template": entries, "local_material_file": rel(OUT / "materials/rev4/r2e_tests/test_1.py"),
               "local_expected_file": rel(OUT / "materials/expected_output.json"),
               "parent": {"base_commit": fact.head_commit, "source_image_ref": fact.source_image_ref,
                          "source_manifest_digest": fact.manifest_digest, "hidden_tests_tree_sha256": r2e_hidden_tests_tree_digest(fact.hidden_files),
                          "expected_output_sha256": digest(row["expected_output_json"]),
                          "current_revision_ids": [], "statement_sha256": digest(row["problem_statement"]),
                          "run_tests_sh_sha256": fact.run_tests_sh_sha256},
               "candidate_material": {"hidden_tests_tree_sha256": r2e_hidden_tests_tree_digest(effective_files),
                                      "expected_output_sha256": digest(expected_text), "public_statement_changed": False,
                                      "grading_script_changed": False},
               "positive_control": draft["env_reverify_positive_control"],
               "material_static_review": {"status": "no_static_blocker", "scope": "non_author_static_only",
                                         "path": rel(OUT / "review_rev4_20261003.md"), "formal_acceptance": False},
               "remaining": ["CPU核Warning实际记录列表、C1与类别候选及负例，静态窄核已完成", "共享维护者分配编号、安放文件并封板 ingest/pins",
                             "CPU 新宿主与派生材料镜像验收", "正式矩阵与 C1 公开开发验证", "统一探针接收及消息交付核对"],
               "probe_ready": False, "model_config_ref": rel(EXEC / "ordinary_probe_20260929/gpu_coordination_decisions_20261002.md")}
    save(OUT / "revision_request.json", request)
    report = {"as_of": "2026-10-03", "scope": "offline_only_no_container_no_model",
              "trusted_parent_verified": True, "rev2_source_and_trial_edits_equal": True,
              "rev2_hidden_test_sha256": digest(rev2), "rev2_trials_recomputed": trials,
              "existing_source_hashes_verified": checked_files, "warning_filter_check": warning_check,
              "schema_preview": "passed_with_memory_only_ids_998_999_not_reserved",
              "prepared_revision": "rev4_record_blocks_draft", "record_blocks_with_local_filter": record_blocks,
              "test_ast_equal_after_removing_warning_support": True,
              "proposed_hidden_test_sha256": digest(rev4), "proposed_hidden_tests_tree_sha256": r2e_hidden_tests_tree_digest(effective_files),
              "formal_acceptance": "not_run", "independent_review_of_new_changes": "non_author_static_no_blocker_runtime_pending",
              "input_snapshot": {rel(ROOT / "rh2/src/repoharness2/envpack/ingest_r2e_subset.py"): digest((ROOT / "rh2/src/repoharness2/envpack/ingest_r2e_subset.py").read_bytes()),
                                 rel(OLD / "revision_draft.json"): digest((OLD / "revision_draft.json").read_bytes())}}
    save(OUT / "offline_checks.json", report)
    print(json.dumps({"historical_rev2_trials_recomputed": len(trials), "prepared_key_count": len(expected),
                      "warning_filter_check": warning_check, "formal_acceptance": "not_run"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
