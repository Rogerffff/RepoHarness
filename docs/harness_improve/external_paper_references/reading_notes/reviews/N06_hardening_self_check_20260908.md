# N06 Hardening Agent Benchmarks：作者自查与交付记录

日期：2026-09-08。正文：[N06_hardening_agent_benchmarks.md](../N06_hardening_agent_benchmarks.md)。

**状态：全文与附录文字精读、主图／主表目视、关键代码与开放产物核查完成；Algorithm 1 与附录 Table 4–8 原页目视尚有缺口。没有独立审查或实验复现。** 本线程没有创建 reviewer/sub-agent 的工具，没有可验证的线程 UUID、模型 effort 运行记录，因此不编造配置，不继承其他任务的“独立审查通过”。

## 1. 版本与任务边界

主来源为 *Hardening Agent Benchmarks with Adversarial Hacker-Fixer Loops*，arXiv `2606.08960v1`，2026-06-08。检查版本历史仍只列 v1；25页，含Appendices A–H。PDF物理页1起算与印刷页一致，网页文本／PDF提取索引不是文档引用页码。

代码固定到 `few-sh/harden-v0@342b8474e0c0cf96e4a8313fd2e26c7a11d51193`（2026-07-03）；Terminal Wrench固定到 `d8a29613235a0ef56a8b70b3142626a533da28c2`（2026-04-18）；KB产物固定到 `fjzzq2002/harden-kb-traces@2721064396f07e536fac5f493b74e7ab161518eb`（2026-06-09）。三个资产彼此独立，不用某一个revision充当整篇实验锁定配置。

项目读取基线为 `Rogerffff/RepoHarness@b895451cb7ad50619bf94569976fbb2c7a1ddb5f`。已读取 O01 Codex quality review 和现有模板；遵守只写本篇及本自查、源码后于论文必须单列、数字携带分母、无独立reviewer不标通过的反馈。

本任务是N06独立精读，不是Terminal Wrench伴生论文、BenchJack或reward-hacking RL文献的批量精读。旧调查只用于发现问题，不是核心事实来源。

## 2. 覆盖检查

| 材料 | 实际完成 | 缺口 |
| --- | --- | --- |
| 摘要、§1–5 | 全读；方法、审计、两个case study和结论 | 无正文未读段 |
| Fig.1 / Fig.2 / Fig.3 | PDF p2/p3/p4截图目视；方法图、柱图、漏洞示例 | 不把Fig.2当训练曲线 |
| Table1 / Table2 / Table3 | PDF p8/p10截图目视，并与HTML表核对 | 原文没有给的分母／CI仍保留未知 |
| A、B、C | 全读；局限、双重用途、相关工作 | 未全文扩读所有引用 |
| D.1–D.9、Algorithm1、Table4 | PDF文字与HTML全读；循环、权限、预算、资源 | p15/p17截图cache miss，未目视伪代码和Table4原页 |
| E.1–E.3 | 全读；MIG、15hint、固定语料重评分、autopatch及示意代码 | 未运行提示或补丁 |
| F.1–F.3、Table5–8 | PDF文字和HTML逐行读并转录数值、p／显著性边界 | p21/p22截图cache miss，五张附录表原页目视未全部完成（含Table4） |
| G五案例 | 全读，含末尾hard-link例子 | 未独立判定每份完整任务的合法性 |
| H八类提示词 | 从PDF提取文本完整读至p25末尾；HTML空框不用来代替内容 | p23–25没有成功取得图页；全文内容已取得 |
| 参考文献 | 阅读用途为来源身份与范围检查 | 不声称被引论文也精读 |
| C源码 | 配置、部分loop、workspace真实导出与消费、README/CLAUDE结构说明 | 不是整库静态审计，不是完整并发／pool事务验证 |
| W、K公开资产 | 固定README；K manifest与两模型iter13逐bucket summary | 未下载权重／全数据／所有代码或复现结果 |

PDF部分原页截图成功、部分请求多次返回cache miss。容器联网下载PDF/HTML/TeX也失败；因此没有伪造本地source文件或来源快照。正文对“未披露、未取得、未检查”分别登记，后续补图页无需重读全部正文。

## 3. 最重要的自查点与修正

**训练身份。** 将“RL训练信号可能受污染”与“本文实际训练了模型”严格分开。三角色和弱到强是API执行／信息条件，不是优化三个策略；没有补写PPO、learning rate或训练GPU-hours。

**指标对象。** 表2针对KB task001，并非100题平均；12×是最终攻击门槛，10×是循环门槛，0.5×是benign判据。`any of N`不是全部N次成功。良性条件通过率也不是每条都是独立人审的真合法解接受率。

**核心负结果。** raw loop最终将攻击与benign都压至0%；headline高benign含autopatch。reference确实在循环中，不能称“完全去掉solver”的受控消融。TB完整三角色仍有约11pp benign下降；Blind+pool在judge-filtered hinted arm反增7.8pp，p=0.002。

**因果和held-out。** Fixed-corpus rescoring是同一批提交跨snapshot执行；第三方hint外推、换强模型、pool代码迁移是不同证据。Autopatch看到了失败良性样本，未据此宣称完整独立的final-benign验证。共享防御的正收益与传播回归同时记录。

**数据口径。** P写323环境，W写331；P/W的SETA与TB2子计数也不同。W明确1,968为有重叠来源合计、另述1,860；不擅改P的16% headline。K summary的0/234与0/232包含benign/control，不能增大攻击分母。

**源码不能凭注释。** 追到`_harden_task_phases`的solver/replay判定与`update_hardened`消费位置。`extract_fixer_artifacts`检查有commit变化后复制工作目录；因此“有commit”不等于所有字节均是commit快照。仅记录条件性静态边界，未声称触发了漏洞，更未说它影响原论文。

**成本。** 8H200用于CUDA任务执行，不是固定API模型的训练；5,000美元是作者估计的API费用，非全部CPU／人力经济成本。C当前trial totals还不计直接litellm总结调用，不能拿其字段当全费用。

**原文差异。** 分列E.3与Table2的iteration／调用措辞、§4.3正文56.2与Fig2/Table7的51.6、D.5四配置与TB公开三行结果。保留有明确标签的表，不“修正原论文”或推定缺失实验一定没做。

## 4. 转录与本地检查

逐表核对主要数值：Table2全部13行两模型三指标；Table3与Table6两层结果、p与原文delta；Table5八hint与多重比较说明；Tables7–8全部百分比。后两表没有机械复制所有星号和四舍五入delta，正文明确提供原表位置并保留承重负结果精确p。

本地检查了引用式链接定义、导航anchor、UTF-8替换字符、表列数、文件终止换行。复算了3,632+1,216+1,441=6,289，hint133+unhint49+benign/control52=234，以及133+49+50=232；重叠来源89+200+70+1,376+233=1,968。印刷后的差值与原文delta有0.1pp差时保留原文，并解释精度问题，没有据此宣称计算错误。

没有执行模型、sandbox、kernel、攻击、autopatch或全流程重放，也没有用代码默认值回填历史配方。文本/算术检查不是实验复现。

## 5. 给后续独立复核的最短路线

优先补PDF p15/p17/p21/p22原页：确认Algorithm1及Tables4–8的布局、限定和已转录数值。其次复核Table2 raw/autopatch分组与E.3的额外干预，再读Table3/F.2/F.3的benign回退和pooled原基线。最后只需抽查C2/C3/C4的接受顺序与W/K的数量差异，不必为这篇再开展整库安全审计。

本轮两份成品是当前专属维护入口。写入前读取最新分支，提交只包含本篇和本记录；README/catalog/batch计划由汇总线程统一处理。远程实际提交与回读结果以交付回复为准，文内不预填尚未存在的commit。
