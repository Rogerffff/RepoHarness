"""私有行为对照：repro --pull 与 --dry / 无 remote 的组合。每个场景一个新的临时 git+dvc 仓库，
比较调用前后工作区与 .dvc/cache 的文件快照（排除 .git、.dvc/tmp）。"""
import json
import os
import shutil
import subprocess
import tempfile
import traceback

from dvc.repo import Repo
from dvc.utils.fs import remove


def snapshot(root):
    out = {}
    for d, dirs, files in os.walk(root):
        rel = os.path.relpath(d, root)
        if rel.startswith(".git") or rel.startswith(os.path.join(".dvc", "tmp")):
            dirs[:] = []
            continue
        for f in files:
            p = os.path.join(d, f)
            out[os.path.relpath(p, root)] = os.path.getsize(p)
    return out


def new_repo(with_remote):
    root = tempfile.mkdtemp(prefix="dvc9395_")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "r"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "r@l"], cwd=root, check=True)
    repo = Repo.init(root)
    remote = None
    if with_remote:
        remote = tempfile.mkdtemp(prefix="dvc9395_remote_")
        with repo.config.edit() as conf:
            conf["remote"]["storage"] = {"url": remote}
            conf["core"]["remote"] = "storage"
    return root, repo, remote


def write(root, name, text):
    with open(os.path.join(root, name), "w") as f:
        f.write(text)


def run_case(name, fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return {"setup_or_case_exception": f"{type(e).__name__}: {str(e)[:200]}", "tb": traceback.format_exc()[-600:]}


def call(root, repo, **kw):
    before = snapshot(root)
    exc = None
    try:
        stages = repo.reproduce(**kw)
        ran = [s.addressing for s in stages] if stages else []
    except Exception as e:  # noqa: BLE001
        exc = f"{type(e).__name__}: {str(e)[:200]}"
        ran = None
    after = snapshot(root)
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    return {"exception": exc, "reproduced": ran, "files_added": added, "files_removed": removed}


def data_source_case(dry):
    root, repo, _ = new_repo(True)
    os.chdir(root)
    write(root, "foo", "foo")
    (stage,) = repo.add("foo")
    repo.push()
    repo.stage.add(name="copy-foo", cmd="cp foo bar", deps=["foo"], outs=["bar"])
    remove(os.path.join(root, "foo"))
    remove(stage.outs[0].cache_path)
    return call(root, repo, pull=True, dry=dry)


def no_remote_case(dry):
    root, repo, _ = new_repo(False)
    os.chdir(root)
    write(root, "foo", "foo")
    repo.add("foo")
    repo.stage.add(name="copy-foo", cmd="cp foo bar", deps=["foo"], outs=["bar"])
    return call(root, repo, pull=True, dry=dry)


def run_cache_case(dry):
    root, repo, _ = new_repo(True)
    os.chdir(root)
    write(root, "foo", "foo")
    stage = repo.run(cmd="cp foo bar", deps=["foo"], outs=["bar"], name="copy-foo-bar")
    repo.push(run_cache=True)
    remove(os.path.join(root, "bar"))
    remove(os.path.join(root, "dvc.lock"))
    remove(stage.outs[0].cache_path)
    remove(repo.stage_cache.cache_dir)
    return call(root, repo, targets=["copy-foo-bar"], pull=True, dry=dry)


out = {}
for name, fn in (("data_source_pull_dry", lambda: data_source_case(True)),
                 ("data_source_pull", lambda: data_source_case(False)),
                 ("no_remote_pull", lambda: no_remote_case(False)),
                 ("no_remote_pull_dry", lambda: no_remote_case(True)),
                 ("run_cache_pull_dry", lambda: run_cache_case(True)),
                 ("run_cache_pull", lambda: run_cache_case(False))):
    out[name] = run_case(name, fn)
print(json.dumps(out, ensure_ascii=False, indent=1))
