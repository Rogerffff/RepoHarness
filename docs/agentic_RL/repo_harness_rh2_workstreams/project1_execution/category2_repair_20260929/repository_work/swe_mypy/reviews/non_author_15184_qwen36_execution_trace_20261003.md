# mypy15184 Qwen3.6 首臂：非作者生产链与身份追踪

日期：2026-10-03。范围：`gpu1003-mypy15184-qwen36-a1` 的题级执行、身份、正式评分和清理。按 `review-standards.md` §10.4 担任 Production Tracer；只读原件并本地重算SHA、解析JSON/tar，不执行SSH、Docker、CPU测试或模型。本次唯一写入为本报告；10174及15184 R10冻结报告保持原样。

## 结论

**本首臂的执行证据可收口：新版公开题面与brief确实进入CC首条实际生成请求；原FP和1422条完整基线自洽，评分只投影1条源码；正式3个F2P和2个P2P全部执行、解析并通过，安装成功，reward1.0；求解进程、session、actor与grader两层清理均正常。** 没有发现本题请求、材料、候选或评分的具体身份矛盾。

该结论限于一次普通探针。它不证明整个配对请求完成、完整mypy回归、训练准入或候选语义已独立审查。**运行时checkpoint精确身份尚未由本题证据确认**：历史下载revision、复制校验、engine挂载和本轮service绑定能形成来源链，但本题gateway audit仍明确`checkpoint_identity_verified=false`。最小接续是补GPU已有checkpoint读回并完成既有Coder首臂；本报告不提出新通用gate或重复运行。

## 原件与封存范围

以下路径从仓库根目录起算。

| 别名 | 原件入口 |
| --- | --- |
| `R` | `runs/ordinary_gpu_probe_20261002/remote/` |
| `G` | `R/queue_v13/results/gpu1003-mypy15184-qwen36-a1/` |
| `P` | `R/prepared_swe_three_code5_v1/mypy15184/`：镜像准备、source/wheel census、prepared/private。 |
| `C` | `runs/ordinary_gpu_probe_20261002/frozen_code_v5/`：本次冻结代码和材料。 |
| `CPU` | `runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/`：已验R10正式矩阵原件，只用于材料与基线对照。 |
| `GW` | `R/services_v11/qwen36/gateway/gpu1003-mypy15184-qwen36-a1/`：本题实际40次生成请求、响应、SSE、usage和session关闭。 |
| `AD` | `R/services_v7/qwen36/adapter/gpu1003-mypy15184-qwen36-a1.turns.jsonl`：本题40条adapter生成记录。 |

独立核`R/gpu1003-mypy15184-qwen36-a1_closed_manifest_v1.json`：字节SHA为`63f34446034872a4433719ade72a7ba15d1be095226e317933d95a337f4db367`，95个文件均存在，SHA/size全部匹配，总封存字节21,307,412。执行方readback同样记录95件匹配，但本报告结论来自本次重算和原件对账，没有把其审查待办标签当成通过证据。

95是封存文件数，包含共用配置、其它题purecheck、无关准备失败记录和公共资源窗口，**不是本题95个结果或95份独立验收**。只对本题相关内容作题级解释，不对同窗口DVC/Conan执行结论背书。closed manifest本身保留`paired_request_closed=false`、`other_jobs_not_claimed_terminal=true`和资源采样缺口。

## 请求、公开交付与运行代码

题主固定请求`runs/ordinary_gpu_probe_20261002/request_copies/swe-mypy15184-nested-nominal-v2-20261003.623bc39612a9.json`，重算SHA为`623bc39612a9812e92b3c5ec218480e916e3c4dae219c4e4f17d7e85056e993e`。终态snapshot的`original_request.owner_request_sha256`、`P/image_readback.json`和固定payload绑定同一值。snapshot里调度外层请求SHA为`0b0b84a51058a46c9f34bec653797e58112d26afa7df3c5a26262ee9f308bece`；这是包装该题主请求的队列对象，不是623bc…身份被替换。

本次另对终态`original_request.input_sha256`中与本题准备、目标消费者、入口和配置有关的56个本地成员重算SHA，全符；不据此把其它题输入也计成本题结果。调度入口`C/rh2/experiments/ordinary_gpu_probe_20261002/serial_dispatch.py:98–141`核固定输入后启动entry、等待进程退出，rc0写`evidence_ready`。该状态表示证据就绪，不是候选语义验收。

| 运行项 | 原件记录与本地冻结源SHA |
| --- | --- |
| snapshot | `code_v5`；终态command使用该路径。 |
| ordinary entry | `a1efff44dc2cbedfc81d93b2da8d84a92f6c9c88b15c2a10bf96db2026a4e82c`，与attempt的自报值及本地冻结文件相同。 |
| shared solve entry | `00ca849909150de02769f297374a9bbfacf2746347c425474775d9c3e22a04f9`。 |
| serial dispatcher | `cb435f7390d9aeba3bad51efabf808634668263e9dfbcffae96f50a4b8f90f10`。 |
| grading manager | `1783533e1e3b66a57fcaa5a599a1da4f8e4e886318e24f040c6df91f294c1c1e`，与已验R10冻结manager逐字相同。 |
| code_v5 source manifest | `37688573eeb6cd9ce11cc89eb55601fa8127feac7ed753f131bdf86ababed814`；这是代码快照身份，不是对577个文件作新的全量审查。 |

code_v5是组合冻结树，不是整树等于R10。目标registry、effective statement、effective test patch和manager逐字与R10相同；其余消费者有发布增量。本题prepared public/private字节、材料identity、scripts和五引用另行精确对账，未把组合说明替代本题消费证据。

公开交付沿`entry.py:61–83`从公开spec和登记brief构造prompt，`:305–330`替换solver实际prompt并保存，`:102–123,370–372`从实际网关请求核交付。独立解析`GW/requests.jsonl`第1条：首个user有两个text block，一个是CC日期reminder，另一个**逐字等于1830字节的`G/solver_prompt.txt`及`G/attempt/prompt.txt`**。题目block SHA为`2efeb37e86cb65e228a92d9623c73c31286bf5eaccacbff2935def2bd75ec8de`；若按含reminder的整个user content canonical JSON计算，则SHA为`824077298f466db04d57ba5c2601e1ee0cb428a4377c959a4c064e4109349581`。两者口径不同，不混写成一个“首消息SHA”。

该实际题目block包含新版a.py/b.py/t.py的两模块例和完整中性brief，对应statement SHA`c17659095d0b4ab71caf2fab52dfaa52e9da009212381a7dc46053c015499178`、brief SHA`0fe106b96bd74d6f28ba226bdc2c8be1b67326048509a5636b8d600e35f3d1e7`。不存在旧失效示例、隐藏嵌套评分节点或gold内容；brief公开的`testAssertType`命令本来就是允许交付的公开回归。这里的“无私有内容”限于首条交付和所核材料，不声称本报告完成整条轨迹泄漏审计。actor prelaunch的实际mounts/binds为空，工作区仅得到公开bundle；private host view留在宿主可信面。

## 镜像、UID、完整基线与候选

| 身份 | 本次值 |
| --- | --- |
| task / physical attempt | `swe_gym_lite::python__mypy-15184` / `gpu1003-mypy15184-qwen36-a1#p1` |
| immutable base / actual HEAD | `13f35ad0915e70c2c299e2eb308968c86117132d`；tracked dirty为空。 |
| source manifest digest | `sha256:affb925329f2dfb2173482c64a1b65648b250777b66b0d7417ee5340fce74835` |
| 实际actor/grader派生image ID | `sha256:cda77e2d613176919d3c6fb8a0f1aae952a1f77a5d0170602db93c432867c025` |
| public / grading / environment | `77b85678b3f20ef5689e4a9b646518ae1247407ff44b250803563c11dce3ea7e` / `3a3c4e78c7dc1b1dce9187d36d00079c4d08621f7019140e6544e77b9f2db4bf` / `de06cc63c20f88a4691b7037dfeaeae5f31c4dc13f09cf703161cf6df2954f1e`（均sha256）。 |
| materials / scripts | `bf000616fc92f2d7869bdb2039ab1fe0d9167e507a5bb15e6c5987ab033d8053` / `eb6990fb1a94e807ee047e7e36029d27f37411fb590c4a36a33e42a6d8a68364`（均sha256）。 |
| FP canonical digest | `sha256:41adba1ea7056b5ac16b09ebdcb69ac59954c0f6ea6243cf5855adfb7e57c4aa` |
| baseline canonical digest | `sha256:fdd59f846a872a5fb2680de446faf5d8a286db2237559c43c8b43874e82df1a5` |

source manifest digest、source image ID和派生image ID是不同字段。`P/actual_image.json`的原inspect得到cda77…；source/actual两份完整准备census的1620项逐项相同，source层保留，Dockerfile只COPY wheel并设置离线pip。该准备census包含目录/Git，不能与后续1422条scoreable baseline相加或直接比较总数。已验CPU image为76b5…，本题没有借用其ID冒充GPU实际image。

本次独立对九wheel逐个核题主请求资产SHA/size、本地资产字节与`P/actual_wheel_census.json`，全部一致；目录root:root0755、文件root:root0644。九资产为packaging24.1、wheel0.43.0、tomli2.0.1、typing_extensions4.12.2、setuptools72.1.0、types-typed-ast1.5.8.7、mypy-extensions1.0.0、types-setuptools74.0.0.20240830、types-psutil6.0.0.20240621。它们是离线editable构建供应，不是完整依赖锁。

actor实际`facts/prelaunch.json`和`agent_env_facts.txt`核UID/GID54321、testbed Python3.11.9、2CPU/4GiB/零swap、无宿主bind、root隐藏、仅relay可达；不是仅凭profile声明。grader候选安装/测试由冻结manager `:3531–3559`以候选user执行；默认profile UID54322，正式观测prefix owner为54322。没有新增逐命令`id`观测，UID结论来自本次冻结调用路径和已有观测。可信setup不以root导入候选包。

本次独立完成：

- 重算原FP与baseline canonical digest，验证FP两个entry的base64内容SHA、execution/physical/runtime血缘。FP修改`mypy/messages.py`和公开测试文件；projection精确只含`mypy/messages.py`。模型增加的测试case不会进入评分控制面。
- tar有1422个常规文件，逐个内容SHA和规范化执行位mode均对应完整manifest；独立解析actor baseline和fresh grader census，两份都逐条等于manifest，排除路径摘要相同，两份census字节也相同。不是只采信`baseline_rebuild_passed=true`。
- 与CPU原件对照：1422条baseline entries、policy及其它字段全部相同，唯一差异为runtime image digest。prepared prompts、rollout views和private host view也逐字相同；private文件SHA为`1ce37a96ae9140654e5604cc6f2570345a92928315b99131cb99b0ce6e2946ff`，prepared manifest只因时间戳不同。

`entry.py:224–289`由原FP和完整baseline构造FrozenDeltaSource、建立可信projection、直接调用正式manager。review diff仅供审阅，没有用于评分重建。投影源码SHA为`2ca8bce8da916a44cf9ef4e598085f1dcd9575a0bf1c4cba71869f6f0ebe330f`；源码变化是在`assert_type_fail`使用既有`format_type_distinctly`成对生成诊断。这里记录候选身份和实际投影，不替代候选语义审查。

## 正式安装、五参考与双层清理

`G/grading/eval_logs/evallog_gpu1003-mypy15184-qwen36_11516763.eval.log:396–468`执行原vendor安装串：test requirements、editable mypy、hash-r。隔离构建依赖和editable wheel成功，卸载原1.4.0+dev后安装候选dirty版；diagnostics `install_failed_commands=[]`、candidate exit0、install末码0、completed=true、partial=false。**安装成功有真实构建日志支持，不仅是段末码0。** 本次没有10174窄验那样的owner额外安装预热。

可信setup恢复/应用登记评分patch，setup/protect均1，评分文件2、保护目录6、缺失0。runner摘要前后均`bffa1d1e04c07d52b4d5db5941f0d97a8c71a68e29cca90c4bf5671ea66e1548`。`candidate_prerequisite=null`，新增其它题前置分支本题未运行；`supply=null`，走原单候选脚本。

同日志`:478–499`精确collection并执行5个node，5 passed，test rc0。独立对照GPU diagnostics与CPU gold：revision `mypy15184-nested-nominal-types-v2`、registry SHA`7abfdf350875e5d28c679ac196f20c8a44efdce184fa7be00ddf97cb2009740c`、材料/scripts、command和四partition均相同。

| 分区 | 实际节点（省略共同`mypy/test/testcheck.py::TypeCheckSuite::`前缀） | 结果 |
| --- | --- | --- |
| original F2P | `check-assert-type-fail.test::testAssertTypeFail1`、`…::testAssertTypeFail2` | 2/2通过。 |
| added F2P | `check-assert-type-fail.test::testAssertTypeFailNestedNominalTypes` | 1/1通过。 |
| original P2P | `check-assert-type-fail.test::testAssertTypeFail3` | 1/1通过。 |
| added P2P | `check-expressions.test::testAssertType` | 1/1通过。 |

五个引用success集合与references精确相等；failure/missing/skipped/unaccounted全空，parsed5、outside-segment0。report resolved、reward1.0、F2P3/3、P2P0失败/2。顶层import指向`/testbed/mypy/__init__.py`；没有关键模块在pytest进程内的源SHA观测，不能把可信投影/安装日志改写成逐模块运行时SHA实测。`resource_facts=null`、`RH2_OBS_PKG_VERSION="?"`、`env_qualification=absent`按原件保留。

求解轨迹末条CC result为success、is_error=false、stop_reason=end_turn；harness exec实际exited/rc0、日志complete、619376字节、stderr0，termination completed。执行中8次tool_result_errors不等于进程失败或预算截断。`launch_facts.launched=null`按原样保留，实际生成40次、完整轨迹和exec状态另行证明已执行。

本题生命周期顺序为：actor求解 → pre-drain stop确认agent residual0 → session revoke/drain且active_requests0 → quiescence确认无agent进程及工作树双读稳定 → export原FP → actor/relay/network清理 → 网关audit → fresh grader完整基线、投影、setup、安装、五参考 → manager close。actor于`00:22:07.807754Z`清理结束；grader报告于`00:23:44.651686Z`生成；外层entry于`00:23:45.528475Z`退出0。

actor cleanup中container_rm0、container_left空、relay/network failures空、按本run标签查询containers/networks均空；grader manager记录1建1移、lease1、open containers/supply/cleanup failures均空。外层调度rc0与两份清理均一致。共享模型engine/adapter是驻留服务，不属于本题应移除的actor/grader容器；不据此要求服务退租。

## 模型身份、预算与计量的真实范围

本题40个请求连续seq1–40，requested alias均`slime-actor`，gateway `model_sent`均`Qwen3.6-35B-A3B`；40份响应均HTTP200、attempt1、stream_error=null，reported alias均`slime-actor`，39次tool_use、最后1次end_turn。adapter同session有40条记录。**这证明传输路由和生成完整性，不直接证明权重checkpoint。**

已有来源链：`R/bootstrap/model_revisions.json`及download36.log记录Qwen仓库revision `995ad96eacd98c81ed38be0c5b274b04031597b0`；`R/storage_copy_qwen36_v1/status.json`记录37文件复制后SHA/size校验、download manifest SHA`32bd30f61860366b3783eabc9d75bee0cd28c474d9c07de8be8d9ae60a4552ab`、源目录保留。对应copy脚本检查该revision，并核目标全部文件及源/目标manifest。engine历史inspect显示容器`a5491775…`只读挂载同源模型目录为`/model`；config_v13实际service绑定保留同一engine和adapter`a97a433e…`。SGLang ready readback记`model_path=/model`、context196608、BF16、TP1、max_running_requests1，revision字段为null。

上述原件支持“按该历史checkpoint来源配置并沿已保留服务生成”的有限推断。37文件copy校验发生在`2026-10-02T18:44:06Z`，不等于本题`00:20Z`服务对实际加载权重再次读回；本地也没有本次engine加载时源模型文件完整hash原件。不得把目录名、force_model或响应alias提升为`checkpoint_identity_verified=true`。现有GPU补已有运行时读回即可，不要求重跑模型；若未补，继续明确保留此来源缺口。

实际40个CC请求`max_tokens`全部65536，adapter配置与本题输入声明一致。CC汇总的`modelUsage.maxOutputTokens=32000`是汇总字段，与实际请求口径不同；本次最大生成仅569 tokens，没有触碰该边界，不由此判截断，也不声称宽预算压力验收完成。context196608、turn240、wall10800、session请求1024和adapter idle14400为本轮配置；本次40turn正常结束，无context-recovery请求。idle TTL未在runtime config观测（input_check留null/config_only），短运行未验证四小时回收。

| 计量 | 结果与口径 |
| --- | --- |
| token | gateway响应usage、adapter与CC汇总都为input528184/output6067。输入为40次请求累积，可重复包含上下文，不能当唯一题面长度；三份计量不相加。单次最大prompt21402。 |
| 回合/工具 | 40次生成、39次tool_use响应；39次工具调用为Bash27/Read8/Edit4；90个assistant事件不是90次生成请求。 |
| 时间 | 外层job约207.459秒；solve62.946秒，CC59.483秒/API39.784秒，gateway请求累计38.788秒，grader96.780秒。这些含嵌套阶段/不同起止点，不累加为总耗时。正式candidate安装2.572秒、测试段0.862秒属于grader内部。 |
| 资源 | closed窗口16个约15秒间隔样本，实际样本`00:20:12.151732Z–00:23:58.179033Z`，manifest包络`00:20:03Z–00:24:00Z`；间隙未知。按本题run/name/image筛出actor7条、relay7条、grader7条。最后样本含Conan，排除它的容器数值。 |
| 采样峰值 | actor memory.peak最大882.262MiB，grader444.004MiB，relay26.457MiB；三者分别记录，不把跨阶段峰值求和。所见样本oom_kill0，不证明所有未采样时刻。GPU字段是宿主级采样，不能归成本题独占GPU消耗；grader ledger resource_facts仍null。 |

## 最小接续与停止条件

本首臂已具备题级身份、公开实际交付、原FP正式消费、安装、五引用、退出和清理证据，停止该边界的重复审查。有限未闭项如下：

- GPU执行侧补已有运行时checkpoint来源读回；目前只按历史来源链和本轮路由描述，不宣称精确加载权重已验。
- 同一请求登记两模型各1次；这里只验Qwen3.6首臂，Coder臂另需自己的原件，`paired_request_closed=false`维持。
- 原候选方法与语义交题主/语义审查处理；reward1.0不能替代该步骤。无需为此修改旧R10报告、重复CPU矩阵或增加普通探针资格gate。

关键原件字节SHA：FP `cc6f3bcf029594bbf452f59273a3e1ab9cf669f7873b61f72c54181e62a5ecaf`；baseline manifest `1019f5a9d08c1cda7676a9385f6a472613d391d7bc6c841c363466819a9ec689`；baseline.tar `448afa99a8b55d88a17b2efd11058a53ae3487b18f654637a58a4d4d24c053fa`；两份census `5d6f0d161a576c62b4161ad3114dfa586e579f4a5ca5485b053fa021984f3fd5`；projection `bd6c010827f6e7ebe55d278aad28f2679f0c22ac3582246713fae12425f877cb`；eval.log `f1ab4a415ad24520c49801cb8136a0f21cfc40db7fd80aa4c8870d75df0c05f5`。其余SHA/size留closed manifest逐文件清单，不重复铺陈。
