#!/usr/bin/env python3
"""汇总"候选身份（uid 54322）最小权限布置"实测。

三种布置（都在一次性容器里以 root 施加，绝不 docker commit）：
  a 就地放权：chmod o+rx /root（打开解释器链路）+ chown -R 54322 /testbed /r2e_tests + git safe.directory '*'
  b 搬迁    ：把解释器从 /root 复制到 /opt 并改 pyvenv.cfg / 符号链接 / shebang，/root 保持 700；其余同 a
  c = b + 评分面收回 root：run_tests.sh 与 /r2e_tests、/testbed/r2e_tests 保持 root 所有

每个 (镜像, 布置, gate) 一个新容器：布置 → [gold 打补丁] → 评分 setup → 以 uid 54322 跑一次 → 同容器再以 root 跑一次
→ 最后才做可写面探测（探测会 touch 文件，不能污染评分）。

输出 docs/.../M3/M3_uid_fix_probe.json。
"""
import json, os, re
from collections import Counter

ROOT = "."
FACTS = os.path.join(ROOT, "runs/env_overnight_20260916/M3/facts")
GOLDLOG = os.path.join(ROOT, "runs/env_overnight_20260916/M3/gold_ledger/logs_r2e")
PKG = os.path.join(ROOT, "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/M3")
OUT = os.path.join(PKG, "M3_uid_fix_probe.json")
CANDS = [os.path.join(ROOT, "runs/env_probe_20260909_codex_backup/data/r2e_candidates_full.jsonl"),
         os.path.join(ROOT, "runs/env_probe_stage1_20260910/r2e_expansion_preparation/r2e_candidates_full.jsonl")]
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def parse(o):
    out = {}
    if "short test summary info" not in o:
        return out
    for l in o.split("short test summary info")[1].strip().split("\n"):
        if "PASSED" in l:
            out[".".join(l.split("::")[1:])] = "PASSED"
        elif "FAILED" in l:
            out[".".join(l.split("::")[1:]).split(" - ")[0]] = "FAILED"
        elif "ERROR" in l:
            out[".".join(l.split("::")[1:]).split(" - ")[0]] = "ERROR"
    return {ANSI.sub("", k).split(" - ")[0]: v for k, v in out.items()}


def reward(m, e):
    if len(m) != len(e):
        return 0
    for k in m:
        if k and (k not in e or m[k] != e[k]):
            return 0
    return 1


def kv(txt):
    d = {}
    for l in (txt or "").splitlines():
        if "=" in l and not l.startswith("PATH="):
            k, v = l.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def read(p):
    return open(p, errors="replace").read() if os.path.exists(p) else ""


def main():
    expected = {}
    for p in CANDS:
        for ln in open(p):
            r = json.loads(ln)
            m = json.loads(r["expected_output_json"]) if r.get("expected_output_json") else {}
            expected[r["commit_hash"][:12]] = {ANSI.sub("", k).split(" - ")[0]: v for k, v in m.items()}
    facts = {t["commit12"]: t for t in json.load(open(os.path.join(ROOT, "runs/env_overnight_20260916/M3/r2e_image_facts.json")))["tasks"]}

    rows = []
    for c12 in sorted(os.listdir(FACTS)):
        base = os.path.join(FACTS, c12, "uidfix")
        if not os.path.isdir(base):
            continue
        repo = facts[c12]["repo"]
        exp = expected[c12]
        # 基线：第一片的 root 结果（同镜像、同入口、未做任何权限布置）
        bl_noop = parse(read(os.path.join(FACTS, c12, "noop_x2", "out1.txt")))
        gp = os.path.join(GOLDLOG, repo, c12, "gold", "a1", "status_map.json")
        bl_gold = {ANSI.sub("", k).split(" - ")[0]: v for k, v in json.load(open(gp)).items()} if os.path.exists(gp) else {}
        for mode in ("a", "b", "c"):
            for gate in ("noop", "gold"):
                d = os.path.join(base, f"{mode}_{gate}")
                if not os.path.isdir(d):
                    continue
                st = read(os.path.join(d, "_STATUS")).strip()
                ar = kv(read(os.path.join(d, "arrange.txt")))
                rc = kv(read(os.path.join(d, "rc.txt")))
                ap = read(os.path.join(d, "apply.txt"))
                setup = read(os.path.join(d, "setup.txt"))
                pr = read(os.path.join(d, "uid_probe.txt"))
                ma = parse(read(os.path.join(d, "out_agent.txt")))
                mr = parse(read(os.path.join(d, "out_root.txt")))
                bl = bl_noop if gate == "noop" else bl_gold
                paths = {}
                for l in pr.splitlines():
                    m = re.match(r"PATH=(\S+) r=(\w+) w=(\w+) owner=(.*)$", l)
                    if m:
                        paths[m.group(1)] = {"r": m.group(2), "w": m.group(3), "owner": m.group(4).strip()}
                writes = dict(re.findall(r"WRITE (\S+) (OK|DENIED)", pr))
                rec = {
                    "commit12": c12, "repo": repo, "mode": mode, "gate": gate, "status": st,
                    "arrange": {
                        "n_paths_changed": int(ar.get("n_paths_changed", 0) or 0),
                        "t_total_ms": ar.get("t_total"), "t_chown_ms": ar.get("t_chown"),
                        "t_copy_interp_ms": ar.get("t_copy_interp"),
                        "chown_paths": int(ar.get("chown_paths", 0) or 0),
                        "copy_interp_paths": int(ar.get("copy_interp_paths", 0) or 0),
                        "grading_surface_protected": ar.get("grading_surface") == "protected",
                        "py_real": ar.get("py_real"),
                    },
                    "container_layer_size": read(os.path.join(d, "layer_size.txt")).strip(),
                    "apply_rc": (re.search(r"apply_rc=(\d+)", ap) or [None, None])[1] if gate == "gold" else None,
                    "setup_ok": "setup_ok" in setup,
                    "agent_rc": rc.get("agent_rc"), "t_agent_s": rc.get("t_agent"),
                    "root_rc": rc.get("root_rc"), "t_root_s": rc.get("t_root"),
                    "parsed_n_agent": len(ma), "parsed_n_root": len(mr),
                    "expected_n": len(exp), "baseline_n": len(bl),
                    "reward_agent": reward(ma, exp), "reward_root_same_container": reward(mr, exp),
                    "reward_baseline_root_no_fix": reward(bl, exp) if bl else None,
                    "agent_map_eq_baseline": (ma == bl) if bl else None,
                    "root_map_eq_baseline": (mr == bl) if bl else None,
                    "agent_eq_root_same_container": (ma == mr),
                    "keys_only_baseline": sorted(set(bl) - set(ma))[:6],
                    "keys_only_agent": sorted(set(ma) - set(bl))[:6],
                    "status_flips_vs_baseline": [(k, bl[k], ma[k]) for k in bl if k in ma and bl[k] != ma[k]][:6],
                    "uid_probe": {
                        "python_runs": bool(re.search(r"Python \d", pr)),
                        "sys_path_under_root": (re.search(r"### sys\.path_under_root\n(.*)", pr) or [None, "?"])[1].strip()[:80],
                        "git_usable": "dubious ownership" not in pr.split("### git")[1].split("###")[0] if "### git" in pr else None,
                        "paths": paths, "writes": writes,
                        "run_tests_replaceable": ("可被候选替换=YES" in pr),
                        "pytest_cache_writable": "MKDIR /testbed/.pytest_cache_probe OK" in pr,
                        "r2e_pycache_writable": "MKDIR r2e_tests/__pycache__ OK" in pr,
                        "src_writable": (re.search(r"SRC_WRITABLE \S+ (\w+)", pr) or [None, None])[1],
                        "test_helper_writable": re.findall(r"TESTHELPER_WRITABLE (\S+) (\w+)", pr)[:4],
                        "root_listable": bool(re.search(r"### /root 可读面.*\n(?!ls:)", pr)),
                    },
                }
                rows.append(rec)

    def agg(mode):
        sel = [r for r in rows if r["mode"] == mode]
        return {
            "n_runs": len(sel),
            "reward_agent_eq_baseline_root": dict(Counter(r["agent_map_eq_baseline"] for r in sel)),
            "agent_eq_root_in_same_container": dict(Counter(r["agent_eq_root_same_container"] for r in sel)),
            "reward_agent": dict(Counter(r["reward_agent"] for r in sel)),
            "python_runs_as_agent": dict(Counter(r["uid_probe"]["python_runs"] for r in sel)),
            "git_usable_as_agent": dict(Counter(r["uid_probe"]["git_usable"] for r in sel)),
            "run_tests_replaceable_by_agent": dict(Counter(r["uid_probe"]["run_tests_replaceable"] for r in sel)),
            "hidden_tests_writable_by_agent": dict(Counter(r["uid_probe"]["writes"].get("/testbed/r2e_tests/.m3w") for r in sel)),
            "r2e_src_writable_by_agent": dict(Counter(r["uid_probe"]["writes"].get("/r2e_tests/.m3w") for r in sel)),
            "root_home_listable_by_agent": dict(Counter(r["uid_probe"]["paths"].get("/root", {}).get("r") for r in sel)),
            "n_paths_changed_range": [min((r["arrange"]["n_paths_changed"] for r in sel), default=0),
                                      max((r["arrange"]["n_paths_changed"] for r in sel), default=0)],
        }

    # ---- 替换攻击验证：目录可写是否足以换掉评分面（只在一次性容器里做，做完还原）----
    attacks = []
    for c12 in sorted(os.listdir(FACTS)):
        base = os.path.join(FACTS, c12, "uidfix")
        if not os.path.isdir(base):
            continue
        for mode in ("a", "b", "c"):
            d = os.path.join(base, f"attack_{mode}")
            if not os.path.isdir(d):
                continue
            t = read(os.path.join(d, "attack.txt"))
            g = lambda k: (re.search(k + r"=(\S+)", t) or [None, None])[1]
            attacks.append({
                "commit12": c12, "repo": facts[c12]["repo"], "mode": mode,
                "run_tests_sh_owner": (lambda m: list(m.groups()) if m else ["?", "?"])(
                    re.search(r"/testbed/run_tests\.sh (\S+) (\d+)", t)),
                "testbed_owner": (lambda m: list(m.groups()) if m else ["?", "?"])(
                    re.search(r"^/testbed (\S+) (\d+)$", t, re.M)),
                "append_in_place": g("APPEND_INPLACE"),
                "unlink_and_replace": g("UNLINK_AND_REPLACE"),
                "rename_hidden_tests": g("RENAME_HIDDEN_TESTS"),
                "rmdir_hidden_tests": g("RMDIR_HIDDEN_TESTS"),
                "venv_bin_dir_writable": g("VENV_BIN_DIR_WRITABLE"),
                "rename_src_r2e": g("RENAME_SRC_R2E"),
                "note": "UNLINK_AND_REPLACE=OK 表示：即使 run_tests.sh 是 root:root 755，"
                        "候选也能因为 /testbed 目录可写而把它 unlink 后换成自己的脚本",
            })

    doc = {"schema": "rh2.env_overnight.m3.uid_fix.v1", "machine": "机器 3",
           "grading_surface_attack": attacks,
           "attack_summary": {
               "append_in_place": {f"{k[0]}:{k[1]}": v for k, v in Counter((a["mode"], a["append_in_place"]) for a in attacks).items()},
               "unlink_and_replace": {f"{k[0]}:{k[1]}": v for k, v in Counter((a["mode"], a["unlink_and_replace"]) for a in attacks).items()},
               "rename_hidden_tests": {f"{k[0]}:{k[1]}": v for k, v in Counter((a["mode"], a["rename_hidden_tests"]) for a in attacks).items()},
           },
           "images": sorted({(r["repo"], r["commit12"]) for r in rows}),
           "n": len(rows),
           "by_mode": {m: agg(m) for m in ("a", "b", "c")},
           "runs": rows}
    json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("wrote", OUT, len(rows))
    for m in ("a", "b", "c"):
        print(m, json.dumps(doc["by_mode"][m], ensure_ascii=False))
    print("attack:", json.dumps(doc["attack_summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
