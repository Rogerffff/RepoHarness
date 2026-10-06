# Moto7584：R13 noop 预检

2026-10-03。作者原件读回全部检查通过，尚非整题 CPU／非作者验收；其余十个控制臂、UID和公开 CC 操作未完成。

固定 R13 manifest `3fad18daff8db219294e10cbf08d4424d68cf7000d008bb983cba4bdc427b641`，matrix v2 manifest `6cd02683d46370adf553531064f29d99a1e9da47ebf9f3c909f1bc6fdb9d1fd3`。job `moto7584-cpu-a9dd947080c8` 在共用 slot 实际从00:52:48到00:58:08 UTC执行，子进程最终0；只选 noop，没有运行其它臂。此前all11尝试75未开始，保留为独立尝试。

实际安装退出0、11.066秒，测试pytest退出1、1.874秒，包装exec退出0，raw0／unresolved／tests_failed。collected20、raw摘要20、parsed20；原1F失败／19P逐项通过，无 missing／skip／重复key。目标失败体位于原有效测试475行：删除从未订阅的endpoint后，publish未抛应有ClientError（DID NOT RAISE）。原完整测试命令、有效patch、材料/环境digest和五份诊断脚本SHA均匹配本题固定消费者；可信恢复/应用/保护完整。没有因此预告gold、其它负对照或两个合法正对照得分。

实际 grader 镜像绑定 `sha256:990e0e91a190f85426e6900828cf758c30f389c927f6c1d0cd1ed8c68b902f96`，与本题注册COPY-only供应一致。候选removed=true、CLI终局和自有label容器/网络查询成功且无残留；资源/UID仍按既定专门核查补齐，不把普通ledger policy替作所有实际inspect。

45件原件归档SHA `bd6ca3c48188f6b3c2dc3696812cef81e4aeb14421dfd833ac91a0e5155d9091`；transport manifest SHA `98c38af9736ae5f23fe2eabb7a8480e325a416e70884ae151a97d4467ee027bd`，SHA与长度逐项核对、原件未改。eval log为41122B／`837b6752d7f165f27d5167101fe50e40d4f65bcd9e6dcc23b6688cf23f78e1c6`。证据根 `runs/category2_repair_20260929/moto_cpu_20261003/moto7584-cpu-a9dd947080c8_evidence`；逐参考作者读回见 `runs/category2_repair_20260929/moto_cpu_20261003/moto7584-cpu-a9dd947080c8_author_raw_readback_v2.json`。

下一项在发布者6408短prepare窗口关闭后，经正常公平名额只运行剩余十臂；不为取得全臂单job汇总而重复noop。合并结果时明确两job相同固定材料/配方与各自原件，必要非作者验收再裁定是否覆盖完整矩阵。
