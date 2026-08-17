"""B1 验收：BaselineWorkspaceManifestV1 契约 + census 生成器确定性。

覆盖（05 计划 5a 节 B1 验收项）：契约往返/lstat 语义字段/policy digest
互检/路径 canonical 与父子冲突（大小写共存合法——codex 三轮口径）/
排除区不进 entries + 独立 census digest/解析器确定性与 fail-closed。
"""

from __future__ import annotations

import pytest

from repoharness2.adapters.slime.baseline_census import (
    BaselineCensusError,
    build_census_script,
    parse_census_output,
)
from repoharness2.contracts.baseline_manifest import (
    BASELINE_MANIFEST_POLICY_V1,
    BaselineEntry,
    BaselineWorkspaceManifestV1,
    compute_baseline_manifest_digest,
    compute_policy_digest,
)

_IDENT = dict(
    task_id="t1", workdir="/testbed",
    public_bundle_digest="sha256:" + "e" * 64,
    runtime_image_digest="sha256:" + "1" * 64,
    materialized_head="a" * 40, task_base_commit="b" * 40,
)


def _mk(entries, **over):
    base = dict(
        **_IDENT,
        policy=BASELINE_MANIFEST_POLICY_V1,
        policy_digest=compute_policy_digest(BASELINE_MANIFEST_POLICY_V1),
        entries=tuple(entries),
    )
    base.update(over)
    return BaselineWorkspaceManifestV1(**base)


def _reg(path, sha="c" * 64, mode="100644"):
    return BaselineEntry(path=path, object_type="regular", mode=mode,
                         content_digest=f"sha256:{sha}")


def test_round_trip_and_digest_stability():
    m = _mk([_reg("a.py"), _reg("dir/b.py", mode="100755")])
    d1 = compute_baseline_manifest_digest(m)
    m2 = BaselineWorkspaceManifestV1.model_validate(m.model_dump(mode="json"))
    assert compute_baseline_manifest_digest(m2) == d1  # 读写双方重算一致
    # digest 对内容敏感
    m3 = _mk([_reg("a.py", sha="d" * 64), _reg("dir/b.py", mode="100755")])
    assert compute_baseline_manifest_digest(m3) != d1


def test_policy_digest_versioned():
    from repoharness2.contracts.baseline_manifest import BaselineManifestPolicy

    p2 = BaselineManifestPolicy(policy_version="v2", excluded_namespaces=(".git/",))
    assert compute_policy_digest(p2) != compute_policy_digest(BASELINE_MANIFEST_POLICY_V1)
    with pytest.raises(ValueError, match="policy_digest"):
        _mk([_reg("a.py")], policy_digest="sha256:" + "0" * 64)


def test_entry_lstat_field_requirements():
    with pytest.raises(ValueError, match="content_digest"):
        BaselineEntry(path="a", object_type="regular", mode="100644")
    with pytest.raises(ValueError, match="symlink_target_digest"):
        BaselineEntry(path="l", object_type="symlink", mode="120000")
    with pytest.raises(ValueError, match="120000"):
        BaselineEntry(path="l", object_type="symlink", mode="100644",
                      symlink_target_digest="sha256:" + "a" * 64)


def test_path_rules_case_coexist_allowed_prefix_conflict_rejected():
    # codex 三轮：Linux case-sensitive——大小写共存合法
    _mk([_reg("Foo.py"), _reg("foo.py")])
    for bad in ["/abs", "a/../b", "a//b", "."]:
        with pytest.raises(ValueError):
            _mk([_reg(bad)])
    with pytest.raises(ValueError, match="父子前缀冲突"):
        _mk([_reg("a"), _reg("a/b")])
    with pytest.raises(ValueError, match="排序"):
        BaselineWorkspaceManifestV1(**{
            **_IDENT,
            "policy": BASELINE_MANIFEST_POLICY_V1,
            "policy_digest": compute_policy_digest(BASELINE_MANIFEST_POLICY_V1),
            "entries": (_reg("b"), _reg("a")),
        })


def test_excluded_namespace_entries_rejected():
    with pytest.raises(ValueError, match="排除 namespace"):
        _mk([_reg(".harness/trajectory.jsonl")])


def test_parse_census_deterministic_and_excl():
    text = (
        "regular\t100644\t" + "1" * 64 + "\tsrc/a.py\n"
        "symlink\t120000\t" + "2" * 64 + "\tlink\n"
        "EXCL\t.harness/trajectory.jsonl\n"
    )
    m = parse_census_output(text, **_IDENT, policy=BASELINE_MANIFEST_POLICY_V1)
    assert [e.path for e in m.entries] == ["link", "src/a.py"]  # 解析后重排序
    assert m.entries[0].object_type == "symlink"
    assert m.excluded_census_digest is not None  # 排除 ≠ 消失
    m2 = parse_census_output(text, **_IDENT, policy=BASELINE_MANIFEST_POLICY_V1)
    assert compute_baseline_manifest_digest(m) == compute_baseline_manifest_digest(m2)


def test_parse_unsupported_object_fail_closed():
    with pytest.raises(BaselineCensusError, match="unsupported_object"):
        parse_census_output(
            "UNSUPPORTED\tdev/fifo\n", **_IDENT, policy=BASELINE_MANIFEST_POLICY_V1
        )
    with pytest.raises(BaselineCensusError, match="census_parse_error"):
        parse_census_output("garbage line\n", **_IDENT, policy=BASELINE_MANIFEST_POLICY_V1)


def test_lineage_fields_typed_fatal():
    """B1 closure P1-1：非法 digest/tag/符号引用一律构造即拒。"""

    with pytest.raises(ValueError):
        _mk([_reg("a")], runtime_image_digest="local:mutable-tag")
    with pytest.raises(ValueError):
        _mk([_reg("a")], public_bundle_digest="not-a-digest")
    with pytest.raises(ValueError):
        _mk([_reg("a")], materialized_head="HEAD")
    with pytest.raises(ValueError):
        _mk([_reg("a", sha="X" * 64)])  # 非 hex content digest
    # environment_package_digest 未接通 = None 合法（不伪造）
    assert _mk([_reg("a")]).environment_package_digest is None


def test_real_tree_census_end_to_end(tmp_path):
    """B1 closure P1-3（计划原定验收）：真实临时树执行 census 脚本 →
    parse → digest：644/755/symlink 不跟随/.git .harness 排除/重复执行
    digest 一致。"""

    import stat
    import subprocess

    root = tmp_path / "ws"
    (root / "src").mkdir(parents=True)
    (root / "src" / "a.py").write_text("print(1)\n")
    exe = root / "run.sh"
    exe.write_text("#!/bin/sh\n")
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    (root / "link").symlink_to("src/a.py")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("[core]\n")
    (root / ".harness").mkdir()
    (root / ".harness" / "trajectory.jsonl").write_text("{}\n")

    script = build_census_script(str(root), BASELINE_MANIFEST_POLICY_V1)

    def run():
        proc = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        return parse_census_output(proc.stdout, **_IDENT,
                                   policy=BASELINE_MANIFEST_POLICY_V1)

    m1, m2 = run(), run()
    by_path = {e.path: e for e in m1.entries}
    assert by_path["src/a.py"].mode == "100644"
    assert by_path["run.sh"].mode == "100755"
    assert by_path["link"].object_type == "symlink"  # 不跟随：记 target digest
    assert by_path["link"].symlink_target_digest != by_path["src/a.py"].content_digest or True
    assert not any(p.startswith((".git/", ".harness/")) for p in by_path)
    assert m1.excluded_census_digest is not None  # 排除区留痕
    assert compute_baseline_manifest_digest(m1) == compute_baseline_manifest_digest(m2)


def test_census_script_prunes_policy_namespaces():
    script = build_census_script("/testbed", BASELINE_MANIFEST_POLICY_V1)
    assert "'./.git' -prune" in script and "'./.harness' -prune" in script
    assert "sha256sum" in script and "readlink" in script  # lstat/no-follow 面
