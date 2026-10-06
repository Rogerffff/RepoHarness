# DVC4166 当前题卡

2026-10-03 19:30 SGT。**Coder 首臂 reward 0，3F 全失败／60P 全过，实际 3失败／63通过。候选只拆 regex 分组，未修复目录类型和尾斜杠；这是有效错修。Qwen 首臂待返回。** R14 CPU 控制与非作者验收已完成，不重跑 CPU。

公开目标是尾斜杠规则按文件／目录区别工作，不能强求 issue 七种写法等效或隐含子文件重入父目录。固定 pathspec0.8.1。原实现的连续 groupby 已保序、最后匹配决定结果；Coder 排序引入的两个单元回归虽撤销，最终修法仍未让父目录正确进入遍历。

## 首轮候选与轨迹

[题主七维审计](coder_a1_semantic_audit_v1.md)、[逐件原件读回](coder_a1_owner_evidence_readback_v1.json)、[非作者语义报告](../../reviews/non_author_dvc_three_coder_a1_semantic_review_20261003.md)已完整读回。范围是本次 Coder 首臂；[原轮次执行证据独立报告](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/closed_four_execution_non_author_20261003_v1.md)已另行交付并核收，没有新增执行矛盾，仍不代表成对请求闭合。完整 FP 有 23 项，其中 22 个根目录脚本，原件不删改。

错误read/readlines mock反复出现；平面文件匹配不验证父目录遍历；29个公开测试通过不足以支持成功声明；FP保留22个调试脚本。实际服务有作业前 engine／adapter、只读模型挂载、argv／HTTP 配置绑定；列出的 25 个模型文件大小匹配，其中 16 个权重分片，声明计数 28 与列表 25 不一致。没有重新全权重 SHA 或 GPU 内存证明。baseline 的 `environment_package_digest` 仍为 null，不能用 prepared 环境摘要补填；资源采样缺口与独立脚本未留存的限制保留。

本轮请求保持 claimed／active，Qwen 首臂待返回，不提前 ACK／returned 或清活动指针。覆盖优先，暂缓未开始的普通重复；本次结果不决定稳定性或训练／留出用途。固定 probe 输入 SHA 不变，材料与原题面／中性说明未热改。

## 当前材料与CPU证据

[revision](revision.json)固定 `dvc4166-behavior-v2-draft`；新增非空目录剪枝F、同名普通文件P、显式父目录可见性与否定目录恢复F。原两个前导空格case以显式ID映射，保留输入／断言，通过题级消费者绑定，不改全局parser。

[正式矩阵](formal_matrix_r14_v1.json) noop0／gold1／去正向尾斜杠0，各66实际／63参考、3F／60P。负例实际64通过／2失败，落在新增否定目录F和普通文件P；不推断旧原版正式reward。[CPU验收](cpu_acceptance_r14_v1.json)与[非作者正式读回](../../reviews/non_author_formal4166_r14_runtime_review_20261003.md)已核UID54322预检／安装、完整节点及两层清理。[公开actor v2](public_actor_r5_v2.json)四命令／29测试通过，首版metadata guard误拒保留历史。

CPU验收未独立留存实际grader HostConfig、apply后新增测试完整源码或8GiB配额强制证明；公开actor桩只验交付。Coder基线430条目已另核。`setup.py` Moto预改已在实际初态，不记作模型业务修改。普通诊断验收不等于训练资格。

## 下一步与历史

等待Qwen实际候选／完整轨迹及其执行审查，再作两模型分析及内部核收；不因有效错修放宽断言。[固定请求](probe_request.json)与[实际发送](../../requests/dvc4166_probe_delivery_20261003_v1.json)保持不变。完整修订史见[此前题卡](history/card_before_coder_a1_20261003.md)，旧v1草案在[history](history/dvc4166-behavior-v1-draft/revision.json)，当前事实见本页及[results](results.json)。
