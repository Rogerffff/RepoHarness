# E10 独立正确性与覆盖审查

**结论：固定初稿通过本次独立审查；未发现必须修订的技术错误、整块后训练遗漏、无依据的因果结论，或将已披露内容误记为“未披露”的实质问题。** 此结论是文献笔记审查，不是论文实验复现，也不证明配套代码完整实现了报告中的方法。作者的处理与最终状态见第5节。

## 1. 版本与独立性

- 审查日期：2026-09-07。
- 主阅读任务：`01a07827-1e43-76b3-a7b5-927d16ceab97`；派工来源：`01a077c4-9f0d-7ef0-a40a-688b42f1b294`。
- 唯一独立审查子线程：`01a0782f-d4e7-7691-ade5-f3ce907e50cb`；agent 路径：`/root/e10_independent_review`。实际模型 `gpt-6-astra`，effort `high`，干净上下文 `fork_turns="none"`；主作者另从真实 `session_meta` / `turn_context` 核对了线程关系与配置并回传。本审查者没有创建子代理。
- 来源：Intern-S2-Preview Team, Shanghai AI Laboratory，[arXiv:2608.13505v1](https://arxiv.org/abs/2608.13505v1)，[指定 PDF](../../pdfs/E10_intern_s2_preview_2608.13505.pdf)。全文 35 页，正文至 p.27，参考文献 p.28–35；本版没有独立附录。页码采用该 PDF 的物理页，与印刷页一致，首页未印页码。
- 被审版本：[固定初稿 E10_intern_s2_preview.initial-20260907.md](../sources/E10/E10_intern_s2_preview.initial-20260907.md)。快照中的原有相对链接按 `reading_notes/` 根解释；当前笔记入口为 [E10 正文](../E10_intern_s2_preview.md)。审查者仅写本文件，未修改正文或固定初稿。
- 阅读顺序：先读 `tex/main.tex` 的全部输入与结束结构，独立枚举范围，随后读全部章节源码；再检查原 PDF 分页提取与关键原页，最后打开固定初稿逐节比对。初稿一次显示发生中段截断，已补读 §5–6 的实际缺失段，不以调用成功代替全文阅读。

## 2. 从原文独立建立的覆盖检查

| 原文范围 | 独立核查内容 | 初稿对应与结论 |
| --- | --- | --- |
| Abstract、§1，p.1–2 | 科学多模态、科学生成与长程 agent 目标；397B 主对象与独立扩展 | §2–3；覆盖，没有只按 SWE 解释全文 |
| §2.1，p.2–4，Fig.1、Eq.1–4 | retrieval datastore、memory 的 KL/CE、融合 router、各阶段冻结对象 | §7.1；训练链完整，未混为会话记忆或第三个 OPD expert |
| §2.2.1–2.2.2，p.4–5，Fig.2 | encoder 的压缩和跨通道处理；数值 forecasting、horizon predictor | §7.2；架构概要足够，未擅自补专项 RL 配方 |
| §3.1–3.3，p.5–8，Fig.3–5、Eq.5–9 | VP、交错图文过滤、图像检索；冻结对象、数据单位 | §2；三条路径清楚，OCR 要求未互相混淆 |
| §4.1–4.2，p.8–9，Fig.6 | SFT 数据域、safety、CoT rejection sampling、人工与模型验证 | §3；全部主要领域及模型依赖关系覆盖 |
| §4.3.1，p.9–11，Fig.7、Eq.10–13 | 共置 pause/resume、completed-only、staleness、IS、R3、精度、BKL | §4.1/4.5；版本、概率对象与 mask 作用分开 |
| §4.3.2–4.3.3，p.10–13，Fig.8、Eq.14–24 | 长度 shaping、触发条件、35B 消融；在线 draft 的 KL/TV 与速度 | §4.3/4.6/8.3；机制、分母与实证范围覆盖 |
| §4.3.4–4.3.5，p.13–15，Eq.25–29 | GEPO、不对称 shaping、LOO、动态补采、完整 loss 与配置 | §4.2–4.4；没有把 RLOO 改写成标准化 GRPO |
| §4.4 总述及 §4.4.1，p.15–17，Fig.9 | harness × task、三 serving 协议、TITO、双视图、PrefixTree | §5.1–5.2；未从树结构推断未披露的 rewrite/分支消费规则 |
| §4.4.2，p.17–18，Table 1、Fig.10 | 七来源、任务合约、技能图、逐阶段验证、离线 skip 与反馈闭环 | §5.3–5.4；未把公开库存当最终消费量 |
| §4.4.3，p.18–20，Fig.11、Eq.30 | session outcome、过程 advantage、非可训 token、verifier 防漏、失败分类、各 harness 曲线 | §5.5–5.6/8.3；在线过程权重与离线模仿 mask 区别明确 |
| §4.5，p.20–21，Eq.31–36 | 两专家与 warmup、reverse KL、sampled-token、prox/beh/current、域与轨迹分母 | §6；理想目标与实际 surrogate 的边界保留 |
| §5.1–5.3，p.22–27，Table 2–5、Fig.12 | 所有科学、通用、多模态、agentic、Memory 和时序评测；预算、负结果、排名 | §7–8；没有遗漏非 SWE 结果，也未把总表当受控组件消融 |
| §6、作者贡献、References，p.27–35 | preview 限制；尾部检查到最后条目 [112] | §9–11；未发现额外附录或尾部技术表 |

原页目视核对覆盖全部 12 幅图、5 张表及关键公式：p.3–7、9–14、16–21、24–27 中实际含图表/公式的 21 页。其余正文通过完整源码阅读与分页提取交叉核对。参考文献只用于核对全文尾部与引用边界，未声称递归精读全部被引论文。

## 3. 关键正确性核验

1. **模型关系正确。** Fig.6 与 p.20 明示同一 SFT 初始化分别产生 reasoning / agentic experts；学生是原 SFT 模型经两专家轨迹 warmup 后进入 OPD。初稿还正确区分 397B 主评测、Fig.8 的 35B 与单独 Intern-MemDec-4B。
2. **三个概率对象与分母正确。** Eq.10/34 的比值为 current / token-specific behavior；Eq.33 为 teacher logprob 减 frozen proximal student logprob。Eq.29 先按 response 原长度平均再按组平均，Eq.36 先按 policy-token 集合长度平均再按域内轨迹平均；BKL 剔除位置没有从这些分母扣除。初稿没有用 PPO surrogate 替代 detached clipped IS。
3. **shaping 与数值 mask 正确。** Eq.25 的组熵对 token 求和，未按 response 长度归一化；Eq.28 为 GEPO 在先、长度正则在后；Eq.14/15 的触发对象是正 advantage 集合。BKL 比较 matched parameters 和 replayed routing 下两个引擎的 sampled-token Bernoulli 概率，不是全词表 KL 或跨版本策略 KL。初稿保留了 p.13 解释与 p.14 GEPO 系数串式的疑点，未自行修成配置。
4. **失败、mask 与过程反馈正确分层。** `skip` 是保留上下文但排除 imitation loss；Eq.30 的过程权重只缩放正 advantage，不更改 session reward 或 token labels。非策略上下文与数值离群 token 分属不同排除机制；初稿没有从“故障单列”推断固定 reward、重试或丢组规则。
5. **训练数量与速度范围准确。** 8,192 completed responses / batch、8 mini-batch update steps、65,536 reasoning generation tokens、OPD maximum sequence 256K、draft K=4/η=3 均与原文一致。Table 1 七行逐格一致，包括 R2E-Gym 的 7,480 tasks / 8,101 environments；未据此计算消费量或镜像复用率。2× rollout、1.7× 整体 RL 的两个测量范围没有相乘或外推硬件预算。
6. **Memory 与时序负结果保留。** Fig.12a 逐行复核并独立计算得到 14 项提高、7 项下降，均值四舍五入为 56.92/60.32；初稿的 +3.40 分是报告均值之差。Table 4 七项改善、两项下降及两个新增雷达任务正确。Table 5 的 NEG03 59.2(100) 并不优于 Moirai 59.1(100)，DeepSeek 4.3 的成功率仅 3.1%；初稿正确保留这些反例以及 MAPE 分母未知项。
7. **评测预算与因果边界正确。** Table 2–3 的所有 S2 分数、ResearchHarness v0.0.49、OpenClaw 2026.5.7、Terminus 2、Mini-SWE-Agent 及 Pro 镜像修改均已核。初稿没有把 1,865 题总库规模当 Pro 实测 split，也没有把 SCI agentic “second only to GLM”当逐行排名。Fig.8 为 35B 训练内曲线，Fig.11 为 160 步经局部平滑的代表图；没有将其认定为全部训练预算或单调提升。
8. **资产、项目映射与旧稿纠错有依据。** 另读保存的官方 HF 模型卡/metadata 与 XTuner README/revision：35B 卡、对应 revision、Apache-2.0 和 agentic Coming Soon 字样与初稿相符；没有据 README 断言实现绝对不存在。阅读指定当前简报与项目建议，并窄核 `capture_wire.py`、`canonicalize.py`、`faithful_dis_loss.py` 及集成 `fully_async_rollout.py` 的被引路径；当前 DIS 区间外置零与论文 clip 到边界确实不同。旧稿的细域多教师“否决”、白盒“自研”、标准 GRPO 和直接项目资格映射均已被正文收紧。未做全仓审计、在线训练或 GPU 验证。

## 4. 发现、残余不确定性与交付边界

**本次必须修订发现：0 项。** 没有为凑审查条数而把已正确保留的论文疑点重复列成初稿错误。以下仍应在最终正文保留，不能由“审查通过”消除：

- GEPO 两系数的排印关系与文字“较温和”的说明未统一；论文没有清晰数值配置。
- agentic 的具体 group baseline、完整 scalar loss 分母，以及故障/截断在组统计、梯度、补采中的处置未完整披露。
- compaction/rewrite 后被移除响应的覆盖、共享 prefix 计权、跨版本 matched-parameter BKL、teacher/prox 刷新均未由原文给出完整实现。
- 数据验证与消费漏斗、各阶段算力/教师成本、完整评测预算、时序专项训练配方与内部科学评测分母仍不够复现。
- 官方保存材料只支持指定版本的资产边界检查，不能由 35B 模型卡证明 397B、两个专家、warmup student 或 memory 权重均已公开；未独立下载权重或审计 XTuner 全部源码。

文件引用按主资料树与本 worktree 新增来源分别核对：初稿的既有目标均在主资料树存在；隔离 worktree 缺少这些未纳入基线的共享材料不是笔记链接拼写错误。来源快照内部链接继续按其留档说明解释，不改写固定初稿。

## 5. 作者处理与最终检查记录

主作者于 2026-09-07 收到真实审查结果并全文阅读本报告。审查发现为0项，因此没有需要逐项消除的技术问题；本文列出的原文披露边界全部保留。正文仅修改第12节：登记审查子线程与实际配置、增加本报告链接、把待审状态改为已完成。没有新增实质技术内容，也未声称进行过第二轮复核。固定初稿未修改，技术正文第1–11节保持与被审版本一致。

最终检查与发布已完成（2026-09-07）：

- 比较固定初稿与终稿，第1–11节技术正文一致；仅审查记录与最终状态更新。
- 正文、审查和E10来源说明的22个本地文件引用/导航锚点均通过检查；代码围栏闭合，无行尾空白，无本机绝对路径。原始第三方快照与初稿留档内部链接遵循来源说明，不作为当前导航入口。
- 仅发布 `E10_intern_s2_preview.md`、`reviews/10_E10_review.md` 与 `sources/E10/`；已复制回主资料 checkout 的 `docs/harness_improve/external_paper_references/reading_notes/` 相同相对位置。共58个专属文件逐字节比对一致，发布后的本地链接再次按实际目标树核验通过。
- 发布前脚本曾因E10目标子目录尚未创建而误报一个含 `..` 的链接；规范化路径后确认原链接正确，发布后直接路径检查也通过。未因此改写技术内容或已有共享文件。
- 未修改共享索引、其他任务成品、训练代码或配置；未commit/push、运行训练、租GPU或下载权重/整套数据。

本任务精读、真实独立审查、作者处置与专属成果发布完成。
