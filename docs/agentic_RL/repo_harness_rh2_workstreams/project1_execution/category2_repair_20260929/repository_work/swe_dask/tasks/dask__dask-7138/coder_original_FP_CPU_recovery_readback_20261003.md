# Dask7138：原Coder补丁的CPU评分恢复

2026-10-03T19:39:41.243569+08:00。CPU只把准备预算300改为900，评分和非作者验收已完成；新raw0、tests_failed。原GPU准备超时None保留，零新增模型调用／样本，不重跑59矩阵。

470正式参考完整：原1F通过、原468P通过，新增`test_ravel_keyword_array`失败；实际`TypeError: ravel() got an unexpected keyword argument 'array'`。全模块1 failed／561 passed／92 warnings。位置输入修法成立，参数改名破坏旧兼容的静态判断已得到实际验证。原FP不改，既有compatible_ravel正对照已验；另一模型首轮仍缺。

安装rc0／4.07秒、测试rc1／15.293秒、可信准备202.623573秒。实际UID54322、原625b镜像、2CPU／4GiB／pids512／断网；同原FP、baseline、code8、材料470参考、single-shell完整脚本摘要一致。PID峰28／max0、无OOM；内存峰4GiB／max209，保留限额回收压力。runner_integrity_changed=true保留，固定pytest安装是有限证据推断，无细粒度diff确定唯一归因。此次没有重验actor或授训练资格。

46原件504,226B全核SHA／大小，manager1创建／1移除、自有容器0、统一槽结束，末次固定源SHA不变。此前v1静态属性错误和v2选错配置的纯构造rc1均未评分，原件保留；最终v3只运行一次，不自动重试grader。该CPU恢复运行依赖关闭，源归档load/inspect已核，文件仍保留；整机退租由发布合并，题主不授权机器销毁。

完整绑定与限制见[结构化读回](coder_original_FP_CPU_recovery_readback_20261003.json)，[独立实际验收](../../reviews/non_author_7138_original_fp_CPU_environment_recovery_review_20261003.md)，[原候选轨迹分析](model_probe_coder_a1_analysis_20261003.md)。共享consumer另立7138支持请求，不追加已封存7305/9378 R23输入。
