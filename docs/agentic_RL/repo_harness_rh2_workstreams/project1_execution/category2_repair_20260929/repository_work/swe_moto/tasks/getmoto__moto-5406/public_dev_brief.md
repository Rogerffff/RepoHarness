# Moto5406 开发环境说明

工作目录为 `/testbed`，仓库基线提交为 `87683a786f0d3a0280c92ea01fecce8a3dd4b0fd`。使用镜像已有的 testbed conda 解释器：`/opt/miniconda3/envs/testbed/bin/python`。Moto 从 `/testbed/moto/` 导入；可以核对解释器、源码及公开依赖：

```bash
cd /testbed
/opt/miniconda3/envs/testbed/bin/python -B -c "import sys, moto, boto3, botocore, pytest; print(sys.executable, moto.__file__, boto3.__version__, botocore.__version__, pytest.__version__)"
```

将题面中的 Python 复现示例保存为 `/tmp/public_repro.py`，运行其 pytest 用例：

```bash
AWS_EC2_METADATA_DISABLED=true /opt/miniconda3/envs/testbed/bin/python -B -m pytest -n0 -rA -vv --tb=long /tmp/public_repro.py::test_table_create
```

仓库已有的公开建表测试也可用于开发验证：

```bash
AWS_ACCESS_KEY_ID=testing AWS_SECRET_ACCESS_KEY=testing AWS_EC2_METADATA_DISABLED=true /opt/miniconda3/envs/testbed/bin/python -B -m pytest -n0 -rA -vv tests/test_dynamodb/test_dynamodb_create_table.py::test_create_table_standard
```

复现使用 Moto 的模拟 DynamoDB，不需要真实 AWS 凭据。项目原安装入口为 `make init`；镜像已有上述 Python 环境和公开依赖。
