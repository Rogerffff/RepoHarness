"""S0-7 SWE smoke runner：对冻结题单中的单个 instance 跑一次 rollout + 官方评分。

链路（与 s0_toy_loop.py 同族，改为 per-task 官方 SWE 镜像）：
    EnvConfig(taskset=swebench_smoke 单段本地插件 id（实现在
    repoharness2/taskset/swebench_smoke.py）, harness=default+docker)
      -> Environment.episode(task, ctx, n=1) -> Rollout
      -> DockerRuntime(官方 sweb.eval.x86_64.* 镜像, workdir=/testbed)
      -> default harness (bash+edit) 经 InterceptionServer 中继 deepseek
      -> taskset.finalize 抓 agent diff -> @reward 同容器跑官方 eval 解析 F2P/P2P

模型端点：EvalClient -> https://api.deepseek.com（OpenAI 兼容，deepseek-chat）。
key 优先取进程环境变量 DEEPSEEK_API_KEY（远程机由 ssh 会话经 stdin 注入 env，
不落远程磁盘）；本机开发时回退读仓库根 deepseek_api.md 的同行值。key 绝不打印、
绝不落盘、绝不进 argv；dump 落盘前统一走 scrub + assert 双重剔除。

用法（单题一进程，远程由 run_all.sh 顺序驱动）：
    .venv/bin/python experiments/s0_swe_smoke.py --instance django__django-11099 \
        --out-dir swe_smoke_out
"""

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

RH2_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = RH2_ROOT / "src"
KEY_FILE_CANDIDATES = [
    RH2_ROOT.parent / "deepseek_api.md",  # 本机：仓库根
    RH2_ROOT / "deepseek_api.md",
]

# repoharness2 是 uv `package = false` 虚拟项目（不装进 venv），taskset 以
# "本地插件"方式经 sys.path 提供。注意：verifiers pin 5885ab9c 的 loader 对多段
# 点分 id（如 repoharness2.taskset.swebench_smoke）会先 find_spec 探测
# `verifiers.v1.tasksets.<id>`，中间父包不存在时 find_spec 直接抛
# ModuleNotFoundError（而非返回 None），本地 fallback 分支永远走不到——实测 8 题
# 全部秒败于此。所以本地插件 id 必须用单段模块名（与 S0-3 toy-taskset fixture
# 同一约定），把 taskset 目录本身加进 sys.path、按 `swebench_smoke` 引用。
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(SRC_DIR / "repoharness2" / "taskset"))

TASKSET_ID = "swebench_smoke"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DUMP_NODES_CAP_BYTES = 5 * 1024 * 1024  # 超过则只保留 branches 摘要

# ---------------------------------------------------------------------------
# 密钥处理（同 s0_toy_loop.py 的修正版：同行匹配，只吃水平空白）
# ---------------------------------------------------------------------------
_SECRET_KEY_NAMES = {
    "authorization", "proxy-authorization", "api_key", "api-key", "apikey",
    "x-api-key", "secret", "access_token", "refresh_token", "password",
}
_SK_RE = re.compile(r"sk-[A-Za-z0-9_\-]{8,}")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{6,}")


def load_deepseek_key() -> str:
    """key 状态：env（环境变量注入，远程路径）/ present（本机文件）/ missing。"""
    if os.environ.get("DEEPSEEK_API_KEY"):
        return "env"
    for key_file in KEY_FILE_CANDIDATES:
        if not key_file.exists():
            continue
        match = re.search(
            r"(?im)^[ \t]*DEEPSEEK_API_KEY[ \t]*:[ \t]*(\S+)[ \t]*$", key_file.read_text()
        )
        if match:
            os.environ["DEEPSEEK_API_KEY"] = match.group(1)
            return "present"
    return "missing"


def scrub_secrets(obj):
    if isinstance(obj, dict):
        return {
            k: ("[REDACTED]" if str(k).lower() in _SECRET_KEY_NAMES else scrub_secrets(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [scrub_secrets(v) for v in obj]
    if isinstance(obj, str):
        return _BEARER_RE.sub("Bearer [REDACTED]", _SK_RE.sub("sk-[REDACTED]", obj))
    return obj


def assert_no_secret(text: str) -> None:
    if _SK_RE.search(text):
        raise RuntimeError("dump 中检测到 sk- 形态字符串，拒绝落盘")
    real_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if real_key and real_key in text:
        raise RuntimeError("dump 中检测到 DEEPSEEK_API_KEY 字面值，拒绝落盘")


# ---------------------------------------------------------------------------
# 镜像准备（pull 时间计入 env_reset 观测，不占 rollout setup 超时）
# ---------------------------------------------------------------------------


def ensure_image(image: str) -> dict:
    """镜像不在本地则 docker pull（计时）；返回 {pulled, pull_seconds, local_digest, size_bytes}。"""
    inspect = subprocess.run(
        ["docker", "image", "inspect", image, "--format",
         "{{json .RepoDigests}} {{.Size}}"],
        capture_output=True, text=True,
    )
    pulled, pull_seconds = False, 0.0
    if inspect.returncode != 0:
        started = time.time()
        subprocess.run(["docker", "pull", "-q", image], check=True, capture_output=True)
        pull_seconds = time.time() - started
        pulled = True
        inspect = subprocess.run(
            ["docker", "image", "inspect", image, "--format",
             "{{json .RepoDigests}} {{.Size}}"],
            capture_output=True, text=True, check=True,
        )
    digests_json, _, size = inspect.stdout.strip().rpartition(" ")
    digests = json.loads(digests_json) if digests_json else []
    return {
        "pulled_now": pulled,
        "pull_seconds": round(pull_seconds, 1),
        "local_repo_digest": digests[0] if digests else None,
        "size_bytes": int(size) if size.isdigit() else None,
    }


# ---------------------------------------------------------------------------
# 单题 runner
# ---------------------------------------------------------------------------


def branch_summary(trace) -> list[dict]:
    """dump 超限时的降级形态：只保留每个 branch 的拓扑摘要，不保留消息全文。"""
    out = []
    for branch in trace.branches:
        out.append(
            {
                "index": branch.index,
                "num_nodes": len(branch.nodes),
                "num_turns": branch.num_turns,
                "roles": [n.message.role for n in branch.nodes],
                "content_chars": [len(str(n.message.content or "")) for n in branch.nodes],
                "tool_calls": [
                    [tc.function.name for tc in (n.message.tool_calls or [])]
                    for n in branch.nodes
                ],
            }
        )
    return out


async def run_one(args) -> dict:
    from verifiers.v1.clients import RolloutContext, resolve_client
    from verifiers.v1.clients.config import EvalClientConfig
    from verifiers.v1.env import EnvConfig, Environment
    from verifiers.v1.types import SamplingConfig

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    eval_log_dir = out_dir / "eval_logs"

    env_config = EnvConfig(
        taskset={
            "id": TASKSET_ID,
            "subset": [args.instance],
            "eval_log_dir": str(eval_log_dir),
        },
        harness={
            "id": "default",
            "runtime": {"type": "docker"},  # image/workdir 由 Task 注入（官方镜像 + /testbed）
            # BASH_ENV：让 agent 的每次 `bash -c` 先 source conda testbed 激活脚本
            # （文件由 taskset.setup 写入容器；bash 对不存在的 BASH_ENV 文件静默跳过）。
            "env": {"BASH_ENV": "/root/.rh2_bash_env"},
        },
        max_turns=args.max_turns,
        timeout={
            "setup": 900,      # 容器启动 + taskset 校验 + harness uv 引导（镜像已预拉）
            "rollout": args.rollout_timeout,
            "finalize": 300,
            "scoring": 1500,   # pip install -e . + 官方测试命令，题单静态目标 <5min
        },
    )
    env = Environment(env_config)
    tasks = env.taskset.load_tasks()
    assert len(tasks) == 1, f"subset 应恰好命中 1 题，得到 {len(tasks)}"
    task = tasks[0]

    image_info = ensure_image(task.image)
    frozen = env.taskset._rows()[task.instance_id]
    digest_match = (
        image_info["local_repo_digest"] is not None
        and image_info["local_repo_digest"].endswith(frozen["image_manifest_digest"])
    )

    client = resolve_client(
        EvalClientConfig(base_url=DEEPSEEK_BASE_URL, api_key_var="DEEPSEEK_API_KEY")
    )
    ctx = RolloutContext(
        model=args.model,
        client=client,
        sampling=SamplingConfig(temperature=0.0, max_tokens=4096),
    )

    wall_start = time.time()
    try:
        episode = env.episode(task, ctx, n=1)
        traces = await episode.run()
    finally:
        await client.close()
    wall_seconds = time.time() - wall_start
    trace = traces[0]

    timing = trace.timing
    summary = {
        "instance_id": task.instance_id,
        "repo": task.repo,
        "image": task.image,
        "image_pull": image_info,
        "image_digest_match": digest_match,
        "reward": trace.reward,
        "rewards": dict(trace.rewards),
        "metrics": dict(trace.metrics),
        "resolution": (trace.info.get("swe_eval") or {}).get("resolution"),
        "num_turns": trace.num_turns,
        "num_branches": trace.num_branches,
        "num_input_tokens": trace.num_input_tokens,
        "num_output_tokens": trace.num_output_tokens,
        "stop_condition": trace.stop_condition,
        "error_type": trace.error.type if trace.error else None,
        "error_message_head": (
            scrub_secrets(trace.error.message)[:300] if trace.error else None
        ),
        "wall_seconds": round(wall_seconds, 1),
        "phase_seconds": {
            "setup": round(timing.setup.duration, 1),
            "generation": round(timing.generation.duration, 1),
            "finalize": round(timing.finalize.duration, 1),
            "scoring": round(timing.scoring.duration, 1),
        },
    }

    dump = {
        "meta": {
            "stage": "rh2-s0-7-swe-smoke",
            "verifiers_pin": "5885ab9c54152e707af2a11797aa52c3eb1752da",
            "taskset_id": TASKSET_ID,
            "harness": "default(bash+edit) @ docker",
            "endpoint_base_url": DEEPSEEK_BASE_URL,
            "model": args.model,
            "max_turns": args.max_turns,
            "sampling": {"temperature": 0.0, "max_tokens": 4096},
            "deepseek_key_status": args.key_status,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "note": (
                "EvalClient 文本中继模式：token_ids/mask/logprobs 为空是预期行为；"
                "评分与 agent 同容器（S0 不做评分隔离，见 taskset docstring）。"
            ),
        },
        "summary": summary,
        "trace": trace.to_record(),
    }
    text = json.dumps(scrub_secrets(dump), ensure_ascii=False, indent=1)
    if len(text.encode()) > DUMP_NODES_CAP_BYTES:
        dump["trace"] = {
            "note": f"完整 nodes 超过 {DUMP_NODES_CAP_BYTES} bytes，降级为 branches 摘要",
            "branches_summary": branch_summary(trace),
            "info": trace.to_record().get("info"),
        }
        text = json.dumps(scrub_secrets(dump), ensure_ascii=False, indent=1)
    assert_no_secret(text)
    out_path = out_dir / f"{task.instance_id}.json"
    out_path.write_text(text)

    print(f"\n=== {task.instance_id} ===")
    print(
        f"reward={summary['reward']:.1f} resolution={summary['resolution']} "
        f"turns={summary['num_turns']} stop={summary['stop_condition']} "
        f"error={summary['error_type']}"
    )
    print(
        f"wall={summary['wall_seconds']}s phases={summary['phase_seconds']} "
        f"pull={image_info['pull_seconds']}s digest_match={digest_match}"
    )
    print(f"dump -> {out_path}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", required=True, help="冻结题单里的 instance_id")
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--max-turns", type=int, default=30)
    parser.add_argument("--rollout-timeout", type=float, default=1800)
    parser.add_argument("--out-dir", default=str(RH2_ROOT / "swe_smoke_out"))
    args = parser.parse_args()

    args.key_status = load_deepseek_key()
    print(f"deepseek key status: {args.key_status}（key 内容不打印）")
    if args.key_status == "missing":
        raise SystemExit("缺少 DEEPSEEK_API_KEY（环境变量或 deepseek_api.md 同行值）")

    asyncio.run(run_one(args))


if __name__ == "__main__":
    main()
