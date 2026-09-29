"""私有对照（不交给求解者）：在 actor 镜像的一次性容器里应用 gold 源码段，按同一命令清单的指定 id 执行，
确认公开命令在"修好"时能过——即 base 上的失败来自目标缺陷而不是命令或环境。容器不联网、跑完即删。
用法：private_control.py --image IMG --gold gold.patch --commands commands/X.json --ids mcve_api,mcve_e2e --out out.json
"""
import argparse, json, subprocess, uuid

ap = argparse.ArgumentParser()
ap.add_argument("--image", required=True); ap.add_argument("--gold", required=True); ap.add_argument("--commands", required=True)
ap.add_argument("--ids", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--python-prefix", default="/opt/miniconda3/envs/testbed")
ns = ap.parse_args()
cmds = {c["id"]: c for c in json.load(open(ns.commands))}
name = f"rh2t2priv-{uuid.uuid4().hex[:10]}"
dk = lambda *a, **k: subprocess.run(["docker", *a], capture_output=True, text=True, **k)  # noqa: E731
res = {"image": ns.image, "gold": ns.gold, "results": {}}
try:
    assert dk("run", "-d", "--name", name, "--network", "none", "--label", "rh2.task2=private_control", "--entrypoint", "sleep", ns.image, "infinity").returncode == 0
    dk("cp", ns.gold, f"{name}:/tmp/gold.patch")
    # 只应用源码段：排除测试文件（隐藏测试不进对照）
    ap_ = dk("exec", name, "bash", "-c", "cd /testbed && git apply --exclude='tests/*' --exclude='*/tests/*' --exclude='test_*' -v /tmp/gold.patch 2>&1 | tail -5; echo rc=${PIPESTATUS[0]}")
    res["apply"] = ap_.stdout
    for cid in ns.ids.split(","):
        c = cmds[cid]
        r = dk("exec", "-e", f"PATH={ns.python_prefix}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "-w", "/testbed", name,
               "timeout", str(c.get("timeout_s", 300)), "bash", "-c", c["cmd"])
        res["results"][cid] = {"rc": r.returncode, "tail": (r.stdout + r.stderr)[-800:]}
finally:
    dk("rm", "-f", name)
json.dump(res, open(ns.out, "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v["rc"] for k, v in res["results"].items()}), res.get("apply", "")[-200:])
