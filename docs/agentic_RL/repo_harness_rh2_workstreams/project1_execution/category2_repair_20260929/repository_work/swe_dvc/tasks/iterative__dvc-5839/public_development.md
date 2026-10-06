# DVC 公开开发环境说明

本题使用 `/testbed` 中的 DVC checkout。Python 解释器为 `/opt/miniconda3/envs/testbed/bin/python`；shell 中先将该目录加入 `PATH`，在 `/testbed` 工作。运行命令时可用 `PYTHONPATH=/testbed` 明确指定当前源码来源。

公开依赖环境固定 `pathspec==0.8.1`，用于匹配此版本 DVC 的规则解析接口。镜像已包含依赖；不需要联网更新它们。可先核对 `python --version`、`python -c 'import dvc; print(dvc.__file__)'` 与 `python -m pip check`。

已有公开测试可从以下命令开始：

```bash
python -m pytest -q tests/unit/command/test_metrics.py::test_metrics_show_precision tests/unit/command/test_metrics.py::test_metrics_diff_precision
```

临时目录中的真实命令可使用 `PYTHONPATH=/testbed python -m dvc metrics show <metrics文件> <选项>`。命令帮助由 `python -m dvc metrics show --help` 查看。
