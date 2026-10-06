# Moto5960：R18 noop 安装预检实际读回

2026-10-03。作业 `moto5960-cpu-eeaa3dd27a5d`，固定 R18 `cat2-cpu-r2e093-swe40-moto-offline-20261003-v1`；原 R13 安装退出2的运行证据保留。新镜像 `sha256:4bafbb6965ff41c0f6eb50a73f831e7b62c41b5beda6ffad957fbc926c2359ac`。

原 `make init` 在 candidate UID54322 下完整完成，退出0，10.346秒；日志显示离线 editable wheel 构建和原 Moto 安装成功。测试实际退出1、28.048秒，CLI wrapper和外层父job均0；raw reward0，表示 noop 保留原题三个失败。它不代表整题已验收。

实际收集159项，短摘要156P／3F；parser158唯一key与参考集3F／155P逐项对应，没有缺失或跳过。历史空格参数的两条实际项 `use attribute name`、`use expression attribute name`均PASSED，合为同一个parser key；没有修改parser或用总数替代逐项读回。三失败准确为 GSI INCLUDE、GSI scan KEYS_ONLY、LSI KEYS_ONLY 原语义断言。

45个回收原件全部核SHA/bytes。归档SHA `0765a8fe269f1aa61b81b577fabba8183290018a189144972ef70048dd27ceb0`，manifest `3877ebd1f0f953f3635bf6583db8b5a44e75707dc6d3054675fd01415fb31efa`。受信测试补丁／材料上下文／脚本身份均与固定R18消费者相同。CLI footer rows1、halted/aborted空、manager关闭和final status0；候选删除成功，作业标签容器/网络两查询均0且为空。

原件目录 `runs/category2_repair_20260929/moto_cpu_20261003/moto5960-cpu-eeaa3dd27a5d_evidence/`；逐参考作者读回 `runs/category2_repair_20260929/moto_cpu_20261003/moto5960-cpu-eeaa3dd27a5d_author_raw_readback_r18_v1.json`。后续在同条件下跑gold和omit_keys_only，再完成实际公开UID安装与非作者结果验收。当前没有CC自主模型尝试或训练资格。
