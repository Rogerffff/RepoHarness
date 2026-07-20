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
from repoharness2.envpack.spec_vendor import vendor_pin, verify_grading_eval_cmd
from repoharness2.envpack.t1_pins import T1InputPins
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
    if len(set(value)) != len(value):  # 轮次 14 一般 3：内部重复拒绝
        raise IngestError(f"{iid}: {what} 含重复测试项")
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

    f2p = _as_test_list(row["FAIL_TO_PASS"], "FAIL_TO_PASS", iid)
    p2p = _as_test_list(row["PASS_TO_PASS"], "PASS_TO_PASS", iid)
    overlap = set(f2p) & set(p2p)
    if overlap:  # 轮次 14 一般 3：同一测试不能既是 F2P 又是 P2P
        raise IngestError(f"{iid}: FAIL_TO_PASS 与 PASS_TO_PASS 交集非空: {sorted(overlap)[:3]}")
    grading = build_private_grading_bundle(
        instance_id=iid,
        repo=row["repo"],
        version=row["version"],
        base_commit=row["base_commit"],
        test_patch=row["test_patch"],
        fail_to_pass=f2p,
        pass_to_pass=p2p,
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
    iid = row["instance_id"]
    return {
        "problem_statement_sha256": _sha256_text(row["problem_statement"]),
        "test_patch_sha256": _sha256_text(row["test_patch"]),
        "fail_to_pass_sha256": _sha256_text(
            json.dumps(sorted(_as_test_list(row["FAIL_TO_PASS"], "FAIL_TO_PASS", iid)))),
        "pass_to_pass_sha256": _sha256_text(
            json.dumps(sorted(_as_test_list(row["PASS_TO_PASS"], "PASS_TO_PASS", iid)))),
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


def build_duplicate_clusters_from_bundles(publics, gradings, validations) -> list[DuplicateCluster]:
    """从已加载 bundle 重构行事实并复算簇（loader 的"声明不可信，重算才可信"）。"""
    g_by = {g.instance_id: g for g in gradings}
    v_by = {v.instance_id: v for v in validations}
    rows = []
    for pub in publics:
        g = g_by[pub.instance_id]
        v = v_by[pub.instance_id]
        rows.append({
            "instance_id": pub.instance_id,
            "repo": pub.repo,
            "base_commit": pub.base_commit,
            "problem_statement": pub.problem_statement,
            "test_patch": g.test_patch,
            "FAIL_TO_PASS": list(g.fail_to_pass),
            "PASS_TO_PASS": list(g.pass_to_pass),
            "patch": v.golden_patch,
        })
    return build_duplicate_clusters(rows)


def ingest_swegym_lite(*, rows: list[dict], survivors: list[str],
                       image_store: Store, raw_archive_sha256: str,
                       image_manifest_keyed_sha256: str) -> IngestResult:
    """216 题主入口。任何一步 fail-closed，不产出半成品。"""
    # 输入行损坏最先报（字段面 + 重复 id），再做 survivor 面与镜像面检查
    by_id: dict[str, dict] = {}
    for r in rows:
        check_strip_spec_fields(r)  # 轮次 14 一般 3：全部行（230）先过字段面，不只选中 216
        iid_r = r["instance_id"]
        if iid_r in by_id:
            raise IngestError(f"raw 行重复 instance_id: {iid_r}（fail-closed，不静默覆盖）")
        by_id[iid_r] = r
    if len(survivors) != EXPECTED_SURVIVOR_COUNT or len(set(survivors)) != EXPECTED_SURVIVOR_COUNT:
        raise IngestError(f"survivors 数量/唯一性异常: {len(survivors)}")
    problems = finish_assertions(image_store, set(survivors))
    if problems:
        raise IngestError("键控镜像清单未达完成态，拒绝消费：\n  " + "\n  ".join(problems))
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


def _relation_errors(package: EnvironmentPackageV1, public: PublicTaskBundle,
                     grading: PrivateGradingBundleV2,
                     validation: ValidationOnlyBundle) -> list[str]:
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
    return errs


def verify_bundle_relations_non_authoritative(package: EnvironmentPackageV1,
                                              public: PublicTaskBundle,
                                              grading: PrivateGradingBundleV2,
                                              validation: ValidationOnlyBundle) -> None:
    """**非权威**关系检查（合成夹具单测用）：不核 T1 pins、不核镜像清单、
    不做消费期泄漏扫描。正式消费方一律用 `verify_package_relations`。"""
    errs = _relation_errors(package, public, grading, validation)
    if errs:
        raise IngestError(f"{package.instance_id}: 关系验证失败: {'; '.join(errs)}")
    verify_grading_eval_cmd(grading)


def verify_package_relations(package: EnvironmentPackageV1,
                             public: PublicTaskBundle,
                             grading: PrivateGradingBundleV2,
                             validation: ValidationOnlyBundle,
                             *, pins: T1InputPins, image_store: Store) -> None:
    """strict 消费期重验（codex 轮次 12 义务 + 轮次 14 严重 2 封旁路）：
    pins 与 image_store 都是**必传**——不存在"忘传就静默跳过"的降级路径。

    无条件验证：四方 digest/身份关系、镜像身份对键控清单、provenance 三 digest
    对可信 pins/注册表、eval_cmd 注册表互检、public 面消费期泄漏扫描。"""
    errs = _relation_errors(package, public, grading, validation)
    entry = image_store.entries.get(package.instance_id)
    if entry is None:
        errs.append("键控清单无该 instance_id")
    elif (entry["source_image_ref"], entry["resolved_manifest_digest"]) != (
            package.image, package.image_manifest_digest):
        errs.append("镜像身份与键控清单不符")
    # provenance 三 digest：raw/keyed 对封板 pins；vendor 对固定注册表（轮次 14 旁路 1/2）
    if package.raw_archive_sha256 != "sha256:" + pins.raw_archive:
        errs.append("raw_archive_sha256 与 T1 封板 pin 不符")
    if package.image_manifest_keyed_sha256 != "sha256:" + pins.image_manifest_keyed:
        errs.append("image_manifest_keyed_sha256 与 T1 封板 pin 不符")
    if package.spec_vendor_json_sha256 != "sha256:" + vendor_pin(grading.spec_vendor_id).json_sha256:
        errs.append("spec_vendor_json_sha256 与固定注册表不符")
    if errs:
        raise IngestError(f"{package.instance_id}: 消费期关系验证失败: {'; '.join(errs)}")
    verify_grading_eval_cmd(grading)   # eval_cmd 消费期互检
    scan_public_bundle(public)         # 消费期泄漏扫描（轮次 14 旁路 4）


INGEST_MANIFEST_NAME = "ingest_manifest_v0.json"
INGEST_MANIFEST_SCHEMA_ID = "rh2.s2_1.ingest_manifest.v1"
_DATA_FILES = (
    "environment_packages_v0.jsonl",
    "public_bundles_v0.jsonl",
    "grading_bundles_v2_v0.jsonl",
    "validation_bundles_v0.jsonl",
    "duplicate_clusters_v0.json",
)


def _atomic_write(path: Path, payload: bytes) -> None:
    import os
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def write_ingest_outputs(result: IngestResult, out_dir: Path, *,
                         pins: T1InputPins) -> dict[str, str]:
    """事务化落盘（轮次 14 一般 4）：五数据文件逐个原子写，最后原子写
    `ingest_manifest_v0.json` 作为**提交记录**（五文件 digest + 行数 +
    T1 输入 pins）。崩溃只可能留下"数据文件超前、无提交记录更新"的状态，
    严格 loader 以提交记录为准。返回 {文件名: sha256}（含提交记录自身）。

    pins **必传**（轮次 15 一般 4）：正式 writer 不许写出 strict loader
    永远无法接受的无 pins 产物；测试需要无权威写出时用
    `write_ingest_outputs_for_tests`（显式命名，产物不可进正式消费链）。"""
    digests: dict[str, str] = {}
    counts: dict[str, int] = {}

    def _payload_jsonl(models) -> bytes:
        return "".join(
            json.dumps(m.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n"
            for m in models
        ).encode("utf-8")

    payloads = {
        "environment_packages_v0.jsonl": _payload_jsonl(result.packages),
        "public_bundles_v0.jsonl": _payload_jsonl(result.public_bundles),
        "grading_bundles_v2_v0.jsonl": _payload_jsonl(result.grading_bundles),
        "validation_bundles_v0.jsonl": _payload_jsonl(result.validation_bundles),
        "duplicate_clusters_v0.json": (json.dumps(
            [c.to_json() for c in result.duplicate_clusters],
            ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8"),
    }
    line_counts = {
        "environment_packages_v0.jsonl": len(result.packages),
        "public_bundles_v0.jsonl": len(result.public_bundles),
        "grading_bundles_v2_v0.jsonl": len(result.grading_bundles),
        "validation_bundles_v0.jsonl": len(result.validation_bundles),
        "duplicate_clusters_v0.json": len(result.duplicate_clusters),
    }
    for name in _DATA_FILES:
        _atomic_write(out_dir / name, payloads[name])
        digests[name] = hashlib.sha256(payloads[name]).hexdigest()
        counts[name] = line_counts[name]

    manifest = {
        "schema_id": INGEST_MANIFEST_SCHEMA_ID,
        "files": {n: {"sha256": digests[n], "count": counts[n]} for n in _DATA_FILES},
        "package_count": len(result.packages),
        "t1_input_pins": {k: getattr(pins, k) for k in sorted(vars(pins))},
    }
    mp = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")
    _atomic_write(out_dir / INGEST_MANIFEST_NAME, mp)
    digests[INGEST_MANIFEST_NAME] = hashlib.sha256(mp).hexdigest()
    return digests


def write_ingest_outputs_for_tests(result: IngestResult, out_dir: Path) -> dict[str, str]:
    """**test-only**：无权威 pins 写出（t1_input_pins 全零占位）。产物永远过不了
    strict loader 的 pins 对账——只用于确定性/字节级单测，绝不进正式消费链。"""
    placeholder = T1InputPins(**{k: "0" * 64 for k in (
        "raw_archive", "image_manifest_keyed", "image_registry_evidence",
        "survivors", "image_refs", "strip_spec", "vendor_specs_json")})
    return write_ingest_outputs(result, out_dir, pins=placeholder)


def load_ingest_outputs(out_dir: Path, *, pins: T1InputPins,
                        image_store: Store,
                        expected_survivors: set[str]) -> IngestResult:
    """strict loader（轮次 14 一般 4 + 轮次 15 严重 2 全集绑定）。链条：
    提交记录严格字段/类型 → 五文件 digest → 模型解析 → 重复 id 拒绝 →
    **四方 id 集合 == 可信 survivor 全集**（裁剪成子集必被拒）→ image_store
    重跑完成断言 → 逐包 strict 验证 → duplicate clusters 由已加载 bundle
    **重算并逐字比对**（声明计数造假必红灯）。

    本函数不验证提交记录的外部锚（代码 pin）——正式消费请用
    `load_trusted_ingest_outputs`（T2-d/e 唯一正式入口）。"""
    mp = out_dir / INGEST_MANIFEST_NAME
    if not mp.exists():
        raise IngestError(f"提交记录缺失: {INGEST_MANIFEST_NAME}")
    manifest = json.loads(mp.read_text())
    # 提交记录严格字段/类型（轮次 15 严重 2：不许多键少键，计数必须真 int）
    if set(manifest) != {"schema_id", "files", "package_count", "t1_input_pins"}:
        raise IngestError(f"提交记录顶层键集合不符: {sorted(manifest)}")
    if manifest.get("schema_id") != INGEST_MANIFEST_SCHEMA_ID:
        raise IngestError(f"提交记录 schema_id 非法: {manifest.get('schema_id')!r}")
    if type(manifest["package_count"]) is not int or manifest["package_count"] < 0:
        raise IngestError("package_count 不是非负 int")
    recorded_pins = manifest.get("t1_input_pins") or {}
    for k in sorted(vars(pins)):
        if recorded_pins.get(k) != getattr(pins, k):
            raise IngestError(f"提交记录的 t1_input_pins.{k} 与封板 pins 不符")
    files = manifest.get("files", {})
    if set(files) != set(_DATA_FILES):
        raise IngestError("提交记录 files 键集合不符")
    for name, ent in files.items():
        if set(ent) != {"sha256", "count"}:
            raise IngestError(f"{name}: 提交记录条目键集合不符")
        if type(ent["count"]) is not int or ent["count"] < 0:
            raise IngestError(f"{name}: count 不是非负 int")
    for name in _DATA_FILES:
        p = out_dir / name
        if not p.exists():
            raise IngestError(f"数据文件缺失: {name}")
        actual = hashlib.sha256(p.read_bytes()).hexdigest()
        if actual != files[name]["sha256"]:
            raise IngestError(f"{name}: digest 与提交记录不符（数据文件被改/半写）")

    def _load_models(name: str, cls):
        out = []
        seen: set[str] = set()
        for line in (out_dir / name).read_text().splitlines():
            if not line.strip():
                continue
            m = cls.model_validate(json.loads(line))
            if m.instance_id in seen:
                raise IngestError(f"{name}: 重复 instance_id {m.instance_id}")
            seen.add(m.instance_id)
            out.append(m)
        if len(out) != files[name]["count"]:
            raise IngestError(f"{name}: 行数 {len(out)} 与提交记录 {files[name]['count']} 不符")
        return out

    result = IngestResult(
        packages=_load_models("environment_packages_v0.jsonl", EnvironmentPackageV1),
        public_bundles=_load_models("public_bundles_v0.jsonl", PublicTaskBundle),
        grading_bundles=_load_models("grading_bundles_v2_v0.jsonl", PrivateGradingBundleV2),
        validation_bundles=_load_models("validation_bundles_v0.jsonl", ValidationOnlyBundle),
    )
    ids = [
        {m.instance_id for m in result.packages},
        {m.instance_id for m in result.public_bundles},
        {m.instance_id for m in result.grading_bundles},
        {m.instance_id for m in result.validation_bundles},
    ]
    if not (ids[0] == ids[1] == ids[2] == ids[3]):
        raise IngestError("四文件 instance_id 集合不一致")
    # 全集绑定（轮次 15 严重 2）：等于可信 survivor 集合，而非只彼此相等
    if ids[0] != set(expected_survivors):
        raise IngestError(
            f"包集合 != 可信 survivor 全集（{len(ids[0])} vs {len(expected_survivors)}；"
            f"缺 {sorted(set(expected_survivors) - ids[0])[:3]}）")
    if manifest["package_count"] != len(result.packages):
        raise IngestError(
            f"package_count={manifest['package_count']} 与实际 {len(result.packages)} 不符")
    problems = finish_assertions(image_store, set(expected_survivors))
    if problems:
        raise IngestError("image store 完成断言不过：\n  " + "\n  ".join(problems))
    by = {
        "public": {m.instance_id: m for m in result.public_bundles},
        "grading": {m.instance_id: m for m in result.grading_bundles},
        "validation": {m.instance_id: m for m in result.validation_bundles},
    }
    for pkg in result.packages:
        verify_package_relations(
            pkg, by["public"][pkg.instance_id], by["grading"][pkg.instance_id],
            by["validation"][pkg.instance_id], pins=pins, image_store=image_store)
    clusters = json.loads((out_dir / "duplicate_clusters_v0.json").read_text())
    result.duplicate_clusters = [
        DuplicateCluster(repo_key_lower=c["repo_key_lower"], base_commit=c["base_commit"],
                         members=c["members"], classification=c["classification"])
        for c in clusters
    ]
    if files["duplicate_clusters_v0.json"]["count"] != len(result.duplicate_clusters):
        raise IngestError("duplicate cluster 声明计数与内容不符")
    # 簇由已加载 bundle 重算并逐字比对（轮次 15 严重 2：声明不可信，重算才可信）
    recomputed = build_duplicate_clusters_from_bundles(
        result.public_bundles, result.grading_bundles, result.validation_bundles)
    if [c.to_json() for c in recomputed] != [c.to_json() for c in result.duplicate_clusters]:
        raise IngestError("duplicate clusters 与按 bundle 重算结果不符")
    return result


# ---------------------------------------------------------------------------
# T2-c 输出外部锚 + 唯一正式消费入口（codex 轮次 15 严重 1 / 一般 4）
# ---------------------------------------------------------------------------

# 真实 216 题产物提交记录（s2/ingest/ingest_manifest_v0.json）的 sha256 pin。
# 与 t1_pins 同律：本文件被 S1 账本 rglob 追踪 → 代码 → 提交记录 → 五数据
# 文件的防篡改链。重新生成产物 = 修改本常量 = 账本可见的审计事件。
INGEST_MANIFEST_SHA256_PIN = "3408bab759b0a22ea2f038b908f298c8a1c241d2f710500c52224f14125003a7"
INGEST_OUT_RELPATH = "docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest"


@dataclass
class TrustedIngest:
    """load_trusted_ingest_outputs 的返回：结果 + 下游继续验证所需的可信上下文。"""

    result: IngestResult
    pins: T1InputPins
    image_store: Store
    survivors: list[str]


def load_trusted_ingest_outputs(repo_root: Path) -> TrustedIngest:
    """T2-d/e 的**唯一正式消费入口**（轮次 15 一般 4）：调用方不自行拼装
    可能未经验证的 pins/store。链条：

      1. T1 封板 pins 三级验证（代码常量 → pins 记录 → 七输入文件）；
      2. survivors 从 pins 已验文件读出；image store 严格加载 + 完成断言；
      3. 提交记录对**代码 pin** 验证（轮次 15 严重 1：T1 pins 只证输入未漂移，
         不证输出由输入派生——外部锚补上这一环；一致性篡改整套产物也会
         在此红灯，因为攻击者改不了账本内的代码常量）；
      4. `load_ingest_outputs` 严格解析 + 全集绑定 + 逐包验证 + 簇重算。
    """
    from repoharness2.envpack.t1_pins import load_and_verify_t1_pins
    from repoharness2.taskset.image_manifest_store import load_state

    pins = load_and_verify_t1_pins(repo_root)
    docs = repo_root / "docs/agentic_RL/repo_harness_rh2_workstreams"
    survivors = [x.strip() for x in
                 (docs / "data_freeze/labels/static_gate_survivors.txt").read_text().splitlines()
                 if x.strip()]
    frozen_refs = {x.strip() for x in
                   (docs / "data_freeze/meta/image_refs_swegym.txt").read_text().splitlines()
                   if x.strip()}
    refs_digest = pins.image_refs

    def _expected_ref(iid: str) -> str:
        return f"xingyaoww/sweb.eval.x86_64.{iid.replace('__', '_s_').lower()}:latest"

    image_store = load_state(
        docs / "s2/image_manifest_keyed.json",
        docs / "s2/raw/image_registry_evidence.jsonl",
        set(survivors), frozen_refs, refs_digest, _expected_ref,
    )
    out_dir = repo_root / INGEST_OUT_RELPATH
    mp = out_dir / INGEST_MANIFEST_NAME
    if not mp.exists():
        raise IngestError("提交记录缺失（trusted 入口）")
    actual = hashlib.sha256(mp.read_bytes()).hexdigest()
    if actual != INGEST_MANIFEST_SHA256_PIN:
        raise IngestError(
            f"提交记录与代码 pin 不符（actual {actual[:16]}… != pin "
            f"{INGEST_MANIFEST_SHA256_PIN[:16]}…）——输出面被改或未经审计重生成，拒绝消费")
    result = load_ingest_outputs(out_dir, pins=pins, image_store=image_store,
                                 expected_survivors=set(survivors))
    return TrustedIngest(result=result, pins=pins, image_store=image_store,
                         survivors=survivors)
