# python__mypy-10174 · 独立私有初稿（历史前封存）

封存UTC：2026-09-20T21:30:43.289761+00:00。暂定 `needs_review / static_review`，仅 `development_diagnostic`。**原题误报、gold修复和历史0/1分差可信；但两条P2P都测未导入Any的提示，不能保护严格比较功能。** 存在具体“non-strict optional时关闭所有危险比较”部分修复的静态漏测路线，宜做一次窄反例对照再决定是否补验收。未执行该路线，不把推断标作已证实假阳性。

## 身份、输入和暴露

ROOT=`${REPO_ROOT}`。P=`runs/swegym_quality_batch03_20260921_v1/public/python__mypy-10174`，Q=同根private/python__mypy-10174；下述源码相对P/base。先读本题封存public_read.md，再核public_bundle、base_identity及Q的grading/validation/test/gold/source_refs/run_refs/environment_record。base=`c8bae06919674b9846e3ff864b0a44592db888eb`，tree=`465ff7bfb889519de37d2ddc384fda40f39240a7`，版本0.820、spec Python3.9，gold SHA256=`7f94c5b71301dbbf5ccce1af8b274444ab5c0de5010f92109e11549154066f6c`。材料验收沿用父协调者，不重做blob清单遍历。

已看见environment_record内verified_environment_pair及noop/gold摘要，随后核精确原ledger/log/diagnostics；本稿不声称未见运行结果。未看本题history/refs、旧质量报告、B1/B2、本批聚合、他题结果或reviewer；不把同仓前题判断当证据。未运行/导入项目、测试、安装/下载、联网、Docker/SSH或模型；只做文本/Git允许范围内静态阅读和文档写入。

R=`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-10174`。GL=`R/gold/eval_logs/evallog_replay-er19-iw1-python___f589d38e.eval.log`，NL=`R/noop/eval_logs/evallog_replay-er19-iw1-python___e59bc664.eval.log`；两角色ledger均第1行，对应diagnostics也已读。

## 1. 公开需求与双向映射

题目明示 `no-strict-optional + strict-equality` 下Optional[Any]成员检查不应误报，并明示strict optional开启时原本正常。公开docs/source/command_line.rst:562-580要求strict equality继续检查真不重叠的等值/身份/容器比较，None例外；checkexpr.py:2293-2308明确Any overlaps with everything。没有新增API、输出字符串或必须修改meet.py的实现限制。不能靠关闭strict equality、隐藏所有错误、修改用户输入完成任务。

| 需求/旧行为 | 公开依据 | 官方验收/原日志 | 覆盖 |
|---|---|---|---|
| 原题Optional[Any]在no-strict optional成员检查无误报 | user_prompt完整例子；checkexpr.py:2307；meet.py:164-176 | 唯一F2P `mypy/test/testcheck.py::TypeCheckSuite::testOverlappingAnyTypeWithoutStrictOptional`；期望空诊断，NL:514-516实际Non-overlapping错误，GL:532通过 | 直接覆盖题面主体；用flags等效表达内联配置 |
| strict optional开启仍无误报 | user_prompt末句 | F2P仅--no-strict-optional | 缺少该对照；gold在strict optional路径中移动guard跨过未执行分支，静态应保持但未新测 |
| 真不重叠类型仍报警 | docs:562-580；check-expressions:2397-2462,2764-2769 | 官方无任何比较应报警断言 | 具体漏测；P2P不能区分关闭比较检查 |
| Any/any未导入的错误和建议保持 | check-expressions:2771-2780；semanal.py:4728-4761 | 两P2P testUnimportedHintAny、testUnimportedHintAnyLower：各一条Name not defined错误+一条typing.Any导入note；NL:520-521、GL:533-534均过 | 确实执行但与overlap算法无直接回归关联 |
| 直接Any、None、数值提升、自定义eq/contains行为保持 | checkexpr.py:2310-2353；公开StrictEquality各组 | 无相关P2P | 已读公开回归；未执行；不能从2P2P推出这些已保护 |
| overlap的收窄/可达性用途保持 | meet.py:53-76；checker.py:4140,4346,4513,4984-4994 | F2P只看诊断，无reveal/可达性断言 | 共享函数回归范围已追，静态gold合理，无完整行为证明 |

反向核约束：F2P的“空输出”直接来自误报应消失，不限定错误文案或代码结构；flags均公开原题已有。P2P精确导入提示是base已有行为，不是隐私新要求。test.patch没有任何内部helper或Mock断言。无需根据gold倒推题意。

## 2. 完整新增测试、P2P及其helper/fixture

test.patch只向现存check-expressions.test插入一个11行case：flags两个开关，导入Any/Optional，未赋值的x:Optional[Any]，`if x in (1,2): pass`，tuple和typing-full两个fixture；没有E/N/out段意味着要求**全部诊断为空**。Python片段供静态类型检查，未赋值x不是运行期NameError缺陷；测试不会执行该程序。无新增/修改helper、fixture文件或业务源码，无Mock/网络/随机数。

该0.820 runner与较新版本不同：testcheck.py:26-97是显式data文件列表，check-expressions在:72；DataSuiteCollector在data.py:558-565直接遍历文件并产生case节点，所以实际ID为三段（不带data文件名）。已读data.py:31-81的fixture装配、:421-449的E/N转换；helpers.py:372-395解析flags、无flags时关闭strict optional；testcheck.py:137-207实际build.build，:214-234比对全部errors；helpers.py:44-58归一can't/cannot和路径后比较，原NL:508-511可见差异断言真实触发。

两个P2P均读完整：base check-expressions.test:2771-2780，分别函数参数写Any和any但没导入。默认最小builtins没有any（lib-stub/builtins.pyi全文1-22已读），因此两例均要求未定义名字错误、另要求精确typing导入建议；semanal.py:4728-4761对缺名小写匹配TYPES_FOR_UNIMPORTED_HINTS（messages.py:45-55含typing.Any）。它们不会调用本题成员检查路径；不是一个隐藏的Any overlap正反测试。

F2P fixture tuple.pyi全文1-47、typing-full.pyi全文1-170已读：tuple继承Sequence、__contains__(object)->bool，Sequence继承Container[T_co]，Container.__contains__声明在:44-48，Any/Optional是语义分析特殊对象（:15-17）。checkexpr.py:2191-2229调用__contains__并经checker.analyze_container_item_type(:3514-3533)取int元素类型，再进入dangerous_comparison，最终meet.is_overlapping_types。fixture无运行时容器比对或伪造输出。

## 3. 原始执行与初态因果

原NL:494-527命令为 `pytest -n0 -rA -k 'testOverlappingAnyTypeWithoutStrictOptional or testUnimportedHintAny'`，9422收集、3选中，真实F2P失败（空Expected vs `Optional[Any]`和int不重叠Actual），两个P2P通过，rc1。GL:521-539同命令三过、rc0。-k第二项同时匹配AnyLower，所以2个选择词产生3个节点是可解释的前缀匹配；所有三个节点均在冻结参考1F2P+2P2P，**不是未评分的额外节点**。

两份ledger第1行：解析键3，reference_missing/skipped均空、段外0；gold f2p1/1+p2p_fail0/2→reward1，noop f2p0/1+p2p_fail0/2→reward0。参考ID三段与原日志一致，未凭新版四段ID猜错配。收集9422、执行3、解析3、参考3分别记；分差来自原题错误，非安装失败、漏收集或仅以rc1固定判0。

源码因果独立成立：meet.py先在:164-166检查直接Any，再在:171-176移除Union中的None；types.py:1801-1806去None、:1777-1783单项Union直接返回Any。之后proper-subtype不把Any视作通配（subtypes.py:1132-1139,1218-1219），可能落到meet.py:354-355不重叠。gold将Any检查移到规范化之后，使该新暴露的Any也命中原Any规则。原日志提供目标症状，未捕获逐函数运行trace，所以精确中间类型流仍属代码推断。

## 4. 合理替代、gold完整性、回归与漏测

合理非gold路线可以在比较路径内对non-strict optional的两侧类型规范化后处理Any，或为共享overlap的规范化新增一致入口；外部要求没有绑定代码行移动。只要保留strict equality其它诊断与公共overlap语义，官方断言不会因实现形状拒绝。未见私有输出格式或函数命名强制；没有理由强制造第二份合法补丁。

gold仅重排meet.py中Any guard，双侧对称、没有新依赖、没有扩大修改范围。strict optional时规范化块不执行；直接Any仍返回True；None、TypeVar、tuple/TypedDict/Callable等后续判断未改。静态未见gold漏修原例或引入不相关语义，官方原题已通过。但共享overlap还用于narrow_declared_type、容器成员收窄、父union属性收窄、optional比较收窄、conditional_type_map；已分别读meet.py:53-76、checker.py:4128-4148,4326-4356,4498-4516,4963-4994。未穷尽meet其它组合递归、插件或所有tuple/TypedDict分支。

公开回归实际阅读范围：check-expressions:2397-2677（Eq/Is/Contains/Unions，bytes/bytearray，promotions，Any，strict optional开关，两个Optional的真不重叠，自定义eq/contains，Type-vs-Callable/Metaclass）；:2764-2780固定tuple负例与两个P2P。check-isinstance:1869-1926读Any收窄及容器内Optional/不重叠分支；:2213-2262读TypeVar None及generic Optional在strict开关两侧。后者有源码注释明确间接测试meet去None。以上未运行且不属于本题P2P，不能写成回归已过；部分依赖fixture仅定位未全文读取，未称扩展测试执行环境已全部审完。

**有具体依据的部分修复**：若dangerous_comparison在not state.strict_optional时直接返回False，题面F2P无诊断，而两个未导入提示P2P仍独立存在；预期可过本题参考，但同配置下`1 in ('x','y')`本应报错也被关闭。这个反例只改元素类型，来自公开strict-equality规格及固定tuple旧用例，而非审查者另加功能。尚未写候选、没有本轮CPU/RH2结果；严格区分“可判别的静态漏测”与“已验证满分错误解”。无条件is_overlapping_types返回True还会影响收窄，不推荐用如此宽补丁代替本次窄实验。

## 5. 开发条件与环境证据

| 需要的操作/资产 | 公开依据 | 本题已有证据 | 缺口和最小验证（未执行） |
|---|---|---|---|
| 定位并运行源码mypy | 原题完整片段；checkexpr/meet路径；公开源码运行说明 | 历史grader Python3.9.19、导入观测/testbed/mypy/__init__.py | 正式actor解释器、PATH、.so遮蔽/源码生效、CC消息未知；先打印sys.executable与meet/checkexpr来源再做公开C2 |
| 历史依赖和工具 | mypy-requirements全文：typed_ast>=1.4,<1.5、mypy_extensions<0.5、toml；test-requirements全文含pytest6.1,<6.2、xdist<2 | GL:430-511、NL:403-484原spec requirements、editable、额外pip install pytest pytest-xdist均成功；typed_ast1.4.3、mypy_extensions0.4.4、pytest6.1.2、xdist1.34.0 | 不应用新版本依赖要求替换旧版；actor预置及可写prefix未知，缺件需离线资产，不能假定公网 |
| fixture与完整typeshed | tuple/typing-full与相关公开存根 | 官方实际fixture读入并运行；静态导出存在 | actor公开CLI完整typeshed与相同镜像仍待验；无需外部数据/服务/GPU |
| 配置/缓存/临时写入 | 内联配置优先级；testcheck输出main及cache_dir | grader有2CPU/4GiB、tmp1GiB、deny_all；单次峰值约124/128MiB、cleanup removed=true | 正式actor身份/权限/资源与稳定性未验；strict optional对照应替换内联首行，不能被旧首行覆盖 |
| 编译/安装/交付 | gold纯.py、源码开发入口；可选mypyc | 原editable wheel是纯Python，已预装typed_ast；无必要新编译 | 需要重建依赖时环境阶段负责；无需改不可提交文件，meet.py/checkexpr.py合法源码修改均不被official恢复 |

已读本题image.json和environment_replay_inventory的common、install_wave1及exact任务对象；派生ID=`sha256:1a440521871061d2e8db3fa660c7bf1a225d7fed9ac82d70dbda6cd726af7369`。仅COPY离线wheels+ENV，仍原spec，无recipe/materials/bindings覆盖；不是COPY即安装成功，结论来自原日志。当前机器镜像存在性与原wheel payload未验/本地未保存，后续不能按历史/work路径直接运行。grader用户rh2grader/54322、补丁apply用户agent/54321不等于正式actor运行已验。

## 6. 投影、官方恢复与评分控制面

复用已只读的baseline.tar.gz成员文本身份，非当前ROOT/rh2：`src/repoharness2/envpack/spec_vendor.py` SHA256 `8e0037b27c87268ed7df97ef64d261d0e6dac7375bc85fd5badd0fecdb94d41d` (:183-197 mypy case正则)；`src/repoharness2/adapters/slime/prepared_task_face.py` SHA256 `3a3d7bcab18e8a83f99104180e065ed32d8ecbce5d1bd4aaa7f8bd72b001aa27` (:185-211,305-330 official路径/test_globs空)；`src/repoharness2/envpack/scoring.py` SHA256 `b6c8b9bd3e9cac604bc0d03b0b243ef9646de369e94bb6a65e60eadd3a64f5ab` (:189-270参考清单)；`src/repoharness2/envpack/swegym_parsers.py` SHA256 `995bb6aae58a94f9553946c2f9aea59a158ad4fdf4d7fc0137802c11362b2276` (:88 pytest parser)。归档=`runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz`，没有解包或执行。

本题官方文件恢复仅test-data/unit/check-expressions.test，NL:229/GL:256精确checkout，diagnostics expected/restored/test_files=1、apply_rc0/setup_ok1/protect_ok1。gold projection included=mypy/meet.py、ignored=[]；test.patch只改测试数据，没有源码/混合职责文件被恢复覆盖。旧公开hints“所有测试都恢复”不能代表实际test_globs空机制。相关runner/helper/config仍属潜在控制面，但本轮不重复平台安全总审计，没有证明新绕过；additional_exclusions=[]。

## 7. 关系和用途

本题类型是选项组合导致的类型检查误报，不是固定输出/安装题；题面没给实现。未见/未查具体跨题相同commit或patch关系，不按mypy目录聚类。公开包无.git不代表实际容器资产、可见历史或缓存无答案；不访问网络答案，未查模型轨迹。审查者已见本题隐藏测试/gold/环境结果，产物不得给solver；无训练/正式评测准入、无能力/成本判断，未知成本null。

## 8. 暂定问题与唯一优先CPU建议

问题一：F2P只要求误报消失，P2P为导入提示；缺少同配置下“确应报警”的负对照，故可容纳关闭比较诊断的部分修复。证据是完整case/调用链的静态推断，不是本轮执行。问题二：grader配方已恢复且0/1可解释，正式actor、当前镜像/资产和实际消息仍待验。gold当前未发现错误；不能把回归缺口改写成gold已破坏。

唯一优先实验（只建议、未写/运行）：在经身份/导入来源核验的干净base、gold及一个“not strict_optional时dangerous_comparison直接False”候选上，同时保存原官方1/2得分与**同开关的公开窄负例** `if 1 in ('x','y'): pass`。该负例基于原公开fixed-length-tuple用例，将no-strict-optional显式加到输入首行；预期base/gold保留comparison-overlap，而部分修复丢失。若候选官方仍满分便确认漏测；之后再把这条行为对照纳入独立修订，不改原reward记录。无需全仓或强制再造正确替代补丁。

尚未查：本题历史（等待放行）、reviewer、正式actor/当前CPU、真实原题CLI（只有等效官方data case运行证据）、所有共享overlap组合与扩展fixture、重复/并发、实际Git/镜像资产/网络可达、独立来源runner对账、模型轨迹/成本。初稿封存后不回写。
