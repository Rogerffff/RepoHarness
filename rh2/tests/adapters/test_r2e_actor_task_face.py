"""R2E 正式 actor 任务面（E09 + D4=B，2026-09-25）：R2E 题只能用派生镜像，两侧容器按 image ID 启动，激活与解释器前缀
用 `/testbed/.venv`；覆盖表输入要路径与摘要成对；修订依赖的环境（orange3 r2e-mr-020 需要批准的 SciPy 1.5.4 配方）不配套即拒，
回放与正式 actor 共用同一处互检（Codex 批次三复核 F1）。"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from repoharness2.adapters.slime.prepared_task_face import (  # noqa: E402
    IMAGE_OVERLAYS_PATH_ENV,
    IMAGE_OVERLAYS_SHA256_ENV,
    R2E_INTERPRETER_PREFIX,
    R2E_VENV_ACTIVATION,
    PreparedTaskFace,
    load_overlays_input,
    overlay_binding_mismatch,
    rollout_spec_from_view,
)
from repoharness2.adapters.slime.r2e_grading_scripts import R2E_PRIVATE_HIDDEN_TESTS_DIR  # noqa: E402
from repoharness2.adapters.slime.replay_grade import _overlay_static_mismatch, prepare_for_replay  # noqa: E402
from repoharness2.contracts.constants import scan_for_forbidden_markers  # noqa: E402
from repoharness2.envpack.environment_overlay import (  # noqa: E402
    REVISION_ENV_REQUIREMENTS,
    EnvironmentOverlayFacts,
    EnvironmentOverlayV1,
    env_requirement_mismatch,
)
from repoharness2.envpack.prepared_tasks import PreparedTasksError  # noqa: E402
from repoharness2.envpack.training_view import RolloutTaskView, task_id_for  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
COV = "r2e_gym_subset::coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae"
ORANGE = "r2e_gym_subset::orange3__9b5494e26f407b75e79699c9d40be6df1d80a040"
IDS = {COV: "sha256:" + "a" * 64, ORANGE: "sha256:" + "b" * 64}
APPROVED_ORANGE_RECIPE = next(iter(REVISION_ENV_REQUIREMENTS["r2e-mr-020"].approved_recipe_sha256))


@pytest.fixture(scope="module")
def prepared(tmp_path_factory) -> dict:
    root = tmp_path_factory.mktemp("r2e_actor_face")
    summary = prepare_for_replay(repo_root=REPO_ROOT, out_dir=root / "prepared", private_dir=root / "private",
                                 task_ids=[COV, ORANGE], sources=("r2e_gym_subset",))
    return {"root": root, "summary": summary}


def _load(prepared: dict, overlays_path=None, overlays_sha=None) -> PreparedTaskFace:
    s = prepared["summary"]
    return PreparedTaskFace.load(
        prepared_dir=prepared["root"] / "prepared", manifest_sha256=s["prepared_manifest_sha256"],
        host_grading_path=prepared["root"] / "private" / "host_grading_views.jsonl",
        host_grading_sha256=s["host_grading_artifact_sha256"], time_budget_seconds=600,
        image_overlays_path=overlays_path, image_overlays_sha256=overlays_sha,
    )


def _views(prepared: dict):
    from repoharness2.envpack.prepared_tasks import load_host_grading_views, load_prepared_manifest, load_prepared_rollout_views

    s = prepared["summary"]
    manifest = load_prepared_manifest(prepared["root"] / "prepared", expected_sha256=s["prepared_manifest_sha256"])
    rviews = load_prepared_rollout_views(prepared["root"] / "prepared", manifest)
    gviews = load_host_grading_views(prepared["root"] / "private" / "host_grading_views.jsonl",
                                     expected_sha256=s["host_grading_artifact_sha256"], manifest=manifest)
    return manifest, rviews, gviews


def _overlay(task_id: str, rview, gview, *, recipe_id: str = "r2e_derive_v1", **changes) -> EnvironmentOverlayV1:
    public, grading = rview.public, gview.grading
    facts = dict(interpreter_relocated=True, testbed_owner="root", git_scrubbed=True,
                 hidden_tests_location=R2E_PRIVATE_HIDDEN_TESTS_DIR, hidden_tests_tree_sha256=grading.hidden_tests_tree_sha256)
    facts.update(changes.pop("facts", {}))
    fields = dict(task_id=task_id, base_image_ref=public.image, base_image_manifest_digest=public.image_manifest_digest,
                  derived_image_ref=f"rh2-r2e-derived/x:{task_id[-12:]}", derived_image_id=IDS[task_id], recipe_id=recipe_id,
                  recipe_sha256="sha256:" + "5" * 64, built_at_utc=datetime(2026, 9, 25, tzinfo=timezone.utc),
                  facts=EnvironmentOverlayFacts(**facts))
    fields.update(changes)
    return EnvironmentOverlayV1(**fields)


def _write_overlays(tmp_path: Path, overlays: list[EnvironmentOverlayV1]) -> tuple[Path, str]:
    path = tmp_path / "overlays.jsonl"
    path.write_text("".join(o.model_dump_json() + "\n" for o in overlays), encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def _good_overlays(prepared: dict) -> list[EnvironmentOverlayV1]:
    _, rviews, gviews = _views(prepared)
    return [_overlay(COV, rviews[COV], gviews[COV]),
            _overlay(ORANGE, rviews[ORANGE], gviews[ORANGE], recipe_id="r2e_derive_v1+env_v2", recipe_sha256=APPROVED_ORANGE_RECIPE)]


def test_r2e_task_face_without_overlays_is_refused(prepared, monkeypatch):
    monkeypatch.delenv(IMAGE_OVERLAYS_PATH_ENV, raising=False)
    monkeypatch.delenv(IMAGE_OVERLAYS_SHA256_ENV, raising=False)
    with pytest.raises(PreparedTasksError, match="必须用派生镜像"):
        _load(prepared)


def test_r2e_rollout_and_grading_use_the_derived_image_id_and_venv(prepared, tmp_path):
    path, sha = _write_overlays(tmp_path, _good_overlays(prepared))
    face = _load(prepared, path, sha)
    manifest, rviews, _ = _views(prepared)
    for tid in (COV, ORANGE):
        spec = face.rollout_spec(tid)
        assert spec.image == IDS[tid] and spec.image_local_build and spec.image_manifest_digest is None
        assert spec.env_activation_script == R2E_VENV_ACTIVATION and spec.expected_interpreter_prefix == R2E_INTERPRETER_PREFIX
        assert json.loads(spec.public_bundle_payload)["image"] == rviews[tid].public.image  # 模型可见面不变
        rec = manifest.record(tid)
        gspec = face.grading_spec(SimpleNamespace(task_id=tid, environment_package_digest=rec.environment_package_digest,
                                                  public_bundle_digest=rec.public_bundle_digest))
        assert gspec.image == IDS[tid] and gspec.image_local_build and gspec.image_local_build_id == IDS[tid]
        assert gspec.image_manifest_digest is None


def test_overlay_input_needs_path_and_digest_together(prepared, tmp_path, monkeypatch):
    path, sha = _write_overlays(tmp_path, _good_overlays(prepared))
    with pytest.raises(PreparedTasksError, match="成对"):
        load_overlays_input(path, None)
    with pytest.raises(PreparedTasksError, match="摘要不符"):
        load_overlays_input(path, "0" * 64)
    assert set(load_overlays_input(path, "sha256:" + sha)) == {COV, ORANGE}
    monkeypatch.setenv(IMAGE_OVERLAYS_PATH_ENV, str(path))
    monkeypatch.setenv(IMAGE_OVERLAYS_SHA256_ENV, sha)
    assert _load(prepared).rollout_spec(COV).image == IDS[COV]  # 调用方不传参时读环境变量（bringup 目前不显式传）


def test_orange3_revision_requires_env_v2_in_every_entry_point(prepared, tmp_path):
    """Codex 批次三复核 F1 的验收：当前材料 + 旧环境覆盖条目在候选开始前被拒（回放互检、正式 actor 构造、构建都拒）。"""

    _, rviews, gviews = _views(prepared)
    old = _overlay(ORANGE, rviews[ORANGE], gviews[ORANGE], recipe_id="r2e_derive_v1")
    new = _overlay(ORANGE, rviews[ORANGE], gviews[ORANGE], recipe_id="r2e_derive_v1+env_v2", recipe_sha256=APPROVED_ORANGE_RECIPE)
    # 步骤名对、依赖内容不对（例如 env_v2 装的是 hypothesis 或别的 SciPy 版本）：配方摘要不在批准集合里，同样拒绝（Codex 09-25 复核 R1）
    wrong_deps = _overlay(ORANGE, rviews[ORANGE], gviews[ORANGE], recipe_id="r2e_derive_v1+env_v2")
    assert "r2e-mr-020" in gviews[ORANGE].grading.material_revisions
    err = overlay_binding_mismatch(old, public=rviews[ORANGE].public, grading=gviews[ORANGE].grading)
    assert err is not None and err.startswith("overlay:env_recipe_required:r2e-mr-020:+env_v2")
    assert overlay_binding_mismatch(new, public=rviews[ORANGE].public, grading=gviews[ORANGE].grading) is None
    err2 = overlay_binding_mismatch(wrong_deps, public=rviews[ORANGE].public, grading=gviews[ORANGE].grading)
    assert err2 is not None and err2.startswith("overlay:env_recipe_not_approved:r2e-mr-020")
    assert _overlay_static_mismatch(old, public=rviews[ORANGE].public, gview=gviews[ORANGE], shadowed=False) == err
    path, sha = _write_overlays(tmp_path, [_overlay(COV, rviews[COV], gviews[COV]), old])
    with pytest.raises(PreparedTasksError, match="env_recipe_required"):
        _load(prepared, path, sha)
    # 构建入口用同一判据：缺 +env_v2 的配方身份不能给带 r2e-mr-020 的题产出覆盖条目；没有这类修订的题不受影响
    assert env_requirement_mismatch("r2e_derive_v1", ["r2e-mr-020"], recipe_sha256=APPROVED_ORANGE_RECIPE) is not None
    assert env_requirement_mismatch("r2e_derive_v1+env_v2", ["r2e-mr-020"], recipe_sha256=APPROVED_ORANGE_RECIPE) is None
    assert env_requirement_mismatch("r2e_derive_v1+env_v2", ["r2e-mr-020"], recipe_sha256="sha256:" + "5" * 64) is not None
    assert env_requirement_mismatch("r2e_derive_v1+env_v2", ["r2e-mr-020"], recipe_sha256=None) is not None
    assert env_requirement_mismatch("r2e_derive_v1+env_v1", [], recipe_sha256="sha256:" + "5" * 64) is None  # numpy 43e333e2：无此修订，行为不变


def test_other_overlay_mismatches_are_refused(prepared):
    _, rviews, gviews = _views(prepared)
    for changes, reason in (
        (dict(base_image_ref="other/image:1"), "overlay:base_image_mismatch"),
        (dict(facts={"hidden_tests_tree_sha256": "sha256:" + "0" * 64}), "overlay:hidden_tests_tree_mismatch"),
        (dict(facts={"git_scrubbed": False}), "overlay:recipe_facts_incomplete"),
    ):
        bad = _overlay(COV, rviews[COV], gviews[COV], **changes)
        assert overlay_binding_mismatch(bad, public=rviews[COV].public, grading=gviews[COV].grading) == reason


def test_non_r2e_sources_do_not_accept_overlays(prepared):
    _, rviews, gviews = _views(prepared)
    view = rviews[COV]
    swe_like = RolloutTaskView(task_id=task_id_for("swe_gym_lite", view.instance_id), source="swe_gym_lite",
                               instance_id=view.instance_id, environment_package_digest=view.environment_package_digest,
                               public_bundle_digest=view.public_bundle_digest, public=view.public)
    spec = rollout_spec_from_view(swe_like, time_budget_seconds=600)
    assert spec.image == view.public.image and not spec.image_local_build  # 默认路径不变
    with pytest.raises(PreparedTasksError, match="没有定义派生镜像覆盖"):
        rollout_spec_from_view(swe_like, time_budget_seconds=600, overlay=_overlay(COV, view, gviews[COV]))


def test_r2e_activation_script_is_clean_for_the_model_visible_container():
    assert scan_for_forbidden_markers(R2E_VENV_ACTIVATION) == []
    assert "/testbed/.venv/bin" in R2E_VENV_ACTIVATION and "PYTHONPATH" not in R2E_VENV_ACTIVATION

def test_overlay_input_parses_the_verified_bytes_without_rereading(prepared, tmp_path, monkeypatch):
    """Codex 09-25 复核 O1：核过摘要的那份字节就是被解析的内容，不再按路径重读（避免核对与解析之间文件被换）。"""

    import pathlib

    path, sha = _write_overlays(tmp_path, _good_overlays(prepared))
    orig_read_text = pathlib.Path.read_text

    def no_reread(self, *args, **kwargs):
        if pathlib.Path(self) == path:
            raise AssertionError("按路径重读了覆盖表")
        return orig_read_text(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "read_text", no_reread)
    assert set(load_overlays_input(path, sha)) == {COV, ORANGE}

