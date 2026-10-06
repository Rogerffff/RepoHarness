# Moto6408 R18 noop：作者原件读回

2026-10-03。固定 R18 离线供应的 noop 已正常完成；这份报告只关闭 noop 安装及参考预检，不授予整题 CPU、actor 或模型资格。

作业 `moto6408-cpu-81c24ca0fe48` 远端父退出0，完整回收45件原件并逐SHA/bytes复核。archive SHA `b2cf1cbe510050faf05d2837ea04d1fe69825aa80819827d63199ae362f84ffa`；manifest SHA `e74cecd71ced4480654382e630460d4a51e90211dc58cd11d2af95a509aab2ec`。

实际消费者为 `cat2-cpu-r2e093-swe40-moto-offline-20261003-v1`，外部manifest `a84bdc339618e010440df3728c982b2d1d141b1f8295f69761984386ee3a512e`；actual COPY-only镜像 `sha256:f00e022c3edf2dd23121abab802e401a64ee9e98598f07fb37a83d5c4c2012a1`。新版ENV、评分脚本、有效测试patch及1F/95P分区逐键与固定expected吻合。

原 `make init` 真正完成且退出0，耗时10.659秒；原完整pytest运行12.030秒，退出1；CLI包装退出0与pytest退出1分别保留。实际收集96项、parser96键，无重复、缺失或skip。原F失败，95P全通过，raw reward0。完整失败位置为 `tests/test_ecr/test_ecr_boto3.py:630`：标签先指向image_001、再移动到image_002后，查询仍返回第一个manifest；属于原标签归属语义问题。

完整安装输出证明editable wheel成功构建并安装；没有复用旧R13安装2结论。trusted restore/apply均成功，patch只由原consumer应用。candidate删除成功；完整CLI footer的manager containers_open/supply_open/cleanup_failures均空、halted/aborted空、final exit0；两项自有容器/网络查询rc0、stdout/stderr空。

原件和逐参考读回位于 `runs/category2_repair_20260929/moto_cpu_20261003/moto6408-cpu-81c24ca0fe48_evidence/` 与同目录 `_author_raw_readback_r18_v1.json`。gold/reorder_only、实际UID安装与公开CC操作及最终非作者审查仍需完成。旧R13三次安装2及原得分不回写。
