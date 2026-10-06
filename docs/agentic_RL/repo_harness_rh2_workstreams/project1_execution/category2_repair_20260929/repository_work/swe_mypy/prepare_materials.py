"""生成 mypy 两题的初版离线准备材料；只读原件，不发布或执行项目测试。

补丁仅在临时单文件副本中应用。正式登记及 CPU 评分另由共用入口完成。
"""

from __future__ import annotations

import ast
import difflib
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/src/repoharness2").is_dir())
HISTORY = ROOT / "runs/swegym_quality_batch03_20260921_v1"
TASK2 = ROOT / "runs/task2_swegym_dev_20260925/runs"


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical_digest(data: dict) -> str:
    return digest(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())


def save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def save_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value)


def ref(path: Path) -> dict:
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "sha256": digest(data), "bytes": len(data)}


def patch_for(path: str, before: str, after: str) -> str:
    return f"diff --git a/{path} b/{path}\n" + "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile="a/" + path, tofile="b/" + path,
    ))


def apply_text_patch(patch: str, originals: dict[str, str]) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="rh2-mypy-material-") as d:
        workspace = Path(d)
        for name, text in originals.items():
            dest = workspace / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text)
        for args in (["git", "apply", "--check", "-"], ["git", "apply", "-"]):
            subprocess.run(args, input=patch, text=True, cwd=workspace,
                           check=True, capture_output=True)
        return {name: (workspace / name).read_text() for name in originals}


def case_body(text: str, name: str) -> str:
    marker = f"[case {name}]\n"
    assert text.count(marker) == 1, name
    body = text.split(marker, 1)[1]
    return body.split("[case ", 1)[0].rstrip() + "\n"


def main() -> None:
    # 初版生成器不能回退已有CPU证据与收敛后的题级提案。
    for iid in ("python__mypy-10174", "python__mypy-15184"):
        existing = HERE / iid / "revision_proposal.json"
        if existing.exists():
            value = json.loads(existing.read_text())
            if value.get("cpu_results") or value.get("state") != "draft_not_cpu_accepted_not_probe_ready":
                raise SystemExit("已有CPU验证或收敛后的提案；保留当前文件，不重生成初版。")
    output = []
    for iid in ("python__mypy-10174", "python__mypy-15184"):
        public_dir = HISTORY / "public" / iid
        private_dir = HISTORY / "private" / iid
        public = json.loads((public_dir / "public_bundle.json").read_text())
        grading = json.loads((private_dir / "grading.json").read_text())
        dest = HERE / iid
        changes = []
        checks = []
        base_test_path = "test-data/unit/check-expressions.test"
        base_test = (public_dir / "base" / base_test_path).read_text()

        if iid.endswith("10174"):
            name = "testStrictEqualityWithFixedLengthTupleInCheckWithoutStrictOptional"
            old_body = case_body(base_test, "testStrictEqualityWithFixedLengthTupleInCheck")
            body = old_body.replace("# flags: --strict-equality\n",
                                    "# flags: --strict-equality --no-strict-optional\n", 1)
            new_case = f"[case {name}]\n" + body + "\n"
            original_patch = grading["test_patch"]
            patched = apply_text_patch(original_patch, {base_test_path: base_test})[base_test_path]
            marker = "[case testUnimportedHintAny]\n"
            assert patched.count(marker) == 1
            revised = patched.replace(marker, new_case + marker, 1)
            effective = patch_for(base_test_path, base_test, revised)
            assert apply_text_patch(effective, {base_test_path: base_test})[base_test_path] == revised
            assert case_body(patched, "testOverlappingAnyTypeWithoutStrictOptional") == case_body(
                revised, "testOverlappingAnyTypeWithoutStrictOptional")
            save_text(dest / "private/effective_test.patch", effective)
            save_text(dest / "private/added_case.test", new_case)
            source_path = "mypy/checkexpr.py"
            source = (public_dir / "base" / source_path).read_text()
            anchor = "        if not self.chk.options.strict_equality:\n            return False\n"
            assert source.count(anchor) == 1
            bad = source.replace(anchor, anchor +
                "        if not self.chk.options.strict_optional:\n            return False\n", 1)
            candidate = patch_for(source_path, source, bad)
            assert apply_text_patch(candidate, {source_path: source})[source_path] == bad
            ast.parse(bad)
            save_text(dest / "private/disable_non_strict_comparisons.patch", candidate)
            # 0.820 的历史节点格式不含 .test 文件层；待真实 collect 确认。
            node = "mypy/test/testcheck.py::TypeCheckSuite::" + name
            changes.append({
                "kind": "replace_test_patch_append_p2p_proposal",
                "original_test_patch": ref(private_dir / "test.patch"),
                "effective_test_patch": ref(dest / "private/effective_test.patch"),
                "baseline_test": ref(public_dir / "base" / base_test_path),
                "baseline_file_exists": True,
                "added_case": name, "proposed_node_id": node,
                "node_id_verified_by_collection": False,
                "preserve_original_fail_to_pass": grading["fail_to_pass"],
                "preserve_original_pass_to_pass": grading["pass_to_pass"],
                "private_candidate": ref(dest / "private/disable_non_strict_comparisons.patch"),
                "rationale": "已有不重叠成员检查只增加 no-strict-optional 条件；不增加功能要求。",
            })
            checks.extend(["原/有效测试补丁能在精确基线单文件副本应用且目标 F2P 内容不变",
                           "错误候选仅改源码、能应用且通过 Python AST 解析"])
        else:
            statement_path = dest / "public/problem_statement_v1.txt"
            statement = statement_path.read_text()
            replacement = dict(public, problem_statement=statement,
                               problem_statement_sha256=digest(statement.encode()))
            save_json(dest / "public/public_bundle_draft.json", replacement)
            statement_diff = "".join(difflib.unified_diff(
                public["problem_statement"].splitlines(keepends=True),
                statement.splitlines(keepends=True),
                fromfile="original_problem_statement", tofile="problem_statement_v1",
            ))
            save_text(dest / "private/problem_statement.diff", statement_diff)
            names = ["testAssertType", "testAssertTypeGeneric",
                     "testAssertTypeUncheckedFunction", "testAssertTypeUncheckedFunctionWithUntypedCheck",
                     "testAssertTypeNoPromoteUnion"]
            cases = []
            for name in names:
                body = case_body(base_test, name)
                cases.append({"case_name": name, "path": base_test_path,
                              "base_sha256": digest(base_test.encode()),
                              "case_body_sha256": digest(body.encode()),
                              "node_id": "mypy/test/testcheck.py::TypeCheckSuite::check-expressions.test::" + name})
            source_path = "mypy/checkexpr.py"
            source = (public_dir / "base" / source_path).read_text()
            anchor = "        if not is_same_type(source_type, target_type):\n"
            assert source.count(anchor) == 1
            bad = source.replace(anchor, "        if True:  # 私有负对照：使有效 assert_type 也报错\n", 1)
            candidate = (private_dir / "gold.patch").read_text() + patch_for(source_path, source, bad)
            messages_path = "mypy/messages.py"
            originals = {source_path: source,
                         messages_path: (public_dir / "base" / messages_path).read_text()}
            applied = apply_text_patch(candidate, originals)
            ast.parse(applied[source_path])
            ast.parse(applied[messages_path])
            save_text(dest / "private/gold_but_always_reject_assert_type.patch", candidate)
            # 公开原件中的复现代码，不复制官方隐藏用例或答案实现。
            examples = {"a.py": "class C: ...\n", "b.py": "class C: ...\n",
                        "t.py": "import a, b\nfrom typing_extensions import assert_type\ndef g(x: a.C) -> None:\n    assert_type(x, b.C)\n"}
            for name, text in examples.items():
                ast.parse(text)
                save_text(dest / "public/reproduction" / name, text)
            changes.extend([
                {"kind": "replace_problem_statement_proposal",
                 "original_public_bundle": ref(public_dir / "public_bundle.json"),
                 "statement": ref(statement_path),
                 "statement_diff": ref(dest / "private/problem_statement.diff"),
                 "public_bundle_draft": ref(dest / "public/public_bundle_draft.json"),
                 "draft_public_digest": canonical_digest(replacement),
                 "scoring_change_from_this_operation": False,
                 "rationale": "用已在历史 actor/gold 原件中核实的公开同名类复现替换不触发缺陷的原例；任务目标不变。"},
                {"kind": "append_existing_mypy_p2p_proposal",
                 "preserve_original_fail_to_pass": grading["fail_to_pass"],
                 "preserve_original_pass_to_pass": grading["pass_to_pass"],
                 "added_mypy_cases": cases[:1],
                 "development_regression_cases": cases[1:],
                 "baseline_test": ref(public_dir / "base" / base_test_path),
                 "baseline_file_exists": True,
                 "private_candidate": ref(dest / "private/gold_but_always_reject_assert_type.patch"),
                 "node_id_verified_by_collection": False,
                 "selector_note": "-k testAssertType 为子串选择；正式 collect 须核出全部节点和额外 suite，不能只按登记行数填执行数。",
                 "rationale": "采纳非作者窄核：仅 testAssertType 进入正式 P2P，直接保护有效断言及返回类型；其余四项保持开发回归。"},
            ])
            checks.extend(["题面草案只改 problem_statement 及其 SHA，其他公开字段保持不变",
                           "一个正式拟登记 case 与四个开发 case 名唯一；错误候选叠加 gold 后能应用且源码通过 AST 解析",
                           "公开复现三文件通过 AST 解析；未在宿主运行 mypy"])

        historical_image = ROOT / "runs/env_recipe_repair_20260919/install_wave1/tasks" / iid / "image.json"
        image = json.loads(historical_image.read_text())
        actor_key = "mypy" + iid.rsplit("-", 1)[1]
        sources = [public_dir / "public_bundle.json", public_dir / "base_identity.json",
                   private_dir / "grading.json", private_dir / "test.patch", private_dir / "gold.patch",
                   historical_image, TASK2 / actor_key / "orig/activation_check.json",
                   TASK2 / actor_key / "orig/captures/tree.out",
                   TASK2 / actor_key / "orig/captures/env.out"]
        capture_names = (["mcve.out", "strict_eq.out"] if iid.endswith("10174") else
                         ["mcve.out", "mcve_ambiguous.out", "assert_type.out"])
        sources.extend(TASK2 / actor_key / "orig/captures" / name for name in capture_names)
        sources.append(TASK2 / "private" / (iid + "_gold.json"))
        sources.extend(ROOT / "runs/env_recipe_repair_20260919/install_wave1/tasks" / iid /
                       variant / "ledger.jsonl" for variant in ("noop", "gold"))
        record = {
            "record_kind": "task_material_preparation_not_runtime_registry",
            "as_of": "2026-10-03", "instance_id": iid,
            "owner_thread_id": "01a0fd63-1eba-7133-951d-7dd3475840a4",
            "state": "draft_not_cpu_accepted_not_probe_ready",
            "base_commit": public["base_commit"],
            "parent_public_digest": canonical_digest(public),
            "parent_grading_digest": canonical_digest(grading),
            "original_test_patch_sha256": digest(grading["test_patch"].encode()),
            "changes": changes,
            "environment_reuse": {"historical_image_record": ref(historical_image),
                                  "historical_image_id": image["image_id"],
                                  "immutable_base": image["base_digest"], "wheel_pins": image["pins"],
                                  "current_remote_image_available": None,
                                  "wheel_payload_directory_exists_locally": (ROOT / "runs/env_recipe_repair_20260919/install_wave1/assets").exists(),
                                  "note": "pins 不是全量依赖锁；新宿主须核实际 wheel SHA、每步安装、actor/grader 源码与解释器来源。"},
            "source_files": [ref(p) for p in sources],
            "local_checks": checks,
            "cpu_results": None, "independent_review": None,
            "production_registration": None, "probe_request": None,
        }
        asset_manifest = HERE / "install_assets_20261003.json"
        if asset_manifest.exists():
            assets = json.loads(asset_manifest.read_text())
            assert assets["task_pins"][iid] == image["pins"]
            for asset in assets["assets"]:
                payload = (ROOT / asset["path"]).read_bytes()
                assert digest(payload) == asset["sha256"] and len(payload) == asset["bytes"]
            record["environment_reuse"]["recovered_wheel_assets"] = ref(asset_manifest)
            record["environment_reuse"]["recovered_payload_verified"] = True
            record["environment_reuse"]["recovered_assets_installed"] = False
        save_json(dest / "revision_proposal.json", record)
        output.append({"instance_id": iid, "local_material_checks": "passed",
                       "proposal": str((dest / "revision_proposal.json").relative_to(ROOT))})
    save_json(HERE / "local_checks_20261003.json", {
        "as_of": "2026-10-03", "status": "passed", "scope": "静态字节、补丁应用与 AST；没有 CPU/正式评分或模型成绩",
        "tasks": output,
    })
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
