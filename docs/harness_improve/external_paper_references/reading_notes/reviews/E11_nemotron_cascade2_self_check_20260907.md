# E11 Nemotron-Cascade 2：作者自查与交付记录

日期：2026-09-07。正文：[E11_nemotron_cascade2.md](../E11_nemotron_cascade2.md)。

**状态：后训练正文及相关附录文本阅读、主要图表核对和作者自查完成；Table11/12图页未取得，尚未独立复查，也未复现训练。** 本会话没有创建独立reviewer的工具，不填写不存在的子线程ID、模型effort、审查通过或实验记录。

## 1. 来源、基线和文件所有权

主来源为 *Nemotron-Cascade 2: Post-Training LLMs with Cascade RL and Multi-Domain On-Policy Distillation*，arXiv `2603.19220v2`，63页，版本提交日2026-03-22；封面2026-03-16另记。使用官方HTML、PDF文本和可取得的截图，不用旧模型摘要补原文缺项。v1与v2历史已确认，但没有进行两个版本全文diff。

项目读取基线为 `Rogerffff/RepoHarness@miles-migration@09b9d68c1803c7bb0c2d1944fcbac2bc5b34f7c6`。先读了O01的Codex反馈，采用重要曲线保留量级、代码附查有范围、未知类别分开和并行文件隔离的要求。

本任务只拥有下列两个文件：

```text
reading_notes/E11_nemotron_cascade2.md
reading_notes/reviews/E11_nemotron_cascade2_self_check_20260907.md
```

不改README、SOURCE_CATALOG、总批次状态、其他论文、旧摘要、训练实现或项目定案。远程写入须从最新branch head建立仅含这两项的提交，遇到并行移动就以新parent重建，禁止force更新。

## 2. 实际阅读与图表覆盖

| 范围 | 完成情况 |
| --- | --- |
| 摘要、§1–2、目录 | 全读；检查主结果及比较来源 |
| §3.1–3.2.10 | 全读十类SFT，不将general chat、safety、science等省略 |
| §4.1–4.8.2 | 全读阶段、GRPO、IF、多域、MOPD、RLHF、long-context、Code与两种SWE训练 |
| §5–6 | 全读数学证明TTS、竞赛代码、局限 |
| Appendix A.1–A.7 | 全读全部评测协议、模式、重复数、judge和预算 |
| Appendix B | 全读Table7–10，对照正文参数，不用表静默覆盖正文 |
| Appendix C | 两个提示框在HTML提取中缺正文，回PDF图页／文本取得IOI和HLE内容 |
| Appendix D | 全读40场CF评估方法、Table11/12 caption与明细；不是重跑在线rating |
| Appendix E | P1–P5模型proof、专家评论与P2 LLM审查文本全读；按工件和评分归属总结，不宣称独立数学证明审查 |
| 致谢、References | 检查文档尾部与相关依赖身份，不对参考论文逐篇扩读 |

实际目视：封面图、Fig.1–4、Table1–10、C.1–C.2提示框。主要对应PDF p.1、5–7、10–14、16–19、24–27。Fig.3记录reverse-KL和grad-norm的目测量级，Fig.4使用图中印出的五个数值，不给目测点虚构高精度。

PDF截图的有版本／无版本入口在本轮有部分cache miss；无版本入口当时仍为同一v2、63页。**Table11/12（p.28–29）图页始终未成功取得**，以HTML和PDF文本交叉读取；部分证明批注和尾页也仅以文本阅读。正文已保留这种证据边界，不把“取得全文文本”写成“逐页视觉审查完成”。原始TeX、本机PDF下载未成功，不虚构本地附件链接。

## 3. 关键数字、目标和反常结果的自查

| 核查对象 | 本稿处理 | 原始定位 |
| --- | --- | --- |
| 模型/阶段来源 | Nano-Base→SFT→IF→多域→MOPD→RLHF→long→Code→SWE；教师RLHF为从SFT独立训练的支线 | Fig.2；§4.1、4.4 |
| SFT数量与单位 | 98K题、410K/400Kproof样本、700K多轮conversation samples等分开；不合成未经核实的总独立任务数 | §3.2 |
| Eq.(1) | 保留原式未显式写policy因子的事实，未补一个自造完整loss，也未据此否定实际训练 | p.11 |
| on-policy／KL | 区分一次更新与训推数值一致；保留RLHF KL=0.03与总述无KL的冲突 | §4.1.2、4.5.3 |
| MOPD Eq.(2–4) | 三种概率身份、两个stop-gradient、sampled-token、带外置零、原token-mask分母完整说明 | p.13 |
| MOPD效率 | 数学实验是math-only；Table3含creative小回退；按步效率不换算成总GPU/teacher成本 | Fig.3、Table3 |
| optimizer/长度/过滤 | 多域与long的Adam/AdamW、long49Ksequence/response、RLHF/long过滤、MOPDlr分别记录 | §4与Table8–9 |
| Code验证服务器 | 2048程序、427.2秒、384CPU为该阶段验证，不是总step或SWE rollout | §4.7.2 |
| SWE预筛与正式训练 | 预筛16/instance、训练16prompts×64；0%题保留10%，不混为删除所有难题 | §4.8.2、Table10 |
| Agentless reward与mask | GPT-OSS120B评分；全部reward≤0.5才屏蔽整prompt，不是逐低分token | §4.8.1 |
| Table4与Table1 | 50.8 intermediate与50.2 final不能单独证明execution-RL收益或退化 | pp.5、16 |
| 主模型弱项 | BFCL、WMT相对Nano回退；Q2Hard=0，不能泛化“所有hard已突破” | Table1、6 |
| IMO评分身份 | P2为GPT-5.4-Thinking(Extensive)带参考规则评分，其他题人工专家为合作者；不是全套独立人工复现 | Table2脚注、Appendix E |
| ProofBench复评分 | 对DeepSeek公开proof重新评分≠复现训练；64grader零分否决，57.7与人工61.9差4.2 | §5.2、A.1.2 |
| TTS预算 | Basic及11个Advanced减配；IOI逐subtask与2000/5000汇总范围未完全解释 | A.1–A.2 |
| CF表顺序 | 正文with/without对应反了，按Table11/12 caption定位；保留迁移限制 | Appendix D |
| HLE/τ²协议 | boxed答案约+6–7pp、history保留约3–5pp、telecom重复指导；不算纯权重收益 | A.3、A.6、C.2 |

这不是一份“论文错误数量榜”。其中包含未披露、简写、粗略数量、正式配置冲突及本轮未核事实，已按不同性质解释。

## 4. 开放资产附查的边界

模型README、目录和可取得的commit页；RL数据卡、四类目录和SWE添加commit；SFT数据卡、八类目录。观察到的revision已记录在正文。未下载模型权重、LFS训练数据、全量JSONL或逐条验证license/provenance，也没有以viewer统计代替数据卡的明确计数。

重点保留：论文SWE/terminal量与发布卡不同；MOPD发布类别未单列正文提到的RLHF；当前模型卡的OpenCode限制、tool-response序列化与2026-07-09 parser变化仅是发布接口说明，不倒填三月训练。没有展开与本篇主张无关的NeMo整库审计。

## 5. 本地稿件检查与结果

对正文及本记录做Markdown引用／锚点、数学分隔符、文件路径和文本检查；复算IOI分项、SWE与RL数据分项、Table4百分点、MOPD比较和importance-weight示例。没有用这些轻量检查冒充GPU数值对拍。

草稿阶段发现并修正了一处RL数据commit字符串转录问题，成品只保留正确40位SHA；也删去了从旧草稿记忆带入、实际Table8没有给的统一min-lr/warmup字段。最终数字以原表／正文分开记录为准，不把自查过程中的草稿错误留给读者解决。

远程提交后应回读两文件并查看diff，确认只涉及本任务路径。提交SHA与实际保存结果由交付消息报告，不在成功前预写“已提交”。

## 6. 后续独立复查优先点

优先核对：Eq.(1)的说明是否准确而不过度批判；Eq.(2–4)的梯度/分母与teacher身份；Table8–10与正文冲突；agentless结果和final SWE的归因；P2与ProofBench两个不同judge；公开数据卡数量与版本引用。若能够取回Table11/12原图，可补视觉核验，不需因此重读全部63页。

本文没有将“建议MOPD”或“增加更多训练阶段”作为项目定案。独立复查若发现需要修改，应只更新E11正文和本记录，保留其他并行线程及历史记录。
