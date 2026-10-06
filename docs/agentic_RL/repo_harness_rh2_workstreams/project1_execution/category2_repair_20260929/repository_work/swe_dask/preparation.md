# Dask 工作包：当前阅读入口

2026-10-04T02:15:17.529033+08:00。五题均完成两款基座各一次的首次执行覆盖、作者分析与非作者核查；五份回执均已ack并清活动请求。固定CPU控制矩阵59行/54候选和四项同原FrozenPatch的CPU补评分保持，不重复运行。当前结论是有限首轮诊断，不代表整题完结、模型稳定能力或训练资格。

| 题目 | 两模型首轮实际结果 | 当前处置与限制 |
| --- | --- | --- |
| [7138](tasks/dask__dask-7138/card.md) | Coder原GPU None、同FP CPU0；Qwen原GPU1、470参考全过。 | Qwen保留array参数名并正确转换array-like，满足现行目标；Coder漏array=兼容。题面已有转换引导，不作无提示能力测量。 |
| [7305](tasks/dask__dask-7305/card.md) | Coder原GPU None/PID143与同FP CPU0分列；Qwen原GPU0，两候选均105参考完整/104P过。 | 两候选在大uint64 1→3分区最小端点偏1。Qwen只钉摘要端点、漏后续浮点插值；auto未到达。原正对照可通过，未见新材料缺陷/误拒。 |
| [7656](tasks/dask__dask-7656/card.md) | 两模型原GPU各1/49参考全过，各正式log50PASS/2非参考XFAIL。 | 当前目标通过；已存在init=False状态重建限制和Coder过宽说明保留，不能推广全部dataclass行为。 |
| [8801](tasks/dask__dask-8801/card.md) | 两模型原行为分1；Coder来自同FP CPU，原GPUNone保留。两候选完整诊断均失败。 | Coder fresh23=19pass/4fail；Qwen fresh13=9pass/4fail，另10假值兼容走空配置，import在各自分母内。四个语法错误未指坏文件。v7仅诊断，v6草稿继续阻断，不自动训练reward。 |
| [9378](tasks/dask__dask-9378/card.md) | Coder原GPU None、同FP CPU1；Qwen原GPU1，两者137参考全过。 | 用户B默认mask/有效值通过。Qwen主动修正computed dtype，但只测少量实例；旧Coder的dtype/忽略选项缺陷与Qwen仅a/dtype签名分别记录，不推广全部可选API。 |

当前四份新Qwen分析：[7138](tasks/dask__dask-7138/model_probe_qwen36_a1_analysis_20261004.md)、[7305](tasks/dask__dask-7305/model_probe_qwen36_a1_analysis_20261004.md)、[8801](tasks/dask__dask-8801/model_probe_qwen36_a1_analysis_20261004.md)、[9378](tasks/dask__dask-9378/model_probe_qwen36_a1_analysis_20261004.md)。[7656首轮分析](tasks/dask__dask-7656/model_probe_qwen36_a1_analysis_20261003.md)已在此前闭合。各报告分别列实际FP、完整轨迹、逐参考、定位/纠错/验证/最终说明、token/响应/工具/耗时及独立核查，不以原评分替代候选语义。

四个新Qwen实际code9/R25作业均已逐SHA/大小核完整原件及各33执行回执引用，分别148/139/144/163件（7305/7138/8801/9378）；编辑重放与原FP一致，模型新测试从正式投影排除并恢复固定评分测试。材料、实际actor/grader镜像ID、完整single-shell脚本、预算和清理已核。7305实际五export/setup900，其他三题仅setup900/selected_env=null，不机械扩大线程变量。完整脚本与各题已验Coder CPU相同，旧code8在途未热换。

实际资源样本未见本批新Qwen的PID超额或OOM，但存在观察间隔。原policy image_inspect=false、actual_execution_mode=null、two_stage=false和diag resource_facts=null按原件保持；声明profile、实际镜像ID/脚本和有限资源样本分开。没有冒称完整Docker Config/内核profile/子进程env/BLAS内部计数或训练资格，after-install只有静态身份、本次未执行分段模式。模型求解与评分/准备耗时单列，不把环境耗时计入基座能力。

8801新的fresh裁决直接绑定本次Qwen原GPUlog的13诊断封包/10兼容/1原始import，import已计入13；干净judge只看中立prompt/匿名可见消息，完整ID/引文/输入输出来源核过，再由非作者核实际FP/log/材料绑定。匿名键明确采用GPU材料/原FP/log/config/prompt/payload，区分旧CPU ledger键；没有伪造ledger、复用旧Coder23或420控制结果，也不新增CPU采集。

四项原CoderCPU补评分是已有真实候选的派生评分，不算新模型样本；原GPU环境失败None及7305/PID143均保留。59控制行、历史分析和CPU读回不改。CPU自有运行与7138源供应依赖已关闭、源文件保留；CPU退租和GPU服务操作由各负责人按用户授权处理，本题主没有新增资源请求或销毁授权。

公开交付范围已与GPU对齐：unchanged保持prepared spec.prompt，不追加旧通用public_hints；旧脚本桩的提示交付与实际模型范围分开。不能把未交“不改测试”判为违令，也不据此重跑。7138题面已有转换提示、9378题面已有ma/map_blocks方向，探针能力解释保留这些引导属性。

[现行覆盖规则](../../overnight_watch_20261003.md)暂停普通追加采样。当前没有新题面/评分缺陷要求复修，模型有效失败不成为重试理由；不修模型候选来替代基座结果。后续只按具体新缺陷、适用用户决定或训练方案继续，不因首轮闭合授训练资格。普通结论已落账，不额外广播；真正影响在途/排队任务的共享缺陷才定向通知。

交接以[总账](../../repository_work_packages_20261002.json)和[三方流程](../../coordination_workflow_20261003.md)为准。共享发布归「负责处理分类二的明确问题」，GPU队列归「负责处理第一类的模型探针」。逐题卡为事实入口，[当前接续点](current_checkpoint_20261003.md)记录已闭合范围，[旧暂停点](pause_checkpoint_20261003.md)保留历史。运行原件在`runs/category2_repair_20260929/swe_dask/`，不回写evidence。
