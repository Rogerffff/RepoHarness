"""复用固定版 R2E devcheck；正对照补丁只由宿主经 stdin 应用，不交给 CC。

此包内适配器不是评分器。原 devcheck 的初始化、身份、CC Bash、取证和清理
保持原样；题面真实交付另走固定版 probe_e2e，不由 devcheck 控制提示证明。
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, add_help=False, allow_abbrev=False
    )
    parser.add_argument("--fixed-repo", required=True, type=Path)
    parser.add_argument("--release-manifest-sha256", required=True)
    parser.add_argument("--host-patch", type=Path)
    parser.add_argument("--host-patch-sha256")
    owner, forwarded = parser.parse_known_args()
    release = owner.fixed_repo.resolve().parent
    if digest((release / "manifest.json").read_bytes()) != owner.release_manifest_sha256:
        raise ValueError("固定发布清单与外部登记摘要不符")
    verify = subprocess.run(
        [sys.executable, "-B", str(release / "verify_release.py")],
        cwd=release, capture_output=True, text=True, check=False,
    )
    if verify.returncode:
        raise RuntimeError("固定发布逐文件回读失败：" + verify.stdout[-1000:])
    patch = None
    if owner.host_patch is not None:
        patch = owner.host_patch.read_bytes()
        if digest(patch) != owner.host_patch_sha256:
            raise ValueError("宿主正对照补丁与登记摘要不符")
    elif owner.host_patch_sha256 is not None:
        raise ValueError("补丁摘要必须和补丁文件同时指定")

    entry = owner.fixed_repo / "rh2/experiments/r2e_actor_20260925/r2e_devcheck.py"
    spec = importlib.util.spec_from_file_location("aiohttp_fixed_devcheck", entry)
    if spec is None or spec.loader is None:
        raise ImportError("无法装载固定版 R2E devcheck")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class HostPatchedRunner(module.R2EDevRunner):
        async def solve(self, task_spec, env_inj):
            self.rec["aiohttp_owner_control"] = {
                "release_manifest_sha256": owner.release_manifest_sha256,
                "adapter_sha256": digest(Path(__file__).read_bytes()),
                "host_patch_sha256": None if patch is None else digest(patch),
                "application": "none" if patch is None else "pending",
                "application_user": self.profile.agent_user,
                "patch_file_delivered_to_actor": False,
            }
            self.save()
            if patch is not None:
                prefix = "cd /testbed && git -c safe.directory=/testbed apply "
                check = await self.sh(
                    prefix + "--check -", user=self.profile.agent_user, input_bytes=patch
                )
                if check.exit_code:
                    raise RuntimeError("宿主正对照补丁不能应用：" + check.stderr[-1000:])
                applied = await self.sh(
                    prefix + "-", user=self.profile.agent_user, input_bytes=patch
                )
                if applied.exit_code:
                    raise RuntimeError("宿主正对照补丁应用失败：" + applied.stderr[-1000:])
                self.rec["aiohttp_owner_control"]["application"] = "applied_before_actor"
                self.save()
            return await super().solve(task_spec, env_inj)

    module.R2EDevRunner = HostPatchedRunner
    return module.main(forwarded)


if __name__ == "__main__":
    raise SystemExit(main())
