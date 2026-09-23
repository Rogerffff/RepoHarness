# pandas-dev__pandas-53958：历史开放前分析

2026-09-21，B2私有主审。ROOT=`${REPO_ROOT}`，下列路径均相对此ROOT。本稿仅静态读本题公开/私有原件、精确S2行、run_refs所指原始账本/日志及本题public_read；未读本题历史、reviewer、其它题内容或批次质量聚合。未执行pandas、pytest、安装、容器、网络或模型；未改源码、测试、gold、参考或reward。共用方法与当前RH2代码知识可复用，不把前题结论当本题证据。

## 1. 公开要求与版本

base=`1186ee0080a43a08c3431a5bfa86898f6ec3b54d`，tree=`0fe5a870217e5ac80b2cc5508a40b2b9f4afa85d`；S2 public/grading/validation各精确第155行，version2.1，vendor=`swegym_constants_242429c1`。公开镜像digest=`sha256:b45817ed11542705d541028f48e9ce8026e783feb14440454141fc6d8129df21`。沿已完成整包身份/blob核验，不另机械逐blob比对。

Issue目标是让应用类型注解能够从一致位置取得已有 `NaTType`、`NAType`。题面明确展示现有 `_libs.NaTType`、`_libs.missing.NAType`，然后以问句提出向 `_libs` 增加NAType，并说另一选项是把两者放到 `pandas.api.typing`，请求维护者意见。当前公开材料没有最终选择。`doc/source/reference/index.rst:21–25` 说明typing是公共类型注解入口，支持该方案的适宜性，但不能抹去题面明确保留的 `_libs` 方案。

合理共同契约：新导出应是现有真正的类型对象，能表达 `pd.NaT`/`pd.NA`，保留原来可工作的进口及单例行为；无需移动Cython定义、修改业务运算或强制外部pandas-stubs/checker版本。公开调用者 `_typing.py:31–43,378–380` 使用NaTType联合类型，`core/dtypes/cast.py:24–28,173` 用NAType作类型注解；这说明不是只需要两个字符串名称。

初态源码的确只在旧位置导出两类：`_libs/__init__.py` 含NaTType而无NAType，`api/typing/__init__.py` 两者皆无。`missing.pyx:366–407,543–544` 定义NAType及其单例；`tslibs/nattype.pyx:359–376,1417–1418` 定义NaTType及NaT。配套pyi声明也一致。历史noop的官方断言报typing名称16对18、缺这两个名称；这证明该特定命名空间目标未实现，不单独证明题面已选择该目标。

## 2. 全部新增/修改断言及F2P

官方test.patch仅向 `pandas/tests/api/test_api.py::TestApi.allowed_typing` 加 `"NaTType"`、`"NAType"`，未新增测试函数。唯一F2P为 `TestApi::test_api_typing`：调用 `Base.check(api_typing, allowed_typing)`；该helper取 `dir(namespace)`，去掉以 `__` 开头的名字及`annotations`，排序后与18个字符串精确相等。`tm.assert_almost_equal` 对list走Cython序列比较，最终字符串比较精确；其check_dtype检查的是传入列表/数组类型，不检查导出对象的类型。无Mock、参数fixture或远程资产。

| 需求/旧行为 | 公开依据 | 对应断言 | 覆盖判断 |
| --- | --- | --- | --- |
| 两个类型能从共同入口导入 | issue同时提供 `_libs` / `api.typing` 两候选 | 唯一F2P只允许typing的18个名字 | 只覆盖其中一个明确候选；合理 `_libs` 单独补导出预计被拒，是具体规格—验收疑点。 |
| typing方案实际提供NaTType/NAType | typing文档及模块现有导出约定 | F2P验证 `dir()` 名称 | 名称覆盖；不读取对应属性对象，不做from-import/类型身份/类型注解有效性验证。 |
| 导出的是真正的类、指向现有类型 | pyx/pyi、公开现有导入及类型注解调用者 | 新断言及10 P2P都不比较 `NAType is type(pd.NA)` / `NaTType is type(pd.NaT)` | 具体漏测：误导出同名singleton值等仍可能满足名称表；这是静态推断，尚无候选实际评分。 |
| 新公共导出遵守 `__all__` | 现有typing模块完整__all__约定 | F2P过滤所有双下划线名；P2P的__all__仅检查顶层pd | typing.__all__未测；只补import未同步名单的自然部分实现可能通过。不要把这一点与类身份问题合并成已证假阳性。 |
| 原有API名称和顶层__all__保留 | 公开完整api测试模块 | 全部10 P2P，见下表 | 保护命名空间形状，不等于验证所有导出行为或缺失值运算。 |

精确名称要求本身符合已有API边界测试；没有要求某内部导入路径或helper名。若公开明确选typing，直接从定义模块或中间包重导出同一类型都合理，gold不是唯一写法。问题在于目标命名空间选择未公开定论，而不在“精确字符串测试一律有错”。

## 3. 执行集合、冻结参考、实际阅读

两run实际命令均为 `pytest -rA --tb=long pandas/tests/api/test_api.py`，收集11项；冻结参考恰为1 F2P+10 P2P，无参数化ID、missing或skipped。实际完整读 `test_api.py`（全部名单、helper及11方法），所以本题评分测试体已全覆盖阅读；另读相关类型定义/调用者/旧标量测试，但未执行。

| 全部P2P ID（均在test_api.py） | 实际行为/局限 |
| --- | --- |
| `TestPDApi::test_api` | 合并公开/私有包、类、函数、模块的名单，忽略tests/locale/conftest/_version_meson；与顶层pd的dir比较。 |
| `TestPDApi::test_api_all` | 顶层pd.__all__与既有公开名单双向差集都为空；不检查typing.__all__。 |
| `TestPDApi::test_depr` | 遍历三个deprecated列表并期望FutureWarning；此base三列表均空，实际为零次循环，不能记作弃用行为已测。 |
| `TestApi::test_api` | pandas.api只能有types/extensions/indexers/interchange/typing五类子入口。 |
| `TestApi::test_api_types` | 精确检查dtype/类型工具名称列表。 |
| `TestApi::test_api_interchange` | 名称为from_dataframe、DataFrame。 |
| `TestApi::test_api_indexers` | check_array_indexer及三种Indexer类名。 |
| `TestApi::test_api_extensions` | 扩展dtype/访问器注册/EA等名称。 |
| `TestTesting::test_testing` | pandas.testing四种assert_*函数名称。 |
| `TestTesting::test_util_in_top_level` | pd.util.foo必须抛AttributeError且含foo；已读util.__getattr__调用者，未定义名确实抛错。 |

这些测试没有显式fixture；全局autouse `configure_tests` 仅把chained_assignment设为raise。conftest、直接依赖和API import路径已读。额外旧行为参考 `test_na_scalar.py` 的singleton/布尔异常及 `test_nat.py::test_identity` 的3构造类×9缺失输入，实际读其参数和断言；它们不在本次执行/冻结参考集合，不能填作本次已通过回归。未以10 P2P这个数量判断强弱。

## 4. Gold、合理替代、自然部分实现

Gold仅改 `pandas/api/typing/__init__.py`：从已有 `_libs` 与missing导入两个真类，并加入本模块__all__。旧定义/入口/单例都保留，无新依赖或额外提交文件。pandas顶层在加载core后再导入api，所读导入链未发现新增循环；历史gold全11项通过支持其运行可行。它完整实现题面的typing方案，不实现 `_libs` 另一提议，不能因gold选择就宣布公开选择唯一。

具体合理替代是只在 `_libs/__init__.py` 现有依赖初始化后重导出真实NAType，并同步该包__all__，保留NaTType及原missing入口。它满足题面第一提议；typing名单不变，官方F2P预计仍报缺两名。该替代尚未构造/执行，需同时核进口身份和评分，不能仅由“不同于gold”判错。

自然部分实现有两类：只补typing两个正确import但漏__all__；或把 `NaT` / `NA` singleton误当成 `NaTType` / `NAType` 导出。后者明显不满足类型注解目的，但dir与本套P2P可能不区分。它们不是已运行攻击，也不是要求全仓完备测试；是可直接追到新增断言观察量的特定缺口。没有改测试/helper、伪造stdout或硬编码测试名的必要。

## 5. 原始环境与已有RH2证据

只从 `run_refs.json` 精确提取baseline01/w06-2 ledger **第11行noop、第12行gold**，不读相邻任务。两者均本题ID。`environment_record.json` 作为入口使用，未打开其跨题汇总引用。

| 条件/原件 | 已有事实 |
| --- | --- |
| 原镜像/身份 | 账本记录公开digest identity，derived_image_recipe=null、image_local_build=false；image_id_actual=null，不虚填观察到的Docker ID。grader为rh2grader/54322、deny_all、2CPU/4GiB、PID512、tmp1GiB、shm64MiB、可写conda前缀。 |
| 安装真实路径 | 原日志中 `python -m pip install 'numpy<2'` 已满足NumPy1.26.4，接 `pip install -ve . --no-build-isolation -Ceditable-verbose=true`，Meson1.0.1 reconfigure现有build/cp310，gcc13.3/Cython0.29.33/ninja1.12.1，仅生成version文件；editable wheel成功安装。这不是从零完整编译耗时证明。 |
| 元数据告警边界 | 两run安装段均有xarray2024.9.0要求pandas>=2.1而当前dev版本不匹配的resolver ERROR文本；之后Successfully installed、安装rc0，实际测试能启动。没有pip check全环境健康证明，也不能把该安装段文本当目标测试失败或整体安装失败。 |
| noop日志 `...a8d9ae3e.eval.log` | 1488恢复official文件、1513–1525自证成功；3031源码安装完成，3036安装rc0；3059收集11；3189附近报名称16对18、缺NAType/NaTType；3204–3214为10通过1失败，3215摘要，3219 test_rc1。账本安装9.152s/test4.616s，F2P0/1、P2P10/10、reward0。 |
| gold日志 `...eed61475.eval.log` | 官方恢复/应用成功；3059安装完成、3064 rc0；3087收集11、3097–3107全11 PASSED、3108摘要、3112 test_rc0。账本安装8.073s/test4.535s，F2P1/1、P2P10/10、reward1。投影仅typing/__init__.py，工作区导入为 `/testbed/pandas/__init__.py`、版本 `2.1.0.dev0+1120.g1186ee0080.dirty`。 |
| parser/清理 | 两侧num_parsed_tests=11、missing/skipped空、日志非partial、cleanup.removed=true。段外1个可解析项来自安装段ERROR前缀，与当前只取Start/End测试段的规则分开。未见参考ID映射修复需求或全局收集故障。 |

这是历史真实grader对照，不是本次CPU重跑；0/1证实当前oracle接受gold，不消除公开方案分歧或对象身份漏测。`apply_user=agent/54321`仅应用候选，不是actor开发。当前公共actor与grader即便镜像digest相同，身份、权限、激活和消息仍不同；未证明actor可写系统prefix或Meson增量build路径。

## 6. 开发需求与真实actor缺口

| 需要的操作/资产 | 公开依据 | 范围与建议的最小验证（均未执行） |
| --- | --- | --- |
| 定位并修改导出 | 题面旧import及两个候选、两个__init__.py、类型定义/pyi | 可纯Python重导出，不需修改Cython定义。普通源代码路径可提交。 |
| 正确解释器/工作区构建 | pyproject Python>=3.9与依赖；pandas/__init__依赖/扩展检查 | actor打印id/cwd/sys.executable/pd.__file__/version，再导入两个原类；应对应/testbed，不以conda名称替代导入来源。 |
| 真实类型身份 | pyx单例构造、pyi和现有注解 | 在选择的共同入口验证 `NaTType is type(pd.NaT)`、`NAType is type(pd.NA)`；保留旧入口检查。若只选一个题面方案，不同时强加两个入口成功。 |
| 窄公开验证 | test_api helper/名单、scalar旧测试 | 原未改API名单会拒绝正常新增typing名称；禁改测试若适用，可先用直接import/身份脚本验证，再运行旧scalar singleton/identity。官方评分会恢复并应用新名单，源码交付无需修改被保护测试。 |
| 构建/安装 | pyproject meson-python0.13.1、meson1.0.1、Cython>=0.29.33,<3、wheel、NumPy；历史editable日志 | 历史用既有build增量工作；actor本地扩展、loader触发的ninja、build目录/前缀权限待验。依赖应准备期固定，解题/安装/测试不假定公网。 |
| 外部资产与资源 | 基本需求只有两个本地类 | 无GPU、远程服务、数据、附件需求；pandas-stubs仅为动机，题面没规定实际checker端到端验收。默认资源不是actor实测，grade峰值不能替代。 |

禁改测试hints的适用消息仍待查，但不造成“源码解一定不可提交”：官方只恢复 `pandas/tests/api/test_api.py` 并加两名字，gold历史通过已经展示纯源码解路径。应提醒这是公开旧测试与新API需求的正常局部不一致，不建议隐藏dir或伪造检查，也不自行授权solver改被禁测试。

## 7. 交付、评分、关系与用途

当前 `prepared_task_face.build_grading_spec_from_host_view` 使用官方patch精确路径、`test_globs=()`；本题恢复/保护只有 `pandas/tests/api/test_api.py`，纯源码的typing或_libs路线都不被该恢复覆盖。源代码交付没发现需要附加排除，`additional_exclusions=[]`。test.patch纯测试列表，不含实现。

当前scoring/parser/manager通用代码已定点读过：正常完整pytest rc1不是独立reward归零门；缺参考计失败，段外状态不用于评分，零解析/全部缺席/全局故障另判。本题命名空间选择失败直接是唯一F2P失败，不需要依赖全套pytest退出码猜reward。共享stdout可伪状态控制面未做本题攻击实验；本题名称值漏测属于正常oracle观察不足，不与parser注入混为一谈。

未读取其它题，不按相同包归重复；没有来源于另题base/修复的关系证据。当前base导出不含.git和镜像全部资产，不证明实际可见材料绝无未来答案；公开issue只给旧import和两方案，没有本题gold文本。审查已暴露隐藏测试/gold，未来历史暴露另记；只能用于development_diagnostic，不给盲解solver，不当正式训练/评测批准。

## 8. 暂定处置与唯一优先下一步

`needs_review / static_review`，原因是明确的公开选项—单一路径验收争议，加上只测名称的对象身份漏测；不是环境执行失败，也不是因题简单或P2P少而拒绝。Gold可行、原oracle已有历史成功，不足以消除这两项质量限制。是否补公开设计决定或修订断言需要独立复核与版本记录，本轮不改题。

**唯一优先下一步：在固定且已能评分的grader条件中，对题面直接支持的 `_libs` 单独重导出方案作一个定点CPU对照：先检查两旧/新共同入口的真实类型身份与单例兼容，再运行原官方测试、取实际RH2分数。** 预期共同 `_libs` 进口正确但typing F2P不通过；若实证成立，能区分公开合法方案与隐藏选择的误拒，而非拿gold差异作标准。保留对象身份漏测作为独立待修/待验证问题，但不为这一步额外扩大成全仓或强制两套补丁。此oracle语义对照不要求先启用付费模型；正式actor启用前仍需独立验证上表条件，二者不互代。

## 9. 实际阅读范围

完整读取本题 public_bundle/user_prompt/environment_brief/base_identity、private grading/validation/test.patch/gold.patch/source_refs/run_refs/environment_record、本题public_read；S2仅第155行。完整读取base `pandas/tests/api/test_api.py`（全文）、`api/typing/__init__.py`、`api/__init__.py`、`_libs/__init__.py`、`_libs/tslibs/__init__.py`、`_libs/missing.pyi`、`util/__init__.py`。

定点读base：`missing.pyx:1–70,360–430,534–548`，`nattype.pyx:350–406,1408–1426`、`nattype.pyi:1–48`，`pandas/__init__.py:1–159`、`core/api.py:1–45`、`_typing.py:23–52,368–387`、`core/dtypes/cast.py:12–38,165–189`；`_testing/asserters.py:51–147,345–388`、`_libs/testing.pyx:35–171`；`test_na_scalar.py:1–151`、`test_nat.py:1–112`；conftest1–142与200–284，pyproject1–64与454–513，reference/index.rst1–35。未沿已读但无关的标量算术fixture继续全量展开，不声称其回归已验证。api目录无局部conftest（定向文件名检索）。

运行原件只读w06-2 ledger11/12与各自eval日志的安装、可信恢复、收集、完整11状态/失败、终态；没有从该多题账本读相邻记录。日志打印的git show片段是本题运行原件的一部分，未据无关片段推断题间关系。实际未读全量激活脚本/构建输出，未审共享全部安全边界。

本稿保存后报SHA暂停，待协调者封存并开放本题历史。
