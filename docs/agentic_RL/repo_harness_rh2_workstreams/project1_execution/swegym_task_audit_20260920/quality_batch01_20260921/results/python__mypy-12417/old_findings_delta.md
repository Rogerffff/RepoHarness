# python__mypy-12417：历史差异核对

本题 `analysis_before_history.md` 已在历史开放前封存，SHA-256 `ea4bfdd3fd600f50f502fecbbf05ea68d3b5d3f540ed9e6087626ef8b3a8519d`，保存时间 `2026-09-20T18:41:17.535840+00:00`，22779 bytes。本文件在协调者明确放行后新增，前稿保持原字节。

历史入口为 `runs/swegym_quality_batch01_20260921_v2/history/python__mypy-12417/refs.json`，唯一展开记录为 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_2/records/python__mypy-12417.json`。该记录没有可重放的本题 CPU 候选/评分日志，`materials_refs.runtime_evidence` 明确为无。历史中未给唯一完整路径及版本的 `kscan.json`、未带对应版本的 manager 行号、其他题关系均未进一步读取；不搜索其他题或全池材料来补旧主张。

以下 R/P/S/D/E/G/N/O 缩写沿前稿证据索引。新读原件只补了 S/mypy/checkpattern.py:112–140,179–206 的模式调用关系，并再次核对 checkexpr.py:253–277、early_non_match:669–670；没有运行项目或构造补丁。

| 旧主张 | 本轮处理 | 决定性证据与适用边界 |
| --- | --- | --- |
| base/补丁一致，None 断言就是问题 | 确认并提升执行证据 | 本题三份 ingest 第199行逐对象相等；N:441–446,498–538 实际包含原 Name 诊断及同一 AssertionError；原题零捕获例仍只有源码路径推断，不能改称已独立执行 |
| 未实跑安装、没有 runtime evidence | 对当前引用条件已过时 | E/image.json/build.log 与 G/N 安装、四项测试结束原件；固定派生镜像854faf…，Python3.10.14；只更新本题历史 grader 条件，不补写 actor pass |
| 题面 hints_text 为空，输入信息充分 | 区分字段后部分保留、当前接收情况未知 | 当前 P/public_bundle.json 的 public_hints 含操作指令与环境声明，P/environment_brief.md 明说实际 system/CLI 接收未核。历史源 hints_text 与当前 public_hints 不是可直接互换的字段；不得推成 actor 无约束或实际消息完整 |
| F2P 强制近乎唯一实现，early_non_match 是完全合理解且会被判0 | 保留具体疑点，撤回已证实口吻 | 完整比较确实要求七条输出；checker.py:4131–4158,2139–2151 支持替代 guard 会跳过分支体的静态预测。但旧记录没有执行，且某种恢复惯例是否适用于该入口仍需判断；同等输出也能由不同实现产生，故不是“唯一实现”证明 |
| 题面原例零捕获未直接进入F2P | 确认覆盖限度 | D/test.patch 仅 xyz(y)/xyz(z=x)；gold guard 在捕获分支前，源码上覆盖 xyz()；两者不能偷换为原例已执行或 gold 漏修已证实 |
| 三个P2P有判别力，能挡全部类模式返回Any | 确认，但细化其保护 | Normal 是 i=str/j=int；NoMatchArgs 是错误；Partial 是过多位置错误及后续 k=str。P2P并非三条都仅检查精确reveal；各有正负行为，base和gold原日志均通过。没有据此证明全部错误实现都被挡住 |
| -k过选直接证明P2P来自子串闭包而非设计 | 执行事实确认，来源动机未核实 | G:448–465/N:429–436,539–545 选择器恰执行参考集中四个ID，reference missing/skipped均空。子串匹配是事实；为何来源选择这三项不能由匹配形状推出，也不是当前评分故障 |
| P2P只有三条，因此回归存在P3 issue，应该全文件测试 | 降为范围限制，不当作已知回归 | gold只改原先必崩的None入口，现有非None路径不变；已读普通/keyword/alias/NamedTuple/capture代码，没有新破坏反例。优先扩展两项有直接恢复语义依据的旧测试，不把未全文件测试自动记为错误 |
| gold正确完整且依赖齐全 | 在已查范围确认，保留动态边界 | 单一源码guard、符号已导入、原例共享入口；G四项通过。完整原例、所有pattern、不同上下文未独立运行；不能将两行补丁小等同普遍正确证明 |
| F2P不需要fixture，全部本地资产 | 修正术语后确认本地性 | F2P没有专用fixture，但依赖lib-stub builtins/typing；P2P依赖dataclasses builtins fixture、dataclasses stub及plugin。runner和这些文件均已读，grader原件实际通过，actor读取权限另待验 |
| traceback给定位答案，应列泄漏issue/低难度 | 不接受该泄漏结论；难度未测 | traceback属于公开缺陷报告，含崩溃语句不等于携带未来修复。它降低搜索空间，但恢复策略仍有选择；真实actor资产/网络答案泄漏未知，基座难度须真实模型证据 |
| mypy/test/*、test-data/* 应全仓保护，改helper会满分 | 未验证的共享控制面线索，不采用额外排除 | 本题确依赖data/helper/config；G/N只证明官方恢复check-python310.test，gold可交付。旧记录没有helper候选执行，且“所有gold没碰”不能证明排除合法修复无副作用。additional_exclusions=[]，不改规则、不重做平台总审计 |
| 与16905/16966同主题和同文件，应训练评测同侧 | 具体谱系未核实，不采用划分规则 | 历史给出主题/文件关系而非修复祖先/重复证据；本轮没有读两题，不能从主题直接确认同族或规定留出划分 |
| ready_for_probe，可先模型探针再决定是否放宽 | 改为needs_review/static_review | 现有grader证据已完整，但actor基本条件及错误恢复公允性尚未验证。用途仅development_diagnostic，不是正式训练/评测批准 |

## 错误恢复：分别记录事实、兼容性判断与待验证项

1. **确有 Any 恢复惯例，不能说 Any 完全无公开源码依据。** `S/mypy/checkexpr.py:258–260` 明确将 unknown reference 变为 error Any，目的是避免额外类型错误；`checkpattern.py:576–580` 对无效keyword的类型也使用 error Any。`checkexpr.py:264–277` 及 `checker.py:405–419` 则规定已存在但未就绪Var的 Cannot determine type/Any 行为。这些代码使 gold 的恢复结果可解释，不属于凭空要求内部helper名称。
2. **主错误是合理兼容要求，五条附带输出尚未找到该入口的既定兼容契约。** Name诊断在base已产生，并直接符合未知类名原例，应保留。该None入口在base检查分支体之前崩溃，因此base并不存在可供兼容的 m/y/x 后续输出。把“未知表达式是Any”继续推到“整个类模式subject要降Any、捕获必须不推断并发出两条附带错误”还需要决定模式恢复策略。若保持gold式可达分支、空captures，附带诊断来自既有代码；但选择这些前提本身未被题面唯一指定。
3. **early_non_match有合理先例，但不是已经证明的所有上下文正确解。** 同一函数对带参数alias、非类型class_ref等错误走该helper；base `testMatchClassPatternCaptureFilledGenericTypeAlias`、`testMatchClassPatternIsNotType` 的body reveal不输出，说明跳过某些无效分支是旧惯例。它与未知引用Any惯例并存，不能仅凭相邻代码就裁定None情况必须采用哪一种。必须同时看公开原例、正常及异常模式、后续分支语义和真实评分结果。
4. **精确字符串比较不是误拒的充分条件。** 两条Name诊断有依据，输出一致性本来就是编译器测试的一部分。当前争议是对原先崩溃入口选择何种可接受恢复行为，且缺少替代候选的执行；因此只保留疑似过严约束，不登记已证实假阴性，不立刻放宽成任意“不崩”。

历史阅读没有改变前稿的needs_review结论或唯一优先CPU方案；它使最终解释更明确地并列Any恢复与early_non_match两种既有惯例。后续仍先做前稿所列 base/gold/替代guard、原例/两捕获输入/三P2P/两恢复旧测试的同条件对照；若存在有依据的兼容破坏，则不把该候选当合法替代解。尚无CPU执行结果，未修订题面、gold、测试、expected或文件规则。
