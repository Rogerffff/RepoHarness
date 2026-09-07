# E3 Envs-FORGE：来源对账与配套代码检查（全文待补）

**2026-09-07｜状态：全文精读未完成；已完成来源对账和下列官方代码的定点静态检查。不得计入“精读完成”或“独立审查通过”。**

本轮没有取得论文 PDF/HTML/TeX 的可读全文，不能交付与 O01 相同等级的全文笔记。下面只保存本次确实取得的证据及续读入口：当前 arXiv 摘要、仓库旧稿之间存在需要核对的口径；官方关联仓库有 terminal task 合成示例，但该示例的 `accepted` 来自静态检查，Harbor 执行验证另行运行，不能直接当成论文 gold-verified 生产链。**正文、附录、公式、实验表和图均待取得原文后逐项补读；不以旧模型摘要替代。**

导航：[来源与覆盖](#sources) · [当前摘要](#abstract) · [历史口径对账](#reconcile) · [实现数据流](#code) · [续读问题](#pending) · [项目边界](#project)

<a id="sources"></a>
## 1. 来源身份、版本和实际覆盖

### 1.1 主来源尚未闭合

- 文献 ID：**arXiv:2608.14312**。
- 本轮直接检索到的 arXiv 摘要标题：**Envs-FORGE: Frontier-Optimized Reward-Grounded Environment Synthesis for Agent RL**。[P]
- 该检索记录给出的作者：Xiaojun Wu、Cehao Yang、Honghao Liu、Xueyuan Lin、Zhichao Shi、Hao Zhou、Xuhui Jiang、Chengjin Xu、Jia Li、Jian Guo；提交日期 **2026-08-14**。这不是 PDF 首页目视核验，版本历史也尚未读取。[P]
- 项目已登记的原始文件：`docs/harness_improve/external_paper_references/pdfs/E3_envs_forge_2608.14312.pdf`；GitHub 返回的 blob 标识为 `e35ca77aab3738fe4a8732d19f28497540884214`，本轮未取得其二进制内容。[PDF-repo]
- RepoHarness 读取基线：`09b9d68c1803c7bb0c2d1944fcbac2bc5b34f7c6`，分支 `miles-migration`。保存本稿时允许分支因其他阅读线程前进，但不回写其他文件。
- 官方关联仓库：`DataArcTech/DataArc-SynData-Toolkit`。下文只核查 **`SynAgenticData` 分支提交 `2a1d65ec8dcfaea2458d67e1fb18078cce6420b9`** 的指定文件。摘要链接指向仓库，**并未指定这一分支或证明这一提交就是论文实验实现**。

### 1.2 覆盖清单

| 材料 | 实际取得与阅读情况 | 可用于什么结论 |
| --- | --- | --- |
| arXiv 摘要 | 从指向原始 arXiv 页的检索结果读到完整摘要；直接页面打开失败 | 仅支持作者在摘要中的方法与结果声明 |
| PDF 正文、附录、图表 | **未取得** | 不填写页数、章节目录、公式编号、图表读数或全文完成状态 |
| arXiv 版本历史、TeX | **未取得** | 不判断发生了改名、修订或实验更换 |
| 项目原始 PDF 文件 | 确认路径／blob，但连接器未返回可用字节 | 说明有待传入的原始资产，不说明本轮读过 |
| `knowledge/summary_envs_forge_synthesis_policy.md` | 已读全文；自述依据 TeX | 续读提纲和待核对断言，不是本轮一手验证 |
| 关联仓库 `docs/SYN_AGENTIC_DATA.md` | 已读全文 | 该提交的说明与运行入口 |
| `sdgsystem/agentic_data/terminal_bench.py` | 分段读至文件尾 | 该提交的合成、静态验证、导出与独立 Harbor helper 行为 |
| `run_terminal_bench.py`、`run_terminal_bench_harbor_smoke.py`、配置 YAML | 已读全文 | 实际示例入口与调用关系；不是论文历史配方 |
| 运行、模型训练、镜像构建 | **未执行** | 不宣称可运行、实验复现、性能收益或漏洞已实际触发 |

### 1.3 访问问题与缺披露不能混写

arXiv PDF/HTML 多个正常版本入口返回 cache miss；仓库 PDF 经 GitHub 文本接口读取时被拒绝或返回空内容，blob 接口不能解码二进制；容器直连下载不可用，连接器文件物化也未成功。因此当前缺的是**本轮可读取的原文**，不是已经证实“作者没有公开细节”。没有获得 PDF view，故本轮也没有可执行的原文截图核查。

下一次应直接使用上传到会话的该 PDF，或同版本完整 TeX/HTML 与图资源。旧稿可能省略附录、条件和负结果，不能用来填充本表的未读项。

<a id="abstract"></a>
## 2. 当前 arXiv 摘要实际声称什么

**以下全部为摘要级作者报告，尚未回到正文核验。**[P]

方法先用 verifier 通过率刻画 seed，再围绕学习前沿对六个 projection–direction 动作评分，以逐 seed MILP 选择合成动作；动作驱动指令、fixtures、oracle 解、测试与 Docker 环境联合改写，只有 gold-verified 包进入 RL。摘要提到可选的 portfolio 软技能覆盖，但没有给其独立实验。

| 摘要中的实验量 | 当前摘要值 | 尚不能推出 |
| --- | --- | --- |
| 每种合成方法导出量 | **100 个验证环境** | 原始候选量、唯一 seed 数、训练全部任务数 |
| 合成 token | **2.27M–2.88M** | 总 API 费用、校准／训练／评测全成本相同 |
| Qwen 3.5 35B，tb-core | Base **40.0% → 49.2%**；高于最强固定配方 **2.4 pp** | Base 是否未经 RL、benchmark 精确版本和显著性 |
| 同模型，tb-2.0 | **23.0% → 29.4%**；高于最强固定配方 **2.1 pp** | 与其他论文同名基准的协议一致 |
| 同模型，SWE-bench Verified | **73.4% → 77.1%** | 跨仓库独立泛化、未污染或模型整体排名 |

摘要的主张对象是**合成前选择如何改写环境**，不是训练时直接筛选学生 token。它仍不足以恢复 MILP 目标、六动作定义、GRPO/PPO 公式、在线更新频率、数据切分或硬件预算。

<a id="reconcile"></a>
## 3. 必须保留的历史口径差异

本轮读到的项目 `knowledge/` 旧稿标题为 *Frontier-Aware Environment Synthesis for Terminal Agents*，其中已记录 **100 环境、40.0→49.2**，与当前 arXiv 摘要一致；而历史会话曾使用 **1,824 个任务**、Qwen3-Coder/Ling 等另一组模型与增益。另有目录使用 *Verifier-Pass-Rate-Guided Synthesis Policy for Executable Environments* 标题。[OLD]

这些差异尚不能被解释成同一论文的“旧版→新版”，也不能用“可能是不同分母”自动消解。**原始 PDF 首页、版本历史、主实验表和配置尚待核对。** 当前稿只保留有本轮来源的摘要口径，不复写历史会话的未核数字；也没有修改旧稿或共享目录。

旧稿中关于 transfer prior、MILP 约束、2×H800、GRPO 及 1,024-token 单响应限制的详细记录，是很有用的核验目标，但本轮没有一手全文可以确认。因此不把这些数字复制进“已确认训练配方”。

<a id="code"></a>
## 4. 关联官方代码：从真正运行入口追到导出

代码证据固定到上述 `SynAgenticData` commit。它是**相关实现的静态检查**，不是完整仓库审计，更不是已找到 Envs-FORGE 全流程公开实现。

### 4.1 主入口实际做什么

`examples/syn_agentic_data/run_terminal_bench.py::main()` 加载 YAML，建立模型客户端，调用 `run_terminal_bench_synthesis()`，最后打印 `num_accepted/num_records`。[C1]

该合成循环按 task name → strategy → direction → sample index 遍历。策略类型仅列 **few_shot / self_instruct / evol_instruct**；只有 Evol 进一步遍历 **in_depth / in_breadth**。配置给三个 seed task、每策略一个样本，故在没有中途异常的情况下，名义上请求 **3×(1+1+2)=12** 个候选；这是读者按循环计算，不是论文数据量。[C2][C3]

在已读入口与整份 `terminal_bench.py` 中，没有看到 seed pass-rate profiling、六动作评分或 MILP 被调用。**这个局部结论不等于对整仓库、其他分支或未公开代码证明“它不存在”。**

### 4.2 工件同步生成存在，但 accepted 的含义有限

`synthesize_terminal_bench_task()` 让模型生成 JSON 工件包，要求包含 `instruction.md`、`solution/solve.sh`、`tests/test_outputs.py`；环境和 fixtures 可一起修改。随后解析和验证 schema／相对路径，复制 seed 目录、应用修改，调用 `static_validate_materialized_task()`。[C2]

该 static validator 的 `matched=True` 只代表所需路径存在、关键文件非空。它**没有运行 Docker、oracle solution 或测试**。主循环直接依据这个 `matched` 将记录加入 accepted，再写出任务目录、manifest 和 `dataarc_train.jsonl`。[C2]

因此：

> **此示例 `accepted` ≠ 已执行 oracle 并通过测试；不能据它证明摘要中的 gold-verified 合成流程已经复现。**

这不是指控论文没有 gold verification，而是限制当前代码证据的归属。

### 4.3 执行验证是独立脚本，未在主合成路径中自动闭合

`run_terminal_bench_harbor_smoke.py` 从 records 中选一条，调用 `run_harbor_verification()`，并打印结果。[C4]

helper 检查必要环境变量，缺少时返回 `status=skipped`；否则用 `subprocess.run` 执行 Harbor，将 **退出码 0 且读取 reward=1** 判作 matched。默认参数是 agent `codex`、model 字符串 `gpt-5.5`、Docker 和 force-build；这些是示例字面配置，不代表论文中的求解器，也不是对模型可用性的独立核验。[C2][C3]

这个 smoke 入口不把结果自动回写合成 records、不重新生成 accepted 集，也不为全部导出任务实施一次 gold 审查。在已查路径中，**“能另行调用验证”与“导出前必须验证通过”仍是两件事**。[C4]

### 4.4 导出的消息行不是目标 coding agent 的实际求解轨迹

`terminal_bench_record_to_dataarc()` 用模板拼出 instruction、assistant reasoning、一个 `run_harbor_terminal_bench` function call、验证摘要以及结束语。主合成路径的 observation 明确写“静态检查通过、可运行 Harbor”；这个函数本身没有执行该 tool call。[C2]

因此 `messages/tools` 格式存在，不证明已经采集目标模型真实 rollout，更不证明有可用于 on-policy RL 的 action token、行为 logprob 或优势值。示例适合作为工件／接口导出入口，不能直接代替 RepoHarness 的训练轨迹消费链。

代码避免把 solution/test 源码直接嵌入这些消息行，是一个表示层边界；它不自动证明实际容器中隐藏资产不可见。

### 4.5 两个静态检查问题，保留触发条件

**reward 与本次运行身份。** `_read_latest_harbor_reward()` 递归扫描共享 jobs 目录，按文件修改时间取最近的可解析 `reward.txt`。没有在该 helper 中绑定本次 job ID。若复用目录且新运行没有产生可解析 reward，可能读到旧结果；是否实际发生还取决于 Harbor 输出、退出码和调用条件。**本轮没有运行复现，不把它写成已证实误评分。**[C2]

**canary 与数据来源。** `load_seed_task()` 和 `materialize_artifact()` 会删除含 terminal-bench canary 等字符串的行。删去标记只是文本处理，不能证明派生任务与评测集已去重、合法分割或去污染。笔记不建议将该处理用作去污染策略；任务来源与派生关系仍需另行核验。[C2]

### 4.6 能复用什么，尚缺什么

已经看到：任务目录读取、工件生成 prompt、静态路径检查、物化、manifest、消息格式导出，以及单任务 Harbor smoke 接口。

未在本次实际调用链中验证：论文专属选择器、完整 gold/no-op 策略、成功候选冻结、训练样本与 verifier 的绑定、论文实验配置、checkpoint、按论文切分的评测入口。**“未验证”不等于作者必然没有实现；当前不能给整套方法打上可一键复现的标签。**

<a id="pending"></a>
## 5. 取得原文后按这些问题续读

以下是待核验事项，不是对论文内容的断言。第一步必须先恢复真实目录、页数、图表与附录，再决定章节覆盖；不能把此表当作论文目录。

| 问题 | 需要回原文查什么 |
| --- | --- |
| 文献身份与历史口径 | PDF 首页、arXiv revision、实验量与模型名；核对 100 与历史 1,824 的来源 |
| 六动作与选择器 | projection–direction 的准确枚举、目标函数、变量、约束；per-seed 与 portfolio 模式区别 |
| prior 与 frontier | 通过率采样预算、平滑方式、transfer prior 的来源及敏感性；分数是否仅是排序启发式 |
| 闭环程度 | 合成前一次性 profile，还是训练中持续重新估计；学生、求解器、生成器各自是否更新 |
| 工件与验证 | 五件套如何同步，静态／构建／oracle／no-op 检查顺序，失败重试与合法替代解 |
| 数据与污染 | seed 来源、accepted 数与实际训练题数、train/dev/test、派生任务分割、重叠检查 |
| 训练方法 | SFT/RL 的实际阶段，reward、loss、group、mask、normalization、终止、staleness 和硬件 |
| 对照与统计 | Base 含义；任务数、生成成本、rollout 与更新预算是否匹配；是否有选择器单因素对照 |
| 全部结果 | tb-core/tb-2.0/SWE 的具体协议、表图数值、方差、失败案例及能力回退 |
| 全成本与开放资产 | 校准、生成修复、环境验证、训练及评测成本；公开分支／脚本与实验 revision 的关系 |

原文若未披露，需要注明检查了哪些章节；原文未取得则继续标“待读取”，不能改成“未披露”。

<a id="project"></a>
## 6. 对项目一仅保留两条条件化意义

**方法候选。** 摘要让“合成前决定如何改写 seed”成为值得比较的候选，但尚不足以支持项目必须建设在线 curriculum、MILP 平台或出题模型。需要原文确认它究竟比简单固定配方多控制了什么。

**工程证据。** 当前代码示例说明，任务结构完整、可以启动验证、验证确实成功、验证结果绑定到被导出的任务，以及轨迹可用于某种训练目标，不能用一个 `accepted` 字段替代。这是本轮定点检查的启示，不是 Envs-FORGE 的已复现模型收益。

本轮不变更 RepoHarness 实现、算法命名、任务集、共享索引或实施定案。完整论文结论待原文补齐后追加；[本轮作者自查与续读记录](reviews/E3_envs_forge_self_check_20260907.md)保存范围与限制。

## 来源定位

[P]: https://arxiv.org/abs/2608.14312
[PDF-repo]: https://github.com/Rogerffff/RepoHarness/blob/09b9d68c1803c7bb0c2d1944fcbac2bc5b34f7c6/docs/harness_improve/external_paper_references/pdfs/E3_envs_forge_2608.14312.pdf
[OLD]: https://github.com/Rogerffff/RepoHarness/blob/09b9d68c1803c7bb0c2d1944fcbac2bc5b34f7c6/knowledge/summary_envs_forge_synthesis_policy.md
[C0]: https://github.com/DataArcTech/DataArc-SynData-Toolkit/blob/2a1d65ec8dcfaea2458d67e1fb18078cce6420b9/docs/SYN_AGENTIC_DATA.md
[C1]: https://github.com/DataArcTech/DataArc-SynData-Toolkit/blob/2a1d65ec8dcfaea2458d67e1fb18078cce6420b9/examples/syn_agentic_data/run_terminal_bench.py
[C2]: https://github.com/DataArcTech/DataArc-SynData-Toolkit/blob/2a1d65ec8dcfaea2458d67e1fb18078cce6420b9/sdgsystem/agentic_data/terminal_bench.py
[C3]: https://github.com/DataArcTech/DataArc-SynData-Toolkit/blob/2a1d65ec8dcfaea2458d67e1fb18078cce6420b9/configs/syn_agentic_terminal_bench.yaml
[C4]: https://github.com/DataArcTech/DataArc-SynData-Toolkit/blob/2a1d65ec8dcfaea2458d67e1fb18078cce6420b9/examples/syn_agentic_data/run_terminal_bench_harbor_smoke.py
