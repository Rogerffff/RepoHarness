# Pydantic5706：actor已结束，实验匹配错误停机（partial）

2026-09-29，`followup_20260928T200118Z-72c261`。**停止原因是我准备的症状预期错误，不是已证实的环境故障。** 原公开题面记录core0.25.0的ValidationError/is_instance_of；当前base `pyproject.toml:64` 明确固定core0.31.0，镜像实况一致。原症状命令错误地只捕获前者，真实JSON调用抛NotImplementedError后rc1，未到达尾marker；runner按既定精确条件安全停止，不能把旧轮改记通过。

实际异常文本为 `Cannot check isinstance when validating from json,use a JsonOrPython validator instead.`。schema分支已精确到达PydanticInvalidForJsonSchema，消息指向IsInstanceSchema (typing.Sequence)。公开base `_generate_schema.py:837–845` 的Sequence链含is_instance_schema，与该失败位置一致；并非导入、采集、权限、core安装失败。

原image `3e3b78ae4098882290d0d7b6d544e81816337295d3a7f0245db7ea58355985d4`，manifest `480f09d76fedfdb406fc845aab7d5e539d8af6ee905c562ce5ba7cc01203b86b`，base `70e7e99ca1861ad71520cc8fcf1a2fb913abbc10`。CC2.1.205下4条Bash各有成对tool_use/tool_result，UID54321、Python3.8.19、core0.31.0、checkout导入与prelaunch/activation正常。初始pdm.lock/pyproject.toml已dirty，结束仍2行，不能归咎actor新改动。症状命令之外：list/tuple/range/deque保持既有类型和值预期；旧公开test_sequence_success实际6 passed/645 deselected。agent进程0，container/network/relay/stub清理已验无残留。真实请求仍是Devcheck控制消息，不证明完整题面交付或自主解题。

旧run steps仅pull_base与actor_original；private三方、wheelhouse构建、正式三方均尚未执行，本卡无正式分数/误奖结论。P5的支持/拒绝JSON目标歧义与异常版本差异是两件事，当前诊断不解除P5。

## 已准备的独立v2续接（未执行）

root已授权新inputs_extra与新runner，原inputs_v1/旧runner/失败原件保持不变。v2仅将JSON捕获改为NotImplementedError并逐字验证消息，保留schema精确异常和尾marker；异常或任意非零仍停止。复制的安装recipe、8公开wheel、gold/退化补丁、其它公开命令字节不变。固定旧run证据SHA并复用identity/两组回归；正式actor最多补跑1条修正症状命令。随后才私有base/gold/sequence_list、既定wheel层和正式noop/gold/sequence_list。2CPU/4GiB、setup900/test1800/whole3600、2F2P+273P2P不变。

本地只作AST/文本/hash核对和纯实验匹配函数检查：旧原始rc1拒绝；精确合成新输出rc0接受；非零带marker、错误异常文本均拒绝。该合成检查不是实际Pydantic运行，v2实际结果全部未知。后续由Dask/mypy负责人窄审、root统一执行；任何新症状或准备/清理未知仍停本题。

证据：[原actor](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-5706/followup_20260928T200118Z-72c261/actor_original/attempt.json)；[症状原输出](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-5706/followup_20260928T200118Z-72c261/actor_original/captures/public_original_symptoms.out)；[旧停止状态](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-5706/followup_20260928T200118Z-72c261/status.json)；[v2输入与完整续接命令](../../../../../../../runs/swegym_cpu_preprobe_20260929/inputs_extra/5706_symptom_v2/README.md)；[v2脚本](../../../../../../../rh2/experiments/swegym_cpu_preprobe_20260929/pydantic5706_symptom_followup_v2.py)；[机器记录](result_partial.json)。
