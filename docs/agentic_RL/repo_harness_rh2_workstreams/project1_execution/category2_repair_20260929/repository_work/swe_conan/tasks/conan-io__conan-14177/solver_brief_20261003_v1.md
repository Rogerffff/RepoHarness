在 `/testbed` 中修复原 GitHub issue。使用该任务已激活的 Python 环境，检查公开源码并实现修复。可运行已有公开测试或编写本地验证；完成后说明改动与实际验证结果。这份说明替代旧通用开发提示，不改变原 issue 的功能要求。

工作目录为 `/testbed`。`python` 对应 `/opt/miniconda3/envs/testbed/bin/python`，`conan` 与 `conans` 从当前工作树导入。可用以下命令确认位置：

```bash
python -c 'import sys,conan,conans; print(sys.executable); print(conan.__file__); print(conans.__file__)'
```

公开源码中已有的相关测试模块可这样运行：

```bash
python -m pytest -n0 -rA conans/test/unittests/tools/files/test_patches.py
```

CLI 可通过当前源码环境运行：

```bash
python -m conans.conan --version
```
