"""租前完整审查 PR-P0-2 / PR-P0-3B 修复验收：launch post-run 探针。

- PR-P0-2（确定性假红）：torch distributed checkpoint 的 ``.metadata`` 是 DCP
  pickle metadata，不是 ``torch.save`` archive——旧探针 ``torch.load`` 必然报
  "Invalid magic number"，训练成功也判红。修复 = FileSystemReader.read_metadata。
  这里用**真实 DCP fixture**（torch.distributed.checkpoint.save 产出）做正例，
  并保留旧读法必失败的锚点测试（防止未来有人"简化"回 torch.load）。
- PR-P0-3B（fail-open 假绿）：docker/ray 查询失败曾被记成"零孤儿"。修复后
  查询失败显式 ``*_query_ok=false`` 且探针非零退出；s1_compat 下 finalization
  store 设计上不存在，必须如实 ``not_applicable`` 而不是拿"目录不存在 ⇒ 未终结
  数 0"冒充通过。docker 用 launch preflight 验证过的 --docker-bin 路径。

探针为纯 stdlib+torch 模块（不 import miles），两条 lane 都真实执行。
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
from pathlib import Path

import pytest

_PROBES_PATH = (
    Path(__file__).resolve().parents[2] / "experiments" / "miles_gpu_spike" / "postrun_probes.py"
)
_spec = importlib.util.spec_from_file_location("postrun_probes_under_test", _PROBES_PATH)
probes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probes)


# ---------------------------------------------------------------------------
# checkpoint 探针（PR-P0-2）
# ---------------------------------------------------------------------------


def _make_dcp_checkpoint(root: Path) -> Path:
    """真实 Megatron 风格布局：tracker + iter_/ 下 torch DCP 产物。"""
    import torch
    import torch.distributed.checkpoint as dcp

    step = root / "iter_0000001"
    dcp.save({"w": torch.arange(6, dtype=torch.float32).reshape(2, 3)}, checkpoint_id=str(step))
    (root / "latest_checkpointed_iteration.txt").write_text("1")
    return step


def test_checkpoint_probe_reads_real_dcp_metadata(tmp_path):
    """正例：真实 DCP checkpoint 通过（saved/reloaded/deleted 全 True，目录删除）。"""
    ckpt = tmp_path / "ckpt"
    _make_dcp_checkpoint(ckpt)
    probe = probes.checkpoint_probe(ckpt)
    assert probe["saved"] is True
    assert probe["reloaded"] is True, f"真实 DCP metadata 必须可读：{probe['note']}"
    assert probe["deleted"] is True and not ckpt.exists()
    assert "dcp" in probe["reload_mode"]


def test_checkpoint_probe_rejects_corrupt_metadata(tmp_path):
    """负例：损坏 .metadata 必须 reloaded=False 且不删除目录（证据保留）。"""
    ckpt = tmp_path / "ckpt"
    step = _make_dcp_checkpoint(ckpt)
    (step / ".metadata").write_bytes(b"corrupted-not-a-pickle")
    probe = probes.checkpoint_probe(ckpt)
    assert probe["saved"] is True
    assert probe["reloaded"] is False
    assert "reload 失败" in probe["note"]
    assert probe["deleted"] is False and ckpt.exists()


def test_audited_false_red_torch_load_cannot_read_dcp_metadata(tmp_path):
    """审查假红锚点：旧探针的 torch.load(.metadata) 对**正常** DCP checkpoint
    也必然抛错（"Invalid magic number"）——本测试钉住该事实，防止探针被改回
    torch.load 后在真实租期上把成功训练判红。"""
    import torch

    step = _make_dcp_checkpoint(tmp_path / "ckpt")
    with pytest.raises(Exception, match="magic number|corrupt"):
        torch.load(step / ".metadata", map_location="cpu", weights_only=False)


def test_checkpoint_probe_missing_tracker_not_saved(tmp_path):
    ckpt = tmp_path / "ckpt"
    ckpt.mkdir()
    probe = probes.checkpoint_probe(ckpt)
    assert probe["saved"] is False and probe["reloaded"] is False


# ---------------------------------------------------------------------------
# shutdown 探针（PR-P0-3B）
# ---------------------------------------------------------------------------


def _write_stub(path: Path, script: str) -> Path:
    path.write_text(f"#!/bin/sh\n{script}\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


@pytest.fixture()
def stub_bins(tmp_path, monkeypatch):
    """桩 docker/ray：docker 走显式 --docker-bin 路径，ray 走 PATH。"""
    bins = tmp_path / "bin"
    bins.mkdir()
    docker = _write_stub(bins / "docker", "exit 0")
    _write_stub(bins / "ray", 'echo "[]"')
    monkeypatch.setenv("PATH", f"{bins}:{os.environ['PATH']}")
    return {"dir": bins, "docker": docker}


def test_shutdown_probe_all_green_s1_compat(tmp_path, stub_bins):
    """正例：查询全部成功、零孤儿；s1_compat finalization 如实 not_applicable
    （不是 unfinalized=0 的 vacuous 零）。"""
    probe = probes.shutdown_probe(tmp_path / "artifacts", str(stub_bins["docker"]), "s1_compat")
    assert probe["docker_query_ok"] is True and probe["ray_query_ok"] is True
    assert probe["orphan_workers"] == 0
    assert probe["finalization"]["status"] == "not_applicable"
    assert probes.shutdown_probe_ok(probe) is True


def test_shutdown_probe_docker_failure_is_not_zero_orphans(tmp_path, stub_bins):
    """审查反例：docker rc=1 曾只写 detail、计数仍为 0 而 judge 放行。现在
    docker_query_ok=false、orphan_workers=None、探针不 ok。"""
    bad_docker = _write_stub(stub_bins["dir"] / "docker_bad", "exit 1")
    probe = probes.shutdown_probe(tmp_path / "artifacts", str(bad_docker), "s1_compat")
    assert probe["docker_query_ok"] is False
    assert probe["orphan_workers"] is None, "查询失败不得给出孤儿计数"
    assert probes.shutdown_probe_ok(probe) is False


def test_shutdown_probe_ray_bad_json_is_query_failure(tmp_path, stub_bins):
    _write_stub(stub_bins["dir"] / "ray", 'echo "not json"')
    probe = probes.shutdown_probe(tmp_path / "artifacts", str(stub_bins["docker"]), "s1_compat")
    assert probe["ray_query_ok"] is False
    assert probes.shutdown_probe_ok(probe) is False


def test_shutdown_probe_missing_docker_binary(tmp_path, stub_bins):
    probe = probes.shutdown_probe(
        tmp_path / "artifacts", str(tmp_path / "no-such-docker"), "s1_compat"
    )
    assert probe["docker_query_ok"] is False
    assert probes.shutdown_probe_ok(probe) is False


def test_shutdown_probe_orphan_container_detected(tmp_path, stub_bins):
    orphan_docker = _write_stub(stub_bins["dir"] / "docker_orphan", 'echo "rh2-rollout-42"')
    probe = probes.shutdown_probe(tmp_path / "artifacts", str(orphan_docker), "s1_compat")
    assert probe["docker_query_ok"] is True
    assert probe["orphan_workers"] == 1
    assert probes.shutdown_probe_ok(probe) is False


def test_shutdown_probe_finalization_required_outside_s1_compat(tmp_path, stub_bins):
    """非 s1_compat 模式下 store 缺失 = absent_required（FAIL 面），不再是
    "absent 只写 detail"的 fail-open。"""
    probe = probes.shutdown_probe(tmp_path / "artifacts", str(stub_bins["docker"]), "fa_audit_only")
    assert probe["finalization"]["status"] == "absent_required"
    assert probes.shutdown_probe_ok(probe) is False

    attempts = tmp_path / "artifacts" / "finalization" / "attempts"
    good = attempts / "a1"
    good.mkdir(parents=True)
    (good / "receipt.json").write_text("{}")
    probe = probes.shutdown_probe(tmp_path / "artifacts", str(stub_bins["docker"]), "fa_audit_only")
    assert probe["finalization"]["status"] == "ok_empty"
    assert probes.shutdown_probe_ok(probe) is True

    bad = attempts / "a2"
    bad.mkdir()
    probe = probes.shutdown_probe(tmp_path / "artifacts", str(stub_bins["docker"]), "fa_audit_only")
    assert probe["finalization"]["status"] == "unfinalized"
    assert probe["finalization"]["num_unfinalized"] == 1
    assert probes.shutdown_probe_ok(probe) is False


def test_shutdown_probe_cli_writes_json_and_exit_code(tmp_path, stub_bins):
    """CLI 契约：写出 JSON 文件；达标 rc=0、失败 rc=1（launch fail-closed 依赖）。"""
    out = tmp_path / "shutdown_probe.json"
    rc = probes.main([
        "shutdown", "--artifacts", str(tmp_path / "artifacts"), "--out", str(out),
        "--docker-bin", str(stub_bins["docker"]), "--execution-mode", "s1_compat",
    ])
    assert rc == 0
    data = json.loads(out.read_text())
    assert data["docker_query_ok"] is True
    bad_docker = _write_stub(stub_bins["dir"] / "docker_bad2", "exit 7")
    rc = probes.main([
        "shutdown", "--artifacts", str(tmp_path / "artifacts"), "--out", str(out),
        "--docker-bin", str(bad_docker), "--execution-mode", "s1_compat",
    ])
    assert rc == 1
