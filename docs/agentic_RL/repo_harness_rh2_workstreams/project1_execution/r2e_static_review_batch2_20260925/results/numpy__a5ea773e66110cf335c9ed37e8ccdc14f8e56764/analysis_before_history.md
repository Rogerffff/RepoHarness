<!-- 协调者注（2026-09-25）：宿主不允许子会话写报告文件（"Subagents should return findings as text"），本文由协调者从该会话被拒的写入调用中原样取出保存，未改一字。 -->
# 私有主审（读历史前）：numpy__a5ea773e66110cf335c9ed37e8ccdc14f8e56764

- 角色：R2E 私有主审（静态审查），2026-09-25。本文件写于读取任何历史调查之前。
- 边界：只读材料和已有运行原件；没有运行项目代码或容器，没有修改原件。
- 证据级别：**执行**指已有运行原件；**代码**指静态阅读源码或配置；**推断**指静态推演，未实测。
- 路径简称：`PUB` 为公开包，`PRIV` 为私有包，`DC` 为 `runs/r2e_actor_20260925/devcheck/numpy__a5ea773e66110cf335c9ed37e8ccdc14f/`。不带前缀的源码行号按 `PUB/worktree`，即 `/testbed`。

## 0. 结论与暂定处置

- **题目**：`numpy.tile` 在所有重复因子都是 1 时，返回的是输入的视图，改结果会改到输入；要求返回独立副本。base 是 1.10.0.dev0（`d770034`），修复是 `numpy/lib/shape_base.py:853` 的一处纯 Python 改动。
- **材料与测试**：
  - 材料互相对应；初态确有题面所述的 bug（执行证据）；gold 正确，只有一个 hunk。
  - 期望映射 32 键全是 PASSED，目标键只有 1 个，就是题面示例逐字照搬。
  - 没有找到会误拒合理修复的断言。
- **主要问题：覆盖窄。** 题面写了 "in all dimensions"，但 `(1,)`、`[1]`、升维、0-d 这些形式都没测。只处理标量 `reps=1` 的部分修复也能得 1（推断，见 §9 候选 B、C）。
- **题目关系**：本题修复（上游后来的演进形式，保留同一句注释）和目标测试 `test_tile_one_repetition_on_array_gh4679`，逐字出现在同仓全部 6 道较新 numpy 题的公开工作树里。协调者的机械比对漏报了这一关系（§7）。
- **暂定处置**：`disposition.state=needs_review`，理由是"静态候选待 actor 验证"；不需要材料修订。本题可以作为 development_diagnostic 探针候选，但使用时注意：
  - 改动小：一个 18 行的纯 Python 函数。
  - reward=1 只能说明题面原例修好了，诊断时要看补丁本身。
  - 做留出评测划分时，要登记 §7 的跨题关系。
- **唯一最值得先做的下一步**：在当前覆盖表镜像 `sha256:4bd9cf42…` 上，用正式评分代码一批跑 noop、gold、候选 A 和候选 B（§9）。

## 1. 与公开读者产物对照

**执行证据确认了公开读者的预测**（`DC/orig/captures/` 是 agent 身份的结果，`DC/private_gold/private_control.json` 是 gold 对照）：

- 导入：`numpy 1.10.0.dev0+d770034`，从 `/testbed/numpy/__init__.py` 导入。
- C2 复现：修复前输出 `[2 3 4 5 6] True`，gold 后输出 `[0 1 2 3 4] False`。
- C3 边界矩阵：12 行修复前的输出与预测逐行一致。gold 后形状和类型不变，最后一列全为 `False`，`matrix` 仍是 `matrix`。
- C4（`-k Tile`）：修复前后都是 3 passed。C5（整个测试文件）：修复前后都是 31 passed。

**公开读者留下的未知项，现在有了答案**：隐藏测试没有覆盖升维、空 `reps` 和子类，只测了题面原例。

**公开读者没有捕获、需要更正的条件**：

1. 公开读者把 `public_hints` 当作解题者能看到的指令来分析，包括"提示与环境说明不完全一致"那一条。按代码，情况不是这样：
   - 正式链的用户消息只有 `render_user_prompt` 的结果，也就是一行开头加题面（`rh2/src/repoharness2/adapters/slime/generate.py:1976`；`envpack/bundles.py:282-289`）。
   - 提示只写进容器文件 `/rh2/public_task_bundle.json`，不注入系统提示（`envpack/ingest_r2e_subset.py:197-201` 的注释；环境卡 §2）。
   - 所以模型默认看不到这几句话：用 `python -m pytest`；没有 pip、没有网络；不要改测试文件。

   真实任务消息仍未捕获：devcheck 的用户消息是 devcheck 指令，不是题面（`DC/orig/stub/requests/messages_000.json`）。
2. home 目录是 256 MiB 的 tmpfs（`DC/orig/prelaunch.json`）。环境说明只写了"可写"。
3. "裸 `pytest` 收集会失败"仍然只有环境说明一方的说法，devcheck 没有测这条命令。

## 2. 八方面覆盖

| 方面（清单号） | 已查 | 结论 | 证据 | 未查 |
|---|---|---|---|---|
| 公开需求（3、23） | 题面、公开包、`public_read.md`、`tile` docstring、`render_user_prompt` | 主需求清楚。边界（升维、空 `reps`、子类）题面没说。公开提示不进入模型消息（§1） | 代码 | 真实任务消息未捕获 |
| 材料与初始问题（1、2、27） | 提交前缀、材料哈希、隐藏测试与公开测试的 diff、noop 日志、devcheck 复现 | 材料对应；noop 的失败正是题面症状 | 执行 | — |
| 测试是否测到要求（18–20、25、32） | 32 键逐一对照；目标键的调用链；noop / gold 日志 | 目标断言测的性质正确（改结果不改输入），但只有"1-D 数组配标量 `1`"这一个输入 | 执行 + 推断 | 部分修复还没实跑 |
| 是否误拒合理解（24、28） | 期望全是 PASSED；考虑替代实现路线 | 没有发现误拒风险 | 推断 | 候选 A 还没实跑 |
| 回归与 gold（26、27） | gold 的各分支；`tile` 的调用者（base 里没有非测试调用者） | gold 正确，没有无关改动。升维、0-d、子类的正确行为没有任何键保护 | 执行（私有 gold 对照）+ 代码 | MaskedArray 掩码、非 ndarray 的 array_like 别名（都在题意范围外） |
| agent 开发条件（6–15） | devcheck：正式启动路径、agent 身份；私有 gold 对照 | 导入、复现、公开测试都可用。复现命令能区分修复前后，公开测试不能 | 执行（actor 路径，桩模型） | 真实模型；裸 `pytest` |
| 交付与评分边界（4、16–17、21–22、29–31） | gold 投影、评分顺序、git 清理事实、隐藏测试是否可读 | 修复文件能交付。派生镜像已清掉未来提交（来源镜像里可达） | 执行 | `numpy/testing/`、根目录 `conftest.py` 这类共享控制面通道，没有逐题验证 |
| 题目关系与用途（5、29–30、37–40） | 跨题比对文件；同仓 6 题的公开工作树 | 本题修复和目标测试出现在 6/6 道较新 numpy 题的初态里，机械比对漏报；模型记忆也能取到答案 | 执行（文件比对） | 与其它来源（如 SWE-Gym）是否重复，未查 |

## 3. 隐藏测试展开

`PRIV/hidden_tests/test_1.py` 与公开的 `numpy/lib/tests/test_shape_base.py` 相比只多了一个测试（diff 只命中 test_1.py:326-331）。所以 32 个键里有 31 个，求解者能直接读到并运行。

**目标键**：`TestTile.test_tile_one_repetition_on_array_gh4679`（test_1.py:327-331）。noop 为 FAILED，gold 为 PASSED，4 次 RH2 运行结果一致。

- 调用：`a = np.arange(5)`；`b = tile(a, 1)`（`tile` 从 `numpy.lib.shape_base` 导入）；`b += 2`；最后 `assert_equal(a, np.arange(5))`。
- base 里的执行路径：
  1. `tup=(1,)`，`d=1`。
  2. `_nx.array(A, copy=False, subok=True, ndmin=1)` 返回 `a` 本身（:853）。
  3. 因子是 1，跳过 `repeat`（:859）。
  4. `c.reshape([5])` 返回视图（:865）。
- 依据：题面示例逐字照搬（`user_prompt.txt:13-17`）。
- 只覆盖 R1 这一个输入；没有其它 `reps` 形式、维度、dtype 或子类。

**回归键**：31 个，noop 和 gold 下都是 PASSED。

- **和 `tile` 有关的 3 个**：
  - `TestTile.test_basic`：`reps` 为 2、(2,2)、(1,2)，以及 list 输入配 2、(2,1)、(2,2)，没有一个是全 1。
  - `test_empty`：`tile(np.array([[[]]]), (3,2,5)).shape == (3,2,0)`。
  - `test_kroncompare`：6 种形状 × 6 种 `reps`，与 `kron` 比值；`reps` 里没有全 1。

  它们保护的是非全 1 路径的值和形状，都不经过本题要改的分支。
- **其余 28 个**：测 `apply_along_axis`、`apply_over_axes`、`array_split`/`split`/`hsplit`/`vsplit`/`dsplit`、`dstack`、`squeeze`、`kron`、`may_share_memory`。base 里没有非测试代码调用 `tile`：全树 grep `tile(`，排除 tests 和 docstring 后结果为空。所以只改 `tile` 的候选影响不到这些键，它们对本题是死键。
- **阅读范围**：32 个测试的全文都读过。辅助函数只有文件内的 `compare_results`。导入的是 `numpy.testing` 的 `assert_*` 和 `TestCase`，以及 `numpy.random.rand` / `randint`。

## 4. 需求—测试双向映射

| 公开要求 / 合理旧行为 | 依据 | 测试键 / 决定性断言 | 覆盖 | 执行证据 / 待做 |
|---|---|---|---|---|
| R1：1-D ndarray 配 `reps=1`，改结果不改输入 | `user_prompt.txt:10-21` | 目标键，test_1.py:331 | 覆盖 | noop 日志 :123-128 为 `x: array([2, 3, 4, 5, 6])`；gold 为 PASSED；devcheck pr1_1 同上（§1） |
| R2：其它全 1 形式，即 `(1,)`、`[1]`、2-D 配 `1`、`A.ndim > d` 时前补 1 | 题面 "in all dimensions"（:7）；docstring :805 | 无 | **缺失** | devcheck pr2_2：base 下这些情形全部共享内存，gold 下全部不共享。见候选 B |
| R3：全 1 且需要升维，即 1-D 配 `(1,1)` 得 (1,5)，0-d 配 `1` 得 (1,) | docstring :796-803（结果维数是 `max(d, A.ndim)`，不足时在前面补轴） | 无 | **缺失** | pr2_2 里 gold 的形状与 base 一致。见候选 C |
| R4：空 `reps=()` | 代码推知（:856-857） | 无 | 缺失（题面未约定） | gold 会复制（pr2_2 的 `a,()` 行为 False） |
| R5：非全 1 路径的值、形状、升维规则不变 | docstring；公开测试 | test_basic / test_empty / test_kroncompare | 覆盖（回归） | noop 和 gold 下都是 PASSED |
| R6：全 1 时结果的值、dtype、形状与 base 相同 | 题面要求的是"copy" | 目标键只检查输入有没有被改，不检查结果的值 | 部分 | — |
| R7：子类（`np.matrix`）返回同一子类 | 题面未约定（base 全程 `subok=True`） | 无 | 缺失（不算需求） | gold 保留 `matrix`（pr2_2） |

**反查**：唯一新增的断言来自题面原例，其余断言都是仓库已有的测试。没有发现缺少公开依据的断言。

## 5. R2E 专项

- **(a) 期望里的非 PASSED 键**：没有 FAILED 或 ERROR 键。更完整的修复不会因为把期望的失败翻成通过而被判 0。
- **(b) 题面报错是否出现在 noop 失败原因里**：出现了。noop 目标键的失败原因是 `AssertionError: Arrays are not equal … x: array([2, 3, 4, 5, 6]) y: array([0, 1, 2, 3, 4])`（R-f noop 日志 :123-128；环境轮复跑逐字相同），与题面 "Actual output: [2 3 4 5 6]" 一致。
- **(c) 题面是否泄漏修法**：题面点明了根因类别（没有复制）和触发条件，但没给实现，不算泄漏修法。需要注意的是，隐藏的目标测试就是题面示例本身，满足示例就能得分。外部答案可达性见 §7。
- **(d) 测试辅助、搬迁伪影、撞键**：
  - 不依赖仓库测试模块里的辅助代码；`compare_results` 定义在文件内。
  - 原目录 `numpy/lib/tests/` 没有 conftest，也没有 `__init__.py`；测试不读相对路径资源。搬到 `r2e_tests/` 后没有伪影。
  - 只有一个测试文件，没有撞键；没有参数化。
  - 注意：断言函数来自候选可以改、评分时又不会重置的 `numpy/testing/utils.py`。这属于共享的控制面通道（清单 31），见 §10。
- **(e) 时间、随机、资源敏感的键**：
  - `TestSqueeze.test_basic` 和 `TestTile.test_kroncompare` 用了未设种子的 `rand` / `randint`，但断言结论与取值无关。
  - `TestArraySplit.test_integer_split_2D_rows` 和 `_2D_default` 依赖 `assert_warns(FutureWarning)`。它内部先 `catch_warnings(record=True)` 再 `simplefilter('always')`（`numpy/testing/utils.py:1595-1596`），所以不受 `-W ignore` 影响。
  - 4 次 RH2 运行和 2 次 M3 运行的逐键结果一致。
  - 没有时间或资源敏感的键：测试耗时不到 1.5 s，内存峰值约 272 MB。
- **(f) 材料修订**：本题没有修订（`revisions.json` 为 `[]`，`current_material.material_revisions=[]`）。

## 6. gold 检查

- **改动内容**：如果 `all(x == 1 for x in tup)` 且 `isinstance(A, ndarray)`，就用 `copy=True` 取数组，否则仍用 `copy=False`。
  - 只有一个 hunk，没有无关改动。
  - 与上游修复提交的源码部分一致：M3 记录 `gold_matches_git_diff_changed_lines=true`，排除的文件正是 `numpy/lib/tests/test_shape_base.py`。
- **原例修好了**：目标键 PASSED（执行）。
- **边界**：私有 gold 对照（root 身份、与 devcheck 同一张镜像）里，12 个情形全部不再共享内存，形状和类型不变，`matrix` 仍是 `matrix`（执行）。
- **判断放在补 1 之前**：补进去的都是 1，不影响结果。`reps=()` 时 `all([])` 为真，也会复制。
- **复制范围**：只对 ndarray（含子类）复制。
  - list、标量输入本来就会新建数组。
  - 经 `__array__` 或缓冲协议暴露内存的非 ndarray 对象，结果仍可能共享内存（推断）。题面限定了 "on a NumPy array"，所以这不算 gold 的缺陷，只是按 Expected 那句话的宽泛读法时没覆盖的范围。
  - MaskedArray 的掩码会不会另拷，没有查，属于题意范围外。
- **未测回归**：gold 本身没有发现回归。但升维后的形状、0-d、子类这几项行为，gold 做对了，却没有任何键保护（见候选 B、C）。

## 7. 题目关系

- **机械比对**：协调者的比对文件（`runs/r2e_static_prep_20260924/cross_task_gold_scan.json`，81 对）里没有任何一对涉及本题。
- **逐题核对**：我打开了同仓 6 道题的公开工作树。

  | 题目 | 版本 |
  |---|---|
  | `numpy__18b7cd9d` | 1.13 |
  | `2f4a9650` | 1.14 |
  | `43e333e2` | 比 1.16 更新（`setup.py` 格式已变） |
  | `5e8301c2` | 1.15 |
  | `d805e9b6` | 1.12 |
  | `d89bc4bb` | 1.16 |

  每一道的 `numpy/lib/shape_base.py` 都含有：
  - `if all(x == 1 for x in tup) and isinstance(A, _nx.ndarray):`
  - 同一段注释 "Fixes the problem that the function does not make a copy…"
  - `return _nx.array(A, copy=True, subok=True, ndmin=d)`

  每一道的 `numpy/lib/tests/test_shape_base.py` 都含有 `test_tile_one_repetition_on_array_gh4679`。本题的 base 是 1.10.0.dev，在 7 道题里最早。
- **漏报原因**：gold 的 3 条非注释新增行里，上游后来做了两处改写：`all((…))` 的双括号改成了 `all(…)`，`c = …copy=True…` 改成了 `return …`。逐字命中只剩 base 里本来就有的 `copy=False` 那一行，即 1/3，低于 80% 阈值。另外比对时去掉了注释，所以注释行也没算上。
- **反方向**：本题 base 最早，其它题的修复不会出现在本题初态里；比对在这个方向上也没有命中。
- **影响**：
  - 这不是同一道题的改写，不影响本题评分。
  - 做留出评测划分时要登记：如果本题进评测，而另外 6 题中任何一道进训练，训练轨迹可能读到修好的 `tile` 和目标测试。
  - 修好的代码就是现代 numpy 的 `tile`，模型从记忆里就能取到答案（清单 30 里的非网络通道）。这只影响把本题当作独立的能力测量，不影响开发诊断用途。

## 8. 开发需求

| 项 | 需求 | 证据级别 |
|---|---|---|
| 导入 | 在 `/testbed` 下用 `python -c` 导入 `/testbed/numpy`；包没有装进 venv | actor 正式启动路径实测（`DC/orig/captures/env.out`，uid 54321） |
| 依赖 | 不需要新包；没有 pip（`No module named pip`）；venv 里已有 pytest 7.4.4、hypothesis 6.79.4、pytest-env 1.0.1 | 同上 |
| 资产 | 无 | 代码 |
| 构建 | 不需要，改动是纯 Python。评分侧 `RH2_INSTALL_SKIPPED=1`，所以改 C 源码不会被编译（本题没有理由改 C） | 评分日志实测 |
| 权限 | agent 拥有 `/testbed`（`WORKDIR_OWNER=54321`）；home 是 256 MiB tmpfs，`/tmp` 1 GiB；激活文件 `/rh2/bash_env` 不可写 | 实测（`prelaunch.json`、`env.out`） |
| 网络 | 任何阶段都不需要网络。外部 DNS 和直连都被拒（DENIED），只有模型 relay 能连 | 实测 |
| 复现 | 公开读者的 C2、C3 两条命令都能区分修复前后（§1） | 实测：agent 身份跑 orig，root 身份跑私有 gold 对照 |
| 公开测试 | `python -m pytest numpy/lib/tests/test_shape_base.py`：31 passed，rootdir 是 `/testbed/numpy/lib`（推断原因：pytest 按 `numpy/lib/setup.py` 定 rootdir）。修复前后结果相同，只能做回归检查 | 实测 |
| 裸 `pytest` | 环境说明称收集会失败。推断原因：`numpy/lib/tests/` 没有 `__init__.py`，而裸 `pytest` 的 `sys.path` 不含 `/testbed`。公开提示不进入模型消息，模型可能先踩到这个问题，但可以自行恢复 | 环境说明称实测；devcheck 未测 |
| 提交边界 | 修复只涉及已跟踪文件 `numpy/lib/shape_base.py`，gold 投影的 `included_paths=["numpy/lib/shape_base.py"]`。pytest 产生的缓存被 `*.py[ocd]` 和 `.pytest_cache/.gitignore` 忽略；devcheck 跑完后 git status 仍只有原来的 2 行 | 实测 |
| 求解 | 真实模型、真实消息、经 adapter 的链路 | actor 待验 |

**镜像出处**：
- 评分侧 current 行的 4 次运行都在 `sha256:cb0ee55e…`（R-f 对账机）。
- devcheck 和私有 gold 对照在 `sha256:4bd9cf42…`。这是同一配方 `r2e_derive_v1`、同一个 tag 名的另一次构建，见 `attempt.json` 的 overlays（`derived9`）。
- 当前覆盖表的镜像上还没有隐藏测试的评分记录。

## 9. 候选（交协调者用正式评分代码实跑；都只改 `numpy/lib/shape_base.py` 里的 `tile`）

| 编号 | 改法 | 语义判断 | 预期得分 / 不符键 |
|---|---|---|---|
| A 合理替代解 | 把 :853 的 `copy=False` 改成 `copy=True`，即无条件复制，保留 `subok=True, ndmin=d` | 满足 R1–R4，R5、R7 不变。非全 1 路径多复制一次只是性能差异 | 1；没有不符键。用来确认评分里没有隐含的对象身份或性能检查 |
| B 部分实现（违反题面） | 在函数体最前面、`try:` 之前加 `if isinstance(reps, int) and reps == 1: return _nx.array(A, copy=True, subok=True)` | `tile(a, (1,))` 和 `tile(a, [1])` 仍共享内存，违反 "in all dimensions"。`tile(np.array(7), 1).shape` 变成 `()`，base 是 `(1,)`，违反 docstring 的维数规则 | 1（误放行）；没有不符键 |
| C 回归型错误实现（可选） | 在 `d = len(tup)` 之后加 `if all(x == 1 for x in tup) and isinstance(A, _nx.ndarray): return A.copy()` | 题面列的各种形式都不再共享内存。但 `tile(np.arange(5), (1, 1)).shape` 变成 `(5,)`，应为 `(1, 5)`（docstring :799-803）；0-d 输入同样丢了升维 | 1（误放行）；没有不符键 |

如果 B、C 得 1，说明 reward 只认证题面原例。可以考虑为诊断用途另加一组**不进 reward** 的补充检查：`(1,)`、`[1]`、`(1,1)` 的形状以及是否共享内存，还有 0-d 输入的形状。检查的依据只取题面和 docstring，不包括子类。要不要加由协调者和用户决定；本文不提议修改评分测试。

## 10. 缺口、建议队列与唯一下一步

1. **（唯一优先）** 在 `4bd9cf42…` 上一批跑 noop、gold、候选 A、候选 B（C 可选）。这样能在同一次构建上补齐 noop=0、gold=1 的证据，同时证实覆盖缺口。
2. 用真实模型、在真实消息下求解（清单 33–35）。对成功的补丁要检查：是否只修了标量 `reps=1`；有没有改 `numpy/testing/` 或根目录的 `conftest.py`。
3. **共享机制问题**（不逐题做）：隐藏测试的断言函数来自 `numpy/testing/utils.py`，候选可以改它，评分时又不重置。请协调者确认共享审查是否覆盖了"库自带的测试工具被候选改写"这种情况。如果没有覆盖，可以用一个"让 `assert_array_compare` 直接返回"的候选来验证（推断预期得 1）。
4. 登记 §7 的跨题关系，并向协调者反馈：机械比对会漏掉"上游后续重构过的修复"这一类关系。
5. 公开提示不进入模型消息，是链路级的事实（代码），影响所有 R2E 题。对本题影响小，只是可以恢复的开发摩擦。

## 11. 清单编号暂记（供后续 `screening_record.json`）

| 状态 | 编号 |
|---|---|
| pass | 1、2、4、6、8、9、10、11、13、14、16（gold 形态）、17、18、19、20、21、22、23（边界未约定）、24、27、29（git 与隐藏测试通道）、30（网络；模型记忆另记）、32 |
| issue | 5（跨题关系需登记，不是本题缺陷）；25（部分修复被放行，推断，待候选 B/C）；26（升维、0-d、子类无键保护，与 25 同源） |
| unknown | 3（真实消息；公开提示不进消息）；31（共享控制面通道） |
| not_applicable | 7、12、28、37 |
| not_checked | 15、33–36、38–40 |

## 附录 A：运行原件核对

| 运行 | 原件 | 结果 | 核对 |
|---|---|---|---|
| R-f noop（current） | `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:20`；日志 `…noop-n_aaa92dfe.eval.log` | 31/32，目标键 FAILED，reward 0，`keys_equal=true` | 日志的 sha256 与 `run_refs.json` 一致 |
| R-f gold | `ledger_r2e_all_gold.jsonl:20`；`…gold-n_5a904c89.eval.log` | 32/32，reward 1 | 同上 |
| 环境轮复跑 noop / gold | `runs/r2e_env_repair_20260924/_rerun2/ledger_{noop,gold}.jsonl:20`；`…rer_f84b2326` / `…rer_04c2baba` | 与 R-f 逐字相同，只差时间戳和耗时 | 同上 |
| M3 独立 runner gold ×2（来源镜像） | `runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:35,80` | 32/32 PASSED。来源镜像的 git 里能找到修复提交（`fix_reachable=commit`，refs 285，remotes 1） | 派生镜像已清理：devcheck 显示 `refs=0`、`remotes=0`、`reflog=0`，HEAD 没有子提交 |
| devcheck orig | `DC/orig/` | 6 条命令都是 rc 0；预检三项都是 ok | 真实 Claude Code 2.1.205 + 桩端点，`--max-turns 9` |
| 私有 gold 对照 | `DC/private_gold/private_control.json` | gold 干净应用；公开命令的输出见 §1 | root 身份 |

**评分侧条件**（来自 ledger）：用户 `rh2grader`，uid 54322；2 CPU / 4 GiB / `/tmp` 1 GiB；`network=deny_all`；`RH2_OBS_IMPORT_PATH=/testbed/numpy/__init__.py`。

**材料哈希**：
- `test_1.py` c032efe6…、`expected_output.json` 136e84d7…、`gold.patch` 9e91a9e4…、`run_tests.sh` 8285765f…，都与 grading bundle / validation bundle 一致。
- 日志里的 `RH2_SETUP_HIDDEN_TESTS_TREE` 与 `hidden_tests_tree_sha256` 一致。
- 题面里的提交号 `d770034969e3` 是 `base_commit` 的前缀。

## 附录 B：阅读范围

**读了**：
- 角色卡和四份方法文档；`public_read.md`。
- `PUB`：`user_prompt.txt`、`environment_brief.md`、`public_bundle.json`。
- 工作树：
  - `numpy/lib/shape_base.py:780-865`；
  - `numpy/lib/tests/test_shape_base.py`（与隐藏测试做了 diff）、`numpy/lib/tests/` 的文件列表；
  - `.gitignore` 的相关行；
  - `numpy/lib/function_base.py:836`（`copy` 的定义）、`numpy/testing/utils.py:1568-1596`（`assert_warns`）；
  - 全树 grep `tile(` 找调用者。
- `PRIV` 的全部文件。
- 附录 A 列出的账本行和日志。
- devcheck：命令清单、captures、prelaunch、activation、attempt、post_run_facts、stdout/stderr、Claude Code 版本、第一个桩请求（只看了系统提示和首条用户消息）、私有 gold 对照。
- 跨题比对文件：筛出与本题有关的行，外加首条样例。
- 同仓 6 题的公开包：题面开头、`setup.py` 里的版本号、`tile` 的实现、测试名 grep。
- RH2 源码：`envpack/bundles.py:282-289`、`envpack/ingest_r2e_subset.py:190-215`、`adapters/slime/generate.py`（grep 到 :219 和 :1976）、`taskset/swebench_smoke.py:95-120`。

**没读**：
- devcheck 的 `trajectory.jsonl`、`stub_log.json`、`stub_script.json`，以及其余 6 个桩请求（内容只是 devcheck 的脚本命令）。
- ledger 引用的远端 `diagnostics.json`。
- C 实现（`numpy/core/src/`）；`numpy/ma` 的复制语义。
- 同仓其它题的私有包和审查产物；任何历史调查。
