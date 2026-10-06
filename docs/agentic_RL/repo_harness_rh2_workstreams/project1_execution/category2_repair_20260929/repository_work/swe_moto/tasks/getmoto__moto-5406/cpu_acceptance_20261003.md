# Moto5406：CPU 矩阵与交付验收

2026-10-03。三行矩阵、真实 Claude Code 的公开操作／冻结及原工件 fresh 独立评分均通过题主原件审读。最终非作者结果验收待另行记录，尚未提交基座探针。

本次绑定第五版 `cat2-cpu-r2e078079-swe7-git-20261003-v1`，外部 manifest SHA `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`。使用已审工具 v3，清单 SHA `09f7b6de626c00fba904137b763c8c4c66777cbe1551fbd41812dbce46d2c86c`；cpu-a 原镜像实际 ID `sha256:808c60d962cb94330e499404720a0813fa400a2e86464aabdb47fcaa05aad5f6`，没有派生层。安装仍为 `make init`，评分仍为原二值 F2P／P2P 语义。

| 实际候选 | 原 East2 F2P | 原 26 P2P | 新增 East1 P2P | 实际 reward |
| --- | --- | --- | --- | --- |
| noop | 失败 | 全通过 | 通过 | 0 |
| gold | 通过 | 全通过 | 通过 | 1 |
| 固定 East2 的错误修复 | 通过 | 全通过 | 失败 | 0 |

逐行原始日志均收集并报告 28 条节点，无缺失、跳过或收集错误。最后一行完整断言显示实际 ARN 为 `us-east-2`、期望为 `us-east-1`，两侧表名均为 `messages`；失败确实来自地区错误。正确修复通过全部节点，未因新增检查误拒。原／修订题面示例的真实辅助 pytest 单独保存，不进入正式 reward。

每行候选均由本次基线重新冻结；noop 没有源码变更，另两行仅含 `moto/dynamodb/models/__init__.py`，实际导入源码 SHA 与工件相同。两个评分测试文件已恢复和保护。实测 2 CPU、4 GiB、PID 512、共享内存 64 MiB；三个容器峰值分别约 783／784／764 MiB。安装逐条成功，测试完整结束。三 grader 创建并移除，manager 正常收口，本 run 容器、网络零残留。

新矩阵作业为 `moto5406-cpu-3e222da9e511`，410 件原件回收后 SHA／长度全匹配。原件位于 `runs/category2_repair_20260929/moto_cpu_20261003/moto5406-cpu-3e222da9e511_evidence/`；可追溯的逐参考、日志及工件摘要见[题主结果审读](../../reviews/moto5406_cpu_matrix_owner_readback_20261003.json)。审读只读取保存原件，没有重跑测试。第三版 `baseline_digest_mismatch` 失败及其 104 件证据保持原样，本次未改绑旧工件。

真实 CC 作业 `moto5406-actor-6cd339dc49b2` 退出 0，37 件运输原件 SHA／长度匹配。首请求与同次 prepared 修订公开题面逐字相同，四个请求与轨迹对应三个 Bash 操作，三条命令退出码为 0／1／0，输出未截断。中间的公开复现完整运行一条 pytest，用例因 `test_table` 的实际 East1／期望 East2 ARN 差异失败；已有公开 East1 建表节点完整通过。实际 Python 位于 testbed conda 环境，导入 `/testbed/moto/` 的基线源码。

生产静止屏障确认进程残留为 0、工作区双读稳定、桩与 relay 消息源关闭；落盘导出后移除 actor。FrozenPatch 没有条目，projection 没有源码增量；分派身份、公开身份、材料身份相符，释放后旧分派不能再解析，本 run 容器和网络为空。见[actor 题主原件审读](../../reviews/moto5406_actor_owner_readback_20261003.json)。这是实际 CC 接入与公开操作验证，模型输出来自桩，不是基座模型能力结果。

原 actor 工件的 fresh 评分作业 `moto5406-a2g-386b9ed209c1` 退出 0，100 件原件 SHA／长度匹配。只调用一次正式 grade，消费同一 actor 的原 manifest、baseline、FrozenPatch 和分派身份，没有改绑；基线重建通过，完整收集／解析 28 节点。结果为 reward 0、原 F2P 0／1、P2P 27／27，唯一失败为原 East2 ARN 用例。安装逐条成功、测试完整，峰值约 768 MiB；单个 grader 已移除，容器及网络无残留。见[原工件评分题主审读](../../reviews/moto5406_a2g_owner_readback_20261003.json)。

三个阶段共保存并核验 547 件运行原件。剩余为非作者对实际证据窄核，最小指针包见[结果复核请求](../../reviews/moto5406_cpu_actor_review_request_20261003.json)。通过后只申请版本化基座诊断，不自动授予训练或留出资格。
