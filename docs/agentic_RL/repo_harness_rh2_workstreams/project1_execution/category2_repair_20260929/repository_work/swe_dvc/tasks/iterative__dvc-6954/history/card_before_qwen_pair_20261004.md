# DVC6954 当前题卡

2026-10-03 19:30 SGT。**Coder 首臂 reward 1，3F／12P 全过，实际26节点全部通过。合法负整数、浮点及容器负数修法正确；Qwen 首臂待返回。** R14 CPU 控制及非作者验收已完成。一次通过不代表完整表达式语义或稳定性。

公开目标是合法Python负数能读取并进入run／repro与lock。候选对USub递归取值再取负，复用原容器的scalar helper，真实CLI负数repro成功。新增UAdd对字符串、USub对非数字的静态边界未保证；当前冻结任务不扩非法operand或算术表达式规范。

## 首轮候选与轨迹

[题主七维审计](coder_a1_semantic_audit_v2.md)、[逐件原件读回](coder_a1_owner_evidence_readback_v1.json)、[非作者语义报告](../../reviews/non_author_dvc_three_coder_a1_semantic_review_20261003.md)已完整读回。范围是本次 Coder 首臂；[原轮次执行证据独立报告](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/closed_four_execution_non_author_20261003_v1.md)已另行交付并核收，没有新增执行矛盾，仍不代表成对请求闭合。完整 FP 有 6 项，其中 5 个根目录脚本，原件不删改。

真实CLI成功未断言lock数值与改值重跑；二元表达式自测由错误raises改成无断言；UAdd字符串／USub非数字静态边界未获保证；FP保留5个脚本。实际服务有作业前 engine／adapter、只读模型挂载、argv／HTTP 配置绑定；列出的 25 个模型文件大小匹配，其中 16 个权重分片，声明计数 28 与列表 25 不一致。没有重新全权重 SHA 或 GPU 内存证明。baseline 的 `environment_package_digest` 仍为 null，不能用 prepared 环境摘要补填；资源采样缺口与独立脚本未留存的限制保留。

本轮请求保持 claimed／active，Qwen 首臂待返回，不提前 ACK／returned 或清活动指针。覆盖优先，暂缓未开始的普通重复；本次结果不决定稳定性或训练／留出用途。固定 probe 输入 SHA 不变，材料与原题面／中性说明未热改。

作者v1把弱自测的 `expr = 1 + 2` 错写成sum调用；[v2](coder_a1_semantic_audit_v2.md)仅更正原代码引用，v1与正式非法sum／constructor参考仍各保留，未修改原件或重评分。

## 当前材料与CPU证据

[revision](revision.json)固定 `dvc6954-behavior-v1-draft`。原13个case仅映射安全ID，原输入／断言保留；新增负浮点／容器及真实run→lock→不变跳过→改浮点repro／lock两F。

[R14正式矩阵](formal_matrix_r14_v1.json) noop0／gold1／int-only0，各26实际／15参考、3F／12P；11额外原有功能节点通过。int-only仅失败新两F，旧原版正式成绩未知。[CPU验收](cpu_acceptance_r14_v1.json)与[非作者正式读回](../../reviews/non_author_formal6954_r14_runtime_review_20261003.md)完整核节点、UID54322预检／安装及两层清理；[新增单测完整文件](actual_new_file_capture_r14_v1.json)1624字节／56行与effective patch相同。[公开actor](public_actor_r5_v1.json)11个测试通过。

CPU没有独立完整grader HostConfig或8GiB强制配额证明；公开actor桩只验交付，模型基线552条目另核。正式新增lock／改值行为不补写成模型自己测试过。

## 下一步与历史

等待Qwen实际候选与完整轨迹，再核两模型语义、执行审查和内部请求；不为取得高分重采样或扩大非法表达式评分。[固定请求](probe_request.json)及[发送回执](../../requests/dvc6954_probe_delivery_20261003_v1.json)不变。[此前题卡](history/card_before_coder_a1_20261003.md)保留历史，当前事实见本页与[results](results.json)。
