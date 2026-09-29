# numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb：独立复核初判（第一步）

2026-09-25 · 独立复核者（静态审查）。本文在读公开读者产物、主审产物和历史引用之前保存。我只做了静态阅读和既有证据核对，没有运行项目代码或容器，也没有修改任何原件。

路径简写：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb`
- `PRI` = `runs/r2e_static_prep_20260924/v3/private/numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb`
- `DEV` = `runs/r2e_actor_20260925/devcheck/numpy__5e8301c2b36097dd8be5a12e0bb4369a1`
- `EF` = `PUB/worktree/numpy/core/einsumfunc.py`（base 版本）
- `HT` = `PRI/hidden_tests/test_1.py`
- `L_NOOP` = `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-n_a9fdcb72.eval.log`，`L_GOLD` = 同目录下的 `evallog_replay-r2e-rf-all-gold-n_b4799438.eval.log`

## 0. 初判摘要

1. **题面、材料和评分彼此一致。** noop 的全部 15 个目标键都报出题面原文里的错误。当前材料下，gold 两轮都是 35/35，noop 两轮都是 20/35。
2. **15 个目标键实际只测同一组断言。** `HT:484-490` 位于 `check_einsum_sums` 末尾，15 个 `test_einsum_sums_*`（`HT:492-539`）各调用一次。这组断言只测题面原例本身：p=(10,2) 在前，q=(1,2) 在后，`optimize=True`。
3. **漏测（中）：没测单例操作数在前的情况。** 有一种部分修复只在"后出现的尺寸为 1"时跳过检查（§6 候选 C）。静态推断它能得 1，但把操作数顺序交换后，它仍会抛出题面原来的错误。
4. **gold 只修了题面泛述中的一部分（中，有执行证据）。** 如果被求和的标签在某一侧尺寸为 1，而这一步又选用了 `tensordot`（例如 `'ij,jk->ik'`，形状 (2,3) 与 (1,4)），gold 仍会抛 `ValueError: shape-mismatch for sum`（私有 gold 对照实测）。同仓较晚题目的公开工作树显示，上游后来另加了 `broadcast_indices` 逻辑（注释为 "If we're broadcasting, nix blas"）。隐藏测试不覆盖这个变体，所以更完整的修复静态上也预计得 1。
5. **gold 新报错文案中的两个尺寸填反了。** 私有对照实测：operand 1 的形状是 (3,2)，文案却写 `operand 1 (10) ... previous terms (3)`。没有测试检查文案，不影响评分。
6. **期望映射的 35 个键全是 PASSED，没有非 PASSED 键。** 所以不存在"更完整修复把 FAILED 翻成 PASSED、反而被判 0"的情况。静态阅读未发现误拒迹象。
7. **开发条件：** devcheck 在镜像层面实测，能复现原错误，也能跑公开测试文件（35 passed）；这个文件与隐藏测试中的回归键来源相同。真实模型实际收到的题面消息没有捕获：devcheck 使用的是合成用户消息。devcheck 和当前评分记录用的不是同一个镜像 ID，而是同一配方的重建镜像。
8. **同仓关系：** 本题 gold 逐字出现在 `numpy__43e333e2` 和 `numpy__d89bc4bb` 的公开工作树里，这两个工作树还包含第 4 条提到的后续修正。本题工作树则包含 `18b7cd9d`、`2f4a9650`、`d805e9b6` 的修复。这几题的题面都与 einsum 无关，不构成同问题簇。

五类问题：
- 漏测：有两条（交换顺序；BLAS 变体，gold 本身也不修）。
- 误拒：未发现（静态）。
- 错误回归：未发现（gold 文案退步不影响计分）。
- 材料错配：未发现。
- 开发缺口：没有阻塞项；三项需 actor 验证（见 §7）。

**暂定处置：** 可作开发诊断候选，状态 `needs_review`（静态候选，待 actor 验证），并附"测试偏松"和"gold 对泛述覆盖不完整"两条记录。**唯一优先下一步：** 用正式评分代码同批实跑候选 C 和 D（§6）。

## 1. 实际读取范围

**角色卡与方法文档**
- `roles/reviewer_r2e.md` 全文。
- `roles/investigator_r2e.md`：工具显示了全文，但我只采用"R2E 的评分口径""材料""第二批补充规则"三节作为口径。
- `quality_review_protocol_20260920.md`、`r2e_environment_card.md`、`record_template.md`。
- 40 项清单没有读。

**公开包**
- `user_prompt.txt`、`environment_brief.md`、`public_bundle.json`；`worktree_manifest.json` 只看了汇总字段和 4 个文件条目。
- 工作树中的文件：
  - `EF` 第 1–900 行和第 1040–1146 行；第 900–1040 行是 docstring 示例，只略读。
  - `numpy/core/tests/test_einsum.py`：与 `HT` 做了 diff，另 grep 了 `optimize`。
  - `numpy/conftest.py` 全文、`pytest.ini`、`run_tests.sh`、`numpy/testing/__init__.py` 的导入行。
  - `numpy/core/numeric.py`：grep 到第 1289 行。
  - `doc/release/1.14.0-notes.rst`：grep `einsum`；`1.15.0-notes.rst`：grep 无命中。
  - 为核对跨题关系，grep 了 `numpy/lib/npyio.py`、`numpy/lib/polynomial.py`、`numpy/ma/core.py`。

**私有包**
- `HT` 全文、`hidden_tests/__init__.py`、`expected_output.json`、`gold.patch`、`run_tests.sh`、`revisions.json`（内容为 `[]`）、`run_refs.json`、`grading_bundle.json`、`validation_bundle.json`。
- 核对结果：`HT` 与 bundle 中的摘要一致；gold.patch 的 sha256 与账本 `candidate.patch_sha256` 一致（`4bf839c2…`）。

**运行原件（均为 `material=current`）**
- 四个账本各自的第 19 行：R-f noop/gold，以及环境轮 `_rerun2` 的 noop/gold。
- `L_NOOP`：头部、全部 FAILURES 定位行、short summary。`L_GOLD` 全文。
- `_rerun2` 的两份日志与 R-f 的两份逐行 diff：去掉对象地址和时间戳后完全相同。
- `independent_reference` 中 M3 的两份日志：只看了 summary 行（来源镜像，都是 35 passed）。

**devcheck**
- `orig/` 下：`commands_with_preflight.json`、`captures/*.out`（全部 6 份）、`prelaunch.json`、`attempt.json`、`activation_check.json`、`bringup_artifacts/cc_version_observed.json`、`post_run_facts_root.txt`、`devcheck_stdout.json`（字段）。
- `stub/requests/messages_000.json`：只看了用户消息和 system 中的关键词。
- `private_gold/private_control.json`、`stdout.log`。
- 没读：`harness/trajectory.jsonl`、其余 stub 请求、stderr。

**跨题材料**
- `cross_task_gold_scan.json`：method 字段和涉及本题的 5 对。
- 同仓 6 题 `public_bundle.json` 中的 base 和题目。
- `numpy__43e333e2` 工作树的 `einsumfunc.py`：读了约第 850–960 行，另做 grep；`numpy__d89bc4bb` 的同一文件：只做 grep。

**暂存区操作**
- 把 gold.patch 应用到 `EF` 的临时副本上，做了 `git apply --check` 和 `git hash-object`。前像 blob `f382b6a901`、后像 blob `280247ecde` 都与补丁头一致。没有执行任何 numpy 代码。

**没读**
- `OUTPUT_DIR` 中的其它文件，包括 `public_read.md`。devcheck 命令来自它，我只看到了命令本身。
- 任何 `history/` 目录；`docs/.../r2e_env_repair_20260924/`；首批审查目录、Codex 复核目录、其它 review 目录。
- 本批 README 和 `assignments.json`；`runs/` 下的分析和汇总文件；其它题的私有包。

## 2. 八方面

1. **公开需求（清单 3、23）**
   - 题面（`user_prompt.txt:4-27`）要求：`optimize=True` 时，含单例维（尺寸为 1 的维度）的操作数应按广播处理；原例输出形状为 (2,)；不应再抛 `Size of label 't' for operand 1 does not match previous terms.`。
   - 这段报错文本 grep 一次就能定位到 `EF:710-712`。
   - base 的 `einsum` 默认 `optimize=True`（`EF:1062`；1.14.0 release notes 第 453–458 行写明默认开启优化），所以不传 optimize 的调用同样会触发这个 bug。题面没有提到这一点，也不要求改默认值。
   - 没有新 API 名，没有文案要求，也没有互相冲突的多个目标。
2. **材料与初始问题（1、2、27）**
   - base、`public_bundle` 和镜像 HEAD 都是 354ac25（`prelaunch.json` 中的 `GIT_HEAD`）；`initial_diff` 为空；包版本为 1.15.0.dev0+354ac25（账本 `observations`）。
   - 两份评分日志中的 `RH2_SETUP_HIDDEN_TESTS_TREE=d8853bba…` 等于当前材料哈希。
   - 出错路径：`einsum` → `einsum_path(einsum_call=True)`（`EF:1088-1089`）→ 尺寸一致性检查（`EF:706-714`）抛错。
   - 执行证据：noop 的 15 段失败都是 `HT:487` → `EF:1089` → `EF:712`，报的就是题面原文（`L_NOOP:34-36,226-228` 等，15 段内容一致）。actor devcheck 的 `captures/pr1_1_cmd.out:1-7` 也复现了同一错误。
   - gold 的前像与工作树文件一致。
3. **测试是否测到要求（18–20、25、32）**
   - `HT:487-490` 有两条断言：结果等于 `optimize=False` 的结果，也等于 `[10.]*2`。这个值可以从原例直接推出。
   - 断言只覆盖原例的一种操作数顺序和 `optimize=True`。详见 §3。
4. **是否误拒合理解（24、28）**
   - 期望映射全是 PASSED。目标断言只比较数值；`assert_raises` 只检查异常类型，不检查文案；没有断言依赖 gold 的内部实现。
   - `TestEinSumPath`（`HT:805-908`）断言精确的收缩路径，但这是公开的既有测试，只修改尺寸检查不会影响它。
   - 更完整修复 D、另一条路线 E，静态预测都得 1（§6）。
   - 若候选在修复的同时把默认 optimize 改回 False，静态看也不会让任何键翻转：不传 optimize 的调用改走 `c_einsum`，结果相同。
5. **回归与 gold 完整性（26、27）**
   - 回归键就是公开测试文件的原样内容：`HT` 与公开的 `test_einsum.py` 只差 `HT:483-490` 这 8 行。它们覆盖视图、各 dtype 求和、广播、错误输入和 path 选择。
   - 跨操作数的"真正不兼容尺寸仍报错"没有直接回归测试，只有单操作数的 `'ii'` 类用例（`HT:82-86`）。不过 gold 和各合理候选都会在下游 `c_einsum` 或 `tensordot` 中抛 ValueError。gold 的其余检查见 §5。
6. **agent 的开发条件（6–15）**：见 §7。
7. **交付与评分边界（4、16–17、21–22、29–31）**
   - 修复文件 `numpy/core/einsumfunc.py` 在 gold 记录的 `projection.included_paths` 中；`candidate_test_like_paths=[]`。
   - 隐藏测试只依赖 `numpy` 和 `numpy.testing`，不引用仓库自己的测试辅助代码。
   - 测试搬迁后，`numpy/conftest.py` 不再作用于 `r2e_tests/`。这个 conftest 提供 FPU 检查 fixture 和 `--runslow` 选项，还把 `numpy.testing.utils/decorators` 换成 pytest_tools 版本。`HT` 没有 slow 标记，也没有装饰器；评分运行 35/35，说明对本题没有影响。
   - 公开工作树里没有答案：grep 不到 gh-10343，公开测试文件也不含目标断言。
   - 候选改 `numpy/testing`，或在 `/testbed` 放一个 conftest，属于 R2E 通用边界问题，不是本题特有的。
8. **题目关系与用途（5、29–30、37–40）**：见 §8。

## 3. 需求—断言双向映射

| 需求或旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖情况 | 执行证据或下一步 |
| --- | --- | --- | --- | --- |
| 原例：`'ti,ti->i'`，(10,2) 在前、(1,2) 在后，`optimize=True` 不报错，输出形状 (2,) | `user_prompt.txt:10-21` | 15 个 `test_einsum_sums_*` 经 `HT:487-490` | 覆盖 | noop 15 键都在 `HT:487` 报题面原错；gold 35/35 |
| 单例在前（交换顺序） | 题面泛述 `user_prompt.txt:7` | 无 | 缺失 | gold 实测通过（私有对照 pr3）；候选 C 可以区分 |
| 被求和标签一侧为 1、且这一步走 `tensordot` | 题面标题和泛述 `:4,7` | 无 | 缺失（gold 也不修） | 私有对照：gold 仍报 `shape-mismatch for sum`；候选 D |
| `'greedy'`/`'optimal'`/显式 path、`np.einsum_path` API 在单例输入下的行为 | 题面只写了 True；docstring `EF:555-575` | 无（单例只测了 True） | 缺失（弱） | gold 修在共享路径上；私有对照中交换顺序在 greedy/optimal 下都 OK |
| 真正不兼容的尺寸仍报 ValueError | 旧行为 | `test_einsum_errors`（`HT:82-86`，仅单操作数） | 部分 | gold 实测仍报 ValueError（私有对照 pr3 末行） |
| 报错文案 | 无公开要求 | 无 | 不适用 | gold 文案中两个数颠倒（§5） |
| 既有 einsum 行为（views、sums、misc、broadcast、path） | 公开测试文件 = `HT` 去掉 484–490 行 | 20 个回归键，加上 sums 中的其余断言 | 覆盖 | noop 和 gold 都是 PASSED |

反向核对：`HT:487-488` 的依据是题面"应按广播处理"加原例；`HT:489-490` 的值 10 可以从 `np.ones` 在 t 维上求和直接推出；精确路径断言来自可见的既有测试。没有哪条断言只能靠读隐藏材料才知道。

## 4. R2E 专项

- **(a) 非 PASSED 键：** 无，35 键全是 PASSED。
  - 更完整修复 D 会让一部分 `optimize=True` 的 n=1 收缩从 `tensordot` 改走 `c_einsum`，涉及 `HT:506,510,526,533`（i4/u4/f8/c8 在 `do_opt=True` 下）。
  - 这些用例的数据都是小整数，两条路径的结果精确相同，静态预测不会有键翻转。
  - 如果实跑得 0，先看这四个键和 `test_einsum_misc`。
- **(b) 题面报错：** 逐字出现在 noop 的全部 15 个目标键里。`L_NOOP` 第 226、430、634、…、3082 行的 `E ... ValueError: Size of label 't' for operand 1 does not match previous terms.` 都定位到 `EF:712`；`_rerun2` 相同。
- **(c) 泄漏：**
  - 题面给了原例和原报错，报错文本可以直接定位到 `EF:710`。"broadcasting should allow singleton dimensions" 说明了修复的语义方向，但没有给代码，也没有给字典更新规则。
  - 我的判断：这是很强的定位线索加上语义层面的修法提示，不算泄漏修法。
  - 隐藏测试注释中的 gh-10343 不在公开材料里。容器不出网，HEAD 没有子提交（`DEV/orig/captures/r2e_preflight.out:1-3`）。
- **(d) 测试支撑与撞键：** 隐藏测试是单个文件加一个空 `__init__.py`，不导入仓库测试模块，没有跨文件撞键。搬迁丢掉 `numpy/conftest.py` 的影响见 §2 第 7 方面。
- **(e) 时间、随机、资源：**
  - `optimize_compare`（`HT:691-704`）、`build_operands`（`HT:785-794`）和 `HT:651` 使用未设种子的随机数。
  - `optimize_compare` 用 `assert_almost_equal` 默认 7 位（绝对误差），数值量级小，失败风险低。
  - `HT:651` 用同一个 x 的两种取法做比较，结果是确定的。
  - 没有计时断言。评分内存峰值约 0.5 GB，测试耗时 1–2.5 s。
  - 我读到的 8 次运行（noop×2、gold×2、M3×2、devcheck 公开测试×2）中，这些键全部通过。
- **(f) 修订：** 无（`revisions.json=[]`，`material_revisions=[]`）。

## 5. gold 检查

- **改动：** 只改了 `EF:709-712`。原逻辑是"尺寸不等就报错"；新逻辑是：已记录的尺寸为 1 时，改记为当前尺寸；当前尺寸既不是 1、也不等于已记录尺寸时才报错。同时改写了报错文案。单文件 +6/−4，没有无关改动。
- **原例：** 修好了。证据：`L_GOLD:27-61` 全部 PASSED；私有对照 `pr1_1_cmd` 输出 `[10. 10.] (2,)`。
- **交换顺序：** 修好了。私有对照 pr3 显示 `OK ti,ti->i [(1, 2), (10, 2)]`，在 True、greedy、optimal 下都通过。
- **未修的同类情形：**
  - 条件：被求和的标签在某一侧尺寸为 1，而且 `_can_dot` 选中了 BLAS。路径是 `EF:772` → `EF:1105-1122` 的 `tensordot`。gold 只放行了尺寸检查，`tensordot` 仍在 `numeric.py:1289` 抛 `shape-mismatch for sum`。
  - 执行证据：私有对照 pr3 中，`'ij,jk->ik'`（(2,3)、(1,4)）和 `'ij,jk,kl->il'`（(2,3)、(1,4)、(4,5)）在 True、greedy、optimal 下全部 ERR；同样的输入用 `optimize=False` 算得出结果（脚本只有参考值计算成功时才会打印 ERR 行）。
  - 原例不受影响：`'ti,ti->i'` 两侧保留同一个 `i`，`_can_dot` 在 `EF:334` 返回 False，于是走 `c_einsum`。
  - 我的定性：题面标题和描述是泛述，这个变体字面上属于同一现象；但题面的示例和 Expected Behavior 只涉及原例。所以记为"gold 对泛述覆盖不完整"。影响是 reward=1 不能证明这类输入已经修好。它不影响合理解得分，不能据此判定题目不可用。
- **报错文案：** 格式参数 `% (char, tnum, dimension_dict[char], dim)` 把已记录尺寸填进了 "operand %d (%d)"，把当前操作数的尺寸填进了 "previous terms (%d)"，两个数正好颠倒。私有对照 pr3 末行 `Size of label 't' for operand 1 (10) does not match previous terms (3).` 可以证实：operand 1 的形状是 (3,2)。没有测试检查文案。
- **旧行为：** gold 只放宽了原本会报错的输入。原本合法的输入，尺寸字典、路径和 BLAS 选择都不变，未发现回归。唯一的小退步：对上面的 BLAS 变体，报错从清楚的标签尺寸错误变成了较含糊的 `shape-mismatch for sum`。

## 6. 可区分候选（供协调者用正式评分实跑）

- **C：顺序相关的部分修复（可能蒙混过关）**
  - 改法：把 `EF` 中 `einsum_path` 第 709 行的 `if dimension_dict[char] != dim:` 改成 `if dimension_dict[char] != dim and dim != 1:`；不更新字典，其余不动。
  - 预期：35/35，reward 1（静态推断，高置信）。
  - 同一容器里再跑 `np.einsum('ti,ti->i', np.ones((1,2)), np.ones((10,2)), optimize=True)`，预期仍抛题面原错。
  - 结论含义：如果得 1，就证实"单例在前"确实漏测。
- **D：更完整的修复（合理替代解）**
  - 改法：在 gold 基础上，把较晚公开工作树 `numpy__43e333e2/worktree/numpy/core/einsumfunc.py` 约第 857–883 行、第 928–950 行的 `broadcast_indices` 逻辑移植到 base 的 `einsum_path`：
    - 尺寸循环里，把 `dim == 1` 的标签记入该操作数的 broadcast 集合；
    - 收缩循环里，随 `input_list.pop(x)` 同步执行 `bcast |= broadcast_indices.pop(x)`；若 `idx_removed & bcast` 非空，设 `do_blas = False`，否则照旧调用 `_can_dot`；
    - 中间结果对应追加 `bcast - idx_removed`。
    - 不移植 `_flop_count` 等无关改动。
  - 预期：35/35，reward 1（静态推断，中高置信）；同时能修好 `'ij,jk->ik'`（(2,3)、(1,4)）和三操作数的例子。
  - 如果得 0：先看 `test_einsum_sums_int32/uint32/float64/cfloat64` 和 `test_einsum_misc`。
  - 结论含义：得 1 说明更完整的修复不会被误拒；得 0 则属于误拒，需要逐键分析。
- **E：另一条修复路线（可选）**
  - 改法：不动尺寸检查，改 `EF:1088-1089`。用 `try` 包住 `operands, contraction_list = einsum_path(...)`，`except ValueError` 时 `return c_einsum(*operands, **kwargs)`。此时 `kwargs` 已去掉 optimize，仍保留用户传入的 out/dtype/order/casting。
  - 预期：35/35，reward 1（静态推断，中置信；主要看 `test_einsum_errors` 里各个异常类型是否保持不变）。
  - 行为：`np.einsum` 在 BLAS 变体上也能算出结果；但 `np.einsum_path` 对单例输入仍会报错（题面没有要求）。
  - 结论含义：确认"绕开优化"这种合法路线同样会被接受。

## 7. 开发需求

| 项 | 需求 | 证据级别 |
| --- | --- | --- |
| 导入 | 在 `/testbed` 下运行；`python` 是 `/testbed/.venv/bin/python`；导入的是 `/testbed/numpy`（1.15.0.dev0+354ac25） | 镜像层面实测：`DEV/orig/captures/env.out:1-5`（agent 54321，经真实 Claude Code 2.1.205 的 Bash 执行） |
| 依赖与构建 | 纯 Python 修改，不需要重编 C 扩展，也不需要新包；pip 不存在（`env.out:6`），但用不到 | 实测 + 静态 |
| 资产与网络 | 不需要；容器只通 relay，外部 DNS 被拒（`prelaunch.json` 的 probe_facts） | 实测 |
| 权限 | agent 可写 `/testbed`（`WORKDIR_WRITABLE=1`，属主 54321）；`/rh2/bash_env` 不可写 | 实测 |
| 复现 | 公开读者的 `python -c` 命令能复现原错误（`pr1_1_cmd.out:1-7`）；pr3 的四类例子在 base 下全部报原错（`pr3_3_cmd.out:1-14`） | 实测 |
| 测试 | `python -m pytest numpy/core/tests/test_einsum.py` 得 35 passed，用时 0.53 s（`pr4_4_pytest.out:12`）；这个文件就是隐藏测试去掉目标块，解题时可以自测全部回归键 | 实测 |
| 资源 | 默认 2 CPU、4 GiB、`/tmp` 1 GiB 足够；评分时内存峰值约 0.5 GB | 评分侧实测 |
| 提交边界 | 修改 `numpy/core/einsumfunc.py`，在投影范围内 | 评分侧实测（gold 记录的 projection 字段） |
| actor 待验 | 模型实际收到的题面和 public_hints：devcheck 的用户消息是合成的 "Devcheck run: execute exactly the tool calls you are given, then stop."（`stub/requests/messages_000.json`）；经 Qwen adapter 的链路；真实模型求解 | 未知 |
| 镜像一致性 | devcheck 和私有对照用的是 `d0b59d8b…`（`attempt.json` 的 overlay 来自 `/work/b_r2e/derived9/overlays.jsonl`，`recipe_id` 和 `derived_image_ref` 与评分记录相同）；当前四条评分记录用的是 `b72f0fc4…`。两边的环境事实一致（Python 3.7.9、numpy 版本串、pytest 7.4.4、HEAD、初始 porcelain），但在我可读的范围内，`d0b59d8b` 上没有隐藏测试的评分记录 | 缺项（影响低） |

## 8. 题目关系

- **本题修复已在另两题的初态里（机器比对结论已核实）。** 本题 gold 新增的 6 行逐字出现在两个同仓题目的公开工作树中：
  - `numpy__43e333e2`（题目：`np.ma.average` 的 NaN 权重）：`einsumfunc.py` 第 873–877 行。
  - `numpy__d89bc4bb`（题目：`histogram2d` 的 density 参数）：同一文件第 866–870 行。
  - 这两个工作树还含后续的 `broadcast_indices` 修正（43e333e2 第 857–950 行；d89bc4bb 第 850–944 行）。einsum 的默认值也已改变：43e333e2 第 998 行是 `optimize=False`，d89bc4bb 第 1323 行是 `len(operands) > 3`。
- **反向（本题工作树含别题的修复）。** 扫描显示本题工作树包含 `18b7cd9d`（poly1d.__eq__）、`2f4a9650`（savetxt）、`d805e9b6`（大型 1D masked array 的 repr）的修复。
  - 我只用公开材料抽查了前两个：`polynomial.py:1239-1244` 已有 isinstance 检查，`npyio.py:1325-1327` 已有 ndim 检查。
  - 第三个没有独立核对。
  - 这几个模块都与 einsum 无关。
- **影响。** 不构成同问题簇。如果与 43e333e2、d89bc4bb 一起进入训练池，模型在那两题的环境里可能读到本题答案；但前提是它主动打开 `einsumfunc.py`，概率低。建议划分数据时记录这层关系。
- **题目类型。** 单文件、Python 层的小修复；靠报错文本 grep 一次就能定位。审查暴露：本记录作者已看过 gold、隐藏测试和运行原件。

## 9. 未知、缺项与修订建议

**未知与缺项**
- 候选 C、D、E 都没有实跑，得分是静态预测。
- 私有 gold 对照中 pr3 的输出开头被截断，看不到原例在 greedy/optimal 下的结果（pr1 已覆盖 True）。
- `d0b59d8b` 上的隐藏测试评分记录缺失。
- `run_refs.json` 的 `mismatched` 只列了 12 个名字，缺 uint8/uint32/uint64。账本字段 `verdict_diagnostics.expected_match.mismatched` 中是完整的 15 个。这是显示截断，不是材料错配。
- 评分日志写着 `RH2_SETUP_EXPECTED_TEST_FILES=3`，但隐藏测试只有 2 个文件。推测是把 run_tests.sh 也算了进去，未核对（影响低）。

**修订建议（交协调者和用户决定，本步不改题）**
- 可选：在 `HT` 目标块旁加一条交换顺序的断言 `np.einsum('ti,ti->i', q, p, optimize=True)`。
  - gold 已实测通过（私有对照 pr3）。
  - 这属于题面中的同一要求，不扩大需求，能挡住候选 C 这类蒙混。
  - 代价：材料版本会变，需要重跑 gold 和 noop。
- 不建议把 BLAS 变体写进测试：gold 过不了，得同时换 gold，等于扩大材料范围。如果确实需要，应另立一个版本并同步更换 gold。

**唯一优先下一步：** 用正式评分代码同批实跑候选 C 和 D，每个只需几秒，预测两者都得 1。这一步能同时回答两个问题：漏测是否真实存在；更完整的修复是否会被误拒。
