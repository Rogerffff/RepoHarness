在 `/testbed` 中修复原 GitHub issue。使用该任务已激活的 Python 环境，检查公开源码并实现修复。可运行已有公开测试或编写本地验证；完成后说明改动与实际验证结果。这份说明替代旧通用开发提示，不改变原 issue 的功能要求。

# Conan11594：公开开发说明

工作目录为 `/testbed`。使用任务环境中的 `python`，对应 `/opt/miniconda3/envs/testbed/bin/python`；`conan` 和 `conans` 应从当前工作树导入。可用下面的命令确认解释器与导入位置：

```bash
python -c 'import sys,conan,conans; print(sys.executable); print(conan.__file__); print(conans.__file__)'
```

该环境保留系统 CMake 3.22.1，并提供 Python 分发包 `ninja==1.10.2.4`（可执行程序的版本串以 `ninja --version` 为准）。issue 中的 CMake／Conan 版本描述提交者环境；修复和本地验证使用当前工作树及固定任务环境。可先核工具版本：

```bash
cmake --version
ninja --version
```

在 recipe 中调用 `cmake.test()` 的公开复现，可通过 `python -m conans.conan build .` 执行。请先按当前源码版本准备 recipe、profiles 及相应构建目录，再运行命令；它不是独立于配置和构建步骤的完整复现。已有测试文件以公开工作树实际存在的路径为准，可运行窄范围测试或在本地准备最小 CMake 工程检查实际测试执行。
