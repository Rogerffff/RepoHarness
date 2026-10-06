# numpy `a5ea773e` 修订方案与试跑验收（R-c，2026-09-29）

修订执行者（Claude 子代理，单题闭环试行）。按统一标准 v1 §5 的 R-c 模板执行；Codex 复核与正式材料由协调者负责。本文件是修订草案和试跑记录，**不是正式修订单**。

路径缩写（均相对仓库根）：

- `PUB` = `runs/r2e_static_prep_20260924/v3/public/numpy__a5ea773e66110cf335c9ed37e8ccdc14f8e56764`
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/numpy__a5ea773e66110cf335c9ed37e8ccdc14f8e56764`
- `CANDS` = `runs/r2e_actor_20260925/grader_cands`
- `GR` = `runs/r2e_actor_20260925/grader`
- `REV` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/numpy__a5ea773e66110cf335c9ed37e8ccdc14f8e56764`
- `GC` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/grader_candidates.md`
- `CX` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_batch2_review_20260925`
- `STD` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md`
- `trials/` = 本目录下的试跑结果

## 0. 结论

- **模板**：R-c，共两处窄修订，都加在隐藏测试 `test_1.py` 的目标测试 `TestTile.test_tile_one_repetition_on_array_gh4679` 里。**期望映射不变**（32 键全 PASSED）。
  - 第 1 处（本包指派，v1 §4 第 2 步，T2c）：补元组形式的全 1 `reps`，即 `(1,)` 与 `(1, 1)`，检查修改结果不影响输入。它堵住 B（只处理整数 1）和 RC2（只在 `tup == (1,)` 时复制）。
  - 第 2 处（v1 §4 第 4 步另列的 S1，仍在元组 `reps` 范围内）：全 1 且 `len(reps) > A.ndim` 时，结果形状要按 docstring 升维（`(1, 1)` → `(1, 5)`）。它堵住 C 与 RC3：这两个候选直接返回不升维的副本。v1 §11 只写了“元组 reps”；两处 edit 锚点不同，可以单独拿掉第 2 处（后果见 §5 末）。
- **试跑（同一镜像，一轮修订、一轮验收，已收敛）**：
  - 正对照 gold 为 1，合理替代解 A（无条件复制）为 1。
  - noop、D、B、RC2、C、RC3 都为 0，各自失败在预期的断言行。
  - 四个触发反例 B、RC2、C、RC3 在同镜像的原版材料上都是 1（`trials/cur_*.json`），修订后变 0。
- **不需要用户决定**。剩余覆盖缺口按 T3 登记（§6）。

## 1. 父版本与试跑环境

- **父版本**：`PRIV/hidden_tests/test_1.py`，sha256 `c032efe66357041e5e913a61a8b1a3a4fc432c6f54da747ea251633e0aef4120`（与 `grading_bundle.json` 一致）。`PRIV/expected_output.json` 32 键全 PASSED，`material_revisions` 为空。
- **修订后**：`test_1.py` 的 sha256 为 `c068c691f51d651859cbeb0b61ab3bb8a412a1921c8acad29454c62fb43830e5`（本机按 §3 的 edits 替换，并用 `ast.parse` 检查语法）。
- **镜像**：`sha256:22b7741c5263cc27bfaa4c491a98a62fbfc9c697902223c268890566afe4164c`，配方 `r2e_derive_v1+sysconfig_v1`。
- **试跑工具**：`rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`，不是正式评分（差别见文件头第 8–9 行）。
- **当前材料确认**：`trials/cur_noop.json` 为 mismatch，唯一不符键是目标键，失败值 `array([2, 3, 4, 5, 6])` 与题面一致；`trials/cur_gold.json` 为 match。

## 2. 要纠正的误判与公开依据

### 2.1 第 1 处：元组形式的全 1 `reps`（T2c，v1 §4 第 2 步）

- **误判**：目标断言只用了题面示例，即 1-D 数组配整数 `reps=1`（`PRIV/hidden_tests/test_1.py:327-331`）。按复核者的说法，它只检验了 `tup == (1,)` 且输入为 1-D 这一个点（`REV/review.md` §3）。下面两个候选在原版都得 1：
  - B 只特判 `isinstance(reps, int) and reps == 1`。`tile(a, (1,))`、`tile(a, [1])`、`tile(a, (1, 1))` 仍与输入共享内存。
  - RC2 是 `copy=(tup == (1,))`。`tile(a, (1, 1))` 仍共享内存。

  证据：`GC:44`、`GC:46` 为 32/32，`GC:158-170` 是语义表；本次同镜像 `trials/cur_B.json`、`trials/cur_RC2.json` 为 match。
- **公开依据**：
  - 题面说的是“所有维度上的重复因子都为 1”（`PUB/user_prompt.txt:4`、`:7`），期望是“每个 tile 结果都是输入的独立副本”（`:21`）。示例只是其中一种写法。
  - docstring 把 `reps` 定义为 array_like，即“沿各轴的重复次数”（`PUB/worktree/numpy/lib/shape_base.py:813-814`），所以元组是 `reps` 的一般写法。
  - base 对元组 `reps` 走同一条路径：`tuple(reps)`，然后 `copy=False` 加 `ndmin=d` 得到视图，因子为 1 时跳过 `repeat`（`shape_base.py:848-853`、`:859-860`、`:865`）。所以元组 `reps` 下有同一个别名问题。
- **检查方式**：沿用目标测试的写法，`b += 2` 之后断言 `a` 不变，也就是检查实际的变异隔离。这里不用 `may_share_memory`，也不看对象身份（`CX/numpy_pillow/README.md:105`）。

### 2.2 第 2 处：全 1 且需要升维时的文档形状（v1 §4 第 4 步，S1）

- **误判**：C（全 1 时 `return A.copy()`）与 RC3（全 1 时 `return _nx.array(A, copy=True, subok=True)`，不传 `ndmin`）都返回副本，所以能通过第 1 处的变异隔离检查。但 `tile(np.arange(5), (1, 1))` 在它们下的形状是 `(5,)`，不是文档规定的 `(1, 5)`；0-d 输入配 `1` 的形状也变成 `()`（`GC:158-170`）。两者在原版都得 1（`GC:45`、`GC:47`；同镜像 `trials/cur_C.json`、`trials/cur_RC3.json` 为 match）。
- **公开依据（有文档的公开行为）**：
  - docstring 规定结果维数是 `max(d, A.ndim)`（`PUB/worktree/numpy/lib/shape_base.py:796-797`）。`A.ndim < d` 时，在前面补轴升维，例如 (3,) 在二维复制时升为 (1, 3)（`:799-801`）。
  - 公开测试 `tile(a, (1, 2))` 得 `[[0, 1, 2, 0, 1, 2]]`，也体现了元组 `reps` 下的升维（`PUB/worktree/numpy/lib/tests/test_shape_base.py:321`）。
  - 题面只要求“复制”，没有要求改变形状。gold 保留了 `ndmin=d`。
- **判级**：已有的构造候选得 1，同时破坏了有文档的公开行为 → S1（`STD:97`）。Codex 第二批复核也把 C、RC3 记为“破坏公开 docstring 约定的升维”（`CX/numpy_pillow/README.md:17`；逐题裁定 `CX/README.md:85`）。v1 §5 要求多个 S1 逐个列出、合并在同一轮修订（`STD:126`）。

## 3. 具体改动（`r2e_tests/test_1.py`，`TestTile.test_tile_one_repetition_on_array_gh4679`）

修订后的完整函数如下；标 `+` 的是新增行：

```python
    def test_tile_one_repetition_on_array_gh4679(self):
        a = np.arange(5)
        b = tile(a, 1)
        b += 2
        assert_equal(a, np.arange(5))
+       # all-ones reps given as a tuple
+       for reps in [(1,), (1, 1)]:
+           a = np.arange(5)
+           b = tile(a, reps)
+           b += 2
+           assert_equal(a, np.arange(5))
+
+       # len(reps) > A.ndim: A is promoted as documented
+       assert_equal(tile(np.arange(5), (1, 1)).shape, (1, 5))

    def test_empty(self):
```

- 条目格式见 `revision_draft.json` 的 `revisions`：一条 `hidden_test_text_replace`，含两个 edit。
  - 第 1 个 edit 以原例的 `b += 2` 与 `assert_equal(a, np.arange(5))` 两行为锚点。
  - 第 2 个 edit 以 `def test_empty(self):` 为锚点，把断言插在它前面，仍属目标测试的函数体。
  - 两个锚点在父版本里各出现一次，可以单独应用。
- 修订后第 332–337 行是第 1 处，第 339–340 行是第 2 处。新增代码只用 ASCII 字符，沿用文件已导入的 `tile` 与 `assert_equal`。

## 4. 期望映射的逐键变化

**无变化。** 仍是 32 键，全部 PASSED。新断言都在已有的目标测试里，没有新增、删除或改名测试。

## 5. 验收计划与试跑结果

全部在 §1 的镜像上运行，带修订草案，`--expected current`。

| 候选 | 补丁 | 应得 | 应在何处失败 | 试跑 | 实际 |
| --- | --- | --- | --- | --- | --- |
| gold（正对照） | `PRIV/gold.patch` | 1 | — | `trials/rev_gold.json` | match（32/32） |
| A：无条件复制（合理替代解，查误拒） | `CANDS/numpy_a5ea_A_always_copy.patch` | 1 | — | `trials/rev_A.json` | match |
| noop | 无 | 0 | 第 331 行（原例） | `trials/rev_noop.json` | mismatch；第 331 行，`x: array([2, 3, 4, 5, 6])` |
| D：按对象身份判断（已知错误，原版就是 0） | `CANDS/numpy_a5ea_D_identity_check_negative.patch` | 0 | 第 331 行 | `trials/rev_D.json` | mismatch；第 331 行 |
| B：只处理整数 1（触发反例，原版 1） | `CANDS/numpy_a5ea_B_scalar_one_only.patch` | 0 | 第 337 行，`reps=(1,)` | `trials/rev_B.json`；原版 `trials/cur_B.json` 为 match | mismatch；第 337 行，`a` 变成 `[2 3 4 5 6]` |
| RC2：`copy=(tup == (1,))`（触发反例，原版 1） | `CANDS/numpy_a5ea_RC2_copy_if_tup_is_1.patch` | 0 | 第 337 行，`reps=(1, 1)` | `trials/rev_RC2.json`；原版 `trials/cur_RC2.json` 为 match | mismatch；第 337 行 |
| C：全 1 时 `return A.copy()`（触发反例，原版 1） | `CANDS/numpy_a5ea_C_all_ones_return_copy.patch` | 0 | 第 340 行（形状） | `trials/rev_C.json`；原版 `trials/cur_C.json` 为 match | mismatch；第 340 行，形状长度 1 对 2 |
| RC3：全 1 时提前返回、不传 `ndmin`（触发反例，原版 1） | `CANDS/numpy_a5ea_RC3_early_return_no_ndmin.patch` | 0 | 第 340 行（形状） | `trials/rev_RC3.json`；原版 `trials/cur_RC3.json` 为 match | mismatch；第 340 行 |

- 行号按修订后的文件计。所有 mismatch 的唯一不符键都是 `TestTile.test_tile_one_repetition_on_array_gh4679`（PASSED → FAILED），其余 31 键不变。补丁都应用成功，修订都已应用（`RH2_APPLY_RC=0`、`RH2_TRIAL_EDITS_APPLIED=1`）。
- B 与 RC2 都失败在循环体的同一行（第 337 行）。两者分别在哪一轮失败，是按补丁源码推断的：B 对元组不生效，所以在 `(1,)` 那一轮失败；RC2 对 `(1,)` 会复制，所以在 `(1, 1)` 那一轮失败。日志只给出行号。
- C 与 RC3 通过了第 1 处（它们确实返回了副本），只在第 2 处失败。这说明两处各自堵住了不同的错误。
- **对照 v1 §5 的验收条目**：
  - 正对照为 1、noop 为 0：满足。
  - 要纠正的误判已纠正：B、RC2、C、RC3 都从 1 变为 0。
  - 已知相关错误候选仍为 0：D。
  - 合理替代解没有被误拒：A。
  - 父版本、新版本、理由和触发反例：见 §1、§2。
  - Codex 复核：待协调者发起。
- **只采纳第 1 处时**：由静态推断，gold、A 仍为 1，noop、D、B、RC2 为 0，但 C、RC3 回到 1（第 1 处的变异隔离检查它们能通过）。这个组合没有单独试跑。

## 6. 修订后受保护的公开要求，以及仍未覆盖的部分

**受保护（有直接断言）**：

- 题面原例：1-D 数组配整数 1；
- 元组形式的全 1 `reps`，包括 `(1,)` 和需要升维的 `(1, 1)`，结果与输入之间有变异隔离；
- `(1, 1)` 的结果形状按 docstring 为 `(1, 5)`；
- 非全 1 路径的值与形状（`test_basic`、`test_empty`、`test_kroncompare`），以及同文件其余 28 个回归键。

**仍未覆盖，按 T3 登记，不在本轮修订内**：

- 0-d 输入配 `1`（按 docstring 应为 `(1,)`）；
- 2-D 输入配整数 `1`（`reps` 前补 1）；
- list 形式的 `[1]`，以及 `np.int64(1)` 这类非 Python int 的 `reps`（`REV/review.md` §4 第 1 条）。

已知候选在这些输入上的错误都已被本次断言在别处拦下，没有已跑候选只在这些输入上出错。子类保持（R7）、空 `reps`（R4）题面没有约定，不纳入。探针后检可以继续复用协调者已有的 `tile_semantics` 命令（`CANDS/numpy_a5ea_extra_commands.json`，六种全 1 情形）作不计分的诊断。

**X1**：本题修复的重构版本和目标测试出现在同仓 6 道较新 numpy 题的公开工作树里（`REV/card.md` §4 第 2 条）。本次修订不改变这层关系；留出划分按 D3 以仓库为单位。

## 7. 交协调者

- 正式材料：把 §3 的两个 edit 写进 `s2_r2e` 下的正式修订单（`hidden_test_text_replace`，`test_1.py`），期望映射不变。然后做派生镜像的材料步骤，在正式评分上复跑 gold、A、noop、D、B、RC2、C、RC3，并交 Codex 复核。本执行者没有写正式修订单与 pins，也没有改生产代码。
- 远端只执行了本包允许的命令：`mkdir`、`scp`、`trial_grade.py`，同一时间最多 2 个试跑。试跑目录是 `/work/r2e/trials/numpy/a5ea773e/`。
