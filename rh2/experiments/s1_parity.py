"""S1-8 parity 脚本：parity-core（token 逐位）与 parity-cross（治理事实级）。

两类 parity 的判据（补充条款 C1 的拆分，验收级）：

parity-core —— **E8 解耦证据本体**：同一批 S1-6 mock 链产出（真实
GenerationCaptureHook / backfill / project_from_slime / finalize_rollout 全链，
只有 docker/harness/SGLang 响应/评分提交是接口同形替身），分两路消费：
  A 路 = slime 在线消费形状（rh2_custom_generate 交付的叶链 Sample：
        tokens / loss_mask / rollout_log_probs / reward / metadata 派生视图键）；
  B 路 = 离线导出（FinalizedRollout -> TrainingExportRecord + artifacts 字节流）。
判据：token ids / loss mask / rollout logprobs / reward facts **逐位一致**，
manifest digest 全部重算命中，重复导出逐字节幂等。

parity-cross —— 跨框架治理一致性：S0-3 真实 verifiers Trace（EvalClient 文本
中继）经 project_from_verifiers，与 slime mock 链经 project_from_slime，都走
同一个 finalize_rollout 关口。**只比治理事实 / RewardFacts / eligibility /
logprob_source / provenance 的结构与语义，token 不比**（renderer/tokenizer/
template 不同，逐位没有意义）。判据分两半：
  - 共享治理面必须一致：reward_scope / security_and_leakage / clean_grading
    三维两路都 ok；RewardFacts 的 scope/raw_reward/credit 策略逐值相等、
    reward_event_refs 各自指向本路评分报告；扫描器版本与 clean 结论一致；
  - 路径差异必须**恰好**落在声明的降级点：verifiers 路 logprob_alignment 失败
    （logprob_missing）、loss_mask_integrity 失败（no_trainable_tokens）、
    policy_staleness 失败（staleness_facts_missing，文本中继无握手事实）；
    slime 路三维全 ok。资格结论：slime = offline_or_sft_candidate（S1 封顶），
    verifiers = audit_only_or_rejected（并被离线导出拒收，audit 门生效）。

运行：cd rh2 && uv run python experiments/s1_parity.py
（tests/adapters/test_s1_parity.py 用 importlib 按路径加载本模块复跑同一批断言。）
"""

from __future__ import annotations

import asyncio
import base64
import dataclasses
import hashlib
import json
import struct
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repoharness2.adapters.offline_export import (
    OfflineExportError,
    OfflineExportInput,
    export_rollouts,
)
from repoharness2.adapters.slime import (
    GenerationCaptureHook,
    RolloutOrchestrator,
    RolloutTaskSpec,
    SlimeBindingConfig,
)
from repoharness2.adapters.verifiers_projection import (
    EVAL_RELAY_RENDERER_CLS_NAME,
    VerifiersProjectionError,
    VerifiersRewardInput,
    project_from_verifiers,
)
from repoharness2.contracts import GradingReport, canonical_json_digest
from repoharness2.governance import finalize_rollout
from repoharness2.grading.manager import ExecResult, GradingEnvSpec, HygieneRules

REPO_ROOT = Path(__file__).resolve().parents[2]
DUMP_DIR = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s0/toy_trace_dump"

# S0-3 的 6 份可投影 dump（EvalClient 文本中继，共 12 条 Trace）；
# 第 7 份 default_subprocess_deepseek_attempt.json 是缺 key 的 error 轨迹
# （nodes=0，无分支），是 fail-closed 拒收路径的真实样本。
PROJECTABLE_DUMPS = (
    "default_docker.json",
    "default_subprocess.json",
    "default_subprocess_deepseek.json",
    "default_subprocess_maxturns1.json",
    "null_docker.json",
    "null_subprocess.json",
)
REJECT_DUMP = "default_subprocess_deepseek_attempt.json"

BASE_COMMIT = "a" * 40
SHA_TEMPLATE = "sha256:" + "a" * 64
SHA_BUNDLE = "sha256:" + "e" * 64
TS = "2026-07-07T09:30:25Z"
EXPORT_STAMP = datetime(2026, 7, 8, 3, 0, 0, tzinfo=timezone.utc)  # 幂等对照用固定时间戳


# ---------------------------------------------------------------------------
# S1-6 mock 链替身（接口形状与 tests/adapters/test_slime_generate.py 逐一对照；
# 真实代码路径——capture 钩子/回填/投影/治理关口——全部走生产模块）
# ---------------------------------------------------------------------------


def b64_int32(values: list[int]) -> str:
    return base64.b64encode(struct.pack(f"<{len(values)}i", *values)).decode("ascii")


def topp_offsets(per_token_kept: list[int]) -> list[int]:
    offsets = [0]
    for kept in per_token_kept:
        offsets.append(offsets[-1] + kept)
    return offsets


def routing_flat(rows: int, layers: int, topk: int) -> list[int]:
    return [(i * 13 + 7) % 128 for i in range(rows * layers * topk)]


@dataclasses.dataclass
class ScriptSample:
    """slime Sample 的 duck 型替身（字段名与 slime/utils/types.py 逐一对应）。"""

    tokens: list[int] = dataclasses.field(default_factory=list)
    response_length: int = 0
    loss_mask: list[int] | None = None
    rollout_log_probs: list[float] | None = None
    rollout_top_p_token_ids: Any = None
    rollout_top_p_token_offsets: Any = None
    rollout_routed_experts: Any = None
    weight_versions: list[str] = dataclasses.field(default_factory=list)
    rollout_id: int | None = None
    index: int | None = None
    status: str = "completed"
    remove_sample: bool = False
    metadata: dict = dataclasses.field(default_factory=dict)


@dataclass
class FakeDocker:
    base_commit: str = BASE_COMMIT
    writes: dict[str, bytes] = field(default_factory=dict)
    removed: list[str] = field(default_factory=list)

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        cmd = args[0]
        if cmd == "image":
            return ExecResult(0, "sha256:" + "ab" * 32 + "\n", "")
        if cmd == "run":
            return ExecResult(0, "f00dfeedcafe\n", "")
        if cmd == "rm":
            self.removed.append(args[-1])
            return ExecResult(0, "", "")
        if cmd == "exec":
            script = args[-1]
            if "rev-parse HEAD" in script:
                return ExecResult(
                    0, f"HEAD={self.base_commit}\nBASE_OBJECT_OK\nPARENT=none\nDIFFSTAT=\n", ""
                )
            if "cat > " in script:
                self.writes[script.rsplit("cat > ", 1)[1].strip()] = input_bytes or b""
                return ExecResult(0, "", "")
            return ExecResult(0, "", "")
        raise AssertionError(f"FakeDocker 不认识的命令: {args}")


def sglang_response(
    *,
    rid: str,
    output_ids: list[int],
    finish: str = "stop",
    top_p_ids: list[int] | None = None,
    top_p_offsets: list[int] | None = None,
    routed_flat: list[int] | None = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "id": rid,
        "finish_reason": {"type": finish},
        "output_token_logprobs": [
            [-(i + 1) * 0.05, token_id, None] for i, token_id in enumerate(output_ids)
        ],
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


class MockAdapter:
    """slime BaseAdapter 接口形状（open/finish/drop）；逐轮喂真实 capture 钩子。"""

    def __init__(self, hook: GenerationCaptureHook, defaults: dict, turns: list[MockTurn], leaves: list[Any]):
        self.hook = hook
        self.defaults = defaults
        self.turns = turns
        self.leaves = leaves

    def open_session(
        self, sid: str, *, sampling_defaults=None, max_context_tokens: int = 0,
        physical_attempt_id: str | None = None,  # F2-1a：paid 经 open 事务传入
        capability_token: str | None = None,  # F2-2：认证映射（parity mock 不用）
        deadline_monotonic: float | None = None,  # 批 B（I03）：episode 期限显式下传（parity mock 不用）
    ) -> None:
        pass

    async def run_all_turns(self) -> None:
        for turn in self.turns:
            self.hook.on_generate_response(
                prompt_token_ids=turn.prompt_ids, sampling_params=self.defaults, response=turn.response
            )

    async def finish_session(self, sid: str, *, base_sample, reward: float = 0.0, extra_metadata=None, wait_timeout: float = 5.0):
        return list(self.leaves)

    async def drop_session(self, sid: str, *, wait_timeout: float = 5.0) -> None:
        pass


class MockDriver:
    """slime BaseHarness.run 关键字签名的替身。"""

    name = "mock_harness"

    def __init__(self, adapter_ref: dict[str, MockAdapter]):
        self.adapter_ref = adapter_ref

    async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt) -> int:
        await self.adapter_ref["adapter"].run_all_turns()
        return 0


def resolved_grading_report(trajectory_id: str, task_id: str) -> GradingReport:
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


def make_task(task_id: str) -> RolloutTaskSpec:
    return RolloutTaskSpec(
        task_id=task_id,
        image="fake-image:v1",
        base_commit=BASE_COMMIT,
        prompt=f"Fix the issue in {task_id}",
        public_bundle_payload=json.dumps({"instance_id": task_id}).encode(),
        public_bundle_digest=SHA_BUNDLE,
        image_local_build=True,  # fake 镜像无 RepoDigests：显式豁免运行期 digest 比对
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


# dense 两轮形状（S1-6 fixture 同形）：prompt 12 + 生成 10 + 工具 5 + 生成 8。
D_PROMPT, D_GEN1, D_TOOL, D_GEN2 = 12, 10, 5, 8
D_TOKENS = (
    [1500 + i for i in range(D_PROMPT)]
    + [2500 + i for i in range(D_GEN1)]
    + [3500 + i for i in range(D_TOOL)]
    + [4500 + i for i in range(D_GEN2)]
)


@dataclass
class Chain:
    orchestrator: RolloutOrchestrator
    adapter_ref: dict[str, MockAdapter]
    docker: FakeDocker
    base_sample: ScriptSample


def build_chain(*, moe: bool, infra_grading: bool = False) -> Chain:
    """组装 mock 链：dense 两轮 或 MoE 单轮探针形状（uh_probe 15/16）。"""

    if moe:
        task_id = "django__django-11099"
        prompt_ids = [1000 + i for i in range(15)]
        gen_ids = [2000 + i for i in range(16)]
        turns = [
            MockTurn(
                prompt_ids=prompt_ids,
                response=sglang_response(
                    rid="rid_moe",
                    output_ids=gen_ids,
                    top_p_ids=list(range(100000, 100057)),
                    top_p_offsets=topp_offsets([4] * 9 + [3] * 7),
                    routed_flat=routing_flat(15 - 1 + 16, 48, 8),
                ),
            )
        ]
        leaves = [
            ScriptSample(
                tokens=prompt_ids + gen_ids,
                response_length=16,
                loss_mask=[1] * 16,
                # 与 mock SGLang 响应的 output_token_logprobs 逐位同源（真实链路里
                # TrajectoryManager 与 capture 钩子读的是同一份 meta_info；两处填
                # 不同数值的 fixture 正是 parity-core 能当场抓出来的漂移形态）。
                rollout_log_probs=[-(i + 1) * 0.05 for i in range(16)],
                rollout_id=7,
                index=0,
            )
        ]
        config = SlimeBindingConfig(
            model_name="Qwen/Qwen3-30B-A3B",
            backend_version="0.5.9",
            renderer_cls_name="Qwen3Renderer",
            expected_renderer_cls_name="Qwen3Renderer",
            tokenizer_name="Qwen/Qwen3-30B-A3B",
            template_hash=SHA_TEMPLATE,
            adapter_url="http://10.0.0.1:18001",
            harness_name="mock_harness",
            expect_moe_routing=True,
            moe_num_layers=48,
            moe_router_topk=8,
            policy_version="step_0",
        )
    else:
        task_id = "psf__requests-2931"
        gen1 = D_TOKENS[D_PROMPT : D_PROMPT + D_GEN1]
        gen2 = D_TOKENS[D_PROMPT + D_GEN1 + D_TOOL :]
        turns = [
            MockTurn(
                prompt_ids=D_TOKENS[:D_PROMPT],
                response=sglang_response(
                    rid="rid_t0",
                    output_ids=gen1,
                    finish="tool_calls",
                    top_p_ids=list(range(120000, 120000 + 3 * D_GEN1)),
                    top_p_offsets=topp_offsets([3] * D_GEN1),
                ),
            ),
            MockTurn(
                prompt_ids=D_TOKENS[: D_PROMPT + D_GEN1 + D_TOOL],
                response=sglang_response(
                    rid="rid_t1",
                    output_ids=gen2,
                    top_p_ids=list(range(121000, 121000 + 3 * D_GEN2)),
                    top_p_offsets=topp_offsets([3] * D_GEN2),
                ),
            ),
        ]
        leaves = [
            ScriptSample(
                tokens=list(D_TOKENS),
                response_length=D_GEN1 + D_TOOL + D_GEN2,
                loss_mask=[1] * D_GEN1 + [0] * D_TOOL + [1] * D_GEN2,
                rollout_log_probs=(
                    [-(i + 1) * 0.05 for i in range(D_GEN1)]
                    + [0.0] * D_TOOL
                    + [-(i + 1) * 0.05 for i in range(D_GEN2)]
                ),
                rollout_id=3,
                index=0,
            )
        ]
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
            policy_version="step_0",
        )

    docker = FakeDocker()
    adapter_ref: dict[str, MockAdapter] = {}

    def adapter_factory(hook: GenerationCaptureHook, defaults: dict[str, Any]):
        adapter = MockAdapter(hook, defaults, turns, leaves)
        adapter_ref["adapter"] = adapter
        return adapter

    async def grading_submit(*, trajectory_id: str, workspace: Any, spec: GradingEnvSpec, **kw):
        if infra_grading:
            return GradingReport.model_validate(
                {
                    "report_id": f"rpt_{trajectory_id}",
                    "trajectory_id": trajectory_id,
                    "task_id": spec.task_id,
                    "grader_name": "swebench_official_parser",
                    "grader_version": "swebench-4.1.0",
                    "outcome": "failed_to_grade",
                    "failure_category": "infra_failure",
                    "reward": None,
                    "infra_failure_detail": "grading_container_killed_oom",
                    "graded_at_utc": TS,
                }
            )
        return resolved_grading_report(trajectory_id, spec.task_id)

    orchestrator = RolloutOrchestrator(
        config=config,
        task_resolver=make_task(task_id),
        adapter_factory=adapter_factory,
        harness_driver=MockDriver(adapter_ref),
        grading_submit=grading_submit,
        docker=docker,
    )
    return Chain(orchestrator, adapter_ref, docker, ScriptSample(index=0))


SAMPLING_PARAMS = {"temperature": 1.0, "top_p": 0.95, "max_new_tokens": 4096}


async def _run_chain(chain: Chain) -> list[Any]:
    class _Args:
        rh2_orchestrator = chain.orchestrator

    from repoharness2.adapters.slime import rh2_custom_generate

    return await rh2_custom_generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))


# ---------------------------------------------------------------------------
# parity-core：slime 在线消费形状 vs 离线导出，token 逐位
# ---------------------------------------------------------------------------


def _decode_bin_int32(path: Path) -> list[int]:
    payload = path.read_bytes()
    return list(struct.unpack(f"<{len(payload) // 4}i", payload))


def _decode_bin_f64(path: Path) -> list[float]:
    payload = path.read_bytes()
    return list(struct.unpack(f"<{len(payload) // 8}d", payload))


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _core_compare_one(chain: Chain, out_dir: Path, label: str) -> dict[str, Any]:
    """一条链的两路比对：断言失败直接抛 AssertionError（parity 不允许带病通过）。"""

    delivered = asyncio.run(_run_chain(chain))
    audit = chain.orchestrator.audits[-1]
    assert audit.finalized is not None, f"{label}: 链没有产出 FinalizedRollout"
    (leaf,) = delivered
    assert leaf.remove_sample is False, f"{label}: 在线路样本被剔除，无从比对"
    hook = chain.adapter_ref["adapter"].hook

    manifest = export_rollouts(
        [
            OfflineExportInput(
                finalized=audit.finalized,
                capture_records=hook.records,
                artifact_store=hook.artifact_store,
            )
        ],
        out_dir=out_dir,
        exported_at_utc=EXPORT_STAMP,
    )
    record = json.loads((out_dir / "records.jsonl").read_text().splitlines()[0])
    (branch,) = record["branches"]
    art = out_dir / "artifacts"

    # --- token ids / loss mask / logprobs 逐位一致（E8 证据本体）---
    exported_tokens = _decode_bin_int32(art / (branch["token_ids_ref"]["ref_id"] + ".bin"))
    exported_mask = _decode_bin_int32(art / (branch["loss_mask_ref"]["ref_id"] + ".bin"))
    exported_lp = _decode_bin_f64(art / (branch["rollout_logprobs_ref"]["ref_id"] + ".bin"))
    assert exported_tokens == list(leaf.tokens), f"{label}: token ids 两路不一致"
    assert exported_mask == list(leaf.loss_mask), f"{label}: loss mask 两路不一致"
    assert exported_lp == list(leaf.rollout_log_probs), f"{label}: rollout logprobs 两路不一致"

    # --- reward facts 逐位一致 ---
    projection = audit.finalized.projection
    assert record["reward_facts"] == projection.reward_facts.model_dump(mode="json"), (
        f"{label}: 导出 reward_facts 与投影不一致"
    )
    assert leaf.reward == record["reward_facts"]["raw_reward"] == 1.0, f"{label}: reward 数值不一致"

    # --- 宿主派生视图键与导出记录互检 ---
    assert leaf.metadata["eligibility_report_ref"] == record["eligibility_report_ref"]
    assert leaf.metadata["training_eligibility_class"] == record["training_eligibility_class"]
    # A3（W1b 第二段）：S1 封顶已删除，s1_compat 七维全过 = online（T1 oracle 改动）
    assert record["training_eligibility_class"] == "online_policy_loss_eligible"

    # --- manifest digest 全部重算命中 ---
    line = (out_dir / "records.jsonl").read_text().splitlines()[0]
    assert canonical_json_digest(json.loads(line)) == manifest.records[0]["sha256"]
    for ref_id, digest in manifest.artifacts.items():
        assert _sha256_file(art / f"{ref_id}.bin") == digest, f"{label}: artifact digest 不符 {ref_id}"
    assert manifest.records_jsonl_sha256 == _sha256_file(out_dir / "records.jsonl")

    # --- 幂等：同输入重导出逐字节相同 ---
    second_dir = out_dir.parent / (out_dir.name + "_again")
    manifest2 = export_rollouts(
        [
            OfflineExportInput(
                finalized=audit.finalized,
                capture_records=hook.records,
                artifact_store=hook.artifact_store,
            )
        ],
        out_dir=second_dir,
        exported_at_utc=EXPORT_STAMP,
    )
    assert manifest2.to_json_dict() == manifest.to_json_dict(), f"{label}: 重复导出 manifest 漂移"
    assert (second_dir / "records.jsonl").read_bytes() == (out_dir / "records.jsonl").read_bytes()

    return {
        "label": label,
        "trajectory_id": record["trajectory_id"],
        "token_count": len(exported_tokens),
        "trainable_token_count": branch["trainable_token_count"],
        "reward": record["reward_facts"]["raw_reward"],
        "eligibility_class": record["training_eligibility_class"],
        "records_jsonl_sha256": manifest.records_jsonl_sha256,
        "token_bitwise_equal": True,
        "loss_mask_bitwise_equal": True,
        "logprobs_bitwise_equal": True,
        "reward_facts_bitwise_equal": True,
        "idempotent_reexport": True,
    }


def run_parity_core(work_dir: Path | None = None) -> dict[str, Any]:
    """parity-core 主入口：dense 两轮 + MoE 探针形状各比一条，另验 audit 拒收门。"""

    base = Path(work_dir) if work_dir is not None else Path(tempfile.mkdtemp(prefix="rh2_s1_parity_core_"))
    results = [
        _core_compare_one(build_chain(moe=False), base / "dense", "dense_2turn"),
        _core_compare_one(build_chain(moe=True), base / "moe", "moe_probe_15_16"),
    ]

    # audit 档拒收门：infra 评分 -> gate 降级 audit -> 导出器 fail-closed。
    infra_chain = build_chain(moe=False, infra_grading=True)
    asyncio.run(_run_chain(infra_chain))
    infra_audit = infra_chain.orchestrator.audits[-1]
    assert infra_audit.finalized is not None
    assert infra_audit.finalized.eligibility_report.eligibility_class == "audit_only_or_rejected"
    try:
        export_rollouts(
            [
                OfflineExportInput(
                    finalized=infra_audit.finalized,
                    capture_records=infra_chain.adapter_ref["adapter"].hook.records,
                    artifact_store=infra_chain.adapter_ref["adapter"].hook.artifact_store,
                )
            ],
            out_dir=base / "audit_refused",
            exported_at_utc=EXPORT_STAMP,
        )
        raise AssertionError("audit 档样本竟然被导出了（资格门失效）")
    except OfflineExportError as exc:
        assert exc.reason_code == "audit_tier_not_exportable", exc

    return {"parity_core_pass": True, "chains": results, "audit_tier_refused": True}


# ---------------------------------------------------------------------------
# parity-cross：verifiers 路 vs slime 路（治理事实级，token 不比）
# ---------------------------------------------------------------------------

CROSS_TRACE_DUMP = "default_subprocess_deepseek.json"  # 真实 provider（deepseek-chat）的 3 轮轨迹
CROSS_TRACE_INDEX = 0


def _load_dump(name: str) -> dict[str, Any]:
    return json.loads((DUMP_DIR / name).read_text())


async def _finalize_verifiers_trace(trace: dict[str, Any], model_name: str):
    """verifiers Trace 走同一个治理关口（grade -> project -> gate）。"""

    trace_id = trace["id"]
    task_id = trace["task"]["name"]
    report = resolved_grading_report(trace_id, task_id)
    reward = VerifiersRewardInput(
        reward_scope="trace_level",
        raw_reward=report.reward,
        reward_event_refs=[report.report_id],
        credit_assignment_strategy="direct_trace_reward",
    )
    return await finalize_rollout(
        grade=lambda: report,
        project=lambda rpt: project_from_verifiers(
            trace, model_name=model_name, reward=reward
        ),
        capture_records=(),  # 文本中继没有 GenerationCaptureRecord——这就是被比对的事实
        handshake=None,  # 无训练后端握手事实：policy_staleness 维按 fail-closed 失败
        # 前置清理批（D2-2，2026-09-04）：每轨迹 sandbox 能力事实证明系统已删，security 维
        # 只判执行级事实——不再需要 s1/verifiers 对照路径显式声明"不要求能力事实"。
    )


def _dim(report, name: str):
    return getattr(report.facts, name)


def run_parity_cross() -> dict[str, Any]:
    # slime 路：mock 链全链产出。
    slime_chain = build_chain(moe=False)
    asyncio.run(_run_chain(slime_chain))
    slime_fin = slime_chain.orchestrator.audits[-1].finalized
    assert slime_fin is not None

    # verifiers 路：S0-3 真实 deepseek 轨迹（3 轮工具往返）走同一关口。
    dump = _load_dump(CROSS_TRACE_DUMP)
    trace = dump["traces"][CROSS_TRACE_INDEX]
    verif_fin = asyncio.run(_finalize_verifiers_trace(trace, dump["meta"]["model"]))

    s_rep, v_rep = slime_fin.eligibility_report, verif_fin.eligibility_report
    s_proj, v_proj = slime_fin.projection, verif_fin.projection

    # 1. 治理层看到的是同一个契约：schema / 关口产物结构完全一致。
    #    （D2-4：projection 扫描已不是关口的一步，FinalizedRollout 无 scan_result。）
    assert s_proj.schema_id == v_proj.schema_id == "rh2.trajectory_projection.v1"
    assert s_proj.source_framework == "slime" and v_proj.source_framework == "verifiers"
    assert not hasattr(slime_fin, "scan_result") and not hasattr(verif_fin, "scan_result")
    assert s_rep.gate_version == v_rep.gate_version  # 同一个 gate 实现判两路

    # 2. RewardFacts 语义一致（逐字段）：scope / 数值 / 出处规则 / 信用策略。
    s_rf, v_rf = s_proj.reward_facts, v_proj.reward_facts
    assert s_rf.reward_scope == v_rf.reward_scope == "trace_level"
    assert s_rf.raw_reward == v_rf.raw_reward == 1.0
    assert s_rf.credit_assignment_strategy == v_rf.credit_assignment_strategy == "direct_trace_reward"
    assert s_rf.reward_event_refs == [slime_fin.grading_report.report_id]
    assert v_rf.reward_event_refs == [verif_fin.grading_report.report_id]
    assert s_rf.segment_count == len(s_proj.branches) and v_rf.segment_count == len(v_proj.branches)

    # 3. 共享治理维两路必须同过（评分/泄漏/reward 语义与来源框架无关）。
    for name in ("reward_scope", "security_and_leakage", "clean_grading"):
        assert _dim(s_rep, name).ok and _dim(v_rep, name).ok, f"共享治理维 {name} 两路应全过"

    # 4. 路径差异必须恰好落在声明的降级点（多一处少一处都算 parity 失败）。
    assert _dim(s_rep, "logprob_alignment").ok
    assert _dim(v_rep, "logprob_alignment").reason_codes == ["logprob_missing"]
    assert _dim(s_rep, "loss_mask_integrity").ok
    assert _dim(v_rep, "loss_mask_integrity").reason_codes == ["no_trainable_tokens"]
    assert _dim(s_rep, "policy_staleness").ok
    assert _dim(v_rep, "policy_staleness").reason_codes == ["staleness_facts_missing"]
    assert _dim(s_rep, "token_provenance").ok and _dim(v_rep, "token_provenance").ok

    # 5. logprob_source / provenance：slime 路 token-faithful，verifiers 路显式降级。
    s_branch, v_branch = s_proj.branches[0], v_proj.branches[0]
    assert s_branch.logprob_alignment_status == "aligned_per_token"
    assert s_branch.logprob_provenance is not None and s_branch.logprob_provenance.engine_name == "sglang"
    assert v_branch.logprob_alignment_status == "missing" and v_branch.logprob_provenance is None
    assert s_branch.sampling_mask.mask_kind == "top_p_kept_token_ids"
    assert v_branch.sampling_mask.mask_kind == "not_captured_text_relay"
    assert v_branch.sampling_mask.top_p is None
    assert s_branch.routing.alignment == "not_applicable_dense_model"
    assert v_branch.routing.alignment == "not_captured_text_relay"
    assert s_branch.capture_record_refs and not v_branch.capture_record_refs
    assert v_proj.renderer_cls_name == EVAL_RELAY_RENDERER_CLS_NAME
    assert v_proj.tokenizer_name.startswith("eval_relay_untokenized:")

    # 6. 资格结论：slime = online（A3 起无封顶，s1_compat 不要求能力事实）；verifiers = audit
    #    （并被导出拒收）。
    assert s_rep.eligibility_class == "online_policy_loss_eligible"
    assert s_rep.reason_codes == []
    assert v_rep.eligibility_class == "audit_only_or_rejected"
    try:
        export_rollouts(
            [OfflineExportInput(finalized=verif_fin, capture_records=(), artifact_store={})],
            out_dir=Path(tempfile.mkdtemp(prefix="rh2_s1_cross_refuse_")),
            exported_at_utc=EXPORT_STAMP,
        )
        raise AssertionError("verifiers 文本中继轨迹（audit 档）竟然被导出了")
    except OfflineExportError as exc:
        assert exc.reason_code == "audit_tier_not_exportable"

    return {
        "parity_cross_pass": True,
        "cross_trace": {"dump": CROSS_TRACE_DUMP, "trace_id": trace["id"], "task": trace["task"]["name"]},
        "shared_dims_agree": ["reward_scope", "security_and_leakage", "clean_grading"],
        "expected_divergence": {
            "logprob_alignment": ["logprob_missing"],
            "loss_mask_integrity": ["no_trainable_tokens"],
            "policy_staleness": ["staleness_facts_missing"],
        },
        "slime_class": s_rep.eligibility_class,
        "verifiers_class": v_rep.eligibility_class,
        "verifiers_export_refused": True,
    }


# ---------------------------------------------------------------------------
# 6 份真实 toy dump 全量投影 + 第 7 份 error dump 的 fail-closed 拒收
# ---------------------------------------------------------------------------


def run_toy_dump_projection() -> dict[str, Any]:
    per_dump: list[dict[str, Any]] = []
    total_traces = 0
    for name in PROJECTABLE_DUMPS:
        dump = _load_dump(name)
        model = dump["meta"]["model"]
        summaries = {s["task_idx"]: s for s in dump["meta"]["summaries"]}
        rows = []
        for trace in dump["traces"]:
            projection = project_from_verifiers(trace, model_name=model)
            (branch,) = projection.branches
            # 降级标注逐项核对（不 token-faithful 的显式形态）
            assert branch.sampling_mask.mask_kind == "not_captured_text_relay"
            assert branch.sampling_mask.top_p is None
            assert branch.routing.alignment == "not_captured_text_relay"
            assert branch.logprob_alignment_status == "missing"
            assert all(span.mask == 0 for span in branch.loss_mask_spans)
            sampled_reasons = {
                span.reason
                for span in branch.loss_mask_spans
                if any(
                    ts.source_type == "sampled_assistant" and ts.start == span.start
                    for ts in branch.token_spans
                )
            }
            assert sampled_reasons == {"token_capture_unavailable_downgraded"}
            assert projection.renderer_cls_name == EVAL_RELAY_RENDERER_CLS_NAME
            # 外部一致性：采样段 token 计数之和 == dump 顶层 num_output_tokens
            sampled_total = sum(
                ts.end - ts.start for ts in branch.token_spans if ts.source_type == "sampled_assistant"
            )
            summary = summaries[trace["task"]["idx"]]
            assert sampled_total == summary["num_output_tokens"], (
                f"{name}/{trace['id'][:8]}: 采样计数 {sampled_total} != "
                f"summary num_output_tokens {summary['num_output_tokens']}"
            )
            assert projection.reward_facts.raw_reward == summary["reward"]
            rows.append(
                {
                    "trace_id": trace["id"][:8],
                    "task": trace["task"]["name"],
                    "prompt_tokens": branch.prompt_token_count,
                    "response_tokens": branch.response_token_count,
                    "sampled_tokens": sampled_total,
                    "reward": projection.reward_facts.raw_reward,
                }
            )
            total_traces += 1
        per_dump.append({"dump": name, "model": model, "traces": rows})

    # 第 7 份：缺 key 的 error 轨迹（nodes=0）必须 fail-closed 拒收，不产投影。
    reject = _load_dump(REJECT_DUMP)
    reject_reasons = []
    for trace in reject["traces"]:
        try:
            project_from_verifiers(trace, model_name=reject["meta"]["model"])
            raise AssertionError(f"{REJECT_DUMP}/{trace['id'][:8]}: error 轨迹竟然投影成功")
        except VerifiersProjectionError as exc:
            assert exc.reason_code == "trace_has_no_branches", exc
            reject_reasons.append(exc.reason_code)

    return {
        "toy_dump_projection_pass": True,
        "projectable_dumps": len(PROJECTABLE_DUMPS),
        "projected_traces": total_traces,
        "per_dump": per_dump,
        "reject_dump": {
            "dump": REJECT_DUMP,
            # 报告侧去重（保序，F5 尾巴）：同一理由码每条被拒轨迹都会追加一次，
            # 逐条计数由 rejected_traces 承担，reason_codes 只报"出现过哪些理由"。
            "reason_codes": list(dict.fromkeys(reject_reasons)),
            "rejected_traces": len(reject_reasons),
        },
    }


def main() -> dict[str, Any]:
    result = {
        "parity_core": run_parity_core(),
        "parity_cross": run_parity_cross(),
        "toy_dumps": run_toy_dump_projection(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    main()
