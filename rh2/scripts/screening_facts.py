#!/usr/bin/env python3
"""环境筛查只读汇总工具（`environment_screening_definition_20260915.md` §6 的"下一实施片"）。

做什么：把**已有产物**汇总成每题一份 `facts.json` 与一份来源对账 `reconcile.md`：

    driver 账本 JSONL（`adapters/slime/replay_grade.py` 的 `rh2.replay_grade_ledger.v1`）
      + eval 日志 / 诊断 sidecar（`rh2.grading_diagnostics.v1`）
      + 冻结工件（frozen_patch / baseline_manifest / projection / classification / stage）
      + 参考清单（`grading_bundles_v2_v0.jsonl`，`rh2.private_grading_bundle.v2`）
      + 可选 oracle（阶段一 `stage1_offline.jsonl` + 其 `logs/.../status_map.json`）
      → `<out-dir>/<instance_id>/facts.json`、`<out-dir>/reconcile.md`、`<out-dir>/summary.json`

**只读**：不写任何输入目录，不启动容器，不调用网络。

两条口径必须记住：

1. sidecar 只有计数，没有逐 ID 状态。逐 ID 状态由本工具**离线重解析** eval 日志得到
   （`repoharness2.envpack.scoring.parse_eval_log_v2`），来源标 `parser_derived`；
   oracle 侧直接读 `status_map.json`，来源标 `oracle`。两者都不改任何既有判定。
2. 每个事实值都带 `source` 与 `status`：

   - `host_observation`：host/driver/grader 进程或容器内 **root** 步骤产生（候选无法直接改写）。
   - `candidate_output`：候选段脚本或以**候选身份**执行的观测脚本产生的文本
     （`manager.py` 的 `_observe` 注释：「观测输出不是可信证据，只进诊断」）。
   - `parser_derived`：本工具离线重解析得到。
   - `static`：冻结数据集 / 账本里记录的配置（参考清单、预算、路径）。
   - `oracle`：阶段一离线探针的账本与 status_map。
   - `status ∈ observed / missing / not_applicable`。未取到就是 `missing`，不猜。

用法（从 `rh2/` 目录）：

    .venv/bin/python scripts/screening_facts.py \
        --ledger ../runs/swe_grading_wiring_20260915/e1/ledger_e1.jsonl \
        --ledger ../runs/swe_grading_wiring_20260915/e1/ledger_e1_pandas.jsonl \
        --eval-log-dir ../runs/swe_grading_wiring_20260915/e1/eval_logs \
        --artifacts-dir ../runs/swe_grading_wiring_20260915/e1/artifacts \
        --grading-bundles ../docs/.../s2/ingest/grading_bundles_v2_v0.jsonl \
        --oracle-ledger ../runs/env_probe_stage1_20260910/ledger/stage1_continuation_20260911/stage1_offline.jsonl \
        --out-dir <out>

账本里的 `log.path` / `diagnostics_ref` 是**运行机**上的绝对路径；本工具按 basename 在
`--eval-log-dir` 里解析（同步到本机后目录名会变）。工件目录按 `projection.frozen_patch_digest`
反查（账本不记 nonce），查不到时退到 `<slug>/a<attempt>-*` 唯一匹配。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# repoharness2 的导入是**可选**的：本工具的绝大多数字段只需要读 JSON，不需要 rh2 运行时。
# 工作树里有别的会话在改 rh2/src 时，import 可能临时抛 SyntaxError；那种情况下降级——
# 照常产出账本/sidecar/工件/oracle 侧的事实，只把离线重解析与逐 ID 对账标成不可用并写清原因。
PARSER_IMPORT_ERROR: str | None = None
try:
    from repoharness2.envpack.bundles_v2 import PrivateGradingBundleV2  # noqa: E402
    from repoharness2.envpack.scoring import parse_eval_log_v2  # noqa: E402
except Exception as _exc:  # noqa: BLE001 - SyntaxError / ImportError / 任何 rh2 侧导入期异常都要降级而不是崩
    PrivateGradingBundleV2 = None  # type: ignore[assignment,misc]
    parse_eval_log_v2 = None  # type: ignore[assignment]
    PARSER_IMPORT_ERROR = f"{type(_exc).__name__}: {str(_exc)[:300]}"

TOOL_VERSION = "screening_facts/0.1"
FACTS_SCHEMA_ID = "rh2.screening_facts.v1"

SOURCES = frozenset({"host_observation", "candidate_output", "parser_derived", "static", "oracle"})
STATUSES = frozenset({"observed", "missing", "not_applicable"})

# 候选 kind → oracle gate（阶段一探针只有 empty/gold 两个 gate）。
GATE_FOR_CANDIDATE_KIND = {"noop": "empty", "gold": "gold"}

# 官方口径（swebench 4.1.0 `test_passed`）：PASSED/XFAIL 计通过，SKIPPED 不进桶，其余计失败。
_PASSED_STATUSES = frozenset({"PASSED", "XFAIL"})

# 紧凑模式下长列表（参考缺席、逐 ID 差异）只留前 N 条 + 计数；`--full-status-maps` 给完整列表。
COMPACT_LIST_LIMIT = 50


class FactsError(RuntimeError):
    """输入不成立（缺必需文件、账本 schema 不认识等）。"""


# --------------------------------------------------------------------------- 事实信封


def fact(value: Any, source: str, *, status: str | None = None, note: str | None = None) -> dict[str, Any]:
    """把一个值包成带来源与状态的事实信封。`status` 缺省按 `value is None` 判 missing。"""

    if source not in SOURCES:
        raise ValueError(f"未知 source={source!r}（允许 {sorted(SOURCES)}）")
    resolved = status if status is not None else ("observed" if value is not None else "missing")
    if resolved not in STATUSES:
        raise ValueError(f"未知 status={resolved!r}（允许 {sorted(STATUSES)}）")
    out: dict[str, Any] = {"value": value, "source": source, "status": resolved}
    if note:
        out["note"] = note
    return out


_KEY_ABSENT_NOTE = "账本行里没有这个键——产出账本的 driver 版本比当前源码旧（不是「本次没有这个事实」）"
_KEY_NULL_NOTE = "账本键在场但为 null：本次确实没有这个事实"


def ledger_fact(row: dict[str, Any], key: str, source: str, *, note: str | None = None) -> dict[str, Any]:
    """按**键是否在账本行里**区分两种"没有值"。

    schema_id 不变而字段集变过（e1 账本缺 `baseline_policy_version` / `omitted_cache_count` 等
    当前源码会写的键），消费方必须能把「旧 producer」和「本次无此事实」分开，否则缺项清单没意义。
    """

    def _join(extra: str) -> str:
        return f"{note}；{extra}" if note else extra

    if key not in row:
        return fact(None, source, status="missing", note=_join(_KEY_ABSENT_NOTE))
    if row[key] is None:
        return fact(None, source, status="not_applicable", note=_join(_KEY_NULL_NOTE))
    return fact(row[key], source, note=note)


def sub_fact(container: Any, key: str, source: str, *, note: str | None = None) -> dict[str, Any]:
    """`ledger_fact` 的通用版：容器本身缺席 / 键缺席 / 键为 null 是三件不同的事。"""

    if not isinstance(container, dict):
        return fact(None, source, status="missing", note=f"{note}；上级对象缺席" if note else "上级对象缺席")
    return ledger_fact(container, key, source, note=note)


def is_fact(obj: Any) -> bool:
    return isinstance(obj, dict) and obj.keys() >= {"value", "source", "status"} and obj["source"] in SOURCES


def walk_facts(node: Any, prefix: str = "") -> list[tuple[str, dict[str, Any]]]:
    """深度遍历，返回 (字段路径, 事实) 列表；列表下标统一记成 `[]`（便于跨题聚合可观测率）。"""

    found: list[tuple[str, dict[str, Any]]] = []
    if is_fact(node):
        found.append((prefix or "<root>", node))
        return found
    if isinstance(node, dict):
        for key, value in node.items():
            found.extend(walk_facts(value, f"{prefix}.{key}" if prefix else key))
    elif isinstance(node, list):
        for value in node:
            found.extend(walk_facts(value, f"{prefix}[]"))
    return found


# --------------------------------------------------------------------------- 输入装载


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            text = line.strip()
            if not text:
                continue
            try:
                rows.append({"_line": line_no, **json.loads(text)})
            except json.JSONDecodeError as exc:
                raise FactsError(f"{path}:{line_no} 不是合法 JSON：{exc}") from exc
    return rows


@dataclass(frozen=True)
class RawGradingBundle:
    """参考清单的降级视图：pydantic 模型不可用时用，**不做 schema 校验**（字段照抄 JSONL）。

    只提供本工具与 `parse_eval_log_v2` 需要的属性；facts 里会标明这次没做 schema 校验。
    """

    instance_id: str
    repo: str
    repo_key_lower: str
    version: str
    base_commit: str
    test_patch: str
    fail_to_pass: list[str]
    pass_to_pass: list[str]
    eval_cmd: str
    spec_vendor_id: str


def load_grading_bundles(path: Path) -> tuple[dict[str, Any], list[str], bool]:
    """参考清单（评分面 v2）。校验失败的行记进 `rejected`，不静默丢弃。

    返回 `(bundles, rejected, schema_validated)`；`schema_validated=False` = 走了降级视图。
    """

    bundles: dict[str, Any] = {}
    rejected: list[str] = []
    validated = PrivateGradingBundleV2 is not None
    for row in load_jsonl(path):
        row.pop("_line", None)
        instance_id = str(row.get("instance_id", "?"))
        try:
            if validated:
                bundles[instance_id] = PrivateGradingBundleV2.model_validate(row)
            else:
                bundles[instance_id] = RawGradingBundle(
                    instance_id=str(row["instance_id"]), repo=str(row["repo"]),
                    repo_key_lower=str(row["repo_key_lower"]), version=str(row["version"]),
                    base_commit=str(row["base_commit"]), test_patch=str(row["test_patch"]),
                    fail_to_pass=list(row["fail_to_pass"]), pass_to_pass=list(row.get("pass_to_pass") or []),
                    eval_cmd=str(row["eval_cmd"]), spec_vendor_id=str(row["spec_vendor_id"]),
                )
        except Exception as exc:  # noqa: BLE001 - 校验失败要如实记账，不能让一行坏数据终止汇总
            rejected.append(f"{instance_id}: {type(exc).__name__}: {str(exc)[:160]}")
    return bundles, rejected, validated


def index_eval_logs(dirs: list[Path]) -> dict[str, Path]:
    """basename → 本机路径（账本里的是运行机绝对路径）。同名冲突时先到先得并在报告里留痕。"""

    index: dict[str, Path] = {}
    for directory in dirs:
        if not directory.is_dir():
            continue
        for child in sorted(directory.iterdir()):
            if child.is_file():
                index.setdefault(child.name, child)
    return index


def index_artifacts(dirs: list[Path]) -> tuple[dict[str, Path], list[Path]]:
    """`frozen_patch_digest` → 工件目录；同时返回全部候选目录（供退化查找）。"""

    by_digest: dict[str, Path] = {}
    all_dirs: list[Path] = []
    for directory in dirs:
        if not directory.is_dir():
            continue
        for projection in sorted(directory.glob("*/*/projection.json")):
            all_dirs.append(projection.parent)
            try:
                digest = json.loads(projection.read_text(encoding="utf-8")).get("frozen_patch_digest")
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(digest, str):
                by_digest.setdefault(digest, projection.parent)
        for stage in sorted(directory.glob("*/*/stage.json")):
            if stage.parent not in all_dirs:
                all_dirs.append(stage.parent)
    return by_digest, all_dirs


def oracle_logs_roots(ledger_path: Path, explicit: list[Path]) -> list[Path]:
    """oracle 账本里的 `log_path` 也是运行机路径（`/work/ledger/...`）。

    本机可能的 `logs/` 根：显式给定 > 账本所在目录 > 其父目录（continuation 账本放在
    `<root>/stage1_continuation_.../stage1_offline.jsonl`，而 `logs/` 在 `stage1_continuation_.../logs/`）。
    """

    roots = list(explicit)
    roots.append(ledger_path.parent)
    roots.append(ledger_path.parent.parent)
    seen: list[Path] = []
    for root in roots:
        if root not in seen:
            seen.append(root)
    return seen


def load_oracle(ledger_paths: list[Path], logs_roots: list[Path]) -> dict[tuple[str, str], dict[str, Any]]:
    """(instance_id, gate) → oracle 记录（含解析好的 status_map 路径）。后读的账本覆盖先读的。"""

    out: dict[tuple[str, str], dict[str, Any]] = {}
    for ledger_path in ledger_paths:
        roots = oracle_logs_roots(ledger_path, logs_roots)
        for row in load_jsonl(ledger_path):
            gate = str(row.get("gate", ""))
            instance_id = str(row.get("instance_id", ""))
            if not gate or not instance_id:
                continue
            log_path = str(row.get("log_path") or "")
            status_map_path: Path | None = None
            if "/logs/" in log_path:
                rel = Path(log_path.split("/logs/", 1)[1]).parent / "status_map.json"
                for root in roots:
                    candidate = root / "logs" / rel
                    if candidate.is_file():
                        status_map_path = candidate
                        break
            row["_ledger_path"] = str(ledger_path)
            row["_status_map_path"] = str(status_map_path) if status_map_path else None
            out[(instance_id, gate)] = row
    return out


# --------------------------------------------------------------------------- 状态规约


def bucket_of_status(raw: str | None) -> str:
    """原始状态串 → 官方四态桶：passed / skipped / failed / missing。"""

    if raw is None:
        return "missing"
    value = raw.strip()
    if value in _PASSED_STATUSES:
        return "passed"
    if value == "SKIPPED":
        return "skipped"
    return "failed"


def rh2_buckets(verdict: Any, f2p: list[str], p2p: list[str]) -> dict[str, str]:
    """把 `EvalVerdict` 的桶还原成逐参考 ID 状态（官方口径，缺席计失败但单独标 missing）。"""

    missing = set(verdict.reference_missing)
    skipped = set(verdict.reference_skipped)
    passed = set(verdict.f2p_success) | set(verdict.p2p_success)
    table: dict[str, str] = {}
    for case in list(f2p) + list(p2p):
        if case in missing:
            table[case] = "missing"
        elif case in skipped:
            table[case] = "skipped"
        elif case in passed:
            table[case] = "passed"
        else:
            table[case] = "failed"
    return table


# --------------------------------------------------------------------------- 单次运行


def _resolve_artifact_dir(row: dict[str, Any], by_digest: dict[str, Path], all_dirs: list[Path]) -> tuple[Path | None, str]:
    digest = (row.get("projection") or {}).get("frozen_patch_digest")
    if isinstance(digest, str) and digest in by_digest:
        return by_digest[digest], "frozen_patch_digest"
    # 退化：没有 projection（apply_failed / unsafe / 阶段失败）时按 task slug + attempt 唯一匹配
    task_id = str(row.get("task_id", ""))
    slug = task_id.replace("::", "--").replace("/", "-")
    attempt = row.get("attempt")
    hits = [d for d in all_dirs if d.parent.name == slug and d.name.startswith(f"a{attempt}-")]
    if len(hits) == 1:
        return hits[0], "slug_attempt_unique"
    return None, "unresolved"


def _run_ref_facts(row: dict[str, Any], ledger_path: Path) -> dict[str, Any]:
    candidate = row.get("candidate") or {}
    return {
        "ledger_path": fact(str(ledger_path), "static"),
        "ledger_line": fact(row.get("_line"), "static"),
        "ledger_schema_id": fact(row.get("schema_id"), "static"),
        "run_id": fact(row.get("run_id"), "host_observation"),
        "attempt": fact(row.get("attempt"), "host_observation"),
        "started_at_utc": fact(row.get("started_at_utc"), "host_observation"),
        "candidate_kind": fact(candidate.get("kind"), "host_observation"),
        "candidate_origin": fact(candidate.get("origin"), "host_observation"),
        "candidate_patch_sha256": fact(
            candidate.get("patch_sha256"), "host_observation",
            status=("observed" if candidate.get("patch_sha256") else "not_applicable"),
            note="noop 候选不写补丁，没有 sha256"),
        "ledger_row_keys": fact(sorted(k for k in row if k != "_line"), "static",
                                note="账本行实际键集：schema_id 不变而键集变过时，跨账本 diff 这一项"),
    }


def _condition_facts(row: dict[str, Any]) -> dict[str, Any]:
    policy = row.get("policy") or {}
    return {
        "image_ref": fact(row.get("image_ref"), "host_observation"),
        "image_digest_expected": fact(row.get("image_digest_expected"), "static"),
        "image_id_actual": ledger_fact(row, "image_id_actual", "host_observation"),
        "image_local_build": fact(row.get("image_local_build"), "host_observation"),
        "derived_image_recipe": ledger_fact(row, "derived_image_recipe", "static"),
        "image_pull": ledger_fact(row, "image_pull", "host_observation"),
        "grader_profile_id": fact(policy.get("profile_id"), "static"),
        "grader_profile_digest": fact(policy.get("grader_profile_digest"), "static"),
        "network": fact(policy.get("network"), "static"),
        "exec_user": fact(policy.get("user"), "static"),
        "exec_uid": fact(policy.get("uid"), "static"),
        "cpus": fact(policy.get("cpus"), "static"),
        "memory_bytes": fact(policy.get("memory_bytes"), "static"),
        "shm_bytes": fact(policy.get("shm_bytes"), "static"),
        "tmpfs_bytes": fact(policy.get("tmpfs_bytes"), "static"),
        "pids_limit": fact(policy.get("pids_limit"), "static"),
        "candidate_writable_prefixes": fact(policy.get("candidate_writable_prefixes"), "static"),
        "budgets": fact(row.get("budgets"), "static"),
    }


def _candidate_facts(row: dict[str, Any], artifact_dir: Path | None, how: str, base_commit: str | None) -> dict[str, Any]:
    candidate = row.get("candidate") or {}
    classification = row.get("classification") or {}
    projection = row.get("projection") or {}
    stage: dict[str, Any] = {}
    if artifact_dir is not None and (artifact_dir / "stage.json").is_file():
        try:
            stage = json.loads((artifact_dir / "stage.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            stage = {}
    head = stage.get("head")
    out = {
        "apply_method": fact(candidate.get("apply_method"), "host_observation"),
        "apply_user": fact(candidate.get("apply_user"), "static"),
        "apply_stderr_tail": fact(candidate.get("apply_stderr_tail"), "host_observation",
                                  status=("observed" if candidate.get("apply_stderr_tail")
                                          else ("not_applicable" if "apply_stderr_tail" in candidate else "missing")),
                                  note="driver 把空 stderr 写成 null（`stage.apply_stderr_tail or None`），"
                                       "空与未采集在账本里不可分"),
        "classification_verdict": fact(classification.get("verdict") if classification else None, "host_observation"),
        "classification_reason_codes": fact(classification.get("reason_codes") if classification else None, "host_observation"),
        "frozen_patch_digest": fact(projection.get("frozen_patch_digest") if projection else None, "host_observation"),
        "projection_included_paths": fact(projection.get("included_paths") if projection else None, "host_observation"),
        "projection_included_count": fact(len(projection["included_paths"]) if projection.get("included_paths") is not None else None, "host_observation"),
        "projection_ignored_paths": fact(projection.get("ignored_paths") if projection else None, "host_observation"),
        "projection_ignored_count": fact(len(projection["ignored_paths"]) if projection.get("ignored_paths") is not None else None, "host_observation"),
        "unsupported_shape_reasons": fact(projection.get("unsupported_shape_reasons") if projection else None, "host_observation"),
        "baseline_policy_version": ledger_fact(row, "baseline_policy_version", "host_observation"),
        "omitted_cache_count": ledger_fact(row, "omitted_cache_count", "host_observation"),
        "artifact_dir": fact(str(artifact_dir) if artifact_dir else None, "static", note=f"resolved_by={how}"),
        "stage_head": fact(head, "host_observation"),
        "stage_last_stage": fact(stage.get("last_stage"), "host_observation"),
        "stage_error": ledger_fact(row, "stage_error", "host_observation"),
        "cleanup": ledger_fact(row, "cleanup", "host_observation"),
        "notes": fact(row.get("notes") or None, "host_observation",
                      status=("observed" if row.get("notes") else ("not_applicable" if "notes" in row else "missing"))),
    }
    if head is None or base_commit is None:
        out["head_equals_base_commit"] = fact(None, "static", status="missing")
    else:
        out["head_equals_base_commit"] = fact(head == base_commit, "static")
    return out


def _scoring_facts(row: dict[str, Any]) -> dict[str, Any]:
    report = row.get("report")
    def _rep(key: str) -> dict[str, Any]:
        return sub_fact(report, key, "host_observation")
    return {
        "report_id": _rep("report_id"),
        "outcome": _rep("outcome"),
        "failure_category": _rep("failure_category"),
        "infra_failure_detail": _rep("infra_failure_detail"),
        "reward": _rep("reward"),
        "f2p_pass": _rep("f2p_pass"),
        "f2p_total": _rep("f2p_total"),
        "p2p_fail": _rep("p2p_fail"),
        "p2p_total": _rep("p2p_total"),
        "grader_version": _rep("grader_version"),
        "regrade_total": ledger_fact(row, "regrade_total", "host_observation"),
    }


_INSTALL_START = "RH2_PHASE_START=install"
_INSTALL_END = "RH2_PHASE_END=install"


def install_segment_evidence(log_text: str) -> dict[str, Any]:
    """安装段的两条低成本线索（`set -x` 回显里读，启发式，只作筛查线索、不作判据）。

    为什么需要：`install_rc_last_command` 只是**安装段最后一条命令**的退出码。e1 的
    mypy-12741 里那条是 `hash -r`，而同段的 `pip install -e .` 因离线拿不到 setuptools
    已经失败——rc=0 不能证明安装成功（`e1_codex_review_20260916.md` §4.2）。
    """

    last_command: str | None = None
    lines = log_text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("+ RH2_INSTALL_RC=") or line.strip() == "+ RH2_INSTALL_RC=$?":
            for previous in reversed(lines[:index]):
                stripped = previous.lstrip("+").strip()
                if previous.startswith("+") and stripped and not stripped.startswith("RH2_"):
                    last_command = stripped
                    break
            break
    segment = log_text
    if _INSTALL_START in log_text:
        segment = log_text.split(_INSTALL_START, 1)[1]
        if _INSTALL_END in segment:
            segment = segment.split(_INSTALL_END, 1)[0]
    errors = [line.strip() for line in segment.splitlines() if line.strip().startswith("ERROR: ")]
    return {"last_command": last_command, "error_lines": errors}


def _segment_facts(row: dict[str, Any], log_text: str | None) -> dict[str, Any]:
    install = row.get("install") or {}
    note = "候选段脚本自报（manager.candidate_facts_from_log），不是 host 独立观测"
    rc_note = (
        note + "；语义是**安装段最后一条命令**的退出码，不等于安装成功"
        "（见 install_segment_last_command / install_segment_error_lines）"
    )
    evidence = install_segment_evidence(log_text) if log_text is not None else {"last_command": None, "error_lines": None}
    heuristic = "启发式：从候选段 `set -x` 回显里读，只作筛查线索，不作判据"
    extra = {
        "install_segment_last_command": fact(evidence["last_command"], "candidate_output", note=heuristic),
        "install_segment_error_lines": fact(
            (evidence["error_lines"][:10] if evidence["error_lines"] else evidence["error_lines"]),
            "candidate_output",
            status=("observed" if evidence["error_lines"] else ("not_applicable" if evidence["error_lines"] == [] else "missing")),
            note=heuristic,
        ),
        "install_segment_error_line_count": fact(
            len(evidence["error_lines"]) if evidence["error_lines"] is not None else None,
            "candidate_output", note=heuristic,
        ),
    }
    return {
        "install_rc_last_command": fact(install.get("install_rc_last_command"), "candidate_output", note=rc_note),
        **extra,
        "install_skipped": fact(install.get("install_skipped"), "candidate_output", note=note),
        "install_seconds": fact(install.get("install_seconds"), "candidate_output", note=note),
        "test_rc": fact(install.get("test_rc"), "candidate_output", note=note),
        "test_seconds": fact(install.get("test_seconds"), "candidate_output", note=note),
        "markers_seen": fact(install.get("markers_seen"), "candidate_output", note=note),
        "log_partial": fact(install.get("log_partial"), "host_observation", note="manager 设置：日志是否为超时后的部分读取"),
    }


def _observation_facts(row: dict[str, Any]) -> dict[str, Any]:
    obs = row.get("observations") or {}
    note = "以候选身份执行的观测脚本输出（manager._observe：观测输出不是可信证据，只进诊断）"
    present = bool(obs)
    def _obs(key: str) -> dict[str, Any]:
        return fact(obs.get(key), "candidate_output", status=None if present else "missing", note=note)
    return {
        "import_path": _obs("RH2_OBS_IMPORT_PATH"),
        "pkg_version": _obs("RH2_OBS_PKG_VERSION"),
        "prefix_owner_pre": _obs("RH2_OBS_PREFIX_OWNER_PRE"),
        "runner_digest_pre": _obs("RH2_OBS_RUNNER_DIGEST_PRE"),
        "runner_digest_post": _obs("RH2_OBS_RUNNER_DIGEST"),
        "obs_error": fact(obs.get("RH2_OBS_ERROR"), "candidate_output", status="observed" if obs.get("RH2_OBS_ERROR") else "not_applicable", note=note),
        "runner_integrity_changed": ledger_fact(row, "runner_integrity_changed", "candidate_output",
                                                note="manager 比对前后 RH2_OBS_RUNNER_DIGEST（两端都来自候选身份进程）"),
        "candidate_test_like_paths": ledger_fact(row, "candidate_test_like_paths", "host_observation"),
        "candidate_touched_conftest_or_fixture": ledger_fact(row, "candidate_touched_conftest_or_fixture", "host_observation"),
    }


def _resource_facts(row: dict[str, Any]) -> dict[str, Any]:
    resource = row.get("resource") or {}
    peak = resource.get("mem_peak_mb")
    zero = resource.get("mem_peak_unavailable_or_zero")
    if zero is None and resource:
        zero = peak is None or peak == 0.0
    return {
        "mem_peak_mb": fact(peak, "host_observation", status="observed" if (peak not in (None, 0.0)) else "missing",
                            note="0 或缺失一律按 unavailable_or_zero 处理，不当作实际用量"),
        "mem_peak_unavailable_or_zero": fact(zero, "host_observation"),
    }


def _log_facts(row: dict[str, Any], log_index: dict[str, Path]) -> tuple[dict[str, Any], Path | None]:
    log = row.get("log") or {}
    ledger_path = log.get("path")
    resolved = log_index.get(Path(ledger_path).name) if ledger_path else None
    size = resolved.stat().st_size if resolved is not None else None
    declared = log.get("sha256")
    verified: bool | None = None
    if resolved is not None and isinstance(declared, str):
        digest = "sha256:" + hashlib.sha256(resolved.read_bytes()).hexdigest()
        verified = digest == declared
    diagnostics_ref = row.get("diagnostics_ref")
    diagnostics_local = log_index.get(Path(diagnostics_ref).name) if diagnostics_ref else None
    return {
        "path_in_ledger": fact(ledger_path, "static"),
        "local_path": fact(str(resolved) if resolved else None, "static"),
        "bytes": fact(size, "static"),
        "sha256": fact(declared, "host_observation"),
        "sha256_verified": fact(verified, "static", note="本机文件重算与账本声明比对"),
        "partial": fact(log.get("partial") if log else None, "host_observation"),
        "diagnostics_path_in_ledger": fact(diagnostics_ref, "static"),
        "diagnostics_local_path": fact(str(diagnostics_local) if diagnostics_local else None, "static"),
    }, resolved


def _attestation_facts(row: dict[str, Any], log_index: dict[str, Path]) -> tuple[dict[str, Any], dict[str, Any]]:
    """控制面 / 可信 setup 自证只在 sidecar 里（账本不带），按 diagnostics_ref 读回。"""

    diagnostics_ref = row.get("diagnostics_ref")
    local = log_index.get(Path(diagnostics_ref).name) if diagnostics_ref else None
    payload: dict[str, Any] = {}
    if local is not None:
        try:
            payload = json.loads(local.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
    control = payload.get("control_surface")
    setup = payload.get("trusted_setup")
    return {
        "control_surface": sub_fact(payload, "control_surface", "host_observation", note="grader 容器内 root 步骤自证"),
        "writable_prefixes_done": sub_fact(control, "WRITABLE_PREFIXES_DONE", "host_observation"),
        "protect_ok": sub_fact(control, "RH2_PROTECT_OK", "host_observation"),
        "trusted_setup": sub_fact(payload, "trusted_setup", "host_observation", note="grader 容器内 root 可信 setup 自证"),
        "setup_ok": sub_fact(setup, "RH2_SETUP_OK", "host_observation",
                             note="空自证 = 可信 setup 没跑到写这一行就失败了"),
        "sidecar_verdict": sub_fact(payload, "verdict", "host_observation"),
    }, payload


def _cap(values: list[Any], full: bool) -> tuple[list[Any], bool]:
    """紧凑模式截断长列表；返回 (列表, 是否截断)。计数字段永远是完整值。"""

    if full or len(values) <= COMPACT_LIST_LIMIT:
        return list(values), False
    return list(values[:COMPACT_LIST_LIMIT]), True


def _parser_facts(
    log_text: str | None,
    bundle: Any,
    row: dict[str, Any],
    full_lists: bool,
) -> tuple[dict[str, Any], Any]:
    """离线重解析 eval 日志（逐 ID 状态的唯一来源），并与 sidecar/账本计数互检。"""

    if parse_eval_log_v2 is None:
        return ({"available": fact(False, "parser_derived", status="missing",
                                   note=f"parser_unavailable:repoharness2 导入失败（{PARSER_IMPORT_ERROR}）；"
                                        "离线重解析与逐 ID 对账本次未做，其余字段照常")}, None)
    if log_text is None or bundle is None:
        reason = "eval_log_not_found" if log_text is None else "grading_bundle_not_found"
        return {"available": fact(False, "parser_derived", status="missing", note=reason)}, None

    try:
        verdict = parse_eval_log_v2(bundle, log_text)
    except Exception as exc:  # noqa: BLE001 - 解析失败要如实记账，不能中断整批汇总
        return ({"available": fact(False, "parser_derived", status="missing",
                                   note=f"parse_error:{type(exc).__name__}:{str(exc)[:160]}")}, None)
    sidecar = row.get("verdict_diagnostics") or {}
    report = row.get("report") or {}
    counts = {
        "f2p_pass": len(verdict.f2p_success),
        "f2p_total": len(verdict.f2p_success) + len(verdict.f2p_failure),
        "p2p_fail": len(verdict.p2p_failure),
        "p2p_total": len(verdict.p2p_success) + len(verdict.p2p_failure),
    }
    matches_sidecar: bool | None = None
    if sidecar:
        matches_sidecar = all(
            sidecar.get(key) == getattr(verdict, key)
            for key in ("apply_ok", "resolution", "num_parsed_tests", "num_parsed_outside_segment", "parser_source")
        ) and sorted(sidecar.get("reference_missing") or []) == sorted(verdict.reference_missing) \
            and sorted(sidecar.get("reference_skipped") or []) == sorted(verdict.reference_skipped)
    matches_report: bool | None = None
    if report and report.get("f2p_total") is not None:
        matches_report = all(report.get(key) == value for key, value in counts.items())
    missing_list, missing_cut = _cap(list(verdict.reference_missing), full_lists)
    skipped_list, skipped_cut = _cap(list(verdict.reference_skipped), full_lists)
    return {
        "available": fact(True, "parser_derived"),
        "parser_source": fact(verdict.parser_source, "parser_derived"),
        "apply_ok": fact(verdict.apply_ok, "parser_derived"),
        "resolution": fact(verdict.resolution, "parser_derived"),
        "resolved": fact(verdict.resolved, "parser_derived"),
        "reward_if_scored": fact(verdict.reward, "parser_derived", note="parser 口径，不覆盖 grader 的 reward"),
        "f2p_pass": fact(counts["f2p_pass"], "parser_derived"),
        "f2p_total": fact(counts["f2p_total"], "parser_derived"),
        "p2p_fail": fact(counts["p2p_fail"], "parser_derived"),
        "p2p_total": fact(counts["p2p_total"], "parser_derived"),
        "num_parsed_tests": fact(verdict.num_parsed_tests, "parser_derived"),
        "num_parsed_outside_segment": fact(verdict.num_parsed_outside_segment, "parser_derived"),
        "reference_missing": fact(missing_list, "parser_derived",
                                  note="紧凑模式已截断，完整表见 --full-status-maps 输出" if missing_cut else None),
        "reference_missing_count": fact(len(verdict.reference_missing), "parser_derived"),
        "reference_skipped": fact(skipped_list, "parser_derived",
                                  note="紧凑模式已截断，完整表见 --full-status-maps 输出" if skipped_cut else None),
        "reference_skipped_count": fact(len(verdict.reference_skipped), "parser_derived"),
        "matches_sidecar_verdict": fact(matches_sidecar, "parser_derived",
                                        note="离线重解析与 grader 当时写的 sidecar 诊断逐字段比对"),
        "matches_ledger_report_counts": fact(matches_report, "parser_derived"),
    }, verdict


def _per_id_facts(
    verdict: Any,
    bundle: Any,
    oracle_row: dict[str, Any] | None,
    gate: str | None,
    include_full_maps: bool,
) -> dict[str, Any]:
    if bundle is None:
        return {"available": fact(False, "parser_derived", status="missing", note="grading_bundle_not_found")}
    f2p, p2p = list(bundle.fail_to_pass), list(bundle.pass_to_pass)
    bucket_of = {case: "F2P" for case in f2p}
    bucket_of.update({case: "P2P" for case in p2p})

    rh2_table = rh2_buckets(verdict, f2p, p2p) if verdict is not None else None
    oracle_raw: dict[str, str] | None = None
    oracle_table: dict[str, str] | None = None
    status_map_path = (oracle_row or {}).get("_status_map_path")
    if status_map_path:
        try:
            oracle_raw = json.loads(Path(status_map_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            oracle_raw = None
    if oracle_raw is not None:
        oracle_table = {case: bucket_of_status(oracle_raw.get(case)) for case in f2p + p2p}

    diffs: list[dict[str, Any]] = []
    if rh2_table is not None and oracle_table is not None:
        for case in f2p + p2p:
            if rh2_table[case] != oracle_table[case]:
                diffs.append({
                    "test_id": case,
                    "bucket": bucket_of[case],
                    "rh2": rh2_table[case],
                    "oracle": oracle_table[case],
                    "oracle_raw": (oracle_raw or {}).get(case),
                })

    def _counts(table: dict[str, str] | None) -> dict[str, int] | None:
        if table is None:
            return None
        counter: Counter[str] = Counter()
        for case, state in table.items():
            counter[f"{bucket_of[case]}:{state}"] += 1
        return dict(sorted(counter.items()))

    comparable = rh2_table is not None and oracle_table is not None
    diff_list, diff_cut = _cap(diffs, include_full_maps)
    out: dict[str, Any] = {
        "available": fact(rh2_table is not None, "parser_derived"),
        "reference_f2p_total": fact(len(f2p), "static"),
        "reference_p2p_total": fact(len(p2p), "static"),
        "rh2_counts": fact(_counts(rh2_table), "parser_derived", note="离线重解析（parse_eval_log_v2）得到的逐 ID 桶"),
        "oracle_gate": fact(gate, "static", status="observed" if gate else "not_applicable"),
        "oracle_status_map_path": fact(status_map_path, "oracle"),
        "oracle_counts": fact(_counts(oracle_table), "oracle", note="阶段一 status_map.json 按官方口径规约"),
        "diff_count": fact(len(diffs) if comparable else None, "parser_derived"),
        "diffs": fact(diff_list if comparable else None, "parser_derived",
                      note="紧凑模式已截断，完整表见 --full-status-maps 输出" if diff_cut else None),
    }
    if include_full_maps:
        out["rh2_status_by_id"] = fact(rh2_table, "parser_derived")
        out["oracle_status_by_id"] = fact(oracle_table, "oracle")
        out["oracle_raw_status_by_id"] = fact(oracle_raw, "oracle")
    return out


def build_run_facts(
    row: dict[str, Any],
    ledger_path: Path,
    *,
    bundle: Any,
    log_index: dict[str, Path],
    artifacts_by_digest: dict[str, Path],
    artifact_dirs: list[Path],
    oracle: dict[tuple[str, str], dict[str, Any]],
    include_full_maps: bool,
) -> dict[str, Any]:
    artifact_dir, how = _resolve_artifact_dir(row, artifacts_by_digest, artifact_dirs)
    log_facts, log_path = _log_facts(row, log_index)
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path is not None else None
    attestations, _sidecar = _attestation_facts(row, log_index)
    parser, verdict = _parser_facts(log_text, bundle, row, include_full_maps)
    kind = (row.get("candidate") or {}).get("kind")
    gate = GATE_FOR_CANDIDATE_KIND.get(str(kind)) if kind else None
    instance_id = str(row.get("instance_id", ""))
    oracle_row = oracle.get((instance_id, gate)) if gate else None
    phases = row.get("phases") or {}
    run = {
        "run_ref": _run_ref_facts(row, ledger_path),
        "conditions": _condition_facts(row),
        "candidate": _candidate_facts(row, artifact_dir, how, bundle.base_commit if bundle else None),
        "scoring": _scoring_facts(row),
        "candidate_segment": _segment_facts(row, log_text),
        "observation": _observation_facts(row),
        "attestations": attestations,
        "phases_seconds": {
            name: fact(value, "host_observation") for name, value in sorted(phases.items())
        } or {"_absent": fact(None, "host_observation", status="missing")},
        "resource": _resource_facts(row),
        "log": log_facts,
        "parser": parser,
        "per_id_status": _per_id_facts(verdict, bundle, oracle_row, gate, include_full_maps),
    }
    run["missing_fields"] = sorted(path for path, node in walk_facts(run) if node["status"] == "missing")
    return run


# --------------------------------------------------------------------------- 每题装配


def _oracle_facts(instance_id: str, oracle: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for gate in ("empty", "gold"):
        row = oracle.get((instance_id, gate))
        if row is None:
            out[gate] = {"available": fact(False, "oracle", status="missing", note="阶段一账本无此 (instance, gate) 行")}
            continue
        strict = row.get("strict") or {}
        out[gate] = {
            "available": fact(True, "oracle"),
            "ledger_path": fact(row.get("_ledger_path"), "static"),
            "official_verdict": fact(row.get("official_verdict"), "oracle"),
            "result": fact(row.get("result"), "oracle"),
            "rc_install": fact(row.get("rc_install"), "oracle"),
            "rc_test": fact(row.get("rc_test"), "oracle"),
            "rc_setup": fact(row.get("rc_setup"), "oracle"),
            "timed_out": fact(row.get("timed_out"), "oracle"),
            "parsed_cases": fact(row.get("parsed_cases"), "oracle"),
            "f2p_missing": fact(strict.get("f2p_missing"), "oracle"),
            "p2p_missing": fact(strict.get("p2p_missing"), "oracle"),
            "ref_skipped": fact(strict.get("ref_skipped"), "oracle"),
            "status_map_path": fact(row.get("_status_map_path"), "oracle"),
            "conditions": fact({
                "image_ref": row.get("image_ref"),
                "image_digest_expected": row.get("image_digest_expected"),
                "image_digest_actual": row.get("image_digest_actual"),
                "network": row.get("network"),
                "exec_user_test": row.get("exec_user_test"),
                "memory_limit_bytes": row.get("memory_limit_bytes"),
                "shm_size_bytes": row.get("shm_size_bytes"),
                "fork_commit": row.get("fork_commit"),
            }, "oracle"),
        }
    return out


def build_task_facts(
    task_id: str,
    rows: list[tuple[dict[str, Any], Path]],
    *,
    bundles: dict[str, Any],
    grading_bundles_path: Path,
    log_index: dict[str, Path],
    artifacts_by_digest: dict[str, Path],
    artifact_dirs: list[Path],
    oracle: dict[tuple[str, str], dict[str, Any]],
    include_full_maps: bool,
) -> dict[str, Any]:
    first = rows[0][0]
    instance_id = str(first.get("instance_id", ""))
    bundle = bundles.get(instance_id)
    reference = {
        "grading_bundles_path": fact(str(grading_bundles_path), "static"),
        "available": fact(bundle is not None, "static"),
        "repo": fact(bundle.repo if bundle else None, "static"),
        "repo_key_lower": fact(bundle.repo_key_lower if bundle else None, "static"),
        "version": fact(bundle.version if bundle else None, "static"),
        "base_commit": fact(bundle.base_commit if bundle else None, "static"),
        "eval_cmd": fact(bundle.eval_cmd if bundle else None, "static"),
        "spec_vendor_id": fact(bundle.spec_vendor_id if bundle else None, "static"),
        "f2p_total": fact(len(bundle.fail_to_pass) if bundle else None, "static"),
        "p2p_total": fact(len(bundle.pass_to_pass) if bundle else None, "static"),
        "test_patch_sha256": fact(
            "sha256:" + hashlib.sha256(bundle.test_patch.encode("utf-8")).hexdigest() if bundle else None, "static"),
    }
    runs = [
        build_run_facts(
            row, ledger_path, bundle=bundle, log_index=log_index, artifacts_by_digest=artifacts_by_digest,
            artifact_dirs=artifact_dirs, oracle=oracle, include_full_maps=include_full_maps,
        )
        for row, ledger_path in rows
    ]
    facts = {
        "schema_id": FACTS_SCHEMA_ID,
        "tool_version": TOOL_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id,
        "instance_id": instance_id,
        "source": first.get("source"),
        "task_revision": "upstream",
        "reference": reference,
        "oracle": _oracle_facts(instance_id, oracle),
        "runs": runs,
    }
    facts["missing_fields"] = sorted(path for path, node in walk_facts(facts) if node["status"] == "missing")
    return facts


# --------------------------------------------------------------------------- 报告


def _fv(node: dict[str, Any] | None) -> Any:
    return node.get("value") if isinstance(node, dict) else None


def render_reconcile(all_facts: list[dict[str, Any]]) -> str:
    lines = [
        "# 来源对账（rh2 vs oracle）",
        "",
        f"生成：{datetime.now(timezone.utc).isoformat()}（{TOOL_VERSION}，只读汇总，不下因果结论）",
        "",
        "口径：rh2 逐 ID 状态 = 离线 `parse_eval_log_v2` 重解析 eval 日志（parser_derived）；",
        "oracle 逐 ID 状态 = 阶段一 `status_map.json`（oracle），按官方口径规约成 passed/failed/skipped/missing。",
        "只列差异；没有 oracle 行的运行标 `oracle 缺席`。",
        "",
    ]
    for facts in all_facts:
        lines.append(f"## {facts['task_id']}")
        lines.append("")
        for gate in ("empty", "gold"):
            block = facts["oracle"].get(gate, {})
            if _fv(block.get("available")):
                lines.append(
                    f"- oracle[{gate}]：verdict={_fv(block.get('official_verdict'))}，result={_fv(block.get('result'))}，"
                    f"rc_install={_fv(block.get('rc_install'))}，rc_test={_fv(block.get('rc_test'))}，"
                    f"status_map={'有' if _fv(block.get('status_map_path')) else '无'}"
                )
            else:
                lines.append(f"- oracle[{gate}]：缺席")
        lines.append("")
        for run in facts["runs"]:
            ref = run["run_ref"]
            head = (
                f"### {_fv(ref['run_id'])} · a{_fv(ref['attempt'])} · {_fv(ref['candidate_kind'])} "
                f"（{Path(str(_fv(ref['ledger_path']))).name}:{_fv(ref['ledger_line'])}）"
            )
            lines.append(head)
            lines.append("")
            scoring, parser, per_id = run["scoring"], run["parser"], run["per_id_status"]
            lines.append(
                f"- rh2 判定：outcome={_fv(scoring['outcome'])}，reward={_fv(scoring['reward'])}，"
                f"F2P {_fv(scoring['f2p_pass'])}/{_fv(scoring['f2p_total'])}，"
                f"P2P 失败 {_fv(scoring['p2p_fail'])}/{_fv(scoring['p2p_total'])}，"
                f"infra={_fv(scoring['infra_failure_detail'])}"
            )
            if _fv(parser.get("available")):
                lines.append(
                    f"- 离线重解析：resolution={_fv(parser['resolution'])}，apply_ok={_fv(parser['apply_ok'])}，"
                    f"解析条数={_fv(parser['num_parsed_tests'])}（段外 {_fv(parser['num_parsed_outside_segment'])}），"
                    f"参考缺席={_fv(parser['reference_missing_count'])}，跳过={_fv(parser['reference_skipped_count'])}；"
                    f"与 sidecar 一致={_fv(parser['matches_sidecar_verdict'])}，"
                    f"与账本计数一致={_fv(parser['matches_ledger_report_counts'])}"
                )
            else:
                lines.append(f"- 离线重解析：不可用（{parser.get('available', {}).get('note')}）")
            gate = _fv(per_id.get("oracle_gate"))
            diffs = _fv(per_id.get("diffs"))
            diff_count = _fv(per_id.get("diff_count"))
            if diffs is None:
                lines.append(f"- 逐 ID 对账：无法比对（oracle gate={gate}，status_map={_fv(per_id.get('oracle_status_map_path'))}）")
            elif not diffs:
                lines.append(f"- 逐 ID 对账（oracle gate={gate}）：无差异（rh2 {_fv(per_id['rh2_counts'])}）")
            elif _fv(parser.get("apply_ok")) is False:
                # rh2 侧根本没有测试结果（坏码 / 缺测试段）：逐条列 ID 是噪声，只给规模与成因指针。
                lines.append(
                    f"- 逐 ID 对账（oracle gate={gate}）：rh2 侧无测试结果（apply_ok=false，"
                    f"outcome={_fv(scoring['outcome'])}，infra={_fv(scoring['infra_failure_detail'])}），"
                    f"全部 {diff_count} 个参考 ID 在 rh2 侧 missing；不是判定分歧，是这次运行没跑到测试。"
                )
            else:
                lines.append(f"- 逐 ID 对账（oracle gate={gate}）：差异 {diff_count} 条")
                lines.append("")
                lines.append("| 桶 | test_id | rh2 | oracle | oracle 原始 |")
                lines.append("|---|---|---|---|---|")
                for item in diffs:
                    tid = str(item["test_id"]).replace("|", "\\|")
                    lines.append(f"| {item['bucket']} | `{tid}` | {item['rh2']} | {item['oracle']} | {item['oracle_raw']} |")
                if diff_count is not None and len(diffs) < diff_count:
                    lines.append(f"| … | 其余 {diff_count - len(diffs)} 条见完整输出 | | | |")
                lines.append("")
            cond = run["conditions"]
            oracle_cond = _fv(facts["oracle"].get(gate, {}).get("conditions")) if gate else None
            if oracle_cond:
                pairs = [
                    ("image_ref", _fv(cond["image_ref"]), oracle_cond.get("image_ref")),
                    ("network", _fv(cond["network"]), oracle_cond.get("network")),
                    ("测试执行用户", _fv(cond["exec_user"]), oracle_cond.get("exec_user_test")),
                    ("memory_bytes", _fv(cond["memory_bytes"]), oracle_cond.get("memory_limit_bytes")),
                    ("shm_bytes", _fv(cond["shm_bytes"]), oracle_cond.get("shm_size_bytes")),
                    ("image_digest", _fv(cond["image_digest_expected"]), oracle_cond.get("image_digest_expected")),
                ]
                delta = [(name, a, b) for name, a, b in pairs if a != b]
                if delta:
                    lines.append("- 条件差异（rh2 → oracle）：" + "；".join(f"{n}: {a} → {b}" for n, a, b in delta))
                else:
                    lines.append("- 条件差异：无")
            lines.append("")
    return "\n".join(lines) + "\n"


def build_summary(all_facts: list[dict[str, Any]], extra: dict[str, Any]) -> dict[str, Any]:
    per_field: dict[str, Counter[str]] = defaultdict(Counter)
    per_source: Counter[str] = Counter()
    per_source_observed: Counter[str] = Counter()
    for facts in all_facts:
        for run in facts["runs"]:
            for path, node in walk_facts(run, "runs[]"):
                per_field[path][node["status"]] += 1
                per_source[node["source"]] += 1
                if node["status"] == "observed":
                    per_source_observed[node["source"]] += 1
    rows = []
    for path, counter in sorted(per_field.items()):
        total = sum(counter.values())
        observed = counter.get("observed", 0)
        rows.append({
            "field": path,
            "observed": observed,
            "missing": counter.get("missing", 0),
            "not_applicable": counter.get("not_applicable", 0),
            "total": total,
            "observed_rate": round(observed / total, 4) if total else None,
        })
    total_facts = sum(r["total"] for r in rows)
    total_observed = sum(r["observed"] for r in rows)
    return {
        "schema_id": "rh2.screening_facts_summary.v1",
        "tool_version": TOOL_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "tasks": len(all_facts),
        "runs": sum(len(f["runs"]) for f in all_facts),
        "run_level_fact_count": total_facts,
        "run_level_observed_rate": round(total_observed / total_facts, 4) if total_facts else None,
        "by_source": {
            source: {
                "total": count,
                "observed": per_source_observed.get(source, 0),
                "observed_rate": round(per_source_observed.get(source, 0) / count, 4) if count else None,
            }
            for source, count in sorted(per_source.items())
        },
        "by_field": rows,
        **extra,
    }


# --------------------------------------------------------------------------- CLI


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="只读汇总 driver 账本 / sidecar / 冻结工件 / 参考 / oracle 为每题 facts.json")
    parser.add_argument("--ledger", action="append", required=True, type=Path, help="driver 账本 JSONL（可多次）")
    parser.add_argument("--eval-log-dir", action="append", default=[], type=Path, help="eval 日志与 sidecar 所在目录（可多次）")
    parser.add_argument("--artifacts-dir", action="append", default=[], type=Path, help="冻结工件根目录（可多次）")
    parser.add_argument("--grading-bundles", required=True, type=Path, help="grading_bundles_v2_v0.jsonl")
    parser.add_argument("--oracle-ledger", action="append", default=[], type=Path, help="阶段一 stage1_offline.jsonl（可多次）")
    parser.add_argument("--oracle-logs-root", action="append", default=[], type=Path, help="oracle logs/ 的本机父目录（可多次）")
    parser.add_argument("--out-dir", required=True, type=Path, help="输出目录")
    parser.add_argument("--full-status-maps", action="store_true", help="facts.json 内嵌完整逐 ID 状态表（体积大）")
    parser.add_argument("--task-ids", default=None, help="逗号分隔的 task_id 或 instance_id 过滤")
    return parser.parse_args(argv)


def run(ns: argparse.Namespace) -> dict[str, Any]:
    for path in list(ns.ledger) + [ns.grading_bundles]:
        if not Path(path).is_file():
            raise FactsError(f"缺输入文件：{path}")
    bundles, rejected, schema_validated = load_grading_bundles(ns.grading_bundles)
    log_index = index_eval_logs([Path(p) for p in ns.eval_log_dir])
    artifacts_by_digest, artifact_dirs = index_artifacts([Path(p) for p in ns.artifacts_dir])
    oracle = load_oracle([Path(p) for p in ns.oracle_ledger], [Path(p) for p in ns.oracle_logs_root])

    wanted = {x.strip() for x in ns.task_ids.split(",")} if ns.task_ids else None
    grouped: dict[str, list[tuple[dict[str, Any], Path]]] = defaultdict(list)
    unknown_schema: list[str] = []
    for ledger in ns.ledger:
        ledger_path = Path(ledger)
        for row in load_jsonl(ledger_path):
            if row.get("schema_id") != "rh2.replay_grade_ledger.v1":
                unknown_schema.append(f"{ledger_path}:{row.get('_line')}:{row.get('schema_id')}")
                continue
            task_id = str(row.get("task_id", ""))
            if wanted and task_id not in wanted and str(row.get("instance_id", "")) not in wanted:
                continue
            grouped[task_id].append((row, ledger_path))

    out_dir = Path(ns.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    all_facts: list[dict[str, Any]] = []
    for task_id in sorted(grouped):
        facts = build_task_facts(
            task_id, grouped[task_id], bundles=bundles, grading_bundles_path=Path(ns.grading_bundles),
            log_index=log_index, artifacts_by_digest=artifacts_by_digest, artifact_dirs=artifact_dirs,
            oracle=oracle, include_full_maps=ns.full_status_maps,
        )
        task_dir = out_dir / facts["instance_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        # 增量落盘：每题写完就落，后续题失败不影响已完成的题。
        (task_dir / "facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        all_facts.append(facts)

    (out_dir / "reconcile.md").write_text(render_reconcile(all_facts), encoding="utf-8")
    summary = build_summary(all_facts, {
        "inputs": {
            "ledgers": [str(p) for p in ns.ledger],
            "eval_log_dirs": [str(p) for p in ns.eval_log_dir],
            "artifacts_dirs": [str(p) for p in ns.artifacts_dir],
            "grading_bundles": str(ns.grading_bundles),
            "oracle_ledgers": [str(p) for p in ns.oracle_ledger],
            "full_status_maps": bool(ns.full_status_maps),
        },
        "grading_bundles_loaded": len(bundles),
        "grading_bundles_schema_validated": schema_validated,
        "grading_bundles_rejected": rejected,
        "parser_available": parse_eval_log_v2 is not None,
        "parser_unavailable_reason": PARSER_IMPORT_ERROR,
        "ledger_rows_with_unknown_schema": unknown_schema,
    })
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    ns = parse_args(argv)
    try:
        summary = run(ns)
    except FactsError as exc:
        print(f"screening_facts: {exc}", file=sys.stderr)
        return 2
    if not summary["parser_available"]:
        print(f"screening_facts: 警告——repoharness2 不可用（{PARSER_IMPORT_ERROR}），"
              "离线重解析与逐 ID 对账已标成 parser_unavailable；修好后重跑可补齐。", file=sys.stderr)
    print(json.dumps({
        "out_dir": str(ns.out_dir),
        "tasks": summary["tasks"],
        "runs": summary["runs"],
        "run_level_observed_rate": summary["run_level_observed_rate"],
        "parser_available": summary["parser_available"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
