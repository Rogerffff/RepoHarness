# getmoto__moto-6114

**建议：needs_review / static_review；仅供 development_diagnostic。** 目标是在 base f01709f9ba656e7cf4399bcd1a0a07fd134b0aec，让 describe_db_clusters 的 DBClusterIdentifier 接受已存在集群 ARN，并保留名称查询。

| 核心要求 | 决定性断言 | 判断 |
| --- | --- | --- |
| ARN 定位目标集群 | F2P test_describe_db_cluster_after_creation 查询第二个集群的 ARN，仅断言长度 1 | 部分：未核 Identifier/ARN |
| 名称、全部列表、空列表及未知名称错误 | F2P 原断言与相关 P2P | 已测场景有保护 |
| Neptune 共用回退、不存在 ARN | 本题 35 项无对应 ARN/混合回退断言 | 缺口，未执行新反例 |

[完整映射与调用链](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch04/results/getmoto__moto-6114/analysis_before_history.md)；[隐藏测试](${REPO_ROOT}/runs/swegym_quality_batch04_20260921_v1/private/getmoto__moto-6114/test.patch:23)；[公开要求](${REPO_ROOT}/runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114/user_prompt.txt:3)。

核心疑点是：保留旧查询路径、遇任何 ARN 返回第一个集群的错误实现，静态上可满足全部断言，却返回错误目标。这是具体漏测候选，**尚未证实 RH2 误收**。gold 只取冒号末段；本题未约定的 ARN 输入 的账号、区域和资源类型语义缺少公开依据，保留歧义，不判为确定 gold 错误。

既有 [noop 原日志](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/getmoto__moto-6114/noop/eval_logs/evallog_replay-er19-iw1-getmoto__793414a1.eval.log:557) 在真实 ARN 查询报 not-found，34 P2P 通过；[gold 原日志](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/getmoto__moto-6114/gold/eval_logs/evallog_replay-er19-iw1-getmoto__356bbc61.eval.log:539) 为 35P，安装成功、参考无缺席。两份 ledger 的镜像、脚本、投影与原日志 hash 已核。这覆盖 install-wave1 修复后的评分环境，真实 actor 的解释器、依赖、消息、资产仍未知；旧安装失败对该评分配方已过时。

八方面已覆盖公开需求、材料/初态、全部 F2P/P2P、合理替代路线、gold/相邻回归、开发需要、文件恢复和诊断用途。未查真实 actor 与模型成本、全部安全面、跨题关系；替代解未运行。题面 cluster-1/cluster-0 笔误是非阻断文本问题，核心目标仍明确。文件排除保持空，独立复审已纳入：暂缓按原 reward 统计普通模型正确率，先做目标身份评分校准。

**唯一优先下一步**：目标身份 CPU 对照——gold 与“ARN 返回首个集群”的候选分别跑原评分，同时核返回 Identifier/ARN 对应请求对象。避免拿创建时 creating 状态与查询时 available 状态做整包相等。此实验未执行。

已读隐藏测试、gold、既有结果及解封旧记录；审查产物不能提供给 solver。[旧发现差量](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch04/results/getmoto__moto-6114/old_findings_delta.md)。

[独立复审](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch04/results/getmoto__moto-6114/review.md) 支持上述暂缓与唯一 CPU 实验。跨账号/区域/服务 ARN 可能语法有效，只是本题未规定相应查询语义；不能统称非法或据此判 gold 错误。
