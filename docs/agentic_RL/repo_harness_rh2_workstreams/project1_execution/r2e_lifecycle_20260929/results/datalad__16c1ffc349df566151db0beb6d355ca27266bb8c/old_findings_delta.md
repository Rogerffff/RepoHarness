# datalad `16c1ffc3`：旧结论核对与改判

- **时点。** 读历史之前的初判 `analysis_before_history.md` 已封存（协调者从写入调用原样保存），本文在那之后写成。
- **历史来源。** 均为 `refs.json` 所列；下文 `H:` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/`。
  - `H:tasks/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c/` 下的 `findings.md`、`screening_record.json`、`facts.json`；
  - `H:known_issues.json` 中的三族：`expected_non_passed_keys`、`hidden_test_relocation_artifacts`、`solver_condition:public_test_noise`；
  - `H:decisions.md` 的 E06、E10、E14；`H:results_20260924.md:22`；`H:repros/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c.py`；`H:packages/p2/README.md` 的 §2.5、§2.6。
- **新证据。** 下文 `N:` = `runs/r2e_lifecycle_20260929/`。
  - 缺省时限复验：`N:env_verify/ledger_l2_{noop,gold}.jsonl` 第 2 行；
  - 放宽时限复验：`N:budget_v5/ledger_{noop,gold}.jsonl` 第 1 行；
  - devcheck：`N:devcheck/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c/`；
  - 候选正式评分与行为对照：`N:inv/datalad_16c1/`。
    - 执行的四个补丁与我的附录 A 逐字节相同（sha256 一致）。
    - 行为对照以 root 身份在不联网的一次性容器里运行，只用来看行为，不是评分。
- **历史审查的范围。** 那一轮是环境资格审查（R01–R20），没有做题意—测试映射，也没有做退化探测。因此下面 §2 的 S1、T1 与历史不冲突，只是历史没有覆盖。

## 1. 旧主张逐条

| # | 旧主张（出处） | 判定 | 新的决定性证据 |
|---|---|---|---|
| 1 | gold 8/8、reward 1；noop 7/8，只差目标键 `test_result_filter`；与参考 runner 逐键一致（`findings.md:6`；R01、R02、R08、R15） | **确认** | 新机器、放宽时限：noop 0（7/8，不符键 `test_result_filter`）、gold 1（8/8）（`N:budget_v5/ledger_noop.jsonl`、`ledger_gold.jsonl` 第 1 行） |
| 2 | 5 个期望 FAILED 的键由隐藏 conftest 的 `path` fixture 与 nose 风格装饰器冲突造成；确定性、与环境无关；永远 FAILED，不区分解答（`findings.md:9`；R06；`known_issues` 两族） | **确认并加强** | 除 noop 和 gold 外，D、N、C1、C2 四个候选的正式评分里，这 5 键同样报 `TypeError: … multiple values for argument 'path'`（例：`N:inv/datalad_16c1/logs_C1/…eval.log:140-144`）。机制上，只改库代码的候选翻转不了它们：错误发生在 `datalad/tests/utils.py:429,564` 装饰器调用测试函数的那一刻。`expected_non_passed_keys` 族原说"'死键不会被合法修复翻转'多数仍是推断"；对本题，现在除了机制，还有两个合理替代解（C1、C2）的实跑支持 |
| 3 | 死键只让覆盖打折，"不影响评分正确性，不提修订"（`findings.md:14`）；"死键评分一致、不误伤正确解，但验证强度打折……交静态筛查决定修不修"（`hidden_test_relocation_artifacts` 族） | **部分推翻** | "不误伤正确解"成立；"不影响评分正确性"不成立：<br>• 失去的恰好是能拒绝 N 的回归覆盖：这 5 个测试本会调用 `ds.create()`，而 Create 的类级默认 filter 是 Constraint；<br>• N 在正式评分里得 1.0（`N:inv/datalad_16c1/ledger_N_budget1200.jsonl` 第 1 行）；<br>• 行为对照显示，N 让带关键字参数调用时的 Constraint filter 报 `TypeError: __call__() got an unexpected keyword argument 'dataset'`（`pcheck_filters_backcompat_N.json`；gold 打印 `BACKCOMPAT_OK`）。<br>静态筛查的决定：死键本身不必修（R-a 可选），改由 R-c 补上不依赖 git-annex 的针对性回归测试 |
| 4 | 环境无缺口；处置为 `environment_qualified`（`findings.md:3`、`screening_record.json` 的 disposition、`results_20260924.md:22`） | 环境部分**确认**；作为用途结论**过时** | devcheck 的检查项全为真（`N:devcheck/…/orig/attempt.json` 的 `checks`）；导入、原例复现、窄公开测试都与预期一致。但按统一标准 v1 §2，环境合格不等于具备能力比较或训练资格，而本题有未处理的 S1 |
| 5 | 资源与时限正常：setup 66 s、test 2 s；探针 `chown -R /testbed` 83.6 s（R12；`p2/README.md:141` 另记 60.8–111.9 s） | **过时** | 新机器上：<br>• 缺省 300 s 时限下，noop 和 gold 都在可信 setup 阶段超时（`grader_trusted_setup` 300.5 s，`infra_failure_detail=grading_control_surface_protect_timeout_after_300s`，见 `N:env_verify/ledger_l2_{noop,gold}.jsonl` 第 2 行），结果记为 failed_to_grade，而不是 0 分；<br>• 放宽后，可信 setup 在单跑时为 153 s（budget_v5），两路并发时为 210–222 s（inv）；<br>• 解题侧从容器启动到 sanitize/init 完成约 434 s（`attempt.json` 的 stages 从 +4.3 s 到 +438.7 s；没有逐项拆分，推断同样是 `chown` 开销）。<br>这些是本机的链路条件（E3），不是题目问题 |
| 6 | git-annex、gcc、make、git 都在；没有 pip；editable 安装（`findings.md:7`；R05） | **确认** | `N:devcheck/…/orig/captures/env_imports.out`：`/usr/bin/git-annex`、git 2.34.1、wrapt 1.16.0、nose 1.3.7、pytest 7.4.4；`env.out`：`No module named pip`，`datalad 0.5.1.dev1 /testbed/datalad/__init__.py` |
| 7 | 公开复现得到 `AssertionError: 'dataset' not found in {}`，"与题面逐字一致"（`findings.md:8`；R03、R16） | **确认**，附一处说明 | devcheck 的 `repro_issue_example.out`：以 agent 身份在 base 上 rc 1，报 `AssertionError: FILTER_KWARGS={}`，调用栈停在 `utils.py:1030`。说明：历史复现脚本里的断言消息是脚本自己写的（`H:repros/…py:30`），真正与题面逐字一致的证据是评分日志里 `assert_in` 给出的消息（`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-d_ff9ede96.eval.log:145`） |
| 8 | 相关公开测试 `test_utils.py` 为 3 passed / 5 errors（fixture 'path' not found）；失败的用例不覆盖本题修复，记为解题侧噪声（`findings.md:10`、E14、`public_test_noise` 族） | **确认** | 与我读历史前的静态推断一致（前稿 §1）。公开读者的窄命令避开了这 5 个用例：`N:devcheck/…/orig/captures/public_tests_narrow.out:200` 显示 18 passed |
| 9 | `install.sh` 是同仓通用的安装脚本，不含修复（R03、R17；followups A） | **未核实** | 我没有读 followups 日志。评分不执行它（`RH2_INSTALL_SKIPPED=1`），所以不影响结论 |
| 10 | agent 的 HOME 没有 git 身份（解题侧条件，`findings.md:16`） | **确认**；对本题无影响 | 本题的最小开发核对不需要提交；devcheck 的各条命令都按预期完成 |
| 11 | 解题不需要改 `r2e_tests` 之外的测试辅助文件（R04） | **确认**，并补一个反面 | 反面是一个通用的控制面风险：隐藏测试用的 `assert_in` 等来自 `datalad/tests/utils.py`，评分时不重置，候选可以改它（E3，交 A 线）。本次四个候选的 `candidate_test_like_paths` 都为空 |
| 12 | 派生镜像的 git 已清理：HEAD 没有子提交、refs 0、reflog 0、没有 remote（R17） | **确认** | devcheck 的 `sanitize_and_init`：HEAD `fddce1e…` 前后不变，`REFS_REMAINING=0`、`REMOTES=0`、`REFLOG_ENTRIES=0`；预检 `RH2_PREFLIGHT_GIT_HISTORY=ok`、`RH2_PREFLIGHT_HIDDEN_TESTS=ok` |
| 13 | 题面没写 `Test_Utils` 在哪里定义，但工作区里能找到（R03） | **确认** | 登记为 P4：公开材料能消解 |
| 14 | `path` fixture 冲突只出现在 16c1、9ba5 两题；隐藏 conftest 在 5 题里逐字相同（R20） | **未核实** | 与本题结论无关 |

## 2. 历史没有覆盖、本次新增的结论

- **S1（T2c，v1 §4 第 2 步）**〔静态〕：核心断言只用了题面示例的字面值。
- **S1（T2b，第 3 步）**：退化候选 D 正式评分 1.0（8/8）。
  - D 日志 `:119-122`、`:139-142` 有 4 条 `not reporting result ('dataset' not found in {} …)`。也就是说，`greatfilter` 的断言被吞掉，4 条结果被丢弃，而外层测试不检查结果。
  - 行为对照：在 D 下运行题面原例，打印 `RESULT []`；在 gold 下打印 `RESULT [0, 1, 2, 3]`。
- **S1（第 4 步）**：N 正式评分 1.0（8/8），但它让旧式 filter 失效，证据见上表第 3 条。
- **T1（由 P3 引出，误拒合理解）**：合理替代解 C2 正式评分 0.0（7/8）。
  - 不符键正是 `test_result_filter`，失败点正是 `sadfilter`：`'dataset' unexpectedly found in {'number': 4, 'dataset': None}`（C2 日志 `:129`、`:139-140`、`:148-153`）。
  - 调用栈经过 C2 自己的 `_result_filter`，说明评分时加载的确实是候选代码。
  - 行为对照：C2 在五种调用下都收到 `['dataset', 'number']`，而 gold 只在给了 dataset 的调用里收到。这正是上游后来 `get_allargs_as_kwargs` 的语义。
- **C1**（合理替代解，读法与 gold 相同）：正式评分 1.0（8/8）。日志里的行号随补丁后移（`generator_func:1047`，见 C1 日志 `:113`），说明候选确已加载。
- **X1**：
  - 同仓 `58ba5165`、`19f5b450` 的初态含本题修复的重构版；本题初态含 `9ba5de09` 的修复；
  - 两份机械扫描对本题都是结构性漏报：gold 扫描做逐字比对，而上游重构了代码；测试扫描只看新增的函数名，而本题只在已有函数里加断言。

## 3. 相对读历史前初判的改动

| 前稿位置 | 前稿 | 现在 | 理由 |
|---|---|---|---|
| §8 第 3、4 步 | D、N 预计得 1〔待跑〕 | 已证实：D 1.0，N 1.0 | `ledger_D_budget1200.jsonl`、`ledger_N_budget1200.jsonl` 第 1 行；执行的补丁与附录 A 逐字节相同 |
| §8 的 T1、§11 的 R-b | conditional，待 C2 实跑与复核 | **建议与 R-c 同批执行**，不单独执行 | C2 实跑为 0，失败点正是 `sadfilter`；C2 满足题面，也兼容旧式 filter（判断逻辑与 C1 相同，C1 得 1）；语义与上游后来的实现一致。是否属于 P5 仍待 Codex 复核：若认定为 P5，撤回 R-b 交用户决定，R-c 照做 |
| §11 R-b 的风险 | 推断：单独放宽会让"固定传 `dataset=None`"的候选过关 | 保留，并补一个可选验收候选 F（`card.md` 附录 B.4） | F 在现材料上判 0（被 `sadfilter` 挡住）；只上 R-b 时预计得 1；R-c 与 R-b 同上时预计得 0（缺 `number`） |
| §1、§6 | git-annex 未知；actor 侧依赖待验 | 已知 | devcheck 的 `env_imports.out` |
| §13 能力比较条件 | 含"devcheck 确认开发路径" | 这一条已满足；新增一条"本机评分时限需放宽" | devcheck 检查项全真；缺省 300 s 会超时 |
| §4(e) | 测试段耗时 1.0–3.0 s | 新机器测试段 4.1–5.0 s，另有可信 setup 153–222 s | 新账本的 `phases` |

前稿没有任何判定被推翻：严重度仍是 S1，第 3、4 步由"待跑"变成了执行证据。

## 4. 仍未核实

- gold 对拿不到签名的可调用对象（如 `bool`、`operator.itemgetter(...)`）会不会出错：只有静态推断，没有实跑。这是罕见路径，不影响处置。
- 解题侧约 434 s 启动开销由哪些步骤组成：没有逐项拆分。
- 真实模型求解（清单第 33–36 项）：没有跑。
- 修订草案 R-c、R-b：尚未实施。验收需要 6 次正式评分，外加 Codex 复核。
