# pandas-dev__pandas-51605：读历史前的私有独立初稿

2026-09-21；`needs_review / static_review`；仅 `development_diagnostic`。本稿在读本题旧单题记录前保存，封存后不回写。权威根目录 `.`，默认 worktree 未作证据源。

**暂定判断：隐藏断言与空列表目标相符，真实原评分可解释；gold 却引入未保护的无长度 iterator 回归，并没有修复 empty iterator，宜先作窄 CPU 语义对照。** 这是源码推导，尚未运行反例；历史 gold 13项通过不等于完整修复。新增测试使用2行索引，没有逐字覆盖公开3行例子；固定2个False的错误实现有具体漏测空间。保留合理替代实现，不以gold为唯一答案。

## 证据、暴露与原件映射

P=`runs/swegym_quality_batch03_20260921_v1/public/pandas-dev__pandas-51605`，Q=同根 `private/pandas-dev__pandas-51605`，B=`runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01`，W=`B/workers/w06-1`。本题 N=`W/eval_logs/evallog_replay-f216-baseline01-w_f5f8cb43.eval.log`，G=`W/eval_logs/evallog_replay-f216-baseline01-w_bff5d554.eval.log`。所有路径相对权威根。

已读指定四个方法文件、本题公开材料/自己的public_read、Q七原件；inventory仅common、families.baseline01和tasks本题项；精确原jobs第11/12项、events第21-24行、ledger第11/12行、两log/diagnostics、prepared本题项/host第154行，及明确指向的campaign/worker和归档harness调用链。**Q/environment_record.json内自带noop0/gold1摘要，初稿前已见，已披露。** 未追其scope_reconciliation聚合，未读旧单题、reviewer、其它题结论、B3assignments/聚合；公开初读来自另一新上下文，本主审不是公开盲读者。共享harness版本知识只作为共用代码知识，本题运行结论均重新取本题原件。

| 原件 | 对应断言/核查 |
| --- | --- |
| P/public_bundle、user_prompt、base_identity | base=`b070d87f118709f7493dfd065a17ed506c93b59a`，tree=`a3d714b05bc870106b35b3bff6f00d7c551b7460`；公开目标3个False。无.git/gitlink/LFS缺件是导出记录，不证明实际镜像资产。 |
| Q/source_refs.json | 原public/grading/validation jsonl第154行，raw SHA分别`3bbfbbc2…`、`1697e233…`、`1523dde7…`与索引相符；三对象与导出一致，未打印其它题行。 |
| Q/grading.json、test.patch | base对应，版本2.1；F2P1/P2P12；新增一个测试函数，无生产源码/Mock；eval_cmd=`pytest -rA --tb=long`。 |
| Q/gold.patch、validation.json | 只改multi.py加两行；SHA=`3e268d05a6a97e89e8b031091642842ca0a7ac6768a6e04bde63b7be5b179f22`与原ledger第12行候选一致。 |
| Q/environment_record、run_refs | 摘要非重新认证；按ledger第11/12行与原log/diagnostics核初态、候选、实际测试、评分、资源/清理。两log和ledger文件/单行SHA都与run_refs一致。 |
| prepared manifest本题项、host_grading第154行 | instance/source/environment digest与库存一致；host row SHA=`812146b5a069c4dc64874ee4a50a5baa32cca5179ee74318f707375cfadc88e7`，grading对象与Q相等。原/work路径在本机不存在，未来重定位另建副本，本轮未动。 |
| B/config.json + campaign.py/worker.py | 当前明确引用脚本SHA与原config记录逐一相等；campaign `37e3fb31…`、worker `b5584d52…`。这两个实验外壳不在baseline.tar.gz；其内部harness使用归档字节，不能拿当前生产harness冒充。 |

## 1. 公开需求与初始问题

题面报告1.5.x返回 `[False False False]`、2.0.x抛`TypeError: Cannot infer number of levels from empty list`。历史版本说法未另复验，但给定base的直接路径及真实noop均成立。题面末句“an Index consisting of False”是用词不准；公开`Index.isin`文档 `base.py:6182-6201` 明确返回 `np.ndarray[bool]`、长度等于self，MultiIndex通过`@doc(Index.isin)`继承。旧公开测试亦断言 ndarray/bool，不能据末句要求改返回Index。

base `multi.py:3749-3753` 在level=None、values非MultiIndex时调用`MultiIndex.from_tuples(values)`；names_compat装饰器`196-212`只兼容name/names关键字。构造器`559-563`验证list-like、将iterator转list，`578-580`发现空列表且无names便抛题面异常。原N:4720-4829完整栈为`test_isin_empty:93`→`isin:3752`→names_compat:210→from_tuples:580；N:1438-1441是clean/base commit。故不是导入/收集失败，也不是材料已修。公开原例是3行，历史新增F2P用2行，路径相同但并非执行过原字面样例。

values声明`set or list-like`（base.py:6192），`lib.pyx:1099-1160`明定字符串/bytes不是list-like，而具有`__iter__`的iterator属于接受范围；`is_iterator:261-291`用PyIter_Check。`from_tuples`旧公开`test_from_tuples_iterator:367-375`专测zip。由标题empty iterable、接口和已有归一化可合理要求空iterator正确，并保持非空iterator旧路径。不推断任意异常自定义容器也必须成功。

harness操作指令（只改非测试、禁改测试）与issue输出要求、conda激活声明分开；实际消息/CLI/system/tool和禁改测试本次适用待验，不自动忽略。业务Python源可表达修复，未发现必须改测试才能做题。公开bundle字段未进入user_prompt不等于不可见。

## 2. test.patch、helper与全部F2P/P2P

本题唯一hunk追加：构造`MultiIndex.from_arrays([[1,2],[3,4]])`（两个元组(1,3)/(2,4)），调用`midx.isin([])`，expected=`np.array([False,False])`，再`tm.assert_numpy_array_equal(result, expected)`。F2P完整nodeid与冻结键都为`pandas/tests/indexes/multi/test_isin.py::test_isin_empty`。无参数化、Mock、文件/内部实现断言。

helper已展开：`pandas/_testing/asserters.py:598-675`默认check_dtype=True，先`assert_class_equal`及`_check_isinstance(...,np.ndarray)`，再`array_equivalent`检查shape/value，最后`assert_attr_equal('dtype')`；class/helper分别在144-169、342-412；`core/dtypes/missing.py:455-542`对bool数组最终比较shape和np.array_equal。故不是宽松的“真假值可转换即可”：list、pandas Index、整数0数组、错误长度均拒绝。check_same默认None，没有强制内存别名/拷贝。输出类型/长度/布尔值均有公开接口依据，未发现此新增测试误拒合理实现。

12个P2P完整逐项如下（前缀都为`pandas/tests/indexes/multi/test_isin.py::`）：

| P2P节点 | 具体输入/调用及决定性断言 | 依据/覆盖 |
| --- | --- | --- |
| test_isin_nan | self=[('foo',1),('bar',nan)]；values=[('bar',np.nan)]和float('nan')两调用 | 两次ndarray[False,True]；保留缺失值匹配。 |
| test_isin_missing[NoneType] | `nulls_fixture=None`；候选MI=[(1,None)]，self=[(1,1),(1,2)] | ndarray[False,False]。 |
| test_isin_missing[float0] | fixture=np.nan，同上 | 同上，候选MultiIndex路径。 |
| test_isin_missing[NaTType] | fixture=pd.NaT，同上 | 同上。 |
| test_isin_missing[float1] | fixture=float('nan')，同上 | 同上；两个float参数有不同pytest后缀。 |
| test_isin_missing[NAType] | fixture=pd.NA，同上 | 同上。 |
| test_isin_missing[Decimal] | fixture=Decimal('NaN')，同上 | 同上。 |
| test_isin | self=[('qux',0),('baz',1),('foo',2),('bar',3)]；values=[('foo',2),('bar',3),('quux',4)] | ndarray[False,False,True,True]；另empty self+同一非空values断言长度0、dtype bool。 |
| test_isin_level_kwarg | vals0=['foo','bar','quux']、vals1=[2,3,10]；0/-2及1/-1定位对应level | 四次正确mask；level5/-5抛明确IndexError；1.0/-1.0/'A'抛KeyError；重命名A/B后正确mask，C仍KeyError。 |
| test_isin_multi_index_with_missing_value[labels0-expected0-None] | self由[[nan,'a','b'],['c','d',nan]]构造；values=[('b',nan)] | ndarray[False,False,True]。 |
| 同函数[labels1-expected1-0] | 同self，values=[nan,'a']、level0 | ndarray[True,True,False]。 |
| 同函数[labels2-expected2-1] | 同self，values=['d',nan]、level1 | ndarray[False,True,True]。 |

`test_isin.py:1-87`已全文读。fixture来自本题`pandas/conftest.py:369-374`，`tm.NULL_OBJECTS`在`_testing/__init__.py:181`展开为上述六值，ids用type名称；没有神秘第七值。局部multi/conftest.py亦全文读，新增F2P不引用其中idx等fixture。顶层conftest导入hypothesis/dateutil/pytz；collection hook片段只增doctest或arraymanager标记，没有替换这些调用。pyproject:388-420有strict配置、JUnit与warning规则；本次实际13项没有skip/xfail。

## 3. 双向映射、覆盖缺口与合理替代

| 公开要求/合理旧行为 | 依据 | 对应测试与覆盖状态 | 现有证据或未来验证（未执行） |
| --- | --- | --- | --- |
| 空list不抛异常并返回self等长全False bool数组 | issue原例；Index.isin文档6184-6201 | 唯一F2P严格验证2行数组，覆盖核心路径；原3行/空self缺失 | N实际同路径TypeError，G实际两False通过；未来补公开原3行。 |
| 常规空set/list-like，包括无长度iterator | 标题empty iterable；values合同；from_tuples559-563、lib.pyx1142-1159 | 只覆盖[]，tuple/set/ndarray/Index/iterator未测 | gold对有len的空容器可静态推导成功；空iterator仍先len报错，未实测。 |
| 非空iterator原匹配行为 | 构造器is_iterator→list；公开zip构造测试367-375 | 12P2P均没有iterator；**缺失且gold有静态回归** | 未来midx.isin(iter([(1,3)]))应[True,False]；base路径支持、gold先len报TypeError，待CPU证实。 |
| 只接受list-like，拒绝空str/bytes | 公共values类型；lib.pyx1153-1155；from_tuples559-560 | 无invalid-values P2P，gold shortcut绕过验证 | 未来 `midx.isin('')`/`b''`应保留非list-like拒绝；gold静态将返回全False。 |
| 普通匹配、缺失值、候选MultiIndex | 上述公开test_isin1-37、75-87 | 11个相关P2P节点（排除level_kwarg；其中部分有level参数）均实际通过 | 不代表iterator或非法类型已覆盖。 |
| level选择/错误不能被空值shortcut绕过 | MultiIndex._get_level_number1478-1503；test_isin40-72；通用test_base889-903 | 非空level矩阵已测；empty values+非法level不在该题P2P | gold只在level=None加分支，静态未绕过原level检查；未来窄保护，不指控不存在的gold回归。 |
| from_tuples([])无names仍应报原错，有names可空构造 | test_constructors353-356、383-387 | 本题评分命令未运行构造器模块 | gold不改构造器，无此实质回归证据；替代方案须保留该合同。 |
| caller依赖一维bool mask | NDFrame._drop_axis generic.py4582-4615 | 未在本题评分命令覆盖 | 已读反转mask/nonzero调用，不声称drop路径已复现或通过。 |

合理非gold路径可以在正确验证/归一化iterator后处理空集合，或只在isin内部为`from_tuples`提供self层数所需names后继续现有匹配；公开接口不规定`len(values)`/`np.zeros`/分支位置。需保持非法level及原构造器直接调用合同。未制作候选，不提前断言所有细节或性能皆正确。当前唯一隐藏新增断言及旧P2P只核外部行为，没有排斥这类合理路线的具体依据。

具体漏测反例与泛称“单样例太弱”分开：未来错误候选若仅在level=None且values为[]时固定返回2个False，再走原其它分支，F2P的2行用例满足，12P2P没有空候选，不会触发该错误分支；但**公开题面的3行输入**必须返回3个False，这条明确合同会被违反。此为可区分的静态候选方案，尚未运行，不能写已获得reward1。无条件全False则会被test_isin/NaN/level等正匹配P2P拒绝。

## 4. gold审查

gold在`if level is None`内，原`isinstance(values,MultiIndex)`/from_tuples调用前，加`if len(values)==0: return np.zeros((len(self),), dtype=np.bool_)`。NumPy在原文件已有依赖，原level空self分支也使用np.zeros，无新包/资产/编译源变更；投影仅multi.py。

对公开[]原例，长度取len(self)、dtype bool，静态满足3行目标，真实F2P二行通过；empty self+[]也推导为0长bool。有len的非空旧输入沿原路径，13官方项全过。但直接len阻止iterator进入原`from_tuples`的list归一化，**非空iterator旧行为回归**，empty iterator也漏修；还会让非list-like空str/bytes在构造器检查前直接返回数组。这两个问题由调用顺序、旧验证代码及Python对象协议直接推出，本轮没有项目执行；不得标成已完成CPU反例。不能因为gold历史reward1就将新len要求升级为公开values必须Sized的合同。

## 5. 原运行来源、收集/节点/键/参考/退出码

原入口不是reference wrapper，也不是声称baseline直接执行replay CLI：`rh2/experiments/full216_diagnostic_20260919/campaign.py:145-154,187-200`生成jobs并启动worker；worker:65-83读取prepared/default profiles，`qualifications={}`、默认ReplayBudgets；worker:94-107用本题job调用`ReplayGrader.replay_one`。这两个文件SHA分别为`37e3fb31733278dbe80970706f5615a9f158442a78dcd4c94e97f51cc9bbebce`、`b5584d5266515ecb64cdb4d46715de0a1696d80c80b4ef575ed2c8b347046207`，与B/config.json的diagnostic_code_sha256相等。

`B/jobs/w06-1.json`只选索引10/11本题noop和gold-dir；`W/events.jsonl:21-24`记录本题start/finish，未打印或使用其它job。内部harness字节来自`runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz`，只用tarfile.extractfile读相关成员、不解包/导入/执行。归档ReplayGrader:177-201/424-438载入prepared并构spec；prepared_task_face:298-333使用原parser/官方文件恢复。归档`spec_vendor`2.1配方安装与测试命令从vendor JSON读出；归档scripts/replay_grade.py可作以后单题入口说明，但不替代原campaign→worker事实。

| 指标 | noop（ledger第11行/N） | gold（ledger第12行/G） |
| --- | --- | --- |
| 实际命令 | N:4708 `pytest -rA --tb=long pandas/tests/indexes/multi/test_isin.py` | G:4726 同一命令 |
| 收集/实际结果 | N:4715收集13；N:4836-4849十二旧PASSED、新FAILED | G:4733收集13；G:4743-4756全部13PASSED |
| 原始完整node/解析键 | 13个完整摘要node，没有空格截断碰撞；去状态/失败尾消息后与冻结13键集合相等 | 同左；原parser的空白split不会截本题node名 |
| 冻结参考 | F2P0/1，P2P12/12；missing/skipped=[] | F2P1/1，P2P12/12；missing/skipped=[] |
| 普通pytest退出码 | N:4857 rc1 | G:4764 rc0 |
| RH2结论 | unresolved/reward0 | resolved/reward1 |
| 安装 | 693.328秒，实际built+installed N:4680-4693；末命令rc0 | 719.751秒，built+installed G:4698-4711；末命令rc0 |
| 测试记录时间 | 5.790秒；pytest自身0.42秒 | 4.552秒；pytest自身0.12秒 |
| 资源/清理 | 2CPU/4GiB/PID512/tmp1GiB/shm64MiB，峰值1081.07MB，resource_facts=null；candidate cleanup removed=true | 同policy，峰值840.5MB、resource_facts=null；candidate cleanup removed=true |

harness `swegym_parsers.py:44-56`从标记段摘要构键；`scoring.py:250-269,291-309`从F2P/P2P桶算reward。`prepared_task_face:147-156`保存pytest rc为诊断，不是直接reward。这五层恰为13/13/13/(1+12)/0或1，不能以收集13独自证明执行，也不能由rc一般推出reward；本题另读了真实失败栈/全部摘要。

两log SHA分别`6ee0ffdfdb152cab009277b0377b16c59dbd444e87816906d15691ef5089f460`、`4509f3f18c8e18a24f6497cb88e7ab14070dc6ea5df8150423ff726c1c35f059`；W/ledger文件SHA=`542f212417495efbacfa8f8e9e9281a6f068711c9bf86819d1a9ed4e535500bf`。环境摘要所称原noop/gold结果在这些材料下确认，不代表新质量/稳定性认证。

## 6. agent开发条件与交付/评分边界

历史conda Python3.8.20、pytest8.3.3、NumPy1.24.4，package path观测为`/testbed/pandas/__init__.py`、版本`2.1.0.dev0+44.gb070d87f11.dirty`。vendor2.1 install串依次为numpy<2、editable安装、不存在也可成功的pytest-qt卸载；last-command rc0不证明前面成功，本次另读了wheel/installed输出。N:2979-2981/G:2997-2999的numpy已满足，grader deny_all下成功，不需要假定运行期公网；pre_install git fetch是准备配方，不在这次candidate安装串。业务修复为纯Python，已能从源码导入的actor通常无需为这两行重编Cython，但pandas本体仍需要已构建扩展。

实际grader为rh2grader/54322、可写conda prefix；apply用户agent/54321只证明补丁应用身份，**不是正式actor CLI/工具验证**。镜像tag=`xingyaoww/sweb.eval.x86_64.pandas-dev_s_pandas-51605:latest`，预期manifest=`sha256:030bdab9144f93f67be2152375db00d2d8de10afbcfec2ddf509a8ff9cb5eccd`；两ledger `image_id_actual=null`、无派生recipe、env_qualification=absent。当前镜像/路径可用性未知。candidate清理字段明确成功，但未读取worker最终全局关闭行（不把其它任务/worker完成情况并入本题）。

| 开发操作/资产 | 公开依据 | 已有证据及缺口 | 未来最小路径（全部未执行） |
| --- | --- | --- | --- |
| 定位和导入本源码 | multi.py3749、pyproject24-30 | 精确base可读；grader导入位置有记录，正式actor身份/PATH/源码加载未知 | agent实际shell检查id/cwd/Python路径/pandas与multi.py来源，再在新进程调用公开例。 |
| 公开3行最小复现 | user_prompt:6-10；Index.isin文档 | 输入全内存，无外部资产；历史只执行2行F2P | 构造题面df，校验ndarray、bool、shape(3,)、全False。 |
| 官方既有窄公开测试 | test_isin1-87、nullfixture/helper；conftest依赖 | 历史13节点运行；actor pytest/hypothesis/JUnit可写待验 | `python -m pytest -q pandas/tests/indexes/multi/test_isin.py`；其通过不证明iterator。 |
| iterator及构造器旧行为 | from_tuples559-563；构造器测试353-387 | 静态识别gold回归；无新CPU结果 | 固定midx=[(1,3),(2,4)]对[]、iter([])、iter([(1,3)])、''逐项记录base/gold/合理替代；构造器模块仅窄选from_tuples。 |
| 构建/依赖 | pyproject1-10，NumPy/dateutil/pytz/pytest/hypothesis导入 | 纯Python改动不主动要求重编；若镜像扩展缺失，工具链/Cython<3/setuptools等须准备期提供 | 先判导入失败原因，仅必要时用预置依赖构建；不假定公网下载或系统包前缀可写。 |
| 服务/资源/提交 | 目标小内存对象；公开无外部数据；gold仅multi.py | 无GPU/数据库/凭证需求；实际actor2CPU/4GiB是否采用待验 | 交付业务源，不要求提交二进制产物/系统包；模型开发前验正式actor代码生效。 |

官方恢复仅`pandas/tests/indexes/multi/test_isin.py`：归档prepared_task_face从test.patch取路径，先恢复base/应用官方补丁，test_globs=()；两diagnostics为1文件保护、5父目录、setup/apply成功，gold ledger projection仅multi.py。新增测试没有夹带业务源码。未发现该业务修复被投影忽略/恢复覆盖；保持additional_exclusions=[]。其它conftest、pytest配置、安装可写控制面属于共享机制，未作攻击/注入验证；runner digest未变是这次观测，不是候选任意行为的安全证明。

## 7. 关系、用途、下一步与未查范围

题面是明确回归修复，GH51599为新增测试注释；未读其它题或未来提交，不能据同模块断定重复/家族，也不把外部历史1.5.x断言当本轮执行事实。公开base不带未来Git元数据；真实镜像的可见资产/祖先/答案线索、实际消息均未验。审查者已见gold/隐藏测试/环境摘要和运行细节，记录不可作为solver材料；模型成功率/训练价值/成本未知，costs均null。

问题分别保留：

1. **S51605-1 gold iterator回归/漏修（静态调用链证据）**：新增len截断既有iterator归一化；非空iterator旧行为预计回归，empty iterator目标未修。唯一优先下一步是精确base/gold/iterator兼容合理路线的小型CPU行为对照，并读真实原评分；无需先跑全仓。此处不强制独立grader诊断先具备正式actor；正式actor是模型开发门槛。
2. **S51605-2 输入验证放宽（静态）**：空str/bytes非list-like，本来构造器拒绝；gold早返回使之接受，P2P未保护。与iterator同一位置，可在上述窄对照并列观测，不能用gold结果当公开规格。
3. **S51605-3 原样例长度/边界缺失（静态测试覆盖）**：唯一F2P自改为2行，缺原3行及empty self+empty values；固定2False候选可能骗过官方但违反原例。候选/得分均未执行；保留为定点测试修订建议而非既成错分记录。
4. **S51605-4 actor/当前准备未知**：历史baseline结果完整，正式身份环境及当前镜像未核；缺证据不等于不可解。

八方面覆盖：公开需求与类型措辞；材料/初态；完整F2P/P2P及helper；合理非gold路线；gold回归与公开caller/构造器；开发环境；官方恢复和解析控制面；本题关系/暴露用途。未查全仓调用者、全仓回归、任意自定义iterator/非法形状、真实actor/模型/镜像泄漏。未读本题历史单题或reviewer，未根据另一题结论判断本题；未执行/导入项目、安装下载、网络、Docker/SSH、付费模型、quota/reset，未改源/test/gold/reference/reward/expected或提交推送。本轮仅stdlib文本/JSON/hash、只读归档与本稿写入。
