"""仅用本地子类模拟未来计划新增字段，不修改当前 schema 或历史证据。"""

from repoharness2.contracts.baseline_manifest import (
    BASELINE_MANIFEST_POLICY_V1,
    BaselineManifestPolicy,
    BaselineWorkspaceManifestV1,
    compute_baseline_manifest_digest,
    compute_policy_digest,
)
class PlannedPolicy(BaselineManifestPolicy):
    regenerable_cache_patterns: tuple[str, ...] = ()
oldp = BASELINE_MANIFEST_POLICY_V1
newp = PlannedPolicy.model_validate(oldp.model_dump())
print('v1_policy_digest_changed_by_empty_default', compute_policy_digest(oldp) != compute_policy_digest(newp))
assert compute_policy_digest(oldp) != compute_policy_digest(newp)
ident = dict(task_id='t', workdir='/testbed', public_bundle_digest='sha256:'+'e'*64, runtime_image_digest='sha256:'+'1'*64, materialized_head='a'*40, task_base_commit='b'*40, policy=oldp, policy_digest=compute_policy_digest(oldp), entries=())
oldm = BaselineWorkspaceManifestV1(**ident)
class PlannedManifest(BaselineWorkspaceManifestV1):
    omitted_cache_count: int = 0
newm0 = PlannedManifest(**ident)
newm1 = PlannedManifest(**ident, omitted_cache_count=1)
print('v1_manifest_digest_changed_by_zero_default', compute_baseline_manifest_digest(oldm) != compute_baseline_manifest_digest(newm0))
print('cache_count_changes_manifest_identity', compute_baseline_manifest_digest(newm0) != compute_baseline_manifest_digest(newm1))
assert compute_baseline_manifest_digest(oldm) != compute_baseline_manifest_digest(newm0)
assert compute_baseline_manifest_digest(newm0) != compute_baseline_manifest_digest(newm1)
