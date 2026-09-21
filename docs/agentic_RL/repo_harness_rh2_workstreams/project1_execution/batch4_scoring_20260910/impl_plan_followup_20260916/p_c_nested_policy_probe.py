"""计划验收提示：只兼容 policy digest 不等于整个 manifest digest 兼容。

仅在当前进程用本地子类和临时函数替身模拟拟议新增字段；不改生产源码。
从仓库根以 PYTHONPATH=rh2/src rh2/.venv/bin/python -B <本文件> 运行。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from repoharness2.contracts import baseline_manifest as mod


class PlannedPolicy(mod.BaselineManifestPolicy):
    regenerable_cache_dirs: tuple[str, ...] = ()


class PlannedManifest(mod.BaselineWorkspaceManifestV1):
    policy: PlannedPolicy


def policy_only_canonical(policy: mod.BaselineManifestPolicy) -> str:
    data = {
        "policy_version": policy.policy_version,
        "excluded_namespaces": list(policy.excluded_namespaces),
    }
    encoded = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode()).hexdigest()


def main() -> None:
    old_policy = mod.BASELINE_MANIFEST_POLICY_V1
    old_manifest = mod.BaselineWorkspaceManifestV1(
        task_id="plan-probe",
        workdir="/testbed",
        public_bundle_digest="sha256:" + "1" * 64,
        runtime_image_digest="sha256:" + "2" * 64,
        materialized_head="a" * 40,
        task_base_commit="b" * 40,
        policy=old_policy,
        policy_digest=mod.compute_policy_digest(old_policy),
        entries=(),
    )
    old_digest = mod.compute_baseline_manifest_digest(old_manifest)
    with patch.object(mod, "compute_policy_digest", policy_only_canonical):
        loaded = PlannedManifest.model_validate_json(old_manifest.model_dump_json())
        new_digest = mod.compute_baseline_manifest_digest(loaded)
    result = {
        "scope": "拟议字段的局部模拟，不是对尚未实施的 v2 宣称已发生回归",
        "old_json_loads": True,
        "policy_digest_preserved": loaded.policy_digest == old_manifest.policy_digest,
        "manifest_digest_changed_by_nested_default": new_digest != old_digest,
        "old_manifest_digest": old_digest,
        "new_manifest_digest": new_digest,
    }
    assert result["policy_digest_preserved"]
    assert result["manifest_digest_changed_by_nested_default"]
    Path(__file__).with_name("p_c_nested_policy_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
