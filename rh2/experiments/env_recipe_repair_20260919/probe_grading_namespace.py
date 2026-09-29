"""用独占label的sleep容器验证年龄清扫反例与诊断命名空间；不碰真实评分容器。

历史反例（2026-09-20，B 线 Claude 标注）：本探针断言的是**修复前**的行为——同命名空间里创建超过 3600 秒的活跃容器
会被另一个 manager 的 `startup()` 删除（证据 `runs/env_recipe_repair_20260919/namespace_probe_1909.json`）。A 线已在
2026-09-20 删除跨 manager 清扫（`startup()` 恒返回 []、`orphan_min_age_seconds` 配置字段已删），对修复后的源码运行
本探针，"same_namespace 被删"这一条**必然不再成立**。保留作历史证据；维护中的等价用例是
`tests/grading/test_manager_docker.py::test_foreign_live_containers_survive_another_manager_startup_and_close_real`。
"""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid


async def main(args):
    sys.path.insert(0, str(Path(args.code_root) / "src"))
    from repoharness2.grading.manager import GradingManagerConfig, SWEGradingManager

    prefix = "rh2.envrepair.namespaceprobe." + uuid.uuid4().hex[:8]
    containers = []
    results = []

    def docker(*values):
        return subprocess.check_output(["docker", *values], text=True, timeout=30).strip()

    try:
        for same_namespace in [True, False]:
            name = "rh2-namespace-probe-" + uuid.uuid4().hex[:8]
            containers.append(name)
            cid = docker("run", "-d", "--name", name, "--network", "none", "--memory", "64m",
                         "--cpus", "0.1", "--pids-limit", "16", "--cap-drop", "ALL",
                         "--label", prefix + ".owner=live-other-manager",
                         "--label", prefix + ".created_at_epoch=" + str(int(time.time()) - 7200),
                         args.image, "sleep", "300")
            assert docker("inspect", "--format", "{{.State.Running}}", name) == "true"
            selected = prefix if same_namespace else prefix + ".other"
            manager = SWEGradingManager(GradingManagerConfig(label_prefix=selected))
            removed = await manager.startup()
            listed = docker("ps", "-q", "--no-trunc", "--filter", "name=^/" + name + "$")
            assert (cid not in listed.splitlines()) == same_namespace
            results.append({"same_namespace": same_namespace, "alive_before_startup": True,
                            "removed": removed, "alive_after_startup": cid in listed.splitlines(),
                            "configured_grace_seconds": getattr(manager.config, "orphan_min_age_seconds", None)})
            await manager.close()
    finally:
        for name in containers:
            subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=30, check=False)
    for name in containers:
        assert not docker("ps", "-aq", "--filter", "name=^/" + name + "$")
    source = Path(args.code_root) / "src/repoharness2/grading/manager.py"
    output = {"at": time.time(), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "cases": results, "cleanup_verified": True,
              "limit": "config isolation for experiments; not a production orphan-detection fix"}
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-root", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", required=True)
    asyncio.run(main(parser.parse_args()))
