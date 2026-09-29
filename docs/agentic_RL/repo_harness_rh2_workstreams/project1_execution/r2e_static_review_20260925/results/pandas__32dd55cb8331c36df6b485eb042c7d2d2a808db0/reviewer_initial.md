# pandas__32dd55cb8331 独立初判（复核第一步）

2026-09-25 · 独立复核者（R2E 静态审查，干净上下文）。写本稿前未读 `public_read.md`、主审产物、`history/`、环境阶段记录与任何审查目录；未运行项目代码或容器，未改任何原件。

路径简写（均相对仓库根）：

- `PUB` = `runs/r2e_static_prep_20260924/v2/public/pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0`
- `PRIV` = `runs/r2e_static_prep_20260924/v2/private/pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0`
- `B5` = `runs/r2e_t0_batch3_20260924/replay_b5`（`run_refs.json` 里 `material=current` 的四次运行）
- **noop 日志** = `B5/eval_logs/evallog_replay-69e318acd762-pand_e72257bb.eval.log`；第二次 `…_1d03fd8e` 除地址、时间外与之相同。
- **gold 日志** = `B5/eval_logs/evallog_replay-caf6d2fe3186-pand_9b708f26.eval.log`；第二次 `…_28cafc33` 的 short summary 与之相同。

## 0. 结论先行

1. **题面主需求清楚，材料一致。** 题面说：`df.mean(numeric_only=True)` 遇到 `Int64` 等 ExtensionArray（下称 EA）列时，报 `the 'dtype' parameter is not supported in the pandas implementation of sum()`。
   - noop 下目标键 `test_mean_extensionarray_numeric_only_true` 的失败原因与题面逐字相同（noop 日志 L187）。
   - gold 两次都得 1。
   - 两项修订只恢复了 fixture 支撑，没有放宽断言。
2. **最重要的问题：误拒风险高（静态推断，待 CPU 验证）。**
   - **隐藏要求**：另一个目标键 `test_mean_datetimelike_numeric_only_false` 要求，当 `numeric_only=False` 且含 Period 列时，`df.mean` 抛出 TypeError，且文案匹配 `"mean is not implemented for Period"`（`PRIV/hidden_tests/test_1.py` L899）。
   - **题面没有依据**：题面没提 Period、`numeric_only=False` 或报错文案。这个文案只是 gold 把 EA 分派给 `values._reduce` 后顺带产生的结果。
   - **与公开测试互斥**：公开工作树里同名旧测试断言旧文案 `"reduction operation 'mean' not allowed"`（`PUB/worktree/pandas/tests/frame/test_analytics.py` L899）。同一个 `df.mean(...)` 调用不可能同时满足两条断言。
   - **后果一**：修好题面问题、但不走 `_reduce` 分派的合理实现会得 0，例如在 nanops 层处理掩码 EA，或只对数值 EA 分派。
   - **后果二**：解题者按 gold 修好后跑公开测试，会看到这条旧测试失败。如果他为了"不破坏已有测试"而保留旧文案，也会得 0。
   - **后果三**：同一个键却放过"只对 `mean` 分派 `_reduce`"这种不完整修复。
3. **次要漏测。** 隐藏测试只测全 `Int64` 列、无缺失值、`axis=0` 下的 `mean`。以下两项没有直接断言：
   - 题面原例：numpy 列与 `Int64` 列混合。
   - 题面所说的其它归约：sum、std、var、min、max 等。
4. **暂定处置**：`needs_review`，理由归为题意/测试争议，不是环境问题。唯一最值得先做的下一步见 §6：做 CPU 反例。

## 1. 材料与初始问题

- **哈希**：`PRIV` 下五个文件的哈希与 `grading_bundle.json` L8/L12/L16/L31 及 `validation_bundle.json` L7 一致：
  - `expected_output.json` `9771cde5…`
  - `hidden_tests/conftest.py` `053ce359…`
  - `hidden_tests/test_1.py` `4a153a37…`
  - `run_tests.sh` `8285765f…`
  - `gold.patch` `7391277e…`

  四份 current 日志的 sha256 与 `run_refs.json` L114/L136/L156/L174 一致。
- **base**：
  - `public_bundle.json` L9 记的 base 是 `b7f061c3d24d…`。
  - 对工作树的 `pandas/core/frame.py` 跑 `git hash-object`，得 blob `f8cb99e2b2e7…`，正是 `gold.patch` L2 的前像 `f8cb99e2b2`。
  - gold 的上下文对应 `frame.py` L8325–8335。
- **隐藏测试与 base 的差别**：用 `diff` 对比 base 的 `pandas/tests/frame/test_analytics.py`，只有两处改动：
  - L899 的期望文案由旧改新；
  - 新增 L902–908 的 `test_mean_extensionarray_numeric_only_true`。

  其余逐行相同，所以 90 个非目标键都是同文件的旧测试。
- **初态改动**：见 `worktree_manifest.json` 的 `initial_diff`，日志 L1–7 的 git status 相同。
  - 只涉及 `pandas/__init__.py`、`_version.py`、`versioneer.py`、`setup.cfg`，并删除了 `pyproject.toml`。
  - `setup.cfg` 只剩 `[versioneer]`，没有 `[tool:pytest]`，所以评分时 pytest 没有 ini 配置（日志头只有 `rootdir: /testbed`）。
  - 这些改动与本题无关。
- **初态 bug 路径**：base 源码与 noop 日志 L112–189 互相印证。
  1. `DataFrame._reduce`（`frame.py` L8264）在 `numeric_only is not None` 时走块归约（L8317–8345）。
  2. `blk_func` 对 1 维非 ndarray 调 `op(values, axis=0, …)`（L8328–8330）。
  3. 进入 `nanops.nanmean`，L554 执行 `values.sum(axis, dtype=dtype_sum)`。
  4. `IntegerArray.sum`（`integer.py` L577–578）把位置参数 `axis` 当成 `skipna`，`dtype` 落进 `kwargs`。
  5. `nv.validate_sum` 拒绝 `dtype`，抛出题面所说的报错。
- **independent_reference**：M3 独立 runner 用来源镜像、来源版材料跑了两次，都是 79 passed / 1 skipped / 13 errors，与 superseded 行一致。当前材料版本没有独立 runner 对照，环境卡 §1 已说明这一点。

## 2. 目标键与需求—断言映射

目标键取自 current 运行：

- noop 两次都是 90/92，`mismatched` 就是这两个键（`B5/ledger_b5_noop.jsonl` L5/L6）。
- gold 两次都是 92/92（`B5/ledger_b5_gold.jsonl` L5/L6）。
- 期望映射的 92 个键全是 PASSED，其余 90 个是回归键，没有死键。

| 需求或旧行为 | 公开依据 | 测试 / 决定性断言 | 覆盖 | 执行证据 / 待做 |
| --- | --- | --- | --- | --- |
| R1：有 EA 列、`numeric_only=True` 时，`mean` 正常返回各列均值 | `user_prompt.txt` L4、L20–25 | `test_mean_extensionarray_numeric_only_true`（L902–908）：5 列 `Int64`、无 NA，`assert_series_equal(df.mean(numeric_only=True), DataFrame(arr).mean())` | 覆盖（限全 EA、无 NA、`axis=0`、只测 `mean`） | noop 失败原因与题面 L27–28 相同（noop 日志 L187）；gold 两次通过 |
| R1′：题面原例，numpy int 列与 `Int64` 列混合 | L14–21 | 无直接断言 | 缺失 | gold 经 `managers.py` L340–343 的标量结果分支应能处理（静态推断） |
| R2：题面说的"reduction operations (e.g., mean)"，即其它归约 | L7 | 无 | 缺失 | base 的 `nansum`（`nanops.py` L505）也调用 `values.sum(axis, dtype=…)`，应同样失败（静态推断） |
| H1：`numeric_only=False` 且含 Period 列时，TypeError 文案须匹配 `mean is not implemented for Period` | **题面无依据**；公开旧测试 L899 要求旧文案 | `test_mean_datetimelike_numeric_only_false` L896–900 | **冲突** | noop 只在 L900 失败，原因是 regex 不匹配（noop 日志 L107–109）；gold 两次通过 |
| 旧行为：`numeric_only=False` 时 datetime64/timedelta64 列可以求均值 | 公开同名测试 L882–894 | 同一测试 L892–894 | 覆盖 | noop 与 gold 都通过这一段（noop 的失败点在 L900） |
| 旧行为：`numeric_only=True` 排除 datetime/Period 列；默认 `mean` 发出 FutureWarning | 公开 `test_mean_datetimelike` L860–880 | 隐藏测试里的同名测试 | 覆盖 | noop、gold 均通过 |
| 旧行为：同一块归约路径上，numpy/object 块的 `numeric_only`、`bool_only` | 公开同文件 | `test_stat_op_api`、`test_numeric_only_flag[*]`、`test_mean_corner`、`test_any_all[*]`、`test_any_all_extra`、`test_any_all_bool_only` | 覆盖（都不含 EA 列） | 通过 |
| 旧行为：其它 EA 类型（Categorical、string、datetimetz、boolean、sparse）走同一路径 | — | 无 | 缺失 | gold 改变了这些类型的行为或报错（静态推断，见 §5 第 5 项） |

**H1 的来源：**

- **base 下**：Period 块走到 `nanmean`，被它上面的 `@disallow(PeriodDtype)` 拦下（`nanops.py` L511，文案在 L66–68）。
- **gold 下**：Period 块改走 `PeriodArray._reduce`，也就是继承自 `DatetimeLikeArrayMixin` 的 `_reduce`（`datetimelike.py` L1555–1560）；它再调 `mean`，在 L1639–1644 抛出 "mean is not implemented for PeriodArray since the meaning is ambiguous…"。
- **上游依据**：`Series._reduce` 本来就把 EA 分派给 `_reduce`（`series.py` L4003–4005），所以新文案与 `pd.Series(period).mean()` 的报错一致。

H1 是有上游依据的新行为，只是本题题面没有交代。反过来，`frame.py:8330` 的报错位置和 `Series._reduce` 的写法都会引导解题者走 gold 路线，所以题目不是不可解，而是多出了一条题面没说的要求。

## 3. 误拒与漏测：候选实现对照（静态推断，未执行）

| 候选实现 | 满足题面？ | 预计隐藏得分 | 理由 |
| --- | --- | --- | --- |
| A（gold）：`blk_func` 对 `ExtensionArray` 调 `values._reduce(name, skipna=…, **kwds)` | 是 | 1（有运行证据） | — |
| B：复用 Series，`Series(values)._reduce(...)` 或 `getattr(Series(values), name)(...)` | 是 | 1 | Series 同样分派到 `_reduce` |
| C：只对数值 EA（或排除 Period）走 `_reduce`，其余不变，以保住公开旧测试 | 是（R1、R1′、R2 都修复） | **0** | Period 仍走 `nanmean`，报旧文案 |
| D：在 nanops 层把掩码 EA 转成 float ndarray，或让 `IntegerArray.sum` 接受 `dtype`/`axis` | R1 是；R2 取决于实现 | **0** | `@disallow(PeriodDtype)` 在函数体之前就抛旧文案 |
| E：只在 `name == "mean"` 时分派 `_reduce` | 否（sum 等仍坏） | 1 | 漏测；这种写法不自然，风险低 |

结论：H1 实际上把"用 `_reduce` 分派"这条实现路线变成了评分条件。更要紧的是公开材料把谨慎的解题者往相反方向推：

- 按 gold 修复后，公开 `test_analytics.py` 里的 `test_mean_datetimelike_numeric_only_false` 会失败（静态推断，高置信）。
- `public_hints`（`public_bundle.json` L15）又写着 "Do NOT modify test files"。

两者叠加会把谨慎的解题者推向 C，奖励因此惩罚"保护已有测试"的行为。这会带来两个问题：

- **训练**：奖励信号不利。
- **诊断**：0 分可能只反映 H1，不代表题面问题没修好。

解题者实际有多少会走 C 或 D，静态阅读无法判断。

## 4. R2E 专项

- **(a) 非 PASSED 期望键**：没有。
  - 92 个键全为 PASSED。`test_kurt` 因缺 SciPy 被 SKIPPED，不成键（noop 日志 L282；`test_1.py` L564）。
  - 因此不存在"更完整的修复把 FAILED 键翻成 PASSED 而被判 0"的风险。
  - 正确修复不会改变收集结果。唯一能改变键集合的途径是让 SciPy 可导入，镜像无出网，不现实。
- **(b) 题面报错是否出现在 noop 目标键**：
  - EA 键：是，逐字出现（noop 日志 L187）。
  - Period 键：不是。它的失败是 regex 不匹配（L107–109），题面没涉及。
  - 两份 superseded noop 日志（R-f、环境轮复跑）在 L217/L295 有同样原因，修订前后目标键不变。
- **(c) 题面是否泄漏修法**：不泄漏。题面只给症状和报错；报错指向 `nanmean → EA.sum` 这条调用链，属于诊断线索，不是修法。
- **(d) 测试支撑与撞键**：
  - 隐藏测试只导入库模块：`pandas._testing`、`pandas.util._test_decorators`、`pandas.core.algorithms`、`pandas.core.nanops`，不导入 `pandas/tests/` 下的辅助模块。
  - 只有一个测试文件；两次日志各解析出 92 个唯一键，没有撞键。
  - `pandas/_testing.py` 是库内的测试辅助，候选可以改，评分时也不会重置。这是 R2E 的通用风险，不是本题特有。
- **(e) 时间、随机、资源**：
  - fixture（`tm.getSeriesData`）和若干测试用了无种子随机数，但断言都与同一份数据的替代计算比较。
  - 目标键的均值是整数和除以 10，在 float64 下精确。
  - 四次 current 运行结果一致。pytest 自报 0.36–0.64 s，ledger 的 `test.seconds` 为 1.58–1.87 s，内存峰值约 727 MB（`resource.mem_peak_mb`）。
  - 没有发现对时间或资源敏感的键。
- **(f) 修订是否只恢复支撑**：是。
  - **r2e-mr-016**：
    - `conftest.py` 里的 7 个 fixture，与 `PUB/worktree/pandas/conftest.py`、`pandas/tests/frame/conftest.py` 的原定义逐字相同（按 AST 逐函数比对）。
    - 每个 fixture 在 conftest 链上只定义一次，不涉及"最内层优先"的取舍。
    - 未带入 autouse 的 `configure_tests`（`pandas/conftest.py` L130–135，把 `chained_assignment` 设为 `"raise"`），也未带入 `add_imports` 和两个 hook（L47、L62）。
    - 隐藏测试不用 slow/network/db 标记，hook 缺席没有影响。
    - 缺了 `configure_tests`，chained assignment 从 raise 变成 warn，比上游略宽，影响可以忽略。
  - **r2e-mr-017**：
    - 翻转的 13 个键，修订前都是 `fixture '…' not found`（R-f gold 日志 L31–133）。
    - 修订后 noop 和 gold 都是 PASSED，所以它们是回归键，目标键没变。
    - `test_1.py` 未改（哈希一致）。
    - 这次修订把 13 个死键恢复成上游原有的回归检查，没有扩大题面需求。

## 5. 八方面覆盖（已查 / 未查）

1. **公开需求**
   - 已查：`user_prompt.txt`、`public_bundle.json`（含 `public_hints`）、`environment_brief.md`、公开旧测试 L860–900，以及相关 base 源码。
   - 结论：R1 明确；R2 的泛化只有一句；H1 没有公开依据，且与公开旧测试冲突。
   - 未查：正式 actor 实际渲染的系统提示。环境卡 §2 说 conda 措辞待改，记为 actor 待验。
2. **材料与初始问题**：见 §1。base、gold 前像、隐藏测试、初态改动都已核对；初态失败有两次 current 执行证据。
3. **测试是否测到要求**：见 §2 表。
   - R1 部分覆盖，R1′、R2 缺失，H1 冲突。
   - 90 个回归键没有逐条写评语，只核了与块归约路径、`numeric_only`/`bool_only` 相关的 9 个测试函数。
4. **误拒**：见 §3。有具体疑点（C、D），需要 CPU 反例。
5. **回归与 gold 完整性**
   - gold 只改 `frame.py` 的 4 行，与 `Series._reduce` 的分派一致，没有无关改动。
   - gold 让所有 EA 类型在块归约路径上都改走 `_reduce`，因此也改变了 string 列（`string_.py` L284–288 只支持 min/max）、Categorical 列等的行为或报错。
   - 隐藏测试只覆盖其中 Period 的 mean 文案。这与 Series 语义一致，不算 gold 错误，属于未测的行为变化。
   - 未查：上游提交除 gold 外有没有 whatsnew 等文档改动（与评分无关）。
6. **开发条件**
   - 环境：解释器是 `/testbed/.venv/bin/python`（3.7.9）；pip 有，但无出网（brief L10–12）。
   - 修复是纯 Python，不需要重编扩展；缺 SciPy 只影响 `test_kurt` 和 skew/kurt 分支。
   - 最小验证：`python -m pytest pandas/tests/frame/test_analytics.py -k "mean"`，再加题面原例脚本。注意正确修复会让公开旧测试失败（§3）。
   - 评分侧的 4 次运行只能证明评分条件。
   - 正式 actor 链目前用的是来源镜像：`/r2e_tests` 可读，main 上有修复提交（环境卡 §2）。进入正式 actor 前必须先改，这一项记为 actor 待验。
7. **交付与评分边界**
   - gold 的投影只含 `pandas/core/frame.py`（gold ledger 的 `projection.included_paths`）。
   - R2E 只重放 `r2e_tests/` 和 `run_tests.sh`。候选对 `pandas/_testing.py` 或仓库根 conftest 的改动会保留下来，并影响评分。
   - 这是通用机制问题，本题没有特例，这里没有重做平台审计。
8. **题目关系与用途**
   - 本题是 T0-6 第二步一并修订的 7 道 pandas 题之一（`revisions.json` 的 `decision_ref`）。它与其它题有无派生或重复关系，未查。
   - 题面不给修法。上游修复是公开的，预训练是否见过无法静态判断。
   - 本复核者已看过 gold、隐藏测试和运行日志。

## 6. 暂定处置与最小实验

**暂定处置**：`needs_review`，理由是题意/测试争议。

- R1 部分可以作为开发诊断信号。
- 如果在修订前使用本题，应逐键读结果：只在 H1 上失败的候选，不能算"没修好题面问题"。

**唯一最值得先做的下一步**：在派生镜像里按评分顺序做 CPU 实验。

1. 在 gold 下，跑公开位置的旧测试 `pandas/tests/frame/test_analytics.py::TestDataFrameAnalytics::test_mean_datetimelike_numeric_only_false`。预期失败，用来坐实公开测试与隐藏测试的冲突。
2. 把候选 C 送进 RH2 评分。C 的写法：在 `blk_func` 里，只有当 `isinstance(values, ExtensionArray) and not is_period_dtype(values.dtype)` 时才走 `values._reduce`。预期 R1 和题面原例都修好，但 reward=0，只错 H1 一个键。
3. 可选：把候选 E（只对 `mean` 分派）送进评分。预期 reward=1，用来确认漏测。

**若 1、2 结果如预期，可选的修订方向（需用户决定）：**

- **较小改动（推荐）**：把隐藏测试 L899 放宽为 `pytest.raises(TypeError)`，不再匹配文案。
  - 它仍然检查"Period 求均值被拒绝"这一旧行为，同时接受新旧两种文案。
  - 放宽后 H1 在 noop 下也会 PASSED，变成回归键。期望映射不用改，题目只剩一个目标键。
- **在题面里加入 Period 文案要求**：这等于把测试细节搬进题面，不推荐。
- **保持原样**：在用途上注明"要求 `_reduce` 分派路线"。
- **另外**：可以补一条题面原例（混合列）或 `sum` 的断言，来弥补漏测。这属于新增断言，需要同时用替代解和错误解验证。

## 附录 A：实际读取范围

**读了：**

- **方法文档**：
  - 复核卡全文。
  - 主审卡：工具一次载入了全文（33 行）。按要求，只把"R2E 的评分口径"和"材料"两节当作口径依据，其余段落没有作为本稿依据。
  - 八方面协议、R2E 环境卡、记录模板。
- **公开包**：`user_prompt.txt`、`environment_brief.md`、`public_bundle.json`；`worktree_manifest.json` 只看了 `export`、`initial_diff`、untracked 字段和 4 个文件条目。
- **工作树（只读片段）**：
  - `pandas/tests/frame/test_analytics.py`：与隐藏测试整体 diff，精读 L860–900。
  - `pandas/core/frame.py` L8255–8404。
  - `pandas/core/nanops.py`：L40–80、`nanmean` 全文、各装饰器所在行。
  - `pandas/core/arrays/integer.py` L550–600。
  - `pandas/core/arrays/datetimelike.py` L1550–1660。
  - `pandas/core/series.py` L3989–4040。
  - `pandas/core/internals/managers.py` L325–355。
  - `pandas/core/arrays/string_.py` L280–296。
  - `pandas/core/arrays/period.py`：只看类定义行。
  - `pandas/conftest.py`、`pandas/tests/frame/conftest.py`：逐函数比对 fixture，并看 autouse/hook 所在行。
  - `setup.cfg`：只看节名。
- **私有包**：全部文件，包括 `hidden_tests/test_1.py` 与 `conftest.py` 全文、`expected_output.json`、`gold.patch`、`run_tests.sh`、`grading_bundle.json`、`validation_bundle.json`、`revisions.json`、`run_refs.json`。
- **运行原件**：
  - current：`B5/ledger_b5_noop.jsonl` L5/L6、`B5/ledger_b5_gold.jsonl` L5/L6 全文；对应的 4 份 `.eval.log` 读了全文或 summary，并逐份核哈希、解析键。
  - superseded：`runs/r2e_rf_20260923/remote/eval_logs_r2e/` 与 `runs/r2e_env_repair_20260924/_rerun2/eval_logs/` 下的 noop/gold 日志，只解析了 summary 和失败原因行。这些都是 `run_refs.json` 指向的原始日志，没有打开这两个目录里的其它文件。
  - independent_reference：M3 的两份 `test_output.txt`，只看了结果行和 fixture 报错计数。

**没读：**

- `OUTPUT_DIR/public_read.md` 及其它产物。
- `history/`。
- `docs/.../r2e_env_repair_20260924/`，包括 `revisions.json` 的 evidence 引用的 `material_revisions/*.md`。
- 任何 review 目录，以及 `r2e_static_review_20260925/README.md`。
- `runs/r2e_t0_batch3_20260924/` 下的 `analysis_b3.json`、`dryrun_b3r2/`、`conftest_sources/`。
- 日志旁的 `*.diagnostics.json`；superseded 行对应的 ledger 行；M3 facts 的 `initial.diff`。
- 40 项清单；其它题的材料。
- 没有联网核对上游提交。
