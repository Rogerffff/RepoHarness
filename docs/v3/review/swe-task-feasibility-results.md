# RepoHarness V3 SWE Task Feasibility Results

## 0. 结果定位

本文记录 RepoHarness V3 前置 SWE 任务可实现性实验的执行结果。本文不是 V3 实现完成声明，也不是 SWE-Bench Lite 榜单结果。

本次实验执行目录：

```text
runs/v3-swe-feasibility-20260502T083722Z/
```

最终结论：

```text
current_v3_entry_status = green_ready_for_v3_implementation_plan
```

这表示：本机 Docker Desktop 内存调整后，官方 SWE-Bench harness、固定 revision 数据快照、Level 1 单任务 gold patch evaluation 和 Level 2 三任务 gold patch evaluation 均已通过。V3 implementation plan 可以使用本次 accepted 的三任务 SWE-Bench-like 小子集作为前置已验证候选集。

这个结论只表示本机可实现性通过，不表示公开 SWE-Bench Lite 榜单结果，也不表示 RepoHarness 已经实现 V3。

## 1. Level 0 环境快照结果

Level 0 初始结果：

```text
level0_environment_snapshot = passed_with_memory_warning
```

初始关键事实：

- Docker Server platform：`linux/arm64`
- Docker architecture：`aarch64`
- Docker Engine：`29.4.1`
- Docker Compose：`v5.1.3`
- Docker context：`desktop-linux`
- Docker 可用 CPU：`18`
- Docker Desktop Linux 虚拟机初始内存：约 `7.748 GiB`
- x86 容器仿真验证：`docker run --rm --platform linux/amd64 alpine:3.20 uname -m` 输出 `x86_64`

初始阻断：

- Docker Desktop Linux 虚拟机内存低于计划要求的至少 `16 GiB`，因此第一次执行时没有启动 Level 1 / Level 2 gold patch evaluation。

内存调整后重新验证：

- Docker Desktop Memory 配置：`18432 MiB`
- 容器内 `/proc/meminfo` 显示：约 `17.537 GiB`
- Docker CPUs：`18`
- Docker architecture：`aarch64`
- 结论：满足 Level 1 / Level 2 的内存门槛。

## 2. Level 0.5 官方 Harness 结果

Level 0.5 结果：

```text
level0_5_harness_setup = passed
```

关键事实：

- 独立虚拟环境已创建在实验目录中。
- 当前 RepoHarness 项目环境未被用于安装 `swebench` 或 `datasets`。
- 官方 SWE-Bench 已克隆并以 editable 方式安装。
- SWE-Bench commit：`f7bbbb2ccdf479001d6467c9e34af59e44a840f9`
- Python 版本：`Python 3.12.13`
- `datasets` 导入检查：通过。
- `swebench` 导入检查：通过。
- `run_evaluation --help` 包含必需参数：`--instance_ids`、`--predictions_path`、`--max_workers`、`--run_id`、`--timeout`、`--cache_level`、`--clean`、`--report_dir`。

判断：

- 官方 harness 安装和版本固定门槛通过。
- 后续 V3 计划应记录该 commit，但不应把本实验结果称为官方榜单结果。

## 3. 固定 Revision 数据快照结果

数据集结果：

```text
dataset_snapshot = passed
```

关键事实：

- Dataset name：`princeton-nlp/SWE-bench_Lite`
- Split：`test`
- Dataset revision：`6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2`
- Row count：`300`
- 候选任务数量：`5`
- 候选任务字段检查：`repo`、`base_commit`、`patch`、`test_patch`、`problem_statement`、`FAIL_TO_PASS`、`PASS_TO_PASS` 均非空。

候选池：

- `sympy__sympy-24909`
- `sympy__sympy-22005`
- `sympy__sympy-15678`
- `pytest-dev__pytest-7220`
- `pytest-dev__pytest-8365`

已生成固定 revision 的本地 JSONL 快照：

- `runs/v3-swe-feasibility-20260502T083722Z/dataset/swebench_lite_fixed_revision_candidates.jsonl`
- `runs/v3-swe-feasibility-20260502T083722Z/dataset/level1_dataset.jsonl`
- `runs/v3-swe-feasibility-20260502T083722Z/dataset/level2_dataset.jsonl`

已生成 gold patch prediction 文件：

- `runs/v3-swe-feasibility-20260502T083722Z/level1/gold_patch_prediction.jsonl`
- `runs/v3-swe-feasibility-20260502T083722Z/level2/gold_patch_predictions.jsonl`

判断：

- evaluation 使用的是固定 revision 生成的本地 JSONL 快照，不是浮动 Hugging Face 默认分支。
- prediction 文件来自同一个本地快照。

## 4. Level 1 单任务 Gold Patch Evaluation

Level 1 任务：

```text
pytest-dev__pytest-7220
```

Level 1 命令要点：

- `--dataset_name runs/v3-swe-feasibility-20260502T083722Z/dataset/level1_dataset.jsonl`
- `--predictions_path runs/v3-swe-feasibility-20260502T083722Z/level1/gold_patch_prediction.jsonl`
- `--instance_ids pytest-dev__pytest-7220`
- `--max_workers 1`
- `--timeout 1800`
- `--cache_level env`
- `--clean True`

Level 1 结果：

```text
level1_infrastructure_completed = true
level1_gold_patch_resolved = true
status = accepted_gold_patch_resolved
```

官方报告：

```text
runs/v3-swe-feasibility-20260502T083722Z/level1/gold_patch_feasibility_probe.v3_swe_feasibility_level1_20260502T085010Z.json
```

报告摘要：

- Total instances：`1`
- Instances submitted：`1`
- Instances completed：`1`
- Instances resolved：`1`
- Instances unresolved：`0`
- Instances with errors：`0`

观察到的运行时间：约 `299` 秒。

## 5. Level 2 三任务 Gold Patch Evaluation

Level 2 任务：

- `pytest-dev__pytest-7220`
- `pytest-dev__pytest-8365`
- `sympy__sympy-24909`

Level 2 命令要点：

- `--dataset_name runs/v3-swe-feasibility-20260502T083722Z/dataset/level2_dataset.jsonl`
- `--predictions_path runs/v3-swe-feasibility-20260502T083722Z/level2/gold_patch_predictions.jsonl`
- `--instance_ids pytest-dev__pytest-7220 pytest-dev__pytest-8365 sympy__sympy-24909`
- `--max_workers 1`
- `--timeout 1800`
- `--cache_level env`
- `--clean True`

Level 2 结果：

```text
level2_infrastructure_completed = true
level2_accepted_count = 3
level2_gold_patch_all_resolved = true
```

官方报告：

```text
runs/v3-swe-feasibility-20260502T083722Z/level2/gold_patch_feasibility_probe.v3_swe_feasibility_level2_20260502T085558Z.json
```

报告摘要：

- Total instances：`3`
- Instances submitted：`3`
- Instances completed：`3`
- Instances resolved：`3`
- Instances unresolved：`0`
- Instances with errors：`0`

观察到的总运行时间：约 `634` 秒。

Accepted task 清单：

| Instance ID | Repo | Base Commit | Status |
| --- | --- | --- | --- |
| `pytest-dev__pytest-7220` | `pytest-dev/pytest` | `56bf819c2f4eaf8b36bd8c42c06bb59d5a3bfc0f` | `accepted_gold_patch_resolved` |
| `pytest-dev__pytest-8365` | `pytest-dev/pytest` | `4964b468c83c06971eb743fbc57cc404f760c573` | `accepted_gold_patch_resolved` |
| `sympy__sympy-24909` | `sympy/sympy` | `d3b4158dea271485e3daa11bf82e69b8dab348ce` | `accepted_gold_patch_resolved` |

## 6. V3 进入条件判定

### 6.1 Green 判定

Green 满足。

满足条件：

- Docker Desktop 内存已经高于 `16 GiB`。
- Level 1 至少 1 个任务 gold patch resolved。
- Level 2 至少 3 个任务 gold patch resolved。
- 每个 accepted 任务都有固定 revision 数据、test patch、FAIL_TO_PASS / PASS_TO_PASS、Docker 运行日志和官方报告。
- 失败任务数量为 0。

### 6.2 Yellow 判定

Yellow 不需要。

原因：

- 已经有 3 个 SWE-Bench Lite 任务通过，不需要公开 issue-style 替代任务。

### 6.3 Red 判定

Red 不满足。

原因：

- 官方 harness 可安装、可运行。
- 固定 revision 数据快照可用。
- Gold patch evaluation 能完成并 resolved。

## 7. 当前完整 V3 进入条件

当前 V3 implementation plan 可以使用以下进入条件：

1. Docker 后端实验基础可行：Apple Silicon / `linux/arm64` Docker Desktop 在 18 GiB 配置下可以运行官方 SWE-Bench harness 的三任务 gold patch evaluation。
2. 官方 harness 版本固定：SWE-Bench commit `f7bbbb2ccdf479001d6467c9e34af59e44a840f9`。
3. 数据集 revision 固定：`princeton-nlp/SWE-bench_Lite` commit `6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2`。
4. 首批 SWE-Bench-like 小子集候选任务：
   - `pytest-dev__pytest-7220`
   - `pytest-dev__pytest-8365`
   - `sympy__sympy-24909`
5. V3 可以进入 implementation planning，但必须继续保持保守表述：这是本机小子集可实现性实验，不是 SWE-Bench Lite 榜单复现。

## 8. 后续建议

进入 V3 implementation plan 时，建议直接把这 3 个任务作为首批候选，并要求 RepoHarness V3 自己的 Docker backend、task adapter、source facts、test patch facts、container execution facts 和 final verifier evidence 对齐本次实验中已经证明可运行的任务。

如果后续要扩大任务集，可以从已验证字段完整但尚未 gold patch evaluation 的两个候选开始：

- `sympy__sympy-22005`
- `sympy__sympy-15678`

但它们不能在当前文档中算作已通过任务，只能算作待验证候选。

## 9. 结论

最终状态：

```text
green_ready_for_v3_implementation_plan
```

V3 可以进入 implementation plan。最小完成定义中的 SWE-Bench-like 小子集可以使用本次通过的 3 个任务作为起点，但所有公开表述仍必须写成 “SWE-Bench-like small subset adapter”，不能写成完整 SWE-Bench Lite 复现或公开榜单可比结果。
