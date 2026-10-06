# numpy `18b7cd9d` 修订方案与试跑验收（R-c，2026-09-29）

修订执行者（Claude 子代理，单题闭环试行）。按统一标准 v1 §5 的 R-c 模板执行；Codex 复核与正式材料由协调者负责。本文件是修订草案和试跑记录，**不是正式修订单**。

路径缩写（均相对仓库根）：

- `PUB` = `runs/r2e_static_prep_20260924/v3/public/numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9`
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9`
- `CANDS` = `runs/r2e_actor_20260925/grader_cands`
- `REV` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9`
- `STD` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md`
- `trials/` = 本目录下的试跑结果

## 0. 结论

- **模板**：R-c，共两处窄修订，都加在隐藏测试 `test_1.py` 的 `TestDocs.test_poly_eq` 里，**期望映射不变**（11 键全 PASSED）。
  - 第 1 处（本包指派，v1 §4 第 2 步，T2c）：补 None 以外的非 poly1d 比较，堵住“只特判 None”（候选 N）。
  - 第 2 处（v1 §4 第 4 步另列的 S1）：补“系数相同的另一个 poly1d 对象应相等”，堵住“删掉 `__eq__`/`__ne__`、退回对象身份比较”（候选 I）。v1 §11 只写了第 1 处；两处 edit 的锚点不同、互不依赖，协调者可以单独拿掉第 2 处（后果见 §5 末）。
- **试跑（同一镜像，一轮修订、一轮验收，已收敛）**：正对照 gold 为 1，合理替代解 A 为 1；noop、D、N、I 都为 0，各自失败在预期的断言行。触发反例 N、I 在同镜像的原版材料上都是 1（`trials/cur_N.json`、`trials/cur_I.json`），修订后变 0。
- **不需要用户决定**。剩余覆盖缺口按 T3 登记（§6）。

## 1. 父版本与试跑环境

- **父版本（当前正式材料）**：`PRIV/hidden_tests/test_1.py`，sha256 `4a86bd4b2d557834c384730be8594ef0dbdcd150e4eb958d09ec78f12c741c25`（与 `PRIV/grading_bundle.json` 的 `hidden_test_files` 一致）；`PRIV/expected_output.json` 11 键全 PASSED；`material_revisions` 为空（`PRIV/revisions.json` 为 `[]`）。
- **修订后**：`test_1.py` 的 sha256 为 `aab99f010b8a175cf0d257bc79d02707ced2b9f51452152904243c648d77c841`（在本机对父版本按 §3 的 edits 逐条替换得到，并用 `ast.parse` 检查语法；试跑容器里用同一组 edits 生成）。
- **镜像**：`sha256:c86794602d47e67eca2e5f28feaf2bde59b71d8be7cd8960353464959d324fdf`，配方 `r2e_derive_v1+sysconfig_v1`（各试跑结果 JSON 的 `image`、`recipe_id` 字段）。
- **试跑工具**：`rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`。它按正式 grader 的顺序应用补丁、放入隐藏测试、以 uid 54322 跑 `run_tests.sh`，并用正式解析器逐键比对；但不做基线重建比对、不核隐藏测试树摘要、权限布置也做了简化（文件头第 8–9 行）。所以这里的结果只能支持修订方向，定稿后要走正式材料和正式评分。
- **当前材料确认**（不带 edits、`--expected current`）：`trials/cur_noop.json` 为 mismatch，唯一不符键 `TestDocs.test_poly_eq`，失败在 `test_1.py:219`，报 `AttributeError: 'NoneType' object has no attribute 'coeffs'`（与题面一致）；`trials/cur_gold.json` 为 match。

## 2. 要纠正的误判与公开依据

### 2.1 第 1 处：None 以外的非 poly1d 对象（T2c，v1 §4 第 2 步）

- **误判**：目标断言只用了题面示例的 `None`（`PRIV/hidden_tests/test_1.py:219-220`）。候选 N 只在 `__eq__` 开头特判 `other is None`，`p == 3` 仍然抛 `AttributeError`，却在原版得 1。证据：2026-09-25 正式评分 11/11（`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/grader_candidates.md:47`、`runs/r2e_actor_20260925/grader/ledger_np_N.jsonl`），本次同镜像原版试跑 `trials/cur_N.json` 为 match。
- **公开依据**：
  - 题面标题说的是与 “Non-poly1d Objects” 比较时崩溃（`PUB/user_prompt.txt:4`）。描述句把 `None` 写成 “such as” 的一个例子（`:7`）。期望行为（`:18`）要求：与非 poly1d 对象比较不抛异常，结果表示“不相等”。
  - base 的 `__eq__` 对任何没有 `coeffs` 属性的对象都会访问 `other.coeffs`（`PUB/worktree/numpy/lib/polynomial.py:1202`），所以题面描述的报错并不局限于 `None`。
- **选用的非示例实例**：
  - `object()`：最一般的非 poly1d 对象。它还能堵住“特判 None 再加 `isscalar`”这一类变体（`REV/review.md` §4.2 表中的 N+）。
  - 整数 `3`：常见的数值标量。
  - 不用 list 和 ndarray。与 ndarray 比较时，gold 得到的是逐元素数组；按算术方法的强制转换读法，系数相同的 list 会被判为相等。这两类属于题面没有约定的灰区（`REV/review.md` §3、§4.2）。

### 2.2 第 2 处：poly1d 之间按值相等（v1 §4 第 4 步，S1）

- **误判**：目标测试里 poly1d 之间只比较了同一个对象（`p == p`，`test_1.py:221`）和系数不同的 `p2`（`:222-223`）。候选 I 删掉 `__eq__` 与 `__ne__`，比较退回对象身份，于是 `poly1d([1,2,3]) == poly1d([1,2,3])` 变成 `False`，原版却得 1。证据：`grader_candidates.md:48`、`ledger_np_I.jsonl`；同镜像原版 `trials/cur_I.json` 为 match。
- **公开依据（有公开旧测试的常用行为）**：
  - base 实现按系数比较（`PUB/worktree/numpy/lib/polynomial.py:1201-1207`）；类里还有 `__hash__ = None`（`:1042`），与按值比较的语义一致。
  - 公开回归测试依赖“两个不同的 poly1d 对象按值相等”：`PUB/worktree/numpy/lib/tests/test_regression.py:18-21`（Ticket #28）与 `:74-79`（Ticket #553）都用 `assert_equal` 比较两个不同的 poly1d。`assert_equal` 最后执行的是 `desired == actual`（`PUB/worktree/numpy/testing/utils.py:399-404`），身份比较下这两例都会失败。
  - 题面没有要求改变 poly1d 之间的比较；gold 保留了这条行为。
- **判级**：按 v1 §4 第 4 步，已有的构造候选得 1，同时破坏了有公开测试支撑的常用行为 → S1，走 R-c（`STD:97`）。首批 Codex 复核也确认 I 是真实的蒙混口子（`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_actor_review_20260925/README.md:61`）。v1 §5 要求一题有多个 S1 缺口时逐个列出、分别写依据，在同一轮修订里完成（`STD:126`）。

## 3. 具体改动（`r2e_tests/test_1.py`，`TestDocs.test_poly_eq`）

修订后的完整函数如下；标 `+` 的是新增行（第 2 处在前，第 1 处在后）：

```python
    def test_poly_eq(self):
        p = np.poly1d([1, 2, 3])
        p2 = np.poly1d([1, 2, 4])
        assert_equal(p == None, False)
        assert_equal(p != None, True)
        assert_equal(p == p, True)
+       # a different poly1d object with the same coefficients
+       assert_equal(p == np.poly1d([1, 2, 3]), True)
+       assert_equal(p != np.poly1d([1, 2, 3]), False)
        assert_equal(p == p2, False)
        assert_equal(p != p2, True)
+       # non-poly1d objects other than None
+       other = object()
+       assert_equal(p == other, False)
+       assert_equal(p != other, True)
+       assert_equal(p == 3, False)
+       assert_equal(p != 3, True)
```

- 修订条目格式与试跑工具相同，见 `revision_draft.json` 的 `revisions`：一条 `hidden_test_text_replace`，target 为 `test_1.py`，含两个 edit。第 1 个 edit 以 `assert_equal(p != p2, True)` 那一行为锚点，第 2 个以 `assert_equal(p == p, True)` 那一行为锚点。两个锚点在父版本里各出现一次；单独应用任意一个都能通过语法检查。
- 只断言表达式结果，不断言 `p.__eq__(x)` 的返回值，所以 `__eq__` 返回 `False` 还是 `NotImplemented` 都能通过（题面 `:18`；首批 Codex 复核 `README.md:61` 的“不强制照 gold 返回 NotImplemented”）。
- 新增代码只用 ASCII 字符，沿用文件已导入的 `assert_equal`。

## 4. 期望映射的逐键变化

**无变化。** 修订后仍是 `PRIV/expected_output.json` 的 11 个键，全部 PASSED。新断言都在已有的 `test_poly_eq` 里，没有新增、删除或改名任何测试，所以 R2E 的键集严格相等。

## 5. 验收计划与试跑结果

全部在 §1 的镜像上运行，带修订草案（`--edits`），`--expected current`（修订后的期望映射与当前相同）。

| 候选 | 补丁 | 应得 | 应在何处失败 | 试跑 | 实际 |
| --- | --- | --- | --- | --- | --- |
| gold（正对照） | `PRIV/gold.patch` | 1 | — | `trials/rev_gold.json` | match（11/11） |
| A：`__eq__` 对非 poly1d 返回 False（合理替代解，查误拒） | `CANDS/numpy_18b7_A_eq_returns_false.patch` | 1 | — | `trials/rev_A.json` | match |
| noop | 无 | 0 | `test_poly_eq`，第 219 行 | `trials/rev_noop.json` | mismatch；第 219 行 `AttributeError` |
| D：`__eq__` 返回 NotImplemented，`__ne__` 不改（已知错误，原版就是 0） | `CANDS/numpy_18b7_D_eq_notimplemented_ne_unchanged.patch` | 0 | 第 220 行 `p != None` | `trials/rev_D.json` | mismatch；第 220 行 AssertionError |
| N：只特判 None（触发反例，原版 1） | `CANDS/numpy_18b7_N_special_case_none.patch` | 0 | 第 229 行 `p == other` | `trials/rev_N.json`；原版 `trials/cur_N.json` 为 match | mismatch；第 229 行 `AttributeError: 'object' object has no attribute 'coeffs'` |
| I：删掉 `__eq__`/`__ne__`（触发反例，原版 1） | `CANDS/numpy_18b7_I_delete_eq_ne.patch` | 0 | 第 223 行 `p == np.poly1d([1, 2, 3])` | `trials/rev_I.json`；原版 `trials/cur_I.json` 为 match | mismatch；第 223 行 AssertionError |

- 行号按修订后的文件计。所有 mismatch 的唯一不符键都是 `TestDocs.test_poly_eq`（PASSED → FAILED），其余 10 键不变。每个结果 JSON 里补丁都应用成功（`RH2_APPLY_RC=0`），修订也已应用（`RH2_TRIAL_EDITS_APPLIED=1`）。
- **对照 v1 §5 的验收条目**：
  - 正对照为 1、noop 为 0：满足。
  - 要纠正的误判已纠正：N、I 都从 1 变为 0。
  - 已知相关错误候选仍为 0：D 仍为 0。
  - 合理替代解没有被误拒：A 为 1。
  - 父版本、新版本、理由和触发反例：见 §1 与 §2。
  - Codex 复核：待协调者发起。
- **只采纳第 1 处时**：由静态推断，gold、A 仍为 1，noop、D、N 仍为 0，但 I 回到 1（I 能通过全部非 None 断言）。这个组合没有单独试跑。

## 6. 修订后受保护的公开要求，以及仍未覆盖的部分

**受保护（有直接断言）**：

- `p == None` 为 False、`p != None` 为 True（题面原例，以及由此推知的 `!=`）；
- 与 `object()`、`3` 比较：不抛异常，`==` 为 False，`!=` 为 True（题面的一般表述）；
- poly1d 之间按值比较：系数相同的不同对象相等；同长度、系数不同的不相等（旧行为）；
- 同文件另外 10 个回归键不变。其中 `test_doctests` 是死键（`REV/card.md` §4 第 3 条），这是上游原样的问题，本次不处理。

**仍未覆盖，按 T3 登记，不在本轮修订内**：

- **长度不同的 poly1d 比较**（`__eq__` 的 shape 分支）：公开的 Ticket #554 测试覆盖了它（`PUB/worktree/numpy/lib/tests/test_regression.py:81-86`），但那个测试不计分。复核者 §4.1 的“去掉 shape 检查、改用 `.all()`”只是静态推断，没有已跑的候选命中它，按 v1 §4 第 4 步不构成 S1。
- **反向比较 `None == p`**：已知候选里没有在这里出错的。
- **list 与 ndarray 的比较**：题面没有约定，属于灰区。
- **`assert_equal` 对数组结果按广播比较**：返回逐元素数组的实现也能过（`REV/review.md` §4.3），风险低。

以上几项在探针与训练的抽查里继续由已有后检覆盖：`rh2/experiments/r2e_actor_20260925/postcheck/numpy_18b7cd9d_behavior.py` 的 12 项包括 `none_eq`、`eq_list_same_coeffs`、`eq_different_len`、`ne_different_len`。后检不计入 reward。

## 7. 交协调者

- 正式材料：把 §3 的两个 edit 写进 `s2_r2e` 下的正式修订单（`hidden_test_text_replace`，`test_1.py`），期望映射不变。然后做派生镜像的材料步骤，在正式评分上复跑 gold、A、noop、D、N、I，并交 Codex 复核。本执行者没有写正式修订单与 pins，也没有改生产代码。
- 远端只执行了本包允许的命令：`mkdir`、`scp` 上传与取回、`trial_grade.py`，同一时间最多 2 个试跑。试跑目录是 `/work/r2e/trials/numpy/18b7cd9d/`。
