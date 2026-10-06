# 9066 Q24 Coder 首臂：独立执行与候选语义窄核

日期：2026-10-03。对象：`gpu1003-pyd9066-coder-a1`，固定请求 `swe-pydantic9066-behavior-v1-20261003`。审查者已读过Pydantic私有材料、对照和参考，**不是fresh公开读者**。本次仅读本地归档及已有源码，以标准库核字节、AST与文本解析；没有执行Docker、SSH、安装、项目测试、模型或作者helper。

## 结论与适用范围

**当前公开题面内没有发现决定性漏修、绕测试或可证回归。本首臂可作为固定版本的一次成功普通探针，保留原raw reward=1。** 原评分的2个F2P与368个P2P在原日志中逐完整ID均为PASSED（370参考），包括既有stdlib dataclass实例默认值保护；源码也确实修复了公开标量IPv4Address默认值被遗漏的根因。

候选仍未修复容器内IP默认值，但旧诊断已明确将其列为公开issue未提及的T3范围限制；不能因此新加本轮评分要求或改原分。模型最终声称“全部既有测试通过”“完全向后兼容”，超过其自测证据，也超过370参考所能证明的范围。本报告仅覆盖`pyd9066-behavior-v1`、本次精确镜像与单个Coder首臂，不证明两模型/重复阶段完成、完整仓库回归、普遍模型能力或训练/留出资格。

## 原件、请求和身份

权威来源为`runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pyd9066-coder-a1/`，本臂原件在其`queue_v24/results/gpu1003-pyd9066-coder-a1/`。我重算清单所列368成员的大小/SHA，合计23,336,197B全部相符，无缺件。目录另有authority自身和`sync_receipt_v3.json`，单独绑定，不计入368。Q24回执本臂条目与原件一致；其他题目成员只核完整性，不纳入本题语义意见。`remote/`兼容副本不是本次权威来源。

| 绑定 | 核查值 |
| --- | --- |
| closed authority | `d9715e4213ab15df48810f87f1a0d2de15ad5a71dd011f08fd92f96011a8cf78` |
| 固定请求 | `8ce6dd65864694476d00eef523149b5e0f00142cafa2f6e93eec409a776914a5` |
| Q24 input manifest | `23abe51243d90e12bf344c01e9c61ba90f6c859d4d03d02073ae291b9d226367` |
| 当前job source manifest | `09ddb8bfdeecd3ffaa38c1048a574161ef6fa6053b2855da50166e8e8677899d`，`code_v8` |
| 当前entry | `bdf806bf8da1d5ebb4970887bfc3c7738eb3e57a75e1d07215d6d68b17e574c4`，27,732B |
| 来源release / manifest | `cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1` / `51b833975be2c3354be45b731552235a33070315f0039c8e6f54987de95f6ca8` |
| registry / effective test | `bef4023a4b614d9ae667f962ef8f2874fff87505d08464204d178a99510268f0` / `9d04a80216d751b3c60528a11d90ebe75da799a4d4dd8415412d13b441b14cec` |

固定manifest本题`expected_record`的所有字段与实际`input_check.json`一致；prepared public/private grading/环境记录与冻结发布三记录精确相同，canonical digest相连。参考为2F+367原P+1新增P；安装登记指向E10。当前job用`code_v8`，模型adapter启动路径仍为独立的`code_v4`；`identity_binding_actual.json`的历史`source_code: code_v4`描述服务运输来源，不能当作本job消费者版本。

公开首请求、prepared prompt、`solver_prompt.txt`与`attempt/prompt.txt`字节相同，SHA为`3b04d5e4d9aa24830812a7c9f9b4a7ff31fe1b94de34c56f15a60515aca8e358`，22处CRLF原样保留；problem_statement亦与冻结public记录相同。36个HTTP记录中35个是生成，另1个是`count_tokens`，不是生成重试。全部请求body解码所得9,620字符串中未见完整私有有效补丁、gold补丁或新增私有参考名称；此精确内容检查不等于所有间接信息流证明。

actor/grader实际镜像均为`sha256:2241ad13bceafacf38976b8cfa3d41d0b489099a11741876abba29cbe32781cb`，与固定请求精确CPU派生镜像/Q24配置一致，并非只比公开latest字符串。actor实际UID54321；grader候选前置原件记录UID54322。实际Python3.8.19、Pydantic2.7.0a1、core2.16.3、`/testbed/pydantic/__init__.py`从事实、安装及正式日志交叉核对。UID54321的8个公开wheel逐SHA/大小可读原件绑定当前镜像；grader候选实际安装RC0，成功构建、卸载并重装Pydantic，没有继承旧Q12 hatchling权限拒绝。本臂成功不核销其他题目旧安装失败。

实际请求`slime-actor`经gateway发送`Qwen3-Coder-30B-A3B-Instruct`。派发前09:15:46.965–09:15:47.145 UTC fresh capture核实际engine/adapter IDs、PID、StartedAt、RestartCount=0、readonly模型mount、HTTP服务/模型配置、bfloat16、TP1、context196608、max_running_requests=1。下载manifest绑定`Qwen/Qwen3-Coder-30B-A3B-Instruct` / revision `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`；25文件大小逐项相符。它支持预派发服务身份，没有重复逐权重SHA或GPU显存权重证明。`*_inspect_after_actual`只是预派发capture之后的inspect，backend log也结束于capture，不是作业结束后复验。保留原`gateway_audit.checkpoint_identity_verified=false`、`input_check.service_readback.config_only=true`历史字段，不忽略新增实际服务读回，也不把它提升为完整checkpoint证明。

## 完整轨迹、候选和baseline

两份trajectory逐字节相同（各398,499B），只计一份；stderr为空。已全文读唯一原轨迹、全部35 adapter turns和35 SSE，并核文本、工具与使用量对应。CC有4处无害归一化：第3/33工具删冗余`cd /testbed &&`；第22工具补默认`replace_all=False`并清空仅空白行；第29工具清空仅空白行。分别保留原adapter/SSE与实际CC输入，不误计为模型纠错。

baseline.tar为7,270,400B，**482个普通文件的精确集合、内容SHA与模式逐成员全部核过**；初始census及grader重建census的482对象逐项相同，排除集合digest相同。baseline原环境digest为null，原值保留，不补造证明。canonical baseline为`358bf444821190bbfe7c321c6c97e541974207284cfce3f896f887f9e223a786`，FP为`78a3a6f008b2b2342c041a96566b0261328905e229d8c0df8ab9e6235cfbec7a`。task/public/image/base_commit等既有身份相连。`pdm.lock`与`pyproject.toml`在模型开始前已dirty，pre-solver archive保留这些字节，前后pip_freeze完全相同；模型末尾归因为“dependency updates”没有依据，它们不是原FP改动。

FP五条均为普通100644对象，逐base64解码核SHA/字节及Python AST：修改`pydantic/json_schema.py`，新增`reproduce_issue.py`、`test_comprehensive.py`、`test_ip_serialization.py`、`test_ipv4address_fix.py`四个root诊断脚本。没有修改既有正式测试、fixture/conftest；新脚本不被当前正式`tests/test_json_schema.py`命令执行，也没有替换/吞掉正式断言。四脚本应留在FP，不能为美化候选删除运输事实。

projection接受原FP五条；result/status/projection同源digest一致，评分是`original_frozen_patch`，diff仅供审阅。code_v8 manager先精确重建baseline，再将解码内容用stdin写入regular对象；独立逐对象census/FP核查支持同源运输。本包没有逐次Docker stdin原始审计流，不声称又观察了每个远端写调用。父题主生产delta1,148B与从原baseline/FP重算delta精确相同；其余生产AST全部不变。父题主标准化副本已全文读并绑定SHA`a98870dc94ec45c3c893eb3e02df9c0c05c92454358210e556fe464854aa821d`，轨迹判断直接来源于原件。

## 是否漏修或产生回归

公开问题是`IPvAnyAddress`字段以`IPv4Address("127.0.0.1")`为默认值，schema发warning并遗漏default。base `default_schema`在`encode_default`抛`PydanticSerializationError`后返回无default的schema（`json_schema.py:1012`附近）；`encode_default:1985`原调用`to_jsonable_python`，core2.16.3不能直接识别该IP对象。候选在真实失败点补类型序列化，未匹配特定字段、地址字符串、期望schema或测试节点。

实际修法保留原`to_jsonable_python(dft, timedelta_mode=..., bytes_mode=...)`调用AST并先执行；仅捕获`PydanticSerializationError`，对六种IPv4/IPv6 Address/Interface/Network返回`str(dft)`，其他类型继续raise。它不对任意类型重建TypeAdapter。既有`_std_types_schema.py:582–656`六种IP schema本来使用`to_string_ser_schema()`，因此str回退有当前源码依据，不是硬编码题面答案。未改变验证、错误判定、正式测试、安装、parser或奖励。当前标量IPv4及相关IPv6正式F2P真实通过；模型公开复现也从无default变为`'default': '127.0.0.1'`。

known stdlib dataclass实例保护依据是**既有base行为**，不是公开issue中的示例。原转换成功则候选直接返回，不触发历史gold无条件`TypeAdapter(..., config=...)`的`type-adapter-config-unused`回归；新增`test_default_encoding_preserves_stdlib_dataclass_instance`真实PASSED。bytes/timedelta配置仍在原调用上，相关旧P2P逐参考通过；这不证明全部配置组合或未知自定义类型。

唯一具体已知未覆盖项：例如`List[IPvAnyAddress] = [IPv4Address("127.0.0.1")]`，顶层list不属于六种IP对象，原转换失败后仍raise，预计schema继续遗漏default。这是分支源码推断，本次没有运行依赖。旧`category3_diagnosis_20260929/tasks/pydantic__pydantic-9066/result.md` `8已明确它是公开issue未提及的T3范围限制；可在未来扩大“复合IP默认值”目标时作为最小公开复现建议，**不提升为本轮阻断或新增评分条件**。没有发现当前题面内必须立刻追加CPU运行的具体缺陷。

## 正式参考与验证边界

原eval log为67,454B，SHA`450edbecfcfa6720fd76d9c1fa1437699f27a793ccc05a1429b5f1dba3ceeb6f`。实际命令为：

```text
pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_json_schema.py
```

| 分区 | 独立原日志逐完整ID |
| --- | --- |
| original F2P | 2/2 PASSED |
| original P2P | 367/367 PASSED |
| added P2P，stdlib dataclass default | 1/1 PASSED |
| 总计 | 370/370 PASSED，无failure/missing/skipped/unaccounted |

唯一RH2安装/测试结束标记均RC0；failed_commands空，没有skip、partial或infra。实际正式文件385节点：383PASSED、1SKIPPED、1XFAIL。来源parser函数SHA`995bb6aae58a94f9553946c2f9aea59a158ad4fdf4d7fc0137802c11362b2276`从R14源码逐SHA匹配code_v8 manifest后，标准库提取纯文本函数重放，得到原377个parser键。15个完整原日志ID未成为完整parser键（13个PASSED含空格参数、另2个SKIPPED/XFAIL），并产生7个截断键，净差8；全部在370参考之外。370逐完整ID在独立原日志和原parser映射中均PASSED，因此该既有parser边界不使本臂分数失真，也不证明完整pytest语法已修复。

trusted setup恢复1个正式test文件，有效patch应用RC0，无missing/irregular；protect OK，保护1文件/2目录。runner pre/post digest同为`d5eb18bb38fd14ad32a6fa0b27231b03753e9c31921a29f55abea680d363d809`。原评分/hygiene字段不改，对新增root脚本另披露事实。

模型完整2passed自写测试、完整1passed原`test_schema_class`、公开复现/普通默认值打印都有原输出；两次`pytest ... | head -50/-30`主动截断，不证明JSON schema/IP模块全过。自测IPv4Network还用了IPvAnyAddress注解，默认未验证，因此只说明default序列化，不证明地址验证接受Network。未实测全部六类型、自定义serializer或container default；“全兼容/全部既有测试通过”的最终表述应收窄。事后正式370参考补足当前任务证据，不能倒推模型当时已经完整自验。

## 定位、纠错、用量与并行

唯一轨迹404事件：system36、stream_event276、assistant57、user34、result1；assistant/stream事件不重计回合。35生成请求、1 token-count HTTP、34工具（Bash18/Read11/Write4/Edit1），没有工具结果错误、生成重试或context recovery，全部35生成响应200。仅1次生产Edit，没有失败修法后的反复猜测。

第8工具Read正确定位`encode_default`，结果09:16:19.154 UTC；第9模型请求明确指出core不会处理IPv4Address。第15工具于09:16:25.644直接确认未知类型错误及str可行；第22工具09:16:32.497生产Edit；第23工具09:16:33.111原复现成功。warning/defaults_schema/encode_default、既有IP schema/validator到直接序列化实验形成完整根因链。没有安装排障或第二次生产纠错；base dirty差异的错误归因单独记录，未当作正确环境修复。

| 成本/时间口径 | 原件值 |
| --- | --- |
| 输入/输出token | 521,938 / 4,806，gateway35响应、adapter35turns、CC result逐项相同，cache read/create均0；累积输入含重复上下文，不是唯一token数 |
| 固定预算 | context196608、每请求max_tokens65536、CC turns240、solve10800s、gateway1024、first-byte1800s、idle14400s；35请求实际均65536，CC modelUsage的32000只是结果metadata |
| 首/末生成HTTP | 09:16:13.874444 / 09:16:56.615681 UTC，请求起点跨度42.741237s，不等于完整solve |
| CC | duration47.557s / duration_api39.620s；不相减估纯推理或工具时间 |
| shared solve / actor attempt | 51.109s / 09:15:47.761830–09:17:08.233017（80.471187s），起止口径不同 |
| 全dispatcher | 09:15:47.246937–09:20:47.162656，299.915719s，含actor/grader |
| grading | total217.675s；reset5.765s、baseline重建0.123528s、delta apply0.310527s、trusted setup204.453659s、test phase6.182767s；不相加造完整账本 |
| 原脚本install / pytest | 2.083460378s / 3.580686471s，唯一RH2_TS起止，与manager phase不同口径 |

34工具均在上次结果后发下次调用，没有实际并行。部分imports/相邻方法读取与修改后独立公开自测可以批量；“复现→定位→序列化确认→改动→复现”仍有依赖。这里只给具体机会，不估省时百分比。CC接口允许多工具输出不证明本臂使用过；SGLang max_running_requests=1也不支持多个同时模型生成。无训练层或跨作业吞吐证据。

## 资源、清理与后续

actor实际2CPU/4GiB/512pids，NNP1、CAPPRM/CAPEFF0、无Mounts/Binds、nonprivileged，隔离network/relay；testbed activation正常，Python前缀对actor不可写。grader代码路径、实际UID54322前置与候选安装/测试相符；本包无每次grader exec的完整资源审计，不补造逐调用全验。

22个离散资源采样中本actor6条、grader14条绑定本题镜像；actor样本memory.peak最大914,874,368B/pids.peak22，grader604,094,464B/8，观测到的OOM/oom_kill/pids.max事件0。前题容器及空窗口不归因本臂。采样有未知间隙；grader诊断peak684.5MB单独保留，不以离散样本最大值代替连续峰值或共享GPU吞吐。

quiescence residual0、workspace digest双读稳定；gateway revoke/drain active0。actor container_rm RC0、container_left空、network/relay failures空、labelled container/network无残留。grader manager实际1建1删，open/supply/cleanup_failures空，cleanup_ok=true。本次核原清理事实，没有重新探测远端。

本首臂执行和当前公开范围语义可接受，原1分保留，不因题外container IP重跑旧CPU矩阵。另一模型、重复门槛及题主最终用途决定不在本报告完成范围；薄诊断入口没有miles/训练receipt。若另立通用复合IP默认值目标，可先用上述List公开复现另定新版本。原FP、baseline、分数和固定材料不回写。

同名JSON保存368原件绑定、完整482 baseline对象、FP五条解码绑定、370逐参考状态、原评分/diagnostics、生成用量/调用索引/时间及服务/资源限制；报告本身的静态检查不等于新运行验收。

