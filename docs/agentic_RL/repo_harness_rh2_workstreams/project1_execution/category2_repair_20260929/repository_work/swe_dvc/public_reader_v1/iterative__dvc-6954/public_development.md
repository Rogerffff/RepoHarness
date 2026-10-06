# DVC 公开开发环境说明

本题使用 `/testbed` 中的 DVC checkout。Python 解释器为 `/opt/miniconda3/envs/testbed/bin/python`；shell 中先将该目录加入 `PATH`，在 `/testbed` 工作。运行命令时可用 `PYTHONPATH=/testbed` 明确指定当前源码来源。

公开依赖环境固定 `pygit2==1.14.1`，保留此版本 DVC 所需的 Git 后端接口。镜像已包含依赖；不需要联网更新它们。可先核对 `python --version`、`python -c 'import dvc; print(dvc.__file__)'` 与 `python -m pip check`。

已有公开测试可从以下命令开始：

```bash
python -m pytest -q tests/func/params/test_show.py
```

真实命令应在临时 Git/DVC 仓库中运行：先 `git init`，再 `PYTHONPATH=/testbed python -m dvc init`。命令帮助可用 `python -m dvc run --help`、`python -m dvc repro --help` 查看。
