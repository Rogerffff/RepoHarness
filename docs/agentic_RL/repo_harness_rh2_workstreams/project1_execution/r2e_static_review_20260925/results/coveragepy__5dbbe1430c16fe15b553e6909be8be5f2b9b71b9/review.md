# coveragepy__5dbbe143 独立复核：第二步复核（review）

2026-09-25 · 独立复核者（Claude）。第一步初判 `reviewer_initial.md` 已封存，本步没有改动。

本步只做静态阅读和文本核对：`cmp`、`diff`、`grep`、JSON 解析，以及只读的 `git status` / `git diff --stat`。没有运行项目代码或容器，没有改任何原件。

路径均相对仓库根，缩写沿用初判：`PRIV` 是本题私有包，`PUB` 是公开包，`WT` 是 `PUB/worktree`。

## 0. 结论

### 同意主结论 `needs_review`

问题是题意与测试不一致：题面没说按什么判定"重复"，隐藏测试却要求按 slug 去重。

- 三份互相独立的阅读都得出了同一个问题：
  - 我的封存初判；
  - 公开读者，在隔离条件下判为"无法裁决"（`public_read.md:24-27`）；
  - 主审的封存初判。
- 本步核实的来源原文说明，这是题面生成时的缺陷：生成器的输入里既有 gold 的 docstring "(determined by the slug.)"，也有决定性断言 `assertNotIn("Warning, warning 2!", err)`，生成出的题面两者都没有写进去（§1 C7）。
- 我初判的处置写的是"可作开发诊断的静态候选，附条件"，现在改为同意 `needs_review`。两种写法本来都要求先处理这个歧义，`needs_review` 的记录口径更准确。

### 同意关闭 R04、不修订；同意不照搬 datalad 的 B1

- **R04**：环境阶段留下的未完成项，指隐藏测试依赖修复前版本的测试辅助 `tests/coveragetest.py`。
- **B1**：datalad `58ba5165` 的修订方式，把隐藏测试的导入改成一行 `from .test_2 import …`。

我已静态核实：照搬 B1 会让 `TESTS_DIR` 指向 `r2e_tests/`，gold 下约 31 个键会失败。

有一处修改。delta 与 card 写的是"若要修，不要改导入路径，改用评分前恢复修复后的 `tests/coveragetest.py`"，这说得过满：

- 还有一种窄改法：只从 `.test_2` 导入 `CoverageTest`，`TESTS_DIR` 和 `UsingModulesMixin` 仍从 `tests.coveragetest` 导入。它在静态上可行，也能用现有的 `hidden_test_text_replace` 修订种类实现。
- "评分前恢复仓库测试文件"要改评分契约，是共享机制，成本更高。
- 两种修法都会失去旧假函数对 `control.py:697` 越界改法的"碰巧拦截"，所以我仍建议不修（§2.2）。

### 补充三项主审没覆盖的范围（§3）

1. 公开规格修订后"用 CE1、CE3 复验"是空转：评分根本不读题面，结果不可能变。
2. 现有的材料修订机制（v3）没有"改题面"这一种类。公开规格修订需要新的修订类别、pins 升级，公开面的摘要也会变。T0 决定应带上这项成本，并把"隔离本题"列为第三个选项。
3. 本题暴露了一类可以批量筛查的生成缺陷：noop 在目标测试的第一次调用就抛异常，走不到决定性断言；这时生成器只描述异常，后面断言的语义容易丢。

### 保留的分歧（§5）

两处，都不改变处置：

- R04 的后备修法里，窄改导入是否应与"评分前恢复"同列；
- "按消息去重是最字面读法"这一措辞。

### 最小后续实验

在派生镜像上用 RH2 回放评分，跑下面三个候选：

| 候选 | 做法 | 预期得分 |
| --- | --- | --- |
| CE1 | 按消息去重 | 0 |
| CE3 | 按 slug 去重的另一种实现 | 1 |
| CE4 | 全局 once：第一次 once 之后压掉所有 once 警告 | 1 |

公开规格修订如果获批，只需核对渲染结果，评分不用重跑。

## 1. 主审决定性主张逐项核对

| # | 主张（出处） | 我的核对 | 证据是否对应当前材料、用户与环境 | 结论 |
| --- | --- | --- | --- | --- |
| C1 | 当前材料下 noop 跑 2 次，都只错目标键，原因就是题面写的 TypeError（analysis A1；delta H2） | 初判已读两份日志的第 30、32 行。本步另读 M3 的两份 noop 输出（`runs/env_overnight_20260916/M3/facts/5dbbe1430c16/noop_x2/out{1,2}.txt` 第 16、7861 行），也是 TypeError，汇总为 `1 failed, 74 passed` | 当前材料的两次运行都在派生镜像 `81bf06a0…` 上、以评分用户 54322 跑。M3 是来源镜像上的独立 runner，主审只把它当参考，没有混用 | 同意 |
| C2 | gold 当前 2 次都是 75/75，M3 的 2 次也是（A1、A2） | 初判已核 | 同上 | 同意 |
| C3 | gold 与来源镜像里的 `git diff HEAD 5dbbe143 -- coverage/control.py` 逐字节相同（delta H1） | `cmp …/gold/a1/git_gold.diff PRIV/gold.patch` 结果相同。M3 自建的 `gold.diff` 与 `gold.patch` 的差别在于：hunk 头没有函数名，docstring 结尾的 `"""` 写成了先删后加（见 `diff` 输出）。这解释了 `gold_matches_git_diff_changed_lines=false` | "两份 diff 应用后得到同一个 blob `4358a541`"这一步我没有重做。但 `git_gold.diff` 与 `gold.patch` 逐字节相同，已足以支撑"gold 就是上游提交对非测试文件的改动" | 同意 |
| C4 | 决定性断言要求按 slug 或更粗的键去重（analysis R3/R4） | `PRIV/hidden_tests/test_1.py:549`；两份 gold 日志中该测试捕获的 stderr 只有 warning 1 | 当前材料 | 同意 |
| C5 | CE1（按消息）、CE2（按消息加 slug）判 0；CE4 判 1（analysis §3） | 与我初判的反例 A、A'、C 结论相同 | 静态推断，未执行，记录里已标明 | 同意，证据级别标得对 |
| C6 | 公开读者隔离阅读后判"无法裁决"（analysis §0） | `public_read.md:24-27` 原文如此。公开读者还指出：在题面示例上，"按消息去重"与"只接受参数、不去重"的输出一模一样 | 公开读者只读了公开包（`public_read.md:130-155`） | 同意 |
| C7 | 来源生成器的输入里有 "(determined by the slug.)"，生成出的题面漏掉了（delta H4） | 原始行 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/raw/r2e_gym_subset_48_e8b9fcbc.jsonl` 第 24 行的 `prompt` 字段：<br>① diff 里有 `If \`once\` is true, only show this warning once (determined by the` / `slug.)`。这句跨两行，所以按整句检索会漏；<br>② 同一 prompt 里还有完整的 `test_warn_once`，包括 `assertNotIn("Warning, warning 2!", err)`；<br>③ 生成指令写着 "Do not reveal the solution… Only describe the bug and the expected behavior" 和 "For errors, describe the error message"；<br>④ 生成器看到的修复前失败只有那个 TypeError | 来源原文，与本题对应 | 同意，并补一点：生成器同时拿到了决定性断言，所以漏写的不只是 docstring，而是断言所表达的语义（§3 N3） |
| C8 | R04 的事实成立；影响只限"给现有调用点加 once"的越界改法；旧假函数碰巧拦住了 `control.py:697` 上的有害改法（delta H5、I4） | 逐条读过：<br>• `test_2.py:267-269`：修复后的假函数接受 `once`，但注释写明"不实现"；<br>• `test_1.py:371-384` 及 `:380` 的注释（有新活动后应再次警告）；<br>• 5 个用到 `assert_warnings` 的键。<br>推理成立 | 静态推断 | 同意。影响面比"加 `once=True`"稍宽：任何把 `once` 关键字传到 `_warn` 回调的改动（包括包装层显式传 `once=False`），只要落在这 5 个键的 `assert_warnings` 块里，都会抛 TypeError。但这仍在题面要求之外 |
| C9 | 照 datalad B1 改导入，会让依赖 `tests/modules` 的键失效（delta H5；card §4.4） | datalad 的 B1 确实是"隐藏测试一行改为 `from .test_2 import …`"（`…/r2e_env_repair_20260924/decisions.md` 的 T0-2 行）。本题：<br>• `test_2.py:38` 定义 `TESTS_DIR = os.path.dirname(__file__)`，只在 `UsingModulesMixin`（`:490-491`）里用到；<br>• `test_1.py:24` 导入 `TESTS_DIR`，`:880` 直接用它 chdir。<br>按 B1 一行改后，gold 下以下约 31 个键会因 `import usepkgs` / `import namespace_420` 失败：`NamespaceModuleTest` 2 个、`SourceIncludeOmitTest` 13 个（除 `test_source_include_exclusive` 外全部）、`ReportIncludeOmitTest` 8 个、`XmlIncludeOmitTest` 8 个 | 静态推断。前提是镜像 ENV 没有另外把 `tests/modules` 放进 `PYTHONPATH`（未见证据） | 同意"不照搬"；对"不要改导入路径"的修改见 §2.2 |
| C10 | 同批另外 4 题与本题同族（analysis §7；delta §2.3） | 在这 4 题公开的 `coverage/control.py` 里 grep：016af5f6、97997d2c、f5eb5f21 在第 206、337、342、589 行，ea6906b0 在第 214、355、360、620 行，都有 gold 版的 `_warn`、它的 docstring，以及 `dynamic-conflict` 那条 `once=True` 调用 | 公开 worktree | 同意。这也证实了我初判里凭记忆写下、当时未核的一项 |
| C11 | 开发条件已在镜像层面实测（delta H6、H10） | `agent_probe.log` 第 14、22、26-28、116-125 行：<br>• `WHICH_pytest=/testbed/.venv/bin/pytest`，pytest 4.6.6；<br>• 从 `/tmp` 也能导入 coverage；pip 19.3.1；<br>• `tests/test_annotate.py` 在默认 addopts 下 rc 0（输出 `bringing up nodes...`）；<br>• 示例复现出 TypeError | 这是用 `docker exec` 进派生镜像跑的探针，不是正式 actor。主审标为"镜像层面"，并注明 `-k warn` 没跑，口径正确 | 同意 |
| C12 | 正式 actor 仍取来源镜像；工作树里已有改走派生镜像的未提交实现（delta H16；I6） | `git status`：`prepared_task_face.py` 为 ` M`（+155/−11 行），`ingest_r2e_subset.py` 为 `??`。`prepared_task_face.py:412-451` 的逻辑：R2E 题如果没有覆盖条目，就拒绝回退到来源镜像；激活脚本和解释器前缀改用 `.venv` | 代码事实。未提交、未审查、未验证 | 同意"actor 待验"。这段代码我没有审 |
| C13 | R-f 的 `prompts.jsonl` 中本题 prompt 与 `user_prompt.txt` 逐字节相同（delta H3） | JSON 解析后比对：都是 850 字节，内容相同 | 只证明静态渲染与 R-f 的准备产物一致，不是正式 actor 收到的完整消息；主审已说明这一点 | 同意 |
| C14 | 期望的三方来源一致（E=H=I，delta H21） | `runs/r2e_t0_batch2_20260924/provenance/expected_provenance.md:3` 的 41 题名单里有 coveragepy `5dbbe143` | — | 同意 |
| C15 | gold 有三处副作用：G1 快照 `disable_warnings`；G2 once 与非 once 共用抑制列表；G3 `slug=None` 也被记入列表（analysis §4） | 与我初判的两处附注一致；G2 我初判没单独列出，同意补上 | 静态推断 | 同意 |

## 2. 两个重点

### 2.1 `needs_review` 是否成立

成立。依据按强度从高到低：

1. **测试与题面对不上**：决定性断言 `test_1.py:549` 要求 slug 相同、消息不同的第二条警告也被压住；题面 `user_prompt.txt:17-18` 只写了 "displayed only once each, preventing duplicate warnings"。
2. **三份独立阅读都把它列为首要问题**：我的初判（封存于读主审产物之前）、公开读者（隔离阅读，判"无法裁决"）、主审的封存初判。
   - 接续会话在读历史之前没有自己的独立判断（见 card 头注），它的"处置不变"是继承前稿。
   - 我已按原件逐条复核它新增的主张（§1），没有发现因锚定前稿而产生的错误。
3. **来源原文显示这是生成缺陷**：生成器拿到了 docstring 和决定性断言，最后却只把 TypeError 写成了问题（C7）。

我初判给的风险是"中"，主审写的是"静态推断，高确定"，两者说的不是一件事：

- CE1 判 0 这件事几乎是确定的；
- 真实解题者有多大比例会选按消息去重，仍然未知。

两边都把后者列为最关键的未知项。

**处置口径**：state 为 `needs_review`，reason 为"题意/测试争议"，符合记录模板对两类 reason 的区分。静态候选与剩余条件也分开了：

- card 写明去重键问题解决之前，本题不作为基座探针候选；
- 修订后才转为"静态候选待 actor 验证"（analysis §9）；
- 剩余条件单列：正式链（I6）、提示措辞（E09）、共享机制（I5）。

### 2.2 关闭 R04、不照搬 datalad

同意"不修订、关闭 `support_pending_decision`，作为已知低风险保留说明"。在 C8、C9 之外，再补一个权衡。下表对比各做法对两类越界改动的判分：

| 做法 | 越界但无害的改动（如给 `inorout.py:343` 加 once） | 越界且有害的改动（给 `control.py:697` 加 once，违反 `test_1.py:380`） | 成本 |
| --- | --- | --- | --- |
| 不修（现状） | 判 0：误拒，但属题面之外 | 判 0：旧假函数抛 TypeError，碰巧拦住 | 无 |
| 照搬 datalad 的一行 B1 | 不可用：约 31 个键在 gold 下也会失败 | — | — |
| 窄改导入：只从 `.test_2` 取 `CoverageTest`（及 `CoverageTestMethodsMixin`），`TESTS_DIR`、`UsingModulesMixin` 仍从 `tests.coveragetest` 取 | 判 1 | 判 1：新假函数不实现 once，会放过 | 一条现有种类的修订（`hidden_test_text_replace`）＋重建派生镜像＋复跑。静态可行，未验证 |
| 评分前恢复修复后的 `tests/coveragetest.py` | 判 1 | 判 1 | 新增评分机制，改评分契约（共享 T0），还会覆盖候选对该文件的改动 |

两种可行的修法，都是拿"放过有害的越界改动"去换"不再误拒无害的越界改动"。而这两类改动都在题面要求之外，所以不修是合理的默认选择。

**我与 delta/card 的分歧只在后备方案上**。它们写"不要改导入，改用评分前恢复"；我认为窄改导入更轻，而且在现有修订机制之内。如果以后确实要修，这两种做法应当并列，由用户选择。

**还有一个耦合要留意**：I5 的一种处理方式是"评分时把被隐藏测试导入的仓库测试模块恢复为 base 版或修复后版本"。对本题来说：

- 恢复 base 版，等于维持 R04 的现状；
- 恢复修复后版本，等于上表第四行。

I5 作决定时应顺带写明本题取哪一版，否则可能在不经意间改变 R04 的结论。

## 3. 反查：主审没覆盖的范围

### N1 修订后的 CE 复验是空转

analysis §8-2 与 delta §3-2 都写"修订后用 CE1（仍判 0）和 CE3（应判 1）复验"。但 R2E 评分只用隐藏测试、期望和 `run_tests.sh`，题面不进入评分，所以纯公开规格修订前后，CE1、CE3 的得分不可能改变。

修订后真正需要核的是两件事：

- 渲染出来的 prompt（`prompts.jsonl` 或正式链消息）确实含有新句子；
- 可选：做少量盲解，看解题者选择的去重键有没有变化（清单 33–36）。

只有同时改了测试（例如 I2 的可选断言）时，才需要复跑 gold、noop、CE3、CE4。

### N2 现有修订机制改不了题面

`docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v3.json` 里的 20 条修订只有四种：`expected_text_replace`、`expected_file_replace`、`hidden_test_file_add`、`hidden_test_text_replace`。目标都是期望、隐藏测试和夹具，没有 `problem_statement`。decisions.md 的 E24 也记录"公开面、验证面 48 题逐字节不变"。

所以公开规格修订需要：新增一种修订类别、升级 pins，而且公开包的 `line_sha256` 与 `problem_statement_sha256` 都会变。

建议 T0 决定包把三个选项写全：

| 选项 | 内容 | 代价 |
| --- | --- | --- |
| A | 公开规格修订 | 语义上最好；要新增修订类别，并实施与验证 |
| B | 不修，留在开发诊断池 | `test_warn_once` 因按消息去重而失败的样本，要标为规格歧义；这需要逐个看候选补丁，不能只看 reward |
| C | 从探针和评测集隔离本题 | 成本最低；少一道简单题 |

用于训练时，B 会带来奖励噪声，应在 A 与 C 之间选。不要因为现有机制只支持改测试，就转去放宽测试（analysis 已不推荐这条路，我同意）。

### N3 一类可以批量筛查的生成缺陷

本题 noop 在 `test_1.py:545`（第一次调用）就抛了异常，决定性断言 `:549` 在修复前从来没有执行过。生成器被要求 "For errors, describe the error message" 和 "Do not reveal the solution"，于是只写了 TypeError，期望行为一句带过。

"新增参数 / 新方法"这类题，noop 很可能都在调用处就失败，后续断言的语义同样可能没写进题面。

建议协调者对全池做一次成本很低的筛查：

1. 从当前 noop 日志取出目标键的失败行号；
2. 与该测试体最后一个断言的行号比较；
3. 失败点更早的题，再人工核对题面有没有写到后续断言的要求。

这只是建议，我没有做这次筛查。

### N4 I5 的绕过面比记录写的宽

除了 `tests/coveragetest.py` 和 `tests/helpers.py`，评分时 pytest 还会加载：

- `/testbed` 根目录的 `conftest.py`（它是 `r2e_tests/` 的父目录）；
- `setup.cfg` 里的 addopts（可以用 `-p` 加载仓库里的插件模块）。

这两处都不在 `r2e_tests/` 下，评分时不会被清除。它们会不会被补丁投影排除或标记，以共享机制的现有记录为准（账本里有 `candidate_touched_conftest_or_fixture` 字段），我没有核。

这些都属于共享机制问题，按 I5 交共享机制负责人处理，不按单题修。以上是静态推断，未实跑。

### N5 题面补句的另一种写法

如果选 A，除了 analysis 给的规则句，也可以按 R2E 题面的惯例直接写出示例的期望输出，例如：

> In the example above, only `Warning, warning 1!` should be displayed.

两种写法信息量相同；后者更像 issue 里描述"期望输出"的写法，不写实现规则。

两者都只是澄清原需求，没有扩大需求：gold 的 docstring 和提交说明 "Warnings can be marked to only display once." 都是原提交自带的意图，不是为了保住 gold 而放宽标准。

### N6 记录里的小更正（不影响处置）

- **card §1 写"gold 只改一个函数"**：实际改了两处，一是 `__init__` 里加 `_no_warn_slugs = None`，二是 `_warn`（来源行 `num_non_test_lines=15`）。
- **card §4.1 把"gold 在真实 RH2 运行中的 stderr"列为争议的一层证据**：这只能证明测试要求第二条不显示、gold 满足了要求，不能证明误拒。误拒仍是静态推断，要靠执行 CE1 才能坐实。
- **下一步的候选列表前后不一**：delta §3 列的是 CE1–CE4；card 和 `screening_record.json` 的 `next_step` 列的是 CE1、CE3、CE4；I1 的 `proposed_action` 又是 CE1–CE4。建议统一。CE2 与 CE1 同类，可选。
- **delta §2.2 说初判的"测试段时长写错了"**：3.4–4.4 s 接近账本的 `phases.test`（3.68–4.39 s）；3.40–4.03 s 是 `install.test_seconds`，也就是日志时间戳之差。这是两种口径，不算写错。
- **`screening_record.json` check 22 说"两份 diff 应用后得到同一个 blob"**：这一步我没有独立重做。`git_gold.diff` 与 `gold.patch` 逐字节相同，已用 `cmp` 核实。

## 4. 过程检查

- **是否先看了答案，再把隐藏要求说成"显然"**：没有。
  - analysis §2 的 R4 同时列出了支持和反对"按 slug"的公开线索，结论是"歧义"。
  - delta 用来源 prompt 说明缺陷从哪里来，没有拿它证明"公开材料已经足够"。
- **公开读者的疑义能否从公开材料合理消除**：不能完全消除，两边的线索都真实存在。
  - 支持按 slug：`_warn` 的 docstring、`doc/config.rst:156-158`、示例的结构。
  - 支持按消息："each"、"duplicate" 的字面意思，以及标准库 `warnings` 的 "once" 语义。
- **修订建议是否扩大原需求**：没有扩大。
  - 补一句规则，和可选的断言（不同 slug 各显示一次），都在原需求与 gold 行为之内，gold 都能通过。
  - "改测试让两种去重键都通过"会偏离原意，主审已不推荐。
- **"可探针"是否把静态候选与剩余条件分开**：分开了，见 §2.1。
- **是否把环境已验当成质量合格**：没有。card 把"环境侧"单列一段，只说评分可复现、镜像层面的开发条件满足，质量问题另行记录。
- **是否只在核对旧结论**：没有。去重键、CE4 漏测、G1–G3、同族关系都是主审新增的。历史的环境审查不涉及题意（delta 引用了 `checks_r2e.md:3`，我没有打开该文件）。

## 5. 与我初判的差异

| 项 | 我的初判 | 主审 | 现在的结论 |
| --- | --- | --- | --- |
| 处置标签 | "可作开发诊断的静态候选，附条件" | `needs_review` | 改为同意 `needs_review`。公开读者隔离阅读也无法裁决，来源证据又显示这是生成缺陷；何况两种写法本来都要求先决定歧义 |
| 风险等级 | 误拒风险"中" | "静态推断，高确定" | 不是分歧：前者说的是发生率，后者说的是 CE1 判 0 的确定性 |
| 按消息去重是否"最字面" | 没这样表述；我认为仓库文档把 slug 定义为警告的名字，所以 "each warning" 在本领域有另一种读法 | "最字面的读法是按消息去重" | **保留**这一措辞分歧；不影响处置 |
| R04 的后备修法 | 未涉及 | 不要改导入，改用评分前恢复 | **保留**分歧：我认为窄改导入更轻，且在现有机制之内，应与恢复方案并列 |
| I5 的绕过面 | `tests/coveragetest.py`、`setup.cfg`、根目录 conftest | `tests/coveragetest.py`、`tests/helpers.py` | 合并为 N4，交共享机制 |
| 裸 `pytest` 能否使用 | 未知 | — | 镜像层面已有答案：`WHICH_pytest=/testbed/.venv/bin/pytest`。正式链仍待验 |
| 同族关系 | 凭记忆写下，未核 | 已 grep 核实 4 题 | 已核实（C10） |
| 下一步 | 先读 public_read，再决定是否澄清题面 | 先在 CPU 上跑 CE1/CE3/CE4，再提修订 | public_read 已读，同意先跑 CPU；另补 N1、N2 |

## 6. 最小后续实验

1. **CPU 实验（主审提出，我同意）**：在 `r2e_derive_v1` 派生镜像上用 RH2 回放评分，跑以下三个候选：
   - CE1（按消息去重）：预期 0，只有 `ApiTest.test_warn_once` 不一致；
   - CE3（按 slug 去重的另一种实现）：预期 1；
   - CE4（全局 once）：预期 1。

   结果能把误拒和漏测从静态推断升级为当前 CPU 证据。它只是确认性实验，T0 决定可以同时进行。镜像所在机器的现状由协调者确认，必要时按配方重建。
2. **可选，可在同一批里顺带跑**：
   - CE-D：给 `inorout.py:343` 加 `once=True`，不改 `tests/coveragetest.py`。预期 0，失败在 `SourceIncludeOmitTest.test_source_include_exclusive`。用途是给关闭 R04 留下执行证据。
   - CE-G：只在 `tests/coveragetest.py` 的模块级给 `Coverage._warn` 打补丁，不改 `coverage/`。预期 1。用途是给 I5 留证据；也可以交共享机制负责人去做。
3. **如果 T0 选了 A**：只需核渲染结果（prompt 含新句子），评分不重跑；再按清单 33–36 做少量盲解，记录解题者选的去重键。
4. **池级筛查（建议）**：做 N3 所说的"noop 失败点早于决定性断言"筛查。

## 7. 第二步阅读范围

- **本题 OUTPUT_DIR**：`public_read.md`、`analysis_before_history.md`、`old_findings_delta.md`、`card.md`、`screening_record.json` 全文。`reviewer_initial.md` 是我的封存稿，没有改动。
- **历史**（`history/…/refs.json` 所列）：
  - 读过：本题 `findings.md` 全文；旧 `screening_record.json` 的 `disposition`、`issues` 字段，以及 `checks` 中 R01–R20 每条的前 600 字符；`decisions.md` 的 grep 输出，覆盖 E01–E24 各行与 T0-1、T0-2 两行。
  - 没读：`known_issues.json`、`results_20260924.md`、复现脚本、`packages/p1/README.md`、`facts.json`、`checks_r2e.md`。
- **为核对主张打开的原件**：
  - 来源原始行：本题一行的 `modified_files` 字段和 `prompt` 字段片段；
  - M3：`git_gold.diff` 与 `gold.diff`（用 `cmp`、`diff` 比对）；账本第 23 行的 `gold_matches_git_diff_changed_lines` 字段；两份 noop 输出（grep）；
  - `runs/r2e_rf_20260923/remote/prepared_r2e/prompts.jsonl`：本题一行；
  - `runs/r2e_rf_20260923/reconcile_all/reconcile.json`：第 [6]、[54] 行；
  - `expected_provenance.md` 第 3 行；
  - dev probe 的 `agent_probe.log`：grep 结果，以及第 112–126 行；
  - 同批另外 4 道 coveragepy 题公开的 `coverage/control.py`（grep）；
  - `s2_r2e/revisions/material_revisions_v3.json`：只统计了修订种类与目标；
  - `rh2/src/repoharness2/adapters/slime/prepared_task_face.py` 第 405–455 行，以及两个代码文件的 `git status` / `git diff --stat`。
- **没读**：批次的 README 与 `assignments.json`；其它题的私有材料；datalad 的修订文件（B1 的内容取自 `decisions.md` 的 T0-2 行）。
