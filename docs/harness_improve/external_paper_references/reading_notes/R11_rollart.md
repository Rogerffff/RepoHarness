# R11 RollArt v2：异构 Agent RL 的执行、陈旧度与端到端性能证据

**RollArt 的贡献不是一种新 RL loss，而是把多任务 agent 训练中的硬件亲和性、环境长尾、突发评分和权重更新一起纳入调度。** v2 在 Qwen3 8B–32B 上报告，相对加强同步、One-off 和 AReaL 式基线，step time 分别改善 2.05×、1.35×、1.31×；但这些基线是在同一代码库内实现，GPU 组成不同，且部分实验使用外部 serverless 算力。论文最值得保留的反例是：放宽 staleness 可缩短 step，却恶化后期 time-to-score；PD 分离收益依赖模型与资源比例，3P1D 反而最差。下文完整覆盖 v2 正文、全部图表、生产案例与适用限制，并对 v1 做定点版本比较。对单节点同构八卡的 RepoHarness，更直接的借鉴是测量方法、环境供给与等待归因，而非照搬异构资源平台。

导航：[来源与版本](#source) · [工作负载与数据](#workload) · [系统与训练语义](#system) · [实验及成本](#experiments) · [生产与限制](#production) · [代码与项目映射](#implementation)

<a id="source"></a>
## 1. 来源、版本与实际阅读范围

**主来源 P。** Wei Gao、Yuheng Zhao、Tianyuan Wu、Shaopan Xiong、Weixun Wang、Dakai An、Lunxi Cao、Dilxat Muhtar、Zichen Liu、Haizhou Zhao、Ju Huang、Siran Yang、Yongbin Li、Wenbo Su、Jiamang Wang、Lin Qu、Bo Zheng、Wei Wang，*RollArt: Disaggregated Multi-Task Agentic RL Training at Scale*。首页机构为 HKUST、Alibaba Group、Tongyi Lab / Alibaba，前五位作者标注同等贡献。首次提交 **2025-12-27**；本次主读 **arXiv `2512.22560v2`，2026-06-15**。2026-09-07 查询 [官方版本历史][P-abs]，最新仍为 v2。[固定 PDF][P] / [HTML][H]。论文登记 CC BY 4.0；本文为带出处的中文分析，不上传原文或第三方代码副本。

[USENIX 官方页面][U] 将本篇列入 **OSDI ’26**，会议论文页码 863–881；本笔记定位一律采用 **arXiv v2 的 PDF 物理页 1–19**，不混用会议页码。本轮核了会议信息，未另取会议 PDF 逐字节比较，因此不宣称两份发行文件完全相同。

**版本对照 V1。** [v1 HTML][V1] 正式标题为 *RollArt: Scaling Agentic RL Training via Disaggregated Infrastructure*。本轮比较标题、设计组织、PD、基线、成本和生产段，不是将 v1 再做一次全部图表独立复核。v1 摘要元数据中的 RollArc 拼写不作为另一系统名称。

**当前代码 C。** v1 摘要指向 `alibaba/ROLL`；当前 [官方 README][C0] 的 2026-06-16 新闻也明确链接本篇 OSDI 论文。本次固定 **`alibaba/ROLL@192b1a01ea61c113b2deb543f7b115783038dff8`**（committer 日期 2026-08-27），只追共享 group queue、staleness 消费和 scheduler 边界，见 §10。该提交晚于 v2；没有恢复原实验逐 run 的代码 revision，也不将整个 ROLL 框架等同本篇可复现 artifact。

**项目基线。** `Rogerffff/RepoHarness@miles-migration:9f93eb64b63f04723c62432fe18027e80b0c15b0`。已读 [来源目录](SOURCE_CATALOG.md) 的 R11 条目与 [当前简报](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md) 的定位／决策边界。目录登记了旧 PDF 及两份综合分析，但本次主来源是在线 v2，没有把旧 PDF 未核定的版本或综合摘要当成新事实。没有覆盖现有独立 R11 稿。

### 1.1 全文覆盖

v2 共 **19 页、15 幅编号图、5 张表、2 个 Listing**。正文 §1–10 和致谢到物理 p.14；p.15–19 为参考文献，末项为 [70] slime。**没有单列技术附录**。正文、脚注和全部技术图表均已读取；参考文献用于检查尾部完整性和引用身份，不表示全文重读全部被引论文。

| 原文范围（物理页） | 覆盖内容 | 本文位置 |
| --- | --- | --- |
| p.1–2，§1、§2.1 | 动机、贡献、五类任务与 Table 1 | §2–3 |
| p.3，§2.2、§3 | Fig.1–3、硬件 Table 2、工作负载定义与阶段占比 | §2–3 |
| p.4，§3.1 | Fig.4 硬件对照、Fig.5 reset/step 长尾 | §3 |
| p.5，§3.1–3.2、§4 开始 | reward 利用率 Fig.6、传输 Table 3、小／大数据路径 | §3、§8 |
| p.6，§4.1–4.2、§5 开始 | 三平面 Fig.7、四类 Cluster 与完整工作流 | §4 |
| p.7，§5.1–5.2 | Worker 声明、资源绑定、Listing 1 | §4 |
| p.8，§5.3、§6.1 | Listing 2、轨迹级流水线 Fig.8 | §4–5 |
| p.9，§6.1–6.3 | 六步协议 Fig.9、staleness、SampleBuffer、通信 | §5、§8 |
| p.10，§6.3、§7.1 | 冗余、PD、模型／软硬件／基线设定 | §6、§8 |
| p.11，§7.1–7.3 | Fig.10 收敛／吞吐／扩展、Fig.11 亲和性／延迟注入 | §6–7 |
| p.12，§7.3–7.4 | Fig.12 serverless、Fig.13 bound、Fig.14 通信／冗余 | §7–8 |
| p.13，§7.4–7.5、§8 | Tables 4–5、3P1D 负结果脚注、disaggregation tax、生产运行 | §8–9 |
| p.14，§8–10、致谢 | Fig.15 生产曲线、故障恢复、静态映射及适用域限制 | §9、§11 |
| p.15–19，References | 依赖来源与尾部检查；无新增训练附录 | §1、§13 |

PDF 图页实际通过截图目视核查，p.1–14 全部技术页已覆盖。带 v2 的 PDF 截图入口有时失败，改用当时仍显示 v2 水印的 arXiv 无版本 PDF 入口补核。容器直接下载 PDF/HTML/TeX 因网络解析失败，未取得本机原始文件；这与“作者未公开”不同。文档中的链接是官方原文入口，不伪造本地缓存路径。

### 1.2 v1 → v2：不只是更换标题

| 事项 | v1 实际表述 | v2 的变化／当前理解 |
| --- | --- | --- |
| 标题与组织 | Scaling…；三条 design principles，架构单列在 §6 | Disaggregated Multi-Task…；四项 R1–R4，资源／数据／控制三平面，§4–6 重组 |
| 基线命名 | veRL、veRL+、StreamRL（one-off） | Sync、Sync+、One-off；新增同代码库的 AReaL 式对照和更具体的基线差异说明 |
| 主速度范围 | 1.35–2.05× | 1.31–2.05×，增加的 1.31 对应 AReaL 对照，不是同一基线数字无条件变差 |
| PD 分离 | §5.2 指出手动配置易失衡，将其留作 future work | §6.3 说明支持，§7.4/Table 5 给 dense/MoE、1P3D/2P2D 对照及 3P1D 负结果；自动调配仍为未来工作 |
| 缓冲区边界 | §5.3 给 start-version 的 α 定义 | §6.2 补 O(αE) 待处理轨迹数量主张与消费前 stale eviction；具体实现前提仍需区分 |
| 通信与远程代价 | 已有异步跨集群通信思路和速度图 | Tables 4–5、§7.5 更明确区分 push、accumulated/exposed pull 与小数据 I/O |
| 使用时间跨度 | §8 写过去六个月 | §8 改为九个月；不据此推断两个版本中所有图都来自全新训练 |

证据：V1 §4–7、§8；P §4–9，尤其 [p.9][P9]、[p.10–13][P10]。上表是定点比较，不是完整文本差分；旧文章中的章节号、图号和基线名字不能无标记平移到 v2。

<a id="workload"></a>
## 2. 核心问题与训练范围

### 2.1 研究对象是四类工作负载的协同，不是“rollout 一定占绝大多数”

作者把 agentic RL 视为 **generation、environment、reward、training** 的组合。generation 内还分计算密集的 prefill 和主要受内存带宽影响的 decoding。真实环境带有状态、容器初始化、网络及 I/O 长尾；reward 可能很轻，也可能是一只固定参数的评分 LLM，其需求通常突发。仅把训练和推理分配到两组 GPU，不能保证其余阶段也匹配资源。[P §1–3，pp.1–5][P1]

Fig.1 描绘计算型／带宽型 GPU、CPU、FaaS 与分布式存储构成的解耦基础设施；Fig.2 比较同步和将训练与生成重叠的流程。多轮 action/observation 的任务定义位于 §2.1，而不是 Fig.1。这些是执行模型，不是独立实测曲线，也不是一套新 SFT→专家 RL→OPD 配方。RollArt 复用 Megatron、vLLM、Ray、NCCL、Mooncake 等组件；论文报告约 **60k 行 Python 实现**，本文没有自行统计代码量。[P §2、§4，pp.3、5–6][P3]

### 2.2 四项设计要求与责任

| 原文标识 | 解决的问题 | 设计内容 | 不应自动推出 |
| --- | --- | --- | --- |
| R1 | 不同任务／阶段对硬件的需求不同 | 硬件亲和性映射，必要时 prefill/decode 分置 | 已有自动学习任务画像的最优调度器 |
| R2 | 环境间逐 turn 屏障放大长尾 | 单条轨迹独立推进、评分完成即可入缓冲 | learner 不需要等待 batch／group；资源之间没有竞争 |
| R3 | 固定预留的 reward GPU 大量空闲 | 将无跨请求状态的评分放到 serverless | 没有额外算力／冷启动／网络成本；所有 grader 都是轻量纯函数 |
| R4 | 跨集群权重同步与长轨迹相互阻塞 | bounded-staleness 的训练／rollout 重叠及恢复 | on-policy 梯度等价、所有旧 token 都来自新策略 |

这些要求来自工作负载剖析，并各有系统层实验。它们不是四个被证明独立可相乘的模型增益。[P §3–7][P3]

### 2.3 所有任务都应保留，但证据职责不同

| Table 1 任务 | 类型 | 原表 modality | 原表交互 turns |
| --- | --- | --- | --- |
| SWE-bench | 软件工程 | Text | 30–50 |
| WebShop | 网页 | Text | 5–30 |
| FrozenLake | 游戏 | Text、Visual | 20–100 |
| GEM-math | 数学与工具 | Text | <5 |
| GEM-game | 游戏 | Text | 1 |

表中是任务类别的行为描述，不是逐 run 的 hard turn cap；FrozenLake 支持视觉也不能证明文中全部训练采用 VLM。主评测使用 Qwen3 8B–32B，因 SWE 较难，§7.1 明确只在 **32B 主实验**加入 SWE；§3 的 Qwen3-8B SWE workload probe 和 §7.4 的 30B-A3B PD 对照是另外的实验范围，不能混成同一 run。[P Table 1，p.2；§7.1/7.4，pp.10、13][P2]

### 2.4 数据／环境不是本篇的生产贡献

本篇没有原始 PR 候选→镜像构建→gold/no-op→任务验证的数量漏斗。没有逐任务训练 manifest、完整 train/dev/test 划分、SWE-bench 具体子版本、仓库时间切分、去污染审计或环境镜像 digest。任务名称与相应引用不能补出这些缺项。

环境使用 Docker/Kubernetes，SWE 与其余任务分别配置 CPU 集群；数学评分明确使用 **Qwen2.5-7B reward LLM** 判断推理过程。这个模型是固定评分器，不是 OPD 教师，也不等于可验证测试覆盖全部推理正确性。其余任务的完整 reward 公式、尺度和最终汇总方式未披露，本文不套用常见环境默认值。[P §3.1、§7.1][P10]

本篇因此适合回答“什么系统损耗阻碍有效运行”，不适合单独回答“如何生产一批可信 SWE 训练题”或“哪些合成任务最有学习价值”。

## 3. 工作负载剖析：瓶颈会随任务和故障状态改变

### 3.1 正常迭代与环境失败迭代的分母不同

作者在 **Qwen3-8B/32K、32×H800、SWE、batch 128** 条件下，比较五个成功迭代与五个含环境故障的迭代。Fig.3 正常组平均 **365.7 s**；主要组成标为 LLM generation **53.8%**、training **23.1%**、env.reset **14.6%**，其余为 env.step 和 reward。文字四舍五入为 366 s、54%、23%、15%。[P Fig.3、§3.1，pp.3–4][P3]

失败组平均 **513.3 s**，正文称 env.reset 占 **rollout time 的 78%**，图中 reset / generation 为 **78.2% / 21.8%**。不能把正常迭代的完整组成和失败图的比例强行视为相同分母，再计算精确的 training 或 reset 秒数。作者强调的是故障发生后瓶颈转向环境，而不是一个固定的“生成占比”。

文中另报告 batched environment interaction 相对理想执行最多增加 **21.3% rollout time**；理想执行 trace 的完整构造与多次重复分布没有展开。这是该剖析的结果，不是任意框架解除屏障后必然得到的增益。[P §3.1，p.4][P4]

### 3.2 同为生成，prefill 与 decode 的硬件结论可能相反

Table 2 给出本文采用的硬件锚点：

| 硬件 | 算力（原表 TFLOPS） | 内存 | HBM 带宽 | NVLink 带宽 | 相对 cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| H20 | 148 | 96 GB | 4 TB/s | 900 GB/s | 1 |
| H800 | 989.5 | 80 GB | 3.35 TB/s | 400 GB/s | 2.85 |

原表未在该栏明确运算精度；cost 采用参考工作 [69] MegaScale-Infer 的相对口径，**不是 2026-09 的实时租赁报价**。不应借这些数字推定 RTX PRO 6000 的相同计算／通信比例。[P Table 2，p.3][P3]

Fig.4 使用 **Qwen3-8B、32K、prefix caching 开启、10 次迭代**，比较近似等成本的 **2×H800 与 6×H20**，并改变 batch 64/96/128/160/192。对多轮 prefill-heavy FrozenLake，H800 的 rollout time 最低为 H20 的 **0.53 倍**；对 decode-heavy GEM-math，H20 时间为 H800 的 **0.49–0.79 倍**。这是端到端 rollout 对照，硬件数量并不相等。[P Fig.4，p.4][P4]

**推断边界。** “按画像选择硬件”有数据支持；“每个数学请求永远该去 H20”“每个 SWE 请求都该去 H800”没有得到普遍证明。prefix cache、输入长度、生成长度和任务内不同阶段都会改变画像；§9 也承认静态 domain 映射的局限。

### 3.3 环境与评分的低利用率问题

Fig.5(a) 的横轴是 **秒的对数刻度**，分别画 reset 与 step 延迟 CDF。reset 长尾可到数百秒，来源包括并发拉镜像造成的网络饱和、宿主 CPU／磁盘争用；step 总耗时还随轮数和每轮工具开销变化。Fig.5(b) 展示逐 turn 批处理时，快环境必须等最慢成员。这一同步点与推理引擎自身的 continuous batching 不应混为一谈。[P Fig.5、§3.1，p.4][P4]

Fig.6 的专用 reward 配置是 **4×H800 reward + 28×H800 rollout**，目标 Qwen3-8B/32K、batch 128、7B reward LLM。图中约 20 个 step 的 reward GPU 利用率均值仅 **7.4%**。这是预留的评分 GPU，不是全部训练集群平均利用率。参数固定且请求独立使评分适合共享／弹性执行，但若要移到外部平台，仍需计算远程资源、调度和数据运输成本。[P Fig.6，p.5][P5]

### 3.4 传输路径：小包稳定性与权重带宽分别处理

单次 action/observation 通常为 KB 到数 MB；反复交互下，连接稳定与累计时延很重要。权重更新则是十几到几十 GB 的传输，易被跨集群低带宽链路主导。Table 3 的具体对照是 **TCP / 200 Gbps Ethernet** 与 **RDMA / 400 Gbps InfiniBand**，同时改变了协议和网络带宽，不是纯粹的 RDMA 单变量实验。[P §3.2、Table 3，p.5][P5]

| 模型 | 权重大小 GB | TCP 秒 | RDMA 秒 | 原表 speedup |
| --- | ---: | ---: | ---: | ---: |
| Qwen3-8B | 15.26 | 6.911 | 5.466 | 1.264× |
| Qwen3-14B | 27.51 | 14.437 | 5.817 | 2.482× |
| Qwen3-32B | 61.02 | 29.649 | 9.442 | 3.140× |

它是本节的通信测量，不与 §7.4/Table 4 中 Mooncake push/pull 的完整路径相混；二者数字明显不同，原文没有足够逐连接／副本信息将它们严格对账。

<a id="system"></a>
## 4. 系统设计：用户声明意图，runtime 组织执行

### 4.1 三平面与四角色

Fig.7 将系统分为：**resource plane 决定放在哪里，data plane 执行具体计算，control plane 决定何时推进、消费和更新**。ResourceManager 维护 H800/H20/CPU/serverless 资源与可用性；pipeline runner 构造角色 Cluster；rollout scheduler、LLMProxy 和 SampleBuffer 协调轨迹。[P §4、Fig.7，pp.5–6][P6]

Worker 是具体执行单元，持有用户计算逻辑及方法级声明。Cluster 是同角色 Worker 的调用代理与控制器，负责部署、绑定方法、分发和收集。四个角色为 **ActorTrain、ActorGen、Reward、Environment**；后端例子为 Megatron、vLLM 和外部函数平台。分开 Worker 角色不等于 agent 的上下文、环境状态和模型权重都无状态。

### 4.2 Listing 1–2 的声明接口

| 声明 | 用户提供什么 | 论文 runtime 行为 |
| --- | --- | --- |
| `register(mode="execute_all")` | 要在全体角色 workers 执行的方法 | Cluster 广播调用并收集结果 |
| `hw_mapping(hw_affinity=...)` | 按任务 domain 指定资源类型，如 FrozenLake→H800 | 根据请求 `tag_name` 选择绑定到相应硬件的 workers |
| `register_serverless(...)` | reward proxy 属性及远程服务地址 | 将代理替换为调用该服务的函数 |

ResourceManager 可借 Redis 等共享 metadata 记录资源绑定；首选池不可用时退到兼容资源。**这里的动态是运行时按标签路由，不是算法自动推断最优硬件。** §5.2 明确使用静态、任务域级声明；自动在线 profiler 到 §9 才作为未来扩展。[P §5、Listings 1–2，pp.7–8][P7]

Listing 为接口／简化实现示例，未给完整可直接运行的 package、部署配置及错误合同。本文不改写其代码成为“官方可运行 recipe”；现代 ROLL 中的同名／类似 API 也要按版本检查。

### 4.3 从任务到可训练样本的流程

启动阶段先绑定资源、建立角色 Cluster；随后并发启动 EnvManager。每个 EnvManager 为一个环境做 reset，维护 observation/action 历史，向 LLMProxy 请求动作，调用环境 step，直到终态。完整轨迹立即触发异步 reward，评分后进入 SampleBuffer，由训练侧成批取走。[P §4.2、§6.1][P8]

数据通过 Ray object references 在不同角色之间传递，并按 worker 并行布局分片。对象引用减少不必要的显式复制和同步，但不代表远程数据不需要实际传输或物化。论文没有公开所有中间张量、精确 tokenizer/template 版本及逐 token capture 对拍；不能仅由该数据模型宣称具备本项目所要求的 TITO 或跨后端 replay-equivalence。

## 5. 轨迹级异步、权重更新与训练语义

### 5.1 两种异步：环境推进与 learner 更新

**轨迹级推进**：每个 inference worker 在引擎步之间处理 `ADD`／`ABORT`；没有待处理控制命令时，继续 prefill/decode。单请求完成即 callback 到对应 EnvManager，不等同一批其他环境；reward 同样按轨迹完成触发。Fig.8 的独立时间线消除的是逐 turn 环境屏障，推理仍可在内部组 batch。[P §6.1、Fig.8，pp.8–9][P8]

**训练／生成重叠**：不同 GPU 执行 learner 与 rollout，并允许尚未完成的轨迹跨权重版本继续。它比只在冻结策略期间并发执行环境更进一步，但仍存在模型安装与 batch 消费同步点。论文所说慢环境不阻塞其他环境，是控制依赖被解除，不保证共享 CPU、存储、GPU、评分或最终 `get_batch` 没有阻塞。

### 5.2 Fig.9 的六步顺序必须按原文保存

| 顺序 | 操作 | 实际作用 |
| ---: | --- | --- |
| 1 | `get_batch` | 阻塞等待 SampleBuffer 收集到预定数量的已评分轨迹 |
| 2 | `suspend` | 令 LLMProxy 停收新的生成请求，保留 in-flight 轨迹 |
| 3 | `update` | 获取 training workers 已有的最新权重，更新 inference workers |
| 4 | `resume` | 恢复 pending generation |
| 5 | `recomp & rollout` | 用新权重重建保存轨迹前缀的 KV cache，继续生成而非从头重做 |
| 6 | `train_step` | 与恢复的 rollout 并行，对步骤 1 的 batch 进行训练 |

第 3 步发布的是已经完成的模型更新，不是第 6 步尚未产生的权重。不能为了叙事顺畅改成“先训练本 batch、再发布、再恢复”，否则会改变重叠方式。异步权重运输也不意味着权重安装完全没有暂停。[P §6.2、Fig.9，p.9][P9]

**读者推论：KV 重算不等于样本重新变成 on-policy。** 新权重重建的是给定前缀的隐藏状态；已生成 token 的行为策略、原 logprob 和原采样事件不会因此变成新策略下的生成。一个 continuation 可能跨版本，仍需另行定义 token/segment 的概率、mask、信用分配及校正。本文没有给出这些优化细节，不能从 `recomp` 一词补出。

### 5.3 staleness 的定义、检查时点与剩余未知

原文定义：当前 agent 模型版本为 $n$，轨迹**开始生成时的版本**为 $b$，只允许满足

$$
n-b\leq\alpha
$$

的轨迹；超出窗口的轨迹中止。该式是对 §6.2 文字的整理，不是新增 loss。v2 说明在迭代内控制轨迹年龄，并在 `get_batch` 形成训练 batch 前清理过期轨迹。默认 **α=1** 来自本篇的速度—收敛折中，不是跨模型通用最优值。[P §6.2，p.9；§7.3，p.12][P9]

这里不以 wall-clock、结束版本、平均 token 年龄或整个 batch 平均 freshness 替代开始版本。脚注把 AReaL 对照描述为只在轨迹开始处限制 staleness；结合 §7.1，应理解为作者选定并重实现的比较语义，不是当前所有上游 AReaL 版本的审计结论。

**缓冲区主张。** v2 声称 E 个并发环境下，窗口将 pending trajectories 控制在 **O(αE)**，并通过消费前 eager eviction 避免乱序完成造成无限增长。原文没有给正式证明、每个环境每个版本最多完成多少次的条件，或按字节限制的背压合同。

**读者推论／待验证前提：**仅限制版本年龄，并不在数学上自动限制同一版本内可完成的轨迹数；还需与 admission、每环境在途／产出限制或消费推进规则结合。即使轨迹条数有界，变长上下文与 KV／工件仍需独立显存／内存预算。这个判断是对主张条件的分析，不是实际复现了 RollArt buffer 泄漏。

### 5.4 GRPO 被明确命名，但算法合同并未完整披露

§7.1 给出 **GRPO、batch size 512、group size 8、均匀任务采样、32K 最大上下文**。论文未明确将 512 钉死为 prompt 数或最终 response 数，不能擅自写成 4,096 条轨迹／step。不同子实验另有 128、84 等 batch 参数，也不能全部合并。[P §7.1，p.10][P10]

全文没有完整 policy loss、advantage 标准化、token／trajectory 分母、importance sampling ratio、clip、KL、entropy、optimizer、学习率、微批更新次数或 mixed-version token 处理公式。也没有说明所有 timeout、工具错误、grader 失败、过期丢弃、冗余取消样本分别如何参与组统计与梯度。**bounded staleness 是系统控制，不等于已经实现或证明某种 off-policy 校正。**

原文没有提出新的 SFT、OPD 或多教师阶段。模型依赖是既有 Qwen3 → 多任务 GRPO 系统实验，以及独立的生产 MoE RL 使用案例；reward LLM 的角色与参数教师分开。

<a id="experiments"></a>
## 6. 主实验：资源、基线与指标先于 headline

### 6.1 可恢复的主配置

| 项目 | §7.1 披露 |
| --- | --- |
| 模型／任务 | Qwen3 8B、14B、32B；Table 1 的多任务，SWE 仅进入 32B 主实验 |
| 学习 | GRPO；batch 512、group 8；任务均匀采样；max context 32K |
| 训练资源 | 异步配置固定 32×H800 |
| rollout 资源 | 其余 64×H800 + 32×H20，共 96 GPU |
| 默认总资源 | RollArt 96×H800 + 32×H20，共 128 GPU；另有两个 CPU 集群及内部 serverless 平台 |
| baseline GPU | 128×H800；不能把 GPU 数相同理解成硬件／成本完全相同 |
| 网络 | 集群内 400 Gbps InfiniBand，跨集群 200 Gbps Ethernet |
| rollout | vLLM 0.8.4，prefix caching、CUDA graphs；8B/14B/32B 的 TP=1/2/4 |
| training | Megatron v0.12.2；训练侧 TP/PP 按吞吐调优，但具体数值没有逐模型列出 |
| 权重运输 | NCCL 2.26.5；Mooncake store 0.3.7 |
| reward | 数学任务使用 Qwen2.5-7B；完整 prompt、评分聚合与逐任务服务开销缺失 |

没有由表中硬件反推出未披露的显存精度、MoE routing replay、通信分片或 wall-clock 总预算。特别是 §7.4 的 Qwen3-30B-A3B 只承担 PD 子实验，不是 Fig.10 全套主对照模型。[P §7.1，pp.10–11][P10]

### 6.2 四个基线是在同一代码库内组织的

| 名称 | 论文赋予的行为 | 比较范围 |
| --- | --- | --- |
| Sync | 标准同步 RL pipeline | 最基本参照 |
| Sync+ | Sync 加异步 reward、异步环境交互和 serverless offloading | 强化基线，不是未优化的上游默认配置 |
| One-off | 消费前一步轨迹，训练与 rollout 重叠；但一轮中的轨迹均须以旧权重完成 | 已包含 Sync+ 的改进 |
| AReaL | 作者在 RollArt 内重实现，bound=1，仅在开始处控制年龄 | 已包含 Sync+ 改进；不是直接跑当前 AReaL 仓库 |
| RollArt | 轨迹内暂停／恢复、迭代级 age 控制、硬件亲和性等 | 与其他行有多个不同点，需结合单项消融解释 |

原文明确因为没有一个开源系统覆盖全部任务，因此在 RollArt 上实现对照。将这一结果写成“公平重跑最新版 veRL/slime/AReaL 得出统一排名”不成立；但同代码库复用执行部分也有助于减少无关实现差异。[P §7.1，p.10–11][P11]

**Laminar 不在实际运行的基线中。** 作者称其闭源，转而把 R1/R2/R3 的隔离实验组合为 gap lower-bound argument。本文把这保留为作者的间接论证，而非直接测量，也不将它升级成严格数学下界。不同 workload 和资源条件下的加速存在共享瓶颈，未经额外假设不能简单连乘得到另一个系统的真实总时间。

### 6.3 指标与误差口径

**Step time** 是五次迭代的平均。**Throughput** 定义为一个 global batch 的 **prompt + response tokens** 除以 step time，不是仅输出 token，不是有效梯度组／GPU-hour，也不是独立逻辑任务吞吐。历史被多次送入模型时怎样统计去重 token，本篇未展开。[P §7.1][P11]

**Validation score** 是各任务的平均分；Qwen3-32B 每十步验证一次，Fig.10(a) 的目标为 **0.85**。这不是 SWE-bench resolution rate 85%，也不是已交代完整权重、样本数和版本的外部综合榜。正文没有给出该曲线的独立训练 seeds、误差条或统计显著性；五个性能迭代不等于五次独立训练。

### 6.4 Fig.10：时间、吞吐和扩展分别记录

**时间—分数。** 横轴 hours、纵轴 average score。到 0.85 附近，原图目测 Sync+ 约 **54 h**，One-off/AReaL 约 **34–36 h**，RollArt α=1 约 **26–27 h**，α=2 约 **29–30 h**；这些是图上近似交叉位置，不是作者逐 run 精确日志，也无置信区间。[P Fig.10(a)，p.11][P11]

邻文给出的 **step-time** 改善分别为 **2.05× / 1.35× / 1.31×**，基线依次为 Sync+ / One-off / AReaL。同段还报告 One-off 相对 Sync+ 为 1.52×。该段位于 Model Convergence 小节并关联 time-to-score 图，但用词为 step time；本文保留这一口径，不把所有数字无条件重命名成“达到同质量的全流程成本”。

α=2 早期更快，后期却比 α=1 更迟到目标，是本篇最直接的速度—质量反例。作者将其解释为 stale 长轨迹的影响；没有独立梯度对拍来证明所有原因仅是 staleness。

**吞吐。** Fig.10(b) 归一化到每个模型自己的 Sync+：

| 比较 | 原文报告的跨模型范围 |
| --- | ---: |
| Sync+ / Sync | 1.40–2.40× |
| One-off / Sync+ | 1.31–1.47× |
| AReaL / One-off | 1.03–1.06× |
| RollArt / AReaL | 1.22–1.36× |
| RollArt / Sync | 2.65–4.58× |

最后一行不能误写成 RollArt / Sync+，也不能任选各行最大值连乘。8B/14B/32B 的任务范围并不完全相同；跨模型吞吐比不是纯模型规模效应。[P §7.2、Fig.10(b)][P11]

**扩展。** Fig.10(c) 使用 Qwen3-14B，在 **64、96、128 张 H800** 上比较吞吐，统一归一化到 Sync+ / 64 H800。这个子实验**没有异构硬件亲和性映射**。作者报告 RollArt 对基线的吞吐优势为 1.33–2.08×，且从 96 增到 128 卡时基线更早出现边际收益下降。没有足够 batch 随规模变化的说明来恢复严格 strong-scaling efficiency；不能据图标题声称线性扩展率。[P §7.2，p.11][P11]

### 6.5 “83% 成本”是硬件比例计算，不是完整账单

按 Table 2 的相对费率，默认 128 GPU 配置的每小时 GPU 成本比为：

$$
\frac{96\times2.85+32\times1}{128\times2.85}\approx0.8377.
$$

这解释了作者约 **83%** 的口径，严格算术约为 **83.8%**。固定 GPU 总数下，它也等于平均每 GPU-hour 的相对价格，但不包含 CPU 环境、外部 reward、存储、网络、服务冷启动和失败作业。它不是“总训练费用已经降低 17%”的完整实证，更不能与另一个不同条件的最高速度直接相乘得到项目预算。[P Table 2、§7.1][P3]

## 7. R1–R4 的单项实验与负结果

### 7.1 R1：近似等成本的异构 rollout，不是等 GPU 数

训练统一固定 **32×H800**，只比较以下 rollout 资源：

| rollout 方案 | 按 cost(H20)=1、cost(H800)=2.85 的相对 GPU 时租 |
| --- | ---: |
| 72×H800 | 205.2 |
| 208×H20 | 208.0 |
| 64×H800 + 24×H20 | 206.4 |

三个价格相近而非精确相等。Fig.11(a) 覆盖模型 8B/14B/32B；混合方案将适合 decoding 的工作放 H20，保留 prefill-heavy 工作在 H800。相对 H20-only 的 step-time 改善为 **1.30–1.68×**，相对 H800-only 为 **1.12–1.37×**。[P §7.3/R1、Fig.11(a)，pp.11–12][P11]

正文有“数学与游戏任务”这一概括，但 FrozenLake 本身也是 prefill-heavy 的游戏例子。实际设计依据是 domain 画像，不宜总结成“所有游戏一律 H20”。增加不同资源数量与选择路由共同构成这个等成本系统对照。

### 7.2 R2：有控制的延迟方差实验

Qwen3-8B/32K，逐 turn 注入 **Gaussian(μ=10 s, σ)** 环境延迟，σ 为 1/3/5/7/10 s；每设置平均十次迭代。Fig.11(b) 标注轨迹级相对 batch-level 的改善依次为 **1.23、1.51、1.69、2.18、2.27×**，随着方差变大优势增大。[P §7.3/R2、Fig.11(b)][P12]

该实验能够分离“逐 turn 同步屏障对方差的敏感性”，比单纯报告总体 GPU utilization 更有解释力。但它使用的是受控高斯注入，不是真实重尾故障分布；原文没有交代可能负延迟的截断／重采样处理，也没有把它作为所有生产故障的准确模型。环境错误率、failed task 的 reward 与重试策略仍需另测。

### 7.3 R3：serverless 让本地 rollout 扩容，不能按相同总资源解释

配置为 **16×H800 本地资源**，并运行三个数学 agentic RL 作业；actor Qwen3-8B/16K，reward Qwen2.5-7B，batch=84。两侧均预留 8 卡训练，本地评分方案另外 4 卡 rollout + 4 卡 reward；serverless 方案把剩余 **8 卡全部用于 rollout**，评分转移到外部弹性平台。[P §7.3/R3、Fig.12，p.12][P12]

原图 reward GPU 利用率从约 **5.8%**（正文四舍五入 6%）升到 **88%**，rollout time（含异步 reward）从 **158 s 降到 77 s**，比值约 **2.05**。这不是全训练 GPU 利用率 88%，也不是固定全部算力情况下只改调用方式就翻倍：**本地 rollout 卡数翻倍，并加入外部 reward 服务资源**。

共享服务能避免单作业评分卡长期空闲，是有价值的部署结论。是否节省全流程费用，仍取决于外部服务实际 GPU 配额、跨作业复用、计费、冷启动和调用成本；本篇没有给完整账单或 serverless 容量分母。§7.5 的 0.01 s 平均 I/O 是运输，不含全部远程推理时间。

### 7.4 R4：更宽的窗口不是越好

Fig.13 对比 α=1/2/4/6。以 α=1 为基准，最大 step-time 改善在 8B/14B/32B 上分别标为约 **1.22×、1.17×、1.14×**，最佳 bound 随模型变化并较快平台化。正文解释是减少因过期而中止的轨迹。[P §7.3/R4、Fig.13，p.12][P12]

然而 Fig.10(a) 已显示 **α=2 的后期 time-to-score 比 α=1 更差**。这项负结果支持按学习目标而非只按 step time 调参。原文没有 α×任务家族×算法的完整稳定性矩阵，故不能据此推出本项目 N 必须为 1 或 2。

## 8. 跨阶段优化与 disaggregation tax

### 8.1 权重 push/pull：累计工作与关键路径残余不同

RollArt 将新权重按桶（例子为 **1 GB**）写入远端 CPU-resident Mooncake store，再由 inference workers 拉取；训练侧跨较慢 Ethernet 写一次，推理侧利用高带宽集群内链路读取，并尽量与 ongoing rollout／push 重叠。集群内仍使用 NCCL/NVLink/InfiniBand。[P §6.3，pp.9–10][P9]

Table 4 的全部数值如下：

| 成本（秒） | 8B | 14B | 32B |
| --- | ---: | ---: | ---: |
| Naive：Push + Accumulated Pull，无重叠 | 38.6 | 84.1 | 157.0 |
| Weight Push | 32.4 | 67.8 | 127.3 |
| Accumulated Weight Pull | 6.2 | 16.3 | 29.7 |
| Exposed Weight Pull | 1.4 | 5.1 | 9.6 |

Push 是训练侧到 store 的总运输；Accumulated Pull 是推理 workers 拉权重的累计成本；Exposed Pull 才是没有被重叠隐藏、仍暴露在关键路径上的拉取时间。算术核对每列 Push+Pull 等于 Naive；被隐藏的 pull 比例约 **77.4%、68.7%、67.7%**，对应作者 67–78% 的范围。[P Table 4，p.13][P13]

Fig.14(a) 实际报告的 **端到端 step-time 改善是 1.10–1.16×**，不是把 157.0/9.6 算成全系统加速。`Exposed Pull` 也不能被改写成全阶段绝对总成本：push 和隐藏部分仍消耗真实带宽与资源，能否隐藏取决于并行工作是否足够。

Table 3 是另一条硬件／传输测量，Table 4 是按该优化拆出的执行路径；原文没有足够拓扑、副本和计时边界解释两表数值的全部差异，本文不将其合成一组“原始带宽实测”。

### 8.2 冗余环境：缓解尾延迟，也改变了样本选择问题

Qwen3-8B/32K、**32×H800、GEM-math**。Fig.14(b) 改变 environment group 数与 group size，以 32组×8 为归一化基准，图中 speedup 标注为：

| group size \ environment groups | 32 | 34 | 36 |
| --- | ---: | ---: | ---: |
| 8 | 1.00 | 1.16 | 1.30 |
| 10 | 1.11 | 1.38 | 1.52 |
| 12 | 1.24 | 1.51 | 1.62 |

系统派发超过目标所需的环境，达到收集配额后允许取消在途轨迹。最大 **1.62× 是 rollout 速度**，没有同时给这些九个设置的独立学习结果、额外 GPU/CPU 工作量和最终训练成员分布。[P §6.3、§7.4、Fig.14(b)，pp.10、12–13][P12]

**读者推论。** 为避开慢成员而优先保留快速完成轨迹，可能改变实际消费的任务难度、长度、成功率和组组成；额外工作也不因取消就没有成本。原文没有证明存在这种偏差，但也没有用匹配分布实验证明它不存在。GRPO 名称不能替代“派发多少、保留多少、按什么组计算 advantage”的合同；当前代码的有限证据见 §10。

### 8.3 PD 分离：30B-A3B 的直接相关证据与明确反例

§7.4 对 SWE、batch=128、32K，比较 Qwen3-32B dense 与 Qwen3-30B-A3B MoE。每个 P 节点为 **8×H800**，每个 D 节点为 **8×H20**；所以 1P3D 对应 8 H800+24 H20，2P2D 对应 16 H800+16 H20。它们都是 32 卡 rollout 配置，不是一个节点内四张卡的含义。[P §7.4、Table 5，p.13][P13]

| 模型 | 1P3D 秒 | 对应 Colocate 秒 | 算术加速 | 2P2D 秒 | 对应 Colocate 秒 | 算术加速 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen3-32B | 722.7 | 741.2 | 1.026× | 701.6 | 734.9 | 1.047× |
| Qwen3-30B-A3B | 294.8 | 327.4 | 1.111× | 251.1 | 305.2 | 1.215× |

作者将其约为 dense **1.03/1.05×**，MoE **1.11/1.21×**。各列有各自 Colocate 对照，不把 2P2D 与 1P3D 的原始秒数当成完全相同硬件价格下的纯调度比较。

脚注同时报告 **3P1D 对两个模型都最差**，因为单个 decoding 节点成为瓶颈。因而这篇提供的是模型和 workload 相关的 PD 证据，不是“MoE 一律应该 PD 分离”；对同构、PCIe、无 NVLink 的八卡节点不能直接外推配置。

### 8.4 远程调用的“税”有多大

| 路径 | 最大 payload | 平均每次运输开销 | 最大每次运输开销 | 必须保留的分母 |
| --- | ---: | ---: | ---: | --- |
| Environment interaction I/O | 2.7 MB | 0.02 s | 1.4 s | 单次环境↔推理传输，不是整个工具执行 |
| Serverless reward I/O | 5.2 MB | 0.01 s | 2.1 s | 单次远程评分数据运输，不是全部评分时延 |
| 跨集群权重 | Table 4 | 未给同口径均值 | exposed pull 1.4–9.6 s，按模型 | 不和 payload 调用统计直接相加 |

这些结果支持在作者网络条件下，数据运输没有抵消系统总收益；不证明所有远程部署零开销。没有完整调用次数、p95/p99、冷启动／热启动分层或 API 费用；多轮累计时延也不能只由单次均值忽略。[P §7.5，p.13][P13]

<a id="production"></a>
## 9. 生产案例与作者主动声明的适用限制

### 9.1 3,000+ GPU 的使用主张与实测窗口

作者称过去九个月有数千个 agentic RL 作业使用 RollArt，并展示 **超过 3,000 GPU**、为 **Qoder** 训练的数百 billion 参数 MoE 案例。数据为内部数学和软件工程任务，prompt 最高 **12K**、response 最高 **46K**；没有披露精确模型架构、任务 manifest、最终能力成绩或完整成本。[P 摘要、§8，pp.1、13–14][P1]

Fig.15(a) 将内部任务匿名为 T1–T8，平均 turns 在 **1–48** 之间；图上有误差标记但没有明确其统计定义，不能擅称 95% CI。每步最大 response 长度高于均值 5 倍，峰值 9 倍；最大 interaction turns 高于均值 40 倍。这些是长尾画像，不等于所有轨迹平均长度都如此大。

### 9.2 彻底异步后依然可能缺样本

训练／生成 GPU 初始比例 **1:5**，bound=1，最长迭代仍到 **1.5小时**。Fig.15(b) 把时间分成模型计算与 `get_batch`：learner 算完 logprob／gradient 后等待足够评分轨迹，单迭代等待最高 **62%**。作者估计完全消除这些等待可理想地减少 **22% 总时间**。最高等待占比、整个区间加权损耗和整个集群利用率是三种不同量，不能互换。[P §8、Fig.15(b)，pp.13–14][P14]

基于画像调整训练／生成资源比例，并调优 MoE prefix caching，前 **25步**取得 **1.66×** 的组合端到端改善。Fig.15(c) 横轴 step、纵轴累计时间 **hours**；原图目测末端约 **19–20 h 对 11–12 h**，与该量级相符。图和文字没有给每项优化独立贡献，也未公开最终资源比例；不是“只开 prefix cache 就快 1.66×”。

### 9.3 环境启动与恢复策略

优化前，60次迭代中有 **7次**遇到长时间初始化失败。原因包括大规模镜像拉取和网络不稳定。优化使用内部 registry 镜像外部来源，在 registry 与计算节点间加入分布式、负载均衡缓存，reset 优先从缓存取镜像。作者报告 reset 成功率 **>99.99%**，**>99.99%** 的初始化在一分钟内完成，数十万次 reset 中重尾事件不超过十次。[P §8，pp.13–14][P13]

这些分母是 reset／初始化事件，不是所有 SWE 任务成功率；精确 reset 总数和误差范围未给。缓存的是环境镜像与分发路径，不自动表示跨 agent 复用污染工作区或 grader 隔离问题已经解决。

恢复策略分别针对阶段：持久连接与指数退避减少环境连接失败；Kubernetes 管环境 workers，serverless 平台管 reward workers；inference worker 首先原卡重启，多次失败后移除并把保存轨迹转到健康 worker；training 从最新 checkpoint 重启。文中说一周训练只观察到 **一次 failure**，没有进一步明确其统计层级，不能把它与前述环境失败拼成“所有类型故障总计只发生一次”。

没有训练事务去重、恢复后的样本身份／策略版本、exactly-once 消费或 grader 工件生命周期的完整合同。本案例证明作者在大规模真实作业中使用并调优该系统，不等于本文独立复现或证明每种恢复机制的正确性。

### 9.4 §9 的限制对八卡项目很关键

作者明确列出三类收益有限的场景：**同构集群使 R1 硬件亲和映射退化为 no-op；严格 on-policy 或 compute-light 训练难从 R4 获得很多重叠收益；没有弹性资源时 R3 无法实现。** R2 的轨迹级推进和冗余环境仍可用于存在环境长尾的工作负载。[P §9，p.14][P14]

当前亲和性配置是静态任务域级声明。作者称单个生产周内 domain 画像相对稳定，不需反复调参；在线 profiler、自动请求重路由和自动 PD 比例是未来方向。这是一段特定运行的经验，不证明随着 policy、任务分布、上下文策略改变，静态映射永远足够。

相关工作将 RollArt 放在 speculative generation、阶段融合、异步／解耦 RL 与资源解耦 serving 谱系中；本篇并未逐项重跑全部被引系统。结论重述四项要求，没有另加数学、偏好或安全后训练附录。

<a id="implementation"></a>
## 10. 官方代码附查：仅验证实际 group／staleness 消费路径

本节所有链接固定到 **`192b1a01ea61c113b2deb543f7b115783038dff8`**。检索从官方 README 和 `GroupQueue` / `LLMProxy` 关键符号开始，完整读取 [C1：`roll/distributed/scheduler/rollout_scheduler.py` 的相关前 700 行][C1]。没有运行代码，没有审计整个 ROLL、optimizer、infer engine 或全部部署文件。

### 10.1 当前代码不是论文命名空间的一一对应 artifact

v1 与当前 README 能确认 ROLL 是官方开放入口，但 Listing 使用示意 `rollart.distributed`。本轮对 `hw_mapping` 的仓库代码检索没有命中，不能据此断言所有版本都不存在该功能；也不能把示意 decorator 当作已经在当前公开入口逐项复现。

没有找到并核验一套同时冻结论文四基线、所有任务、异构硬件、serverless 资源及成绩日志的完整 artifact。基于 ROLL 有同类组件是一层证据，完整复现 RollArt v2 是另一层。

### 10.2 队列单位是 group，创建步与消费步都有作用

`GroupData` 保存 `group_id`、`episode_id`、`create_step`、rollouts 和在途计数。`GroupQueue.advance_step(step)` 按 **step − create_step > async_generation_ratio** 清理过期 episode；`GroupQueueManager.get_batch` 消费时再次进行相同年龄检查。当前这条路径据 **group 创建步**判断，不是逐 token 最新 logprob 的语义。[C1，约 L214–294、L483–542][C1]

`get_episode_id` 允许派发到 **group_size + group_size_redundancy**。`put` 累积返回结果，在达到 group_size 时触发完成或 group_filter；过滤后重新创建组。`GroupQueue.get()` 按本队列最小 episode_id 消费，即使稍晚的组先完成，也不直接越过它。[C1，L296–374][C1]

外层 manager 对不同 group queue 的 get 使用 `FIRST_COMPLETED`，保留尚未消费的 pending/done 请求；注释明确指出持续复用最快队列可能造成 episode_id 不平衡。最终去掉 None、重新检查过期、截取 `group_rollout[:group_size]` 后组装 batch。[C1，L483–550][C1]

这说明“轨迹级异步”和“保留 GRPO 分组／公平性约束”可以同时存在。**它不证明所有 group 内到达次序、额外冗余和筛选均不会改变学习分布**，也不能自动恢复论文 batch 512 的单位。

### 10.3 scheduler 的控制路径与版本边界

`RolloutScheduler.suspend()` 依次让 router suspend、abort_all、wait_complete。`_get_batch_impl()` 更新 EnvManager 的 step、推进 queue、恢复 router，再等待 batch 或 rollout loop 异常；随后拼接 `DataProto` 并转为远程对象。[C1，L627–700][C1]

这是当前实际消费路径的静态事实，不是“论文里 ABORT 一定如何恢复 token”的完整证明。单靠该文件不能判断 abort 命令是如何保留前缀、哪个版本生成每个 token、group filter 的完整规则、loss mask、权重安装与所有 worker acknowledgments。本文没有为了补全这些未知而继续整库追踪。

当前 `EnvActivityMonitor` 记录开始／提交时间，超时主要产生 warning；从这个类本身不能推导自动取消、环境修复和 exactly-once 恢复。纸面生产容错与当代某一个公开监视类也不是同一层证据。

## 11. 证据强度、未知项与易混淆边界

| 命题 | 本篇直接支持 | 不支持／仍需验证 |
| --- | --- | --- |
| RollArt 已实际用于训练 | Qwen 系统实验及内部生产 MoE 运行 | 独立复现、外部提供方共同评测 |
| 对比有系统控制变量 | 同代码库基线；近等成本亲和实验；方差注入；α sweep | 所有分数都是单因素因果效应；各收益可相乘 |
| 异步提高有效效率 | 更好 step time／token throughput，Fig.10 time-to-score | 相同全流程费用、所有任务无退化、梯度与同步等价 |
| 环境独立执行 | 解除逐 turn 环境屏障，callback 及时返回 | 所有长尾消失；最终 learner 没有 batch 等待 |
| serverless 有价值 | 多作业共享评分、提高评分卡利用并释放本地 rollout 卡 | 免费额外算力、整个集群 88% 利用、完整成本下降比例 |
| bounded stale 可控 | α 定义、检查／中止、速度—收敛实验 | 具体 IS loss、token provenance、严格缓冲区内存上界 |
| PD 可以帮助同量级 MoE | 30B-A3B 特定 SWE/32卡实验 1.11–1.21× | 八卡同构节点可复刻；3P1D 或所有配比都改善 |
| 环境稳定性显著改善 | 内部 registry/cache 后的 reset 统计 | grader 可信、防作弊、数据质量或任务可解性改善 |
| 开放实现可复用 | 官方 ROLL 入口、若干对应机制当前可查 | 全部 v2 recipe 与原始 run revision 已冻结公开 |

还影响复现的未披露项集中如下：**任务数量和 split、每任务评价器及预算、GRPO 完整 loss 与样本单位、采样参数／精度、模型与数据 revision、所有 runs 的资源与独立 seeds、serverless 账单和容量、取消／重试造成的有效训练分布、生产模型精确结构与恢复消费语义。** 这些缺口是检查全文后的记录；没有把未下载成功的源文件、未做代码审计、作者未披露混成一种 unknown。

没有发现需要自行改写原表数字才能讲通的理由。主要需保留的版本／口径差异是：旧版 baseline 名称与新版不同、main probe 与主训练模型范围不同、Fig.3 的正常／失败分母不同、Table 3 与 Table 4 的传输路径不同、step time 与 time-to-score 相邻但不等义。表中的报告值按来源保存，本文新增算术另作标注。

## 12. 对 RepoHarness 项目一的条件化判断

映射日期 **2026-09-07**，基线见 §1。当前项目是 **miles + SGLang + 外部 coding harness / Claude Code**，目标单节点 **8×96GB RTX PRO 6000、PCIe、无 NVLink、约30B-A3B**；rh2 负责可信任务、评分与训练消费。简报仍保留 GPU 资格、taskset 和部分算法／harness 决策开放项。本篇阅读不把这些改成已完成，也不改当前设计约束。

### 12.1 先借测量方法，再决定是否需要改机制

| 候选借鉴 | 原文依据 | 当前边界与条件 | 最小对照／结果 |
| --- | --- | --- | --- |
| 对一条真实 rollout 分段定位等待 | Fig.3、5、15 | 利用现有 timing/trace，先判断生成、reset、工具、grader、queue 谁限制训练；不是再建监控平台 | 固定任务、模型、预算，报告阶段关键路径、尾部、错误率与每GPU-hour的合格组 |
| 改善环境启动及评分供给 | §8 registry/cache；R2/R3 | 已有 miles 异步不代表 CPU/grader 没有瓶颈；缓存不可变镜像，不借机放宽评分隔离 | 一项缓存／并发／生命周期改动开关，比较相同样本供给下等待、成本和评分一致性 |
| staleness 以质量—时间联合选择 | α=2 后期 TTS 回退 | consume-time 权威在 miles，不能增第二套 age 规则或把 α=1 当默认答案 | 在已验证版本语义下比较有限N，记录丢弃、有效更新、开发曲线与总预算；最终保留独立测试 |
| 冗余只作为确认存在长尾后的窄候选 | Fig.14(b) | 先核上游是否已有，不能改坏全组准入；额外派发、取消、成员与重试要有明确统计 | 固定实际消费逻辑组，比较速度，同时报告额外执行成本与保留任务／长度／reward分布 |

每一项只有在真实瓶颈被测到后才值得实施。尤其是权重传输，若已非关键路径，就不该因 Table 4 数字显眼而再造 Mooncake 同步层。

### 12.2 目前不支持直接引入的部分

本项目同构八卡不具备论文 R1 的 H800/H20 差异；没有独立弹性 GPU 平台时，R3 的资源转移实验也不可复制。PD 32卡结果不能当八卡配置建议。三平面 Worker/Cluster 架构是可理解的参考，但 miles 已承担的训练、推理、权重更新和通用调度不应重写。

本篇也没有提供“动态任务供给必需”的直接证据：§7 采用固定多任务、均匀采样，主要收益来自执行与资源组织。反过来，它也没有证明任务供给永远充足——生产 `get_batch` 长期等待说明需要实际区分计算供给不足、环境失败、任务长尾和被过滤的样本。

**项目判断：**RollArt 支持把“一项可归因的环境／执行效率改进，加上正确训练消费和独立学习结果”作为有价值的研究工程成果，而不要求项目一先补齐所有前沿训练技巧。其本篇数据不能替我们证明具体八卡增益；最小成功证据应同时包含实际节省、样本语义保持和模型结果，而不是只复制论文的模块名。

## 13. 快速定位与关联阅读

| 想回答的问题 | 本文入口 | 原文入口 |
| --- | --- | --- |
| 1.31–2.05× 相对谁、是什么指标？ | §6.2–6.4 | §7.1–7.2，Fig.10，pp.10–11 |
| 83% 是否包含外部评分与全部费用？ | §6.5、§7.3 | Table 2；§7.1/R3，pp.3、11–12 |
| 异步怎样暂停、发权重、恢复？ | §5 | §6.2，Fig.9，p.9 |
| group_size、冗余派发和消费是否同一数量？ | §8.2、§10 | Fig.14(b)，pp.12–13；当前 C1 |
| 32B 权重157秒为何不等于系统十多倍改善？ | §8.1 | Table 4、Fig.14(a)，pp.12–13 |
| 30B-A3B 的 PD 数据和负例是什么？ | §8.3 | Table 5、3P1D脚注，p.13 |
| 生产长尾和reset工程如何量化？ | §9 | Fig.15、§8，pp.13–14 |
| 同构八卡适合借什么？ | §12 | §9 Operational Regime，p.14 |

关联已存在笔记：[O01 SkyRL-Agent](O01_skyrl_agent_sa_swe.md) 用于比较 rollout 阶段重叠与 learner 异步；[N10 Forge](N10_minimax_forge.md) 用于比较速度和实际消费分布；[N11 miles](N11_miles_agentic_rollout.md) 用于核对本项目接线与上游职责；[N07 SDPO](N07_sdpo.md) 说明新增反馈／教师通路会引入另一类执行成本。关联只是问题导航，不把其他来源的公式或默认值填入 RollArt。

## 14. 作者自查与交付状态

**完整精读与作者自查完成，待独立复查。** 全部 v2 技术正文、5表、15图和2Listing已覆盖；无技术附录。已单列 v1 定点增量，复算硬件成本、通信组成、PD和serverless比例，并检查当前代码的窄消费路径。没有创建独立 reviewer，没有训练、模型权重下载或分布式数值复现。

详细范围、成文修正、图表核查和建议后续抽查见 [R11 作者自查](reviews/R11_rollart_v2_self_check_20260907.md)。仅本稿和自查由本线程维护；共享索引交汇总线程更新。本文不批准项目新组件、算法或实验范围。

## 官方来源链接

[P-abs]: https://arxiv.org/abs/2512.22560
[P]: https://arxiv.org/pdf/2512.22560v2
[H]: https://arxiv.org/html/2512.22560v2
[V1]: https://arxiv.org/html/2512.22560v1
[U]: https://www.usenix.org/conference/osdi26/presentation/gao
[P1]: https://arxiv.org/pdf/2512.22560v2#page=1
[P2]: https://arxiv.org/pdf/2512.22560v2#page=2
[P3]: https://arxiv.org/pdf/2512.22560v2#page=3
[P4]: https://arxiv.org/pdf/2512.22560v2#page=4
[P5]: https://arxiv.org/pdf/2512.22560v2#page=5
[P6]: https://arxiv.org/pdf/2512.22560v2#page=6
[P7]: https://arxiv.org/pdf/2512.22560v2#page=7
[P8]: https://arxiv.org/pdf/2512.22560v2#page=8
[P9]: https://arxiv.org/pdf/2512.22560v2#page=9
[P10]: https://arxiv.org/pdf/2512.22560v2#page=10
[P11]: https://arxiv.org/pdf/2512.22560v2#page=11
[P12]: https://arxiv.org/pdf/2512.22560v2#page=12
[P13]: https://arxiv.org/pdf/2512.22560v2#page=13
[P14]: https://arxiv.org/pdf/2512.22560v2#page=14
[C0]: https://github.com/alibaba/ROLL/blob/192b1a01ea61c113b2deb543f7b115783038dff8/README.md
[C1]: https://github.com/alibaba/ROLL/blob/192b1a01ea61c113b2deb543f7b115783038dff8/roll/distributed/scheduler/rollout_scheduler.py
