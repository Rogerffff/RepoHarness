# Moto5406 最终旧隔离 consumer／runner 窄核

2026-10-03。审查者为本仓库题主，未编写被审 consumer 或旧 runner；已见私有评分与反例，不是公开 fresh 盲审。本轮只核 `d6_moto5406_implementation_v1/code_v1` 的最终 R-f／已有 P2P 联动和旧工具接缝，不重审历史 CPU、既有公开阅读或全套设计。未修改被审源码、旧材料或工具。

**未发现该范围内必须先修的缺陷。** 本地定向 consumer 检查为 22 passed；实际调用旧 `replay_acceptance.py` 默认准备入口成功，得到 `prepared_static_join_only_no_docker`，没有执行 Docker 或评分。这个结论供统一发布者移植与集成核对使用，不能代替新 release 的审查和 CPU 验收。逐文件身份、测试及产物指针见 [检查记录](moto5406_consumer_narrow_review_20261003.json)。

## 核到了什么

- R-f 仅接受原题目、base、来源公开摘要和两处原表名；新公开摘要为 `sha256:1b128b3d708c1a29956bf4e846b81248ec77bd4ecd710f83b9f7a3ab6ca1e39e`。正式 producer 与 consumer 都从可信原件重放这两处修正，不接受运行时自由 prompt。
- 评分登记绑定该新公开身份；保留原 test patch 字节、1 F2P 和 26 P2P 顺序，只追加既有 East1 节点形成 28 参考。父评分面重建核摘要，固定路径／节点不允许 shell 或自由选择器。
- 实际受信 prepare 输出的公开 prompt 与修订公开包相符，私有 test patch／评分修订标识不进入公开面。actor 与 replay 生成同一材料和脚本；旧 prepared 配新 host、旧 public／environment 的 dispatch 均被拒绝。
- 原受测文件和追加节点所在的既有文件都纳入恢复／保护。定向 shell fixture 的内容及符号链接篡改被恢复，原补丁按原字节应用；候选投影剥离这两份测试改动。该 fixture 不执行 Moto 测试。
- 旧 runner 的材料／运行镜像核对已接受本次实际 5406 镜像记录和最终 producer；脚本仍为原 `make init`，实际默认入口核 actor／replay join、分区、命令与 profile。正式三行路径会检查逐参考状态、安装错误、完整日志、实际候选源码和自己 label 的容器／网络清理；没有改 reward 或 parser。

22 个本地检查来自四个现有函数：真实 prepare／dispatch 混配、完整材料与其它 215 行、18 种模型语义篡改、两种测试文件恢复。没有重跑作者的 282 项全套检查，也没有执行来源题目、SDK、CC、容器或新评分。

## 哪些仍未完成

`tools/moto5406_acceptance_0930_v1/common.py` 的 `DRAFT_PENDING_PRODUCER=True` 仍保留，`--execute` 仍拒绝。本题主没有因静态入口成功而取消闸门。统一维护者正在将最小实现移植至新的不可变候选；新版本需要重新核其实际 pins、producer 与代码身份，旧检查记录不能直接覆盖新版本。

发布后仍需在新宿主执行 28 参考 noop／gold／constant_east2 的 0／1／0，保留修订例与原例的辅助对照；真实 CC 首请求必须逐字匹配修订公开 prompt，完成公开开发、正式冻结工件和独立 grader 的关联及清理。当前无新正式发布、CPU／actor 通过、探针提交或训练资格。
