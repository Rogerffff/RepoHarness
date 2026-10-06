# mypy CPU独立核查输入

2026-10-03。本包作者尚未安排新修订正式评分。下列已执行证据可以先核，正式发布矩阵补齐后仅查受影响增量。审阅者应披露已见题卡、作者回读、gold与私有材料的范围；这次审查不要求fresh公开上下文，也不替代既有fresh题面审。

## 本轮实际证据

| 范围 | 本地原件（运行根下） | 作者回读（本包题目录下） |
| --- | --- | --- |
| 10174原正式矩阵 | `cpu_a_round1/mypy10174-original-r2-20261002T171442Z-f5b43f/` | `python__mypy-10174/original_cpu_readback_20261003.json` |
| 15184原正式矩阵 | `cpu_a_round1/mypy15184-original-r1-20261002T174349Z-51ce62/attempt/` | `python__mypy-15184/original_cpu_readback_20261003.json` |
| 两题私有行为 | `cpu_a_round1/mypy-private-controls-r3-20261002T173657Z-cdd6d3/` | 各题 `private_behavior_readback_20261003.json` |
| 15184嵌套case首版失败 | `cpu_a_round1/mypy15184-nested-r1-20261002T175423Z-e27fcb/attempt/` | 第二版回读的首版失败说明 |
| 15184嵌套case有效版本 | `cpu_a_round1/mypy15184-nested-r2-20261002T175739Z-090d84/attempt/` | `python__mypy-15184/nested_guard_cpu_readback_20261003.json` |
| 真实CC两题公开命令 | `cpu_a_round1/mypy-actor-r1-20261002T180207Z-3a9dcf/attempt/` | 各题 `actor_cpu_readback_20261003.json` |

完整运行根为仓库的 `runs/category2_repair_20260929/repository_work/swe_mypy/`，被Git忽略。候选、有效测试补丁和题级提案在本包题目录的 `private/`、`revision_proposal.json`；不要用上传input_v1的旧15184五P2P提案。SSH凭据不属于审查报告；本地已取回原始逐项日志、ledger、diagnostics和包装器状态。

## 核查问题

1. 原正式矩阵与私有root行为确实分开记录，不能以wrapper0当题目通过，也不能以私有case状态当新正式reward。10174原0/1/1，15184原0/1/1/1；确认每个成绩对应实际源码候选及原三参考。
2. 逐参考在collect、执行、解析中的真实节点/状态、缺席/跳过和额外未评分节点；0.820节点没有.test层，1.4有.test层。15184公开actor选出六项，含Self；私有正向校准选出五项，新正式拟五参考不是上述计数相加。
3. 安装各子步骤确实成功、mypy源来自/testbed、宿主release/manifest、runtime、镜像及HEAD一致、runner摘要未变、未把infra失败当错解拒绝。10174原正式矩阵用旧runtime成功，后续作业用runtime_v2；不合并成同一运行。
4. 新10174 P2P应base/gold通过、关闭非strict-optional比较的候选失败。新15184 P2P应拒绝有效断言全部报错；嵌套F2P应base/top_only失败、gold通过。嵌套首版的list/List格式错误须保留，第二版依据公开suite格式且原三case正文不变。
5. 实际actor是CC2.1.205、UID54321、2CPU/4GiB、精确派生镜像，activation和prelaunch成功，无宿主bind/mount，公开命令实际0/1/0/0/0、输出未截断，容器/网络/relay/stub正常清理。10174镜像初态已经修改test-requirements.txt；COPY-wheel派生和此次命令未新增此变化。15184干净。
6. 冻结normal场景遗留的`bashenv_denied_for_agent=False`在本清单是未执行对应写入命令导致，报告须披露未测，不声称所有checks通过。prelaunch已有ACTIVATION_WRITE=DENIED与实际激活证据，按本轮actor条件验收范围判断，不扩成全隔离角色审。
7. 待新版本矩阵完成后，核正式public/grading/material/revision/选择/保护及基线身份，10174预期0/1/0、四参考；15184预期0/1/0/0、五参考。实际成绩为空时不能批准探针就绪。

15184正式solver新题面实际交付还需新release/探针链证据，开发控制prompt不能替代。报告区分材料窄审、CPU作者证据、独立验收和GPU资格；不新增训练/留出资格。若发现错解仍reward1、gold被误拒或安装/保护/源码异常，保留原件并返回具体节点和条件。
