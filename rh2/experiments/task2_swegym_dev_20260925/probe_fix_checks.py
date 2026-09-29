"""Codex 任务二完成复核 F1–F4 的窄对照（本机即可跑；不起容器、不评分）。
F1 run_matrix.grade：导出失败 / 记录缺失 → 不评分；导出成功且为空 → noop；导出成功非空 → patch-dir。
F2 run_matrix.one：恢复一个 cleanup_ok=False 的尝试 → 写 STOP、不评分；cleanup_ok=True → 进入评分。
F3 model_gateway._sse_has_message_stop：真实终局事件 / 正文含同名词但无终局 / 无终局。
F4 git：镜像初态 dirty 文件再被编辑时，相对 HEAD 导出的补丁在初态上 apply 失败，相对 stash-create 基线导出的补丁 apply 成功。
"""
import asyncio, json, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "base_probe_20260922"))
import model_gateway  # noqa: E402
import run_matrix  # noqa: E402

res = {}

# ---------- F1 / F2
calls = []
async def fake_run_proc(cmd, env=None, log=None, timeout=None):
    calls.append(cmd)
    return 0
run_matrix.run_proc = fake_run_proc

def make_matrix(out):
    m = object.__new__(run_matrix.Matrix) if hasattr(run_matrix, "Matrix") else None
    return m

async def f1():
    out = Path(tempfile.mkdtemp())
    M = run_matrix.Matrix.__new__(run_matrix.Matrix)
    M.ns = type("NS", (), {"prepared_summary": "x", "grade_seconds": 10})()
    r = {}
    for name, cand in [("export_failed", {"export_ok": False, "bytes": 0, "empty": False}),
                       ("record_missing", {}),
                       ("empty_ok", {"export_ok": True, "bytes": 0, "empty": True}),
                       ("nonempty_ok", {"export_ok": True, "bytes": 10, "empty": False})]:
        calls.clear()
        adir = out / name; adir.mkdir()
        g = await M.grade("t", {}, adir, "aid", {"candidate": cand})
        cand_arg = None
        if calls:
            c = calls[0]; cand_arg = c[c.index("--candidate") + 1]
        r[name] = {"returned": g, "candidate_passed_to_grader": cand_arg}
    return r
res["F1"] = asyncio.run(f1())

async def f2():
    r = {}
    for name, cleanup in [("cleanup_failed", {"cleanup_ok": False, "labeled_containers_left": ["x"]}),
                          ("cleanup_ok", {"cleanup_ok": True, "labeled_containers_left": [], "labeled_networks_left": []})]:
        out = Path(tempfile.mkdtemp())
        M = run_matrix.Matrix.__new__(run_matrix.Matrix)
        M.ns = type("NS", (), {"no_grade": False})()
        M.out = out; M.tasks = {"t": {}}; M.solvers = {"s": {}}; M.sem = asyncio.Semaphore(1); M.solver_sems = {"s": asyncio.Semaphore(1)}
        M.stopped_solvers = {}; M.infra_streak = {}; M.lock = asyncio.Lock(); M.slot = 0
        led = []
        M.ledger = lambda row: led.append(row)
        graded = []
        async def fake_grade(*a, **k):
            graded.append(1); return {"reward": 0}
        M.grade = fake_grade
        adir = out / "attempts" / "t" / "s" / "a1"; adir.mkdir(parents=True)
        (adir / "attempt.json").write_text(json.dumps({"result": "ran", "finished_at": "now", "cleanup": cleanup}))
        await M.one("t", "s", 1)
        r[name] = {"stop_file": (out / "STOP").exists(), "graded": bool(graded), "ledger_stopped": [x.get("stopped") for x in led]}
    return r
res["F2"] = asyncio.run(f2())

# ---------- F3
def sse(evs):
    return b"".join(f"event: {n}\ndata: {json.dumps(d)}\n\n".encode() for n, d in evs)
start = ("message_start", {"type": "message_start", "message": {"id": "m"}})
delta_word = ("content_block_delta", {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "the message_stop event"}})
stop = ("message_stop", {"type": "message_stop"})
res["F3"] = {"real_terminal": model_gateway._sse_has_message_stop(sse([start, delta_word, stop])),
             "word_in_body_no_terminal": model_gateway._sse_has_message_stop(sse([start, delta_word])),
             "no_terminal": model_gateway._sse_has_message_stop(sse([start]))}

# ---------- F4
def sh(cmd, cwd):
    return subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
root = Path(tempfile.mkdtemp())
up = root / "repo"; up.mkdir()
sh("git init -q && git config user.email a@b && git config user.name a && printf 'a\\nb\\nc\\n' > f.txt && printf 'x\\n' > g.txt && git add -A && git commit -qm base", up)
sh("printf 'a\\nB-image\\nc\\n' > f.txt", up)                      # 镜像初态自带的已跟踪改动
head = sh("git rev-parse HEAD", up).stdout.strip()
base = sh("git -c user.name=rh2 -c user.email=rh2@local stash create x", up).stdout.strip()
porcelain_after_stash = sh("git status --porcelain", up).stdout
f4 = {"stash_create_left_worktree_dirty": porcelain_after_stash.strip() == "M f.txt"}
for case, edits in [("dirty_untouched_src_edit", "printf 'y\\n' > g.txt"), ("dirty_file_edited", "printf 'a\\nB-image\\nc\\nagent\\n' > f.txt")]:
    w = root / case; sh(f"cp -a {up} {w}", root); sh(edits, w)
    for ref_name, ref in [("vs_head", head), ("vs_baseline", base)]:
        patch = sh(f"git diff --binary {ref}", w).stdout
        # grader 侧：同一镜像初态（带 dirty 改动）上 apply
        init = root / f"init_{case}_{ref_name}"; sh(f"cp -a {up} {init}", root)
        (init / "c.patch").write_text(patch)
        chk = sh("git apply --check c.patch", init)
        f4[f"{case}:{ref_name}"] = "apply_ok" if chk.returncode == 0 else f"apply_failed: {chk.stderr.strip()[:80]}"
res["F4"] = f4
print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
out = HERE / "probe_fix_checks.result.json"
