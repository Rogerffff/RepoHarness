# 验收记录（Claude，2026-09-24）

按 [README §8](README.md#8-验收标准claude) 逐包验收；每包写：机械核对、抽题独立重跑、共享文件与保护路径、远端清理、对记录的更正、未决项。状态词：**已验证**＝我有独立运行或读原始证据；**已核对**＝我读了记录与其引用；**待**＝等中央复跑或用户决定。

## P1（aiohttp ×5、coveragepy ×5）—— 通过，8 题待 R13

| 项 | 结果 |
| --- | --- |
| ① 机械核对 | `check_records.py` 10/10 记录、R01–R20 全覆盖、证据引用全部存在（rc 0）。**已验证** |
| ② 抽题独立重跑探针 | coveragepy `ea6906b0`、aiohttp `4075c653`（含 P1 的复现脚本）：`derived` 全部字段与 P1 的 `dev_probe.json` 逐项相同，关键值（PY_INFO / PIP_VERSION / IMPORT_FROM_TMP_RC / 公开测试 rc / REPRO_RC / git 状态）相同，两题 `REPRO_OBSERVED=1`。证据 `runs/r2e_env_repair_20260924/_accept/p1/`。**已验证** |
| ③ R13 | 待中央复跑并入（8 题 `pending_checks: ["R13"]`；`240da100`、`016af5f6` 已有 reps 第二次运行）。**待** |
| ④ 远端 | 无 P1 容器残留（`docker ps -a` 只见中央复跑与 P3 的容器）；`r2e_snapshot.sha256` 388 文件核对通过；`/work/replay`、`/work/r2e_derived` 文件时间未变。**已验证** |
| ⑤ 仓库 | `s2_r2e/`、`rh2/src`、`rh2/scripts`（本轮工具除外）无新改动；共享文件 sha256 与派发时一致（P1 未改）。**已验证** |
| ⑥ 提案 | 材料修订只有提案（`016af5f6`，选项 A/B/C，推荐 A，已登记 decisions T0-1 与 dispositions）；无资源配方需求。**已核对** |
| ⑦ 包报告 | 建议 / 已实施 / 已验证分列；逐题证据路径可打开。**已核对** |

**读记录时的核对结论**：`240da100` 与 `016af5f6` 的 findings 与 gold 日志、来源执行记录一致（我重读了 `016af5f6` 的 M3 与 R-f 日志里该键的 PASSED 行）；`4075c653` "期望 3 键＝C 解析器扩展未构建"与 gold 日志原因行一致。

**对记录的更正（验收时改）**：三份记录（`240da100`、`61833518`、`ea6906b0`）的 `solver_conditions.pip` 写成 "present（无 pip）"，与 issues 和探针 `PIP_VERSION` 矛盾，改为 `absent`，并在记录里加 `review_notes`。值本身（无 pip）按探针为准。

**P1 提出、我采纳的流程 / 工具改动**：解析器 v2（`WHICH_*` 键）+ `--reparse`（各包本地 `dev_probe.json` 已重建，远端副本保持原样）；README §9 更正（`016af5f6` 只有 M3 参考）；decisions E06 备注；known_issues 三个新族。**未采纳（记入下一轮待办）**：探针加裸 `pytest` 检查、公开测试模块由审查者指定、`PUBLIC_*_TAIL` 改记根因行、复现脚本经 stdin 运行（`sys.path[0]` = cwd）、汇总器三方比对期望来源——本轮不改探针语义，避免四包结果不可比。

## P2（datalad ×5、numpy ×7）—— 通过，10 题待 R13

| 项 | 结果 |
| --- | --- |
| ① 机械核对 | `check_records.py` 12/12（rc 0）。**已验证** |
| ② 抽题独立重跑探针 | datalad `19f5b450`、numpy `d89bc4bb`（含 P2 的复现脚本）：`derived` 与关键值与 P2 的 `dev_probe.json` 逐项相同，两题 `REPRO_OBSERVED=1`；datalad `chown` 120 s（与 P2 记录的 61–112 s 同量级，机器并发所致）。证据 `runs/r2e_env_repair_20260924/_accept/p2/`。**已验证** |
| ③ R13 | 10 题待中央复跑；numpy `2f4a9650` 配方下已有两次一致（`qualified_with_recipe`）；datalad `58ba5165` `held_material`。**待** |
| ④ 远端 | 无 P2 容器与 unit 残留；保护路径未动。**已验证** |
| ⑤ 仓库 | 共享文件由我合并（known_issues 六处更新 + 五个新族、dispositions、decisions T0-2 / E11 / E04 状态、README numpy ×7 与 sys.path 措辞、checks R14 措辞）；`s2_r2e/`、`rh2/src`、`rh2/scripts` 无新改动。**已验证** |
| ⑥ 提案 | datalad `58ba5165`：根因经字节对照 + 沙盒 dry-run 确认（B1 / A 都 gold 4/4），提案完整（选项、推荐 B1 + 先隔离、长期代价、验收要求）。**已核对** |
| ⑦ 包报告 | 状态词分列；焦点题的数值依据（4096.2 MiB 两份 + 340 MiB 基线 ≈ 4436 MiB，实测 4429–4439）我核过账本峰值。**已核对** |

**读记录时的核对**：datalad 16c1/9ba5 的 5 个 FAILED 键原因行（`got multiple values for argument 'path'`）与 gold 日志一致；6b6fa389 的 `~` 转义与 Python 3.7 行为一致。P2 指出的两处工具问题（M3 导入判断只取首行 → datalad 两题误报；`checks` R14 措辞）已修：汇总器改为看整段（datalad 两题不再标 sys.path 条件），族名改为 `testbed_must_be_on_sys_path`。

## P4（pillow ×7、scrapy ×5）—— 通过，11 题待 R13；3 题材料问题待用户

| 项 | 结果 |
| --- | --- |
| ① 机械核对 | `check_records.py` 12/12（rc 0）。**已验证** |
| ② 抽题独立重跑探针 | scrapy `9a15fcf8`、pillow `2b061b68`（含 P4 的复现脚本）：`derived` 与关键值与 P4 的 `dev_probe.json` 逐项相同；scrapy 复现 `REPRO_OBSERVED=1`，pillow `2b061b68` 两边都是 0（题面所述行为在 base 上触发不了——与 P4 结论一致）。证据 `runs/r2e_env_repair_20260924/_accept/p4/`。**已验证** |
| ③ R13 | pillow `3ac9396e` 已三次一致；其余 11 题待中央复跑。**待** |
| ④ 远端 | 无 P4 容器与 unit 残留（over-fix 评分容器已清理，账本 `cleanup.removed`）；保护路径未动。**已验证** |
| ⑤ 仓库 | 共享文件由我合并（dispositions 三条 needs_decision、decisions T0-3/4/5、known_issues 新族 flippable / relocation_artifacts / prompt_quality / public_test_noise）。**已验证** |
| ⑥ 提案 | 三份提案完整；scrapy `9a15fcf8` 的"更完整修复被判 0"有真实 RH2 评分证据（`ledger_overfix.jsonl`，run_id `r2e-envrepair-p4-overfix`）和离线重算；"只删期望键无效"的判断与 `scoring.expected_map_matches` 的并集口径一致。**已核对** |
| ⑦ 包报告 | 状态词分列；跨题发现（期望键带 ANSI、自定义 runner 解析、gold 与 hygiene 不相交、泄漏面）都有证据路径。**已核对** |

P4 指出的工具问题已修：`pip_ok` 判断（"No module named pip" 也判 true）→ 解析器 v3，各包本地 `dev_probe.json` 已重建；汇总器原因行提取先去 ANSI（pillow 两题的原因行现已取到）。

## P3（orange3 ×7、pandas ×7）—— 通过，12 题待 R13；8 题材料提案待用户

| 项 | 结果 |
| --- | --- |
| ① 机械核对 | `check_records.py` 14/14（rc 0）。**已验证** |
| ② 抽题独立重跑探针 | pandas `32dd55cb`、orange3 `4014f248`（含 P3 的复现脚本、orange3 带 xvfb 前缀）：`derived` 与关键值与 P3 的 `dev_probe.json` 逐项相同，两题 `REPRO_OBSERVED=1`；orange3 `chown` 169 s。证据 `runs/r2e_env_repair_20260924/_accept/p3/`。**已验证** |
| ③ R13 | 12 题待中央复跑；`22e98f8f`、`19c5eea5` 已有两次一致。**待** |
| ④ 远端 | 无 P3 容器与 unit 残留（memprobe 与 2 GiB gold 复跑共 2 次尝试，未超上限）；保护路径未动。**已验证** |
| ⑤ 仓库 | 共享文件由我合并（known_issues：orange3 内存族改 not_an_issue、pandas fixture 族、orange3 依赖伪影族、上游伪影族、chown 成本族、prompt_quality 追加 7 条；decisions T0-6 / T0-7 / E12；checks R12 措辞；汇总器 R12 提示语）。**已验证** |
| ⑥ 提案 | pandas 7 题共用的 fixture 不可达分析：我核对了 `4ec87eb9` 的 gold 日志 `fixture '…' not found` 计数与 ERROR 键数相等的说法（族级证据 `fixture_check/`），"只删期望键无效"与并集口径一致；orange3 `9b5494e2` 的 sklearn / SciPy 版本证据在 `fixture_check/orange3_9b5494e2_versions.txt`。**已核对** |
| ⑦ 包报告 | 状态词分列；内存结论有 memprobe 采样 + 真实 grader 2 GiB 复跑两条独立证据（`ledger_gold_mem2g.jsonl` 两行 reward 1、同一派生镜像 ID）。**已核对** |

**读记录时的核对**：P3 对 R12 的反驳成立——我把 R12 的 60% 判据降为"提示"（E12），不再作为资源 issue 的依据；orange3 不设档位。P3 的题面观察里 orange3 `22e98f8f`（题面 Example Buggy Code 逐行等于 gold 修复）是答案泄漏候选，已放进 prompt_quality 族首位，交题意筛查。

## 中央复跑（R13）—— 完成，48/48 一致

- 两路 unit（noop / gold）各 48 行，`final_status.exit_code=0`，评分容器全部清理；账本与 196 份日志 / sidecar 回传 `runs/r2e_env_repair_20260924/_rerun2/`。
- `collate_facts.py --extra-evidence` 并入后 R13：48 题 noop 与 gold 的 reward、mismatched / missing 集合与 R-f 逐条相同（`R13_repeat_noop` / `R13_repeat_gold` 48/48 pass）。P1 关注的 aiohttp `1c1c0ea3` 时序敏感键第二次仍 PASSED（两次一致，`timing_sensitive_key_watch` 族保持 open，样本仍少）。
- `reconcile_r2e.py` 对第二次运行与独立 runner 逐键对账：94/96 agree，2 行不一致仍是 numpy `2f4a9650` 默认 profile（资源假阴性），与 R-f 相同。证据 `runs/r2e_env_repair_20260924/reconcile_rerun2/`。
- `apply_r13.py` 把 R13 写回 41 份记录（`unknown` → `environment_qualified` 30 份；已是 qualified / needs_decision 的 11 份只补 R13 证据）；7 份本已有两次运行、不需改。之后 `check_records.py` 48/48 零问题（`runs/r2e_env_repair_20260924/check_records_final.json`）。
  - **09-24 晚更正（Codex R1）**：这 30 份"兜底提升"把"已归因"当成了"已解决"。按 E14 重核后，其中 22 份维持 `environment_qualified`（无未完成项），7 份（pandas ×6、orange3 `9b5494e2`）改为 `grading_ok_open_items`，numpy `43e333e2` 先改为 `grading_ok_open_items`、修好后现为 `qualified_with_recipe`（E15）。pandas `19c5eea5` 是审查者直接写的合格，也按 E14 改为 `grading_ok_open_items`。`apply_r13.py` 已去掉兜底提升。

## Codex 复核更正与 T0 实施（09-24 晚）—— 已实施、已验证

**Codex R1–R3 的更正（不需机器，已落）**：资格口径新增 `grading_ok_open_items` 与 `qualified_with_revision`，逐题 `open_items`，`apply_r13.py` 不再兜底提升（E14）；期望非 PASSED 键 16 → 20 题；探针独立重跑 8 题的一致性说法改为"统一用解析器 v3 重算后逐字段一致"；T0-5 / T0-6 / T0-7 的推断按 Codex R2 收窄（decisions 表内已标）；`r2e_grading_wiring_20260920.md` 两处措辞。

**T0-1 / T0-2 实施（E13）**：修订走摄入面。封板修订单 `s2_r2e/revisions/material_revisions_v1.json`（`r2e-mr-001` 期望单键、`r2e-mr-002` 隐藏测试一行导入），pins v2、manifest v2，ingest 从来源原文重放并核前后摘要，评分面新增 `material_revisions` 标记，消费期校验标记与修订单一致；隐藏测试修订另由派生配方 `material_v1.sh` 写入私有目录（写前核原摘要、写后核新摘要）。修订前产物原件存 `s2_r2e/ingest_history/source_v0_20260923/`。新增测试：ingest 修订 5 例、解析器语料 1 例、对账 2 例。

**numpy `43e333e2` 环境配方（E15）**：`recipes/env_pins_v1.json` 把 hypothesis 固定回仓库 `test_requirements.txt` 的 6.24.1，派生配方 `env_v1.sh` 离线安装核过摘要的 wheel。选型依据是同一派生镜像上的三组诊断：

| hypothesis / pytest | 相关模块 `numpy/ma/tests/test_extras.py` | 隐藏测试 noop / gold | 证据 |
| --- | --- | --- | --- |
| 6.124.1 / 8.3.4（来源） | 收集失败 rc 4 | 87/88 / 88/88 | `runs/r2e_t0_revisions_20260924/diag43/v0.*` |
| 6.79.4 / 8.3.4（其它 numpy 镜像的版本） | 仍报 `HealthCheck.all()` 弃用错误 | — | `diag43/v1.public.txt` |
| **6.24.1 / 8.3.4（采用）** | 78 passed / 10 failed，失败全在无关的 TestCov / TestCorrcoef；TestAverage 6 passed | 87/88 / 88/88 | `diag43b/h.*` |
| 6.24.1 / 6.2.5 | 88 passed | 87/88 / 88/88 | `diag43b/hp.*` |

不换 pytest 的理由：pytest 同时是 grader 跑隐藏测试用的，换大版本改动面更大；剩下的 10 个失败已核为与本题修复（`ma.extras.average`）无关。

**真实验证（A 线机器上的独立目录 `/work/b_r2e/`；本机代码与 `s2_r2e/` 同步后逐文件核 sha256（首次 407 个文件，改构建工具后再同步一次，两次都 SNAPSHOT_OK）；真实 grader + 覆盖表，期限 1800/1800，各 2 次）**：

| 题 | 派生配方 / 镜像 | noop ×2 | gold ×2 | 其它核对 |
| --- | --- | --- | --- | --- |
| coveragepy `016af5f6` | `r2e_derive_v1`（与 R-f 同配方摘要，换宿主后镜像 ID `565a8f36…`） | 0，14/15，只差目标键 | 1，15/15 | 与 M3 逐键一致 |
| datalad `58ba5165` | `r2e_derive_v1+material_v1`，`a5d5a8c2…`；私有树 `86561f1a…` = 评分面 | 0，2/4（api、cmdline） | 1，4/4 | 与沙盒 dry-run B1 逐键相同；修订后无同版本独立 runner |
| numpy `43e333e2` | `r2e_derive_v1+env_v1`，`b8f6f112…`；放行 129 个 hypothesis 路径 | 0，87/88，只差目标键 | 1，88/88 | 与配方前及独立 runner 逐键一致；解题身份下相关模块可收集；探针十项满足、公开入口 rc 0 |

所有运行 `exit 0`，评分容器全部清理。grader 侧导入路径都在 `/testbed`（账本 `observations.RH2_OBS_IMPORT_PATH`）。

**对账（`reconcile_r2e.py`）**：计入的 8 行（coveragepy 4、numpy 4）全部一致；datalad 4 行因隐藏测试已修订而单列（noop 2 行与修订前参考一致，gold 不同是修订本身的效果）。第一次对账把 coveragepy gold 两行标成"M3 账本与自己的日志矛盾"：M3 账本按来源期望算分，工具却用修订后期望重算。已修：期望修订过的题改用倒放出的来源期望互核 M3 账本（倒放逐步核 `sha256_after` / `sha256_before`，对不上即报错），新增 2 个测试；重跑后账本矛盾 0。证据 `runs/r2e_t0_revisions_20260924/reconcile/`。

**记录**：三题记录按新证据更新，旧值留在各检查项的 `previous`，处置改为 `qualified_with_revision` ×2、`qualified_with_recipe`；`dispositions.json`、`known_issues.json` 相应族改 `verified`；`check_records.py` 48/48 零问题（`runs/r2e_t0_revisions_20260924/check_records.json`）；`results_20260924.md` 改由 `render_results.py` 从记录生成。三题的 `facts.json` 与 `facts_summary.md` 保持来源材料下的汇总、不重生成：把修订前后的运行并进同一份汇总会让 R13 把两种材料的结果当成"重复不一致"，所以修订后的证据直接写进记录的检查项与 `posthoc_refs`。

**本机测试（改对账工具后重跑，从 `rh2/`）**：`pytest tests/envpack tests/adapters tests/grading tests/contracts -m "not docker"` 1536 passed / 2 skipped / 61 deselected；`pytest tests/grading tests/envpack -m docker`（本机 Docker Desktop 在跑）39 passed；`tests/adapters_miles` lane A 463 passed / 343 skipped（生产代码改动后跑的，之后只改了脚本与文档）；改动文件 ruff 无告警。~~全目录一起跑时 `tests/contract_slime_async/test_dp_schedule_differential.py` 有 6 个顺序相关失败，单独跑 6 passed，与本轮改动无关（既有问题，未处理）。~~ 根因是对账测试夹具没恢复 `sys.path`（Codex F2），09-24 夜已修，见下文"回应 Codex 聚焦复核"。

## 批次二（09-24 晚）：T0-5 修复、T0-6 代表修复、T0-7 诊断与全池补查 —— 已实施、已验证

**用户决定（09-24 晚）**：T0-3、T0-4 留给后续题意与评分质量筛查；继续做 T0-6 的代表修复、T0-5 的搬迁支撑修复；T0-7 先做窄范围兼容性诊断；按统一决策执行。在静态筛查、基座探针和后续可能的修复之前，没有筛选好的环境池。

**修订机制 v2（E16）**：修订单升到 v2，新增"整份期望替换"（逐键声明增删改）与"隐藏测试新增文件"两类；pins v3、提交记录 schema v3，旧版本全部保留为历史；派生步骤 `material_v2.sh` 支持新增文件。重新摄入后只有 pandas `4ec87eb9` 与 scrapy `cfed9b66` 的评分面变化，其余 46 题逐字节不变（与 `s2_r2e/ingest_history/material_v1_20260924/` 逐行比对）。

**期望怎么重新核定**：先在一次性容器里按 grader 顺序试跑（从私有目录复制隐藏测试、叠加修订草稿、以评分 uid 跑来源入口）。对原材料，这样由 gold 日志重新生成的期望与来源原文**逐字相同**（两题都是），说明试跑与 R2E 生成期望的方式一致。修订后的期望取来源原文做最小改动，并断言与两次修复后 gold 试跑逐键相同。

| 题 | 修订 | 试跑 noop（两次） | 试跑 gold（两次） | 正式 noop ×2 | 正式 gold ×2 |
| --- | --- | --- | --- | --- | --- |
| pandas `4ec87eb9` | `r2e-mr-006` 私有 conftest 原样摘出 base 的两个 fixture；`r2e-mr-007` 期望删 2 个 ERROR 键、加 13 个参数化键 | 4 失败（原有 allNA 两键 + 题面场景 `NA_float[Float32/Float64]`） | 237 全过 | 0，233/237 | 1，237/237 |
| scrapy `cfed9b66` | `r2e-mr-003` 补回 `test.egg`；`r2e-mr-004` 两处自引用改 `r2e_tests.test_2`；`r2e-mr-005` 期望 3 键改 PASSED | 2 失败（`test_load_object`、`test_instances_from_settings`） | 9 全过 | 0，7/9 | 1，9/9 |

正式运行在 A 线机器，派生配方 `r2e_derive_v1+material_v2`（镜像 `b4ff9483…` / `5e1679ba…`），期限 1800/1800，四次都与试跑逐键相同，grader 侧导入路径都在 `/testbed`，无残留容器。scrapy 另跑了两个单项变体：只加 egg 修好 `test_walk_modules_egg`，只改路径修好两个中间件键。对账把这 8 行单列（隐藏测试已修订，没有同版本独立参考）。

**T0-7 诊断（E17，不改材料）**：

| SciPy | noop 失败键 | gold 失败键 |
| --- | --- | --- |
| 1.7.3（来源） | 两个目标键 + 四个期望 FAILED 键 | 四个期望 FAILED 键 |
| 1.4.1 | 两个目标键 + 两个 scorer 键 | 两个 scorer 键（两次） |
| 1.5.4 | 两个目标键 + 两个 scorer 键 | 两个 scorer 键 |

`test_LogisticRegression`、`test_coefficients` 是 SciPy 不兼容造成的，两个 scorer 键另有原因、未定位。本批换版本后的 3 次 gold 警告复跑都出现 lbfgs 未收敛（有限次观察，不证明所有正确候选都会走到出错分支，也不解释两个 scorer 键），两个恢复键的兼容修复得到验证。

**全池补查（E18）**：隐藏测试支撑扫描标出 17 题，逐条归因后没有新的搬迁伪影或 fixture 缺口，新发现 coveragepy `5dbbe143` 的隐藏测试依赖修复前版本的测试辅助（低风险，转 `grading_ok_open_items` 交静态筛查）。期望来源三方比对：41 题三者一致，另 7 题的差异都已知或已处理。aiohttp `1c1c0ea3` 时序敏感键加跑 10 次全部 PASSED（累计 14/14），与独立 runner 逐键一致 10/10。

**记录与测试**：`check_records.py` 48/48 零问题（`runs/r2e_t0_batch2_20260924/check_records.json`）；结果表由记录重新生成。本机测试：非 Docker 1558 passed / 2 skipped，Docker 39 passed，miles lane A 463 passed / 343 skipped，改动文件 ruff 无告警。

## 回应 Codex 聚焦复核（09-24 夜）

[聚焦复核](../r2e_t0_review_20260924/README.md)接受 T0-1 / T0-2 / numpy `43e333e2` 三题修复与资格更正，留下两个工具 P2，已修（E19）：

- **F1 对账工具套错材料版本**：改为按账本自带证据逐行判定。R-f 三题 6 行恢复 6/6 一致，datalad 不再被错误排除；上一批 12 行仍是 8 行一致加 4 行单列；强制指定与证据不符时标"版本未匹配"。
- **F2 测试夹具污染导入路径**：两个动态加载脚本的夹具都在结束时恢复 `sys.path`；对账测试、构建工具测试与差分测试连跑 14 passed，Codex 给的那对文件的顺序失败已消除。
  **但全目录一起跑仍有同样的 6 个差分测试失败，来源不同**：排除我的两个测试文件后照样出现；`tests/adapters` 与 `tests/adapters_miles` 两个目录一起、在差分测试之前运行时才出现，任一目录单独加差分测试都全过。这些都是其它线的测试，我没有改，交 A 线 / Codex 定位。复现（从 `rh2/`）：

  ```
  .venv/bin/python -m pytest -q -p no:cacheprovider tests/adapters tests/adapters_miles tests/contract_slime_async/test_dp_schedule_differential.py -m "not docker"
  ```
  **更正（09-24 夜，Codex 批次二复核 F1）**：上面"来源不同、交 A 线"的判断是错的，这 6 个失败同样由 B 线测试引起。`tests/adapters/test_replay_grade.py` 与 `tests/adapters/test_r2e_replay_overlay.py` 各有一个 CLI 测试加载脚本后没有恢复 `sys.path`；二分后又找到 B 线 09-16 夜留下的未跟踪测试 `tests/test_screening_facts.py`，它在模块级执行脚本，同样把 `rh2/src` 插到 `sys.path[0]`，遮住了差分测试要导入的 `reference/slime`。三处都已改为用完恢复，修复后全量非 Docker 测试 0 失败（E20）。
- 复核 §4 的旧文案（dispositions 的旧 scope、scrapy `cfed9b66` 的"三个死键"、known_issues 的"16 题"）已更正；pandas `4ec87eb9` 的旧 `state_if_r13_passes` 随记录重写已不存在。

## 批次三（09-24 深夜）

用户看过 [Codex 批次二复核](../r2e_t0_batch2_review_20260924/README.md) 后决定"你们的建议一致，就按建议做"。本节是实施与验证（E20–E24）。

**复核回应（E20）**

- **F1 导入路径污染**：两个 CLI 测试在加载脚本前 `monkeypatch.setattr(sys, "path", list(sys.path))`；二分又找到 B 线 09-16 夜留下的未跟踪测试 `tests/test_screening_facts.py`（模块级执行脚本），改为执行后恢复。此前"剩下 6 个失败来源不同、交 A 线"的判断是错的，已在上文与 E19 注明更正。
- **F2 静态源码导出**：公开包改为实际解题工作树，见 [static_screening_prep.md](static_screening_prep.md) §5 与下面的"静态筛查固定材料"。
- orange3 诊断措辞收窄为"有限次观察"（5 处）。

**T0-6 第二步：pandas 另 6 题（E21）**

每题加一份私有 `r2e_tests/conftest.py`，从各自 base 提交的 conftest 链原样摘出隐藏测试实际请求的 fixture，期望按修复后 gold 重新核定。第一版草稿按报错补 fixture，32dd 漏了 `int_frame`、`mixed_float_frame`，7dd3 漏了 `names`：pytest 对每个用例只报第一个找不到的 fixture，试跑还剩 4 个 ERROR。改为由 `extract_fixtures.py` 新加的 `requested_fixtures` 从隐藏测试原文一次算全，6 题的清单与试跑一致；代表题 4ec87eb9 的静态结果也与已封板的 `r2e-mr-006` 相同。

| 题 | fixture | 来源 ERROR 键 | 期望变化 | 修复后 gold | 正式 noop / gold（各 2 次） |
| --- | --- | --- | --- | --- | --- |
| 19c5 | 6 个 | 17 | 删 6、加 13、改状态 11 | 162 全 PASSED | 161/162、162/162 |
| 294c | `float_frame` | 1 | 改状态 1 | 21 全 PASSED | 20/21、21/21 |
| 32dd | 7 个 | 13 | 改状态 13 | 92 全 PASSED | 90/92、92/92 |
| 7dd3 | `names`、`sort` | 4 | 删 4、加 16 | 46 全 PASSED | 44/46、46/46 |
| 8778 | `idx`、`join_type` | 9 | 删 8、加 32、改状态 1 | 58 全 PASSED | 56/58、58/58 |
| f656 | `join_type`、`using_array_manager` | 12 | 删 10、加 40、改状态 2 | 353 全 PASSED | 350/353、353/353 |

展开键的来历：参数化 fixture 可达后，用例按 fixture 的参数展开，键名多出参数 ID（例：7dd3 的 `test_intersection_empty` 展开成 `[None-names0]` 到 `[False-names2]` 共 6 键）。只改状态的 294c、32dd 用文本替换，键集合与顺序不变；其余 4 题整份替换，删除键原位换成展开键，其余行逐字不变。试跑核对五件事都成立：原样材料下由 gold 日志重建的期望与来源原文逐字相同；补 conftest 后 noop、gold 各两次逐键相同；保留键状态不变；修复后 gold 全 PASSED；目标键（noop 失败、gold 通过）修复前后一致，新活过来的键在 noop 下也都 PASSED。

**T0-7 方案 B：orange3 `9b5494e2`（E22、E23）**

- 第一次构建失败：`env_v1.sh` 装完 wheel 用 `importlib.metadata` 核版本，这个模块从 Python 3.8 起才有，本题解释器是 3.7.9。新增环境步骤 `env_v2.sh`，只把读版本换成只用标准库的 dist-info 读法（同名分发必须恰好一份）；配方条目用 `env_step` 选步骤。`env_v1` 的 Dockerfile 与配方摘要逐字节等于 numpy `43e333e2` 现有镜像的构建记录（`0cda3024…`，已写进测试）。新读法在 numpy 派生镜像（3.10）与 orange3 镜像（3.7.9）上各验了一次。
- 镜像 `r2e_derive_v1+env_v2`（配方摘要 `51227719…`）：scipy 1.7.3 → 1.5.4，venv 只在登记路径内变化（635 个文件），以沙箱身份读到 1.5.4，其余复核全过。
- 原样材料试跑 noop、gold 各 3 次逐键相同：gold 只有两个 scorer 键 FAILED；据此写 `r2e-mr-020`（两个恢复键 FAILED → PASSED）。正式 noop 0（11/13）×2、gold 1（13/13）×2。两个 scorer 键保持未完成项（`grading_keys_unexplained`），交后续题意与评分质量筛查。

**封板与对账（E24）**：修订单 v3（v2 的 7 条逐字不变 + 13 条），pins v4（`91bcf90c…`），产物提交记录 `adbd27a1…`；只有这 7 题的评分面与环境包变化，公开面、验证面 48 题逐字节不变。28 行正式记录与一次性容器试跑逐键相同；对账 28 行都判定为修订版材料、版本未匹配 0，pandas 24 行按隐藏测试已修订单列、orange3 4 行按环境配方单列，M3 账本矛盾 0。

**静态筛查固定材料**：[r2e_static_prep_20260924/materials.md](../r2e_static_prep_20260924/materials.md)。48 题的公开包（实际解题工作树：base blob 字节 + 12 题镜像初态差异 + 未跟踪构建文件）、私有包（120 个隐藏测试文件逐个核过评分面摘要）与历史包；15 张镜像逐文件比对一致，覆盖三类脏树；33 题没有镜像，缺 `install.sh` 等只在镜像里的文件，逐题写明。为核对第三类脏树新拉了 aiohttp `240da100`、`61833518` 两张来源镜像。

**记录与测试**：`check_records.py` 48/48 零问题（未完成项词表加了 `grading_keys_unexplained`）；结果表由记录重新生成；dispositions、known_issues、提案状态、HTML 一览已同步。测试结果见下方"测试"。

**测试**（从 `rh2/`，本机 Docker 在运行）：全量非 Docker `pytest -m "not docker" tests` 2374 passed / 344 skipped / 0 failed；`pytest -m docker tests/grading tests/envpack` 39 passed；本批改动文件 ruff 无告警，`env_v2.sh` 过 `bash -n`。第一次全量跑出 1 个失败（`tests/adapters/test_startup_fix_1_activation.py::test_launch_claude_code_is_stateless_and_concurrent_executions_keep_their_own_env`，`_Sandbox` 没有 `exec`）：A 线正在改的未提交代码里，`bringup.py`（22:16）先改成调用 `sb.exec`，同一测试的替身在 22:26:18 才补上 `exec`，而我那次全量约 22:26:09 开始加载测试，拿到的是改到一半的文件；单独重跑 3 次都通过，全量重跑 0 失败。这是与 A 线并行改动的时间窗口，不是 B 线改动引起的，也没有改 A 线的文件。

## 总结

四包全部通过验收。48 题当前环境侧状态（09-24 深夜批次三后）：`environment_qualified` 32、`qualified_with_recipe` 2、`qualified_with_revision` 10、`grading_ok_open_items` 4、`needs_decision` 0，见 [README §11](README.md#11-结果与收口2026-09-24) 与 [results_20260924.md](results_20260924.md)。环境侧状态不等于入池。环境阶段已没有待用户决定的事项：T0-1 / T0-2 / T0-5 / T0-6（代表题与第二步）/ T0-7 方案 B 都已实施并验证，T0-3、T0-4、coveragepy `5dbbe143` 与 orange3 `9b5494e2` 的两个 scorer 键交后续题意与评分质量筛查。静态筛查的固定材料已准备；何时开工、是否派审查 sub-agent 由用户定。R-f 机器 SSH 报主机密钥变化，未再登录；验证都在用户借给的 A 线机器上完成，证据已回传，机器上无残留容器，B 线镜像与目录的清理由用户决定。
