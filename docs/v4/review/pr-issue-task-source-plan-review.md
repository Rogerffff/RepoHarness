# RepoHarness V4 PR / Issue Task Source Plan Review

## 0. 审查对象

本文记录对 `docs/v4/pr-issue-task-source-plan.md` 的只读审查、发现、修复和最终结论。

审查目标是确认 V4 至少 4 个 PR / issue 构造任务的来源计划是否满足 RepoHarness 的核心边界：

- 来源必须公开、可审计、可冻结。
- 任务必须能在本机 Docker 中执行 baseline verifier、post-patch verifier 和 flaky probe。
- adapter-visible 输入必须与 evaluator-only evidence、上游补丁、上游新增测试和 verifier 原始证据强隔离。
- 任务选择不能把 V4 写成大规模自动 PR mining、完整 SWE-Bench 榜单复现或完整产品复刻。

## 1. 信息搜集记录

本轮先安排三个只读 subagent 分别搜集候选来源：

| 方向 | 重点 | 主要建议来源 |
| --- | --- | --- |
| Python 候选 | 小中型库、稳定测试、问题语义清楚 | `pallets/click`、`pytest-dev/pluggy`、`python-attrs/attrs`、`pypa/packaging`、`hynek/structlog` |
| JavaScript / TypeScript 候选 | 依赖可固定、测试可局部执行、避免过旧或过重工具链 | `sindresorhus/execa`、`yargs/yargs`、`chalk/chalk`、`colinhacks/zod` |
| Go / Rust 候选 | 单机 Docker 可执行、命令行或 parser 行为可验证、多语言多样性 | `spf13/cobra`、`stretchr/testify`、`pelletier/go-toml`、`sharkdp/fd`、`clap-rs/clap` |

同时使用浏览器打开 GitHub pull request 页面，并用 GitHub CLI 查询 merged pull request 元数据、base commit、merge commit、changed files、closing issue reference 和测试说明。浏览器确认的核心候选包括：

- `spf13/cobra#2356`
- `stretchr/testify#1531`
- `pelletier/go-toml#1041`
- `pallets/click#3208`
- `pytest-dev/pluggy#646`
- `sindresorhus/execa#1176`
- `yargs/yargs#2332`
- `sharkdp/fd#1805`

## 2. 审查安排

完成计划草稿后，安排三个只读 subagent 做独立审查：

| 审查方向 | 审查重点 | 结论 |
| --- | --- | --- |
| 来源和 provenance 审查 | 是否把 GitHub issue、pull request、fix commit、base commit、任务来源、无 issue 候选风险写清楚 | 发现若干 P2 / P3 问题，已修复 |
| 训练数据和污染边界审查 | 是否保护 evaluator-only evidence，是否禁止 PR diff、gold patch、provider raw response 等进入模型可见输入和训练 payload | 发现两个 P1 和两个 P2 问题，已修复 |
| 工程可执行性审查 | 是否有 Docker 可执行硬门槛，是否有足够候选余量，机器产物是否有最低字段 | 发现一个 P1、三个 P2 和一个 P3 问题，已修复 |

## 3. 主要发现和修复

### Finding A：`chalk/chalk#335` 不应占用第一批核心 accepted 名额

严重级别：P2 / P3。

问题：`chalk/chalk#335` provenance 清楚，但修复规模过小，工具链较旧，作为 V4 真实 PR / issue 构造任务的代表性不足。

修复：计划正文已把 `chalk/chalk#335` 从第一批强候选和保守最小 accepted 组合中移出，改为 JavaScript smoke / fallback accepted。JavaScript / TypeScript 的优先 accepted 候选改为 `sindresorhus/execa#1176` 或 `yargs/yargs#2332`。

### Finding B：候选表缺少冻结字段和 provenance 字段

严重级别：P2。

问题：草稿只列了 PR、issue 和变更规模，缺少 base commit、merge commit、fix patch hash、upstream test patch hash、license、adapter-visible 来源和 visibility risk 等后续 implementation plan 需要的字段。

修复：计划正文已补充第一批和第二批候选的 base commit 与 merge commit，并在机器产物章节新增 `candidate_pr_issue_inventory.jsonl` 最低字段，包括 `base_commit`、`merge_commit`、`fix_commit_url`、`fix_patch_sha256`、`upstream_test_patch_sha256`、`adapter_visible_source`、`visibility_risk` 和 `environment_lock_strategy`。

### Finding C：Docker 可执行性没有形成 accepted 前置硬门槛

严重级别：P1。

问题：草稿要求“可以在本机 Docker 中运行”，但没有定义每个 accepted 候选必须记录哪些 Docker facts，也没有明确未通过 Docker probe 的降级口径。

修复：计划正文已新增 Docker execution probe gate，要求记录 `base_image`、`image_digest`、`requested_platform`、`actual_container_arch`、`docker_memory_limit`、`docker_cpu_limit`、`disk_available_bytes`、`network_policy_by_phase`、`dependency_install_command`、`verifier_command`、`timeout_sec`、`stdout_log_ref`、`stderr_log_ref`、`exit_code` 和 `failure_category`。未通过 Docker execution probe 的候选只能进入 `diagnostic-only`、`quarantined` 或 `rejected`，不能计入 accepted / auditable。

### Finding D：候选余量不足

严重级别：P2。

问题：如果只要求 4 个候选完成全套 probe，则任何一个候选在污染扫描、flaky probe 或 Docker 重跑中失败，都会导致 V4 P0 任务构造目标没有余量。

修复：计划正文已把进入 implementation plan 前的建议门槛改为：8 到 12 个 discovery metadata，至少 6 个完成 source materialization probe，至少 6 个完成 Docker execution probe、baseline verifier、post-patch verifier 和 flaky probe，至少 5 个达到 freeze readiness，最终从中选择至少 4 个 accepted / auditable PR / issue task definitions。

### Finding E：训练导出边界和运行时可见性边界不够硬

严重级别：P1。

问题：草稿虽然区分了 `adapter_visible/` 和 `evaluator_only/`，但没有规定 agent 执行容器实际能挂载什么，也没有定义训练导出 allowlist 和 denylist。这样后续实现可能误读整个 run 目录。

修复：计划正文已新增“运行时可见性和训练导出边界”。硬规则包括：

- Agent 执行容器只能挂载 fixed base source tree、必要 dependency cache、允许的 public docs 和 `adapter_visible/task.json`。
- Agent loop、检索器、调试工具和日志上传器不得挂载或遍历 feasibility run root。
- `evaluator_only/`、`patch/`、`baseline/`、`flaky/`、`post_patch` 和 official report 目录必须位于 agent 不可见路径或独立权限域。
- 训练导出只能读取经过 schema 校验的 adapter-visible task statement、base source tree 中模型实际读取过的公开文件、agent 自己运行工具得到的可见结果和明确标记为 trainable 的观察。

### Finding F：禁止内容列表和污染扫描范围不够完整

严重级别：P2。

问题：草稿已经禁止 PR diff、fix commit、gold patch、hidden selector 和 official resolved status，但漏写 provider raw response、PR body、review comments、commit messages after base、CI raw logs、AI session URL 等高风险材料，也没有定义扫描范围和 fail-closed 条件。

修复：计划正文已扩展训练导出 denylist，并增加污染扫描范围和 fail-closed 规则。默认禁止内容包括 `evaluator_only/`、gold patch、hidden tests、上游新增测试、verifier raw output、provider raw response、PR body、PR diff、review comments、review suggestions、commit messages after base、fix commit URL、merge commit URL、LLM / Claude / Codex session URL。命中 gold patch、上游新增测试、fix commit、PR diff、hidden selector、AI coding session URL、provider raw response 或 verifier raw output 时，候选默认不能 accepted。

### Finding G：无 issue 候选和 Rust 候选需要降级口径

严重级别：P3。

问题：`colinhacks/zod#5708` 和 `clap-rs/clap#6340` 没有关联 issue；`sharkdp/fd#1805` provenance 清楚但 patch 跨多个文件，涉及命令行输出、排序和 shell 行为。

修复：计划正文已写明无 issue 候选默认不优先计入 4 个新增任务；若要计入，必须补充人工 review note，说明公开问题来源、PR body 摘要、复现症状、测试意图和可审计性。`sharkdp/fd#1805` 已标记为 stretch / diagnostic-first，通过 Linux-only、排序、shell、feature 和 flaky probe 后才能升级为 accepted。

## 4. 最终建议候选

最保守的第一轮 accepted 目标组合：

- `spf13/cobra#2356`
- `stretchr/testify#1531`
- `pallets/click#3208`
- `pytest-dev/pluggy#646`

更强调生态多样性的目标组合：

- `spf13/cobra#2356`
- `pelletier/go-toml#1041`
- `pallets/click#3208`
- `sindresorhus/execa#1176` 或 `yargs/yargs#2332`

为了避免最后一关没有余量，实际 feasibility run 不应只跑 4 个候选。建议第一轮同时跑 6 个以上完整 probe，优先顺序为：

1. `spf13/cobra#2356`
2. `pallets/click#3208`
3. `stretchr/testify#1531`
4. `pytest-dev/pluggy#646`
5. `pelletier/go-toml#1041`
6. `sindresorhus/execa#1176` 或 `yargs/yargs#2332`

Rust 候选 `sharkdp/fd#1805` 可以作为多样性 probe，但默认不阻塞 P0。

## 5. 与 SWE-Bench Lite 的关系

本计划明确：V4 至少 4 个 PR / issue 构造流程新增任务不从 `princeton-nlp/SWE-bench_Lite` 数据集直接计数。

这 4 个任务应从 GitHub 原始 issue、pull request、fix commit、base commit 和人工审查记录出发，由 RepoHarness 自己生成 task definition、source archive、baseline verifier、post-patch verifier、evaluator-only evidence manifest、污染扫描报告和 freeze readiness 报告。

此前选出的 SWE-Bench Lite 候选可以继续作为 V4 公开 SWE-Bench-like 固定任务扩展、技术栈参考和 Docker 可行性参考，但不能替代这 4 个 V4 新构造 PR / issue task。

## 6. 审查结论

修复后，`docs/v4/pr-issue-task-source-plan.md` 可以作为 V4 implementation plan 中 `task source freeze / construction preflight` 阶段的输入。

进入正式 V4 implementation plan 时，仍必须保持两个边界：

- 计划可以引用这些候选作为第一轮来源，但不能提前宣称它们已经 accepted。
- accepted / auditable 计数必须等到 Docker execution probe、baseline verifier、post-patch verifier、flaky probe、adapter-visible denylist scan、training export boundary report 和 freeze readiness report 全部通过后再计算。

总体结论：审查通过，可以进入“本机可行性检查和任务冻结”阶段。
