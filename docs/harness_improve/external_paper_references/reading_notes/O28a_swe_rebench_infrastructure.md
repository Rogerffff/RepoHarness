# O28a SWE-rebench 运维：可执行数据、环境生命周期与评分后端

这篇材料的用途是解释 SWE 实验如何运行、失败和扩展，不是提供一个新的 RL 配方。本笔记将原文的短事实摘记、配套实现核查和读者分析分层保存：后两者不能倒填历史实验。对项目一最直接的价值，是确定环境与评分需要保存哪些事实、如何辨认未完成结果，以及怎样在扩大并发前测量真实瓶颈；它不构成采用某个云平台的批准。

导航：[来源与覆盖](#source) · [原文事实与数字](#facts) · [配套实现](#implementation) · [方法分析](#analysis) · [B 线消费建议](#mapping) · [检查状态](#review)

<a id="source"></a>
## 1. 来源、版本与阅读范围

**A：官方运维文章。** Karasik et al.，Nebius，*Behind SWE-rebench: Infrastructure to collect massive datasets of SWE tasks and evaluate agents at scale*，**2025-11-07**。[原文][A]。阅读日期 **2026-09-08**。正文、伪代码、贡献者、引用及结尾的开放资产说明均已读；这是网页，不存在论文页码或技术附录。以原文小标题及段落主题定位。顶部装饰图片未成功取得；已取得正文未出现依赖该图的技术表格。未阅读全文所链接的其他论文、产品文档或促销页面。

**C：官方配套实现。** `SWE-rebench/SWE-bench-fork@e4907b7a90eafaa1f0a6428fd04fe31cdd8b4284`，提交日期 **2026-06-03**。只检查下列文件及函数，不审整个仓库：

| 标记 | 文件／符号 | 检查范围 |
| --- | --- | --- |
| [C0][C0] | 根 `README.md` | fork 入口、数据与镜像示例、Tracto 后端说明 |
| [C1][C1] | `swebench/harness/tracto_eval/README.md` | 完整部署、镜像导入和评测命令 |
| [C2][C2] | `swebench/harness/tracto_eval/run_evaluation_tracto.py` | 全文；输入输出、Podman、mapper、跳过及汇总路径 |
| [C3][C3] | `swebench/harness/run_evaluation.py` | 约 L200 至文件末尾；筛选、后端选择和 CLI 默认值 |

这个代码提交晚于文章，**未证明它就是 2025 年性能实验的 revision**。本次没有启动 Docker/Podman、登录 Tracto、导入镜像或运行评分；所有实现发现都是静态阅读。

**项目读取基线：** `Rogerffff/RepoHarness@miles-migration@d2df06d49e42b93436d10d1b7a12d4e1f0ae3be5`。按 [B 派工说明][B-request] 只维护本篇及自己的自查记录。与 [O28b 原演讲](O28b_swe_rebench_evaluation_lessons.md)、[O11 V2 论文](O11_swe_rebench_v2.md) 互相链接，不重做 O11。旧索引将运维文和二手演讲整理并排；它仅用作待核说法的入口。

### 1.1 按原文顺序的覆盖索引

| 原文小标题／位置 | 范围 | 本篇承接 |
| --- | --- | --- |
| 开头、SWE agents and their evaluation | 正文与全部伪代码 | §2、§4.1 |
| Research ideas face the single-host limit | 全读 | §4.2 |
| Treating codebases as executable data | 全读 | §4.2 |
| Building upon a robust stack | 全读 | §2、§4.2 |
| Using Kubernetes / Being in charge of the pods | 六项经验全部读 | §4.3–4.4 |
| Using TractoAI / Mining SWE tasks | 四阶段与三项困难全部读 | §2、§4.2 |
| Evaluation of agent solutions / Kubernetes vs. TractoAI | 三版后端及比较全部读 | §3–4 |
| Sharing our infrastructure | 资产、假设、运行数字全部读 | §2–3 |
| Research credits / Contributors / Citation / References | 核验身份和来源关系 | 本节；不作为价格或服务承诺 |

<a id="facts"></a>
## 2. 原文事实摘记：不要把这一页当作训练报告

**作者描述的结构：** agent 在工作容器产生补丁，另建测试容器评分；伪代码先应用测试补丁，再应用候选补丁。运行用 Kubernetes，数据生产、镜像、评分与工件用 TractoAI。任务生产经采集、处理、执行验证、镜像发布；Pod 管理重点是状态超时、归属、清理、整题重试、监控和资源配置。评分后端经历 Volcano、Tracto vanilla、Tracto map＋Podman 三次组织方式。[A，evaluation / scaling / Kubernetes / TractoAI 各节][A]

| 作者报告值 | 分母或对象 | 原文位置 |
| --- | --- | --- |
| 约 21 TB；32K 仓库／1 TB | Archive 未压缩数据；完整仓库历史 | Mining，第 1 项 |
| 约 153K → 21K | 候选 → 执行验证后的任务 | Mining，第 2–3 项 |
| 最多 8,000 | 同时运行的 agent Pods | Using Kubernetes |
| 4 CPU / 16 GB | Pod limits 的示例 | Being in charge，第 6 项 |
| 5+ 次／题 | agent 尝试次数 | Evaluation |
| 21.3K；6.38K；80K | SWE-rebench 任务；SWE-bench-extra 任务；agent 轨迹 | Sharing |
| 500 个，约 18 分钟 | 已生成补丁的 Verified 评分；依赖集群负载 | Sharing |

**其他机制定位：** Mining 的三项困难对应 tmpfs、Buildah/VFS 与内部制品镜像；Evaluation 的 vanilla 阶段说明每个 operation 的 100-task 限制；Sharing 明确其 **2025-09-28** 接口假设已有任务镜像。[A][A]

本篇未披露具体模型训练的 loss、组统计、token mask、教师、超参数和训练曲线。它提到下游训练与推理搜索的用途，**不能据此生成一份 GRPO、OPD 或 fully-async learner 配方**。产品信用额度也不是本项目可使用预算。

<a id="implementation"></a>
## 3. 配套代码核查：从命令到评分产物

以下均为 **C 提交的实现事实**，不是文章历史运行的补全。

### 3.1 三种对象与一条调用链

执行需要区分：**评测 runner 的镜像、每个任务的预建镜像、待评分的候选补丁**。C1 给出 runner 构建与第三方任务镜像导入步骤；导入 registry 是资产搬运，不等于创建新任务或重复执行 gold/no-op 验证。

静态路径为：

```text
run_evaluation.main
  → 载入 predictions 和任务
  → --tracto 分支
  → run_instances_tracto
  → TestInput 行 / input table
  → yt.run_map(RunInstanceTracto)
  → Podman API + 原 run_instance
  → TestOutput 行
  → 回写本地日志与 report
  → make_run_report
```

C2 的 `TestInput` 包含 instance、test spec、prediction、run ID 与 timeout；`TestOutput` 分开保存测试输出、report JSON、实例日志、补丁、异常标志，以及 operation/job ID。**`errored=False` 只表示这层没有捕获到异常，不能替代 report 中的 resolved，也不保证四种文件全部存在。** `_maybe_read_text` 允许返回空值。[C2，两个 Pydantic 类、RunInstanceTracto][C2]

### 3.2 一个可以明确核实的文档问题

C1 文字要求增加 `--tracto yes`，但该页的 **Run evaluation using Tracto** 命令块没有这个参数。C3 的 argparse 默认 `tracto=False`，实际选择也只看该布尔值；仅设置 `TRACTO_EVAL_IMAGE` 等环境变量不会切换后端。[C1][C1]、[C3，main / CLI][C3]

因此，**按那个命令块原样执行，不会选中 Tracto 分支**。这是固定提交的文档—实现不一致；本轮没有运行这条命令，也不据此断言作者自己的实验跑错后端。正式提 issue/PR 前还需检查上游最新版本和已有修复，本轮没有对外提交。

### 3.3 “已有目录”与“已经成功产出评分”是不同条件

C3 的上层筛选以 `report.json` 存在来识别已完成实例；C2 内部却在 `run_instances_tracto` 中使用 **`log_dir.exists()` 就跳过**。如果一次失败留下目录但没有 report，上层可能把任务保留下来，后端又将其跳过。[C3，get_dataset_from_preds 尾部][C3]、[C2，run_test_specs 构造][C2]

这是一个具体的**条件性静态风险**：需要验证失败时是否留下该目录、重跑是否使用相同身份、最终汇总如何报告缺失。没有检查完 `make_run_report`，不能直接声称它会记成功、记零或偷偷缩小分母。也不能将现代实现的风险归咎于 2025 年公开结果。

另一个边界是 C3 在执行前过滤空／空值 prediction。因而“以空字符串调用普通评测入口”**不自动等于真正运行了 no-op 验证**。要做环境资格检查，必须核实其实际启动测试的路径；最终 empty-patch 分母如何汇总不在本次检查范围内。

### 3.4 重试、异常、资源与隔离不能从平台标签推导

C2 捕获 mapper 内部部分异常并形成结果行；Podman context 的进入／退出等并非全部在同一捕获范围。`max_failed_job_count=1` 是调度配置，不能据名称推成“每题重试一次”。服务重试、评分重试、重新求解是不同操作，完整语义需要继续检查调度平台及调用者。

这个提交默认并行 job 上限为 100，tmpfs 为 16 GiB，CPU 请求按 tmpfs 数量计算，默认得到 4；均可由对应环境变量调整。它们是 **map worker 配置**，不是我们可给任何 SWE 题的通用资源规格，也不证明复现了文章的 18 分钟。[C2，常量与 yt.run_map spec][C2]

C2 通过 Podman service 的 Docker 兼容 API 调用原评分函数，并传入 `network_mode="host"`。没有在这条路径中取得网络白名单或隐藏评分工件的独立安全保证。文章选择 rootless/daemonless 工具，不等于其所有适配路径从不启动 API 服务；两种陈述不能不分层就当作矛盾或安全证明。

C3 默认 test timeout 为 1,800 秒，镜像 tag 为 `latest`。前者不覆盖全部启动／排队／求解时间，后者不是内容不可变身份。它们是当前 CLI 默认值，**不是论文实验预算**。

### 3.5 可取得的东西与尚未复现的东西

C1 提供 registry 导入、runner 构建与云评分步骤；C0 提供本地评分入口。其可执行性仍取决于任务镜像、数据版本、依赖及服务权限。本文没有登录服务、核价或验证许可链；不能把 README 的历史试用额度写成当前报价。

公开 fork 说明至少有一条可研究的评测实现，但本轮没有发现足以声称 **文章完整的 Kubernetes runner、全部数据挖掘作业与生产监控都已公开**的证据。“初步开放评分后端”与“整个内部平台可复现”应分开。

<a id="analysis"></a>
## 4. 阅读分析：哪些结论能迁移，哪些不能

本节是读者推论和实验设计，不是作者做过的额外实验。

### 4.1 干净评分容器不等于可信评分的全部条件

重新创建环境可以减少求解阶段留下的安装、进程或文件状态对评分的影响，但还须回答：最终导出的补丁是否包含新增文件、二进制、权限及符号链接变化？哪些路径可以覆盖？test patch 与 candidate patch 的应用顺序是否允许候选改写评分内容？

文章的几行伪代码没有给出这些合同，不能补写“已完整防止测试篡改”。B 应把它作为**工作区与评分区分工的参照**，而不是已经实现了 rh2 所需的全部保证。

同理，重跑测试得到一致状态，只能建立某个版本和条件下的评分稳定性；不能证明题面充分、所有合法替代解都会被接受，或目标模型拥有非零成功概率。这三项需要不同证据。

### 4.2 候选存活率不等于坏题率，也不是当前模型的课程

按原文两个近似数作算术，`21/153 ≈ 13.7%`。这是本文派生值，精度不能高于原始计数。候选已经经过上游选择，随后又受到安装、测试、状态一致性等多项约束；因此不能推出“原始 GitHub 问题约 86% 是坏题”。

此外，生产漏斗没有目标 policy 的逐题表现，不能据此推定保留题集适合我们当前模型。对 B 而言，**资产能够运行**与**实际提供学习信号**应分别测量；不是把前者的过滤率调到某个文献数字。

数据处理的优化也应由瓶颈决定。tmpfs 以内存换 I/O，镜像本地化以存储和维护换下载时间；在小批任务或内存紧张时可能不划算。不要因为规模化文章用了内部 registry，就把部署它变成几十题验证的前置条件。

### 4.3 整题重启需要保留尝试身份

状态丢失后的重新求解不是继续原轨迹。建议记录逻辑任务与每次尝试的关系，并把失败尝试的时间与成本保留下来；不要只保留最后成功的那次，否则平均成本和成功率都会受选择影响。

这是对原文生命周期经验的项目化推论，不是要求新造事务平台。一个明确的 attempt ID、终止原因和输出位置就能支持最初排查。原文没有规定 RL 如何消费失败尝试，本篇也不批准任何 reward 或 mask 策略。

### 4.4 对 B 而言，应先保证“可解释地终止”，再追求更高并发

镜像缺失、启动太慢、工具命令超时、测试收集失败、评分超时与候选补丁导致测试失败，不能用一个“超时”或“失败”概括。不同阶段需要不同的责任记录；是否重试应在实验前确定，而不是看到模型得零后临时决定。

以作者规模为背景可以解释为何需要自动归属与清理，但不能把 Pods 数量当吞吐指标。对八卡训练，更相关的计数是完成了多少有效求解、取得多少可判分补丁，以及尾部等待影响了多少训练供给。

### 4.5 一个“18 分钟”没有回答的成本问题

本篇给 B 的成本核算建议是拆开：任务构建、镜像搬运／冷启动、LLM 求解、评分、失败重跑和结果保留。并发度、预热状态及共享集群负载同时改变时，仅墙钟时间不足以比较经济性。

历史评分时间不能换算为目标模型端到端成本，更不能用 500 除以 18 分钟就宣称我们可以达到稳定吞吐。相同补丁的评分加速也不需要被包装成模型学会了新能力；但若加速改变了任务选择、截止时间或有效样本分布，就需要进一步检查学习侧影响。

<a id="mapping"></a>
## 5. 项目一／B 线可消费结论

映射日期 **2026-09-08**，项目定位依据 B 派工而非重新审计全部 rh2。以下是候选验证，不批准训练、平台或最终题单。

| 候选检查 | 来源触发 | 最小实验与输出 | 不能顺手声称 |
| --- | --- | --- | --- |
| 本地与分布式 scorer 等价性 | A 分离执行和评分；C 保留原 run_instance | 固定任务、镜像、补丁，逐测试比对结果与最终报告 | 换后端后天然同语义 |
| 不完整结果的重跑 | C 两层完成判断不同 | 目录存在但 report 缺失的 CPU fixture；检查跳过及汇总 | 已复现某次线上事故 |
| 启动失败与模型失败分离 | A 生命周期经验 | 缺镜像／超时的受控任务；保留退出原因和尝试链 | 一律 reward=0 或一律不训练 |
| 冷／热路径成本 | A I/O 与镜像经验 | 同一小批任务分开测构建、拉取、求解、评分 | 全流程节约等于某局部节约 |
| 可信工件投影 | A 的评分伪代码未给完整 patch 合同 | gold、empty、一个合法替代补丁及路径边界例 | gold/no-op 就覆盖所有 verifier 风险 |

**最小资产表：**可复用的是文章中的架构经验与固定 commit 的评测后端代码；任务／镜像要另行固定 revision；内部完整平台、生产日志和精确成本不在本篇交付范围。与现有 [O11](O11_swe_rebench_v2.md) 的关系是“运维／评测执行”对“V2 数据生产与诊断”，不是同一时代同一数据漏斗的两份证据。

## 6. 未知项与旧说法修正

| 状态 | 具体事项 |
| --- | --- |
| 原文未披露 | 完整生产机器数／资源时、18 分钟逐任务分布、全流程费用、任务重试次数、原始代码 revision、学习增益消融 |
| 本轮未取得 | 顶部装饰图；源码对应历史实验 revision |
| 本轮未检查／未执行 | 完整原 scorer、最终报告分母实现、Kubernetes 私有 runner、镜像与容器实验、平台当前价格和授权条件 |
| 必须纠正的混用 | 153K→21K 不是坏题率；21.3K 任务不是 80K 轨迹；500 个补丁的评分不是 5 次全流程评测；未提供的人时不能从原演讲倒填本篇 |

与演讲中的数字或观点发生差异时，见 [O28b](O28b_swe_rebench_evaluation_lessons.md) 的来源账本；不通过相加两份数据集或改写日期“调平”数字。

<a id="review"></a>
## 7. 自查与交付状态

**官方正文及伪代码精读完成；配套 C0–C3 定点静态核查完成；无独立 reviewer、无运行复现。** 详细边界与算术／链接检查见 [作者自查](reviews/O28a_self_check_20260908.md)。本篇不改变共享索引或 A/B 实施决定。

## 来源定位

[A]: https://nebius.com/blog/posts/infrastructure-behind-swe-rebench
[C0]: https://github.com/SWE-rebench/SWE-bench-fork/blob/e4907b7a90eafaa1f0a6428fd04fe31cdd8b4284/README.md
[C1]: https://github.com/SWE-rebench/SWE-bench-fork/blob/e4907b7a90eafaa1f0a6428fd04fe31cdd8b4284/swebench/harness/tracto_eval/README.md
[C2]: https://github.com/SWE-rebench/SWE-bench-fork/blob/e4907b7a90eafaa1f0a6428fd04fe31cdd8b4284/swebench/harness/tracto_eval/run_evaluation_tracto.py
[C3]: https://github.com/SWE-rebench/SWE-bench-fork/blob/e4907b7a90eafaa1f0a6428fd04fe31cdd8b4284/swebench/harness/run_evaluation.py
[B-request]: ../../../agentic_RL/repo_harness_rh2_workstreams/project1_execution/b_external_reading_requests_20260908.md
