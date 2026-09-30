# coveragepy `f5eb5f21` 独立复核：初判（读作者材料前封存）

2026-09-30 / 独立复核者（Claude，新会话，不继承作者上下文）。

**封存声明**：本文写于阅读作者 `result.md`、`initial_judgment.md`、`evidence/`、`rh2/experiments/category3_cloud_20260929/cov_f5eb/` 中作者文件，以及 `r2e_lifecycle_20260929/results/coveragepy__f5eb…/`、`codex_reviews/` 之前，写完后不再修改。依据只有下列原件、镜像只读运行和一份上游发布包：

- 题面：`s2_r2e/ingest/public_bundles_v0.jsonl`（`problem_statement_sha256 = sha256:6a516854…`，v0 与现行一致）。
- gold：`validation_bundles_v0.jsonl`（`golden_patch_sha256 = sha256:c8fa460d…`），只在 `coverage/jsonreport.py` 的 totals 分支块里加两行：`covered_branches = self.total.n_executed_branches`、`missing_branches = self.total.n_missing_branches`。逐文件 `summary` 不动。
- 评分材料：
  - 原版（v0–v7）：隐藏测试 `test_1.py` sha256 `ee874f37…`（= 镜像内 `/r2e_tests/test_1.py`），期望映射 `9e555e51…`，4 键全 PASSED；
  - 现行（v8 起生效，v11 仍是同一内容）：`r2e-mr-053`（隐藏测试 → `73ad2f27…`）＋`r2e-mr-054`（期望映射 → `755e53ba…`，6 键全 PASSED）。
  - 读 `material_revisions_v8.json` 时看到了修订单 `purpose` 里的一句“coveragepy f5eb〔只落 R-c，C1 的 R-b 属 P5 待用户定〕”，以及两条修订的 `reason` 字段。这是现行材料的一部分，我据此知道“有个 C1 的放宽被挂为 P5”，但不知道 C1 是什么、理由是什么。
- `run_tests.sh`：`8285765f…`，`.venv/bin/python -W ignore -m pytest -rA r2e_tests`。
- 镜像 `c3keep/coveragepy_f5eb:src` = `namanjain12/coveragepy_final@sha256:fb0335af…`（与冻结摘要一致），Image ID `sha256:45810d8d…`；coverage 5.0.5a0，Python 3.7.9，CTracer。
- 上游对照（只作佐证，不是公开依据）：PyPI `coverage-5.1.tar.gz`（sha256 `f90bfc4a…`，2020-04-12 发布）。

原版隐藏测试 = base 公开 `tests/test_json.py` 只在 `test_branch_coverage` 的 **totals** 里多了 `covered_branches: 1`、`missing_branches: 1`；逐文件 `summary` 与公开测试逐字相同。

## (a) 题面核心要求

标题：JSON 报告缺少分支属性。期望行为：开启分支覆盖时，`coverage.json` 的 `totals` 应包含 `covered_branches` 与 `missing_branches`，“providing detailed branch coverage information”。

按题面一般表述理解：

1. 数据含分支（arcs）时，`totals` 有这两个键；
2. 数值有意义：`covered_branches` 是被走过的分支目标数，`missing_branches` 是没走过的分支目标数，两者合起来等于 `num_branches`。依据：base 已有公开可见的 `Numbers.n_executed_branches = n_branches - n_missing_branches`；题面示例 1／1；XML 报告的 `branches-covered` 也是同一口径；
3. **`totals` 是全部被报告文件的汇总**。这是“totals”一词本身的含义，base 里其它 totals 键都是逐文件 `Numbers` 相加（`self.total += nums`），文本报告的 TOTAL 行同样如此。题面示例 `json_report(outfile=...)` 不带 morfs，报告全部被测文件；
4. 题面**没有提**逐文件 `summary`，也限定在“with branch coverage enabled”。

需要保持的已有公开行为：只测行覆盖时输出不变；逐文件已有键的值不变；`meta.branch_coverage` 与分支键按“数据是否含 arcs”决定（base 的 `jsonreport.py`、`summary.py`、`xmlreport.py` 都这样做）。

## (b) 现行隐藏测试断言了什么、没断言什么

| 键 | 断言 |
| --- | --- |
| `test_branch_coverage`（目标） | 题面示例 `a.py`，**整个 JSON 字典精确相等**：totals 含 1／1；逐文件 `summary` 必须与旧格式完全相同，即**不能**出现这两个键 |
| `test_simple_line_coverage`、`test_context_*`（回归） | 行覆盖模式整字典相等：任何位置都不能出现分支键 |
| `test_branch_totals_count_branch_arcs`（v8 新增，下称 K1） | 单文件 BRANCHY：totals 为 `num_branches` 6、`num_partial_branches` 0、covered 4、missing 2。能区分“missing”与“partial”（h 的 `if` 从未执行） |
| `test_branch_totals_from_saved_branch_data`（v8 新增，K2） | 先存数据，再用不带 `branch` 配置的新 `Coverage` 读回后出报告：`meta.branch_coverage` 为 True，totals 4／2。拦住按 `config.branch` 判断的写法，对应 `coverage run --branch` 后单独 `coverage json` 的常用流程 |

**没断言**：

- **多文件汇总**：所有测试都只报告一个模块（`json_report(mod)`），totals 与该文件数值恒等。只取某一个文件数值的写法挡不住；
- 逐文件 `summary` 里这两个键的值（现在是禁止出现）；
- 真正的 CLI 路径（K2 用 API 模拟）；
- 文件顺序、含无分支文件的组合。

## (c) 题面示例能否在 base 上复现

能。题面示例原样（`branch=True`、`start/stop` 之间执行代码、`json_report(outfile='coverage.json')`）在 base 上生成的 totals 没有这两个键。附带现象：示例不带 morfs，镜像 venv 的 `_distutils_hack/__init__.py`、`_virtualenv.py` 也被测量并进入报告。这不影响评分，隐藏测试都带 morfs。题面的 Error Message 是隐藏测试整字典断言的缩写。

## (d) 合理实现与隐藏测试是否都接受

| 合理实现 | 原版 | 现行 v8 |
| --- | --- | --- |
| gold：在 totals 块用 `self.total` 的两个属性 | 1（已跑） | 1（已跑） |
| `rv_sym`：totals 与逐文件 `summary` 都加（上游 5.1 发布版的写法） | **0（已跑）** | **0（已跑）** |
| 另设累加器 `+=`、按 XML 报告的 `branch_stats()` 汇总等，只改 totals | 预计 1 | 预计 1 |

`rv_sym` 两版都失败在 `test_branch_coverage` 的逐文件 `summary` 多出两个键。它在多文件、读回、CLI 各场景下 totals 都与 gold 相同（私有探针：两文件 8／1／5／3，顺序对调相同，读回相同）。

## (e) 可能拿到 1 的错误实现

| 错误候选 | 违反的公开要求 | 原版 | 现行 v8 |
| --- | --- | --- | --- |
| `wr_loopvar`：totals 用循环结束后残留的 `analysis.numbers`，即最后一个文件的数值 | totals 不是汇总：两文件探针得 covered 4、missing 2，应为 5、3 | 1（已跑） | **1（已跑）** |
| 只取第一个文件；给 `Numbers` 新增字段但 `__add__` 里写成赋值 | 同上 | 预计 1 | 预计 1 |
| missing 用 `n_partial_branches` | 从未执行的分支行不计入 missing | 预计 1 | 预计 0（K1） |
| 按 `self.config.branch` 判断 | `coverage run --branch` 后单独 `coverage json` 时缺键 | 预计 1 | 预计 0（K2） |
| 硬编码 1／1 | 与输入无关 | 预计 1 | 预计 0（K1） |

## 初判严重度（§4，D1 严格版）

- 第 1 步：核心要求有直接断言 → 不命中。
- 第 2 步：v8 已补 BRANCHY 这个非示例程序；但所有断言仍是单文件报告，“totals 汇总多文件”这一实例没有断言。
- 第 3 步：在 gold 修改处把 `self.total` 换成最后一个文件的 `Numbers`（作用在无关对象上），现行材料得 1 → **S1（T2b）**。
- 第 4 步：`wr_loopvar` 是已构造候选，得 1，且在“多文件 totals”这一同一核心要求的主路径实例上违例 → **S1**。

初判去向：**S1 → R-c**，补一个多文件报告的 totals 断言。两个文件数值要不同，让“只取首个”“只取末个”“取最大”都失败。a.py＋BRANCHY 用 gold 私有探针得 8／1／5／3，与报告顺序无关，读回后也相同。

## 初判：逐文件 `summary` 问题怎么归类

事实：`rv_sym`（上游 5.1 发布版同款）在原版与 v8 下都是 0。原因只有一个：逐文件 `summary` 多了两个键。

两种读法各自的依据：

- **只改 totals**：题面三处都说“in the totals”，Error Message 也只显示 totals；旧公开测试整字典固定了逐文件格式。但同一个旧测试也固定了旧 totals，而题面正是要改 totals。所以“整字典不许多键”是断言写法，不是格式承诺。XML 报告把 covered 计数只放在根节点，可算弱先例。
- **两处都加**：base 的 JSON 里逐文件 `summary` 与 `totals` 键集完全一致，两个分支键在同一个 `has_arcs()` 条件下同时加入。标题泛称“JSON coverage report missing branch attributes”。上游 5.1 发布版正是两处都加，CHANGES 写“The JSON report now includes counts of covered and missing branches”，只作佐证。

**初判倾向：不属于 P5 的“任务目标分歧”，而是 T1，可在 R-b 模板内处理。** 理由：

- 确定需求（totals 的两个键及其数值）两种实现都满足；
- 分歧只在题面没有提到的附加范围上；
- 测试惩罚的是更一致、更完整的写法；
- 统一标准 v1 的复核来源 F2 第 4 条原文是“两种实现都符合确定需求时可以都接受”。它禁止 OR 的，是“合并还是替换”这类核心行为本身相反的情形。

对照 dask-9378 的先例，那里判 P5 第一分支的理由之一是“测试并不惩罚两处都改”；本题恰好相反。

修法：R-b 把 `test_branch_coverage` 的逐文件断言改为三条：旧键逐项相等；只允许多出这两个键；多出时数值必须正确（1／1）。totals 与行模式断言不变。

我也承认 P5 第二分支的读法可以成立，因为题面明确限定了 totals。若按 P5 交用户，凡是继续拒绝 `rv_sym` 的选项，都必须同时用 R-f 在题面写明逐文件 `summary` 不变。否则上游发布版写法得 0，而解题者没有任何公开信号。最终意见待核对作者依据后给出。

## 未查（写初判时）

- 另造合理实现与错误候选的实际评分；
- 作者的 R-c v2、R-b v2、题面草案、选项定义；
- 真实 CLI 下各候选的行为（只跑了 gold、`rv_sym`、`wr_loopvar`、base 的探针）；
- R2E 正式评分链、派生镜像、解题身份 UID 54321。
