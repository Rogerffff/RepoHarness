"""dask__dask-8801 v4 聚焦复核：私有对照／私有模拟评分的运行器（不是正式评分）。

用法：python run_review.py <输出目录> <变体名...>
- 启动容器前等待本机运行中的容器少于 3 个；一次调用只起 1 个一次性、断网容器（镜像 c3keep/dask8801:src）；
- 变体在同一容器里依次处理：每个变体开始前 `git checkout` 还原 dask/config.py 与 dask/tests/test_config.py，
  并断言 `git status --porcelain` 为空、dask/config.py 与 base 摘要相同，然后 `git apply` 候选补丁；
- 每个变体：行为探针（root、nobody 各一次），再把 4 份测试文件（原版、v4、v4rva、v4rvb）
  分别以 nobody（UID 65534）与 root 运行 pytest；
- 输出 <out>/<变体>/{apply.txt, behavior_root.json, behavior_nobody.json, <test>_<who>.out}。
"""

import hashlib
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path("/home/user/RepoHarness")
EV = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks/dask__dask-8801/evidence"
IMAGE = "c3keep/dask8801:src"
BASE_SHA = "689e71ce770ee620c1e1c9ddaa72d12c1639c93d5d9c1c12f0be0e99c2d631ee"
PY = "/opt/miniconda3/envs/testbed/bin"
PATH = f"{PY}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
TESTS = {
    "orig": EV / "rerun_0930/testfiles/test_config_orig.py",
    "v4": EV / "rerun_0930/testfiles/test_config_revised_v4.py",
    "v4rva": HERE / "test_config_v4rva.py",
    "v4rvb": HERE / "test_config_v4rvb.py",
}
AUTHOR = HERE.parent


def patch_for(name):
    if name == "base":
        return None
    if name == "gold":
        return EV / "gold/dask__dask-8801.gold.patch"
    p = HERE / f"{name}.patch"
    return p if p.exists() else AUTHOR / f"{name}.patch"


def sh(*a, **k):
    return subprocess.run(list(a), capture_output=True, text=True, **k)


def wait_slot():
    while int(sh("bash", "-c", "docker ps -q | wc -l").stdout.strip() or 0) >= 3:
        time.sleep(20)


out = Path(sys.argv[1])
names = sys.argv[2:]
out.mkdir(parents=True, exist_ok=True)
cname = f"rv4f-{uuid.uuid4().hex[:8]}"
wait_slot()
r = sh("docker", "run", "-d", "--name", cname, "--network", "none", "--entrypoint", "sleep", IMAGE, "infinity")
assert r.returncode == 0, r.stderr


def dx(cmd, timeout=600):
    return sh("docker", "exec", "-e", f"PATH={PATH}", "-e", "PYTHONDONTWRITEBYTECODE=1", "-w", "/testbed", cname,
              "timeout", str(timeout), "bash", "-c", cmd)


try:
    sh("docker", "exec", cname, "mkdir", "-p", "/in")
    sh("docker", "cp", str(HERE / "behavior_review.py"), f"{cname}:/in/behavior_review.py")
    for t, p in TESTS.items():
        sh("docker", "cp", str(p), f"{cname}:/in/test_{t}.py")
    for n in names:
        p = patch_for(n)
        if p is not None:
            sh("docker", "cp", str(p), f"{cname}:/in/{n}.patch")
    sh("docker", "exec", cname, "chmod", "-R", "a+rX", "/in")
    env_info = dx("id; python -c 'import sys,yaml; print(sys.version.split()[0], yaml.__version__)'; git rev-parse HEAD")
    (out / f"_container_{cname}.txt").write_text(
        sh("docker", "inspect", "--format", "{{.Image}} {{.Config.Image}} {{.HostConfig.NetworkMode}}", cname).stdout
        + env_info.stdout + env_info.stderr
    )
    for n in names:
        vd = out / n
        vd.mkdir(exist_ok=True)
        log = []
        r = dx("git checkout -q -- dask/config.py dask/tests/test_config.py && git status --porcelain && sha256sum dask/config.py")
        clean = r.returncode == 0 and r.stdout.strip() == f"{BASE_SHA}  dask/config.py"
        log.append(f"reset rc={r.returncode} clean_and_base={clean}\n{r.stdout}{r.stderr}")
        assert clean, (n, r.stdout, r.stderr)
        p = patch_for(n)
        if p is not None:
            r = dx(f"git apply /in/{n}.patch")
            log.append(f"apply rc={r.returncode}\n{r.stdout}{r.stderr}")
            assert r.returncode == 0, (n, r.stderr)
            log.append("patch_sha256=" + hashlib.sha256(p.read_bytes()).hexdigest())
        r = dx("sha256sum dask/config.py; git diff --stat")
        log.append(r.stdout)
        (vd / "apply.txt").write_text("\n".join(log))
        r = dx("python /in/behavior_review.py")
        (vd / "behavior_root.json").write_text(r.stdout + (("\n#STDERR\n" + r.stderr) if r.returncode else ""))
        r = dx("setpriv --reuid=65534 --regid=65534 --clear-groups env HOME=/tmp python /in/behavior_review.py")
        (vd / "behavior_nobody.json").write_text(r.stdout + (("\n#STDERR\n" + r.stderr) if r.returncode else ""))
        for t in TESTS:
            for who, pre in (("nobody", "setpriv --reuid=65534 --regid=65534 --clear-groups env HOME=/tmp "), ("root", "")):
                r = dx(f"cp /in/test_{t}.py dask/tests/test_config.py && "
                       f"{pre}python -m pytest -p no:cacheprovider -n0 -rA --color=no dask/tests/test_config.py")
                (vd / f"{t}_{who}.out").write_text(r.stdout + r.stderr + f"\n#RC={r.returncode}\n")
        print(n, "done", flush=True)
finally:
    sh("docker", "rm", "-f", cname)
