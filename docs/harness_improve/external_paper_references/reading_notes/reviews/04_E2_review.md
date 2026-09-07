# E2 CalibForge 独立精读审查

审查日期：2026-09-07。审查配置：独立 GPT-6 Astra / high。对象：[E2 初稿](../E2_calibforge.md)。本轮仅写本审查文件，没有修改笔记或项目实现，也没有再委派审查。

## 1. 实际阅读范围与总体判断

先逐页读取原始 PDF 的完整提取文本，按实际标题与附录建立下面的独立清单，再打开初稿逐项比对；未把初稿或旧摘要作为原文替代。全文为 27 页，正文 §1–5、Algorithm 1、Eq.(1)–(2)、Fig.1–9、Table 1–3、附录 A–F 均在范围内。参考文献页用于确认完整结构和引用出处，没有声称精读其所引各篇论文。另目视复核 PDF p.5 的公式、p.12 的 Table 3/Fig.8–9、p.25 的 Table E1/F.1。

在线核对了 [arXiv v1 页面](https://arxiv.org/abs/2608.06352v1)的正式标题、作者与提交记录，以及[官方 PDF](https://arxiv.org/pdf/2608.06352v1)的版本和页数。来源内容以本地原始 PDF 为主，在线页面用于交叉确认。读取了 [manifest](../sources/E2/source_manifest.json) 所列九份固定版本 README、配置和源码快照；九份 SHA256 均与 manifest 相符。另检查原始 HF 文件清单的根文件和轨迹相关命名。未下载模型权重、环境镜像或整套训练数据，未运行作者训练/评测代码，未审计 AweAgent 完整 runner。

项目映射检查限于 CURRENT-STATE-BRIEF 的当前状态、边界及未闭合项，以及 2026-09-07 项目一建议的 §3–9 相关内容；没有将咨询建议视作已批准实现。模板要求的后训练内容没有因为暂不用于 SWE 而被略去。

**总体：主要方法、模型关系、附录覆盖、表格转录和因果边界准确。发现一项需补的 P2 数值分母缺口，以及三项 P3 表述/资产落差。没有发现 P0/P1 级错误。完成下面定点修订后可交付为完整精读；本报告不宣称论文实验已复现。**

## 2. 独立覆盖清单与逐项对照

| 原文实际结构与位置 | 独立识别的后训练内容 | 初稿对应与判断 |
| --- | --- | --- |
| 首页、§1 Introduction，p.1–3 | 训练环境必须可执行、可验证且相对 solver 有挑战；论文贡献为任务构造校准与离线 SFT | §1–3；覆盖，不误写在线 RL |
| §2.1 Overview、Algorithm 1，p.3–4 | `V(τ)`、`γ`、验证修复循环、每轮探测、满足条件立即返回、最多 Rmax 后丢弃 | §3、4.1、5.1；覆盖；19/15 与早停的关系还可说得更明确，见 F2 |
| §2.2 Candidate Task Authoring and Validation，p.4–5 | clue、技术研究、多方向选择、规格与安装/资源预试；instruction/environment/tests 联合构建；解答工件与未声明要求检查；fail-first 和隔离自解 | §4.1；实质覆盖，检查时序有一处措辞错误，见 F4 |
| §2.3 Adversarial Solver Calibration，p.5 | 每 solver 独立 sandbox、相同指令；verifier 二元结果；完整轨迹及结构反馈；multi 分歧和 strong-pass/weak-fail 两公式；四态诊断 | §4.2、5.1；公式、角色、诊断与接受信号区别准确 |
| §3.1 Experimental Setup，p.6 | author/solver/teacher/student；100 步/30 分钟、50 轮；2 次蒸馏、200 步/1 小时；成功轨迹过滤；full-parameter SFT；基线重蒸馏；评测与去污染 | §3–8；覆盖，评分有效分母新增疑点见 F1 |
| §3.2 Main Results、Table 1，p.7 | 两底座全表、基线限定、三 benchmark、均值与 SEM/单次运行、百分点增益、迁移 | §7.1–7.2；转录及差值正确，未把全量表写成等成本因果对照 |
| §3.3 Analysis of Synthesized Data、Fig.3–7、Table 2，p.7–11 | 1,263+4,168；16类；pass@3 分类图；能力标签长尾；工件/类型/依赖/测试统计；teacher steps 与 thinking tokens 分布 | §4.5、7.2；覆盖，标签分母、distinct 与总计、步数与推理量区别准确 |
| §3.4 Effect of Solver Calibration、Table 3，p.11–12 | No/Single/Multi/Contrast；各1,300题；保留轨迹并不相同；Single同时得到结果与轨迹；等任务数不等 token/API预算 | §7.3；覆盖，Multi 1,300 与最终1,263的关系已列未知 |
| §3.4、Fig.8–9，p.11–12 | 首次状态19/61/16/4；最终96/4；按完成run记录probe数的15/53/76/93/96漏斗与长尾 | §7.4；值准确，保留了未解释差异；应加算法早停关联，见 F2 |
| §4 Related Work、§5 Conclusion，p.13 | 与环境构造、行为反馈、solver自身反思的区别；作者归因及其证据边界 | §2、9；覆盖，没有借引用扩张为未经阅读的训练事实 |
| A From a Clue to a Calibrated Task，p.18–19 | 传感器日志 clue、24搜索、多方向排除、输入工件、CSV输出、11测试、Pro过/Flash败、自评CRC示例不一致 | §4.4；覆盖，单例搜索/判断不作总体结论 |
| B.1 Removing Procedural Hints after Both Solvers Pass，p.20 | 交易记录修复；8/17步均过；去流程提示后强过弱败 | §4.4；准确，未偷换成去验收条件 |
| B.2 Clarifying Comparison Semantics after All Solvers Fail，p.20–21 | 数据库导出；50/15/26步全败；共有字段比较语义；复测GLM/Flash过、Kimi败 | §4.4；准确，未把规格歧义误判纯难度 |
| B.3 Generalizing an Overly Prescriptive Verifier after an Inverted Outcome，p.21–22 | 强40步败/弱38步过；合法整体加密被逐字段布局测试误杀；修 verifier 后目标关系 | §4.4；准确，没有声称全库误杀率为零 |
| C.1 Tool Interface、Table C1，p.22 | execute_bash、str_replace_editor、finish；持久 runtime，结束后评分 | §6.2；工具面准确，区别于 author web research |
| C.2 Prompt Templates，p.23–24 | system完整工作流、工具、长任务、验证、安全/范围要求；instruction/workdir user包装；必须finish | §6.2；实质覆盖，明确不是完整author/revision prompt |
| D Benchmark Decontamination，p.24–25 | exact14-gram；规范化5-shingle Jaccard；0.30/0.45阈值；路径/测试函数/任务族；蒸馏前删除 | §4.3、9；覆盖，未因正文称full matching rule而虚报完整可执行规则 |
| E Supervised Fine-Tuning Details、Table E1，p.25 | 全参数多轮SFT；最终10epoch checkpoint；全部超参、64 H20；有效batch关系 | §5；覆盖，128与64×1×4正确保留未解，不补TP=2 |
| F.1 Reasoning without Producing the Required Artifact，p.25–26 | regex-log；30B三败、35B三过；交付文件缺失/指定接口验证 | §7.5；准确，未将中间推理当完成 |
| F.2 Committing to Partial Forensic Evidence，p.26 | password-recovery；同样三败/三过；前缀误计长度、片段拼接、23字符约束 | §7.5；准确，未泛化精选案例比例 |
| F.3 Changing State before Preserving Recovery Evidence，p.26–27 | db-wal-recovery；两模型六次全败；5条基础记录与6条WAL；打开数据库先破坏恢复证据 | §7.5；准确，保留更强模型共同失败与schema不足 |
| 固定版本官方资产，manifest所列九份快照 | 数据/模型/镜像引用、README范围、部署示例、运行入口、默认预算、加载跳题、same-session评分与reward约定 | §6.3、8；主要准确；README的已发布轨迹声明应补，见 F3 |

## 3. 分级发现与建议修订

### F1 — P2：数据集规模不能自动当作实际评分分母

**位置：初稿 §6.1、§7.1、§9.2；原文 §3.1 p.6、Table 1 p.7、Fig.3 p.8。** 论文声明使用731题SWE-bench Pro public set并只评测一次，但多项 Table 1 分数不能由整数成功数除以731并四舍五入到小数点后两位得到。例如30.94%的最近整数解为226/731=30.91655%，应显示30.92%；3.26%的最近整数解为24/731=3.28317%，应显示3.28%。35B base的41.29%同样不匹配。并非所有行都不匹配：44.32%=324/731四舍五入后成立。

TB2也有一处独立问题：Fig.3分类题数合计89，Table 1说三次运行均值。若每次均以89题二元结果等权计分，则均值只能是整数总成功数/267；35B base的39.10%不可能由这个口径得到，104/267=38.95131%，105/267=39.32584%。CalibForge两行32.58%=87/267、47.57%=127/267则能对上。这一点由主作者提出核查，审查者已独立计算确认。

**建议：** 原表照录，不擅自“更正”成绩；把731/89标为论文或图中声明的集合规模，同时说明实际有效分母、任务排除或聚合规则不足以核实，列入复现未知项。不能自行推断丢弃了哪些题、每行分母变化、宏平均或多次采样，也不据此断言作者分数虚假。现有SWE-Pro单次分数间百分点相减可作为“报告值差”，不能据整数成功数解释。

### F2 — P3：19%与15%的未解关系应联系Algorithm 1早停

**位置：初稿 §7.4、§9.2；原文 Algorithm 1 lines 7–10 p.4、§3.4 p.11、Fig.8–9 p.12。** 初稿已经写明首次verified probe与completed-run recorded-probe count是不同文字定义，也明确差4个百分点的具体规则未解释；这一点正确。但“区别是原文标注的两种统计口径”容易让读者以为两个量已经能相容。

**建议：** 增一句：在Algorithm 1“首轮满足就立即return”的字面流程下，如果两图覆盖同一批run且记录规则一致，首次目标关系与一probe完成保留应对应；论文没有提供让19%与15%相容的计数规则。这是未消除的原文报告关系，不能由“口径不同”本身解决。不要补造隐藏重试或二次验证步骤。

### F3 — P3：补记官方“成功轨迹已发布”声明与未定位资产的落差

**位置：初稿 §8.2；固定版本 [CalibForge README](../sources/E2/calibforge_README.md) 的 Released Data。** 该README明确声称release也包含按共享协议蒸馏的successful trajectories。数据卡主要说明任务目录；当前文件清单根文件是README、metadata.jsonl、image_mapping.jsonl等，轨迹相关命名搜索只找到任务内科学计算工件，未定位独立SFT/rollout文件。

初稿“未取得SFT轨迹集”没有写成“官方未发布”，并不错误；但精读公开资产时应保留这个实际读到的声明。建议写“GitHub README称包含成功轨迹；本次在固定HF卡/文件清单未定位可核的独立轨迹资产，也未验证metadata是否承载所称内容”。文件名检索不能证明轨迹绝不存在，不扩大为‘作者未发布’结论。

### F4 — P3：将“构造前检查”改为“进入验证前检查”

**位置：初稿 §4.1首段；原文 §2.2 p.4。** 原文先说jointly constructs instruction/environment/tests，再说Before validation检查初始环境没有解答工件、测试不施加未声明要求。初稿上一句已联合构建，下一句却写“构造前检查”，时序不准确。改成“进入验证前检查”即可，不影响方法主结论。

## 4. 关键数字、公式及预算检查

| 检查项 | 独立复核结果 |
| --- | --- |
| `Cmulti=1[0<Σyi<K]`、`Ccon=1[ys=1 ∧ yw=0]` | 与p.5原页一致；K=3异构模型；是任务保留判据，不是student loss/reward |
| 模型角色 | author/self-solver/strong/teacher为Pro；weak为Flash；multi为Flash/GLM-5/Kimi K2.5；两个Qwen分别SFT；Single为同模型独立subagent且有轨迹反馈 |
| task总数 | 1,263+4,168=5,431；两次teacher尝试名义数10,862；原文无全量过滤后轨迹/token漏斗 |
| 校准预算 | 每solver attempt100步/30分钟，每候选最多50轮；multi150、contrast100是名义attempt上限；75/50为累计attempt小时，不是墙钟/成本 |
| 蒸馏/TB2预算 | 分别200/500步；均1小时attempt/task；teacher每题2次；TB2三run；正文明确的16CPU/32GB不可拿后发YAML4CPU/8Gi替换 |
| 全量主结果 | Table 1全部数字与初稿一致；30B增益24.71/27.68/30.04 pp，35B8.47/3.03/3.85 pp，TB2比最强对应基线6.36/6.75 pp，算术正确；有效评分分母见F1 |
| 四臂消融 | 每臂1,300；轨迹2,466/2,493/2,425/2,561；TB2 22.47/24.34/29.21/31.09；差值1.87/6.74/8.62正确；非等token/总构造预算 |
| 校准漏斗 | 首次19/61/16/4总计100；最终96/4；累计15/53/76/93/96；无精确总run数；初次状态不是最终任务固定版本通过率 |
| 数据画像 | 16类、3,885 distinct tags、中位5；51.6%/82.2%分母为不同标签；19,911工件、362类型、615依赖、45,953测试及中位/IQR/P90转录正确 |
| thinking/steps | CalibForge中位21步/5.3k、CLI-Gym28/4.0k，其他四源中位值准确；更多生成tokens不是更高预设预算的证据 |
| 去污染 | exact14-gram；规范化5-shingle；0.30/0.45；结构证据；D确未给完整布尔组合/任务族列表/剔除量，初稿不假装可逐位复现 |
| SFT超参 | 与Table E1逐项相符；64×1×4=256与global128的条件性不符真实存在；并行布局未给，不能据部署TP8/DP1反推 |
| 模型卡补充 | 两卡均写262,144 configured maximum positions与131,072训练context；SGLang命令为部署示例，初稿新增分层正确 |
| 后发recipe差异 | README示例200与YAML/论文TB2 500确实不同；same-session、跳过加载异常、reward>0和score clamp源码描述准确；不证明全runner隔离或论文实验配置 |

## 5. 无需改动的证据边界与剩余未核项

初稿正确保留了这些重要限制：外部panel分歧不是目标student通过率；纯SFT成果不能冒充RL/OPD；Table 1不等任务规模，Table 3不等token或构造成本；精选A/B/F案例不能推成总体错误率；单次outcome不估稳定性；同一任务可被重写，96%不是固定题提升；“author/strong/teacher同用Pro的偏好风险”清楚标为读者推断；测试/代码公开不等于训练完全可复现。项目映射限定为设计候选、归因上游且不新增治理平台，这与读取的项目背景一致。

仍无法核实：原始候选分母与删除漏斗；各校准run日志、19/15关系；1,300与1,263批次关系；F1有效评分分母；完整去污染程序；SFT样本序列化/token mask/loss分母/过滤阈值与统计；训练有效batch和并行布局；完整author/revision prompt；训练/生产/推理真实总成本；镜像可运行性；README所指成功轨迹的精确资产位置。以上均是“在本轮查阅材料内未能核实”，不是对所有可能资源存在性的否定。

建议主作者将F1补入§7.1/§9.2，定点处理F2–F4，并在笔记§12记录实际审查与修订。保留原文矛盾即可交付，不需要为了消除作者未披露问题而扩大框架审计或新增实验。

## 6. 审查结束前的回读状态

主作者在审查进行中采纳F1–F3后，审查者重新读取了当前笔记§7.1、§7.4、§8.2及§9相关行，确认新增评分分母限制、早停逻辑的一致性疑点、已声明发布但未定位的轨迹资产均已落入笔记，且没有擅改原文数字。原始发现保留在本报告以供追溯。F4已发送主作者，最后处置及笔记§12记录由主作者完成。


## 7. 主作者逐项处置与证据（2026-09-07）

本节为主作者在收到正式审查后追加，保留审查者原始发现不删改。独立审查者通过本线程回读确认 F1–F3 的现稿修改；F4 由主作者按原页作定点更正。

| 发现 | 处理 | 修订定位与复核证据 |
| --- | --- | --- |
| F1 / P2 | 接受，已修订 | 笔记 §7.1/§9.2 区分声明集合规模与实际评分分母。主作者枚举整数 n/731，确认30.94和3.26均无两位小数匹配；TB2 39.10不能由整数/267得到。保持Table 1值与报告值差不动，不补造排除/聚合机制 |
| F2 / P3 | 接受，已修订 | 笔记 §7.4/§9.2/§9.3 直接对照 Algorithm 1 p.4行9–10；在同一run集合与probe记录的条件下应立即早停，19/15仍为未解关系，未添加原文没有的重试步骤 |
| F3 / P3 | 接受，已修订 | 笔记 §8.2 加 fixed CalibForge README Released Data 的成功轨迹声明；HF API原始siblings根文件仅 `.gitattributes`、README、metadata、image_mapping，轨迹名匹配项是科学计算题内工件。本次仅卡片/文件名检查，未穷尽内容，不断言所有轨迹不存在 |
| F4 / P3 | 接受，已修订 | 笔记 §4.1 的“构造前检查”改成“进入验证前检查”。原文 §2.2 p.4 先jointly constructs，再Before validation，时序与原文一致 |

笔记 §12 已替换初稿待审文字，记录实际审查模型、干净上下文、范围和处置。额外作者自查修正 E3/E4/E5 关联编号，区分模型卡最大positions、SFT context与SGLang部署示例；这些不改变论文事实。已核验完整笔记12节、公式和代码围栏、九份快照hash与文档无真实本机绝对路径。剩余来源缺口见本审查 §5 和笔记 §9.2；不为填空扩展源码审计，也不声称作者实验已复现。
