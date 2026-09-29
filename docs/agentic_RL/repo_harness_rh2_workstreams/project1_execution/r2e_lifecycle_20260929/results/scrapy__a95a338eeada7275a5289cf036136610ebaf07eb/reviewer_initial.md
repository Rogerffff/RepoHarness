# scrapy__a95a338e：独立复核初判（第一步，未读主审产物与历史）

- 角色：独立复核者。按 `roles/reviewer_r2e.md` 第一步与统一标准 v1 执行。整理时间：2026-09-29 07:24 +08（取自 `date`）。
- 材料版本：hidden_tests 树 `63928e22…`，expected `2c5d045c…`，gold `59a59f25…`，`run_tests.sh` `8285765f…`；`revisions.json` 为 `[]`（没有材料修订）。本地私有文件逐个 sha256，与 `grading_bundle.json`、`validation_bundle.json`、`run_refs.json` 的 current_material 一致（本次 `shasum` 核对）。
- 路径简写（相对仓库根）：
  - `PUB` = `runs/r2e_static_prep_20260924/v3/public/scrapy__a95a338eeada7275a5289cf036136610ebaf07eb`
  - `PRI` = `runs/r2e_static_prep_20260924/v3/private/scrapy__a95a338eeada7275a5289cf036136610ebaf07eb`
  - `NOOP` = `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-s_b7461f67.eval.log`
  - `GOLD` = `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-gold-s_9377378e.eval.log`
  - `M3a1` = `runs/env_overnight_20260916/M3/gold_ledger/logs_r2e/scrapy/a95a338eeada/gold/a1/test_output.txt`
  - `PUB75` = `runs/r2e_static_prep_20260924/v3/public/scrapy__75450e75d269b2a2b00b6303af1033df1f69cc67`

## 1. 初判结论

- **严重度：S1。**
  - 第 2 步命中 **T2c**：唯一的目标键 `UtilsMiscPy3TestCase.test_partial` 只断言题面示例。输入形态与题面相同：`(arg1, arg2)` 签名、函数体只有 `yield {}`、用关键字 `arg1=42` 绑定；期望结果也相同（返回假）。
  - 第 3 步 **T2b 预测命中**：退化候选 DG-B 吞掉 `TypeError` 后返回 `False`。按源码推导，它在当前材料上得 1；待协调者用正式评分实跑确认，在此之前记 conditional。
- **修订：R-c-1（必做，属于模板内）。** 在 `test_partial` 里补一个非示例实例：包装了"带返回值的生成器"的 partial 应返回真。键集与 expected 都不变。
- **另外登记两项。**
  - **两个期望 FAILED 键**：`test_generators_return_something` 和 `test_indentation_error`。它们恒失败，是因为评分命令里的 `-W ignore` 让 `warnings` 计数断言永远拿到 0 条警告（T5，已按固定来源解释）。
    - 合理修复不会把它们翻成 PASSED，所以**不构成误拒**。
    - 代价：有两类行为没有任何键保护（T3，S2）——"普通生成器带返回值 → 真"，以及 `warn_on_generator_with_return_value` 的全部行为。
  - **gold 的遗漏**：`warn_on_generator_with_return_value` 对 partial 取 `callable.__name__` 时会出错，gold 没修（G1→T3）。这超出题面范围，只登记。
- **没有发现的问题**：误拒（T1）、材料错配（X2）、题面直接给出答案（P1）、题面与测试矛盾（P2/P5）、时序敏感的键（E5）。
- **开发条件**：本次没有本题的 devcheck，actor 侧记为"待验"。
- **题目关系（X1）**：
  - 本题的 gold 与 `test_partial` 逐字出现在 `scrapy__75450e75…` 的公开初态里。
  - 本题初态已经包含 `scrapy__9a15fcf8…` 的修复，以及 `scrapy__e9387529…` 的新测试。
- **用途（v1 初判）**：问题定位 yes；能力比较 conditional；训练候选 no（当前材料有未处理的 S1，R-c-1 验收后重评）；留出评测候选 no。
- **唯一最优先的下一步**：用正式评分在当前材料上实跑 DG-B（预期 reward=1），然后实施 R-c-1 并验收（§10）。

## 2. 实际读取范围

**读了：**

- 角色卡与方法：
  - `docs/.../r2e_lifecycle_20260929/roles/reviewer_r2e.md` 全文。
  - `investigator_r2e.md`：工具一次读入了全文 53 行。我只把指定的四节当作口径（材料、R2E 的评分口径、第二批补充规则、单题闭环试行补充）。另外两节"对每题按顺序完成""边界"是通用流程，不含本题信息。
  - 方法文档：`task_screening_standard_v1_20260925.md` 全文（§10–§11 提到其它 R2E 题的处置，没有本题）、`r2e_environment_card.md`、`quality_review_protocol_20260920.md`、`record_template.md`。
- 公开包 `PUB`：
  - 元数据：`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`worktree_manifest.json`（元数据与两个文件的摘要）。
  - `worktree/` 下的源码与配置：`scrapy/utils/misc.py` 全文、`scrapy/utils/datatypes.py:66-109`、`scrapy/core/scraper.py` 中 `call_spider` 附近、`scrapy/utils/python.py:180-208`、`pytest.ini`、`conftest.py`、`run_tests.sh`、`tests/keys/__init__.py:24-49`。
  - 测试：`tests/test_utils_misc/test_return_with_argument_inside_generator.py`，并与隐藏测试做了 diff。
  - grep：`partial`，以及两个目标函数的调用者。
- 私有包 `PRI`：全部文件。
- 运行原件（都是 `run_refs.json` 列出的）：
  - 4 条 current 账本行：R-f 09-23 的 noop/gold 第 46 行，环境轮 `_rerun2` 的 noop/gold 第 46 行。
  - 对应的 4 份 `.eval.log`，sha256 与 run_refs 一致。
  - M3 独立参考：账本 `r2e_gold_m3.jsonl` 第 36、84 行，以及 a1/a2 两份 `test_output.txt`。
- 跨题：
  - `cross_task_gold_scan.json`、`cross_task_test_scan.json` 中与本题相关的条目。
  - 同仓另外 4 题的**公开包**：标题与 base，`scrapy/utils/misc.py`，`tests/test_utils_misc/`。
  - 本题 `scrapy/responsetypes.py` 与 `tests/test_exporters.py` 的定点 grep。

**没读：**

- `OUTPUT_DIR` 下的任何文件，任何 `history/` 目录。
- 各 `*review*` 目录，`docs/.../r2e_env_repair_20260924/`。
- 本批的 README、board.json、assignments.json。
- `runs/` 下的分析与汇总文件。
- 其它题的私有包，以及 40 项清单。
- 本次没有提供 devcheck 目录。

**没做：** 没有运行项目代码或容器。下文说"两轮日志一致"，是文件比对的结果，不是重跑。

## 3. 公开要求与断言的双向映射

公开要求来自 `PUB/user_prompt.txt`：

| 行 | 内容 |
|---|---|
| L5 | 标题 |
| L8 | "instead of properly determining if the callable is a generator with a return value" |
| L15-19 | 示例 |
| L23 | 不报错，并且 "should return `False` since the partial function does not have a return value" |
| L29 | 实际报错原文 |
| L32 | "accurately determining the nature of the callable when it is wrapped with `functools.partial`" |

函数契约见 `PUB/worktree/scrapy/utils/misc.py:216-220` 的 docstring：生成器函数里有值不为 None 的 `return` 时返回 True，否则返回 False。

| # | 要求或合理旧行为 | 公开依据 | 键与决定性断言 | 覆盖 | 证据 |
|---|---|---|---|---|---|
| R1 | 对示例 partial 不抛 `TypeError` | L5、L29 | `test_partial`（`PRI/hidden_tests/test_1.py:259-264`）；L264 调用时抛异常即 FAILED | 覆盖，但只用示例字面值 | NOOP L89-132 抛出题面原文的错误；GOLD L85 PASSED |
| R2 | 示例返回假 | L23 | `test_partial` L264 `assert not …` | 覆盖，但只用示例字面值 | 同上 |
| R3 | 包装了"带非 None 返回值的生成器"的 partial 应返回真 | L8；L23 的 "since" 从句；L32；docstring | 无 | **缺失 → T2c / T2b** | 源码推导；DG-B 待实跑 |
| R4 | 其它 partial 形态：位置参数绑定、嵌套 partial、包装绑定方法的 partial | 题面的一般表述 | 无 | 缺失（边缘情形，见 §7） | 源码推导 |
| G1 | 普通生成器带返回值 → 真（含嵌套 helper、docstring 顶格时的缩进处理） | docstring；公开测试 `tests/test_utils_misc/test_return_with_argument_inside_generator.py:70-74` | `test_generators_return_something` L71-75 有断言，但该键期望 FAILED | **死键，不保护**：noop 与 gold 都在 L79 失败 | NOOP L64-67；GOLD L65-68 |
| G2 | 无返回值、裸 `return`、非生成器、被装饰 → 假 | docstring；公开测试 L134-141、L217-224 | `test_generators_return_none` L135-142、`test_generators_return_none_with_decorator` L218-225（都是 PASSED 键） | 覆盖 | NOOP L137-138；GOLD L83-84 |
| G3 | `warn_on_generator_with_return_value` 发警告、警告文案、`IndentationError` 分支 | `misc.py:247-271`；公开测试 L76-95、L251-256 | 计数断言都在两个 FAILED 键里；PASSED 键里的 `len(w) == 0` 在 `-W ignore` 下恒为真 | **完全不保护** | `PRI/run_tests.sh:1`；日志同上 |

**反向核对：**

- `test_partial` 的断言都能在公开材料里找到依据（就是示例本身）。它不要求精确文案、mock 形状或内部 helper。
- `test_indentation_error` 用 `mock.patch("scrapy.utils.misc.is_generator_with_return_value", …)` 约束了内部名。但公开测试里已有同样写法（公开测试 L251），而且这个键恒 FAILED，不影响得分。

## 4. 目标键与运行原件

- **4 条 current 行**：R-f（09-23）与环境轮 `_rerun2`（09-24）各跑了一次 noop 和一次 gold。
  - 运行条件：派生镜像 `rh2-r2e-derived/scrapy:a95a338eeada-r2e_derive_v1`（image ID `sha256:378c5320…`），`recipe_id=r2e_derive_v1`，评分用户 54322，2 CPU / 4 GiB，`network=deny_all`。
  - noop：`expected_match 4/5`，不一致的只有 `test_partial`，reward 0。
  - gold：5/5，reward 1。`candidate_touched_conftest_or_fixture=[]`，`projection.included_paths=["scrapy/utils/misc.py"]`。
  - 两轮日志去掉时间戳和内存地址后逐字相同（本次用 `diff` 比对）。
- **键的分工**：
  - 目标键 = `test_partial`（1 个）。
  - 回归键 2 个，都是 PASSED。
  - 死键 2 个，都是 FAILED。
- **初态失败位置**：NOOP L93-94 指向 `scrapy/utils/misc.py:229 src = inspect.getsource(callable)`，再由 `inspect.getfile` 抛出题面原文的 `TypeError`（NOOP L132）。
  - 这也说明 Python 3.9.21 的 `inspect.isgeneratorfunction` 对 partial 返回真；否则走不到 L229。
  - 所以题面的触发条件在本环境成立。
- **M3 独立参考**：在来源镜像 `namanjain12/scrapy_final@sha256:cd01a127…` 上，用同一 `run_tests.sh` 跑 gold 两次，结果相同（M3a1 L7 `..FF.`、L50-51、L62-63）。
  - 因此两个 FAILED 键不是派生配方造成的，而是 R2E 来源的 runner 本身带来的。

## 5. R2E 专项

**(a) 非 PASSED 的期望键**

- 两个键都在 `self.assertEqual(len(w), 1)` 处报 `0 != 1`（NOOP L64-65、L76-77；GOLD L65-66、L77-78）。
- 原因：`PRI/run_tests.sh:1` 用 `PYTHONWARNINGS='ignore::UserWarning,…'` 加 `-W ignore` 启动。全局的 ignore 过滤器使 `warnings.warn` 发出的警告不会进入测试里 `warnings.catch_warnings(record=True)` 的记录。
  - 这个上下文管理器只复制过滤器，不改它们。
  - pytest 8 只在 `sys.warnoptions` 为空时才对 DeprecationWarning 加 `always`。
  - 这两点是源码推断，与日志一致。
- 按固定来源解释，属于 T5。
- **会不会惩罚正确修复**：合理修复不会去改全局警告过滤，所以不会把这两个键翻成 PASSED。只有强行 `simplefilter("always")` 这类违背惯例的改动才会翻转并被判 0，而那不是合理解。
- **结论：不构成误拒，但造成覆盖丢失**（见 §3 的 G1、G3）。
- 池级排查的提示：`unittest.assertWarns` 和 `pytest.warns` 进入时会自己设 `always`，不受影响。受影响的只是"裸 `catch_warnings(record=True)` + 计数"这种写法，可以按这个模式搜。

**(b) 题面报错是否出现在 noop 的目标键里**：是。NOOP L132 与 `user_prompt.txt:29` 逐字相同，位置在 `misc.py:229`。

**(c) 题面是否泄漏修法**：没有。
- 题面只说函数 "does not correctly handle `functools.partial` objects"，停在原因层面，没有给出解包 `.func` 的写法。
- 仓库里的 `scrapy/utils/python.py:194-196`（`get_func_args` 对 partial 取 `func.func`）本来就是公开先例，不算泄漏。

**(d) 测试支撑与撞键**

- 隐藏测试 = 公开的 `tests/test_utils_misc/test_return_with_argument_inside_generator.py` 加上 `from functools import partial` 和 `test_partial`。本次 diff 显示只多这两处。
- 不导入 `tests.*` 下的辅助代码。
- 依赖根目录的 `conftest.py`（导入 `tests.keys`，会话开始时 `generate_keys()` 写 `tests/keys/`）和 `pytest.ini`（`usefixtures = chdir`、`--doctest-modules`）。日志显示两者正常生效。
- 单文件单类，5 个键，没有撞键。
- `inspect.getsource` 按绝对路径读 `/testbed/r2e_tests/test_1.py`，`chdir` 不影响它（GOLD 日志中 L71-75 的调用都成功）。

**(e) 时间、随机、资源敏感的键**：没有。都是纯函数断言；测试段约 1.2 s，内存峰值约 235 MB。

**(f) 材料修订**：`revisions.json` 为 `[]`，不适用。

## 6. 退化候选与合理替代解

### DG-B：第 3 步的退化候选（"吞掉错误"）

改的位置：`scrapy/utils/misc.py` 的 `is_generator_with_return_value`，把 L229 改成捕获 `TypeError` 后写缓存并返回 `False`：

```diff
@@ -226,7 +226,11 @@ def is_generator_with_return_value(callable):
         return value is None or isinstance(value, ast.NameConstant) and value.value is None
 
     if inspect.isgeneratorfunction(callable):
-        src = inspect.getsource(callable)
+        try:
+            src = inspect.getsource(callable)
+        except TypeError:
+            _generator_callbacks_cache[callable] = False
+            return False
         pattern = re.compile(r"(^[\t ]+)")
         code = pattern.sub("", src)
```

- **构造依据**：只凭 gold 的修改位置（同一行）就能写出。
- **违反的公开要求**：题面 L8、L23、L32 与 docstring 要求对 partial"正确判断"是否带返回值。
- **能看出违例的输入**：
  ```python
  def gen(arg1, arg2):
      yield {}
      return 1
  ```
  `is_generator_with_return_value(partial(gen, arg1=42))` 应为真，DG-B 返回假；连带 `warn_on_generator_with_return_value` 也不会警告。
- **当前材料的预测**：reward=1。`test_partial` 变成 PASSED；其余 4 个键走的路径与 base 相同。
- **协调者实跑时核对**：交付路径包含 `scrapy/utils/misc.py`；日志里 `test_partial` 为 PASSED；其余键与 expected 一致。
- **R-c-1 后的预测**：0（在新断言处失败）。

### DG-A：可选，用来佐证死键造成的回归缺口（不是第 3 步的唯一候选）

- **改法**：在同一函数的 docstring 之后（`misc.py:220` 后）插入 `return False`，即"与输入无关的固定结果"。
- **违反的公开要求**：docstring，以及公开测试 L70-74。
- **当前材料的预测**：1。`test_generators_return_something` 改在 L71 失败，但仍是 FAILED，与期望一致。
- **R-c-1 后的预测**：0。

### 部分实现能被正确拒绝的例子

- 有一种实现为 partial 另写一条路径：直接 `ast.parse(inspect.getsource(callable.func))`，不做缩进处理。
- 它对题面的顶层示例可行，但对缩进定义的函数会抛 `IndentationError`。
- `test_partial` 里的 `cb` 是嵌套定义的，所以会拒绝这种实现。这个拒绝有依据：spider 方法都是缩进定义的，这正是原有代码处理缩进的原因。

### 合理替代解（核查误拒）

| 候选 | 做法 | 预测得分 |
|---|---|---|
| ALT-1 | 先解包再判断：`func = callable; while isinstance(func, functools.partial): func = func.func`；`isgeneratorfunction` 与 `getsource` 都用 `func`，缓存仍以 `callable` 为键 | 当前材料与 R-c-1 后都是 1 |
| ALT-2 | 对 partial 递归调用 `is_generator_with_return_value(callable.func)` | 1 |
| ALT-3 | 只解一层 `callable.func`（CPython 构造嵌套 partial 时会展平，效果相同） | 1 |
| 更完整的修复 | 同时修 `warn_on_generator_with_return_value` 里 partial 的名字，或处理包装绑定方法的 partial | 不影响任何现有键，1 |

没有找到会被判 0 的合理解。**没有 T1。**

## 7. gold 检查

- 修到了原例（GOLD L85）。
- 对非 partial 的可调用对象，新增的循环不会执行，行为与 base 相同。
- 新增的 `from functools import partial` 不会遮蔽 `misc.py` 里已有的名字。
- 没有无关改动。

**G1（→T3，超出题面范围，只登记）**

- `warn_on_generator_with_return_value`（`misc.py:255`、`:263`）使用 `callable.__name__`，而 partial 没有这个属性。
- 在 gold 下，包装"带返回值生成器"的 partial 会被 `is_generator_with_return_value` 判为真，随后在 L255 抛 `AttributeError`。base 在这种情况下抛的是 L229 的 `TypeError`。
- 调用者 `scrapy/core/scraper.py:164`、`:169` 会对请求的回调调用这个函数。
- 题面只要求修 `is_generator_with_return_value`，所以这一点不作为 S1 依据。
- **设计 R-c-1 时不能对这种 partial 调用 `warn_on_generator_with_return_value`**，否则 gold 会失败。

**边缘情形（T3）**

- Python 3.9 的 `inspect.isgeneratorfunction` 先解方法、再解 partial，但不会再解 partial 里包着的绑定方法。
- 所以 `partial(obj.gen_method, …)` 在 base 和 gold 下都直接返回假、不报错，即使方法里有返回值。
- 这不在题面描述的症状里，不补断言。若补，gold 会通不过，需要另找正对照，属于扩大需求。

## 8. 严重度判定五步（v1 §4）

| 步 | 结果 | 依据 |
|---|---|---|
| 1 核心要求有无直接断言 | 有（`test_partial` L264） | §3 的 R1、R2 |
| 2 是否只用题面示例字面值 | **是 → S1（T2c）** | `test_1.py:260-264` 与 `user_prompt.txt:15-19` 输入形态相同、期望相同，只有名字不同 |
| 3 退化探测 | **DG-B 预测得 1 → T2b**（conditional，待正式实跑） | §6 |
| 4 已有候选是否违反其它实例或有文档的常用行为 | 我的读取范围内没有真实候选。DG-A 若实跑得 1，就是一个"破坏有文档常用行为"的已构造候选 | §6 |
| 5 | 不适用 | 第 2 步已命中 |

## 9. 问题清单

| 编号 | 严重度 | 内容 | 证据层级 | 去向 |
|---|---|---|---|---|
| T2c | S1 | 唯一的目标断言只用题面示例 | 静态对照 | R-c-1 |
| T2b | S1（待实跑） | DG-B 预测得 1 | 源码推导，待正式评分 | R-c-1 可一并堵住 |
| T5 | 已解释 | 两个 FAILED 键因 `-W ignore` 恒失败，不误拒 | 当前 RH2 日志 ×2，M3 来源镜像 ×2 | 不走 R-a；见 T3 与"待用户决定" |
| T3 | S2 | §3 的 G1、G3 没有键保护（死键，加上 `len(w)==0` 空断言） | 同上 | 登记；可选 R-c-2 |
| G1→T3 | S2 | gold 没修 `warn_on_…` 对 partial 的 `__name__` | 源码推导 | 登记；设计 R-c 时回避 |
| T3 | S2 | 包装绑定方法的 partial 恒返回假（3.9 `inspect` 语义） | 源码推导 | 登记 |
| X1 | 登记 | 见 §11 | 公开包核对 | 训练时控制重复采样；留出按仓库划分 |

## 10. 修订建议（v1 §5）

### R-c-1（必做，属于模板内）

**公开依据**：`user_prompt.txt` L8、L23（"since the partial function does not have a return value"）、L32；docstring `misc.py:216-220`。

**改动**：在 `PRI/hidden_tests/test_1.py` 的 `UtilsMiscPy3TestCase.test_partial` 中，L264 之后追加：

```python
        def cb_with_return(arg1, arg2):
            yield {}
            return 1

        assert is_generator_with_return_value(partial(cb_with_return, arg1=42))
        assert is_generator_with_return_value(partial(cb_with_return, 42))
```

- 键集不变（5 个键），`expected_output.json` 不变。
- 第二行用位置参数绑定，是一个非示例的输入形态，零成本，可选。
- 不对这些 partial 调用 `warn_on_generator_with_return_value`（见 §7 G1）。

**gold 预测能通过**：
- noop 日志已说明，在 3.9 下 `isgeneratorfunction(partial)` 为真。
- gold 会解包到 `cb_with_return`，走的是与已通过的 `cb` 相同的取源码路径。
- AST 中的 `return 1` 不是 None，所以返回真。

**验收**：
- 预期结果：gold=1；noop=0；DG-B=0（在新断言处失败）；DG-A=0；可选加 ALT-1=1。
- 在日志里核对 `test_partial` 确实执行到了新断言。
- 保存新版本、父版本、修订理由和触发反例（即 DG-B 在原版材料上的结果）。
- Codex 复核。

**修订后仍受保护的公开要求**：R1、R2、R3（关键字绑定与位置绑定各一个实例）、G2。G1 和 G3 仍是 S2 缺口。

### R-c-2（可选；针对 S2 缺口，不作为进训练的前置条件）

- **改动**：把 `test_generators_return_something` 的 L44-75 复制成新测试 `test_generators_return_something_detection`。复制到 `assert is_generator_with_return_value(i1)` 为止，不含 warnings 部分。
- expected 增加 `"UtilsMiscPy3TestCase.test_generators_return_something_detection": "PASSED"`。
- **依据**：docstring，以及公开测试 L70-74。
- **为什么是可选**：R-c-1 已经能让"永远返回假"这类候选得 0。R-c-2 只额外防住"对 partial 特判、却弄坏普通生成器"这种较牵强的候选。
- **与 R-a 的关系**：如果协调者想对齐 v1 §10 里 scrapy `9a15fcf8` 的 R-a 先例，可以把"R-a（删掉两个死测试及其键）"和 R-c-2 合并，做成"把有效断言从死键里拆出来"。单做 R-a 对评分没有增益。

### 待用户决定（属于模板外，不阻塞本题）

- R2E runner 里的 `-W ignore`，使所有"裸 `warnings.catch_warnings(record=True)` + 计数"的断言恒为 FAILED。这是池级的共同根因。
- 改 runner 属于改通用评分语义，需要用户决定。
- 建议：先按 §5(a) 的模式做一次池级扫描，列出受影响的键，再由用户决定是否改。
- 本题的处置不依赖这个决定。

## 11. 题目关系（X1）

**本题答案出现在别题初态里**

- `cross_task_gold_scan.json:473-476`：本题 gold 的 5 行全部出现在 `scrapy__75450e75…` 的公开初态中。
- 已核：
  - `PUB75/worktree/scrapy/utils/misc.py:12`（import）与 `:228-231`（解包循环和 `getsource(func)`）。
  - 同一个 `test_partial` 在 `PUB75/worktree/tests/test_utils_misc/test_return_with_argument_inside_generator.py:259`，与 `cross_task_test_scan.json:845` 一致。
- 也就是说，75450e75 的初态里既有本题答案，也有本题测试。

**别题答案出现在本题初态里**

- `scrapy__9a15fcf8…` 的修复（`cross_task_gold_scan.json:455-458`）：本题 `worktree/scrapy/responsetypes.py:25` 有 `'application/x-json': 'scrapy.http.TextResponse'`，而 9a15fcf8 自己的初态里没有。
- `scrapy__e9387529…`：
  - 它的新测试 `test_export_binary`（`cross_task_test_scan.json:864-872`）在本题 `worktree/tests/test_exporters.py:182`。
  - 它的 gold 5 行中有 4 行也在本题初态里（`cross_task_gold_scan.json:485-488`）。

**其它 scrapy 题**：9a15fcf8、e9387529、cfed9b66 三题的初态里还没有 `is_generator_with_return_value` 这个函数，与扫描结果一致。

**影响**：训练时控制这几题的重复采样。留出评测按 D3 以仓库划分，这几题同属 scrapy，自然在同一组。

## 12. 开发条件（方面 6）与交付（方面 7）

**需求**

- 只需改 `scrapy/utils/misc.py`，只用标准库（`functools`、`inspect`）。
- 没有依赖、资产、网络或构建需求。
- 环境（`environment_brief.md`）：`/testbed/.venv` 的 Python 3.9.21，没有 pip，不能出网，agent（uid 54321）可写 `/testbed`。

**最小公开验证（actor 待验）**

- 命令：`python -m pytest tests/test_utils_misc/test_return_with_argument_inside_generator.py`，另加一个**写在文件里**的复现脚本（即题面示例）。
- 注意：如果函数定义在 `python -c` 里，修复后 `inspect.getsource` 会抛 `OSError: could not get source code`，容易被误读成没修好；而 base 上用 `-c` 仍然抛题面的 `TypeError`。
- 公开环境不带 `-W ignore`，按源码推导，公开测试里的 warnings 断言在 base 上应该通过（未实测）。

**证据级别**：评分侧的 current 行已实测。本题没有 devcheck，所以 **actor 侧记为"镜像层面待验"**，不写"环境正常"。

**交付**

- gold 只改一个普通源文件（`projection.included_paths=["scrapy/utils/misc.py"]`），没有构建产物。
- 公开工作树里有 `run_tests.sh`（`worktree_manifest.json` 标为评分面原文）。它会暴露 `r2e_tests` 目录名和 `-W ignore`，但不含答案。

## 13. 用途（v1 §2，初判）

- `problem_localization`: yes
- `capability_comparison`: conditional。还差两个条件：
  - 本题的 actor devcheck。
  - R-c-1 验收通过；或者预先登记事后审计（候选对 `partial(<带返回值的生成器>)` 必须判为真），原始 reward 与语义结果分开列。
- `training_candidate`: no（针对当前材料）。
  - 原因：有未处理的 S1（T2c，T2b 待实跑）。
  - 重评条件：R-c-1 实施、验收并经 Codex 复核，补齐 actor 证据，登记 X1。剩下的 T3 都是 S2 登记项。
- `heldout_candidate`: no。
  - 原因同上的 S1。
  - 修订版只能作为"标明版本的自建评测"。
  - X1 关系（75450e75 的初态含本题答案与测试）按 D3 归入同组。
- `intended_use`: development_diagnostic

## 14. 探针就绪差距

按规则，本批 README §3 在第一步不可读。下面按 v1 §2 的训练候选条件和 §5 的验收要求逐条列出，待协调者对照 README §3：

| 条件 | 现状 | 谁来补 |
|---|---|---|
| 核心要求有决定性断言 | 部分满足：只有示例实例；R-c-1 后满足 | 协调者实施，Codex 复核 |
| 当前版本 noop=0、gold=1 | 原版已满足（2 轮 current，加 M3 参考）；修订版待测 | 协调者 |
| 第 2 步 | 命中 T2c | 由 R-c-1 解决 |
| 第 3 步退化探测 | DG-B 待正式实跑（预测 1）；修订版上预测 0 | 协调者 |
| actor 开发条件 | 没有本题 devcheck | 协调者 |
| X1 登记 | 已核对，待写入题卡 | 主审 / 协调者 |
| 未查范围 | 40 项清单编号、真实模型候选、G1 之外的 scrapy 调用链 | — |

## 15. 最小后续实验（按优先级）

1. 用正式评分在当前材料上跑 DG-B，预期 1，以确认 T2b。
2. 实施 R-c-1，跑 gold、noop、DG-B、DG-A（可选再加 ALT-1），预期依次为 1 / 0 / 0 / 0（ALT-1 为 1）。
3. 跑本题的 actor devcheck：公开测试文件，加上写在文件里的复现脚本。
4. （可选）在当前材料上跑 DG-A，预期 1，用来佐证死键造成的缺口；另做 `-W ignore` 影响范围的池级扫描。
