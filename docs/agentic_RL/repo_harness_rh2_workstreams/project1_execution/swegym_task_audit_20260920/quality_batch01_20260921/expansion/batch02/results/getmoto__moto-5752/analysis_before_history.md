# getmoto__moto-5752：无质量历史初稿

只读本题指定原件，未运行项目/测试/容器/安装/联网。暂定 `needs_review / static_review`，用途限 `development_diagnostic`。核心顺序缺陷及 gold/no-op 分差可解释；新增 F2P 还捆绑单标签 BeginsWith 的独立旧缺陷，保留验收范围待核。正式 actor 条件另待验，不称 `ready_for_probe`。

路径均相对 `.`：`PUB=runs/swegym_quality_batch02_20260921_v2/public/getmoto__moto-5752`；`PRI=同包/private/getmoto__moto-5752`；`RUN=runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w04-1`；`GLOG=RUN/eval_logs/evallog_replay-f216-baseline01-w_fb82c576.eval.log`；`NLOG=同目录/evallog_replay-f216-baseline01-w_0ec23aeb.eval.log`；`RH2=rh2/src/repoharness2`。公开源码引用从 `PUB/base/` 起算；`T=tests/test_ssm/test_ssm_boto3.py`，`M=moto/ssm/models.py`。

## 1. 材料、输入与初态

固定 base=`b2300f1eae1323e3e8bc45f97e530ce129dff12e`、tree=`af5bc183f2d8898aca1282badb9e2dc1554d552f`。逐题核 `PRI/source_refs.json` 指定 S2 三个 JSONL 第73行，public/grading/validation 与包内对象相等。test patch SHA256=`e978cfc7231752056767cc3192ed5a67be3e630ae0ab3b32a4c2f6d071e397f8`，gold=`94e23bedb77a52fbef589882aec31531129cab051d1d6b49d1a28adcb9986a64`；原 gold artifact candidate.patch 字节一致。整包 blob/mode 核验复用协调层，不重复全包扫描。

`base_identity.json` 记1844跟踪条目、1843物化 blob；唯一未物化 gitlink 是 `tests/terraformtests/terraform-provider-aws@f9a6db6e3c3f3299701747972fd6c37ba4af36f4`，公开 `.gitmodules:1-3` 对应 HashiCorp provider。Makefile:46-50 将 Terraform 作为另一个入口；本题进程内 SSM mock/MWE、选中的 Python 模块没有用到它。本轮不补该子模块，也不把导出缺口解释为实际镜像不存在该资产。无symlink/LFS缺项，包未导出Git元数据。

公开要求是 `describe_parameters(ParameterFilters=...)` 对同一组过滤器排列返回相同且符合全部条件的结果；MWE两个 Equals 标签只应选 b（prompt:3-8,42-79）。接口层 `moto/ssm/responses.py:247-271` 先匹配、后分页；backend在 M:1302 调 `_match_filters`。其公开契约写“matches all the filters”（M:1578-1580），标签分支却在单个标签命中时立即 return True（M:1608-1613）。这精确解释 hello在前时 a、b 都被接收，x在前只收b；NLOG:944-972 实际在第二个顺序断言得到两参数。初态成立，非安装/收集错误造成的伪分差。

public_hints 的禁止改测试、conda已激活等是原操作指令/声明，不是运行证据；user_prompt只是当前静态渲染，真实CLI消息和工具层未捕获。`prepared_task_face.py:342-357` 正式actor取public image并投放public bundle，未出现于user_prompt不等于字段不可读。本题可只改SSM源码，核心开发不需要绕过禁止改测试。原提示“全部测试改动永不计分”的机制解释已过时，具体恢复见§5。

## 2. 每个新增/修改断言与双向映射

冻结奖励为1个F2P、79个P2P；执行命令选中整个 `T`，实际收集80项（GLOG:933-939、NLOG:886-892）。唯一F2P为 `T::test_describe_parameters__multiple_tags`，四个断言在同一函数；no-op第二项失败以后没有执行后两项，不能称no-op四项都失败。

| 公开要求/旧行为 | 断言、输入与公开依据 | 评价及证据 |
| --- | --- | --- |
| x=b且hello=world，两个顺序均只应返回b | F2P先创建a/b，两个标签分别hello=world、x=a/b；先x后hello，`Parameters.length_of(1)`（test.patch:64-78） | 直接覆盖prompt:42-56；no-op首项已过。只查数量，未查实际Name。 |
| 交换上述顺序仍按全部条件匹配 | 同函数先hello后x，`length_of(1)`（:80-87） | 直接覆盖prompt:58-79；原日志在此2≠1失败，gold完成全部函数。能拒绝无操作、首个标签命中即成功、单纯取最后过滤器等直接错误。 |
| 标签值前缀hello以w开头，两参数均符合 | 同函数一个过滤器tag:hello/BeginsWith/[w]，`length_of(2)`（:89-94） | **题面未明示，独立于顺序**。公开M:1462-1468允许非Path的BeginsWith，普通字段M:1617-1620及T:175-179,704-710,752-758展示前缀含义，因此有可推知接口依据；但旧tag分支忽略Option，无旧tag前缀正例。属于验收范围待核，不能仅据校验器宣布所有窄顺序修复均不合理。 |
| 标签x以a开头，只选一个 | tag:x/BeginsWith/[a]，`length_of(1)`（:95-99） | 同上；输入a也是完整值，这一条不能单独区分BeginsWith与Equals，上一条w/world才有区分力。没有要求内部helper、list表示或遍历布局。 |
| 修改的旧by_path fixture保留其原断言 | patch:8-52从7个put_parameter调用去掉Description；T:66-234断言本身不变 | Description不参与 `_match_filters`，且该API的response_object不输出Description（M:225-240）。保留根/递归路径数量、Value/ARN/时间、Type默认/Equals/多值OR/BeginsWith、KeyId、分页、非法Name/Path/Tier与Label断言。仍是冻结P2P `test_get_parameters_by_path`，非新的业务修复要求。 |
| 无过滤器、单标签/缺标签、默认Equals、元数据与分页 | P2P `test_describe_parameters`、`_paging`、`_tags`、`_attributes`（T:553-604,1002-1045）；M:1584-1587,1644-1645 | 公开旧行为有依据；单标签用默认Equals，明确Name=/spam/eggs、排除无标签参数；两角色这些引用都PASSED。 |
| 旧Filters，以及Name/KeyId/Path等ParameterFilters行为 | T:607-892的6个函数；两字段互斥T:895-904 | 已读且属于冻结P2P。名称归一化、前缀/Contains、路径OneLevel/Recursive、多值OR有断言。gold一般标量分支保留这些语义。 |
| 非法过滤器和路径的错误、重复键限制 | T:907-999含14个参数化filter输入及3个非法path输入；M:1332-1470校验器 | 已读全部这些参数化输入和异常断言，冻结P2P含各ID；校验没有改。Contains只允许Name，Path只允许OneLevel/Recursive，避免把gold列表分支不存在的组合当新回归。 |
| 混合tag+Name/Type、三个以上tag、tag多值、空交集 | “all filters”契约与题面“结果符合过滤器”；M:1578-1645 | 新F2P未直接枚举，gold逐过滤器失败终止可合理泛化。数量断言没有证明结果身份或所有排列；作为覆盖限制保留，未构造通过错误候选，不自动判坏。 |

fixture/caller链已读：`T:1-15`导入boto3、sure、pytest和mock_ssm；`moto/ssm/__init__.py:1-4 → core/models.py:396-411` 默认进程内MockAWS，TEST_SERVER_MODE=true才用server；`tests/__init__.py:3 → tests/helpers.py`注册sure扩展，但F2P用标准length_of。NLOG:909-925给出sure实际取len并抛AssertionError的栈，不是测试收集或空操作。创建的参数、标签、region均在本地mock中，不需要真实AWS比较。

**P2P实际阅读范围：**T:1-234、553-1068的18个旧函数（按参数化ID展开对应33/79个P2P）已读；包含全部describe_parameters相关旧测试及直接共用调用者get_parameters_by_path。其余46个P2P（put/get parameter的其它版本/密文、历史/labels、command/instance-tag等）仅核到原日志与冻结列表对应，未逐个展开函数体。不声称全仓或全部SSM回归已人工审过。

## 3. gold、合理替代解与范围疑点

gold只改M的 `_match_filters`，把tag值提取为list，让每个条件均有机会失败，并在Equals/BeginsWith支持列表。缺标签时空list在这两种已允许Option下会失败；多个Values取任一匹配，过滤器之间取全部。Label分支在前面continue，原有语义不被列表分支改写；Name/KeyId/Type仍是标量；Path后续分支未变。未引入依赖、helper命名要求或无关源文件；静态上修复题面原例，现有原日志gold80通过。Tier等校验接受但匹配未实现的旧相邻问题不因本次遇到就算gold新回归。

不同于gold的一条完整路线：在tag分支用`any`分别处理Equals和BeginsWith，未命中返回False，命中后继续外层过滤器循环，最后返回True；通用标量分支可以原样保留。也可独立求各条件布尔再取all。两者不需采用gold的列表改造；当前断言只检查外部结果。

**自然的窄修复与疑点：**将旧tag分支改为“若不存在Key和值都相等的tag则False，否则继续外层过滤器”，即可消除题面及任意Equals标签组合的顺序问题，同时保留旧Option处理。它静态预计过原MWE和旧P2P，却在新增w/world前缀断言失败。它不是完整的已允许Option实现，因此目前只能证明“验收捆绑两项缺陷”的具体线索，不能不加条件地声称误拒已证实。公开读者也把tag BeginsWith列为可见相邻疑义。是否把这项旧缺陷视为本issue必须修复，需要独立reviewer结合公开范围判断；本轮未读历史解释。

单纯排序过滤器以固定先读x，可能掩盖样例但未实现AND；返回错误单例也可能满足数量。它们不满足公开“匹配全部条件”的要求。未执行这类候选，不用普通覆盖缺口推导题目不可用，也不机械另造第二份坏补丁。

## 4. 原始运行与身份

本题只有指定baseline01证据，无附加安装配方。`RUN/ledger.jsonl:7`=noop，`:8`=gold，均attempt1、run_id=`f216-baseline01-w04-1`；原日志/工件均依这些精确行定位，没有读同账本其它题行。

- 镜像为public的`xingyaoww/sweb.eval.x86_64.getmoto_s_moto-5752:latest`，固定digest=`sha256:2665296135d73d6ed10e225ac3942fcc9086811fdfa0ede89a8465a63716c134`，derived_image_recipe=null、image_local_build=false；image_id_actual=null仍保留未知，不补写镜像ID。两artifact的HEAD均是固定base，runtime digest同上述值。
- 两角色真实grader=`rh2grader/54322`、deny_all，testbed解释器前缀获写权限；2CPU/4GiB、PID512、shm64MiB、tmp1GiB。candidate.apply_user=agent/54321只证明应用阶段身份，不能视为正式actor运行。
- `make init`实际执行`python setup.py develop`与`pip install -r requirements-dev.txt`（公开Makefile:17-19），前者写egg-link指向/testbed，后者再次legacy editable install成功（GLOG:623-674,819-923；NLOG:576-627,772-876）。依赖有deprecated warnings但未见安装失败；不是只有最后RC的推断。ledger导入观测为`/testbed/moto/__init__.py`、4.0.12.dev，runner摘要前后相同。传递依赖版本未全部人工复核。
- GLOG:933-1044完整80 passed、testRC0；NLOG:886-1075完整79 passed+目标F2P第二顺序失败、testRC1。冻结F2P/P2P分别1/1+79/79和0/1+79/79，reward1/0；missing/skipped=[]，无全局失败。测试时长17.077/19.780秒，历史峰值309.227/298.637MiB仅适用于该grader观测，不代表actor资源或重复稳定性。
- 部分P2P参考ID在参数值空格处截断（如`filters0-Member`、`[something`），原日志显示完整参数值（GLOG:968,982-995）。当前vendored `RH2/envpack/swegym_parsers.py:44-55,89` 以split取第二项，来源冻结ID采用同一形式；0–13索引区分这些case，账本解析80项无缺席。未据此改ID或奖励，也不把parser map当测试体执行的独立证明。
- `RUN/artifacts/swe_gym_lite--getmoto__moto-5752/a1-2407113c`是gold；`a1-92ad04e1`是noop。已读stage/projection/frozen和baseline元数据，gold仅M纳入投影、noop空变更，candidate.patch与PRI/gold.patch相同。不是全包逐blob复验。

暴露披露：读取了`PRI/environment_record.json`中evidence路径和limit环境摘要（原no-op目标失败、gold完整通过的概述）；未打开所指scope_reconciliation聚合。上述结论用精确账本/日志重核。本题历史refs与旧质量报告未读。

## 5. 开发条件、投影与可见性

| 操作/资产 | 公开入口与证据范围 | 待验及最小命令（只建议，未执行） |
| --- | --- | --- |
| 解释器、当前源码和依赖 | setup.py:29-48,92,99,140；M:7-17需EC2、SecretsManager及yaml；历史grader能导入当前源码 | 真实actor/54321执行`python -c 'import sys,moto,boto3,botocore,yaml,pytest,sure; from moto import mock_ssm; import moto.ssm.models; print(sys.executable,moto.__file__)'`，应命中/testbed源码。激活、PATH、包可读/可写需实测。 |
| 窄复现与回归 | prompt的mock_ssm入口；T公开旧测试、sure依赖已声明 | 用已封存public_read的MWE（加us-east-1、虚拟凭据、AWS_EC2_METADATA_DISABLED=true）核两顺序的Name集合；再`python -m pytest -q tests/test_ssm/test_ssm_boto3.py -k 'describe_parameters or get_parameters_by_path'`。旧测试本身不包含新增F2P，不能替代MWE。 |
| 安装、编译与交付 | Makefile:17-19与requirements-dev；本题纯Python过滤逻辑 | grader能写conda前缀不代表actor能。若源码已直接导入，局部修改无需强制重装；必要安装需实际身份/离线资产验证。未识别必需编译器或新增系统包；无需把全仓make test变成开发前提。 |
| 资产/网络 | M:54-82只在/aws前缀触发全局参数资源加载；MWE用普通String；.gitmodules为Terraform另入口 | 最小MWE不需真实AWS、Terraform、密钥、Docker或GPU。题面建议对比AWS不是修复必须步骤。准备可固定依赖；解题/候选安装/测试不假定公网。历史baseline deny_all成功只覆盖grader。 |
| 资源与写入位置 | actor环境卡默认2CPU/4GiB等；历史数据见§4 | 本题actor的实际UID/HOME/cwd/tmp、解释器前缀、资源与重复稳定性待验。修复只需可写/testbed源码；无需提交生成的egg-info或改只在系统包中的文件。 |
| 官方恢复与评分控制面 | private test.patch仅触碰`tests/test_ssm/test_ssm_boto3.py`；GLOG:446-454精确checkout base后注入 | 当前RH2 `prepared_task_face.py:312-336`用test.patch触碰路径和`test_globs=()`。业务源码M不会被官方恢复，artifact已证明gold纳入。test.patch无生产源码；`additional_exclusions=[]`。tests/helpers、tests/__init__与setup.cfg已读相关部分，没有篡改实验或新增排除依据。 |

真实消息、agent工具shell、public bundle字段应用和运行可见Git/祖先/缓存/预装包仍未验。静态包没有.git不等于实际容器无答案；本题没有发现必须从外部取得的附件或新资产，也没有依据宣布答案泄漏已排除。任务关系没有跨题检查，不按同仓文件名成组；没有真实solver轨迹或基座能力/成本证据。

## 6. 唯一优先实验与暂停点

八方面都已核到上述范围：公开要求；版本与初态；全部新/改断言及fixture；替代解和验收范围；相关P2P/共用调用者与gold；开发条件；精确投影/恢复；用途、关系和暴露。没有运行新的CPU测试或模型，未知成本留null；未查完整SSM其它测试、Terraform、实际actor、重复/并发和solver行为。

**只优先一个定点实验：确认“仅修顺序”的自然窄实现是否被独立前缀要求拒绝。** 在隔离baseline配方上，使用已有base/gold和一个不改测试的窄候选：tag分支以any检查现有相等条件，失败False、命中continue外层，保留其它逻辑。分别核公开MWE两顺序的返回Name和混合Equals条件，再跑原冻结选集并定位首个失败断言。预期候选修复公开原例、P2P不退化，却在单标签w/world处失败；gold同时通过两类行为。实验仅确认拒绝原因和范围差异，是否属于不公还要判断BeginsWith的公开API线索是否足以纳入本issue，不预先裁决为坏题或改oracle。不再并列设计作弊补丁。

实际actor验证仍是任何未来模型探针的前置缺项；不能把这个私有诊断补丁算独立求解。初步处置保持needs_review/static_review，范围疑点与环境缺项分别记录；若reviewer接受前缀为合理隐含契约，可转为静态候选待actor条件验证，仍不冒用ready_for_probe。

实际阅读：本题public根材料和封存public_read；private test/gold/grading/validation、source/run refs、经过字段筛选的environment_record；精确S2第73行和baseline账本7/8行；两日志安装关键步骤、F2P失败栈、完整测试摘要；本题artifact元数据及gold candidate.patch对应；公开T:1-234,553-1068、M:1-85,176-275,1280-1315,1330-1485,1500-1653、responses:209-277、SSM mock/core入口、tests初始化/helpers、setup/Makefile/requirements及.gitmodules；必要RH2选择/恢复/解析控制面。未呈现的长日志依赖列表不称已逐项读完。阅读其它任务时取得的结论未作为本题证据。

本稿保存后暂停，等待协调者SHA封存并明确开放5752历史refs；不读本题历史，不生成delta/card/record，不进入5134原件阶段。
