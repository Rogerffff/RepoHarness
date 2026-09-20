"""S1-d（评分接线 2026-09-15）：真实评分链 driver——用脚本代替"模型写补丁"，其余逐字复用生产实现。

流程（每题每次尝试）：

    fresh 候选容器（rollout profile 的 docker run 参数 + 可信初始化，driver 唯一 owner）
      → materialize 血缘探针 → generate_baseline_manifest（B1）
      → 以候选用户（agent/54321）`git apply --check` 后写入补丁；失败即记 apply_failed 停止，不 fuzz、不改补丁
      → export_frozen_patch（B2）→ classify_frozen_patch（unsafe 保存证据、不评分）
      → build_trusted_scoring_projection（D2-3）→ FrozenDeltaSource 持久化 → 释放候选容器
      → SWEGradingManager.grade(workspace=None, frozen_delta=…, deadline_monotonic=…)（正式 grader profile）
      → 账本行（§6.5）+ 诊断 sidecar 引用。

两份预算互不共用：`candidate_stage_seconds` 覆盖创建到导出持久化；`grading_deadline_seconds` 只给 grade()。
外层 `finally` 用独立有限时间清理候选容器。任务加载走 actor 同一读取口（prepared/private 两目录 + manifest
digest），gold 由受信步骤 `export_gold_candidates` 从 validation bundle 导出为普通候选补丁文件（prepared/private
本身不含 gold）。派生镜像（D4）只能以 `image_local_build=True` 使用，账本记录实际 image ID。

这是接线对账工具，不是训练链入口：不走队列、不走 miles；A 线复核点见接线页 §6.3。
"""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import re
import time
import uuid
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from repoharness2.adapters.slime.baseline_census import (
    BaselineCensusError,
    baseline_policy_for_task_id,
    generate_baseline_manifest,
)
from repoharness2.adapters.slime.patch_exporter import PatchExportError, export_frozen_patch
from repoharness2.adapters.slime.prepared_task_face import build_grading_spec_from_host_view
from repoharness2.adapters.slime.sandbox_profile import (
    GraderSandboxProfile,
    RolloutSandboxProfile,
    rollout_trusted_init_script,
    run_labels_from_env,
)
from repoharness2.contracts.frozen_patch import compute_frozen_patch_digest
from repoharness2.contracts.scoring_projection import ProjectionContractError, classify_frozen_patch
from repoharness2.envpack import materialize
from repoharness2.envpack.bundles_v2 import ValidationOnlyBundle
from repoharness2.envpack.prepared_tasks import (
    HOST_GRADING_FILE,
    PreparedTasksManifest,
    load_host_grading_views,
    load_prepared_manifest,
    load_prepared_rollout_views,
    manifest_file_sha256,
    prepare_tasks,
)
from repoharness2.envpack.training_view import HostGradingView, RolloutTaskView, TrustedTaskController
from repoharness2.grading.manager import (
    BaselineIntegrityError,
    ExecResult,
    FrozenDeltaSource,
    GradingEnvSpec,
    SWEGradingManager,
    run_docker,
    EnvQualification,
    env_qualification_status,
    grading_image_identity,
    grading_scripts_digest,
)
from repoharness2.grading.trusted_projection import build_trusted_scoring_projection

DockerRunner = Callable[..., Awaitable[ExecResult]]
LEDGER_SCHEMA_ID = "rh2.replay_grade_ledger.v1"
CANDIDATE_PATCH_PATH = "/tmp/rh2_candidate.patch"
CandidateKind = Literal["noop", "gold", "cc", "contrast"]


class ReplayHaltError(RuntimeError):
    """I2：候选容器无法确认已终止/移除——记证据后停止本批，不再开新尝试。"""


class ReplayStageError(RuntimeError):
    """候选阶段某一步失败（记录首个失败原因；不是评分结论）。"""

    def __init__(self, stage: str, reason: str) -> None:
        self.stage = stage
        self.reason = reason
        super().__init__(f"[{stage}] {reason}")


@dataclass(frozen=True)
class ReplayBudgets:
    candidate_stage_seconds: float = 900.0
    grading_deadline_seconds: float = 3600.0
    cleanup_seconds: float = 120.0
    image_pull_seconds: float = 1800.0  # 首次拉镜像单独预算，不消耗候选阶段预算

    def __post_init__(self) -> None:
        for name in ("candidate_stage_seconds", "grading_deadline_seconds", "cleanup_seconds", "image_pull_seconds"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} 必须为正数")


@dataclass(frozen=True)
class CandidateInput:
    kind: CandidateKind
    origin: str
    patch_text: str | None = None  # None = noop（不写任何改动）

    @property
    def patch_sha256(self) -> str | None:
        if self.patch_text is None:
            return None
        return "sha256:" + hashlib.sha256(self.patch_text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DerivedImage:
    """D4=A 的诊断性派生镜像：只能以 image_local_build 使用，账本记录实际 image ID 与配方说明。"""

    ref: str
    recipe: str


@dataclass
class DockerExecWorkspace:
    """`docker exec` 形态的 WorkspaceRunner（census / 探针 / 补丁写入共用）。"""

    docker: DockerRunner
    name: str
    user: str | None = None
    home: str | None = None

    async def run_bash(self, script: str, *, input_bytes: bytes | None = None) -> ExecResult:
        args: list[str] = ["exec"]
        if input_bytes is not None:
            args.append("-i")
        if self.user is not None:
            args += ["-u", self.user]
        if self.home is not None:
            args += ["-e", f"HOME={self.home}"]
        args += [self.name, "bash", "-c", script]
        if input_bytes is not None:
            return await self.docker(*args, input_bytes=input_bytes)
        return await self.docker(*args)


@dataclass(frozen=True)
class ReplayContext:
    manifest: PreparedTasksManifest
    rollout_views: dict[str, RolloutTaskView]
    grading_views: dict[str, HostGradingView]
    rollout_profile: RolloutSandboxProfile
    grader_profile: GraderSandboxProfile
    run_id: str
    artifacts_dir: Path
    docker: DockerRunner = run_docker
    derived_image: DerivedImage | None = None
    # 第四组 P-A：按 task_id 的环境资格记录（load_env_qualifications 从账本构造；manager 自行核对身份与摘要）
    qualifications: dict[str, EnvQualification] = field(default_factory=dict)

    def resolve_task_id(self, ref: str) -> str:
        """接受 source-qualified task_id 或裸 instance_id。"""
        if ref in self.grading_views:
            return ref
        hits = [t for t in self.grading_views if t.endswith("::" + ref)]
        if len(hits) != 1:
            raise KeyError(f"task 引用 {ref!r} 不唯一或不存在（命中 {hits}）")
        return hits[0]


def load_context(
    *,
    prepared_dir: Path | str,
    private_dir: Path | str,
    manifest_sha256: str,
    rollout_profile: RolloutSandboxProfile,
    grader_profile: GraderSandboxProfile,
    artifacts_dir: Path | str,
    run_id: str | None = None,
    docker: DockerRunner = run_docker,
    derived_image: DerivedImage | None = None,
    qualifications: dict[str, EnvQualification] | None = None,
) -> ReplayContext:
    """走 actor 同一读取口（identity/digest/权限复核），不调完整 loader。"""
    manifest = load_prepared_manifest(prepared_dir, expected_sha256=manifest_sha256)
    rollout_views = load_prepared_rollout_views(prepared_dir, manifest)
    grading_views = load_host_grading_views(
        Path(private_dir) / HOST_GRADING_FILE, expected_sha256=manifest.host_grading_artifact_sha256, manifest=manifest,
    )
    return ReplayContext(
        manifest=manifest, rollout_views=rollout_views, grading_views=grading_views,
        rollout_profile=rollout_profile, grader_profile=grader_profile,
        run_id=run_id or uuid.uuid4().hex[:12], artifacts_dir=Path(artifacts_dir), docker=docker,
        derived_image=derived_image, qualifications=dict(qualifications or {}),
    )


def prepare_for_replay(*, repo_root: Path | str, out_dir: Path | str, private_dir: Path | str, task_ids: Iterable[str] | None) -> dict[str, Any]:
    """受信准备（host 进程一次性）：与 `envpack.trusted_prep` 同一入口，附带写出 summary.json 供 run 子命令消费。"""
    controller = TrustedTaskController.from_repo_root(Path(repo_root).resolve())
    manifest = prepare_tasks(controller, out_dir=out_dir, private_dir=private_dir, task_ids=list(task_ids) if task_ids else None)
    summary = {
        "prepared_dir": str(Path(out_dir).resolve()),
        "private_dir": str(Path(private_dir).resolve()),
        "prepared_manifest_sha256": manifest_file_sha256(out_dir),
        "host_grading_artifact_sha256": manifest.host_grading_artifact_sha256,
        "task_ids": list(manifest.task_ids()),
    }
    (Path(out_dir) / "replay_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


def export_gold_candidates(*, ingest_dir: Path | str, instance_ids: Iterable[str], out_dir: Path | str) -> dict[str, Any]:
    """受信步骤：把 validation bundle 的 golden_patch 导出为绑定 instance 的普通候选补丁文件（<iid>.gold.patch），
    校验 golden_patch_sha256；不经过 prepared/private（safe view 边界不变）。"""
    wanted = set(instance_ids)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(line) for line in (Path(ingest_dir) / "validation_bundles_v0.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    written: dict[str, str] = {}
    for row in rows:
        bundle = ValidationOnlyBundle.model_validate(row)
        if bundle.instance_id not in wanted:
            continue
        actual = "sha256:" + hashlib.sha256(bundle.golden_patch.encode("utf-8")).hexdigest()
        declared = bundle.golden_patch_sha256 if str(bundle.golden_patch_sha256).startswith("sha256:") else "sha256:" + str(bundle.golden_patch_sha256)
        if actual != declared:
            raise ValueError(f"{bundle.instance_id}: golden_patch sha256 不符（{actual} != {declared}）")
        path = out / f"{bundle.instance_id}.gold.patch"
        path.write_text(bundle.golden_patch, encoding="utf-8")
        written[bundle.instance_id] = actual
    missing = sorted(wanted - set(written))
    if missing:
        raise KeyError(f"validation bundle 缺少 {missing}")
    manifest = {"schema_id": "rh2.gold_candidate_export.v1", "entries": written, "exported_at_utc": _now_iso()}
    (out / "gold_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    return manifest


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(text: str, limit: int = 40) -> str:
    return (re.sub(r"[^a-zA-Z0-9_.-]", "-", text).strip("-.") or "x")[:limit]


def _tail(text: str, n: int = 400) -> str:
    return text.strip()[-n:]


@dataclass
class _CandidateStage:
    """候选阶段产物（导出持久化后候选容器即可释放）。"""

    head: str = ""
    apply_method: str = "noop"
    apply_stderr_tail: str = ""
    baseline: Any = None
    artifact: Any = None
    classification: Any = None
    projection: Any = None
    split: Any = None
    last_stage: str = "created"
    stage_error: str | None = None
    omitted: dict[str, Any] = field(default_factory=dict)  # P-C：{"baseline": {...}, "post": {...}}


class ReplayGrader:
    """一个 run 的对账执行器：持有上下文、manager 与账本；每题每次尝试一行。"""

    def __init__(
        self,
        ctx: ReplayContext,
        manager: SWEGradingManager,
        *,
        ledger_path: Path | str,
        budgets: ReplayBudgets | None = None,
    ) -> None:
        self.ctx = ctx
        self.manager = manager
        self.ledger_path = Path(ledger_path)
        self.budgets = budgets or ReplayBudgets()
        self.cleanup_failures: list[str] = []

    # ------------------------------------------------------------------ 候选阶段
    async def _candidate_stage(
        self, *, task_id: str, candidate: CandidateInput, container: str, stage: _CandidateStage, spec: GradingEnvSpec,
        runtime_image_digest: str,
    ) -> None:
        ctx = self.ctx
        view = ctx.rollout_views[task_id]
        public = view.public
        rp = ctx.rollout_profile
        docker = ctx.docker

        stage.last_stage = "container_start"
        image = ctx.derived_image.ref if ctx.derived_image is not None else public.image
        run = await docker(*rp.docker_run_args(name=container, network="none", image=image, labels=run_labels_from_env()))
        if run.exit_code != 0:
            raise ReplayStageError("container_start", _tail(run.stderr))
        root_ws = DockerExecWorkspace(docker, container)
        agent_ws = DockerExecWorkspace(docker, container, user=str(rp.agent_uid), home=f"/home/{rp.agent_user}")

        stage.last_stage = "trusted_init"
        init = await root_ws.run_bash(rollout_trusted_init_script(rp))
        if init.exit_code != 0 or "RH2_INIT_OK=1" not in init.stdout:
            raise ReplayStageError("trusted_init", _tail(init.stdout + init.stderr))

        stage.last_stage = "materialize_probe"
        probe = await root_ws.run_bash(materialize.build_probe_script(public.base_commit))
        check = materialize.evaluate_probe(public.base_commit, probe.exit_code, probe.stdout, probe.stderr)
        try:
            check.ensure_ok()
        except materialize.MaterializeError as exc:
            raise ReplayStageError("materialize_probe", str(exc)) from exc
        stage.head = check.head

        stage.last_stage = "baseline_census"
        try:
            base_omitted: dict[str, int] = {}
            stage.baseline = await generate_baseline_manifest(
                root_ws, task_id=view.task_id, workdir=public.workdir, public_bundle_digest=view.public_bundle_digest,
                runtime_image_digest=runtime_image_digest, materialized_head=check.head, task_base_commit=public.base_commit,
                policy=baseline_policy_for_task_id(view.task_id), omitted_sink=base_omitted,
            )
            stage.omitted["baseline"] = base_omitted
        except BaselineCensusError as exc:
            raise ReplayStageError("baseline_census", str(exc)) from exc

        stage.last_stage = "apply_candidate"
        if candidate.patch_text is not None:
            write = await agent_ws.run_bash(f"cat > {CANDIDATE_PATCH_PATH}", input_bytes=candidate.patch_text.encode("utf-8"))
            if write.exit_code != 0:
                raise ReplayStageError("apply_candidate", "写入补丁失败：" + _tail(write.stderr))
            wd = public.workdir
            check_res = await agent_ws.run_bash(f"cd {wd} && git apply --check {CANDIDATE_PATCH_PATH}")
            if check_res.exit_code != 0:
                stage.apply_method = "apply_failed"
                stage.apply_stderr_tail = _tail(check_res.stderr + check_res.stdout)
                return  # 不 fuzz、不改补丁：记录后停止，不进入评分
            applied = await agent_ws.run_bash(f"cd {wd} && git apply {CANDIDATE_PATCH_PATH} && rm -f {CANDIDATE_PATCH_PATH}")
            if applied.exit_code != 0:
                raise ReplayStageError("apply_candidate", "--check 通过但 apply 失败：" + _tail(applied.stderr))
            stage.apply_method = "git_apply"

        stage.last_stage = "export"
        try:
            post_omitted: dict[str, int] = {}
            stage.artifact = await export_frozen_patch(
                root_ws, stage.baseline,
                rollout_execution_id=f"replay-{ctx.run_id}-{_slug(task_id)}",
                physical_attempt_id=f"replay-{ctx.run_id}-{_slug(task_id)}-{container[-8:]}",
                omitted_sink=post_omitted,
            )
            stage.omitted["post"] = post_omitted
        except PatchExportError as exc:
            raise ReplayStageError("export", str(exc)) from exc

        stage.last_stage = "classify"
        try:
            stage.classification, _ = classify_frozen_patch(stage.artifact, stage.baseline)
        except ProjectionContractError as exc:
            raise ReplayStageError("classify", f"契约矛盾（fatal）：{exc}") from exc
        if stage.classification.verdict != "projectable":
            return  # unsafe：证据已在 artifact/classification 里，不评分

        stage.last_stage = "projection"
        stage.projection, stage.split = build_trusted_scoring_projection(stage.artifact, spec.hygiene)
        if stage.split.unsupported_shape_reasons:
            # 第四组 P-D（R5）：投影后必要的祖先删除被控制面排除——已知不支持形状，不进 grader
            raise ReplayStageError("projection", ";".join(stage.split.unsupported_shape_reasons)[:300])

    async def _remove_container(self, container: str) -> dict[str, Any]:
        """I2：rm -f → 失败则 inspect → 仍在运行则 kill → 再 rm；有界；只有 daemon 明确"没有这个容器"或 rm 成功
        才算 removed。不能确认时返回 removed=False，由 replay_one 记证据并停止本批。"""

        budget = self.budgets.cleanup_seconds
        deadline = time.monotonic() + budget
        steps: list[str] = []

        async def _run(*args: str) -> ExecResult | None:
            left = deadline - time.monotonic()
            if left <= 0:
                steps.append(f"{args[0]}:no_budget")
                return None
            try:
                return await asyncio.wait_for(self.ctx.docker(*args), timeout=left)
            except (TimeoutError, asyncio.TimeoutError):
                steps.append(f"{args[0]}:timeout")
                return None
            except Exception as exc:  # noqa: BLE001 - 清理路径上的 CLI 异常只留痕，不让收口本身崩溃
                steps.append(f"{args[0]}:exception:{type(exc).__name__}")
                return None

        def _absent(res: ExecResult) -> bool:
            err = (res.stderr or res.stdout or "").lower()
            return ("no such container" in err or "no such object" in err) and container.lower() in err

        rm = await _run("rm", "-f", container)
        if rm is not None and (rm.exit_code == 0 or _absent(rm)):
            return {"removed": True, "detail": "", "steps": steps + ["rm:ok"]}
        steps.append("rm:failed:" + (_tail(rm.stderr, 120) if rm is not None else "none"))
        ins = await _run("inspect", "-f", "{{.State.Running}}", container)
        if ins is not None and ins.exit_code != 0 and _absent(ins):
            return {"removed": True, "detail": "absent_on_inspect", "steps": steps}
        if ins is not None and ins.stdout.strip() == "true":
            kill = await _run("kill", container)
            steps.append("kill:" + ("ok" if kill is not None and kill.exit_code == 0 else "failed"))
        rm2 = await _run("rm", "-f", container)
        if rm2 is not None and (rm2.exit_code == 0 or _absent(rm2)):
            return {"removed": True, "detail": "removed_after_kill", "steps": steps + ["rm:ok"]}
        detail = _tail(rm2.stderr, 200) if rm2 is not None else "rm timeout"
        self.cleanup_failures.append(f"{container}: {detail}")
        return {"removed": False, "detail": detail, "steps": steps}

    # ------------------------------------------------------------------ 一次尝试
    async def replay_one(self, task_ref: str, candidate: CandidateInput, *, attempt: int = 1) -> dict[str, Any]:
        ctx = self.ctx
        task_id = ctx.resolve_task_id(task_ref)
        view = ctx.rollout_views[task_id]
        gview = ctx.grading_views[task_id]
        public = view.public
        nonce = uuid.uuid4().hex[:8]
        container = f"rh2-replay-cand-{_slug(gview.instance_id, 24)}-{nonce}"
        started = _now_iso()
        stage = _CandidateStage()

        spec = build_grading_spec_from_host_view(
            view=gview, image=public.image, image_manifest_digest=public.image_manifest_digest,
            env_qualification=ctx.qualifications.get(task_id),  # P-A：manager 核对身份/摘要，不符视同缺席
        )
        image_id_actual: str | None = None
        runtime_image_digest = public.image_manifest_digest
        derived_error: str | None = None
        if ctx.derived_image is not None:
            # 派生镜像：先把 spec 切到 local_build（身份先按 tag，inspect 到 ID 后换成 ID）
            spec = dataclasses.replace(spec, image=ctx.derived_image.ref, image_manifest_digest=None, image_local_build=True)
        row: dict[str, Any] = {
            "schema_id": LEDGER_SCHEMA_ID, "run_id": ctx.run_id, "task_id": task_id, "instance_id": gview.instance_id,
            "source": gview.source, "attempt": attempt, "started_at_utc": started,
            "image_ref": spec.image, "image_digest_expected": public.image_manifest_digest,
            "image_id_actual": image_id_actual, "image_local_build": spec.image_local_build,
            "derived_image_recipe": ctx.derived_image.recipe if ctx.derived_image else None,
            "candidate": {"kind": candidate.kind, "origin": candidate.origin, "patch_sha256": candidate.patch_sha256,
                          "apply_method": None, "apply_user": f"{ctx.rollout_profile.agent_user}/{ctx.rollout_profile.agent_uid}",
                          "apply_stderr_tail": None},
            "classification": None, "projection": None,
            "policy": {**_policy_of(ctx.grader_profile)},
            "budgets": dataclasses.asdict(self.budgets),
            "report": None, "phases": None, "diagnostics_ref": None, "install": None, "test": None,
            "verdict_diagnostics": None, "resource": None, "log": None, "reference": None,
            "stage_error": None, "cleanup": None, "regrade_total": None, "notes": [],
            # P-A：资格账本的键（镜像身份 + 脚本摘要）、本次资格状态、三路判定与资源事实（评分后填）
            "image_identity": grading_image_identity(spec), "scripts_digest": grading_scripts_digest(spec),
            "env_qualification": env_qualification_status(spec)[1],
            "reference_missing_count": None, "execution_failure_decision": None, "resource_facts": None,
        }
        if ctx.derived_image is not None:
            # 接线页 §14.2 余项：账本行先建立，inspect 期间被取消也有落账；R5-P2：资格键用实际 image ID
            try:
                ins = await asyncio.wait_for(
                    ctx.docker("image", "inspect", "-f", "{{.Id}}", ctx.derived_image.ref), timeout=self.budgets.image_pull_seconds,
                )
            except (TimeoutError, asyncio.TimeoutError):
                derived_error = "derived_image:inspect_timeout"  # R4：inspect 也在镜像预算内
            except asyncio.CancelledError:
                row["stage_error"] = "cancelled:derived_image_inspect"
                self._append(row)
                raise
            else:
                if ins.exit_code != 0 or not ins.stdout.strip().startswith("sha256:"):
                    derived_error = f"derived_image:not_inspectable:{_tail(ins.stderr, 200)}"
                else:
                    image_id_actual = ins.stdout.strip()
                    runtime_image_digest = image_id_actual
                    spec = dataclasses.replace(spec, image_local_build_id=image_id_actual)
                    row["image_id_actual"] = image_id_actual
                    row["image_identity"] = grading_image_identity(spec)
                    row["env_qualification"] = env_qualification_status(spec)[1]

        if derived_error is not None:
            row["stage_error"] = derived_error
            self._append(row)
            return row

        # ---- 首次拉镜像单独预算（R4：inspect 与 pull 一起包在预算内；拉取期间取消也落账）----
        try:
            row["image_pull"] = await asyncio.wait_for(self._ensure_image(spec.image), timeout=self.budgets.image_pull_seconds)
        except (TimeoutError, asyncio.TimeoutError):
            row["image_pull"] = {"pulled": False, "error": "timeout"}
        except asyncio.CancelledError:
            row["stage_error"] = "cancelled:image_pull"
            self._append(row)
            raise
        if row["image_pull"].get("error"):
            row["stage_error"] = f"image_pull:{row['image_pull']['error']}"
            self._append(row)
            return row

        # ---- 候选阶段（有界；finally：先持久化、再有界清理；R1：持久化失败或清理期间被取消都不跳过清理）----
        cancelled = False
        persist_error: str | None = None
        try:
            await asyncio.wait_for(
                self._candidate_stage(task_id=task_id, candidate=candidate, container=container, stage=stage, spec=spec,
                                      runtime_image_digest=runtime_image_digest),
                timeout=self.budgets.candidate_stage_seconds,
            )
        except (TimeoutError, asyncio.TimeoutError):
            stage.stage_error = f"candidate_stage_timeout:{stage.last_stage}"
        except ReplayStageError as exc:
            stage.stage_error = f"{exc.stage}:{exc.reason}"
        except asyncio.CancelledError:
            stage.stage_error = f"cancelled:{stage.last_stage}"  # I6：取消也要有账本行
            cancelled = True
        finally:
            try:
                self._persist_candidate_artifacts(task_id, attempt, nonce, candidate, stage)
            except Exception as exc:  # noqa: BLE001 - 写盘失败不能跳过容器清理；记录后停止本批
                persist_error = f"{type(exc).__name__}:{_tail(str(exc), 200)}"
            cleanup_task = asyncio.ensure_future(self._remove_container(container))
            try:
                row["cleanup"] = await asyncio.shield(cleanup_task)
            except asyncio.CancelledError:
                # 清理期间收到首次取消：等这个已有预算的清理跑完，记录结果后再传播取消
                cancelled = True
                if stage.stage_error is None:
                    stage.stage_error = "cancelled:cleanup"
                row["cleanup"] = await cleanup_task
        if persist_error is not None:
            row["notes"].append(f"artifact persist failed: {persist_error}")
            stage.stage_error = stage.stage_error or f"persist_failed:{persist_error}"
        row["candidate"]["apply_method"] = stage.apply_method
        row["candidate"]["apply_stderr_tail"] = stage.apply_stderr_tail or None
        if stage.classification is not None:
            row["classification"] = {"verdict": stage.classification.verdict, "reason_codes": list(stage.classification.reason_codes)}
        if stage.split is not None and stage.projection is not None:
            row["projection"] = {
                "included_paths": list(stage.projection.included_entry_paths),
                "ignored_paths": [e.to_dict() for e in stage.split.ignored_entries],
                "unsupported_shape_reasons": list(stage.split.unsupported_shape_reasons),
                "frozen_patch_digest": stage.projection.frozen_patch_digest,
            }
        row["omitted_cache_count"] = stage.omitted or None
        row["baseline_policy_version"] = stage.baseline.policy.policy_version if stage.baseline is not None else None
        if stage.stage_error is not None:
            row["stage_error"] = stage.stage_error
            self._append(row)
            if cancelled:
                raise asyncio.CancelledError()
            if not row["cleanup"]["removed"]:
                raise ReplayHaltError(f"{container}: 候选容器未能确认移除（{row['cleanup']['detail']}），停止本批")
            if persist_error is not None:
                raise ReplayHaltError(f"{container}: 工件持久化失败（{persist_error}），停止本批")
            return row
        if not row["cleanup"]["removed"]:
            # I2：不能确认候选容器已终止/移除 → 记证据后停止本批，不开新尝试（也不评分）
            row["stage_error"] = f"candidate_container_cleanup_failed:{row['cleanup']['detail']}"
            self._append(row)
            raise ReplayHaltError(f"{container}: 候选容器未能确认移除（{row['cleanup']['detail']}），停止本批")
        if stage.apply_method == "apply_failed":
            row["notes"].append("candidate patch failed `git apply --check`; not graded")
            self._append(row)
            return row
        if stage.classification is not None and stage.classification.verdict != "projectable":
            row["notes"].append("unsafe artifact; not graded")
            self._append(row)
            return row

        # ---- 评分（只依赖冻结输入）----
        source = FrozenDeltaSource(
            frozen_patch=stage.artifact, baseline_manifest=stage.baseline, projection=stage.projection,
            frozen_patch_digest=compute_frozen_patch_digest(stage.artifact),
        )
        trajectory_id = f"replay-{ctx.run_id}-{_slug(gview.instance_id, 24)}-a{attempt}-{nonce}"
        try:
            report = await self.manager.grade(
                trajectory_id=trajectory_id, workspace=None, spec=spec, frozen_delta=source,
                deadline_monotonic=time.monotonic() + self.budgets.grading_deadline_seconds,
            )
        except asyncio.CancelledError:
            row["stage_error"] = "cancelled:grading"  # I6：评分期间取消同样落账后原样上抛
            self._fill_cancelled_grading_refs(row, trajectory_id)  # R3：取消时 manager 已落盘的日志/sidecar 引用
            self._append(row)
            raise
        except BaselineIntegrityError as exc:
            row["stage_error"] = f"baseline_integrity:{getattr(exc, 'reason_code', '')}:{exc}"
            self._append(row)
            raise  # run-halt 通道：契约矛盾不继续下一题
        except Exception as exc:  # noqa: BLE001 - 记录首个失败原因后继续下一题
            row["stage_error"] = f"grade_exception:{type(exc).__name__}:{_tail(str(exc))}"
            self._append(row)
            return row
        self._fill_from_report(row, report)
        self._append(row)
        return row

    async def _ensure_image(self, image: str) -> dict[str, Any]:
        """镜像预拉取（独立预算）：已在本机则 0 秒；否则 `docker pull`，超时/失败记 error（不评分）。"""
        started = time.monotonic()
        ins = await self.ctx.docker("image", "inspect", image)
        if ins.exit_code == 0:
            return {"pulled": False, "seconds": round(time.monotonic() - started, 3)}
        pull = await self.ctx.docker("pull", image)  # 整体（inspect + pull）由调用方用镜像预算包住（R4）
        if pull.exit_code != 0:
            return {"pulled": False, "seconds": round(time.monotonic() - started, 3), "error": "pull_failed:" + _tail(pull.stderr, 200)}
        return {"pulled": True, "seconds": round(time.monotonic() - started, 3)}

    def _fill_cancelled_grading_refs(self, row: dict[str, Any], trajectory_id: str) -> None:
        for rec in reversed(getattr(self.manager, "container_records", ())):
            if rec.trajectory_id != trajectory_id:
                continue
            ref = getattr(rec, "cancelled_eval_log_ref", None)
            if ref is not None and self.manager.config.eval_log_dir is not None:
                log_dir = Path(self.manager.config.eval_log_dir)
                # 接线页 §14.2 余项：候选段已完整结束、后观测期间才被取消时日志是完整的，partial 按候选事实记
                partial = bool((rec.candidate_facts or {}).get("log_partial", True))
                row["log"] = {"path": str(log_dir / f"{ref.ref_id}.eval.log"), "sha256": ref.sha256, "partial": partial}
                side = log_dir / f"{ref.ref_id}.diagnostics.json"
                row["diagnostics_ref"] = str(side) if side.exists() else None
            if rec.candidate_facts is not None:
                row["install"] = rec.candidate_facts
            break

    def _fill_from_report(self, row: dict[str, Any], report: Any) -> None:
        row["report"] = {
            "report_id": report.report_id, "outcome": report.outcome, "failure_category": report.failure_category,
            "reward": report.reward, "f2p_pass": report.f2p_pass_count, "f2p_total": report.f2p_total_count,
            "p2p_fail": report.p2p_fail_count, "p2p_total": report.p2p_total_count, "grader_version": report.grader_version,
            "infra_failure_detail": report.infra_failure_detail,
            "execution_failure_stage": report.execution_failure_stage,
            "execution_failure_evidence": list(report.execution_failure_evidence),
            "grading_semantics": report.grading_semantics,
        }
        row["regrade_total"] = getattr(self.manager, "regrade_total", None)
        timing = self.manager.take_grader_phase_timing(report.timings.record_id) if report.timings is not None else None
        row["phases"] = dict(timing.segments) if timing is not None else None
        peak = report.timings.container_peak_memory_mb if report.timings is not None else None
        row["resource"] = {"mem_peak_mb": peak, "mem_peak_unavailable_or_zero": (peak is None or peak == 0.0)}
        diag = None
        for rec in reversed(self.manager.container_records):
            if rec.trajectory_id == report.trajectory_id and rec.diagnostics is not None:
                diag = rec.diagnostics
                break
        if diag is not None:
            row["install"] = diag.get("candidate")
            cand = diag.get("candidate") or {}
            row["test"] = {"rc": cand.get("test_rc"), "seconds": cand.get("test_seconds")} if cand else None
            row["verdict_diagnostics"] = diag.get("verdict")
            row["observations"] = diag.get("observations")
            row["runner_integrity_changed"] = diag.get("runner_integrity_changed")
            row["candidate_test_like_paths"] = diag.get("candidate_test_like_paths")
            row["candidate_touched_conftest_or_fixture"] = diag.get("candidate_touched_conftest_or_fixture")
            verdict = diag.get("verdict") or {}
            row["reference_missing_count"] = len(verdict.get("reference_missing") or []) if verdict else None
            row["execution_failure_decision"] = diag.get("execution_failure_decision")
            row["resource_facts"] = diag.get("resource_facts")
        if report.eval_log_ref is not None and self.manager.config.eval_log_dir is not None:
            log_dir = Path(self.manager.config.eval_log_dir)
            row["log"] = {
                "path": str(log_dir / f"{report.eval_log_ref.ref_id}.eval.log"), "sha256": report.eval_log_ref.sha256,
                "partial": bool((diag or {}).get("candidate", {}) and diag["candidate"].get("log_partial")),
            }
            side = log_dir / f"{report.eval_log_ref.ref_id}.diagnostics.json"
            row["diagnostics_ref"] = str(side) if side.exists() else None

    def _persist_candidate_artifacts(self, task_id: str, attempt: int, nonce: str, candidate: CandidateInput, stage: _CandidateStage) -> None:
        out = self.ctx.artifacts_dir / _slug(task_id, 60) / f"a{attempt}-{nonce}"
        out.mkdir(parents=True, exist_ok=True)
        if candidate.patch_text is not None:
            (out / "candidate.patch").write_text(candidate.patch_text, encoding="utf-8")
        for name, obj in (("baseline_manifest", stage.baseline), ("frozen_patch", stage.artifact),
                          ("classification", stage.classification), ("projection", stage.projection)):
            if obj is not None:
                (out / f"{name}.json").write_text(obj.model_dump_json(indent=1), encoding="utf-8")
        (out / "stage.json").write_text(json.dumps({
            "head": stage.head, "apply_method": stage.apply_method, "apply_stderr_tail": stage.apply_stderr_tail,
            "last_stage": stage.last_stage, "stage_error": stage.stage_error,
        }, ensure_ascii=False, indent=1), encoding="utf-8")

    def _append(self, row: dict[str, Any]) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n")


def _policy_of(g: GraderSandboxProfile) -> dict[str, Any]:
    return {
        "profile_id": g.profile_id, "grader_profile_digest": g.digest(), "network": "deny_all",
        "user": g.candidate_exec_user, "uid": g.candidate_exec_uid, "cpus": g.cpus, "memory_bytes": g.memory_bytes,
        "shm_bytes": g.shm_size_bytes, "tmpfs_bytes": g.tmp_tmpfs_bytes, "pids_limit": g.pids_limit,
        "candidate_writable_prefixes": list(g.candidate_writable_prefixes),
    }


def candidate_from_spec(spec: str, *, instance_id: str) -> CandidateInput:
    """CLI 候选说明：noop | patch:<file> | gold-dir:<dir>（<iid>.gold.patch）| patch-dir:<dir>（<iid>.diff）。"""
    if spec == "noop":
        return CandidateInput(kind="noop", origin="noop")
    kind, _, arg = spec.partition(":")
    if kind == "patch":
        return CandidateInput(kind="cc", origin=arg, patch_text=Path(arg).read_text(encoding="utf-8"))
    if kind == "gold-dir":
        p = Path(arg) / f"{instance_id}.gold.patch"
        return CandidateInput(kind="gold", origin=str(p), patch_text=p.read_text(encoding="utf-8"))
    if kind == "patch-dir":
        p = Path(arg) / f"{instance_id}.diff"
        return CandidateInput(kind="cc", origin=str(p), patch_text=p.read_text(encoding="utf-8"))
    raise ValueError(f"未知候选说明 {spec!r}")


__all__ = [
    "CandidateInput", "DerivedImage", "DockerExecWorkspace", "ReplayBudgets", "ReplayContext", "ReplayGrader",
    "ReplayHaltError", "ReplayStageError", "candidate_from_spec", "export_gold_candidates", "load_context",
    "prepare_for_replay",
]


def load_env_qualifications(ledger_paths: Sequence[Path | str]) -> dict[str, EnvQualification]:
    """P-A：从重放账本构造每题的环境资格记录。资格行 = gold/noop 候选、评分成功（resolved 或 tests_failed）、
    参考清单缺席数 0、且账本带 image_identity / scripts_digest（旧账本没有这两列 → 不算资格）。
    同题多行取最后一行；manager 评分时再核对镜像身份与脚本摘要，不符视同缺席。"""

    out: dict[str, EnvQualification] = {}
    for raw in ledger_paths:
        path = Path(raw)
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            rep = row.get("report") or {}
            cand = row.get("candidate") or {}
            if cand.get("kind") not in ("gold", "noop"):
                continue
            if rep.get("outcome") not in ("resolved", "unresolved") or rep.get("failure_category") not in (None, "tests_failed"):
                continue
            if row.get("reference_missing_count") != 0 or not row.get("image_identity") or not row.get("scripts_digest"):
                continue
            out[row["task_id"]] = EnvQualification(
                image_identity=row["image_identity"], scripts_digest=row["scripts_digest"], reference_missing_count=0,
                source=f"{path.name}:{rep.get('report_id')}", qualified_at_utc=str(row.get("started_at_utc")),
                install_rc_last_command=(row.get("install") or {}).get("install_rc_last_command"),
            )
    return out
