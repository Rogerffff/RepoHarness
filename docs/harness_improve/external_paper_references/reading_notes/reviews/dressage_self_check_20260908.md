# Dressage：作者自查、执行证据与交付范围

日期：2026-09-08。对应[源码精读正文](../dressage_claude_code_step_balance.md)。

**状态：核心文档文本及指定代码路径精读、25项CPU函数探针、作者自查完成；原图／真实训练／分布式复现和独立review未完成。** 这是一项用户明确批准的代码专题（上一轮任务2），不是新算法立项，也没有为其他线程更新总完成数。

## 1. 固定事实边界

Dressage：`3e3142fe8ea07e4504c3b20a936a4c201a3de44c`，2026-08-27。

slime submodule：`aaf5c2092b01219fa0d5c2d323741d409086ca32`。

RepoHarness读取基线：`32b615c4e4f869b448174e5974e7a8d29fc4612c`，分支`miles-migration`。提交时以远程最新head为父节点，只增加本任务专属文件，保留其他线程工作。实际写入commit在最终交付回复给出，不预填一个尚未存在的提交。

主来源为官方README、SWE-Claude实验说明、training guide、Step Balance报告、固定代码和既有测试。不以搜索镜像、旧Pro摘要或动态main链接替代一手事实。

## 2. 阅读覆盖与尚未完成的部分

三份核心guide/report文本均完整读到末尾；README为架构／配方概览。核心同步脚本、SWE generate、sync rollout、multi_segment、reward_post_process、converter、sample writer和两个Step Balance主实现按完整文件阅读。Proxy/BBS、fresh evaluator、generation controller和slime后端按正文所列范围与函数追查。

并未声称逐行阅读所有MOPD、TQ、Claw、Harbor、多agent与底层缓存代码。源码topic的边界以正文§1.2为准，不能借“全部后训练”模板将未读分支自动标为完成。

原图访问失败的范围已保留：Step Balance workload distribution、metrics、engine deviation、utilization/heatmap，以及SWE训练曲线。只使用正文和README明确给出的数字，不做图上精确读数。没有使用OCR，没有把未成功下载的文件写成已保存附件。后续补齐原图即可定点复核，不必从头重读源码。

## 3. 本次核验中实际修正的解释

| 问题 | 容易产生的错误 | 最终处理 |
| --- | --- | --- |
| 同步与异步 | 看到项目有fully async就把主Claude/SWE脚本也这样描述 | 脚本实际train.py+colocate+sync，整batch屏障保留 |
| 节点数 | 文件名4_node代表实际四节点 | 默认回退1节点；区分配置、文档与运行事实 |
| reward归一化 | 不除组内std等于没有优势标准化 | 下游还默认masked whitening；分开两个开关 |
| 训练行数 | segment增多等于独立轨迹增多 | anchor按parent、优势按group、分母按instance |
| Step Balance得分 | 压力分数就是剩余秒数，10%阈值必然抵消迁移成本 | 无量纲启发式；校准主要约束路径readiness |
| 缓存 | 完整input_ids表示必须full-prefill，或LCP表示必然cache hit | 完整请求与实际命中分开；SGLang负责恢复 |
| 局部deltas | fetch前revision就是engine逐请求ack | 是观测近似，不是精确逐请求确认 |
| 预留字段 | 报告的生命周期token预算完全对应当前scheduler | `_ReservationEntry`仅scoring fields；保留文档—代码差异 |
| 版本fallback | 没候选即全局拒绝；或router fallback就意味着无版本检查 | scheduler有fallback，generation controller另有expected-version校验 |
| 首样本None概率 | converter反例直接证明正式SWE链有bug | 深追失败helper发现使用[]；追加实际格式反例后降级 |
| 评分隔离 | fresh sandbox即所有失败reward可信 | 某些grader网络/超时被转成0分；与ABORTED分开 |
| 性能成绩 | 39.4%–64.2%来自真实RL质量改善 | 独立同步n=1、8engine调度对照；不和+5.2pp模型结果合并 |
| 默认迁移阈值 | 三类工作负载均采用.1 | A/B=.0，C=.1 |
| 未来方向 | 报告出现MILP即已经实现 | 正式路径仍single-step greedy；MILP/path-level列future |

这些是维护判断的过程，不是发现十四项“重大bug”。其中一些是设计取舍、接口前提或证据强度问题。

## 4. CPU执行是什么，具体没有测什么

脚本：[dressage_cpu_probes_20260908.py](../checks/dressage_cpu_probes_20260908.py)。

输出：[dressage_cpu_results_20260908.json](../checks/dressage_cpu_results_20260908.json)。

实际环境Python3.13.5，CPU，numpy可用。三个GitHub原始源文件在本地恢复后，以Git blob对象哈希核对，全部与固定版本相同：

- greedy：`8d1bfe709461e29ee556873b6ceb29ba2edb2b21`。
- reward_post_process：`4b47ae8a944af45354cf993d4170f79d8f098941`。
- convert_samples：`646dee74c2b0c410f7cca1b41f57cba60ef48253`。

直接加载这三个源模块，不执行heavy package initializer。Sample为显式轻量替身；transport模块仅提供源代码登记的metadata key。没有真实TQ存储、Ray、SGLang、Mooncake、Megatron、沙箱或外部CLI；不把它们称为被模拟验证通过。

结果：**25 tests，0 failures，0 errors。** 1–11检查路由纯函数；12–16检查anchor/reward；17–20检查分母／身份；21–23检查异构数据与互斥开关；24是采用真实分母函数的加权代数；25使用正式失败helper的输出格式，排除不恰当的主路径bug外推。

特别说明第21和第25项：

- `remove=True, logprobs=None`在converter边界会造成首行决定字段是否存在，这是已执行反例。
- 正式`_mark_no_grad_failed`使用`logprobs=[]`，不是上述输入。第25项按此格式构造测试；heavy worker本身未运行。
- 因而最多得出“异构输入需要明确前提”，不能得出“作者的SWE训练一定丢失logprob”。

也没有把prompt-pool分母等式当作分布式训练证明：pinned reducer会clamp到1，实际whitening、CP/DP和optimizer仍是额外边界。

## 5. 项目建议如何受到约束

正文只提出成本分解、固定轨迹语义对照和缓存恢复微基准三类候选。RH2已定的miles消费时staleness、faithful DIS分母、fresh grader与控制面投影不被本篇改写。

不建议立即复制整套Step Balance，也不将四处静态风险自动变成PR。提交上游前仍要确认更新版本、已有issue/PR、维护者意图及真正可达的最小复现。本次未进行完整维护历史审计，不对上游发送issue、评论或PR。

## 6. 文档检查与后续独立复核

本地检查引用定义、导航锚点、数学块与代码围栏、内部新建链接、JSON结果及Python语法；复算+5.2百分点、3.19h→2.08h的时间减少／速度比。源码副本不随文档提交，读者可对固定checkout重跑探针。

本线程没有独立子agent工具；没有使用虚构reviewer或沿用前两批“独立审查通过”标签。建议独立复核优先查看：

1. 文本性能数字与原图的一致性，以及headline采用的n=1、阈值和硬件条件。
2. reward mean-centering→masked whitening→prompt denominator的实际后端调用链。
3. fresh-grader异常是否应该作为模型负样本，以及受影响任务的真实比例。
4. source sandbox生命周期、版本guard与router fallback是否被完整解释。
5. CPU反例对应的真实生产者前提，避免以人为输入报告默认路径缺陷。

本次仅交付正文、本自查、探针脚本及结果四个专属文件。共享索引由汇总线程维护，防止并行覆盖。
