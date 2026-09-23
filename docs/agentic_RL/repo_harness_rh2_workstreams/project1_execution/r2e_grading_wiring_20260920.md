# 第二步：R2E 经真实 RH2 评分与训练运输闭环（接线执行计划）

日期：2026-09-20。作者：B 线 Claude（计划起草）；复核：A 线 / B 线 Codex；决定：用户。
状态：**计划已按 A/B 线复核修订（§11 第二行），用户 09-20 已决定 DR1=A、DR3=A、DR4=接线阶段不处理题目，DR2 撤回；未改 R2E 代码**。复核：[A 线](r2e_grading_wiring_review_20260920/README.md)、[B 线](r2e_grading_wiring_review_20260920/B_review.md)。上一片（SWE-Gym 真实评分接线 + 第四组 + 链路修复）已于 `58a14b00` / `e3d120b5` 提交，见[第一步接线页](swe_grading_wiring_20260915.md)。

## 0. 结论先行

1. R2E 目前只有**材料、独立 runner 对照和方案 A 的契约字段**；`rh2/src` 里没有 R2E 的来源适配、parser、评分脚本，也没有任何生产路径调用 `grading_outcome_fields_r2e`。
2. 接线本身分五个本机切片（来源材料 → parser 与判定 → 评分脚本 → 环境覆盖表 → 训练运输）加一个真机对账切片；本机切片**不需要机器**。
3. 真正的前置是**环境**：48 个 R2E 镜像在我们的沙箱身份下一题都跑不起来（解释器在 `/root` 下），且答案在镜像 git 库里一条命令可得。M3 已实测出可用修法，需要做成逐题派生镜像；建议由 B 线 Codex 出配方并构建，本计划只定 rh2 怎么引用它。
4. 用户 09-20 已决定（§8）：扩公共契约 = A；派生镜像与隐藏测试的放法 = A；接线阶段不处理题目、按来源原样判。原 DR2（键归一化二选一）**撤回**——它建立在一条 09-09 已撤回过的误读上，上游实际只有一种去色行为。
5. 接线通过 ≠ 题目合格：期望映射里混着环境缺陷（20/48 题）、仓库测试模块可写、单键信号等问题留给流水线阶段，本片只保证"rh2 的判定与来源 runner 逐题一致、报告经训练运输不变形"。

## 1. 目标、范围与非目标

**目标**：一条 R2E 候选（noop / gold / 真实补丁）经 `prepared task → 候选应用与导出 → 冻结投影 → 正式 grader profile → R2E parser → GradingReport(grading_semantics="r2e_expected_map")`，结论与独立 runner（`rh2/experiments/env_probe_20260909/r2e_probe.py`，Prime `r2e_gym` 规则的复刻）逐题一致；同一份报告经 RewardFacts → gate → 准入 → 组缓冲 → 训练转换后语义不变。

**范围**：`R2E-Gym/R2E-Gym-Subset` revision `e8b9fcbc…` 里已有完整材料与镜像事实的 **48 题**（旧 24 + 夜间扩展 24，清单 `env_overnight_20260916/L4_r2e/r2e_tasks_48.json`）。

**非目标**（本片不做，各有去处）：

| 不做 | 去处 |
| --- | --- |
| 判断哪些 R2E 题可进训练题单；修订 expected（FAILED/ERROR 键、SKIPPED 键集漂移） | 流水线阶段（L4 报告 Q1/Q6） |
| 恢复仓库自带测试支撑模块（`pandas.util.testing` 等可写控制面） | 流水线 + 真实模型探针（L4 Q5；用户 09-19：反作弊力度后定） |
| 正式 actor 的 rollout 租约使用本地派生镜像 | D4=B 流水线阶段；本片只让 replay driver 与 spec 支持覆盖表 |
| 其余 4,530 题、其它 R2E 子集 | 未验证，不外推 |
| 改 binary_v1、infra 语义、SWE 路径的任何判定 | 不变 |

## 2. 核对后的事实

### 2.1 代码事实（2026-09-20，`58a14b00`）

| 位置 | 事实 | 对 R2E 的含义 |
| --- | --- | --- |
| `envpack/bundles_v2.py:167`、`training_view.py:94,153`、`prepared_tasks.py:87` | `source: Literal["swe_gym_lite"]`，注释"首版封闭枚举；扩源升版本" | 加来源必须改公共契约（§8 DR1） |
| `bundles_v2.PrivateGradingBundleV2` | 字段是 SWE 形状：`test_patch / fail_to_pass / pass_to_pass / eval_cmd / spec_vendor_id=Literal["swegym_constants_242429c1"]` | R2E 没有 test_patch 与 F2P/P2P，需要新的私有材料模型 |
| `training_view.HostGradingView.grading: PrivateGradingBundleV2` | 评分视图的密封材料类型写死 | 改成按 `schema_id` 判别的联合类型 |
| `training_view.TrustedTaskController.from_repo_root` → `ingest_swegym_lite.load_trusted_ingest_outputs` | 只读 `docs/…/s2/ingest/` 一个来源，带 T1 pins | 需要第二个来源目录与 pins，controller 合并多来源 |
| `adapters/slime/prepared_task_face.build_grading_spec_from_host_view` | 直接渲染 SWE 的 conda 环境行、安装段、`derive_test_command_for_bundle`，parser 绑 `parse_eval_log_v2` | 入口要按材料类型分派；R2E 用自己的渲染器 |
| `grading/manager.py`（结论组装） | `fields = scoring.grading_outcome_fields(verdict)`，`EvalVerdict` 只有 F2P/P2P 列表 | 需要让 verdict 带 expected 匹配结果并分派到 `grading_outcome_fields_r2e` |
| `envpack/scoring.expected_map_matches / grading_outcome_fields_r2e`、`contracts/grading.GradingReport.grading_semantics` | 已实现、有契约矩阵测试，**无生产调用** | 直接复用；口径是"期望键 ∪ 观测键"，多键/缺键都让 match < total |
| `adapters/slime/baseline_census.baseline_policy_for_task_id` | 只有 `swe_gym_lite` 用政策 v2；`excluded_namespaces` 只有 `.git/`、`.harness/` | R2E 的 `.venv` 在 `/testbed` 里，必须进排除区（§3.4） |
| `envpack/materialize.build_probe_script` | 血缘判据 = HEAD 或其父等于 `base_commit`；脏树只作证据不作判定 | R2E 的"初态不是干净树"不会被物化校验拒绝 |
| `sandbox_profile.rollout_trusted_init_script` | 已做 `useradd`、`safe.directory '*'`、`chown -R workdir` | 解决 `/testbed` 写权限，但**解决不了解释器在 `/root`**（§2.2） |
| `adapters/slime/replay_grade.py` | `--derived-image` 是整批单镜像（D4=A 诊断用） | R2E 每题一张派生镜像，需要按题映射（§3.5） |
| `grading/manager.execution_failure_trigger` | 用四个 F2P/P2P 桶的总长度减缺席数判"参考全缺席" | R2E 的四个桶恒空 → **只缺一个键也会被当成全缺席**（A 线 R2 反例）；必须改为按 expected / observed 的键在场关系判 |
| `grading/manager._grade_within_deadline` 的公共报告字段 | `grading_semantics` 只由判分 helper 的字段字典带出；P-A 候选归因、提前 infra、patch-apply 分支都不经 helper | 这三条分支的报告会回落到默认 `swe_f2p_p2p`；来源语义必须在 spec 构造时确定并进所有报告分支 |
| `envpack/prepared_tasks.prepare_tasks`（`trusted_prep --task-ids` 省略时） | 准备 controller 的**全部**任务 | 多来源合并后默认集合必须保持旧行为（只 SWE），R2E 要显式选入 |
| `sandbox_profile`：rollout uid 54321、grader 候选 uid 54322 | rollout 初始化与 grader 权限布置**各自**递归 `chown -R /testbed` | 一张派生镜像不能同时预置成两个属主；运行期属主更改的成本仍在（§3.5） |
| `adapters/slime/baseline_census`（排除区） | 排除区不读文件内容，但**路径清单的摘要仍进 manifest**，且排除区里的 `__pycache__` 不剪 | `.venv` 进排除区后，census 之前任何写 `.venv` 缓存的步骤都会让 fresh grader 的基线摘要对不上（B 线 B1） |
| `adapters/miles/group_admission`（457–466 行） | 同组成员必须同 `task_id / environment_package_digest / public_bundle_digest` | 运输验收只能是"同批不同组"，不能把 SWE 与 R2E 放进同一组 |

### 2.2 来源与镜像事实（出处：[L4 适配器卡](env_overnight_20260916/L4_r2e/L4_r2e_adapter_card.md)、[L4 报告](env_overnight_20260916/L4_r2e/L4_report.md)、[M3 报告](env_overnight_20260916/M3/M3_report.md)；均为 48 题实测或读码）

- **判定语义**：`reward = 1 ⇔ 观测状态映射 == 期望状态映射`（键集相等且逐键状态相等）。期望值可以是 PASSED / FAILED / ERROR。例：pandas `19c5eea5` 的期望里本来就有 ERROR 键（fixture 在抽取后不可见），gold 跑出来 `rc=1` 但 reward 1——**不能套 SWE 的"失败即不过"**。
- **入口**：固定 `/testbed/run_tests.sh`，三种原文：40 题 `… .venv/bin/python -W ignore -m pytest -rA r2e_tests`；orange3 7 题前面加 `xvfb-run`；pillow `3ac9396e` 是自定义 unittest runner（手工打印 `short test summary info`，**也打印 pytest 形状的收尾行**，既有 gold 日志里是 `11 passed in …s`）。不要重写成我们自己的 pytest 命令。
- **parser**：只读 `short test summary info` 之后的行；键 = node id 去掉文件路径后用 `.` 连接；FAILED/ERROR 再截 `" - "`；SKIPPED/XFAIL 行被丢弃。期望映射用同一 parser 生成，所以两侧对称。
- **键归一化（09-20 更正）**：原稿称"Prime 原版对期望侧只删 `[数字m`、不删 ESC，pillow 6 题 gold 恒 0"——**这是误读，已撤回**。固定源码 [`PrimeIntellect-ai/prime-envs@c4d04dfe…/environments/swe/r2e_gym/r2e_gym/taskset.py`](https://github.com/PrimeIntellect-ai/prime-envs/blob/c4d04dfe212c153a587ea4ce072ae6753e74d6e9/environments/swe/r2e_gym/r2e_gym/taskset.py) 的 `_decolor` 正则是 `\x1b\[\d+m`，ESC 是源文件里的不可见字节；这一点 09-09 已由 [Codex 远端核查 §3.1](env_probe_20260909/codex_remote_check_20260909.md) 指出、我在[当日记录 §8](env_probe_20260909/README.md) accepted 并撤回过，L4 适配器卡又沿用了旧说法，我写计划时没有回查。A 线本次用固定源码的三个纯函数重放 336 份既有日志（旧 24 的 144 份 + M3 的 192 份），与本地 runner 的 reward **全部相同**，带 ANSI 的 pillow 六题 24 次 gold 全为 1。上游只有一种去色行为，接入它即可。
- **独立 runner 的基线**（对账靶子）：noop 48/48 = 0，且每题至少 1 个键与期望不同；gold 46/48 = 1，两个 0 是来源缺陷——coveragepy `016af5f6`（期望 FAILED，我们环境里 PASSED）、datalad `58ba5165`（隐藏测试 import 了被 gold 排除的测试文件）。
- **初态不是干净树**：镜像把"让旧代码在新 Python 上能跑"的补丁留在未提交状态（已跟踪改动 **aiohttp 5 题 + pandas 7 题，共 12/48**——原稿的 3+3 是扩展 24 题的局部计数；48/48 有未跟踪文件，至少 `run_tests.sh` 与 `.venv`）。任何 `git reset/checkout/clean/stash` 都会破坏环境；候选 delta 不能用 `git diff HEAD` 取。rh2 现有的"census 基线 + 导出"天然正确。
- **隐藏测试在镜像里**：`/r2e_tests`（1–5 个文件：`test_1.py`，部分带 `conftest.py` / `helper.py` / `test_2.py` / 自定义 runner），默认可读；评分前 `cp -r /r2e_tests /testbed/r2e_tests`。
- **沙箱身份跑不动（48/48）**：`/testbed/.venv/bin/python` 链到 `/root/.local/share/uv/python/…`，`/root` 是 0700；uid 54321/54322 执行即 `Permission denied`，标准库也在 `/root` 下。M3 实测三种布置，"搬迁解释器到 `/opt/py` + `chown -R /testbed` + `safe.directory`"在 48 题 × noop/gold 共 96 次实跑里与 root 基线逐键相同；`chown -R` 在 M3 的条件下要 11–149 s 并让可写层涨 0.35–2 GB。**注意**：M3 的对照用的是 uid 54322；正式链里 rollout（54321）与 grader（54322）各自在运行期递归改属主，构建期预置解决不了两边（§3.5），实际成本要在正式 profile 下重新量。
- **答案可达（48/48）**：修复提交是 HEAD 的直接子提交，`git rev-list --children --all | grep ^$(git rev-parse HEAD)` 一条命令、不需要哈希和网络。M3 的 git 清理（删 ref/tag/remote、过期 reflog、`gc --prune=now`）在 48 题上让修复提交不可达且 noop 判分逐键不变。
- **`.venv` 在工作目录里**：`/testbed/.venv` 是环境本体（数千到上万文件）；SWE-Gym 的环境在 `/opt/miniconda3`，没有这个问题。

## 3. 设计

### 3.1 来源材料（私有 / 公开 / 验证）

```text
R2E 数据行 ──ingest_r2e_subset──► PublicTaskBundle            （题面=problem_statement、image、workdir、base_commit）
                                 PrivateGradingBundleR2E      （expected 映射、run_tests.sh 原文+摘要、隐藏测试清单+树摘要、parser/归一化版本）
                                 ValidationOnlyBundle         （gold：固定 Prime `extract_gold_patch` 的实际实现由 parsed_commit_content 重建，只含非测试 .py）
                                 EnvironmentPackageV1(source="r2e_gym_subset")
```

- `source = "r2e_gym_subset"`；`instance_id = "<repo>__<commit_hash 40 位>"`（例 `aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52`，满足 `SafeIdentifier`）；`task_id = "r2e_gym_subset::<instance_id>"`；`base_commit` = 镜像 HEAD（修复提交的父提交）。
- `PrivateGradingBundleR2E`（`schema_id="rh2.private_grading_bundle.r2e.v1"`）字段：`instance_id / repo / base_commit / expected_map`（来源原文，键不预归一化）`/ expected_map_sha256 / run_tests_sh`（逐字）`/ run_tests_sh_sha256 / hidden_test_files`（相对 `r2e_tests/` 的路径清单）`/ hidden_tests_tree_sha256 / parser_id="r2e_prime_pytest_v1" / normalization_version / source_revision / spec_vendor_id="r2e_gym_subset_e8b9fcbc"`。**不含 gold**。
- 公开面 fail-closed 断言：不得出现 `expected_output_json`、`parsed_commit_content`、`prompt`（那是造题指令，不是 solver 输入）、`execution_result_content`、`modified_*`；沿用现有保留键与泄漏标记扫描。
- 输出目录与 pins：`docs/…/s2_r2e/{raw,ingest}/` + 自己的 T1 pins；48 题原始行取 **`runs/env_overnight_20260916/M3/probe_data/r2e_candidates_full.jsonl`**（合并后的 48 行，A 线核对其 48 个 commit 与 `r2e_tasks_48.json` 完全相等；原稿指向的 `inputs/r2e_expansion_preparation/` 下同名文件只有扩展 24 行），连同旁边的 revision 记录；ingest 时核对 revision 与逐行摘要，保持 expected 原文。镜像 manifest digest 表单独成文件（与 SWE 的 `image_manifest_keyed.json` 同形）。
- `HostGradingView.grading` 改为按 `schema_id` 判别的联合（`PrivateGradingBundleV2 | PrivateGradingBundleR2E`）；`TrustedTaskController` 支持多来源合并，`task_id` 前缀区分；**默认来源集合保持旧行为（只 SWE）**，R2E 必须用显式来源或题单选入——装上新适配器不会把尚未接好派生环境的 48 题自动混进 `trusted_prep` 的默认输入。SWE 侧序列化字节不变、旧命令产出同一份题单（两个验收项）。

### 3.2 parser、归一化与判定

- `envpack/r2e_parsers.py`（与 `swegym_parsers.py` 并列、不复用）：`parse_r2e_pytest_summary(text)` 逐步复刻 Prime：去日志侧 ANSI 与 CR → 取 `short test summary info` 之后 → PASSED / FAILED / ERROR 三类行的取键规则 → 没有该段返回空映射。
- 键归一化只有一种：按固定的上游实现（两侧同规则去色、截 `" - "`）。**代码来源固定为 `prime-envs@c4d04dfe…` 的 `taskset.py`**（本地归档 `runs/env_probe_20260909_codex_backup/analysis/prime_taskset.py`，sha256 `b928139e…`）；数据 revision `e8b9fcbc…` 不能替代代码版本。版本写进 `grader_version`（`r2e-gym-subset@e8b9fcbc+parser:prime-envs@c4d04dfe`），不再扩报告契约，也不维护第二套实现。
- `scoring.parse_eval_log_r2e(grading, log_text) -> EvalVerdict`：与 SWE v2 入口同纪律——**只解析 Start/End 标记段**；坏码或缺标记 → `apply_ok=False`。`EvalVerdict` 增两个带默认值的字段：`grading_semantics`（默认 `swe_f2p_p2p`）、`expected_match: ExpectedMapMatch | None`；R2E verdict 的 F2P/P2P 列表为空，`resolved = expected_match.resolved`，`num_parsed_tests = 观测键数`，`reference_missing = expected_match.missing`。
- `grading_outcome_fields(verdict)` 按 `grading_semantics` 分派到既有 `grading_outcome_fields_r2e`。
- **manager 的来源语义迁移（A 线 R2，必须随 R-b/R-c 一起做）**：① `GradingEnvSpec` 新增 `grading_semantics`，由 spec 构造入口在 parser 运行**之前**确定，`_grade_within_deadline` 的公共报告字段带上它——P-A 候选归因、提前 infra、冻结重放失败等所有分支的报告都是 `r2e_expected_map`，未知计数仍为 None；② `execution_failure_trigger` 对 R2E 按键在场关系判："参考全缺席" = 期望键非空且**没有任何期望键出现在观测里**；不借用空的 SWE 桶，也不用"状态匹配数为 0"代替"参考键在场数为 0"。反例：期望 `{test_a, test_b}`、观测只有 `test_a` → 是部分在场的 tests_failed / 0，不进 P-A。
- 与 Prime `calculate_reward` 的差别只有一处：Prime 跳过空 parsed 键（键集不等也可能给 1），我们用并集口径更严；48 题实测 `n_missing / n_extra` 全为 0，未触发。对账时若出现分歧单列。

例（单测固定样本，取自适配器卡 I2/I3）：

| 输入 | 期望结果 |
| --- | --- |
| pillow `4bc64835`：期望 24 键全带 `\x1b[1m…\x1b[0m`，日志 24 条 PASSED | 24/24 → resolved（与固定上游函数一致） |
| 日志没有 `short test summary info` 段 | 空映射 → 零解析 → 走既有 P-A 三路（不抛异常） |
| 观测比期望多 1 个键（环境变好多出用例） | total = 期望 + 1，match < total → tests_failed |
| 期望 `{a: PASSED, b: PASSED}`，观测 `{a: FAILED}`（b 收集失败缺席） | 部分在场 → tests_failed / 0，**不**触发"参考全缺席" |
| 期望带 ERROR 键且观测同为 ERROR、测试命令 `rc=1`（pandas `19c5eea5` 形态） | 全匹配 → resolved |

### 3.3 评分脚本（grader 内）

- **可信 setup（root）**：`rm -rf /testbed/r2e_tests && cp -r <隐藏测试私有位置> /testbed/r2e_tests` → 按 bundle 原文重写 `/testbed/run_tests.sh`（agent 对它的任何改动在此被覆盖）→ 核对隐藏测试树摘要与 `run_tests.sh` 摘要（不符 = `grading_trusted_setup_failed` infra，候选测试不启动）→ 复用现有自证尾段（`grader_trusted_setup_attest_lines`），official 文件清单 = `r2e_tests/<每个隐藏测试文件>` + `run_tests.sh`。R2E 的 root setup 没有 `git apply test_patch`，而该 helper 的 `RH2_APPLY_RC` 缺省为 1：复制、重写、摘要核验**全部成功之后**才显式置成功状态（B 线 B3）。随后现有权限布置脚本把这些文件收回 root、祖先目录加 sticky。
- **候选段（uid 54322）**：没有安装段（打 `RH2_INSTALL_SKIPPED=1`）；`cd /testbed` → Start 标记 → `bash run_tests.sh` → `RH2_TEST_RC=$?` → End 标记。不加 `-q`、不加插件、不改入口（入口换了 `short test summary info` 的内容就变）。
- **观测与复证**：运行器摘要、导入路径探针、P-A 编译复证都改用 `/testbed/.venv/bin/python`（复证仍是 `-I -S`、内存内 `compile`）。
- **hygiene / 投影**：`HygieneRules.test_files` = 上述 official 清单；候选对这些路径的改动按 D2-3 不重放。`test_globs=()` 不变（P-B）。
- **P-A 触发**：零解析 = 观测映射为空；"参考全缺席" = 期望键无一在观测里。形状规则、外层完成判据、语法位置关联原样适用（`RH2_TEST_RC` 是 `bash run_tests.sh` 的退出码）。自定义 unittest runner 的真实日志带 pytest 形状收尾行；按既有规则，"参考全缺席且无全局失败形状"直接走来源规则，没有收尾行并不自动变成 None——不为 unittest 入口新增任何日志格式拒绝规则，只用它的真实完整输出与启动失败各验一次。

### 3.4 baseline 政策（R2E 变体）

新政策 `baseline_policy_r2e_v1`：`excluded_namespaces = (".git/", ".harness/", ".venv/")`，`regenerable_cache_dirs` 同 v2。理由：`.venv` 是环境本体不是答案，census 它既慢又会把 agent 的 `pip install` 当成候选 delta；排除后 fresh grader 用镜像自带的 `.venv`，与"环境改动不重放"的既有口径一致。政策摘要进 manifest 身份，是新增版本，不改 v1/v2 的摘要（验收项）。已知后果：候选对 C/Cython 源码的修改会被重放但不会重建（R2E 没有安装段，gold 也只含 `.py`），记录为来源限制。

**排除 ≠ 不参与基线身份（B 线 B1）**：排除区的路径清单摘要仍进 manifest，且排除区内的 `__pycache__` 不剪。所以任何在**首次 census 之前**让 `.venv` 里多出缓存文件的步骤（例如用解释器做预检）都会让 fresh grader 重建的基线摘要对不上并停批。处理：R2E 专属预检放在首次 census **之后**、候选应用之前，且以 `python -B -I -S` 执行不写字节码；R-c/R-d 增一个"未经 Python 预热"的 fixture 往返，R-f 第一题确认同一边界。48 张真实镜像是否会新生缓存尚未验证，不列为现存缺陷。

### 3.5 环境覆盖表（逐题派生镜像的引用方式）

`EnvironmentOverlayV1`（JSON，一题一条）：`task_id / base_image_ref / base_image_manifest_digest / derived_image_ref / derived_image_id / recipe_id / recipe_sha256 / built_at_utc / facts{interpreter_relocated, testbed_owner, git_scrubbed, hidden_tests_location, hidden_tests_tree_sha256}`。

- replay driver：`run --image-overlays <file>`；有覆盖条目的题用派生镜像起候选容器与 grader（`image_local_build=True` + `image_local_build_id`，资格键随 image ID），并核对 `base_image_manifest_digest` 与环境包一致、本机 `inspect` 到的 ID 与表内一致（不一致 = 该题 `stage_error`，不评分）；两类容器直接用确认过的 image ID 启动（顺手关掉 tag 重指窗口，不为此重开已验收项）。现有 `--derived-image`（整批单镜像）保留给 D4=A 诊断。
- rollout 侧预检（**首次 census 之后**、候选应用之前，R2E 专属三条，失败即该题不进入候选阶段；解释器预检用 `-B -I -S`，见 §3.4）：① agent uid 能执行 `.venv/bin/python -c pass`；② agent uid 读不到隐藏测试私有位置，且 `/r2e_tests`、`/testbed/r2e_tests` 不存在；③ `git rev-list --children --all` 里 HEAD 没有子提交（清理生效）。
- 覆盖表的数据由环境侧产出（DR3）；SWE 这边 Codex 正在做的环境维修派生镜像可以用同一张表，但**不在本片接入 SWE 路径**。
- 正式 actor 的 rollout 租约目前只认"registry 镜像 + manifest digest"，让它使用本地派生镜像属于 D4=B，本片不做；所以本片结束时只能表述为"**真实 RH2 grader 路径 + 训练报告运输已验证**"；正式 actor 取到正确的派生环境、harness 执行与冻结工件仍未验，须在正式基座诊断开始前补这段入口（CPU Docker + harness 替身即可先查）。正式接入有两种表示途径——租约支持本地 image ID，或把派生镜像发布到 registry 后写它真实的 manifest digest——到 D4=B 再结合部署选择；无论哪种，都不能把基础镜像的 digest 当成派生镜像的身份。
- **属主与成本（A 线 R5）**：派生镜像只解决解释器位置、答案历史与隐藏测试存放；rollout 与 grader 仍按现有 profile 在运行期各自 `chown -R /testbed`。本片不做权限重构，先在正式 profile 的小样本上记录两侧初始化耗时与可写层增长，再定批量预算；要兑现"构建一次、运行不改属主"需要同时设计角色镜像与 runtime 的消费路径，不在本片。

### 3.6 两个入口共用一个适配器

`build_grading_spec_from_host_view` 按 `view.grading.schema_id` 分派到 SWE / R2E 渲染器，并在这里确定 `GradingEnvSpec.grading_semantics`；driver 与 `PreparedTaskFace.grading_spec()` 都走它，没有第二份 R2E 逻辑。账本行增 `grading_semantics / expected_match / expected_total / overlay{derived_image_id, recipe_id}`。

## 4. 切片与顺序

| 切片 | 内容 | 主要文件（归属：Claude 实现；★ = A 线共享文件，A 线复核） | 依赖 |
| --- | --- | --- | --- |
| R-0（归 B 线 Claude，**已实施**，见 §11） | driver CLI 把 manager 最终收口状态外显：结束时仍有未确认关闭的评分容器 → 退出码非 0；累计出现过、之后已清成功的清理失败只留诊断不算失败；grader scope 无法确认终止 → 停批并以约定退出码结束；`stage_error`、reward 0 与运行失败分别对账（manager 的跨实例清扫已由 A 线修复，本片基于其快照） | `scripts/replay_grade.py`、`adapters/slime/replay_grade.py` | 无 |
| R-a 来源材料 | 扩 `source` 枚举；`PrivateGradingBundleR2E`；`envpack/ingest_r2e_subset.py`；R2E T1 pins；多来源 controller；prepared 视图；gold 重建（Prime 规则） | `envpack/bundles_v2.py`★、`training_view.py`★、`prepared_tasks.py`★、新 `ingest_r2e_subset.py`、`s2_r2e/` | DR1 |
| R-b parser 与判定 | `envpack/r2e_parsers.py`（固定 `prime-envs@c4d04dfe` 实现）；`parse_eval_log_r2e`；`EvalVerdict` 两字段；`grading_outcome_fields` 分派；`execution_failure_trigger` 的 R2E 键在场判据；离线语料对拍 | `envpack/scoring.py`、新 `r2e_parsers.py`、`grading/manager.py`★（基于 A 线清扫修复后的快照串行合入） | — |
| R-c 评分脚本 | R2E 渲染器（可信 setup / 候选段 / 观测 / 复证）；spec 入口分派并确定 `grading_semantics`，manager 所有报告分支带来源语义；official 清单；`baseline_policy_r2e_v1` | `adapters/slime/prepared_task_face.py`、`baseline_census.py`、`contracts/baseline_manifest.py`★、`grading/manager.py`★ | R-a、R-b |
| R-d 环境覆盖表 | `EnvironmentOverlayV1`；driver `--image-overlays`；rollout 侧三条预检；账本新列 | `adapters/slime/replay_grade.py`、`scripts/replay_grade.py`、新 `envpack/overlays.py` | DR3 |
| R-e 训练运输 | 由**真实 `manager.grade()` 产出**的 r2e 报告（不手工构造）→ RewardFacts → gate → 准入 → 组缓冲 → 训练转换；同一批次含一个 SWE 组与一个 R2E 组；run 报告对 None 计数的展示 | 测试为主；`adapters/miles/run_report.py`★ 正由 A 线其它任务修改，优先测现有消费者，确实缺字段再协调窄改 | R-b、R-c |
| R-f 真机对账 | 先少量代表题（纯 pytest / xvfb / 自定义入口 / 脏树 / 期望 ERROR 仍 resolved / 冷镜像基线 / P-A / 超时），再 48 题 × noop/gold；重复只对出现分歧或波动的题做 | runbook + `experiments/` 脚本 | R-0…R-d、派生镜像、机器 |
| R-g 记录 | 本页 §11、`env_data_eval.md`、对账页与报告 | docs | — |

顺序：R-0（已完成）→ R-a → R-b（可与 R-a 并行起步）→ R-c → R-d → R-e → 等派生镜像与机器 → R-f。每片完成后在 §11 登记验证结果；R-a/R-b 完成后可先交一次中途复核，不必等全部切片。

## 5. 验收

### 5.1 本机（每片）

| 切片 | 验收样例 |
| --- | --- |
| R-a | 48 行 ingest 往返；公开 bundle 逐键扫描无 expected / gold / prompt；环境包与三份 bundle 的摘要关系核对；SWE 既有 ingest / prepared 产物摘要逐字节不变，且省略 `--task-ids` 的旧命令产出同一份（只含 SWE 的）题单；gold 重建固定 Prime 实现，与独立 runner **比较纳入文件集合与应用后的内容摘要**（B 线 B2：两种重建方式 48/48 补丁字节不同，但纳入路径相同、在来源旧文件临时树里应用后内容摘要 48/48 相同；不为凑字节一致再改一套 gold） |
| R-b | §3.2 表内五条固定样本；**与固定上游函数对拍**：从 `prime_taskset.py` 归档按 AST 取 `parse_log_pytest / _decolor / calculate_reward` 三个纯函数，连同新 adapter 一起重放既有 336 份真实日志（旧 24 的 noop/gold ×3 = 144，M3 的 48 题 noop/gold ×2 = 192；路径见下），reward 与键级差异逐份一致。保留并单列一条真实差别：RH2 的键并集口径比 Prime 的"跳过空键"更严，本语料未触发不代表所有输入同义。`execution_failure_trigger` 的 R2E 判据：状态全错但键全在 / 部分缺键 / 全部缺键 / 零解析 四例。语料路径：`runs/env_overnight_20260916/M3/{facts/<commit12>/noop_x2, gold_ledger, logs_r2e, r2e_gold_m3.jsonl}`、`runs/env_probe_20260909_codex_backup/ledger/{r2e_ledger_v3.jsonl, logs_r2e}` |
| R-c | 渲染脚本的阶段顺序与标记（含自证 helper 的成功状态只在全部核验通过后置位）；**经新材料 / spec → 真实 `manager.grade()`** 的全流程：全匹配（含期望带 ERROR/FAILED 键、`rc=1` 仍 resolved 的 pandas 形态）/ 状态全错但键全在 / 部分缺键 / 全部缺键 / 零解析 / P-A 候选归因 / 提前 infra（摘要不符）——逐条断言报告的 `grading_semantics == "r2e_expected_map"` 且未知计数为 None；`run_tests.sh` 被候选改写后评分仍用原文；fixture Docker 往返（用 fixture 仓库模拟 `.venv` 排除与隐藏测试恢复） |
| R-d | 覆盖表缺条目 / ID 不符 / base digest 不符 → 不评分且账本留因；三条 rollout 预检的正反例（FakeDocker），预检位于首次 census 之后；"未经 Python 预热"的 fixture 往返（基线摘要在 rollout 与 fresh grader 两侧一致）；资格键随派生 image ID |
| R-e | 真实 `grade()` 产出的 r2e 报告经正式链替身运输：reward 1 / 0 / None 与 SWE 同形；四个 F2P/P2P 计数为 None 不致下游异常；**同一批次一个 SWE 组 + 一个 R2E 组**各自完成准入、优势与转换（组内仍是同一题的多个 execution）；保留反例：不同题硬塞同组 → `mixed_group_members` 被拒 |

通用：`ruff check src tests scripts`；已有套件按变更范围跑，最终集成再完整跑一次 contracts / adapters / governance / grading / envpack 非 Docker 套件与 Docker 套件；SWE 路径零回归。

### 5.2 真机对账（R-f）

先跑代表题，再跑全量。通过标准：① noop 48/48 = 0，且与期望不同的键集合与独立 runner 账本相同；② gold 46 题 = 1，coveragepy `016af5f6`、datalad `58ba5165` = 0 且失配键相同；③ 出现分歧或波动的题针对性重复（旧 24 已有多轮重复证据，不机械重跑）；④ 三种入口各至少一题（纯 pytest / xvfb / 自定义 runner），另含脏树题与冷镜像基线边界；⑤ 候选身份事实：解释器可执行、隐藏测试私有位置对候选 uid 不可读、修复提交不可达；⑥ 人为超时 → infra / None 且部分日志留存；⑦ P-A 对照一题（gold 行作资格 → 人为语法错误补丁 → `candidate_execution_failed`，无资格 → None）。任何与独立 runner 的分歧逐题写明原因，不以"多数一致"收口。通过后的表述限定为"真实 RH2 grader 路径 + 训练报告运输已验证"，不等于 48 题具备训练资格，也不等于正式 actor 已能执行 R2E。

## 6. 机器与成本

本机切片（R-0…R-e）不需要机器。R-f 需要一台 x86 CPU Docker 机：≥ 16 vCPU、≥ 32 GB 内存、≥ 300 GB 磁盘（48 个镜像约 76 GB，派生层每题另加 0.35–2 GB）、网络通畅。预计拉镜像 1–2 小时、构建派生镜像 1–2 小时；对账批的耗时**不能**只按 M3 的测试中位 9 s 估——正式 profile 下两侧初始化（递归改属主、census、控制面布置）才是大头，先用代表题量出单题耗时与可写层增长再定批量预算。仍按租一天准备。建议在 R-a…R-d 本机通过、派生镜像配方定稿之后再租；派生镜像构建期按 B 线已验证的做法关 metacopy，评分期开。

## 7. 风险

| 风险 | 影响 | 处置 |
| --- | --- | --- |
| 联合类型改动波及 SWE 既有 prepared 产物的字节与摘要 | 已生成的题包失效 | R-a 验收钉死"SWE 产物逐字节不变"；不过则改用并列字段而非改型 |
| `short test summary info` 在某些 pytest / 插件版本下形态不同（coveragepy 的 `-rfe`、scrapy 的 `--doctest-modules`） | 零解析或键集漂移 | 离线语料回放覆盖 48 题真实日志；仓库 `addopts` 已由 M3 逐题记录 |
| 派生镜像与原镜像的环境差异 | 判分漂移 | M3 已在 96 次实跑里证明布置 b 与 root 基线逐键相同；R-f 再以正式 profile 复核 |
| 期望映射记录的是上游坏环境（§2.2） | "修好环境"反而 0 分 | 本片不修环境、不修 expected；逐题标注，交流水线 |
| 候选进程 stdout 可伪造状态行（与 SWE 同族） | 伪 1 分 | 已登记的 T0 族，按用户 09-19 意见留到流水线与真实模型探针阶段 |
| `.venv` 进排除区后，census 前的任何解释器活动改变排除区路径摘要（B1） | 基线重建不等、停批 | 预检移到首次 census 之后且不写字节码；冷镜像 fixture 往返 + R-f 首题确认 |
| 默认来源集合被多来源 controller 改变 | 未接好环境的 R2E 题混进正式输入 | 默认只 SWE，R2E 显式选入；验收钉死旧命令题单不变 |

## 8. 决策事项（用户 2026-09-20 已决定）

| 项 | 决定 |
| --- | --- |
| DR1 | **A**：扩 `source` 枚举 + `PrivateGradingBundleR2E` + 按 `schema_id` 判别的联合（保留旧 SWE 字节与默认题单） |
| DR2 | **撤回**：原稿的二选一建立在对 Prime `_decolor` 的误读上（§2.2 更正）；固定真实上游代码，按其实际去色行为接入，不维护第二套实现 |
| DR3 | **A**：逐题派生环境（解释器搬迁、答案历史清理、隐藏测试 root 私有位置，评分时恢复来源原文）+ 环境覆盖表；成本与属主边界按 §3.5 收窄。配方构建的派发由用户另行安排，本页写的 owner 不等于已启动 |
| DR4 | 接线阶段**不处理题目**：保持 expected-map 来源口径、保留两个 gold=0 的已知反例；资格、参考修订与额外防护归后续流水线 |

以下为决策包原文（DR2 保留原文仅供追溯，事实前提已更正）。

### DR1 · 扩公共契约：新增来源与 R2E 私有材料模型（T0：公共契约）

- **要决定什么**：是否把 `source` 枚举扩为 `swe_gym_lite | r2e_gym_subset`，新增 `PrivateGradingBundleR2E`，并把 `HostGradingView.grading` 改成按 `schema_id` 判别的联合。
- **现有代码事实**：三处 `Literal["swe_gym_lite"]`；私有材料与 spec 入口全是 SWE 形状（§2.1）。
- **方案**：A 判别联合 + 新模型（推荐）；B 把 R2E 材料塞进通用 `dict` 载荷；C 为 R2E 另建一套 controller / task face。
- **推荐 A**：类型校验与泄漏断言都保留；SWE 序列化不变；两个入口共用一个适配器。B 丢掉 fail-closed 校验；C 复制一整套读取口，之后每次改动都要改两处。
- **长期代价**：A 以后每加一个来源多一个联合分支（可控）；B 的代价是运行期才发现材料缺字段；C 是持续的双份维护。
- **以后还能改的**：字段名、pins 目录布局。**改起来贵的**：`task_id` 前缀与 `instance_id` 形态（进 manifest、账本与训练数据身份）。

### DR2 · parser 键归一化口径（T0：来源判定口径）

- **要决定什么**：评分用 `prime_v1` 还是 `sym_ansi_v1`。
- **事实**：pillow 6 题期望键全带 ANSI；`prime_v1` 下这 6 题 gold 恒 0；独立 runner 的 46/48 基线是 `sym_ansi_v1` 跑出来的。
- **方案**：A 评分用 `sym_ansi_v1`，版本写进 `grader_version`，sidecar 同时记 `prime_v1` 的结果供对外比较（推荐）；B 评分用 `prime_v1`（与官方逐字一致，放弃 pillow 6 题）；C 按题配置。
- **推荐 A**：去掉的是数据侧的显示转义，不改变任何测试的通过与否；与我们唯一的对账基线一致。代价是这 6 题的分数不能称为"官方口径分数"。
- **以后还能改**：随时可切版本（版本进报告，可追溯）。

### DR3 · 逐题派生镜像、隐藏测试的放法与分工（T0：环境与安全边界；含 T1 分工）

- **要决定什么**：R2E 的环境准备做成什么、隐藏测试放哪、谁来构建。
- **事实**：原镜像在沙箱身份下 48/48 不可用；答案一条 git 命令可得；M3 已实测布置 b 与 git 清理各 48/48 不改判分。
- **方案**：A 逐题派生镜像 = 搬迁解释器 + `chown /testbed` + git 清理 + 把 `/r2e_tests` 挪到 root 专属目录（0700），bundle 记树摘要，评分时由 root 恢复并核对；rh2 通过环境覆盖表引用（推荐）。B 同 A，但隐藏测试内容随私有 bundle 下发、镜像里彻底删除（更干净，ingest 要依赖一次 Docker 抽取）。C 不做派生镜像，每次评分由 root 现场就地放权（`chmod o+rx /root` + `chown`，每次付 11–149 s 且候选能列出 `/root`）。
- **推荐 A**，分工：**B 线 Codex 出配方并构建、产出覆盖表数据**（它有 M3 的脚本与证据，也负责环境配方）；Claude 实现覆盖表的模型、driver 引用与三条预检。git 清理一并放进配方——M3 已验证、几乎零成本；它是答案泄漏的基本卫生，不属于待定的"反作弊力度"。
- **长期代价**：A/B 都要维护派生镜像（与 D4=B 同一件事，早晚要做）；C 省事但每次评分都慢，且把 `/root` 暴露给候选。
- **以后还能改**：A → B 的迁移只动可信 setup 的取材位置。**改起来贵的**：覆盖表的身份字段（进账本与资格键）。

### DR4 · 接线阶段一律按来源原样判（范围确认）

- **要决定什么**：L4 的 Q1（期望里的 FAILED/ERROR 键）、Q5（仓库测试支撑模块是否恢复）、Q6（单键信号宽度）在本片如何处理。
- **推荐**：本片全部"按来源原样"——精确匹配、什么都不额外恢复、不因信号窄而剔题；逐题事实进账本与对账页，题目取舍与 expected 修订留给流水线阶段。理由：先让 rh2 与来源 runner 逐题一致，才有基线去评估任何修订；也符合"不在无真实模型证据时加码防护"的方向。
- **代价**：接线通过的 48 题里有 20 题的期望混着环境缺陷，**不能**据此进训练题单（§0 第 5 条）。

## 9. 本片不改变的语义

binary_v1 二值 reward；infra 族无 reward；SWE 路径的 F2P/P2P 官方口径、P-A 三路判定、`--init`、baseline 政策 v1/v2 的摘要；S1 unsafe 整组 DROP；D1–D4、R2E 方案 A、用户 09-19 对反作弊与资格记录的分期。

## 10. 与其它工作的关系

- B 线 Codex 的环境维修（SWE 派生镜像）与本片并行；覆盖表设计成两边可共用，但 SWE 路径不在本片接入。
- B 线 09-19 runtime finding（manager 跨实例清扫活跃容器）：manager 半边已由 A 线 Claude 修复（`startup()` 不再跨 manager 清扫；候选段是否完整以收口标记与 exec 退出码为准，被信号终止 → infra）；driver 半边（R-0）由本线完成，见 §11。本片基于该快照实施，不再维护"独立 `label_prefix` 绕行"这类临时做法。
- 正式资格记录仍待流水线产出；R-f 的 P-A 对照沿用 driver 的 `--qualification-ledger`。

## 11. 实施与复核记录

| 日期 | 进展/决定 | 下一步 |
| --- | --- | --- |
| 2026-09-20 | Claude 起草本计划：核对代码事实（来源枚举封闭、私有材料与 spec 入口为 SWE 形状、方案 A 助手无生产调用、`.venv` 在工作目录内、driver 单镜像覆盖）与来源事实（L4 / M3）；六个切片、验收样例、DR1–DR4。未改代码。 | A/B 线 Codex 复核；用户决定 DR1–DR4；R-a / R-b 可在决定后立即开工。 |
| 2026-09-20 | Codex A 完成[计划复核与 CPU 探针](r2e_grading_wiring_review_20260920/README.md)：方向可行，2 项 P1 / 3 项 P2。DR2 复用了已于 09-09 撤回的 ESC 转录误读；固定 Prime 函数与本地 runner 重放 336 份既有日志，reward 全部一致，带 ANSI 的 pillow 六题 24 次 gold 均为 1。另需补 manager 的来源语义与全缺席判据、纠正同组混来源验收、24/48 输入路径、单镜像 chown 成本推断。 | 作者逐项修订后推进切片；建议 DR1/DR3 选 A、DR4 保持既定分期，DR2 撤回当前二选一。本行是审查意见，不是用户批准。未改生产代码、未运行 Docker/远端、未提交。 |
| 2026-09-20 | Codex B 完成[独立复核](r2e_grading_wiring_review_20260920/B_review.md)：重跑 A 探针确认五项；补做 336 日志逐键一致与 48 gold 应用结果一致（补丁字节均不同）。补充 `.venv` 预检与基线先后、真实自定义 runner 收尾、12 题 dirty tree 等局部澄清；未新增架构或训练语义阻塞。 | 作者修订后按切片实施；DR1/DR3 推荐 A、DR4 保持来源对账、DR2 撤回。未改生产代码或配方，未跑 Docker/远端，未提交；不替用户批准。 |
| 2026-09-20 | **按 A/B 线复核修订本页**（逐项处置见下表）；用户决定 DR1=A、DR2 撤回、DR3=A、DR4=接线阶段不处理题目。R-0（driver 收口状态外显）已实施：`replay_grade.final_exit_status`（最终仍有未关评分容器 → 退出码 3；停批 → 2；历史清理失败但最终已清 → 0 且留诊断）、CLI 把基线契约矛盾 / grader scope 无法确认终止转成停批退出码而不是 traceback、账本 `test` 块增 `exec_exit_code` / `segment_completed`（取自 A 线新增的 sidecar 事实）；B 线环境维修的两份实验脚本已适配被删除的 `orphan_min_age_seconds`（`replay_with_install_recipe.py` 容忍缺席，`probe_grading_namespace.py` 标注为修复前行为的历史反例）。本机验证（含 A 线未提交的 manager 修复）：ruff 无告警，非 Docker 1451 passed / 1 skipped，Docker 35 passed。未改 R2E 代码，未提交。 | R-a / R-b 开工（待用户指示）；派生镜像配方的派发由用户安排。 |

### 11.1 对 A/B 线复核意见的处置（2026-09-20）

| 项 | 处置 | 落点 |
| --- | --- | --- |
| A-R1 DR2 基于已撤回的误读 | **accepted**。这是我第二次犯同一个错：09-09 已 accepted 过 Codex 的更正，写本计划时照抄了 L4 适配器卡的旧说法而没有回查。撤回 DR2 与双版本设计，固定 `prime-envs@c4d04dfe` 的真实实现，验收改为与固定上游函数对拍 336 份日志 | §0、§2.2、§3.2、§5.1 R-b、§8；L4 适配器卡 §5 与 L4 报告 Q2 各加一行勘误指针 |
| A-R2 manager 来源语义与全缺席判据 | **accepted**。`grading_semantics` 进 `GradingEnvSpec`、在 parser 之前确定并进所有报告分支；R2E 的"参考全缺席"按键在场关系判；验收改为真实 `grade()` 产出七种形态；`manager.py` 列入 R-b/R-c 共享文件。按 B 线的收窄：旧 diff/workspace 分支的 `patch_apply_failed` 不作为 R2E 必跑场景（正式冻结路径在候选阶段 apply 失败即 `apply_failed`，不进 grader） | §2.1、§3.2、§3.3、§4、§5.1 |
| A-R3 混来源验收口径 | **accepted**：同批不同组 + 同组不同题被拒的反例 | §2.1、§5.1 R-e |
| A-R4 输入只有 24 行 | **accepted**：改用 `M3/probe_data/r2e_candidates_full.jsonl`（48 行） | §3.1 |
| A-R5 属主与成本 | **accepted**：不再声称构建期 chown 消掉运行期成本；先量正式 profile 小样本；不做权限重构 | §2.2、§3.5、§6 |
| A §2 分期六条 | **accepted**：R-f 的完成表述、默认来源集合、正式镜像两种表示途径、R-0 归 B 且在 R-f 前完成、先代表题后全量、共享文件串行 | §3.1、§3.5、§4、§5.2、§10 |
| B-B1 `.venv` 排除区路径摘要 | **accepted**：预检移到首次 census 之后、`-B -I -S`；冷镜像 fixture 往返 | §3.4、§3.5、§5.1 R-d、§7 |
| B-B2 gold 比较应用结果 | **accepted** | §3.1、§5.1 R-a |
| B-B3 三处事实 / 细节 | **accepted**：脏树 12/48；自定义 runner 有 pytest 形状收尾；自证 helper 的成功状态置位时机 | §2.2、§3.3 |
| B §3 范围与顺序 | **accepted**：隐藏测试方案 A；不重开 tag 重指；R-0 先于真机批；基于 A 线修复快照；代表题优先 | §3.5、§4、§10 |

### 11.2 A 线修订复核与 R-0 聚焦审查（2026-09-20）

Codex A：[完整复核、探针与结果](r2e_grading_wiring_review_20260920/followup_20260920.md)。计划修订通过，上一轮五项及 B 线补充均已落实；R-a / R-b 可开始，无新 T0 或 P0/P1。R-0 的正常、晚清成功、最终残留、typed 停批、停批后晚清成功五条退出码主路径通过；exec=137 的报告与事实运输保持 infra / None。

两项非阻塞 P2 留给 driver 后续窄改：CR1 未捕获异常/取消继续传播时，`finally` 仍可能打印 `final_status.exit_code=0`；CR2 scope 收口异常时，已经落盘的日志/sidecar 未挂入停批账本，取消分支的新 `test` 块也未填。建议由 B 在 R-f 异常对账或摘要消费者启用前补齐，不阻塞材料/parser 切片；保持既有停批和 reward 语义，不新增恢复机制。

独立验证：21 个维护测试通过，8 案 CPU 控制流探针与 1 个真实 CLI 子进程；相关 ruff 通过，测试文件末尾多一空行留提交前清理。本轮未运行 Docker/远端/全套测试，未改生产代码或提交；这不是 R2E 实施验收。
