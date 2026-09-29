# dask__dask-9378 独立复核：初判（读作者结论前封存）

2026-09-29 / 独立复核者（Claude，新会话，不继承作者上下文）。

**封存说明**：本文写于读取作者的 `result.md` 与 `evidence/` 之前；对这两处只看过目录里的文件名（`result.md`、`evidence/{evidence_manifest.json,formal,formal_revised_v1,gold,semantic_v1}`），没有读内容。写完后不再修改，后续核对写入同目录 `review.md`。

## 0. 本次实际读过的材料

- 规则：`project1_execution/task_screening_standard_v1_20260925.md` 全文（重点 §3 P3/P5/T1/T2、§4、§5）。
- 原件：`s2/ingest/public_bundles_v0.jsonl`、`validation_bundles_v0.jsonl`、`grading_bundles_v2_v0.jsonl` 中 `instance_id == "dask__dask-9378"` 的三条记录（题面、public_hints、gold、test_patch、3 个 F2P、134 个 P2P）。
- 既有调查：`swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-9378/` 下的 `card.md`、`public_read.md`、`review.md`。其余文件（`analysis_before_history.md`、`reviewer_initial.md`、`old_findings_delta.md`、`screening_record.json`）未读。
- base 源码：只读镜像 `xingyaoww/sweb.eval.x86_64.dask_s_dask-9378:latest`（本机镜像 ID `sha256:1e5a0ee85016…`，RepoDigest `@sha256:d59dc8d2aa23…`，与 public bundle 的 `image_manifest_digest` 一致），`/testbed` HEAD `8b95f983c232c1bd628e9cba0695d3ef229d290b`，Python 3.10.14，numpy 1.26.4。读了 `dask/array/utils.py:16-20,172-184,225-386`、`dask/array/ma.py` 全文（1-192）、`dask/array/creation.py:31-182`、`dask/array/routines.py:2439,2476,2492-2493`、`docs/source/array-api.rst:352-375`，以及 numpy `numpy/ma/core.py:8096-8191`（`np.ma.allclose`）。
- 未读：dask 上游 issue/PR 讨论、`dask/array/wrap.py`、`test_creation.py` 全文（只做了关键字检索）、作者的所有产物。

## (a) 公开核心要求

题面（public bundle 的 `problem_statement`）：

- 标题 “Mask preserving \*_like functions”。
- 请求句：“It would be useful to have **versions of** `ones_like`, `zeros_like` and `empty_like` that **preserve masks** when applied to masked dask arrays.”
- 对照例：`da.ones_like(da.ma.masked_array([2,3,4], mask=[0,0,1])).compute()` 得 `[1 1 1]`，而 NumPy 得 `[1 1 --]`。
- 末段建议：“perhaps the simplest thing would be to implement `dask.array.ma.ones_like`, etc. that way”（“that way” 指 `dask.array.ma` 里已有函数对 `numpy.ma` 版本做 `map_blocks` 的写法）。

据此，核心要求是：**对 masked dask array 调用这三个 `*_like`，结果逐元素保留输入的 mask**；`ones_like`/`zeros_like` 在未屏蔽位置分别为 1/0，结果仍是同形状、同 dtype 的 masked array；`empty_like` 的数值未初始化，不作约束，只约束 mask（与形状/类型）。“保留 mask” 是三个函数共同的、唯一明确的行为要求，不是边缘条件。

## (b) 原 F2P 对 ones_like / zeros_like 是否检查 mask

**不检查。** 断言链（测试补丁应用后 `dask/array/tests/test_masked.py:432-448`）：

- `ones_like`/`zeros_like` 分支只有 `assert_eq(res, sol)`（`:448`）。
- `assert_eq`（`dask/array/utils.py:282-386`）依次检查：dtype 字符串（`:321-322`）、shape（`:325-327`）、计算后的 Python 类型相同（`:328-333`，两边都须是 `MaskedArray`）、meta 类型与计算结果类型一致（`:334-372`）、chunk 形状与 dtype（`:225-240`）；最后值比较走 `allclose(a, b, equal_nan=True)`（`:374`）。
- `allclose` 在任一侧有 `mask` 属性时调用 `np.ma.allclose(a, b, masked_equal=True)`（`utils.py:176-177`）。
- `np.ma.allclose` 先把两侧 mask 取并集 `m = mask_or(getmask(x), getmask(y))`（`numpy/ma/core.py:8182`），再把被屏蔽位置填成 `masked_equal`（即 True）后求 `np.all`（`:8189-8191`）。所以**任一侧被屏蔽的位置都算相等，mask 本身从不比较**。

后果：结果 mask 全 False 时，只在 `sol` 未屏蔽的 2 个位置比较值，1/0 正确就通过；结果 mask 取反时，并集覆盖全部 6 个位置，**任何值都通过**。

`empty_like` 分支（`:445-446`）直接比较 `da.ma.getmaskarray(res)` 与 `np.ma.getmaskarray(sol)`（两个 bool 数组，走 `np.allclose`，等价于逐元素相等），**mask 有检查**；但它不检查 `res` 的 dtype 和类型（只看 mask 数组）。

**私有检查（只读容器，内存中给函数赋值，不改 `/testbed`，不是正式评分）**：

- 脚本：`scratchpad/initial/check_assert_eq.py`（本机临时目录，不入库）。
- 命令：`docker run --rm --network none -v <scratch>:/scratch:ro --entrypoint bash xingyaoww/sweb.eval.x86_64.dask_s_dask-9378:latest -c "cd /testbed && /opt/miniconda3/envs/testbed/bin/python /scratch/check_assert_eq.py"`。
- 做法：照抄测试函数体，把 `da_func` 换成不同实现。

| 实现（按块 `map_blocks`，值/dtype/`MaskedArray` 类型均正确，除非另注） | ones_like | zeros_like | empty_like |
| --- | --- | --- | --- |
| gold 式 `np.ma.core.*_like` | PASS | PASS | PASS |
| mask 全 False | **PASS** | **PASS** | FAIL |
| mask 取反 | **PASS** | **PASS** | FAIL |
| mask 取反且每个位置都填 7 | **PASS** | **PASS** | FAIL |
| 返回普通 ndarray | FAIL（类型） | FAIL（类型） | FAIL |
| 直接用顶层 `da.*_like` | FAIL（类型） | FAIL（类型） | FAIL |

同一脚本还显示，base 上顶层 `da.ones_like(masked)` 的 `_meta` 是 `MaskedArray`，但算出来是普通 `ndarray`（值 `[1 1 1]`）；`da.ma` 在 base 上没有 `ones_like`。

**推论**：要让一个退化候选在正式评分中拿到 1，它必须让 `empty_like` 正确，只把 `ones_like`/`zeros_like` 的 mask 做错。这样的候选全部落在 gold 的修改位置（`dask/array/ma.py`），且明确违反题面“preserve masks”的要求。由于 P2P 的 134 项都是 base 已有的 `test_masked.py` 测试，不会调用新函数，我预计它在正式评分中得 1。**我没有跑正式评分**（本角色不允许），这一步以作者的正式评分证据为准，第二步核对。

## (c) 题面要求的接口，测试接受哪种

- **测试只接受 `dask.array.ma.*_like`**：`getattr(da.ma, funcname)`（`:439`）。只修顶层 `da.*_like`、不新增 `da.ma` 入口的候选，三个 F2P 都在 `getattr` 处 `AttributeError`，得 0。在 `da.ma` 下直接别名到 base 的顶层函数也得 0（类型检查失败，见上表）。同时新增 `da.ma` 入口和修改顶层的候选可以得 1。P2P 只含 `test_masked.py`，不含 `test_creation.py::test_arr_like*`，所以改坏顶层 `*_like` 不会被评分发现（见 (d) 非阻断项）。
- **新增 `da.ma.*_like` 的公开依据（直接、多条）**：
  1. 题面末段点名 `dask.array.ma.ones_like, etc.`，这是题面里唯一给出的具体 API。
  2. 请求句是 “versions of … that preserve masks”，字面上是另一组版本。
  3. numpy 1.26.4 本身就有 `np.ma.ones_like/zeros_like/empty_like`（`np.ma.ones_like is np.ma.core.ones_like` 为 True），而 `dask/array/ma.py` 一贯按 `numpy.ma` 同名镜像（`@derived_from(np.ma)`，`ma.py:21-192`）。
  4. dask 已有先例：mask 感知版放在 `da.ma`，顶层版不感知 mask。`da.ma.average` 用 `is_masked=True`（`ma.py:172-174`），`da.average` 用 `is_masked=False`（`routines.py:2492-2493`）。
- **“只修顶层”的依据（间接）**：题面的 “Currently” 例子用的是顶层 `da.ones_like`，并与 NumPy 顶层 `np.ones_like` 对比；按 “dask 应与 numpy 一致” 的一般期待，可以推出应修顶层。但 dask 顶层 `ones_like` 的 docstring 与签名不含 `subok`，返回值写作 `out : ndarray`（`creation.py:87-122`）；公开旧测试中也没有断言顶层 `*_like` 在 masked 输入上的行为（`test_creation.py` 无 `np.ma`/`masked` 字样，`test_masked.py` 无 `_like` 字样）。题面也没有说 `da.ones_like` 的现行为是缺陷或必须改。
- **判断**：两种读法都“能想到”，但依据强度不对称。测试采用的读法有题面点名加 API 惯例的直接依据；另一种只有从例子推出的间接依据，没有文档、API 或旧测试支持。按 P5 第一分支，走 R-f 补一句即可。这不是 T1：T1 针对没有公开依据的实现约束，而 `da.ma.*_like` 是题面点名的 API。也不应改测试去“接受两种设计”：§5 明写 R-b 不处理 P5，按 P5 也不能把两种设计用“或”并起来；而且那样会放弃题面点名、`numpy.ma` 对称的入口。

## (d) 初判处置

1. **严重度：S1。**
   - §4 第 1 步命中 T2a：`ones_like`/`zeros_like` 保留 mask 属于核心要求，但参考测试没有直接断言。
   - 第 3 步预计命中 T2b：只错 mask、其余正确的退化候选预计得 1，待核正式证据。
   - 第 2 步不命中：测试输入是 3×2、`chunks=2`、另一种 mask，不是题面 `[2,3,4]`/`[0,0,1]` 的字面值。
   - 第 4 步没有真实模型候选，未查。
2. **R-c**：给 `ones_like`/`zeros_like` 补直接的 mask 相等断言。
   - 最小写法：三个函数都比较 `getmaskarray(res)` 与 `getmaskarray(sol)`，并保留原来的 `assert_eq(res, sol)`。
   - 依据：题标题、请求句、`[1 1 --]` 例。
   - 不应比较 `empty_like` 的未初始化值；也不应要求超出题面的参数（`dtype`/`shape` 覆盖等）。
   - 验收：gold 为 1、noop 为 0，本次两类只错 mask 的退化候选为 0。
3. **接口歧义：P5 第一分支，走 R-f。** 补一句已公开的接口说明，例如“以 `dask.array.ma.ones_like`、`dask.array.ma.zeros_like`、`dask.array.ma.empty_like` 提供，与 `numpy.ma` 对应”。不得写入测试输入、mask 形状等隐藏细节。若 Codex 或用户认为“只修顶层”也有同等依据，再按 P5 第二分支交用户。**我倾向第一分支，不作阻断。**
4. **用途**：
   - SWE-Gym 目前没有测试与题面修订机制（§9 D6、§11），所以本题进训练前必须修，**当前不能作训练候选**。
   - 问题定位：yes。
   - 能力比较：至多 conditional。须预先登记事后审计：mask 是否正确、是否因只修顶层得 0。原始 reward 与语义结果分列。
5. **非阻断项**：
   - `empty_like` 分支不检查 dtype 与返回类型；gold 的 `**kwargs` 经 `map_blocks` 时 `dtype` 被当成元数据，不会传进 numpy 内核；惰性（不提前 compute）没有断言。这些都属于 T3，题面没有把它们列为核心要求。
   - P2P 不含 `test_creation.py::test_arr_like*`：选择改顶层的候选若改坏普通数组行为，评分发现不了。可在同一轮 R-c 考虑把这些现成公开测试加进 P2P，但目前没有触发反例，按 §5 不必专门造。

## 未查

- 正式评分（按角色限制不跑）。
- 作者构造的候选实际内容与账本（第二步核对）。
- 真实模型候选。
- 上游 dask PR 讨论。
- `wrap.py` 的实现细节（只用运行结果观察到顶层返回 ndarray）。
