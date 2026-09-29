"""Behavior probes for iterative__dvc-9395 (reviewer's own, private).

Runs inside a throwaway container after a candidate patch is applied to /testbed.
Every scenario uses its own temp git+dvc repo and a local directory remote.
Output: JSON lines to stdout, one per scenario.
"""
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time

PY = "/opt/miniconda3/envs/testbed/bin/python"
DVC = [PY, "-m", "dvc"]
HOME = tempfile.mkdtemp(prefix="home_")
ENV = dict(os.environ, HOME=HOME, DVC_NO_ANALYTICS="true", GIT_AUTHOR_NAME="r",
           GIT_AUTHOR_EMAIL="r@x", GIT_COMMITTER_NAME="r", GIT_COMMITTER_EMAIL="r@x")
ONLY = set(sys.argv[1:])


def run(cmd, cwd, stdin=None):
    p = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True,
                       text=True, env=ENV, input=stdin, timeout=120)
    return p.returncode, (p.stdout + p.stderr)


def dvc(args, cwd):
    return run(DVC + args, cwd)


def md5(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()[:8]


def snap(root):
    """Workspace files (except .git, .dvc/tmp, .dvc/config*) and cache files."""
    ws, cache = {}, {}
    for base, dirs, files in os.walk(root):
        rel = os.path.relpath(base, root)
        if rel == ".":
            dirs[:] = [d for d in dirs if d != ".git"]
        if rel.startswith(os.path.join(".dvc", "tmp")):
            continue
        for fn in files:
            p = os.path.join(base, fn)
            r = os.path.relpath(p, root)
            if r.startswith(os.path.join(".dvc", "cache")):
                cache[r] = md5(p)
            elif r.startswith(".dvc" + os.sep):
                continue
            else:
                ws[r] = md5(p)
    return ws, cache


def diff(a, b):
    added = sorted(k for k in b if k not in a)
    removed = sorted(k for k in a if k not in b)
    changed = sorted(k for k in a if k in b and a[k] != b[k])
    return {"added": added, "removed": removed, "changed": changed}


def tail(out, n=int(os.environ.get("TAILN", "4"))):
    lines = [l for l in out.splitlines() if l.strip() and "hardlink_lock" not in l]
    return lines[-n:]


def new_repo(remote=True):
    root = tempfile.mkdtemp(prefix="repo_")
    rem = tempfile.mkdtemp(prefix="remote_")
    run("git init -q", root)
    rc, out = dvc(["init", "-q"], root)
    assert rc == 0, out
    if remote:
        rc, out = dvc(["remote", "add", "-d", "local", rem], root)
        assert rc == 0, out
    return root, rem


def base_pipeline(root):
    with open(os.path.join(root, "foo"), "w") as f:
        f.write("foo\n")
    rc, out = dvc(["add", "-q", "foo"], root)
    assert rc == 0, out
    rc, out = dvc(["stage", "add", "-q", "-n", "copy-foo", "-d", "foo", "-o", "bar",
                   "sed s/foo/BAR/ foo > bar"], root)
    assert rc == 0, out
    rc, out = dvc(["repro", "-q"], root)
    assert rc == 0, out
    run("git add -A && git commit -qm init", root)


def rd(root, name):
    p = os.path.join(root, name)
    return open(p).read() if os.path.exists(p) else None


RESULTS = []


def scenario(fn):
    if ONLY and fn.__name__ not in ONLY:
        return fn
    try:
        res = fn()
    except Exception as exc:  # noqa: BLE001
        res = {"harness_error": repr(exc)}
    res = {"scenario": fn.__name__, **res}
    print(json.dumps(res), flush=True)
    return fn


@scenario
def B1_dry_missing_source():
    """`repro --pull --dry` with missing data source, missing bar and empty local cache."""
    root, rem = new_repo()
    base_pipeline(root)
    rc, out = dvc(["push", "-q", "--run-cache"], root)
    assert rc == 0, out
    os.remove(os.path.join(root, "foo"))
    os.remove(os.path.join(root, "bar"))
    shutil.rmtree(os.path.join(root, ".dvc", "cache"))
    before = snap(root)
    rc, out = dvc(["repro", "--pull", "--dry"], root)
    after = snap(root)
    return {"rc": rc, "workspace": diff(before[0], after[0]),
            "cache_added_n": len(diff(before[1], after[1])["added"]),
            "runs_added": [k for k in diff(before[1], after[1])["added"] if "runs" in k],
            "tail": tail(out)}


@scenario
def B2_no_remote_up_to_date():
    """No remote configured, pipeline up to date: `repro --pull`."""
    root, _ = new_repo(remote=False)
    base_pipeline(root)
    rc, out = dvc(["repro", "--pull"], root)
    return {"rc": rc, "tail": tail(out)}


@scenario
def B2b_no_remote_dep_changed():
    """No remote configured, data source modified: `repro --pull`."""
    root, _ = new_repo(remote=False)
    base_pipeline(root)
    with open(os.path.join(root, "foo"), "w") as f:
        f.write("new\n")
    rc, out = dvc(["repro", "--pull"], root)
    return {"rc": rc, "foo": rd(root, "foo"), "bar": rd(root, "bar"), "tail": tail(out)}


@scenario
def B3_modified_source_with_remote():
    """Remote configured and pushed; user edits data source foo; `repro --pull` (non-TTY)."""
    root, _ = new_repo()
    base_pipeline(root)
    rc, out = dvc(["push", "-q"], root)
    assert rc == 0, out
    with open(os.path.join(root, "foo"), "w") as f:
        f.write("new\n")
    rc, out = dvc(["repro", "--pull"], root)
    foo_dvc = open(os.path.join(root, "foo.dvc")).read()
    return {"rc": rc, "foo": rd(root, "foo"), "bar": rd(root, "bar"),
            "foo_dvc_md5_is_new": hashlib.md5(b"new\n").hexdigest() in foo_dvc,
            "tail": tail(out)}


@scenario
def B3_ctrl_modified_source_no_pull():
    """Control: same as B3 but plain `repro` (no --pull)."""
    root, _ = new_repo()
    base_pipeline(root)
    with open(os.path.join(root, "foo"), "w") as f:
        f.write("new\n")
    rc, out = dvc(["repro"], root)
    return {"rc": rc, "foo": rd(root, "foo"), "bar": rd(root, "bar"), "tail": tail(out)}


@scenario
def B3t_modified_source_tty_yes():
    """Same as B3 but with a pseudo-TTY answering 'y' to any prompt."""
    root, _ = new_repo()
    base_pipeline(root)
    rc, out = dvc(["push", "-q"], root)
    assert rc == 0, out
    with open(os.path.join(root, "foo"), "w") as f:
        f.write("new\n")
    cmd = "script -qec '" + " ".join(DVC) + " repro --pull' /dev/null"
    rc, out = run(cmd, root, stdin="y\ny\ny\n")
    return {"rc": rc, "foo": rd(root, "foo"), "bar": rd(root, "bar"),
            "prompted": "Are you sure" in out, "tail": tail(out)}


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _http_remote(root, rem):
    port = _free_port()
    srv = subprocess.Popen([PY, "-m", "http.server", str(port), "--bind", "127.0.0.1",
                            "--directory", rem], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    rc, out = dvc(["remote", "add", "-d", "web", f"http://127.0.0.1:{port}"], root)
    assert rc == 0, out
    return srv


@scenario
def B4_http_missing_source():
    """Default remote is HTTP (read-only mirror of the pushed local remote): missing data source."""
    root, rem = new_repo()
    base_pipeline(root)
    rc, out = dvc(["push", "-q", "--run-cache"], root)
    assert rc == 0, out
    srv = _http_remote(root, rem)
    try:
        os.remove(os.path.join(root, "foo"))
        shutil.rmtree(os.path.join(root, ".dvc", "cache"))
        rc, out = dvc(["repro", "--pull"], root)
        return {"rc": rc, "foo": rd(root, "foo"), "bar": rd(root, "bar"), "tail": tail(out)}
    finally:
        srv.kill()


@scenario
def B4b_http_runcache_restore():
    """HTTP default remote: bar + lock + bar cache removed, local run-cache kept (base feature)."""
    root, rem = new_repo()
    base_pipeline(root)
    rc, out = dvc(["push", "-q", "--run-cache"], root)
    assert rc == 0, out
    srv = _http_remote(root, rem)
    try:
        bar_md5 = hashlib.md5(b"BAR\n").hexdigest()
        os.remove(os.path.join(root, "bar"))
        os.remove(os.path.join(root, "dvc.lock"))
        cache_bar = os.path.join(root, ".dvc", "cache", bar_md5[:2], bar_md5[2:])
        os.chmod(cache_bar, 0o644)
        os.remove(cache_bar)
        rc, out = dvc(["repro", "--pull"], root)
        return {"rc": rc, "bar": rd(root, "bar"),
                "restored_from_run_cache": "is cached - skipping run" in out,
                "tail": tail(out)}
    finally:
        srv.kill()


@scenario
def B5_existing_output_without_hash():
    """New stage whose output already exists in the workspace (content not in cache)."""
    root, _ = new_repo()
    base_pipeline(root)
    rc, out = dvc(["push", "-q"], root)
    assert rc == 0, out
    with open(os.path.join(root, "baz"), "w") as f:
        f.write("manual\n")
    rc, out = dvc(["stage", "add", "-q", "-n", "make-baz", "-d", "foo", "-o", "baz",
                   "cp foo baz"], root)
    assert rc == 0, out
    rc, out = dvc(["repro", "--pull"], root)
    return {"rc": rc, "baz": rd(root, "baz"), "tail": tail(out)}


@scenario
def B5_ctrl_existing_output_no_pull():
    root, _ = new_repo()
    base_pipeline(root)
    with open(os.path.join(root, "baz"), "w") as f:
        f.write("manual\n")
    rc, out = dvc(["stage", "add", "-q", "-n", "make-baz", "-d", "foo", "-o", "baz",
                   "cp foo baz"], root)
    assert rc == 0, out
    rc, out = dvc(["repro"], root)
    return {"rc": rc, "baz": rd(root, "baz"), "tail": tail(out)}


@scenario
def B6_no_run_cache_flag():
    """`repro --pull --no-run-cache` with nothing missing: are remote runs downloaded?"""
    root, _ = new_repo()
    base_pipeline(root)
    rc, out = dvc(["push", "-q", "--run-cache"], root)
    assert rc == 0, out
    shutil.rmtree(os.path.join(root, ".dvc", "cache", "runs"))
    rc, out = dvc(["repro", "--pull", "--no-run-cache"], root)
    return {"rc": rc, "runs_dir_exists": os.path.isdir(os.path.join(root, ".dvc", "cache", "runs")),
            "tail": tail(out)}


@scenario
def B7_missing_source_outcome():
    """F2P1 scenario via CLI: missing data source + its cache; check real outcome."""
    root, _ = new_repo()
    with open(os.path.join(root, "foo"), "w") as f:
        f.write("foo\n")
    rc, out = dvc(["add", "-q", "foo"], root)
    assert rc == 0, out
    rc, out = dvc(["push", "-q"], root)
    assert rc == 0, out
    rc, out = dvc(["stage", "add", "-q", "-n", "copy-foo", "-d", "foo", "-o", "bar", "cp foo bar"], root)
    assert rc == 0, out
    os.remove(os.path.join(root, "foo"))
    shutil.rmtree(os.path.join(root, ".dvc", "cache"))
    rc, out = dvc(["repro", "--pull"], root)
    return {"rc": rc, "foo": rd(root, "foo"), "bar": rd(root, "bar"),
            "lock_exists": os.path.exists(os.path.join(root, "dvc.lock")), "tail": tail(out)}


@scenario
def B8_intermediate_nondeterministic():
    """Intermediate output with a non-deterministic command: restored or recomputed?"""
    root, _ = new_repo()
    with open(os.path.join(root, "fixed"), "w") as f:
        f.write("fixed\n")
    rc, out = dvc(["stage", "add", "-q", "-n", "create-foo", "-d", "fixed", "-o", "foo",
                   "date +%s%N > foo"], root)
    assert rc == 0, out
    rc, out = dvc(["stage", "add", "-q", "-n", "copy-foo", "-d", "foo", "-o", "bar", "cp foo bar"], root)
    assert rc == 0, out
    rc, out = dvc(["repro", "-q"], root)
    assert rc == 0, out
    orig = rd(root, "foo")
    rc, out = dvc(["push", "-q"], root)
    assert rc == 0, out
    shutil.rmtree(os.path.join(root, ".dvc", "cache"))  # also drops local run-cache
    os.remove(os.path.join(root, "foo"))
    rc, out = dvc(["repro", "--pull"], root)
    return {"rc": rc, "foo_restored_same": rd(root, "foo") == orig,
            "bar_eq_foo": rd(root, "bar") == rd(root, "foo"), "tail": tail(out)}


@scenario
def B9_changed_dep_old_output_unavailable():
    """Deps changed; old output neither local nor on remote (remote empty): `repro --pull`."""
    root, _ = new_repo()
    with open(os.path.join(root, "fixed"), "w") as f:
        f.write("fixed\n")
    rc, out = dvc(["stage", "add", "-q", "-n", "create-foo", "-d", "fixed", "-o", "foo",
                   "cp fixed foo"], root)
    assert rc == 0, out
    rc, out = dvc(["repro", "-q"], root)
    assert rc == 0, out
    shutil.rmtree(os.path.join(root, ".dvc", "cache"))
    with open(os.path.join(root, "fixed"), "w") as f:
        f.write("fixed2\n")
    rc, out = dvc(["repro", "--pull"], root)
    return {"rc": rc, "foo": rd(root, "foo"), "tail": tail(out)}


@scenario
def B1b_dry_missing_output_only():
    """`repro --pull --dry` with only the command output bar missing and empty local cache."""
    root, rem = new_repo()
    base_pipeline(root)
    rc, out = dvc(["push", "-q", "--run-cache"], root)
    assert rc == 0, out
    os.remove(os.path.join(root, "bar"))
    shutil.rmtree(os.path.join(root, ".dvc", "cache"))
    before = snap(root)
    rc, out = dvc(["repro", "--pull", "--dry"], root)
    after = snap(root)
    return {"rc": rc, "workspace": diff(before[0], after[0]),
            "cache_added_n": len(diff(before[1], after[1])["added"]),
            "runs_added_n": len([k for k in diff(before[1], after[1])["added"] if "runs" in k]),
            "tail": tail(out)}


@scenario
def B1c_dry_missing_source_keep_bar():
    """`repro --pull --dry`: data source foo missing (bar, lock intact), empty local cache."""
    root, rem = new_repo()
    base_pipeline(root)
    rc, out = dvc(["push", "-q", "--run-cache"], root)
    assert rc == 0, out
    os.remove(os.path.join(root, "foo"))
    shutil.rmtree(os.path.join(root, ".dvc", "cache"))
    before = snap(root)
    rc, out = dvc(["repro", "--pull", "--dry"], root)
    after = snap(root)
    return {"rc": rc, "workspace": diff(before[0], after[0]),
            "cache_added_n": len(diff(before[1], after[1])["added"]),
            "runs_added_n": len([k for k in diff(before[1], after[1])["added"] if "runs" in k]),
            "tail": tail(out)}


@scenario
def B2c_no_remote_runcache_hit():
    """No remote; bar and dvc.lock deleted, local cache and run-cache kept: `repro --pull`."""
    root, _ = new_repo(remote=False)
    base_pipeline(root)
    os.remove(os.path.join(root, "bar"))
    os.remove(os.path.join(root, "dvc.lock"))
    rc, out = dvc(["repro", "--pull"], root)
    rc2, out2 = dvc(["repro"], os.path.join(root))
    return {"rc_pull": rc, "bar": rd(root, "bar"), "tail_pull": tail(out, 2)}
