# 题卡：scrapy `a95a338e`（`is_generator_with_return_value` 与 `functools.partial`）

R2E 私有主审，2026-09-29 07:05（+08），按统一标准 v1。依据是静态审查加上新机实跑，尚未经过独立复核。路径缩写与 `old_findings_delta.md` 相同：`PUB/`、`PRIV/`、`INV/`、`DC/`。

## 1. 目标、版本与结论

- **目标**：`scrapy.utils.misc.is_generator_with_return_value` 收到 `functools.partial` 时不再抛 `TypeError`，而且要正确判断被包装的生成器有没有带值的 `return`。题面的例子（无返回值）应返回 False。
- **版本**：
  - base `9077d0f9`（scrapy 2.7.0）、Python 3.9.21、pytest 8.3.4；
  - 材料 `expected_v0`，没有修订（v3–v8 对本题相同）；
  - 评分镜像 `rh2-r2e-derived/scrapy:a95a338eeada-r2e_derive_v1s`（`sha256:d7f8d826…`，配方 `r2e_derive_v1+sysconfig_v1`）。
- **结论：S1。必须先做测试层修订，才能进训练。** 有三处独立命中：
  - 第 2 步：唯一目标键只用题面示例（T2c）；
  - 第 3 步：退化候选 D 实际得 1.0（T2b）；
  - 第 4 步：C2、C3 实际得 1.0，根因是两个期望 FAILED 的死键（T5）。
- 环境与评分条件正常：新机 noop 0、gold 1；devcheck 13 项检查全部通过。**问题出在测试层，不在环境。**
- `disposition.state=needs_review`（`static_review`；理由：题意 / 测试争议，核心判据失效）。

| v1 用途 | 结论 | 差什么 / 依据 |
| --- | --- | --- |
| 问题定位 | **yes** | 无门槛 |
| 能力比较 | **conditional** | 用原版材料时，必须预先登记事后审计：得 1 的补丁还要过私有语义对照 `INV/pcheck_semantics.sh`，第 1 行应为 `True False True`，第 2 行应为 `1`；原始 reward 与语义结果分开报。或者改用 R1+R2 验收后的标明版本 |
| 训练候选 | **no** | S1 未处理。R1+R2 验收并经 Codex 复核后再评 |
| 留出评测候选 | **no** | S1 未处理；修订后只能作"标明版本的自建题"；与 `scrapy__75450e75` 同源，按 D3 放在同一侧 |

## 2. 关键需求—测试映射

| 需求或旧行为 | 公开依据 | 决定性断言（`PRIV/hidden_tests/test_1.py`） | 覆盖 | 执行证据 |
| --- | --- | --- | --- | --- |
| partial 包装无返回值的生成器 → False，不抛错 | `PUB/user_prompt.txt:22-30` | `test_partial` `:264` | 有覆盖，但只用题面字面值（T2c） | noop 报 TypeError（FAILED），gold PASSED |
| partial 包装带返回值的生成器 → True | `user_prompt.txt:8`、`:32`；docstring `misc.py:217-220` | 无 | **缺失** | D 得 1.0；私有对照里 D 对这种输入给 False |
| 非 partial、带返回值 → True | docstring；公开测试 `:70-74` | `:71-75`，但在死键里 | **名义覆盖，实际失效** | C3 在 `:71` 失败，仍得 1.0 |
| 警告的条数与文案；`IndentationError` 回退警告 | `docs/news.rst:1919-1921`；公开测试 `:76-95`、`:251-256` | `:77-96`、`:252-257`（死键） | **实际失效** | C2（关掉警告）得 1.0 |
| 非 partial、无返回值 → False | 公开测试；`news.rst:841-844`、`:1187-1189` | `:135-142`、`:218-225` | 有覆盖 | 各候选都 PASSED |

## 3. 八方面：查了什么、没查什么

- **公开需求**：查了题面、提示、docstring、调用者和文档条目。模型实际收到的消息没有捕获：devcheck 发给模型的是 devcheck 指令，不是题面。
- **材料与初始问题**：gold 的前像 blob 与公开源码一致；隐藏测试就是上游测试文件加 `test_partial`；初态没有差异；noop 的失败正是题面报错（旧机和新机都是）。
- **测试是否测到要求**：5 个键都追到了断言。问题见 §4。
- **误拒**：没有发现。更完整的合理解 C1 实际得 1.0。
- **回归与 gold**：gold 修到了原例；登记了两处边缘缺口（G1）；True 路径和警告在评分下没有保护。
- **开发条件**：devcheck 用 agent 身份、正式启动路径、v7 任务面，13 项检查全部通过；复现、诊断、公开测试都能用（4 passed、14 passed）。端到端抓取在本镜像不可用（E1）。
- **交付与评分边界**：只需改 `scrapy/utils/misc.py`，投影和导出都正常。根目录 `conftest.py` / `pytest.ini` 以及可写的 `.venv` 属于共用控制面，没查，归 A 线。
- **题目关系**：X1 三处。
- **没查的**：真实模型求解（清单 33–36）、并发与缓存复用（15）、共用控制面（31）。

## 4. 问题与证据

| 编号 | 问题 | 严重度 | 证据层次 | 去向 |
| --- | --- | --- | --- | --- |
| T2c | 目标键只用题面示例的字面值：两个参数、只有 `yield {}`、`arg1=42` | S1 | 静态对照（`user_prompt.txt:15-19` 对 `test_1.py:259-264`） | R1 |
| T2b | 退化候选 D（在 gold 修改的那一行吞掉 TypeError、返回 False）得 1.0 | S1 | 当前 CPU 正式评分（`INV/ledger_D.jsonl`：补丁已交付，`test_partial` 已执行并 PASSED）+ 私有语义对照 | R1 |
| T5 → 第 4 步 | 评分命令 `-W ignore` 让两个期望 FAILED 的键变成死键；C2、C3 各得 1.0，破坏了文档记载的警告功能和 docstring 规定的判定语义 | S1 | 正式评分（C3 的失败位置从 `:79` 前移到 `:71`，状态不变）+ 私有对照 + devcheck（在解题环境下，同样的断言有效） | R2 |
| G1 / T3 | gold 下，警告路径收到"partial 包装带返回值的生成器"会抛 `AttributeError`；partial 包装绑定方法时不会被分析 | S2（登记） | gold 私有对照（诊断项 H、F） | 题面没有要求，不加断言 |
| P4 | 示例要写成文件运行；修好后用 `python -c` 会得到 `OSError` | 登记 | 静态推断 + devcheck（文件形式已实跑） | — |
| E1 | `CrawlerProcess.start()` 因 Twisted 缺少 `_handleSignals` 不可用，base 和 gold 都一样 | 登记，不影响本题 | devcheck + gold 私有对照 | 不修；开发验证改用单元级脚本 |
| X1 | 本题答案与隐藏测试逐字出现在 `75450e75` 的初态；本题初态包含 `9a15fcf8`、`e9387529` 的修复 | 登记 | 公开包比对 + 机械扫描 | 训练时控制重复采样；按 D3 放同一侧 |

**与历史的关系**：09-24 的环境审查已经把死键正确归因于 `-W ignore`，并判"不改"。那是在环境资格范围内的结论。本轮按 v1 的第 3、4 步推翻"不改"，详见 `old_findings_delta.md` 第 3 条。

## 5. 修订草案（进训练前必做）

- **R1（v1 §5 R-c）**
  - 公开依据：`user_prompt.txt:8`（"properly determining if the callable is a generator with a return value"）、`:32`，以及 docstring。
  - 改法：在 `test_partial` 末尾加一个非示例实例，断言 `is_generator_with_return_value(partial(cb_with_return, 1))` 为真，其中 `cb_with_return` 带 `return 1`（附录 A 的 B-1 第二个 hunk）。
- **R2（v1 §5 R-a：让在评分命令下必然失败的有效断言恢复生效；依据与 R-c 的"复用现成公开测试"一致）**
  - 改法：
    - 给测试类加一个 `setUp`：先进入 `warnings.catch_warnings()`，再调用 `simplefilter("always", UserWarning)`，并用 `addCleanup` 在测试结束后复原（附录 A 的 B-1 第一个 hunk）；
    - 把两个键的期望改为 PASSED（附录 A 的 B-2）。
  - 独立依据：
    - 在解题环境里，同样的断言在 base 上以 agent 身份 4 passed，在 gold 上也是 4 passed（`DC/orig/captures/pytest_generator_return_tests.out`、`DC/private_control.json`）；
    - agent 身份下 `sys.warnoptions` 为 `[]`（`INV/pcheck_warnoptions_agent.json`）；
    - 失败机理与候选无关：所有候选都在 `:79` 和 `:256` 报 `0 != 1`。
  - 与既有做法一致：09-24 的 T0-5 / T0-6 也是用材料修订救活死键、改期望（`r2e_env_repair_20260924/decisions.md:42-43`）。
- **实施要求**：
  - 键集不变（R1 放进已有的键，R2 只加 `setUp`）；
  - 按既有材料修订流程生成新的隐藏测试树和期望，重建派生镜像，更新 pins；
  - 保存父版本（`expected` `2c5d045c…`、`hidden_tests_tree` `63928e22…`），以及触发修订的反例账本（`INV/ledger_{D,C2,C3}.jsonl`）。

**验收矩阵**（正对照用 gold；左列是实跑结果，右列是修订后的预期）：

| 候选 | 当前材料（实跑） | 修订后预期（不符的键） | 预期依据（实跑） |
| --- | --- | --- | --- |
| gold（正对照） | 1（L0） | **1**（5/5），跑 2 次 | 私有对照 `True False True / 1`；公开同名用例 4 passed |
| noop | 0（L0，只有 `test_partial` 不符） | **0**（只有 `test_partial`），跑 2 次 | base 下公开同名用例 4 passed（devcheck orig） |
| D（退化候选） | 1 | **0**（`test_partial`） | 私有对照 `False False True / 1` |
| C1（合理替代解） | 1 | **1** | 私有对照 `True False True / 1` |
| C2（关掉警告） | 1 | **0**（`test_generators_return_something`、`test_indentation_error`） | 私有对照中警告为 0 条 |
| C3（恒 False） | 1 | **0**（`test_generators_return_something`、`test_partial`） | 私有对照 `False False False / 0` |

**待验证项**：

1. **R2 的机制**：`setUp` 加 `simplefilter` 的写法，在镜像的 pytest 8.3.4、`-W ignore` 和 `PYTHONWARNINGS` 下能否让 UserWarning 可见。由修订执行者先用 gold 在修订材料上试跑确认。
   - 本机只做过 CPython 3.9.6 的标准库实验：在同样的解释器参数下，这种写法有效，cleanup 后过滤器也会复原。
   - 如果不生效，改用逐块写法：在 22 个 `with warnings.catch_warnings(record=True) as w:` 块里，各自的第一行加 `warnings.simplefilter("always", UserWarning)`。
2. **R1 的断言在 gold 下为真**：私有对照用的是模块级函数；修订里用的是测试方法内的嵌套函数。gold 对 `f1` 这类嵌套函数有效，但仍要以修订后的实跑为准。
3. **Codex 复核 R2 的模板归属**：如果认定"在隐藏测试里改警告过滤"超出 R-a，就按 v1 §5 的模板外情形交用户决定。退路"删掉两测两键"消不掉第 4 步的 S1，本题仍不能进训练。

## 6. 复核与分歧

还没有独立复核（reviewer 未派）。与历史结论的分歧见 `old_findings_delta.md`。

## 7. 唯一优先的下一步

实施 R1+R2 后，先用 gold 在修订材料上跑一次正式评分，确认 R2 生效；再跑完整的验收矩阵。

## 8. 探针就绪差距

本卡**没有读**本批 README §3（派发规则禁止），下面按 v1 §2 与八方面协议 §5 的条件列出，请协调者按 README §3 的措辞对齐。

| 条件 | 状态 | 谁来补 |
| --- | --- | --- |
| 公开要求可追溯，参考测试可解释 | 已满足：5 个键全部归因 | — |
| 当批有效运行条件 | 已满足：新机 L0 noop 0 / gold 1；devcheck 13 项全过；agent 无警告过滤 | — |
| reward 能区分核心行为（没有未处理的 S1） | **未满足**：D、C2、C3 都得 1.0 | 协调者实施 R1+R2 并跑验收矩阵；Codex 复核 |
| 修订前若要用原版进探针，需预先登记事后审计 | 未设 | 协调者：可直接用 `INV/pcheck_semantics.sh` 作 PASS / FAIL 判定（读第 1 行三个布尔值和第 2 行的警告数） |
| 独立复核 | 未做 | 协调者派 reviewer |
| 真实模型链路（Qwen adapter、模型实际收到的消息） | 未验（环境卡 §2） | A 线 / 探针链路 |
| 端到端抓取不可用（E1） | 已登记，不阻塞 | — |
| 跨题关联（X1） | 已登记 | 探针抽样时注意与 `75450e75` 的关系 |

## 9. 建议队列（给协调者）

1. 实施 R1+R2，并按 §5 的矩阵验收。
2. 标注公开读者的 `crawl_partial_callback` 命令在本镜像无效：它失败的原因是 Twisted，不是题目。如果要做端到端验证，可以试 `process.start(install_signal_handlers=False)`（`crawler.py:332`、`:355`；静态推断，未实跑）。
3. 线索（未查，不属本题）：其它 scrapy 2.7.x 题（`75450e75`）的开发或评分路径，是否也经过 `CrawlerProcess.start()`。

## 附录 A：修订补丁草案（相对 `PRIV/` 应用，已用 `git apply --check` 核过；评分时的 `r2e_tests/test_1.py` 就是这里的 `hidden_tests/test_1.py`）

**B-1** 隐藏测试（第一个 hunk 是 R2 的 `setUp`，第二个是 R1 的非示例实例）：

```diff
diff --git a/hidden_tests/test_1.py b/hidden_tests/test_1.py
--- a/hidden_tests/test_1.py
+++ b/hidden_tests/test_1.py
@@ -40,6 +40,14 @@ def generator_that_returns_stuff():
 
 class UtilsMiscPy3TestCase(unittest.TestCase):
 
+    def setUp(self):
+        # run_tests.sh runs pytest with `-W ignore` and PYTHONWARNINGS=ignore::UserWarning,
+        # so the UserWarnings recorded below were never visible; re-enable them per test.
+        catcher = warnings.catch_warnings()
+        catcher.__enter__()
+        self.addCleanup(catcher.__exit__, None, None, None)
+        warnings.simplefilter("always", UserWarning)
+
     def test_generators_return_something(self):
         def f1():
             yield 1
@@ -262,3 +270,9 @@ class UtilsMiscPy3TestCase(unittest.TestCase):
 
         partial_cb = partial(cb, arg1=42)
         assert not is_generator_with_return_value(partial_cb)
+
+        def cb_with_return(arg1, arg2):
+            yield {}
+            return 1
+
+        assert is_generator_with_return_value(partial(cb_with_return, 1))
```

**B-2** 期望映射（原文件末尾没有换行）：

```diff
diff --git a/expected_output.json b/expected_output.json
--- a/expected_output.json
+++ b/expected_output.json
@@ -2,6 +2,6 @@
     "UtilsMiscPy3TestCase.test_generators_return_none": "PASSED",
     "UtilsMiscPy3TestCase.test_generators_return_none_with_decorator": "PASSED",
     "UtilsMiscPy3TestCase.test_partial": "PASSED",
-    "UtilsMiscPy3TestCase.test_generators_return_something": "FAILED",
-    "UtilsMiscPy3TestCase.test_indentation_error": "FAILED"
+    "UtilsMiscPy3TestCase.test_generators_return_something": "PASSED",
+    "UtilsMiscPy3TestCase.test_indentation_error": "PASSED"
 }
\ No newline at end of file
```

## 附录 B：证据索引

- **正式评分（新机）**：
  - `runs/r2e_lifecycle_20260929/env_verify/ledger_l0_noop.jsonl` 与 `ledger_l0_gold.jsonl` 的第 13 行；
  - `INV/ledger_{D,C1,C2,C3}.jsonl` 各 1 行（均为 reward 1.0、`keys_equal=true`），日志 `INV/logs_*/…eval.log`：
    - C3：`:57-60`，失败在 `test_1.py:71`；
    - D：`:85`，`test_partial` PASSED；
    - C2：`:66-68`、`:78-80`，失败在 `:79` 与 `:256`。
- **私有对照**：
  - `INV/pcheck_semantics_{gold,D,C1,C2,C3}.json`（root、不联网、不参与评分）；
  - `INV/pcheck_warnoptions_agent.json`；
  - `DC/private_control.json`（gold 下的公开命令）。
- **devcheck**：
  - `DC/orig/attempt.json`（13 项检查；CC 2.1.205）；
  - `DC/orig/captures/*.out`。
- **旧机对照**：
  - `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-{noop-s_b7461f67,gold-s_9377378e}.eval.log`；
  - `runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl` 第 36、84 行。
- **分析**：`analysis_before_history.md`（初判与候选补丁）、`old_findings_delta.md`（历史对照）。
