# Dressage 源码精读：Claude Code／SWE 训练闭环与 Step Balance

**日期：2026-09-08。类型：固定版本的官方文档 + 源码专题，不是论文复现。**

Dressage 是与 RepoHarness 很接近的参照：它复用 slime 的训练内核，通过模型代理、Paddock、Blackbox Server 和训练 hooks，把真实 coding harness 的多轮执行送进 RL。最值得借鉴的不是“又支持了异步”，而是两件具体工作：**把动态拆分的 segment 按正确的轨迹／题目单位消费；在保留缓存局部性的同时，利用后续 generation step 缓解 engine 长尾。**

两类成绩必须分开：官方 SWE 训练文章报告 Qwen3.5-4B 在 Claude Code 下的 SWE-bench Verified 从 **32.6% 到 37.8%**；Step Balance 的 **Effective TPS/GPU +39.4%–64.2%** 来自另一个单机八 GPU、八个单 GPU engine、temperature=0、每题一条轨迹的同步 rollout 对照，**不是该 RL 训练增益的消融，也不是八卡 30B-A3B 的性能承诺**。[S1]；[S2]

本轮读完三份核心文档的文本，沿实际 SWE 脚本追查关键消费路径，并完整阅读 Step Balance 的调度器与 greedy 实现。对三个原始源文件做 Git blob 校验后执行 **25 个 CPU 探针，25 通过**。探针暴露了若干需辨认的边界，也排除了一个不应轻率报告为主路径 bug 的疑点。没有启动 GPU、Ray、SGLang、E2B、Claude Code 或完整 upstream test suite；若干原图未取得，不标为全图核验完成。

导航：[版本与覆盖](#scope) · [架构与执行路径](#architecture) · [SWE 环境与评分](#environment) · [轨迹和训练目标](#learning) · [Step Balance](#balance) · [实证边界](#evidence) · [CPU 探针](#probes) · [适用性与贡献机会](#project) · [复核入口](#references)

<a id="scope"></a>
## 1. 来源身份、范围与证据分层

### 1.1 固定版本

| 对象 | 本轮固定版本 | 用途 |
| --- | --- | --- |
| Accio-Lab/Dressage main | `3e3142fe8ea07e4504c3b20a936a4c201a3de44c`，2026-08-27，`docs(readme): update news for step balance` | 本篇全部 Dressage 代码和文档事实 |
| Dressage 的 slime submodule | `aaf5c2092b01219fa0d5c2d323741d409086ca32`，THUDM/slime | 检查后端 advantage、TIS 和 reducer；不使用另一版本的同名实现代证 |
| RepoHarness 读取基线 | `32b615c4e4f869b448174e5974e7a8d29fc4612c`，`miles-migration` | 仅用于文末项目映射，写入时保留其他线程更新 |
| SWE 官方 harness | 配套实验文档登记 `SWE-Gym/SWE-Bench-Package@16dd480cce9b27bf111a362d280881c6def5d2a7` | 实验依赖身份；本轮未逐行审计该仓库 |

Dressage 是公开 Apache-2.0 代码库，但外部 CLI、模型权重、任务镜像和数据的许可应各自核对，不能由项目许可证推出全部资产的统一许可。[S0]；[S1]

**本轮主要证据来自官方仓库，不用旧 Pro 调查替源码补细节。** 搜索时出现的镜像／聚合页面不作为承重来源。本稿以该固定仓库的工程文档和代码为主来源，不将工程报告表述为“论文证明”。

### 1.2 阅读范围表

| 材料 | 实际范围 | 不在本轮完成范围内的内容 |
| --- | --- | --- |
| README | 架构、能力、news、训练与文档入口概览 | 全部链接所指的每个发布／模型／数据集 |
| `docs/training.md` | 完整文本：hooks、multi-segment、reward、分母、staleness、TITO 和模式关系 | 不把每个说明都视为已有同条件模型消融 |
| `docs/blackbox-swegym-claude-code-experiment-en.md` | 完整文本：数据、运行、fresh grader、反作弊、配置、结果 | 训练曲线图片未成功取得；所有训练／评测日志未重放 |
| `docs/engine-rebalancing-report-en.md` | §01–06 完整文本：动机、机制、实现、实验和未来工作 | 图中独有的逐数据集数值、热力图和精确分布未完成目视核验 |
| SWE 实际脚本、sync rollout、blackbox dispatch、multi-segment、converter、reward post-process | 全文／对应完整函数，绑定真实入口 | 没有执行真实训练作业 |
| sample writer | `samples.py` 全文 | 未执行真实 routing tensor／TQ 数据恢复 |
| Step Balance | `scheduler.py`、`greedy.py` 全文；其 calibration/profile/state 依赖追到调用边界 | 未完整审计 Ray 校准 kernel、Mooncake 服务、SGLang 内部缓存实现 |
| Proxy／BBS | Proxy `server.py` 1960–2425 行附近的请求、路由、生成、记账；generation controller 220–530；Claude adapter 1–220 | 非全文件审计；未完整遍历所有协议转换和 BBS backend |
| fresh evaluator | 1–270 行的 patch→新沙箱→评分→清理路径；reward parser 全文 | 不宣称完整网络／进程隔离安全审计 |
| slime 后端 | `cp_utils.py` 的 reducer／metric helper；`loss.py` 525–1130 的 advantage、TIS、policy loss，另看 response/CP 输入切片 | 没有完整审核 Megatron optimizer、训练调度和所有分布式 collective |
| tests | greedy 的现有测试全文；converter 现有测试前 230 行；自写窄探针 | 未运行整套 upstream 测试，也未穷尽现有测试覆盖 |

**图页缺口的处理：**本文只引用报告正文／README 明确写出的数字。原图入口仍留在官方文档中；没有根据图片文件名猜测值，也没有把文本阅读写成原图审查。此缺口不影响所列源码函数的阅读状态，但限制了对完整性能图表的复核。

### 1.3 如何理解本文的“确认”

**官方报告值**是作者对其运行的描述；**源码事实**是固定 commit 上可追踪的实现；**CPU 观察**仅来自 §9 指定函数及测试替身；**静态待验证项**未必在正式路径触发；**项目建议**不属于原作者结论。代码中存在某功能，不自动等于官方 SWE 训练启用了它，更不等于 RepoHarness 已有同样收益。

<a id="architecture"></a>
## 2. 架构：复用训练后端，但自己负责执行和消费接缝

### 2.1 责任不是“训练框架 vs 一个 HTTP adapter”两层

| 层 | Dressage 的职责 | 上游或外部职责 |
| --- | --- | --- |
| slime training | 通过自定义 generate、reward、convert、日志／loss hooks 对接 | Ray 训练编排、Megatron、优化器、SGLang worker 和权重同步主体 |
| Dressage rollout | 题目组派发、失败重试、完整轨迹收集、segment→Sample | 不实现新的模型训练内核 |
| Dressage Proxy | 模型 API 代理、实际 token/概率记录、上下文 lineage、暂停／恢复、Step Balance | 不直接实现 SGLang 的 KV 搬运 kernel |
| Paddock | agent 交互方式；whitebox 自己循环，blackbox 委托外部 harness | 不等于某一种沙箱部署 |
| Blackbox Server（BBS） | 在沙箱内注册并调用 CLI backend，处理会话与协议代理 | Claude Code 自己管理工具调用、历史、compaction 等实际行为 |
| SandboxProvider | 创建／销毁执行环境，命令和文件能力 | E2B／自有容器平台等具体基础设施 |
| SWE recipe | 数据转换、执行约束、候选 patch、fresh scoring、完整性处理 | 官方 SWE-Gym task/test 语义 |

来源：README、SWE guide 及实际 `generate()` 路径。[S0]；[S1]；[C2]

**whitebox/blackbox 是谁控制 agent loop；local/remote 是环境放在哪里。** 这两个维度不能混用。一个 blackbox CLI 可以在自有容器中运行；已有 SandboxProvider 也不意味着需要它实现 `register_agent` 或 Claude 会话管理——这些是 Paddock/BBS 职责。[S1]

### 2.2 本轮选择的真实路径

```text
SWE-Gym data converter → JSONL(prompt + trusted runtime metadata)
    → slime train.py + Dressage sync rollout hook
    → 一次派发 rollout_batch_size 个 prompt groups
    → 每个逻辑 rollout 获得 session / instance 身份
    → Paddock.create → BBS.register_agent → before-agent commands
    → Claude Code 的模型请求
       → BBS/本地代理 → Dressage Proxy
       → 输入 token 构建与 lineage
       → Step Balance（仅显式开启时）
       → SGLang /generate → output ids / logprobs / versions
       → CLI 继续工具操作、后续 turn
    → 冻结／提取候选 patch → fresh sandbox 评分
    → Proxy finalize → read_trajectory(drain=True)
    → integrity scan → 全部 segment 展开为 Sample
    → 正常未预填 reward 的路径，仅 terminal anchor 进入 reward_fn
    → 轨迹级 reward 组统计 → 向 sibling segments 广播
    → step-wide loss denominator → slime CP/DP 训练消费
```

这个流程中的 **BBS→CLI 协议和服务内部**只做了边界检查；图不是对它们全部代码的审计证明。实际调用主线见 `blackbox_dispatch_swegym.generate`，同步边界见 `sync_rollout._run_sync_rollout`。[C2]；[C3]；[C16]

### 2.3 “fork-free hooks”不等于零维护耦合

`convert_samples.py` 在文件头明确说它接近逐字复制 slime 的 converter，并要求升级 slime 时逐项 diff。Dressage 没改训练内核，不等于与上游内部 train-data 结构无关。它还复用 `train_data['prompt']` 运输 MOPD teacher route 或 TQ layout，二者在当前 converter 中被明确判为不可同时使用。[C6]

对 RepoHarness 的启示不是也复制 converter，而是：**应把必要的跨层语义增量做窄、写测试，并明确谁承担与上游版本同步的成本。** 这是架构分析，不是已经比较维护成本的实验。

## 3. 真实 SWE launch 配置：不要从文件名猜实验

主入口是 `examples/scripts/run_dressage_swegym_qwen3.5_4b_claude_code_sync_4_node.sh`。[C1]

| 配置项 | 固定文件中的默认／明确设置 | 解释 |
| --- | --- | --- |
| 基座 | Qwen3.5-4B | 不是本项目 Qwen3-30B-A3B |
| trainer | `train.py`、`--colocate`、Dressage sync hook | 一批 rollout 完成后训练，不是这份脚本自动启用 fully async |
| 节点 | `ACTOR_NUM_NODES` 回退 `WORLD_SIZE`，再回退 1 | **文件名含 `4_node` 不证明默认四节点，更不证明历史实际用了四节点** |
| GPU/并行 | 默认每节点 8 GPU；TP2、CP4、PP1、EP1 | 配置不是硬件运行证明；GPU 型号和拓扑不能由文件名补齐 |
| 组与 batch | 8 prompts × 16 rollouts，GBS=128 | 128 是逻辑 rollout，不是最终 segment 行数 |
| 长度 | agent context=65536；response 参数=16000；Claude max turns=80；proxy steps=100 | agent turn、一次模型生成、segment cap、总轨迹 token 不是同一种预算 |
| compaction | 阈值由 context−8000 派生，默认 57536 | 是触发配置，不代表每个任务都实际压缩 |
| 优化 | Adam，lr=1e-6，weight decay=.1，betas=.9/.98，constant LR | CPU optimizer offload、overlap 与 precision-aware optimizer 也开启 |
| PG / TIS | clip=.2/.28；vanilla token TIS 开启，文档给 [0,2] | 不是本项目 faithful DIS；也不是单一 ratio |
| KL | reward-side kl_coef=0；单独 KL loss=.001，low_var_kl | “KL 系数为0”不能解释成完全没有 KL 正则 |
| advantage | group reward mean-centering；`NORMALIZE_ADVANTAGES` 默认1 | 后者还触发后端 token-mask 统计 whitening，见 §5.4 |
| 推理副本 | 默认每 engine 2 GPU，concurrency4，mem fraction .5，consistent_hashing | 与 Step Balance 实验的 8×单 GPU engine 不是同一个运行配置 |
| Step Balance | 这份脚本未显式加入相应启用参数 | 不能把7月模型结果归因给8月的调度改进 |
| TQ/R3 | TQ 通过开关选新入口；R3 另有字段与参数要求 | 功能能组合到什么范围，要看 converter 的互斥检查 |
| num_rollout | 默认500 | 不等于作者报告完整跑了500步；训练文本主要描述前80步 |

`blackbox_dispatch_swegym.generate()` 明确丢弃传入的 `sampling_params`；真正模型请求在 Proxy 的 `_build_sampling_params(body, max_output_tokens, rollout_temperature)` 构造。**这不代表采样温度被忽略**，而是说明查一个自定义 generate 参数不足以确定实际模型采样。后续若做按任务预算或温度调整，需要追到代理的最终请求。[C2]；[C13]

同步入口一次取得目标数量的题目组，不靠丢掉未完成尾部而补新题凑齐；内部虽并发执行，仍等所有组终结。失败可按配置整组重试，耗尽后保留无梯度占位；整个 batch 没有可训练 token 时默认拒绝训练，除非显式允许。该入口和 SWE generate 都拒绝 `evaluation=True`，所以不能把训练 hook 直接当作已完成评测接口。[C3]；[C4]

<a id="environment"></a>
## 4. 数据、环境与评分：有明确流水线，也有不同于 RH2 的失败语义

### 4.1 数据供给不是一条新的大规模 PR 生产论文

实验文本采用 `NovaSky-AI/SkyRL-v0-293-data` 中的 **293 train / 23 validation**，为 SWE-Gym 的已筛选子集。转换器根据官方 harness 的 TestSpec 生成执行脚本、测试解析及 F2P/P2P 信息，保存到 runtime metadata。这里主要是在已有任务上建立可执行 recipe，而不是披露从百万 PR 到可信任务的完整漏斗。[S1]

| 供给阶段 | 可以确认 | 未披露或未核验 |
| --- | --- | --- |
| 来源任务 | 293/23 子集与官方 harness pin | 原始候选如何淘汰、完整质量审查成本 |
| 数据转换 | prompt 与 runtime metadata；official script/parser/test target | 全量数据逐实例人工检查，本轮未下载核验 |
| 沙箱 | 复用任务原镜像，保持 `/testbed` 和依赖 | 每镜像实际构建成功率、平台账单和全量稳定性 |
| CLI/BBS runtime | 文档示例固定 Claude Code 2.1.207、BBS1.1.0、独立 Python3.10.20 runtime | 当前仓库代码与当时发布二进制是否逐字一致 |
| 训练信号 | fresh official harness 的二元 resolved | 没有展示该 reward 对所有合法替代解的充分性 |

E2B 路线为不同任务镜像建立 template；custom 路线要求 provider 真正消费 `sandbox_cmd`，等待健康检查，而不是等待前台 BBS 进程自然退出。按SWE guide说明，公开factory没有直接注册名为 `custom` 的provider；文档要求通过 `DRESSAGE_PADDOCK_CLASS` 注入。资源示例不等于实验真实资源统计。[S1]

### 4.2 三类完整性措施各自能做什么

**清理 Git 线索。** before-agent 阶段回到 base commit、detached HEAD，去 remotes、refs、reflogs 和不可达对象。`git clean -ffd` 不是 `-ffdx`；保留 ignored 缓存对任务可执行性有实际意义，也说明“清理工作区”需要具体解释。[S1]

**检测远程获取答案。** 轨迹中搜索访问任务仓库／配置相关 fork 的 clone/fetch/pull、curl、wget、gh 和 web 工具行为，命中则奖励归零。**这是事后完整性策略，不是网络执行层隔离，也不是已经证明无法绕过的访问控制。**[S1]

**保护测试与控制文件。** prompt、工具轨迹、最终 patch 均检查 tests、conftest、pytest.ini、tox.ini、setup.cfg、pyproject.toml 等路径；违反则 reward=0。[S1]；[C9]

这些政策与 RH2 的可信评分投影不同：RH2 已明确“修改测试路径不自动等于作弊”，并将候选 delta 与评分控制面分开。不能因为 Dressage 规则更严，就断言它的评分更正确。对于需要合法修改配置的任务，必须确认任务定义是否允许，以及严格路径规则是否造成 false negative。该问题是项目适配分析，不是本轮测得的误杀率。[RH]

### 4.3 fresh evaluator 的真实生命周期

`execute_fresh_swegym_eval()`：从原 sandbox 相对 base commit 提取 patch；空 patch、提取失败或禁止路径直接记录失败；否则新建 eval session，从同一镜像创建干净环境，注册 BBS、应用 patch，再运行 official harness；eval sandbox 在 `finally` 中终止。长评分通过后台命令加轮询完成，避免一个长 HTTP 请求承载全程。[C9]

**源 sandbox 并未在提取 patch 后立即释放。** `generate()` 先等待 fresh eval、代理 finalize、轨迹读取和 sample 构造，最后才安排源 sandbox 终止。因此在评分阶段源／评测环境可能同时存活。RH2 已选“冻结产物后立即释放源容器”，这是一个真实的架构差异；是否值得改变 Dressage 要看后续提取和诊断是否仍需要源状态，不能只凭峰值容器数认定多余。[C2]；[C9]；[RH]

### 4.4 零奖励不总意味着模型完成了一个合法失败尝试

reward parser 从规定的 `after_agent/swegym_harness` 命令结果中解析 `DRESSAGE_SWEGYM_REWARD_JSON=`。只有 `resolved is True` 才记1，其余0；随后完整性策略仍可将1改为0。[C10]

fresh evaluator 把若干 `httpx.HTTPError` 和 `TimeoutError` 转成 `fresh_eval_exception` 的失败记录并返回；missing marker、patch application failure 等也可以进入零奖励。与此同时，其他逃逸异常由外层 generate 标为 ABORTED，再走整组重试／无梯度处置。[C2]；[C9]；[C10]

因此应拆分三种语义：

| 事件 | 当前路径中的可能处置 | 需要保留的含义 |
| --- | --- | --- |
| official tests 真实失败 | reward0，通常仍训练 | 可验证的模型失败 |
| policy integrity 违规 | reward0 | 行为约束学习，而不是额外负数 penalty |
| 某些 grader 传输／超时／marker 失败 | 诊断记录 + reward0 | 不一定提供“修代码失败”的可靠证据 |
| 外层不可恢复异常 | ABORTED，组重试或 no-grad placeholder | 与上项并非统一分类 |

**“fresh sandbox”只描述隔离方式，不能替代失败归因。** 若某些仓库评分更慢且更容易触发错误，零奖励政策可能同时影响学习信号与任务分布。本文没有测出该现象的实际频率，不据此否定作者训练结果。

<a id="learning"></a>
## 5. 轨迹身份与实际训练目标

### 5.1 五种单位要分别看

| 名称 | 在本路径的含义 | 主要使用处 |
| --- | --- | --- |
| `instance_id` | 任务／题目标识 | prompt-equal denominator 聚合键 |
| `group_index` | 当前采样题目组 | GRPO reward mean/std 的分组键 |
| `session_id` / `parent_traj_id` | 一次逻辑 agent rollout | proxy history、terminal reward anchor、siblings |
| `rollout_id` | 展开时设为 template sample.index | slime 识别同一逻辑 rollout 的多个训练行 |
| `segment_index` | 上下文发生边界后的训练片段序号 | 排序、唯一性检查、terminal anchor |

`expand_segments_to_samples` 先按 segment index 排序，重复索引报错；每个 segment 深拷贝 template。末段保留待评分的 reward，前段设0。`reward_post_process` 只拿每个 parent 的最高 segment index 作为代表参加组统计，再向其余 segment 广播处理后的优势。[C5]；[C7]

**所有 segment 收到同一个终局优势，不等于细粒度过程信用已经解决。** 它解决的是拆分后怎样保持逻辑轨迹的基本消费语义，而非判断哪一轮导致成功。

### 5.2 token-faithful 接入仍然有模型与失败边界

Proxy 请求路径在 session request lock 内操作：校验 session/epoch，比较历史是否 append-only、tools hash 是否变化，选择 lineage；构造输入 token 后调用 `/generate`；保存真实 output ids、logprobs 和版本，再把适合 CLI 的文本／工具调用返回。[C13]

历史重写、工具变化、prefix mismatch、增量 token 构造失败都会影响边界。发生某些构造失败时，代码采用 full-prompt safety reset，并记录边界原因，而不是继续假装原输入前缀完全相同。**这是一种显式的恢复路径，不是证明任意 renderer 在任意模型下均无漂移。**[C13]

当前资料的 TITO 支持集中在 Qwen3.5／Qwen3.6 家族；本篇不把它自动外推到用户当前 Qwen3-30B-A3B、任意 tokenizer 或所有 Claude 子代理路径。Claude adapter 默认为 subagents disabled，设置继承凭据清理、独立 HOME/CONFIG/TMP、thinking 和 compaction 配置；这说明所谓“真实 CLI”仍处于明确定制的运行配置中。[S0]；[S3]；[C15]

注意 **Claude 的 prompt-cache 开关与 SGLang KV/HiCache 不是同一个缓存**；不能从 adapter 禁用 Anthropic prompt caching 推出后端没有可复用 KV。

### 5.3 Sample writer：训练片段可能再被裁剪

`write_sample_from_segment` 校验 tokens、full_loss_mask、full_logprobs 长度；loss mask 只允许0/1，路由重放开启时还要求相应 routed experts。response_start 取原始 mask 的第一个1，后面的 response 区间可以包含 mask0的工具观测，**response_length 不等于动作 token 数**。[C8]

它另按 `max_tokens_per_gpu × CP` 从前方保留 token 前缀；裁剪会写 `metadata['truncated']=True`，但 Sample.status 最后只根据 segment.finish_reason 是否为 `length` 设置。因此 **物理裁剪标记与 trainer 的 status-based truncated 字段可以不同**。这在正常长度配置匹配时未必触发；若改变 trainer 容量而不改变 agent 预算，应单独验证 reward、截断标志与有效动作的对应关系。[C8]；[C6]

`mask_nonlast_version_tokens` 保留的是该 segment 中最后一个真实 output version 的 token，并不是自动保留“当前 learner 最新版本”。工具／输入占位版本、跨 generation 暂停恢复和多个 segment 必须分别解释。当前函数也不会因为 mask 全零就自动把 `remove_sample` 设为True。[C8]

### 5.4 组均值与后端 whitening 是两个操作

以题目采样组 $g$ 的未移除 parent rewards $r_i$ 表示，reward hook 先计算：

$$
a_i=r_i-\frac{1}{|g|}\sum_{j\in g}r_j.
$$

GRPO／GSPO 在 `grpo_std_normalization=True` 时可再除以总体标准差；默认该开关为False。raw_rewards 保持稀疏：仅 anchor 有终局 reward，避免将一条多段轨迹的 raw reward 重复计数。[C7]

但真实 launch 默认同时打开 `--normalize-advantages`。pinned slime 的 `compute_advantages_and_returns()` 在将 scalar reward 展为 token returns/advantages 后，还会基于 loss mask 做跨 DP 统计的 whitening；CP 情况另切局部 mask。因此，**不能把“关闭组内 std normalization”写成“整个训练没有任何优势标准化”**。[C1]；[U2]

这会使有效 token 分布影响 whitening 统计。两次统计的权重与归一化分母都需要保留，不能只抄 reward_post_process 的数值作为最终进入 PG 的优势。

### 5.5 prompt-equal denominator：不是 trajectory-equal

Dressage 的 GRPO／Reinforce++ baseline 路径以 `instance_id` 聚合：

$$
M_p=\sum_{s:\,instance(s)=p,\,\neg remove(s)}\sum_t m_{s,t},\qquad
N_p=\#\{p:\exists\text{未被 remove 的 sample}\},
$$

$$
D_s=M_{instance(s)}\frac{N_p}{B},\qquad B=global\_batch\_size.
$$

各 segment 获得整步预计算的同一个题目分母，再由后端按相应分片累加。**只有在使用对应 sample-mean 路径、后端按该 GBS 还原全局尺度且 $D_s\ge1$ 等条件下**，才能化成常见的题目等权表达：

$$
L=\frac{1}{N_p}\sum_p\frac{\sum_{s\in p,t}m_{s,t}\ell_{s,t}}{M_p}.
$$

这里 $\ell$ 已包含实际优势、PG clipping/TIS 等影响；这不是本篇新算法，也不是完整分布式梯度复现。pinned slime 的 reducer 实际使用 `clamp_min(denom,1)`，小分母时上面的化简不成立；若启用 per-token-loss 路径，又改为另一种归约方式。[C6]；[U1]

**三点重要后果：**

其一，同一题下所有有效动作 token 共同归一化，不等于先对每条轨迹算平均再对轨迹平均。不同长度的轨迹可以获得不同总权重。

其二，单纯改变 segment 切分、且不改变动作 token 与权重时，预计算分母可保持一致；但若拆分同时复制 trainable 前缀、改变 mask 或移除部分轨迹，就不是同一份经验的简单重排。

其三，`N_p` 的判定是未 remove，而不是“至少存在一个 mask=1”。一个 mask全零但 remove=False 的独立题目仍可扩大其他题目的分母。CPU 探针确认了这一函数行为，是否符合目标需与 no-gradient 策略共同判断，不自动定性为 bug。[C6]；[P0]

组统计使用 `group_index`，分母使用 `instance_id`。同一个任务在一批中出现多个不同采样组时，会有不同 baseline，却可能共用一个题目分母。代码只检查活样本 group_index 不为None，没有在这个函数中检查二者的一对一关系。这样设计可能有意让同一任务等权，不能擅自“修正”，但需要明确实验单位。[C6]；[C7]

### 5.6 三套概率与两类正则

pinned slime 的实际 PG 路径区分：当前训练 logprob、更新前训练侧 logprob、rollout logprob。PPO 比率由当前／old 产生；vanilla TIS 另计算：

$$
w_t=\operatorname{clip}\left(\exp(\log\pi_{old,train}(a_t)-\log\pi_{rollout}(a_t)),\;0,\;2\right),
$$

再乘到已计算的 PG token loss 上。KL loss 单独比较当前 logprob 与 reference logprob。TIS 的默认夹值来源为 SWE 文档；公式与应用位置回查了 pinned backend，而不是从方法名猜测。[S1]；[U2]

所以这份 recipe **不是“直接拿 rollout probability 作 PPO old，然后再套本项目 DIS”**。reward-side KL=0 与KL loss=.001也应分别保留。TIS路径要求batch里存在 rollout_log_probs；若缺字段，会在后端断言，而非自动变成正确 on-policy 训练。[U2]

### 5.7 失败占位与一个被下调的疑点

converter 用 `samples[0].rollout_log_probs is not None` 判断是否输出整批 rollout logprob 字段。CPU 反例显示：首样本为None、其余样本有概率时，字段可整体缺失；反转顺序后则出现带None的列表。[C6]；[P0]

**但不能把它直接报告成真实 SWE 主路径 bug。** 继续追查 `_mark_no_grad_failed()` 后确认：正式失败占位将 response_length 设0、mask设空、rollout_log_probs设 **`[]` 而不是None**，同时 remove=True。补充的第25个探针确认该占位格式保留批级字段。因此它首先是“converter 接口对异构输入的前提和未来扩展风险”，不是本轮已复现的主链故障。[C4]；[P0]

这也说明测试需要同时包含能触发疑点的反例与实际生产者输出，不能为了找 PR 忽略上游已经满足的约定。

<a id="balance"></a>
## 6. Step Balance：局部性、长尾与可恢复状态之间的取舍

### 6.1 它移动的是什么

基线通过 `X-SMG-Routing-Key=session_id` 和 consistent_hashing 保持 session 亲和。好处是同一 agent 后续请求可复用缓存；问题是未知的轨迹长度使少数 engine 在后半程持续繁忙，而其他 engine 提前空闲。[S2]

Step Balance 在**下一次 generation step 到达**时选择 engine，不抢占并迁移正在 decode 的请求，也不把同一串行 agent 的未来动作提前并行。若最后只剩一条轨迹，它不能凭八张卡把依赖串行的八个未来 turn 同时执行；其机会来自还有多个待执行／后续到达的 step 可以重新分布。

Proxy 始终传完整 input_ids，实际命中多少 prefix 由 SGLang 决定。Dressage 不自己实现 KV 传输 kernel；HiCache／Mooncake 是可选恢复路径。模型含 Mamba/linear state 时，恢复对象也不只是普通 dense-attention KV；profile／fingerprint需要反映实际结构。[S2]；[C11]

### 6.2 调度不是“找最闲 engine”一个 if

固定版本的关键顺序如下：[C11]

```text
启动 → 机器／传输校准 → 释放校准占用的 Ray/GPU 资源
     → 发布 READY 或 DEGRADED → engine discovery + 独立负载轮询

每次 generation：
  等待初始快照的有限窗口
  → session / owner / expected version / fingerprint 检查
  → fresh candidate 与可恢复路径筛选
  → snapshot + 尚未被快照覆盖的 local deltas
  → greedy pressure + owner hysteresis
  → 保留 reservation → 将请求送给所选 engine
  → 成功才更新 owner 和 committed token prefix
  → 失败或结束释放 reservation
```

其余控制路径很重要：停机取消 calibration／poll tasks 并清理；首次没有快照只有限等待；失败的校准可降级，而不是永久等待；正常请求不逐次同步查询所有 engine。

### 6.3 compatibility、load freshness 与恢复可行性是三道不同检查

`EngineDeploymentInfo` 的 fingerprint 包含模型、weight_version、SGLang版本、TP/PP/DP、KV/state dtype、page/SWA、Mamba配置、HiCache 和 Mooncake 参数。当前最低版本检查为 SGLang **0.5.15.post1**。这是一份配置兼容身份，不是实际内存权重逐字一致的证明。[C11]

owner健康但快照过期时，代码保留owner，不用陈旧指标主动迁移。新session／强制failover缺新鲜快照时可稳定哈希选择健康候选；没有eligible engine时也可能返回 `worker_url=None`，交回普通 router。**这不是“没有候选就必定 fail-closed”。**[C11]

但另一路 generation controller 会在请求明确带 `expected_version` 时，核对实际响应版本，缺失／不同则报错；server还检查epoch和跨版本轨迹。所以“调度 fallback”也不能直接推成“版本保护全部失效”。expected version 是否传入、partial rollout开关和response校验是不同边界。[C13]；[C14]

健康owner之间的**自愿迁移**要求同兼容fingerprint、fresh负载，并通过共享Mooncake路径的readiness。没有L3或校准未完成时，自愿迁移通常被过滤；新session放置和必须failover仍可能full-prefill。**“无L3也能运行”与“无L3也有同样的重平衡收益”完全不同。**[C11]

### 6.4 快照与局部预留：正确名称是估计，不是精确在途计数

每个健康engine至多有一个在途 `/v1/loads` 探针，1秒timeout；实验轮询间隔60ms。discovery与deployment刷新另走控制循环，deployment检查间隔在当前代码为10秒。慢或失败的engine探针不让所有engine逐次串行阻塞。[C11]

一次load fetch开始前记录scoring revision。收到合法、拓扑未变的快照时，旧revision的local deltas标记为已覆盖；fetch开始后增加的reservation继续计入。fetch失败则不错误清空这些增量。这比“每poll一次清零本地计数”更细。[C11]

**但revision边界不是engine逐请求ack。** 若某个已reserve请求尚未真正到达engine，快照可能仍不包含它。当前机制依靠dispatch／观测时序近似覆盖，而不是为每个请求证明已被观测。它适合作为压力估计，不能被宣传为严格线性一致的容量账本；本轮未测该窗口在实际网络上的影响。

报告描述了生命周期预留的 `prompt+N_out` 与page-aligned prefill估计；当前 `scheduler.py::_ReservationEntry` 实际只有engine、scoring queue/token增量、revision和active。**在这个调度器中没有找到报告所述那套生命周期容量字段。** generation controller 的active request表也不等于同一个容量预留公式。本文保留文档—代码差异，不把两套口径暗中合并。[S2]；[C11]

### 6.5 精确 pressure 公式与迁移规则

记快照running为 $R_e$、active tokens加未确认token增量为 $N_e$、waiting加未确认queue增量为 $Q_e$。对新到达step：

$$
\Delta Q=1,\qquad
\Delta N_e=\begin{cases}
\max(0,|input|-LCP),& e\text{为健康owner},\\
|input|,& \text{新会话／迁移／failover}.
\end{cases}
$$

$$
P_e=\frac{R_e}{C_{req,e}}
+\max\left(\frac{N_e+\Delta N_e}{C_{token,e}},u_e\right)
+\frac{Q_e+1}{C_{req,e}}.
$$

$u_e$ 为engine报告的token_usage。选最小压力；差值在 `1e-7` 内视为tie，优先保留owner，否则使用session和engine URL的稳定SHA256顺序。已有session还要求：

$$
\frac{P_{owner}-P_{best}}{\max(P_{owner},10^{-9})}\ge\theta,
\qquad P_{best}<P_{owner}-10^{-7}.
$$

默认 $\theta=.10$，new/failover不受此门槛。源码拒绝非有限／负压力、无效容量、重复edge和错误session边。以上公式均来自当前 `greedy.py` 与其调用，而不是我们发明的scheduler。[C11]；[C12]

**关键解释：这个压力是无量纲启发式，不是预计剩余毫秒。** 校准用于判定恢复链路可用，实际greedy比较没有直接代入本次transfer latency、预计输出长度或完整恢复成本模型。报告“足够收益覆盖迁移开销”的叙事应理解为设计意图和条件，不能读成逐请求已验证的收益保证。[S2]；[C11]；[C12]

owner使用LCP降低token增量，migrant即使可能从L3恢复也按full prompt计压力：这是保守的placement估计，不等于目标实际重算全部prefix，更不等于实际KV命中统计。反过来，owner的LCP也不能证明其缓存尚未被淘汰。

### 6.6 reservation 与异常路径

`acquire()` 在锁内记录session、reservation和scoring revision。调度抛异常时回滚本次新增状态并记录失败决策；`complete()`先释放reservation，成功时才提交owner与prefix；`fail()`仅释放不改成功owner。Proxy使用session request lock序列化同session请求，并在生成异常时settle失败lease。[C11]；[C13]

因此不能仅看scheduler本身“没有阻止同session并发”就报告竞态：它的真实调用者承担了锁。另一方面，只有读了调用者才能知道生成成功后的settle失败被日志记录并允许继续，不能把每一项监控／归属更新失败都描述为run-fatal。[C13]

### 6.7 未来工作不能计入已实现能力

报告最后提出短窗口多step MILP、先最小化最大压力再最小化迁移成本，以及PD分离下的P→KV→D路径压力。这些是**future work**。当前代码的默认路径是single-step greedy；没有因为文档出现MILP公式就实现联合全局调度。[S2]

即使MILP在其模型中优于某个greedy解，也不等于真实系统的time-to-completion全局最优：快照、代价估计、等待成批的延迟和不可预知输出仍是外部条件。原报告自身保留了这一限定。

<a id="evidence"></a>
## 7. 报告结果：把训练、调度、容量分析分成三类

### 7.1 SWE 模型训练

| 项目 | 官方文本 | 本轮能支持什么 |
| --- | --- | --- |
| 训练数据 | 293 train / 23 validation | 一条小规模真实SWE recipe，不代表全SWE-Gym生产线 |
| 训练reward | 前80步约 .27 上升到 .6以上 | 作者报告的训练趋势；曲线图片本轮未目视复核 |
| logprob差值 | 约 .009–.011 | 某诊断指标稳定，不证明训推逐token一致 |
| grad norm | 后期约 .3 | 运行诊断，不证明每一处mask或group计算正确 |
| SWE-bench Verified | Qwen3.5-4B：32.6%→37.8%，+5.2pp | 作者报告的训练前后模型结果 |
| 评测harness与预算 | Claude Code，256K context，最多160steps | 与64K/80turns训练设置不同，需分别记录 |
| 成本与统计 | 未充分给出GPU型号、总GPU-hour、API/环境账单、种子/CI、完整逐题清单 | 不能写作八卡30B预算或独立复现 |

没有找到把工具、数据筛选、TIS、prompt-equal reduction、失败策略与Step Balance逐个隔离的模型消融。因此最稳妥的归因是**整份公开recipe的作者报告结果**。[S1]

### 7.2 Step Balance 的同步 rollout 对照

| 条件 | 原报告 |
| --- | --- |
| 模型与硬件布局 | 单机8GPU，Qwen3.5-4B，8个单GPU engine；正文未标GPU具体型号 |
| 请求 | batch256，n=1，temperature0；作者称模型、数据、random seed和推理配置相同 |
| 长度 | 256K context，4K response |
| cache | HiCache ratio2，write_through，page_first_direct；Mooncake segment size64GB |
| 工作负载 | 来自内部压力形态抽象的A/B/C：不同短轨迹与长尾混合 |
| 阈值 | A/B用0.0，C用0.1；不是三组都运行默认0.1 |
| Effective TPS/GPU | 作者报告 +39.4%–64.2% |
| rollout时间 | README报告 −28.2%–38.9%；正文例子B为3.19h→2.08h |
| load dispersion | per-engine step分布CV最高约38%降到2%以下 |
| 观察解释 | 前段双方接近饱和，主要收益来自尾段减少空闲engine等待 |

来源：[S0]；[S2]。B例子的算术是约 **1.534×速度、34.8%时间减少**，不是把34.8%再称为1.348×。

正文未给出所有指标的计算脚本、原始任务/长度manifest、重复次数和CI；本轮又未取得完整原图，因此不从图推A/B/C逐项精确值。**Effective TPS/GPU的精确token计数边界、GPU Spread的计算方式也不能靠名称自行补齐。** 已知正文说明是有效token吞吐和跨engine离散度，进一步精确复核需要原始脚本／图页。

这个工作负载有意研究长尾分配，能够支持该配置上的调度论证，但不是完整真实SWE训练：没有展示本对照中更新模型权重、组内n=16采样、梯度一致性或固定预算held-out质量。temperature0和固定seed也不保证不同batch/cache顺序完全相同，需要实际轨迹检查。

### 7.3 哪些headline不属于本次主实验

README中的TransferQueue **两节点Qwen3.6约67%内存降低**与**32节点GLM-5.2约91%容量分析**是不同证据种类；Claw训练、Harbor、多教师共享buffer也是其他范围。本稿只读它们的架构／发布概览，不把它们计入主SWE recipe或Step Balance对照，不据此声称所有功能已共同训练成功。[S0]

## 8. 一个系统性限制：同步尾部加速为什么不能直接等同 fully async 收益

**以下是依据前述机制的项目分析，不是Dressage报告的新增实验。**

同步batch必须等最慢组，所以最后几条长轨迹造成的idle有直接壁钟代价。fully async可继续从新题中补工作，GPU可能不因某个batch尾部而空闲；此时更好的step placement仍可能降低单轨迹时延、staleness和内存驻留，但也可能增加恢复流量或重复prefill。

应区分至少四个计量：generation step吞吐、完整逻辑轨迹吞吐、实际被learner接受的有效组吞吐、固定总预算的验证质量。迁移改善第一个，不自动改善最后三个。

对于单机8×96GB目标，30B总参数／3B激活仍需存储全模型；engine数量由训练／推理分配与TP决定，未必存在8个可迁移目标。**只有一个推理engine时，跨engineStep Balance没有目标；只有两个时，收益形态也不同于8副本。** 无NVLink并不自动排除主机／L3恢复，但必须实测H2D、缓存容量、带宽竞争和模型状态兼容，不能由8GPU字样等同资源条件。

<a id="probes"></a>
## 9. 本轮实际执行的25个CPU探针

可复用脚本：[checks/dressage_cpu_probes_20260908.py](checks/dressage_cpu_probes_20260908.py)；实际输出：[checks/dressage_cpu_results_20260908.json](checks/dressage_cpu_results_20260908.json)。

```bash
python checks/dressage_cpu_probes_20260908.py \
  --source-root /path/to/Dressage-at-3e3142fe \
  --output dressage_cpu_results.json
```

**执行环境：Python3.13.5 + numpy，CPU。** 使用从GitHub取得的三个源文件；执行前校验Git blob：

| 文件 | 校验通过的blob SHA |
| --- | --- |
| `proxy/rebalancing/greedy.py` | `8d1bfe709461e29ee556873b6ceb29ba2edb2b21` |
| `training/reward_post_process.py` | `4b47ae8a944af45354cf993d4170f79d8f098941` |
| `rollout/convert_samples.py` | `646dee74c2b0c410f7cca1b41f57cba60ef48253` |

这些原文件只在本地检查，不作为第三方源码副本提交阅读库。脚本用独立模块加载，避免执行heavy package initializer；Sample为明确的轻量替身，transport只替换已知metadata-key常量。**没有把TQ、Ray或SGLang stub成“已经工作”。**

| 探针组 | 实际验证 | 结果及意义 |
| --- | --- | --- |
| 1–11 路由纯函数 | pressure=.72、usage floor、new placement、hysteresis、tie、failover、stable hash、非法输入、locality代价 | 全通过；owner=.411而冷target=1.01的例子说明idle并不自动优先 |
| 12–16 reward | terminal anchor、sibling广播、raw稀疏、parent而非segment计组、removed排除、std开关 | 全通过；不把奖励日志平均与训练优势混用 |
| 17–20 denominator | 同题跨轨迹池化、等token拆分、零mask未remove题目、缺身份 | 全通过；零masklive题目仍扩大N_p是实际函数行为 |
| 21–23 接口边界 | 首样本None的logprob顺序敏感、同instance多group分母合并、TQ与MOPD互斥 | 全通过；验证边界存在，不等于默认主路径触发 |
| 24 加权代数 | 使用真实denominator helper比较prompt池化和trajectory均值 | 示例分别−.25与0；不是后端梯度或训练效果 |
| 25 正式失败占位反例 | 用`_mark_no_grad_failed`实际约定的空logprob列表格式 | 字段保留，不能把第21项直接作为真实SWE故障报告 |

**25通过意味着上述断言与固定代码一致，不意味着Dressage整体“25项可靠性认证”。** 本轮没有执行官方全部pytest、distributed loss、真实缓存迁移、故障恢复、网络隔离或模型训练；不作独立复现标签。

## 10. 文档与代码核验后的维护机会

| 事项 | 当前证据 | 合理下一步 | 本轮没有做什么 |
| --- | --- | --- | --- |
| 报告的生命周期reserve字段与当前scheduler结构不同 | 完整读报告及scheduler | 明确是历史设计、其他层实现还是已删除；更新文档／补对应测试 | 未发布“资源超卖bug” |
| `instance_id`与`group_index`分别用于loss与优势 | 函数与CPU反例 | 用同一任务多次采样组检查预期权重，写接口约定 | 不擅自合并或拆分组 |
| 零mask但未remove的题目影响分母 | CPU实测 | 明确全零segment/parent/prompt的预期处理，补目标级测试 | 未断言必须删这些任务 |
| 裁剪metadata与status不同步 | sample writer＋converter静态路径 | 构造token_cap低于已完成segment的实际Sample，核reward/truncated/loss消费 | 未运行真实trainer裁剪实验 |
| 混合None logprob顺序敏感 | CPU边界可复现；主失败占位用[]规避 | 新adapter/TQ路径若允许None再加校验，避免破坏正常空序列 | 未宣称主recipe丢概率 |
| 源沙箱保留至fresh eval之后 | generate/evaluator控制流 | 量化评分期间重叠容器成本及诊断依赖 | 未擅自提前销毁环境 |
| load revision并非逐请求ack | scheduler结构推论 | 模拟延迟dispatch与poll边界，检查短时估计误差 | 未构建持久账本或新的控制平台 |

**这些是贡献候选，不是“已经找到七个可直接提交的bug”。** 真正向上游提PR前，需要重查主分支、已有issue/PR、维护者预期和最小复现。本轮不创建外部issue／PR，也没有全面检索当前全部维护历史。能解释某设计是有意取舍，也是一项有效阅读结论。

<a id="project"></a>
## 11. 对 RepoHarness 的取舍建议

### 11.1 最有价值的启示：不要把“外层框架”低估成接线

Dressage的结构说明：基于成熟trainer仍然可以围绕真实harness执行、segment组织、运行资源和实验协议形成实质工程工作。但它也意味着**“有TITO、有multi-segment、有fresh grader、有异步”本身已经不是差异化终点**。我们需要证明自己的明确增量，而不是增加同类组件。[S0]；[S1]；[S3]

RH2当前已选择miles负责异步与consume-time staleness，vendored slime负责agent adapter，自己的资格、评分和loss合同有已定边界。本文不会因为Dressage另建某层，就批准替换或复制整层；尤其不把当前正式候选改成另一个sticky routing／dead-engine平台。[RH]

### 11.2 三个最值得保留的小实验

| 顺序 | 问题 | 最小做法 | 成立时才考虑的改动 |
| --- | --- | --- | --- |
| A：已有轨迹的成本分解 | 实际瓶颈是engine局部热点，还是环境／评分／组等待？ | 固定若干真实SWE任务，分别记录生成、工具、评分、有效组消费及engine尾部；先不改scheduler | 只有跨engine热点与可用空闲容量同时存在，才考虑placement |
| B：明确训练单位 | 同一逻辑轨迹的切分／mask／组身份是否改变了声明的目标？ | 固定轨迹与参考计算，比较RH2当前分母、Dressage prompt-pool及必要baseline；保持token集合一致 | 只修不符合已声明目标的错误，不把不同目标当bug |
| C：缓存恢复与迁移的净收益 | 本机目标模型的恢复代价是否低于减少的排队？ | 先测相同固定权重／token的owner、cold target、可恢复target；记录TTFT、prefill、命中、字节、response parity和总用时 | 若存在稳定净收益，再用最小调度实验，不先造MILP |

A与C应按本机实际engine数量、TP与模型结构做；B可以先CPU／离线完成。模型行为／数据选择发生变化时才需要进一步在线学习对照；语义保持的局部系统优化可以先由固定输入正确性与性能证据支持，不强迫每一项都另训练“新能力”。

### 11.3 必须设强基线，避免把额外组件当作收益来源

若测试routing，至少比较当前合理配置的miles/router，而非故意制造热点的弱基线。固定模型、任务、工具预算和评分；实际工作负载与报告式压力分布分开。缓存服务的CPU内存、启动／校准、H2D与重算都计入成本；迁移失败、fallback和stale丢弃不能从统计中消失。

若减少step壁钟，却降低valid-group/GPU-hour或固定预算的held-out收益，优化不能仅靠更高GPU utilization判定成功。反之，如果只是让资源更早释放而不改变学习样本，清楚的资源曲线也足以构成工程成果，不必把它包装成新优化算法。

### 11.4 暂不建议直接移植的内容

**不立即移植整套Step Balance。** 当前RH2多engine拓扑、负载形态和恢复路径尚无本轮实测；miles可能已有相应能力或更合适的扩展点。

**不改成Dressage的prompt-equal目标。** RH2 faithful DIS分母是另一份已定语义，差异需要实验而非复制替换。

**不照搬“所有grader错误都0分”或禁止所有测试／配置改动。** 两者都改变了训练任务与数据含义，需要依照RH2可信投影和失败分类来判断。

**不把MOPD、TQ、R3同时列成已完成配方。** 当前源文件有明确组合限制；本稿也没深审这些分支，不得将主recipe之外的能力补成共同训练证据。

## 12. 当前仍缺什么

| 缺口 | 类型 | 后续复核入口 |
| --- | --- | --- |
| Step Balance原始图表的目视核验 | 本轮访问限制，不是作者未公开 | S2中Figure4–8及对应assets |
| SWE训练曲线原图 | 同上 | S1／README链接图片 |
| 性能原始任务manifest、指标计算、重复次数与完整费用 | 在已读报告文本中未充分披露 | 作者公开脚本或补充日志；不能自行估计 |
| July训练实际代码／二进制与August main的严格对应 | 未证实 | 固定训练release／记录，而非当前README |
| 三层cache真实恢复、linear-state兼容和数值一致性 | 未执行 | 实际SGLang/HiCache/Mooncake与目标模型 |
| 25函数探针以外的官方测试与分布式更新 | 未执行 | upstream suite、短GPU parity作业 |
| 全量SWE评分／合法替代解／网络隔离 | 不属于本轮完成的安全审计 | 任务级检查与运行时测试 |
| 独立reviewer | 本轮不存在 | 由真实独立Codex／另一线程复核 |

**完成状态：核心文档文本精读、指定源码路径精读、25项CPU函数探针和作者自查完成；图像／分布式／真实模型实验及独立审查未完成。** 这个状态比“全部源码都精读过”更准确，也允许后续只补具体缺口。

<a id="references"></a>
## 13. 固定来源、关键函数与维护入口

| 代号 | 来源／函数 | 主要定位 |
| --- | --- | --- |
| S0 | README | 架构、News、TITO、training recipes |
| S1 | SWE-Gym + Claude Code实验文章 | 数据、环境、反作弊、Experiment Setup与结果 |
| S2 | Engine rebalancing report | §01–06，公式、Evaluation、Future Work |
| S3 | training.md | multi-segment、advantage、prompt-equal、staleness |
| C1 | 真实SWE同步脚本 | TRAIN_ENTRY、PROXY/ROLLOUT/GRPO/PERF_ARGS与默认环境变量 |
| C2/C3/C4 | generate、sync、fully_async共享helper | `generate`、`_run_sync_rollout`、`_mark_no_grad_failed` |
| C5/C6/C7/C8 | segment、converter、reward、sample writer | 全部关键函数，正文已对应 |
| C9/C10 | fresh evaluator与reward parser | `execute_fresh_swegym_eval`、`swegym_harness_marker_reward` |
| C11/C12 | Step Balance | scheduler全文件、greedy全文件 |
| C13/C14 | 实际请求／生成控制 | server约1960–2425；controller约220–530 |
| C15 | Claude Code adapter | options/settings/env约1–220 |
| C16 | custom reward入口 | reward未预填时交回slime赋值，不写proxy状态 |
| U1/U2 | pinned slime reducer／loss | sample-denom、whitening、vanilla TIS、policy loss |
| T1/T2 | upstream tests | greedy全文、converter前230行；仅阅读，非全suite运行 |

作者自查详见 [reviews/dressage_self_check_20260908.md](reviews/dressage_self_check_20260908.md)。与既有 [SkyRL-Agent](O01_skyrl_agent_sa_swe.md)、[miles](N11_miles_agentic_rollout.md)、[Forge](N10_minimax_forge.md) 笔记比较时，先按本篇固定代码与训练对象对齐；不让同名“异步”“TITO”或“归一化”代替实际定义。

本篇及专属检查文件是维护入口。本轮不改共享README／来源总表、不重计其他线程完成状态，不改训练实现或项目定案；汇总线程可按上述完成范围登记。

[S0]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/README.md
[S1]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/docs/blackbox-swegym-claude-code-experiment-en.md
[S2]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/docs/engine-rebalancing-report-en.md
[S3]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/docs/training.md
[C1]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/examples/scripts/run_dressage_swegym_qwen3.5_4b_claude_code_sync_4_node.sh
[C2]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/rollout/generate/blackbox_dispatch_swegym.py
[C3]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/rollout/sync_rollout.py
[C4]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/rollout/fully_async_rollout.py#L240-L265
[C5]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/rollout/multi_segment.py
[C6]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/rollout/convert_samples.py
[C7]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/training/reward_post_process.py
[C8]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/rollout/artifacts/samples.py
[C9]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/recipes/swegym/evaluator.py
[C10]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/recipes/swegym/reward.py
[C11]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/proxy/rebalancing/scheduler.py
[C12]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/proxy/rebalancing/greedy.py
[C13]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/proxy/server.py#L1960-L2425
[C14]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/proxy/generation_controller.py#L220-L530
[C15]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/blackbox_server/adapters/claude_code.py#L1-L220
[C16]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/dressage/reward/custom_rm.py
[U1]: https://github.com/THUDM/slime/blob/aaf5c2092b01219fa0d5c2d323741d409086ca32/slime/backends/megatron_utils/cp_utils.py#L49-L177
[U2]: https://github.com/THUDM/slime/blob/aaf5c2092b01219fa0d5c2d323741d409086ca32/slime/backends/megatron_utils/loss.py#L661-L1123
[T1]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/tests/test_greedy.py
[T2]: https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/tests/test_convert_samples_multi_segment.py
[RH]: https://github.com/Rogerffff/RepoHarness/blob/32b615c4e4f869b448174e5974e7a8d29fc4612c/docs/agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md
[P0]: checks/dressage_cpu_results_20260908.json
