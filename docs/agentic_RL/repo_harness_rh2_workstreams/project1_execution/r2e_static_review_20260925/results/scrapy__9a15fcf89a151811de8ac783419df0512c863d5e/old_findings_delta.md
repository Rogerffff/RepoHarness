# 旧主张核对：scrapy__9a15fcf89a151811de8ac783419df0512c863d5e

> **第二步由接续会话完成：原主审会话在封存初判后、读历史阶段因 API 错误中止。** 原会话没有写出第二步的任何文件。封存初判 `analysis_before_history.md` 未作任何改动。

- 角色：R2E 私有主审（静态审查），接续执行角色卡第 7 步后半与第 8 步，2026-09-25。
- 顺序：先读角色卡、四份方法文档、`public_read.md` 和 `analysis_before_history.md`，并对照原件核对了其中的关键主张（附录 A）；之后才打开 `history/…/refs.json` 列出的历史路径。**未读** `reviewer_initial.md`、本批 README 和 `assignments.json`。
- 没有运行项目代码，没有开容器或远端，也没有修改任何原件。文中只读过生产代码（`scoring.py`、`r2e_parsers.py`）；这两个文件与 R-f 运行时的代码快照逐字节相同（附录 A）。
- 证据级别：沿用封存初判的标记，另加两种。
  - **【离线重算】**：用生产函数对已有日志重新判分，没有在修订后的材料上真实评分。
  - **【历史镜像层面实测】**：环境阶段 P4 包在派生镜像中以 agent/54321 身份、`--network none` 跑出的结果。
- 编号对照：下文一律使用历史提案的选项编号。
  - **A** = 不改。
  - **B** = 修改隐藏测试和期望，两侧对称去掉两个键。
  - **C** = 评分时对称忽略指定键。
  - **D** = 隔离。
  - 封存初判 §6 的“A（修订）”就是这里的 **B**。封存初判的“B（不改材料、只加判读规则）”记作 **A′**。

## 0. 结论

1. **历史的事实主张基本都能复核。** 下列各项都在原件或生产代码上核对成立：
   - 目标键；
   - noop 与 gold 的结果，以及两次运行一致；
   - 与 M3 逐键一致；
   - P4 更完整修复（下称 over-fix）经真实评分得 0；
   - 只删期望键无效，必须在期望和观测两侧对称去掉。
2. **主要分歧在推荐处置。** 历史推荐 D（本轮隔离），理由是 B 要为 1 题重做派生镜像和 pins。本审查不采纳 D 作为默认，理由有三：
   - **成本论据已部分过时。** 09-24 夜的 E16 已经建成 `material_v2`，支持对隐藏测试做 `edits`、对期望做 `expected_file_replace`。同仓的 `cfed9b66` 就是按这条路径修订并验收的。
   - **这两个键是死键。** 两个测试都在第一个带头映射处抛 `TypeError`，后面的断言从未执行。所以对称去掉不损失任何实际生效的覆盖。
   - **去掉它们有上游依据。** 它们会进入期望，是因为 R2E 把测试文件搬到 `r2e_tests/`，绕开了上游在 `tests/py3-ignores.txt:40` 对整个文件的 py3 忽略。

   因此仍按封存初判的方向建议：要作 reward 就做 **B**；不想为这题付重建成本时退回 **D**；近期做诊断可以用 **A′**。
3. **历史只提升了证据级别，没有改变处置。** 下面两项从【静态推断 / actor 待验】升为【历史镜像层面实测】：
   - 显式给出路径运行公开测试，结果是 5 过 2 败；
   - `cwd=/tmp` 时也能导入。

   Twisted 24.11.0 和 zope.interface 7.2 的版本已从镜像的安装清单核实。
4. **历史结论只在派生镜像上成立，需要注明。**
   - 环境阶段所说的“环境无缺口”和“R17 泄漏 pass”，检查对象都是**派生镜像**。
   - 环境卡 §2（09-25 核对的代码事实）指出，正式 actor 目前用的是**来源镜像**。在来源镜像里：
     - `/r2e_tests` 所有用户可读；
     - 修复提交可达；
     - 远端 1.1…2.x 分支都在（M3 facts）。

## 1. 旧主张逐条核对

**H1　目标键只有 `test_from_content_type`；noop 的失败原因是 x-json 被判成 `Response` 而不是 `TextResponse`，与题面一致**（出处：screening_record R16，facts `R16_f2p_keys`）
- 判定：**确认**。
- 证据：
  - R-f noop 日志（`…noop-s_49e74388`）第 :78 行是断言原文，:122-128 是状态段；
  - 账本 `ledger_r2e_all_noop.jsonl:45` 的 `mismatched` 只含目标键；
  - M3 的 `noop_x2/out1.txt` 与 `out2.txt` 第 :112-114 行同样是三个 FAILED。

**H2　noop 得 0 只因 1 个键不符，没有缺键，也不是零解析**（出处：R02）
- 判定：**确认**。证据同 H1；`num_parsed_tests=7`。

**H3　gold 7/7、reward 1，导入的是 `/testbed/scrapy/__init__.py`**（出处：R08）
- 判定：**确认**。
- 证据：
  - R-f gold 日志第 :1 行为 ` M scrapy/responsetypes.py`，:22 行为 `.F....F`，:103-109 为状态段；
  - `TypeError` 的行号从 56 变为 57，说明补丁确实生效。

**H4　noop 与 gold 在同条件下各跑两次，结果一致**（出处：R13，由中央复跑并入）
- 判定：**确认**。
- 证据：`_rerun2/ledger_{noop,gold}.jsonl` 第 45 行与 R-f 相同，两份日志的状态段也相同。

**H5　R15 agree；提案事实表写“RH2 与两个独立 runner 对该题逐键一致”**
- 判定：**实质确认，措辞推翻**。
- 证据：`runs/r2e_rf_20260923/reconcile_all/reconcile.json` 第 44 项（noop）和第 92 项（gold），每项的两组比较的 `source` 都是 `m3`。
  - noop 的参考日志是 M3 facts 的 `noop_x2/out1.txt` 与 `out2.txt`；
  - gold 的参考日志是 M3 gold 账本的 a1 与 a2。
  - 逐键结果、差异集合和 reward 全部一致。
- 说明：
  - 这是同一个独立 runner（M3，来源镜像、来源版材料）的两份日志，不是两个 runner。
  - 另有新增：`run_refs.json` 只列了 M3 的 gold。这里补到 M3 的 noop ×2，同样与 RH2 逐键一致。

**H6　期望中 2 个 FAILED 键的失败点在库代码里（对 bytes 用 str 切分），原因是 py3 移植没做完，合法的源码改动就能把它们翻成 PASSED**（出处：R06、提案、known_issues 的 flippable 族）
- 判定：**确认，并补上根源**。
- 证据：
  - traceback 落在 `/testbed/scrapy/responsetypes.py:56`（gold 下为 :57）；
  - 上游在这个 base 上把整个 `tests/test_responsetypes.py` 列进了 `tests/py3-ignores.txt:40`，`conftest.py:25-29` 在 py3 下就不收集这个文件；
  - R2E 把它搬到 `r2e_tests/` 后绕开了这条忽略。
- 说明：历史没有提到 py3-ignores 这一来源。补上它之后，对称去掉这两个键就是在恢复上游的意图，而不是新增一种评分口径。

**H7　P4 over-fix 候选经真实评分 7/7 PASSED，reward 0**
- 该候选是 gold 加上两处改动：`from_content_type` 和 `from_content_disposition` 先对 bytes 做 latin-1 解码。
- 判定：**确认**（历史真实 RH2 评分，诊断用途）。
- 证据：
  - `p4/ledger_overfix.jsonl:1`：`expected_match` 为 5，`mismatched=[test_from_args, test_from_headers]`，`included_paths=[scrapy/responsetypes.py]`，派生镜像 `fe908bed…` 与当前相同；
  - 评分日志第 :33-39 行全部 PASSED，`RH2_TEST_RC=0`；
  - 候选 diff 的 sha256 为 `81cedada…`，与账本一致。

**H8　只删期望键不行（在并集口径下会被记为 unexpected，gold 也得 0）；两侧对称去掉后 noop 0 / gold 1 / over-fix 1**（出处：提案、P4 README §2.1、acceptance ⑥）
- 判定：**确认**。证据级别为【离线重算】加【静态】。
- 证据：
  - `p4/offline_rescore_9a15fcf8.json` 的九行结果；
  - 静态读 `envpack/scoring.py` 的 `expected_map_matches`：`unexpected = obs_keys - exp_keys`，键集不等就不算 resolved；
  - 静态读 `r2e_parsers.prime_calculate_reward`：两侧键数不等直接给 0。
- 说明：修订后的材料还没有真实评分。

**H9　公开 `tests/test_responsetypes.py` 在 base 上同样是 2 败 5 过，求解者看得到，顺手修掉就会判 0**（出处：R06、R09、solver_conditions、public_test_noise 族）
- 判定：**确认**（历史镜像层面实测），另作**细化**。
- 证据：`p4/targeted_public_tests/<iid>/agent_probe.log`。
  - 运行条件：uid 54321，`PWD=/testbed`，派生镜像。
  - 命令见 `p4/tools/targeted/dev_probe_agent.sh:22`：`python -m pytest -q -rfEs … tests/test_responsetypes.py`，没有加 `-W ignore`。
  - 结果：`2 failed, 5 passed`，两例都是 `responsetypes.py:56 TypeError`。
- 细化：
  - 只有显式给出文件路径才看得到这两个失败。`pytest tests` 在 py3 下会经 `collect_ignore` 跳过这个文件（静态推断，依据 `conftest.py:25-29`）。
  - 公开提示写着“keep runs narrow (a single test file or module)”，会把求解者引向显式路径。
  - 求解者是否真会顺手去修，属于清单 34/35，要看真实轨迹。

**H10　公开复现 `REPRO_OBSERVED=1`（传 str 返回 `Response`，传 bytes 抛 `TypeError`）**（出处：R03、R09）
- 判定：**确认**。
- 证据：
  - `p4/dev_probe/<iid>/agent_probe.log:118-125`；
  - 验收时独立重跑结果相同（`_accept/p4/dev_probe/<iid>/agent_probe.log:123`，acceptance ②）。

**H11　解释器与工具（出处：R05）**
- 主张：
  - 解释器 `/testbed/.venv/bin/python` 3.9.21，pytest 8.3.4；
  - 没有 pip / pip3 / uv；
  - `cwd=/tmp` 时也能导入；
  - gcc、make、git 都在。
- 判定：**确认**（镜像层面）。
- 证据：`agent_probe.log:9-28`。
- 说明：`dev_probe.json` 里的 `pip_ok=true` 是工具误判，历史已指出。以原始行 `PIP_VERSION=… No module named pip` 为准。

**H12　Scrapy 1.1.0dev1 与镜像中的 Twisted 24.11 / zope.interface 不兼容，抓取类公开测试恒失败，但本题路径不受影响**（出处：R05、issue 3）
- 判定：**确认**。
- 证据：
  - `targeted2_cmds/<iid>/agent_probe.log:14-17`：`cannot import name 'implements' from 'zope.interface'`；
  - 版本：派生镜像的安装清单 `integrity_derived.txt` 含 `twisted-24.11.0.dist-info`；M3 的 `pth.txt` 含 `zope.interface-7.2`。
- 说明：该日志里的 `C1_RC=0` 被管道 `| tail` 掩盖了，不是真实退出码。应以日志里的 `4 failed` 为准。

**H13　权限：agent 可写 `/testbed`、site-packages、`.venv/bin`、home 和 `/tmp`；私有目录拒绝访问**（出处：R07）
- 判定：**确认**（镜像层面）。
- 证据：`agent_probe.log:33-38`、`:64-66`；派生 facts 中 `hidden_tests_unreadable_as_agent_uid` 为 ok。
- 说明：site-packages 可写会不会影响评分，属于共享机制，本审查没有核对。

**H14　网络：无出网，解题和测试也都不需要网络**（出处：R10、R11）
- 判定：**确认**。
- 证据：`NET_CONNECT_RC=1`、`NET_DNS_RC=2`；账本 policy 为 `deny_all`。
- 说明：正式链使用隔离内网加 relay，这条路径没有验证（E02）。

**H15　资源：峰值 205 MB（限额 4 GiB），setup 14 s，test 1 s；chown 18.14 s**（出处：R12）
- 判定：**确认**。
- 证据：facts.json 的 `rh2_runs`；`root_init.log`。
- 说明：chown 是探针初始化的成本，与题目无关。

**H16　泄漏检查（出处：R17）**
- 主张：
  - 派生镜像 `fix_present=no`，私有目录权限 700；
  - HEAD 没有子提交，也没有 refs、remote、reflog 或补丁残留；
  - install.sh 是通用安装脚本。
- 判定：**在派生镜像上确认；对当前正式链不成立**。
- 证据：
  - 派生 facts 的 `root_facts`：`fix_present` no，refs 0，reflog 0，remotes 0，`private_mode` 700；
  - `image_readout/<iid>.txt` 中 install.sh 全文只有 `uv venv` 和 `uv pip install`。
- 说明：
  - 环境卡 §2：`rollout_spec_from_view` 取 `public.image`，也就是来源镜像。
  - M3 facts 显示来源镜像里：
    - `/r2e_tests` 所有用户可读（`r2e_tests_list.txt`）；
    - `git cat-file -t 9a15fcf8…` 的结果是 commit；
    - master 和远端 1.1…2.x 各分支都包含这个修复（`git_fix.txt`、`git_contains.txt`）。
  - 这属于共享问题，B 线正在改。

**H17　评分只替换 `r2e_tests/{__init__,test_1}.py` 与 `run_tests.sh`，gold 改动的路径与之不相交**（出处：R04）
- 判定：**确认**。
- 证据：gold 和 P4 的 `projection.included_paths` 都是 `[scrapy/responsetypes.py]`；另见日志中的 `RH2_SETUP_EXPECTED_TEST_FILES`。
- 补充（历史没有提到）：根目录有两个文件对 `r2e_tests` 生效，而且评分时不重置。
  - `conftest.py`：含 `chdir` fixture 和 `collect_ignore`；
  - `pytest.ini`：含 `--doctest-modules --assert=plain`，`python_files` 包含 `__init__.py`。

  合法解用不到这两个文件，但候选如果改了它们，会影响评分。这属于共享机制，对应清单 31，未测。

**H18　环境阶段的处置：分类 material；needs_decision → grading_ok_open_items，T0-4 交给题意与评分质量筛查**
- 判定：**确认**（作为环境阶段的记录）。
- 证据：`results_20260924.md:56`、`dispositions.json`、decisions 表中的 T0-4 行。
- 说明：本审查正是 T0-4 的承接环节。

**H19　提案推荐 D**（出处：提案、decisions T0-4、P4 README §2.1）
- 主张：
  - 推荐 D（本轮隔离）。
  - B 的代价是“隐藏测试 + expected 双修订 → 派生镜像私有目录与 pins 要重做”，只为救 1 题。
  - C 要改公共契约，全池只有这一题，不值得。
- 判定：**事实部分确认；成本论据部分过时；推荐不采纳为默认。**
- 证据：
  - E16（09-24 夜）：修订单 v2 已支持对隐藏测试做 `edits`、对期望做 `expected_file_replace`，派生步骤 `material_v2.sh` 已建成。
  - 同仓的 `cfed9b66` 已按这条路径修订并验收：noop 0、gold 1 各 2 次。
  - 当前封板输入已经到 `t1_input_pins_r2e_v4.json`，其中 `material_revisions_v3.json` 不含本题。
  - 所以本题再修订，只需走一遍现成流程：修订单 v4、pins v5、重建一张派生镜像，再验收。
- 说明：
  - 不采纳 D 作默认的理由见 §2。
  - 同意“C 不值得”。
  - “全池只此一题”未核实，见 H21。

**H20　`disposition.reason` 和 `open_items` 里仍写着“R13 待中央复跑并入（记录时 unknown），若复跑与 R-f 不一致则需重判”**
- 判定：**过时**。
- 证据：`checks.R13` 已是 pass，`review_notes` 在 09-23 记录了并入。
- 说明：只是文字没更新，不影响结论。

**H21　“本包其它期望 FAILED 键都翻不动，只有本题会误伤正确解”；T0-4 行写“四包汇总后全池只此一题属可翻转键”**
- 判定：**未核实**（超出本题范围）。
- 说明：
  - 历史自己在 README:132 承认，“死键不会被合法修复翻转”大多只是推断。
  - 其中 scrapy `cfed9b66` 的 3 个键已由 T0-5 修订消失，这句话对它已经过时。
  - 这条只影响“C 是否值得做”，不影响本题。

**H22　source_adapter_ref 为 `s2_r2e ingest_manifest_v0 (pin ea567fec…)`，task_revision 为 `expected_v0`**
- 判定：**引用过时，内容仍对**。
- 证据：
  - 当前封板输入是 `t1_input_pins_r2e_v4.json`；
  - `grading_bundles_r2e_v0.jsonl` 第 45 行的 sha256 前缀 `e7cabb31…`，与静态包 `grading_bundle.json` 的记录相同；
  - 修订单 v3 不含本题。
- 说明：本题的评分面从 v0 起没有变过。

**H23　P4 README §7.5 的筛查规则：traceback 落在库代码里的，可能被翻转，要做 over-fix 实测；落在测试或框架里的，是死键**
- 判定：**对本题确认**。本题两个键的 traceback 都落在 `scrapy/responsetypes.py`，而且确实被翻转了。
- 说明：这条规则是启发式的。“死键”那一侧的判断大多是推断（见 H21）。

**H24　复现脚本写于读取隐藏测试、gold 和日志正文之前（E06 规定的先后顺序）**
- 判定：**未核实**。这是流程陈述，没有可核对的原件。
- 说明：不影响结论。

**H25　venv 里没有 pip，与公开提示“`pip` already points at it”矛盾；另有 conda 措辞问题（E09）**
- 判定：**确认，问题仍未关闭**。
- 证据：公开 `public_bundle.json` 中 `public_hints` 的原文；环境卡 §2。
- 说明：属于共享问题。

## 2. 与封存初判不同或细化的判断，以及理由

1. **只升级证据，结论不变。**
   - 封存初判 §5 把两项写成“静态推断 / actor 待验”：显式路径运行公开测试会“5 过 2 败”，以及 agent 身份下的导入。
   - 这两项现在有了【历史镜像层面实测】（H9、H11）。
   - 正式启动链（来源镜像、Claude Code 非交互 shell、`/rh2/bash_env`）仍然是【actor 待验】。所以清单 8、10 的状态保持 `unknown`，不写成“环境正常”。
2. **细化修订 B 的实施方式**（封存初判原写“按 py3 条件跳过”）。
   - 读 `r2e_parsers.parse_log_pytest` 后发现，parser 按子串判断状态：short summary 某一行只要含有 `PASSED`、`FAILED` 或 `ERROR` 就会成为键。
   - 所以如果用 `unittest.skipIf` 跳过，理由文字里不能出现这三个大写词，否则 `SKIPPED` 行会被解析成键。
   - 更稳妥的做法是直接删除这两个方法，只需 2 处 `edits`。
   - 不建议在 `run_tests.sh` 里加 `--deselect`。这个文件是公开工作树中可见的未跟踪文件，改它会同时改变公开材料和 `RH2_SETUP_ENTRY_SHA256`。
3. **补上修订 B 的长期代价**（封存初判没有写）。
   - 修订后，本题与 M3（来源版材料）就不再是同版本对照。按 E13 / E16 的规则，对账时本题会单独列出，不计入“一致”总数。
   - 清单 22 的独立 runner 证据，从此只剩修订前的来源版。环境卡 §1 给出的替代办法是用一次性容器试跑，逐键对照。
4. **不采纳历史的 D 作默认，理由如下。**
   - (a) 修订已有现成流程，成本明显下降（H19）。
   - (b) 两个键是死键，去掉后有效覆盖不会减少。`content_encoding → Response` 和整条 header 路径，现在本来就没有被测到。
   - (c) 有上游 `py3-ignores` 作依据（H6）。
   - (d) D 会丢掉一道评分确定、目标键清楚的题。
   - D 仍是合理的退路：适用于近期没有合批修订的机会，或者决定不为一道低难度题付重建成本的情况。
   - 这一选择属于训练语义与材料层面的 T0 决定，最终由用户定。
5. **以下封存初判的发现，历史既没有覆盖，也没有反证，维持原判：**
   - K1′ 回归覆盖弱：把 `'application/json'` 改名为 x-json 也能得 1（静态推断，未跑）；
   - 只解码 content_type 的部分修复仍得 1（静态推断）；
   - 题面加上相邻的 `application/json` 表项，几乎直接指出了修法，难度很低；
   - 共享的 actor 条件待验。

## 3. 建议队列（已按历史更新，均未执行）

1. **【决定，T0-4】**
   - 推荐 B：私有 `r2e_tests/test_1.py` 删除 `test_from_headers` 和 `test_from_args` 两个方法，期望同步删这两个键，走 `material_v2`、修订单 v4、pins v5。
   - 退路是 D。
   - 近期诊断用 A′：如果得 0，且不符的恰好是这两个键从 FAILED 变成 PASSED、其余键都匹配，就记为“过度修复误判”。
2. **【CPU，随 B 一起验收】** 在修订后的材料上，下面四个候选各跑 2 次，并核对键集只剩 5 个：

   | 候选 | 预期 |
   | --- | --- |
   | noop | 0 |
   | gold | 1 |
   | P4 over-fix | 1 |
   | 只解码 content_type 的部分修复 | 1 |

   如果选了 D 或 A′，可以只在当前材料上跑一次部分修复（预期 1），用来核实“得分取决于修复的完整度”。
3. **【CPU，低优先级】** 跑 K1′ 反例（把 json 改名为 x-json），预期得 1。要不要补断言，属于扩大测试标准，需要另行决定，不能夹带进 B。
4. **【流程，清单 40】** 给搬迁伪影扫描补一条规则：隐藏测试的原文件在 base 的 `collect_ignore` 或 `py3-ignores` 这类忽略表里。本题就是这种情况；scrapy 1.1.0dev1 时期的其它题可能同型。这条规则只用来标出候选，再逐题归因。对其它题尚未核实。
5. **【actor，共享】** 等正式链改用派生镜像、修好解释器前缀之后，以 agent 身份核对 H9 与 H11。

## 附录 A：本步打开的原件

**核对封存初判（读历史之前）：**
- 私有包全部文件；公开包中的 `user_prompt.txt`、`environment_brief.md`、`public_bundle.json`；
- worktree 中的 `scrapy/responsetypes.py`、`conftest.py`、`pytest.ini`、`.gitignore`，以及 `tests/py3-ignores.txt` 第 35-45 行；
- R-f noop / gold 日志中被引用的行；P4 over-fix 的日志与账本；over-fix diff 的 sha256。

**历史（refs.json 所列）：**
- `tasks/<iid>/{screening_record.json, findings.md, facts.json}`；
- `known_issues.json` 中与本题相关的 9 个族；
- `decisions.md`：E01–E20 与 T0-1…T0-7 的 grep 命中行；
- `results_20260924.md`、`material_revisions/<iid>.md`、`repros/<iid>.py`、`packages/p4/README.md`。

**同一历史目录下另读的部分（只看了与本题相关的 grep 命中）：**
- `README.md:126,132`、`acceptance_20260924.md:42,46`、`static_screening_prep.md:15`、`facts_summary.md:47`、`dispositions.json` 中本题的条目。

**历史引用到的原始证据：**
- `runs/r2e_env_repair_20260924/p4/` 下：
  - `targeted_public_tests/<iid>/agent_probe.log`；
  - `dev_probe/<iid>/{agent_probe.log, root_init.log}`；
  - `targeted2_cmds/<iid>/agent_probe.log`；
  - `image_readout/<iid>.txt`；
  - `tools/targeted/{dev_probe_agent.sh, run_p4_targeted.py, lists/<iid>.txt}`；
  - `offline_rescore_9a15fcf8.json`、`rerun_overfix_1848.log`；
- `_accept/p4/` 的 grep 行；
- `runs/r2e_rf_20260923/reconcile_all/reconcile.json` 的第 44、92 项；
- M3 `facts/9a15fcf89a15/` 下的 `noop_x2/out{1,2}.txt` 状态段、`facts/{git_fix, git_contains, git_fix_files, git_refs, r2e_tests_list, status_porcelain, pth}.txt`；
- 派生镜像的 `facts.json`，以及 `integrity_derived.txt` 中的 dist-info 名单；
- `s2_r2e/t1_input_pins_r2e_v4.json`，修订单 v3（只 grep 本题），`grading_bundles_r2e_v0.jsonl` 第 45 行的哈希。

**生产代码（静态阅读）：**
- `rh2/src/repoharness2/envpack/scoring.py`（sha256 `7c26f6a2…`）中的 `expected_map_matches`；
- `rh2/src/repoharness2/envpack/r2e_parsers.py`（sha256 `339b7c80…`）中的 `parse_log_pytest` 与 `prime_calculate_reward`。
- 两个文件都与 `runs/r2e_snapshot_20260923.sha256` 的记录相同。注意：工作树中 `scoring.py` 显示为已修改、`r2e_parsers.py` 显示为未跟踪，但内容与快照一致。

**未读：**
- `reviewer_initial.md`；本批 `README.md` 与 `assignments.json`；
- `r2e_env_repair_20260924/` 以外的其它审查目录；
- 其它题的逐题记录。
