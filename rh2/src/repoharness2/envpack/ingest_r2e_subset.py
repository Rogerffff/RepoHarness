"""R2E-Gym-Subset 48 题 ingestion（R2E 接线 R-a，2026-09-20；用户决定 DR1=A）。

与 `ingest_swegym_lite` 并列、同纪律（任何一步 fail-closed，不产出半成品），形状不同：

```text
来源原始行（48 行，14 列）─┐
镜像实测事实表（M3，48 条）─┼─► PublicTaskBundle            题面 / 镜像 / workdir / base_commit
固定版本的上游规则源文件 ──┘    PrivateGradingBundleR2E      期望状态映射原文 / run_tests.sh 原文 / 隐藏测试清单
                                ValidationOnlyBundle         gold（上游 extract_gold_patch 由 parsed_commit_content 重建）
                                EnvironmentPackageV1(source="r2e_gym_subset")
```

为什么要镜像事实表这第二份输入：来源行的 `old_commit_hash` 只有符号形式（`"<commit>^"`），40 位的基线提交、
`run_tests.sh` 的逐字原文、`/r2e_tests` 的文件清单与摘要都只存在于镜像里——它们取自 M3 对 48 张镜像的实测
（`runs/env_overnight_20260916/M3/r2e_image_facts.json` 的逐字节副本）。两份输入之间能互检的都互检
（镜像引用、数据 revision、期望键数）。

可信输入链与 SWE 同构：代码常量 → pins 记录 → 四项输入文件；代码常量 → 提交记录 → 四个数据文件。
正式消费入口只有 `load_trusted_r2e_ingest_outputs`。

本片（接线阶段）**不做**的事：不筛题、不去重（用户决定 DR4）。已知事实照原样带入：coveragepy `97997d2c` 与
`f5eb5f21` 共用同一个基线提交（同环境不同任务）。

**材料修订（2026-09-24 起）**：来源缺陷按用户逐项批准的修订单修正，第五项封板输入
`s2_r2e/revisions/material_revisions_v3.json`（v1 / v2 保留为历史）。四类修订：期望文本替换（只改状态值）、
整份期望替换（允许增删键，必须逐键声明变化）、隐藏测试文本替换、隐藏测试新增文件；每条都记修订前后的
sha256，ingest 从来源原文出发重放或读取，摘要与声明都对上才用修订后的内容，评分面的 `material_revisions`
字段记下修订编号。来源原件与原摘要不丢：原始行、镜像事实表都不改，修订单里就有原摘要。逐条内容与批准出处
见修订单本身（T0-1 / T0-2 / T0-5 / T0-6 / T0-7）。

**第五类：题面文本替换**（2026-09-29 实现，统一标准 v1 §5 R-f / §9 D6；经 Codex 复核后才用于正式材料）：
`statement_text_replace` 在构建公开面之前把 `edits` 作用在来源题面上，公开面的题面与题面摘要都是修订后的；
评分材料不变。修订编号走同一条记录路径（评分面 `material_revisions`、提交记录、pins 里的修订单摘要），
修订后的题由此可识别为标明版本的自建题。
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, replace
from pathlib import Path

from repoharness2.envpack.bundles import PublicTaskBundle, scan_public_bundle
from repoharness2.envpack.bundles_v2 import (
    TASK_SOURCE_R2E_GYM_SUBSET,
    EnvironmentPackageV1,
    PrivateGradingBundleR2E,
    R2EHiddenTestFile,
    ValidationOnlyBundle,
    build_environment_package,
    r2e_hidden_tests_tree_digest,
    r2e_instance_id_for,
)
from repoharness2.envpack.r2e_parsers import (
    R2E_DATASET,
    R2E_DATASET_REVISION,
    R2E_RULE_SOURCE_ID,
    extract_gold_patch,
    normalize_status_map,
    r2e_rule_source_pin,
)

# 来源 14 列的归属（多列 / 少列都 fail-closed——数据面变动必须先改这张表）。
R2E_SUBSET_FIELD_CLASSES: dict[str, str] = {
    "repo_name": "public_identity",
    "docker_image": "public_identity",
    "commit_hash": "public_identity",
    "problem_statement": "public",
    "expected_output_json": "grading_private",
    "parsed_commit_content": "validation_only",      # gold 的原料（含修复前后的完整文件内容）
    # 以下不进任何面：
    "execution_result_content": "dropped",           # 来源侧的执行记录（含测试输出与测试代码）
    "modified_files": "dropped",                     # 修复提交改了哪些文件 = 定位答案
    "modified_entity_summaries": "dropped",
    "relevant_files": "dropped",
    "num_non_test_files": "dropped",
    "num_non_test_func_methods": "dropped",
    "num_non_test_lines": "dropped",
    "prompt": "dropped",                             # 造题指令（让 LLM 据 commit diff 写 issue），不是 solver 输入
}

EXPECTED_TASK_COUNT = 48
IMAGE_FACTS_SCHEMA = "rh2.env_overnight.m3.r2e_image_facts.v1"
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HIDDEN_TESTS_ROOT = "/r2e_tests/"

_DOCS = "docs/agentic_RL/repo_harness_rh2_workstreams"
R2E_RAW_ARCHIVE_RELPATH = f"{_DOCS}/s2_r2e/raw/r2e_gym_subset_48_e8b9fcbc.jsonl"
R2E_SOURCE_REVISION_RELPATH = f"{_DOCS}/s2_r2e/raw/r2e_subset.revision"
R2E_IMAGE_FACTS_RELPATH = f"{_DOCS}/s2_r2e/raw/r2e_image_facts_m3_48.json"
R2E_INGEST_OUT_RELPATH = f"{_DOCS}/s2_r2e/ingest"


class R2EIngestError(ValueError):
    """R2E ingestion fail-closed 异常（未知字段 / 输入互检不符 / 身份不一致 / 输入不完整）。"""


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 输入一：镜像实测事实表
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class R2EImageFact:
    """一张来源镜像的实测事实里 ingestion 要用的那部分（其余观测留在事实表原文里，不进产物）。"""

    commit_hash: str
    repo: str
    source_image_ref: str
    manifest_digest: str          # "sha256:…"（docker RepoDigests 里 @ 之后的部分）
    head_commit: str              # 镜像内 /testbed 的 HEAD
    workdir: str
    run_tests_sh: str
    run_tests_sh_sha256: str      # "sha256:…"
    hidden_files: tuple[tuple[str, str], ...]   # (相对 r2e_tests/ 的路径, "sha256:…")
    expected_n: int


def parse_r2e_image_facts(doc: dict) -> dict[str, R2EImageFact]:
    """事实表 → {commit_hash: R2EImageFact}。结构或内部一致性不符即拒。"""

    if doc.get("schema") != IMAGE_FACTS_SCHEMA:
        raise R2EIngestError(f"镜像事实表 schema 非法: {doc.get('schema')!r}")
    tasks = doc.get("tasks")
    if not isinstance(tasks, list) or doc.get("n") != len(tasks):
        raise R2EIngestError("镜像事实表 n 与 tasks 条数不符")
    out: dict[str, R2EImageFact] = {}
    for t in tasks:
        commit = t.get("commit_hash", "")
        where = f"镜像事实 {commit[:12] or '?'}"
        if not _HEX40.match(commit):
            raise R2EIngestError(f"{where}: commit_hash 不是 40 位 hex")
        if commit in out:
            raise R2EIngestError(f"{where}: 事实表重复 commit_hash")
        if t.get("collect_status") != "OK":
            raise R2EIngestError(f"{where}: collect_status={t.get('collect_status')!r}（事实采集未完成）")
        if t.get("source") != R2E_DATASET or t.get("source_revision") != R2E_DATASET_REVISION:
            raise R2EIngestError(f"{where}: 来源 / revision 与固定值不符")
        image_ref = t.get("image_ref", "")
        repo_digest = (t.get("image") or {}).get("repo_digest", "")
        digest_repo, _, digest = repo_digest.partition("@")
        if not image_ref.endswith(":" + commit) or digest_repo != image_ref.rsplit(":", 1)[0]:
            raise R2EIngestError(f"{where}: image_ref / repo_digest 与 commit 不自洽: {image_ref!r} / {repo_digest!r}")
        if not re.match(r"^sha256:[0-9a-f]{64}$", digest):
            raise R2EIngestError(f"{where}: repo_digest 不含合法 manifest digest")
        git = t.get("git") or {}
        head = git.get("head", "")
        if not _HEX40.match(head) or git.get("head_is_ancestor_of_fix") != "yes":
            raise R2EIngestError(f"{where}: 镜像 HEAD 事实不成立（head={head!r}, ancestor={git.get('head_is_ancestor_of_fix')!r}）")
        rt = t.get("run_tests_sh") or {}
        rt_text = rt.get("text", "")
        if not rt_text or hashlib.sha256(rt_text.encode("utf-8")).hexdigest() != rt.get("sha256"):
            raise R2EIngestError(f"{where}: run_tests.sh 原文与其记录的 sha256 不符")
        hidden: list[tuple[str, str]] = []
        for f in (t.get("r2e_tests") or {}).get("files") or []:
            path = f.get("path", "")
            if not path.startswith(_HIDDEN_TESTS_ROOT) or not re.match(r"^[0-9a-f]{64}$", f.get("sha256", "")):
                raise R2EIngestError(f"{where}: 隐藏测试条目非法: {path!r}")
            hidden.append((path[len(_HIDDEN_TESTS_ROOT):], "sha256:" + f["sha256"]))
        if not hidden or len(hidden) != (t.get("r2e_tests") or {}).get("n_files"):
            raise R2EIngestError(f"{where}: 隐藏测试清单为空或与 n_files 不符")
        workdir = (t.get("image") or {}).get("workdir", "")
        if workdir != "/testbed":
            raise R2EIngestError(f"{where}: 镜像 workdir={workdir!r}（R2E 入口与隐藏测试路径都写死在 /testbed）")
        out[commit] = R2EImageFact(
            commit_hash=commit,
            repo=t.get("repo", ""),
            source_image_ref=image_ref,
            manifest_digest=digest,
            head_commit=head,
            workdir=workdir,
            run_tests_sh=rt_text,
            run_tests_sh_sha256="sha256:" + rt["sha256"],
            hidden_files=tuple(sorted(hidden)),
            expected_n=int(t.get("expected_n", -1)),
        )
    return out


# ---------------------------------------------------------------------------
# 单题构造
# ---------------------------------------------------------------------------


def check_r2e_row_fields(row: dict) -> None:
    """14 列双向相等：多列（未知字段）与少列（数据面变动）都 fail-closed。"""

    keys, spec = set(row), set(R2E_SUBSET_FIELD_CLASSES)
    who = f"{row.get('repo_name', '?')}@{str(row.get('commit_hash', '?'))[:12]}"
    if keys - spec:
        raise R2EIngestError(f"{who}: 字段归属表未列字段（fail-closed）: {sorted(keys - spec)}")
    if spec - keys:
        raise R2EIngestError(f"{who}: 行缺字段归属表声明的字段: {sorted(spec - keys)}")


# R2E 的公开提示（E09，2026-09-25；用户批准"按来源区分的提示措辞"，交 A 审）。SWE-Gym 的 PUBLIC_SYSTEM_HINTS 说
# "pre-activated conda env named testbed"、"pip 可用"、"grading resets the test files"，三处对 R2E 都不成立：R2E 的解释器是
# /testbed/.venv，27/48 题没有 pip、全池无出网；评分只重放隐藏测试目录与入口脚本，不重置仓库自己的测试文件。这里只改
# 与事实不符的句子，其余指令与 SWE-Gym 版逐句对应。正式链目前不把它注入系统提示，它随 public bundle 写进容器的
# /rh2/public_task_bundle.json，解题者读到时不应被误导。
R2E_PUBLIC_HINTS = (
    "You are a software engineer fixing a real GitHub issue in the repository "
    "checked out at /testbed (your bash tool already runs there).\n"
    "- The project's Python environment is the virtualenv at /testbed/.venv: `python` "
    "and the repo's test tools already point at it. There is no network access and "
    "`pip` may be unavailable, so work with the packages that are already installed.\n"
    "- Explore the code, find the root cause, and edit NON-TEST source files to fix "
    "the issue.\n"
    "- Do NOT modify the repository's test files: the fix is judged by a separate set "
    "of tests.\n"
    "- You may run tests to verify your fix, but keep runs narrow (a single test "
    "file or module) to save time; run them from /testbed with `python -m pytest`.\n"
    "- When you are confident the fix is complete, reply with a short summary and "
    "stop calling tools."
)


# ---------------------------------------------------------------------------
# 输入五：材料修订单（用户逐项批准；2026-09-24 起）
# ---------------------------------------------------------------------------

# v1（material_revisions_v1.json：两类"唯一一处 old→new"修订，T0-1 / T0-2）保留为历史记录。
# v2（2026-09-24 晚，用户批准 T0-5 / T0-6）：文本修订改为 `edits` 列表（逐条恰好一处替换），新增两类——
#   `expected_file_replace`：整份期望换成修订后文件，允许增删键（fixture 恢复后参数化用例会展开），但必须在
#     `expected_change` 里逐键声明变化，ingest 重算差异，对不上即拒；
#   `hidden_test_file_add`：在 r2e_tests/ 下新增来源里没有的文件（可为二进制，如夹具 egg），目标原本不得存在。
# v3（2026-09-24 夜，用户批准 T0-6 第二步与 T0-7 方案 B）：格式与 v2 相同（schema_id 不变），r2e-mr-001…007 逐字不变，
#   新增 r2e-mr-008…020（pandas 另 6 题的私有 conftest 与期望核定；orange3 9b5494e2 两个恢复键的期望，
#   只在 +env_v2 环境配方镜像上成立）。v2 保留为历史。
R2E_MATERIAL_REVISIONS_RELPATH = f"{_DOCS}/s2_r2e/revisions/material_revisions_v11.json"
R2E_MATERIAL_REVISIONS_SCHEMA_ID = "rh2.s2_r2e.material_revisions.v2"
REVISION_KIND_EXPECTED = "expected_text_replace"
REVISION_KIND_EXPECTED_FILE = "expected_file_replace"
REVISION_KIND_HIDDEN_TEST = "hidden_test_text_replace"
REVISION_KIND_HIDDEN_ADD = "hidden_test_file_add"
# 第五类（2026-09-29，统一标准 v1 §5 R-f / §9 D6；经 Codex 复核后才用于正式材料）：题面文本替换。`target` 固定为
#   `problem_statement`，`edits` 语义与 `hidden_test_text_replace` 相同，`revised_file` / `expected_change` 为 null；
#   只改公开面的题面，评分材料不动。修订单格式与 schema_id 不变（v3 里没有这一类，解析结果不变）。
REVISION_KIND_STATEMENT = "statement_text_replace"
STATEMENT_REVISION_TARGET = "problem_statement"
EXPECTED_REVISION_KINDS = frozenset({REVISION_KIND_EXPECTED, REVISION_KIND_EXPECTED_FILE})
HIDDEN_REVISION_KINDS = frozenset({REVISION_KIND_HIDDEN_TEST, REVISION_KIND_HIDDEN_ADD})
_REVISION_KINDS = EXPECTED_REVISION_KINDS | HIDDEN_REVISION_KINDS | frozenset({REVISION_KIND_STATEMENT})
# 期望映射允许的状态词：上游解析器只为这三种结果产出键（SKIPPED / XFAIL 不产出键）。
R2E_EXPECTED_STATUSES = frozenset({"PASSED", "FAILED", "ERROR"})
_REVISION_ID_RE = re.compile(r"^r2e-mr-[0-9]{3}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_REVISION_FIELDS = frozenset({"revision_id", "instance_id", "kind", "target", "edits", "sha256_before", "sha256_after",
                              "revised_file", "expected_change", "decision_ref", "reason", "evidence"})


@dataclass(frozen=True)
class R2EExpectedChange:
    """期望映射的逐键变化（规范化为排序元组，便于比较）：改状态、新增键、删除键。"""

    changed: tuple[tuple[str, str, str], ...] = ()   # (键, 修订前状态, 修订后状态)
    added: tuple[tuple[str, str], ...] = ()          # (键, 状态)
    removed: tuple[str, ...] = ()

    @classmethod
    def diff(cls, before: dict[str, str], after: dict[str, str]) -> "R2EExpectedChange":
        return cls(
            changed=tuple(sorted((k, before[k], after[k]) for k in before if k in after and before[k] != after[k])),
            added=tuple(sorted((k, after[k]) for k in after if k not in before)),
            removed=tuple(sorted(k for k in before if k not in after)),
        )

    @classmethod
    def from_doc(cls, doc: object, *, who: str) -> "R2EExpectedChange":
        """修订单里的声明：`{"changed": {键: [前, 后]}, "added": {键: 状态}, "removed": [键]}`，三项都必须在。"""

        if not isinstance(doc, dict) or set(doc) != {"changed", "added", "removed"}:
            raise R2EIngestError(f"{who}: expected_change 必须恰好含 changed / added / removed")
        changed, added, removed = doc["changed"], doc["added"], doc["removed"]
        if not (isinstance(changed, dict) and isinstance(added, dict) and isinstance(removed, list)):
            raise R2EIngestError(f"{who}: expected_change 的 changed / added 必须是对象、removed 必须是列表")
        statuses = [s for pair in changed.values() for s in (pair if isinstance(pair, list) else [None])] + list(added.values())
        if any(not isinstance(p, list) or len(p) != 2 or p[0] == p[1] for p in changed.values()):
            raise R2EIngestError(f"{who}: expected_change.changed 的值必须是 [修订前, 修订后] 且两者不同")
        if any(s not in R2E_EXPECTED_STATUSES for s in statuses):
            raise R2EIngestError(f"{who}: expected_change 里有非法状态词（只许 {sorted(R2E_EXPECTED_STATUSES)}）")
        if len(set(removed)) != len(removed) or not all(isinstance(k, str) and k for k in removed):
            raise R2EIngestError(f"{who}: expected_change.removed 必须是不重复的非空键")
        out = cls(
            changed=tuple(sorted((k, v[0], v[1]) for k, v in changed.items())),
            added=tuple(sorted(added.items())),
            removed=tuple(sorted(removed)),
        )
        if out.is_empty():
            raise R2EIngestError(f"{who}: expected_change 为空（期望修订必须改动至少一个键）")
        return out

    def is_empty(self) -> bool:
        return not (self.changed or self.added or self.removed)


@dataclass(frozen=True)
class R2EMaterialRevision:
    """一条已批准的材料修订。五类（前四类改评分材料，第五类只改公开面题面）：

    - `expected_text_replace`：`target=expected_output_json`；在来源期望原文上依次做 `edits`（每条恰好一处
      old→new）；只许改状态值，键集合与顺序不变；`expected_change` 必须与实际变化逐键相同。
    - `expected_file_replace`：`target=expected_output_json`；整份期望换成 `revised_file`；允许增删键，
      但 `expected_change` 必须与重算出的差异逐键相同（修订前原文取自来源行，摘要 = `sha256_before`）。
    - `hidden_test_text_replace`：`target` 是相对 `r2e_tests/` 的隐藏测试路径；原文取自来源行
      `execution_result_content` 的 `test_file_codes`（该列不进任何产物面，只在这里重放修订），依次做 `edits`；
      修订后全文另存在 `revised_file`（派生镜像构建时原样放进私有目录）。
    - `hidden_test_file_add`：在 `r2e_tests/` 下新增来源里没有的文件，内容就是 `revised_file`（可为二进制）；
      `sha256_before` 为 None，目标原本不得存在。
    - `statement_text_replace`：`target=problem_statement`；在来源行 `problem_statement` 上依次做 `edits`，结果进公开面；
      `revised_file` 与 `expected_change` 为 None。
    `sha256_*` 是整段内容修订前后的摘要（`sha256:` 前缀）；重放或读取结果对不上即拒。`revised_content`
    由 `load_r2e_material_revisions` 附上（已核对 `sha256_after`）。
    """

    revision_id: str
    instance_id: str
    kind: str
    target: str
    edits: tuple[tuple[str, str], ...]
    sha256_before: str | None
    sha256_after: str
    revised_file: str | None
    expected_change: R2EExpectedChange | None
    decision_ref: str
    revised_content: bytes | None = None


def _safe_hidden_rel(rel: str) -> bool:
    parts = rel.split("/")
    return bool(rel) and not rel.startswith("/") and "\\" not in rel and all(p and p not in (".", "..", "__pycache__") for p in parts)


def _parse_edits(raw: object, *, who: str) -> tuple[tuple[str, str], ...]:
    if not isinstance(raw, list) or not raw:
        raise R2EIngestError(f"{who}: edits 必须是非空列表")
    out = []
    for e in raw:
        if not isinstance(e, dict) or set(e) != {"old", "new"}:
            raise R2EIngestError(f"{who}: edits 的每一项必须恰好含 old / new")
        if not (isinstance(e["old"], str) and e["old"] and isinstance(e["new"], str)) or e["old"] == e["new"]:
            raise R2EIngestError(f"{who}: edits 的 old 必须是非空字符串、new 是字符串且两者不同")
        out.append((e["old"], e["new"]))
    return tuple(out)


def parse_r2e_material_revisions(doc: dict) -> dict[str, tuple[R2EMaterialRevision, ...]]:
    """修订单 → {instance_id: (修订, …)}（按编号排序）。结构非法、编号重复、同一题同一目标改两次都拒。"""

    if doc.get("schema_id") != R2E_MATERIAL_REVISIONS_SCHEMA_ID:
        raise R2EIngestError(f"材料修订单 schema_id 非法: {doc.get('schema_id')!r}")
    entries = doc.get("revisions")
    if not isinstance(entries, list):
        raise R2EIngestError("材料修订单 revisions 必须是列表")
    out: dict[str, list[R2EMaterialRevision]] = {}
    seen_ids: set[str] = set()
    seen_targets: set[tuple[str, str]] = set()
    for ent in entries:
        if not isinstance(ent, dict) or set(ent) != _REVISION_FIELDS:
            raise R2EIngestError(f"材料修订条目字段集合不符: {sorted(ent) if isinstance(ent, dict) else ent!r}")
        rid = ent["revision_id"]
        if not isinstance(rid, str) or not _REVISION_ID_RE.match(rid) or rid in seen_ids:
            raise R2EIngestError(f"材料修订编号非法或重复: {rid!r}")
        seen_ids.add(rid)
        kind = ent["kind"]
        if kind not in _REVISION_KINDS:
            raise R2EIngestError(f"{rid}: 未知修订类型 {kind!r}")
        for key in ("instance_id", "target", "decision_ref", "reason"):
            if not isinstance(ent[key], str) or not ent[key]:
                raise R2EIngestError(f"{rid}: {key} 必须是非空字符串")
        if not isinstance(ent["evidence"], list) or not ent["evidence"]:
            raise R2EIngestError(f"{rid}: evidence 必须是非空列表")
        if not isinstance(ent["sha256_after"], str) or not _SHA256_RE.match(ent["sha256_after"]):
            raise R2EIngestError(f"{rid}: sha256_after 不是 sha256: 前缀摘要")
        before = ent["sha256_before"]
        if kind == REVISION_KIND_HIDDEN_ADD:
            if before is not None:
                raise R2EIngestError(f"{rid}: 新增文件的 sha256_before 必须为 null（目标原本不存在）")
        elif not isinstance(before, str) or not _SHA256_RE.match(before):
            raise R2EIngestError(f"{rid}: sha256_before 不是 sha256: 前缀摘要")
        edits: tuple[tuple[str, str], ...] = ()
        if kind in (REVISION_KIND_EXPECTED, REVISION_KIND_HIDDEN_TEST, REVISION_KIND_STATEMENT):
            edits = _parse_edits(ent["edits"], who=rid)
        elif ent["edits"] is not None:
            raise R2EIngestError(f"{rid}: {kind} 不用 edits（必须为 null）")
        revised = ent["revised_file"]
        if kind in (REVISION_KIND_EXPECTED, REVISION_KIND_STATEMENT):
            if revised is not None:
                raise R2EIngestError(f"{rid}: {kind} 的 revised_file 必须为 null")
        elif not isinstance(revised, str) or not revised.startswith(f"{_DOCS}/s2_r2e/revisions/") or ".." in revised.split("/"):
            raise R2EIngestError(f"{rid}: revised_file 必须位于 s2_r2e/revisions/ 下")
        change: R2EExpectedChange | None = None
        if kind in EXPECTED_REVISION_KINDS:
            if ent["target"] != "expected_output_json":
                raise R2EIngestError(f"{rid}: 期望修订的 target 必须是 expected_output_json")
            change = R2EExpectedChange.from_doc(ent["expected_change"], who=rid)
            if kind == REVISION_KIND_EXPECTED and (change.added or change.removed):
                raise R2EIngestError(f"{rid}: expected_text_replace 只许改状态值；增删键用 expected_file_replace")
        elif kind == REVISION_KIND_STATEMENT:
            if ent["target"] != STATEMENT_REVISION_TARGET:
                raise R2EIngestError(f"{rid}: 题面修订的 target 必须是 {STATEMENT_REVISION_TARGET}")
            if ent["expected_change"] is not None:
                raise R2EIngestError(f"{rid}: 题面修订的 expected_change 必须为 null")
        else:
            if not _safe_hidden_rel(ent["target"]):
                raise R2EIngestError(f"{rid}: 隐藏测试路径不安全: {ent['target']!r}")
            if ent["expected_change"] is not None:
                raise R2EIngestError(f"{rid}: 隐藏测试修订的 expected_change 必须为 null")
        key = (ent["instance_id"], ent["target"])
        if key in seen_targets:
            raise R2EIngestError(f"{rid}: 同一题的同一目标只允许一条修订（{key}）")
        seen_targets.add(key)
        out.setdefault(ent["instance_id"], []).append(R2EMaterialRevision(
            revision_id=rid, instance_id=ent["instance_id"], kind=kind, target=ent["target"], edits=edits,
            sha256_before=before, sha256_after=ent["sha256_after"], revised_file=revised,
            expected_change=change, decision_ref=ent["decision_ref"],
        ))
    return {iid: tuple(sorted(revs, key=lambda r: r.revision_id)) for iid, revs in sorted(out.items())}


def load_r2e_material_revisions(repo_root: Path, pins: "R2EInputPins") -> dict[str, tuple[R2EMaterialRevision, ...]]:
    """修订单（已由 pins 验证的文件）→ 严格解析；带 `revised_file` 的修订读取内容、核 `sha256_after` 后附上。"""

    del pins  # 文件内容已由 pins 验证；形参保留以强制调用顺序
    doc = json.loads((repo_root / R2E_MATERIAL_REVISIONS_RELPATH).read_text(encoding="utf-8"))
    revisions = parse_r2e_material_revisions(doc)
    loaded: dict[str, tuple[R2EMaterialRevision, ...]] = {}
    for iid, revs in revisions.items():
        items = []
        for rev in revs:
            if rev.revised_file is not None:
                path = repo_root / rev.revised_file
                if not path.is_file():
                    raise R2EIngestError(f"{rev.revision_id}: 修订后文件缺失 {rev.revised_file}")
                content = path.read_bytes()
                if "sha256:" + hashlib.sha256(content).hexdigest() != rev.sha256_after:
                    raise R2EIngestError(f"{rev.revision_id}: 修订后文件内容与 sha256_after 不符")
                rev = replace(rev, revised_content=content)
            items.append(rev)
        loaded[iid] = tuple(items)
    return loaded


def _replace_once(text: str, old: str, new: str, *, who: str) -> str:
    n = text.count(old)
    if n != 1:
        raise R2EIngestError(f"{who}: 修订原文片段出现 {n} 次（必须恰好 1 次）")
    return text.replace(old, new, 1)


def _apply_edits(text: str, edits: tuple[tuple[str, str], ...], *, who: str) -> str:
    for i, (old, new) in enumerate(edits, 1):
        text = _replace_once(text, old, new, who=f"{who} 第 {i} 处")
    return text


def _parse_expected_map(text: str, *, who: str) -> dict[str, str]:
    try:
        mapping = json.loads(text)
    except ValueError as exc:
        raise R2EIngestError(f"{who}: 期望原文不是合法 JSON: {exc}") from exc
    if not isinstance(mapping, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()):
        raise R2EIngestError(f"{who}: 期望原文必须是 键→状态 的字符串对象")
    return mapping


def expected_key_delta(revisions: tuple[R2EMaterialRevision, ...]) -> int:
    """已批准期望修订造成的键数变化（新增 − 删除）；镜像事实表记的是来源键数。"""

    return sum(len(r.expected_change.added) - len(r.expected_change.removed)
               for r in revisions if r.kind in EXPECTED_REVISION_KINDS and r.expected_change is not None)


def apply_expected_revisions(iid: str, expected_text: str, revisions: tuple[R2EMaterialRevision, ...]) -> str:
    """把期望修订作用在来源原文上：文本类按 edits 重放、文件类读取修订后全文；前后摘要都要对上，
    重算出的逐键变化必须与修订单声明的 `expected_change` 完全相同；状态词只许 PASSED / FAILED / ERROR。"""

    for rev in revisions:
        if rev.kind not in EXPECTED_REVISION_KINDS:
            continue
        who = f"{iid}/{rev.revision_id}"
        if _sha256_text(expected_text) != rev.sha256_before:
            raise R2EIngestError(f"{who}: 期望原文摘要与修订单的 sha256_before 不符")
        if rev.kind == REVISION_KIND_EXPECTED:
            revised = _apply_edits(expected_text, rev.edits, who=who)
        else:
            if rev.revised_content is None:
                raise R2EIngestError(f"{who}: 整份期望替换缺修订后内容（须经 load_r2e_material_revisions 载入）")
            revised = rev.revised_content.decode("utf-8")
        if _sha256_text(revised) != rev.sha256_after:
            raise R2EIngestError(f"{who}: 修订后的期望原文摘要与 sha256_after 不符")
        before = _parse_expected_map(expected_text, who=who)
        after = _parse_expected_map(revised, who=who)
        bad = sorted(set(after.values()) - R2E_EXPECTED_STATUSES)
        if bad:
            raise R2EIngestError(f"{who}: 修订后的期望里有非法状态词 {bad}")
        change = R2EExpectedChange.diff(before, after)
        if change.is_empty():
            raise R2EIngestError(f"{who}: 期望修订没有改变任何键")
        if change != rev.expected_change:
            raise R2EIngestError(f"{who}: 实际的逐键变化与修订单声明的 expected_change 不符")
        if rev.kind == REVISION_KIND_EXPECTED and list(before) != list(after):
            raise R2EIngestError(f"{who}: 文本替换类期望修订改变了键集合或顺序（只许改状态值）")
        expected_text = revised
    return expected_text


def apply_hidden_test_revisions(iid: str, hidden_files: tuple[tuple[str, str], ...], original_codes: dict[str, str],
                                revisions: tuple[R2EMaterialRevision, ...]) -> tuple[tuple[str, str], ...]:
    """把隐藏测试修订作用到清单上，返回修订后的 (路径, 摘要)：文本类从来源行 test_file_codes 的原文重放 edits；
    新增类要求目标原本不存在、内容已载入且摘要对上。"""

    files = dict(hidden_files)
    for rev in revisions:
        if rev.kind not in HIDDEN_REVISION_KINDS:
            continue
        who = f"{iid}/{rev.revision_id}"
        if rev.kind == REVISION_KIND_HIDDEN_ADD:
            if rev.target in files:
                raise R2EIngestError(f"{who}: 新增的隐藏测试文件 {rev.target} 在来源清单里已存在")
            if rev.revised_content is None or "sha256:" + hashlib.sha256(rev.revised_content).hexdigest() != rev.sha256_after:
                raise R2EIngestError(f"{who}: 新增文件内容缺失或与 sha256_after 不符（须经 load_r2e_material_revisions 载入）")
            files[rev.target] = rev.sha256_after
            continue
        if rev.target not in files:
            raise R2EIngestError(f"{who}: 隐藏测试清单里没有 {rev.target}")
        if files[rev.target] != rev.sha256_before:
            raise R2EIngestError(f"{who}: 镜像事实里 {rev.target} 的摘要与修订单的 sha256_before 不符")
        original = original_codes.get(rev.target)
        if original is None:
            raise R2EIngestError(f"{who}: 来源行没有 {rev.target} 的原文，无法重放修订")
        if _sha256_text(original) != rev.sha256_before:
            raise R2EIngestError(f"{who}: 来源行里 {rev.target} 的原文摘要与镜像事实不符")
        revised = _apply_edits(original, rev.edits, who=who)
        if _sha256_text(revised) != rev.sha256_after:
            raise R2EIngestError(f"{who}: 重放后的 {rev.target} 摘要与 sha256_after 不符")
        files[rev.target] = rev.sha256_after
    return tuple(sorted(files.items()))


def apply_statement_revisions(iid: str, statement: str, revisions: tuple[R2EMaterialRevision, ...]) -> str:
    """把题面修订作用在来源题面原文上，返回修订后的题面（R-f：统一标准 v1 §5、§9 D6）。

    从来源行 `problem_statement` 出发依次做 `edits`（每条在当前文本里恰好出现一次）；`sha256_before` 必须等于题面原文
    的摘要、`sha256_after` 必须等于做完全部 edits 后的摘要，对不上即拒；修订后的题面不许为空、不许与原文相同。
    只作用于公开面：期望映射、隐藏测试等评分材料不经过这里。解析层已保证每题至多一条题面修订（同一题同一目标只许一条）。"""

    for rev in revisions:
        if rev.kind != REVISION_KIND_STATEMENT:
            continue
        who = f"{iid}/{rev.revision_id}"
        if rev.target != STATEMENT_REVISION_TARGET:
            raise R2EIngestError(f"{who}: 题面修订的 target 必须是 {STATEMENT_REVISION_TARGET}")
        if _sha256_text(statement) != rev.sha256_before:
            raise R2EIngestError(f"{who}: 题面原文摘要与修订单的 sha256_before 不符")
        revised = _apply_edits(statement, rev.edits, who=who)
        if _sha256_text(revised) != rev.sha256_after:
            raise R2EIngestError(f"{who}: 修订后的题面摘要与 sha256_after 不符")
        if not revised.strip():
            raise R2EIngestError(f"{who}: 修订后的题面为空")
        if revised == statement:
            raise R2EIngestError(f"{who}: 题面修订没有改变题面")
        statement = revised
    return statement


def effective_hidden_files(fact: "R2EImageFact", revisions: tuple[R2EMaterialRevision, ...]) -> tuple[tuple[str, str], ...]:
    """消费期用：镜像事实的隐藏测试清单，套上已批准修订的 sha256_after（不需要原文）。"""

    files = dict(fact.hidden_files)
    for rev in revisions:
        if rev.kind == REVISION_KIND_HIDDEN_TEST:
            if files.get(rev.target) != rev.sha256_before:
                raise R2EIngestError(f"{rev.revision_id}: 镜像事实里 {rev.target} 的摘要与 sha256_before 不符")
            files[rev.target] = rev.sha256_after
        elif rev.kind == REVISION_KIND_HIDDEN_ADD:
            if rev.target in files:
                raise R2EIngestError(f"{rev.revision_id}: 新增的隐藏测试文件 {rev.target} 在镜像事实里已存在")
            files[rev.target] = rev.sha256_after
    return tuple(sorted(files.items()))


def _source_test_codes(row: dict) -> dict[str, str]:
    """来源行 `execution_result_content` 里的隐藏测试原文（只供修订重放；该列不进任何产物面）。"""

    try:
        doc = json.loads(row.get("execution_result_content") or "{}")
    except (TypeError, ValueError):
        return {}
    names, codes = doc.get("test_file_names") or [], doc.get("test_file_codes") or []
    if len(names) != len(codes):
        return {}
    return {n: c for n, c in zip(names, codes) if isinstance(n, str) and isinstance(c, str)}


def _assert_public_face_is_clean(public: PublicTaskBundle, row: dict, golden_patch: str) -> None:
    """公开面 fail-closed 断言（在通用泄漏标记扫描之外的 R2E 专项）：

    1. 键面：公开 bundle 的键里不出现任何非公开归属的来源字段名；
    2. 值面：期望映射原文、gold 补丁、造题指令不得原样出现在任何公开字符串里。
    """

    dumped = public.model_dump(mode="json")
    forbidden_keys = {k for k, cls in R2E_SUBSET_FIELD_CLASSES.items() if not cls.startswith("public")}
    leaked = forbidden_keys & set(dumped)
    if leaked:
        raise R2EIngestError(f"{public.instance_id}: 公开面出现非公开来源字段: {sorted(leaked)}")
    haystack = "\n".join(v for v in dumped.values() if isinstance(v, str))
    for name, needle in (
        ("expected_output_json", row["expected_output_json"]),
        ("gold", golden_patch),
        ("prompt", row["prompt"]),
    ):
        if needle and needle in haystack:
            raise R2EIngestError(f"{public.instance_id}: 公开面原样包含 {name} 内容")


def build_r2e_task(row: dict, fact: R2EImageFact, *, raw_archive_sha256: str,
                   image_facts_sha256: str, source_revision: str,
                   revisions: tuple[R2EMaterialRevision, ...] = ()):
    """单题：来源行 + 镜像事实（+ 该题已批准的材料修订）→ (public, grading, validation, package)。"""

    check_r2e_row_fields(row)
    repo, commit = row["repo_name"], row["commit_hash"]
    if not _HEX40.match(commit):
        raise R2EIngestError(f"{repo}: commit_hash 不是 40 位 hex: {commit!r}")
    iid = r2e_instance_id_for(repo, commit)
    if fact.commit_hash != commit or fact.repo != repo:
        raise R2EIngestError(f"{iid}: 镜像事实与来源行身份不符（{fact.repo}@{fact.commit_hash[:12]}）")
    if fact.source_image_ref != row["docker_image"]:
        raise R2EIngestError(f"{iid}: 镜像引用不符: 行 {row['docker_image']!r} / 事实 {fact.source_image_ref!r}")

    commit_doc = json.loads(row["parsed_commit_content"])
    if commit_doc.get("new_commit_hash") != commit or commit_doc.get("old_commit_hash") != commit + "^":
        raise R2EIngestError(
            f"{iid}: parsed_commit_content 的提交身份与行不符"
            f"（new={commit_doc.get('new_commit_hash')!r}, old={commit_doc.get('old_commit_hash')!r}）"
        )

    if any(rev.instance_id != iid for rev in revisions):
        raise R2EIngestError(f"{iid}: 传入了别的题的材料修订")
    # 题面修订（R-f）在构建公开面之前作用：公开面的 problem_statement / problem_statement_sha256 都是修订后的。修订编号
    # 与其余修订走同一条记录路径（评分面 `material_revisions`、提交记录 `material_revisions`、pins 里的修订单摘要）。
    statement = apply_statement_revisions(iid, row["problem_statement"], revisions)
    public = PublicTaskBundle(
        instance_id=iid,
        repo=repo,
        base_commit=fact.head_commit,
        image=fact.source_image_ref,
        image_manifest_digest=fact.manifest_digest,
        workdir=fact.workdir,
        problem_statement=statement,
        problem_statement_sha256=_sha256_text(statement),
        public_hints=R2E_PUBLIC_HINTS,
    )
    scan_public_bundle(public)

    expected_text = apply_expected_revisions(iid, row["expected_output_json"], revisions)
    hidden_files = apply_hidden_test_revisions(iid, fact.hidden_files, _source_test_codes(row), revisions)
    grading = PrivateGradingBundleR2E(
        instance_id=iid,
        repo=repo,
        repo_key_lower=repo.lower(),
        base_commit=fact.head_commit,
        source_commit_hash=commit,
        expected_output_json=expected_text,
        expected_output_json_sha256=_sha256_text(expected_text),
        run_tests_sh=fact.run_tests_sh,
        run_tests_sh_sha256=fact.run_tests_sh_sha256,
        hidden_test_files=[R2EHiddenTestFile(path=p, sha256=d) for p, d in hidden_files],
        hidden_tests_tree_sha256=r2e_hidden_tests_tree_digest(hidden_files),
        rule_source_id=R2E_RULE_SOURCE_ID,
        source_revision=source_revision,
        material_revisions=sorted(rev.revision_id for rev in revisions),
    )
    expected_map = grading.expected_map()
    want_n = fact.expected_n + expected_key_delta(revisions)
    if len(expected_map) != want_n:
        raise R2EIngestError(f"{iid}: 期望键数 {len(expected_map)} 与镜像事实表记录的 {fact.expected_n}"
                             f"（套上已批准修订的增删后应为 {want_n}）不符")
    if len(normalize_status_map(expected_map)) != len(expected_map):
        # 两个期望键归一化后相同：上游会静默让后者覆盖前者，判定口径就不再是"逐键"了——不带病入库
        raise R2EIngestError(f"{iid}: 期望键归一化后发生碰撞")

    golden = extract_gold_patch(row["parsed_commit_content"])
    if not golden:
        raise R2EIngestError(f"{iid}: 上游规则重建不出 gold（没有非测试 .py 改动）")
    validation = ValidationOnlyBundle(
        instance_id=iid, golden_patch=golden, golden_patch_sha256=_sha256_text(golden),
    )
    _assert_public_face_is_clean(public, row, golden)

    package = build_environment_package(
        public=public, grading=grading, validation=validation,
        source=TASK_SOURCE_R2E_GYM_SUBSET,
        raw_archive_sha256=raw_archive_sha256,
        image_manifest_keyed_sha256=image_facts_sha256,
    )
    return public, grading, validation, package


@dataclass
class R2EIngestResult:
    """与 `ingest_swegym_lite.IngestResult` 同形的四面结果（controller 按属性名鸭子消费）。"""

    packages: list[EnvironmentPackageV1] = field(default_factory=list)
    public_bundles: list[PublicTaskBundle] = field(default_factory=list)
    grading_bundles: list[PrivateGradingBundleR2E] = field(default_factory=list)
    validation_bundles: list[ValidationOnlyBundle] = field(default_factory=list)


def ingest_r2e_subset(*, rows: list[dict], image_facts: dict[str, R2EImageFact],
                      raw_archive_sha256: str, image_facts_sha256: str,
                      source_revision: str,
                      expected_task_count: int | None = EXPECTED_TASK_COUNT,
                      revisions: dict[str, tuple[R2EMaterialRevision, ...]] | None = None) -> R2EIngestResult:
    """48 题主入口。来源行集合与镜像事实集合必须**完全相等**（不许一边多一边少）。
    `revisions` = 已批准的材料修订（`load_r2e_material_revisions`）；指向不存在任务的修订即拒。"""

    if source_revision != R2E_DATASET_REVISION:
        raise R2EIngestError(f"source_revision={source_revision!r} 与固定 revision 不符")
    by_commit: dict[str, dict] = {}
    for r in rows:
        check_r2e_row_fields(r)
        if r["commit_hash"] in by_commit:
            raise R2EIngestError(f"来源行重复 commit_hash: {r['commit_hash']}（fail-closed，不静默覆盖）")
        by_commit[r["commit_hash"]] = r
    if expected_task_count is not None and len(by_commit) != expected_task_count:
        raise R2EIngestError(f"来源行数量异常: {len(by_commit)}（期望 {expected_task_count}）")
    if set(by_commit) != set(image_facts):
        only_rows = sorted(set(by_commit) - set(image_facts))[:3]
        only_facts = sorted(set(image_facts) - set(by_commit))[:3]
        raise R2EIngestError(f"来源行与镜像事实的任务集合不相等（行独有 {only_rows}，事实独有 {only_facts}）")

    revisions = revisions or {}
    known_ids = {r2e_instance_id_for(row["repo_name"], commit) for commit, row in by_commit.items()}
    orphans = sorted(set(revisions) - known_ids)
    if orphans:
        raise R2EIngestError(f"材料修订指向不存在的任务: {orphans[:3]}")
    result = R2EIngestResult()
    built = []
    for commit, row in by_commit.items():
        built.append(build_r2e_task(
            row, image_facts[commit],
            raw_archive_sha256=raw_archive_sha256, image_facts_sha256=image_facts_sha256,
            source_revision=source_revision,
            revisions=revisions.get(r2e_instance_id_for(row["repo_name"], commit), ()),
        ))
    for public, grading, validation, package in sorted(built, key=lambda item: item[0].instance_id):
        result.public_bundles.append(public)
        result.grading_bundles.append(grading)
        result.validation_bundles.append(validation)
        result.packages.append(package)
    return result


# ---------------------------------------------------------------------------
# 关系检查
# ---------------------------------------------------------------------------


def _r2e_relation_errors(package: EnvironmentPackageV1, public: PublicTaskBundle,
                         grading: PrivateGradingBundleR2E, validation: ValidationOnlyBundle) -> list[str]:
    errs: list[str] = []
    if package.source != TASK_SOURCE_R2E_GYM_SUBSET:
        errs.append(f"包记录 source={package.source!r} 不是 r2e_gym_subset")
    if not isinstance(grading, PrivateGradingBundleR2E):
        errs.append(f"评分面类型 {type(grading).__name__} 不是 PrivateGradingBundleR2E")
        return errs
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
    if not public.image.endswith(":" + grading.source_commit_hash):
        errs.append("镜像 tag 与 source_commit_hash 不符")
    return errs


def verify_r2e_bundle_relations_non_authoritative(package, public, grading, validation) -> None:
    """**非权威**关系检查（合成夹具单测用）：不核 pins、不核镜像事实表。正式消费方用
    `verify_r2e_package_relations`。"""

    errs = _r2e_relation_errors(package, public, grading, validation)
    if errs:
        raise R2EIngestError(f"{package.instance_id}: 关系验证失败: {'; '.join(errs)}")


def verify_r2e_package_relations(package, public, grading, validation, *,
                                 pins: "R2EInputPins", image_facts: dict[str, R2EImageFact],
                                 revisions: dict[str, tuple[R2EMaterialRevision, ...]] | None = None) -> None:
    """strict 消费期重验：四方 digest / 身份关系、镜像身份与入口 / 隐藏测试摘要对事实表（套上已批准修订）、
    评分面的修订标记与修订单一致（期望修订 → 评分面期望摘要、题面修订 → 公开面题面摘要都等于 `sha256_after`）、
    provenance 三 digest 对封板 pins 与规则源注册表、public 面消费期泄漏扫描。
    pins 与事实表都是必传；`revisions` 不传 = 没有修订（修订过的评分面在这种调用下必然被拒）。"""

    errs = _r2e_relation_errors(package, public, grading, validation)
    if not errs:
        fact = image_facts.get(grading.source_commit_hash)
        if fact is None:
            errs.append("镜像事实表无该任务")
        else:
            if (fact.source_image_ref, fact.manifest_digest) != (package.image, package.image_manifest_digest):
                errs.append("镜像身份与事实表不符")
            if fact.head_commit != package.base_commit:
                errs.append("base_commit 与事实表的镜像 HEAD 不符")
            if fact.run_tests_sh_sha256 != grading.run_tests_sh_sha256:
                errs.append("run_tests.sh 摘要与事实表不符")
            revs = (revisions or {}).get(grading.instance_id, ())
            if grading.material_revisions != sorted(rev.revision_id for rev in revs):
                errs.append(f"评分面的修订标记 {grading.material_revisions} 与修订单不符")
            try:
                hidden = effective_hidden_files(fact, revs)
            except R2EIngestError as exc:
                errs.append(str(exc))
            else:
                if r2e_hidden_tests_tree_digest(hidden) != grading.hidden_tests_tree_sha256:
                    errs.append("隐藏测试树摘要与事实表（套上已批准修订）不符")
                if sorted((f.path, f.sha256) for f in grading.hidden_test_files) != sorted(hidden):
                    errs.append("隐藏测试清单与事实表（套上已批准修订）不符")
            for rev in revs:
                if rev.kind in EXPECTED_REVISION_KINDS and grading.expected_output_json_sha256 != rev.sha256_after:
                    errs.append(f"{rev.revision_id}: 期望原文摘要不是修订后的摘要")
                if rev.kind == REVISION_KIND_STATEMENT and public.problem_statement_sha256 != rev.sha256_after:
                    errs.append(f"{rev.revision_id}: 公开面的题面摘要不是修订后的摘要")
        if package.raw_archive_sha256 != "sha256:" + pins.raw_archive:
            errs.append("raw_archive_sha256 与封板 pin 不符")
        if package.image_manifest_keyed_sha256 != "sha256:" + pins.image_facts:
            errs.append("image_manifest_keyed_sha256 与封板 pin（镜像事实表）不符")
        if package.spec_vendor_json_sha256 != "sha256:" + r2e_rule_source_pin(grading.rule_source_id).sha256:
            errs.append("spec_vendor_json_sha256 与规则源注册表不符")
    if errs:
        raise R2EIngestError(f"{package.instance_id}: 消费期关系验证失败: {'; '.join(errs)}")
    scan_public_bundle(public)


# ---------------------------------------------------------------------------
# 封板输入 pins（代码常量 → pins 记录 → 四项输入文件）
# ---------------------------------------------------------------------------

# v1（t1_input_pins_r2e_v1.json，四项输入）与 v2（加第五项"材料修订单" v1，2026-09-24，用户批准 T0-1 / T0-2）
# 都保留为历史记录；v3（2026-09-24 晚）只把第五项换成修订单 v2（新增 T0-5 / T0-6 的修订与两类修订类型），键集合不变；
# v4（2026-09-24 夜）只把第五项换成修订单 v3（T0-6 第二步、T0-7 的 13 条修订），键集合不变，v3 保留为历史。
# v5（2026-09-29，单题闭环试行）只把第五项换成修订单 v4（统一标准 v1 §9 D4 模板授权、Codex 复核通过的修订），键集合不变。
# v6（2026-09-29，单题闭环试行）只把第五项换成修订单 v5（统一标准 v1 §9 D4 模板授权、Codex 复核通过的修订），键集合不变。
# v7（2026-09-29，单题闭环试行）只把第五项换成修订单 v6（统一标准 v1 §9 D4 模板授权、Codex 复核通过的修订），键集合不变。
# v8（2026-09-29，单题闭环试行）只把第五项换成修订单 v7（统一标准 v1 §9 D4 模板授权、Codex 复核通过的修订），键集合不变。
# v9（2026-09-29，单题闭环试行）只把第五项换成修订单 v8（统一标准 v1 §9 D4 模板授权、Codex 复核通过的修订），键集合不变。
# v10（2026-09-29，单题闭环试行）只把第五项换成修订单 v9（统一标准 v1 §9 D4 模板授权、Codex 复核通过的修订），键集合不变。
# v11（2026-09-29，单题闭环试行）只把第五项换成修订单 v10（统一标准 v1 §9 D4 模板授权、Codex 复核通过的修订），键集合不变。
# v12（2026-09-29，单题闭环试行）只把第五项换成修订单 v11（统一标准 v1 §9 D4 模板授权、Codex 复核通过的修订），键集合不变。
R2E_PINS_RELPATH = f"{_DOCS}/s2_r2e/t1_input_pins_r2e_v12.json"
R2E_PINS_SCHEMA_ID = "rh2.s2_r2e.t1_input_pins.v12"
# pins 记录自身的 sha256（封板后不许变；变更 = 显式新版本 + 评审，不是改常量）。
R2E_PINS_SHA256 = "64d45468b421cd93b97bbe7618b9c9f54ec01fdf3b3cd76fce856a8b332a9fb0"

R2E_EXPECTED_PIN_KEYS = frozenset({
    "raw_archive",        # s2_r2e/raw/r2e_gym_subset_48_e8b9fcbc.jsonl（48 行来源原始行）
    "source_revision",    # s2_r2e/raw/r2e_subset.revision（数据集 revision 记录）
    "image_facts",        # s2_r2e/raw/r2e_image_facts_m3_48.json（M3 镜像实测事实表的逐字节副本）
    "rule_source",        # s2_r2e/vendor/prime_envs_r2e_gym_taskset_c4d04dfe.py（固定版本的上游规则源）
    "material_revisions",  # s2_r2e/revisions/material_revisions_v11.json（用户逐项批准的材料修订单）
})


@dataclass(frozen=True)
class R2EInputPins:
    """已验证的 pins 视图：字段值即四项输入的 sha256（裸 hex）。"""

    raw_archive: str
    source_revision: str
    image_facts: str
    rule_source: str
    material_revisions: str


def load_and_verify_r2e_pins(repo_root: Path, *, pins_sha256: str | None = None) -> R2EInputPins:
    """三级验证：pins 文件自身 digest → 记录结构 → 五项输入文件逐一比对。

    `pins_sha256` 只给封板流程与测试用（验证一份尚未写进代码常量的 pins 记录）；正式消费不传。"""

    want_self = R2E_PINS_SHA256 if pins_sha256 is None else pins_sha256
    pins_path = repo_root / R2E_PINS_RELPATH
    if not pins_path.exists():
        raise R2EIngestError(f"R2E pins 记录缺失: {R2E_PINS_RELPATH}")
    data = pins_path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != want_self:
        raise R2EIngestError(
            f"R2E pins 记录 digest 不符（actual {actual[:16]}… != pin {want_self[:16]}…）——封板记录被修改，拒绝消费"
        )
    doc = json.loads(data)
    if doc.get("schema_id") != R2E_PINS_SCHEMA_ID:
        raise R2EIngestError(f"pins schema_id 非法: {doc.get('schema_id')!r}")
    entries = doc.get("pins", {})
    if set(entries) != R2E_EXPECTED_PIN_KEYS:
        raise R2EIngestError(
            f"pins 键集合不符：多={sorted(set(entries) - R2E_EXPECTED_PIN_KEYS)} "
            f"少={sorted(R2E_EXPECTED_PIN_KEYS - set(entries))}"
        )
    resolved: dict[str, str] = {}
    for key, ent in entries.items():
        path = repo_root / ent["path"]
        if not path.exists():
            raise R2EIngestError(f"{key}: 输入文件缺失 {ent['path']}")
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        if got != ent["sha256"]:
            raise R2EIngestError(
                f"{key}: 输入漂移！文件 {got[:16]}… != 封板 pin {ent['sha256'][:16]}…——先人工裁决漂移原因"
            )
        resolved[key] = ent["sha256"]
    if resolved["rule_source"] != r2e_rule_source_pin(R2E_RULE_SOURCE_ID).sha256:
        raise R2EIngestError("pins 的 rule_source 与代码里的规则源注册表不符")
    return R2EInputPins(**resolved)


def load_r2e_image_facts(repo_root: Path, pins: R2EInputPins) -> dict[str, R2EImageFact]:
    """镜像事实表（已由 pins 验证的文件）→ 严格解析。调用方必须先过 `load_and_verify_r2e_pins`。"""

    del pins  # 文件内容已由 pins 验证；形参保留以强制调用顺序
    return parse_r2e_image_facts(json.loads((repo_root / R2E_IMAGE_FACTS_RELPATH).read_text(encoding="utf-8")))


def load_r2e_rows(repo_root: Path, pins: R2EInputPins) -> tuple[list[dict], str]:
    """（来源原始行, revision）。只有 ingestion 运行器需要——原始行文件约 25 MB，加载入口不读它的内容。"""

    del pins
    raw = (repo_root / R2E_RAW_ARCHIVE_RELPATH).read_text(encoding="utf-8")
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    revision = (repo_root / R2E_SOURCE_REVISION_RELPATH).read_text(encoding="utf-8").strip()
    return rows, revision


# ---------------------------------------------------------------------------
# 落盘与严格加载（代码常量 → 提交记录 → 四个数据文件）
# ---------------------------------------------------------------------------

R2E_INGEST_MANIFEST_NAME = "ingest_manifest_v0.json"
# v2（2026-09-24）：提交记录多一项 `material_revisions`（本次产物实际应用的修订清单，与封板修订单逐条对应）。
# v3（2026-09-24 晚）：记录格式不变，但修订单升到 v2（四类修订；新增文件的 sha256_before 为 null）。
# 修订单 v3（2026-09-24 夜）格式同 v2，提交记录 schema 不变，只是 material_revisions 多了 13 条。
# 数据文件名里的 `v0` 是产物格式版本，内容版本看提交记录的 material_revisions 与 t1_input_pins。
R2E_INGEST_MANIFEST_SCHEMA_ID = "rh2.s2_r2e.ingest_manifest.v3"
_R2E_DATA_FILES = (
    "environment_packages_v0.jsonl",
    "public_bundles_v0.jsonl",
    "grading_bundles_r2e_v0.jsonl",
    "validation_bundles_v0.jsonl",
)
# 真实 48 题产物提交记录（s2_r2e/ingest/ingest_manifest_v0.json）的 sha256 pin。重新生成产物 = 修改本常量。
R2E_INGEST_MANIFEST_SHA256_PIN = "6209850e5f0115fd330bfd3e3d7ea2dd3dab821991d61f2566a30c7a1d733536"


def _atomic_write(path: Path, payload: bytes) -> None:
    import os

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _revision_records(revisions: dict[str, tuple[R2EMaterialRevision, ...]] | None) -> list[dict]:
    return [
        {"revision_id": r.revision_id, "instance_id": r.instance_id, "kind": r.kind, "target": r.target,
         "sha256_before": r.sha256_before, "sha256_after": r.sha256_after, "decision_ref": r.decision_ref}
        for revs in (revisions or {}).values() for r in revs
    ]


def write_r2e_ingest_outputs(result: R2EIngestResult, out_dir: Path, *, pins: R2EInputPins,
                             revisions: dict[str, tuple[R2EMaterialRevision, ...]] | None = None) -> dict[str, str]:
    """事务化落盘：四数据文件逐个原子写，最后原子写提交记录（四文件 digest + 行数 + 输入 pins）。
    产物不含时间戳——同一输入重跑逐字节相同。返回 {文件名: sha256}（含提交记录自身）。"""

    def _payload(models) -> bytes:
        return "".join(
            json.dumps(m.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n" for m in models
        ).encode("utf-8")

    payloads = {
        "environment_packages_v0.jsonl": _payload(result.packages),
        "public_bundles_v0.jsonl": _payload(result.public_bundles),
        "grading_bundles_r2e_v0.jsonl": _payload(result.grading_bundles),
        "validation_bundles_v0.jsonl": _payload(result.validation_bundles),
    }
    digests: dict[str, str] = {}
    for name in _R2E_DATA_FILES:
        _atomic_write(out_dir / name, payloads[name])
        digests[name] = hashlib.sha256(payloads[name]).hexdigest()
    manifest = {
        "schema_id": R2E_INGEST_MANIFEST_SCHEMA_ID,
        "files": {n: {"sha256": digests[n], "count": len(result.packages)} for n in _R2E_DATA_FILES},
        "package_count": len(result.packages),
        "t1_input_pins": {k: getattr(pins, k) for k in sorted(vars(pins))},
        "material_revisions": sorted(_revision_records(revisions), key=lambda r: r["revision_id"]),
    }
    mp = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")
    _atomic_write(out_dir / R2E_INGEST_MANIFEST_NAME, mp)
    digests[R2E_INGEST_MANIFEST_NAME] = hashlib.sha256(mp).hexdigest()
    return digests


def load_r2e_ingest_outputs(out_dir: Path, *, pins: R2EInputPins, image_facts: dict[str, R2EImageFact],
                            expected_instance_ids: set[str],
                            revisions: dict[str, tuple[R2EMaterialRevision, ...]] | None = None) -> R2EIngestResult:
    """strict loader：提交记录严格字段 → 四文件 digest → 模型解析 → 重复 id 拒绝 →
    四方 id 集合 == 可信全集（裁剪成子集必被拒）→ 逐包 strict 验证。

    不验证提交记录的外部锚（代码 pin）——正式消费用 `load_trusted_r2e_ingest_outputs`。"""

    mp = out_dir / R2E_INGEST_MANIFEST_NAME
    if not mp.exists():
        raise R2EIngestError(f"提交记录缺失: {R2E_INGEST_MANIFEST_NAME}")
    manifest = json.loads(mp.read_text(encoding="utf-8"))
    if set(manifest) != {"schema_id", "files", "package_count", "t1_input_pins", "material_revisions"}:
        raise R2EIngestError(f"提交记录顶层键集合不符: {sorted(manifest)}")
    if manifest["material_revisions"] != sorted(_revision_records(revisions), key=lambda r: r["revision_id"]):
        raise R2EIngestError("提交记录的 material_revisions 与封板修订单不符（产物不是按这份修订单生成的）")
    if manifest["schema_id"] != R2E_INGEST_MANIFEST_SCHEMA_ID:
        raise R2EIngestError(f"提交记录 schema_id 非法: {manifest['schema_id']!r}")
    if type(manifest["package_count"]) is not int or manifest["package_count"] < 0:
        raise R2EIngestError("package_count 不是非负 int")
    recorded = manifest["t1_input_pins"] or {}
    if set(recorded) != set(vars(pins)):
        raise R2EIngestError("提交记录 t1_input_pins 键集合不符")
    for k in sorted(vars(pins)):
        if recorded.get(k) != getattr(pins, k):
            raise R2EIngestError(f"提交记录的 t1_input_pins.{k} 与封板 pins 不符")
    files = manifest["files"]
    if set(files) != set(_R2E_DATA_FILES):
        raise R2EIngestError("提交记录 files 键集合不符")
    for name, ent in files.items():
        if set(ent) != {"sha256", "count"} or type(ent["count"]) is not int or ent["count"] < 0:
            raise R2EIngestError(f"{name}: 提交记录条目非法")
        path = out_dir / name
        if not path.exists():
            raise R2EIngestError(f"数据文件缺失: {name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != ent["sha256"]:
            raise R2EIngestError(f"{name}: digest 与提交记录不符（数据文件被改 / 半写）")

    def _load(name: str, cls):
        out, seen = [], set()
        for line in (out_dir / name).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            m = cls.model_validate(json.loads(line))
            if m.instance_id in seen:
                raise R2EIngestError(f"{name}: 重复 instance_id {m.instance_id}")
            seen.add(m.instance_id)
            out.append(m)
        if len(out) != files[name]["count"]:
            raise R2EIngestError(f"{name}: 行数 {len(out)} 与提交记录 {files[name]['count']} 不符")
        return out

    result = R2EIngestResult(
        packages=_load("environment_packages_v0.jsonl", EnvironmentPackageV1),
        public_bundles=_load("public_bundles_v0.jsonl", PublicTaskBundle),
        grading_bundles=_load("grading_bundles_r2e_v0.jsonl", PrivateGradingBundleR2E),
        validation_bundles=_load("validation_bundles_v0.jsonl", ValidationOnlyBundle),
    )
    ids = [
        {m.instance_id for m in result.packages},
        {m.instance_id for m in result.public_bundles},
        {m.instance_id for m in result.grading_bundles},
        {m.instance_id for m in result.validation_bundles},
    ]
    if not (ids[0] == ids[1] == ids[2] == ids[3]):
        raise R2EIngestError("四文件 instance_id 集合不一致")
    if ids[0] != set(expected_instance_ids):
        raise R2EIngestError(
            f"包集合 != 可信任务全集（{len(ids[0])} vs {len(expected_instance_ids)}；"
            f"缺 {sorted(set(expected_instance_ids) - ids[0])[:3]}）"
        )
    if manifest["package_count"] != len(result.packages):
        raise R2EIngestError(f"package_count={manifest['package_count']} 与实际 {len(result.packages)} 不符")
    by_public = {m.instance_id: m for m in result.public_bundles}
    by_grading = {m.instance_id: m for m in result.grading_bundles}
    by_validation = {m.instance_id: m for m in result.validation_bundles}
    for pkg in result.packages:
        verify_r2e_package_relations(
            pkg, by_public[pkg.instance_id], by_grading[pkg.instance_id], by_validation[pkg.instance_id],
            pins=pins, image_facts=image_facts, revisions=revisions,
        )
    return result


@dataclass
class TrustedR2EIngest:
    """`load_trusted_r2e_ingest_outputs` 的返回：结果 + 下游继续验证所需的可信上下文。"""

    result: R2EIngestResult
    pins: R2EInputPins
    image_facts: dict[str, R2EImageFact]
    revisions: dict[str, tuple[R2EMaterialRevision, ...]] = field(default_factory=dict)


def load_trusted_r2e_ingest_outputs(repo_root: Path) -> TrustedR2EIngest:
    """R2E 产物的**唯一正式消费入口**：pins 三级验证 → 镜像事实表严格解析 → 提交记录对代码 pin →
    `load_r2e_ingest_outputs` 严格解析 + 全集绑定 + 逐包验证。"""

    pins = load_and_verify_r2e_pins(repo_root)
    image_facts = load_r2e_image_facts(repo_root, pins)
    revisions = load_r2e_material_revisions(repo_root, pins)
    out_dir = repo_root / R2E_INGEST_OUT_RELPATH
    mp = out_dir / R2E_INGEST_MANIFEST_NAME
    if not mp.exists():
        raise R2EIngestError("提交记录缺失（trusted 入口）")
    actual = hashlib.sha256(mp.read_bytes()).hexdigest()
    if actual != R2E_INGEST_MANIFEST_SHA256_PIN:
        raise R2EIngestError(
            f"提交记录与代码 pin 不符（actual {actual[:16]}… != pin {R2E_INGEST_MANIFEST_SHA256_PIN[:16]}…）"
            "——输出面被改或未经审计重生成，拒绝消费"
        )
    expected_ids = {r2e_instance_id_for(f.repo, f.commit_hash) for f in image_facts.values()}
    result = load_r2e_ingest_outputs(out_dir, pins=pins, image_facts=image_facts,
                                     expected_instance_ids=expected_ids, revisions=revisions)
    return TrustedR2EIngest(result=result, pins=pins, image_facts=image_facts, revisions=revisions)
