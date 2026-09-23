#!/usr/bin/env python3
"""对每题在 base_commit 的一次性 worktree 上验证：
   fake / gold / test_patch 单独可应用，且 fake+test_patch、gold+test_patch 可叠加应用。
运行完自动 `git worktree remove --force`。结果写 verify_report.json。"""
import json, os, subprocess, sys, glob

ROOT = "runs/env_overnight_20260916"
KIT = os.path.join(ROOT, "L7_fake_fix_kits")
PATCHES = os.path.join(KIT, "patches")
WT = os.path.join(KIT, "wt")
REPO_DIR = {"iterative/dvc": "dvc", "Project-MONAI/MONAI": "MONAI", "getmoto/moto": "moto",
            "pydantic/pydantic": "pydantic", "python/mypy": "mypy", "dask/dask": "dask",
            "conan-io/conan": "conan", "modin-project/modin": "modin", "pandas-dev/pandas": "pandas"}


def run(*a, **kw):
    return subprocess.run(a, capture_output=True, text=True, **kw)


def main():
    facts = json.load(open(os.path.join(PATCHES, "_facts.json")))
    out = {}
    for iid in sorted(facts):
        v = facts[iid]
        src = os.path.join(ROOT, "repos", REPO_DIR[v["repo"]])
        wt = os.path.join(WT, iid)
        r = run("git", "-C", src, "worktree", "add", "--detach", wt, v["base_commit"])
        if r.returncode != 0:
            out[iid] = {"worktree": "FAIL", "err": r.stderr.strip()[:300]}
            continue
        res = {"base_commit": v["base_commit"], "checks": {}}
        tp = os.path.join(PATCHES, f"{iid}.test_patch.diff")
        gold = os.path.join(PATCHES, f"{iid}.gold.diff")

        def check(label, patches):
            run("git", "-C", wt, "checkout", "--", ".")
            run("git", "-C", wt, "clean", "-fd")
            ok, err = True, ""
            for i, p in enumerate(patches):
                last = i == len(patches) - 1
                cmd = ["git", "-C", wt, "apply"] + (["--check"] if last else []) + ["--whitespace=nowarn", p]
                rr = run(*cmd)
                if rr.returncode != 0:
                    ok, err = False, rr.stderr.strip()[:300]
                    break
            res["checks"][label] = "OK" if ok else f"FAIL: {err}"

        check("test_patch", [tp])
        check("gold", [gold])
        check("gold+test_patch", [gold, tp])
        for fp in sorted(glob.glob(os.path.join(PATCHES, f"{iid}.fake*.diff"))):
            name = os.path.basename(fp)[len(iid) + 1:-5]
            check(name, [fp])
            check(f"{name}+test_patch", [fp, tp])
        run("git", "-C", wt, "checkout", "--", ".")
        run("git", "-C", wt, "clean", "-fd")
        run("git", "-C", src, "worktree", "remove", "--force", wt)
        out[iid] = res
        bad = [k for k, s in res["checks"].items() if not s.startswith("OK")]
        print(f"{iid:34s} {'ALL OK' if not bad else 'FAIL: ' + ','.join(bad)}")
    with open(os.path.join(KIT, "verify_report.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    nbad = sum(1 for v in out.values() for s in v.get("checks", {}).values() if not s.startswith("OK"))
    print(f"\n总计 {len(out)} 题，失败检查 {nbad} 条 -> {os.path.join(KIT, 'verify_report.json')}")


if __name__ == "__main__":
    main()
