# 8511 v2：R27 CPU与完整FP补评分入口

2026-10-04。**四候选177参考CPU及独立验收通过，原完整Qwen FP的同版实际补评分也已核收、ACK并清活动指针。** CPU奖励noop0／gold0／narrow1／Qwen源码0；完整FP旧173通过、新4失败、正式0/tests_failed、非infra。原173/raw1、原FP与历史失败保持，模型新采样0。

[原完整FP新版核收](../../model_audits_20261003/8511_original_fp_v2_regrade_acceptance.md)是当前结果入口。新job `pyd8511-fp-r27-20261003T190211Z-v1`由cpu-a执行，实际109原件／435,098字节、独立25检查和题主143绑定／221核对通过；完整FP stdin与原content完全一致，原452项baseline及HEAD／canonical保持。实际安装0／测试1／外层0、一个创建一个删除、slot/systemd收口和独占容器／网络查空已核。原请求returned并ACK/revision5，题目progress26、active=null。

[此前实际CPU矩阵与语义](actual_matrix_semantics_20261004.md)及[非作者CPU报告](../../reviews/non_author_8511_v2_targetfix_cpu_review_20261004.md)保持：唯一作业`pyd8511-formal-20261003175031-v27-dc821`自然结束RC0，526原件／148 Docker调用、各177逐ID终态及清理已核收；narrow全通过，Qwen旧173通过、新4失败，gold三项旧继承护栏及新继承factory失败，不能作为正对照。[CPU验收快照](cpu_acceptance_snapshot_20261004_v2.json)保留当时“完整FP尚未重评”的范围，不回写历史。

R27发布／部署、1529成员与21材料副本、固定[输入](formal_inputs.json)、11件上传和[独立输入delta](../../reviews/non_author_8511_v2_targetfix_input_review_20261004.md)均已核收。三实际评分脚本恢复原`tests/test_dataclasses.py`目标，其余spec及材料保持。原R26错误目标、false报告／hold及旧173/raw1不改，不再次CPU、模型求解、prepare、generator或upload。

原完整FP-only[固定请求](probe_request_v2_fp_regrade.json)及[非作者请求终版](../../reviews/non_author_8511_v2_targetfix_regrade_request_review_20261004.md)保持。实际补评分和源码对照各有独立证据；原baseline environment=null与excluded=true未重写。前置核查通知的发送时序已核，最终书面预检事后落盘的限制见新版核收报告；不把本次评分扩大为GPU主机／模型准备、训练或留出资格。
