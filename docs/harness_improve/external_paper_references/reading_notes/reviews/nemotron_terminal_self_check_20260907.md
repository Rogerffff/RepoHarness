# Nemotron-Terminal 数据工程论文：作者自查与交付记录

日期：2026-09-07。正文：[nemotron_terminal_data_engineering_2602.21193.md](../nemotron_terminal_data_engineering_2602.21193.md)。

**状态：主论文全文、附录与配套资产定点阅读完成；作者自查完成，待独立复核。未运行训练、评测或环境实验。** 本线程没有可用的独立子 agent 工具，未虚构 reviewer、线程 ID 或推理配置。

本任务依据用户单篇分配与 [O01 Codex 反馈](15_O01_codex_quality_review_20260907.md)执行：先原文全覆盖，再做项目映射；重要曲线保留近似量级；代码／资产检查以论文所需范围为限；并行只提交本篇和本记录，不维护共享 README、目录和批次计数。

## 1. 来源与版本

主文：Renjie Pi 等，*On Data Engineering for Scaling LLM Terminal Capabilities*，NVIDIA，arXiv **2602.21193v1**，提交2026-02-24，PDF首页日期2026-02-25。2026-09-07版本页只列v1。原文 [HTML](https://arxiv.org/html/2602.21193v1)、[PDF](https://arxiv.org/pdf/2602.21193v1)。PDF24页，正文§1–6、参考文献、Appendix A.1–A.3。

项目读取基线：`Rogerffff/RepoHarness@9f93eb64b63f04723c62432fe18027e80b0c15b0`，branch `miles-migration`。写入时重新取得共享分支最新head，基线不冒充最终提交。

配套资产以NVIDIA官方collection、两份数据卡／文件树及8B/32B模型卡为主：Corpus页面显示revision `a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9`；Synthetic-Tasks显示 `7e53648e183cee7bcb0aed623cc91a121d37fa38`；8B固定README为 `bb1413579351dfada0c203699ea32d2d08f0942c`。正文§8保留实际访问边界，不把“页面显示revision”写成已经下载并校验全部字节。

本来源尚无预分配的新目录编号，使用arXiv号唯一文件名；协调线程可之后登记正式来源号，避免并行抢占N编号。

## 2. 原文覆盖检查

| 范围 | 阅读／核查内容 | 状态 |
| --- | --- | --- |
| p.1–3，摘要、§1–2、§3.1 | 供给成本、轻量生成与scaffold关系、TB2.0定义；Fig.1、Table1 | 全读，图表已查看 |
| p.4，§3.2、Fig.2–3 | 标准任务包与Terminus JSON；区分标准oracle布局与本文合成产物 | 全读，原图已核 |
| p.5–7，§4.1–4.3、Table2 | 三adapter、seed／skill生成、镜像复用、解法隔离、teacher角色 | 全读 |
| p.8–11，§4.4、§5.1–5.7、§6、Tables3–9、Fig.4 | 去污染、训练参数、模型及类别结果、所有消融、RL仅未来方向 | 全读，所有结果表目视核对 |
| p.11–14，参考文献 | 检查尾部及Cascade/YaRN等引用身份；不逐篇重读被引工作 | 已检查 |
| p.15–16，A.1、Table10、Fig.5–6 | 九域、token与turn分布；N/mean/median取图内打印值 | 全读并核原图 |
| p.15–18，A.2、Fig.7–10 | 完整system prompt与三suffix；必需／可选字段、命令等待与任务预算 | 全读；以合同转述，不复制完整提示词 |
| p.16、19–24，A.3、Fig.11–20 | 通用生成模板与九个领域模块，包含交叉引用漏掉的末页Fig.20 | 全读并目视各模块 |

重要图页通过web screenshot读取。部分versioned入口失败后换同一arXiv当前PDF，页数／v1水印与文本一致；未使用OCR。容器requests与下载工具受DNS限制，未取到本机PDF/TeX；没有捏造本地原文附件。主稿仍有稳定官方页码链接供独立复核。

## 3. 本轮重点纠错与解释收紧

| 检查问题 | 容易写错的结论 | 正文处理 |
| --- | --- | --- |
| SFT与RL | 用veRL、有tests就代表做了RL | §2、§5：离线teacher轨迹SFT，RL为未来工作；不补PPO/GRPO公式 |
| “two-stage” | 数据生产两条路线等于两阶段参数训练 | §2.2、§7.5：生产与训练顺序分开，最终采用mixed SFT |
| 测试和oracle | 标准TB目录有solution，因此所有生成任务都有oracle | §3：adapter无tests；synthetic明确不生成oracle；seed参考解另列 |
| 原仓库真实性 | SWE prompt给文件就还原完整真实仓库 | §3.1：只确认文件实例化，未继承依赖／完整测试保证 |
| 镜像数量 | 九镜像等于九个实例、无需每题隔离 | §3.4：共享基础环境不等于共享可变状态或没有实例化成本 |
| 无额外筛选 | “No filter”可以解释成无去污染／无质量要求 | §3.6：基础过滤与complete/success筛选分层 |
| 失败数据收益 | No filter优势证明错误动作本身有益 | §7.3：样本量、更新量混杂；需要匹配token／更新的额外对照 |
| Math子集 | 各子集都因不筛incomplete改善 | §7.2：Math完成筛选点估计更高，保留各方向 |
| Seed稳健性 | 相同均值但±稍小即可证明稳健性提升 | §7.1：作者解释与证据分开，统计定义和raw重复未知 |
| 长上下文 | 32K胜出证明所有长轨迹没有价值 | §7.4：仅限当前SFT和YaRN2设置，原因仍为作者推测 |
| 课程负结果 | 两阶段SFT失败等于动态RL curriculum无效 | §7.5：保留实际顺序和未做对照，不跨范式外推 |
| 分类分数 | 总分提高意味着所有能力改善 | §6.3：scientific computing 32B从2.9到0；数学/游戏/视频仍零 |
| 单题与误差 | 60%查询=广泛数据库能力；所有±都是95%CI | §6–7：类别任务数紧邻分数；只有Fig.4明确95%CI |
| 数据规模 | 论文490,520等于全量公开可执行任务 | §3.5、§8.2：样本／任务／镜像分开，公开366,154对应adapter+skill |
| 领域列表 | 正文／附录九域可以无声改成同一名单 | §3.3：dependency management与system administration差异分别保留 |
| 当前资产 | HF viewer失败就代表资产没公开或损坏 | §8：文件树仍在，格式／扫描限制与执行有效性分开 |

这些是事实边界、原文不一致或推论限制，不是将所有项目都指认为原作者错误。特别是没有oracle和不过滤失败，首先是作者的SFT生产选择，不能用本项目RL标准替它改写研究目标。

## 4. 数值、结构与链接检查

本地独立加法核验：162,692+31,960+31,661=226,313；124,366+139,841=264,207；两路线合计490,520；公开adapter+skill合计366,154；差额124,366对应seed。验证Table4类别数相加为89。

计算主模型增益10.53/16.16/24.03个百分点，synthetic complete-only与success-only相对No filter分别保留约39.6%和31.6%，No filter/success-only约3.17倍。没有由均值长度推算训练token总额或GPU费用。

Fig.4保留0/10/100%的少量目测量级，明确横轴标签并非按数值间距绘制；Fig.5/6保留原图打印的精确摘要统计，不用柱高伪造精确截断率。表格中现成结果优先采用表值。

Markdown本地检查包括：reference链接定义、导航anchor、表格列数、代码块成对、行尾空格、替换字符和新增文件路径。内部关联仅指向已经存在的O01、CalibForge、SWE-smith和Codex反馈；本记录与正文互链。

## 5. 残余缺口和独立复核重点

最值得独立复核的是：§4.1.2/4.2.3的tests与oracle范围；Tables6–9的样本／预算混杂；Fig.4的误差标注与近似读数；Table4负结果；公开数据是否确实不含论文seed-based子集。各自都已给明确位置，无需重新追逐大量无关新论文。

本轮没有取得整套数据生成／过滤／SFT原始recipe，未确认每个训练token的mask与分母，也未运行样本、镜像和模型。未把这些缺口填成通用SFT默认；未将最新Harbor/veRL代码用作论文历史配置。数据卡许可仅记录原标注，不替所有上游内容作许可判断。

并行交付只新增正文和本记录。README、SOURCE_CATALOG、批次状态及其他任务由汇总会话维护；不修改O01正文来顺带解决其单独反馈。远程commit和回读结果在交付回复中给出，文档不在写入前预填成功状态。
