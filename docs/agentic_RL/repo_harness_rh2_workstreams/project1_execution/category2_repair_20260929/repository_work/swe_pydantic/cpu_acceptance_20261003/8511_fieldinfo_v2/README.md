# 8511 v2：177 参考正式 CPU 验收入口

2026-10-04 接续。R26实际发布及cpu-a部署已核收；[固定输入](formal_inputs.json)、actor/host spec join与11件远端上传身份核验通过，**随后独立核查发现三份实际评分脚本丢失`tests/test_dataclasses.py`，扩大为全仓测试，R26固定输入已阻断；尚未派发新矩阵。** [原件与题主读回](../../coordination_20261003/8511_v2_test_target_preflight_block_v1_20261004.json)保留SHA/具体行号；共享修复请求`swe-pydantic8511-v2-test-target-support-20261004`已落账并真实通知。identity join相等只证明两端一致，不能证明目标命令正确。[独立输入报告](../../reviews/non_author_8511_v2_input_review_20261004.md)不通过，题主92绑定核收；修复发布后只补受影响delta。[v2 材料](../../tasks/pydantic__pydantic-8511/revisions/pyd8511-behavior-v2/README.md)只追加四项既有 P2P；[直接行为诊断及非作者核收](../8511_fieldinfo_retention_diagnostic_v1/actual_v3_readback.md)证明新增组合的基线语义，不代替本轮正式评分。

`run_formal.py` 逐字复用已独立核查的 R14 四题入口，本轮固定输入只含 8511。生成器必须从实际新发布回执、全部 release 成员、正式 public／grading／environment 行和已封材料逐件校验后生成；生成器现已从真实R26完成固定输入；[题主核收](../../coordination_20261003/8511_v2_publication_owner_readback_v1_20261004.json)逐件验证1528 release成员及21份原件拷贝。新输入不得覆盖父 R14。

唯一矩阵按 noop／gold／narrow／原 Qwen 源码顺序执行，预期奖励 0／0／1／0。每行都须保留完整 177 参考终态、安装各步退出码、精确镜像／core／源码及新有效测试身份、受保护私有测试 UID 与不可写性、FrozenPatch 运输、评分分区和完整日志。noop 与 narrow 的四个新节点应全部通过；原 Qwen 原 173 应保持通过而新增四个失败。gold 既有三类继承失败保留，不把 gold 当作新版正对照，也不预先宣称其余新节点终态。

公开public行、base、派生镜像、E10配方、core和题面保持；environment仅关联grading摘要从旧版更新至受审v2，其余字段保持。此范围内，旧 8511 公开 actor 的 source/base 交付事实可按原已验范围复用；新 consumer 的实际 prepare 与 actor/host grading spec join 仍须核查。不会把私有测试交给 solver，也不把有限公开 actor 复用扩成 typed 训练验收。

所有 Docker 运行走 cpu-a 公共 run 槽，独立 job/run ID、自有包输出。原评分准备／测试／清理预算保持。首次新 infra、身份错配或清理未知即保存原件并 scoped hold，不自动重试、加预算或热换 release。自然结束后实际核源、逐参考、异常归因、精确 CID/网络和 PID1 终态，再做非作者实际验收。通过后只申请原 Qwen 完整 FP 在新版本下补评分，新模型采样为 0；旧 173/raw1/FP 保持原件。
