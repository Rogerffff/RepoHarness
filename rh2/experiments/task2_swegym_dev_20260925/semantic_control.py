"""私有语义对照（不交给求解者）：每个变体在全新、断网的一次性容器（root）里准备，执行同一组命令，
并按物化基线（git stash create，镜像初态 dirty 不混入）导出该变体的补丁，供随后真实 RH2 评分。
spec.json：{"image": "...", "python_prefix": "/opt/miniconda3/envs/testbed",
            "variants": {"base": [], "gold": ["git apply /in/gold.patch"], "C1": ["python - <<'PY'\\n...\\nPY"]},
            "files": {"gold.patch": "/abs/path"},                # 拷进容器 /in/
            "commands": [{"id": "...", "cmd": "...", "timeout_s": 300}]}
输出：<out>/<variant>/{prep.txt, <cmd>.out, rc.json, candidate.diff}
"""
import argparse, json, subprocess, uuid
from pathlib import Path

ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("--out", required=True)
ns = ap.parse_args(); spec = json.load(open(ns.spec)); out = Path(ns.out); out.mkdir(parents=True, exist_ok=True)
dk = lambda *a, **k: subprocess.run(["docker", *a], capture_output=True, text=True, **k)  # noqa: E731
PATH = f"{spec.get('python_prefix', '/opt/miniconda3/envs/testbed')}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
summary = {}
for vname, prep in spec["variants"].items():
    vd = out / vname; vd.mkdir(exist_ok=True)
    name = f"rh2t2sem-{uuid.uuid4().hex[:10]}"
    rcs = {}
    try:
        assert dk("run", "-d", "--name", name, "--network", "none", "--label", "rh2.task2=semantic_control", "--entrypoint", "sleep", spec["image"], "infinity").returncode == 0
        dk("exec", name, "mkdir", "-p", "/in")
        for fn, src in (spec.get("files") or {}).items():
            dk("cp", src, f"{name}:/in/{fn}")
        base = dk("exec", "-w", "/testbed", name, "bash", "-c", "git -c user.name=r -c user.email=r@l stash create x || true").stdout.strip()
        base = base or dk("exec", "-w", "/testbed", name, "git", "rev-parse", "HEAD").stdout.strip()
        log = []
        for step in prep:
            r = dk("exec", "-e", f"PATH={PATH}", "-w", "/testbed", name, "bash", "-c", step)
            log.append(f"$ {step[:300]}\n[rc={r.returncode}]\n{(r.stdout + r.stderr)[-3000:]}")
            if r.returncode != 0:
                rcs["_prep_failed"] = step[:200]
        (vd / "prep.txt").write_text("\n".join(log))
        diff = dk("exec", "-w", "/testbed", name, "bash", "-c", f"git -c core.fileMode=false diff --binary {base} -- .")
        (vd / "candidate.diff").write_text(diff.stdout)
        for c in spec["commands"]:
            r = dk("exec", "-e", f"PATH={PATH}", "-w", "/testbed", name, "timeout", str(c.get("timeout_s", 300)), "bash", "-c", c["cmd"])
            (vd / f"{c['id']}.out").write_text(r.stdout + r.stderr)
            rcs[c["id"]] = r.returncode
    finally:
        dk("rm", "-f", name)
    (vd / "rc.json").write_text(json.dumps(rcs))
    summary[vname] = rcs
(out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
print(json.dumps(summary, ensure_ascii=False))
