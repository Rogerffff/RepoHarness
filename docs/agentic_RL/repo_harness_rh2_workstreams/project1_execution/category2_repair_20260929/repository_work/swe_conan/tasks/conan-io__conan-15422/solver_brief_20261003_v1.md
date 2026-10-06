在 `/testbed` 中修复原 GitHub issue。使用该任务已激活的 Python 环境，检查公开源码并实现修复。可运行已有公开测试或编写本地验证；完成后说明改动与实际验证结果。这份说明替代旧通用开发提示，不改变原 issue 的功能要求。

# Conan15422：公开开发说明

工作目录为 `/testbed`。使用任务环境中的 `python`，对应 `/opt/miniconda3/envs/testbed/bin/python`；`conan` 和 `conans` 应从当前工作树导入。可用下面的命令确认解释器与导入位置：

```bash
python -c 'import sys,conan,conans; print(sys.executable); print(conan.__file__); print(conans.__file__)'
```

该环境的 `cmake`／`ctest` 使用 CMake 3.23.5，保留来源工作树和 Conan CLI；原 issue 的 3.27.4 描述提交者环境。可核工具入口和已有相关公开测试模块：

```bash
cmake --version
ctest --version
python -m pytest -n0 -rA conans/test/integration/toolchains/cmake/test_cmaketoolchain.py
```

按当前公开 CLI 和 recipe 生成 presets 后，可以检查生成文件，也可以让当前 CMake 实际配置和构建最小工程。实际命令须使用工程中存在的 configure／build preset 名称；没有执行成功的步骤应明确记录，不把 JSON 文件能够读取视作配置和构建已经通过。
