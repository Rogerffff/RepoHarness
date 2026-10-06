# coveragepy 四题当前执行入口

2026-10-04。**四题均已有两模型首轮分析。EA69评分盲区已在R28修订到51项，原完整两模型补丁补评分及正负控制、非作者增量核完成。当前没有Coverage CPU/GPU作业在途，不默认追加模型采样。**

本线程端到端负责修订、CPU验收、探针交接、模型分析和必要修复。固定交接先落总账，再直接通知发布或GPU；本包证据保存在逐题card、当前结果清单与reviews。

| 题目 | 已完成与实际结论 | 限制和后续条件 |
| --- | --- | --- |
| [5dbb](tasks/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/card.md)，76项 | 原两模型76/76，所选源码目标满足；首对七维与非作者核通过，returned/ACK | Coder两个失败的新自测保留；每模型另2次计划为可选校准，覆盖优先暂缓，单次不判稳定 |
| [016a](tasks/coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae/card.md)，15项 | 原两模型15/15+1非参考skip，当前保存/read目标满足；首对分析与独立核通过，returned/ACK | Qwen枚举/弱自测、Coder NULL孤儿行限制保留；追加4次本轮0执行，returned/ACK，后续仅可选校准 |
| [EA69](tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/card.md)，R28/51项 | 原GPU49/49分保留；[原补丁新51补评分](tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/model_analysis_scoring51_supplement_20261004.md)两模型均50/51、奖励0，各自公开目标缺口被新增验收捕捉。safe51/51、noop41/51；CPU与非作者核完成 | 两候选均未完整达标。没有重求解；旧R6/R17缺陷版本仍阻断。未来新求解另核新版实际actor/overlay身份，本次CPU验收不授该资格 |
| [F5eb](tasks/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/card.md)，8项 | 原两模型8/8，两源码路线满足所选目标；首对七维与独立核通过，returned/ACK | Coder5个调试产物、9次工具失败保留；追加计划未新提交，覆盖优先暂缓 |

## EA69本次修订验收

公开要求保留已有用户规则，使首次和再次生成的报告文件被真实Git忽略。Coder特殊CSS字面名、Qwen已有规则子串检查各有已实测缺口。R28保留073/093、用096/097替换旧074/075私有评分，旧49方法和期望状态保持，只增加两个行为键。公开题面/brief、源镜像、base、配方不变；私有评分改变，因此整个环境包摘要已更新，没有新加字节相同、文本幂等或指定实现扣分门槛。

新root恢复按固定完整私有材料身份写入test_2，再核新树/旧入口及权限；实际grader显式绑定原精确e23镜像，分别重建同源360项基线并应用原完整FrozenPatch。Qwen包含.coverage与html.py两项，Coder仅html.py。四次正式评分参考键全部在场，安装跳过/RCnull，safe测试rc0，其余tests_failed/rc1；全部自然收口、无残留。103个清单payload项加5份清单，共108个tar成员；这不是新增模型样本。

[最终CPU验收](tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/cpu/scoring51_final_acceptance_20261004_v1.json)与[非作者核查](reviews/non_author_ea69_scoring51_full_FP_CPU_review_20261004_v1.md)可追溯逐项映射、完整输入、实际容器身份、日志及计数勘误。此前边界反例、公开读者和七维分析按未变范围复用，原报告SHA不改；失败方法首错停止，不把其未执行子输入称为已跑过，也不宣称原DB全部记录已消费。

## 当前资源与用途

[Coverage CPU依赖](cpu_dependency_qwen_boundary_20261004.json)已关闭：本轮无后续CPU作业或供给运输，机器与其他仓库依赖未作全局审计，不据此停机。发布请求已returned/ACK并清活动指针；本次不新提GPU、不重旧矩阵、不默认追加采样。

当前结果用于注明版本的普通基座诊断。新CPU评分验收不等于新51 actor环境/overlay已就绪，也不证明正式训练typed actor租约或训练准入。未来选中追加校准时，先核该次实际运行材料、actor和grader身份。旧49原分、候选语义和新51关联分分别保存。

[当前接续点](resume_checkpoint_20261004.md)；历史详细字段见[旧导航快照](history/scoring51_20261004/results_manifest_pre_R28_navigation_20261004.json)，先前阅读入口见[历史preparation](history/scoring51_20261004/preparation.md)。
