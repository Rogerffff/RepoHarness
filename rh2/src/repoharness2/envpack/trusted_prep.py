"""一次性 trusted-prep 进程入口（W1b 第一集成切片 F6）。

用法（host 侧，在 miles 训练脚本调用 create_rollout_manager **之前**运行，跑完即退出；
不是长驻服务）::

    uv run python -m repoharness2.envpack.trusted_prep \
        --repo-root /path/to/claude-code-verl-stage0h \
        --out-dir   /root/run/prepared_tasks \
        --private-dir /root/run/private/host_grading

随后启动参数：
    miles:   --prompt-data /root/run/prepared_tasks/prompts.jsonl --input-key prompt --label-key label --metadata-key metadata
    bringup: RH2_PREPARED_TASKS_DIR=/root/run/prepared_tasks
             RH2_PREPARED_TASKS_MANIFEST_SHA256=<本命令 stdout 打印的 prepared_manifest_sha256>
             RH2_HOST_GRADING_ARTIFACT_PATH=/root/run/private/host_grading/host_grading_views.jsonl
             RH2_HOST_GRADING_ARTIFACT_SHA256=<本命令 stdout 打印的 host_grading_artifact_sha256>

`prepared_manifest_sha256` 是公开 manifest 文件的**外部**输入身份（06 §6 的被动 digest，
不是授权闸门）：actor 启动时核验 manifest 文件 digest 与之相等，目录内三件套协调篡改
在此 fail-closed。只有本进程调用完整 loader（TrustedTaskController.from_repo_root）；
RolloutManager actor 只读产物。stdout 打印的 JSON 只含路径、计数与 digest，不含任何私有内容。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from repoharness2.envpack.prepared_tasks import (
    HOST_GRADING_FILE,
    MANIFEST_FILE,
    PROMPTS_FILE,
    manifest_file_sha256,
    prepare_tasks,
)
from repoharness2.envpack.training_view import TrustedTaskController


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="rh2 一次性 trusted-prep：生成 prepared artifact 后退出。")
    parser.add_argument("--repo-root", required=True, help="仓库根（load_trusted_ingest_outputs 的 repo_root）")
    parser.add_argument("--out-dir", required=True, help="公开产物目录（prompts.jsonl / rollout_task_views.jsonl / manifest）")
    parser.add_argument("--private-dir", required=True, help="runtime-private 产物目录（0700；host_grading_views.jsonl 0600）")
    parser.add_argument(
        "--task-ids",
        default=None,
        help="逗号分隔的 source-qualified task_id 子集（缺省 = controller 全部任务）",
    )
    ns = parser.parse_args(argv)

    controller = TrustedTaskController.from_repo_root(Path(ns.repo_root).resolve())
    task_ids = [x.strip() for x in ns.task_ids.split(",") if x.strip()] if ns.task_ids else None
    manifest = prepare_tasks(
        controller,
        out_dir=Path(ns.out_dir),
        private_dir=Path(ns.private_dir),
        task_ids=task_ids,
    )
    summary = {
        "prepared_dir": str(Path(ns.out_dir).resolve()),
        "manifest": str((Path(ns.out_dir) / MANIFEST_FILE).resolve()),
        "prepared_manifest_sha256": manifest_file_sha256(Path(ns.out_dir)),
        "prompt_data": str((Path(ns.out_dir) / PROMPTS_FILE).resolve()),
        "host_grading_artifact_path": str((Path(ns.private_dir) / HOST_GRADING_FILE).resolve()),
        "host_grading_artifact_sha256": manifest.host_grading_artifact_sha256,
        "task_count": manifest.task_count,
    }
    json.dump(summary, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":  # pragma: no cover - 进程入口
    raise SystemExit(main())
