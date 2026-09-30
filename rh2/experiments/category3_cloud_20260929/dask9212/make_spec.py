"""为 semantic_control.py 生成逐变体的 spec（每个变体一个文件，便于在两次容器之间等待机器空闲）。

用法：python make_spec.py <spec 目录> <版本：v1|v2> [变体...]
- 镜像：compat_v2b 云端等效派生镜像（base + /opt/rh2/compat-wheels 下 pandas 1.4.4、numpy 1.24.4 两个 wheel）。
  每个变体先离线装这两个版本，与 compat_v2b 配方的 revised_install 相同：镜像自带 numpy 1.26.4，
  而 setup.cfg 把 numpy 警告当错误（cumproduct 在 1.25 弃用），不装 pins 时 test_base.py 的部分旧测试会报错；
- v1：env、behavior（私有矩阵）、orig_file（应用原 test_patch 后跑整份 test_base.py，即私有模拟评分）；
- v2：env、rev_file（应用修订测试草案后跑整份 test_base.py）。
"""
import json
import sys
from pathlib import Path

ROOT = Path("/home/user/RepoHarness")
E = ROOT / "rh2/experiments/category3_cloud_20260929/dask9212"
W = ROOT / "runs/category3_cloud_20260929/dask9212"
IMAGE = "rh2-envrepair/compat-v2b-dask__dask-9212:c3cloud"
PIN = ("python -m pip install -q --no-index --find-links=/opt/rh2/compat-wheels --no-deps "
       "pandas==1.4.4 numpy==1.24.4")
TESTFILE = "dask/tests/test_base.py"
PYTEST = f"python -m pytest -n0 -rA --color=no -p no:cacheprovider {TESTFILE}"

CANDS = ["alt_modqual", "alt_hookfirst", "alt_up2024", "alt_pickle", "alt_docs",
         "w_value", "w_noval", "w_hash", "w_name", "w_str"]


def run_tests(patch):
    return (f"git apply /in/{patch} && {PYTEST} > /tmp/t.txt 2>&1; rc=$?; "
            f"git checkout -- {TESTFILE}; cat /tmp/t.txt; exit $rc")


def main():
    out, version, *names = sys.argv[1:]
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    names = names or ["base", "gold", *CANDS]
    files = {"behavior.py": str(E / "behavior.py"), "test_orig.patch": str(E / "original_test.patch"),
             "gold.patch": str(W / "gold/dask__dask-9212.gold.patch")}
    for c in CANDS:
        files[f"{c}.patch"] = str(E / f"candidates/{c}.patch")
    if version == "v2":
        files["test_rev.patch"] = str(E / "revised_test_v1.patch")
    env = {"id": "env", "timeout_s": 120,
           "cmd": "id -u; python -c 'import sys,numpy,pandas,dask,pytest; print(sys.version.split()[0], numpy.__version__, "
                  "pandas.__version__, dask.__version__, pytest.__version__, dask.__file__)'; git status --porcelain"}
    if version == "v1":
        commands = [env,
                    {"id": "behavior", "timeout_s": 600, "cmd": "python /in/behavior.py"},
                    {"id": "orig_file", "timeout_s": 1200, "cmd": run_tests("test_orig.patch")}]
    else:
        commands = [env,
                    {"id": "rev_file", "timeout_s": 1200, "cmd": run_tests("test_rev.patch")}]
    for name in names:
        if name == "base":
            prep = [PIN]
        elif name == "gold":
            prep = [PIN, "git apply /in/gold.patch"]
        else:
            prep = [PIN, f"git apply /in/{name}.patch"]
        spec = {"image": IMAGE, "python_prefix": "/opt/miniconda3/envs/testbed",
                "variants": {name: prep}, "files": files, "commands": commands}
        (out / f"{name}.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1) + "\n")
        print(out / f"{name}.json")


if __name__ == "__main__":
    main()
