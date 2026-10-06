# 8316：五行完成，第六行保护超时，尚未通过全题CPU验收

2026-10-03。正式R14 job `pyd8316-formal-20261003020938-r14-d2baf` 于02:09:41 UTC入槽，02:34:26 UTC自然停止rc1。固定24候选未全跑完；题主已核归档759件原件的大小/SHA，[非作者部分核查](../../reviews/non_author_8316_partial_cpu_review_20261003.md)通过，五行可保留原job复用；451项政策内baseline及18份完整census、实际安装/导入和运输核查通过。未运行本题公开actor，没有提交GPU探针。

| 候选 | 实际结果 | 范围 |
| --- | ---: | --- |
| noop | 0 | 144参考完整，原F失败。 |
| gold、keep_digit、scan | 各1 | 144参考全通过，三种合理实现被接受。 |
| w_example_only | 0 | 144参考完整，仅修题面示例的错误实现被拒绝。 |
| w_acr_max8 | null | 控制面保护超时，安装及pytest未开始，没有行为评分。 |
| 后18个候选 | 未执行 | 不能计入通过或失败。 |

第六行的Docker调用0210执行原 `grader-protect-control-surface v1`，300.110秒后超时，没有result/stdout。正式report为 `infra_failure/grading_control_surface_protect_timeout_after_300s`、reward=null，trusted setup恢复/apply/attest通过；没有实际安装、测试或测试阶段导入审计。OOM和PID限制事件均为0。没有阶段输出，不能定位卡在哪个递归chown，也不能确认根因。

六个candidate和六个grader已删除，最终本run容器与网络查询返回0且为空。外层“收尾异常或存在本run残留”掩盖“真实测试标记缺失”异常；实际查空结果不支持把它解释为残留。失败原件、原null和五行结果不回写。

此前8567保护-only诊断成功以及七行补验成功，不证明共享保护永久恢复。已落账并实际通知共享维护者支持请求 `swe-pydantic8316-control-protect-timeout-support-v1-20261003`，[固定故障输入](../../coordination_20261003/8316_control_protect_cpu_support_input_v1.json)绑定调用、日志、资源和清理原件。本包暂停新的CPU派发（包括6283 v2），不热改R14、增300秒、禁保护或自动重试；已验收GPU探针继续。

独立R20已实际发布并部署，1479文件及264条完整spec记录的变化范围已[核收](../../coordination_20261003/8316_r20_support_owner_readback_v1.json)，支持请求ACK。只给本题和DVC9395的固定材料／精确grader将准备reset allowance由300改900；安装／测试／whole预算、保护、资源、材料保持。[新十九行输入](../../cpu_acceptance_20261003/8316_r20_resume/README.md)及实际consumer本地prepare已生成，144参考/7脚本身份及spec900已核，非作者输入审查中。发布者未运行真实题级CPU，900是否足够尚未证明；旧R14超时不回写，也不称效率根治。6283继续R19/300，其hold按具体影响范围另核。

支持实际回执、版本变化核对及新输入非作者核查通过后，再按受影响范围接续失败和未跑的19行，保留独立job与版本归属；如需共享新版本，先核实际发布及变化范围。完整144参考矩阵、实际公开actor和全题非作者验收仍待。当前无训练或留出资格结论。
