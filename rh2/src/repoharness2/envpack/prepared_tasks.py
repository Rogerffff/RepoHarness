"""W1b 第一集成切片（F6）：trusted-prep 产物（prepared artifact）的形态、写入与 actor 侧读取。

所有权架构（06 计划 §3 W2a 行 + Wave1 复核 F6；切片定义由 owner 裁定）::

    host 进程：一次性 trusted-prep（create_rollout_manager 之前运行，结束即退出）
      TrustedTaskController.from_repo_root   ← 完整 loader + 四面关系检查，**只在这里**
        ├─ (a) 公开产物目录 prepared_dir/
        │      prompts.jsonl            miles --prompt-data 直接消费（prompt + label + metadata 五键）
        │      rollout_task_views.jsonl RolloutTaskView 行（public bundle 全量 + 身份 + 两个 digest）
        │      prepared_manifest.json   逐任务 (task_id, environment_package_digest, public_bundle_digest)
        │                               + 两个公开文件的 sha256 + 私有产物的期望 sha256
        └─ (b) runtime-private 产物 private_dir/host_grading_views.jsonl（目录 0700 / 文件 0600）
               HostGradingView 行（v2 评分面，无 golden）——只以 opaque 路径 + 期望 digest 被引用

    RolloutManager actor 进程
      只读 (a)(b) 并复核 identity/digest（本模块 load_* 三个读取口）；**不调用完整 loader**，
      进程内因此不存在 ValidationOnlyBundle / golden_patch / v1 PrivateGradingBundle 对象。

公开产物是模型侧可见面：写入前逐行过 forbidden marker 扫描；prompt 行的 metadata 只允许
`PromptRowMetadata` 的五个键，任何以 ``rh2_`` 开头的系统保留键都 fail-closed——这是 Wave1
F1"输入数据不得携带身份历史"的第二道边界（第一道在 identity.py 的铸造点）。

私有产物允许跨且只跨 "prep → actor" 这一次 runtime-private 文件边界；读取口除 digest 外还
检查 POSIX 权限位（group/other 任一可读即拒），路径与期望 digest 由启动参数携带，内容
不进任何 args/env/公共 evidence。
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, StringConstraints, ValidationError, model_validator

from repoharness2.contracts import scan_for_forbidden_markers
from repoharness2.contracts._base import NonEmptyStr, SafeIdentifier, Sha256Digest, StrictModel
from repoharness2.envpack.bundles import render_user_prompt
from repoharness2.envpack.bundles_v2 import task_id_for
from repoharness2.envpack.training_view import HostGradingView, RolloutTaskView, TrustedTaskController

PREPARED_MANIFEST_SCHEMA_ID = "rh2.prepared_tasks_manifest.v1"
MANIFEST_FILE = "prepared_manifest.json"
PROMPTS_FILE = "prompts.jsonl"
ROLLOUT_VIEWS_FILE = "rollout_task_views.jsonl"
HOST_GRADING_FILE = "host_grading_views.jsonl"

# miles Dataset 的三个取数键（launch: --input-key prompt --label-key label --metadata-key metadata）。
PROMPT_KEY = "prompt"
LABEL_KEY = "label"
METADATA_KEY = "metadata"

# 系统保留前缀：六字段身份键与 termination 事实键都以它开头；prompt 行 metadata 里出现即污染。
RESERVED_METADATA_PREFIX = "rh2_"

# F4 authoritative join 消费的三个分派键（host 原始分派事实，随 Sample.metadata 进入 actor）。
DISPATCH_METADATA_KEYS: tuple[str, ...] = (
    "task_id",
    "environment_package_digest",
    "public_bundle_digest",
)

HexDigest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class PreparedTasksError(ValueError):
    """prepared artifact 写入/读取的 fail-closed 异常（digest 不符、保留键、权限、记录错位、缺文件）。"""


class PromptRowMetadata(StrictModel):
    """prompt 行的 metadata（miles 原样放进 Sample.metadata 的模型侧可见分派事实）。"""

    task_id: NonEmptyStr = Field(description='source-qualified 任务主键（"<source>::<instance_id>"）。')
    source: Literal["swe_gym_lite"] = Field(description="数据源（与 EnvironmentPackageV1 同枚举）。")
    instance_id: SafeIdentifier = Field(description="源内任务 id（只作人读/事件记录，不是 join 键）。")
    environment_package_digest: Sha256Digest = Field(description="EnvironmentPackageV1.digest()（join 锚）。")
    public_bundle_digest: Sha256Digest = Field(description="PublicTaskBundle.digest()（模型可见面内容锚）。")

    @model_validator(mode="after")
    def _check_identity(self) -> "PromptRowMetadata":
        if self.task_id != task_id_for(self.source, self.instance_id):
            raise ValueError(f"task_id={self.task_id!r} 与 source::instance_id 不一致")
        return self


class PreparedTaskRecord(PromptRowMetadata):
    """manifest 里的逐任务记录：与 prompt 行 metadata 同形（actor 侧逐字比对）。"""


class PreparedFileDigest(StrictModel):
    sha256: HexDigest
    count: int = Field(ge=0, description="行数。")


class PreparedTasksManifest(StrictModel):
    schema_id: Literal["rh2.prepared_tasks_manifest.v1"] = Field(default=PREPARED_MANIFEST_SCHEMA_ID)
    prepared_at_utc: datetime
    task_count: int = Field(ge=1)
    tasks: list[PreparedTaskRecord]
    files: dict[str, PreparedFileDigest] = Field(description="两个公开文件（prompts / rollout views）的 digest。")
    host_grading_artifact_sha256: HexDigest = Field(
        description="runtime-private 产物文件内容的 sha256（只有 digest，无内容；actor 加载时与启动参数交回值双重比对）。"
    )
    host_grading_row_count: int = Field(ge=1)

    @model_validator(mode="after")
    def _check_consistency(self) -> "PreparedTasksManifest":
        if self.task_count != len(self.tasks):
            raise ValueError(f"task_count={self.task_count} 与 tasks 行数 {len(self.tasks)} 不符")
        ids = [t.task_id for t in self.tasks]
        if len(set(ids)) != len(ids):
            raise ValueError("manifest tasks 存在重复 task_id")
        if set(self.files) != {PROMPTS_FILE, ROLLOUT_VIEWS_FILE}:
            raise ValueError(f"manifest files 键集合不符: {sorted(self.files)}")
        for name, ent in self.files.items():
            if ent.count != self.task_count:
                raise ValueError(f"{name}: 行数 {ent.count} 与 task_count {self.task_count} 不符")
        if self.host_grading_row_count != self.task_count:
            raise ValueError("host_grading_row_count 与 task_count 不符")
        return self

    def record(self, task_id: str) -> PreparedTaskRecord:
        for rec in self.tasks:
            if rec.task_id == task_id:
                return rec
        raise PreparedTasksError(f"unknown task_id（不在 prepared manifest 内）: {task_id!r}")

    def task_ids(self) -> tuple[str, ...]:
        return tuple(t.task_id for t in self.tasks)


# 导入期静态断言：分派键必须是 prompt metadata 的字段子集，且没有任何字段撞保留前缀。
assert set(DISPATCH_METADATA_KEYS) <= set(PromptRowMetadata.model_fields)
assert not any(name.startswith(RESERVED_METADATA_PREFIX) for name in PromptRowMetadata.model_fields)


# ---------------------------------------------------------------------------
# 边界工具
# ---------------------------------------------------------------------------


def assert_no_reserved_keys(mapping: Mapping[str, Any], *, where: str) -> None:
    """F1 第二道边界：模型侧输入 metadata 不得携带任何 ``rh2_`` 保留键（含完整自洽的六键伪造）。"""

    polluted = sorted(str(k) for k in mapping if str(k).startswith(RESERVED_METADATA_PREFIX))
    if polluted:
        raise PreparedTasksError(
            f"{where}: metadata 携带系统保留键 {polluted}——输入数据不得携带身份/事实历史，fail-closed"
        )


def _reject_marker_hits(value: Any, *, where: str) -> None:
    hits = scan_for_forbidden_markers(value)
    if hits:
        detail = "; ".join(f"{h.path} 命中 {h.marker}（{h.kind}）" for h in hits)
        raise PreparedTasksError(f"{where}: 模型侧产物泄漏扫描命中 {len(hits)} 处：{detail}")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _jsonl(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows).encode("utf-8")


def _write_atomic(path: Path, data: bytes, *, mode: int) -> None:
    """临时文件 + fsync + os.replace；创建即带目标权限位（私有文件不经历 0644 窗口）。"""

    tmp = path.with_name(f".{path.name}.tmp")
    if tmp.exists():
        tmp.unlink()
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    os.chmod(tmp, mode)  # umask 可能收窄了 open 的 mode；显式钉死
    os.replace(tmp, path)
    dir_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def _read_jsonl(data: bytes, *, what: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(data.decode("utf-8").split("\n")[:-1], start=1):
        if not line.strip():
            raise PreparedTasksError(f"{what}: 第 {lineno} 行为空——产物不允许空行")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PreparedTasksError(f"{what}: 第 {lineno} 行不是合法 JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise PreparedTasksError(f"{what}: 第 {lineno} 行不是 JSON 对象")
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# host 侧：一次性 trusted-prep
# ---------------------------------------------------------------------------


def prepare_tasks(
    controller: TrustedTaskController,
    *,
    out_dir: Path | str,
    private_dir: Path | str,
    task_ids: Iterable[str] | None = None,
) -> PreparedTasksManifest:
    """从 trusted controller 生成两份产物（公开 + runtime-private）。

    只接受 `TrustedTaskController`（正式链 `from_repo_root`、测试 `build_for_tests_from_ingest_result`
    ——两条路径都已跑过四面关系检查）；取数口返回深拷贝，本函数在序列化前对每个视图再
    `revalidated()` 一次（消费时刻重验，Wave1 F3 纪律）。产物目录不覆盖已有文件：一次性
    产物如需重生成，换目录重跑（避免"半旧半新"的产物被 actor 读到）。
    """

    out_dir = Path(out_dir)
    private_dir = Path(private_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in (MANIFEST_FILE, PROMPTS_FILE, ROLLOUT_VIEWS_FILE):
        if (out_dir / name).exists():
            raise PreparedTasksError(f"{out_dir / name} 已存在——trusted-prep 是一次性产物，不覆盖旧产物（换目录重跑）")
    private_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(private_dir, 0o700)
    host_path = private_dir / HOST_GRADING_FILE
    if host_path.exists():
        raise PreparedTasksError(f"{host_path} 已存在——runtime-private 产物不覆盖（换目录重跑）")

    wanted = list(task_ids) if task_ids is not None else list(controller.task_ids())
    if not wanted:
        raise PreparedTasksError("task_ids 为空——没有可准备的任务")
    if len(set(wanted)) != len(wanted):
        raise PreparedTasksError("task_ids 存在重复")

    prompt_rows: list[dict[str, Any]] = []
    view_rows: list[dict[str, Any]] = []
    host_rows: list[dict[str, Any]] = []
    records: list[PreparedTaskRecord] = []
    for tid in wanted:
        rv = controller.rollout_view(tid).revalidated()
        gv = controller.grading_view(tid, environment_package_digest=rv.environment_package_digest).revalidated()
        if (gv.task_id, gv.source, gv.instance_id) != (rv.task_id, rv.source, rv.instance_id):
            raise PreparedTasksError(f"{tid}: 两侧视图身份不一致，拒绝准备")
        if gv.environment_package_digest != rv.environment_package_digest:
            raise PreparedTasksError(f"{tid}: 两侧 environment_package_digest 不一致，拒绝准备")
        meta = PromptRowMetadata(
            task_id=rv.task_id,
            source=rv.source,
            instance_id=rv.instance_id,
            environment_package_digest=rv.environment_package_digest,
            public_bundle_digest=rv.public_bundle_digest,
        )
        row = {
            PROMPT_KEY: render_user_prompt(rv.public),
            LABEL_KEY: rv.task_id,
            METADATA_KEY: meta.model_dump(mode="json"),
        }
        assert_no_reserved_keys(row[METADATA_KEY], where=f"{tid} prompt metadata")
        _reject_marker_hits(row, where=f"{tid} prompt 行")
        view_json = rv.model_dump(mode="json")
        _reject_marker_hits(view_json, where=f"{tid} rollout 视图")
        prompt_rows.append(row)
        view_rows.append(view_json)
        host_rows.append(gv.model_dump(mode="json"))
        records.append(PreparedTaskRecord(**meta.model_dump()))

    prompts_bytes = _jsonl(prompt_rows)
    views_bytes = _jsonl(view_rows)
    host_bytes = _jsonl(host_rows)
    _write_atomic(out_dir / PROMPTS_FILE, prompts_bytes, mode=0o644)
    _write_atomic(out_dir / ROLLOUT_VIEWS_FILE, views_bytes, mode=0o644)
    _write_atomic(host_path, host_bytes, mode=0o600)
    manifest = PreparedTasksManifest(
        prepared_at_utc=datetime.now(timezone.utc),
        task_count=len(records),
        tasks=records,
        files={
            PROMPTS_FILE: PreparedFileDigest(sha256=_sha256(prompts_bytes), count=len(records)),
            ROLLOUT_VIEWS_FILE: PreparedFileDigest(sha256=_sha256(views_bytes), count=len(records)),
        },
        host_grading_artifact_sha256=_sha256(host_bytes),
        host_grading_row_count=len(records),
    )
    _write_atomic(out_dir / MANIFEST_FILE, manifest.model_dump_json(indent=2).encode("utf-8"), mode=0o644)
    return manifest


# ---------------------------------------------------------------------------
# actor 侧：只读取 + 复核（不调完整 loader）
# ---------------------------------------------------------------------------


def load_prepared_manifest(prepared_dir: Path | str) -> PreparedTasksManifest:
    path = Path(prepared_dir) / MANIFEST_FILE
    if not path.is_file():
        raise PreparedTasksError(f"prepared manifest 缺失: {path}")
    try:
        return PreparedTasksManifest.model_validate_json(path.read_bytes())
    except ValidationError as exc:
        raise PreparedTasksError(f"prepared manifest 非法: {exc}") from exc


def _verify_file_digest(path: Path, expected: PreparedFileDigest, *, what: str) -> bytes:
    if not path.is_file():
        raise PreparedTasksError(f"{what}: 文件缺失 {path}")
    data = path.read_bytes()
    actual = _sha256(data)
    if actual != expected.sha256:
        raise PreparedTasksError(
            f"{what}: sha256 与 prepared manifest 不符（actual {actual[:16]}… != expected {expected.sha256[:16]}…）"
            "——产物被改/半写，拒绝消费"
        )
    return data


def _check_record(rec: PreparedTaskRecord, *, what: str, **actual: Any) -> None:
    for key, value in actual.items():
        if getattr(rec, key) != value:
            raise PreparedTasksError(f"{what}: {key}={value!r} 与 manifest 记录 {getattr(rec, key)!r} 不符")


def load_prepared_rollout_views(prepared_dir: Path | str, manifest: PreparedTasksManifest) -> dict[str, RolloutTaskView]:
    """读公开产物：两个文件 digest ↔ manifest；视图行 revalidated() 后逐字段对 manifest 记录；
    prompt 行 metadata 不得带保留键、必须与记录逐字相等、prompt 文本必须等于由 public bundle
    重新渲染的结果（模型可见面不得被单独改写）。"""

    prepared_dir = Path(prepared_dir)
    prompts_bytes = _verify_file_digest(prepared_dir / PROMPTS_FILE, manifest.files[PROMPTS_FILE], what=PROMPTS_FILE)
    views_bytes = _verify_file_digest(
        prepared_dir / ROLLOUT_VIEWS_FILE, manifest.files[ROLLOUT_VIEWS_FILE], what=ROLLOUT_VIEWS_FILE
    )
    expected_ids = set(manifest.task_ids())

    views: dict[str, RolloutTaskView] = {}
    for row in _read_jsonl(views_bytes, what=ROLLOUT_VIEWS_FILE):
        try:
            view = RolloutTaskView.model_validate(row).revalidated()
        except ValidationError as exc:
            raise PreparedTasksError(f"{ROLLOUT_VIEWS_FILE}: 视图行非法: {exc}") from exc
        rec = manifest.record(view.task_id)
        _check_record(
            rec,
            what=f"{ROLLOUT_VIEWS_FILE} {view.task_id}",
            source=view.source,
            instance_id=view.instance_id,
            environment_package_digest=view.environment_package_digest,
            public_bundle_digest=view.public_bundle_digest,
        )
        if view.task_id in views:
            raise PreparedTasksError(f"{ROLLOUT_VIEWS_FILE}: 重复 task_id {view.task_id}")
        views[view.task_id] = view
    if set(views) != expected_ids:
        raise PreparedTasksError(f"{ROLLOUT_VIEWS_FILE}: task 集合与 manifest 不一致")

    seen: set[str] = set()
    for row in _read_jsonl(prompts_bytes, what=PROMPTS_FILE):
        if set(row) != {PROMPT_KEY, LABEL_KEY, METADATA_KEY}:
            raise PreparedTasksError(f"{PROMPTS_FILE}: 行键集合不符 {sorted(row)}")
        raw_meta = row[METADATA_KEY]
        if not isinstance(raw_meta, dict):
            raise PreparedTasksError(f"{PROMPTS_FILE}: metadata 不是对象")
        assert_no_reserved_keys(raw_meta, where=f"{PROMPTS_FILE} 行")
        try:
            meta = PromptRowMetadata.model_validate(raw_meta)
        except ValidationError as exc:
            raise PreparedTasksError(f"{PROMPTS_FILE}: metadata 非法: {exc}") from exc
        rec = manifest.record(meta.task_id)
        if meta.model_dump() != PromptRowMetadata(**rec.model_dump()).model_dump():
            raise PreparedTasksError(f"{PROMPTS_FILE} {meta.task_id}: metadata 与 manifest 记录不符")
        if row[LABEL_KEY] != meta.task_id:
            raise PreparedTasksError(f"{PROMPTS_FILE} {meta.task_id}: label 与 task_id 不符")
        if row[PROMPT_KEY] != render_user_prompt(views[meta.task_id].public):
            raise PreparedTasksError(f"{PROMPTS_FILE} {meta.task_id}: prompt 文本与 public bundle 渲染结果不符（模型可见面被改写）")
        if meta.task_id in seen:
            raise PreparedTasksError(f"{PROMPTS_FILE}: 重复 task_id {meta.task_id}")
        seen.add(meta.task_id)
    if seen != expected_ids:
        raise PreparedTasksError(f"{PROMPTS_FILE}: task 集合与 manifest 不一致")
    return views


def _check_private_permissions(path: Path) -> None:
    if os.name != "posix":
        return
    for target, what in ((path, "文件"), (path.parent, "目录")):
        mode = stat.S_IMODE(target.stat().st_mode)
        if mode & 0o077:
            raise PreparedTasksError(
                f"runtime-private 产物{what} {target} 权限 {oct(mode)} 对 group/other 开放——拒绝加载（要求目录 0700 / 文件 0600）"
            )


def load_host_grading_views(
    path: Path | str, *, expected_sha256: str, manifest: PreparedTasksManifest
) -> dict[str, HostGradingView]:
    """读 runtime-private 产物：权限位 + 双重 digest（启动参数交回值 == manifest 期望 == 实际内容）
    + 逐行 revalidated() + 逐字段对 manifest 记录。"""

    path = Path(path)
    if not path.is_file():
        raise PreparedTasksError(f"runtime-private 产物缺失: {path}")
    _check_private_permissions(path)
    if expected_sha256 != manifest.host_grading_artifact_sha256:
        raise PreparedTasksError(
            "启动参数交回的 runtime-private 产物期望 digest 与 prepared manifest 记录不符——两份期望值分家，拒绝加载"
        )
    data = path.read_bytes()
    actual = _sha256(data)
    if actual != expected_sha256:
        raise PreparedTasksError(
            f"runtime-private 产物 sha256 不符（actual {actual[:16]}… != expected {expected_sha256[:16]}…）——拒绝加载"
        )
    views: dict[str, HostGradingView] = {}
    for row in _read_jsonl(data, what=HOST_GRADING_FILE):
        try:
            view = HostGradingView.model_validate(row).revalidated()
        except ValidationError as exc:
            raise PreparedTasksError(f"{HOST_GRADING_FILE}: 视图行非法: {exc}") from exc
        rec = manifest.record(view.task_id)
        _check_record(
            rec,
            what=f"{HOST_GRADING_FILE} {view.task_id}",
            source=view.source,
            instance_id=view.instance_id,
            environment_package_digest=view.environment_package_digest,
        )
        if view.task_id in views:
            raise PreparedTasksError(f"{HOST_GRADING_FILE}: 重复 task_id {view.task_id}")
        views[view.task_id] = view
    if len(views) != manifest.host_grading_row_count or set(views) != set(manifest.task_ids()):
        raise PreparedTasksError(f"{HOST_GRADING_FILE}: task 集合/行数与 manifest 不一致")
    return views


def verify_prompt_data_binding(prompt_data: Any, manifest: PreparedTasksManifest) -> None:
    """miles RolloutDataSource 读的文件（args.prompt_data）必须就是 prep 写出的 prompts.jsonl
    （按内容 digest 绑定，不按路径字符串）。"""

    if not isinstance(prompt_data, (str, os.PathLike)) or not str(prompt_data):
        raise PreparedTasksError("prepared 链要求 args.prompt_data 指向 prep 产物的 prompts.jsonl（缺失/非法）")
    _verify_file_digest(Path(prompt_data), manifest.files[PROMPTS_FILE], what="args.prompt_data")


__all__ = [
    "DISPATCH_METADATA_KEYS",
    "HOST_GRADING_FILE",
    "LABEL_KEY",
    "MANIFEST_FILE",
    "METADATA_KEY",
    "PREPARED_MANIFEST_SCHEMA_ID",
    "PROMPTS_FILE",
    "PROMPT_KEY",
    "RESERVED_METADATA_PREFIX",
    "ROLLOUT_VIEWS_FILE",
    "PreparedFileDigest",
    "PreparedTaskRecord",
    "PreparedTasksError",
    "PreparedTasksManifest",
    "PromptRowMetadata",
    "assert_no_reserved_keys",
    "load_host_grading_views",
    "load_prepared_manifest",
    "load_prepared_rollout_views",
    "prepare_tasks",
    "verify_prompt_data_binding",
]
