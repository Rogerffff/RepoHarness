# dask__dask-9378：第3类诊断结果

2026-09-29 / Claude（云端，第3类负责人）。原分类：第3类“具体疑点缺辨别实验”。已登记的实验是：保持 shape、dtype、类型和值都正确，只改 mask，然后核对正式得分和显式 mask 比较的结果。

> **当前状态（09-30 更正，采纳 Codex 独立复核）：暂留第3类，目标需要用户选择。**
>
> - **不变的部分**：mask 漏检已证实（两个退化候选在原材料正式得 1），R-c“逐元素比较 mask”的修法成立，不需要重跑。
> - **推翻的部分**：09-29 把“只修顶层”判为没有公开依据、按 P5 第一分支用 R-f 把 `da.ma` 新 API 写成必须——这把题面的建议路线升级成了强制要求。依据如下：
>   - 题面用**顶层** `da.ones_like(array)` 的 `[1 1 1]` 对比 numpy **顶层** `np.ones_like` 的 `[1 1 --]` 说明问题；新增 `dask.array.ma.ones_like` 只是 “perhaps the simplest thing” 式的建议；
>   - base `dask/array/creation.py` 顶层 `ones_like` 的 docstring 写的是 “Return an array of ones with the same shape and type as a given array”，返回值也写 “same shape and type as `a`”，实现把输入的 `_meta` 传给结果；`MaskedArray` 本身也是 `ndarray` 子类；
>   - 09-30 按 base 提交 `8b95f983` 核对了 `dask/array/ma.py`、`creation.py`、`wrap.py`、`docs/source/array-api.rst`、`array.rst`：Masked Arrays 一节只列出 `da.ma` 已有函数，**没有**“mask 相关功能只放在 `da.ma`”之类的排他性约定；
>   - `toplevel_only` 已实测保留 mask，并通过 320 项公开 creation 测试，原材料正式得 0（只因 `da.ma` 下没有该函数）。
>
>   两种读法都有公开依据，属于目标选择，按规则交用户；不以依据是否“同等”为门槛，也不能先改题面、再用新公开读者认为清楚来倒推原目标唯一。
>
> **决策包（请用户选择）**
>
> - **要决定什么**：本题目标是“必须新增 `dask.array.ma.ones_like/zeros_like/empty_like`”，还是“让 `*_like` 在 masked dask 数组上保留 mask，路线不限（包括修顶层 `da.*_like`）”。
> - **A：必须新增 `da.ma` API（与 gold 一致）。**
>   - 测试沿用 R-c v1（只测 `da.ma`，逐元素比较 mask）；
>   - 题面按 R-f 补一句写明新增 `dask.array.ma.*_like`，形成**自建题面版本**，须经新公开读者验收；
>   - `toplevel_only` 仍得 0，按新题面属未完成要求。
> - **B：路线不限，只验保留 mask 的行为。**
>   - 测试改为：对 ones、zeros、empty 三个函数，若 `da.ma` 下有该函数就检查它，否则检查顶层 `da.*_like`；两处都在时至少一处按 numpy 的方式逐元素保留 mask；
>   - 题面不改；
>   - 预期：gold 与 `toplevel_only` 为 1，两个退化候选与 noop 为 0。R-c 的 mask 比较照常保留。
> - **推荐 B（建议，不是决定）**：它按题面实际展示的行为验收；不需要改题面和新公开读者；也不惩罚与 numpy 顶层行为一致的修法。
> - **反方理由**：若更看重“按题面建议的 API 形态”这一训练信号，或希望与上游实际的做法一致，选 A。
> - **长期代价与可逆性**：
>   - A 要长期标明题面版本；
>   - B 的测试多一层“任一入口”逻辑，第2类落地时要写清楚；
>   - 两者在正式落地前都可以换。
> - **不决定时**：本题留第3类，只作问题定位；R-c 的 mask 断言可以先交第2类作为与目标无关的部分，但不能按当前 R-f 草案落地。
>
> 以下是 09-29 的原始结论，保留作历史。

**（09-29 原结论，已被上方更正取代）结论：问题和修法已明确，建议转第2类。独立复核同意，无阻断项。**

- 疑点已坐实：值、dtype、类型都对但 mask 错误的退化候选，在原材料下得满分（S1：T2a＋T2b）。
- 修法 R-c：ones／zeros 也逐元素比较 mask。gold 仍可作正对照，已通过诊断评分。
- 附带的范围问题：只修顶层 `da.*_like` 的设计得 0。按 P5 第一分支，走 R-f 补一句接口说明，不需交用户。
- 实施依赖 D6 的“测试补丁替换”和 `statement_replace` 两个后续切片。

## 1．公开要求

题面希望 `ones_like`、`zeros_like`、`empty_like` 在处理 masked dask 数组时**保留 mask**。它用顶层 `da.ones_like(array)` 的输出 `[1 1 1]` 对比 numpy 的 `[1 1 --]`，结尾建议“perhaps the simplest thing would be to implement `dask.array.ma.ones_like`, etc.”，即用 `map_blocks` 包装 `numpy.ma` 的对应函数。

## 2．实测结果

镜像 `xingyaoww/sweb.eval.x86_64.dask_s_dask-9378`，摘要 `sha256:d59dc8d2…91b1`，原材料，无派生配方。

**（1）为什么会漏检。** 镜像内 `dask/array/utils.py` 的 `allclose` 对 masked 数组调用 `np.ma.allclose(a, b, masked_equal=True)`。它先把两侧 mask 取并集，并集内的位置一律算作相等，所以**只比较两侧都未屏蔽的位置**；mask 取反时，一个值也不比较。`assert_eq` 另外只检查类型和 dtype。因此原 F2P 对 ones／zeros 不检查 mask；只有 `empty_like` 分支显式比较了 `getmaskarray`。

**（2）私有行为对照。** 数据与隐藏测试相同：3×2、`chunks=2`，mask 非均匀。

| 版本 | `da.ma.ones/zeros_like` 的 mask 与 numpy 一致 | `empty_like` 的 mask | 顶层 `da.ones_like(题面示例)` |
| --- | --- | --- | --- |
| base | 无该入口 | 无该入口 | `ndarray [1 1 1]`（缺陷复现） |
| gold | 是 | 是 | 仍为 `ndarray [1 1 1]`（gold 只新增 ma 入口） |
| `ma_mask_none`：值、dtype、类型正确，不屏蔽任何位置（输入被屏蔽的 4/6 个位置出错） | **否** | 是 | 同 base |
| `ma_mask_invert`：值、dtype、类型正确，mask 取反（6/6 个位置出错） | **否** | 是 | 同 base |
| `toplevel_only`：让顶层三个函数对 masked 输入保留 mask，不新增 ma 入口 | 无该入口 | 无该入口 | `MaskedArray [1 1 --]`，与 numpy 一致 |

公开 `test_masked.py`（134 项）和 `test_creation.py -k arr_like`（320 项）在五个版本下全部通过。

**（3）原材料正式评分**（F2P 3 项，P2P 134 项）：

| 候选 | reward | 说明 |
| --- | --- | --- |
| noop | 0 | 与历史一致 |
| gold | 1 | 与历史一致 |
| `ma_mask_none` | **1** | mask 错误仍得满分 |
| `ma_mask_invert` | **1** | mask 错误仍得满分 |
| `toplevel_only` | 0 | 三个 F2P 都因 `da.ma` 下没有该函数而失败 |

以上评分参考缺席 0，安装成功，清理成功；准备阶段约 23–35 秒。独立复核另外构造了 `invert_values7`：值全填 7、mask 取反，它在原测试下三项全过。这说明 mask 取反时原断言连值都不检查。

## 3．判定（v1 §3–§4）

- **T2a（§4 第 1 步）**：“ones／zeros 保留 mask”是题面核心要求，原测试没有直接断言。
- **T2b（§4 第 3 步，S1）**：只改 mask 的退化候选违反“保留 mask”，正式得 1。
- **命名空间，按 P5 第一分支处理**：
  - 测试采用的 `da.ma.*_like` 读法有直接公开依据：
    - 题面点名了这组函数；
    - numpy 本身有 `np.ma.ones_like` 等；
    - `dask/array/ma.py` 一贯用 `@derived_from(np.ma)` 镜像 `numpy.ma`；
    - dask 已有把 mask 感知版放在 `da.ma` 的先例，如 `da.ma.average` 对 `da.average`。
  - “只修顶层”只能从“Currently”示例间接推出，没有文档、API 或旧测试支持：顶层 `*_like` 的 docstring 写的是返回 `ndarray`，`test_creation.py` 也没有 masked 用例。因此它不构成“两种读法都有依据”，不交用户。
  - 这也不是 T1：`da.ma` 入口是题面点名的公开 API，所以不改测试去接受两种设计。测试并不惩罚两处都改。
  - 按 v1 P5 规则，“测试采用的读法有公开依据时，走 R-f 补一句说明”。
- gold 可继续作正对照。

## 4．修法（交第2类）

### R-c：修订版测试草案 v1

[`revised_test_v1.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask9378/revised_test_v1.patch)，sha256 `67393733…6a75`。`test_like_funcs` 对三个函数都先比较 `getmaskarray`；ones／zeros 再保留原来的 `assert_eq(res, sol)`。测试编号不变。

修订后仍受保护的公开要求：

- ones／zeros 在未屏蔽位置的 1／0 值、dtype、shape、`MaskedArray` 类型及 meta 一致性（原 `assert_eq`）；
- 三个函数的逐元素 mask（新增）。

修订版诊断评分（`--materials`，grader 后缀 `+c3-dask9378-mask-equality-v1`）：

| 候选 | 修订版 reward |
| --- | --- |
| noop | 0 |
| gold（正对照） | **1** |
| `ma_mask_none` | 0（F2P 1/3，失败在新增 mask 断言） |
| `ma_mask_invert` | 0 |
| `toplevel_only` | 0（命名空间问题由 R-f 处理，不靠放宽测试） |

独立复核用私有 pytest 复现了上表，另外确认 `invert_values7` 在修订版为 0，并确认自写的非 gold 正确实现通过修订版。

### R-f：修订题面草案 v1（尚未由新公开读者验收）

[`revised_statement_v1.txt`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask9378/revised_statement_v1.txt)：

- 父版本题面 SHA256 为 `0a0975ae06c4…d058`，与 public bundle 的 `problem_statement_sha256` 一致；
- 修订后 SHA256 为 `06cfa618f648…366e`；
- 保留原文 CRLF 换行，只在末尾新增一句：“Please add these as `dask.array.ma.ones_like`, `dask.array.ma.zeros_like` and `dask.array.ma.empty_like`.”

依据是题面原有建议和 `dask.array.ma` 的现有模式。新增句不含隐藏测试的数据、mask 形状或断言写法，函数名题面中已有。

### 交接给第2类

1. D6 落地 R-c 需要“测试补丁替换”切片，R-f 需要 `statement_replace` 切片，两者都不在首片内：测试补丁替换计划随 MONAI5932 切片引入，`statement_replace` 随 mypy15184 切片引入（`category2_repair_20260929/d6/implementation_brief.md`）。
2. 请一名新公开读者读修订后的题面，确认推出的接口与断言一致。
3. 复验：修订版下 noop 0、gold 1，两个 mask 退化候选为 0。
4. Codex 复核。

## 5．当前用途（v1 §2，D6 落地前）

| 版本 | 问题定位 | 能力比较 | 训练候选 | 留出评测 |
| --- | --- | --- | --- | --- |
| 原版 | 是 | 否 | 否 | 否 |

原版能力比较为“否”（09-30 按 Codex 复核更正：原版有已证的 S1 未修，不能靠事后审计进入普通能力比较；特殊诊断试解另列调查目的，不混用原分数）。09-29 曾写作“至多 conditional，预先登记两项事后审计”，已撤下。

## 6．独立复核（已完成）

复核结论：**同意处置，无阻断项**。见 [review_initial.md](review_initial.md)（先于读作者材料封存）和 [review.md](review.md)。非阻断建议全部采纳：

- 措辞：`ma_mask_none` 只在输入被屏蔽的位置出错；并集比较的精确说法；
- 补记 T2a；
- 写全 P5 第一分支的理由；
- 交接写明 D6 的两个后续切片、D6 落地前的用途、修订后受保护的要求，以及 R-f 父版本 SHA 与完整修订题面；
- 登记下列 T3／T6 缺口。

## 7．登记的缺口（T3／T6，按 §8 抽查，不要求本轮修）

- **惰性没有覆盖**：先 `.compute()` 再返回 numpy MaskedArray 的实现，在原版和修订版都通过。题面没有把惰性列为核心要求。
- **P2P 不含 `test_creation.py`**：改坏顶层 `*_like` 的候选，评分发现不了。
- **`empty_like` 分支不检查 dtype 与返回类型**：题面对 empty 只要求 mask。

## 8．未做与剩余事项

真实 actor 开发条件未验，没有模型求解证据，R-f 草句未经新公开读者验收。

## 9．版本与证据

- 代码与运行环境：见 [环境说明](../../environment.md)。
- 候选补丁（sha256 前缀）：`ma_mask_none` `41244f3d`、`ma_mask_invert` `c9f68c60`、`toplevel_only` `f9762bb1`，位于 `rh2/experiments/category3_cloud_20260929/dask9378/`。
- 原始证据：[evidence/](evidence/)，其中 `formal/` 为原材料评分，`formal_revised_v1/` 为修订版评分，`semantic_v1/` 为私有对照；全部文件的 SHA256 见 `evidence_manifest.json`。
