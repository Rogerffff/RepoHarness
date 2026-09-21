#!/usr/bin/env python3
"""把机器 3 的原始观测折成 COMMON.md §1 的题级记录（checks 用 machine_checks.md 的 M-01…M-13 编号）。

输入：runs/env_overnight_20260916/M3/{r2e_image_facts.json,noop_repeat.json}
输出：docs/.../env_overnight_20260916/M3/M3_r2e_check_records.json
"""
import json, os, re
from collections import Counter

ROOT = "."
RUNS = os.path.join(ROOT, "runs/env_overnight_20260916/M3")
PKG = os.path.join(ROOT, "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/M3")
OUT = os.path.join(PKG, "M3_r2e_check_records.json")
EV = "runs/env_overnight_20260916/M3/facts/{c}"          # 本机大文件目录（相对仓库根）
BY = "M3"


def main():
    COLLIDE = json.load(open(os.path.join(PKG, "M3_key_collisions.json")))
    SCRUB = json.load(open(os.path.join(PKG, "M3_git_scrub_probe.json")))
    GAS = json.load(open(os.path.join(PKG, "M3_gold_after_scrub.json")))
    LEAK = json.load(open(os.path.join(PKG, "M3_leak_path_probe.json")))
    UF = json.load(open(os.path.join(PKG, "M3_uid_fix_probe.json")))
    UID_BY = {}
    for r in UF["runs"]:
        UID_BY.setdefault(r["commit12"], []).append(r)
    GR = {t["commit12"]: t for t in json.load(open(os.path.join(PKG, "M3_gold_repeat.json")))["tasks"]}
    UN = {}
    up = os.path.join(RUNS, "unrelated_ledger", "r2e_unrelated_m3.jsonl")
    if os.path.exists(up):
        for ln in open(up):
            r = json.loads(ln)
            UN[r["commit_hash"][:12]] = r
    GOLD = {}
    gp = os.path.join(RUNS, "gold_ledger", "r2e_gold_m3.jsonl")
    if os.path.exists(gp):
        for ln in open(gp):
            r = json.loads(ln)
            GOLD[r["commit_hash"][:12]] = r
    F = {t["commit12"]: t for t in json.load(open(os.path.join(RUNS, "r2e_image_facts.json")))["tasks"]}
    N = {t["commit12"]: t for t in json.load(open(os.path.join(RUNS, "noop_repeat.json")))["tasks"]}
    pkgsrc = {}
    for c in F:
        p = os.path.join(RUNS, "facts", c, "pkgsrc.txt")
        if os.path.exists(p):
            txt = open(p, errors="replace").read()
            tb = txt.split("### import from /testbed")[1].split("### import from /tmp")[0].strip().splitlines()[-1]
            tm = txt.split("### import from /tmp")[1].split("### import from /")[0].strip().splitlines()[-1]
            pkgsrc[c] = {"cwd_testbed": tb, "cwd_tmp": tm, "cwd_dependent": tb != tm}

    recs = []
    for c, b in sorted(F.items(), key=lambda kv: (kv[1]["repo"], kv[0])):
        n = N[c]
        ev = EV.format(c=c)
        ck = {}

        def put(k, status, note, refs, **extra):
            ck[k] = dict(status=status, evidence_refs=refs, note=note, by=BY, **extra)

        # M-01 /r2e_tests 完整内容
        rt = b["r2e_tests"]
        imports_helper = b["imports"]["repo_test_module_names"]
        put("M-01", "issue" if imports_helper else "pass",
            f"{rt['n_files']} 个文件 {rt['basenames']}；隐藏测试 import 的仓库测试支撑模块={imports_helper or '无'}",
            [f"{ev}/r2e_tests/", f"{ev}/facts/r2e_tests_list.txt", f"{ev}/facts/r2e_tests_sha.txt", f"{ev}/import_origins2.json"])
        # M-02 run_tests.sh
        r = b["run_tests_sh"]
        put("M-02", "pass",
            f"mode={r.get('mode_str')} owner={r.get('owner')} bytes={r.get('bytes')} sha256={r.get('sha256')}；"
            f"入口={r.get('entry_kind')}；候选身份(uid 54322)不可写（/testbed 755 root）",
            [f"{ev}/facts/run_tests_sh.txt", f"{ev}/facts/run_tests_meta.txt", f"{ev}/asuser.txt"])
        # M-03 venv 属主 / 可写 / 测的是不是候选代码
        ps = pkgsrc.get(c, {})
        put("M-03", "issue",
            f"/testbed=755 root:root；uid 54322 对 /testbed、/r2e_tests、.venv/bin 全部不可写；"
            f"解释器真实路径 {b['agent_exec_probe'].get('interp_realpath')} 位于 /root（mode 700）→ 候选身份无法执行测试解释器；"
            f"目标包 __file__={b['venv']['pkg_file']}（在 /testbed 源码树内）；"
            f"cwd 依赖={ps.get('cwd_dependent')}"
            + (("；【第二片修法实测】本题做了布置 "
                + "/".join(sorted({x["mode"] for x in UID_BY[c]}))
                + "，uid 54322 的 noop 与 gold 结果与 root 基线逐键相同；"
                + "布置 b（搬迁解释器到 /opt + chown -R /testbed /r2e_tests + git safe.directory）耗时："
                + f"chown {next((x['arrange']['t_chown_ms'] for x in UID_BY[c] if x['mode'] == 'b'), '?')}"
                + f"（{next((x['arrange']['chown_paths'] for x in UID_BY[c] if x['mode'] == 'b'), '?')} 条目）"
                + f" + 复制解释器 {next((x['arrange']['t_copy_interp_ms'] for x in UID_BY[c] if x['mode'] == 'b'), '?')}"
                + f"，overlay2 copy-up 使容器可写层涨到 {next((x['container_layer_size'] for x in UID_BY[c] if x['mode'] == 'b'), '?')}"
                + "；但布置本身挡不住候选把 run_tests.sh unlink 后替换、把 /testbed/r2e_tests 整个 mv 走"
                + "（替换攻击只在 numpy 18b7cd9df7a4 与 pillow 3ac9396e8c99 上实测，见 M3_uid_fix_probe.json 的 grading_surface_attack）")
               if c in UID_BY else "；本题未做第二片修法实测"),
            [f"{ev}/facts/stat.txt", f"{ev}/asuser.txt", f"{ev}/asuser_exec.txt", f"{ev}/interp.txt",
             f"{ev}/pkgsrc.txt"] + ([f"{ev}/uidfix/"] if c in UID_BY else []))
        # M-04 依赖快照
        pipav = b["venv"]["pip_available"]
        put("M-04", "issue" if (b["venv"]["order_affecting_plugins"] or not pipav) else "pass",
            f"{b['venv']['os']} / {b['venv']['python']} / pytest {b['venv']['pytest_version']}；"
            f"venv 里有 pip={pipav}"
            + ("（无 pip → pip freeze/list 无输出，依赖快照只能靠 import 探测；候选也装不了包）" if not pipav else
               f"，pip freeze {b['venv']['pip_freeze_lines']} 行") +
            f"；顺序相关插件={b['venv']['order_affecting_plugins'] or '无'}"
            f"（判定来源：pip list + noop 输出的 xdist banner + addopts）",
            [f"{ev}/facts/pip_freeze.txt", f"{ev}/facts/pip_plugins.txt", f"{ev}/facts/pytest_version.txt",
             f"{ev}/noop_x2/out1.txt"])
        # M-05 修复提交可发现性
        g = b["git"]
        put("M-05", "issue",
            f"本地分支 {g['local_branches_containing_fix']} 含修复提交；含该提交的 tag {len(g['tags_containing_fix'])}+ 个；"
            f"remote={g['remote_urls']}；HEAD..fix={g['rev_count_head_to_fix']} 个提交；refs={g['refs_total']} tags={g['tags_total']}"
            + (f"；HEAD 游离={LEAK[c]['detached']}，修复提交是 HEAD 的直接子提交="
               f"{LEAK[c]['fix_in_children']}，`git rev-list --children --all | grep ^$(git rev-parse HEAD)` "
               f"给出 {LEAK[c]['n_children']} 个子提交、修复提交排第 {LEAK[c]['fix_rank']}"
               f"（不需要知道哈希、不需要网络）" if c in LEAK else "")
            + (f"；清理实验（分离 HEAD + 删全部 ref/tag/remote + expire reflog + gc --prune=now）后："
               f"refs {SCRUB[c]['before']['refs']}→{SCRUB[c]['after']['refs']}、"
               f"tags {SCRUB[c]['before']['tags']}→{SCRUB[c]['after']['tags']}、"
               f"修复提交对象 `{SCRUB[c]['after']['fix_object'][:46]}`、"
               f".git {SCRUB[c]['before']['git_du']}→{SCRUB[c]['after']['git_du']}、"
               f"noop 键集与状态不变={SCRUB[c]['noop_identical']}" if c in SCRUB else ""),
            [f"{ev}/facts/git_contains.txt", f"{ev}/facts/git_refs.txt", f"{ev}/facts/git_remote.txt",
             f"{ev}/facts/git_log.txt", f"{ev}/git_scrub/"],
            severity="P1")
        # M-06 初态脏树
        iw = b["initial_worktree"]
        put("M-06", "issue",
            f"初态非干净树：已跟踪改动 {[m['code']+' '+m['path'] for m in iw['tracked_modified']] or '无'}；"
            f"未跟踪 {iw['untracked']}；diff {iw['diff_bytes']} 字节",
            [f"{ev}/facts/status_porcelain.txt", f"{ev}/facts/initial.diff", f"{ev}/facts/untracked.txt"])
        # M-07 隐藏测试依赖模块的可写范围
        rl = [x["rel"] for x in b["imports"]["repo_local_modules"]]
        put("M-07", "issue" if imports_helper else "pass",
            f"隐藏测试 import 的仓库内文件 {sorted(rl)}；其中测试支撑模块 {imports_helper or '无'}；"
            f"这些文件 root:root 644/755，候选身份当前不可写，但一旦 rh2 把 /testbed 交给候选用户即成为可写评分控制面",
            [f"{ev}/import_origins2.json", f"{ev}/facts/r2e_imports.txt"],
            severity="P1" if imports_helper else "P3")
        # M-08 其它答案材料
        put("M-08", "pass" if not b["other_answer_material"]["beyond_r2e_tests"] else "issue",
            f"/r2e_tests 之外未发现 expected/gold 材料；命中={b['other_answer_material']['beyond_r2e_tests'] or '无'}；"
            f".git 体积 {b['git_dir_size']}",
            [f"{ev}/facts/find_expected.txt", f"{ev}/facts/ls_slash.txt", f"{ev}/facts/git_dir.txt"])
        # M-09 默认网络出网：本包纪律要求 --network none，未做
        put("M-09", "not_checked",
            "本包机器纪律要求全部容器 --network none，未做默认网络实验；"
            "但 M-05 已证明离线就能从本地分支拿到修复提交，出网与否不改变泄漏结论",
            [])
        # M-10 收集配置
        pc = b["pytest_config"]
        addopts = [l for l in pc["grep"] if "addopts" in l and not l.strip().endswith("addopts =")]
        put("M-10", "issue" if addopts else "pass",
            f"rootdir=/testbed；conftest.py(根)={pc['files_present'].get('conftest.py')}；"
            f"addopts={addopts or '无'}",
            [f"{ev}/facts/pytest_cfg.txt", f"{ev}/pkgsrc.txt"])
        # M-11 折键碰撞（以来源入口实跑摘要为准，collect-only 只作旁证）
        co = b["collect_only"]
        cl = COLLIDE.get(c, {})
        put("M-11", "pass" if cl.get("dup") == {} else "unknown",
            f"来源入口实跑摘要 {cl.get('summary_lines')} 行 → Prime 折键 {cl.get('prime_keys')} 个，"
            f"碰撞 {cl.get('dup')}，跨文件碰撞 {cl.get('crossfile')}；"
            f"旁证 --collect-only 报数 {co['reported_collected']}（rc={co['rc']}）——本轮 collect-only 沿用仓库 addopts，"
            f"多数题没有 -q，输出的是收集树而非 node id（本题解析出 {co['n_nodeids']} 条），故碰撞判定只用实跑摘要",
            [f"{ev}/noop_x2/out1.txt", f"{ev}/collect.txt"])
        # M-12 重复一致性与实跑（noop×2 + gold×1 + 清理后 gold×1）
        g1 = GOLD.get(c, {})
        gd = g1.get("reward_details") or {}
        ga = GAS.get(c, {})
        put("M-12", "pass" if n.get("run1_eq_run2") else "unknown",
            f"同一容器内连跑两次 noop：键集与状态完全一致={n.get('run1_eq_run2')}；"
            f"parsed={n.get('parsed_n1')} expected={n.get('expected_n')} "
            f"missing={n['vs_expected1']['n_missing']} extra={n['vs_expected1']['n_extra']} "
            f"判别键(n_mismatch)={n['vs_expected1']['n_mismatch']}；noop reward={n.get('noop_reward1')}/{n.get('noop_reward2')}；"
            f"t={n.get('t1')}s/{n.get('t2')}s；SKIPPED={n['drops1']['skipped_cases']} XFAIL={n['drops1']['xfail_lines']}；"
            f"gold gate（r2e_probe/0.3 副本，--network none）result={g1.get('result')} reward={g1.get('reward')} "
            f"parsed={gd.get('parsed_n')}/{gd.get('expected_n')} mismatch={gd.get('mismatch')} "
            f"patch_apply={g1.get('patch_apply')} t={g1.get('t_test')}s；"
            f"git 清理后再跑 gold：apply_rc={ga.get('apply_rc')} reward={ga.get('reward_after_scrub')} "
            f"与未清理一致={ga.get('same')}；"
            f"gold 第二次独立运行：reward={GR.get(c, {}).get('reward_a2')} 键集与状态与第一次一致="
            f"{GR.get(c, {}).get('map_identical')}（SKIPPED {GR.get(c, {}).get('drops_a1', {}).get('skipped_cases')}→"
            f"{GR.get(c, {}).get('drops_a2', {}).get('skipped_cases')}）；"
            + (f"probe_unrelated gate：reward={UN[c]['reward']} result={UN[c]['result']} "
               f"判别键数={(UN[c].get('reward_details') or {}).get('n_mismatch')}（与 noop 相同则说明无关补丁没改变任何测试）"
               if c in UN else "probe_unrelated：本题未跑（只抽了 10 题）"),
            [f"{ev}/noop_x2/out1.txt", f"{ev}/noop_x2/out2.txt", f"{ev}/noop_x2/rc.txt",
             f"runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl",
             f"runs/env_overnight_20260916/M3/gold_ledger/logs_r2e/{b['repo']}/{c}/gold/a1/",
             f"{ev}/gold_after_scrub/"])
        # M-13 图形依赖
        put("M-13", "pass",
            f"xvfb-run={b['xvfb']['xvfb_run']} Xvfb={b['xvfb']['Xvfb']}；run_tests.sh 用 xvfb={b['run_tests_sh']['uses_xvfb']}",
            [f"{ev}/facts/xvfb.txt", f"{ev}/facts/run_tests_sh.txt"])

        issues = []
        issues.append(dict(category="leakage", severity="P1",
                           evidence_refs=[f"{ev}/facts/git_contains.txt", f"{ev}/leak_path/children.txt"],
                           note=f"修复提交是 HEAD 的直接子提交：`git rev-list --children --all | grep ^$(git rev-parse HEAD)` 一条命令列出 {LEAK.get(c,{}).get('n_children','?')} 个候选、修复提交排第 {LEAK.get(c,{}).get('fix_rank','?')}，不需要哈希也不需要网络；本地分支 {g['local_branches_containing_fix']}、含该提交的 tag 与 remote 也都在",
                           proposed_action="派生镜像时做：分离 HEAD → 删全部 ref/tag → 删 remote → reflog expire --expire=now --all → 删 packed-refs → git gc --prune=now。48/48 实测：修复提交对象被删除且 noop 评分逐键不变（M3_git_scrub_probe.json）",
                           next_experiment="在清理后的镜像上补跑 gold gate 与 probe_unrelated，确认 git apply 与 reward 不受影响"))
        issues.append(dict(category="control_surface", severity="P1",
                           evidence_refs=[f"{ev}/asuser.txt", f"{ev}/asuser_exec.txt", f"{ev}/interp.txt"],
                           note="镜像默认 root 运行；候选身份 uid 54322 既不能写 /testbed，也不能执行 /testbed/.venv/bin/python（真实解释器在 /root，mode 700），并且 git 因 dubious ownership 不可用",
                           proposed_action="方案 A 要么以 root 跑 agent（等于放弃身份隔离），要么同时 chown /testbed + 放开 /root 的遍历位或把解释器搬出 /root + 配 git safe.directory",
                           next_experiment="在派生镜像上验证 chown/权限方案后 noop 与 gold 的 reward 不变"))
        if imports_helper:
            issues.append(dict(category="grading_control_surface", severity="P1",
                               evidence_refs=[f"{ev}/import_origins2.json"],
                               note=f"隐藏测试 import 仓库自带测试支撑模块 {imports_helper}；评分只恢复 /testbed/r2e_tests，不恢复这些文件",
                               proposed_action="按 import 闭包在评分前把这些文件恢复到 base 版本（L4 报告 Q5 的选项 b）",
                               next_experiment="构造改写该模块的对照补丁，确认恢复前后 reward 变化"))
        if iw["n_tracked_modified"]:
            issues.append(dict(category="initial_state", severity="P2",
                               evidence_refs=[f"{ev}/facts/initial.diff"],
                               note=f"镜像自带未提交的已跟踪改动 {[m['path'] for m in iw['tracked_modified']]}，`git reset --hard`/`git checkout .` 会破坏环境",
                               proposed_action="候选 delta 用文件系统基线（baseline census）而不是 git diff HEAD；清理流程禁用 git 还原",
                               next_experiment="无（已由 M-06 直接证据支撑）"))
        if not pipav:
            issues.append(dict(category="environment", severity="P3",
                               evidence_refs=[f"{ev}/facts/pip_freeze.txt"],
                               note="venv 里没有 pip（`No module named pip`）：候选无法 pip install，依赖快照也取不到",
                               proposed_action="接受为环境约束并写进任务卡；若要给候选装包能力需在派生镜像里补 pip",
                               next_experiment="无"))
        if b["venv"]["order_affecting_plugins"]:
            issues.append(dict(category="determinism", severity="P2",
                               evidence_refs=[f"{ev}/facts/pip_plugins.txt", f"{ev}/facts/pytest_cfg.txt"],
                               note=f"安装了 {b['venv']['order_affecting_plugins']}，且 addopts 里带 {addopts}；--failed-first 依赖 /testbed/.pytest_cache",
                               proposed_action="评分容器每次从干净容器起，或显式 -p no:cacheprovider；记录 xdist worker 数进 reward 元数据",
                               next_experiment="同容器连跑 3 次以上并注入一次失败，观察 --failed-first 是否改变键集"))
        if b["run_tests_sh"]["entry_kind"] != "pytest":
            issues.append(dict(category="entrypoint", severity="P1",
                               evidence_refs=[f"{ev}/facts/run_tests_sh.txt", f"{ev}/collect.txt"],
                               note="入口不是 pytest（unittest_custom_runner.py）；实测用 pytest 跑该题 2 个模块都 ImportError（test_1/test_2 用绝对 `from helper import`），收集 0 个用例",
                               proposed_action="rh2 必须逐题沿用 run_tests.sh 原文，不做入口归一化",
                               next_experiment="无（已由 M-11 的 collect_rc=2 直接证据支撑）"))
        if pkgsrc.get(c, {}).get("cwd_dependent"):
            issues.append(dict(category="entrypoint", severity="P1",
                               evidence_refs=[f"{ev}/pkgsrc.txt"],
                               note=f"目标包没有装进 venv：cwd=/testbed 时 __file__={ps.get('cwd_testbed')}，cwd=/tmp 时直接 ModuleNotFoundError",
                               proposed_action="评分执行必须 cwd=/testbed，且测试路径用相对路径 r2e_tests；换 cwd 或用绝对路径会让全部用例 ERROR",
                               next_experiment="无（已由 M-03 直接证据支撑）"))

        if g1.get("reward") == 0:
            issues.append(dict(category="source_signal", severity="P1",
                               evidence_refs=[f"runs/env_overnight_20260916/M3/gold_ledger/logs_r2e/{b['repo']}/{c}/gold/a1/test_output.txt"],
                               note=f"gold gate 在机器 3 上 reward=0，判别键 {gd.get('mismatch')}：来源期望与实际执行不符",
                               proposed_action="按 L4 报告 Q1 决定（原样判 / 剔非 PASSED 键 / 本地重验证生成修订版 expected）；在决定前不要放进训练题单",
                               next_experiment="逐键归因该测试在本条件下的状态来源（conftest/fixture/依赖版本）"))

        tier = "M1" if (b["run_tests_sh"]["entry_kind"] != "pytest" or co["n_collision_keys"]) else \
               ("M2" if (imports_helper or pkgsrc.get(c, {}).get("cwd_dependent")) else
                ("M3" if (iw["n_tracked_modified"] or b["venv"]["order_affecting_plugins"]) else "M4"))
        recs.append({
            "task_id": b["task_id"], "repo": b["repo"], "commit_hash": b["commit_hash"], "commit12": c,
            "group": b["group"], "source": b["source"], "source_revision": b["source_revision"],
            "task_revision": "upstream", "image_ref": b["image_ref"],
            "image_digest": b["image"]["repo_digest"], "image_size_bytes": b["image"]["size_bytes"],
            "materials_refs": {"machine_facts": ev, "noop_x2": f"{ev}/noop_x2/",
                               "aggregate": "runs/env_overnight_20260916/M3/r2e_image_facts.json",
                               "repeat": "runs/env_overnight_20260916/M3/noop_repeat.json",
                               "l4_static": "docs/.../env_overnight_20260916/L4_r2e/r2e_task_facts.json"},
            "public_view": {"note": "本包只采镜像事实，未读题面；题面与 gold 事实见 L4 包"},
            "checks": ck, "issues": issues,
            "file_rules": {"additional_exclusions": ["r2e_tests/", ".pytest_cache/"],
                           "rationale": "评分 setup 把 /r2e_tests 拷进 /testbed/r2e_tests（48/48 实测新增未跟踪条目）；pytest 在 /testbed 生成 .pytest_cache（47/48）。二者都不是候选改动。",
                           "evidence_refs": [f"{ev}/noop_x2/status_after.txt", f"{ev}/noop_x2/cache_after.txt"]},
            "proposed_regression_tests": [
                "候选 delta 提取排除 r2e_tests/ 与 .pytest_cache/（夹具用一次实跑后的工作区快照）",
                "评分执行 cwd 必须是 /testbed：构造 cwd=/tmp 的用例断言拒绝而不是静默 0 分",
                "run_tests.sh 原文 digest 在评分前校验（M-02 已给每题 sha256）",
            ],
            "disposition_hint": {"state": "environment_exploration_only",
                                 "reason": f"tier={tier}；泄漏清理与候选身份权限两项未解决前不进训练题单",
                                 "m3_tier": tier, "m3_flags": sorted(set(
                                     (["entry_not_pytest"] if b["run_tests_sh"]["entry_kind"] != "pytest" else []) +
                                     (["imports_repo_test_helper"] if imports_helper else []) +
                                     (["cwd_dependent_import"] if pkgsrc.get(c, {}).get("cwd_dependent") else []) +
                                     (["ships_dirty_tracked"] if iw["n_tracked_modified"] else []) +
                                     (["order_affecting_plugins"] if b["venv"]["order_affecting_plugins"] else []) +
                                     (["single_discriminating_key"] if n["vs_expected1"]["n_mismatch"] <= 1 else []) +
                                     ["fix_on_local_branch", "agent_uid_cannot_exec"]))},
            "gold_gate_m3": {"result": g1.get("result"), "reward": g1.get("reward"),
                             "parsed_n": gd.get("parsed_n"), "expected_n": gd.get("expected_n"),
                             "n_mismatch": gd.get("n_mismatch"), "mismatch": gd.get("mismatch"),
                             "patch_apply": g1.get("patch_apply"), "t_test": g1.get("t_test"),
                             "runner_version": g1.get("runner_version"),
                             "after_git_scrub": {"apply_rc": ga.get("apply_rc"),
                                                 "reward": ga.get("reward_after_scrub"),
                                                 "same_as_pristine": ga.get("same")}},
            "costs": {"minutes": round((int(n.get("t1", 0)) + int(n.get("t2", 0)) + (g1.get("t_test") or 0)) / 60 + 2.0, 1)},
        })
    doc = {"schema": "rh2.env_overnight.m3.check_records.v1", "machine": "机器 3",
           "checks_numbering": "docs/.../env_overnight_20260916/L4_r2e/machine_checks.md (M-01…M-13)",
           "n": len(recs), "tasks": recs}
    json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("wrote", OUT, len(recs))
    print("tier:", Counter(r["disposition_hint"]["m3_tier"] for r in recs))
    print("status:", Counter(s["status"] for r in recs for s in r["checks"].values()))


if __name__ == "__main__":
    main()
