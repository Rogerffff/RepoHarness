"""SWE-Gym Lite → EnvironmentPackage 的 ingestion 构造器（S2-1 T2-c）。

输入（全部为冻结/账本化资产，路径由调用方显式提供）：
  - raw archive（T1a：230 行 × 11 列，冻结 revision 重抓，digest 有账）
  - survivors（data_freeze 静态门存活 216）
  - T1b 键控镜像清单（schema v4，经 `image_manifest_store.load_state`
    严格加载 + `finish_assertions` 全过才允许消费）
  - vendor spec（经 `spec_vendor` 固定注册表；eval_cmd 由派生构造器产生）

输出：v2 三分 bundle + `EnvironmentPackageV1`（216 条，确定性排序）+
duplicate cluster 报告（**只标记不删除**）。

安全/正确性要点（历轮 codex 审查的义务落位）：
  - strip_spec 驱动：11 列与 `SWE_BENCH_FAMILY_FIELD_CLASSES` **双向相等**
    （多列 = 未知字段 fail-closed；少列 = 数据面变动 fail-closed）。常量与
    冻结 yaml 的同步由 digest pin（运行期核对文件）+ 语义等价测试双保险。
  - `hints_text`/`created_at` 等 strip/pipeline_meta 类字段**不进任何 bundle**。
  - survivor 级 D5 断言（真实 join，T1a 原型收编）：held-out 四仓库命中即拒。
  - resolved-package 校验（轮次 12/13 登记）：public 的 image 与
    image_manifest_digest 必须逐字等于键控清单该 instance_id 的记录。
  - 去重语义（轮次 6/8 定案）：任务身份 = source-qualified task_id；
    `(repo_key_lower, base_commit)` 是**环境身份**——同环境多任务合法；
    五重内容 digest（题面/test_patch/F2P/P2P/golden）全等才标记
    suspected_duplicate，且**只入报告供规则/人工判定，绝不自动剔除**。
  - 消费期重验（轮次 12 义务）：`verify_package_relations` 供任何按 digest
    取回 bundle 的消费方（门 runner / T2-d）重跑关系验证——不能只信构造时检查。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from repoharness2.envpack.bundles import PublicTaskBundle, scan_public_bundle
from repoharness2.envpack.bundles_v2 import (
    EnvironmentPackageV1,
    PrivateGradingBundleV2,
    ValidationOnlyBundle,
    build_environment_package,
    build_private_grading_bundle,
)
from repoharness2.envpack.spec_vendor import verify_grading_eval_cmd
from repoharness2.taskset.image_manifest_store import Store, finish_assertions

# ---------------------------------------------------------------------------
# strip_spec 的 swe_bench_family 段（冻结常量；与 yaml 的同步见 digest pin + 测试）
# ---------------------------------------------------------------------------

SWE_BENCH_FAMILY_FIELD_CLASSES: dict[str, str] = {
    "instance_id": "env_materialization",
    "repo": "env_materialization",
    "base_commit": "env_materialization",
    "version": "env_materialization",
    "created_at": "pipeline_meta",
    "problem_statement": "model_visible",
    "hints_text": "strip",
    "patch": "validation_only",
    "test_patch": "grader_only",
    "FAIL_TO_PASS": "grader_only",
    "PASS_TO_PASS": "grader_only",
}

# 冻结 strip_spec.yaml 的内容 digest（data_freeze v0.1 账本值；运行器加载原文件
# 时核对——常量若与文件脱节，这里先红灯）。
STRIP_SPEC_SHA256 = "e96af018a660274c716e41fcdb10357c5892fa355d5d0998f2bc9b5e865ecd9c"

# D5 不变量：held-out 四仓库（frozen 规则按 basename 判，见 heldout_proposal）
HELDOUT_BASENAMES: frozenset[str] = frozenset({"tornado", "pyramid", "hydra", "bokeh"})

EXPECTED_SURVIVOR_COUNT = 216


class IngestError(ValueError):
    """ingestion fail-closed 异常（未知字段/D5 命中/身份不一致/输入不完整）。"""


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class DuplicateCluster:
    """同环境身份（repo_key_lower + base_commit）的任务簇（>1 成员才成簇）。"""

    repo_key_lower: str
    base_commit: str
    members: dict[str, dict[str, str]]  # instance_id -> 五重内容 digest
    classification: str  # distinct_tasks_shared_environment | suspected_duplicate

    def to_json(self) -> dict:
        return {
            "repo_key_lower": self.repo_key_lower,
            "base_commit": self.base_commit,
            "members": self.members,
            "classification": self.classification,
        }


@dataclass
class IngestResult:
    packages: list[EnvironmentPackageV1] = field(default_factory=list)
    public_bundles: list[PublicTaskBundle] = field(default_factory=list)
    grading_bundles: list[PrivateGradingBundleV2] = field(default_factory=list)
    validation_bundles: list[ValidationOnlyBundle] = field(default_factory=list)
    duplicate_clusters: list[DuplicateCluster] = field(default_factory=list)


def check_strip_spec_fields(row: dict) -> None:
    """11 列双向相等：多列（未知字段）与少列（数据面变动）都 fail-closed。"""
    keys = set(row)
    spec = set(SWE_BENCH_FAMILY_FIELD_CLASSES)
    unknown = keys - spec
    missing = spec - keys
    if unknown:
        raise IngestError(f"{row.get('instance_id', '?')}: strip_spec 未列字段（fail-closed）: {sorted(unknown)}")
    if missing:
        raise IngestError(f"{row.get('instance_id', '?')}: 行缺 strip_spec 声明字段: {sorted(missing)}")


def _as_test_list(value, what: str, iid: str) -> list[str]:
    if isinstance(value, str):  # 兼容 JSON 字符串编码（Verified 家族部分发行形态）
        value = json.loads(value)
    if not isinstance(value, list) or not all(isinstance(x, str) and x for x in value):
        raise IngestError(f"{iid}: {what} 不是非空字符串列表")
    return list(value)


def build_task(row: dict, image_entry: dict, *,
               raw_archive_sha256: str, image_manifest_keyed_sha256: str):
    """单题：raw 行 + 键控镜像条目 → (public, grading, validation, package)。"""
    check_strip_spec_fields(row)
    iid = row["instance_id"]

    # D5（真实 join 语义：调用方已按 survivor 选行，此处按行内 repo 再断言）
    if row["repo"].split("/")[-1].lower() in HELDOUT_BASENAMES:
        raise IngestError(f"{iid}: D5 违反——repo {row['repo']} 属 held-out 仓库")

    if image_entry.get("instance_id") != iid:
        raise IngestError(f"{iid}: 键控镜像条目 instance_id 不符: {image_entry.get('instance_id')!r}")

    statement = row["problem_statement"]
    public = PublicTaskBundle(
        instance_id=iid,
        repo=row["repo"],
        base_commit=row["base_commit"],
        image=image_entry["source_image_ref"],
        image_manifest_digest=image_entry["resolved_manifest_digest"],
        problem_statement=statement,
        problem_statement_sha256=_sha256_text(statement),
    )
    scan_public_bundle(public)  # 模型可见面泄漏扫描（v1 第三道防线复用）

    grading = build_private_grading_bundle(
        instance_id=iid,
        repo=row["repo"],
        version=row["version"],
        base_commit=row["base_commit"],
        test_patch=row["test_patch"],
        fail_to_pass=_as_test_list(row["FAIL_TO_PASS"], "FAIL_TO_PASS", iid),
        pass_to_pass=_as_test_list(row["PASS_TO_PASS"], "PASS_TO_PASS", iid),
    )
    validation = ValidationOnlyBundle(
        instance_id=iid,
        golden_patch=row["patch"],
        golden_patch_sha256=_sha256_text(row["patch"]),
    )
    package = build_environment_package(
        public=public, grading=grading, validation=validation,
        raw_archive_sha256=raw_archive_sha256,
        image_manifest_keyed_sha256=image_manifest_keyed_sha256,
    )
    return public, grading, validation, package


def _member_fingerprint(row: dict) -> dict[str, str]:
    return {
        "problem_statement_sha256": _sha256_text(row["problem_statement"]),
        "test_patch_sha256": _sha256_text(row["test_patch"]),
        "fail_to_pass_sha256": _sha256_text(json.dumps(sorted(row["FAIL_TO_PASS"]))),
        "pass_to_pass_sha256": _sha256_text(json.dumps(sorted(row["PASS_TO_PASS"]))),
        "golden_patch_sha256": _sha256_text(row["patch"]),
    }


def build_duplicate_clusters(rows: list[dict]) -> list[DuplicateCluster]:
    """环境身份分组 → 五重内容 digest 判定。只标记，不删除。"""
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        groups.setdefault((r["repo"].lower(), r["base_commit"]), []).append(r)
    clusters: list[DuplicateCluster] = []
    for (repo_l, commit), members in sorted(groups.items()):
        if len(members) < 2:
            continue
        fps = {m["instance_id"]: _member_fingerprint(m) for m in members}
        ids = sorted(fps)
        suspected = any(
            fps[a] == fps[b] for i, a in enumerate(ids) for b in ids[i + 1:]
        )
        clusters.append(DuplicateCluster(
            repo_key_lower=repo_l, base_commit=commit, members=fps,
            classification=("suspected_duplicate" if suspected
                            else "distinct_tasks_shared_environment"),
        ))
    return clusters


def ingest_swegym_lite(*, rows: list[dict], survivors: list[str],
                       image_store: Store, raw_archive_sha256: str,
                       image_manifest_keyed_sha256: str) -> IngestResult:
    """216 题主入口。任何一步 fail-closed，不产出半成品。"""
    if len(survivors) != EXPECTED_SURVIVOR_COUNT or len(set(survivors)) != EXPECTED_SURVIVOR_COUNT:
        raise IngestError(f"survivors 数量/唯一性异常: {len(survivors)}")
    problems = finish_assertions(image_store, set(survivors))
    if problems:
        raise IngestError("键控镜像清单未达完成态，拒绝消费：\n  " + "\n  ".join(problems))

    by_id = {r["instance_id"]: r for r in rows}
    missing = [s for s in survivors if s not in by_id]
    if missing:
        raise IngestError(f"{len(missing)} 个 survivor 不在 raw 行中: {missing[:5]}")

    result = IngestResult()
    picked = []
    for iid in sorted(survivors):
        row = by_id[iid]
        public, grading, validation, package = build_task(
            row, image_store.entries[iid],
            raw_archive_sha256=raw_archive_sha256,
            image_manifest_keyed_sha256=image_manifest_keyed_sha256,
        )
        result.public_bundles.append(public)
        result.grading_bundles.append(grading)
        result.validation_bundles.append(validation)
        result.packages.append(package)
        picked.append(row)
    result.duplicate_clusters = build_duplicate_clusters(picked)
    return result


def verify_package_relations(package: EnvironmentPackageV1,
                             public: PublicTaskBundle,
                             grading: PrivateGradingBundleV2,
                             validation: ValidationOnlyBundle,
                             image_store: Store | None = None) -> None:
    """消费期重验（codex 轮次 12 义务）：按 digest 取回 bundle 后必须重跑本函数，
    不能只信构造时检查。image_store 提供时同时核对镜像身份。"""
    errs: list[str] = []
    if package.public_bundle_digest != public.digest():
        errs.append("public digest 不符")
    if package.grading_bundle_digest != grading.digest():
        errs.append("grading digest 不符")
    if package.validation_bundle_digest != validation.digest():
        errs.append("validation digest 不符")
    if not (package.instance_id == public.instance_id == grading.instance_id == validation.instance_id):
        errs.append("instance_id 四方不一致")
    if not (package.repo == public.repo == grading.repo):
        errs.append("repo 三方不一致")
    if not (package.base_commit == public.base_commit == grading.base_commit):
        errs.append("base_commit 三方不一致")
    if (package.image, package.image_manifest_digest) != (public.image, public.image_manifest_digest):
        errs.append("镜像身份 package↔public 不符")
    if image_store is not None:
        entry = image_store.entries.get(package.instance_id)
        if entry is None:
            errs.append("键控清单无该 instance_id")
        elif (entry["source_image_ref"], entry["resolved_manifest_digest"]) != (
                package.image, package.image_manifest_digest):
            errs.append("镜像身份与键控清单不符")
    if errs:
        raise IngestError(f"{package.instance_id}: 消费期关系验证失败: {'; '.join(errs)}")
    verify_grading_eval_cmd(grading)  # eval_cmd 第 N 道互检（消费期防线）


def write_ingest_outputs(result: IngestResult, out_dir: Path) -> dict[str, str]:
    """确定性落盘（instance_id 排序 + 键排序），返回 {相对文件名: sha256}。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    digests: dict[str, str] = {}

    def _dump_jsonl(name: str, models) -> None:
        payload = "".join(
            json.dumps(m.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n"
            for m in models
        ).encode("utf-8")
        (out_dir / name).write_bytes(payload)
        digests[name] = hashlib.sha256(payload).hexdigest()

    _dump_jsonl("environment_packages_v0.jsonl", result.packages)
    _dump_jsonl("public_bundles_v0.jsonl", result.public_bundles)
    _dump_jsonl("grading_bundles_v2_v0.jsonl", result.grading_bundles)
    _dump_jsonl("validation_bundles_v0.jsonl", result.validation_bundles)
    clusters_payload = (json.dumps(
        [c.to_json() for c in result.duplicate_clusters],
        ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")
    (out_dir / "duplicate_clusters_v0.json").write_bytes(clusters_payload)
    digests["duplicate_clusters_v0.json"] = hashlib.sha256(clusters_payload).hexdigest()
    return digests
