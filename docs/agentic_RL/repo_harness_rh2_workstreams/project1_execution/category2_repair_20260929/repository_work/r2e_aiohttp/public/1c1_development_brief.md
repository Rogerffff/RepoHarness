# aiohttp 1c1 公开开发说明

工作区为 `/testbed`，`python` 指向 `/testbed/.venv/bin/python`（Python 3.9.21）。使用已安装依赖，环境没有外网。

题面的 startup 示例可以直接观察异常传播与日志。应分别记录向调用者抛出的异常和相关日志条数；脚本退出 0 不表示示例所述问题已修复。

相关公开运行／关闭测试使用：

```bash
cd /testbed
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider \
    --color=no -rfE tests/test_run_app.py
```

这条命令包含真实本地运行与关闭测试，部分测试会等待数秒。按题面与公开回归验证修复，并记录实际输出。
