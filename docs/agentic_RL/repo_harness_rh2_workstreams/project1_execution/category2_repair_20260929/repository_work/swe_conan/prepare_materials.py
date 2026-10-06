"""生成 Conan 题级草案并做轻量静态检查，不运行项目、不发布 D6 材料。"""

from __future__ import annotations

import ast
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2").is_dir() and (p / "AGENTS.md").is_file())
EXEC = Path("docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution")
S2 = Path("docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest")
OWNER = "01a0fd61-bd33-7553-8a0e-cba65444cfb6"
TASKS = (11594, 12397, 13230, 13403, 14177, 15422)
FILES = {
    11594: "conans/test/unittests/tools/cmake/test_cmake_test.py",
    12397: "conans/test/integration/toolchains/meson/test_mesontoolchain.py",
    13230: "conans/test/unittests/client/toolchain/autotools/autotools_toolchain_test.py",
    13403: "conans/test/unittests/tools/gnu/autotools_test.py",
    14177: "conans/test/unittests/tools/files/test_patches.py",
    15422: "conans/test/integration/toolchains/cmake/test_cmaketoolchain.py",
}
ADDED = {
    11594: ["test_ninja_multiconfig_executes_requested_release"],
    12397: ["test_linux_native_clang_libcxx_link_args"],
    13230: ["test_linux_host_from_macos_has_no_apple_cflags[no_sdk]",
            "test_linux_host_from_macos_has_no_apple_cflags[sdk_sentinel]"],
    15422: ["test_presets_jobs_default_matches_public_helper",
            "test_presets_jobs_explicit_values[jobs2]", "test_presets_jobs_explicit_values[jobs7]",
            "test_presets_jobs_multiconfig_append_replace"],
}
FACTS = {
    11594: ("Ninja Multi-Config 必须真正执行请求的 Release 测试。",
            "已有 Ninja 离线恢复、actor、真实 CTest 和正式 0/1/1；新补丁追加真实 Release marker 断言。",
            ["新机按已验配方恢复 Ninja，保持 CMake 3.22.1", "受信新测试文件缺席登记", "两个 Ninja 节点 ALL 绑定正式消费", "新补丁正式 0/1/0", "非作者核查"]),
    12397: ("Apple cross 与 Linux native 的完整 cpp_link_args 键都必须包含对应 libc++ 选项。",
            "旧材料只有静态错键/Apple-only 线索；新补丁用完整键解析并添加 Linux native 配置生成。",
            ["actor 的生成配置路径", "gold、objcpp-only、Apple-only 的实际对照", "新增断言正式验收", "非作者核查"]),
    13230: ("Macos build / Linux host 的最终 CFLAGS 不应含 Apple flags。",
            "已有真实 actor、公开 CLI 两场景及正式 0/1/1；新增无 SDK 与 SDK 哨兵两节点，保留 Android 和34旧参考。",
            ["新增节点实际收集及正式 0/1/0", "关键 CLI 身份/导入复用核对", "非作者核查"]),
    13403: ("autoreconf 使用所选目录，执行一次、报错并恢复调用者目录。",
            "接续云端 v4，不改字节；41份历史诊断账本与日志重新核 SHA。此检查不等于 D6 正式登记或 GNU actor 验收。",
            ["共享入口只替换测试，不变 F2P/P2P", "新机 actor 及真实 GNU 开发路径", "正式矩阵按已知机制去重", "D6 版本的独立核查"]),
    14177: ("verbose 参数默认关闭，打开后能看见每个补丁的文件名，且真实应用补丁。",
            "接续云端 v2，不改字节；替代正对照 pubcand；单补丁描述旧行为移入 P2P，保留公开签名的位置参数和默认日志等级要求。",
            ["F2P→P2P 分组发布", "actor 开发条件", "替代正对照及错误候选正式验收", "非作者核查"]),
    15422: ("生成的 Ninja build preset 使用显式 jobs 或公开 helper 默认值，多配置追加/替换保持对应值。",
            "已有12个模型候选和正式actor后续证据；复用默认遗漏/多配置遗漏候选。新增同进程默认值、显式2/7、Release2→Debug7→Debug3断言。",
            ["新补丁正式评分", "已有模型候选回放", "Qwen3.6 a2 的 CMake 3.23.5 真实消费兼容诊断", "非作者核查"]),
}


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def source_root(number: int) -> Path:
    batch = "swegym_quality_batch01_20260921" if number in (14177, 15422) else "swegym_quality_expansion_20260925"
    return ROOT / "runs" / batch


def apply(base: str | None, file: str, patch: str) -> str:
    with tempfile.TemporaryDirectory(prefix="conan-material-check-") as name:
        work = Path(name)
        target = work / file
        target.parent.mkdir(parents=True)
        if base is not None:
            target.write_text(base)
        patch_file = work / "input.patch"
        patch_file.write_text(patch)
        for args in (("--check",), ()):
            subprocess.run(["git", "apply", *args, str(patch_file)], cwd=work,
                           check=True, capture_output=True, text=True)
        return target.read_text()


def diff(base: str | None, output: str, file: str) -> str:
    header = f"diff --git a/{file} b/{file}\n"
    if base is None:
        header += "new file mode 100644\n"
    return header + "".join(difflib.unified_diff(
        (base or "").splitlines(keepends=True), output.splitlines(keepends=True),
        fromfile=f"a/{file}" if base is not None else "/dev/null", tofile=f"b/{file}"))


def check_archive(number: int, version: int) -> dict:
    directory = ROOT / EXEC / "category3_diagnosis_20260929/tasks" / f"conan-io__conan-{number}" / "evidence"
    directory /= "rerun_0930/formal_revised_v4" if version == 4 else "formal_revised_v2"
    rows = []
    for ledger in sorted(directory.glob("ledger_*.jsonl")):
        for line in ledger.read_text().splitlines():
            row = json.loads(line)
            log = directory / "eval_logs" / Path(row["log"]["path"]).name
            assert sha(log.read_bytes()) == row["log"]["sha256"], ledger
            assert row["instance_id"] == f"conan-io__conan-{number}"
            assert row["cleanup"]["removed"] is True
            assert row["install"]["install_rc_last_command"] == 0
            assert row["install"]["candidate_segment_completed"] is True
            assert row["reference_missing_count"] == 0
            rows.append({"candidate": ledger.stem.removeprefix("ledger_"),
                         "ledger": rel(ledger), "ledger_sha256": sha(ledger.read_bytes()),
                         "log": rel(log), "log_sha256": row["log"]["sha256"],
                         "reward": row["report"]["reward"], "test_rc": row["install"]["test_rc"],
                         "f2p_pass": row["report"]["f2p_pass"], "p2p_fail": row["report"]["p2p_fail"]})
    assert len(rows) == (41 if version == 4 else 15)
    return {"status": "historical_files_checked_not_rerun", "records": rows}


def main() -> None:
    # 进入运行/审查后，派生材料不能静默覆盖题卡或清空结果。
    for number in TASKS:
        manifest = HERE / "tasks" / f"conan-io__conan-{number}" / "result_manifest.json"
        if manifest.exists():
            existing = json.loads(manifest.read_text())
            if (existing.get("project_tests_run") or existing.get("cpu_acceptance")
                    or existing.get("independent_review") or existing.get("probe_request")
                    or existing.get("probe_results")):
                raise RuntimeError(f"{manifest}: 已有运行或审查记录，请创建新材料版本，不覆盖当前证据")
    envs = {x["instance_id"]: x for x in map(json.loads, (ROOT / S2 / "environment_packages_v0.jsonl").read_text().splitlines())}
    original = {x["instance_id"]: x for x in map(json.loads, (ROOT / S2 / "grading_bundles_v2_v0.jsonl").read_text().splitlines())}
    results = []
    for number in TASKS:
        iid = f"conan-io__conan-{number}"
        source = source_root(number)
        public, private = source / "public" / iid, source / "private" / iid
        grading = json.loads((private / "grading.json").read_text())
        file = FILES[number]
        path = public / "base" / file
        base = path.read_text() if path.exists() else None
        assert grading["test_patch"] == original[iid]["test_patch"]
        assert grading["base_commit"] == envs[iid]["base_commit"]
        assert (private / "test.patch").read_text() == grading["test_patch"]
        task = HERE / "tasks" / iid
        task.mkdir(parents=True, exist_ok=True)
        if number in (13403, 14177):
            version = 4 if number == 13403 else 2
            cloud = ROOT / "rh2/experiments/category3_cloud_20260929" / f"conan{number}"
            patch = (cloud / f"revised_test_v{version}.patch").read_text()
            material = json.loads((cloud / f"materials_revised_v{version}.json").read_text())["tasks"][iid]
            assert sha(patch.encode()) == "sha256:" + material["revised_patch_sha256"]
            assert sha(grading["test_patch"].encode()) == "sha256:" + material["original_patch_sha256"]
            output = apply(base, file, patch)
            if number == 13403:
                reviewer_patch = (cloud / "review_v3/tests/v3_fix_plus.patch").read_text()
                assert apply(base, file, reviewer_patch) == output
            dump(task / "historical_integrity.json", check_archive(number, version))
            origin = rel(cloud / f"revised_test_v{version}.patch")
        else:
            output = apply(base, file, grading["test_patch"])
            output += (HERE / "snippets" / f"conan{number}.py").read_text()
            if number == 12397:
                old = ('    assert "cpp_args = [\'-isysroot\', \'/other/sdk/path\', \'-arch\', \'myarch\', \'-otherminversion=10.7\', \'-stdlib=libc++\']" in content\n'
                       '    assert "cpp_link_args = [\'-isysroot\', \'/other/sdk/path\', \'-arch\', \'myarch\', \'-otherminversion=10.7\', \'-stdlib=libc++\']" in content\n')
                new = '''    for key in ("cpp_args", "cpp_link_args"):
        args = _rh2_meson_args(content, key)
        assert "-stdlib=libc++" in args
        assert "-otherminversion=10.7" in args
        for pair in (["-isysroot", "/other/sdk/path"], ["-arch", "myarch"]):
            assert any(args[i:i + 2] == pair for i in range(len(args) - 1))
'''
                assert old in output
                output = output.replace(old, new, 1)
            patch = diff(base, output, file)
            assert apply(base, file, patch) == output
            origin = rel(HERE / "snippets" / f"conan{number}.py")
        tree = ast.parse(output, filename=file)
        functions = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        f2p, p2p = list(grading["fail_to_pass"]), list(grading["pass_to_pass"])
        f2p += [f"{file}::{name}" for name in ADDED.get(number, [])]
        move = []
        if number == 14177:
            node = f"{file}::test_single_patch_description"
            f2p.remove(node)
            p2p.append(node)
            move.append(node)
        assert set(f2p).isdisjoint(p2p)
        for node in f2p + p2p:
            assert node.split("::")[1].split("[")[0] in functions, node
        (task / "effective_test.patch").write_text(patch)
        (task / "effective_test.py").write_text(output)
        candidates = [{"id": "noop", "expected_reward": 0, "path": None}]
        candidates.append({"id": "gold", "expected_reward": 0 if number == 14177 else 1,
                           "path": rel(private / "gold.patch"), "sha256": sha((private / "gold.patch").read_bytes())})
        if number == 11594:
            p = ROOT / "runs/swegym_cpu_preprobe_20260929/task_inputs" / iid / "private/degenerate_drop_config.patch"
            bindings = ROOT / "runs/swegym_cpu_preprobe_20260929/task_inputs" / iid / "private/reference_bindings.json"
            (task / "reference_bindings.json").write_bytes(bindings.read_bytes())
            candidates.append({"id": "drop_config", "expected_reward": 0, "path": rel(p), "sha256": sha(p.read_bytes())})
        elif number == 13230:
            p = ROOT / "runs/swegym_cpu_preprobe_20260929/task_inputs_reserve6_v1" / iid / "private/android_only.patch"
            candidates.append({"id": "android_only", "expected_reward": 0, "path": rel(p), "sha256": sha(p.read_bytes())})
        elif number == 12397:
            candidate_file = "conan/tools/meson/toolchain.py"
            candidate_base = (public / "base" / candidate_file).read_text()
            gold_source = apply(candidate_base, candidate_file, (private / "gold.patch").read_text())
            for name, before, after in (
                ("objcpp_only", "self.cpp_link_args.append(self.libcxx)", "self.objcpp_link_args.append(self.libcxx)"),
                ("apple_only", "            self.cpp_link_args.append(self.libcxx)",
                 "            if self._is_apple_system:\n                self.cpp_link_args.append(self.libcxx)"),
            ):
                assert gold_source.count(before) == 1
                candidate_source = gold_source.replace(before, after, 1)
                ast.parse(candidate_source)
                candidate_patch = diff(candidate_base, candidate_source, candidate_file)
                assert apply(candidate_base, candidate_file, candidate_patch) == candidate_source
                cp = task / f"{name}.patch"
                cp.write_text(candidate_patch)
                candidates.append({"id": name, "expected_reward": 0, "path": rel(cp), "sha256": sha(cp.read_bytes()),
                                   "status": "new_static_control_not_run"})
        elif number in (13403, 14177):
            names = ({"runcwd": 1, "oschdir": 1, "r3_deferred_raise": 1, "rv_retcode": 1,
                      "noenter": 0, "relonly": 0, "buildlit": 0, "norestore": 0,
                      "mutate_source": 0, "fallback": 0, "swallow_run": 0, "w_ignore_errors": 0,
                      "nofinally": 0, "w_argsdrop": 0,
                      "w_twice": 0, "w3_fallback_code": 0, "w3_abs_swallow": 0,
                      "w3_fail_restore_build": 0, "w3_code_norestore": 0}
                     if number == 13403 else
                     {"pubcand": 1, "probe_post": 1, "probe_abspath": 1, "probe_merged": 1,
                      "probe_header": 1, "always_log": 0, "never_log": 0, "gold_log_only": 0,
                      "print_only": 0, "output_verbose": 0, "probe_basename": 0,
                      "probe_kwonly": 0, "probe_logonly_v": 0})
            for name, expected in names.items():
                cp = cloud / f"{name}.patch"
                candidates.append({"id": name, "expected_reward": expected, "path": rel(cp), "sha256": sha(cp.read_bytes()),
                                   "status": "historical_control_reused_formal_revision_pending"})
        elif number == 15422:
            matrix = ROOT / "runs/base_probe_20260922/remote/runs/matrix/attempts" / iid
            for name, model, attempt, expected in (
                ("coder_a1", "qwen3-coder-30b-a3b-instruct", "a1", 0),
                ("coder_a3", "qwen3-coder-30b-a3b-instruct", "a3", 0),
                ("deepseek_a1", "deepseek-v4-pro", "a1", 0),
                ("deepseek_a4_generator_boundary", "deepseek-v4-pro", "a4", 1),
                ("coder_a2_alternative", "qwen3-coder-30b-a3b-instruct", "a2", 1),
                ("qwen36_a2_schema_diagnostic", "qwen3.6-35b-a3b", "a2", None),
            ):
                matches = list((matrix / model / attempt).rglob("candidate.patch"))
                assert len(matches) == 1, (name, matches)
                cp = matches[0]
                candidates.append({"id": name, "expected_reward": expected, "path": rel(cp), "sha256": sha(cp.read_bytes()),
                                   "status": "historical_model_candidate_new_reward_not_run"})
        title, fact, pending = FACTS[number]
        revision = {
            "format": "conan_owner_preparation_v1_not_production_registry",
            "instance_id": iid, "owner_thread_id": OWNER, "as_of": "2026-10-03",
            "status": "draft_static_checked_cpu_acceptance_pending", "formal_registry_version": None,
            "base_commit": envs[iid]["base_commit"], "parent_grading_digest": envs[iid]["grading_bundle_digest"],
            "public_bundle_digest": envs[iid]["public_bundle_digest"],
            "original_image_manifest_digest": envs[iid]["image_manifest_digest"],
            "original_test_patch_sha256": sha(grading["test_patch"].encode()),
            "effective_test_patch_sha256": sha(patch.encode()), "effective_test_file_sha256": sha(output.encode()),
            "test_file": file, "base_test_file_exists": base is not None,
            "base_test_file_sha256": sha(base.encode()) if base is not None else None,
            "base_test_file_source": rel(path) if base is not None else None,
            "effective_patch_source": origin,
            "requested_operations": ["replace_test_patch"] + (["append_fail_to_pass"] if ADDED.get(number) else [])
                                    + (["move_fail_to_pass_to_pass_to_pass"] if move else [])
                                    + (["bind_truncated_reference_all_members", "restore_ninja_environment"] if number == 11594 else []),
            "original_fail_to_pass": grading["fail_to_pass"], "original_pass_to_pass": grading["pass_to_pass"],
            "effective_fail_to_pass": f2p, "effective_pass_to_pass": p2p,
            "moved_to_pass_to_pass": move, "candidate_matrix": candidates,
            "public_problem_statement_changed": False, "public_hints_changed": False,
            "solver_context": "原公开材料与已登记中性环境说明；本目录的测试、候选、结论不进入solver上下文",
            "pending": pending,
        }
        dump(task / "revision_plan.json", revision)
        dump(task / "result_manifest.json", {"instance_id": iid, "owner_thread_id": OWNER,
             "static_patch_apply": "passed", "static_python_parse": "passed",
             "project_tests_run": False, "cpu_acceptance": None, "independent_review": None,
             "probe_request": None, "probe_results": [], "training_eligibility": "not_established"})
        (task / "card.md").write_text(f"# Conan {number} 当前题卡\n\n2026-10-03。状态：材料草案静态检查完成，CPU验收未做。\n\n"
            f"**目标：** {title}\n\n**接续与处理：** {fact}\n\n"
            "材料与精确节点见 [revision_plan.json](revision_plan.json)，有效补丁见 [effective_test.patch](effective_test.patch)。"
            "该修订单是题主准备记录，不是共享入口已接受的正式登记。\n\n"
            "**待完成：**\n\n" + "\n".join(f"- {item}。" for item in pending) +
            "\n\n[结果清单](result_manifest.json)只登记静态检查；历史评分、当前预期和新实跑结果分开。"
            "当前不标记普通探针就绪或训练资格。\n")
        results.append({"instance_id": iid, "patch_sha256": sha(patch.encode()),
                        "f2p_count": len(f2p), "p2p_count": len(p2p),
                        "new_f2p_count": len(ADDED.get(number, [])), "static_patch_apply": True,
                        "static_python_parse": True, "project_tests_run": False})
    dump(HERE / "static_checks.json", {"as_of": "2026-10-03", "scope": "isolated git apply and Python AST, no imports or project runtime",
                                       "tasks": results})
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
