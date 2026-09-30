"""复核者私有模拟评分驱动（pillow__a682ceaf 独立复核），仿照主审的 run_matrix.py。

每个候选一个全新、断网、root 的一次性容器（共用工具 semantic_control.py）；依次跑选定版本的隐藏测试、
公开测试 Tests/test_file_gif.py＋Tests/test_image_convert.py、复核者探针 probe_review.py；
需要评分身份时再以 UID 54322（setpriv，私有近似）跑隐藏测试。之后用 grade_r2e.py 逐键对照期望映射，
并另算 RH2 生产口径（键集相等且逐键相等）。

用法：python run_review.py <输出目录> <候选,...> <材料 id,...>
候选名先在 review/cands/ 找补丁，找不到再到主审目录 pillow_a682/ 找；base 表示不打补丁。
这是私有模拟，不是 R2E 正式评分链。
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUTHOR = HERE.parent
RH2 = HERE.parents[3]
SEMCTL = RH2 / "experiments/task2_swegym_dev_20260925/semantic_control.py"
GRADE = RH2 / "experiments/category3_cloud_20260929/pillow3a61/grade_r2e.py"
IMAGE = "c3keep/pillow_a682:src"  # = namanjain12/pillow_final@sha256:c9ee334c…5733
EXPECTED = AUTHOR / "expected_output_orig.json"  # a465b6c9…，93 键，与评分包一致

# 材料 id → (替换进 r2e_tests/test_1.py 的文件（None=镜像原件），运行身份)
MATERIALS = {
    "h0_orig": (None, "root"),
    "h1_rev1": (AUTHOR / "hidden_test_1_revised_v1.py", "root"),
    "h1u_rev1": (AUTHOR / "hidden_test_1_revised_v1.py", "uid54322"),
    "h2_nowarn": (AUTHOR / "hidden_test_1_revised_v1_nowarn.py", "root"),
    "h4_rv2": (HERE / "materials/hidden_test_1_review_v2.py", "root"),
    "h4u_rv2": (HERE / "materials/hidden_test_1_review_v2.py", "uid54322"),
    "h5_rv2_nowarn": (HERE / "materials/hidden_test_1_review_v2_nowarn.py", "root"),
}


def hidden_cmd(test_file, who):
    cp = "rm -rf /testbed/r2e_tests && cp -r /r2e_tests /testbed/r2e_tests"
    if test_file:
        cp += f" && cp /in/{test_file.name} /testbed/r2e_tests/test_1.py"
    if who == "root":
        run = "bash /in/run_tests.sh 2>&1"
    else:
        # 与主审相同的私有近似：放开 /root 遍历权限，把 /testbed 交给 54322，再 setpriv 降权
        run = ("chmod 755 /root && chown -R 54322:54322 /testbed && rm -rf /tmp/u54322 && mkdir -p /tmp/u54322 "
               "&& chown 54322:54322 /tmp/u54322 && HOME=/tmp/u54322 TMPDIR=/tmp/u54322 "
               "setpriv --reuid=54322 --regid=54322 --clear-groups bash /in/run_tests.sh 2>&1")
    return f"{cp} && sha256sum /testbed/r2e_tests/test_1.py && {run}; rm -rf /testbed/r2e_tests"


def patch_path(cand):
    for d in (HERE / "cands", AUTHOR):
        p = d / f"{cand}.patch"
        if p.exists():
            return p
    raise SystemExit(f"no patch for {cand}")


def main():
    out = Path(sys.argv[1]).resolve()
    cands = sys.argv[2].split(",")
    mats = sys.argv[3].split(",")
    extra = sys.argv[4].split(",") if len(sys.argv) > 4 else ["pub_tests", "probe"]
    out.mkdir(parents=True, exist_ok=True)
    files = {"run_tests.sh": str(AUTHOR / "run_tests.sh"), "probe_review.py": str(HERE / "probe_review.py")}
    for m in mats:
        if MATERIALS[m][0]:
            files[MATERIALS[m][0].name] = str(MATERIALS[m][0])
    cmds = [{"id": m, "cmd": hidden_cmd(*MATERIALS[m]), "timeout_s": 900} for m in mats if MATERIALS[m][1] == "root"]
    if "pub_tests" in extra:
        cmds.append({"id": "pub_tests", "timeout_s": 900,
                     "cmd": "PYTHONDONTWRITEBYTECODE=1 python -m pytest Tests/test_file_gif.py "
                            "Tests/test_image_convert.py -p no:cacheprovider -q --color=no 2>&1 | tail -n 15; "
                            "echo \"pytest_rc=${PIPESTATUS[0]}\""})
    if "probe" in extra:
        cmds.append({"id": "probe", "timeout_s": 600,
                     "cmd": "rm -rf /tmp/probe && python /in/probe_review.py /tmp/probe 2>/dev/null"})
    # 非 root 身份放最后：它会 chown /testbed 并放开 /root
    cmds += [{"id": m, "cmd": hidden_cmd(*MATERIALS[m]), "timeout_s": 900} for m in mats if MATERIALS[m][1] != "root"]

    for cand in cands:
        while int(subprocess.run("docker ps -q | wc -l", shell=True, capture_output=True, text=True).stdout) >= 3:
            time.sleep(20)
        spec_files = dict(files)
        prep = []
        if cand != "base":
            p = patch_path(cand)
            spec_files[p.name] = str(p)
            prep = [f"git apply /in/{p.name} && git diff --stat"]
        spec = {"image": IMAGE, "python_prefix": "/testbed/.venv", "variants": {cand: prep},
                "files": spec_files, "commands": cmds}
        spec_path = out / f"spec_{cand}.json"
        spec_path.write_text(json.dumps(spec, indent=1))
        t0 = time.time()
        r = subprocess.run([sys.executable, str(SEMCTL), str(spec_path), "--out", str(out)],
                           capture_output=True, text=True)
        (out / "summary.json").replace(out / f"summary_{cand}.json")
        print(json.dumps({"cand": cand, "wall_s": round(time.time() - t0, 1), "rc": r.returncode,
                          "stderr_tail": r.stderr[-300:]}), flush=True)

    exp = json.loads(EXPECTED.read_text())
    with (out / "grades.jsonl").open("a") as g:
        for cand in cands:
            row = {"variant": cand}
            for m in mats:
                log = out / cand / f"{m}.out"
                if not log.exists():
                    row[m] = "missing"
                    continue
                res = subprocess.run([sys.executable, str(GRADE), str(log), str(EXPECTED)],
                                     capture_output=True, text=True)
                if res.returncode != 0:
                    row[m] = {"grade_error": res.stderr[-300:]}
                    continue
                d = json.loads(res.stdout)
                # RH2 生产口径：键集相等且逐键相等
                d["prod_match"] = (d["n_parsed"] == len(exp) and not d["mismatch"] and not d["unexpected"])
                row[m] = d
            g.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(json.dumps({"variant": cand, **{m: (row[m].get("reward") if isinstance(row[m], dict) else row[m])
                                                   for m in mats}}), flush=True)


if __name__ == "__main__":
    main()
