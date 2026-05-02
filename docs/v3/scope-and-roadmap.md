# RepoHarness V3 Scope And Roadmap

## 0. 文档定位

本文定义 RepoHarness 第三版的推荐范围、优先级、最小完成定义、机器验收证据和明确非目标。本文不是第三版已经完成的声明，也不是逐阶段实施计划；后续如果进入实现，应另写 `docs/v3/implementation-plan.md`，并把每个阶段拆成可以测试、可以审查、可以回滚的工程任务。

本文基于当前仓库的第二版文档、第二版最终机器验收产物、现有 Python 代码、Claude Code TypeScript 参考源码、以及 `docs/13-agentic-technical-report-reading-map.md` 中总结的工业界 agentic training infrastructure 方向。本文不会把候选方向机械照抄为第三版范围，而是按 RepoHarness 当前定位进行取舍。

当前工作区状态也需要作为范围探索背景记录：写作开始时执行 `git status --short`，工作区已有未提交修改、删除和未跟踪文件，例如 `docs/02-system-architecture.md` 被修改，一批旧版文档路径显示删除，`docs/v1/`、`docs/build-your-own/`、`.vscode/` 和 `uv.lock` 等文件未跟踪。本文写作不删除、不回滚、不提交这些既有状态。具体提交历史以执行本文后续实施或审查时的 `git log` 和 `git status` 为准，本文不把实时 `HEAD` 写成长期范围事实。

仓库根目录的 `AGENT.md` 文件存在，要求文档和注释除专业词汇外使用清晰、通俗、详细的中文，必要时搭配具体数值或实现例子解释。本文同时按用户消息中的 AGENTS.md 指令执行中文文档写作：中文表述必须清晰、详细，避免缩略或含混表达。

## 1. V2 已建立的基础

第二版已经把第一版的 replay-only 最小闭环推进为真实模型可运行、导出审计更严格、多 rollout 和多 scaffold 可比较的研究型 Harness。根据 `docs/v2/final-acceptance.md` 和 `runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json`，第二版最终状态为 `status = "passed"`。

第二版已经建立的关键基础包括：

- 第二版 run schema、版本常量、`run_config_facts.json`、最终 `run_metadata.json`、环境指纹和 tool schema snapshot。
- `inspect-run` 第二版展示、legacy metadata 兼容、run metadata 审计和 artifact 引用检查。
- SFT、RL rollout、preference 三种导出格式的 format-specific export directory、`export_manifest.json`、`audit_report.json` 和 `audit_report.md`。
- `training_eligibility` 主状态、oracle hidden feedback 默认 diagnostic-only、preference pair 硬门控和 compare scope。
- `ExperimentConfig` 最小多 rollout runner、`experiment_manifest.json`、`aggregate_metrics.json` 和 task-set 阈值检查。
- `ModelClient` 协议、replay/fake 兼容层、mock provider、DeepSeek primary real provider、OpenAI fallback adapter 和受控 provider raw artifact。
- scaffold registry、`single_shot_patch`、`simple_react` 和顺序式 `planner_coder_verifier`。
- repo materialization、命令环境策略门、verifier parser policy，以及 20 个 replay task set。
- Docker execution mode 的 Stage 14 `interface_only` 可审计路径：当前会清晰拒绝 `runtime.execution_mode=docker`，不会静默回退到 `local_process`。
- 全局 `v2_acceptance_report.json` 和 `inspect-v2-acceptance --assert-complete`，并且验收检查会重新读取关键 evidence refs，拒绝 Docker backend 伪装、real provider 凭证状态伪装和 provider raw marker 进入正式训练 JSONL 等路径。

第二版最终验收中的关键事实是：

- replay task set 有 20 个任务、20 个 recorded runs、18 个进入 Agent Loop、18 个 formal final verifier runs、18 个 success runs、2 个 structured skipped runs。
- mock provider smoke accepted，real provider smoke 为 DeepSeek primary accepted with credentials，凭证来源只记录为 `local_secret_file_redacted`。
- Docker stage 是 `interface_only passed`，`docker_backend_implemented = false`，`docker_execution_mode_behavior = "clearly_rejected"`，`production_sandbox_claimed = false`。
- provider raw request、raw response、reasoning summary、Authorization marker、hidden tests、gold patch 和 secrets 没有进入正式训练 payload。

这些基础非常重要。第三版不应该重写第二版闭环，也不应该绕开第二版已经建立的事实链条。第三版的价值应该体现在：让这些事实链条跑在更真实的仓库级执行环境和任务来源上，并让较长、较不稳定的实验运行仍然可以恢复、诊断和导出。

## 2. V2 遗留问题和 V3 机会

第二版的最大短板不是“缺少更多模型供应商”，而是执行环境和任务来源仍然偏轻量。第二版已经可以证明协议、导出审计和 provider artifact 可以闭环，但主要任务集仍然是 replay fixture，Docker 只是 interface-only，真实仓库任务和 SWE-Bench-like 小子集尚未形成端到端机器验收。

第三版最值得解决的遗留问题包括：

1. Docker backend 没有端到端实现。现有 `WorkspaceAdapter` 协议、`WorkspaceBackendFacts`、`WorkspaceExecutionFacts` 和 `docker_stage_status.json` 已经为后端扩展留出接口，但当前 `run_task` 仍在早期拒绝 `runtime.execution_mode=docker`。
2. 任务多样性有限。第二版 20 个 replay task set 满足验收数量，但成功任务主要还是围绕 repository-style fixture。它还不是面向真实或半真实仓库任务的评测环境。
3. SWE-Bench-like 适配尚未落地。第二版有 fail-to-pass、pass-to-pass、hidden feedback、final-only policy 等基础，但没有把 issue statement、base commit、test patch、environment spec、source hash 和 verifier evidence 组合成可运行的小子集。
4. Experiment runner 不支持恢复。当前实验 runner 顺序运行并写 manifest，但没有 pending、running、completed、failed、skipped 的可恢复状态机，没有 checkpoint manifest，也没有 run-level retry policy。
5. 长轨迹上下文治理仍偏最小。第二版已有 `ContextManager`、content replacement state、prepared messages artifact 和 token estimate，但还没有把 context compaction、repeated tool call、no progress、context-limit failure 作为长 rollout 的明确验收闭环。
6. reward 和 failure diagnostics 还可以更训练友好。第二版已有基础 `FailureDiagnostics` 和 reward metadata，但真实仓库任务需要更强的失败分布、环境不稳定分类、reward hacking suspected、unfinished trajectory penalty、invalid tool call penalty、regression penalty 等字段。
7. Acceptance evidence bundle 还不够不可变。当前 `docs/v2/final-acceptance.md` 已经同步为 `sft_jsonl = 6`、`rl_jsonl = 6`、`preference_jsonl = 5`，与当前 `v2_acceptance_report.json` 一致；但 `runs/v2-final-acceptance-20260501T223447Z-command.log` 中的旧摘要仍显示 `sft = 3`、`rl = 3`、`preference = 2`。这不表示第二版能力失败，但说明最终报告、命令日志、输入 evidence refs 和文档摘要之间还缺少不可变绑定。第三版验收必须避免这种“机器报告后来更新，命令日志或人工摘要未形成同一个不可变验收包”的漂移。
8. Real provider accepted run 的导出证据与全局 acceptance report 仍然分散。Stage 11 单独检查过 DeepSeek accepted run 的 SFT/RL 导出，但全局第二版 acceptance report 的 export audit roots 主要来自 V1、mock provider 和 replay task set。第三版应该把真实 provider run 的导出审计纳入全局验收扫描。
9. Preference export 的硬门控已经完成，但第二版最终单 rollout task set 没有产生真实 preference pair。第三版如果要强调训练数据价值，应该至少产生一组同条件多 rollout preference baseline，或者在无法产生时给出机器可审计的阻断原因分布。
10. 真实仓库任务的来源门槛必须比本地 fixture 更硬。第三版可以保留本地 Git 仓库快照作为开发和回归样例，但最小完成定义中至少一个真实 repository-level task 必须来自公开仓库固定 commit 或预下载公开归档，并记录 remote URL、base commit、archive sha256、source tree hash 和 dataset/source revision。
11. SWE-Bench-like 小子集不能被普通 issue fixture 空壳替代。第三版默认目标应该是从公开 SWE-bench Lite 的 test split 手工选择 3 个稳定任务；如果使用等价 issue-style task，则必须具备非空 fail-to-pass / pass-to-pass 列表，或者具备明确 `test_patch` / `verifier_patch` 证据，并由 inspect 命令拒绝空壳 issue-style task。
12. Context compaction 的验收口径不能被 long rollout diagnostics 替代。第三版至少需要一个真实 context compaction 闭环，同时至少需要一个 long rollout diagnostics 样例；不能只实现无进展或重复工具调用诊断后宣称完成上下文压缩能力。
13. 第三版 Docker 后端的现实硬件环境是 Apple Silicon 上的 Docker Desktop：Docker Desktop 4.71.0、Docker Engine 29.4.1、Docker backend platform `linux/arm64`、Docker context `desktop-linux`、Docker Compose 5.1.3。SWE-Bench 官方资料推荐 x86_64 并把 arm64 支持标为 experimental，因此第三版必须优先挑选轻量、可在 linux/arm64 或本地可构建镜像上稳定运行的任务，并把 platform、image、build mode、是否使用本地构建或跨架构仿真写入 evidence。

第三版的机会是把 RepoHarness 从“真实模型小规模 Harness”推进为“可复现的 repository-level evaluation harness”。这里的 repository-level 不表示完整公开榜单系统，而是表示任务、源码快照、执行环境、工具轨迹、final verifier 和训练导出都围绕真实或半真实仓库级工作流记录完整证据。

## 3. V3 一句话主线

RepoHarness V3 将第二版的真实模型小规模 Harness 推进为可复现的 repository-level evaluation harness，核心实现 Docker-based executable repository environment、真实仓库任务和 SWE-Bench-like 小子集、单机可恢复多 rollout 实验，以及长轨迹上下文和失败诊断证据链，同时继续保持轻量级研究 Harness 边界，不声称生产级安全沙箱、完整 SWE-Bench 榜单或新的强化学习算法。

这条主线是一个组合，而不是单点功能。Docker backend 解决“在哪里执行”的可信度；真实仓库和 SWE-Bench-like 任务解决“执行什么任务”的研究价值；可恢复 experiment runner 解决“如何稳定收集多 rollout 轨迹”；长轨迹诊断和增强 reward/failure metadata 解决“轨迹为什么可训练、为什么失败、如何过滤”的数据质量问题。

## 4. V3 范围优先级

### 4.1 第一优先级：Docker Workspace Backend 端到端执行

第三版必须优先实现独立的 Docker Workspace Backend。原因是第二版已经把 Docker 明确列为未完成能力，并且 Stage 14 已经把伪装 Docker backend 的验收路径封住。如果第三版继续不实现 Docker，那么 RepoHarness 的“executable repository environment”叙事会停留在本地进程执行边界，无法接近工业界报告中反复强调的 sandbox / execution substrate / environment service 方向。

纳入第三版的原因：

- 解决第二版最大的执行环境短板。
- 为真实仓库任务和 SWE-Bench-like 小子集提供更可复现的依赖和命令执行上下文。
- 让 setup、agent tool execution、`run_tests` 和 formal final verifier 都有可审计 container execution facts。
- 让简历叙事从“本地进程 Harness”升级为“Docker-based executable repository environment”，同时保守避免生产级安全沙箱表述。

最小可交付物：

- 新增独立 `DockerWorkspaceAdapter` 或等价 Docker backend，不能把容器逻辑塞进 `LocalWorkspaceAdapter`。
- Docker backend 不能只实现 `WorkspaceAdapter` 协议中声明的生命周期方法，还必须覆盖当前工具和 verifier 实际调用面，包括命令执行、路径解析、读写文件、patch apply、final patch capture 和 verification workspace patch replay。
- Eval Runner 需要引入 workspace backend factory，替换当前对 `LocalWorkspaceAdapter` 和 local environment fingerprint 的硬编码路径。
- Docker mode 下 source checkout、setup workspace、agent workspace、verification workspace 都在容器执行上下文中运行命令。
- setup、普通 agent tool execution、`run_tests`、final patch capture、verification workspace strict patch replay 和 formal final verifier 都记录 execution facts。
- 记录 image reference、image id、platform、container id 或 execution id、container workdir、container path、host artifact path、mount policy、network policy、timeout、exit code、stdout/stderr artifact、container cleanup status。
- 明确记录本机 Docker 环境事实：Docker Desktop 4.71.0、Docker Engine 29.4.1、Docker backend platform `linux/arm64`、Docker context `desktop-linux`、Docker Compose 5.1.3，以及每个 run 实际使用的 image platform、build mode、是否本地构建、是否跨架构仿真。
- 最小执行方式可以先采用宿主机 run directory 保存源码和 artifacts、Docker 容器 bind mount workspace 执行命令的模式。即使采用这种方式，也必须证明命令实际在 container execution context 中运行，而不是 host local process。
- Docker mode 不能静默回退到 `local_process`。Docker 不可用时，声明 `docker_backend` 必须失败；只有 interface-only 路径才允许在第二版成立，第三版核心完成不再以 interface-only 作为通过条件。
- Docker mode 仍然必须先冻结 `final.patch` 和 `final.diff`，再在独立 verification workspace 中 strict patch replay。

机器验收证据：

- `docker_backend_status.json`：声明 Docker backend implemented，列出所有 Docker 后端测试和 evidence refs。
- `container_execution_facts.json` 或 run-level `container_execution_facts/*.json`：记录每个阶段的容器执行事实。
- Docker replay smoke：至少一个 replay task 在 Docker backend 下完成 source checkout、setup、agent tools、`run_tests`、final patch、verification workspace 和 final verifier。
- Docker provider smoke：至少一个 mock provider task 必须在 Docker backend 下通过；有真实 provider 凭证时，至少一个真实 provider smoke 必须在 Docker backend 下通过 formal final verifier。无凭证环境可以结构化 skip 真实 provider，但不能把 skip 记为真实 provider accepted。
- Docker repository-level combination smoke：至少一个真实 repository-level task 和至少一个 SWE-Bench-like task 必须在 Docker backend 下完成 source checkout、setup、agent tools、final patch freeze、verification workspace strict patch replay 和 formal final verifier。若 Apple Silicon / `linux/arm64` 平台限制导致某个 SWE-bench Lite 实例无法稳定运行，替代 issue-style task 必须满足同等测试证据门槛。这样第三版证明的是 Docker-based repository-level harness，而不是“Docker 只跑 fixture，真实任务只跑本地进程”。
- `docker_phase_coverage_matrix.json`：逐 run 和逐 phase 检查 `source_checkout`、`setup`、`agent_tool`、`run_tests`、`final_patch_capture`、`verification_workspace`、`final_verifier` 是否都有 container execution facts。`inspect-workspace-backend --assert-docker-backend` 必须读取这个矩阵并拒绝只验证 summary 或少量 smoke run 的通过方式。
- `inspect-workspace-backend --assert-docker-backend` 和后续 `inspect-v3-acceptance --assert-complete` 必须重新读取 Docker evidence refs，而不是只信任 summary 字段。

主要风险：

- Docker 可用性受本机环境影响。解决方式是把 Docker availability、backend implemented、backend e2e evidence 和 credential-gated provider smoke 分开记录。
- Apple Silicon / `linux/arm64` 与 SWE-Bench 官方推荐的 x86_64 环境存在差异。解决方式是第三版只承诺 RepoHarness 自己的小子集适配器验收，优先选择 arm64 可运行或可本地构建的轻量任务，并记录任何跨架构仿真、镜像构建失败或平台不兼容原因。
- setup 阶段可能需要网络。解决方式是 setup network policy 显式记录，agent run 和 final verifier 默认 no network 或 controlled network，并把实际生效状态写入 facts。
- 容器内路径和主机路径容易泄漏。解决方式是训练导出继续扫描本机绝对路径，并新增 container path / host path redaction 检查。

### 4.2 第二优先级：真实仓库任务和 SWE-Bench-like 小子集

第三版第二条主线应该是任务来源升级。第二版已经有 repo materialization 和 20 个 replay task set，但它还不能代表真实仓库级训练轨迹。第三版不应直接承诺完整 SWE-Bench，而应实现一个小而硬的 SWE-Bench-like 适配路径。

纳入第三版的原因：

- 解决第二版任务多样性不足的问题。
- 把 Qwen3-Coder、KAT-Coder / KwaiEnv、Cursor Composer 2 报告中的 GitHub PR mining、issue-style task、fail-to-pass / pass-to-pass、runnable environments 降维为可落地的小子集。
- 提升训练轨迹的真实价值：模型需要探索真实目录结构、理解不完整 issue、修改多文件、保护回归测试，而不是只修复一个固定 micro fixture。

最小可交付物：

- 扩展任务 schema，新增或强化 `RealRepositorySourceFacts` 和 `SweBenchLikeTaskFacts`。
- 新增 `TaskAdapterFacts`，记录 adapter 名称、adapter 版本、上游数据集名称、上游 instance id、转换策略版本、issue statement hash、final-only 标记和 decontamination artifact ref。
- 支持三类受控来源：本地 Git 仓库快照、本地归档、公开仓库固定 commit 的预下载 archive。第三版可以不主动联网抓取公开仓库，但必须记录 remote URL、commit sha、archive sha256、source tree hash 和 decontamination metadata。
- 接入至少 3 个真实 repository-level task。其中至少 1 个任务必须来自公开仓库固定 commit 或预下载公开归档，并记录 remote URL、base commit、archive sha256、source tree hash、dataset/source revision 和本地 materialization ref。其余任务可以来自本地受控 Git 仓库快照或本地归档，但不能只是同一个 calculator fixture 的复制。
- 接入至少 3 个 SWE-Bench-like task。默认来源是公开 SWE-bench Lite 的 test split，优先使用 `SWE-bench/SWE-bench_Lite` 或 `princeton-nlp/SWE-bench_Lite`。第三版最小完成只要求手工选择 3 个稳定任务，并固定 dataset name、dataset revision、split、instance_id、repo、base_commit、source archive sha256、test_patch hash、FAIL_TO_PASS、PASS_TO_PASS 和 Docker execution facts。
- 如果因 Apple Silicon / `linux/arm64` 平台限制无法稳定运行某个 SWE-bench Lite 实例，可以替换为等价 issue-style task；但替代任务必须具备非空 fail-to-pass / pass-to-pass 列表，或者具备明确 `test_patch` / `verifier_patch` 证据。inspect 命令必须拒绝缺少测试证据的空壳 issue-style task。
- SWE-Bench-like task 默认 `test_feedback_policy = disabled`；如果允许模型运行公开测试，只能使用 `public_only` 或 `structured_public_feedback`。hidden fail-to-pass 和 pass-to-pass suite 不能进入模型可见上下文或训练 payload。
- 任务质量门控必须区分 dependency setup failed、test command error、parser low confidence、flaky baseline、fail-to-pass initially passed、pass-to-pass initially failed 和 environment unstable。

#### 4.2.1 SWE-Bench-like 小子集数据源口径

第三版的 SWE-Bench-like 小子集默认来源是公开 SWE-bench Lite 的 test split。公开资料显示，SWE-bench 数据实例包含 `repo`、`instance_id`、`base_commit`、`problem_statement`、`patch`、`test_patch`、`FAIL_TO_PASS` 和 `PASS_TO_PASS` 等字段；SWE-bench 官方评测会把 patch 应用到真实仓库并在 Docker 环境中运行测试。第三版只使用这些字段建立 RepoHarness 的 adapter 和 verifier evidence，不声称复现 SWE-Bench Lite 榜单。

推荐来源优先级：

1. `SWE-bench/SWE-bench_Lite` 或 `princeton-nlp/SWE-bench_Lite` 的 `test` split，手工选择 3 个在 Apple Silicon / `linux/arm64` Docker 后端上稳定的轻量任务。
2. `SWE-bench/SWE-bench_Verified` 或 `princeton-nlp/SWE-bench_Verified` 只作为增强目标。Verified 样本质量更高，但更接近公开主流榜单，污染和表述风险也更高；即使使用 3 个 Verified 样例，也只能称为 RepoHarness 的 SWE-Bench-like adapter smoke，不能称为 Verified 榜单结果。
3. 等价 issue-style task 只能作为平台兼容替代。替代任务必须有可审计测试证据，不能用普通 issue text 加一个空 verifier 伪装成 SWE-Bench-like task。

公开资料来源：

- SWE-Bench datasets 文档：`https://www.swebench.com/SWE-bench/guides/datasets/`
- SWE-Bench evaluation 文档：`https://www.swebench.com/SWE-bench/guides/evaluation/`
- Hugging Face 数据集页：`https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite`
- SWE-Bench GitHub README：`https://github.com/princeton-nlp/SWE-bench/blob/main/README.md`

机器验收证据：

- `source_materialization_report.json`：记录每个任务的 source kind、base commit、archive sha256、source tree hash、remotes/branches/tags stripped 状态。
- `real_repository_task_manifest.json`：列出真实仓库任务、source facts、environment spec、verifier evidence 和 run refs。
- `swebench_like_task_manifest.json`：列出 SWE-Bench-like 小子集任务、fail-to-pass / pass-to-pass 配置、final-only policy 和 hidden feedback 隔离证据。
- `task_adapter_facts.json`：记录每个 adapter 转换输入、输出 task hash、final-only policy、visibility policy 和 decontamination evidence refs。
- 至少 6 个新增 repository-level runs，其中至少 3 个真实仓库任务和至少 3 个 SWE-Bench-like task。只有在 Apple Silicon / `linux/arm64` 平台限制导致部分公开 Lite 实例不可运行时，才允许使用满足同等测试证据门槛的 issue-style task 替代，并且替代理由必须进入 manifest。
- 至少 1 个真实 repository-level task 的 `source_kind` 必须是公开仓库固定 commit 或预下载公开归档；`inspect-v3-task-set --assert-complete` 必须拒绝 3 个任务全部来自本地新建 fixture 的情况。
- 至少 3 个 SWE-Bench-like task 必须有 dataset/source revision、split、instance_id、base_commit、test_patch hash、FAIL_TO_PASS / PASS_TO_PASS 或等价 verifier patch 证据；`inspect-swebench-like` 必须拒绝缺少测试证据的 issue-style 空壳替代。
- `inspect-task-source`、`inspect-swebench-like` 或统一 `inspect-v3-task-set` 命令可以断言 source hash、base commit、environment spec、verifier evidence 和 hidden feedback 隔离。

主要风险：

- 真实仓库依赖可能不稳定。解决方式是第三版只选 3 到 10 个小型、固定、可归档、可运行的样例，不追求规模。
- SWE-Bench-like 容易被误表述为完整 SWE-Bench。文档、报告和 README 必须始终写“小子集”“SWE-Bench-like adapter”“issue-style executable task”，不能写“完整 SWE-Bench 复现”或“榜单结果”。
- 任务构造可能引入污染。解决方式是记录 decontamination metadata，训练 JSONL payload 只能包含脱敏摘要，完整污染检查材料只能作为 audit artifact。

### 4.3 第三优先级：单机可恢复多 rollout 实验运行器

真实仓库任务和 Docker backend 会显著增加运行时间和失败类型。第三版不需要实现 GLM-5 或 DeepSeek V4 级别的异步 rollout service，但必须把第二版的顺序 Experiment Runner 升级为单机可恢复 runner。

纳入第三版的原因：

- 解决第二版 ExperimentConfig 不能 resume 的问题。
- 避免一次真实仓库任务失败或 provider transient error 破坏整个实验。
- 为后续更大规模 rollout service 留出正确状态模型。
- 提高训练轨迹采集的可运营性和审计性。

最小可交付物：

- 新增 `ExperimentResumeManifest`，记录 experiment id、config hash、run specs、run state、checkpoint time、resume policy、retry policy 和 failure summary。
- run-level 状态至少包括 `pending`、`running`、`completed`、`failed`、`skipped`、`interrupted`。
- 每个 run 在开始、baseline 后、agent loop 前、agent loop 后、final verifier 后、export 后写 checkpoint 或状态更新。
- resume 时跳过 completed runs，继续 pending/interrupted runs，对 failed runs 按 retry policy 决定是否重试。
- 区分 transient provider failure、Docker infrastructure failure、environment setup failure、deterministic verifier failure 和 task quality failure。
- 支持有限本地并行，例如 `max_parallel_runs`，默认仍为 1。并行必须有 run directory lock，不能让两个 worker 写同一 run directory。
- 支持同条件多 rollout preference baseline：至少对一个任务生成两个或更多可比较 rollout，并通过第二版 compare scope 硬门控生成一组 trainable preference pair，或者输出明确的 `preference_pair_blocked_distribution` 证明为什么没有合格 pair。

机器验收证据：

- `experiment_resume_manifest.json`：记录每个 run 的状态、attempts、checkpoint refs、failure category 和 resume action。
- `run_checkpoint_manifest.json`：记录每个 run 的 checkpoints 和 sha256。
- `interrupted_run_diagnostics.json`：记录被中断 run 是否有完整 tool result pairing、artifact manifest、partial metadata 和 resume eligibility。
- `inspect-experiment-resume --assert-resumable`：构造一次中断实验，恢复后跳过 completed runs，继续 pending runs，并保留原 run evidence。
- `failure_distribution_report.json`：统计 provider transient、environment、verifier、permission、tool protocol、context limit 等失败类别。
- `preference_pair_baseline_report.json`：记录同条件多 rollout 的 chosen/rejected、compare key、blocked reasons 和 training export eligibility。

主要风险：

- resume 容易被夸大为任意 turn 恢复。第三版只应承诺 run-level resume 和 checkpoint-aware experiment resume，不承诺 KV cache resume、token-granular write-ahead logging 或任意中间工具进程恢复。
- 并行容易破坏轨迹顺序。第三版只能做 limited local parallelism，并且每个 run directory 独立写入，artifact id 和 events 顺序在 run 内保持确定。

### 4.4 第四优先级：上下文管理、压缩和长轨迹诊断

第二版已有 `ContextManager`，可以写 prepared messages、content replacement state 和 context event。第三版不应该实现完整 Claude Code auto compact 或 session memory 系统，但应该把长轨迹诊断从“内部机制”升级为可验收能力。

纳入第三版的原因：

- 真实仓库任务会产生更长文件读取、搜索结果和测试输出。
- 工业界报告都强调 long rollout、context management、noise-aware filtering 和 unfinished trajectory penalty。
- 训练导出必须能证明 observation 来自当时模型实际可见的 prepared messages，而不是导出时重新摘要。

最小可交付物：

- 新增或强化 `ContextCompactionFacts`，记录 token estimate、tokens before/after、compact policy、kept message ids、dropped message ids、replaced tool result ids、summary artifact refs 和 prepared messages hash。
- 支持 deterministic tool observation compaction：keep recent turns、keep recent test results、replace old tool output with stable artifact-backed preview。
- 新增长轨迹诊断：repeated tool call detection、repeated edit detection、no progress detection、context limit failure diagnostics、max output recovery failure、unfinished trajectory classification。
- 最小完成定义必须同时满足两个样例：至少一个真实长工具输出任务触发 context compaction，并且至少一个 long rollout diagnostics 样例产生 no progress、repeated tool call 或 context limit 诊断。不能用 long rollout diagnostics 替代 context compaction。
- 支持 continuation run，但必须创建新的 run id，记录 `parent_run_id`、`continuation_reason` 和 `resume_from`，不能覆盖原 run。
- 训练导出继续使用对应 `context_revision` 的 prepared messages artifact，不能使用最终压缩状态重写历史 observation。

机器验收证据：

- `context_compaction_report.json`：至少一个长工具输出任务真实触发 compaction，并记录 before/after、替换列表、prepared messages hash、observation source 和 training export context revision。
- `long_rollout_diagnostics.json`：至少一个 no progress、repeated tool call 或 context limit 样例有结构化诊断。这个报告不能替代 `context_compaction_report.json`。
- `inspect-context-report --assert-consistent`：检查 tool call / tool result pairing 在压缩后仍然完整，prepared messages ref 存在且 hash 匹配。
- export audit 新增 `prepared_messages_context_revision_valid`、`context_compaction_facts_valid` 和 `observation_matches_prepared_messages` 检查项。

主要风险：

- 语义压缩容易引入不可复现摘要。第三版应优先使用确定性 preview replacement；如果引入 LLM summary，默认只能 diagnostic-only，并且 summary prompt、summary model、summary input hash、summary output artifact 都必须记录。
- continuation 容易被误写成 session resume。第三版只承诺 continuation run，不承诺恢复任意中间 turn 或 provider KV cache。

### 4.5 计划内增强：Hook System 最小审计版

Hook System 对训练 Harness 有价值，但不是第三版主线。Claude Code 的 hook、插件、技能、MCP 能力非常完整，直接复制会让 RepoHarness 偏离“训练轨迹基础设施”的核心。因此第三版建议把 hook 放入计划内增强，而不是最小完成定义。

建议范围：

- 支持 `before_model_call`、`after_model_call`、`before_tool`、`after_tool`、`tool_error`、`before_verifier`、`after_verifier` 七类最小 hook event。
- `HookPolicy` 进入 `run_config_facts.json` 和最终 `run_metadata.json`。
- hook 输出默认只进入 audit artifact，不进入模型上下文。
- hook 可以记录诊断、阻断工具或标记 policy violation，但不能改写 reward、final verifier fact、training eligibility 主状态或历史 transcript。
- hook 失败必须有结构化 `hook_error`，不能破坏 tool result pairing。
- 如果 hook 需要生成额外上下文、synthetic tool result 或 transcript repair artifact，第三版默认只能把它们作为 audit / diagnostic evidence，不能把它们作为模型可见上下文、训练目标或正式 tool result。

机器验收证据：

- 如果启用 hook 增强，则必须生成 `hook_audit_report.json` 和 `hook_policy_snapshot.json`。
- 如果启用 hook 增强，则至少一个 before_tool 阻断样例、一个 `hook_error` 样例和一个 after_verifier 诊断样例必须通过 tool result pairing 检查。
- 如果第三版最小完成没有启用 hook 增强，V3 核心验收不要求 hook 样例；`inspect-v3-acceptance --assert-complete` 只需要确认 hook 未启用状态被明确记录，且没有未标记的 hook-generated observation 进入训练 payload。

推迟完整插件市场和完整 MCP 生态。第三版的 hook 只是生命周期审计扩展点，不是产品插件平台。

### 4.6 计划内增强：核心失败诊断和更强 reward / metrics 分析

增强 reward 和 metrics 对训练数据价值很高，而且实现风险低于完整 MCP 或 LSP。第三版应把“最低失败分类和训练过滤所需字段”纳入核心验收，把 penalty 权重、reward hacking 深度分析和复杂统计放入计划内增强。这样既能保证真实仓库轨迹有基本训练数据质量，又不会把第三版扩大成新的 reward model 或强化学习算法项目。

核心验收字段至少包括：

- `patch_size`
- `files_changed`
- `tool_call_count`
- `test_run_count`
- `invalid_tool_call_count`
- `unfinished_trajectory`
- `permission_violation_count`
- `regression_detected`
- `environment_failure_category`
- `parser_low_confidence`
- `no_patch_generated`
- `provider_transient_failure`
- `deterministic_verifier_failure`
- `context_limit_failure`
- `no_progress_detected`

计划内增强字段可以包括：

- edit churn、repeated edits、patch locality。
- invalid tool call penalty、unfinished trajectory penalty、permission violation penalty。
- regression penalty、reward hacking suspected、public tests pass but hidden tests fail。
- dependency setup instability score、environment flakiness score、复杂失败聚类和复杂过滤统计。

机器验收证据：

- `failure_diagnostics_core_report.json`：核心失败分类和训练过滤字段，属于 V3 最小完成定义。
- `failure_distribution_report.json`：核心失败分布报告，属于 V3 最小完成定义。
- `inspect-reward-diagnostics --assert-core-complete`：只断言核心字段完整，不强制要求 penalty 权重或 reward hacking 深度分析。
- `enhanced_reward_diagnostics.json`：可选增强产物。只有启用增强 reward diagnostics 时才生成，不能作为 V3 核心验收的必需条件。
- export audit 证明这些诊断只作为 metadata 或 filtering evidence，不把 hidden tests、gold patch 或 provider raw response 带入训练 payload。

### 4.7 明确推迟：MCP、LSP、子代理和大规模 rollout 集群

以下能力不进入第三版核心范围：

- 完整 MCP 生态和动态外部工具市场。
- 运行中动态改变工具集合、工具参数 schema 或工具权限边界。若第三版做 MCP 只读预留，也只能保存冻结的 tool contract snapshot，不能把动态 MCP 生态作为核心交付。
- LSP 诊断和代码智能服务。LSP 对产品体验有价值，但不是第三版训练 Harness 的最短路径。
- 后台子代理、agent swarm、parallel agent reinforcement learning、agent-to-agent mailbox、自动 worktree 分叉。
- 大规模异步 rollout service、远程 worker 平台、可抢占分布式 rollout、KV cache resume、token-granular write-ahead logging。
- GUI、browser、computer-use benchmark。
- LLM judge 或 reward model 训练的完整闭环。
- 默认 session memory、跨实验长期用户记忆和产品形态的 resume / recovery UI。第三版只需要 run-level 和 experiment-level provenance，不需要复刻 Claude Code 的会话产品能力。

这些能力可以在对象模型中保留扩展余地，但第三版文档、验收和简历叙事不应该把它们写成已交付或即将交付的核心成果。

## 5. V3 对象模型和接口演进

第三版应该沿用第二版对象模型，避免推翻 `RunConfigFacts`、`RunMetadata`、`WorkspaceBackendFacts`、`SourceCheckoutFacts`、`ExperimentConfig`、`ContextManager` 和 export audit。建议新增或扩展以下对象。

Claude Code 参考源码反复体现一个工程纪律：模型可见的 tool contract、工具调用、工具结果和权限判断必须形成可审计闭环。第三版应把第二版已有的 tool schema snapshot 提升为更严格的 `ToolContractSnapshot`，并明确 synthetic tool result、transcript repair、hook-generated observation 都只能默认作为 diagnostic artifact，不能伪装成当时模型实际看到的正式工具结果。

### 5.1 DockerBackendFacts

建议字段：

- `schema_version`
- `backend = "docker"`
- `backend_version`
- `docker_cli_version`
- `docker_server_version`
- `docker_desktop_version`
- `docker_compose_version`
- `docker_context`
- `image_ref`
- `image_id`
- `platform`
- `backend_platform = "linux/arm64"`
- `image_build_mode`
- `cross_arch_emulation_used`
- `network_policy`
- `mount_policy`
- `user_policy`
- `workdir_policy`
- `cleanup_policy`
- `container_runtime_available`
- `production_sandbox_claimed = false`

### 5.2 ContainerExecutionFacts

建议字段：

- `execution_id`
- `run_id`
- `task_id`
- `phase`：`source_checkout`、`setup`、`agent_tool`、`feedback_verifier`、`final_patch_capture`、`verification_workspace`、`final_verifier`
- `container_id`
- `image_ref`
- `image_id`
- `command`
- `container_workdir`
- `container_path`
- `host_artifact_path_status`
- `mounts`
- `network_mode`
- `timeout_sec`
- `exit_code`
- `duration_ms`
- `stdout_artifact_ref`
- `stderr_artifact_ref`
- `interrupted`
- `cleanup_status`

### 5.3 RealRepositorySourceFacts

建议字段：

- `source_kind`
- `source_type`：`local_git_repository`、`local_archive`、`public_snapshot_archive`
- `remote_url`
- `base_commit`
- `current_commit`
- `archive_sha256`
- `source_tree_hash`
- `dataset_or_source_revision`
- `working_tree_clean`
- `dirty_snapshot_allowed`
- `remotes_stripped`
- `branches_stripped`
- `tags_stripped`
- `decontamination_status`
- `decontamination_metadata_ref`
- `source_materialization_policy_version`

### 5.4 TaskAdapterFacts

建议字段：

- `adapter_name`
- `adapter_version`
- `upstream_dataset_name`
- `upstream_instance_id`
- `upstream_split`
- `upstream_dataset_revision`
- `conversion_policy_version`
- `input_ref`
- `output_task_ref`
- `issue_statement_hash`
- `final_only`
- `visibility_policy`
- `decontamination_status`
- `decontamination_metadata_ref`

### 5.5 SweBenchLikeTaskFacts

建议字段：

- `task_style = "swebench_like"`
- `dataset_name`
- `dataset_revision`
- `split`
- `instance_id`
- `repo`
- `version`
- `issue_statement_ref`
- `base_commit`
- `environment_setup_commit`
- `repo_source_ref`
- `test_patch_ref`
- `test_patch_sha256`
- `verifier_patch_ref`
- `fail_to_pass_tests`
- `pass_to_pass_tests`
- `empty_test_evidence_allowed = false`
- `public_tests`
- `hidden_tests_policy`
- `final_only_policy`
- `environment_spec_hash`
- `docker_platform`
- `docker_image_build_mode`
- `arm64_compatibility_status`
- `verifier_parser_policy_version`
- `decontamination_status`
- `benchmark_comparability = "not_public_leaderboard_comparable"`

### 5.6 ExperimentResumeManifest

建议字段：

- `experiment_id`
- `experiment_config_path`
- `experiment_config_sha256`
- `resume_policy_version`
- `retry_policy`
- `max_parallel_runs`
- `generated_at`
- `updated_at`
- `runs`
- `state_distribution`
- `failure_distribution`
- `completed_run_refs`
- `pending_run_specs`
- `interrupted_run_refs`

每个 run entry 至少包含：

- `run_id`
- `task_id`
- `rollout_index`
- `model_alias`
- `scaffold_id`
- `status`
- `attempt`
- `run_dir`
- `last_checkpoint_ref`
- `failure_category`
- `failure_type`
- `retryable`
- `resume_action`

### 5.7 RunCheckpoint

建议字段：

- `checkpoint_id`
- `run_id`
- `checkpoint_type`：`created`、`baseline_completed`、`agent_loop_started`、`agent_loop_completed`、`final_patch_frozen`、`final_verifier_completed`、`export_completed`、`interrupted`
- `created_at`
- `run_config_facts_ref`
- `run_metadata_ref`
- `events_offset`
- `transcript_offset`
- `artifact_manifest_ref`
- `workspace_snapshot_ref` 或 `final_patch_ref`
- `resume_eligibility`

### 5.8 ContextCompactionFacts

建议字段：

- `context_revision`
- `context_policy_version`
- `token_estimator_version`
- `tokens_before`
- `tokens_after`
- `compact_strategy`
- `kept_message_ids`
- `dropped_message_ids`
- `replaced_tool_result_ids`
- `summary_artifact_refs`
- `content_replacement_state_hash`
- `prepared_messages_ref`
- `prepared_messages_sha256`
- `tool_pairing_validation`
- `training_export_observation_source`

### 5.9 HookPolicy

建议字段：

- `hook_policy_version`
- `enabled`
- `configured_events`
- `hook_sources`
- `model_context_visibility_default = "audit_only"`
- `can_block_tool`
- `can_modify_reward = false`
- `can_modify_verifier_facts = false`
- `can_modify_training_eligibility = false`
- `failure_policy`

### 5.10 ToolContractSnapshot

建议字段：

- `tool_contract_snapshot_id`
- `tool_contract_version`
- `tool_names`
- `tool_schema_refs`
- `tool_schema_sha256`
- `permission_policy_ref`
- `workspace_backend_ref`
- `context_policy_ref`
- `dynamic_tool_changes_allowed = false`
- `mcp_tool_contract_frozen`
- `synthetic_tool_results_policy = "diagnostic_only"`
- `transcript_repair_policy = "diagnostic_only"`
- `tool_call_result_pairing_policy`
- `tool_contract_visibility`

### 5.11 CoreFailureDiagnostics

建议在第二版 `FailureDiagnostics` 基础上扩展：

- `patch_size`
- `files_changed`
- `tool_call_count`
- `test_run_count`
- `invalid_tool_call_count`
- `permission_violation_count`
- `regression_detected`
- `environment_failure_category`
- `environment_unstable`
- `docker_backend_failure`
- `container_timeout`
- `source_materialization_failed`
- `dependency_setup_failed`
- `parser_low_confidence`
- `public_tests_pass_hidden_tests_fail`
- `unfinished_trajectory`
- `no_patch_generated`
- `no_progress`
- `repeated_tool_call_loop`
- `reward_hacking_suspected`

### 5.12 EnhancedRewardDiagnostics

这是计划内增强对象，不属于第三版最小完成定义。建议字段：

- `reward_diagnostics_version`
- `base_reward_ref`
- `patch_size_penalty`
- `edit_churn_penalty`
- `invalid_tool_call_penalty`
- `unfinished_trajectory_penalty`
- `permission_violation_penalty`
- `regression_penalty`
- `reward_hacking_penalty`
- `environment_failure_neutralized`
- `diagnostic_only_reasons`
- `training_eligibility_effect`

## 6. V3 机器产物和审计证据

第三版新增或强化的机器产物建议如下：

- `docker_backend_status.json`：全局 Docker backend 状态和 evidence refs。
- `container_execution_facts.json` 或 `container_execution_facts/*.json`：容器执行事实。
- `docker_phase_coverage_matrix.json`：逐 run 和逐 phase 验证 Docker execution facts 覆盖 source checkout、setup、agent tool、test、final patch、verification workspace 和 final verifier。
- `source_materialization_report.json`：真实仓库 source materialization 汇总。
- `task_adapter_facts.json`：adapter 输入输出、转换策略和 final-only policy 事实。
- `real_repository_task_manifest.json`：真实仓库任务集合 manifest。
- `swebench_like_task_manifest.json`：SWE-Bench-like 小子集 manifest。
- `experiment_resume_manifest.json`：可恢复实验状态 manifest。
- `run_checkpoint_manifest.json`：run-level checkpoint 汇总。
- `interrupted_run_diagnostics.json`：中断运行诊断。
- `failure_diagnostics_core_report.json`：核心失败分类、训练过滤字段和最小 reward metadata。
- `failure_distribution_report.json`：失败分布报告。
- `context_compaction_report.json`：上下文压缩和 prepared messages 证据。
- `long_rollout_diagnostics.json`：重复工具、无进展、上下文限制等诊断。
- `tool_contract_snapshot.json`：工具名称、参数 schema、权限策略、上下文策略、动态工具变更禁用状态和 synthetic result policy。
- `hook_policy_snapshot.json`：如果启用 hook，记录 hook policy。
- `hook_audit_report.json`：如果启用 hook，记录 hook 执行与阻断事实。
- `enhanced_reward_diagnostics.json`：如果启用增强 reward diagnostics，记录 reward penalty、reward hacking suspected 和复杂过滤统计；未启用时不作为 V3 核心验收必需产物。
- `preference_pair_baseline_report.json`：同条件多 rollout preference baseline 证据。
- `acceptance_bundle_manifest.json`：不可变验收包清单，绑定验收报告、命令日志、输入 evidence refs、export roots、文档摘要和 sha256。
- `v3_acceptance_report.json`：全局第三版验收报告。

第三版还需要新增或扩展只读 inspect 命令。建议至少包括：

- `inspect-v3-acceptance --assert-complete`
- `inspect-workspace-backend --assert-docker-backend`
- `inspect-v3-task-set --assert-complete`
- `inspect-experiment-resume --assert-resumable`
- `inspect-context-report --assert-consistent`
- `inspect-reward-diagnostics --assert-core-complete`
- `inspect-acceptance-bundle --assert-immutable`

这些命令必须重新读取 evidence refs、校验 sha256、检查关键字段和负例，而不能只信任最终 summary。

## 7. V3 成功标准

### 7.1 产品能力验收

- Docker backend 端到端跑通 replay task 和 mock provider task；有真实 provider 凭证时，真实 provider smoke 也必须在 Docker backend 下 accepted。
- Docker mode 下 source checkout、setup、agent workspace、`run_tests`、final patch、verification workspace 和 formal final verifier 都有机器可审计 execution facts。
- `docker_phase_coverage_matrix.json` 覆盖 source checkout、setup、agent tool、`run_tests`、final patch capture、verification workspace 和 formal final verifier，inspect 命令不能只检查 summary。
- 接入至少 3 个真实 repository-level task，并记录 source hash、base commit、environment spec、decontamination status 和 verifier evidence；其中至少 1 个必须来自公开仓库固定 commit 或预下载公开归档。
- 接入至少 3 个 SWE-Bench-like task，默认从公开 SWE-bench Lite 的 test split 手工选择；每个任务必须记录 dataset name、dataset revision、split、instance_id、base_commit、test_patch hash、FAIL_TO_PASS 和 PASS_TO_PASS，或记录具备同等测试证据的 verifier patch。
- 至少一个真实 repository-level task 和至少一个 SWE-Bench-like task 必须在 Docker backend 下端到端完成，覆盖 source checkout、setup、agent tools、final patch freeze、verification workspace strict patch replay 和 formal final verifier。
- Experiment runner 支持 resume，能够跳过 completed runs、继续 pending 或 interrupted runs，并记录 retry / skip 决策。
- 至少一个长工具输出任务真实触发 context compaction，并保留 prepared messages hash、observation source evidence 和 training export context revision。
- 至少一个 long rollout diagnostics 样例产生 no progress、repeated tool call 或 context limit 诊断。这个样例不能替代 context compaction 样例。
- 至少一个同条件多 rollout preference baseline 生成合格 preference pair，或者输出机器可审计的硬门控阻断分布。若第三版最终没有生成任何合格 pair，必须把原因列为 V3 残余风险，不能只把 skipped 当作训练偏好数据成功。

### 7.2 研究评测验收

- 能在同一任务、同一 verifier、同一工具协议下比较不同 rollout、不同 scaffold 或不同模型配置。
- 评测报告包含 success rate、fail-to-pass pass rate、pass-to-pass preservation rate、average turns、average tool calls、test run count、patch size、files changed、timeout rate、permission denial rate、invalid tool call rate、environment failure distribution。
- 能区分模型失败、provider transient failure、Docker backend failure、environment setup failure、task quality failure 和 deterministic verifier failure。
- 核心 failure / reward diagnostics 至少覆盖 `invalid_tool_call_count`、`unfinished_trajectory`、`regression_detected`、`environment_failure_category`、`parser_low_confidence`、`no_patch_generated`、`context_limit_failure` 和 `no_progress_detected`。
- SWE-Bench-like 小子集结果不和公开榜单直接比较，只作为 adapter 和 harness 能力验收。

### 7.3 工程质量验收

- 第二版全量测试继续通过，第二版 `inspect-v2-acceptance --assert-complete` 仍可读取历史验收产物。
- Docker backend 有单元测试、集成测试和端到端 smoke test；Docker 不可用时不能伪装通过。
- 实验 resume 有中断恢复负例测试。
- `acceptance_bundle_manifest.json` 必须绑定 `v3_acceptance_report.json`、生成命令日志、输入 evidence refs、export audit roots、文档摘要和 sha256。`inspect-v3-acceptance --assert-complete` 必须拒绝报告和命令日志、输入 artifact 或文档摘要之间的关键统计漂移。
- export audit 继续证明 hidden tests、gold patch、provider raw response、reasoning summary、Authorization marker、完整 decontamination metadata 和本机绝对路径不进入正式训练 payload。
- 每个已解析 tool call 仍然必须有终态 tool result；context compaction、provider fallback 和 interrupted run 都不能破坏配对不变量。
- 如果启用 hook 增强，before_tool 阻断、`hook_error` 和 after_verifier 诊断样例都不能破坏 tool result pairing。如果未启用 hook 增强，V3 核心验收不要求 hook 样例，只要求 hook disabled facts 和训练 payload 污染检查。
- synthetic tool result、transcript repair、hook-generated observation 和 MCP prototype 工具快照必须被显式标记；除非后续单独设计并验收，否则它们不能进入正式训练目标，也不能替代当时模型实际看到的 tool result。

### 7.4 训练数据质量验收

- SFT、RL rollout、preference export 继续生成 `export_manifest.json`、`audit_report.json` 和 `audit_report.md`。
- Docker facts、source facts、SWE-Bench-like facts、resume facts 和 context facts 进入 export metadata 或 audit report，但不会把隐藏评测内容带入模型可见 payload。
- diagnostic-only、skipped、invalid 样本不会进入正式训练 JSONL。
- preference pair 继续受 compare scope 硬门控保护，不能因为同一 task id 就跨 source hash、verifier、tool protocol、context policy、scaffold、模型或预算误配。

## 8. V3 非目标

第三版明确不做以下事项：

- 不实现生产级安全沙箱。
- 不承诺沙箱逃逸防护、多租户隔离、企业权限平台或操作系统级强制断网。
- 不实现完整 SWE-Bench 榜单复现。
- 不声称结果可以和公开 SWE-Bench 榜单直接比较。
- 不实现大规模分布式 rollout 集群。
- 不实现新的强化学习算法、训练调度器或参数更新流程。
- 不实现完整插件市场。
- 不实现完整 MCP 生态。
- 不实现远程 worker 平台。
- 不实现后台多智能体 swarm、agent-to-agent mailbox 或 parallel agent reinforcement learning。
- 不实现 GUI、browser、computer-use benchmark。
- 不声称训练出了 coding agent。
- 不复刻 Claude Code、Cursor、OpenHands 或任何生产级 coding agent 产品。

## 9. V3 风险和保守表述

第三版必须保持可信边界。

可以写：

- Docker-based executable repository environment。
- Container execution facts。
- Repository-level executable task adapter。
- SWE-Bench-like small subset。
- Issue-style executable task。
- Single-machine resumable experiment runner。
- Verifier-aligned reward metadata。
- Provenance-rich trajectory logging。
- Auditable SFT / RL rollout / preference export。

不要写：

- Production-grade sandbox。
- 完整网络隔离。
- 沙箱逃逸防护。
- 完整 SWE-Bench 复现。
- 公共榜单级评测平台。
- 工业级分布式 rollout service。
- 新强化学习算法。
- 已训练出 coding agent。
- 复现 Claude Code 或 Cursor 产品。

如果引入 LLM judge，默认只能是 diagnostic judge，不能作为正式 reward 或 training eligibility 主事实来源，除非后续单独设计 judge audit、bias check 和 verifier alignment policy。

如果真实 provider 运行通过，只能说明真实 provider 可以驱动 RepoHarness 任务运行并通过 formal final verifier；不能说明模型经过了训练，也不能说明 harness 达到生产代理产品能力。

如果 SWE-Bench-like 小子集在 Apple Silicon / `linux/arm64` Docker 后端上通过，只能说明 RepoHarness 在该本机 Docker 环境中完成了 adapter、Docker execution facts、test patch / verifier patch 和 final verifier 证据链；不能说明结果可与 SWE-Bench Lite 或 Verified 官方榜单比较，也不能说明 x86_64 官方评测环境已经复现。

## 10. 建议实施顺序

第三版建议按下面顺序实施。这里是路线建议，不是详细实施计划。

0. 进入第三版实现前的 SWE 任务可实现性实验：按 `docs/v3/swe-task-feasibility-experiment-plan.md` 先验证本机 Docker Desktop、Apple Silicon / `linux/arm64`、x86 仿真、官方 SWE-Bench harness、gold patch evaluation 和候选任务选择。只有至少 3 个 SWE-Bench-like 候选任务通过实验，或者明确进入 Yellow 降风险路径，后续 implementation plan 才能把这些任务写入第三版最小完成定义。
1. 第三版 schema 和 acceptance skeleton：定义 Docker facts、real repository facts、SWE-Bench-like facts、resume manifest、checkpoint、context compaction facts、core failure diagnostics、optional enhanced reward diagnostics 和 `v3_acceptance_report.json` schema。
2. Docker Workspace Backend：先跑通 replay task 和 mock provider task，再接入 credential-gated real provider smoke；同时完善 `inspect-workspace-backend --assert-docker-backend`。
3. 真实仓库任务和 SWE-Bench-like 小子集：先支持本地归档和本地 Git 仓库快照，再接至少 1 个公开仓库固定 commit 或预下载公开 archive；SWE-Bench-like 小子集默认从公开 SWE-bench Lite test split 手工选择 3 个稳定任务，并优先筛选 Apple Silicon / `linux/arm64` Docker 后端可运行样例。
4. 可恢复 Experiment Runner：加入 run state、checkpoint manifest、resume 命令、failure distribution、同条件多 rollout preference baseline 和有限本地并行。
5. 长轨迹上下文和失败诊断：在真实仓库任务上至少触发一次真实 context compaction，同时产生至少一个 no progress、repeated tool call 或 context limit 的 long rollout diagnostics 样例。
6. Export audit 和 acceptance 收口：扩展导出审计项，把 real provider run exports 纳入全局训练 payload scan，生成 `acceptance_bundle_manifest.json` 和 `v3_acceptance_report.json`，新增 `inspect-v3-acceptance --assert-complete`。
7. 计划内增强：如果前六步稳定，再实现最小 hook audit、penalty 权重、reward hacking 深度分析和更丰富 reward diagnostics。核心失败分类字段不等到第七步，应该伴随真实仓库任务和可恢复 runner 一起进入验收。

## 11. 子代理审查结论整合

本次范围探索安排了多个只读子代理视角，并结合本地阅读形成本文判断。

V2 基线和残余风险视角的结论是：第二版已经完成 run metadata、export audit、多 rollout、provider adapter、task set 和 Docker interface-only 验收；第三版最应处理 Docker backend、真实仓库任务、SWE-Bench-like 小子集、resume 能力、真实 provider export evidence 纳入全局验收，以及 acceptance evidence bundle 不可变绑定。本文采纳这个方向，把 Docker backend 和任务来源升级列为第一、第二优先级，并把 acceptance drift 作为第三版验收风险写入文档。

Claude Code 参考项目映射视角的结论是：Claude Code 的 query loop、tool execution lifecycle、permission 分层、tool result pairing、large output artifact 化、context compaction、resume、hooks、AgentTool、MCP、session memory 和 SDK / print mode 都有参考价值。但 RepoHarness 不应复制交互式终端 UI、完整插件市场、完整 MCP、远程会话、默认 session memory、运行中动态工具生态和后台 agent swarm。本文采纳其中的工程纪律，把 tool result pairing、权限与执行分层、`ToolContractSnapshot`、hook 最小审计、context compaction facts、synthetic result diagnostic-only 和子代理非目标写入第三版边界。

技术报告方向映射子代理的结论是：第三版最适合吸收 DeepSeek V4 的 rollout log / provenance / execution substrate，GLM-5 的 rollout orchestrator 和 failure filtering，Qwen3-Coder 的 GitHub PR executable task、fail-to-pass / pass-to-pass 和 reward hacking blocker，KAT-Coder / KwaiEnv 的 dataset / sandbox / scaffold / verifier 解耦，Cursor Composer 的真实 codebase environment、long rollout 和 code quality metrics，以及 LongCat / Kimi / Tongyi 的长程上下文与噪声感知训练思想。本文采纳这些方向，但全部降维为单机、可审计、可验收版本。

Docker 和真实仓库任务可行性视角的结论是：现有代码已有 `WorkspaceAdapter` protocol、`WorkspaceBackendFacts`、repo materialization、command policy、parser policy 和 strict patch replay final verifier；因此第三版实现 Docker backend 和真实仓库小子集是可行的。但当前实际调用面不只包括协议中的生命周期方法，还包括命令执行、路径解析、文件读写、patch apply、final patch capture 和 verification workspace patch replay；第三版必须引入 backend factory 并新增容器执行事实、真实 source facts、task adapter facts、SWE-Bench-like task facts 和更强验收命令。本文采纳这些作为对象模型和机器产物要求。

最终范围审查子代理的结论是：未发现 P1 阻断问题，但发现三个 P2 问题，分别是第二版 evidence drift 表述过期、Docker backend 和真实仓库任务缺少组合验收、reward / failure diagnostics 的核心与增强边界不够硬。本文已经按这些意见修订：更新第二版 evidence drift 表述，新增 Docker repository-level combination smoke，拆分核心 failure / reward diagnostics 字段和计划内增强字段。修订后，本文可以作为第三版范围文档使用。

第二轮范围审查进一步指出：真实仓库任务口径仍可能被本地 fixture 满足，SWE-Bench-like 小子集来源和硬门槛需要更明确，上下文压缩不能被 long rollout diagnostics 替代，reward diagnostics 需要拆成核心报告和可选增强报告，hook 作为计划内增强时验收必须条件化，实时 Git HEAD 不适合写死在长期范围文档中，Docker backend 需要 phase coverage matrix。本文已经按这些意见继续收紧：至少 1 个真实仓库任务必须来自公开仓库固定 commit 或预下载公开归档；SWE-Bench-like 小子集默认来自公开 SWE-bench Lite test split；context compaction 和 long rollout diagnostics 同时作为最小完成要求；新增 `failure_diagnostics_core_report.json` 和可选 `enhanced_reward_diagnostics.json` 的边界；hook 验收改为“启用时强制、未启用时不要求样例”；移除固定 HEAD；新增 `docker_phase_coverage_matrix.json`。

## 12. 最终结论

第三版推荐范围是一个克制但有明显工业基础设施价值的组合：

1. 核心主线：Docker Workspace Backend、真实仓库任务、SWE-Bench-like 小子集、可恢复多 rollout 实验和长轨迹诊断。
2. 最小完成定义：Docker backend 端到端跑通 replay 和 mock provider，有凭证时跑通真实 provider；至少 3 个真实 repository-level task，其中至少 1 个来自公开仓库固定 commit 或预下载公开归档；至少 3 个 SWE-Bench-like task，默认来自公开 SWE-bench Lite test split，若因 Apple Silicon / `linux/arm64` 限制替换，替代任务必须有同等测试证据；至少一个真实 repository-level task 和至少一个 SWE-Bench-like task 在 Docker backend 下端到端完成；experiment resume 能恢复中断；至少一个同条件多 rollout preference baseline 产生合格 pair 或明确阻断分布；至少一个真实 context compaction 闭环，同时至少一个 long rollout diagnostics 样例；核心 failure / reward diagnostics 字段进入验收；export audit 继续证明隐藏字段和 provider raw artifacts 不进入训练 payload；生成不可变 `acceptance_bundle_manifest.json` 和 `v3_acceptance_report.json`，并通过 `inspect-v3-acceptance --assert-complete`。
3. 计划内增强：最小 hook audit、penalty 权重、reward hacking 深度分析、更丰富 failure distribution、复杂过滤统计和高于默认值的本地并行策略调优。
4. 明确推迟：完整 SWE-Bench 榜单、大规模异步 rollout 集群、新强化学习算法、完整 MCP / 插件市场、LSP、后台多代理 swarm、远程 worker、GUI / browser / computer-use benchmark。

如果第三版按本文范围完成，RepoHarness 可以被保守、准确地表述为：

> 一个面向软件工程智能体训练轨迹的轻量级 repository-level evaluation harness，支持 Docker-based executable repository environment、真实或半真实仓库任务、SWE-Bench-like 小子集、可恢复多 rollout、长轨迹诊断、verifier-aligned reward metadata 和可审计训练数据导出。

这条表述既能体现 agentic training infrastructure 的工程含量，也避免把项目夸大成生产级安全沙箱、完整公开榜单系统或训练框架。
