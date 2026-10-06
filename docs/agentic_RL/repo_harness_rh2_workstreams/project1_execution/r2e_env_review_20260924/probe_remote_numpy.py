"""在既有派生镜像的临时容器复核公开测试；不改镜像、材料、评分代码。"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/scripts/r2e_env").is_dir())
IID = "numpy__43e333e2ff641f6dce852e46c9c650333b0d4b3d"

REMOTE = r'''
import json, subprocess, secrets, time
def run(args, timeout=90):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return {"args": args, "rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
name = "rh2-codex-envreview-numpy-" + secrets.token_hex(4)
out = {"iid": C["iid"], "image": C["image"], "conditions": "temporary derived-image container, uid54321, cpu2,mem4GiB,tmp1GiB,networknone"}
try:
    insp=run(["docker","image","inspect","-f","{{.Id}}",C["image"]])
    assert insp["rc"]==0 and insp["stdout"].strip()==C["image"], insp
    args=["docker","run","--detach","--init","--network","none","--cap-drop","ALL"]
    for cap in C["caps"]: args += ["--cap-add",cap]
    args += ["--security-opt","no-new-privileges","--pids-limit","512","--cpus","2", "--memory", str(4*2**30),"--memory-swap",str(4*2**30),"--tmpfs","/tmp:size=1073741824,mode=1777","--tmpfs","/home/agent:size=268435456,mode=0750,uid=54321,gid=54321","--name",name,C["image"],"sleep","infinity"]
    started=run(args)
    assert started["rc"]==0, started
    init=run(["docker","exec",name,"bash","-c",C["init"]], timeout=180)
    out["init"]={k:init[k] for k in ("rc","stdout","stderr")}
    assert init["rc"]==0, init
    checks=[
      ("versions", "python -c 'import pytest,hypothesis; print(pytest.__version__, hypothesis.__version__)'"),
      ("public_target_default", "timeout 45 python -m pytest --collect-only -q numpy/ma/tests/test_extras.py::TestAverage"),
      ("public_target_warning_override", "timeout 45 python -m pytest -q -o filterwarnings=ignore numpy/ma/tests/test_extras.py::TestAverage"),
      ("public_module_warning_override", "timeout 45 python -m pytest -q -o filterwarnings=ignore numpy/ma/tests/test_extras.py"),
    ]
    out["checks"]=[]
    for label,command in checks:
      r=run(["docker","exec","-u","54321","-w","/testbed","-e","HOME=/home/agent",name,"bash","-c",command], timeout=60)
      out["checks"].append({"label":label,"command":command,**{k:r[k] for k in ("rc","stdout","stderr")}})
finally:
    removed=run(["docker","rm","-f",name])
    verify=run(["docker","ps","-a","-q","-f","name=^"+name+"$"])
    out["cleanup"]={"rm_rc":removed["rc"],"confirmed_absent":verify["rc"]==0 and not verify["stdout"].strip()}
    print(json.dumps(out))
'''


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--host", required=True)
    p.add_argument("--key", required=True)
    ns=p.parse_args()
    probe=json.loads((ROOT / "runs/r2e_env_repair_20260924/p2/dev_probe" / IID / "dev_probe.json").read_text())
    spec=importlib.util.spec_from_file_location("review_dev",ROOT / "rh2/scripts/r2e_env/run_dev_probe.py")
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    config={"iid":IID,"image":probe["image_id"],"caps":mod.TRUSTED_INIT_CAPS,"init":mod.ROOT_INIT}
    proc=subprocess.run(["ssh","-i",str(Path(ns.key).expanduser()),"-o","BatchMode=yes","-o","ConnectTimeout=10",ns.host,"python3 -"],input="C="+repr(config)+"\n"+REMOTE,capture_output=True,text=True,timeout=420)
    (HERE / "remote_numpy_stderr.txt").write_text(proc.stderr)
    if not proc.stdout.strip():
        raise RuntimeError(f"remote returned {proc.returncode}: {proc.stderr[:500]}")
    result=json.loads(proc.stdout)
    result["ssh_exit_code"]=proc.returncode
    (HERE / "remote_numpy.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"ssh_exit_code":proc.returncode,"checks":[{"label":x["label"],"rc":x["rc"],"summary":x["stdout"].splitlines()[-4:]} for x in result.get("checks",[])],"cleanup":result["cleanup"]},ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
