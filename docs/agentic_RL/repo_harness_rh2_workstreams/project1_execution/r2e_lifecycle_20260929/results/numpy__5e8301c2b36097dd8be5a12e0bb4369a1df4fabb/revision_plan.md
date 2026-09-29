# numpy `5e8301c2` 修订方案与试跑验收（R-c，替代正对照 C-A，2026-09-29）

修订执行者（Claude 子代理，单题闭环试行）。本题按统一标准 v1 §5 的 R-c 模板和 §9 D4 的替代正对照规则执行；Codex 复核与正式材料由协调者负责。本文件是修订草案和试跑记录，**不是正式修订单**。

路径缩写（均相对仓库根）：

- `PUB` = `runs/r2e_static_prep_20260924/v3/public/numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb`
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb`
- `CANDS` = `runs/r2e_actor_20260925/grader_cands`
- `GR` = `runs/r2e_actor_20260925/grader`
- `REV` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb`
- `CX` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_batch2_review_20260925`
- `STD` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md`
- `trials/`、`cands/` = 本目录下的试跑结果与新构造的补丁

## 0. 结论

- **模板**：R-c，共两处窄修订，都加在隐藏测试 `test_1.py` 的 `check_einsum_sums` 末尾，也就是已有的 gh-10343 断言块所在的位置。这个 helper 由 15 个 `test_einsum_sums_*` 目标键调用。**期望映射不变**（35 键全 PASSED）。这两处就是 v1 §10 对本题的书面结论（`STD:260`）。
  - 第 1 处（v1 §4 第 2 步，只测了示例方向）：补交换操作数顺序，即单例操作数在前。它堵住只放宽一个方向的 C-C。
  - 第 2 处（v1 §4 第 4 步，同一核心要求的求和维实例）：补两个操作数、被求和标签一侧为 1 的收缩。这种收缩会走 BLAS 分支，**原 gold 通不过**。按 D4，改用经独立核实的替代解 C-A 作正对照，并记录原 gold 的失败。
- **试跑（同一镜像，一轮修订、一轮验收，已收敛）**：
  - 正对照 C-A 为 1；另一个独立的合理实现 UP（上游写法）也为 1。
  - noop、C-C、原 gold 都为 0。
  - C-C 和 gold 在同镜像的原版材料上都是 1（`trials/cur_CC.json`、`trials/cur_gold.json`）。
- **需要协调者特别处理的后果**：修订后，**本题的 gold 补丁本身得 0**。正式流程里如果有“gold 必须得 1”的校验（材料步骤、validation bundle 的 gold 对照、探针预检等），本题要按 D4 改用 C-A 作正对照，并登记 gold 的失败。这是 D4 已授权的做法，不属于新的用户决定；但它会影响正式材料怎样落地，见 §7。

## 1. 父版本与试跑环境

- **父版本**：`PRIV/hidden_tests/test_1.py`，sha256 `799c5db85a3a00d89af16a0473d1464a8ebffba828dc1f5e9048db77bf18cfe8`（与 `grading_bundle.json` 一致）。`PRIV/expected_output.json` 35 键全 PASSED，`material_revisions` 为空。
- **修订后**：`test_1.py` 的 sha256 为 `18a7570132d2f0bab3a584ecd2325f4bfe921d657bac74bfde7448ac94231897`（本机按 §3 的 edits 替换，并用 `ast.parse` 检查语法）。
- **镜像**：`sha256:df792ef10616bb4d8f173695b0d4ac7c6c19107dd799be778ed13f5083a6e867`，配方 `r2e_derive_v1+sysconfig_v1`。
- **试跑工具**：`rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`，不是正式评分（差别见文件头第 8–9 行）。
- **当前材料确认**：`trials/cur_noop.json` 为 mismatch，15 个 `test_einsum_sums_*` 键 FAILED，报题面原句 `Size of label 't' for operand 1 ...`；`trials/cur_gold.json` 为 match（35/35）。

## 2. 要纠正的误判与公开依据

### 2.1 第 1 处：单例操作数在前（T2c，v1 §4 第 2 步）

- **误判**：目标断言只用了题面示例的顺序，即 `p`（10×2）在前、`q`（1×2）在后（`PRIV/hidden_tests/test_1.py:484-490`）。
  - C-C 只在“后出现的尺寸为 1”时放宽检查（`CANDS/numpy_5e83_CC_relax_one_direction.patch`），在原版得 1。证据：`GR/ledger_np5_CC.jsonl` 35/35；本次同镜像 `trials/cur_CC.json` 为 match。
  - 交换顺序后，C-C 仍抛题面原句（`GR/numpy5e83_extra/CC.json`；批次记录 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/grader_candidates.md:97-105`）。
- **公开依据**：
  - 题面泛指 singleton dimensions，期望用广播处理（`PUB/user_prompt.txt:7`、`:21`），没有限定哪个操作数带单例维。广播本身与操作数顺序无关。
  - base 的尺寸检查以先出现的尺寸为准（`PUB/worktree/numpy/core/einsumfunc.py:706-714`）。所以交换顺序后，base 报的是同一类错误。公开读者在没看私有材料时就列出了这条要求（`REV/public_read.md:20` 的 R3）。

### 2.2 第 2 处：被求和的单例标签，两个操作数（v1 §4 第 4 步，S1；gold 通不过）

- **误判**：隐藏测试只测了 `'ti,ti->i'`。在这个例子里，`t` 在两侧都保留在输入中，`_can_dot` 按“partial inner”返回 False，于是不走 BLAS。
  - 如果被求和的标签一侧为 1，`_can_dot` 会选中 `tensordot`（`PUB/worktree/numpy/core/einsumfunc.py:342` 的 DDOT 分支，`:355-357` 的 GEMM 分支）。而 `tensordot` 要求尺寸严格相等（`PUB/worktree/numpy/core/numeric.py:1289`）。
  - 结果是 gold 式补丁在这类输入上改报 `ValueError: shape-mismatch for sum`。原版评分测不到这一点，gold 与 gold 式补丁都得 1。
- **公开依据**：
  - 题面标题说的是优化时遇到 singleton dimensions 报 ValueError（`PUB/user_prompt.txt:4`）；描述泛指（`:7`）；期望“不报错、按广播处理”（`:21`）。
  - base 在这类输入上报的正是题面那一类错误：`np.einsum('i,i', [2., 3.], [4.])` 在 base 上报 `Size of label 'i' for operand 1 does not match previous terms.`，`optimize=False` 返回 20.0（`GR/numpy5e83_extra/extra2_none.json`；批次记录 `grader_candidates.md:107-113`）。本 base 的 `einsum` 默认 `optimize=True`（`PUB/worktree/numpy/core/einsumfunc.py:1062`）。
  - 参照语义是 `optimize=False` 的 `c_einsum`，它会把尺寸 1 的标签广播出去（`REV/public_read.md:19` 的 R2 及其引用的 `einsum.c.src` 行）。公开测试也以 `optimize=False` 作对照（`PUB/worktree/numpy/core/tests/test_einsum.py:578`、`:586`、`:692` 等）。
  - Codex 第二批复核 NP-2 指出：gold 的失败不能用来划定公开修复范围；两个操作数的单例求和维要与更广的多操作数、路径规划问题分开，前者有公开依据（`CX/numpy_pillow/README.md:62-76`）。v1 §10 据此判为 S1，走 R-c，用 C-A 作替代正对照（`STD:260`）。
- **范围**：只加两个操作数、一次收缩的情形。不加三个及以上操作数、中间收缩或路径规划，也不测 `einsum_path` 本身（它的范围未定，`REV/public_read.md:22-23` 的 R5、R6；`CX/numpy_pillow/README.md:74`）。

### 2.3 选用的输入

- `'i,i'`，`x = [1., 2., 3.]`，`y = [5.]`，结果 30：一维内积，被求和的 `i` 一侧为 1。
- `'ij,jk->ik'`，`a = arange(6.).reshape(2, 3)`，`b = arange(1., 5.).reshape(1, 4)`：矩阵乘，被求和的 `j` 一侧为 1。结果是 `[[3, 6, 9, 12], [12, 24, 36, 48]]`，即 `a` 的行和乘以 `b[0]`。
- 数据都是小整数值的浮点数。不论走 BLAS 还是 `c_einsum`、按什么顺序求和，结果都精确，所以沿用块内的 `assert_array_equal` 不会因为舍入误拒合理实现（`CX/numpy_pillow/README.md:104`：非整数输入要允许合理舍入误差）。
- 断言只比较结果，不检查走哪条路径、是否调用 BLAS helper。
- 有意没有照抄上游 #10930 测试的取值（`[2., 3.]` 与 `[4.]`）。那个测试出现在同仓后续题的公开工作树里（`REV/review.md` §4 第 1 条）。这只是避免逐字重复，同仓 X1 关系依然存在，见 §6。

## 3. 具体改动（`r2e_tests/test_1.py`，`check_einsum_sums` 末尾）

修订后的块如下；标 `+` 的是新增行：

```python
        # singleton dimensions broadcast (gh-10343)
        p = np.ones((10,2))
        q = np.ones((1,2))
        assert_array_equal(np.einsum('ti,ti->i', p, q, optimize=True),
                           np.einsum('ti,ti->i', p, q, optimize=False))
        assert_array_equal(np.einsum('ti,ti->i', p, q, optimize=True),
                           [10.] * 2)
+       # the singleton operand may also come first
+       assert_array_equal(np.einsum('ti,ti->i', q, p, optimize=True),
+                          np.einsum('ti,ti->i', q, p, optimize=False))
+       assert_array_equal(np.einsum('ti,ti->i', q, p, optimize=True),
+                          [10.] * 2)
+
+       # a singleton label that is summed over (two operands)
+       x = np.array([1., 2., 3.])
+       y = np.array([5.])
+       assert_array_equal(np.einsum('i,i', x, y, optimize=True),
+                          np.einsum('i,i', x, y, optimize=False))
+       assert_array_equal(np.einsum('i,i', x, y, optimize=True), 30.)
+       a = np.arange(6.).reshape(2, 3)
+       b = np.arange(1., 5.).reshape(1, 4)
+       assert_array_equal(np.einsum('ij,jk->ik', a, b, optimize=True),
+                          np.einsum('ij,jk->ik', a, b, optimize=False))
+       assert_array_equal(np.einsum('ij,jk->ik', a, b, optimize=True),
+                          [[3., 6., 9., 12.], [12., 24., 36., 48.]])

    def test_einsum_sums_int8(self):
```

- 条目格式见 `revision_draft.json` 的 `revisions`：一条 `hidden_test_text_replace`，含两个 edit。
  - 第 1 个 edit 以块内 `[10.] * 2)` 结尾的那条断言为锚点。
  - 第 2 个 edit 以 `def test_einsum_sums_int8(self):` 为锚点，把新块插在它前面，仍在 `check_einsum_sums` 函数体内。
  - 两个锚点在父版本里各出现一次，可以单独应用。
- 修订后第 491–495 行是交换顺序，第 497–508 行是求和维。新块用到的名字 `x`、`y`、`a`、`b` 在函数末尾之后不再使用。新增代码只用 ASCII 字符。

## 4. 期望映射的逐键变化

**无变化。** 仍是 35 键，全部 PASSED。新断言在已有的 helper 里，键集与状态不变。15 个 `test_einsum_sums_*` 目标键现在同时检查题面示例、交换顺序和求和维；其余 20 个回归键不受影响。

## 5. 正对照 C-A：独立核实依据

- **补丁**：`CANDS/numpy_5e83_CA_gold_plus_blas_guard.patch`，sha256 `63198523bc33a44c…`。它在 gold 的尺寸检查之上，在 `einsum()` 的收缩循环里加了一个守卫（补丁第 26–29 行）：如果这一步要走 BLAS，而某个被求和标签在两个操作数中的长度不同，就改走 `c_einsum`。
- **为什么满足公开要求**：
  - 尺寸检查接受任意顺序的“1 对 N”，同时仍拒绝两边都不为 1 且不相等的尺寸。
  - 通过检查之后，被求和标签两侧长度不同就说明有一侧为 1。这时交给会广播的 `c_einsum`，结果等于 `optimize=False` 的结果。
  - 两侧长度相同的正常输入不触发守卫，原有路径和 `TestEinSumPath` 的路径断言都不受影响。
- **执行证据**：
  - 当前材料上正式评分 35/35（`GR/ledger_np5_CA.jsonl`，derived9 镜像）。
  - 私有语义命令：交换顺序输出 `[10. 10.]`；`(2,3)×(1,4)` 的随机矩阵与 `optimize=False` 一致；`'i,i'` 在不传 `optimize` 时得 20.0（`GR/numpy5e83_extra/CA.json`、`GR/numpy5e83_extra/extra2_numpy_5e83_CA_gold_plus_blas_g.json`）。
  - 本次修订草案上 `trials/rev_CA.json` 为 match（35/35）。
- **独立复核**：第二批独立复核把 C-A 的“更完整的修复不会被误拒”记为执行确认（`REV/review.md` §0 表、§3）。Codex 第二批复核接受 C-A 覆盖了私有检查中的两类失败，并仍得 35/35（`CX/numpy_pillow/README.md:16`）。
- **第二个独立实现**：补充构造了 UP（`cands/numpy_5e83_UP_upstream_bcast_nix_blas.patch`，sha256 `aebf0307aff6a3d91521f50fb59f4339e2c421dc595534487e988e6647676941`）。它就是复核者提出、未执行过的候选 D，按同仓后续题公开工作树里的上游写法改写到本 base 上（参照 `runs/r2e_static_prep_20260924/v3/public/numpy__43e333e2ff641f6dce852e46c9c650333b0d4b3d/worktree/numpy/core/einsumfunc.py:857-953`）：
  - 在 `einsum_path` 里记下哪些标签的尺寸为 1；
  - 如果被求和的标签在其中，这一步就不走 BLAS。
  
  UP 在修订草案上也是 match（`trials/rev_UP.json`）。这说明新断言不只拟合 C-A 一种写法。模型可能凭记忆写出上游写法，所以值得查它会不会被误拒。
- **原 gold 的失败**：`trials/rev_gold.json` 为 mismatch，15 个 `test_einsum_sums_*` 键 FAILED，报 `ValueError: shape-mismatch for sum`（`numpy/core/numeric.py:1289`）。这个错误只可能来自新增的求和维块：原断言和交换顺序断言用的是 `'ti,ti->i'`，不会走 `tensordot`。原版材料上 gold 为 match（`trials/cur_gold.json`）。

## 6. 验收计划与试跑结果

全部在 §1 的镜像上运行，带修订草案，`--expected current`。

| 候选 | 补丁 | 应得 | 应在何处失败 | 试跑 | 实际 |
| --- | --- | --- | --- | --- | --- |
| C-A（正对照） | `CANDS/numpy_5e83_CA_gold_plus_blas_guard.patch` | 1 | — | `trials/rev_CA.json` | match（35/35） |
| UP（第二个合理实现，查误拒） | `cands/numpy_5e83_UP_upstream_bcast_nix_blas.patch` | 1 | — | `trials/rev_UP.json` | match（35/35） |
| 原 gold（记录失败） | `PRIV/gold.patch` | 0 | 求和维块 | `trials/rev_gold.json`；原版 `trials/cur_gold.json` 为 match | mismatch；15 键 FAILED，`shape-mismatch for sum` |
| noop | 无 | 0 | 原 gh-10343 断言 | `trials/rev_noop.json` | mismatch；15 键 FAILED，题面原句 |
| C-C（触发反例，原版 1） | `CANDS/numpy_5e83_CC_relax_one_direction.patch` | 0 | 交换顺序断言 | `trials/rev_CC.json`；原版 `trials/cur_CC.json` 为 match | mismatch；15 键 FAILED，`Size of label 't' for operand 1 ...` |

- 每个 mismatch 的不符键都正好是那 15 个 `test_einsum_sums_*`（PASSED → FAILED）。补丁都应用成功，修订都已应用（`RH2_APPLY_RC=0`、`RH2_TRIAL_EDITS_APPLIED=1`）。
- **失败行号怎么定的**：`trial_grade.py` 只保留日志末 8000 字符，这一段被 pytest 打印的 `einsum_path` 与 `tensordot` 源码占满，看不到 `test_1.py` 的行号。所以按报错判定失败位置：
  - C-C 报的是标签 `t` 的尺寸错误。修订后的块里，只有原 gh-10343 断言和交换顺序断言用到 `t`，而 C-C 在同镜像原版上通过了原断言（`trials/cur_CC.json`），所以失败在交换顺序断言。
  - gold 的依据见 §5 末条。
- **对照 v1 §5 的验收条目**：
  - 正对照为 1（C-A，按 D4 使用），noop 为 0：满足。
  - 要纠正的误判已纠正：C-C 与 gold 式补丁都从 1 变为 0。
  - 已知相关错误候选为 0：noop、C-C、gold 式补丁。
  - 合理实现没有被误拒：C-A、UP 为 1。
  - 父版本、新版本、理由和触发反例：见 §1、§2。原 gold 的失败已记录（§5）。
  - Codex 复核：待协调者发起。

## 7. 修订后受保护的要求、仍未覆盖的部分与交接

**受保护（有直接断言）**：

- 题面示例（15 个目标键）；
- 交换操作数顺序；
- 两个操作数、被求和标签一侧为 1 的内积与矩阵乘。三者都与 `optimize=False` 比较，并比对显式数值；
- 其余 20 个回归键，包括 `test_einsum_errors` 与 `TestEinSumPath` 的路径断言。

**仍未覆盖，按 T3 或范围边界登记**：

- 三个及以上操作数、经过中间收缩的广播，以及 `einsum_path` 本身（R5 的多操作数部分、R6）。这属于更广的范围，按 Codex NP-2 与 v1 §10 不并入本轮。
- `optimize='greedy'`、`'optimal'`、显式路径等其它取值。只特判 `optimize is True` 的实现仍能得分（`REV/review.md` §4 第 5 条），登记即可。
- 跨操作数、两边都不为 1 的不兼容尺寸仍应报错。只有同一操作数内 `'ii'` 的用例有断言（`REV/card.md` §2），C-D 类“删掉检查”的候选没有跑。

**X1**：上游的 #10930 修复与相近测试出现在同仓后续题 `numpy__43e333e2`、`numpy__d89bc4bb` 的公开工作树里（`REV/review.md` §2 第 9 行、§4 第 1 条）。本次修订没有改变这层关系，只是让本题的隐藏测试与它们的公开测试在语义上更接近。留出划分按 D3 以仓库为单位；训练时按 X1 控制重复采样。

**交协调者**：

1. 在 `s2_r2e` 下写正式修订单，内容是 §3 的两个 edit，期望映射不变。
2. 本题的正对照登记为 C-A（D4），同时记录原 gold 在修订版上为 0。如果正式材料或派生镜像的材料步骤会用 gold 做自动对照，要为本题改成 C-A 或允许 gold 失败。这需要协调者按正式流程落实；本执行者没有改生产代码或 pins。
3. 在正式评分上复跑 C-A、UP、gold、noop、C-C，然后交 Codex 复核。
4. 远端只执行了本包允许的命令：`mkdir`、`scp`、`trial_grade.py`，同一时间最多 2 个试跑。试跑目录是 `/work/r2e/trials/numpy/5e8301c2/`。
