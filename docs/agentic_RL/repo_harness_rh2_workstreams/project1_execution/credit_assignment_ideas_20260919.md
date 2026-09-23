# 后续实验候选：轨迹评分与轨迹内 advantage 分配

记录日期：2026-09-19。用户要求保留此方向，供后续设计实验时参考。**状态是候选研究思路，尚未批准训练配方、judge 服务或实验预算；未改实现。**

## 要检验的两个不同问题

1. **整条轨迹评分是否有益**：保持可信测试结果为主信号，用固定 rubric / verifier 区分同样通过或同样失败的轨迹，再计算组 advantage。
2. **轨迹内定位是否有额外收益**：保留原 reward 与轨迹 advantage，只根据动作证据重分配步骤/token 权重。它与新增过程 reward 不同，应单独消融。

推荐顺序：先用已有真实轨迹做 judge 离线审计，再比较基线、轨迹评分、轨迹内乘权；加入打乱步骤标签及必要的纯长度处理对照，最后按总成本比较 held-out 能力。具体题量、模型、权重和预算以后再定。

## 参考资料与证据强度

| 资料 | 可借鉴内容 | 不能外推的部分 |
| --- | --- | --- |
| [SWE-RM](https://arxiv.org/html/2512.21919v1) | SWE RL 中 verifier 分数 + 执行奖励；判分模型的区分度与校准 | 是专门训练的 verifier，不能保证任意通用 judge 同样有效；不是动作级 ADV 改写 |
| [SWE-TRACE](https://arxiv.org/html/2604.14820v1) | rubric 完整轨迹分数与测试结果混合；同结果轨迹之间提供区分 | 正文 RL 使用轨迹标量，不能把 process 名称当作逐步骤数值 reward |
| [Agentic Rubrics](https://arxiv.org/html/2601.04171v1) | 探索 repo 后生成问题级准则，跨候选复用，检查 patch 证据 | 主要是推理时重排实验，不是 RL 增益证据 |
| [DRACO](https://arxiv.org/html/2609.04094v1) / [固定实现](https://github.com/IBM/draco/blob/cfafd0f81f2c49aa36a4b25a2a7b6ac6e119f47b/training/src/verl_appworld/credit_advantage_patch.py) | GRPO advantage 后按步骤质量和正负分支重分配；明确的长度处理、回退规则 | 相关实验不是 SWE；固定 rubric 下也有加 credit 后下降的结果 |
| [IAPO](https://arxiv.org/html/2608.24588v1) | 用动作间支持/错误传播关系分配学习信号，按 token 长度保留总量 | 相关实验是服务任务；本轮取得的 v1 缺少若干被引用附录 |

完整公式、结果与 14 篇候选的适用边界见 [09-17 研究报告](../../../harness_improve/external_paper_references/live_reports/mimo_v26_rl_20260917/credit_assignment_followup_20260917/README.md)及[来源版本和自查记录](../../../harness_improve/external_paper_references/live_reports/mimo_v26_rl_20260917/credit_assignment_followup_20260917/evidence_notes.md)。作者结果未独立运行复现。

## 设计时必须重新检查的限制

- judge 可省去 value critic 的训练接线，但长输入、反复评分和组等待可能很贵；计入评分、环境、重试、过期浪费和 wall-clock。不能预设 judge 比 critic 算力更省。
- 非负乘权不改变原 advantage 符号，也不能唤醒零 advantage 的组。若组内结果相同，混合 reward 后的组标准化可能抵消“小 judge 系数”，不能据此宣称干预很小。
- advantage 标量总和守恒，不等于梯度守恒。DRACO 的步骤总量分配与按 token 乘权不同，要隔离长度效应。
- SWE 离线审计应包含主动复现失败、正常空搜索、有效探索、预算耗尽等情况；不能用工具退出码机械判断好坏，不能把基础设施异常塞成普通任务失败。
- 若以后接线，动作定位应依据真实捕获的 token/span；沿用现有 loss mask、behavior logprob、faithful DIS gate 和 execution provenance 分母，不通过改分母掩盖权重变化。
- MiMo 公开字段支持 advantage 行重写等记录，尚不能确定其完整公式、先后顺序或轨迹内动作粒度。上述论文提供候选方法，不是 MiMo 算法身份的证明。
