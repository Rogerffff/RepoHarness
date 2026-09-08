# slime 专题 01：训练数据流、真实 SWE 接入、异步组合与近期修复

**本轮重点由模型发布博客转到可追踪的代码路径。** slime 的核心不是为每一种 agent 再做一个 trainer，而是让 Megatron 训练、SGLang 生成、任务数据与 reward 通过同一条消费链连接。当前实现已经包含真实 Claude Code/Codex 接入、分段 rollout 计数、流式前缀恢复和专门的 GLM-5 数值对齐路径；但这些功能是否可以直接组合，仍要检查接口形状、概率语义和生命周期。此次发现 fully-async collector 与分段返回值之间的形状不兼容，并用独立 Python 小检查核实局部行为。**这是一轮有范围的源码精读，不是整库审计、GLM 历史训练复现或本项目升级批准。**

导航：[版本与范围](#scope) · [GLM材料的角色](#glm) · [核心执行链](#flow) · [异步和恢复](#async) · [最新改动](#changes) · [后续精读安排](#next)

<a id="scope"></a>
## 1. 版本、证据与本次实际覆盖

阅读日期：**2026-09-08**。

| 对象 | 固定身份 | 本轮用途 |
| --- | --- | --- |
| slime 主线 | `THUDM/slime@4c193f1f37509cca70f0e88807a9305b70f63f4e`，提交时间 2026-09-03 | 下文 C 系列代码事实的统一版本 |
| 最新非预发布 release | `v0.3.2`，发布于 2026-08-28；tag 指向 `3778dbf6d1a533ab478ecf5ddaa11449a47752b2` | release 说明与之后两个主线提交分开，不把 main 功能都写进 v0.3.2 |
| GLM 官方仓库 | `zai-org/GLM-5@008de4dbcc220032eb9b80a9a9802afad46a4053` | 读取 5.3 / Flash 的 Introduction 与关联模型关系，不作为历史训练代码 |
| RepoHarness | `miles-migration@ac0e2e64163fbe49411540e901df439aea16b6b0` | 写入前读取基线；本篇只做设计层映射，不重新审计当前 miles 适配器 |

版本来自 GitHub 分支、tag 和 release API；“最新”仅指本轮查询到的主线与稳定 release，不代表每个开发分支、未合并 PR 或私有版本均已调查。[release][REL]、[tag][TAG]、[main 固定提交][HEAD]

### 1.1 覆盖表

| 来源 | 实际阅读范围 | 未冒称完成的内容 |
| --- | --- | --- |
| C0 README | 目标、架构、上游参数直通、正确性说明、agentic examples、Miles 关系等相关段落 | 不审核 README 中全部生态项目，不把厂商采用声明当作每项功能的独立消融 |
| C1 `train.py`、C2 `train_async.py` | 全文件 | 未运行分布式训练 |
| C3 `slime/ray/rollout.py` | 全部主要类方法、生成/转换/reward/DP分发 | `build_dp_schedule` 内部算法、全体后端 reducer 未完整精读 |
| C4 `slime/rollout/data_source.py` | 全文件 | 未执行并发重启、持久化恢复实验 |
| C5 `slime/utils/types.py` | 前250行：Sample身份、状态、token/logprob/top-p字段等 | 后续 append/merge 函数留到 token 专题 |
| C6 `slime/rollout/fully_async_rollout.py` | 全文件；另读其 example README | 不以 README 的开箱兼容声明代替组合路径检查 |
| C7 `slime/rollout/sglang_rollout.py` | 250–510行：generate/RM/group、abort、默认collector和hooks | 前部完整请求构造、后部全部eval流程未通读 |
| C8 coding-agent README、C9 `generate.py` | README及完整generate编排、退出和占位返回 | sandbox provider、所有grader、trajectory manager算法未全审 |
| C10 权重更新 factory | 全文件 | 四种实现的传输原子性、恢复和engine版本确认另排 |
| C11 streaming generator | 全文件 | accumulator全部格式实现与测试矩阵另排 |
| D1 customization | 前260行及与本轮接口相关部分 | 未把文档所有扩展点逐一追到消费者 |
| D2 reproducibility | 全文 | 无GPU实测；未逐算子检查完整Megatron patch |
| T1 数值对齐测试 | 文件说明、常量、前置检查、模型及训练/推理参数主体 | 长文件尾部启动与日志处理未全部核读；不称测试已由本轮通过 |
| PR #2340 / #2272 | #2340完整diff；#2272完整说明、关键diff及C11当前文件 | PR作者运行结果不是本轮复现；#2272全部529行新增测试未逐项重读 |

下文每个 C/D/T 标识均在文末给固定提交的完整文件链接。独立小检查仅验证 Python 局部谓词与算术，不导入 slime，也不冒充上游单元测试。

<a id="glm"></a>
## 2. GLM-5.3 与 Flash：短博客提取采用声明，源码专题负责实现

用户本轮明确：两篇博客以相关训练/系统段落为重点，benchmark 展示图不应拖住代码阅读。后续不套用长论文的机械篇幅：**原文写了什么就记录什么，没有 loss 或训练配置就不补公式。** 关键方法图仍需按内容核查，纯榜单图片则不必全部重新抄成表。

本轮再次尝试 [GLM-5.3博客][B53]、[Flash博客][BF] 及官方文档，原站仍未返回可读正文；容器直连失败于DNS。这里没有将障碍说成只有图片，也没有把二手文章拼成官方全文。既有 [R5c预读](R5c_glm5_3_blog.md) 的历史状态不改；本篇可以先用实际取得的官方README、release和代码推进，不要求用户再次制作PDF。

### 2.1 目前可直接核实的关系

官方GLM README明确区分：普通5.3沿用5.2的base、增益归于post-training；Flash从新base开始，采用稀疏与线性attention混合、mHC和30T多模态预训练语料。**Flash不是只给普通5.3换一个推理预算，也不能默认沿用其全部训练数值路径。** “同一base”同样不能自动推出从公开5.2最终checkpoint续训。[G1 Introduction][G1]

这是架构与训练关系的发布声明，不是组件因果实验。比如Flash的架构变化确实值得检查其状态缓存与训练实现，但本轮没有取得其完整RL/OPD目标，不能将SAO、CompactionRL、普通5.3的所有细节直接套上去。

### 2.2 一处已取得的新一手证据

slime **v0.3.2 release** 明确称新增GLM-5训练/生成对齐，覆盖DeepEP、DeepGEMM、DSA与FP8 KV cache，并称该路径在大规模GLM-5.3训练中得到验证。[REL][REL]

因此可以新增“**官方框架release报告了实际使用**”这条证据，而不必等到博客正文恢复；但不能扩大为每个当前slime开关都用于5.3。`x e-7`的可读文档和回归配置见§7；旧索引中`>2.3×`的旗舰吞吐数字本轮仍没有核到对应实验设置，不能由release的功能列表推出。

<a id="flow"></a>
## 3. 核心设计：Data Buffer 是数据职责，不应想象成另一个万能服务

### 3.1 最小执行图

```text
启动driver: train.py 或 train_async.py
  ├─ placement: 安排训练/推理资源
  ├─ RolloutManager: 启动SGLang服务、加载data_source/generate/eval/hooks
  └─ training models: actor，可选critic；先发布初始权重

DataSource.get_samples(组数)
  → 同prompt的n条Sample，设置group_index与index
  → rollout函数组织组并发
  → custom_generate: 普通生成 / 搜索 / 真实harness / 分段返回
  → sample hooks + reward（缺reward时才计算；group-RM另走组路径）
  → RolloutManager: 生成结果 → 身份检查 → flatten → reward处理
  → tokens / masks / logprobs / rollout_ids / teacher等训练字段
  → 按逻辑rollout调度step，再按DP与microbatch安排
  → Ray对象引用 → actor/critic训练 → 权重更新 → 后续生成
```

这张图来自C1–C4/C7的调用顺序，不是把README架构图片转换成未经检查的运行事实。当前首个`update_weights()`在首批生成前执行，保证已加载训练权重进入rollout引擎；有critic时，driver允许先做若干critic-only迭代，达到`num_critic_only_steps`后再更新actor。[C1][C1]、[C2][C2]

### 3.2 扩展点应该落在哪层

| 需求 | 最小扩展点 | 不能由此自动获得什么 |
| --- | --- | --- |
| 一条任务内调用Claude Code、Codex、工具或沙箱 | `--custom-generate-function-path` | 不自动解决新采样组织、评分可信性或多段loss权重 |
| 执行测试/调用reward服务 | `--custom-rm-path`，或生成器预填reward | 预填reward不等于来源正确；不能重复调用导致双计 |
| 整批完成顺序、长期在途任务、特定collector | `--rollout-function-path` | 替换外层可能绕过默认外层的filter/process hooks |
| 任务来源、buffer、取样 | `--data-source-path` | 不自动等于策略自适应课程或持久化经验库 |
| 组统计或训练字段的特殊定义 | reward-post-process / convert-samples hooks | 定义了rollout_id并不会自动重写GRPO组归一化 |

官方建议先改per-sample generate/RM，确有必要才替换整个rollout。[D1][D1] 这给RepoHarness的是职责划分参照，不是要求从miles退回slime或重新写异步循环。

### 3.3 DataSource与运输各自负责什么

`RolloutDataSource.get_samples(n)`的实际返回是**n个prompt组**，每组复制`n_samples_per_prompt`个Sample。`RolloutDataSourceWithBuffer`先取buffer中的整组，再补新prompt；默认`pop_first`是FIFO。[C4][C4]

持久化方面，父类save保存offset、epoch、group/sample计数和metadata。所读WithBuffer没有覆盖save以显式保存`self.buffer`；fully-async worker的在途task和完成队列另在进程内。**保存数据游标不能被称作完整保存所有在途/已完成经验。** 这是当前代码中的职责范围，不是说项目不能扩展恢复。

`RolloutManager._split_train_data_by_dp`调用独立的`build_dp_schedule`，再按partition组织DP-local数据，通过`Box(ray.put(...))`运输；支持object-store与NIXL选项。图上的Data Buffer并非一份自动完成所有重放、事务与持久化的独立数据库。[C3, _split_train_data_by_dp][C3]

### 3.4 四类编号必须区分

| 字段/变量 | 当前代码含义 |
| --- | --- |
| driver的`rollout_id` | 生成/训练循环的迭代编号，也用于日志和周期操作 |
| `Sample.group_index` | 同一prompt采样组的身份 |
| `Sample.index` | 采样实例编号 |
| `Sample.rollout_id` | 一次逻辑执行的身份；该执行拆出的多个训练Sample应共享它 |
| `Sample.weight_versions` | 生成侧收集的权重版本信息，不由上述编号替代 |

C4设置group/index；C5定义其余字段。C3在flatten前检查嵌套Sample的rollout_id，并为允许缺省的平坦Sample分配后备ID。**同名`rollout_id`在driver与Sample里不应被当成同一概念；本轮也没有证明weight_versions已形成逐token版本区间。** [C3][C3]、[C4][C4]、[C5][C5]

## 4. 真实SWE入口：生命周期、消息协议和任务评分分层

`examples/coding_agent_rl/generate.py`通过`SWE_AGENT`选择两对实现：`ClaudeCodeHarness + AnthropicAdapter`或`CodexHarness + OpenAIAdapter`。sandbox provider、harness安装/执行、SWE准备/评分、模型协议adapter分别承担不同职责。README偏重Claude Code，但当前generate确有两种选择，不应仅按README给出单一支持范围。[C8][C8]、[C9][C9]

实际次序是：解析训练/评测protocol和metadata → 可评估性检查 → open_session → 新agent sandbox并安装CLI → 准备workspace → harness运行 → 捕获diff → **退出agent sandbox** → 调用独立评测函数 → finish_session导出训练段。`evaluation=True`时返回仅用于成绩的占位Sample，不走正常训练导出。

默认时间预算分三层：agent 1800秒、grader 600秒、outer guard为二者之和加180秒。agent CLI非零退出只产生告警和metadata，仍可能对已经生成的diff评分；outer timeout/异常则构造ABORTED、`remove_sample=True`、全零mask的占位结果。故不能把CLI超时、整个编排失败和解题失败压成一个状态。[C9 generate/_abort_result/_eval_result][C9]

生成器返回`list[Sample]`，会被`generate_and_rm_group`的`asyncio.gather`保留成`list[list[Sample]]`。这是后文collector形状问题的直接来源，而不是虚构的异常输入。[C7][C7]

C8说明adapter记录每轮prompt/output原始token与logprob，按历史前缀构建消息树，将工具/模板文本mask为0、模型输出mask为1；前缀漂移可能分叉或去掉无法证明来源的训练token。本卷将其作为**文档描述**，没有逐行审完TrajectoryManager。下一卷需要追finish_session、分叉共享前缀与实际loss消费者，不能仅凭“TITO”名称验收。

README的“新评分sandbox所以no test-cheating”也需要收紧：新sandbox是隔离设计，并不独自证明隐藏评分材料不可见、所有测试配置安全或合法替代解都能通过。本轮没有完整审计`swe.py`及provider，故不对通用反作弊效果作背书。

<a id="async"></a>
## 5. 三种异步语义：选择driver还不够

| 组合 | 实际行为 | 本轮不能外推的性质 |
| --- | --- | --- |
| `train.py` + 默认rollout | 生成完成后再训练，之后更新权重；可做共置offload/onload | 生成器内部有async调用，不等于learner持续异步 |
| `train_async.py` + 默认rollout | 先派下一批，再训练当前批；权重更新前等待已派出的生成future | 不等于任意跨版本轨迹无边界流入trainer；代码明确不支持colocate |
| `train_async.py` + `generate_rollout_fully_async` | 持续后台worker保留跨collector调用的在途任务和完成队列；每次取够B组即可返回 | 需要另核buffer、版本、恢复、eval与fan-out的组合；不能只看driver的await就认为全池已排空 |

C2等待的是一次`RolloutManager.generate`的future；在第三种组合里，这个future对应“收够目标组数”，不等于后台worker所有任务已结束。C6还明确不自行负责高层pause/weight-update协议，而依赖底层生成器暴露ABORTED。[C2][C2]、[C6][C6]

### 5.1 fully-async不等于不再等待同题组

C6每个并发task执行`generate_and_rm_group`；C7内部仍用`gather`等待该组成员完成。它绕开的是**训练批次等最慢组**，而不是自动把同题n条样本变成无组等待。single-rollout SAO是否采用，是另一个算法与配置选择。

worker并发池按`sglang_server_concurrency × engine数`配置；同时底层Sample生成还有semaphore。这两个层级的“并发”不能都理解成GPU当前请求数。[C6][C6]、[C7][C7]

### 5.2 backpressure和完成队列

完成队列刻意使用无`maxsize`的`queue.Queue`，避免event-loop回调在put上阻塞所有生成。backpressure通过worker补任务条件中的`qsize < max_concurrent`实现。门关闭后，已经在途的任务仍可能完成，所以这不是队列长度的严格硬上限。[C6 AsyncRolloutWorker][C6]

`get_completed_groups(limit=还缺的组数)`保留多余已评分组给下一轮，避免“先弹出全部，再丢弃超额”。它修复的是经验浪费，而不是一个新的policy-gradient算法。v0.3.2 release列出了对应#2238；本轮看了当前limit逻辑，没有逐行重读该PR的历史diff。[REL][REL]、[C6][C6]

### 5.3 hooks不是通过配置名字自动继承

默认C7外层显式运行dynamic sampling filter、rollout sample filter、all-samples processor；C6外层没有调用这些相同位置的流程，但仍复用了`generate_and_rm_group`内的generation、sample hooks和RM。因此：**per-sample插件复用成立，不等于默认外层所有筛选/分析副作用都自动复用。** 是否需要补接，应根据实际启动组合逐项确认，不凭CLI参数存在判断其生效。[C6][C6]、[C7][C7]

### 5.4 当前collector的分段返回形状不兼容

C7明确允许每个逻辑执行返回多个Sample。C6却有两处按扁平组处理：

1. `_make_done_cb`直接对result的第一层成员读`.status`。成员若是`list[Sample]`，`getattr(..., 'status', None)`得到None，内部ABORTED不会触发该处整组回队列。
2. 排序函数`_key`对第一层成员读`.index`并调用`int(idx)`。成员若是Python list，`.index`是内置方法，不是None，转换会抛出TypeError。

本轮用相同谓词做了独立CPU小检查：平坦输入正确识别ABORTED，嵌套输入漏掉；平坦sort key为17，嵌套sort key确实抛TypeError。**这是局部行为复核，不是已运行SWE完整训练。** 但它足以说明README“custom per-sample logic works unchanged”在当前fan-out组合上不能不加限定地采用。[C6][C6]、[C7][C7]、[C9 _abort_result][C9]

### 5.5 同一rollout的loss计数与GRPO组统计是两个问题

C3先flatten，再调用默认`_post_process_rewards`。在GRPO等算法且启用rewards_normalization时：若长度等于`n_samples_per_prompt × rollout_batch_size`，按固定n reshape；不等时，fallback把整个向量当一个大组。这个分支**不读取group_index**。[C3 _post_process_rewards][C3]

另一方面，C3用Sample.rollout_id计算整条执行的`rollout_mask_sums`，使分散到microbatch的多个段仍有同一rollout分母，并把逻辑执行ID交给step/DP调度。这是很有用的训练单位设计，但不能修复前面的reward组归一化。

纯算术示意：两组`[1,0]`和`[0,0,0]`按组中心化为`[.5,-.5,0,0,0]`；fallback整批中心化为`[.8,-.2,-.2,-.2,-.2]`。例子只说明组关系丢失会改变统计，并不指定一个合法SWE fan-out应该怎样奖励或归一化。自定义reward hook、关闭该归一化或采用其他目标可能绕开该路径；因此不宣称全部slime训练都有此问题。

C3还在reward处理之后才把remove_sample对应mask清零。**无自身梯度不等于不影响组统计**；这与已经精读的SkyRL/SAO/CompactionRL中的训练单位问题可以相互参照，但方法不能混称。

<a id="changes"></a>
## 6. 近期代码改动：release与main分开读

### 6.1 2026-09-03，#2340：超时后真的取消worker请求

此前adapter向SGLang URL直接POST `/abort_request`；最新实现先GET `/workers`，如果是router便向各worker发同一rid的取消，GET返回404时按直连worker处理。它解决的是客户端退出后，后端可能仍占用KV槽并干扰后续内存释放的生命周期问题。[P2340 diff][P2340]

当前helper仍是**best-effort**：worker POST异常被吞掉，没有逐worker完成确认或持续轮询idle；不能把“发了取消”写成“已证明全部后端资源清空”。本轮检查了完整diff，没有重现真实服务超时。

### 6.2 2026-09-03，#2272：streaming external rollout

当前C11将SSE每个可用chunk中的新token/logprob写入Sample，支持cumulative与incremental两种表示。流正常结束却没有`finish_reason`会抛错，不能静默把断流当完整成功。`generate_streaming.abort_mode='request'`令外层只取消相应任务；不是默认对所有worker进行server-wide abort。[C11][C11]、[P2272][P2272]

它保留**已经收到**的内容；源码特别注明SGLang的top-p/routed-expert数据可能只在terminal chunk出现。中途取消无法凭空恢复这些尚未收到的元数据。因此“可以恢复文本前缀”“可以保留所有概率/路由信息”“可以安全参与R3训练”是不同条件。

PR作者报告了Qwen3-30B-A3B、分离4+4 GPU布局、TP4/EP4、两题各两采样、256 response tokens、一个真实optimizer step及前后116个权重bucket同步。cumulative/incremental两次生成约26.1/26.3秒。**这是小型E2E接线证据，不是长程SWE收益、性能显著差异或本项目RTX预算估计。** 两次grad norm不同，材料本身也不构成same-sample梯度等价证明。[P2272 Live external-SGLang E2E][P2272]

### 6.3 v0.3.2里值得下一轮追的修复

release列出teacher在rollout temperature而非0下评分（#2085）、dual-clip epsilon透传（#2247）、跨含CP的DP组做advantage whitening（#2235）、DP-local reward日志配对（#2234）、partial continuation token预算（#2261）、GLM-5 DeepEP对齐（#2262）等。[REL][REL]

**这些目前是已确认release条目，不全是本轮逐行核过的结论。** 例如日志配对修复不能直接升级为“训练reward错配已证实”；要看其字段实际是只用于日志还是进入loss。后续按影响的数据消费者选读，不按PR数量排行。

## 7. 数值一致性与权重发布：已有明确边界，但本轮不替代专项深读

### 7.1 `1e-7`现在有了可读的官方条件

D2把单侧可重复性与训练/rollout logprob对齐分开。后者明确限制在**GLM-5结构（MLA+DSA）**，依赖deterministic SGLang、batch-invariant DeepGEMM、DeepEP以及Megatron专用patch；不是打开一个全局deterministic开关即可对所有模型成立。[D2][D2]

文档描述FP8 forward、BF16 backward、FP32 MoE router，但LM head两侧保持BF16；对齐关键是两侧一致，而不是所有算子一律升FP32。维护的gate默认FP8-E4M3 KV、不使用R3，主模型router/experts参与backward，辅助DSA indexer仍冻结。

公开回归fixture是**6层GLM-5.2、单节点EP8**，不是完整744B旗舰。T1默认阈值实际字符串为`9.999e-7`，文档概括为`<1e-6`；注释给H100参考约`2e-7`。缺deterministic依赖或Megatron patch时测试会skip，所以**CI总览绿色不能替代检查此项有没有实际执行**。[T1说明、常量、前置检查][T1]

这提供了数字对应的模型/依赖/门槛，但本轮没有运行gate，也没有审完整reduce分母；不能把它概括为每个token的最坏误差界，更不能外推到Qwen30B-A3B或Flash混合架构。release中的大规模5.3使用声明与这个公开小fixture也应分别保留。

### 7.2 权重同步选择不是所有模式任意组合

C10按mode/transport/colocate选择实现：

| 条件 | 实现/限制 |
| --- | --- |
| mode=delta | 仅disk transport；assert非colocate |
| full + disk | `UpdateWeightFromDisk` |
| 非disk且colocate | `UpdateWeightFromTensor` |
| 非colocate的剩余分支 | assert full + nccl；`UpdateWeightFromDistributed` |

factory还初始化weight_version；C3返回第一个`update_weights=True`模型的engine和lock，冻结模型不进入该发布集合。**能服务多个模型不等于能同时训练并发布任意多个actor。** 本轮未追完各updater的发布、ack、部分失败、delta基版本校验，因此不作原子发布或exactly-once保证。[C10][C10]、[C3 _get_updatable_server][C3]

<a id="next"></a>
## 8. 后续精读按问题拆分，不再把代码库附在短博客后面扫一遍

| 专题 | 范围及直接入口 | 应交付的核心内容 | 本轮状态 |
| --- | --- | --- | --- |
| **01 主数据流/异步/近期变化** | 本篇C1–C11 | 职责图、字段身份、配置组合、实际限制与最近改动 | 已按上述范围完成首轮静态精读与作者自查 |
| **02 token轨迹与训练单位** | `slime/agent/adapters/`、`slime.agent.trajectory`对应实现（按固定tree定位）、`slime/utils/dp_schedule.py`、loss reducer与相应tests | 一条带sub-agent/compaction的真实请求如何到最终token/mask/reward/梯度；共享前缀和分母的独立小算例 | 待执行；入口目录需按固定tree再精确定位 |
| **03 OPD、PPO与数值对齐** | `slime/backends/megatron_utils/loss.py`、teacher scoring、alignment目录、PR #2085/#2247/#2235/#2262 | current/old/rollout/teacher身份；温度、top-p、top-k/full-vocab、KL方向、detach、CP/DP归一化；GLM专属与通用能力分开 | 待执行；不得从博客关键词推断全部路径 |
| **04 发布、取消、恢复与性能** | 四种weight updater、engine/router生命周期、streaming accumulator、health monitor与tests | 一次更新的严格时序、所有队列的状态保存、request/server取消、失败与恢复边界；可量化性能探针 | 待执行；本篇已提供范围和两项近期实例 |

02优先于继续收集更多benchmark分数：它直接回答真实harness产生的数据是否被按声明训练。03与04分别回答新目标和高性能运行是否破坏同一数据语义。每篇只选关键消费链，不以整库每个文件读过作为完成标准。

GLM两篇博客则保持轻量、分别记录：5.3重点看任务/环境生产、训练采用、质量与风险；Flash重点看新底座、模态、训练/serving约束和实际后训练披露。架构细节只展开到能解释后训练边界为止。配套代码支持的能力、官方宣称使用的能力和本项目实际启用的能力，始终分开。

## 9. 对RepoHarness的直接意义与检查状态

本篇没有要求切换后端、重写异步循环或补齐全部slime功能。当前项目使用miles，是否已修正这些slime路径，需要与项目pin做**定点比较**；本轮没有执行该比较，不能把上游静态问题直接归到RepoHarness。

最有价值的借鉴是三件事：扩展点应优先局部化；数据结构与实际消费者要配对阅读；最新release必须连同适用模型、测试前提和未组合验证的路径一起解释。由此形成的项目候选，是少量真实harness轨迹的CPU形状/身份检查、固定样本数值对照和一个受控运行实验，而不是再加一层通用治理平台。

作者自查见[本篇检查记录](reviews/slime_01_self_check_20260908.md)。本轮没有独立reviewer，没有运行GPU、沙箱、上游测试套件或付费模型；局部Python检查已明确标注。R5b原来的待补图和R5c未取得全文状态不因本篇而被改成全部完成。

## 来源

[C0]: https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/README.md
[C1]: https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/train.py
[C2]: https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/train_async.py
[C3]: https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/slime/ray/rollout.py
[C4]: https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/slime/rollout/data_source.py
[C5]: https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/slime/utils/types.py
[C6]: https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/slime/rollout/fully_async_rollout.py
[C7]: https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/slime/rollout/sglang_rollout.py#L250-L510
[C8]: https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/examples/coding_agent_rl/README.md
[C9]: https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/examples/coding_agent_rl/generate.py
[C10]: https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/slime/backends/megatron_utils/update_weight/__init__.py
[C11]: https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/slime/rollout/sglang_streaming_rollout.py
[D1]: https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/docs/en/get_started/customization.md
[D2]: https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/docs/en/advanced/reproducibility.md
[T1]: https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/tests/test_glm52_6layer_deterministic_e2e.py
[G1]: https://github.com/zai-org/GLM-5/blob/008de4dbcc220032eb9b80a9a9802afad46a4053/README.md
[B53]: https://z.ai/blog/glm-5.3
[BF]: https://z.ai/blog/glm-5.3-flash
[REL]: https://github.com/THUDM/slime/releases/tag/v0.3.2
[TAG]: https://api.github.com/repos/THUDM/slime/git/ref/tags/v0.3.2
[HEAD]: https://github.com/THUDM/slime/commit/4c193f1f37509cca70f0e88807a9305b70f63f4e
[P2272]: https://github.com/THUDM/slime/pull/2272
[P2340]: https://github.com/THUDM/slime/pull/2340/files
