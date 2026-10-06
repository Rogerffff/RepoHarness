# Dask7138：array-like 转换与旧关键字兼容

2026-10-04T01:59:26.439112+08:00。Qwen raw1/470参考全过，完整正式module562passed；Coder原GPU None/同FP CPU0因漏array=兼容保留。 当前目标经[新分析](model_probe_qwen36_a1_analysis_20261004.md)和[非作者核](../../reviews/non_author_7138_qwen36_a1_candidate_review_20261004.md)通过；双模型回执已ack，活动请求清空。实际code9/R25材料/镜像ID/完整脚本已核，当前没有新增题级阻断，不追加CPU或模型。单次结果不授稳定能力/训练资格。

公开目标是 `ravel` 接受标量及 array-like，返回正确展开的 Dask Array。原 gold 的转换主体有效，但把 `array` 改名为 `array_like`，导致既有 `da.ravel(array=...)` 调用无法绑定。题面已给转换方向，后续探针必须注明引导属性；不新增零拷贝要求。

本轮保留原 F2P 的四类零值输入，增加一个含非零、负数的嵌套输入；追加旧签名的关键字 P2P。有效参考为 1 F2P、469 P2P（原 468）。`compatible_ravel.patch` 保留旧参数名并调用 `asanyarray`；已通过完整私有测试和 R15 正式评分、独立结果核查。

| 候选 | R15实际 reward | 验收关注 |
| --- | --- | --- |
| noop | 0 | 原标量/array-like 错误仍触发 |
| compatible_ravel | 1 | 新旧输入、关键字兼容及全参考均过 |
| gold | 0 | F2P 应过；新增关键字 P2P 应失败 |

历史 Python3.8.15/pytest7.4.4 的 noop/gold=0/1、468 P2P 全过，只对应原材料。本轮在 cpu-c 重建固定 pytest7.4.4 配方；非 root actor 交付原题面，原公开模块 560 passed，旧关键字调用通过。新完整私有模块中 noop 为 1 failed/561 passed，兼容修法 562 passed，gold 为 1 failed/561 passed，且只失败于新增关键字测试。每份 470 参考完整、原 468 P2P 全通过、无残留。这些是实际行为诊断，不是新材料正式 reward，配方也不外推其它四题。

当前证据见 [实际 CPU 读回](cpu_readback_20261003.md)与 [results.json](results.json)，固定参考及摘要见 [revision.json](revision.json)，预期矩阵见 [acceptance_matrix.json](acceptance_matrix.json)，正式接续见 [cpu_acceptance_plan.json](cpu_acceptance_plan.json)。历史判断见 [原题卡](../../../../../swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-7138/card.md)。材料静态核查、正式发布评分、实际结果及替代正对照的非作者核查均已完成；首Coder轨迹与补评分已核，另一模型首轮待接续。

当前正式结果：固定 R15 `cat2-cpu-r2e089092-swe39-dask-monai-20261003-v1`、manifest `2b788d1ce84228a27894e04886ade347e91993f48ddc9bdeeb8f92de4aa92917`，三行正式 **noop0 / compatible_ravel1 / source gold0**。45份原件逐SHA/大小核，三行各470参考完整；gold只失新增keyword P，原468P均过。候选apply54321按ledger/冻结执行路径核，评分54322另有实际UID/wheel prerequisite成功证据；固定625b、离线pytest7.4.4/原editable安装、完整test、无infra及清理完成。原件与逐参考见[正式读回](formal_cpu_readback_r15_20261003.json)，[独立结果核查](../../reviews/non_author_7138_formal_cpu_r15_review_20261003.md)无本范围阻断。

三行实际 `runner_integrity_changed=true` 保留。摘要覆盖pytest/_pytest/pluggy文件，与实际固定pytest安装一致；没有细粒度前后diff，归因是有限证据推断。旧pip check依赖冲突仍在，不能从本题通过推广整个环境兼容。

[首轮探针固定输入](probe_request.json) SHA `819534ee0ada1c63ec2a2ad4a37a22f97aa4642e8ac010ad7083b3a421b123da`，请求 `probe-swe-dask-7138-20261003-v1` 已提交并直接通知。每款既定模型首轮1次，沿权威宽预算；现有actor fdd298/grader625b在cpu-c，精确镜像已在prepare槽导出并核11份小原件，1,885,056,720B归档SHA及两config ID一致；传输供应已直接交GPU，目标load/inspect及实际run身份已核、供应依赖关闭并保留源文件；当前两模型首轮均已核收并分析，原Coder基础设施None与CPU派生分保持。题主持有逐轨迹方法/定位/工具/并行/验证/效率及必要复修责任；训练资格不由这次诊断授予。

实际同FP作业`dask7138-original-fp-cpu-recovery-20261003-v1`：完整module1 failed／561 passed／92 warnings；实际keyword TypeError，470参考无缺/skip/unaccounted。安装0／4.07s、测试1／15.293s、可信准备202.623573s；原625b镜像、实际UID54322、2CPU／4GiB／pids512／断网、single-shell无supply及完整脚本摘要已核，未套7305五键。46份原件504,226B闭合，manager1／1、自有容器0、槽结束、固定code8不变。PID峰28／max0、无OOM；memory peak4GiB／max209，保留回收压力。runner_integrity_changed=true与diag resource_facts=null仍保留；独立资源读回不回填raw字段，没有逐文件diff确定runner变化唯一归因。此次只验grader，不重验actor或授训练资格。该恢复运行及源供应依赖关闭，源文件不删，整机退租由发布合并。

R24已在cpu-c冻结来源部署，consumer仅setup300→900、五脚本和470参考不变；原R23两政策保留。来源manifest及回执见[当前入口](../../preparation.md)。这不是新的CPU评分或模型样本；当前Qwen code9/R25实际job已核材料、actor fdd298/grader625b、single-shell完整脚本与setup900；旧code8不热换。


本次新Qwen限制：本轮有限输入，不证明全部NumPy选项兼容、稳定能力或训练资格；不新增零拷贝要求。 评分投影排除模型新测试，实际原FP与自测仍保留。详见新分析；不把旧臂缺陷默认为新臂同样失败，也不推广有限自测。
