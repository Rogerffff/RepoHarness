"""F1 验收纵链（finding §3.4）：真实 record_turn 制造"旧轮被 rewrite 掉落、
旧轮与活轮 token 相同、support/version/logprob 不同"，贯穿

    record_turn -> finish/to_sample -> backfill + sampling-mask 装配
    -> projection -> canonicalize -> convert_samples_to_train_data

断言精确选中活轮：version/support/logprob 三类事实全部来自活轮。

链路形状与 test_b2_mask_chain 同构（wire/stage/commit/树/叶链/装配/投影/
canonicalize/转换全是生产代码；替身只有 fake HTTP 引擎、docker、消息脚本、
评分提交），关键差异：

1. token 布局 = F1 反例 [11,21,21]（finding §3.2）：gen1=[11]（v1），
   掉落轮=[21]（v2，support {21,700}），tool 上下文 token 恰为 21（mask=0
   诱饵），活轮=[21]（v3，support {21,800}）。旧 matcher 按内容 first-match
   会把活轮位置绑到掉落轮（本测试先直接调 `_match_turns_to_runs` 固定该
   错误形状作对照），身份路径必须选中活轮。
2. finish_session 走**生产身份导出**：`attach_turn_identity_spans`（树走查
   重放）+ CaptureRegistry 的 commit 时刻绑定（真实 rh2_record_turn 包装
   写入）；orchestrator 用**生产 `bringup_leaf_facts`**（bringup.py）读出
   身份 span 装 LeafFacts——backfill/装配走身份直取路径。
3. 三轮引擎 weight_version 各不相同（"1"/"2"/"3"）——最终样本
   weight_versions 必须是 ["1","3"]（活轮 v3，掉落轮 v2 绝不混入）。
"""

from __future__ import annotations

import logging
from argparse import Namespace
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.integration_base

BASE_COMMIT = "a" * 40
SHA_TEMPLATE = "sha256:" + "a" * 64
SHA_BUNDLE = "sha256:" + "e" * 64
TS = "2026-07-07T09:30:25Z"

# ---------------------------------------------------------------------------
# token 布局（F1 反例）：prompt(4) + gen1(1) + tool(1, token=21) + live(1)
# ---------------------------------------------------------------------------

PROMPT = [100, 101, 102, 103]
GEN1 = [11]
GEN1_SUPPORTS = [[11, 5]]
GEN1_SUPPORT_LOGPROBS = [-0.10]
TOOL = [21]  # 与掉落轮/活轮同 token 的 mask=0 上下文（内容反推的诱饵位）
DROPPED = [21]
DROPPED_SUPPORTS = [[21, 700]]
DROPPED_SUPPORT_LOGPROBS = [-0.20]
LIVE = [21]
LIVE_SUPPORTS = [[21, 800]]
LIVE_SUPPORT_LOGPROBS = [-0.30]

LEAF_TOKENS = PROMPT + GEN1 + TOOL + LIVE
LEAF_LOSS_MASK = [1, 0, 1]
# 行为 logprob 列 = support-normalized（工具位 0.0）；活轮位必须是 -0.30
# （掉落轮的 -0.20 若出现即 F1 复发）
LEAF_LOGPROBS = GEN1_SUPPORT_LOGPROBS + [0.0] + LIVE_SUPPORT_LOGPROBS

# 期望 CSR：gen1 支持集 + tool 单例 {21} + 活轮支持集 {21,800}
EXPECTED_MASK_IDS = [11, 5, 21, 21, 800]
EXPECTED_MASK_OFFSETS = [0, 2, 3, 5]


def _engine_payload(output_ids, supports, support_logprobs, weight_version):
    return {
        "text": "<fake>",
        "meta_info": {
            "id": f"rid-{weight_version}",
            "weight_version": weight_version,
            "finish_reason": {"type": "stop"},
            "output_token_logprobs": [
                [-1.0 - i, token_id] for i, token_id in enumerate(output_ids)
            ],
            "output_token_sampling_mask": supports,
            "output_token_sampling_logprobs": support_logprobs,
        },
    }


TURN_SCRIPT = [
    (PROMPT, _engine_payload(GEN1, GEN1_SUPPORTS, GEN1_SUPPORT_LOGPROBS, "1")),
    (
        PROMPT + GEN1 + TOOL,
        _engine_payload(DROPPED, DROPPED_SUPPORTS, DROPPED_SUPPORT_LOGPROBS, "2"),
    ),
    (
        PROMPT + GEN1 + TOOL,
        _engine_payload(LIVE, LIVE_SUPPORTS, LIVE_SUPPORT_LOGPROBS, "3"),
    ),
]

_USER_MSG = {"role": "user", "content": "fix the issue"}
_ASST1_MSG = {"role": "assistant", "content": "gen1"}
_TOOL_MSG = {"role": "tool", "content": "tool output"}
_DROPPED_DRAFT_MSG = {"role": "assistant", "content": "dropped draft"}
_DROPPED_REWRITTEN_MSG = {"role": "assistant", "content": "dropped draft [rewritten]"}
_LIVE_MSG = {"role": "assistant", "content": "live"}

MESSAGE_SCRIPT = [
    ([_USER_MSG], _ASST1_MSG),
    ([_USER_MSG, _ASST1_MSG, _TOOL_MSG], _DROPPED_DRAFT_MSG),
    ([_USER_MSG, _ASST1_MSG, _TOOL_MSG, _DROPPED_REWRITTEN_MSG], _LIVE_MSG),
]


# ---------------------------------------------------------------------------
# fake HTTP 面 / docker / 评分替身（与 test_b2_mask_chain 同形）
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
# 会话替身：wire/stage/commit/树/叶链全真 + **生产身份导出**（F1 差异点）
# ---------------------------------------------------------------------------


def _make_identity_wire_adapter(registry, hook, session_defaults, holder):
    import slime.agent.adapters.common as slime_common
    from slime.agent.trajectory import TrajectoryManager

    from repoharness2.adapters.slime.turn_identity import attach_turn_identity_spans

    class IdentityWireAdapter:
        """finish_session 用生产 attach_turn_identity_spans（树走查 + commit
        绑定账解析），与 bringup PerRolloutAdapter 的身份步同一实现。"""

        def __init__(self):
            self.sid: str | None = None
            self.manager: TrajectoryManager | None = None

        def open_session(
            self,
            sid,
            *,
            sampling_defaults=None,
            max_context_tokens=0,
            physical_attempt_id=None,
            capability_token=None,
        ):
            assert TrajectoryManager.record_turn.__name__ == "rh2_record_turn", (
                "capture_wire 的生产 commit+绑定接线（rh2_record_turn 包装）未安装"
            )
            self.sid = sid
            self.sampling_defaults = dict(sampling_defaults or {})
            self.manager = TrajectoryManager()
            registry.register(sid, hook, physical_attempt_id=physical_attempt_id)

        def revoke_session(self, sid):
            registry.revoke(sid)

        async def run_all_turns(self):
            adapter_ns = SimpleNamespace(
                logger=logging.getLogger("test_f1_e2e_identity_chain"),
                max_token_keys=("max_tokens",),
                stop_keys=("stop",),
                sglang_url="http://fake-engine:1",
            )
            for (prompt_ids, _payload), (prompt_messages, response_message) in zip(
                TURN_SCRIPT, MESSAGE_SCRIPT, strict=True
            ):
                session = slime_common.Session(
                    sampling_defaults=dict(self.sampling_defaults),
                    max_context_tokens=0,
                )
                turn = await slime_common.call_sglang_generate(
                    list(prompt_ids), session, {}, adapter=adapter_ns,
                    session_id=self.sid,
                )
                # 真实 commit + F1 绑定时点：rh2_record_turn 包装
                self.manager.record_turn(
                    self.sid,
                    turn=turn,
                    prompt_messages=[dict(m) for m in prompt_messages],
                    response_message=dict(response_message),
                )

        async def finish_session(
            self, sid, *, base_sample, reward=0.0, extra_metadata=None, wait_timeout=5.0
        ):
            # 与 bringup PerRolloutAdapter.finish_session 同一顺序：先持树根
            # 引用，get_trajectory 弹树后在持有的根上做生产身份导出。
            holder["bindings"] = registry.turn_identity_bindings(sid)
            root = self.manager._trees.get(sid)
            samples = self.manager.get_trajectory(
                sid, base_sample=base_sample, reward=reward, extra_metadata=extra_metadata
            )
            if samples:
                assert root is not None
                attach_turn_identity_spans(
                    samples,
                    root,
                    fork_threshold=self.manager._fork_threshold,
                    max_sample_tokens=0,
                    resolve_capture_id=(
                        lambda turn_index: registry.turn_capture_binding(sid, turn_index)
                    ),
                )
            return samples

        async def drop_session(self, sid, *, wait_timeout=5.0):
            registry.unregister(sid)

    return IdentityWireAdapter()


# ---------------------------------------------------------------------------
# 主测试
# ---------------------------------------------------------------------------


async def test_f1_e2e_live_turn_facts_survive_duplicate_tokens(world):
    world.install_sglang_stub()
    from miles.rollout.base_types import GenerateFnInput, GenerateFnOutput
    from miles.rollout.inference_rollout.compatibility import load_generate_function
    from miles.utils.sampling_mask import RolloutSamplingMask

    from repoharness2.adapters.slime import (
        RolloutOrchestrator,
        SlimeBindingConfig,
    )
    from repoharness2.adapters.slime import capture_wire as cw
    from repoharness2.adapters.slime.bringup import bringup_leaf_facts
    from repoharness2.adapters.slime.generate import _mask1_runs, _match_turns_to_runs

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
            policy_version="3",
        )

        adapter_holder: dict = {}

        def adapter_factory(hook, session_defaults):
            assert session_defaults.get("return_sampling_mask") is True
            adapter = _make_identity_wire_adapter(
                registry, hook, session_defaults, adapter_holder
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

        orchestrator = RolloutOrchestrator(
            config=config,
            task_resolver=task,
            adapter_factory=adapter_factory,
            harness_driver=Driver(),
            grading_submit=grading_submit,
            docker=_make_fake_docker(),
            # F1 差异点：生产 bringup_leaf_facts（身份 span 读出）
            leaf_facts_fn=bringup_leaf_facts,
            session_poison_check=registry.poison.is_poisoned,
            capture_boundary_check=registry.assert_session_clean,
        )

        fn = load_generate_function(
            "repoharness2.adapters.miles.generate_fn.Rh2MilesGenerateFn"
        )
        args = Namespace(
            rh2_orchestrator=orchestrator,
            rollout_top_p=0.8,
            rh2_engine_sampling_mask=True,
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

        hook = adapter_holder["hook"]
        cap_first, cap_dropped, cap_live = [r.record_id for r in hook.records]

        # ===== ① 对照：旧 matcher 在同一事实上必然错绑掉落轮（F1 反例）====
        legacy_runs = _mask1_runs(LEAF_LOSS_MASK)
        _per_run, legacy_used = _match_turns_to_runs(
            LEAF_TOKENS[-len(LEAF_LOSS_MASK):], legacy_runs, hook.tapes
        )
        assert [t.record_id for t in legacy_used] == [cap_first, cap_dropped]
        assert [t.weight_version for t in legacy_used] == ["1", "2"]  # 错误形状

        # ===== ② commit 时刻绑定账：三轮全部正向登记 =======================
        assert adapter_holder["bindings"] == {
            1: cap_first, 2: cap_dropped, 3: cap_live,
        }
        assert registry.stats["staged"] == 3 and registry.stats["committed"] == 3

        # ===== ③ 交付样本：活轮事实精确胜出 ================================
        assert isinstance(out, GenerateFnOutput)
        (delivered,) = out.samples
        assert delivered.status is world.MS.Status.COMPLETED
        assert delivered.reward == 1.0 and grading_calls
        assert delivered.tokens == list(LEAF_TOKENS)
        assert delivered.loss_mask == list(LEAF_LOSS_MASK)
        # version 事实：["1","3"]——掉落轮 v2 绝不混入（F1 修复核心断言）
        assert delivered.weight_versions == ["1", "3"]
        # 行为 logprob：活轮位 = -0.30（掉落轮 -0.20 出现即复发）
        assert delivered.rollout_log_probs == LEAF_LOGPROBS
        # support 事实：活轮位 = {21,800}（掉落轮 {21,700} 出现即复发）
        mask = delivered.rollout_sampling_mask
        assert isinstance(mask, RolloutSamplingMask)
        mask_ids, mask_offsets = mask._as_tensors()
        assert mask_ids.tolist() == EXPECTED_MASK_IDS
        assert mask_offsets.tolist() == EXPECTED_MASK_OFFSETS

        # ===== ④ projection：capture 回链 = [first, live] ==================
        audit = orchestrator.audits[0]
        assert audit.steps[-1] == "step9_samples_delivered"
        projection = audit.finalized.projection
        (branch,) = projection.branches
        assert branch.capture_record_refs == [cap_first, cap_live]
        assert branch.sampling_mask.mask_kind == "sampler_support_token_ids"
        assert branch.logprob_provenance.normalization == "behavior_support_normalized"
        # 两个入训轮版本不同（1/3）——单一 weight_version 无事实，诚实 None
        assert branch.logprob_provenance.weight_version is None

        # ===== ⑤ miles 训练面：buffer -> conversion ========================
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
            rollout_top_p=0.8,
        )
        recycled: list = []
        buf = DefaultDataBuffer(
            DataBufferConstructorInput(args=margs, unused_handler_fn=recycled.append)
        )
        await buf.put(DataBufferInput(prompt_group=[miles_input], group=[[delivered]]))
        got = await buf.get(current_version=4)
        assert recycled == []
        data, metadata = postprocess_rollout_data(margs, [got.group], None)
        td = convert_samples_to_train_data(margs, data, metadata, None, None)
        assert td["loss_masks"] == [LEAF_LOSS_MASK]
        assert td["rollout_log_probs"] == [LEAF_LOGPROBS]
        (ids_tensor,) = td["rollout_sampling_mask_ids"]
        (offsets_tensor,) = td["rollout_sampling_mask_offsets"]
        assert ids_tensor.tolist() == EXPECTED_MASK_IDS
        assert offsets_tensor.tolist() == EXPECTED_MASK_OFFSETS
    finally:
        cw.aiohttp = saved_aiohttp
