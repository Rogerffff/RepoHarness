# RepoHarness V4 PR / Issue Task Source Plan

## 0. 文档定位

本文定义 V4 为“至少 4 个 V4 PR / issue 构造流程新增任务”寻找来源、筛选候选、执行本机可行性 probe、冻结证据和进入 implementation plan 的计划。

本文不实现 V4 代码，不修改 V3 运行逻辑，不把候选任务直接宣称为最终 accepted / auditable task definition。它只回答：

> V4 应该从哪些公开 GitHub 仓库和 issue / pull request / fix commit 中，较方便地构造 4 个可审计、可冻结、可验证、技术栈更多样的 PR / issue 任务？

## 1. 结论摘要

V4 的 4 个 PR / issue 构造任务不建议直接从 `princeton-nlp/SWE-bench_Lite` 数据集计数。它们应该从 GitHub 上公开 issue、merged pull request 和 fix commit 的原始材料出发，由 RepoHarness 自己构造 task definition、source archive、baseline verifier、post-patch verifier 和 evaluator-only evidence manifest。

本轮调研结论：

- Go 生态目前最适合作为第一批稳定 accepted 候选，尤其是 `spf13/cobra`、`stretchr/testify`、`pelletier/go-toml`。
- Python 生态适合作为稳定补位和语义型任务来源，尤其是 `pallets/click`、`pytest-dev/pluggy`、`python-attrs/attrs`、`pypa/packaging`。
- JavaScript / TypeScript 可以纳入候选池，但要优先选择依赖轻、单元测试清楚、可固定 Node 和 package manager 的仓库。`sindresorhus/execa` 和 `yargs/yargs` 优先级高于 `chalk/chalk`；`chalk/chalk` 只作为 JavaScript smoke / fallback 候选。
- Rust 可以作为多样性候选，但第一批应谨慎。`sharkdp/fd` 和 `clap-rs/clap` 都先按 stretch / diagnostic-first 处理，通过 Linux-only、排序、shell、feature 和 flaky probe 后再升级为 accepted。

建议 V4 第一批 probe 不只准备 4 个，而是准备 8 到 12 个候选，目标从中冻结至少 4 个 accepted / auditable task definitions。

## 2. 调研方式

本轮使用三类来源：

- 浏览器打开 GitHub issue / pull request 页面，确认公开状态、merged 状态、issue 与 PR 关系、测试计划和人工可审计性。
- GitHub CLI 查询 merged pull request 元数据、changed files、merge commit、closing issues 和 patch 规模。
- 只读 subagent 分别从 Python、JavaScript / TypeScript、Rust / Go 三个方向搜集候选来源和风险建议。

示例查询命令：

```bash
gh search prs --repo spf13/cobra --state closed --merged 'fix test' --limit 10 --json repository,number,title,url,closedAt,author,labels
gh pr view 2356 --repo spf13/cobra --json number,title,url,body,mergeCommit,baseRefName,headRefName,changedFiles,files,additions,deletions,closingIssuesReferences
```

## 3. 选择原则

候选必须优先满足：

- GitHub public repository。
- 明确的 issue / pull request / fix commit provenance。
- merged pull request 与 issue 或问题描述关系清楚。
- 有新增或修改的 regression test。
- 可以固定 base commit、source archive 和 source tree hash。
- 可以在本机 Docker 中安装依赖并运行 deterministic verifier。
- baseline 上目标行为测试稳定失败，应用 evaluator-only gold patch 后稳定通过。
- 可以把 adapter-visible task input 与 evaluator-only evidence 强隔离。

优先任务类型：

- CLI 参数解析、completion、输出格式、错误提示。
- Parser / serializer 边界行为。
- Assertion / validation / schema error tree。
- 插件注册、hook 调度、内部状态一致性。
- 纯函数或单进程单元测试能验证的行为 bug。

硬排除：

- 纯文档、纯依赖升级、纯 CI、纯 release、纯格式化。
- 需要真实网络、云凭据、数据库集群、浏览器端到端、GPU、GUI、长期后台服务。
- 依赖超大二进制、模型权重、外部服务或不可缓存资源。
- 上游 patch 过大或同时修多个独立问题，导致任务目标不可审计。
- 只有 benchmark 或人工观察能证明修复。
- 测试依赖浮动时间、系统 locale、真实终端宽度、随机输入且无法固定。
- 必须把上游 patch、PR diff、hidden selector、official resolved status 或 verifier 原始输出暴露给模型才能完成的任务。

## 4. 第一批强候选

以下候选建议进入第一批本机 feasibility probe。它们不是最终 accepted 清单，只有通过 source materialization、baseline verifier、post-patch verifier、flaky probe 和 evidence partition 后才能计数。

| 优先级 | 生态 | 仓库 | 来源 | base commit / fix commit | 变更规模 | 建议 verifier | 初步判断 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | Go | `spf13/cobra` | PR [#2356](https://github.com/spf13/cobra/pull/2356)，fixes issue [#2257](https://github.com/spf13/cobra/issues/2257) | base `61968e893eee2f27696c2fbc8e34fa5c4afaf7c4`，merge `746ef07158728502482cea9f880a6f4b21ef29a9` | 2 files，59 additions，1 deletion | `go test ./...` 或定向 completion package | 强候选。issue、PR、test plan、review 和 merged evidence 清楚。 |
| A | Go | `stretchr/testify` | PR [#1531](https://github.com/stretchr/testify/pull/1531)，closes issue [#1462](https://github.com/stretchr/testify/issues/1462) | base `d25ac14e7d3638f46181f355432a30f4a5801320`，merge `5911e38e09462765ebbe93bd7e79d761cc73d4fd` | 2 files，61 additions，20 deletions | `go test ./...` 或 `go test ./assert` | 强候选。overflow / underflow 语义清楚，测试局部。 |
| A | Go | `pelletier/go-toml` | PR [#1041](https://github.com/pelletier/go-toml/pull/1041)，fixes issue [#1032](https://github.com/pelletier/go-toml/issues/1032) | base `e14bde7c1d0e055cc26b8348f7a08ba0c7af1cdb`，merge `16b1ef5508d99a35131b454a80e05a784d0f61fe` | 2 files，7 additions，1 deletion | `go test ./...` 或 parser/error 定向测试 | 强候选，但 PR body 含 Claude session 链接；adapter-visible 输入只能用 issue 描述或人工改写，不得暴露 PR body。 |
| A | Python | `pallets/click` | PR [#3208](https://github.com/pallets/click/pull/3208)，fixes issue [#2790](https://github.com/pallets/click/issues/2790) | base `8d3449517a97b6fd457a025bd9c3d2acfd301fa4`，merge `0cd28d6548f92e46396e0ffdd19ec5ea75b4b5e4` | 3 files，76 additions，1 deletion | `pytest tests/test_formatting.py` 加少量 pass-to-pass | 强候选。错误提示行为清楚，测试局部。 |
| A | Python | `pytest-dev/pluggy` | PR [#646](https://github.com/pytest-dev/pluggy/pull/646)，fixes issue [#431](https://github.com/pytest-dev/pluggy/issues/431) | base `6ab917ba3b2dc1dceba6a260a0c30cb947f6a69c`，merge `20d8143f127a4d7526dbbea441857b4b80ec8bdd` | 4 files，81 additions，8 deletions | `uv run pytest` 或 `pytest testing/test_pluginmanager.py` | 强候选。仓库小，hook 状态行为适合训练轨迹。 |
| A- | JavaScript / TypeScript | `sindresorhus/execa` | PR [#1176](https://github.com/sindresorhus/execa/pull/1176)，fixes issue [#1175](https://github.com/sindresorhus/execa/issues/1175) | base `c8cff27a47b6e6f1cfbfec2bf7fa9dcd08cefed1`，merge `2aa3b0ceeb76bc9bd5e4e4789d965cc483dba185` | 2 files，13 additions，1 deletion | `npm test` 或 template parser 定向测试 | 强候选但涉及子进程库，应确认 Linux-only verifier 稳定。 |
| A- | JavaScript / TypeScript | `yargs/yargs` | PR [#2332](https://github.com/yargs/yargs/pull/2332)，fixes issue [#2330](https://github.com/yargs/yargs/issues/2330) | base `3a40a787edc5784b8134af022948b30c707001ba`，merge `888db19ccebcb5065a7aa415445e41cb15411c50` | 2 files，32 additions，1 deletion | `npm test` 或 completion 定向测试 | parser configuration 与 completion 语义清楚，适合作为 JS / TS accepted 候选。 |
| B | Rust | `sharkdp/fd` | PR [#1805](https://github.com/sharkdp/fd/pull/1805)，fixes issue [#1797](https://github.com/sharkdp/fd/issues/1797) | base `ba2dde80f37214e050a684ee3093db8b7f595ff4`，merge `5558e407bebafd5669d9f606eeaaba59938d67f0` | 7 files，49 additions，24 deletions | `cargo test` 或 CLI integration 定向测试 | stretch / diagnostic-first。PR/issue 关系清楚，但涉及 CLI 输出、文件排序、shell 和多文件 patch。 |

## 5. 第二批备选候选

这些候选适合作为第一批不稳定时的替换，或作为 diagnostic-only / staged enhancement。

| 生态 | 仓库 | 来源 | base commit / fix commit | 主要风险 |
| --- | --- | --- | --- | --- |
| Python | `pallets/click` | PR [#3364](https://github.com/pallets/click/pull/3364)，fixes issue [#2745](https://github.com/pallets/click/issues/2745) | base `8a2b48901a08b3d2ec3a9bbd151948a9765368c6`，merge `c8da1fcc2cb4523c1fb5bef7f0ca82394dde1efd` | 文档改动较多，但核心修复和测试清楚。 |
| Python | `python-attrs/attrs` | PR [#1428](https://github.com/python-attrs/attrs/pull/1428)，fixes issue [#1427](https://github.com/python-attrs/attrs/issues/1427) | base `94caa57142c057ce52504cdf239ae0ed3168f9b5`，merge `937b1e232803cc4ec9b9375ef525fc57c24ec498` | 代码生成语义较细，需要人工改写 task statement。 |
| Python | `pypa/packaging` | PR [#1124](https://github.com/pypa/packaging/pull/1124)，fixes issues [#766](https://github.com/pypa/packaging/issues/766) and [#978](https://github.com/pypa/packaging/issues/978) | base `e9385363dcbdc4494cd1b2438e1f945b42a49422`，merge `69307a312b3e4a3d989fd46abc6cbc0acf70adba` | 覆盖两个 issue，可能需要拆分或降低优先级。 |
| Python | `hynek/structlog` | PR [#620](https://github.com/hynek/structlog/pull/620)，fixes issue [#619](https://github.com/hynek/structlog/issues/619) | base `767ec8b9a196263bf9d8addcd4cb031433a49d4b`，merge `b16e08f0c2989be813b666c62e633a70e59cfb42` | 任务较小，适合作稳定补位。 |
| JavaScript | `chalk/chalk` | PR [#335](https://github.com/chalk/chalk/pull/335)，fixes issue [#334](https://github.com/chalk/chalk/issues/334) | base `c25c32a25f4315c1f7ee21cc7b36b497c4f0212a`，merge `87156ce8e2696a6002a51fbd1168e43eb9c70ce4` | 修复过小且工具链较旧；只作为 JS smoke / fallback accepted，不优先占用 4 个核心名额。 |
| TypeScript | `colinhacks/zod` | PR [#5708](https://github.com/colinhacks/zod/pull/5708) | base `08b14b51501335a3e0de3cb92c3b2fdeae00a0d6`，merge `9cf868d20cdaf4cf80f6d33a6eaf31582f1cdeba` | 没有关联 issue；可以 diagnostic probe，accepted 需人工 review note 弥补 provenance。 |
| Rust | `clap-rs/clap` | PR [#6340](https://github.com/clap-rs/clap/pull/6340) | base `14202755e52802a3d294c4ceeadd703d24b21fe6`，merge `2b3ddd0294a147d1eda917cb303243bcde0c12ee` | 无关联 issue，workspace 较大、completion 测试较细；accepted 需要人工 review note、PR body 摘要和测试意图证明，默认 diagnostic-only。 |

## 6. 建议最终构成

为了兼顾稳定性和技术栈多样性，第一轮目标不是一次只挑 4 个，而是从以下候选中 probe 8 到 12 个，最终冻结至少 4 个：

- Go：至少 probe 3 个，目标 accepted 2 个。
- Python：至少 probe 3 个，目标 accepted 1 到 2 个。
- JavaScript / TypeScript：至少 probe 2 个，目标 accepted 1 个；如果不稳定则降级为 diagnostic-only。
- Rust：至少 probe 1 到 2 个，优先作为多样性 stretch；通过后可计入 accepted，不通过不阻塞 P0。

一个保守的最小 accepted 组合可以是：

- `spf13/cobra#2356`
- `stretchr/testify#1531`
- `pallets/click#3208`
- `pytest-dev/pluggy#646`

一个更有多样性的目标组合可以是：

- `spf13/cobra#2356`
- `pelletier/go-toml#1041`
- `pallets/click#3208`
- `sindresorhus/execa#1176` 或 `yargs/yargs#2332`

## 7. Feasibility Probe 阶段设计

每个候选必须按相同 pipeline 执行：

1. Source provenance freeze：
   - 记录 `repository_url`、`base_branch`、`base_commit`、`merge_commit`、`issue_url`、`pull_request_url`、`fix_commit_url`。
   - 生成 source archive，并记录 `source_archive_sha256` 和 `source_tree_hash`。

2. Adapter-visible task draft：
   - 只使用公开 issue 描述或人工改写问题陈述。
   - 不包含 PR diff、fix commit、上游新增测试、gold patch、hidden selector、official resolved status、CI 结果或模型生成 session 链接。

3. Evaluator-only evidence freeze：
   - 保存上游 fix patch、上游新增测试、baseline failing log、post-patch passing log、patch apply facts、flaky probe records。
   - 保存 PR / issue / fix commit URL 和 hash ref，但不把解法内容暴露给 agent loop。

4. Dependency and environment probe：
   - Python：固定 Python 版本、lockfile 或 dependency snapshot，运行 `pytest` 或定向测试。
   - Go：固定 Go 版本，记录 `go env`、module cache 行为，运行 `go test ./...` 或人工说明的 package scope。
   - JavaScript / TypeScript：固定 Node major / minor、package manager 名称和版本、lockfile、`CI=1`、`TZ=UTC`，并记录是否允许 install 命令修改 lockfile。默认不允许修改 lockfile。
   - Rust：固定 `rust-toolchain` 或 pinned toolchain、target triple、feature flags、测试临时目录、排序稳定化策略和 CLI integration test 范围。

5. Docker execution probe：
   - 每个 accepted 候选必须在 Docker 中完成 dependency install、baseline verifier 和 post-patch verifier。
   - 记录 `base_image`、`image_digest`、`requested_platform`、`actual_container_arch`、`docker_memory_limit`、`docker_cpu_limit`、`disk_available_bytes`、`network_policy_by_phase`、`dependency_install_command`、`verifier_command`、`timeout_sec`、`stdout_log_ref`、`stderr_log_ref`、`exit_code` 和 `failure_category`。
   - 允许在 dependency install 阶段联网，前提是依赖版本和下载产物被记录；verifier 阶段默认不得联网。
   - 未通过 Docker execution probe 的候选只能进入 `diagnostic-only`、`quarantined` 或 `rejected`，不能计入 accepted / auditable。

6. Baseline verifier：
   - bug-fix fail-to-pass 测试在 baseline 上失败是有效任务信号。
   - pass-to-pass、setup、依赖和环境健康失败才判定为 unstable。

7. Post-patch verifier：
   - 在干净 verification workspace 应用 evaluator-only gold patch。
   - 目标 fail-to-pass 通过，pass-to-pass 不回退。

8. Flaky probe：
   - 默认重复 3 次。
   - 若出现 1 次非预期失败，扩展到 5 次。
   - 5 次中仍有非预期失败则不能 accepted，只能 quarantined 或 diagnostic-only。

无 issue 候选默认不优先计入 4 个新增任务。若要计入，必须补充人工 review note，说明公开问题来源、PR body 摘要、复现症状、测试意图和为什么没有 issue 仍然可审计。

## 8. 运行时可见性和训练导出边界

V4 PR / issue 任务的隔离不能只依赖目录命名。accepted / auditable 前必须满足以下硬规则：

- Agent 执行容器只能挂载 fixed base source tree、必要 dependency cache、允许的 public docs 和 `adapter_visible/task.json`。
- Agent loop、检索器、调试工具和日志上传器不得挂载或遍历本次 feasibility run root。
- `evaluator_only/`、`patch/`、`baseline/`、`flaky/`、`post_patch` 或 official report 目录必须位于 agent 不可见路径或独立权限域。
- Agent prompt、prepared messages、tool output、trajectory、context compaction、checkpoint、debug bundle 和 export observation 不得包含 evaluator-only 文件内容。
- 如果需要记录 evaluator-only 文件路径，只能在 acceptance / audit manifest 中记录 path、sha256、size 和 purpose；该 manifest 默认不进入模型上下文。

训练导出 allowlist：

- 允许进入训练 payload 的内容只能来自经过 schema 校验的 adapter-visible task statement、仓库 base source tree 中模型实际读取过的公开文件、agent 自己运行工具得到的可见结果，以及经过 export policy 标记为 trainable 的观察。
- 允许作为外部 metadata 的内容包括 task id、repo、base commit、source archive hash、tool policy id、environment id、verifier id 和非敏感 task source tag。

训练导出 denylist：

- 禁止导出 `evaluator_only/`、`patch/`、`baseline/`、`flaky/`、post-patch verifier 原始报告、official harness / GitHub CI raw logs、official resolved status、CI status、gold patch、hidden tests、上游新增测试、verifier raw output、provider raw response、PR body、PR diff、review comments、review suggestions、commit messages after base、fix commit URL、merge commit URL、LLM / Claude / Codex session URL。
- 禁止把 provider raw response、reward scalar、reward label、hidden selector 命中细节、final verifier trace 或 post-patch passing log 放入模型可见训练文本。

污染扫描必须覆盖：

- `adapter_visible/` 下所有 JSON、Markdown、prompt fragment 和 task statement。
- 允许进入 agent workspace 的额外文件。
- prepared messages、tool observations、trajectory、context replacement report、debug bundle、export manifest 和训练 shard。
- PR 编号、issue 编号、fix commit hash 的前 7 到 12 位、merge commit hash、PR URL、diff hunk 特征、上游新增测试函数名、hidden selector、`patch` / `test_patch` 字段名、Claude / Codex / session URL、provider response keys。

污染扫描默认 fail closed：

- 命中 gold patch、上游新增测试、fix commit、PR diff、hidden selector、AI coding session URL、provider raw response 或 verifier raw output 时，候选不能 accepted。
- 唯一例外是人工审查明确记录该命中只是安全 provenance metadata，且该 metadata 不会进入 agent loop 或训练 payload。

## 9. 建议机器产物

建议运行目录：

```text
runs/v4-pr-issue-task-source-feasibility-YYYYMMDDTHHMMSSZ/
  discovery/
  source_archives/
  adapter_visible/
  evaluator_only/
  baseline/
  patch/
  flaky/
  freeze/
  manifests/
```

建议产物：

- `pr_issue_candidate_source_registry.json`
- `github_discovery_query_log.jsonl`
- `candidate_pr_issue_inventory.jsonl`
- `candidate_source_provenance_report.json`
- `source_archive_manifest.json`
- `adapter_visible_task_draft.jsonl`
- `evaluator_only_evidence_manifest.json`
- `baseline_verifier_probe_report.json`
- `post_patch_verifier_probe_report.json`
- `flaky_probe_report.json`
- `adapter_visible_denylist_scan_report.json`
- `training_export_boundary_report.json`
- `pr_issue_task_selection_manifest.json`
- `pr_issue_task_freeze_readiness_report.json`

`candidate_pr_issue_inventory.jsonl` 最低字段：

- `schema_version`
- `candidate_id`
- `recommended_status`
- `repo`
- `license`
- `language_ecosystem`
- `repository_url`
- `base_commit`
- `merge_commit`
- `fix_commit_url`
- `issue_url`
- `pull_request_url`
- `fix_patch_sha256`
- `upstream_test_patch_sha256`
- `adapter_visible_source`
- `visibility_risk`
- `environment_lock_strategy`

`pr_issue_task_selection_manifest.json` 和 `pr_issue_task_freeze_readiness_report.json` 最低字段：

- `schema_version`
- `candidate_id`
- `repo`
- `base_commit`
- `merge_commit`
- `source_archive_sha256`
- `source_tree_hash`
- `adapter_visible_input_hash`
- `evaluator_only_evidence_manifest_hash`
- `verifier_definition_hash`
- `docker_probe_ref`
- `baseline_probe_ref`
- `post_patch_probe_ref`
- `flaky_probe_ref`
- `denylist_scan_ref`
- `training_export_boundary_ref`
- `final_status`
- `primary_failure_category`
- `secondary_failure_category`
- `retryable`
- `accepted_counting_reason`

## 10. 进入 V4 Implementation Plan 的门槛

implementation plan 可以引用本计划作为 task construction preflight 输入，但不能假设所有候选已经 accepted。

进入 V4 implementation plan 前，建议至少完成：

- 8 到 12 个候选的 discovery metadata。
- 至少 6 个候选完成 source materialization probe。
- 至少 6 个候选完成 Docker execution probe、baseline verifier、post-patch verifier 和 flaky probe。
- 至少 5 个候选达到 freeze readiness。
- 最终从 freeze-ready 候选中选择至少 4 个 accepted / auditable PR / issue task definitions。
- 至少 2 个生态进入最终候选，理想为 3 个生态。
- 所有 accepted 候选都有 evaluator-only evidence manifest、adapter-visible denylist scan、training export boundary report 和物理挂载边界记录。

如果第一轮无法达到 4 个 accepted / auditable 候选，则 implementation plan 必须把 PR / issue task construction 作为第一阶段阻塞项，而不能继续假设任务集已准备好。

## 11. 已知风险

- Go 候选最稳，但如果 4 个任务都来自 Go，会削弱 V4 技术栈多样性。
- JavaScript / TypeScript 候选需要固定 Node、package manager 和 lockfile，否则依赖漂移风险高。
- Rust 候选多样性价值高，但 workspace、feature flags、snapshot 或 CLI integration test 容易增加 probe 成本。
- `chalk/chalk#335` 的修复规模很小，只适合作为 JavaScript smoke 或 fallback accepted。除非 selection manifest 明确说明其价值是低成本多语言验证，否则不应占用 4 个核心 accepted 名额。
- `sharkdp/fd#1805` 的 provenance 清楚，但 patch 跨 7 个文件，默认应作为 Rust stretch / diagnostic-first。
- 部分近期 PR body 含 AI coding session 链接或直接解释修复方法。这些材料不能进入 adapter-visible input。
- 上游 PR 的新增测试可以作为 evaluator-only hidden verifier，但不应原样暴露给模型。
- GitHub merged 状态和 CI 通过只能作为 provenance，不是 RepoHarness final verifier。

## 12. 下一步执行建议

建议下一步启动一个独立 feasibility run：

1. 生成 `pr_issue_candidate_source_registry.json`，先收录本文第一批和第二批候选。
2. 对第一批强候选执行 clone、checkout base commit、source archive 和 hash。
3. 先跑 `spf13/cobra#2356`、`pallets/click#3208`、`stretchr/testify#1531`、`pytest-dev/pluggy#646` 四个轻中量任务。
4. 同轮补跑 `pelletier/go-toml#1041` 和 `sindresorhus/execa#1176` 或 `yargs/yargs#2332`，给最终 4 个 accepted 保留余量和生态多样性。
5. 再以 `sharkdp/fd#1805` 或 `clap-rs/clap#6340` 做 Rust 多样性 probe；稳定则纳入 accepted，失败则保留 diagnostic-only。
