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
from typing import Any

import pytest
from fixtures.common import FixtureSlimeSample, b64_int32, routing_flat, topp_offsets

from repoharness2.adapters.slime import (
    LIFECYCLE_STEPS,
    GenerationCaptureHook,
    LeafFacts,
    RolloutOrchestrator,
    RolloutTaskSpec,
    SlimeBindingConfig,
    SlimeBindingError,
    SlimeProjectionError,
    StartupCheckError,
    backfill_leaf_sample,
    rh2_custom_generate,
    startup_checks,
)
from repoharness2.contracts import BundleMount, GradingReport
from repoharness2.grading.manager import ExecResult, GradingEnvSpec, HygieneRules

BASE_COMMIT = "a" * 40
SHA_TEMPLATE = "sha256:" + "a" * 64
SHA_BUNDLE = "sha256:" + "e" * 64
TS = "2026-07-07T09:30:25Z"

# ---------------------------------------------------------------------------
# 替身：docker / harness / adapter / SGLang 响应 / 评分提交
# ---------------------------------------------------------------------------


@dataclass
class FakeRolloutDocker:
    """rollout 容器通道替身（与 tests/grading 的 FakeDocker 同风格）。"""

    base_commit: str = BASE_COMMIT
    run_fail: bool = False
    rm_fail: bool = False
    calls: list[tuple[str, ...]] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    writes: dict[str, bytes] = field(default_factory=dict)  # 容器内路径 -> 写入内容

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        self.calls.append(args)
        cmd = args[0]
        if cmd == "image":  # image inspect -f {{.Id}} <image>
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


def make_task(task_id: str) -> RolloutTaskSpec:
    return RolloutTaskSpec(
        task_id=task_id,
        image="fake-image:v1",
        base_commit=BASE_COMMIT,
        prompt=f"Fix the issue in {task_id}",
        public_bundle_payload=b'{"instance_id": "%s"}' % task_id.encode(),
        public_bundle_digest=SHA_BUNDLE,
        grading_spec=GradingEnvSpec(
            task_id=task_id,
            image="fake-image:v1",
            base_commit=BASE_COMMIT,
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
) -> Chain:
    docker = FakeRolloutDocker(rm_fail=rm_fail)
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
        task_resolver=make_task(TASK_ID_DENSE),
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
        rollout_log_probs=[-(i + 1) * 0.03125 for i in range(16)],
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

    assert len(result[0].rollout_routed_experts) == rows * 48 * 8  # len(tokens)-1 行
    projection = chain.orchestrator.audits[0].finalized.projection
    (branch,) = projection.branches
    assert branch.routing.alignment == "sglang_prompt_minus1_plus_gen"
    assert (branch.routing.num_rows, branch.routing.num_layers, branch.routing.router_topk) == (30, 48, 8)
    assert branch.sampling_mask.offsets_len == 17
    assert chain.orchestrator.audits[0].steps == list(LIFECYCLE_STEPS)


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
    # 清理照常执行
    assert len(chain.docker.removed) == 1


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
