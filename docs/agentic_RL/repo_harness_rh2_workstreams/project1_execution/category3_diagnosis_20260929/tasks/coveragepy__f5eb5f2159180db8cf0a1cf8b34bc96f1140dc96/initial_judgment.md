# coveragepy__f5eb5f21：读历史前的初判（封存）

2026-09-30 / Claude（第3类第二批主审子代理）。按 v1 §7.1 第 3 步封存：写完不再修改。此时只读了原件，还没读 R2E 线的题卡、修订计划、复核和公开读者稿。

**已读的原件**：
- `s2_r2e/ingest/` 四个包：题面、gold、评分包（run_tests.sh、期望 6 键、`material_revisions: [r2e-mr-053, r2e-mr-054]`）、环境包；
- 修订单 v8–v11 中本题两条（v8 起逐字不变，当前封板 pins v12 引用 v11）；修订后文件 `revisions/files/<iid>/`；
- 镜像 `c3keep/coveragepy_f5eb:src` 中的原隐藏测试 `/r2e_tests/test_1.py`（sha256 `ee874f37…`，与 r2e-mr-053 的 `sha256_before` 一致）；
- base 源码：`coverage/jsonreport.py`、`results.py`、`xmlreport.py`、`summary.py`，`doc/branch.rst`、`doc/cmd.rst`，公开测试 `tests/test_json.py`。

**唯一读到的历史痕迹**：修订单 v8 的 `purpose` 字段写着“coveragepy f5eb〔只落 R-c，C1 的 R-b 属 P5 待用户定〕”。下面的判断是我对原件的独立判断，与这条记录的出入在读历史后再对照。

## 1．公开目标

题面只要求一件事：开启分支覆盖时，JSON 报告的 `totals` 要带 `covered_branches` 和 `missing_branches`。

- 数值口径有公开依据，按分支去向（arc）计数，`covered + missing = num_branches`：
  - 题面错误信息里的示例是 `covered_branches: 1, missing_branches: 1`，对应 base 已有的 `num_branches: 2`；
  - XML 报告的 `branches-covered` 就按去向计数；
  - `doc/branch.rst` 写明“each branch destination”是一个执行机会。
- 题面对每个文件的 `summary` 一句没提：既没要求加，也没说不能加。
- 行覆盖模式（`branch=False`）不在题面范围内，题面限定“with branch coverage enabled”。base 的 `num_branches` 等字段也只在 `has_arcs()` 为真时输出。

## 2．测试与公开目标的对应

原测试 4 键，都走 `_assert_expected_json_report`，对整份报告做字典相等比较（`==`）。

- `test_branch_coverage`：`totals` 要求两个新字段为 1／1，这一部分有依据；但它同时要求每个文件的 `summary` **恰好**是旧字段集合，不能多出 `covered_branches`、`missing_branches`。
- 另外 3 键（行模式、contexts）与公开的 `tests/test_json.py` 逐字相同，base 与 gold 都应通过。

**疑点（T1 候选）**：
- 现象：base 的 `report_one_file` 在分支模式下给每个文件的 `summary` 也加 `num_branches`、`num_partial_branches`，与 `totals` 平行。所以一个自然的实现会把两个新字段同时加到每个文件和 `totals`，但它会在 `test_branch_coverage` 上失败。
- “每个文件不能有这两个字段”没有公开依据：
  - 题面没有这样说；
  - 公开 `tests/test_json.py::test_branch_coverage` 的旧写法同时锁定了旧的 `totals`，而正确修复必然让这条公开测试失败（P6），所以它不能作为“每个文件不能变”的依据。
- 初步看法：这不是 P5 的两种目标读法，而是测试多了一条题面之外的形状约束，应走 **R-b**。
  - 目标只有一种读法，`totals` 必须带两个字段；
  - 每个文件的 `summary` 是题面没有约束的实现细节；
  - 放宽后，“只加 `totals`”与“两处都加”都能通过，不会把相反的输出用“或”并起来，因为只加 `totals` 的读法并不禁止多加字段。
  - 窄放宽：在 `test_branch_coverage` 里允许每个文件的 `summary` 多出这两个字段，出现时值必须正确（此例为 1／1）；其余字段仍逐项精确比较。

**行模式 3 键的精确比较**：有公开依据，保留。依据是题面范围、base 的 `has_arcs()` 门控，以及公开测试在 base 上本来就通过。行模式下也输出这两个字段（例如 0）的候选，被拒是正确的。

## 3．已落地的 R-c（r2e-mr-053／054）

新增 2 键：
- `test_branch_totals_count_branch_arcs`：用非示例程序，6 个去向、4 个走到、2 个没走到、0 个部分分支；
- `test_branch_totals_from_saved_branch_data`：先保存，再由没有 `branch` 配置的新对象读数据出报告。

初判两键都有依据：
- 第一键按 D1 严格版补了非示例实例。它能挡住硬编码 1／1、两字段对调、`covered = num_branches - num_partial`、按行而不是按去向计数这几类候选，因为示例里 1＝1、部分分支数也是 1，这些错误写法在示例上都碰巧对；
- 第二键依据是 base 的 JSON、XML、文本报告都用 `data.has_arcs()`，而不是用 `config.branch`，也对应 CLI 常见用法 `coverage run --branch` 后接 `coverage json`。

## 4．要查的反例与计划

- **退化探测**（§4 第 3 步）：在 gold 位置写硬编码 1／1、`n_branches - n_partial`／`n_partial`，以及字段对调。预期：原测试得 1，当前材料得 0。
- **合理但与 gold 不同**：
  - `files_too`（两处都加）：原测试和当前材料预期都是 0，这正是误拒的疑点；
  - `branch_stats`（从 `analysis.branch_stats()` 求和）：预期 1；
  - 按文件累加：预期 1。
- **可能的新缺口**：
  - `last_file_only`：`totals` 只取最后一个文件的数。现有测试每次只报告一个文件，所以预期放过，需要多文件实例；
  - `need_branches`：`num_branches == 0` 时省略字段。分支模式下文件没有分支属于边缘情形，预期 T3；
  - `line_mode_too`：行模式也输出这两个字段。预期被行模式 3 键拒绝，属于正确拒绝；
  - `files_wrong`：每个文件的字段值写错。放宽后要能拒绝，所以放宽时出现就必须校验值；
  - `config_branch`：用 `config.branch` 门控。预期被第二键拒绝。
- **上游对照（佐证，不作公开依据）**：coverage 5.1 发布版的 `jsonreport.py` 是否也给每个文件的 `summary` 加了这两个字段。如果加了，“两处都加”就是上游最终写法，误拒更实在。
