# pydantic__pydantic-6283 公开开发环境说明

工作目录为 `/testbed`。本题按 Python 3.8 与 pydantic-core 0.42.0 的项目依赖准备；使用 testbed 环境解释器 `/opt/miniconda3/envs/testbed/bin/python`。

可查看仓库现有公开测试，运行对应测试文件：

```bash
/opt/miniconda3/envs/testbed/bin/python -m pytest -q tests/test_root_model.py
```

项目运行依赖及测试依赖以当前候选的 `pyproject.toml` 为准。安装错误需要保留完整日志。
