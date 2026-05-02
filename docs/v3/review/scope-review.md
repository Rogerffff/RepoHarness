# RepoHarness V3 Scope Review

## 0. 审查定位

本文记录 RepoHarness 第三版范围文档 `docs/v3/scope-and-roadmap.md` 的只读探索来源、子代理审查结论、最终审查发现和修订结果。本文不是第三版实现计划，也不是第三版完成声明。

## 1. 已阅读材料

本次范围探索阅读了第二版范围、计划、验收、walkthrough、implementation log，以及当前系统架构、Agent Loop、工具系统、workspace / sandbox、task adapter、verifier / reward、trajectory export、scaffold / multi-agent、context diagnostics 和 object model 文档。

本次范围探索也阅读了 Claude Code TypeScript 参考项目的 `AGENT.md`，并围绕 query loop、tool execution、permission system、tool result pairing、context compaction、resume / recovery、hooks、task / subagent、MCP、session memory、background task、SDK / print mode 阅读了相关源码。

本次范围探索结合 `docs/13-agentic-technical-report-reading-map.md`，把 DeepSeek V4、GLM-5、Qwen3-Coder、KAT-Coder / KwaiEnv、Cursor Composer、Kimi / LongCat / Tongyi DeepResearch 等方向降维为 RepoHarness 第三版可执行、可审计、边界清晰的工程范围。

## 2. 子代理结论摘要

V2 基线和残余风险审查结论：第二版已经完成 run metadata、export audit、多 rollout、provider adapter、task set 和 Docker interface-only 验收；第三版最应该补 Docker backend、真实仓库任务、SWE-Bench-like 小子集、experiment resume、真实 provider export evidence 纳入全局验收，以及 acceptance evidence bundle 不可变绑定。

Claude Code 参考项目映射结论：RepoHarness 应吸收 tool lifecycle、tool result pairing、权限与执行分层、large output artifact 化、context compaction、resume 边界、hook 生命周期审计和 tool contract snapshot 等工程纪律；不应复制交互式终端产品、完整 MCP、完整插件市场、默认 session memory、后台 agent swarm 或远程会话系统。

技术报告方向映射结论：第三版最适合吸收 executable environment、trajectory provenance、rollout orchestrator、failure filtering、fail-to-pass / pass-to-pass verifier、reward hacking blocker、dataset / sandbox / scaffold / verifier 解耦、long rollout diagnostics 和 code quality metrics。所有方向都应落到单机、少量样例、可审计的版本。

Docker 和真实仓库任务可行性结论：现有代码已有 workspace protocol、backend facts、repo materialization、command policy、parser policy 和 strict patch replay final verifier，但 Docker backend 需要覆盖实际调用面，包括命令执行、路径解析、文件读写、patch apply、final patch capture 和 verification workspace patch replay；真实仓库和 SWE-Bench-like 任务需要新增 source facts、task adapter facts 和组合验收。

最终范围审查结论：未发现 P1 阻断问题。审查发现三个 P2 问题，分别是第二版 evidence drift 表述过期、Docker backend 与真实仓库任务可以被分开满足、reward / failure diagnostics 核心与增强边界不够硬。范围文档已经按这三点修订。

## 3. P2 问题和修订结果

第一项 P2：第二版 export audit 统计漂移描述过期。

修订结果：范围文档现在明确说明 `docs/v2/final-acceptance.md` 已经同步为 `sft_jsonl = 6`、`rl_jsonl = 6`、`preference_jsonl = 5`，与当前 `v2_acceptance_report.json` 一致；仍需记录的是命令日志旧摘要 `3/3/2` 与当前机器报告之间的不可变验收包绑定风险。

第二项 P2：Docker backend 与真实仓库任务缺少组合验收。

修订结果：范围文档已经新增 Docker repository-level combination smoke，初版要求至少一个真实 repository-level task 和至少一个 SWE-Bench-like 或等价 issue-style task 在 Docker backend 下完成 source checkout、setup、agent tools、final patch freeze、verification workspace strict patch replay 和 formal final verifier。第二轮审查后进一步收紧为：默认必须是 SWE-Bench-like task；只有 Apple Silicon / `linux/arm64` 平台限制导致公开 Lite 实例不可稳定运行时，才允许具备同等测试证据的 issue-style task 替代。

第三项 P2：reward / failure diagnostics 核心与增强边界不够硬。

修订结果：范围文档已经拆分核心验收字段和计划内增强字段。核心字段包括 `patch_size`、`files_changed`、`tool_call_count`、`test_run_count`、`invalid_tool_call_count`、`unfinished_trajectory`、`permission_violation_count`、`regression_detected`、`environment_failure_category`、`parser_low_confidence`、`no_patch_generated`、`provider_transient_failure`、`deterministic_verifier_failure`、`context_limit_failure` 和 `no_progress_detected`。penalty 权重、reward hacking 深度分析、复杂失败聚类和复杂过滤统计被放入计划内增强。

## 4. 多维度审查结论

- 与第二版当前能力一致：通过。文档没有把 Docker backend、真实 SWE-Bench、生产级安全沙箱或分布式 rollout 写成第二版已完成能力。
- Claude Code 映射：通过。文档吸收了工具契约、工具结果配对、权限分层、context compaction 和 hook 生命周期审计，但明确推迟完整 MCP、插件市场、默认 session memory、后台子代理和产品 UI。
- 技术报告映射：通过。文档没有空泛引用报告，而是把工业方向转化为 Docker backend、真实仓库任务、SWE-Bench-like 小子集、experiment resume、failure filtering 和 trajectory provenance。
- 可执行性：通过。第三版核心任务数量被控制在至少 3 个真实仓库任务和至少 3 个 SWE-Bench-like 任务；只有平台限制导致公开 Lite 实例不可稳定运行时，才允许具备同等测试证据的 issue-style task 替代，并且要求单机可恢复而不是分布式 rollout service。
- 机器验收证据：通过。每个核心方向都有 manifest、audit report、inspect 命令或 acceptance report 证据。
- 非目标清晰度：通过。文档明确排除生产级安全沙箱、完整 SWE-Bench 榜单、大规模分布式 rollout、新强化学习算法、完整 MCP、完整插件市场、远程 worker、后台多智能体 swarm、GUI / browser / computer-use benchmark 和训练出 coding agent 的声明。
- 保守表述：通过。文档使用 Docker-based executable repository environment、SWE-Bench-like small subset、single-machine resumable experiment runner 等保守表述。
- 简历价值：通过。文档的推荐范围能体现 agentic training infrastructure 的工程含量，包括 containerized executable environment、provenance-rich trajectory logging、repository-level task adapter、failure diagnostics 和 auditable training export。

## 5. 最终审查结论

`docs/v3/scope-and-roadmap.md` 修订后可以作为 RepoHarness 第三版范围文档使用。后续如果进入实施，应单独编写 `docs/v3/implementation-plan.md`，并把范围文档中的核心交付拆成可测试、可审查、可回滚的阶段。

## 6. 第二轮范围审查修订

用户完成第二轮详细检查，并让三个只读子代理从范围一致性、可执行性和公开数据源三个角度继续审查。第二轮结论仍然是没有 P1 阻断问题，但有几项 P2 需要继续收紧。范围文档已经按这些意见修订。

### 6.1 真实仓库任务来源门槛

问题：原文允许本地受控 Git 仓库快照计入 3 个真实 repository-level task，实施时可能仍然用几个新 fixture 满足门槛。

修订结果：范围文档现在要求至少 1 个真实 repository-level task 必须来自公开仓库固定 commit 或预下载公开归档，并记录 remote URL、base commit、archive sha256、source tree hash 和 dataset/source revision。`inspect-v3-task-set --assert-complete` 必须拒绝 3 个任务全部来自本地新建 fixture 的情况。

### 6.2 SWE-Bench-like 小子集来源和硬门槛

问题：原文多处使用“SWE-Bench-like 或等价 issue-style task”，口径偏宽。

修订结果：范围文档现在明确默认来源是公开 SWE-bench Lite 的 test split，优先使用 `SWE-bench/SWE-bench_Lite` 或 `princeton-nlp/SWE-bench_Lite`，手工选择 3 个稳定任务，并固定 dataset name、dataset revision、split、instance_id、repo、base_commit、source archive sha256、test_patch hash、FAIL_TO_PASS、PASS_TO_PASS 和 Docker execution facts。只有 Apple Silicon / `linux/arm64` 平台限制导致公开 Lite 实例不可稳定运行时，才允许使用具备同等测试证据的 issue-style task 替代。

参考公开资料：

- SWE-Bench datasets 文档：`https://www.swebench.com/SWE-bench/guides/datasets/`
- SWE-Bench evaluation 文档：`https://www.swebench.com/SWE-bench/guides/evaluation/`
- Hugging Face 数据集页：`https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite`
- SWE-Bench GitHub README：`https://github.com/princeton-nlp/SWE-bench/blob/main/README.md`

### 6.3 Apple Silicon Docker 后端约束

问题：本机 Docker 后端是 Apple Silicon 上的 `linux/arm64`，而 SWE-Bench 官方资料推荐 x86_64，并把 arm64 支持标为 experimental。

修订结果：范围文档现在记录本机 Docker 事实：Docker Desktop 4.71.0、Docker Engine 29.4.1、Docker backend platform `linux/arm64`、Docker context `desktop-linux`、Docker Compose 5.1.3。V3 范围只承诺 RepoHarness 自己的小子集适配器验收，优先选择 arm64 可运行或可本地构建的轻量任务，并记录 image platform、build mode、本地构建、跨架构仿真和平台不兼容原因。

### 6.4 上下文压缩硬验收

问题：原文把 context compaction 和 long rollout diagnostics 写成“或”，可能允许只实现无进展诊断而不证明压缩、prepared messages hash 和 observation 来源一致。

修订结果：范围文档现在要求最小完成定义同时包含至少一次真实 context compaction 和至少一个 long rollout diagnostics 样例。`long_rollout_diagnostics.json` 不能替代 `context_compaction_report.json`。

### 6.5 Reward diagnostics 分层

问题：核心字段和增强字段仍然混杂。

修订结果：范围文档现在拆成 `failure_diagnostics_core_report.json` 和可选 `enhanced_reward_diagnostics.json`。`inspect-reward-diagnostics --assert-core-complete` 只断言核心字段，不强制要求 penalty 权重、reward hacking 深度分析或复杂过滤统计。

### 6.6 Hook 条件化验收

问题：hook 是计划内增强，但工程质量验收可能让人误以为 V3 核心必须实现 hook 样例。

修订结果：范围文档现在明确：如果启用 hook 增强，则 before_tool 阻断、`hook_error` 和 after_verifier 诊断样例必须通过 tool result pairing 检查；如果未启用 hook 增强，V3 核心验收不要求 hook 样例，只要求 hook disabled facts 和训练 payload 污染检查。

### 6.7 Docker phase coverage matrix

问题：Docker evidence refs 写得完整，但 inspect 命令需要明确逐阶段检查，避免只验证 summary。

修订结果：范围文档新增 `docker_phase_coverage_matrix.json`，要求逐 run 和逐 phase 检查 source checkout、setup、agent tool、test、final patch、verification workspace 和 final verifier 的 container execution facts。

### 6.8 V3 前置可实现性实验计划

问题：在正式进入 V3 实施前，需要先确认 SWE-Bench-like 数据选择和本机 Docker 环境可实现性，避免实施阶段才发现官方 harness、镜像构建、平台或依赖不可用。

修订结果：新增 `docs/v3/swe-task-feasibility-experiment-plan.md`。该计划把实验拆成 Level 0、Level 1 和 Level 2：Level 0 记录已完成的 Docker / Hugging Face / 磁盘预检查；Level 1 用官方 gold patch 跑 1 个纯 Python 候选任务；Level 2 选择 3 个 SWE-Bench Lite 小任务并记录 instance id、repo、base commit、test patch hash、FAIL_TO_PASS、PASS_TO_PASS、运行平台、构建日志和结果。范围文档的建议实施顺序也新增第 0 步，要求 implementation plan 先读取该实验结果。

### 6.9 可实现性实验计划可操作性修订

第三轮审查指出，`docs/v3/swe-task-feasibility-experiment-plan.md` 方向正确，但执行前仍有一个 P1 和多个 P2 需要修订。

P1：计划直接运行 `python -m swebench.harness.run_evaluation`，但当前项目环境不能假设已经安装 `swebench` 或 `datasets`。修订结果：计划新增 Level 0.5，要求在独立实验目录中创建独立虚拟环境，克隆官方 SWE-Bench，记录 SWE-Bench remote、commit sha、Python 版本、安装命令、`pip freeze`、import check 和 `run_evaluation --help` 输出。后续所有命令必须使用实验虚拟环境，不能使用当前 RepoHarness 项目环境。

P2：官方 harness 命令不够确定，可能误跑完整 300 个 test split 任务。修订结果：计划现在强制使用 `--instance_ids`，固定 `--max_workers 1`、`--timeout 1800`、`--cache_level env`、`--clean True` 和 `--report_dir`，并要求从对应实验子目录执行，避免 `logs/` 和 `evaluation_results/` 散落到仓库根目录。

P2：native `linux/arm64` 与 `linux/amd64` 仿真路径口径不够准确。修订结果：计划现在明确第一轮实验验证官方 harness 默认平台路径；普通 CLI 不能假设可以直接切换 native `linux/arm64`。如果要验证 native `linux/arm64`，必须另写补充实验，说明使用官方 API、自定义 TestSpec 或修改后的脚本。

P2：Level 1 通过标准把 resolved 和可诊断失败混在一起。修订结果：计划现在拆成 `level1_infrastructure_completed` 和 `level1_gold_patch_resolved`。只有 `level1_gold_patch_resolved = true` 可以作为 Green 路径或候选任务 accepted 的证据。

P2：`dataset_revision` 要求了但没有固定方法。修订结果：计划现在要求使用 Hugging Face dataset repo 的具体 commit sha，并把 dataset name、revision、split、row count、columns、candidate manifest sha256 和每个候选样本关键字段 sha256 写入 `hf_dataset_schema.json` 和 `candidate_task_manifest.json`。

P2：Yellow 替代任务标准偏宽。修订结果：计划现在要求替代任务必须来自公开仓库固定 commit 或预下载公开归档，并具备 remote URL、base commit、archive sha256 或 source tree hash、issue statement、verifier patch 或 test patch、baseline failing evidence、gold patch passing evidence、fail-to-pass / pass-to-pass 或等价测试命令，以及 Docker execution logs。

P3：timeout、重试和 Docker 清理策略需要具体化。修订结果：计划现在默认 timeout 为 1800 秒，Level 1 每个候选任务最多 2 次尝试，Level 2 每个任务最多 1 次重试；实验前后记录 `docker system df`，只允许清理本实验创建的资源，禁止无边界执行 `docker system prune -a`。

第四轮复查继续指出两个问题。第一，计划虽然记录 Hugging Face dataset revision，但官方 harness 命令仍传远程 dataset name，会导致 evaluation 阶段重新读取浮动默认分支。修订结果：计划现在要求从固定 revision 加载数据后导出本地 JSONL 快照，Level 1 / Level 2 的 `--dataset_name` 必须指向 `dataset/level1_dataset.jsonl` 或 `dataset/level2_dataset.jsonl`，prediction 文件也必须从同一个本地快照生成。第二，`--report_dir` 在不同官方 harness 版本中的行为可能不完全一致。修订结果：计划现在要求 stdout / stderr 显式重定向到实验日志文件，并在运行后扫描 `official_reports/`、`logs/` 和 `evaluation_results/`，生成 `actual_report_paths.json`，记录真实存在的报告路径。
