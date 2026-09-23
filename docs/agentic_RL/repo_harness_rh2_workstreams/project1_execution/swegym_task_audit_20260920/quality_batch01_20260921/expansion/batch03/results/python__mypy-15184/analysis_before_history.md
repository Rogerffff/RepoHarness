# python__mypy-15184 · 独立私有初稿（历史前封存）

封存UTC：2026-09-20T21:25:55.074421+00:00。暂定 `needs_review / static_review`，人工建议为**静态候选，待actor开发条件和原题复现验证**；仅 `development_diagnostic`。两条消歧F2P和一条无歧义P2P与公开目标相符，真实分差可解释，尚无证据证明误拒或gold错误。覆盖不是完整：原题协议/typing_extensions路径、正向assert_type与泛型参数内部冲突没有进入评分。

## 身份与实际暴露

ROOT=`${REPO_ROOT}`，P=`runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15184`，Q=同根 `private/python__mypy-15184`。源码位置以下相对P/base。先读本题已封存public_read.md，再读public_bundle/base_identity及Q的grading/test/gold/validation/run_refs/source_refs/environment_record。精确base=`13f35ad0915e70c2c299e2eb308968c86117132d`，tree=`a4e70a35d21d198daf4151d6b2aba79c41fc034d`；gold SHA256=`365adadcf2ad3dbed4dc98bf30ebda81f9c788a8ced939ff2a2abd8bfef1a280`。沿用父协调者材料和清单验收，未重做blob遍历。

本题environment_record的 `verified_environment_pair`、noop=0/gold=1摘要已看见并披露；随后核精确原ledger/log/diagnostics和image.json。本稿不能自称未见运行结果。未打开本题history/refs或旧报告、reviewer/其他题结果/批聚合；同仓公共版本知识仅作导航，本题结论由本题源码与原件支持。前题历史曾提及本题“同messages.py热点/近base”，这条交叉信息已暴露但未用作质量/关系证据；未见本题旧实质结论。没有执行项目、导入项目模块、测试、安装、下载、网络、Docker/SSH或模型。

运行前缀R=`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-15184`。GL=`R/gold/eval_logs/evallog_replay-er19-iw1-python___d57f367c.eval.log`，NL=`R/noop/eval_logs/evallog_replay-er19-iw1-python___0ecfe8ca.eval.log`；两份ledger均第1行，同前缀diagnostics亦已读。

## 1. 公开需求与双向映射

标题和正文要求assert_type失败时对同名不同类型使用完整限定名。末段“perhaps”协议等价性是征询讨论，没有给新等价关系规则；不把“让该断言通过”当必须目标，也不能通过删错误冒充诊断修复。既有错误的表达式/期望顺序、引号、assert-type错误码和无歧义短名，分别有messages.py:1658-1664、errorcodes.py:151和公开check-expressions.test:931-990支持。

| 需求/旧行为 | 公开依据 | 官方断言及实测 | 覆盖判断 |
|---|---|---|---|
| 不同模块的同名类须消歧，保留参数 | 题面“fully qualified names”；messages.py:2584-2661已有共同消歧契约 | F2P1：arr.array[int] 对本地array；完整 `array.array[int]` / `__main__.array`；NL:450-452错，GL:470过 | 直接覆盖；即使旧整个字符串array[int]/array不完全相同，类短名仍冲突，测试不是无依据的强制 |
| 嵌套类的限定名包含外层类 | 题面一般同名消歧；TypeInfo fullname/formatter | F2P2：目标本地array.array；期望 `__main__.array.array`；NL:463-465错，GL:471过 | 覆盖嵌套类名；不是泛型参数内部冲突测试 |
| 无歧义仍保持简洁，不能无条件加全名 | 公开testAssertType普通int/str/Any错误；formatter短名惯例 | P2P3：arr.array[int] 对int，要求 `array[int]` / `int`；NL:473、GL:472均过 | 明确正反政策保护；它仍是一个预期失败的类型断言，不是assert_type成功用例 |
| 原报告typing_extensions.SupportsIndex vs typing.SupportsIndex | user_prompt完整输入；两份typeshed协议与ASSERT_TYPE_NAMES | 官方三个都用typing.assert_type和array，无该原例 | 共用调用链静态适用，但完整原例未实测，不能宣称已复现/修好 |
| 保留正确assert_type无错误、返回原类型、Literal/泛型/unchecked行为 | checkexpr.py:3911-3932；check-expressions:931-990 | 全部官方case都是错误分支 | 未评分保护；已读完整相关旧case、gold未动判定，窄公开回归可验证 |
| 泛型参数/union等内部同名Instance也须消歧 | 标题一般性；collect_all_instances和TypeTraverser递归 | 官方source虽带int参数，但参数本身无冲突 | 未覆盖；gold的共用helper会递归，静态无新缺陷 |

反向看关键约束：完整模块/嵌套类限定名来自公开目标与既有fullname规则；保留int短名来自既有无歧义输出；无内部helper名称、Mock调用次数、对象布局或执行顺序断言。__main__来自测试runner模块身份，不是新私有API要求。没有新增实现函数名需要从gold猜。

## 2. 原问题与全部test.patch/helper展开

唯一新文件 `test-data/unit/check-assert-type-fail.test`，28行、三个case；无helper或业务源码修改。每例import typing及array as arr，定义本地class array。case1本地类空体、函数参数arr.array[int]，一条E断言；case2/3本地类含嵌套array和class attribute i=1，函数参数相同，case2以array.array为目标、case3以int为目标。i=1只建立嵌套类实体，不是断言/运行时行为。三个均 `[builtins fixtures/tuple.pyi]`。没有Mock、真实array对象构造、网络或外部服务。

完整辅助链：testcheck.py:35-55用check-*.test收集新增文件；data.py:52-60,95-107读取case与替代builtins，:210-214,518-544把E注释变为完整预期诊断；helpers.py:358-390无flags时隐藏error code、强制旧大写和union风格，testcheck.py:113-155调用真实build.build；:162-184比较全部error数组；helpers.py:46-58进行can't/cannot及路径清理后比对，失败路径pytest.fail位于:118。没有只测文件存在/错误数量的捷径。

fixture tuple.pyi全文1-56已读（object/type/tuple/int/slice/list和typing依赖）；lib-stub/typing.pyi:1-60含assert_type=0及Generic/TypeVar特殊语义，mypy/modulefinder.py:793-801插入lib-stub。没有lib-stub/array.pyi；相关定义来自包内typeshed/stdlib/array.pyi:1-84（已全文读，class array(Generic[_T])、_T约束int/float/str）。不需要运行Python标准库array或联网下载该数据。题面完整typeshed的SupportsIndex两定义、typing.assert_type版本分支、typing_extensions重导出已分别核读；不能把测试最小typing桩与原例完整typing桩混为同一环境证明。

NL:433-480命令 `pytest -n0 -rA -k 'testAssertTypeFail1 or testAssertTypeFail2 or testAssertTypeFail3'`，收集11322、选3；F2P1/2实际生成array[int]/array而未限定，P2P3通过；rc1。GL:457-477同命令、三项均通过、rc0。原ledger第1行分别reward0/1，f2p0/2与2/2，p2p_fail0/total1，解析键3、reference_missing/skipped空、段外0。收集总数、实际节点3、解析键3、冻结参考2+1分开记录；非根据摘要标题或退出码猜结果。

## 3. 合理替代路线与漏测边界

gold调用既有format_type_distinctly；可接受的不同路线是给assert_type诊断局部联合收集冲突fullnames，随后分别用现有format_type_inner和quote_type_string渲染，或抽出共享的成对显示策略。只要保留短名/参数/语义并按需限定双方，测试不要求调用gold的helper。无证据宣布所有合法解均接受，但没发现具体误拒疑点，不强制造第二个补丁。

一条具体部分修复路线只比较两个顶层Instance的name/fullname；它可处理两个官方array冲突、保持int P2P，却遗漏 `list[a.C]` 与 `list[b.C]` 的参数内部同名类型。公开共同消歧契约与TypeTraverser支持这种泛化范围。这是静态覆盖限度，未构造/运行候选，不能把它写成已证实RH2假阳性，更不能因任何有限测试总能硬编码就直接判坏题。全部case为负例，也不保护“不应多报错”的正向assert_type；公开旧testAssertType可作定点回归。

## 4. gold、公开调用者和回归

调用链：types.py:138两个公开assert_type名字 → semanal.py:4807-4819/5147-5151转AssertTypeExpr → checkexpr.py:3911-3932原先做is_same_type检查及Literal处理/unchecked note/返回源类型 → messages.assert_type_fail。gold只把独立format_type改为成对format_type_distinctly，并保留self.fail、context、codes.ASSERT_TYPE、原句式与参数顺序；不改子类型语义、不需新依赖、无不相关文件。helper本就用于赋值/列表错误（messages.py:654-659,675-679），不是隐藏新增依赖。

共享helper：collect_all_instances收集两侧Instance（:2559-2581），find_type_overlaps按同短名多个fullname标记（:2584-2602），format_type_distinctly共同渲染（:2638-2661）；typetraverser.py:80-104递归Instance参数、Callable、Tuple、Union、TypeType；非递归别名展开有明确分支。gold覆盖普通/嵌套类的判据有代码和真实官方测试；递归别名/类型变量/重载等更广显示限制没有穷举，不把“一切内部不同类型都必须输出不同”自行加入规格。

已读公开完整五组旧assert_type行为：testAssertType、testAssertTypeGeneric、testAssertTypeUncheckedFunction、testAssertTypeUncheckedFunctionWithUntypedCheck、testAssertTypeNoPromoteUnion（check-expressions:931-990），以及testInvalidAssertType（semanal-errors:845-852）、其它诊断testIncompatibleAssignmentAmbiguousShortnames（check-basic:69-86）。它们不是本题P2P，没运行，不能说已过回归。gold只改失败文案，静态未见这些语义被破坏。

**原例特别保留未知**：is_same_type不是TypeInfo身份比较，而是双向proper subtype（subtypes.py:251-267）；同文件:602-605和:990-1064确有结构协议判定，两份SupportsIndex桩表面方法相同。因此不能仅凭类定义fullname不同断言该原例在此base必定仍失败，public_read中的预计错误也不是本次执行证据。即使原协议实例已不触发错误，官方两个名义类冲突仍真实证明该诊断路径有缺陷；是否需更新公开复现是待验证点，不据静态猜测宣布原题已修复。

## 5. 开发环境与当前证据

| 操作/资产 | 公开依据 | 本题已有证据 | 仍缺与最小建议（均未执行） |
|---|---|---|---|
| 定位/导入源码与CLI | messages/checkexpr/semanal；setup.py:223-236 | 原grader导入观测 `/testbed/mypy/__init__.py`，Python3.11.9 | 正式actor PATH、解释器、模块/.so来源、实际工具消息未知；以agent shell打印来源后跑公开C3原例 |
| 运行和测试依赖 | CONTRIBUTING:39-44；setup依赖；pytest数据runner | GL:379,419-447，NL:355,395-423真实离线requirements+editable安装完成，非仅COPY成功 | grader可写prefix不等同actor；若必须安装需可写位置/离线wheel，不能假定公网 |
| 类型桩与fixture | tuple/lib-stub typing/typeshed array和SupportsIndex | 静态源码齐全且官方fixture路径实际运行成功 | 原题完整typeshed/目标版本与actor是否一致未验；无需外部附件/下载数据 |
| 临时工作区/资源 | data.py临时case文件；testcheck.py缓存关闭 | 历史grader2CPU/4GiB、tmp1GiB、deny_all，峰值约137MiB；一次清理removed=true | 无actor权限、并发稳定性、当前资源验收；单次评分不能泛化 |
| 编译/资产/合法提交 | gold仅messages.py；公开源码开发指南 | 无新依赖、GPU、数据库/服务或必须C编译需求 | 有旧.so时先确认候选源码生效；修复可提交非测试源码，无必需恢复路径冲突 |

image.json与清单精确本题对象：派生ID=`sha256:38c3651c72ac2fe7ce40e3cf3e2a6056f8e983fe325d0fed771124e5827a829e`；仅COPY wheels与PIP_NO_INDEX/PIP_FIND_LINKS，原spec安装/测试仍保留，无recipe/materials/bindings覆盖。已读environment_replay_inventory的common、install_wave1及本题exact对象；未读analysis_reference聚合。原wheel payload/context本地未保存，目标机镜像存在性未核。grader=rh2grader/54322、补丁apply=agent/54321；后者不是正式actor验证。

## 6. 交付/恢复/评分边界

沿用已静态读取的baseline.tar.gz相关历史代码身份（只读成员文本、不解包/导入）：spec_vendor.py SHA256 `8e0037b27c87268ed7df97ef64d261d0e6dac7375bc85fd5badd0fecdb94d41d` :183-197；prepared_task_face.py SHA256 `3a3d7bcab18e8a83f99104180e065ed32d8ecbce5d1bd4aaa7f8bd72b001aa27` :185-211、305-330；scoring.py SHA256 `b6c8b9bd3e9cac604bc0d03b0b243ef9646de369e94bb6a65e60eadd3a64f5ab` :189-270；swegym_parsers.py SHA256 `995bb6aae58a94f9553946c2f9aea59a158ad4fdf4d7fc0137802c11362b2276` :88；前二在src/repoharness2/envpack与adapters/slime，后二在envpack。归档根 `runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz`；未用当前ROOT/rh2替代。

精确official路径只有新增 `test-data/unit/check-assert-type-fail.test`。它base中不存在，setup正常跳过checkout后应用新文件：diagnostics restored=0、expected/test_files=1、apply_rc=0、setup_ok=1、missing=0；**restored=0不能解读为漏恢复/保护失败**。gold projection仅mypy/messages.py、ignored=[]。test_globs=空，不按名称猜整个mypy/test或test-data都排除。无源码被test.patch混入，合法诊断修复不受恢复覆盖。additional_exclusions=[]；本次未证明helper/config绕过，不凭可能性新增排除。所有测试都会恢复的public_hints仅是过宽操作说明，不能当机制事实。

## 7. 关系、泄漏与用途

本题与其它messages.py任务不能仅凭同文件或base相近判重复；未审跨题commit/补丁关系。题面给要求和实例，没有指定实现函数；base已有可用helper是正常公开信息。公共base无.git不证明实际镜像无未来对象/答案；真实可见资产、网络答案、安装缓存未验。已暴露test/gold/运行结果，后续历史亦需单独登记，产物禁止进入solver输入。无真实模型成功率/token/费用，costs保留null。

## 8. 初判、优先验证和未查项

暂未发现应阻止开发诊断候选的具体gold语义问题；官方2/1分差和精确字符串有公开依据。但正式actor仍未知，不填ready_for_probe；测试覆盖仅三个负例，不能说所有回归通过。

唯一优先下一步：**经actor身份/源码导入来源验明后，做一次base/gold公开行为对照**：先运行题面SupportsIndex程序（显式目标3.10、无site-package搜索），同时跑既有 `testAssertType` 的窄公开组，确认原例是否仍产生错误、如果产生是否完整限定、普通成功/失败/返回类型是否保持。预期有诊断的CLI非零不是环境失败；若base原例已无错误，应保留事实并另用公开同名名义类说明该缺陷，不能倒推改写原记录。此选择优先解决当前最具体的不确定性；顶层-only部分修复的嵌套泛型反例作为后续有限覆盖增强理由，未执行/未写补丁。

未查：本题旧历史（待明确放行）、reviewer、当前CPU/actor、原题实测、全部共享formatter调用者/递归别名边界、重复/并发、真实Git资产泄漏、独立来源runner对账、真实模型轨迹/成本。初稿封存后不回写。
