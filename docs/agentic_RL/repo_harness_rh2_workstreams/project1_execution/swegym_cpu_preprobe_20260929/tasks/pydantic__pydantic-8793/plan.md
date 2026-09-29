# Pydantic8793：CPU 前置记录（2026-09-29）

**公开开发路径已在真实 actor 工具通道验证；正式评分和质量对照未完成。** 当前不授予比较／训练资格。此次为真实 CC 2.1.205 加确定性桩，没有自主模型推理。

原镜像 actor（UID54321）使用 testbed Python3.8.19、core2.16.2，从 /testbed 导入，fields.py 可写。精确base为832225b90672；初态保留pdm.lock/pyproject.toml两处来源改动。公开原例完整复现：required只有foo、bar/baz非必填、缺值被接受成Ellipsis；rc1来自预先指定的三项行为断言，非依赖或执行失败。合法输入/真实默认5/工厂7通过；两份公开旧测试72 passed、1 skipped（0.54秒），日志未给skip节点；公开test_annotated_alias仅Python<3.10因repr不同skip，与本次单skip一致（静态推断）。

四个Bash工具调用与四份结果ID逐一对应，日志完整，容器/网络/relay清理成功且无残留；起止39秒，solve15.034秒。attempt的wall_seconds=1800是预算，不是耗时。桩返回的token/cost不记模型成本。

两个旧摘要标记为false不能当作失败：解释器检查只识别旧RH2_SYS_EXECUTABLE格式，实际PY_CHECK/activation已有正证据；本清单未安排BASHENV攻击标记，prelaunch已见激活文件不可写。pytest-sugar摘要未被runner正则识别，但capture有明确72/1。首次image inspect rc1，随后container/prelaunch确认实际base镜像ID e61eaef6…；完整身份见结构记录。

**限制直接保留：实际用户消息是Devcheck控制文本，并非题面/public_hints。** 因此本次验证公开命令能在正式actor通道执行，不证明正式解题输入交付已验。当前也没有候选投影、安装消费、正式评分或gold/退化对照的新结论。

执行输入：`runs/swegym_cpu_preprobe_20260929/task_inputs/pydantic__pydantic-8793/public_commands.json`；私有补丁/矩阵不进actor。原始结果：`runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-8793/actor_original_v1/`。逐项事实、摘要纠正与证据SHA256：本目录`actor_original_v1_review.json`。

剩余：root完成8公开wheel恢复/候选安装与noop、gold、force-required退化评分；我归因目标执行/P2P/错误候选，观察Ellipsis与内层默认边界；正式题面/提示交付、初始元数据实质差异与版本对应、skip原因按必要性补核；独立复核。公共GPU入口与预算仍待，不称GPU-ready。

既有调查继续引用：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/pydantic__pydantic-8793/`的card/public_read/review/screening_record。没有重写历史资格或原件。
