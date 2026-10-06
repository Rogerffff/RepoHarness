# Moto7584：R13 控制矩阵原件读回

2026-10-03T02:30:33.049431+00:00。**11组控制已完成作者读回，UID／真实公开CC操作及非作者整题验收未完成。** 此处不授予正式CPU或探针准入。

先前 noop 作业 `moto7584-cpu-a9dd947080c8` 保留：安装0，20项实际收集／解析，1F失败／19P通过，raw0。剩余10臂作业 `moto7584-cpu-0121b210ce7a` 远端实际返回0；本地SSH曾255但未重启，状态／阶段持续推进且最终正常结束。172个回收成员逐SHA／长度匹配，归档SHA `2d3329686fa5b599787d76da9b82e5df607168f905356dba0b5ac252cfcae7a3`。两作业runtime inputs完全相等，固定R13、consumer、source与派生镜像、参考、脚本和预算保持，因此同条件合并控制结果而非机械重跑noop。

| 控制 | raw reward | 实际安装退出 | pytest退出 | 参考 |
| --- | ---: | ---: | ---: | --- |
| noop（原已完成） | 0 | 0 | 1 | 1F失败／19P通过 |
| gold | 0 | 0 | 1 | 1F失败／19P通过 |
| all_protocols | 0 | 0 | 1 | 1F失败／19P通过 |
| arn_form | 0 | 0 | 1 | 1F失败／19P通过 |
| deleted_set | 0 | 0 | 1 | 1F失败／19P通过 |
| gold_order_stmtmsg | 0 | 0 | 1 | 1F失败／19P通过 |
| reject_all_application | 0 | 0 | 1 | 1F失败／19P通过 |
| reject_all_arnmsg | 0 | 0 | 1 | 1F失败／19P通过 |
| stmt | 1 | 0 | 0 | 20通过 |
| stmt_arnmsg | 1 | 0 | 0 | 20通过 |
| wrong_code | 0 | 0 | 1 | 1F失败／19P通过 |

每臂收集／原始summary／parser分别20／20／20，所有参考有PASSED或FAILED状态，无缺失、跳过、合键或未知节点。八个raw0只失败目标 `test_publish_to_deleted_platform_endpoint`；gold／deleted_set／gold_order_stmtmsg表现为应拒绝情形没有ClientError，all_protocols／arn_form错误拒绝合法email／SQS订阅，reject_all_application／reject_all_arnmsg错误拒绝仍存在的application endpoint，wrong_code返回NotFound而预期InvalidParameter。两个stmt正对照20参考全过。历史gold明确是known_incomplete，不能按其名称预设正对照1。

所有10臂实际make init退出0、完整安装marker和测试段marker均齐；pytest0／1与包装exec0分开记录。有效测试patch、注册材料/环境/context、诊断脚本身份、可信测试恢复均精确。实际评分镜像为 `sha256:990e0e91a190f85426e6900828cf758c30f389c927f6c1d0cd1ed8c68b902f96`。候选移除、每次原CLI的正常footer／manager清理，以及每臂自有label容器与网络两项rc0空输出均逐件复核。

逐参考、安装、完整官方日志与诊断见 `runs/category2_repair_20260929/moto_cpu_20261003/moto7584-cpu-0121b210ce7a_author_raw_readback_v2.json`，以及同job `_evidence/output`。UID作业 `moto7584-uid-1f6cf47cd641` 返回75、未开始，尚待公平入槽；四条原公开命令的真实CC操作尚待执行。没有模型调用、没有真实AWS调用，没有训练资格结论。
