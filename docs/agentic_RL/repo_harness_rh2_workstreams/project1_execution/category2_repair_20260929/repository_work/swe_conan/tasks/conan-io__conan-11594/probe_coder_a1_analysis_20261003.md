# Conan11594：Coder 首次探针分析

2026-10-03。请求 `swe-conan11594-r12-briefv2-20261003-v1`；作业 `gpu1003-conan11594-coder-a1`；模型 `Qwen/Qwen3-Coder-30B-A3B-Instruct`。固定 R12、`conan11594-private-test-v1`、brief v2、`probe-wide-v1`。只覆盖该模型一次尝试。

**raw1，2F／4P、7个完整节点全部通过。题主核查及非作者语义窄核确认候选修复了默认测试目标，并保留 Ninja Multi-Config 的配置传递，未发现绕过或生产阻断。GPU执行独立审也已返回。模型自身验证较弱，且无关pytest出现被命令掩盖的失败。Qwen3.6首次尚缺，整个双模型请求仍在活动，不能按单臂核销或判定稳定性。**

## 输入、候选与评分依据

- [固定请求](probe_request_20261003_r12_v1.json) SHA `274c7e394eda8da6b3dd1f2161754338a721bc4fa71f300ed9a5db237a65b581`；评分材料身份 `fe68e56946f2eeab35c4c335f317ef2a17fb27da4af54024b3d837f2548788a4`。原issue未改，实际actor与grader均为固定config ID `f3b8d6671607e167fa549c05faa860345e5256c8f834a6a711447df9dce6839f`。
- [闭合原件清单](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/gpu1003-conan11594-coder-a1_closed_manifest_v1.json) SHA `c3065e88ca6689b0be6ca6520a46d92d6864f2b7215a1d2ba930b655feece116`；题主重新核对145件、14,818,108字节的SHA和大小。此清单含Q17的共享输入原件，不把其它任务的文件计为11594模型尝试。
- 实际第一条gateway请求完整包含原issue及当前brief。prompt SHA `5de84366859c5a995d424db0543d2fcde183d102d52f13197f9d98cae2c3e699`；brief SHA `c0ab743d03d433b9fd9f23b5d152430592f3ccb38cf703acec45a45dcddaa5f7`。按原字节核对，原issue的CRLF保留；组装仅去掉brief文件末尾换行。
- 完整候选只改 `conan/tools/cmake/cmake.py`。原diff SHA `ca6c034cf2cea1390c5267d6dacd2b9f58c83a4b5b87b9172b5befadc2d7e423`。题主从实际求解前baseline archive取源码，与公开base逐字节核对；在临时隔离目录应用完整diff，结果等于FrozenPatch内容，内容SHA `8d1d639cccf643b0305c7b6446bf2a2e1b6fa283b8f8a08ec7187bd2ea1235a2`。可信评分投影包含这一生产文件；两份临时自测脚本已被模型删除，不进入候选，没有测试改动。
- 原eval log SHA `d62545b2db4d41c1a7297e8a31050d939aa425acff056295f3cb29eafdee1ab9`。六个来源参考对应七个完整节点：来源Ninja参考按固定ALL绑定两个节点，不能用其中一个通过替代另一项；其余五参考逐项匹配。安装及测试退出0，无缺席／跳过。新增可信节点真实运行CTest并核Release marker，区别于仅返回目标名称的模拟测试。
- [GPU非作者执行审](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/conan11594_coder_a1_execution_review_v1.json) SHA `4be7e58d6ace46c3969cb3b001792592b232669985044c672e8324b578ad7275`，结论为限定范围的执行证据成立，覆盖公开交付、实际服务／镜像、FrozenPatch投影、完整参考、运输、清理及有限资源；不代替题主语义终审。权重未重新全量逐文件哈希，不据实际启动参数宣称196K最坏容量已测。

题主读回及全工具索引位于私有目录 `runs/category2_repair_20260929/conan_cpu_20261003/probe_analysis_11594_coder_a1_20261003_v1/`，其中 `owner_readback.json` 保存SHA、映射和指标，`tool_events.json` 保存完整文本。原轨迹 `runs/ordinary_gpu_probe_20261002/remote/queue_v17/results/gpu1003-conan11594-coder-a1/attempt/trajectory.jsonl`；下文行号均为该JSONL的一基行号。

## 七个维度

### 解题方法与修法

模型行58正确指出：多配置生成器不一定使用 `RUN_TESTS`，Ninja Multi-Config需要 `test`。行114的唯一编辑使默认目标仅在Visual／Xcode生成器下为 `RUN_TESTS`，其余为 `test`。它保持 `is_multi_configuration()`，没有把Ninja Multi-Config误改为单配置；`_build()`仍按显式 `build_type` 或settings生成 `--config`，原issue的Release运行保持。

`tools.build:skip_test`提前返回、显式target、`cli_args`／`build_tool_args`传递均未改变。None／空generator先由 `is_multi`短路，未引入 `in None`异常；Visual／Xcode沿既有helper的相同判据，Ninja单配置和Makefiles保持原默认目标。源码推导和可信实际Release测试支持根因修复；Visual／Xcode只验证命令选择，未在Windows/macOS真实构建。不将任意未知generator都视为实际支持证明。

模型还读取了legacy CMake helper并指出相似逻辑，但最终只改公开问题及brief所指的新helper。没有测试识别条件、跳过评分或伪造marker。原CPU的noop／gold／drop_config为0／1／0；错配置候选通过六个模拟case但实际运行Debug，新增可信节点拒绝。本次候选与这些对照分别保留。

### 定位能力

工具1全树查 `cmake.*test` 未命中正确helper；工具2按cmake路径找到，工具3首次读对生产文件（结果行40），距第一模型请求 **1.862秒**。工具4读utils，行58形成正确根因判断；对应第五响应完成距第一请求 **3.650秒**，这是包含诊断文字及随后请求的响应完成时间上界，不是产生判断的精确时刻。

四个工具定位根因，无错误编辑后回退。但随后全树搜索、读完整legacy模块、全量列 `is_multi_configuration` 使用增加上下文，未改变核心诊断。不能把快速定位直接外推为一般能力或与另一题的模型比较。

### 工具使用与纠错

共 **21次工具：Bash15、Read3、Edit1、Write2**。模型多次用 `find /testbed -path "*/test*"` 搜测试；由于 `/testbed`本身匹配该模式，实际没有限定测试目录，返回了生产文件、加载器乃至自己刚写的脚本。brief给出的公开测试入口未被使用。`find/grep/head`大范围搜索替代精确路径读取，造成反复无效定位。

工具19（行236）跑 `conans/test/unittests/util/tools_test.py`，使用 `2>/dev/null || echo "No specific test found, but that's okay"`。真实输出被CC持久化，题主从原 `cc_home.tgz` 抽取72,953字节完整日志，摘要为 **1 failed／78 passed／2 skipped，6.75秒**。唯一失败为下载重试测试遇到 `google.es` DNS故障，与本次CMake修订无关，不能归因为候选回归；但外层 `is_error=false`也不能记作pytest通过。

模型可见的2KB预览已含FAILED，未读完整持久化结果，行247说这些测试不直接相关后略过，未诊断或准确披露失败。故报告工具错误0仅是外层标志，纠错在此处不足。它最终清理临时脚本并用 `git diff`确认候选，路径和编辑范围正确。

### 并行调用

22次模型响应中，前21次各请求一个工具，末次最终说明；没有多工具请求或实际重叠。读完当前helper后，utils与有关公开测试是可独立读取的机会，本次仍串行；legacy读取及全树搜索存在必要性更低的开销。现有原件未独立证明CC／adapter多工具调度的可用性，故模型并行能力**不可判断**，不把单工具序列直接判为能力缺陷。

### 验证质量

| 实际观察 | 能支持什么／限制 |
| --- | --- |
| 行170，模块import成功 | 仅导入可用，未执行helper |
| 行192，临时脚本打印七种generator结果 | 复制新表达式并打印✓，未调用生产 `CMake.test()`；不匹配也不会assert失败，不能当生产回归 |
| 行214，第二脚本打印Ninja新旧表达式差异 | 同样只模拟表达式，未执行Ninja或CTest，与前脚本覆盖重叠 |
| 行242，真实公开util测试81项 | 1失败／78通过／2跳过；范围偏离问题且非零被掩盖，未重跑，不计入目标修复覆盖 |
| 可信grader七节点 | 调用实际helper的六种generator命令选择＋真实Ninja Multi-Config Release CTest；2F／4P全部通过，安装／测试退出0 |

模型没有旧树真实复现、真实CTest改后复验、持久化生产回归、skip_test／显式target自测。中间总结行260称“确保所有其它generator正常”，超出复制表达式所证明的运行范围；最终行273准确描述源码改动，没有声称完整pytest通过，但也未披露遇到的测试失败和自测限制。候选正确性由源码分析及可信评分另行支持，不能据raw1给模型自身验证高评价。

### 完成效率

求解墙钟 **39.538秒**，harness exec36.605秒；CC总时长35.996秒，API26.784秒，两者差9.212秒包含工具及控制开销，不能精确当作纯工具时间。求解前Git清理10.118秒、可信初始化10.230秒和容器准备分别列账；可信评分总97.410秒，其中测试2.661秒、评分队列0秒。跨机器镜像续传／load是已完成供应阶段，不能算成本次模型求解耗时；未据时间差编造完整队列或生成时间分解。

累计输入 **283,679 tokens**、输出 **3,416 tokens**，CC／gateway／adapter一致。单次最大输入18,488，与累计输入区分。完整legacy读取、全树搜索、多次误查测试、两份复制逻辑脚本及重复总结是可减少开销；最后diff确认有检查价值。未新增未经校准总分，也不跨题比较模型效率。

22条实际gateway请求均为 `max_tokens=65536`；CC汇总 `modelUsage.maxOutputTokens=32000`未降低实际请求。声明上下文196,608／240回合／3小时，均未触及；不据此证明极限容量。缓存计数0不证明后端前缀缓存关闭，CC自动费用估计1.503795美元不是本地推理账单。

### 结束与稳定性

CC `success/end_turn`、harness退出0，22条gateway响应HTTP200且无流错误，未发生截断、拒绝或上下文续接。FrozenPatch已评分；执行独立审核实际actor／grader两层关闭和后续主机闭合证据。14个资源采样有未知间隔，仅限定点位，不能推导全程GPU利用率或真实峰值。

本模型只有**一次**成功候选，Qwen3.6首次待回，稳定成功率未知；没有训练／留出资格。原双模型请求保持claimed，不ACK、不释放活动指针、不重提交已覆盖首波。

## 当前处置

未发现需要修改题面、brief、评分或候选处理流程的具体阻断。[非作者语义窄核](../../reviews/non_author_11594_coder_a1_semantic_review_20261003.md) SHA `6e27c869397a213f5f0f86c0bc1b67729426732e9e7c906a172b97e536694500`，已由题主读回并采纳；报告另记模型中间验证范围的非阻断P2。模型自测缺陷记录为基座诊断，不据此启动相同CPU矩阵或模型重跑。保留raw reward及全部原件，等待Qwen3.6首次结果，再按整项回执范围核收。CPU当前无本题作业；发生后续修题时可再申请CPU，整机退租由跨包收口决定。
