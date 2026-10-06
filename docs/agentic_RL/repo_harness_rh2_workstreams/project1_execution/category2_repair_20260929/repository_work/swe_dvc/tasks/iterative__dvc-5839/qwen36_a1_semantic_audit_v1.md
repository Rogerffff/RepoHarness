# DVC5839：Qwen3.6 首臂题主语义审计

2026-10-03 08:55 SGT。请求 `swe-dvc5839-precision-values-r10-v1-20261003`，尝试 `gpu1003-dvc5839-qwen36-a1`，材料 `dvc5839-precision-values-v1`，预算 `probe-wide-v1`。这是本题作者对已封存首臂的分析；GPU执行身份独立核查仍待执行者完成，Coder首臂未执行，完整双模型请求不ack，最终用途未定。

**当前结论：实际补丁修复了漏传参数的根因，符合公开CLI“小数点后n位、默认5”的契约，未发现需要阻断下一模型的题目或评分缺陷。** 原始评分1与语义判断吻合：2个F2P和21个P2P全部通过；该结论只针对本次候选，不支持稳定性或训练资格。模型验证了真实命令行为，但没有修复前的CLI故障复现，也没有新增持久回归测试。相关验证习惯须与得分分开评价。

## 原件与实际补丁

题主已逐个核封存清单的70件文件SHA及大小，共4,796,381字节；完整CC轨迹231行、14个工具调用及结果、15次gateway请求／响应均已读取。原baseline归档547条目与manifest集合及内容SHA相符；原FrozenPatch只修改 `dvc/command/metrics.py`，解码后与实际baseline逐字比较，仅新增 `precision=self.args.precision` 一行。用于评分的是原FrozenPatch，宿主导出的git diff只作审阅。

[题主逐件核对及工具时间线](qwen36_a1_owner_evidence_readback_v1.json)保存原件指针与SHA。FrozenPatch canonical SHA为 `41ddcc7f615b1bbad555e05852c1d27b235f97203ad23885c6fa980f0bbb36da`；baseline canonical SHA为 `e9062a880a5d58acc4e0edc5f1fb014cc13c0c5c33daef1e70b35b39451942f1`。首请求中题面与开发说明精确匹配交付prompt字节，包括原CRLF；没有把文本读取时的换行归一化当作字节变化。

### 1. 修法与边界

`CmdMetricsShow.run()` 的表格分支没有把解析好的 `self.args.precision` 交给已有 `_show_metrics()`；helper在参数为None时回落到5。候选只补该传参，沿用既有float rounding，不改变默认精度、JSON分支、指标读取或 `metrics diff`。修复位置和行为对应公开问题，既不是固定8位，也不是对示例数值特判。

CLI源码明确使用小数位数，原题关于科学记数法的两种期望不构成追加有效数字要求。实际CLI显示：默认的accuracy／mae／mse为0.98765／1e-05／0.0；8位为0.98765432／1.483e-05／1e-08；3位为0.988／0.0／0.0。模型最后称“5或8 digits”，表述不如“小数点后5或8位”精确，但实际实现和输出均符合后者，没有据此判补丁错误。

未改测试或其它工作区文件，FP classification projectable；实际评分projection只包含该业务文件。原始卫生报告clean，与原FP条目一致。未发现评分高而实际修法只迎合私有断言的迹象；此判断不宣称测试覆盖所有合理实现。

### 2. 定位与纠偏

第1个工具直接运行公开提示提供的两项helper测试，2通过；第2个读取完整公开metrics测试文件；第3个读取336行metrics实现，首次取得正确文件、类及调用边界。第4次模型请求随即说明漏传参数，并用 `CmdMetricsDiff.run()` 的正确传参作对照，然后执行唯一一次Edit。没有错误修法、反复搜索或绕到无关模块。

以首次gateway请求为零点，第3工具完整结果在约3.021秒返回，正确诊断在第4次请求区间约3.045–7.169秒生成，Edit结果在7.212秒返回。这是网关与工具结果之间的时间边界，不能细化成内部推理每一步的准确耗时。首次路径由公开题面／开发测试入口提供，不能把它当作无提示的大仓库搜索能力。

### 3. 工具使用

14次工具调用为11 Bash、2 Read、1 Edit，逐次工具结果均非error，未观察重试。路径 `/testbed/dvc/command/metrics.py`、公开测试路径及临时目录一致；临时真实CLI均显式 `PYTHONPATH=/testbed`，避免运行其它安装来源。shell自动恢复cwd时，模型每次显式进入临时目录，未错误依赖前一条shell的cwd。

工具序列为：两项helper测试 → 完整测试文件 → 实现文件 → Edit → 两项helper测试 → 初始化临时git/DVC仓库 → 写YAML → 默认CLI → 8位CLI → 3位CLI → 全metrics模块 → 再看原 `test_metrics_show` → 重读实现前110行 → 清理临时目录。Edit使用精确上下文且成功；最后FP只有预期一行修改。

两次helper测试都通过，第二次只能支持无回归，不能支持故障已修。模型随后用真实CLI弥补了这个缺口。末尾重看测试和实现提供复查，但前文已读取同样源码，属于小量重复；未观察无效报错循环或依赖安装。

### 4. 实际并行机会

15次请求中的工具调用均串行，每轮最多一个工具。独立的测试文件与实现读取、编辑后的helper测试与临时仓库准备，可以合并为一个工具批次；YAML写好后，不同precision的只读CLI核验与模块回归也存在批量执行机会。临时目录清理必须等待CLI完成。

没有实际多工具并发或后台重叠记录，故只记“未使用可行的少量并行机会”，不能断言模型不具备并行能力。此题是单行修复，公开测试分别约0.03–0.15秒，并行收益有限；不为了并行而把有依赖的编辑／核验顺序打散。

### 5. 验证习惯与最终陈述

模型先运行两项helper测试，但没有在修改前运行真实CLI，因而没有保存原故障失败→修复通过的同路径对照。修复后用真实YAML和正常decimal accuracy，同时核默认／8／3三个precision，并执行公开模块22个测试全部通过。它意识到原 `test_metrics_show` 没覆盖precision参数，但没有新增持久回归测试。临时样例在完成后清理。

模型没有实际运行Markdown CLI、JSON CLI或多revision的自建边界场景；不能把原模块默认Markdown测试冒充显式precision Markdown验证。独立grader真实运行修订后的23节点，其中新增真实数值F2P覆盖默认／3／8及Markdown；完整eval日志23个PASSED，与2F／21P参考逐一相符，无missing／skip／unaccounted。该grader覆盖与模型自身验证分别记录。

最终“22单元测试通过、默认与8位生效”有工具输出支持。它没有声称自己新增测试或验证所有边界，没有虚报失败测试转绿；precision术语需按公开CLI解释。

### 6. 效率、预算与资源

正常solve为25.07秒；CC内部duration为18.727秒、API duration为14.754秒，15份gateway响应耗时加总14.334秒。这些计时范围不同，不能直接相减后命名为纯工具或纯推理时间。首次API到最后响应约18.664秒；15回合／14工具，输入token累计168,905、输出2,257，无缓存记账。累计输入含重复上下文，单次最大输入14,463，不能称上下文接近196,608上限。

15次实际gateway请求均max_tokens=65,536，无stream error、HTTP重试或context recovery；CC modelUsage中的32,000是本地metadata，不能推导此次截断。检查点身份由执行者的独立运行核查负责；本作者未自行完成权重／SGLang实际pin验收。CC `total_cost_usd=0.90095` 为本地API价格估算，不是实际付款。

评分总耗时243.859秒，其中启动／reset约14.236秒、trusted setup聚合段219.595秒、测试段6.049秒（pytest正文0.48秒）。trusted段含固定恢复／应用及控制保护等，未留其逐子步耗时，不能把219.595秒全归到chown。该评分准备成本明显超过模型solve，不能计作模型慢或工具重复成本。报告peak为1029.742MiB，queue_wait0仅限此评分manager，不能解释为GPU全队列从无等待。

有限资源采样中的actor peak为878,522,368字节，采样OOM kill／PID上限事件均0。GPU grader实际标签带 `-grade`，已在[资源绑定更正](qwen36_a1_resource_binding_addendum_v1.json)按实际名称与run_id核对；早期核对记录的旧过滤器零样本不是缺失监测。有限采样不替代全程监控或事后HostConfig验收，报告peak独立保留。

### 7. 结束原因、稳定性与后续

CC exit0、subtype success、stop_reason end_turn、terminal_reason completed；完整日志无partial原因。gateway session已revoke／drain，active_requests0；actor和grader清理均正常，manager created1／removed1，无open或cleanup failures。没有观察到输出预算截断、墙钟期限、模型错误或infra中断。

本次可记“单次有效候选语义通过”，暂不更改题目、测试或公开说明，也没有需阻断Coder的语义blocker。仍待GPU执行独立核查、Coder首臂完整回传及同条件必要重复采样；后续若出现score0，须读取实际候选再区分语义错误、断言过窄和基础设施失败。本报告不核销完整请求、不宣称稳定通过、不作训练／留出用途决定。
