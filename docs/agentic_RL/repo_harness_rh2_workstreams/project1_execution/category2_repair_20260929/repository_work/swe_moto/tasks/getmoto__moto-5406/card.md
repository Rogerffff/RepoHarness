# Moto5406：地区 ARN 与公开表名

2026-10-03。当前：第五版新工件三行矩阵 0／1／0，28 参考完整；真实 Claude Code 的修订公开题面、开发操作与冻结通过。原 actor 工件 fresh 独立评分得到完整 28 节点的 noop 0，清理通过；[最终非作者结果复核](../../reviews/moto5406_cpu_result_coordinator_review_20261003.md)通过，单题探针请求已提交通知，待统一执行者核验。第三版旧基础设施失败保留。

**问题与有效证据：** 原 27 参考对 noop／gold／constant_east2 为 0／1／1；另跑公开 East1 节点时 constant_east2 失败。原公开示例的 create／describe 名为 `mock_Foundational_AMI_Catalog`，期望 ARN 却用 `test_table`。已有正式修订设计只替换两处表名，新公开读者已核，没有新增要求。

**接续修订：** 保留原测试补丁，追加 `test_dynamodb_create_table.py::test_create_table_standard` 为 P2P，总参考 28。公开修订与评分修订须一起绑定有效 public digest。复用隔离 `code_v1`，不另造一套实现。

本轮重算材料 manifest 中 111 个资产的 SHA 和长度，全部匹配。[旧 consumer 非作者窄核](../../reviews/moto5406_consumer_narrow_review_20261003.md) 的 22 项本地检查通过；随后[发布移植核查](../../reviews/moto5406_publisher_integration_review_20261003.md)和[工具 v2 核查](../../reviews/moto5406_tools_v2_root_review_20261003.md)完成。第三份 CPU 发布的默认 prepare 在 cpu-a 成功，actor／replay spec相同、坏 dispatch 被拒、原 `make init` 与 28 参考保持。正式首行的两侧 1685 条 included 记录完全相同，仅 excluded 的 Git pack／idx 文件名不同，触发 `baseline_digest_mismatch`；未进入测试评分。本 run 清理零残留，完整 104 件证据已核 SHA／长度，详见 [CPU 状态](../../cpu_preparation.json)。旧版本和基线保留；第五版及工具 v3 已生成全新工件，三行均完成真实 fresh grade，得分 0／1／0；原始日志确认错误 fixed-East2 仅新增 East1 节点失败。真实 CC 实际首请求与修订公开题面相同，三条公开命令完整执行，导出 no-op 后清理完成。见 [当前验收](cpu_acceptance_20261003.md)。

**后续矩阵：** noop 0、gold 1、constant_east2 0；逐项核原 East2 F2P 与新增 East1 P2P，原表名例及修订例的 base／gold 辅助对照另列。需证明 actor 收到修订版公开消息，不能让运行器临时替换 prompt。

当前允许版本化基座诊断；还没有模型结果，训练、留出资格未授予。范围不扩展到 stream／SSE／backup／CloudFormation。

原件：[材料包](../../../../swe_materials/moto5406_next/README.md)、[实施 Brief](../../../../d6/moto5406_implementation_brief_20260930.md)、[公开修订补充](../../../../d6/moto5406_public_revision_addendum_20260930.md)。新准备入口：[preparation.md](../../preparation.md)。
