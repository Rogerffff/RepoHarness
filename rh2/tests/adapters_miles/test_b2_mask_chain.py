"""B2（R6-ext）验收组合测试：sampling mask 的真实纵链，一条链跑通、零手工短路。

链路（与审查验收标准逐字对应，禁手工 attach、禁 `_pop_staged` 绕过）::

    miles generate input（load_generate_function -> GenerateFnInput）
    -> Rh2MilesGenerateFn -> 真实 RolloutOrchestrator.generate（9 步生命周期）
    -> 真实 rh2_call_sglang_generate（install_capture_wire 后的 wire 本体）
       打 fake HTTP 引擎，收 sglang-miles wire 形态响应
    -> 真实 capture stage（wire 内）/ commit（registry.commit——生产链由
       record_turn 包装调用同一函数；脚本化轮不经 TrajectoryManager，
       驱动替身在每轮响应后按同一时点调它）
    -> 真实 leaf backfill + assemble_leaf_sampling_mask（generate step5）
    -> 真实 project_from_slime（经 project_group_with_sampler_support 换成
       sampler_support_token_ids + behavior_support_normalized 事实）
    -> 真实 canonicalize（附加属性 -> miles RolloutSamplingMask 一等字段）
    -> miles DefaultDataBuffer put/get -> postprocess -> convert_samples_to_train_data

    替身面只有：HTTP 客户端（fake aiohttp 短路到内存 fake 引擎）、docker、
    harness 驱动（把脚本轮喂进真实 wire）、评分提交、叶链树侧
    （finish_session 按 vendor to_sample 形状产叶——TrajectoryManager 本体
    归真实 CC 链）。capture/装配/投影/canonicalize/转换全是生产代码。

    orchestrator 说明：这里的 args.rh2_orchestrator 是**真实
    RolloutOrchestrator**（按其文档化注入点配 CPU 替身），不是 fake 同形
    对象；"不得手工塞 fake orchestrator" 的 B1 bootstrap 验收（真实
    BringupService 构造并注入）在 test_b1_real_bootstrap.py——那条链的
    docker/harness 面在 CPU 上到不了本测试要覆盖的 mask 纵链终点，两个
    验收各占一档。

覆盖恰好三个场景（审查明示不扩）：两轮生成、观察/工具位单例 support、
一个掉落轮（committed 但 token 不进叶链，装配与回链都必须跳过它）。
"""

from __future__ import annotations

import logging
import struct
from argparse import Namespace
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.integration_base

BASE_COMMIT = "a" * 40
SHA_TEMPLATE = "sha256:" + "a" * 64
SHA_BUNDLE = "sha256:" + "e" * 64
TS = "2026-07-07T09:30:25Z"

# ---------------------------------------------------------------------------
# token 布局：prompt(4) + gen1(3) + tool(2, mask=0) + gen2(2)
# ---------------------------------------------------------------------------

PROMPT = [100, 101, 102, 103]
GEN1 = [201, 202, 203]
GEN1_SUPPORTS = [[201, 5], [202], [203, 7, 8]]
GEN1_SUPPORT_LOGPROBS = [-0.10, -0.11, -0.12]
TOOL = [301, 302]
GEN2 = [401, 402]
GEN2_SUPPORTS = [[401, 9], [402, 10]]
GEN2_SUPPORT_LOGPROBS = [-0.30, -0.31]
DROPPED = [901, 902]  # 掉落轮：committed 但 token 不出现在叶链里

LEAF_TOKENS = PROMPT + GEN1 + TOOL + GEN2
LEAF_LOSS_MASK = [1, 1, 1, 0, 0, 1, 1]
# vendor to_sample 语义：采样位 = TurnRecord logprob（wire 已切换成
# support-normalized 列），工具位 = 0.0
LEAF_LOGPROBS = GEN1_SUPPORT_LOGPROBS + [0.0, 0.0] + GEN2_SUPPORT_LOGPROBS

# 期望 CSR（采样位 = 引擎支持集；tool 位 = 单例 {该 token}；offsets 重基）
EXPECTED_MASK_IDS = [201, 5, 202, 203, 7, 8, 301, 302, 401, 9, 402, 10]
EXPECTED_MASK_OFFSETS = [0, 2, 3, 6, 7, 8, 10, 12]


def _engine_payload(output_ids, supports, support_logprobs):
    return {
        "text": "<fake>",
        "meta_info": {
            "id": f"rid-{output_ids[0]}",
            "weight_version": "7",
            "finish_reason": {"type": "stop"},
            # 全词表列（诊断，值刻意与 support-normalized 列不同）
            "output_token_logprobs": [
                [-1.0 - i, token_id] for i, token_id in enumerate(output_ids)
            ],
            "output_token_sampling_mask": supports,
            "output_token_sampling_logprobs": support_logprobs,
        },
    }


TURN_SCRIPT = [
    # (prompt_ids, 引擎应答)——第 2 条是掉落轮
    (PROMPT, _engine_payload(GEN1, GEN1_SUPPORTS, GEN1_SUPPORT_LOGPROBS)),
    (
        PROMPT + GEN1 + TOOL,
        _engine_payload(DROPPED, [[901], [902]], [-0.20, -0.21]),
    ),
    (
        PROMPT + GEN1 + TOOL,
        _engine_payload(GEN2, GEN2_SUPPORTS, GEN2_SUPPORT_LOGPROBS),
    ),
]


# ---------------------------------------------------------------------------
# fake HTTP 面（真实 wire 的 aiohttp 客户端短路到内存 fake 引擎；
# 与 test_capture_wire_sampling_mask 同一形状）
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload):
        self.status = 200
        self._payload = payload

    async def json(self, content_type=None):
        return self._payload

    async def text(self):
        return ""


class _PostCM:
    def __init__(self, resp):
        self._resp = resp

    async def __aenter__(self):
        return self._resp

    async def __aexit__(self, *exc):
        return False


class _FakeEngine:
    def __init__(self):
        self.requests: list[dict] = []
        self.responses: list[dict] = []

    def next_response(self):
        return self.responses.pop(0)


class _FakeClientSession:
    def __init__(self, engine):
        self._engine = engine

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def post(self, url, json=None, headers=None):
        self._engine.requests.append({"url": url, "payload": json, "headers": headers})
        return _PostCM(_FakeResponse(self._engine.next_response()))


class _FakeAiohttp:
    class ClientError(Exception):
        pass

    def __init__(self, engine):
        self._engine = engine

    def ClientTimeout(self, **_kw):  # noqa: N802 - 镜像 aiohttp API 名
        return None

    def ClientSession(self, **_kw):  # noqa: N802
        return _FakeClientSession(self._engine)


# ---------------------------------------------------------------------------
# docker / 评分替身（形状对齐 tests/adapters/test_slime_generate.py 的既有替身）
# ---------------------------------------------------------------------------


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
                if "rev-parse HEAD" in script:
                    probe = (
                        f"HEAD={BASE_COMMIT}\nBASE_OBJECT_OK\nPARENT=none\nDIFFSTAT=\n"
                    )
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

    task_id = "psf__requests-2931"
    return RolloutTaskSpec(
        task_id=task_id,
        image="fake-image:v1",
        base_commit=BASE_COMMIT,
        prompt=f"Fix the issue in {task_id}",
        public_bundle_payload=b'{"instance_id": "psf__requests-2931"}',
        public_bundle_digest=SHA_BUNDLE,
        image_local_build=True,
        grading_spec=GradingEnvSpec(
            task_id=task_id,
            image="fake-image:v1",
            base_commit=BASE_COMMIT,
            image_local_build=True,
            eval_script="echo eval",
            parse_log=lambda text: (_ for _ in ()).throw(
                AssertionError("mock 不该调 parser")
            ),
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


# ---------------------------------------------------------------------------
# 会话替身：把脚本轮喂进**真实 wire**，commit 用**真实 registry.commit**
# ---------------------------------------------------------------------------


def _make_mask_wire_adapter(registry, hook, session_defaults, leaf_builder):
    import slime.agent.adapters.common as slime_common

    class MaskWireAdapter:
        """SessionAdapter 形状：wire/stage/commit 全真，只有树侧是脚本。"""

        def __init__(self):
            self.sid: str | None = None

        def open_session(
            self,
            sid,
            *,
            sampling_defaults=None,
            max_context_tokens=0,
            physical_attempt_id=None,
            capability_token=None,
        ):
            self.sid = sid
            self.sampling_defaults = dict(sampling_defaults or {})
            registry.register(sid, hook, physical_attempt_id=physical_attempt_id)

        def revoke_session(self, sid):
            registry.revoke(sid)

        async def run_all_turns(self):
            adapter_ns = SimpleNamespace(
                logger=logging.getLogger("test_b2_mask_chain"),
                max_token_keys=("max_tokens",),
                stop_keys=("stop",),
                sglang_url="http://fake-engine:1",
            )
            for prompt_ids, _payload in TURN_SCRIPT:
                session = slime_common.Session(
                    sampling_defaults=dict(self.sampling_defaults),
                    max_context_tokens=0,
                )
                # 真实 wire：翻译旗标/前置校验/发 HTTP/解析校验/stage
                await slime_common.call_sglang_generate(
                    list(prompt_ids), session, {}, adapter=adapter_ns,
                    session_id=self.sid,
                )
                # 真实 commit：生产链由 rh2_record_turn（record_turn 包装）在
                # 该轮确定进入轨迹树后调用 registry.commit——这里按同一时点
                # 调用同一函数（不是 _pop_staged 手工绕过）。
                registry.commit(self.sid)

        async def finish_session(
            self, sid, *, base_sample, reward=0.0, extra_metadata=None, wait_timeout=5.0
        ):
            return [leaf_builder()]

        async def drop_session(self, sid, *, wait_timeout=5.0):
            registry.unregister(sid)

    return MaskWireAdapter()


# ---------------------------------------------------------------------------
# 主测试
# ---------------------------------------------------------------------------


async def test_b2_mask_real_chain_two_turns_singleton_and_dropped_turn(world):
    world.install_sglang_stub()
    from miles.rollout.base_types import GenerateFnInput, GenerateFnOutput
    from miles.rollout.inference_rollout.compatibility import load_generate_function
    from miles.utils.sampling_mask import RolloutSamplingMask

    from repoharness2.adapters.slime import (
        GenerationCaptureHook,
        RolloutOrchestrator,
        SlimeBindingConfig,
    )
    from repoharness2.adapters.slime import capture_wire as cw
    from repoharness2.adapters.slime.generate import GenerationCaptureHook as _Hook

    assert GenerationCaptureHook is _Hook

    # -- 真实 capture wire + fake HTTP 面 -----------------------------------
    registry = cw.CaptureRegistry()
    cw.install_capture_wire(registry)
    engine = _FakeEngine()
    engine.responses = [payload for _prompt, payload in TURN_SCRIPT]
    saved_aiohttp = cw.aiohttp
    cw.aiohttp = _FakeAiohttp(engine)

    try:
        task = _make_task()
        config = SlimeBindingConfig(
            model_name="Qwen/Qwen3-4B",
            backend_version="0.5.9",
            renderer_cls_name="Qwen3Renderer",
            expected_renderer_cls_name="Qwen3Renderer",
            tokenizer_name="Qwen/Qwen3-4B",
            template_hash=SHA_TEMPLATE,
            adapter_url="http://127.0.0.1:1",
            harness_name="mock_harness",
            policy_version="7",
        )

        def leaf_builder():
            # vendor TrajectoryManager to_sample 形状的叶链（树侧脚本）：
            # 不带 tape/weight_versions，logprob 列 = TurnRecord 的
            # support-normalized 值（wire 已切换）+ 工具位 0.0。
            return world.SS(
                index=0,
                group_index=0,
                rollout_id=0,
                prompt="prompt",
                tokens=list(LEAF_TOKENS),
                response="resp",
                response_length=len(LEAF_LOSS_MASK),
                loss_mask=list(LEAF_LOSS_MASK),
                rollout_log_probs=list(LEAF_LOGPROBS),
                reward=0.0,
                weight_versions=[],
                status=world.SS.Status.COMPLETED,
                metadata={"truncated": False, "use_tool": True, "ill_formed": False},
            )

        adapter_holder: dict = {}

        def adapter_factory(hook, session_defaults):
            # 请求侧二选一在这里可见：mask 引擎会话默认键必须带新约定
            assert session_defaults.get("return_sampling_mask") is True
            assert session_defaults.get("return_top_p_token_ids") is False
            adapter = _make_mask_wire_adapter(
                registry, hook, session_defaults, leaf_builder
            )
            adapter_holder["adapter"] = adapter
            adapter_holder["hook"] = hook
            return adapter

        class Driver:
            name = "mock_harness"

            async def run(self, sandbox, *, workdir, session_id, adapter_url,
                          time_budget_sec, prompt):
                await adapter_holder["adapter"].run_all_turns()
                return 0

        grading_calls: list = []

        async def grading_submit(*, trajectory_id, workspace, spec, **kw):
            grading_calls.append(trajectory_id)
            return _make_grading_report(trajectory_id, spec.task_id)

        docker = _make_fake_docker()
        orchestrator = RolloutOrchestrator(
            config=config,
            task_resolver=task,
            adapter_factory=adapter_factory,
            harness_driver=Driver(),
            grading_submit=grading_submit,
            docker=docker,
            session_poison_check=registry.poison.is_poisoned,
            capture_boundary_check=registry.assert_session_clean,
        )

        # -- miles 侧入口：loader -> GenerateFnInput ------------------------
        fn = load_generate_function(
            "repoharness2.adapters.miles.generate_fn.Rh2MilesGenerateFn"
        )
        args = Namespace(
            rh2_orchestrator=orchestrator,
            rollout_top_p=0.8,  # miles 严格开关：<1.0 即 replay，canonicalize 强制 mask
            rh2_engine_sampling_mask=True,  # 请求侧二选一 = args 显式配置
        )
        miles_input = world.mk_miles_input(index=0, group_index=0)
        gi = GenerateFnInput(
            state=SimpleNamespace(args=args),
            sample=miles_input,
            sampling_params={
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 32,
                "max_new_tokens": 512,
            },
            evaluation=False,
        )

        out = await fn(gi)

        # ============ ① wire/stage/commit：真实路径证据 ====================
        assert len(engine.requests) == 3
        for request in engine.requests:
            payload = request["payload"]
            assert payload["return_sampling_mask"] is True  # 新顶层约定
            sp = payload["sampling_params"]
            assert "custom_params" not in sp  # 旧 custom_params 约定未开
            assert sp["top_k"] == 32 and sp["top_p"] == 0.8
        assert registry.stats["staged"] == 3
        assert registry.stats["committed"] == 3
        assert registry.stats["dropped_uncommitted"] == 0

        # ============ ② 交付样本：canonicalize 后的 miles 一等字段 =========
        assert isinstance(out, GenerateFnOutput)
        (delivered,) = out.samples
        assert isinstance(delivered, world.MS)
        assert delivered.status is world.MS.Status.COMPLETED
        assert delivered.reward == 1.0 and grading_calls
        mask = delivered.rollout_sampling_mask
        assert isinstance(mask, RolloutSamplingMask)
        mask_ids, mask_offsets = mask._as_tensors()
        assert mask_ids.tolist() == EXPECTED_MASK_IDS
        assert mask_offsets.tolist() == EXPECTED_MASK_OFFSETS
        # 行为 logprob 列 = support-normalized（工具位 0.0），掉落轮不混入
        assert delivered.rollout_log_probs == LEAF_LOGPROBS
        assert delivered.weight_versions == ["7", "7"]  # 只有两个入训轮
        # 旧 slime tape 字段既没有被借道残留、也没有混进 miles 对象
        assert "rollout_top_p_token_ids" not in delivered.__dict__
        assert "rh2_sampling_mask" not in delivered.__dict__

        # ============ ③ 中立 projection：sampler_support 事实 ==============
        audit = orchestrator.audits[0]
        assert audit.steps[-1] == "step9_samples_delivered"
        projection = audit.finalized.projection
        (branch,) = projection.branches
        ref = branch.sampling_mask
        assert ref.mask_kind == "sampler_support_token_ids"
        assert ref.top_p == 0.8 and ref.top_k == 32
        assert ref.response_token_count == 7
        assert ref.offsets_len == 8 and ref.kept_token_count == 12
        assert branch.logprob_provenance.normalization == "behavior_support_normalized"
        assert branch.logprob_provenance.weight_version == "7"
        # 掉落轮不回链：capture 回链只剩两个入训轮
        hook = adapter_holder["hook"]
        assert branch.capture_record_refs == [
            hook.records[0].record_id,
            hook.records[2].record_id,
        ]
        # artifact 面：support tape 落盘（ids int32 / offsets int64），
        # 借道产生的 *_topp_* 诱饵已清理
        store = hook.artifact_store
        ids_key = f"{projection.trajectory_id}_{branch.branch_id}_support_ids"
        offsets_key = f"{projection.trajectory_id}_{branch.branch_id}_support_offsets"
        assert list(struct.unpack(f"<{len(EXPECTED_MASK_IDS)}i", store[ids_key])) == (
            EXPECTED_MASK_IDS
        )
        assert list(
            struct.unpack(f"<{len(EXPECTED_MASK_OFFSETS)}q", store[offsets_key])
        ) == EXPECTED_MASK_OFFSETS
        assert not [k for k in store if "_topp_" in k]

        # ============ ④ miles 训练面：buffer -> conversion =================
        from miles.ray.rollout.rollout_data_conversion import postprocess_rollout_data
        from miles.ray.rollout.train_data_conversion import (
            convert_samples_to_train_data,
        )
        from miles.rollout.fully_async_data_buffer import (
            DataBufferConstructorInput,
            DataBufferInput,
            DefaultDataBuffer,
        )

        margs = world.mk_miles_args(
            rollout_batch_size=1,
            global_batch_size=1,
            n_samples_per_prompt=1,
            rewards_normalization=False,
            rollout_top_p=0.8,  # replay 开关：conversion 强制逐样本 mask
        )
        recycled: list = []
        buf = DefaultDataBuffer(
            DataBufferConstructorInput(args=margs, unused_handler_fn=recycled.append)
        )
        await buf.put(DataBufferInput(prompt_group=[miles_input], group=[[delivered]]))
        got = await buf.get(current_version=8)
        assert recycled == []
        data, metadata = postprocess_rollout_data(margs, [got.group], None)
        td = convert_samples_to_train_data(margs, data, metadata, None, None)
        assert td["loss_masks"] == [LEAF_LOSS_MASK]
        assert td["rollout_log_probs"] == [LEAF_LOGPROBS]
        (ids_tensor,) = td["rollout_sampling_mask_ids"]
        (offsets_tensor,) = td["rollout_sampling_mask_offsets"]
        assert ids_tensor.tolist() == EXPECTED_MASK_IDS
        assert offsets_tensor.tolist() == EXPECTED_MASK_OFFSETS
        assert str(ids_tensor.dtype) == "torch.int32"
        assert str(offsets_tensor.dtype) == "torch.int64"
    finally:
        cw.aiohttp = saved_aiohttp
        # vendor slime 模块随 _vendor_slime_world teardown 整体摘除，wire
        # monkeypatch 不需要单独还原（下个 world 重新 import 干净模块）。
