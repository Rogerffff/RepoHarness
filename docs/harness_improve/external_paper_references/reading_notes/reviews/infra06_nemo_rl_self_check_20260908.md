# Infra06 · NeMo RL 作者自查与交付记录

日期：2026-09-08。正文：[packing、动态 batch 与分布式 loss 消费](../infra06_nemo_rl_packing_dynamic_batch_loss.md)。

**状态：指定范围内源码／文档精读与作者自查完成；10 个独立 CPU 语义探针已执行。没有独立 reviewer、上游 pytest、真实模型/GPU 或性能复现。** 本记录不能当作前几批独立审查的延续。

## 1. 版本与范围

主代码为 `NVIDIA-NeMo/RL@13182a5f24a47856aa9191f651510d0df249c9c0`。沿 gitlink 确认 Megatron-Bridge 为 `5ed97996cc2b422904d18179375b6d7366915097`，其 Megatron-LM 为 `1e7598cbfae888cdd3d741a351aae588d56f66c0`。

正文列出完整覆盖表：设计文档、实际 GRPO 入口、一个明确的 Megatron SWE 配置、共同 sharder、四种 packer、TQ 元数据路径、Megatron packed/CP 数据准备、loss/wrapper、MCore scheduler、Automodel 对照和两类上游测试。大文件只检查列出的函数与范围，没有将整个仓库标为已审计。

源码 pin 晚于多个模型报告；不将当前配置／修正倒填为历史 Nemotron 训练事实。官方发布站 latest/nightly 与固定代码分开，兼容性声明不跨版本拼接。

本轮可见项目基线为 `miles-migration@da82518af1de11ebe6fa054c0cb7b73f9502a0a0`。两次 remote branches 列表与一次 search_branches 都只显示 `main`、`miles-migration` 和旧 `codex/repo-harness-verl-stage0h`，无法识别用户所说的新工作分支。因此采用独立文档分支交付，不改动旧业务分支、共享 README、来源目录或其他线程文件。

## 2. 实际回查与修正

| 对象 | 回查了什么 | 最终处理 |
| --- | --- | --- |
| 默认入口 | run_grpo 默认 YAML 的后端选择 | 明确默认是 DTensor v2；Megatron 用另一个实际 SWE 配置说明 |
| 训练单位 | GBS、原始行、packing bin、DP shard、chunk | 不把 B=1 的 packed tensor 称为一次只有一个训练样本 |
| packing 规划 | 先按 optimizer GBS 切分，再装箱；bin 数调整 | 不允许将“全数据重排后再切 step”称为纯布局等价；填 bin 不是复制样本 |
| 对齐公式 | 回 `_get_pack_sequence_parameters_for_megatron` | TP 因子只在 TP+SP 条件适用，不无条件使用 2×CP×TP |
| MFFD 实现 | 完整读取 leftovers 循环 | 保留算法命名与 list 操作的复杂度说明差异；未提出理论界或性能结论 |
| 动态 batch | 跨 DP 按最大长度协调边界 | 单独说明局部最优与全局 collective 顺序的取舍 |
| CP 布局 | raw/padded offsets、逐序列 zigzag、routing | 不按字段名猜 q cumulative 必须是 raw；routing 不做 next-token shift |
| 全局分母 | process_global_batch、masked_mean、主 actor reduction | token/sequence 目标分开；EPS 是加法，不是 clamp；IS 置零不自动重计分母 |
| MCore 缩放 | 沿真实依赖查看两个返回值的 scheduler 分支 | 解释 cp_normalize 与 scheduler compensation 的不同作用，非只引注释 |
| Automodel 缩放 | 实际 backward 的 DP×CP/fanout | 不将 FSDP 平均补偿照搬到 Megatron SUM；CPU 只核标量关系 |
| streaming | begin/chunk/finish hooks、真实计数、裁剪、finalize | 归一化先于裁剪；finalization 不等于只有 DP reduce；aux 分母另查 |
| F1 正样本 NLL | 当前 loss 内部 correct_valid_toks 及 wrapper 调用单位 | 有条件的布局敏感性反例；默认 μ=0 不受该项影响；尚未运行真实 loss |
| F2 置换 | preshard 返回语义、BDD inverse、TQ 调用方 | 发现当前 keyed writes 丢弃可疑返回，因此降为文档／接口风险，不报当前训练错配 |
| F3 host 占位张量 | metadata planner 的 dense skeleton | 128 MiB 是算术示例，不是实测瓶颈；原宽度过小的问题当前已修正 |
| 上游等价测试 | 实际 fixture、断言与默认辅助项 | transport parity、logit 梯度 parity、模型参数更新是三个证据等级 |

这些是阅读时做的事实校准，不是“发现了十五个上游 bug”。尤其 F2 经追踪调用方后收窄了结论；没有为获得更多 finding 而忽略反证。

## 3. 本次真实执行

命令：

```bash
python docs/harness_improve/external_paper_references/reading_notes/probes/nemo_rl_semantics_probe.py \
  --output /tmp/nemo_rl_semantics_probe_results.json
```

实际环境：Python 3.13.5，PyTorch 2.10.0+cpu，CUDA 不可用；设 torch CPU threads=1。只导入 torch 和标准库，没有导入 NeMo/Ray，没有下载模型。

脚本分别验证：全局 token reduction 的三种划分、token 与 sequence 目标差异、非自逆置换、协调 µ 计划、CP 身份标签、packed shift、后端缩放代数、正 NLL 局部分母、全零 mask/NaN、对齐预算及占位张量大小。

**10 个 PASS 包含预期不等的负对照。** 主要可复核值：P01 三种划分梯度误差 0；错误局部均值 5.10 vs 7.8333；P08 NLL 约 2.5 vs 4.0 且梯度不同；P10 指定 int64 张量 128 MiB。

脚本是独立语义模型，不是抽出上游类进行测试。因此 F1 只能称为当前源码同型归约反例，不能标为完整 ClippedPGLossFn 或 GPU bug 已复现。P04 不是调用 BDD；P05 没有实际 CP attention；P07 没有分布式 autograd。

结果文件：[nemo_rl_semantics_probe_results.json](../probes/nemo_rl_semantics_probe_results.json)。脚本注释和解释字段采用中文，技术标识符保留原名。

## 4. 文稿与交付检查

检查引用式链接定义、首屏锚点、脚本语法、数学分隔符、相对文件链接以及结果中的 passed 数量。配套代码和 JSON 与正文使用同一来源 pin；不把本地缓存、原始文档下载失败或未安装依赖写成作者不公开资料。

本轮只交付四个任务专属文件：正文、此记录、CPU 探针、结果 JSON。没有改训练实现、loss 合同、任务集、原有阅读笔记或 NVIDIA 上游仓库。独立文档分支和最终 commit 由交付回复报告，保存前不预填 commit。

## 5. 尚未完成的验证与后续建议

最优先的独立复核是 F1：用实际 NeMo loss/wrapper、非零 μ、rewards、长短正样本和固定 global counts，比较 padded、逐序列和 fused loss 的值与 logit 梯度。然后才扩展到真实模型参数与 DP/CP。

F2 应核所有调用方及最新主分支，确认返回值是否仍未消费；若要提交 PR，以方向清晰的 API 注释和非自逆置换回归为主，不宣称当前已发生错配。F3 应先做真实 host RSS/CPU profiling，而不是根据示意尺寸修改公共数据层。

仍未完成：完整模型支持矩阵、旧 DTensor v1 全路径、所有 VLM 和辅助损失、streaming 故障恢复实测、GPU/NCCL、训练学习曲线、性能基准、最新 issue/PR 去重、用户新工作分支映射和独立 reviewer。需要继续阅读时按正文索引定位，不必再次从零梳理整个仓库。
