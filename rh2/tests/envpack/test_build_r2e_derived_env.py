"""派生镜像构建工具的环境步骤版本（2026-09-24 夜，env_v2）：配方条目的 `env_step` 选步骤脚本。
`env_v1.sh` 的 Dockerfile 与配方身份必须与 numpy `43e333e2` 现有镜像的构建记录逐字节一致；`env_v2.sh` 读包版本
不依赖 `importlib.metadata`（Python 3.7 没有），脚本里嵌的读法与构建后复核用的 `DIST_VERSIONS_PY` 逐字相同。"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_r2e_derived.py"

# numpy 43e333e2 的环境配方条目（env_pins_v1 / v2 里逐字相同）与它的派生镜像构建记录（2026-09-24，+env_v1）
NUMPY_ENTRY = {
    "pins": [{
        "dist": "hypothesis", "version": "6.24.1", "wheel": "hypothesis-6.24.1-py3-none-any.whl",
        "sha256": "ecbf7197ef85f0024b8c3dc947cfbf8296a5d1e6138562fc2f04d71ac9a96333",
        "url": "https://files.pythonhosted.org/packages/23/df/b10b922532146902e7fb1c3163d90472fd61f79688d5fb02f760504b5567/"
               "hypothesis-6.24.1-py3-none-any.whl",
    }],
    "venv_changed_globs": ["lib/python3.10/site-packages/hypothesis/*"],
}
NUMPY_RECIPE_SHA256 = "sha256:0cda30240295d5d13279972a95d4d349e20c42d21a7719c2ca4a4873c60599b1"
NUMPY_DOCKERFILE_SHA256 = "33b77ae518ffffe81bb346ff0a37ffc572e9b2d17ece62fc444a43ca88d17b06"


REPO_ENV_PINS_V2 = SCRIPT.parents[2] / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/recipes/env_pins_v2.json"


@pytest.fixture(scope="module")
def build():
    """脚本导入时改 sys.path；用完恢复，不影响后续测试的导入（同 test_build_r2e_derived_material）。"""
    saved = list(sys.path)
    spec = importlib.util.spec_from_file_location("build_r2e_derived_env_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.path[:] = saved


def test_env_v1_dockerfile_and_identity_match_the_existing_numpy_image(build):
    dockerfile = build.render_dockerfile(material=False, env=True)
    assert hashlib.sha256(dockerfile.encode("utf-8")).hexdigest() == NUMPY_DOCKERFILE_SHA256
    assert build.render_dockerfile(material=False, env=True, env_step="env_v1.sh") == dockerfile
    digest = build.composite_recipe_digest(material_manifest_bytes=None, env_manifest_bytes=build.env_manifest(NUMPY_ENTRY))
    assert digest == NUMPY_RECIPE_SHA256
    assert build.ENV_STEPS["env_v1.sh"] == ("+env_v1", "e")


def test_env_v2_uses_its_own_script_in_dockerfile_and_identity(build):
    dockerfile = build.render_dockerfile(material=False, env=True, env_step="env_v2.sh")
    assert "bash /rh2_build/env_v2.sh /rh2_build/env" in dockerfile and "env_v1" not in dockerfile
    assert "material_v2.sh" in build.render_dockerfile(material=True, env=True, env_step="env_v2.sh")
    env_bytes = build.env_manifest(NUMPY_ENTRY)
    v1 = build.composite_recipe_digest(material_manifest_bytes=None, env_manifest_bytes=env_bytes)
    v2 = build.composite_recipe_digest(material_manifest_bytes=None, env_manifest_bytes=env_bytes, env_step="env_v2.sh")
    assert v1 != v2
    assert build.ENV_STEPS["env_v2.sh"] == ("+env_v2", "e2")
    with pytest.raises(ValueError, match="未知环境步骤"):
        build.render_dockerfile(material=False, env=True, env_step="env_v9.sh")
    with pytest.raises(ValueError, match="未知环境步骤"):
        build.composite_recipe_digest(material_manifest_bytes=None, env_manifest_bytes=env_bytes, env_step="env_v9.sh")


def test_load_env_pins_accepts_known_steps_and_rejects_unknown(build, tmp_path):
    def write(entry: dict) -> Path:
        path = tmp_path / "pins.json"
        path.write_text(json.dumps({"schema_id": build.ENV_PINS_SCHEMA_ID, "tasks": {"x__y": entry}}), encoding="utf-8")
        return path

    assert build.load_env_pins(write(NUMPY_ENTRY))["x__y"].get("env_step") is None
    assert build.load_env_pins(write({**NUMPY_ENTRY, "env_step": "env_v2.sh"}))["x__y"]["env_step"] == "env_v2.sh"
    with pytest.raises(ValueError, match="未知环境步骤"):
        build.load_env_pins(write({**NUMPY_ENTRY, "env_step": "env_v3.sh"}))


def test_env_v2_script_embeds_exactly_the_probe_used_after_build(build):
    text = (build.ENV_STEP_DIR / "env_v2.sh").read_text(encoding="utf-8")
    start = text.index("CODE=$(cat <<'PYEOF'\n") + len("CODE=$(cat <<'PYEOF'\n")
    embedded = text[start:text.index("\nPYEOF\n)", start)]
    assert embedded == build.DIST_VERSIONS_PY.rstrip("\n")
    assert "importlib" not in build.DIST_VERSIONS_PY


def _dist_info(site: Path, dirname: str, name: str, version: str) -> None:
    d = site / dirname
    d.mkdir(parents=True)
    (d / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n\nName: not-a-header\n", encoding="utf-8")


def test_dist_versions_probe_reads_metadata_along_sys_path(build, tmp_path):
    site_a, site_b, cwd = tmp_path / "a", tmp_path / "b", tmp_path / "cwd"
    cwd.mkdir()
    _dist_info(site_a, "scipy-1.5.4.dist-info", "scipy", "1.5.4")
    _dist_info(site_a, "Foo_Bar-2.0.dist-info", "Foo_Bar", "2.0")
    _dist_info(site_b, "scipy-1.7.3.dist-info", "scipy", "1.7.3")
    (site_b / "legacy.egg-info").write_text("Metadata-Version: 1.0\nName: legacy\nVersion: 0.9\n", encoding="utf-8")

    def run(paths: list[Path], *dists: str) -> dict[str, str]:
        # -I -S：不读环境变量、不加 site-packages，sys.path 只有标准库与这里给的目录（不受开发 venv 里装了什么影响）
        prelude = "import sys; sys.path[:0] = " + repr([str(p) for p in paths]) + "\n"
        proc = subprocess.run([sys.executable, "-I", "-S", "-c", prelude + build.DIST_VERSIONS_PY, *dists],
                              capture_output=True, text=True, cwd=cwd, check=True)
        return dict(line.split("=", 1) for line in proc.stdout.splitlines())

    assert run([site_a], "scipy", "foo-bar", "nothing-here") == {"scipy": "1.5.4", "foo-bar": "2.0", "nothing-here": "absent"}
    # 同名两份：按 sys.path 顺序都列出，调用方据此判为与配方不符
    assert run([site_a, site_b], "scipy", "legacy") == {"scipy": "1.5.4,1.7.3", "legacy": "0.9"}
    # 同一目录在 sys.path 上出现两次不算两份
    assert run([site_a, site_a], "scipy")["scipy"] == "1.5.4"


def test_material_that_needs_an_env_step_is_not_built_without_it(build, tmp_path):
    """Codex 批次三复核 F1：orange3 9b5494e2 带 r2e-mr-020（只在 +env_v2 下成立），不给环境配方的构建在动 Docker 之前
    就失败，不写 facts.json，也就不会进 overlays.jsonl。"""

    from repoharness2.envpack.ingest_r2e_subset import load_trusted_r2e_ingest_outputs

    repo_root = SCRIPT.parents[2]
    trusted = load_trusted_r2e_ingest_outputs(repo_root)
    iid = "orange3__9b5494e26f407b75e79699c9d40be6df1d80a040"
    public = next(p for p in trusted.result.public_bundles if p.instance_id == iid)
    grading = next(g for g in trusted.result.grading_bundles if g.instance_id == iid)

    class NoDocker:
        def __getattr__(self, name):
            raise AssertionError(f"不应调用 Docker（{name}）")

    res = build.build_one(NoDocker(), out=tmp_path, public=public, grading=grading, tag_prefix="t", skip_pull=True,
                          timeouts={"pull": 1, "build": 1, "check": 1}, repo_root=repo_root,
                          revisions=trusted.revisions.get(iid, ()), env_entry=None)
    assert not res["ok"] and res["failures"] and res["failures"][0].startswith("env_recipe_required:r2e-mr-020:+env_v2")
    assert not (tmp_path / iid / "facts.json").exists()


def _orange_case():
    from repoharness2.envpack.ingest_r2e_subset import load_trusted_r2e_ingest_outputs

    repo_root = SCRIPT.parents[2]
    trusted = load_trusted_r2e_ingest_outputs(repo_root)
    iid = "orange3__9b5494e26f407b75e79699c9d40be6df1d80a040"
    public = next(p for p in trusted.result.public_bundles if p.instance_id == iid)
    grading = next(g for g in trusted.result.grading_bundles if g.instance_id == iid)
    return repo_root, trusted, iid, public, grading


class _StopAtDocker(Exception):
    pass


class _DockerBoundary:
    """第一次碰 Docker 就停下：用来证明输入已经通过了构建前的材料 / 环境检查，但不真的构建。"""

    def __getattr__(self, name):
        raise _StopAtDocker(name)


def _pin(dist: str, version: str, sha: str) -> dict:
    return {"dist": dist, "version": version, "wheel": f"{dist}-{version}-py3-none-any.whl", "sha256": sha,
            "url": f"https://example.invalid/{dist}-{version}-py3-none-any.whl"}


def test_orange3_revision_is_bound_to_the_approved_scipy_recipe_not_the_step_name(build, tmp_path):
    """Codex 09-25 复核 R1：r2e-mr-020 只在批准的 SciPy 1.5.4 配方下成立。步骤名 env_v2 相同、装的依赖不同的配方
    （hypothesis wheel、别的 SciPy 版本）必须在动 Docker 之前被拒；批准的配方通过检查、走到 Docker 边界。"""

    from repoharness2.envpack.environment_overlay import REVISION_ENV_REQUIREMENTS

    repo_root, trusted, iid, public, grading = _orange_case()
    approved = build.load_env_pins(REPO_ENV_PINS_V2)[iid]
    wrong = {
        "hypothesis_wheel": {**approved, "pins": [_pin("hypothesis", "6.24.1", "e" * 64)]},
        "other_scipy": {**approved, "pins": [_pin("scipy", "1.7.3", "f" * 64)]},
    }
    kw = dict(out=tmp_path, public=public, grading=grading, tag_prefix="t", skip_pull=True,
              timeouts={"pull": 1, "build": 1, "check": 1}, repo_root=repo_root, revisions=trusted.revisions.get(iid, ()))
    for name, entry in wrong.items():
        res = build.build_one(_DockerBoundary(), env_entry=entry, **kw)
        assert not res["ok"] and res["failures"][0].startswith("env_recipe_not_approved:r2e-mr-020"), (name, res["failures"])
        assert not (tmp_path / iid / "facts.json").exists()
    with pytest.raises(_StopAtDocker):
        build.build_one(_DockerBoundary(), env_entry=approved, **kw)
    # 登记的批准摘要就是按当前脚本从批准条目算出的配方身份；脚本或依赖变了，这里会失败，提醒先复验再更新登记
    digest = build.composite_recipe_digest(material_manifest_bytes=None, env_manifest_bytes=build.env_manifest(approved),
                                           env_step=approved.get("env_step", build.DEFAULT_ENV_STEP))
    assert digest in REVISION_ENV_REQUIREMENTS["r2e-mr-020"].approved_recipe_sha256

