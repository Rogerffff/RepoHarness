"""A7 条 1/3/4 的 hygiene 单测：diff 段切分、篡改/污染分类、cleaned patch 剥离。

不需要 docker；末尾几个用例用本机 git 仓库验证真实导出链路
（含 `git add -N` 的未跟踪新文件导出，以及 add -N 失败必须 fail-closed
的 codex#3 正反例）。
"""

from pathlib import Path

import pytest
from grading_fixtures import (
    GOOD_PATCH,
    POLLUTION_SEGMENT,
    TAMPER_SEGMENT,
    FIXTURE_HYGIENE,
    build_fixture_repo,
    clone_workspace,
)

from repoharness2.contracts import PatchHygieneResult
from repoharness2.envpack.bundles import sha256_of_text
from repoharness2.grading.manager import (
    BASE_UNTRACKED_SNAPSHOT_SCRIPT,
    UNPARSEABLE_SEGMENT_LABEL,
    HostWorkspace,
    HygieneRules,
    WorkspaceExportError,
    build_export_patch_script,
    clean_patch,
    export_cleaned_patch,
    patch_touched_paths,
    split_patch_segments,
)


# ---------------------------------------------------------------------------
# 段切分
# ---------------------------------------------------------------------------


def test_split_segments_paths_and_roundtrip():
    patch = GOOD_PATCH + TAMPER_SEGMENT + POLLUTION_SEGMENT
    segments = split_patch_segments(patch)
    assert [seg.paths for seg in segments] == [
        ("src/thing.py",),
        ("tests/test_thing.py",),
        ("grader/secret.txt",),
    ]
    # 段文本拼回去必须等于原文（切分不许丢字节，否则重放载荷会被悄悄改写）
    assert "".join(seg.text for seg in segments) == patch


def test_split_segments_empty_patch():
    assert split_patch_segments("") == []
    assert split_patch_segments("   \n") == []


def test_split_segments_unparseable_preamble_is_flagged():
    patch = "some stray text not a diff\n" + GOOD_PATCH
    segments = split_patch_segments(patch)
    assert segments[0].header_parsed is False
    assert segments[0].paths == ()
    assert segments[1].paths == ("src/thing.py",)


def test_patch_touched_paths():
    assert patch_touched_paths(GOOD_PATCH + POLLUTION_SEGMENT) == {
        "src/thing.py",
        "grader/secret.txt",
    }


# ---------------------------------------------------------------------------
# 分类 + 剥离
# ---------------------------------------------------------------------------


def test_clean_patch_clean_case():
    cleaned = clean_patch(GOOD_PATCH, FIXTURE_HYGIENE)
    assert cleaned.verdict == "clean"
    assert cleaned.cleaned_patch == GOOD_PATCH
    assert cleaned.cleaned_patch_digest == sha256_of_text(GOOD_PATCH)
    hygiene = cleaned.hygiene_result(replayed_on_clean_checkout=True)
    assert isinstance(hygiene, PatchHygieneResult)
    assert hygiene.verdict == "clean" and not hygiene.forbidden_paths


def test_clean_patch_strips_test_tampering():
    cleaned = clean_patch(GOOD_PATCH + TAMPER_SEGMENT, FIXTURE_HYGIENE)
    assert cleaned.verdict == "rejected_test_tampering"
    assert cleaned.test_files_modified is True
    assert cleaned.stripped_test_paths == ("tests/test_thing.py",)
    # 篡改段被整段剥离，合法 src 段保留
    assert cleaned.cleaned_patch == GOOD_PATCH
    assert "tests/test_thing.py" not in cleaned.cleaned_patch


def test_clean_patch_strips_forbidden_contamination():
    cleaned = clean_patch(GOOD_PATCH + POLLUTION_SEGMENT, FIXTURE_HYGIENE)
    assert cleaned.verdict == "rejected_forbidden_contamination"
    assert cleaned.forbidden_paths == ("grader/secret.txt",)
    assert cleaned.cleaned_patch == GOOD_PATCH


def test_clean_patch_tampering_takes_priority_and_both_recorded():
    """篡改 + 污染同时在场：verdict 取篡改（契约优先级），污染事实照记。"""

    cleaned = clean_patch(TAMPER_SEGMENT + POLLUTION_SEGMENT, FIXTURE_HYGIENE)
    assert cleaned.verdict == "rejected_test_tampering"
    assert cleaned.forbidden_paths == ("grader/secret.txt",)
    assert cleaned.cleaned_patch == ""  # 两段全剥，重放载荷为空
    # 该组合能构造出合法的契约对象（verdict 一致性校验器放行）
    hygiene = cleaned.hygiene_result(replayed_on_clean_checkout=True)
    assert hygiene.test_files_modified and hygiene.forbidden_path_touched


def test_clean_patch_unparseable_segment_fails_closed():
    patch = "garbage that is not a diff header\n@@ fake hunk @@\n" + GOOD_PATCH
    cleaned = clean_patch(patch, FIXTURE_HYGIENE)
    assert cleaned.verdict == "rejected_forbidden_contamination"
    assert UNPARSEABLE_SEGMENT_LABEL in cleaned.forbidden_paths
    assert cleaned.cleaned_patch == GOOD_PATCH  # 看不懂的段绝不进重放载荷


def test_glob_semantics_cover_nested_test_dirs():
    rules = HygieneRules(test_globs=("*tests/*", "test_*.py", "*/test_*.py"))
    for path in (
        "tests/test_a.py",
        "sympy/vector/tests/test_simplify.py",
        "test_requests.py",
        "pkg/test_utils.py",
    ):
        assert rules.is_test_path(path), path
    assert not rules.is_test_path("src/thing.py")


# ---------------------------------------------------------------------------
# 真实导出链路（本机 git，无 docker）
# ---------------------------------------------------------------------------


async def test_export_cleaned_patch_from_real_workspace(tmp_path: Path):
    """真实 git workspace：跟踪文件修改 + 未跟踪新文件（污染）都要被导出并分类。"""

    repo = build_fixture_repo(tmp_path / "snapshot")
    ws = clone_workspace(repo, tmp_path / "ws")
    (ws / "src" / "thing.py").write_text('def feature():\n    return "fixed"\n')
    (ws / "grader").mkdir()
    (ws / "grader" / "secret.txt").write_text("stolen grading assets\n")  # 未跟踪新文件

    cleaned = await export_cleaned_patch(HostWorkspace(ws), FIXTURE_HYGIENE)
    assert cleaned.verdict == "rejected_forbidden_contamination"
    assert cleaned.forbidden_paths == ("grader/secret.txt",)
    # 未跟踪文件出现在 raw patch（git add -N 生效），但被剥出 cleaned patch
    assert "grader/secret.txt" in cleaned.raw_patch
    assert "grader/secret.txt" not in cleaned.cleaned_patch
    assert 'return "fixed"' in cleaned.cleaned_patch


async def test_export_from_dead_workspace_raises(tmp_path: Path):
    """workspace 不是 git 仓库（≈ rollout 容器已死）→ WorkspaceExportError（infra 族源头）。"""

    empty = tmp_path / "not_a_repo"
    empty.mkdir()
    with pytest.raises(WorkspaceExportError):
        await export_cleaned_patch(HostWorkspace(empty), FIXTURE_HYGIENE)


async def test_export_includes_untracked_new_source_file(tmp_path: Path):
    """codex#3 正例：解法新增源文件（未跟踪）——导出 patch 必须完整含新文件段且判 clean。"""

    repo = build_fixture_repo(tmp_path / "snapshot")
    ws = clone_workspace(repo, tmp_path / "ws")
    (ws / "src" / "helper.py").write_text('def impl():\n    return "fixed"\n')  # 新文件
    (ws / "src" / "thing.py").write_text(
        "from src.helper import impl\n\n\ndef feature():\n    return impl()\n"
    )

    cleaned = await export_cleaned_patch(HostWorkspace(ws), FIXTURE_HYGIENE)
    assert cleaned.verdict == "clean"
    assert "src/helper.py" in cleaned.cleaned_patch
    assert "new file mode" in cleaned.cleaned_patch  # intent-to-add 段完整在场
    assert 'return "fixed"' in cleaned.cleaned_patch


async def test_export_excludes_preexisting_untracked_baseline(tmp_path: Path):
    """S1-7a 远程回归实测反例：镜像 /testbed 自带未跟踪残留（psf__requests-1142
    的 build/lib/**）不得进 patch——否则 clean checkout 重放因 already exists
    整体失败，S0-7 直评 resolved 的题被误判 patch_apply_failed。

    生产链路：物化侧跑 BASE_UNTRACKED_SNAPSHOT_SCRIPT 存基线清单，导出脚本按
    清单逐路径 :(exclude,literal)。本测试用宿主临时路径注入同一对脚本。
    """

    repo = build_fixture_repo(tmp_path / "snapshot")
    ws = clone_workspace(repo, tmp_path / "ws")
    # 基线未跟踪残留（agent 动工前就存在，非 agent 产物）
    (ws / "build" / "lib").mkdir(parents=True)
    (ws / "build" / "lib" / "junk.py").write_text("# stale build artifact\n")
    manifest = tmp_path / "artifacts" / "base_untracked.txt"

    snap = await HostWorkspace(ws).run_bash(
        BASE_UNTRACKED_SNAPSHOT_SCRIPT.format(manifest=manifest)
    )
    assert snap.exit_code == 0
    assert "build/lib/junk.py" in manifest.read_text()

    # agent 改动：跟踪文件修改 + 新增源文件（codex#3 语义必须保留）
    (ws / "src" / "helper.py").write_text('def impl():\n    return "fixed"\n')
    (ws / "src" / "thing.py").write_text(
        "from src.helper import impl\n\n\ndef feature():\n    return impl()\n"
    )

    cleaned = await export_cleaned_patch(
        HostWorkspace(ws),
        FIXTURE_HYGIENE,
        export_script=build_export_patch_script(str(manifest)),
    )
    assert cleaned.verdict == "clean"
    assert "src/helper.py" in cleaned.cleaned_patch  # agent 新文件仍在
    assert 'return "fixed"' in cleaned.cleaned_patch
    assert "build/lib/junk.py" not in cleaned.raw_patch  # 基线残留被排除
    # 清单缺席时行为与旧版逐字节一致（fixture/host workspace 兼容）
    legacy = await export_cleaned_patch(HostWorkspace(ws), FIXTURE_HYGIENE)
    assert "build/lib/junk.py" in legacy.raw_patch  # 无清单 -> 残留仍会进（旧语义）


async def test_export_fails_closed_when_intent_to_add_fails(tmp_path: Path):
    """codex#3 反例：`git add -N` 失败（注入 index.lock 残留）必须让导出整体失败
    （WorkspaceExportError 带 stderr），而不是旧行为的 `|| true` 吞错——那时
    `git diff HEAD` 照样成功，未跟踪新文件被静默漏出 patch，评分得假阴性。"""

    repo = build_fixture_repo(tmp_path / "snapshot")
    ws = clone_workspace(repo, tmp_path / "ws")
    (ws / "src" / "helper.py").write_text('def impl():\n    return "fixed"\n')  # 会被漏的新文件
    (ws / ".git" / "index.lock").write_text("")  # add -N 拿不到索引锁 -> 失败

    with pytest.raises(WorkspaceExportError) as exc_info:
        await export_cleaned_patch(HostWorkspace(ws), FIXTURE_HYGIENE)
    assert "index.lock" in str(exc_info.value)  # stderr 已记录进错误（排障可用）
