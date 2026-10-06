"""R2E 48 题静态筛查的固定材料（SWE-Gym 流程步骤 ①；2026-09-24 夜，Claude / B 线）。从仓库根用 rh2/.venv/bin/python 运行。

子命令：
  fetch         唯一联网的一步：8 个上游仓库各建一个裸仓库，按 base 提交浅取（git fetch --depth 1 <sha>）。
  image-hashes  在有 Docker 的机器上跑（只用标准库）：对给定镜像，列 /testbed 下"跟踪 + 未忽略的未跟踪"文件，记逐文件
                sha256 / 权限 / 软链目标，并拷出只在镜像里的未跟踪文件（install.sh 等）。镜像以 --network none 启动，只读。
  prepare       离线：读受信摄入面、git 对象与本地事实，写三个包（已有输出目录不覆盖）：
                public/<iid>/  public_bundle.json、user_prompt.txt（render_user_prompt 渲染）、environment_brief.md（中性说明）、
                               worktree/（**实际解题工作树**）与 worktree_manifest.json；
                private/<iid>/ 当前生效的隐藏测试（含修订）、expected_output.json（含修订）、gold.patch、run_tests.sh、
                               评分面 / 验证面原行、本题修订单条目、run_refs.json（只有原始运行证据，见下）；
                history/<iid>/ refs.json（环境阶段的逐题记录、findings、提案等路径；主审自己的分析保存后才开放）。
  verify        离线：重算交付工作树的实际文件，核 worktree_manifest，再与 image-hashes 的镜像记录逐文件比对，结果并入
                material_check.json；没有可核对的输入或有任何不符即返回非零。

实际解题工作树 = base 提交跟踪文件的原始 blob 字节（ls-tree + cat-file，逐个核 blob sha1；不 checkout、不用 git archive——
它的 export-subst 会改写 pandas 的 _version.py）→ 叠加 M3 事实采集在镜像内取得的 `git diff HEAD`（12 题非空：pandas ×7、
aiohttp ×5；要求干净应用，删除项保留为删除）→ 未跟踪的构建文件（run_tests.sh 取评分面原文；install.sh 等只在镜像里的文件
从 image-hashes 拷出的副本补，拿不到的记进 untracked_missing）。被 .gitignore 忽略的构建产物（编译扩展、.venv 等）与 .git
不导出。准备过程不运行题目代码。

v2（2026-09-25，Codex 批次三复核 F2 与 R2E 静态审查开工核对）：私有包不再给 `refs.json`（v1 由逐题环境记录生成，
既混入历史结论路径，又早于批次三写回，7 题的配方与材料版本是旧的），改为 `run_refs.json`：只列各账本里本题的原始运行行
（行号、候选、配方、得分、日志与摘要），并标明是否属于当前材料版本；逐题记录、findings、提案、复现脚本、facts 等历史类路径
全部移到 `history/<iid>/refs.json`。`verify` 改为重算交付工作树的实际文件（字节、权限、软链）再核清单与镜像记录，
没有可核对的输入即报失败，不再输出空的成功。

v3（2026-09-25 上午，R2E 静态审查第二批）：摄入面换成按来源区分的 R2E 提示后重新生成（pin `781363b0…`，48 题只变
`public_hints` 与 `public_bundle_digest`）；中性说明里"public_hints 与镜像不符"一句随之改为描述新提示。私有与历史包的生成方式不变。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/src/repoharness2").is_dir())
DOCS = "docs/agentic_RL/repo_harness_rh2_workstreams"
RND = f"{DOCS}/project1_execution/r2e_env_repair_20260924"
RUNS = ROOT / "runs/r2e_static_prep_20260924"
M3 = ROOT / "runs/env_overnight_20260916/M3/facts"
UPSTREAM = {  # 48 题镜像里 git remote 的原值（M3 git_remote.txt）
    "aiohttp": "https://github.com/aio-libs/aiohttp.git",
    "coveragepy": "https://github.com/nedbat/coveragepy.git",
    "datalad": "https://github.com/datalad/datalad.git",
    "numpy": "https://github.com/numpy/numpy.git",
    "orange3": "https://github.com/biolab/orange3.git",
    "pandas": "https://github.com/pandas-dev/pandas.git",
    "pillow": "https://github.com/python-pillow/Pillow.git",
    "scrapy": "https://github.com/scrapy/scrapy.git",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_new(path: Path, data: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as fh:
        fh.write(data.encode("utf-8") if isinstance(data, str) else data)


def write_json(path: Path, value: object) -> None:
    write_new(path, json.dumps(value, ensure_ascii=False, indent=1) + "\n")


def jsonl_rows(rel: str) -> dict[str, tuple[int, str, dict]]:
    out = {}
    for n, line in enumerate((ROOT / rel).read_text(encoding="utf-8").splitlines(), 1):
        row = json.loads(line)
        out[row["instance_id"]] = (n, line, row)
    return out


# --------------------------------------------------------------------------- 私有运行证据（run_refs）

# 账本组：(glob, 说明, 种类)。种类 run = 常规 noop/gold；diag = 设计的诊断对照（错误对照、资源、更完整修复候选等）
LEDGER_GROUPS = [
    ("runs/r2e_rf_20260923/remote/ledger_r2e_all_{noop,gold}.jsonl", "R-f 全池（09-23，来源版材料）", "run"),
    ("runs/r2e_rf_20260923/remote/ledger_r2e_reps_{noop,gold}.jsonl", "R-f 代表题重复", "run"),
    ("runs/r2e_rf_20260923/remote/ledger_r2e_requal_{noop,gold}.jsonl", "R-f 重新定性", "run"),
    ("runs/r2e_rf_20260923/remote/ledger_r2e_numpy_bigtmp_{noop,gold}.jsonl", "R-f numpy 资源配方（/tmp 6 GiB + 内存 12 GiB）", "recipe"),
    ("runs/r2e_rf_20260923/remote/ledger_r2e_contrast*.jsonl", "R-f 设计的错误对照（执行失败 / 未定 infra / 期限耗尽）", "diag"),
    ("runs/r2e_env_repair_20260924/_rerun2/ledger_{noop,gold}.jsonl", "环境轮中央复跑（09-24）", "run"),
    ("runs/r2e_env_repair_20260924/_rerun2/ledger_numpy_bigtmp_{noop,gold}.jsonl", "环境轮 numpy 资源配方复验", "recipe"),
    ("runs/r2e_env_repair_20260924/p3/ledger_gold_mem2g.jsonl", "环境轮 P3 内存 2 GiB 对照", "diag"),
    ("runs/r2e_env_repair_20260924/p4/ledger_overfix.jsonl", "环境轮 P4 更完整修复候选（真实评分）", "diag"),
    ("runs/r2e_t0_revisions_20260924/replay/ledger_t0_{noop,gold}.jsonl", "T0-1 / T0-2 修订后正式运行", "revision"),
    ("runs/r2e_t0_revisions_20260924/replay/ledger_env43_{noop,gold}.jsonl", "numpy 43e333e2 环境配方正式运行", "recipe"),
    ("runs/r2e_t0_batch2_20260924/replay_b2/ledger_watch1c1c_{noop,gold}.jsonl", "aiohttp 1c1c0ea3 时序敏感键加跑", "run"),
    ("runs/r2e_t0_batch2_20260924/replay_b3/ledger_b3_{noop,gold}.jsonl", "批次二修订后正式运行", "revision"),
    ("runs/r2e_t0_batch3_20260924/replay_b5/ledger_b5_{noop,gold}.jsonl", "批次三修订后正式运行", "revision"),
]
LOG_ROOTS = ["runs/r2e_rf_20260923", "runs/r2e_env_repair_20260924", "runs/r2e_t0_revisions_20260924", "runs/r2e_t0_batch2_20260924",
             "runs/r2e_t0_batch3_20260924"]
M3_REMOTE_PREFIX = "/work/envscreen/M3/"


def _expand(pattern: str) -> list[Path]:
    m = re.search(r"\{([^}]*)\}", pattern)
    pats = [pattern[:m.start()] + alt + pattern[m.end():] for alt in m.group(1).split(",")] if m else [pattern]
    out = []
    for pat in pats:
        out += sorted(ROOT.glob(pat))
    return [p for p in out if not p.name.endswith("_local.jsonl")]


def build_run_index() -> tuple[dict[str, list[dict]], dict[str, list[Path]]]:
    """→ ({instance_id: [账本行摘要]}, {日志文件名: [本机路径]})。只读账本与日志，不改任何东西。"""

    logs: dict[str, list[Path]] = {}
    for root in LOG_ROOTS:
        for fp in sorted((ROOT / root).rglob("*.eval.log")):
            logs.setdefault(fp.name, []).append(fp)
    rows: dict[str, list[dict]] = {}
    for pattern, label, kind in LEDGER_GROUPS:
        for ledger in _expand(pattern):
            for n, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
                r = json.loads(line)
                em = (r.get("verdict_diagnostics") or {}).get("expected_match") or {}
                log = r.get("log") or {}
                local = None
                for cand in logs.get(Path(log.get("path") or "x").name, []):
                    if log.get("sha256") and "sha256:" + sha256(cand.read_bytes()) == log["sha256"]:
                        local = str(cand.relative_to(ROOT))
                        break
                rows.setdefault(r["instance_id"], []).append({
                    "group": label, "group_kind": kind, "ledger": str(ledger.relative_to(ROOT)), "line": n,
                    "candidate": (r.get("candidate") or {}).get("kind"), "candidate_origin": (r.get("candidate") or {}).get("origin"),
                    "recipe_id": (r.get("overlay") or {}).get("recipe_id"), "reward": (r.get("report") or {}).get("reward"),
                    "outcome": (r.get("report") or {}).get("outcome"),
                    "match": f"{em['match_count']}/{em['expected_count']}" if "match_count" in em else None,
                    "mismatched": sorted(em.get("mismatched") or [])[:12], "missing": sorted(em.get("missing") or [])[:12],
                    "unexpected": sorted(em.get("unexpected") or [])[:12],
                    "log": local, "log_sha256": log.get("sha256"), "log_remote_path": log.get("path"),
                })
    return rows, logs


def m3_reference(iid: str, c12: str) -> list[dict]:
    """M3 独立 runner（来源镜像、来源版材料）的 gold 参考行。"""

    out = []
    ledger = M3.parent / "gold_ledger" / "r2e_gold_m3.jsonl"
    if not ledger.exists():
        return out
    for n, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
        r = json.loads(line)
        if r.get("commit_hash", "")[:12] != c12:
            continue
        rp = r.get("log_path") or ""
        local = ROOT / "runs/env_overnight_20260916/M3" / rp.removeprefix(M3_REMOTE_PREFIX) if rp.startswith(M3_REMOTE_PREFIX) else None
        ok = bool(local and local.exists() and "sha256:" + sha256(local.read_bytes()) == r.get("log_sha256"))
        out.append({"group": "M3 独立 runner 参考（来源镜像、来源版材料）", "ledger": str(ledger.relative_to(ROOT)), "line": n,
                    "gate": r.get("gate"), "attempt": r.get("attempt"), "reward": r.get("reward"), "result": r.get("result"),
                    "log": str(local.relative_to(ROOT)) if ok else None, "log_sha256": r.get("log_sha256")})
    return out


def classify_rows(iid: str, rows: list[dict], revised: bool) -> list[dict]:
    """标出每行是否对应本题当前生效的材料与环境。有修订的题：只有修订后运行组是当前；numpy 43e333e2 只有环境配方组是当前；
    numpy 2f4a9650 默认 profile 的行是已知资源假阴性；其余题的常规运行都是当前。诊断对照单独标。"""

    out = []
    for r in rows:
        r = dict(r)
        if r["group_kind"] == "diag":
            r["material"] = "diagnostic"
        elif revised:
            r["material"] = "current" if r["group_kind"] == "revision" else "superseded（修订前的来源版材料或来源环境）"
        elif iid.startswith("numpy__43e333e2"):
            r["material"] = "current" if r["group_kind"] == "recipe" else "superseded（来源环境，未固定 hypothesis）"
        elif iid.startswith("numpy__2f4a9650"):
            r["material"] = "current" if r["group_kind"] == "recipe" else "superseded（默认 profile，已知资源假阴性）"
        else:
            r["material"] = "current"
        out.append(r)
    return out


# --------------------------------------------------------------------------- fetch

def cmd_fetch(ns: argparse.Namespace) -> int:
    rows = jsonl_rows(f"{DOCS}/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl")
    for iid, (_, _, g) in sorted(rows.items()):
        repo = g["repo_key_lower"]
        gd = RUNS / "git" / f"{repo}.git"
        if not gd.exists():
            subprocess.run(["git", "init", "-q", "--bare", str(gd)], check=True)
            subprocess.run(["git", "--git-dir", str(gd), "remote", "add", "origin", UPSTREAM[repo]], check=True)
        have = subprocess.run(["git", "--git-dir", str(gd), "cat-file", "-e", g["base_commit"] + "^{commit}"],
                              capture_output=True, check=False).returncode == 0
        if not have:
            subprocess.run(["git", "--git-dir", str(gd), "fetch", "-q", "--depth", "1", "--no-tags", "origin", g["base_commit"]],
                           check=True, timeout=1800)
        print(f"{iid} {'have' if have else 'fetched'} {g['base_commit'][:12]}", flush=True)
    return 0


# --------------------------------------------------------------------------- image-hashes（远端，只用标准库）

IMAGE_PROBE = r'''
import hashlib, json, os, stat, subprocess, sys
os.chdir("/testbed")
ls = subprocess.run(["git", "-c", "safe.directory=*", "ls-files", "-z", "-c", "-o", "--exclude-standard"],
                    stdout=subprocess.PIPE, check=True).stdout
tracked = set(subprocess.run(["git", "-c", "safe.directory=*", "ls-files", "-z", "-c"], stdout=subprocess.PIPE,
                             check=True).stdout.split(b"\0"))
out = {}
for raw in ls.split(b"\0"):
    if not raw:
        continue
    p = raw.decode("utf-8", "surrogateescape")
    kind = "tracked" if raw in tracked else "untracked"
    if os.path.islink(p):
        out[p] = {"kind": kind, "symlink": os.readlink(p)}
    elif os.path.isfile(p):
        with open(p, "rb") as fh:
            out[p] = {"kind": kind, "sha256": hashlib.sha256(fh.read()).hexdigest(), "mode": oct(os.stat(p).st_mode & 0o777)}
    elif not os.path.lexists(p):
        out[p] = {"kind": kind, "deleted": True}
    else:
        out[p] = {"kind": kind, "other": True}
head = subprocess.run(["git", "-c", "safe.directory=*", "rev-parse", "HEAD"], stdout=subprocess.PIPE, check=True).stdout.decode().strip()
print(json.dumps({"head": head, "files": out}))
'''


def cmd_image_hashes(ns: argparse.Namespace) -> int:
    out = Path(ns.out)
    for spec in ns.image:
        iid, _, ref = spec.partition("=")
        base = ["docker", "run", "--rm", "--network", "none", "--entrypoint", "/testbed/.venv/bin/python", ref]
        proc = subprocess.run(base + ["-c", IMAGE_PROBE], capture_output=True, timeout=1800, check=False)
        if proc.returncode != 0:
            print(f"{iid}: probe rc={proc.returncode} {proc.stderr.decode()[-400:]}", file=sys.stderr)
            continue
        doc = json.loads(proc.stdout)
        img = json.loads(subprocess.run(["docker", "image", "inspect", ref], capture_output=True, check=True).stdout)[0]
        doc.update({"instance_id": iid, "image_ref": ref, "image_id": img["Id"], "repo_digests": img.get("RepoDigests")})
        (out / iid).mkdir(parents=True, exist_ok=True)
        for p, f in sorted(doc["files"].items()):
            if f["kind"] == "untracked" and "sha256" in f:
                data = subprocess.run(["docker", "run", "--rm", "--network", "none", "--entrypoint", "cat", ref, f"/testbed/{p}"],
                                      capture_output=True, check=True).stdout
                if sha256(data) != f["sha256"]:
                    raise RuntimeError(f"{iid}: 拷出的 {p} 摘要不符")
                dst = out / iid / "untracked" / p
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(data)
        (out / iid / "image_hashes.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{iid}: {len(doc['files'])} 项，HEAD {doc['head'][:12]}", flush=True)
    return 0


# --------------------------------------------------------------------------- prepare

def export_base(gitdir: Path, commit: str, dest: Path) -> dict:
    """直接读 blob（同 SWE-Gym prepare_materials.export_base）：保留原字节、可执行位与软链。"""

    def git(*args: str) -> bytes:
        return subprocess.check_output(["git", "--git-dir", str(gitdir), *args])

    tree = git("rev-parse", commit + "^{tree}").decode().strip()
    entries = git("ls-tree", "-rz", "--full-tree", commit).split(b"\0")
    dest.mkdir(parents=True)
    count, total, links, gitlinks = 0, 0, [], {}
    proc = subprocess.Popen(["git", "--git-dir", str(gitdir), "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        for entry in entries:
            if not entry:
                continue
            meta, raw_name = entry.split(b"\t", 1)
            mode, kind, oid = meta.split()
            name = raw_name.decode("utf-8")
            target = dest / name
            if not target.resolve().is_relative_to(dest.resolve()):
                raise ValueError(f"路径越出导出目录: {name}")
            if kind == b"commit" and mode == b"160000":
                # 子模块（gitlink）：只记提交号，导出为空目录——镜像是不递归克隆的，/testbed 里同样只有空目录（image-hashes 核对）
                target.mkdir(parents=True)
                gitlinks[name] = oid.decode()
                continue
            if kind != b"blob":
                raise ValueError(f"未支持的 git 对象: {name} {kind!r}")
            proc.stdin.write(oid + b"\n")
            proc.stdin.flush()
            header = proc.stdout.readline().split()
            data = proc.stdout.read(int(header[2]))
            if proc.stdout.read(1) != b"\n" or hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() != oid.decode():
                raise ValueError(f"blob 字节不符: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            if mode == b"120000":
                target.symlink_to(data.decode("utf-8"))
                links.append(name)
            elif mode in (b"100644", b"100755"):
                target.write_bytes(data)
                target.chmod(0o755 if mode == b"100755" else 0o644)
            else:
                raise ValueError(f"未支持的 git mode: {name} {mode!r}")
            count += 1
            total += len(data)
    finally:
        proc.stdin.close()
        proc.stdout.close()
        proc.wait()
    return {"base_tree": tree, "tracked_entries": count, "blob_bytes": total, "symlinks": links, "gitlinks": gitlinks,
            "blob_bytes_verified": True}


def apply_initial_diff(dest: Path, diff: Path) -> dict:
    data = diff.read_bytes()
    info = {"source": str(diff.relative_to(ROOT)), "bytes": len(data), "sha256": sha256(data), "files": {}}
    if not data:
        return info
    if b"Binary files " in data or b"GIT binary patch" in data:
        raise ValueError(f"{diff}: 含二进制差异，需单独处理")
    cur = None
    for line in data.decode("utf-8").splitlines():
        m = re.match(r"diff --git a/(\S+) b/(\S+)$", line)
        if m:
            cur = m.group(2)
            info["files"][cur] = "modified"
        elif cur and line.startswith("deleted file mode"):
            info["files"][cur] = "deleted"
        elif cur and line.startswith("new file mode"):
            info["files"][cur] = "added"
    # 导出目录在本仓库的 runs/ 下：挡住向上发现仓库，git apply 只当补丁工具用。GIT_CEILING_DIRECTORIES 只认绝对路径——
    # 给相对路径时 git 会找到项目仓库，把补丁当成仓库根下的路径全部 "Skipped patch" 却返回 0（09-25 用相对 --out 时实测）
    env = {**os.environ, "GIT_CEILING_DIRECTORIES": str(dest.parent.resolve())}
    for args in (["--check"], []):
        proc = subprocess.run(["git", "apply", "-v", *args, "--whitespace=nowarn", str(diff.resolve())], cwd=dest.resolve(), env=env,
                              capture_output=True, text=True, check=True)
        if "Skipped patch" in proc.stdout + proc.stderr:
            raise ValueError(f"{diff}: git apply 跳过了补丁（可能发现了外层仓库）：{(proc.stdout + proc.stderr)[-300:]}")
    for p, how in info["files"].items():
        if (how == "deleted") == (dest / p).exists():
            raise ValueError(f"{diff}: 应用后 {p} 的存在性与差异声明不符")
    return info


def m3_untracked(c12: str) -> list[str]:
    text = (M3 / c12 / "facts" / "untracked.txt").read_text(encoding="utf-8")
    body = text.split("\n", 1)[1].split("--count--")[0]
    return [ln for ln in body.splitlines() if ln.strip()]


def tree_files(dest: Path) -> dict[str, dict]:
    out = {}
    for dirpath, dirnames, filenames in os.walk(dest):
        dirnames.sort()
        for fn in sorted(filenames) + sorted(d for d in dirnames if os.path.islink(os.path.join(dirpath, d))):
            fp = Path(dirpath) / fn
            rel = fp.relative_to(dest).as_posix()
            if fp.is_symlink():
                out[rel] = {"symlink": os.readlink(fp)}
            else:
                out[rel] = {"sha256": sha256(fp.read_bytes()), "mode": oct(fp.stat().st_mode & 0o777)}
    return dict(sorted(out.items()))


def neutral_brief(repo: str, rec: dict, env_pins: list[dict]) -> str:
    sc = rec.get("solver_conditions") or {}
    ver = re.search(r"\b3\.\d+\.\d+\b", sc.get("interpreter", ""))
    pip = (sc.get("pip") or "").strip()
    lines = [
        "# 本题公开审查的环境说明（中性，R2E）", "",
        "这是静态材料，不是实际容器，也不是捕获的模型请求。`user_prompt.txt` 由当前 `render_user_prompt` 渲染；",
        "`public_bundle.json` 的 `public_hints` 是正式链写进容器的 R2E 提示（`.venv`、不联网、pip 可能没有、不要改仓库测试文件）；环境细节以本说明为准。",
        "`worktree/` 是解题者在 `/testbed` 看到的初始工作树：base 提交的跟踪文件，加上镜像初态相对 base 的改动与未跟踪的构建文件；",
        "不含 `.git`、被 `.gitignore` 忽略的构建产物（编译扩展、`.venv` 等）和隐藏测试。缺哪些文件见 `worktree_manifest.json`。", "",
        "## 解题环境（环境阶段实测，按本题填写）", "",
        f"- 工作目录 `/testbed`；`python` 经镜像环境变量指向 `/testbed/.venv/bin/python`（Python {ver.group(0) if ver else '未记录'}）。",
        f"- pip：{'有' if pip.startswith('present') else '没有（pip / pip3 / uv 命令都不在 PATH）' if pip.startswith('absent') else '未记录'}；无出网，装不了新包。",
        "- 解题身份是 agent（uid 54321），可写 `/testbed` 与 home；资源默认 2 CPU / 4 GiB，`/tmp` 1 GiB。",
    ]
    cwd = sc.get("cwd_required", "")
    if "sys.path" in cwd or "python -m pytest" in cwd:
        lines.append("- 包没有装进 venv：`/testbed` 必须在 `sys.path` 上才能导入（在 `/testbed` 下用 `python -c`，或设 `PYTHONPATH=/testbed`）；"
                     "跑测试用 `python -m pytest`，裸 `pytest` 收集会失败。")
    if (sc.get("xvfb") or "").startswith("需要"):
        lines.append("- 涉及 Qt 的 widget 测试要带前缀 `QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum`（`xvfb-run` 在 `/usr/bin`）；纯库调用不需要。")
    if repo == "datalad":
        lines.append("- agent 的 HOME 里没有 git 身份（user.name / user.email）；需要提交时在命令里临时指定。")
    for pin in env_pins:
        lines.append(f"- 本题镜像按环境配方把 `{pin['dist']}` 固定为 {pin['version']}（与来源镜像装的版本不同）。")
    lines += ["", "请只据公开材料列出必要的开发条件与最小验证命令；不要把缺证据当作题目不可解。不要读其它题或本目录之外的调查材料。", ""]
    return "\n".join(lines)


def cmd_prepare(ns: argparse.Namespace) -> int:
    sys.path.insert(0, str(ROOT / "rh2/src"))
    from repoharness2.envpack.bundles import PublicTaskBundle, render_user_prompt
    from repoharness2.envpack.ingest_r2e_subset import (
        REVISION_KIND_HIDDEN_ADD,
        REVISION_KIND_HIDDEN_TEST,
        load_trusted_r2e_ingest_outputs,
    )

    out = Path(ns.out).resolve()
    if out.exists():
        print(f"输出目录已存在，不覆盖: {out}", file=sys.stderr)
        return 2
    trusted = load_trusted_r2e_ingest_outputs(ROOT)
    publics = jsonl_rows(f"{DOCS}/s2_r2e/ingest/public_bundles_v0.jsonl")
    gradings = jsonl_rows(f"{DOCS}/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl")
    validations = jsonl_rows(f"{DOCS}/s2_r2e/ingest/validation_bundles_v0.jsonl")
    trusted_ids = {g.instance_id for g in trusted.result.grading_bundles}
    assert trusted_ids == set(gradings) == set(publics) == set(validations) and len(trusted_ids) == 48
    raw = {}
    for line in (ROOT / f"{DOCS}/s2_r2e/raw/r2e_gym_subset_48_e8b9fcbc.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        raw[f"{r['repo_name']}__{r['commit_hash']}"] = r
    rev_doc = json.loads((ROOT / f"{DOCS}/s2_r2e/revisions/material_revisions_v3.json").read_text(encoding="utf-8"))
    image_files = Path(ns.image_files) if ns.image_files else None
    env_pins = json.loads((ROOT / RND / "recipes/env_pins_v2.json").read_text(encoding="utf-8"))["tasks"]
    known_issue_families = json.loads((ROOT / RND / "known_issues.json").read_text(encoding="utf-8"))["families"]
    run_rows, _ = build_run_index()
    check = {"schema_id": "rh2.r2e_static_materials_check.v1", "output": str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out),
             "code_sha256": sha256(Path(__file__).read_bytes()),
             "inputs": {"ingest_manifest_sha256": sha256((ROOT / f"{DOCS}/s2_r2e/ingest/ingest_manifest_v0.json").read_bytes()),
                        "material_revisions_v3_sha256": sha256((ROOT / f"{DOCS}/s2_r2e/revisions/material_revisions_v3.json").read_bytes())},
             "tasks": {}}
    for iid in sorted(trusted_ids):
        _, pline, prow = publics[iid]
        gn, gline, grow = gradings[iid]
        vn, vline, vrow = validations[iid]
        repo, base, c12 = grow["repo_key_lower"], grow["base_commit"], grow["source_commit_hash"][:12]
        rec = json.loads((ROOT / RND / "tasks" / iid / "screening_record.json").read_text(encoding="utf-8"))
        pub = out / "public" / iid
        # ---- public：冻结行、提示、中性说明
        write_json(pub / "public_bundle.json", {"source": f"{DOCS}/s2_r2e/ingest/public_bundles_v0.jsonl", "line_sha256": sha256(pline.encode()),
                                                "row": prow})
        write_new(pub / "user_prompt.txt", render_user_prompt(PublicTaskBundle.model_validate(prow)))
        write_new(pub / "environment_brief.md", neutral_brief(repo, rec, env_pins.get(iid, {}).get("pins", [])))
        # ---- public：实际解题工作树
        wt = pub / "worktree"
        exp = export_base(RUNS / "git" / f"{repo}.git", base, wt)
        diff = apply_initial_diff(wt, M3 / c12 / "facts" / "initial.diff")
        expected_untracked = m3_untracked(c12)
        included, missing = {}, []
        for name in expected_untracked:
            dst = wt / name
            if name == "run_tests.sh":
                data = grow["run_tests_sh"].encode("utf-8")
                assert "sha256:" + sha256(data) == grow["run_tests_sh_sha256"]
                write_new(dst, data)
                included[name] = {"origin": "grading_bundle.run_tests_sh（评分面原文，与镜像事实核过摘要）", "sha256": sha256(data)}
                continue
            src = image_files / iid / "untracked" / name if image_files else None
            ih = image_files / iid / "image_hashes.json" if image_files else None
            link = (json.loads(ih.read_text(encoding="utf-8"))["files"].get(name) or {}).get("symlink") if ih and ih.exists() else None
            if link is not None:   # 未跟踪的软链（orange3 的 datasets → Orange/tests/datasets/，install.sh 建的）：按镜像记录重建
                dst.symlink_to(link)
                included[name] = {"origin": f"image_hashes:{iid}（镜像里的软链，按记录的目标重建）", "symlink": link}
            elif src is not None and src.exists():
                write_new(dst, src.read_bytes())
                included[name] = {"origin": f"image_hashes:{iid}（从镜像拷出）", "sha256": sha256(src.read_bytes())}
            else:
                missing.append(name)
        files = tree_files(wt)
        write_json(pub / "worktree_manifest.json", {
            "instance_id": iid, "repo": repo, "upstream": UPSTREAM[repo], "base_commit": base, "export": exp, "initial_diff": diff,
            "untracked_in_image": expected_untracked, "untracked_included": included, "untracked_missing": missing,
            "not_included": "被 .gitignore 忽略的文件（.venv、编译产物等）、.git、隐藏测试",
            "files": files})
        # ---- private：当前生效的评分材料
        prv = out / "private" / iid
        write_json(prv / "grading_bundle.json", {"source": f"{DOCS}/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl", "line": gn,
                                                 "line_sha256": sha256(gline.encode()), "row": grow})
        write_json(prv / "validation_bundle.json", {"source": f"{DOCS}/s2_r2e/ingest/validation_bundles_v0.jsonl", "line": vn,
                                                    "line_sha256": sha256(vline.encode()), "row": vrow})
        write_new(prv / "expected_output.json", grow["expected_output_json"])
        write_new(prv / "gold.patch", vrow["golden_patch"])
        write_new(prv / "run_tests.sh", grow["run_tests_sh"])
        doc = json.loads(raw[iid]["execution_result_content"])
        codes = dict(zip(doc["test_file_names"], doc["test_file_codes"]))
        revs = [r for r in rev_doc["revisions"] if r["instance_id"] == iid]
        hidden = {}
        for f in grow["hidden_test_files"]:
            path, want = f["path"], f["sha256"]
            rev = next((r for r in revs if r["kind"] in (REVISION_KIND_HIDDEN_ADD, REVISION_KIND_HIDDEN_TEST) and r["target"] == path), None)
            if rev is not None:
                data, origin = (ROOT / rev["revised_file"]).read_bytes(), f"revision:{rev['revision_id']}"
            elif path in codes:
                data, origin = codes[path].encode("utf-8"), "raw_row.execution_result_content"
            else:
                data, origin = (M3 / c12 / "r2e_tests" / path).read_bytes(), f"M3 镜像副本 facts/{c12}/r2e_tests"
            if "sha256:" + sha256(data) != want:
                raise ValueError(f"{iid}/{path}: 隐藏测试内容与评分面摘要不符（{origin}）")
            write_new(prv / "hidden_tests" / path, data)
            hidden[path] = {"sha256": want, "origin": origin}
        write_json(prv / "revisions.json", revs)
        classified = classify_rows(iid, run_rows.get(iid, []), revised=bool(grow["material_revisions"]))
        env_step = env_pins.get(iid, {}).get("env_step") if iid in env_pins else None
        write_json(prv / "run_refs.json", {
            "note": ("只列原始运行证据（账本行、日志与摘要）；material=current 的行对应本题当前生效的材料与环境，superseded 的行是修订前"
                     "或来源环境下的结果，只能作对照。历史结论（逐题记录、findings、提案）不在这里，封存初判后由协调者开放 history 包。"),
            "current_material": {"material_revisions": grow["material_revisions"], "expected_sha256": grow["expected_output_json_sha256"],
                                 "hidden_tests_tree_sha256": grow["hidden_tests_tree_sha256"],
                                 "env_recipe": ({"env_pins": "env_pins_v2", "env_step": env_step or "env_v1.sh",
                                                 "pins": [f"{x['dist']}=={x['version']}" for x in env_pins[iid]['pins']]} if iid in env_pins else None),
                                 "resource_recipe": "task_resources_v1（grader：/tmp 6 GiB + 内存 12 GiB）" if iid.startswith("numpy__2f4a9650") else None},
            "rh2_runs": classified,
            "independent_reference": m3_reference(iid, c12),
            "runs_without_local_log": [f"{r['ledger']}:{r['line']}" for r in classified if not r["log"]],
        })
        # ---- history：环境阶段的记录与结论，只给路径（封存初判后开放）
        hist = {"screening_record": f"{RND}/tasks/{iid}/screening_record.json", "findings": f"{RND}/tasks/{iid}/findings.md",
                "facts": f"{RND}/tasks/{iid}/facts.json", "known_issues": f"{RND}/known_issues.json", "decisions": f"{RND}/decisions.md",
                "results": f"{RND}/results_20260924.md"}
        for key, rel in (("proposal", f"material_revisions/{iid}.md"), ("repro_script", f"repros/{iid}.py")):
            if (ROOT / RND / rel).exists():
                hist[key] = f"{RND}/{rel}"
        pkg = [str(q.relative_to(ROOT)) for q in sorted((ROOT / RND / "packages").glob("p*/README.md"))
               if iid in q.read_text(encoding="utf-8") or iid.split("__")[1][:8] in q.read_text(encoding="utf-8")]
        if pkg:
            hist["package_readmes"] = pkg
        hist["known_issue_families"] = [f["family"] for f in known_issue_families if iid in json.dumps(f, ensure_ascii=False)]
        write_json(out / "history" / iid / "refs.json", hist)
        check["tasks"][iid] = {
            "repo": repo, "base_commit": base, "base_tree": exp["base_tree"], "tracked_entries": exp["tracked_entries"],
            "blob_bytes_verified": exp["blob_bytes_verified"], "initial_diff_files": diff["files"],
            "untracked_included": sorted(included), "untracked_missing": missing, "worktree_files": len(files),
            "worktree_digest": sha256(json.dumps(files, sort_keys=True).encode()),
            "hidden_tests_verified": len(hidden), "expected_sha256": grow["expected_output_json_sha256"],
            "gold_sha256": vrow["golden_patch_sha256"], "revisions": [r["revision_id"] for r in revs],
            "run_refs": {"current": sum(r["material"] == "current" for r in classified),
                         "superseded": sum(r["material"].startswith("superseded") for r in classified),
                         "diagnostic": sum(r["material"] == "diagnostic" for r in classified),
                         "without_local_log": sum(not r["log"] for r in classified)},
        }
        print(f"{iid}: 跟踪 {exp['tracked_entries']}，初始差异 {len(diff['files'])} 个文件，未跟踪 {sorted(included)} 缺 {missing}，"
              f"隐藏测试 {len(hidden)}", flush=True)
    write_json(out / "material_check.json", check)
    return 0


# --------------------------------------------------------------------------- verify

def cmd_verify(ns: argparse.Namespace) -> int:
    """① 每题交付工作树的实际文件（重算字节、权限、软链）与 worktree_manifest 逐项相同；② 有镜像记录的题，实际文件与镜像
    逐文件比对。只比清单不读实际文件的旧做法（Codex 批次三复核 F2）已去掉；没有任何题可核即判失败。"""

    out = Path(ns.out)
    check_path = out / "material_check.json"
    if not check_path.exists():
        print(f"未验证：{check_path} 不存在（先运行 prepare）", file=sys.stderr)
        return 2
    check = json.loads(check_path.read_text(encoding="utf-8"))
    tasks = sorted(check.get("tasks") or {})
    if not tasks:
        print("未验证：material_check.json 里没有题目", file=sys.stderr)
        return 2
    manifest_results, image_results, actual_files = {}, {}, {}
    for iid in tasks:
        man_path = out / "public" / iid / "worktree_manifest.json"
        wt = out / "public" / iid / "worktree"
        if not man_path.exists() or not wt.is_dir():
            manifest_results[iid] = {"ok": False, "error": "缺 worktree 或 worktree_manifest.json"}
            continue
        man = json.loads(man_path.read_text(encoding="utf-8"))
        actual = tree_files(wt)
        gitlinks = man["export"].get("gitlinks") or {}
        for g in gitlinks:   # 子模块导出为空目录，os.walk 不列空目录
            if not (wt / g).is_dir():
                actual[g] = {"missing_gitlink_dir": True}
        actual_files[iid] = actual
        listed = man["files"]
        content = sorted(p for p in set(actual) & set(listed) if actual[p] != listed[p])
        extra = sorted(set(actual) - set(listed) - set(gitlinks))
        missing = sorted(set(listed) - set(actual))
        ok = not (content or extra or missing)
        manifest_results[iid] = {"ok": ok, "files": len(actual), "differs_from_manifest": content[:20],
                                 "not_in_manifest": extra[:20], "missing_on_disk": missing[:20]}
        if not ok:
            print(f"{iid}: 实际文件与清单不符：内容/权限/软链 {len(content)}，多出 {len(extra)}，缺失 {len(missing)}", flush=True)
    image_dir = Path(ns.image_files)
    for hp in sorted(image_dir.glob("*/image_hashes.json")):
        img = json.loads(hp.read_text(encoding="utf-8"))
        iid = img["instance_id"]
        if iid not in actual_files:
            image_results[iid] = {"ok": False, "error": "镜像记录对应的题没有可核对的交付工作树"}
            continue
        man = json.loads((out / "public" / iid / "worktree_manifest.json").read_text(encoding="utf-8"))
        exp_files = actual_files[iid]
        same, diff_content, diff_mode, only_image, deleted_ok, deleted_bad = 0, [], [], [], 0, []
        gitlinks = man["export"].get("gitlinks") or {}
        gitlink_dirs = []
        for p, f in img["files"].items():
            e = exp_files.get(p)
            if p in gitlinks:
                (gitlink_dirs if f.get("other") and (out / "public" / iid / "worktree" / p).is_dir() else diff_content).append(p)
                continue
            if f.get("deleted"):
                if e is not None:
                    deleted_bad.append(p)
                else:
                    deleted_ok += 1
                continue
            if e is None:
                only_image.append(p)
            elif ("symlink" in f) != ("symlink" in e) or f.get("symlink") != e.get("symlink") or f.get("sha256") != e.get("sha256"):
                diff_content.append(p)
            else:
                same += 1
                if f.get("mode") != e.get("mode"):
                    diff_mode.append(p)
        only_export = sorted(set(exp_files) - set(img["files"]) - set(gitlinks))
        ok = not (diff_content or only_image or only_export or deleted_bad) and img["head"] == man["base_commit"]
        image_results[iid] = {"image_ref": img["image_ref"], "image_id": img["image_id"], "head_is_base": img["head"] == man["base_commit"],
                              "files_compared": len(img["files"]), "identical": same, "deleted_as_expected": deleted_ok,
                              "gitlink_dirs": gitlink_dirs, "content_mismatch": diff_content[:20], "only_in_image": only_image[:20],
                              "only_in_export": only_export[:20], "deleted_but_exported": deleted_bad,
                              "mode_mismatch_count": len(diff_mode), "mode_mismatch_sample": diff_mode[:10], "ok": ok}
        print(f"{iid}: {'OK' if ok else 'MISMATCH'} 镜像比对 {len(img['files'])}，相同 {same}，删除 {deleted_ok}，内容不符 {len(diff_content)}，"
              f"只在镜像 {len(only_image)}，只在导出 {len(only_export)}，权限不同 {len(diff_mode)}", flush=True)
    check["worktree_verification"] = {"method": "重算实际文件（字节、权限、软链）后与 worktree_manifest 逐项比对", "tasks": manifest_results}
    check["image_verification"] = image_results
    check_path.write_text(json.dumps(check, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    bad_manifest = [i for i, r in manifest_results.items() if not r["ok"]]
    bad_image = [i for i, r in image_results.items() if not r["ok"]]
    print(f"工作树对清单：{len(manifest_results) - len(bad_manifest)}/{len(manifest_results)} 一致；"
          f"镜像比对：{len(image_results) - len(bad_image)}/{len(image_results)} 一致", flush=True)
    if not image_results:
        print("注意：没有镜像记录，镜像比对未验证", file=sys.stderr)
    return 0 if manifest_results and image_results and not bad_manifest and not bad_image else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch")
    ih = sub.add_parser("image-hashes")
    ih.add_argument("--image", action="append", required=True, help="<instance_id>=<镜像引用>")
    ih.add_argument("--out", required=True)
    pr = sub.add_parser("prepare")
    pr.add_argument("--out", default=str(RUNS / "v1"))
    pr.add_argument("--image-files", default=str(RUNS / "image_files"))
    ve = sub.add_parser("verify")
    ve.add_argument("--out", default=str(RUNS / "v1"))
    ve.add_argument("--image-files", default=str(RUNS / "image_files"))
    ns = ap.parse_args(argv)
    return {"fetch": cmd_fetch, "image-hashes": cmd_image_hashes, "prepare": cmd_prepare, "verify": cmd_verify}[ns.cmd](ns)


if __name__ == "__main__":
    sys.exit(main())
