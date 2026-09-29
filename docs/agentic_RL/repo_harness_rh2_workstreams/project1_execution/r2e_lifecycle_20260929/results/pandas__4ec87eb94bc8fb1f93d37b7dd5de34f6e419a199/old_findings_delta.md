# pandas__4ec87eb9 旧结论核对（old_findings_delta）

- **前稿**：`analysis_before_history.md`（读历史前封存）。本稿在读完历史引用与新机实跑结果之后写成。
- **读过的历史**：`runs/r2e_static_prep_20260924/v3/history/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/refs.json` 列出的全部文件：
  - 环境审查的 `screening_record.json`、`findings.md`、`facts.json`（抽读）
  - `known_issues.json`（两个相关族）
  - `decisions.md`（E09、E16、E21、T0-6）
  - `results_20260924.md`
  - 材料修订提案、复现脚本
  - `packages/p3/README.md`（本题相关段落）
- **新证据**（新机，2026-09-28/29）：
  - 正式复验：`runs/r2e_lifecycle_20260929/env_verify/ledger_l2_noop.jsonl` 与 `ledger_l2_gold.jsonl` 各第 8 行。
  - devcheck：agent 身份、正式启动链、真实 CC 2.1.205 + 桩端点。
  - C0 / C1 正式评分。
  - A-2 私有行为对照。
- **路径简写**：
  - `HIST/` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/`
  - `INV/` = `runs/r2e_lifecycle_20260929/inv/pandas_4ec8/`
  - `DC/` = `runs/r2e_lifecycle_20260929/devcheck_rev/unrev/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/`

## 1. 结论变化一览

- **旧处置**：`qualified_with_revision`，且没有未完成项。
  - 作为环境侧结论，仍然成立。
  - 作为题目质量结论，不够：按统一标准 v1，本题有一个未处理的 S1（T2b）。
- **旧记录没讨论过的三件事**：退化候选能不能得 1、结果 dtype、同仓跨题包含。这三项都是本轮新增的。
- **我自己的判断**：从"S1 conditional（等 C0）"改为"S1 成立"。其余判断没有改。

## 2. 旧主张逐条核对

| # | 旧主张（出处） | 判定 | 决定性证据 |
| --- | --- | --- | --- |
| 1 | 修订前期望里的 2 个 ERROR 键，都是隐藏测试搬出原目录后 fixture 不可达造成的；结果确定，与参考一致（`HIST/tasks/pandas__4ec87eb9…/findings.md:5,10`） | 确认 | 修订前日志逐键显示 `fixture '…' not found`（`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-p_e47e4f78.eval.log:31-45`）；M3 独立 runner 结果相同（`runs/env_overnight_20260916/M3/gold_ledger/logs_r2e/pandas/4ec87eb94bc8/gold/a1/test_output.txt:13-26`） |
| 2 | 被掩盖的恰好是题面场景的测试；修订前"只修好全 NA 的部分解理论上能得 1"（`findings.md:16`；R16 的 previous） | 确认（仅指修订前，属推断，没有实跑） | 修订前的目标键只有 `allNA_column` 两个 |
| 3 | r2e-mr-006 原样摘出两个 fixture，没有加别的（`HIST/material_revisions/pandas__4ec87eb9….md:3`） | 确认 | 与 base 的 `pandas/conftest.py:1258-1269, 1329-1343` 做 diff，结果为空；私有 conftest 的 sha256 `632b5ee3…` 与修订记录一致 |
| 4 | r2e-mr-007 删 2 键、加 13 键；修订后 noop 0（233/237）两次、gold 1（237/237）两次（`findings.md:3`；R13） | 确认；新机补了 1 次 | 新机 `ledger_l2_noop.jsonl` 第 8 行：mismatched 同样是那 4 个键；`ledger_l2_gold.jsonl` 第 8 行：237/237；镜像 `85f550e6…` |
| 5 | **R16 当前记录**："修订后 F2P 扩到 4 键……'部分解也能得 1'的推断不再成立"，并据此判 pass | **部分推翻** | 对"只修全 NA"这类部分解，这句话成立，因为 `NA_float` 要求结果为 0.2。但退化候选 C0 正式评分 1.0：`INV/ledger_C0.jsonl` 第 1 行 237/237，投影包含 `groupby.py`；日志 `INV/logs_C0/evallog_replay-r2e-inv-4ec8-C0-0_ba0f9574.eval.log:257-258, 267-268` 显示 4 个目标键都执行且 PASSED。C0 在三种常见来源的 NA 上算错（`INV/pcheck_C0.json`：astype / reindex / 除法依次得 [1.0] / [0.0] / [1.0]，gold 为 [2.0] / [2.5] / [2.0]）。可见 F2P 键区分不了"按 mask 忽略 NA"和"依赖掩码位置恰好是 NaN" |
| 6 | 处置 `qualified_with_revision`，`pending_checks: []`（`HIST/tasks/…/screening_record.json` 的 disposition） | 环境侧确认；质量侧过时 | 同第 5 行：按 v1 §4 第 3 步判为 S1，进训练前必须修 |
| 7 | 期望里已经没有 ERROR 键，"候选在根目录建 conftest 让键翻转、正确解反而得 0"这条路径也随之消失（issues[0].resolution） | 确认 | 当前期望 237 键全是 PASSED。另注：根目录 `conftest.py`，以及候选可以改的 `pandas._testing`，作为作弊方向的通用控制面仍然存在；这属于共享机制，不在本题处置 |
| 8 | 解释器是 `.venv` 3.8.20；pip 24.3.1 有但没有网络；pytest 8.3.4（solver_conditions；R05） | 确认（新机，agent 身份） | `DC/orig/captures/env.out`、`env_import_version.out`；另补 numpy 1.20.3 |
| 9 | 公开测试 `pandas/tests/test_aggregation.py` rc=0（R09） | 被更相关的证据取代 | 新 devcheck 跑的是本题相关的 `test_quantile.py`：agent 侧 222 passed、2 skipped（`DC/orig/captures/public_test_quantile.out`）；gold 私有对照结果相同（`DC/private_control.json`） |
| 10 | 复现脚本 `REPRO_OBSERVED=1`（R09） | 确认 | `DC/orig/captures/repro_issue_example.out`：报错与题面逐字一致，退出码 1 |
| 11 | 仓库内编译；Cython 0.29.37、gcc、make 都在；改 `.pyx` 要自己跑 `build_ext --inplace`（solver_conditions.notes） | 未核实（新机没查） | 本题用不到：修复只改 Python。只改 Cython 内核也修不好，因为 `TypeError` 在调用内核之前、`groupby.py:2957` 的 Python 代码里就已抛出 |
| 12 | 5 个已跟踪改动来自 install.sh，不要 reset；pandas 自带的 pytest 配置不生效（solver_conditions） | 确认 | `DC/orig/attempt.json` 的 `image_facts.initial_worktree` 共 7 行；公开测试照常通过 |
| 13 | HEAD 没有子提交，也没有 remote / reflog（R17） | 确认（新机） | `DC/orig/attempt.json` 的 `stages.sanitize_and_init.git_sanitize`：HEAD 不变，REFS、REMOTES、REFLOG 都是 0；preflight `GIT_HISTORY=ok` |
| 14 | gold 内存峰值 763 MB（R12） | 确认 | 新机 L2 gold 峰值 764 MB。新机测试段耗时 9.7-12.5 s，旧机 2.3-2.4 s，期限 3600 s |
| 15 | `public_hints` 的 conda 措辞对 R2E 不成立（R03；E09） | 过时 | 当前公开包的 hints 已改为 `.venv` 措辞；devcheck 的 `activation_check` 通过（`DC/orig/activation_check.json`） |
| 16 | known_issues 的 `prompt_quality_candidates` 里本题条目：掩盖问题已修好，题面场景成了活的 F2P | 部分过时 | 掩盖问题已修好，这点确认。但本题应改登记为测试强度问题（T2b，S1）。题面本身没有问题：它的报错与 noop 失败原因逐字一致 |
| 17 | 修订提案选项 B 写的是 `from pandas.conftest import *` | 过时（以实际实施为准） | 实际实施只逐字摘出隐藏测试用到的两个 fixture，范围更窄；我核对后认为合理 |
| 18 | 修订版没有同版本的独立 runner，改用一次性容器试跑（R15） | 未核实 | dryrun 目录我没读；旧机、新机两条正式链的结果逐键一致，作为可复现证据已经够用 |

## 3. 我的前稿哪些改了、哪些没改

- **严重度**：前稿是"S1（T2b），conditional"，现在定为"S1 成立"。
  - C0 确实交付并执行了：由 agent 身份 `git_apply`，`RH2_SETUP_APPLY_RC=0`（`INV/logs_C0/…ba0f9574.eval.log:11`），git 状态显示 `groupby.py` 已修改（同一日志第 3 行），投影 `included_paths=["pandas/core/groupby/groupby.py"]`，4 个目标键 PASSED，共 237/237。
  - 违反公开要求这一点已由执行确认（`INV/pcheck_C0.json`）。
  - 掩码位置的底层值与前稿预测一致：astype 为 [1. 1. 3.]，reindex 为 [2.5 0.]，除法为 [1. 1. 3.]。
- **C1**：得 1.0，与预期一致。说明测试不限制修改放在哪里。不影响处置。
- **dtype（P3）**：判断不变，证据更强了。
  - agent 侧在 base 上实测，无 NA 的 `Float64` 基线返回 float64（`DC/orig/captures/variants_float_masked.out` 最后一行）。
  - gold 在 8 个变体上都返回 float64（`DC/private_control.json`）。
  - 结论仍是不交用户。
- **开发条件**：从"actor 待验"改为"新机实测"，devcheck 全部命令都符合预期（`DC/devcheck.log`）。numpy 版本从未知改为 1.20.3。
- **运行身份**：新机配方比旧机多了一层 `sysconfig_v1`（`r2e_derive_v1+material_v2+sysconfig_v1`，配方 sha256 `76710ab5…`，镜像 `85f550e6…`）。这一层的内容我没读；本题 noop / gold 的逐键结果与旧机相同。
- **用途**：
  - `capability_comparison` 仍是 conditional，但本题只剩一个条件：R-c 之前得 1 的补丁要做事后审计。另外，adapter 链路还没验，这是批次级条件。
  - `training_candidate` 定为 no（指当前版本）。
