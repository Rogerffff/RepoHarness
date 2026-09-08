# O04 SWE-Gym：全文精读、原始评分路径与环境接入边界

SWE-Gym 将真实 GitHub issue、仓库快照、预装依赖和可执行测试组合为训练环境：论文 v2 发布 2,438 个任务、230 个 Lite 任务，用成功轨迹微调和迭代拒绝采样训练 Qwen2.5-Coder，再训练 outcome verifier 做候选排序。它不是在线 GRPO 配方；OpenHands 的一次自产成功轨迹扩充反而使成绩下降。本文覆盖全部正文、附录、图表，并沿作者 OpenHands fork 的实际评分入口追到测试命令、日志解析、F2P/P2P 和最终判定。最直接的工程结论是：原 fork 有 SWE-Gym parser；mypy 命令不能用通用文件列表补齐；历史评分器对 skip、空参考集和超时存在需要独立检查的语义边界。文末只提出对 B 线的有限验证建议，不批准任务集或修改实现。

导航：[来源与覆盖](#sources) · [数据环境](#data) · [训练及评测](#training) · [原始评分链](#scoring) · [复现边界](#limits) · [B 线建议](#project)

<a id="sources"></a>
## 1. 来源、版本与实际阅读范围

**主来源 P：** Jiayi Pan、Xingyao Wang、Graham Neubig、Navdeep Jaitly、Heng Ji、Alane Suhr、Yizhe Zhang，*Training Software Engineering Agents and Verifiers with SWE-Gym*。机构为 UC Berkeley、UIUC、CMU、Apple；Pan/Wang 为共同一作，Suhr/Zhang 为共同指导。arXiv 首次提交 2024-12-30；本次主读 **`2412.21139v2`（2025-06-06，ICML 2025）**，PDF 共 **21 个物理页**。原文有附录 A、B.1–B.6，最后三页继续放 Figure 7–9，不能读到参考文献即停止。[版本入口][Pabs]／[固定 PDF][P]／[固定 HTML][PH]。arXiv 许可链接标为 CC BY 4.0；本稿以中文改写与原文定位为主，不复制长段提示词。

**阅读日期：2026-09-08。** 通读摘要、§1–6、Impact Statement、A、B.1–B.6；检查致谢／参考文献和末页范围。全部 10 张表、9 幅图已回 PDF 截图核对。B.5/B.6 的 prompt 全文通过可读文本检查，未复制整段。没有逐篇扩读参考文献。正文与附录的差异分别保留，详见 §8。

### 1.1 代码与项目事实分别固定

| 标记 | 来源与固定版本 | 本次用途与限制 |
| --- | --- | --- |
| G | `SWE-Gym/SWE-Gym@b681068ca20628c6987b7416cc4cf03f06b77ba5`，2025-07-29 | 官方 README、两个复现指南、OpenHands 主 SFT 配置、verifier 训练脚本；晚于论文 v2，不把现代文件所有值回填到历史实验 |
| F | `SWE-Gym/SWE-Bench-Fork@242429c188fcfd06aad13fce9a54d450470bf0ac`，2025-01-27 | 项目已引用的原作者评分 fork；完整读核心 spec/parser/grading 与 gold/empty runner，另查执行器、工具函数和相关 constants；**不是论文明确声明的完整实验 lock** |
| H | `SWE-Gym/OpenHands@e644a2ca45c3623b27a7e6c169e3d479f0a87fbc`，2025-02-20 | 从复现指南追到真实远程评分 wrapper；没有全面审计 OpenHands runtime 或锁文件中所有依赖 |
| B | `Rogerffff/RepoHarness@miles-migration` 的 `d2df06d49e42b93436d10d1b7a12d4e1f0ae3be5` | 本轮项目映射基线；阅读 B 请求与资产盘点。盘点里的本地 Docker/loader 结果是 B 报告，不冒充本轮重跑 |
| HF | 官方 SWE-Gym Lite、SFT、Verifier 数据页面 | 实际读取数据预览与可见 metadata；HF revision API／固定 README 原文访问失败，未下载 parquet，也未独立枚举全量内容 |

本轮没有成功下载 PDF/TeX 到本机，但通过网页原文与 PDF 图页完成阅读。没有提交第三方 PDF、镜像或代码副本。**只交付本篇与 [作者自查记录](reviews/O04_self_check_20260908.md)**；不改共享索引、A/B 实现、训练配置、任务池或一次性交接包。

此前资料索引和 B 的请求仅用于定位，不作为论文实验事实的证据。本篇是 O04 的后续维护入口；关联的 R2E-Gym 是另一篇较晚工作，不能与本论文 Table 1 的 R2E（2024）混淆。

### 1.2 覆盖表（按 PDF 物理页）

| 原文 | 范围及处理 | 本篇位置 |
| --- | --- | --- |
| p.1–3，摘要、§1、§2、Fig.1、Table 1 | 全读；历史定位、相关工作分类、整体结果与三种计算预算 | §2、§4–6 |
| p.3–5，§3.1–3.3、Table 2、Fig.2 | 全读；采集、版本化、人工环境建设、Lite 规则、全部统计和仓库分布 | §3 |
| p.5–6，§4.1–4.2、Table 3 | 全读；OpenHands 示范微调、行为指标、自改进负结果 | §4.1、§5.1 |
| p.6，§4.3、Table 4 | 全读；Moatless 的有限动作空间、自产轨迹、多轮微调 | §4.2、§5.2 |
| p.6–8，§5.1、Fig.3–4 | 全读；两类 ORM、混合数据、采样与排序、训练规模对照 | §4.3、§5.3 |
| p.8–9，§5.2、Fig.5、§6 | 全读；三种数据缩放、未饱和解释、未来方向 | §5.4、§6 |
| p.9–12，Impact、致谢、参考文献 | Impact 全读；参考文献用于身份和范围核验，不逐篇精读 | §2、§6 |
| p.13，Appendix A、Table 5–6、B.1–B.2 | 全读；同时期工作、子集重采样方差、每题轨迹 cap | §4–6、§8 |
| p.14，Table 7–8 | 全表目视；轨迹／任务／仓库缩放与长度分布 | §3.4、§5.4 |
| p.15，Fig.6、B.3–B.4 | 全读；训练参数、教师轨迹收集 | §4、§6 |
| p.16，Table 9–10、B.5 开头 | 全读；历史榜单、逐批采样、ORM 输入 | §3.4、§4.3、§8 |
| p.17–18，B.5–B.6 | 全文检查两个 prompt：输入、输出、可见材料与模板差异 | §4.3 |
| p.19–21，Fig.7–9 | 全部目视；不同 policy/verifier、混合数据、去重缩放 | §5.3–5.4 |

<a id="data"></a>
## 2. 论文要解决的问题：可执行训练环境，而不只是补丁数据

作者区分一般代码生成、repository-level issue solving，以及训练所需的可执行反馈。一个 issue+gold patch 数据行不包含形成补丁的动作轨迹，也未必具有可运行依赖与有区分力的测试。SWE-Gym 的核心贡献是把后一层补齐，使 agent 可以实际探索、执行、取得测试反馈，再训练 policy 或 verifier。[P, §1–3, pp.1–5][P3]

Table 1 的比较对象包括 CodeFeedback、APPS、HumanEval、MBPP、R2E（2024）、SWE-Bench train/test、SWE-Gym Raw 和 Full。它把“仓库级、预装可执行环境、真人任务、训练实例数”分开。SWE-Bench 当时 train 的 19,008 行不等于提供了 Full test 那样的环境；R2E 的 246 个实例不是后来 R2E-Gym。表中“first”及“没有适合训练的数据”的判断属于作者当时的历史范围，不是 2026 年生态结论。

两种 agent 是不同实验分支：**OpenHands** 使用较自由的 ReAct 工具交互，模型自行规划；**MoatlessTools** 用人工定义的定位、编辑等工作流收窄决策空间。后者的较好起点并不能单独证明短 horizon 的因果收益，因为工具、上下文和流程同时改变。[P, §2、§4.1, pp.2–5][P5]

本文必须区分三种“验证”：

1. **环境／任务验证**：gold 与原始代码在测试中的行为差异，形成可用任务。
2. **可执行评分器**：对候选 patch 运行规定测试，生成成功标签。
3. **学到的 ORM**：读取轨迹或补丁上下文，估计成功概率，用于 Best@N 排序。

第三项不是第一、二项的替代，也不是论文已经用作在线 GRPO 奖励的证据。作者选择的是 rejection-sampling fine-tuning（filtered behavior cloning）；在线 PPO/RL 是明确列出的未来方向。[P, §4.1、§4.2、§5.1、§6][PH]

## 3. 数据与环境的生产、分布和开放资产

### 3.1 从仓库到可执行任务的漏斗

| 阶段 | 数量／单位 | 原文方法 | 关键缺口／成本 | 定位 |
| --- | --- | --- | --- | --- |
| 仓库筛选 | 358 个 Python 仓库 | SEART；仓库创建早于 2022-07-01，>500 stars、至少 300 LOC、>500 PR、100 contributors | 这是仓库创建时间，不是任务统一截止日期 | §3.1 p.4 |
| Raw | 64,689 个 issue/PR 实例 | SWE-Bench extraction，取得题面、仓库快照、解法和测试相关材料 | 无可执行环境保证，也无测试有效性保证 | §3.1 pp.4–5 |
| 重点建设 | 11 个实例较多的仓库 | 先按代码版本分组，利用 pyproject、tag、脚本等半自动识别版本 | 没有给这 11 仓实际尝试构建的完整任务分母 | §3.1 |
| 环境安装 | 半人工逐版本配置 | 查当时 requirements、CI、文档，处理历史依赖 | 约 200 人工小时、10,000 CPU core-hours；分别是作者报告值 | §3.1 p.5 |
| Full | 2,438 个经测试验证的任务 | gold patch 比原始代码通过更多测试，过滤失败实例 | 不能据 2438/64689 宣称“环境构建成功率”；中间分母未给 | §3.1 |
| 镜像发布 | 逐实例预构建镜像 | 论文报告总计约 6 TB | 未分压缩／展开、共享层／重复存储；不是完整项目费用 | §3.1 |
| Lite | 230 个任务 | 沿用 SWE-Bench Lite 过滤原则 | 不是按目标 30B-A3B policy 通过率选择 | §3.2 |

**Lite 规则：**排除需编辑多个文件、描述不佳、gold diff 过复杂，以及主要测试错误消息的任务。它是方便快速迭代的**训练子集**，不是额外的未见评测集。规则减少某些结构复杂度，却不能保证在当前模型、harness、上下文和工具预算下容易。[P, §3.2][P5]

作者称 11 个仓库与 SWE-Bench 仓库分离，以减少污染。这支持两个数据集在作者构造时的仓库分离，不证明底座预训练没见过 issue／patch，也不证明运行时 git 历史、网络或镜像中不存在未来信息。[P, §3][P4]

### 3.2 Full 与 Lite 不是同分布缩小

下表逐项转录 Fig.2 数量，合计分别为 2438 和 230；大小写沿用仓库身份。

| 仓库 | Full | Lite |
| --- | ---: | ---: |
| pandas-dev/pandas | 737 | 5 |
| Project-MONAI/MONAI | 374 | 27 |
| getmoto/moto | 343 | 59 |
| python/mypy | 257 | 40 |
| iterative/dvc | 225 | 36 |
| dask/dask | 145 | 14 |
| modin-project/modin | 107 | 5 |
| pydantic/pydantic | 83 | 20 |
| conan-io/conan | 75 | 12 |
| facebookresearch/hydra | 66 | 11 |
| bokeh/bokeh | 26 | 1 |
| **合计** | **2,438** | **230** |

来源：[P, Fig.2, p.4][P4]。据此计算，pandas 从 Full 约 30.2% 降到 Lite 约 2.2%，moto 从约 14.1% 升至 25.7%。因此“在 Lite 上收益如何”不能不附条件地代表 Full。论文认为 SWE-Gym 平均更难，依据是 gold patch 统计和特定模型／harness 的较低表现，而不是通用难度常数。

### 3.3 任务统计：括号内是 SWE-Bench 对应测试集

| 指标（除数量外均为均值） | SWE-Gym Full（SWE-Bench Full） | SWE-Gym Lite（SWE-Bench Lite） |
| --- | ---: | ---: |
| 实例数 | 2438（2294） | 230（300） |
| 仓库数 | 11（12） | 11（12） |
| 题面词数 | 239.8（195.1） | 186.2（175.9） |
| 非测试文件数 | 971.2（2944.2） | 818.8（2988.5） |
| 非测试 LOC | 340675.0（363728.4） | 340626.2（377562.4） |
| gold 编辑行数 | 69.8（32.8） | 10.6（10.1） |
| gold 编辑文件数 | 2.5（1.7） | 1.0（1.0） |
| gold 编辑函数数 | 4.1（3.0） | 1.4（1.34） |
| F2P 测试数 | 10.0（9.0） | 2.04（3.5） |
| 测试总数 | 760.8（132.5） | 99.9（85.2） |

来源：[P, Table 2, p.4][P4]。**测试数不是独立语义约束数**，也不是每次执行的恒定成本；参数化测试、资源依赖、被选择的测试文件和版本都会影响实际运行。

### 3.4 OpenHands 教师轨迹：491 条、294 道题，和完整任务池不同

原文取得 **491 条成功轨迹**，来自 `gpt-4o-2024-08-06` 与 `claude-3-5-sonnet-20241022`。这只覆盖 **294 个不同实例**。成功轨迹平均约 19 turns、18,578.5 tokens；Table 8 的 messages 均值 39.9，不能把 messages 当作 agent turns。[P, §4.2、B.2、Tables 7–8][P14]

| 仓库 | 全部成功轨迹 | 按 instance 去重 |
| --- | ---: | ---: |
| moto | 155 | 72 |
| MONAI | 95 | 53 |
| pandas | 70 | 61 |
| mypy | 46 | 27 |
| dask | 45 | 29 |
| dvc | 36 | 24 |
| conan | 20 | 12 |
| pydantic | 11 | 7 |
| hydra | 7 | 5 |
| bokeh | 3 | 2 |
| modin | 3 | 2 |
| **合计** | **491** | **294** |

**Table 10 的采样批次**如下。表中 4o 指上述日期版，Sonnet 同理；D1、D2 是累计轨迹集，不是在线策略版本。

| 批次增量 | 数据 | 温度 | 最大轮数 | 成功轨迹 |
| --- | --- | ---: | ---: | ---: |
| D0 | Lite，4o | 0 | 30 | 19 |
| D1−D0 | Lite，4o | 0.2 / 0.3 / 0.4 / 0.5 / 0.8 | 30 | 11 / 17 / 21 / 18 / 20 |
| D2−D1 | Lite，4o | 0 | 50 | 19 |
| D2−D1 | Lite，Sonnet | 0 | 50 | 67 |
| D2−D1 | Full，4o | 0 | 50 | 111* |
| D2−D1 | Full，4o | 1 | 50 | 188 |

*111 对应的运行受到基础设施问题影响，原文提醒可能低估；不据此比较模型固有能力。以上成功数合计 491。按每行任务数粗算名义调度量为 6716，而 Table 8 统计 491 成功+5557 失败=6048。原文没有提供完整 attempt 账本，**不能把差额 668 自动归为超时、重试或环境损坏**。[P, B.4、Table 10, pp.15–16][P16]

Table 8 用 Qwen2.5-Coder-7B tokenizer 统计：成功 token 中位数 15999，p90 31632，p95 39512.5，最大 81245；失败均值 17218.3，最大 167834。故原始轨迹含明显超过 32K 的实例；训练配置 max length=32768 不代表这些完整长轨迹都无截断进入 loss。裁剪、丢弃、打包后的实际 token 总账未披露，当前代码事实另见 §7.7。

### 3.5 可消费资产不应混为一个“数据集”

| 资产 | 本次实际确认 | 能做什么／还缺什么 |
| --- | --- | --- |
| [SWE-Gym Full][HFfull]、[Lite][HFlite]、[Raw][HFraw] | 官方 README 与原文提供入口；Lite 网页显示 train 230 行、11 个 repo 类、patch/test_patch/F2P/P2P 等字段 | Full/Lite 是环境任务；Raw 不是已验证环境。未独立下载全量 parquet |
| [OpenHands-SFT-Trajectories][HFsft] | 页面显示 `train.success.oss`，491 行，messages 列，MIT 标签 | 是成功示范；不能将其行数当成唯一任务数或在线 RL 样本 |
| [OpenHands-Verifier-Trajectories][HForm] | 页面显示三个 split、`train.mixture` 约 2.64K 行，总计 5272 行，messages+resolved | 三个 split 包含不同混合方案；总行数不等于 5272 条独立训练轨迹，本文没有检查跨 split 去重 |
| [Codebase-Index-Lite][HFindex] | [Moatless 复现指南][Gmoatless]指向 SWE-Gym Lite/SWE-Bench Lite 索引 | 检索资产，不是 gold/no-op 环境验证证据；未下载索引 |
| [SWE-Gym 模型组织页][HForg] | 官方论文／README 公开 policy/verifier 入口 | 本轮没有下载权重、冻结模型 revision 或评测 checkpoint |
| Docker Hub `xingyaoww/sweb.eval.x86_64.*` | 官方 README 登记预建镜像 | 未在本线程 pull。镜像存在、digest 已解析、实际能稳定评分是三个不同状态 |

本次 HF 固定 revision API 访问失败；Lite 网页的 230 与 B 记录的 `f70b1a29…` 230 行吻合，但网页预览不能证明二者逐字节相同。[官方 README][Greadme] 的 234 与论文／可见数据页的 230 不一致，保留为版本／描述差异，不擅改任一来源。数据卡许可标签只代表该资产声明，不替原仓库内容、镜像依赖、教师输出条款或模型许可做统一判定。

<a id="training"></a>
## 4. 后训练阶段、目标、数据身份和预算

### 4.1 OpenHands：教师成功轨迹微调，及一次失败的自产扩充

```text
Qwen2.5-Coder-Instruct 7B / 14B / 32B
    └─ 491 条教师成功轨迹 → full-parameter SFT → OpenHands policy

fine-tuned 32B → 每个 SWE-Gym 实例采样 6 条、t=0.5
    └─ 868 条成功轨迹 + 上述 491 条教师轨迹
        └─ 原文写“fine-tune the base 32B model” → Lite 表现下降
```

这不是“先教师 OPD，再在线 PPO”。自采样发生在一轮训练后，再进行监督微调；原文称 on-policy 是相对于采样 policy 的来源，**没有 likelihood ratio、GRPO advantage、critic 或逐步 RL update**。第二分支也不能擅写成从第一分支 optimizer checkpoint 继续训练，因为原文措辞是 base model。[P, §4.1–4.2][P5]

论文披露 OpenHands **CodeActAgent 2.1**，有 bash 和文件编辑器、禁用浏览器；模型自主规划。全参数 torchtune，lr=1e-4、最多 5 epochs、batch=8、context=32768；Modal 使用 2–8 张 H100 80GB。评测通常温度 0，最多 100 turns 或 32K context。采样阶段的 30/50 turns 与评测的 100 turns 分开；工具超时、环境评分超时不在这个 turn 数内。[P, B.2, pp.13–15][P15]

**关键负结果：**加入 868 条自产成功轨迹后，32B 的 SWE-Bench Lite resolution **15.3%→8.7%**。作者只提出更高级优化方法或更强模型可能改善；没有证明退化唯一由 on-policy 数据、数量、分布或 SFT 本身导致。它不能支持“更多成功数据必然更好”，也不能支持“所有自产数据都会伤害”。[P, §4.2 p.6][P6]

### 4.2 MoatlessTools：限制工作流后进行小规模自改进

每次从 Lite230 每题采样 **30 条，t=1**，保留成功数据，并用累计成功数据微调，做两个迭代；再增加迭代收益有限。为避免容易任务提供过多重复成功轨迹，每题最多保留两条，优先保留 model response rounds 较少的轨迹。这是成功数据策展，不是动态调整环境难度的 RL curriculum。[P, §4.3、B.3][P6]

| 角色 | 原文模型／训练方式 | 训练设置 |
| --- | --- | --- |
| Moatless 7B policy | Qwen2.5-Coder-Instruct，全参数 torchtune | 4×H100，lr=2e-5，batch=8，5 epochs，max sequence=10240 |
| Moatless 32B policy | Qwen2.5-Coder-Instruct，Unsloth LoRA | 1×H100，rank64，lr=5e-4，batch=8，5 epochs，max sequence=10240 |
| 7B/32B verifier | 主文写使用 LoRA；来自第二轮自产轨迹 | 成功每题 cap2，失败下采样至同数；B.3 写其余配置同 agent |

主文对 verifier 的 LoRA 描述与 B.3 对 7B policy 全参、verifier“同配置”的简写不够精确，不能据此断言 verifier 7B 也必然全参。推理使用 SGLang、FP8；作者说精度影响很小，但本篇没有完整 FP8/BF16 同条件消融。以上不是把现有 30B-A3B 显存成本直接换算成 32B dense 的依据。[P, B.3 p.15][P15]

### 4.3 Learned verifier：执行标签的监督学习，不是执行真值本身

OpenHands ORM 读取 task 与 action-observation 轨迹，训练预测成功/失败。数据包括 **443 条教师成功、875 条 fine-tuned policy 成功，共1318成功，配1318失败**；仅保留不超过32K的轨迹。这里的 **875 与 §4.2 的868 不同**，原文未解释来源差异，不能强行合并。主要 ORM 为 Qwen2.5-Coder-Instruct-32B，LoRA/Unsloth，最多2epochs；另外做全参数训练和来源混合消融。[P, §5.1.1, pp.6–7][P7]

模型对二元标签的分数按原文公式归一化：

$$
r=\frac{\exp(l_{\mathrm{yes}})}{\exp(l_{\mathrm{yes}})+\exp(l_{\mathrm{no}})}.
$$

这里 $l$ 是对应判断标签的 logits；它是模型给候选排序的分数，不自动是校准过的真实成功概率。原文文字使用 `<YES>/<NO>`，B.6 的实际回复模板为 `<judgement>YES</judgement>` 或 NO；B.5 的 Moatless prompt 用 True/False。不能假定不同模板是同一 tokenizer 的同一特殊 token，或者把整段回复概率直接当成单标签 logits。[P, §5.1.1、B.5–B.6][P17]

**Moatless ORM 输入**不是 OpenHands 式完整交错轨迹，而是 issue、agent 自己定位得到的相关文件片段、补丁，以及修改前后上下文。B.5 列出格式和一致性检查要求。不能把参考方法使用的强模型生成上下文自动加入本篇；作者说明使用 agent 自己的 context。[P, §5.1.2、B.5][P16]

**OpenHands ORM prompt**要求检查主要目标、边界情况、错误处理和完成验证；输入是轨迹文本，训练目标为判断。它不能读取这个实例的 hidden unit-test verdict 再声称完成无执行验证；本轮未对全部发布轨迹做信息泄漏审计。两类 ORM 在推理时都是候选选择器，而不是在本篇中替代执行评分器给在线 RL 发 reward。

### 4.4 哪些训练语义没有被论文披露

原文没有给 policy SFT 或 ORM 的完整逐 token loss 分母、长轨迹切分／截断合同、packed 多样本权重、所有模板版本和每个实验 checkpoint 选择记录。也没有 fully-async learner、staleness、partial rollout、MoE routing、KL penalty 或 token-level importance correction 的实际实验。

后面的训练代码可以补“公开示例如何配置”，不能补“论文必然这样训练”。尤其本项目现有 GRPO 的整组消费和坏样本处理，不是由这篇过滤式 SFT 自然规定的。

## 5. 效果、消融、推理扩展和失败结果

### 5.1 OpenHands：同一 scaffold 内的 policy 对照

Table 3 使用 SWE-Bench Lite300／Verified500，Qwen2.5-Coder-Instruct 为底座。以下是 zero-shot→fine-tuned；百分比均为原表值。[P, Table 3, p.6][P6]

| 测试集／模型 | Empty patch % | Stuck in loop % | 平均 turns | Resolution %（原表 ±） |
| --- | ---: | ---: | ---: | --- |
| Lite / 7B | 40.3→29.7 | 47.0→31.0 | 20.3→22.2 | 1.0±1.0 → 10.0±2.4 |
| Lite / 14B | 49.7→18.1 | 31.7→27.1 | 23.2→21.4 | 2.7±1.9 → 12.7±2.3 |
| Lite / 32B | 27.0→18.1 | 16.7→18.1 | 15.5→29.3 | 3.0±1.4 → 15.3±2.5 |
| Verified / 7B | 45.8→33.8 | 39.6→21.0 | 21.9→35.3 | 1.8±1.1 → 10.6±2.1 |
| Verified / 14B | 44.9→14.5 | 32.1→21.3 | 25.5→30.1 | 4.0±1.6 → 16.4±2.0 |
| Verified / 32B | 9.5→13.8 | 29.4→23.8 | 24.6→31.6 | 7.0±1.3 → 20.6±2.1 |

Loop 指连续三次同动作。训练后并非每项行为都改善：32B Lite loop 增加，32B Verified empty patch 增加，很多平均 turns 更长。因此不能概括为“微调同时减少所有循环、空补丁和调用成本”。原表的 ± 未明确交代为多少独立训练种子的标准差或某种置信区间；B.1 的子集重采样定义不能未经说明套到所有表值。

### 5.2 Moatless：强工作流起点与有限自提升

| 模型 | zero-shot：empty / resolution | 第1轮：empty / resolution | 第2轮：empty / resolution |
| --- | --- | --- | --- |
| 7B | 56.3 / 7.0 | 29.0 / 9.0 | 23.3 / 10.0 |
| 32B | 24.3 / 19.0 | 18.3 / 19.7 | 9.7 / 19.7 |

来源：[P, Table 4, p.6][P6]，测试 Lite，通常 t=0。32B 之后主要是空补丁下降，而非 resolution 持续上升；减少空补丁不是模型必然解决更多问题的充分条件。

Table 6 的7B轨迹 cap 消融：

| 每题 cap | 训练轨迹数 | Empty % | Resolution % |
| --- | ---: | ---: | ---: |
| 无训练 | 0 | 56.3 | 7.0 |
| 1 | 36 | 37.3 | 9.0 |
| 2 | 62 | 29.0 | 9.7 |
| 3 | 82 | 43.7 | 7.7 |
| 全保留 | 172 | 30.7 | 9.3 |

来源：[P, Table 6, p.13][P13]。cap2 略优于全保留，但同时改变了数据数量和组成，不是等 token 控制变量实验；300题上0.4pp差距不能不带不确定性放大。Table 4 第1轮9.0与Table6 cap2的9.7不完全一致，原文未将二者配置逐项对齐，本文不擅自选一个替换另一个。

### 5.3 Pass@N 是可解上界，Best@N 是实际排序结果

OpenHands-32B+ORM 在 Verified 上：[P, Fig.3, p.7][P7]

| 候选数 | Pass@N：至少一条实际通过 | Best@N：verifier 选中候选后通过 |
| --- | ---: | ---: |
| 1 | 20.6 | 20.6 |
| 8 | 37.8 | 29.8 |
| 16 | 42.8 | 32.0 |

最佳32.0%是多次生成与学习到的排名器组合，**不是单次 policy 成绩20.6%，不是16次全部成功率，也不是不增加推理成本的提升**。本篇没有给包括全部采样和 verifier forward 的端到端费用。

首个 OpenHands hypothesis 使用 t=0，以和单次结果连接，其余 t=0.5。B.1 对 N<M 的统计，是从已有 M 条中随机抽 N 条，重复 **100次子集抽样**估计均值和方差；不是100次新的环境运行，更不是100个训练seed。OpenHands 的 N=1 被单独处理。混合温度也不能不加说明套用同分布独立采样的 Pass@N 理论解释。[P, Fig.1、B.1][P13]

**ORM 训练比较：**LoRA 的 Best@8=29.8，高于全参27.2。作者提出正则化解释，但没有单独证明机制。全参来源混合消融中，on+off-policy 混合约27，纯off-policy约22附近早早平台；增加off-policy负例没有解决主要差距。图8是不同数据组成的比较，不能只称“相同数据下的算法改进”。[P, §5.1.1、Fig.8 p.20][P20]

**Moatless 推理扩展：**32B policy在t=0.5时，Pass@8约33.3；32B verifier 的 Best@8图示26.0，7B verifier约21.0。7B policy的Pass@8约23.3；配7B/32B verifier的Best@8分别13.3/15.0。原文 §5.1.2 写32B组合26.3，而摘要、Table5和图示使用26.0；保留差异。7B verifier 在较大k平台，不能推成任意更大的verifier都单调更好。[P, Fig.4、Fig.7、§5.1.2][P19]

### 5.4 数据缩放：几百条有效示范内的证据，不是永久的“不缺多样性”

三种设置分别是：491轨迹随机取25%/50%/100%；先每个实例留一条的294去重轨迹再随机取；按仓库字母顺序取对应规模。都是 OpenHands SFT／Verified 评测，没有动态RL curriculum。[P, §5.2、Table7、Fig.5/9][P21]

32B 的491轨迹线总体上升；7B后段增幅较小。去重后的随机与仓库顺序线在294总量时接近，491轨迹的最终表现更高。作者解释“当前实例／仓库多样性尚非瓶颈”，这里的条件是当前底座、少量成功轨迹、所选11仓与评测。不能据此给未来30B-A3B真实harness训练取消多样性检查。

还有一个源内差异：文字说仓库顺序取“完整仓库”，但Table7的25%为 MONAI53+conan12+dask6+bokeh2=73；dask去重总数29，故至少一个仓库被截断。50%中moto46也少于去重总数72。表格支持按顺序切到目标数量，不支持每个纳入仓库都完整保留。本文不把这种样本组成改写成更干净的仓库级随机消融。

### 5.5 同时期比较、结论与影响讨论

Appendix A/Table5 将 Lingma-SWE-GPT72B、Nebius72B 与本篇32B结果并列；Table9 是截至2024-12-21的开放权重榜单，使用不同数据、模型与scaffold。它们是历史对照，不是同底座同预算实验，也不能作为当前排名。Table5中的 Lingma Verified30.2与Table9的28.8不同，不强行合并。[P, A、Tables5/9][P16]

作者明确承认语言、仓库和任务类型覆盖有限，建议环境／测试合成；自改进成果仍温和，在线RL是未来方向；单次任务设置缺少人机协作，用户模拟也是未来工作。Impact说明当前产物仍属研究阶段，并讨论生产力、开发者就业、代码归属及恶意代码滥用风险。本文未额外扩展为安全训练配方。[P, §6、Impact, p.9][P9]

## 6. 成本与可复现性：公开资源并不等于可原样重跑

| 成本项 | 一手披露 | 不能推出什么 |
| --- | --- | --- |
| 环境生产 | 约200人工小时、10000 CPU core-hours、6TB镜像 | 不含明确完整API费、采样／训练／评测总费用；未分失败尝试和维护成本 |
| 教师采样 | Table10逐批尝试配置；491成功、294题；一批有infra故障 | 不能把成功条数作为全部API调用分母，也不能由“$1或更多/题”背景句核算全项目 |
| OpenHands SFT | 2–8×H10080GB、最多5epochs、batch8、32K | 无每阶段GPU-hours／墙钟；不是RTX PRO6000预算预测 |
| Moatless | 7B四H100全参，32B单H100 LoRA | 不能与全参32B agentic RL显存／速度直接相比 |
| ORM | 独立训练与Best@N推理，主要LoRA2epochs | 更高Best@N不代表更低成功成本 |
| 开源资产 | 数据、模型、训练脚本、原始fork和镜像入口 | 仍需精确revision、环境包可用性、模板、数据处理和checkpoint选择来复现 |

论文未给基于“环境资格规则开关”的受控训练实验，也未独立验证合法替代解、全面去污染或对抗评分完整性。**本篇最强证据是：可执行真实任务能提供有用的示范和verifier标签，并在特定模型／scaffold上产生训练与推理扩展结果。** 不应升级成“原始评分实现对任意 agent 都可靠”。

<a id="scoring"></a>
## 7. 原始评分路径：从任务行到 `resolved`

这里的“原始”指作者官方仓库所指向的 fork，而非假设当前 PyPI `swebench` 与它等价。原复现文档明确要求使用 SWE-Gym 的 OpenHands fork，并提醒使用最新 OpenHands 可能有明显性能差异。[G, docs/OpenHands.md][Goh]

### 7.1 实际复现入口与三个层次

```text
SWE-Gym/SWE-Gym: docs/OpenHands.md
  → SWE-Gym/OpenHands: scripts/eval-swetrain-full-rollout.sh
  → evaluation/swe_bench/scripts/eval_infer_remote.sh
  → evaluation/swe_bench/eval_infer.py
      → load_swebench_dataset / make_test_spec
      → 新建 runtime，放入 candidate patch 与 eval script
      → 应用 candidate patch，执行测试，取回原始 log
      → swebench.harness.grading.get_eval_report
          → get_logs_eval → repo-specific parser → status map
          → get_eval_tests_report → F2P/P2P ratio → resolved
```

H的`pyproject.toml`评测依赖来自 **`SWE-Gym/SWE-Bench-Fork.git`**，不是普通 PyPI scorer。这里没有核查全部 lockfile，所以不声称 H 在每个历史安装中必然解析为本次F的242429c1。[H, pyproject][Hdep]

独立Docker路径`F/run_evaluation.py`与OpenHands远程路径最终共用`get_eval_report`，但在空补丁、超时和错误报告上有不同外层逻辑。`F/run_validation.py`是环境建设中的gold/empty运行器，使用另一种中间报告；不能只因为都输出`resolved`，就把它当成最终F2P/P2P判分。

### 7.2 任务字段、TestSpec 与环境准备

任务至少需关联`instance_id,repo,base_commit,version,test_patch,FAIL_TO_PASS,PASS_TO_PASS`。公开row同时含`patch`和`hints_text`，加载全部row不意味着应将全部字段暴露给policy。`load_swebench_dataset`支持HF名称和本地JSON/JSONL，但直接HF加载不带revision参数；复现时需由调用方提供固定本地清单或另行冻结。[F, utils.load_swebench_dataset][Futils]

`make_test_spec`将repo和instance_id转成小写，以`(repo,version)`查`MAP_REPO_VERSION_TO_SPECS`，组装三个脚本列表：

| 层 | 主要内容 | 本次看到的实际边界 |
| --- | --- | --- |
| base image | 系统／Conda基础 | 本轮未完整审计所有Docker构建依赖与registry状态 |
| env script | requirements／environment.yml、指定Python、额外pip、env patches | 部分Python版本来自YAML；`python`字段不存在并不证明没有Python环境 |
| repo script | clone、reset到base、安装、pre_install | 通常移除origin，但不是完整历史／网络隔离 |
| eval script | 环境激活、额外eval_commands、候选后重装、恢复／应用测试、执行和清理 | 不只是`eval_cmd + test_files` |

`environment_setup_commit`存在时可用于依赖文件读取，否则用base_commit。镜像键与环境脚本hash、instance_id相关，但源码的`:latest`tag并不自动锁住registry里的字节；项目已有digest冻结是另一层工作。[F, test_spec、utils][Fspec]

**一个重要数据处理边界：**`make_test_spec`对F2P/P2P的JSON解析失败会打印错误并退回空列表，而不是抛出不可用任务异常。结合后面的空分母规则，它可能把坏metadata变成宽松判分。此处是固定源码静态事实；本轮没有发现某个真实任务已触发该分支。

### 7.3 原作者支持哪些仓库、怎样选测试

`F/log_parsers.py`明确含SWE-Gym全部11仓映射。除了pydantic用特殊parser，其余这11仓多数映射到普通`parse_log_pytest`。**本地依赖查不到这些key，不等于原作者未实现它们。**[F, MAP_REPO_TO_PARSER][Fparse]

| 仓库／例子 | 测试命令／准备特点 | parser／接入注意 |
| --- | --- | --- |
| mypy | 版本相关Python3.9–3.12；`pytest [-n0] -rA -k`后接case表达式 | 普通pytest parser；`-k`值来自test_patch，不是路径 |
| moto | `make init`；`pytest -n0 -rA` | 普通pytest summary格式 |
| conan | 编译工具和requirements；eval额外设置`PYTHONPATH`为repo目录 | 只保留test_cmd会漏掉eval_commands |
| dask | 从environment.yml建环境，处理自安装行；`pytest -n0 -rA --color=no` | Python可由YAML决定，不应给None任意补版本 |
| MONAI | 清理requirements中的自仓库Git安装，安装开发依赖 | key最终小写；原row大小写仍需一致映射 |
| dvc | 多版本历史依赖修补；`pytest -rA` | 部分安装子命令带`|| true`，存在spec不等于已成功安装 |
| modin | environment.yml、版本相关numpy/protobuf修补；`pytest -n0 -rA` | 镜像与版本重要，不能用当前最新依赖重建历史任务后假定相同 |
| pydantic | `pdm`/`make install`，`pytest -rA --tb=short -vv -o console_output_style=classic --no-header` | `parse_log_pytest_pydantic`，与普通parser不同 |
| pandas | environment.yml、editable安装、版本相关numpy限制 | pre_install还会添加upstream并fetch tags；“移除origin”不是完整未来历史清理 |
| hydra | Java和开发requirements，旧版本pip/isort修补 | 普通pytest parser；已被本项目当前候选规则排作held-out不改变源实现事实 |
| bokeh | Python与bokehjs依赖随版本变化 | 普通pytest parser；本轮只定点读相关constants，不证明每版本可重建 |

来源：[F, constants.py相关SPECS，约1620行以后][Fconstants]；表是接入注意摘要，不是完整安装脚本。源码还含mne、hypothesis等其他repo映射；**注册表大小不是论文数据集仓库数**。

**普通测试选择。** `get_test_directives`从`test_patch`中的`diff --git a/... b/...`提取目的文件，滤掉常见非测试扩展，得到test命令参数；不是直接将F2P/P2P全部作为pytest nodeid执行。测试集合由test patch与版本spec共同决定，结果再对固定参考case做匹配。[F, utils.get_test_directives][Futils]

**mypy特殊选择。** `make_test_command`在原始`repo`恰为`python/mypy`时，从test_patch提取所有`[case NAME]`，以`or`连接并整体加引号。正则作用于完整diff文字，故新增、删除及上下文中的case都可能被提取；并非只取新增测试名。该特殊分支的repo判断本身区分大小写，与后续lower-map并非同一行为。[F, test_spec.make_test_command][Fspec]

例如隔离文本fixture产生：

```text
pytest -rA -k "old_case or new_case or context_case"
```

这与把`test-data/unit/*.test`拼在`-k`后面不是同一个测试选择。也不能只按测试文件后缀把mypy数据文件排除，然后认为该任务没有测试。

### 7.4 正式候选评分的执行顺序

`run_evaluation.run_instance`新建候选容器，复制候选patch，先`git apply --allow-empty -v`，失败再尝试`patch --batch --fuzz=5 -p1`；这有容错意义，但接受范围不同于严格git apply。需要记录是否用了fallback，不能悄悄改变可接受补丁定义。[F, run_evaluation.run_instance][Feval]

`TestSpec.eval_script`的大致顺序是：

```text
activate testbed / cd /testbed
→ repo-specific eval_commands
→ git safe.directory、status/show/diff（日志）
→ optional install
→ reset test_patch涉及的旧测试文件到base
→ apply official test_patch
→ run repo/version-specific test command
→ reset旧测试文件
```

其中脚本使用 **`set -xo pipefail`而非`set -e`**，原作者注释是为了测试失败后仍能恢复文件。于是最后一个reset成功可能掩盖前面测试命令的非零exit。**最终脚本exit code不能单独作为测试全过的证据。** 本轮用`false; true`的隔离shell执行确认了这一普通shell行为，不等同于运行了SWE镜像。

测试reset列表来自`--- a/...`，对新增文件、重命名与其他控制文件不构成完整覆盖。候选diff执行前后变化在独立runner中仅记录，不作为自动拒绝条件。所谓clean grading应区分“新容器、原始base、官方测试恢复”与“所有评分控制面均不可修改”，这份历史实现没有证明后者。[F, test_spec.make_eval_script_list；run_evaluation][Fspec]

### 7.5 日志解析、测试身份与状态含义

`get_logs_eval`先由**log路径的父目录名**恢复instance_id/repo，再查parser；不是直接消费调用方的`TestSpec.repo`。它通过是否包含某些错误标记和`applied patch`文本决定日志是否可解析，再调用repo parser。单独传输日志时必须保留身份与规定路径；OpenHands wrapper显式建了小写instance目录来兼容这一约定。[F, grading.get_logs_eval；H, eval_infer.process_instance][Fgrading]

这只是历史字符串标记约定，不是加密或强鉴真的结果回执；`found=True`也不保证解析出了全部必需测试。

**普通pytest parser**主要读`PASSED nodeid`／`FAILED nodeid - ...`这样的summary行；它不自动识别所有`nodeid PASSED`形式，不清理所有ANSI，遇到重复test key时后值覆盖前值。`split()`还会截断含空格的参数化测试名。当前HF预览中也能看到一些参考nodeid呈截断形式，因此升级parser时应同时比较参考case的规范化规则，不能只把新日志解析得“更完整”而不处理join键。[F, parse_log_pytest][Fparse]；[HF Lite预览][HFlite]。

**pydantic parser**会清理部分终端控制字符、支持status前后两种方向，额外处理`FAILED [..]`前缀；没有对所有短行做长度检查。`PASSED`单独一行会在隔离fixture中产生IndexError。此证据只说明该函数对这种输入的行为，不说明真实pydantic日志一定有该行。

最终测试状态以F2P/P2P参考集逐项匹配：

| eval status map中的参考case状态 | `test_passed` | `test_failed` | 对分母的实际影响 |
| --- | --- | --- | --- |
| PASSED | 是 | 否 | success+1 |
| XFAIL | 是 | 否 | success+1 |
| FAILED / ERROR | 否 | 是 | failure+1 |
| 完全缺失 | 否 | 是 | failure+1 |
| SKIPPED | 否 | 否 | **不进success也不进failure** |
| 其他未识别但存在的值 | 否 | 通常否 | 可能同样不入分母 |

源码的一条“silent success”注释与实际missing判定不符；以执行分支为准。这里的F2P/P2P都是**发布任务给定的参考类别**：不能每次根据候选结果重建类别，以免目标随候选改变。[F, grading.test_passed/test_failed/get_eval_tests_report][Fgrading]

令 $S_F,F_F,S_P,F_P$ 分别为上述规则收集的成功／失败列表。实际比例为：

$$
q_F=\begin{cases}|S_F|/(|S_F|+|F_F|),& |S_F|+|F_F|>0\\1,&\text{否则}\end{cases},\qquad
q_P=\begin{cases}|S_P|/(|S_P|+|F_P|),& |S_P|+|F_P|>0\\1,&\text{否则}\end{cases}.
$$

`FULL`要求两者均1；`PARTIAL`要求0<qF<1且qP=1；其他为NO。正式`get_eval_report`只把FULL转为`resolved=True`。这不是将所有测试通过比例作为连续训练reward。[F, compute_*、get_resolution_status][Fgrading]

**两个必须分开的边界：**原任务P2P为空时，历史scorer允许其通过，这不意味着有回归保护；参考case存在但全部SKIPPED时，也可能由于实际计数分母归零而FULL，这不等于全部执行通过。

### 7.6 Gold/empty 建设验证与远程wrapper，不能只看一个 `resolved`

**建设验证器 F/run_validation.py。** 它依次提交gold patch与empty patch，允许空patch，分别生成报告。中间报告只收集literal PASSED和FAILED，并在“有PASSED、没有FAILED”时设置`resolved=True`；ERROR、XFAIL、SKIPPED未加入这两个列表。这与最终F2P/P2P判定不同。脚本本身没有完整发布数据的F2P/P2P衍生及过滤账本；本轮未恢复从全部gold/empty原始日志生成最终HF任务行的完整历史作业，不能据此证明最终任务都按这一中间布尔值直接筛选。[F, run_validation.get_validation_report/main][Fvalidation]

**正式独立Docker runner。** 测试超时会抛出EvaluationError并不写正常成功报告；执行与构建异常会清理容器。存在report文件时直接复用，故`run_id/model/instance`缓存路径不是自动包含patch、镜像和scorer版本的幂等键。重复相同运行名不能代替多次fresh-run稳定性验证。[F, run_evaluation][Feval]

**OpenHands远程wrapper H。** [官方full-eval shell][Hwrapper] 经[remote shell][Hshell]选择`RUNTIME=remote`与指定registry；Python wrapper创建一个用于评分的runtime，不复用policy工作区。非字符串／空白patch被规范化为空，**空patch立即设置`empty_generation=True`并返回，根本不运行官方测试**。因此用这个普通候选评测入口得到“empty失败”，不能证明empty控制实验确实执行并命中F2P失败。[H, eval_infer.process_git_patch/process_instance][Heval]

远程wrapper将eval脚本放后台，每30秒轮询，超过1800秒标记`test_timeout=True`并跳出轮询；**随后仍读取现有日志并调用get_eval_report**。静态路径中没有“test_timeout则禁止resolved=True”的互斥条件。如果部分日志已足够满足参考集合，就可能同时出现timeout标志和resolved结果；本轮没有运行真实远程超时实例。B需显式保留这种外层事实，而不能只取最后一个布尔值。

候选patch应用失败、启动测试失败、parser异常分别有flags；`runtime.connect`及一部分准备步骤发生在清理用的try/finally之前，完整资源故障恢复未在本轮审计。脚本总结字段还不含test_timeout。不要把代码记录一个flag等同于全部统计和训练消费都已使用它。[H, eval_infer.py][Heval]

### 7.7 公开训练配置与论文的距离

实际主policy配置为[G, `1116-sonnet-4o-491i-32k-qwen25_coder_32b_full-lr1e-4.yaml`][Gpolicy]：Qwen2.5-Coder-32B-Instruct权重、OpenAI格式messages、`train_on_input:false`、packing、max_seq_len32768、每设备batch1、累积1、5epochs、AdamW lr1e-4/weight_decay0.01、5步warmup、BF16及activation checkpointing。这支持assistant输出监督的配置意图；本轮没有把torchtune内部所有role mask与packing实现逐行审计，不能声称任意tool/assistant边界已完成数值对拍。

配置注释还残留7B样例说明，应以实际组件和checkpoint路径为准。相对于论文“global batch8”，本配置的每设备1还需知道world size才能对齐。

公开verifier脚本[G, train_unsloth_qwen25coder_32b_verifier.py][Gverifier]设单H100、LoRA rank/alpha64、batch1×累积8、2epochs、lr2e-4、max_seq_length默认**10240**、response-only SFT、paged AdamW8bit。入口模型路径写`Qwen2.5-Coder-32B`而非`…-Instruct`，也不同于原文描述。**这两个差异不应被悄悄修成一致：脚本是可复用示例，不是已证明的论文运行lock。** Modal 24h timeout是作业上限，不是训练耗时。

### 7.8 本轮执行的隔离CPU见证

本地按固定源码的条件、循环与分母逻辑转写小fixture，实际运行parser例子和shell例子；不是安装完整fork、不是Docker评分、不是所有真实任务的重放。可运行代码、实际输出和范围在 [自查记录](reviews/O04_self_check_20260908.md)。

| 输入／检查 | 观察到的结果 | 解释边界 |
| --- | --- | --- |
| 非空F2P/P2P参考，status全PASSED | FULL，两个分母均1 | 正常对照 |
| 同样参考，status map完全空 | NO，缺失计入failure | 不能泛称“空日志必通过” |
| 同样参考，status全SKIPPED | FULL，两个分母均0 | 证明函数边界，不证明真实任务触发频率 |
| 同样参考，status全XFAIL | FULL | 历史接受规则，不等于本项目必须接受 |
| F2P=PASSED、P2P为空 | FULL | 无P2P维护证据 |
| 两个参考集都空 | FULL | 与坏metadata退回空集组合时需警惕；外层日志仍有其他前提 |
| F2P部分PASSED部分SKIPPED | FULL，分母仅保留PASSED | skip不只在全skip时影响判定 |
| validation中有PASSED和ERROR、无FAILED | 中间resolved为True | 与最终评分的ERROR失败不同 |
| 普通parser：只给`nodeid PASSED`或ANSI前缀 | 空map | 正式命令的summary与颜色设置是合同的一部分 |
| pydantic：ANSI PASSED，或FAILED前缀附`[gw0]` | 对应case被正确解析 | 说明特殊parser有实质作用 |
| pydantic：单独`PASSED`行 | IndexError | 畸形输入见证，非真实故障频率 |
| 参数名含空格 | 被`split()`截到第一个空格 | 日志与发布参考ID必须一起规范化 |
| mypy patch含旧／新／上下文case | 三者都进入`-k`表达式 | 保留原始命令语义，不简单按新增行提取 |
| `set -xo pipefail; false; true` | 最终exit0 | 脚本最终exit非测试命令exit |

这些结果足以为B提供定点测试，但不意味着应原样继承历史宽松规则。更严格的资格审计可以单列；若改变正式benchmark判分规则，应明确报告差异而非仍冒用原始分数定义。

<a id="limits"></a>
## 8. 矛盾、未披露与未取得：分开记录

| 项目 | 证据状态 | 本文处理 |
| --- | --- | --- |
| Lite230 vs README234 | 原文/当前README/页面描述不一致 | 论文与可见HF230；README234；项目固定230由B盘点支持，不推定多出的4题是什么 |
| 自产868 vs verifier自产875 | 同一论文不同章节数字不同 | 分别附角色与位置，不合并为一个池 |
| Moatless26.3 vs26.0 | 正文与图表/摘要不一致 | 不替作者选定统一成绩 |
| Moatless首轮7B9.0 vs cap2的9.7 | 两表未完整对齐配置 | 不假设两者精确同一训练checkpoint |
| “完整仓库”缩放 vs Table7截断仓库 | 原文描述与表格组成不同 | 以数量说明实际边界，保留作者解释 |
| 6716名义尝试 vs6048长度统计 | 未披露attempt对账 | 不将差额全部归为infra失败 |
| Table3 ± 的统计定义 | 未充分披露 | 不擅写为多seed置信区间；B.1只确定子集重采样 |
| policy/ORM全部loss分母、截断、checkpoint选择 | 未披露完整配方 | 公开配置单列，不填补历史实验 |
| gold/empty日志到正式HF F2P/P2P的完整生成作业 | 本轮未闭合历史链 | 参考集合按发布资产消费；不从validation中间布尔反推全数据质量 |
| 固定HF revision原文与完整parquet | 本轮工具未取得 | 官方页面仅作可访问性证据；不伪称上游未公开 |
| 原始实际镜像可运行性、CPU预算、flakiness | 本轮未执行 | 不宣布216或2438全部有效／无效 |
| 当前scorer、旧fork、远程wrapper的一致性 | 尚需同输入实跑 | 本篇提供差异与测试点，不等同跨实现等价证明 |
| 全面合法替代解、污染、评分隔离 | 论文未给完整审计 | 仓库分离、gold通过、删除origin均不是完整保证 |

<a id="project"></a>
## 9. 对 RepoHarness B 线的建议：先恢复事实，再选任务池

项目映射固定于2026-09-08的B基线。它不是对A/B当前工作树的实时审计，也不修改已讨论的角色分工。[B请求][Brequest]／[B资产盘点][Binventory]。

### 9.1 可以直接反馈给B的三个结论

**第一，当前parser缺口是接入问题，不是SWE-Gym没有原始实现。** B报告`scoring.parse_eval_log → parse_official_eval → swebench 4.1.0`不能覆盖survivor仓库，而项目只vendor了constants。原fork确有全部11仓parser。最小增量应先把选定scorer适配器的spec、命令、parser和判定关联起来，不先淘汰整类题或造通用新评分平台。

**第二，mypy和Conan必须追到完整测试执行合同。** 原mypy使用case表达式；Conan有eval_commands；dask/pandas可从YAML决定Python。把`eval_cmd`与注册表字符串互检正确，仅证明前缀一致，不能证明最终脚本执行了原来的测试。

**第三，gold-pass/no-op-fail要检查有效执行证据，不只检查resolved。** 普通OpenHands评分入口会直接拒绝空patch；历史低层scorer允许skip消失、空参考集真值化；remote timeout可能仍进入日志判分。这些正说明本项目四门需要记录执行、解析和参考覆盖，而不是简单调用一次返回bool的函数。

### 9.2 建议优先做的有限对照

| 检查 | 最小输入 | 应交付什么 |
| --- | --- | --- |
| scorer语义 | 固定合成日志、非空参考F2P/P2P | parser key、缺失／skip／error、实际计数、外层错误的分离测试 |
| mypy命令 | 一道真实task的test_patch、version | 原fork生成命令与本项目命令逐项比较，再在同镜像确认选中的测试集合 |
| 普通pytest/pydantic | 各一类代表任务 | summary/nodeid/参数化规范化，官方参考集合是否完整匹配 |
| Conan或依赖复杂任务 | 固定镜像与版本spec | pre_install/install/eval_commands在何处完成，执行用户与PYTHONPATH是否匹配 |
| empty/gold差分 | 同任务、同grader profile、独立fresh环境 | empty真实触发预期F2P失败；gold通过；将parser错误、setup错误和候选失败分开 |
| 基座学习性 | 已通过环境检查的小批任务 | 当前准确checkpoint+harness+预算的task级成功分布，不借旧Qwen2.5成绩代替 |

若项目采用非root grader，应在相同权限配置下验证gold/empty；原作者root或远程默认运行结果不能自然迁移。普通公共开发测试与评分时才写入的测试材料应分别处理，不能以“隐藏测试”为理由拿走全部正常开发反馈。

### 9.3 哪些事情现在不应提前决定

论文没有证明Lite230或项目216是当前模型最优训练池，也没有证明只要更多成功示范就会继续变好。B记录的216由静态筛选形成、9仓、78个(repo,version)，以及22题P2P为空，是本地盘点事实，不是本轮容器验收。Full→Lite分布变化和OH自改进负结果，已经足够支持一次小批候选比较，但不要求先做自动curriculum。

比较其他来源时，明确任务版本、测试可见性、工具、预算、执行用户和评分身份。**评分不可用应先修；评分有效但模型全错，再考虑更合适题、SFT或反馈；信号足够则先做有限静态训练。** 不应为了“第一篇环境论文很重要”而把完整SWE-Gym生产过程复制一遍。

任务级输出建议至少有：source/revision、repo/base/version、image digest、scorer pin、实际test command、candidate/gold/empty身份、参考case覆盖、原始status map、timeout/parse/setup事实、最终任务结果与分阶段时间。B负责环境与判分依据，A决定这些事实怎样进入训练统计和loss；本笔记不替A规定GRPO组过滤算法。

## 10. 本轮交付与可继续复核的位置

**完成：**v2全部正文与附录、Table1–10、Fig1–9、两个verifier prompt；原作者数据/训练复现入口；固定原fork的test selection、parser、F2P/P2P、gold/empty与正式评分；OpenHands实际远程wrapper；公开SFT/ORM配置；隔离CPU语义见证；针对B的最小接入建议。

**未完成：**真实Docker/RemoteRuntime运行、216任务级对账、原论文模型训练或最终分数复现、完整HF下载、所有Git锁文件与依赖内核审计、独立review。实际检查与可运行fixture详见 [作者自查](reviews/O04_self_check_20260908.md)。本轮工具没有独立子agent审查能力，不标“独立审查通过”。

后续优先复核§7.5–7.6的计数和wrapper行为，以及mypy命令；这比重新读一遍摘要更可能改变B的实施。与[SWE-smith](E5_swe_smith.md)、[R2E-Gym](O03_r2e_gym.md)、[SkyRL-Agent](O01_skyrl_agent_sa_swe.md)的比较应建立在各自版本和实证类型上，不能将后来RL结果归到SWE-Gym原论文。

## 官方来源与项目定位链接

[Pabs]: https://arxiv.org/abs/2412.21139
[P]: https://arxiv.org/pdf/2412.21139v2
[PH]: https://arxiv.org/html/2412.21139v2
[P3]: https://arxiv.org/pdf/2412.21139v2#page=3
[P4]: https://arxiv.org/pdf/2412.21139v2#page=4
[P5]: https://arxiv.org/pdf/2412.21139v2#page=5
[P6]: https://arxiv.org/pdf/2412.21139v2#page=6
[P7]: https://arxiv.org/pdf/2412.21139v2#page=7
[P9]: https://arxiv.org/pdf/2412.21139v2#page=9
[P13]: https://arxiv.org/pdf/2412.21139v2#page=13
[P14]: https://arxiv.org/pdf/2412.21139v2#page=14
[P15]: https://arxiv.org/pdf/2412.21139v2#page=15
[P16]: https://arxiv.org/pdf/2412.21139v2#page=16
[P17]: https://arxiv.org/pdf/2412.21139v2#page=17
[P19]: https://arxiv.org/pdf/2412.21139v2#page=19
[P20]: https://arxiv.org/pdf/2412.21139v2#page=20
[P21]: https://arxiv.org/pdf/2412.21139v2#page=21
[Goh]: https://github.com/SWE-Gym/SWE-Gym/blob/b681068ca20628c6987b7416cc4cf03f06b77ba5/docs/OpenHands.md
[Gmoatless]: https://github.com/SWE-Gym/SWE-Gym/blob/b681068ca20628c6987b7416cc4cf03f06b77ba5/docs/MoatlessTools.md
[Greadme]: https://github.com/SWE-Gym/SWE-Gym/blob/b681068ca20628c6987b7416cc4cf03f06b77ba5/README.md
[Gpolicy]: https://github.com/SWE-Gym/SWE-Gym/blob/b681068ca20628c6987b7416cc4cf03f06b77ba5/scripts/training/openhands/configs/policy/1116-sonnet-4o-491i-32k-qwen25_coder_32b_full-lr1e-4.yaml
[Gverifier]: https://github.com/SWE-Gym/SWE-Gym/blob/b681068ca20628c6987b7416cc4cf03f06b77ba5/scripts/training/openhands/train_unsloth_qwen25coder_32b_verifier.py
[Fspec]: https://github.com/SWE-Gym/SWE-Bench-Fork/blob/242429c188fcfd06aad13fce9a54d450470bf0ac/swebench/harness/test_spec.py
[Fparse]: https://github.com/SWE-Gym/SWE-Bench-Fork/blob/242429c188fcfd06aad13fce9a54d450470bf0ac/swebench/harness/log_parsers.py
[Fgrading]: https://github.com/SWE-Gym/SWE-Bench-Fork/blob/242429c188fcfd06aad13fce9a54d450470bf0ac/swebench/harness/grading.py
[Fvalidation]: https://github.com/SWE-Gym/SWE-Bench-Fork/blob/242429c188fcfd06aad13fce9a54d450470bf0ac/swebench/harness/run_validation.py
[Feval]: https://github.com/SWE-Gym/SWE-Bench-Fork/blob/242429c188fcfd06aad13fce9a54d450470bf0ac/swebench/harness/run_evaluation.py
[Futils]: https://github.com/SWE-Gym/SWE-Bench-Fork/blob/242429c188fcfd06aad13fce9a54d450470bf0ac/swebench/harness/utils.py
[Fconstants]: https://github.com/SWE-Gym/SWE-Bench-Fork/blob/242429c188fcfd06aad13fce9a54d450470bf0ac/swebench/harness/constants.py
[Hdep]: https://github.com/SWE-Gym/OpenHands/blob/e644a2ca45c3623b27a7e6c169e3d479f0a87fbc/pyproject.toml
[Heval]: https://github.com/SWE-Gym/OpenHands/blob/e644a2ca45c3623b27a7e6c169e3d479f0a87fbc/evaluation/swe_bench/eval_infer.py
[Hwrapper]: https://github.com/SWE-Gym/OpenHands/blob/e644a2ca45c3623b27a7e6c169e3d479f0a87fbc/scripts/eval-swetrain-full-rollout.sh
[Hshell]: https://github.com/SWE-Gym/OpenHands/blob/e644a2ca45c3623b27a7e6c169e3d479f0a87fbc/evaluation/swe_bench/scripts/eval_infer_remote.sh
[HFfull]: https://huggingface.co/datasets/SWE-Gym/SWE-Gym
[HFlite]: https://huggingface.co/datasets/SWE-Gym/SWE-Gym-Lite
[HFraw]: https://huggingface.co/datasets/SWE-Gym/SWE-Gym-Raw
[HFsft]: https://huggingface.co/datasets/SWE-Gym/OpenHands-SFT-Trajectories
[HForm]: https://huggingface.co/datasets/SWE-Gym/OpenHands-Verifier-Trajectories
[HFindex]: https://huggingface.co/datasets/SWE-Gym/Codebase-Index-Lite
[HForg]: https://huggingface.co/SWE-Gym
[Brequest]: https://github.com/Rogerffff/RepoHarness/blob/d2df06d49e42b93436d10d1b7a12d4e1f0ae3be5/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/b_external_reading_requests_20260908.md
[Binventory]: https://github.com/Rogerffff/RepoHarness/blob/d2df06d49e42b93436d10d1b7a12d4e1f0ae3be5/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/B_materials_20260908/repo_asset_inventory.md
