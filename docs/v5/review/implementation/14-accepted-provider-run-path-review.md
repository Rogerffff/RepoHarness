# V5 accepted provider run path 审查记录

## 审查范围

本轮审查覆盖真实 provider accepted run 的新增执行路径和导出防线：

- `src/repo_harness/cli/main.py`
- `src/repo_harness/v5_run_matrix.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/v5_export_pack.py`
- `src/repo_harness/v5_demo_artifacts.py`
- `tests/unit/test_v5_run_matrix.py`
- `tests/unit/test_v5_export_pack.py`

审查目标是确认失败运行不会进入 trainable export，accepted result 的 final verifier boundary 和 result payload 可由 inspect 复核，且命令不会覆盖既有 evidence。

## 审查方式

- 子代理只读审查：检查 accepted-run runner、inspect gate、Stage 4 export predicate 和泄漏风险。
- 本地复核：运行 V5 相关单元测试和 `git diff --check`。

## 发现与处理

### P1：hidden test patch failure can still be accepted

发现：accepted 判定只检查 baseline verifier 失败、final verifier 退出码为 0、补丁非空和 provider call 数量，没有要求 baseline 和 final 的 evaluator-only 测试补丁应用成功。

处理：accepted 判定新增 `baseline_hidden_patch_apply_ok` 和 `final_hidden_patch_apply_ok`，两者都必须成功。boundary 记录两个布尔字段和对应 command result。

结论：已修复。

### P2：inspect does not verify final verifier result payload

发现：`inspect-v5-run-matrix` 对 accepted result 只校验 boundary 的浅层字段，没有读取 final verifier result payload。

处理：accepted result 必须绑定 `final_verifier_result_ref`，并要求 result payload 满足 `accepted=true`、`exit_code=0`、`timed_out=false`。boundary 内部的 `final_verifier_result_ref` 也会被复核。

结论：已修复。

### P2：export trusts shallow accepted flags

发现：Stage 4 trainable 过滤只看顶层 `accepted=true` 和 `final_verifier_status=accepted`，如果上游没有先严格 inspect，存在浅层字段伪造风险。

处理：Stage 4 export pack 增加严格 accepted predicate，要求 final verifier ran、strict replay mode、非空 final patch ref、boundary 完整、hidden patch apply 成功、final verifier result 完整。

结论：已修复。

### P2：accepted result 未严格要求 timed_out=false

发现：final verifier result 使用 `timed_out is not True`，会把字段缺失或 `null` 当作可接受结果。

处理：`inspect-v5-run-matrix` 和 Stage 4 export predicate 都改为严格要求 `timed_out` 字段存在且值为 `false`。测试覆盖 `timed_out` 缺失、`timed_out=true` 和 `exit_code` 非 0 的负例。

结论：已修复。

### P3：failure dataset 和分区说明文字过于固定

发现：strict final verifier replay 已运行但失败时，failure dataset 仍可能写成 final verifier 未执行；有 trainable record 时，分区说明仍可能保留“没有 trainable records”的旧口径。

处理：failure dataset 根据 `final_verifier_ran` 区分 `final_verifier_rejected` 和 `final_verifier_not_executed`；partition summary 根据 trainable record 数量动态写入说明。

结论：已修复。

## 验证命令和结果

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_v5_run_matrix.py tests/unit/test_v5_export_pack.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_v5_*.py
git diff --check -- src/repo_harness/v5_run_matrix.py src/repo_harness/v5_evidence.py src/repo_harness/v5_export_pack.py src/repo_harness/v5_demo_artifacts.py src/repo_harness/cli/main.py tests/unit/test_v5_run_matrix.py tests/unit/test_v5_export_pack.py
```

结果：

- `compileall src`：通过。
- targeted V5 run matrix / export pack tests：11 passed。
- 全部 V5 单元测试：66 passed。
- V5 相关路径 diff check：通过。

## 进入下一步结论

当前没有未修复的 P1 或 P2。可以进入 DeepSeek V4 Flash 链路烟测和 DeepSeek V4 Pro 正式 accepted 尝试。若 provider 或 verifier 未通过，应生成 blocked evidence，不得生成 trainable SFT 或 reinforcement learning rollout records。
