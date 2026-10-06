# orange3__22e98f8f4cccc25f0d0217f9f4251b66d49b4237 · 独立复核初判

独立复核者（Claude，干净上下文）· 2026-09-25 · 第一步，写于读取公开读者与主审产物之前。只做了静态阅读和已有证据核对：没有运行项目代码或容器，没有修改原件。

路径简写（均相对仓库根）：
- `PUBLIC` = `runs/r2e_static_prep_20260924/v2/public/orange3__22e98f8f4cccc25f0d0217f9f4251b66d49b4237`（`WT` = `PUBLIC/worktree`）
- `PRIVATE` = `runs/r2e_static_prep_20260924/v2/private/orange3__22e98f8f4cccc25f0d0217f9f4251b66d49b4237`
- `DEVCHECK` = `runs/r2e_actor_20260925/devcheck/orange3__22e98f8f4cccc25f0d0217f9f4251b6`

## 0. 摘要

- **评分材料没发现问题。** 目标键 `TestHelpers.test_unique_in_order_mapping` 直接断言题面原例：`[2, 3, 1]` 应返回 `([2, 3, 1], [0, 1, 2])`，另有两个带重复元素的变体。期望映射的 23 个键全是 PASSED，所以没有"更完整的修复会让失败键变 PASSED、反被判 0"的风险。3 组 current 运行中，noop 都是 22/23 → 0，gold 都是 23/23 → 1；去掉时间戳后，三份 noop 日志彼此逐字相同，三份 gold 日志也一样。
- **最重要的问题：题面泄漏了完整修法，而且标签自相矛盾。** 题面标为 "Example Buggy Code" 的代码（`PUBLIC/user_prompt.txt:14-23`）和 gold 后像逐行相同：def 行之后的 9 行函数体完全一致，只少了 docstring（已用脚本比对）。这段代码其实是修好的版本：在真实 actor 条件下逐字运行，输出 `Mapping: [0, 1, 2]`，也就是期望值，而不是题面说的 `[2, 0, 1]`。仓库里真正的 base 实现是 `np.unique` 版本（`WT/Orange/widgets/data/owcreateclass.py:155-157`），题面的 "Actual Behavior" 描述的是这个版本。解题者只要把题面代码贴进函数，行为就和 gold 相同，能拿到 1 分。
- **暂定建议：** 评分侧可以用。但按现在的题面，不适合作能力诊断、训练或评测题，最多作为易题或链路正对照，并标注"题面给修法（完整）"。如果要当正常题用，需要修订公开题面，隐藏测试和期望映射不用改。最终由用户决定。

## 1. 题目目标与材料对应

- **公开目标：** `unique_in_order_mapping(a)` 返回两样东西：按首次出现顺序排列的唯一元素，以及每个输入元素在这些唯一元素中的下标。docstring（`owcreateclass.py:151-154`）和题面 Description 说法一致。
- **初态 bug 的机制（源码推断，有执行证据支持）：**
  - base 的写法是 `order = np.argsort(idx)` 后接 `mapping = order[inv]`（`:156-157`）。正确写法应该用 `order` 的逆置换，即 `np.argsort(order)[inv]`。
  - 只有当 `order` 是对合置换（逆置换就是它自己）时，base 才碰巧正确。公开旧测试里的 `[2,1,0,3]`、`[2,1,2,3]`，以及只有两个类名的 widget 用例都属于这种情况，所以旧测试全过。
  - 输入 `[2,3,1]` 时 `order=[1,2,0]`，这是一个三轮换，base 得到 `[2,0,1]`。
  - 执行证据（agent 身份，经真实 Claude Code Bash）：`DEVCHECK/orig/captures/mcve_repo_function.out:3-4` 输出 `(array([2, 3, 1]), array([2, 0, 1]))`；字符串输入 `('b','c','a')` 也得到 `[2, 0, 1]`。widget 里唯一调用者 `_create_variable`（`owcreateclass.py:537-539`）用的就是这个映射，所以例如类名 b/c/a 的规则会被分到错误的类（静态推断）。
- **材料一致性：**
  - `WT` 里 `owcreateclass.py` 的 blob 是 `bbf20096726…`，等于 gold.patch 的前像 `bbf200967`。
  - gold sha256 `474672197e…` 与 3 条 gold 账本的 `candidate.patch_sha256` 以及 validation_bundle 相同。
  - `test_1.py` 的 sha256 `84054928…`、隐藏测试树 `385348d3…`、`run_tests.sh` 的 `5dee57d9…`、期望映射 `1a43a298…` 都与 grading_bundle 第 23 行一致；各 eval log 头部的 `RH2_SETUP_HIDDEN_TESTS_TREE` / `RH2_SETUP_ENTRY_SHA256` 也与之相同。
  - 题面写的 commit `96fda39bb0dc` 等于 base_commit，也等于 devcheck `attempt.json` 里的 `HEAD_BEFORE/AFTER`。
  - `revisions.json` 为 `[]`。R-f 组虽然标为"来源版材料"，但本题没有修订，所以它就是 current 材料。
- **隐藏测试的来源：** 等于 base 公开测试文件，只在 `test_unique_in_order_mapping` 末尾加了 9 行（`PRIVATE/hidden_tests/test_1.py:92-100`）。与 `WT/Orange/widgets/data/tests/test_owcreateclass.py` 做 diff，只有这一处不同。

## 2. 核心映射

| 公开要求 / 合理旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖 | 执行证据 / 下一步验证 |
|---|---|---|---|---|
| 原例 `[2,3,1]` → u `[2,3,1]`、m `[0,1,2]` | 题面 Expected/Actual（`user_prompt.txt:31-45`） | 目标键，`test_1.py:92-94` | 覆盖（原例逐字出现） | noop 在 `test_1.py:94` 失败，`x: array([2, 0, 1])` vs `y: array([0, 1, 2])`（R-f all noop log:45-55）；gold PASSED ×3 |
| 三轮换加重复：`[2,3,1,1]`→`[0,1,2,2]`，`[2,3,1,2]`→`[0,1,2,0]` | 由题面定义和 docstring 直接推出 | `test_1.py:95-100` | 覆盖 | gold PASSED；noop 在 :94 已停，没执行到这里 |
| 旧行为：空输入、单元素、重复、对合排列 | base 公开测试 `test_owcreateclass.py:75-91` | `test_1.py:77-91` | 覆盖（回归断言，base 已通过） | noop 第一个失败在 :94，说明 :77-93 在 base 上通过；devcheck `test_helper.out:4,14` 显示 base 上 1 passed |
| 唯一元素保持首次出现顺序 | Description、docstring | 每组的 `assert_equal(u, …)` | 覆盖 | 同上 |
| widget 按重复类名合并规则 | 公开源码 `:537-539`、公开 widget 测试 | `test_repeated_class_values_{string,discrete}`（`test_1.py:346-364`）等 | 部分：只测了两个类名（对合）的情形 | 修好 helper 就会经唯一调用者修好 widget，不算漏测；字符串输入只经 widget 回归键间接覆盖 |
| 返回类型 | 没有公开约定 | 全部断言都用 `np.testing.assert_equal`，list、tuple、ndarray 都接受 | 不要求 | 静态推断：返回 ndarray 或 list 都能通过 |

**反查：** 目标键的每条断言都能在题面或 base 公开测试里找到依据。没有精确字符串、Mock 调用形状、内部 helper 名这类要求。

**区分力（静态推断，未执行）：**
- `mapping = inv` 在 `[2,1,0,3]` 这组失败。
- `mapping = idx[inv]` 得到的是首次出现位置而不是唯一元素下标。它能通过三个新例，但在 `[2,1,2,3]`（`:89-91`）失败，而这组断言公开测试里也有。
- 按排序返回唯一元素，在 `[2,1,0,3]` 的 u 断言失败。

**合理的非 gold 实现（静态推断，未执行）：** 保留 numpy，写成 `order = np.argsort(idx); unique_in_order = u[order]; mapping = np.argsort(order)[inv]`。空输入时 `np.unique` 返回空的整型 `idx` 和 `inv`，而断言按值比较，所以应该全部通过。

## 3. R2E 专项

- **(a) 非 PASSED 期望键：没有**，23 个键全是 PASSED，正确修复不会因为失败键翻转而判 0。键集合可能变化的情形只来自一般 R2E 边界：
  - 改动 `WT/Orange/widgets/tests/base.py`。它是隐藏测试导入的 base 版辅助代码，评分时不会被重置。
  - 在 rootdir 新增 conftest。
  - 正常修复不会碰这两处。
- **(b) 题面报错是否出现在 noop 目标键：出现。**
  - 题面 "Actual Behavior" 的 mapping `[2, 0, 1]`，与 3 份 current noop 日志在 `test_1.py:94` 报出的 `x: array([2, 0, 1])` 一致；devcheck 里仓库函数也输出 `[2, 0, 1]`。
  - 题面的 Unique Elements `[2, 3, 1]` 同样成立（`:93` 通过）。
  - 小瑕疵：题面按 list 的格式打印。base 返回的是 ndarray，直接 print 会显示成 `[2 0 1]`。这不影响语义。
- **(c) 题面是否泄漏修法：是，完整泄漏。**
  - `user_prompt.txt:14-23` 的函数与 gold 后像逐行相同，只少了 docstring。
  - 标签也是错的：这段代码逐字运行，输出 `Unique Elements: [2, 3, 1]` / `Mapping: [0, 1, 2]`（`DEVCHECK/orig/captures/mcve_statement_code.out:1-2`），和题面说它产生 `[2, 0, 1]` 相矛盾。
  - 所以这段 Buggy Code 并不是仓库代码。题面把"修复后代码"和"修复前输出"拼在了一起，看起来是生成模型把 diff 的后像当成了前像。这也是一处题面与 base 的材料错配。
- **(d) 测试支撑与撞键：**
  - 隐藏测试导入仓库 base 版的 `Orange.widgets.tests.base.WidgetTest`（候选可以改，评分不重置）。它继承 venv 里的 `orangewidget.tests.base.WidgetTest`，给 `TestOWCreateClass` 带来 3 个继承键：`test_image_export`、`test_minimum_size`、`test_msg_base_class`，都是 PASSED。
  - 被导入的 `WidgetTest` 自己也会被 pytest 收集，产生 3 个 SKIPPED（原因是 ".widget was not set"，见 noop log:156-158）。SKIPPED 不成键，没有影响。
  - 仓库没有 conftest，也没有 pytest 配置（`setup.cfg`、`pyproject.toml`、`tox.ini` 都没有）。`Orange/widgets/tests/__init__.py` 只有 unittest 的 `load_tests`。
  - `Table("zoo")` 这类数据加载按 `dataset_dirs = ['', get_sample_datasets_dir()]`（`WT/Orange/data/table.py:43`）去 `Orange/datasets/` 找。它不依赖原测试目录的相对路径，也不依赖镜像里未导出的顶层 `datasets/`。
  - 只有一个隐藏测试文件、两个类，没有撞键。
- **(e) 时间、随机、资源敏感：**
  - 目标键是纯计算，没有这类问题。
  - widget 键依赖 Qt 和 `xvfb-run --auto-servernum`。以下运行结果都稳定：current 3 次 noop 与 3 次 gold、M3 独立 runner 两次 gold、devcheck 跑公开文件一次。
  - 测试耗时 3.4–4.0 s；内存峰值 2139–2198 MB（账本 `resource.mem_peak_mb`），限额是 4 GiB。
  - `OWCreateClass.cached_variables` 是类级缓存，`test_same_class` 依赖同一进程内的执行顺序。但顺序固定，历次结果一致。
- **(f) 修订：** 本题没有材料修订，不适用。

## 4. 八方面：已查与未查

1. **公开需求（3、23）**
   - 已查：题面、`public_hints`、`environment_brief.md`、docstring、调用者、公开旧测试。目标和原例清楚，没有新 API 或错误格式要求。题面问题见 (c)。
   - 未查：真实 Claude Code 渲染后的任务消息。devcheck 的用户消息是固定的 "Devcheck run…"，system prompt 里也搜不到 conda 或测试重置相关的字样，所以 `user_prompt.txt` 只能算计划输入。实际运行是否带 conda 版 `public_hints`，属于 actor 待验（环境卡 §2 说明 B 线在改）。`public_hints` 说"测试文件会被重置"，这不是 R2E 的机制。但对本题的效果一样：仓库测试文件的改动不会被评分收集。
2. **材料与初始问题（1、2、27）**
   - 已查：base 的出错路径、blob 与各哈希链、noop 失败位置、devcheck 复现。
   - 未查：上游修复提交的历史（本地没有 git 历史）。
3. **测试是否测到要求（18–20、25、32）**
   - 已查：读完了目标键的全部 16 条断言；回归键逐个读了测试体，并核对了它们经过的调用链（`apply` → `_create_variable` → helper）。
   - 未查：没有逐条追 `update_counts`、context handling 的内部实现，它们与本改动无关。
4. **误拒（24、28）**
   - 已查：见 §2，numpy 逆置换替代解静态推断可以通过。
   - 未查：没有实际执行。
5. **回归与 gold（26、27）**
   - 已查：唯一调用者用 `tuple(str(a) for a in names)` 和 `tuple(map_values)` 包装返回值。gold 把返回类型从 ndarray 改成 list，不影响仓库内行为。gold 只有一个 hunk，没有无关改动，并修到了原例（private control 输出 `([2, 3, 1], [0, 1, 2])`）。
   - 未查：仓库外调用者是否依赖 ndarray 返回类型。评分没测这一点，docstring 也没有约定。
6. **开发条件（6–15）**
   - devcheck 已测，条件是真实 CC 2.1.205、agent 54321、派生镜像 `50fd6e31e77a…`：
     - `python` 指向 `/testbed/.venv/bin/python` 3.7.9，Orange 从 `/testbed` 导入，`_valuecount` 扩展已构建；
     - `xvfb-run` 在 `/usr/bin`，pip 24.0 可用但无网，pytest 7.4.4；
     - 带 Qt 前缀跑公开测试文件：23 passed / 3 skipped；
     - 预检：隐藏测试不可见，HEAD 没有子提交（修复提交已从历史中去掉）。
   - 公开测试在 base 上全部通过，解题者需要自己写复现。题面原例就能用来复现，所以不算缺口。
   - 未测：不带 xvfb 前缀能否导入 widget 模块；真实任务提示词的渲染。
   - 注意镜像不同：devcheck 用的镜像 ID 是 `50fd6e31…`（derived8），评分运行用的是 `24840fed8928…` / `a013522716b2…`。三者配方都是 `r2e_derive_v1`，来源镜像相同，结果也一致，但这不能证明是同一个构建。
   - private gold 对照是以 root（uid 0）执行的，不是 agent 身份。
7. **交付与评分边界（4、16–17、21–22、29–31）**
   - 已查：
     - 修复文件是普通源码，gold 账本 `projection.included_paths=['Orange/widgets/data/owcreateclass.py']`。
     - 候选在仓库测试文件里补用例不影响评分，因为 grader 只跑 `r2e_tests`。
     - `WT` 里能看到未跟踪的 `run_tests.sh`，内容与评分入口相同，指向的 `r2e_tests` 在解题容器里不存在。它暴露了评分命令，但不含测试内容。
     - 未跟踪的 `datasets/`、`install.sh` 没有导出（`worktree_manifest.json` 的 `untracked_missing`），内容未知，但与本题评分无关，见 (d)。
     - 除题面本身外，可见资产里没有答案：全树 grep `unique_in_order`、`first_position` 只命中 base 源码和公开测试。
   - 未查：平台级隔离审计，引用环境卡，不重做。
8. **题目关系与用途（5、29–30、37–40）**
   - 已查：题面给了完整修法；外部答案线索方面无网，git 历史也已清理。任务类型是 helper 的算法 bug，本身难度低，泄漏后接近复制粘贴。
   - 未查：与池中其它 orange3 题（例如环境卡提到的 `9b5494e2`）的关系。

## 5. 问题清单

| # | 问题 | 影响 | 证据级别 |
|---|---|---|---|
| P1 | 题面 "Example Buggy Code" 就是 gold 实现（逐行相同），标为 buggy 却输出期望值，与 base 代码不符 | 可直接复制拿 1 分；作能力诊断、训练或评测会虚高。期望行为本身写得清楚，矛盾不至于让解题者误解语义 | 脚本静态比对 + 真实 actor 条件执行（devcheck `mcve_statement_code`、`mcve_repo_function`） |
| P2 | 没有测 widget 层三个以上、非排序类名的场景 | 低：helper 修好后，唯一调用者自然修好 | 静态推断 |
| P3 | 隐藏测试依赖仓库 base 版测试辅助 `Orange/widgets/tests/base.py`，评分不重置 | 低：正常修复不会改它 | 静态阅读 + 环境卡描述的机制 |
| G1 | 证据缺项：真实任务消息的渲染与提示；替代解没有实跑；devcheck 与评分用的镜像构建不同；gold 对照以 root 执行 | 不影响评分结论，但限制了"actor 条件已验"能说到的范围 | 缺项 |

未发现：（对题面要求的）漏测、误拒、错误回归、开发缺口。材料错配只有题面代码块与 base 不符这一处，已并入 P1。

## 6. 暂定处置、优先下一步与建议队列

- **暂定：** 评分材料可以用：noop 0 / gold 1 稳定，目标键充分覆盖题面要求，没有非 PASSED 键的风险。按现在的题面，不列为能力探针候选；可以作易题或链路正对照，用途里标注"题面给修法（完整）"。
- **唯一优先下一步：** 请用户决定题面怎么处理，二选一：
  1. 修订公开规格：删掉或替换 "Example Buggy Code"，比如改成只调用仓库函数的用法示例，或者贴出真实的 base 实现；保留 Expected/Actual。隐藏测试和期望映射不改；修订后需要重新渲染提示，并更新、核对 `problem_statement_sha256`。
  2. 保持原样，只在用途里标注泄漏。
- **建议队列（由协调者安排）：**
  - **Q1（跨题，成本低）：** 本题的错误像是题面生成器把 gold 后像当成了 "Buggy Code"。建议对全池机械扫描一次：计算每题题面代码块与 gold `+` 行的逐行重合率，找出同类泄漏。
  - **Q2（CPU，低优先）：** 用 §2 的 numpy 逆置换替代解走一次 RH2 评分，确认非 gold 解也能拿 1 分。
  - **Q3（actor）：** 真实任务消息渲染出来后，核对提示措辞（conda、测试重置）；再测一次不带 xvfb 前缀导入 widget 模块。

## 7. 实际读取范围

- **角色与方法：**
  - `roles/reviewer_r2e.md`：全文。
  - `roles/investigator_r2e.md`：Read 工具显示了全文，包括主审步骤与边界两节；评分口径只采用"材料"和"R2E 的评分口径"两节。
  - `quality_review_protocol_20260920.md`、`r2e_environment_card.md`、`record_template.md`：全文。
  - 没读 40 项清单原文，文中编号取自协议表。
- **公开包：**
  - `user_prompt.txt`、`environment_brief.md`、`public_bundle.json`：全文。
  - `worktree_manifest.json`：结构，`export`、`initial_diff`、`untracked_*` 字段，以及相关文件条目。
  - `WT` 内：
    - `Orange/widgets/data/owcreateclass.py` 全文；
    - `Orange/widgets/data/tests/test_owcreateclass.py`，通过与隐藏测试做 diff 读取；
    - `Orange/widgets/tests/base.py:1-80`，外加测试方法 grep；
    - `Orange/widgets/tests/__init__.py`、`Orange/widgets/data/tests/__init__.py`、`Orange/widgets/__init__.py`；
    - `Orange/data/table.py`（grep）、`Orange/datasets/` 文件名；
    - `setup.cfg`、`pyproject.toml`、`tox.ini`（grep）、`run_tests.sh`、`CHANGELOG.md`（grep）；
    - 全树 grep `unique_in_order` / `first_position`。
- **私有包：**
  - `hidden_tests/test_1.py`：全文；`hidden_tests/__init__.py`：空文件。
  - `expected_output.json`、`gold.patch`、`run_tests.sh`、`revisions.json`、`run_refs.json`、`grading_bundle.json`：全文。
  - `validation_bundle.json`：截断查看。
- **运行原件：**
  - `run_refs.json` 的 6 条 current 行：账本行全部取了关键字段，其中 `ledger_r2e_all_noop.jsonl:23` 读了全文。
  - 6 份 eval log：R-f all noop 读全文，R-f all gold 读头部和 summary；另外 4 份去掉时间戳后与这两份 diff，逐字一致。
  - independent_reference：M3 两份 gold 日志的汇总行，以及账本第 7、56 行的前 600 字符。
- **devcheck：**
  - `orig/` 下：
    - `commands_with_preflight.json`、`stub_script.json`（截断）、`captures/*.out`（6 份全文）；
    - `attempt.json`（逐字段，长字段截断）、`activation_check.json`、`prelaunch.json`（前 60 行）；
    - `post_run_facts_root.txt`（前 28 行）、`devcheck_stderr.log`、`bringup_artifacts/cc_version_observed.json`；
    - `stub/requests/messages_000.json`：用户消息全文，system prompt 只做关键词检索。
  - `private_gold/private_control.json`：全文。
- **没读：**
  - OUTPUT_DIR 里的其它文件；任何 `history/`；`docs/.../r2e_env_repair_20260924/`；任何 review 目录。
  - `r2e_static_review_20260925/` 的 README、assignments.json、actor_devcheck.md；`runs/` 下的分析与汇总文件。
  - devcheck 的 `harness/trajectory.jsonl`、`harness/stderr.log`、`stub/requests/messages_001-006.json`、`stub/stub_log.json`、`stub_stdout.log`、`devcheck_stdout.json`、`private_gold/stdout.log`。
  - 账本引用的 `diagnostics.json`（远端路径）。
  - venv 里 `orangewidget/tests/base.py` 的源码：本地没有，3 个继承键的行为只从日志得知。
- **操作：**
  - 全程只读。
  - 用 `git hash-object --no-filters` 算 blob，没有写入对象库。
  - 用内存中的 python 片段做比对、抽字段。
  - 除本文件外没有写任何文件。

## 附录：运行证据索引（均为 `material=current`，配方 `r2e_derive_v1`，`env_recipe` 为 null）

| 账本行 | 候选 | 派生镜像 ID | 结果 | mem_peak_mb | 日志 |
|---|---|---|---|---|---|
| `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:23` | noop | `24840fed8928…` | 0.0，22/23，mismatch=目标键 | 2197.7 | `…/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-o_a29ba791.eval.log`（1 failed, 22 passed, 3 skipped；RC=1） |
| `runs/r2e_rf_20260923/remote/ledger_r2e_all_gold.jsonl:23` | gold `474672197e…` | `24840fed8928…` | 1.0，23/23 | 2148.3 | `…/evallog_replay-r2e-rf-all-gold-o_6a0d5a19.eval.log`（23 passed, 3 skipped；RC=0；summary 在 :101-128） |
| `runs/r2e_rf_20260923/remote/ledger_r2e_reps_noop.jsonl:4` | noop | `a013522716b2…` | 0.0，22/23 | 2155.1 | `…/evallog_replay-r2e-rf-reps-noop-_bdbfd895.eval.log`（去时间戳后与 all noop 相同） |
| `runs/r2e_rf_20260923/remote/ledger_r2e_reps_gold.jsonl:4` | gold | `a013522716b2…` | 1.0，23/23 | 2152.4 | `…/evallog_replay-r2e-rf-reps-gold-_b84ef6c6.eval.log`（与 all gold 相同） |
| `runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl:23` | noop | `24840fed8928…` | 0.0，22/23 | 2140.1 | `…/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_f5bf55c2.eval.log`（与 all noop 相同） |
| `runs/r2e_env_repair_20260924/_rerun2/ledger_gold.jsonl:23` | gold | `24840fed8928…` | 1.0，23/23 | 2139.4 | `…/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_33ac9fd3.eval.log`（与 all gold 相同） |

- 6 份日志的 sha256 都与 `run_refs.json` 记录一致。
- 独立参考（来源镜像 `sha256:7eb0b912…`，M3 runner）：`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:7,56` 两次 gold 都是 23 passed, 3 skipped。
- devcheck（镜像 `50fd6e31e77a…`，agent 身份，经 CC Bash）：`orig/captures/` 的 `r2e_preflight.out`、`env.out`、`mcve_repo_function.out`、`mcve_statement_code.out`、`test_helper.out`、`test_widget_file.out`。
- private gold 对照（同一镜像，root 身份）：`private_gold/private_control.json`，其中 `results.mcve_repo_function` 为 `([2, 3, 1], [0, 1, 2])` / `(['b', 'c', 'a'], [0, 1, 2])`。
