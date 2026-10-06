# MONAI 3715 公开开发信息

项目工作目录是 `/testbed`。使用环境中已有的 testbed Python：

```bash
cd /testbed
/opt/miniconda3/envs/testbed/bin/python -c "import sys, monai; print(sys.executable); print(monai.__file__)"
/opt/miniconda3/envs/testbed/bin/python -m pytest -q --tb=short tests/test_prepare_batch_default.py
```

可用 CPU 合成张量与小网络复现题面中的 evaluator 模式行为；无需 GPU、预训练权重或外部数据。公开 API 包括 `monai.engines.SupervisedEvaluator`、`monai.utils.ForwardMode` 和 PyTorch。使用仓库中的 MONAI 源码与已有 testbed 依赖执行开发和测试。
