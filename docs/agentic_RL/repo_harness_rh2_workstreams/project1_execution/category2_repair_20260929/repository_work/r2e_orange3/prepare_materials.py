"""生成 orange3 本包的未发布材料；不写共享修订单，不运行 Docker 或项目代码。"""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
HERE = Path(__file__).resolve().parent
EXECUTION = Path("docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution")
S2 = Path("docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e")
OLD_RESULTS = EXECUTION / "r2e_lifecycle_20260929/results"
PUBLIC_ROOT = Path("runs/r2e_static_prep_20260924/v3/public")
PRIVATE_ROOT = Path("runs/r2e_static_prep_20260924/v3/private")
IDS = {
    "22e98f8f": "orange3__22e98f8f4cccc25f0d0217f9f4251b66d49b4237",
    "4014f248": "orange3__4014f2483e3bab0621c9ae0f994947c008183253",
    "50f6a758": "orange3__50f6a758f1c66b8f4a18806714e3c2f4cefcab3e",
    "9b5494e2": "orange3__9b5494e26f407b75e79699c9d40be6df1d80a040",
}


def sha(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return "sha256:" + hashlib.sha256(value).hexdigest()


def read(path: Path) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def record(path: Path) -> dict:
    return {"path": str(path), "sha256": sha((ROOT / path).read_bytes())}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def replace_once(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, "替换目标必须恰好命中一次"
    return text.replace(old, new, 1)


def method(text: str, cls: str, name: str) -> str:
    tree = ast.parse(text)
    c = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)
    m = next(n for n in c.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return "".join(text.splitlines(keepends=True)[m.lineno - 1:m.end_lineno])


def unchanged_other_methods(before: str, after: str, changed: tuple[str, str]) -> int:
    def inventory(text: str) -> dict:
        result = {}
        for c in ast.parse(text).body:
            if isinstance(c, ast.ClassDef):
                for m in c.body:
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        result[(c.name, m.name)] = ast.dump(m, include_attributes=False)
        return result
    a, b = inventory(before), inventory(after)
    assert set(a) == set(b), "不得改变测试方法集合"
    assert all(a[k] == b[k] for k in a if k != changed), "发现题级目标之外的 AST 变化"
    assert a[changed] != b[changed]
    return len(a) - 1


def preparation_inputs(pubs: dict) -> None:
    """冻结候选引用与待运行目标；不生成共享runner或自行分配公共修订号。"""
    actor_cands = Path("runs/r2e_actor_20260925/grader_cands")
    proto = Path("runs/r2e_lifecycle_20260929/probe_proto/runs")
    cand4014 = OLD_RESULTS / IDS["4014f248"] / "cands/orange3_4014_DG_dup_to_empty.patch"
    candidates = {
        "4014f248": [
            ("noop", None, 0, "原缺陷仍应失败"),
            ("gold", PRIVATE_ROOT / IDS["4014f248"] / "gold.patch", 1, "正确去重"),
            ("C1", actor_cands / "orange3_4014_C1_dedupe_in_create_var.patch", 1, "不同修改位置的合理解"),
            ("DG", cand4014, 0, "保留057已验非退化保护"),
            ("C3", actor_cands / "orange3_4014_C3_round_dedupe.patch", 0, "新增小量级保护纠正漏判"),
            ("C4", actor_cands / "orange3_4014_C4_unique_only_when_n_ge_len.patch", 0, "保留循环分支原保护"),
            ("pyx_build", proto / "orange3_4014_pyx_build/attempt/candidate" / (IDS["4014f248"] + ".diff"), 1, "历史含真实构建产物的冻结工件"),
            ("pyx_only", proto / "orange3_4014_pyx_only/attempt/candidate" / (IDS["4014f248"] + ".diff"), 0, "源码修改尚未生效"),
        ],
        "9b5494e2": [
            ("noop", None, 0, "原L1失败"),
            ("gold", PRIVATE_ROOT / IDS["9b5494e2"] / "gold.patch", 1, "正确solver修复"),
            *[(name, actor_cands / filename, score, purpose) for name, filename, score, purpose in (
                ("V1", "orange3_9b54_OR1_keep_lbfgs_switch_for_l1.patch", 1, "无auto哨兵的合理解"),
                ("V3", "orange3_9b54_OR2_auto_sentinel_saga_for_l1.patch", 1, "L1用saga的合理解"),
                ("V4", "orange3_9b54_V4_resolve_in_fit.patch", 1, "拟合时解析"),
                ("V5", "orange3_9b54_V5_mapping_table.patch", 1, "映射表选择"),
                ("W1", "orange3_9b54_W1_gold_silently_drop_l1.patch", 0, "不得静默改penalty"),
                ("V7", "orange3_9b54_V7_default_liblinear.patch", 0, "不得改变默认solver"),
                ("P1", "orange3_9b54_P1_resolve_in_init.patch", 0, "保留公开默认repr"),
                ("G1", "orange3_9b54_G1_gold_plus_multiclass_ovr.patch", 0, "新增默认multinomial关系拒绝OvR回归"),
            )],
        ],
        "50f6a758": [
            ("noop", None, 0, "原未用变量无警告"),
            ("gold", PRIVATE_ROOT / IDS["50f6a758"] / "gold.patch", 1, "原合理名单格式"),
            *[(name, OLD_RESULTS / IDS["50f6a758"] / "cands" / ("orange3_50f6_" + name + ".patch"), score, purpose)
              for name, score, purpose in (
                  ("K1", 1, "全列名单的合理解"), ("K2", 0, "加载数据后抑制警告"),
                  ("K3", 0, "混合文件抑制警告"), ("K4", 0, "遗漏numeric段"),
                  ("Cdeg", 0, "警告后提前返回，破坏已匹配定义应用"),
              )],
            ("K5", HERE.relative_to(ROOT) / "tasks/50f6a758/cands/K5_unnamed_warning.patch", 0, "警告不点名变量"),
        ],
    }
    counts = {"4014f248": 27, "9b5494e2": 13, "50f6a758": 48}
    for short, entries in candidates.items():
        out = HERE / "tasks" / short
        rows = [{"candidate": name, "patch": record(path) if path else None,
                 "expected_score": score, "purpose": purpose, "observed_score": None}
                for name, path, score, purpose in entries]
        write_json(out / "acceptance_plan.json", {
            "instance_id": IDS[short], "status": "prepared_not_run", "expected_key_count": counts[short],
            "fixed_material": record((out / "revision_draft.json").relative_to(ROOT)),
            "env_reset_timeout_seconds": 1200,
            "budget_note": "这是grader基线重建/控制面准备预算，不是模型求解时限；在最终consumer核实际生效值。",
            "shared_runner_ref": "rh2/experiments/r2e_lifecycle_20260929/replay_grade_budget.py / rh2/scripts/replay_grade.py",
            "machine_resource_entry": "由总协调正式入口提供；本文件不含SSH或凭据。",
            "candidates": rows,
            "acceptance_requires": ["固定新版材料与镜像/配方/consumer", "补丁成功应用和对应源码/产物确被加载",
                                    "精确键集与完整日志", "失败来自目标断言而非环境故障", "实际准备预算与清理证据",
                                    "非作者修订/证据复核", "受影响公开开发路径与实际题面交付"],
            "extra": (["新宿主actor实际重编并导出原冻结工件至新grader，与pyx_only成对；旧原型不替代最终入口。"]
                      if short == "4014f248" else
                      ["先在base/gold确认默认与显式multinomial的概率关系与容差；不能照抄gold常量或绕过环境绑定。"]
                      if short == "9b5494e2" else
                      ["fresh公开读者给出等效开发命令；保留公开冲突旧断言的失败，不要求actor修改测试。"]),
        })

    short = "50f6a758"
    task_id = IDS[short]
    package = HERE / "tasks" / short / "public_reader_package"
    package.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HERE / "tasks" / short / "files/problem_statement.txt", package / "user_prompt.txt")
    public = {key: pubs[task_id][key] for key in ("instance_id", "repo", "base_commit", "public_hints") if key in pubs[task_id]}
    public.update({"problem_statement": (package / "user_prompt.txt").read_text(),
                   "problem_statement_sha256": sha((package / "user_prompt.txt").read_bytes()),
                   "scope": "curated_public_snapshot_not_runtime_or_captured_model_delivery"})
    write_json(package / "public_task.json", public)
    selected = ("Orange/widgets/data/owcolor.py", "Orange/widgets/data/tests/test_owcolor.py",
                "Orange/widgets/tests/base.py", "doc/visual-programming/source/widgets/data/color.md",
                "README-dev.md", "tox.ini", "run_tests.sh")
    source_records = []
    for rel in selected:
        source = PUBLIC_ROOT / task_id / "worktree" / rel
        dest = package / "worktree" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / source, dest)
        source_records.append({"copied_path": "worktree/" + rel, **record(source)})
    (package / "environment_brief.md").write_text(
        "# 静态公开材料说明\n\n这是公开材料节选，不是完整工作树或可运行环境，不能据此宣称当前模型已收到题面。\n"
        "未包含虚拟环境、Qt运行环境、编译扩展或数据集；不含gold、隐藏测试、评分结果或私有修订理由。\n"
        "文档节选中的图片和无关跨widget链接未打包，不影响本次警告与载入契约的文字核对。\n"
        "public_hints仅为来源元数据，当前consumer、解释器和权限须在后续actor运行核实。\n"
        "历史公开环境记录Python3.7、agent身份、离线开发；Qt测试使用QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum前缀。\n"
        "本次请只静态读取，提出必要条件和最小公开验证命令；实际命令尚未执行。\n", encoding="utf-8")
    files = [{"path": str(p.relative_to(package)), "sha256": sha(p.read_bytes())}
             for p in sorted(package.rglob("*")) if p.is_file() and p.name != "manifest.json"]
    write_json(package / "manifest.json", {"instance_id": task_id, "scope": "public_only_curated_files",
                                           "files": files, "source_copies": source_records})


def main() -> None:
    registry_path = S2 / "revisions/material_revisions_v11.json"
    registry = json.loads(read(registry_path))
    registry_hash = sha(read(registry_path))
    # 若公共父版本变化，需要人工接续；不能靠重跑覆盖已有准备版本。
    assert registry_hash == "sha256:03acd34d7421bcf9c379612d0b8a5ce3d4292fdee0ee67327661eae5169d5c33"
    grades = {r["instance_id"]: r for r in map(json.loads, read(S2 / "ingest/grading_bundles_r2e_v0.jsonl").splitlines())}
    pubs = {r["instance_id"]: r for r in map(json.loads, read(S2 / "ingest/public_bundles_v0.jsonl").splitlines())}
    results = []

    for short, cls, test in (
        ("4014f248", "TestEqualFreq", "test_below_precision"),
        ("9b5494e2", "TestLogisticRegressionLearner", "test_auto_solver"),
        ("50f6a758", "TestOWColor", "test_load_ignore_warning"),
    ):
        task_id = IDS[short]
        out = HERE / "tasks" / short
        source_path = PRIVATE_ROOT / task_id / "hidden_tests/test_1.py"
        source = read(source_path)
        parent = source
        for entry in registry["revisions"]:
            if entry["instance_id"] == task_id and entry["target"] == "test_1.py":
                assert sha(source) == entry["sha256_before"]
                parent = read(Path(entry["revised_file"]))
                assert sha(parent) == entry["sha256_after"]
        expected = json.loads(grades[task_id]["expected_output_json"])
        source_file = next(r for r in grades[task_id]["hidden_test_files"] if r["path"] == "test_1.py")
        assert sha(parent) == source_file["sha256"]

        if short == "4014f248":
            replacement = method(parent, cls, test) + (out / "additional_assertion.txt").read_text()
        elif short == "9b5494e2":
            old_draft = json.loads(read(OLD_RESULTS / task_id / "revision_draft.json"))
            replacement = old_draft["optional_extra_s1"]["B_prime"]["revisions"][0]["edits"][0]["new"]
            replacement += (out / "additional_assertion.txt").read_text()
        else:
            replacement = (out / "revised_target_test.txt").read_text()

        new = replace_once(parent, method(parent, cls, test), replacement)
        ast.parse(new, feature_version=(3, 7))
        checked = unchanged_other_methods(parent, new, (cls, test))
        revised_path = out / "files/r2e_tests/test_1.py"
        revised_path.parent.mkdir(parents=True, exist_ok=True)
        revised_path.write_text(new, encoding="utf-8")
        (out / "expected_output.json").write_text(grades[task_id]["expected_output_json"], encoding="utf-8")
        assert sha(grades[task_id]["expected_output_json"]) == grades[task_id]["expected_output_json_sha256"]
        operation = {
            "kind": "hidden_test_text_replace", "target": "test_1.py",
            "edits": [{"old": method(source, cls, test), "new": replacement}],
            "sha256_before": sha(source), "sha256_after": sha(new),
            "revised_file": str(revised_path.relative_to(ROOT)), "expected_change": None,
        }
        assert replace_once(source, operation["edits"][0]["old"], replacement) == new
        draft = {
            "schema": "category2_orange3_preparation.v1", "as_of": "2026-10-03",
            "instance_id": task_id, "status": "draft_not_published_not_cpu_accepted",
            "parent_registry": record(registry_path),
            "parent_material_revisions": grades[task_id]["material_revisions"],
            "parent_test": {"source": record(source_path), "effective_sha256": sha(parent)},
            "operation_from_source": operation, "revision_id": None,
            "expected": {"sha256": sha(grades[task_id]["expected_output_json"]), "key_count": len(expected),
                         "non_passed": {k: v for k, v in expected.items() if v != "PASSED"}, "changed": False},
            "changed_method": cls + "." + test,
            "local_checks": {"python37_ast": True, "other_methods_ast_equal": checked,
                             "source_replacement_matches_full_file": True},
            "independent_revision_review": "pending", "formal_cpu_acceptance": "pending",
            "public_revision": "none" if short != "50f6a758" else "statement_draft.json",
        }
        if short == "4014f248":
            draft["publication_dependency"] = {
                "existing_target_revision": "r2e-mr-057",
                "constraint": "当前加载器拒绝同题同目标两条修订，不能直接追加。",
                "prepared_input": "从来源文件应用合并 edit，完整保留057已验第三段，再追加小量级回归。",
                "required_action": "公共维护者明确新版本的合并取代或已授权链式接续方案；不回写旧057。",
            }
        if short == "9b5494e2":
            draft["publication_dependency"] = {
                "keep_revision": "r2e-mr-020", "required_environment": "r2e_derive_v1+env_v2 / scipy==1.5.4",
                "approved_final_composite_digest": None,
                "required_action": "最终材料会改变配方摘要；由维护者核验并登记，不能绕过旧环境批准集合。",
                "multinomial_relation_on_base_gold": "pending_cpu",
            }
        write_json(out / "revision_draft.json", draft)
        results.append({"instance_id": task_id, "test_after_sha256": sha(new),
                        "expected_key_count": len(expected), "other_methods_ast_equal": checked})

    # 50f6 的题面只修已由真实 actor 证实的错误陈述，附公开旧断言冲突说明。
    task_id = IDS["50f6a758"]
    original = pubs[task_id]["problem_statement"]
    edits = [
        {"old": "**Title:** Error Occurs When Loading Variable Definitions with Unused Variables",
         "new": "**Title:** Missing Warning When Loading Variable Definitions with Unused Variables"},
        {"old": "When loading variable definitions that include unused variables, the application fails to handle the warnings properly. This results in a `TypeError` because the warning message is not correctly generated or handled.",
         "new": "When loading variable definitions that include variables absent from the current data, the application silently ignores those definitions without displaying the warning described below."},
        {"old": "A `TypeError` is raised with the message: `'NoneType' object is not subscriptable`, preventing the warning from being displayed and disrupting the loading process.",
         "new": "The definitions for the unused variables are silently ignored and no warning is displayed. The example does not raise an application exception.\n\n**Development Note:**\nThe existing public `TestOWColor.test_parse_var_defs_no_rename` ends with an assertion that a definition for an unused variable produces no warning. That assertion conflicts with the behavior requested here. Preserve its checks for duplicate renames, and validate the final unused-variable case against the warning behavior requested in this issue."},
    ]
    revised = original
    for edit in edits:
        revised = replace_once(revised, edit["old"], edit["new"])
    out = HERE / "tasks/50f6a758"
    statement_path = out / "files/problem_statement.txt"
    statement_path.write_text(revised, encoding="utf-8")
    write_json(out / "statement_draft.json", {
        "schema": "category2_orange3_statement_preparation.v1", "instance_id": task_id,
        "status": "draft_not_published_fresh_public_reader_pending", "template": "R-f",
        "operation": {"kind": "statement_text_replace", "target": "problem_statement", "edits": edits,
                      "sha256_before": sha(original), "sha256_after": sha(revised),
                      "revised_file": None, "expected_change": None},
        "statement_file": str(statement_path.relative_to(ROOT)),
        "public_basis": [str(PUBLIC_ROOT / task_id / "worktree/Orange/widgets/data/tests/test_owcolor.py") + ":885-888"],
        "base_actual_behavior_evidence": record(Path("runs/r2e_lifecycle_20260929/devcheck_rev/unrev") / task_id / "orig/captures/repro_unused_vars_warning.out"),
        "fresh_public_reader": "pending", "actual_actor_delivery": "pending_cpu",
        "note": "不改公开工作树的测试文件；公开等效开发命令由fresh读者提出并在actor身份核验。",
    })

    # 22e98 保留既有隔离候选，不重生成或复制整份材料。
    r22 = {
        "schema": "category2_orange3_existing_candidate.v1", "instance_id": IDS["22e98f8f"],
        "status": "independently_reviewed_isolated_candidate_not_shared_activation",
        "candidate": record(Path("runs/category2_repair_20260929/r2e/orange22_rf_v1/new_entries.json")),
        "public_reader": record(EXECUTION / "category2_repair_20260929/reviews/orange22_public_reading.md"),
        "independent_revision_review": record(EXECUTION / "category2_repair_20260929/reviews/orange22_isolated_revision_review.md"),
        "expected_statement_sha256": "sha256:f8701d3a4322270fde2618cc7cfc094460c9a5f1ec874e400c5bfaeef9ec7199",
        "shared_statement_sha256": sha(pubs[IDS["22e98f8f"]]["problem_statement"]),
        "shared_material_revisions": grades[IDS["22e98f8f"]]["material_revisions"],
        "next": ["唯一维护者接入版本与consumer", "实际模型消息匹配新题面摘要", "新宿主关键身份与实际准备预算"],
        "reuse": "既有noop/gold/DG评分矩阵，不因题面-only重复不变评分内容。",
    }
    assert r22["candidate"]["sha256"] == "sha256:750f5d151df1e004af95c448339afbd057e9423e87d38cd328355f31ab3bda7b"
    (HERE / "tasks/22e98f8f").mkdir(parents=True, exist_ok=True)
    write_json(HERE / "tasks/22e98f8f/existing_candidate.json", r22)
    write_json(HERE / "local_material_check.json", {
        "as_of": "2026-10-03", "scope": "本地文本/摘要/Python3.7语法/目标以外方法AST核对",
        "parent_registry": record(registry_path), "tasks": results,
        "docker": False, "ssh": False, "orange_runtime": False, "model_run": False,
        "formal_acceptance": False, "independent_review": False,
    })
    preparation_inputs(pubs)
    print(json.dumps({"generated": len(results), "reused_candidate": "22e98f8f", "scope": "local_material_only"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
