# Conan12397：Coder 首次探针分析

2026-10-03。请求 `swe-conan12397-r12-briefv1-20261003-v1`，作业 `gpu1003-conan12397-coder-a1`，模型 `Qwen/Qwen3-Coder-30B-A3B-Instruct`；R12、brief v1、`probe-wide-v1`。

**raw1，2F／2P四个完整参考全部通过。题主与非作者语义窄核确认生产改动补足链接参数，未发现绕过或生产阻断；执行独立报告已回。模型完成配置生成与有关回归，未实际复现原issue的编译／链接；最后把测试范围说宽。Qwen3.6首次尚缺，成对请求继续活动。**

## 原件与评分范围

[固定请求](probe_request_20261003_r12_v1.json)及其SHA `4a572b10c29cb121f241fd6b5b4313044745144d54222cfeb5527f977439ca3a`保持。题主重新核133件、14,578,333字节闭合原件的SHA／大小；完整原issue和brief v1按原字节出现在实际首gateway请求中，保留CRLF，brief只去末尾换行。核查清单位于 `runs/ordinary_gpu_probe_20261002/migration_20261003/gpu1003-conan12397-coder-a1_closed_manifest_v1.json`。

完整候选保留生产 `conan/tools/meson/toolchain.py` 与公开 `conans/test/integration/toolchains/meson/test_mesontoolchain.py` 新增Linux测试。题主从实际baseline archive取原件，与公开base相等，在隔离临时目录应用完整diff，结果逐字节等于两份Frozen内容。**可信投影只有生产文件**，恢复并保护固定评分测试；模型新增测试不贡献四参考，不按测试改动自动判作弊，也不声称模型没有改测试。

四个完整参考逐项核原eval log，Apple cross／Linux native完整cpp编译／链接键各属F2P；quotes／用户extra flags属P2P，全部通过、无缺席／跳过。eval SHA `3ce1c0213a944be548bf5840f9a3a9d387e685ca26bfc9e1cbb5f995ea606f37`，安装／测试退出0。[执行独立报告](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/conan12397_coder_a1_execution_review_v1.json)按其执行／运输范围复用：实际actor镜像 `d0b6f915791c8c4597dffc2642093dfdc864a90f122544b23561e09ad6ba90a1`，两层清理闭合；不当作候选语义或极限容量证明。

SHA、工具全文、指标见私有目录 `runs/category2_repair_20260929/conan_cpu_20261003/probe_analysis_12397_coder_a1_20261003_v1/owner_readback.json`／`tool_events.json`。轨迹根为 `runs/ordinary_gpu_probe_20261002/remote/queue_v18/results/gpu1003-conan12397-coder-a1/attempt/trajectory.jsonl`；下文行号为其一基行号。

## 七个维度

### 方法

行58正确定位 `_context()` 仅把 `self.libcxx` 加到 `cpp_args`，行62补 `cpp_link_args.append(self.libcxx)`，与公开issue的clang／libc++链接选择一致。保留helper对不同compiler/libcxx的条件、用户extra linker flags和Apple flags；没有把GCC ABI宏误加进链接参数，也没有只改objcpp后缀键来掩盖cpp缺项。新增公开回归为Linux生成配置，没有放宽旧断言；临时脚本被删除。没有测试识别或绕过，实际完整键评分避免substring误命中。

这是配置生成范围内的根因修复，支持正确参数进入链接命令准备；没有真实clang／libc++包创建、编译或链接成功的原件。Apple cross亦为生成文件验证。

### 定位

工具1限定meson路径找到文件，工具2读对生产源码，工具3读compiler helper，工具4读公开测试。首次生产读取距第一模型请求 **1.427秒**；正确根因文字行58对应第五响应完成 **5.064秒**，这是响应完成上界，不是首次产生判断的精确时刻。无错误修法回退；完整507行compiler模块读取可缩到libcxx相关符号，未据本样本评一般定位能力。

### 工具与纠错

14次工具：**Bash8、Read3、Edit2、Write1**。编辑、精确测试路径、临时文件清理和最后diff确认正确。工具12的功能目录测试在工具fixture阶段出现3 errors（行153）：`shutil.which()`没有找到所需exe，`Path(None)`抛TypeError；11 skipped、6 deselected、0.38秒，`--maxfail=3`提前停止，未进入这些测试本体。原错误调用链未经过本次修订函数。

行158正确识别为环境工具缺口，但没有核具体exe／修复后再跑，不能说完整functional范围已验证。pytest原非零作为 `is_error=true`保留，未掩盖；本轮不为超出固定评分范围的功能工具缺口修改已验镜像，也不把它当候选失败或全题环境失效。

### 并行

15响应前14各一个工具，最后结束；无工具重叠。读完源码后compiler helper与公开测试可独立读取。本次串行；CC／adapter实际多工具并行支持未独立建立，能力不可判断。相同TestClient工作树和缓存的pytest不直接列为安全并行机会。

### 验证

| 轨迹结果 | 实际范围 |
| --- | --- |
| 行92 | 新Linux配置测试1通过，0.38秒 |
| 行105 | 同一公开模块4通过，0.33秒，含上面新例；不是额外四个不重叠case |
| 行118 | Meson单元模块1通过，0.04秒；构建命令mock，非实际链接 |
| 行140 | 同一Linux配置临时脚本输出并assert cpp编译／链接参数；与新测试重复，不调用原issue的conan create编译链 |
| 行153 | 功能范围3工具setup errors／11 skips／6 deselected；未通过 |
| 可信grader | 固定2F／2P四参考全部通过，模型公开新增测试已被投影排除 |

无旧树失败复现，也无真实链接复验。最终行184称“所有既有测试通过”并称手工脚本“复现准确场景”，超出证据：通过的只是有限公开模块，功能目录失败；脚本只生成配置。这个非生产阻断问题单独记为验证与披露不足，不能据raw1忽略。

### 效率

求解 **30.374秒**，harness27.402秒；CC26.787秒／API23.654秒，差3.133秒不是纯工具时间。15回合累计输入 **271,298**／输出 **2,816 tokens**，最大单请求输入24,594；CC、gateway、adapter核一致。完整源码读取、重复Linux生成脚本与重复总结可减少；不跨题比较模型效率。

Git清理10.497秒、可信初始化10.471秒和容器准备独立列账；评分总93.047秒、测试2.614秒、评分队列0秒，不混入求解时间。15条实际gateway请求均65536输出预算，CC32000汇总元数据未降低它；声明196608上下文／240回合／3小时未触及，不证明极限容量。CC费用1.42689美元是自动估算，非本地账单。

### 结束与稳定性

`completed/success/end_turn`、harness0，15gateway响应HTTP200且无流错误，无截断／拒绝。原件显示安全actor／grader收尾；13个有限采样存在未知间隔，不推全程峰值或利用率。仅一次Coder，Qwen3.6首次与整项回执尚缺，不判稳定成功率或训练资格。

## 处置

题主已读回并采纳[非作者语义窄核](../../reviews/non_author_12397_coder_a1_semantic_review_20261003.md)，SHA `2f4c908570dcf42f69da5fd6304f870f92ad6574d13b54327bbab08e879d0c3e`；生产无阻断，验证陈述范围记非阻断P2。不因模型夸大验证而重跑同一候选，也不重审旧CPU矩阵。继续等待同请求Qwen首次；请求保持claimed，不ACK、不清活动指针、不追加普通采样。具体材料阻断未发现。
