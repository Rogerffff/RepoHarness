# Conan14177：Coder 首次探针分析

2026-10-03。请求 `swe-conan14177-r11-briefv2-20261003-v1`，作业 `gpu1003-conan14177-coder-a1`，模型 `Qwen/Qwen3-Coder-30B-A3B-Instruct`；R11、brief v2、`probe-wide-v1`。

**raw1，2F＋10原P＋1移入P共13个可信参考全部通过。题主与非作者窄核确认生产候选符合公开verbose目标，执行独立报告已回；模型纠正首版KeyError，也正确移除了自己新增的错误断言，原13公开测试未改。另记非阻断P2：demo实际只显示首份文件的尝试日志，模型却声称两条都已展示。Qwen3.6首次尚缺，成对请求保持活动。**

## 原件与评分范围

[当前固定请求](probe_request_20261003_r11_briefv2_v1.json) SHA `478ba02b7ead3aabda7a6493694434c350a694c1600e0f71851eabef5d8ffff7`未改。题主核121件、11,667,817字节闭合原件SHA／大小；完整原issue与brief v2在实际首gateway请求中按原字节出现，CRLF保留，仅去brief末尾换行。原brief v1模型前取消的历史原件保持，不计一次模型尝试。本次实际目录筛选运行也已补足原静态入口核查的运行边界。

原件根为 `runs/ordinary_gpu_probe_20261002/remote/queue_v19/results/gpu1003-conan14177-coder-a1/`，闭合清单为 `runs/ordinary_gpu_probe_20261002/migration_20261003/gpu1003-conan14177-coder-a1_closed_manifest_v1.json`。完整diff共4,986字节，SHA `5e90bae63e77d0583063207bfdd940e5af98f194379488bbcb40918683b1f617`；从实际baseline archive取原件、核公开base并隔离应用完整diff，三项内容、模式与FrozenPatch相符。

| 原候选路径 | 内容 | 实际评分投影 |
| --- | --- | --- |
| conan/tools/files/patches.py | opt-in日志及参数说明 | 保留 |
| conans/test/unittests/tools/files/test_patches.py | 新增一个公开文件名mock测试，原13函数AST不变 | 排除，恢复并保护固定可信测试 |
| demo_verbose_patches.py | 新增46行演示，捕获缺文件异常 | 保留；正式评分命令不执行它 |

不能把原FP的测试改动写成不存在，也不能猜测demo已被剔除；没有测试识别或评分绕过，不按改公开测试自动判作弊。FP canonical digest `41c9276e4c4748dca5f6c56f77ba7e0f16c0617a4e28745e99f164ca0afd2495`，实际baseline canonical digest `6fdad6e91c67e236fae68334aaa479344f4669406564d26b032f9c5b466497a3`。

题主逐可信key核原eval：两个multiple节点、十原P节点和移入P的单描述节点全部PASS，无missing／skip，安装0／测试0、完整13 passed尾部；eval SHA `6d5cf8d328fc83e84683b9a217f78bd27d2390d8f413f74f57b9ecf1da6bebc5`。[执行独立报告](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/conan14177_coder_a1_execution_review_v1.json)按执行／运输范围复用，实际actor镜像 `4ca5aeae4e588c89008e6ca335500ffa71aea77bd6eab0b7491d514534696bb0`，actor／grader收尾及gateway drain完成；不把它当候选语义、全程容量或成对请求完成的证明。

完整SHA与指标见私有目录 `runs/category2_repair_20260929/conan_cpu_20261003/probe_analysis_14177_coder_a1_20261003_v1/owner_readback.json`／`tool_events.json`。下文行号均指原 `attempt/trajectory.jsonl` 的一基行号。

## 七个维度

### 方法

最终实现 `apply_conandata_patches(conanfile, verbose=False)`；True时按entry顺序输出原`it["patch_file"]`，然后调用原`patch()`。省略／False不新增Applying行，但原type／description及无补丁提示仍可输出，不能说默认绝无日志。文件名日志在实际应用前打印，表示尝试；异常仍向外传播，不单凭Applying证明成功。

保留版本字典筛选、列表输入、拷贝后pop、不改变conandata、base_path／strip／fuzz及额外kwargs。`patch()`、PatchLogHandler和export helper AST与原base相等；单描述／类型日志未替换为文件名。True时为patch_string加一条说明，原字符串应用不变，公开要求没有规定字符串文件名。位置／关键字True均符合公开调用方式。两个可信multiple节点独立核默认、文件顺序、metadata、版本、输入不变和记录型应用调用；这些调用证据不是两份真实补丁文件的磁盘修改实验。

### 定位

首工具搜索patch路径；工具2读对生产源码，随后读公开exports、unit和functional测试。首次相关源码读取距第一模型请求 **2.071秒**；正确目标文字行71在5工具后、第六响应完成 **9.920秒**，是该响应完成上界，不是首次形成判断的精确时刻。

定位方向正确，但初版在`entry.pop("patch_file")`之后仍读entry同名键；默认13公开测与一个functional通过都没有覆盖True缺陷。新增True测试暴露KeyError后，行140改读保留的原`it`，才使新文件名测试通过。正确目标与首个正确实现分别记录，不把早期默认PASS视为新功能完成。

### 工具与纠错

22次实际工具：**Bash12、Read5、Edit4、Write1**。原轨迹保留两次pytest非零：行131为两个新verbose例KeyError，行170为修正生产后另一个新例的输出断言错误。后者在True下仍要求只存在旧description整行，忽略新增的两条文件名；行192移除的是模型刚写的这一个错误新例，保留原13测试和新的两文件名例。题主核最终完整diff／原函数AST，没有删旧回归或弱化生产行为来换PASS。

Demo未创建输入文件，两次调用都在首文件失败，异常由脚本捕获，故行261工具正常退出。`is_error=false`只说明命令正常收尾；不代表补丁成功或两文件均被执行。行266模型却贴出第二条未观察到的日志并称输出完全匹配。这个P2归验证陈述，生产代码和可信节点另有依据；保留原轨迹，不改写观察。

### 并行

23响应前22各一个工具，最后结束，无实际工具重叠。生产源码定位后，公开exports／unit／functional的只读检查可以独立进行；本次未并行。CC／adapter多工具并发支持未独立建立，不能从串行样本判并行能力。测试共用工作树、客户端配置和缓存，不把同时运行这些pytest直接列为安全机会；编辑后的验证及纠错有真实顺序依赖。

### 验证

| 轨迹行 | 实际结果与范围 |
| --- | --- |
| 88→92、101→105 | 已编辑初版后原unit13P、单functional1P；未覆盖True，非修改前失败复现 |
| 127→131、153→157 | 两新例2F／13P暴露KeyError；修正后新文件名例1P |
| 166→170、192、205→209 | 错误新增断言1F／14P；删除该新例后最终unit14P、0.16秒 |
| 218→222 | 公开目录`-k patches`实际62 collected／48 deselected／14P、0.20秒；与上项重复，其他模块先收集后筛选 |
| 231→235 | 三个functional patch flow全部P、1.06秒；包含先前一个例 |
| 257→261 | Demo只输出首Applying及预期缺文件异常；无成功断言，不验证第二文件或实际应用 |
| 270→274、283→287 | 联合unit＋functional17P、1.07秒，同14＋3不叠加；testbed Python和source导入身份确认 |
| 可信grader | 固定2F／11P全部P；新增公开unit不贡献分数，单描述节点仍参与 |

最终14unit＋3functional通过有原件支持；“all tests passing”只在这些选择范围成立，不能扩成全仓。两个文件日志有mock新例及独立可信节点支持，真实True两文件磁盘应用没有由demo建立。没有修改前失败复现，重复13／14／17结果不累计成更多独立覆盖。当前证据足以判本候选语义，无须为错误demo陈述重跑旧CPU或扩模型采样。

### 效率

求解 **55.135秒**，harness52.307秒；CC51.682秒／API44.056秒，差7.626秒不是纯工具时间。23回合累计输入 **347,827**／输出 **5,736 tokens**，最大单请求输入22,717；CC、gateway和adapter读回一致。首次搜索、两轮新例纠错有实际作用；重复同选择unit、冗余缺输入demo与长重复总结可以减少，不据单样本比较一般能力。

Git清理15.259秒、可信初始化7.625秒等环境准备单列；评分总93.305秒、测试2.075秒、评分reset16.179秒／prep0.328秒／队列0秒，不混入求解耗时。23实际gateway请求输出预算均65536，CC32000为元数据，不冒称实际限制降低；声明196608上下文／240回合／3小时未触及，不能证明极限容量。CC费用1.882535美元是内置估算，非本地GPU账单。

### 结束与稳定性

原件为`completed/success/end_turn`、harness0，23gateway响应HTTP200且无stream error、截断或拒绝；actor、grader和gateway收尾闭合。执行采样不推断全程峰值、容量或利用率。仅一次Coder，有效raw1支持本次生产候选，不建立稳定成功率或训练资格。Qwen3.6首次与整项回执尚缺，不能核销成对请求。

## 处置

题主已全文读回并采纳[非作者语义窄核](../../reviews/non_author_14177_coder_a1_semantic_review_20261003.md)，SHA `abf8a8222eb42d64943e2ebec9a744f87ff62e2b0409da9be423f29def6f1f4b`。生产候选无阻断；P2／C14177-A1-S1是demo观察被夸大，只需在题级分析准确限定验证范围，没有发现当前材料缺陷或相同材料Qwen阻断。继续等待Qwen首次和整项回执，保持claimed、不ACK、不清活动指针；覆盖优先，普通追加采样暂缓。本题当前无CPU作业，未来有具体修订才另核资源需求。
