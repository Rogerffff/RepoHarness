"""派生镜像构建工具的材料步骤清单（2026-09-24 晚，material_v2）：`material_v2.sh` 按这份清单逐行执行，
替换类核修订前摘要，新增类（修订前写 `-`）要求目标原本不存在。清单格式错了，镜像里的隐藏测试就会与评分面不符。"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

from repoharness2.envpack.ingest_r2e_subset import (
    REVISION_KIND_HIDDEN_ADD,
    REVISION_KIND_HIDDEN_TEST,
    R2EMaterialRevision,
)

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_r2e_derived.py"


@pytest.fixture(scope="module")
def build():
    """脚本导入时改 sys.path；用完恢复，不影响后续测试的导入（同 test_reconcile_r2e 的做法）。"""
    saved = list(sys.path)
    spec = importlib.util.spec_from_file_location("build_r2e_derived_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.path[:] = saved


def _sha(tag: str) -> str:
    return "sha256:" + hashlib.sha256(tag.encode()).hexdigest()


def _rev(kind: str, target: str, before: str | None, after: str) -> R2EMaterialRevision:
    return R2EMaterialRevision(revision_id="r2e-mr-900", instance_id="x__y", kind=kind, target=target, edits=(),
                               sha256_before=before, sha256_after=after, revised_file="f", expected_change=None,
                               decision_ref="test")


def test_material_manifest_marks_added_files_with_a_dash_and_sorts_by_path(build):
    revs = [_rev(REVISION_KIND_HIDDEN_TEST, "test_2.py", _sha("old"), _sha("new")),
            _rev(REVISION_KIND_HIDDEN_ADD, "test.egg", None, _sha("egg"))]
    lines = build.material_manifest(revs).decode().splitlines()
    assert lines == [
        f"test.egg\t-\t{_sha('egg').removeprefix('sha256:')}",
        f"test_2.py\t{_sha('old').removeprefix('sha256:')}\t{_sha('new').removeprefix('sha256:')}",
    ]


def test_dockerfile_and_recipe_identity_use_the_v2_material_step(build):
    assert build.MATERIAL_STEP == "material_v2.sh" and build.MATERIAL_PATH.is_file()
    assert (build.MATERIAL_PATH.parent / "material_v1.sh").is_file()  # v1 保留：datalad 现有镜像按它构建
    dockerfile = build.render_dockerfile(material=True, env=False)
    assert "bash /rh2_build/material_v2.sh /rh2_build/material" in dockerfile and "material_v1" not in dockerfile
    assert "material_v2.sh" in build.render_dockerfile(material=True, env=True)
    manifest = build.material_manifest([_rev(REVISION_KIND_HIDDEN_ADD, "conftest.py", None, _sha("c"))])
    assert build.composite_recipe_digest(material_manifest_bytes=manifest, env_manifest_bytes=None) == \
        build.material_recipe_digest(manifest)
    assert build.MATERIAL_RECIPE_ID == "r2e_derive_v1+material_v2"
