# coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266 · 复核（第二步）

2026-09-25 · R2E 第二批独立复核。封存初判见同目录 `reviewer_initial.md`，本步没有改它。本步读了：公开读者报告，主审的三份产物和结构化记录，`history/.../refs.json` 所列 8 份历史文件，以及协调者新给的正式评分和语义复核原件。只做阅读和原件核对，没有运行项目代码、容器或远端。读取范围见附录 A。

## 0. 结论

**同意**主审的处置和两项问题：
- 处置：`needs_review`，scope `static_review`，用途 `development_diagnostic`，属于静态候选、待 actor 验证。
- ISS-1：目标测试覆盖不足。
- ISS-2：同族关系与跨题暴露。

主审的决定性主张我逐项核过，引用都支持，证据都对应本题当前材料（见 §2）。

**新执行事实把证据级别升了，处置不变。**
- W1、W2、M、A1 正式评分都是 1（44/44）。
- N1 是 0（16/44），不符的键与主审预测的 28 个逐一相同。
- ISS-1 由"静态推断"升为"当前 CPU 正式评分已确认"（每个候选跑 1 次）。

**修改 5 处**（详见 §3）：
1. ISS-1 的缺口有三条独立的轴，不是两条，三条都已执行确认：
   - `CoverageConfig` 入口（W1）；
   - 设置的值是否真正生效（W2）；
   - 替换还是合并（M）。
2. REV1 按现在的写法关不住 W2；其中"采用上游后来版本写法"那一半也关不住 W1。
3. PASS-AUDIT 的判据"补丁是否改在 CoverageConfig"不够用：W2 和 M 都改在 `CoverageConfig` 里，仍然是错的。应改用已有的语义复核脚本，再加上 `replace_vs_merge` 命令。
4. ISS-2 里"本题初态含 `016af5f6`、`5dbbe143` 的修复"，只用公开包就能在行为层面核实，不再只是机械比对线索或测试辅助层面的证据。
5. 清单 31 的适用范围要补上 `coverage/backunittest.py`。隐藏测试的 `TestCase` 基类来自这个文件，而它是**非测试路径**的源码。

**保留 2 项分歧**（§5）：R4 的定性（替换还是合并）；要不要用 `cov.config.paths` 或 `combine()` 断言来关住 W2。

**唯一优先下一步**：由用户对 R4 定案，并决定是否修订目标测试。
- 修订：先做 §6 的最小沙盒实验。
- 不修订：不需要新的 CPU 实验，直接进 actor 验证；每个通过的补丁都跑语义复核加 `replace_vs_merge`。

## 1. 新执行事实（逐项核对后）

| 候选 | 补丁 sha256 前缀 | 正式评分（当前材料） | 语义复核（root、不联网、不计 reward） | replace_vs_merge |
| --- | --- | --- | --- | --- |
| gold | `0a9c0747` | 1，44/44 | 三项都通过 | 替换：before 是文件里的 `first`，after 只剩 `magic` |
| W1 只改 `control.py` | `51acee3f` | 1，44/44；投影 `included_paths=["coverage/control.py"]` | `config_roundtrip` 失败（`No such option: 'paths'`），另两项通过 | 替换 |
| W2 旁路属性 | `8a2b34e3` | 1，44/44 | `config_paths_updated` 失败（`config.paths={}`）；`combine_remaps` 失败（仍是 `/src/pkg/a.py`） | 未跑；静态推断为替换 |
| A1 复制加 `~` 展开 | `8cd48b49` | 1，44/44 | 三项都通过 | 未跑；静态推断为替换 |
| M 合并 | `b7e1a4d6` | 1，44/44（只有账本行，本地没有日志） | 未跑；静态推断三项都通过 | **合并**：after 是 `first` 加 `magic` |
| N1 加进 `CONFIG_FILE_OPTIONS` | `612d0e7b` | 0，16/44，28 个 FAILED | — | — |

核对要点：
- **补丁**：
  - W1 与我初判的候选 B 逐字相同，都是在 `control.py` 两个方法开头加 `if option_name == "paths"`；M 与我的候选 M 相同。
  - 补丁前像 `f7db26e`、`78a3e86` 正是本题工作树 `control.py`、`config.py` 的 `git hash-object`。
  - 各账本的 `candidate.patch_sha256` 与 `grader_cands/` 下的补丁文件一致。
- **当前材料**：本地 5 份日志的 sha256 与账本 `log.sha256` 一致。日志头部是 `RH2_SETUP_HIDDEN_TESTS_TREE=ddfa078c…`、`RH2_SETUP_ENTRY_SHA256=8285765f…`，与当前材料相同。
- **镜像**：
  - 本批评分镜像是 `59ba6725…`（与 devcheck 相同），`overlay.recipe_sha256=0da821a1…`，`scripts_digest=ecf73086…`。
  - 旧评分账本用的镜像是 `ab9a4d0f…`，配方和脚本摘要都相同。
  - 所以两张镜像是同一配方的两次构建。这关闭了我初判的未知 ③。
- **N1 失败原因**：日志第 86 行 `Couldn't read config file .coveragerc: not enough values to unpack (expected 2, got 1)`，同类报错全文共 28 处。
- **M 的证据缺口**：M 的日志 `evallog_replay-1fc0d65f6ebe-cove_aada0fab.eval.log` 不在本地 `eval_logs/`，得分只有账本行支撑（`log.sha256=503ec135…`）。
- **运行次数**：每个候选只跑 1 次。gold 的正式评分在 `ab9a4d0f` 上 2 次、`59ba6725` 上 1 次，另有 M3 在来源镜像上 2 次，全部 44/44。测试本身是确定性的，单次足够。

## 2. 逐项核主审的决定性主张

| # | 主审主张（出处） | 核对 | 结论 |
| --- | --- | --- | --- |
| C1 | 材料一致；gold 与上游 diff 逐字节相同；上游提交只改了 `config.py` 和 `tests/test_config.py`（analysis §2） | 我初判时核过各哈希；`M3/.../gold/a1/git_gold.diff` 与 `gold.patch` 经 `cmp` 相同；M3 账本第 29 行 `gold_meta.excluded=[["tests/test_config.py","test"]]`。主审写的"M3 gold_meta"实际是账本字段，不是单独文件 | 同意 |
| C2 | 只有一个目标键；noop 在 get 处抛出题面所说的异常（§2、§5b） | R-f noop 日志 20–63 行；rerun2 日志 29–63 行 | 同意 |
| C3 | ISS-1：W1、W2 静态预期得 1（§7；card §4） | 已执行，都是 1；语义复核分别暴露了各自的缺陷 | 同意，证据升为当前 CPU |
| C4 | A1 预期得 1，没有误拒（§7） | 已执行，得 1；语义复核三项都通过 | 同意 |
| C5 | N1 预期得 0，28 个键不符（`screening_record` 的 `suggestion_queue.N1`） | 已执行，不符键集合与预测完全相同 | 同意。这是正确拒绝：读任何配置文件都失败，违反公开旧测试 K1、K4。不是规格争议 |
| C6 | M 可选，属"规格歧义，不作为反例"（§7；card §5） | 已执行，得 1；`replace_vs_merge` 确认它是合并 | 事实同意；定性保留分歧（§5 D1） |
| C7 | H6：默认 addopts 的原命令形式在 agent 身份下可用（old_findings_delta） | 探针以 agent（uid 54321）在镜像 `ab9a4d0f` 上跑 `tests/test_annotate.py`，出现 `bringing up nodes...`，rc 0（`agent_probe.log` 第 2 行与 116–120 行）。命令见 `rh2/scripts/r2e_env/dev_probe_agent.sh:86`：只加了 `-o cache_dir=/tmp/...`，没有清空 addopts | 同意。措辞建议："同一派生镜像"改为"同配方的另一次构建"（当前构建是 `59ba6725`）。本题的 `tests/test_config.py` 仍没有用原命令形式跑过 |
| C8 | H24：与 5dbbe143 的包含关系"测试辅助部分已核实"；与 016af5f6 的只有机械比对 | 见 §3 第 4 条 | 修改：两条都能在公开包的行为层面核实 |
| C9 | ea6906b0 含本题修复和加强版测试；与 f5eb5f21 的公开工作树逐字节相同 | 我初判时独立核过 | 同意 |
| C10 | 清单 3 记 unknown：模型实际收到的消息没有捕获 | devcheck `messages_000.json` 的 user 文本是桩指令，不是题面 | 同意 |
| C11 | 清单 29：system 提示里的 gitStatus 只列到 base | `messages_000.json` 的 system 部分：Recent commits 第一行是 `17204597 One clarification`；Status 只有两个未跟踪文件 | 同意 |
| C12 | 环境结论与历史一致（H1–H23） | 抽查了 H3、H6、H10、H13、H15、H17。H15 的依据 `RH2_OBS_IMPORT_PATH=/testbed/coverage/__init__.py` 在旧 R-f 账本和新 W1 账本里都有 | 同意 |
| C13 | H14："site-packages 可写只在旧探针里见过，正式链没测" | devcheck `post_run_facts_root.txt:24-26` 列出 agent 会话后在 `/testbed/.venv/lib/python3.7/site-packages/py/_io/__pycache__/` 新出现的 pyc。由此推断 agent 在正式链上写过 site-packages（文件属主没记录） | 小更正。与评分无关：`.venv` 不出现在 `git status` 里，投影只带源码文件 |

## 3. 反查：主审没覆盖到的范围

1. **REV1 关不住 W2；REV1 的"上游写法"那一半也关不住 W1。**
   - REV1 分两部分：(i) 在目标测试里对 `cov.config` 做 get/set 往返；(ii) 改用上游后来版本的写法，从非空的 `[paths]` 起步（`ea6906b0` 工作树 `tests/test_config.py:339-360`）。
   - **W1 能通过 (ii)**：`replace_vs_merge` 实测，W1 从非空起点 get 到的是文件里的值，set 之后只剩 `magic`，正好满足上游后来的断言。所以只有 (i) 能拦住 W1。
   - **W2 能通过 (i) 和 (ii)**：
     - (i)：语义复核里 W2 的 `config_roundtrip` 通过。
     - (ii)：W2 的 get 是 `getattr(self, "_paths_override", self.paths)`，set 之前返回文件里的值，set 之后返回新值。这一条是静态推断，W2 没跑 `replace_vs_merge`。
   - **M 只会被 (ii) 拦住。**
   - **要关住 W2**，set 之后需要再加一条断言，二选一：
     - `cov.config.paths == new_paths`：更轻。同一文件的回归键已经在断言 `cov.config.paths`（`test_1.py:297`、`559-562`），不引入新的耦合。
     - 断言 `combine()` 用上了新值：更贴近行为。公开依据是 `control.py:388-395`（set_option "has the same effect as this configuration file"），加上 `doc/config.rst:223-235`（`[paths]` 用于 combine）。
   - 主审写的是"不建议强制加 combine() 断言，除非另有公开依据"。我认为可推知级别的公开依据是存在的，见 §5 D2。
   - 不论选哪种，都要先用 A1 验证不会误拒合理解。
2. **PASS-AUDIT 的判据不够用。**
   - `screening_record` 的 `conditions` 与 `PASS-AUDIT` 写的是"检查补丁是否改在 CoverageConfig，排除 W1 型"。但 W2 和 M 都改在 `CoverageConfig` 里，仍然是错的。
   - 建议改为：对每个通过的补丁跑下面两项。
     - `rh2/experiments/r2e_actor_20260925/postcheck/coveragepy_97997d2c_paths.py`：`config_roundtrip` 拦 W1，`combine_remaps` 拦 W2。`config_paths_updated` 与实现方式耦合，只作诊断用。
     - `grader_cands/coveragepy_9799_extra_commands.json` 里的 `replace_vs_merge`：拦 M。
   - 两项缺一不可：M 在三项语义复核里都会通过。这是静态推断：`CoverageConfig()` 和 `Coverage(config_file=False)` 的起点都是空的 `OrderedDict`，合并和替换结果相同。
3. **清单 31 要补一个非测试路径的评分依赖。**
   - 隐藏测试通过 `tests/coveragetest.py:26` 的 `from coverage.backunittest import TestCase, unittest` 继承 `TestCase`，而 `coverage/backunittest.py` 是源码文件。
   - 公开提示"不要改测试文件"管不到它。按路径名推断，账本的 `candidate_test_like_paths` 也不会标记它（平台规则未核）。
   - 蓄意修改它可以改变断言行为；正常修复不会碰它。只记适用，风险低。
4. **ISS-2 的两条"本题初态含别题修复"，只用公开包就能核实。**
   - `5dbbe143` 的题面是"`_warn()` 不认 `once` 参数"：
     - 本题工作树 `coverage/control.py:337` 是 `def _warn(self, msg, slug=None, once=False)`；
     - `5dbbe143` 的工作树 `control.py:336` 是 `def _warn(self, msg, slug=None)`。
   - `016af5f6` 的题面是"非 UTF-8 文件名在保存时报 `UnicodeEncodeError`"：
     - 本题工作树 `coverage/inorout.py:336-340` 对不能编码的文件名返回 `"non-encodable filename"`，不再追踪它；`CHANGES.rst:105-108` 把这一改动记为 issue 891。
     - `016af5f6` 工作树的 `coverage/*.py` 里没有这段处理。
   - 结论：两条都升为"公开包行为层面已核实"；我仍然没读它们的私有 gold。本题的公开工作树（以及初态相同的 `f5eb5f21`）实质上带着这两题的答案，所以同族划分是硬约束。
5. **题面唯一的内部不一致不构成规格争议。**
   - 题面 Actual Behavior 说异常在 set 时抛出。
   - 只修 `set_option` 的候选会在目标键第 346 行的 get 处失败，得 0。
   - 但 Expected Behavior 明确要求 get 也能取回，而且示例一运行就在 get 处报错。所以这个 0 有公开依据，不需要实跑。

## 4. 事后认定、修订范围与可探针检查

- **不是先看答案再把隐藏要求说成"显然"**：
  - ISS-1 用到的四条要求——替换语义、插件可能拿到 `CoverageConfig`、设置值要在 combine 中生效、能取回配置文件里的值——公开读者报告已经独立列出（`public_read.md:16-19` 的 R4–R7）。第 44 行还点名了 W1 型实现。这些都早于任何私有材料。
  - 主审对 R4 的定性（规格歧义）比公开读者（明示倾向）更弱，方向与事后拔高相反。
- **措辞建议**：card §1 把"两种对象都要能用"写成了题目本身。但题面从没提到 `CoverageConfig`，这一条是读 `control.py:276` 推出来的，公开读者标的是"可推知"。建议 card 注明"由公开代码推知"。
- **修订是否扩大需求**：
  - **REV1(i)**：依据是题面的插件动机、`plugin.py:213-216` 和 `control.py:276`。它属于"查代码就能知道"，不是"只有读隐藏材料才知道"，所以不算扩大需求。但它把门槛从"明示"提到了"可推知"，修订说明里应写明。
  - **REV1(ii)**：
    - 从非空起点取回文件里的值，有明示依据：题面第 27 行 "retrieve the current paths configuration"。
    - 强制替换语义则要先对 R4 定案。主审自己把 R4 定为"规格歧义"；按这个定性，REV1(ii) 会误拒合并读法，前后矛盾。我倾向替换（§5 D1），但必须由用户先定 R4。
    - 上游后来的测试只能当写法模板，要求的依据仍须来自本题公开材料。主审就是这样引用的。
- **可探针检查**：
  - `screening_record` 的 `disposition` 把静态候选（`static_probe_candidate: true`，`needs_review`）和剩余条件（`open_items` 里的 cpu_counterexample、actor_unverified、optional_revision_pending_user）分开写了。
  - 也没有把环境已验当成质量合格：old_findings_delta 的 H1 明说 `env_ok` 不等于题目质量合格。
  - 主审也不只是在核对旧结论：新增了 ISS-1、ISS-2 和 W1、W2、A1、N1 等候选。
- **建议协调者收口时更新的字段**：
  - `open_items.cpu_counterexample`：改为已完成，附 §1 的结果。
  - 清单 25：证据改为当前 CPU。
  - 清单 24：注明 A1 已实跑得 1。
  - 清单 5：改为公开包行为层面已核实。
  - 清单 31：补 `coverage/backunittest.py`。
  - `PASS-AUDIT` 与 `conditions`：按 §3 第 2 条更新。
  - `next_step`：改为 §0 的唯一优先下一步。

## 5. 未解决的分歧（显式保留）

- **D1：R4 是替换还是合并**
  - 主审：规格歧义，M 不算反例（analysis §4、§7；card §2）。
  - 我：倾向替换，M 是偏离。依据有四条：
    - 题面第 23 行的注释 "Expected to output the new_paths OrderedDict"；
    - `control.py:388-395` 说 set_option 与写配置文件效果相同；
    - 其它所有选项的 set 都是 `setattr` 整体替换（`config.py:426-430`）；
    - 公开读者独立判为"明示倾向"（`public_read.md:16`）。
  - 反方依据：题面第 27 行的 "containing the new paths" 按合并理解也说得通；示例从空起点开始，区分不出两者。
  - 事实部分已没有争议：M 得 1，行为是合并（`cov9799_rvm_coveragepy_9799_M_merge_paths.json`）。
  - 收敛方式：由用户对 R4 定案。定案之前，不应采用 REV1(ii)。
- **D2：是否需要 `cov.config.paths` 或 `combine()` 断言来关住 W2**
  - 主审：除非另有公开依据，不建议强制 `combine()` 断言。
  - 我：可推知级别的公开依据存在（§3 第 1 条），而且 `cov.config.paths` 断言已是同一文件的既有做法。但 W2 是人为构造的旁路存储，自然出现的可能性比 W1 低，优先级也更低。
  - 收敛方式：由用户决定是否修订；如果修订，先用 A1 验证不误拒。

**原始 reward 全部保留**：
- W1、W2、M 的 1 和 N1 的 0 都按实测记录。
- W1、W2、M 暴露的缺口记在 ISS-1 与 PASS-AUDIT，不回头改它们的得分。
- 没有任何候选因可能属于规格争议的原因得 0；N1 的 0 是正确拒绝。

## 6. 最小后续实验

**只有用户决定修订时才做。** 先写一版修订后的目标测试 T'，内容包括：
- REV1(i)：对 `cov.config` 做 get/set 往返；
- 从非空起点取回配置文件里的值；
- set 之后断言 `cov.config.paths == new_paths`；
- 替换断言要不要保留，按 D1 的定案决定。

然后在一次性沙盒里对下列候选各跑一次：

| 候选 | 预期结果 | 若不符，说明什么 |
| --- | --- | --- |
| noop | 0，只错 T' | — |
| gold | 1 | — |
| A1 | 1 | 新断言误拒了合理解 |
| W1 | 0 | T' 没拦住 W1 |
| W2 | 0 | T' 没拦住 W2 |
| M | 保留替换断言时为 0，否则为 1 | — |

**不修订**：不需要新的 CPU 实验。到 actor 阶段，对每个通过的补丁跑 §3 第 2 条的语义复核加 `replace_vs_merge`。

**可选的证据补全（价值低）**：把 M 的评分日志取回本地。

## 附录 A：读取范围

- **OUTPUT_DIR**：`public_read.md`、`analysis_before_history.md`、`old_findings_delta.md`、`card.md`、`screening_record.json` 全文；自己的 `reviewer_initial.md`（没改）。
- **历史**：`history/.../refs.json` 所列 8 份文件：
  - 全文：旧 `screening_record.json`、`findings.md`、`facts.json`、复现脚本。
  - `known_issues.json`：与本题相关或被引用的族，包括 `no_pip_in_venv`、`conda_wording…`、`expected_provenance_mixed`、`hidden_test_relocation_artifacts`、`support_stale_helper:coveragepy_5dbbe143`、`prompt_quality_candidates`、`public_test_noise`、`expected_key_flippable_by_legit_fix`。
  - `decisions.md`：E06、E09、E18 三行。
  - `results_20260924.md`、P1 README：涉及本题的行。
- **为核对主审引用另外读的**：
  - `runs/r2e_env_repair_20260924/p1/dev_probe/coveragepy__97997d2c…/agent_probe.log`（部分）和 `dev_probe.json`（元数据）；
  - `rh2/scripts/r2e_env/dev_probe_agent.sh:78-92`；
  - M3 的 `gold/a1/git_gold.diff`（与 gold 做 `cmp`），以及 M3 账本第 29 行的 `gold_meta`；
  - 旧 R-f gold 账本第 8 行的 `RH2_OBS_IMPORT_PATH`。
- **新执行证据**：
  - `runs/r2e_actor_20260925/grader/` 下：6 份 `ledger_cov9799_*.jsonl`、5 份本地 eval log、6 份 `stdout_cov9799_*.log`、`b2_post_cov9799.sh`、`postcheck_b2/cov9799_*.json`（5 份）、`private_public_b2/cov9799_rvm_*.json`（3 份）；
  - `grader_cands/coveragepy_9799_*.patch`（5 份）和 `coveragepy_9799_extra_commands.json`；
  - `rh2/experiments/r2e_actor_20260925/postcheck/coveragepy_97997d2c_paths.py`。
- **同仓公开包**：
  - `5dbbe143`、`016af5f6` 的 `public_bundle.json` 题面，以及对其工作树 `control.py`、`coveragetest.py`、`coverage/*.py` 的 grep；
  - 本题工作树的 `inorout.py:330-342`、`CHANGES.rst:100-112`、`doc/config.rst:216-250`、`control.py:377-400`。
- **devcheck**：`stub/requests/messages_000.json` 的 system gitStatus 段和工具名。
- **没有读**：批次目录的 README、`assignments.json`、`grader_candidates.md`；首批审查目录和 Codex 复核目录；其它题的私有包；`runs/` 下的汇总文件（`reconcile.json`、`provenance/`、`scan/`）。
- **本地操作**：只读文件，以及 `git hash-object`、`cmp`、`shasum`。没有运行项目代码、容器或远端，也没有修改任何原件。

## 附录 B：关键证据定位

- **正式评分（当前材料，镜像 `59ba6725`）**：
  - 账本：`runs/r2e_actor_20260925/grader/ledger_cov9799_{gold,W1_control_layer_only,W2_side_attribute,A1_copy_and_expand,M_merge_paths,N1_config_file_option}.jsonl:1`。
  - 日志：`eval_logs/evallog_replay-{c798b9d25693-cove_a533baa9,c0790758af70-cove_28fea453,b0d4887b173f-cove_f336f4bf,eda7c4ac73ea-cove_be249d4b,f0c4b514a04d-cove_bce03e28}.eval.log`，依次对应 gold、W1、W2、A1、N1。M 的 `1fc0d65f6ebe-cove_aada0fab` 不在本地。
- **语义复核**：`postcheck_b2/cov9799_{base,gold,W1_control_layer_only,W2_side_attribute,A1_copy_and_expand}.json`。
- **替换还是合并**：`private_public_b2/cov9799_rvm_{coveragepy__97997d2cd6801d0335e3fa162b71,coveragepy_9799_W1_control_layer_only,coveragepy_9799_M_merge_paths}.json`，依次对应 gold、W1、M。
- **旧探针（agent 身份、默认 addopts）**：`runs/r2e_env_repair_20260924/p1/dev_probe/coveragepy__97997d2c…/agent_probe.log:2,116-123`。
- **公开依据**：
  - 替换与生效语义：`control.py:388-395`、`doc/config.rst:223-235`、`config.py:426-430`；
  - 插件拿到的对象：`control.py:276`、`plugin.py:213-216`；
  - 回归键已在断言 `cov.config.paths`：隐藏测试 `test_1.py:297`、`559-562`（同样出现在公开 `tests/test_config.py`）。
