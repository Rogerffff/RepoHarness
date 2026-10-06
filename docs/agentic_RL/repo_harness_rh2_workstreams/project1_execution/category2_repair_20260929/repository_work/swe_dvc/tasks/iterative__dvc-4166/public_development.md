# DVC 公开开发环境说明

源码 checkout 在 `/testbed`，解释器是 `/opt/miniconda3/envs/testbed/bin/python`。先把该解释器目录加入 `PATH`，在 `/testbed` 工作；在临时目录运行DVC命令时使用 `PYTHONPATH=/testbed` 明确当前源码来源。

此版本使用 `pathspec==0.8.1` 和 NetworkX2.3。NetworkX保留原算法，只对Python3.9已移除的 `fractions.gcd` 做兼容替换；包元数据为2.3+rh2.1。镜像已安装这些依赖，不需要联网更新。可用 `python -m pip check` 和 `python -c 'import dvc,networkx; print(dvc.__file__, networkx.__version__)'` 核对来源。

已有公开ignore测试入口为：

```bash
python -m pytest -q tests/unit/test_ignore.py tests/func/test_ignore.py
```

测试文件需以当前checkout中的公开基线为准。命令帮助可通过 `python -m dvc --help` 查看。
