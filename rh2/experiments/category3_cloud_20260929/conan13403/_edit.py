# 私有候选构造（第3类 conan-13403 主审）：在 base 的 conan/tools/gnu/autotools.py 上替换 autoreconf 方法。
# 用法：在 /testbed 下 `CAND=<名称> python _edit.py`。每个候选的用途见 CANDS 注释与 result.md。
import os
from pathlib import Path

cand = os.environ["CAND"]
p = Path("conan/tools/gnu/autotools.py")
s = p.read_text()

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
assert OLD in s

DOC = '''        """
        Call ``autoreconf``

        :param args: (Optional, Defaulted to ``None``): List of arguments to use for the
                     ``autoreconf`` call.
        :param build_script_folder: Folder where the ``configure.ac`` file is located. A relative
                                    path is relative to conanfile.source_folder. If not specified
                                    conanfile.source_folder is used.
        """
'''
SIG_ARGS_FIRST = "    def autoreconf(self, args=None, build_script_folder=None):\n"
JOIN = '''        script_folder = os.path.join(self._conanfile.source_folder, build_script_folder) \\
            if build_script_folder else self._conanfile.source_folder
        args = args or []
        command = join_arguments(["autoreconf", self._autoreconf_args, cmd_args_to_string(args)])
'''

CANDS = {
    # 合理实现：保留 args 为第一个位置参数，新目录参数放后面，语义同 configure
    "argsfirst": SIG_ARGS_FIRST + DOC + JOIN + '''        with chdir(self, script_folder):
            self._conanfile.run(command)
''',
    # 合理实现（T1 探针）：chdir 的首参按其文档传 recipe 对象
    "conanfile_chdir": SIG_ARGS_FIRST + DOC + JOIN + '''        with chdir(self._conanfile, script_folder):
            self._conanfile.run(command)
''',
    # 合理实现（T1 探针）：用公开的 ConanFile.run(cwd=...) 指定子进程目录，不改变 Python 进程目录
    "runcwd": SIG_ARGS_FIRST + DOC + JOIN + '''        self._conanfile.run(command, cwd=script_folder)
''',
    # 合理实现（T1 探针）：手写 os.chdir + try/finally 恢复
    "oschdir": SIG_ARGS_FIRST + DOC + JOIN + '''        old_folder = os.getcwd()
        os.chdir(script_folder)
        try:
            self._conanfile.run(command)
        finally:
            os.chdir(old_folder)
''',
    # 退化候选（§4 第 3 步）：调用了 chdir 工厂但没有进入上下文，命令在调用者当前目录执行
    "noenter": "    def autoreconf(self, build_script_folder=None, args=None):\n" + DOC + JOIN + '''        chdir(self, script_folder)
        self._conanfile.run(command)
''',
    # 部分修复：用字符串拼接，只对 source 下的相对子目录有效；题面的 build_folder（绝对路径）失效
    "relonly": SIG_ARGS_FIRST + DOC + '''        script_folder = "{}/{}".format(self._conanfile.source_folder, build_script_folder) \\
            if build_script_folder else self._conanfile.source_folder
        args = args or []
        command = join_arguments(["autoreconf", self._autoreconf_args, cmd_args_to_string(args)])
        with chdir(self, script_folder):
            self._conanfile.run(command)
''',
    # 示例拟合：只特判题面示例 build_folder，其它路径按字符串拼到 source 下（其它绝对目录失效）
    "buildlit": SIG_ARGS_FIRST + DOC + '''        if build_script_folder and build_script_folder == self._conanfile.build_folder:
            script_folder = self._conanfile.build_folder
        elif build_script_folder:
            script_folder = "{}/{}".format(self._conanfile.source_folder, build_script_folder)
        else:
            script_folder = self._conanfile.source_folder
        args = args or []
        command = join_arguments(["autoreconf", self._autoreconf_args, cmd_args_to_string(args)])
        with chdir(self, script_folder):
            self._conanfile.run(command)
''',
    # 错误实现：成功时恢复目录，但没有 try/finally，autoreconf 失败时目录不恢复
    "nofinally": SIG_ARGS_FIRST + DOC + JOIN + '''        old_folder = os.getcwd()
        os.chdir(script_folder)
        self._conanfile.run(command)
        os.chdir(old_folder)
''',
    # 错误实现：切换目录后不恢复（之后 configure/make 在错误目录运行）
    "norestore": SIG_ARGS_FIRST + DOC + JOIN + '''        os.chdir(script_folder)
        self._conanfile.run(command)
''',
    # 吞掉错误：指定目录不存在时静默退回 source_folder
    "fallback": SIG_ARGS_FIRST + DOC + JOIN + '''        if not os.path.isdir(script_folder):
            self._conanfile.output.warning("autoreconf folder {} not found, using {}"
                                           .format(script_folder, self._conanfile.source_folder))
            script_folder = self._conanfile.source_folder
        with chdir(self, script_folder):
            self._conanfile.run(command)
''',
    # 吞掉错误：目录错误与 autoreconf 失败都只打警告
    "swallow_all": SIG_ARGS_FIRST + DOC + JOIN + '''        try:
            with chdir(self, script_folder):
                self._conanfile.run(command)
        except Exception as e:
            self._conanfile.output.warning("autoreconf failed: {}".format(e))
''',
    # 吞掉错误：只吞 autoreconf 命令失败
    "swallow_run": SIG_ARGS_FIRST + DOC + JOIN + '''        from conans.errors import ConanException
        with chdir(self, script_folder):
            try:
                self._conanfile.run(command)
            except ConanException as e:
                self._conanfile.output.warning("autoreconf failed: {}".format(e))
''',
    # 错误实现：通过改写 recipe 的 source 目录实现（题面明确不希望改 source folder），且不恢复
    "mutate_source": SIG_ARGS_FIRST + DOC + JOIN + '''        self._conanfile.folders.set_base_source(script_folder)
        with chdir(self, self._conanfile.source_folder):
            self._conanfile.run(command)
''',
    # 误读：缺省改为调用者当前目录（破坏 base 的缺省 source_folder 行为）
    "cwd_default": SIG_ARGS_FIRST + DOC + '''        script_folder = os.path.join(self._conanfile.source_folder, build_script_folder) \\
            if build_script_folder else os.getcwd()
        args = args or []
        command = join_arguments(["autoreconf", self._autoreconf_args, cmd_args_to_string(args)])
        with chdir(self, script_folder):
            self._conanfile.run(command)
''',
    # 参数名不同（P3 检查）：folder=
    "named": "    def autoreconf(self, args=None, folder=None):\n" + DOC + '''        script_folder = os.path.join(self._conanfile.source_folder, folder) \\
            if folder else self._conanfile.source_folder
        args = args or []
        command = join_arguments(["autoreconf", self._autoreconf_args, cmd_args_to_string(args)])
        with chdir(self, script_folder):
            self._conanfile.run(command)
''',
    # ---- 以下按独立复核 review.md §1 的描述重建（复核者文件不在仓库），另加 rv_retcode ----
    # 合理：args 在首位；目录不存在时先抛 ConanException
    "rv_check": SIG_ARGS_FIRST + DOC + JOIN + '''        if not os.path.isdir(script_folder):
            from conans.errors import ConanException
            raise ConanException("autoreconf folder '{}' does not exist".format(script_folder))
        with chdir(self, script_folder):
            self._conanfile.run(command)
''',
    # 合理：目录参数只能用关键字传；chdir 传 recipe、newdir 用关键字
    "rv_kw": "    def autoreconf(self, args=None, *, build_script_folder=None):\n" + DOC + JOIN + '''        with chdir(self._conanfile, newdir=script_folder):
            self._conanfile.run(command)
''',
    # 合理（边界）：失败时抛出带目录信息的新 ConanException，并 from e 保留原异常
    "rv_wrap": SIG_ARGS_FIRST + DOC + JOIN + '''        from conans.errors import ConanException
        with chdir(self, script_folder):
            try:
                self._conanfile.run(command)
            except ConanException as e:
                raise ConanException("Error running autoreconf in '{}'".format(script_folder)) from e
''',
    # 合理（作者补充）：run(ignore_errors=True) 取返回码，非零时自己抛 ConanException
    "rv_retcode": SIG_ARGS_FIRST + DOC + JOIN + '''        from conans.errors import ConanException
        with chdir(self, script_folder):
            ret = self._conanfile.run(command, ignore_errors=True)
        if ret:
            raise ConanException("autoreconf in '{}' failed with code {}".format(script_folder, ret))
''',
    # 错误：指定目录时命令只剩 autoreconf，丢掉 toolchain 参数与用户 args
    "w_argsdrop": "    def autoreconf(self, build_script_folder=None, args=None):\n" + DOC + JOIN + '''        if build_script_folder:
            command = "autoreconf"
        with chdir(self, script_folder):
            self._conanfile.run(command)
''',
    # 错误：总是先在 source 执行一次，再在指定目录执行一次
    "w_twice": "    def autoreconf(self, build_script_folder=None, args=None):\n" + DOC + JOIN + '''        with chdir(self, self._conanfile.source_folder):
            self._conanfile.run(command)
        with chdir(self, script_folder):
            self._conanfile.run(command)
''',
    # 错误：改写 recipe 的 folders.source，再在 source_folder 执行（传 None 时回落，原测试看不出）
    "w_mutate_src2": "    def autoreconf(self, build_script_folder=None, args=None):\n" + DOC + '''        self._conanfile.folders.source = build_script_folder
        args = args or []
        command = join_arguments(["autoreconf", self._autoreconf_args, cmd_args_to_string(args)])
        with chdir(self, self._conanfile.source_folder):
            self._conanfile.run(command)
''',
    # 错误：与 gold 相同，只是 run(..., ignore_errors=True)，吞掉 autoreconf 失败
    "w_ignore_errors": "    def autoreconf(self, build_script_folder=None, args=None):\n" + DOC + JOIN + '''        with chdir(self, script_folder):
            self._conanfile.run(command, ignore_errors=True)
''',
    # 错误：结束后切到 build_folder，而不是回到调用者原目录（os.chdir + finally）
    "w_restore_build": "    def autoreconf(self, build_script_folder=None, args=None):\n" + DOC + JOIN + '''        os.chdir(script_folder)
        try:
            self._conanfile.run(command)
        finally:
            os.chdir(self._conanfile.build_folder)
''',
    # 错误：同上，chdir 上下文之后再切到 build_folder
    "w_restore_build_ctx": "    def autoreconf(self, build_script_folder=None, args=None):\n" + DOC + JOIN + '''        with chdir(self, script_folder):
            self._conanfile.run(command)
        os.chdir(self._conanfile.build_folder)
''',
    # 边界（复核者判为不合理）：目录不存在时先创建
    "w_mkdir": SIG_ARGS_FIRST + DOC + JOIN + '''        if not os.path.isdir(script_folder):
            os.makedirs(script_folder)
        with chdir(self, script_folder):
            self._conanfile.run(command)
''',
    # 另一种相对基准（边界检查）：相对路径以 build_folder 为基准
    "rel_build": SIG_ARGS_FIRST + DOC + '''        script_folder = os.path.join(self._conanfile.build_folder, build_script_folder) \\
            if build_script_folder else self._conanfile.source_folder
        args = args or []
        command = join_arguments(["autoreconf", self._autoreconf_args, cmd_args_to_string(args)])
        with chdir(self, script_folder):
            self._conanfile.run(command)
''',
}

s = s.replace(OLD, CANDS[cand], 1)
p.write_text(s)
print("edited", cand)
