"""聚焦复核（v3）：用真实的 ``ConanFile.run``（不是测试里的记录器）看候选在命令失败时的实际行为。

镜像里没有 autoreconf，这里在 PATH 前放一个假的 ``autoreconf`` 脚本：当前目录的 configure.ac 含
``BROKEN`` 时以 1 退出，否则生成 configure 并以 0 退出；每次执行都把当前目录记到标记文件。
在已打好候选补丁的 /testbed 里运行（一次性、断网容器）：
    python /exp/review_v3/real_run_demo.py <候选名>
输出一行 JSON：每个场景是否抛出异常（类型与首行信息）、假 autoreconf 实际在哪些目录执行、调用后的当前目录。
"""
import json
import os
import stat
import sys
import tempfile

from conan import ConanFile
from conan.internal.conan_app import ConanFileHelpers
from conan.tools.build import save_toolchain_args
from conan.tools.gnu import Autotools
from conans.test.utils.mocks import ConanFileMock

FAKE = """#!/bin/sh
echo "$(pwd -P)" >> "$AUTORECONF_MARK"
if grep -q BROKEN configure.ac 2>/dev/null; then
  echo "autoreconf: configure.ac: error: possibly undefined macro: BROKEN" >&2
  exit 1
fi
[ -f configure.ac ] || { echo "autoreconf: no configure.ac" >&2; exit 1; }
printf '#!/bin/sh\\n' > configure
exit 0
"""


class _Wrapper:
    def wrap(self, cmd):
        return cmd


class RealRunConanFile(ConanFileMock):
    """ConanFileMock 的目录设置，加上真实的 ConanFile.run（conan_run 起子进程）。"""

    def __init__(self):
        super().__init__()
        self._conan_helpers = ConanFileHelpers(None, _Wrapper())

    def run(self, *args, **kwargs):
        return ConanFile.run(self, *args, **kwargs)


def scenario(name, broken, kwargs, caller, fake_on_path=True):
    root = os.path.realpath(tempfile.mkdtemp(prefix="c3rv3_"))
    source, build = os.path.join(root, "source"), os.path.join(root, "build")
    sub, gen = os.path.join(source, "subfolder"), os.path.join(root, "gen")
    for f in (source, sub, build, gen, os.path.join(root, "bin")):
        os.makedirs(f, exist_ok=True)
    for f in (source, sub, build):
        with open(os.path.join(f, "configure.ac"), "w") as fd:
            fd.write("BROKEN\n" if f in broken(source, sub, build) else "AC_INIT\n")
    fake = os.path.join(root, "bin", "autoreconf")
    with open(fake, "w") as fd:
        fd.write(FAKE)
    os.chmod(fake, os.stat(fake).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    mark = os.path.join(root, "mark.txt")
    open(mark, "w").close()
    env_path = os.environ["PATH"]
    os.environ["AUTORECONF_MARK"] = mark
    os.environ["PATH"] = (os.path.join(root, "bin") + os.pathsep if fake_on_path else "") + \
        "/usr/bin:/bin"
    os.chdir(gen)
    save_toolchain_args({"configure_args": "", "make_args": "", "autoreconf_args": ""})
    conanfile = RealRunConanFile()
    conanfile.folders.set_base_source(source)
    conanfile.folders.set_base_build(build)
    conanfile.folders.set_base_generators(gen)
    autotools = Autotools(conanfile)
    start = {"build": build, "root": root}[caller]
    os.chdir(start)
    kw = {k: (v.format(build=build) if isinstance(v, str) else v) for k, v in kwargs.items()}
    raised = None
    try:
        autotools.autoreconf(**kw)
    except BaseException as e:  # noqa: B902 — 记录任何异常
        raised = "{}: {}".format(type(e).__name__, str(e).splitlines()[0] if str(e) else "")
    after = os.path.realpath(os.getcwd())
    os.environ["PATH"] = env_path
    ran = [os.path.relpath(l.strip(), root) for l in open(mark) if l.strip()]
    rel_after = os.path.relpath(after, root) if after.startswith(root) else after
    return name, {"raised": raised, "ran_in": ran, "cwd_after": rel_after,
                  "caller": os.path.relpath(start, root) if start != root else "."}


def main():
    cand = sys.argv[1]
    out = {}
    for name, broken, kwargs, caller, fake in [
        # 题面场景：build 目录里的 configure.ac 有错，source 里的是好的
        ("build_broken", lambda s, sub, b: {b}, {"build_script_folder": "{build}"}, "build", True),
        # 缺省调用：source 里的 configure.ac 有错
        ("default_broken", lambda s, sub, b: {s}, {}, "build", True),
        # 相对子目录有错
        ("sub_broken", lambda s, sub, b: {sub}, {"build_script_folder": "subfolder"}, "build", True),
        # 调用者不在 build 目录（如外层 with chdir）；build 目录有错
        ("build_broken_from_root", lambda s, sub, b: {b}, {"build_script_folder": "{build}"}, "root",
         True),
        # 机器上没有 autoreconf（与本镜像相同，退出码 127）
        ("no_tool", lambda s, sub, b: set(), {"build_script_folder": "subfolder"}, "build", False),
    ]:
        k, v = scenario(name, broken, kwargs, caller, fake)
        out[k] = v
    print(json.dumps({"cand": cand, "scenarios": out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
