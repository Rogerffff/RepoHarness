# datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb：旧主张核对（读历史后）

2026-09-25 · 私有主审（静态）。`analysis_before_history.md` 已先行保存，本文在其后写成。

**本次读取范围**
- 历史引用：按 `runs/r2e_static_prep_20260924/v3/history/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb/refs.json` 读了其中列出的全部文件：
  - 本题 `screening_record.json`、`findings.md`、`facts.json`；
  - `known_issues.json` 中与本题相关的两个族；
  - `decisions.md`、`results_20260924.md`、复现脚本、`packages/p2/README.md`。
- 为核对旧主张而打开的原始证据：
  - `runs/r2e_env_repair_20260924/p2/` 下的 `dev_probe/…19f5…/agent_probe.log` 与 `root_init.log`、`pubtests.sh`、`pubtests/…19f5….log`、`followups/followups.log`（A、C、D 段）；
  - `runs/env_overnight_20260916/M3/facts/19f5b45096ca/` 下的 `pkgsrc.txt`、`leak_path/children.txt`、`git_scrub/{git_before,git_after,out_after}.txt`。
- 新补的私有 gold 对照：`runs/r2e_actor_20260925/devcheck/datalad__19f5b45096cadaa4677c9b15f18a6d3/private_gold_full/private_control_full.json`（sha256 `9d36f755…`）。条件：镜像 `sha256:851a10b6…`，root，`network=none`，每条命令保存完整 stdout / stderr，`truncated=false`。
- 仍然没读：首批审查目录、Codex 复核目录、本批 README 与 `assignments.json`、其它题的私有包。

判定词：**确认**、**推翻**、**过时**（当时成立、现在已变）、**未核实**、**补充**（旧主张本身不错，但范围外还有问题）。下文 `hist/` 指 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/`，`DEV/` 指上面的 devcheck 目录。

## 1. 逐条核对

| # | 旧主张（出处） | 判定 | 新的决定性证据 |
|---|---|---|---|
| 1 | 分类 `solver_condition`，处置 `environment_qualified`，范围为当前材料 + `r2e_derive_v1` + 默认 rollout profile（`hist/tasks/…/screening_record.json`；`results_20260924.md:23`） | **确认（环境维度）＋补充** | 4 次评分实跑结果一致；本批正式链 devcheck 的解题侧条件可用；私有 gold 对照在正式链的公开命令上表现正确。旧记录只做环境资格，没有审"测试是否测到要求"。本审查新发现的测试偏窄见 §3 |
| 2 | R01：派生镜像复核通过，镜像 ID 与覆盖表一致 | **确认（限定构建）** | 旧 R01 只对 R-f 机的构建 `sha256:19535845…` 成立（`facts.json identity.derived_image_id`）。本批 devcheck 和两份私有 gold 对照用的是同配方 `r2e_derive_v1` 的另一次构建 `sha256:851a10b6…`（`DEV/orig/attempt.json` 的 `overlay`）。隐藏测试没有在后者上跑过；配方相同，风险低 |
| 3 | R02 / R16：noop 只差目标键，原因行为 `assert 1 == 3`，与题面一致 | **确认** | R-f noop 日志第 39–48 行；rerun2 noop 日志规范化后与之逐行相同；M3 `git_scrub/out_after.txt` 的 noop 也只在 `test_run_exit_code` 上失败 |
| 4 | R03 / P2 §2.6：题面示例的三个导入位置不存在，照抄会 ImportError | **确认** | `followups.log` D 段三项都是 False；public_read §3.3 也指出了这一点；devcheck pr2 改正导入后可以运行 |
| 5 | R03："文字描述清楚" | **补充（部分不同意）** | 题目意图清楚，但公开文档对 Python API 的说法互相矛盾：`run.py:105-106` 的 docstring 说仍抛 `CommandError`；`CHANGELOG.md:1191` 说改抛 `IncompleteResultsError`、CLI 不再转发退出码；`cli.rst:61-71` 把命令失败列为转发退出码的一类。题面没有说明 Python API 是否要跟着改，于是存在一条会得 1 的错误路线：按 docstring 恢复 `CommandError`（K2） |
| 6 | R03：全局提示写的是 "conda testbed"（R2E 实际为 `.venv`），属 E09 | **过时** | v3 的 `public_hints` 已改成 `.venv` 措辞，并写明 "pip may be unavailable"（`PUB/public_bundle.json`）；devcheck `activation_check.json` 的前缀为 `/testbed/.venv` |
| 7 | R03 / R17：`run_tests.sh` 与 `install.sh` 在工作区可见；`install.sh` 是通用脚本，不含修复 | **确认** | 容器中 `git status` 为 `?? install.sh` 与 `?? run_tests.sh`（devcheck `env.out`）；同仓 5 题的 `install.sh` 摘要相同（`followups.log` A 段）。公开包只导出了 `run_tests.sh`（manifest 的 `untracked_missing` 为 `install.sh`） |
| 8 | R04：gold 只触碰 `datalad/cli/main.py`，不在官方测试文件内；解题不需要改 `r2e_tests` 以外的测试辅助 | **确认＋补充** | gold diff 与账本 `projection.included_paths` 一致。补充：隐藏测试依赖的 base 版辅助（如 `datalad/tests/utils_pytest.py`）在评分时不重置，候选改动它们就能影响判定。这是 R2E 的通用通道，不是本题特有 |
| 9 | R05：`.venv` 解释器 3.9.21、pytest 8.3.4、没有 pip、editable 安装、有 git-annex；gcc / make / git 可用 | **确认** | devcheck `env.out`（正式链，agent 身份）：解释器、pytest、`No module named pip`、git 2.34.1、`/usr/bin/git-annex`、`/testbed/.venv/bin/datalad`，`cwd=/` 下也导入 `/testbed/datalad`。gcc / make 只见于旧探针（`agent_probe.log:16-17`），本题不需要构建 |
| 10 | findings：M3 标记的"cwd 不在 /testbed 时导入失败"是误报 | **确认** | M3 `pkgsrc.txt` 显示在 `/tmp` 与 `/` 下都导入 `/testbed/datalad/__init__.py`，前面只多一行 git 身份警告；devcheck `env.out` 的结果相同 |
| 11 | R06：不适用（期望全是 PASSED，没有未跟踪资产） | **确认＋补充** | 补充：SKIPPED 的 `test_help_np` 依赖 stdin 不是 TTY（`ui/utils.py:40-51` 的 ioctl）。如果改用 TTY 评分，所有候选都会多出一个键而判 0。现有 6 份日志一致，属低风险的评分配置敏感点 |
| 12 | R07：权限——chown 后 `/testbed`、site-packages、HOME、`/tmp` 可写；`/rh2_private` 不可读；`/` 与 `/testbed` 下没有 `r2e_tests` | **确认** | devcheck `prelaunch.json`：`WORKDIR_OWNER=54321`，`HOME_WRITABLE=1`，`TMP_WRITABLE=1`，`HIDDEN_0=DENIED:/root`；R2E 预检三项都为 ok |
| 13 | R08：从 `/testbed` 导入，gold 19/19 | **确认** | 账本 `RH2_OBS_IMPORT_PATH=/testbed/datalad/__init__.py`；gold 19/19 共 4 次（R-f 与 rerun2 各一次，M3 两次） |
| 14 | R09：探针公开测试（`test__main__.py`）rc 0；`test_main.py` 18 passed / 1 skipped；复现 `REPRO_OBSERVED=1` | **确认** | `pubtests/…19f5….log` 第 1–2 行（uid 54321、HOME=/tmp、不联网，`docker run`，非正式链）；`agent_probe.log:144-150` 为 `EXIT_CODE=1`。探针自带的 `test__main__.py` 与本题无关（P2 README §7.3 已自述），已被本批 devcheck 的 pr3 / pr4 取代 |
| 15 | R10：没有网络，解题与测试都不需要下载 | **确认** | devcheck `prelaunch.json`：`DNS_EXTERNAL=DENIED`，`NET_forbidden_*=DENIED`，只能连 relay；评分侧 `policy.network=deny_all` |
| 16 | R12：内存峰值 751 MB / 4 GiB；setup 86 s，测试 11 s；chown 111.88 s（并发偏高） | **确认**；chown 一项**未核实** | 账本记录 `mem_peak_mb` 751–813，`test.seconds` 11.2–12.3。本批 devcheck 从容器启动到 git 清理加初始化完成约 45 s（`attempt.json` stages），口径不同，没有单列 chown 耗时 |
| 17 | R13：noop 与 gold 同条件各 2 次，结果一致 | **确认** | 两组日志去掉时间戳与临时路径后 diff 为空 |
| 18 | R14：每次都是 fresh 容器，缓存计数不变，git status 前后都是 2 行 | **确认** | 账本 `cleanup.removed=true`，`omitted_cache_count` 的 baseline 与 post 相等；devcheck `post_run_facts` 中 `RH2_GIT_STATUS_LINES=2` |
| 19 | R15：与参考逐键一致 | **确认**（`reconcile.json` 本身未读） | M3 a1 / a2 的 gold 都是 19 passed、1 skipped，键集合相同；M3 noop（`git_scrub/out_after.txt`）只在目标键上失败 |
| 20 | R17：git 已清理（没有子提交、refs、reflog、remote） | **确认** | devcheck `attempt.json` 的 `git_sanitize`：`REFS_REMAINING=0`，`REMOTES=0`，`REFLOG_ENTRIES=0`；预检 `GIT_HISTORY=ok`。来源镜像中修复提交可达（M3 `leak_path/children.txt` 的 `children=19f5b450…`，`git_before` 有 refs 264），派生镜像已清除 |
| 21 | R18：不需要修复配方或材料修订，只有解题侧条件 | **确认（环境维度）＋补充** | 环境与材料本身没有缺口，这一点成立。补充：隐藏测试只覆盖题面原例，按静态推断 K2 / K3 / 硬编码 3 都会得 1。如果本题用于训练奖励，可能需要以公开要求为依据补测。这是修订提案，需用户决定，不是本审查已作的决定 |
| 22 | R20：editable 安装与缺 git 身份是 datalad 5 题的共性；隐藏 conftest 5 题逐字相同（`551a34e5…`） | **确认** | `PRIV/hidden_tests/conftest.py` 的 sha256 为 `551a34e5…`；`followups.log` C 段 5 题摘要相同 |
| 23 | issue：agent HOME 没有 git 身份，不设身份时 `create` 报 `Author identity unknown`；评分不受影响 | **确认，且仍未解决** | `agent_probe.log:146` 为旧探针实测（同构建 `19535845…`，uid 54321）。本批正式链 devcheck `env.out` 仍打印 "highly recommended to configure Git"（HOME 是 tmpfs `/home/agent`）。v3 `public_hints` 仍没有提到 git 身份，解题者得自己发现并设置 `GIT_AUTHOR_*` / `GIT_COMMITTER_*`。评分侧的身份由隐藏 `conftest.py:12-21` 提供 |
| 24 | known_issues `prompt_quality_candidates`：建议自动检查"题面 Actual Behavior 的报错是否出现在 noop 目标键的原因行里" | **确认（本题符合）** | 题面说以 1 而非 3 退出，noop 原因行为 `assert 1 == 3` |
| 25 | `solver_conditions.public_tests` 与 `repro` 字段（探针版） | **过时（被取代）** | 被本批 devcheck 的 pr1–pr5（正式链，agent 身份）和 `private_gold_full` 取代 |

## 2. 新证据怎样改变我的初判

初判为 `needs_review`：静态候选待 actor 验证，另附测试偏窄。**这一处置不变**，但下面四处证据有所加强或更正：

1. **初判缺口 2 已补上（gold 行为从源码推断升为执行证据）。** `private_control_full.json` 中：
   - pr1 五个用例依次为 `EXIT 3 / 3 / 0 / 1 / 0`，分别对应 `--explicit` 失败、不带 `--explicit` 失败、成功、输入缺失、`--on-failure ignore`；
   - pr5 的 console script 为 `exit=3`；
   - pr2 输出 `run_main(exit_code=3) passed`；pr3 与 pr4 通过。

   因此 gold 满足 R1–R4、R6、R7 已有执行证据（清单 27 的证据升级）。这也说明 console script 用的是 `/testbed` 的改动（清单 9）。条件：root、不联网、构建 `851a10b6…`。
2. **初判缺口 5（`.venv` 是否是答案通道）部分补上。** M3 `pkgsrc.txt` 显示 site-packages 里只有 editable 的 `datalad-1.1.3+6.gb07ea09c8.dist-info`，其 `direct_url` 为 `file:///testbed` 且 `editable=true`，不含 datalad 源码副本。这是来源镜像的事实；派生镜像的评分与 devcheck 都导入 `/testbed/datalad`，与之一致。其它包未查。
3. **开发需求中"不设身份照题面示例调用 `create` 是否失败"由"actor 待验"改为"历史实测会失败"**（`agent_probe.log:146`，旧探针，非正式链）。
4. **解题侧的完整公开 `test_main.py`**：历史 pubtests 的结果为 18 passed、1 skipped，其中包括需要 console script 的 5 个测试（uid 54321，非正式链）。清单 10 的证据因此更完整。

唯一最值得先做的下一步不变：用正式评分代码实跑 K2 与 K3，同批跑 K1 与 K4。

## 3. 与历史的主要分歧

1. **测试质量（新增，历史没有覆盖）。** 历史只做环境资格审查，R18 记"不需要材料修订"。本审查读完了隐藏测试：唯一目标键只测题面原例，R2（任意 N）、R4（非命令失败仍退 1）、R6（Python API 与 rerun）、R7（ignore 退 0）都没有键保护。
   - 已由执行证据确认的是 gold 在这些路径上都正确（§2 第 1 条）。
   - 待确认的是错误实现能否拿到 1：K2（按 docstring 恢复 `CommandError`）、K3（取首条失败记录的 `exit_code` 且不回退）以及硬编码 3，按源码推断都会得 1。
   - 这对训练奖励用途有实质影响，对诊断探针用途只影响对"通过"结果的解释。
2. **题面清晰度（部分不同意）。** 历史只记了"示例导入写错"；本审查另外指出公开文档对 Python API 语义互相矛盾，这会把解题者引向会被奖励的 K2 路线。
3. **评分配置敏感点（新增，低风险）。** SKIPPED 的 `test_help_np` 依赖 stdin 不是 TTY。

**历史结论中没有被推翻的项。** 过时的两项分别是：conda 提示已改成 `.venv` 措辞；探针版的公开测试与复现字段已被本批 devcheck 取代。
