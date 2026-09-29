# numpy d805e9b6 私有主审：读历史前的初判

- **题目**：`numpy__d805e9b66228e68a0eb14d901cd350159c49af18`。base 为 `25e3ebf4`，修复提交为 `d805e9b6`；来源 runner 事实 `head_is_parent_of_fix=yes`。
- **角色与时间**：R2E 私有主审（单题闭环试行，按统一标准 v1），2026-09-29。本文件在读任何历史调查之前封存。
- **路径约定**（下文都用这些简写）：
  - `PUB/` = `runs/r2e_static_prep_20260924/v3/public/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/`
  - `PRIV/` = `runs/r2e_static_prep_20260924/v3/private/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/`
  - `OUT/` = 本题结果目录
  - 日志与账本路径都相对仓库根。
- **证据级别**：
  - 【日志】：当前材料下已有的 RH2 评分原件。运行时间为 09-23/24，在 R-f 机上，派生镜像为 `sha256:fd832b05…`。
  - 【静态】：读代码推导得出。
  - 【仿真】：本审在 scratch 里写的一维逻辑仿真，不导入项目代码，只核对显示的 token 内容，不含折行。
  - 【待跑】：需要协调者实跑。
  - 本题目前没有当前 CPU 证据，也没有真实模型证据。
- **材料修订**：没有。`PRIV/revisions.json` 为 `[]`。

## 0. 结论速览（暂定）

- **核心要求**：大的一维掩码数组，str / repr 的 data 段要像 numpy 普通数组一样摘要显示，被省略的值用省略号标出（`PUB/user_prompt.txt:5, 8, 19-25`）。
- **目标键**：只有 `TestMaskedArray.test_str_repr` 一个。新增的断言就是题面示例原样：n=2000，掩码 `a[1:50]`（`PRIV/hidden_tests/test_1.py:454-461`）。隐藏文件与公开的 `numpy/ma/tests/test_core.py` 相比只多这 9 行，其余 228 个键都是公开旧测试。期望映射 229 键全部为 PASSED。
- **v1 §4 判定**：
  - 第 1 步：有直接断言。
  - **第 2 步命中 S1（T2c，示例拟合）**：核心断言只用了题面示例的字面值。这一点是确定的，不依赖实跑。
  - 第 3 步：退化候选 K-DE 只把截取量改成 750，预计得 1，即 T2b【待跑】。
  - 第 4 步：本审构造的部分修复 K-DC、K-DF 预计也得 1，并且在同一核心要求的其它实例上违反公开要求【待跑】。
  - gold 在默认打印选项下，对一维数组是正确的。自定义 `threshold` 与多维数组仍有缺口，前者是边缘输入、后者在题外，登记为 S2 / T3。
- **修订建议（R-c）**：在 `test_str_repr` 末尾追加两处非示例断言，期望映射不变。
  - n=100000、末尾两个值被掩：应得到摘要结果。
  - n=500：应全量显示，没有省略号，值不缺也不重复。
  - 验收矩阵见 §7。
- **题面**：Actual Behavior 段与 base 的实际输出不符，按 P4 登记，可选做 R-f。题面没有泄漏答案，不是 P1。
- **题目关系（X1）**：
  - 本题 gold 与隐藏断言逐字出现在同仓另外 5 题的公开工作树里。
  - 本题工作树里含 numpy a5ea773e 的修复（以重构后的形式）以及它的测试。
- **暂定处置**：`needs_review`。用途四项：
  - problem_localization = yes
  - capability_comparison = conditional
  - training_candidate = no（R-c 验收前）
  - heldout_candidate = no
- **唯一优先的下一步**：在当前材料上正式评分 K-DE，同批评分 K-DC、K-DF、K-A5，同时跑 §6.3 的两条私有行为核对。

## 1. 公开读者没有捕获的真实条件

- **模型实际收到的消息**：没有捕获。`PUB/user_prompt.txt` 只是静态渲染；系统提示、工具描述，以及 `/rh2/public_task_bundle.json` 里的 hints 如何呈现，都不知道。清单第 3 项记为 unknown。
- **容器初态**：以下内容不在公开包里。
  - `.venv`（3.7.9）、就地构建出的 `.so` / `version.py` / `__config__.py`、`install.sh`、git 状态。
  - 来源镜像里修复提交可以到达：`fix_reachable=commit`，`commits_after_head=29588`（`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl` 第 39 行）。按环境卡，派生镜像已经清掉修复提交，actor 预检会检查 HEAD 没有子提交。
- **评分侧观测**（4 份账本第 21 行的 `observations`，以及 eval.log 头部）：
  - 导入路径 `/testbed/numpy/__init__.py`，版本 `1.12.0.dev0+25e3ebf`；
  - pytest 7.4.4，hypothesis 6.79.4；
  - 峰值内存约 282–299 MB，测试阶段 1–2 s。
- **解题身份与资源**（uid 54321、2 CPU / 4 GiB、`/tmp` 1 GiB、断网）：只有 `PUB/environment_brief.md:10-13` 和环境卡 §2 的说法。以下几项都要等 devcheck 结果：
  - 新机器上重建的派生镜像的身份；
  - actor 侧能否写 `/testbed`；
  - 公开命令的实际输出。
- **警告参数的差别**：评分用 `-W ignore` 与 `PYTHONWARNINGS`（`PRIV/run_tests.sh`），公开命令没有加。这只影响警告是否显示，不影响本题判定【静态】。

## 2. 隐藏测试展开

### 2.1 目标键 `TestMaskedArray.test_str_repr`（`PRIV/hidden_tests/test_1.py:447-461`）

**前半段（448-452 行）**：小数组 `array([0,1,2], mask=[F,T,F])` 的 str 与 repr。这段与公开 `test_core.py:447-452` 相同，是同一个键里的回归检查。

**后半段（454-461 行，新增）的调用路径**：

1. `np.ma.arange(2000)` 建出数组（`core.py:7770`）。
2. `a[1:50] = np.ma.masked` 经过 `__setitem__`（`core.py:3189-3225`），建出长 2000 的完整掩码。
3. `repr(a)` 调用 `__repr__`（`core.py:3816-3836`），用 `short_std` 模板（`core.py:2396-2400`）拼接，data 段就是 `str(self)`。
4. `__str__` 走非结构化分支（`core.py:3794-3807`）：
   - 按 `_print_width=100` 在每条轴上截取首尾各 50 个元素；
   - 把截出的部分转成 object；
   - 在掩码位置填入 `masked_print_option`，它的 repr 是 `--`（`core.py:2364-2367`）。
5. `str(res)` 进入 `arrayprint._array2string`。只有元素数大于 `_summaryThreshold=1000` 时才会摘要（`PUB/worktree/numpy/core/arrayprint.py:37-38, 252-257`）。

**断言**：用 `numpy.ma.testutils.assert_equal`（`PUB/worktree/numpy/ma/testutils.py:109-133`）对整串做 `==` 比较，包括结尾的换行。这个键没有 fixture，`setUp` 里的数据与它无关。

**这个键到底测什么**：只测一件事——题面示例这一个输入，在默认打印选项下，repr 与 Expected 逐字相同。

- 依据是 Expected 块（`PUB/user_prompt.txt:21-25`）。
- 结尾换行来自模板，公开旧断言也检查它（`test_core.py:450-452`）。
- mask 行与 fill_value 行由 numpy 自身生成，任何合理修复都不会改动它们。

**初态失败位置**【日志】：

- noop 两次都只失败这一个键，失败位置是 `r2e_tests/test_1.py:458`。
  - ACTUAL 的 data 段共 6 行：0、49 个 `--`、1950…1999，没有省略号。这与公开读者的静态推导一致（`runs/r2e_env_repair_20260924/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_0338a8c6.eval.log:47, 78-79, 313`）。
  - 09-23 那一次（`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-n_e62017bf.eval.log`）除耗时外与上面逐行相同。
- gold 两次都是 229 passed（`…rer_62e681a9.eval.log:258`、`…rf-all-gold-n_cffc79f5.eval.log:258`）。
- M3 独立 runner 在来源镜像上跑 gold，也是 229 passed（`runs/env_overnight_20260916/M3/gold_ledger/logs_r2e/numpy/d805e9b66228/gold/a1/test_output.txt`，a2 相同）。

### 2.2 回归键（228 个）

- **与打印相关的回归键，逐条读过**：
  - `test_basic0d`（80-88）
  - `test_maskedelement`（249-255）
  - `test_indexing` 与 `test_matrix_indexing`（277-278、327-328，只检查 str / repr 不抛异常）
  - `test_oddfeatures_1`（547）
  - `test_fancy_printoptions`（651-669，结构化 dtype）
  - `test_mvoid_print`（756-767，改显示字符后在 finally 里恢复）
  - `test_mvoid_multidim_print`（769-803）
  - `test_assign_dtype`（1531-1537，repr 冒烟检查）
- **这些键保护了什么**：小数组、0 维、结构化 dtype、mvoid、`masked_print_option`、matrix 的打印。
- **没有被保护的**：
  - 任何一条轴长度大于 100 的数组的打印；
  - 子类打印（`test_subclassing.py` 不在隐藏测试里）；
  - `numpy/core` 的 arrayprint 测试。
- **其余键**：约 220 个运算、方法类的键只按类名和函数名浏览过。gold 的 diff 不触及它们的调用链。
- **不稳定因素**：约 8 个回归键用了没有设种子的 `np.random`（例如 161、1056-1057、2547-2548 行）。它们与同一份数据上的 numpy 结果比较，属于上游稳健写法。6 次运行里 228 个回归键的状态完全一致。

## 3. 需求—断言双向表

| 公开要求或合理旧行为 | 依据 | 测试 / 决定性断言 | 覆盖 | 证据或下一步 |
| --- | --- | --- | --- | --- |
| C0 题面示例的 repr 逐字等于 Expected | `PUB/user_prompt.txt:11-25` | `test_str_repr`，454-461 行 | 覆盖，但只有示例字面值 | 【日志】noop 失败、gold 通过 |
| C1 其它"大的一维掩码数组"（不同的 n 或掩码位置）也要摘要并标省略号 | 标题（第 5 行）；Expected 的一般表述（第 20 行） | 无 | **缺失 → T2c** | R-c 第 1 处 |
| C2 省略值必须用省略号标出，不得静默丢值或重复；元素数不超过阈值时全量显示（包括 100 < n ≤ 1000） | Expected 第 20 行；`set_printoptions` 文档中 threshold 的定义（`arrayprint.py` 约 62-64 行）；`core.py:3797-3798` 注释说截角只是为了避免昂贵的转换；1.11 发布说明把它记为内存优化（`doc/release/1.11.0-notes.rst:252-257`）；同一个 repr 里的 mask 行就是按阈值规则显示的 | 无 | **缺失** | R-c 第 2 处 |
| R2 `str(a)` / `print(a)` 同样修好 | 标题写的是 "String Representation"；描述里写的是 "printing" | 只通过 repr 的 data 段间接覆盖（`core.py:3828`） | 部分 | R-c 两处都断言 `str` |
| R4 摘要格式与 numpy 默认一致（edgeitems=3，`..., `） | Expected 的格式 | 只在示例上断言 | 部分 | R-c 第 1 处补一个实例 |
| R5–R6 模板对齐、结尾换行、mask 行与 fill_value 行不变 | 公开旧断言 `test_core.py:450-452`；Expected | 同一个键 | 覆盖 | 【日志】 |
| R7 小数组、0 维、结构化、mvoid、自定义显示字符、nomask 分支不变 | 公开旧测试 | §2.2 列出的各键 | 覆盖（只到小数组） | 【日志】 |
| R8 子类的 `__str__` 委派，以及填 `--` 时不经过子类的 `__setitem__` | 公开 `test_subclassing.py:318-341` | 隐藏测试里没有 | 缺失（回归，不是核心；解题者可以用公开测试自测） | 登记为 T3 |
| 多维、自定义 printoptions、性能 | 标题限定一维；题面没提 printoptions；性能在描述里只提了一句 | 无 | 不适用或不测 | 见 §5 |

**反查**：唯一新增的决定性断言，其期望串由题面 Expected 原样给出；结尾换行有公开旧断言作依据。断言里没有只能从隐藏材料得知的细节，不构成 P3 或 T1。

**和公开读者的一处分歧**：公开读者把 R9（100 < n ≤ 1000）记为"多解"。本审认为"按阈值全量显示"一种读法有依据：numpy 文档对 threshold 的定义、截角代码的注释与发布说明（截角只是优化，不应改变显示结果），以及同一 repr 中 mask 行的表现。另一种读法 K-DG 是"凡是被截过就一律摘要"，它唯一的依据是私有常数 100，本审认为依据弱。复核时请针对这一点给反证（见 §7.4）。

**合理替代解与蒙混解**：见 §6.2。
- 合理替代解：K-A5（按当前 threshold 决定截取宽度），另有可选的 K-A4（去掉截角）。
- 蒙混解：K-DE、K-DC、K-DF 都只在示例、或在 n > 1000 的一部分输入上正确。

## 4. R2E 专项

- **(a) 非 PASSED 的键**：没有，期望的 229 个键全部是 PASSED。更完整的修复只会影响"某条轴大于 100 的数组打印"，而现有 228 个回归键都不涉及这种打印。因此，处理多维、处理自定义 printoptions、或干脆去掉截角的修复，都不会把任何键翻转成失败【静态】。
- **(b) 题面描述的报错是否出现在 noop 目标键的失败原因里**：失败原因确实是"没有省略号、data 段过长"，但与题面 Actual 块的内容对不上。
  - Actual 块（`user_prompt.txt:28-34`）写的是 31 个 `--` 加上 `..., 1997 1998 1999`，并说 "displaying up to 1000 elements"。
  - base 实际输出的是 100 个值：49 个 `--` 和 1950…1999，没有省略号（上面引用的 noop 日志第 78 行）。
  - 结论：按 P4 登记，公开材料可以消解。照 Expected 修就能通过，不构成 P2。
- **(c) 题面是否泄漏修法**：没有。题面没有提到 `_print_width`、1500 或截角逻辑。标题里的 "1D" 描述的是症状范围；数字 "1000" 出现在错误的 Actual 描述里，可能误导，但不是答案。不是 P1。
- **(d) 测试辅助、搬迁伪影与撞键**：
  - 隐藏测试导入 `numpy.ma.testutils` 与 `numpy.testing`。这两个是包内模块，候选可以修改，评分时不会被重置。这是 R2E 的通用通道（清单第 31 项、E3）：本题只登记，建议在事后审计中标记改动了 `numpy/ma/testutils.py` 或 `numpy/testing/**` 的补丁，不加排除规则。
  - 没有 conftest，没有相对路径资源，也没有相对导入。
  - 隐藏测试是单文件，collected 229 = 期望 229，不存在撞键。
- **(e) 时间、随机、资源敏感**：目标键是确定性的。随机性见 §2.2，风险低。资源占用很小。
- **(f) 修订核对**：没有修订，不适用。

## 5. gold 检查（按公开要求）

- **原例修到了吗**：修到了【日志】。
  - 一维时截取宽度改为 1500。n ≤ 1500 时不截取，完全按 numpy 规则显示；n > 1500 时保留首尾各 750 个，1500 > 1000，于是 `array2string` 会自行摘要【静态】【仿真】。
  - 示例、n=100000、n=1001、n=1200 都输出正确的摘要；n=500 全量显示；n=3 不变。
- **改动范围**：只改了 `numpy/ma/core.py` 的一个类属性和截取宽度的选择，外加注释，没有无关改动。projection 的 included_paths 只有 `["numpy/ma/core.py"]`【日志，gold 账本第 21 行】。
- **未测的回归**：没有发现。
  - 一维 101–1500 个元素的数组，现在会整体转成 object，最多 1500 个，开销可以忽略。
  - 多维、结构化、nomask 分支，以及显示被禁用的分支，行为都与 base 相同。
- **G1 缺口**（按 v1 第 4 步归为边缘路径，S2 / T3，只登记，不作修订目标）：
  - 用户把 `threshold` 调到大于 1500（例如 `sys.maxsize`，一种常见的"打印全部"写法）时，n=2000 只显示 1500 个值，也没有省略号，仍在静默丢值【仿真】。base 同样有这个问题，而且更严重。上游后来的版本也保留了这个设计：同仓 d89bc4bb 公开工作树的 `core.py:3839-3852`。
  - 多维没有改动。例如 (150, 5) 仍然只显示 100 行、没有省略号。标题限定一维，这属于题外。
- **判定理由**：题面的核心要求在默认选项下被完整满足；上面两项缺口都不在题面核心要求之内。

## 6. v1 §4 严重度与候选

### 6.1 五步判定

1. **有无直接断言**：有（454-461 行），不命中 T2a。
2. **是否只用示例字面值**：是。n=2000、`a[1:50]`、`np.ma.arange` 与题面完全相同，决定性断言只有这一个。**S1（T2c）**，走 R-c 补非示例实例。
3. **退化探测**：K-DE 预计得 1【待跑】。若得 1，则为 **S1（T2b）**。
4. **已有候选在其它实例上的违例**：已有的真实候选只有 gold（没有模型候选），gold 的缺口见 §5，属边缘或题外。审查中构造的 K-DC、K-DF 预计得 1，并且分别在 n=500 与 n=100000 上违例【待跑】，命中则为 S1。
5. 第 2 步已经命中，所以不是 S2。

### 6.2 候选（都可以直接做成补丁）

四个 diff 都对 base `core.py` 做过 `git apply --check`，能干净应用；scratch 里存有副本。每个候选的"违反的公开要求 / 暴露违例的输入"都写在它自己的条目里。

**K-DE：退化候选（v1 第 3 步，每题只给这一个）**

- 构造方向：只改 gold 修改位置上的截取量，把 gold 的 1500//2 直接写成常数，不改截取条件。属于"与输入长度无关的固定截取量"。
- 预期：当前材料上得 1。n=2000 时保留 [0:750] 与 [1250:2000]，共 1500 个，摘要结果与 Expected 相同；其它 228 个键不打印任何一条轴大于 100 的数组。
- 违反的公开要求：str 应显示数组本身的元素，C2 也不允许重复显示。
- 暴露违例的输入：`a = np.ma.arange(500); a[1:50] = np.ma.masked; str(a)`。此时 `np.split(data, (750, -750))` 的首段与尾段都是整个数组，拼接后是 1000 个元素，因为 1000 不大于阈值，每个值都会被全量显示两次【静态】【仿真】。
```diff
--- a/numpy/ma/core.py
+++ b/numpy/ma/core.py
@@ -3798,7 +3798,7 @@ def __str__(self):
                     # object dtype, extract the corners before the conversion.
                     for axis in range(self.ndim):
                         if data.shape[axis] > self._print_width:
-                            ind = self._print_width // 2
+                            ind = 750
                             arr = np.split(data, (ind, -ind), axis=axis)
                             data = np.concatenate((arr[0], arr[2]), axis=axis)
                             arr = np.split(mask, (ind, -ind), axis=axis)
```

**K-DC：部分修复（只处理元素数大于 threshold 的一维数组）**

- 预期：当前材料上得 1。
- 违反的公开要求：C2，也就是题面 "using an ellipsis to indicate omitted values" 这一句。
- 暴露违例的输入：n=500 时仍是 base 的行为，只显示 100 个值、没有省略号，静默丢掉 400 个。
```diff
--- a/numpy/ma/core.py
+++ b/numpy/ma/core.py
@@ -2711,6 +2711,7 @@ class MaskedArray(ndarray):
     _baseclass = ndarray
     # Maximum number of elements per axis used when printing an array.
     _print_width = 100
+    _print_width_1d = 1500
 
     def __new__(cls, data=None, mask=nomask, dtype=None, copy=False,
                 subok=True, ndmin=0, fill_value=None, keep_mask=True,
@@ -3796,9 +3797,13 @@ def __str__(self):
                     mask = m
                     # For big arrays, to avoid a costly conversion to the
                     # object dtype, extract the corners before the conversion.
+                    print_width = self._print_width
+                    if (self.ndim == 1 and
+                            self.size > np.get_printoptions()['threshold']):
+                        print_width = self._print_width_1d
                     for axis in range(self.ndim):
-                        if data.shape[axis] > self._print_width:
-                            ind = self._print_width // 2
+                        if data.shape[axis] > print_width:
+                            ind = print_width // 2
                             arr = np.split(data, (ind, -ind), axis=axis)
                             data = np.concatenate((arr[0], arr[2]), axis=axis)
                             arr = np.split(mask, (ind, -ind), axis=axis)
```

**K-DF：部分修复（只提高截取门槛，不改截取量）**

- 预期：当前材料上得 1。n=2000 时不截取，整体转 object 后正常摘要。
- 违反的公开要求：C1 核心要求本身。
- 暴露违例的输入：n=100000 时仍只显示 100 个值、没有省略号。
```diff
--- a/numpy/ma/core.py
+++ b/numpy/ma/core.py
@@ -3797,7 +3797,7 @@ def __str__(self):
                     # For big arrays, to avoid a costly conversion to the
                     # object dtype, extract the corners before the conversion.
                     for axis in range(self.ndim):
-                        if data.shape[axis] > self._print_width:
+                        if self.size > 10000 and data.shape[axis] > self._print_width:
                             ind = self._print_width // 2
                             arr = np.split(data, (ind, -ind), axis=axis)
                             data = np.concatenate((arr[0], arr[2]), axis=axis)
```

**K-A5：合理替代解（一维时按当前 threshold 决定截取宽度；多维保持原样）**

- 预期：当前材料与修订后的材料上都得 1。
- 作为独立的正对照：它保留了截角优化，同时在自定义 threshold 下仍然正确，比 gold 更完整。
- 可选的另一个正对照 K-A4：删掉 3799-3805 行的截角循环，改为整体转 object。输出与 numpy 完全一致，代价是大数组变慢。
```diff
--- a/numpy/ma/core.py
+++ b/numpy/ma/core.py
@@ -3796,9 +3796,19 @@ def __str__(self):
                     mask = m
                     # For big arrays, to avoid a costly conversion to the
                     # object dtype, extract the corners before the conversion.
+                    print_width = self._print_width
+                    if self.ndim == 1:
+                        # Keep more items than the summarization threshold so
+                        # that array2string still summarizes, and do not cut
+                        # at all when the array is going to be printed in full.
+                        threshold = np.get_printoptions()['threshold']
+                        if data.size > threshold:
+                            print_width = max(print_width, int(threshold) + 2)
+                        else:
+                            print_width = data.size
                     for axis in range(self.ndim):
-                        if data.shape[axis] > self._print_width:
-                            ind = self._print_width // 2
+                        if data.shape[axis] > print_width:
+                            ind = print_width // 2
                             arr = np.split(data, (ind, -ind), axis=axis)
                             data = np.concatenate((arr[0], arr[2]), axis=axis)
                             arr = np.split(mask, (ind, -ind), axis=axis)
```

### 6.3 私有行为核对（只留在私有对照里，不进解题者的材料）

在已经应用候选的 `/testbed` 下运行，`python` 即 `.venv` 的解释器：

```
cd /testbed && python -c "import numpy as np; a=np.ma.arange(500); a[1:50]=np.ma.masked; s=str(a); t=s.replace('[',' ').replace(']',' ').split(); print('n500', len(t), '...' in s, t==['0']+['--']*49+[str(i) for i in range(50,500)])"
cd /testbed && python -c "import numpy as np; a=np.ma.arange(100000); a[-2:]=np.ma.masked; s=str(a); print('n1e5', s=='[0 1 2 ..., 99997 -- --]', len(s.split()))"
```

### 6.4 预测结果（【仿真】加【静态】；实跑后以日志为准）

| 候选 | 当前材料 | n500 核对 | n1e5 核对 | 修订后（R-c） |
| --- | --- | --- | --- | --- |
| noop / base | 0【日志】 | 100 个，False | False | 0 |
| gold | 1【日志】 | 500 个，True | True | 1 |
| K-DE（退化） | 1 → T2b | **1000 个**，False | True | 0（第 2 处） |
| K-DC | 1 | **100 个**，False | True | 0（第 2 处） |
| K-DF | 1 | 500 个，True | **False** | 0（第 1 处） |
| K-A5 | 1 | 500 个，True | True | 1 |

- **评分时需要确认的事项**：
  - projection 的 included_paths 为 `numpy/ma/core.py`；
  - 解析出 229 个键；
  - `TestMaskedArray.test_str_repr` 确实执行了（得 1 的候选在该键上为 PASSED；得 0 的候选失败在预期的那一行）。
- **读公开命令 `diag_sizes` 时的提醒**：gold 控制下，(150, 5) 与 (101, 10) 两行预计分别是 False/500 与 False/1000，而不是公开读者写的"numpy 一致值"。这是因为 gold 不处理多维，不是环境问题。

## 7. 修订建议

### 7.1 R-c：两处，都放进 `PRIV/hidden_tests/test_1.py` 的 `TestMaskedArray.test_str_repr`，接在 461 行之后

```python
        # a large 1d array other than the issue example is summarized too
        a = np.ma.arange(100000)
        a[-2:] = np.ma.masked
        assert_equal(str(a), '[0 1 2 ..., 99997 -- --]')

        # below the default summarization threshold (1000 items) a 1d array
        # is printed in full: no ellipsis, nothing dropped or repeated
        a = np.ma.arange(500)
        a[1:50] = np.ma.masked
        s = str(a)
        assert_('...' not in s)
        assert_equal(s.replace('[', ' ').replace(']', ' ').split(),
                     ['0'] + ['--'] * 49 + [str(i) for i in range(50, 500)])
```

- **第 1 处（T2c）**：
  - 公开依据：标题，以及 Expected 的一般表述；用 `str` 断言是因为描述里写了 "printing"。
  - 这一处选用与示例不同的规模、不同的掩码位置，并确实走 gold 的截取路径。
- **第 2 处（T2b / 第 4 步）**：
  - 公开依据：Expected 中"用省略号标出被省略的值"那一句；`set_printoptions` 文档对 threshold 的定义；`core.py:3797-3798` 的注释与 1.11 发布说明（截角只是优化）。
  - 这一处只比较 token 内容，不比较折行，所以不会惩罚折行方式不同的实现。
- **期望映射**：键集不变（仍是 `TestMaskedArray.test_str_repr: PASSED`），不需要改 `expected_output.json`。如果协调者更想按键区分诊断，也可以拆成两个新测试函数，但那样要同时加入对应的期望键，保证严格相等。
- **两处都是【静态】核对**：gold 的输出分别是 `'[0 1 2 ..., 99997 -- --]'` 与 500 个 token，都能通过；运行开销可以忽略。

### 7.2 验收计划（按 v1 §5）

- **修订后的材料**：
  - gold 与 K-A5 为 1（正对照；K-A4 可选）；
  - noop 为 0；
  - K-DE、K-DC、K-DF 为 0，并核对它们失败在预期的那一处；
  - 229 个键严格相等。
- **原版材料**：同一批候选的结果分开保存（§6.4 第 2 列）。
- **修订后仍受保护的公开要求**：C0、C1、C2、R5–R7。
- **归档与复核**：保存新版本、父版本、理由，以及作为触发反例的 K-DE；最后交 Codex 复核。

### 7.3 P4（可选 R-f，不阻塞训练候选）

Actual Behavior 块可以换成 noop 日志第 78 行实际给出的 base 输出，并删去 "displaying up to 1000 elements before cutting off"，改为经 base 实跑核实的症状描述，例如"只显示首尾各 50 个值，中间被丢掉，也没有省略号"。按 P4 的默认去向，可以只登记不修改；如果做，要按 R-f 的验收流程走。

### 7.4 不建议或待复核的事项

- **不建议补自定义 printoptions 和多维的断言**：题面没有写这两类需求，而且 gold 通不过。
- **K-DG 读法请复核者给反证**：K-DG 认为"只要截过就一律摘要"。在它的读法下，n=500 应显示为 `[0 -- -- ..., 497 498 499]`，那么第 2 处断言就会误拒它。本审认为这种读法依据弱（理由见 §3）。如果复核认为两种读法都有依据，第 2 处就改为待用户决定的 P5，第 1 处照做。

## 8. 开发需求（逐题）

| 项 | 本题的需要 | 证据级别 |
| --- | --- | --- |
| 导入 | 在 `/testbed` 下用 `python -c` 或 `python -m pytest`，`/testbed` 要在 `sys.path` 上；numpy 没有装进 venv | 镜像层面：brief 声明为实测；评分侧的导入路径有【日志】；actor 侧待验（新机器的 devcheck） |
| 依赖 | 不需要新依赖；pytest 7.4.4 已有；不需要 pip | 评分侧【日志】；actor 侧待验 |
| 资产 | 无 | 不适用 |
| 权限 | uid 54321 要能写 `numpy/ma/core.py` | actor 待验 |
| 网络 | 准备、解题、安装 / 构建、测试四个阶段都不需要网络 | 【静态】；评分侧在 `deny_all` 下通过 |
| 构建 | 纯 Python 改动，不需要重编；`.so` 保持不变 | 【静态】 |
| 提交边界 | 修复文件是 `numpy/ma/core.py`；R2E 按文件字节差异导出；解题者自己的草稿应放在 `/tmp` | gold projection【日志】 |
| 公开验证路径 | 题面示例本身就是复现方法（公开命令 `repro_issue_repr`）；`pytest_ma_core_full` 覆盖全部 228 个回归键，因为公开文件与隐藏文件的函数集合相同，预计 base 上 229 passed；`diag_sizes` 能让解题者自己发现 n=500 的问题 | 预期结果为【静态】；实际输出与墙钟时间等 devcheck |

公开命令是否足够：足够用来复现问题和做回归。风险在于，如果解题者只核对题面示例，就会写出 K-DE、K-DC 一类的补丁，而这正是测试没有覆盖到的地方。

## 9. 题目关系（X1）

- **本题 gold 出现在其它题的公开工作树里**：本审逐一 grep 核对了机械扫描的结论（`runs/r2e_static_prep_20260924/cross_task_gold_scan.json`）。以下 5 题的 `core.py` 都已含 `_print_width_1d = 1500` 与宽度选择，`test_core.py` 也都含 `np.ma.arange(2000)` 的 repr 断言：
  - 18b7cd9d（`core.py:2766, 3839-3840`）
  - 2f4a9650（`2753, 3856-3857`）
  - 43e333e2（`2812, 3926-3927`）
  - 5e8301c2（`2763, 3826-3827`）
  - d89bc4bb（`2770, 3844-3845`）
  
  也就是说，这 5 题的初态里就有本题的答案和测试。
- **其它题的修复出现在本题初态里**：机械扫描 `cross_task_test_scan.json` 只记了一对，是 a5ea773e 的新测试 `test_tile_one_repetition_on_array_gh4679` 出现在本题初态中。本审核实：
  - 本题 `PUB/worktree/numpy/lib/shape_base.py:860-863` 已含 a5ea773e 的修复（在 reps 全为 1 时复制，写法重构过，所以逐字扫描漏报）；
  - 测试位于 `numpy/lib/tests/test_shape_base.py:357-361`。
  
  除此之外，扫描没有发现其它题的 gold 被包含在本题里；这只是下限。
- **影响**：按仓库划分训练集与留出集时，这些 numpy 题整组放在一起。训练时要控制同一修复被重复采样。

## 10. 八方面覆盖与未查项

- **公开需求**
  - 已查：题面、hints、brief、公开读者报告，以及 base 的 arrayprint 文档、截角注释、1.11 发布说明。
  - 未查：模型实际收到的消息。
- **材料与初始问题**
  - 已查：base 是修复提交的父提交；gold 与隐藏测试对应（M3 的 `gold_meta` 排除了 `test_core.py`）；`initial_diff` 为 0 字节；noop 失败的位置与内容【日志】。
  - 未查：新机器上派生镜像的身份。
- **测试是否测到要求**
  - 已查：目标键读完；与打印相关的回归键逐条读过。
  - 其余约 220 个键只看了名称。
- **是否误拒合理解**：没有发现过严的断言；合理替代解 K-A5、K-A4 预计都能通过（【静态】，待跑）。
- **回归与 gold 完整性**：见 §5。子类打印不在评分范围内，记为 T3。
- **开发条件**：见 §8。actor 侧的全部条件都等 devcheck。
- **交付与评分边界**：
  - 单个 `.py` 文件，projection 正常；
  - 没有 conftest；
  - `run_tests.sh` 对解题者可见，但直接运行只会报找不到 `r2e_tests`，没有害处；
  - testutils 可被候选修改（通用问题，见 §4(d)）。
- **题目关系与用途**：
  - 题目关系见 §9；
  - 不是 P1；
  - 任务类型：打印格式缺陷修复，补丁很小。
  - 公开读者自报的意外接触不涉及本题私有材料，不影响本审对其产物的使用。

## 11. 暂定处置、用途与缺口

- **disposition**：`needs_review`，`scope=static_review`。reason 分两部分：
  - 题意 / 测试：S1（T2c 已定；T2b 与第 4 步待实跑），R-c 验收后再定。
  - 环境：静态候选待 actor 验证，即新机器的 devcheck。
- **v1 用途**：
  - problem_localization = yes。
  - capability_comparison = conditional，还差三个条件：新机器的 devcheck 结果（actor 的导入、写权限、公开命令）；重建镜像上的 noop / gold 正式评分；R-c 落地前，对得 1 的补丁预先登记 §6.3 的两条核对作为事后审计。
  - training_candidate = no：T2c 还没修；R-c 验收并经 Codex 复核后再评估。
  - heldout_candidate = no：修订后只能作为标明版本的自建评测，而且有 §9 的包含关系。
- **缺口**：
  - K-DE、K-DC、K-DF、K-A5 都还没有正式评分；
  - actor 侧条件与模型实际收到的消息没有核对；
  - 其余约 220 个回归键没有逐条阅读；
  - K-DG 读法的分歧交给复核。
- **唯一优先的下一步**：在当前材料上正式评分 K-DE（同批跑 K-DC、K-DF、K-A5），并跑 §6.3 的两条私有核对。它会直接决定 T2b 与第 4 步是否命中，同时验证 R-c 两处断言各自是必要的。

## 附录 A：`checks` 预映射（按 40 项清单编号，只记有结论的项）

- **pass**：
  - 1、2、4、9、11、13、16–22（都有【日志】为据）；
  - 14（范围有限：同一镜像上 2 次 noop 与 2 次 gold 逐键一致，另有 M3 的 2 次 gold）；
  - 24、30、32；
  - 26（只到打印类的回归；子类打印记 T3）；
  - 27（附 G1 注：见 §5）。
- **issue**：
  - 5：X1；
  - 23：P4；
  - 25：T2c，另有 T2b 与第 4 步待跑；
  - 31：testutils 通道，通用问题。
- **unknown**：
  - 3；
  - 8、10：actor 侧；
  - 29：派生镜像清除修复提交一事以环境卡为据，本题 actor 侧预检待 devcheck。
- **not_applicable**：7、12、37–40。
- **not_checked**：15、28、33–36。
- **6**：评分侧 pass，actor 侧 unknown。

## 附录 B：证据原件

| 用途 | 路径与行 |
| --- | --- |
| noop（current，09-23） | 账本 `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:21`；日志 `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-n_e62017bf.eval.log`；228/229 |
| gold（current，09-23） | 账本 `runs/r2e_rf_20260923/remote/ledger_r2e_all_gold.jsonl:21`；日志 `…/evallog_replay-r2e-rf-all-gold-n_cffc79f5.eval.log:258`；229/229 |
| noop / gold（current，09-24 复跑） | 账本 `runs/r2e_env_repair_20260924/_rerun2/ledger_{noop,gold}.jsonl:21`；日志 `…/evallog_replay-r2e-envrepair-rer_0338a8c6.eval.log`（47、78-79、313 行）与 `…rer_62e681a9.eval.log:258` |
| 来源 runner 参考 | `runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:39, 88`；`…/logs_r2e/numpy/d805e9b66228/gold/a{1,2}/test_output.txt` |
| 以上日志的完整性 | sha256 都与 `PRIV/run_refs.json` 一致（本审重算过） |

## 附录 C：阅读范围

- **方法文档**：角色卡、八方面协议、环境卡、记录模板、40 项清单、v1 全文。
- **公开包**：
  - 顶层文件全部读过；
  - 工作树中 `numpy/ma/core.py` 读了 2318-2405、2700-2720、3760-3840 行；
  - `numpy/core/arrayprint.py` 读了 25-120、195-520 行；
  - `numpy/ma/testutils.py` 读了 80-140 行；
  - `numpy/lib/shape_base.py` 读了 395-430 行；
  - `doc/release/1.11.0-notes.rst` 读了 245-262 行；
  - `tox.ini`、`.gitignore`、`1.12.0-notes` 用 grep 查过。
- **私有包**：全部文件都读过；`test_1.py` 精读了打印相关的部分，其余按类名和函数名浏览。
- **同仓其它题的公开包**：只 grep 了相关行与题面首行，a5ea773e 另读了题面全文。
- **本地辅助**：在 scratch 里对 base `core.py` 的副本做了补丁 `--check`，并运行了不导入项目代码的一维仿真脚本。
- **没有做的事**：没有运行项目代码，没有开容器，也没有修改任何原件。
