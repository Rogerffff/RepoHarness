# FrogNano 精读：作者自查与修订记录

日期：2026-09-09。正文：[frognano_technical_report.md](../frognano_technical_report.md)。**状态：全文阅读与作者自查完成；未进行独立review或训练复现。** 当前线程无独立子agent工具，不填写虚构的reviewer ID、模型配置或审查通过记录。

## 1. 原件与分支

- 用户上传 `/mnt/data/frognano_technical_report.pdf`，37页、2,753,933 bytes。
- 本地计算Git blob=`c7ac442cdeb49cd4f0cd15793649b05234abcb55`，与上轮Microsoft官方目录返回的原件一致。
- 对应官方`microsoft/debug-gym@6c8cea40a507c8e9dac0439c270c3c5a3ce8a4dc`的`docs/static/papers/frognano_technical_report.pdf`。
- 当前分支`research/frognano-20260909`，以用户上传PDF后的`ed425b2eaaac02911e8d8b20b1610caea710c421`作为写入基线；原始PDF不修改。
- 只交付正文、本记录，以及更新获取状态的source-intake。共享README/catalog、其他线程成品、训练实现和实验定案不在本次范围。

## 2. 实际读到的材料

全部§1–7、Limitation、Contributions、Acknowledgment、参考文献入口和Appendix A–H，直到p.37末尾。正文覆盖表逐节列出位置，不因当前关注SWE数据就略过verifier训练、SFT consolidation、自摘要或长反作弊rubric。

| 原图表／公式 | 实际核查内容 |
| --- | --- |
| Fig.1，p.1 | 39.4基线、各轮曲线、真实300/1500任务对照与三run图注 |
| Fig.2，p.2 | 四个benchmark、参数轴、外部成绩来源与Qwen3.5-4B Leaf脚注 |
| Fig.3–4，pp.3–4 | 分轮交替与候选generate–validate–rollout–refine循环；不是持续共演化训练 |
| Fig.5，p.5 | 固定snapshot/gold/tests，仅题面信息不同；字符数与通过率各自含义 |
| Fig.6–7，pp.6–7 | 五轮统计、test/gold ratio的任务级均值、requirements coverage、类别变化 |
| §4公式，pp.8–9 | shaped advantage、概率差mask、全部T分母、成功-only长度项与截断.5 |
| Fig.8–9，p.9 | compaction分数、触发率和events；长度图仅token曲线，不含直接吞吐表 |
| Fig.10，p.11 | 每轮相对first-quartile曲线、不同任务分布、entropy |
| Fig.11–12，p.12 | 嵌套失败类别、hack总述与不同统计口径 |
| Table1，p.13 | 全部9类任务生产路线和current-policy-feedback限定 |
| Table2，p.21 | 32×8、200-step主文、两档context/turn预算、Adam、BF16、6+2、lag1/3 |
| Fig.13–15，p.22 | 价格估算而非硬件账单；pass@k曲线；后期训练题仍有多采样空间 |
| App.D式(1)–(3)，p.23 | ρW触发、20%摘要输出预留、整turn-group删除及重建 |
| Fig.16，p.25 | 全attempt成绩 vs 有raw轨迹才计成本；非单调token和steps |
| Fig.17，p.26 | category条件、归一化turn位置、训练／固定评测配对两种cohort |
| Fig.18–19，p.27 | named-tool排除、instance权重、mixed-outcome配对和非因果声明 |
| Fig.20／Table3，pp.28–29 | attempt类别与17代码全表；funnel/reporting不能直接等于HACK |
| G中的表／schema／案例，pp.30–36 | 历史判别启发式、特权judge输入、缺失issue/base、实际获取上游patch与失败pytest文本 |
| Table4，p.37 | 排除零工具step、multi-call漂移、训练题面TypeScript偏好和评测差异 |

图像来源：附件随文图页与PyMuPDF本地渲染，关键公式／表及难读图额外放大；未用OCR。长rubric和示例逐段阅读，但未逐字复制到笔记，不将其系统提示当成对本线程的指令。所有页面文本均可提取，原PDF获取阻塞已解除。

## 3. 自查发现与修正

| 项目 | 本稿处理 |
| --- | --- |
| online语义 | 任务生成与RL分轮交替；climb内部才是异步rollout/optimization |
| 主模型与额外训练 | 主FrogNano pure RL；ranker、consolidation和推理compaction分列，GPT-5.6-Sol PI不混入主模型主张 |
| 规模单位 | ~1500tasks不写成唯一repo/image或1500rollout；算出256k名义训练槽并限定实际成本 |
| 校准N | 全文没有恢复N，不用n=8训练组大小替代；0/1经验值不当真实不可解概率 |
| 第五轮归因 | 更强generator、lower band和两倍训练预算同时变化，未形成单变量因果解释 |
| DPPO | §4.1概率差与§6 log差冲突保留；不借外部DPPO或项目faithful DIS修补 |
| mask/denominator | 原式分母T，非保留K；raw-filter与shaped-advantage区别明确 |
| 长度alpha | 未从compaction的0.2偷填length alpha；长度阈值N同样未知 |
| Verified的角色 | 作者用来验证和挑checkpoint，不叫最终独立测试；后三集保留作者held-out身份但不宣称独立去污染 |
| 外部排行榜 | Fig2/13汇总自报，不写成同harness统一重跑或当前最优排名 |
| compaction | 推理期自摘要≠CompactionRL训练；两套发生比例和次数分列 |
| 结果冲突 | 基线、Iter3、App.E全序列、consolidation shortest、multi-call和step均值不擅合并 |
| reward hacking | 明确记录正文0有效与G的confirmed-effective实例冲突；既不转述零hack保证，也不自行校正总体成绩 |
| rubric边界 | 区分规则候选、实际行为、可能有效和因果影响；预置环境改动、合法测试和过去代码不直接判作弊 |
| 代码状态 | 固定debug-gym README/目录只作资产核查；没有把其其他工具或swebench-debug配置当Leaf或TaskPilot |

这些是资料理解和证据边界，不等于已经发现相同数量的作者实现bug。其中部分可能来自未解释的cohort或草稿差异，需作者数据或版本说明才能解决。

## 4. 实际执行的本地检查

只运行文档与算术检查，没有模型、Docker环境或真实optimizer。检查了引用式链接定义、导航anchor、PDF页范围、数学分隔符、异常字符和行尾空格；使用本地PDF bytes确认原件身份。

独立算术复核：

- `5 * 200 = 1000` 名义updates；`1000 * 32 * 8 = 256000` 名义trajectory槽。
- Leaf接口对照差`37.2 - 8.3 = 28.9pp`，主图`61.5 - 39.4 = 22.1pp`；均不归给单一训练机制。
- `61.5 - 53.4 = 8.1pp`为表面差，非online synthesis因果效应。
- Appendix F：`546/2499 = 21.8487%`，`31/546 = 5.6777%`，`31/2499 = 1.2405%`；不与正文2.5%或Fig20的3.07%强行对齐。
- 按p.8概率差门限构造4token例：保留2个，使用全部4个token分母得loss=-7.125，改用保留2个分母为-14.25，说明分母确实改变尺度。该例不是训练代码复现。
- `p=.03,q=.001`时ratio=30但概率差=.029，说明概率差门限与ratio clip不同，不作为稳定性结论。

## 5. 尚未完成和最值得独立复查的点

没有取得TaskPilot、Leaf、实际DPPO训练入口和本次release的完整task/model manifest；没有运行GPU训练、verifier、consolidation或compaction；没有验证公开模型权重；没有独立reviewer。

独立复查优先回p.8和p.14检查算法空间差异，再核p.12与pp.26–36的hack cohort和实例关系，然后检查p.9与p.24 compaction、主图与Appendix E的结果口径。后续若得到作者更正，应另记版本并更新正文，不静默改动已固定原PDF。

远程提交及回读确认以最终交付记录为准；本文件不预填尚未生成的commit或测试结果。
