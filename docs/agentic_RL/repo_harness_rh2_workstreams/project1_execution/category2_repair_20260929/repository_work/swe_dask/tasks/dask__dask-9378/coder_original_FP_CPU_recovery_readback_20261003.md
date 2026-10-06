# Dask9378：原Coder候选的CPU补评分

2026-10-03T18:39:19.568020+08:00。同原FP的环境恢复与非作者验收完成。补评分为1／resolved：3F+134P共137全部通过，安装5.267秒、测试13.848秒。当前用户B范围的mask和有效值成立；dtype/chunks/name/shape限制及过宽最终说明保留，不能把此分扩成全参数兼容。

仅把setup调至900，未继承7305线程变量。PID峰值53、max事件0、无OOM；内存峰值4GiB，memory.max事件154，发生了限额回收压力。

原GPU None及原失败封存保持；本次零模型调用、零新增候选，不重复59行有效CPU矩阵。实际同code8、镜像/FP/baseline/材料/参考，2CPU/4GiB/pids512、UID54322及断网均核。是single-shell，after-install摘要只留静态身份。manager1创建/1移除、自有容器0、槽已结束；未重验actor或授训练资格。

完整证据见[机器读回](coder_original_FP_CPU_recovery_readback_20261003.json)和[独立验收](../../reviews/non_author_9378_original_fp_CPU_environment_recovery_review_20261003.md)。本CPU环境依赖已关闭；7138源归档和整机其它依赖仍由发布合并。
