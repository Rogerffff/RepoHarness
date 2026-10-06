# DVC6954 当前题卡

2026-10-04。**双模型首轮已核收：Coder1／Qwen1，各3F／12P全过，实际26节点全部通过。** 两份合法负整数、浮点和容器负数候选修法成立；完整轨迹、执行与非作者复核闭合，请求已ACK、活动指针已释放。R14材料和CPU0／1／0保持；单次正确不代表完整表达式语义或稳定性。

公开目标是合法Python负数能读取并进入run／repro与lock。两者均对USub递归取值再取负、UAdd取正，复用容器scalar helper。非数字一元运算可能泄漏TypeError，当前冻结任务不扩非法operand或二元算术规范。

## 两模型候选与轨迹

[配对分析](../../dvc4166_6954_two_model_first_round_audit_20261004_v1.md)、[配对核收](two_model_first_round_acceptance_v1.json)、[Coder更正后审计](coder_a1_semantic_audit_v2.md)、[Qwen七维审计](qwen36_a1_semantic_audit_v1.md)完整区分正式成绩、正确范围与自测质量。完整原FP Coder6项（5脚本），Qwen仅一个业务源码；评分投影范围单列。

Coder真实CLI成功，却未自动断言lock数值／改值重跑；二元表达式自测从错误raises改为无断言。作者v1把expr=1+2误写sum，v2只改引用，历史v1保持。Qwen真实CLI可见负整数／浮点lock，另有parser／容器断言，但用force做改值，未验不变跳过／自动改值触发。其扩展实验9项中4通过／5失败；仅一个节点stash至原基线仍失败，另外四个原因未确定。最终只报两模块31通过，遗漏已观察的扩展失败，不能归为环境全失败或五个新增回归。

[非作者配对执行报告](../../reviews/non_author_dvc4166_6954_pair_execution_review_20261004_v1.md)与[非作者Qwen配对语义报告](../../reviews/non_author_dvc4166_6954_qwen_pair_semantic_review_20261004_v1.md)已核收，旧Coder范围固定复用。Qwen417成员／baseline552、42工具／43请求／CC43回合，solve56.742秒；Coder600成员／baseline552、36工具／37请求／CC37回合，solve60.305秒。不作稳定速度／能力排名。

两侧实际公开prompt字节、image／HEAD／baseline／预算一致，profile仅模型端口不同；作业前实时engine／adapter／只读模型挂载及HTTP配置另核。Coder模型清单声明28／枚举25文件（16权重分片），Qwen声明40／枚举37（26权重分片），未重复全权重SHA或GPU内存身份验证。baseline环境lineage仍null；有限资源样本、8GiB配额配置与强制生效分别保留，不能推断全程资源峰值或最低配置。hygiene clean也不等于完整FP无脚本／测试改动。

## 当前材料与CPU证据

[revision](revision.json)固定 `dvc6954-behavior-v1-draft`。原13个case仅映射安全ID，原输入／断言保留；新增负浮点／容器及真实run→lock→不变跳过→改浮点repro／lock两F。

[R14正式矩阵](formal_matrix_r14_v1.json) noop0／gold1／int-only0，各26实际／15参考、3F／12P；11额外原有功能节点通过。int-only仅失败新两F，旧原版正式成绩未知。[CPU验收](cpu_acceptance_r14_v1.json)与[非作者正式读回](../../reviews/non_author_formal6954_r14_runtime_review_20261003.md)完整核节点、UID54322预检／安装及两层清理；[新增单测完整文件](actual_new_file_capture_r14_v1.json)1624字节／56行与effective patch相同。[公开actor](public_actor_r5_v1.json)11个测试通过。

CPU没有独立完整grader HostConfig或8GiB强制配额证明；公开actor桩只验交付，模型基线552条目另核。正式新增lock／改值行为不补写成模型自己测试过。

## 下一步与历史

首覆盖完成，进入题组训练信号分析；普通追加采样暂缓，无当前必跑CPU／GPU缺项，不扩大非法表达式评分。稳定性、训练／留出资格及最终用途未判定。[固定请求](probe_request.json)与[发送回执](../../requests/dvc6954_probe_delivery_20261003_v1.json)SHA不变。[Qwen返回前题卡](history/card_before_qwen_pair_20261004.md)及[更早题卡](history/card_before_coder_a1_20261003.md)保留，当前事实见本页和[results](results.json)。
