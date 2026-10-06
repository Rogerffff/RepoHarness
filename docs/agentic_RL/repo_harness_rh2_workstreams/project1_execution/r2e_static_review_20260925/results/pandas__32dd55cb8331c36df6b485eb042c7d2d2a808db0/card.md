# pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0（R2E）静态审查短卡

> **2026-09-25 协调者更正（按 Codex 复核 r2e_static_actor_review_20260925/README.md）**：第 60 行附近"T1 通过、只有 T2 失败的解单独归类、不计为能力失败"改为：这种失败模式只标疑似规格争议，失败键模式只用来筛出'疑似规格争议'的待复核样本：保留原始 reward，逐一核对候选是否满足公开要求、是否破坏受影响的旧行为，核实后才标'合理误拒'，不能按失败位置自动免除能力失败。 反例：只对 mean 分派的半修 T1 过、T2 败，但题面同属数值归约的 sum 仍然坏（静态）。C1 的具体分析保留（真实评分 91/92），不推广到所有 T1 过 / T2 败的补丁。修订草案的新断言应覆盖非 mean 归约，不只含缺失值的 mean。 以下原文保留不改。

主审 2026-09-25，已读历史。完整证据见同目录 `analysis_before_history.md`（附录 A）与 `old_findings_delta.md`。

## 1. 目标、版本与用途

- **问题所在。**base `b7f061c3` 处于 pandas 1.1 开发期。`DataFrame._reduce` 在 `numeric_only` 不为 None 时，把 EA 块交给 nanops 处理，于是含 Int64 列的 `df.mean(numeric_only=True)` 会报 `ValueError: the 'dtype' parameter is not supported in the pandas implementation of sum()`。
- **gold 的改法。**只改 `pandas/core/frame.py` 的 `blk_func`：EA 块一律改调 `values._reduce(...)`。
- **当前材料。**来源材料加修订 r2e-mr-016/017：私有 conftest 补 fixture，13 键从 ERROR 改为 PASSED。
- **期望。**92 键全部 PASSED。目标键有两个：
  - T1 = `test_mean_extensionarray_numeric_only_true`；
  - T2 = `test_mean_datetimelike_numeric_only_false`。
- **建议用途。**`development_diagnostic`（须带第 4 节的标注）。修订并复验之前，不作训练 reward 题。

## 2. 关键映射

| 需求或旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖 | 执行证据或下一步验证 |
|---|---|---|---|---|
| 含 Int64 列时 `mean(numeric_only=True)` 可用，结果包含 EA 列，且与逐列均值一致 | 题面示例与 Expected | T1：全 Int64 帧的均值等于 int64 帧的均值（float64） | 部分：无缺失值，只测 mean，不是混合帧 | noop 报出题面原错（b5 noop 日志 L187）；gold 两次 PASSED |
| Period 列 `mean(numeric_only=False)` 抛 TypeError，文字为 `reduction operation 'mean' not allowed` | 公开 `test_analytics.py:899`；该用例在 base 上通过（fixture_check `PT_RC=0`） | T2 要求的是 `mean is not implemented for Period`（`H/test_1.py:899`） | **冲突** | noop 保持旧文字，因此被判 FAILED（L105-109）。下一步：在 CPU 上跑 C1 |
| 其它归约（sum/min/max…）与缺失值 | 题面写 "reduction operations (e.g., mean)"；Series 语义 | 无 | 缺失 | 静态推断：只对 mean 分派的半修 C3 能得 1 |
| ndarray 块的归约结果与报错文字不变 | 公开测试中 90 个同文用例 | 90 个回归键（其中 13 个经修订恢复） | 覆盖 | noop 与 gold 都 PASSED |

## 3. 八方面：已查与未查

- **公开需求：**已查，发现 T2 冲突，以及其它归约（R4）、缺失值（R5）两个缺口。未查：实际渲染出的消息。
- **材料与初态：**已查。base 是修复提交的父提交；noop 在题面路径上报出原错（当前运行证据，加上 agent 身份的复现）。
- **测试是否测到要求：**已查，92 键全读。T1 只覆盖部分要求；T2 测的是 gold 的副作用。
- **是否误拒合理解：**是，原因是 T2。有静态推断和 noop 执行结果支撑，候选层面尚未实跑。
- **回归与 gold 完整性：**已查。
  - ndarray 分支的回归覆盖充分；
  - gold 没有修默认 `numeric_only=None` 路径，但题面不要求；
  - Int64 均值被截断的继承问题未测，不影响判分；
  - 未查：`tests/extension`、`tests/arrays` 在 gold 下的状态。
- **开发条件：**以 agent/54321 身份在镜像层面实测过：
  - 解释器是 `.venv` 下的 Python 3.7.9，pytest 7.4.4；
  - 有 pip，但没有网络；
  - bottleneck 未启用；
  - 公开测试可以运行。

  正式启动链尚未验证。
- **交付与评分边界：**
  - 只需改 `.py`；
  - expected 绑定"无 SciPy"；
  - 根目录 conftest、`setup.cfg`、`pandas/_testing.py` 这几条改动通道按共享审查处理。
- **关系与用途：**与其它 pandas 题的关系未查；题面不泄漏修法。

## 4. 具体问题与证据级别

1. **T2 误拒合理解（高）。**只有让 Period 列走 `PeriodArray.mean` 的实现能过 T2。
   - 以下几种写法都能解决题面，也能让公开测试全部通过：
     - C1：只对数值 EA 调 `_reduce`；
     - C2：只在 `numeric_only=True` 时分派；
     - 在 nanops 层支持掩码；
     - 窄修 `IntegerArray.sum`。
   - 但它们在 T2 上执行的是与 noop 相同的代码，所以整题得 0。
   - `public_hints` 里"不要改测试文件"一句，更会把解题者推向保留旧文字。
   - 证据级别：静态推断、noop 执行结果、公开测试在 base 上通过；还没有候选实跑。

   **诊断用法的标注：**遇到"T1 通过、只有 T2 失败"的解，要单独归类，不计为能力失败。
2. **漏测（中）。**T1 没有缺失值，也只测 mean。
   - 静态推断：C3（只对 mean 分派）能得 1。
   - 窄修 `IntegerArray.sum` 现在得 0，只是被 T2 顺带挡住了。
3. **正式 actor 镜像泄漏（共享问题，高，已排期）。**正式链目前用的是来源镜像：`/r2e_tests` 可读，修复提交也可达。派生镜像已核对，是干净的（derived7 facts）。
4. **提示与镜像不符（共享问题 E09，低）。**提示里的 conda 说法，以及"评分会重置测试文件"的说法，对 R2E 都不准确。
5. **环境修复的覆盖范围。**r2e-mr-016/017 已核对通过：fixture 逐字摘自 base，死键恢复，没有弱化断言，也没有扩大需求。但这两项修订不涉及 T2。

## 5. 建议与下一步

- **静态建议：**`needs_review`，理由是题意与测试有争议。
- **修订草案（须经用户或独立审查决定）：**
  - 让 T2 的 `match` 同时接受两条文字（公开先例：`tests/reductions/test_reductions.py:350-358`）；
  - 同时补一条含 `pd.NA` 的 Int64 均值断言，堵住窄修；
  - 每条新断言都要双向复验：gold、C1、C2 应通过，C3、C4 应不通过。
- **与历史的分歧：**环境阶段把 T2 问题当成已解决：R16 改为 pass，issues[1] 标为 verified，而且 resolution 是从 fixture 问题复制过来的，因此本题显示"无未完成项"。本次核对确认，这个问题仍然存在，而且比历史描述的更具体。
- **独立复核：**待做。
- **唯一优先的下一步：**在当前派生镜像里，按评分顺序跑 C1，即只在 `isinstance(values, ExtensionArray) and is_numeric_dtype(values.dtype)` 时调用 `_reduce`。预期结果：
  - 题面示例正确；
  - 公开 `test_analytics.py` 全部通过；
  - 隐藏测试 91/92，reward 为 0。
