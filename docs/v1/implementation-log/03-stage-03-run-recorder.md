# Stage 03: RunRecorder And Artifact Manifest

## Scope

本阶段实现了：

- `RunRecorder`，提供 `append_transcript()`、`append_event()`、`write_artifact()`、`write_json_artifact()`、`finalize_run()` 和 `mark_interrupted()`。
- run directory 初始化，包含 `events.jsonl`、`transcript.jsonl`、`artifacts.json`、`run_status.json`、`summary.md` 和 `artifacts/`。
- `run.lock` 独占写锁，防止两个 writer 同时写入同一个 run directory。
- 稳定递增的 event、record 和 artifact id。
- artifact 临时文件写入、sha256 和 size 计算、相对路径 manifest 写入。
- JSONL 读取 helper、artifact manifest 校验 helper。
- 最小 `inspect-run` 只读能力，可以读取运行中、已 finalize 或 interrupted 的目录，并报告 metrics 或 summary 缺失状态。
- `repo-harness inspect-run <run_dir>` CLI 路由。

本阶段明确不实现：

- 不实现任务加载。
- 不实现 workspace 生命周期。
- 不运行 verifier。
- 不执行工具。
- 不生成 metrics、reward 或 final patch。

## Design References

- `docs/v1/implementation-plan.md`
- `docs/11-object-model-config-and-data-flow.md`
- `docs/08-trajectory-store-and-training-export.md`
- `docs/02-system-architecture.md`

## Files Changed

- `src/repo_harness/trajectory/recorder.py`
- `src/repo_harness/trajectory/inspect.py`
- `src/repo_harness/trajectory/__init__.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_run_recorder.py`

## Verification

运行的命令：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_run_recorder.py
PATH=.venv/bin:$PATH python -m pytest
PATH=.venv/bin:$PATH python -m compileall src
```

结果：

- 通过。
- `tests/unit/test_run_recorder.py` 收集并通过 8 个测试。
- 全量测试收集并通过 27 个测试。
- `compileall` 通过。

## Review

审查方式：

- 主实现 agent 自查。
- sub agent 只读审查。

关键审查意见：

- `FINALIZED` run directory 在关闭 writer 后可以被新的 `RunRecorder` 重新打开并追加事实记录，削弱审计不可变性。
- artifact manifest 校验不能信任被篡改的 `relative_path`，需要拒绝绝对路径、`..` 和逃逸 run directory 的路径。
- `inspect-run` 面对损坏的 JSONL、manifest 或 status 文件时不应崩溃，应报告 `CORRUPT_PARTIAL`。
- 重复 finalize、缺失 summary、JSONL 每行合法性、损坏 JSONL/manifest 的测试需要更明确。

处理结果：

- 采纳：`RunRecorder` 初始化时拒绝重新打开 `FINALIZED` run directory。
- 采纳：`finalize_run()` 只允许相同 summary 的幂等重复调用；不同 summary 或状态改写会抛出 `RunRecorderError`。
- 采纳：`verify_artifact_manifest()` 拒绝绝对路径、`..`、逃逸 run directory 的路径，并要求 artifact 位于 `artifacts/` 下。
- 采纳：`inspect-run` 捕获损坏 JSONL、manifest 和 status 文件，返回 `CORRUPT_PARTIAL` 摘要而不是崩溃。
- 采纳：新增测试覆盖 JSONL 每行合法 JSON、不同 summary 重复 finalize 拒绝、finalized run 重新打开拒绝、缺失 summary 报告、unsafe manifest 路径拒绝、损坏半成品目录检查。

## Known Limitations

- `RunRecorder` 当前使用 `run.lock` 文件作为本地单进程写锁；第一版批量并发默认为 1，后续如果支持多进程并发，需要进一步明确锁清理和崩溃恢复策略。
- `finalize_run()` 会重写 `summary.md` 和 `run_status.json`，但不会改写历史 events 或 transcript。
- `inspect-run` 当前只读展示核心摘要和 artifact manifest 校验结果；更详细的 metrics、reward、verifier 展示会在后续阶段补齐。
- artifact redaction 目前只记录 `redaction_status` 字段，不执行 secret scan。

## Commit

- Commit: `stage 03: implement run recorder and artifact manifest`
- Commit message: `stage 03: implement run recorder and artifact manifest`
