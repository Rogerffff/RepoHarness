# python__mypy-17071：无历史私有审查初稿

2026-09-21；B2 private investigator。**needs_review / static_review；intended_use=development_diagnostic；additional_exclusions=[]；未知 cost=null。** 本稿先写后封存，未打开本题 history/refs.json、旧调查或 environment_record.json。已读本题封存的 public_read.md，但下列私有判断以原始包、源码、账本和日志交叉核对。没有运行项目代码、测试、安装、Docker/SSH、网络或付费模型；没有修改源码、原测试、gold、reward、共享镜像或提交。

路径均相对于权威 ROOT=${REPO_ROOT}。U=`runs/swegym_quality_batch02_20260921_v2/public/python__mypy-17071`；P=对应的 private/python__mypy-17071；`base/` 指 U/base。W=`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-17071`；G=W/gold，N=W/noop。Glog=`G/eval_logs/evallog_replay-er19-iw1-python___9334e4a9.eval.log`，Nlog=`N/eval_logs/evallog_replay-er19-iw1-python___2965a84e.eval.log`。Ga/Na 分别是两侧 `artifacts/swe_gym_lite--python__mypy-17071/a1-2c4b6784`、`a1-a6be602c`。

## 1. 公开需求、可推导范围与可解性

公开 issue 在 U/user_prompt.txt:3–34 与37–68重复：`type_guard(x: Any, type_check_func: Callable[[Any], TypeGuard[T]]) -> T` 在回调判断失败时抛异常、否则返回 x；传入 `is_string` 后不应报 “A function returning TypeVar should receive at least one argument containing the same TypeVar [type-var]”。任务指定基线是 `4310586460e0af07fa8994a0b4f03cb323e352f0`；报告者写的1.4.1不是要求另装该版本，任务材料版本1.10与源码/日志一致。

复现片段缺 Any/Callable/TypeVar/TypeGuard 的导入、T定义，return 缩进不一致。按本地已有 TypeGuard 示例补导入、`T = TypeVar("T")`、把 return 放回函数体即可保留原意；不需私有测试才能修复语法。公开明确要求修检查器，不是要求用户删泛型、加cast、改函数名或关闭错误码。函数名、字符串值、异常拼写不构成固定接口。题面说“不报错”，结合函数返回 T 及现有泛型约束，结果继续为 str 是合理保留语义；退成 Any 不是等价完成。

静态因果链完全位于公开代码：checker.py:1156–1168 对直接 TypeVar 返回调用 check_unbound_return_typevar；1422–1430 用 CollectArgTypeVarTypes 遍历每个参数，再判断返回变量是否被收集；7389–7396 只重写 TypeVar 的访问。typetraverser.py:83–87 访问 callable 的 arg_types、ret_type、fallback；types.py:1802–1803 明确 TypeGuard/TypeIs 的目标类型另存在 type_guard/type_is，普通 ret_type 是 bool。因此仅存在于 callback guard 目标中的 T 被漏收集。constraints.py:1020–1037 已分别用 guard/is 目标推约束；Nlog:504–524 确认 no-op 已推断 str，同时多报目标错误。这是约束存在性检查的遗漏，不是“完全不会推断T”。

本地 docs/source/type_narrowing.rst:197–242、255–274 解释 TypeGuard 的 bool 表示、目标收窄与泛型行为；公开已有高阶/泛型/别名用例，无必须补入的外部附件或在线服务。TypeIs 未出现在 issue，但相同字段表示、约束、旧高阶/别名测试已经公开存在。统一补两字段有充分源码依据；是否把 TypeIs 同形新用例当作本任务强制新增需求仍需审定，不能把 gold 处理了它直接当成公开明示要求。

U/public_bundle 的 public_hints 是通用 harness 操作指示，含只改 NON-TEST、窄测试、conda已激活以及“所有测试修改都恢复”等文字。实际 actor 消息/可见内容未捕获，不能从 user_prompt 未渲染该字段断言 actor 看不到；prepared_task_face.py:342–356 将公开 bundle 另送入任务面。当前机制并非恢复所有测试，见§7。正常源码修复不需要违背不改测试的指示；测试禁改不使本题不可解。

## 2. 初态、材料身份与原始运行对应

P/source_refs 指向 S2/ingest 的 public_bundles_v0.jsonl、grading_bundles_v2_v0.jsonl、validation_bundles_v0.jsonl **各第212行**。只抽取这些精确行，三个对象与 U/public_bundle、P/grading、P/validation 逐字段相同；canonical JSON SHA256 分别为 `a0f8fbcda2a23a59e6da28a2c312a57afefd7cc9cbf74b243e0f0f0d58c966cb`、`1bcfca5542bb8ec1a151bf09b650604f3745174912d0300862149f2f42092ac5`、`37d8a270e19c0539189937eb7f96833b7b6d083621190da85d46bb2d30ec95d8`。P/test.patch SHA256=`3bd1f0adaf901bb07a24fed9578779b45deac88e565f46977997a34bace12c8e`；P/gold.patch=`fcc697876239908bf4070a03921326432d564c54da43073587fec909aae0467b`。本题未发现测试材料修订；install-wave1 是依赖轮子镜像修订，不能称改变了断言或冻结引用。

U/base_identity 给 base tree `e8da67af898c33c185acbc9477abfba4f87e3551`、1474个blob、无git元数据/symlink/LFS缺件/gitlink。Ga/Na stage 的HEAD都等于指定base；baseline_manifest 两侧完全相同；1474个公开blob逐个按SHA核对全部一致，无缺失/差异，额外只有6个 mypy.egg-info 文件。这证明已读记录中的评分初态与导出源码相符，不等于正式actor镜像/预装包全部验净。

Ga/candidate.patch 与 P/gold.patch 字节相等；Ga/frozen_patch 只有 mypy/typetraverser.py，解码源码 SHA256=`b7be216425043ada1ca5eeda039b22699de86e8704868730f87fb247094ad0eb`。完整diff与保留空行的精确文本构造均核实只是 gold 的两个字段访问及空行。Na/frozen_patch entries=[]。两侧 classification 都是 projectable，无runtime_private_pathset_changed，无stage_error。

G/N ledger.jsonl:1 的真实环境相同：public manifest `ffc5cb69679917b638305b44d91ad941f22934fbb49acb20eac12f2fdae3ed99` 对应 base image ID `de8e2c4bf1c31507ed2ea5d0312e7b8e43d2a70b03a6a2698d7d2059f046ca35`；实际使用依赖修订后的 image ID `65be15358f008d20c0dd256c9e70e3f09c85154113ea04875f1a71e98ed751fe`。正式actor仍指public image。Glog/Nlog的字节SHA与P/run_refs一致，分别 `0c3a93d8b6e408f077e7c0850360e3bea27df194b2b2db402c69c1ca2f769022`、`157f289d953f20635d3aebd663e2932d8dc7c6eab52f32815ebae558ec8f5148`。

| 原始对照 | 安装、运行和原始输出 | 冻结评分解释 |
|---|---|---|
| Gold，attempt1，G/ledger.jsonl:1 | install5.451s；test17.359s，rc0；Glog:471–495 editable build与安装每步成功；509–530四项通过 | F2P2/2；P2P0失败/2；reward1；4个解析结果，无缺引用/跳过/段外解析，无全局失败 |
| No-op，attempt1，N/ledger.jsonl:1 | install4.821s；test19.759s，rc1；Nlog:449–473安装成功；487–541真实2失败2通过 | F2P0/2；P2P0失败/2；reward0；两个目标均多出UNBOUND_TYPEVAR，已正确reveal str；不是零解析或安装早退 |

两侧账本记录从 `/testbed/mypy/__init__.py` 导入，runner前后digest一致、cleanup removed=true；包版本观测为“?”，不能借此补出独立版本证明。日志editable产物名和base HEAD提供该次版本对应。只有这对各一次历史执行原件，不宣称重复稳定性或完整测试通过。

## 3. 逐项断言、F2P真正测什么，以及三种范围

P/test.patch只有两处新增case，没有修改旧case断言：check-typeguard.test插入12行，check-typeis.test插入12行。两个新增case结构相同，将TypeGuard替换为TypeIs；unused Optional 导入不承担行为断言。都用 `object`（题面用Any）、显式 T、`is_str(...): pass`、失败分支 `raise Exception()`、正常分支return x，最后只显式写一条 `reveal_type(...)=builtins.str` note。

| case/断言位置 | 真实断言与可观测边界 | 对公开需求/失败的解释 |
|---|---|---|
| `testTypeGuardTypeVarReturn`，patch:8–18，特别13–17 | 声明 callback 的目标T使外层返回T合法；整份输出只有 main:9 的str note，隐式拒绝所有额外error；return x需在成功路径收窄可返回T；调用保留str推断 | 直接对应issue的结构，使用object比Any更能约束收窄；Nlog:515–524仅多出main:5目标诊断，str本身已对。未覆盖真实isinstance函数体或题面Any/TypeError文本组合 |
| `testTypeIsTypeVarReturn`，patch:30–40，特别35–39 | 同样要求callback中的TypeIs[T]参与外层变量收集、输出仅str；保留该控制流的返回类型检查 | 同根因扩展；Nlog:499–508多出同一诊断。仓库已有同类语义，但题面没有明示TypeIs，范围疑义见§4 |
| 新输入共用fixture，patch:18、40 | `[builtins fixtures/exception.pyi]` 已存在，定义object、str、bool、BaseException/Exception；lib-stub/typing_extensions.pyi:36–37定义TypeGuard/TypeIs | 没有缺件证据。测试做静态类型检查，不执行is_str的pass；mypy/test/testcheck.py:137–138允许empty body。不能把pass当runtime假函数漏洞，也不能仅凭运行包版本推断TypeIs stub缺失 |

mypy/test/data.py:55–60、106–117 解析case并加载stub；334–360创建独立临时目录写入输入。testcheck.py:108–165配置数据测试并调用真实build.build，读取真实checker/constraints/traverser；165–195取得完整diagnostics并逐行比较预期。不是mock调用次数、内部方法名或gold文件形状检查。简化builtins、关闭普通incremental缓存、允许empty bodies限定了覆盖范围，不代表在用户CLI默认typeshed中的所有形式均已验。

**执行选集**来自 vendor 对整个test.patch（含上下文case名）的正则抽取，不只新增行：`pytest -rA -k 'testTypeGuardTypeVarReturn or testTypeGuardIsBool or testTypeIsTypeVarReturn or testTypeIsUnionIn'`。Glog:509–517、Nlog:487–495实际为4 items；pyproject.toml:111默认`-nauto`，原件实际11 workers，不能冒称用-n0单进程。上述四项全部有状态，不把全仓可收集项目或阅读范围当执行覆盖。

**冻结奖励引用**也是四项，但角色不同：F2P为 `mypy/test/testcheck.py::TypeCheckSuite::check-typeguard.test::testTypeGuardTypeVarReturn` 与 `...::check-typeis.test::testTypeIsTypeVarReturn`；P2P为 `...::check-typeis.test::testTypeIsUnionIn` 与 `...::check-typeguard.test::testTypeGuardIsBool`。这里执行集恰与引用集相等，来源机制仍不同，不能一般化为从执行输出重建奖励引用。

**实际阅读**除这四项，还沿调用链读了未选中的公开负例、合法嵌套、generic/alias/higher-order旧case以及共享visitor调用者；见§5和末尾清单。它们没有运行，也不受当前两个P2P保护。不能把“读过该测试文件”“运行该case”或“冻结保护该行为”混用。

两个P2P逐项解释：TypeGuardIsBool（base/check-typeguard.test:57–66）的三个reveal断言分别检查函数参数、普通变量、实例属性都按bool表示，保护既有表示而非返回TypeVar检查。TypeIsUnionIn（base/check-typeis.test:95–105）的三个reveal断言检查if分支str、else分支int、分支后原Union[str,int]；它保护正负分支收窄。两者无返回未绑定TypeVar的函数，不能发现全局关闭该诊断。

## 4. 合理解法、范围疑义与具体部分实现

两条合理源码路线有公开依据，均可合法投影：A在 CollectArgTypeVarTypes 中补callable guard/is目标递归访问，保持其它类型访问；B完善自称遍历所有类型组件的公共 TypeTraverserVisitor，让现有收集器自然收到T。B是gold路线，但测试不检查必须改哪一文件，A并未被静态规则排除。只改顶层参数名、把未知T统一当Any、直接关闭[type-var]、改用户输入等不算正确修复。没有运行任何替代补丁，不能宣称已证oracle接受所有正确解。

仅列与已见证据直接相关的两项待验候选：

1. **有具体依据的部分实现漏判候选**：将 checker.py:1422 的 `check_unbound_return_typevar` 方法体变为直接return，其它推断保持不变。Nlog证明两个F2P的str已经正确，只多出此方法发出的诊断；两个P2P不进入直接返回TypeVar检查。因此静态上很可能得到四项通过。它会漏报公开 check-typevar-unbound.test:1–19 中 `f() -> T`、上界U、取值约束V的错误，以及check-generics:1599、1601的不匹配返回变量。无硬编码测试名也能形成偏差。尚无该候选的实际冻结得分，所以记为unknown的强假设，不写“已证false positive”。最小实验是统一CPU负责人的同环境candidate重放，配合公开未绑定负例；不能只以新增F2P通过认证质量。
2. **范围过窄可能被拒的合理路线候选**：仅在参数收集器递归访问type_guard，保留base type_is行为。它可能完成题面TypeGuard原例并保持已存在旧例，却仍失败TypeIs新增F2P。公开两个字段/约束/成对旧测试支持应一并修；issue只明示TypeGuard又支持较窄修复的可辩护性。因此这是待裁定的scope ambiguity，不是已经证明隐藏测试越界。最小验证同时记录原题补全样例、该候选四个引用结果及TypeIs对应行为；范围决定需先看公开契约，不能以gold或旧结论倒推需求。

F2P的str输出并非无依据的唯一字面偏好：泛型结果若被降级Any、错误类型或破坏guard收窄，会违背公开返回T语义与旧推断习惯。测试没有新错误文案匹配要求，主目标恰是不得出现错误。未发现“只有gold特定内部调用才能产生该输出”的证据；也未证明所有实现/更复杂泛型均正确。

## 5. Gold、相关旧回归与调用者

Gold只在 typetraverser.py 的 visit_callable_type 中，现有arg/ret/fallback遍历之后新增两个非None检查并accept type_guard、type_is（patch:8–13，含空行）。其直接效果是收集只存在于guard/is目标中的T，不重写约束推断、Subtype、诊断文本或测试。对公开TypeGuard需求方向正确，原件已证明冻结四项通过；TypeIs扩展有共享组件完整性依据。未运行题面补全原样CLI，不能把object+empty-body数据测试替代所有用户默认条件。

| 相关公开行为（实际静态读过） | 必须保持的内容及与本补丁关系 | 当前保护/验证范围 |
|---|---|---|
| check-typevar-unbound.test:1–19；check-generics:1593–1601、1643–1652；check-errorcodes:256–263 | 真正返回未绑定T仍报同一诊断；上界提示与[type-var]仍在；排除“取消检查” | 不在F2P/P2P；未运行。第一优先的独立负例 |
| check-typevar-unbound.test:21–65 | 外层绑定、普通Callable返回T、Union/List/Tuple中嵌套合法参数继续接受 | 不在冻结引用；帮助限定局部visitor方案必须递归而非一层特判 |
| TypeGuardWithTypeVar:68–76；TypeGuardHigherOrder:115–125；TypeIsHigherOrder:124–134 | 泛型收窄/高阶回调结果保留T或Iterable[float] | 静态已读；没有被这次四项命令选中。高阶返回Iterable[T]不等于直接返回T，不能替代新F2P |
| TypeGuardAsFunctionArgAsBoolSubtype:461–474、TypeGuardAsFunctionArg:476–491、TypeGuardAsGenericFunctionArg:493–508；TypeIsAsGenericFunctionArg:496–511 | guard可用于bool期望；bool回调不能反过来当任意guard，目标类型须兼容 | 静态已读；P2P IsBool仅覆盖表示，不能概括这些compatibility负例已保护 |
| GenericAliasWithTypeGuard:687–696；GenericAliasWithTypeIs:707–717 | 泛型别名中目标类型继续推成str；fixture本身带入的变量按真实测试环境解释 | 静态已读；traverser的TypeAliasType访问参数、不直接无限展开target（129–133）；不是新直接形式的重复测试 |

共享visitor调用者也已跟读：FreezeTypeVarsVisitor（checkmember.py:847–855）递归冻结callable变量；TypeVarLikeNamespaceSetter（tvar_scope.py:21–37）设置变量namespace；CollectAllInstancesQuery及find_type_overlaps（messages.py:2678–2720）影响同名类型的诊断显示；LocationSetter（types.py:3486–3495）设置Instance位置；MixedTraverserVisitor（mixedtraverser.py:25–99）把AST和类型连接。公共修复会使这些调用者看见以前遗漏的目标组件，这是设计一致性和额外回归检查的依据，不是已观测的回归。没有穷举全部调用图、TypeVar默认值/递归别名、method泛型或增量行为；不将它们机械列成题目缺陷。

## 6. Actor开发条件、依赖与镜像修订

W/image.json 与build.log以及 install_wave1/run_install_wave1.py:24–62 只核通用构建机制及本题参数：源base ID核对后，用固定RepoDigest为FROM，仅COPY既有wheel到`/opt/rh2/build-wheels/`，设置`PIP_NO_INDEX=1`、`PIP_FIND_LINKS`，断言原层保留，再将 derived image 显式传给replay_grade.py。未运行此脚本，未读取批次计划/其它题分支。W/image.json SHA256=`80d96e1136aced851e42fe9bddae91b3a23650665ec54f343d5c71c13ef6e744`；完整derived ID为 **`sha256:65be15358f008d20c0dd256c9e70e3f09c85154113ea04875f1a71e98ed751fe`**。该镜像并非包含本题gold的新源码层。

本题轮子pin为setuptools68.2.2、wheel0.43.0、typing-extensions4.8.0、mypy-extensions1.0.0、tomli2.0.1、types-psutil5.9.5.17、types-setuptools68.2.0.0、packaging23.2；pyproject:1–16的editable构建依赖及G/N安装原日志与之对应。requirements安装已满足、build isolation完成、editable wheel构建/安装完成都有原始成功行（Glog:436–495；Nlog:409–473）；不以最终hash -r的rc=0独自认定每步成功。无需在本轮再“修复”这套已存在的依赖实验；它也没有证明public镜像actor得到同样资产。

| 开发动作/资产 | 已有证据 | 正式actor缺口 |
|---|---|---|
| 激活Python、导入mypy和开发依赖、运行补全issue | 公开源码/依赖，评分Python3.12.4；G/N观测导入/testbed/mypy/__init__.py | formal public image在agent/54321下的sys.executable、PATH、mypy及子模块来源、shadowing/编译模块均待验；grader导入不代替actor |
| 运行TypeGuard静态示例与真实数据测试 | 本地lib-stub/fixture齐全，四项真实build已在grader运行 | actor pytest/xdist插件、临时目录写权限需验证；输入是静态检查，不能误要求执行示例运行时函数 |
| 若需要editable安装 | derived镜像预置离线wheel，grader允许conda prefix写入，实际成功 | actor不能假定有这些wheel或可写/opt/miniconda3/envs/testbed，更不能假定公网pip可用 |
| 写代码、临时输入与缓存 | 数据harness使用TemporaryDirectory；公开hints要求源码修改 | 工作树/home/tmp实际容量、所有者、实际shellcwd待验；本轮只有读出的计划边界和grader原件 |
| 资源、外部服务 | 问题是本地类型检查，无必要外部服务/GPU/私有附件；原grader2CPU/4GiB/PID512、shm64MiB、tmp1GiB、deny_all | 默认-nauto实际创建11workers，已有四项成功但不能保证全文件/全仓或重复运行稳定；正式actor资源/网络边界仍需实际验 |

G/N policy是 **rh2grader UID54322**，conda prefix owner观测也为54322；candidate阶段可写该prefix，env_qualification=absent。它们不是agent/54321的开发测试记录。当前 rollout_spec_from_view:342–356仍取public.image与public.image_manifest_digest；RolloutSandboxProfile:323–339规定agent/54321、2CPU/4GiB、tmp1GiB、home256MiB等默认边界，实际值和权限需要actor原件。公开image为 `xingyaoww/sweb.eval.x86_64.python_s_mypy-17071:latest`，manifest固定如§2；不能把派生评分环境直接填成正式actor已验收。

后续命令只作建议，未执行：先在真实actor `/testbed` 用`id`、`python -c 'import sys, mypy; print(sys.executable); print(mypy.__file__)'`确认身份与源码，再用public_read.md B/C中的最小补全issue和`def unbound() -> T: raise RuntimeError`负例，`python -m mypy --no-incremental --cache-dir=/dev/null --show-error-codes -c ...`。窄公开pytest宜显式`-n0`，但冻结评分重放应保留正式派生命令，不将建议的开发命令冒充原运行。缺依赖时由统一CPU负责人确定已有离线资产及权限，不自动联网/安装。

## 7. 投影、恢复、评分、控制面与泄漏

prepared_task_face.py:312–338从grading.test_patch推导精确test_files，test_globs=()；本题只有 `test-data/unit/check-typeguard.test` 与 `test-data/unit/check-typeis.test`。Glog:249–262真实checkout这两文件并应用官方test.patch。gold只改typetraverser.py，未被恢复覆盖；Na为空投影。没有“全部测试恢复”或按测试文件名统一剔除的机制事实；源码、依赖文件、未被官方patch触及的fixture/测试辅助代码不能因名字含test而被推定不可交付。公开hints与实际边界存在描述差异，但本题正常源码路线仍可完成；不新增额外排除项。

当前 scoring.py:234–269只用有效标记段解析状态，对冻结F2P/P2P计分，报告缺/跳过引用；spec_vendor.py:183–190则只负责派生执行选集。manager.py:1197–1249区分正常完成pytest的0/1与启动、收集、内部等全局失败。普通完整pytest rc=1中的非引用失败不自动使reward0；本题N的两次失败恰都在F2P，所以reward0确由目标。原G/N各4个解析，段外0、缺/跳过=[]、execution_failure_decision=null；不能借一般RC规则掩盖这两项真实目标失败，也不把测试外的日志行当参考状态。

边界静态审查支持控制脚本与候选源码分层：实际runner前后hash相等，raw ledger与frozen artifact各自留身份，public任务面grading_spec=None。它没有完整证明actor对隐藏tests/gold/宿主路径/预装包完全不可见。导出无Git历史，公开包无gold补丁；Ga/Na额外egg-info内容并未作为源码泄漏全面审计，实际镜像、mount和访问拒绝未运行验证。审查者持有隐藏测试、gold、评分和原件是特权暴露，本稿与后续私有card/record不能交给solver。未知的预训练或先前解题暴露不能由文件隔离声明消除。

没有发现需要本题额外禁止某算法文件的证据；将checker.py或typetraverser.py排除反而可能封死合理源码解法。对§4的诊断关闭候选，首选验证冻结保护范围的实际语义，不以禁改整个checker文件代替可解释的oracle。测试辅助/fixture修改能否形成控制面绕过未作候选重放，不写已验安全或已证漏洞。

## 8. 八方面结论、未知项与下一项实验

已覆盖公开要求/可解性、初态与材料、所有新增断言和真实测试路径、合理替代与部分实现、gold和既有回归、actor依赖/资源、投影恢复/评分/泄漏、关系/用途/成本八方面。当前适合作为开发诊断候选继续review；没有证据自动判为坏题、成熟eval题或RL可直接投产题。

主要支持：公开链条足够定位字段遍历遗漏；两新增F2P真正调用类型检查器；同初态/同派生镜像的base和gold分差可解释；两个P2P真实通过；源码修复可交付且官方恢复不覆盖gold。主要缺口：正式actor未验；TypeIs扩展的任务范围仍需公开契约裁定；直接返回TypeVar负例未被冻结引用保护；原题补全CLI、合理替代/部分实现、较广共享visitor影响与重复稳定性均未运行。coverage gap不是拒收结论，只有具体偏差经对照确认后才决定修订或用途限制。

**唯一优先下一项实验**：由统一CPU负责人在明确身份与依赖的正式actor开发条件下，完成补全公开issue的base/gold对照，同时观察unbound负例（预期原态有目标误报、gold消除误报且负例保留）；这先确认真实解题可达与gold满足原要求。随后才对§4的“关闭诊断”和“只补TypeGuard”候选执行冻结评分/独立行为配对，不在本轮自行运行。没有原例失败证据前不补写题面输出、不自动增删F2P/P2P或改测试。

本题没有展开跨任务去重/近重复检索，未读别题材料或用共享文件名断言关系；relation仍unknown。未做盲解、真实actor轨迹、付费求解成本或训练收益实验。现存ledger阶段耗时可解释历史执行成本，但不是本次静态审查的wall/token/费用，也不是一次解题成本；当前未知成本为null。处置保持needs_review/static_review/development_diagnostic，独立reviewer待审，额外排除=[]。

## 实际阅读与版本边界

方法只用已授权B1 roles/investigator.md、record_template.md、actor_environment_card.md、上层quality_review_protocol及其明确链接定义。未打开B1/B2汇总、manifest、method_adjustments；未读17071/11236历史或本题environment_record。开始17071前已接触10308私有题并按其门禁完成审查，这是同主审顺序暴露，未将其结论作为本题证据。当前通用RH2机制按同一ROOT源码独立核对。

| 原件/源码 | 本主审实际阅读范围（非执行范围） |
|---|---|
| U公开包/身份/题面；P/source_refs、run_refs、grading、validation、test.patch、gold.patch；封存public_read | 全文或结构化字段；S2只抽第212行。sealed public_read中建议命令没有执行，也不把该角色读过的所有文件算作本主审已读 |
| G/N ledger.jsonl:1，W/image.json、build.log | 本题原件；账本/图像metadata全读，资源和成功事实仅用于对应派生grader。未读批次表或其它任务记录 |
| Glog/Nlog | 关键身份/恢复/安装/执行/完整四case结果相关段；G249–262、431–533，N409–544重点复核，另有激活/命令匹配行。未逐行通读重复conda输出；未将全日志哈希核对等同内容逐行阅读 |
| Ga/Na的stage、classification、projection、frozen_patch、baseline_manifest、Ga/candidate.patch | JSON元数据、全部路径/哈希比对；只解码gold唯一源码entry作文本diff；baseline不代表实际镜像所有文件 |
| install_wave1/run_install_wave1.py | 通用构建/每题replay机制24–71；本题参数取W/image。未读计划清单/其它题参数；只静态 |
| base/mypy/typetraverser.py；checker.py；types.py；constraints.py | traverser全文1–142；checker1148–1172、1422–1438、5707–5767、7387–7400；types1790–1815、3480–3510；constraints1007–1049（关键1020–1037截断后单独重读） |
| base/mypy/checkmember.py、tvar_scope.py、messages.py、mixedtraverser.py | 分别825–866、1–60、2652–2722、1–99；只沿共享traverser调用关系 |
| base/test-data/unit/check-typeguard.test、check-typeis.test | Guard1–95、115–126、461–509、687–700；Is1–26、88–135、496–512、707–718；已明确区分两个P2P和未选旧case |
| base/test-data/unit/check-typevar-unbound.test、check-generics.test、check-errorcodes.test | unbound全文1–71；generics1580–1618、1635–1664；errorcodes252–264 |
| base/mypy/test/testcheck.py、data.py；fixture/stub/config/doc | testcheck101–195；data55–70、98–122、326–365；fixtures/exception.pyi全文；lib-stub/typing_extensions.pyi1–40；pyproject1–25、98–116；type_narrowing197–242、255–274。文件名搜索包括不存在的mypy/conftest.py，未据此报缺依赖；实际配置来自pyproject与公开reader所述根conftest |
| 当前RH2 | prepared_task_face312–357；spec_vendor183–191；scoring234–270；manager1197–1249；sandbox_profile311–340。哈希分别为31ff5145…e4f8a3、8e0037b2…94d41d、b6c8b9bd…64f5ab、eadaa64a…ad6342、698edb17…fe5899，均可按相应当前文件重算 |

工具仅作静态文本/JSON阅读、搜索、stdlib哈希/字节/文本比较及写本初稿。未遵循日志中的“update test output”等被审计文本指令；未用搜索命中或输出截断部分作独立执行证据。保存后交协调者计算SHA封存并等待本题历史门禁，不提前进入11236或历史阶段。
