# 16 / N07 SDPO：作者自查与交付记录

日期：2026-09-07。对应正文：[N07_sdpo.md](../N07_sdpo.md)。

**状态：完整正文及 A–F 附录精读完成，作者自查完成，待独立复查。** 这是用户分叉后单独指派的 SDPO 线程，没有创建独立 reviewer，也没有复现论文训练。当前工具不提供可审计的独立子 agent 或会话 thread UUID，不填写虚构身份或推理配置。

## 1. 输入、版本与文件所有权

主来源为 *Reinforcement Learning via Self-Distillation*，arXiv `2601.20802v2`（2026-02-16），[PDF](https://arxiv.org/pdf/2601.20802v2) 与 [HTML](https://arxiv.org/html/2601.20802v2)。已核 arXiv 版本历史：v1 为 2026-01-28，本轮访问最新为 v2；论文许可 CC BY 4.0。没有把 N08 OPSD 或 E7 MOPD 的内容补入本篇。

官方代码固定 `lasgroup/SDPO@7c457fc1b1f636ae794eb0362ba37d4743b06fbc`（2026-07-01）。项目读取基线 `Rogerffff/RepoHarness@miles-migration:f0eaf0df1f27bb08c6254edb0346e11cd6479a9c`。该基线只限定项目映射和已读协调材料，写入时应基于最新分支头保留并行提交。

已阅读 O01 的 [Codex 质量反馈](15_O01_codex_quality_review_20260907.md)、NOTE_TEMPLATE、BATCH3_PLAN 的任务16和当前简报。遵守并行所有权：**只写 N07 正文与本记录，不更新 README、SOURCE_CATALOG、BATCH3_PLAN、共享质量记录、历史导出包或训练代码。** 本文件名沿用预定 `16_N07_review.md`，但标题与状态明确为作者自查，不以文件名暗示独立审查。

## 2. 全文覆盖与访问缺口

正文 §1–7、贡献／致谢及参考文献范围已检查；A.1–A.4、B.1–B.2、C/C.1、D.1–D.3、E.1–E.3、F.1–F.4 均已读。参考文献用于定位原作者讨论的来源，不意味着另外全文阅读其引用的所有论文。

| 原文材料 | 核查情况 |
| --- | --- |
| Fig.1–4、Table1–2、Algorithm1、Eq1–2 | 问题设置、教师是否重新生成、原始continuation、stop-gradient均核；PDF关键图页已看 |
| Table3、Fig6–7 | 五任务×两模型的1h/5h选择口径、例子与平均结果分开；原表与PDF已看 |
| Fig8–11、Table4–6 | step80/90/60、teacher类型、SFT基线、SD与SEM逐项核；不统一改成“误差条” |
| Eq4、Fig12–13 | TTT真实权重更新、generation单位、事后筛选、基线预算、90%CI已核 |
| Fig14、A/B/C公式 | 局部KL梯度、额外prefix项、teacher几何混合、top-K tail、两种ratio、实际分母、隐式reward解释已核 |
| Table7–8，物理p36 | HTML表格完整读取并与PDF提取文字比对；该页截图多次失败，**未声称目视raster核查通过** |
| Fig15–18、Table9 | 难度标签、相对增益、不同平均区间、弱模型、稳定性指标、高熵token筛选基线已核 |
| Table10–11、Fig19–20 | 完整19题、9 very hard、2750截断均值、初始teacher、MT模板、逐题不利结果已核 |
| Table12–13、Listing1–3 | 三配方、n/mini/teacher-rate/divergence、硬件、搜索网格、prompt格式已核 |
| Fig21–22、F.2全文、Listing4–6 | 不同色标、完整失败代码、expected output反馈与局部候选例子已核；没有把展示性例子当独立训练结论 |

全文共50个物理页。p27–28目录有未同步标题；HTML多行公式导致A.2后的编号偏移。正文统一使用PDF物理页与印刷编号，并记录网页对应差异。部分PDF截图失败后已用可访问入口补核；**p36是保留的图像读取缺口，不是漏读Table7–8文字**。

没有成功下载TeX或PDF到容器；这是本轮网络／工具访问限制，不记成作者未公开。未上传原始PDF、图片、TeX或第三方代码缓存。原文网页可读部分已充分覆盖，不用旧模型调查来补原文缺项。

## 3. 自查发现及正文处理

| 项目 | 最容易发生的误读 | 已采取的处理 |
| --- | --- | --- |
| 学习对象 | 在教师新生成修复解上做SFT | §2/4/10追原始response，教师只重新评分；额外生成仅属于诊断／基线 |
| 梯度理论 | Eq2无偏等于真实终局reward policy gradient | §3区分局部KL、frozen-prefix与额外sequence梯度；保留教师偏差 |
| 两种sequence-level | 把A.1 estimator和§4.2序列标量消融合并 | 分别命名和定位 |
| JSD与reverse KL | 所有divergence都可原样使用log(q/p) | 明确Eq2/B.1适用reverse-KL，JSD另走分布梯度 |
| 正则教师 | EMA、概率平均、logit混合视为一回事 | §4给公式和参照条件；B.2使用反馈条件化初始teacher |
| Top-K | 教师和学生独立top-K按排名相减 | 同一student支持集；tail与内部重归一化分开 |
| 两种IS | current/old与train/rollout混同，忽视PPO符号相关min | §3.4逐项写概率身份；§10指出现有代码并非Eq13原式 |
| 无信号样本 | reward0或组全零就必然无SDPO梯度 | 区分可信反馈存在与否、row mask、response mask和其他优化器作用 |
| LCB split | 将48.8称未见题目泛化或直接胜过Claude | 同131题训练，tests级划分；当前验证文件保留全suite；外榜协议另列 |
| 3×/4× | 一律解释GPU-hour或平均训练加速 | §6/7/8分开目标交叉点、截断平均generations、单步开销与墙钟 |
| 稳定性 | stop-grad即可保证自教师不崩溃 | Table4无正则发散；冻结/EMA/trust结果全部保留 |
| 遗忘 | Table5标题等于所有能力零回退 | 保留holdout均值43.5→42.4及单项退化 |
| Table9 baseline | 将“only high-entropy tokens”误写成增加entropy bonus | 最后回原文检查时修正为仅对高熵token训练；正文不以该表解释熵正则系数效果 |
| Science汇总 | 强行用Table3凑70.2/66.6 | 独立均值为70.03/66.77；未知聚合口径标记，不擅自修正作者结果 |
| Qwen2.5名字 | 正文8B直接当成实际中间模型 | Fig17实际轴为3B，标记源文差异 |
| Table2 self-demo | 当前默认等同论文所有成功轨迹规则 | 源文允许自身成功示范，rich脚本排除；分别记录 |
| 现代代码单位 | `mini=1`等于一条全局rollout；配置GRPO就消费其advantages | 追FSDP的n/DP变换和SDPO分支；仅作条件性静态推算 |
| 扩展范围 | 已验证真实SWE、多harness、MoE和fully-async | 按§7保留为未来工作，不借verl继承模块扩大训练证据 |

这些项目包含方法边界、实际负结果、源文不一致和作者草稿的修正，并不都是“发现原论文错误”。没有把当前代码中的条件性风险写成已影响历史实验的故障。

## 4. 独立算术和小型CPU检查

本轮在容器执行了纯CPU PyTorch／算术脚本；没有导入或运行论文训练系统。结果：

- Table3十个5h单元格均值：GRPO 66.77、SDPO 70.03；Table7相应均值68.40、71.10。用于识别聚合口径，不替代作者headline。
- LCB主结果差值：48.8−41.2=7.6pp。Table10截断均值比：1145/894≈1.28076，2180/1739≈1.25359。
- 固定前缀、detach教师的KL自动梯度与解析式最大误差约8.33e−17；检查的是一个双精度toy分布，不是大模型梯度等价。
- raw-logit插值softmax与归一化几何混合最大误差约1.11e−16。
- top-K+tail两分布各自和为1；toy full-KL≈0.87860，合并KL≈0.86807，说明合并不是全词表精确KL。
- 文本检查：引用式链接定义齐全、显式导航anchor存在、数学块分隔符成对、UTF-8无替换字符、无行尾空白。逐表回查均值／终点及SD/SEM/CI口径。

这些检查不证明公开代码已经实现全局token分母、DP不变性、30B MoE适配或数值稳定。相关未验证项写在正文§10–11。

## 5. 供独立复查者优先抽查

建议首先检查paper §4脚注5与C6的测试划分，以及§5的筛题规则和Table10，确认没有将适应结果写成未见任务泛化。其次核对Eq1–2、A.1/A.4、B.2与当前loss实现的差别，特别是JSD、支持集、detached ratio和mask分母。最后回查Table4/5/6/9及D/F，确保负结果和统计口径没有在摘要中丢失。

p36如能通过本地PDF打开，应补一次图页目视核验。若需验证现代代码的micro-batch归一化、全零mask优化器行为或reprompt截断，可另建最小复现；它们不是本次阅读已完成的实验。

## 6. 交付给汇总线程的信息

本篇正式入口 `N07_sdpo.md`；主要查阅区：§3目标与IS、§4教师／反馈、§5科学与工具、§6代码反馈消融、§7TTT、§8配方与成本、§10实际代码、§12条件化项目映射。状态应登记为“全文精读＋作者自查完成，待独立复查”。**共享索引请由汇总线程统一更新，本线程不触碰。**

远程保存后以实际提交和回读结果为准；本记录不提前编造commit，也不需要修改本文件来追踪每次共享分支移动。本文与正文是唯一计划交付文件。
