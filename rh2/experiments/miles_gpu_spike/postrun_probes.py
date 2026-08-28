#!/usr/bin/env python3
"""miles GPU spike post-run 探针（launch.sh 从 heredoc 拆出，租前审查 PR-P0-2/P0-3B）。

拆出为独立模块的原因：heredoc 里的探针逻辑无法被 pytest 直接测试，租前审查在
checkpoint 探针里发现了确定性假红（用 ``torch.load`` 读 torch distributed
checkpoint 的 ``.metadata``——它是 DCP pickle metadata，不是 ``torch.save``
archive，正常 checkpoint 必然报 "Invalid magic number"）。现在：

- ``checkpoint`` 子命令：tracker + 迭代目录清单 + **DCP FileSystemReader.
  read_metadata()** 结构化反序列化（与 miles ``tools/convert_torch_dist_to_hf.py``
  的读取方式同族），成功后删除目录（探针 checkpoint 不作任何后续起点）。
- ``shutdown`` 子命令：孤儿容器 / 存活 ray actor / finalization store 三面。
  孤儿容器面（租前聚焦修复批 #4）同时覆盖 rollout（rh2-rollout）与真实评分
  （rh2-grading）两类容器名前缀，并在 ``--run-id`` 给定时优先按本 run 的
  owner label ``rh2.run_id=<run_id>``（launch 经 MILES_RH2_RUN_ID 下发，
  rollout/评分容器启动时盖章）精确归属；只查仍在运行容器，``docker ps -a``
  的已退出未删除容器留作 P1。
  租前审查 PR-P0-3B 的核心修复：**查询失败 ≠ 观测为零**——docker/ray 命令
  异常、非零退出码、坏 JSON 都显式记 ``*_query_ok=false`` 并导致探针非零退出；
  ``s1_compat`` 下 bringup 有意不建 FileFinalizationStore（bringup.py
  ``EXECUTION_MODE != "s1_compat"`` 才注入），此时 finalization 检查如实记
  ``not_applicable``，而不是拿 "store 不存在 ⇒ 未终结数 0" 冒充通过。
  docker 二进制用 launch preflight 验证过的 ``--docker-bin`` 路径，不再依赖
  环境 PATH 里碰巧的另一个 docker。

退出码：0 = 全部观测成功且达标；非零 = 任一查询失败或观测不达标。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

FINALIZATION_OK_STATUSES = ("ok_empty", "not_applicable")


# ---------------------------------------------------------------------------
# checkpoint 探针（PR-P0-2）
# ---------------------------------------------------------------------------

def read_dcp_metadata(step_dir: Path):
    """按 DCP 真实格式读 ``.metadata``（pickle，非 torch.save archive）。

    优先 ``torch.distributed.checkpoint.FileSystemReader.read_metadata()``；
    该 reader 内部就是对 ``.metadata`` 做 pickle 反序列化（Miles 转换工具
    ``UnpicklerWrapper`` 同族），损坏文件会抛异常。返回 Metadata 对象。
    """
    from torch.distributed.checkpoint import FileSystemReader  # noqa: PLC0415 - torch 仅探针期加载

    return FileSystemReader(str(step_dir)).read_metadata()


def checkpoint_probe(ckpt: Path) -> dict:
    probe = {
        "saved": False,
        "reloaded": False,
        "deleted": False,
        "reload_mode": "tracker+file-manifest+dcp_filesystemreader_metadata",
        "digest": None,
        "note": None,
    }
    tracker = ckpt / "latest_checkpointed_iteration.txt"
    iters = sorted(p for p in ckpt.glob("iter_*") if p.is_dir())
    if not (tracker.is_file() and iters):
        probe["note"] = f"tracker={tracker.is_file()} iter_dirs={len(iters)}"
        return probe
    probe["saved"] = True
    latest = iters[-1]
    files = sorted(p for p in latest.rglob("*") if p.is_file())
    digest = hashlib.sha256()
    digest.update(tracker.read_bytes())
    for p in files:
        digest.update(str(p.relative_to(ckpt)).encode())
        digest.update(str(p.stat().st_size).encode())
    probe["digest"] = digest.hexdigest()
    probe["num_files"] = len(files)
    meta = latest / ".metadata"
    try:
        if meta.is_file():
            metadata = read_dcp_metadata(latest)
            n = len(getattr(metadata, "state_dict_metadata", {}) or {})
            probe["reloaded"] = True
            probe["note"] = f"dcp metadata ok: {n} state_dict entries"
        else:
            # 非 torch_dist 布局：以首个 .pt 可反序列化为 reload 判据
            cand = next((p for p in files if p.suffix == ".pt"), None)
            if cand is not None:
                import torch  # noqa: PLC0415

                torch.load(cand, map_location="cpu", weights_only=False)
                probe["reloaded"] = True
                probe["reload_mode"] = "tracker+file-manifest+torch_load_pt"
            else:
                probe["note"] = "未找到 .metadata/.pt，无法结构化 reload"
    except Exception as exc:  # noqa: BLE001 - 探针如实记录失败，不吞
        probe["note"] = f"reload 失败: {exc!r}"
    if probe["saved"] and probe["reloaded"]:
        import shutil  # noqa: PLC0415

        shutil.rmtree(ckpt)
        probe["deleted"] = not ckpt.exists()
    return probe


# ---------------------------------------------------------------------------
# shutdown 探针（PR-P0-3B）
# ---------------------------------------------------------------------------

def _docker_ps_names(docker_bin: str, filter_arg: str, detail: dict, tag: str) -> list[str] | None:
    """一次 `docker ps`（只查仍在运行的容器）；失败返回 None 并写 detail。

    已退出未删除容器（docker ps -a）留作 P1，见模块 docstring。
    """
    try:
        r = subprocess.run(
            [docker_bin, "ps", "--filter", filter_arg, "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as exc:  # noqa: BLE001 - 失败是显式事实（query_ok=false），不是零
        detail[f"docker_error_{tag}"] = repr(exc)
        return None
    if r.returncode != 0:
        detail[f"docker_rc_{tag}"] = r.returncode
        detail[f"docker_stderr_{tag}"] = r.stderr[-500:]
        return None
    return [x for x in r.stdout.splitlines() if x.strip()]


def shutdown_probe(
    artifacts: Path, docker_bin: str, execution_mode: str, run_id: str | None = None
) -> dict:
    probe = {
        "execution_mode": execution_mode,
        "docker_query_ok": False,
        "ray_query_ok": False,
        "docker_orphan_containers": None,
        "ray_alive_actors": None,
        "orphan_workers": None,
        "finalization": {"status": None, "unfinalized": None},
        "detail": {},
    }

    # 孤儿 sandbox 容器：**rollout 与评分容器都查**（租前聚焦修复批 #4——
    # 旧探针只查 name=rh2-rollout，G1 真实评分容器名前缀是 rh2-grading
    # （grading/manager.py GradingManagerConfig.name_prefix），仅遗留一个
    # 评分容器时曾报 orphan_workers=0）。优先本 run 的 owner label：
    # launch 下发 MILES_RH2_RUN_ID 后，rollout（adapters/slime/generate.py）
    # 与评分（grading/manager.py）容器都带 label rh2.run_id=<run_id>，
    # --run-id 给定时按 label 精确匹配本 run；name 前缀查询同时保留，兜住
    # 无 label 的旧容器/异常路径。三路查询任一失败 = docker_query_ok=false
    # （查询失败 ≠ 观测为零，PR-P0-3B 语义不变）。
    # docker 二进制 = preflight 验证过的那一个（--docker-bin），不取 PATH。
    detail = probe["detail"]
    queries = [
        ("rollout_name", "name=rh2-rollout"),
        ("grading_name", "name=rh2-grading"),
    ]
    if run_id:
        queries.append(("run_label", f"label=rh2.run_id={run_id}"))
    results = {tag: _docker_ps_names(docker_bin, flt, detail, tag) for tag, flt in queries}
    if all(v is not None for v in results.values()):
        probe["docker_query_ok"] = True
        probe["docker_orphan_containers"] = sorted({name for v in results.values() for name in v})
        probe["detail"]["docker_matches"] = {tag: v for tag, v in results.items()}

    # 作业结束后仍存活的 miles Ray actor
    try:
        r = subprocess.run(
            ["ray", "list", "actors", "--filter", "state=ALIVE", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if r.returncode == 0:
            alive = [a.get("class_name") for a in json.loads(r.stdout or "[]")]
            probe["ray_query_ok"] = True
            probe["ray_alive_actors"] = [
                c for c in alive if c and ("Train" in c or "Rollout" in c or "SGLang" in c)
            ]
        else:
            probe["detail"]["ray_rc"] = r.returncode
            probe["detail"]["ray_stderr"] = r.stderr[-500:]
    except Exception as exc:  # noqa: BLE001
        probe["detail"]["ray_error"] = repr(exc)

    if probe["docker_query_ok"] and probe["ray_query_ok"]:
        probe["orphan_workers"] = len(probe["docker_orphan_containers"]) + len(probe["ray_alive_actors"])

    # finalization store：s1_compat 下 bringup 有意不注入 FileFinalizationStore
    # （receipt 语义 fa_audit_only 起生效）——如实 not_applicable，不冒充零。
    attempts = artifacts / "finalization" / "attempts"
    if execution_mode == "s1_compat":
        probe["finalization"]["status"] = "not_applicable"
        probe["detail"]["finalization_note"] = (
            "s1_compat 不创建 FileFinalizationStore（bringup 注入条件 EXECUTION_MODE != s1_compat）；"
            "内存 pending draft 无 durable receipt 可查，此项不构成 F5 收口证据"
        )
    elif not attempts.is_dir():
        probe["finalization"]["status"] = "absent_required"
    else:
        unfinalized = [
            p.name for p in attempts.iterdir() if p.is_dir() and not (p / "receipt.json").is_file()
        ]
        probe["finalization"]["unfinalized"] = unfinalized[:20]
        probe["finalization"]["num_unfinalized"] = len(unfinalized)
        probe["finalization"]["status"] = "ok_empty" if not unfinalized else "unfinalized"
    return probe


def shutdown_probe_ok(probe: dict) -> bool:
    return bool(
        probe.get("docker_query_ok")
        and probe.get("ray_query_ok")
        and probe.get("orphan_workers") == 0
        and probe.get("finalization", {}).get("status") in FINALIZATION_OK_STATUSES
    )


# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    pc = sub.add_parser("checkpoint")
    pc.add_argument("--ckpt", required=True)
    pc.add_argument("--out", required=True)
    ps = sub.add_parser("shutdown")
    ps.add_argument("--artifacts", required=True)
    ps.add_argument("--out", required=True)
    ps.add_argument("--docker-bin", required=True)
    ps.add_argument("--execution-mode", required=True)
    ps.add_argument("--run-id", default=None,
                    help="本 run 的唯一 id；给定时按容器 label rh2.run_id=<id> 精确匹配本 run 遗留容器")
    args = parser.parse_args(argv)

    if args.cmd == "checkpoint":
        probe = checkpoint_probe(Path(args.ckpt))
        ok = probe["saved"] and probe["reloaded"] and probe["deleted"]
    else:
        probe = shutdown_probe(
            Path(args.artifacts), args.docker_bin, args.execution_mode, run_id=args.run_id
        )
        ok = shutdown_probe_ok(probe)
    Path(args.out).write_text(json.dumps(probe, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(probe, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
