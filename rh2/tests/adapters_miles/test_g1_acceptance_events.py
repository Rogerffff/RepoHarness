"""租前终审 B1/B2 + 租前完整审查（PR-P0-1/3/4/5/6/8）修复验收：
g1_acceptance 结构化事件 collect→judge 全链。

对应条款：

- B1：collect 消费 miles 结构化事件（不再日志正则、无"校准位"None 字段）；
  代表性事件目录全链 PASS；删除任一必要事件类别 → 总判定 INCOMPLETE。
- B2：judge 的 applied oracle 用独立 ``optimizer_step_applied`` 事实（NORMAL
  枚举不计入），并与 Adam/scheduler 前后计数交叉验证；``current_version``
  来自 trainer 的 train_rollout 事实；正控组必须被 applied step 消费。
- PR-P0-1：collect 原子发布（失败不留可判证据）、输出目录不可复用、异 run
  事件按污染 FAIL——审查反例"旧 PASS + 新 collect 失败仍可 PASS"在此关死。
- PR-P0-3A/4/5/6/8 的假绿反例负测试在 g1_acceptance --self-test 内逐条覆盖
  （self-test 是单一事实源）；本文件跑全量 self-test 一次并抽查关键反例，
  避免两处维护同一批 fixture。
- 生产 emitter 同源性（integration base 专属）：直接调用 miles
  ``rh2_event_log.emit`` 产出事件文件，喂给 collect，证明生产 schema 与
  消费端联结逻辑同源，不存在"测试自造 schema、生产另一套"的缝。

事件生成复用 g1_acceptance 自带的代表性 fixture 生成器（_selftest_write_events），
它就是 --self-test 用的同一生成器——单一事实源，避免测试与 self-test 两套样例。
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
from pathlib import Path

import pytest

_G1_PATH = (
    Path(__file__).resolve().parents[2] / "experiments" / "miles_gpu_spike" / "g1_acceptance.py"
)
_spec = importlib.util.spec_from_file_location("g1_acceptance_under_test", _G1_PATH)
g1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g1)


def _collect(events_dir: Path, out_dir: Path, run_id: str | None = None) -> dict:
    ns = argparse.Namespace(
        events_dir=str(events_dir), dmon_csv=None, gpu_mem_total_mb=None,
        out_dir=str(out_dir), run_id=run_id,
    )
    with contextlib.redirect_stdout(io.StringIO()):
        g1.cmd_collect(ns)
    return json.loads((out_dir / "collect_report.json").read_text())


def _judge(ev: Path, r3: str = "on") -> dict:
    ns = argparse.Namespace(
        evidence_dir=str(ev),
        thresholds=str(_G1_PATH.parent / "thresholds.md"),
        r3=r3,
        custom_config=str(_G1_PATH.parent / "custom_config.yaml"),
        out=str(ev / "verdict.json"),
    )
    with contextlib.redirect_stdout(io.StringIO()):
        g1.cmd_judge(ns)
    return json.loads((ev / "verdict.json").read_text())


def _full_chain(tmp_path: Path, mutate: str = "") -> dict:
    """代表性事件 → collect → 探针/manifest 落盘 → judge（与 self-test 同一装配）。"""
    ev = g1._selftest_evidence(tmp_path, mutate=mutate)
    return _judge(ev)


def _failed(verdict: dict) -> set[str]:
    return {c["check"] for c in verdict["checks"] if c["status"] == "FAIL"}


def test_representative_events_full_chain_pass(tmp_path):
    """B1 验收正例：代表性事件目录 collect→judge 全链 PASS；除 s1_compat
    finalization 的 NOT_APPLICABLE（如实标注面）外无非 PASS 判定项。"""
    verdict = _full_chain(tmp_path)
    not_pass = [
        (c["check"], c["status"], c["detail"])
        for c in verdict["checks"]
        if c["status"] not in ("PASS", "NOT_APPLICABLE")
    ]
    assert verdict["overall"] == "PASS", f"非 PASS 项：{not_pass}"
    na = [c["check"] for c in verdict["checks"] if c["status"] == "NOT_APPLICABLE"]
    assert na == ["shutdown_finalization"], (
        f"NOT_APPLICABLE 只允许出现在 s1_compat finalization 面，got {na}"
    )


def test_full_selftest_suite_passes():
    """全部租前审查反例（P0-1/3/4/5/6/8 假绿 + B2 oracle 坏例 + 事件删除
    INCOMPLETE）由 --self-test 单一事实源覆盖；这里整体执行一次。"""
    assert g1.cmd_selftest() == 0


@pytest.mark.parametrize(
    "drop",
    [
        "drop_train_step",
        "drop_train_step_consumed",
        "drop_train_rollout",
        "drop_rollout_group",
        "drop_rollout_workers",
        "drop_logprob_compare",
        "drop_eval_smoke",
        "drop_actor_identity",
        "drop_publish_facts",
        "drop_sample_dis",
        "drop_replay_events",
    ],
)
def test_delete_any_required_event_kind_yields_incomplete(tmp_path, drop):
    """B1 验收反例：删掉任一必要事件类别，总判定必须 INCOMPLETE（缺证据
    fail-closed，不允许假绿也不允许误报 FAIL 掩盖缺失）。"""
    verdict = _full_chain(tmp_path, mutate=drop)
    assert verdict["overall"] == "INCOMPLETE", (
        f"{drop} 应 INCOMPLETE，得 {verdict['overall']}: "
        + str([(c["check"], c["status"]) for c in verdict["checks"] if c["status"] != "PASS"])
    )


def test_normal_enum_is_not_applied_evidence(tmp_path):
    """B2 复现修复：outcome=NORMAL 但 optimizer_step_applied=False（found-inf/
    debug 型）不得计入 applied step——规模项必须 FAIL 而不是被枚举名判绿。"""
    verdict = _full_chain(tmp_path, mutate="normal_not_applied")
    assert "g1_min_applied_optimizer_steps" in _failed(verdict)


def test_applied_requires_optimizer_counter_progress(tmp_path):
    """B2 交叉验证：声称 applied 的 step 若 Adam step 计数没有 +1，独立计数
    事实与 applied 布尔矛盾，必须 FAIL optimizer_step_progress_consistent。"""
    verdict = _full_chain(tmp_path, mutate="counter_mismatch")
    assert "optimizer_step_progress_consistent" in _failed(verdict)


def test_current_version_from_trainer_fact_not_behavior_tail(tmp_path):
    """B2 复现修复：behavior weight_versions=["1","3"] 而 trainer current=1 时，
    sample_records.current_version 必须取 train_rollout 的 trainer 事实（1），
    behavior_version 取逐 turn 最旧数值版本（1）——不得再取列表末位 3。"""
    ev = g1._selftest_evidence(tmp_path, mutate="stale_behavior")
    rows = [
        r
        for r in g1.read_jsonl(ev / "collected" / "sample_records.jsonl")
        if r.get("behavior_versions") == ["1", "3"]
    ]
    assert rows, "fixture 应包含 behavior=[1,3] 的样本"
    assert all(r["current_version"] == 1 for r in rows)
    assert all(r["behavior_version"] == 1 for r in rows)


def test_positive_control_must_be_consumed_by_applied_step(tmp_path):
    """B2 验收：正控组 reward 有方差但其样本只进了 SKIPPED_ZERO_SIGNAL step
    （没有驱动任何真实 optimizer 更新）→ 消费判定必须 FAIL。"""
    verdict = _full_chain(tmp_path, mutate="pc_not_applied")
    assert "positive_control_consumed_by_applied_step" in _failed(verdict)


def test_zero_variance_group_reaching_applied_step_fails(tmp_path):
    """拒绝面守恒：零方差组绕过 filter 混进训练批并被 applied step 消费时，
    zero_variance_groups_must_not_train 必须 FAIL。"""
    verdict = _full_chain(tmp_path, mutate="zero_var_trained")
    assert "zero_variance_groups_must_not_train" in _failed(verdict)


def test_actor_identity_mismatch_fails(tmp_path):
    """B3 判定面：任一 actor 的 miles tree digest 与其余/钉死值不一致 → FAIL。"""
    verdict = _full_chain(tmp_path, mutate="identity_mismatch")
    assert "integration_tree_identity" in _failed(verdict)


# ---------------------------------------------------------------------------
# 聚焦复核（codex_pr_p0_recheck）3 个残余 P0 假绿的直接负测试。
# 反例 fixture 与 --self-test 同源（_selftest_write_events 单一事实源）；这里
# 逐条钉住"修复前判 PASS、修复后必 FAIL"的判定项。
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutate",
    [
        # 复核 finding 1：删除 rank5（6 rank 拓扑中最后一个）的全部
        # replay fill/consume/exhausted——修复前 judge 只查 rollout/step 级
        # 存在性，其余 rank 的事件即可洗绿。
        "replay_missing_rank",
        # 只删 rank5 在 r0s1 的 train_step 消费事件（census 细粒度）。
        "replay_missing_rank_step",
    ],
)
def test_replay_rank_census_incomplete_fails(tmp_path, mutate):
    """finding 1（P0-5/P0-8）：预期 trainer global rank census（thresholds
    expected_trainer_global_ranks）内任一 rank 的 replay 消费链不完整 → FAIL。"""
    verdict = _full_chain(tmp_path, mutate=mutate)
    assert "routing_replay_trainer_consumption" in _failed(verdict)


def test_replay_same_dp_replica_digest_conflict_fails(tmp_path):
    """finding 1（P0-5）：同 dp 组的 PP 副本消费同一份数据，sample_digests
    必须一致；修复前 setdefault 只取每 dp 第一条 fill，rank4 与 rank0/2 的
    冲突被静默吞掉。"""
    verdict = _full_chain(tmp_path, mutate="replay_dp_digest_conflict")
    assert "routing_replay_source_linkage" in _failed(verdict)


@pytest.mark.parametrize(
    "mutate",
    [
        # 复核 finding 2：bootstrap update（rollout_id=None）缺失——版本链
        # 无可信起根，修复前 prev_after=None 时链检查整体跳过。
        "drop_bootstrap",
        # bootstrap 必须唯一。
        "duplicate_bootstrap",
        # 首个 regular update 声称 99->100，而 trainer current（train_rollout
        # 独立事实）= 1——修复前 version_before 从不与 trainer current 比较。
        "wrong_first_update_before",
        # 发布账本自洽（0->1->2->3）但 r1 的 trainer current 与上一边界
        # version_after 断链——version_after 必须与下一 rollout current 联结。
        "next_rollout_current_mismatch",
        # 全 skipped 轮却出现 weight_update（代码分支已有，此前无提交测试）。
        "all_skipped_but_update",
    ],
)
def test_publish_bootstrap_and_current_anchor(tmp_path, mutate):
    """finding 2（P0-6）：bootstrap 有且唯一；每个 interval 的 update 版本必须
    与 trainer current 双向锚定，缺锚/断链/无 applied 推版本一律 FAIL。"""
    verdict = _full_chain(tmp_path, mutate=mutate)
    assert "weight_publish_conservation" in _failed(verdict)


@pytest.mark.parametrize(
    "mutate",
    [
        # 复核 finding 3：behavior_versions=["1","99"]、current=1——修复前
        # min 折叠成 1、staleness=0，future turn 被隐藏。
        "mixed_future_behavior",
        # 数值+非数值混合：不可解析项被 min 折叠静默丢弃。
        "nonnumeric_behavior_version",
        # 空列表（样本无任何版本事实）。
        "missing_behavior_version",
    ],
)
def test_behavior_version_list_validated_per_item(tmp_path, mutate):
    """finding 3（P0-8）：逐 turn 版本列表必须逐项存在、可解析且
    <= current_version；任何单项异常都不得被 min 折叠洗绿。"""
    verdict = _full_chain(tmp_path, mutate=mutate)
    assert "staleness_max_versions" in _failed(verdict)


# ---------------------------------------------------------------------------
# 租前聚焦修复批 #1：leaf 唯一身份（fan-out 假红/假绿双向的直接负测试）
# ---------------------------------------------------------------------------


def test_fanout_two_leaves_are_not_duplicate_consumption(tmp_path):
    """假红消除的正例锚点：代表性 fixture 含一个双叶 fan-out run（两叶共享
    sample_index、leaf_ordinal 0/1），全链必须 PASS——修复前 queue 守恒把两个
    合法叶按纯 index 判成"重复消费"必红（G1 要求覆盖 fan-out，即真实运行
    必然假红）。"""
    verdict = _full_chain(tmp_path)
    assert verdict["overall"] == "PASS"
    coverage = next(c for c in verdict["checks"] if c["check"] == "g1_fanout_multileaf_coverage")
    assert coverage["status"] == "PASS"


def test_fanout_tape_swap_fails_source_linkage(tmp_path):
    """假绿反例：把两个 fan-out 叶的 routing tape 对调——digest multiset 不变，
    修复前 R3 source linkage 仍 PASS；leaf_id→digest 精确联结必须 FAIL。"""
    verdict = _full_chain(tmp_path, mutate="fanout_tape_swap")
    assert "routing_replay_source_linkage" in _failed(verdict)


def test_same_leaf_consumed_twice_fails(tmp_path):
    """同一 leaf 被消费两次（另一叶未消费）：纯 index multiset 不变（旧判定
    洗绿），leaf 口径必须 FAIL queue 守恒。"""
    verdict = _full_chain(tmp_path, mutate="fanout_duplicate_consumed")
    assert "queue_multiset_conservation" in _failed(verdict)


def test_all_linear_data_fails_fanout_coverage(tmp_path):
    """G1 要求证明运行中真出现 ≥1 个多叶 fan-out：全线性数据（每 run 单叶）
    不得冒充覆盖。"""
    verdict = _full_chain(tmp_path, mutate="no_fanout")
    assert "g1_fanout_multileaf_coverage" in _failed(verdict)


def test_missing_leaf_identity_is_incomplete(tmp_path):
    """旧 emitter/wire（无 leaf_ordinal 字段）必须 INCOMPLETE：身份缺失时
    重复消费/tape 对调双向不可判，不得按纯 index 口径继续判绿。"""
    verdict = _full_chain(tmp_path, mutate="strip_leaf_ordinals")
    assert verdict["overall"] == "INCOMPLETE"
    leaf = next(c for c in verdict["checks"] if c["check"] == "leaf_identity")
    assert leaf["status"] == "MISSING_EVIDENCE"


# ---------------------------------------------------------------------------
# 租前聚焦修复批 #2：trainer per-rank oracle（三个已复现假绿反例 + census 边界）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutate",
    [
        # 复现反例 1：删除 rank5 的全部 train_step（保留其 replay/consume 事件）
        # ——聚合面 outcome/applied/计数一致性全部 PASS。
        "rank_missing_all_steps",
        # census 边界：预期拓扑之外的额外 rank。
        "train_step_extra_rank",
    ],
)
def test_train_step_rank_census(tmp_path, mutate):
    verdict = _full_chain(tmp_path, mutate=mutate)
    assert "train_step_global_rank_census" in _failed(verdict)


def test_train_step_duplicate_rank_emission_is_conflict(tmp_path):
    """同 (rollout, step, attempt, rank) 双重发射 = 证据账本冲突（FAIL），
    不是静默去重。"""
    verdict = _full_chain(tmp_path, mutate="train_step_dup_rank")
    assert "collect_consistency" in _failed(verdict)


@pytest.mark.parametrize(
    "mutate",
    [
        # 复现反例 2：每个 applied step 都写成 Adam 0→1、scheduler 0→32
        # （每步重建 optimizer）——单步自洽，跨 step 链断裂。
        "optimizer_rebuilt",
        # scheduler 步进必须精确 +num_rollouts，不是"前进了就行"。
        "scheduler_wrong_increment",
    ],
)
def test_optimizer_state_continuity_per_rank(tmp_path, mutate):
    verdict = _full_chain(tmp_path, mutate=mutate)
    assert "optimizer_state_continuity_per_rank" in _failed(verdict)


@pytest.mark.parametrize(
    "mutate",
    [
        # 复现反例 3：applied step 的 grad_norm 与 loss 改为 NaN。
        "nan_loss_grad",
        # PP-last 指标只覆盖 dp0（"随便取第一条 metrics"的反例形态）。
        "pp_last_metrics_missing_dp",
    ],
)
def test_train_step_metrics_coverage(tmp_path, mutate):
    verdict = _full_chain(tmp_path, mutate=mutate)
    assert "train_step_metrics_coverage" in _failed(verdict)


# ---------------------------------------------------------------------------
# 租前聚焦修复批 #5：run_manifest 的 thresholds digest 缺失/空/非法不得 PASS
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutate",
    [
        "manifest_missing_thresholds_sha",
        "manifest_empty_thresholds_sha",
        "manifest_bad_thresholds_sha",
    ],
)
def test_manifest_thresholds_digest_required(tmp_path, mutate):
    """thresholds_sha256 缺失/空/非法时 run_identity 必须 FAIL——不得错误声称
    "三方一致"（阈值页失去外部锚点）。"""
    verdict = _full_chain(tmp_path, mutate=mutate)
    assert "run_identity" in _failed(verdict)


# ---------------------------------------------------------------------------
# PR-P0-1：run 隔离 / 原子发布 / 污染拒绝（审查反例的直接负测试）
# ---------------------------------------------------------------------------


def test_collect_failure_publishes_nothing(tmp_path):
    """审查反例（PR-P0-1）：第二次 collect 遇到损坏事件 JSON 抛异常后，旧
    normalized evidence 曾继续存在并被 judge 读到旧 PASS。现在 collect 先写
    .tmp 再原子发布：失败时 collected/ 根本不存在，judge 只能 INCOMPLETE。"""
    events = tmp_path / "events"
    g1._selftest_write_events(events)
    # 混入损坏 JSON 行
    (events / "rh2_events_h_2.jsonl").write_text('{"event": "train_step", broken\n')
    out = tmp_path / "evidence" / "collected"
    with pytest.raises(json.JSONDecodeError):
        _collect(events, out, run_id=g1._RUN_ID)
    assert not out.exists(), "collect 失败不得发布任何 normalized evidence"
    assert not (tmp_path / "evidence").exists() or not any(
        p.name == "collected" for p in (tmp_path / "evidence").iterdir()
    )
    # judge 面对无 collected/ 的 evidence 目录：全部 MISSING → INCOMPLETE
    (tmp_path / "evidence").mkdir(exist_ok=True)
    verdict = _judge(tmp_path / "evidence")
    assert verdict["overall"] == "INCOMPLETE"


def test_collect_refuses_existing_out_dir(tmp_path):
    """PR-P0-1：collect 输出目录已存在（同 run root 第二次 collect）直接拒绝
    ——一个 run root 只绑定一次 run。"""
    events = tmp_path / "events"
    g1._selftest_write_events(events)
    out = tmp_path / "collected"
    _collect(events, out, run_id=g1._RUN_ID)
    with pytest.raises(SystemExit, match="已存在"):
        _collect(events, out, run_id=g1._RUN_ID)


def test_foreign_run_events_are_contamination(tmp_path):
    """PR-P0-1：事件目录混入其他 run 的事件（run_id 不同）→ conflict → FAIL，
    绝不静默并入本 run 的证据。"""
    verdict = _full_chain(tmp_path, mutate="run_id_mismatch")
    assert "collect_consistency" in _failed(verdict)
    assert verdict["overall"] != "PASS"


def test_run_manifest_binding(tmp_path):
    """PR-P0-1：judge 的 run_identity 检查——manifest run_id 与 collect run_id
    不一致必须 FAIL（verdict 只能绑定一个不可变 run）。"""
    verdict = _full_chain(tmp_path, mutate="manifest_run_id_mismatch")
    assert "run_identity" in _failed(verdict)


# ---------------------------------------------------------------------------
# 生产 emitter 同源性（integration base：真实 miles.utils.rh2_event_log）
# ---------------------------------------------------------------------------


@pytest.mark.integration_base
def test_producer_emitter_schema_consumed_by_collect(tmp_path, monkeypatch, world):
    """用 miles 生产模块真函数 emit 事件（含 enabled 门控、run_id 印章与文件
    命名约定），喂给 collect：step/rollout/publish/replay 联结字段必须逐一落到
    normalized evidence。这钉住"生产写什么、collect 读什么"是同一份 schema。"""
    from miles.utils import rh2_event_log

    events_dir = tmp_path / "events"
    monkeypatch.setenv(rh2_event_log.EVENT_DIR_ENV, str(events_dir))
    monkeypatch.setenv(rh2_event_log.RUN_ID_ENV, "prod-run-1")
    assert rh2_event_log.enabled()

    rh2_event_log.emit("actor_identity", role="megatron_train_actor", miles_file="/x/miles/__init__.py",
                       tree_digest="ab" * 32, expected_tree_digest="ab" * 32)
    rh2_event_log.emit("train_rollout", rollout_id=0, trainer_current_version=1)
    rh2_event_log.emit("rollout_workers", rollout_id=0, worker_ids=["train/e0"], weight_version=1)
    rh2_event_log.emit("rollout_group", rollout_id=0, group_index=0, instance_id="django__django-11099",
                       sample_indices=[0, 1], leaf_ordinals=[0, 0],
                       rewards=[1.0, 0.0], behavior_versions=[["1"], ["1"]],
                       statuses=["Status.COMPLETED"] * 2, response_lengths=[8, 8],
                       routing_tape=[None, None])
    rh2_event_log.emit("logprob_compare", rollout_id=0, dp_rank=0, trainer_current_version=1,
                       entries=[{"sample_index": 0, "leaf_ordinal": 0, "same_version": True,
                                 "mean_abs_diff": 0.01,
                                 "num_tokens": 6, "total_tokens": 8, "length_mismatch": False}])
    rh2_event_log.emit("sample_dis_accounting",
                       entries=[{"sample_index": 0, "leaf_ordinal": 0,
                                 "accepted_tokens": 5, "provenance_tokens": 6}])
    rh2_event_log.emit("train_step_consumed", rollout_id=0, step_id=0, dp_rank=0, rank=0,
                       sample_indices=[0, 1], leaf_ordinals=[0, 0],
                       num_tokens=16, num_microbatches=1,
                       attribution="micro_batch_indices")
    rh2_event_log.emit("train_step", rollout_id=0, step_id=0, attempt=0, outcome="NORMAL",
                       optimizer_step_applied=True, adam_step_before=0, adam_step_after=1,
                       scheduler_steps_before=0, scheduler_steps_after=32, num_rollouts=32,
                       grad_norm=0.5,
                       duration_seconds=1.0, zero_signal_scan_seconds=0.05, rank=0, dp_rank=0,
                       is_pp_last_stage=True,
                       metrics={"loss": 0.5, "dis_accepted_tokens": 10.0, "dis_rejected_tokens": 2.0,
                                "dis_microbatch_provenance_tokens": 12.0})
    rh2_event_log.emit("replay_fill", manager="routing", rollout_id=0, rank=0, dp_rank=0,
                       enabled=True, num_streams=16, records_min=1, records_max=1,
                       expected_records=1, num_samples=2,
                       sample_indices=[0, 1], leaf_ordinals=[0, 0],
                       sample_digests=["aa" * 32, "bb" * 32])
    rh2_event_log.emit("weight_update", rollout_id=0, version_before=1, version_after=2,
                       duration_seconds=3.0)
    rh2_event_log.emit("weight_publish", rollout_id=0)
    rh2_event_log.emit("eval_smoke", rollout_id=0, ok=True, num_metrics=1, weight_version=2)

    files = list(events_dir.glob("rh2_events_*.jsonl"))
    assert files, "生产 emitter 应按 rh2_events_<host>_<pid>.jsonl 命名落盘"
    rows = g1.read_jsonl(files[0])
    assert all(r.get("run_id") == "prod-run-1" for r in rows), "每条事件必须带 run_id 印章"

    ev = tmp_path / "collected"
    report = _collect(events_dir, ev, run_id="prod-run-1")
    assert report["run_id"] == "prod-run-1"
    assert report["step_rows"] == 1 and report["sample_rows"] == 2
    assert not report["conflicts"]
    assert report["leaf_identity_missing"] == []  # 生产 schema 携带完整 leaf 身份
    [step] = g1.read_jsonl(ev / "step_records.jsonl")
    assert step["outcome"] == "NORMAL"
    assert step["optimizer_step_applied"] is True
    assert step["adam_step_after"] == 1 and step["scheduler_steps_after"] == 32
    assert step["weight_version_before"] == 1 and step["weight_version_after"] == 2
    assert step["queue_consumed_sample_ids"] == ["0:0", "1:0"]  # leaf id = index:ordinal
    assert step["dp_ranks"] == [0]
    assert step["worker_ids"] == ["train/e0"]
    assert step["dis_accepted_tokens"] == 10.0
    assert step["zero_signal_scan_seconds_max"] == 0.05
    [rank_row] = g1.read_jsonl(ev / "step_rank_records.jsonl")
    assert rank_row["rank"] == 0 and rank_row["num_rollouts"] == 32
    assert rank_row["is_pp_last_stage"] is True and rank_row["metrics"]["loss"] == 0.5
    rows = g1.read_jsonl(ev / "sample_records.jsonl")
    assert {r["sample_id"] for r in rows} == {"0:0", "1:0"}
    assert all(r["current_version"] == 1 for r in rows)
    s0 = next(r for r in rows if r["sample_id"] == "0:0")
    assert s0["sample_index"] == 0 and s0["leaf_ordinal"] == 0
    assert s0["dis_accepted_tokens"] == 5 and s0["dis_provenance_tokens"] == 6
    assert s0["logprob_masked_tokens"] == 6 and s0["logprob_length_mismatch"] is False
    publish = json.loads((ev / "publish_records.json").read_text())
    assert publish["updates"][0]["version_after"] == 2
    assert publish["publishes"] == [0]
    replay = json.loads((ev / "replay_records.json").read_text())
    assert replay["fills"][0]["sample_digests"] == ["aa" * 32, "bb" * 32]
    assert replay["fills"][0]["sample_indices"] == [0, 1]
    assert replay["fills"][0]["leaf_ordinals"] == [0, 0]
    ident = json.loads((ev / "actor_identity.json").read_text())
    assert ident["consistent"] is True
    evals = json.loads((ev / "eval_smoke.json").read_text())["events"]
    assert evals == [{"rollout_id": 0, "ok": True, "weight_version": 2}]


@pytest.mark.integration_base
def test_producer_identity_assertion_stops_on_digest_mismatch(monkeypatch, world):
    """B3 worker 侧钉死：RH2_EXPECTED_MILES_TREE_DIGEST 与实际 miles tree
    digest 不一致时，assert_and_emit_identity 必须 raise（actor 启动即停），
    一致时不抛。digest 为真实树内容哈希（与 launch preflight 同函数）。"""
    from miles.utils import rh2_event_log

    monkeypatch.delenv(rh2_event_log.EVENT_DIR_ENV, raising=False)
    real = rh2_event_log.miles_tree_digest()
    assert re_hex64(real)
    monkeypatch.setenv(rh2_event_log.EXPECTED_TREE_DIGEST_ENV, real)
    rh2_event_log.assert_and_emit_identity("unit_test_role")  # 一致：不抛
    monkeypatch.setenv(rh2_event_log.EXPECTED_TREE_DIGEST_ENV, "0" * 64)
    with pytest.raises(RuntimeError, match="identity mismatch"):
        rh2_event_log.assert_and_emit_identity("unit_test_role")


@pytest.mark.integration_base
def test_producer_tree_digest_matches_audit_manifest(world):
    """PR-P0-4 去自我背书：launch preflight 用的 expected digest 必须来自审计
    manifest（integration_base_manifest.json 的 miles_source_tree_digest），而
    这里验证 manifest 值与 integration checkout 实算值一致——manifest 漂移或
    树漂移都在本测试红。"""
    from miles.utils import rh2_event_log

    manifest = json.loads(
        (Path(__file__).resolve().parents[3]
         / "docs" / "agentic_RL" / "repo_harness_rh2_workstreams" / "miles_spike"
         / "integration_base_manifest.json").read_text()
    )
    pinned = manifest.get("miles_source_tree_digest")
    assert re_hex64(pinned or ""), "manifest 必须携带 miles_source_tree_digest（P0-4）"
    assert pinned == rh2_event_log.miles_tree_digest()


def re_hex64(s: str) -> bool:
    return isinstance(s, str) and len(s) == 64 and all(c in "0123456789abcdef" for c in s)
