"""inspect-rh2-s1：S1 阶段总账本的生成与四步范式自校验（S1-9 交付物）。

沿用 AGENTS.md"Inspector 自校验范式"四步，并按 S1 计划 A10 补机器可读探针：

  ① digest 重算：summary 的 source_digests（s1 全部 evidence）与 code_digests
     （关键 rh2 源文件）逐文件重算 sha256 对照——防"摘要刷分但源代码/证据偷换"；
  ② 关键 report 重建对照：任务状态表 / 闸门 / 递延风险 / blockers 由本模块常量
     重建后与 summary 结构化比对——防"篡改 summary 但字段仍合法"；另外两项
     "重建"是**重跑生产校验器**：frozen_v1 账本经 load_bundle_pairs() 全量
     重算比对（fail-closed），聚合 registry 的 codex#5 收编清单逐 id 复核；
  ③ 字段白名单：summary 经 pydantic 严格模型（extra="forbid"）校验，未知字段拒收；
  ④ forbidden marker 扫描（fail-closed）：summary 整树无豁免扫描；s1 目录下带
     schema_id 的 JSON 工件按聚合 registry 校验 + 扫描——S1-5 发现的"资格报告
     evidence 串天然含 marker"按 schema_id 白名单豁免（沿用 contracts 的
     MARKER_SCAN_EXEMPT_SCHEMAS 机制，S1-9 已把 rh2.eligibility_report.v1 收编）。
     自由文本 .md 证据（如 grading_p_matrix.md **按设计**要讨论 test_patch 等
     私有名词——它们是审计文档不是模型可见面）只做 digest 锚定、不做 marker
     扫描，这一范围决策记录在 implementation-notes S1-9 条目。

  另有 A10 探针核对：读机器可读的 uh_probe_result.json，断言 overall_pass、
  镜像 digest 与 summary pin 逐字节一致、top-p offsets 对齐律仍在。

  可选开关 --run-contract-tests：以子进程重跑 rh2 契约测试（pytest tests/contracts），
  失败即整体失败（S1 计划"重跑契约测试的可选开关"）。

退出码约定（与 inspect-rh2-artifact 同风格）：

  0  全部通过
  2  summary 读不到 / 不是合法 JSON / 字段白名单（schema）失败
  3  digest 重算不符或被引用文件缺失
  4  forbidden marker 命中
  5  结构化对照失败（任务状态/闸门/递延/blockers/探针/frozen/registry）
  6  --run-contract-tests 重跑失败

用法：

  cd rh2
  uv run inspect-rh2-s1                  # 校验在盘 summary
  uv run inspect-rh2-s1 --write         # （重新）生成 summary 后立即校验
  uv run inspect-rh2-s1 --run-contract-tests
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError

from repoharness2.contracts import StrictModel, scan_for_forbidden_markers
from repoharness2.registry import (
    EXTRA_SCHEMA_REGISTRY,
    FULL_MARKER_SCAN_EXEMPT_SCHEMAS,
    FULL_SCHEMA_REGISTRY,
)

EXIT_OK = 0
EXIT_SUMMARY_INVALID = 2
EXIT_DIGEST_MISMATCH = 3
EXIT_FORBIDDEN_MARKER = 4
EXIT_STRUCTURAL_FAILED = 5
EXIT_CONTRACT_TESTS_FAILED = 6

# 路径推导（editable 安装形态：src/repoharness2/inspect_s1.py -> 仓库根）
_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_S1_DIR = _REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s1"
DEFAULT_RH2_ROOT = _REPO_ROOT / "rh2"
SUMMARY_FILENAME = "s1_acceptance_summary.json"

# ---------------------------------------------------------------------------
# 阶段事实常量（步骤 ② 的"重建关键 report"来源；改这里必须同步重生成 summary）
# ---------------------------------------------------------------------------

STAGE = "rh2_s1"
SLIME_IMAGE_DIGEST_PIN = (
    "sha256:a7317182c71d35712ee4edc86a5d1c313dc969efdf0026d339673299c186ea75"
)
VERIFIERS_PIN = "5885ab9c54152e707af2a11797aa52c3eb1752da"

TASK_STATUS: dict[str, str] = {
    "S1-0": "done_uh_probe_pass_image_pinned",
    "S1-1": "done_contracts_15_schemas_plus_1b_hardening",
    "S1-2": "done_envpack_bundle_split_frozen_v1",
    "S1-3": "done_project_from_slime_fixture_plus_7a_regression",
    "S1-4": "done_grading_manager_p1_p11_docker_verified",
    "S1-5": "done_gate_seven_dims_finalize_wrapper",
    "S1-6": "done_custom_generate_glue_a5_handshake",
    "S1-7a": "done_debug_transport_step_2_optimizer_steps_ckpt_discarded",
    # 与 deferred_risks 同步（codex 2026-07-10 指出两处状态曾不一致）
    "S1-7b": "closed_by_p3_20260708",
    "S1-8": "done_offline_export_parity_core_cross_pass",
    "S1-9": "done_closeout_inspector_h1_h2_h3",
}

GATES: dict[str, Any] = {
    # 检查点 2 已由用户（项目所有者）于 2026-07-11 确认，pending 注记摘除；
    # note 保留确认事件本身作为审计痕迹。
    "rh2_s1_closed_loop": True,
    "rh2_s1_closed_loop_note": "checkpoint2_confirmed_by_user_20260711",
    "rh2_s2_signal_trusted": False,
    "rh2_formal_training_allowed": False,
}

# 递延风险清单（C3/A3 措辞，逐条来自 03 计划与 7a 报告 §4；
# 2026-07-09 P3 八卡预实验后改判，判定依据见 preflight/preflight_report.md §1）
DEFERRED_RISKS: list[dict[str, str]] = [
    {
        "id": "s1_7b_30b_full_train_step",
        "status": "closed_by_p3_20260708",
        "note": "P3 关闭：J4 replay（gbs16）+ J5 gbs20 online 完成 30B-A3B 真实训练 step + 权重同步（update_weights 11.45s@512MB）。注意：formal J4 严格模式（治理过滤后在线组 batch）仍受 batch schedule alignment 阻塞，该问题独立登记（preflight_report.md §3），不影响本项关闭",
    },
    {
        "id": "u_c_multi_gpu_training_side",
        "status": "closed_by_p3_20260708",
        "note": "P3 关闭：Megatron on sm_120 绿（J3 A4 + J4 replay + J5 训练 step）；PCIe all-to-all 绿（J1 基准 + J5 actor_train 174s）；CPU offload 代价绿（actor_train_tok_per_s=4528）；colocate 显存水位以放置决策方式关闭——T3 分离 + train_async 定案后 colocate 不再是候选（分析性关闭，preflight_report.md §2）",
    },
    {
        "id": "routing_tape_training_consumption",
        "status": "closed_by_p3_20260708",
        "note": "P3 关闭：J4 replay + J5 gbs20 两条路径均真实消费 rollout_top_p_token_ids/offsets + rollout_routed_experts 进 loss，loss/grad_norm 有限；train_rollout_logprob_abs_diff≈0.036~0.039 留档",
    },
    {
        "id": "s1_7a_checkpoint",
        "status": "checkpoint_discarded_true",
        "note": "7a 两次 optimizer step 的 checkpoint 均保存后删除留证（ckpt_discard_run7/9.log），不作任何后续初始权重",
    },
    {
        "id": "rh2_formal_training_allowed",
        "status": "false",
        "note": "8 题来自 Verified 仓库，复用会污染评测叙事；正式训练闸门保持关闭",
    },
]

# S2 阻塞项（任务 C：不淡化，三处登记之一；另两处 = implementation-notes + s2_blockers.md）
BLOCKERS: list[dict[str, str]] = [
    {
        "id": "s2_blocker_offline_export_thinking_models",
        "severity": "blocks_offline_export_and_warm_start_for_thinking_models",
        "summary": (
            "S1-8 导出器的线性追加式 token 重建假设（分支首轮 prompt == refs[0]）"
            "对真实 Claude Code 轨迹全量 fail-closed 拒绝（token_reconstruction_mismatch）："
            "CC 按 Anthropic 协议在后续请求剥离历史 thinking 块，Qwen3 thinking 重渲染"
            "必然漂移，REALIGN 把每条轨迹的首轮 t0 整轮掉落——离线导出/warm-start 路线"
            "对 thinking 模型当前不可用"
        ),
        "impact": "E3 warm-start 回退预案的前置依赖：预案启用前必须先修导出器",
        "upgrade_path": "分叉感知重建（叶链自身 tokens + used-refs 逐位锚定，或树侧前缀血缘），技术要点见 s1/s2_blockers.md",
        "details_doc": "s1/s2_blockers.md",
        "reason_code": "token_reconstruction_mismatch",
    }
]

# 测试基线（生成时点的实测值；信息性字段，inspector 只做下界核对）
TEST_BASELINE: dict[str, int] = {
    "pytest_q_passed": 0,  # 由 --write 时的 --pytest-count 参数覆盖；0 = 未填
    "pytest_docker_passed": 15,
}
MIN_EXPECTED_PYTEST = 560  # 7a 收口态基线，S1-9 只增不减


# ---------------------------------------------------------------------------
# summary 的字段白名单（步骤 ③：extra="forbid" 严格模型）
# ---------------------------------------------------------------------------


class S1AcceptanceSummary(StrictModel):
    """s1_acceptance_summary.json 的严格 schema（未知字段即拒收）。"""

    stage: Literal["rh2_s1"] = Field(description="阶段判别字段。")
    generated_at_utc: str = Field(description="生成时刻（运行时 UTC，F4 时钟纪律）。")
    clock_baseline_note: str = Field(
        description="时钟基准声明的指针（F4：notes 顶部声明为准）。"
    )
    slime_image_digest_pin: str = Field(description="S1-0 冻结的 slime 镜像 digest。")
    verifiers_pin: str = Field(description="verifiers commit pin（F6 双 pin 之一）。")
    tasks: dict[str, str] = Field(description="S1-0~9 任务状态表。")
    gates: dict[str, Any] = Field(description="阶段闸门（含 pending 注记）。")
    deferred_risks: list[dict[str, str]] = Field(description="递延风险清单（C3/A3）。")
    blockers: list[dict[str, str]] = Field(description="S2 阻塞项（任务 C 登记）。")
    test_baseline: dict[str, int] = Field(description="生成时点的测试基线。")
    uh_probe_file: str = Field(description="机器可读探针结果的相对路径（A10）。")
    source_digests: dict[str, str] = Field(description="s1 evidence 逐文件 sha256。")
    code_digests: dict[str, str] = Field(description="关键 rh2 源文件逐文件 sha256。")


# ---------------------------------------------------------------------------
# 生成
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _iter_evidence_files(s1_dir: Path) -> list[tuple[str, Path]]:
    """s1 evidence 枚举规则（确定性）：s1/ 顶层全部文件 + 7a_artifacts/ 顶层全部
    文件（不递归 artifacts_run* 批量 sidecar 目录——它们由 bringup_7a_report.md
    锚定），排除 summary 自身。"""

    entries: list[tuple[str, Path]] = []
    for file in sorted(s1_dir.iterdir()):
        if file.is_file() and file.name != SUMMARY_FILENAME:
            entries.append((f"s1/{file.name}", file))
    artifacts = s1_dir / "7a_artifacts"
    if artifacts.is_dir():
        for file in sorted(artifacts.iterdir()):
            if file.is_file():
                entries.append((f"s1/7a_artifacts/{file.name}", file))
    return entries


def _iter_code_files(rh2_root: Path) -> list[tuple[str, Path]]:
    """关键 rh2 源文件枚举规则（确定性）：src/repoharness2 全部 .py +
    pyproject.toml + s1_parity.py + s1_7a_bringup 顶层 .py/.sh。"""

    entries: list[tuple[str, Path]] = []
    for file in sorted((rh2_root / "src" / "repoharness2").rglob("*.py")):
        entries.append((f"rh2/{file.relative_to(rh2_root)}", file))
    for extra in [
        rh2_root / "pyproject.toml",
        rh2_root / "experiments" / "s1_parity.py",
    ]:
        if extra.is_file():
            entries.append((f"rh2/{extra.relative_to(rh2_root)}", extra))
    bringup = rh2_root / "experiments" / "s1_7a_bringup"
    if bringup.is_dir():
        for file in sorted(bringup.iterdir()):
            if file.is_file() and file.suffix in {".py", ".sh"}:
                entries.append((f"rh2/{file.relative_to(rh2_root)}", file))
    return entries


def build_summary(
    s1_dir: Path = DEFAULT_S1_DIR,
    rh2_root: Path = DEFAULT_RH2_ROOT,
    *,
    pytest_count: int | None = None,
) -> dict[str, Any]:
    """从阶段常量 + 在盘文件重算 digest，构造完整 summary dict。"""

    baseline = dict(TEST_BASELINE)
    if pytest_count is not None:
        baseline["pytest_q_passed"] = pytest_count
    return {
        "stage": STAGE,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "clock_baseline_note": (
            "时间戳基准声明见 s1/implementation-notes.md 顶部（F4）：S1 线程内部标注"
            "曾统一用 2026-07-09，实际执行日为 UTC 2026-07-07/08；本文件与后续 "
            "evidence 一律以生成时刻的 date -u 为准，不许未来日期"
        ),
        "slime_image_digest_pin": SLIME_IMAGE_DIGEST_PIN,
        "verifiers_pin": VERIFIERS_PIN,
        "tasks": dict(TASK_STATUS),
        "gates": dict(GATES),
        "deferred_risks": [dict(item) for item in DEFERRED_RISKS],
        "blockers": [dict(item) for item in BLOCKERS],
        "test_baseline": baseline,
        "uh_probe_file": "s1/uh_probe_result.json",
        "source_digests": {key: _sha256_file(path) for key, path in _iter_evidence_files(s1_dir)},
        "code_digests": {key: _sha256_file(path) for key, path in _iter_code_files(rh2_root)},
    }


def write_summary(
    s1_dir: Path = DEFAULT_S1_DIR,
    rh2_root: Path = DEFAULT_RH2_ROOT,
    *,
    pytest_count: int | None = None,
) -> Path:
    summary = build_summary(s1_dir, rh2_root, pytest_count=pytest_count)
    path = s1_dir / SUMMARY_FILENAME
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 校验（四步范式 + A10 探针）
# ---------------------------------------------------------------------------


def _fail(code: int, message: str) -> int:
    print(f"[inspect-rh2-s1] FAIL: {message}", file=sys.stderr)
    return code


def verify(
    s1_dir: Path = DEFAULT_S1_DIR,
    rh2_root: Path = DEFAULT_RH2_ROOT,
    *,
    run_contract_tests: bool = False,
) -> int:
    summary_path = s1_dir / SUMMARY_FILENAME

    # -------------------------------------------------- 读 summary
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _fail(EXIT_SUMMARY_INVALID, f"summary 读取失败: {summary_path}: {exc}")

    # -------------------------------------------------- ③ 字段白名单
    try:
        summary = S1AcceptanceSummary.model_validate(payload)
    except ValidationError as exc:
        return _fail(EXIT_SUMMARY_INVALID, f"summary 字段白名单校验失败:\n{exc}")

    # -------------------------------------------------- ④ marker 扫描（summary 本体，无豁免）
    hits = scan_for_forbidden_markers(payload)
    if hits:
        for hit in hits:
            print(
                f"[inspect-rh2-s1] marker 命中: path={hit.path} marker={hit.marker!r} kind={hit.kind}",
                file=sys.stderr,
            )
        return _fail(EXIT_FORBIDDEN_MARKER, "summary 本体含 forbidden marker（总账本必须干净）")

    # -------------------------------------------------- ② 关键 report 重建对照（常量重建）
    structural_problems: list[str] = []
    if summary.tasks != TASK_STATUS:
        structural_problems.append(
            f"任务状态表与重建值不符: summary={summary.tasks} != expected={TASK_STATUS}"
        )
    if summary.gates != GATES:
        structural_problems.append(f"闸门与重建值不符: {summary.gates} != {GATES}")
    if summary.deferred_risks != DEFERRED_RISKS:
        structural_problems.append("递延风险清单与重建值不符（C3/A3 措辞不许漂移）")
    if summary.blockers != BLOCKERS:
        structural_problems.append("blockers 与重建值不符（S2 阻塞项不许淡化/丢失）")
    if summary.slime_image_digest_pin != SLIME_IMAGE_DIGEST_PIN:
        structural_problems.append("slime 镜像 pin 与 S1-0 冻结值不符")
    if summary.verifiers_pin != VERIFIERS_PIN:
        structural_problems.append("verifiers pin 与 F6 冻结值不符")
    if summary.test_baseline.get("pytest_q_passed", 0) < MIN_EXPECTED_PYTEST:
        structural_problems.append(
            f"pytest 基线 {summary.test_baseline.get('pytest_q_passed')} < 下界 {MIN_EXPECTED_PYTEST}"
        )

    # blocker 详情文档三处登记之一：s2_blockers.md 必须在场且点名 blocker id 与升级路径
    blockers_doc = s1_dir / "s2_blockers.md"
    if not blockers_doc.is_file():
        structural_problems.append("s1/s2_blockers.md 缺失（任务 C 的三处登记之一）")
    else:
        doc_text = blockers_doc.read_text(encoding="utf-8")
        for blocker in BLOCKERS:
            if blocker["id"] not in doc_text:
                structural_problems.append(f"s2_blockers.md 未点名 blocker id {blocker['id']}")
        if "分叉感知重建" not in doc_text:
            structural_problems.append("s2_blockers.md 缺少升级路径'分叉感知重建'的技术要点")

    # codex#5 收编闭环：聚合 registry 必须仍含全部五个收编 id。
    # 校验语义 = S1-9 五个是**下界**（漂移/丢失即 FAIL）；S1 之后的阶段
    # （FA-0 起）按扩展机制新增的 id 走各自阶段的 inspector，这里用白名单
    # 前缀放行，未知前缀仍 FAIL（防不明 schema 静默混入）。
    expected_extra = {
        "rh2.grading_backpressure_event.v1",
        "rh2.group_repair_signal.v1",
        "rh2.public_task_bundle.v1",
        "rh2.private_grading_bundle.v1",
        "rh2.bundle_pair.v1",
    }
    _post_s1_prefixes = ("rh2.fa.",)  # FA 工作流契约（05 计划 FA-0，2026-07-12）
    # S2-1 T2-b（2026-07-13）：bundle v2 三分体系（golden 面与 grading 面分离，
    # 执行计划 §3.0）。显式清单放行（不共享前缀，故不用前缀机制）。
    _post_s1_extra_ids = {
        "rh2.private_grading_bundle.v2",
        "rh2.validation_only_bundle.v1",
        "rh2.environment_package.v1",
    }
    missing_extra = expected_extra - set(EXTRA_SCHEMA_REGISTRY)
    unknown_extra = {
        schema_id
        for schema_id in set(EXTRA_SCHEMA_REGISTRY) - expected_extra - _post_s1_extra_ids
        if not schema_id.startswith(_post_s1_prefixes)
    }
    if missing_extra or unknown_extra:
        structural_problems.append(
            f"聚合 registry 收编清单漂移: 缺失={sorted(missing_extra)} 未知={sorted(unknown_extra)}"
        )

    # -------------------------------------------------- A10 机器可读探针
    probe_path = s1_dir / "uh_probe_result.json"
    try:
        probe = json.loads(probe_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        structural_problems.append(f"uh_probe_result.json 读取失败: {exc}")
        probe = None
    if probe is not None:
        if probe.get("overall_pass") is not True:
            structural_problems.append("uh_probe_result.json overall_pass != true（U-H 背书失效）")
        if probe.get("slime_image_digest") != summary.slime_image_digest_pin:
            structural_problems.append(
                "探针镜像 digest 与 summary pin 不一致："
                f"{probe.get('slime_image_digest')} != {summary.slime_image_digest_pin}"
            )
        alignment = probe.get("alignment") or {}
        if alignment.get("offsets_eq_genlen_plus_1") is not True:
            structural_problems.append("探针 top-p offsets 对齐律（len==gen+1）未通过")

    # -------------------------------------------------- frozen_v1 生产校验器重跑
    try:
        from repoharness2.envpack.bundles import load_bundle_pairs
        from repoharness2.envpack.freeze import load_frozen_v1

        pairs = load_bundle_pairs()  # 默认全量对照 frozen_v1（fail-closed）
        if len(pairs) != 8:
            structural_problems.append(f"frozen 题单数量异常: {len(pairs)} != 8")
        frozen_at = str(load_frozen_v1()["meta"].get("frozen_at", ""))
        today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if frozen_at > today_utc:
            structural_problems.append(
                f"frozen_v1 含未来日期 frozen_at={frozen_at}（F4 时钟纪律）"
            )
    except Exception as exc:  # noqa: BLE001 防漂移校验失败必须显式露出
        structural_problems.append(f"frozen_v1 防漂移校验失败: {exc}")

    if structural_problems:
        for problem in structural_problems:
            print(f"[inspect-rh2-s1] 结构化对照: {problem}", file=sys.stderr)
        return _fail(EXIT_STRUCTURAL_FAILED, f"结构化对照 {len(structural_problems)} 项失败")

    # -------------------------------------------------- ① digest 重算
    mismatches: list[str] = []
    for section, base in (("source_digests", s1_dir), ("code_digests", rh2_root)):
        digests: dict[str, str] = getattr(summary, section)
        for key, expected_digest in digests.items():
            if section == "source_digests":
                relative = key[len("s1/"):] if key.startswith("s1/") else key
                file_path = base / relative
            else:
                relative = key[len("rh2/"):] if key.startswith("rh2/") else key
                file_path = base / relative
            if not file_path.is_file():
                mismatches.append(f"{key}: 文件缺失 ({file_path})")
                continue
            actual = _sha256_file(file_path)
            if actual != expected_digest:
                mismatches.append(f"{key}: 记录 {expected_digest[:12]}… != 重算 {actual[:12]}…")
    # 反向核对：在盘 evidence 不许多出未入账文件（防"塞私货绕过账本"）
    recorded = set(summary.source_digests)
    on_disk = {key for key, _ in _iter_evidence_files(s1_dir)}
    unrecorded = sorted(on_disk - recorded)
    if unrecorded:
        mismatches.append(f"在盘 evidence 未入账: {unrecorded}（须重新生成 summary）")
    if mismatches:
        for mismatch in mismatches:
            print(f"[inspect-rh2-s1] digest: {mismatch}", file=sys.stderr)
        return _fail(EXIT_DIGEST_MISMATCH, f"digest 重算 {len(mismatches)} 项不符")

    # -------------------------------------------------- ④ 带 schema_id 的 JSON 工件
    for key in summary.source_digests:
        if not key.endswith(".json"):
            continue
        relative = key[len("s1/"):]
        file_path = s1_dir / relative
        try:
            content = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue  # digest 步骤已锚定字节；非 JSON 解析问题不在本步职责
        if not isinstance(content, dict):
            continue
        schema_id = content.get("schema_id")
        if not isinstance(schema_id, str) or schema_id not in FULL_SCHEMA_REGISTRY:
            continue  # 非契约工件（如 uh_probe_result.json / frozen_v1 有专用校验）
        model_cls = FULL_SCHEMA_REGISTRY[schema_id]
        try:
            model_cls.model_validate(content)
        except ValidationError as exc:
            return _fail(EXIT_STRUCTURAL_FAILED, f"{key}: schema 校验失败（{schema_id}）:\n{exc}")
        if schema_id not in FULL_MARKER_SCAN_EXEMPT_SCHEMAS:
            artifact_hits = scan_for_forbidden_markers(content)
            if artifact_hits:
                for hit in artifact_hits:
                    print(
                        f"[inspect-rh2-s1] {key} marker 命中: path={hit.path} marker={hit.marker!r}",
                        file=sys.stderr,
                    )
                return _fail(EXIT_FORBIDDEN_MARKER, f"{key} 含 forbidden marker")

    # -------------------------------------------------- 可选：重跑契约测试
    if run_contract_tests:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "tests/contracts"],
            cwd=rh2_root,
            capture_output=True,
            text=True,
        )
        tail = "\n".join((result.stdout or "").strip().splitlines()[-3:])
        print(f"[inspect-rh2-s1] 契约测试重跑（tests/contracts）:\n{tail}")
        if result.returncode != 0:
            print(result.stdout[-2000:], file=sys.stderr)
            print(result.stderr[-2000:], file=sys.stderr)
            return _fail(EXIT_CONTRACT_TESTS_FAILED, "契约测试重跑未全绿")

    print(
        "[inspect-rh2-s1] OK："
        f"digest {len(summary.source_digests)} evidence + {len(summary.code_digests)} code 全部命中；"
        "字段白名单/结构化对照/A10 探针/frozen_v1 重算/marker 扫描全部通过。"
    )
    return EXIT_OK


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inspect-rh2-s1",
        description="S1 阶段总账本的四步范式自校验（--write 先重新生成再校验）。",
    )
    parser.add_argument("--s1-dir", default=str(DEFAULT_S1_DIR), help="s1 evidence 目录。")
    parser.add_argument("--rh2-root", default=str(DEFAULT_RH2_ROOT), help="rh2 包根目录。")
    parser.add_argument("--write", action="store_true", help="重新生成 summary 后再校验。")
    parser.add_argument(
        "--pytest-count", type=int, default=None,
        help="--write 时写入 test_baseline.pytest_q_passed 的实测值。",
    )
    parser.add_argument(
        "--run-contract-tests", action="store_true",
        help="以子进程重跑 rh2 契约测试（pytest tests/contracts），失败即整体失败。",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    s1_dir = Path(args.s1_dir)
    rh2_root = Path(args.rh2_root)
    if args.write:
        path = write_summary(s1_dir, rh2_root, pytest_count=args.pytest_count)
        print(f"[inspect-rh2-s1] summary written -> {path}")
    return verify(s1_dir, rh2_root, run_contract_tests=args.run_contract_tests)


def entry() -> None:
    """console_scripts 入口（inspect-rh2-s1 命令）。"""

    raise SystemExit(main())


if __name__ == "__main__":
    raise SystemExit(main())
