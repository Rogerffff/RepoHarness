"""Reviewer probes, round 2 (focused on c3_missing_only and N2).

Each scenario: fresh temp git+dvc repo, local directory remote, real CLI (non-TTY unless noted).
Prints one JSON line per scenario.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

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


def ok(rc_out):
    rc, out = rc_out
    assert rc == 0, out[-800:]
    return out


def tail(out, n=3):
    lines = [l for l in out.splitlines() if l.strip() and "hardlink_lock" not in l]
    return lines[-n:]


def rd(root, name):
    p = os.path.join(root, name)
    if os.path.isdir(p):
        return sorted(os.listdir(p))
    return open(p).read() if os.path.exists(p) else None


def w(root, name, text):
    p = os.path.join(root, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(text)


def new_repo():
    root = tempfile.mkdtemp(prefix="repo_")
    rem = tempfile.mkdtemp(prefix="remote_")
    ok(run("git init -q", root))
    ok(dvc(["init", "-q"], root))
    ok(dvc(["remote", "add", "-d", "local", rem], root))
    return root, rem


def commit(root):
    ok(run("git add -A && git commit -qm c", root))


def clone(root):
    dst = tempfile.mkdtemp(prefix="clone_")
    shutil.rmtree(dst)
    ok(run(f"git clone -q {root} {dst}", "/tmp"))
    return dst


def scenario(fn):
    if ONLY and fn.__name__ not in ONLY:
        return fn
    try:
        res = fn()
    except Exception as exc:  # noqa: BLE001
        res = {"harness_error": repr(exc)[:600]}
    print(json.dumps({"scenario": fn.__name__, **res}), flush=True)
    return fn


@scenario
def C1_frozen_stage_missing_output():
    """Frozen command stage (e.g. a download step) whose output is only on the remote."""
    root, _ = new_repo()
    w(root, "src", "src\n")
    ok(dvc(["stage", "add", "-q", "-n", "download", "-d", "src", "-o", "raw", "cp src raw"], root))
    ok(dvc(["stage", "add", "-q", "-n", "prep", "-d", "raw", "-o", "prep", "sed s/src/PREP/ raw > prep"], root))
    ok(dvc(["repro", "-q"], root))
    ok(dvc(["freeze", "download"], root))
    ok(dvc(["push", "-q", "--run-cache"], root))
    os.remove(os.path.join(root, "raw"))
    shutil.rmtree(os.path.join(root, ".dvc", "cache"))
    rc, out = dvc(["repro", "--pull"], root)
    return {"rc": rc, "raw": rd(root, "raw"), "prep": rd(root, "prep"), "tail": tail(out)}


@scenario
def C2_fresh_clone_with_frozen():
    """Fresh clone: data source + frozen stage + two command stages, everything pushed."""
    root, _ = new_repo()
    w(root, "data", "data\n")
    w(root, "src", "src\n")
    ok(dvc(["add", "-q", "data"], root))
    ok(dvc(["stage", "add", "-q", "-n", "download", "-d", "src", "-o", "ext", "cp src ext"], root))
    ok(dvc(["stage", "add", "-q", "-n", "prep", "-d", "data", "-o", "prep", "sed s/data/PREP/ data > prep"], root))
    ok(dvc(["stage", "add", "-q", "-n", "train", "-d", "prep", "-d", "ext", "-o", "model",
            "cat prep ext > model"], root))
    ok(dvc(["repro", "-q"], root))
    ok(dvc(["freeze", "download"], root))
    ok(dvc(["push", "-q", "--run-cache"], root))
    commit(root)
    cl = clone(root)
    rc, out = dvc(["repro", "--pull"], cl)
    return {"rc": rc, "data": rd(cl, "data"), "ext": rd(cl, "ext"), "model": rd(cl, "model"),
            "tail": tail(out)}


@scenario
def C3_fresh_clone_no_frozen():
    """Fresh clone without frozen stages: data source + two command stages."""
    root, _ = new_repo()
    w(root, "data", "data\n")
    ok(dvc(["add", "-q", "data"], root))
    ok(dvc(["stage", "add", "-q", "-n", "prep", "-d", "data", "-o", "prep", "sed s/data/PREP/ data > prep"], root))
    ok(dvc(["stage", "add", "-q", "-n", "train", "-d", "prep", "-o", "model", "cat prep prep > model"], root))
    ok(dvc(["repro", "-q"], root))
    ok(dvc(["push", "-q", "--run-cache"], root))
    commit(root)
    cl = clone(root)
    rc, out = dvc(["repro", "--pull"], cl)
    return {"rc": rc, "data": rd(cl, "data"), "prep": rd(cl, "prep"), "model": rd(cl, "model"),
            "tail": tail(out)}


@scenario
def C4_subdir_pipeline_run_from_subdir():
    """Data source and pipeline in a subdirectory; `repro --pull` run with cwd=sub."""
    root, _ = new_repo()
    sub = os.path.join(root, "sub")
    w(root, "sub/raw", "raw\n")
    ok(dvc(["add", "-q", "raw"], sub))
    ok(dvc(["stage", "add", "-q", "-n", "copy", "-d", "raw", "-o", "out", "cp raw out"], sub))
    ok(dvc(["push", "-q"], sub))
    os.remove(os.path.join(sub, "raw"))
    shutil.rmtree(os.path.join(root, ".dvc", "cache"))
    rc, out = dvc(["repro", "--pull"], sub)
    return {"rc": rc, "raw": rd(sub, "raw"), "out": rd(sub, "out"), "tail": tail(out)}


@scenario
def C5_dir_source_fully_missing():
    root, _ = new_repo()
    w(root, "d/a", "a\n")
    w(root, "d/b", "b\n")
    ok(dvc(["add", "-q", "d"], root))
    ok(dvc(["stage", "add", "-q", "-n", "ls", "-d", "d", "-o", "listing", "ls d > listing"], root))
    ok(dvc(["push", "-q"], root))
    shutil.rmtree(os.path.join(root, "d"))
    shutil.rmtree(os.path.join(root, ".dvc", "cache"))
    rc, out = dvc(["repro", "--pull"], root)
    return {"rc": rc, "d": rd(root, "d"), "listing": rd(root, "listing"), "tail": tail(out)}


@scenario
def C6_dir_source_partially_missing():
    """One file deleted inside a tracked directory: restored, or treated as a modification?"""
    root, _ = new_repo()
    w(root, "d/a", "a\n")
    w(root, "d/b", "b\n")
    ok(dvc(["add", "-q", "d"], root))
    ok(dvc(["stage", "add", "-q", "-n", "ls", "-d", "d", "-o", "listing", "ls d > listing"], root))
    ok(dvc(["repro", "-q"], root))
    ok(dvc(["push", "-q"], root))
    os.remove(os.path.join(root, "d", "b"))
    before = open(os.path.join(root, "d.dvc")).read()
    rc, out = dvc(["repro", "--pull"], root)
    after = open(os.path.join(root, "d.dvc")).read()
    return {"rc": rc, "d": rd(root, "d"), "listing": rd(root, "listing"),
            "d_dvc_rewritten": before != after, "tail": tail(out)}


@scenario
def C7_mixed_missing_and_modified():
    root, _ = new_repo()
    w(root, "a", "a\n")
    w(root, "b", "b\n")
    ok(dvc(["add", "-q", "a", "b"], root))
    ok(dvc(["stage", "add", "-q", "-n", "cat", "-d", "a", "-d", "b", "-o", "ab", "cat a b > ab"], root))
    ok(dvc(["repro", "-q"], root))
    ok(dvc(["push", "-q"], root))
    a_md5 = hashlib.md5(b"a\n").hexdigest()
    os.remove(os.path.join(root, "a"))
    cp = os.path.join(root, ".dvc", "cache", a_md5[:2], a_md5[2:])
    os.chmod(cp, 0o644)
    os.remove(cp)
    w(root, "b", "B-modified\n")
    rc, out = dvc(["repro", "--pull"], root)
    return {"rc": rc, "a": rd(root, "a"), "b": rd(root, "b"), "ab": rd(root, "ab"), "tail": tail(out)}


@scenario
def C8_missing_source_not_on_remote():
    """Data source missing locally and never pushed: `repro --pull` must not report success."""
    root, _ = new_repo()
    w(root, "foo", "foo\n")
    ok(dvc(["add", "-q", "foo"], root))
    ok(dvc(["stage", "add", "-q", "-n", "copy", "-d", "foo", "-o", "bar", "cp foo bar"], root))
    os.remove(os.path.join(root, "foo"))
    shutil.rmtree(os.path.join(root, ".dvc", "cache"))
    rc, out = dvc(["repro", "--pull"], root)
    return {"rc": rc, "foo": rd(root, "foo"), "bar": rd(root, "bar"), "tail": tail(out)}


@scenario
def C9_failing_command_with_pull():
    """A stage command fails: `repro --pull` must fail too."""
    root, _ = new_repo()
    w(root, "foo", "foo\n")
    ok(dvc(["add", "-q", "foo"], root))
    ok(dvc(["stage", "add", "-q", "-n", "bad", "-d", "foo", "-o", "bar", "exit 3"], root))
    rc, out = dvc(["repro", "--pull"], root)
    return {"rc": rc, "bar": rd(root, "bar"), "tail": tail(out)}


@scenario
def C10_modified_source_tty_yes():
    """User edits data source; interactive terminal answering 'y' to any prompt."""
    root, _ = new_repo()
    w(root, "foo", "foo\n")
    ok(dvc(["add", "-q", "foo"], root))
    ok(dvc(["stage", "add", "-q", "-n", "copy", "-d", "foo", "-o", "bar", "cp foo bar"], root))
    ok(dvc(["repro", "-q"], root))
    ok(dvc(["push", "-q"], root))
    w(root, "foo", "new\n")
    cmd = "script -qec '" + " ".join(DVC) + " repro --pull' /dev/null"
    rc, out = run(cmd, root, stdin="y\ny\ny\n")
    return {"rc": rc, "foo": rd(root, "foo"), "bar": rd(root, "bar"),
            "prompted": "Are you sure" in out, "tail": tail(out, 2)}


@scenario
def C11_import_missing_output():
    """`dvc import` from a local git+dvc repo; output and cache removed; `repro --pull`."""
    src, _ = new_repo()
    w(src, "foo", "foo\n")
    ok(dvc(["add", "-q", "foo"], src))
    ok(dvc(["push", "-q"], src))
    commit(src)
    root, _ = new_repo()
    ok(dvc(["import", "-q", src, "foo"], root))
    ok(dvc(["stage", "add", "-q", "-n", "copy", "-d", "foo", "-o", "bar", "cp foo bar"], root))
    ok(dvc(["repro", "-q"], root))
    commit(root)
    os.remove(os.path.join(root, "foo"))
    shutil.rmtree(os.path.join(root, ".dvc", "cache"))
    rc, out = dvc(["repro", "--pull"], root)
    return {"rc": rc, "foo": rd(root, "foo"), "bar": rd(root, "bar"), "tail": tail(out)}
