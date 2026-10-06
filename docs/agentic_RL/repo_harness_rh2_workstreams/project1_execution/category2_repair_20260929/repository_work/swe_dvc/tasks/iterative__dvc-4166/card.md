# DVC4166 当前题卡

2026-10-04。**双模型首轮已核收：Coder0／Qwen0，均为有效行为失败。** Coder F0/3、P60/60；Qwen F1/3、P60/60。两份候选、完整轨迹、执行原件及非作者语义／执行复核闭合，请求已ACK，活动指针已释放。R14材料和CPU0／1／0保持，不为有效0放宽测试。

公开目标是尾斜杠按文件／目录区别匹配，不能强求issue七种写法等效或隐含子文件重入父目录；固定pathspec0.8.1。Coder只拆regex分组，错误排序曾引入回归后撤销，最终仍未修目录语义。Qwen正确定位裸目录名不匹配尾斜杠，并修了否定尾斜杠；正向尾斜杠父目录仍不匹配，原父目录排除及新增非空目录剪枝两F失败。

## 两模型候选与轨迹

[配对分析](../../dvc4166_6954_two_model_first_round_audit_20261004_v1.md)、[配对核收](two_model_first_round_acceptance_v1.json)、[Coder七维审计](coder_a1_semantic_audit_v1.md)、[Qwen七维审计](qwen36_a1_semantic_audit_v1.md)分别保留原始评分与候选解释。Coder实际66节点63通过／3失败，Qwen64通过／2失败；3个未计分原节点均通过。原FP分别23项（22脚本）／2项（业务源码＋公开测试），评分投影范围单列。

Coder反复错误read/readlines mock、平面匹配误当遍历验证；Qwen使用正确mock并修正导入／正则错误，但没建立真实WorkingTree遍历与同名文件区别回归。Qwen最终29公开＋8追加mock断言通过；工具正文另有真实公开失败及自测试例错误，不能只数is_error。两模型自测均不足以证明目录行为完整。

[非作者配对执行报告](../../reviews/non_author_dvc4166_6954_pair_execution_review_20261004_v1.md)与[非作者Qwen配对语义报告](../../reviews/non_author_dvc4166_6954_qwen_pair_semantic_review_20261004_v1.md)已完整核收；旧Coder范围按原审计和报告固定身份复用。Qwen435成员／baseline430、67工具／66请求／CC68回合，solve201.240秒；Coder653成员／baseline430、89工具／90请求／CC90回合，solve293.626秒。仅两次单次观察，不作稳定速度排名。

两侧实际公开prompt字节、image／HEAD／baseline／预算一致，profile仅模型端口不同；作业前实时engine／adapter／只读模型挂载及HTTP配置另核。Coder模型清单声明28／枚举25文件（16权重分片），Qwen声明40／枚举37（26权重分片），未重复全权重SHA或GPU内存身份验证。baseline环境lineage仍null；有限资源样本、8GiB配额配置与强制生效分别保留，不能推断全程资源峰值或最低配置。hygiene clean也不等于完整FP无脚本／测试改动。

## 当前材料与CPU证据

[revision](revision.json)固定 `dvc4166-behavior-v2-draft`；新增非空目录剪枝F、同名普通文件P、显式父目录可见性与否定目录恢复F。原两个前导空格case以显式ID映射，保留输入／断言，通过题级消费者绑定，不改全局parser。

[正式矩阵](formal_matrix_r14_v1.json) noop0／gold1／去正向尾斜杠0，各66实际／63参考、3F／60P。负例实际64通过／2失败，落在新增否定目录F和普通文件P；不推断旧原版正式reward。[CPU验收](cpu_acceptance_r14_v1.json)与[非作者正式读回](../../reviews/non_author_formal4166_r14_runtime_review_20261003.md)已核UID54322预检／安装、完整节点及两层清理。[公开actor v2](public_actor_r5_v2.json)四命令／29测试通过，首版metadata guard误拒保留历史。

CPU验收未独立留存实际grader HostConfig、apply后新增测试完整源码或8GiB配额强制证明；公开actor桩只验交付。Coder基线430条目已另核。`setup.py` Moto预改已在实际初态，不记作模型业务修改。普通诊断验收不等于训练资格。

## 下一步与历史

首覆盖完成，进入候选错误与训练信号分析；普通追加采样暂缓，无当前必跑CPU／GPU缺项。稳定性、训练／留出资格及最终用途未判定。[固定请求](probe_request.json)与[实际发送](../../requests/dvc4166_probe_delivery_20261003_v1.json)SHA不变。此前状态见[Qwen返回前题卡](history/card_before_qwen_pair_20261004.md)、[更早题卡](history/card_before_coder_a1_20261003.md)及[旧v1草案](history/dvc4166-behavior-v1-draft/revision.json)；当前结构记录见[results](results.json)。
