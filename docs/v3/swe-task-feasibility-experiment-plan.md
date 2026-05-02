# RepoHarness V3 SWE Task Feasibility Experiment Plan

## 0. 文档定位

本文定义进入 RepoHarness 第三版实现前必须先完成的小规模 SWE 任务数据本机可实现性实验。本文不是第三版实现计划，不实现 RepoHarness V3 代码，也不评测模型能力。

这个实验的唯一目标是提前回答一个具体问题：

> 在当前 Apple Silicon + Docker Desktop 环境中，RepoHarness V3 准备使用的 SWE-Bench-like 任务数据，是否可以被稳定读取、构建、checkout、应用官方 gold patch，并通过 Docker 化 verifier 路径运行测试？

如果这个问题没有先回答，第三版直接把 SWE-Bench-like 小子集写进最小完成定义会有执行风险。尤其是当前 Docker 后端是 `linux/arm64`，而 SWE-Bench 官方资料推荐 `x86_64`，并把 `arm64` 支持标为 experimental，因此必须先做小规模探针。

## 1. 已知本机环境事实

当前轻量预检查已经得到以下事实：

- Docker Server platform 是 `linux/arm64`。
- Docker Engine 是 `29.4.1`。
- Docker Desktop 是 `4.71.0`。
- Docker context 是 `desktop-linux`。
- Docker Compose 是 `5.1.3`。
- Docker 可用 CPU 是 `18` 核。
- Docker Desktop 当前分配给 Linux 虚拟机的内存约 `8.3GB`，低于 SWE-Bench 官方建议的 `16GB`。
- 宿主机磁盘剩余约 `663GiB`，短期做 1 到 3 个任务实验足够。
- `docker run --rm --platform linux/amd64 alpine:3.20 uname -m` 已成功输出 `x86_64`，说明本机可以走 x86 容器仿真路径。
- Hugging Face 上 `princeton-nlp/SWE-bench_Lite` 当前可读取，字段包含 `repo`、`base_commit`、`patch`、`test_patch`、`FAIL_TO_PASS`、`PASS_TO_PASS` 等，`test` split 是 300 条，`dev` split 是 23 条。

这些事实说明：硬件能力本身足够，数据读取路径可用，x86 容器仿真路径可用；但 Docker Desktop 内存配置和 `arm64` 平台仍然是主要风险。

## 2. 实验原则

本实验必须遵守以下原则：

- 先验证基础设施，不测模型能力。
- 先使用官方 gold patch，不使用模型生成 patch。
- 先使用官方 SWE-Bench harness，不先实现 RepoHarness V3 adapter。
- 使用独立实验虚拟环境，不使用当前 RepoHarness 项目环境。当前项目环境不能假设已经安装 `swebench` 或 `datasets`。
- 官方 SWE-Bench harness 必须固定来源和版本，不能由执行者自由安装一个不可追溯版本。
- 先固定 `max_workers = 1`，避免并行构建把内存、磁盘和日志问题混在一起。
- 每个候选任务都必须记录 instance id、repo、base commit、test patch hash、FAIL_TO_PASS、PASS_TO_PASS、运行平台、镜像构建方式、运行日志和最终结果。
- 实验结果只用于 RepoHarness V3 的任务选择和可实现性判断，不作为 SWE-Bench Lite 榜单结果。

## 3. 非目标

本实验明确不做以下事项：

- 不跑完整 SWE-Bench Lite 300 个 test split 任务。
- 不评测任何真实模型或 agent scaffold。
- 不实现 RepoHarness V3 Docker backend。
- 不实现 RepoHarness V3 SWE-Bench-like adapter。
- 不调优模型 prompt。
- 不声称本机结果可与官方 SWE-Bench Lite 榜单比较。
- 不把失败任务直接归因于模型能力，因为本实验只跑官方 gold patch。

## 4. Docker Desktop 前置配置

进入 Level 1 前，建议先调整 Docker Desktop：

- Memory：至少 `16GB`，建议 `24GB`。
- CPU：`8` 到 `12` 核即可，不需要把 18 核全部给 Docker。
- Disk image limit：至少 `200GB`，建议 `300GB` 以上。
- Rosetta / x86 emulation：保持开启。
- `max_workers`：先固定为 `1`。

如果 Docker Desktop 内存仍保持约 `8.3GB`，本实验可以做数据读取和非常轻量的 dry run，但不应该把 gold patch evaluation 失败直接解释为任务不可用。内存不足时的失败应分类为 `docker_memory_below_recommended`。

## 5. 实验分层

### 5.1 Level 0：已完成的轻量预检查

目标：确认本机具备继续实验的基本条件。

已完成检查：

- Docker server 是 `linux/arm64`。
- Docker Engine 版本与预期一致。
- Docker 可用 CPU 足够。
- 宿主机磁盘空间足够短期实验。
- x86 容器仿真可以运行。
- Hugging Face 数据集可读取，字段完整。

Level 0 结论：通过，但 Docker Desktop 内存配置需要在 Level 1 前调整到至少 `16GB`。

### 5.2 Level 0.5：官方 harness 安装和版本固定

目标：在独立实验目录中创建独立虚拟环境，安装固定版本的官方 SWE-Bench harness，并记录足够的版本证据，避免执行时因为当前项目环境缺少 `swebench` 或 `datasets` 而阻塞，也避免自由安装导致实验不可复现。

建议目录：

```text
runs/v3-swe-feasibility-YYYYMMDDTHHMMSSZ/
  swebench-src/
  .venv/
  setup/
    python_version.txt
    swebench_git_remote.txt
    swebench_git_commit.txt
    install_commands.txt
    pip_freeze.txt
    import_check.txt
    run_evaluation_help.txt
```

建议安装流程：

```bash
RUN_DIR="$(pwd)/runs/v3-swe-feasibility-YYYYMMDDTHHMMSSZ"
mkdir -p "$RUN_DIR/setup"
python3 -m venv "$RUN_DIR/.venv"
"$RUN_DIR/.venv/bin/python" -m pip install --upgrade pip setuptools wheel
git clone https://github.com/SWE-bench/SWE-bench "$RUN_DIR/swebench-src"
cd "$RUN_DIR/swebench-src"
git rev-parse HEAD > "../setup/swebench_git_commit.txt"
git remote -v > "../setup/swebench_git_remote.txt"
{
  echo "python3 -m venv $RUN_DIR/.venv"
  echo "$RUN_DIR/.venv/bin/python -m pip install --upgrade pip setuptools wheel"
  echo "git clone https://github.com/SWE-bench/SWE-bench $RUN_DIR/swebench-src"
  echo "$RUN_DIR/.venv/bin/python -m pip install -e $RUN_DIR/swebench-src"
  echo "$RUN_DIR/.venv/bin/python -m pip install datasets huggingface_hub"
} > "../setup/install_commands.txt"
"../.venv/bin/python" -m pip install -e .
"../.venv/bin/python" -m pip install datasets huggingface_hub
"../.venv/bin/python" --version > "../setup/python_version.txt"
"../.venv/bin/python" -m pip freeze > "../setup/pip_freeze.txt"
"../.venv/bin/python" - <<'PY' > "../setup/import_check.txt"
import datasets
import swebench
print("datasets_import=ok")
print("swebench_import=ok")
PY
"../.venv/bin/python" -m swebench.harness.run_evaluation --help > "../setup/run_evaluation_help.txt"
```

实际执行时可以固定到一个经过人工确认的 SWE-Bench commit，而不是使用 clone 当时的默认分支 HEAD。无论使用哪个 commit，都必须把 commit sha、安装命令、Python 版本、依赖版本和 `run_evaluation --help` 输出写入实验产物。

Level 0.5 通过标准：

- `swebench` 和 `datasets` 可以在实验虚拟环境中导入。
- `python -m swebench.harness.run_evaluation --help` 成功执行。
- help 输出中可以看到 `--instance_ids`、`--predictions_path`、`--max_workers`、`--run_id`、`--timeout`、`--cache_level`、`--clean` 和 `--report_dir`。
- SWE-Bench git remote、commit sha、Python 版本和 `pip freeze` 已记录。

Level 0.5 不通过时，不进入 Level 1。

### 5.3 Level 1：单任务官方 gold patch evaluation

目标：使用官方 SWE-Bench harness 跑通 1 个纯 Python 候选任务的 gold patch evaluation，确认镜像能构建、仓库能 checkout、测试能运行、official evaluator 能产出结果。

建议候选任务优先从下面列表中选择 1 个：

- `pytest-dev__pytest-7220`
- `pytest-dev__pytest-8365`
- `sympy__sympy-24909`
- `sympy__sympy-22005`
- `sympy__sympy-15678`

选择顺序建议：

1. 先选择依赖安装最轻、历史 Python 版本要求最清晰、FAIL_TO_PASS 数量较少的任务。
2. 如果 pytest 任务构建更轻，优先选择 pytest。
3. 如果 pytest 任务因为版本或依赖失败，再尝试 sympy。

Level 1 产物：

- `host_environment.json`
- `docker_environment.json`
- `hf_dataset_schema.json`
- `setup/python_version.txt`
- `setup/swebench_git_commit.txt`
- `setup/pip_freeze.txt`
- `setup/run_evaluation_help.txt`
- `level1_candidate_task.json`
- `gold_patch_prediction.jsonl`
- `official_harness_command.txt`
- `official_harness_stdout.log`
- `official_harness_stderr.log`
- `level1_result.json`
- `level1_decision.md`

Level 1 结论必须拆成两个布尔值，不能把可诊断失败和 gold patch resolved 混在一起：

- `level1_infrastructure_completed`：官方 harness 完成 Docker 构建或拉取、repo checkout、test patch apply、gold patch apply 和测试运行，并产出完整 evaluator result。即使最终 unresolved，只要失败可诊断，也可以为 true。
- `level1_gold_patch_resolved`：最终结果明确显示该 instance 在 gold patch 下 resolved。只有这个字段为 true，才能作为 Green 路径或候选任务 accepted 的证据。

Level 1 基础检查标准：

- 数据集中目标 `instance_id` 可读取。
- `patch`、`test_patch`、`FAIL_TO_PASS`、`PASS_TO_PASS` 均非空，或者 PASS_TO_PASS 为空时有明确官方字段解释和 verifier 记录。
- 官方 gold patch 被写入 prediction 文件。
- 官方 harness 的 `--instance_ids` 参数只包含 Level 1 目标 instance，不能运行完整 test split。
- `level1_result.json` 必须同时记录 `level1_infrastructure_completed` 和 `level1_gold_patch_resolved`。

Level 1 不通过时的处理：

- 如果失败原因是 Docker 内存不足，先调整 Docker Desktop 内存后重试同一任务。
- 如果失败原因是单个任务依赖不可安装，保留日志并换下一个候选任务。
- 如果失败原因是官方 harness 在本机平台无法启动，记录为 `official_harness_platform_blocker`，进入替代路径评估。
- 如果 `level1_infrastructure_completed = true` 但 `level1_gold_patch_resolved = false`，说明基础设施至少跑到了 evaluator 结果阶段，但该任务不能进入 accepted 清单。应保留日志并换下一个候选任务，直到至少一个任务 `level1_gold_patch_resolved = true`，或者候选池耗尽。

### 5.4 Level 2：三任务 SWE-Bench-like 小子集可实现性实验

目标：选择 3 个 SWE-Bench Lite 小任务，确认它们能在本机 Docker 后端上用官方 gold patch 跑通，并作为 RepoHarness V3 的 SWE-Bench-like 小子集候选。

候选池初始建议：

- `sympy__sympy-24909`
- `sympy__sympy-22005`
- `sympy__sympy-15678`
- `pytest-dev__pytest-7220`
- `pytest-dev__pytest-8365`

最终选择不应机械固定为这 5 个。正式实验时必须先扫描 `princeton-nlp/SWE-bench_Lite` 或 `SWE-bench/SWE-bench_Lite` 的 `test` split，确认这些 instance 仍存在、字段完整，并按依赖风险重新排序。

Level 2 每个任务必须记录：

- `dataset_name`
- `dataset_revision`
- `split`
- `instance_id`
- `repo`
- `base_commit`
- `environment_setup_commit`
- `version`
- `problem_statement_sha256`
- `patch_sha256`
- `test_patch_sha256`
- `FAIL_TO_PASS`
- `PASS_TO_PASS`
- `docker_server_platform`
- `requested_container_platform`：普通官方 CLI 路径可以记录为 `official_default`，不能伪造为显式请求了 native `linux/arm64`。
- `actual_container_arch`
- `image_build_mode`
- `cross_arch_emulation_used`
- `max_workers`
- `timeout`
- `created_image_tags`
- `docker_system_df_before_ref`
- `docker_system_df_after_ref`
- `cleanup_actions`
- `build_duration_sec`
- `evaluation_duration_sec`
- `resolved`
- `failure_category`
- `logs_ref`

Level 2 通过标准：

- 至少 3 个候选任务完成官方 gold patch evaluation。
- 至少 3 个任务有完整的 source、test patch、FAIL_TO_PASS / PASS_TO_PASS、Docker platform 和 evaluator result 证据。
- 至少 3 个任务可以被标记为 `v3_candidate_status = accepted`。这里的 accepted 等价于 `accepted_gold_patch_resolved`，不能用 `diagnostic_infrastructure_completed_but_unresolved` 替代。
- 所有 accepted 任务都能说明官方 harness 实际使用的容器架构和本机 Docker server 架构。第一轮实验默认验证官方 harness 的默认平台路径；如果要验证 native `linux/arm64`，必须另行说明使用官方 API、自定义 TestSpec 或修改后的实验脚本。普通 CLI 路径不能假设可以直接切换 native `linux/arm64`。
- 所有失败任务都有结构化失败分类，而不是只记录“失败”。

Level 2 不通过时的处理：

- 如果 5 个候选池中少于 3 个任务通过，可以扩大候选池，但仍优先选择纯 Python、小依赖、测试数量少的任务。
- 如果失败集中在平台相关依赖构建，应先确认官方 harness 实际容器架构。若当前路径是官方默认 x86 容器路径，记录 `official_default_platform_failed`；若后续自定义 native `linux/arm64` 路径失败，记录 `native_arm64_custom_path_failed`。
- 如果 `linux/amd64` 仿真路径也普遍超时，应降低 V3 最小完成定义，不把公开 SWE-bench Lite 任务作为硬门槛，改为公开仓库 issue-style task 加明确 verifier patch 证据。

## 6. 推荐目录和产物布局

建议把实验产物放在 `runs/` 下，不把大型日志和 Docker 构建产物提交进 Git。

建议目录：

```text
runs/v3-swe-feasibility-YYYYMMDDTHHMMSSZ/
  host_environment.json
  docker_environment.json
  docker_system_df_before.txt
  docker_system_df_after.txt
  hf_dataset_schema.json
  dataset/
    swebench_lite_fixed_revision_candidates.jsonl
    swebench_lite_fixed_revision_candidates.sha256
    level1_dataset.jsonl
    level1_dataset.sha256
    level2_dataset.jsonl
    level2_dataset.sha256
  candidate_task_manifest.json
  setup/
    python_version.txt
    swebench_git_remote.txt
    swebench_git_commit.txt
    install_commands.txt
    pip_freeze.txt
    import_check.txt
    run_evaluation_help.txt
  level1/
    level1_candidate_task.json
    gold_patch_prediction.jsonl
    official_harness_command.txt
    official_harness_stdout.log
    official_harness_stderr.log
    actual_report_paths.json
    official_reports/
    logs/
    evaluation_results/
    level1_result.json
    level1_decision.md
  level2/
    selected_task_manifest.json
    gold_patch_predictions.jsonl
    official_harness_command.txt
    official_harness_stdout.log
    official_harness_stderr.log
    actual_report_paths.json
    official_reports/
    logs/
    evaluation_results/
    per_task_results.json
    rejected_task_report.json
    level2_decision.md
  feasibility_decision.md
```

如果需要把实验结论写入仓库文档，只提交简短摘要，例如：

```text
docs/v3/review/swe-task-feasibility-results.md
```

不要把 Docker image、完整 build cache、大型 stdout/stderr 或完整源码归档提交进 Git。

## 7. 建议执行步骤

### 7.1 环境快照

记录以下命令输出：

```bash
docker version
docker info
docker context ls
docker compose version
docker run --rm --platform linux/amd64 alpine:3.20 uname -m
docker system df
df -h
```

把结果整理为 `host_environment.json`、`docker_environment.json` 和 `docker_system_df_before.txt`。

### 7.2 官方 harness 安装检查

必须先完成 Level 0.5 中的独立虚拟环境和官方 SWE-Bench 安装。后续所有命令都必须使用：

```bash
"$RUN_DIR/.venv/bin/python"
```

不能使用当前 RepoHarness 项目的 Python 环境。

执行者必须检查 `setup/run_evaluation_help.txt`。如果 help 输出中缺少 `--instance_ids`、`--predictions_path`、`--max_workers`、`--run_id`、`--timeout`、`--cache_level`、`--clean` 或 `--report_dir`，必须停止实验并记录 `official_harness_cli_contract_mismatch`，不能继续自由改命令。

### 7.3 固定 revision 数据集 schema 和本地快照

读取 `princeton-nlp/SWE-bench_Lite` 或 `SWE-bench/SWE-bench_Lite` 的 `test` split，记录：

- dataset name
- dataset revision
- split
- row count
- column names
- 候选 instance 是否存在
- 候选 instance 的关键字段是否非空

dataset revision 必须使用 Hugging Face dataset repo 的具体 commit sha，而不是只写 `main` 或默认分支。建议用 `huggingface_hub` 记录：

```bash
"$RUN_DIR/.venv/bin/python" - <<'PY'
import hashlib
import json
from pathlib import Path
from datasets import load_dataset
from huggingface_hub import HfApi

run_dir = Path(__import__("os").environ["RUN_DIR"])
dataset_dir = run_dir / "dataset"
dataset_dir.mkdir(parents=True, exist_ok=True)

dataset_name = "princeton-nlp/SWE-bench_Lite"
split = "test"
candidate_ids = [
    "sympy__sympy-24909",
    "sympy__sympy-22005",
    "sympy__sympy-15678",
    "pytest-dev__pytest-7220",
    "pytest-dev__pytest-8365",
]

info = HfApi().dataset_info(dataset_name)
dataset_revision = info.sha
ds = load_dataset(dataset_name, split=split, revision=dataset_revision)
rows = [row for row in ds if row["instance_id"] in set(candidate_ids)]

def sha256_json(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()

candidate_snapshot = dataset_dir / "swebench_lite_fixed_revision_candidates.jsonl"
with candidate_snapshot.open("w", encoding="utf-8") as f:
    for row in rows:
        f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")

snapshot_sha256 = hashlib.sha256(candidate_snapshot.read_bytes()).hexdigest()
(dataset_dir / "swebench_lite_fixed_revision_candidates.sha256").write_text(
    snapshot_sha256 + "  " + candidate_snapshot.name + "\n",
    encoding="utf-8",
)

summary = {
    "dataset_name": dataset_name,
    "dataset_revision": dataset_revision,
    "split": split,
    "row_count": len(ds),
    "columns": list(ds.column_names),
    "candidate_count": len(rows),
    "candidate_instance_ids": [row["instance_id"] for row in rows],
    "candidate_manifest_sha256": sha256_json(rows),
    "candidate_snapshot_path": str(candidate_snapshot),
    "candidate_snapshot_sha256": snapshot_sha256,
    "candidate_field_sha256": {
        row["instance_id"]: {
            key: hashlib.sha256(str(row.get(key, "")).encode("utf-8")).hexdigest()
            for key in [
                "repo",
                "base_commit",
                "patch",
                "test_patch",
                "problem_statement",
                "FAIL_TO_PASS",
                "PASS_TO_PASS",
            ]
        }
        for row in rows
    },
}
(run_dir / "hf_dataset_schema.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
(run_dir / "candidate_task_manifest.json").write_text(
    json.dumps(rows, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
PY
```

同一批候选任务还必须写入 `candidate_task_manifest.json`，并记录 manifest 文件自身的 sha256。后续 Level 1 和 Level 2 只能从这个 manifest 选择任务。

非常重要：官方 harness 的 CLI 没有单独的 dataset revision 参数。为了避免 evaluation 阶段重新读取 Hugging Face 默认分支，Level 1 和 Level 2 必须从上面固定 revision 加载出的本地 JSONL 快照生成自己的本地数据集文件：

- `dataset/level1_dataset.jsonl`
- `dataset/level1_dataset.sha256`
- `dataset/level2_dataset.jsonl`
- `dataset/level2_dataset.sha256`

后续 `--dataset_name` 必须指向这些本地 JSONL 文件路径，不能再传 `princeton-nlp/SWE-bench_Lite` 让官方 harness 重新读取浮动默认分支。prediction 文件也必须从同一个本地 JSONL 快照生成。

必须确认字段至少包含：

- `repo`
- `instance_id`
- `base_commit`
- `patch`
- `test_patch`
- `problem_statement`
- `FAIL_TO_PASS`
- `PASS_TO_PASS`

### 7.4 生成 gold patch predictions

对 Level 1 或 Level 2 选中的任务，把本地固定 revision JSONL 快照中的 `patch` 字段作为 `model_patch` 写入官方 harness 需要的 prediction 文件。prediction 文件必须标记这是 gold patch infrastructure validation，不是模型输出。

Level 1 的 prediction 必须从 `dataset/level1_dataset.jsonl` 生成。Level 2 的 prediction 必须从 `dataset/level2_dataset.jsonl` 生成。不能从 Hugging Face 默认分支重新加载数据后生成 prediction，否则 prediction 和 evaluation dataset 可能不是同一个 revision。

建议字段：

```json
{
  "instance_id": "pytest-dev__pytest-7220",
  "model_name_or_path": "gold_patch_feasibility_probe",
  "model_patch": "<dataset patch field>"
}
```

### 7.5 运行官方 harness

所有官方 harness 命令必须从对应实验子目录执行，例如：

```bash
cd "$RUN_DIR/level1"
```

这样即使官方 harness 仍把部分日志写入相对路径 `logs/` 或 `evaluation_results/`，产物也会留在本次实验目录中，而不是散落到仓库根目录。

官方 harness 文档和源码说明 `run_evaluation` 可以从 Hugging Face Datasets 或本地 `.json` / `.jsonl` 文件加载 SWE-Bench 数据集。本实验必须使用本地 `.jsonl` 快照路径。

Level 1 命令模板：

```bash
"$RUN_DIR/.venv/bin/python" -m swebench.harness.run_evaluation \
  --dataset_name "$RUN_DIR/dataset/level1_dataset.jsonl" \
  --split test \
  --predictions_path "$RUN_DIR/level1/gold_patch_prediction.jsonl" \
  --instance_ids "$INSTANCE_ID" \
  --max_workers 1 \
  --run_id "v3_swe_feasibility_level1_$TIMESTAMP" \
  --timeout 1800 \
  --cache_level env \
  --clean True \
  --report_dir "$RUN_DIR/level1/official_reports" \
  > "$RUN_DIR/level1/official_harness_stdout.log" \
  2> "$RUN_DIR/level1/official_harness_stderr.log"
```

Level 2 命令模板：

```bash
"$RUN_DIR/.venv/bin/python" -m swebench.harness.run_evaluation \
  --dataset_name "$RUN_DIR/dataset/level2_dataset.jsonl" \
  --split test \
  --predictions_path "$RUN_DIR/level2/gold_patch_predictions.jsonl" \
  --instance_ids "$INSTANCE_ID_1" "$INSTANCE_ID_2" "$INSTANCE_ID_3" \
  --max_workers 1 \
  --run_id "v3_swe_feasibility_level2_$TIMESTAMP" \
  --timeout 1800 \
  --cache_level env \
  --clean True \
  --report_dir "$RUN_DIR/level2/official_reports" \
  > "$RUN_DIR/level2/official_harness_stdout.log" \
  2> "$RUN_DIR/level2/official_harness_stderr.log"
```

`--instance_ids` 是强制参数。执行者不得省略它，也不得依赖 predictions 文件间接过滤任务。省略 `--instance_ids` 会有误跑完整 `test` split 的风险，应视为实验计划违规。

`--report_dir` 不是唯一可信的日志位置。不同 SWE-Bench 版本可能仍会把日志写入当前工作目录下的 `logs/` 和 `evaluation_results/`。因此每次运行后必须扫描 `official_reports/`、`logs/`、`evaluation_results/`、stdout 和 stderr，生成 `actual_report_paths.json`，记录真实存在的 result、instance result、run log、build log 和 report 文件路径。不能假设 `official_reports/` 一定完整。

默认 timeout 为 `1800` 秒，即每个 instance 30 分钟。Level 1 每个候选任务最多允许 2 次尝试：第一次正常运行，第二次只允许在明确修复 Docker 内存、网络瞬断或下载中断后重试。Level 2 每个任务最多允许 1 次重试。所有重试必须写入 `attempt`、`retry_reason` 和 `previous_logs_ref`。

本轮实验默认验证官方 harness 的默认平台路径。普通 CLI 不应假设可以直接切换 native `linux/arm64`。执行者必须从日志中记录实际容器架构，例如通过 evaluator 日志、Docker image inspect 或容器内 `uname -m` 证据。若后续要验证 native `linux/arm64`，必须另写实验补充，说明使用官方 API、自定义 TestSpec 或修改后的脚本。

### 7.6 Docker 清理边界

实验前后必须记录：

```bash
docker system df
```

分别写入 `docker_system_df_before.txt` 和 `docker_system_df_after.txt`。

允许的清理：

- 使用官方 harness 的 `--clean True` 清理由本次 evaluation 创建、且高于 `cache_level` 的临时资源。
- 删除本实验明确创建的 prediction 文件副本、临时日志副本或临时容器。
- 删除带有本次 `run_id`、本次 image tag 或本次 namespace 标记的实验资源。

禁止的清理：

- 不得执行无边界的 `docker system prune -a`。
- 不得删除与本实验无关的镜像、volume、builder cache 或容器。
- 不得为了腾空间删除用户已有 Docker 资源，除非用户另行明确批准。

如果磁盘或 Docker image cache 成为阻塞项，实验结果应记录 `docker_storage_cleanup_required`，然后暂停等待人工决策。

### 7.7 结果归类

每个任务必须归类为以下状态之一：

- `accepted_gold_patch_resolved`
- `diagnostic_infrastructure_completed_but_unresolved`
- `rejected_dataset_fields_incomplete`
- `rejected_image_build_failed`
- `rejected_dependency_install_failed`
- `rejected_test_patch_apply_failed`
- `rejected_gold_patch_apply_failed`
- `rejected_timeout`
- `rejected_platform_incompatible`
- `rejected_docker_memory_below_recommended`
- `rejected_harness_error`

其中只有 `accepted_gold_patch_resolved` 可以进入 V3 SWE-Bench-like 小子集首选清单。`diagnostic_infrastructure_completed_but_unresolved` 只能证明官方 harness 和本机基础设施跑到了 evaluator 结果阶段，不能作为候选任务 accepted 证据。所有 `rejected_*` 状态只能作为诊断材料。

## 8. V3 进入条件

完成本实验后，按以下规则决定是否进入 V3 实施计划。

### 8.1 Green：可以进入 V3

满足全部条件：

- Docker Desktop 内存已经调整到至少 `16GB`，建议 `24GB`。
- Level 1 至少 1 个任务 gold patch resolved。
- Level 2 至少 3 个任务 gold patch resolved。
- 每个 accepted 任务都有完整 metadata、test patch hash、FAIL_TO_PASS、PASS_TO_PASS、Docker platform 和日志引用。
- 失败任务有结构化 failure category。

### 8.2 Yellow：可以进入 V3，但必须降风险

满足以下任一情况：

- 只有 2 个 SWE-Bench Lite 任务通过，但第 3 个可以用有同等测试证据的公开 issue-style task 替代。
- 任务只能通过 `linux/amd64` 仿真路径运行，native `linux/arm64` 不稳定。
- 单任务运行时间明显较长，但仍能在固定 timeout 内完成。

Yellow 状态进入 V3 时，实施计划必须把平台限制写成风险，并把 SWE-Bench-like 小子集目标写成 “2 到 3 个公开 Lite 任务 + 最多 1 个同等测试证据替代任务”。

“同等测试证据替代任务”必须同时满足以下最低条件：

- 来自公开仓库固定 commit 或预下载公开归档。
- 记录 remote URL、base commit、archive sha256 或 source tree hash。
- 有明确 issue statement 或 problem statement。
- 有 verifier patch 或 test patch。
- 有 baseline failing evidence，证明任务初始状态会失败。
- 有 gold patch passing evidence，证明参考修复后会通过。
- 有 fail-to-pass / pass-to-pass 列表，或者有等价的测试命令分组和解析规则。
- 有 Docker execution logs、timeout、平台和依赖安装记录。

不满足这些条件的本地 fixture 不能作为 Yellow 替代任务。

### 8.3 Red：不应进入 V3 SWE-Bench-like 实现

满足以下任一情况：

- Docker Desktop 内存不能调整到至少 `16GB`。
- Level 1 无法跑通任何 gold patch evaluation。
- 官方 harness 在本机平台无法稳定启动。
- 3 个候选任务全部因为平台、依赖或镜像构建失败而不可用。

Red 状态下，V3 应先只做 Docker backend、真实公开仓库固定 commit 任务和 RepoHarness 自有 verifier patch issue-style task，不应把 SWE-Bench Lite 小子集作为最小完成硬门槛。

## 9. 后续文档更新

实验完成后，应更新或新增：

- `docs/v3/review/swe-task-feasibility-results.md`：记录 Level 1 / Level 2 结果、accepted task 清单和失败分类。
- `docs/v3/scope-and-roadmap.md`：如果实验结果改变 V3 最小完成定义，需要同步修改范围口径。
- 后续 `docs/v3/implementation-plan.md`：只能使用实验 accepted 的任务作为首批 SWE-Bench-like 小子集。

## 10. 参考资料

- SWE-Bench GitHub README：`https://github.com/SWE-bench/SWE-bench`
- SWE-Bench Evaluation Guide：`https://www.swebench.com/SWE-bench/guides/evaluation/`
- SWE-Bench Lite 官方介绍：`https://www.swebench.com/lite.html`
- Hugging Face dataset：`https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite`

这些资料只用于选择实验路径和记录风险。RepoHarness V3 仍然只应声明 “SWE-Bench-like small subset adapter”，不能声明完整 SWE-Bench Lite 复现或公开榜单可比结果。
