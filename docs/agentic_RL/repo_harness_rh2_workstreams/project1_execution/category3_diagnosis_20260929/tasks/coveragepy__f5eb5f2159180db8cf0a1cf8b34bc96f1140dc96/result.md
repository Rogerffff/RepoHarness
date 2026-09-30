# R2E coveragepy__f5eb5f21：第3类范围核定结果

2026-09-30 / Claude（第3类第二批主审子代理）。

- 原分类：第3类“公开目标与验收关系需核定”（范围题）。
- 工作清单登记的下一步：“明确允许的字段范围，再按已有窄 R-b 草案或保留范围完成验收”。
- 读历史前的初判已封存：[initial_judgment.md](initial_judgment.md)。
- **本页所有分数都是私有模拟**，不是 R2E 正式评分链。

**结论：仍有具体问题，需要用户决定。** 每文件 `summary` 能不能也带 `covered_branches`、`missing_branches` 这两个计数，属于 P5 第二分支：两种读法都有公开依据，交负责人转用户。与读法无关的部分都已明确。修订草案按 A 与 B／C 各备一版（B 另有题面草稿），都做完了私有模拟验收。

- **字段范围核定**（§1）：
  - `totals` 两键的存在、计数口径、按数据门控：有公开依据，保留；
  - 多文件累加：有公开依据，但现行材料没测，本页补上；
  - 行模式不出现分支键、不另加其它新键：有公开依据，保留精确比较；
  - 只有“每文件 `summary` 的这两个键”两边都有依据，属 P5。
- **P5 的处理**（§2）：同意 Codex 的归类，这不是 R-b 模板内的放宽。
  - 本次补查了上游 5.1 发布版和 XML 报告的层级，都不能把任一读法的依据降为零；
  - 但佐证了 C1 是合理实现：它的 `jsonreport.py` 与上游 coverage 5.1 发布版逐字相同。
  - 建议选 A（R-b v2），这只是建议，由用户定。
- **新发现的 S1，与 P5 无关**（v1 §4 第 4 步）：
  - 候选 `LF` 是 A1 的一字之差：逐文件计数把累加写成了赋值，`totals` 只剩最后一个文件的数；
  - 它在原版、现行 v8 材料、历史窄 R-b 草案上都得 1；
  - 两文件报告里它给出 1/1，而 `num_branches` 是 8；API、保存后读回、CLI 三条路径都一样；
  - 修法：R-c v2 新增一键，覆盖两文件的 `totals` 汇总。R2E 线原先把多文件汇总登记为 T3，本页改判为 S1，理由见 §4。
- **历史窄 R-b 草案有一个缺口**：
  - 候选 `FC` 在每文件 `summary` 里写“累加到当前文件为止的总数”，单文件时恰好对，所以在历史草案上得 1；
  - 修法：R-b v2 在多文件测试里加每文件核对。
- **私有模拟**（14 个候选 × 5 版材料，另有 2 版以 uid 54322 重跑）：
  - R-c v2 与 R-b v2 下：gold、A1 都是 1，noop 与 9 个已知错误候选（D0、C2、W2、C3、LF、C1swap、FC、LM、XP）都是 0；
  - C1 在 R-c v2 下为 0，在 R-b v2 下为 1，这正是 P5 的分歧点；
  - `NB`（零分支时省略两键）两版都是 1，登记为 T3。

## 1．公开要求与字段范围

题面（public bundle，`problem_statement_sha256` `6a516854…`）要求：开启分支覆盖时，JSON 报告的 `totals` 要带 `covered_branches` 和 `missing_branches`。

- 题面在描述、期望、实际三处都只点名 `totals`；
- 错误信息是 pytest “Differing items” 的一行，只列了 `totals`。我在 noop 上跑原隐藏测试，得到的正是这一行，另附 “Omitting 2 identical items”（`evidence/matrix_v1/base/h0_orig.out`）。

隐藏测试里每条字段／断言的依据：

| 字段或断言 | 所在测试 | 公开依据 | 核定 |
| --- | --- | --- | --- |
| 分支模式下 `totals` 有两键 | BC、K1、K2、K3 | 题面三处 | 有依据，保留 |
| 两值按分支去向计数，`covered + missing = num_branches` | K1（BRANCHY 6/0/4/2）、K3 | `results.py:35-36`、`:201-204`；`doc/branch.rst:45-46`（“each branch destination”）；XML 的 `branches-covered`；题面示例 1/1 与已有的 `num_branches` 2 | 有依据，保留 |
| 按数据 `has_arcs()` 门控（先 `coverage run --branch`，再单独 `coverage json`） | K2 | `jsonreport.py:38`、`:59`、`:94`；`coverage json` 没有 `--branch` 选项（`cmdline.py:374-388`） | 有依据，保留 |
| **多文件时 `totals` 按文件累加** | 现行材料**没有**；本页新增 K3 | `totals` 已有各键都由 `self.total += nums` 按文件累加；文本报告只在多于一个文件时打印 TOTAL 行（`summary.py:115-116`）；XML 根元素计数按包汇总 | 有依据，**补断言**（R-c v2） |
| 行模式下 `totals` 与每文件都不出现分支键 | LINE、CTX_R、CTX_NR 的整字典比较 | 这 3 个测试与公开 `tests/test_json.py` 逐字相同，base 与任何正确修复都通过；题面限定 “with branch coverage enabled”；`has_arcs()` 门控 | 有依据，保留 |
| 不另加题面没点名的键（如分支覆盖率） | BC 的整字典比较 | 题面只点名两个键；公开读者也写了“不建议顺手扩展”（`public_read.md` §2）。`doc/branch.rst:52-54` 说 JSON 含 “separate … branch coverage percentages”，这是 base 原有的文档与实现不符，不是本题要求 | 有依据，保留（登记为 P4 注记） |
| **分支模式下每文件 `summary` 恰好是原来 7 键** | BC（`test_1.py:35` 整字典相等、`:50-58`） | 两种读法都有依据，见 §2 | **P5，交用户** |
| `meta`、行号列表、`percent_covered` 等其余输出 | BC | 旧行为 | 保留 |

键名简写：
- BC = `test_branch_coverage`；LINE = `test_simple_line_coverage`；CTX_R／CTX_NR = `test_context_relative`／`test_context_non_relative`；
- K1 = `test_branch_totals_count_branch_arcs`；K2 = `test_branch_totals_from_saved_branch_data`（这两键由 R2E 线 R-c 加入，即现行材料）；
- K3 = `test_branch_totals_add_up_across_files`（本页新增）。

## 2．需要用户决定：每文件 `summary` 能不能也带这两个计数（P5 第二分支）

### 2.1 两种读法与依据

| | 读法 K：只改 `totals`，每文件保持原来 7 键 | 读法 S：每文件也可以带这两个计数 |
| --- | --- | --- |
| 公开依据 | ① 题面三处只点名 `totals`；错误信息的 “Differing items” 只有 `totals` 一项。② 公开 `tests/test_json.py:35` 做整字典相等，`:50-58` 写明分支模式下每文件 7 键。它的 `totals` 部分注定过时（P6），但每文件部分在 base 和 gold 下都成立。③ 惯例：题面没要求改的输出不改（仓库里没有成文规定） | ① `jsonreport.py:59-63` 与 `:94-98`：已有的两个分支计数在 `totals` 和每文件里成对输出；每文件还有与 `totals` 同名的行计数。② 文本报告的每文件行与 TOTAL 行给出同样的分支列（`summary.py:84-86`、`:116-120`）。③ 没看过隐藏测试的公开读者把这一点判为“多种合理解释”（`public_read.md` R7），真实解题者会分成两种做法 |
| 不算依据的佐证 | — | 上游 coverage 5.1 发布版（PyPI sdist，sha256 `f90bfc4a…`，2020-04-12）：`jsonreport.py` 与“base＋C1”逐字相同（`evidence/upstream_check/c1_vs_upstream51.txt`）；它的 `test_json.py` 每文件 `summary` 也有这两键；CHANGES 5.1 写 “The JSON report now includes counts of covered and missing branches”。`ea6906b0` 的初态也是这种形态（X1）。这些解题者都看不到 |
| 中性材料 | XML 报告的计数属性（`lines-*`、`branches-*`）只在根元素，每个类只有比率（`xmlreport.py:118-128`、`:211-216`）。行计数与分支计数一视同仁，不支持任何一方 | 同左 |

**为什么不按 R-b 直接放宽**：
- R-b 用于“没有公开依据的实现约束”，而每文件 7 键这一约束有依据（K 的 ①②），只是依据弱；
- 放宽等于替用户选了“允许”。这与 Codex 的判断一致（`r2e_lifecycle_20260929/codex_reviews/review_revision_coveragepy_f5eb.md` §3）；
- 我初判时倾向 R-b（见 initial_judgment.md §2），读了 Codex 的论证、补查上游和 XML 之后，改为同意 P5。

**为什么也不是 P5 第一分支**（只有测试的读法有依据，走 R-f）：读法 S 的 ①② 是 base 代码和文档化的其它报告里的现成结构，不能算“没有依据”。

### 2.2 选项与影响

三个选项都含 R-c v2（§5）；对 `totals` 的要求（两键、计数口径、门控、多文件累加）同样严格。

| | A：R-b v2（允许每文件带这两键，成对且值对） | B：R-f，题面补一句“每文件不变” | C：维持，不改题面 |
| --- | --- | --- | --- |
| 隐藏测试 | `hidden_test_1_rb2.py`（7 键） | `hidden_test_1_rc2.py`（7 键） | 同 B |
| C1（＝上游 5.1 写法） | **1** | 0，正确拒绝 | 0，有争议的拒绝 |
| 已知错误候选（含 FC、C1swap、LF） | 全 0（私有模拟） | 全 0 | 全 0 |
| 额外工作 | 正式评分加跑 C1、C1swap、FC | 新公开读者验收修订题面；逐行核对；Codex 复核题面；标明题面版本 | 预登记探针分析规则：只错 BC、差异只在每文件多两键的结果单列；每文件两值另用多文件夹具私核 |
| 训练信号 | 上游式对称实现得 1 | 学“题面没说的输出不改” | C1 型解稳定得 0；X1（`ea6906b0`）可能让这类解更常见（推测，未实测） |

- B 的题面句子沿用 R2E 线草稿（`revision_plan.md` §6.4）：“The per-file `summary` entries under `files` are not part of this change and keep their current keys.” 已做成 `statement_text_replace` 草稿（`revision_draft_statement_B.json`，修订后题面 `revised_statement_B.txt`，`6a516854…` → `170ad612…`），未经新公开读者验收。
- **不可选**：去掉整字典比较，或接受任意额外键。那会拿掉行模式形状与其余旧字段的保护（§1）。
- **不裁定时的默认**：本题只作问题定位，不进能力比较，也不标 `probe_ready`（沿用 Codex 意见）。R-c v2 与裁定无关，可以先落地（§5.3）。

**建议（不是决定）：选 A。** 理由：
1. 三个选项对核心要求同样严格；
2. C1 是上游实际发布的写法，拒绝它等于惩罚一个更完整的正确解；
3. R-b v2 校验值，补上多文件核对后，9 个已知错误候选都不能通过；
4. 不改题面，不需要新公开读者。

**反方理由也成立**：R-b 模板本来是给“没有依据的约束”用的，这里的约束有弱依据。如果用户更看重“题面没要求的输出不改”这一训练信号，选 B。

## 3．实测（全部为私有模拟）

**环境**：
- 镜像：`c3keep/coveragepy_f5eb:src`，即 `namanjain12/coveragepy_final@sha256:fb0335af…`，与冻结摘要一致；image ID `45810d8d…`；
- Docker 29.3.1，overlay2；
- 每个候选一个全新、断网、root 的一次性容器，由 `semantic_control.py`（`b8cce4c3…`）驱动，驱动脚本为 `rh2/experiments/category3_cloud_20260929/cov_f5eb/run_matrix.py`。

**评分方式**：
- 运行评分包的 `run_tests.sh`（`8285765f…`，带 `-n3`）；
- 用 `grade_r2e.py`（RH2 移植的上游 `parse_log_pytest`＋`prime_calculate_reward`）逐键对照期望映射；
- 所有运行都解析到全部期望键，没有多余键。

**身份**：R-c v2 与 R-b v2 另以 uid 54322 重跑，14 个候选的逐键结果与 root 完全相同。
- 这是近似做法：在一次性容器里对 `/root` 做 `chmod 755`，让非 root 身份能用解释器；
- 正式派生镜像的做法是搬迁解释器，两者不同。

**材料版本**：

| 简称 | 文件（`rh2/experiments/category3_cloud_20260929/cov_f5eb/`） | sha256 | 键数 |
| --- | --- | --- | --- |
| 原版 | `hidden_test_1_original.py`（镜像 `/r2e_tests`） | `ee874f37…` | 4（`9e555e51…`） |
| 现行 v8 | `hidden_test_1_v8_rc.py`，即 r2e-mr-053/054。修订单 v8–v11 中逐字不变，封板 pins v12 引用 v11 | `73ad2f27…` | 6（`755e53ba…`） |
| 历史 R-b | `hidden_test_1_hist_rb.py`，由 R2E 线 `revision_draft_rb.json` 重放 | `f73a7561…` | 6 |
| **R-c v2** | `hidden_test_1_rc2.py`（本页，选项 B、C 用） | `2cbeb5f2…` | 7（`333b4a68…`） |
| **R-b v2** | `hidden_test_1_rb2.py`（本页，选项 A 用） | `b1d83e2b…` | 7（同上） |

**候选与得分**（`evidence/matrix_v1/grades.jsonl`；括号内是失败的键）：

补丁都在上述目录。gold 取自 validation bundle，sha256 等于 `golden_patch_sha256`。R2E 线的 7 个补丁与 `r2e_lifecycle_20260929/results/<iid>/cands/` 中的文件逐字节相同；其中 C1swap 只有 R2E 线的试跑，其余 6 个在 v8 上正式评分过。

| 候选 | sha256 | 来源 | 做法 | 原版 | 现行 v8 | 历史 R-b | R-c v2 | R-b v2 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base（noop） | — | — | — | 0（BC） | 0 | 0 | 0 | 0 |
| gold | `c8fa460d…` | 参考修复 | `totals` 加两行 | 1 | 1 | 1 | **1** | **1** |
| A1 | `73da109a…` | R2E 线 | 逐文件累加 `branch_stats()` | 1 | 1 | 1 | **1** | **1** |
| C1 | `08b92222…` | R2E 线 | 每文件也加两键（＝上游 5.1） | 0（BC） | 0（BC） | 1 | **0**（BC） | **1** |
| C1swap | `6389c07a…` | R2E 线 | C1，但每文件两值对调 | 0 | 0 | 0（K1） | 0（BC） | 0（K1、K3） |
| FC | `e62545b0…` | 本页 | C1 式，每文件写累计到当前文件的总数 | 0（BC） | 0（BC） | **1** | 0（BC） | 0（K3） |
| D0 | `1644ae7c…` | R2E 线 | 硬编码 1/1（§4 第 3 步退化） | **1** | 0 | 0 | 0 | 0 |
| C2 | `85d59dd2…` | R2E 线 | 用部分分支口径 | **1** | 0 | 0 | 0 | 0 |
| W2 | `5515226b…` | R2E 线 | 两值对调 | **1** | 0 | 0 | 0 | 0 |
| C3 | `55e34064…` | R2E 线 | 按配置 `branch` 门控 | **1** | 0（K2） | 0（K2） | 0（K2） | 0（K2） |
| **LF** | `a9e10822…` | 本页 | A1 的累加写成赋值，`totals` 只剩最后一个文件 | **1** | **1** | **1** | 0（K3） | 0（K3） |
| NB | `07d0b1ff…` | 本页 | 没有任何分支时省略两键 | 1 | 1 | 1 | 1 | 1 |
| LM | `5b799eb6…` | 本页 | 行模式也输出两键（0/0） | 0（LINE、CTX×2） | 0 | 0 | 0 | 0 |
| XP | `90a833bb…` | 本页 | `totals` 另加 `percent_covered_branches` | 0（BC） | 0 | 0 | 0 | 0 |

**与正式评分的一致性**：现行 v8 一列中 gold、A1、noop、D0、C2、W2、C3、C1 的得分，与 R2E 线 v8 正式评分（`probe_card.md` 第 1 条）逐项相同；原版一列与其修订前的正式账本（D0、C2、C3 为 1，C1 为 0）相同。

**失败位置核对**：
- base 在 K3 上先通过两个锚点（`num_branches == 8`、`num_partial_branches == 1`），到 `covered_branches` 才出 `KeyError`，说明锚点是 base 已有的行为；
- LF 在 K3 的 `assert 1 == 5` 处失败（`rc2` 第 245 行）；
- FC 在 R-b v2 的每文件核对处失败，`(5, 3) == (1, 1)`（第 269 行）；
- C1 在 R-c v2 上只错 BC，差异只在 `files`。

**行为矩阵**（`probe_matrix.py`，结果在各候选的 `probe.out`，汇总在 `evidence/matrix_v1/summary_table.json`）：

期望值不取自 gold：BRANCHY 为 6/0/4/2；题面示例文件为 2/1/1/1；两文件合计 8/1/5/3。同一数据的 XML 报告不经过 `jsonreport.py`，所有候选下都给出 `branches-valid="8" branches-covered="5"`。

| 情形 | gold、A1、C1 | LF | C3 | FC（每文件） | NB | LM | D0／C2／W2 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 单文件，进程内 | 4/2 | 4/2 | 4/2 | 4/2 | 4/2 | 4/2 | 1/1／6/0／2/4 |
| 两文件，进程内 | 5/3 | **1/1** | 5/3 | 主模块 **5/3**（应为 1/1） | 5/3 | 5/3 | 1/1／7/1／3/5 |
| 两文件，保存后由不设 `branch` 的新对象读回 | 5/3 | **1/1** | **缺键** | 同上 | 5/3 | 5/3 | 同上 |
| 两文件，CLI：`coverage run --branch` 再 `coverage json` | 5/3 | **1/1** | **缺键** | 同上 | 5/3 | 5/3 | 同上 |
| 分支模式、零分支 | 0/0 | 0/0 | 0/0 | 0/0 | **缺键** | 0/0 | 1/1／0/0／0/0 |
| 行模式，两文件 | 无分支键 | 无 | 无 | 无 | 无 | **0/0** | 无 |

C1 在两文件时每文件为 4/2、1/1，是正确的。

**公开测试** `tests/test_json.py`：
- base：4 passed；
- 12 个改了 `totals` 的候选：都是 `test_branch_coverage` 失败、其余 3 个通过，即 P6：任何正确修复都会让这条公开测试失败；
- LM：4 个全部失败。

**上游对照**（佐证，不作公开依据）：`evidence/upstream_check/` 保存了 PyPI 记录、sdist 摘要，以及 5.1 的 `jsonreport.py`、`test_json.py` 与 CHANGES 摘录。

## 4．判定（v1 §3–§5）

- **§4 第 1 步**：核心要求（分支模式下 `totals` 两键）有直接断言，即 BC、K1、K2。
- **§4 第 2 步**（D1 严格版）：原版只用题面示例值 1/1，判 S1（T2c）。现行 v8 的 K1 已补上非示例实例，**已处理**。
- **§4 第 3 步**：退化候选 D0 在原版得 1，判 S1（T2b）；现行 v8 为 0，**已处理**。
- **§4 第 4 步**：
  - C2、C3、W2：原版得 1，现行 v8 都为 0，**已处理**。
  - **LF：新 S1。** 现行 v8 与历史 R-b 草案都得 1，但它在“两文件的 `totals`”这一同一核心要求的实例上违反要求：`covered + missing = 2`，而 `num_branches = 8`；API、保存后读回、CLI 三条路径都是这样。这不是边缘输入：
    - `totals` 本来就是为了汇总多个文件；
    - 文档化的 `coverage json` 会报告全部被测文件；
    - 题面示例 `json_report(outfile=...)` 没传 `morfs`；
    - 文本报告只有多于一个文件时才打印 TOTAL 行。

    R2E 线把它登记为 T3（`card.md` I9，复核 `review.md` 第 80 行），理由是风险低、改夹具要重新核值。现在有了得 1 的具体候选，而且两文件的值已由 XML 独立核对，按严格版改判 S1，修法见 §5（R-c v2）。
  - **NB：T3。** 只在“开启分支覆盖、但所有文件合计零个分支去向”时缺键，属边缘输入，登记，不补断言。
- **T1／P5**：C1 被 BC 拒绝，属 P5 第二分支（§2），交用户。
- **R-b 草案自身的缺口**：FC 在历史窄 R-b 下得 1。这只在选 A 时相关，R-b v2 已补。
- **沿用的登记**（R2E 线已登记，本次未改）：
  - P6：公开 `test_branch_coverage` 锁定旧 `totals`；
  - P4：题面说的 AssertionError 在 base 的公开测试上不出现，示例里的 “execute some code” 是占位；另加一条：`doc/branch.rst:52-54` 与实现不符（§1）；
  - X1：`97997d2c` 与本题初态逐字节相同；`ea6906b0` 的初态含本题答案，而且是 C1 形态；
  - G1：无。gold 在多文件、读回、CLI 各情形下都正确，只是不给每文件计数。
  - 共享控制面：隐藏测试依赖候选可改的 base 测试辅助（A 线清单 #31）。K3 仍只用 `make_file`、`start_import_stop`，暴露面不变。

## 5．修法与交接（R2E 材料修订机制）

### 5.1 R-c v2（三个选项都需要）

- **草案**：`rh2/experiments/category3_cloud_20260929/cov_f5eb/revision_draft_rc2.json`，用 `_build_materials.py` 生成。
- **隐藏测试条目**（`hidden_test_text_replace`，`test_1.py`，`ee874f37…` → `2cbeb5f2…`）：
  - 第 1 处 edit 与 r2e-mr-053 逐字相同；
  - 第 2 处在 K2 之后新增 K3：`branchy_sum.py` 为 BRANCHY，`branchy_sum_main.py` 先 import 它，再跑题面的单分支示例；
  - 两文件一起测量，用 `json_report([main, main.branchy_sum])` 出报告，断言：文件恰好这两个；`num_branches == 8`、`num_partial_branches == 1`（锚点，base 已有行为）；`covered_branches == 5`、`missing_branches == 3`。
- **期望条目**（`expected_file_replace`，`9e555e51…` → `333b4a68…`）：4 → 7 键，新增 K1、K2、K3，都是 PASSED；无改、无删。
- **用 RH2 的 `_apply_edits` 重放**，得到的 sha256 与文件一致。
- **落地方式**：同一题同一目标只许一条修订（`ingest_r2e_subset.py:415-418`），所以两条合并条目要整体取代 r2e-mr-053/054。
  - 草案已含正式条目的 12 个字段，并按 `_REVISION_FIELDS` 核对过；
  - `revision_id` 和 `revised_file` 的版本路径留给第2类定。若沿用现有的 `revisions/files/<iid>/` 路径，会改掉旧修订单 v8–v11 引用的文件内容。

### 5.2 R-b v2（只在选 A 时用，取代 5.1）

- **草案**：`revision_draft_rb2.json`（`ee874f37…` → `b1d83e2b…`，期望同 5.1）。
- 前 5 处 edit 与 R2E 线 `revision_draft_rb.json` 逐字相同：
  - `_assert_expected_json_report` 加 `optional_summary`；
  - BC 允许 `a.py` 的每文件 `summary` 带这两键，但必须两个都有、都为 1；
  - K1 若每文件带这两键，必须是 4/2。
- 第 6 处是 K3，另加每文件核对：带了这两键就必须是本文件自己的数，`branchy_sum.py` 为 4/2，`branchy_sum_main.py` 为 1/1。这一处用来挡 FC。
- 只放行这两个键；只带一个键或另加别的键，仍判 0。行模式、`totals` 与其余字段照旧精确比较。

### 5.3 交给第2类的清单

1. 等用户就 P5 选定 A、B 或 C。若短期不裁定，可以先落 5.1：它不替 P5 选边，C1 在 5.1 下只错 BC，与现行材料相同。选 A 后再以 5.2 取代。
2. 在 R2E 修订单中登记所选版本（5.1 或 5.2），出新 pins，重建派生镜像。
3. **正式评分**，按缺省时限逐键核对：
   - gold、A1 为 1；
   - noop、D0、C2、W2、C3、LF、C1swap、FC、LM、XP 为 0；
   - C1：选 A 为 1，选 B 或 C 为 0（只错 BC）；
   - NB 为 1（T3，可选跑）；
   - 失败位置按 §3：LF 只错 K3；C3 只错 K2；FC 在 5.1 下只错 BC、在 5.2 下只错 K3。
   - R2E 线的 7 个补丁用 `results/<iid>/cands/` 中的原件（与本页所用逐字节相同）；LF、FC、NB、LM、XP 在本页实验目录。
4. **选 B**：再登记 `revision_draft_statement_B.json`。另安排一位没看过隐藏测试与 gold 的新公开读者验收修订题面，逐行核对，Codex 复核题面，并标明题面版本。
5. Codex 复核修订条目。
6. R2E 线的准入卡相应改写，这部分不在本目录：
   - 多文件汇总从 T3 改为已由 K3 覆盖；
   - 登记 NB 为 T3；
   - 登记 LF、FC 为新的负对照。
7. 修订后仍只作“标明版本的自建题”。

## 6．当前用途（v1 §2）

| 用途 | 结论 | 条件 |
| --- | --- | --- |
| 问题定位 | yes | — |
| 能力比较 | no | 现行 v8 上 LF 型解会被误判为 1，且差 P5 裁定（09-30 按 Codex 复核更正：原版有已证的 S1 未修，不能靠事后审计进入普通能力比较；特殊诊断试解另列调查目的，不混用原分数）。R-c v2 落地并验收后重新评估 |
| 训练候选 | no | 现行材料有未处理的 S1（LF），另差 P5 裁定与 X1 训练侧登记 |
| 留出评测 | no | 同训练候选；另按 D3 以仓库划分（`ea6906b0` 与本题同侧） |

## 7．未做与证据

**未做**：
- R2E 正式评分链与派生镜像没有在云端重建；本页分数都是私有模拟。
- uid 54322 的重跑用 `chmod 755 /root` 近似派生镜像的解释器搬迁；真实 actor 开发条件（devcheck）未重跑，沿用 R2E 线在 v8 镜像上的结果。
- 未重做公开读者：按要求复用 `public_read.md`。只有选 B 才需要新公开读者。
- 本页的独立复核未做，由负责人安排。
- 多于两个文件、`--include`／`--omit` 过滤、`combine` 合并后的数据，未单独测：它们走同一累加路径，由两文件情形代表。
- 上游 5.1 与本题之间的中间提交没有逐个核对，GitHub 在云端读不到；只核对了 PyPI 发布版。

**证据**（[evidence/](evidence/)，用 `archive_evidence.py` 从 `runs/category3_cloud_20260929/cov_f5eb/` 归档）：
- `matrix_v1/<候选>/`：每个候选的 `candidate.diff`、`prep.txt`、7 份隐藏测试输出（`h0_orig`、`h1_v8rc`、`h2_histrb`、`h3_rc2`、`h4_rb2`、`h3u_rc2`、`h4u_rb2`）、`pub_test_json.out`、`probe.out`；
- `matrix_v1/grades.jsonl`：逐键评分；`matrix_v1/summary_table.json`：汇总；`matrix_v1.log`：驱动日志；
- `upstream_check/`：上游对照；
- `evidence_manifest.json`：摘要清单。

注意：`rc.json` 里的值是各命令管道末端的退出码，不代表测试结果；得分以 `grades.jsonl` 为准。

**补丁、脚本、草案**：`rh2/experiments/category3_cloud_20260929/cov_f5eb/`
- `_make_cands.py`：生成本页 5 个新候选；
- `_build_materials.py`：生成两版草案；
- `run_matrix.py`、`probe_matrix.py`、`summarize.py`、`grade_r2e.py`（抄自 `pillow3a61/`）。
