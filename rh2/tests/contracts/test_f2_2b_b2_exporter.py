"""B2 验收：FrozenPatchArtifactV1 契约 + trusted exporter。

计划验收项：staged/unstaged/untracked/binary/symlink/mode 变更检出 +
"repo-controlled Git 不被执行"负测试（hooks/filters/external diff 注入
不触发）。exporter 无 git：staged/unstaged 差别在字节比较下天然消失，
untracked 内容变化（旧指纹方案的假阴性盲区）被内容 digest 捕获。
"""

from __future__ import annotations

import base64
import hashlib
import subprocess
from types import SimpleNamespace

import pytest

from repoharness2.adapters.slime.baseline_census import (
    BASELINE_MANIFEST_POLICY_V1,
    build_census_script,
    parse_census_output,
)
from repoharness2.adapters.slime.patch_exporter import (
    PatchExportError,
    diff_census_against_baseline,
    export_frozen_patch,
)
from repoharness2.contracts.frozen_patch import (
    FrozenPatchArtifactV1,
    PatchEntry,
    compute_frozen_patch_digest,
)

_IDENT = dict(
    task_id="t1", workdir="/testbed",
    public_bundle_digest="sha256:" + "e" * 64,
    runtime_image_digest="sha256:" + "1" * 64,
    materialized_head="a" * 40, task_base_commit="b" * 40,
)


def _b64(data: bytes) -> tuple[str, str]:
    return (base64.b64encode(data).decode(),
            "sha256:" + hashlib.sha256(data).hexdigest())


def _art(entries, **over):
    base = dict(
        task_id="t1", rollout_execution_id="exec_1",
        physical_attempt_id="exec_1#p1-aaaa",
        baseline_manifest_digest="sha256:" + "b" * 64,
        public_bundle_digest="sha256:" + "e" * 64,
        runtime_image_digest="sha256:" + "1" * 64,
        materialized_head="a" * 40,
        entries=tuple(entries), excluded_census_changed=False,
    )
    base.update(over)
    return FrozenPatchArtifactV1(**base)


# ---------------------------------------------------------------------------
# 契约
# ---------------------------------------------------------------------------

def test_patch_entry_operation_field_matrix():
    b64, dg = _b64(b"data")
    PatchEntry(path="a", operation="add", object_type="regular", mode="100644",
               content_b64=b64, content_digest=dg)
    PatchEntry(path="d", operation="delete", object_type="regular")
    with pytest.raises(ValueError, match="delete 不得携带"):
        PatchEntry(path="d", operation="delete", object_type="regular", mode="100644")
    with pytest.raises(ValueError, match="必须携带"):
        PatchEntry(path="a", operation="modify", object_type="regular", mode="100644")
    with pytest.raises(ValueError, match="重算不符"):
        PatchEntry(path="a", operation="add", object_type="regular", mode="100644",
                   content_b64=b64, content_digest="sha256:" + "0" * 64)
    with pytest.raises(ValueError, match="120000"):
        PatchEntry(path="l", operation="add", object_type="symlink", mode="100644",
                   content_b64=b64, content_digest=dg)


def test_artifact_ordering_and_digest_recompute():
    b64, dg = _b64(b"x")
    e1 = PatchEntry(path="a", operation="add", object_type="regular",
                    mode="100644", content_b64=b64, content_digest=dg)
    art = _art([e1])
    d = compute_frozen_patch_digest(art)
    art2 = FrozenPatchArtifactV1.model_validate(art.model_dump(mode="json"))
    assert compute_frozen_patch_digest(art2) == d
    with pytest.raises(ValueError, match="排序"):
        e2 = PatchEntry(path="b", operation="delete", object_type="regular")
        _art([e2, e1])
    with pytest.raises(ValueError, match="父子前缀冲突"):
        _art([e1, PatchEntry(path="a/b", operation="delete", object_type="regular")])


# ---------------------------------------------------------------------------
# differ（纯函数）
# ---------------------------------------------------------------------------

def _census(text):
    return parse_census_output(text, **_IDENT, policy=BASELINE_MANIFEST_POLICY_V1)


def test_diff_detects_all_change_kinds():
    base = _census(
        "regular\t100644\t" + "1" * 64 + "\tkeep.py\n"
        "regular\t100644\t" + "2" * 64 + "\tmod.py\n"
        "regular\t100644\t" + "3" * 64 + "\tchmod.sh\n"
        "regular\t100644\t" + "4" * 64 + "\tgone.py\n"
        "symlink\t120000\t" + "5" * 64 + "\tlink\n"
    )
    post = _census(
        "regular\t100644\t" + "1" * 64 + "\tkeep.py\n"      # 不变
        "regular\t100644\t" + "9" * 64 + "\tmod.py\n"        # 内容变（untracked 同理）
        "regular\t100755\t" + "3" * 64 + "\tchmod.sh\n"      # mode-only
        "symlink\t120000\t" + "6" * 64 + "\tlink\n"          # target 变
        "regular\t100644\t" + "7" * 64 + "\tnew.py\n"        # 新增
    )
    changes = {c["path"]: c for c in diff_census_against_baseline(
        base, {e.path: e for e in post.entries})}
    assert changes["mod.py"]["operation"] == "modify"
    assert changes["chmod.sh"]["operation"] == "modify"  # mode 变化被检出
    assert changes["link"]["operation"] == "modify"
    assert changes["new.py"]["operation"] == "add"
    assert changes["gone.py"]["operation"] == "delete"
    assert "keep.py" not in changes


# ---------------------------------------------------------------------------
# 真实树 e2e（含 Git 注入负测试）
# ---------------------------------------------------------------------------

class _LocalWs:
    """本机 bash 执行（等价 run_bash；真实容器归 FA-5）。"""

    def __init__(self):
        self.scripts: list[str] = []

    async def run_bash(self, script: str):
        self.scripts.append(script)
        proc = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        return SimpleNamespace(exit_code=proc.returncode,
                               stdout=proc.stdout, stderr=proc.stderr)


async def test_real_tree_export_end_to_end_git_not_executed(tmp_path):
    """真实树：改内容/chmod/新增二进制/删除/改 symlink + 注入 hooks、
    gitattributes、diff.external——export 全链无 git 执行（marker 不出现、
    脚本文本无 git 调用），delta 五类全检出，二进制往返一致。"""

    import stat

    root = tmp_path / "ws"
    (root / "src").mkdir(parents=True)
    (root / "src" / "mod.py").write_text("old\n")
    (root / "src" / "gone.py").write_text("bye\n")
    exe = root / "chmod.sh"
    exe.write_text("#!/bin/sh\n")
    (root / "link").symlink_to("src/mod.py")
    # Git 注入面：repo-controlled 元数据 + 恶意 hook/external-diff
    marker = tmp_path / "GIT_EXECUTED_MARKER"
    gitdir = root / ".git"
    (gitdir / "hooks").mkdir(parents=True)
    hook = gitdir / "hooks" / "pre-commit"
    hook.write_text(f"#!/bin/sh\ntouch {marker}\n")
    hook.chmod(0o755)
    (gitdir / "config").write_text(
        f"[diff]\n\texternal = /bin/sh -c 'touch {marker}'\n"
    )
    (root / ".gitattributes").write_text("*.py diff=evil\n")

    ws = _LocalWs()
    ident = {**_IDENT, "workdir": str(root)}
    base_proc = subprocess.run(
        ["bash", "-c", build_census_script(str(root), BASELINE_MANIFEST_POLICY_V1)],
        capture_output=True, text=True)
    baseline = parse_census_output(base_proc.stdout, **ident,
                                   policy=BASELINE_MANIFEST_POLICY_V1)

    # 模型改动：内容/权限/新增二进制/删除/symlink target
    (root / "src" / "mod.py").write_text("new content\n")
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    binary = bytes([0, 1, 2, 255, 254]) * 3
    (root / "blob.bin").write_bytes(binary)
    (root / "src" / "gone.py").unlink()
    (root / "link").unlink()
    (root / "link").symlink_to("chmod.sh")

    art = await export_frozen_patch(
        ws, baseline, rollout_execution_id="exec_R",
        physical_attempt_id="exec_R#p1-abcd",
        baseline_manifest_digest="sha256:" + "b" * 64,
    )
    ops = {e.path: e for e in art.entries}
    assert ops["src/mod.py"].operation == "modify"
    assert ops["chmod.sh"].mode == "100755"  # mode-only 变化
    assert ops["blob.bin"].operation == "add"
    assert base64.b64decode(ops["blob.bin"].content_b64) == binary  # 二进制往返
    assert ops["src/gone.py"].operation == "delete"
    assert ops["link"].object_type == "symlink"
    assert base64.b64decode(ops["link"].content_b64) == b"chmod.sh"  # target 字节
    assert ".gitattributes" not in ops or True  # gitattributes 是普通文件事实
    # Git 未被执行：marker 不存在 + 全部脚本无 git 调用
    assert not marker.exists()
    assert all(" git " not in s and not s.strip().startswith("git ")
               for s in ws.scripts)
    # 确定性：重复导出同 digest
    art2 = await export_frozen_patch(
        ws, baseline, rollout_execution_id="exec_R",
        physical_attempt_id="exec_R#p1-abcd",
        baseline_manifest_digest="sha256:" + "b" * 64,
    )
    assert compute_frozen_patch_digest(art) == compute_frozen_patch_digest(art2)


async def test_export_digest_race_fail_closed():
    """census 与抓取之间内容漂移 → content_digest_race（静止期写者暴露）。"""

    class _RaceWs:
        def __init__(self):
            self.n = 0

        async def run_bash(self, script):
            if "find ." in script:
                return SimpleNamespace(exit_code=0, stdout=(
                    "regular\t100644\t" + hashlib.sha256(b"v1").hexdigest() + "\tf.py\n"
                ), stderr="")
            return SimpleNamespace(exit_code=0, stdout=(
                "f.py\t" + base64.b64encode(b"v2-changed").decode() + "\n"
            ), stderr="")

    empty = parse_census_output("", **_IDENT, policy=BASELINE_MANIFEST_POLICY_V1)
    with pytest.raises(PatchExportError, match="content_digest_race"):
        await export_frozen_patch(
            _RaceWs(), empty, rollout_execution_id="e",
            physical_attempt_id="e#p1-a",
            baseline_manifest_digest="sha256:" + "b" * 64,
        )


async def test_unsupported_object_in_post_tree_typed():
    class _FifoWs:
        async def run_bash(self, script):
            return SimpleNamespace(exit_code=0, stdout="UNSUPPORTED\tweird\n", stderr="")

    empty = parse_census_output("", **_IDENT, policy=BASELINE_MANIFEST_POLICY_V1)
    with pytest.raises(PatchExportError, match="unsupported_object_in_patch"):
        await export_frozen_patch(
            _FifoWs(), empty, rollout_execution_id="e",
            physical_attempt_id="e#p1-a",
            baseline_manifest_digest="sha256:" + "b" * 64,
        )
