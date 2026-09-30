"""dask__dask-8801 v4 聚焦复核的私有行为探针（不交给求解者）。

在候选已套用的 /testbed 中运行（root 或 nobody 均可），输出一行 JSON。用来证明复核者候选的对错，
依据是公开要求而不是 gold：
- realistic_commented_default：配置目录里先有 ensure_file(comment=True) 写出的全注释 distributed.yaml
  （configuration.rst 描述的下游做法），再有一个顶层为 str 的 mine.yaml：报错点名哪个文件；新进程 import 同样；
- unreadable_then_bad：名为 0.yaml 的子目录排在坏文件 a.yaml 之前；
- multi_file：坏文件 a.yaml 之后有两个正常文件：报错是否也列出正常文件；
- messages：各类坏内容在目录形态下的异常类型与消息（人工判读“原因”）；
- nullish / falsy：显式 null、只有 '---' 与注释、四种假值；
- permission：不可读文件与不可读目录（只有非 root 才有意义）；
- other_ext：.yml 与 .json 的顶层非映射；
- collect_api：dask.config.collect(paths=[坏目录], env={}) 的结果（API 路径）；
- import_direct_file：DASK_CONFIG 直接指向坏文件时新进程 import。
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import warnings

from dask.config import collect, collect_yaml, ensure_file, merge


def load(paths):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            res = collect_yaml(paths=paths)
            out = {"exc": None, "merged": repr(merge(*res))[:200]}
        except Exception as exc:
            out = {"exc": type(exc).__name__, "msg": str(exc)[:400]}
        out["warnings"] = [str(x.message)[:200] for x in w]
    return out


def names(out, **paths):
    msg = out.get("msg") or ""
    return {k: (p in msg) for k, p in paths.items()}


def fresh_import(dask_config, probe="import dask"):
    with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as root_cfg:
        env = dict(os.environ, HOME=home, DASK_ROOT_CONFIG=root_cfg, DASK_CONFIG=dask_config)
        env.pop("PYTHONWARNINGS", None)
        r = subprocess.run([sys.executable, "-c", probe], env=env, capture_output=True, text=True, cwd="/")
        err = [ln for ln in r.stderr.strip().splitlines() if ln.strip() and "dubious ownership" not in ln]
        return {"rc": r.returncode, "stdout": r.stdout.strip()[-200:], "stderr_last": err[-1][:300] if err else "",
                "_stderr": r.stderr}


result = {"uid": os.getuid()}

# 1) realistic: commented default written by ensure_file, then a bad user file
with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as d:
    src_fn = os.path.join(src, "distributed.yaml")
    shutil.copy("/testbed/dask/dask.yaml", src_fn)
    ensure_file(source=src_fn, destination=d, comment=True)
    bad = os.path.join(d, "mine.yaml")
    with open(bad, "wb") as f:
        f.write(b"distributed.worker.memory.target 0.6\n")  # missing colon -> top-level str
    commented = os.path.join(d, "distributed.yaml")
    out = load([d])
    out["names"] = names(out, bad_mine=bad, commented_distributed=commented)
    out["files"] = sorted(os.listdir(d))
    imp = fresh_import(d)
    imp["names_bad_mine"] = bad in imp["_stderr"]
    imp["names_commented_distributed"] = commented in imp["_stderr"]
    del imp["_stderr"]
    result["realistic_commented_default"] = {"collect_yaml": out, "import": imp}

# 2) unreadable entry sorted before the bad file
with tempfile.TemporaryDirectory() as d:
    os.mkdir(os.path.join(d, "0.yaml"))
    bad = os.path.join(d, "a.yaml")
    with open(bad, "wb") as f:
        f.write(b"[1234]")
    out = load([d])
    out["names"] = names(out, bad_a=bad, unreadable_0=os.path.join(d, "0.yaml"))
    result["unreadable_then_bad"] = out

# 3) bad file followed by two valid files
with tempfile.TemporaryDirectory() as d:
    bad = os.path.join(d, "a.yaml")
    with open(bad, "wb") as f:
        f.write(b"hello")
    for n in ("b.yaml", "c.yaml"):
        with open(os.path.join(d, n), "wb") as f:
            f.write(b"x: 1\n")
    out = load([d])
    out["names"] = names(out, bad_a=bad, good_b=os.path.join(d, "b.yaml"), good_c=os.path.join(d, "c.yaml"))
    result["multi_file"] = out

# 4) messages per kind of bad content (directory form)
CASES = {
    "list": b"[1234]",
    "str": b"hello",
    "int": b"1234",
    "float": b"1.5\n",
    "syntax_brace": b"{",
    "syntax_tab": b"a: 1\n\tb: 2\n",
}
result["messages"] = {}
for name, content in CASES.items():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "a.yaml")
        with open(p, "wb") as f:
            f.write(content)
        out = load([d])
        out["path_in_msg"] = p in (out.get("msg") or "")
        result["messages"][name] = out

# 5) null-ish documents and falsy top levels
NULLISH = {"explicit_null": b"null\n", "tilde": b"~\n", "doc_marker_and_comments": b"---\n# x: 1\n",
           "blank_lines": b"\n\n", "empty_mapping": b"{}\n"}
FALSY = {"zero": b"0\n", "false": b"false\n", "empty_list": b"[]\n", "empty_str": b"''\n"}
for group, cases in (("nullish", NULLISH), ("falsy", FALSY)):
    result[group] = {}
    for name, content in cases.items():
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "a.yaml"), "wb") as f:
                f.write(content)
            with open(os.path.join(d, "b.yaml"), "wb") as f:
                f.write(b"x: 1\n")
            result[group][name] = load([d])

# 6) permissions (meaningful only when not root)
result["permission"] = {}
with tempfile.TemporaryDirectory() as d:
    a = os.path.join(d, "a.yaml")
    with open(a, "wb") as f:
        f.write(b"x: 1\n")
    with open(os.path.join(d, "b.yaml"), "wb") as f:
        f.write(b"y: 2\n")
    os.chmod(a, 0)
    result["permission"]["unreadable_file"] = load([d])
    os.chmod(a, 0o644)
    os.chmod(d, 0o300)
    result["permission"]["unreadable_dir"] = load([d])
    os.chmod(d, 0o700)

# 7) other extensions
result["other_ext"] = {}
for ext in (".yml", ".json"):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "a" + ext)
        with open(p, "wb") as f:
            f.write(b"[1234]")
        out = load([d])
        out["path_in_msg"] = p in (out.get("msg") or "")
        result["other_ext"][ext] = out

# 8) collect() API with a bad directory
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "a.yaml")
    with open(p, "wb") as f:
        f.write(b"hello")
    with open(os.path.join(d, "b.yaml"), "wb") as f:
        f.write(b"x: 1\n")
    try:
        res = collect(paths=[d], env={})
        result["collect_api"] = {"exc": None, "result": repr(res)[:200]}
    except Exception as exc:
        result["collect_api"] = {"exc": type(exc).__name__, "path_in_msg": p in str(exc), "msg": str(exc)[:200]}

# 9) DASK_CONFIG pointing directly at a bad file
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "bad.yaml")
    with open(p, "wb") as f:
        f.write(b"hello")
    imp = fresh_import(p)
    imp["path_in_stderr"] = p in imp["_stderr"]
    del imp["_stderr"]
    result["import_direct_file"] = imp

print(json.dumps(result, ensure_ascii=False))
