#!/usr/bin/env python3
"""在 base_commit worktree 上做最小替换 -> 生成 <iid>.fake.diff -> 复原 -> git apply --check。

用法（作为库）：mk(iid, [(relpath, old, new), ...])
只操作 runs/.../L7_fake_fix_kits/wt/<iid> 这个一次性 worktree，不碰任何裸克隆的引用。
"""
import os, subprocess, sys

ROOT = "runs/env_overnight_20260916/L7_fake_fix_kits"
WT = os.path.join(ROOT, "wt")
PATCHES = os.path.join(ROOT, "patches")


def mk(iid, edits, suffix="fake"):
    wt = os.path.join(WT, iid)
    if not os.path.isdir(wt):
        raise SystemExit(f"worktree 不存在: {wt}")
    for rel, old, new in edits:
        p = os.path.join(wt, rel)
        s = open(p).read()
        n = s.count(old)
        if n != 1:
            subprocess.run(["git", "-C", wt, "checkout", "--", "."], check=False)
            raise SystemExit(f"[{iid}] {rel} 锚点出现 {n} 次（需要恰好 1 次）:\n{old[:300]}")
        open(p, "w").write(s.replace(old, new))
    out = os.path.join(PATCHES, f"{iid}.{suffix}.diff")
    d = subprocess.run(["git", "-C", wt, "diff"], capture_output=True, text=True).stdout
    open(out, "w").write(d)
    subprocess.run(["git", "-C", wt, "checkout", "--", "."], check=True)
    r = subprocess.run(["git", "-C", wt, "apply", "--check", out], capture_output=True, text=True)
    ok = r.returncode == 0
    print(f"[{iid}] ({suffix}) apply --check {'OK' if ok else 'FAIL: ' + r.stderr.strip()}  ({len(d.splitlines())} 行 diff)")
    if not ok:
        raise SystemExit(1)
    return out


def mk_append(iid, rel, text, suffix="fake"):
    """在文件末尾追加一段文本后生成 diff（用于『重定义评分支撑函数』一类的假修复）。"""
    wt = os.path.join(WT, iid)
    p = os.path.join(wt, rel)
    s = open(p).read()
    if not s.endswith("\n"):
        s += "\n"
    open(p, "w").write(s + text)
    out = os.path.join(PATCHES, f"{iid}.{suffix}.diff")
    d = subprocess.run(["git", "-C", wt, "diff"], capture_output=True, text=True).stdout
    open(out, "w").write(d)
    subprocess.run(["git", "-C", wt, "checkout", "--", "."], check=True)
    r = subprocess.run(["git", "-C", wt, "apply", "--check", out], capture_output=True, text=True)
    ok = r.returncode == 0
    print(f"[{iid}] ({suffix}) apply --check {'OK' if ok else 'FAIL: ' + r.stderr.strip()}  ({len(d.splitlines())} 行 diff)")
    if not ok:
        raise SystemExit(1)
    return out


def mk_newfile(iid, rel, text, suffix="fake"):
    """新建文件的假修复：手写 new-file diff，再用 git apply --check 校验。"""
    import hashlib
    wt = os.path.join(WT, iid)
    if os.path.exists(os.path.join(wt, rel)):
        raise SystemExit(f"[{iid}] {rel} 已存在，新建文件的假修复不成立")
    body = text if text.endswith("\n") else text + "\n"
    blob = b"blob %d\0%s" % (len(body.encode()), body.encode())
    sha = hashlib.sha1(blob).hexdigest()
    lines = body.split("\n")[:-1]
    d = (f"diff --git a/{rel} b/{rel}\n"
         f"new file mode 100644\n"
         f"index 0000000000000000000000000000000000000000..{sha}\n"
         f"--- /dev/null\n"
         f"+++ b/{rel}\n"
         f"@@ -0,0 +1,{len(lines)} @@\n"
         + "".join("+" + l + "\n" for l in lines))
    out = os.path.join(PATCHES, f"{iid}.{suffix}.diff")
    open(out, "w").write(d)
    r = subprocess.run(["git", "-C", wt, "apply", "--check", out], capture_output=True, text=True)
    ok = r.returncode == 0
    print(f"[{iid}] ({suffix}) apply --check {'OK' if ok else 'FAIL: ' + r.stderr.strip()}  ({len(d.splitlines())} 行 diff)")
    if not ok:
        raise SystemExit(1)
    return out
