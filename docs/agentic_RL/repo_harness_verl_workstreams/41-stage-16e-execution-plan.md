# Stage 16E 执行计划：patch hygiene 和训练目标清洁度

## 1. 阶段定位

Stage 16E 的目标是把模型最终补丁和训练目标里的诊断残留清理成可训练、可审计、可复用的形式。

前面阶段已经完成了下面这些基础能力：

- Stage 16A：`execute_bash` 被收紧成安全最小 shell 子集。
- Stage 16B：`diagnostic_shell` 有持久会话、projection workspace、Docker 后端和训练资格门闸。
- Stage 16B.5：远端 Docker-capable 训练后端已经通过 smoke。
- Stage 16C：模型可见的公开环境入口和公开测试提示已经有 visibility gate。
- Stage 16D / Stage 16D.1：official verifier、gold patch 和 no-op healthcheck 的合同和小样本真实 smoke 已经建立。

Stage 16E 不继续扩大工具权限，也不重新证明 official harness 能运行。它专门解决一个问题：

```text
模型或 diagnostic shell 可能在仓库里留下 patch.txt、*.orig、*.rej、临时复现脚本、依赖目录、
缓存目录或其它诊断产物。它们可以作为 runtime-private 诊断事实保留，但不能污染 final.patch、
SFT target、RL reward evidence、preference pair 或 official prediction。
```

这一阶段完成后，后续 Stage 16.5 才适合扩大到 20 到 30 题代表性 harness 诊断。否则代表性诊断会把补丁噪声、测试入口噪声和训练目标污染混在一起，难以判断是真实模型能力问题还是 harness 问题。

## 2. 非目标

Stage 16E 不做下面这些事情：

- 不训练模型。
- 不扩大 `execute_bash` allowlist。
- 不扩大 `diagnostic_shell` 权限。
- 不实现新的 persistent diagnostic session 后端。
- 不重新运行 Stage 16D.1 的 official SWE-Bench smoke。
- 不实现 Stage 16.5 的 20 到 30 题代表性诊断。
- 不把所有 test-like 文件改动无条件删除。test-like 文件变更需要按 task policy 分类，不能用一个全局规则误删合法任务。
- 不把 raw patch、raw diff、gold patch、test patch、official result 或 hidden selector 放入公开 evidence。

## 3. 前置条件

进入 Stage 16E 前必须满足：

```text
Stage 16A 提交存在。
Stage 16B 提交存在。
Stage 16B.5 提交存在。
Stage 16C 提交存在。
Stage 16D.0 提交存在。
Stage 16D 提交存在。
Stage 16D.1 提交存在，当前基线至少包含 5457b3f3。
Stage 16D.1 的 official result artifact kind 绑定修复已经提交：
gold_official_result_ref 和 noop_official_result_ref 必须都是
runtime-private:official-result:<sha256>，不能只校验 sha256 而忽略 artifact kind。
```

如果当前工作区仍有 Stage 16D.1 未提交文件，必须先停止并整理 Stage 16D.1。Stage 16E 提交不能混入既有未跟踪 HTML、训练设计资料、平台凭证文档、`vastai_cli.md`、`pyrightconfig.json` 或其它和 patch hygiene 无关的文件。

本阶段开始前建议跑：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_stage16d_healthcheck_schema.py \
  tests/unit/test_stage16d_healthcheck_builder.py \
  tests/unit/test_stage16d_healthcheck_acceptance.py \
  tests/unit/test_pre_verl_swebench_official_inputs.py

PATH=.venv/bin:$PATH python -m compileall -q src scripts/pre_verl
```

## 4. 当前问题

当前代码已经有一部分补丁清洁能力，但它们分散在不同位置：

- `LocalWorkspaceAdapter.capture_final_patch(...)` 直接用 `git diff --binary <base>` 写出 `final.patch`。
- `DockerWorkspaceAdapter.capture_final_patch(...)` 也直接用 `git diff --binary <base>` 写出 `final.patch`。
- `scripts/pre_verl/build_swebench_official_inputs.py` 会剥离部分 test-like 文件、`patch.txt`、`*.orig`、`*.rej` 和根目录诊断脚本。
- export audit 能检查训练导出是否含隐藏字段或本机路径，但还没有统一理解 patch hygiene 的过滤事实。

这会留下几个风险：

1. `final.patch` 可能包含诊断残留文件。
2. official prediction builder 的过滤规则和最终补丁捕获规则可能不一致。
3. SFT / RL / preference export 只能看到最终 run 事实，不能机器化确认训练目标是否来自清洁补丁。
4. 只有诊断文件变更的 episode 可能被误判成“有 patch”，从而污染训练目标。
5. 过滤掉的文件缺少统一审计报告，后续无法判断是模型行为问题、工具提示问题还是 harness 过滤问题。

Stage 16E 必须把这些规则收敛成一个统一、可测试、可审计的 policy。

## 5. 设计原则

### 5.1 只过滤补丁，不静默修改 workspace

Stage 16E 第一版应优先过滤最终补丁和训练导出，而不是在模型 workspace 中偷偷删除文件。

```text
模型 workspace 可以保留诊断文件，方便 debug。
final.patch / final.diff / official prediction / training target 必须使用 cleaned patch projection。
被过滤内容写入 runtime-private 或 audit-only hygiene report，不进入模型可见上下文和训练样本。
```

如果后续阶段需要自动清理 workspace，可以单独设计；Stage 16E 的核心是“训练目标清洁”，不是“替模型整理目录”。

### 5.2 统一 policy，避免多处规则漂移

新增统一模块，例如：

```text
src/repo_harness/patch_hygiene.py
```

或者放在 workspace 边界下：

```text
src/repo_harness/workspace/patch_hygiene.py
```

执行 agent 应优先选择和现有 workspace ownership 更贴近的路径。建议第一版放在 `src/repo_harness/workspace/patch_hygiene.py`，因为它直接服务 `capture_final_patch(...)`、workspace adapter 和 Docker adapter。

统一模块至少提供：

```text
PatchHygienePolicy
PatchHygieneDecision
PatchHygieneReport
classify_patch_path(path, policy)
filter_patch_text(patch_text, policy)
build_patch_hygiene_report(raw_patch, cleaned_patch, decisions)
```

`scripts/pre_verl/build_swebench_official_inputs.py` 必须复用同一套路径分类逻辑，不能继续维护完全独立的临时 artifact 判断规则。它可以保留 official prediction 专属的 test-like 文件策略，但底层 temporary / dependency / diagnostic artifact 分类应来自统一 policy。

### 5.3 区分硬过滤、风险标记和任务策略

不是所有可疑改动都应该用同一条规则处理。

建议第一版分成三类：

```text
hard_exclude:
  永远不能进入 final.patch / SFT target / RL reward evidence / preference pair / official prediction。

flag_only:
  不一定删除，但必须写入 hygiene report，供 Stage 16.5 和 Stage 17 判断任务是否适合训练。

task_policy_controlled:
  是否允许取决于任务声明、数据集适配器或 official prediction 模式。
```

第一版 hard exclude 至少包含：

```text
patch.txt
*.orig
*.rej
*.swp
*.swo
*~
.DS_Store
__pycache__/**
*.pyc
.pytest_cache/**
.mypy_cache/**
.ruff_cache/**
.repo_harness_tmp/**
.repo_harness_runtime/**
.repo_harness_env_overlay/**
runtime_private/**
repo-harness-run/**
tmp/**
temp/**
node_modules/**
.venv/**
venv/**
env/**
dist/**
build/**
*.egg-info/**
根目录 debug_*.py
根目录 check_*.py
根目录 probe_*.py
根目录 repro*.py
根目录 reproduce*.py
根目录 tmp_*.py
根目录 *.fit / *.fits / *.fits.gz
```

其中常见嵌套依赖、虚拟环境、构建输出和缓存目录必须显式覆盖任意层级形式。`env`、`build` 这类普通英文名称也可能出现在合法源码路径中，因此第一版采用更具体的例外规则：根目录或非 `src/env/...`、`src/build/...` 的嵌套 `env/`、`venv/`、`dist/`、`build/` 默认视为依赖环境或构建产物并过滤；`src/env/config.py`、`src/build/plugin.py` 这类源码布局路径必须有 false-positive 测试证明不会被误删。后续如果需要放宽其它合法目录名，必须先增加任务环境事实或更精确的路径 provenance，不能只靠目录名全局放行。

第一版至少要覆盖：

```text
**/node_modules/**
**/__pycache__/**
**/.pytest_cache/**
**/.mypy_cache/**
**/.ruff_cache/**
**/.venv/**
**/venv/**
**/env/**
**/dist/**
**/build/**
**/*.egg-info/**
```

hard exclude pattern 的锚定语义必须写进 policy：

```text
没有 `**/` 前缀的目录模式默认按仓库根目录锚定；对于 `env/`、`venv/`、`dist/`、`build/` 这类需要任意层级匹配但又有源码布局例外的目录，必须用专门的分类 helper 表达例外规则，不能只依赖宽泛 glob。
需要任意层级匹配时必须显式写成 `**/node_modules/**`、`**/__pycache__/**` 这类形式，或者在 policy helper 中写明 source-layout 例外。
每个新增 hard-exclude pattern 必须同时有命中测试和 false-positive 测试。
```

这样可以避免把 `src/build.py`、`src/env.py`、`docs/debugging.md` 这类合法源码或文档误删，也可以避免把“任意层级依赖目录”误理解成只匹配仓库根目录。

第一版 flag_only 至少包含：

```text
test-like 文件变更
锁文件变更
项目配置变更
大体积二进制文件变更
```

test-like 文件不要在 generic final.patch 中无条件删除，因为某些内部任务可能要求补测试或改测试 fixture。但是在 SWE-Bench official prediction builder 中，默认仍然应剥离 test-like 文件变更，除非显式传入 `--keep-test-file-changes`。

### 5.4 raw patch 和 cleaned patch 的可见性必须分层

本阶段至少区分：

```text
raw_patch:
  runtime-private 或 audit-only。可以包含模型写出的所有仓库变更。

cleaned_patch:
  用于 final.patch、final.diff、strict patch replay、final verifier、official prediction 和训练导出。

hygiene_report:
  public-safe summary 可以提交；详细路径、raw diff 摘要和内容 hash 根据 visibility 分层处理。
```

公开 evidence 不得包含 raw patch 内容、diff hunk、hidden selector、gold patch、test patch、本机绝对路径或 runtime-private 路径。

## 6. 实施步骤

### Step 1：新增统一 patch hygiene policy

新增模块并实现纯函数级逻辑。

建议文件：

```text
src/repo_harness/workspace/patch_hygiene.py
tests/unit/test_repo_harness_stage16e_patch_hygiene_policy.py
```

核心输入输出：

```python
filtered = filter_patch_text(
    patch_text,
    policy=PatchHygienePolicy.default_training_policy(),
    structured_diff_facts=structured_diff_facts,
)

filtered.cleaned_patch_text
filtered.filtered_paths
filtered.flagged_paths
filtered.decisions
filtered.report
```

`filter_patch_text(...)` 可以保持纯函数，但必须允许调用方传入 `structured_diff_facts`。Local / Docker final patch capture 路径必须提供来自 `git diff --name-status -z`、`git diff --numstat -z` 或等价命令的结构化事实。不能拿到结构化事实，或者结构化事实和 patch block 解析结果不一致时，capture 路径必须 fail closed，不能只依赖 patch 文本解析继续生成 cleaned patch。

要求：

1. 解析 unified diff block，不做基于整段字符串的粗暴替换。
2. 对 `diff --git a/path b/path`、`---`、`+++` 中的路径做一致解析。
3. 路径必须是 repository-relative；绝对路径、`..`、空路径、控制字符路径直接 hard exclude 并写入 `unsafe_patch_path`。
4. 对二进制 diff、rename、delete、new file 都能按目标路径分类。
5. 必须正确处理 Git quoted path、路径中的空格、制表符、转义字符、`/dev/null`、rename path、copy path、delete path 和 new file path。
6. 必须用 `git diff --name-status -z`、`git diff --numstat -z` 或等价结构化路径列表做交叉校验。patch block 解析出的路径集合和结构化路径集合不一致时，必须 fail closed，不能继续生成 cleaned patch。
7. 如果一个 diff block 的 old path 和 new path 任意一边命中 hard exclude，整块过滤。
8. 保留 patch block 顺序，避免改变其它源文件 diff。
9. 生成 stable report，包含过滤数量、原因、路径、raw patch hash、cleaned patch hash，但 public-safe report 不包含 raw hunk 内容。
10. public-safe report 不能无条件公开 raw filtered path。对于安全的 repository-relative path，可以公开 batch-safe normalized path；对于 `unsafe_patch_path`、包含 evaluator-only marker、本机路径、`runtime_private`、hidden selector、`test_patch`、`gold_patch` 或其它敏感片段的路径，只能公开 `path_category`、`path_sha256`、`basename_redacted` 和 `reason`。原始路径只能进入 runtime-private report。

需要覆盖的单元测试：

```text
patch.txt 被过滤。
*.orig / *.rej 被过滤。
根目录 debug_*.py / repro*.py 被过滤。
node_modules/** / .venv/** / __pycache__/** 被过滤。
src/patch.py 不因为名字包含 patch 被过滤。
src/original.py 不因为包含 orig 字符串被过滤。
合法源码改动保留。
混合源码改动和诊断产物时，只保留源码改动。
只有诊断产物改动时，cleaned patch 为空，report 标记 only_filtered_changes=true。
路径穿越、绝对路径和控制字符路径被 hard exclude。
binary diff 指向 hard exclude 路径时被过滤。
Git quoted path、空格路径、rename/copy path 和 /dev/null 路径被正确解析。
patch block 路径和 git diff --name-status -z 路径不一致时 fail closed。
```

### Step 2：接入 LocalWorkspaceAdapter 和 DockerWorkspaceAdapter 的 final patch capture

修改：

```text
src/repo_harness/workspace/adapter.py
src/repo_harness/workspace/docker_adapter.py
```

`capture_final_patch(...)` 当前写出的 `final.patch` 和 `final.diff` 必须改成 cleaned projection。

建议保留下面几类 artifact：

```text
final.patch:
  cleaned patch。用于 final verifier、strict replay、official prediction 和训练。

final.diff:
  cleaned diff。用于公开或训练侧 diff 统计。

final_patch_hygiene_report.json:
  public-safe 或 audit-safe summary，记录过滤计数、原因、路径摘要、cleaned/raw hash。

raw_final_patch:
  runtime-private artifact，不进入模型可见上下文和训练导出。

raw_final_diff:
  runtime-private artifact，不进入模型可见上下文和训练导出。
```

`PatchCapture` 返回对象的 clean/raw 语义必须保持一致：

```text
PatchCapture.patch_text 必须是 cleaned patch。
PatchCapture.diff_text 必须是 cleaned diff。
PatchCapture.patch_artifact_ref 必须指向 cleaned final_patch artifact。
PatchCapture.diff_artifact_ref 必须指向 cleaned final_diff artifact。
raw patch / raw diff 只能通过 raw_final_patch_ref / raw_final_diff_ref 或等价 runtime-private metadata 暴露。
raw patch / raw diff 不能复用 final_patch / final_diff artifact 名称。
```

这条规则是 hard requirement。否则即使 `final.patch` 文件本身已经被清理，后续 `RepoHarnessEpisodeResult`、TrainingView、AgentLoopOutput、DataProto 或 export 仍可能从 `PatchCapture.patch_text` 或 recorder artifact 中读到 raw patch。

如果现有 `RunRecorder.write_artifact(...)` 没有 runtime-private visibility 字段，本阶段至少要在 metadata 中写清：

```json
{
  "visibility": "runtime_private",
  "training_export_allowed": false,
  "model_visible": false
}
```

并在 export / public scan 中拒绝这些 raw artifact 进入训练数据。

`PatchCapture` 或 `patch_stats` 需要加入 hygiene facts，例如：

```text
patch_hygiene_status = passed / filtered / failed
raw_patch_sha256
cleaned_patch_sha256
filtered_file_count
flagged_file_count
only_filtered_changes
filtered_reasons
test_like_modified_files
```

所有默认 patch 统计都必须使用 cleaned projection 口径：

```text
PatchCapture.added_lines
PatchCapture.removed_lines
patch_stats.changed_files
patch_stats.modified_files
patch_stats.binary_files
reward / metrics / export 使用的默认 patch 统计
```

raw patch 统计只能进入 `patch_hygiene.raw_*`、runtime-private report 或等价 audit-only 字段，不能被默认 reward、metrics 或 export 当作模型最终补丁统计。

如果改变 `PatchCapture` schema 风险过高，也可以先通过 `patch_stats["patch_hygiene"]` 承载，但必须有测试证明 `RepoHarnessEpisodeResult`、TrainingView 或 metadata 能看到这些 facts。

### Step 3：保证 final verifier 使用 cleaned patch

`capture_final_patch(...)` 已经发生在 final verifier 之前。Stage 16E 必须保持这个顺序，并证明 final verifier 使用的是 cleaned `final.patch`。

测试要求：

```text
workspace 中同时有 src/app.py 改动和 patch.txt 改动。
capture_final_patch 后 final.patch 只包含 src/app.py。
strict patch replay / final verifier 使用 final.patch 时能应用源码改动。
patch.txt 不进入 verification workspace。
```

如果只有 `patch.txt`、`debug_*.py`、`node_modules/**` 等过滤项发生变化：

```text
final.patch 必须为空或无有效 diff。
run metadata / reward boundary 必须把它归类为 empty_cleaned_patch 或 only_filtered_changes。
该样本不能作为成功正样本进入训练。
```

这不能被误判成“模型没有产生任何行为”；应记录模型产生了诊断残留，但没有产生可训练源码补丁。

### Step 4：接入 official prediction builder

修改：

```text
scripts/pre_verl/build_swebench_official_inputs.py
tests/unit/test_pre_verl_swebench_official_inputs.py
```

要求：

1. 复用 Stage 16E 的统一 temporary / dependency / diagnostic artifact classifier。
2. 保留 official prediction 的 test-like 文件剥离策略。
3. 不能只读取已经清洁过的 `final.patch` 然后重新分类。Stage 16E 后 `final.patch` 本身已经是 cleaned patch，如果 builder 只看它，会丢失 raw patch 曾经被过滤的事实。builder 必须读取并校验 `final_patch_hygiene_report.json`、`patch_stats["patch_hygiene"]` 或等价事实来源。
4. builder 必须校验：

```text
final.patch sha256 == cleaned_patch_sha256
official prediction 使用 cleaned patch
manifest 中投影了原始过滤事实
raw patch 内容没有进入 public manifest
```

5. manifest 中新增或对齐：

```text
patch_hygiene_policy_version
raw_patch_sha256
cleaned_patch_sha256
filtered_file_count
filtered_files
filtered_reasons
flagged_file_count
test_like_modified_files
official_prediction_uses_cleaned_patch = true
```

`filtered_files` 也必须是 public-safe projection：安全的仓库相对路径可以公开；命中 `runtime_private`、hidden marker、本机路径、`test_patch`、`gold_patch` 或其它敏感片段的路径，只能公开 `path_sha256`、`path_category` 和 `reason`，原始路径必须留在 runtime-private report。

6. 如果 exported patch 因为 hard exclude 变空，必须记录：

```text
prediction_exclusion_reason = only_filtered_changes
```

或者等价结构化状态，不能生成一条空 `model_patch` 冒充可评测 prediction。

7. 内容级泄漏扫描继续保留。路径级 hygiene 通过不代表内容一定安全。

### Step 5：接入 TrainingView、AgentLoopOutput 和 export audit

Stage 16E 不需要把 raw patch 内容写进 TrainingView。需要做的是把 batch-safe 的 hygiene facts 投影进去。

建议字段：

```text
repo_harness_patch_hygiene_status
repo_harness_patch_hygiene_policy_version
repo_harness_cleaned_patch_sha256
repo_harness_raw_patch_sha256
repo_harness_filtered_file_count
repo_harness_flagged_file_count
repo_harness_only_filtered_changes
repo_harness_test_like_modified_file_count
```

规则：

```text
raw_patch 内容不能进入 TrainingView。
filtered path 明细默认不进入 TrainingView，除非已经证明是 batch-safe projection。
only_filtered_changes=true 的样本不能进入 policy loss。
patch_hygiene_status=failed 的样本不能进入 policy loss。
patch_hygiene_status=filtered 但 cleaned patch 非空，可以继续进入候选，但必须保留过滤事实。
```

修改点可能包括：

```text
src/repo_harness/rl/episode.py
src/repo_harness/rl/runtime.py
src/repo_harness/rl/training_view.py
src/repo_harness_verl/conversion.py
src/repo_harness/export/audit.py
```

执行 agent 必须先读当前对象流，避免随意新增 schema 字段。如果已有 `patch_summary`、`extra_fields`、`patch_stats` 或 metadata 可以承载 batch-safe facts，应优先复用现有结构。

export audit 必须拒绝：

```text
SFT target 中包含 raw final patch 内容。
RL reward evidence 中包含 filtered file hunk。
preference pair 任一侧来自 patch_hygiene_status=failed 或 only_filtered_changes=true 的样本。
data file 或 manifest 中出现 patch.txt、*.orig、*.rej、node_modules、.venv、runtime_private 等 hard-exclude 路径。
```

### Step 6：新增 Stage 16E inspector 和本地 evidence

新增机器验收命令或脚本。可以二选一：

```text
repo-harness inspect-stage16e-patch-hygiene <evidence_dir> --assert-complete
```

或者：

```text
python scripts/pre_verl/inspect_stage16e_patch_hygiene.py <evidence_dir> --assert-complete
```

建议第一版优先用 `scripts/pre_verl`，如果后续确认为长期入口，再接入 `repo-harness` CLI。

本地 evidence 目录：

```text
runs/repo-harness-verl-stage16e-local-<timestamp>/
```

公开 canonical items：

```text
stage16e_acceptance_summary.json
stage16e_patch_hygiene_policy.json
stage16e_final_patch_hygiene_report.json
stage16e_official_prediction_hygiene_report.json
stage16e_export_hygiene_report.json
stage16e_fixture_manifest.json
stage16e_command_log.sanitized.jsonl
stage16e_public_leak_scan_report.json
stage16e_canonical_evidence_map.json
```

runtime-private items：

```text
runtime_private/raw_patch_cases/
runtime_private/raw_final_patch_samples/
runtime_private/raw_export_samples/
runtime_private/stage16e_command_log.raw.jsonl
```

公开 evidence 不得包含 raw diff hunk、本机绝对路径、`runtime_private` 真实路径、gold patch、test patch、hidden selector、official result 原文。

公开 evidence 允许出现下面这种 opaque ref：

```text
runtime-private:<kind>:<sha256>
```

但必须拒绝下面这些真实路径或准路径：

```text
runtime_private/...
/.../runtime_private/...
本机绝对路径
workspace 真实路径
run directory 真实路径
```

acceptance summary 最少字段：

```json
{
  "schema_version": "repo_harness_stage16e_acceptance_summary_v0",
  "stage": "16E",
  "patch_hygiene_policy_version": "...",
  "final_patch_capture_hygiene_passed": true,
  "official_prediction_hygiene_passed": true,
  "training_export_hygiene_passed": true,
  "only_filtered_changes_rejected_from_training": true,
  "filtered_file_count": 0,
  "filtered_fixture_count": 0,
  "flagged_test_like_change_count": 0,
  "public_path_leak_scan_passed": true,
  "runtime_private_evidence_present": true,
  "acceptance_ready": true
}
```

其中 `filtered_file_count` 可以大于 0，表示测试 fixture 中故意制造了诊断残留；通过条件不是“没有过滤”，而是“过滤正确、训练目标没有污染”。

## 7. 测试计划

### 7.1 新增 focused tests

建议新增：

```text
tests/unit/test_repo_harness_stage16e_patch_hygiene_policy.py
tests/unit/test_repo_harness_stage16e_final_patch_capture.py
tests/unit/test_repo_harness_stage16e_export_hygiene.py
tests/unit/test_repo_harness_stage16e_acceptance.py
```

如果文件数量过多，也可以合并，但测试名称必须能清楚区分 policy、capture、export 和 acceptance。

### 7.2 Policy tests

覆盖：

```text
hard exclude:
  patch.txt
  *.orig
  *.rej
  root debug_*.py
  root repro*.py
  node_modules/**
  .venv/**
  __pycache__/**
  .pytest_cache/**
  runtime_private/**
  .repo_harness_runtime/**
  .repo_harness_env_overlay/**

false positive:
  src/patch.py 保留
  src/original.py 保留
  src/reproducer.py 是否过滤必须由 policy 明确。建议第一版只过滤根目录 repro*.py，不过滤 src/reproducer.py。
  docs/debugging.md 保留
  pyproject.toml 默认 flag_only，不 hard exclude
```

### 7.3 Capture integration tests

覆盖 local adapter 和 Docker adapter。如果 Docker 在本机不可用，Docker 测试可以使用现有 integration marker，但 Stage 16E 不能声称 Docker path 完整通过，除非 Docker 测试实际跑过。

必测：

```text
source + diagnostic 混合改动 -> final.patch 只包含 source。
only diagnostic 改动 -> cleaned patch 为空，only_filtered_changes=true。
final verifier strict replay 使用 cleaned patch。
raw patch artifact 不进入 public evidence。
final_patch_hygiene_report 不泄漏 raw hunk。
```

### 7.4 Official prediction builder tests

在 `tests/unit/test_pre_verl_swebench_official_inputs.py` 中补：

```text
patch.txt / *.orig / debug_*.py 被剥离。
node_modules/** 被剥离。
内容级 FAIL_TO_PASS / test_patch / 本机绝对路径仍 fail closed。
只有 filtered changes 时 prediction 被排除或明确 diagnostic-only。
manifest 记录 patch_hygiene_policy_version 和 filtered_file_count。
--keep-test-file-changes 只影响 test-like 文件，不影响 hard exclude。
```

### 7.5 Export hygiene tests

覆盖：

```text
SFT export 不含 filtered patch hunk。
RL export 不含 filtered patch hunk。
preference pair 不消费 only_filtered_changes 样本。
patch_hygiene_status=failed 的样本被 export audit 拒绝。
patch_hygiene_status=filtered 且 cleaned patch 非空的样本可以保留，但必须带 batch-safe hygiene facts。
```

### 7.6 Inspector tests

覆盖：

```text
缺少 stage16e_patch_hygiene_policy.json -> reject。
summary 声称 passed，但 report 有 filtered hunk 泄漏 -> reject。
canonical evidence map 缺少关键 artifact -> reject。
public evidence 出现 raw diff hunk -> reject。
public evidence 出现 runtime_private 真实路径 -> reject。
public hygiene report 直接暴露 unsafe raw filtered path -> reject。
only_filtered_changes_rejected_from_training=false -> reject。
```

## 8. 前置回归命令

实施前后都建议跑：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_command_policy.py \
  tests/unit/test_repo_harness_stage16a_execute_bash.py \
  tests/unit/test_repo_harness_stage16b_diagnostic_shell_tool.py \
  tests/integration/test_repo_harness_stage16b_docker_diagnostic_session.py \
  tests/unit/test_repo_harness_stage16c_public_environment_context.py \
  tests/unit/test_stage16d_healthcheck_schema.py \
  tests/unit/test_stage16d_healthcheck_builder.py \
  tests/unit/test_stage16d_healthcheck_acceptance.py \
  tests/unit/test_pre_verl_swebench_official_inputs.py
```

Stage 16E focused tests 完成后，还必须跑：

```bash
PATH=.venv/bin:$PATH python -m compileall -q src scripts/pre_verl
git diff --check
```

如果接入 `repo-harness` CLI，还需要至少跑一个 CLI dispatch 测试。

## 9. 验收标准

Stage 16E 可以标记为本地完成，必须同时满足：

1. 统一 patch hygiene policy 存在，且 Local / Docker final patch capture 和 official prediction builder 共用同一套 hard-exclude 分类。
2. `final.patch` 和 `final.diff` 使用 cleaned patch projection。
3. raw patch / raw diff 只进入 runtime-private 或 audit-only artifact。
4. 被过滤文件可以在 hygiene report 中审计，但不能进入 final patch、SFT target、RL reward evidence、preference pair 或 official prediction。
5. only-filtered-changes 样本不能进入 policy loss，也不能作为成功正样本。
6. source + diagnostic 混合改动时，source 改动仍可进入 final verifier 和训练候选。
7. official prediction builder 仍然能构建 SWE-Bench prediction，并记录 patch hygiene facts。
8. public evidence leak scan 通过。
9. Stage 16E inspector 或等价验收命令通过。
10. Stage 16A 到 Stage 16D.1 关键回归通过。

## 10. 风险和取舍

### 10.1 误删真实源码风险

过宽过滤会误删真实源码改动。例如 `src/reproducer.py` 可能是合法源码文件。第一版因此只过滤根目录明显诊断脚本，不递归过滤所有包含 `repro` 的路径。

如果后续代表性诊断发现更多真实残留模式，应先加入 fixture 和 false-positive 测试，再扩大 hard-exclude。

### 10.2 test-like 文件策略

SWE-Bench official prediction 默认应剥离 test-like 文件变更；但 RepoHarness generic final patch 不应全局剥离所有 test-like 改动。Stage 16E 第一版应把 test-like 改动标记为 `flag_only`，由 task policy 或 official prediction policy 决定是否排除。

### 10.3 raw patch 保留风险

raw patch 对 debug 很有价值，但也最容易包含隐藏路径、诊断脚本和本机路径。它必须 runtime-private，不能进入公开 evidence、TrainingView、AgentLoopOutput、DataProto 或导出数据文件。

### 10.4 与 Stage 17 的关系

Stage 16E 只保证单条 run 的补丁和训练目标清洁。Stage 17 仍需定义 dataset-level policy，例如哪些任务允许测试文件变更、哪些任务只允许源码变更、哪些任务的 lock file 变更可训练。

## 11. 建议提交边界

Stage 16E 建议至少拆成一个提交：

```text
feat: add stage16e patch hygiene gates
```

如果实现较大，可以拆成两个提交：

```text
feat: add patch hygiene policy and final patch capture
test: add stage16e export and acceptance coverage
```

提交不要混入：

```text
既有未跟踪 HTML
training_design 原始资料
vastai_cli.md
pyrightconfig.json
runs/ 下非本阶段必要 evidence
```

## 12. 完成后交付

执行完成后应给出：

```text
新增或修改的代码文件列表
新增测试文件列表
Stage 16E evidence 目录
focused tests 结果
前置回归测试结果
compileall 结果
git diff --check 结果
inspector 结果
仍保留的非阻断风险
```

如果 Docker integration 无法在本机运行，必须明确说明：

```text
Local final patch capture path 已通过。
Docker final patch capture path 未通过完整验收。
Stage 16E 不能标记为 complete，只能标记为 local-only partial。
```
