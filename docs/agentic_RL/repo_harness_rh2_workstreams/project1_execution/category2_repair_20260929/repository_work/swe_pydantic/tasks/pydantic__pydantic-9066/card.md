# Pydantic 9066 当前题卡

2026-10-03。**独立P2P保护已准备，沿用已复核的替代正对照；新登记尚未验收。**

题面要求IP默认值在JSON schema中保留可序列化default。gold修好IP，却使原本可编码的stdlib dataclass默认实例抛配置冲突。云端已找到并独立核实fallback与upstream271两种不同机制正对照；旧v1诊断为noop0／gold0／fallback1／upstream2711／gold_catch_user_error0。[历史最终卡与复核](../../../../../category3_diagnosis_20260929/tasks/pydantic__pydantic-9066/result.md)。

本轮保留原两项IP F2P＋367 P2P，将v1混在IP测试体的stdlib dataclass默认实例断言独立为 `test_default_encoding_preserves_stdlib_dataclass_instance` P2P，提案为2 F2P＋368 P2P。直接依据是base原本支持默认实例及encode_default职责，删除“文档直接规定实例默认值”的错误措辞。[有效补丁](effective_test.patch)和[修订单](revision.json)均已静态检查。

新正式矩阵预期仍0／0／1／1／0。fallback在无法解析前向引用与回退分支ser_json配置上有已记录边缘缺口，不能用它推断其它输入规范；容器内IP默认值等原范围说明保留。新独立节点、正式D6消费、Python3.8/core身份与实际actor开发尚未验收；固定wheel来源和SHA后运行，再作非作者核查和探针申请。
