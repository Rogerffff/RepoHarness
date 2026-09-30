"""聚焦复核（v3）：逐份核对作者 v3 正式账本、归档评测日志、failure_reasons.txt 与结论页的预期。

只读已归档证据，不运行任何评分。用法（仓库根目录）：
    python3 rh2/experiments/category3_cloud_20260929/conan13403/review_v3/audit_ledgers.py
"""
import glob
import hashlib
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 5))
EXP = os.path.join(REPO, "rh2/experiments/category3_cloud_20260929/conan13403")
TASK = os.path.join(REPO, "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/"
                          "category3_diagnosis_20260929/tasks/conan-io__conan-13403")
V3 = os.path.join(TASK, "evidence/rerun_0930/formal_revised_v3")
GOLD = os.path.join(TASK, "evidence/gold/conan-io__conan-13403.gold.patch")
V3_PATCH_SHA = hashlib.sha256(open(os.path.join(EXP, "revised_test_v3.patch"), "rb").read()).hexdigest()
SUFFIX = "+c3-conan13403-autoreconf-folder-v3"

# 结论页 §4 v3 小节的表：候选 -> (预期 reward, 预期失败位置的关键字；None 表示通过)
EXPECTED = {
    "gold": (1, None), "argsfirst": (1, None), "conanfile_chdir": (1, None), "runcwd": (1, None),
    "oschdir": (1, None), "rv_check": (1, None), "rv_kw": (1, None), "rv_wrap": (1, None),
    "rv_retcode": (1, None),
    "noop": (0, "autotools_test.py:83"),
    "noenter": (0, "autotools_test.py:84"), "cwd_default": (0, "autotools_test.py:84"),
    "w_twice": (0, "autotools_test.py:84"), "w_argsdrop": (0, "autotools_test.py:84"),
    "norestore": (0, "autotools_test.py:86"),
    "mutate_source": (0, "autotools_test.py:87"), "w_mutate_src2": (0, "autotools_test.py:87"),
    "relonly": (0, "FileNotFoundError"), "buildlit": (0, "FileNotFoundError"),
    "fallback": (0, "autotools_test.py:92"), "swallow_all": (0, "autotools_test.py:92"),
    "w_mkdir": (0, "autotools_test.py:92"),
    "w_restore_build": (0, "autotools_test.py:101"), "w_restore_build_ctx": (0, "autotools_test.py:101"),
    "swallow_run": (0, "autotools_test.py:108"), "w_ignore_errors": (0, "autotools_test.py:108"),
    "nofinally": (0, "autotools_test.py:116"),
    "named": (0, "autotools_test.py:83"), "rel_build": (0, "FileNotFoundError"),
}


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def failure_from_log(text):
    """pytest 失败摘要：第一处 'E ' 行与测试文件或源码中的行号。"""
    e_lines = [l for l in text.splitlines() if l.startswith("E ")]
    locs = re.findall(r"(/testbed/\S+\.py:\d+): \w+", text)
    return (e_lines[0].strip() if e_lines else ""), (locs[-1].split("/")[-1] if locs else "")


def main():
    reasons = {}
    for line in open(os.path.join(V3, "failure_reasons.txt")):
        if line.strip():
            reasons[line.split()[0]] = line.rstrip("\n")
    rows = []
    problems = []
    for ledger in sorted(glob.glob(os.path.join(V3, "ledger_*.jsonl"))):
        cand = os.path.basename(ledger)[len("ledger_"):-len(".jsonl")]
        lines = [l for l in open(ledger).read().splitlines() if l.strip()]
        row = json.loads(lines[-1])
        rep, diag, ins = row["report"], row["verdict_diagnostics"], row["install"]
        pol, cand_info = row["policy"], row["candidate"]
        log_name = os.path.basename(row["log"]["path"])
        log_path = os.path.join(V3, "eval_logs", log_name)
        log_ok = os.path.exists(log_path) and "sha256:" + sha(log_path) == row["log"]["sha256"]
        log_text = open(log_path, errors="replace").read() if os.path.exists(log_path) else ""
        e_line, loc = failure_from_log(log_text)
        # 候选补丁摘要：账本记录的 sha 与仓库里的补丁文件一致
        if cand == "noop":
            patch_ok = cand_info.get("patch_sha256") in (None, "")
        elif cand == "gold":
            patch_ok = True  # gold-dir 候选：摘要在 gold_manifest 中核对
        else:
            p = os.path.join(EXP, cand + ".patch")
            patch_ok = os.path.exists(p) and cand_info.get("patch_sha256") == "sha256:" + sha(p)
        audit = os.path.join(V3, "audit_" + cand, "materials.json")
        mat_ok = False
        if os.path.exists(audit):
            mat = json.load(open(audit))
            mat_ok = hashlib.sha256(mat["test_patch"].encode()).hexdigest() == V3_PATCH_SHA \
                and mat.get("revised_patch_sha256") == V3_PATCH_SHA
        exp_reward, exp_loc = EXPECTED.get(cand, (None, None))
        reward = int(rep["reward"])
        loc_ok = True
        if exp_loc:
            loc_ok = exp_loc in (loc + " " + e_line + " " + reasons.get(cand, ""))
        checks = {
            "reward==expected": reward == exp_reward,
            "f2p": "{}/{}".format(rep["f2p_pass"], rep["f2p_total"]) == ("1/1" if reward else "0/1"),
            "p2p_total==0": rep["p2p_total"] == 0,
            "apply_ok": diag["apply_ok"] is True,
            "ref_missing==0": row["reference_missing_count"] == 0 and diag["reference_missing"] == [],
            "install_rc==0": ins["install_rc_last_command"] == 0,
            "test_rc": ins["test_rc"] == (0 if reward else 1),
            "cleanup": row["cleanup"]["removed"] is True,
            "grader_suffix": rep["grader_version"].endswith(SUFFIX),
            "uid54322/deny_all": pol["uid"] == 54322 and pol["network"] == "deny_all",
            "log_sha": log_ok,
            "patch_sha": patch_ok,
            "materials_v3": mat_ok,
            "fail_loc": loc_ok,
            "reasons_line": cand in reasons and ("reward={:.1f}".format(reward) in reasons[cand]),
        }
        bad = [k for k, v in checks.items() if not v]
        if bad:
            problems.append((cand, bad))
        rows.append((cand, reward, exp_reward, loc, e_line[:90], "OK" if not bad else "BAD:" + ",".join(bad)))
    for r in rows:
        print("{:<20} reward={} expected={} loc={:<24} {:<92} {}".format(*r))
    print("\nledgers:", len(rows), " problems:", problems or "none")
    print("v3 patch sha256:", V3_PATCH_SHA)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
