<!-- 协调者注（2026-09-25）：宿主不允许子会话写报告文件（"Subagents should return findings as text"），本文由协调者从该会话被拒的写入调用中原样取出保存，未改一字。 -->
# 私有主审初判（读历史前）：numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb

- 角色：R2E 私有主审（静态），2026-09-25，单题、干净上下文。尚未读任何历史调查、审查目录、本批 README 或 `assignments.json`。
- 没有运行项目代码或容器。下文区分三种证据：**执行**（账本、eval 日志、devcheck 捕获）、**静态**（读代码推出）、**未知**。
- 路径简写：`W/` = 公开包 `worktree/`；`T` = `PRIVATE_DIR/hidden_tests/test_1.py`；`DC/` = devcheck 目录 `runs/r2e_actor_20260925/devcheck/numpy__5e8301c2b36097dd8be5a12e0bb4369a1/`（按协调者更正，末尾是 `a1`）。

## 0. 摘要

- **题目目标**：`np.einsum('ti,ti->i', np.ones((10,2)), np.ones((1,2)), optimize=True)` 不再在 `einsum_path` 的标签尺寸检查处报错（`W/numpy/core/einsumfunc.py:706-714`），结果与 `optimize=False` 相同（`[10., 10.]`）。
- **隐藏测试**：就是 base 公开的 `W/numpy/core/tests/test_einsum.py`，只在 `check_einsum_sums` 末尾多了 8 行（`T:484-490`，gh-10343 例）。已用 `diff -u` 核对。目标键是调用这个 helper 的 15 个 `TestEinSum.test_einsum_sums_*`，它们检查的是**同一个输入、同一对断言**；其余 20 键是同文件回归。期望 35 键全是 PASSED。
- **执行证据一致**：
  - noop 两轮都是 20/35。15 个目标键全部停在 `T:487` → `einsumfunc.py:1089` → `einsumfunc.py:712`，报题面原句。
  - gold 两轮都是 35/35。09-23 R-f 与 09-24 rerun2 的日志，把地址和耗时归一化后逐字相同。
  - M3 独立 runner 在来源镜像上跑 gold，两次都是 35 passed。
  - devcheck 用 agent 身份，经正式启动路径 + 真实 Claude Code 2.1.205 + 桩端点，复现出题面报错；公开测试 35 passed。
- **主要问题是覆盖面窄，不是过严。** 测试只检查题面这一个输入：全 1、大尺寸操作数在前、收缩不走 `tensordot`。以下几点都没有测到：
  - 只放宽一个方向的实现（C-C）、直接删掉检查的实现（C-D），静态上都能拿 1。
  - gold 自己也没修 `tensordot` 与多操作数的情形：私有 gold 对照实测报 `ValueError: shape-mismatch for sum`。上游后来用 `broadcast_indices` 补了这一处，补丁已出现在同仓后续题的工作树里。
  - 过严风险没找到：期望里没有 FAILED/ERROR 键，也没有针对报错文本、收缩路径或内部结构的新断言。
- **暂定处置**：静态候选，`needs_review`，理由是"静态候选待 actor 验证"，不是题意或测试争议；附覆盖限度说明。**唯一最优先的下一步**：用正式评分实跑 C-C（单向放宽）和 C-A（更完整的修复），确认两者都得 1 的静态预期。

## 1. 八方面覆盖

| 方面（清单号） | 已查 | 未查 / 限度 |
| --- | --- | --- |
| 公开需求（3、23） | 题面、`public_hints`、`environment_brief.md`、`public_read.md`。题面报错能从 base 逐行读出：`einsumfunc.py:1062`（默认 `optimize=True`）→ `1088-1089` → `706-712`。R1、R2 明确；R5、R6 的范围不确定 | **真实渲染消息仍未捕获**：devcheck 的用户消息是桩文本（`DC/orig/stub/requests/messages_000.json`：`Devcheck run: execute exactly the tool calls you are given, then stop.`），系统提示里没有题面 → 清单 3 记 unknown |
| 材料与初态（1、2、27） | 隐藏测试树、期望映射、`run_tests.sh` 的摘要都与 `grading_bundle.json` 一致；日志头 `RH2_SETUP_HIDDEN_TESTS_TREE=d8853bba…`、`RH2_SETUP_ENTRY_SHA256=8285765f…`；`validation_bundle` 里的 gold 与 `gold.patch` 相同；`initial_diff` 0 字节；noop 失败位置就是题面原句（两轮日志 + `DC/orig/captures/pr1_1_cmd.out`） | — |
| 测试是否测到要求（18–20、25、32） | 逐行追了 15 个目标键的新断言（§2）；日志证明测试体确实执行到 487 行，helper 前半段已全部执行 | R3–R6 没有覆盖；全 1 输入的数值区分力弱 |
| 是否误拒合理解（24、28） | 没有报错文本、路径或内部 helper 的新断言；期望全是 PASSED；新断言与题面例子一一对应；更完整修复在正常输入上不会触发它新增的分支（§4 C-A） | C-A 待实跑 |
| 回归与 gold 完整性（26、27） | 20 个回归键，加上 helper 原有部分（含默认 `optimize=True` 下的 BLAS/`tensordot` 路径）和 `TestEinSumPath` 的精确路径断言。gold 做了执行对照（私有 pr1/pr3）和代码检查（§6）。生产代码里没有别的 `einsum`/`einsum_path` 调用者：grep 只命中 `numpy/core/__init__.py` 的导出、文档与注释 | 没有逐条追回归键背后的 C 实现 |
| 开发条件（6–15） | devcheck 以 agent 身份实测：导入、pytest 7.4.4、无 pip、断网、R2E 预检三项、复现命令、公开测试。公开测试文件 = 隐藏测试减 8 行，所以 20 个回归键在本地可以完整自检 | 真实模型求解、经 Qwen adapter 的链路、候选的真实交付都未验 |
| 交付与评分边界（4、16–17、21–22、29–31） | 修复落在受 git 跟踪的纯 Python 文件；评分不重编译（`RH2_INSTALL_SKIPPED=1`），本题不受影响；git 已清洗（`HEAD` 无子提交，refs/remotes/reflog/unreachable 都是 0，`DC/orig/attempt.json`）；agent 读不到隐藏测试（`HIDDEN_0=DENIED:/root`） | 两处都是共享机制或全仓共性，不是本题特例：隐藏测试借 `numpy.testing` 断言，而它是候选可改的仓库源码；agent 能在 `.venv/site-packages` 写入（运行后多出 pycache） |
| 题目关系与用途（5、29–30、37–40） | 跨题包含已逐文件核对（§8）；题面不泄漏修法 | 3 个前序题的 gold 是否逐行出现在本题初态没有核对（规则不许读他题私有包），只抽查了行为 |

## 2. 隐藏测试展开

**目标键（15 个）**：`test_einsum_sums_{int8,uint8,int16,uint16,int32,uint32,int64,uint64,float16,float32,float64,longdouble,cfloat64,cfloat128,clongdouble}`，都调用 `check_einsum_sums(dtype[, True])`，新增断言在 helper 末尾：

```python
p = np.ones((10,2)); q = np.ones((1,2))                       # T:485-486
assert_array_equal(np.einsum('ti,ti->i', p, q, optimize=True),
                   np.einsum('ti,ti->i', p, q, optimize=False))  # T:487-488
assert_array_equal(np.einsum('ti,ti->i', p, q, optimize=True), [10.] * 2)  # T:489-490
```

- 这段与 `dtype`、`do_opt` 都无关，输入固定是 float64 全 1。`i4/u4/f8/c8` 四个键各调用 helper 两次，所以同一检查一共执行 19 次。noop 下第一次调用就在 487 行抛错，第二次（`do_opt=True`）没有执行到。
- 修复后的调用链（静态）：两个操作数 → `path=[(0,1)]`（`einsumfunc.py:737-739`）。接着 `_can_dot(['ti','ti'], …, {'t'})` 在第 334 行返回 False，因为两边保留的标签有交集 `{i}`。于是走 `c_einsum('ti,ti->i', q, p)`，由 nditer 广播 `t`，**不经过 `tensordot`**。
- 目标键要先把 helper 原有部分跑完：各种求和、trace、inner/outer、matvec/matmat、三矩阵乘、`tensordot`、逻辑与、标量、步长变体、object 数组、#1885。其中多处没有传 `optimize`（`T:275`、`411-414`、`434-442`、`470-482`），按 base 默认 `optimize=True` 走优化路径，也覆盖了 BLAS 分支。所以这 15 个键同时充当优化路径在非单例输入上的回归检查。
- **回归键（20 个）**，全是 base 公开文件原样：
  - `test_einsum_errors`：在 True/False 两种模式下检查异常类型。其中与 K1 相关的只有同一操作数内的 `'ii'` 配 `(2,3)`（`T:83-86`）。
  - `views`（检查 `base is a`）、`misc`、`broadcast`（省略号广播）、`fixedstridebug`、`fixed_collapsingbug`、`all_contig_non_contig_output`、`small_boolean_arrays`。
  - `optimize_compare` 系列 8 键：比较 greedy/optimal 与不优化的结果，用 `assert_almost_equal`，输入是未设种子的 `rand`。
  - `TestEinSumPath` 4 键：断言精确的收缩路径，输入尺寸都 ≥ 2。
- **阅读范围**：`T` 全文逐行读过；回归键的断言逐条看过，没有逐条追到 C 实现。

## 3. 双向映射

| 要求 / 旧行为 | 公开依据 | 测试键 / 断言 | 覆盖 | 证据 / 下一步 |
| --- | --- | --- | --- | --- |
| R1 示例不报错，形状 `(2,)` | 题面 | 15 个目标键，`T:487-490` | 覆盖 | 执行：noop 15 FAILED（原句）；gold 35/35 ×2，另有 M3 ×2 |
| R2 值与 `optimize=False` 相同 | 题面 + `c_einsum` 参照 | 同上两条 `assert_array_equal` | 覆盖，但输入全是 1，区分力弱 | 同上 |
| R3 与顺序无关（`(1,2)` 在前） | 广播是对称的（可推知） | 无 | **缺失** | 执行：gold 通过（私有 pr3 情况 2；greedy/optimal 两行可见为 OK，True 行的状态前缀在截断处之外）；C-C |
| R4 `optimize` 的其它取值 | 都经过 `einsum_path` 的同一处检查 | 无（只测 `True`） | 缺失；gold 修的正是这一个检查点 | 执行：私有 pr3 情况 2 的 greedy/optimal 为 OK；情况 1 的这两行被截断，未见 |
| R5 `tensordot` / 多操作数 | 题面描述段是泛指 | 无 | **缺失，gold 也不满足** | 执行：私有 pr3 情况 3、4 报 `shape-mismatch for sum`；上游后续补丁见 §8 |
| R6 直接调用 `np.einsum_path` | 公开 API | 无 | 缺失 | 静态 |
| K1 真正不兼容的尺寸仍报 `ValueError` | 旧行为 | `test_einsum_errors` 的 `'ii'` 配 `(2,3)`，True/False 两种模式 | **部分**：只测了同一操作数内；跨操作数的真不兼容没测（C 层照样会报错） | 执行：私有 pr3 情况 5 gold 报 `ValueError` |
| K2 `optimize=False` 行为不变 | 旧行为 | `T:488` 作参照，另有多键 | 覆盖 | — |
| K3 旧测试（含精确路径）继续通过 | 旧行为 | 20 个回归键 + helper 原有部分 | 覆盖（仅限非单例输入） | 执行：noop 和 gold 下这 20 键都是 PASSED |
| 报错文本 | 没有约定 | 无断言 | 不约束（这是对的） | gold 改了报错文本仍得 1 |

反查：新断言全部来自题面示例，其余断言都是 base 公开测试原样。**没有找到缺少公开依据的断言。**

## 4. 候选（可直接改成补丁，请协调者实跑）

都在 `numpy/core/einsumfunc.py` 里改。下面的预期结果是静态推断。

- **C-A（合理且更完整，检验是否过严）**：在 gold 的基础上，于 `einsum()` 收缩循环（`1094` 行起）组好 `tmp_operands` 之后、`if blas:` 之前加一段：
  `if blas:` → 取 `_l, _r = einsum_str.split('->')[0].split(',')`；如果 `any(tmp_operands[0].shape[_l.find(s)] != tmp_operands[1].shape[_r.find(s)] for s in idx_rm)`，就令 `blas = False`（交给 `c_einsum` 广播）。
  也可以照上游后续做法，在 `einsum_path` 里记录 `broadcast_indices`，被求和的标签属于广播标签时不走 BLAS。
  **预期 35/35 → 1**：正常输入不会触发这个守卫，而 helper 里的 `tensordot` 用例会走到这个分支。公开 C4 的情况 3、4 在三种 `optimize` 下都应变成 OK。
- **C-C（可能蒙混：单向放宽）**：只把第 709 行改成 `if dimension_dict[char] != dim and dim != 1:`，不更新字典，其余不动。
  **预期 35/35 → 1**：隐藏测试里大尺寸在前；`'ii'` 配 `(2,3)` 仍会报错。
  但 `np.einsum('ti,ti->i', np.ones((1,2)), np.ones((10,2)), optimize=True)` 仍然报原句，违反 R3。这可以说明测试放过了不对称的实现。
- **C-D（可能蒙混：删掉检查）**：把第 708-714 行换成无条件的 `dimension_dict[char] = dim`，不校验，后见的尺寸覆盖先见的。
  **预期 35/35 → 1**：`'ii'` 配 `(2,3)` 由 C 层报 `ValueError`（`einsum.c.src:2229-2236`）；示例走 `c_einsum`。
  副作用有三：`np.einsum_path('ti,ti->i', np.ones((10,2)), np.ones((3,2)))` 不再报错，而是返回一条路径；`np.einsum(..., optimize=True)` 改由 nditer 报错，措辞变了；示例里 `t` 被记成 1，代价估算偏小。这说明 K1 只靠下游兜底，`einsum_path` 自身的校验没有测。

没有专门列"错误数值"的负例：`[10.]*2` 那条断言能挡住"截短到尺寸 1"这类实现（结果会是 `[1,1]`）。但对"忽略 `q` 的值"这类错误，全 1 输入挡不住。这类实现不自然，没有列为待跑候选，只作覆盖限度记录。

## 5. R2E 专项

- **(a) 期望里的非 PASSED 键**：没有，35 键全是 PASSED。因此不存在"更完整的修复把失败键翻成通过、反而判 0"的风险。测试没有参数化，收集结果也不会变。
- **(b) 题面报错是否出现在 noop 目标键的失败原因里**：出现了。两份 noop 日志中，15 个 `E` 行都是 `ValueError: Size of label 't' for operand 1 does not match previous terms.`，位置 15 次都是 `T:487` → `einsumfunc.py:1089` → `:712`。15 个 FAILED 键在 short summary 里都有。
- **(c) 题面是否泄漏修法**：没有。题面给出的是失败调用和期望语义（"by broadcasting"），没提修改位置和写法。报错文本可以 grep 到（`Size of label`），定位很直接，但这不算泄漏。
- **(d) 依赖 base 版测试辅助、搬迁伪影或撞键**：都没有。
  - 隐藏测试只导入 `numpy.testing`（库代码），不导入仓库测试模块里的辅助代码。
  - 搬到 `r2e_tests/` 后不再加载 `numpy/conftest.py`（FPU 检查、slow 标记、`numpy.testing.utils` 替换），各轮运行都没受影响：收集 35 键，状态一致。
  - 只有一个文件，不存在跨文件撞键。
- **(e) 时间、随机、资源敏感**：
  - 目标键是确定性的。
  - `optimize_compare` 系列用未设种子的 `rand`，容差是绝对 1.5e-7。在 8 次观测中都通过：评分 4 次、M3 2 次、devcheck 公开测试 orig 与 gold 各 1 次。
  - `TestEinSumPath` 的路径只由尺寸决定。
  - 评分侧内存峰值 489–503 MB，测试耗时 1–3 s。
- **(f) 材料修订**：没有（`revisions.json` 是 `[]`）。

## 6. gold 检查

gold 只改了 `einsum_path` 的尺寸检查（6 行）：遇到"1 对 N"时记下非 1 的尺寸，两边都不为 1 且不相等时才报错，报错文本里带上两个尺寸。

- **修到了**：
  - 题面原例：私有 pr1 输出 `[10. 10.] (2,)`；评分两轮 35/35；M3 两次通过。
  - 对调顺序：私有 pr3 情况 2。
  - 其它 `optimize` 取值：同一检查点；情况 2 的 greedy/optimal 可见为 OK。
- **没修到（执行）**：被求和的标签一侧为 1、并且这一步走 `tensordot` 的情形（情况 3），以及三操作数的情形（情况 4），仍报 `ValueError: shape-mismatch for sum`（`W/numpy/core/numeric.py:1276-1289`）。
  - 与题面描述段"operands that include singleton dimensions"对照，这是**部分修复**。题面的期望行为和示例本身是修好了的。
  - 上游后来补了这一处，见 §8 两道后续题工作树里的 `broadcast_indices` 与 `# If we're broadcasting, nix blas`。
  - 测试不检查这类情形，所以 reward 区分不了部分修复和完整修复。
- **报错文本里两个尺寸写反了（执行，外观问题，未测）**：`% (char, tnum, dimension_dict[char], dim)` 让实际大小为 3 的 operand 1 显示成 `(10)`。私有 pr3 情况 5 的输出是 `Size of label 't' for operand 1 (10) does not match previous terms (3).`。上游后续版本保留了同样的写法。
- **小的宽松（静态，未测）**：同一操作数内的重复标签如果是"1 对 N"（例如 `'ii'` 配 `(1,3)`），现在能通过 `einsum_path` 的检查。`np.einsum` 仍会在 C 层报错（`einsum.c.src:2229-2236` 要求严格相等），只有直接调用 `einsum_path` 时不再报错。
- 没有无关改动。判定依据是公开要求，不是"与 gold 不同"。

## 7. 开发需求（逐题）

devcheck 的镜像是 `sha256:d0b59d8b…`，评分侧 current 运行用的是 `sha256:b72f0fc4…`。两者 ref 相同（`rh2-r2e-derived/numpy:5e8301c2b360-r2e_derive_v1`），配方都是 `r2e_derive_v1`，但属于不同机器上的两次构建。

| 条件 | 本题事实 | 证据级别 |
| --- | --- | --- |
| 导入 | 在 `/testbed` 下 `python` 能导入 `numpy 1.15.0.dev0+354ac25`，来自 `/testbed/numpy/__init__.py`；扩展已在镜像里编译好 | 镜像层面实测（`DC/orig/captures/env.out`，agent 身份） |
| 依赖 | 只需要 numpy 自身和 pytest 7.4.4（插件 hypothesis 6.79.4、pytest-env 1.0.1）；没有 pip（`No module named pip`），也不需要 pip | 实测（env.out；评分日志头） |
| 资产 | 不需要 | 静态 |
| 权限 | agent uid 54321；`/testbed` 属主 54321、可写；home、`/tmp` 可写；激活文件 `/rh2/bash_env` 不可写 | 实测（`DC/orig/prelaunch.json`、`env.out`） |
| 网络 | 解题和测试都不需要；外部 DNS 与禁止目标都是 DENIED | 实测 |
| 构建 | 不需要：改纯 Python 文件后直接生效；评分侧 `RH2_INSTALL_SKIPPED=1`，不重编译，本题合法修复不受影响；编译器是否可用没查（本题用不到） | 实测 + 未查 |
| 复现 / 验证 | pr1 原样复现题面报错；pr2 参照输出 `[10. 10.]`；pr3 扩展情形的行为与公开读者预期一致；pr4 公开测试 35 passed、0.53 s。公开测试就是隐藏测试减去 8 行，所以回归可以在本地完整自检 | 实测（agent）；gold 对照是 root 身份、一次性容器 |
| 提交边界 | 修改受跟踪的 `numpy/core/einsumfunc.py`；gold 能干净 `git apply`；评分 gold = 1 | 实测（`DC/private_gold/private_control.json`、评分账本） |
| 资源 | 默认 2 CPU / 4 GiB / `/tmp` 1 GiB 足够 | 实测 |
| actor 待验 | 真实题面消息的渲染、真实模型求解、经 adapter 的链路、候选经 RH2 冻结和投影后交给 grader（devcheck 没有提交候选） | 未知 |

## 8. 题目关系

- v3 公开包里同仓 numpy 共 7 题，只有本题涉及 `einsum`。
- **本题的修复出现在两道后续题的初态里（已逐文件核对）**：
  - 两题是 `numpy__43e333e2`（`np.ma.average`，Python ≥ 3.8 的新版 numpy）和 `numpy__d89bc4bb`（`histogram2d` density，1.16）。
  - 两者公开工作树的 `numpy/core/einsumfunc.py` 都含 gold 的新增行：`dimension_dict[char] == 1`、`dim not in (1, dimension_dict[char])`，以及新报错文本。另外还有上游后续的 `broadcast_indices` 补丁。
  - 两者公开的 `test_einsum.py` 都含 `# singleton dimensions broadcast (gh-10343)` 这一块，也就是本题的隐藏断言（grep 计数都是 1）。
  - 这与机械比对结果（6/6）一致。影响：本题的答案和隐藏断言在这两题的初态里可见。做评测留出时应把三题放在同一侧，或者记录这项暴露。本题自身不泄漏。
- **反向（机械比对 + 抽查行为）**：`numpy__18b7cd9d`（`poly1d.__eq__`，1.13）、`numpy__2f4a9650`（`savetxt`，1.14）、`numpy__d805e9b6`（masked 数组 repr，1.12）的 gold 按比对结果都出现在本题初态里。
  - 我抽查了两处，都与比对一致：`W/numpy/lib/polynomial.py:1239-1244` 对非 `poly1d` 返回 `NotImplemented`；`W/numpy/lib/npyio.py:1325-1327` 对 0 维或大于 2 维的数组报 `ValueError`。
  - 没有逐行核对（不读他题私有包）。影响同上：这三题如果做留出，本题的初态会暴露它们的答案。
- `numpy__a5ea773e`（`tile`，1.10）与本题无关。任务类型：单文件、6 行的 Python 缺陷修复；题面不给修法。

## 9. 缺口、问题与暂定处置

**问题（按影响排序）**

1. **I1 覆盖窄**（清单 25、32）：只测题面这一个输入。R3–R6 都缺；输入全 1；15 个目标键是同一检查的复制。C-C、C-D 静态上都能拿 1。证据：静态 + gold 执行对照；待实跑 C-C/C-D。
2. **I2 gold 部分修复**（清单 27）：没修 `tensordot` 和多操作数情形。证据：执行（私有 pr3）+ 上游后续补丁（§8）。与 I1 叠加后，reward 分不出完整修复和部分修复。
3. **I3 gold 报错文本里尺寸写反**（外观，未测）：执行证据。
4. **I4 跨题包含**（清单 5、29 的跨题面）：影响数据划分，不影响本题评分。
5. **I5 协调者材料注记**：`run_refs.json` 两条 noop 行的 `mismatched` 只列了 12 个（少了 `uint8/uint32/uint64`），账本第 19 行实际有 15 个，`match_count=20`。这是汇总被截断，本题证据本身没问题。
6. **I6 真实消息没有捕获**（清单 3）：devcheck 用的是桩用户消息。

**缺口**
- actor 链路（真实模型、adapter、真实交付）未验。
- 私有 pr3 的输出只保留了尾部：情况 1 的 greedy/optimal 两行、情况 2 的 True 行状态前缀都不可见；情况 1 在 `optimize=True` 下由 pr1 覆盖。
- devcheck 那次构建上没有跑隐藏测试评分（评分证据在另一次构建上）。
- 反向包含没有逐行核对。

**暂定处置**
- `disposition.scope=static_review`；`state=needs_review`，reason 写"静态候选待 actor 验证"（不是题意或测试争议）。
- 用途注记：reward 1 只说明题面这一例修好了（大尺寸在前、收缩不走 BLAS），不能解读为完整支持单例维广播；gold 本身也不完整。
- **建议队列**（不阻塞）：
  1. 实跑 C-A、C-C、C-D（下一步首选 C-C + C-A）。
  2. 可选的测试加强修订：在隐藏断言里加上对调顺序的一例。gold 已实测能过（私有 pr3 情况 2），可以挡住 C-C 这类实现。**不建议**加 `tensordot`/多操作数的断言：gold 过不了，属于扩大需求，要先由用户定范围。
  3. actor 验证时捕获真实题面消息。

## 附录：证据索引（全部已读，sha256 与 `run_refs.json` 一致）

- 评分 current（09-23 R-f）：
  - noop：`runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:19`，日志 `…/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-n_a9fdcb72.eval.log`：15 failed / 20 passed，`test_rc=1`，short summary 在第 3086-3121 行。
  - gold：`ledger_r2e_all_gold.jsonl:19`，日志 `…gold-n_b4799438.eval.log`：35 passed，`RH2_SETUP_APPLY_RC=0`。
- 评分 current（09-24 rerun2）：`runs/r2e_env_repair_20260924/_rerun2/ledger_{noop,gold}.jsonl:19`，日志 `…rer_d46437e5` / `…rer_14e906b7`。与 R-f 日志归一化后 `diff` 为空。
- 独立参考：`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:26,72`（来源镜像、`network=none`）；两份 `test_output.txt` 都是 35 passed。
- devcheck：
  - `DC/orig/`：`commands_with_preflight.json`、`captures/{r2e_preflight,env,pr1_1_cmd,pr2_2_cmd,pr3_3_cmd,pr4_4_pytest}.out`、`attempt.json`、`prelaunch.json`、`activation_check.json`、`post_run_facts_root.txt`、`stub/requests/messages_000.json`。
  - `DC/private_gold/{private_control.json,stdout.log}`。
- 代码位置：
  - `W/numpy/core/einsumfunc.py`：`266-372`（`_can_dot`）、`660-683`、`699-714`、`737-749`、`754-785`、`1062-1146`。
  - `W/numpy/core/numeric.py:1276-1289`；`W/numpy/core/src/multiarray/einsum.c.src:2222-2242`；`W/pytest.ini`；`W/numpy/conftest.py`。
- 跨题：`runs/r2e_static_prep_20260924/cross_task_gold_scan.json`（本题相关 5 条）；`v3/public/numpy__43e333e2…/worktree/numpy/core/einsumfunc.py:856-883,928-937`；`numpy__d89bc4bb…` 同文件 `850-876`；两题的 `test_einsum.py` 都含 gh-10343 块。
