# Moto5960 开发环境说明

工作目录为 `/testbed`，仓库基线为 `d1e3f50756fdaaea498e8e47d5dcd56686e6ecdf`。沿用原公开说明中的 testbed conda 环境，使用该环境的 `python`；Moto 应从工作区源码导入。可以核对实际解释器与导入：

```bash
cd /testbed
python -B -c "import sys, moto, boto3, botocore, pytest; print(sys.executable, moto.__file__, boto3.__version__, botocore.__version__, pytest.__version__)"
```

原项目安装入口为 `make init`。Moto 的模拟 AWS 操作使用测试凭据，无需真实 AWS 账户；模拟操作可设置 `AWS_ACCESS_KEY_ID=testing`、`AWS_SECRET_ACCESS_KEY=testing`、`AWS_EC2_METADATA_DISABLED=true` 环境变量。题目的功能要求以原公开 issue 为准。

以下为原公开任务的开发说明，内容保留：

You are a software engineer fixing a real GitHub issue in the repository checked out at /testbed (your bash tool already runs there).
- The project's Python environment is a pre-activated conda env named `testbed`: `python`, `pip` and the repo's test tools already point at it.
- Explore the code, find the root cause, and edit NON-TEST source files to fix the issue.
- Do NOT modify test files: grading resets the test files to their original state before running the official test suite, so test edits never count.
- You may run tests to verify your fix, but keep runs narrow (a single test file or module) to save time.
- When you are confident the fix is complete, reply with a short summary and stop calling tools.
