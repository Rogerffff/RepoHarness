"""聚焦复核（v3）：把 run_matrix.sh 的 results.tsv 汇总成“候选 × 测试版本”表，并比较 root 与评分 UID。

用法（仓库根目录）：
    python3 rh2/experiments/category3_cloud_20260929/conan13403/review_v3/summarize.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = ["orig", "v2", "v3", "v3_nochain", "v3_fix", "v3_fix_plus"]
REASONABLE = ["gold", "argsfirst", "conanfile_chdir", "runcwd", "oschdir", "rv_check", "rv_kw",
              "rv_wrap", "rv_retcode", "r3_fromnone", "r3_calledprocess", "r3_validate_conf",
              "r3_deferred_raise", "r3_restore_then_raise"]
BOUNDARY_OK = ["w3_code_unrelated"]  # 失败时仍会报错（信息误导），不算隐藏失败


def load(name):
    res, order = {}, []
    for line in open(os.path.join(HERE, "results", name)):
        t, c, r = line.rstrip("\n").split("\t")[:3]
        res[(t, c)] = r
        if c not in order:
            order.append(c)
    return res, order


def main():
    root, cands = load("private_root.tsv")
    uid, _ = load("private_uid54322.tsv")
    print("{:<24}".format("candidate") + "".join("{:<12}".format(t) for t in TESTS))
    for c in cands:
        print("{:<24}".format(c) + "".join("{:<12}".format(root.get((t, c), "-")) for t in TESTS))
    print()
    for t in TESTS:
        rej = [c for c in REASONABLE if root[(t, c)] != "1"]
        wrong = [c for c in cands if root[(t, c)] == "1" and c not in REASONABLE + BOUNDARY_OK]
        print("{:<12} reasonable rejected: {}\n{:<12} wrong/boundary passing: {}".format(t, rej, "", wrong))
    diff = [(k, root.get(k), v) for k, v in uid.items() if root.get(k) != v]
    print("\nuid 54322 rows: {}, differences vs root: {}".format(len(uid), diff or "none"))


if __name__ == "__main__":
    main()
