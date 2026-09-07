# Agent Lightning v1.0：作者自查与续读交接

日期：2026-09-07。对应正文：[agent_lightning_v1_2608.17528.md](../agent_lightning_v1_2608.17528.md)。

**状态：正文、公式和附录文字阅读及作者自查完成；原始 PDF／图形复核尚未完成，待补图与独立审查。** 本线程没有独立 reviewer 工具，没有执行训练或集群实验，不继承前两批的“独立审查通过”标签。

## 1. 来源和文件责任

主来源是 *Agent Lightning v1.0: Towards Harnessed Agentic RL*，arXiv `2608.17528`，不是 2025 年的 `2508.03680`。已通读公开返回的全文，包括 Abstract、Introduction、Challenges、System Design、三个 Experiments、Related Work、Conclusion、References 和 Appendix A。标题、作者与机构来自一手全文；提交日期来自原始检索 metadata。没有取得可独立确认的完整版本历史，因而不写“v1 唯一／最新”。

当前官方实现固定为 `microsoft/agent-lightning@218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4`。该提交晚于论文，配置、shaping、兼容行为与 paper-era 实验均分开。项目读取基线为 `Rogerffff/RepoHarness@f5d373b566244ddc02b53b881e773257511820fd`，分支 `miles-migration`；提交时再取最新 head，仅追加本线程两个文件。

本轮事先阅读 [Codex 的 O01 质量反馈](15_O01_codex_quality_review_20260907.md)、阅读库模板及项目一建议相关部分。只维护本篇正文和本记录，不修改 README、SOURCE_CATALOG、其他线程笔记、一次性交接包或训练实现。

## 2. 实际取得的原文与未完成范围

| 对象 | 本轮状态 | 正确解释 |
|---|---|---|
| 正文与附录 A | 已通读 | 可支撑方法、实验文字和 API／状态说明 |
| Eq.1–17 | 公式文本已读 | 主要是建模与 reduction 公式；不能当成完整 PPO 数值配方 |
| Table 1 | 九条端点的文字已取得 | 已在正文按 HTTP 方法组合整理；未看原始排版 |
| Fig.1–6、11–12 | 图题、相邻文字和可恢复公式已读 | 尚未目视原图，不声称完整箭头／状态图／时间轴已核对 |
| Fig.7–10 | 图题、文字中的起终点、峰值、均值已读 | 尚缺曲线轴、近似波动范围、熵量级及异常段 |
| PDF、TeX、原始图片 | 尝试官方入口与替代入口，未能取得 | 属于本轮访问限制，不是“作者没披露” |
| 当前 GitHub 文档／关键代码 | 已读取固定 commit 下指定文件 | 静态检查，不是代码运行或历史实验复现 |
| 数据包、镜像、最终权重 | 未下载核验 | 公开入口不等于复现资产已验收 |

本轮没有成功取得可截图的 PDF ref，因此没有伪报 PDF 截图成功或编造物理页码。成功读取全文文字不被登记成“全部图表精读完成”。官方博客、README 的宣传图片也没有被用作论文原图的替代品。

## 3. 如何落实 Codex 反馈

### 3.1 字段必须追到最终消费

不因某个字典存在 metadata 就断言其参与训练，也不因注释声称 drop 就认为真实路径 drop。实际追踪了下面四条链：

1. `proxy → events → manager → RolloutAdapter → trainer`：token/logprob 的获取、缺失、合并与 rollout correction 条件。
2. `rollout_id/data_id → 行过滤与对齐 → compute_rollout_level_advantage → normalize_advantages_by_rollout → _update_actor`：逻辑组、保留行、统计与目标的边界。
3. `evaluate → reward shaping → reward.value/raw_value → events → manager`：实际更新使用哪个奖励字段。
4. `async group collection → pause/drain → replicas sleep → update → weight publication → resume`：共享 GPU、在途请求与旧轨迹的关系。

每条静态发现都标出条件与缺口，不宣布已经测得发生率、造成论文失效或证明跨 DP 梯度错误。没有读取 upstream actor 的所有 reducer，因此局部 `S` 与论文 `R` 的尺度差只限定在已检查的边界。

### 3.2 不再遗漏非 coding 案例

分别记录 Search 的 Llama-3.2-3B-Instruct / GRPO / 六来源 EM，General Instruction Following 的 Qwen3-4B-Instruct-2507 / RLOO / 80–20 split，以及 Coding 的 Qwen3.5-9B / 三臂 GRPO。当前 sandbox 文档使用另一套 train/validation 配置，明确与原论文结果分开。

### 3.3 曲线量级不编造

正文明确给出的 25.1→41.7、51.9→70.2、35.0/33.1/38.2、step128、41.8→56.4、step208、36% 与2.41均记录其对象。Fig.7–10 的额外横纵轴和熵量级暂时标为“图待取得”，不是笼统写成 unknown 或自行按趋势估计。取得原图后，这部分仍需补读，不能以本文已较长为理由省略。

### 3.4 限制代码附查范围

代码阅读只服务论文的数据、token、统计、归一化、调度和 reward 主张，没有扩成多模态子系统审计、全仓漏洞清单或新系统设计。正文 §11 的建议不批准任何算法迁移、taskset 或新训练平台。

## 4. 已确认的解释边界与需防止的误读

| 事项 | 本次处理 |
|---|---|
| 两个归一化问题 | 先去除 reward 的重复组统计，再处理 rollout 的目标权重；不是一个开关 |
| 三臂基线 | 原基线为 token mean Eq.14，不是 sequence mean Eq.15 |
| 单改优势的负结果 | 保留33.1低于35.0，不把每项改动都写成独立正增益 |
| 三臂峰值 | 只有38.2明确对应step128，不猜其他峰值在同一步，不补多种子显著性 |
| 总体外部提升 | 41.8→56.4属于step208的SWE-bench Verified，不是内部约400题验证集 |
| “2×” | 作者端到端速度主张，没有本轮可复算的完整对照账；图6仍待核 |
| pipeline合并 | exact-token-prefix成立才合并，不能把文字相同当成原始条件相同 |
| Eq.16与代码分母 | 本地函数使用保留行数S；单测明确两rollout三行各质量1/3；不跳到最终全局梯度结论 |
| 组完整性 | manager等完整组不保证后续行级删除后仍完整 |
| None logprob | adapter可能保留行、整批不输出rollout_log_probs；trainer相关分支因此不一定做TIS |
| 去重 | 保留同prompt最后事件发生在HTTP错误过滤之前；不等于最新有效响应或已证明exactly-once |
| raw/shaped reward | 代码有两种字段，但训练取value；不把未在论文出现的penalty填回消融 |
| API与持久化 | 部分创建操作幂等不代表所有事件append幂等；内存dict不代表durable replay |
| 数据规模 | 约5K混合+1K全错与约6Ktrain/400test保留近似关系，不补造中间数和split |
| 当前代码与论文 | 脚本、默认硬件、校准数据、额外shaping等按日期单列 |

这是一份解释与证据质量记录，不是“发现论文有若干已验证 bug”的报告。

## 5. 文本、算术与交付检查

在本地文稿上执行引用定义、章节锚点、相对链接规范化、UTF-8、数学分隔符和表格列数检查；复算 reward均值、三种loss权重算例、局部R/S尺度与实验百分点差。算术检查不依赖GPU，不属于原训练的数值复现。

提交只包含本篇及本记录，写入前检查分支新head，不强制移动分支；写入后回读文件与提交差异。最终commit与实际核对结果在会话交付中给出，本记录不在写入前编造提交成功。

## 6. 下一位复查者的有限续读范围

优先取得同一版本的原始 PDF／TeX 或原图，核首页、版本和有无新增附录。对 Fig.7–10 填写 step范围、纵轴含义、近似波动区间、熵量级和关键异常段；对 Fig.6 检查是否包含正文没有写出的硬件、时长与速度对照条件；其余图核状态箭头与本文表述一致性，再补物理页码。

随后抽查三条最影响项目判断的消费者路径：行对齐是否破坏组；`per_rollout_mean` 在实际上游 actor 中的归一化；缺失 rollout logprob 的真实处置。不能只看本稿提出的疑点，应同时检查它们是否由其他已存在条件保护。若要改变“最终梯度”或“可复现收益”的状态，仍需对应实验，阅读本身不足。

在上述图形检查完成前，保留正文首屏的未完成状态。独立复查后追加真实记录，不回填不存在的reviewer身份、线程ID或实验结果。
