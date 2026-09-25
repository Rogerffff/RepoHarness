"""R2E 接线 R-e 组级运输：同一批里一个 SWE 组 + 一个 R2E 组经**真实 miles `DefaultDataBuffer`**进入真实转换；
混来源组在 put() 被拒。

单成员运输（`r2e_expected_map` 报告 → RewardFacts → gate → Outcome v2 → 交付叶）见
tests/adapters/test_r2e_transport.py；本模块是那里点名留给 tests/adapters_miles 的组级两例，形状同评审探针
r2e_local_review_20260922/probes/training_transport_probe.py 的 `run_groups`::

    trusted-prep（一题 SWE + 一题 R2E，tests/r2e_synthetic_tasks.py）→ stock miles Dataset + RolloutDataSource
      → Rh2MilesGenerateFn → 真实 RolloutOrchestrator（fa_formal，经 prepared face + registry）
      → 真实 SWEGradingManager（grader profile；容器替身 ProfileGraderFakeDocker 给罐头测试日志）→ GradingReport
      → DefaultDataBuffer.put()（rh2_group_admission_filter）→ get() → postprocess_rollout_data
      → convert_samples_to_train_data

报告不手工构造；替身只在容器、冻结屏障、harness 与 session adapter 这些 W1a/W1b 已文档化的注入点。
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))
sys.path.insert(0, str(_HERE.parent / "grading"))
sys.path.insert(0, str(_HERE.parent / "adapters"))
from r2e_synthetic_tasks import R2E_TID, prepare_mixed_swe_and_r2e  # noqa: E402
from sandbox_test_support import make_grader_profile  # noqa: E402
from test_w1a_formal_chain import SAMPLING_PARAMS  # noqa: E402
from test_w1b_group_admission import N, _buffer, _build_chain, _entry, _miles_args  # noqa: E402
from test_w1b_prepared_chain import _dispatch_groups  # noqa: E402
from test_w3a_formal_grading_freeze import make_barrier  # noqa: E402
from test_w3b_grader_profile_unit import GOOD_SETUP_ATTEST, ProfileGraderFakeDocker  # noqa: E402
from w1b_synthetic_tasks import BASE_COMMIT, IMG_DIG, TID1  # noqa: E402


# ---------------------------------------------------------------------------
# 罐头评分日志（形状同评审探针）：成员 slot 0 全对，slot 1 失败
# ---------------------------------------------------------------------------


def _r2e_log(*lines: str, rc: int = 1) -> str:
    """R2E 评分段：pytest -rA 摘要 + RH2 标记行。"""

    counts = {label: sum(line.startswith(prefix + " ") for line in lines)
              for prefix, label in (("PASSED", "passed"), ("FAILED", "failed"), ("ERROR", "error"))}
    summary = ", ".join(f"{n} {label}" for label, n in counts.items() if n) or "no tests ran"
    segment = "=== short test summary info ===\n" + "\n".join(lines) + f"\n=== {summary} in 0.1s ===\n"
    return "RH2_INSTALL_SKIPPED=1\n>>>>> Start Test Output\n" + segment + f">>>>> End Test Output\nRH2_TEST_RC={rc}\n"


R2E_LOGS = (
    # gold：三键逐一命中期望映射（test_x PASSED / test_legacy FAILED / test_env ERROR）
    _r2e_log("PASSED r2e_tests/t.py::TestCore::test_x", "FAILED r2e_tests/t.py::TestCore::test_legacy - known",
             "ERROR r2e_tests/t.py::TestCore::test_env - known"),
    # all_wrong：三键全部与期望不符
    _r2e_log("FAILED r2e_tests/t.py::TestCore::test_x - fail", "PASSED r2e_tests/t.py::TestCore::test_legacy",
             "PASSED r2e_tests/t.py::TestCore::test_env"),
)


def _swe_log(slot: int) -> str:
    status = "PASSED" if slot == 0 else "FAILED"
    return (f">>>>> Start Test Output\n{status} t.py::judge_1\nPASSED t.py::test_ok\n"
            f">>>>> End Test Output\nRH2_TEST_RC={slot}\n")


# ---------------------------------------------------------------------------
# 装配
# ---------------------------------------------------------------------------


R2E_DERIVED_ID = "sha256:" + "d" * 64


def _r2e_overlays_env(fx, tmp_path, monkeypatch) -> None:
    """E09 + D4=B（09-25）：正式 actor 任务面对 R2E 题只用派生镜像，缺覆盖条目即拒。给合成 R2E 题写一条合法的
    覆盖条目，经 `RH2_IMAGE_OVERLAYS_PATH` / `_SHA256` 交给共用的任务面加载（W1b 夹具不显式传覆盖表）。"""

    import hashlib
    from datetime import datetime, timezone

    from repoharness2.adapters.slime.r2e_grading_scripts import R2E_PRIVATE_HIDDEN_TESTS_DIR
    from repoharness2.envpack.environment_overlay import EnvironmentOverlayFacts, EnvironmentOverlayV1
    from repoharness2.envpack.prepared_tasks import load_host_grading_views, load_prepared_rollout_views

    public = load_prepared_rollout_views(fx.prepared_dir, fx.manifest)[R2E_TID].public
    grading = load_host_grading_views(fx.private_dir / "host_grading_views.jsonl",
                                      expected_sha256=fx.manifest.host_grading_artifact_sha256, manifest=fx.manifest)[R2E_TID].grading
    overlay = EnvironmentOverlayV1(
        task_id=R2E_TID, base_image_ref=public.image, base_image_manifest_digest=public.image_manifest_digest,
        derived_image_ref="rh2-r2e-derived/demo:test", derived_image_id=R2E_DERIVED_ID, recipe_id="r2e_derive_v1",
        recipe_sha256="sha256:" + "5" * 64, built_at_utc=datetime(2026, 9, 25, tzinfo=timezone.utc),
        facts=EnvironmentOverlayFacts(interpreter_relocated=True, testbed_owner="root", git_scrubbed=True,
                                      hidden_tests_location=R2E_PRIVATE_HIDDEN_TESTS_DIR,
                                      hidden_tests_tree_sha256=grading.hidden_tests_tree_sha256),
    )
    path = tmp_path / "overlays.jsonl"
    path.write_text(overlay.model_dump_json() + "\n", encoding="utf-8")
    monkeypatch.setenv("RH2_IMAGE_OVERLAYS_PATH", str(path))
    monkeypatch.setenv("RH2_IMAGE_OVERLAYS_SHA256", hashlib.sha256(path.read_bytes()).hexdigest())


class _VenvActivationDocker:
    """R2E 成员的激活探针（任务面声明 `/testbed/.venv` 前缀）按 `.venv` 已激活回答；其余调用原样交给共用替身。
    共用替身默认答 conda testbed（SWE-Gym 的前缀），同一批里 SWE 与 R2E 成员共用一个替身，不能用静态覆盖。"""

    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, name):
        return getattr(self._inner, name)

    async def __call__(self, *args, input_bytes=None):
        from repoharness2.grading.manager import ExecResult

        script = args[-1] if args else ""
        if args and args[0] == "exec" and "rollout-activation-probe" in script and "ACT_EXPECTED_PREFIX=/testbed/.venv" in script:
            facts = {"ACT_EXPECTED_PREFIX": "/testbed/.venv", "ACT_PYTHON": "/testbed/.venv/bin/python",
                     "ACT_SYS_EXECUTABLE": "/testbed/.venv/bin/python", "ACT_SYS_PREFIX": "/testbed/.venv",
                     "ACT_CONDA_DEFAULT_ENV": "", "ACT_VIRTUAL_ENV": "/testbed/.venv", "RH2_ACTIVATION_PROBE_OK": "1"}
            return ExecResult(0, "".join(f"{k}={v}\n" for k, v in facts.items()), "")
        return await self._inner(*args, input_bytes=input_bytes)


def _transport_chain(world, tmp_path, monkeypatch):
    """混来源夹具上的 W1b 链；评分改由真实 SWEGradingManager 完成。返回 (fx, chain, args, reports)，
    reports 按 trajectory id 收集每次评分产出的 GradingReport。"""

    from repoharness2.grading.manager import GradingManagerConfig, SWEGradingManager

    fx = prepare_mixed_swe_and_r2e(tmp_path)
    _r2e_overlays_env(fx, tmp_path, monkeypatch)
    chain = _build_chain(world, tmp_path, grading_kinds={}, fx=fx)
    chain.orchestrator._docker = _VenvActivationDocker(chain.orchestrator._docker)
    chain.orchestrator._runtime_barrier = make_barrier({"src/thing.py": b"def feature(:\n"})
    reports: dict = {}

    async def grading_submit(*, trajectory_id, workspace, spec, frozen_delta=None, **kw):
        assert workspace is None and frozen_delta is not None  # grader 只拿持久化的冻结 delta，不回读 workspace
        slot = int(trajectory_id.rsplit("m", 1)[1])
        log = R2E_LOGS[slot] if spec.task_id == R2E_TID else _swe_log(slot)
        docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=log, repo_digests=("fixture@" + IMG_DIG,))
        n_files = str(len(spec.hygiene.test_files))
        docker.setup_attest = {**GOOD_SETUP_ATTEST, "RH2_SETUP_EXPECTED_TEST_FILES": n_files,
                               "RH2_SETUP_TEST_FILES": n_files}
        manager = SWEGradingManager(
            GradingManagerConfig(sandbox_profile=make_grader_profile(), eval_log_dir=tmp_path / "logs"), docker=docker,
        )
        report = await manager.grade(trajectory_id=trajectory_id, workspace=None, spec=spec, frozen_delta=frozen_delta)
        reports[trajectory_id] = report
        return report

    chain.orchestrator._grading_submit = grading_submit
    args = _miles_args(world, chain)
    args.rollout_batch_size = 2
    args.global_batch_size = 4
    args.rewards_normalization = True
    args.grpo_std_normalization = False
    return fx, chain, args, reports


async def _generate(world, args, prompt_groups) -> list:
    """逐成员走真实 Rh2MilesGenerateFn（一个实例服务全部成员）；成员 = GenerateFnOutput.samples。"""

    from miles.rollout.base_types import GenerateFnInput

    fn = world.Rh2MilesGenerateFn()
    groups = []
    for prompt_group in prompt_groups:
        group = []
        for sample in prompt_group:
            out = await fn(GenerateFnInput(state=SimpleNamespace(args=args), sample=sample,
                                           sampling_params=dict(SAMPLING_PARAMS), evaluation=False))
            group.append(out.samples)
        groups.append(group)
    return groups


# ---------------------------------------------------------------------------
# 验收
# ---------------------------------------------------------------------------


async def test_same_batch_swe_group_and_r2e_group_reach_real_conversion(world, tmp_path, monkeypatch):
    """同一批两组（SWE getmoto__moto-1、R2E demo__fff…，各 n=2，成员 0 全对、成员 1 失败）都过真实 buffer 的
    复合 dynamic filter，经真实 postprocess_rollout_data + convert_samples_to_train_data 进入训练数据。
    两族评分语义并存：R2E 报告带期望映射计数、四个 F2P/P2P 计数全为 None；训练侧只消费 reward。"""

    world.install_sglang_stub()
    from miles.ray.rollout.rollout_data_conversion import postprocess_rollout_data
    from miles.ray.rollout.train_data_conversion import convert_samples_to_train_data

    fx, chain, args, reports = _transport_chain(world, tmp_path, monkeypatch)
    prompt_groups = _dispatch_groups(fx, n=N)
    assert [[s.metadata["task_id"] for s in pg] for pg in prompt_groups] == [[TID1] * N, [R2E_TID] * N]
    groups = await _generate(world, args, prompt_groups)
    assert len(chain.registry) == 0  # attempt 结束即 release

    # 报告出自真实 SWEGradingManager：R2E 走期望映射语义，SWE 走 F2P/P2P 语义
    assert sorted(reports) == ["miles_g0_m0", "miles_g0_m1", "miles_g1_m0", "miles_g1_m1"]
    r2e_gold, r2e_wrong = reports["miles_g1_m0"], reports["miles_g1_m1"]
    assert (r2e_gold.outcome, r2e_gold.reward) == ("resolved", 1.0)
    assert (r2e_wrong.failure_category, r2e_wrong.reward) == ("tests_failed", 0.0)
    assert [r2e_gold.expected_match_count, r2e_gold.expected_total_count] == [3, 3]
    assert [r2e_wrong.expected_match_count, r2e_wrong.expected_total_count] == [0, 3]
    for report in (r2e_gold, r2e_wrong):
        assert report.task_id == R2E_TID and report.grading_semantics == "r2e_expected_map"
        swe_counts = [report.f2p_pass_count, report.f2p_total_count, report.p2p_fail_count, report.p2p_total_count]
        assert swe_counts == [None] * 4
    for trajectory_id in ("miles_g0_m0", "miles_g0_m1"):
        assert reports[trajectory_id].task_id == TID1 and reports[trajectory_id].grading_semantics == "swe_f2p_p2p"

    buf, recycled = _buffer(world, args)
    for prompt_group, group in zip(prompt_groups, groups):
        await buf.put(_entry(world, prompt_group, group))
    assert len(buf._buffer) == 2 and recycled == []
    got = [(await buf.get(current_version=5)).group for _ in range(2)]
    data, metadata = postprocess_rollout_data(args, got, train_parallel_config=None)
    td = convert_samples_to_train_data(args, data, metadata, None, None)
    assert td["raw_reward"] == [1.0, 0.0, 1.0, 0.0]
    assert td["rewards"] == [0.5, -0.5, 0.5, -0.5]  # 组内减均值、不除 std
    # 正式派发 metadata 不带 source：来源由可信 task_id 的命名空间确定
    assert [s.metadata["task_id"].split("::", 1)[0] for s in data] == ["swe_gym_lite"] * 2 + ["r2e_gym_subset"] * 2
    assert all(sum(mask) > 0 for mask in td["loss_masks"])


async def test_mixed_source_group_is_rejected_by_real_buffer_put(world, tmp_path, monkeypatch):
    """同一 prompt 组混入 SWE 成员与 R2E 成员（模拟 caller 组装错误）：两名成员各自正常铸造身份、正常评分，
    真实 buffer put() 的组准入以 mixed_group_members 结构 fatal 拒绝（不是 keep=False）；buffer 为空、
    不回收，零样本进转换。"""

    world.install_sglang_stub()
    from repoharness2.adapters.miles.group_admission import GroupAdmissionFatal

    fx, chain, args, reports = _transport_chain(world, tmp_path, monkeypatch)
    swe_group, r2e_group = _dispatch_groups(fx, n=N)
    # 真实 Dataset 派出两个来源后，取 SWE 成员 0 与 R2E 成员 1 拼一组：只改后者的 group/index，
    # 身份仍由真实 generate 入口铸造
    prompt_group = [swe_group[0], r2e_group[1]]
    prompt_group[1].group_index = 0
    prompt_group[1].index = 1
    (group,) = await _generate(world, args, [prompt_group])
    assert len(chain.registry) == 0
    assert [reports[t].task_id for t in ("miles_g0_m0", "miles_g0_m1")] == [TID1, R2E_TID]

    buf, recycled = _buffer(world, args)
    with pytest.raises(GroupAdmissionFatal, match="同组不同任务") as info:
        await buf.put(_entry(world, prompt_group, group))
    assert info.value.reason_code == "mixed_group_members", info.value
    assert buf._buffer == [] and recycled == []
