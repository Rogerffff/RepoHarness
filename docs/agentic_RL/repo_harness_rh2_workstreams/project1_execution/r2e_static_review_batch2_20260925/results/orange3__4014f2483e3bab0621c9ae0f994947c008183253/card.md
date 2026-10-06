# orange3__4014f248 短卡（静态审查，主审）

**题目**：对只差 1 ulp 的几个值做 `EqualFreq` 离散化时，相邻中点经舍入后相撞，得到重复切点；随后建区间时，`_fmt_interval` 的 `low < high` 断言（`Orange/preprocess/discretize.py:53`）失败。题面要求切点唯一。

- 版本：base 9403704f，来源修复 4014f248。
- gold：1 行 `points = list(np.unique(points))`，外加 1 行注释。
- 材料修订：无。
- 建议用途：开发诊断（`development_diagnostic`）。目前是静态候选，还没有经过 actor 验证。

**关键映射**

| 需求或旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖 | 执行证据或下一验证 |
| --- | --- | --- | --- | --- |
| 题面原例不抛错，切点唯一 | 题面 Example、Expected | `TestEqualFreq.test_below_precision` 第一段：4 个值、n=4，断言 `len(np.unique(points)) == len(points)` | 覆盖 | noop 两次都 FAILED，位置 `:53`，`low = high = 1+2ε`；gold 两次 PASSED；M3 两次 PASSED |
| 一般情形：不同值多于 n（走循环分支） | Expected 的一般表述 | 同一测试第二段：10 个值、n=8 | 覆盖（示例之外） | 算术转写显示 base 在循环分支也产生重复点；C4 可选 |
| `points` 仍是升序 list，正常数据的结果不变 | 公开 `Orange/tests/test_discretize.py` | 26 个回归键，逐值比较 `[24.5, 49.5, 74.5]` 等 | 覆盖 | base 与 gold 下都 PASSED；以 agent 身份跑公开同名文件，26 passed |
| 小量级数据的切分分辨率 | 合理旧行为，题面没约定 | 无 | 缺失 | C3 |
| 改 `.pyx` 的根因修复能够交付 | hints 写 "edit NON-TEST source files" | 目标键 | 冲突（发生在交付层） | C2 |

**八方面**

- 已查：公开需求、材料与初态、测试映射、回归与 gold、开发条件、交付边界、题目关系。
- 未查：
  - 模型实际收到的消息（devcheck 发的是固定提示）；
  - 真实模型求解；
  - C1–C4 实跑；
  - 改 `.pyx` 后重编译的耗时；
  - SQL 分支，以及 owmosaic、owsieve 等调用方；
  - R2E 全集里的其它 orange3 题。

**问题与证据层次**

1. **I1（中）只改 `.pyx` 的正确修复预计得 0。** 导出按 `.gitignore` 排除 `*.so`；评分时 `RH2_INSTALL_SKIPPED=1`，用的仍是镜像预编译的 `.so`。本地工具链（Cython 0.29.37、gcc）齐全，解题者自己重编译后，本地看起来已经修好。证据是代码配置加日志事实，还没有实跑。这是带编译扩展的 R2E 仓库共有的机制，本题的根因正好在 `.pyx`，所以相关性高。
2. **I2（低到中）目标键不检查点数。** 按容差合并切点的实现能拿满分，但会让小量级数据的切分变粗。证据：静态推断加算术转写。
3. **I3 同族暴露（已核实）。** 本题 gold（连注释）和目标测试逐字出现在 22e98f8f、50f6a758、c3fb72ba、f5026689 的公开初态中。
4. **I4 公开测试噪声（实测）。** `test_owdiscretize.py::TestOWDiscretize::test_minimum_size` 在 base 和 gold 下都失败，与本题无关。
5. **I5 题面措辞不准。** "below floating point precision" 不准确：塌缩发生在中点舍入，不是输入本身无法区分。
6. **I6 共有的评分控制面问题。** 隐藏测试导入候选可改的测试辅助模块，本题没有具体证据。
7. **环境修复覆盖情况。** 本题没有配方，也没有修订。09-24 的环境资格与 09-25 的 devcheck 覆盖了 gold、noop 与开发条件，不覆盖 I1。

**待实跑候选**（协调者用正式评分代码运行）

- **C2（优先）**：改 `Orange/preprocess/_discretize.pyx` 的 `split_eq_freq`，把第 17 行改成 `return sorted(set([(v1+v2)/2 for v1,v2 in zip(dist[0], dist[0][1:])]))`，把第 57 行改成 `return sorted(set(points))`，不改任何 `.py` 文件。预期 reward 0，唯一不符的键是 `TestEqualFreq.test_below_precision`（FAILED，与 noop 相同）。
- **C3**：在 `Orange/preprocess/discretize.py` 的 `EqualFreq.__call__` 非 SQL 分支，`points = _discretize.split_eq_freq(d, self.n)` 之后加 `points = sorted(set(round(float(p), 10) for p in points))`。预期 reward 1（27/27，没有不符的键）。但对 `np.arange(100).reshape(-1, 1) * 1e-12`，切点会从 `[2.45e-11, 4.95e-11, 7.45e-11]` 变成 `[0.0, 1e-10]`。
- **C1**：在 `Orange/preprocess/discretize.py` 的 `Discretizer.create_discretized_var` 里，`lpoints = list(points)` 之前加 `points = sorted(set(points))`，不改 EqualFreq。预期 reward 1（27/27，没有不符的键）。
- **C4（可选）**：在 `Orange/preprocess/discretize.py` 的 `EqualFreq.__call__` 非 SQL 分支，只在 `self.n >= d.shape[1]` 时执行 `points = list(np.unique(points))`。预期 reward 0，唯一不符的键是 `TestEqualFreq.test_below_precision`（第二段仍会触发断言，FAILED）。

**建议**

- 处置为 `needs_review`：静态候选待 actor 验证，I1 待 C2 实跑。
- 不改题面，也不改隐藏测试。
- 如果 C2 确认 I1，由协调者或用户决定修在哪一层：在公开提示里说明"编译扩展不会在评分时重新编译"，或者让评分端重新编译改动过的 `.pyx`。两种都属于环境或提示层。
- 划分训练与评测时，本题要与 I3 的 4 题按同族处理。

**与历史的分歧**：09-24 环境记录说"环境无缺口""候选代码生效"，这只对 `.py` 改动成立。它用的公开测试证据是 `test__orange.py`（1 例），本轮换成 `test_discretize.py`（26 例）。独立复核尚未进行。

**唯一最值得先做的下一步**：实跑 C2。
