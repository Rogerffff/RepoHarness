# 新增F2P的窄扩展成本与消费者

2026-09-30。此页是材料提案的接缝说明，**没有实施生产**。不能把本题塞进现有 `replace_test_patch_append_p2p` 后再把base失败的节点称为P2P。root后续决定新增F2P操作；操作名可以沿命名约定确定，但必须精确区分F2P追加和P2P追加。

| 消费位置 | 当前事实／最低所需变化 |
| --- | --- |
| `envpack/bundles_v2.py` 的修订类型和 `PrivateGradingBundleSWERevision` | 当前新增参考由 `added_pass_to_pass` 提供；本题需精确题目、同文件和一个普通节点的F2P型登记。有效F2P为原4项按原顺序＋新1项，有效P2P仍原5项；禁止重复、交集、原参考遗漏或重排。 |
| `envpack/swe_material_revisions.py` 的 record、pin、loader、`_apply_one`、producer | 独立登记/资产/pin/输出目录；从原216来源重放，只改本题私有评分面和环境包身份。原 `test_patch` 和base文件SHA先验核对；有效完整patch保持原补丁AST。当前 `_apply_one`只更新P2P，新增操作必须更新F2P。 |
| parent恢复与关系重验 | 恢复原test_patch、原4F2P及原5P2P后，重算原grading digest。不能只删新增P2P，也不能拿有效test_patch代替父补丁。public/validation与来源镜像身份不变；新材料资格不能沿旧资格。 |
| `adapters/slime/prepared_task_face.py` 共用builder | 原文件路径保护、revision基线SHA、测试恢复和原命令可复用；新类型须被安全消费者接受。actor/replay都读取新正式producer，构造相同脚本/预算/材料身份，不用私有shell或候选侧条件代替正常测试。 |
| `envpack/spec_vendor.py` 命令派生 | 沿现有MONAI通用同文件派生 `pytest -rA tests/test_box_transform.py`，安装沿原vendor串。只补新类型的正式分派；不增加自由shell、新selector、parser alias或安装修复。 |
| `grading/material_revision.py`、builder context及diagnostics | 当前分区是 `original_f2p/original_p2p/added_p2p`，且要求有added P2P；本题需允许只有added F2P，并单独诊断原4、新1和原5。不得让新增F2P冒充原F2P。旧修订的有效身份/序列化/报告口径须保持。 |
| parser/scoring/report与qualification消费者 | 普通F2P计分可沿既有5F2P+5P2P口径，无需改parser或奖励函数；证明新普通node不缺席/skip，完整十项共同决定reward。材料digest/脚本digest/runtime image身份按新材料重新join，旧资格失效。 |
| 本题CPU工具和相关定向验证 | 按5F2P+5P2P和新分区调整检查；单路noop/gold/2D-only为0/1/0。需窄类型/父恢复/错SHA/交集/旧资格拒绝及actor/replay一致性检查，之后正式三行、真实公开开发和同次原actor完整baseline直评。无需机械重跑旧mypy矩阵或扩大GPU范围。 |

实现至少涉及现有四个材料/构造文件及私有诊断context；不是只换test_patch便完成。确切改动数由root实施审查决定，不能把此估算写成已实施。原通用评分运输、oracle权限、基线excluded census、异常fatal和双层清理继续使用，不因本题增加F2P而绕开。

静态材料已保留原4F2P和5P2P的精确顺序，新增只在 `proposal.extra_fail_to_pass` / `references_candidate.added_fail_to_pass`；没有新增P2P。此材料未被现有生产登记器加载，也未取得环境或训练资格。
