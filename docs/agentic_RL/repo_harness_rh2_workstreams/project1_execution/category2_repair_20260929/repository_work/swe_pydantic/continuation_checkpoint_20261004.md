# Pydantic 接续点：8511新版补评分已核收

2026-10-04（Asia/Singapore）。**六题原固定探针及8511的v2修订／原完整FP补评分均已执行、独立验收和题主核收，ACK并清活动指针。** 当前没有待派发CPU或模型作业。本次固定闭环完成不等于训练、留出或稳定成功率资格；后续重复及用途由总协调按覆盖门槛另排。

8511原完整Qwen FP在cpu-a/R27实际177参考补评分：原173通过、新4失败、正式0/tests_failed，非infra。原173/raw1、原FP／baseline／trajectory及历史失败保持，新模型采样0。当前唯一结论入口是[新版完整FP核收](model_audits_20261003/8511_original_fp_v2_regrade_acceptance.md)，机器可读[结论](model_audits_20261003/8511_original_fp_v2_regrade_acceptance.json)对应相同范围。

## 当前状态与验收范围

- 原请求`swe-pydantic8511-behavior-v2-fp-regrade-20261004`已returned并在19:24:29Z ACK/revision5；题目progress revision26、phase=probe、active=null，见[实际ACK](coordination_20261003/8511_original_full_FP_v2_request_ACK_actual_v1_20261004.json)。不要再次ACK或重开首臂。
- 实际新job `pyd8511-fp-r27-20261003T190211Z-v1`于19:02:14Z至19:05:14Z运行。109件原件／435,098字节、独立25项、题主143绑定／221核对（包含177逐参考原日志终态）均通过；原完整stdin、452项fresh census／HEAD／canonical、安装0／测试1／外层0及一个创建一个删除、slot和systemd终态0、独占标签容器／网络空均已核，见[题主证书](coordination_20261003/8511_original_full_FP_v2_regrade_technical_owner_readback_v1_20261004.json)。技术回执位于`runs/category2_repair_20260929/pyd8511_original_FP_regrade_20261004/technical_receipt_v1.json`，SHA `69be8cee03e5b1d0e761277f1e0e740d8209b2e70cb3cb01c014a3d644e3596b`。
- R27四候选正式CPU `pyd8511-formal-20261003175031-v27-dc821`的177参考完整，奖励noop0／gold0／narrow1／Qwen源码0；[实际矩阵](cpu_acceptance_20261003/8511_fieldinfo_v2_targetfix/actual_matrix_semantics_20261004.md)、[非作者报告](reviews/non_author_8511_v2_targetfix_cpu_review_20261004.md)及题主526原件／148调用、528原件与报告、11支持绑定证据保持。原[CPU验收快照](cpu_acceptance_20261003/8511_fieldinfo_v2_targetfix/cpu_acceptance_snapshot_20261004_v2.json)继续记录当时完整FP尚未重评，后续事实另记，不回写。
- [预检时间线读回](coordination_20261003/8511_original_full_FP_v2_preflight_chronology_owner_readback_v1_20261004.json)确认非作者19:01:49Z发送工具调用／返回均在派发19:02:11Z前；发布方明示收到固定runner通过通知后派发。消息参数加密，未独立核明文或root接收UTC；最终书面预检19:02:51Z是事后持久化，不能称派发前书面封存。实际25项独立核收也是事后范围，未追加实验。

## 已固定的R27材料和原候选

R27 ID `cat2-cpu-r2e094095-swe40-pyd8511-fieldinfo-v2-test-target-20261004-v1`，manifest SHA `897cac778bce053740d7ac6dce9b2e90ac96a553a119c0bbdfe7e62b298cfe0d`，1529成员。相对R26仅spec_vendor／SNAPSHOT_ID及一个维护测试变化；21材料、bundles保持。发布和cpu-a部署已[核收](coordination_20261003/8511_v2_r27_publication_owner_readback_v1_20261004.json)，支持请求ACK。固定[正式输入](cpu_acceptance_20261003/8511_fieldinfo_v2_targetfix/formal_inputs.json)SHA `88939f7d852133b2b6130f8d2e2c5a3237e9c7bdd13ed994dfa25c6782f368cd`；四候选／177参考／8资产／runner保持，实际三脚本明确指定`tests/test_dataclasses.py`。新namespace的11上传件和[独立输入delta](reviews/non_author_8511_v2_targetfix_input_review_20261004.md)、68绑定已核收。

原job `gpu1003-pyd8511-qwen36-a1`，FP canonical `sha256:4c305765cca042e14a8b79ebafa304394739f982b0eb68a471a47efbf92b3da1`，baseline canonical `sha256:40135f281c216e76a04de6772eaaadcdfd0b46d949e98c5164f29cba2f454e45`。原`excluded_pathset_changed=true`及baseline environment=null保持；新评分未用源码重构工件替代。此次在cpu-a执行，既有df6c镜像实际身份已核；不证明GPU主机或模型／权重准备状态。

原完整FP-only[固定请求](cpu_acceptance_20261003/8511_fieldinfo_v2_targetfix/probe_request_v2_fp_regrade.json)SHA `e94ec718add3e42785141c8e38f25928d8268e7cc8f7b81f10c463ad42bea6e3`；[该实际请求非作者终版](reviews/non_author_8511_v2_targetfix_regrade_request_review_20261004.md)及题主44绑定核收保持。18:48:55Z提交、18:49:53Z实际通知，后续完整FP结果及ACK另在上述新报告记录。生成器本地可选error键第一次失败的源／输出保持，修复后单次生成请求成功；不再运行独占创建generator或upload。

## 保留的历史与阻断范围

旧R26 `cat2-cpu-r2e094095-swe40-pyd8511-fieldinfo-v2-20261004-v1`发布和身份／上传曾通过，但三评分脚本为裸pytest、缺原文件目标。原false[独立输入报告](reviews/non_author_8511_v2_input_review_20261004.md)、[实际阻断](coordination_20261003/8511_v2_test_target_preflight_block_v1_20261004.json)、旧输入namespace及hold保持；R26未启动177CPU。后续R27窄修不解除旧版阻断，也不热改封存材料。

旧R14/v1覆盖材料、R26和v1/v2零行为身份hold、原173/raw1以及失败诊断原件保持。唯一直接诊断v3的baseline／narrow四PASS、Qwen四FAIL、完整452源身份及非作者证据见[实际v3读回](cpu_acceptance_20261003/8511_fieldinfo_retention_diagnostic_v1/actual_v3_readback.md)。私有v2的21成员[正式清单](tasks/pydantic__pydantic-8511/revisions/pyd8511-behavior-v2/publication_manifest_20261004.json)和所列材料／报告保持封存；只更新当前导航和新核收记录。

其它五题有效结论见[模型审查入口](model_audits_20261003/README.md)：5662和8316、9066本次正式参考通过；6283原Qwen回归／新Coder有效；8567两候选均有真实回归。各题交付文件、模型来源和求解环境差异保持各自报告限制。8793仍归原探针线程。

本轮无新模型、题主GPU SSH、共享consumer／pins自行修改、commit或push。连接资料只留忽略目录；新的infra、身份或清理未知应停止具体新attempt并先分析，不自动重试或扩大预算。
