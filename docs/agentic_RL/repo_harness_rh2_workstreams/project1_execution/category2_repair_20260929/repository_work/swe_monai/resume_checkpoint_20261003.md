# MONAI：三方流程恢复检查点

2026-10-03 04:37 SGT。依据已批准的[三方流程](../../coordination_workflow_20261003.md)和[总账工具](../../task_board_usage_20261003.md)，行政暂停已解除。本线程继续负责 2446、3715、6975 的 CPU 验收、非作者核查、探针分析和必要修复。

- 实际 cpu-c `control/dispatch_paused` 已不存在；只读回执为 `runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/resume-gate-read-1ac4e5e9.json`。门控由共用维护者负责，本线程未修改 control/setup。
- 2446 发布请求 `swe-monai2446-shuffle-nib4-publish-20261003-v1` 已入账：[固定输入](materials/2446/publish_request_v1.json)，SHA `3e93dfa9fa5dd19713c3c7d1df1bb315e289f9ae669b346aabce4b7e95c9831c`。限定单文件 P2P＋E11 NiBabel4 配方；正式 reward 矩阵尚未执行。
- 6975 发布请求 `swe-monai6975-dict-pixels-publish-20261003-v1` 已入账：[固定输入](materials/6975/publish_request_v1.json)，SHA `ff4783bfc2c8dc4fc9f6543023b94a57cc790ba48071653c65aa20195e7c5c97`。保留 Compose/Dataset 两文件和原参考次序；正式新节点与 64 参考结果尚未执行。
- 两个发布请求已合并一次直接通知登记发布线程，真实发送回执为 `runs/category2_repair_20260929/repository_work/swe_monai/coordination_20261003/publisher_message_receipt_v1.json`；各请求 notice 已登记。没有抄送巡检线程。
- 3715 原探针请求 `swe-monai3715-string-modes-r5-20261003-v1` 及 SHA `6a348f0a92f54a054eacf3e51d22cb14f769fb8d7d13f11d279a1889c0b14d67` 原样保留，总账版本仍为 `binding-sha256:b3b1f1914810993c8f9980534aed5f456382de638a9af39388f8f9cb48232cbd`，未重提。CPU 资格已验，GPU 实际准入与原公开提示交付由执行者核验。
- 新作业 `monai6975-image-20261003-f121f560` 已提交，并已观察到 prepare 槽0实际入槽；174 件 SHA 通过。公开 actor 首次申请 `monai-2446-actor-20261003-968e050d` 返回 busy75、未执行；空槽出现后新申请 `monai-2446-actor-20261003-b6bf42bd` 已入 run 槽1。它使用 release5 原 public 与已验 NiBabel4 实际镜像；该2446 actor已完成、四条公开命令符合预期；6975原镜像亦完成，后续actor确认原图缺失。当前详见preparation入口和6975逐题证据，不能把作业提交或外层RC0当题目验收。

[旧暂停记录](pause_checkpoint_20261003.md)保留为当时零在途的历史证据，不再是当前执行闸门。当前情况继续维护在 [preparation.md](preparation.md)、[preparation.json](preparation.json)和总账 progress。回执先核 SHA 与实际发布/部署范围，再 ack 并清活动指针；材料变化另建请求，不改已冻结输入。
