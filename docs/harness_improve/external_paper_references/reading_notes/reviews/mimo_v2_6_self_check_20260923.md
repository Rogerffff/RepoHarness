# MiMo-V2.6 全文精读：作者自查与交付记录

日期：2026-09-23。正文：[mimo_v2_6_technical_report.md](../mimo_v2_6_technical_report.md)。

**状态：44页全文、全部编号图表与公式已读，作者自查完成；没有独立reviewer，没有训练或环境复现。** 本会话没有实际创建独立子agent的工具，因此不记录虚构的审查线程、模型设置或独立审查通过状态。

## 1. 版本、文件和实际操作

主证据是用户本轮上传 `MiMo_V2_6_technical_report.pdf`，标题 *MiMo-V2.6: Scaling Reinforcement Learning Towards Self-Improvement*，署名LLM-Core Xiaomi。44页，PDF内部创建时间2026-09-22，不把元数据当已验证发布日期。SHA256：

```text
fb81e6e083801b3358f084ed6be953dc23b0d2e434690f4541d5eae03e01e7af
```

读取与分支基线为 `RepoHarness@0554dafd633cd982288bd60a54f75da65e5c54d4`。新分支 `pro/mimo-v2-6-reading-20260923` 从它创建，正文只在末尾映射9月23日项目现状，不改A/B实施或同步快照。

实际操作：PyMuPDF读取元信息、目录及全部page text；每页独立保存文本；渲染44页；打开关键单页与全分辨率并排页图，核验17图、7表、7编号公式及p.21未编号IS mask；再按source回查正文表述。没有使用OCR。附录A只有贡献与致谢，已读，不遗漏技术附录。

原始PDF、图片、提取文本和本地算术检查脚本不上传仓库。上传的是变换后的中文精读和本记录；读者可用文件名、指纹与页节定位恢复对应版本。

## 2. 视觉核查清单

| P页 | 材料 | 重点核查 |
| --- | --- | --- |
| 1 | Fig1 | 六域训练曲线、Pro/Flash颜色和step轴；不是最终MOPD2表 |
| 5 | Fig2 | audio/visual输入、hybrid主干、MTP示意 |
| 6 | Table1 | 主干、ViT、audio两个模块、spec decoder；层／head／参数口径 |
| 8 | Fig3、Eq1 | 预算美元、avg@3、两模型cost share、prompt内分母 |
| 10 | Fig4 | 来源模块、accuracy/robustness两种检查，F2P/P2P前后条件 |
| 12 | Fig5 | general环境与任务两条流水线、真实文件和mock软件 |
| 15 | Table2 | 五个repo的示例行为，任务／思路／动作身份，不将例子做成操作教程 |
| 16 | Fig6 | 清理轮次与检测hack比例的不同分母；检测不等于总体真实发生率 |
| 17 | Fig7 | GRS offline rubric→online scoring，与GAR组内对比两条路径 |
| 18 | Eq2、Eq3 | reward乘法、pass集合、未cap质量守恒、失败分支 |
| 19 | Fig8、Eq4 | GAR code-only/128/token-mean；passrate、turns、token三曲线；长度扣分幂次 |
| 20 | Eq5 | 正负分支、两种scale、sum计token、零分母与clip说明 |
| 21 | IS mask、CyberGym脚注 | ratio四个界和[0.2,5]；修订评测环境不能忽略 |
| 22 | Fig9 | score与总token同时观察，未默认token普遍下降 |
| 23 | Fig10 | 4个训练与3个held-out harness，两个mean |
| 24 | Fig11、Fig12 | layer9专家指标；冻结/可训练路由；123.1h/81.8h含失败恢复 |
| 25 | Fig13 | Standard MOPD、Teacher-Prefix、SFT-Prefix的状态和teacher不同 |
| 26 | Table3 | 17行×6模型原值；CyberGym V2.5为40.1，不是40.0 |
| 28 | Fig14 | 控制面／数据面、actor pool、KV/top-p/routing、QDQ与training方向 |
| 30 | Fig15、Eq6/7 | log轴、25source、start/end均值；acceptance非pass@1；调度变量重名 |
| 31 | Fig16 | 四策略仿真、6源精确输入、明确排除training/credit/staleness/replay |
| 34 | Table4/5 | weighted SFT总／loss tokens，7k task identifiers，不是镜像数 |
| 35 | Table6 | avg@3与avg@1；四域独立RL，不当统一checkpoint |
| 36 | Table7 | 21个dataset×harness格子、7列不加权mean；重复核对Pro/RL均值显示差 |
| 37 | Fig17 | 九张网站截图；原prompt已标truncated；视觉展示非完整功能验证 |
| 37–44 | References与Appendix A | 关键引用身份、尾页完整性；最后一页为致谢与贡献 |

部分页使用并排原尺寸渲染作总览；小字、公式与Table7均回单页确认。没有留“图片打不开所以仅凭图注”来支撑关键结论的情况。

## 3. 自查时重点收紧的解释

| 问题 | 容易发生的过度归纳 | 本稿处理 |
| --- | --- | --- |
| 训练阶段 | You Only RL Once意味着没有SFT/蒸馏 | 保留主RL前short SFT、后MOPD2，以及独立9B路线 |
| 数据数量 | 7k就是Pro/Flash训练环境总数 | 主大模型未给完整规模；7k为开放集合task IDs |
| 环境审计 | 四次审查能证明正确，八次执行能证明题意 | potential FP/FN仅为复查线索；稳定性与准确性分开 |
| GRS/GAR | 同一条流水线解决全部稀疏奖励 | 不同子集；GRS可分all-test-pass但不创造all-fail信号 |
| GAR守恒 | capped最终版失败优势不变 | 区分Eq3未cap和cap后全组中心化，给显式算术例 |
| 行为塑形 | 正轨迹错误token变负；质量守恒等于梯度守恒 | 正错误为零，plain-token质量与IS/分母加权梯度分开 |
| loss | 默认PPO min/clip、默认GRPO std、默认零KL | 恢复Eq1和p.21mask；没给的项不补 |
| 多harness | 迁移改善证明多样性独立收益 | 记录缺同条件single-vs-multi完整比较；原作者不推荐生产harness直训的理由不删 |
| router | 冻结router即可不做R3 | 参数冻结与激活／数值导致的路由选择分开 |
| Sample Mixer | 仿真图证明全链加速 | 明确图16排除项及真实运行中的预测失效 |
| 成本 | 31.3%、6%、10.3%可以相乘 | accepted length/global throughput/per-node throughput分母不同 |
| 9B结果 | 一列RL代表一个全域模型 | 四个域独立训练；Table7另一个coding实验 |
| 开放代码 | generic README等于论文全栈公开复现 | 固定三个fork，只读声明范围；主大系统仍是SGLang/Megatron |

源文数学中的A、alpha、r、M在不同章节重名；正文逐处解释，未为了统一符号而改写原方法含义。没把这些边界都当论文错误。

## 4. 已执行的算术和文档检查

在本地草稿执行45项检查，覆盖：7个编号公式和math分隔符；导航／引用式链接；字符编码和行尾；各Markdown表列数；1,568×16；主任务比例、两模型成本比例、SFT total/loss token sums、6源目标占比；Table7九行均值范围；Code mini增量范围；GAR未cap和cap-recenter例；行为塑形plain-token质量例。

一次初始检查发现：Table7 Pro的multi-harness RL，按七个**已round**显示数值求均值为46.442857，而原表Mean为46.5。已重新看原图确认抄录无误，正文明确保留源值；可能来自底层未round值，未取得底表不作擅自修正。检查因此分开记录显示值复算和可兼容rounding范围，不声称所有表均能用显示小数精确重算。

源文Table4已经说明share来自未round总数，同理不因显示token数复算小差异改表。Table3中CyberGym V2.5数值回图校正为40.1。外部Muown标题回arXiv核为 *Row-Norm Control for Muon Optimization*，不沿用泛化标题。

这些是算术／文档检查，不是模型梯度测试或训练复现。repo本地相对链接按现有目录层级组织；正文指向用户PDF的位置用P页节而非不存在的仓库PDF路径。

## 5. 外部补查与访问限制

Muown、ReOPD、DFlash取得一手arXiv摘要／版本信息，作为术语与关系补查，非完整关联论文精读。CodeMidas在P的书目和正文中可定位，本轮外部一手入口未取回，不从二手搜索补入其规模数字。

官方公告、动态训练日志及两款HF模型卡正文未成功返回；搜索索引不能代替完整页面。GitHub官方组织中实际发现并固定了：

- `mimoagent@467f0a19016f0ac4d63b8d17a1f0da9ba07f232c`：完整README。
- `uni-agent@c63e0b01c375ebede95e01fe92bc367df24e5bf3`：完整README。
- `verl@e2b9fc03c6e01247f5d93c44201b068ea320b7de`：请求前180行，工具返回截断；只使用已见背景，不称完整README已读。

没有训练代码深审、权重下载、数据／镜像测试或全套许可核验。上面这些开放资产访问缺口不影响用户上传PDF的完整阅读，也未被伪记为“作者未公开”。

## 6. 交付范围与下一步复核入口

本次只新增正文和作者自查，不重写共享README中的历史计数，不改项目实现或旧笔记，不把新分支自动合并回协作分支。最终commit和回读校验在交付回复报告；提交前不预填假SHA。

独立复查优先看：Eq1与Eq3–5的分母／cap／mask职责；四次求解与八次rerun的精确对象；9B独立RL与multi-harness的成绩归属；Fig16仿真排除项与真实失败分析；公开fork与私有大模型系统的边界。修订应针对具体事实与缺口，不要求因为没有全套开放日志就把已经读完的44页重新从头总结。
