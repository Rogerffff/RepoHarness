# Stage 01: Project Scaffold And CLI Placeholders

## Scope

本阶段实现了：

- 更新 `pyproject.toml`，加入 Pydantic v2、PyYAML、pytest、`repo-harness` 命令行入口和基础 pytest 配置。
- 创建第一版计划中的 Python 模块目录和 `__init__.py`。
- 创建 `src/repo_harness/cli/main.py`，提供空命令行入口和帮助信息。
- 创建统一异常基类和常见业务异常类型。
- 增加一个最小 CLI 单元测试，确认不带子命令时会展示帮助。

本阶段明确不实现：

- 不加载任务定义。
- 不创建工作区。
- 不运行 verifier。
- 不执行工具或模型循环。
- 不实现训练导出。

## Design References

- `docs/v1/implementation-plan.md`
- `docs/11-object-model-config-and-data-flow.md`
- `docs/02-system-architecture.md`
- `docs/v1/implementation-log/README.md`

## Files Changed

- `pyproject.toml`
- `src/repo_harness/__init__.py`
- `src/repo_harness/errors.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/*/__init__.py`
- `tests/test_cli_stage01.py`

## Verification

运行的命令：

```bash
PATH=.venv/bin:$PATH python -m repo_harness.cli.main --help
PATH=.venv/bin:$PATH repo-harness --help
PATH=.venv/bin:$PATH python -m pytest
```

结果：

- 通过。
- 两种命令行调用都能显示帮助。
- pytest 收集并通过 1 个测试。

补充说明：

- 当前系统 Python 是外部管理环境，直接 `python -m pip install -e '.[dev]'` 被拒绝。本阶段使用项目内 `.venv` 安装依赖，并通过 `PATH=.venv/bin:$PATH` 执行文档要求的命令形态。

## Review

审查方式：

- 主实现 agent 自查。
- sub agent 只读审查。

关键审查意见：

- Stage 01 实现符合阶段范围，只做工程骨架、依赖声明、模块目录、CLI 空入口、异常基类和最小测试。
- CLI 只解析参数和展示帮助，没有执行工具、解析测试结果或创建 workspace。
- 包导入没有明显副作用，依赖范围只包含第一版需要的 Pydantic、PyYAML 和 pytest。
- `docs/build-your-own/`、`docs/review/07-industrial-agent-harness-design-check.md`、`docs/review/08-pre-implementation-design-readiness-review.md` 仍是未跟踪文件，不能在本阶段误暂存或提交。

处理结果：

- 采纳：补充本阶段审查结论到 implementation log。
- 采纳：后续提交使用显式路径暂存，避免误纳入用户要求不要主动提交的历史文档。

## Known Limitations

- CLI 子命令目前只注册参数和帮助信息，调用具体子命令会得到“尚未在当前阶段实现”的错误。
- 当前阶段只证明包可安装、可导入、可调用，不证明任务、工作区、工具或 verifier 运行能力。

## Commit

- Commit: `stage 01: scaffold package and cli`
- Commit message: `stage 01: scaffold package and cli`
