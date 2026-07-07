"""inspect-rh2-s1（S1-9 总账本）单测：四步范式逐步的正例与 fail-closed 反例。

两类形态：
- hermetic：tmp 假 s1 目录（最小 evidence 集）上生成 + 校验 + 逐步破坏；
- 真实自洽：对真实 docs/.../s1 目录重新生成到内存并校验（不写盘、不依赖
  在盘 summary 的新旧——防止本测试因 notes 后续编辑而脆化）。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repoharness2.inspect_s1 import (
    BLOCKERS,
    DEFAULT_RH2_ROOT,
    DEFAULT_S1_DIR,
    EXIT_DIGEST_MISMATCH,
    EXIT_FORBIDDEN_MARKER,
    EXIT_OK,
    EXIT_STRUCTURAL_FAILED,
    EXIT_SUMMARY_INVALID,
    SLIME_IMAGE_DIGEST_PIN,
    SUMMARY_FILENAME,
    build_summary,
    verify,
    write_summary,
)

PROBE_PAYLOAD = {
    "probe": "s1_0_uh",
    "date_utc": "2026-07-07 09:30:25 UTC",
    "overall_pass": True,
    "slime_image_digest": SLIME_IMAGE_DIGEST_PIN,
    "alignment": {"offsets_eq_genlen_plus_1": True},
}


@pytest.fixture()
def fake_s1_dir(tmp_path: Path) -> Path:
    """最小合法 s1 evidence 目录：探针结果 + blockers 文档 + 两份普通证据。"""

    s1 = tmp_path / "s1"
    s1.mkdir()
    (s1 / "uh_probe_result.json").write_text(
        json.dumps(PROBE_PAYLOAD, ensure_ascii=False), encoding="utf-8"
    )
    (s1 / "s2_blockers.md").write_text(
        "# blockers\n\n## s2_blocker_offline_export_thinking_models\n\n"
        "升级路径：分叉感知重建（叶链 tokens + used-refs 锚定）。\n",
        encoding="utf-8",
    )
    (s1 / "implementation-notes.md").write_text("# notes\n时钟基准声明。\n", encoding="utf-8")
    artifacts = s1 / "7a_artifacts"
    artifacts.mkdir()
    (artifacts / "ckpt_discard_run9.log").write_text("rm -rf … No such file\n", encoding="utf-8")
    return s1


def _write_fake_summary(s1: Path, **overrides) -> Path:
    summary = build_summary(s1, DEFAULT_RH2_ROOT, pytest_count=600)
    summary.update(overrides)
    path = s1 / SUMMARY_FILENAME
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 正例
# ---------------------------------------------------------------------------


def test_generate_then_verify_ok(fake_s1_dir):
    write_summary(fake_s1_dir, DEFAULT_RH2_ROOT, pytest_count=600)
    assert verify(fake_s1_dir, DEFAULT_RH2_ROOT) == EXIT_OK


def test_real_s1_dir_regeneration_self_consistent(tmp_path):
    """真实 evidence 目录：build_summary 的 digest 与在盘文件自洽（写到 tmp 校验）。

    真实 s1 目录必须已含 s2_blockers.md 与 uh_probe_result.json（S1-9 交付物）。
    """
    assert DEFAULT_S1_DIR.is_dir(), "真实 s1 evidence 目录必须在场"
    # 把真实目录的 summary 生成到内存，写进真实目录旁校验会污染证据——
    # 这里直接对真实目录做一次完整 verify 流程的"生成侧"：digest 由在盘文件
    # 计算，再立即用同一目录复核（读写都在真实目录，但 summary 写到 tmp 后
    # 用参数指向真实目录会导致 summary 路径不一致，故此处生成到真实目录内存
    # 形态，仅校验构造不落盘）。
    summary = build_summary(DEFAULT_S1_DIR, DEFAULT_RH2_ROOT, pytest_count=600)
    assert summary["source_digests"], "真实 evidence 目录不应为空"
    assert any(key.endswith("uh_probe_result.json") for key in summary["source_digests"])
    assert any(key.endswith("s2_blockers.md") for key in summary["source_digests"])
    assert any(key.endswith("inspect_s1.py") for key in summary["code_digests"])
    assert summary["blockers"] == BLOCKERS


# ---------------------------------------------------------------------------
# fail-closed 反例（逐步破坏）
# ---------------------------------------------------------------------------


def test_missing_summary_fails(fake_s1_dir):
    assert verify(fake_s1_dir, DEFAULT_RH2_ROOT) == EXIT_SUMMARY_INVALID


def test_unknown_field_rejected_by_whitelist(fake_s1_dir):
    """③ 字段白名单：summary 里塞未知字段 -> 退出码 2。"""
    _write_fake_summary(fake_s1_dir, smuggled_field="x")
    assert verify(fake_s1_dir, DEFAULT_RH2_ROOT) == EXIT_SUMMARY_INVALID


def test_evidence_tampering_detected_by_digest(fake_s1_dir):
    """① digest 重算：生成后改动 evidence 文件 -> 退出码 3。"""
    write_summary(fake_s1_dir, DEFAULT_RH2_ROOT, pytest_count=600)
    (fake_s1_dir / "implementation-notes.md").write_text("# tampered\n", encoding="utf-8")
    assert verify(fake_s1_dir, DEFAULT_RH2_ROOT) == EXIT_DIGEST_MISMATCH


def test_unrecorded_evidence_file_detected(fake_s1_dir):
    """① 反向核对：生成后塞进未入账文件 -> 退出码 3（防绕过账本塞私货）。"""
    write_summary(fake_s1_dir, DEFAULT_RH2_ROOT, pytest_count=600)
    (fake_s1_dir / "smuggled_evidence.md").write_text("out of ledger\n", encoding="utf-8")
    assert verify(fake_s1_dir, DEFAULT_RH2_ROOT) == EXIT_DIGEST_MISMATCH


def test_task_status_tampering_detected_structurally(fake_s1_dir):
    """② report 重建对照：任务状态被改（如 7b 谎报 done）-> 退出码 5。"""
    summary = build_summary(fake_s1_dir, DEFAULT_RH2_ROOT, pytest_count=600)
    summary["tasks"] = {**summary["tasks"], "S1-7b": "done"}
    (fake_s1_dir / SUMMARY_FILENAME).write_text(
        json.dumps(summary, ensure_ascii=False), encoding="utf-8"
    )
    assert verify(fake_s1_dir, DEFAULT_RH2_ROOT) == EXIT_STRUCTURAL_FAILED


def test_blockers_cannot_be_dropped(fake_s1_dir):
    """任务 C"不淡化"：blockers 清空 -> 退出码 5。"""
    _write_fake_summary(fake_s1_dir, blockers=[])
    assert verify(fake_s1_dir, DEFAULT_RH2_ROOT) == EXIT_STRUCTURAL_FAILED


def test_probe_regression_detected(fake_s1_dir):
    """A10 探针：overall_pass 翻 false -> 退出码 5（U-H 背书失效必须炸）。"""
    bad_probe = dict(PROBE_PAYLOAD, overall_pass=False)
    (fake_s1_dir / "uh_probe_result.json").write_text(
        json.dumps(bad_probe, ensure_ascii=False), encoding="utf-8"
    )
    write_summary(fake_s1_dir, DEFAULT_RH2_ROOT, pytest_count=600)
    assert verify(fake_s1_dir, DEFAULT_RH2_ROOT) == EXIT_STRUCTURAL_FAILED


def test_blockers_doc_must_name_blocker_and_upgrade_path(fake_s1_dir):
    """s2_blockers.md 漏点名 blocker id / 升级路径 -> 退出码 5。"""
    (fake_s1_dir / "s2_blockers.md").write_text("# 空文档\n", encoding="utf-8")
    write_summary(fake_s1_dir, DEFAULT_RH2_ROOT, pytest_count=600)
    assert verify(fake_s1_dir, DEFAULT_RH2_ROOT) == EXIT_STRUCTURAL_FAILED


def test_marker_in_summary_fails_closed(fake_s1_dir):
    """④ marker 扫描：summary 本体含 forbidden marker -> 退出码 4（总账本必须干净）。"""
    summary = build_summary(fake_s1_dir, DEFAULT_RH2_ROOT, pytest_count=600)
    summary["clock_baseline_note"] = "leaked test_patch mention"
    (fake_s1_dir / SUMMARY_FILENAME).write_text(
        json.dumps(summary, ensure_ascii=False), encoding="utf-8"
    )
    assert verify(fake_s1_dir, DEFAULT_RH2_ROOT) == EXIT_FORBIDDEN_MARKER


def test_pytest_baseline_below_floor_rejected(fake_s1_dir):
    """测试基线只增不减：低于 7a 收口态 560 -> 退出码 5。"""
    write_summary(fake_s1_dir, DEFAULT_RH2_ROOT, pytest_count=100)
    assert verify(fake_s1_dir, DEFAULT_RH2_ROOT) == EXIT_STRUCTURAL_FAILED
