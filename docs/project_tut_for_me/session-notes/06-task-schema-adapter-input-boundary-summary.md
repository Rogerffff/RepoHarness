# 第一轮源码讲解总结：任务 schema、Task Adapter 与输入边界

## 1. 这份笔记记录什么

这份笔记整理的是当前学习计划中第一轮已经讲过的内容。主题是：

```text
任务定义 -> Task Adapter -> 运行时任务对象 -> 验证器配置 -> 模型可见输入边界
```

这一轮不是讲完整 `run_task()` 主流程，而是先把“任务到底是什么”讲清楚。因为在 RepoHarness 里，一个任务不是一段 prompt，也不是一个 GitHub issue 的原文，而是由这些部分共同组成：

- 仓库来源：例如 fixture repository、本地仓库、本地源码归档、固定 public snapshot。
- 问题描述：也就是模型最终要解决的用户可见问题。
- 环境信息：例如 Python 版本、依赖安装方式、Docker image、pytest 命令。
- 验证器信息：例如 `test_command`、final verifier timeout、fail-to-pass tests、pass-to-pass tests。
- 可见性策略：哪些字段可以给模型看，哪些只能给 evaluator 或 audit 使用。
- 证据绑定：例如 source archive 的哈希、base commit、隐藏测试 selector 的哈希、PR/issue 来源引用。

本轮核心结论可以先记住一句话：

```text
TaskDefinition 是完整任务事实，RunnableTask 是运行时可用投影，VerifierConfig 是验证器视角输入，adapter-visible input 是模型可见任务说明。
```

## 2. 本轮重点阅读过的源码文件

本轮主要围绕下面几个文件展开：

```text
src/repo_harness/schema_base.py
src/repo_harness/tasks/schemas.py
src/repo_harness/tasks/adapter.py
src/repo_harness/tasks/command_policy.py
src/repo_harness/context/builder.py
```

对应的真实任务和证据例子包括：

```text
runs/v3-core-realrepo-deepseek-20260504T000000Z/agent_loop_runs/v3_core_realrepo_local_buggy_calculator_deepseek_docker_v2/task.yaml
runs/v3-core-realrepo-deepseek-20260504T000000Z/generated_inputs/realrepo_local_buggy_calculator_deepseek_docker_v2.yaml
runs/v3-final-swebench-agent-loop-20260503T035615Z/generated_inputs/sympy__sympy-24909_agent_loop_task.yaml
runs/v4-pr-issue-task-source-feasibility-20260504T063745Z/adapter_visible/v4_py_click_help_hint_shadowing.json
docs/v4/evidence/task-source-freeze/task_freeze_manifest.json
docs/v4/evidence/task-source-freeze/adapter_visible_task_input_manifest.json
docs/v4/evidence/task-source-freeze/evaluator_only_evidence_manifest.json
docs/v4/evidence/task-source-freeze/source_archive_manifest.json
```

## 3. Pydantic 在这里解决什么问题

RepoHarness 的任务 schema 是用 Pydantic 定义的。你可以把 Pydantic 理解成“带运行时校验能力的数据类系统”。

普通 Python 类只是在代码里约定字段，而 Pydantic model 会在读取 JSON 或 YAML 时做实际检查。例如：

- 字段类型不对会报错。
- 必填字段缺失会报错。
- 多写了 schema 不认识的字段会报错。
- 某些字段之间互相矛盾时，可以通过 validator 报错。

项目里的基础类在：

```text
src/repo_harness/schema_base.py
```

里面的 `StrictBaseModel` 使用了两个重要配置：

```python
extra = "forbid"
validate_assignment = True
```

含义是：

- `extra = "forbid"`：任务文件里出现未声明字段时不能静默接受。这样可以避免拼错字段名导致训练或评测输入悄悄失真。
- `validate_assignment = True`：对象创建之后，如果代码再给字段赋新值，也要重新校验。这样可以避免规范化过程中写入非法状态。

这对 agentic training 很关键，因为训练样本和评测任务如果字段含义不稳定，后面的轨迹、reward、export 都会变得不可审计。

## 4. TaskDefinition：磁盘上的完整任务事实

`TaskDefinition` 定义在：

```text
src/repo_harness/tasks/schemas.py
```

它代表磁盘任务文件中的完整事实。常见字段包括：

- `schema_version`：任务 schema 版本。
- `id`：任务标识。
- `task_version`：同一个任务定义的版本。
- `dataset_name`：任务来源数据集名称，例如 SWE-Bench-like 子集或项目自己的任务集合。
- `source_kind`：源码来源类型或任务来源类型。
- `repo`：仓库标识。
- `repo_source_spec`：源码如何取得，例如本地仓库、本地归档、fixture repository、public snapshot。
- `base_commit`：任务基准 commit。它不一定直接发给模型，但会用于复现和证据绑定。
- `source_archive_sha256`：源码归档的 sha256 哈希，用于确认源码没有被替换。
- `issue`：模型需要解决的问题描述。
- `setup_command`：任务运行前的准备命令。
- `test_command`：公开或验证用测试命令。
- `timeouts`：setup、test、agent、final verifier 等阶段的超时。
- `environment`：Python、Docker、依赖等环境要求。
- `expected_files`：期望模型关注或可能修改的文件。
- `fail_to_pass_tests`：修复前失败、修复后应通过的测试标识。
- `pass_to_pass_tests`：修复前通过、修复后也应保持通过的测试标识。
- `gold_patch`：参考答案 patch。这个字段必须隐藏，不能给模型看。
- `visibility`：字段可见性策略。
- `metadata`：额外元数据，例如 evidence hash、任务构造来源等。

这里最容易混淆的是 `fail_to_pass_tests`、`pass_to_pass_tests` 和 `gold_patch`。

它们不是普通提示词，而是 evaluator 用来判断任务是否解决的证据或验证计划。第一版设计里，这些内容默认不能直接进入模型可见上下文。原因很简单：如果模型知道 hidden test selector 或 gold patch，就不是在解决任务，而是在读取答案。

## 5. VisibilityPolicy：模型可见和 evaluator-only 的边界

`VisibilityPolicy` 也是在 `src/repo_harness/tasks/schemas.py` 中定义的。它描述不同字段的可见性。

典型策略包括：

- `model_visible`：可以进入模型上下文。
- `hidden_reference`：作为参考答案或隐藏证据，只能用于评测或审计。
- `verifier_only`：验证器可使用，但模型不能看到。

`TaskDefinition` 中有 validator 会检查几个关键边界：

- `gold_patch` 必须是 `hidden_reference`。
- `fail_to_pass_tests` 不能直接是 `model_visible`。
- `pass_to_pass_tests` 不能直接是 `model_visible`。

这就是 RepoHarness 和普通“把题目和答案一起塞给模型”的脚本之间的重要区别：它维护了模型可见输入、验证器输入和训练导出证据之间的边界。

## 6. VerifierConfig：验证器真正需要的输入

`VerifierConfig` 也是由 `TaskDefinition` 派生出来的。它不是完整任务，而是验证器运行时真正需要的配置。

它通常包含：

- `test_command`
- `test_timeout_sec`
- `final_verifier_timeout_sec`
- `fail_to_pass_tests`
- `pass_to_pass_tests`
- `visibility_policy`

在代码里，`TaskDefinition.to_verifier_config()` 会负责这个转换。

这样设计的好处是：验证器不需要拿到完整 `TaskDefinition`，只拿它需要的那部分。比如验证器不需要知道 agent provider 是 DeepSeek 还是 OpenAI，也不应该关心训练导出怎么写。

## 7. RunnableTask：运行时任务投影

`RunnableTask` 也是从 `TaskDefinition` 派生出来的运行时对象。

你可以这样理解三者关系：

```text
TaskDefinition
  -> VerifierConfig：给验证器用
  -> RunnableTask：给运行主流程、workspace 和 context builder 用
```

`RunnableTask.from_definition()` 会把完整任务定义转换成运行时对象。它会保留运行任务所需字段，例如：

- `id`
- `task_version`
- `dataset_name`
- `issue`
- `repo`
- `base_commit`
- `setup_command`
- `test_command`
- `timeouts`
- `environment`
- `expected_files`
- `visibility`

它不会把 `gold_patch` 当成模型可见内容传下去。

## 8. 关于 agent_visible_view() 的疑问

你问过一个很关键的问题：

> 为什么 `agent_visible_view()` 里面会有 `id`、`version`、`base_commit` 这些字段？模型真的需要知道这些吗？还是只是用于构造环境，不会发给模型？

准确答案是：

```text
agent_visible_view() 返回的是“安全可见投影”，不等于“所有字段都会原样发给模型”。
```

也就是说，这个函数更像是在声明：

```text
这些字段从泄漏角度看可以进入上下文构造层。
```

但真正进入模型 prompt 的内容，还要看 `ContextBuilder.build_initial_messages()` 怎么使用这些字段。

当前实现里，Context Builder 主要使用这些内容：

- `task_id`
- `task_version`
- `dataset_name`
- `issue_statement`
- `expected_files`
- 在可见性允许时使用 `test_command`

`base_commit`、`setup_command`、`environment` 这类字段更偏向复现、运行和审计，不一定会直接出现在模型消息里。

所以你觉得“这里有点奇怪”是合理的。更准确的命名也许不是 `agent_visible_view()`，而是类似：

```text
safe_context_projection()
```

意思是“上下文构造层可以安全读取的投影”。它和“最终 prompt 内容”之间还有一层 Context Builder。

## 9. TaskAdapter.load() 的完整作用

你还问过这一段代码的作用：

```python
normalized_definition = self._normalize_repo_source(definition, resolved_task_path)
repo_path_for_command_checks = self._command_validation_repo_path(normalized_definition)
self._validate_commands(normalized_definition, repo_path_for_command_checks)
verifier_config = normalized_definition.to_verifier_config()
runnable = RunnableTask.from_definition(normalized_definition)
return LoadedTask(
    definition=normalized_definition,
    runnable_task=runnable,
    verifier_config=verifier_config,
    task_path=resolved_task_path,
)
```

它可以拆成六步理解。

第一步：`_normalize_repo_source(...)`

这一步负责把任务里的源码来源规范化。例如：

- 如果任务只写了 fixture repo 名称，就解析成确定的 fixture repository path。
- 如果任务使用本地源码归档，就补充 archive path、archive sha256、base commit 等信息。
- 如果任务使用本地 Git 仓库，就解析 source path，并读取或确认 base commit。
- 如果任务使用 public snapshot，就绑定固定 archive 和 commit sha。

这一步的目标是把“可能比较松散的任务输入”变成“后续运行可以复现的任务定义”。

第二步：`_command_validation_repo_path(...)`

这一步决定命令校验时能不能拿到本地仓库路径。

例如 `setup_command` 如果是：

```text
python scripts/setup_task.py
```

那么 adapter 需要知道这个脚本是不是在仓库内部，不能让任务定义随便指向仓库外面的脚本。

第三步：`_validate_commands(...)`

这一步做静态命令检查。对应实现主要在：

```text
src/repo_harness/tasks/command_policy.py
```

当前策略比较保守：

- `test_command` 通常只允许 `pytest` 或 `python -m pytest` 形式。
- `setup_command` 当前主要允许 `python <repo_script.py>` 形式。
- 禁止 shell fragments，例如用 `&&`、`;`、管道等把额外命令藏进去。

这不是完整生产级安全沙箱，而是为了保证 harness 任务定义的命令边界可审计、可解释、可复现。

第四步：`to_verifier_config()`

这一步从完整任务定义中抽取验证器需要的配置。验证器只关心怎么跑测试、超时时间是多少、哪些测试是 fail-to-pass 或 pass-to-pass。

第五步：`RunnableTask.from_definition(...)`

这一步生成运行时任务对象。后面的 workspace、Context Builder、agent loop 都不直接操作原始 YAML 字典，而是操作已经校验过的结构化对象。

第六步：返回 `LoadedTask`

`LoadedTask` 同时保存四个东西：

- `definition`：规范化后的完整任务定义。用于 provenance、metadata 和必要的产物写入。
- `runnable_task`：运行主流程使用的任务对象。
- `verifier_config`：验证器使用的配置。
- `task_path`：任务文件路径，用于审计和复现。

所以 `TaskAdapter.load()` 的职责不是运行任务，也不是调用模型，而是：

```text
读取任务文件 -> 校验 schema -> 规范化源码来源 -> 校验命令边界 -> 拆出运行对象和验证器配置
```

## 10. SWE-Bench-like 任务文件怎么看

我们看过一个 SWE-Bench-like 例子：

```text
runs/v3-final-swebench-agent-loop-20260503T035615Z/generated_inputs/sympy__sympy-24909_agent_loop_task.yaml
```

它是一个可读取的任务定义文件，里面会包含：

- `dataset_name`，例如 `princeton-nlp/SWE-bench_Lite`。
- `source_kind`，例如 `swebench_like_fixed_snapshot`。
- `issue`，也就是模型看到的问题描述。
- `repo_source_spec`，也就是源码怎么固定。
- `metadata.hidden_evidence_hashes`，也就是隐藏证据的哈希，而不是隐藏证据原文。
- `visibility`，说明哪些内容可见、哪些内容隐藏。

这个例子的重点不是“完全复刻官方 SWE-Bench”，而是 RepoHarness 用 SWE-Bench-like 的方式表达：

```text
固定仓库源码 + 问题描述 + 隐藏验证证据绑定 + final-only verifier 边界
```

这里的 `fail_to_pass_tests` 和 `pass_to_pass_tests` 可以为空，因为 V3/V4 的某些任务采用 final-only 或隐藏证据绑定方式，不要求把 selector 直接放在模型可见字段中。

## 11. GitHub PR / issue 数据是什么意思

你问过：

> SWE-Bench-like 例子是一个可读取的 `task.yaml`，那么 GitHub PR / issue 数据是什么意思，要如何读取？

这里的“GitHub PR / issue 数据”不是说模型直接读取 GitHub 网页，也不是说每个任务都保存成一个和 SWE-Bench-like 完全一样的 `task.yaml`。

在 V4 中，它更准确地表示：

```text
从 GitHub PR / issue 任务构造流程中冻结出来的一组任务输入、源码归档、模型可见描述和 evaluator-only 证据。
```

推荐阅读顺序是：

```text
docs/v4/evidence/task-source-freeze/task_freeze_manifest.json
docs/v4/evidence/task-source-freeze/adapter_visible_task_input_manifest.json
runs/v4-pr-issue-task-source-feasibility-20260504T063745Z/adapter_visible/*.json
docs/v4/evidence/task-source-freeze/evaluator_only_evidence_manifest.json
docs/v4/evidence/task-source-freeze/source_archive_manifest.json
docs/v4/evidence/task-source-freeze/task_validity_report.json
```

这些文件共同回答：

- 哪些 PR/issue-like 任务被接受进入冻结集合。
- 哪些任务说明可以给模型看。
- 哪些证据只能给 evaluator 使用。
- 每个任务绑定哪个源码归档和 source hash。
- 任务是否具备 baseline、post-patch、flaky、license、dependency 等有效性证据。

## 12. adapter_visible JSON 里是什么

你指定过这个文件：

```text
runs/v4-pr-issue-task-source-feasibility-20260504T063745Z/adapter_visible/v4_py_click_help_hint_shadowing.json
```

这类文件不是仓库源码，也不是完整 PR 原始数据。它是“模型可见任务说明侧”的安全投影。

典型字段包括：

- `adapter_visible_task_id`：模型可见任务输入的标识。
- `repository`：任务对应的仓库，例如 `pallets/click`。
- `title`：任务标题。
- `problem_statement`：模型要解决的问题描述。
- `public_behavior_hints`：允许公开给模型的行为提示。
- `allowed_public_test_hint`：允许公开的测试提示。
- `forbidden_material_notice`：提醒哪些材料不能进入模型可见输入。
- `source_ref_id`：指向源码归档或来源绑定的引用标识。

它回答的是：

```text
模型应该知道自己要修什么问题。
```

它不负责回答：

```text
仓库所有文件内容是什么。
```

仓库内容是在运行时通过 workspace 和工具读取的。

## 13. 模型不是只看任务 JSON，它还会通过工具看仓库

你问过：

> 模型要解决 PR/issue，不是应该看到仓库内的内容吗？

是的，模型通常需要看仓库内容。但 RepoHarness 不会把整个仓库一次性塞进初始 prompt。

更合理的链路是：

```text
初始上下文给任务说明
-> agent loop 让模型决定要读哪些文件
-> 工具层执行 list_files、read_file、grep、bash、run_tests、git_diff 等操作
-> 工具结果回流给模型
-> 模型根据结果继续修改和测试
```

也就是说，`adapter_visible/*.json` 是任务说明，仓库文件内容来自 workspace。

这和真实软件工程智能体的工作方式更接近：人类开发者拿到 issue 后，也不会一开始就把整个仓库所有文件读进脑子，而是根据问题描述定位相关文件。

## 14. PR / issue 原始结构通常是什么

你还问过：

> PR / issue 的结构通常是什么样的，是直接从 GitHub 上能够获取的吗？

通常 GitHub issue 会包含：

- repository
- issue number
- title
- body
- author
- labels
- created_at / updated_at
- comments
- linked pull requests

通常 GitHub pull request 会包含：

- repository
- pull request number
- title
- body
- base branch
- head branch
- base commit
- head commit
- commits
- changed files
- diff / patch
- review comments
- CI status
- linked issue
- merge commit 或 fix commit

这些数据可以通过 GitHub API、`gh` 命令行、网页抓取或已有数据集导出获得。

但是在训练和评测任务中，原始 GitHub 数据不能不加区分地给模型。尤其这些内容通常不能进入模型可见输入：

- raw PR diff
- fix commit
- gold patch
- review comments 中暴露答案的部分
- hidden test selector
- official resolved status
- post-patch passing log
- provider raw response
- reward / score 字段

RepoHarness 的 V4 task freeze 就是在做这件事：

```text
从原始 PR/issue-like 材料中，拆出模型可见任务说明和 evaluator-only evidence，并把二者通过哈希、manifest 和 source_ref_id 绑定起来。
```

## 15. 本机源码、source archive 和 Docker 的关系

你问过：

> 在本机上是要拉仓库然后在 Docker 中创建仓库的镜像来作为执行环境吗？

当前更准确的理解是：

```text
不是每个仓库都单独构建一个 Docker 镜像。
Docker image 提供通用执行环境，仓库源码通过 source archive 或本地仓库物化到 workspace，再挂载进容器执行。
```

也就是说，Docker image 主要提供：

- Python
- pytest
- git
- 基础系统依赖
- harness 需要的运行工具

具体任务的仓库源码来自：

- fixture repository
- local repository
- local archive
- public snapshot 的预下载归档

V4 例子中，`source_archive_manifest.json` 会记录类似信息：

- `repo`
- `selected_fixed_revision`
- `source_archive_path`
- `source_archive_sha256`
- `source_tree_hash`

这样做的好处是：任务运行时不依赖 GitHub 当前分支状态，也不依赖网络临时拉取结果。源码内容由本地归档和哈希绑定。

## 16. Docker workspace 的四个阶段

后续讲到 `workspace/materialization.py` 和 `workspace/docker_adapter.py` 时会展开。这里先记录本轮已经提到的四个概念：

```text
source_checkout
setup_workspace
agent_workspace
verification_workspace
```

它们分别解决不同问题：

- `source_checkout`：从 source archive 或本地仓库物化出来的干净源码。
- `setup_workspace`：用于执行 setup 或 baseline 相关准备，记录依赖和初始状态。
- `agent_workspace`：模型工具实际读写的工作区。
- `verification_workspace`：final verifier 使用的干净验证工作区，通常会重新应用 final patch，避免 agent workspace 的临时副作用污染最终验证。

这也是为什么 RepoHarness 不只是“让模型在一个目录里改代码然后跑 pytest”。它要把源码来源、模型修改、最终 patch、验证器重放和证据产物拆开，才能支持后续训练导出和审计。

## 17. 本轮问答索引

### 问题一：为什么 `agent_visible_view()` 会包含 `id`、`version`、`base_commit`？

回答要点：

- 它返回的是安全可见投影，不等于最终 prompt。
- 真正进入模型消息要看 Context Builder。
- `base_commit` 主要用于复现和审计，不一定直接发给模型。
- 当前命名可能会让人误解，理解成“Context Builder 可以读取的安全字段集合”更准确。

### 问题二：`TaskAdapter.load()` 中那几行代码分别做什么？

回答要点：

- `_normalize_repo_source()`：把源码来源规范化，补齐路径、哈希、base commit。
- `_command_validation_repo_path()`：决定命令校验是否需要仓库路径。
- `_validate_commands()`：检查 `test_command` 和 `setup_command` 是否符合安全、可审计策略。
- `to_verifier_config()`：抽出验证器需要的配置。
- `RunnableTask.from_definition()`：生成运行时任务对象。
- `LoadedTask(...)`：把完整定义、运行对象、验证器配置和任务路径一起交给后续主流程。

### 问题三：SWE-Bench-like 任务和 GitHub PR / issue 数据有什么区别？

回答要点：

- SWE-Bench-like 例子通常可以直接看到生成后的任务定义文件。
- V4 GitHub PR/issue 数据更像是一套冻结证据目录，包括 adapter-visible input、evaluator-only evidence、source archive manifest 和 task validity report。
- PR/issue 原始数据会被拆分。可公开的问题描述给模型，隐藏答案和验证证据只给 evaluator。

### 问题四：`adapter_visible/v4_py_click_help_hint_shadowing.json` 是什么？

回答要点：

- 它是模型可见任务说明，不是仓库源码。
- 它告诉模型要解决什么问题、属于哪个仓库、有哪些允许公开的行为提示。
- 仓库文件内容要通过 workspace 工具读取。
- 它通过 `source_ref_id` 和 source archive / evaluator evidence 形成绑定。

### 问题五：真实 PR/issue 数据能不能直接从 GitHub 获取？

回答要点：

- 可以通过 GitHub API、`gh`、网页或数据集导出获取。
- 但是不能原样全部给模型。
- raw diff、fix commit、gold patch、hidden tests、post-patch logs、reward 字段等都需要留在 evaluator-only 或 audit-only 边界内。

### 问题六：是不是要把每个仓库做成 Docker 镜像？

回答要点：

- 当前 RepoHarness 更像是“通用 Docker 执行环境 + 任务源码 workspace 挂载”。
- Docker image 提供 Python、pytest、git 和基础依赖。
- 仓库源码由 source archive 或 local repository 物化出来。
- final verifier 会在独立 verification workspace 中重放 patch 并运行测试。

## 18. 下一部分应该讲什么

第一轮已经讲完：

```text
任务 schema 和 Task Adapter
```

下一轮建议进入：

```text
真实输入 freeze / materialization
```

也就是看清楚：

- SWE-Bench-like 输入怎么变成任务定义。
- GitHub PR/issue-like 输入怎么冻结成 adapter-visible input 和 evaluator-only evidence。
- source archive 如何被校验、解压和物化成 workspace。
- 为什么运行时应该使用固定源码归档，而不是临时拉取 GitHub 最新分支。

下一轮建议按这个顺序读源码：

```text
src/repo_harness/workspace/materialization.py
src/repo_harness/v3_swebench_like.py
src/repo_harness/v4_implementation_inputs.py
src/repo_harness/v4_task_freeze.py
```

读完这一块之后，再进入 `src/repo_harness/evaluation/runner.py`，也就是完整 `run_task()` 主编排。
