# numpy `d805e9b6` 独立复核（第二步：对照公开读者、主审与今晚实跑）

- 题目：`numpy__d805e9b66228e68a0eb14d901cd350159c49af18`。独立复核者，2026-09-29。第一步初判见同目录 `reviewer_initial.md`（已封存，本文不改它）。
- 证据层级：
  - 【静态】读代码推导；
  - 【正式】RH2 正式评分，由 agent/54321 用 `git_apply` 应用补丁；
  - 【私核】私有行为核对：root 身份、一次性容器，只证明行为事实，不是评分；
  - 【devcheck】真实 Claude Code + 桩端点、agent 身份、正式启动路径；
  - 【历史】09-24 环境轮的记录。
- 路径简写（相对仓库根）：
  - `OUT` = 本题结果目录；`LIFE` = `runs/r2e_lifecycle_20260929/`；`INV` = `LIFE/inv/numpy_d805/`；`DEV` = `LIFE/devcheck/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/`；
  - `PUB`、`PRIV` 同第一步（`runs/r2e_static_prep_20260924/v3/{public,private}/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/`）；
  - `HIST` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/`。

## 0. 结论

| 类别 | 要点 |
| --- | --- |
| **同意** | 处置 `needs_repair`；S1 成立。<br>- T2c：静态即可确定。<br>- T2b：K-DE 正式评分 1.0，私核显示 n=500 时每个值出现两次。<br>- 第 4 步：K-DC、K-DF 正式评分都是 1.0，并且各自在其它实例上违例。<br>K-A5 得 0 是补丁自身的错误，不是误拒；K-A5b 可作补充正对照。<br>P4、G1→T3、子类打印 T3、X1、E3（通用）的登记都同意。<br>新镜像 `c080fc6b…` 上的环境条件已由 devcheck 与正式 noop / gold 核实；我第一步写的"actor 待验"就此解除 |
| **修改** | 1. **R-c 合并**：原样采用主审的两处断言（diff 的 sha256 为 `1092cedb…`），撤回我第一步提的 1200 / 10000 / `str(示例)` / n=200 宽松版。关键理由：我的 n=10000 恰好落在 K-DF 的门槛上（`size > 10000` 不成立），拦不住 K-DF（§3）。<br>2. **验收候选集**：加入 DG-e（只修 `__repr__`）。DG-b 不需要，它在一维上与 K-DE 的行为逐一等价。另建议可选的 DG-g（把全局阈值改成 99），用它实证第 2 处"不得出现 `...`"这半句是必要的（§4）。<br>3. **P4 的 R-f 优先级上调**：第 2 处断言依赖 1000 这个阈值，而题面唯一提到"1000"的地方正是那句失实的 Actual 描述，它还把"显示约 1000 个值"说成缺陷本身。建议 R-f 机制可用后尽快做，不作为 R-c 的前置条件（§6）。<br>4. **用途表述**：R-c 验收后，训练候选应为 conditional（只剩池级条件），不是 yes；X1 的影响是"答案暴露与留出方向"，不是"重复采样"（§7、§8） |
| **保留（有分歧时交协调者）** | 第 2 处采用严格读法（n≤1000 全量显示），我同意主审，不构成 P5。理由与残余风险见 §5；若 Codex 坚持宽松读法，宽松版仍能拦下除 DG-g 以外的全部已知错误候选 |
| **修订能否开做** | **可以。** R-c 用主审 diff 原样实施，按 §10 的矩阵验收，再交 Codex 复核。P4 的 R-f 等机制实现后做，不阻塞 R-c |

## 1. 本步新读范围

- 公开读者：`OUT/public_read.md` 全文、`OUT/commands.json` 全文。
- 主审：`OUT/analysis_before_history.md`、`old_findings_delta.md`、`card.md` 全文；`screening_record.json` 的 issues、disposition、usage、candidate_runs、recipe_ref、costs；`OUT/cands/` 下 6 个文件全文。
- 历史（`PUB` 同级的 `…/v3/history/numpy__d805…/refs.json` 列出的 8 项）：
  - 本题 `HIST/tasks/numpy__d805…/findings.md` 全文；
  - 同目录 `screening_record.json`、`facts.json` 的全部字段（长字段截断到约 700 字）；
  - `HIST/repros/numpy__d805….py` 全文；
  - `known_issues.json` L70–112、L235–275；
  - `decisions.md`、`results_20260924.md`、`packages/p2/README.md` 只 grep 了本题与 E03 / E06 / E09 / E10。
- 实跑：
  - `LIFE/env_verify/ledger_l0_{noop,gold}.jsonl` 第 6 行（这两次的 eval 日志只有远端路径，本地没有）；
  - `INV/ledger_{KDE,KDC,KDF,KA5,KA5b}.jsonl` 第 1 行；5 份 eval 日志的头部、L73、L258，以及 KA5 的 L28–80、L311；
  - `INV/pcheck_*.json`（7 份）、`run.sh`、`run.log`、`run_b.log`、`private_check_6_3.py`；
  - `DEV/orig/attempt.json` 的 checks 与 commands_result、`prelaunch.json`、`activation_check.json`、`captures/*.out`（8 份）、`DEV/private_control.json`。
- 公开包补读：`PUB/worktree/doc/release/1.11.0-notes.rst` L245–262。
- 本地辅助（只在 scratch 目录 `…/scratchpad/agents/rev_numpy_d805e9b6/`）：
  - 对隐藏测试副本 `git apply` 主审 diff，再做 AST 解析；
  - 对 base `numpy/ma/core.py`（blob `35c1ec79…`，等于 gold 的 pre-image）和 `numpy/core/arrayprint.py`（blob `282fbd1c…`）的副本，生成 DG-e / DG-b / DG-g 三个 diff 并 `git apply --check`。
  - 没有运行项目代码。

## 2. 主审决定性主张逐项核对

| 主张 | 核对结果 | 依据 |
| --- | --- | --- |
| T2c：唯一核心断言就是题面示例原样 | 同意（与我第一步一致） | `PRIV/hidden_tests/test_1.py:454-461` 对照 `PUB/user_prompt.txt:10-25` |
| T2b：退化候选 K-DE（截取量写死为 750，截取条件不变）得 1 | 同意；K-DE 是合格的第 3 步候选：落在 gold 的修改位置，截取量是与输入无关的固定值 | 【正式】`INV/ledger_KDE.jsonl:1`：reward 1.0、229/229，由 agent/54321 `git_apply`，projection 只含 `numpy/ma/core.py`；日志 L4 的隐藏测试树为 `088fe58b…`（= current），L73 目标键 PASSED，L258 为 229 passed。【私核】`pcheck_KDE.json`：n500 得 1000 个 token。【静态】长度 500 时 `np.split(data, (750, -750))` 的首段与尾段都是整个数组 |
| 第 4 步：K-DC、K-DF 得 1 并违例 | 同意。K-DC 在 n=500 时静默丢值，这一违例不依赖 §5 的读法之争 | 【正式】`INV/ledger_KDC.jsonl:1`、`ledger_KDF.jsonl:1` 都是 1.0。【私核】`pcheck_KDC`：n500 只有 100 个；`pcheck_KDF`：n1e5 为 False，只有 100 个 |
| K-A5 得 0 是补丁自身错误 | 同意 | `INV/logs_KA5/…eval.log` L30–80：模块内的 `max` 是 `numpy.ma.max`，把 1002 当成了 axis；L311 为 ValueError |
| K-A5b 可作正对照 | 同意，但只作**补充正对照**：它由主审编写、协调者改了一行，不是独立求解；"自定义 threshold 下也正确"是静态推断，没有实跑。主正对照仍是 gold | 【正式】`INV/ledger_KA5b.jsonl:1` 为 1.0；【私核】`pcheck_KA5b` 与 gold 相同；diff 与 K-A5 只差 `max` 那一行（`OUT/cands/`） |
| 新镜像上环境合格，devcheck 13 项全真 | 同意 | `LIFE/env_verify/ledger_l0_noop.jsonl:6`（0.0，只错目标键）与 `ledger_l0_gold.jsonl:6`（1.0，229/229）；`DEV/orig/attempt.json` 的 checks 全为 true；env.out 显示 uid 54321、`.venv`、无 pip；prelaunch 显示 `DNS_EXTERNAL=DENIED`；公开 `test_core.py` 229 passed，用时 1.73 s |
| P4 | 同意登记。溯源补充：Actual 块逐项对应 noop 日志 L50 中 pytest 自己截断的 `actual =` 显示（我第一步的发现）；公开读者也独立判定"不可能由 base 产生"（`OUT/public_read.md` L75–79）。优先级见 §6 | `DEV/orig/captures/repro_issue_repr.out` 与 noop 日志 L78 给出真实输出 |
| G1→T3：threshold 大于 1500、多维 | 同意。多维缺口现已有执行证据 | `DEV/private_control.json` 在 gold 下的 diag_sizes：(150,5) 为 False/500（750 个值只显示 500 个），(101,10) 为 False/1000（1010 个只显示 1000 个），都没有省略号 |
| 子类打印 T3 | 同意；公开命令 `pytest_print_related` 已覆盖子类测试，解题者可以自测（devcheck 中 6 passed） | `DEV/orig/captures/pytest_print_related.out` |
| X1 | 事实同意；对用途影响的表述需修改（§7） | 我第一步逐题 grep 的结果与主审一致 |
| 历史对照 | 同意：R16 / R18 只核了环境层；P4 被旧判据漏掉（旧判据只数 `--`） | `HIST/tasks/numpy__d805…/findings.md` L8；`HIST/known_issues.json` L241–262 建议的"Actual 文本应出现在 noop 失败原因里"没有应用到本题 |
| 训练候选"三步完成后可改为 yes" | **修改**，见 §8 | v1 §2 |

证据使用没有混用：奖励只取正式评分，行为事实取私核（私核以 root 运行，但只涉及输出内容，与身份无关），actor 条件取 devcheck；旧镜像 `fd832b05…` 的运行作为同材料的对照，M3 只作参考。唯一的小缺口是 env_verify 两次运行的日志只在远端，本地无法核隐藏测试树的哈希；不过同一镜像上的 5 次候选运行都显示 `088fe58b…`，可以接受。

## 3. R-c 如何合并（协调者第 1 问）

### 3.1 结论

原样采用主审 diff（`OUT/card.md` 附录 A）。我在 scratch 里对隐藏测试副本独立复核：
- diff 的 sha256 为 `1092cedb…`；
- `git apply` 干净，结果文件的 sha256 为 `ea62cd09…`；
- AST 能解析；按 AST 数 test 函数，前后都是 231 个，没有新增测试函数，所以期望映射不变；
- 第 1 处的断言在修订后文件第 468 行，第 2 处的 `'...'` 检查在第 476 行、token 断言在第 477 行，与 card 一致。

### 3.2 候选 × 断言（修订后材料）

"✓ / ✗"表示通过或失败；"—"表示前一条已经失败，不再执行。

| 候选 | 原材料得分 | 示例 repr（L454–461） | 第 1 处 n=100000（L468） | 第 2 处 `...`（L476） | 第 2 处 token（L477） | 修订后预期 | 证据 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gold | 1【正式】 | ✓ | ✓ | ✓ | ✓（500 个） | **1** | `pcheck_gold` |
| K-A5b | 1【正式】 | ✓ | ✓ | ✓ | ✓ | **1** | `pcheck_KA5b` |
| noop | 0【正式】 | ✗ | — | — | — | **0**（L456–461） | env_verify L6 |
| K-DE | 1【正式】 | ✓ | ✓ | ✓ | ✗（1000 个） | **0**（L477） | `pcheck_KDE` |
| K-DC | 1【正式】 | ✓ | ✓ | ✓ | ✗（100 个） | **0**（L477） | `pcheck_KDC` |
| K-DF | 1【正式】 | ✓ | ✗（100 个值） | — | — | **0**（L468） | `pcheck_KDF` |
| DG-e | 预计 1【静态】 | ✓ | ✗（`__str__` 未改，仍是 100 个值） | — | — | **0**（L468） | 静态 |
| DG-b | 预计 1【静态】 | ✓ | ✓ | ✓ | ✗（1000 个，同 K-DE） | **0**（L477） | 静态 |
| DG-g（可选） | 预计 1【静态】 | ✓ | ✓ | **✗（出现 `...`）** | — | **0**（L476） | 静态 |

主审的两处断言已经能同时拦住 K-DE、K-DC、K-DF、DG-e、DG-b，并且不误拒 gold 与 K-A5b。按静态推导，K-A4（去掉截角）和 ALT-1（`_print_width` 改为 ≥1002）也都能通过。

### 3.3 撤回我第一步的哪些断言，为什么

- **n=10000（头部遮蔽）**：K-DF 只在 `self.size > 10000` 时截角，10000 恰好不触发，于是整体转换后由 numpy 正常摘要，K-DF 能通过。主审的 n=100000 严格更好。这是我第一步建议的一个实际缺陷。
- **n=1200**：它覆盖了 gold 的"不截角、直接摘要"分支和 K-A5b 的"截到 1002"分支，但已知错误候选里没有一个非它不可才能拦住（K-DE 在 n=1200 时的重复被摘要掩盖；K-DC、K-DF 在 n=1200 时输出正确）。按 v1 §5"每处修改只针对一个窄问题"，不加。
- **示例的 `str(a)`**：两处新断言都用 `str`，DG-e 已经在 L468 失败，这一行是冗余的。
- **n=200 宽松版**（"要么全量，要么有省略号"）：能拦住 K-DE、K-DC、DG-b、DG-e，但会放过 DG-g 和 K-DG 式实现。改用主审的严格版（§5）。

## 4. DG-e、DG-b 是否进验收集（协调者第 2 问）

| 候选 | 是否进入 | 理由 |
| --- | --- | --- |
| DG-e（只修 `__repr__`） | **进入**：原材料上跑 1 次（预计 1，作为记录），修订材料上跑 1 次（预计 0，失败在 L468） | 它是唯一一个把 `repr` 和 `str` 拆开的候选，其余候选都改的是 `__str__`。它直接检验"新断言用 `str`"是否确实生效。它违反的公开要求：标题"String Representation"与描述里的"printing"；公开读者也把 `str(a)` 列为推知需求（`OUT/public_read.md` L21）。它改的是 gold 所改函数的调用者，不是 gold 的修改位置，所以作为"已知相关的错误候选"用于验收，不当作第二个第 3 步退化候选（第 3 步已由 K-DE 命中） |
| DG-b（只照抄 gold 的一半） | **不需要** | 对一维输入，它的截取量是 1500//2 = 750，截取条件仍是 >100，与 K-DE 逐行为等价（n=500 时同样是 1000 个 token）。两者只在多维上不同，而现有测试和修订后的测试都不打印多维大数组。K-DE 已经在集内。diff 附后，备用 |
| DG-g（全局阈值改成 99，可选） | **建议进入**（原材料预计 1，修订后预计 0，失败在 L476） | 它"作用在无关对象上"：改的是 numpy 全局默认阈值，违反 `arrayprint.py:62-64` 的文档（默认 1000），所有 ndarray 的打印都会变。示例和第 1 处都能通过，只有第 2 处"不得出现 `...`"能拦住它。它是 §5 选择严格版的实证依据 |

三个 diff 都已在 base 副本上 `git apply --check` 通过：`core.py` 的 blob 为 `35c1ec79…`，`arrayprint.py` 的 blob 为 `282fbd1c…`。scratch 里的副本与 sha256：
- DG-e：`numpy_d805_DGe.patch`，`b89992b3…`
- DG-b：`numpy_d805_DGb.patch`，`453272f6…`
- DG-g：`numpy_d805_DGg.patch`，`1a7d3c94…`

**DG-e**（`numpy/ma/core.py`，`MaskedArray.__repr__`）：

```diff
diff --git a/numpy/ma/core.py b/numpy/ma/core.py
--- a/numpy/ma/core.py
+++ b/numpy/ma/core.py
@@ -3824,8 +3824,14 @@
         else:
             name = self._baseclass.__name__
 
+        opts = np.get_printoptions()
+        if self.ndim == 1 and self.size > opts['threshold']:
+            e = opts['edgeitems']
+            data = '[%s ..., %s]' % (str(self[:e])[1:-1], str(self[-e:])[1:-1])
+        else:
+            data = str(self)
         parameters = dict(name=name, nlen=" " * len(name),
-                          data=str(self), mask=str(self._mask),
+                          data=data, mask=str(self._mask),
                           fill=str(self.fill_value), dtype=str(self.dtype))
         if self.dtype.names:
             if n <= 1:
```

**DG-b**（备用；`numpy/ma/core.py`）：

```diff
diff --git a/numpy/ma/core.py b/numpy/ma/core.py
--- a/numpy/ma/core.py
+++ b/numpy/ma/core.py
@@ -2711,6 +2711,7 @@
     _baseclass = ndarray
     # Maximum number of elements per axis used when printing an array.
     _print_width = 100
+    _print_width_1d = 1500
 
     def __new__(cls, data=None, mask=nomask, dtype=None, copy=False,
                 subok=True, ndmin=0, fill_value=None, keep_mask=True,
@@ -3796,9 +3797,11 @@
                     mask = m
                     # For big arrays, to avoid a costly conversion to the
                     # object dtype, extract the corners before the conversion.
+                    print_width = (self._print_width if self.ndim > 1
+                                   else self._print_width_1d)
                     for axis in range(self.ndim):
                         if data.shape[axis] > self._print_width:
-                            ind = self._print_width // 2
+                            ind = print_width // 2
                             arr = np.split(data, (ind, -ind), axis=axis)
                             data = np.concatenate((arr[0], arr[2]), axis=axis)
                             arr = np.split(mask, (ind, -ind), axis=axis)
```

**DG-g**（可选；`numpy/core/arrayprint.py`）：

```diff
diff --git a/numpy/core/arrayprint.py b/numpy/core/arrayprint.py
--- a/numpy/core/arrayprint.py
+++ b/numpy/core/arrayprint.py
@@ -35,7 +35,7 @@
     return x*y
 
 _summaryEdgeItems = 3     # repr N leading and trailing items of each dimension
-_summaryThreshold = 1000  # total items > triggers array summarization
+_summaryThreshold = 99  # total items > triggers array summarization
 
 _float_output_precision = 8
 _float_output_suppress_small = False
```

各候选的静态预期理由：
- **DG-e**：示例 `size=2000 > 1000`，走新分支。`str(self[:3])` 为 `'[0 -- --]'`，`str(self[-3:])` 为 `'[1997 1998 1999]'`，拼出的 data 等于期望串。3 元素部分仍走 `str(self)`。评分集里没有 >1000 个元素的一维 repr 断言。
- **DG-g**：示例被截成 100 个值，100 > 99，于是摘要；mask 行同样摘要；评分集里没有 `array2string` / `get_printoptions` 的调用，也没有打印 100–1000 个元素并做断言的地方（grep 核过）。
- **补丁交付**：DG-g 的 projection 应只含 `numpy/core/arrayprint.py`；实跑时核对它确实被导出并被加载。

## 5. 第 2 处的严格度（主审请复核者对 K-DG 读法给反证）

**我的判断：严格读法（默认阈值下 n≤1000 全量显示）有充分的公开依据，K-DG（只要截过就一律摘要）依据弱。这不是 P5，第 2 处照做。**

严格读法的依据：
1. numpy 文档定义了 `threshold`：元素总数超过它才摘要，默认 1000（`PUB/worktree/numpy/core/arrayprint.py:62-64`）。
2. base 在所有不经过截角的路径上已经遵守这条规则：
   - 无掩码时直接打印 `self._data`（`core.py:3777-3778`）；
   - 每条轴不超过 100 的带掩码数组全量打印。

   按 K-DG，`np.ma.arange(500)` 会全量显示 500 个值，同一数组只要掩掉一个元素就变成 6 个值。加一个掩码就改变截断方式，没有合理依据。
3. 截角被明确写成优化：`core.py:3797-3798` 的注释，以及 1.11 发布说明"avoid a memory peak and useless computations when printing a masked array"（`doc/release/1.11.0-notes.rst:253-257`）。优化不应改变显示结果。
4. 同一个 repr 里的 mask 行由普通 ndarray 打印；n=500 时 mask 行显示全部 500 个。按 K-DG，data 行只有 6 个，两行对不上。
5. 公开读者没看答案，但也写了"按 R3、R4 应显示全部 n 个"（`OUT/public_read.md` L28、L89）。它把这一点标为"多解"，是因为题面没提这个区间，而不是因为存在相反的依据。可见这一要求并非主审看过 gold 之后才觉得"显然"。

K-DG 的依据只有私有类属性 `_print_width = 100`（公开读者也指出它是私有的）和"a certain number of elements"这一模糊说法。另外，DG-g 说明严格版里"不得出现 `...`"这半句是承重的：宽松版会放过"把全局阈值调低"这类作用在无关对象上的补丁。

残余风险：题面唯一提到"1000"的，是失实的 Actual 描述"displaying up to 1000 elements before cutting off … very long and unwieldy"，它可能把解题者引向 K-DG。这一点不改变结论，但提高了 P4 的处理优先级（§6）。如果 Codex 仍坚持宽松读法，可以退回宽松版：它仍能拦下 K-DE、K-DC、DG-b、DG-e，只放过 DG-g 与 K-DG；这时应把 DG-g 在原材料上得 1 的结果写成已知缺口。

## 6. P4 与 T3 的处理是否一致（协调者第 3 问）

**T3 与第 2 处的关系：一致。**
- 第 2 处断言的是**默认打印选项下的一维数组**。
- "threshold 调到 1500 以上时仍丢值"，是同一原则在非默认全局配置下的延伸，属于罕见路径，按 v1 §4 第 4 步记 T3。
- 二维窄轴超出标题"1D"的范围。
- gold 在这两种情况下都不对，而上游在之后的版本里也保留了这个设计（主审引了 d89bc4bb 公开初态 `core.py:3839-3852`）。若要补断言，就需要 D4 替代正对照，而且会扩大题意。

建议在题卡里写明一句：第 2 处借用 numpy 阈值文档作依据，不代表本题要求遵守**自定义**阈值。这样可以预先回应"既然依据是阈值，为何不测自定义阈值"的质疑。多维缺口现在已有执行证据（§2），证据层级可从"静态 + 仿真"升为"当前 CPU（私有对照）"。

**P4：登记处理一致，但优先级应上调。**
- R-c 之前，那句失实的 Actual 描述只会让人困惑，照 Expected 修就能得 1。
- R-c 之后，第 2 处开始评分 100<n≤1000 这一区间；而题面中唯一的"1000"恰恰把"显示约 1000 个值"描述成缺陷本身，可能诱导出 K-DG 式补丁并被判 0。
- 这还不构成 P2：题面没有直接要求"500 个也要截"。所以它仍在 P4 的范围内，但已经与一条评分要求相关。

建议：
- R-f 机制可用后尽快做，最好与 R-c 版本相邻发布。改法按 v1 §5 的 R-f 模板：把 `PUB/user_prompt.txt:27-34` 的 Actual 块换成在 base 上实跑证实的输出（`DEV/orig/captures/repro_issue_repr.out`，与 noop 日志 L78 相同），并删去"displaying up to 1000 elements before cutting off"。不写入任何隐藏测试细节，也不提 `_print_width`。
- R-f 落地之前，在探针与训练分析里，把"n≤1000 也被摘要"式的失败单独标注为"P4 相关"，不当作干净的能力失败证据。原始 reward 不变。
- 这一条不阻塞 R-c，也不单独阻塞训练候选。

## 7. X1 对用途的影响（协调者第 4 问）

事实（主审与我分别核过）：
- 同仓 5 题（`18b7cd9d`、`2f4a9650`、`43e333e2`、`5e8301c2`、`d89bc4bb`）的公开初态里，已含本题 gold（`_print_width_1d = 1500` 与宽度选择）和本题新增的示例断言。
- 本题初态含 `a5ea773e` 的修复（`shape_base.py:860`）及其测试。

影响：
1. **训练候选：不构成阻塞。** 另外 5 题并不奖励这个修复，这段代码只是它们的环境，所以不存在"重复采样同一 reward"的问题；主审"控制重复采样"的措辞建议改掉。真正的影响是**答案暴露**：同批训练那 5 题时，策略可能在它们的环境里读到本题答案（例如 `43e333e2` 做的是 `np.ma.average`，解题时有可能打开 `numpy/ma`）。因此本题的训练通过率应视为"可能开卷"，不能当作泛化到未见代码的证据。
2. **留出评测：有方向性约束。**
   - 本题要留出，那 5 道后续题就都不能进训练，因为它们的初态含本题答案；
   - 反过来，本题进训练时，`a5ea773e` 就不能留出。
   - 按 D3 整仓划分，两条都会自动满足；任何按题或按时间的划分都必须逐条核对。
   - R-c 之后，本题只能作"标明版本的自建评测"。
3. **能力比较：不阻塞。** 比较训练过 numpy 题的模型时，要把本题标为"已暴露"。

## 8. 复核后的用途与处置

| 用途 | 当前版本 | R-c 验收并经 Codex 复核后 | 理由 |
| --- | --- | --- | --- |
| `problem_localization` | yes | yes | — |
| `capability_comparison` | conditional | conditional（只剩池级条件） | 同意主审。补充两点：(1) `private_check_6_3.py` 这两条事后审计同样能标出 DG-e（两条都用 `str`）和 DG-g（n500 不许出现 `...`）；另应标出改动了 `numpy/core/arrayprint.py`、`numpy/ma/testutils.py` 或 `numpy/testing/**` 的补丁。(2) 池级条件：模型实际收到的消息与 adapter 链路未验 |
| `training_candidate` | no（S1 未修） | **conditional（只剩池级条件）**；card 写的"可以改为 yes"需要限定 | v1 §2 要求训练候选先满足能力比较的条件；在池级条件核清之前不写 yes。若本批把池级条件放在逐题记录之外统一处理，再改为 yes |
| `heldout_candidate` | no | conditional | 标明版本；按 §7 的方向约束整组划分；登记暴露 |
| `disposition` | `needs_repair` | 按验收结果再定 | 同意 |

我第一步把训练候选与留出写成 conditional，现改为与主审一致的"当前版本 no"：S1 已由正式评分确认，而不只是证据不足。

## 9. 反查补充（主审没有列出的范围）

1. **只修 `repr` 的补丁（DG-e）**：主审没有构造这一类，但它的 R-c 两处都用 `str`，已经能拦住，建议放进验收集实证（§4）。
2. **改全局打印阈值的补丁（DG-g）**：只有严格版第 2 处能拦住（§4、§5）。
3. **`numpy/ma/core.py` 里内置函数名被遮蔽**：`max`、`min`、`sum`、`abs`、`round` 等在这个模块内都指向 `numpy.ma` 的同名函数。K-A5 就是这样崩溃的，真实模型也可能踩到。测试拒绝崩溃的实现是正确行为；探针分析时应把这类失败归为候选错误，不归为环境问题。
4. **非示例长度的 `repr`**：R-c 没有补，这可以接受。repr 的 data 段就是 `str(self)`；只有改动 `__repr__` 的补丁能让两者脱钩，而这类补丁已被示例的 repr 断言与两处 `str` 断言夹住。
5. **性能**：
   - K-A4（去掉截角）能通过 R-c；n=100000 规模很小，没有超时风险。
   - 10^7 以上元素的性能退化没有测试，按 T3 登记（公开读者的 R12）。
   - 公开命令 `diag_perf_large` 能让解题者自己看到开销：gold 为 0.001 s（`DEV/private_control.json`），base 为 0.002 s。
6. **测试顺序**：这是 unittest 风格的类，pytest 按方法名顺序执行。评分集里没有测试修改全局打印选项（`masked_print_option` 的改动在 `finally` 里还原），所以新断言不依赖顺序。
7. **未核实**：主审说"材料 v3–v5 对本题逐字相同"，但 v4、v5 不在我的阅读范围内。

## 10. 验收清单与下一步

1. **实施 R-c**：
   - 用主审 diff 原样实施（sha256 `1092cedb…`；结果文件 `ea62cd09…`）；`expected_output.json` 不变。
   - 按 R2E 材料修订流程登记新的隐藏测试树哈希；如框架要求，重建派生镜像。
2. **修订材料上的正式评分**：
   - 预期结果：gold=1，K-A5b=1，noop=0，K-DE=0（L477），K-DC=0（L477），K-DF=0（L468），**DG-e=0（L468）**；可选 DG-g=0（L476）、DG-b=0（L477）。
   - 每个得 0 的候选，都要核对它失败在预期的那一行，确认确实是目标断言在起拒绝作用。
   - 每个候选都要核对：解析出 229 个键；由 agent 应用；projection 符合（DG-g 为 `numpy/core/arrayprint.py`）。
3. **原材料（可选，只作记录）**：DG-e（预计 1）、DG-g（预计 1）。
4. **Codex 复核**：保存父版本、新版本、理由与触发反例（K-DE、K-DC、K-DF，以及 DG-e）。
5. **题卡修改**：
   - 训练候选在 R-c 后改为 conditional（池级）；
   - 按 §7 改写 X1 的措辞；
   - 加入 §6 那句 T3 边界说明；
   - 验收集加入 DG-e；
   - P4 的 R-f 优先级上调。
6. **P4 的 R-f**：机制实现后做（§6），不阻塞 R-c。

## 附录：对第一步初判的更正

| 第一步的说法 | 现在 | 依据 |
| --- | --- | --- |
| R-c(1)：`str(示例)` 加上 n=1200、n=10000 | 撤回，改用主审两处 | n=10000 拦不住 K-DF；其余是冗余（§3.3） |
| R-c(2)：n=200 宽松版 | 撤回，改用严格版 | DG-g 与 K-DG 只有严格版能拦（§5） |
| DG-b 作为备选退化候选 | 不需要 | 一维上与 K-DE 等价，K-DE 已正式评分 1.0 |
| actor 待验 | 已解除 | `DEV/orig/attempt.json` 13 项全真 |
| 训练 / 留出为 conditional | 当前版本改为 no | S1 已由正式评分确认 |
| P4 可选、低优先 | 仍可选、不阻塞，但优先级上调 | 与第 2 处评分要求有关（§6） |
