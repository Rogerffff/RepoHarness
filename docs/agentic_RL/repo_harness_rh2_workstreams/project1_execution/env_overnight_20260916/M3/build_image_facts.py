#!/usr/bin/env python3
"""把机器 3 采回的原始观测目录聚合成逐题 JSON。

输入：runs/env_overnight_20260916/M3/facts/<commit12>/{image_summary.txt,facts/*,asuser.txt,collect.txt,r2e_tests/}
输出：runs/env_overnight_20260916/M3/r2e_image_facts.json
只读本地文件，不连机器。
"""
import json, os, re, sys, hashlib
from collections import Counter, defaultdict

ROOT = "."
FACTS = os.path.join(ROOT, "runs/env_overnight_20260916/M3/facts")
L4 = os.path.join(ROOT, "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L4_r2e")
OUT = os.path.join(ROOT, "runs/env_overnight_20260916/M3/r2e_image_facts.json")
ANSI = re.compile(r"\x1b\[[0-9;]*m")
STDLIB_HINT = set("""asyncio base64 contextlib contextvars hashlib logging os pathlib platform signal socket ssl subprocess sys tempfile time typing unittest uuid json re io math itertools functools collections shutil textwrap warnings copy pickle random string threading datetime gc glob inspect operator struct types weakref abc argparse array binascii bisect calendar cgi codecs concurrent csv ctypes decimal difflib dis email enum errno fnmatch fractions ftplib gettext gzip heapq hmac html http imp importlib ipaddress keyword linecache locale lzma marshal mimetypes mmap multiprocessing numbers operator optparse os.path pdb pkgutil posixpath pprint profile pty queue quopri runpy sched secrets select selectors shelve shlex site smtplib sqlite3 stat statistics stringprep sunau symtable sysconfig tarfile telnetlib termios test textwrap threading timeit token tokenize trace traceback tracemalloc tty turtle unicodedata urllib uu venv wave weakref webbrowser wsgiref xdrlib xml xmlrpc zipapp zipfile zipimport zlib builtins __future__""".split())
THIRD_PARTY_HINT = set("pytest mock hypothesis trustme numpy pandas PIL scrapy Orange coverage datalad aiohttp yarl multidict attr attrs freezegun requests six setuptools pkg_resources".split())


def body(path):
    """读取 run() 生成的文件，去掉 ### CMD / ### RC 包裹，返回 (正文, rc)。"""
    if not os.path.exists(path):
        return None, None
    txt = open(path, encoding="utf-8", errors="replace").read()
    rc = None
    m = re.search(r"### RC=(\d+)\s*$", txt)
    if m:
        rc = int(m.group(1))
        txt = txt[: m.start()]
    txt = re.sub(r"^### CMD:.*\n", "", txt, count=1)
    return txt, rc


def prime_key(nodeid: str) -> str:
    return ANSI.sub("", ".".join(nodeid.split("::")[1:])).split(" - ")[0]


def parse_stat(txt):
    out = {}
    for ln in (txt or "").splitlines():
        p = ln.split()
        if len(p) >= 5 and p[0].startswith("/"):
            out[p[0]] = {"owner": p[1], "uidgid": p[2], "mode": p[3], "type": " ".join(p[4:])}
    return out


def parse_asuser(txt):
    out = {"id": None, "paths": {}, "writes": {}}
    for ln in (txt or "").splitlines():
        if ln.startswith("uid="):
            out["id"] = ln.strip()
        m = re.match(r"PATH=(\S+) r=(\w+) w=(\w+) x=(\w+)", ln)
        if m:
            out["paths"][m.group(1)] = {"r": m.group(2), "w": m.group(3), "x": m.group(4)}
        elif ln.startswith("PATH=") and "MISSING" in ln:
            out["paths"][ln.split()[0][5:]] = {"missing": True}
        m2 = re.match(r"TOUCH (\S+) (OK|DENIED)", ln)
        if m2:
            out["writes"][m2.group(1)] = m2.group(2)
    return out


def build(c12, d):
    rec = {"commit12": c12}
    st = open(os.path.join(d, "_STATUS")).read().strip() if os.path.exists(os.path.join(d, "_STATUS")) else "MISSING"
    rec["collect_status"] = st
    F = os.path.join(d, "facts")

    # ---- 镜像 ----
    p = os.path.join(d, "image_summary.txt")
    if os.path.exists(p):
        parts = open(p).read().strip().split("|")
        rec["image"] = {"id": parts[0], "repo_digest": parts[1], "size_bytes": int(parts[2]),
                        "config_user": parts[3].strip('"'), "cmd": parts[4], "entrypoint": parts[5],
                        "workdir": parts[6], "created": parts[7] if len(parts) > 7 else None}

    # ---- 属主 / 候选可写 ----
    rec["ownership"] = parse_stat(body(os.path.join(F, "stat.txt"))[0])
    rec["agent_uid54322"] = parse_asuser(open(os.path.join(d, "asuser.txt"), errors="replace").read()
                                         if os.path.exists(os.path.join(d, "asuser.txt")) else "")

    # ---- run_tests.sh ----
    rts = os.path.join(F, "run_tests_sh.txt")
    meta, _ = body(os.path.join(F, "run_tests_meta.txt"))
    r = {"text": open(rts, errors="replace").read() if os.path.exists(rts) else None}
    if meta:
        m = re.search(r"^([0-9a-f]{64})\s+/testbed/run_tests\.sh", meta, re.M)
        r["sha256"] = m.group(1) if m else None
        m = re.search(r"^(\S+)\s+\d+\s+(\S+)\s+(\S+)\s+(\d+).*run_tests\.sh", meta, re.M)
        if m:
            r["mode_str"], r["owner"] = m.group(1), m.group(2) + ":" + m.group(3)
            r["bytes"] = int(m.group(4))
        r["other_sh"] = sorted(set(re.findall(r"/testbed/(\w[\w.-]*\.sh)", meta)))
    if r.get("text"):
        r["uses_xvfb"] = "xvfb" in r["text"]
        r["entry_kind"] = "pytest" if "-m pytest" in r["text"] else ("custom" if "python" in r["text"] else "other")
    rec["run_tests_sh"] = r

    # ---- /r2e_tests ----
    lst, _ = body(os.path.join(F, "r2e_tests_list.txt"))
    sha, _ = body(os.path.join(F, "r2e_tests_sha.txt"))
    files = []
    for ln in (lst or "").splitlines():
        p2 = ln.split()
        if len(p2) >= 5 and p2[0] == "f":
            files.append({"path": p2[1], "size": int(p2[2]), "mode": p2[3], "owner": p2[4]})
    shas = {}
    for ln in (sha or "").splitlines():
        p2 = ln.split(None, 1)
        if len(p2) == 2 and len(p2[0]) == 64:
            shas[p2[1].strip().lstrip("./")] = p2[0]
    for f in files:
        f["sha256"] = shas.get(f["path"].replace("/r2e_tests/", ""))
    names = [os.path.basename(f["path"]) for f in files]
    test_mods = [n for n in names if re.match(r"test_.*\.py$", n)]
    rec["r2e_tests"] = {
        "files": files, "n_files": len(files), "basenames": sorted(names),
        "n_test_modules": len(test_mods), "test_modules": sorted(test_mods),
        "has_conftest": "conftest.py" in names,
        "has_custom_runner": any("runner" in n for n in names),
        "other_py": sorted(n for n in names if n.endswith(".py") and n not in test_mods and n not in ("conftest.py", "__init__.py")),
        "non_py": sorted(n for n in names if not n.endswith(".py")),
    }

    # ---- import 目标 / fixture 依赖 ----
    tgt, _ = body(os.path.join(F, "r2e_import_targets.txt"))
    targets = [t.strip() for t in (tgt or "").splitlines() if t.strip()]
    rec["imports"] = {"all": targets}
    origins = []
    op2 = os.path.join(d, "import_origins2.json")   # pass2: sys.path 含 /testbed，结果可信
    op = os.path.join(F, "import_origins.json")     # pass1: sys.path 缺 /testbed，仓库模块解析失败
    for cand in (op2, op):
        if os.path.exists(cand):
            try:
                origins = json.load(open(cand))
                rec.setdefault("_import_origin_source", os.path.basename(cand))
                break
            except Exception:
                origins = []
    rec["imports"]["origins"] = origins
    repo_src, repo_test = [], []
    for o in origins:
        og = o.get("origin") or ""
        if og.startswith("/testbed/") and "/.venv/" not in og:
            rel = og[len("/testbed/"):]
            repo_src.append({"module": o["module"], "rel": rel, "mode": o.get("mode"), "uid": o.get("uid"),
                             "dir_mode": o.get("dir_mode"), "dir_uid": o.get("dir_uid")})
            if re.search(r"(^|/)(tests?|testing|_test|test_)", rel) or "test_utils" in rel or "testutils" in rel:
                repo_test.append(rel)
    rec["imports"]["repo_local_modules"] = repo_src
    rec["imports"]["repo_test_modules"] = sorted(set(repo_test))
    rec["imports"]["repo_test_module_names"] = sorted({t for t in targets
                                                       if re.search(r"(\.|^)tests?(\.|$)|test_utils|testutils|conftest|testing", t)
                                                       and t.split(".")[0] not in STDLIB_HINT})

    # ---- venv / 包来源 ----
    po, _ = body(os.path.join(F, "pkg_origin.txt"))
    pv, _ = body(os.path.join(F, "pyver.txt"))
    pth, _ = body(os.path.join(F, "pth.txt"))
    egg, _ = body(os.path.join(F, "egg.txt"))
    plug, _ = body(os.path.join(F, "pip_plugins.txt"))
    ptv, _ = body(os.path.join(F, "pytest_version.txt"))
    osr, _ = body(os.path.join(F, "osrelease.txt"))
    fz = os.path.join(F, "pip_freeze.txt")
    m = re.search(r"^FILE=(.*)$", po or "", re.M)
    pkg_file = m.group(1) if m else None
    mv = re.search(r"^VER=(.*)$", po or "", re.M)
    rec["venv"] = {
        "python": (re.search(r"Python \S+", pv or "") or [None])[0] if re.search(r"Python \S+", pv or "") else None,
        "pkg_file": pkg_file,
        "pkg_version": mv.group(1) if mv else None,
        "pkg_in_testbed_src": bool(pkg_file and pkg_file.startswith("/testbed/") and "/.venv/" not in pkg_file),
        "pth_files": sorted(set(re.findall(r"(/testbed/\.venv/\S+\.pth)", pth or ""))),
        "editable_markers": sorted(set(re.findall(r"(/testbed/\S*(?:egg-info|egg-link|__editable__\S*))", egg or ""))),
        # pytest>=5 打印 "pytest 8.3.4"，pytest 4.x 打印 "This is pytest version 4.6.6, imported from ..."
        "pytest_version": (lambda m: m.group(1) if m else None)(
            re.search(r"pytest (?:version )?([0-9][^\s,]*)", ptv or "")),
        # pytest --version 在没有 pip 的 venv 里也能列出已注册插件，是比 pip list 更可靠的插件证据
        "registered_plugins": sorted(set(re.findall(r"^\s{2}([A-Za-z0-9_.-]+-[0-9][^\s]*) at ", ptv or "", re.M))),
        "plugins": sorted({ln.split()[0] for ln in (plug or "").splitlines() if ln.strip() and not ln.startswith("###")}),
        "os": (osr or "").splitlines()[0].replace('PRETTY_NAME=', '').strip('"') if osr else None,
        "pip_freeze_lines": sum(1 for _ in open(fz, errors="replace")) if os.path.exists(fz) else None,
    }
    fz_txt = open(fz, errors="replace").read() if os.path.exists(fz) else ""
    rec["venv"]["pip_available"] = "No module named pip" not in fz_txt
    if not rec["venv"]["pip_available"]:
        # 27/48 镜像的 venv 里没有 pip：pip list / pip freeze 无输出，plugins 字段不可信，
        # 顺序相关插件改用「运行输出 + addopts」判定。
        rec["venv"]["plugins"] = []
        rec["venv"]["pip_freeze_lines"] = None
    risky = [p for p in rec["venv"]["plugins"] if re.match(r"pytest-(randomly|xdist|timeout|forked|order|repeat|rerunfailures)$", p)]
    risky += [p.rsplit("-", 1)[0] for p in rec["venv"]["registered_plugins"]
              if re.match(r"(pytest-(randomly|xdist|timeout|forked|order|repeat|rerunfailures)|flaky)-", p)]
    # 直接证据：noop 运行输出里的 xdist banner / addopts 里的 -n<N>
    np = os.path.join(d, "noop_x2", "out1.txt")
    run_txt = open(np, errors="replace").read() if os.path.exists(np) else ""
    if "bringing up nodes" in run_txt or re.search(r"\bgw\d\b", run_txt):
        if "pytest-xdist(runtime)" not in risky:
            risky.append("pytest-xdist(runtime)")
    rec["venv"]["order_affecting_plugins"] = sorted(set(risky))

    # ---- git / 泄漏面 ----
    gh, _ = body(os.path.join(F, "git_head.txt"))
    gf, _ = body(os.path.join(F, "git_fix.txt"))
    gc, _ = body(os.path.join(F, "git_contains.txt"))
    gr, _ = body(os.path.join(F, "git_refs.txt"))
    grm, _ = body(os.path.join(F, "git_remote.txt"))
    gl, _ = body(os.path.join(F, "git_log.txt"))
    gff, _ = body(os.path.join(F, "git_fix_files.txt"))
    br = []
    tg = []
    sec = None
    for ln in (gc or "").splitlines():
        if ln.startswith("--branches--"): sec = "b"; continue
        if ln.startswith("--tags--"): sec = "t"; continue
        if ln.startswith("--describe--"): sec = "d"; continue
        s = ln.strip()
        if not s: continue
        if sec == "b": br.append(s)
        elif sec == "t": tg.append(s)
    local_br = [b for b in br if not b.startswith("remotes/")]
    rec["git"] = {
        "head": (re.search(r"^([0-9a-f]{40})$", (gh or "").strip().splitlines()[0] if (gh or "").strip() else "", re.M) or [None]) and ((gh or "").strip().splitlines() or [None])[0],
        "head_subject": (re.search(r"^[0-9a-f]{40} (.*)$", gh or "", re.M) or [None, None])[1],
        "fix_object_type": ((gf or "").strip().splitlines() or [None])[0],
        "fix_subject": next((l for l in (gf or "").splitlines()[1:2]), None),
        "rev_count_head_to_fix": next((l.strip() for l in (gf or "").splitlines() if re.fullmatch(r"\d+", l.strip())), None),
        "head_is_ancestor_of_fix": (re.search(r"HEAD_IS_ANCESTOR_OF_FIX=(\w+)", gf or "") or [None, None])[1],
        "branches_containing_fix": br[:20],
        "local_branches_containing_fix": local_br,
        "n_branches_containing_fix": len(br),
        "tags_containing_fix": tg[:10],
        "describe_contains": next((l.strip() for l in (gc or "").splitlines()[::-1] if l.strip() and not l.startswith("--")), None),
        "remote_urls": sorted(set(re.findall(r"(https?://\S+|git@\S+)", grm or ""))),
        "refs_total": (re.search(r"refs_total=(\d+)", gr or "") or [None, None])[1],
        "tags_total": (re.search(r"tags=(\d+)", gr or "") or [None, None])[1],
        "branches_total": (re.search(r"branches=(\d+)", gr or "") or [None, None])[1],
        "packed_refs": (re.search(r"packed_refs=(\d+)", gr or "") or [None, None])[1],
        "rev_list_all_count": next((l.strip() for l in (gl or "").split("--all_count--")[1].splitlines() if l.strip()), None) if "--all_count--" in (gl or "") else None,
        "reflog_lines": next((l.strip() for l in (gl or "").split("--reflog--")[1].splitlines() if l.strip()), None) if "--reflog--" in (gl or "") else None,
        "log_all_head5": [l for l in (gl or "").split("--all_count--")[0].splitlines() if l.strip()][:5],
        "fix_files": [l.strip() for l in (gff or "").splitlines() if l.strip()],
    }

    # ---- 初态脏树 ----
    sp, _ = body(os.path.join(F, "status_porcelain.txt"))
    tracked, untracked = [], []
    for ln in (sp or "").split("--lines--")[0].splitlines():
        if not ln.strip(): continue
        code, _, path = ln[:2], ln[2:3], ln[3:].strip()
        if code == "??":
            untracked.append(path)
        elif code.strip():
            tracked.append({"code": code.strip(), "path": path})
    db = open(os.path.join(F, "initial_diff_bytes.txt")).read().split()[0] if os.path.exists(os.path.join(F, "initial_diff_bytes.txt")) else None
    ds, _ = body(os.path.join(F, "diff_stat.txt"))
    rec["initial_worktree"] = {
        "tracked_modified": tracked, "n_tracked_modified": len(tracked),
        "untracked": untracked, "n_untracked": len(untracked),
        "diff_bytes": int(db) if db and db.isdigit() else None,
        "diff_stat_tail": [l for l in (ds or "").splitlines() if l.strip()][-1:],
        "clean": len(tracked) == 0 and len(untracked) == 0,
    }

    # ---- 其它答案材料 ----
    fe, _ = body(os.path.join(F, "find_expected.txt"))
    hits = [l.strip() for l in (fe or "").splitlines() if l.strip() and not l.startswith("/tmp/m3out")]
    rec["other_answer_material"] = {"find_hits": hits, "beyond_r2e_tests": [h for h in hits if not h.startswith("/r2e_tests")]}
    gd, _ = body(os.path.join(F, "git_dir.txt"))
    rec["git_dir_size"] = (re.search(r"^(\S+)\s+/testbed/\.git$", gd or "", re.M) or [None, None])[1]

    # ---- pytest 收集配置 ----
    pc, _ = body(os.path.join(F, "pytest_cfg.txt"))
    present = {}
    for f in ("conftest.py", "pytest.ini", "setup.cfg", "tox.ini", "pyproject.toml"):
        present[f] = ("/testbed/" + f) in (pc or "") and "No such file" not in "".join(
            [l for l in (pc or "").splitlines() if f in l and "----grep----" not in l][:1])
    cfg_lines = [l.strip() for l in (pc or "").split("----grep----")[-1].splitlines() if l.strip()]
    # 注意：grep 出来的行形如 "<file>:<lineno>:<正文>"，要剥掉前缀再判注释，否则把注释掉的 addopts 当成生效配置
    def _payload(l):
        parts = l.split(":", 2)
        return parts[2].strip() if len(parts) == 3 else l.strip()
    ao_lines = [l for l in cfg_lines
                if "addopts" in l and not _payload(l).startswith("#") and not _payload(l).rstrip().endswith("addopts =")]
    rec["pytest_config"] = {"files_present": present, "grep": cfg_lines[:25],
                            "addopts_lines": ao_lines,
                            "has_addopts": bool(ao_lines),
                            "addopts_parallel": bool([l for l in ao_lines if re.search(r"-n\s*\d", l)]),
                            "addopts_flaky": bool([l for l in ao_lines if "flaky" in l]),
                            "addopts_failed_first": bool([l for l in ao_lines if "failed-first" in l]),
                            "has_testpaths": any("testpaths" in l for l in cfg_lines)}

    # ---- 资源 ----
    tc, _ = body(os.path.join(F, "testbed_count.txt"))
    nums = [l.strip() for l in (tc or "").splitlines() if l.strip()]
    rec["resources"] = {"testbed_entries": nums[0] if nums else None,
                        "testbed_entries_no_git": nums[2] if len(nums) > 2 else None,
                        "testbed_du": nums[-1].split()[0] if nums and "\t" in nums[-1] else (nums[-1].split()[0] if nums else None)}

    # ---- xvfb ----
    xv, _ = body(os.path.join(F, "xvfb.txt"))
    rec["xvfb"] = {"xvfb_run": "/xvfb-run" in (xv or ""), "Xvfb": "/Xvfb" in (xv or ""),
                   "qt_qpa": (re.search(r"QT_QPA_PLATFORM=(\S*)", xv or "") or [None, ""])[1]}

    # ---- M-11 收集与 Prime 键碰撞 ----
    cp = os.path.join(d, "collect.txt")
    col = {"status": "not_checked"}
    if os.path.exists(cp):
        txt = open(cp, errors="replace").read()
        rcx = open(os.path.join(d, "collect_rc.txt")).read().strip() if os.path.exists(os.path.join(d, "collect_rc.txt")) else ""
        nodeids = [l.strip() for l in txt.splitlines() if re.match(r"^r2e_tests/\S+\.py::", l.strip())]
        m = re.search(r"(\d+) tests? collected", txt)
        errm = re.search(r"(\d+) errors?", txt)
        keys = Counter(prime_key(n) for n in nodeids)
        dup = {k: v for k, v in keys.items() if v > 1}
        dup_src = {}
        if dup:
            bysrc = defaultdict(list)
            for n in nodeids:
                bysrc[prime_key(n)].append(n)
            dup_src = {k: bysrc[k] for k in dup}
        col = {"status": "pass" if (m and not dup) else ("issue" if dup else ("unknown" if not m else "pass")),
               "rc": rcx, "reported_collected": int(m.group(1)) if m else None,
               "n_nodeids": len(nodeids), "n_prime_keys": len(keys),
               "n_collision_keys": len(dup), "collisions": {k: dup_src[k][:4] for k in list(dup)[:10]},
               "collect_errors": int(errm.group(1)) if errm else 0,
               "files_seen": sorted({n.split("::")[0] for n in nodeids}),
               "tail": txt.strip().splitlines()[-3:]}
    rec["collect_only"] = col

    # ---- pass2：候选身份能否执行入口、解释器属主链 ----
    p2 = {"status": "not_checked"}
    ap = os.path.join(d, "asuser_exec.txt")
    if os.path.exists(ap):
        t = open(ap, errors="replace").read()
        p2 = {
            "status": "pass" if "OK" in t else "issue",
            "venv_python_exec_denied": "Permission denied" in t.split("### run pytest entry")[0],
            "venv_python_out": [l for l in t.split("### run venv python")[1].split("### run pytest")[0].splitlines() if l.strip()][:2] if "### run venv python" in t else [],
            "root_listable": "Permission denied" not in (t.split("### ls /root")[1].split("###")[0] if "### ls /root" in t else "x Permission denied"),
            "run_tests_readable": bool(re.search(r"### read run_tests\.sh\n\S", t)),
            "git_usable": "dubious ownership" not in (t.split("### git status")[1].split("### write")[0] if "### git status" in t else "dubious ownership"),
            "tmp_writable": "TMP_WRITE_OK" in t,
        }
    ip = os.path.join(d, "interp.txt")
    if os.path.exists(ip):
        t = open(ip, errors="replace").read()
        rp = next((l.strip() for l in t.splitlines()[1:2]), None)
        p2["interp_realpath"] = rp
        p2["interp_under_root_home"] = bool(rp and rp.startswith("/root/"))
        m = re.search(r"^/root root:root 0:0 (\d+)", t, re.M)
        p2["root_home_mode"] = m.group(1) if m else None
        m2 = re.search(r"^(/\S+)\n(/\S+)\n(\[.*\])\s*$", t, re.M | re.S)
        sp = re.findall(r"'([^']+)'", t.split("### sys.prefix/base_prefix")[-1]) if "### sys.prefix/base_prefix" in t else []
        p2["sys_path"] = sp
        p2["sys_path_under_root_home"] = [x for x in sp if x.startswith("/root/")]
    rec["agent_exec_probe"] = p2
    return rec


def main():
    tasks = {t["commit_hash"][:12]: t for t in json.load(open(os.path.join(L4, "r2e_tasks_48.json")))["tasks"]}
    l4f = {t["commit_hash"][:12]: t for t in json.load(open(os.path.join(L4, "r2e_task_facts.json")))["tasks"]}
    out = []
    for c12 in sorted(os.listdir(FACTS)):
        d = os.path.join(FACTS, c12)
        if not os.path.isdir(d):
            continue
        rec = build(c12, d)
        t = tasks.get(c12, {})
        rec["task_id"] = t.get("task_id", "r2e::" + c12)
        rec["repo"] = t.get("repo")
        rec["group"] = t.get("group")
        rec["commit_hash"] = t.get("commit_hash")
        rec["image_ref"] = t.get("image_ref")
        rec["source"] = t.get("source")
        rec["source_revision"] = t.get("source_revision")
        rec["task_revision"] = "upstream"
        rec["expected_n"] = t.get("expected_n")
        rec["expected_status_counts"] = t.get("expected_status_counts")
        f4 = l4f.get(c12, {})
        rec["l4_expected"] = f4.get("expected")
        rec["l4_gold_patch"] = f4.get("gold_patch")
        rec["l4_commit_content"] = f4.get("commit_content")
        out.append(rec)
    doc = {"schema": "rh2.env_overnight.m3.r2e_image_facts.v1",
           "generated_by": "docs/.../env_overnight_20260916/M3/build_image_facts.py",
           "machine": "机器 3",
           "n": len(out), "tasks": out}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("wrote", OUT, len(out))


if __name__ == "__main__":
    main()
