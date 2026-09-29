# scrapy a95a338e：R-c + R-a（恢复型）修订方案（补 partial 带返回值的非示例实例与绑定方法实例；让被评分命令屏蔽的警告断言恢复生效）

2026-09-29 08:45（+08）· 修订执行者（Claude，单题闭环试行；统一标准 v1 §5 模板内，Claude 执行、Codex 复核）。本版按 Codex 复核"需小改"（`codex_reviews/review_revision_scrapy_a95a.md`）改过一次，第一版草案（08:22）的说法与试跑保留在 §5.3。

**状态：第 2 版草案定稿，试跑验收 9 次全部与预期一致（试跑工具，不是正式评分）。**

- **改动**：一条 `hidden_test_text_replace`（`test_1.py`，两处 edit），加期望映射两键 FAILED → PASSED；键集不变（5 键）。
  - R1（R-c）：`test_partial` 末尾补三条断言。partial 包装带返回值的生成器函数，按位置绑定、按关键字绑定各一条；**本版新增**一条 partial 包装带返回值的绑定方法。
  - R2（R-a 恢复型）：测试类加 `setUp`，让 UserWarning 可见；两个死键的期望改为 PASSED。Codex 已确认 R2 属于现行预授权的 R-a，§8 的决定包不需要启动。
- **正对照改用 C1**（v1 §5 / D4，经独立核实的替代解，依据见 §5.2）。**原 gold 在修订版为 0**：只在新加的绑定方法断言 `HT':286` 失败，原因与范围见 §5.2，已留档。
- **是否需要用户决定**：不需要。
- **待办**：协调者落正式修订单与派生镜像材料、跑正式评分，再送 Codex 收口复核。

路径约定（仓库根相对；`trials/`、`cands/`、`card.md`、`review.md`、`public_read.md`、`analysis_before_history.md`、`reviewer_initial.md`、`revision_draft.json` 相对本目录）：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/scrapy__a95a338eeada7275a5289cf036136610ebaf07eb/`，`W` = `PUB/worktree`。
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/scrapy__a95a338eeada7275a5289cf036136610ebaf07eb/`；`HT` = `PRIV/hidden_tests/test_1.py`（父版本，264 行）；`HT'` = 修订后的 `test_1.py`（第 2 版，286 行）。
- `INV` = `runs/r2e_lifecycle_20260929/inv/scrapy_a95a/`；`DC` = `runs/r2e_lifecycle_20260929/devcheck_rev/unrev/scrapy__a95a338eeada7275a5289cf036136610ebaf07eb/`。
- `v1` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md`；`CX` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/codex_reviews/review_revision_scrapy_a95a.md`。

## 1. 模板与要纠正的误判

| 项 | 模板 | 要纠正的 S1 | 触发反例 | 出处 |
| --- | --- | --- | --- | --- |
| R1 | R-c | T2c：唯一目标断言 `HT:259-264` 只用题面示例（两个参数、只有 `yield {}`、`arg1=42`、结果为假）。T2b：退化候选 D（在 gold 修改的那一行吞掉 `TypeError`、返回 False）得 1 | D 当前材料正式评分 1.0（`INV/ledger_D.jsonl:1`） | `card.md` §4、§5；`review.md` §3 |
| R1（本版新增的一条） | R-c | v1 §4 第 4 步：同一接口、同一 partial 判定要求下的已知漏判。partial 包装带返回值的绑定方法被判为 False，gold 也如此，而当前材料让 gold 得 1 | gold 对 `partial(Holder().meth_ret, 1)` 返回 False（`DC/private_control.json` 的 `diag_partial_variants` 诊断 F，Python 3.9.21） | `CX` §3 |
| R2 | R-a（恢复型） | v1 §4 第 4 步：两个期望 FAILED 的键被评分命令变成死键（T5），True 路径与有文档的警告功能在评分下没有保护；C2（关掉警告）、C3（恒 False）得 1 | C2、C3 当前材料正式评分各 1.0（`INV/ledger_C2.jsonl:1`、`INV/ledger_C3.jsonl:1`） | `card.md` §4；`review.md` §4.1–§4.2；`CX` §1 |

**R1、R2 必须同批**，本版有直接的执行证据：
- **只做 R1 挡不住"关掉警告"**：C2b（以 C1 为底再关掉警告，§5.2）在本版只在两个复活键失败，`test_partial` 的五条断言全部通过（`trials/rev2_C2b.json`）。没有 R2 时，这两个键期望 FAILED，C2b 会是 5/5、得 1。原 C2 以 gold 为底，本版也在绑定方法断言失败，所以单看它已经说明不了 R2 的必要性；C2b 就是为补这一点加的。
- **只做 R2 挡不住 D**：D 在本版只在 R1 新增的 `HT':278` 失败，两个复活键都 PASSED（`trials/rev2_D.json`）。去掉 R1，D 就是 5/5、得 1。
- 这两条由已跑结果推出，没有另外试跑"只 R1""只 R2"两种中间稿。

## 2. 公开依据

### R1：partial 包装"带返回值的生成器"应判为真，包括绑定方法

- **题面的一般表述**：
  - 标题 `PUB/user_prompt.txt:5`；
  - 描述 `:8`：函数应当 "properly determining if the callable is a generator with a return value"；
  - Expected `:23`：示例返回 False 的理由是 "since the partial function does not have a return value"；
  - `:32`："accurately determining the nature of the callable when it is wrapped with `functools.partial`"。
- **函数契约**：docstring `W/scrapy/utils/misc.py:216-220`（生成器函数里有值不为 None 的 `return` 时返回 True，否则 False）。
- **示例只是其中一个实例**（`:15-19`），`HT:259-264` 与它同形。按 v1 §4 第 2 步严格版（D1），要补非示例实例。
- **独立佐证**：没看隐藏测试的公开读者也推出了"partial 包装带返回值的生成器应为 True"（`public_read.md:24`，R3）。
- **三条新断言**：
  - `partial(cb_with_return, 1)`：带 `return 1`，按位置绑定；即主审 `card.md` 附录 A 的 B-1 第二个补丁段，原样使用；
  - `partial(cb_with_return, arg1=42)`：与示例只差"有无返回值"一项（复核 `review.md` §4.4 建议的可选一行）；
  - `partial(Callbacks().method_with_return, 1)`：partial 包装带 `return 1` 的**绑定方法**。本版按 `CX` §3 新增。

**更正第一版的范围说明**：第一版 §2 把"partial 包装绑定方法"与 G1 并列，写成"题面没有要求……加断言属于扩大需求"。这个判断依据不足，本版撤回，理由如下（采纳 `CX` §3）：
- 它与示例是同一个目标接口 `is_generator_with_return_value`、同一条 partial 判定要求。题面的一般表述（`:8`、`:32`）没有把绑定方法排除在外。
- "示例没写""Python 3.9 的 `inspect` 如此""gold 会失败"都不能用来排除它。v1 §5 明确"任何情况下都不为保住 gold 而放宽需求"。
- 已有执行证据证明这是漏判，不是推测：Python 3.9.21 下，方法体含 `yield {}` 和 `return 1`，gold 对 `partial(Holder().meth_ret, 1)` 返回 False（`DC/private_control.json` 诊断 F）。
- 补充观察（不是本条的必要依据）：scrapy 的回调缺省就是 spider 的绑定方法（`W/scrapy/core/scraper.py:163` 的 `spider._parse`），用 partial 给绑定方法预填参数是自然用法。

**仍然不测**：`warn_on_generator_with_return_value` 收到 partial 时的行为（G1）。那是另一个接口的能力，gold 在这里抛 `AttributeError`（诊断项 H），加断言属于扩大需求（`CX` §3、协调者 09-29 指示）。

### R2：让被评分命令屏蔽的警告断言恢复生效

**这些断言保护的是公开行为**：
- 正常警告：公开文档 `W/docs/news.rst:1919-1921`（"Scrapy logs a warning when it detects a request callback or errback that uses yield but also returns a value"）；`warn_on_generator_with_return_value` 的 docstring `W/scrapy/utils/misc.py:247-251`；调用者 `W/scrapy/core/scraper.py:164`、`:169`，每个回调和 errback 都会经过它。
- `IndentationError` 回退警告：依据是公开测试 `W/tests/test_utils_misc/test_return_with_argument_inside_generator.py:251-256` 与 `W/scrapy/utils/misc.py:262-271`。新闻条目推不出这一条（`CX` §1 第 3 条）。
- 公开测试 `:70-74` 断言五个带返回值的生成器判为真，`:76-95` 断言各发 1 条警告并核对文案。
- `HT` 就是这个公开文件加一行 `from functools import partial` 和 `test_partial`（本地 `diff` 只差这两处），所以 `HT:71-75`、`:77-96`、`:252-257` 与公开测试逐字相同。

**为什么恒失败**：
- `PRIV/run_tests.sh:1` 是 `PYTHONWARNINGS='ignore::UserWarning,ignore::SyntaxWarning' .venv/bin/python -W ignore -m pytest -rA r2e_tests`。
- `warnings.catch_warnings(record=True)` 只复制过滤器、不重置。全局的 ignore 过滤器使记录到的警告恒为 0 条。
- 执行证据：所有候选都在 `HT:79`、`:256` 报 `AssertionError: 0 != 1`。
  - 本轮当前材料试跑的 noop 与 gold：`trials/env_noop_current.json`、`trials/env_gold_current.json`；
  - 协调者的 D、C1、C2 正式评分：`INV/logs_{D,C1,C2}/…eval.log`；
  - C3 在更早的 `HT:71` 就失败，状态同样是 FAILED（`INV/logs_C3/…eval.log:57-60`）。这是"死键掩盖 True 路径"最直接的证据。

**改期望状态的独立证据**（`v1:124`："改期望状态要有独立的语义或环境证据，不复制本次 gold 输出"）：
- **解题环境没有这层屏蔽**：agent 身份下 `sys.warnoptions` 为 `[]`，没有 `PYTHONWARNINGS`（`INV/pcheck_warnoptions_agent.json`）。
- **同样的断言在解题环境里有效**：base、agent 身份、正式启动路径下，同名公开测试 4 passed，其中就有这两个测试（`DC/orig/captures/pytest_generator_return_tests.out:11-15`）；gold 下同样 4 passed（`DC/private_control.json` 的 `pytest_generator_return_tests`）。
- **新期望 PASSED 不是 gold 的输出**：在现行 runner 下，gold 这两键的输出是 FAILED（`trials/env_gold_current.json`；协调者正式 L0 `runs/r2e_lifecycle_20260929/env_verify/ledger_l0_gold.jsonl:13`）。修订后 noop 也让这两键 PASSED（`trials/rev2_noop_{1,2}.json`），说明期望反映的是 base 已有的公开行为，与修复无关。

**改法与项目惯例一致**：项目自己的公开测试就用同一手法让警告可见，例如 `W/tests/test_spider.py:32-36`（`setUp` 里 `simplefilter("always")`，`tearDown` 里 `resetwarnings()`）、`W/tests/test_http_request.py:1288-1290`、`W/tests/test_spidermiddleware_offsite.py:84-85`。R2 比这些更窄：用 `catch_warnings()` 包住、`addCleanup` 复原，只放开 UserWarning。

**模板归属：R-a，Codex 已确认**（`CX` §1）：
- 断言原文不变，过滤器按测试恢复，五键不变，不改通用评分规则，不属于 R-d。
- `v1:124` 明确允许凭独立语义或环境证据改期望状态，不是"R-a 只准删测试、删键"。

## 3. 具体改动

- **目标文件**：`r2e_tests/test_1.py`，即唯一的隐藏测试文件 `HT`；`__init__.py` 不动。
- **草案条目**：**一条** `hidden_test_text_replace`，两处 edit，按顺序应用，每处 `old` 在当时文本里恰好出现一次。见 `revision_draft.json` 的 `revisions`，与试跑输入 `trials/inputs/draft_a95a_r1r2_v2.json` 逐字相同（已用脚本比对）。
- **与主审草案的关系**：Edit 1 与 Edit 2 的前 6 行，等于 `card.md` 附录 A 的 B-1 原样应用（在仓库外副本上 `git apply` 后逐行 `diff` 核过）；Edit 2 另加关键字绑定一行和绑定方法三段。

**Edit 1（R2，不变）**：在类头与第一个测试之间插入 `setUp`（`HT'` 43–50 行）。

```python
class UtilsMiscPy3TestCase(unittest.TestCase):

    def setUp(self):
        # run_tests.sh runs pytest with `-W ignore` and PYTHONWARNINGS=ignore::UserWarning,
        # so the UserWarnings recorded below were never visible; re-enable them per test.
        catcher = warnings.catch_warnings()
        catcher.__enter__()
        self.addCleanup(catcher.__exit__, None, None, None)
        warnings.simplefilter("always", UserWarning)

    def test_generators_return_something(self):
```

**Edit 2（R1）**：在 `test_partial` 末尾追加（`HT'` 273–286 行；281–286 行是本版新增）。

```python
        partial_cb = partial(cb, arg1=42)
        assert not is_generator_with_return_value(partial_cb)

        def cb_with_return(arg1, arg2):
            yield {}
            return 1

        assert is_generator_with_return_value(partial(cb_with_return, 1))
        assert is_generator_with_return_value(partial(cb_with_return, arg1=42))

        class Callbacks:
            def method_with_return(self, arg1, arg2):
                yield {}
                return 1

        assert is_generator_with_return_value(partial(Callbacks().method_with_return, 1))
```

**行号对照**：`setUp` 插入 8 行，原文件第 43 行起的行号都加 8。

| 位置 | 原 `HT` | 修订后 `HT'` |
| --- | --- | --- |
| 第一条 True 断言 | `:71` | `:79` |
| 第一条"1 条警告"断言 | `:79` | `:87` |
| `IndentationError` 回退的计数断言 | `:256` | `:264` |
| 题面示例断言 | `:264` | `:272` |
| R1 位置绑定 / 关键字绑定 / 绑定方法 | — | `:278` / `:279` / `:286` |

**设计说明**：
- **`setUp` 的作用范围**：一处改动覆盖全部 22 个 `with warnings.catch_warnings(record=True) as w:` 块，断言原文不改。
- **机制**：内层记录块进入时复制当时的过滤器，`setUp` 插在最前面的 `always` 过滤器随之生效；每个测试结束时 `addCleanup` 复原，后进先出，此时内层块都已退出。这是源码推断；生效与否以试跑为准，两版试跑中两个复活键在 gold、C1、noop 下都 PASSED。
- **只放开 UserWarning**：被测的两条警告都用 `warnings.warn` 的默认类别 UserWarning（`W/scrapy/utils/misc.py:254-261`、`:264-271`）。放开全部类别，会让垃圾回收时的 ResourceWarning、库里的 DeprecationWarning 混进"0 条 / 1 条"计数（`review.md` §4.3）。代价见 §6 的类别约束。
- **绑定方法断言的写法**：`Callbacks` 定义在测试方法内，与 `cb_with_return` 同处；pytest 只收集 `unittest.TestCase` 子类（`W/pytest.ini:5` 的 `python_classes=` 为空），不会把它当测试类。它只断言 True 这一面，没有配"无返回值绑定方法为 False"的反例：`CX` 要的是窄断言，而且目前没有会对无返回值方法误报 True 的具体候选。
- **与 `mock.patch` 的关系**：`test_indentation_error` 的装饰器在调用测试方法时才生效，晚于 `setUp`，两者互不影响。
- **不引入新依赖或时序**：不依赖 `tests/` 下的 base 测试辅助；不起网络、线程或定时器。

## 4. 期望映射逐键变化

| 键（均省略 `UtilsMiscPy3TestCase.`） | 修订前 | 修订后 | 依据 |
| --- | --- | --- | --- |
| `test_generators_return_none` | PASSED | PASSED | 不变；R2 后其中 8 个"0 条警告"断言变为有效 |
| `test_generators_return_none_with_decorator` | PASSED | PASSED | 不变；同上，8 个 |
| `test_partial` | PASSED | PASSED | 状态不变；R1 的三条新断言并入此键 |
| `test_generators_return_something` | FAILED | **PASSED** | 公开测试 `:70-95`、docstring、`news.rst:1919-1921`；解题环境下 base 与 gold 都通过 |
| `test_indentation_error` | FAILED | **PASSED** | 公开测试 `:251-256`、`W/scrapy/utils/misc.py:262-271`；同上 |

- **键集不变**（5 键），没有 added / removed。正式修订单的 expected 部分：`changed` 为这两键（FAILED → PASSED）。修订后期望里不再有非 PASSED 键。
- **期望从哪里来**：两个复活键来自公开测试原文与解题环境的执行结果（§2 R2），不是 gold 在评分命令下的输出；`test_partial` 的三条新断言由题面一般表述与 docstring 推出。gold 在修订版上反而是 0（§5.2），期望显然不是照 gold 输出写的。
- **版本记录**：

  | 文件 | sha256 |
  | --- | --- |
  | 父版本 `test_1.py`（`HT`，264 行） | `baf73412…` |
  | 父版本 `expected_output.json`（5 键） | `2c5d045c…` |
  | 父版本隐藏测试树 | `63928e22…`（按 `rh2/src/repoharness2/envpack/bundles_v2.py:158` 的定义在本地复算一致）；`material_revisions` 为空 |
  | `run_tests.sh`（不变） | `8285765f…` |
  | 修订后 `test_1.py`（`HT'` 第 2 版，286 行） | `9ce38e46…` |
  | 修订后隐藏测试树（本地复算） | `33628b69…` |
  | 试跑用 `trials/inputs/draft_a95a_r1r2_v2.json` | `85d755d1…` |
  | 试跑用 `trials/inputs/expected_after_a95a.json`（两版共用） | `95f7d31f…` |
  | 第一版草案 `trials/inputs/draft_a95a_r1r2.json`（已被取代） | `d9ff9044…`，对应 `test_1.py` `e9ec1c06…` |

  父版本与当前正式材料 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl:46` 一致；本题至今没有材料修订。全长哈希见 `revision_draft.json`。

## 5. 验收计划与试跑结果

**试跑环境**：
- **工具**：`rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`（远端 `/work/code/rh2`），只作试跑。与正式评分的差别见其文件头：不做基线重建比对，不核隐藏测试树与入口摘要，权限布置简化。
- **对 R2 有效**：它以评分用户 54322 在标记之间执行的就是来源入口 `bash run_tests.sh`，含 `-W ignore` 与 `PYTHONWARNINGS`。日志头为 Python 3.9.21、pytest 8.3.4。
- **镜像**：派生镜像 `sha256:d7f8d826…`，配方 `r2e_derive_v1+sysconfig_v1`，与 `INV` 下四份正式账本的 `image_id_actual` 相同。
- **补丁**：都从磁盘原件直接上传（`PRIV/gold.patch` 与 `cands/` 下 5 个，sha256 见 `revision_draft.json`）。新写的 `cands/scrapy_a95a_C2b.patch` 用 `diff -u` 生成，在仓库外的 base 副本上 `git apply --check` 通过，应用后与预期文件逐字节相同、`py_compile` 通过。
- **完整性**：每次 `RH2_APPLY_RC=0`；修订草案每次 `RH2_TRIAL_EDITS_APPLIED=1`；每次 5 键全部解析，没有 missing / extra；日志尾部都完整，没有被截断。
- **时间**：第 2 版 2026-09-29 08:37–08:41（+08），同时最多 2 个；单次墙钟 36–49 s，其中测试 2.5–3.1 s。

### 5.1 当前材料上的对照（不进 acceptance）

| 候选 | 结果 | 出处 |
| --- | --- | --- |
| noop | 0：只差 `test_partial`（FAILED，题面 TypeError，`HT:264`）；两个死键在 `:79`、`:256` 报 `0 != 1`，与期望的 FAILED 一致 | `trials/env_noop_current.json` |
| gold | 1：5/5；两个死键同样在 `:79`、`:256` 失败 | `trials/env_gold_current.json` |
| D、C1、C2、C3 | 都是 1.0，5/5 | `INV/ledger_{D,C1,C2,C3}.jsonl:1`（协调者正式评分） |

环境与协调者正式 L0（`runs/r2e_lifecycle_20260929/env_verify/ledger_l0_{noop,gold}.jsonl:13`）一致。

### 5.2 第 2 版草案下的验收

**正对照 C1 的核实依据**（v1 §5 / D4"经独立核实的合理替代解"）：
- **做法**：`cands/scrapy_a95a_C1.patch` 先逐层展开 `functools.partial`，再对展开后的对象做 `inspect.isgeneratorfunction` 与 `inspect.getsource`，缓存仍以原 callable 为键。非 partial 输入时展开后的对象就是它本身，与 base 走同一路径，所以非 partial 的判定与 base 相同。`warn_on_generator_with_return_value` 的名字取展开后函数的 `__name__`；普通函数的文案与 base 相同，仍经模块全局名调用 `is_generator_with_return_value`（mock 照常生效）。只改 `scrapy/utils/misc.py`。
- **满足哪些公开要求**：题面示例为 False、不抛错；partial 包装带返回值的生成器函数或绑定方法为 True。Python 3.9 下 `inspect.isgeneratorfunction` 对绑定方法返回 True，`inspect.getsource` 也接受绑定方法，所以先展开的写法能分析到方法体（源码推断，试跑确认）。
- **独立来源**：主审（`analysis_before_history.md` §8 与附录 A-2）与独立复核（`reviewer_initial.md` §6 的 ALT-1）两个互不继承上下文的会话，各自给出同一做法。它写于 06:34，早于绑定方法断言，不是照着新测试写的。`CX` §4 第 2 条也认为源码与函数级核对支持此路径。
- **执行证据**：私有语义对照 `True False True / 1`，与 gold 相同（`INV/pcheck_semantics_C1.json`）；当前材料正式评分 1.0（`INV/ledger_C1.jsonl:1`）；第一版草案试跑 5/5（`trials/rev_C1.json`）；本版试跑两次 5/5（`trials/rev2_C1_1.json`、`trials/rev2_C1_2.json`）。本版测试含复活的公开测试原文，所以 C1 在评分命令下也通过了全部公开测试断言。
- **没核的**：C1 下以 agent 身份跑公开开发命令（devcheck 的私有对照只跑了 gold）。

**原 gold 在修订版为 0（留档）**：
- **范围**：只差 `test_partial` 一个键，只在新加的绑定方法断言 `HT':286` 失败（AssertionError）；`:272`（题面示例）、`:278`、`:279`（partial 包装普通生成器函数）都通过，其余 4 键都 PASSED（`trials/rev2_gold.json`）。
- **原因**：gold 先对 partial 本身调用 `inspect.isgeneratorfunction`，再展开 partial 取源码（`PRIV/gold.patch` 第 2 个 hunk）。Python 3.9.21 下，partial 包装绑定方法时这个调用返回 False，gold 不分析源码、直接缓存 False。执行证据：`DC/private_control.json` 诊断 F（`partial(Holder().meth_ret, 1)` → False）与 `trials/rev2_gold.json`。
- **处理**：按 v1 §5 与 D4，不为保住 gold 放宽需求，正对照改用 C1；`revision_draft.json` 的 `gold_on_revised` 记录了失败位置与原因，`env_reverify_positive_control` 写明以后批量环境复验本题用 C1（`cands/scrapy_a95a_C1.patch`，sha256 `33457199…`）。

**验收表**（键名省略 `UtilsMiscPy3TestCase.`；行号是 `HT'` 的；结果文件为 `trials/rev2_<候选>.json`，C1、noop 各两份，带 `_1`、`_2`）：

| 候选 | 补丁 | 角色 | 应得 | 应不符的键（失败位置） | 试跑结果 | 当前材料 |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | `cands/scrapy_a95a_C1.patch` | **正对照**（替代解） | 1 | — | 1，5/5，两次 | 1（正式） |
| gold | `PRIV/gold.patch` | 原 gold，已知遗漏 | 0 | `test_partial`（`:286`） | 0，恰好此键，`:286` AssertionError | 1 |
| noop | 无 | — | 0 | `test_partial`（`:272`，题面 TypeError） | 0，恰好此键；两个复活键 PASSED；两次相同 | 0 |
| D | `cands/scrapy_a95a_D.patch` | 第 3 步退化候选，R1 的触发反例 | 0 | `test_partial`（`:278`） | 0，恰好此键；两个复活键 PASSED | **1**（正式） |
| C2 | `cands/scrapy_a95a_C2.patch` | 第 4 步构造（gold 加关掉警告），R2 的触发反例 | 0 | `test_generators_return_something`（`:87`）、`test_indentation_error`（`:264`）、`test_partial`（`:286`） | 0，恰好这三键 | **1**（正式） |
| C2b | `cands/scrapy_a95a_C2b.patch`（本版新写） | 第 4 步构造（C1 加关掉警告） | 0 | `test_generators_return_something`（`:87`）、`test_indentation_error`（`:264`） | 0，恰好这两键，都是 `0 != 1`；`test_partial` PASSED | 未跑 |
| C3 | `cands/scrapy_a95a_C3.patch` | 第 4 步构造（恒 False） | 0 | `test_generators_return_something`（`:79`，即原 `:71`）、`test_partial`（`:278`） | 0，恰好这两键 | **1**（正式） |

**C2b 补丁**（sha256 `60771ab4…`）：在 C1 的基础上，于 `warn_on_generator_with_return_value` 的 docstring 之后插入 `return`。违反的公开要求与 C2 相同：带返回值的生成器回调不再发警告（`news.rst:1919-1921`、公开测试 `:76-95`、`:251-256`）。加它的原因见 §1：原 C2 以 gold 为底，本版也会在绑定方法断言失败，单看 C2 已经分不清是 R1 还是 R2 挡住了"关掉警告"。

**判读**：
- **正对照 1、noop 0**：成立，各两次一致。noop 的两个复活键 PASSED，证明 R2 不依赖修复。
- **误判已纠正**：D、C2、C3 在当前材料正式评分都是 1.0，本版都是 0：
  - D 只在 R1 的位置绑定断言；
  - C3 在复活的 True 断言与 R1 的位置绑定断言；
  - C2 在两个复活键和绑定方法断言；
  - C2b 只在两个复活键，说明 R2 仍然必要。
- **已知漏判已纠正**：原 gold 式实现（先判 partial、后展开）在绑定方法实例上被拒，并且只在这一处。
- **没有误拒**：C1 仍为 1。
- **旧键不受影响**：两个 PASSED 回归键在本版 9 次试跑中都是 PASSED。R2 使其中 16 个"0 条警告"断言变为有效，没有候选因此失败。
- **未跑**：复核初判的 DG-A 与 C3 同类；ALT-1、ALT-2 与 C1 同类（先展开 partial，或对 `.func` 递归），按静态判断本版得 1。若有"先判 partial、再展开一层"的写法（例如复核的 ALT-3 按 gold 的顺序实现），会与 gold 一样在 `:286` 被拒；这是本版要纠正的漏判本身，不是误拒。

### 5.3 第一版草案（已被取代，保留记录）

- **内容**：R1 只有位置绑定与关键字绑定两条（`test_1.py` `e9ec1c06…`，279 行），R2 相同；正对照是 gold。
- **试跑**（08:03–08:13）：`trials/rev_gold_{1,2}.json` 5/5；`trials/rev_noop_{1,2}.json` 只差 `test_partial`；`trials/rev_D.json` 只差 `test_partial`（`:278`）；`trials/rev_C1.json` 5/5；`trials/rev_C2.json` 恰好两个复活键；`trials/rev_C3.json` 在 `:79` 与 `:278`。当时第一次试跑就是 gold，确认了 R2 在 pytest 8.3.4 下生效；这一结论本版不变。
- **为什么被取代**：Codex 复核（`CX` §3）指出，把 partial 包装绑定方法写成"扩大需求"依据不足，gold 在这一已知漏判上仍得 1。本版按 §2 补上，正对照改为 C1。

## 6. 修订后仍受保护的公开要求与剩余事项

**受保护的公开要求**（键名省略类名，行号是 `HT'` 的）：
- **partial 包装无返回值的生成器 → False、不抛错**：`test_partial` `:272`（题面示例）。
- **partial 包装带返回值的生成器函数 → True**：`test_partial` `:278`（位置绑定）、`:279`（关键字绑定）。
- **partial 包装带返回值的绑定方法 → True**：`test_partial` `:286`。
- **非 partial 带返回值 → True**：`test_generators_return_something` `:79-83`。覆盖顶层函数、嵌套函数、docstring 缩进浅于代码、嵌套 helper 里的 return 不计入。
- **非 partial 的 False 判定**：`test_generators_return_none`、`test_generators_return_none_with_decorator`。覆盖无返回值、`return None`、裸 `return`、`yield from`、非生成器、被非生成器装饰器包住。
- **带返回值的生成器回调发 1 条警告，文案为 `The "NoneType.<名字>" method is a generator`**：`test_generators_return_something` `:85-104`。
- **不该警告时发 0 条**：两个 `return_none` 键里的 16 个计数断言。R2 前它们在 `-W ignore` 下恒真，现在生效，能挡住"对什么都发警告"的候选。
- **`IndentationError` 时发 "Unable to determine" 回退警告**：`test_indentation_error` `:264-265`。

**残余与登记**（都不阻塞本题，按 S2 或登记处理）：
1. **类别约束（R2 带来，低风险）**：`setUp` 只对 UserWarning 设 `always`。若候选把这条警告改成非 UserWarning 类别，例如 `ScrapyDeprecationWarning`（继承 `Warning`，`W/scrapy/exceptions.py:80`），解题环境的公开测试能记录到，评分时却会被 `-W ignore` 丢掉而判 0。题面没有要求改类别，base 用的是默认类别，所以只登记（`review.md` §4.3、`CX` §3）。
2. **随复活而生效的既有约束**：都在公开测试里原样存在，解题者跑公开测试就能看到，按 v1 不算 T1，登记即可。
   - 警告文案：`HT':88`、`:92`、`:96`、`:100`、`:104` 的 5 处 `assertIn`；
   - `test_indentation_error` 用 `mock.patch` 替换模块全局名，要求 `warn_on_…` 经模块全局名调用 `is_generator_with_return_value`。
3. **G1（另一个接口的能力，不加断言）**：`warn_on_generator_with_return_value` 收到"partial 包装带返回值的生成器"时抛 `AttributeError`（partial 没有 `__name__`），gold 也如此（`DC/private_control.json` 诊断项 H）。C1 顺带修了这一点，但不作为要求。
4. **partial 路径的其它形态**（边缘实例，T3）：`return None`、嵌套 helper 里的 return 只在非 partial 路径上有断言；partial 包装无返回值的绑定方法没有 False 方向的断言；partial 子类、带 `__dict__` 的嵌套 partial 没有断言。例如只对 partial 用"源码里有没有 return 字样"判断的候选能通过 R1（`review.md` §5）。
5. **P4、E1 照旧登记**（`card.md` §4）：
   - P4：示例要写成文件运行，修好后用 `python -c` 会得到 `OSError`；
   - E1：`CrawlerProcess.start()` 因 Twisted 缺 `_handleSignals` 不可用，与修复无关。
6. **X1**：
   - `scrapy__75450e75` 的公开初态含本题 gold 与原版隐藏测试（逐字）；本题初态含 `9a15fcf8`、`e9387529` 的修复。
   - R1 的新测试文本是新写的：按 `cb_with_return` grep 了 v3 的 5 个 scrapy 公开工作树，没有命中。
   - 75450e75 的初态就是 gold 的写法，所以在本修订版上它也会在 `:286` 失败；这只影响两题关系的说明，不改变按 D3 同组的处理。
7. **池级线索（不属本题）**：复核建议在各题隐藏测试里查"裸 `catch_warnings(record=True)` 且没有 `simplefilter`"的写法，看还有哪些断言被 R2E runner 的 `-W ignore` 变成死键或恒真（`review.md` §5）。由协调者决定是否做。

## 7. 边界与交接

- **只做 v1 §5 模板内的 R-c 与 R-a（恢复型）**：
  - 不改题面、`run_tests.sh` 和解析器；
  - 不删键，不放宽已有断言；
  - 期望不是抄 gold 输出，gold 在本版是 0（§4、§5.2）。
- **没有越界**：没写 `s2_r2e` 下的正式修订单与 pins，没改生产代码。远端只用了建目录、上传、试跑与取回结果这几类命令，文件都在 `/work/r2e/trials/lc_scrapy_a95a/a95a338e/`。
- **新增文件**：`cands/scrapy_a95a_C2b.patch` 与 `trials/inputs/*` 是用 `cp` 从 scratchpad 原件复制的（逐字节），没有经过 Write 工具，以保住 diff 里只含一个空格的上下文行。
- **协调者待办**：
  1. 把 `revision_draft.json` 的 `revisions` 落为一条 `hidden_test_text_replace`（目标 `test_1.py`，前摘要 `baf73412…`，后摘要 `9ce38e46…`）；按 `expected_after` 落期望映射（`changed` 两键）；修订说明注明正对照为 C1、gold 在修订版为 0；
  2. 重建材料与派生镜像；
  3. 正式评分：C1 ×2、noop ×2、gold、D、C2、C2b、C3，按 §5.2 判读（gold 应为 0，只在 `test_partial`）；
  4. 送 Codex 收口复核；
  5. 以后批量环境复验本题时，正对照改用 C1（`revision_draft.json` 的 `env_reverify_positive_control`）。
- **之后重判 v1 用途**（按 `card.md` §1、`review.md` §7）：
  - 训练候选要的正面证据（核心断言、noop 0 / 正对照 1、第 2、3 步结果）届时齐全，正对照是 C1；
  - 修订版只能作"标明版本的自建题"；
  - 留出评测仍受 D3 按仓库划分的限制，并与 `75450e75` 同组；
  - 改用修订版做能力比较时，不再需要预先登记事后审计。

## 8. 模板外决定包：未启动

第一版在这里准备了"若 Codex 判 R2 不在 R-a 内"的决定包（方案 A–E）。Codex 已确认 R2 属于现行预授权的 R-a（`CX` §1），所以不需要启动。其中的判断仍成立，留作记录：只做 R1，或删掉两个死测试和两个键，都挡不住"关掉警告"的候选；本版 C2b 的试跑是直接证据。
