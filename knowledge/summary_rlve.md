# RLVE：使用自适应可验证环境扩展语言模型强化学习

## 论文与定位

- 论文：<https://arxiv.org/abs/2511.07317>
- 官方代码：<https://github.com/Zhiyuan-Zeng/RLVE>
- 核心定位：训中的 `policy-relative curriculum`。它根据当前 policy 的真实 rollout 表现，为每个环境家族独立调整生成难度。

## 环境与算法

一个环境定义为 `E=(I, P, R)`：输入模板、按难度生成问题的程序、算法 verifier。每个环境有整数难度 `d`。

每个环境家族独立维护难度窗口 `[l, h]`：

- 初始 `l=h=0`；
- 从窗口均匀采样；
- 累计当前最高难度 `h` 上的正确数和尝试数；
- 样本足够且准确率达到 90% 后令 `h += 1`；
- 窗口长度为 4。

训练使用 slime + DAPO/GRPO：batch 128、oversampling 384、每 prompt 16 rollouts、partial rollout、TIS correction。论文用 `effective prompt ratio` 表示一组 rollout 中 reward 不完全相同、能产生有效 advantage 的 prompt 比例。

## 核心实验

- 人工构建 400 个程序化可验证环境；50 个环境家族完全 held out，每家族 50 题。
- adaptive difficulty 相比固定低/中/高难度，保持更高 effective prompt ratio，并获得更好的 ID 与 held-out-family 表现。
- 在严格嵌套的 1、4、16、256 个训练环境集合中，环境家族越多，50 个未见环境上的表现一致提高。核心结论是环境家族多样性，而不是同一生成器内无限增加样本。
- 从已在约 136K 题上训练饱和的 ProRL-1.5B-v2 出发，RLVE 用约 1,100 H100-hours 使六项 reasoning benchmark 平均提高 3.37；继续原数据训练用约 3,600 H100-hours 只提高 0.49。

## 资源与成熟度

- 每个 run：单节点 8×H100 80GB，2–8 天，约 350–1,500 H100-hours。
- 官方公开 400 个 environment/controller、训练脚本、curriculum checkpoint 状态、held-out eval 和最终模型权重。
- 代码是带修改的完整 slime fork；适合移植 controller 契约，不适合直接替换 RepoHarness 当前训练栈。

## 关键局限

- 环境主要是单轮程序化推理，不是长程 SWE、workspace 或工具调用环境。
- 难度 `d` 的单调性需要人工设计；真实 SWE issue 很难找到类似数组长度的自然难度轴。
- 400 个环境依赖大量人工工程。作者尝试自动环境工程，但无法稳定保证 prompt 无歧义、generator 有效多样和 verifier 对合法输出稳健。
- curriculum 只升不降，没有处理 policy 回退、遗忘或 reward drift。
- 固定阈值缺少置信区间和序贯检验；环境均匀采样也没有考虑成本、稀有能力和 verifier 风险。
- 主要昂贵训练曲线没有多 seed 误差带。

## 对 RepoHarness 的意义

应迁移的是 version-aware curriculum 状态：

```text
environment_family_id
difficulty_revision
policy_version / rollout_version
l / h
pass_count / attempt_count
effective_prompt_ratio
nonzero_advantage_group_ratio
generation_seed
controller checkpoint lineage
```

在 fully-async 下，旧 policy 的 rollout 不能无条件推动当前 policy 的难度；controller 更新、retry、resume 和 checkpoint 必须与 sample identity 和 model version 绑定。
