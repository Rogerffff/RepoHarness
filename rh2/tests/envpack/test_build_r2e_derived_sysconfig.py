"""R2E 派生镜像的构建配置步骤（sysconfig_v1.sh，2026-09-29）：Dockerfile 拼接顺序、配方身份叠加与向后兼容。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_r2e_derived.py"
_spec = importlib.util.spec_from_file_location("build_r2e_derived_sysconfig_under_test", _SCRIPT)
bd = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = bd
_spec.loader.exec_module(bd)


def test_without_step_dockerfiles_are_unchanged():
    assert bd.render_dockerfile(material=False, env=False) == bd.DOCKERFILE
    assert bd.render_dockerfile(material=True, env=False) == bd.DOCKERFILE_MATERIAL
    assert bd.render_dockerfile(material=False, env=True, sysconfig=False) == bd.render_dockerfile(material=False, env=True)


def test_step_runs_right_after_recipe_v1():
    plain = bd.render_dockerfile(material=False, env=False, sysconfig=True)
    assert f"COPY {bd.SYSCONFIG_STEP} /rh2_build/{bd.SYSCONFIG_STEP}" in plain
    assert f'RUN bash /rh2_build/recipe_v1.sh "$FIX_COMMIT" && bash /rh2_build/{bd.SYSCONFIG_STEP} && rm -rf /rh2_build' in plain

    full = bd.render_dockerfile(material=True, env=True, env_step="env_v2.sh", sysconfig=True)
    run = next(line for line in full.splitlines() if line.startswith("RUN "))
    order = [run.index("recipe_v1.sh"), run.index(bd.SYSCONFIG_STEP), run.index(bd.MATERIAL_STEP), run.index("env_v2.sh")]
    assert order == sorted(order)


def test_identity_is_layered_on_the_base_recipe():
    rid, sha, tag = bd.with_sysconfig_step(bd.RECIPE_ID, "sha256:" + "0" * 64, bd.RECIPE_ID)
    assert rid == "r2e_derive_v1+sysconfig_v1" and tag == "r2e_derive_v1s" and sha.startswith("sha256:")
    rid2, sha2, _ = bd.with_sysconfig_step(bd.RECIPE_ID, "sha256:" + "1" * 64, bd.RECIPE_ID)
    assert rid2 == rid and sha2 != sha  # 原配方摘要不同，叠加后的身份也不同
    # 环境要求按片段匹配：叠加后仍含 +env_v2（orange3 9b5494e2 的 r2e-mr-020 依赖它）
    rid3, _, tag3 = bd.with_sysconfig_step("r2e_derive_v1+material_v2+env_v2", "sha256:" + "2" * 64, "r2e_derive_v1m2e2")
    assert "+env_v2" in rid3 and rid3.endswith("+sysconfig_v1") and tag3 == "r2e_derive_v1m2e2s"


def test_step_script_exists_and_only_touches_opt_py():
    body = (bd.ENV_STEP_DIR / bd.SYSCONFIG_STEP).read_text()
    assert "set -euo pipefail" in body and 'NEW="/opt/py/$PYDIR"' in body
    code = "\n".join(line for line in body.splitlines() if not line.lstrip().startswith("#"))  # 只看可执行行，注释可以提到这些路径
    for forbidden in ("/testbed", ".venv", "pip install", "chmod -R a+rX /root"):
        assert forbidden not in code
