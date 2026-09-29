"""包索引网关对真实上游的冒烟（本机 macOS，非目标机；组件级，不是 grader 联网验收）。

1. devpi-server（临时 venv，`root/pypi` 镜像缓存）作上游：pip 冷 / 热各下一次同一个包（第二次换新 token、devpi 已缓存）；
   sdist 也走一次；被 1A 封禁的项目被拒；uv 用同一网关做一次解析。
2. 直连 PyPI 作上游（文件来源 files.pythonhosted.org）：pip `install --dry-run` 解析一个带依赖的包——PyPI 页面声明了
   PEP 658 元数据，验证网关的 `.metadata` 路由被真实客户端用到。
3. 汇总：各次 rc / 墙钟、网关日志的判定计数、devpi / pip / uv 版本；写 `<out>/smoke_result.json`。token 不落盘。

用法（仓库根）：rh2/.venv/bin/python rh2/experiments/batch6_network_20260924/gateway_real_upstream_smoke.py --out runs/<dir>
需要：出网到 pypi.org；uv；系统 python3 带 pip。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import socket
import sys
import time
from collections import Counter
from pathlib import Path

import aiohttp

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "rh2" / "src"))

from repoharness2.adapters.slime.pkg_index_gateway import PackageIndexGateway, SupplyGrant  # noqa: E402

PIP_PYTHON = shutil.which("python3")
UV = shutil.which("uv")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _run(*cmd: str, env: dict | None = None, stdin: bytes | None = None, timeout: float = 600) -> dict:
    started = time.monotonic()
    proc = await asyncio.create_subprocess_exec(
        *cmd, env=env, stdin=asyncio.subprocess.PIPE if stdin is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await asyncio.wait_for(proc.communicate(stdin), timeout=timeout)
    return {"rc": proc.returncode, "seconds": round(time.monotonic() - started, 2), "tail": out.decode(errors="replace")[-1500:]}


def _pip_env(tmp: Path) -> dict:
    return {**os.environ, "PIP_CONFIG_FILE": os.devnull, "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_INPUT": "1",
            "HOME": str(tmp / "home")}


async def _wait_http(url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    async with aiohttp.ClientSession() as s:
        while time.monotonic() < deadline:
            try:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                    if resp.status < 500:
                        return
            except (aiohttp.ClientError, asyncio.TimeoutError):
                pass
            await asyncio.sleep(0.5)
    raise TimeoutError(f"{url} 在 {timeout}s 内没有就绪")


def _decisions(log: Path) -> dict:
    rows = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    return {"by_kind_decision": dict(Counter(f"{r['kind']}:{r['decision']}" for r in rows)), "rows": len(rows)}


async def main(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "work"
    (tmp / "home").mkdir(parents=True, exist_ok=True)
    result: dict = {"platform": sys.platform, "note": "本机组件冒烟：非目标机、非 grader 联网流程"}
    assert PIP_PYTHON and UV, "需要系统 python3（带 pip）与 uv"
    result["pip"] = (await _run(PIP_PYTHON, "-m", "pip", "--version"))["tail"].strip()
    result["uv"] = (await _run(UV, "--version"))["tail"].strip()

    # ---- devpi-server（临时 venv）
    venv = tmp / "devpi-venv"
    if not (venv / "bin" / "devpi-server").exists():
        r = await _run(UV, "venv", str(venv), "--python", "3.12", "-q")
        assert r["rc"] == 0, r
        r = await _run(UV, "pip", "install", "--python", str(venv / "bin" / "python"), "-q", "devpi-server", timeout=900)
        assert r["rc"] == 0, r
    result["devpi_server"] = (await _run(str(venv / "bin" / "devpi-server"), "--version"))["tail"].strip()
    serverdir = tmp / "devpi-data"
    if not serverdir.exists():
        r = await _run(str(venv / "bin" / "devpi-init"), "--serverdir", str(serverdir))
        assert r["rc"] == 0, r
    devpi_port = _free_port()
    devpi_log = (out / "devpi-server.log").open("w")
    devpi = await asyncio.create_subprocess_exec(
        str(venv / "bin" / "devpi-server"), "--serverdir", str(serverdir), "--host", "127.0.0.1", "--port", str(devpi_port),
        stdout=devpi_log, stderr=asyncio.subprocess.STDOUT,
    )
    gw_devpi = PackageIndexGateway(upstream_simple_url=f"http://127.0.0.1:{devpi_port}/root/pypi/+simple/",
                                   log_path=out / "gateway_devpi.jsonl")
    gw_pypi = PackageIndexGateway(upstream_simple_url="https://pypi.org/simple/", file_origins=["https://files.pythonhosted.org"],
                                  log_path=out / "gateway_pypi.jsonl")
    try:
        await _wait_http(f"http://127.0.0.1:{devpi_port}/+api", 120)
        port_devpi = await gw_devpi.start("127.0.0.1", 0)
        port_pypi = await gw_pypi.start("127.0.0.1", 0)
        env = _pip_env(tmp)

        def grant(attempt: str, blocked=("requests",)) -> SupplyGrant:
            return SupplyGrant.build(attempt_id=attempt, task_id="smoke", plane="grading", phase="install", blocked_dists=blocked)

        def index(gw: PackageIndexGateway, port: int, token: str) -> str:
            return f"http://127.0.0.1:{port}{gw.index_path(token)}"

        steps: dict = {}
        cold = gw_devpi.issue(grant("devpi-cold"))
        steps["devpi_pip_cold_six_wheel"] = await _run(
            PIP_PYTHON, "-m", "pip", "download", "--no-deps", "--no-cache-dir", "--index-url", index(gw_devpi, port_devpi, cold),
            "-d", str(tmp / "d_cold"), "six==1.16.0", env=env)
        hot = gw_devpi.issue(grant("devpi-hot"))
        steps["devpi_pip_hot_six_wheel"] = await _run(
            PIP_PYTHON, "-m", "pip", "download", "--no-deps", "--no-cache-dir", "--index-url", index(gw_devpi, port_devpi, hot),
            "-d", str(tmp / "d_hot"), "six==1.16.0", env=env)
        steps["devpi_pip_sdist_six"] = await _run(
            PIP_PYTHON, "-m", "pip", "download", "--no-deps", "--no-cache-dir", "--no-binary", ":all:",
            "--index-url", index(gw_devpi, port_devpi, hot), "-d", str(tmp / "d_sdist"), "six==1.16.0", env=env)
        steps["devpi_pip_blocked_requests"] = await _run(
            PIP_PYTHON, "-m", "pip", "download", "--no-deps", "--no-cache-dir", "--index-url", index(gw_devpi, port_devpi, hot),
            "-d", str(tmp / "d_blocked"), "requests", env=env)
        steps["devpi_uv_compile_six"] = await _run(
            UV, "pip", "compile", "-", "--index-url", index(gw_devpi, port_devpi, hot), "--no-cache", "--python-version", "3.12",
            "-q", env={**env, "UV_NO_CONFIG": "1"}, stdin=b"six==1.16.0\n")
        pypi = gw_pypi.issue(grant("pypi-direct", blocked=("moto",)))
        steps["pypi_pip_dry_run_resolve_rich"] = await _run(
            PIP_PYTHON, "-m", "pip", "install", "--dry-run", "--ignore-installed", "--no-cache-dir",
            "--index-url", index(gw_pypi, port_pypi, pypi), "--report", str(tmp / "rich_report.json"), "rich==13.7.1", env=env)
        steps["pypi_pip_blocked_moto"] = await _run(
            PIP_PYTHON, "-m", "pip", "download", "--no-deps", "--no-cache-dir", "--index-url", index(gw_pypi, port_pypi, pypi),
            "-d", str(tmp / "d_moto"), "moto", env=env)
        for name, step in steps.items():
            step["ok"] = step["rc"] == 0
        result["steps"] = steps
        report = tmp / "rich_report.json"
        if report.exists():
            result["rich_resolution"] = sorted(f"{i['metadata']['name']}=={i['metadata']['version']}"
                                               for i in json.loads(report.read_text())["install"])
        for gw, token in ((gw_devpi, cold), (gw_devpi, hot), (gw_pypi, pypi)):
            gw.withdraw(token)
            summary = await gw.release(token)
            result.setdefault("token_summaries", []).append(summary)
    finally:
        await gw_devpi.stop()
        await gw_pypi.stop()
        devpi.terminate()
        try:
            await asyncio.wait_for(devpi.wait(), timeout=30)
        except asyncio.TimeoutError:
            devpi.kill()
        devpi_log.close()
    result["gateway_devpi_log"] = _decisions(out / "gateway_devpi.jsonl")
    result["gateway_pypi_log"] = _decisions(out / "gateway_pypi.jsonl")
    tokens_in_logs = any(t in (out / f).read_text() for t in (cold, hot, pypi) for f in ("gateway_devpi.jsonl", "gateway_pypi.jsonl"))
    result["token_leaked_into_logs"] = tokens_in_logs
    (out / "smoke_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ns = ap.parse_args()
    res = asyncio.run(main(Path(ns.out)))
    print(json.dumps({k: v for k, v in res.items() if k not in ("token_summaries",)}, ensure_ascii=False, indent=1)[:6000])
