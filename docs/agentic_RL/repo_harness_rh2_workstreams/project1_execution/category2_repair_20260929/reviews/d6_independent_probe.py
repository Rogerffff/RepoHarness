"""D6 独立窄探针：只读正式材料，在内存制造同脚本／不同参考反例。"""

from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "rh2/src"))

from repoharness2.adapters.slime import prepared_task_face as current
from repoharness2.envpack.bundles_v2 import PrivateGradingBundleSWERevision, build_environment_package
from repoharness2.envpack.ingest_swegym_lite import IngestError
from repoharness2.envpack.swe_material_revisions import (
    load_trusted_swe_revision_outputs, verify_swe_revision_package_relations,
)
from repoharness2.envpack.training_view import HostGradingView
from repoharness2.grading.manager import (
    EnvQualification, env_qualification_status, grading_image_identity, grading_scripts_digest,
)


def main():
    trusted = load_trusted_swe_revision_outputs(ROOT)
    old_source = subprocess.check_output(
        ["git", "show", "HEAD:rh2/src/repoharness2/adapters/slime/prepared_task_face.py"], cwd=ROOT, text=True,
    )
    old = types.ModuleType("d6_review_old_face")
    exec(compile(old_source, "HEAD:prepared_task_face.py", "exec"), old.__dict__)
    # 直接执行旧 HEAD 渲染器；不仅比较新增测试作者写出的字符串期望。
    renderers = (
        "render_v2_eval_script", "render_v2_trusted_setup_script", "render_v2_candidate_test_script",
        "render_v2_candidate_install_script", "render_v2_candidate_test_after_install_script",
    )
    checked = 0
    for grading in trusted.source.result.grading_bundles:
        files = tuple(sorted(current.patch_touched_paths(grading.test_patch)))
        for name in renderers:
            args = (grading, files) if name in renderers[:3] else (grading,)
            assert getattr(old, name)(*args) == getattr(current, name)(*args), (grading.instance_id, name)
            checked += 1

    index = next(i for i, g in enumerate(trusted.result.grading_bundles) if g.instance_id == "python__mypy-10424")
    grading = trusted.result.grading_bundles[index]
    public = trusted.result.public_bundles[index]
    package = trusted.result.packages[index]
    validation = trusted.result.validation_bundles[index]
    data = grading.model_dump(mode="json")
    case = data["revision"]["added_mypy_cases"][0]
    # 模拟未来只改变精确参考 nodeid 的修订：case 选择和所有执行脚本完全不变。
    case["node_id"] = "mypy/test/testcheck.py::TypeCheckSuite::" + Path(case["path"]).name + "::" + case["case_name"]
    data["pass_to_pass"][len(data["revision"]["original_pass_to_pass"])] = case["node_id"]
    changed = PrivateGradingBundleSWERevision.model_validate(data)
    changed_package = build_environment_package(
        public=public, grading=changed, validation=validation,
        raw_archive_sha256=package.raw_archive_sha256,
        image_manifest_keyed_sha256=package.image_manifest_keyed_sha256,
    )

    def spec_for(g, p):
        view = HostGradingView(task_id=p.task_id, source=p.source, instance_id=p.instance_id,
                               environment_package_digest=p.digest(), grading_bundle_digest=g.digest(), grading=g)
        return current.build_grading_spec_from_host_view(
            view, image=public.image, image_manifest_digest=public.image_manifest_digest,
        )

    before, after = spec_for(grading, package), spec_for(changed, changed_package)
    assert grading_scripts_digest(before) == grading_scripts_digest(after)
    assert before.grading_materials_identity != after.grading_materials_identity
    assert package.digest() != changed_package.digest()
    q = EnvQualification(image_identity=grading_image_identity(before), scripts_digest=grading_scripts_digest(before),
                         reference_missing_count=0, source="independent_probe", qualified_at_utc="2026-09-29T00:00:00Z",
                         grading_materials_identity=before.grading_materials_identity)
    status = env_qualification_status(dataclasses.replace(after, env_qualification=q))
    assert status == (False, "grading_materials_identity_mismatch")
    try:
        verify_swe_revision_package_relations(changed_package, public, changed, validation, trusted=trusted)
    except IngestError as exc:
        rejection = str(exc)
    else:
        raise AssertionError("未登记的自洽变体被正式消费口接受")
    print(json.dumps({
        "old_head_script_comparisons": checked, "original_tasks": len(trusted.source.result.grading_bundles),
        "all_original_scripts_byte_equal": True,
        "reference_only_variant": {"scripts_digest_unchanged": True, "materials_identity_changed": True,
                                   "environment_package_digest_changed": True, "old_qualification": list(status),
                                   "formal_controller_rejection": rejection},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
