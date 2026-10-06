# 旧主张核对（读历史后）：orange3__4014f2483e3bab0621c9ae0f994947c008183253

- 角色：R2E 私有主审，2026-09-25。初判 `analysis_before_history.md` 已在读历史前封存，本文不改它。
- 历史来源：`runs/r2e_static_prep_20260924/v3/history/orange3__4014f2483e3bab0621c9ae0f994947c008183253/refs.json` 列出的 8 份文件。
  - 本题的 `screening_record.json`、`findings.md`、`facts.json`（都在 `docs/.../r2e_env_repair_20260924/tasks/orange3__4014f248…/` 下）。
  - `known_issues.json`：只读了与 orange3 和本题有关的 8 个族。
  - `decisions.md`：扫了 E01–E24 与 T0 表，与本题相关的只有 E06、E09、E11、E12、E14。
  - `results_20260924.md`、`repros/orange3__4014f248….py`、`packages/p3/README.md`。
  - 历史记录里的二级引用原件没有打开：`dev_probe.json`、`agent_probe.log`、`reconcile.json`、`hygiene_check`、`memprobe`。
- 历史的性质：09-24 的**环境资格审查**。它明确不含题目质量和训练准入，也没有设计非 gold 候选。

## 1. 结论

- 历史在它自己的范围内基本成立：gold 与 noop 的评分、可复现性、权限、网络、git 清理，本轮都用原始日志、账本和 devcheck 重新核对过，结果一致。
- 本轮不推翻它的环境资格结论，但有四类改动：
  - **收窄两条**："环境无缺口"和 R08"候选代码生效"只对 `.py` 改动成立。
  - **替换一条**：公开测试证据。
  - **标记过时两条**：conda 措辞相关的两条。
  - **新增 6 个问题**：都是历史范围之外的。
- 主审初判不改。

## 2. 逐条核对

| # | 旧主张 | 出处 | 判定 | 新的决定性证据 |
| --- | --- | --- | --- | --- |
| 1 | 分类 `env_ok`，处置 `environment_qualified`，范围只是环境资格 | screening_record 的 `disposition`；results 表 | 确认（限其范围） | 下面各条的 gold、noop 与开发条件证据都复核一致。本轮的静态处置另外记录，不替代环境资格 |
| 2 | "环境无缺口"，`issues: []` | findings 结论；screening_record `issues` | **收窄（部分推翻）** | 对只改 `.py` 的修复成立。改 `Orange/preprocess/_discretize.pyx` 的修复不会生效，理由有三：① 导出脚本 `git add -N . && git diff --binary HEAD`（`rh2/src/repoharness2/grading/manager.py@cee933b4` 第 364–369 行；工作树里的未提交改动不涉及这几行）受 `.gitignore` 约束，第 2、7、20 行分别排除 `build`、`*.so`、`_discretize.c`；② 评分日志有 `RH2_INSTALL_SKIPPED=1`，账本 `install_skipped: true`；③ 所以评分时仍然使用镜像预编译的 `.so`。证据是代码配置加执行事实推断，C2 尚未实跑 |
| 3 | R08"候选代码生效"：导入 `/testbed/Orange/__init__.py`，gold 27/27 | R08 | **收窄** | 导入路径和 gold 结果确认（账本 `RH2_OBS_IMPORT_PATH`；gold 日志 27 passed）。但 gold 只改 `.py`，由此推不出编译扩展的改动也会生效，理由同第 2 条 |
| 4 | R01：派生镜像复核通过；隐藏测试树、入口、HEAD 与评分面一致 | R01 | 部分确认 | 隐藏测试树 `98a4a29e…`、入口 `5dee57d9…` 与 R-f 和复跑的日志头一致；devcheck 中 HEAD = base。21 项复核本身没有重读，属未核实 |
| 5 | R02：noop 为 0，只差 1 个键 | R02 | 确认 | noop 日志 26/27。目标键失败在 `discretize.py:53`，`low = high = 1.0000000000000004`，正是题面描述的断言 |
| 6 | R03：公开 prompt 1654 字、含代码块，题面示例可原样运行 | R03 | 确认 | `user_prompt.txt` 为 1654 字节；devcheck 的 `pr1_1` 以 agent 身份复现了示例 |
| 7 | R03 与 facts：public_hints 写的是 conda testbed，不适用于 R2E；known_issues `solver_hints:conda_wording_and_activation_prefix` 状态为 open | R03；`facts.source.public_hints_mention_conda` | **过时（对本题而言）** | v3 公开包的 `public_hints` 已换成 R2E 措辞：`.venv`、不联网、pip 可能没有、不改测试文件、用 `python -m pytest`。devcheck `activation_check` 实测前缀为 `/testbed/.venv`。这个族的全局状态不由本题决定 |
| 8 | R03：工作区可见 `run_tests.sh` 与 `install.sh`，两者都不含修复内容 | R03 | 部分确认 | 容器里两个文件都在（devcheck `env.out` 的 git status）。`install.sh` 的内容本轮没看（公开包没有导出它），属未核实 |
| 9 | R04：可信测试文件 3 个；gold 只触碰 `discretize.py`；解题不需要改 `r2e_tests` 以外的测试辅助文件 | R04 | 确认 | 日志 `RH2_SETUP_EXPECTED_TEST_FILES=3`、`RH2_SETUP_RESTORED=2`；gold 账本的 `included_paths` 只有 `Orange/preprocess/discretize.py` |
| 10 | R05：解释器是 `.venv` 3.7.9，pytest 7.4.4，pip 24.0，gcc、make、xvfb 在，uv 不在 | R05 | 确认，并有补充 | devcheck `env.out` 与之相同。另外测到 Cython 0.29.37 和 numpy 头文件；`python setup.py build_ext --inplace` 以 agent 身份 rc=0，但它只复制了已有的 `.so`，没有真正重编译 |
| 11 | R06：期望全 PASSED；`datasets` 是 install.sh 建的软链 | R06 | 前半确认，后半未核实 | `expected_output.json` 的 27 键全是 PASSED；软链没有检查 |
| 12 | R07：权限与 cgroup | R07 | 确认 | devcheck `prelaunch.json`：`WORKDIR_OWNER=54321`，激活文件不可写，内存 4 GiB，CPU 2 核，pids 512，`/tmp` 1 GiB |
| 13 | R09：公开测试选 `Orange/tests/test__orange.py`（1 例）并通过；复现 `REPRO_OBSERVED=1` | R09；`solver_conditions.public_tests` | 复现部分确认；**公开测试证据被替换** | devcheck 跑了直接对应的公开测试：`Orange/tests/test_discretize.py` 26 passed，这 26 例正好是隐藏测试的 26 个回归键；`Orange/preprocess/tests/test_discretize.py` 11 passed。两者都不需要 xvfb 前缀。P3 README §4 也承认原来的选择太弱 |
| 14 | 解题侧：纯库调用不需要 xvfb；`test_discretize.py` 可以带前缀运行 | findings 的建议；`solver_conditions.xvfb` | 确认，并扩展 | 不带前缀也能运行（devcheck `pr4_3`）；widget 测试带前缀可以运行，结果见第 3 节 I4 |
| 15 | R10：不需要网络 | R10 | 确认 | `prelaunch.json`：外部 DNS 与直连都是 DENIED；gold 在断网的 grader 里得 1 |
| 16 | R11：不依赖外部服务；sql 测试整体 skip | R11 | 前半确认，后半未核实 | 隐藏测试不含 sql 测试；sql 测试的 skip 情况本轮没有运行 |
| 17 | R12：峰值 2071 MB（占 51%）；E12 与 P3 §2.3：orange3 不设内存档位，峰值主体是 chown 产生的页缓存 | R12；E12；P3 §2.3 | 数值确认；成因采纳历史结论，本题未复验 | 账本 `mem_peak_mb`：gold 2070.6，noop 2153.2。本题没有单独做 memprobe |
| 18 | R13：同条件两次运行一致 | R13 | 确认 | 本轮把两轮的 noop 日志、gold 日志各自去掉时间和地址后逐行比对，完全相同 |
| 19 | R14：每次评分都用 fresh 容器，缓存计数前后相同 | R14 | 确认（限于账本） | 账本 `cleanup.removed=true`，`omitted_cache_count` 的 baseline 与 post 相同。并发没有检查 |
| 20 | R15：与独立 runner 逐键一致 | R15 | gold 侧确认，noop 侧未核实 | M3 的 a1、a2 都是 27 passed，键与状态和 RH2 gold 相同。noop 对账文件没有打开 |
| 21 | R16：目标键只有 1 个，对应题面 | R16 | 确认并细化 | 目标键分两段。第一段 4 个值、n=4，是题面原例，走 `n >= llen` 分支；第二段 10 个值、n=8，走循环分支，依据是题面的一般要求。两段都只断言唯一，不锁定点数或数值 |
| 22 | R17：git 已清理，`fix_present=no` | R17 | 确认 | devcheck 预检三项都是 ok；`git_sanitize` 显示 refs、remotes、reflog 都是 0；worktree 里 EqualFreq 没有修复 |
| 23 | R18：没有配方，没有修订 | R18 | 确认 | `revisions.json` 为 `[]`；run_refs 里 `env_recipe`、`resource_recipe` 都是 null |
| 24 | R19、R20：探针命令与适用范围 | R19、R20 | 未核实（属流程记录） | 不影响本题结论 |
| 25 | chown 203 s，rollout 初始化 1.5–4 分钟；`costs.probe_seconds` 224 s | R12 的 note；`solver_conditions.notes`；`costs` | 未核实 | 本轮没有独立计时。历史数值是在 4 个包并行、互相争 CPU 的条件下测得的 |

## 3. 历史未涉及、本轮新增的问题

| # | 问题 | 证据级别 | 与历史的关系 |
| --- | --- | --- | --- |
| I1 | 只改 `.pyx` 的根因修复在评分时不生效。本地工具链齐全，可以重编译，所以本地看起来已经修好 | 代码配置 + 日志；C2 待实跑 | 收窄第 2、3 条。历史只验了 gold（`.py`）。这是带编译扩展的 R2E 仓库共有的机制，本题根因正好在 `.pyx`，所以相关性高 |
| I2 | 目标键不检查点数和分辨率。先按容差合并切点再去重的写法预计能拿满分，但会让小量级数据的切分变粗 | 静态推断 + 算术转写；C3 待实跑 | 超出历史范围（历史不设计候选） |
| I3 | 同族暴露：本题 gold（连注释）和目标测试（方法体 sha256 `06cad36a…`）逐字出现在 22e98f8f、50f6a758、c3fb72ba、f5026689 的公开初态中；反过来，本题初态包含 9b5494e2 和 f237f968 的修复 | 已核实（公开包逐文件核对） | 历史 R17 只查本题容器，没查跨题 |
| I4 | 公开测试噪声：`Orange/widgets/data/tests/test_owdiscretize.py::TestOWDiscretize::test_minimum_size` 在 base 和 gold 下都失败（`1028 not less than 800`） | 实测（devcheck 的 agent 身份与私有 root 各一次） | 与 known_issues `upstream_test_artifacts:orange3_f237f968` 里同名测试的像素阈值问题同类（那边是 815 ≥ 800）。本题不在 `solver_condition:public_test_noise` 族的名单里，建议并入 |
| I5 | 题面 "below floating point precision" 的说法不准确：输入是互不相同的 double，塌缩发生在中点舍入 | 静态推断 + 日志 | 超出历史范围（历史的题意观察里没有本题） |
| I6 | 隐藏测试在导入时加载候选可以修改的测试辅助模块 `Orange/widgets/tests/utils.py`，评分时不重置 | 静态推断 | R2E 共有的评分控制面问题。历史 E18 的扫描针对的是"辅助模块被修复提交改过"，没有覆盖这一点。本题没有具体证据，按共享机制审查 |

## 4. 主审改判与理由

- **处置不改判。** 仍是 `needs_review`：静态候选待 actor 验证，I1 待 C2 实跑。历史里没有与本轮初判相矛盾的证据，历史的环境资格也不覆盖非 gold 候选。
- **细化一：资源。** 初判 §5(e) 把 2.1 GB 峰值说成"整个评分容器的峰值"。现在采纳 P3 的实测结论：主体是 `chown -R /testbed` 产生的可回收页缓存，测试本身的匿名内存约 0.2 GB（这是 P3 在同仓其它题上的测量，本题未复验）。结论不变：资源不构成问题。
- **细化二：分类口径。** E11 把"公开测试噪声"列为 `solver_condition`。本题的噪声只出现在调用方的 widget 测试里，直接对应的 `test_discretize.py` 没有噪声；P3 对同样有 widget 条件的 orange3 题也记为 `env_ok`。所以 `env_ok` 要不要改成 `solver_condition`，交协调者按全池口径决定；本记录只把 I4 写进解题侧条件。

## 5. 与历史的主要分歧（一句话）

历史的"环境无缺口"和"候选代码生效"只对 `.py` 改动成立；改 `Orange/preprocess/_discretize.pyx` 的正确修复在评分时不生效，唯一的下一步是用正式评分代码实跑 C2 确认。
