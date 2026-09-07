# R5b GLM-5.2 官方文章：作者自查与待补图记录

记录日期：2026-09-08。正文：[R5b_glm5_2_blog.md](../R5b_glm5_2_blog.md)。

**状态：官方 HF 正文、文字数表、全部 Footnote 的阅读与作者自查完成；原博客指定技术图/曲线待补。未独立审查，未训练复现。** 本轮仅维护 R5b；GLM-5.3 未开始成文。没有实际可用的独立 reviewer/sub-agent 工具，不编造线程 UUID 或运行 effort 元数据。

## 1. 实际来源与读取范围

| 来源 | 实际操作 | 不宣称完成的内容 |
| --- | --- | --- |
| 官方 HF Team Article | 读取标题、2026-06-17日期、导语、Architecture三节、slime、RL/Anti-hack、两个数表、Getting started和全部脚注 | 未拿到其修订历史与全部原图 |
| z.ai 原站 | 打开规范URL，但返回零行正文 | 不声称完成原站动态页面或和HF逐字节比较 |
| 项目已有 `pdfs/glm5.2_blog_RL.md` | 读取固定commit的完整摘录并核对B对应两节 | 摘录不覆盖架构/图表/完整评测，不让它替代整篇 |
| 项目已有 `R5b_glm5_2_blog_zai.pdf` | 核实7,170,515bytes、blob `8d8a48dda0c06933aeaff73dbf7543213bebb6f4` | 二进制和下载未取得；没有检查任何PDF页或页数 |
| HF模型卡 | 当前README正文、Raw全文、benchmark、脚注和Citation；核LICENSE确为MIT | 没有读取下载的权重或运行推理；固定完整head的README读取失败 |
| HF变更信息 | README最近提交`f2263102df303b2faa54a6861a29d1770ce846c0`增加脚注；页面head `b4734de4facf877f85769a911abafc5283eab3d9`配置变更 | 不将当前所有模型卡内容自动认定为固定head已逐字回读 |
| 官方开发文档 | 读取说明/规格/应用/评测；实际查看两幅CDN评测图G1/G2 | 未逐项执行API示例；不将其视为博客缺失技术图的同一资产 |
| 官方GitHub | 固定`zai-org/GLM-5@008de4dbcc220032eb9b80a9a9802afad46a4053`的README相关范围及树/图片元数据 | 没有整库训练实现审计，没有恢复历史运行配置 |
| IndexCache、MTP链接论文 | 核正式标题和摘要，界定是关联来源 | 不标为本轮全文精读，不导入其独立实验配方/速度数据 |

项目读取基线为`b895451cb7ad50619bf94569976fbb2c7a1ddb5f`。共享索引作为来源导航，旧模型研究回答不作为新的训练事实。既有R14/R15仅建立关系索引，不重写这两篇，也不将其公式拼成GLM-5.2最终配方。

## 2. 图表与数字核验

B的文字表包含4行MTP累加实验、19行benchmark结果（8 reasoning、9 coding、2 agentic，8个模型列）。逐项核对源表，保留破折号和HLE星号，不将这些指标统称pass@1或求平均综合分。

G1已看原图：三项长程评测，FrontierSWE的Max20Hrs，PostTrainBench/SWE-Marathon的Max10Hrs；图值直接印出，非目测插值。G2已看原图：八个benchmark、max-effort说明，HLE有/无工具均有值；没有把图中的分层柱相加为新的成绩。

重要的未取得图：原博客effort/token对比、MTP两步隐藏状态示意、long-context throughput；IndexShare附近其他图需连同完整源资产清点。没有确认缺图总数，没有根据正文“如图所示”补出坐标、baseline、GPU或曲线数字。

本轮尝试多种官方载体、仓库PDF和直连下载后仍留下这一缺口。GitHub文本接口不支持该大二进制，部分web请求cache miss，容器网络域名解析失败。**访问失败不等于作者未披露图中信息。** 正文已记录可继续阅读的位置，后续无需重做已完成的文字表与脚注。

## 3. 实际收紧与保留的结论

| 检查点 | 本稿处理 |
| --- | --- |
| 日期和载体 | HF发布时间6月17日，FrontierSWE成绩截止6月16日；旧索引日期不替代网页发布时间 |
| CritPt | 博客16.7、模型卡20.9，主表采用博客并列冲突，不选最大值 |
| TB2.1旧模型 | 博客/模型卡/图中63.5，官方README/Docs文字62.0；两种增益分别17.5/19.0 |
| PostTrainBench对手 | GPT-5.5表值28.4、G1为25.0，不将G1 silently更新为表值 |
| MCP-Atlas | 5.2表值76.8、G2为77.0，不擅自断言舍入 |
| MTP消融基座 | 原实验使用5.1 backbone/data、7 MTP steps；不是最终5.2模型端到端吞吐对照 |
| +20% | 对象为acceptance length，非概率或tokens/s；IndexShare与KVShare是同一行累加变动 |
| 训练资源 | >10专家、约2天限OPD阶段；未给硬件及前置专家成本，不能转为八卡预算 |
| PPO与子轨迹 | 作者明确采用critic/single-rollout/token loss；未补DIS、GAE、分母和mask超参数 |
| guard | 两级检测不是两个训练阶段；阻断调用后继续不等于所有动作继续有梯度，也不证明裸权重更诚实 |
| 架构/数值边界 | KV-cache FP8不是权重或梯度FP8；MTP训推偏差不是RL全过程数值一致 |
| 评测协议 | Terminus 4h与Claude Code无wall-clock上限、输出上限等不同；82.7−81不能作为纯harness因果增益 |
| 多域覆盖 | reasoning/tool结果全保留，但不由benchmark名称推定相同训练数据或十余专家的域 |
| SAO/CompactionRL关系 | 后来的专项论文与6月采用声明分开；不拼合一套未经披露的统一目标 |
| 后续模型 | 不导入GLM-5.3的logprob/吞吐说法、专属clear_thinking配置或安全结论 |

这些记录是证据限定，不把各站点差异一概判为作者错误。原文未足够明确的地方，不用工程常识替它选择。

## 4. 本地检查与边界

独立复算MTP接受长度变化`5.47/4.56-1≈19.96%`，以及TB17.5/19.0、SWE-Pro3.7、Frontier dominance43.9和两种TB协议1.7的差值。检查19行结果和8个模型列完整，重点核对四处跨来源差异是否未被覆盖。

检查Markdown引用式链接定义、导航anchor、内部相对路径形式、行尾空格、Unicode替换字符和ZIP内文件范围。不运行GPU、调用付费teacher、安装训练框架或执行文章中的工具命令。此类文本/算术自查不等于模型实验或独立复核。

## 5. 并行写入与下一步复核

文件所有权限于`R5b_glm5_2_blog.md`和本记录。写入前读取最新miles-migration头及tree，确认目标路径状态；只叠加两文件，非force更新。若并行分支前进，基于新head重建本任务提交，不覆盖他人笔记。共享README/catalog、批次状态及训练代码不改。提交后核差异与回读；实际SHA由交付回复给出，不预填成功。

下一次最有价值的是补齐原博客技术图/现存PDF快照，再独立检查§7预算和§8跨官方载体差异。补图时首先确认快照日期与正文相符，不将旧快照默认为最新网页。在没有完成这些核查前，维持“正文已读、技术图待补、独立审查待做”，不把它升级成全部精读验收通过。
