在 `/testbed` 中修复原 GitHub issue。使用该任务已激活的 Python 环境，检查公开源码并实现修复。可运行已有公开测试或编写本地验证；完成后说明改动与实际验证结果。这份说明替代旧通用开发提示，不改变原 issue 的功能要求。

# Conan13403：公开开发说明

工作目录为 `/testbed`。使用任务环境中的 `python`，对应 `/opt/miniconda3/envs/testbed/bin/python`；`conan` 和 `conans` 应从当前工作树导入。可用下面的命令确认解释器与导入位置：

```bash
python -c 'import sys,conan,conans; print(sys.executable); print(conan.__file__); print(conans.__file__)'
```

该环境提供 GNU Autoconf 2.71、Automake 1.16.5 和 M4 1.4.18；使用当前工作树的 Conan。可核工具入口和已有公开回归：

```bash
autoreconf --version
automake --version
m4 --version
python -m pytest -n0 -rA conans/test/unittests/tools/gnu/autotools_test.py
```

公开 recipe 的 `install`／`build` 可通过 `python -m conans.conan` 调用。CLI 参数以当前工作树帮助为准；当命令需要 profiles 时显式指定 host／build profile，例如 `-pr:h default -pr:b default`，并先确认 profiles 已存在。不要将 profile 缺失或 recipe 尚未执行的失败当作 issue 已复现；读取完整输出，确认命令到达目标 `build()`／`autoreconf()` 调用。
