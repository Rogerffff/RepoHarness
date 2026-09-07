# N01 独立审查：KAT-Coder-V2.5 Technical Report

审查日期：2026-09-07。对象：[N01 笔记](../N01_kat_coder_v2_5.md)。审查者为本任务唯一独立 sub-agent，未派生其他 agent，未修改笔记正文。

## 1. 先读原文所得覆盖清单

以下清单在打开初稿之前建立。已独立通读 [v1 TeX 正文](../sources/N01/tex/main.tex) 全部技术章节及结论、贡献与参考文献，查阅 [references.bib](../sources/N01/tex/references.bib)，并检查文末表。没有技术附录；Table 1–3 漂移到参考文献后的 PDF 第 23–24 页，不能当作无关尾页略过。[arXiv v1 页面](https://arxiv.org/abs/2607.05471v1) 确认为 2026-07-06 提交的正式版本，共 24 页。

| 原文范围 | 独立阅读所得必须覆盖内容 | 核查深度 |
| --- | --- | --- |
| 摘要、§1，PDF pp.1–3 | 实际五类专家；正文重点 SWE/Claw；不能由摘要只列三类就删去 terminal/general knowledge | 全文 |
| §2.1、Fig.2，pp.3–4 | PR/commit → golden/test patch → 三段任务描述 → clarity check；AutoBuilder build/verification agent；结构化测试采集 >90%；重复一致；16.5%→57.2%、>100k 环境/12 语言；预应用非题意依赖编辑、移除 git 泄漏 | 全文、图视觉核查 |
| §2.2，pp.5–6 | zero-pass 任务经 hint 达约20%，固定已验 patch 后无 hint 再生成；规则门控+过程评分；偏好/rejection/process RM 信号；等价 harness 改写与异常注入 | 全文 |
| §3.1–3.4、Fig.3，pp.6–9 | Service/Task/Eval 闭环；Skill 与生成服务双来源；OpenAPI/container/fixture；服务生成 >90%；候选 millions、保留 >100k instances；平均15次工具、最长>100 steps；三阶段一致性验证、三种处置、两层轨迹筛选 | 全文、图视觉核查 |
| §4.1，pp.9–10 | 协议/context/control-flow 三轴；mini-swe-agent 白盒；ClaudeCode/Codex/OpenClaw/OpenHands 黑盒；两者都进 RL | 全文 |
| §4.2、Fig.4–5，pp.10–12 | Rollout/Train/KwaiEnv/Gateway/Buffer；token-in/out、weight sync；约200轮样本40%有 drift；/generate；早期 sandbox 轨迹级16%；磁盘95%→60%；timeout与verifier各6–7%→<1%；整体反馈<2%；collapse约降一数量级 | 全文、图视觉核查 |
| §4.3、Eq.(1)–(4)，pp.12–13 | PPO 三点选择理由；token ratio、轨迹内1/\|o\|、GAE、critic MSE；原文 r_t 重名；训练期 hindsight context、actor 普通历史、部署丢弃 critic | 全文、全部公式 PDF 视觉核查 |
| §4.4、Eq.(5)，pp.13–15 | 三层规则 reward；模型 rubric 来源、适用范围；GRM 为单独 RL 训练的 judge；GT 召回与误报计数惩罚、空 GT 分支 | 全文、公式 PDF 视觉核查 |
| Table 1–3，pp.23–24 | 10项规则，含正文列表未列的 Debug Artifact Cleanup；Table 2八项代表标准与适用条件；Table 3四种 bad cases；表2/3仅 Partial Display | 全部表格 PDF 视觉核查 |
| §5–5.1、Eq.(6)–(8)，pp.15–17 | K=5 domain routing；student on-policy prefix 上 teacher logits；KL(student\|\|teacher)；teacher 轨迹 cold-start NLL；top-k overlap/k；单调权重、连续m低阈值截断、保留有效prefix、gradient mask、length-stratified batching | 全文、全部公式 PDF 视觉核查 |
| §6.1–6.2、Table 4，pp.17–19 | 内部 Code/Claw benchmark 构造与质检；默认统一Claude Code协议及PinchBench外部Avg例外；全部6×5分数、Kimi星号模型替换；负结果；未给消融/具体预算 | 全文、Table 4 PDF 视觉核查 |
| §7–8、References，pp.19–22 | 结论仅方法叙事，无额外训练配置；检查V2引用目标与未披露边界 | 全文 |

原始 PDF 已视觉检查 pp.1、3、6、10–13、15–16、19、23–24，覆盖全部八个公式、四张表及五幅图；其余技术页经完整 TeX 与 PDF 文本对照阅读。

## 2. 与初稿逐项对照的发现

### 2.1 结论与一处低优先级修订

**未发现 P0/P1/P2 正确性问题，也未发现后训练章节或文末技术表遗漏。** 笔记对模型关系、数字分母、公式、评测脚注及因果证据边界的处理与原文吻合。保留一处 P3 措辞收紧建议；它不影响核心技术结论。

| 编号/严重度 | 初稿位置 | 原文证据 | 问题与最小修订建议 |
| --- | --- | --- | --- |
| R1 / P3 | §5.4 表2摘要，初稿第183行：“允许未动态复现但凭源码/既有测试/历史/框架推理准确定位的情形” | Table 2 / PDF p24，Static Bug Localization；TeX main.tex 第626–630行只描述这一情形。该表是 Partial Display，没有正负符号、权重或显式豁免规则 | “允许”略强于原文，可能被理解为已披露的复现豁免政策。改为“列出未动态复现、但经源码/既有测试/历史/框架推理准确定位根因的情形；奖惩方向未披露”。初稿第188行已有正确限制，保留它即可；无需删除静态定位条目。 |

P3 表示局部表述精确性建议；不把它升级为尚未发生的实现风险或新准入要求。

### 2.2 实际对照证据

| 核查主题 | 初稿对应 | 独立核对结果与证据 |
| --- | --- | --- |
| 标题、日期、署名、版本 | §1，第5–9行 | 与 PDF p1、§8/p20、arXiv v1 元数据相符。正文署 KwaiKAT Team，网站列 Bo Huang 等53位作者。物理页码、无独立Appendix、文末表位置正确。 |
| 全后训练覆盖 | §1.1覆盖表；§3–6 | 独立清单中的 SWE 数据、Claw 数据、所有 RL/奖励/GRM、五域专家、cold start/MOPD/动态截断全部有实质解释。terminal、web coding、general knowledge 作为未单独展开的专家保留，没有强塞入串行流水线；没有把参考文献里的数学/多模态配方算作本模型训练。 |
| SWE 环境数字与分母 | §4.1，第70–84行 | >90% 是 expected tests **collected**，不是通过率；16.5%→57.2% 是环境构建成功率；>100,000 是 environments、覆盖12语言。原文没有完整原始候选分母、重试次数、训练实际消费量；笔记没有偷换成题数/镜像数。 |
| 恢复数据与过程过滤 | §4.2–4.3 | 约20%对应 previously zero-pass tasks 经过程hint后的通过率，不能代替无hint重建保留率。先固定 verified patch 后重新生成无hint轨迹、再查验证/泄漏/一致性，与§2.2/p5及Fig.2一致。过程维度、偏好用途、鲁棒性扰动均未漏。 |
| KwaiClawEnv 全流程 | §4.4 | Service/Task/Eval、双来源服务、三种派生方式、三阶段一致性检查、三种处置、两层过滤及judge三维均对应§3.2–3.4。区分 Skill服务生成>90%、millions候选→>100k instances、数万trajectories、平均15 tool calls与最长>100 steps；保留口径不明而未强行凑漏斗。 |
| PPO/GAE/critic 公式 | §5.1–5.2 | 已对 PDF pp.12–13 Eq.(1)–(4)逐项核查：行为策略采样、token ratio、min/clip、每条o内1/\|o\|、GAE上界T−t−1、MSE目标均一致；准确指出r_t重名。c_t是may include，actor只见常规历史；没有把前代mini-critic大小补成KAT事实。 |
| GRM、规则reward和文末表 | §5.3–5.4 | Table 1的10项完整，包括正文bullet缺少的清理项；Table 2八条、Table 3四类均有覆盖且标Partial Display。Eq.(5)两分支均正确：非空GT以\|GT\|为分母、误报按数量惩罚；空GT从1起扣。明确这是训练judge的reward，非actor总奖励。F₂公式标为标准释义而非原文披露。除R1措辞外无误。 |
| MOPD模型关系与公式 | §3、§5.5–5.6 | K=5，按样本domain选择一位teacher；student自采样前缀上KL(student\|\|teacher)，不是五teacher平均。Eq.(6)无长度分母；Eq.(7)teacher采样NLL；Eq.(8)top-k交集除k。兼容权重、连续m低阈值、gradient mask、有效prefix及length-stratified batching全部保留。没有把top-k compatibility说成top-k KL实现。 |
| infra与故障率 | §6 | §4.1–4.2及Fig.4支持双类harness均参与RL、Gateway/Buffer/权重同步、后端/generate；200-turn实验中40%是发生drift的samples比例。16%是早期抽审含sandbox故障的轨迹比例；两个6–7%分别为超时rollout和verifier受污染样本。笔记正确分开峰时95%与稳态60%，不把错误率相加、不从约180步曲线造总预算。 |
| 全部表4数字与派生差值 | §7.2 | 已对PDF p19核对30个表格单元（含GLM-5.1的缺值），均与初稿相符；差值4.0、4.2、1.4、5.2、23.9、0.2、3.2正确。KAT Claw第三、Terminal五者最低；SciCode并列第一与第二不同分值说明正确。 |
| harness/评测协议 | §7.1–7.3 | §6默认统一Claude Code，固定工具/context/环境/decoding，但Table 4明确PinchBench是2026-07-02外部Avg，Kimi该格是K2.7-Code。笔记没有将六项全部包装成统一预算重跑，也未把缺乏定义的全表统一改成pass@1。 |
| 消融与因果 | §2、§5.2、§5.6、§7.3、§9 | 原文确无等底座/数据/算力的PPO、critic、GRM、harness或MOPD消融表。笔记准确把工程前后观察、作者解释、读图近似和阅读者理论问题分开；没有把榜单领先归因给单项机制，也不把hindsight仅训练可见推成无偏证明。 |
| “未披露”是否经过查阅 | §5.7、§6.2、§8–9 | 已独立读完§1–7、图1–5、表1–4和参考文献：确未见base/teacher/GRM参数规模、tokenizer、GPU-hour、optimizer/LR、训练batch/steps、PPO常数、奖励权重、MOPD k/m/阈值、实际KL估计/token mask/staleness策略、评测题数/重复/具体预算。笔记没有用前代或框架默认值填空。StreamLake超时是主作者访问记录，本审查未独立重试，因此不另背书网站当前状态。 |
| 旧稿误引与原文内部引用 | §9.2–9.3 | 已读旧稿相关段落及引用定义：KAT与Qwen共挂[7]、该段末[7]实际指2603.00729v1，纠错成立。原文§4.2指称V2却引2510.18779；§1引用的V2则是2603.27703，references.bib亦可核实。笔记没有因此声称精读了两篇前代。 |
| 项目映射 | §10 | 对照主目录2026-09-05简报和2026-09-07建议：miles/SGLang/外部harness基线、rh2职责、新审查覆盖缺口、C包未定和咨询建议身份处理正确；没有把通用Gateway/TITO变成原创或把PPO/MOPD变成已批准首版设计。属于已查状态文档支持的设计候选，没有虚构本轮代码审计或训练实测。 |

### 2.3 保留的审查边界

本次是原文与笔记一致性审查，不是报告实验的独立复现；未执行训练、取得作者私有代码、重算内部benchmark，也未查阅所有被引用论文全文。全文未披露不等于互联网上绝不存在资产，初稿对此已有正确限定。

主目录中的项目状态/旧稿链接目标已核存在；这些文件不在当前工作树快照中。主作者仍须在最终发布副本检查跨目录相对链接，不应为了消除工作树缺文件提示而把真实本机绝对路径写入笔记。

## 3. 主作者处理记录

由主作者在完成修订后逐项追加；本审查不预先宣称修订通过。

### 3.1 2026-09-07 修订与证据

独立审查按用户指定使用GPT-6 Astra / high、`fork_turns="none"`；主作者收到完整审查后处理如下。

| 发现 | 处理 | 原文证据与修订核验 |
| --- | --- | --- |
| R1 / P3 | 已采纳。笔记§5.4将“允许未动态复现……”改为“列出未动态复现、但经源码/既有测试/历史/框架推理准确定位根因的情形；奖惩方向未披露”。保留后文无正负号/权重、不能一律当违规的限制。 | Table 2/PDF p24只描述Static Bug Localization；TeX main.tex相应行无明确豁免政策。主作者重新对照已渲染原页与TeX后修订，检查旧措辞已不存在、新措辞存在且其他八条标准覆盖保留。 |

没有其他待修发现；未发现问题不等于作者实验已独立复现。残余来源/配置缺口按笔记§8–9保留。此处记录主作者对R1的核验，未假称审查者再次审了整篇。

交付排版核验另修正本审查覆盖表两处数学竖线的Markdown转义（PPO长度分母、KL方向），仅保持正确表格列数，不改公式含义或审查结论。
