# 第四组实施计划 A 线补充核查的 CPU 证据

日期：2026-09-15。作者：Claude（A 线）。对象：[实施计划 §5](../impl_plan_20260915.md#5-codex-实施前审查2026-09-15) 的补充核查，结论在[实施计划 §6](../impl_plan_20260915.md#6-a-线-claude-补充核查2026-09-15)。

Codex 的四个探针（[impl_plan_review_20260915/](../impl_plan_review_20260915/README.md)）已在会话临时目录独立复跑，结果与其保存的 stdout / JSON 逐项一致（真实 pytest 探针的 `parsed_status_map`、`num_parsed_tests`、`reference_missing`、`current_grading_fields` 与源码 sha256 全部相同），不重复保存。本目录只放 A 线新增的探针。

| 探针 | 观察到的结果 | 适用边界 |
| --- | --- | --- |
| [file_to_dir_formal_chain_probe.py](file_to_dir_formal_chain_probe.py) / [stdout](file_to_dir_formal_chain_probe.stdout.txt) | fa_formal 正式链（`rh2/tests/adapters` 的 rollout 替身 + 真实 `SWEGradingManager`）：基线普通文件 `config` → post 只有 `config/default.json`，以及反向，两例都在 `assemble` 段以 pydantic `ValidationError`（`父子前缀冲突`）升 `rh2_contract_validation_failed` run-fatal，无 Outcome、不评分；对照组（只改 `config` 内容）正常 completed。 | 基线 census 与 post census 都是罐头（同 W3a 测试），不运行 Docker。证明的是编排对该异常的收口，不是某道题已出现该形状。断言钉住的是修复前行为，修复后应改为断言新通道。 |

复核命令（仓库根）：

```bash
PYTHONDONTWRITEBYTECODE=1 rh2/.venv/bin/python -m pytest -q -s -p no:cacheprovider \
  docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch4_scoring_20260910/impl_plan_a_line_probes_20260915/file_to_dir_formal_chain_probe.py
```
