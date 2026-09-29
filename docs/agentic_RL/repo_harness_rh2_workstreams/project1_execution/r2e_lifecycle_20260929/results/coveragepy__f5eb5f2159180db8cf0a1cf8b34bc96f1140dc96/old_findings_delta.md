# coveragepy__f5eb5f21：旧结论对照（读历史之后）

- 顺序：`analysis_before_history.md` 在读任何历史之前写成并封存；本文之后才读了 `runs/r2e_static_prep_20260924/v3/history/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/refs.json` 列出的 8 份文件，以及协调者第二步给出的新机器实跑。
- 历史的性质：旧材料全部来自 09-23/24 的**环境审查**（`r2e_env_repair_20260924`），范围是"当前材料（expected_v0）+ `r2e_derive_v1` + 默认 rollout profile"下的环境资格，不做题意和测试强度审查。它的 `findings.md:11` 自己写明："期望只有 4 键，判分面较窄（题目质量问题，不属本轮）"。
- 路径约定：
  - `PUB/` = `runs/r2e_static_prep_20260924/v3/public/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/`
  - `PRIV/` = `runs/r2e_static_prep_20260924/v3/private/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/`
  - `HIST/` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/`
  - `NEW/` = `runs/r2e_lifecycle_20260929/`
  - `INV/` = `NEW/inv/coveragepy_f5eb/`
  - `DC/` = `NEW/devcheck/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/`

## 1. 逐条对照

判定取值：确认 / 推翻 / 过时 / 未核实。

| # | 旧主张（出处） | 判定 | 新的决定性证据 |
| --- | --- | --- | --- |
| O1 | 环境无缺口，分类 `env_ok`，处置 `environment_qualified`（`HIST/tasks/…/findings.md:3`；`screening_record.json` 的 classification / disposition） | **确认（环境层）**；适用范围需要更新 | 新机器镜像 `rh2-r2e-derived/coveragepy:f5eb5f215918-r2e_derive_v1s`（配方 `r2e_derive_v1+sysconfig_v1`，ID `98b19b5a2ce4…`）：noop 0（3/4，只差目标键），gold 1（4/4）（`NEW/env_verify/ledger_l1_noop.jsonl:2`、`ledger_l1_gold.jsonl:2`）；devcheck 13 项检查全部为真（`DC/devcheck.log`）。注意：`environment_qualified` 只是环境资格，不等于训练资格 |
| O2 | `issues: []`（旧 `screening_record.json`） | **过时**（审查范围不同） | 旧审只查环境。本轮在题意 / 测试层发现 S1：D0、C2、C3 正式评分都是 1.0（`INV/ledger_D0.jsonl`、`ledger_C2.jsonl`、`ledger_C3.jsonl`）；另有 C1 规格争议（`INV/ledger_C1.jsonl`，0.0） |
| O3 | "期望只有 4 键，判分面较窄（题目质量问题，不属本轮）"（`findings.md:11`） | **确认，并升级为 S1** | 唯一的分支断言只用题面示例值 1/1（T2c）；硬编码 1/1 的 D0 得 1（T2b）；错误口径的 C2 和按配置门控的 C3 都得 1（v1 第 4 步） |
| O4 | R-f 中 noop 为 0 且只差目标键、gold 为 1；与 M3 和 09-09 共 5 份参考对账一致（`findings.md:6`；R02 / R08 / R15） | **确认**；其中"5 份参考"的对账汇总**未核实** | 本审读过 RH2 的 4 条账本行和 6 份日志（sha256 与 `run_refs.json` 一致），以及 M3 两次 gold 4/4 的日志。`runs/r2e_rf_20260923/reconcile_all/reconcile.json` 属于 runs/ 下的汇总文件，没有打开 |
| O5 | 公开复现 `REPRO_OBSERVED=1`（`findings.md:8`；R03 / R09；`HIST/repros/…py`） | **确认** | devcheck `repro_api_totals` 退出码 1，输出 "BUG PRESENT"，totals 只有 7 个键（`DC/orig/captures/repro_api_totals.out`）；`repro_cli_json` 同样缺这两个键 |
| O6 | 解题侧：python 3.7.9、pytest 4.6.6 + xdist、pip 20.0.2 且 `pip check` 无问题；coverage 以 editable 方式安装，所以不要求 cwd（R05；`solver_conditions`） | **确认**；`pip check` **未核实** | `DC/orig/captures/env.out`、`env_versions.out`、`pytest_version.out`（插件：xdist 1.30.0、flaky 3.6.1、hypothesis 4.41.2、pytest-forked 1.6.0；CTracer 可用）。P-1：agent 身份在 cwd=/ 下导入的是 `/testbed/coverage/__init__.py` 5.0.5a0，`/testbed` 之外没有另装一份（`INV/pcheck_P1_agent_cwd_root.json`） |
| O7 | 公开测试 `tests/test_annotate.py` 收集 4 个、rc 0（R09；`solver_conditions.public_tests`） | **过时**（与本题无关） | 本题相关的公开测试是 `tests/test_json.py`：base 上 4 passed（`DC/orig/captures/public_test_json.out`），gold 下 `test_branch_coverage` 失败，这就是 P6（`DC/private_control.json` 中 `public_test_json.rc=1`）；另外 `tests/test_results.py` 35 passed |
| O8 | 脏树只有 `?? install.sh`、`?? run_tests.sh`，没有修复痕迹；HEAD 没有子提交，refs / reflog / remote 都为空（`findings.md:9`；R17） | **确认** | `DC/orig/captures/env.out`；`r2e_preflight.out` 为 `GIT_HISTORY=ok`；`DC/orig/prelaunch.json` 中 `GIT_REMOTES`、`GIT_REFLOG`、`GIT_REFS` 都是 0，`GIT_HEAD=17204597…` |
| O9 | 隔离：agent 读不到 `/rh2_private`，`r2e_tests` 不在根目录也不在工作区（R07） | **确认** | `r2e_preflight.out` 为 `HIDDEN_TESTS=ok`；`prelaunch.json` 中 `HIDDEN_0=DENIED:/root` |
| O10 | agent 可写 `/testbed`、site-packages、home、`/tmp`（R07） | **确认**；另补一条共享问题 | `prelaunch.json` 中 `WORKDIR_WRITABLE=1`、`WORKDIR_OWNER=54321`。`DC/orig/post_run_facts_root.txt` 显示 agent 跑 pytest 时在 `/testbed/.venv/…/site-packages/_pytest/__pycache__` 写了文件，说明 `.venv` 对 agent 可写。这些改动会不会随候选带进 grader，属于共享机制问题（清单 #31），不在本题范围内逐题核对，交 A 线 |
| O11 | 无出网（R10） | **确认** | `prelaunch.json`：`DNS_EXTERNAL=DENIED`，`NET_forbidden_0..3=DENIED`，只有模型中继是 `CONNECTED`；grader 的网络策略是 `deny_all` |
| O12 | 资源：内存峰值 272 MB，setup 16 秒，测试 2 秒（R12） | 内存**确认**；耗时**过时** | 新机器上内存峰值约 272.7 MB；`grader_trusted_setup` 约 68 秒，测试阶段约 7 秒（`ledger_l1_*`）。新机器更慢，但不影响结论 |
| O13 | R13：同条件下 noop 与 gold 各跑 2 次，结果一致 | **确认并扩展** | 新镜像上 noop、gold 各 1 次，结果一致；4 个候选的评分都完整（4 键全部解析、测试段完整、`stage_error=null`） |
| O14 | R14：镜像基线里有 33 个 `__pycache__` 文件，被 census 剪除，前后不变 | **确认** | 新镜像上 env_verify 与候选账本的 `omitted_cache_count`，baseline 和 post 都是"1 个目录、33 个文件" |
| O15 | R04：gold 只改 `coverage/jsonreport.py`；解题不需要改 `r2e_tests` 以外的测试辅助文件 | **确认** | gold 以及 D0、C1、C2、C3 的 `projection.included_paths` 都是 `["coverage/jsonreport.py"]`，`candidate_test_like_paths` 都为空 |
| O16 | R06 / R11：期望的 4 个键全是 PASSED，没有非 PASSED 键 | **确认** | `PRIV/expected_output.json` |
| O17 | R16：目标键 `test_branch_coverage` 与题面对应 | **确认并细化** | 题面里的错误信息，就是隐藏测试在 noop 上失败时输出的 "Differing items" 行（R-f noop 日志第 93 行）。所以测试只用题面示例值这一点是由出题方式决定的，必然成立 |
| O18 | R03 注："conda 措辞是全局问题（E09）"；`known_issues` 的 `solver_hints` 族状态为 open | **过时** | v3 材料已经换成 R2E 措辞（`PUB/public_bundle.json:15`）；`DC/orig/activation_check.json` 显示 `ACT_EXPECTED_PREFIX=/testbed/.venv`、`VIRTUAL_ENV=/testbed/.venv`，`ok=true` |
| O19 | R18 / R20：没有配方，也没有材料修订 | **部分过时** | 仍然没有材料修订（v3–v5 对本题逐字相同）；但新机器的环境配方是 `r2e_derive_v1+sysconfig_v1`，属于环境层改动，不是题目修订 |
| O20 | `known_issues` 的 `no_pip_in_venv` 族把本题列为有 pip 的题 | **确认** | `env.out`：pip 20.0.2 |
| O21 | 建议："无额外解题侧条件"（`findings.md:13`） | **基本确认，补两条** | ① P6：任何正确修复都会让公开 `test_branch_coverage` 失败（private_control 中 rc=1），不能把这当作环境故障或模型改错；② `public_hints` 是否真的送到了模型面前还没验证（环境卡 §2） |
| O22 | P1 包 README 把本题记为 `env_ok`、"unknown（只差 R13）" | **过时** | 之后已记为 `environment_qualified`（`HIST/results_20260924.md:21`），现在又有了新镜像证据 |

没有任何历史主张推翻本审的初判。历史里也没有涉及题意与测试强度的结论，因此不存在旧结论与本审 S1 判定冲突的地方。

## 2. 主审相对初判的修改与补充

1. **严重度的证据级别升级。** 初判是"第 2 步静态成立，第 3、4 步待实跑"。现在由正式评分确认：D0 1.0（`INV/ledger_D0.jsonl`，4/4，`included_paths=["coverage/jsonreport.py"]`），C2 1.0，C3 1.0。**S1 定稿。**
2. **C1 = 0.0 属实，而且只因为每文件多了两个键。** `INV/logs_C1/…eval.log` 第 91–94 行显示 "Omitting 2 identical items"，也就是 `meta` 和 `totals` 都与期望相同，差异只在 `files['a.py']['summary']` 多出的 `covered_branches` / `missing_branches`。争议的范围由此确定：`totals` 的要求没有分歧，只有"每文件 summary 能不能额外加键"这一点有分歧。
3. **R-c 的期望值从静态推导变为实测核对。**
   - P-3 在 gold 下：JSON 为 6/0/4/2；XML 为 `branches-valid="6" branches-covered="4" lines-valid="16" lines-covered="13"`；另起报告对象时仍是 4/2（`INV/pcheck_P3_gold.json`）。与附录 B 的推导逐项一致。
   - 同一个夹具上：D0 报 1/1，C2 报 6/0，C3 在进程内是 4/2，但另起报告对象时两个键缺失（`pcheck_P3_{D0,C2,C3}.json`）；P-2 显示公开命令 `repro_cli_json` 在 C3 下缺键，在 gold 下为 1/1。
   - 因此 R-c 草案改用显式的 `data_file`，与已经核过的 P-3 流程保持一致。
4. **`checks` 状态更新。** #6、#8、#10、#29 由 unknown 改为 pass（依据 devcheck、P-1）。#3 仍是 unknown：模型实际收到的消息没有验证。
5. **能力比较的条件收窄。** "devcheck"和"新镜像上的 noop / gold"两项已经满足。剩下的条件：C1 争议由用户裁定（按 v1 §11 口径，题意争议或误拒尚未消解的题只作问题定位）；以及在 R-c 验收之前，如果先纳入比较，得 1 的补丁必须按预先登记的规则做事后审计。
6. **当前环境身份更新。** 当前环境是新配方 `+sysconfig_v1` 的镜像；旧 `r2e_derive_v1` 镜像（`1a2107883a20…`）上的结果只作对照。两边的逐键结果相同。
7. **共享问题记录，不作为本题问题。** `.venv` 对 agent 可写（O10）。这属于清单 #31 的共享控制面问题，本题标 not_checked，交 A 线。
