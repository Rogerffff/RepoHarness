# 私有行为矩阵（第3类 conan-13403 主审）：不 mock chdir，用真实临时目录；recipe.run 被替换为记录器，
# 记录命令执行时的实际目录（与 ConanFile.run 相同：给了 cwd 用 cwd，否则用进程当前目录），不执行系统 autoreconf。
# 每个场景前把进程目录设为 build（recipe 的 build() 在 build 目录运行），场景后核对进程目录是否恢复、
# recipe 的 source/build 目录是否被改写。
import json
import os
import tempfile
import traceback

from conan.tools.build import save_toolchain_args
from conan.tools.gnu import Autotools
from conans.errors import ConanException
from conans.test.utils.mocks import ConanFileMock
from conans.util.files import save


class Recorder(ConanFileMock):
    def __init__(self):
        super().__init__()
        self.runs = []
        self.fail_next = False

    def run(self, command, stdout=None, cwd=None, **kwargs):
        where = cwd if cwd else os.getcwd()
        if not os.path.isdir(where):
            raise FileNotFoundError(where)
        self.command = command
        self.runs.append((os.path.realpath(where), command))
        if self.fail_next:
            self.fail_next = False
            raise ConanException("simulated autoreconf failure")
        return 0


def main():
    original = os.getcwd()
    root = os.path.realpath(tempfile.mkdtemp())
    gen = os.path.join(root, "gen")
    source = os.path.join(root, "src")
    sub = os.path.join(source, "sub")
    build = os.path.join(root, "build dir")
    for d in (gen, sub, build):
        os.makedirs(d, exist_ok=True)
    for d in (source, sub, build):
        save(os.path.join(d, "configure.ac"), "AC_INIT([x], [1])\n")
    os.chdir(gen)
    save_toolchain_args({"configure_args": "", "make_args": "", "autoreconf_args": "--verbose"})
    names = {source: "SRC", sub: "SRC/sub", build: "BUILD"}

    def fresh():
        cf = Recorder()
        cf.folders.set_base_source(source)
        cf.folders.set_base_build(build)
        cf.folders.set_base_generators(gen)
        return cf, Autotools(cf)

    scenarios = [
        ("default", lambda at, cf: at.autoreconf()),
        ("args_kw", lambda at, cf: at.autoreconf(args=["--install"])),
        ("args_positional", lambda at, cf: at.autoreconf(["--install"])),
        ("rel_sub", lambda at, cf: at.autoreconf(build_script_folder="sub")),
        ("abs_build", lambda at, cf: at.autoreconf(build_script_folder=cf.build_folder)),
        ("abs_build_args", lambda at, cf: at.autoreconf(build_script_folder=cf.build_folder, args=["--install"])),
        ("abs_sub", lambda at, cf: at.autoreconf(build_script_folder=sub)),
        ("missing", lambda at, cf: at.autoreconf(build_script_folder="missing")),
        ("run_fails_sub", None),
        ("sequence_sub_then_default", None),
    ]
    result = {}
    for name, fn in scenarios:
        cf, at = fresh()
        os.chdir(build)
        rec = {}
        try:
            if name == "run_fails_sub":
                cf.fail_next = True
                at.autoreconf(build_script_folder="sub")
            elif name == "sequence_sub_then_default":
                at.autoreconf(build_script_folder="sub")
                at.autoreconf()
            else:
                fn(at, cf)
            rec["exception"] = None
        except Exception as e:  # noqa
            rec["exception"] = "{}: {}".format(type(e).__name__, str(e)[:160])
            tb = traceback.extract_tb(e.__traceback__)
            rec["raised_at"] = "{}:{}".format(os.path.basename(tb[-1].filename), tb[-1].lineno) if tb else None
        rec["runs"] = [[names.get(w, w), c] for w, c in cf.runs]
        after = os.path.realpath(os.getcwd())
        rec["cwd_after"] = names.get(after, after)
        rec["cwd_restored"] = after == os.path.realpath(build)
        rec["source_folder_unchanged"] = cf.source_folder == source
        result[name] = rec
    os.chdir(original)
    print(json.dumps(result, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
