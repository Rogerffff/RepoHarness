# numpy a5ea773e：`tile` 在重复因子全为 1 时不复制（静态审查短卡）

主审是 Claude（R2E 第二批，2026-09-25）。前稿见 `analysis_before_history.md`，历史核对见 `old_findings_delta.md`。独立复核尚未进行。

## 1. 目标、版本与用途

- **目标**：`np.tile(A, reps)` 在所有重复因子为 1 时，要返回独立副本。
  - 题面原例：`b = np.tile(np.arange(5), 1)`，执行 `b += 2` 之后，`a` 应仍为 `[0 1 2 3 4]`。
- **版本**：
  - numpy 1.10.0.dev0，提交 `d770034`；Python 3.7.9。
  - 派生配方 `r2e_derive_v1`；当前覆盖表镜像 `4bd9cf42…`。
  - 没有材料修订。
  - 修复点在 `numpy/lib/shape_base.py:853`，纯 Python 代码。
- **建议用途**：作为 development_diagnostic 的静态探针候选。reward=1 只能说明题面原例修好了，不能说明修复完整。

## 2. 关键映射

| 需求或旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖 | 执行证据或下一验证 |
|---|---|---|---|---|
| 题面原例：1-D 数组，`reps=1` | `user_prompt.txt:10-21` | `TestTile.test_tile_one_repetition_on_array_gh4679`：`b += 2` 后 `assert_equal(a, np.arange(5))` | 覆盖 | noop FAILED，日志中 `x: array([2, 3, 4, 5, 6])`；gold PASSED。两次构建上 noop、gold 各 3 次，结果一致 |
| 其它全 1 形式：`(1,)`、`[1]`、2-D 数组配 `1` | 题面 "in all dimensions" | 无 | 缺失 | devcheck 实测：base 下全部共享内存，gold 下全部不共享。见候选 B |
| 全 1 且需要升维：`(1,1)` 应得 (1,5)，0-d 应得 (1,) | docstring `:796-803` | 无 | 缺失 | 见候选 C |
| 非全 1 路径的值和形状不变 | docstring、公开测试 | `test_basic` / `test_empty` / `test_kroncompare` | 覆盖（回归） | noop、gold 下都是 PASSED |
| 其余 28 键（split、stack、kron 等） | 仓库已有测试 | 同文件回归 | 与本题无关：base 里没有非测试代码调用 `tile` | 全部 PASSED |

## 3. 八方面：已查与未查

| 方面 | 已查 | 未查 / 缺口 |
|---|---|---|
| 公开需求 | 已查 | 真实任务消息没有捕获；按代码，公开提示不进入模型消息 |
| 材料与初态 | 已查：哈希一致；隐藏测试 = 公开测试 + 1 个新测试；noop 的失败值与题面一致 | — |
| 测试是否测到 | 32 键全部读过 | 目标断言测的性质正确，但只用了一个输入 |
| 误拒 | 未发现，期望全是 PASSED | 候选 A 待实跑确认 |
| 回归与 gold | gold 正确，只有一个 hunk | 全 1 分支的旧行为（升维、0-d、子类）没有任何键保护 |
| 开发条件 | 实测：正式启动路径 + 真实 Claude Code + 桩模型 | 真实模型求解未验 |
| 交付与评分 | 实测：gold 投影、评分顺序、git 清理 | 共享控制面（`numpy/testing/`、根目录 `conftest.py`）未逐题验证 |
| 题目关系 | 已查同仓 6 题的公开工作树 | 其它来源的重复未查 |

## 4. 问题、影响与证据层次

1. **覆盖窄**（清单 25、26；静态推断，待实跑）：部分修复也可能得 1。用于诊断时要读补丁，不能凭 reward 断言修复完整。
2. **跨题关系**（清单 5；文件比对实证）：
   - 同仓 6 道较新 numpy 题的公开工作树里，都有本题修复的重构版本（注释逐字相同）和目标测试。
   - 逐字代码比对之所以漏报，是因为上游后来改写了修复代码，只命中 1/3 行。
   - 做留出评测划分时要登记这一关系。
   - 修好的代码就是现代 numpy 的 `tile` 原文，模型从记忆里就能取到答案。
3. **公开提示不进模型消息**（清单 3；代码证据；链路级问题）：模型默认不知道要用 `python -m pytest`，也不知道环境没有 pip。对本题影响小。
4. **解题侧条件**（历史 + devcheck 实证）：
   - `/testbed` 必须在 `sys.path` 上；脚本放在 `/testbed` 之外时，要设 `PYTHONPATH=/testbed`。
   - 裸 `pytest` 收集会失败（18b7 实测，本题是推断）。
   - 没有 pip。
   - 公开测试里只有无关模块 `test_ctypeslib.py` 有 1 个 ERROR。

**环境侧**：本题没有环境配方，也没有材料修订。当前构建 `4bd9cf42` 上已实测 noop=0、gold=1，历史给的 `environment_qualified` 在新构建上依然成立。

## 5. 建议与下一步

- **静态建议**：`needs_review`（静态候选，待 actor 验证）。不修订材料，不改评分测试。
- **读历史后未改判**。有两处更新：关闭了"当前构建没有评分记录"这个未知项；补充了一条关于脚本位置的解题侧条件。
- **独立复核**：待进行。
- **唯一优先的下一步**：用正式评分代码实跑候选 A、B；C、D 可以放在同一批里一起跑。

**候选**：都只改 `numpy/lib/shape_base.py` 的 `tile`。下文 T 指 `TestTile.test_tile_one_repetition_on_array_gh4679`。

| 候选 | 优先级 | 改法 | 行为后果 | 预期 |
|---|---|---|---|---|
| A 合理替代解 | 必跑 | 把第 853 行 `c = _nx.array(A, copy=False, subok=True, ndmin=d)` 中的 `copy=False` 改成 `copy=True`，即无条件复制 | 正确修复 | reward 1，32/32，没有不符键 |
| B 部分修复 | 必跑 | 在函数体第一行（`try:` 之前）插入 `if isinstance(reps, int) and reps == 1: return _nx.array(A, copy=True, subok=True)` | `tile(a, (1,))` 和 `tile(a, [1])` 仍共享内存；`tile(np.array(7), 1).shape` 变成 `()` | reward 1（误放行），没有不符键 |
| C 回归型错误 | 建议 | 在 `d = len(tup)` 之后插入 `if all(x == 1 for x in tup) and isinstance(A, _nx.ndarray): return A.copy()` | `tile(np.arange(5), (1, 1)).shape` 变成 `(5,)`，应为 `(1, 5)` | reward 1（误放行），没有不符键 |
| D 负对照 | 可选 | 把末行 `return c.reshape(shape)` 改成 `r = c.reshape(shape)`，再 `return r.copy() if r is A else r` | `reshape` 总是返回新的视图对象，`r is A` 永远不成立，所以仍然共享内存 | reward 0，唯一不符键是 T |
