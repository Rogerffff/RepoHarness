# 《Endless Terminals: Scaling RL Environments for Terminal Agents》阅读摘要

## 论文信息

- arXiv:2601.16443,2026-01 首次提交,v3 2026-02-14
- 作者:Kanishk Gandhi、Noah D. Goodman(Stanford),Shivam Garg、Dimitris Papailiopoulos(Microsoft Research / UW-Madison)
- 官方页面:<https://arxiv.org/abs/2601.16443>;代码:<https://github.com/kanishkg/endless-terminals>

## 核心问题

论文的出发点是"环境是自我改进 agent 的瓶颈":现有 terminal benchmark 为评测而建、依赖人工标注,规模上无法作为 RL 训练供给。RL 需要的是可扩展的环境生产管线而不是固定数据集,目标是完全自动、无人工标注地程序化生成容器化、可验证的 terminal 任务。

## 方法:四段程序化生成管线

1. 任务描述生成:按任务类别、复杂度、场景采样,生成多样化任务说明。
2. 环境构建:生成 Apptainer 容器定义或 Dockerfile 搭建初始环境,并用自动生成的 precondition 测试验证环境成立。
3. 完成测试生成:生成 completion test 验证预期终态。
4. 可解性过滤(solvability filtering):用 o3 对每个任务采样 16 个解,保留至少一解通过的任务;此步丢弃约一半候选。

最终得到 3,255 个任务(文件操作、日志管理、数据处理、脚本、数据库操作等),其中约 2,500 个另转为 Harbor 格式。

## RL 训练设置与结果

- 算法:vanilla PPO(PPO 标准 actor-critic 形式,论文强调不加花样),二值 episode-level reward,无 KL 惩罚,clip 上下界 ε_low=0.2 / ε_high=0.28,训练评测均用温度 0.6。
- 规模参数:每 batch 16 条 rollout,每 episode 最多 16 轮,每轮最多 2,048 token,完整对话 context 16k。
- 模型与算力:Llama-3.2-3B-Instruct、Qwen2.5-7B-Instruct(各用 4×A100 约 2 天),Qwen3-8B-openthinker-sft(8×B200 约 8 小时)。
- held-out dev 成功率:Llama-3.2-3B 4.0%→18.2%;Qwen2.5-7B 10.7%→53.3%;Qwen3-8B-openthinker-sft 42.6%→59.0%。
- TerminalBench 2.0(外部人工基准):三模型分别 0.0%→2.2%、2.2%→3.4%、1.1%→6.7%;同期参照 Claude Sonnet 4.5 + Terminus-2 为 42.8%。
- 失败分析:39% 的失败是循环行为、26% 是轮次耗尽;成功 rollout 的命令多样性 0.49 vs 循环失败的 0.18(成功者出错后会换路子,失败者重复同一命令)。

## 重要限制

- 程序生成任务偏"竞赛题"风格,不像真实用户那种含糊、欠定的需求;缺少歧义目标与隐式上下文类环境。
- 可解性过滤用 o3 pass@16 定天花板:管线造不出超出 frontier 验证模型能力的任务,难度上限被验证器锁死。
- 域内提升不等于通用能力:Qwen2.5-7B 在 dev 上 +42.6 点,但 TerminalBench 2.0 只从 2.2% 到 3.4%。

## 对 RepoHarness 的意义

- terminal 域程序化任务生产的可复现参照:四段管线(描述→环境+precondition→completion test→可解性过滤)是我们域 2 供给侧的现成蓝本,产能与损耗率(候选被过滤约一半,余 3,255)可据此估算。
- vanilla PPO 就能在自产任务上拿到大幅域内提升(10.7%→53.3%),说明供给侧质量比算法花样更先决;但 dev 与外部基准的落差提醒:采用此路线必须配独立外部评测面,防止把分布内提升当真实能力。
- 可解性过滤同时是质量闸门和偏置来源:frontier 验证器锁定难度上限,与我们样本准入设计中"拒绝路径引入系统性偏置"的关切直接对应。
- 后续产能证据:ECHO(arXiv 2605.24517,Microsoft Research,2026-05-23)用修改版 Endless Terminals 管线再生成 6,170 个任务(含 Dockerfile 生成/验证与 Harbor 格式导出),经 GPT-5 pass@16 过滤合并后共 8,870 个任务用于训练。注:任务线索中提过的 arXiv 2602.21193 实为 NVIDIA 的 terminal 数据工程论文(Nemotron-Terminal,SFT 路线),未引用 Endless Terminals 也无 6,170 这一数字;"再产 6170 任务"的出处核实为 ECHO。
