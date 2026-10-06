# DVC 公开开发环境说明

源码 checkout 在 `/testbed`，解释器是 `/opt/miniconda3/envs/testbed/bin/python`。先把该解释器目录加入 `PATH`，在 `/testbed` 工作；在临时目录运行DVC命令时使用 `PYTHONPATH=/testbed` 明确当前源码来源。

Git后端固定 `pygit2==1.14.1`，匹配此版本DVC所需接口与CPython3.9 ABI。镜像已安装依赖，不需要联网更新。可先核对 `python -m pip check`、`python -c 'import dvc,pygit2; print(dvc.__file__, pygit2.__version__, pygit2.LIBGIT2_VERSION)'`。

已有公开工作流测试入口为：

```bash
python -m pytest -q tests/func/test_repro_multistage.py
```

测试文件需以当前checkout中的公开基线为准。命令选项可用 `python -m dvc repro --help` 查看；临时复现仓库先执行 `git init` 和 `python -m dvc init`。
