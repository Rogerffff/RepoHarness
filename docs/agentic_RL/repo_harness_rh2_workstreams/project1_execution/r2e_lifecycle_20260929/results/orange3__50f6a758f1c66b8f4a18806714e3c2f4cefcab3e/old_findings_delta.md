# orange3__50f6a758 旧结论核对（old_findings_delta）

- 角色：R2E 私有主审。2026-09-29 08:40 +08 起草，在读历史前封存稿 `analysis_before_history.md` 之后写；前稿不改。
- 路径缩写（相对仓库根）：
  - `HIST/` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/`
  - `LC/` = `runs/r2e_lifecycle_20260929/`
  - `INV/` = `LC/inv/orange3_50f6/`
  - `DC/` = `LC/devcheck_rev/unrev/orange3__50f6a758f1c66b8f4a18806714e3c2f4cefcab3e/`
  - `PRIV/`、`PUB/` 同前稿
- 读了哪些历史：`runs/r2e_static_prep_20260924/v3/history/orange3__50f6a758f1c66b8f4a18806714e3c2f4cefcab3e/refs.json` 列出的全部文件，即：
  - 本题 `HIST/tasks/orange3__50f6a758…/{screening_record.json, findings.md, facts.json}`；
  - `HIST/repros/orange3__50f6a758….py`；
  - `HIST/known_issues.json`（本题所在的 `prompt_quality_candidates` 族，另读了相关的 `resource:orange3_memory_headroom`、`setup_cost:chown_copy_up_large_workdir` 两族）；
  - `HIST/decisions.md`（E06、E09、E12–E14）；
  - `HIST/results_20260924.md` 中本题那一行；
  - `HIST/packages/p3/README.md` 的 §0、§1、§2.3–§2.5。
- 另查阅：处置状态取值见 `docs/.../project1_execution/environment_screening_definition_20260915.md` §4（记录模板指向的字段来源）。
- 没读：复核者的 `reviewer_initial.md`（协调者已转述要点）。
- **旧结论的范围**：09-24 的旧结论是**环境资格审查**（P3 包），它自己注明"不含题目质量 / 训练准入"。它记的 `issues: []` 只在这个范围内成立，不能当作题目质量结论。

## 1. 逐条核对

| # | 旧主张（出处） | 判定 | 新的决定性证据 |
| --- | --- | --- | --- |
| 1 | 分类 `env_ok`、处置 `environment_qualified`，"环境无缺口"（`findings.md:3`、`screening_record.json` disposition） | **旧机范围内确认；换到新机已过时** | 新机、缺省 300 s 时，noop 与 gold 都是 `failed_to_grade`：`infra_failure_detail = grading_control_surface_protect_timeout_after_300s`，`grader_trusted_setup` 300.7 s，没有进入测试段（`LC/env_verify/ledger_l1_{noop,gold}.jsonl:7`）。放宽到 1200 s 后，noop 为 0、gold 为 1（`LC/budget_v5/ledger_{noop,gold}.jsonl:8`）。这是本机的链路条件（chown copy-up 成本，`setup_cost` 族，A 线），不是题目缺陷 |
| 2 | noop 0（47/48，只差目标键）、gold 1（48/48）（R02、R08） | **确认** | 新机（镜像 `sha256:f5573c5a…`，配方 `r2e_derive_v1+sysconfig_v1`）：noop 47/48，mismatched 只有 `TestOWColor.test_load_ignore_warning`；gold 48/48（`LC/budget_v5/ledger_{noop,gold}.jsonl:8`） |
| 3 | 同条件重复一致（R13） | **确认** | 旧机 2 次、新机 1 次，结论相同。K1–K4 四次正式评分里，其余 47 键全部 PASSED（`INV/ledger_K*_budget1200.jsonl`） |
| 4 | 目标键只有 1 个，对应题面"加载含未使用变量的定义时应警告"（R16） | **目标键确认；"对应题面"这一判断不完整** | 旧审只核了主题，没核断言强度。新发现两点：<br>① 断言按字符逐一匹配名单格式，合理解 K1 判 0（T1）：`INV/logs_K1/evallog_replay-r2e-inv-50f6-K1-0_9e2e4112.eval.log:55-58` 在 `test_1.py:820` 报 `"'foo', 'bar', 'baz', 'qux' and 2 other" not found in "Definitions for variables 'foo', 'bar', 'baz', 'qux', 'quux' and 'corge', …"`。<br>② 只覆盖题面示例的形态（T2）：退化候选 K2、部分实现 K3、K4 都拿到 48/48（各 `ledger_K*_budget1200.jsonl` 与日志 `:82`） |
| 5 | `issues: []`（screening_record） | **过时（范围不同）** | 在题目质量范围内，新增 T1、T2（S1）、P4、P6、X1、T3，详见 `card.md` |
| 6 | 题面说的 TypeError，是测试去读一个从未被调用的 mock 的 `call_args` 时产生的（`prompt_quality_candidates` 族；`p3/README.md` §2.5） | **确认（记为 P4）** | noop 日志 `runs/r2e_env_repair_20260924/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_df1485a0.eval.log:54-57`。<br>devcheck 在 noop 下复现：例 1、例 2 的失败原因都是"没有任何警告"（`AssertionError: False is not true : []`），不是 TypeError（`DC/orig/captures/repro_unused_vars_warning.out:12, 30`）。<br>族状态仍是 open；R-f 可选（见 card） |
| 7 | 公开提示里"pre-activated conda env named testbed"对 R2E 不成立（R03、E09） | **过时（已修）** | v3 公开提示已改为 `.venv` 措辞（`PUB/public_bundle.json:15`）。devcheck 的激活核对：`ACT_PYTHON=/testbed/.venv/bin/python`、`VIRTUAL_ENV=/testbed/.venv`（`DC/orig/attempt.json`，activation_check） |
| 8 | 解题侧：python → `.venv` 3.7.9、pytest 7.4.4、pip 24.0；agent 可写 `/testbed`、HOME、`/tmp`（R05、R07） | **确认** | `DC/orig/captures/env.out:1-7`（uid 54321、pip 24.0、pytest 7.4.4、Orange 从 `/testbed` 导入）；`DC/orig/prelaunch.json`（HOME、/tmp 可写；2 CPU / 4 GiB；`DNS_EXTERNAL=DENIED`） |
| 9 | 公开测试 `Orange/tests/test__orange.py` 收集和运行都 rc=0；复现 `REPRO_OBSERVED=1`（R09） | **确认，但已有更相关的证据取代** | 旧探针跑的是与本题无关的测试文件。devcheck 跑的是相关的 `test_owcolor.py`：<br>- noop 下：除冲突用例外 46 passed / 3 skipped / 1 deselected（`captures/public_owcolor_tests_except_conflict.out:63`）；冲突用例通过（`public_no_rename_conflict.out:14`）。<br>- gold 下（私有对照）：同一批 46 个通过；冲突用例在 `test_owcolor.py:888` 失败，报 `Expected 'warning' to not have been called. Called 1 times.`（`DC/private_control.json`）。这就是 P6 |
| 10 | widget 测试与复现必须带 `QT_QPA_PLATFORM=minimal … xvfb-run` 前缀（solver_conditions.xvfb） | **按声明确认；不带前缀会怎样，未核实** | devcheck 的命令都带前缀，全部成功。不带前缀的对照没有跑 |
| 11 | 解题不需要网络（R10） | **确认** | `prelaunch.json` 显示外网 DNS 被拒；devcheck 全部命令在无网络下完成 |
| 12 | 内存峰值 58%，推断成因同 c3fb72ba / f5026689（页缓存）（R12） | **确认不构成问题** | 族结论已验证为 `not_an_issue`（E12）。新机 `mem_peak_mb` 为 2231 / 2230，同一量级（budget_v5 ledger 的 `resource` 字段） |
| 13 | `chown -R /testbed` 用时 212.52 s；可信 setup 160 s（costs、R12） | **过时（新机更慢）** | 新机可信 setup：noop / gold 分别 279 / 281 s；K1、K4 为 329 s，K2、K3 两题并行时为 497 s（`INV/ledger_K*`）。devcheck 容器初始化约 198 s（`DC/orig/attempt.json`，从 `container_started` 到 `sanitize_and_init`）。超过缺省 300 s 控制面保护，所以本机评分必须放宽到 1200 s |
| 14 | HEAD 无子提交，无 remote、reflog（R17） | **确认** | devcheck：`RH2_PREFLIGHT_GIT_HISTORY=ok`；git_sanitize 的 `REFS_REMAINING=0`、`REMOTES=0`、`REFLOG_ENTRIES=0`（`DC/orig/attempt.json`） |
| 15 | 未跟踪的 `datasets` 是 install.sh 建的软链，指向 `Orange/tests/datasets/`（R06） | **未核实** | 本轮没看；与修复无关，隐藏测试用的 iris / heart_disease / zoo 在跟踪目录 `Orange/datasets/` 下 |
| 16 | gold 只触碰 `owcolor.py`；评分面文件 = `r2e_tests/{__init__.py, test_1.py}` + `run_tests.sh`（R04） | **确认** | gold 与 K1–K4 的 `projection.included_paths` 都只有 `Orange/widgets/data/owcolor.py`；日志 `RH2_SETUP_TEST_FILES=3` |
| 17 | 与独立 runner 逐键一致（R15） | **确认（沿用旧证据）** | 本轮没有重跑独立 runner；新机 noop / gold 的逐键结果与旧机相同 |
| 18 | 解题侧条件只适用于本题镜像（R20） | **确认；镜像身份已变** | 新机派生镜像的配方身份是 `r2e_derive_v1+sysconfig_v1`，image `sha256:f5573c5a…`，旧机是 `r2e_derive_v1` / `sha256:9fa2177f…`。本轮新证据都在新镜像上 |

## 2. 我自己初判的改动

读历史前的前稿见 `analysis_before_history.md`，保持原样不改。

1. **处置：`needs_review` → `needs_repair`**。按定义文档 §4，`needs_repair` 指"已有可复现的材料缺陷，并已记录修复方案"；`needs_review` 指语义分歧或关键证据不足。现在缺陷已由正式评分坐实（K1 为 0，K2、K3、K4 为 1），修订草案也写成了可执行的形式（`card.md` 附录 A），所以改判。
2. **S1 的依据**：前稿是"第 2 步静态命中，第 3 步待跑"，现在改为"第 3 步 K2 实跑得 1，命中 T2b（有执行证据）；第 4 步 K3、K4 实跑得 1"。第 2 步严格版的争议不再影响 S1 结论。
3. **错误候选清单**：补上复核者提出的 C-deg（拼好消息后直接弹框并 `return`，跳过已匹配定义的赋值与提交），作为修订验收时必须判 0 的已知错误候选。
   - 按源码推断，它现在能得 1：唯一带未用变量的隐藏测试不检查赋值结果。
   - 我在 R-c 里加的"已用定义照常生效"断言能拦住它：私有探针 b 用的是同一组输入，C-deg 在其中应当失败。
   - 正式评分与探针结果尚未回来，列为待验证。
4. **其余预测全部被实跑证实，未作修改**：
   - K1 恰好在 n=6 那一轮、`test_1.py:820` 失败；
   - K2、K3、K4 都是 48/48；
   - 私有探针矩阵与前稿 §8.3 逐格一致（`INV/pcheck_probe_{none,gold,K1,K2,K3,K4}.json`）；
   - devcheck 的 noop 复现报"无警告"而非 TypeError；
   - gold 下公开冲突用例在第 888 行失败。

## 3. 协调者关心的两点

- **K4 的补丁摘要不同**：协调者生成的 K4（`71c27fda…`）与我本地的（`2aa27974…`）只差 `index` 行和 hunk 头里的函数名上下文（因为它从 gold.patch 派生），增删行完全相同，我已逐行 diff 确认。**就是我要的 K4**；日志 `:1` 也显示 `owcolor.py` 被修改、`RH2_SETUP_APPLY_RC=0`。
- **devcheck 私有对照中 `public_no_rename_conflict` 在 gold 下退出 1**：失败位置是 `Orange/widgets/data/tests/test_owcolor.py:888`，报 `AssertionError: Expected 'warning' to not have been called. Called 1 times.`，**正是 P6 的那条旧断言**（输入含未用变量 `"var not"`）。gold 按新需求对它发出警告，所以失败；这不是回归。
