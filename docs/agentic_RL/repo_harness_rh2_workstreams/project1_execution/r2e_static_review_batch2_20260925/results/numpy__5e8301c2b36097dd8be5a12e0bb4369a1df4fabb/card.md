# numpy__5e8301c2 静态审查短卡（2026-09-25，私有主审）

## 1. 题目、版本与用途

- **目标**：`np.einsum('ti,ti->i', np.ones((10,2)), np.ones((1,2)), optimize=True)` 不再在 `einsum_path` 的标签尺寸检查处报 `ValueError`，结果与 `optimize=False` 相同（`[10., 10.]`）。
- **版本**：numpy 1.15.0.dev0，base `354ac25c`；材料 `expected_v0`，没有修订；配方默认 `r2e_derive_v1`。
- **gold**：只改 `numpy/core/einsumfunc.py` 的 6 行，接受"1 对 N"并记下非 1 的那个尺寸。
- **用途**：`development_diagnostic`；静态候选，待 actor 验证。

## 2. 关键需求—测试映射（完整表见 analysis §3）

| 需求或旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖 | 执行证据或下一验证 |
| --- | --- | --- | --- | --- |
| 题面示例不报错，结果为 `(2,)` 的 `[10,10]` | 题面 | 15 个 `TestEinSum.test_einsum_sums_*` → `check_einsum_sums` 末尾 `T:487-490` | 覆盖。但输入全 1，15 键检查的是同一处 | noop 两轮 15 FAILED，都是题面原句（`einsumfunc.py:712`）；gold 两轮 35/35；M3 两次 |
| 与顺序无关（`(1,2)` 在前） | 广播是对称的 | 无 | 缺失 | gold 实测能过（私有对照）；**C-C** |
| 被求和的单例标签走 `tensordot`，或多操作数 | 题面描述段是泛指 | 无 | 缺失，gold 也不满足 | 私有对照报 `shape-mismatch for sum`；**C-A** |
| 真正不兼容的尺寸仍报 `ValueError` | 旧行为 | `test_einsum_errors` 只测同一操作数内的 `'ii'` 配 `(2,3)` | 部分 | **C-D** |
| 旧测试（含精确收缩路径）继续通过 | 旧行为 | 20 个回归键 + helper 原有部分 | 覆盖 | 这 20 键在 noop 和 gold 下都是 PASSED |

## 3. 八方面：已查与未查

| 方面 | 结论 |
| --- | --- |
| 公开需求 | 示例明确，报错能从 base 逐行读出；泛化范围不定。**真实题面消息没捕获**（devcheck 用的是桩消息） |
| 材料与初态 | 各项摘要一致；noop 的失败就是题面原句 |
| 测试 | 只测题面示例，隐藏测试 = 公开测试 + 8 行 |
| 误拒 | 没有过严断言；期望全 PASSED，不存在"更完整的修复反被判 0"的风险 |
| 回归与 gold | 回归键够用；gold 只是部分修复，新报错文本把两个尺寸写反了 |
| 开发条件 | devcheck 以 agent 身份实测：导入、pytest 7.4.4、复现、公开测试 35 passed 都可用；没有 pip、没有网络，本题都不需要。放在 `/testbed` 外的脚本导入不了 numpy，提示里没写 |
| 交付 | 单个纯 Python 文件；评分不重编译，本题不受影响 |
| 题目关系 | 本题 gold 和隐藏断言出现在 `numpy__43e333e2`、`numpy__d89bc4bb` 的公开初态里 |

**未查**：真实模型求解、真实候选交付、并发；共享控制面（`numpy.testing` 可被候选改写、`.venv` 可写）。

## 4. 问题与证据层次

- **I1 覆盖窄**：静态推断，待实跑。
- **I2 gold 部分修复**：当前 CPU 执行证据（私有一次性容器，root 身份）。
- **I3 gold 报错文本尺寸写反**：执行证据；外观问题，没有测试覆盖。
- **I4 跨题包含**：已逐文件核对。影响留出集划分，不影响本题评分。
- **I5 真实题面消息未捕获。**
- **I6 解题侧条件**：`/testbed` 外的脚本导入失败，提示没告知；旧记录说"裸 pytest 会失败"，对本题的依据不成立（静态判断）。

环境轮的 `environment_qualified` 保留：本题没有环境修复，也不依赖任何修订。

## 5. 建议与下一步

- **静态建议**：保留为静态候选。reward 为 1 只能说明题面这一例修好了，不能理解为完整支持单例维广播。
- 可选的测试加强：在隐藏断言里加入对调顺序的一例，gold 已实测能过。不建议加 `tensordot` 或多操作数的断言：gold 过不了，这等于扩大需求，要先由用户定范围。
- 独立复核还没做。
- **唯一优先的下一步**：用正式评分实跑 C-C 和 C-A。

**待实跑的候选**（都在 `numpy/core/einsumfunc.py`）：

- **C-C（只放宽一个方向，预计能蒙混过关）**：在 base 上改 `einsum_path` 第 709 行，把 `if dimension_dict[char] != dim:` 改成 `if dimension_dict[char] != dim and dim != 1:`；不更新字典，报错文本不动。
  - 预期：35/35，得 1；预期不符的键：无。
  - 另手动核：`np.einsum('ti,ti->i', np.ones((1,2)), np.ones((10,2)), optimize=True)` 仍抛题面原句，违反"与顺序无关"。
- **C-A（更完整的合理修复）**：先应用 gold，再在 `einsum()` 收缩循环里 `tmp_operands.append(operands.pop(x))` 之后、`if blas:` 之前加一段：取 `_l, _r = einsum_str.split('->')[0].split(',')`；如果 `blas` 为真，且 `idx_rm` 里有任一 `s` 满足 `tmp_operands[0].shape[_l.find(s)] != tmp_operands[1].shape[_r.find(s)]`，就令 `blas = False`。
  - 预期：35/35，得 1；预期不符的键：无。
  - 公开读者 C4 的情况 3、4，在 `True`、`greedy`、`optimal` 三种设置下都应变成 OK。
- **C-D（删掉检查，可选）**：在 base 上把 `einsum_path` 第 708-714 行整段 if/else 换成无条件的 `dimension_dict[char] = dim`。
  - 预期：35/35，得 1；预期不符的键：无。
  - 另手动核：`np.einsum_path('ti,ti->i', np.ones((10,2)), np.ones((3,2)))` 不再报错。

## 附录：证据

- 评分：
  - R-f：`runs/r2e_rf_20260923/remote/ledger_r2e_all_{noop,gold}.jsonl:19`
  - rerun2：`runs/r2e_env_repair_20260924/_rerun2/ledger_{noop,gold}.jsonl:19`
  - M3：`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:26,72`
- devcheck：`runs/r2e_actor_20260925/devcheck/numpy__5e8301c2b36097dd8be5a12e0bb4369a1/`，其中 `orig/captures/*.out`、`private_gold/private_control.json`
- 分析：同目录 `analysis_before_history.md`（§2 隐藏测试、§4 候选、§6 gold、§8 关系）、`old_findings_delta.md`
