# coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266：旧主张对照（读历史后）

2026-09-25 · 私有主审。`analysis_before_history.md` 已先行保存，本文不改它。

## 读取范围

- `history/.../refs.json` 列出的 8 份文件全文：
  - 旧逐题记录 `screening_record.json`、`findings.md`、`facts.json`；
  - `known_issues.json`、`decisions.md`、`results_20260924.md`；
  - 复现脚本；P1 包 README。
- 为核对旧主张，另读了两处：
  - 旧记录引用的原始探针输出：`runs/r2e_env_repair_20260924/p1/dev_probe/coveragepy__97997d2c…/` 下的 `agent_probe.log`、`dev_probe.json`、`container.json`、`root_init.log`；
  - 仓库脚本 `rh2/scripts/r2e_env/dev_probe_agent.sh` 第 84–87 行（公开测试命令）。
- 没有打开：`runs/r2e_rf_20260923/reconcile_all/reconcile.json`、`runs/r2e_t0_batch2_20260924/{scan,provenance}/` 等汇总文件。依赖它们的旧主张记为"未核实"。

## 1. 总体判断

旧调查是环境资格审查，范围是"expected_v0 + `r2e_derive_v1` + 默认 rollout profile"，结论为 `env_ok` / `environment_qualified`，`issues` 为空。本轮是题意与评分质量的静态审查，两者范围不同。

- **环境结论**：基本全部确认，当前材料仍是 expected_v0（无修订）。
- **本轮新增两项问题**：测试覆盖不足（清单 25）；同族关系与跨题暴露（清单 5）。旧调查没有覆盖这两个维度，不构成推翻。
- **过时的旧表述**：R13 缺口、conda 措辞、处置 `reason` 文本。
- **对初判的影响**：历史让我初判里的两项未知缩小，处置不变。

## 2. 逐条对照

| # | 旧主张（出处） | 判定 | 新的决定性证据 |
|---|---|---|---|
| H1 | 分类 `env_ok`（findings；record.classification；results 第 19 行） | 确认（环境维度） | devcheck 正式启动链上：`python` = `/testbed/.venv` 3.7.9；`cd /` 后仍导入 `/testbed/coverage`；pip 20.0.2；无出网。没有题级解题条件。`env_ok` 不等于题目质量合格 |
| H2 | 处置 `unknown`，"只差 R13"（findings；P1 README §1；record.disposition.reason） | 过时 | `review_notes` 已改为 `environment_qualified`。我逐行比对了 R-f 与 `_rerun2` 的 noop、gold 日志，只有 xdist 顺序和耗时不同。record 的 `reason` 文本没随状态更新 |
| H3 | R-f noop 0（只错目标键，`No such option: 'paths'`），gold 1（44/44）（findings；R02、R16） | 确认 | R-f noop log 第 61 行与第 135–136 行；gold log 第 92 行 |
| H4 | 对账 agree（R15；facts.reference） | gold 侧确认；noop 侧未核实 | M3 两份 gold `test_output.txt` 各 44 passed，与 RH2 相同。M3 本题目录下只有 `gold/`，noop 参考日志的位置我没查；`reconcile.json` 未打开 |
| H5 | 探针十项；python 3.7.9；pytest 4.6.6 + xdist；pip 20.0.2 且 pip check 通过；在 `/tmp` 下能导入（R05；solver_conditions） | 确认 | 原始 `agent_probe.log`（镜像 `ab9a4d0f`，agent 54321）。devcheck `env.out` 在正式链上复现了同样的事实 |
| H6 | 公开测试 `tests/test_annotate.py` 收集 4 个、rc 0（R09；solver_conditions.public_tests） | 确认，但与本题相关性弱；同时补强了我的判断 | 该文件是探针按字母序挑的，与本题无关（P1 README §7.2）。探针命令是 `python -m pytest -q -o cache_dir=/tmp/rh2_pytest_cache --maxfail=5 -x`（`dev_probe_agent.sh:86`），没覆盖 `setup.cfg` 的 addopts。输出里有 "bringing up nodes..."，说明 `-n3`、`--failed-first` 等默认 addopts 在 agent 身份下可用 |
| H7 | 公开复现 `REPRO_OBSERVED=1`（R03、R09） | 确认 | `agent_probe.log` 的 `REPRO_OUTPUT`；devcheck pr1_1。附注：脚本的"修复后"分支也只检查往返，同样会放过 W1。它只用来展示 base 行为，不算缺陷 |
| H8 | R03："题面带可运行示例……conda 措辞为全局问题（E09）" | 复现部分确认；conda 部分过时；"实际输入"部分未核实 | v3 的 `public_hints` 已改为 `.venv` 措辞。devcheck `activation_check` 报 `ACT_EXPECTED_PREFIX=/testbed/.venv`，结果 ok。模型实际收到的消息仍没捕获：devcheck 的首条 user 消息是核对指令。所以我把清单 3 记为 unknown；旧 R03 的 pass 依据的是渲染文件 `prompts.jsonl`，不是捕获到的消息 |
| H9 | `facts.source.public_hints_mention_conda=true`；known_issues 的 `solver_hints:conda_wording…` 与 `no_pip_in_venv` 中"提示写 `pip` already points at it"；decisions E09"正式链启动前核对会拒绝 R2E" | 对当前 v3 材料过时 | v3 提示写的是 "`pip` may be unavailable"。devcheck 的预检与激活核对都通过（环境卡 §2：R2E 接线已实施，待 A 线审查） |
| H10 | 脏树只有未跟踪的 `install.sh`、`run_tests.sh`，没有修复痕迹（findings；R17） | 确认 | `worktree_manifest.json` 的 `initial_diff` 为 0 字节。devcheck `attempt.json` 的 git 清理：refs、remotes、reflog 都是 0，不可达对象 0；预检 `GIT_HISTORY=ok`。system 里的 gitStatus 只列到 base |
| H11 | R17：容器内无泄漏 | 确认，但范围有限 | 在题目层面，本题修复和加强版目标测试出现在 `ea6906b0` 的公开工作树里（`coverage/config.py:428,459`、`tests/test_config.py:339–361`、`doc/changes.rst:75–88`）。这是新增 issue（清单 5），不推翻容器内的结论 |
| H12 | R04：`test_files` 与 gold 的边界；来源镜像的既有脏改动不会卷进候选补丁（代码阅读，未经真实 rollout 验证） | 前半确认；后半在重放层面确认，真实 rollout 仍未核实 | eval log 中 `RH2_SETUP_EXPECTED_TEST_FILES=3`；gold 投影 `included_paths=["coverage/config.py"]`，两个未跟踪文件没有带入。补充一点旧 R04 没提的：隐藏测试导入候选可改的 `tests/coveragetest.py`，评分时 pytest 读 `setup.cfg`（共享控制面，清单 31） |
| H13 | R06、R11 为 not_applicable（期望全 PASSED、无资产） | 确认 | `expected_output.json` 44 个键全是 PASSED |
| H14 | R07 权限 | 探针结论确认；正式链上部分确认 | devcheck prelaunch：`WORKDIR_WRITABLE=1`，HOME 与 TMP 可写，`HIDDEN_0=DENIED`。site-packages 可写只在旧探针里见过（`WRITE_SITE=ok`），正式链没测，与本题无关 |
| H15 | R08 候选代码生效 | 确认 | 账本 `RH2_OBS_IMPORT_PATH=/testbed/coverage/__init__.py`；gold 44/44 |
| H16 | R10 无出网 | 确认 | 旧探针 `NET_CONNECT_RC=1`、`NET_DNS_RC=2`；devcheck `DNS_EXTERNAL=DENIED`、`NET_forbidden_*=DENIED`。旧 solver_conditions 里"`--network none` 保留回环"说的是探针条件；正式链是隔离网络加 relay |
| H17 | R12 资源（峰值约 273 MB） | 确认 | 4 行账本的峰值在 272–282 MB |
| H18 | R13 两次一致 | 确认 | 逐行 diff 日志 |
| H19 | R14：每次 fresh 容器；`__pycache__` 基线 33 个文件 | 确认 | 账本 `omitted_cache_count` 基线与后置都是 1 个目录、33 个文件。并发没测（我记清单 15 为 not_checked） |
| H20 | R16：目标键 ↔ 题面 | 确认，但结论不完整 | 目标键就是题面示例，但只经 `Coverage` 对象、从空起点做一次往返。它不覆盖：插件拿到的 `CoverageConfig`（R5）、`combine()` 是否生效（R6）、替换语义（R4）、配置文件读入的值能否取回（R7）。新增 issue（清单 25） |
| H21 | R18、R20：无配方、无修订、不涉及共享修复 | 确认 | `revisions.json` 为 `[]`；grading bundle 的 `material_revisions` 为 `[]` |
| H22 | `issues: []` | 范围不同，不构成推翻 | 本轮新增 ISS-1、ISS-2，见 card |
| H23 | E18 与 `hidden_test_relocation_artifacts`：扫描没标出本题 | 确认 | 上游提交只改了 `config.py` 与 `tests/test_config.py`（M3 `gold_meta`），隐藏测试依赖的 `tests/coveragetest.py` 不是被修复提交改过的辅助。`tests/conftest.py` 对 `r2e_tests/` 不生效，但 6 次运行都没受影响 |
| H24 | `support_stale_helper:coveragepy_5dbbe143`（另一题） | 不是本题主张，但为本题的题目关系提供了证据 | 本题工作树 `tests/coveragetest.py:264` 已经是 `capture_warning(msg, slug=None, once=False)`，正是 5dbbe143 上游提交改过的版本。这支持"本题初态含 5dbbe143 的修复"；我初判记为"线索，未核实"，现升级为"测试辅助部分已核实" |
| H25 | `expected_provenance_mixed`："41 题三者一致"（没点名本题） | 未核实 | 没读 provenance 输出。本题 expected 全是 PASSED，与来源镜像（M3）和派生镜像的 gold 结果一致，已足以支撑评分确定性 |
| H26 | `costs.probe_seconds=32.18` | 确认 | `dev_probe.json` 的 `timings.total_seconds` 为 32.18 |
| H27 | `order_note`（E06：先写复现脚本，再读隐藏材料） | 未核实 | 这是流程声明，无法从产物复核 |

## 3. 我的初判在读历史后的变化

- **不变**：处置（静态候选，待 actor 验证）、两项 issue、W1/W2/A1 的预期得分。
- **缩小的未知**：
  1. 默认 addopts 的原命令形式在 agent 身份下能否使用：由 H6 升级为"镜像层面已实测"（旧探针，同一派生镜像 `ab9a4d0f`，另一个公开文件）。devcheck 里 pr5_* 的 rc=4 仍是核对命令加了 `-p no:cacheprovider` 造成的伪影；本题的 `tests/test_config.py` 用原命令形式在正式链上仍没跑过。
  2. 与 5dbbe143 的包含关系：由 H24 升级为"测试辅助部分已核实"。
- **新增的负对照 N1**：把 `('paths', 'paths')` 加进 `CONFIG_FILE_OPTIONS`。这是本步补充的校准候选，不是读历史引出的，用来确认回归键会拒绝破坏配置读取的做法。候选 M（合并语义）降为可选。
- **与历史的主要分歧**：旧环境记录 `issues` 为空、R16 为 pass、R03 为 pass。我认为：
  - 目标测试覆盖不足，W1、W2 静态推断得 1；
  - 存在同族与跨题暴露；
  - "实际输入"仍是 unknown。
  这些分歧来自审查范围不同，不是对同一事实判断相反。
- **建议下次汇总时更正的旧表述**：旧记录 `reason` 的"只差 R13"；facts 与 known_issues 里针对旧提示的 conda / pip 措辞。
