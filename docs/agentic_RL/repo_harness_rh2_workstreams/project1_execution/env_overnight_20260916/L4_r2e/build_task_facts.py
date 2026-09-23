#!/usr/bin/env python3
"""L4：R2E 48 题逐题静态事实。只读本地证据，不起容器、不联网。"""
import json, re, collections
from pathlib import Path

ROOT = Path("${REPO_ROOT}")
DOCS = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams"
PKG = DOCS / "project1_execution/env_overnight_20260916/L4_r2e"
OLD_LEDGER = DOCS / "project1_execution/env_probe_20260909/ledger/r2e_ledger_v3.jsonl"
OLD_LOGS = ROOT / "runs/env_probe_20260909_final_sync/ledger/logs_r2e"
NEW_BATCHES = ["r2e_preflight_20260911", "r2e_remainder_20260911", "r2e_failure_repeats_20260911"]
NEW_LEDGER_DIR = ROOT / "runs/env_probe_stage1_20260910/ledger"
NEW_FULL = ROOT / "runs/env_probe_stage1_20260910/r2e_expansion_preparation/r2e_candidates_full.jsonl"
SNAP = NEW_LEDGER_DIR / "r2e_fixture_snapshots_20260911"
SUBSET_META = DOCS / "data_freeze/meta/r2e_subset.jsonl"
IMG_FACTS = [ROOT / "runs/env_probe_stage1_20260910/logs/r2e_all24_image_facts.json",
             ROOT / "runs/env_probe_stage1_20260910/logs/r2e_remainder_image_facts.json"]

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
TESTMOD_RE = re.compile(r"(^|\.)(tests?|testing|conftest)(\.|$)|test_utils|testutils|testproc|testsite")


def jl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def is_test_path(p):
    parts = p.split("/"); base = parts[-1]
    if base.startswith("test_") or base.endswith("_test.py") or base == "conftest.py":
        return True
    return any(seg in ("test", "tests", "testing") for seg in parts[:-1])


def prime_key(nodeid):
    return ".".join(nodeid.split("::")[1:])


def analyze_expected(expected_map, source):
    """expected 键的形态统计。expected_map 为 {key: status}。"""
    keys = list(expected_map)
    norm = collections.Counter()
    for k in keys:
        k2 = ANSI_RE.sub("", k)
        k2 = re.sub(r"\[\d+m", "", k2)
        norm[k2.split(" - ")[0]] += 1
    return {
        "expected_n_raw": len(keys),
        "expected_n_after_normalize": len(norm),
        "collisions_after_normalize": sorted([k for k, v in norm.items() if v > 1]),
        "keys_with_ansi": sum(1 for k in keys if "\x1b" in k),
        "keys_with_space": sum(1 for k in keys if " " in k),
        "keys_with_dash_space": sum(1 for k in keys if " - " in k),
        "keys_parameterized_bracket": sum(1 for k in keys if "[" in k and "]" in k),
        "status_counts": dict(collections.Counter(expected_map.values())),
        "expected_source": source,
    }


def main():
    tasks = json.loads((PKG / "r2e_tasks_48.json").read_text())["tasks"]
    by_commit = {t["commit_hash"]: t for t in tasks}

    old_rows = collections.defaultdict(list)
    for r in jl(OLD_LEDGER):
        old_rows[r["commit_hash"]].append(r)
    new_rows = collections.defaultdict(list)
    for b in NEW_BATCHES:
        for r in jl(NEW_LEDGER_DIR / b / "results.jsonl"):
            r["_batch"] = b
            new_rows[r["commit_hash"]].append(r)

    new_full = {}
    with NEW_FULL.open() as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                new_full[r["commit_hash"]] = r

    subset = {r["commit_hash"]: r for r in jl(SUBSET_META)}
    img_facts = {}
    for p in IMG_FACTS:
        if p.exists():
            for r in json.loads(p.read_text()):
                img_facts[r["commit"]] = r

    # observation 目录：key -> dir（新 24）
    obs_by_key = {}
    for b in NEW_BATCHES:
        d = NEW_LEDGER_DIR / b / "observations"
        if d.exists():
            for sub in d.iterdir():
                obs_by_key[sub.name] = sub

    out = []
    for commit, t in sorted(by_commit.items(), key=lambda kv: (kv[1]["repo"], kv[0])):
        group = t["group"]
        rows = old_rows[commit] if group == "core24" else new_rows[commit]
        rec = {
            "task_id": t["task_id"], "group": group, "repo": t["repo"],
            "commit_hash": commit, "image_ref": t["image_ref"],
            "source": t["source"], "source_revision": t["source_revision"], "task_revision": "upstream",
        }

        # ---- 1. expected 形态
        if group == "night_expansion24":
            exp = json.loads(new_full[commit]["expected_output_json"])
            rec["expected"] = analyze_expected(exp, "source_row:expected_output_json")
        else:
            g1 = [r for r in rows if r["gate"] == "gold" and r["attempt"] == 1]
            sm = OLD_LOGS / t["repo"] / commit[:12] / "gold/a1/status_map.json"
            exp = json.loads(sm.read_text()) if sm.exists() else {}
            a = analyze_expected(exp, "recovered_from_gold_a1_status_map(reward==1, 已去 ANSI)")
            a["keys_with_ansi"] = "unknown_raw_side"
            a["expected_keys_have_ansi_flag"] = (g1[0].get("reward_details") or {}).get("expected_keys_have_ansi") if g1 else None
            a["expected_n_declared_by_ledger"] = g1[0].get("expected_n") if g1 else None
            rec["expected"] = a

        # ---- 2. 账本 noop / gold
        def gate_summary(gate):
            rs = [r for r in rows if r["gate"] == gate]
            if not rs:
                return {"status": "not_checked"}
            d0 = rs[0].get("reward_details") or {}
            return {
                "attempts": len(rs),
                "batches": sorted({r.get("_batch", "core24_v3") for r in rs}),
                "rewards": [r.get("reward") for r in rs],
                "results": sorted({str(r.get("result")) for r in rs}),
                "test_rc": sorted({str(r.get("test_rc")) for r in rs}),
                "t_test_s": [r.get("t_test") for r in rs],
                "timed_out": any(r.get("timed_out") for r in rs),
                "n_missing": sorted({(r.get("reward_details") or {}).get("n_missing") for r in rs}),
                "n_extra": sorted({(r.get("reward_details") or {}).get("n_extra") for r in rs}),
                "n_mismatch": sorted({(r.get("reward_details") or {}).get("n_mismatch") for r in rs}),
                "parsed_n": sorted({(r.get("reward_details") or {}).get("parsed_n") for r in rs}),
                "mismatch_sample": d0.get("mismatch", [])[:4],
                "missing_sample": d0.get("missing", [])[:4],
                "extra_sample": d0.get("extra", [])[:4],
            }
        rec["noop"] = gate_summary("noop")
        rec["gold"] = gate_summary("gold")

        gold_rows = [r for r in rows if r["gate"] == "gold"]
        gm = (gold_rows[0].get("gold_meta") or {}) if gold_rows else {}
        excl = gm.get("excluded") or []
        rec["gold_patch"] = {
            "included": gm.get("included", []),
            "excluded": excl,
            "excluded_test_files": [p for p, why in excl if why == "test"],
            "excluded_non_py": [p for p, why in excl if why == "non_py"],
            "excluded_other": [[p, why] for p, why in excl if why not in ("test", "non_py")],
            "patch_apply": sorted({str(r.get("patch_apply")) for r in gold_rows}) or None,
            "gold_matches_git_diff_changed_lines": sorted({str(r.get("gold_matches_git_diff_changed_lines")) for r in gold_rows}) or None,
            "gold_git_diff_lines": sorted({r.get("gold_git_diff_lines") for r in gold_rows}) or None,
        }

        # ---- 3. 来源 commit 是否含测试改动
        if group == "night_expansion24":
            mf = new_full[commit].get("modified_files") or []
            rec["commit_content"] = {
                "modified_files": mf,
                "modified_test_files": [p for p in mf if is_test_path(p)],
                "n_non_test_files": new_full[commit].get("num_non_test_files"),
                "n_non_test_lines": new_full[commit].get("num_non_test_lines"),
                "relevant_files": new_full[commit].get("relevant_files"),
                "source": "r2e_candidates_full.jsonl",
            }
        else:
            mf = sorted(set(gm.get("included", []) + [p for p, _ in excl]))
            rec["commit_content"] = {
                "modified_files": mf,
                "modified_test_files": [p for p in mf if is_test_path(p)],
                "n_non_test_files": len(gm.get("included", [])),
                "n_non_test_lines": "unknown",
                "relevant_files": "unknown",
                "source": "gold_meta(included+excluded) 反推；源行未同步到本机",
            }

        # ---- 4. 隐藏测试（只有新 24 有快照）
        sd = SNAP / commit / "r2e_tests"
        if sd.exists():
            files = sorted(p.name for p in sd.iterdir() if p.is_file())
            imports = set()
            for p in sd.iterdir():
                if p.is_file() and p.suffix == ".py":
                    for m in re.finditer(r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_.]*)", p.read_text(errors="replace"), re.M):
                        imports.add(m.group(1))
            repo_test_imports = sorted(m for m in imports if TESTMOD_RE.search(m))
            rec["hidden_tests"] = {
                "files": files,
                "n_test_modules": sum(1 for f in files if f.startswith("test_")),
                "has_conftest": "conftest.py" in files,
                "has_helper": any(f in ("helper.py", "helpers.py") for f in files),
                "custom_runner": [f for f in files if "runner" in f],
                "repo_test_module_imports": repo_test_imports,
                "source": f"runs/env_probe_stage1_20260910/ledger/r2e_fixture_snapshots_20260911/{commit}/r2e_tests/",
            }
        else:
            rec["hidden_tests"] = {"status": "unknown", "reason": "旧 24 无镜像快照；见 machine_checks.md M-01"}

        # ---- 5. 容器初态事实
        f = (rows[0].get("facts") or {}) if rows else {}
        rec["container_facts"] = {
            "head": f.get("head"), "head_is_parent_of_fix": f.get("head_is_parent_of_fix"),
            "fix_reachable": f.get("fix_reachable"), "commits_after_head": f.get("commits_after_head"),
            "refs": f.get("refs"), "tags": f.get("tags"), "remotes": f.get("remotes"),
            "status_lines": f.get("status_lines"), "venv_python": f.get("venv_python"),
            "r2e_tests_root_entries": f.get("r2e_tests_root"), "r2e_tests_in_testbed": f.get("r2e_tests_in_testbed"),
            "expected_file_at_two_paths": f.get("expected_file"),
            "egress_pypi_under_network_none": f.get("egress_pypi"),
            "image_size_bytes": (img_facts.get(commit) or {}).get("Size"),
            "image_repo_digest": ((img_facts.get(commit) or {}).get("RepoDigests") or [None])[0],
        }

        # ---- 6. 初态脏工作区（新 24 的 noop 观测）
        dirty = {"status": "unknown", "reason": "旧 24 无 pre_test.diff 观测；见 machine_checks.md M-06"}
        for r in rows:
            if r["gate"] != "noop":
                continue
            d = obs_by_key.get("rh2r2e_" + r["key"])
            if d and (d / "pre_test.diff").exists():
                txt = (d / "pre_test.diff").read_text(errors="replace")
                files = [ln.split(" b/")[-1] for ln in txt.splitlines() if ln.startswith("diff --git ")]
                dirty = {"tracked_modified_files": files, "diff_bytes": len(txt.encode()),
                         "evidence": str(d.relative_to(ROOT) / "pre_test.diff")}
                break
        rec["initial_dirty_worktree"] = dirty

        # ---- 6b. 隐藏测试 import 的模块是否正好是 gold 排除的测试文件
        def mod_to_paths(m):
            base = m.replace(".", "/")
            return {base + ".py", base + "/__init__.py"}
        ht = rec["hidden_tests"]
        matches, near = [], []
        if isinstance(ht.get("repo_test_module_imports"), list):
            excl_test = set(rec["gold_patch"]["excluded_test_files"])
            for m in ht["repo_test_module_imports"]:
                cand = mod_to_paths(m)
                hit = sorted(cand & excl_test)
                if hit:
                    matches.append({"import": m, "gold_excluded_file": hit})
                else:
                    pref = sorted(f for f in excl_test if f.startswith(m.replace(".", "/") + "/"))
                    if pref:
                        near.append({"import": m, "gold_excluded_under": pref})
        rec["fixture_risk"] = {
            "import_equals_gold_excluded_file": matches,
            "import_package_contains_gold_excluded_file": near,
            "note": "gold 补丁按 Prime 规则排除全部测试路径；隐藏测试若 import 被排除的文件，其修改不会被移植",
        }

        # ---- 6c. parser 静默丢弃的摘要条目（SKIPPED / XFAIL / XPASS）
        log_roots = [ROOT / "runs/env_probe_20260909_final_sync/ledger/logs_r2e"] + [
            NEW_LEDGER_DIR / b / "logs_r2e" for b in NEW_BATCHES]
        dropped = {"status": "unknown"}
        for lr in log_roots:
            lp = lr / t["repo"] / commit[:12] / "gold/a1/test_output.txt"
            if not lp.exists():
                continue
            txt = lp.read_text(errors="replace")
            if "short test summary info" not in txt:
                dropped = {"status": "issue", "reason": "日志没有 short test summary info 段"}
                break
            seg = txt.split("short test summary info")[1]
            n_skip, reasons = 0, []
            for line in seg.splitlines():
                m = re.match(r"^SKIPPED \[(\d+)\] (.*)$", line)
                if m:
                    n_skip += int(m.group(1)); reasons.append(m.group(2)[:90])
                elif line.startswith("SKIPPED"):
                    n_skip += 1; reasons.append(line[:90])
            n_xfail = sum(1 for line in seg.splitlines() if line.startswith("XFAIL"))
            n_xpass = sum(1 for line in seg.splitlines() if line.startswith("XPASS"))
            dropped = {"status": "pass" if (n_skip + n_xfail + n_xpass) == 0 else "issue",
                       "skipped_cases": n_skip, "xfail_lines": n_xfail, "xpass_lines": n_xpass,
                       "skip_reasons": reasons[:4], "gate": "gold/a1",
                       "evidence": str(lp.relative_to(ROOT)),
                       "note": "Prime parse_log_pytest 只识别 PASSED/FAILED/ERROR；SKIPPED/XFAIL 既不进 parsed 也不在 expected 里，键数变化就会让 reward 归 0"}
            break
        rec["parser_dropped_summary_lines"] = dropped

        # ---- 6d. 题面（agent 可见面）扫描：是否出现判别测试名 / gold 文件路径 / r2e_tests
        ps = ((new_full.get(commit) or {}).get("problem_statement")
              or (subset.get(commit) or {}).get("problem_statement") or "")
        sig_names = set()
        for k, _e, _o in rec["noop"].get("mismatch_sample", []):
            for part in k.replace("[", " ").replace("]", " ").split("."):
                if part.startswith("test"):
                    sig_names.add(part)
        rec["public_statement_scan"] = {
            "discriminating_test_names_in_statement": sorted(n for n in sig_names if n in ps),
            "gold_file_paths_in_statement": [f for f in rec["gold_patch"]["included"] if f in ps],
            "mentions_r2e_tests": "r2e_tests" in ps,
            "test_like_identifiers": sorted(set(re.findall(r"\b(?:test_[A-Za-z0-9_]+|Test[A-Za-z0-9_]+)\b", ps)))[:8],
            "note": "题面由 R2E 用 commit + 测试 diff + 执行结果反译生成；复现片段天然像测试代码，出现测试样标识不自动等于泄漏",
        }

        rec["run_tests_sh"] = t.get("run_tests_sh")
        rec["problem_statement_chars"] = len(
            (new_full.get(commit) or {}).get("problem_statement")
            or (subset.get(commit) or {}).get("problem_statement") or "") or None

        # ---- 7. 风险标记
        flags = []
        sc = rec["expected"]["status_counts"]
        if sc.get("FAILED"): flags.append("expected_has_FAILED")
        if sc.get("ERROR"): flags.append("expected_has_ERROR")
        if sc.get("SKIPPED"): flags.append("expected_has_SKIPPED")
        if rec["expected"]["collisions_after_normalize"]: flags.append("expected_key_collision")
        if rec["expected"].get("keys_with_ansi") not in (0, "unknown_raw_side"): flags.append("expected_keys_ansi")
        if rec["expected"].get("expected_keys_have_ansi_flag"): flags.append("expected_keys_ansi")
        if rec["gold_patch"]["excluded_test_files"]: flags.append("gold_excludes_test_files")
        if 0 in (rec["gold"].get("rewards") or []): flags.append("gold_reward_0")
        if 1 in (rec["noop"].get("rewards") or []): flags.append("noop_reward_1")
        for g in ("noop", "gold"):
            if any(x for x in (rec[g].get("n_missing") or []) if x): flags.append(f"{g}_missing_keys")
            if any(x for x in (rec[g].get("n_extra") or []) if x): flags.append(f"{g}_extra_keys")
        ht = rec["hidden_tests"]
        if isinstance(ht.get("repo_test_module_imports"), list) and ht["repo_test_module_imports"]:
            flags.append("hidden_tests_import_repo_test_modules")
        if ht.get("custom_runner"): flags.append("non_pytest_runner")
        if isinstance(dirty.get("tracked_modified_files"), list) and dirty["tracked_modified_files"]:
            flags.append("image_ships_dirty_tracked_files")
        if len(rec["noop"].get("attempts", 0) and rec["noop"]["rewards"] or []) < 2 and group == "night_expansion24":
            flags.append("single_attempt_only")
        if rec["fixture_risk"]["import_equals_gold_excluded_file"]:
            flags.append("hidden_test_imports_gold_excluded_file")
        if rec["parser_dropped_summary_lines"].get("status") == "issue":
            flags.append("parser_drops_skipped_or_xfail")
        if rec["public_statement_scan"]["discriminating_test_names_in_statement"]:
            flags.append("statement_names_discriminating_test")
        rec["risk_flags"] = sorted(set(flags))

        # ---- 8. 风险分层
        t1 = [f for f in flags if f in ("gold_reward_0", "noop_reward_1", "expected_key_collision", "non_pytest_runner")]
        t2 = [f for f in flags if f in ("expected_has_FAILED", "expected_has_ERROR", "expected_has_SKIPPED",
                                        "hidden_test_imports_gold_excluded_file", "gold_missing_keys", "gold_extra_keys",
                                        "noop_missing_keys", "noop_extra_keys")]
        t3 = [f for f in flags if f in ("hidden_tests_import_repo_test_modules", "image_ships_dirty_tracked_files",
                                        "expected_keys_ansi", "single_attempt_only", "parser_drops_skipped_or_xfail",
                                        "statement_names_discriminating_test")]
        rec["risk_tier"] = "T1" if t1 else ("T2" if t2 else ("T3" if t3 else "T4"))
        unknown = []
        if rec["hidden_tests"].get("status") == "unknown":
            unknown += ["M-01 隐藏测试内容", "M-07 隐藏测试 import 与 gold 排除的交集"]
        if rec["initial_dirty_worktree"].get("status") == "unknown":
            unknown.append("M-06 初态脏工作区逐文件清单")
        if rec["expected"].get("keys_with_ansi") == "unknown_raw_side":
            unknown.append("expected 原始键的 ANSI 逐键计数（只有布尔标志）")
        unknown.append("M-11 node id 折键后是否碰撞")
        unknown += ["M-03 venv 属主/可写性与安装生效", "M-05 修复提交可发现性", "M-09 默认网络下的出网"]
        rec["unknown_checks"] = unknown
        rec["static_coverage"] = "partial" if rec["hidden_tests"].get("status") == "unknown" else "mostly_complete"
        rec["risk_tier_reasons"] = {"T1": sorted(set(t1)), "T2": sorted(set(t2)), "T3": sorted(set(t3))}
        out.append(rec)

    doc = {
        "schema": "rh2.env_overnight.l4.r2e_task_facts.v1",
        "generated_by": "docs/.../env_overnight_20260916/L4_r2e/build_task_facts.py",
        "scope": "48 题静态事实；未起容器、未连机器。unknown 的项在 machine_checks.md 有对应编号。",
        "flag_counts": dict(collections.Counter(f for r in out for f in r["risk_flags"])),
        "tier_counts": dict(collections.Counter(r["risk_tier"] for r in out)),
        "static_coverage_counts": dict(collections.Counter(r["static_coverage"] for r in out)),
        "tier_caveat": "T4 只表示『本轮静态证据里没有发现已知风险』；旧 24 题的隐藏测试内容与初态脏树未查，不能读成 pass。",
        "tier_counts_by_group": {g: dict(collections.Counter(r["risk_tier"] for r in out if r["group"] == g))
                                 for g in ("core24", "night_expansion24")},
        "tasks": out,
    }
    (PKG / "r2e_task_facts.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("wrote r2e_task_facts.json", len(out))
    print(json.dumps({k: doc[k] for k in ("flag_counts", "tier_counts", "tier_counts_by_group")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
