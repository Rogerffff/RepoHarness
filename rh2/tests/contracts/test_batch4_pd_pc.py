"""第四组 P-D（文件变目录）与 P-C（可再生缓存省略）的契约/纯函数验收（2026-09-16）。

P-D：artifact 契约只放开"祖先 = 删除的普通文件、后代 = 新增"一种父子形状；分类器要求基线祖先确为普通文件；
投影检出"必要祖先删除被控制面排除"。P-C：政策 v2 只剪两类目录且按类型；canonical digest 让 v1 政策与真实
e1 落盘的 v1 manifest 的 digest 不变；manifest 与分类器都拒绝落在缓存目录内的路径。
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest

from repoharness2.adapters.slime.baseline_census import (
    BASELINE_MANIFEST_POLICY_V1,
    baseline_policy_for_task_id,
    build_census_script,
    parse_census_omitted_counts,
    parse_census_output,
)
from repoharness2.contracts.baseline_manifest import (
    BASELINE_MANIFEST_POLICY_V2,
    BaselineManifestPolicy,
    BaselineWorkspaceManifestV1,
    compute_baseline_manifest_digest,
    compute_policy_digest,
    is_regenerable_cache_path,
)
from repoharness2.contracts.frozen_patch import FrozenPatchArtifactV1, PatchEntry
from repoharness2.contracts.scoring_projection import ProjectionContractError, classify_frozen_patch
from repoharness2.grading.manager import HygieneRules
from repoharness2.grading.trusted_projection import build_trusted_scoring_projection, split_trusted_scoring_projection

DATA = Path(__file__).resolve().parent / "data"
IDENT = dict(task_id="t1", workdir="/testbed", public_bundle_digest="sha256:" + "e" * 64,
             runtime_image_digest="sha256:" + "1" * 64, materialized_head="a" * 40, task_base_commit="b" * 40)


def _b64(data: bytes) -> tuple[str, str]:
    return base64.b64encode(data).decode(), "sha256:" + hashlib.sha256(data).hexdigest()


def _add(path: str, data: bytes = b"x\n") -> PatchEntry:
    b, d = _b64(data)
    return PatchEntry(path=path, operation="add", object_type="regular", mode="100644", content_b64=b, content_digest=d)


def _delete(path: str, object_type: str = "regular") -> PatchEntry:
    return PatchEntry(path=path, operation="delete", object_type=object_type)


def _census(text: str, policy=BASELINE_MANIFEST_POLICY_V1) -> BaselineWorkspaceManifestV1:
    return parse_census_output(text, **IDENT, policy=policy)


def _artifact(entries, baseline: BaselineWorkspaceManifestV1) -> FrozenPatchArtifactV1:
    return FrozenPatchArtifactV1(
        task_id="t1", rollout_execution_id="exec_1", physical_attempt_id="exec_1#p1-aaaa",
        baseline_manifest_digest=compute_baseline_manifest_digest(baseline),
        public_bundle_digest=IDENT["public_bundle_digest"], runtime_image_digest=IDENT["runtime_image_digest"],
        materialized_head=IDENT["materialized_head"], entries=tuple(sorted(entries, key=lambda e: e.path)),
        excluded_pathset_changed=False,
    )


# ---------------------------------------------------------------------------- P-D 契约

def test_pd_contract_allows_only_regular_file_delete_plus_child_adds():
    ok = FrozenPatchArtifactV1(
        task_id="t1", rollout_execution_id="e", physical_attempt_id="e#p1-aaaa",
        baseline_manifest_digest="sha256:" + "b" * 64, public_bundle_digest="sha256:" + "e" * 64,
        runtime_image_digest="sha256:" + "1" * 64, materialized_head="a" * 40,
        entries=(_delete("config"), _add("config/default.json"), _add("config/sub/x.json")), excluded_pathset_changed=False,
    )
    assert [e.path for e in ok.entries] == ["config", "config/default.json", "config/sub/x.json"]
    for entries, why in [
        ((_add("config"), _add("config/default.json")), "祖先是新增"),
        ((_delete("config", "symlink"), _add("config/default.json")), "祖先是软链删除"),
        ((_delete("config"), _delete("config/default.json")), "后代是删除（目录反向变文件）"),
        ((_add("config"), _delete("config/default.json")), "目录变文件"),
    ]:
        with pytest.raises(ValueError, match="父子前缀冲突"):
            FrozenPatchArtifactV1(
                task_id="t1", rollout_execution_id="e", physical_attempt_id="e#p1-aaaa",
                baseline_manifest_digest="sha256:" + "b" * 64, public_bundle_digest="sha256:" + "e" * 64,
                runtime_image_digest="sha256:" + "1" * 64, materialized_head="a" * 40,
                entries=tuple(sorted(entries, key=lambda e: e.path)), excluded_pathset_changed=False,
            )


def test_pd_classifier_requires_regular_ancestor_in_baseline():
    sha = hashlib.sha256(b"a=1\n").hexdigest()
    base_regular = _census("regular\t100644\t" + sha + "\tconfig\nregular\t100644\t" + "1" * 64 + "\tkeep.py\n")
    report, projection = classify_frozen_patch(_artifact([_delete("config"), _add("config/default.json")], base_regular), base_regular)
    assert report.verdict == "projectable" and projection is not None
    base_symlink = _census("symlink\t120000\t" + sha + "\tconfig\nregular\t100644\t" + "1" * 64 + "\tkeep.py\n")
    art = _artifact([_delete("config", "regular"), _add("config/default.json")], base_symlink)
    report, projection = classify_frozen_patch(art, base_symlink)
    assert report.verdict == "unsafe_artifact" and projection is None
    assert "file_to_dir_ancestor_not_regular:config" in report.reason_codes


def test_pd_projection_reports_excluded_ancestor_delete():
    rules_official_config = HygieneRules(test_files=("config",), test_globs=(), forbidden_globs=())
    split = split_trusted_scoring_projection([_delete("config"), _add("config/default.json")], rules_official_config)
    assert split.candidate_paths == ("config/default.json",) and split.ignored_paths == ("config",)
    assert split.unsupported_shape_reasons == ("unsupported_delta_shape:ancestor_delete_excluded_by_control_plane:config->config/default.json",)
    assert any(r.startswith("unsupported_delta_shape") for r in split.evidence_refs())
    assert split.to_record()["unsupported_shape_reasons"]
    plain = HygieneRules(test_files=("tests/test_x.py",), test_globs=(), forbidden_globs=())
    split2 = split_trusted_scoring_projection([_delete("config"), _add("config/default.json")], plain)
    assert split2.unsupported_shape_reasons == () and split2.candidate_paths == ("config", "config/default.json")
    art = _artifact([_delete("config"), _add("config/default.json")], _census("regular\t100644\t" + "0" * 64 + "\tconfig\n"))
    projection, split3 = build_trusted_scoring_projection(art, plain)
    assert projection.included_entry_paths == ("config", "config/default.json") and split3.unsupported_shape_reasons == ()


# ---------------------------------------------------------------------------- P-C 政策与身份

def test_pc_policy_v2_and_canonical_digests():
    v1 = BASELINE_MANIFEST_POLICY_V1
    assert v1.regenerable_cache_dirs == () and "regenerable_cache_dirs" not in v1.canonical_dump()
    assert compute_policy_digest(v1) == compute_policy_digest(BaselineManifestPolicy(policy_version="baseline_policy_v1", excluded_namespaces=(".git/", ".harness/")))
    v2 = BASELINE_MANIFEST_POLICY_V2
    assert v2.regenerable_cache_dirs == (".pytest_cache", "__pycache__") and compute_policy_digest(v2) != compute_policy_digest(v1)
    assert "regenerable_cache_dirs" in v2.canonical_dump()
    for bad in ("a/b", ".", "..", ""):
        with pytest.raises(ValueError):
            BaselineManifestPolicy(policy_version="x", excluded_namespaces=(".git/",), regenerable_cache_dirs=(bad,))
    with pytest.raises(ValueError, match="排序且唯一"):
        BaselineManifestPolicy(policy_version="x", excluded_namespaces=(".git/",), regenerable_cache_dirs=("b", "a"))
    assert is_regenerable_cache_path(v2, "src/__pycache__/x.pyc") and not is_regenerable_cache_path(v2, "tests/__pycache__")
    assert not is_regenerable_cache_path(v1, "src/__pycache__/x.pyc")
    assert baseline_policy_for_task_id("swe_gym_lite::x") is v2 and baseline_policy_for_task_id("other::x") is v1


def test_pc_real_e1_v1_manifest_loads_and_digest_unchanged():
    raw = json.loads((DATA / "e1_dvc5822_baseline_manifest_v1.json").read_text())
    expect = json.loads((DATA / "e1_dvc5822_baseline_manifest_v1.expect.json").read_text())
    assert "regenerable_cache_dirs" not in raw["policy"]  # 真实 v1 落盘形态
    manifest = BaselineWorkspaceManifestV1.model_validate(raw)  # 加载时重算 policy_digest，必须仍相符
    assert manifest.policy.regenerable_cache_dirs == ()
    assert compute_baseline_manifest_digest(manifest) == expect["baseline_manifest_digest"]
    # 重序列化后再加载仍是同一身份
    again = BaselineWorkspaceManifestV1.model_validate(json.loads(manifest.model_dump_json()))
    assert compute_baseline_manifest_digest(again) == expect["baseline_manifest_digest"]


def test_pc_manifest_and_classifier_reject_cache_paths_under_v2():
    with pytest.raises(ValueError, match="可再生缓存目录"):
        _census("regular\t100644\t" + "0" * 64 + "\tsrc/__pycache__/x.pyc\n", policy=BASELINE_MANIFEST_POLICY_V2)
    base = _census("regular\t100644\t" + "0" * 64 + "\tsrc/a.py\n", policy=BASELINE_MANIFEST_POLICY_V2)
    with pytest.raises(ProjectionContractError, match="cache_entry_present_despite_policy"):
        classify_frozen_patch(_artifact([_add("src/__pycache__/a.cpython-312.pyc")], base), base)
    # 末段同名普通文件不是缓存目录内部路径：合法 entry
    report, _ = classify_frozen_patch(_artifact([_add("tests/__pycache__")], base), base)
    assert report.verdict == "projectable"


def test_pc_census_script_prunes_directories_by_type_and_counts():
    script = build_census_script("/testbed", BASELINE_MANIFEST_POLICY_V2)
    assert "\\( -type d \\( -name .pytest_cache -o -name __pycache__ \\) -prune \\) -o" in script
    assert "CACHE_OMITTED_DIRS" in script and "CACHE_OMITTED_FILES" in script
    assert "CACHE_OMITTED" not in build_census_script("/testbed", BASELINE_MANIFEST_POLICY_V1)
    text = "regular\t100644\t" + "0" * 64 + "\tsrc/a.py\nCACHE_OMITTED_DIRS\t2\nCACHE_OMITTED_FILES\t7\n"
    manifest = _census(text, policy=BASELINE_MANIFEST_POLICY_V2)
    assert [e.path for e in manifest.entries] == ["src/a.py"]
    assert parse_census_omitted_counts(text) == {"dirs": 2, "files": 7} and parse_census_omitted_counts("") == {}
