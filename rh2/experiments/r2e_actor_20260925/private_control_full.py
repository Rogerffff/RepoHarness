"""私有对照的全量输出版（不交给求解者）：与任务二的 private_control.py 同一做法——派生镜像的一次性容器、
不联网、root，只应用 gold 的源码段（排除测试文件），按命令清单的指定 id 执行——但保存每条命令的完整输出
（各自上限 200k 字符），用于 800 字符尾部截断了退出码行或关键行的情况。
用法：private_control_full.py --image IMG --gold gold.patch|none --commands commands/X.json --ids a,b --out out.json
--gold none 表示不应用补丁（base）。
"""
import argparse
import json
import subprocess
import uuid

CAP = 200_000
ap = argparse.ArgumentParser()
ap.add_argument("--image", required=True)
ap.add_argument("--gold", required=True)
ap.add_argument("--commands", required=True)
ap.add_argument("--ids", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--python-prefix", default="/testbed/.venv")
ns = ap.parse_args()
cmds = {c["id"]: c for c in json.load(open(ns.commands))}
name = f"rh2-r2e-privfull-{uuid.uuid4().hex[:10]}"
dk = lambda *a, **k: subprocess.run(["docker", *a], capture_output=True, text=True, errors="replace", **k)  # noqa: E731
res = {"image": ns.image, "gold": ns.gold, "user": "root", "network": "none", "results": {}}
try:
    assert dk("run", "-d", "--name", name, "--network", "none", "--label", "rh2.b_r2e=private_control_full",
              "--entrypoint", "sleep", ns.image, "infinity").returncode == 0
    if ns.gold != "none":
        dk("cp", ns.gold, f"{name}:/tmp/gold.patch")
        ap_ = dk("exec", name, "bash", "-c", "cd /testbed && git apply --exclude='tests/*' --exclude='*/tests/*' --exclude='test_*' -v /tmp/gold.patch 2>&1 | tail -5; echo rc=${PIPESTATUS[0]}")
        res["apply"] = ap_.stdout
    for cid in ns.ids.split(","):
        c = cmds[cid]
        r = dk("exec", "-e", f"PATH={ns.python_prefix}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "-w", "/testbed", name,
               "timeout", str(c.get("timeout_s", 300)), "bash", "-c", c["cmd"])
        res["results"][cid] = {"rc": r.returncode, "cmd": c["cmd"], "stdout": r.stdout[-CAP:], "stderr": r.stderr[-CAP:],
                               "truncated": len(r.stdout) > CAP or len(r.stderr) > CAP}
finally:
    dk("rm", "-f", name)
json.dump(res, open(ns.out, "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v["rc"] for k, v in res["results"].items()}), res.get("apply", "")[-200:])
