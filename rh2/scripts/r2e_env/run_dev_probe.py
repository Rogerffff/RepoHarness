#!/usr/bin/env python3
"""R2E 派生镜像上的"求解者开发条件"探针（宿主 runner）。

目的：回答 40 项清单第 8 / 10 项在 R2E 上的问题——以**真实解题身份**（agent/54321，HOME=/home/agent，cwd=/testbed，
容器由派生镜像按 rollout profile 的资源与能力启动、无网络）能否：执行 `.venv` 解释器、导入本仓库包、运行 pytest 与
仓库自带的公开测试、写工作区 / 包环境、看不到隐藏测试与修复提交；可选运行 sub-agent 按公开题面写的复现脚本。

与正式链的关系：容器初始化逐字复用 `rollout_trusted_init_script` 的步骤（建 agent 用户、safe.directory、
`chown -R /home/agent` 与 `/testbed`、`install -d /rh2`），执行方式与正式链一样是 `docker exec -u 54321`
（进程继承镜像 ENV：PATH 里 `.venv/bin` 在前、VIRTUAL_ENV=/testbed/.venv）。`--activation` 可额外写 `/rh2/bash_env`
并注入 BASH_ENV（正式链 #1 的运输方式），用来对照"R2E 该给什么激活内容"——这只是 CPU 侧证据，正式 actor 接入
（D4=B）与真实 CC 验证归 A 线。网络用 `--network none`（正式链是每 attempt 的隔离内网 + relay；对"无出网"的
判断等价，对 relay 可达性不作结论）。

输出：`<out-dir>/<iid>/dev_probe.json`（结构化）、`root_init.log`、`agent_probe.log`、`container.json`；`<out-dir>/summary.json`。
容器名 `rh2-devprobe-<iid12>-<8hex>`，结束一律 `docker rm -f`；`--keep-container` 仅调试。
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2] / "src"))

from repoharness2.adapters.slime.r2e_grading_scripts import _R2E_IMPORT_PROBE_MODULES  # noqa: E402
from repoharness2.envpack.environment_overlay import load_environment_overlays  # noqa: E402
from repoharness2.envpack.ingest_r2e_subset import load_trusted_r2e_ingest_outputs  # noqa: E402

import re  # noqa: E402

AGENT_UID = 54321
AGENT_USER = "agent"
# 键名以大写字母开头、后面允许小写（`WHICH_python` / `WHICH_xvfb-run`）；P1 sub-agent 09-24 指出旧正则丢掉了 WHICH_* 行
_KV_RE = re.compile(r"^[A-Z][A-Za-z0-9_.-]*=")
PARSER_VERSION = 3
TRUSTED_INIT_CAPS = ("CHOWN", "DAC_OVERRIDE", "DAC_READ_SEARCH", "FOWNER", "KILL")
ACTIVATIONS = {
    "none": None,
    # 建议给 R2E 任务面的激活内容（.venv；不依赖 conda）——探针用它对照，正式采用归 A 线任务面
    "r2e_venv": "# rh2 envpack (r2e): activate the project's uv virtualenv for every non-interactive bash\n"
                "export VIRTUAL_ENV=/testbed/.venv\ncase \":$PATH:\" in *\":/testbed/.venv/bin:\"*) ;; *) export PATH=\"/testbed/.venv/bin:$PATH\" ;; esac\n",
    # 当前 materialize.BASH_ENV_CONTENT（swe_gym_lite 的 conda 形态）——R2E 镜像没有 conda，看它是否无害
    "swe_conda": "# rh2 envpack: 让 agent 的每个非交互 bash 命令都运行在 conda testbed 环境里。\n"
                 "source /opt/miniconda3/bin/activate testbed 2>/dev/null || true\n",
}

ROOT_INIT = r"""#!/bin/bash
set -u
T0=$(date +%s.%N)
U=agent; UIDV=54321
if ! id -u "$U" >/dev/null 2>&1; then
  getent group "$UIDV" >/dev/null 2>&1 || groupadd -g "$UIDV" "$U"
  useradd -M -u "$UIDV" -g "$UIDV" -s /bin/bash -d "/home/$U" "$U"
fi
ACT=$(id -u "$U")
if [ "$ACT" != "$UIDV" ]; then echo "RH2_INIT_ERROR=uid_mismatch:$ACT"; exit 3; fi
mkdir -p "/home/$U"
git config --system --add safe.directory '*' >/dev/null 2>&1 || true
chown -R "$UIDV:$UIDV" "/home/$U" || { echo "RH2_INIT_ERROR=chown_home_failed"; exit 4; }
install -d -m 0755 -o 0 -g 0 /rh2 || { echo "RH2_INIT_ERROR=rh2_dir_failed"; exit 4; }
T1=$(date +%s.%N)
if [ -d /testbed ]; then
  chown -R "$UIDV:$UIDV" /testbed || { echo "RH2_INIT_ERROR=chown_workdir_failed"; exit 4; }
  echo "WORKDIR_PRESENT=1"
else
  echo "WORKDIR_PRESENT=0"
fi
T2=$(date +%s.%N)
echo "CHOWN_WORKDIR_SECONDS=$(awk "BEGIN{printf \"%.2f\", $T2-$T1}")"
echo "TESTBED_OWNER_AFTER=$(stat -c %u:%g /testbed 2>/dev/null)"
echo "RH2_INIT_OK=1"; echo "AGENT_UID=$ACT"
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _run(args: list[str], *, timeout: float, input_bytes: bytes | None = None) -> tuple[int, str, str]:
    try:
        p = subprocess.run(args, input=input_bytes, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return 124, (exc.stdout or b"").decode(errors="replace"), f"timeout after {timeout}s"
    return p.returncode, p.stdout.decode(errors="replace"), p.stderr.decode(errors="replace")


def _docker_write(container: str, path: str, content: str, *, mode: str = "0644") -> None:
    script = f"cat > {shlex.quote(path)} && chmod {mode} {shlex.quote(path)} && chown 0:0 {shlex.quote(path)}"
    rc, _, err = _run(["docker", "exec", "-i", container, "bash", "-c", script], timeout=60, input_bytes=content.encode())
    if rc != 0:
        raise RuntimeError(f"write {path} failed rc={rc}: {err[:300]}")


def _parse_kv_blocks(text: str) -> tuple[dict[str, str], dict[str, str]]:
    kv: dict[str, str] = {}
    blocks: dict[str, str] = {}
    cur: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        if cur is not None:
            if line == f"@@END {cur}":
                blocks[cur] = "\n".join(buf).rstrip("\n")
                cur, buf = None, []
            else:
                buf.append(line)
            continue
        if line.startswith("@@BEGIN "):
            cur, buf = line[len("@@BEGIN "):], []
        elif _KV_RE.match(line):
            k, _, v = line.partition("=")
            kv[k] = v
    if cur is not None:
        blocks[cur] = "\n".join(buf).rstrip("\n") + "\n[block unterminated]"
    return kv, blocks


def _derive(kv: dict[str, str], blocks: dict[str, str]) -> dict:
    def ok_rc(key: str) -> bool | None:
        v = kv.get(key)
        return None if v in (None, "", "n/a") else v == "0"

    d = {
        "interpreter_isolated_ok": ok_rc("PY_ISOLATED_RC"),
        "python_resolves_to_venv": (kv.get("PY_INFO", "").startswith("/testbed/.venv/bin/python")),
        "pytest_ok": ok_rc("PYTEST_RC"),
        "import_from_testbed_ok": ok_rc("IMPORT_FROM_TESTBED_RC"),
        "import_from_testbed_path_in_testbed": kv.get("IMPORT_FROM_TESTBED", "").startswith("/testbed"),
        "import_from_tmp_ok": ok_rc("IMPORT_FROM_TMP_RC"),
        # "No module named pip" 也含 "pip"——P4 sub-agent 09-24 指出旧判断恒 true；改为看 `pip <版本> from …` 形态
        "pip_ok": kv.get("PIP_VERSION", "").startswith("pip "),
        "pip_check_ok": ok_rc("PIP_CHECK_RC"),
        "writable_testbed": kv.get("WRITE_TESTBED") == "ok",
        "writable_site_packages": kv.get("WRITE_SITE") == "ok",
        "writable_home": kv.get("WRITE_HOME") == "ok",
        "writable_tmp": kv.get("WRITE_TMP") == "ok",
        "root_fs_readonly_for_agent": kv.get("WRITE_ROOT_FS") == "denied",
        "hidden_tests_denied": ("denied" in kv.get("PRIVATE_LS", "").lower() or "permission" in kv.get("PRIVATE_LS", "").lower())
                               and kv.get("R2E_TESTS_ROOT") == "absent" and kv.get("R2E_TESTS_WORKDIR") == "absent",
        "git_head_has_no_children": kv.get("GIT_HEAD_CHILDREN_WORDS") == "1",
        "git_no_remotes": kv.get("GIT_REMOTES", "") == "",
        "git_reflog_empty": kv.get("GIT_REFLOG_COUNT") == "0",
        "stray_patch_files": [l for l in blocks.get("STRAY_PATCH_FILES", "").splitlines() if l.strip()],
        "public_test_file": kv.get("PUBLIC_TEST_FILE") or None,
        "public_collect_ok": ok_rc("PUBLIC_COLLECT_RC"),
        "public_run_rc": kv.get("PUBLIC_RUN_RC"),
        "repro_rc": kv.get("REPRO_RC"),
        "network_blocked": kv.get("NET_CONNECT_RC") not in (None, "0"),
        "git_status_count_before_after": [kv.get("GIT_STATUS_COUNT"), kv.get("GIT_STATUS_COUNT_AFTER")],
        "probe_completed": kv.get("PROBE_DONE") == "1",
    }
    core = ["interpreter_isolated_ok", "python_resolves_to_venv", "pytest_ok", "import_from_testbed_ok",
            "import_from_testbed_path_in_testbed", "writable_testbed", "hidden_tests_denied", "git_head_has_no_children",
            "network_blocked", "probe_completed"]
    d["min_dev_conditions_ok"] = all(d[k] is True for k in core)
    d["min_dev_conditions_failed"] = [k for k in core if d[k] is not True]
    return d


def reparse_dir(out_dir: Path) -> list[dict]:
    """只用已落盘的 `agent_probe.log` / `root_init.log` 重建每题的 `dev_probe.json`（解析器修正后补字段，不重跑容器）。
    保留原 JSON 的身份、时间与 timings；`agent` / `root_init` / `derived` 按当前解析器重算；记 `reparsed_at_utc` 与 `parser_version`。"""

    rows = []
    for d in sorted(p for p in out_dir.iterdir() if p.is_dir()):
        jp, ap, rp = d / "dev_probe.json", d / "agent_probe.log", d / "root_init.log"
        if not (jp.is_file() and ap.is_file()):
            continue
        res = json.loads(jp.read_text(encoding="utf-8"))
        agent_text = ap.read_text(encoding="utf-8", errors="replace").split("\n[stderr]\n", 1)[0]
        kv, blocks = _parse_kv_blocks(agent_text)
        exec_rc = (res.get("agent") or {}).get("exec_rc")
        res["agent"] = {"exec_rc": exec_rc, "values": kv, "blocks": blocks}
        if rp.is_file():
            init_kv, _ = _parse_kv_blocks(rp.read_text(encoding="utf-8", errors="replace").split("\n[stderr]\n", 1)[0])
            res["root_init"] = {"rc": (res.get("root_init") or {}).get("rc"), **init_kv}
        res["derived"] = _derive(kv, blocks)
        res["ok"] = res["derived"]["probe_completed"] if not res.get("error") else False
        res["reparsed_at_utc"] = _now()
        res["parser_version"] = PARSER_VERSION
        jp.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        rows.append({"instance_id": res.get("instance_id"), "which_keys": sorted(k for k in kv if k.startswith("WHICH_")),
                     "min_dev_conditions_ok": res["derived"]["min_dev_conditions_ok"]})
    return rows


def probe_one(*, iid: str, task_id: str, image_id: str, module: str, module_dir: str, prefix: str,
              activation: str, repro: Path | None, out_dir: Path, keep: bool, cpus: float, memory_bytes: int,
              tmp_bytes: int, home_bytes: int, pids: int) -> dict:
    task_out = out_dir / iid
    task_out.mkdir(parents=True, exist_ok=True)
    name = f"rh2-devprobe-{iid.split('__')[1][:12]}-{secrets.token_hex(4)}"
    result: dict = {"schema_id": "rh2.r2e_dev_probe.v1", "parser_version": PARSER_VERSION, "instance_id": iid, "task_id": task_id, "image_id": image_id,
                    "container": name, "activation": activation, "module": module, "runner_prefix": prefix,
                    "repro": str(repro) if repro else None, "started_at_utc": _now(), "timings": {}, "ok": False}
    t0 = time.monotonic()
    rc, out, err = _run(["docker", "image", "inspect", "-f", "{{.Id}}", image_id], timeout=60)
    if rc != 0 or out.strip() != image_id:
        result["error"] = f"image_id_mismatch_or_missing: {out.strip()[:80]} {err[:120]}"
        return result
    args = ["docker", "run", "--detach", "--init", "--network", "none", "--cap-drop", "ALL"]
    for cap in TRUSTED_INIT_CAPS:
        args += ["--cap-add", cap]
    args += ["--security-opt", "no-new-privileges", "--pids-limit", str(pids), "--cpus", f"{cpus:g}",
             "--memory", str(memory_bytes), "--memory-swap", str(memory_bytes),
             "--tmpfs", f"/tmp:size={tmp_bytes},mode=1777",
             "--tmpfs", f"/home/{AGENT_USER}:size={home_bytes},mode=0750,uid={AGENT_UID},gid={AGENT_UID}",
             "--label", "rh2.role=devprobe", "--name", name, image_id, "sleep", "infinity"]
    rc, out, err = _run(args, timeout=120)
    if rc != 0:
        result["error"] = f"docker_run_failed rc={rc}: {err[:300]}"
        return result
    try:
        rc, insp, _ = _run(["docker", "inspect", name], timeout=60)
        (task_out / "container.json").write_text(insp, encoding="utf-8")
        t1 = time.monotonic()
        rc, out, err = _run(["docker", "exec", name, "bash", "-c", ROOT_INIT], timeout=900)
        (task_out / "root_init.log").write_text(out + ("\n[stderr]\n" + err if err else ""), encoding="utf-8")
        result["timings"]["root_init_seconds"] = round(time.monotonic() - t1, 2)
        init_kv, _ = _parse_kv_blocks(out)
        result["root_init"] = {"rc": rc, **init_kv}
        if rc != 0 or init_kv.get("RH2_INIT_OK") != "1":
            result["error"] = f"root_init_failed rc={rc}"
            return result
        _docker_write(name, "/rh2/dev_probe_agent.sh", (HERE.parent / "dev_probe_agent.sh").read_text(encoding="utf-8"))
        env = ["-e", f"HOME=/home/{AGENT_USER}", "-e", f"MODULE={module}", "-e", f"MODULE_DIR={module_dir}",
               "-e", f"PREFIX={prefix}"]
        if ACTIVATIONS.get(activation):
            _docker_write(name, "/rh2/bash_env", ACTIVATIONS[activation])
            env += ["-e", "BASH_ENV=/rh2/bash_env"]
        if repro is not None:
            _docker_write(name, "/rh2/repro.py", repro.read_text(encoding="utf-8"))
            env += ["-e", "REPRO=/rh2/repro.py"]
        t2 = time.monotonic()
        rc, out, err = _run(["docker", "exec", "-u", str(AGENT_UID), "-w", "/testbed", *env, name, "bash", "/rh2/dev_probe_agent.sh"], timeout=1800)
        (task_out / "agent_probe.log").write_text(out + ("\n[stderr]\n" + err if err else ""), encoding="utf-8")
        result["timings"]["agent_probe_seconds"] = round(time.monotonic() - t2, 2)
        kv, blocks = _parse_kv_blocks(out)
        result["agent"] = {"exec_rc": rc, "values": kv, "blocks": blocks}
        result["derived"] = _derive(kv, blocks)
        result["ok"] = result["derived"]["probe_completed"]
    finally:
        if not keep:
            _run(["docker", "rm", "-f", name], timeout=120)
            rc2, out2, _ = _run(["docker", "ps", "-a", "-q", "-f", f"name=^{name}$"], timeout=60)
            result["container_removed"] = (rc2 == 0 and out2.strip() == "")
        result["timings"]["total_seconds"] = round(time.monotonic() - t0, 2)
        result["finished_at_utc"] = _now()
        (task_out / "dev_probe.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo-root", default=None, help="含 s2_r2e 可信摄入面的仓库根（机器上 /work/code）；--reparse 不需要")
    ap.add_argument("--overlays", default=None, help="环境覆盖表 overlays.jsonl（派生镜像 ID）；--reparse 不需要")
    ap.add_argument("--reparse", action="store_true", help="只按当前解析器重建 <out-dir>/<iid>/dev_probe.json（不起容器）")
    ap.add_argument("--task-ids", default="", help="逗号分隔 instance_id 或 task_id；空 = --all")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--repro-dir", default=None, help="可选：<iid>.py 公开复现脚本目录（以 agent 身份在 /testbed 运行）")
    ap.add_argument("--activation", choices=sorted(ACTIVATIONS), default="none")
    ap.add_argument("--keep-container", action="store_true")
    ap.add_argument("--cpus", type=float, default=2.0)
    ap.add_argument("--memory-bytes", type=int, default=4 * 2**30)
    ap.add_argument("--tmp-bytes", type=int, default=1 * 2**30)
    ap.add_argument("--home-bytes", type=int, default=256 * 2**20)
    ap.add_argument("--pids-limit", type=int, default=512)
    args = ap.parse_args(argv)
    if args.reparse:
        rows = reparse_dir(Path(args.out_dir).resolve())
        for r in rows:
            print(f"[{r['instance_id']}] reparsed which={len(r['which_keys'])} min_ok={r['min_dev_conditions_ok']}")
        print(f"reparsed {len(rows)} tasks")
        return 0
    if not args.repo_root or not args.overlays:
        ap.error("--repo-root 与 --overlays 为必填（除非 --reparse）")

    repo_root = Path(args.repo_root).resolve()
    trusted = load_trusted_r2e_ingest_outputs(repo_root)
    grading = {b.instance_id: b for b in trusted.result.grading_bundles}
    packages = {p.instance_id: p for p in trusted.result.packages}
    overlays = load_environment_overlays(args.overlays)
    wanted = sorted(grading) if args.all or not args.task_ids else [
        x.split("::", 1)[1] if "::" in x else x for x in args.task_ids.split(",") if x.strip()]
    unknown = [x for x in wanted if x not in grading]
    if unknown:
        ap.error(f"未知 instance_id: {unknown}")
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    repro_dir = Path(args.repro_dir).resolve() if args.repro_dir else None
    rows = []
    for iid in wanted:
        g = grading[iid]
        task_id = packages[iid].task_id
        ov = overlays.get(task_id)
        if ov is None:
            rows.append({"instance_id": iid, "error": "no_overlay"})
            print(f"[{iid}] no overlay entry", flush=True)
            continue
        module = _R2E_IMPORT_PROBE_MODULES.get(g.repo_key_lower, g.repo_key_lower)
        # 包目录：pillow 用 src/PIL（3ac9 例外为 PIL）；其余等于导入名。只用于找公开测试目录，找不到就跳过。
        module_dir = {"pillow": "src/PIL", "orange3": "Orange", "coveragepy": "coverage"}.get(g.repo_key_lower, module)
        body = " ".join(l for l in g.run_tests_sh.splitlines() if l.strip() and not l.lstrip().startswith("#"))
        prefix = body.split(".venv/bin/python", 1)[0].strip() if ".venv/bin/python" in body else ""
        repro = (repro_dir / f"{iid}.py") if repro_dir and (repro_dir / f"{iid}.py").is_file() else None
        print(f"[{iid}] probe start image={ov.derived_image_id[:19]} activation={args.activation} repro={'yes' if repro else 'no'}", flush=True)
        res = probe_one(iid=iid, task_id=task_id, image_id=ov.derived_image_id, module=module, module_dir=module_dir,
                        prefix=prefix, activation=args.activation, repro=repro, out_dir=out_dir, keep=args.keep_container,
                        cpus=args.cpus, memory_bytes=args.memory_bytes, tmp_bytes=args.tmp_bytes, home_bytes=args.home_bytes,
                        pids=args.pids_limit)
        d = res.get("derived") or {}
        rows.append({"instance_id": iid, "ok": res.get("ok"), "error": res.get("error"),
                     "min_dev_conditions_ok": d.get("min_dev_conditions_ok"), "failed": d.get("min_dev_conditions_failed"),
                     "public_test_file": d.get("public_test_file"), "public_collect_ok": d.get("public_collect_ok"),
                     "public_run_rc": d.get("public_run_rc"), "repro_rc": d.get("repro_rc"),
                     "chown_workdir_seconds": (res.get("root_init") or {}).get("CHOWN_WORKDIR_SECONDS"),
                     "total_seconds": res["timings"].get("total_seconds"), "container_removed": res.get("container_removed")})
        print(f"[{iid}] done ok={res.get('ok')} min_ok={d.get('min_dev_conditions_ok')} failed={d.get('min_dev_conditions_failed')} "
              f"public={d.get('public_test_file')} collect={d.get('public_collect_ok')} run_rc={d.get('public_run_rc')} "
              f"repro_rc={d.get('repro_rc')} t={res['timings'].get('total_seconds')}s err={res.get('error')}", flush=True)
    summary = {"schema_id": "rh2.r2e_dev_probe_summary.v1", "generated_at_utc": _now(), "activation": args.activation,
               "profile": {"cpus": args.cpus, "memory_bytes": args.memory_bytes, "tmp_bytes": args.tmp_bytes,
                           "home_bytes": args.home_bytes, "pids_limit": args.pids_limit, "network": "none",
                           "caps": list(TRUSTED_INIT_CAPS)},
               "rows": rows}
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    bad = [r for r in rows if r.get("error") or r.get("min_dev_conditions_ok") is not True]
    print(f"probed {len(rows)} tasks; min_dev_conditions not ok / errors: {len(bad)}")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    raise SystemExit(main())
