# orange3 `22e98f8f`：R-f 题面修订草案（2026-09-29，修订执行者）

**结论：**R-f 草稿已写好并在本机核对过（三处替换各恰好命中一次，修订后摘要可复现）。题面改完以后，按 v1 §4 没有"已有候选证据"的 S1，所以不附 R-c。还差三件事才能用：新公开读者验收、Codex 复核、§4 第 3 步的一次退化探测正式评分（不影响本草稿，影响"训练候选"结论）。评分材料不动，本题没有试跑。

- 草案：同目录 `revision_draft.json`（`statement_edits`、`sha256_before/after`、修订后全文）。
- 路径均相对仓库根。缩写：`PUB` = `runs/r2e_static_prep_20260924/v3/public/orange3__22e98f8f4cccc25f0d0217f9f4251b66d49b4237`，`PRIV` = 同题 `…/v3/private/…`，`DC` = `runs/r2e_actor_20260925/devcheck/orange3__22e98f8f4cccc25f0d0217f9f4251b6/orig`，`R1` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925`（首批审查）。

## 1. 问题与模板

| 项 | 内容 |
| --- | --- |
| 问题编号 | P1（公开材料直接给出完整答案），附带 P2 型的自相矛盾：标为 "buggy" 的代码照字面运行打印的就是期望值 |
| 证据 | `PUB/user_prompt.txt:14-23` 的函数体与 `PRIV/gold.patch` 的 8 行新增加未改的 `return` 行逐行相同（本机逐行比对 8/8 命中）；`DC/captures/mcve_statement_code.out:1-2` 实跑输出 `Mapping: [0, 1, 2]`，即期望值 |
| 模板 | v1 §5 R-f：第二种（删掉答案内容，换成在 base 上核实过的症状描述）为主，加第一种（改正 "Actual Behavior" 对 base 输出格式的错误陈述） |
| 评分材料 | 不变：隐藏测试、`expected_output.json`（23 键全 PASSED）、`run_tests.sh` 都不动 |

## 2. 公开依据与运行证据

| 新题面里的陈述 | 依据 |
| --- | --- |
| 例子改为导入仓库函数：`from Orange.widgets.data.owcreateclass import unique_in_order_mapping` | 函数就在 `PUB/worktree/Orange/widgets/data/owcreateclass.py:150-158`；公开测试同样这样导入（`PUB/worktree/Orange/widgets/data/tests/test_owcreateclass.py:9-12`） |
| 当前实现打印 `(array([2, 3, 1]), array([2, 0, 1]))` | 已有运行证据，逐字：`DC/captures/mcve_repo_function.out:3`。命令是 `DC/commands_with_preflight.json` 的 `mcve_repo_function`（`print(f([2, 3, 1]))`，f 即本函数），以 agent 身份（uid 54321）在派生镜像 `sha256:50fd6e31e77a…`（`rh2-r2e-derived/orange3:22e98f8f4ccc-r2e_derive_v1`）里跑，身份见 `DC/attempt.json`。此外 noop 评分日志在 `test_1.py:94` 也是 `x: array([2, 0, 1])`（`R1/results/orange3__22e98f8f…/analysis_before_history.md` 附录 A 所列 3 份）。该函数是纯 numpy，与新配方的 `+sysconfig_v1` 无关 |
| "The unique elements are correct" | 同一行输出的第一项 `array([2, 3, 1])` 等于期望的 `[2, 3, 1]`；原题面的期望与实际两处 Unique Elements 也都是 `[2, 3, 1]` |
| 期望：返回 unique `[2, 3, 1]` 与 mapping `[0, 1, 2]` | 原题面 `PUB/user_prompt.txt:31-37` 的数值，未改 |

注：上面的运行证据是带 Qt 前缀（`QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum`）跑的；不带前缀能否导入 widget 模块未核实（首批复核 `R1/results/orange3__22e98f8f…/review.md` §3 第 4 条第 5 点，只影响开发时方不方便）。题面不写运行方式，这一点不构成对 base 行为的陈述。

## 3. 具体改动（三处，均在来源 `problem_statement` 上恰好命中一次）

1. `**Example Buggy Code:**` 连同整个代码块（含 `def unique_in_order_mapping` 的 9 行实现与 "Example usage"）→ `**Example Code:**`，代码块只剩导入仓库函数与 `print(unique_in_order_mapping([2, 3, 1]))`。
2. "Expected Behavior" 的打印块 `Unique Elements: [2, 3, 1]` / `Mapping: [0, 1, 2]` → 一句按值陈述："should return the unique elements `[2, 3, 1]` and the mapping `[0, 1, 2]`."。原因：新例子直接打印返回值，保留 list 风格的打印块会暗示返回类型；题面与测试都不约定类型（隐藏测试用 `np.testing.assert_equal`），gold 返回 list、base 返回 ndarray，两者都应被接受。数值不变。
3. "Actual Behavior" 的打印块改成 base 实际输出 `(array([2, 3, 1]), array([2, 0, 1]))`，并把 "This incorrect mapping does not accurately represent" 改为 "The unique elements are correct, but the mapping `[2, 0, 1]` does not accurately represent"（句尾原文保留）。

修订后完整题面（渲染进 user prompt 的部分）：

````text
[ISSUE]

**Title:** Incorrect Mapping in `unique_in_order_mapping` Function

**Description:**
The `unique_in_order_mapping` function is intended to return a list of unique elements from the input while preserving their order of first appearance, along with a mapping that associates each original element to its corresponding unique element index.

However, when provided with the input `[2, 3, 1]`, the function incorrectly assigns the mapping indices.

**Example Code:**
```python
from Orange.widgets.data.owcreateclass import unique_in_order_mapping

print(unique_in_order_mapping([2, 3, 1]))
```

**Expected Behavior:**
For the input `[2, 3, 1]`, the function should return the unique elements `[2, 3, 1]` and the mapping `[0, 1, 2]`.
This mapping correctly associates each element in the original list to its index in the list of unique elements.

**Actual Behavior:**
With the current implementation, the example prints:
```
(array([2, 3, 1]), array([2, 0, 1]))
```
The unique elements are correct, but the mapping `[2, 0, 1]` does not accurately represent the association between the original elements and their unique indices.

[/ISSUE]
````

摘要：修订前 `sha256:0d196bc2ef106b2f053da4acdc09718b142561e72c912d9d36f86f98d0296698`（与 `PUB/public_bundle.json` 的 `problem_statement_sha256` 相同），修订后 `sha256:f8701d3a4322270fde2618cc7cfc094460c9a5f1ec874e400c5bfaeef9ec7199`。

**没有采用的写法：**
- 不把仓库实现（`np.unique` 那三行）贴进题面：解题者本来就能在仓库里读到，贴进来只是重复，还会把注意力引向"哪一行错"。
- 不补"什么输入会触发"的说明（非对合的首现顺序）：那是根因分析，属于解题内容，不是症状。
- 不加 widget 层的例子（例如类名依次为 `b, c, a`，`DC/captures/mcve_repo_function.out:4` 也有实跑结果）：解题不需要，按 R-f 边界不加。
- "Description" 里 "return a list of unique elements" 保留原文：是意图描述，不影响评分（类型不限）。

## 4. 与 R-f 边界的逐项核对

| R-f 边界 | 本草案 |
| --- | --- |
| 只做三种改动 | 是：删答案内容换症状（改动 1、3 的前半）、改正 base 输出格式（改动 3）、期望按值陈述（改动 2，数值不变，属于改动 1 的连带调整） |
| 关于 base 行为的新陈述要实跑证实 | 是：输出行逐字来自 `DC/captures/mcve_repo_function.out:3` |
| 不写隐藏测试细节 | 是，见 §5 |
| 不新增没有公开依据的要求 | 是：没有类型、文案、helper 名或新输入要求 |
| 不涉及两种读法的选择（P5） | 不涉及 |

## 5. 逐行核对（本机脚本，对来源文本与私有材料逐行比对）

- 旧题面含 gold 新增行 8 行（`first_position = {}` 至 `mapping.append(first_position[e])`）；**新题面 0 行**。
- 新题面与 `PRIV/hidden_tests/test_1.py` 的非空行逐行比对：**0 行相同**。
- 隐藏测试在原例之外的输入 `[2, 3, 1, 1]`、`[2, 3, 1, 2]`：**新题面都没有出现**。`[2, 3, 1]` 与 `[0, 1, 2]` 是原题面已有的原例。
- ingest 的公开面断言（`rh2/src/repoharness2/envpack/ingest_r2e_subset.py:602-621`：期望原文、gold 补丁、造题指令不得原样出现在公开面）：按上面的比对不会触发；正式 ingest 时由代码复核。

## 6. 题面改完以后，按 v1 §4 判 S1（协调者补充第 3 条要求）

| 步 | 判断 | 依据 |
| --- | --- | --- |
| 1 核心要求有无直接断言 | 有，不命中 | `TestHelpers.test_unique_in_order_mapping`：原例 `PRIV/hidden_tests/test_1.py:92-94`，含重复元素的一般规则 `:95-100`，5 组公开用例 `:77-91` |
| 2 是否只用示例字面值 | 不命中 | 原例之外有 `[2, 3, 1, 1]`、`[2, 3, 1, 2]` 两个非示例输入（期望映射不同）；公开用例里的对合置换 `[2, 1, 0, 3]` 会拒绝只对原例的三元轮换成立的写法（`p[p][inv]` 在 `:88` 失败，复核已重算，见 `R1/results/orange3__22e98f8f…/review.md` C8）。**剩余理论缺口**：非对合输入都是同一个三元轮换，只对阶数整除 6 的置换成立的写法（如 `p^5`）能过；不自然，登记为 T3 / S2，不修 |
| 3 退化探测 | **未做**（本题各批只有 noop 与 gold 的评分证据） | 建议候选（只凭 gold 修改位置写出，"与输入无关的固定结果"）：在 `Orange/widgets/data/owcreateclass.py` 的 `unique_in_order_mapping` 里保留 `unique_in_order = u[np.argsort(idx)]`，把 `mapping` 改成 `np.arange(len(a))`。它对原例 `[2, 3, 1]` 恰好给出期望的 `[0, 1, 2]`，但违反题面描述的一般规则（每个元素映射到它在 uniques 里的下标）：公开用例 `[42, 42]` 应得 `[0, 0]`（`test_owcreateclass.py:83-85`），它给 `[0, 1]`。源码推导预计在隐藏 `:85` 失败、得 0。按 v1 §4 须 1 次正式评分并确认补丁交付、测试执行，做之前训练候选记 conditional |
| 4 已有候选得 1 却违反公开要求 | 不命中 | 已评分的候选只有 gold（旧题面代码块与 gold 相同）；静态列出的部分实现（`inv`、`idx[inv]`、`p[p][inv]`、`range(len(a))`、只改调用方）按复核重算都在 `:85/:88/:91/:94` 失败 |

结论：**没有已有候选证据的 S1，不需要 R-c**。第 3 步是用途结论（v1 §2"训练候选"要求第 2、3 步结果）的缺口，不是题面修订的前提。

## 7. 验收计划（v1 §5 R-f）

| 验收项 | 状态 | 由谁 |
| --- | --- | --- |
| 新公开读者读修订后题面，推出的需求 = 原例加一般规则 `u[m[i]] == a[i]`，不需要猜隐藏细节 | 待做。本会话看过 gold 与隐藏测试，不能充当 | 协调者另派未接触私有材料的新会话 |
| 逐行核对无答案、无隐藏细节 | 已做（§5） | — |
| 评分材料不变 | 是；不需要重跑 noop / gold 验证评分 | — |
| 保存新版本与父版本；标"自建修订题 + 版本" | 待做：新增修订单版本（kind `statement_text_replace`，target `problem_statement`，`sha256_before/after` 见 §3），同步 pins 与 ingest 产物，保留旧 v3 | 协调者 |
| 正式链路实际题面消息 | 待做：发布后捕获一次，确认模型收到修订后文本（首批 Codex 复核 §2 表） | 协调者 / 探针链路 |
| Codex 复核 | 待做 | 协调者 |

## 8. 暴露与阅读范围

- 读了：v1 标准、本批 README、R2E 主审角色卡"评分口径"一节、本题首批审查产物（`card.md`、`review.md`、`public_read.md` 前 80 行、`analysis_before_history.md` 的候选与附录段）、首批 Codex 复核与 `grader_candidates.md` 中与本题相关的段落、本批 Codex 代码复核、`PRIV` 全部文件、`PUB` 的题面与环境说明、`DC` 的 captures / 命令 / 身份字段、ingest 的修订与公开面检查代码。
- 本会话见过 gold 与隐藏测试，属于审查暴露，不能作本题的公开读者或解题者。
