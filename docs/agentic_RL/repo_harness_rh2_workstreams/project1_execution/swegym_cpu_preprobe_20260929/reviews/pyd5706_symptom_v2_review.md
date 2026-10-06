# Pydantic5706 症状修正版 v2：独立窄审

2026-09-29。**静态结论：可交 root 统一执行，未发现新增阻断。** 这是跨包独立核验，复用当前上下文及已审旧编排，不是新盲审，也不证明运行成功或 OS 隔离。只读取本地原件并做 AST、heredoc Python 语法、`bash -n` 和摘要核对；未导入 Pydantic、运行项目、容器或远端。

审查对象：[新实验脚本](../../../../../../rh2/experiments/swegym_cpu_preprobe_20260929/pydantic5706_symptom_followup_v2.py)，SHA256 `267e440d990309e0a7af7be05732eb3c1d8e8d19634e4309b4ff3601c60f480a`；[input_manifest.json](../../../../../../runs/swegym_cpu_preprobe_20260929/inputs_extra/5706_symptom_v2/input_manifest.json)，SHA256 `63bddc4c5bac3ef70a9fc09f533378fb5c2f9e099fb27fb3cdb9afeda74221b0`。清单15件材料的内容 SHA 均匹配，脚本四个 frozen 入口 pin 与本地冻结代码一致。

## 异常修正有实际依据

先读[旧 actor captures](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-5706/followup_20260928T200118Z-72c261/actor_original/captures)：core 为0.31.0，schema 调用按预期产生 `PydanticInvalidForJsonSchema`/`IsInstanceSchema`；JSON 调用实际抛出 `NotImplementedError: Cannot check isinstance when validating from json,use a JsonOrPython validator instead.`。旧命令未捕获它，rc=1；旧任务在 actor 后以 `Sequence base symptoms not precisely reproduced` 停止，不能改记为旧轮通过。

新[症状命令](../../../../../../runs/swegym_cpu_preprobe_20260929/inputs_extra/5706_symptom_v2/actor_symptom_commands.json) 保留 schema 错误断言，增加 core==0.31.0，JSON只捕获这个异常类型并断言完整消息相等；最后才输出完成 marker。外层 matcher 同时要求 rc=0、精确异常标记和完成标记。未知异常、同类异常但消息不同、任一调用意外成功均不满足。此修正表示“当前固定版本症状已定位”，不表示题面 core0.25.0 症状已逐项复刻，也不选择“应支持”或“应拒绝”JSON 的题义方向。

逐字段对照旧 `public_commands.json`，只有 `public_original_symptoms` 改动；actor单命令列表恰等于新版公开列表中的这一条。没有顺带改回归、超时或期望成任意非零。

## 复用绑定与后续链条

- [prior_actor_evidence.json](../../../../../../runs/swegym_cpu_preprobe_20260929/inputs_extra/5706_symptom_v2/prior_actor_evidence.json) 的10份旧文件 SHA 均匹配。脚本检查旧停止原因、base commit、实际image、harness完成及清理；三个复用命令与旧 attempt 字段完全一致并为 rc=0。原件另证实 prelaunch/activation 通过、流完整且输出未截断。旧 identity 为uid54321、Python3.8.19、`/testbed/pydantic/__init__.py`、core0.31；四种Python容器控制通过，旧pytest为6 passed/645 deselected。初始 `pdm.lock` 和 `pyproject.toml` 已有修改，不能描述为 pristine 源树。
- 新 actor 用相同固定base config ID `3e3b78ae4098882290d0d7b6d544e81816337295d3a7f0245db7ea58355985d4`，仅补症状命令。新旧证据分开，新 `symptom_v2_<UTC+随机>` 目录 `exist_ok=False`；旧 inputs_v1、结果和失败原因不覆盖。
- 私有 base/gold/sequence_list 仍各建独立容器。base运行修正症状及两组回归；gold/退化排除“必须出现base异常”的症状命令，继续Python类型/值及六项旧测。这与旧编排一致，避免把症状断言误施于gold。每个变体先检查源码导入/core及pytest收集，再逐子命令核目标，超时/未完整执行停止本题；私有root不替代actor。
- 安装 recipe、candidate_install.sh、Dockerfile、fetch_wheels、八wheel清单、gold/退化补丁及其它私有输入与旧材料逐字节相同。gold还与冻结gold目录核SHA；下载轮子核大小/SHA并拒绝额外资产，派生镜像保留base层。候选 editable 与 testing/testing-extra 元数据安装仍保留；没有通过省略安装或换版本让测试继续。
- 正式仍为 noop/gold/sequence_list、原2 F2P+273 P2P。保留源码导入/core、apply、参考缺席、runner、完整test段与noop/gold结果检查，`artifacts-dir`、完整日志、ledger和recipe/budget审计不变。没有改源测试、评分参考或生产入口。

## 预算与清理边界

2 CPU/4 GiB、actor wall1800、症状60秒、回归60/300秒、端口18098不变；formal setup900、test1800、whole3600、candidate-stage900沿用本批条件。不是提高权限或修改内核后的复验。

actor保留自身清理校验；private保留rm/query及remaining检查；SIGTERM/SIGINT会抛出并进入子进程组TERM→等待→必要时KILL路径，强杀标记cleanup_unconfirmed且不继续。grade要求候选清理成功，同时调用的[冻结replay CLI](../../../../../../runs/swegym_cpu_preprobe_20260929/frozen_code_v1/rh2/scripts/replay_grade.py)在finally执行manager.close，并用final_exit_status对未关评分容器返回非零，新脚本run拒绝非零。供应本批关闭；不能仅凭静态代码宣称资源已经清理，实际验收仍读两层清理与完整输出。

本次无需为非阻断美化推迟派发。运行后应分别报告旧失败、补验结果、私有行为、正式评分及真实候选导出，不把 `executed_pending_review` 写成题目通过。P5目标歧义、D6未实施、公开材料交付与模型/训练资格继续保留；本review仅确认这份诊断编排具备进入已有授权CPU执行流程的静态条件。
