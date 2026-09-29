# pandas `32dd55cb` 修订方案（R-b：放宽 T2 的报错文字约束；加 sum 对照；附加：含缺失值的均值）

2026-09-29 · 修订执行者（Claude，单题闭环试行）。规则：[统一标准 v1](../../../task_screening_standard_v1_20260925.md) §3 T1、§4、§5 R-b / R-c 与验收，§11 本题"R-b，加 sum 对照"；本批 [README §3](../../README.md)。本文是修订草案与试跑记录，**不是正式修订单**；试跑不是正式评分（差别见 `rh2/experiments/r2e_lifecycle_20260929/trial_grade.py` 文件头）。

路径缩写（均相对仓库根）：

- `PUB/` = `runs/r2e_static_prep_20260924/v3/public/pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0/`，`W/` = `PUB/worktree/`
- `PRIV/` = `runs/r2e_static_prep_20260924/v3/private/pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0/`
- `CANDS/` = `runs/r2e_actor_20260925/grader_cands/`，`LEDG/` = `runs/r2e_actor_20260925/grader/`
- `B1/` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/`（首批审查；本题产物在 `B1/results/pandas__32dd…/`）
- `CX1` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_actor_review_20260925/README.md`（首批 Codex 复核）
- `DC/` = `runs/r2e_actor_20260925/devcheck/pandas__32dd55cb8331c36df6b485eb042c7d2d/orig/captures/`（agent 身份、正式启动路径的开发核对）
- 键简称：**T1** = `TestDataFrameAnalytics.test_mean_extensionarray_numeric_only_true`，**T2** = `TestDataFrameAnalytics.test_mean_datetimelike_numeric_only_false`

## 0. 结论

- **模板**：R-b（T2 的报错文字）为主；同一轮加两条 R-c 性质的新断言：sum 对照（v1 §11 已列）与含缺失值的均值（v1 §11 未单列，§6 单列依据，便于单独拿掉）。三处都只改隐藏测试 `test_1.py` 的文本，**键集合与期望映射不变**（92 键全 PASSED）。
- **与旧修订的关系**：本题已批准 r2e-mr-016（新增私有 `conftest.py`）与 r2e-mr-017（期望映射 13 键 ERROR→PASSED）。本次只改 `test_1.py`，该文件此前没有修订；期望映射不动。所以**不与旧修订合并**，是一条独立的新修订，父版本是"来源 `test_1.py` + mr-016/017 已生效"的当前材料。
- **试跑**：见 §5。修订后 gold 与被误拒的合理解 C1 都是 1；noop、两种"只修 mean"的半修（C3、C3g）、窄修 `IntegerArray.sum` 的 C4 都是 0，且都只错 T1。其中 C3g 在**当前材料下就得 1**（92/92），是现存的 S1，由 sum 对照堵上；逐条去掉新断言的对照草案下，C3 与 C4 分别重新得 1，证明两条新断言各自都是必要的。
- **状态**：修订草案已试跑通过，待 Codex 复核；正式修订单、材料摘要、派生镜像材料步骤与正式评分由协调者落。不需要用户决定。

## 1. 要纠正的问题与触发候选

1. **T2 误拒合理解（v1 §3 T1，R-b）。** T2 第 899 行要求 Period 列 `mean(numeric_only=False)` 抛出的 TypeError 匹配 `"mean is not implemented for Period"`，这是 gold 路线（所有 EA 块改调 `values._reduce`）的副作用。公开的 DataFrame 级旧测试在同一行要求另一条文字 `"reduction operation 'mean' not allowed"`（`W/pandas/tests/frame/test_analytics.py:899`），题面没有提 Period。
   - 触发候选 **C1**（`CANDS/pandas_32dd_C1_numeric_ea_only.patch`，sha256 `932cbaf9…`）：只对数值 EA 调 `values._reduce`，Period 等其它 EA 保持 base 路径。首批正式评分 0（91/92，只错 T2；`LEDG/ledger_pandas_C1.jsonl`，镜像 `3d40959d…`，当前材料），今晚本机试跑同样只错 T2（`trials/cur_C1.json`）。首批记录把"C1 能否修好题面原例"标为代码推断（`B1/grader_candidates.md:85`）；现在修订后的 T1（全 Int64 帧均值、题面式混合帧含缺失值的均值、sum）C1 全过，是试跑事实（`trials/rev_C1.json`）。C1 不改 Period 路径，公开 `test_analytics.py:899` 的旧文字仍成立；公开测试是否全过仍是代码推断，本次没有另跑。
2. **只修 mean 的半修，现在就能得 1（v1 §4 第 4 步，S1）。**
   - **C3g**（本目录 `cands/pandas_32dd_C3g_all_ea_mean_only.patch`，按主审候选表的"C3：只在 `name == "mean"` 时对 EA 分派（半修）"写成，即 gold 式分派只对 mean 生效）：当前材料下 **92/92、得 1**（`trials/cur_C3g.json`；Period 的 mean 也被分派到 `PeriodArray.mean`，所以 T2 通过），但 `df.sum(numeric_only=True)` 仍抛题面那条 ValueError。这是题面"reduction operations (e.g., mean)"的同一核心要求在非示例实例上的违反，由 v1 §11 的"加 sum 对照"修。
3. **放宽 T2 后会被放行的已知错误候选。** 当前它们只是被 T2 顺带挡住（`B1/results/pandas__32dd…/analysis_before_history.md` §3 候选表；`CX1:39,63`）：
   - **C3**（本目录 `cands/pandas_32dd_C3_mean_only_numeric_ea.patch`，按 `CX1:39` "只给 C1 增加 `name == 'mean'` 条件"写成）：`sum` 仍抛题面同一条 ValueError。同样由 sum 对照挡住。
   - **C4**（本目录 `cands/pandas_32dd_C4_integerarray_sum_accepts_axis_dtype.patch`，按主审"窄修 `IntegerArray.sum`，让它接受 `axis`/`dtype`（缺失值计数不对）"写成）：题面示例能跑，但含缺失值时均值按总行数计数（按源码推导：`_maybe_get_mask` 对整数型 dtype 不算掩码，`W/pandas/core/nanops.py:226-229`，计数取总行数，而求和跳过缺失值，`[1, NA, 3]` 得 4/3）。需要含缺失值的均值断言（§6）。
   - 三个构造补丁都是按已有文字描述写成、只改库源码；在公开工作树副本上 `git apply --check` 通过。

## 2. 公开依据

**R-b：T2 同时接受两条有文档的报错文字。**

- 旧文字：公开 DataFrame 级测试 `W/pandas/tests/frame/test_analytics.py:896-900`；来源 `W/pandas/core/nanops.py:60-68`（`disallow`："reduction operation '{f_name}' not allowed for this dtype"）与 `nanops.py:511`（`nanmean` 上的 `@disallow(PeriodDtype)`）。
- 新文字：公开 Series/Index/PeriodArray 级测试 `W/pandas/tests/reductions/test_stat_reductions.py:38-60`（Period `mean` 抛 TypeError，匹配 "ambiguous"）；来源 `W/pandas/core/arrays/datetimelike.py:1639-1645`（"mean is not implemented for {PeriodArray} since the meaning is ambiguous"）。
- 写法先例：`W/pandas/tests/reductions/test_reductions.py:350-362` 用 `"|".join([...])` 同时接受两类文字，并对 `td.to_frame()` 的 `numeric_only=False` 按块归约路径使用同一正则。
- 题面 `PUB/user_prompt.txt:3-30` 只讲 Int64 列与 `numeric_only=True`，没有 Period、没有报错文字。
- **保留的行为要求**：T2 前半段（datetime/timedelta 在 `numeric_only=False` 下求均值，`PRIV/hidden_tests/test_1.py:891-894`）不变；Period 列求 `mean` 仍必须抛 TypeError，且文字必须是两条有文档的之一——"改坏 Period 报错"（例如转成 object 后抛无关 TypeError，或不报错）仍判 0。这不是为保住 gold 放宽：gold 前后都过。

**R-c（v1 §11 已列）：sum 对照。**

- 题面标题 `PUB/user_prompt.txt:4`："DataFrame Reduction Fails with ExtensionArray Columns When `numeric_only=True`"；`:7`："reduction operations (e.g., mean)"——mean 是示例，要求是归约操作。
- base 上 `df.sum(numeric_only=True)` 抛与题面**逐字相同**的 ValueError（`DC/mcve_sum.out:13-25`，agent 身份实测）。所以 sum 是同一缺陷的非示例实例（v1 §4 第 2 步），不是扩大需求；当前测试只用 mean，只修 mean 的 C3g 因此今天就得 1（§1 第 2 条）。
- 公开读者在读隐藏材料前独立把 sum 列为倾向需要的要求，并建议用它作确定性复现、用逐列 Series 归约作对照（`B1/results/pandas__32dd…/public_read.md:25,103,105`）。
- 结果 dtype 公开材料未约定（gold 下为 int64，转浮点的实现为 float64；`public_read.md:26` R5、首批复核 `review.md` §2 第 3 点），所以只比数值：`check_dtype=False`。

**R-c（附加，§6）：含缺失值的均值。**

- 题面 `PUB/user_prompt.txt:25`："The `mean` function should correctly compute the average of the numeric columns, including the ExtensionArray column 'B'"。
- `W/pandas/core/generic.py:10420-10421`（DataFrame 归约文档 `_num_doc`）："skipna : bool, default True — Exclude NA/null values when computing the result."
- `W/pandas/tests/extension/test_integer.py:236-245`：Int64 的 Series 归约在 `skipna=True` 时等于先 `dropna()` 再归约——`[1, NA, 3]` 的均值为 2.0、和为 4。
- 避开整列缺失（结果是 `pd.NA` 还是 NaN 属公开读者 R5 的多解）；帧结构用题面示例的"numpy int 列 + Int64 列"。

## 3. 具体改动（`PRIV/hidden_tests/test_1.py`，一条 `hidden_test_text_replace`，两处 edit）

**Edit A（T2，原第 899 行）** old（全文恰好一次）：

```python
        with pytest.raises(TypeError, match="mean is not implemented for Period"):
            df.mean(numeric_only=False)
```

new：

```python
        # either documented TypeError text is acceptable: the PeriodArray.mean
        # one or the nanops one (reduction operation ... not allowed)
        msg = "|".join(
            [
                "mean is not implemented for Period",
                "reduction operation 'mean' not allowed for this dtype",
            ]
        )
        with pytest.raises(TypeError, match=msg):
            df.mean(numeric_only=False)
```

**Edit B（T1 函数体末尾，原第 907–908 行之后）** old（全文恰好一次）：

```python
        expected = pd.DataFrame(arr).mean()
        tm.assert_series_equal(result, expected)
```

new = old 原样保留，其后追加：

```python

        # mixed frame as in the issue example, with a missing value in the
        # EA column: skipna=True (default) excludes it
        df = pd.DataFrame(
            {"A": [1, 2, 3], "B": pd.array([1, None, 3], dtype="Int64")}
        )
        result = df.mean(numeric_only=True)
        expected = pd.Series({"A": 2.0, "B": 2.0})
        tm.assert_series_equal(result, expected)

        # a reduction other than mean on the same frame (the result dtype
        # of sum is not prescribed, only the values)
        result = df.sum(numeric_only=True)
        expected = pd.Series({"A": 6, "B": 4})
        tm.assert_series_equal(result, expected, check_dtype=False)
```

设计取舍：

1. **放进 T1 函数体，不新建测试函数**：键集合与期望映射都不变，不必动已被 r2e-mr-017 改过的期望映射（首批独立复核 `B1/results/pandas__32dd…/review.md` §2 第 2 点的放置建议）。代价是 C3、C3g、C4、noop 都只表现为 T1 FAILED，要看失败点区分（§5 表中已注明）。
2. **期望值写死**：均值 A=2.0、B=2.0（float64，与原 T1 的 float64 要求一致），和 A=6、B=4；都由公开语义直接算出，不取自 gold 输出，也不与候选自己的 Series 归约比较（避免候选同时改坏两边）。
3. 修订条目的机器可读形式见 `revision_draft.json` 的 `revisions`，与试跑用的 `trials/draft_edits.json` 逐字相同；草案全文 ASCII，`ast.parse` 通过。

## 4. 期望映射的逐键变化

- **无变化**：92 键全部 PASSED（当前材料 = 来源期望 + r2e-mr-017）。`revision_draft.json` 的 `expected_after` 即当前映射。
- 观测映射的变化（不是期望变化）：修订后 noop 的 T2 由 FAILED 变为 PASSED（旧文字被接受），T2 不再是目标键，而是"datetime/timedelta 均值 + Period 均值报 TypeError"的回归键；修订后唯一目标键是 T1。
- 父版本：`PRIV/hidden_tests/test_1.py` sha256 `4a153a37884f47bbfe1525d1285ad5ab78bc85a17eac2fac7ffcedf6b598bb96`；`conftest.py`（mr-016）`053ce359…`；`expected_output.json`（mr-017 后）`9771cde591cfc03943ad96243769be99e38d34c68946db660cd5cd5578a6c73c`。
- 修订后 `test_1.py` sha256 `3ad05d5c3934d40a499665a0cdedb9dc2d2c84e4cf28578d8ff0a00e30c314e3`（1283 行）。

## 5. 验收计划与试跑结果

正对照用 gold（`PRIV/gold.patch`，sha256 `7391277e…`）。试跑机为本批 R2E CPU 机，派生镜像 `sha256:0fb0a2f54d0ccf02e1e89f5b679abddacdab433dccc40247f825bdb978cb6945`，配方 `r2e_derive_v1+material_v2+sysconfig_v1`（`/rh2_private` 含 mr-016/017）；期望一律用 `--expected current`（映射不变）。每个候选跑 1 次。

**环境确认（当前材料）**：noop 为 mismatch，错 T1、T2（`trials/cur_noop.json`）；gold 为 match 92/92（`trials/cur_gold.json`）。与 09-24 修订后的 noop/gold 结论一致。

| 候选（补丁） | 当前材料试跑 | 修订后预期 | 修订后试跑（完整草案 `trials/draft_edits.json`） | 失败键与失败点 |
| --- | --- | --- | --- | --- |
| gold（`PRIV/gold.patch`） | match 92/92（`trials/cur_gold.json`） | 1 | **match 92/92**（`trials/rev_gold.json`） | — |
| noop | mismatch：T1、T2（`trials/cur_noop.json`） | 0 | **mismatch**（`trials/rev_noop.json`） | 仅 T1（题面那条 ValueError，`pandas/util/_validators.py:66`）；T2 变为 PASSED |
| C1（`CANDS/pandas_32dd_C1_numeric_ea_only.patch`） | mismatch：仅 T2（`trials/cur_C1.json`，`test_1.py:900` 正则不匹配；与首批正式评分 91/92 一致） | 1 | **match 92/92**（`trials/rev_C1.json`） | —（误判已纠正） |
| C3g（`cands/pandas_32dd_C3g_all_ea_mean_only.patch`） | **match 92/92，得 1**（`trials/cur_C3g.json`；现存 S1） | 0 | **mismatch**（`trials/rev_C3g.json`） | 仅 T1（sum 对照：非 mean 归约不分派，走 base 路径抛题面 ValueError）。对照：完整草案去掉 sum 对照时 **match**（`trials/ablate_nosum_C3g.json`） |
| C3（`cands/pandas_32dd_C3_mean_only_numeric_ea.patch`） | 未跑（T2 上与 C1 同一路径） | 0 | **mismatch**（`trials/rev_C3.json`） | 仅 T1：sum 对照抛题面同一 ValueError（`_validators.py:66`）。对照：只放宽 T2 时 **match**（`trials/t2only_C3.json`）；完整草案去掉 sum 对照时 **match**（`trials/ablate_nosum_C3.json`） |
| C4（`cands/pandas_32dd_C4_integerarray_sum_accepts_axis_dtype.patch`） | 未跑 | 0 | **mismatch**（`trials/rev_C4.json`） | 仅 T1：含缺失值的均值断言不符（日志 `[right]: [2.0, 2.0]`）。对照：只放宽 T2 时 **match**（`trials/t2only_C4.json`）；完整草案去掉含缺失值均值断言时 **match**（`trials/ablate_noNA_C4.json`） |

每次试跑都观测到 92 键、无缺键与多余键；修订草案已应用（`RH2_TRIAL_EDITS_APPLIED=1`），补丁都干净应用。试跑工具只保留日志末尾 8000 字符，noop、C3、C3g 的失败行号被截掉，只剩异常类型；C3、C3g 失败在 sum 对照这一点由对照草案确定：完整草案去掉 sum 对照、其余不变时，C3 与 C3g 都是 92/92（`trials/ablate_nosum_C3.json`、`trials/ablate_nosum_C3g.json`）。

**验收要点（v1 §5）**：

1. 正对照为 1、noop 为 0：见上表。
2. 本次要纠正的误判已纠正：C1 由 0（当前材料，只错 T2）变为 1；现存漏判 C3g 由 1 变为 0。
3. 已知相关错误候选仍为 0：C3、C3g、C4 在完整草案下都是 0。C3、C4 在"只放宽 T2"的对照草案下为 1，且逐条去掉 sum 对照 / 含缺失值均值断言后分别重新得 1，说明放宽 T2 必须与两条新断言一起落，不能单独落。
4. 修订后仍受保护的公开要求：题面原例（全 Int64 帧 `mean(numeric_only=True)` 等于 int64 帧均值，float64）；题面混合帧、含缺失值时的均值（skipna）；非 mean 归约 sum；Period 均值仍报两条有文档文字之一的 TypeError；datetime/timedelta 均值；其余 90 个回归键。

## 6. 附加项单列：含缺失值的均值断言（v1 §11 未单列）

- **为什么加**：R-b 放宽 T2 后，C4 失去 T2 的顺带阻挡；C4 在原 T1（无缺失值）与 sum 对照上都正确，只有含缺失值的均值会错（按源码推导为 4/3 而非 2.0；试跑日志只留下期望侧 `[right]: [2.0, 2.0]`）。不加这条，R-b 的验收"已知相关错误候选仍为 0"不成立：完整草案去掉这条断言、其余不变时 C4 为 match（`trials/ablate_noNA_C4.json`），完整草案下 C4 为 mismatch（`trials/rev_C4.json`）。
- **性质**：它不是 v1 §4 第 4 步意义上"今天就得 1"的现存 S1（当前材料下 C4 被 T2 挡住），而是 R-b 放宽的配套条件；所以不能在保留 R-b 的同时单独拿掉它。
- **公开依据**：§2 最后一组（题面 `user_prompt.txt:25`、`generic.py:10420-10421`、`test_integer.py:236-245`）。它也在主审与首批独立复核的修订提案里（`B1/results/pandas__32dd…/screening_record.json` `disposition.revision_proposal`；`review.md` §5 第 3 步草案），首批 Codex 复核的措辞是"新断言应覆盖非 mean 归约，不仅含 NA 的 mean"（`CX1:63`）。
- **如何单独拿掉**：只删 Edit B 追加块里从 `result = df.mean(numeric_only=True)` 起的 3 行（均值计算、期望、断言）；混合帧的定义保留，sum 对照照常使用它（对照草案 `trials/draft_ablate_noNA_edits.json` 就是这样删的）。拿掉后 C4 得 1（`trials/ablate_noNA_C4.json`），R-b 的验收第 3 条随之不成立，需另找能挡住 C4 的断言，或连同 R-b 一起退回。

## 7. 边界与未做

- 没有改 gold、题面、`run_tests.sh`、解析规则；没有为保住 gold 放宽要求（gold 前后都过）；新期望来自公开语义。
- 未覆盖（登记为 S2 级缺口，不在本次范围）：`prod/min/max/median/std/var` 等其它归约（公开读者 R4 另列；按其静态阅读，base 上 prod/min/max 报的是另一种错误，不是题面那条 ValueError）、整列缺失（公开读者 R5 多解）、`axis=1`、默认 `numeric_only=None` 路径（题面未要求，gold 也未修）。一个只修 mean 与 sum 的实现仍可能得 1，这是本次有意不扩的范围。
- 试跑工具不核隐藏测试树与入口摘要、权限布置简化；定稿后须走正式修订单、派生镜像材料步骤与正式评分（noop、gold 各 ≥1 次，C1、C3、C3g、C4 各 1 次）。

## 8. 交协调者落正式修订单时

1. 一条 `hidden_test_text_replace`，`target: test_1.py`，两处 edit（§3），父 sha256 `4a153a37…`，子 sha256 `3ad05d5c…`；与 r2e-mr-016/017 并存，不改它们。
2. 期望映射不变（仍为 mr-017 后的 `9771cde5…`）。
3. 新增的三个构造候选补丁（C3、C3g、C4）存于 `cands/`，供正式评分复验；对照草案（`trials/draft_t2only_edits.json`、`draft_ablate_nosum_edits.json`、`draft_ablate_noNA_edits.json`）只作证据，不进正式材料。
