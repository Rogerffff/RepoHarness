# L1_mypy_1 · 逐题静态审查小结

范围：python/mypy 20 题（ASSIGNMENT.json 顺序）。方法：先只看 `problem_statement` + base 代码写 `public_view`，再读 `test_patch` / `fail_to_pass` / `pass_to_pass` / `golden_patch` / `hints_text`。
base 代码用裸克隆的 `git grep <base_commit>` / `git show <base_commit>:<path>` 读取（COMMON.md 允许的只读操作），未建 worktree。
逐题记录：`records/<instance_id>.json`。辅助产物在 `runs/env_overnight_20260916/L1_mypy_1/`：
`kcheck_all.txt`（`-k` 子串过选核查）、`dupidx.txt`（40 道 mypy 题的 test_patch/gold 路径与 base_commit 交叉索引）、`mat/`（四面材料抽取）。

| task | 主要发现 | 建议处置 | 下一实验 |
| --- | --- | --- | --- |
| python__mypy-11236 | **P2P 为空**（零回归保护）；test_patch 改写的既有 case `testLiteralFinalGoesOnlyOneLevelDown` 既不在 F2P 也不在 P2P；F2P 用精确错误文本 `got "Tuple[bool, int]"` 锁死 subtypes 层修法，作者在 hints 里首选的 `visit_tuple_expr` splice 方案会被判 0 | needs_repair | 用刻意放宽的假修复（`visit_instance` 对 LiteralType 直接 return True）跑 check-literal.test 全量，验证补 P2P 能否拦下 |
| python__mypy-11352 | **F2P 与题面矛盾**：题面写 "non-async counterpart ... does not produce any errors"，F2P 却含同步 `testContextManagerWithGenericFunctionAndSendType`；只做 hints 里的 two-line fix 仅过 1/3 F2P。**题面整段重复两遍**（3984 字符 = 1992×2 逐字相同）。base 里唯一相关既有用例 `testContextManagerWithGenericFunction` 未入 P2P | needs_repair | 只加 fullname 判断（不加 detach_callable），跑三条 F2P 验证 1 过 2 挂 |
| python__mypy-12741 | **题面截断**在半句话 "…maybe some reasoning about"；**题面与评分方向相反**：正文抱怨 `Invalid statement in TypedDict definition` 这条错误，F2P 恰恰要求保留它（真正目标是"别崩溃"，正文里没有任何 traceback，只有标题有 Crash 一词）；gold 改的是全局热点 `CallableType.__hash__`，P2P 只有 1/177 条 | needs_repair | 把 `__hash__` 改成 `return 0` 跑当前 F2P+P2P，验证评分会放行 |
| python__mypy-16869 | 题面质量最好的一题（完整 traceback + 最小复现），F2P 断言的是对外可见 stub 文本、未锁实现。但 **eval_cmd 缺 `-n0`**：mypy 各版本 pytest 配置都有 `addopts=-nauto`，40 题里 6 道 version≥1.8 的题（16555/16869/16905/16963/16966/17071）会在 xdist 并行下评分；test_patch 往 `mypy/test/teststubgen.py` 注入了 `pytest.skip()`，需确认 SKIPPED 不被当作通过 | ready_for_probe | 同机对比 `pytest -rA -k` 与 `pytest -n0 -rA -k` 跑 gold 的逐 case 状态、耗时与峰值内存 |
| python__mypy-10174 | 题面/gold 都干净，stage1 gold=RESOLVED_FULL。但 **F2P 是"无输出"负向断言**（题面代码原样），**P2P 两条 `testUnimportedHintAny*` 与被改的 `is_overlapping_types` 毫无关系** → `_is_overlapping_types` 开头 `return True` 之类的假修复可拿满分。由此确认仓库级机制：40/40 道 mypy 题的 F2P∪P2P 都落在"test_patch 中出现的 case 名 + `-k` 子串过选闭包"内，14/40 题 P2P 为空 | needs_repair | 写 3 个假修复跑当前 F2P+P2P，预期全部满分，形成反例 |
| python__mypy-10284 | 题面只要求 `type(x) == T` 的 if 分支窄化，**F2P 8 条**却还要求 `is`/`!=`/`is not`/链式比较，以及"**else 分支只有被比较类型是 `@final` 时才可窄化**"这条题面完全没提的类型安全规则；gold 改的是窄化总入口 `find_isinstance_check`，P2P 只有 1 条且是新增用例 → 既有窄化行为零保护。另发现两个 case 写了重复 `[builtins ...]` 段（data.py:69-75 后者覆盖前者） | needs_review | 只实现题面字面要求（`==` 的 if 分支），统计 8 条 F2P 通过数（预期 ≤3） |
| python__mypy-10308 | **材料不完整**：上游 commit c0490b4c2 新增的 `test-data/unit/fixtures/object_hashable.pyi` 在 test_patch 与 gold 里都缺失，而 test_patch 引入的 `[case testHashable]` 正依赖它（data.py 会 FileNotFoundError）——当前不影响判分（testHashable 未入 F2P/P2P），但"整文件跑"的 P2P 方案会立刻炸。F2P 用 `[out]` 段断言 10 行精确诊断，题面却只描述崩溃；**P2P 为空**；gold 自称 "Trivial check that circumvents the bug" 是绕过而非根因修复 | needs_repair | base+test_patch 跑 `-k testHashable` 验证 FileNotFoundError；补 fixture 后确认 fail→pass |
| python__mypy-10382 | 题面（485 字符，直接点根因）、gold（2 行）、F2P（只断言标准诊断文本）三者干净对应，是本包质量最好的题之一。**唯一缺陷：P2P=0**，而 gold 改的是 `semanal.visit_import_from` —— 所有 from-import 的公共路径；丢掉 `id == as_id == '__all__'` 限定的放宽版修复也能拿满分 | needs_repair（仅补 P2P） | 跑放宽版修复，验证当前 F2P 通过而 check-modules.test 整文件大面积失败 |
| python__mypy-10392 | **本包里 P2P 唯一真正有判别力的一题**：F2P 是 Py2 模式下 `xx/@python2/m.pyi` 生效，P2P 是 Py3 模式下必须落回 `xx/m.pyi` —— 去掉 `if options.python_version[0] == 2` 守卫会让 P2P 失败。题面（维护者写的功能需求）把优先级/回退/模式区分三条都写清了。小缺口：题面要求 MYPYPATH 也生效，测试只覆盖 config 的 `mypy_path`；上游 PR 的 `docs/source/running_mypy.rst` 改动被丢弃 | ready_for_probe | 在 gold 上用 `MYPYPATH=tmp/xx` 复跑同一输入，确认行为一致 |
| python__mypy-10401 | **182 个 stage1 任务目录里唯一 gold/empty 两侧都没有 test_output.txt 的题**——ledger 记 `infra_failed:run_stopped` / `wall_deadline`（批次截断，不是题目缺陷），目前零实跑证据。题面与 gold 质量好；但 P2P 仅 `testAssignEmptyBogus`（`() = 1`）与被改的 `join_types` 无关。另：**10392 的上游修复 commit 就是本题的 base_commit**（mypy 40 题里这种精确相邻只有 10392→10401 与 16963→16966 两对；11824 与 11857 共用同一 base），拆分训练/评测集时必须同侧 | needs_repair | 单独补跑 stage1；并在 `join_types` 开头 `return AnyType` 验证当前评分放行 |
| python__mypy-10424 | **本包最容易被一行破坏性改动骗过的题**：F2P 的 5 条断言全是"保持 `Type[__main__.C]`"即"什么都不要窄化"，P2P=0 → 在 `meet.narrow_declared_type` 开头写 `return declared` 即可满分，代价是整个 mypy 的 isinstance 窄化失效。题面/gold 本身正确（gold 注释 "We'd need intersection types, so give up."）。meet.py 一族本包共 3 题（10174/10424/10658），互为天然回归集 | needs_repair | 直接跑 `return declared` 版假修复，预期 RESOLVED_FULL |
| python__mypy-10430 | 题面线索（traceback + "第三次运行" + "re-export from `__getattr__`"）与 gold（`VAR_FLAGS` 里补一个字符串 `'from_module_getattr'`）匹配得好，是本包定位难度合理的一题。缺口：F2P 三段期望输出全空（纯负向），改 `lookup.py:47` 的 assert 静默返回也能过；**P2P 9 条全是 `testAddedMissingStubs*` 同族**——diff 上下文只有 1 个 case 名，多出的 8 条恰是它的 `-k` 子串过选集合，这是 P2P 生成机制的最清楚证据 | ready_for_probe（建议补 P2P） | 写"assert 改静默返回"的假修复跑当前 F2P+P2P |
| python__mypy-10478 | 题面质量高（引 PEP 591 + **逐字给出期望错误文本**），gold 只有 5 行且复用 base 已有的 `is_classvar`，F2P 里 2/3 条断言是既有行为的回归保护。唯一缺口：**P2P=0**，而 gold 改的 `unwrap_final` 是所有 `Final` 声明的必经路径，同文件现成有 67 个 case 可直接纳入——本包里补回归成本最低的一题。test_patch 末尾 `\ No newline at end of file`（卫生问题） | ready_for_probe（仅补 P2P） | gold 上跑 check-final.test 全量取基线通过集 |
| python__mypy-10658 | **题面与评分直接冲突**：题面写 "should be narrowed to **A**"，F2P 却断言 `Revealed type is "T`-1"`；题面抱怨 `<nothing>`，F2P 又要求 `b: B` 分支保留 `<nothing>`（因为 `is_subtype(T.upper_bound=A, B)` 为假）——两条都无法从公开材料推出。**与 10424 是同一函数 `meet.narrow_declared_type` 的连续两次修补**，本题 base 已含 10424 的 gold 与其测试；加上 10174（改它调用的 `is_overlapping_types`），三题是 meet.py 同族，划分必须同侧。P2P=0 | needs_repair | 实现题面字面要求（TypeVar 时 `return declared`）跑 F2P，确认第一条断言即失败 |
| python__mypy-11241 | **本包"要求不可推断"最严重的一题**：gold 既没让 `Annotated[int, 3:4]` 合法，也没改变"报错并中止"的结果，只是把诊断文本从 `syntax error in type comment` 换成 `Slice usage in type annotation is invalid`；F2P 三条逐字匹配这句题面里从未出现的话。题面标题写 Crash 但正文展示的是普通错误。另：既有 case `testIncorrectTypeCommentIndex` 的期望被 test_patch 改写却未入 F2P/P2P。P2P 质量反而较好（含 AST dump 级的"正确切片不受影响"断言） | reject_revision（除非改题面+放宽断言） | 让模型各跑一次，统计猜中该字符串的次数（预期 0） |
| python__mypy-11420 | **P2P 选错对象最清楚的例子**：`testNewReturnType1`~`9` 九条与本次改动一一对应的既有用例就在插入点正上方，一条都没进 P2P；进 P2P 的是插入点下方的 `testGenericOverride` 及其 4 个子串过选（与 `__new__` 无关）。gold 完整（`INVALID_NEW_TYPE`、`type_type()` 在 base 已有）。次要问题：F2P 的 11/12（裸 `type` 应通过、`int` 应报 `subtype of "type"`）在题面无依据 | needs_repair（补 P2P 性价比最高） | base/gold 各跑 `testNewReturnType1..9` 确认双侧 PASSED 后入 P2P |
| python__mypy-11434 | **P2P 设计最贴切的一题之一**：两条 P2P 都是针对 gold 新分支边界条件构造的反向用例——`testSelfTypeVarIndexExpr` 专门覆盖"bound 自带 `__getitem__`"，去掉 `not has_member(upper_bound, "__getitem__")` 守卫就会失败。gold 三行、不依赖未交付改动。缺口：Union bound 的期望（`Union[builtins.int, builtins.str*]`）题面无依据；同文件 46 条既有 case 未入 P2P；三条 case 写了重复 `[builtins ...]` 段（与 10284 同型）。hints 里直接点名了 `visit_index_with_type` 与递归 bound 的修法，而 hints 不可见 | ready_for_probe | gold 上跑 check-typevar-values.test 全量取基线 |
| python__mypy-11567 | 题面自带 traceback 与准确诊断（"astdiff.py hasn't been updated to deal with ParamSpecExpr"），gold 只加一个分支，**F2P 只断言 diff 结果的符号集合而不是快照内容 —— 对实现最宽容的一题**。缺口：P2P=0（diff.test 有 71 条现成 case），且给 ParamSpecExpr 返回常量快照的假修复也能过 F2P（会让两个不同 ParamSpec 之间的变化在 daemon 里漏报） | ready_for_probe（补 P2P） | 用常量快照 `('ParamSpec',)` 的假修复跑 F2P，预期通过 |
| python__mypy-11707 | **"题面与评分方向相反"最彻底的一例**：题面结论是 "One would expect both cases to be accepted"，F2P 却要求**新增**一条 `Module "util" has no attribute "internal_detail"` 错误；决定方向的依据（维护者按 PEP 484 裁定"两种都该报错"）只存在于**不可见的 hints** 里，题面无任何反向线索。另：题面复现是普通 `.py` 包，F2P 复现是 stub 包，不是同一组文件；base 已有的 `testReExportChildStubs`/`2`（gold 最可能误伤的两条）未入 P2P，P2P 只收了方向相反的 `testNoReExportChildStubs` | reject_revision（除非把维护者裁定写进题面） | 把题面那四个文件在 base/gold 上各跑一次 `mypy --strict --no-implicit-reexport`，看 gold 站哪边 |
| python__mypy-11824 | **本包评分设计最健康的一题**：F2P 两条覆盖两种不同的"两遍语义分析"触发路径（Protocol/Generic bound、PEP 585 前向引用），P2P 两条（显式 `__slots__ = ('data',)` 与空的 `__slots__ = ()` 仍须报错）精确堵住"把冲突检查删掉"这类过度修复，且不强制唯一实现。风险点：**题面给出的因果假设是错的**（归因于 Protocol 的 `__slots__ = ()`，而 F2P 里的 `Comparable` 根本没有 `__slots__`），真正原因"semanal 两遍"只在不可见的 hints 里。与 11857 共用同一 base_commit | ready_for_probe | base/gold 各跑 base 已有的 4 条 slots case，补进 P2P |

## 覆盖与统计

- 覆盖 **20/20** 题，全部落盘 `records/<instance_id>.json`（均为合法 JSON）。**未做清单：空**。
- 处置建议分布：`ready_for_probe` 7（10392、10430、10478、11434、11567、11824、16869）、`needs_repair` 10（10174、10308、10382、10401、10424、10658、11236、11352、11420、12741）、`needs_review` 1（10284）、`reject_revision` 2（11241、11707）。
- 记录 issue 数：P1 18 条、P2 19 条、P3 12 条。
- 方法与限制：全部为**静态审查**，未启动 Docker、未实跑任何测试、未调用模型 API。base 代码用裸克隆的 `git grep <base_commit>` / `git show <base_commit>:<path>` 读取（COMMON.md 允许的只读操作），未建 worktree。凡标 `pass` 的检查都附了具体文件行号或日志路径；未做的检查写 `not_checked`，证据不足写 `unknown`。

## 仓库级（跨题）发现

以下五条不是单题问题，证据文件都在 `runs/env_overnight_20260916/L1_mypy_1/`。

1. **mypy 的 P2P 不是设计出来的回归集，而是 diff 邻接 + `-k` 子串过选的副产物。**（`p2p_mechanism.txt`）
   对全部 40 道 mypy 题验证：`F2P ∪ P2P` 100%（40/40）落在「test_patch 里出现过的 case 名（新增行 `+[case X]` 或上下文行 ` [case X]`）」再取 pytest `-k` 子串闭包之内。
   直接后果：**14/40 题 P2P 为空**（本包内 10308、10382、10424、10478、10658、11236、11567 七题）；有 P2P 的题也常常选到与改动无关的邻居——最清楚的是 11420（九条 `testNewReturnType1~9` 就在插入点上方，一条没选；选进去的是下方的 `testGenericOverride` 系列）和 10174（P2P 是 `testUnimportedHintAny*`，与被改的 `is_overlapping_types` 毫无关系）。
   由此产生的可利用面很具体：10424 在 `meet.narrow_declared_type` 开头写一行 `return declared` 即可满分；10174 在 `_is_overlapping_types` 开头 `return True` 亦然。

2. **6 道 version ≥1.8 的 mypy 题 `eval_cmd` 缺 `-n0`，会在 pytest-xdist 并行下评分。**（`kcheck_all.txt` 与仓库配置核对）
   40 题里 34 道是 `pytest -n0 -rA -k`，6 道（16555、16869、16905、16963、16966、17071）是 `pytest -rA -k`；而 mypy 各版本的 pytest 配置都含 `addopts = -nauto`（已核对 0.820/0.920 的 `pytest.ini`、0.960 的 `pytest.ini`、1.9 的 `pyproject.toml`）。这 6 题的执行模式、输出交织、worker 崩溃归因与资源占用都与其余 34 题不同。

3. **`pytest -k` 是子串匹配，会连带选中同前缀的 case。**（`kcheck_all.txt`）
   本包 20 题里 8 题命中过选；实跑证据见 `runs/env_probe_stage1_20260910/.../python__mypy-10174/gold/offline/a1/`：命令只写了 2 个选择器，实际跑了 3 条，`status_map.json` 也记了 3 条。
   **当前不影响判分**——status_map 按完整 nodeid 记账，多跑的条目不在 F2P/P2P 里就被忽略；而且本包所有过选出来的 case 恰好本来就在 F2P/P2P 内。风险只在成本与将来重建 P2P 时。另已核对：本包 20 题的所有 selector 在 `test-data/` 下都只出现在一个 `.test` 文件里（`dupfile.py`），不存在跨 suite 同名冲突。

4. **题面质量问题分三类，都能低成本检出。**
   - 整段重复：`dup_problem_statements.txt` —— 216 题里 6 题的 `problem_statement` 前后半逐字相同（本包内是 11352，另有 MONAI-4775/6523/6975、dvc-4785、mypy-17071）。
   - 半句截断：`truncation_scan.txt` —— 启发式命中 13 条，人工确认其中明确是半句截断的有 2 条（mypy-12741 结尾 "…maybe some reasoning about"、conan-13610 结尾 "…to be consistent across"），其余多为正常散文结尾。
   - 材料丢件：`upstream_filelist_check.txt` + `fixture_check.txt` —— 逐题比对上游 PR commit 的文件集与 `test_patch ∪ golden_patch`，40 题里只有 **10308** 丢了真正的测试资产（上游 c0490b4c2 新增的 `test-data/unit/fixtures/object_hashable.pyi`，以及对 `typing-full.pyi` 的修改）；10392/15876/5617 丢的是文档或 README。10308 当前不影响判分（依赖该 fixture 的 `testHashable` 不在 F2P/P2P），但**只要把 P2P 改成「整文件跑」就会立刻炸**。

5. **跨题的历史相邻关系需要作为数据集划分约束。**（`cross_task_leak.txt`）
   40 题在同一条 mypy 历史上，时间靠后的题 base 天然包含更早题的修复（SWE-bench 系数据集的固有性质，不单独算缺陷）。但有三组是**紧邻**的，训练/评测划分必须同侧：`10392 的上游修复 commit == 10401 的 base_commit`；`16963 的上游修复 commit == 16966 的 base_commit`；`11824 与 11857 共用同一个 base_commit`。
   另外本包内 **10174 / 10424 / 10658 三题都改 `mypy/meet.py`**，其中 10424 与 10658 改的是**同一个函数 `narrow_declared_type`** 的同一条 elif 链，10658 的 base 里就能直接读到 10424 的参考解与其测试。

## 最值得用户裁定的 3 个问题

1. **mypy 的 P2P 要不要整体重建？** 现状是 diff 邻接 + `-k` 过选的副产物，14/40 题为空，已经能举出「一行破坏性改动拿满分」的具体反例（10424、10174）。重建方案（按 test_patch 触碰的 `.test` 文件整文件取基线通过集）代价是单题评分要跑成百上千个 case，需要先测时间；而且 10308 因为丢了 fixture 会直接失败，得先补件。**是按文件整体重建、只对高风险题补、还是维持现状并接受这个奖励漏洞？**
2. **「题面与评分方向相反」的题怎么处置？** 本包命中 4 道：11707（题面要求两种情形都被接受，F2P 要求新增报错，依据只在不可见的 hints 里）、12741（题面抱怨的那条错误恰是 F2P 要求保留的）、10658（题面写"应窄化到 A"，F2P 要求 `T`-1`）、11241（gold 只是把错误文本换了个措辞，那句话题面里从没出现）。它们不是环境缺陷，而是**题面与 upstream 决定之间的信息落差**。**是补题面（把维护者的裁定写进去）、放宽 F2P 断言、还是直接剔除？** 我给出的建议是 11241/11707 `reject_revision`、12741/10658 `needs_repair`，但这属于数据集取舍，需要用户拍板。
3. **mypy 这个仓库整体还适不适合做后训练题源？** 它的测试全部是逐字比对期望输出的数据驱动用例，导致「强制唯一实现」是结构性的而不是个别题的毛病（11236 会因为选了作者自己更看好的另一种修法而判 0；11420 会因为换了比较对象而判 0）。好处是判分确定、无网络、无外部资产、单题秒级。**是接受这种"必须复刻 upstream 具体实现"的信号并把它当作特性，还是把 mypy 限定为评测集而不进训练？**
