"""聚焦复核（v3）：生成复核者新增候选补丁与私有测试变体。

- 候选：只替换 base 的 ``Autotools.autoreconf`` 方法，写成 ``cands/<名称>.patch``（相对 /testbed，可 ``git apply``）。
  ``r3_*`` 是“合理但与 gold 和已有合理候选都不同”的写法，用来查 v3 的新误拒；
  ``w3_*`` 是针对 v3 放宽处另造的错误或边界候选。
- 测试变体（只用于私有对照，不是正式材料）：在 ``revised_autotools_test_v3.py`` 上做逐字替换，写成
  ``tests/<名称>.py`` 与 ``tests/<名称>.patch``（相对 base 测试文件）。
  ``v3_nochain``：只删掉失败断言里的“异常链或失败码”条件，用来隔离这一条的作用；
  ``v3_fix``：复核建议的修法（失败时命令只在所选目录执行一次；从非 build 目录发起；去掉异常链条件）；
  ``v3_fix_plus``：在 ``v3_fix`` 上把失败场景扩到缺省目录与绝对 build 目录（非阻断建议）。

用法（仓库根目录）：
    python3 rh2/experiments/category3_cloud_20260929/conan13403/review_v3/make_candidates.py \
        --base-autotools <从镜像 /testbed 取出的 conan/tools/gnu/autotools.py>
base 测试文件只有 26 行，内容写在本脚本里（取自镜像 /testbed，提交 55163679）。
"""
import argparse
import difflib
import hashlib
import os

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)

OLD = '''    def autoreconf(self, args=None):
        """
        Call ``autoreconf``

        :param args: (Optional, Defaulted to ``None``): List of arguments to use for the
                     ``autoreconf`` call.
        """
        args = args or []
        command = join_arguments(["autoreconf", self._autoreconf_args, cmd_args_to_string(args)])
        with chdir(self, self._conanfile.source_folder):
            self._conanfile.run(command)
'''

DOC = '''        """
        Call ``autoreconf``

        :param args: (Optional, Defaulted to ``None``): List of arguments to use for the
                     ``autoreconf`` call.
        :param build_script_folder: Folder where the ``configure.ac`` file is located. A relative
                                    path is relative to conanfile.source_folder. If not specified
                                    conanfile.source_folder is used.
        """
'''
SIG_FOLDER_FIRST = "    def autoreconf(self, build_script_folder=None, args=None):\n"
SIG_ARGS_FIRST = "    def autoreconf(self, args=None, build_script_folder=None):\n"
FOLDER = '''        folder = os.path.join(self._conanfile.source_folder, build_script_folder) \\
            if build_script_folder else self._conanfile.source_folder
'''
COMMAND = '''        args = args or []
        command = join_arguments(["autoreconf", self._autoreconf_args, cmd_args_to_string(args)])
'''

CANDS = {
    # ---- 合理（查新误拒） ----
    # try/except 转换异常类型，并用 raise ... from None 隐去原异常的显示
    "r3_fromnone": SIG_FOLDER_FIRST + DOC + '''        from conans.errors import ConanException
        folder = self._conanfile.source_folder
        if build_script_folder:
            folder = os.path.join(folder, build_script_folder)
''' + COMMAND + '''        with chdir(self, folder):
            try:
                self._conanfile.run(command)
            except ConanException as exc:
                raise RuntimeError("autoreconf failed in '{}': {}".format(folder, exc)) from None
''',
    # subprocess 风格：先校验目录，run(cwd=, ignore_errors=True) 拿返回码，非零时抛 CalledProcessError
    "r3_calledprocess": SIG_ARGS_FIRST + DOC + '''        import subprocess
        folder = os.path.normpath(os.path.join(self._conanfile.source_folder,
                                               build_script_folder or ""))
        if not os.path.isdir(folder):
            raise FileNotFoundError("autoreconf folder '{}' not found".format(folder))
''' + COMMAND + '''        returncode = self._conanfile.run(command, cwd=folder, ignore_errors=True)
        if returncode != 0:
            raise subprocess.CalledProcessError(returncode, command)
''',
    # 先校验目录里有 configure.ac 或 configure.in 再切换；chdir 传 recipe 对象
    "r3_validate_conf": SIG_FOLDER_FIRST + DOC + '''        from conans.errors import ConanException
        source_folder = self._conanfile.source_folder
        folder = source_folder if build_script_folder is None \\
            else os.path.join(source_folder, build_script_folder)
        if not any(os.path.isfile(os.path.join(folder, name))
                   for name in ("configure.ac", "configure.in")):
            raise ConanException("autoreconf: no configure.ac or configure.in found in '{}'"
                                 .format(folder))
''' + COMMAND + '''        with chdir(self._conanfile, folder):
            self._conanfile.run(command)
''',
    # 失败时先记下异常，离开 chdir 后再抛新异常（在 except 块之外抛，不连到原异常）
    "r3_deferred_raise": SIG_FOLDER_FIRST + DOC + '''        from conans.errors import ConanException
''' + FOLDER + COMMAND + '''        error = None
        with chdir(self, folder):
            try:
                self._conanfile.run(command)
            except ConanException as exc:
                error = exc
        if error is not None:
            raise ConanException("autoreconf failed in '{}': {}".format(folder, error))
''',
    # 手写 os.chdir，finally 恢复目录后再报错（同样在 except 块之外抛）
    "r3_restore_then_raise": SIG_ARGS_FIRST + DOC + '''        from conans.errors import ConanException
''' + FOLDER + COMMAND + '''        previous = os.getcwd()
        os.chdir(folder)
        failure = None
        try:
            self._conanfile.run(command)
        except ConanException as exc:
            failure = str(exc)
        finally:
            os.chdir(previous)
        if failure is not None:
            raise ConanException("autoreconf in '{}' failed: {}".format(folder, failure))
''',
    # ---- 错误或边界（查 v3 的放宽处） ----
    # 所选目录里失败时，警告后改到 source 目录重跑（与作者 fallback 同类，但由命令失败触发）
    "w3_fallback_on_fail": SIG_FOLDER_FIRST + DOC + '''        from conans.errors import ConanException
        source_folder = self._conanfile.source_folder
        folder = os.path.join(source_folder, build_script_folder) \\
            if build_script_folder else source_folder
''' + COMMAND + '''        try:
            with chdir(self, folder):
                self._conanfile.run(command)
        except ConanException as exc:
            if folder == source_folder:
                raise
            self._conanfile.output.warning("autoreconf failed in '{}' ({}), trying the source "
                                           "folder".format(folder, exc))
            with chdir(self, source_folder):
                self._conanfile.run(command)
''',
    # 同上，返回码写法：拿到失败码后改到 source 目录重跑，仍失败才报错
    "w3_fallback_code": SIG_ARGS_FIRST + DOC + '''        from conans.errors import ConanException
        source_folder = self._conanfile.source_folder
        folder = os.path.join(source_folder, build_script_folder) \\
            if build_script_folder else source_folder
''' + COMMAND + '''        ret = self._conanfile.run(command, cwd=folder, ignore_errors=True)
        if ret != 0 and folder != source_folder:
            self._conanfile.output.warning("autoreconf failed in '{}', trying the source folder"
                                           .format(folder))
            ret = self._conanfile.run(command, cwd=source_folder, ignore_errors=True)
        if ret != 0:
            raise ConanException("autoreconf failed with exit code {}".format(ret))
''',
    # 只在部分路径处理 ignore_errors：只有指定了目录才检查返回码，缺省调用的失败被吞
    "w3_check_only_selected": SIG_ARGS_FIRST + DOC + '''        from conans.errors import ConanException
''' + FOLDER + COMMAND + '''        ret = self._conanfile.run(command, cwd=folder, ignore_errors=True)
        if build_script_folder and ret != 0:
            raise ConanException("autoreconf failed in '{}' with exit code {}".format(folder, ret))
        return ret
''',
    # 只在部分路径处理 ignore_errors：绝对目录（题面的 build 目录）只返回退出码，不报错
    "w3_abs_swallow": SIG_ARGS_FIRST + DOC + FOLDER + COMMAND + '''        if build_script_folder and os.path.isabs(build_script_folder):
            # absolute folders (e.g. the build folder): let the caller check the exit code
            return self._conanfile.run(command, cwd=folder, ignore_errors=True)
        with chdir(self, folder):
            self._conanfile.run(command)
''',
    # 目录恢复只在成功路径正确：失败时切到 build_folder 而不是调用者原目录
    "w3_fail_restore_build": SIG_FOLDER_FIRST + DOC + FOLDER + COMMAND + '''        previous = os.getcwd()
        os.chdir(folder)
        try:
            self._conanfile.run(command)
        except Exception:
            os.chdir(self._conanfile.build_folder)
            raise
        os.chdir(previous)
''',
    # 拿到失败码后抛出与失败“无关”的异常：本意是只打警告，但拼接 int 触发 TypeError
    "w3_code_unrelated": SIG_ARGS_FIRST + DOC + FOLDER + COMMAND + '''        with chdir(self, folder):
            ret = self._conanfile.run(command, ignore_errors=True)
        if ret:
            self._conanfile.output.warning("autoreconf returned " + ret)
''',
    # 返回码写法，目录恢复只在成功路径做：失败时先报错、没有回到原目录
    "w3_code_norestore": SIG_ARGS_FIRST + DOC + '''        from conans.errors import ConanException
''' + FOLDER + COMMAND + '''        previous = os.getcwd()
        os.chdir(folder)
        ret = self._conanfile.run(command, ignore_errors=True)
        if ret != 0:
            raise ConanException("autoreconf failed in '{}' with exit code {}".format(folder, ret))
        os.chdir(previous)
''',
}

BASE_TEST = '''import os

from conan.tools.build import save_toolchain_args
from conan.tools.gnu import Autotools
from conans.test.utils.mocks import ConanFileMock
from conans.test.utils.test_files import temp_folder


def test_source_folder_works():
    folder = temp_folder()
    os.chdir(folder)
    save_toolchain_args({
        "configure_args": "-foo bar",
        "make_args": "",
        "autoreconf_args": ""}
    )
    conanfile = ConanFileMock()
    sources = "/path/to/sources"
    conanfile.folders.set_base_source(sources)
    autotools = Autotools(conanfile)
    autotools.configure(build_script_folder="subfolder")
    assert conanfile.command.replace("\\\\", "/") == '"/path/to/sources/subfolder/configure" -foo bar '

    autotools = Autotools(conanfile)
    autotools.configure()
    assert conanfile.command.replace("\\\\", "/") == '"/path/to/sources/configure" -foo bar '
'''

V3_FAILURE = '''        # A failing autoreconf is not hidden: an error is raised, as is or chained to the
        # failure (or raised after the failing exit code was returned), and the current folder
        # is restored
        conanfile.run_error = ConanException("autoreconf failed")
        with pytest.raises(Exception) as raised:
            autotools.autoreconf(build_script_folder="subfolder")
        chain = []
        error = raised.value
        while error is not None and all(error is not e for e in chain):
            chain.append(error)
            error = error.__cause__ or error.__context__
        assert any(e is conanfile.run_error for e in chain) or conanfile.failed_codes_returned
        assert real(os.getcwd()) == real(build)
'''

NOCHAIN_FAILURE = '''        # A failing autoreconf is not hidden: an error is raised, and the current folder
        # is restored
        conanfile.run_error = ConanException("autoreconf failed")
        with pytest.raises(Exception):
            autotools.autoreconf(build_script_folder="subfolder")
        assert real(os.getcwd()) == real(build)
'''

FIX_FAILURE = '''        # A failing autoreconf is not hidden: an error is raised (any type and message), the
        # failing command ran once, only in the selected folder, and the current folder of the
        # caller is restored (here the caller is not in the build folder)
        conanfile.run_error = ConanException("autoreconf failed")
        os.chdir(root)
        before = len(conanfile.runs)
        with pytest.raises(Exception):
            autotools.autoreconf(build_script_folder="subfolder")
        assert conanfile.runs[before:] == [(real(subfolder), 'autoreconf -bar foo')]
        assert real(os.getcwd()) == real(root)
'''

FIX_PLUS_FAILURE = '''        # A failing autoreconf is not hidden: an error is raised (any type and message), the
        # failing command ran once, only in the selected folder, and the current folder of the
        # caller is restored (here the caller is not in the build folder). Checked for the
        # default folder, a relative folder and an absolute folder (the build folder)
        conanfile.run_error = ConanException("autoreconf failed")
        os.chdir(root)
        for kwargs, expected_folder in [({}, source),
                                        ({"build_script_folder": "subfolder"}, subfolder),
                                        ({"build_script_folder": build}, build)]:
            before = len(conanfile.runs)
            with pytest.raises(Exception):
                autotools.autoreconf(**kwargs)
            assert conanfile.runs[before:] == [(real(expected_folder), 'autoreconf -bar foo')], \\
                kwargs
            assert real(os.getcwd()) == real(root), kwargs
'''

TEST_VARIANTS = {
    "v3_nochain": [(V3_FAILURE, NOCHAIN_FAILURE)],
    "v3_fix": [(V3_FAILURE, FIX_FAILURE)],
    "v3_fix_plus": [(V3_FAILURE, FIX_PLUS_FAILURE)],
}

TEST_PATH = "conans/test/unittests/tools/gnu/autotools_test.py"
SRC_PATH = "conan/tools/gnu/autotools.py"


def unified(path, old, new):
    diff = difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                "a/" + path, "b/" + path, n=3)
    return "diff --git a/{0} b/{0}\n".format(path) + "".join(diff)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-autotools", required=True)
    ns = ap.parse_args()
    base = open(ns.base_autotools).read()
    assert base.count(OLD) == 1, "base autoreconf not found"
    os.makedirs(os.path.join(HERE, "cands"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "tests"), exist_ok=True)
    for name, body in CANDS.items():
        new = base.replace(OLD, body)
        compile(new, name, "exec")
        text = unified(SRC_PATH, base, new)
        with open(os.path.join(HERE, "cands", name + ".patch"), "w") as f:
            f.write(text)
        print("cand", name, hashlib.sha256(text.encode()).hexdigest()[:8])
    v3 = open(os.path.join(EXP, "revised_autotools_test_v3.py")).read()
    for name, repls in TEST_VARIANTS.items():
        new = v3
        for old, rep in repls:
            assert new.count(old) == 1, (name, old[:40])
            new = new.replace(old, rep)
        compile(new, name, "exec")
        with open(os.path.join(HERE, "tests", name + ".py"), "w") as f:
            f.write(new)
        text = unified(TEST_PATH, BASE_TEST, new)
        with open(os.path.join(HERE, "tests", name + ".patch"), "w") as f:
            f.write(text)
        print("test", name, hashlib.sha256(text.encode()).hexdigest()[:8])


if __name__ == "__main__":
    main()
