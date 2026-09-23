# L1_mypy_2 · 逐题静态审查小结

范围：python/mypy 20 题（ASSIGNMENT.json 顺序）。与 L1_mypy_1 合起来覆盖 SWE-Gym lite 里全部 40 道 mypy 题。
方法：先只看 `problem_statement` + base 代码写 `public_view`，再读 `test_patch` / `fail_to_pass` / `pass_to_pass` / `golden_patch` / `hints_text`。
base 代码一律用裸克隆的 `git show <base_commit>:<path>` / `git grep <pat> <base_commit>` 只读读取，未建 worktree、未跑任何测试、未启 Docker。

**本包 20 题全部没有任何历史实跑证据**：不在 stage1 的 182 题样本内、`in_e2` 全空、无 DeepSeek 候选（`task_signals_swegym.json`）。所以所有结论都是静态的，运行期问题只能写成"下一实验"。

逐题记录：`records/<instance_id>.json`。脚本在 `scripts/`（`extract.py` 抽四面材料、`prescan.py` 路径/评分面预扫、`kscan.py` -k 子串过选与 case 归属文件、`tpcases.py` 把 test_patch 改动逐行归属到 `[case X]`、`dump.py` 单题查看）。中间产物在 `${REPO_ROOT}/runs/env_overnight_20260916/L1_mypy_2/`（`mat/`、`prescan.json`、`kscan.json`）。

| task | 主要发现 | 建议处置 | 下一实验 |
| --- | --- | --- | --- |
| python__mypy-11857 | gold 改全局类型打印器 `TypeStrVisitor.visit_instance`，test_patch 批量更新 16 个 `.test` 文件共 **45 个 case 的期望**，但只有 26 个 case 名进入 F2P/P2P，**33 个被改 case 完全不参与评分**；F2P 里有 3 条 `pep561` 用例要在临时目录建 virtualenv 并 `pip install` 本地包（`testpep561.py:33-82`），环境可行性未验证；恰好 `pip install .` 那一条变体（testTypedPkgSimple）被上游从 F2P/P2P 里剔除了 | needs_repair | 镜像内单跑 `-k testTypedPkgSimpleEgg` 看 rc/耗时/是否联网；再用全部 45 个 case 名重算 F2P/P2P |
| python__mypy-11945 | gold 只把 `check_compatibility_final_super` 里的 `and` 改成 `or`；**F2P=1 且是"错误消失"型断言、P2P=0**，而同文件往下 3 个 case 就是断言该错误必须存在的 `testEnumNotFinalWithMethodsAndUninitializedValues`，没被选进 P2P → 在该分支直接 `return True` 即可满分。hints 透露"上一次修复没修好"，题面没有这条信息，base 里已有一个看似正确的同名豁免分支会误导 agent | needs_repair | 用"分支直接 return True"的假修复跑 F2P（预期满分）与 testEnumNotFinal...（预期 FAILED） |
| python__mypy-11966 | 题面/gold/F2P 三者对应良好（hints 为空，无信息不对称）。**P2P=0**，而 gold 改的是所有 dataclass 的 `__init__` 生成入口：删掉 `if info.fallback_to_any:` 守卫（对所有 dataclass 补 `*args/**kwargs` 并把位置参数降级为可选）仍能过 F2P 三条断言，check-dataclasses.test 的 78 个既有 case 一条都没进 P2P | needs_repair | 假修复（删守卫）跑 F2P 预期满分；再整文件跑 check-dataclasses.test 统计被破坏的 case |
| python__mypy-12222 | **题面明确提议的错误消息与 F2P 要求的不是同一句**：题面 Pitch 写 `Argument after ** to "test" has incompatible type "Union[Any, None]", expected "Mapping[str, Any]"`，F2P 要求 `Argument after ** must be a mapping, not "Optional[Any]"`。照题面字面实现必 0 分，唯一线索是 base 既有 case 已用后者句式。P2P 仅 1 条且未被 test_patch 改动 | needs_review | 分别按"题面 Pitch"与"沿用 base 措辞"各实现一版跑 F2P，量化题面误导的代价 |
| python__mypy-12417 | 题面自带完整 traceback，**直接点名 `checkpattern.py:466` 的那句 assert**，定位成本近乎为零；难点全落在"崩溃后走哪条恢复路径"，而这条题面没说、F2P 却锁死（要求 case 体可达且 revealed 为 Any，用 `early_non_match()` 的合理实现会挂）。P2P 3 条是本包里少见真有判别力的（挡住"一律返回 AnyType"的粗暴修复），但同样是 -k 子串过选的副产物 | ready_for_probe | 写 `early_non_match()` 版本跑 F2P，确认因缺少 reveal 输出而失败 |
| python__mypy-15131 | **纯猜字符串题**：gold 只改 `message_registry.py` 的一条常量文本，题面一个字的措辞建议都没给，F2P 却逐字要求 `(or be a tuple of exception classes)`。公开材料到 F2P 之间没有可推理路径。另：test_patch 改了 11 个 case 的期望，只有 2 个进 F2P，唯一的 P2P 与本次改动无关 | reject_revision | 让模型生成 10 个候选措辞统计逐字命中率（预期 0） |
| python__mypy-15139 | 题面讲的是 `type`/`builtins.type`/`Type` 三种写法不一致，**从没出现 `--force-uppercase-builtins` 这个开关**，而 F2P 正是靠 `--no-force-uppercase-builtins` 触发；gold 也没动题面第一个例子 reveal_type。**P2P=0，而同文件 base 已有 8 条结构完全对称的 case**（Tuple/List/Dict/Set × On/Off）一条没选 → 把 `Type[` 无条件改成 `type[` 即可满分 | needs_repair | 无条件小写的假修复跑 F2P（预期满分）+ 跑 check-classes.test（预期大面积失败） |
| python__mypy-15184 | **题面复现按上游自述在 master 上已不报错**（"This code doesn't produce any errors in current master branch"，作者承认复现写得绕），F2P 换了一套 `array.array` / `__main__.array` 的复现；hints 里还直接给了 gold 方案（"use `format_type_distinctly`"）。好消息：P2P `testAssertTypeFail3` 罕见地有判别力，堵住"一律输出全限定名"的假修复 | needs_review | 在 base 上直接跑题面那段代码，确认是否还报 `"SupportsIndex", not "SupportsIndex"` |
| python__mypy-15208 | 题面/gold/F2P 对应是本包最好的（hints 为空、期望输出逐字给出）。但 gold 里 `if name == "metaclass": continue` 这一行是必需的——base 的 `stubgen.py:968-980` 已经单独拼过 `metaclass=`——而 **stubgen.test 里 11 条 metaclass 既有用例一条都不在 P2P**；漏掉这行跳过的实现照样满分，却会生成重复的 `metaclass=` | needs_repair | 写"漏掉 metaclass 跳过"的假修复跑 F2P+P2P（预期满分）再跑 11 条 metaclass 用例（预期全挂） |
| python__mypy-15413 | **题面自己写着"我也不确定这算 bug 还是特性"**，hints 里维护者同样不确定；"lambda 一律豁免 `--warn-return-any`"这个决定只在 PR 里。F2P 是纯"无输出"断言且 P2P=0 → 删掉 `incorrectly_returning_any` 调用即可满分。真正的回归集 check-warnings.test（4 条断言）既不在 test_patch 也不在评分里 | reject_revision | 删调用的假修复跑 F2P（预期满分）+ 跑 check-warnings.test（预期 4 条挂） |
| python__mypy-15876 | **本包唯一一道 `additional_exclusions` 不能留空的题**：4 条 P2P（testEmptyReturnIn*）落在 `check-statements.test` / `check-dynamic-typing.test` / `check-basic.test`，这三个文件不在 test_patch 里，既不被 eval 还原也不进 hygiene.test_files → agent 可就地改断言让 P2P 恢复绿色。成因是 `-k testEmptyReturn` 的子串过选把评分对象拉出了受保护文件集。另：又一道"猜措辞"题，hints 里最接近的提议 `(or returns None)` 与 gold 的 `(it only ever returns None)` 也不同；18 个被改 case 只有 6 个进 F2P | needs_repair | 造"破坏 P2P + 改 check-statements.test 断言"的候选 patch 走完整评分，确认当前会判通过 |
| python__mypy-16555 | 根因（mypy 把 enum **成员名**当成字符串字面量去做 `.format` 检查）题面完全没提，要自己从 `checkexpr.py:636` 读出来；F2P 三条里有 2 条在题面无依据（StrEnum 只在 hints 里、非 str Enum 两处都没有）。好处是 F2P 正反两侧都有（NORMAL.format(42) 仍须报错），挡住了"整体关掉 str-format 检查"。P2P=0，check-formatting.test 的 40+ 既有 case 一条没选。属 eval_cmd 缺 `-n0` 的 6 题之一 | ready_for_probe | 只实现题面字面要求（str, Enum）跑三条 F2P，统计通过数（预期 1~2） |
| python__mypy-16905 | **本包 P2P 设计最贴切的一题**：test_patch 新增的两条 `...LengthMismatchNoNarrowing` 是 P2P，精确对应 gold 新函数里那句裸 `assert len(expr.items) == len(typ_.items)`。另外 6 条 P2P 则是 `testMatchMappingPatternCaptures` 的 -k 子串过选产物，与改动无关。题面只给"一层元组 + 类模式"，F2P 还要求 Literal 窄化与三层嵌套递归 | ready_for_probe | 构造 `match a, b:` 配 `case [x]:` 跑 gold，确认裸 assert 是否崩 |
| python__mypy-16963 | 题面 4561 字符、列了 **5 条**要消失的错误，但那是 mypy 0.910 的输出；作者自己在 hints 里更新成 1.7.1 的 3 条，而 base 是 1.10 —— 题面的初态描述对不上。gold 只有 2 行、只解决其中一族。F2P 正反两侧齐全（挡住"一律返回 Any"），但 P2P=0，check-typeddict.test 的 232 个既有 case 一条没选。**本题的上游修复 commit 就是 16966 的 base_commit** | needs_review | 在 base 上对题面那份 40 行脚本实跑 mypy，逐条比对真实错误清单 |
| python__mypy-16966 | **命中 `-k` 选择器构造缺陷**：`spec_vendor.py:183-191` 用 `\[case ([^\]]+)\]` 直接拼 `-k`，把 `testMatchLiteralPatternEnumCustomEquals-skip` 的 `-skip` 后缀一起拼了进去；`data.py:649-695` 运行时会剥掉该后缀，所以这个选择器永远匹配不到（空转）。**本机已复验 pytest 的 -k 词法接受连字符**（rh2/.venv, pytest 9.1.1，`Expression.compile` 通过），所以不会导致评分命令失败，风险从 P1 降为 P3。题面/gold（一行）/P2P 本身质量好；真正没人守的是上游有意 `-skip` 的自定义 `__eq__` 枚举边界用例 | ready_for_probe | 决定是否把 `testMatchLiteralPatternEnumCustomEquals` 从 -skip 放出来跑；顺带在镜像里确认该 -k 表达式 rc |
| python__mypy-17071 | 题面与 hints **都整段重复两遍**（1638 = 819×2），题面代码块缩进损坏且无 import。根因链条清楚、gold 6 行正确。风险在覆盖面：gold 改的是公共基类 `TypeTraverserVisitor.visit_callable_type`，**6 个子类同时受影响**（CollectArgTypeVarTypes / FreezeTypeVarsVisitor / CollectAllInstancesQuery / MixedTraverserVisitor / TypeVarLikeNamespaceSetter / LocationSetter），而 2 条 P2P 只覆盖其中 1 个的效果 | ready_for_probe | gold 上跑 semanal-types.test / merge.test / check-serialize.test，看遍历器改动是否泄漏副作用 |
| python__mypy-5617 | **题面直接写出修法**："I believe it could be implemented by removing the check on line 1930 of `mypy/semanal.py` and updating the tests"——本包最露骨的静态泄漏（行号过期，文件与做法完全对）。另一个发现：P2P 的 `testAssignEmptyPy27` 守不住任何 semanal 改动——全仓只有 `semanal.py:2641` 写这句话且被 gold 删掉，py2 下的同名错误其实来自 typed_ast 的 CPython2 语法解析（`fastparse2.py:121-122`），所以它是**环境探针**而非回归护栏。-k 表达式还含已被 test_patch 删除的 `testInvalidLvalues5` | needs_repair | 删/留题面末段各跑一次同模型比解决率；镜像里单跑 `-k testAssignEmptyPy27` 确认 typed_ast py2 路径可用 |
| python__mypy-9625 | **P2P=0** 而 gold 改的是 `expr_to_unanalyzed_type` —— 所有下标型类型表达式（`List[int]`、`Dict[str,int]`…）的公共入口：把 `base.args = tuple(...)` 无条件换成 `return expr_to_unanalyzed_type(args[0], expr)`（不加 Annotated 判断）即可满分，代价是泛型系统整体崩塌，check-annotated.test 的 18 个既有 case 一条没选。gold 自带 TODO 承认"丢掉全部注解信息"，一个**更正确**（保留注解）的实现反而会被 F2P 判 0 | needs_repair | 无条件版假修复跑 F2P（预期满分）+ 跑 check-generics.test（预期大面积失败） |
| python__mypy-9629 | **题面是两篇不同 issue 的正文直接拼接**，且前半段（多重继承 `super().__init__(**kwds)`）的诉求已被维护者在 hints 里明确否定（"mypy type-checks calls purely on the basis of the given signature"），gold 也确实没修那一半。评分覆盖只占 gold 行为改变的 **1/6**：4 条删除了 `# E: Too many arguments` 的既有 case 全部未评分，两条 P2P 与改动无关 | needs_repair | "只特判字面空 dict"的实现跑 F2P（预期满分）再跑那 4 条（预期全挂） |
| python__mypy-9909 | **本包"强制唯一实现"最强的一题**：F2P 逐字断言 `'__main__.<subclass of "A1" and "B">1'` / `'...>2'`，这些**数字后缀**是 `gen_unique_name` 的去重计数，等于把 gold 内部"先试 (A,B) 失败再试 (B,A)、每次都 make_fake_typeinfo"的控制流写进了期望输出；任何"先判断再构造"的等价实现都拿 0 分。题面另有中等泄漏（点名 `check_multiple_inheritance` 与 `find_isinstance_check_helper`）。P2P 3 条有判别力 | needs_repair | 实现"只构造一个 TypeInfo"的等价修复，跑 F2P 确认因名字后缀不同而失败 |

## 覆盖与统计

- 覆盖 **20/20** 题，全部落盘 `records/<instance_id>.json`（均为合法 JSON，已用 `json.load` 全量校验）。**未做清单：空**。
- 处置建议分布：`needs_repair` 10（11857、11945、11966、15139、15208、15876、5617、9625、9629、9909）、`needs_review` 3（12222、15184、16963）、`ready_for_probe` 5（12417、16555、16905、16966、17071）、`reject_revision` 2（15131、15413）。
- 记录 issue 数：P1 40 条、P2 27 条、P3 7 条。检查项状态：pass 187、issue 133、unknown 3、not_checked 17（未实跑的安装/环境项一律写 `not_checked`，证据不足写 `unknown`）。
- `file_rules.additional_exclusions` **只有 python__mypy-15876 非空**，其余 19 题按第四组 B 保持默认空。
- 方法与限制：全部为**静态审查**。未启动 Docker、未实跑任何测试、未调用模型 API、未连接任何远程机器。base 代码一律用裸克隆 `git show <base_commit>:<path>` / `git grep <pat> <base_commit>` 只读读取，未建 worktree。凡标 `pass` 的检查都附了具体文件行号或 commit:path。

## 仓库级（跨题）发现

证据文件都在 `${REPO_ROOT}/runs/env_overnight_20260916/L1_mypy_2/`。第 1、3 条与 L1_mypy_1 的仓库级结论方向一致，这里给出**精确成因与量化**；第 2、4、5 条是本包新增。

1. **P2P/F2P 的候选集就是 `re.findall(r"\[case ([^\]]+)\]", test_patch)`，即 test_patch **diff 文本**里字面出现过的 case 名，再取 pytest `-k` 子串闭包。**
   代码依据：`rh2/src/repoharness2/envpack/spec_vendor.py:183-191 derive_test_command`（逐字对齐上游 fork `test_spec.make_test_command`），mypy 分支是 `test_cmd + " " + '"' + " or ".join(keys) + '"'`，**不带测试文件路径**。
   全量验证（20/20 题）：`F2P ∪ P2P` 的 case 名全部落在「diff 文本里的 `[case X]` 字面量」∪「其 `-k` 子串扩展」之内，没有例外。
   量化后果见 `ungraded_changed_cases.txt`：本包 20 题的 test_patch 一共改动 **115 个 case**，其中 **67 个（58%）既不在 F2P 也不在 P2P**。最严重的是 11857（45 改 → 33 未评分）、15876（18 → 12）、15131（11 → 9）、9629（6 → 5）。
   成因很直接：只有当某个 case 的 `[case X]` 头行恰好落进某个 hunk 的上下文（±3 行）或新增行时，它才会进候选集；仅仅"期望输出被改了几行"是不够的。

2. **（新）mypy 的评分驱动文件与测试夹具完全不受 hygiene 保护。**
   `rh2/src/repoharness2/grading/manager.py:656` 把 `hygiene.test_files` 定为 `patch_touched_paths(private.test_patch)`，`:672` 把 `test_globs` 设为空（P-B 已决定取消默认通配），`:581` 的 `DEFAULT_SWE_FORBIDDEN_GLOBS` 只有 `('.rh2*','rh2/*')`。
   对 mypy 而言，test_patch 只含 `test-data/unit/*.test`，因此 **`mypy/test/*.py`（testcheck.py / data.py / helpers.py —— F2P/P2P 的 nodeid 前缀就是它们）与 `test-data/unit/fixtures/*.pyi` 既不被 eval 的 `git checkout` 还原，也不会触发 `rejected_test_tampering`**（`rh2/src/repoharness2/contracts/grading.py:118-121`）。改一行 `mypy/test/helpers.py::assert_string_arrays_equal` 让它恒真，就能让所有数据驱动用例通过。
   可行性证据：对 `validation_bundles_v0.jsonl` 全量核对，**40 道 mypy 题的 gold 无一触碰 `mypy/test/` 或 `test-data/`**（唯一相关例外是 16869 的 *test_patch* 触碰 `mypy/test/teststubgen.py`，属 L1_mypy_1 范围）。所以把 `mypy/test/*` 与 `test-data/*` 纳入保护不会挡住任何合法解答。需用户裁定的副作用：agent 在 `test-data/` 下建临时文件会让整份提交作废。
   **本包 15876 是必须立刻处理的特例**：它有 4 条 P2P 落在 `check-statements.test` / `check-dynamic-typing.test` / `check-basic.test` —— 这三个文件不在自己的 test_patch 里（成因是 `-k testEmptyReturn` 的子串过选把评分对象拉出了受保护文件集）。

3. **6 道 version ≥1.8 的题 `eval_cmd` 缺 `-n0`，会在 pytest-xdist 全核并行下评分。**
   逐题 `git show <base>:pytest.ini|pyproject.toml` 核对（见 `prescan_report.txt` 与本包各记录的检查 18）：**20/20 题的 pytest 配置都含 `addopts = -nauto`**；而 eval_cmd 里 16555 / 16905 / 16963 / 16966 / 17071（本包 5 题）与 16869（mypy_1）是 `pytest -rA -k`，其余 34 题是 `pytest -n0 -rA -k`。
   `test-requirements.in`（1.8）含 `pytest>=7.4.0` 与 `pytest-xdist>=1.34.0`，所以 `-nauto` 会真的生效。这 6 题的输出交织、worker 崩溃归因、内存占用都与其余 34 题不同口径。

4. **（新）`-k` 选择器直接取自 diff 文本，会把不合法/已失效的名字也拼进去。**
   全量扫描 40 题（脚本逻辑同 `scripts/kscan.py` 的取名方式）只有两例异常，都来自 `[^\]]+` 把 mypy 的 magic 后缀一起吃进去：
   - `python__mypy-16966`（本包）：`-k` 含 `testMatchLiteralPatternEnumCustomEquals-skip`。而 `mypy/test/data.py:649-695` 的 `_case_name_pattern` 运行时会剥掉 `-skip`，nodeid 里没有这个后缀，所以该选择器永远匹配不到；原先担心的"带连字符的 `-k` 表达式可能非法"已**本机排除**：`_pytest.mark.expression` 的标识符正则是 `(:?\w|:|\+|-|\.|\[|\]|\\|/)+`（含连字符），本机 pytest 9.1.1 下 `Expression.compile("testA or testB-skip or testC")` 编译通过；镜像里的 pytest 版本（1.8+ 段 >=7.4.0、0.800 段 6.x）未实跑确认，但风险已降为低。
   - `python__mypy-10308`（L1_mypy_1 范围）：`-k` 含 `testWeirdRecursiveInferenceForProtocols-skip`，同型。
   另一个变体在 `python__mypy-5617`：test_patch **删除**了 `[case testInvalidLvalues5]`，但该名字仍被拼进 `-k`（选择器取自 diff 文本而非应用后的文件状态），运行时空转。
   三例当前都不改判分，但它们说明选择器派生缺少"派生后校验每个 selector 都是合法标识符、且在应用 test_patch 后的文件里存在"的一步。

5. **（新）本包 20 题全部零运行期证据，且题面质量问题集中在三类。**
   - **零证据**：20 题都不在 stage1 的 182 题样本内（`runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/` 下只有 6 个 mypy 目录，全属 mypy_1），`in_e2` 全空、无 DeepSeek 候选（`task_signals_swegym.json`）。所以本包所有结论都只能是静态的。
   - **题面直接给修法**：5617（"removing the check on line 1930 of `mypy/semanal.py`"）、9909（点名 `check_multiple_inheritance` 与 `find_isinstance_check_helper`）、12417（traceback 精确到 `checkpattern.py:466` 的那句 assert）。
   - **题面与评分方向不一致/无法推断**：15131 与 15876 是纯猜措辞（题面一个字的提示都没有，15876 连 hints 里最接近的提议 `(or returns None)` 都与 gold 的 `(it only ever returns None)` 不同）；12222 题面提议的消息与 F2P 要求的不是同一句；15413 题面自述"我也不确定该不该改"；9629 题面是两篇 issue 拼接且前半段诉求已被维护者否定；15184 与 16963 的题面复现按上游自述在 base 版本上已经失效或已部分修好；17071 题面与 hints 整段重复两遍。

## 最值得用户裁定的三个问题

1. **要不要把 `mypy/test/*` 与 `test-data/*` 加进 hygiene 保护清单？** 证据齐全（40 题 gold 均不触碰），不加则存在"改测试驱动即满分"的通路；加则 agent 在 `test-data/` 下建临时文件会被判 `rejected_test_tampering`（整份提交作废）。这是 T0 口径变更。若暂不做全局改动，至少 15876 必须单独补 `additional_exclusions`。
2. **"猜措辞"类任务（gold 只改一条错误消息文本）是否纳入训练/评测？** 本包的 15131、15876 属此类，12222 更糟（题面给了另一种措辞当陷阱）。保留就要改题面或放宽断言；剔除则 40 题里要连带复查同类题。这直接决定要不要为 mypy 建立"题面改写"这条工序。
3. **F2P/P2P 是否重建？** 本包 115 个被改 case 里 67 个不参与评分，且 P2P 是 `-k` 子串闭包的副产物而非设计结果（9 题 P2P=0）。重建的最小方案是"把 test_patch 改过期望的 case 全部纳入 F2P + 按功能挑 P2P"，但这会脱离与上游 fork `make_test_command` 的逐字对齐关系，需要先定"是否允许偏离 vendor 口径"。

## 补充复验（写完逐题记录后追加，用于收紧/推翻前面的判断）

- **`-k` 选择器不会误选到普通 pytest 函数。** 对 20 题逐一比对：所有 F2P/P2P 的 case 名，与该 base 下 `mypy/test/**.py` 里的全部 `def`/`class` 名、以及 `mypy/test/` 下的 `.py` 文件名，**无一构成子串关系**（脚本 `scripts/selcheck.py`，输出 `runs/.../L1_mypy_2/selcheck.txt`，结果：0 处冲突）。`kscan.json` 里 `dup_in_base` 也全为 false，即没有同名 case 出现在两个 `.test` 文件里。所以 `-k` 的过选范围严格限制在数据驱动用例内，当前不会把无关单测拉进 status_map。
- **带连字符的 `-k` 表达式合法（推翻了先前对 16966 的高危判断）。** 本机 `rh2/.venv`（pytest 9.1.1）实测 `_pytest.mark.expression.Expression.compile("testA or testB-skip or testC")` 编译通过；标识符正则 `(:?\w|:|\+|-|\.|\[|\]|\\|/)+` 含连字符。16966 的风险因此从"整题评分命令可能失败"降为"一个选择器空转"。镜像内 pytest 版本按 `test-requirements` 分别是：0.800 段 `>=6.0.0,<7.0.0`、0.940 段 `>=6.2.0,<7.0.0`、1.8 段 `>=7.4.0`；未在镜像里实跑确认。
- **5617 的 P2P `testAssignEmptyPy27` 确认是环境探针而非回归护栏。** `git log -S testAssignEmptyPy27` 只有两条记录：引入它的正是本题的修复 commit `48f2b10d5`，删除它的是 `5718dfff7`（"No longer support checking Python 2 (#13135)"）。它在 semanal 检查被删掉之后仍在上游 CI 上通过了约两年，说明 py2 下那句 `can't assign to ()` 来自 typed_ast 的 `ast27.parse`（`fastparse2.py:112-124` 以 blocker 语法错误上报）。因此它守不住任何 semanal 改动，但只要镜像里 typed_ast 的 py2 路径不可用，本题就恒定 0 分。
- **11857 的 pep561 依赖已查到打包层面。** `test-data/packages/typedpkg/setup.py` 是纯 setuptools 包，`test-data/packages/` 下**没有任何 `pyproject.toml`**；`test-requirements.txt` 含 `virtualenv>=20.6.0`。仍未确认的是镜像内 pip 版本与构建隔离行为（现代 pip 即使无 pyproject.toml 也会建隔离环境、需要 setuptools/wheel，离线会失败）。上游把走 `pip install .` 的那条变体（testTypedPkgSimple）从 F2P/P2P 里剔除、只留 `no-pip` 与 `editable` 变体，是这一假设的**旁证**，不是直接证据。
