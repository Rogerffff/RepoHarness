"""2d01 私有正确解开发对照：复用固定 R2E actor 入口，不交付给 solver。"""

import argparse
import hashlib
import importlib.util
from pathlib import Path
import re


def checked_bytes(path, expected):
    data = path.read_bytes()
    if "sha256:" + hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("固定输入摘要不符：" + path.name)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r2e-devcheck", type=Path, required=True)
    parser.add_argument("--r2e-devcheck-sha256", required=True)
    parser.add_argument("--correct-patch", type=Path, required=True)
    parser.add_argument("--correct-patch-sha256", required=True)
    args, remaining = parser.parse_known_args()
    if remaining[:1] == ["--"]:
        remaining = remaining[1:]
    runner_path = args.r2e_devcheck.resolve()
    checked_bytes(runner_path, args.r2e_devcheck_sha256)
    patch = checked_bytes(args.correct_patch, args.correct_patch_sha256)
    text = patch.decode("utf-8")
    headers = re.findall(r"^diff --git (.+)$", text, flags=re.MULTILINE)
    targets = re.findall(r"^\+\+\+ (.+)$", text, flags=re.MULTILINE)
    if headers != ["a/src/PIL/TiffImagePlugin.py b/src/PIL/TiffImagePlugin.py"]:
        raise ValueError("私有开发对照只允许单个已固定 TIFF 源码补丁")
    if targets != ["b/src/PIL/TiffImagePlugin.py"]:
        raise ValueError("不能向 actor 对照写入测试、材料或其他文件")

    spec = importlib.util.spec_from_file_location("pillow_fixed_r2e_devcheck", runner_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original_runner = module.R2EDevRunner

    class PositiveControlRunner(original_runner):
        async def solve(self, task_spec, env_injections):
            if self.ns.task_id != "r2e_gym_subset::pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96":
                raise ValueError("该对照只接受固定的 2d01 题")
            # 启动前、隔离与解释器检查仍由原入口完成；私有源码对照沿 agent 的可信 shell 环境执行。
            identity = await self.sh("id -u", user="agent", env=env_injections, timeout=60)
            uid = identity.stdout.strip()
            if identity.exit_code != 0 or uid != "54321":
                self.stage("private_positive_control", ok=False, step="identity", observed_uid=uid)
                raise RuntimeError("私有正确解对照的实际身份不符，停止 actor 对照")
            checked = await self.sh(
                "cd /testbed && git apply --check -", user="agent", env=env_injections,
                input_bytes=patch, timeout=120,
            )
            if checked.exit_code != 0:
                self.stage("private_positive_control", ok=False, step="apply_check", exit_code=checked.exit_code)
                raise RuntimeError("私有正确解补丁不能应用，停止 actor 对照")
            applied = await self.sh(
                "cd /testbed && git apply -", user="agent", env=env_injections,
                input_bytes=patch, timeout=120,
            )
            self.stage(
                "private_positive_control", ok=applied.exit_code == 0,
                patch_sha256=args.correct_patch_sha256, target="src/PIL/TiffImagePlugin.py",
                exit_code=applied.exit_code, user="agent", observed_uid=uid,
                delivery="host_stdin_as_agent_before_driver",
            )
            if applied.exit_code != 0:
                raise RuntimeError("私有正确解补丁应用失败，停止 actor 对照")
            return await super().solve(task_spec, env_injections)

    module.R2EDevRunner = PositiveControlRunner
    return module.main(remaining)


if __name__ == "__main__":
    raise SystemExit(main())
