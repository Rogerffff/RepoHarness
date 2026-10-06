# numpy `d805e9b6` 独立复核初判（第一步：未读主审与公开读者产物）

- 题目：`numpy__d805e9b66228e68a0eb14d901cd350159c49af18`；base `25e3ebf4def5`（运行观测 `RH2_OBS_PKG_VERSION: 1.12.0.dev0+25e3ebf`）；已批准材料修订：无（`PRIV/revisions.json` 为 `[]`）。
- 角色与日期：独立复核者，2026-09-29。口径按统一标准 v1 与主审卡"R2E 的评分口径"；本文是读主审产物前封存的初判。
- 证据层级：【静态】读源码或测试推导；【运行】重读已有账本与日志（不是独立重跑）；【待实跑】需要协调者用正式评分实跑。本步没有运行任何项目代码。
- 路径简写（均相对仓库根）：
  - `PUB` = `runs/r2e_static_prep_20260924/v3/public/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/`
  - `PRIV` = `runs/r2e_static_prep_20260924/v3/private/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/`
  - `NOOP1` = `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-n_e62017bf.eval.log`
  - `NOOP2` = `runs/r2e_env_repair_20260924/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_0338a8c6.eval.log`
  - `GOLD1` = `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-gold-n_cffc79f5.eval.log`
  - `GOLD2` = `runs/r2e_env_repair_20260924/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_62e681a9.eval.log`

## 0. 初判一览

| 项 | 初判 | 证据层级 |
| --- | --- | --- |
| 题目目标 | 大的一维 masked array 的字符串表示要像 numpy 普通数组那样截断，并用省略号标出被省略的值。题面例子：`np.ma.arange(2000)`，`a[1:50]` 遮蔽，期望 `repr` 的 data 行为 `[0 -- -- ..., 1997 1998 1999]` | 公开 |
| 严重度 | **S1（T2c，示例拟合）**。唯一的目标断言就是题面示例原样：同一长度、同一遮蔽、同一期望字符串，v1 §4 第 2 步（严格版）命中。第 3 步退化候选 DG-e（只修 `__repr__`，不修 `__str__`）预计得 1，【待实跑】。第 4 步只有 gold 一个现成候选，它的缺口在非默认打印选项与二维上，按边缘路径记 T3 | 静态 + 运行 |
| 误拒 | 未发现。期望字符串逐字来自题面 Expected Behavior；229 个期望键全是 PASSED，没有会惩罚更完整修复的 FAILED / ERROR 键 | 静态 + 运行 |
| 材料 | 一致。4 条 current 运行的隐藏测试树、base、gold、派生镜像都对得上；noop 两次都只错目标键，gold 两次 229/229 | 运行 |
| 题面 | **P4**。Actual Behavior 那段输出与 base 真实输出不符：真实输出是 100 个值、没有省略号；题面写的是带 `...,` 的输出，还说"displaying up to 1000 elements before cutting off"。它与 noop 日志里 pytest 自己截断的 `actual =` 显示逐项对得上，应是把那段截断显示改写而成（§6(b)）。跑一次示例即可消除误解，期望行为本身正确 | 运行 |
| gold | 修好了题面示例，默认打印选项下一维所有长度都正确【静态】。未测缺口：`threshold` 调到 ≥1500 时仍静默丢值；二维窄轴（如 `(2, 2000)`）仍静默丢列，超出"1D"范围。记 G1→T3 | 静态 |
| 题目关系 | X1：本题 gold 的 5 行逐字出现在同仓 5 题（`18b7cd9d`、`2f4a9650`、`43e333e2`、`5e8301c2`、`d89bc4bb`）的公开初态，这些题的公开 `test_core.py` 也已含本题新断言；反向，`a5ea773e` 的 tile 修复与其测试名已在本题初态 | 已逐个核对 |
| 用途（v1） | 问题定位 yes；能力比较 conditional；训练候选 conditional（先完成 R-c 验收）；留出评测 conditional | — |
| 唯一优先下一步 | 一轮正式评分：原材料上跑 DG-e、DG-b（验证 T2b）；按 §9 实施 R-c(1)+(2) 后跑 gold、noop、DG-e、DG-b 验收 | 待实跑 |

复核卡要求的检查项：
- **漏测**：有。T2c；另外 `str()` / `print` 路径、非示例长度、100<n≤1000 时的静默丢值都没有断言（§3）。
- **误拒**：未发现（§5 第 4 条）。
- **错误回归**：gold 在题面范围内没有破坏旧行为。评分没覆盖的回归面有两处：子类 `__str__`、全局打印选项被改，记 T3（§5 第 5 条）。
- **材料错配**：未发现。题面 Actual Behavior 失实，记 P4，不是串题（§6(b)）。
- **开发缺口**：修复是纯 Python，不需构建。本题 actor 侧核对本步没有证据，记"actor 待验"（§5 第 6 条）。

## 1. 实际读取范围

公开：
- `PUB/user_prompt.txt`、`PUB/environment_brief.md`、`PUB/public_bundle.json` 全文；`PUB/worktree_manifest.json` 的汇总字段（`initial_diff` 为 0 字节；`untracked_in_image` 为 `install.sh`、`run_tests.sh`）。
- `PUB/worktree/numpy/ma/core.py`：L2320–2419（`_MaskedPrintOption`、`_print_templates`）、L2700–2724（类属性 `_print_width`）、L3760–3844（`__str__`、`__repr__`）。在 `numpy/` 下 grep `_print_width`，只有 core.py L2713、L3800、L3801 三处。
- `PUB/worktree/numpy/core/arrayprint.py`：L36–65、L173–206（`get_printoptions`）、L205–330、L455–529。
- `PUB/worktree/numpy/ma/tests/test_core.py` 与隐藏测试逐行 diff；`test_subclassing.py` L300–345；其它 ma 测试文件只 grep 了 `str(` / `repr(`；`numpy/lib/shape_base.py` 的 `array_split` 与 `tile`（L860）；`numpy/lib/tests/test_shape_base.py` L355–365。
- 同仓其它题公开包：7 道 numpy 题 `public_bundle.json` 的标题与 base；各题 `worktree/numpy/ma/core.py` 有无 `_print_width_1d`；5 道后续题 `test_core.py` 中 `np.ma.arange(2000)` 的计数，其中 `43e333e2`、`d89bc4bb` 看了上下文，`5e8301c2` 只看计数；`a5ea773e` 的题面开头。

私有与运行：
- `PRIV/gold.patch`、`run_tests.sh`、`revisions.json`、`run_refs.json` 全文；`expected_output.json` 的 229 个键逐一计数；`grading_bundle.json`、`validation_bundle.json` 的字段与摘要。
- `PRIV/hidden_tests/test_1.py`：L1–60、L75–92、L262–280、L312–330、L420–680、L756–768、L1525–1540，外加全文 grep `str(` / `repr(` / `print(` / `set_printoptions` / `set_display`；与 base `test_core.py` 的完整 diff（只多 L454–461 这 9 行）。
- `run_refs.json` 中 4 条 current 账本行（都在第 21 行）的全部字段；4 份 eval 日志：noop 两份读 L1–90、L300–316，gold 两份读头部、L73、L258；M3 参考账本第 39、88 行开头；M3 两份 `test_output.txt` 的 grep。
- 跨题比对：`runs/r2e_static_prep_20260924/cross_task_gold_scan.json`、`cross_task_test_scan.json` 中与本题有关的 6 条。

没读：主审与公开读者产物、`history/`、本批 README / `board.json` / `assignments.json`、其它题私有包、任何审查目录；devcheck 证据（本步没有提供）；`numpy/ma/testutils.py` 源码（只在 NOOP1 L54–81 的 traceback 里看到 `assert_equal` 的字符串分支）；228 个回归键中与打印无关的测试体。

## 2. 公开要求

| 编号 | 公开要求或合理旧行为 | 依据 |
| --- | --- | --- |
| R1 | 大的一维 masked array 的 `repr` 要截断，并用省略号表示省略的值。题面例子的期望 `repr` 逐字给出：`data = [0 -- -- ..., 1997 1998 1999]`、`mask = [False  True  True ..., False False False]`、`fill_value = 999999` | `PUB/user_prompt.txt` L5、L10–24 |
| R2 | 标题是"Incorrect String Representation"，描述是"When creating and printing ..., the string representation does not truncate"，所以 `str(a)` / `print(a)` 也在核心要求内。v1 §4 把核心要求定为"题面标题与期望行为"；而且 `repr` 的 data 字段本身就是 `str(self)` | L5、L7–8；base `core.py` L3827–3829 |
| R3 | 截断格式与 numpy 普通数组一致：前后各 3 项，中间是 `..., `。题面 mask 行本身就是 ndarray 的标准摘要。numpy 文档写明 `threshold` 默认 1000（元素总数超过它才摘要），`edgeitems` 默认 3 | L22–23；`arrayprint.py` L37–38、L62–64、L252–257、L473–480 |
| R4 | 被省略的值必须用省略号标出，不能静默丢值 | L20 "using an ellipsis to indicate omitted values" |
| R5 | 小数组旧行为不变：`[0 -- 2]` 与三行 `repr` 模板 | base `test_core.py` L447–452（公开） |
| 范围外 | 二维及更高维：标题限定"1D" | L5 |

只用公开材料就能写出正确修复：示例能在 base 复现症状（虽与题面 Actual 文本不同，见 §6(b)），期望格式逐字给出，不需要猜新 API 名或文案。

## 3. 目标键、断言与双向映射

目标键只有 `TestMaskedArray.test_str_repr`，它是 noop 与 gold 结果唯一不同的键（§4）。隐藏测试就是修复提交后的 `numpy/ma/tests/test_core.py`：M3 账本 `gold_meta.excluded` 列的是这个文件；它与 base 版逐行比较，只多 `PRIV/hidden_tests/test_1.py` L454–461：

```python
a = np.ma.arange(2000)
a[1:50] = np.ma.masked
assert_equal(repr(a), 'masked_array(data = [0 -- -- ..., 1997 1998 1999],\n' ...)
```

断言用 `numpy.ma.testutils.assert_equal`（L25–29 导入）；对字符串，它做 `desired == actual` 的精确比较（NOOP1 L54–81）。

| 要求 | 测试 ID / 决定性断言 | 覆盖 | 说明 |
| --- | --- | --- | --- |
| R1 示例的 `repr` | `test_str_repr` L454–461 | 覆盖，但只有示例字面值 | 输入与期望逐字等于题面 L12–24 |
| R2 `str` / `print` | 无 | **缺失** | 大数组的 `str()` 没有断言，只修 `__repr__` 的补丁不受约束 |
| R1/R3 非示例实例（其它长度、遮蔽位置、dtype） | 无 | **缺失** | 1000<n≤1500（gold 不裁剪，交给 numpy 摘要）和 n>1500 的其它长度都没测 |
| R4 100<n≤1000 不静默丢值 | 无 | **缺失** | base 对任何 n>100 且带遮蔽的一维数组都只印前 50 与后 50 个值，没有省略号。gold 修好了，但没有测试 |
| R5 小数组 | `test_str_repr` L447–452；`test_basic0d` L80–87；`test_fancy_printoptions` L651–669；`test_mvoid_print` / `test_mvoid_multidim_print` L756–803 | 覆盖 | 回归键，noop 与 gold 都通过 |
| 打印冒烟 | `test_indexing` L277–278、`test_matrix_indexing` L327–328、`test_assign_dtype` L1537 | 只测不抛错 | 都是小数组，没有输出断言 |
| 子类 `__str__` 保留（公开旧测试） | `test_subclassing.py` L318–341，**不在评分集** | 评分外缺失 | 重写 `__str__` 时绕过 `str(res)` 的实现会丢掉 `myprefix` / `mypostfix`，评分发现不了 |

反查：唯一的新断言完全来自题面 Expected Behavior，有公开依据；mask 行与 `fill_value` 行是 base 已有格式。

## 4. 运行原件核对（`run_refs.json` 中 `material=current` 的 4 行）

| 运行 | 账本行 | 结果 | 日志要点 |
| --- | --- | --- | --- |
| R-f 全池 noop | `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:21` | reward 0.0，228/229，mismatched = [`TestMaskedArray.test_str_repr`]，missing 与 unexpected 为空，test_rc 1 | NOOP1 L3 隐藏测试树 `088fe58b…`（与 current 相同）；L17 pytest 7.4.4；L20 collected 229；L78 ACTUAL；L312–313 |
| R-f 全池 gold | `runs/r2e_rf_20260923/remote/ledger_r2e_all_gold.jsonl:21` | reward 1.0，229/229，`included_paths=['numpy/ma/core.py']` | GOLD1 L1 ` M numpy/ma/core.py`；L73 目标键 PASSED；L258 229 passed |
| 环境轮复跑 noop | `runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl:21` | 与上面 noop 相同 | NOOP2 L78 的 ACTUAL 与 NOOP1 逐字相同 |
| 环境轮复跑 gold | `runs/r2e_env_repair_20260924/_rerun2/ledger_gold.jsonl:21` | 与上面 gold 相同 | GOLD2 L73、L258 |

四次都用同一派生镜像 `sha256:fd832b05…`（`rh2-r2e-derived/numpy:d805e9b66228-r2e_derive_v1`），评分用户 54322，2 CPU / 4 GiB，断网；测试耗时 1.2–1.6 s，内存峰值约 300 MB。M3 独立 runner 在来源镜像上跑 gold 两次都是 229 passed（`runs/env_overnight_20260916/M3/gold_ledger/logs_r2e/numpy/d805e9b66228/gold/a1/test_output.txt` 与 `a2/` 的 L58、L243），只作对照。

**base 真实初态**（NOOP1 L78，执行证据）：data 行是 `[0 -- … -- 1950 1951 … 1999]`，共 100 个值（`0`、49 个 `--`、`1950`–`1999`），**没有省略号**，中间 1900 个值被静默丢掉；mask 行已经正常摘要。原因【静态】：base `core.py` L3797–3806 先用 `_print_width = 100` 把每一轴裁到 50+50 = 100 个值；100 没超过 numpy 的摘要阈值 1000（`arrayprint.py` L252），于是 numpy 把这 100 个值原样全部打印。gold 把一维的裁剪宽度改成 1500（>1000），裁剪后的数组仍会触发 numpy 摘要（`PRIV/gold.patch` L5–31）。

## 5. 八方面

1. **公开需求**：见 §2。查了题面、公开提示、base 源码、numpy 打印文档与公开旧测试。
2. **材料与初始问题**：base、gold、隐藏测试、镜像一致；原问题在 base 上成立，执行证据是 NOOP1 / NOOP2 L78。镜像初态相对 base 没有改动（`worktree_manifest.json` 的 `initial_diff` 为 0 字节）。题面 Actual 失实，见 §6(b)。
3. **测试是否测到要求**：核心要求有直接断言，但只用示例字面值（T2c）；`str` 路径和非示例实例缺失（§3）。
4. **误拒**：未发现。唯一新断言的精确字符串逐字来自题面 L21–24。几种合理替代实现对该示例输出同一字符串【静态】：把 `_print_width` 调到 ≥1002、一维不裁剪、按 `threshold` 决定裁剪。把 `_print_width` 调到 1000 或 1001 会被判 0，但这类补丁本身没修好：裁剪后只剩 ≤1000 个值，numpy 不会摘要。所以这不是误拒。
5. **回归与 gold 完整性**：
   - gold 只改 `numpy/ma/core.py` 两处，没有无关改动；默认打印选项下，一维所有长度都正确【静态】。
   - G1 缺口，都没有测试：(i) 执行 `np.set_printoptions(threshold=3000)` 后，带遮蔽的 `np.ma.arange(2000)` 仍被裁到 1500 个值且没有省略号；(ii) 二维窄轴，例如 `(2, 2000)` 仍被裁到 `(2, 100)`，共 200 个值，不触发摘要，静默丢列。题面限定 1D，所以 (ii) 在范围外。更完整的修复不会被现有键惩罚，因为评分集里没有大二维或打印选项断言。
   - 评分外的回归面：子类 `__str__`（`test_subclassing.py` L329–341）；全局打印选项被改（numpy core 的打印测试不在评分集）。
   - 性能：一维完全不裁剪的替代解输出正确，但丢掉了 base 注释写明的性能优化（`core.py` L3797–3798）。打印超大数组时会把全部元素转成 object。没有测试，记 T3。
6. **agent 开发条件**：
   - 环境（`PUB/environment_brief.md` L10–13）：Python 3.7.9 的 `/testbed/.venv`；没有 pip、没有网络；`/testbed` 必须在 `sys.path` 上；用 `python -m pytest`。修复是纯 Python，不需要重编译。
   - 建议的最小公开验证：
     - `cd /testbed && python -c "import numpy as np; a=np.ma.arange(2000); a[1:50]=np.ma.masked; print(repr(a)); print(a)"`
     - `cd /testbed && python -m pytest numpy/ma/tests/test_core.py -q`（可加 `numpy/ma/tests/test_subclassing.py`）
   - 评分侧跑完整个文件约 1–2 s。本题 actor 侧实测本步没有证据：actor 待验。
7. **交付与评分边界**：
   - 合法修复只涉及 `numpy/ma/core.py`（或 `numpy/core/arrayprint.py`），都是纯 Python，按文件差异就能导出（见 gold 账本的 `included_paths`）。
   - 隐藏测试依赖仓库自带的 `numpy.ma.testutils` 与 `numpy.testing`：它们是 base 版，候选可以改，评分时不会重置。这是 R2E numpy 题的通用风险，不是本题特有；事后审计可以查候选有没有改这两处。
   - 没有 conftest 依赖、相对路径资源或跨文件撞键。
8. **题目关系与用途**：X1，见 §0 与附录 C；用途见 §10。

## 6. R2E 专项

- **(a) 非 PASSED 期望键**：没有，229 个键全是 PASSED。更完整的修复（同时修二维，或遵守 `threshold` / `edgeitems`）对示例输出同一字符串；现有 228 个回归键里没有大二维或非默认打印选项的断言，所以不会被判 0【静态】。
- **(b) 题面描述的报错是否出现在 noop 目标键**：总体症状出现了。noop 失败的原因正是 data 行没有截断成 `[0 -- -- ..., 1997 1998 1999]`（NOOP1 L78–79）。但题面 Actual Behavior（`PUB/user_prompt.txt` L27–34）与 base 真实输出不符：
  - 真实输出是 100 个值，没有省略号，以 `1950 … 1999` 结尾；
  - 题面写的是第二行 7 个 `--` 后接 `..., 1997 1998 1999`，并说"displaying up to 1000 elements before cutting off"；
  - 题面第一行的 24 个 `--` 和第二行的 7 个 `--`，与 NOOP1 L50 中 pytest 自己截断的 `actual = '…-- -- --... 1996 1997 1998 1999]…'` 逐项对得上。可见题面是把 pytest 的截断显示误写成了 numpy 的省略号。

  记 **P4**：agent 跑一次示例就能看到真实输出，期望行为不受影响。开发核对应记录"原例能复现症状，但输出与题面 Actual 文本不同"。
- **(c) 题面是否泄漏修法**：没有。题面没提 `_print_width`、裁剪、1500，也没提裁剪宽度与阈值的关系；"1000"只出现在失实的 Actual 描述里。期望输出逐字等于隐藏断言，这是 R2E 常态，不算 P1。
- **(d) 测试支撑与撞键**：
  - 依赖 base 版 `numpy.ma.testutils`，是通用风险（§5 第 7 条）。
  - 没有搬迁伪影：不用 conftest，也不用相对路径资源；pytest rootdir 是 `/testbed`，账本 `RH2_OBS_IMPORT_PATH` 是 `/testbed/numpy/__init__.py`。
  - 只有一个隐藏文件；collected 229 等于期望 229，`keys_equal=True`，没有撞键。
- **(e) 时间、随机、资源敏感键**：未见。目标测试是确定性的；4 次评分和 2 次 M3 运行里，228 个回归键全部通过。`test_mvoid_print` 用 `finally` 还原 `masked_print_option.set_display`（L762–767），没有全局打印状态泄漏，所以新增断言不受测试顺序影响。
- **(f) 材料修订**：没有，不适用。

## 7. v1 §4 严重度

| 步 | 结果 | 依据 |
| --- | --- | --- |
| 1 核心要求有无直接断言 | 有 | test_1.py L454–461 |
| 2 是否只用题面示例的字面值 | **是 → S1（T2c）** | `np.ma.arange(2000)`、`a[1:50]` 和期望字符串都与题面 L12–24 逐字相同；整个文件没有其它大一维数组的打印断言 |
| 3 退化探测 | DG-e 预计得 1【待实跑】；若得 1，另记 T2b | §8 |
| 4 已有候选 | 只有 gold，没有真实模型候选。gold 在非默认 `threshold≥1500` 时仍静默丢值，这是"不静默丢值"要求在非默认全局选项下的一个实例。我按边缘路径判 T3（S2 级，登记）。若按严格读法判 S1，就需要 D4 的替代正对照，成本高、收益低，建议只登记 | §5 第 5 条 |
| 综合 | **S1**（T2c 已命中；T2b 待实跑） | — |

实际可利用程度（静态判断，供取舍）：对 n>1000 的一维数组，大多数按长度处理的修复会自然推广；把长度写死成 2000 的补丁不自然。现实的蒙混路径有两条：(1) 只修 `__repr__`，因为题面 Expected Behavior 那句只点名 `repr`，测试也只查 `repr`；(2) 只对 n>1000 生效、在 100<n≤1500 出错的半截修复。R-c 应覆盖这两条。

## 8. 候选（可直接写成补丁；预期结果是静态推导，待正式评分实跑）

**DG-e（主退化候选；方向是"抑制症状 / 作用在无关对象上"）**
- 改动：`numpy/ma/core.py` 的 `MaskedArray.__repr__`（base L3816–3836）。把 `parameters` 里的 `data=str(self)` 换成下面的计算，`__str__` 和 `_print_width` 都不动：
  ```python
  opts = np.get_printoptions()
  if self.ndim == 1 and self.size > opts['threshold']:
      e = opts['edgeitems']
      data = '[%s ..., %s]' % (str(self[:e])[1:-1], str(self[-e:])[1:-1])
  else:
      data = str(self)
  ```
- 预期得分：1。示例的 `repr` 正好等于期望字符串；3 元素部分仍走 `str(self)`，结果不变；其它键不受影响。
- 违反的公开要求：R2（标题"String Representation"、描述"printing"）。输入就是题面原例：`a = np.ma.arange(2000); a[1:50] = np.ma.masked; print(a)` 或 `str(a)`，输出仍是 base 的 100 个值、没有省略号，与 NOOP1 L78 的 data 字段相同；而且 `repr(a)` 的 data 字段与 `str(a)` 不一致。
- 说明：DG-e 改的是 gold 所改函数的直接调用者（`__repr__` 用 `str(self)` 取 data，base L3828），不是 gold 改动的函数本身；题面 Expected Behavior 那句也只点名 `repr`。如果协调者或 Codex 认为 `str` 不属于核心要求，或要求退化候选严格落在 gold 改动的函数内，就改用 DG-b。

**DG-b（备选退化候选；只照抄 gold 的一半）**
- 改动：`numpy/ma/core.py`。像 gold 一样新增 `_print_width_1d = 1500`，并在 `__str__` 里算出 `print_width`；但裁剪条件仍写 `if data.shape[axis] > self._print_width:`（即 100），只把 `ind` 改成 `print_width // 2`。
- 预期得分：1。n=2000 走的路径与 gold 相同；评分集里没有 100<n<1500 的带遮蔽一维打印断言。
- 违反：R4，以及"输出显示的是数组自身的值"这一基本行为。输入：`d = np.ma.arange(200); d[100] = np.ma.masked; str(d)`。`np.split(data, (750, -750))` 在长度 200 上切出的首段和尾段都是整个数组（base `array_split` 按普通切片 `sary[st:end]` 实现），所以输出 400 个值（0…199 重复两遍），没有省略号。n=1200 时的重复会被 numpy 摘要掩盖，所以只有 R-c(2) 能拦住它。

**可区分的合理替代解（可选，只在需要替代正对照时跑）**
- ALT-1：只把 `_print_width = 100` 改为 `_print_width = 2000`，各维共用。预期得 1，R-c(1)、R-c(2) 都应通过；代价是打印大二维数组时要转换更多元素（只影响性能，不影响输出）。

## 9. 修订建议（v1 §5；由协调者实施与实测，Codex 复核）

**R-c(1)（必做：解决 T2c，并拦住 DG-e）**
- 公开依据：
  - 标题"Incorrect String Representation for Large 1D Masked Arrays"；
  - 描述"When creating and printing a large 1D masked array, the string representation does not truncate"；
  - Expected Behavior 给出的格式：前后各 3 项，中间 `..., `；
  - numpy `threshold` 文档（`arrayprint.py` L62–64）。
- 改动：在 `PRIV/hidden_tests/test_1.py` 的 `TestMaskedArray.test_str_repr` 中，L461 之后追加下面的断言。不新增测试函数，因此键集与 `expected_output.json` 都不变：
  ```python
          # 同一数组的 str()（print 走这条路径）
          assert_equal(str(a), '[0 -- -- ..., 1997 1998 1999]')

          # 非示例实例：长度 1200（超过 numpy 摘要阈值 1000），遮蔽在尾部
          b = np.ma.arange(1200)
          b[-2:] = np.ma.masked
          assert_equal(str(b), '[0 1 2 ..., 1197 -- --]')
          assert_equal(
              repr(b),
              'masked_array(data = [0 1 2 ..., 1197 -- --],\n'
              '             mask = [False False False ..., False  True  True],\n'
              '       fill_value = 999999)\n'
          )

          # 非示例实例：长度 10000，遮蔽在头部
          c = np.ma.arange(10000)
          c[0] = np.ma.masked
          assert_equal(str(c), '[-- 1 2 ..., 9997 9998 9999]')
  ```
  期望字符串是【静态】推导：依据 base `arrayprint.py` 的规则（阈值 1000、前后各 3 项、object 元素用 `repr` 格式化、中间插 `..., `）和 gold 的裁剪逻辑。必须用 gold 实跑确认。如果 gold 的实际输出不同，在差异不违反 R1–R4 的前提下，以核实后的 gold 输出为准，并记录差异。每个实例都至少带一个遮蔽值，因为 `nomask` 时 `__str__` 直接走 `str(self._data)`（`core.py` L3777–3778），根本不经过裁剪代码。
- 验收：gold=1；noop=0；DG-e=0（`str(a)` 与 `str(b)` 两处失败）；公开核心要求 R1–R3 都有直接断言。

**R-c(2)（建议做：拦住 DG-b 这类半截修复，依据 R4）**
- 公开依据：Expected Behavior 的"using an ellipsis to indicate omitted values"，即被省略的值必须标出。base 对任何 n>100 的带遮蔽一维数组都会静默丢值，与题面是同一个缺陷。
- 改动：在同一个测试函数里再追加：
  ```python
          # 长度 200：要么显示全部 200 个值（含 1 个 --），要么用省略号标出省略
          d = np.ma.arange(200)
          d[100] = np.ma.masked
          shown = str(d).replace('[', ' ').replace(']', ' ').split()
          assert_('...,' in shown or (len(shown) == 200 and shown.count('--') == 1))
  ```
  这是宽松写法，只要求"不静默丢值"，不钉死摘要阈值；因此"阈值取 100 并加省略号"这类实现不会被误拒。严格写法是 `assert_equal(len(shown), 200)`，即要求与 numpy 默认阈值 1000 一致、data 行与 mask 行同样不摘要。它的依据是 numpy 文档和题面 mask 行的格式，但题面没有直接说小于 1000 的数组不截断，所以**用哪种写法交协调者或用户决定**。
- 验收：gold=1（不裁剪，完整显示 200 个值）；noop=0（100 个值，不含 `--`）；DG-b=0（400 个值）；DG-e=0。

**R-f（可选，低优先；对应 P4）**
- 改动：把 `PUB/user_prompt.txt` L27–34 的 Actual Behavior 换成在 base 上实跑证实的输出（NOOP1 L78 的 data 行：100 个值，没有省略号），并删去"displaying up to 1000 elements before cutting off"。
- 验收：按 v1 §5 的 R-f 流程：新的公开读者读修订后的题面，逐行核对没有带入隐藏细节。
- P4 默认只登记；这一条不做，也不影响训练资格。

**可选 R-c(3)（低优先，回归保护）**
- 改动：把公开的 `numpy/ma/tests/test_subclassing.py` 中 `test_subclass_repr`、`test_subclass_str`（L318–341）加入隐藏测试，并补上期望键；需同时验证 noop 与 gold 都是 PASSED、没有撞键。
- 它只保护"改写 `__str__` 时不丢子类 `__str__`"这一条旧行为；不做就记 T3。

**不建议**：加入非默认 `set_printoptions(threshold=…)` 的断言。gold 会失败，需要走 D4 的替代正对照；而题面没提打印选项，加进去属于扩大需求。

## 10. 用途结论（v1 §2，初判）

| 用途 | 取值 | 差什么条件 / 依据 |
| --- | --- | --- |
| `problem_localization` | yes | 无门槛 |
| `capability_comparison` | conditional | 评分依据已核（§4）。还差：本题 actor 侧开发核对的证据；R-c 之前如果做比较，要把 T2c 写进事后审计，对得 1 的补丁再查 `str(a)` 和一个非示例长度 |
| `training_candidate` | conditional | 当前有未处理的 S1，不能进训练。还差：R-c(1)（建议连同 R-c(2)）实施并验收；退化探测的正式结果；actor 开发核对；并登记 P4、T3 / G1、X1 |
| `heldout_candidate` | conditional | 先满足训练候选的全部条件。另外：按 D3 按仓库划分时，5 道后续 numpy 题的初态含本题答案和本题新测试，必须与本题分在同一侧；修订后只能作"标明版本的自建评测"；不得用于选模型或调提示 |
| `intended_use` | `development_diagnostic` | — |

## 11. 探针就绪差距

本步按指令没有读本批 README，无法逐条对照其 §3。下面按 v1 §2 的训练候选条件列出，由协调者映射到 README §3。

| 条件 | 状态 | 谁来补 |
| --- | --- | --- |
| 当前材料 noop=0、gold=1 | 已满足：各 2 次，同一派生镜像、同一隐藏测试树 | — |
| 核心要求有直接断言 | 已满足，但只有示例 | — |
| §4 第 2 步 | 未满足（T2c） | 协调者实施 R-c(1) / R-c(2)，Codex 复核 |
| §4 第 3 步退化探测 | 未满足：DG-e、DG-b 还没实跑 | 协调者用正式评分实跑 |
| actor 开发核对（公开命令、原例复现、墙钟时间） | 未满足：本步没有证据 | 协调者跑 devcheck |
| 登记 P4、G1 / T3、X1 | 本文已列出，待写进题卡 | 主审或协调者 |

## 12. 未知项与唯一优先的下一步

- 未知：
  - 本题 actor 侧的实际条件；
  - 主审给出的退化候选；
  - `str()` 是否被认定为核心要求（决定 DG-e 的违例论证是否成立，不成立就用 DG-b）；
  - R-c 期望字符串待 gold 实跑确认。
- 唯一优先的下一步：一轮正式评分。先在原材料上跑 DG-e 和 DG-b（预计都得 1，用来确认 T2b），再实施 R-c(1)+(2)，用 gold、noop、DG-e、DG-b 验收。

---

## 附录 A：关键定位

| 事实 | 位置 |
| --- | --- |
| 题面标题、描述、示例、期望、实际 | `PUB/user_prompt.txt` L5、L7–8、L10–17、L19–25、L27–34 |
| 公开提示（`.venv`、不联网、不要改测试文件、用 `python -m pytest`） | `PUB/public_bundle.json` L15；`PUB/environment_brief.md` L10–13 |
| `_print_width = 100` 与注释 | `PUB/worktree/numpy/ma/core.py` L2712–2713 |
| `__str__`：`nomask` 分支、裁剪、转 object、`str(res)` | 同文件 L3777–3778、L3797–3805、L3806–3807、L3814 |
| `__repr__`：`data=str(self)`、`short_std` 模板 | 同文件 L3827–3829、L3834–3835；模板 L2396–2400 |
| numpy 摘要规则 | `PUB/worktree/numpy/core/arrayprint.py` L37–38、L62–64、L234–235、L252–257、L315–316、L473–480、L489–490 |
| gold 改动 | `PRIV/gold.patch` L5–15（类属性）、L18–31（`__str__`） |
| 目标断言 | `PRIV/hidden_tests/test_1.py` L447–461（新增 L454–461） |
| 期望映射 | `PRIV/expected_output.json`：229 键，全部 PASSED |
| 评分命令 | `PRIV/run_tests.sh` L1 |
| noop 失败的真实输出与 pytest 截断显示 | NOOP1 L50（截断显示）、L78（ACTUAL）、L79（DESIRED）、L312–313；NOOP2 相同行号，内容相同 |
| gold 通过 | GOLD1 与 GOLD2 的 L73、L258 |
| 评分外的子类打印测试 | `PUB/worktree/numpy/ma/tests/test_subclassing.py` L318–341 |

## 附录 B：输出机制（静态推导）

- base，一维、带遮蔽、长度 n：n≤100 时完整打印；n>100 时只打印前 50 和后 50 个值，没有省略号（裁剪后恰好 100 个值，永远不超过阈值 1000）。
- gold，一维、带遮蔽：n≤1000 完整打印；1000<n≤1500 不裁剪，由 numpy 摘要；n>1500 裁到 1500 个值，仍由 numpy 摘要。
- 没有遮蔽（`nomask`）时，`__str__` 直接 `str(self._data)`，不经过裁剪，base 本来就正确。R-c 的每个实例都至少带一个遮蔽值，就是这个原因。
- 裁剪宽度 W 对长度 2000 的示例：W≤1001 时裁剪后 ≤1000 个值，不摘要，判 0；W≥1002 时正确。所以只把常量调大到 ≥1002 就是合理修复。

## 附录 C：跨题关系（机械扫描 + 逐个核对）

- `cross_task_gold_scan.json`：本题 gold 的 5 行全部出现在 5 道题的公开初态（`18b7cd9d`、`2f4a9650`、`43e333e2`、`5e8301c2`、`d89bc4bb`）。
  - 我逐题 grep 核实：这 5 题的 `core.py` 里都有 `_print_width_1d = 1500`，`test_core.py` 里都有 `np.ma.arange(2000)`。
  - `43e333e2`、`5e8301c2`、`d89bc4bb` 各有 2 处。我看过上下文的两题（`43e333e2`、`d89bc4bb`）里，一处是 numpy 1.14 的新 repr 风格，另一处是在 legacy 打印模式里原样保留本题断言。上游后来也没有为这个行为补非示例实例。
  - 反向：扫描没有发现别题的 gold 出现在本题初态。
- `cross_task_test_scan.json`：`a5ea773e`（tile 不复制）的新测试名 `test_tile_one_repetition_on_array_gh4679` 已在本题初态（`PUB/worktree/numpy/lib/tests/test_shape_base.py` L357），对应的修复分支也在（`numpy/lib/shape_base.py` L860）。这与本题功能无关，影响的是 `a5ea773e` 的留出资格。
- 同仓其它 numpy 公开题（poly1d、savetxt、ma.average、einsum、tile、histogram2d）都不涉及 masked array 打印。
