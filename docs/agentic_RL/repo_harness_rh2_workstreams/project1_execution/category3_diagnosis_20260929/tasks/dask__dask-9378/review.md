# dask__dask-9378 独立复核

2026-09-29 / 独立复核者（Claude，新会话，不继承作者上下文）。

**总判断：同意作者的处置，无阻断项。**

- 原测试不检查 ones/zeros 的 mask，已由正式评分坐实（S1，T2b）。
- 按修订测试 v1 走 R-c，gold 作正对照。
- “只修顶层”得 0 的问题，按 P5 第一分支走 R-f 补一句。
- 转第2类。

需要补的是几处措辞精确化、一段 P5 分支理由和几条交接说明，均不影响处置。

## 0. 独立性

- 先只读原件，写成 [review_initial.md](review_initial.md)（SHA256 `7757357e38376938f13cf33c059b04ab4d9ae8b9a8b1a7be015f34a19c9c9918`，写后未改），之后才读作者的 `result.md`、`evidence/` 和 `rh2/experiments/category3_cloud_20260929/dask9378/`。
- 初判与作者结论一致的部分：S1、R-c 写法（三者都比较 `getmaskarray`，ones/zeros 保留 `assert_eq`）、P5 第一分支走 R-f、D6 前不进训练。初判当时只能预测退化候选会正式得 1，作者的正式证据证实了这一点。
- 初判多出的两点：§4 第 1 步也命中（T2a）；P5 分支的依据比较（见主张 5）。

## 1. 逐条核对

| # | 作者主张 | 判断 | 依据 |
| --- | --- | --- | --- |
| 1 | `assert_eq` 对 masked 数组只比较未屏蔽位置的值、不比较 mask；empty 分支显式比较 `getmaskarray`（result.md:21） | **同意，需精确化** | base `dask/array/utils.py:176-177`：任一侧有 `mask` 就调用 `np.ma.allclose(a, b, masked_equal=True)`。numpy 1.26.4 `numpy/ma/core.py:8182` 先对两侧 mask 取并集，`:8189-8191` 再把并集位置填 True。所以准确说法是**只比较两侧都未屏蔽的位置**；mask 取反时并集覆盖全部位置，一个值也不比较（见 §2 反例 1）。`assert_eq` 除类型和 dtype（`utils.py:321,331`）外，还查 shape（`:325`）、meta（`:334-372`）、chunks（`:225-240`）；这不影响结论。empty 分支：测试补丁应用后 `test_masked.py:445-446`。 |
| 2 | `ma_mask_none`、`ma_mask_invert` 在原材料正式得 1，值、dtype、类型都对，只有 mask 错（result.md:29-30,41-42） | **同意** | **账本** `evidence/formal/ledger_ma_mask_{none,invert}.jsonl`：reward 1.0、F2P 3/3、P2P 失败 0/134、`reference_missing_count` 0、`apply_ok` true；投影只含 `dask/array/ma.py`；`patch_sha256` 与 `ma_mask_none.patch`（`41244f3d…`）、`ma_mask_invert.patch`（`c9f68c60…`）一致；清理 `rm:ok`；以 `rh2grader`、`deny_all` 运行。<br>**日志**：`formal/eval_logs/…ma_ma_697733c2.eval.log:651` 是 `mask=False`，`…ma_ma_17c1a605.eval.log:651` 是 `mask=~np.ma.getmaskarray(x)`；两份日志 `:1098-1100` 三项 PASSED，`:1252` 为 “137 passed”；日志 SHA256 与账本 `log.sha256` 一致。<br>**值、dtype、类型**：`semantic_v1/ma_mask_{none,invert}/b1_behavior.out:93-113` 中，`fixture.ma.ones_like/zeros_like` 为 `MaskedArray`、`int64`，`all_values_equal=true`，`mask_equal_numpy=false`；`empty_like` 的 `mask_equal_numpy=true`，其补丁与 gold 相同。<br>我的私有 pytest 矩阵（§3）得到相同结果。<br>**措辞**：`ma_mask_none` 不是 “mask 全错”（result.md:7,41）；它只在输入被屏蔽的位置出错（测试数据 6 个位置中 4 个），`ma_mask_invert` 才是每个位置都错。 |
| 3 | 修订测试 v1 下两个退化候选 0、gold 1、noop 0（result.md:57-65） | **同意** | **账本** `evidence/formal_revised_v1/ledger_*.jsonl`：gold 1.0（3/3）、noop 0（0/3）、`ma_mask_none` 0（1/3）、`ma_mask_invert` 0（1/3）、`toplevel_only` 0（0/3）；P2P 均 0/134 失败；参考缺席 0；grader 版本带 `+c3-dask9378-mask-equality-v1`；`scripts_digest` 由原版的 `baf55642…` 变为 `f2b83e18…`。<br>**失败位置**：`rev1-_4a24bb20.eval.log`（none）与 `rev1-_687fb23f.eval.log`（invert）的 `:1123`、`:1263` 都指向 `test_masked.py:446`，即新增的 mask 断言；`:1240` 打印的结果 mask 分别是全 False 和取反。<br>**补丁哈希**：`materials.json` 的 `original_patch_sha256`（`7ea58fb7…`）与我从 grading bundle 原 `test_patch` 重新计算的值一致；`revised_patch_sha256`（`67393733…`）与 `revised_test_v1.patch` 一致。 |
| 4 | 修订断言：三个函数都先比较 `getmaskarray`，ones/zeros 再保留原 `assert_eq(res, sol)`（result.md:55）。是否有公开依据、是否过严 | **同意：有依据，不过严** | **依据**：题标题、请求句 “preserve masks”，以及 `[1 1 --]` 示例。<br>**改动范围**：修订只是把原 empty 分支已有的比较推广到 ones/zeros（与原补丁的 diff 只动了 `:445-448`），测试编号不变。修订版约束是原版的超集，原来失败的候选修订后仍失败。<br>**不过严的核对**：<br>- empty_like 的未初始化值仍不比较；<br>- 被屏蔽位置下的数据仍不比较；<br>- 没有新增 API 名、实现方式或惰性要求。<br>**私有矩阵实测**（§3）：非 gold 的正确替代设计 `alt_correct`（顶层 `*_like` 结果再挂上 `getmaskarray(a)`）在修订版三项通过；gold 加顶层修复也三项通过。 |
| 5 | 只修顶层得 0，按 P5 处理：测试读法有公开依据，走 R-f 补一句，不需交用户（result.md:50,67） | **同意结论，论证需补全** | **测试读法有直接依据**：<br>- 题面末段点名 `dask.array.ma.ones_like, etc.`；<br>- numpy 1.26.4 本身有 `np.ma.ones_like/zeros_like/empty_like`，而 `dask/array/ma.py` 一贯用 `@derived_from(np.ma)` 镜像 `numpy.ma`；<br>- dask 已有把 mask 感知版放在 `da.ma` 的先例：`da.ma.average`（`ma.py:172-174`，`is_masked=True`）对 `da.average`（`routines.py:2492-2493`，`is_masked=False`）。<br>**“只修顶层”只有间接依据**：来自 “Currently” 例子用的是顶层函数。没有文档、API 或旧测试支持：<br>- 顶层 `*_like` 的签名与 docstring 不含 `subok`，返回写作 `out : ndarray`（`creation.py:31-182`）；<br>- `test_creation.py` 没有 masked 用例；<br>- `docs/source` 里除 `array-api.rst` 的 `ma.*` 清单外，没有相关说法。<br>因此它不构成 “两种读法都有依据”，不需交用户。<br>**不是 T1**：T1 针对没有公开依据的实现约束，而 `da.ma.*_like` 是题面点名的公开 API。<br>**不宜改测试去接受两种设计**：§5 写明 R-b 不处理 P5；测试也不惩罚两处都改（gold 加顶层修复在两版都过），只拒绝缺 `da.ma` 入口的候选。<br>**R-f 草句**（result.md:67）只含题面已出现的函数名，不含测试数据、mask 形状或断言写法，符合 §5 R-f 边界；尚待新公开读者验收。<br>**不足**：作者写 “只修顶层的设计也合理”，却没说明为什么不落入第二分支，读者容易理解成应交用户。 |
| 6 | 转第2类，交接四项（result.md:5,69-74） | **同意转第2类；交接基本完整，缺几项说明** | 第3类 README:18-22 的第二种结论成立：问题与修法都已明确，gold 可作正对照。缺的说明见 §5 非阻断建议 3。依据：D6 `category2_repair_20260929/d6/implementation_brief.md:7,51,117-118` 显示首片只支持 mypy 的追加 P2P，测试补丁替换与 `statement_replace` 都还没实现。 |
| 7 | gold 可继续作正对照（result.md:51）；不存在 T2c（result.md:80） | **同意** | gold 在修订版正式诊断评分中 137 passed（`rev1-_fbee4890.eval.log:1090-1092,1244`），私有矩阵也通过。测试数据是 3×2、`chunks=2`、另一种 mask，不是题面的 `[2,3,4]`/`[0,0,1]`。 |
| 8 | 证据归档完整（result.md:92） | **同意** | `evidence_manifest.json` 登记 141 项，其中 78 项已归档；我逐个重算 SHA256，78 项全部一致。其余 63 项按 `environment.md` §4 未归档（artifacts、prepared/private、超大文件）。result.md 的三个相对链接都能解析到实际文件。 |

## 2. 新发现的问题或反例

1. **mask 取反时，原测试连值都不查（强化 S1）。**
   - 候选 `invert_values7`：ones/zeros 每个位置填 7 且 mask 取反，empty 同 gold。
   - 结果：原测试三项全过；修订版下 ones/zeros 失败（§3）。
   - 原因：`np.ma.allclose` 的 mask 并集覆盖了测试数据全部 6 个位置。
   - 含义：原断言在这类输出上完全空转，不只是 “漏查 mask”。
2. **§4 第 1 步也命中（T2a）。** ones/zeros 保留 mask 是题面核心要求，原测试没有直接断言。作者只记了 T2b。两者去向相同（S1 → R-c），建议题卡同时登记。
3. **惰性没有覆盖（T3，原有缺口，修订未改）。** 候选 `eager` 在函数内先 `.compute()`，再调用 `np.ma.core.*_like`，返回 numpy MaskedArray 而不是 dask Array；它在原版和修订版都三项全过。题面没有把惰性列为核心要求，登记即可，不建议本轮加断言。
4. **P2P 不含顶层创建测试（T6/T3，登记）。**
   - P2P 134 项全在 `test_masked.py`。一个同时改顶层的候选如果改坏普通数组的 `*_like`，评分发现不了。
   - 作者的 `toplevel_only` 在 `test_creation.py -k arr_like` 320 项全过（`semantic_v1/toplevel_only/b3_public_creation_like.out`），目前没有反例。
   - 按 §5 “没有误拒案例的修订，不必专门造”，只登记，不要求本轮修。
5. **`empty_like` 分支不查 dtype 与返回类型（T3，原有）。** 修订保持不变，这是合理的：题面对 empty 只要求 mask。
6. **背景事实，不影响处置。** base 上顶层 `da.ones_like(masked)` 的 `_meta` 是 `MaskedArray`，但计算结果是 `ndarray`。因此在 `da.ma` 下直接别名顶层函数，会在 `assert_eq` 的类型检查处失败（见初判的私有检查）。

## 3. 复核者的私有复现（非正式评分）

**方法**
- 命令：`docker run --rm --network none -v <scratch>:/s:ro --entrypoint bash xingyaoww/sweb.eval.x86_64.dask_s_dask-9378:latest /s/run_matrix.sh`。
- 每个组合先把 `/testbed` 复位，再应用候选，并把 `test_masked.py` 恢复到 base 后套用原测试补丁或 `revised_test_v1.patch`。
- 然后运行 `pytest -p no:cacheprovider -n0 -q -rA --color=no dask/array/tests/test_masked.py -k test_like_funcs`。
- 墙钟 28 秒。只跑 F2P 三项，不跑 P2P。
- 所用补丁的 SHA256 与账本、`materials.json` 一致：gold `073b18f0…`、none `41244f3d…`、invert `c9f68c60…`、toplevel `f9762bb1…`、原测试 `7ea58fb7…`、修订 `67393733…`。

**复核者自建的三个候选**（只在容器内追加到 `dask/array/ma.py`，未入库）：
- `invert_values7`：ones/zeros 每块返回 `np.ma.masked_array(np.full(r.shape, 7, dtype=r.dtype), mask=~np.ma.getmaskarray(x))`，empty 同 gold。
- `alt_correct`：`masked_array(<顶层 *_like>(a, **kw), mask=getmaskarray(a))`。
- `eager`：`np.ma.core.*_like(asanyarray(a).compute(), **kw)`。

| 候选 | 原测试 ones / zeros / empty | 修订 v1 ones / zeros / empty |
| --- | --- | --- |
| noop | F / F / F | F / F / F |
| gold | P / P / P | P / P / P |
| `ma_mask_none`（作者） | P / P / P | F / F / P |
| `ma_mask_invert`（作者） | P / P / P | F / F / P |
| `toplevel_only`（作者） | F / F / F | F / F / F |
| gold + `toplevel_only` | P / P / P | P / P / P |
| `invert_values7`（复核者） | **P / P / P** | F / F / P |
| `alt_correct`（复核者） | P / P / P | P / P / P |
| `eager`（复核者） | P / P / P | P / P / P |

## 4. 阻断项

无。

## 5. 非阻断建议

1. **补 P5 分支理由。** 在 result.md §3 写明为什么不属于 “两种读法都有依据”：
   - 只修顶层能修好示例，是能想到的读法，但没有文档、API 或旧测试支持 “顶层 `*_like` 必须保留 mask”；
   - `numpy.ma` 有同名函数，dask 也已有 `da.ma.average` / `da.average` 的分工。

   同时把 “也合理” 改成 “可以想到但无公开依据”。
2. **措辞与登记。**
   - 同时登记 T2a。
   - “mask 全错” 改为 “mask 全不屏蔽” 与 “mask 取反”。
   - §2(1) 改为 “只比较两侧都未屏蔽的位置”，并可引用 `invert_values7` 反例。
3. **交接补充**（供第2类使用）：
   - (a) 写明本题依赖 D6 尚未实现的两类修订：测试补丁替换（D6 brief 计划随 MONAI5932 接入）和 `statement_replace`（计划随 mypy15184 接入）。在它们落地前，本题不能入库。
   - (b) 写明 D6 落地前的用途：训练候选为 no；能力比较至多 conditional，条件是预先登记两项事后审计——ones/zeros 的 mask 是否与输入一致，以及是否因只修顶层而得 0，原始 reward 与语义结果分列；否则只作问题定位。
   - (c) 按 §5 R-c 验收，列出修订后仍受保护的公开要求：ones/zeros 未屏蔽位置的 1/0 值、dtype、shape、`MaskedArray` 类型与 meta 一致性；三者的逐元素 mask。
   - (d) R-f 需登记父版本题面 SHA（public bundle 的 `problem_statement_sha256` 为 `sha256:0a0975ae…`），并形成完整修订题面后再交新公开读者。
   - (e) 注明修订后的题只能作 “标明版本的自建题”。
4. **登记 T3/T6 缺口**：惰性、P2P 不含顶层创建测试、empty 不查 dtype。按 §8 抽查，不要求本轮修。
5. 本复核完成后，由作者或协调者更新 result.md:11,78 的 “独立复核待做” 和第3类 README 表格。本复核没有改动这些文件。

## 6. 未查

- **正式评分**：按角色限制，我没有跑 `replay_grade.py`。原版与修订版的正式分数全部取自作者的账本与日志；我的私有 pytest 只覆盖 F2P 三项，没跑 P2P。
- **未涉及的范围**：真实模型候选；actor 开发条件；上游 dask PR 讨论；`dask/array/wrap.py` 的实现细节；D6 代码实现；新公开读者对 R-f 草句的验收。
- **未读的旧调查文件**：`quality_expansion_20260925/results/dask__dask-9378/` 下的 `analysis_before_history.md`、`reviewer_initial.md`、`old_findings_delta.md`、`screening_record.json`。
