# Moto6114：ARN 查询返回正确集群

2026-10-03。**必要 CPU 修订验收和最终非作者复核已通过，三臂为 0／1／0，当前固定首轮基座探针请求。尚无新模型结果，训练和留出用途未定。** 详见 [CPU 验收](cpu_acceptance_20261003.md)及 [results.json](results.json)。

原评分对返回第一个集群的错误候选给 1：原 F2P 只查 ARN 结果数量。本轮 [有效补丁](revised_test_draft_v1.patch)保持原节点，核 ARN 返回 Identifier 和精确 ARN，以及名称查询对应同一对象；只比较稳定身份字段。公开功能题面、原 1 F2P／34 P2P、安装和完整测试命令不改，不扩入跨账号／地区／服务行为。

修订后 noop=0（ARN 查找失败），gold=1（35 条全通过），wrong_first=0（新增 Identifier 断言实际比较 cluster-id1／cluster-id2 失败，原 34 P2P 全通过）；每臂参考完整，没有缺失或跳过，安装、测试、候选和 manager 清理完整。新宿主实际 UID/GID 54321、conda testbed、本地 Moto/RDS 导入与 boto3/botocore 1.35.9、实际镜像及资源限额相符，容器和网络零残留。

固定消费为 `cat2-cpu-r2e088-swe12-git-20261003-v1`，修订 `moto6114-cluster-identity-v1`，操作 `replace_test_patch_preserve_refs`。v3 已完整完成 noop 后因 gold 目录冲突外层 rc1，保留该事实；[v4 修正和复用独立核查](../../reviews/moto6114_v4_entry_and_noop_reuse_non_author_20261003.md)接受原行复用，v4 只补后两臂。43＋59＋5 件原件各核 SHA／长度；详细固定身份与作业见 CPU 验收。

[最终非作者 CPU 窄核](../../reviews/moto6114_final_cpu_non_author_20261003.md)通过。[历史真实 CC 公开路径条件复用](../../reviews/moto6114_public_actor_reuse_non_author_20261003.md)由本次 UID 补查关闭环境缺项；没有把旧 devcheck 视为自主理解、新 CC actor、冻结导出或本题 a2g。旧两个 legacy flags 保留 false，原件不回写。5406 代表验证共享 actor→原冻结工件评分路径；6114 模型探针必须建立新实际工件。

[probe_request.json](probe_request.json)仅供宿主接收，固定原材料、配方和二进制、必要 CPU 及独立证据；[公开开发说明](public_dev_brief.md)仅补中性环境。GPU 线程按既定两模型各一次接收、核实际生效预算并排队，本线程审全部轨迹和候选语义，再按全批进度接续重复采样及可能修复。历史 [暂停点](../../pause_checkpoint_20261003.md)与旧材料诊断保留。
