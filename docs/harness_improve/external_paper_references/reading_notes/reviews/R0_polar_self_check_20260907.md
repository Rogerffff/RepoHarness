# R0 Polar：作者自查与交付记录

日期：2026-09-07。正文：[R0_polar.md](../R0_polar.md)。

**状态：正文与附录精读、图表核对、关键配套代码定点检查及作者自查完成；待独立复查。** 本线程没有独立 reviewer／subagent，也没有执行训练或沙箱复现。未取得可审计的线程 UUID、effort 标识，故不编造相关字段。

## 1. 依据、版本和文件所有权

主来源为 *Polar: Agentic RL on Any Harness at Scale*，arXiv **2605.24220v1**，首次提交2026-05-22；本轮查询仍只列v1。实际PDF17页，全部正文§1–5、附录A.1–A.5、6幅图、4张表及2个JSON框均在阅读范围内。

官方代码固定 `NVIDIA-NeMo/ProRL-Agent-Server@6a1ead6bfac054fce6c1e62d1a77b330d96c58db`（stable，2026-08-13）。本项目读取基线为 `Rogerffff/RepoHarness@09b9d68c1803c7bb0c2d1944fcbac2bc5b34f7c6`，branch `miles-migration`。实际写入前需再次读取最新分支，避免并行覆盖。

本次落实 [Codex对O01的质量反馈](15_O01_codex_quality_review_20260907.md)：先读原文章节；代码追到实际字段消费；保留重要曲线数量级；区分未披露、未取得、未检查；仅维护两个本任务路径。旧综合调查只作为来源指针，未用作论文证据。

所有权仅包括：

- `reading_notes/R0_polar.md`
- `reading_notes/reviews/R0_polar_self_check_20260907.md`

不修改共享README、SOURCE_CATALOG、批次计划、交接快照、其他精读正文、自查记录、训练实现或项目定案。未新增或上传第三方PDF、源代码缓存和图像副本。

## 2. 原文覆盖与关键图表

| 位置 | 实际检查 |
| --- | --- |
| p.1–4，摘要、§1–2、Fig.1–2 | 问题定义、前作关系、harness不改内部代码的范围、训练器与服务分工、历史比较 |
| p.5，Fig.3；§3.1–3.3 | gateway阶段与READY缓冲，proxy与runtime职责、共享deadline；图中示意容量不是实验配置 |
| p.7，Fig.4与§3.4 | 逐请求/链合并、主代理/子代理/压缩后调用，四次调用到三条trace示例 |
| p.7–8，四组展示公式 | completion链、prompt-prefix条件、canonical tail与拼接；原文公式没有编号，不造Eq编号 |
| p.8，Fig.5(a)(b) | a轴为Training step、近90–100% rollout为目测量级；b轴为分钟，三个训练步的局部对照 |
| p.9，Fig.6 | 四个独立harness训练曲线、原始波动与平滑线；使用正文首/末十步精确均值，不以目测终点替代 |
| p.10，Table1、§4.1 | 四个benchmark前后值和百分点；reconstruction消融与reward hacking负结果；未补不存在的混训/迁移矩阵 |
| p.11，Table2与§4.2 | 七仓库逐行Attempts/Accepted/Rate、总计、122B生成配置、筛选、长度与切分；核算冲突见§3 |
| p.12–14 | §5全读、参考文献及尾部范围检查；未逐篇扩读引用来源 |
| p.15，Table3/4 | 框架比较符号定义及其历史范围；全部RL超参数和明确省略的topology |
| p.16–17，A.3–A.5 | 从PDF补齐HTML缺失的两份JSON；示例n=8/1200s不倒填RL n=16；全部API与best-effort cleanup |

正文与关键图页均从官方arXiv取得。HTML的A.3/A.4显示不完整，因此以PDF文本和截图补齐；没有将这两节误写成未披露。TeX与本机PDF下载未成功，没有因此省略已可从网页读取的内容，也没有声称作者未公开。

## 3. 实际发现、修正和限定

| 项目 | 检查结果／成文处理 |
| --- | --- |
| 表数 | 摘要comments写2 tables，实际正文2张、附录2张；覆盖记录写4张 |
| 训练分支 | 四个harness分别从同一4B checkpoint做RL；122B固定模型离线生成不构成其教师阶段 |
| 训练数据身份 | 293个SWE-Gym train任务；与SkyRL-Agent的4.5K R2E-Gym分开 |
| 示例与实验 | A.3的8次/1200秒、Table4的16次、offline的3600秒、现代配置2400秒分别保存 |
| 5.39× | 三个training steps的墙钟对照，非总GPU-hour或等能力时间；原文updates计数没有充分细化 |
| 训练曲线 | 首末10步均值与SWE-Bench Verified分数分开；QwenCode噪声/平台没有被正面总述掩盖 |
| Reward hacking | 保留作者的现象与信用解释；未造攻击类别、频率或prefix-merging已消除作弊的结论 |
| Table2加总 | Attempts逐行合计1589而Total为1638，差49；Accepted合计504一致 |
| Table2 pandas | 98/477约20.55%，原表19.7%；PDF/HTML相同，不自行改一栏或猜retry解释 |
| 64 GPU-hours | 122B离线数据生成成本，不是四个RL run的训练成本；没有租金外推 |
| 90/10切分 | 每个repo同时在两边，非未见仓库泛化；未从数据生产推下游SFT收益 |
| 原文与现代路由 | 原文/README有message candidate gate；当前函数只按prompt token前缀最长匹配。按版本差异列出，不倒判历史实验 |
| 重建截断 | 当前代码break只返回已保留链段，记录truncated统计，没有在该函数重发剩余calls；只作静态路径事实 |
| Token保真范围 | 采样目标身份与完整条件历史分开；后者的风险推理明确标为阅读者分析，未作模型logprob复现 |
| 失败mask | 按adapter实际状态→mask→logprob消费顺序区分TIMEOUT/ERROR/length；不只引用注释意图 |
| 组归一化 | 当前hook按有效trajectory均值做LOO；不写成历史论文完整GRPO公式，也不声称最终reducer已审计 |
| 框架比较 | Table3的×不是所有相近功能不存在；2025 AgentLightning不代表v1.0 |

这些不是对论文的“错误总数”。其中有原文内部算术冲突、版本差异、作者未披露项、未测试的实现边界和读者分析，应分别处理。

## 4. 代码检查范围

详细固定链接见正文C0–C10。主要读取入口README、SWE-Gym示例README/run.sh/polar_config.yaml、bridge README、record_utils.py、prefix_merging.py与其README、adapter.py、reward_post_process.py、rollout.py第1–415行、swebench_harness.py与evaluator README。

没有把整个rollout.py、gateway状态机、评分父类、Slime动态batch/TIS/KL/reducer和全部分布式后端都标成已审计。当前代码的group_id交付可以验证字段意图与传播，但不证明所有loss项已经以相同逻辑trajectory加权。

没有执行上游源码、训练脚本、日志重放或任何针对其缺陷的最小运行复现。重建残余调用丢弃、相同prompt分支等观察应由后续针对性测试判断实际触发与影响，不推断历史模型分数受损。

## 5. 本地自查与残余事项

本地独立计算Table1全部差值、Table2加总和比例、Fig.5速度比；核对引用式链接、首屏导航、成对数学分隔符、UTF-8完整性和行尾。此类检查只是文档与算术验证。

本轮没有独立核验offline发布集：官方HF入口返回429；训练集HF页面已读，显示train为293行，未下载全量revision。没有取得四个RL checkpoint及逐题评测manifest，未用“开源仓库存在”替代历史实验可复现性。

建议独立复查优先检查三处：§4的原文不变量与读者条件历史分析是否分明；§6的局部速度/updates与最终质量边界；§7 Table2的冲突及成本归属。代码复查则集中于C6、C7、C9，不要求为了验收本笔记完整重审所有框架。

远程提交前核对最新HEAD和目标路径；只提交本任务两份文件，非强制更新branch，完成后回读并核对diff。具体提交标识在交付回复给出，不在保存前编造。
