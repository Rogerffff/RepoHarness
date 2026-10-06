# coveragepy__5dbbe143 独立复核：第一步初判（reviewer_initial）

2026-09-25 · 独立复核者（Claude，干净上下文）· 只做静态阅读和已有原件复读：没有运行代码或容器，没有读主审产物、公开读者产物或任何历史结论。复读已有日志**不算**独立重跑。

路径约定（均相对仓库根）：`PUB` = `runs/r2e_static_prep_20260924/v2/public/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9`，`PRIV` = `runs/r2e_static_prep_20260924/v2/private/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9`，`WT` = `PUB/worktree`（实际初始工作树）。行号都是文件内行号。

## 0. 初判摘要

- **题目**：给私有方法 `Coverage._warn` 加 `once` 关键字参数，让 `once=True` 的警告只显示一次。gold 只改 `coverage/control.py`：新增 `_no_warn_slugs` 列表，第一次调用 `_warn` 时从 `config.disable_warnings` 复制出来；`once=True` 的警告显示后，把它的 slug 追加进这个列表（`PRIV/gold.patch`）。
- **目标键只有 1 个**：`ApiTest.test_warn_once`。两组 current 运行结果一致：noop FAILED，gold PASSED。其余 74 键是同文件回归键，noop 和 gold 都是 PASSED。期望映射的 75 键全部是 PASSED，所以不存在"更完整的修复把 FAILED/ERROR 键翻成 PASSED、反而判 0"的问题。
- **题面描述的报错**逐字出现在 noop 目标键上：`TypeError: _warn() got an unexpected keyword argument 'once'`，位置 `r2e_tests/test_1.py:545`。材料身份逐项核对一致：gold 的修改前 blob、隐藏测试树、期望映射、入口脚本摘要都对得上。本题没有材料修订。
- **最重要的疑点：误拒风险，中等**。决定性断言 `assertNotIn("Warning, warning 2!", err)`（`PRIV/hidden_tests/test_1.py:549`）要求"slug 相同、消息不同"的第二条警告也算重复，也就是**按 slug 去重**。题面只写了 "displayed only once each, preventing duplicate warnings"，没有说什么算"重复"。
  - 公开材料偏向按 slug 判定：`_warn` 的 docstring、文档把 slug 称为警告的名字、原例两次调用用的是同一 slug 和不同消息。
  - 但 base 代码里现成的 `self._warnings` 记录的是消息文本；Python `warnings` 模块的 "once" 规则也按消息去重。
  - 因此按消息去重、或按 (slug, msg) 组合去重的实现，一定判 0。
- **漏测：低到中**。测试只检查"同 slug 的第二条被压住"，没有检查"不同 slug 的 once 警告各自显示一次"。一个全局开关式实现（第一条 once 警告之后，压掉所有后续 once 警告）能拿满 75 键。
- **搬迁伪影：低**。隐藏测试 `test_2.py` 是修复后的 `tests/coveragetest.py`，其中 `capture_warning` 接受 `once`。但 `test_1.py:24` 导入的是工作树里 base 版的 `tests/coveragetest.py`，它的 `capture_warning(msg, slug=None)`（第 267 行）不接受 `once`。如果候选在 `assert_warnings` 覆盖到的生产调用点显式传 `once=`，5 个回归键会抛 TypeError，除非候选同时修改这份 helper（评分不会重置它）。
- **评分边界（R2E 通用性质，本题实例）**：候选可以修改 `tests/coveragetest.py`、`setup.cfg`（其 addopts 在评分时生效）和根目录 conftest，评分都不重置。例如在 helper 里 monkeypatch `Coverage._warn`，不改产品代码也能让目标键通过。
- **gold 按题面修好了原例**，但有两处未测的边角：
  - `slug=None` 且 `once=True` 时，gold 把 `None` 加进屏蔽列表，此后所有不带 slug 的警告都被压住。
  - `disable_warnings` 从每次实时读取，变成第一次 `_warn` 时的快照。
  - 两者都不影响评分，也不是题面要求。
- **暂定处置**：可作开发诊断用的静态候选，附三个条件：
  1. 全局 actor 镜像要先切换。正式链目前用来源镜像，隐藏测试和修复提交对解题者可见，见环境卡 §2。
  2. 对"按 slug 去重"的歧义做出决定：要么澄清题面，要么在探针解读中明确标注。
  3. 检查通过的补丁是否改了 `tests/`、`setup.cfg` 或根 conftest。

五类问题一览：

| 类别 | 结论 |
| --- | --- |
| 漏测 | 有：不同 slug 之间是否独立未测；`once` 与 `disable_warnings`、`slug=None` 的交互未测 |
| 误拒 | 有风险：按消息去重会判 0（中）；在生产调用点传 `once=` 会碰上 base helper（低） |
| 错误回归 | 测试层面未发现：74 个回归键在 noop 和 gold 下都 PASSED，断言与旧行为一致。gold 自身有两处未测的语义变化 |
| 材料错配 | 未发现：所有摘要一致。公开工作树缺 `install.sh`，manifest 已披露，评分侧不用它 |
| 开发缺口 | `public_hints` 与 R2E 不符（全局问题）；公开 `run_tests.sh` 不能直接运行；actor 用的来源镜像会泄漏隐藏测试和修复提交（全局问题）；actor 正式链未验 |

## 1. 实际读取范围

- **角色卡与方法文档**
  - `roles/reviewer_r2e.md`：全文。
  - `roles/investigator_r2e.md`：Read 工具返回了全文（34 行）。我只把"R2E 的评分口径""材料"两节当口径使用；另外两节是主审流程和边界说明，不含本题的主审产物。
  - 方法文档全文：`quality_review_protocol_20260920.md`、`r2e_environment_card.md`、`record_template.md`。
  - **未读** 40 项清单：初判用不到 checks 编号。
- **PUB**
  - 全文：`user_prompt.txt`、`environment_brief.md`、`public_bundle.json`。
  - `worktree_manifest.json`：只看了顶层字段、`export`、`initial_diff`、三个 untracked 字段。
- **WT**
  - 全文：`run_tests.sh`、`setup.cfg`、`.gitignore`、`tests/conftest.py`。
  - `coverage/control.py`：第 180–360、391–530、680–720 行，外加全文 grep `_warn`。
  - `coverage/config.py`：grep `disable_warnings`。
  - `coverage/` 下所有 `warn(` 调用点：grep。
  - `CHANGES.rst`：前 60 行。`doc/config.rst`：154–166 行。`doc/cmd.rst`：129–160 行。
  - `tests/helpers.py`：grep。`tests/modules`：只列了目录。
  - `tests/test_api.py`、`tests/coveragetest.py`：与隐藏测试做 diff，看改动处，再 grep 定位。
- **PRIV**
  - 全文：`gold.patch`、`run_tests.sh`、`revisions.json`（内容为 `[]`）、`expected_output.json`、`run_refs.json`、`hidden_tests/__init__.py`、`test_1.py`（1128 行）、`test_2.py`（502 行）。
  - `grading_bundle.json`、`validation_bundle.json`：只看了字段摘要。
  - 隐藏测试三个文件：算了 sha256。
- **运行原件**（都是 `run_refs.json` 列出的）
  - 4 个 current 账本的第 7 行全文。
  - 对应的 4 份 `.eval.log`：核对 sha256；读开头的标记行、目标键的失败段和捕获输出段、short test summary；全文 grep 收集错误、cache 警告和 Traceback。
  - M3 独立参考账本第 23、70 行，以及两份 `test_output.txt`（只核 sha256 并 grep 结果行）。
- **没读**
  - OUTPUT_DIR 里的其它文件、任何 `history/`、`docs/.../r2e_env_repair_20260924/`、任何审查目录、`r2e_static_review_20260925/README.md`。
  - `runs/` 下的分析或汇总文件、账本引用的 `*.diagnostics.json`。
  - `.venv` 里的第三方库源码，例如 `unittest_mixins`（不在公开包里）。
  - `runs/r2e_env_repair_20260924/_rerun2/` 下只读了 run_refs 列出的两份账本和两份日志。

## 2. 八方面：看了什么，初判是什么

| 方面 | 看了什么 | 初判 |
| --- | --- | --- |
| 公开需求 | 题面、`_warn` 的 docstring、`doc/config.rst`、`doc/cmd.rst`、`CHANGES.rst` | 要加的参数 `once` 和"只显示一次"的目标都写清了；按什么判断"重复"没有明说（见 §3 的 R2b）。base 的代码、文档和 CHANGES 里 grep 不到任何与 `once` 相关的内容，没有答案泄漏 |
| 材料与初始问题 | gold 的修改前 blob、manifest、账本、日志 | `WT/coverage/control.py` 的 git blob 是 `6e59078c…`，等于 gold 的修改前 blob。`initial_diff` 为空（0 字节）。noop 在 `test_1.py:545` 抛出题面描述的 TypeError，说明原问题在这个 base 上成立（通过直接调用触发） |
| 测试是否测到要求 | `test_1.py` 全文、两份 helper 的 diff | 目标键覆盖了"能接受 `once`"和"同 slug 的第二条被压住"。没覆盖：不同 slug 各显示一次、`once` 与 `disable_warnings` 的交互、`slug=None` |
| 是否误拒合理解 | 反例推演（§5） | 按消息去重或按 (slug, msg) 去重一定判 0；公开依据偏向 slug，但不够充分，风险中等。在生产调用点传 `once=` 的候选会受 base helper 影响，风险低 |
| 回归与 gold 完整性 | 74 个回归键、`warn(` 调用点、gold diff | 输出格式（`test_warnings`）、`disable_warnings`（`test_warnings_suppressed`）、默认 `once=False` 时同 slug 连发两条都照常显示（`test_warnings` 里的两条 module-not-imported）都有保护。gold 有两处未测边角（见 §3 附注） |
| agent 开发条件 | brief、环境卡、账本 observations、`setup.cfg` | 纯 Python 单文件改动，不需要新依赖、构建或网络。复现时要先调用 `cov.load()`。公开的 `run_tests.sh` 指向解题侧不存在的 `r2e_tests`。actor 正式链未验 |
| 交付与评分边界 | 环境卡 §3、账本 projection、`test_1.py:24` | gold 投影只包含 `coverage/control.py`。helper 和 `setup.cfg` 可以改变验收结果（R2E 通用性质，本题实例）。来源镜像泄漏答案（全局问题） |
| 题目关系与用途 | `CHANGES.rst`、M3 账本的 `gold_meta` | 小型 API 行为补充，约 10 行。题面示例就是测试输入。与池中其它题的关系未核（§7） |

## 3. 需求—断言双向映射

| 公开要求或合理旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖情况 | 运行证据或下一步验证 |
| --- | --- | --- | --- | --- |
| R1：`_warn` 接受 `once` 关键字，不再抛 TypeError | `PUB/user_prompt.txt:4-7、10-15、20-21` | `ApiTest.test_warn_once`（`test_1.py:545-546` 的两次调用） | 覆盖 | 两次 noop 都在 :545 抛 TypeError；两次 gold 都 PASSED |
| R2a：`once=True` 的第一条照常显示 | `user_prompt.txt:17-18` | `test_1.py:548` `assertIn("Warning, warning 1!", err)` | 覆盖 | gold 日志中该测试捕获的 stderr 只有 `Coverage.py warning: Warning, warning 1! (bot)`（R-f gold 日志 :31；环境轮 gold 日志 :25） |
| R2b：同一个警告不重复显示；"同一"按 slug 判定 | 题面 "displayed only once each, preventing duplicate warnings"（:18）；原例同 slug、不同消息（:13-14）；`_warn` 的 docstring "For warning suppression, use `slug` as the shorthand"（`WT/coverage/control.py:339`）；`WT/doc/config.rst:156-158` 把 slug 称为 "the name of the warning" | `test_1.py:549` `assertNotIn("Warning, warning 2!", err)` | 覆盖，但与"按消息去重"的读法**冲突** | 静态推断：按消息去重的候选一定判 0。现有运行从没让 :549 失败过（noop 在 :545 就停了），这条断言的区分力只来自阅读 |
| R2c："each"：不同 slug 的 once 警告各显示一次 | 题面 "only once each" | 无 | **缺失** | 全局开关式实现能拿满分（§5 反例 C） |
| R3：默认 `once=False` 不去重，同 slug 的多条都显示 | 旧行为 | `ApiTest.test_warnings`（`test_1.py:511-516`，断言两条 `(module-not-imported)` 都出现） | 覆盖 | noop 和 gold 都 PASSED |
| R4：输出格式 `Coverage.py warning: msg (slug)\n` | 旧行为，`WT/coverage/control.py:345-349` | 同上，比对一个精确的 4 行文本块 | 覆盖 | 同上 |
| R5：`disable_warnings` 仍然生效 | 旧行为，`doc/config.rst:156` | `ApiTest.test_warnings_suppressed`（:518-540，通过 `.coveragerc` 配置） | 覆盖，但只测了构造时的配置 | 隐藏版比 base 版少断言一个行尾换行（`test_1.py:535-538` 对照 `WT/tests/test_api.py` 同处），是同一上游提交做的放宽，不影响任何合理实现 |
| R6："No data" 警告靠 `_warn_no_data` 标志只发一次 | 旧行为 | `test_two_getdata_only_warn_once` / `test_two_getdata_warn_twice`（经 `assert_warnings` 替换了 `_warn`，不走真正的 `_warn`） | 覆盖的是标志逻辑 | 如果候选把这个标志重构成用 `once`，会被 `warn_twice`（第二次仍须警告）拦住，还会碰上 §4(d) 的 helper 问题 |
| R7：`once` 与 `disable_warnings` 的交互；`slug=None` 配 `once`；once 之后同 slug 的 `once=False` 警告 | 题面没提 | 无 | 未规定，也未测 | 不影响评分 |

附注：gold 的两处未测边角（静态推断）。

1. **`slug=None` 配 `once=True`**：gold 会执行 `self._no_warn_slugs.append(None)`（`gold.patch:39-40`）。此后所有 `slug=None` 的警告都满足 `slug in self._no_warn_slugs`，被压住。仓库里不带 slug 的调用点有：
   - `coverage/data.py:115`：合并时遇到坏数据文件；
   - `coverage/control.py:455`：插件 tracer 不受支持；
   - `coverage/control.py:707`：`[run] note` 设置已废弃；
   - `coverage/html.py:88`：没有测到任何 context。

   目前没有调用方传 `once`，所以这是潜在缺陷，不是现有回归。
2. **`disable_warnings` 变成快照**：gold 在第一次调用 `_warn` 时把 `config.disable_warnings` 复制成 `_no_warn_slugs`（`gold.patch:28-29`）。此后再用 `set_option("run:disable_warnings", …)` 修改配置就不生效了；base 每次都实时读取（`WT/coverage/control.py:341`）。这一点未测，影响小；保留实时读取的候选同样能通过。

## 4. R2E 专项

**(a) 非 PASSED 的期望键**：没有。`PRIV/expected_output.json` 里 75 键全是 PASSED，不存在"更完整的修复把 FAILED 翻成 PASSED、反而判 0"的情况。反过来要注意：评分要求逐键完全一致，所以候选只要让任何一个回归键失败（例如 §5 反例 D），也是 0。

**(b) 题面描述的报错**：两份 current noop 日志都逐字出现 `E       TypeError: _warn() got an unexpected keyword argument 'once'`，位置 `r2e_tests/test_1.py:545`。

- R-f noop 日志：第 30、32 行。
- 环境轮 noop 日志：第 30、32 行。
- short test summary 里有 `FAILED r2e_tests/test_1.py::ApiTest::test_warn_once`（R-f noop 日志第 7874 行）。

这与题面的 Actual Behavior（`user_prompt.txt:20-21`）一致。

**(c) 题面是否泄漏修法**：

- 题面给出了方法名 `_warn`、参数名 `once` 和完整的调用示例。示例（`user_prompt.txt:11-14`）和测试体（`test_1.py:543-546`）逐字相同：测试的输入是公开的，但期望输出（第二条被压住）没有明说。
- 没有泄漏实现方式：既没提屏蔽列表，也没提按 slug 判定。
- base 工作树、CHANGES 和文档里都 grep 不到 `once` 相关内容。

**(d) 测试支撑与撞键**：

- `test_1.py:24` 从 `tests.coveragetest` 导入 `CoverageTest, CoverageTestMethodsMixin, TESTS_DIR, UsingModulesMixin`，用的是工作树里的 base 版文件。候选可以修改它，评分也不重置它。
- 隐藏测试 `test_2.py` 是同一文件修复后的版本，与 base 只差一处：`capture_warning` 接受 `once`（`test_2.py:267-269`）。但没有任何文件导入它。它只作为测试模块被 pytest 收集，不产生键（里面的 `CoverageTest` 没有 `test_` 方法）。M3 账本的 `gold_meta.excluded` 显示上游修复提交同时改了 `tests/coveragetest.py` 和 `tests/test_api.py`，与此对应。
- 结果：`assert_warnings` 里替换 `cov._warn` 的是 base 版 `capture_warning(msg, slug=None)`（`WT/tests/coveragetest.py:267、274`）。用到它的 5 个回归键是：
  - `ApiTest.test_two_getdata_only_warn_once`
  - `ApiTest.test_two_getdata_warn_twice`
  - `ApiTest.test_combining_corrupt_data`
  - `NamespaceModuleTest.test_bug_572`
  - `SourceIncludeOmitTest.test_source_include_exclusive`

  对应 `test_1.py:364-381、407、763、850`。如果候选在这些路径的生产调用点显式传 `once=`（例如给 `coverage/inorout.py:343` 的 include-ignored 警告加 `once=True`），base 替身会抛 TypeError，键变成 FAILED，整题判 0。而上游自己的测试套件里 helper 已更新，同样的改动会通过。题面没要求改调用点，所以发生概率低。
- 另一个搬迁伪影：`tests/conftest.py` 里的 autouse fixture（`reset_sys_path`、`fix_xdist_sys_path`、`set_warnings`）对 `r2e_tests/` 不生效。现有 6 次运行（4 次 current 加 2 次 M3）结果稳定，没看到影响。`unittest_mixins` 自身是否保存和恢复 `sys.path` 我没读源码。
- 撞键：没有。75 键全部来自 `test_1.py`（summary 里每一行都是 `r2e_tests/test_1.py::…`）。`IncludeOmitTestsMixin` 的 8 个方法分别挂在 3 个不同类名下，键不重复。

**(e) 时间、随机、资源敏感的键**：

- `WT/setup.cfg:2` 的 addopts `-q -n3 --strict --no-flaky-report -rfe --failed-first` 在评分时生效：日志里有 "bringing up nodes..."，即 3 个 xdist worker 跑在 2 个 CPU 上。
- current 运行的测试段耗时 2.1–2.5 秒，内存峰值约 300 MB。
- `test_include_can_measure_stdlib` 用了 `random`，但断言与随机数值无关。
- `CurrentInstanceTest` 依赖类级的 `_instances` 栈。只有同一 worker 上前面的测试异常中断且没调用 `stop()` 时，它才可能被污染；这只影响本来就已经失败的候选。
- 没发现时间敏感的键。4 次 current 和 2 次 M3 的结果完全一致。

**(f) 修订**：不适用。`revisions.json` 是 `[]`，`run_refs.current_material.material_revisions` 为空。R-f 组的标注是"来源版材料"，但标记为 `material=current`，两者不矛盾：没有修订时，来源版就是当前版；而且日志里的隐藏测试树摘要 `5a450eab…` 与当前材料一致。

## 5. 反例设计与最小后续实验（全是静态预测，都没有执行）

| 编号 | 候选实现 | 与题面的关系 | 预测 reward | 说明 |
| --- | --- | --- | --- | --- |
| A | 按消息去重：`if once and msg in self._warnings: return`（复用 `control.py:208` 已有的消息记录） | 合理读法之一（"displayed only once each"） | 0（只有 `test_warn_once` 不一致，挂在 :549） | 误拒风险的核心 |
| A' | 按 (slug, msg) 组合去重 | 同上 | 0 | 同上 |
| B | 另一种按 slug 的实现：单独维护一个 set，`disable_warnings` 仍实时读取；`slug is None` 时退回按消息判定 | 符合 gold 的语义 | 1 | 说明测试不绑死 gold 的内部结构 |
| C | 全局开关：第一条 once 警告之后，压掉所有后续 once 警告（甚至所有警告） | 违反 "each" | 1 | 漏测 |
| D | 按 slug 实现，并在 `inorout.py:343` 等调用点加 `once=True`，不改 `tests/coveragetest.py` | 超出题面，但与上游后续方向一致 | 0（`test_source_include_exclusive` 抛 TypeError） | 搬迁伪影 |
| E | 只加参数不实现：`once` 被忽略 | 不满足题面 | 0（挂在 :549） | 说明目标键能区分"只改了签名" |
| F | 不管 `once`，总按 slug 去重 | 破坏旧行为 | 0（`test_warnings` 里第二条 module-not-imported 丢失） | 说明回归键保护了默认行为 |
| G | 不改产品代码，只在 `tests/coveragetest.py` 里 monkeypatch `Coverage._warn` | 作弊 | 1 | 评分边界问题，要靠审查补丁才能发现 |

**最小后续实验**：用 CPU 在派生镜像上各评一次 A、C、E，预期结果分别是 0、1、0。这样能把"静态必然"升级为"当前 CPU 实测"证据；D、G 可选。但实验回答不了"A 是否算合理解"，那要靠对公开规格的判断。

**唯一最值得先做的下一步**：在第二步对照公开读者的 `public_read.md`，看它独立理解的"重复"按什么判定。

- 如果公开读者也没能确定是按 slug，建议澄清题面：只改公开规格、不改测试，例如写明"重复按 slug 判定"。
- 否则保持题面不变，但在探针解读里把"按消息去重导致 `test_warn_once` 失败"标为规格歧义，而不是能力不足。

## 6. 逐题开发需求

- **解释器**：`/testbed/.venv/bin/python`，Python 3.7.9（brief）。账本 observations 的 `RH2_OBS_IMPORT_PATH=/testbed/coverage/__init__.py` 说明评分侧从工作树内导入，改了源码就直接生效（评分侧实测）。
- **依赖**：不需要新增。venv 里有 pytest；有 pytest-xdist（日志 "bringing up nodes..."）；有 flaky（`--no-flaky-report` 参数被接受）；有 unittest_mixins（隐藏测试会导入它）。以上是评分侧实测；解题侧只有镜像层面实测（环境卡 §2），actor 待验。
- **资产**：`tests/modules/**`、`tests/moremodules/**`、`tests/helpers.py` 都在工作树里。
- **权限**：agent（uid 54321）可写 `/testbed`（brief）。`.coverage` 和 `.pytest_cache` 已被 `WT/.gitignore:8、29` 忽略，在 `/testbed` 里复现不会留下被跟踪的改动。
- **网络**：不需要。**构建**：不需要，纯 Python 改动。
- **提交边界**：gold 投影的 `included_paths` 是 `["coverage/control.py"]`（R-f gold 账本第 7 行）。
- **复现方法**：必须先调用 `cov.load()`。原因：base 的 `_warn` 会用到 `self._debug`，而它在 `_init()` 之前是 None；`load()` 会调用 `_init()`（`WT/coverage/control.py:391-401`）。例如在临时目录里运行：
  `python -c "import coverage; c=coverage.Coverage(); c.load(); c._warn('w1', slug='bot', once=True); c._warn('w2', slug='bot', once=True)"`
- **相关测试**：`python -m pytest tests/test_api.py -k warn`（会带上 `setup.cfg` 的 addopts）。
- **公开材料的缺陷**：
  - `public_hints` 说 conda 环境、pip 可用、"测试文件会被重置"，这些都不适用于 R2E（环境卡 §3）。
  - `WT/run_tests.sh` 指向解题侧不存在的 `r2e_tests`，直接运行会报找不到路径。
  - `install.sh` 在镜像里存在，但没有导出到公开工作树（manifest 的 `untracked_missing`）。评分侧日志有 `RH2_INSTALL_SKIPPED=1`，对评分没有影响。
- **actor 镜像（全局阻塞项）**：正式链目前取 `public.image`，即来源镜像 `namanjain12/coveragepy_final:5dbbe…`（`PUB/public_bundle.json:10`）。M3 账本第 23 行的 facts 显示这张镜像：
  - 根目录有 `r2e_tests`（3 个文件）；
  - 修复提交可以通过 git 取到（`fix_reachable: commit`），HEAD 之后还有 2401 个提交。

  也就是说解题者能看到隐藏测试和答案。环境卡 §2 已把它列为进入 actor 前必须修改的全局项。

## 7. 未知与未查

- 公开读者对"重复"是怎么理解的：没读，属于第二步材料。
- actor 正式链的条件：非交互 shell 的 PATH、`/rh2/bash_env`、提示措辞。actor 待验。
- 本仓库的公开测试在解题侧有没有与本题无关的失败：环境卡说有 13 题存在这种情况，但本题 brief 没提。未知。
- `unittest_mixins` 的临时目录和 `sys.path` 行为：不在公开包里，没读。
- 与池中其它题的关系：以下凭记忆，未核。上游在 5.0.2 版随后加入了一条使用 `once=True` 的 "dynamic-conflict" 警告；base 的 CHANGES 在 Unreleased 段还没有这一条。如果池中有这道后续题，本题的修复可能已经在它的 base 里。按边界要求，我没有读其它题。
- §5 的反例都没有执行。

## 附录 A：运行原件核对

| 组 | 账本:行 | 候选 | 结果 | 日志 sha256（与 run_refs 一致） | 关键定位 |
| --- | --- | --- | --- | --- | --- |
| R-f noop | `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:7` | noop | reward 0.0，74/75 一致，mismatched=[`ApiTest.test_warn_once`]，test rc=1 | `d802aba1…` ✓ | 日志 :21-32 是失败段；:7874-7875 是汇总（1 failed, 74 passed） |
| R-f gold | `runs/r2e_rf_20260923/remote/ledger_r2e_all_gold.jsonl:7` | gold（patch sha `47297da7…`，与 validation_bundle 一致） | reward 1.0，75/75 一致 | `4f0b31e3…` ✓ | :28-31 捕获的 stderr 只有 warning 1；:7867 "75 passed" |
| 环境轮 noop | `runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl:7` | noop | reward 0.0，74/75 一致 | `be74bcf2…` ✓ | :30、:32；:7874-7875 |
| 环境轮 gold | `runs/r2e_env_repair_20260924/_rerun2/ledger_gold.jsonl:7` | gold | reward 1.0，75/75 一致 | `1f07de08…` ✓ | :25；:7867 |
| M3 参考 a1、a2 | `runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:23、70` | gold（来源镜像、来源版材料） | reward 1，75 passed | `fb4425ad…` / `04a3880a…` ✓ | `test_output.txt` 末行 "75 passed" |

- **同一环境**：四个 current 行用的是同一张派生镜像 `sha256:81bf06a0…`（`rh2-r2e-derived/coveragepy:5dbbe1430c16-r2e_derive_v1`，配方 sha `0da821a1…`）。评分用户 54322，资源 2 CPU / 4 GiB / `/tmp` 1 GiB，网络 deny_all。
- **摘要逐项对得上**：
  - 日志开头的 `RH2_SETUP_HIDDEN_TESTS_TREE=5a450eab…` 等于 `run_refs.current_material.hidden_tests_tree_sha256`。
  - `RH2_SETUP_ENTRY_SHA256=8285765f…` 等于 grading_bundle 的 `run_tests_sh_sha256`。
  - `expected_output.json` 的 sha256 `c65a3c08…` 等于当前期望映射的摘要。
  - 隐藏测试三个文件的 sha256 与 grading_bundle 一致。
- **gold 日志开头的 `git status`** 只有 ` M coverage/control.py`，外加两个未跟踪文件 `install.sh`、`run_tests.sh`。
- **日期标注**：环境轮这一组名称写的是 09-24，但账本的 `started_at_utc` 是 2026-09-23T18:10Z，推测是时区差，不影响材料对应关系。
