# 9066 Qwen 首臂：独立执行与候选语义窄核

日期：2026-10-03。对象：`gpu1003-pyd9066-qwen36-a1`，固定请求 `swe-pydantic9066-behavior-v1-20261003`，修订 `pyd9066-behavior-v1`。审查者已接触本题私有材料、对照及参考，**不是 fresh 公开读者**。本次全文读唯一原轨迹及全部请求/响应，以本地标准库核字节、运输、AST、逐参考文本和原运行记录；没有运行 SSH、Docker、安装、项目测试、模型或作者 helper，没有改原件、原分或共享材料。

## 结论与范围

**没有发现新的执行阻断、公开题面内的决定性漏修、绕测试或可证回归。本次 Qwen 首臂可接受为固定版本的一次成功普通探针，保留原 raw reward=1。** 候选安装/测试均 RC0，370 个正式参考（2F+368P）逐完整 ID 均为 PASSED；实际补丁只修改 `pydantic/json_schema.py` 的六类 IP 导入与 `GenerateJsonSchema.encode_default`。

Qwen 最终先将六类标量 IP 转为字符串，再调用原 core 转换；Coder 首臂先调用 core，发生 `PydanticSerializationError` 后才对六类 IP 回退。两者在本题公开标量默认值和正式参考上均有实际成功证据，**不能把这两种机制扩大为一般语义等价**。容器内 IP 默认值仍是旧 T3 范围限制，不能借本轮新增评分要求。重复阶段、完整仓库回归、通用模型能力、权重显存证明、typed 训练验收和训练/留出资格不在本报告完成范围。

早期宽泛 `fallback=str` 的确破坏 Callable 默认值 warning；模型看到实际自测失败后撤回该改动，最终 FP 没有这一回归。早先“pytest/Faker 前后换版本”的线索在权威原件中不存在，已撤回：前后 pip_freeze 字节完全相同，实际可见版本均为 pytest7.4.4/Faker22.2.0。端点一致和可见命令没有安装不等于连续依赖监控，本报告不补造环境切换解释。

## 原件与固定身份

权威根为 `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-pyd9066-qwen36-a1/`；本臂结果在其 `queue_qwen_first10_v1/results/gpu1003-pyd9066-qwen36-a1/`。closed manifest 的 **214 成员、21,096,651B** 已逐大小/SHA/精确集合独立核齐。目录另有清单自身及 `sync_receipt_v4.json`，单独绑定，不计入214。execution receipt v4 和 pair receipt 与原件一致；pair 只记录首臂各执行一次、本次无新增重复样本，不代替语义审查。

| 绑定 | SHA256 |
| --- | --- |
| closed manifest（47,772B） | `ecd052ea8065e14d973ebe25eef7c095436f915239f1e93f475bc3817fb47d7c` |
| 本臂 execution receipt v4（240,354B） | `73179e9619713563d311f50e25876b795ec52a4eecd52bbd5858ffa51d91dc1d` |
| pair receipt（3,045B） | `bba2cf960b6225807a42523e53dedef0b23a800799683fa57fbaea681d533e3c` |
| 注册请求（18,341B） | `cf54ad3e149ade9c36ba3709376f7af4bc3734a43e2fe91f0bb0a600d877f908` |
| 原 owner request | `8ce6dd65864694476d00eef523149b5e0f00142cafa2f6e93eec409a776914a5` |
| 当前 code_v8 source manifest / entry | `09ddb8bfdeecd3ffaa38c1048a574161ef6fa6053b2855da50166e8e8677899d` / `bdf806bf8da1d5ebb4970887bfc3c7738eb3e57a75e1d07215d6d68b17e574c4` |
| 来源发布 / registry | `51b833975be2c3354be45b731552235a33070315f0039c8e6f54987de95f6ca8` / `bef4023a4b614d9ae667f962ef8f2874fff87505d08464204d178a99510268f0` |
| 有效 test patch | `9d04a80216d751b3c60528a11d90ebe75da799a4d4dd8415412d13b441b14cec` |

来源 release 为 `cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1`。注册请求引用的60份固定输入逐字节核齐；其中沿用的其他题目文件只核完整性，不在本题给予语义验收。当前题 `expected_record` 全字段与实际 input_check 相同，prepared public/private grading、registry、E10 安装和冻结 public/grading/env 三记录连接一致。任务配置与固定 manifest 精确相同；whole/setup/apply/test 预算为 **3600/300/120/1800 秒，actual policy=null**。本题没有使用8316的reset900支持，也没有因生成器旧字段推定预算。

actor/grader 实际均为镜像 `sha256:2241ad13bceafacf38976b8cfa3d41d0b489099a11741876abba29cbe32781cb`。actor UID54321、grader 候选前置 UID54322；Python3.8.19、Pydantic2.7.0a1、core2.16.3、testbed 导入路径与原安装/事实/正式日志相符。候选实际安装成功，构建、卸载并重装 Pydantic，未出现旧 Q12 wheel 权限拒绝。本包未新做另一套 UID/wheel 实验，沿用已核同镜像与固定 E10 材料，并以本臂实际安装 RC0证明本臂安装。

公开 prompt、prepared prompt、solver_prompt、attempt/prompt 以及首 HTTP 用户公开文本精确相同：1,393B、22处CRLF、SHA `3b04d5e4d9aa24830812a7c9f9b4a7ff31fe1b94de34c56f15a60515aca8e358`。39个实际请求解码的14,021字符串中没有完整私有有效 patch 或新增私有 dataclass 参考名称；这是指定精确内容核查，不是所有间接信息流证明。

## 实际模型服务与依赖边界

派发前的 fresh capture 为14:19:31.990344–14:19:32.186671 UTC，早于dispatcher启动14:19:32.314100。实际 engine CID `5a023c27c62bb2f37cf060429a59f96b726d1b404cf756bc8052564037bf3349`、PID999327、StartedAt13:24:03.233754906Z；adapter CID `aff52a71c621b2520b42350259a2992a18c0ed40ea209906357d3c2a552fc36d`、PID1000924、StartedAt13:26:58.312905352Z；二者 RestartCount=0。HTTP/model配置与 `Qwen3.6-35B-A3B`、bfloat16、TP1、context196608、max_running_requests=1、readonly /model mount 相符。adapter实际来自code_v8，使用 qwen3_coder/qwen3 parser、idle14400，默认temperature1/top_p0.95/top_k20/max_new_tokens65536。

下载 manifest 指向 `Qwen/Qwen3.6-35B-A3B` / revision `995ad96eacd98c81ed38be0c5b274b04031597b0`，SHA `32bd30f61860366b3783eabc9d75bee0cd28c474d9c07de8be8d9ae60a4552ab`；实际列表37文件含26个safetensors，逐大小核过，历史 declared_files_count=40 原值保留。没有重复逐权重 SHA 或 GPU 显存权重证明。`inspect_after_actual` 属于此次预派发 capture 后的 inspect，并非作业结束后服务复验。原 input_check 的 config_only=true/runtime_readback=false 和 gateway checkpoint_identity_verified=false 原样保留；新增 actual capture 支持当前派发服务身份，不将其提升为完整checkpoint证明。

actor前后 pip_freeze 均SHA `b88b1934fe48d2891bf385dba0ffa88121331c0ab7715d9d3f6024b64740c9ef`，字节相同，含 pytest==7.4.4、Faker==22.2.0、pydantic_core==2.16.3。完整唯一640事件、全部39 adapter raw/parsed响应、公开工具命令和题主标准化副本均未出现所谓 pytest7.4.3/Faker20.1.0。RAW305实际是 `pytest -x | tail -100` 的失败尾部，无pytest版本头；RAW479含真实pytest7.4.4/Faker22.2.0头。可见模型命令没有pip安装、换解释器或环境激活切换。因此旧版本切换线索无原件依据，不能写成发生过的环境问题。dirty的pdm.lock/pyproject.toml属于开始前baseline事实，不属于最终FP，也不推定模型做过依赖更新。

## 完整轨迹、baseline与补丁运输

两份trajectory逐字节相同，各871,450B/SHA `b78114e8f23fe4b1e30543ea785f974cdba7903276cf0f1ea6e6636661302869`，只计一份；harness stderr为空。已全文读640唯一事件、公开prompt、39实际adapter turns与39 SSE。parsed reasoning/content、SSE、trajectory工具和usage逐项对应；raw_output与 parsed reasoning 的 `</think>` 分界一致。CC仅在第1生成删去已知/testbed cwd下的冗余 `cd /testbed &&`，Edit默认 replace_all=False 归一化单独核对，未计为新模型纠错。

baseline.tar 为7,270,400B，**482普通文件的精确集合、内容SHA和执行位逐成员核齐**；初始census和grader重建census逐对象相同，排除集合digest相同。canonical baseline 为 `sha256:358bf444821190bbfe7c321c6c97e541974207284cfce3f896f887f9e223a786`，与已核Coder首臂一致。baseline原environment digest=null保留，不补造环境证明。

FP canonical 为 `sha256:e4c40db9c7c2334eedb6de489293c1dfd1642b0dc1a3ea21f5e98fc33b88d878`，只有一个regular100644 modify：`pydantic/json_schema.py`，103,553B/SHA `2f219e53bea3fad542efe7cd3e14b6f748a56016f25607f15c0de5fa7542575a`。严格base64解码与FP内容digest一致；从baseline按原5次Edit顺序重放得到FP的完全相同字节。没有新增测试/root脚本、fixture/conftest或评分/runner修改。projection含唯一原FP条目；result/FP/baseline/projection各digest相连，评分运输为 original_frozen_patch，不把diff当权威补丁。

code_v8评分消费者先重建原baseline，再按原FP内容用stdin写regular对象；逐成员census、解码内容与原patch应用RC0共同支持同源运输。本包没有每次远端stdin原始审计流，不声称独立观察了所有Docker写调用。生产delta792B；去掉新增ipaddress导入及encode_default里唯一IP guard后，整个模块AST与base完全相同，原core调用及kwargs也完全相同。

## 根因、修法与纠错

公开例子是 `IPvAnyAddress` 字段默认 `IPv4Address("127.0.0.1")`；core2.16.3直接转换不能识别该对象，`encode_default` 抛 `PydanticSerializationError`，`default_schema` 据此发warning并返回没有default的schema。模型首先实跑公开例子确认warning/default遗漏，第7工具Read正确定位encode_default（14:20:05.751 UTC），第6生成已经提出core未知IP类型；第8工具的直接core调用确认错误后，第7生成（14:20:07.074956→14:20:09.091877）给出有实测支持的根因。定位在首次改代码前完成。

第17工具首次Edit加入 `fallback=str`，公开例子及六类IP打印成功。第20工具的自测带不存在的 `--timeout=120` 参数，pipeline使外层结果未标error；模型看到原输出后移除参数。第21工具 `pytest ... -x | tail -100` 真正出现 Callable `DID NOT WARN`（1failed/98passed），同样被pipeline返回码掩盖，模型没有忽略输出，随后查看原warning测试，撤回宽fallback。第26工具先还原core调用，第28/29工具改为六类IP导入/顶层isinstance→str，第30工具删除误加的无用import（14:20:44.665）；最后两次Read与正式FP一致。第36工具动态构造模型漏写annotation，得到实际工具error；第37工具补annotation，六种IP默认值观察成功。这是自测代码错误的纠正，不能计为生产修法或环境修复。

最终修法：
```python
if isinstance(dft, (IPv4Address, IPv6Address, IPv4Interface, IPv6Interface, IPv4Network, IPv6Network)):
    dft = str(dft)
config = self._config
return pydantic_core.to_jsonable_python(
    dft, timedelta_mode=config.ser_json_timedelta, bytes_mode=config.ser_json_bytes
)
```

原 `_std_types_schema.py` 六种IP schema使用 `to_string_ser_schema()`；公开字段默认的字符串表示有旧源码依据，候选按类型修根因，没有匹配固定地址、字段、预期schema或参考名称。顶层非IP默认值继续原core调用，bytes/timedelta配置及其他模块AST全部保留；没有对任意类型重建TypeAdapter，没有留下fallback=str。stdlib dataclass实例保护依据是**base既有行为**，不是公开issue示例；最终源码保留该路径，新增 `test_default_encoding_preserves_stdlib_dataclass_instance` 在正式原日志中PASSED。

Qwen的提前str与Coder的错误后str在core将来能成功处理IP或特殊IP子类时可能不同；本报告只认当前六类标量/default题面和真实参考。没有当前公开范围内的可证新回归，不以一般假设追加评分。例 `List[IPvAnyAddress] = [IPv4Address("127.0.0.1")]` 的顶层list不进此guard，预计仍因原core转换失败遗漏default；这是源码推断，未运行依赖。旧T3诊断已明确公开issue没有提出容器IP默认值，沿用这个范围限制；未来若扩大目标可用此最小公开复现另立版本，不改本臂分数。

## 正式参考与模型自验

原eval log为67,001B/SHA `8e7253fb7d1105fc592584b7a068d111aeaf0586e91ee24220c9d3af9833a61a`，实际正式命令：
```text
pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_json_schema.py
```

| 参考分区 | 原日志逐完整ID / 原parser |
| --- | --- |
| original F2P | 2/2 PASSED |
| original P2P | 367/367 PASSED |
| added P2P，stdlib dataclass default | 1/1 PASSED |
| 合计 | 370/370 PASSED，无failure/missing/skipped/unaccounted |

正式文件385节点为383PASSED、1SKIPPED、1XFAIL，不写成385全PASS。独立提取完整ID与实际source parser纯文本重放一致证明370参考全过。source parser SHA `995bb6aae58a94f9553946c2f9aea59a158ad4fdf4d7fc0137802c11362b2276` 与code_v8 manifest相符；它产生377键，15完整raw ID没有完整parser键、另7截断键，净差8，均在370参考之外。既有parser边界不改变本臂评分，也不证明通用pytest参数解析已修复。

唯一RH2安装/测试结束标记均RC0；failed_commands为空，无infra/skip/partial。trusted setup恢复1正式test文件，有效patch应用RC0；保护1文件/2目录成功，无missing/irregular；runner pre/post digest同为 `d5eb18bb38fd14ad32a6fa0b27231b03753e9c31921a29f55abea680d363d809`。实际scripts_digest为 `6d45f7dbb32b6486be3d9aa75c3ecc399c6452bced6c5a02fcf513d01cb9f60e`；没有env_qualification额外证明。

模型最终公开例子default恢复且无warning；Callable选择8passed、IPvAnyAddress选择9passed等有完整输出。full json_schema的tail输出有380passed/1skipped/1xfailed summary，networks的tail有232passed/1skipped/1xfailed summary；这些支持所运行文件的summary，不能替代逐ID原日志或扩大成完整仓库回归。六IP动态模型结果主要是打印，未新增正式断言。早期失败的pipeline外层is_error=false不意味着pytest成功，报告保留真正失败及纠错；实际正式370逐参考是本轮最终评分依据。最终陈述准确解释targeted IP修法及lambda warning保留，仍应限定已测范围，不能从“fix complete”推定未知类型/子类/容器或全仓库兼容。

## 调用、时间与实际并行

唯一640事件为system81、stream_event417、assistant100、user41、result1；stream增量及两份trajectory不重计。39实际生成请求、0count_tokens、41工具（Bash26/Read10/Edit5），全部HTTP200/attempt1，无stream错误或context recovery。CC num_turns=42是它自身口径，与39请求分别保留；工具结果errorflag共1，不把pipeline掩盖的两次失败吞掉。

| 口径 | 原件值 |
| --- | --- |
| 实际输入/输出token | 570,297 / 8,676，总578,973；39 gateway/SSE/adapter/CC逐项相符，cache0。输入是重复上下文累计，不是唯一文本长度 |
| 固定模型/求解预算 | context196608、每请求max_tokens65536、CC240turns、solver10800s、gateway1024、first-byte1800s、idle14400s；CC modelUsage的32000是metadata，不能替换实际39HTTP值 |
| 首HTTP / 末adapter返回 | 14:20:00.813053 / 14:21:11.624064 UTC，跨度70.811011s |
| CC / CC API | 70.891s / 54.889s；不相减估纯推理时间 |
| shared solve / actor attempt | 75.367s / 14:19:32.996571–14:21:18.575576（105.579005s） |
| dispatcher | 14:19:32.314100–14:24:49.407735（317.093635s） |
| grading | 209.393s；start/verify6.258071、baseline0.137501、delta0.133347、trusted_setup195.705413、test_phase6.319074，cleanup/parser字段null保留 |
| 原脚本install / test | 14:24:41.107537–43.212814（2.105276s）/ 14:24:43.213959–46.894589（3.680630s） |

上述时间是嵌套/不同边界，不相加造“总成本”，不将全部trusted setup归为模型推理或安装排障。可见代码推理与两次自测纠错没有模型依赖安装排障。

第1、2、38生成各有两个工具，同一bundle两个调用都先于任一结果；第2bundle结果还倒序返回，支持实际独立工具共同交付/执行。它们分别是ls+公开复现、find+warning查找、最终imports+encode_default读取；不是全41工具严格串行，也没有子代理/同时模型生成。记录缺少每个工具连续start/end，不能量化实际重叠秒数或省时。相邻独立源码读取和修改后独立自测可批量；根因确认→修改→复验存在依赖。SGLang max_running_requests=1限制模型请求并行，不能从多工具bundle推断跨题吞吐。

## 资源、终态和后续

actor prelaunch实际2CPU/4GiB/512pids/swap0，UID54321、NNP1、有效/许可cap均0、nonprivileged、无Mounts/Binds，独立network/relay与readonly activation。grader原前置UID54322和实际候选安装/测试相符；本包没有每次grader exec的完整资源审计，不补造该范围。

23个离散外部采样按exact CID、run_id、实际name、image和时间窗归因：

| 对象 | 实际CID / 样本与窗口（UTC） | 样本memory.peak / pids.peak |
| --- | --- | --- |
| actor | `ac5784b9b04108bee257b8587972b9d8a0eeac1f1eaf381923a0faad349549a2`；6有限样本，14:19:47.856559–14:21:03.252705 | 922,185,728B / 35 |
| relay | `ed2f899bf704930b8a798b08f7145c0f968e33679add316030a3e24b3043a035`；7条中6有限，14:19:47.856559–14:21:18.327782 | 27,774,976B / 7 |
| grader | `cd9320c90f8db353f24d5ce5a4f767997807ff67c3eb5068d56c4ffcd89de563`；13有限样本，14:21:33.396595–14:24:34.354809 | 537,219,072B / 8 |

grader实际name为截断的 `/rh2-gpu-grade-gpu1003-pyd9066-qwen36-a-39125b88`、run_id为exact job-grade，不能要求完整jobname prefix而丢失归属。有限样本OOM/oom_kill/pids.max事件均0；grader diagnostics peak678.996MB独立保留。原install/test两个短阶段没有外部采样点，间隙未知，不把离散采样当连续资源全验、共享GPU归因或权重显存证明。

gateway针对exact job revoke/drain，active_requests0；quiescence agent residual0、workspace digest双读稳定。actor_rm RC0，container_left、标签container/network、network/relay失败均空。grader manager实际1建1删，open/supply/cleanup_failures空。原dispatcher RC0与exact unit `rh2-gpu1003-pyd9066-qwen36-a1-qwen-first10-v1.service` 的PID1原journal成功事件（14:24:49.445815 UTC）相互支持；_PID=1、_EXE=systemd、UNIT、request/result/attempt SHA及时间窗准确匹配。已retired unit的not-found/MainPID0/默认ExecMainStatus0不能单独证明退出码；不将manager/PID1终态扩大为宿主所有PID或其他任务清理。

没有当前范围必须追加CPU/模型的具体新缺陷。保留原FP、baseline、raw1和固定材料；题主可结合已核Coder报告形成首轮两模型范围结论，重复门槛和最终用途仍按原约定。JSON保存214逐件原件绑定、482 baseline对象与tar大小/模式、唯一FP、370逐参考分区、完整调用/用量、服务捕获、实际资源和终态。报告静态结构核查不等于新CPU/GPU运行。
