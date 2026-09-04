# 《The Interplay of Harness Design and Post-Training in LLM Agents》阅读摘要

## 论文信息

- arXiv:2606.25447v1,2026-06-24 提交
- 作者机构:POSTECH(浦项科技大学,机械智能研究生院与计算机科学系)
- 官方页面:<https://arxiv.org/abs/2606.25447>

## 核心问题

harness(提供给模型的接口信息层:工具描述、每步可用工具列表、状态提示等)通常被当作与训练无关的推理期封装。论文用受控实验回答三个问题:RQ1 harness 信息量造成的差距会不会被 post-training 抹平;RQ2 harness 应该在训练时就位,还是训练后再套用;RQ3 harness-aware post-training 是否影响对工具接口变化与任务分布变化的鲁棒性。

## 实验设计

1. 环境:扩展版 ALFWorld,共 3,827 个任务实例(训练 3,553,测试 274 = 140 seen + 134 unseen);六类任务按难度分组:t-easy(Pick 4 步 / Look 3 步)、t-med(Clean/Heat/Cool 各 5 步)、t-hard(Pick 2,8 步)。
2. 三档 harness(信息量递增):h-low 只有工具单行描述;h-mid 增加每步 valid tool 列表;h-high 再加丰富工具描述与当前持有物品等状态信息。
3. 模型与算法:Qwen2.5-3B-Instruct、Qwen2.5-7B-Instruct × GRPO、GiGPO,共 24 组 post-training 配置(2 模型 × 3 harness × 2 算法 × 2 种训练任务集设定:全任务集 vs 难度特定子集);GPT-5 Mini 只作 zero-shot 参照。
4. 工具接口变体测鲁棒性:v1.0 基础、v1.1 工具重命名(轻微变化)、v2.0 五个工具聚合成新接口(强变化)。

## 关键结果(带具体数字)

- zero-shot 阶段 harness 差距就很大:GPT-5 Mini 在 Pick 2 任务上 h-high 61.0% vs h-low 17.1%。
- post-training 抹不平 harness 差距,还能以小胜大:Qwen2.5-3B + GRPO + h-high 达 69.7%±0.6,比 Qwen2.5-7B + GRPO + h-low 的 55.6%±0.8 高 14.1 点。
- 训练时就位 vs 训练后套用(4.3 节):Qwen2.5-7B + GRPO 下,训练时使用 h-mid 比 h-low 训练、评测时才换 h-mid 高 20.7 点;h-high 对应高 22.5 点。
- 接口变化鲁棒性:h-low 训练的模型在强变化 v2.0 下跌到 2.7%(对照基线 13.5%,低 10.8 点);h-high 模型保持 95.7% 的合法工具调用率,但其中 34.9% 调用不可执行。
- 任务分布迁移:GiGPO 从 h-low 的 28.8% 升到 h-high 的 73.4%(+44.6 点);GRPO 对应提升 +17.5 点。
- 总算力:全部实验约 1,800 H200 GPU-hours(论文 Limitations 部分自述)。

## 重要限制

- 只在 ALFWorld 一个环境验证,结论外推到 SWE/terminal 等重工具域缺乏直接证据。
- 开源模型只有 3B/7B 两档,算法只有 GRPO/GiGPO;更广的模型与算法覆盖被明确留作 future work(受算力预算限制)。
- harness 只有人工设计的三档离散档位,没有对 harness 维度做连续或组合分解。

## 对 RepoHarness 的意义

- 这是 harness-aware post-training 目前最直接的受控证据:同一环境同一算法下,harness 信息量既改变性能天花板、又必须在训练时就位,直接支撑我们 B 线"用目标 harness 训练"的做法。
- 20.7~22.5 点的 train-time vs post-hoc 差距意味着:训练后换 harness 不是免费的;我们若切换 harness 版本,默认假设需要重训或适配训练,而不是直接套用旧 checkpoint。
- 证据边界必须守住:论文只做了"单一 harness 训练→换 harness 评测",没有做多 harness 随机化训练的实验;不能外推为"多 harness 随机化必然学出接口不变性",该假设要靠我们自己的实验回答。
- ALFWorld 是文本游戏,动作空间与工具面远小于 repo/terminal 场景;点数大小不可直接搬用,方向性结论(信息量、训练时就位、接口变化脆弱性)可作设计输入。
