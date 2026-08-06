"""S1-6 slime 绑定编排胶水单测（mock 全链，真实 GPU 验收留 S1-7a）。

mock 纪律：可注入替身全部打 slime 真实接口形状——
- MockClaudeCodeDriver = BaseHarness.run 关键字签名（workdir/session_id/
  adapter_url/time_budget_sec/prompt，见 reference/slime/slime/agent/harness/common.py）；
- MockSessionAdapter = BaseAdapter 的 open_session/finish_session/drop_session；
- mock SGLang 响应 = {"meta_info": {"id", "finish_reason": {"type"},
  "output_token_logprobs": [[logprob, token_id, None], ...], "top_p_token_ids"(b64),
  "top_p_token_offsets"(b64), "routed_experts"(b64)}}（S1-0 探针 wire 形态）。

只有 harness / adapter / SGLang / docker / 评分提交是替身；capture 钩子、
回填、project_from_slime、finalize_rollout（grade→project→scan→gate）、
A5 契约实例全部走真实代码。
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from fixtures.common import FixtureSlimeSample, b64_int32, routing_flat, topp_offsets

from repoharness2.adapters.slime import (
    LIFECYCLE_STEPS,
    GenerationCaptureHook,
    RolloutOrchestrator,
    RolloutTaskSpec,
    SlimeBindingConfig,
    SlimeBindingError,
    SlimeProjectionError,
    StartupCheckError,
    backfill_leaf_sample,
    rh2_custom_generate,
    rollout_task_from_bundle_pair,
    startup_checks,
)
from repoharness2.adapters.slime.generate import (
    TurnTape,
    detect_context_shrink,
    CLAUDE_CODE_TRAINING_GUARD_ENVS,
    assert_adapter_status_not_404,
    ensure_claude_code_training_guards,
)
from repoharness2.contracts import BundleMount, GradingReport
from repoharness2.envpack import bundles
from repoharness2.grading.manager import ExecResult, GradingEnvSpec, HygieneRules

BASE_COMMIT = "a" * 40
SHA_TEMPLATE = "sha256:" + "a" * 64
SHA_BUNDLE = "sha256:" + "e" * 64
TS = "2026-07-07T09:30:25Z"


def _routing_shape(value: Any) -> tuple[int, int, int]:
    if hasattr(value, "shape"):
        return tuple(int(dim) for dim in value.shape)
    return (len(value), len(value[0]), len(value[0][0]))


# ---------------------------------------------------------------------------
# 替身：docker / harness / adapter / SGLang 响应 / 评分提交
# ---------------------------------------------------------------------------


@dataclass
class FakeRolloutDocker:
    """rollout 容器通道替身（与 tests/grading 的 FakeDocker 同风格）。"""

    base_commit: str = BASE_COMMIT
    run_fail: bool = False
    rm_fail: bool = False
    # 镜像 RepoDigests 罐头值（codex#1 运行期比对；json 序列化后返回）。
    repo_digests: tuple[str, ...] = ()
    calls: list[tuple[str, ...]] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    writes: dict[str, bytes] = field(default_factory=dict)  # 容器内路径 -> 写入内容

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        self.calls.append(args)
        cmd = args[0]
        if cmd == "image":  # image inspect -f {{.Id}}|{{json .RepoDigests}} <image>
            if "RepoDigests" in " ".join(args):
                import json as _json

                return ExecResult(0, _json.dumps(list(self.repo_digests)) + "\n", "")
            return ExecResult(0, "sha256:" + "ab" * 32 + "\n", "")
        if cmd == "inspect":  # inspect -f {{.Image}} <container>（codex#1 比对入口）
            assert "{{.Image}}" in args, f"FakeRolloutDocker 不认识的 inspect: {args}"
            return ExecResult(0, "sha256:" + "ab" * 32 + "\n", "")
        if cmd == "run":
            if self.run_fail:
                return ExecResult(1, "", "cannot start container (fake)")
            return ExecResult(0, "f00dfeedcafe\n", "")
        if cmd == "rm":
            name = args[-1]
            if self.rm_fail:
                return ExecResult(1, "", f"cannot remove {name}: fake failure")
            self.removed.append(name)
            return ExecResult(0, "", "")
        if cmd == "exec":
            script = args[-1]
            if "rev-parse HEAD" in script:
                probe = (
                    f"HEAD={self.base_commit}\n"
                    "BASE_OBJECT_OK\n"
                    "PARENT=none\n"
                    "DIFFSTAT=\n"
                )
                return ExecResult(0, probe, "")
            if "cat > " in script:
                path = script.rsplit("cat > ", 1)[1].strip()
                self.writes[path] = input_bytes or b""
                return ExecResult(0, "", "")
            return ExecResult(0, "", "")
        raise AssertionError(f"FakeRolloutDocker 不认识的命令: {args}")


def sglang_response(
    *,
    rid: str,
    output_ids: list[int],
    finish: str = "stop",
    top_p_ids: list[int] | None = None,
    top_p_offsets: list[int] | None = None,
    routed_flat: list[int] | None = None,
    weight_version: str | None = None,
) -> dict[str, Any]:
    """SGLang /generate 响应替身（meta_info 字段名与 S1-0 探针 wire 形态一致）。"""

    meta: dict[str, Any] = {
        "id": rid,
        "finish_reason": {"type": finish},
        "output_token_logprobs": [
            [-(i + 1) * 0.05, token_id, None] for i, token_id in enumerate(output_ids)
        ],
        "prompt_tokens": 0,
        "completion_tokens": len(output_ids),
    }
    if weight_version is not None:
        meta["weight_version"] = weight_version
    if top_p_ids is not None:
        meta["top_p_token_ids"] = b64_int32(top_p_ids)
        meta["top_p_token_offsets"] = b64_int32(top_p_offsets or [])
    if routed_flat is not None:
        meta["routed_experts"] = b64_int32(routed_flat)
    return {"text": "<mock generation>", "meta_info": meta}


@dataclass
class MockTurn:
    prompt_ids: list[int]
    response: dict[str, Any]


class MockSessionAdapter:
    """slime BaseAdapter 接口形状的替身：turn 脚本驱动 capture 钩子 + 产叶链样本。"""

    def __init__(
        self,
        hook: GenerationCaptureHook,
        session_defaults: dict[str, Any],
        turns: list[MockTurn],
        leaf_samples: list[Any],
    ) -> None:
        self.hook = hook
        self.session_defaults = session_defaults
        self.turns = turns
        self.leaf_samples = leaf_samples
        self.opened: list[str] = []
        self.finished: list[str] = []
        self.dropped: list[str] = []

    def open_session(
        self, sid: str, *, sampling_defaults: dict | None = None, max_context_tokens: int = 0
    ) -> None:
        if sid in self.opened:  # 真实 BaseAdapter.open_session 的唯一性约束
            raise ValueError(f"session_id {sid!r} already exists")
        self.opened.append(sid)

    async def run_all_turns(self) -> None:
        """由 harness 替身调用：逐轮把 mock SGLang 响应喂给真实 capture 钩子。"""

        for turn in self.turns:
            self.hook.on_generate_response(
                prompt_token_ids=turn.prompt_ids,
                sampling_params=self.session_defaults,
                response=turn.response,
            )

    async def finish_session(
        self,
        sid: str,
        *,
        base_sample: Any,
        reward: float = 0.0,
        extra_metadata: dict | None = None,
        wait_timeout: float = 5.0,
    ) -> list[Any]:
        self.finished.append(sid)
        return list(self.leaf_samples)

    async def drop_session(self, sid: str, *, wait_timeout: float = 5.0) -> None:
        self.dropped.append(sid)


class MockClaudeCodeDriver:
    """slime BaseHarness.run 关键字签名的替身（真实实现 = ClaudeCodeHarness().run）。"""

    name = "mock_harness"

    def __init__(self, adapter_ref: dict[str, MockSessionAdapter], crash: Exception | None = None):
        self.adapter_ref = adapter_ref
        self.crash = crash
        self.calls: list[dict[str, Any]] = []

    async def run(
        self,
        sandbox: Any,
        *,
        workdir: str,
        session_id: str,
        adapter_url: str,
        time_budget_sec: int,
        prompt: str,
    ) -> int:
        self.calls.append(
            {
                "workdir": workdir,
                "session_id": session_id,
                "adapter_url": adapter_url,
                "time_budget_sec": time_budget_sec,
                "prompt": prompt,
            }
        )
        if self.crash is not None:
            raise self.crash
        await self.adapter_ref["adapter"].run_all_turns()
        return 0


def make_grading_report(trajectory_id: str, task_id: str, *, infra: bool = False) -> GradingReport:
    if infra:
        return GradingReport.model_validate(
            {
                "report_id": f"rpt_{trajectory_id}",
                "trajectory_id": trajectory_id,
                "task_id": task_id,
                "grader_name": "swebench_official_parser",
                "grader_version": "swebench-4.1.0",
                "outcome": "failed_to_grade",
                "failure_category": "infra_failure",
                "reward": None,
                "infra_failure_detail": "grading_container_killed_oom",
                "graded_at_utc": TS,
            }
        )
    return GradingReport.model_validate(
        {
            "report_id": f"rpt_{trajectory_id}",
            "trajectory_id": trajectory_id,
            "task_id": task_id,
            "grader_name": "swebench_official_parser",
            "grader_version": "swebench-4.1.0",
            "outcome": "resolved",
            "failure_category": None,
            "reward": 1.0,
            "f2p_pass_count": 1,
            "f2p_total_count": 1,
            "p2p_fail_count": 0,
            "p2p_total_count": 1,
            "patch_hygiene": {
                "cleaned_patch_digest": "sha256:" + "d" * 64,
                "replayed_on_clean_checkout": True,
                "test_files_modified": False,
                "forbidden_path_touched": False,
                "forbidden_paths": [],
                "verdict": "clean",
            },
            "graded_at_utc": TS,
        }
    )


@dataclass
class GradingSubmitStub:
    """GradingQueue.submit / SWEGradingManager.grade 同关键字形状的评分替身。"""

    infra: bool = False
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def __call__(self, *, trajectory_id: str, workspace: Any, spec: GradingEnvSpec, **kw):
        self.calls.append({"trajectory_id": trajectory_id, "workspace": workspace, "spec": spec})
        return make_grading_report(trajectory_id, spec.task_id, infra=self.infra)


# ---------------------------------------------------------------------------
# 链路装配（dense 两轮 / MoE 单轮探针形状）
# ---------------------------------------------------------------------------

TASK_ID_DENSE = "psf__requests-2931"
TASK_ID_MOE = "django__django-11099"


def make_task(task_id: str, *, image_manifest_digest: str | None = None) -> RolloutTaskSpec:
    """默认 image_local_build=True（fake 镜像无 RepoDigests）；
    传 image_manifest_digest 则改走运行期 RepoDigests 比对路径（codex#1 用例）。"""

    return RolloutTaskSpec(
        task_id=task_id,
        image="fake-image:v1",
        base_commit=BASE_COMMIT,
        prompt=f"Fix the issue in {task_id}",
        public_bundle_payload=b'{"instance_id": "%s"}' % task_id.encode(),
        public_bundle_digest=SHA_BUNDLE,
        image_manifest_digest=image_manifest_digest,
        image_local_build=image_manifest_digest is None,
        grading_spec=GradingEnvSpec(
            task_id=task_id,
            image="fake-image:v1",
            base_commit=BASE_COMMIT,
            image_local_build=True,
            eval_script="echo eval",
            parse_log=lambda text: (_ for _ in ()).throw(AssertionError("mock 不该调 parser")),
            grader_version="swebench-4.1.0",
            hygiene=HygieneRules(),
        ),
        time_budget_seconds=900,
    )


def dense_config(**overrides: Any) -> SlimeBindingConfig:
    defaults = dict(
        model_name="Qwen/Qwen3-4B",
        backend_version="0.5.9",
        renderer_cls_name="Qwen3Renderer",
        expected_renderer_cls_name="Qwen3Renderer",
        tokenizer_name="Qwen/Qwen3-4B",
        template_hash=SHA_TEMPLATE,
        adapter_url="http://10.0.0.1:18001",
        harness_name="mock_harness",
        expect_moe_routing=False,
        policy_version="step_0",
    )
    defaults.update(overrides)
    return SlimeBindingConfig(**defaults)


# dense 两轮：prompt 12 + 生成 10 + 工具 5 + 生成 8（dense_4b fixture 同形）。
D_PROMPT, D_GEN1, D_TOOL, D_GEN2 = 12, 10, 5, 8
D_TOKENS = (
    [1500 + i for i in range(D_PROMPT)]
    + [2500 + i for i in range(D_GEN1)]
    + [3500 + i for i in range(D_TOOL)]
    + [4500 + i for i in range(D_GEN2)]
)


def dense_turns() -> list[MockTurn]:
    gen1_ids = D_TOKENS[D_PROMPT : D_PROMPT + D_GEN1]
    gen2_ids = D_TOKENS[D_PROMPT + D_GEN1 + D_TOOL :]
    return [
        MockTurn(
            prompt_ids=D_TOKENS[:D_PROMPT],
            response=sglang_response(
                rid="rid_t0",
                output_ids=gen1_ids,
                finish="tool_calls",
                top_p_ids=list(range(120000, 120000 + 3 * D_GEN1)),
                top_p_offsets=topp_offsets([3] * D_GEN1),
            ),
        ),
        MockTurn(
            prompt_ids=D_TOKENS[: D_PROMPT + D_GEN1 + D_TOOL],
            response=sglang_response(
                rid="rid_t1",
                output_ids=gen2_ids,
                top_p_ids=list(range(121000, 121000 + 3 * D_GEN2)),
                top_p_offsets=topp_offsets([3] * D_GEN2),
            ),
        ),
    ]


def dense_leaf_sample() -> FixtureSlimeSample:
    """TrajectoryManager 叶链产物形状：**不带 tape / weight_versions**（S1-3 发现）。"""

    return FixtureSlimeSample(
        tokens=list(D_TOKENS),
        response_length=D_GEN1 + D_TOOL + D_GEN2,
        loss_mask=[1] * D_GEN1 + [0] * D_TOOL + [1] * D_GEN2,
        rollout_log_probs=(
            [-(i + 1) * 0.05 for i in range(D_GEN1)]
            + [0.0] * D_TOOL
            + [-(i + 1) * 0.05 for i in range(D_GEN2)]
        ),
        rollout_top_p_token_ids=None,
        rollout_top_p_token_offsets=None,
        rollout_routed_experts=None,
        weight_versions=[],
        rollout_id=3,
        index=0,
    )


@dataclass
class Chain:
    orchestrator: RolloutOrchestrator
    docker: FakeRolloutDocker
    driver: MockClaudeCodeDriver
    adapter_ref: dict[str, MockSessionAdapter]
    grading: GradingSubmitStub
    repair_signals: list[Any]
    base_sample: FixtureSlimeSample


def build_dense_chain(
    *,
    infra_grading: bool = False,
    crash: Exception | None = None,
    rm_fail: bool = False,
    mount_planner=None,
    artifact_dir=None,
    config: SlimeBindingConfig | None = None,
    turns: list[MockTurn] | None = None,
    leaf_samples: list[Any] | None = None,
    task: RolloutTaskSpec | None = None,
    docker: FakeRolloutDocker | None = None,
) -> Chain:
    docker = docker if docker is not None else FakeRolloutDocker(rm_fail=rm_fail)
    grading = GradingSubmitStub(infra=infra_grading)
    adapter_ref: dict[str, MockSessionAdapter] = {}
    repair_signals: list[Any] = []
    the_turns = turns if turns is not None else dense_turns()
    the_leaves = leaf_samples if leaf_samples is not None else [dense_leaf_sample()]

    def adapter_factory(hook: GenerationCaptureHook, session_defaults: dict[str, Any]):
        adapter = MockSessionAdapter(hook, session_defaults, the_turns, the_leaves)
        adapter_ref["adapter"] = adapter
        return adapter

    driver = MockClaudeCodeDriver(adapter_ref, crash=crash)
    orchestrator = RolloutOrchestrator(
        config=config or dense_config(),
        task_resolver=task if task is not None else make_task(TASK_ID_DENSE),
        adapter_factory=adapter_factory,
        harness_driver=driver,
        grading_submit=grading,
        docker=docker,
        repair_signal_sink=repair_signals.append,
        mount_planner=mount_planner,
        artifact_dir=artifact_dir,
    )
    base_sample = FixtureSlimeSample(index=0)
    return Chain(orchestrator, docker, driver, adapter_ref, grading, repair_signals, base_sample)


SAMPLING_PARAMS = {"temperature": 1.0, "top_p": 0.95, "max_new_tokens": 4096}


class _Args:
    """slime args 替身（custom_generate 只从上面取 rh2_orchestrator）。"""

    def __init__(self, orchestrator=None):
        if orchestrator is not None:
            self.rh2_orchestrator = orchestrator


# ---------------------------------------------------------------------------
# 正常路径：9 步顺序 + 交付 + A5 八问契约实例
# ---------------------------------------------------------------------------


async def test_normal_path_nine_step_order():
    chain = build_dense_chain()
    result = await rh2_custom_generate(
        _Args(chain.orchestrator), chain.base_sample, dict(SAMPLING_PARAMS)
    )
    audit = chain.orchestrator.audits[0]
    assert audit.steps == list(LIFECYCLE_STEPS)  # 9 步顺序逐一断言
    assert audit.failure_records == [] and audit.cleanup_failures == []

    # 交付：叶链样本原样返回，reward 回写评分值，metadata 只加两个白名单派生视图键
    assert len(result) == 1 and result[0] is chain.adapter_ref["adapter"].leaf_samples[0]
    leaf = result[0]
    assert leaf.reward == 1.0
    report = audit.finalized.eligibility_report
    assert leaf.metadata == {
        "eligibility_report_ref": report.report_id,
        "training_eligibility_class": "offline_or_sft_candidate",  # S1 封顶
    }
    # S1 封顶不算降级：七维全过 -> 可交付（S1-7a debug step 的样本来源）
    assert audit.finalized.group_repair_signal.degraded is False
    assert "s1_default_ceiling_offline" in report.reason_codes

    # 容器清理（Q7）：run 一次、rm 一次、租约记为已释放
    run_calls = [c for c in chain.docker.calls if c[0] == "run"]
    assert len(run_calls) == 1 and len(chain.docker.removed) == 1
    assert audit.lease_released is True
    # session 生命周期与 slime 例程一致：open -> finish -> drop（finally 必达）
    adapter = chain.adapter_ref["adapter"]
    assert adapter.opened == adapter.finished == adapter.dropped == [audit.trajectory_id]


async def test_normal_path_a5_eight_questions_as_schema_instances():
    chain = build_dense_chain()
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    lease, handle, launch = audit.lease, audit.workspace_handle, audit.launch_spec

    assert lease.created_by == "slime_adapter"  # Q1 谁建容器
    assert handle.materialized_by == "repoharness_envpack"  # Q2 谁物化 /testbed
    assert handle.lineage_check == "head_equals_base" and handle.head_commit == BASE_COMMIT
    assert launch.workdir == "/testbed"  # Q3 workdir 显式传入
    driver_call = chain.driver.calls[0]
    assert driver_call["workdir"] == "/testbed"
    assert driver_call["time_budget_sec"] == 900

    proxy = launch.model_proxy  # Q4 模型代理注入
    assert proxy.inject_env_var == "ANTHROPIC_BASE_URL"
    assert proxy.wire_protocol == "anthropic_messages"
    assert proxy.session_id == audit.trajectory_id == driver_call["session_id"]
    assert driver_call["adapter_url"] == proxy.base_url == "http://10.0.0.1:18001"

    assert lease.network_policy_owner == "slime_adapter"  # Q5 网络/权限策略归属
    assert lease.permission_policy_owner == "slime_adapter"
    assert lease.network_policy == "allowlist"
    assert lease.network_allowlist_justification is not None

    kinds = [m.bundle_kind for m in handle.mounted_bundles]  # Q6 bundle 挂载
    assert kinds == ["public_task_bundle"]
    assert chain.docker.writes["/rh2/public_task_bundle.json"].startswith(b'{"instance_id"')
    assert "/root/.rh2_bash_env" in chain.docker.writes  # envpack 的 agent 环境注入

    assert lease.cleanup.owner == "slime_adapter"  # Q7 清理责任
    assert "remove_container" in lease.cleanup.steps
    assert (  # Q8 清理失败的处置策略（schema 上没有"不留痕"选项）
        lease.cleanup.on_cleanup_failure == "record_runtime_finding_and_infra_failure"
    )

    # 评分复用同一 workspace 通道（rollout 容器 docker exec 形态，S1-4 同签名）
    grading_call = chain.grading.calls[0]
    assert grading_call["workspace"].container_name == lease.container_id
    assert grading_call["trajectory_id"] == audit.trajectory_id


async def test_normal_path_backfill_feeds_real_projection():
    """按轮回填（S1-3 发现的落点）：叶链无 tape，回填后真实投影全绿。"""

    chain = build_dense_chain()
    result = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    leaf = result[0]
    # 回填后的 slime 字段（合并 + 零宽 pad 语义）：offsets 长 = response 23 + 1
    assert len(leaf.rollout_top_p_token_offsets) == 24
    assert leaf.rollout_top_p_token_offsets[-1] == 3 * (D_GEN1 + D_GEN2) == 54
    assert leaf.rollout_top_p_token_offsets[D_GEN1] == leaf.rollout_top_p_token_offsets[D_GEN1 + D_TOOL]
    assert leaf.weight_versions == ["step_0", "step_0"]  # 每轮一条 policy_version

    projection = chain.orchestrator.audits[0].finalized.projection
    (branch,) = projection.branches
    assert (branch.prompt_token_count, branch.response_token_count) == (12, 23)
    assert branch.sampling_mask.offsets_len == 24
    assert branch.sampling_mask.kept_token_count == 54
    assert branch.routing.alignment == "not_applicable_dense_model"  # dense 显式声明
    # 回链 = capture 钩子的两轮记录，按轮次序
    hook_records = chain.adapter_ref["adapter"].hook.records
    assert branch.capture_record_refs == [record.record_id for record in hook_records]
    assert [ref.rsplit("_t", 1)[1] for ref in branch.capture_record_refs] == ["0", "1"]


async def test_moe_probe_shape_routing_backfill():
    """MoE 单轮（uh_probe_result.json 形状 15/16）：routing 整段替换回填 + 投影对齐。"""

    prompt_ids = [1000 + i for i in range(15)]
    gen_ids = [2000 + i for i in range(16)]
    rows = 15 - 1 + 16  # 30（SGLang 对齐律）
    turns = [
        MockTurn(
            prompt_ids=prompt_ids,
            response=sglang_response(
                rid="rid_moe",
                output_ids=gen_ids,
                top_p_ids=list(range(100000, 100000 + 57)),
                top_p_offsets=topp_offsets([4] * 9 + [3] * 7),  # 长 17、末位 57
                routed_flat=routing_flat(rows, 48, 8),
            ),
        )
    ]
    leaf = FixtureSlimeSample(
        tokens=prompt_ids + gen_ids,
        response_length=16,
        loss_mask=[1] * 16,
        # 与 mock SGLang 响应的 output_token_logprobs 逐位同源（S1-9 F5 收口：
        # 真实链路里两者同读一份 meta_info，fixture 不许出现第二个数值源——
        # parity-core 首跑抓过 0.03125 vs 0.05 的不同源残留）。
        rollout_log_probs=[-(i + 1) * 0.05 for i in range(16)],
        rollout_top_p_token_ids=None,
        rollout_top_p_token_offsets=None,
        rollout_routed_experts=None,
        weight_versions=[],
        rollout_id=7,
        index=0,
    )
    config = dense_config(
        model_name="Qwen/Qwen3-30B-A3B",
        tokenizer_name="Qwen/Qwen3-30B-A3B",
        expect_moe_routing=True,
        moe_num_layers=48,
        moe_router_topk=8,
    )
    chain = build_dense_chain(config=config, turns=turns, leaf_samples=[leaf])
    result = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))

    assert _routing_shape(result[0].rollout_routed_experts) == (rows, 48, 8)
    projection = chain.orchestrator.audits[0].finalized.projection
    (branch,) = projection.branches
    assert branch.routing.alignment == "sglang_prompt_minus1_plus_gen"
    assert (branch.routing.num_rows, branch.routing.num_layers, branch.routing.router_topk) == (30, 48, 8)
    assert branch.sampling_mask.offsets_len == 17
    assert chain.orchestrator.audits[0].steps == list(LIFECYCLE_STEPS)


def test_moe_routing_backfill_trims_extra_prefix_rows():
    """实机 J4 mini 形态：capture prompt 比叶链 prompt 多前缀行。

    routing tape 行序是 prompt-1 后接 generated；当叶链 prompt 少了一段前缀时，
    只能裁前缀、保留末尾 response 对齐行。少行仍由 backfill fail-closed。
    """

    capture_prompt = [1000 + i for i in range(15)]
    leaf_prompt = capture_prompt[2:]
    gen_ids = [2000 + i for i in range(16)]
    capture_rows = len(capture_prompt) - 1 + len(gen_ids)  # 30
    leaf_rows = len(leaf_prompt) - 1 + len(gen_ids)  # 28
    hook = GenerationCaptureHook(
        trajectory_id="traj_moe_trim",
        model_name="Qwen/Qwen3-30B-A3B",
        backend_name="sglang",
        backend_version="0.5.13",
        renderer_cls_name="Qwen3Renderer",
        tokenizer_name="Qwen/Qwen3-30B-A3B",
        template_hash=SHA_TEMPLATE,
    )
    hook.on_generate_response(
        prompt_token_ids=capture_prompt,
        sampling_params={
            **SAMPLING_PARAMS,
            "return_top_p_token_ids": True,
            "return_routed_experts": True,
        },
        response=sglang_response(
            rid="rid_moe_trim",
            output_ids=gen_ids,
            top_p_ids=list(range(100000, 100000 + 3 * len(gen_ids))),
            top_p_offsets=topp_offsets([3] * len(gen_ids)),
            routed_flat=routing_flat(capture_rows, 48, 8),
        ),
    )
    leaf = FixtureSlimeSample(
        tokens=leaf_prompt + gen_ids,
        response_length=len(gen_ids),
        loss_mask=[1] * len(gen_ids),
        rollout_log_probs=[-(i + 1) * 0.05 for i in range(len(gen_ids))],
        rollout_id=9,
        index=0,
    )

    used = backfill_leaf_sample(leaf, hook.tapes, moe_num_layers=48, moe_router_topk=8)

    assert [tape.record_id for tape in used] == [hook.tapes[0].record_id]
    assert _routing_shape(leaf.rollout_routed_experts) == (leaf_rows, 48, 8)
    assert leaf.metadata["rh2_routing_backfill_trimmed_prefix_rows"] == 2
    assert leaf.metadata["rh2_routing_backfill_actual_rows"] == capture_rows
    assert leaf.metadata["rh2_routing_backfill_expected_rows"] == leaf_rows


# ---------------------------------------------------------------------------
# 故障路径：harness 崩溃 / 私有 bundle / 降级 / 清理失败注入
# ---------------------------------------------------------------------------


async def test_harness_crash_cleanup_still_runs_and_failure_recorded():
    chain = build_dense_chain(crash=RuntimeError("claude cli exploded"))
    result = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]

    # 清理仍执行（Q7）：容器被 rm，drop_session 也走到
    assert len(chain.docker.removed) == 1 and audit.lease_released is True
    assert chain.adapter_ref["adapter"].dropped == [audit.trajectory_id]
    # FailureCategory 记录：rollout 级故障归 infra_failure
    (failure,) = audit.failure_records
    assert failure.stage == "harness_run"
    assert failure.failure_category == "infra_failure"
    assert "claude cli exploded" in failure.detail
    # 编排没有伪造后续步骤，返回 slime abort 形状
    assert "step3_harness_completed" not in audit.steps
    assert result[0].remove_sample is True and result[0].status == "aborted"
    assert result[0].metadata["abort_reason"].startswith("rh2_harness_run_failed")


async def test_private_bundle_mount_into_rollout_rejected():
    """A6/Q6：私有 bundle 出现在 rollout 挂载计划 -> schema 拒绝 -> abort + 清理。"""

    def bad_planner(task: RolloutTaskSpec) -> list[BundleMount]:
        return [
            BundleMount(
                bundle_kind="public_task_bundle",
                bundle_digest=task.public_bundle_digest,
                mount_path="/rh2/public_task_bundle.json",
            ),
            BundleMount(
                bundle_kind="private_grading_bundle",
                bundle_digest="sha256:" + "f" * 64,
                mount_path="/rh2/private.json",
            ),
        ]

    chain = build_dense_chain(mount_planner=bad_planner)
    result = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]

    (failure,) = audit.failure_records
    assert failure.stage == "materialize" and failure.error_type == "ValidationError"
    assert "private_grading_bundle" in failure.detail
    assert result[0].remove_sample is True  # 样本被剔除
    assert len(chain.docker.removed) == 1  # 容器已起就必须清（物化中途失败路径）
    assert "step2_workspace_materialized" not in audit.steps
    assert chain.grading.calls == []  # 根本走不到评分


async def test_gate_degraded_path_signal_forwarded_and_artifacts_written(tmp_path):
    """infra 评分 -> gate 降级：GroupRepairSignal 透传 + artifact 旁路落盘 + abort 剔除。"""

    chain = build_dense_chain(infra_grading=True, artifact_dir=tmp_path)
    result = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]

    # 组修复信号一等暴露且在返回前透传（P4：组装配前可见）
    (signal,) = chain.repair_signals
    assert signal.degraded is True
    assert signal.trajectory_id == audit.trajectory_id
    assert "reward_scope" in signal.failed_dimensions or "clean_grading" in signal.failed_dimensions
    assert audit.repair_signal_forwarded is True
    assert audit.steps[-1] == "step9_degraded_signal_forwarded"

    # 资格结论：infra 双维失败 -> audit 档（S1-5 地板）
    report = audit.finalized.eligibility_report
    assert report.eligibility_class == "audit_only_or_rejected"

    # artifact 旁路：sidecar 与 capture 记录都落盘（目录名 = trajectory_id 的净化截断形态）
    root = next(p for p in tmp_path.iterdir() if p.is_dir())
    for name in (
        "eligibility_report.json",
        "trajectory_projection.json",
        "grading_report.json",
        "group_repair_signal.json",
        "capture_records.json",
    ):
        assert (root / name).exists(), f"缺 sidecar {name}"
    assert list((root / "tapes").glob("*.bin"))  # 解码后的 tape 字节流

    # 样本以 slime abort 形状剔除，metadata 仍只带白名单派生视图键 + abort 事实
    aborted = result[0]
    assert aborted.remove_sample is True
    assert aborted.metadata["abort_reason"] == "rh2_gate_degraded"
    assert aborted.metadata["eligibility_report_ref"] == report.report_id
    assert aborted.metadata["training_eligibility_class"] == "audit_only_or_rejected"
    # top-p 训练配置（SAMPLING_PARAMS top_p=0.95）下剔除样本必须带零宽 tape：
    # slime _convert_samples_to_train_data 在 rollout_top_p!=1.0 时对每条样本
    # （含 remove_sample）断言双字段在场且 len(offsets)==response_length+1
    # （S1-7a 源码核对，差异假设 7 的修正）。
    assert aborted.rollout_top_p_token_ids == []
    assert aborted.rollout_top_p_token_offsets == [0, 0]
    assert len(aborted.rollout_top_p_token_offsets) == aborted.response_length + 1
    # 清理照常执行
    assert len(chain.docker.removed) == 1


async def test_abort_shape_keeps_stock_fields_when_top_p_is_one():
    """top_p=1.0 时 abort 形状必须与 slime 例程逐字段一致（不带 top-p 字段）：
    此时 slime 转换按 samples[0] 是否带字段分叉收集，混填会让 batch 收集崩。"""

    chain = build_dense_chain(infra_grading=True)
    params = {**SAMPLING_PARAMS, "top_p": 1.0}
    result = await chain.orchestrator.generate(_Args(), chain.base_sample, params)
    aborted = result[0]
    assert aborted.remove_sample is True
    assert getattr(aborted, "rollout_top_p_token_ids", None) is None
    assert getattr(aborted, "rollout_top_p_token_offsets", None) is None


async def test_cleanup_failure_injection_records_failure_category():
    """Q8：docker rm 失败 -> CleanupFailureRecord(infra_failure) 留痕，交付不受影响。"""

    chain = build_dense_chain(rm_fail=True)
    result = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]

    assert len(result) == 1 and result[0].reward == 1.0  # 正常交付
    (cleanup_failure,) = audit.cleanup_failures
    assert cleanup_failure.step == "remove_container"
    assert cleanup_failure.failure_category == "infra_failure"  # Q8 的 FailureCategory 落点
    assert cleanup_failure.lease_id == audit.lease.lease_id
    assert audit.lease_released is False  # 没删掉就不许记"已释放"
    assert audit.lease.cleanup.on_cleanup_failure == "record_runtime_finding_and_infra_failure"


# ---------------------------------------------------------------------------
# codex#1：运行期镜像 digest 比对（rollout 容器侧，S1-7a 前置修复）
# ---------------------------------------------------------------------------

FROZEN_IMG_DIGEST = "sha256:" + "1" * 64


async def test_rollout_image_digest_match_delivers():
    """正例：容器实际镜像的 RepoDigests 命中冻结 digest -> 正常交付，且比对确实发生。"""

    docker = FakeRolloutDocker(repo_digests=("docker.io/fake/img@" + FROZEN_IMG_DIGEST,))
    chain = build_dense_chain(
        task=make_task(TASK_ID_DENSE, image_manifest_digest=FROZEN_IMG_DIGEST), docker=docker
    )
    result = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert result[0].reward == 1.0
    assert chain.orchestrator.audits[0].failure_records == []
    joined = [" ".join(call) for call in docker.calls]
    assert any("{{.Image}}" in text for text in joined)  # 查的是容器实际镜像
    assert any("RepoDigests" in text for text in joined)  # 比对的是 RepoDigests 而非 image ID


async def test_rollout_image_digest_mismatch_aborts_and_cleans():
    """反例：RepoDigests 与冻结 digest 不符 -> materialize 阶段 infra_failure + 容器已清。"""

    docker = FakeRolloutDocker(repo_digests=("docker.io/fake/img@sha256:" + "2" * 64,))
    chain = build_dense_chain(
        task=make_task(TASK_ID_DENSE, image_manifest_digest=FROZEN_IMG_DIGEST), docker=docker
    )
    result = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    (failure,) = audit.failure_records
    assert failure.stage == "materialize"
    assert failure.failure_category == "infra_failure"
    assert "rollout_image_digest_mismatch" in failure.detail
    assert "digest 漂移" in failure.detail
    assert result[0].remove_sample is True
    assert len(docker.removed) == 1  # 容器已起必须清（Q7 物化中途失败路径）
    assert chain.grading.calls == []  # 漂移镜像上一步都不跑


async def test_rollout_image_without_repo_digests_and_no_marker_rejected():
    """反例（豁免必须显式）：镜像无 RepoDigests 且任务未声明 local_build -> 拒。"""

    docker = FakeRolloutDocker(repo_digests=())
    chain = build_dense_chain(
        task=make_task(TASK_ID_DENSE, image_manifest_digest=FROZEN_IMG_DIGEST), docker=docker
    )
    result = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    (failure,) = chain.orchestrator.audits[0].failure_records
    assert "rollout_image_digest_mismatch" in failure.detail
    assert "RepoDigests" in failure.detail and "local_build" in failure.detail
    assert result[0].remove_sample is True and len(docker.removed) == 1


async def test_rollout_local_build_exemption_is_explicit_and_skips_probe():
    """豁免路径：image_local_build=True 时不做 RepoDigests 查询，正常交付。"""

    chain = build_dense_chain()  # make_task 默认 image_local_build=True
    result = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert result[0].reward == 1.0
    joined = [" ".join(call) for call in chain.docker.calls]
    assert not any("RepoDigests" in text for text in joined)


def test_rollout_task_spec_digest_declaration_is_mandatory():
    """schema 层钉死：digest 与 local_build 二选一——两者都缺或都给，构造即拒。"""

    with pytest.raises(ValueError, match="二选一"):
        dataclasses.replace(make_task(TASK_ID_DENSE), image_local_build=False)  # 都缺
    with pytest.raises(ValueError, match="二选一"):
        dataclasses.replace(  # 都给
            make_task(TASK_ID_DENSE), image_manifest_digest=FROZEN_IMG_DIGEST
        )


# ---------------------------------------------------------------------------
# F3：golden_patch 永不进 rollout 容器（把代码路径事实钉成不变量）
# ---------------------------------------------------------------------------

GOLDEN_SENTINEL = "RH2_GOLDEN_PATCH_SENTINEL_9f3ae1"


def make_pair_with_golden_sentinel() -> "bundles.BundlePair":
    """真实 BundlePair（走生产构造与校验），private.golden_patch 植入唯一哨兵串。"""

    statement = "Fix the broken feature() function so it returns the right value."
    instance_id = "rh2-fixture.golden-0001"
    public = bundles.PublicTaskBundle(
        instance_id=instance_id,
        repo="psf/requests",
        base_commit=BASE_COMMIT,
        image="fake-image:v1",
        image_manifest_digest="sha256:" + "c" * 64,
        problem_statement=statement,
        problem_statement_sha256=bundles.sha256_of_text(statement),
    )
    private = bundles.PrivateGradingBundle(
        instance_id=instance_id,
        repo="psf/requests",
        version="2.3",
        base_commit=BASE_COMMIT,
        golden_patch=(
            "diff --git a/src/thing.py b/src/thing.py\n"
            "--- a/src/thing.py\n+++ b/src/thing.py\n"
            f"@@ -1 +1 @@\n-broken\n+{GOLDEN_SENTINEL}\n"
        ),
        test_patch=(
            "diff --git a/tests/test_thing.py b/tests/test_thing.py\n"
            "--- a/tests/test_thing.py\n+++ b/tests/test_thing.py\n@@ -1 +1 @@\n-# a\n+# b\n"
        ),
        fail_to_pass=["tests/test_thing.py::test_feature"],
        eval_script="echo eval",
        test_cmd="python tests/test_thing.py",
    )
    return bundles.BundlePair(public=public, private=private)


async def test_golden_patch_never_reaches_rollout_container_surfaces():
    """F3 不变量：真实取数通道（rollout_task_from_bundle_pair）构造任务并跑完整
    rollout 编排，rollout 容器的全部注入面——docker 调用参数（run 挂载/labels、
    exec 脚本）、容器内写入字节流、harness prompt、env 注入——找不到 golden_patch
    内容。链路必须正常走完（reward 回写），排除"因早退而未泄漏"的假阴性。"""

    pair = make_pair_with_golden_sentinel()
    assert GOLDEN_SENTINEL in pair.private.golden_patch  # 哨兵确实在场，测试不空转
    task = rollout_task_from_bundle_pair(pair, time_budget_seconds=900)
    docker = FakeRolloutDocker(
        repo_digests=("docker.io/fake/img@sha256:" + "c" * 64,)  # 与 public 冻结 digest 一致
    )
    chain = build_dense_chain(task=task, docker=docker)
    result = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert result[0].reward == 1.0

    for call in docker.calls:  # 挂载参数、exec 载荷、labels 全在这里
        assert GOLDEN_SENTINEL not in " ".join(call)
    for path, payload in docker.writes.items():  # 容器内全部写入字节
        assert GOLDEN_SENTINEL.encode() not in payload, f"泄漏进容器写入 {path}"
    assert GOLDEN_SENTINEL not in task.prompt
    assert GOLDEN_SENTINEL.encode() not in task.public_bundle_payload
    launch = chain.orchestrator.audits[0].launch_spec
    assert GOLDEN_SENTINEL not in " ".join(
        f"{key}={value}" for key, value in launch.env_injections.items()
    )


async def test_capture_hook_records_silent_downgrade_as_partial():
    """U-H 形态：请求了 top-p tape 但响应没带 -> capture 记录只能是 partial/not_checked，
    编排随后在投影层拒收（top_p_tape_requested_but_missing 语义链）——不静默成功。"""

    gen1_ids = D_TOKENS[D_PROMPT : D_PROMPT + D_GEN1]
    turns = [
        MockTurn(
            prompt_ids=D_TOKENS[:D_PROMPT],
            response=sglang_response(rid="rid_t0", output_ids=gen1_ids),  # 无 tape
        )
    ]
    leaf = dataclasses.replace(dense_leaf_sample(), loss_mask=[1] * D_GEN1 + [0] * (D_TOOL + D_GEN2))
    chain = build_dense_chain(turns=turns, leaf_samples=[leaf])
    result = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]

    # capture 层如实记 partial/not_checked（schema 禁止 complete）——U-H 的日常探测点
    (record,) = chain.adapter_ref["adapter"].hook.records
    assert record.capture_status == "partial"
    assert record.alignment_status == "not_checked"
    assert record.top_p_token_ids_ref is None
    # finalize 阶段整链 fail-closed：投影拒绝产出（reason_code 即机器可读降级标注）
    assert audit.finalized is None
    (failure,) = audit.failure_records
    assert failure.stage == "finalize"
    assert "top_p_tape_requested_but_missing" in failure.detail
    assert result[0].remove_sample is True
    assert len(chain.docker.removed) == 1  # 清理仍执行


# ---------------------------------------------------------------------------
# 启动期守门：U-G renderer 断言 + U-H tape 探针断言（startup_checks）
# ---------------------------------------------------------------------------

PROBE_SAMPLING = {
    "temperature": 1.0,
    "top_p": 0.95,
    "max_new_tokens": 16,
    "return_top_p_token_ids": True,
    "return_routed_experts": True,
}


def moe_probe_response() -> dict[str, Any]:
    """uh_probe_result.json 同形：prompt 15、生成 16、offsets 17、routing [30,48,8]。"""

    return sglang_response(
        rid="probe_rid",
        output_ids=list(range(3000, 3016)),
        top_p_ids=list(range(100000, 100057)),
        top_p_offsets=topp_offsets([4] * 9 + [3] * 7),
        routed_flat=routing_flat(30, 48, 8),
    )


class Qwen3Renderer:  # 类名即断言对象（U-G 按类名精确核对）
    pass


def test_startup_checks_pass_returns_evidence():
    evidence = startup_checks(
        renderer=Qwen3Renderer(),
        expected_renderer_cls_name="Qwen3Renderer",
        probe_sampling_params=PROBE_SAMPLING,
        probe_response=moe_probe_response(),
        prompt_token_count=15,
        expect_routing_tape=True,
        moe_num_layers=48,
        moe_router_topk=8,
    )
    assert evidence["renderer_cls_name"] == "Qwen3Renderer"
    assert evidence["generated_token_count"] == 16
    assert evidence["top_p_token_offsets_len"] == 17
    assert evidence["routed_experts_shape"] == [30, 48, 8]


def test_startup_checks_renderer_mismatch_fails():
    class DefaultRenderer:  # U-G 的静默降级形态
        pass

    with pytest.raises(SlimeProjectionError, match=r"^\[renderer_class_mismatch\]"):
        startup_checks(
            renderer=DefaultRenderer(),
            expected_renderer_cls_name="Qwen3Renderer",
            probe_sampling_params=PROBE_SAMPLING,
            probe_response=moe_probe_response(),
            prompt_token_count=15,
            expect_routing_tape=True,
        )


def test_startup_checks_missing_top_p_tape_fails_not_silent():
    response = moe_probe_response()
    del response["meta_info"]["top_p_token_ids"]
    del response["meta_info"]["top_p_token_offsets"]
    with pytest.raises(StartupCheckError, match=r"^\[top_p_tape_missing_in_probe\]"):
        startup_checks(
            renderer="Qwen3Renderer",
            expected_renderer_cls_name="Qwen3Renderer",
            probe_sampling_params=PROBE_SAMPLING,
            probe_response=response,
            prompt_token_count=15,
            expect_routing_tape=True,
        )


def test_startup_checks_missing_routing_tape_fails_not_silent():
    response = moe_probe_response()
    del response["meta_info"]["routed_experts"]
    with pytest.raises(StartupCheckError, match=r"^\[routing_tape_missing_in_probe\]"):
        startup_checks(
            renderer="Qwen3Renderer",
            expected_renderer_cls_name="Qwen3Renderer",
            probe_sampling_params=PROBE_SAMPLING,
            probe_response=response,
            prompt_token_count=15,
            expect_routing_tape=True,
            moe_num_layers=48,
            moe_router_topk=8,
        )


def test_startup_checks_dense_rejects_unexpected_routing():
    """U-J：dense 声明（expect_routing_tape=False）撞上 routing tape -> 配置错配即 fail。"""

    with pytest.raises(StartupCheckError, match=r"^\[unexpected_routing_tape_in_probe\]"):
        startup_checks(
            renderer="Qwen3Renderer",
            expected_renderer_cls_name="Qwen3Renderer",
            probe_sampling_params=PROBE_SAMPLING,
            probe_response=moe_probe_response(),
            prompt_token_count=15,
            expect_routing_tape=False,
        )


def test_startup_checks_offsets_len_mismatch_fails():
    response = moe_probe_response()
    response["meta_info"]["top_p_token_offsets"] = b64_int32(topp_offsets([4] * 9 + [3] * 6))
    with pytest.raises(StartupCheckError, match=r"^\[top_p_offsets_len_mismatch\]"):
        startup_checks(
            renderer="Qwen3Renderer",
            expected_renderer_cls_name="Qwen3Renderer",
            probe_sampling_params=PROBE_SAMPLING,
            probe_response=response,
            prompt_token_count=15,
            expect_routing_tape=True,
        )


# ---------------------------------------------------------------------------
# 回填与入口的独立单元
# ---------------------------------------------------------------------------


def test_backfill_rejects_turn_run_mismatch():
    leaf = dense_leaf_sample()
    hook = GenerationCaptureHook(
        trajectory_id="traj_x",
        model_name="m",
        backend_name="sglang",
        backend_version="0.5.9",
        renderer_cls_name="Qwen3Renderer",
        tokenizer_name="t",
        template_hash=SHA_TEMPLATE,
    )
    hook.on_generate_response(
        prompt_token_ids=D_TOKENS[:D_PROMPT],
        sampling_params={**SAMPLING_PARAMS, "return_top_p_token_ids": True, "return_routed_experts": False},
        response=sglang_response(
            rid="r0",
            output_ids=D_TOKENS[D_PROMPT : D_PROMPT + D_GEN1],
            top_p_ids=list(range(30)),
            top_p_offsets=topp_offsets([3] * D_GEN1),
        ),
    )
    # 叶链有两个 mask=1 段，但只回链一轮 -> 对不上就炸（fail-closed）
    with pytest.raises(SlimeBindingError, match=r"^\[capture_turns_vs_mask_runs_mismatch\]"):
        backfill_leaf_sample(leaf, hook.tapes)


def _mk_hook_with_turns(turn_outputs: list[list[int]], prompt: list[int]) -> GenerationCaptureHook:
    hook = GenerationCaptureHook(
        trajectory_id="traj_match",
        model_name="m",
        backend_name="sglang",
        backend_version="0.5.13",
        renderer_cls_name="Qwen3Renderer",
        tokenizer_name="t",
        template_hash=SHA_TEMPLATE,
    )
    for output_ids in turn_outputs:
        hook.on_generate_response(
            prompt_token_ids=prompt,
            sampling_params={
                **SAMPLING_PARAMS,
                "return_top_p_token_ids": True,
                "return_routed_experts": False,
            },
            response=sglang_response(
                rid=f"r{len(hook.records)}",
                output_ids=output_ids,
                top_p_ids=list(range(3 * len(output_ids))),
                top_p_offsets=topp_offsets([3] * len(output_ids)),
            ),
        )
    return hook


def test_backfill_token_anchored_turn_drop():
    """S1-7a 实机形态 1（REALIGN 整轮掉落，django-16139 实测 3 段 vs 4 轮）：
    掉落轮的 token 以 mask=0 上下文留在序列，token 锚定匹配须跳过该轮、
    只回链入训轮，top-p 合并只含入训轮的核集合。"""

    prompt = [1, 2, 3]
    t1, t_dropped, t2 = [11, 12], [21, 22, 23], [31, 32]
    # 序列 = prompt + t1(mask1) + dropped(mask0 上下文) + t2(mask1)
    leaf = FixtureSlimeSample(
        tokens=prompt + t1 + t_dropped + t2,
        response_length=len(t1) + len(t_dropped) + len(t2),
        loss_mask=[1] * len(t1) + [0] * len(t_dropped) + [1] * len(t2),
        rollout_log_probs=[-0.1] * 7,
        weight_versions=[],
        rollout_id=1,
        index=0,
    )
    hook = _mk_hook_with_turns([t1, t_dropped, t2], prompt)
    used = backfill_leaf_sample(leaf, hook.tapes, policy_version="wv1")
    assert [tape.record_id for tape in used] == [
        hook.tapes[0].record_id,
        hook.tapes[2].record_id,
    ]  # 掉落轮不入训
    # top-p 合并：入训 4 token（每 token 核 3）+ mask0 位置零宽 pad
    assert len(leaf.rollout_top_p_token_offsets) == leaf.response_length + 1
    assert leaf.rollout_top_p_token_offsets[-1] == 3 * 4
    assert leaf.weight_versions == ["wv1", "wv1"]


def test_backfill_token_anchored_tiling_two_turns_one_run():
    """S1-7a 实机形态 2（相邻轮无工具 token -> 两轮连成一个 mask=1 段）：
    平铺匹配按 token 逐位切开，两轮 tape 顺序拼接。"""

    prompt = [1, 2, 3]
    t1, t2 = [11, 12], [21, 22, 23]
    leaf = FixtureSlimeSample(
        tokens=prompt + t1 + t2,
        response_length=5,
        loss_mask=[1] * 5,  # 一个连续段覆盖两轮
        rollout_log_probs=[-0.1] * 5,
        weight_versions=[],
        rollout_id=1,
        index=0,
    )
    hook = _mk_hook_with_turns([t1, t2], prompt)
    used = backfill_leaf_sample(leaf, hook.tapes)
    assert len(used) == 2
    assert leaf.rollout_top_p_token_offsets == topp_offsets([3] * 5)


def test_backfill_token_anchored_rejects_unbacked_tokens():
    """mask=1 token 与任何捕获轮 token 都对不上 -> 当场炸（比旧版更严：逐位）。"""

    prompt = [1, 2, 3]
    leaf = FixtureSlimeSample(
        tokens=prompt + [99, 98],  # 与捕获轮 [11,12] 不同
        response_length=2,
        loss_mask=[1, 1],
        rollout_log_probs=[-0.1] * 2,
        weight_versions=[],
        rollout_id=1,
        index=0,
    )
    hook = _mk_hook_with_turns([[11, 12]], prompt)
    with pytest.raises(SlimeBindingError, match=r"^\[capture_turns_vs_mask_runs_mismatch\]"):
        backfill_leaf_sample(leaf, hook.tapes)


async def test_rh2_custom_generate_requires_orchestrator():
    with pytest.raises(SlimeBindingError, match=r"^\[orchestrator_not_configured\]"):
        await rh2_custom_generate(_Args(None), FixtureSlimeSample(), dict(SAMPLING_PARAMS))


async def test_multi_leaf_without_tree_facts_fails_closed():
    """fan-out 两叶链但没注入树侧事实提取器 -> 默认推导拒绝（不猜轮次归属）。"""

    chain = build_dense_chain(leaf_samples=[dense_leaf_sample(), dense_leaf_sample()])
    result = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    (failure,) = audit.failure_records
    assert failure.stage == "assemble"
    assert "leaf_facts_extractor_required" in failure.detail
    assert result[0].remove_sample is True
    assert len(chain.docker.removed) == 1


async def test_evaluation_mode_returns_eval_placeholder():
    """E10 主评测面 = 训练同链路 eval 模式：只消费 reward，样本按 slime eval 占位形状返回。"""

    chain = build_dense_chain()
    result = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS), evaluation=True
    )
    (placeholder,) = result
    assert placeholder is chain.base_sample
    assert placeholder.reward == 1.0 and placeholder.remove_sample is True
    assert placeholder.status == "completed"
    assert placeholder.metadata["training_eligibility_class"] == "offline_or_sft_candidate"
    # eval 同样走完整条治理链（评分/投影/gate 都有 evidence）
    assert chain.orchestrator.audits[0].finalized is not None


# ---------------------------------------------------------------------------
# 分离拓扑配置冒烟（preflight §8 H-3，S1-9）
# ---------------------------------------------------------------------------


async def test_disaggregated_topology_args_mock_smoke():
    """H-3：编排胶水在"分离放置 + train_async"形态的 args 下 mock 冒烟全绿。

    背景：S1-6/7a 此前只在 colocate 单卡 args 下验证过；S4 预实验 J4 要在
    分离拓扑（train_async，无 --colocate）复用同一编排胶水。本测试给 args
    挂上 slime 分离放置解析后会出现的字段（colocate=False、rollout_num_gpus、
    rollout_num_gpus_per_engine、actor/update-weight 参数），断言 9 步生命
    周期、交付与清理与 colocate mock 完全一致——编排只读 rh2_orchestrator，
    不对放置模式做任何隐藏假设（若未来有人误读 args.colocate 分支，
    此处的显式 False 会立即暴露行为差异）。
    """

    chain = build_dense_chain()
    args = _Args(chain.orchestrator)
    # slime train_async 分离放置解析后的关键字段（preflight §1.5 T3 形态）
    args.colocate = False
    args.actor_num_nodes = 1
    args.actor_num_gpus_per_node = 4
    args.rollout_num_gpus = 4
    args.rollout_num_gpus_per_engine = 2
    args.update_weights_interval = 1
    args.update_weight_mode = "full"
    args.update_weight_transport = "nccl"

    result = await rh2_custom_generate(args, chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.steps == list(LIFECYCLE_STEPS)  # 与 colocate mock 逐步一致
    assert audit.failure_records == [] and audit.cleanup_failures == []
    assert len(result) == 1 and result[0].reward == 1.0
    assert result[0].metadata["training_eligibility_class"] == "offline_or_sft_candidate"
    assert len(chain.docker.removed) == 1 and audit.lease_released is True
    # H-1 顺带核对：分离形态下 staleness 记账照常落在投影 handshake
    projection = audit.finalized.projection
    assert projection.handshake is not None
    assert set(projection.handshake.weight_versions) == {"step_0"}


def test_disaggregated_template_pins_train_async_form():
    """H-2 模板防漂移：container_train_disaggregated.sh 必须保持分离 + 双缓冲形态。

    钉住四个不变量：入口 train_async.py、无激活的 --colocate（train_async
    自身断言禁用）、显式 --rollout-num-gpus 分区、分离基线权重同步 full+nccl
    （preflight §1.6 / J3 附④）。7a 实跑的 container_train.sh 是历史证据，
    不在本断言范围。
    """

    template = (
        Path(__file__).resolve().parents[2]
        / "experiments"
        / "s1_7a_bringup"
        / "container_train_disaggregated.sh"
    )
    text = template.read_text(encoding="utf-8")
    assert "train_async.py" in text
    active_lines = [
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    ]
    assert not any("--colocate" in line for line in active_lines), (
        "分离模板出现激活的 --colocate：train_async 断言禁 colocate，模板漂移"
    )
    assert any("--rollout-num-gpus " in line or "--rollout-num-gpus\t" in line
               or line.strip().startswith("--rollout-num-gpus") for line in active_lines)
    assert "--update-weight-transport nccl" in text
    assert "--update-weights-interval 1" in text


# ---------------------------------------------------------------------------
# FA-0（05 计划）：真实 weight_version 管道 / 正式链断言 / D-FA-6 compaction 硬事实
# ---------------------------------------------------------------------------

import os as _os
import subprocess as _subprocess
import sys as _sys


def _mk_hook_with_versions(
    turn_outputs: list[list[int]], prompt: list[int], versions: list[str | None]
) -> GenerationCaptureHook:
    hook = GenerationCaptureHook(
        trajectory_id="traj_fa0",
        model_name="m",
        backend_name="sglang",
        backend_version="0.5.13",
        renderer_cls_name="Qwen3Renderer",
        tokenizer_name="t",
        template_hash=SHA_TEMPLATE,
    )
    for output_ids, version in zip(turn_outputs, versions):
        hook.on_generate_response(
            prompt_token_ids=prompt,
            sampling_params={
                **SAMPLING_PARAMS,
                "return_top_p_token_ids": True,
                "return_routed_experts": False,
            },
            response=sglang_response(
                rid=f"r{len(hook.records)}",
                output_ids=output_ids,
                top_p_ids=list(range(3 * len(output_ids))),
                top_p_offsets=topp_offsets([3] * len(output_ids)),
                weight_version=version,
            ),
        )
    return hook


def _two_run_leaf() -> tuple[FixtureSlimeSample, list[int], list[list[int]]]:
    """t1(mask1) + dropped(mask0) + t2(mask1) 的标准三轮形态（复用 S1-7a 形态 1）。"""

    prompt = [1, 2, 3]
    t1, t_dropped, t2 = [11, 12], [21, 22, 23], [31, 32]
    leaf = FixtureSlimeSample(
        tokens=prompt + t1 + t_dropped + t2,
        response_length=len(t1) + len(t_dropped) + len(t2),
        loss_mask=[1] * len(t1) + [0] * len(t_dropped) + [1] * len(t2),
        rollout_log_probs=[-0.1] * 7,
        weight_versions=[],
        rollout_id=1,
        index=0,
    )
    return leaf, prompt, [t1, t_dropped, t2]


def test_hook_captures_turn_weight_version():
    """meta_info.weight_version 原文透传进 TurnTape 与 capture 记录（FA-0.3）。"""

    hook = _mk_hook_with_versions([[11, 12]], [1, 2, 3], ["7"])
    assert hook.tapes[0].weight_version == "7"
    assert hook.records[0].weight_version == "7"
    hook2 = _mk_hook_with_versions([[11, 12]], [1, 2, 3], [None])
    assert hook2.tapes[0].weight_version is None
    assert hook2.records[0].weight_version is None


def test_backfill_per_turn_real_versions_beat_fallback():
    """逐入训轮真实版本优先；掉落轮的版本不进序列（每入训轮恰一条）。"""

    leaf, prompt, outputs = _two_run_leaf()
    hook = _mk_hook_with_versions(outputs, prompt, ["3", "999", "4"])  # 中间轮掉落
    used = backfill_leaf_sample(leaf, hook.tapes, policy_version="step_0")
    assert len(used) == 2
    assert leaf.weight_versions == ["3", "4"]  # 真实值胜过 policy_version 回退


def test_backfill_mixed_versions_fallback_per_turn():
    """个别轮缺真实版本 -> 该轮回退 policy_version，其余轮保留真实值（非正式链容忍）。"""

    leaf, prompt, outputs = _two_run_leaf()
    hook = _mk_hook_with_versions(outputs, prompt, ["3", None, None])
    used = backfill_leaf_sample(leaf, hook.tapes, policy_version="wv_fallback")
    assert len(used) == 2
    assert leaf.weight_versions == ["3", "wv_fallback"]


def test_backfill_no_version_facts_leaves_field_unset():
    """无真实版本且无回退值 -> 字段不写（无事实，gate policy_staleness 维收口）。"""

    leaf, prompt, outputs = _two_run_leaf()
    hook = _mk_hook_with_versions(outputs, prompt, [None, None, None])
    backfill_leaf_sample(leaf, hook.tapes, policy_version=None)
    assert leaf.weight_versions == []


def test_backfill_formal_chain_rejects_missing_turn_version():
    """正式链：入训轮缺 meta_info.weight_version -> fail-closed（不许配置值冒充）。"""

    leaf, prompt, outputs = _two_run_leaf()
    hook = _mk_hook_with_versions(outputs, prompt, ["3", "3", None])  # t2 是入训轮且缺版本
    with pytest.raises(SlimeBindingError, match="turn_weight_version_missing_in_formal_chain"):
        backfill_leaf_sample(
            leaf,
            hook.tapes,
            policy_version="5",
            require_real_weight_versions=True,
        )


def _dummy_orchestrator(config: SlimeBindingConfig) -> RolloutOrchestrator:
    return RolloutOrchestrator(
        config=config,
        task_resolver=make_task(TASK_ID_DENSE),
        adapter_factory=lambda hook, session_defaults: None,
        harness_driver=lambda **kwargs: None,
        grading_submit=lambda **kwargs: None,
    )


def _formal_config(**overrides: Any) -> SlimeBindingConfig:
    defaults = dict(
        require_real_weight_versions=True,
        policy_version="5",
        reject_context_shrink=True,
        reject_on_nonzero_harness_exit=True,  # codex 轮次 9 P0-3：正式链强制
    )
    defaults.update(overrides)
    return dense_config(**defaults)


def test_orchestrator_rejects_static_policy_version_in_formal_chain():
    """FA-0 验收负测试：require_real_weight_versions=True 时 step_0/None 启动即炸。"""

    with pytest.raises(StartupCheckError, match="static_policy_version_forbidden_in_formal_chain"):
        _dummy_orchestrator(_formal_config(policy_version="step_0"))
    with pytest.raises(StartupCheckError, match="static_policy_version_forbidden_in_formal_chain"):
        _dummy_orchestrator(_formal_config(policy_version=None))
    with pytest.raises(StartupCheckError, match="policy_version_not_numeric_in_formal_chain"):
        _dummy_orchestrator(_formal_config(policy_version="ckpt_a"))
    # 正式链必须同时开启收缩兜底（D-FA-6 是硬要求不是注释——codex FA-0 审查）
    with pytest.raises(StartupCheckError, match="context_shrink_rejection_disabled"):
        _dummy_orchestrator(_formal_config(reject_context_shrink=False))
    # 轮次 14 解耦回归：非零 exit 拒绝不再与正式链硬耦合（episode 时间
    # 预算耗尽 = slime EXIT_TIME_BUDGET_EXCEEDED=-1 是正常终止，硬耦合会
    # 确定性剔除长任务）——关闭旋钮的正式链配置必须能启动
    _dummy_orchestrator(_formal_config(reject_on_nonzero_harness_exit=False))
    # 数值版本 + 收缩兜底开启：通过
    _dummy_orchestrator(_formal_config())


def test_handshake_staleness_computed_in_formal_chain():
    """正式链握手：staleness = current - min(seen)，within 派生一致（FA-0.3）。"""

    orch = _dummy_orchestrator(_formal_config())
    leaf = FixtureSlimeSample(weight_versions=["3", "4"], index=0)
    handshake = orch._build_handshake("traj_hs", [leaf])
    assert handshake.staleness_steps == 2
    assert handshake.staleness_within_threshold is True
    # 超阈值：current=9, seen min=3 -> lag 6 > threshold 4
    orch2 = _dummy_orchestrator(_formal_config(policy_version="9"))
    handshake2 = orch2._build_handshake("traj_hs2", [leaf])
    assert handshake2.staleness_steps == 6
    assert handshake2.staleness_within_threshold is False
    # S1 兼容路径（flag=False）行为逐字不变：恒 0/True
    orch3 = _dummy_orchestrator(dense_config())
    handshake3 = orch3._build_handshake("traj_hs3", [leaf])
    assert handshake3.staleness_steps == 0
    assert handshake3.staleness_within_threshold is True


def test_handshake_rejects_seen_newer_than_current():
    """codex FA-0 反例：current=3、turn 版本 [5] -> 必须 fail-closed，
    不得 clamp 成 staleness=0 伪装健康。"""

    orch = _dummy_orchestrator(_formal_config(policy_version="3"))
    leaf = FixtureSlimeSample(weight_versions=["5"], index=0)
    with pytest.raises(SlimeBindingError, match="weight_version_ahead_of_current"):
        orch._build_handshake("traj_contradiction", [leaf])


def test_handshake_uses_current_version_provider_when_injected():
    """FA-1 接线点：provider 实测值优先于 config（finalize 时刻 current）。"""

    orch = RolloutOrchestrator(
        config=_formal_config(),
        task_resolver=make_task(TASK_ID_DENSE),
        adapter_factory=lambda hook, session_defaults: None,
        harness_driver=lambda **kwargs: None,
        grading_submit=lambda **kwargs: None,
        current_policy_version_provider=lambda: "7",
    )
    leaf = FixtureSlimeSample(weight_versions=["5", "6"], index=0)
    handshake = orch._build_handshake("traj_provider", [leaf])
    assert handshake.policy_version == "7"
    assert handshake.staleness_steps == 2  # 7 - min(5,6)


def _tape(turn_index: int, prompt_tokens: int) -> TurnTape:
    return TurnTape(
        record_id=f"cap_{turn_index}",
        turn_index=turn_index,
        prompt_token_count=prompt_tokens,
        response_token_count=1,
        output_ids=(1,),
        output_log_probs=(-0.1,),
        top_p_token_ids=None,
        top_p_token_offsets=None,
        routed_experts_flat=None,
    )


def test_detect_context_shrink_monotone_and_small_shrink_pass():
    """正常累积与 thinking 剥离级小幅缩短不误报（0.6 预注册比例）。"""

    assert detect_context_shrink([_tape(0, 10), _tape(1, 30), _tape(2, 60)]) == []
    # 25 >= 0.6 * 30：thinking 剥离量级，放行
    assert detect_context_shrink([_tape(0, 10), _tape(1, 30), _tape(2, 25)]) == []


def test_detect_context_shrink_flags_collapse():
    """prompt 大幅坍缩（compaction/Microcompact 机械信号）必须检出。"""

    reasons = detect_context_shrink([_tape(0, 10), _tape(1, 60), _tape(2, 20)])
    assert len(reasons) == 1 and "turn 2" in reasons[0]


def test_detect_context_shrink_ratio_must_be_valid():
    """ratio 域校验：0 关闭检测、>=1 误报等长 prompt——都拒绝（codex FA-0 审查）。"""

    tapes = [_tape(0, 10), _tape(1, 30)]
    for bad in (0.0, 1.0, 1.5, -0.2, float("inf"), float("nan")):
        with pytest.raises(SlimeBindingError, match="context_shrink_ratio_invalid"):
            detect_context_shrink(tapes, shrink_ratio=bad)


def test_detect_context_shrink_per_branch_spares_subagent():
    """codex FA-0 严重 2 的负测试：主 agent 长上下文后启动短上下文子 agent。

    CC 子 agent 与主 agent 共享 session id——session 级全量比较会误判；
    按叶链（lineage）分开检测时两条链各自单调，都不得报收缩。
    """

    main_chain = [_tape(0, 10), _tape(1, 40), _tape(2, 80)]
    sub_chain = [_tape(3, 6), _tape(4, 12)]  # 子 agent：全新短上下文，随后增长
    # 叶链级（编排层的硬拒绝口径）：各自干净
    assert detect_context_shrink(main_chain) == []
    assert detect_context_shrink(sub_chain) == []
    # session 级（audit-only 口径）：混排后必然报警——这正是它只能作审计信号的原因
    assert detect_context_shrink(main_chain + sub_chain) != []


async def test_context_shrink_rejects_trajectory_end_to_end():
    """D-FA-6 兜底端到端：叶链内 prompt 坍缩 + reject 开启 -> 轨迹收口为
    abort 形状（remove_sample=True，退出基线），audit 留痕。"""

    base = dense_turns()
    shrunk = [
        base[0],
        MockTurn(prompt_ids=[1, 2, 3, 4, 5], response=base[1].response),  # 5 < 0.6*12
    ]
    chain = build_dense_chain(config=dense_config(reject_context_shrink=True), turns=shrunk)
    result = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS)
    )
    assert result[0].remove_sample is True
    assert result[0].metadata["abort_reason"].startswith("rh2_assemble_failed")
    audit = chain.orchestrator.audits[-1]
    assert any("branch" in reason for reason in audit.context_shrink_reasons)
    assert any(
        "context_shrink_detected" in record.detail or "上下文收缩" in record.detail
        for record in audit.failure_records
    )


async def test_context_shrink_audit_only_when_reject_disabled():
    """reject 关闭（S1 兼容默认）：同样的收缩只记录 audit，不改变交付。"""

    base = dense_turns()
    shrunk = [
        base[0],
        MockTurn(prompt_ids=[1, 2, 3, 4, 5], response=base[1].response),
    ]
    chain = build_dense_chain(config=dense_config(), turns=shrunk)
    result = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS)
    )
    assert not getattr(result[0], "remove_sample", False)
    audit = chain.orchestrator.audits[-1]
    assert audit.context_shrink_reasons  # 信号仍留痕


def test_ensure_compaction_disabled_merges_and_fail_closed():
    """DISABLE_COMPACT 合并进 SLIME_AGENT_CC_EXTRA_ENVS；已有键保留；坏 JSON 拒绝。"""

    env: dict[str, str] = {}
    merged = ensure_claude_code_training_guards(env)
    # 四变量训练守卫全在（codex 轮次 8：源码引导验证）
    assert merged == dict(CLAUDE_CODE_TRAINING_GUARD_ENVS)
    assert merged["CLAUDE_CODE_MAX_RETRIES"] == "0"
    assert merged["CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK"] == "1"

    env2 = {"SLIME_AGENT_CC_EXTRA_ENVS": '{"FOO": "bar"}'}
    merged2 = ensure_claude_code_training_guards(env2)
    assert merged2["FOO"] == "bar" and merged2["DISABLE_COMPACT"] == "1"

    env3 = {"SLIME_AGENT_CC_EXTRA_ENVS": "[1, 2]"}
    with pytest.raises(SlimeBindingError, match="cc_extra_envs_not_object"):
        ensure_claude_code_training_guards(env3)

    # 冲突检测：用户不得覆盖正式防线
    env4 = {"SLIME_AGENT_CC_EXTRA_ENVS": '{"CLAUDE_CODE_MAX_RETRIES": "3"}'}
    with pytest.raises(SlimeBindingError, match="cc_training_guard_conflict"):
        ensure_claude_code_training_guards(env4)


def test_adapter_status_not_404_guard():
    """CC 2.1.205 对流式创建阶段 404 绕过 fallback 开关——adapter 不得返 404。"""

    assert assert_adapter_status_not_404(503) == 503
    with pytest.raises(SlimeBindingError, match="adapter_must_not_return_404"):
        assert_adapter_status_not_404(404)


def test_compaction_disabled_env_reaches_child_process():
    """FA-0 验收探针（本地冒烟替身）：子进程真实读到 DISABLE_COMPACT=1。

    真实 CC 子进程的验真挂 FA-5 短租（slime claude_code.py 合并逻辑同源）；
    本测试证明"env 准备 -> 子进程可见"这一段管道无泄漏。
    """

    env = dict(_os.environ)
    ensure_claude_code_training_guards(env)
    out = _subprocess.run(
        [
            _sys.executable,
            "-c",
            "import os, json; print(json.loads(os.environ['SLIME_AGENT_CC_EXTRA_ENVS'])['DISABLE_COMPACT'])",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert out.stdout.strip() == "1"


async def test_poison_actively_cancels_running_harness():
    import asyncio
    """codex 轮次 9 P0-4：poison 不再只是"harness 返回后复检"——proxy 判
    不可归因时**主动取消**运行中的 harness task（不等 CC 自退），收口为
    缺员 abort 形状，且订阅在结束后清理。"""

    from repoharness2.adapters.slime.async_worker import SessionPoisonRegistry

    registry = SessionPoisonRegistry()
    cancelled = {"seen": False}
    started = None  # 在事件循环内创建

    class HangingDriver:
        async def run(self, *args, **kwargs):
            started.set()  # 先宣告已运行，再投毒（消除"取消先于首次调度"竞态）
            try:
                await asyncio.Event().wait()  # 永不返回，只能被取消
            except asyncio.CancelledError:
                cancelled["seen"] = True
                raise

    adapter_ref: dict[str, MockSessionAdapter] = {}

    def adapter_factory(hook, session_defaults):
        adapter = MockSessionAdapter(hook, session_defaults, dense_turns(), [dense_leaf_sample()])
        adapter_ref["adapter"] = adapter
        return adapter

    docker = FakeRolloutDocker()
    orch = RolloutOrchestrator(
        config=dense_config(),
        task_resolver=make_task(TASK_ID_DENSE),
        adapter_factory=adapter_factory,
        harness_driver=HangingDriver(),
        grading_submit=GradingSubmitStub(),
        docker=docker,
        session_poison_check=registry.is_poisoned,
        session_poison_subscribe=registry.subscribe,
        session_poison_unsubscribe=registry.unsubscribe,
    )

    async def poison_when_subscribed():
        await started.wait()  # harness 真在运行中
        (sid,) = registry._subscribers
        registry.poison(sid, "unattributable_model_call")

    started = asyncio.Event()
    result, _ = await asyncio.gather(
        orch.generate(_Args(), FixtureSlimeSample(index=0), dict(SAMPLING_PARAMS)),
        poison_when_subscribed(),
    )
    assert cancelled["seen"] is True  # harness 被主动取消，不是自然退出
    aborted = result[0]
    assert aborted.remove_sample is True  # 缺员 abort 形状
    audit = orch.audits[0]
    (failure,) = audit.failure_records
    assert "session_poisoned_during_execution" in failure.detail
    assert registry._subscribers == {}  # 订阅已清理（有界）
    assert len(docker.removed) == 1  # sandbox 清理照常


async def test_poison_subscribe_after_poison_fires_immediately():
    """订阅时已中毒 -> 立即回调（竞态窗口收口：poison 先于 subscribe 到达）。"""

    from repoharness2.adapters.slime.async_worker import SessionPoisonRegistry

    registry = SessionPoisonRegistry()
    registry.poison("sid_X", "already_bad")
    fired: list[tuple[str, str]] = []
    registry.subscribe("sid_X", lambda sid, reason: fired.append((sid, reason)))
    assert fired == [("sid_X", "already_bad")]


async def test_finish_session_drain_precedes_boundary_check():
    """codex 轮次 14 仍需修正 5：drain 屏障（finish_session）必须先于交付账
    边界断言——顺序错了会 false reject（正常轮还在 flush）或 false accept
    （drain 期间才失败）。本测试录制真实调用顺序。"""

    order: list[str] = []
    adapter_ref: dict[str, MockSessionAdapter] = {}

    class OrderRecordingAdapter:
        """包装 MockSessionAdapter，录制 finish_session 时刻。"""

        def __init__(self, inner):
            self._inner = inner

        def open_session(self, *a, **k):
            return self._inner.open_session(*a, **k)

        async def finish_session(self, *a, **k):
            order.append("drain")
            return await self._inner.finish_session(*a, **k)

        async def drop_session(self, *a, **k):
            return await self._inner.drop_session(*a, **k)

    def adapter_factory(hook, session_defaults):
        inner = MockSessionAdapter(hook, session_defaults, dense_turns(), [dense_leaf_sample()])
        adapter_ref["adapter"] = inner
        return OrderRecordingAdapter(inner)

    def boundary_check(sid: str) -> None:
        order.append("boundary")

    orch = RolloutOrchestrator(
        config=dense_config(),
        task_resolver=make_task(TASK_ID_DENSE),
        adapter_factory=adapter_factory,
        harness_driver=MockClaudeCodeDriver(adapter_ref),
        grading_submit=GradingSubmitStub(),
        docker=FakeRolloutDocker(),
        capture_boundary_check=boundary_check,
    )
    result = await orch.generate(_Args(), FixtureSlimeSample(index=0), dict(SAMPLING_PARAMS))
    assert result[0].remove_sample is not True  # 正常交付
    assert order == ["drain", "boundary"]  # drain 屏障先行（轮次 13 P0-2 顺序）


async def test_audit_sink_failure_formal_chain_raises_fatal():
    """codex 轮次 14 仍需修正 3：正式链审计落盘失败必须是**基建级致命错误**
    （worker 据此停机），不是普通 execution 失败；bring-up 链只打印容忍。"""

    from repoharness2.adapters.slime.async_worker import (
        FatalExecutionInfrastructureError,
    )

    def broken_sink(audit) -> None:
        raise OSError("audit disk full")

    def build(config):
        adapter_ref: dict[str, MockSessionAdapter] = {}

        def adapter_factory(hook, session_defaults):
            adapter = MockSessionAdapter(
                hook, session_defaults, dense_turns(), [dense_leaf_sample()]
            )
            adapter_ref["adapter"] = adapter
            return adapter

        return RolloutOrchestrator(
            config=config,
            task_resolver=make_task(TASK_ID_DENSE),
            adapter_factory=adapter_factory,
            harness_driver=MockClaudeCodeDriver(adapter_ref),
            grading_submit=GradingSubmitStub(),
            docker=FakeRolloutDocker(),
            audit_sink=broken_sink,
        )

    # bring-up：容忍（正常返回）
    orch = build(dense_config())
    result = await orch.generate(_Args(), FixtureSlimeSample(index=0), dict(SAMPLING_PARAMS))
    assert result  # 未被审计失败打断

    # 正式链：FatalExecutionInfrastructureError 传播（worker 停机信号）
    orch2 = build(_formal_config())
    with pytest.raises(FatalExecutionInfrastructureError, match="execution_audit_write_failed"):
        await orch2.generate(_Args(), FixtureSlimeSample(index=0), dict(SAMPLING_PARAMS))


async def test_orchestrator_reads_paid_from_metadata_and_registers():
    """F2-1a：member metadata 的 rh2_physical_attempt_id → audit 字段 +
    经注入点登记 sid→paid（glue 接 registry.set_physical_attempt_id）；
    metadata 缺失时（S1 兼容路径）audit 为 None 且不调用登记点。"""

    registered: list[tuple[str, str]] = []
    chain = build_dense_chain()
    chain.orchestrator._physical_attempt_registrar = (
        lambda sid, paid: registered.append((sid, paid))
    )
    sample = FixtureSlimeSample(index=0)
    sample.metadata = dict(getattr(sample, "metadata", {}) or {})
    sample.metadata["rh2_physical_attempt_id"] = "exec_X#p1-abcd1234"
    await chain.orchestrator.generate(_Args(), sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.physical_attempt_id == "exec_X#p1-abcd1234"
    assert registered == [(audit.session_id, "exec_X#p1-abcd1234")]

    # S1 兼容：无 metadata 键 → None + 不登记
    registered.clear()
    chain2 = build_dense_chain()
    chain2.orchestrator._physical_attempt_registrar = (
        lambda sid, paid: registered.append((sid, paid))
    )
    await chain2.orchestrator.generate(_Args(), FixtureSlimeSample(index=1), dict(SAMPLING_PARAMS))
    assert chain2.orchestrator.audits[0].physical_attempt_id is None
    assert registered == []
