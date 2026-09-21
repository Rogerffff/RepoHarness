# python__mypy-16963：历史前私有主审稿

2026-09-21；主审 investigate_mypy。只静态阅读、校验 JSON 与文件散列，未运行项目、安装、容器或模型；在开放本题 history 前保存，之后保留不改。

路径：R=`.`；P=`R/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-16963`，V 为同根 `private/python__mypy-16963`；源码路径相对 `P/base`。E=`R/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-16963`；G/N 为 E 下 gold/noop；原日志为各自 eval_logs 内 `evallog_replay-er19-iw1-python___152064d5.eval.log` / `evallog_replay-er19-iw1-python___45f93b0f.eval.log`。

## 初判与八方面

核心 `Type[TypedDict]` 构造问题明确，真实原始 grader 对照显示 no-op 失败于 Cannot instantiate，gold 通过唯一 case。该 case 含合法调用和三类非法参数保护，不能因 P2P=0 判成没有回归约束。不过题面明确关注返回值不能退化 Any、Union、完整 Car/Boat/Truck；这些没有被该 F2P 直接覆盖。另有两条具体待查线索：复用直接 TypedDict 构造检查的合理路线可能只因诊断措辞被拒；gold 复用的 callable 把可选字段也当必需，构造支持范围不完整。前者待合法实现对照，后者不是相对 base 已支持行为的回归。暂为 `needs_review / static_review`，用途 development_diagnostic。优先 CPU 只选 base/gold 的完整公开复现，以先界定 gold 是否满足实际题面。

| 方面 | 已查 / 未查 |
| --- | --- |
| 公开要求（3、23） | 已读完整问题、公开读者产物、TypedDict 文档/旧测试与调用路径。明确核心目标与 Boat 旁注的范围歧义；真实 CC 请求、public_hints 注入未捕获。 |
| 材料初态（1、2、27） | base `f19b5d3a026319687dd81a5c7c976698bbe948a8`，源码 1.10.0+dev、grader Python3.12；issue 的 0.910/Python3.9 是旧报告条件。S2 第210行三个对象与本题包相同，patch/validation及日志散列对应。N 初始工作树 clean 且真实目标调用报错；未逐字复现旧五条错误。 |
| 测试（18–20、25、32） | 唯一 F2P 全部断言、无诊断成功调用、collector、parser、临时文件、两份完整 fixture及其导入、整数组比较均已追踪。P2P=0；只执行1 item，不是整个 TypedDict 套件。 |
| 合理解（24、28） | 没有 helper 名或 gold 结构要求；但三类错误文本固定为普通 callable 文案，公开直接 TypedDict 构造同类错误文案不同，存在可区分误拒疑点。未运行替代解。 |
| 回归/gold（26、27） | 已读直接构造、字段类型、total=False、普通 Type/Union/NamedTuple旧行为及实现。gold 两行依赖已有 helper；直接构造路径不变。输入/返回/Union/Boat 覆盖限度与 total=False新支持缺口分开；未做广回归。 |
| 开发条件（6–15） | 已读 setup/pyproject、运行依赖、fixture、原始 install/test 日志及本题 image/build 原件。grader 支持不等于 actor；本题无新增外部资产、服务或必需编译。 |
| 交付/评分边界（4、16–17、21–22、29–31） | official restore 只针对 check-typeddict.test，gold checkexpr.py 被投影；test patch 无业务源码。runner/helper/config依赖已列，不证明任意候选不能操控；不新增排除规则。 |
| 关系/用途（5、29–30、37–40） | 不据同仓/文件判重复；未读其它题或未来历史。已暴露本题 private与环境 summary，不能作为 solver；真实 Git/镜像资产/模型能力未验。 |

## 要求与每个新增行为的双向映射

冻结 F2P：`mypy/test/testcheck.py::TypeCheckSuite::check-typeddict.test::testInitTypedDictFromType`。test.patch 只在该数据文件末尾加一 case，输入为 Point(TypedDict) 的 x/y 必需 int 字段，函数 `func(cls: Type[Point]) -> None`。函数不必在输入内被调用，mypy 会静态检查其已注解函数体。

| 要求/旧语义 | 公开依据 | 新 case / 保护状态 | 原始执行或缺口 |
| --- | --- | --- | --- |
| Type[TypedDict] 参数保持类型信息 | 题面 f/g、Car/Truck；types.py TypeType 表示 | main:8 reveal **cls本身** 为 `Type[TypedDict(...x:int,y:int)]`；覆盖参数类型，未覆盖调用结果 | N/G 该 note 正确。不能把它说成返回值类型断言。 |
| 合法间接关键字调用不报错 | 题面 Car/Truck.move(x=,y=) | main:9 `cls(x=1,y=2)` 无 E：完整输出数组隐式断言无诊断；覆盖 | N 报 Cannot instantiate；G case PASS。 |
| 拒绝两个位置参数 | 直接构造公开旧 testCannotCreateTypedDictInstanceWithUnknownArgumentPattern:47–50 | main:10 精确 E `Too many positional arguments`；有负向保护 | N 仅给 Cannot instantiate，G按预期。合法性有依据；文案与直接构造不一致。 |
| 拒绝缺必需字段 y | 旧 testCannotCreateTypedDictInstanceWithMissingItems:66–69 | main:11 E `Missing named argument "y"`；覆盖必需字段 | G通过；不含可选字段。 |
| 拒绝额外字段 | 旧 testCannotCreateTypedDictInstanceWithExtraItems:60–63 | main:12 E `Unexpected keyword argument "error"`；覆盖 | G通过；没有错误字段类型断言。 |
| 构造返回 D/PointDict，而非 Any | 题面最小 f 的 return、--warn-return-any、公开旧直接构造 reveal:3–42 | 新 case返回 None，调用结果丢弃，没启 warn-return-any；缺失 | 维持参数签名但把 callable.ret_type 改 Any 的部分实现，静态上可保留所有新断言，却违背明确目标；未运行，不称已证实满分。 |
| 空 TD、Type[Union[int,D]]传入int/D、成员保存调用与赋值 | 题面两短例、Car/Truck | case 不调用func(Point)、无empty/Union、赋值/成员路径；缺失直接验收 | gold可利用已有 normalization、subtypes、union-call实现，属源码支持而非实际原例执行。 |
| Boat 无注解条件表达式的返回类型 | 完整示例“No errors”；题面又称NamedTuple后object返回可能是另一bug | 无相应断言；缺失且范围有歧义 | checkexpr:5681–5688 非Union上下文走join，gold不改此层。不可凭F2P认定完整示例通过，也不可擅自删除Boat。 |
| 直接TD构造、字段值类型、total=False、普通Type/NamedTuple保留 | check-typeddict:3–98,1072–1125；check-classes:3381–3404,3472–3487,3524–3528,3568–3581 | 旧测试已读但不是P2P，也未执行 | gold未改直接构造/普通Instance路径。支持经Type构造非total TD的边界仍欠缺：helper949–955无required_keys判断。 |

逆向看隐藏约束：使用 Type 而非 type 拼写来自现有表示；输出强制大写由测试runner设置，不要求CLI逐字复刻旧版本。三种非法输入确实不应接受，因而“直接返回Any/全部关闭错误”**不能**通过该F2P（缺三条错误）。但精确选择普通callable诊断并非题面指定；旧直接TD检查同义诊断为 `Expected keyword arguments, {...}, or dict(...) in TypedDict constructor`、`Missing key "y" for TypedDict "Point"`、`Extra key ...`。保留这些旧文案的专用TD调用实现可能语义正确但被此精确数组拒绝，需实现级正对照核定，不能仅凭字符串不同立即认定误拒。

## runner、fixture 与真实执行

conftest.py:5 加载 data 插件；pyproject:90–114 禁默认类/函数收集，默认 `-nauto --strict-markers --strict-config`。testcheck.py:35–55 从 `check-*.test` 搜索；data.py:632–750 的 DataSuiteCollector **再经过 DataFileCollector** 产生 case Item，因此本版本精确ID含 `.test` 中间层，不能沿用旧版节点形状。case 无skip/xfail/增量标记。

data.py:106–117 把 `fixtures/typing-full.pyi` 与 `fixtures/tuple.pyi` 分别写作临时 typing/builtins；334–360建立tmp与文件。已读 tuple 全55行、typing-full全201行；后者声明 Type/TypedDict 特殊名称和 _TypedDict Mapping fallback，前者提供object/type/int/str/tuple等。导入的lib-stub/abc.pyi全9行与_typeshed.pyi全8行也已读；没有Mock、网络请求或业务数据。它们是真正的测试fixture，不能称“无fixture”。

data.py:215–229、527–553把N/E注释生成main:8、10、11、12整段期望。testcheck.py:100–195写main、parse_options、use_builtins_fixtures、nonincremental/cache=/dev/null，真正调用build.build，取errors/CompileError.messages；只有最后完整数组完全匹配才成功。helpers.py:107–139比较字符串，clean_up只规整路径/行尾，不能把直接TD诊断自动视为callable诊断。未启--update-data。原case无flags，helpers:354–364隐藏error codes且没有warn-return-any。fixture复制不是对项目业务实现的Mock。

## 实现调用链、不同路线及 gold 边界

具体TD名 `visit_name_expr` 路径使用typeddict_callable（checkexpr:383–387,925–947）；直接TD构造被visit_call_expr_inner单独分派至check_typeddict_call（488–500），检查required_keys、值类型及单dict输入（736–776,958–996）。经Type[T]调用则在check_call:1593–1595进入analyze_type_type_callee；base处理Any、Instance、Union、TypeVar、NamedTuple后对TD发unsupported_type_type并返回错误Any（1818–1860）。N日志四个Cannot instantiate正好证明此故障仍在指定base，不能把issue 0.910所有错误当当前初态。

gold加TypedDictType分支并复用typeddict_callable_from_context（949–956），以字段名/值类型为命名参数、返回callee本身；随后普通check_callable_call检查参数数量/类型并返回ret_type（1748–1792）。三类错误落到check_argument_count/extra_actual_arguments（2278–2401）与messages:948–1000。helper已在base，无遗漏依赖。Type[Union]先正规化为Union[Type]（types:2984–2999），check_union_call逐分支检查并合并结果（3210–3224）；Callable→Type兼容用返回类型（subtypes:724–726）。这些支持核心最小例/Car/Truck合理可修，不是完整复现执行证据。

不同于gold的合理核心路线是在Type[TD]调用分派处复用直接check_typeddict_call，然后保留Type/Union与返回类型信息；它能沿用直接构造的required_keys和字段检查。需要相同合法/非法语义，并处理其不同诊断文案。未写或运行候选。另一个具体错误候选是保留字段Callable签名但将返回类型设为Any，仍可产生三种预期调用错误却丢失返回精度；同样尚未运行。

gold完整性未知主要有：①Boat的非Union上下文join路径（checkexpr:5616–5690，join:396–422,705–733）未变，不能担保No errors；②helper把所有items都设ARG_NAMED，故经Type调用 `total=False` TD的缺省字段静态上仍会被当必需。公开文档typed_dict:123–131、旧直接构造testTypedDictConstructorWithTotalFalse明确允许缺省；这提示新增间接接口不完整，但base经Type本已不能实例化，**不是gold把既有可用间接构造改坏**。③直接TypedDict单dict参数是否应完全转移到间接Type调用未由issue单列；不擅自扩大成必需修全部TypedDict边界。

## 原始证据、配方与开发需求

S2 source_refs指定第210行的public/grading/validation与本题对象完全相同；test.patch/gold.patch与内嵌文本相同，gold散列a720daac…5050d。G/N原日志整文件SHA分别 `c913edffdc9bf122710f7680ce2f4e55228ae461e1a76e783dd89ac14a6e1af7`、`a33cd0a0cd51422cf2c3088a5e800ce2a9d45113b977f7e9f5c1b9142c49dace`，已核对run_refs/ledger。

两账本均E/<role>/ledger.jsonl:1，attempt1、grader rh2grader/54322、deny_all、2CPU/4GiB，candidate writable prefix为conda testbed。N日志132–136工作树clean/base精确；G132–141只有checkexpr变动，254–267是gold两行。G268–307/N250–289恢复官方check-typeddict.test再打补丁。投影仅gold checkexpr.py，无忽略；N空提交。故业务源码可交付，test patch无混合普通源码。runner_integrity_changed=false仅是这两个候选观测，不等于所有control面受保护。

G445–513/N427–495显示依赖与editable安装成功、RH2_INSTALL_RC=0，账本import_path=/testbed/mypy/__init__.py；内部模块来源仍非独立逐个观测。运行Python3.12.4/pytest7.4.2/xdist3.3.1。G518–539：`pytest -rA -k testInitTypedDictFromType`，11 workers [1 item]，目标PASS、RC0。N500–543：同selector，目标FAIL、四次Cannot instantiate和准确期望差异，RC1。两parser精确1 ID、missing/skipped/outside全空。真正有测试体诊断比较，不只是收集/解析标签。没有执行任何P2P或完整公开例。

E/image.json、build.log全读。base_digest与public一致；derived=`sha256:ab5d4a172a64f9969e2264af18f6389a7c688cad8e7cdfb417c96be961771add`与两账本一致。Dockerfile仅COPY预备wheels，设置PIP_NO_INDEX/PIP_FIND_LINKS；pins为setuptools68.2.2、wheel0.43.0、typing-extensions4.8.0、mypy-extensions1.0.0、tomli2.0.1、types-psutil5.9.5.17、types-setuptools68.2.0.0、packaging23.2。共享run_install_wave1.py:23–58直接replay_grade.py --derived-image，无其它波次的revised_install wrapper；未改expected/业务源码。build.log记录同ID。actor是否消费该派生镜像待验。

历史G/N安装5.182/5.787s、测试15.003/16.859s、峰值820.918/835.750MiB；11个worker来自默认-nauto而不是本题需要11CPU，当前未见OOM。可以建议公开开发用-n0，不能把改selector与参考运行当同一实测。只有一对运行，不证明稳定性或并发资源；cleanup账本removed=true，不是本次容器inspect。当前costs未知null。

| 操作/资产 | 公开依据 | 可确认与缺口 | 建议最小验证，未执行 |
| --- | --- | --- | --- |
| 本题源码与Python导入 | setup.py:221–234、version.py:11；公开例 | grader有Python3.12/工作区editable；actor激活/路径未知 | 实际agent shell打印sys.executable、mypy/checkexpr路径，再python -m mypy运行题面；不安装0.910代替base。 |
| 运行与构建依赖 | mypy-requirements1–4，pyproject1–16 | 已固定相关wheel、离线安装成功；actor可写prefix未知 | 如需安装，已有wheel与写权限应在准备完成；源码运行不必编译，MYPY_USE_MYPYC默认false（setup88–98,178–179）。 |
| fixtures/typeshed/临时写入 | 上述fixture、data334–360、题面typing/dataclasses | 本题无第三方业务资产、服务或GPU；运行角色实际读取待验 | agent运行公开`check-typeddict.test`窄case与原例，检查临时目录可写、使用正确typeshed；-n0。 |
| 交付与提示 | gold源码only；官方恢复仅.test | 核心修复不必修改测试；新增正常回归会受禁止改测试指令约束 | 真实messages/public_hints仍要核对。没有按测试文件名统一排除的现机制不能被旧提示“永不计分”替代。 |

## 唯一优先下一实验

在固定配方和精确base的独立诊断环境，分别检查base与gold；输入包括题面两个最小f/g例（补typing标准导入）以及完整Car/Boat/Truck代码，保持`--show-error-codes --warn-return-any`，记录各行诊断，勿把打印程序拿去Python运行代替mypy检查。原F2P/reward保持独立记录。

结果判别：若gold通过冻结F2P且f/g、Car/Truck干净，但Boat仍返回Any/object或出错，则证实完整“No errors”要求与当前参考支持范围不齐；应先界定Boat是否属于本题并保留原版，不能静默删例。若gold完整例都无错，则撤回这条gold完整性疑点，仍保留返回值漏测与诊断路线问题等待后续按风险验证。若base某些旧报错已不存在，按指定base实际症状描述，不能把0.910日志当本题起点。安装/导入问题另归环境，不能冒充语义反例。

优先这一步是因为不需要先猜一个新补丁就能检验最强公开承诺；本轮不强制生成两份补丁。返回Any的部分实现、直接TD诊断路线以及total=False边界都是单独保留的静态线索，不借此宣告已实测误收/误拒或gold回归。

## 阅读、暴露与边界

已读本题封存public_read、public bundle/base_identity/user_prompt/environment_brief，全部私有bundle/test/gold/refs/environment_record，source_refs仅指定210行，两份原始ledger、日志的初态/补丁/安装/执行/退出关键范围、image.json/build.log全件。environment_record的verified_environment_pair标签/checks已暴露；未沿analysis/history链接。共用方法同角色许可，共享run_install源码只读23–58行。仅复用runner版本知识，不以前题结论作为本题证据。

源码阅读为本文逐节列出的checkexpr/subtypes/types/join、runner/helper/config、两fixture及导入stub、TypedDict与Type相关旧测试、docs/setup/pyproject/requirements/version片段；不宣称读完整仓库或所有测试。未读本题history、旧质量报告、manifest、主计划、method_adjustments、其它角色结论、其它题资料、未来Git或任何模型轨迹。未进行项目执行、变更原题/评分参考或修改他人产物。
