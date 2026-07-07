"""materialize 血缘校验单测：合法/非法用例（S1-2 验收条款）。

判据（S0-7 两次实证迭代的最终形态）：base_commit 对象存在 且
（HEAD == base_commit 或 HEAD^ == base_commit）；叠加提交内容可非空
（astropy-14995 的 "SWE-bench" 提交带 1 行 pyproject.toml 环境修补）。

用例里的 sha 取自 S0-7 真实记录：django-11099 的
HEAD=2a2861e0…、HEAD^=base=d26b2424…。
"""

import pytest

from repoharness2.envpack.materialize import (
    BASH_ENV_CONTENT,
    MaterializeError,
    build_probe_script,
    evaluate_probe,
)

# S0-7 实测值（swe_smoke_report.md 发现 2）：
BASE = "d26b2424437dabeeca94d7900b37d2df4410da0c"  # django-11099 base_commit
OVERLAY_HEAD = "2a2861e07ba48f39e6b6ee5c2c6c320b436b2b78"  # 构建时叠加的 "SWE-bench" 提交（40 位合法形态）
UNRELATED = "a" * 40


def probe_stdout(
    head: str,
    parent: str,
    base_object_ok: bool = True,
    diffstat: str = "",
    dirty: list[str] | None = None,
) -> str:
    lines = [f"HEAD={head}"]
    if base_object_ok:
        lines.append("BASE_OBJECT_OK")
    lines.append(f"PARENT={parent}")
    lines.append(f"DIFFSTAT={diffstat}")
    lines.extend(dirty or [])
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 合法用例
# ---------------------------------------------------------------------------


def test_head_equals_base_passes():
    """镜像 HEAD 直接就是 base_commit 的形态（判据第一分支）。"""
    check = evaluate_probe(BASE, 0, probe_stdout(head=BASE, parent="none"))
    assert check.lineage_ok and check.ok
    check.ensure_ok()  # 不抛


def test_overlay_commit_with_parent_base_passes():
    """官方常态：HEAD 是叠加提交、HEAD^ == base（django/sympy/requests 7 题，空 diff）。"""
    check = evaluate_probe(BASE, 0, probe_stdout(head=OVERLAY_HEAD, parent=BASE))
    assert check.lineage_ok and check.ok
    assert check.env_diffstat_vs_base == ""


def test_overlay_commit_with_nonempty_env_patch_passes():
    """astropy-14995 形态：叠加提交内容非空（1 行环境修补）——血缘判据下照样合法。"""
    diffstat = "1 file changed, 1 insertion(+), 1 deletion(-)"
    check = evaluate_probe(
        BASE, 0, probe_stdout(head=OVERLAY_HEAD, parent=BASE, diffstat=diffstat)
    )
    assert check.ok
    assert check.env_diffstat_vs_base == diffstat  # 修补作证据记录，不影响判定


def test_dirty_worktree_is_evidence_not_failure():
    """setup 时工作树非干净只记证据（trace.info），不构成物化失败。"""
    check = evaluate_probe(
        BASE, 0, probe_stdout(head=OVERLAY_HEAD, parent=BASE, dirty=[" M setup.py", "?? junk.txt"])
    )
    assert check.ok
    assert check.dirty_paths == ["M setup.py", "?? junk.txt"]
    assert check.trace_info()["setup_git_dirty"] == ["M setup.py", "?? junk.txt"]


# ---------------------------------------------------------------------------
# 非法用例（fail-closed）
# ---------------------------------------------------------------------------


def test_unrelated_head_rejected():
    """HEAD 与 base 无血缘（HEAD != base 且 HEAD^ != base）→ 拒绝。"""
    check = evaluate_probe(BASE, 0, probe_stdout(head=UNRELATED, parent=OVERLAY_HEAD))
    assert not check.lineage_ok and not check.ok
    with pytest.raises(MaterializeError, match="物化校验失败"):
        check.ensure_ok()


def test_missing_base_object_rejected():
    """base_commit 对象不存在（探针拿不到 BASE_OBJECT_OK）→ 即使 HEAD^ 碰巧相等也拒绝。"""
    check = evaluate_probe(
        BASE, 0, probe_stdout(head=OVERLAY_HEAD, parent=BASE, base_object_ok=False)
    )
    # 真实探针里 cat-file 失败会让整段 exit!=0；这里单独制造 base_object_ok=False
    # 的矛盾形态，证明判定不只依赖 exit code。
    assert not check.ok
    with pytest.raises(MaterializeError):
        check.ensure_ok()


def test_probe_failure_rejected_and_stdout_untrusted():
    """探针 exit!=0 → 不解析 stdout（不可信），保留 stderr 尾部证据并拒绝。"""
    check = evaluate_probe(
        BASE, 1, probe_stdout(head=BASE, parent="none"), stderr="fatal: not a git repository"
    )
    assert check.head == "" and not check.base_object_ok and not check.ok
    with pytest.raises(MaterializeError, match="not a git repository"):
        check.ensure_ok()


def test_empty_stdout_rejected():
    check = evaluate_probe(BASE, 0, "")
    assert not check.ok


# ---------------------------------------------------------------------------
# 探针脚本生成
# ---------------------------------------------------------------------------


def test_probe_script_embeds_base_commit_and_tags():
    script = build_probe_script(BASE)
    assert BASE in script
    for needle in ("HEAD=", "BASE_OBJECT_OK", "PARENT=", "DIFFSTAT=", "git status --porcelain"):
        assert needle in script


def test_probe_script_rejects_malformed_sha():
    """base_commit 要内插进 bash 文本，形态错误（含注入形态）直接拒绝生成。"""
    for bad in ("HEAD", "d26b2424", BASE.upper(), f"{BASE}; rm -rf /", ""):
        with pytest.raises(ValueError, match="40 位十六进制"):
            build_probe_script(bad)


def test_bash_env_content_activates_testbed():
    assert "activate testbed" in BASH_ENV_CONTENT
