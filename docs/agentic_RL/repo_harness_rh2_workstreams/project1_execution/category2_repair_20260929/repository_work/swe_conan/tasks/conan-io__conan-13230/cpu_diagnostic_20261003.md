# Conan13230：新机草案诊断

2026-10-03。**新草案已能识别原来获分的 Android-only 缺陷；正式验收仍待发布版本与非作者意见。** 题面、候选与补丁字节未改变，本次仅运行已准备的固定草案。

原镜像按manifest `3f7ba164d697c75bf27b917cd2ea794c8ebefbbb3c6954113e1dc1f2d5e62376`拉取，实际config为`sha256:470bafe8634b5ef92f942aef63a818d7dd681ba591548d467a6f25be420806df`，与历史一致。有效测试patch仍为`15834b7e16c8fac6c5386c5ebf1f6ad1df9ad56c67af1c87df6a178f6e374db1`。base HEAD、基线测试/代码和候选应用后的全文SHA逐项核实。

| 私有候选 | 实际收集 | F2P通过 | P2P通过 | pytest RC |
| --- | --- | --- | --- | --- |
| gold | 37 | 3/3 | 34/34 | 0 |
| noop | 37 | 0/3 | 34/34 | 1 |
| android_only | 37 | 1/3 | 34/34 | 1 |

noop 的失败是原Android测试及新增两个Linux节点；android_only的失败恰为新增`no_sdk`与`sdk_sentinel`节点。gold执行并通过最终`toolchain.vars()["CFLAGS"]`断言。三份完整日志共111条精确参考状态，无缺失、重复或skip；不是只读总通过数。

镜像准备job为`conan13230-image-20261003-v1`；诊断job为`conan13230-draft-diagnostic-20261003-v1`。两者均由`cpu_slot.py`持锁等待到结束，外层RC0。诊断复用原`private_behavior.py`，候选串行、2CPU/4GiB、network none；每容器rm/query RC0、残留为空。容器UID0，项目从`/testbed`导入，pytest6.2.5；不能据此宣称新机actor权限已验证。

本次未重跑原安装前缀，未调用D6正式评分器，也没有发布新的共享版本。实测是私有草案行为，不填正式reward，不生成探针请求，不增加训练资格。[非作者材料窄核](../../reviews/non_author_material_review_20261003.md)已完成，四份新测试未见静态阻断；报告早于本次诊断交付，不把其尚待运行描述当新机结论。

原件入口为忽略目录`runs/category2_repair_20260929/conan_cpu_20261003/`：`diagnostic_audit_13230_v1.json`保存逐ID状态；`diagnostic_evidence_13230_v1/output/`保留原日志；`image_evidence_13230_v1/receipt/`保存镜像与拉取记录；`remote_transfer_audit_13230_v1.json`保存远端SHA及作业回执。本地核对62件输入和回传文件SHA全部一致。历史09-29正式0/1/1原件未回写。

下一步使用共用维护者确认的不可变release完成正式0/1/0及必要actor接续，再交统一探针。
