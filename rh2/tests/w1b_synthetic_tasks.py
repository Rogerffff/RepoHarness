"""W1b 第一集成切片测试共用的合成任务夹具（不是测试模块，无 test_ 前缀）。

与 tests/test_w2a_trusted_views.py 的合成 IngestResult 同形：两题 getmoto/moto。
内容锚（泄漏断言逐字扫描的依据）：
- golden 内容 ``goldfix(<iid>)`` 只存在于 validation 面（golden_patch）；
- 判定测试内容 ``judge(<iid>)`` 只存在于 grading 面（test_patch / FAIL_TO_PASS）。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from repoharness2.envpack.ingest_swegym_lite import IngestResult, build_task
from repoharness2.envpack.prepared_tasks import HOST_GRADING_FILE, PROMPTS_FILE, PreparedTasksManifest, prepare_tasks
from repoharness2.envpack.training_view import TrustedTaskController

IMG_DIG = "sha256:" + "b" * 64
BASE_COMMIT = "a" * 40  # 与 test_w1a_formal_chain 的 fake docker 血缘探针应答同值
D = "sha256:" + "a" * 64
IIDS: tuple[str, ...] = ("getmoto__moto-1", "getmoto__moto-2")
TID1 = "swe_gym_lite::getmoto__moto-1"
TID2 = "swe_gym_lite::getmoto__moto-2"


def golden_content(iid: str) -> str:
    return f"goldfix({iid})"


def judge_content(iid: str) -> str:
    return f"judge({iid})"


def make_row(iid: str, statement: str | None = None) -> dict:
    return {
        "instance_id": iid,
        "repo": "getmoto/moto",
        "base_commit": BASE_COMMIT,
        "version": "4.1",
        "created_at": "2023-01-01T00:00:00Z",
        "problem_statement": statement or f"Resolve the moto bug ({iid}).",
        "hints_text": "maintainer said: apply this diff ...",
        "patch": f"diff --git a/m.py b/m.py\n-bug\n+{golden_content(iid)}\n",
        "test_patch": f"diff --git a/t.py b/t.py\n+{judge_content(iid)}\n",
        "FAIL_TO_PASS": [f"t.py::judge_{iid[-1]}"],
        "PASS_TO_PASS": ["t.py::test_ok"],
    }


def make_image_entry(iid: str) -> dict:
    return {
        "instance_id": iid,
        "source_image_ref": f"xingyaoww/sweb.eval.x86_64.{iid.replace('__', '_s_').lower()}:latest",
        "resolved_manifest_digest": IMG_DIG,
    }


def make_result(iids: tuple[str, ...] = IIDS) -> IngestResult:
    result = IngestResult()
    for iid in iids:
        public, grading, validation, package = build_task(
            make_row(iid), make_image_entry(iid), raw_archive_sha256=D, image_manifest_keyed_sha256=D
        )
        result.public_bundles.append(public)
        result.grading_bundles.append(grading)
        result.validation_bundles.append(validation)
        result.packages.append(package)
    return result


def make_controller(iids: tuple[str, ...] = IIDS) -> TrustedTaskController:
    return TrustedTaskController.build_for_tests_from_ingest_result(make_result(iids))


@dataclass
class PreparedFixture:
    controller: TrustedTaskController
    prepared_dir: Path
    private_dir: Path
    manifest: PreparedTasksManifest

    @property
    def prompts_path(self) -> Path:
        return self.prepared_dir / PROMPTS_FILE

    @property
    def host_path(self) -> Path:
        return self.private_dir / HOST_GRADING_FILE


def prepare_synthetic(root: Path, iids: tuple[str, ...] = IIDS) -> PreparedFixture:
    """在 root 下跑一次 trusted-prep（合成 controller）：root/prepared 公开、root/private 私有。"""

    controller = make_controller(iids)
    prepared_dir = root / "prepared"
    private_dir = root / "private"
    manifest = prepare_tasks(controller, out_dir=prepared_dir, private_dir=private_dir)
    return PreparedFixture(controller=controller, prepared_dir=prepared_dir, private_dir=private_dir, manifest=manifest)
