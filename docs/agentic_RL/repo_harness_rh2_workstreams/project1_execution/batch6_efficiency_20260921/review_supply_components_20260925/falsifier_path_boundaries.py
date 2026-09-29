"""9c59a1f6 / b169c10e 有界本地复核；不调用 Docker、不修改生产文件。

从仓库根执行：PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=rh2/src rh2/.venv/bin/python <本文件>
使用真实 rollout workspace 命令前缀，但以当前本机 UID 执行，不声称是容器 root 验证。
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

from pydantic import ValidationError
from repoharness2.adapters.slime.baseline_census import generate_baseline_manifest
from repoharness2.adapters.slime.generate import RolloutContainerWorkspace
from repoharness2.adapters.slime.patch_exporter import (
    PatchExportError,
    export_frozen_patch,
)
from repoharness2.contracts.baseline_manifest import (
    BASELINE_MANIFEST_POLICY_V1,
    BaselineWorkspaceManifestV1,
    compute_policy_digest,
)
from repoharness2.grading.manager import ExecResult

HERE = Path(__file__).resolve().parent
SYSTEM_PATH = "/usr/sbin:/usr/bin:/sbin:/bin"


class LocalRunner:
    def __init__(self, env: dict[str, str]):
        self.env = env

    async def __call__(self, *args: str, **_kwargs) -> ExecResult:
        assert args[:2] == ("exec", "local-probe")
        proc = await asyncio.create_subprocess_exec(
            *args[2:], env=self.env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, err = await asyncio.wait_for(proc.communicate(), timeout=5)
        return ExecResult(proc.returncode, out.decode(errors="replace"), err.decode(errors="replace"))


def empty_baseline(workdir: str) -> BaselineWorkspaceManifestV1:
    return BaselineWorkspaceManifestV1(
        task_id="t", workdir=workdir, public_bundle_digest="sha256:" + "e" * 64,
        runtime_image_digest="sha256:" + "1" * 64, materialized_head="a" * 40, task_base_commit="a" * 40,
        policy=BASELINE_MANIFEST_POLICY_V1, policy_digest=compute_policy_digest(BASELINE_MANIFEST_POLICY_V1), entries=(),
    )


async def export_result(workspace, baseline) -> dict:
    try:
        artifact = await export_frozen_patch(workspace, baseline, rollout_execution_id="e", physical_attempt_id="e#p1-aaaa")
        return {"class": "FrozenPatchArtifactV1", "paths": [entry.path for entry in artifact.entries]}
    except (PatchExportError, ValidationError) as exc:
        validation = exc if isinstance(exc, ValidationError) else exc.__cause__
        result = {"class": type(exc).__name__, "reason": getattr(exc, "reason_code", None)}
        if isinstance(exc, PatchExportError):
            result.update(object_path=exc.object_path, object_type=exc.object_type)
        if isinstance(validation, ValidationError):
            result["validation_errors"] = [
                {"loc": list(error["loc"]), "type": error["type"], "msg": error["msg"]}
                for error in validation.errors()
            ]
        return result


async def actual_files(base: Path) -> dict:
    results = {}
    runner = LocalRunner({"PATH": SYSTEM_PATH, "HOME": str(base)})
    for case, filename, symlink in (
        ("normal", "normal.py", False),
        ("regular_0x01", "bad\x01name.py", False),
        ("symlink_0x7f", "bad\x7fname.py", True),
    ):
        tree = base / case
        tree.mkdir()
        workspace = RolloutContainerWorkspace(runner, "local-probe", str(tree))
        baseline = await generate_baseline_manifest(
            workspace, task_id="t", workdir=str(tree), public_bundle_digest="sha256:" + "e" * 64,
            runtime_image_digest="sha256:" + "1" * 64, materialized_head="a" * 40, task_base_commit="a" * 40,
        )
        if symlink:
            (tree / filename).symlink_to("missing-target")
        else:
            (tree / filename).write_text("x = 1\n")
        results[case] = await export_result(workspace, baseline)
    return results


class TextWorkspace:
    def __init__(self, text: str):
        self.text = text

    async def run_bash(self, _script: str) -> SimpleNamespace:
        return SimpleNamespace(exit_code=0, stdout=self.text, stderr="")


async def mixed_error_probe() -> dict:
    good_hash = "a" * 64
    rows = {
        "digest_error_only": "regular\t100644\tNOT_A_DIGEST\tfirst.py\n",
        "digest_error_then_bad_path": f"regular\t100644\tNOT_A_DIGEST\tfirst.py\nregular\t100644\t{good_hash}\tbad\x01name.py\n",
        "mode_error_and_bad_path": f"regular\t999999\t{good_hash}\tbad\x01name.py\n",
    }
    return {name: await export_result(TextWorkspace(row), empty_baseline("/testbed")) for name, row in rows.items()}


async def root_prefix_probe(base: Path) -> dict:
    tree, planted = base / "commands", base / "planted"
    tree.mkdir()
    planted.mkdir()
    fake = planted / "find"
    fake.write_text("#!/bin/sh\nprintf 'HIJACKED_FIND\\n'\n")
    fake.chmod(0o755)
    startup = planted / "startup.sh"
    startup.write_text("printf 'HIJACKED_BASH_ENV\\n'\n")
    runner = LocalRunner({"PATH": f"{planted}:{SYSTEM_PATH}", "BASH_ENV": str(startup), "HOME": str(base)})
    workspace = RolloutContainerWorkspace(runner, "local-probe", str(tree))
    script = "find . -name absent-probe-file -print"
    old = await runner("exec", "local-probe", "/bin/bash", "-c", f"cd {tree} && {script}")
    new = await workspace.run_bash(script)
    assert "HIJACKED_BASH_ENV" in old.stdout and "HIJACKED_FIND" in old.stdout
    assert new.exit_code == 0 and new.stdout == ""
    return {
        "scope": "local command selection; current UID, no Docker/root claim",
        "old": {"rc": old.exit_code, "stdout": old.stdout},
        "new": {"rc": new.exit_code, "stdout": new.stdout},
    }


async def main() -> None:
    with tempfile.TemporaryDirectory(prefix="falsifier_local_", dir=HERE) as temp:
        base = Path(temp)
        result = {
            "scope": "current source on local CPU; synthetic malformed metadata cases are test_only",
            "uid": os.getuid(),
            "actual_files": await actual_files(base),
            "root_prefix": await root_prefix_probe(base),
            "synthetic_mixed_errors": await mixed_error_probe(),
        }
    assert result["actual_files"]["normal"]["class"] == "FrozenPatchArtifactV1"
    for name in ("regular_0x01", "symlink_0x7f"):
        assert result["actual_files"][name]["reason"] == "unsupported_object_in_patch"
    assert result["synthetic_mixed_errors"]["digest_error_only"]["class"] == "ValidationError"
    assert result["synthetic_mixed_errors"]["digest_error_then_bad_path"]["class"] == "PatchExportError"
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    HERE.joinpath("falsifier_path_boundaries.json").write_text(output)
    print(output, end="")


if __name__ == "__main__":
    asyncio.run(main())
