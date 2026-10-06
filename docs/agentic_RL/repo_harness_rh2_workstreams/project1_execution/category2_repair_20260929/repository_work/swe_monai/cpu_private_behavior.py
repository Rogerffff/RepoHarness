# 本包隔离适配：仅追加作业身份/标签；原行为辅助脚本 SHA256 379c4610b19aafa829fcf7967ad95d0ac9f5374c9e85f16c0b62a01a25cbb7bc
"""本批私有确定性行为对照。不是 actor 权限证明，也不是正式评分。

消费已有 semantic_control 的 spec 形状；补齐准备失败停止、完整输出、有界调用和清理核对。
输入中的 gold/错误候选只进入这个私有容器，绝不挂载到 devcheck/模型容器。
"""
import argparse
import hashlib
import json
import re
import signal
import subprocess
import time
import uuid
from pathlib import Path


def main():
    def interrupted(signum, _frame):
        raise SystemExit(128 + signum)

    # systemd 的正常停止先发送 TERM；确保仍进入容器 finally 收尾。
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("spec")
    parser.add_argument("--out", required=True)
    ns = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,100}", ns.run_id):
        parser.error("unsafe run id")
    spec_path = Path(ns.spec)
    spec = json.loads(spec_path.read_text())
    out = Path(ns.out)
    out.mkdir(parents=True, exist_ok=False)
    summary = {"scope": "private root unit diagnosis only; not actor or formal grading", "run_id": ns.run_id, "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
               "started_at": time.time(), "variants": {}}
    image = json.loads(subprocess.check_output(["docker", "image", "inspect", spec["image"]], timeout=30))[0]
    summary["image_id_actual"] = image["Id"]
    for variant, steps in spec["variants"].items():
        dest = out / variant
        dest.mkdir()
        name = "rh2-monai-private-" + ns.run_id + "-" + uuid.uuid4().hex[:8]
        record = {"container": name, "started_at": time.time(), "preparation": [], "commands": []}
        summary["variants"][variant] = record

        def save():
            (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")

        def dk(*args, timeout=120, check=True):
            result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)
            if check and result.returncode:
                raise RuntimeError(f"docker {args[:2]} rc={result.returncode}: {(result.stderr or result.stdout)[-1500:]}")
            return result

        def shell(command, timeout=120):
            prefix = spec.get("python_prefix", "/opt/miniconda3/envs/testbed")
            return dk("exec", "-e", f"PATH={prefix}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                      "-w", "/testbed", name, "timeout", "-k", "10", str(timeout), "bash", "-c", command,
                      timeout=timeout + 30, check=False)

        try:
            dk("run", "-d", "--name", name, "--network", "none", "--init", "--cpus", str(spec.get("cpus", 2)),
               "--memory", spec.get("memory", "8g"), "--pids-limit", "512", "--label", "rh2.run_id=" + ns.run_id, "--label", "rh2.package=swe_monai",
               "--entrypoint", "sleep", image["Id"], "infinity")
            dk("exec", name, "mkdir", "-p", "/in")
            for fn, source in spec.get("files", {}).items():
                if Path(fn).name != fn:
                    raise ValueError("input filename must be a basename")
                dk("cp", source, f"{name}:/in/{fn}")
            facts = shell("id; git rev-parse HEAD; git status --porcelain")
            (dest / "initial.txt").write_text(facts.stdout + facts.stderr)
            for index, step in enumerate(steps):
                result = shell(step, timeout=600)
                (dest / f"prep_{index}.out").write_text(result.stdout + result.stderr)
                record["preparation"].append({"step": step, "rc": result.returncode})
                save()
                if result.returncode:
                    raise RuntimeError(f"preparation {index} failed; behavior not executed")
            for command in spec["commands"]:
                cid = command["id"]
                if Path(cid).name != cid:
                    raise ValueError("command id must be a basename")
                start = time.monotonic()
                result = shell(command["cmd"], timeout=int(command.get("timeout_s", 300)))
                (dest / f"{cid}.out").write_text(result.stdout + result.stderr)
                record["commands"].append({"id": cid, "rc": result.returncode, "seconds": time.monotonic() - start,
                                           "stdout_bytes": len(result.stdout.encode()), "stderr_bytes": len(result.stderr.encode())})
                save()
            record["status"] = "executed_interpret_separately"
        except BaseException as exc:
            record["status"] = "execution_error"
            record["error"] = repr(exc)
            raise
        finally:
            removed = dk("rm", "-f", name, timeout=120, check=False)
            remaining = dk("ps", "-a", "--filter", f"name=^/{name}$", "--format", "{{.Names}}", check=False)
            record["cleanup"] = {"rm_rc": removed.returncode, "query_rc": remaining.returncode,
                                  "remaining": remaining.stdout.split(), "stderr": removed.stderr[-1000:]}
            record["finished_at"] = time.time()
            save()
            if remaining.returncode or remaining.stdout.strip():
                raise RuntimeError("private container cleanup unconfirmed; stop dispatch")
    summary["finished_at"] = time.time()
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
