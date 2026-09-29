# numpy `18b7cd9d` 静态审查短卡（2026-09-25，私有主审）

> **2026-09-25 协调者更正（按 Codex 复核 r2e_static_actor_review_20260925/README.md）**：四个候选的真实评分已出：A 1、D 0、N 1、I 1，与预期一致。探针里得 1 的补丁用逐项行为检查复核（rh2/experiments/r2e_actor_20260925/postcheck/numpy_18b7cd9d_behavior.py，入口 run_postcheck.py）：None、普通对象、标量、系数相同的列表、等值的另一个 poly1d、同长不同值、不同长度，共 12 项，每项单独捕获异常；不要求照 gold 返回 NotImplemented。已用 gold / A 通过，D / N / I 与 base 不通过验证。 以下原文保留不改。

## 1. 题目、版本与用途

- **目标**：`poly1d.__eq__` 与非 poly1d 对象（题面例子是 `None`）比较时抛 `AttributeError`；修好后不应抛异常，结果应表示"不相等"。
- **版本**：base `6a3edf32`，NumPy 1.13.0.dev0，Python 3.7.9，派生镜像配方 `r2e_derive_v1`，没有材料修订。期望映射 11 个键全是 PASSED；只有一个目标键 `TestDocs.test_poly_eq`。
- **建议用途**：`development_diagnostic`，可列为基座探针候选。这是一道易题：题面给出了修法方向，主要区分点在 `__ne__`。
- **处置**：`static_review` / `needs_review`。这只是静态候选，不是训练或评测批准。

## 2. 关键映射

| 需求或旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖情况 | 执行证据或下一步验证 |
|---|---|---|---|---|
| `p == None` 不抛异常，结果为 `False` | 题面原例 | `test_poly_eq` 第 219 行 | 覆盖 | noop ×2 在此处以题面报错失败；gold ×2 通过；devcheck 在 agent 身份下复现 |
| `p != None` 为 `True` | 题面"表示不相等"，加上 `__ne__` 调用 `__eq__` | 第 220 行 | 覆盖；拒绝 D 有依据 | 私有 gold 对照输出 `True`；D 的真实评分待出 |
| `__eq__` 返回 `False` 或 `NotImplemented` 都可以 | 题面第 18 行 | 只断言表达式结果 | 覆盖，不误拒 | A 的真实评分待出 |
| 任意非 poly1d 对象（int、str、list）比较都不抛异常 | 题面泛称 "a non-`poly1d` object" | 无 | **部分**，N 可以蒙混 | N 的真实评分待出 |
| poly1d 之间按值比较（不同对象、系数相同即相等） | 旧行为；公开 `test_regression.py` 的 `test_poly1d`、`test_poly_div` | 第 221–223 行只比较 `p == p`（同一对象）和系数不同的 `p2` | **部分**，I 可以蒙混 | I 的真实评分待出 |
| poly1d 的其它接口（repr、算术等） | base 源码 | 10 个同文件回归键；其中 `test_doctests` 是死键 | 部分 | 静态推断，加本机合成模块对照 |

**四个候选**（都只改 `numpy/lib/polynomial.py` 的 `poly1d` 类，第 1201–1207 行）：

- **A（合理替代解，预期得 1）**：在 `poly1d.__eq__` 开头加 `if not isinstance(other, poly1d): return False`，`poly1d.__ne__` 保持 `return not self.__eq__(other)` 不变。
- **D（陷阱，预期得 0）**：只在 `poly1d.__eq__` 开头加 `if not isinstance(other, poly1d): return NotImplemented`，`poly1d.__ne__` 不改。结果 `p != None` 得到 `not NotImplemented`，即 `False`，在第 220 行失败。
- **N（蒙混，预期得 1）**：只在 `poly1d.__eq__` 开头加 `if other is None: return False`，其余不改。`p == 3` 仍抛 `AttributeError`。
- **I（蒙混，预期得 1）**：删除 `poly1d` 类里的 `__eq__` 和 `__ne__` 两个方法定义，保留 `__hash__ = None`，比较退回 `object` 的身份比较。这时 `poly1d([1,2,3]) == poly1d([1,2,3])` 为 `False`。

四个候选都可以用同一条行为探针区分：`python -c "from numpy import poly1d as P; p=P([1,2,3]); print(p==None, p!=None, p==3, p==P([1,2,3]))"`，正确修复应输出 `False True False True`。

## 3. 八方面：已查与未查

| 方面 | 已查 | 未查 / 未知 |
|---|---|---|
| 公开需求 | 题面、公开读者报告；`!=` 的要求可以从公开材料推知 | 真实渲染的消息与提示措辞没有捕获 |
| 材料与初始问题 | 各 sha 一致；`initial_diff` 为空；noop 失败即题面报错（RH2 ×2，独立 runner ×5） | — |
| 测试是否测到要求 | 目标键 5 条断言逐条追到 `assert_equal` | N、I 未执行 |
| 是否误拒 | A、C、F 类静态可过 | 未执行 |
| 回归与 gold | gold 共 4 行，没有无关改动；仓库内没有依赖旧行为的调用者；私有 gold 对照符合静态推断 | 没追 `np.poly` / `polyfit` 内部 |
| 开发条件 | 正式启动路径加真实 Claude Code、桩端点、agent 身份（devcheck）：解释器、nose、pytest、导入、复现命令与公开测试都正常 | 真实模型求解（33–36） |
| 交付与评分边界 | 投影收入 `polynomial.py`；隐藏测试恢复与解析正确；派生镜像无隐藏测试，git 历史干净 | 候选改 `numpy/testing`、venv 或新建 rootdir conftest 的风险，只引用共享机制 |
| 题目关系与用途 | 本池 48 题中只有本题的 gold 改到 poly1d；修法方向在题面明示 | 跨来源重复、预训练污染 |

## 4. 问题、影响与证据层次

1. **只测 `None`**（检查 25）。N 类特判能得满分，但它违背题面的泛称要求。证据层次：静态推断。影响：拿到 reward 1 不能证明对所有非 poly1d 对象都修好了。
2. **poly1d 之间只比较同一对象**（检查 25、32）。I 类身份比较能得满分，但破坏了按值比较的旧行为。证据层次：静态推断。按静态推断，公开的 `test_regression.py -k poly` 会抓到 I，但它不计分。
3. **`test_doctests` 是死键**：模块字符串不是 docstring，所以 `rundocs` 实际运行 0 个例子；repr 和算术因此没有评分保护。证据层次：静态推断加本机合成模块对照。这是上游原样的问题，只记为覆盖限度。
4. **已知的全局问题**：公开提示里的 conda / pip 和"测试文件会被重置"的措辞与 R2E 不符（E09 的措辞部分），尚未核实是否已改。它会浪费解题步数，但不妨碍合法修复。
5. **本次引用条件已覆盖的环境问题**：`/testbed` 须在 `sys.path` 上、没有 pip、没有出网，都属于解题侧条件，有实测证据；正式链的解释器前缀和派生镜像已经在 devcheck 中生效（派生镜像切换待 A 线审查）。本题没有需要修复的环境缺口。

## 5. 结论与下一步

- **静态建议**：保留为开发诊断和探针候选。探针之后逐个检查通过的补丁是否属于 N 类或 I 类。只有在打算用于训练时，才考虑做测试修订：
  - 加 `assert_equal(p == np.poly1d([1, 2, 3]), True)`、`assert_equal(p == 3, False)`、`assert_equal(p != 3, True)`；
  - 不要加与 ndarray 的比较：题面没有约定，gold 下会得到逐元素数组；
  - 修订需要用户决定，并用 gold、A、C、D、N、I 双向复验。
- **与历史的分歧**：历史的环境事实全部确认，没有推翻项；过时的是 R13 相关文字、chown 耗时和 E09 激活前缀。测试质量方面的发现是新增的，历史审查范围不含测试质量。reviewer 复核结果暂无。
- **唯一优先的下一步**：核对协调者安排的 A、D、N、I 真实评分，预期依次为 1、0、1、1，并同时记录第 2 节那条行为探针的输出。结果将决定 N、I 是否从静态推断升为执行证据，以及训练用途下是否需要修订测试。

## 附录：证据索引（路径相对仓库根）

- 私有材料：`runs/r2e_static_prep_20260924/v2/private/numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9/`（隐藏测试 `test_1.py` 第 216–223 行，`gold.patch`，`expected_output.json`，`run_refs.json`）。
- 评分日志：
  - `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-{noop-n_3cdaf461,gold-n_d91e0720}.eval.log`；
  - `runs/r2e_env_repair_20260924/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_{f466e78b,f34c3153}.eval.log`；
  - 对应账本各自的第 16 行。
- 独立 runner：`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl` 第 1、49 行；`runs/env_overnight_20260916/M3/facts/18b7cd9df7a4/noop_x2/out1.txt`；`runs/r2e_rf_20260923/reconcile_all/reconcile.json`（本题两条）。
- actor devcheck：`runs/r2e_actor_20260925/devcheck/numpy__18b7cd9df7a4d960550b18faa14d5473e/orig/`（`attempt.json`、`prelaunch.json`、`activation_check.json`、`captures/*.out`）；私有 gold 对照在 `private_gold/private_control.json`。
- 历史：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/tasks/numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9/{findings.md,screening_record.json,facts.json}`；逐条核对见本目录 `old_findings_delta.md`；先稿见 `analysis_before_history.md`。
