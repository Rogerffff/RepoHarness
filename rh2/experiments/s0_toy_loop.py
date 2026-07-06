"""S0-3 玩具闭环 runner：用 pinned verifiers（5885ab9c）在本机跑 ToyTaskset 的 in-process rollout。

矩阵维度（每次调用跑一格）：
    --harness  default | null        （default = bash+edit 本地工具；null = 纯 chat 无本地工具）
    --runtime  subprocess | docker   （docker 用本机 daemon，镜像默认 python:3.12-slim）
    --endpoint mock | deepseek       （模型端点，见下）

入口链路（对应执行计划 S0-3 第 2 步）：
    EnvConfig -> Environment -> Environment.episode(task, ctx, n=1) -> Episode.run()
    （不进入 env.serving()：本 taskset 无 shared tools / user sim，走 per-rollout
    InterceptionServer 路径，也让 macOS docker shim 只需要覆盖 reachable_url 一个点。）

模型端点两种模式：
    - deepseek：EvalClient 指向 https://api.deepseek.com（OpenAI 兼容），模型 deepseek-chat。
      key 在进程内从 deepseek_api.md 读取并写入 os.environ["DEEPSEEK_API_KEY"]，
      绝不打印、绝不落盘、绝不出现在命令行参数里。
    - mock：本进程起一个脚本化的 OpenAI 兼容 /v1/chat/completions server（无需任何 key），
      按任务内容回放固定的 bash/edit 工具调用。用途：在 deepseek key 缺失/失效时，
      仍然完成矩阵的结构层验收（branches/messages/工具往返/limits/reward 边界）。
      mock 的 usage 数字是合成值，不代表真实 provider 计数——dump 的 meta 里有标注。

产物：把每格两条 Trace 用 to_record()（即 model_dump(mode="json") 去掉张量字段）序列化，
经过密钥剔除检查后写入
    docs/agentic_RL/repo_harness_rh2_workstreams/s0/toy_trace_dump/<tag>.json
默认 tag = <harness>_<runtime>。

用法示例（在仓库根目录）：
    rh2/.venv/bin/python rh2/experiments/s0_toy_loop.py --harness default --runtime subprocess
    rh2/.venv/bin/python rh2/experiments/s0_toy_loop.py --harness null --runtime docker
    rh2/.venv/bin/python rh2/experiments/s0_toy_loop.py --harness default --runtime subprocess \
        --max-turns 1 --tag default_subprocess_maxturns1     # 验证 RolloutLimits
    rh2/.venv/bin/python rh2/experiments/s0_toy_loop.py --harness default --runtime subprocess \
        --endpoint deepseek --tag default_subprocess_deepseek_attempt
"""

import argparse
import asyncio
import contextlib
import json
import os
import platform
import re
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "rh2" / "tests" / "fixtures"
DUMP_DIR = (
    REPO_ROOT / "docs" / "agentic_RL" / "repo_harness_rh2_workstreams" / "s0" / "toy_trace_dump"
)
KEY_FILE = REPO_ROOT / "deepseek_api.md"

# toy_taskset 作为"本地 taskset 插件"必须在 EnvConfig 构造之前可 import
# （EnvConfig 的 model_validator 会按 id 收窄 taskset config 类型）。
sys.path.insert(0, str(FIXTURES_DIR))

DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# ---------------------------------------------------------------------------
# 密钥处理：进程内读文件设 env；任何输出路径都做剔除检查
# ---------------------------------------------------------------------------

# dump 前要整体掩码的字典键名（不区分大小写）。
_SECRET_KEY_NAMES = {
    "authorization",
    "proxy-authorization",
    "api_key",
    "api-key",
    "apikey",
    "x-api-key",
    "secret",
    "access_token",
    "refresh_token",
    "password",
}
# 字符串内容里出现的 key 形态也要掩码（sk- 前缀 / Bearer 头）。
_SK_RE = re.compile(r"sk-[A-Za-z0-9_\-]{8,}")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{6,}")


def load_deepseek_key() -> str:
    """从 deepseek_api.md 的 `DEEPSEEK_API_KEY:` 行读 key，写入进程 env，返回状态。

    返回值只有三种（都不含 key 内容）：
        present      —— 行存在且有值，已写入 os.environ["DEEPSEEK_API_KEY"]
        missing      —— 行存在但值为空（或没有该行）
        file_missing —— 文件不存在
    """
    if not KEY_FILE.exists():
        return "file_missing"
    # 关键：冒号后只吃"水平空白"[ \t]，绝不用 \s*（\s 含换行）。
    # 否则一个空的 `DEEPSEEK_API_KEY:` 行会跨行匹配到下一行的 OPENAI key，
    # 把 OpenAI 凭据发到 DeepSeek 端点——这正是必须杜绝的跨服务凭据误用。
    match = re.search(
        r"(?im)^[ \t]*DEEPSEEK_API_KEY[ \t]*:[ \t]*(\S+)[ \t]*$", KEY_FILE.read_text()
    )
    if match:
        os.environ["DEEPSEEK_API_KEY"] = match.group(1)
        return "present"
    return "missing"


def scrub_secrets(obj):
    """递归剔除疑似凭据：敏感键名的值整体替换；字符串里的 sk-*/Bearer * 掩码。"""
    if isinstance(obj, dict):
        return {
            key: ("[REDACTED]" if str(key).lower() in _SECRET_KEY_NAMES else scrub_secrets(value))
            for key, value in obj.items()
        }
    if isinstance(obj, list):
        return [scrub_secrets(value) for value in obj]
    if isinstance(obj, str):
        return _BEARER_RE.sub("Bearer [REDACTED]", _SK_RE.sub("sk-[REDACTED]", obj))
    return obj


def assert_no_secret(text: str) -> None:
    """落盘前最后一道检查：dump 文本里不允许出现 sk- 形态串或已知 key 的字面值。"""
    if _SK_RE.search(text):
        raise RuntimeError("trace dump 中检测到 sk- 形态字符串，拒绝落盘")
    real_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if real_key and real_key in text:
        raise RuntimeError("trace dump 中检测到 DEEPSEEK_API_KEY 字面值，拒绝落盘")


# ---------------------------------------------------------------------------
# mock 模型端点：脚本化 OpenAI 兼容 server（无 key、无外网）
# ---------------------------------------------------------------------------


def _scripted_reply(body: dict) -> dict:
    """按请求内容回放一个确定性的 assistant 回复（OpenAI chat.completion JSON）。

    策略（刻意保持无状态，只看请求本身）：
      1. 最后一条消息是 tool 结果 -> 收尾：纯文本"done"，finish_reason=stop。
      2. 否则看请求里 harness 声明的工具集（body["tools"]）：
         - 有 bash 且任务提到 hello.txt -> 调 bash 写文件；
         - 有 edit 且任务提到 a.py     -> 调 edit 把 def foo( 换成 def bar(；
         - 没有可用工具（null harness）-> 只能口头描述，直接结束。
    这样 default harness 两题各走"工具调用 -> 工具结果 -> 收尾"两轮，
    null harness 一轮结束且 reward=0，正好压出工具归属边界。
    """
    messages = body.get("messages", [])
    tools = body.get("tools") or []
    tool_names = {
        t.get("function", {}).get("name")
        for t in tools
        if t.get("type", "function") == "function"
    }
    user_text = " ".join(
        str(m.get("content", "")) for m in messages if m.get("role") == "user"
    )
    last_role = messages[-1].get("role") if messages else None

    content: str | None
    tool_calls: list[dict] | None = None
    if last_role == "tool":
        content = "Done. The requested file change has been made and verified."
    elif "hello.txt" in user_text and "bash" in tool_names:
        content = None
        tool_calls = [
            {
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "function": {
                    "name": "bash",
                    # printf 不带结尾换行，精确等于要求内容；cat 回显用于"verify"语义。
                    "arguments": json.dumps(
                        {"command": "printf 'hello rh2' > hello.txt && cat hello.txt"}
                    ),
                },
            }
        ]
    elif "a.py" in user_text and "edit" in tool_names:
        content = None
        tool_calls = [
            {
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "function": {
                    "name": "edit",
                    "arguments": json.dumps(
                        {"path": "a.py", "old_str": "def foo(", "new_str": "def bar("}
                    ),
                },
            }
        ]
    elif "a.py" in user_text and "bash" in tool_names:
        # 兜底：edit 工具被禁时用 bash+python 做同样的单点替换（当前矩阵默认不走这支）。
        content = None
        tool_calls = [
            {
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "function": {
                    "name": "bash",
                    "arguments": json.dumps(
                        {
                            "command": (
                                "python3 - <<'EOF'\n"
                                "from pathlib import Path\n"
                                "p = Path('a.py')\n"
                                "p.write_text(p.read_text().replace('def foo(', 'def bar(', 1))\n"
                                "EOF"
                            )
                        }
                    ),
                },
            }
        ]
    else:
        # null harness：没有本地工具可用，模型只能口头交代 —— 这就是预期 reward=0 的路径。
        content = (
            "I have no file-system tools available in this chat, so I cannot "
            "actually create or edit files. If I had a shell I would run the "
            "appropriate command; as it stands, no file was changed."
        )

    message: dict = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    # usage 为合成值（mock 没有真实 tokenizer）；只用来验证字段通路，meta 里有声明。
    prompt_tokens = max(1, sum(len(str(m)) for m in messages) // 4)
    completion_tokens = 24
    return {
        "id": f"mock-cmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.get("model", "mock-model"),
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": "tool_calls" if tool_calls else "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


class _MockHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802 (http.server 命名约定)
        if not self.path.endswith("/chat/completions"):
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        payload = json.dumps(_scripted_reply(body)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):  # 静默访问日志
        return


@contextlib.contextmanager
def mock_model_server():
    """在随机空闲端口起 mock server，yield base_url（http://127.0.0.1:<port>/v1）。"""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _MockHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/v1"
    finally:
        server.shutdown()
        server.server_close()


# ---------------------------------------------------------------------------
# macOS docker 网络 shim（记录在 field_check.md 发现节）
# ---------------------------------------------------------------------------


def apply_mac_docker_shim() -> None:
    """verifiers DockerRuntime 假设 `--network host` 下容器可用 127.0.0.1 访问宿主
    （Linux 成立）。macOS Docker Desktop 上实测 127.0.0.1 不通、`host.docker.internal`
    可达宿主 loopback 端口。这里只在实验层 monkeypatch
    `verifiers.v1.rollout.reachable_url`：当消费方是 DockerRuntime 且服务在 HOST
    （即 per-rollout InterceptionServer）时，改用 host.docker.internal。
    不修改 reference/ 与 site-packages 的任何文件。"""
    import verifiers.v1.rollout as vf_rollout
    from verifiers.v1.runtimes import HOST
    from verifiers.v1.runtimes.docker import DockerRuntime

    if getattr(vf_rollout.reachable_url, "_rh2_mac_docker_shim", False):
        return
    original = vf_rollout.reachable_url

    @contextlib.asynccontextmanager
    async def patched(service, port, *, consumer=None, consumer_is_local=True):
        if service is HOST and isinstance(consumer, DockerRuntime):
            yield f"http://host.docker.internal:{port}"
            return
        async with original(
            service, port, consumer=consumer, consumer_is_local=consumer_is_local
        ) as url:
            yield url

    patched._rh2_mac_docker_shim = True
    vf_rollout.reachable_url = patched


# ---------------------------------------------------------------------------
# 单格 runner
# ---------------------------------------------------------------------------


async def run_cell(args, base_url: str, api_key_var: str, key_status: str) -> dict:
    from verifiers.v1.clients import RolloutContext, resolve_client
    from verifiers.v1.clients.config import EvalClientConfig
    from verifiers.v1.env import EnvConfig, Environment
    from verifiers.v1.types import SamplingConfig

    if args.runtime == "docker":
        runtime_cfg: dict = {"type": "docker", "image": args.image}
    else:
        runtime_cfg = {"type": "subprocess"}

    env_config = EnvConfig(
        taskset={"id": "toy-taskset"},
        harness={"id": args.harness, "runtime": runtime_cfg},
        max_turns=args.max_turns,
        # setup 放宽到 15 分钟：docker 分支每条 rollout 都是新容器，要现装 uv 并解析
        # harness 程序的 openai/mcp/httpx 依赖。
        timeout={"setup": 900, "rollout": 300, "finalize": 120, "scoring": 120},
    )
    env = Environment(env_config)
    tasks = env.taskset.load_tasks()

    client = resolve_client(EvalClientConfig(base_url=base_url, api_key_var=api_key_var))
    ctx = RolloutContext(
        model=args.model,
        client=client,
        sampling=SamplingConfig(temperature=0.0, max_tokens=2048),
    )

    records: list[dict] = []
    summaries: list[dict] = []
    try:
        # 顺序跑两题（n=1），日志可读且避免 docker/uv 并发抖动。
        # 不进入 env.serving()：无 shared tools/user sim，走 per-rollout interception。
        for task in tasks:
            episode = env.episode(task, ctx, n=1)
            traces = await episode.run()
            for trace in traces:
                records.append(trace.to_record())
                summaries.append(
                    {
                        "task_idx": task.idx,
                        "task_kind": task.kind,
                        "reward": trace.reward,
                        "rewards": dict(trace.rewards),
                        "num_turns": trace.num_turns,
                        "num_branches": trace.num_branches,
                        "stop_condition": trace.stop_condition,
                        "error_type": trace.error.type if trace.error else None,
                        "error_message_head": (
                            scrub_secrets(trace.error.message)[:200] if trace.error else None
                        ),
                        "num_input_tokens": trace.num_input_tokens,
                        "num_output_tokens": trace.num_output_tokens,
                    }
                )
    finally:
        await client.close()

    tag = args.tag or f"{args.harness}_{args.runtime}"
    dump = {
        "meta": {
            "stage": "rh2-s0-3-toy-loop",
            "verifiers_pin": "5885ab9c54152e707af2a11797aa52c3eb1752da",
            "harness": args.harness,
            "runtime": args.runtime,
            "docker_image": args.image if args.runtime == "docker" else None,
            "endpoint_mode": args.endpoint,
            "endpoint_base_url": base_url if args.endpoint == "mock" else DEEPSEEK_BASE_URL,
            "model": args.model,
            "max_turns": args.max_turns,
            "deepseek_key_status": key_status,
            "mac_docker_shim_applied": bool(
                args.runtime == "docker" and platform.system() == "Darwin"
            ),
            "usage_note": (
                "endpoint_mode=mock 时 usage 数字为合成值，仅验证字段通路；"
                "token_ids/mask/logprobs 为空是 EvalClient 文本中继模式的预期行为。"
            ),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "summaries": summaries,
        },
        "traces": records,
    }
    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    text = json.dumps(scrub_secrets(dump), ensure_ascii=False, indent=1)
    assert_no_secret(text)
    out_path = DUMP_DIR / f"{tag}.json"
    out_path.write_text(text)

    print(f"\n=== cell {tag} (endpoint={args.endpoint}) ===")
    for s in summaries:
        print(
            f"task{s['task_idx']}({s['task_kind']}): reward={s['reward']:.1f} "
            f"turns={s['num_turns']} branches={s['num_branches']} "
            f"stop={s['stop_condition']} error={s['error_type']}"
        )
    print(f"dump -> {out_path.relative_to(REPO_ROOT)}")
    return dump


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", choices=["default", "null"], required=True)
    parser.add_argument("--runtime", choices=["subprocess", "docker"], required=True)
    parser.add_argument("--endpoint", choices=["mock", "deepseek"], default="mock")
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--image", default="python:3.12-slim")
    parser.add_argument("--max-turns", type=int, default=6)
    parser.add_argument("--tag", default=None, help="dump 文件名（默认 <harness>_<runtime>）")
    args = parser.parse_args()

    key_status = load_deepseek_key()

    if args.runtime == "docker":
        # 预拉镜像，避免把 pull 时间算进 rollout setup 超时。
        subprocess.run(["docker", "pull", args.image], check=True, capture_output=True)
        if platform.system() == "Darwin":
            apply_mac_docker_shim()

    if args.endpoint == "deepseek":
        print(f"deepseek key status: {key_status}（key 内容不打印）")
        asyncio.run(run_cell(args, DEEPSEEK_BASE_URL, "DEEPSEEK_API_KEY", key_status))
    else:
        with mock_model_server() as base_url:
            asyncio.run(run_cell(args, base_url, "RH2_MOCK_API_KEY", key_status))


if __name__ == "__main__":
    main()
