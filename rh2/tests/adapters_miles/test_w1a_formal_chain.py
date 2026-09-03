"""W1a 验收主链：**bringup 挡板以下**的真实 fa_formal 生产链在 miles 路径通过。

链路（全部生产代码，替身只在文档化注入点）::

    miles GenerateFnInput -> Rh2MilesGenerateFn（W1a 六字段铸造点）
    -> rh2_custom_generate -> 真实 RolloutOrchestrator.generate
       （execution_mode=fa_formal：generate.py:2366-2378 六字段强校验、
        baseline manifest、单 owner drain、评分、quiescence 屏障、
        finalization store、Outcome v2）
    -> 真实 canonicalize_group -> 六字段盖回输出叶（round-trip 无损）

替身面 = tests/adapters/test_slime_generate.py 的既有 mock 纪律（docker /
harness 驱动 / session adapter / 评分提交 / 屏障 / finalization store /
drain owner），移植到 vendor slime + miles 测试世界。bringup.py:705 的
fa_formal 临时拒绝挡板只挡完整启动入口——本测试按 W1a 验收口径直接构造
挡板以下的编排本体，不碰挡板本身。

验收断言：
① 六字段强校验真实通过（audit 无 identity 阶段失败、9 步走满、真实交付）；
② 未铸造身份的同链路必然被 fa_identity_incomplete 拒绝（证明校验未被放宽，
   铸造是使其通过的唯一差异）；
③ retry（真实 reset_for_retry）换新 attempt/seq/session，member 身份稳定；
④ 交付 miles 样本的六字段与铸造结果逐字一致，Outcome v2 身份同源。
"""

from __future__ import annotations

from argparse import Namespace
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

BASE_COMMIT = "a" * 40
SHA_TEMPLATE = "sha256:" + "a" * 64
SHA_BUNDLE = "sha256:" + "e" * 64
TS = "2026-07-07T09:30:25Z"
TASK_ID = "psf__requests-2931"
POLICY_VERSION = "5"

# dense 两轮 token 布局（与 tests/adapters dense fixture 同形）：
# prompt 12 + 生成 10 + 工具 5 + 生成 8。
D_PROMPT, D_GEN1, D_TOOL, D_GEN2 = 12, 10, 5, 8
D_TOKENS = (
    [1500 + i for i in range(D_PROMPT)]
    + [2500 + i for i in range(D_GEN1)]
    + [3500 + i for i in range(D_TOOL)]
    + [4500 + i for i in range(D_GEN2)]
)
SAMPLING_PARAMS = {"temperature": 1.0, "top_p": 1.0, "max_new_tokens": 4096}


# ---------------------------------------------------------------------------
# 替身（形状 = tests/adapters/test_slime_generate.py 的既有 mock 纪律）
# ---------------------------------------------------------------------------


def _sglang_response(rid: str, output_ids: list[int], finish: str = "stop") -> dict[str, Any]:
    """SGLang /generate 响应替身；formal 链要求每轮真实 weight_version。
    不带 top-p tape（top_p=1.0 链路；canonicalize 拒绝 slime tape 字段）。"""

    return {
        "text": "<mock generation>",
        "meta_info": {
            "id": rid,
            "finish_reason": {"type": finish},
            "output_token_logprobs": [
                [-(i + 1) * 0.05, token_id, None] for i, token_id in enumerate(output_ids)
            ],
            "prompt_tokens": 0,
            "completion_tokens": len(output_ids),
            "weight_version": POLICY_VERSION,
        },
    }


@dataclass
class _MockTurn:
    prompt_ids: list[int]
    response: dict[str, Any]


def _dense_turns() -> list[_MockTurn]:
    gen1 = D_TOKENS[D_PROMPT : D_PROMPT + D_GEN1]
    gen2 = D_TOKENS[D_PROMPT + D_GEN1 + D_TOOL :]
    return [
        _MockTurn(D_TOKENS[:D_PROMPT], _sglang_response("rid_t0", gen1, finish="tool_calls")),
        _MockTurn(D_TOKENS[: D_PROMPT + D_GEN1 + D_TOOL], _sglang_response("rid_t1", gen2)),
    ]


class _MockSessionAdapter:
    """slime BaseAdapter 接口形状：turn 脚本驱动真实 capture 钩子 + 产叶链样本。"""

    def __init__(self, hook, session_defaults, turns, leaf_samples):
        self.hook = hook
        self.session_defaults = session_defaults
        self.turns = turns
        self.leaf_samples = leaf_samples
        self.opened: list[str] = []

    def revoke_session(self, sid):
        pass

    def open_session(self, sid, *, sampling_defaults=None, max_context_tokens=0,
                     physical_attempt_id=None, capability_token=None):
        if sid in self.opened:
            raise ValueError(f"session_id {sid!r} already exists")
        self.opened.append(sid)
        self.opened_paid = physical_attempt_id

    async def run_all_turns(self):
        for turn in self.turns:
            self.hook.on_generate_response(
                prompt_token_ids=turn.prompt_ids,
                sampling_params=self.session_defaults,
                response=turn.response,
            )

    async def finish_session(self, sid, *, base_sample, reward=0.0,
                             extra_metadata=None, wait_timeout=5.0):
        return list(self.leaf_samples)

    async def drop_session(self, sid, *, wait_timeout=5.0):
        pass


class _MockDriver:
    name = "mock_harness"

    def __init__(self, adapter_ref):
        self.adapter_ref = adapter_ref

    async def run(self, sandbox, *, workdir, session_id, adapter_url,
                  time_budget_sec, prompt):
        await self.adapter_ref["adapter"].run_all_turns()
        return 0


def _make_fake_docker():
    from repoharness2.grading.manager import ExecResult

    class FakeRolloutDocker:
        def __init__(self):
            self.calls: list[tuple[str, ...]] = []
            self.writes: dict[str, bytes] = {}
            self.removed: list[str] = []

        async def __call__(self, *args, input_bytes=None):
            self.calls.append(args)
            cmd = args[0]
            if cmd == "image":
                return ExecResult(0, "sha256:" + "ab" * 32 + "\n", "")
            if cmd == "inspect":
                return ExecResult(0, "sha256:" + "ab" * 32 + "\n", "")
            if cmd == "run":
                return ExecResult(0, "f00dfeedcafe\n", "")
            if cmd == "rm":
                self.removed.append(args[-1])
                return ExecResult(0, "", "")
            if cmd == "exec":
                script = args[-1]
                # baseline 锚（run_bash 包了 cd 前缀）先于血缘探针分支匹配
                if "&& git -C" in script.strip() and "rev-parse HEAD" in script:
                    return ExecResult(0, BASE_COMMIT + "\n", "")
                if "find ." in script and "sha256sum" in script:
                    return ExecResult(0, "", "")  # 空树 = 零 entries 合法基线
                if "rev-parse HEAD" in script:
                    probe = f"HEAD={BASE_COMMIT}\nBASE_OBJECT_OK\nPARENT=none\nDIFFSTAT=\n"
                    return ExecResult(0, probe, "")
                if "cat > " in script:
                    path = script.rsplit("cat > ", 1)[1].strip()
                    self.writes[path] = input_bytes or b""
                    return ExecResult(0, "", "")
                return ExecResult(0, "", "")
            raise AssertionError(f"FakeRolloutDocker 不认识的命令: {args}")

    return FakeRolloutDocker()


def _make_task():
    from repoharness2.adapters.slime import RolloutTaskSpec
    from repoharness2.grading.manager import GradingEnvSpec, HygieneRules

    return RolloutTaskSpec(
        task_id=TASK_ID,
        image="fake-image:v1",
        base_commit=BASE_COMMIT,
        prompt=f"Fix the issue in {TASK_ID}",
        public_bundle_payload=b'{"instance_id": "psf__requests-2931"}',
        public_bundle_digest=SHA_BUNDLE,
        image_local_build=True,
        grading_spec=GradingEnvSpec(
            task_id=TASK_ID,
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


def _make_grading_report(trajectory_id: str, task_id: str):
    from repoharness2.contracts import GradingReport

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
class _FakeFinalizationStore:
    bodies: list[dict[str, Any]] = field(default_factory=list)
    receipts: list[Any] = field(default_factory=list)
    cleanup_results: list[Any] = field(default_factory=list)

    def put_artifact_bodies(self, *, frozen_patch, baseline_manifest):
        self.bodies.append({"frozen_patch": frozen_patch, "baseline_manifest": baseline_manifest})

    def persist_receipt(self, receipt):
        self.receipts.append(receipt)

    def append_cleanup_result(self, result):
        self.cleanup_results.append(result)


class _Barrier:
    async def establish(self, *, workspace, audit):
        from repoharness2.adapters.slime.generate import QuiescenceConfirmed

        class _FrozenWs:
            def __init__(self, underlying):
                self._u = underlying

            async def run_bash(self, script):
                return await self._u.run_bash(script)

        return QuiescenceConfirmed(
            frozen_grading_workspace=_FrozenWs(workspace),
            snapshot_ref="sha256:abc",
            evidence_refs=("s",),
        )


@dataclass
class _Chain:
    orchestrator: Any
    grading_calls: list
    store: _FakeFinalizationStore
    adapter_ref: dict


def _build_formal_chain(world, leaf_samples) -> _Chain:
    from repoharness2.adapters.slime import RolloutOrchestrator, SlimeBindingConfig
    from repoharness2.adapters.slime.capture_wire import SessionPlaneDrainResult

    config = SlimeBindingConfig(
        model_name="Qwen/Qwen3-4B",
        backend_version="0.5.9",
        renderer_cls_name="Qwen3Renderer",
        expected_renderer_cls_name="Qwen3Renderer",
        tokenizer_name="Qwen/Qwen3-4B",
        template_hash=SHA_TEMPLATE,
        adapter_url="http://10.0.0.1:18001",
        harness_name="mock_harness",
        expect_moe_routing=False,
        execution_mode="fa_formal",
        policy_version=POLICY_VERSION,
        require_real_weight_versions=True,
        reject_context_shrink=True,
        reject_on_nonzero_harness_exit=True,
        staleness_threshold=4,  # 前置清理批（B-1）起只是 consume-time 阈值的记录用镜像，不是资格门
    )
    adapter_ref: dict[str, Any] = {}
    turns = _dense_turns()

    def adapter_factory(hook, session_defaults):
        adapter = _MockSessionAdapter(hook, session_defaults, turns, leaf_samples)
        adapter_ref["adapter"] = adapter
        return adapter

    grading_calls: list[str] = []

    async def grading_submit(*, trajectory_id, workspace, spec, **kw):
        grading_calls.append(trajectory_id)
        return _make_grading_report(trajectory_id, spec.task_id)

    async def fake_drain_owner(sid: str):
        return SessionPlaneDrainResult(
            physical_attempt_id=sid.removeprefix("s-"),
            revoke_enforced=True,
            inflight_at_drain_start=0,
            inflight_zero_confirmed=True,
            pending_turns=0,
            unfinalized_drafts=0,
            poison_clean=True,
            late_requests_rejected_after_revoke=0,
            turn_seq_high_water=2,
            weight_versions_seen=[POLICY_VERSION],
            drain_owner="fake_adapter_loop",
        )

    store = _FakeFinalizationStore()
    orchestrator = RolloutOrchestrator(
        config=config,
        task_resolver=_make_task(),
        adapter_factory=adapter_factory,
        harness_driver=_MockDriver(adapter_ref),
        grading_submit=grading_submit,
        docker=_make_fake_docker(),
        runtime_quiescence_barrier=_Barrier(),
        finalization_store=store,
        session_drain_owner=fake_drain_owner,
    )
    return _Chain(orchestrator, grading_calls, store, adapter_ref)


def _mk_leaf(world, *, index, group_index):
    """vendor 叶链形状（TrajectoryManager 产物：不带 tape/weight_versions，
    版本事实由 backfill 从 capture 轮次真实回填）。"""

    return world.mk_vendor_sample(
        index=index,
        group_index=group_index,
        rollout_id=None,
        tokens=list(D_TOKENS),
        response="resp",
        response_length=D_GEN1 + D_TOOL + D_GEN2,
        loss_mask=[1] * D_GEN1 + [0] * D_TOOL + [1] * D_GEN2,
        rollout_log_probs=(
            [-(i + 1) * 0.05 for i in range(D_GEN1)]
            + [0.0] * D_TOOL
            + [-(i + 1) * 0.05 for i in range(D_GEN2)]
        ),
        weight_versions=[],
        metadata={},
    )


def _mk_generate_input(world, orchestrator, sample):
    from miles.rollout.base_types import GenerateFnInput
    from repoharness2.adapters.miles.group_admission import GROUP_ADMISSION_FILTER_PATH

    # W1b 第二段：非 s1 模式派发要求复合 group filter 已接线（generate_fn 守卫）
    args = Namespace(
        rh2_orchestrator=orchestrator, n_samples_per_prompt=2,
        dynamic_sampling_filter_path=GROUP_ADMISSION_FILTER_PATH,
    )
    return GenerateFnInput(
        state=SimpleNamespace(args=args),
        sample=sample,
        sampling_params=dict(SAMPLING_PARAMS),
        evaluation=False,
    )


# ---------------------------------------------------------------------------
# 主验收：铸造使 fa_formal 强校验真实通过 + round-trip + Outcome 身份同源
# ---------------------------------------------------------------------------


async def test_w1a_formal_chain_minted_identity_passes_and_round_trips(world):
    world.install_sglang_stub()
    from miles.rollout.base_types import GenerateFnOutput
    from repoharness2.adapters.miles import identity as idm

    # group_index=3, n=2, index=7 -> slot=1（stock data_source 算术）
    miles_input = world.mk_miles_input(index=7, group_index=3)
    chain = _build_formal_chain(world, [_mk_leaf(world, index=7, group_index=3)])

    fn = world.Rh2MilesGenerateFn()
    out = await fn(_mk_generate_input(world, chain.orchestrator, miles_input))

    minted = {k: miles_input.metadata[k] for k in idm.IDENTITY_KEYS}
    assert minted[idm.GROUP_ID_KEY] == "miles_g3"
    assert minted[idm.EXECUTION_ID_KEY] == "miles_g3_m1"
    assert minted[idm.MEMBER_SLOT_KEY] == 1
    assert minted[idm.ATTEMPT_SEQ_KEY] == 1

    # ① 六字段强校验真实通过：audit 无 identity 失败、九步走满、真实评分交付
    audit = chain.orchestrator.audits[0]
    assert not any(f.stage == "identity" for f in audit.failure_records)
    assert audit.failure_records == [] and audit.cleanup_failures == []
    assert audit.steps[-1] == "step9_samples_delivered"
    assert chain.grading_calls == ["miles_g3_m1"]
    assert chain.store.receipts  # finalization 真实发生（fa_formal 全链）

    # audit 身份与铸造同源：trajectory = execution id、session 按 attempt 铸造
    assert audit.trajectory_id == minted[idm.EXECUTION_ID_KEY]
    assert audit.physical_attempt_id == minted[idm.ATTEMPT_ID_KEY]
    assert audit.session_id == "s-" + minted[idm.ATTEMPT_ID_KEY]

    # ② round-trip 身份无损：交付 miles 样本六字段与铸造逐字一致
    assert isinstance(out, GenerateFnOutput)
    samples = out.samples
    assert isinstance(samples, list) and len(samples) == 1
    (delivered,) = samples
    assert isinstance(delivered, world.MS)
    assert delivered.status is world.MS.Status.COMPLETED
    assert delivered.reward == 1.0
    assert delivered.weight_versions == [POLICY_VERSION, POLICY_VERSION]
    for key in idm.IDENTITY_KEYS:
        assert delivered.metadata[key] == minted[key], key

    # ③ Outcome v2 身份同源（producer 从同一 metadata 读出；audit 上是
    # JSON dump，typed 对象在 orchestrator.outcomes）
    assert audit.outcome_v2 is not None
    (ov2,) = chain.orchestrator.outcomes
    assert ov2.identity.prompt_group_id == minted[idm.GROUP_ID_KEY]
    assert ov2.identity.rollout_execution_id == minted[idm.EXECUTION_ID_KEY]
    assert ov2.identity.physical_attempt_id == minted[idm.ATTEMPT_ID_KEY]
    assert ov2.identity.physical_attempt_seq == 1
    assert ov2.member_slot == 1  # member_slot 是 Outcome v2 顶层字段
    assert ov2.identity.group_index == 3


async def test_w1a_formal_chain_retry_new_attempt_new_session(world):
    """③ retry：真实 reset_for_retry 后重派发——member/trajectory 身份稳定，
    physical attempt/seq/session 全部换新（session capability 按 attempt
    重铸，见 session_capability.mint_session_capability）。"""

    world.install_sglang_stub()
    from repoharness2.adapters.miles import identity as idm

    miles_input = world.mk_miles_input(index=7, group_index=3)
    fn = world.Rh2MilesGenerateFn()

    chain1 = _build_formal_chain(world, [_mk_leaf(world, index=7, group_index=3)])
    out1 = await fn(_mk_generate_input(world, chain1.orchestrator, miles_input))
    paid1 = miles_input.metadata[idm.ATTEMPT_ID_KEY]
    audit1 = chain1.orchestrator.audits[0]

    # miles 真实回收路径：reset_for_retry 保留 metadata（旧 attempt 身份在场）
    miles_input.reset_for_retry()
    chain2 = _build_formal_chain(world, [_mk_leaf(world, index=7, group_index=3)])
    out2 = await fn(_mk_generate_input(world, chain2.orchestrator, miles_input))
    paid2 = miles_input.metadata[idm.ATTEMPT_ID_KEY]
    audit2 = chain2.orchestrator.audits[0]

    assert paid1 != paid2
    assert miles_input.metadata[idm.ATTEMPT_SEQ_KEY] == 2
    assert audit1.trajectory_id == audit2.trajectory_id == "miles_g3_m1"
    assert audit1.session_id != audit2.session_id  # 会话身份按 attempt 隔离
    assert audit2.session_id == "s-" + paid2
    assert audit2.steps[-1] == "step9_samples_delivered"
    (d1,) = out1.samples
    (d2,) = out2.samples
    assert d1.metadata[idm.ATTEMPT_ID_KEY] == paid1
    assert d2.metadata[idm.ATTEMPT_ID_KEY] == paid2


async def test_w1a_formal_chain_unminted_identity_rejected(world):
    """② 对照负例：同一 fa_formal 链、未经铸造的 miles 样本——
    generate.py:2366-2378 的强校验必然 fail-closed（不评分不交付），
    证明校验未被放宽、W1a 铸造是使其通过的唯一差异。"""

    world.install_sglang_stub()
    from repoharness2.adapters.slime.generate import rh2_custom_generate

    miles_input = world.mk_miles_input(index=7, group_index=3)
    chain = _build_formal_chain(world, [_mk_leaf(world, index=7, group_index=3)])

    args = Namespace(rh2_orchestrator=chain.orchestrator)  # 直接调 rh2 入口，不经 generate_fn 守卫
    delivered = await rh2_custom_generate(args, miles_input, dict(SAMPLING_PARAMS))

    audit = chain.orchestrator.audits[0]
    assert chain.grading_calls == []  # 不评分
    assert audit.finalized is None  # 不交付
    assert any(
        f.stage == "identity" and "fa_identity_incomplete" in f.detail
        for f in audit.failure_records
    )
    assert all(getattr(x, "remove_sample", False) for x in delivered)  # abort 形状
