# E8 ECHO：作者自查与并行交付记录

日期：2026-09-07。正文：[E8_echo.md](../E8_echo.md)。

**状态：全文与附录精读、图表核查及作者自查完成；尚未独立复查，也没有复现训练。** 本任务由用户在分叉会话中单独分配，当前工具不支持创建独立审查子 agent。没有可核验的线程 UUID 或运行 effort 元数据，故不编造这些字段。

## 1. 来源与边界

主来源为 Microsoft Research 的 *ECHO: Terminal Agents Learn World Models for Free*，arXiv `2605.24517v1`，2026-05-23。2026-09-07 查询版本历史仍只列 v1。PDF 14 个物理页；全部正文 §1–7、附录 A–D、致谢和参考文献范围均已检查，没有其他未读的技术附录。

官方实现固定 `microsoft/echo-rl@f4c3c7ecf78412a507d3c7b0dc0079cdae45d10c`（2026-05-26）；README 指定的 SkyRL 基座为 `43aab09782953cc7cfc93bda52b1635d717ce446`。本次没有全文审计该 SkyRL 基座，更没有把当前配置倒填成论文历史作业配置。

RepoHarness 读取基线：`miles-migration@f5d373b566244ddc02b53b881e773257511820fd`。写入前另取最新分支头，仅添加两份 E8 专属文件。遵循 [Codex 对 O01 的反馈](15_O01_codex_quality_review_20260907.md)，不改 README、SOURCE_CATALOG、批次总状态、旧笔记或训练实现。

## 2. 实际阅读及图表核对

| 范围 | 实际核查内容 |
| --- | --- |
| §1–3，Eq.(1)–(3)，Algorithm 1 | GRPO 动作位置、环境 CE、完整 observation 分母、单 forward、目标子集和 λ 扫描 |
| §4 | 2,700+6,170 题、GPT-5 筛选、8,770/100 切分、三类模型起点、harness 与预算 |
| §5.1、Table1、Fig2 | 所有主表数值；图的坐标、配色、阴影含义、交叉和终点量级 |
| §5.2、Fig3 | Qwen3-32B 的 2,168 条异策略评测轨迹、全部柱上 CE 标签 |
| §5.3、Fig4 | SFT gap、ECHO lift、恢复比例；与附录 C 交叉检查 |
| §5.4、Table2–3 | 各模型学习步数、效率定义差异、timeout/turns/completion tokens，保留反向结果 |
| §5.5、Fig5 | 适应起点、四个目标分布、筛选条件、PyTerm 拆分、内嵌表和负结果 |
| §6–7、致谢 | 按作者组织保留相关工作、结论与系统定位；不扩写为其他论文的全文精读 |
| Appendix A、Fig6 | warning 对数坐标、env 曲线、step60 文本与图示的不同量级 |
| Appendix B | 优化器、学习率调度、clip、λ、硬件、步数、评测重复与统计措辞 |
| Appendix C、Table4 | 全部精确表值及 SFT gap 算术 |
| Appendix D、Fig7 | OT-SFT 三条评测曲线的近似终点，与 Table1 的差异 |
| References | 检查到完整尾部，确认依赖身份；未逐篇读取所有被引用来源 |

目视核对了 PDF 第 1、3、4、5、6、7、8、9、13、14 页，覆盖全部 7 幅编号图、4 张编号表、3 个编号公式与 Algorithm 1。曲线近似读数明确标注为目测，不数字化每一个点，不冒充作者精确终值或置信区间。

部分固定 v1 的截图调用失败后，使用当时无版本 PDF 入口补读；该入口同为 v1 水印、14 页与相同正文。HTML 与 PDF 文本结合使用。容器直接下载 PDF/TeX 失败，没有取得本机源文件，也没有上传第三方 PDF／图像副本。本轮没有读 repo 的 `echo.pdf` 镜像，故不宣称它与 arXiv 逐字节一致。

## 3. 官方代码附查范围

| 正文来源编号 | 已读文件／范围 | 附查目的 |
| --- | --- | --- |
| C0 | README 全文、固定提交的完整文件树 | 实际开放资产、SkyRL 依赖、MIT 代码许可；不泛化为全部数据许可 |
| C1、C8 | 两份 Qwen3-8B YAML 全文 | 基线与 ECHO 的目标开关；与论文／附录的参数差异 |
| C2 | `terminal_agent/terminal_agent_generator.py` 第1–720行 | 批次执行、观测生成、token/mask、失败、评分及 world-model-only 字段来源 |
| C3 | `world_modeling/trainer.py` 全文 | mask 右对齐与 padding、辅助筛选、动作目标清零 |
| C4 | `world_modeling/loss.py` 全文 | 实际 CE 分母、零目标处理、系数与诊断指标 |
| C5 | `world_modeling/fsdp_worker.py` 全文 | 局部 batch 权重、辅助项消费、共用 forward 的调用关系 |
| C6 | `patches/skyrl_minimal_hooks.patch` 第1–260行 | extra tensors 与零填充、同一 actor forward 后的辅助 loss hook |
| C7 | `terminal_agent/entrypoint.py` 第140行至末尾 | 真正选择的 generator/trainer、fsdp/fsdp2 限制、数据路径 |

没有继续把整个 Harbor、SkyRL、分布式 reducer 或终端任务集当作本次审计对象；父类过滤、全局分片数值等价与实际部署表现留作明确未检查项。读取调用链是代码证据，不是已运行的故障复现。

## 4. 成文时实际保留或修正的关键问题

| 核验项 | 本稿处理 |
| --- | --- |
| 正式身份 | E8 是 hybrid observation-prediction objective，不只是“新增6,170题”的管线文章；共享目录的更新留给汇总线程 |
| PG 与 CE | 两套 mask、两类目标；工具 observation 没有因此变成 policy action，也没有 teacher logits |
| 辅助归一化 | 分子为 O'，分母为全部 O；用独立算术例说明，区分 selected-token CE 指标 |
| 原文聚合 | Eq.(2) token-global 与 §4 sequence-level 不自动等价，未擅自统一 |
| 训练配置 | 正文0.05与附录SFT/base系数、附录与YAML的β2/warmup/clip均分列 |
| 效率定义 | Table2“各自峰值”与正文“共同GRPO阈值”不同，不强称已复现同质量墙钟加速 |
| 数据与成本 | 8,870是最终池，不推出100%构建或筛选率；新增任务与外部solver不属于零成本 |
| 主表负结果 | OT-SFT p@3下降、p@5持平；14B timeout和turns变差，不概括成每项全面改善 |
| 观测预测的证据 | 固定异策略历史的 teacher-forced CE，不当作自由模拟、规划或因果中介已验证 |
| 专家SFT比较 | 内部约覆盖gap，但TB2约一半；不把微小超过或恢复比例写成SFT无价值 |
| 曲线与表 | Fig1/2箭头、Fig6阈值、Fig7终点与Table1存在不同，不自行决定一个“正确值” |
| verifier-free | 从已经reward训练的checkpoint继续；更新目标、筛选信息、模型选择、实际评分调用分别说明 |
| 实际env_only | 解析错误、无命令提示等可进入env参数；字段名不能证明全为纯stdout/stderr |
| 代码目标开关 | world_model_only清零动作mask，但所查正常路径仍run_verifier；不反推历史实验使用违规信息 |
| 开放资产状态 | 实际找到正式微软训练代码；未定位的数据／模型／日志仅按已查README、树和配置记录，不断言全网未发布 |

上述问题有些是文献未披露，有些是表述与图表差异，有些是公开实现范围；不是一份“论文全部失效”的指控清单。主要训练对照和预测能力改善仍有原文结果支持。

## 5. 本轮执行的本地检查

对 Markdown 检查引用式链接定义、首屏 anchor、数学块配对、UTF-8、行尾空格、表格列数和相对链接的预期目标。重新计算任务数量、CE 分母示例、主表增量／倍率、Table2步数比、Table3相对变化及Table4恢复比例。原表50.0%等四舍五入值仍保留原值，不用显示精度产生的细小差别改写作者表。

这些仅为文本与算术自查；没有执行模型训练、GPU 梯度对拍、环境生成、权重下载或 benchmark 复现。没有独立 reviewer。

## 6. 后续复查优先点与交付

建议独立复查首先核 Eq.(2)(3) 的分母、App.B 的配置差异及 Table2 的效率定义，再核 Fig6/7 与正文／主表的对应关系。代码方面优先沿 C2→C3→C4/C5 检查两个 mask 与 verifier-free 的实际消费，不必重复整个框架静态审计。

正文文末仅给少量条件化的项目候选：复用真实工具反馈、区分PG/CE资格、检查实际监督文本；没有批准改动 miles、现有 policy loss 或 taskset。

正式交付路径为 `reading_notes/E8_echo.md` 与本文件。提交前使用分支最新 tree 并保留其他并行工作；提交成功与远程回读结果在最终回复中报告，不提前编造 commit。README、SOURCE_CATALOG、批次总状态和旧 E8 材料均未修改。
