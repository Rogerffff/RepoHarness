"""诊断配方覆写：安装行或版本化参考绑定作为spec输入，调用原真实driver。"""

import argparse
import dataclasses
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-root", required=True)
    parser.add_argument("--recipe")
    parser.add_argument("--bindings")
    parser.add_argument("--materials")
    parser.add_argument("--grading-label-prefix", help="仅本批诊断的评分容器命名空间；隔离并行manager的启动清扫")
    parser.add_argument("--audit-dir", required=True)
    args, remaining = parser.parse_known_args()
    if remaining and remaining[0] == "--":
        remaining = remaining[1:]
    root = Path(args.code_root)
    recipe = json.loads(Path(args.recipe).read_text()) if args.recipe else None
    bindings = json.loads(Path(args.bindings).read_text()) if args.bindings else None
    materials = json.loads(Path(args.materials).read_text()) if args.materials else None
    assert recipe or bindings or materials
    audit = Path(args.audit_dir)
    audit.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(root / "src"))
    from repoharness2.adapters.slime import replay_grade as replay
    from repoharness2.envpack.spec_vendor import derive_install_cmd

    original = replay.build_grading_spec_from_host_view

    def build(view, **kwargs):
        if recipe:
            assert view.instance_id == recipe["instance_id"]
        grading = view.grading
        old = derive_install_cmd(grading.spec_vendor_id, grading.repo_key_lower, grading.version)
        spec = original(view=view, **kwargs)
        changes = {}
        if materials:
            from repoharness2.adapters.slime.prepared_task_face import (
                render_v2_candidate_test_script, render_v2_eval_script, render_v2_trusted_setup_script,
            )
            from repoharness2.grading.manager import patch_touched_paths
            entry = materials["tasks"][view.instance_id]
            assert hashlib.sha256(grading.test_patch.encode()).hexdigest() == entry["original_patch_sha256"]
            revised = type(grading).model_validate({**grading.model_dump(), "test_patch": entry["test_patch"]})
            files = tuple(sorted(patch_touched_paths(revised.test_patch)))
            # 材料修订不能悄悄扩大/缩小执行命令；只变更受保护的测试资产。
            assert render_v2_candidate_test_script(revised, files) == spec.candidate_test_script
            changes["trusted_setup_script"] = render_v2_trusted_setup_script(revised, files)
            changes["eval_script"] = render_v2_eval_script(revised, files)
            changes["hygiene"] = dataclasses.replace(spec.hygiene, test_files=files)
            changes["grader_version"] = spec.grader_version + "+" + materials.get("version", "materials-v1")
            (audit / "materials.json").write_text(json.dumps({
                **entry, "original_grading_digest": grading.digest(), "revised_grading_digest": revised.digest(),
                "scope": "versioned diagnostic GradingEnvSpec; source prepared package preserved; refreeze before production",
            }, ensure_ascii=False, indent=2) + "\n")
        if recipe:
            assert old == recipe["original_install"]
            if recipe.get("test_timeout_seconds"):
                changes["test_timeout_seconds"] = float(recipe["test_timeout_seconds"])
                (audit / "diagnostic_test_budget.json").write_text(json.dumps({
                    "before": spec.test_timeout_seconds, "after": changes["test_timeout_seconds"],
                    "scope": "this diagnostic spec only; CLI whole-grading deadline remains independent",
                }, indent=2) + "\n")
            if recipe.get("trusted_setup_append"):
                before = changes.get("trusted_setup_script", spec.trusted_setup_script)
                changes["trusted_setup_script"] = before + "\n" + recipe["trusted_setup_append"] + "\n"
                changes["grader_version"] = changes.get("grader_version", spec.grader_version) + "+env-setup-v1"
                (audit / "trusted_setup.after.sh").write_text(changes["trusted_setup_script"])
        for field in (("eval_script", "candidate_test_script") if recipe else ()):
            before = changes.get(field, getattr(spec, field))
            assert before.count(old) == 1
            after = before.replace(old, recipe["revised_install"], 1)
            (audit / (field + ".before.sh")).write_text(before)
            (audit / (field + ".after.sh")).write_text(after)
            changes[field] = after
        probe = (
            "python -I -c \"import importlib.util; "
            "s=importlib.util.find_spec('rh2_env_install_probe'); "
            "print('RH2_OBS_INSTALL_PROBE=' + ('absent' if s is None else s.origin))\"\n"
        )
        if recipe:
            changes["pre_candidate_observation_script"] = spec.pre_candidate_observation_script + probe
            changes["post_candidate_observation_script"] = spec.post_candidate_observation_script + probe
            if recipe.get("environment_prefix"):
                import shlex
                prefix = shlex.quote(recipe["environment_prefix"] + "/bin")
                for field in ("pre_candidate_observation_script", "post_candidate_observation_script"):
                    before = changes[field]
                    assert before.count("conda activate testbed") == 1
                    changes[field] = before.replace("conda activate testbed", "conda activate testbed\nexport PATH=" + prefix + ':"$PATH"', 1)
            if recipe.get("post_observation_append"):
                # 仅候选身份诊断输出；不得把服务日志当可信评分事实。
                changes["post_candidate_observation_script"] += "\n" + recipe["post_observation_append"] + "\n"
            (audit / "recipe.json").write_text(json.dumps({
                **recipe, "recipe_sha256": hashlib.sha256(Path(args.recipe).read_bytes()).hexdigest(),
                "scope": "diagnostic spec input; original driver, projection, manager and tests",
            }, indent=2, ensure_ascii=False) + "\n")
        if bindings:
            from reference_bindings import VERSION, parse_bound
            entry = bindings["tasks"][view.instance_id]

            def write_audit(value):
                (audit / (view.instance_id + ".reference.json")).write_text(
                    json.dumps(value, ensure_ascii=False, indent=2) + "\n")

            changes["parse_log"] = lambda text: parse_bound(grading, text, entry["bindings"], write_audit)
            changes["grader_version"] = changes.get("grader_version", spec.grader_version) + "+" + VERSION
            (audit / "reference_bindings.json").write_text(json.dumps(entry, ensure_ascii=False, indent=2) + "\n")
        return dataclasses.replace(spec, **changes)

    replay.build_grading_spec_from_host_view = build
    module_spec = importlib.util.spec_from_file_location("frozen_replay_cli", root / "scripts/replay_grade.py")
    cli = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(cli)
    if args.grading_label_prefix:
        config_type = cli.GradingManagerConfig

        def diagnostic_config(*values, **kwargs):
            before = config_type(*values, **kwargs)
            after = dataclasses.replace(before, label_prefix=args.grading_label_prefix)
            (audit / "diagnostic_grading_namespace.json").write_text(json.dumps({
                "before": before.label_prefix, "after": after.label_prefix,
                # 2026-09-20（B 线 Claude 适配）：A 线已删除跨 manager 年龄清扫与 `orphan_min_age_seconds` 配置字段；
                # 这里改为容忍缺席。独立命名空间此后只是隔离诊断批次的选择，不再是绕开生产缺陷的必要手段。
                "orphan_min_age_seconds": getattr(after, "orphan_min_age_seconds", None),
                "scope": "diagnostic runtime configuration only; cross-manager orphan sweep removed in production on 2026-09-20",
            }, ensure_ascii=False, indent=2) + "\n")
            return after

        cli.GradingManagerConfig = diagnostic_config
    return cli.main(remaining)


if __name__ == "__main__":
    raise SystemExit(main())
