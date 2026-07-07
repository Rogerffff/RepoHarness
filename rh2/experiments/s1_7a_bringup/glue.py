"""S1-7a 训练主链路胶水：slime custom_generate -> rh2 编排本体（真实接线）。

slime 启动参数指向本模块：

    --custom-generate-function-path s1_7a_bringup.glue.generate

进程内单例 `BringupService` 在**第一条 rollout 到来时**完成一次性启动
（与 slime 例程 `_AdapterService` 同层级；差别是本服务随后把编排本体挂到
`args.rh2_orchestrator`，rh2_custom_generate 只认这个显式挂点）：

1. tokenizer + renderer（renderers 库 `Qwen3RendererConfig` 显式配置，
   规避 U-G 本地路径静默回落 DefaultRenderer）；
2. **startup_checks 真实执行（A2/U-G/U-H）**：对真实 SGLang router 发一次
   带 tape flag 的 /generate 探针，renderer 断言 + top-p tape 断言全过才放行，
   evidence 落 startup_evidence.json；任一失败直接抛异常，训练循环起不来；
3. 起共享 AnthropicAdapter（aiohttp 线程），安装 capture wire（替换
   call_sglang_generate + 包装 record_turn，见 capture_wire.py）；
4. 冻结 8 题 -> RolloutTaskSpec 表（防漂移校验开启）；
5. GradingManager + GradingQueue（F5 默认并发 4 / 队列 8）；
6. RolloutOrchestrator（config.policy_version = 探针实测引擎 weight_version，
   假设 4 的真实事实源）。

评测模式：本 bring-up 不跑 eval（E10 主评测面语义已在库层与 mock 全绿，
7a 只验训练传输链）。

infra 注入（验收项"gate 拒绝路径真实触发一次"）：环境变量
`RH2_INJECT_INFRA_INSTANCE=<instance_id>` 时，该题的**第一条** rollout 的
评分 spec 被替换成产不出合法官方日志的 eval 脚本 -> 官方 parser 解析失败
-> GradingReport(failed_to_grade/test_log_parse_failed, reward=None) ->
gate clean_grading/reward_scope 维失败 -> GroupRepairSignal.degraded ->
样本以 abort 形状剔除。注入靠 artifact 目录下的 marker 文件保证恰好一次。
"""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import aiohttp

from repoharness2.adapters.slime.generate import (
    LeafFacts,
    RolloutOrchestrator,
    SlimeBindingConfig,
    rh2_custom_generate,
    rollout_task_from_bundle_pair,
    startup_checks,
)
from repoharness2.envpack import bundles
from repoharness2.grading.manager import (
    GradingManagerConfig,
    SWEGradingManager,
)
from repoharness2.grading.queue import GradingQueue, GradingQueueConfig

from s1_7a_bringup.capture_wire import CaptureRegistry, install_capture_wire
from s1_7a_bringup.docker_sandbox import DockerSandbox

# ---------------------------------------------------------------------------
# 环境旋钮（全部有默认值；训练脚本统一显式设置）
# ---------------------------------------------------------------------------

MODEL_ID = os.environ.get("RH2_MODEL_ID", "Qwen/Qwen3-4B")
EXPECTED_RENDERER = os.environ.get("RH2_EXPECTED_RENDERER", "Qwen3Renderer")
ADAPTER_BIND_HOST = os.environ.get("ADAPTER_BIND_HOST", "0.0.0.0")
ADAPTER_PORT = int(os.environ.get("ADAPTER_PORT", "18001"))
# rollout 容器（bridge 网络）反连宿主侧 adapter 的地址：默认 docker0 网关
ADAPTER_PUBLIC_HOST = os.environ.get("ADAPTER_PUBLIC_HOST", "172.17.0.1")
ARTIFACT_DIR = Path(os.environ.get("RH2_BRINGUP_ARTIFACT_DIR", "/root/bringup/artifacts"))
HARNESS_KIND = os.environ.get("RH2_BRINGUP_HARNESS", "claude_code")  # claude_code | simple
AGENT_TIME_BUDGET_SEC = int(os.environ.get("SWE_AGENT_TIME_BUDGET_SEC", "600"))
MAX_TURNS_PER_SID = int(os.environ.get("RH2_MAX_TURNS_PER_SID", "25"))
INJECT_INFRA_INSTANCE = os.environ.get("RH2_INJECT_INFRA_INSTANCE", "")
# MoE routing tape 期望（P3 预实验 J4 增补，见 preflight/8gpu_preflight_protocol.md
# J4 判据 2/3）：Qwen3-30B-A3B 等 MoE 模型置 "1"——启动探针与生产会话都请求
# return_routed_experts，startup_checks 按 MoE 口径断言 routing tape 在场。
# 默认 "0"，7a 的 Qwen3-4B dense 行为逐字不变（A2：dense 只是没有 routing）。
EXPECT_MOE_ROUTING = os.environ.get("RH2_EXPECT_MOE_ROUTING", "0") == "1"

_INJECTED_EVAL_SCRIPT = (
    "#!/bin/bash\n"
    "echo 'RH2_BRINGUP_INJECTED_INFRA_NOISE: this log has no official markers'\n"
)


# ---------------------------------------------------------------------------
# harness 驱动（真实 = slime ClaudeCodeHarness；降级 = 容器内最小 Anthropic 循环）
# ---------------------------------------------------------------------------


class ClaudeCodeDriver:
    """HarnessDriver 形状 -> slime ClaudeCodeHarness。

    安装偏离（记录进 bring-up 报告）：slime 例程的 install_cli 走
    Node22 + `npm install -g <主包 tgz>`，但 Claude Code 2.x 的 npm 主包是
    bootstrap（postinstall 再去 registry 拉平台二进制，沙箱内引入一次
    在线依赖）。这里改为直接上载 `@anthropic-ai/claude-code-linux-x64`
    平台包并解出**自包含原生二进制**（免 Node/npm、离线可装），随后
    write_config/launch_and_wait 原样走 slime ClaudeCodeHarness.run。
    """

    name = "claude_code"
    platform_tarball_env = "SLIME_AGENT_CC_PLATFORM_TARBALL"

    async def _install_native_cli(self, sb: DockerSandbox) -> None:
        tarball = os.environ[self.platform_tarball_env]
        await sb.write_file("/tmp/cc-platform.tgz", Path(tarball))
        await sb.exec(
            "set -e && mkdir -p /tmp/cc-extract && "
            "tar -xzf /tmp/cc-platform.tgz -C /tmp/cc-extract && "
            "install -m 0755 /tmp/cc-extract/package/claude /usr/local/bin/claude && "
            "/usr/local/bin/claude --version",
            user="root",
            timeout=180,
            check=True,
        )

    async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
        from slime.agent.harness import ClaudeCodeHarness

        sb = DockerSandbox(sandbox.container_name)
        await self._install_native_cli(sb)
        # 预建 agent 用户（与 slime ensure_agent_user 同一命令、宽超时）：
        # slime 侧写死 timeout=60s，django 官方镜像 /testbed 数万文件的
        # chown -R 在 overlay2 copy-up 下超时（run6 实测 8/8 django rollout
        # exit=124 全灭）。本命令幂等（id agent 短路），预跑成功后 slime
        # 内部那次变成 no-op。
        await sb.exec(
            f"id agent >/dev/null 2>&1 || useradd -m -s /bin/bash agent && "
            f"chown -R agent:agent /home/agent {workdir} && "
            f"git config --system --add safe.directory '*' && id agent",
            user="root",
            check=True,
            timeout=900,
        )
        return await ClaudeCodeHarness().run(
            sb,
            workdir=workdir,
            session_id=session_id,
            adapter_url=adapter_url,
            time_budget_sec=time_budget_sec,
            prompt=prompt,
        )


_SIMPLE_AGENT_PY = r'''
import json, os, subprocess, sys, urllib.request

ADAPTER = os.environ["RH2_ADAPTER_URL"]
SID = os.environ["RH2_SESSION_ID"]
WORKDIR = os.environ.get("RH2_WORKDIR", "/testbed")
MAX_TURNS = int(os.environ.get("RH2_SIMPLE_MAX_TURNS", "12"))
PROMPT_PATH = os.environ["RH2_PROMPT_PATH"]

TOOLS = [{
    "name": "bash",
    "description": "Run a bash command in the repository checkout and return stdout+stderr.",
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    },
}]

def post(messages):
    body = {
        "model": "slime-actor",
        "max_tokens": 1024,
        "messages": messages,
        "tools": TOOLS,
        "system": "You are a software engineer fixing a bug in the repo at " + WORKDIR + ".",
    }
    req = urllib.request.Request(
        ADAPTER + "/v1/messages",
        data=json.dumps(body).encode(),
        headers={
            "content-type": "application/json",
            "authorization": "Bearer " + SID,
            "x-api-key": SID,
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read().decode())

prompt = open(PROMPT_PATH).read()
messages = [{"role": "user", "content": prompt}]
for turn in range(MAX_TURNS):
    reply = post(messages)
    content = reply.get("content") or []
    messages.append({"role": "assistant", "content": content})
    tool_uses = [b for b in content if b.get("type") == "tool_use"]
    if reply.get("stop_reason") != "tool_use" or not tool_uses:
        break
    results = []
    for block in tool_uses:
        cmd = (block.get("input") or {}).get("command") or "true"
        proc = subprocess.run(
            ["bash", "-c", cmd], cwd=WORKDIR, capture_output=True, text=True, timeout=180
        )
        out = (proc.stdout + proc.stderr)[-4000:]
        results.append({
            "type": "tool_result",
            "tool_use_id": block["id"],
            "content": out or "(no output)",
        })
    messages.append({"role": "user", "content": results})
print("SIMPLE_AGENT_DONE turns=", turn + 1)
'''


class SimpleLoopDriver:
    """降级预案（风险预案条款）：容器内最小 Anthropic Messages 循环 + bash 工具。

    诚实标注：SlimeBindingConfig.harness_name 必须配 "mock_harness"——这不是
    Claude Code，transport 链路等价但 harness 行为面不同（deviation 上报）。
    """

    name = "mock_harness"

    async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
        sb = DockerSandbox(sandbox.container_name)
        await sb.write_file("/rh2/simple_agent.py", _SIMPLE_AGENT_PY)
        await sb.write_file("/rh2/prompt.txt", prompt)
        code, out, err = await sb.exec(
            "python3 /rh2/simple_agent.py || python /rh2/simple_agent.py",
            env={
                "RH2_ADAPTER_URL": adapter_url,
                "RH2_SESSION_ID": session_id,
                "RH2_WORKDIR": workdir,
                "RH2_PROMPT_PATH": "/rh2/prompt.txt",
            },
            timeout=time_budget_sec,
        )
        if code != 0:
            # 与 CC 语义一致：非零退出码原样上抛给编排层记录（不是异常）
            print(f"[rh2-simple-agent] exit={code} tail={err[-300:] or out[-300:]}")
        return code


# ---------------------------------------------------------------------------
# 服务单例
# ---------------------------------------------------------------------------


# 单例锁必须在 import 期创建（import 单线程）：懒创建有并发窗口——32 条
# rollout 同时首调 get() 时会各自 new Lock -> 多个 BringupService 实例 ->
# 多个 adapter 线程抢同一端口（run4 实测 "Exception in thread
# rh2-anthropic-adapter" 即此形态）。
_SERVICE_LOCK = asyncio.Lock()


class BringupService:
    _instance: "BringupService | None" = None

    def __init__(self, args: Any) -> None:
        from slime.agent.adapters import AnthropicAdapter
        from slime.agent.aiohttp_threaded import FilteredAccessLogger, run_app_in_thread
        from slime.utils.processing_utils import load_tokenizer

        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        self.registry = CaptureRegistry()
        self.tokenizer = load_tokenizer(args.hf_checkpoint, trust_remote_code=True)
        self.sglang_url = f"http://{args.sglang_router_ip}:{args.sglang_router_port}"
        self.max_context_len = int(getattr(args, "rollout_max_context_len", 0) or 0)

        # -- U-G：renderer 显式配置 + 类名断言（v2_renderer_report §4 的规避写法）
        from renderers import Qwen3RendererConfig, create_renderer

        self.renderer = create_renderer(self.tokenizer, config=Qwen3RendererConfig())

        # -- 共享 adapter（slime 现成组件）+ capture wire
        self.adapter = AnthropicAdapter(
            tokenizer=self.tokenizer,
            sglang_url=self.sglang_url,
            tool_parser=getattr(args, "sglang_tool_call_parser", None) or None,
            reasoning_parser=getattr(args, "sglang_reasoning_parser", None) or None,
            max_turns_per_sid=MAX_TURNS_PER_SID,
        )
        install_capture_wire(self.registry)
        self.app_handle = run_app_in_thread(
            self.adapter.app,
            host=ADAPTER_BIND_HOST,
            port=ADAPTER_PORT,
            thread_name="rh2-anthropic-adapter",
            runner_kwargs={
                "handler_cancellation": True,
                "access_log_class": FilteredAccessLogger,
            },
        )
        self.adapter_url = f"http://{ADAPTER_PUBLIC_HOST}:{self.app_handle.port}"

        # -- 任务面：冻结 8 题（防漂移校验开启）
        self.pairs = {pair.instance_id: pair for pair in bundles.load_bundle_pairs()}
        self.task_specs = {
            iid: rollout_task_from_bundle_pair(pair, time_budget_seconds=AGENT_TIME_BUDGET_SEC)
            for iid, pair in self.pairs.items()
        }

        # -- 评分面：manager + F5 队列（并发 4 / 队列 8 默认）
        eval_log_dir = ARTIFACT_DIR / "eval_logs"
        eval_log_dir.mkdir(parents=True, exist_ok=True)
        self.grading_manager = SWEGradingManager(
            GradingManagerConfig(eval_log_dir=eval_log_dir)
        )
        self.grading_queue = GradingQueue(self.grading_manager, GradingQueueConfig())
        self._queue_started = False

        # -- 事件流（假设核对 + 计时证据的落盘面）
        self.events_path = ARTIFACT_DIR / "bringup_events.jsonl"
        self.signals_path = ARTIFACT_DIR / "group_repair_signals.jsonl"
        self.inject_marker = ARTIFACT_DIR / "infra_injection_fired.marker"

        self.probe_evidence: dict[str, Any] | None = None
        self.policy_version: str = "step_0"
        self.orchestrator: RolloutOrchestrator | None = None
        self.started_monotonic = time.monotonic()

    # -- 一次性异步启动（探针必须在事件循环里发）---------------------------------

    async def async_start(self, args: Any) -> None:
        await self._run_startup_checks()
        await self.grading_queue.start()
        self._queue_started = True

        template_hash = "sha256:" + hashlib.sha256(
            (self.tokenizer.chat_template or "").encode()
        ).hexdigest()

        config = SlimeBindingConfig(
            model_name=MODEL_ID,
            backend_name="sglang",
            backend_version=f"sglang-{_sglang_version()}",
            renderer_cls_name=type(self.renderer).__name__,
            expected_renderer_cls_name=EXPECTED_RENDERER,
            tokenizer_name=MODEL_ID,
            template_hash=template_hash,
            adapter_url=self.adapter_url,
            serving_precision="bfloat16",
            harness_name="claude_code" if HARNESS_KIND == "claude_code" else "mock_harness",
            expect_moe_routing=EXPECT_MOE_ROUTING,  # dense 默认 False；30B MoE 由 RH2_EXPECT_MOE_ROUTING=1 打开
            policy_version=self.policy_version,
            max_context_len=self.max_context_len,
        )
        driver = ClaudeCodeDriver() if HARNESS_KIND == "claude_code" else SimpleLoopDriver()

        def repair_signal_sink(signal) -> None:
            with self.signals_path.open("a", encoding="utf-8") as fh:
                fh.write(signal.model_dump_json() + "\n")

        def bringup_leaf_facts(sid, samples, hook):
            """多叶链（FORK/compaction）也放行：候选回链 = 全部捕获轮，
            实际归属由 backfill 的 token 同一性匹配裁决（入训轮子集写回
            分支注释）。库层 default_leaf_facts 的单叶限制保持不变，这里是
            bring-up 面对真实 CC FORK（run6 实测 4/32）的显式选择。"""

            all_ids = tuple(record.record_id for record in hook.records)
            return [
                LeafFacts(branch_id=f"b{i}", capture_record_ids=all_ids)
                for i in range(len(samples))
            ]

        self.orchestrator = RolloutOrchestrator(
            config=config,
            task_resolver=self._resolve_task,
            adapter_factory=self._adapter_factory,
            harness_driver=driver,
            grading_submit=self._grading_submit,
            leaf_facts_fn=bringup_leaf_facts,
            repair_signal_sink=repair_signal_sink,
            backpressure_events_source=lambda: list(self.grading_queue.events),
            artifact_dir=ARTIFACT_DIR / "rollouts",
        )

    async def _run_startup_checks(self) -> None:
        """U-G renderer 断言 + U-H tape 探针。

        探针**走生产同一条 wire 路径**（capture_wire 替换后的
        call_sglang_generate + 真实 AnthropicAdapter 的 url/参数面），而不是
        手搓 HTTP 体——首日实测手搓探针被 router/引擎以 400 拒（体形状与
        生产路径分叉），改走同路径后探针失败即生产失败，证据同源。
        原始响应经 capture registry 的暂存槽取出（探针轮不 record_turn，
        不会污染任何轨迹）。
        """

        import types

        from slime.agent.adapters import common as slime_common
        from repoharness2.adapters.slime.generate import GenerationCaptureHook

        probe_messages = [{"role": "user", "content": "ping"}]
        # return_dict=False 必须显式：新版 transformers 该函数默认返回
        # BatchEncoding（dict），直接当 input_ids 用会把键名字符串发给引擎
        # （router 报 "did not match any variant of untagged enum InputIds"，
        # run5 实测）。
        ids = self.tokenizer.apply_chat_template(
            probe_messages, tokenize=True, add_generation_prompt=True, return_dict=False
        )
        if isinstance(ids, dict):  # 兼容仍返回 dict 的版本
            ids = ids["input_ids"]
        probe_sid = "rh2-startup-probe"
        probe_hook = GenerationCaptureHook(
            trajectory_id=probe_sid,
            model_name=MODEL_ID,
            backend_name="sglang",
            backend_version=f"sglang-{_sglang_version()}",
            renderer_cls_name=type(self.renderer).__name__,
            tokenizer_name=MODEL_ID,
            template_hash="sha256:" + "0" * 64,
        )
        self.registry.register(probe_sid, probe_hook)
        try:
            session = types.SimpleNamespace(
                sampling_defaults={
                    "temperature": 1.0,
                    "top_p": 0.95,
                    "max_new_tokens": 16,
                    "return_top_p_token_ids": True,
                    "return_routed_experts": EXPECT_MOE_ROUTING,
                },
                max_context_tokens=0,
            )
            await slime_common.call_sglang_generate(
                list(ids), session, {}, adapter=self.adapter, session_id=probe_sid
            )
            pending = self.registry.pending.get(probe_sid)
            if pending is None:
                raise RuntimeError("探针轮未进入 capture 暂存槽——capture wire 未接上（A4）。")
            data = pending.raw_response
            probe_params = pending.capture_params
        finally:
            self.registry.unregister(probe_sid)

        evidence = startup_checks(
            renderer=self.renderer,
            expected_renderer_cls_name=EXPECTED_RENDERER,
            probe_sampling_params=probe_params,  # 生产路径生效值（含两个 tape flag）
            probe_response=data,
            prompt_token_count=len(ids),
            expect_routing_tape=EXPECT_MOE_ROUTING,  # dense 默认不请求；MoE（J4）按口径断言
        )
        meta = data.get("meta_info") or {}
        if meta.get("weight_version") is not None:
            self.policy_version = str(meta["weight_version"])  # 假设 4：引擎实测事实源
        evidence["engine_weight_version"] = meta.get("weight_version")
        evidence["sglang_url"] = self.sglang_url
        evidence["adapter_url"] = self.adapter_url
        evidence["harness_kind"] = HARNESS_KIND
        self.probe_evidence = evidence
        (ARTIFACT_DIR / "startup_evidence.json").write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False)
        )

    # -- 编排可注入件 ----------------------------------------------------------

    def _resolve_task(self, sample: Any):
        metadata = getattr(sample, "metadata", None) or {}
        iid = metadata.get("instance_id") or getattr(sample, "label", None)
        if iid not in self.task_specs:
            raise ValueError(f"样本没有可识别的 instance_id（metadata/label 均未命中）: {iid!r}")
        return self.task_specs[iid]

    def _adapter_factory(self, hook, session_defaults):
        service = self

        class PerRolloutAdapter:
            """SessionAdapter 形状：共享 AnthropicAdapter + 按 sid 挂 capture hook。"""

            def open_session(self, sid, *, sampling_defaults=None, max_context_tokens=0):
                service.registry.register(sid, hook)
                service.adapter.open_session(
                    sid,
                    sampling_defaults=sampling_defaults,
                    max_context_tokens=max_context_tokens,
                )

            async def finish_session(
                self, sid, *, base_sample, reward=0.0, extra_metadata=None, wait_timeout=5.0
            ):
                try:
                    return await service.adapter.finish_session(
                        sid,
                        base_sample=base_sample,
                        reward=reward,
                        extra_metadata=extra_metadata,
                        wait_timeout=wait_timeout,
                    )
                finally:
                    # weight_versions 证据在 finish 后仍需要（events 记录），
                    # 注销推迟到 drop_session（编排 finally 必经）。
                    pass

            async def drop_session(self, sid, *, wait_timeout=5.0):
                try:
                    await service.adapter.drop_session(sid, wait_timeout=wait_timeout)
                finally:
                    service.registry.unregister(sid)

        return PerRolloutAdapter()

    async def _grading_submit(self, *, trajectory_id, workspace, spec):
        if INJECT_INFRA_INSTANCE and spec.task_id == INJECT_INFRA_INSTANCE:
            fired = False
            try:  # marker 文件 O_EXCL 原子创建 = 恰好注入一次
                fd = os.open(self.inject_marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w") as fh:
                    fh.write(trajectory_id + "\n")
                fired = True
            except FileExistsError:
                fired = False
            if fired:
                spec = dataclasses.replace(spec, eval_script=_INJECTED_EVAL_SCRIPT)
        return await self.grading_queue.submit(
            trajectory_id=trajectory_id, workspace=workspace, spec=spec
        )

    # -- 事件记录 --------------------------------------------------------------

    def record_event(self, *, args: Any, sample: Any, result: list, wall_seconds: float) -> None:
        sid = getattr(sample, "session_id", None)
        audit = None
        if self.orchestrator is not None:
            for candidate in reversed(self.orchestrator.audits):
                if candidate.trajectory_id == sid:
                    audit = candidate
                    break
        finalized = audit.finalized if audit else None
        grading = finalized.grading_report if finalized else None
        event = {
            "ts": time.time(),
            "session_id": sid,
            "index": getattr(sample, "index", None),
            "group_index": getattr(sample, "group_index", None),  # 假设 10 实测核对
            "instance_id": (getattr(sample, "metadata", None) or {}).get("instance_id"),
            "wall_seconds": round(wall_seconds, 2),
            "returned_samples": len(result),
            "statuses": [str(getattr(s, "status", None)) for s in result],
            "remove_sample": [bool(getattr(s, "remove_sample", False)) for s in result],
            "abort_reason": [
                (getattr(s, "metadata", None) or {}).get("abort_reason") for s in result
            ],
            "response_lengths": [getattr(s, "response_length", None) for s in result],
            "loss_mask_ones": [
                sum(getattr(s, "loss_mask", None) or []) for s in result
            ],
            "truncated_meta": [
                (getattr(s, "metadata", None) or {}).get("truncated") for s in result
            ],  # 假设 6
            "weight_versions_engine": self.registry.weight_versions.get(sid, []),  # 假设 4
            "weight_versions_sample": [
                list(getattr(s, "weight_versions", None) or []) for s in result
            ],
            "rewards": [getattr(s, "reward", None) for s in result],
            "top_p_offsets_len": [
                len(getattr(s, "rollout_top_p_token_offsets", None) or []) for s in result
            ],
            "capture_stats": dict(self.registry.stats),
            "audit_steps": list(audit.steps) if audit else None,
            "harness_exit_code": audit.harness_exit_code if audit else None,
            "failure_records": (
                [
                    {"stage": f.stage, "error_type": f.error_type, "detail": f.detail[:200]}
                    for f in audit.failure_records
                ]
                if audit
                else None
            ),
            "cleanup_failures": (
                [f"{c.step}:{c.detail[:120]}" for c in audit.cleanup_failures] if audit else None
            ),
            "grading": (
                {
                    "outcome": grading.outcome,
                    "failure_category": grading.failure_category,
                    "reward": grading.reward,
                    "timings": json.loads(grading.timings.model_dump_json())
                    if grading.timings
                    else None,
                }
                if grading
                else None
            ),
            "eligibility_class": (
                finalized.eligibility_report.eligibility_class if finalized else None
            ),
            "degraded": (
                finalized.group_repair_signal.degraded if finalized else None
            ),
        }
        with self.events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

    # -- 单例接口 --------------------------------------------------------------

    @classmethod
    async def get(cls, args: Any) -> "BringupService":
        async with _SERVICE_LOCK:
            if cls._instance is None:
                service = BringupService(args)
                await service.async_start(args)
                cls._instance = service
            return cls._instance


def _sglang_version() -> str:
    try:
        import sglang

        return str(sglang.__version__)
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# slime custom_generate 入口
# ---------------------------------------------------------------------------


async def generate(args: Any, sample: Any, sampling_params: dict, evaluation: bool = False):
    service = await BringupService.get(args)
    if getattr(args, "rh2_orchestrator", None) is None:
        args.rh2_orchestrator = service.orchestrator
    started = time.monotonic()
    result = await rh2_custom_generate(args, sample, dict(sampling_params), evaluation=evaluation)
    try:
        service.record_event(
            args=args, sample=sample, result=result, wall_seconds=time.monotonic() - started
        )
    except Exception as exc:  # noqa: BLE001 - 证据记录不许伤主链路
        print(f"[rh2-bringup] record_event failed: {type(exc).__name__}: {exc}")
    return result
