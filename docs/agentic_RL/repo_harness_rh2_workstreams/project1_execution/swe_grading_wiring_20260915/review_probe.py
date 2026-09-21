"""接线计划的四类窄 CPU 反例；不运行容器、安装、评分作业或训练。"""

from __future__ import annotations

import base64
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "rh2" / "src"))

from repoharness2.contracts.baseline_manifest import (  # noqa: E402
    BASELINE_MANIFEST_POLICY_V1,
    BaselineWorkspaceManifestV1,
    compute_baseline_manifest_digest,
    compute_policy_digest,
)
from repoharness2.contracts.frozen_patch import FrozenPatchArtifactV1, PatchEntry  # noqa: E402
from repoharness2.contracts.scoring_projection import classify_frozen_patch  # noqa: E402
from repoharness2.grading.manager import HygieneRules  # noqa: E402
from repoharness2.grading.trusted_projection import build_trusted_scoring_projection  # noqa: E402
from swebench.harness.grading import get_eval_tests_report, get_resolution_status  # noqa: E402


def projection_cases() -> list[dict]:
    baseline = BaselineWorkspaceManifestV1(
        task_id="review", workdir="/testbed",
        public_bundle_digest="sha256:" + "e" * 64,
        runtime_image_digest="sha256:" + "1" * 64,
        materialized_head="a" * 40, task_base_commit="b" * 40,
        policy=BASELINE_MANIFEST_POLICY_V1,
        policy_digest=compute_policy_digest(BASELINE_MANIFEST_POLICY_V1), entries=(),
    )
    results = []
    for target in (b"../target.py", b"../../outside", b"../.git/config"):
        entry = PatchEntry(
            path="src/link", operation="add", object_type="symlink", mode="120000",
            content_b64=base64.b64encode(target).decode(),
            content_digest="sha256:" + hashlib.sha256(target).hexdigest(),
        )
        artifact = FrozenPatchArtifactV1(
            task_id=baseline.task_id, rollout_execution_id="review-exec",
            physical_attempt_id="review-attempt",
            baseline_manifest_digest=compute_baseline_manifest_digest(baseline),
            public_bundle_digest=baseline.public_bundle_digest,
            runtime_image_digest=baseline.runtime_image_digest,
            materialized_head=baseline.materialized_head,
            entries=(entry,), excluded_pathset_changed=False,
        )
        report, classified_projection = classify_frozen_patch(artifact, baseline)
        # 故意省略调用前置条件，复现计划步骤直接调用 builder 的后果。
        direct_projection, _ = build_trusted_scoring_projection(artifact, HygieneRules())
        results.append({
            "target": target.decode(), "classifier_verdict": report.verdict,
            "classifier_reasons": report.reason_codes,
            "classifier_has_projection": classified_projection is not None,
            "direct_builder_included_paths": direct_projection.included_entry_paths,
        })
    return results


def status_cases() -> list[dict]:
    cases = {
        "missing": {}, "skipped": {"f": "SKIPPED", "p": "SKIPPED"},
        "passed": {"f": "PASSED", "p": "PASSED"},
        "failed": {"f": "FAILED", "p": "PASSED"},
    }
    results = []
    for name, statuses in cases.items():
        report = get_eval_tests_report(statuses, {"FAIL_TO_PASS": ["f"], "PASS_TO_PASS": ["p"]})
        results.append({"case": name, "report": report, "resolution": get_resolution_status(report)})
    return results


def untracked_patch_case() -> dict:
    # 独立临时仓库：不修改工作区 Git 状态或用户 Git 配置。
    with tempfile.TemporaryDirectory(prefix="rh2-wiring-review-") as directory:
        def git(*args: str, patch: str | None = None) -> str:
            return subprocess.run(
                ["git", *args], cwd=directory, input=patch, text=True,
                capture_output=True, check=True,
            ).stdout

        git("init", "-q")
        Path(directory, "existing.py").write_text("old = 1\n")
        git("add", "existing.py")
        git("-c", "user.name=Review", "-c", "user.email=review@example.invalid", "commit", "-qm", "baseline")
        git("apply", "-", patch=(
            "diff --git a/new.py b/new.py\nnew file mode 100644\n"
            "--- /dev/null\n+++ b/new.py\n@@ -0,0 +1 @@\n+answer = 42\n"
        ))
        return {
            "new_file_exists": Path(directory, "new.py").is_file(),
            "git_diff_head_paths": git("diff", "--name-only", "HEAD").splitlines(),
            "untracked_paths": git("ls-files", "--others", "--exclude-standard").splitlines(),
        }


if __name__ == "__main__":
    shell = subprocess.run(["bash", "-c", "set -o pipefail; false; true"], check=False)
    print(json.dumps({
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "swebench_version": importlib.metadata.version("swebench"),
        "projection": projection_cases(), "report_function_only": status_cases(),
        "composite_shell": {"command": "set -o pipefail; false; true", "final_rc": shell.returncode},
        "git_diff_is_not_workspace_census": untracked_patch_case(),
        "scope": "真实纯函数与 shell 语义；不是完整 manager、真实安装或新 driver 的验收。",
    }, ensure_ascii=False, indent=2))
