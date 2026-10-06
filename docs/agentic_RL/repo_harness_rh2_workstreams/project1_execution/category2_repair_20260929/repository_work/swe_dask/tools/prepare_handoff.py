"""固定本包候选、原受信身份和 CPU 接续计划；不发布材料或执行评分。"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import tempfile
from pathlib import Path

from repoharness2.envpack.ingest_swegym_lite import load_trusted_ingest_outputs

from prepare_materials import CLOUD, HERE, ROOT, rel, save_json, sha, source


def candidate(task: int, name: str, patch: Path | None, expected: int | None,
              role: str, reason: str, *, priority: str = "first_formal_matrix") -> dict:
    _, _, _, grade = source(task)
    return {"name": name, "patch": None if patch is None else {"path": rel(patch), "sha256": sha(patch.read_bytes())},
            "role": role, "expected_reward": expected, "reason": reason, "priority": priority,
            "observed_reward_on_this_revision": None,
            "original_material_f2p_count": len(grade["fail_to_pass"])}


def rows(task: int) -> list[dict]:
    _, private, _, _ = source(task)
    out = HERE / "tasks" / f"dask__dask-{task}"
    base = [candidate(task, "noop", None, 0, "unrepaired", "未修复的原源码须被拒绝")]
    add = lambda name, patch, expected, role, reason, **kw: base.append(candidate(task, name, patch, expected, role, reason, **kw))
    if task == 7138:
        add("compatible_ravel", out / "compatible_ravel.patch", 1, "positive_draft", "保留旧 array=，同时支持 array-like；尚待运行和非作者核实")
        add("gold", private / "gold.patch", 0, "incomplete_gold", "转换主体有效，但改名后不兼容原 array= 调用；应在新增 P2P 被拒")
    elif task == 7656:
        previous = ROOT / "runs/swegym_cpu_preprobe_20260929/remote/results/dask__dask-7656/grading_setup900_v1"
        add("gold", private / "gold.patch", 1, "historical_positive", "历史实际参数类型、默认值及嵌套控制均过；新版本评分仍须运行")
        for name, folder, expected, reason in [
            ("wrong_result_type", "wrong_result_type", 0, "实际参数被重建成 SimpleNamespace，应在新增类型断言被拒"),
            ("opaque", "opaque", 0, "不遍历 dataclass，嵌套 Delayed 未求值，应被拒")]:
            matches = list((previous / folder).glob("artifacts/**/candidate.patch"))
            assert len(matches) == 1
            add(name, matches[0], expected, "known_wrong", reason)
    elif task == 9378:
        add("gold", private / "gold.patch", 1, "historical_positive", "已有 ma 入口的 mask 与 ones/zeros 值均须正确")
        for name, expected, role, reason in [
            ("toplevel_only", 1, "alternative_positive", "用户选 B，ma 入口缺失时接受顶层正确路线"),
            ("ma_mask_none", 0, "known_wrong", "ma 入口存在，但丢失逐元素 mask"),
            ("ma_mask_invert", 0, "known_wrong", "ma 入口存在，但翻转逐元素 mask")]:
            add(name, CLOUD / "dask9378" / (name + ".patch"), expected, role, reason)
        add("wrong_values_seven", out / "wrong_values_seven.patch", 0, "new_wrong_control", "mask 正确但 ones/zeros 值变为 7；本轮新构造，不冒充旧 invert_values7")
    elif task == 7305:
        add("gold_full_auto", out / "gold_full_auto.patch", 1, "positive_draft", "既有 gold_full 加整数 auto 修补；新组合尚待 CPU 和非作者核实")
        add("gold", private / "gold.patch", 0, "incomplete_gold", "唯一值不足、跨 2**63 和 auto 均有已证残缺")
        for name in ("gold_full", "exact_full", "higher_full"):
            add(name, CLOUD / "dask7305/candidates" / (name + ".patch"), 0, "historically_partial_positive", "显式分区的已核正对照，仍在已证 auto 路径丢行；保留原资格范围")
        controls = {
            "nearest_via_float": "先转 float64 再求分位数，题面原例端点仍偏移",
            "clip_partition": "只抑制分区症状，分位数端点仍错",
            "uint_only": "只覆盖 uint64，遗漏有符号大整数",
            "k1_only": "只覆盖题面字面分区数 1",
            "first_last": "假定输入有序，把首尾当端点",
            "gold_pin_only": "只钉端点，跨 2**63 的数组 dtype 仍有精度损失",
            "gold_typed_only": "只固定 dtype，唯一值不足的插值仍错",
        }
        for name, reason in controls.items():
            add(name, CLOUD / "dask7305/candidates" / (name + ".patch"), 0, "known_wrong", reason)
    elif task == 8801:
        add("gold", private / "gold.patch", 1, "historical_positive", "应覆盖错误内容、诊断、导入、空配置和权限；新正式版本待验证")
        add("reasonable_named_values", out / "reasonable_named_values.patch", 1, "acceptance_positive_draft", "正确原因不用旧同义词表；本地 API 过，完整环境及非作者接受性待核")
        add("wrong_missing_file_reason", out / "wrong_missing_file_reason.patch", 0, "new_wrong_control", "文件实际存在且 YAML 合法，非映射诊断却说文件不存在；用于核原因区别草案是否仍误奖")
        controls = {
            "rv_enum_types": "只枚举 list/str/int，遗漏 float 1.5",
            "wr_null_raises": "将合法显式 null/文档分隔符当错误",
            "wr_perm_fatal": "将不可读文件致命化，违背既有权限 P2P",
            "wr_wrong_reason": "将合法 YAML 的顶层非映射错误说成语法无效",
            "wrong_file": "报错点名错误文件",
            "wr_zip_misalign": "跳过空文件后 zip 错位，点名之前的正常文件",
            "wr_zip_misalign_orempty": "跳过不可读条目后 zip 错位",
            "wr_all_files": "列出全部文件但未指出具体坏文件",
            "wr_dir_named": "只点名目录而不点名坏文件",
            "oserr_fatal": "目录等不可读条目也致命化",
            "noreason": "只报路径，不解释内容问题",
            "parsererror_only": "仅处理 ParserError，漏其它 YAML 解析错误",
            "import_swallow": "完整 import dask 吞掉错误；本地 API 检查不能代表它被拒",
            "rv_import_warn": "完整 import dask 只警告；本地 API 检查不能代表它被拒",
            "wr_import_only": "只在导入时诊断，加载 API 仍静默吞错",
        }
        for name, reason in controls.items():
            add(name, CLOUD / "dask8801" / (name + ".patch"), 0, "known_wrong", reason)
        for name in ("chain_cause", "gr_attr_wrap", "ok_aggregate", "ok_object_value", "ok_map_settings", "ok_dictionary_typeerror", "ok_yamlerror_subclass", "gr_csafe_loader"):
            add(name, CLOUD / "dask8801" / (name + ".patch"), None if name == "gr_csafe_loader" else 1,
                "acceptance_comparison", "复用不同合理异常类、异常链、聚合或措辞；CSafeLoader 仍有已登记语法措辞边界，不在本轮静默裁定",
                priority="private_batch_then_formal_if_not_equivalent")
    return base


def check_candidate(task: int, row: dict) -> dict:
    if row["patch"] is None:
        return {"candidate": row["name"], "status": "not_applicable_noop"}
    public, _, _, _ = source(task)
    patch = (ROOT / row["patch"]["path"]).read_bytes()
    pairs = re.findall(rb"^diff --git a/(\S+) b/(\S+)$", patch, re.M)
    if not pairs:
        # 历史 runner 原件有纯 unified diff；保留字节与 SHA，不补写头部。
        pairs = re.findall(rb"^--- a/(\S+)\n\+\+\+ b/(\S+)$", patch, re.M)
    assert pairs and all(a == b for a, b in pairs), "这里只核已有文件的源码补丁"
    paths = [a.decode("utf-8") for a, _ in pairs]
    assert not any("tests/" in p or Path(p).is_absolute() or ".." in Path(p).parts for p in paths)
    bases = {name: sha((public / "base" / name).read_bytes()) for name in paths}
    with tempfile.TemporaryDirectory(prefix="rh2-dask-candidate-") as td:
        for name in paths:
            target = Path(td) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((public / "base" / name).read_bytes())
        subprocess.run(["git", "apply", "--check", "-"], input=patch, cwd=td, check=True, capture_output=True)
        subprocess.run(["git", "apply", "-"], input=patch, cwd=td, check=True, capture_output=True)
        applied = {}
        for name in paths:
            data = (Path(td) / name).read_bytes()
            ast.parse(data.decode("utf-8"), filename=name)
            applied[name] = sha(data)
    return {"candidate": row["name"], "candidate_sha256": sha(patch), "status": "apply_and_ast_pass",
            "exported_base_source_sha256": bases, "applied_source_sha256": applied, "runtime_execution": "not_performed"}


def main() -> None:
    trusted = load_trusted_ingest_outputs(ROOT)
    publics = {p.instance_id: p for p in trusted.result.public_bundles}
    gradings = {g.instance_id: g for g in trusted.result.grading_bundles}
    packages = {p.instance_id: p for p in trusted.result.packages}
    counts = {}
    for task in (7138, 7656, 9378, 7305, 8801):
        out = HERE / "tasks" / f"dask__dask-{task}"
        revision = json.loads((out / "revision.json").read_text())
        iid = revision["instance_id"]
        public, private, exported_public, exported_grade = source(task)
        assert publics[iid].model_dump(mode="json") == exported_public
        assert gradings[iid].model_dump(mode="json") == exported_grade
        results = json.loads((out / "results.json").read_text())
        assert results["cpu_formal_acceptance"] == "pending" and not results["new_reward_rows"], "不得覆盖已有 CPU 结果"
        revision["trusted_parent_identity"] = {
            "validation": "load_trusted_ingest_outputs_pass_and_exports_match",
            "public_bundle_digest": publics[iid].digest(), "grading_bundle_digest": gradings[iid].digest(),
            "environment_package_digest": packages[iid].digest(),
            "effective_revision_publication": "pending_not_same_as_parent_identity"}
        matrix_rows = rows(task)
        checks = [check_candidate(task, row) for row in matrix_rows]
        matrix = {"schema": "dask_acceptance_plan.v1", "as_of": "2026-10-03", "instance_id": iid,
                  "revision_id": revision["revision_id"], "effective_test_patch": revision["effective_test_patch"],
                  "expected_results_are_not_observed_scores": True, "rows": matrix_rows,
                  "success_conditions": ["固定材料身份、镜像、执行入口、安装配方与身份", "有效正对照为 1；未修复及各已知错解为 0",
                    "安装和测试实际执行、参考无缺席；逐项参考状态和失败断言符合预期", "保存完整评分账本、输出、候选和清理结果", "非作者核公开依据、正对照及本轮实际结果"],
                  "known_wrong_coverage": "初始矩阵按独立机制选取；其余历史候选保留原件。接受性比较不能因私有检查通过而省略正式身份/导入等差异。"}
        save_json(out / "acceptance_matrix.json", matrix)
        save_json(out / "offline_candidate_checks.json", {"scope": "patch_context_and_ast_only", "rows": checks})
        plan = {"schema": "dask_cpu_handoff_preparation.v1", "instance_id": iid, "revision_id": revision["revision_id"],
                "state": "awaiting_cpu_acceptance_and_trusted_publication", "host": None, "resource_lease": None,
                "parent_image": revision["image"], "parent_image_manifest_digest": revision["image_manifest_digest"],
                "formal_revision_identity": None, "formal_recipe": "maintainer_to_bind_from_validated_recipe",
                "trusted_setup_timeout_s": 900 if task == 7656 else None,
                "grader_identity": "non_root_required" if task == 8801 else "use_trusted_grader_identity",
                "public_actor_followup": ("引用已验证 actor 配方；换宿主核身份/源码/关键导入；补本轮 prompt 的真实交付"
                                           if task == 7656 else "尚缺完整 actor 证明；在干净公开源码中核身份、base、依赖、导入及公开目标命令"),
                "private_inputs": [rel(out / "revision.json"), rel(out / "acceptance_matrix.json")],
                "solver_boundary": "solver 只接收正式公开题面、干净源码与中性环境说明；本包测试、候选、验收预期及作者分析不进入求解上下文",
                "independent_review": "pending", "model_probe_request": "not_submitted"}
        if task == 7656:
            prefix = ROOT / "runs/swegym_cpu_preprobe_20260929/task_inputs/dask__dask-7656"
            plan["historical_recipe_inputs"] = [{"path": rel(prefix / name), "sha256": sha((prefix / name).read_bytes())}
                    for name in ("actor_build_plan.json", "grader_build_plan.json", "grader_install_recipe.json", "public_commands.json")]
            assert sha((private / "gold.patch").read_bytes()) == "2f6f59d094834f3e8db2d1e5332f1415ff65d151678d5cc6c6590f1883de63e9"
        elif task == 7138:
            plan["historical_environment_condition"] = "仅此题历史 pair 为 Python3.8.15/pytest7.4.4；须绑定等价配方，不外推其它四题"
        elif task == 8801:
            plan["statement_revision"] = rel(out / "statement_revision.json")
            plan["fresh_public_reader"] = "pending_required_before_probe"
        save_json(out / "cpu_acceptance_plan.json", plan)
        save_json(out / "revision.json", revision)
        results["current_checks"]["trusted_original_parent_and_exports"] = "pass"
        results["current_checks"]["candidate_patch_context_and_ast"] = "pass"
        results["offline_candidate_checks"] = rel(out / "offline_candidate_checks.json")
        if task == 8801:
            report = json.loads((out / "local_config_checks.json").read_text())
            assert report["effective_test_file_sha256"] == revision["effective_test_file"]["effective_sha256"]
            results["isolated_config_api_check"] = {"path": rel(out / "local_config_checks.json"), "candidate_count": len(report["rows"]),
                  "scope": report["scope"], "not_formal_acceptance": True}
        save_json(out / "results.json", results)
        counts[iid] = len(matrix_rows)
    print(json.dumps({"trusted_parent_identity": "5 passed", "offline_candidates": counts, "cpu_acceptance": "not_performed", "publication": "pending"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
