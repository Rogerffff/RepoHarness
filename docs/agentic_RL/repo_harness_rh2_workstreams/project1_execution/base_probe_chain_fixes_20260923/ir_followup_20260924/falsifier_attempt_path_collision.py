"""日志路径限定 CPU 反例：真实身份铸造、路径函数和 wb 写入；不运行 Docker。

从仓库根执行：
  PYTHONDONTWRITEBYTECODE=1 rh2/.venv/bin/python <本文件>
默认只打印；--out 用独占创建保存新证据，拒绝覆盖已有 JSON。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

REPO = next(p for p in Path(__file__).resolve().parents if (p / "rh2/src").is_dir())
sys.path[:0] = [str(REPO / "rh2/src"), str(REPO / "reference/miles-rh2-integration")]

from repoharness2.adapters.miles.identity import (
    mint_attempt_identity,
    mint_eval_attempt_identity,
)
from repoharness2.adapters.slime.docker_sandbox import _open_log
from repoharness2.adapters.slime.generate import RolloutOrchestrator


def eval_identity(*, slot: int, prompt: int = 0, samples: int = 2) -> dict:
    sample = SimpleNamespace(status="pending", metadata={"rh2_eval_dispatch": {
        "eval_point_id": "0123456789ab",  # 当前 miles 集成真实形状：uuid4().hex[:12]
        "dataset": "probe", "dataset_index": 0, "prompt_index": prompt,
        "sample_slot": slot, "n_samples_per_eval_prompt": samples, "num_prompts": 200,
    }})
    return mint_eval_attempt_identity(sample)


def describe(identity: dict, artifact_dir: Path) -> dict:
    execution = identity["rh2_rollout_execution_id"]
    attempt = identity["rh2_physical_attempt_id"]
    path = RolloutOrchestrator._harness_log_dir(
        SimpleNamespace(artifact_dir=artifact_dir),
        SimpleNamespace(trajectory_id=execution, physical_attempt_id=attempt),
    )
    relative = Path(path).relative_to(artifact_dir)
    return {
        "trajectory_id": execution,
        "physical_attempt_id": attempt,
        "attempt_seq": identity["rh2_physical_attempt_seq"],
        "trajectory_length": len(execution), "attempt_length": len(attempt),
        "trajectory_directory_component": relative.parts[0],
        "attempt_directory_component": relative.parts[-1],
        "log_dir_relative_to_artifacts": str(relative),
        "attempt_suffix": attempt[len(execution):],
        "attempt_directory_ends_before_suffix": len(execution) >= 24,
    }


def pair(label: str, first: dict, second: dict, artifact_dir: Path) -> dict:
    rows = [describe(first, artifact_dir), describe(second, artifact_dir)]
    return {"case": label, "rows": rows,
            "same_log_dir": rows[0]["log_dir_relative_to_artifacts"] == rows[1]["log_dir_relative_to_artifacts"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    ns = parser.parse_args()
    rows = []
    with tempfile.TemporaryDirectory(prefix="rh2-log-path-review-", dir="/tmp") as temporary:
        root = Path(temporary)
        slot0, slot1 = eval_identity(slot=0), eval_identity(slot=1)
        rows.append(pair("eval_same_prompt_slots_0_1", slot0, slot1, root))
        rows.append(pair("eval_single_sample_prompts_100_101", eval_identity(slot=0, prompt=100, samples=1),
                         eval_identity(slot=0, prompt=101, samples=1), root))
        rows.append(pair("same_eval_trajectory_two_fresh_physical_ids", slot0, eval_identity(slot=0), root))
        # 上一项验证两个真实铸造的 physical id；不声称当前 miles eval 实施 retry。
        for group in (0, 1, 1000, 1_000_000):
            sample = SimpleNamespace(status="pending", group_index=group, index=group * 4, metadata={})
            first = mint_attempt_identity(sample, n_samples_per_prompt=4)
            sample.status = "aborted"
            second = mint_attempt_identity(sample, n_samples_per_prompt=4)
            rows.append(pair(f"training_group_{group}_real_retry", first, second, root))
        a = root / rows[0]["rows"][0]["log_dir_relative_to_artifacts"] / "trajectory.jsonl"
        b = root / rows[0]["rows"][1]["log_dir_relative_to_artifacts"] / "trajectory.jsonl"
        with _open_log(a) as fh:
            fh.write(b"slot0 log\n")
        with _open_log(b) as fh:
            fh.write(b"slot1 log\n")
        overwrite = {"same_file": a == b, "final_content": a.read_text(),
                     "first_log_lost": a.read_bytes() == b"slot1 log\n"}
    result = {
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "scope": "真实 minter + _harness_log_dir + _open_log；Sample 外壳用 SimpleNamespace；无 Docker/GPU/网络",
        "production_sources": {
            "eval_point_id_12_hex": "reference/miles-rh2-integration/miles/rollout/inference_rollout/inference_rollout_eval.py:52",
            "eval_identity": "rh2/src/repoharness2/adapters/miles/identity.py:372",
            "name_truncation_24": "rh2/src/repoharness2/adapters/slime/generate.py:2431",
            "log_path": "rh2/src/repoharness2/adapters/slime/generate.py:3957",
            "write_mode": "rh2/src/repoharness2/adapters/slime/docker_sandbox.py:423",
        },
        "cases": rows,
        "actual_wb_overwrite": overwrite,
        "interpretation": "正式评测身份发生确定碰撞；所测短训练身份的真实 retry 均不碰撞。仅日志隔离问题，不是训练或评分混样。",
    }
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if ns.out:
        with ns.out.open("x", encoding="utf-8") as fh:
            fh.write(output)
    print(output, end="")


if __name__ == "__main__":
    main()
