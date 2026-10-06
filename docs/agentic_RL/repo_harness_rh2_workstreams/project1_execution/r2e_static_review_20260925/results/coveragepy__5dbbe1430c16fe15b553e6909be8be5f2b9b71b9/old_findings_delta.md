> **第二步由接续会话完成：原主审会话在封存初判后因 API 错误中止。** 本文由接续会话写成；封存初判 `analysis_before_history.md` 原样保留、未改一字；`reviewer_initial.md` 没有读。

# coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9：旧主张核对（读历史之后）

- 角色：R2E 私有主审第二步（静态审查），2026-09-25。
- 执行边界：没有运行项目代码、容器或远端。只做了三类文本核对：
  1. 6 份日志的 sha256 与 `run_refs.json` 比对，全部一致；
  2. 在 scratchpad 的 base `coverage/control.py` 复制件上，分别应用私有 `gold.patch` 和 M3 自建的 `gold.diff`，再用 `git hash-object` 比较结果；
  3. 用 `grep` 查同批另外 4 道 coveragepy 题公开 worktree 里 `_warn` 的相关行。
- 读过的历史（`refs.json` 所列）：
  - 本题的 `screening_record.json`、`findings.md`、`facts.json`；
  - `known_issues.json` 中与本题相关的族：`support_stale_helper:coveragepy_5dbbe143`、`solver_condition:no_pip_in_venv`、`solver_hints:conda_wording_and_activation_prefix`、`hidden_test_relocation_artifacts`、`expected_provenance_mixed`、`prompt_quality_candidates`；
  - `decisions.md` 中与本题相关的行（E05、E06、E09、E10、E13、E14、E18）；
  - `results_20260924.md`、复现脚本、`packages/p1/README.md`；
  - 另读了同目录的 `checks_r2e.md`，用来把 R 编号对到 40 项编号。
- 为核对旧主张而打开的原件（都是历史记录引用过的）：
  - `dev_probe.json`、`agent_probe.log`、`hidden_support_scan.md`；
  - 来源原始行：`s2_r2e/raw/r2e_gym_subset_48_e8b9fcbc.jsonl` 中本题一行的 `modified_files`、`parsed_commit_content`、`prompt`；
  - `reconcile.json` 中本题的两行；
  - M3：账本第 23、70 行，runner 源码 `r2e_probe_m3.py:318-329`，`gold.diff` 与 `git_gold.diff`，noop 参考日志；
  - `expected_provenance.md`，以及 R-f 的 `prompts.jsonl`。
- 为确认共享阻塞的当前状态，只读了工作树里两处代码：
  - `rh2/src/repoharness2/adapters/slime/prepared_task_face.py:412-451`，git 状态为 ` M`（有未提交改动）；
  - `rh2/src/repoharness2/envpack/ingest_r2e_subset.py:196-215`，git 状态为 `??`（未跟踪的新文件）。

## 0. 结论

1. **历史只做了环境资格审查。** `checks_r2e.md` 第 3 行写明，题意、反作弊、真实求解都不在那一轮。历史的环境结论逐条核实成立：
   - 评分可复现；
   - 镜像层面的开发条件满足。
2. **历史没有覆盖本题的主要问题。** 题面没有说按什么判定"重复"，隐藏测试却强制按 slug 去重。历史在这点上的沉默是范围所限，不是相反结论。新找到的来源证据还加强了这一判断：题面生成器的输入里有 gold 的 docstring "(determined by the slug.)"，生成出来的题面把这一句漏掉了。
3. **需要修正的历史主张有三条：**
   - R16"目标键与题面对应"只对了一半，属于部分推翻。
   - R04 的事实成立，但影响要收窄。它给的处理办法（"同 datalad 58ba5165 的做法"）在本题不能照搬。
   - R07 / R17 的"无泄漏"只适用于派生镜像；对正式链来说，这个结论已经过时。
4. **封存初判的处置不变：** `needs_review`，理由是题意/测试争议。另有 5 处更正或补充（见 §2），都不改变处置。

## 1. 旧主张逐条

判定：**确认**（新证据支持）/ **部分推翻**（部分成立，需收窄或改写）/ **推翻** / **过时**（当时成立，条件或范围已变）/ **未核实**（没有拿到决定性证据）。

| # | 旧主张（出处） | 判定 | 新的决定性证据 |
| --- | --- | --- | --- |
| H1 | 身份对应：派生镜像复核通过，隐藏测试树、入口脚本、HEAD 与评分面一致（R01） | 确认 | 期望 `c65a3c08…`、隐藏测试树 `5a450eab…`、入口 `8285765f…` 这三个 sha256，与 `grading_bundle.json` 一致，也与日志中的 `RH2_SETUP_*` 行一致。探针报 `GIT_HEAD=8240c58c…`。**新增：** M3 在来源镜像里跑出的 `git diff HEAD 5dbbe143 -- coverage/control.py`（`…/gold/a1/git_gold.diff`）与私有 `gold.patch` 逐字节相同（`cmp` 返回 0）。 |
| H2 | noop 得 0，只有目标键不符，原因是 `TypeError`（R02、R16、findings） | 确认 | 4 份 noop 日志：当前材料 2 份，M3 在来源镜像上 2 份（`M3/facts/5dbbe1430c16/noop_x2/out{1,2}.txt`）。失败都在 `test_1.py:545`，报 `TypeError: _warn() got an unexpected keyword argument 'once'`，汇总都是 `1 failed, 74 passed`。 |
| H3 | 题面带可运行的示例，原样运行就能复现（R03、复现脚本） | 确认，但只到渲染与复现这一层 | 探针的 `REPRO_OUTPUT` 显示 TypeError，`REPRO_OBSERVED=1`。R-f `prompts.jsonl` 里本题的 prompt 与 `user_prompt.txt` 逐字节相同（850 字符）。R03 不检查题意是否完整，这一点另记为清单 23 的 issue。 |
| H4 | 目标键与题面描述的行为对应（R16 pass） | **部分推翻** | 题面能支撑的只有两点：不再抛 TypeError；第一条警告照常显示。决定性断言 `assertNotIn("Warning, warning 2!", err)`（`test_1.py:549`）要求按 slug 或更粗的键去重，题面第 18 行没有写。来源行的 `prompt` 字段里有 gold diff，含 "only show this warning once (determined by the slug.)"，生成的题面却没有这一句。 |
| H5 | 隐藏测试依赖修复前的 `tests/coveragetest.py`，"正确解可能被判 0"；需要时可按 datalad 58ba5165 的做法修订（R04 issue、`support_stale_helper` 族、E18） | 事实**确认**；影响**收窄**；处理办法**部分推翻** | **事实：** `test_2.py` 与 base 的差别只在第 267 行，假函数多了 `once=False`，外加一行注释。来源提交的 `modified_files` 恰好是 `coverage/control.py`、`tests/coveragetest.py`、`tests/test_api.py`。<br>**影响：** 只影响给现有调用点加 `once=True` 的改法，而题面没有要求这样改。用到 `assert_warnings` 的键有 5 个：`test_two_getdata_only_warn_once`、`test_two_getdata_warn_twice`、`test_combining_corrupt_data`、`NamespaceModuleTest.test_bug_572`、`SourceIncludeOmitTest.test_source_include_exclusive`。修复后的假函数也写明"不实现 once"（`test_2.py:269`）。举例：给 `control.py:697` 加 once 后，第二条"No data was collected"会被压掉，这违反 `test_1.py:380` 注释写明的预期（有新活动后应再次警告）。换成修复后的假函数，这个改法反而能通过；旧假函数抛 TypeError，碰巧把它拦住了。<br>**处理办法：** 照 datalad B1 那样让 test_1 整体改从 `.test_2` 导入，在本题会出问题。`test_2.py:38` 的 `TESTS_DIR = os.path.dirname(__file__)` 会指向 `r2e_tests/`，而 `test_2.py:490-491`（`UsingModulesMixin`）和 `test_1.py:880` 都依赖 `tests/modules`。此条是静态推断。 |
| H6 | 依赖与工具链：python 3.7.9、pytest 4.6.6 + xdist、pip 19.3.1、editable 安装（R05） | 确认（镜像层面） | `agent_probe.log` 中的 `WHICH_pytest`、`PYTEST_VERSION`、`PIP_VERSION`；`IMPORT_FROM_TMP=/testbed/coverage/__init__.py`；M3 `pkgsrc.txt` 中 `dir_info.editable=true`。`tests/test_annotate.py` 在默认 addopts（`-n3 --no-flaky-report`，输出 `bringing up nodes...`）下 rc 0，说明 xdist、flaky、unittest_mixins 都已安装。这回答了公开读者关于测试依赖的未知项。 |
| H7 | 期望里没有非 PASSED 键，资产与外部服务不适用（R06、R11） | 确认 | `expected_output.json` 的 75 键全部是 PASSED。 |
| H8 | agent 身份下工作区可写，私有目录不可读，`r2e_tests` 不存在（R07） | 确认（派生镜像） | 探针：`WRITE_TESTBED/SITE/HOME/TMP=ok`，`WRITE_ROOT_FS=denied`，`PRIVATE_LS` 为 Permission denied，`R2E_TESTS_ROOT/WORKDIR=absent`。正式链的情况见 H16。 |
| H9 | 评分时实际执行的是候选代码（R08） | 确认 | 4 次评分运行都从 `/testbed/coverage/__init__.py` 导入，版本 5.0.2a1。 |
| H10 | 可以做本地开发验证（R09） | 确认（镜像层面），需注明范围 | 探针跑的公开测试是 `tests/test_annotate.py`（4 个用例，rc 0），与本题无关。与本题相关的 `tests/test_api.py -k warn` 没有跑过；说它能跑，是按同一套依赖推断的。 |
| H11 | 无出网（R10） | 确认 | 探针 `NET_CONNECT_RC=1`、`NET_DNS_RC=2`；评分侧网络为 `deny_all`。 |
| H12 | 资源：峰值约 301 MB，setup 约 17 s，测试约 4 s（R12） | 确认 | 4 次运行的内存峰值在 296.7–303.5 MB 之间；按日志时间戳，测试段耗时 3.40–4.03 s。 |
| H13 | 同条件下两次结果一致（R13） | 确认 | 两轮 noop 的差异集合都是 `{ApiTest.test_warn_once}`；两轮 gold 都是 75/75。 |
| H14 | 每次评分都用 fresh 容器，基线自带的 `__pycache__` 前后不变（R14） | 确认 | 依据是历史账本（`facts.json` 中 `cleanup_removed=true`），我没有独立重算。 |
| H15 | 与参考 runner 逐键一致（R15） | 确认 | `reconcile.json` 第 [6] 行（noop，M3 两份参考）和第 [54] 行（gold）都是 `observed_maps_equal=true`。noop 行的 `reference_ledger_consistent=null`：按字段推断，是因为 noop 参考不在 M3 gold 账本里（`m3_ledger_rewards=[]`），不代表不一致。 |
| H16 | 无泄漏：HEAD 没有子提交，没有 remote，reflog 为 0，`fix_present=no`（R17） | 确认（派生镜像）；**对正式链已过时** | M3 在来源镜像上的 facts：`fix_reachable=commit`、`remotes=1`、`refs=171`、`commits_after_head=2401`、`r2e_tests_root=3`。环境卡 §2 记载正式 actor 取的是来源镜像。工作树的 `prepared_task_face.py:412-451` 已把 R2E 改走派生镜像，并改用 `.venv` 前缀，但这是未提交的改动，没有审查或验证记录，因此仍按"actor 待验"处理。 |
| H17 | 没有配方、材料修订或共享修复（R18–R20） | 确认 | `revisions.json` 为 `[]`；`grading_bundle.json` 中 `material_revisions=[]`。 |
| H18 | 解题侧条件：不要求 cwd、用 `.venv`、有 pip、无网络，"无额外解题侧条件"（`solver_conditions`、findings） | 确认（镜像层面）；正式链待验 | 依据同 H6、H8、H11。以下三项没有经过验证：Claude Code 非交互 shell 下的 PATH、`/rh2/bash_env`、提示措辞。 |
| H19 | 本题的 venv 里有 pip（`no_pip_in_venv` 族） | 确认 | `PIP_VERSION=pip 19.3.1 …` |
| H20 | 提示里的 conda 措辞是全局问题，状态 open（E09、`solver_hints` 族） | 未核实（修复在进行中） | 工作树里未跟踪的 `ingest_r2e_subset.py:196-215` 已有 `R2E_PUBLIC_HINTS` 草案（写的是 `.venv`、"`pip` may be unavailable"、"judged by a separate set of tests"），其注释说正式链目前不注入这段提示。本题的静态包仍是来源原来的 conda 措辞。 |
| H21 | 三方比对一致（`expected_provenance_mixed` 族）：来源期望、来源宿主机的执行记录（H）、发布镜像的实测结果（I） | 确认 | `expected_provenance.md:3`：本题在 E=H=I 的 41 题之内。 |
| H22 | "环境无缺口，分类 `env_ok`"（findings、P1 README 表） | 过时 | 历史自己已经按 E18 改为 `material` / `grading_ok_open_items`。本审查的判断是：环境侧确实没有阻断缺口，主要问题在题意与测试。 |
| H23 | 未完成项 `support_pending_decision` 交给静态筛查判断（disposition、E18） | 本审查的判断（建议，尚未决定） | 建议不修订，关闭这个未完成项，作为已知低风险留下说明，理由见 H5。本题另立"题意/测试争议"，处置为 `needs_review`。 |
| H24 | "低风险"（E18、known_issues） | 确认 | 同 H5。 |
| H25 | `prompt_quality_candidates` 族没有列入本题 | 不构成相反结论 | 历史的范围不含题意（`checks_r2e.md:3`）；这一项由本审查新增。 |

## 2. 与封存初判的差异

**处置不变**：仍为 `needs_review`，理由是题意/测试争议。

- 历史材料里没有任何关于去重语义的证据。
- 新看到的来源行 `prompt` 说明，"按 slug 判定"是题面生成时丢掉的信息，而不是一条公开材料里本来就有依据的要求。这加强了初判。

以下更正与补充都不改变处置：

1. **初判附录 A2 的未知项已解决。**
   - M3 runner（`r2e_probe_m3.py:318-329`）比较的是两份 diff 的改动行：一份是它自建的 `gold.diff`，一份是 `git diff HEAD 修复提交`。
   - 自建 diff 在 docstring 结尾的 `"""` 处是"删一行再加一行"，所以逐行文本对不上，标志为 `false`。
   - 两份 diff 分别应用到 base 复制件上，结果都是 blob `4358a541…`，内容相同。
   - `git_gold.diff` 与私有 `gold.patch` 逐字节相同。
   - 结论："gold 就是上游提交对非测试文件的全部改动"成立，证据比初判更强。
2. **初判 §5(e) 的测试段时长写错了**：应为 3.40–4.03 s，不是 3.4–4.4 s。
3. **初判 §7 可以写得更准。**
   - 首个 `once=True` 调用者（`slug="dynamic-conflict"`）不只出现在 016af5f6 里。016af5f6、97997d2c、f5eb5f21 三题都在 `control.py:589`，ea6906b0 在 `control.py:620`。
   - 同族判断不变。
4. **初判 §6 的开发条件得到镜像层面实测的补强**（H6）。
   - 包是 editable 安装，在 `/tmp` 下也能导入。
   - 因此公开读者给的 C2、C6 两条命令，在镜像层面具备前提条件。
   - 与本题相关的公开测试仍然没有实际跑过。
5. **两处补充。**
   - 初判说"候选可以改 `tests/coveragetest.py`，合法解不需要改它"。这里补一句：它同时是一条绕过路径。候选可以在 `CoverageTest` 或模块级代码里给 `coverage.Coverage._warn` 打补丁，一行 `coverage/` 源码都不改，就可能让目标键通过。这属于共享机制（环境卡 §3），是静态推断，没有实跑。
   - 初判的"共享阻塞：正式 actor 取来源镜像"：工作树里已经有未提交的实现，但结论仍是"actor 待验"（H16、H20）。

## 3. 更新后的建议队列（都是建议，尚未决定）

1. **唯一最值得先做的一步**：在当前派生镜像 `sha256:81bf06a0…` 上用 RH2 回放评分，跑下表 4 个候选。目的是把误拒和漏测从静态推断变成执行证据，再据此写题面修订提案。镜像所在机器的现状不明，可能需要按 `r2e_derive_v1` 重建镜像。

   | 候选 | 实现 | 预期得分 | 用途 |
   | --- | --- | --- | --- |
   | CE1 | 按消息去重 | 0 | 检验误拒 |
   | CE2 | 按（消息, slug）去重 | 0 | 检验误拒 |
   | CE3 | 按 slug 去重，用独立集合记录 | 1 | 正对照 |
   | CE4 | 过粗：第一次 once 之后，所有 once 警告都不显示 | 1 | 检验漏测 |

2. **公开规格修订**（T0，由用户决定）：在 Expected Behavior 后补一句"按 slug 判定"，依据是 gold 的 docstring。修订后用 CE1 和 CE3 复验。
3. **R04 不修订。** 如果以后仍要修，采用"评分前恢复修复后的 `tests/coveragetest.py`"这类做法，不要改导入路径。
4. **两项共享机制问题**，交给共享机制负责人处理，不按单题修：
   - 隐藏测试会导入仓库里的测试辅助模块，而候选可以修改这些模块，形成绕过路径。一种处理是评分时把被导入的仓库测试模块恢复到 base 版或修复后版本。
   - 正式链的派生镜像路由与 R2E 专用提示：改动已在进行，还需提交、审查、验证。
5. **划分数据时**，本题与同批 016af5f6、97997d2c、ea6906b0、f5eb5f21 视为同族。
