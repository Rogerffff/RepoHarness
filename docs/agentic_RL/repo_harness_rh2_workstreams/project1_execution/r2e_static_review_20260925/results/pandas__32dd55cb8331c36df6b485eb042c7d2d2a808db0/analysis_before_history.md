<!-- 协调者注（2026-09-25）：宿主不允许子会话写报告文件（"Subagents should return findings as text"），本文由协调者从该会话被拒的写入调用中原样取出保存，未改一字。 -->
# pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0：私有主审分析（读历史前）

- 角色：R2E 私有主审（静态审查），2026-09-25。按角色卡第 1–7 步完成；保存本稿前没有打开任何历史调查（阅读范围见附录 B）。
- 证据级别：
  - 【当前执行】`run_refs.json` 中 `material=current` 的账本与日志，即批次三修订后的正式运行，noop、gold 各 2 次。
  - 【历史执行】superseded 行、M3 独立 runner、修订时的一次性容器试跑（`dryrun_b3r2`）。
  - 【静态】读源码和测试得出的推断，没有运行。
- 路径约定：`W/` 指公开包 `worktree/`（即 base 源码），`H/` 指 `PRIVATE_DIR/hidden_tests/`。当前日志按文件名尾号简称：noop 为 `…e72257bb` / `…1d03fd8e`，gold 为 `…9b708f26` / `…28cafc33`。
- 键的简称：**T1** = `TestDataFrameAnalytics.test_mean_extensionarray_numeric_only_true`，**T2** = `TestDataFrameAnalytics.test_mean_datetimelike_numeric_only_false`。

## 0. 速览

1. **题目。**base 的 `DataFrame._reduce` 在 `numeric_only is not None` 时按块归约，EA 块被原样交给 nanops（`W/pandas/core/frame.py:8327-8331`）。Int64 列在 `nanmean` 里调用 `IntegerArray.sum(axis, dtype=float64)`，触发 `nv.validate_sum` 的 ValueError。gold 只改 `blk_func`：EA 块一律改调 `values._reduce(name, skipna=skipna, **kwds)`，其它块照旧调用 `op(values, axis=1, ...)`。
2. **当前材料。**隐藏测试是修复提交版的 `test_analytics.py`，与公开的 `W/pandas/tests/frame/test_analytics.py` 只差两处；另有修订加入的私有 `conftest.py`。期望共 92 键，全部 PASSED：2 个目标键（T1、T2），90 个回归键（其中 13 个由 r2e-mr-016/017 从死键恢复），没有死键。noop 两次都是 0 分（90/92），gold 两次都是 1 分（92/92），同一候选两次运行的日志逐行一致【当前执行】。
3. **主要问题：冲突，影响判分。**T2 要求 Period 列在 `numeric_only=False` 下求 `mean` 时抛出的 TypeError 匹配 `"mean is not implemented for Period"`（`H/test_1.py:899`）。公开旧测试在同一行要求 `"reduction operation 'mean' not allowed"`（`W/pandas/tests/frame/test_analytics.py:899`）。题面只讲 Int64 列和 `numeric_only=True`，没有提 Period，也没有提报错文字。能过 T2 的只有让 Period 列也走 `PeriodArray.mean` 的路线，即 gold 的"所有 EA 都分派"或逐列回退到 Series 归约。下面几种同样能解决题面的合理解，在 T2 上执行的是与 noop 相同的代码，而 noop 日志已经显示这段代码在 T2 上 FAILED，所以整题判 0：
   - 只对数值 EA 分派，或只在 `numeric_only=True` 时分派；
   - 在 nanops 层识别掩码数组；
   - 修改 `IntegerArray.sum` 的签名。
4. **次要问题：漏测。**与题面直接相关的目标键只有 T1，而 T1 只测 `mean`、帧里全是 Int64 列、没有缺失值。"只对 `mean` 分派 EA"的半修能拿 1【静态】。窄修 `IntegerArray.sum`（缺失值计数不对）目前被判 0，只是因为 T2 顺带把它挡住了。
5. **修订核对通过。**
   - conftest 的 7 个 fixture 与 base 最内层定义逐字相同，没有 autouse fixture，也没有 hook。
   - 从 ERROR 改为 PASSED 的 13 个键，正好是请求这些 fixture 的 13 个用例。修订前它们在 noop、gold 和 M3 独立 runner 上都报 `fixture ... not found`，是死键。
   - 修订只恢复了测试支撑，没有弱化断言，也没有扩大需求。T2 的冲突出自来源测试本身，与修订无关。
6. **暂定处置：`needs_review`，原因是题意与测试有争议。**修订前不宜作 reward 题。作 `development_diagnostic` 可以用，但须标注"只有 gold 式路线能得 1"。**唯一最值得先做的下一步**：在当前派生镜像里按评分顺序跑一个非 gold 候选 C1（只对数值 EA 调 `_reduce`），核实三件事：题面行为正确，公开测试全过，RH2 判 0。

## 1. 公开读者没有捕获的条件

| 条件 | 事实与证据 | 对本题的影响 |
|---|---|---|
| 实际渲染消息 | `user_prompt.txt` 是静态渲染，模型实际收到的消息没有捕获（公开读者已注明） | 清单 3 仍记 unknown |
| bottleneck | 评分镜像里没有启用。noop 的 traceback 经过 `nanops.py:129` 的 `alt` 分支（noop 日志 L134-135）。按 `W/pandas/core/nanops.py:115-152`，此时 `skipna=True`，`_bn_ok_dtype(Int64Dtype, "nanmean")` 为 True，走到这个分支只剩 `_USE_BOTTLENECK=False` 一种可能【当前执行 + 静态】 | 公开读者列的最大环境未知项在评分侧已经解决：题面的 `mean` 复现会得到题面那条 ValueError。解题侧用的是同一个 venv，推断相同，但 actor 待验 |
| 版本 | Python 3.7.9、pytest 7.4.4、hypothesis 6.79.4；没有 scipy，`test_kurt` 被 SKIPPED，原因是 "Missing SciPy requirement"（noop 日志 L21-23、L282） | 缺 scipy 只让 `test_kurt` 不成键；skew/kurt 分支有 try/except，会静默跳过 |
| 提示与评分机制 | `public_hints` 说"不要改测试文件，评分会把测试文件重置"。R2E 实际只删除并重放 `r2e_tests/`，公开的 `test_analytics.py` 不参与评分 | 提示会让解题者把公开的 `test_analytics.py` 当作官方回归并尽力让它通过。这恰好把人推向第 0 节第 3 条的失分路线 |
| 正式 actor 镜像 | 环境卡 §2：正式 actor 目前用的是来源镜像，`/r2e_tests` 对所有用户可读，修复提交也可达（M3 账本第 14 行的事实：`fix_reachable=commit`、`r2e_tests_root=1`） | 在来源镜像里，隐藏的 `test_1.py:899` 会直接暴露目标报错文字。进 actor 前必须换成派生镜像。这是共享问题，B 线已排期 |

## 2. 隐藏测试展开

### 2.1 目标键（noop FAILED、gold PASSED）

**T1（`H/test_1.py:902-908`，新增用例）**
- 输入：用 `np.random.randint(1000, size=(10, 5))` 构造 `pd.DataFrame(arr, dtype="Int64")`。帧里 5 个 Int64 列，每列一个 ExtensionBlock，没有缺失值。
- 调用：`df.mean(numeric_only=True)` 先经 `_get_numeric_data`。由于 `Int64Dtype._is_numeric` 为 True（`integer.py:71-72`，`blocks.py:1644-1646`），全部 EA 块都保留，再交给 `df._mgr.reduce(blk_func)`。
- 断言：`tm.assert_series_equal(result, pd.DataFrame(arr).mean())`，要求 float64、索引为 RangeIndex(5)、数值相等。
- noop 的失败路径：`frame.py:8330` → `nanops.py:554 values.sum(axis, dtype=dtype_sum)` → `integer.py:578 nv.validate_sum`，抛出 `ValueError: the 'dtype' parameter is not supported in the pandas implementation of sum()`（noop 日志 L120-187）。这与题面的 Actual Behavior 逐字一致。
- gold 的通过路径：`IntegerArray._reduce("mean")`（`integer.py:556-575`）在没有缺失值时用 int64 的 `_data` 调 `nanops.nanmean(..., mask=mask)`，得到 np.float64 标量；标量经 `managers.py:340-343` 的 EA 分支汇总成 float64 Series。
- 随机性：没有固定种子，但结果与随机数无关。整数都小于 1000，每列 10 个，float64 求和是精确的，两侧都是 sum/10【静态】。

**T2（`H/test_1.py:882-900`，只改了第 899 行）**
- 第一段：帧里是 A（int64）、B（tz-naive datetime）、C（timedelta），调用 `mean(numeric_only=False)`。在这个版本里 B、C 是 ndarray 块，base 和 gold 都走 `op(values, axis=1)`，两边都通过（noop 在 L44-46 没有失败）。这一段同时是 ndarray 分支的回归检查。
- 第二段：加入 Period 列 D（`ObjectValuesExtensionBlock`，持有 `PeriodArray`），断言 `pytest.raises(TypeError, match="mean is not implemented for Period")`。
  - base：`blk_func` 调到 `nanops.nanmean` 上的 `@disallow(PeriodDtype)`（`nanops.py:52-68, 511`），报 `"reduction operation 'mean' not allowed for this dtype"`，正则不匹配，因此 FAILED（noop 日志 L51-80、L105-109）。
  - gold：`PeriodArray._reduce` 经 `DatetimeLikeArrayMixin._reduce`（`datetimelike.py:1555-1560`）调用 `mean`（`:1639-1645`），报 `"mean is not implemented for PeriodArray since the meaning is ambiguous. ..."`，匹配。
- **这个键实际测的是：Period 列 `mean` 的报错由 `PeriodArray.mean` 给出。**这是 gold 路线的副作用，不是题面要求（见 §3、§4）。

### 2.2 回归键（90 个，noop 与 gold 都 PASSED）

- 90 个回归键的测试体，以及 4 个模块级 helper，都与公开 `W/pandas/tests/frame/test_analytics.py` 中的同名内容逐字相同。`diff` 只显示两处差异：新增的 T1，和 T2 的第 899 行。解题者可以直接在工作区跑这些用例。
- **覆盖被修改的 `blk_func` ndarray 分支的键**（该分支在 `numeric_only` 非 None 时进入，覆盖 axis 0/1，`filter_type` 为 None 或 bool）：
  - `test_stat_op_api`：`sum` 在 `numeric_only` 为 True/False、axis 为 0/1 的组合；
  - `test_numeric_only_flag[sem|var|std]`：axis=1，外加两条 TypeError 文案；
  - `test_mean_corner`；
  - `test_mean_datetimelike`：`numeric_only=True` 时排除 datetime、timedelta、period 列；
  - `test_any_all[any|all]`、`test_any_all_extra`、`test_any_all_bool_only`；
  - T2 的第一段。
- **走 `numeric_only=None` 路径、gold 没有改动的键**：`test_stat_op_calc`、`test_median`、`test_mixed_ops[*]`、`test_mean_mixed_datetime_numeric[*]`、`test_mean_excludes_datetimes[*]`、`test_sum_prod_nanops[*]`、`test_operators_timedelta64`、`test_min_max_dt64_with_NaT` 等。
- 其余键（`test_matmul`、`test_mode_*`、31 个 `test_any_all_np_func[*]`、`test_series_broadcasting` 等）不经过本题修改的路径。
- 阅读范围：全部测试体都逐个读过。在 T1、T2 之外，没有任何回归键让 EA 列走 `numeric_only` 非 None 的路径：
  - `test_mode_dropna` 里的 Categorical 列不经过 `_reduce`；
  - `test_any_all_np_func` 里的 category 列走的是 `numeric_only=None` 且 `axis=None` 的路径。

## 3. 双向映射

**公开要求 / 旧行为 → 隐藏键：**

| 需求或旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖 | 执行证据或下一步验证 |
|---|---|---|---|---|
| R1 帧里有 Int64 列时，`mean(numeric_only=True)` 不报错 | 题面示例 | T1 的 `df.mean(numeric_only=True)` | 部分。T1 用的是全 Int64 帧；题面的 int64 + Int64 混合帧没有直接测，但两者走同一个 `blk_func` EA 分支 | noop 报出题面原错（L187）；gold 两次 PASSED |
| R2 结果包含 EA 列 | 题面 Expected Behavior | T1 与 5 列 int64 帧的均值逐项相等 | 覆盖 | 同上 |
| R3 每列结果与逐列 Series 归约一致，dtype 为 float64 | 公开读者 R3；`series.py:4003-4005` | T1 的 `assert_series_equal`，检查 dtype 与索引 | 覆盖（仅无缺失值情形） | — |
| R4 其它归约（sum、prod、min、max、median、std、var 等） | 题面写的是 "reduction operations (e.g., mean)" | 无 | **缺失**。只对 `mean` 分派的半修能拿 1【静态】 | CPU 负例 C3 |
| R5 EA 列含缺失值 | Series 语义（`integer.py:556-575`） | 无 | **缺失**。不处理掩码的窄修在 T1 上能过【静态】 | 若放宽 T2，须同时补缺失值断言（C4） |
| R6 `numeric_only=False` 下的数值 EA | 题面未提 | 无（只有 Period 的报错键） | 缺失（题面不要求） | — |
| R7 `axis=1`；R8 默认的 `numeric_only=None` | 题面未提 | 无 | 缺失（题面不要求；gold 也没修 R8） | — |
| P1 ndarray 块的归约结果和报错文字不变 | 公开 `test_analytics.py` | §2.2 列出的回归键 | 覆盖 | noop、gold 都 PASSED |
| P2 `numeric_only=True` 排除 datetimelike 与 period 列 | 公开 `test_analytics.py:860-874` | `test_mean_datetimelike` | 覆盖 | 同上 |
| **P3 Period 列 `mean(numeric_only=False)` 抛 TypeError，文字为 `reduction operation 'mean' not allowed`** | 公开 `test_analytics.py:899`；`nanops.disallow` | T2 要求相反的文字 `mean is not implemented for Period` | **冲突** | noop 保持 P3 行为，因此被判 FAILED（L105-109） |
| P4 `IntegerArray.sum` 的公开用法；P5 Series 级 EA 归约 | `tests/arrays/integer/test_function.py`、`tests/extension/base/reduce.py` | 不在隐藏测试里 | 不计分 | — |

**隐藏关键断言 → 公开依据：**

| 断言 | 公开依据 | 判断 |
|---|---|---|
| T1：Int64 帧 `mean(numeric_only=True)` 等于 int64 帧的 `mean()` | 题面 Expected Behavior 与示例 | 有依据 |
| T2：Period 报错匹配 `mean is not implemented for Period` | 题面没有。公开测试写的是另一条文字。唯一的间接依据是"DataFrame 归约应与 Series 一致"：`Series._reduce` 对 EA 分派到 `_reduce`（`series.py:4003-4005`），`PeriodArray.mean` 的文字在 `datetimelike.py:1639-1645`。在 `pandas/tests` 与 `doc` 下检索 "mean is not implemented"，没有任何断言使用这条文字 | 与直接公开证据冲突；间接依据只是推断 |
| 90 个回归键 | 公开测试里有同名、同文的用例 | 有依据 |

**替代实现与预计判分**（都满足题面；除 gold 与第二行外，也都让公开测试全过）【静态；T2 一列有 noop 日志支撑】：

| 路线 | 题面示例 | 公开 `test_analytics.py` | T1 | T2 | RH2 得分 |
|---|---|---|---|---|---|
| gold：所有 EA 块调 `values._reduce` | 过 | Period 旧文字用例失败 | 过 | 过 | 1 |
| EA 块逐列回退到 `Series._reduce` | 过 | 同上，失败 | 过 | 过 | 1 |
| **C1**：只对 `is_numeric_dtype(values.dtype)` 的 EA 调 `_reduce` | 过 | 全过 | 过 | 与 noop 同一路径，FAILED | **0** |
| **C2**：只在 `numeric_only is True` 时对 EA 调 `_reduce` | 过 | 全过 | 过 | 同上，FAILED | **0** |
| nanops 层识别 `BaseMaskedArray`，拆成 `_data` 与 `_mask` | 过 | 全过 | 过 | FAILED | 0 |
| **C4**：窄修 `IntegerArray.sum`，让它接受 `axis`/`dtype`（缺失值计数不对） | 无缺失值时过 | 全过 | 过（T1 无缺失值） | FAILED | 0（判 0 的原因是 T2，而不是缺失值处理） |
| **C3**：只在 `name == "mean"` 时对 EA 分派（半修） | 过 | Period 用例失败 | 过 | 过 | **1**（`sum` 仍然报错） |

## 4. R2E 专项

- **(a) 非 PASSED 键。**当前期望 92 键全部 PASSED，没有必须继续失败的键，所以不存在"更完整的修复把 FAILED 翻成 PASSED、反被判 0"的风险。反向也查了：更完整地修 R7、R8（`axis=1`、默认 `numeric_only=None` 路径）不会碰到现有键【静态】。原因有两点：
  - 默认路径下，tz-aware 列会先被 FutureWarning 分支剔除（`frame.py:8277-8286`）；
  - Period 列在 `frame_apply(ignore_failures=True)` 里失败后被丢弃（`apply.py:324-333`），结果与期望相同。

  真正会因为"修法不同或更保守"而被判 0 的是 T2（见 §3）。
- **(b) 题面报错是否出现在 noop 的目标键失败里。**T1 出现，与日志 L187 逐字一致。T2 没有出现：它的 noop 失败是正则不匹配（L107-109），与题面无关。题面由模型根据修复提交和测试生成，却漏掉了测试里被改的 Period 文字。
- **(c) 题面是否泄漏修法。**没有。标题点明了 EA 列和 `numeric_only=True`；Actual Behavior 复述了 `sum()` 的 `dtype` 报错，可能把人引向症状层（`IntegerArray.sum`），但没有给出 `_reduce` 分派的做法。
- **(d) base 版测试辅助、搬迁伪影、跨文件撞键。**
  - `test_1.py` 只导入库模块：`pandas._testing`、`pandas.util._test_decorators`、`pandas.core.algorithms`、`pandas.core.nanops`。helper 都定义在文件内，不导入仓库的测试模块。
  - 搬迁伪影是 fixture 不可达，已由 r2e-mr-016 解决。
  - 只有一个测试文件，两个类，没有同名测试，所以不会撞键。
  - 还有一个共享通道，不是本题特有：评分的 rootdir 是 `/testbed`（日志 L22）。候选若改 `pandas/_testing.py`，或在 `/testbed` 下新增 `conftest.py`、给 `setup.cfg` 加 pytest 段，这些改动在评分时都会生效。按共享审查处理；账本里有 `candidate_touched_conftest_or_fixture` 观测字段。
- **(e) 时间、随机、资源敏感。**
  - T1 用了随机数，但结果是确定的（见 §2.1）。
  - fixture 用 `tm.getSeriesData()` 等随机数据。`test_stat_op_calc` 带有上游注释"GH#32571：个别构建上精度偶发"，但在当前材料下，4 次正式运行和 4 次修订后试跑都是 PASSED【当前/历史执行】。
  - 不依赖时钟、时区或网络。pytest 自报用时 0.36–0.63 s，内存峰值约 726 MB，限额 4 GiB。
- **(f) 修订核对。**
  - **r2e-mr-016。**`H/conftest.py` 的 7 个 fixture 来源如下：`int_frame`、`datetime_frame`、`float_frame` 来自 `W/pandas/conftest.py`；`float_frame_with_na`、`bool_frame_with_na`、`float_string_frame`、`mixed_float_frame` 来自 `W/pandas/tests/frame/conftest.py`。
    - 用 AST 切出源码逐段比较，每个都与 base 最内层定义逐字相同。
    - 装饰器都是不带参数的 `@pytest.fixture`，没有 autouse，没有 `pytest_*` hook，也不导入工作区的 conftest。
    - 修订证据里 `conftest_sources/` 下的两个文件与工作树中的 base 文件逐字节相同。
    - base 里的 autouse fixture（如 `configure_tests`）没有搬过来；gold 仍是 92/92，说明这不影响任何键。
  - **r2e-mr-017。**
    - 从 ERROR 改成 PASSED 的 13 个键，正好是请求上述 fixture 的 12 个测试函数（`test_any_all` 参数化后算 2 个）。键集合不变。
    - 修订前，这 13 键在以下运行里都报 `fixture '...' not found`：R-f 的 noop、试跑的 `noop_orig` / `gold_orig`、M3 的 gold（`79 passed, 1 skipped, 13 errors`）。它们是 noop 与 gold 都 ERROR 的死键。
    - 修订后，在试跑 `fix_a` / `fix_b` 和正式 b5 运行里，noop 与 gold 下这 13 键都是 PASSED，目标键不变。
  - **结论。**修订只恢复了测试支撑，把死键变成了活的回归键。这些用例在公开测试里可见，而且正好覆盖 `blk_func` 的 ndarray 分支。修订没有弱化断言，也没有扩大题面需求。

## 5. gold 检查

- **题面原例：修到了。**混合帧里 A（IntBlock）走 `op(values, axis=1)`，B（Int64）走 `IntegerArray._reduce("mean")`，结果是 {A: 均值, B: 5.5}，dtype 为 float64【静态；同一分支由 T1 的执行结果证实】。
- **修改范围比题面广。**所有 EA 块、所有归约名，无论 `numeric_only` 是 True 还是 False，都改走 EA 自己的实现，与 `Series._reduce` 一致。这是合理的设计。副作用是 Period、Categorical、DatetimeTZ 等列在 `numeric_only=False` 下的报错文字或行为会变；其中 Period 的变化与公开测试冲突，也就是 T2。
- **没有修的相关路径。**默认 `numeric_only=None` 时，混合帧仍会把 Int64 列静默丢掉（公开读者的 R8；`frame.py:8347-8372`，`apply.py:324-333`）。题面不要求修这里，隐藏测试也不查。
- **没有测到的继承问题。**当 `numeric_only=False` 且帧里有 datetimelike 列时，按块路径末尾会调用 `coerce_to_dtypes`（`frame.py:8341-8344`、`cast.py:853-880`），对 `kind == "i"` 的列执行 `int(r)`。`Int64Dtype.kind` 也是 `"i"`（`integer.py:80-81`），所以在 gold 下 Int64 列的均值会被截断，例如 5.5 变成 5。这是 base 对 numpy int 列已有的权宜处理延伸到了 Int64【静态】，不影响任何键。
- **无关改动：没有。**gold 只改了 `blk_func` 的 4 行。来源修复里的 whatsnew 与测试文件已被剔除（M3 账本第 14 行的 `gold_meta.excluded`）。
- **结论。**gold 对题面是正确的，也是合理的一般修法。但它不是唯一的合理解，而 T2 把它的一个副作用写成了得分的必要条件。

## 6. 开发需求（逐题）

| 项 | 需求与依据 | 证据级别 |
|---|---|---|
| 导入 | `python` 指向 `/testbed/.venv/bin/python`（3.7.9）；pandas 就地构建，导入路径是 `/testbed/pandas/__init__.py`（账本字段 `RH2_OBS_IMPORT_PATH`） | 解释器：镜像层面实测（`environment_brief.md`）；导入路径：评分侧实测；解题侧 actor 待验 |
| 依赖 | 不需要装新包；bottleneck 未启用（§1）；没有 scipy；venv 里有 pytest 7.4.4 和 hypothesis 6.79.4 | 评分侧实测；解题侧是同一 venv，actor 待验 |
| 资产 | 无 | 静态 |
| 权限 | agent/54321 可写 `/testbed` 与 home | 镜像层面实测（brief） |
| 网络 | 准备、解题、测试都不需要网络；评分在 `deny_all` 下正常 | 评分侧实测；解题侧为静态推断 |
| 构建 | 只改 `.py`，不需要重新编译。评分日志显示 `RH2_INSTALL_SKIPPED=1`，所以候选若改了 `.pyx`，评分时不会重建 | 评分侧实测 + 静态 |
| 本地验证 | 复现可用公开读者给的 `df.mean(numeric_only=True)`（关闭 bottleneck）或 `df.sum(numeric_only=True)` 命令。回归可跑 `python -m pytest pandas/tests/frame/test_analytics.py`，它包含 90 个回归键的同名用例。注意：其中的 `test_mean_datetimelike_numeric_only_false` 与隐藏的 T2 相反。公开测试能否在 actor 条件下干净跑通，没有看到记录；环境卡说"13 题公开测试有无关失败"，但没有点名本题 | actor 待验 |
| 提交边界 | gold 只触及 `pandas/core/frame.py`（投影 `included_paths`）。R2E 只重放 `r2e_tests/` 与 `run_tests.sh`；候选对仓库测试文件的改动会保留，但不参与评分 | 评分侧实测 + 代码配置（环境卡） |
| 正式 actor 镜像 | 须换成派生镜像（见 §1 最后一行） | 代码事实（环境卡） |

## 7. 八方面覆盖（已查 / 未查）

1. **公开需求。**已查题面、提示、公开测试与相关源码，发现 T2 冲突和 R4、R5 缺口。未查：实际渲染出的消息。
2. **材料与初态。**base 是修复提交的父提交（M3 事实 `head_is_parent_of_fix=yes`）；gold 和隐藏测试都与上游修复对应。noop 在题面所说的路径上报出原错【当前执行】。
3. **测试是否测到要求。**T1 覆盖了题面核心，但只是部分覆盖；R4、R5 未测；T2 测的是副作用。90 个回归键已全部读过。
4. **是否误拒合理解。****是**，原因是 T2（见 §3 的替代实现表），待 CPU 反例确认。
5. **回归与 gold 完整性。**ndarray 分支的回归覆盖充分。gold 没有修 R8，并把 int 截断的权宜处理延伸到了 Int64，两者都不影响判分。未查：其它测试目录（`tests/extension`、`tests/arrays`）在 gold 下的状态。
6. **开发条件。**见 §6；解题侧的正式启动链尚未验证。
7. **交付与评分边界。**只需改 `.py`。共享通道（`pandas/_testing.py`、根目录的 `conftest.py` / `setup.cfg`）按共享审查处理。
8. **题目关系与用途。**未查本题与其它 pandas 题的派生或重叠关系（按要求不读其它题）。题面不泄漏修法；来源镜像会暴露隐藏测试和修复提交（共享问题）。

## 8. 缺口与建议队列（交协调者安排）

1. **CPU 误拒反例（优先）。**在当前派生镜像里按评分顺序跑候选 C1：把 `blk_func` 改成 `if isinstance(values, ExtensionArray) and is_numeric_dtype(values.dtype): return values._reduce(name, skipna=skipna, **kwds)`，其余保持 base 不变。预期结果：
   - 题面示例得到 A、B 两列的均值；
   - 公开 `test_analytics.py` 全过；
   - 隐藏测试 91/92（T2 FAILED），reward 为 0。

   C2（只在 `numeric_only is True` 时分派）可作第二个候选。
2. **CPU 漏测负例。**
   - C3：只在 `name == "mean"` 时对 EA 分派。预期 reward 为 1，但帧里有 Int64 列时 `df.sum(numeric_only=True)` 仍报原错。
   - C4：窄修 `IntegerArray.sum`，让它接受 `dtype`，并且按位置传入的 `axis` 不再绑定到 `skipna`。预期现在 reward 为 0（原因是 T2）。对 `pd.DataFrame({"A": [1, 2, 3], "B": pd.array([1, None, 3], dtype="Int64")}).mean(numeric_only=True)`，B 列得不到 `df["B"].mean()` 的 2.0：因为 `nanops.py:226-229` 对整数 dtype 不给掩码，计数按长度 3 算；若 `skipna` 被错误绑定，则直接报错。
3. **修订草案（需用户或独立审查决定；采纳后形成修订版，清单 37）。**
   - 放宽 T2，让它同时接受两条文字，例如 `match="mean is not implemented for Period|reduction operation 'mean' not allowed"`。公开先例：`W/pandas/tests/reductions/test_reductions.py:350-358` 已经用 `|` 同时接受 nanops 与 EA 两类文字。放宽后，T2 在 noop 上会 PASSED，变成回归键。
   - 同时补一条有公开依据的缺失值断言，依据是 R2、R3：含 `pd.NA` 的 Int64 列，其均值应等于该列的 Series 均值。否则放宽 T2 后，C4 能拿 1。
   - 是否再补 `sum` 的断言（R4）由审查决定。每条新断言都须双向复验：gold、C1、C2 应通过，C3、C4 应不通过。
4. **仍未知。**实际渲染的消息；公开测试能否以 actor 身份运行；正式 actor 链（换成派生镜像、解释器前缀）。

## 9. 暂定处置

- **`disposition`：**`needs_review`，scope 为 `static_review`。原因是题意与测试有争议：目标键 T2 强制要求 gold 路线下 Period 的报错文字，这与公开旧测试冲突，题面也没有提；另有 R4、R5 漏测。
- **用途：**可以作 `development_diagnostic`，但诊断时须把"没有让 Period 走 `PeriodArray.mean` 的正确解"单独归类，因为它们会得 0 分。修订并复验之前，不作训练 reward 题。
- **唯一最值得先做的下一步：**建议队列第 1 条，即 C1 的 CPU 定点运行。

---

## 附录 A：决定性证据索引

| 证据 | 位置 |
|---|---|
| T2 的新旧文字 | `H/test_1.py:899`，对比 `W/pandas/tests/frame/test_analytics.py:899`；两文件的 `diff` 只有这一行和新增的 T1 |
| noop 下 T2 失败 | `runs/r2e_t0_batch3_20260924/replay_b5/eval_logs/evallog_replay-69e318acd762-pand_e72257bb.eval.log` L51-80（`nanops.py:67` disallow）、L105-109（Regex 不匹配）；`…1d03fd8e` 去掉地址和时间戳后与它逐行相同 |
| noop 下 T1 失败即题面原错 | 同一日志 L116-189，其中 L134-135 为 `nanops.py:129` 的 alt 分支，L187 为 ValueError 原文 |
| gold 全过 | `…9b708f26.eval.log` L76-77、L125（`92 passed, 1 skipped`）；`…28cafc33` 与它逐行相同 |
| 账本 | `runs/r2e_t0_batch3_20260924/replay_b5/ledger_b5_noop.jsonl` 第 5、6 行：reward 0，mismatched 为 T1、T2，镜像 `rh2-r2e-derived/pandas:32dd55cb8331-r2e_derive_v1m2`，配方 `r2e_derive_v1+material_v2`，内存峰值 726 MB；`ledger_b5_gold.jsonl` 第 5、6 行：reward 1，`RESOLVED_FULL`，`included_paths=['pandas/core/frame.py']` |
| 修订前的死键 | `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-p_75e948f0.eval.log` L33-132（`fixture ... not found`）、L378-393；`runs/env_overnight_20260916/M3/gold_ledger/logs_r2e/pandas/32dd55cb8331/gold/a1,a2/test_output.txt` L213（`79 passed, 1 skipped, 13 errors`） |
| 修订试跑 | `runs/r2e_t0_batch3_20260924/dryrun_b3r2/pandas_32dd55cb_{noop,gold}_{orig,fix_a,fix_b}.test.log` 的汇总行 |
| 源码路径 | `W/pandas/core/frame.py:8264-8420`（重点看 8317-8345）；`W/pandas/core/internals/managers.py:329-353`；`W/pandas/core/nanops.py:52-81, 84-152, 218-232, 511-554`；`W/pandas/core/arrays/integer.py:71-81, 556-582`；`W/pandas/core/arrays/datetimelike.py:1555-1661`；`W/pandas/core/arrays/base.py:1026-1050`；`W/pandas/core/series.py:3989-4014`；`W/pandas/core/dtypes/cast.py:853-880`；`W/pandas/core/apply.py:318-340` |
| 公开文字先例 | `W/pandas/tests/reductions/test_reductions.py:343-362`；`W/pandas/tests/groupby/test_groupby.py:786-790` |

## 附录 B：阅读范围

- **方法文件：**角色卡；八方面协议；R2E 当批环境卡；记录模板；40 项清单。
- **公开材料：**`public_read.md`（全文）；`user_prompt.txt`；`environment_brief.md`；`public_bundle.json`；`worktree_manifest.json`（顶层键）。工作树中读了附录 A 列出的源码段，以及公开 `test_analytics.py`（与隐藏文件做全文 `diff`，并读了 880-900 行），另外检索了 `pandas/tests` 与 `doc` 下的相关报错文字。
- **私有材料：**`hidden_tests/test_1.py`、`hidden_tests/conftest.py`（均为全文）；`expected_output.json`；`gold.patch`；`run_tests.sh`；`grading_bundle.json`；`validation_bundle.json`；`revisions.json`；`run_refs.json`。
- **运行证据：**
  - 当前 b5 的 noop、gold 日志：各全文读 1 份，另 1 份做了归一化后的 `diff`。账本第 5、6 行读了选定字段。
  - superseded 的 R-f noop 日志：只检索了 ERROR/FAILED 行与汇总行。
  - M3 的 a1、a2：只看了汇总行；M3 账本第 14 行读了前 1500 字符。
  - `dryrun_b3r2` 中本题 6 份 test log：只看了汇总行。
  - `conftest_sources/` 下本题的两个文件：只用 `cmp` 与工作树做了逐字节比较。
- **没有打开：**
  - 任何 history 目录、`docs/.../r2e_env_repair_20260924/`、`*review*` 目录、`r2e_static_review_20260925/README.md`、OUTPUT_DIR 下除 `public_read.md` 以外的文件；
  - `runs/` 下的分析与汇总文件。我列出过 `runs/r2e_t0_batch3_20260924/` 的文件名，因此看到了 `analysis_b3.json` 等文件名，但没有打开；
  - superseded 的 R-f gold 日志和 `_rerun2` 的日志、各 `.diagnostics.json`、其它题的任何材料。
- **没有运行**任何项目代码、容器或远端命令。

## 附录 C：预填 checks（草稿，供第 8 步使用）

| 编号 | 状态 | 要点 |
|---|---|---|
| 1 | pass | base 是修复提交的父提交；gold 是上游修复去掉测试与 whatsnew 后的部分；隐藏测试是修复版测试文件加修订 conftest |
| 2 | pass | noop 下 T1 报出题面原错【当前执行】 |
| 3 | unknown | 实际渲染消息没有捕获；提示里 conda 和"重置测试"的说法不适用 R2E（共享问题 E09） |
| 4 | pass | 只需改 `.py` 就能交付；R2E 不重置其它路径 |
| 5 | not_checked | 没有核对与其它 pandas 题的关系 |
| 6 | pass | 评分侧不需要新依赖 |
| 7 | not_applicable | 本题没有资产 |
| 8 | pass | 评分用户 54322 已实测；解题侧只有镜像层面实测 |
| 9 | pass | 导入路径是 `/testbed/pandas`；gold 让两个目标键翻转 |
| 10 | unknown | 公开测试能否在 actor 条件下运行没有记录 |
| 11 | pass | 各阶段都不需要网络 |
| 12 | not_applicable | 不依赖外部服务 |
| 13 | pass | 评分侧内存 726 MB，测试不到 1 s |
| 14 | pass | noop、gold 各两次，逐行一致；另有修订后的 4 次试跑 |
| 15 | not_checked | 没有核对重置、缓存复用与并发 |
| 16 | pass | 用 `git_apply` 应用，投影只含 `pandas/core/frame.py` |
| 17 | pass | `RH2_SETUP_RESTORED=2`，隐藏测试树的摘要与材料一致 |
| 18 | pass | 收集 93 项，92 项执行、1 项 SKIPPED，测试体确实执行了 |
| 19 | pass | 92 个键互不重复；SKIPPED 不成键 |
| 20 | pass | T1 的 noop 失败来自题面问题；T2 的问题记在 24 |
| 21 | pass | 日志完整，失败原因没有被总分掩盖 |
| 22 | pass | 修订前，M3 独立 runner 与来源期望一致；修订后没有独立 runner 对照，用一次性容器试跑代替（环境卡已说明） |
| 23 | issue | T2 的要求无法从公开材料推知，而且与公开测试冲突 |
| 24 | issue | T2 强制 gold 路线（Period 必须走 `PeriodArray.mean`）；C1、C2 预计判 0 |
| 25 | issue | T1 不含缺失值，也不测其它归约；C3 能拿 1，C4 只是被 T2 顺带挡住 |
| 26 | issue | gold 改变了 P3（与 24 同源）；ndarray 分支的回归覆盖充分；Int64 均值截断未测且不影响判分 |
| 27 | pass | gold 对题面正确且比题面更广；没修 R8，但题面不要求 |
| 28 | pass | 已批准的修订没有引入新要求 |
| 29 | issue | 来源镜像暴露隐藏测试和修复提交（共享问题；进 actor 前须换派生镜像） |
| 30 | pass | 无网络（静态判断；评分侧为 `deny_all`） |
| 31 | unknown | 共享通道（`pandas/_testing.py`、根目录 `conftest.py` / `setup.cfg`）按共享审查处理 |
| 32 | issue | T2 校验的是 gold 路线特有的报错文字 |
| 33–36 | not_checked | 需要真实模型求解 |
| 37 | pass | 修订只恢复测试支撑，并按修订后的 gold 重新核定期望 |
| 38 | pass | 试跑和正式 b5 各有复跑；我没有独立复跑 |
| 39 | not_applicable | conftest 是逐题的，不是共享修复 |
| 40 | not_applicable | 不涉及流程本身的抽样统计 |
