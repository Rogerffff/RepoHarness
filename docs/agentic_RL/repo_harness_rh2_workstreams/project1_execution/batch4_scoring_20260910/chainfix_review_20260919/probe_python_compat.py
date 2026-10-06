"""在已有 SWE 镜像里验证实际复证 renderer；不安装依赖、不执行题目测试。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import subprocess

from repoharness2.adapters.slime.prepared_task_face import render_v2_compile_probe_script


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ssh-target", required=True)
    parser.add_argument("--ssh-port", required=True)
    parser.add_argument("--ssh-key", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    images = [
        "xingyaoww/sweb.eval.x86_64.iterative_s_dvc-2141:latest",
        "xingyaoww/sweb.eval.x86_64.iterative_s_dvc-5822:latest",
        "xingyaoww/sweb.eval.x86_64.getmoto_s_moto-6913:latest",
    ]
    paths = ["good.py", "broken.py", "missing.py"]
    files = {
        "good.py": "raise RuntimeError('CANDIDATE_BODY_EXECUTED')\n",
        "broken.py": "def broken(:\n    pass\n",
        **{name: "print('SHADOW_MODULE_EXECUTED')\nraise RuntimeError('shadow import')\n"
           for name in ("json.py", "py_compile.py", "sitecustomize.py", "usercustomize.py")},
    }
    setup = ["cd /testbed"]
    for name, content in files.items():
        setup.append(f"printf %s {shlex.quote(content)} > {shlex.quote(name)}")
    setup += [
        "/opt/miniconda3/envs/testbed/bin/python -I -S -c 'import sys; print(\"PYTHON_VERSION=\" + sys.version.split()[0])'",
        "id -u",
    ]
    script = "\n".join(setup) + "\n" + render_v2_compile_probe_script(paths)
    remote = '''import json,subprocess,time
payload = PAYLOAD
results = []
for i,image in enumerate(payload["images"]):
    identity = subprocess.check_output(["docker","image","inspect",image,"--format","{{.Id}}"],text=True).strip()
    name = "codex-a-compile-0919-%s-%s" % (int(time.time()),i)
    command = ["docker","run","--rm","--pull","never","--init","--name",name,
               "--network","none","--read-only","--cpus","0.5","--memory","512m","--pids-limit","64",
               "--user","54321","--env","HOME=/tmp","--tmpfs","/tmp:rw,mode=1777,size=16m",
               "--tmpfs","/testbed:rw,mode=1777,size=16m","--entrypoint","/bin/bash","-i",identity,"-s"]
    try:
        p = subprocess.run(command,input=payload["script"],text=True,capture_output=True,timeout=45)
        results.append({"image":image,"image_id":identity,"command":command,"returncode":p.returncode,
                        "stdout":p.stdout,"stderr":p.stderr})
    finally:
        subprocess.run(["docker","rm","-f",name],capture_output=True,timeout=15)
print(json.dumps(results))
'''.replace("PAYLOAD", repr({"images": images, "script": script}))
    proc = subprocess.run(
        ["ssh", "-i", args.ssh_key, "-p", args.ssh_port, "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
         "-o", "ConnectTimeout=15", args.ssh_target, "python3 -"],
        input=remote, text=True, capture_output=True, timeout=200,
    )
    if proc.returncode:
        raise RuntimeError(proc.stderr)
    results = json.loads(proc.stdout)
    args.output.write_text(json.dumps({"renderer": "render_v2_compile_probe_script", "results": results}, indent=2) + "\n")
    for row in results:
        output = row["stdout"]
        assert row["returncode"] == 0, row
        assert "RH2_COMPILE_OK=good.py" in output, row
        assert "RH2_COMPILE_ERROR=broken.py:SyntaxError:" in output, row
        assert "RH2_COMPILE_MISSING=missing.py" in output, row
        assert "SHADOW_MODULE_EXECUTED" not in output + row["stderr"], row
        assert "CANDIDATE_BODY_EXECUTED" not in output + row["stderr"], row
        print(json.dumps({"image": row["image"], "returncode": row["returncode"], "stdout": output}))


if __name__ == "__main__":
    main()
