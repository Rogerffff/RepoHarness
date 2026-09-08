# Task08 · OpenThoughts-Agent 作者自查记录

日期：2026-09-08。正文：[task08_openthoughts_agent_2606.24855.md](../task08_openthoughts_agent_2606.24855.md)。

**状态：正文与A–G精读完成，作者自查完成，待独立复查；没有训练／环境／权重复现。** 当前会话没有可创建独立审查子agent的工具，不编造reviewer、线程ID或运行effort。Task08是本轮用户分派编号，不覆盖库中E8（ECHO）。

## 1. 输入与版本

- 主来源：`arXiv:2606.24855v1`，2026-06-23，36页；本轮版本历史只列v1。
- 官方博客：2026-06-10的OpenThoughts-Agent发布文章；不是独立复现。
- HF实际查看：SFT-100K dataset card/viewer、RL-5K README、32B SFT model card、8B RL model card。未下载全量parquet或权重，未锁定全部HF revision。
- 历史代码pin全部展开：OT-Agent `4e2b8422b7ee5ca4af3566df603c1ca58d576238`；SkyRL fork `ada3bd4f952ef5ff59134389e5577f54530d29f6`；Harbor `94f358bc51fb214d8089f098c746ef6f3f66e9a3`。
- 当前OT main仅作额外文档核验：`3bd1917e62c9d03d73063b433f5c442c279c0563`。
- RepoHarness读取基线：`research/nemo-rl-packing-loss-20260908@827dcdf2f113b745e2c3901e58c38bb12e634131`。交付使用从该快照新建的 `research/openthoughts-agent-20260908` 独立分支，避免覆盖其他线程。

## 2. 覆盖与图表检查

通读摘要、§1–6、全部A–G；References用于来源身份核查，不将引用列表中的全部论文标成也已精读。

| 材料 | 完成范围 |
| --- | --- |
| 正文六阶段数据流水线 | 来源、混合、增强、任务过滤、教师、rollout过滤；没有仅摘最佳配方 |
| 数据扩容 | 同题补采、同来源新题、描述改写、增加来源四条路线；小规模增强负结果与大规模条件分别记录 |
| SFT／RL | 两个SFT规模、独立8B ColdSFT+RL；配置、样本单位、预算和目标未披露项 |
| A | 完整95来源排名、两种混合presentation、等token对照 |
| B/C | 8B scaling及所有SFT参数表；硬件／成本／梯度限幅表述冲突 |
| D/E | RL配置、三处pin、近重复实验与误差估计缺口 |
| F | 300-row/100-task行为分析、两个相反策略、过探索／超时崩溃、全尝试和条件均值区别 |
| G | 全部评测、harness选择、超时、OpenSWE未闭合复现、TB2.1单baseline核验 |
| Fig.1–8 | 均目视核对曲线、坐标、分项数量与caption；曲线不是全部逐点数字化 |
| Table2–24 | 均通过PDF原图核对；未将全部表逐行复制进正文 |
| Table1 | p.3截图多次失败；PDF提取文本与Table23原图、官方32B模型卡交叉核数，仍保留单页目视缺口 |

HTML缺表、附录C空白及错误`LABEL:`引用，均由PDF补读；正文的表号／页码以PDF为准。PDF本机下载与TeX未取得，未使用OCR；这属于本轮获取状态，不是作者未公开。

## 3. 实际修正与边界检查

| 项目 | 本稿采取的处理 |
| --- | --- |
| “32B SFT+RL”误读 | 明确32B只有SFT；RL只在独立8B冷启动线上 |
| “100次同条件重复”误读 | >100是多个阶段／来源的消融，不是全因子或独立团队复现 |
| 最佳教师 | GLM4.7按z-score胜出，Kimi raw均分／SWE更高；不将二者混同 |
| 五轮筛选 | 对照匹配约145M token，不夸大为所有FLOPs／费用相同；不是RL长度reward |
| 数据多样性 | 区分原始来源、底层问题、改写表面、rollout和训练行；997 Tezos底层问题没有变成21K新问题 |
| 100K计数 | Fig4分项相加94334；HF viewer显示94334；保留卡片100000声明而不静默纠正 |
| 公开数据字段 | 观察到trace_source含main/summary、result含timeout/null；未以可见样例推全量比例或训练污染结论 |
| SFT／RL来源 | pymethods2test在SFT第85、RL最优；不是永久低／高质量标签 |
| RL增量 | 区分base→SFT+RL约17.7pp与强SFT→SFT+RL约0.5pp；保留SWE/Med回退 |
| 行为解释 | 保留探索增加与后期崩溃；LLM judge是30对轨迹、非独立反作弊审计 |
| 统计与时序 | 不混step45发布、step48诊断、F的wall-clock；不将11K分析轨迹视为实际总消费 |
| 近重复实验 | 不是只换seed；Table20均分范围和正文不一致，caption没有正文提到的完整mixed variance公式 |
| 共同harness | 主榜取每模型每题集best harness，含部分原论文补值；不称纯权重统一比较 |
| 旧代码与现代README | 历史rl/README仍讲v1；固定基础YAML也不等于最终resolved config |
| 异步与mask | 主论文描述有staleness，模型卡写on-policy；retry exclude与训练mask两名单分开 |
| 项目建议 | 仅映射当前任务选择／基线／可验证接口，不批准新curriculum、换框架或新loss |

## 4. 实际执行的本地检查

对Markdown检查了：引用式链接定义、导航anchor、UTF-8解码、展示公式分隔符、相对路径规范与行尾空格。对下面数值使用独立Python算术计算；这是文献数字检查，不是训练仿真、统计复现或GPU测试。

| 检查 | 结果 |
| --- | --- |
| Fig4分项 | 25000+25000+22848+21486 = 94334 |
| 145M token过滤对照 | 3个单项差5.4/1.3/3.8，均值3.5pp |
| 8B七项均值（逐项公开四舍五入数） | ColdSFT+RL=27.9429；SFT100K=27.3857；差0.5571pp，对应表内27.9−27.4=0.5pp |
| 同两行的回退 | SWE31.9−38.9=−7.0pp；Med31.1−36.2=−5.1pp |
| 32B对Nemotron | 由公开单项均值差3.9000pp；Med差−14.8pp |
| Table20 Raw范围 | 21.72−19.68=2.04pp，而非正文1.6pp |
| Hero RL计算量粗算 | 24×166000/3600≈1106.67 A100 GPU-hours；不含全流程外部成本 |
| 32B／8B配置差异 | 逐字段对照PDF C/D与固定YAML；未使用另一框架默认值补公式 |

## 5. 独立复查建议与交付边界

独立复查首先补PDF p.3原图，然后优先核Table15、Table20、Table23脚注及F的统计cohort；若要复现RL，优先取得模型仓库实际run config，检查其与论文D、固定基础YAML和CLI覆写的差异，再追实际RLOO-n的组成员与loss分母。此时才值得进行昂贵GPU实验。

本次仅新增正文和本自查记录，不修改共享README、source catalog、训练代码、评测配置、旧稿或其他线程的文档。提交成功和远程回读由最终交付回复说明；不在写入前伪填commit。
