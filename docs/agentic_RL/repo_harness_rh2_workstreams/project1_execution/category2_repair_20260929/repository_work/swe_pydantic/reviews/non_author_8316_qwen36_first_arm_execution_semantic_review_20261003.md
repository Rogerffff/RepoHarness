# 8316 Qwen首臂：独立执行与候选语义窄核

2026-10-03。**当前约定范围内未见新阻断：原候选通用修复to_snake缩写边界；真实安装／测试RC0，144条正式参考全PASS。** 原FP仅改pydantic/alias_generators.py，没有正式测试修改或遗留失败测试文件。原raw reward=1保留。本报告接受本臂执行证据与当前目标源码语义，不授予训练／留出资格，也不证明稳定成功率。

审查者已接触私有修订、CPU材料及旧Coder报告，不是fresh公开读者。本轮只读本地原件／必要既有源码，用标准库hash、base64、tar、AST和文本解析；没有SSH、Docker、安装、项目pytest、CPU／GPU／模型新运行、作者helper执行、GPU消息或看板写入。只新增本报告与同名JSON。

## 输入、完整运输与实际评分

权威目录为runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pydantic8316-qwen36-a1/。150个manifest成员共10,446,992B全部核大小／SHA和精确集合；另有manifest自身和同步回执，不增计候选或执行。451项baseline逐tar路径、普通文件类型、执行位、大小／内容SHA核齐；actor census与grader rebuild census字节一致，baseline摘要159f3843…与旧Coder相同。预先依赖差异不能归因模型；原environment_package_digest=null不回填。

FP摘要81b15f10…一致，唯一100644修改条目为alias_generators.py，1471B／SHA dcc56c93…。唯一Edit应用到baseline与FP逐字节相同，原候选diff也核齐；无评分投影剥离候选测试的误读。公开首HTTP文本与原2650B prompt完全一致，64个CRLF保留；全部14请求解码2554个字符串，完整私有patch与4个非公开标记未出现。此为指定内容扫描，不声称穷尽所有泄漏渠道。

registered request、41项归档输入绑定、prepared三视图、题主固定请求swe-pydantic8316-behavior-v1-20261003／SHA d935ed00…、expected record与实际input_check一致。code_v8 source manifest 09ddb8bf…、entry bdf806bf…、共享solve 00ca8499…；v3 revision、registry 6fa5f011…、proposal 8b7b2145…、effective patch b248daa2…、公开／环境／grading摘要、materials identity 05c81527…保持已审R20来源。本轮不重审旧CPU矩阵或整release。

正式命令测试tests/test_utils.py。逐原日志、结果分区与实际source parser核144项：original F2P 1／1 PASS、original P2P 143／143 PASS，无缺席／skip／失败。全文件173节点为159 PASS／14 SKIP，分母不同，不能写173全通过。既有parser对非参考含空格参数ID有截断：169解析key，20完整原ID不在解析map、16额外截断key，均不涉及正式144。保留非参考格式边界，不据此推翻精确参考结论。

安装RC0／测试RC0，无失败安装命令／skip／partial；实际导入/testbed/pydantic/__init__.py、版本2.6.0a1，原日志core2.14.5已满足。actor UID54321／Py3.8.19，grader UID54322离线前置实际OK；可信测试恢复／保护完成，runner前后cdcb38ab…相同。CPU同f939镜像既有wheel证明关联，未做新GPU两UID完整矩阵；env_qualification仍absent。

## 语义与公开范围

三个regex依次是([A-Z]+)([A-Z][a-z])、([a-z0-9])([A-Z])、([a-zA-Z])([0-9])，插入下划线后整体小写。第一步分开HTTP与Response；整个输入扫描支持内嵌、多处、长短缩写，没有次数／长度上限、串首限定或输入表hardcode。第二、三步保留小写／数字→大写和字母→数字边界。

三段pattern／顺序与已审Coder一致；Qwen lambda的group(1)+下划线+group(2)与Coder替换串等价。分别确认替换结构后归一化比较修法AST，不冒称两个原AST／文件字节相同；旧Coder29项纯函数重放仅在机制等价范围复用，本臂144真实评分独立核。没有新纯函数重跑。

唯一生产AST变化为to_snake；to_camel／to_pascal保持原AST。当前主问题与v3断言未见漏修、绕测试或可证生产回归。题卡已把公开附注大小写HTTPResponseCode别名要求列为P4，不新增casefold、单字母缩写、kebab或额外非ASCII／数字规则的评分要求。

工具10先断言HTTPResponse正确，后错误期待Foo(HTTPResponseCode=200)匹配生成别名httpResponseCode，实际RC1／ValidationError。下一请求正确认识大小写与当前范围，未再改to_camel。失败是在inline python -c中，FP无遗留脚本；与[旧Coder交付缺陷](../model_audits_20261003/8316_coder_first_arm_acceptance.md)分开：旧Coder目标修法／原分有效，但遗留test_fix_verification.py缺陷仍保留，pair执行完成不抹去它。

## 轨迹、纠错与验证

完整读取唯一221条轨迹和14个adapter原输出／HTTP-SSE；attempt与harness两份130514B字节相同，144个stream事件、34个assistant事件为分块，不能增计请求。逐消息ID、文本／reasoning、工具参数和usage核齐。CC只在已知/testbed cwd下去掉一次“cd /testbed && ”前缀，并给Edit补replace_all=false；明确这两种规范化，其余一致，原件未改。

| 定位或验证 | 实际证据 |
| --- | --- |
| 首次假设／定位 | 请求1从公开例子提出缺缩写边界；工具1找到文件、工具2读源码，返回13:56:47.728Z。 |
| 根因纠错 | 请求3／4错误想象HTTPResponse中非相邻eR匹配；工具3实际复现旧输出、工具4打印两条旧regex都没有正确分词。 |
| 首次完整正确机制 | 请求5（13:56:52.612070→13:56:55.759208Z）正确解释相邻字符匹配缺口、提出三段regex，工具5验证；不把首次读文件当完整正确定位。 |
| 编辑／验证 | 工具8唯一生产Edit；工具9原camel2snake 17 passed；工具10 P4失败并纠正范围；工具11 snake/camel/pascal选择38 passed／134 deselected；工具13打印28检查全通过。 |
| 陈述边界 | 最终只说明to_snake修复，未声称修好to_camel。中途“all tests pass”超出当时17／38选择，应收窄为所选测试；正式144来自后续可信grader。 |

真实14次请求／生成（全HTTP200、single attempt、无counttokens）、14 CC回合；13工具（10 Bash、2 Read、1 Edit）、1工具错误。上报输入110510／输出4665，共115175 token，cache输入0。双份trajectory、stream与历史messages不增计；未估有效token或节省比例。

全部时间UTC：dispatcher 13:56:19.951839→14:00:58.234093＝278.282254s；actor attempt 13:56:20.474821→13:57:24.375442＝63.900621s；solve34.719s、CC31.192s（API27.838s）、首HTTP至末adapter返回31.128562s，均嵌套不相加。grader212.699s，其中start/verify5.505808、baseline0.117005、delta0.112337、可信准备201.953438、test阶段4.209143s；短安装2.026708s／pytest1.673784s为内嵌区间。cleanup／parser段未记录保持null，不以差额造数；长耗时在可信环境准备，模型代码推理无环境排障。

13工具全串行，无子agent；模型侧max-running-requests=1。独立只读阅读可批量，但复现→推导→编辑→验证存在依赖，无可量化并行节省证据。当前薄诊断没有miles／训练捕获／训练receipt，不推断typed训练消费、梯度或训练效率。

## 服务、900保护、资源及清理

本次运行前真实捕获13:56:19.706271→19.858496，早于派发19.951839；不是把历史启动时间当本次捕获。engine CID 5a023c27…／PID999327、adapter CID aff52a71…／PID1000924均restart0，前后inspect身份／argv一致，实际分别启动13:24:03.233754906Z／13:26:58.312905352Z。只读Qwen3.6-35B-A3B→/model，bfloat16／TP1／context196608／max-running1；adapter code_v8／qwen3_coder工具解析／qwen3 reasoning解析，配置与HTTP关联成立。revision995ad96e…、download manifest32bd30f6…，37文件大小／集合含26权重核齐；未重复逐权重hash或证明显存字节。input原config_only=true／runtime_readback=false、gateway checkpoint_identity_verified=false不回填，以实际capture独立补证。

probe-wide为context196608／输出65536／CC240／solver10800s／gateway1024／首字节1800s／idle14400s，真实HTTP输出65536（CC静态modelUsage另报32000，实际HTTP优先）。准备900s政策仅绑定8316／v3／grading摘要／有效patch／f939精确镜像／支持请求f6f157c2…，政策源与固定JSON SHA独立核；不是任意镜像预算上调。原policy actual_image_inspect_verified=false保留，真实actor／grader CID镜像补证；whole3600／apply120／test1800不变。

20有限外采样按exact CID、run_id、name、PID、镜像、时间关联：actor4／relay4／grader15（14 finite，最后cgroup／metrics=null）。grader真实截断name为/rh2-gpu-grade-gpu1003-pydantic8316-qwe-148d05e8，CID fa4c2e5c…／run_id gpu1003-pydantic8316-qwen36-a1-grade；不能用全jobname前缀漏关联。sampled memory.peak最大actor885800960B／pids21、relay27615232B／7、grader528953344B／8，有限点OOM／oom_kill／pids.max均0。grader report峰值647.207MB保持原字段来源，不与外采样混为连续峰值。安装14:00:52.305851→54.332559、test54.333784→56.007569各0采样点；最后null不填0，间隙未知，宿主GPU聚合不作每actor显存／吞吐证明。prelaunch2CPU／4GiB／512pids、swap0、非privileged／无Binds或Mounts；actor UID54321／有效许可cap0／NNP1，可信root初始化caps分开。

actor stop／quiescence residual0、工作区双读稳定，唯一gateway close与attempt完全一致且revoked／drained／active0。actor／relay／网络清理RC0、标签残留空；manager创建1删除1，open／supply／failures空。

原PID1 journal exact unit为rh2-gpu1003-pydantic8316-qwen36-a1-qwen-first10-v1.service：start、Deactivated successfully.及CPUtime，_PID=1／_EXE=/usr/lib/systemd/systemd，时间窗、原request／result／attempt SHA一致。成功14:00:58.264325Z与原dispatcher RC0关联。retired unit的MainPID0／not-found／默认ExecMainStatus0不是实际exit证明；使用原entry完成加exact PID1成功日志，不宣称全宿主PID0或其他在途作业清理。

execution receipt efdc6284…为机械核对；较早closed manifest的semantic pending／pair未闭合保持历史时点。后到pair receipt 38c4207c…表明两个模型各首次一次执行完成、0新重复，本审查只对Qwen独立签结论，保留旧Coder交付缺陷。题主交接请求已returned，本轮没有公共状态读／写。

当前可记录本臂“执行齐全、目标修复有效、144正式参考全通过、当前范围未见新交付阻断”。不授予训练／holdout，不声称typed训练消费、跨镜像通用性、稳定成功率、模型优劣或连续资源效率。没有具体当前公开回归需要新增评分或实验；原分／baseline／FP／历史报告／材料保持。
