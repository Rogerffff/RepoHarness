# Moto6114：两条既有 Neptune 委托 P2P 的题级裁定请求

2026-10-03。请求按本批已授权题级裁定判断：**是否在保留公开题面、base、原 F2P、34 个原 P2P、ARN/name identity 断言及原预算的前提下，增加两条公开 base 已实现的 RDS façade→Neptune 名称委托 P2P。** 推荐增加，作为新的 `moto6114-cluster-identity-neptune-preservation-v2`，总参考改为 1F／36P；不覆盖原 R7 或原 Qwen raw1。

实际模型 `gpu1003-moto6114-qwen36-a1` 改 `moto/rds/models.py`，公开 describe ARN helper 可查正确对象，但它同时扩到五项写操作并移除了两条原名称委托。非作者静态确定正常创建 available Neptune 名称的 start 原可返回 started、候选新增 stopped 条件拒绝；delete 原可删除、候选先访问不存在的 deletion_protection 属性而异常。现有 35 参考全部通过，所以这是实际候选揭示的评分覆盖缺口，不是设想未要求的新 AWS 功能。

依据：[固定非作者语义报告](../../../reviews/moto6114_qwen_a1_semantics_non_author_20261003.md)，SHA256 `eb30f25349feac4b04d76087e270e76faf318d071647fcdd5a9fd23f7d40c13f`。报告逐原公开 source 和实际 patch 证明，未执行项目或将异常推导冒作运行结果。完整实际模型／源码 pin 见[proposal.json](proposal.json)。GPU 的安装 wheel 权限问题独立处理，不能用它将模型改判为 0。

新[测试草案](proposed_effective_test.patch) SHA256 `2a9661d78743cf5e36f8363e308d63260ab2076bf4bc1d68de8a9e5fd226dda4`。保留旧有效 patch 的全部身份断言，新增两项分别创建独立名称、调用原 backend name start/delete 并检查原返回／存留行为，双 mock 隔离 RDS/Neptune 状态。没有要求写操作的 ARN 支持、跨账户/跨区校验或完整修复原 rename 缺陷。测试属于 P2P 既有行为保留，不改变公开问题。

当前只通过本地文本/AST核对，尚未正式发布、运行或验收。已准备最小 base／实际候选两容器诊断，复用已 CPU 验证的 source、COPY供应镜像、production 初始化及 agent UID54321；其工具在非作者静态核查。CPU 入槽遵守 Mypy 临时优先窗口。裁定如同意，先确认两条原行为实际通过及候选实际失败，再做新材料发布、noop/gold/wrong_first/原实际 Qwen 源码的必要 37 参考对照和非作者核查。预期奖励只是计划，不写成事实。

原 GPU request 保持 claimed，已通知 GPU 暂缓新的 Coder／重复；允许它完成 wheel修复和原FP／原35参考诊断重grade。新测试通过验收后，再以新身份安排原候选重评分及未覆盖的模型尝试；没有对原 FrozenPatch 的 runtime_identity 做静默重绑定，也不以一个 Qwen 样本声称稳定能力。
