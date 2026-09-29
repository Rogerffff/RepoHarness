# numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9 旧主张核对（读历史后）

- 角色：R2E 私有主审；2026-09-25。先稿 `analysis_before_history.md` 已封存，本文不改它。
- 本轮读了哪些材料：
  - 历史引用 `refs.json` 列出的全部 8 项：旧 `screening_record.json`、`findings.md`、`facts.json`，以及 `known_issues.json`、`decisions.md`、`results_20260924.md`、复现脚本、P2 包 README。
  - 这些材料引用的部分原始证据：P2 探针的 `agent_probe.log`、`followups/bare_pytest.log`、`followups/followups.log` 的 A/B 段、M3 noop 参考日志 `facts/18b7cd9df7a4/noop_x2/out1.txt`、`reconcile_all/reconcile.json` 中本题的两条。
  - 协调者新开放的 actor 开发命令证据 `runs/r2e_actor_20260925/devcheck/numpy__18b7cd9df7a4d960550b18faa14d5473e/`（下称 devcheck）。
  - 没有读批次目录里的协调文件。
- 判定词：**确认**（新证据支持）、**推翻**（新证据相反）、**过时**（当时成立，但条件或记录已变）、**未核实**（本轮没有决定性证据）。

## 1. 旧主张逐条核对

| # | 旧主张（出处） | 判定 | 新的决定性证据 |
|---|---|---|---|
| 1 | 分类 `solver_condition`，"环境本身无缺口"，处置 `environment_qualified`，范围为"当前材料 + `r2e_derive_v1` + 默认 rollout profile"（旧 `findings.md:3`、旧 `screening_record.json` 的 `disposition`、`results_20260924.md:27`） | 确认（仅限环境范围） | 4 份当前评分日志都已读：noop 10/11，只有目标键不一致；gold 11/11。devcheck 的 13 项检查全部为 true。注意"环境合格"不等于题意与测试合格，后者见 §3 |
| 2 | gold 11/11、导入 `/testbed/numpy`；noop 只有 `TestDocs.test_poly_eq` 失败，原因行与题面一致；与参考逐键一致（R01/R02/R08/R15/R16） | 确认 | 评分日志第 31–42 行与账本 `observations`；M3 来源镜像 noop 原始日志 `out1.txt` 第 26–41 行给出同一失败；`reconcile.json` 中本题 noop 与 gold 各 5 份参考（M3 ×2、旧探针 ×3）观测映射都相同 |
| 3 | R16 说目标键对应"`poly1d.__eq__` 与 None 比较" | 确认，但不完整 | 目标键第 220–223 行还检查 `p != None` 和 poly1d 之间的比较。只改 `__eq__` 返回 `NotImplemented` 的实现正是在第 220 行失败，这是本题主要的区分点（先稿 §3.3 D） |
| 4 | `.venv` 是 Python 3.7.9，pytest 7.4.4，没有 pip / uv，有 gcc / make（`findings.md:7`，R05） | 确认 | devcheck `captures/env.out`（agent 身份，经 Claude Code Bash）：`3.7.9 1.13.0.dev0+6a3edf3 /testbed/numpy/__init__.py`、`No module named pip`、`pytest 7.4.4`，另外直接看到 `nose 1.3.7`。gcc / make 只有旧日志 `agent_probe.log:16-17`，devcheck 没有复测 |
| 5 | `chown -R /testbed` 耗时 19.1 s（`findings.md:7`，R12） | 过时 | 正式链已改为复用初始化结果：devcheck `attempt.json` 中 `agent_user_init_*` 为 `mode=reused`，从容器启动到可信初始化完成约 6.9 s（含 git 清理 0.61 s）。两者条件不同，不可比 |
| 6 | 就地构建、没有装进 venv，所以 `/testbed` 必须在 `sys.path` 上：在 `/tmp` 下导入失败，脚本放在 `/testbed` 外即使 cwd 是 `/testbed` 也失败，裸 `pytest` 收集失败，`python -m pytest` 可以（`findings.md:8,15`；issues；known_issues `testbed_must_be_on_sys_path`） | 确认 | 旧原始日志：`agent_probe.log:24-27`（`IMPORT_FROM_TMP_RC=1`）、`:117-118`（`IMPORT_PLAIN=fail`）、`bare_pytest.log`（`CMD=[pytest] RC=2`，`python -m pytest` 10 passed）。devcheck 在 cwd=`/testbed` 下用 `python -c` 和 `python -m pytest` 都正常。几种失败方式 devcheck 没有复测 |
| 7 | 公开复现 `REPRO_OBSERVED=1`（`findings.md:9`，R03/R09） | 确认，且证据更强 | devcheck `captures/mcve_statement.out`：在正式启动路径下以 agent 身份运行，同样在 `polynomial.py:1202` 抛 `AttributeError`。`mcve_other_entries.out` 显示 `p != None` 经 `__ne__`（第 1207 行）走到同一根因 |
| 8 | 公开 `numpy/lib/tests/test_polynomial.py` 10 passed；探针另选的 `numpy/tests/test_ctypeslib.py` 7 passed（`findings.md:10`，R09） | 前半确认；后半未核实 | devcheck `captures/test_polynomial.out`：10 passed，1 个 nose 的 `imp` 弃用警告；`test_regression.py -k poly`：9 passed。`test_ctypeslib.py` 与本题无关，没有复查 |
| 9 | 残留的 `numpy/linalg/lapack_lite/f2c_config.c.patch` 是 git 跟踪的上游文件（`findings.md:11`，R17） | 确认 | 公开 `worktree_manifest.json` 的跟踪文件列表里有它，也只有它一个 `.patch` 文件；`followups.log` B 段一致 |
| 10 | "缺口：R13 只有一次运行"；"处置暂为 unknown"（`findings.md:3,13`；P2 README 逐题表；旧 `screening_record.json` 的 `disposition.reason`） | 过时 | 中央复跑已经并入：旧记录 R13 为 pass，state 也已是 `environment_qualified`，但 `findings.md` 和 `disposition.reason` 的文字没有同步。复跑日志 `_rerun2/…f466e78b`、`…f34c3153` 已读 |
| 11 | 无网络，解题和测试都不需要下载（R10、solver_conditions） | 确认，并补充细节 | devcheck `prelaunch.json`：外部 DNS、4 个禁止目标和上游直连都是 DENIED，只有模型中转 `NET_relay` 可连 |
| 12 | 全局提示写 conda testbed，属于 E09，不计入本题（R03；known_issues `solver_hints:conda_wording_and_activation_prefix`，状态 open） | 部分过时，部分未核实 | 解释器前缀已在正式链解决：devcheck `activation_check.json` 中 `ACT_EXPECTED_PREFIX=/testbed/.venv`，`VIRTUAL_ENV` 已设置，核对通过。提示措辞未核实：devcheck 用的是合成的用户消息（`stub/requests/messages_000.json`），没有捕获本题真实渲染的提示 |
| 13 | `install.sh` 是本仓库通用安装脚本，不含修复（R03/R17） | 确认 | `followups.log` A 段：7 道 numpy 题的 `install.sh` 摘要相同（`5f15d21e…`，56 行）；两次 noop 和 5 份参考 noop 都失败，说明修复没有被预装。脚本全文我没有读 |
| 14 | 官方测试文件只有 `r2e_tests/{__init__.py,test_1.py}` 和 `run_tests.sh`；gold 只改 `numpy/lib/polynomial.py`；解题不需要改其它测试辅助文件（R04） | 确认 | 隐藏测试只从 `numpy.testing` 导入 helper，合法修复不需要动它们。补充：候选改这些 helper 会影响评分，但这是共享机制，本题没有特例 |
| 15 | 期望 11 键全是 PASSED，没有外部服务（R06、R11 为 not_applicable） | 确认 | `expected_output.json`；隐藏测试不联网 |
| 16 | 派生镜像里隐藏测试不可读、git 已清理（R07、R17） | 确认，并扩展到正式链 | devcheck `captures/r2e_preflight.out`：`HIDDEN_TESTS=ok`、`GIT_HISTORY=ok`。`attempt.json` 的 git 清理结果：`REFS_REMAINING=0`、`REMOTES=0`、`REFLOG_ENTRIES=0`、`UNREACHABLE_OBJECTS=0`，HEAD 仍是 base |
| 17 | 资源：峰值约 296 MB，test 约 1 s（R12） | 确认 | 账本 `resource.mem_peak_mb`：gold 296.48，noop 304.85；`test_seconds` 0.71–0.95 |
| 18 | noop / gold 同条件各 2 次一致（R13）；每次 fresh 容器，清理干净，gold 的 `candidate_test_like_paths=[]`（R14） | 确认 | 4 个账本行都已读：`cleanup.removed=true`，`omitted_cache_count` 前后相同 |
| 19 | 不需要修复配方或材料修订（R18） | 确认（环境范围） | 我建议的测试修订属于测试质量范围，而且只在打算用于训练时才考虑（§3），不与 R18 冲突 |
| 20 | 导入条件是本批 7 道 numpy 题共有的（R20） | 本题确认；其余 6 题未核实 | 不在本题范围 |
| 21 | 复现脚本在读隐藏测试和 gold 之前写成（`findings.md:19`，E06） | 未核实 | 从产物无法证明先后顺序。脚本内容只用了题面示例，与这个说法一致 |

没有推翻项。历史中的环境事实都得到确认，其中几项有了更强的证据；过时的只是记录文字，以及已被新链路替代的条件。

## 2. 我对先稿判断的改动与理由

| 先稿判断 | 现在的判断 | 理由（新证据） |
|---|---|---|
| 检查 29 为 issue：正式 actor 用来源镜像，`/r2e_tests` 可读，修复提交可达 | **pass**（附条件：派生镜像切换还待 A 线审查） | 协调者告知正式 actor 已改用派生镜像。devcheck 在正式启动路径下：`checks.image_is_overlay_derived_id=true`，preflight 的隐藏测试和 git 历史两项都 ok，refs / remotes / reflog 都是 0。先稿依据的是 09-25 环境卡的代码事实，当时成立，现在已被替代 |
| 检查 10 为 unknown（actor 待验） | **pass** | devcheck：真实 Claude Code 2.1.205 以 agent 身份运行，复现命令、`python -m pytest` 两条公开命令都正常。私有 gold 对照中同一批命令的结果变为 `False` 和 `True False False False NotImplemented`，公开测试仍然全过，说明公开验证路径能区分修前与修后 |
| 检查 8：解题侧只有镜像层面的实测 | pass，证据层级升为"正式启动路径" | `prelaunch.json`：uid 54321，工作目录属主 54321 且可写，能力全部丢弃，不允许提权（no-new-privileges），`/rh2/bash_env` 为只读 0644 |
| 检查 22：部分通过，因为 run_refs 没有 M3 noop | **pass** | `reconcile.json` 中本题有 noop 参考 5 份（M3 ×2、旧探针 ×3），与 RH2 逐键相同；我读了 M3 `out1.txt` 原文核对 |
| venv 里有 nose 是推知 | 已实测 | devcheck `env.out`：`nose 1.3.7` |
| `install.sh` 内容未知 | 部分解决 | 7 题摘要相同；就地构建的说法来自 P2 README §2.3。全文仍没有读，这不影响本题判断 |
| 检查 3 为 unknown | 仍为 unknown，但范围缩小 | 解释器前缀的一半已经解决；真实渲染的消息和提示措辞仍未捕获 |
| 检查 25、32 为 issue（反例 N、I），`test_doctests` 是死键，D 是有依据的区分点 | **不变** | 历史只审环境，没有涉及测试语义。devcheck 的私有 gold 对照印证了先稿对 gold 行为的静态推断（`p == 3`、`p == [1, 2, 3]` 为 False，`p.__eq__(None)` 为 NotImplemented）。N、I 的真实评分由协调者安排 |
| 处置 `needs_review`，理由"静态候选待 actor 验证" | state 不变，理由更新 | 开发条件已由正式启动路径的 devcheck（桩端点）实测；还剩三件事：A 线审查派生镜像切换、捕获真实提示渲染、四个候选的真实评分 |

## 3. 与历史的主要分歧

1. **范围不同，结论不冲突。** 历史做的是环境资格审查，给出 `environment_qualified`，本题没有进入 `prompt_quality_candidates`，也没有 issue 项。我确认了全部环境事实。另外新增了历史范围之外的测试质量发现：
   - 目标键只测 `None`，只特判 `None` 的 N 可以得 1；
   - poly1d 之间的比较对象身份与值相等无法区分，删除比较方法的 I 可以得 1；
   - `test_doctests` 是死键；
   - `__ne__` 陷阱 D 是本题主要的区分点。

   这些都是静态推断，真实评分待出，不影响把本题用作开发诊断。
2. **历史记录中有过时文字**（第 10、12 项）。建议协调者收口时同步 `findings.md` 和旧 `disposition.reason`，并更新 known_issues 中 E09 的"激活前缀"部分。这不属于本题结论。
3. **镜像版本说明。** 评分证据来自派生镜像 `61363b45…`（R-f / 复跑时的构建），devcheck 用的是同一配方在另一台机器上的构建 `065c0cc8…`。两者同源同配方，但没有逐字节核对内容。devcheck 自带的检查确认它是本题的覆盖派生镜像。
