# Pydantic 5706：CPU 最终结果（2026-09-29）

**正式 noop 0／gold 1／sequence_list 1；退化候选破坏公开既有 Python Sequence 行为，构成实测误奖 S1/T2b。P5 的 JSON 支持或拒绝方向仍未解决：当前仅作诊断，不能用于能力比较或训练，不能以增加私有后检解除限制。**

## 症状恢复与实际范围

旧轮 `followup_20260928T200118Z-72c261` 将题面 core0.25.0 的异常形式套到固定 base/core0.31.0，导致精确症状匹配失败并正常停止。实际 JSON 异常是 `NotImplementedError: Cannot check isinstance when validating from json,use a JsonOrPython validator instead.`；schema 则是涉及 `IsInstanceSchema(typing.Sequence)` 的 `PydanticInvalidForJsonSchema`。这是实验匹配器错误，不能称为环境修复。旧失败原件及 [partial 卡](result_partial.md) 保留。

v2 `symptom_v2_20260928T201808Z-232b80` 只重跑一条修正后的公开症状命令，严格匹配上述异常并到达完成标记，rc0；没有放宽为任意非零。1 个 Bash 与 tool_result 配对，trusted_init UID54321、prelaunch/activation 和实际原镜像核对正常。旧轮 identity、类型回归、既有六项测试三条命令通过 10 份 receipt 的逐文件 SHA 复用，不声称新 actor 又执行了它们。新旧 actor 清理均完成；初始 pdm.lock/pyproject.toml 两行 dirty 状态保留，agent 进程为0。devcheck 不证明完整题面/public_hints 已交给自主解题模型。

固定 base `70e7e99ca1861ad71520cc8fcf1a2fb913abbc10`，原 image `3e3b78ae4098882290d0d7b6d544e81816337295d3a7f0245db7ea58355985d4`；Python3.8.19/core0.31.0，从 /testbed 导入。

## 私有行为与正式评分

独立 root 私有行为中，base 的精确症状、list/tuple/range/deque 类型和值控制与旧六项测试均符合预期；gold 保留这些 Python 行为，旧六项全过。退化仅增加 `collections.abc.Sequence: list` 映射：tuple/deque 变成 list，range 遇到 `ValidationError/list_type`；旧 `test_sequence_success` 中 tuple、range、deque、tuple-of-tuples 四项失败，2 passed、645 deselected。依据是公开 base 已有测试，并非从 gold 反推需求。matrix 外层 rc0 表示子命令失败符合预登记预期，不表示退化语义正确。三组准备、矩阵尾标记及 rm/query 清理完整。

| 正式候选 | reward；F2P；P2P | 完整 pytest | 安装 rc／秒；测试 rc／秒 |
| --- | --- | --- | --- |
| noop | 0；0/2；273/273 | 2 failed、275 passed、1 xfailed | 0／4.443；1／3.392 |
| gold | 1；2/2；273/273 | 277 passed、1 xfailed | 0／4.205；0／2.576 |
| sequence_list | 1；2/2；273/273 | 277 passed、1 xfailed | 0／4.122；0／2.647 |

两个 F2P 是 `test_sequences_int_json_schema[sequence_type1]` 和 `test_sequence_schema[sequence_type1]`。noop 均准确失败在 IsInstanceSchema 的 JSON schema 生成，属于正常目标0。三方全部275个参考逐ID核对，无缺席、重复或参考外失败。完整原日志另有两个带空格参数名的 callable 测试 PASS、一个已有 XFAIL；冻结 parser 对这两个非参考节点分词不完整，已直接核原日志，不能将其误称失败或丢失参考。

正式参考不仅检查 schema，也执行 `Model.model_validate_json('{"int_seq":[1,2,3]}')` 的支持示例；gold/退化确实都通过。正式命令只跑 `tests/test_json_schema.py`，未覆盖上述四项 Python 回归，因此错奖有直接证据。题面将 schema 拒绝描述为正确、要求一致报错，而 gold/参考选择支持；这项 P5 方向冲突不因正式通过或修正版本异常而消失。

## 实际候选、配方与清理

noop 实际投影为空。gold 仅导出 `_generate_schema.py`，60,545字节，SHA `82a04ddea65392cf028fecf3acb54c36ef6975540d24b483a74403d5c5fc4522`；退化仅导出 `_std_types_schema.py`，36,471字节，SHA `7bae36e523323b768de09a8fa885f52217b47a75943408848dae9514f1645f4c`。两份完整导出均逐字等于公开 base 加对应输入补丁，实际 candidate.patch 也完全相同。私有 helper 仅记录固定补丁绑定、git apply 和 diff，没有独立私有完整源码 SHA；正式导出核验不扩大为私有容器字节捕获。

8个公开 wheel 的下载日志文件名、尺寸、SHA 对齐冻结清单；grader 为原13层加 COPY 层的 `d8e8a4475e62b5c38ec3629a6ed33bad147ef915084d311f1571325285dbb943`，离线 PIP 设置已核，1021byte canary 排除。同步未含 wheel 内容，不声称本地重算 wheel 字节。实际 candidate-aware 配方 editable 安装并消费 testing/testing-extra，安装后 core0.31.0、pydantic2.0a4 和 /testbed 导入均观察到；原 dirty 元数据不抹除。三方安装失败命令为空，测试段标记完整，runner 摘要前后一致。

三方候选容器 removed=true，driver 日志最终 manager_close 均创建/移除各1，open/supply/cleanup failures 为空，final exit0；本 runner 没有独立 driver_close_checked.json，直接以实际日志核双层清理。资源是2CPU/4GiB；setup900、test1800、whole3600秒。trusted_setup 分别170.798／162.298／159.222秒，内存峰值678.469／672.586／673.059MiB；resource_facts=null，不外推全程无 OOM。root 04:29 的归属容器清空与 unit 正常退出0提供外层收口证据。

## 用途与剩余事项

当前可保留为环境、评分遗漏和目标歧义诊断。S1/T2b 禁止训练，P5 禁止能力比较；私有回归通过也不能把本题直接纳入比较。最小后续要求是先由公开任务的决策方确定 JSON 支持还是拒绝，再在版本化正式参考中加入已有 Python Sequence 保持行为，连同选定 JSON 行为复验 noop/gold/退化三方。D6 正式题面/测试修订本夜未实施，本稿未改原题或评分。

尚缺：P5 方向决定、D6 实施及其正式 CPU 复验、完整公开题面/public_hints 的实际交付、自主解题与 GPU/模型/预算验证、训练/留出划分；完整 pip-check 和全生命周期资源观察也未由本轮覆盖。原件审阅、root 冻结 parser 重放及115件1,922,316字节远端/本地 SHA（0差异）均完成；跨包原件复核及最终题卡对齐均已完成，无新增阻断。

证据：[逐参考/候选/清理审计](evidence_audit.json)、[机器结果](result.json)、[跨包复核](../../reviews/pyd5706_result_review.md)、[root parser](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/pyd5706_final_v2.json)、[root SHA 清单](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_pyd5706_v2.json)。原件根为 `runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-5706/symptom_v2_20260928T201808Z-232b80/`；早期 [v2 partial](result_v2_partial.md) 保持历史范围。
