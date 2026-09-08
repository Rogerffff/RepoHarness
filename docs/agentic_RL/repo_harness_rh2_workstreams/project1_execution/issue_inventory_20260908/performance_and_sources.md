# 项目一旧问题库存：吞吐、维护面与相关资料

日期：2026-09-08。主仓读取基线：`17d9899c`。本文只整理 2026-09-05 审查及 09-06 交叉复核中的旧主题，定点复读现有代码锚点和六篇新增笔记；不开展新审计、不改实现、不跑 GPU／Docker／全套测试、不删除文件。本文不是修复授权或训练验收。

## 1. 证据口径与结论边界

原报告中的“存在成本”“成本已测量”“可以删掉”“可以无语义变化地删掉”是四个不同命题。当前最充分的性能证据是 **R3 同步捕获的 CPU 探针、重复 chown 的 shell 复现，以及额外 actor forward 的窄配置等价探针**。其余多数是生产调用位置加条件估算，需在已有 GPU 资格作业中测量；不能汇总成一个已经证明的节省百分比。

本轮材料优先顺序：

1. [09-06 交叉复核](../../miles_spike/external_infra_review_crosscheck_20260906.md)及 [Claude 总报告顶部 09-07 勘误](../../tmp/external_review_20260905/00_FINAL_REVIEW.md)。它们覆盖旧切片中的冲突结论。
2. [09-05 Codex 独立审查](../../miles_spike/external_infra_review_20260905.md)，其中 F1、C1 等仍保留各自证据范围。
3. Claude 原切片 [B：执行路径](../../tmp/external_review_20260905/report_B_rollout_path.md)、[E：冗余](../../tmp/external_review_20260905/report_E_dead_code_bloat.md)、[F：miles fork／关停](../../tmp/external_review_20260905/report_F_miles_fork_shutdown.md)、[G：外部对照](../../tmp/external_review_20260905/report_G_frontier_gap.md)，用于保留尚未裁决的线索。
4. 本文 §4 的 Pro 笔记只提供阅读入口与候选解释，不替代项目代码证据、独立论文复核或本机实验。

代码位置沿用旧审查且对主要性能锚点作了定点复读；没有据此宣称每个旧静态判断均已独立证实。下文 `R/` 指 `rh2/src/repoharness2/`，`V/` 指 `rh2/src/slime/`，`M/` 指 `reference/miles-rh2-integration/`；这些是仓库相对位置。旧文中的 302 commits、行数、clone 体积、skip 比例均保留 **2026-09-05 快照** 身份，不当作今天重新测量的统计。

## 2. 性能问题：按因果机制去重

### P01：R3 张量反复转换与逐轮双份保留

- **旧条目**：Codex F1；B F-04；F F-06 中大 tape 成本的捕获侧。R3 是记录并重放 MoE expert 路由；它不是普通小型 metadata。
- **机制与锚点**：`R/adapters/slime/capture_wire.py:737` 同步调用 hook；`projection.py:171` 把 int32 bytes 解为 Python list；`generate.py:950` 对完整 meta 再做 canonical JSON digest，`:967–988` 同时保存 packed bytes 与 routing tuple，`:4732` 最后逐 artifact 写盘。没有逐轮释放。请求返回全前缀 routing，规模随上下文增长。
- **数值例子**：32,768 行×48 层×8 路由项×4B=48 MiB 原始 tape，base64 为64 MiB。仅 tuple 指针与 packed bytes 的常驻下限就是144 MiB，未含原 JSON、临时 list 或额外整数对象。旧真实 registry/hook 探针在8K／16K／32K行测到86／172／346 ms同步 commit；同 loop callback 等量延迟，另一次测得约74／150／294 ms。此处不能沿用 B 的“每轮3–6秒”作为实测。
- **内存估算边界**：50轮×平均16K行×48×8×12B×32个存活 execution=112.5 GiB，只是条件估算；没有当前作业 RSS／OOM／GPU 吞吐证据。buffer 的 group 容量也不是整个进程的内存上限，在飞 member、评分等待对象和其 artifact 仍占内存。
- **是否可删**：可讨论紧凑 bytes／int32 表示、减少重复序列化；不能直接删所有早轮 tape 或只留整个 session 最后一轮。不同 fan-out leaf 可能各需不同末轮，原路由来源、逐轮审计产物和落盘合同也不能一起悄悄改变。移到线程涉及提交次序与 GIL，不能称为无风险五行修复。
- **仍需查证／最小验收**：固定 token、shape、route ID、digest、分支结果，比较 retained bytes 和 loop 占用；资格作业再测 peak RSS、loop lag。路由来源近似属于原 Codex R1，与表示优化分开定案。参考 S1、S2、S5。

### P02：额外 actor logprob forward 与同版本对拍共用一个开关

- **旧条目**：交叉复核 §4.1；Claude 总报告 §2 对“无用 forward”的建议。
- **机制与锚点**：`M/miles/backends/megatron_utils/actor.py:625–666` 在 `!use_rollout_logprobs || get_mismatch_metrics` 时执行 actor logprob forward；当前零 KL GRPO＋faithful DIS 中，优势侧主要读取它的 shape，custom loss 随后重新算 current logprob。该 pass 同时触发 `:483–521` 的 `logprob_compare`。
- **已有证据**：交叉复核的 CPU 数值探针在两类非零／抵消样本上比较开关，优势、loss、梯度一致；生产 AST 控制流探针核了分支。`false,false` 会算且产对拍；`true,false` 跳过且对拍消失；`true,true` 仍算且保留对拍。它们用引擎／模型替身，未证明真实 GPU replay 消费或耗时。
- **是否可删**：可作为 **当前限定训练 profile** 的候选开关；不能泛化到 PPO、OPD、reference KL 或其他 consumer。不能称为完全无消费者，也不能直接批准删 `logprob_compare`。
- **仍需查证／最小验收**：分训练与对拍 profile，保留同版本概率证据；实际测该 pass 的 GPU 时间与 R3 填充／消耗。旧“节省20–30% step时间”未实测。参考 S3、S4。

### P03：rollout 的重复递归 chown

- **旧条目**：B F-07；交叉复核 §3.3。
- **机制与锚点**：`R/adapters/slime/sandbox_profile.py:965–968` 已可信初始化权限；`bringup.py:355–362` 又运行 `id agent || useradd ... && chown ...`；`V/agent/sandbox.py:375–384` 再运行同形命令。shell 将 `A || B && C` 解释为 `(A || B) && C`，已有用户仍执行 C。fresh grader 另有独立权限设置，不能计为同一冗余。
- **证据**：交叉复核以真实 shell 结构和无副作用命令替身看到 `CHOWN`、`GIT` 被调用；“id 短路后成为 no-op”的注释错误。B 引用的1480文件／1.36秒来自 W3b 历史模拟环境，不是当前八卡时延。
- **是否可删**：具备局部减掉 rollout 重复操作的明确候选；须保留唯一权限初始化和用户／safe.directory 前提，遵守 vendor 不改字节的现有边界。不能借此删除非 root grader 或官方测试保护。
- **仍需查证**：最终哪一层拥有一次初始化、各种 driver 入口是否仍成立；大树 overlay copy-up 前后时间。无需先改变安全目标。参考 S1。

### P04：census、重复 digest、对象重验与镜像 inspect 不能混成一个“hash 慢”

- **旧条目**：B F-05、F-10、F-15、F-20。census 是枚举工作树中文件类型、权限与内容摘要的清单。
- **机制与锚点**：`R/adapters/slime/baseline_census.py:61–78` 每文件启动 `sha256sum|cut`；`generate.py:2671`、`patch_exporter.py:140`、`grading/manager.py:1705` 分别采基线、运行后和 fresh grader 树。另有 `compute_baseline_manifest_digest`／`compute_frozen_patch_digest` 多次模型导出与 JSON/hash、`prepared_task_face.py:325–330 → training_view.py:178–183` 的 Pydantic 往返、`generate.py:3807,4107` 及 manager 中多次镜像 inspect。
- **证据界限**：三处 census 和 shell 子进程结构可从源码定位；“一万文件数万次 fork/exec”“三次分钟级”“重复 digest 每 attempt 0.5–1秒”是旧静态估算，没有当前大树 profile。prepared 文件／manifest 主要在启动加载，不能由此声称每轮所有身份 digest 都是瓶颈。
- **是否可删**：批量 hash、避免重复 JSON materialization、可信不可变镜像预解析具有讨论价值，但第三次 census 比对的是 fresh grader 的实际树；相同镜像名／HEAD不自动代替文件内容与权限事实。仅缓存 digest 后比较字段也不再检测对象被修改。需先证明不可变性、消费者与相同信任边界，再删检查。
- **仍需查证**：每次 census 的文件数／路径／耗时；批量方式对 symlink、权限、特殊文件名、排除规则是否等价；哪些检查可前移到准备期，哪些必须保留为 fresh 实体读取。修改镜像挂载或 B4 的重建合同不能按普通删死代码处理。参考 S1、S2。

### P05：CLI 安装、完成轮询与 HTTP 连接反复付启动成本

- **旧条目**：B F-06、F-18、F-19。
- **机制与锚点**：`R/adapters/slime/bringup.py:304–315` 每个容器上传 tarball、解压、install、`claude --version`；`docker_sandbox.py:77–79` 同步 `read_bytes()`。`V/agent/sandbox.py:63–77` 每5秒通过 Docker 读 done marker；600秒预算最多约120次。`capture_wire.py:1084,1121` 每次生成／abort 新建 `aiohttp.ClientSession`。
- **例子与证据**：64条同时等待的轨迹按5秒间隔约产生12.8次轮询／秒，这是满占用条件计算，非已测 dockerd 负载。远端 CLI tarball 大小未取得；“固定数秒安装”与“省119次子进程”的收益也未实测，短轨迹并不跑满120次。
- **是否可删**：可研究镜像内预装／只读安装资产按 run 摊销、连接池、一次持续等待替换轮询。只读 volume 会改变 sandbox mount 白名单和可信安装来源；长驻 `docker exec` 会改变取消、期限及断链行为；连接池要有 loop 所有权和 shutdown close。都不应写成零风险。
- **仍需查证**：真实安装大小与冷／热成本，poll 次数、连接建立比例，以及退出／取消是否仍及时清理。参考 S1、S2、S4。

### P06：finalization 的同步序列化、fsync 与每 attempt 基线副本

- **旧条目**：B F-17；F F-02 中关停 fsync 微基准另见 M08。
- **机制与锚点**：`R/adapters/slime/bringup.py:180–201` 每文件执行 fsync＋目录 fsync，已存在则全文回读对比；冻结 patch、baseline、receipt、cleanup result／audit 分开落盘。`generate.py:4687–4735` 写所有捕获 artifact。
- **证据边界**：写法为源码事实；每 attempt 约8次 fsync、5MB增长、几十到几百毫秒均是旧路径估算，受工件大小和存储影响。R3 大量产物另归 P01，不能重复累计收益。
- **是否可删**：可考虑异步 I/O 或不重复生成同一内容，但 `to_thread` 仍须维持持久化成功先于交付、异常首因和 close 等待。把 baseline 改成按 task／image 共用改变现有工件引用与持久性合同，不是仅减少写盘。
- **仍需查证**：工件尺寸、fsync p50/p95、突发完成时 loop 延迟，空间随 run 增长；单独解释失去哪些复核能力。参考 S1。

### P07：model-call、grading、Docker 网络与镜像供给的并发瓶颈

- **旧条目**：B F-08、F-09、F-21；G G-6；交叉复核 §3.2–3.3。
- **机制与锚点**：`R/adapters/slime/bringup.py:608` 缺省 model_call=32；`:1001–1006` grader=4、队列=8；`grading/queue.py:161–203` 队满会让 submitter 等待。评分结束才返回 generate_fn，仍占 miles 在飞名额。`sandbox_profile.py:736–796` 每 attempt 创建网络、连接／断开同一 relay、删除网络；manager `:1273–1289` 懒拉镜像后缓存。
- **例子与边界**：若稳定到达0.1条/秒、平均评分60秒，则平均约需6个 grader 忙碌位；评分180秒则约18个。这是 Little 定律条件例子，不是当前服务时间。execution 包含模型、工具和评分等待，所以32<64、4<64本身不能证明 GPU 空转。旧0.27秒网络测量也不能线性推出64并发真实时延。
- **已证窄问题**：`async_worker.py:735–756` 在 semaphore 前算 timeout，等待不受绝对 deadline 覆盖，取得许可后仍使用旧余量；交叉复核20ms deadline／40ms占用探针仍发出了 send。此为具体排队边界问题，应与“删除限流”提案分开。
- **是否可删**：目前无证据支持直接移除 model-call 限流、扩大 grader内存和并发各4倍、复用污染工作区或取消每 attempt 网络隔离。已有镜像预拉可在选定任务后讨论；不必引入环境池或外部服务。
- **仍需查证**：每阶段服务时间、队列 wait／backpressure、实际运行模型请求数、CPU/RAM/dockerd压力、镜像冷热分布；用合格逻辑组/GPU-hour判断，而非原始并发值。参考 S1、S2。

### P08：多 engine 的前缀局部性与负载均衡存在取舍

- **旧条目**：F F-04；G G-4；交叉复核 §6.4。
- **机制与锚点**：`R/adapters/slime/capture_wire.py:1071` 发送 `X-SMG-Routing-Key`；`M/miles/router/router.py:134–162,215–230` 先按最少活跃请求选 worker，未读 session key。每 turn 都传完整 prompt，SGLang prefix cache 属各 engine。单 engine 无跨 engine 选路问题。
- **已纠正**：最小负载不是均匀独立随机路由；不能推导命中率=1/N，换 engine 也可能命中该 engine 更早缓存的前缀。旧“40轮≈10倍 prefill”和“重算一半”是过强估算，不应作为定案依据。
- **是否可删／替换**：不能因15行实现就默认批准 hash 路由；它改变亲和与负载策略，热点／队列可能反向变差。1×TP4也增加PCIe通信，不可只按缓存选胜者。已批不建粘滞路由／dead-engine恢复的边界仍在。
- **仍需查证**：固定任务和预算比较1×TP4／2×TP2；记录真实 cached tokens、prefill/decode时间、排队与每engine请求分布；先核 `prefix_cache_info` 在 capture→Sample→事件中实际非空。参考 S1；Polar 的训练侧 prefix merging 不是本项推理 KV 路由。

### P09：retract 重算与 JIT drain 的重叠损失

- **旧条目**：G G-5及能力表A；F F-12；Codex R1提供语义限制。
- **机制与锚点**：miles `update_weight_from_distributed/mixin.py:309–331` 在 retract 发布中 flush cache；在飞上下文可能重新 prefill。`M/train_async.py:119–121` 将 drain 放到消费前，修正 stock 预取使 staleness少算一代，代价是 drain/convert不再与前次训练完全重叠；持续 producer本身仍并发。
- **数值边界**：旧64在飞×16K／32K上下文、每engine1–2万token/秒所算的35–100秒／6–20%均是条件估算；没有当前真机逐 publish重算量。不能沿用旧P3的23分钟step证明现在forward永远不是瓶颈。
- **是否可删**：不能删除JIT consume-time权威换取重叠；`in_place`是另一资格profile，须核其spans、sampling mask、R3来源与真实更新。fully async＋retract＋spans也不能直接宣称与K3 partial rollout全部恢复合同等价。
- **仍需查证**：实际retract次数、重算tokens、发布暂停与关键路径残余；把算力成本和R3路由近似分开。参考 S1、S3、S4。

### P10：事件、tape digest 与梯度扫描的成本要按消费者拆分

- **旧条目**：F F-03、F-06、F-13；G G-1、G-2；B F-22；交叉复核 §4。
- **机制与锚点**：候选 `launch.sh:376` 启用 `MILES_RH2_EVENT_DIR`；`M/miles/utils/rh2_event_log.py:118–148` 每事件同步open/write/close。`rollout_manager.py:295` 对 routing ndarray做`tobytes＋sha256`，`actor.py:561` 每rank做 replay tape digest；`model.py:523,726,1021` 读optimizer进度，`:424–483,919` 扫梯度并同步标志。这与P01的捕获转换是两个位置。
- **证据界限**：静态存在不等于已确认瓶颈；“每step十几GB hash／十几到几十秒”依赖长度、fan-out、分片与并发假设，未实测。小事件I/O与大tape搬运应分别计时。
- **诊断价值**：在线`logprob_compare`已存在，不能写成“完全缺失”；缺的是custom loss更丰富的ratio/support统计、drop的长度／原因与collector消费。`bringup.generate()`的`record_event`未走miles主入口，不等于整个主链没有audit；execution audit和shutdown capture统计仍在。
- **是否可删**：可以讨论训练／对拍事件分档，迁出纯展示emitter或在后端扩展点实现，但judge当前使用的重放、身份、消费归属证据需有替代来源。`leaf_ordinals`在wire中移动位置也要证明DP分片和顺序推导一致。不能同时要求同版本对拍又删唯一producer。
- **零信号纠正**：`custom_config.yaml:27`已设连续阈值8，launch有检查和注入；非零优势也可能因singleton支持集或参数梯度抵消产生零梯度。旧“默认无限静默跳步”“只有三种病态才零”的论证已被推翻。用`grad_norm==0`替代完整判定是否等价，需实际归约／optimizer时点证据；0002/0003不是已获准删除项。
- **仍需查证**：分别测digest、`.cpu()`、逐参数同步和事件I/O；保留哪些事件、由谁消费、缺失时是否影响资格判断。参考 S1、S3、S4。

### P11：完整组损耗与重试建议属于训练分布取舍

- **旧条目**：G G-2、G-3；Codex §7全员KEEP_FULL代价；B计数缺口。
- **机制**：一个成员ABORTED／failed_to_grade可让n=8整组丢弃，miles继续补组。若成员独立保留率0.9，则组保留率`0.9^8≈43%`；若独立infra失败率2%，则存活`0.98^8≈85%`。这解释放大效应，实际失败未必独立。
- **锚点**：`M/miles/rollout/fully_async_data_buffer.py:239–256`在dynamic filter前处理ABORTED；group admission和consume-time staleness另有各自drop；`R/adapters/miles/drop_events.py`当前按stage/reason/task聚合。
- **是否可删／新增**：不能据代数例子直接加成员重试、拆组或MASK_MEMBER。控制API重发、重新采样同一成员、重新评分固定patch分别改变不同事实；即使1次typed retry也需明确新attempt身份、原输出是否影响环境、组统计和额外成本。
- **仍需查证**：可归因infra故障率、被丢组与消费组的长度／轮数／task／reward分布。drop短缺不能靠accepted token数替代真实更新；`accepted ∧ support_size>1`也不是非零最终梯度证明。参考 S1、S3、S4。

### P12：轨迹合并可省训练计算，但不能用token数量节省替代语义验收

- **旧条目**：G训练效率表、B F-04“只留最后一轮”提案；交叉复核generated→trained补查。
- **机制与锚点**：当前按leaf构造训练Sample，兄弟叶前缀可重复forward但共享动作只计一次loss；`V/agent/trajectory.py:180–224`的REALIGN会将上一响应区域改写并清mask，`:370–426`另有assistant rewrite merge。少了行／token既可能省计算，也可能丢失真实动作信号。
- **已有边界**：交叉复核正常tool-only回放可CLEAN保留29/29；加reminder可只剩2/29，长旧响应例子只剩2/1127；这些是合成真实模板／builder探针，不代表全部真实CC轨迹比例。历史run8保留样本有JSON键序变化且旧响应前556token未变仍整轮移出loss，不支持thinking唯一根因。
- **是否可删**：不得因效率理由删早轮、改变FORK／REALIGN、强制每turn一行或换模板。表示、每execution分母、同组reward及同次optimizer更新必须一起看。具体训练语义由项目一主清单处理，此处保留性能代价接口。
- **仍需查证**：固定捕获session比较generated/trained/dropped、真实prompt条件、fan-out重复计算和最后梯度；再谈每GPU-hour有效经验。参考 S2、S4、S5、S6。

## 3. 维护面：哪些是真删除候选，哪些是退役或改约定

### M01：未接线的 governed buffer／attempt ledger 是最明确的窄清理面

对应Codex C1、E E-1/E-4c。`R/adapters/miles/attempt_ledger.py`394行＋`governed_buffer.py`260行=654物理行；专用测试572＋252=824行。当前候选launch没有`--custom-async-data-buffer-path ...Rh2GovernedBuffer`，正式组准入采用dynamic filter。包`__init__.py:7,36–54`仍导出账本和惰性buffer；generate_fn旧“未来接线”注释误导读者。

**处置讨论**：可独立删除或移出生产包，连同专用测试、导出、仅服务原型的fixture一起清理；不连带删共享fixture和真实group admission。当前证据支持“当前候选配置无消费者”，不支持“过去或远端任何手写命令都从未使用”。收益是维护面减少，不主张吞吐收益。参考S4只支持复用上游边界，不代替本项目消费者证明。

### M02：async_worker 中冻结worker与活proxy需要按符号拆分

对应E E-2、B F-11。E把worker/retry/queue等约380行列为旧slime-FA面；B进一步把proxy更新窗口、draft、notifier也算进去，估约900行。**两个数字不冲突地相加，而是删除范围不同。** `ContinuousExecutionWorker`消费者在旧`rh2/experiments/fa_bringup/rollout_entry.py`；当前miles主线仍用`ModelCallProxy`、`SessionPoisonRegistry`、`ResourceLimits`、active coordinator及capture交付。

**可删边界**：先决定是否退役旧FA入口，再删其worker/retry/queue；不能凭miles采用retract就直接删除整个proxy，pending commit、失败poison、deadline、取消可达性仍需保留或承接。`fatal_halt_notifier`在miles中是否恒空、更新窗口是否对所有异常都不可达，只是旧静态判断，尚未构成整段删除证明。参考S2、S4；不新造一套ModelCallGuard作为本轮结论。

### M03：不在formal训练根上的模块并非都“无用”

对应E E-1/E-3/E-4a–d/E-9。按用途去重为五组：

| 模块／能力 | 当前训练关系 | 当前能否按死代码删 |
|---|---|---|
| `inspect_s1.py`、`cli.py`、`registry.py`、`outcome_crosswalk.py` | 历史账本／公开CLI／v1读取 | 不能。它们有CLI或历史复核消费者；删除意味着放弃对应能力，需先给替代入口或退役说明 |
| `adapters/offline_export/`、`contracts/export.py`、`adapters/verifiers_projection.py`、`taskset/swebench_smoke.py`及verifiers依赖 | 不在当前miles训练根；仍承载导出、parity、smoke等 | 不能把“训练未用”改写为“verifiers已被全项目放弃”；重要依赖和公开能力退役需单列 |
| `adapters/slime/batch_admission.py` | 旧slime同步调度／GRPO纯函数，当前由miles承担调度 | 可列旧后端退役候选；它与`governance/admission.py`职责不同，不能因名字相似删后者 |
| `s1_compat`／`fa_audit_only`、v1私有bundle、freeze及八题JSON、SimpleLoopDriver | 冻结兼容／探针；分支与数据仍在 | 退役会改变可用执行模式与smoke前提。formal缺配置前移可单做，默认mode改formal与删模式都不是T2删死代码 |
| `shutdown/run_residue.py`／trap、`adapters/miles/drop_events.py` | 前者是计划中的launcher清理接缝，后者是离线汇总工具 | 不能因未审launch尚未调用而删；先完成W7消费者／说明是否保留离线工具 |

v1的`PublicTaskBundle`及helper仍供v2／prepared链使用，不能整删`bundles.py`。`projection_ext.py`当前仍被`generate.py:4445`附近调用；并回projection是组织方式选择，保留sampling-support语义。shared `adapters/slime`目录不是死后端。可直接修正其过时文案，但文件移动／大重命名不是首训前必要条件。参考S4、S6。

### M04：同一事实的多份schema与自检可合并，不能只删校验

对应E E-4e、B F-12–F-16/F-20及交叉复核§6.3。`ExecutionIdentity`字段复制进多个payload，`TerminationFactsPayloadV1`和`AdmissionPayloadV1`由receipt/outcome派生后多次反序列化对账，确有结构简化空间。锚点：`R/contracts/fa_runtime.py:102–143`、`envpack/termination_facts.py:217–373`、`governance/admission.py:198,334–525`、`adapters/miles/generate_fn.py:52–78`。

但TerminationFacts还带receipt／冻结／静止事实，不是outcome全副本；AttemptAssignmentRegistry横跨await rollout并供task及评分材料解析读取，不能称为同一调用栈立即查回。组汇合消费仍需identity/reward/version/shape、同题、fan-out和跨组绑定。19个检查位置≠一次execution执行19次，130拒绝点的“不到10%真实”是旧分类判断，不是发生概率。

**处置条件**：可考虑不可变context／组合identity、减少重复派生，但schema／状态所有权／拒绝路径变化先走T0。drain latch、typed receipt、双读指纹、invariant helper要各自证明等价，不能根据“只防本进程bug”统一删掉。五类timing容器也可能分别服务server／grader／attempt，没有完整消费者图前不能只保留名字最像统一计时器的一个。

### M05：测试负担应按能力、oracle与fixture分开处理

对应E E-6、Codex§7/§8、交叉复核§6.3。旧48.6K行／1612测试、7.1K“硬删”、2K fixture节省、总21–25%等均来自旧静态分类或估算；E声称的import_graph／used_graph／统计原始输出未随报告交付。本轮不重新造全仓import审计，也不把这些数当可执行删单。

1. **随退役能力删除**：M01专用824行最明确；CLI／export／legacy模式测试要等其能力退役，不能倒过来先删测试以证明模块无人使用。
2. **合并重复fixture**：旧多套FakeDocker／formal-chain脚手架可以统一最小公共构造，但某些独立fixture承担不同故障注入。约3880行前置脚手架减半只是预算；过度合一也可能让独立测试共享同一个错误假设。
3. **按不变量区分覆盖**：attempt六字段身份与turn spans不是同一件事；consume-time staleness与per-token版本不是重复。unit＋真实Docker分别证明逻辑和权限／进程事实，不能按同名测试直接二选一。
4. **oracle有效性优先于passed数量**：F3的旧测试把receipt失败保留容器写成正向oracle，已与现行要求冲突。修oracle需说明定案来源，不是T2改期望值。数值oracle如`faithful_dis_loss_by_execution`可考虑移入tests，但不能在移动时重写成和实现同源的镜像。
5. **双lane与stub**：默认pin下integration测试skip是显式lane分工，第二lane跑集成patch语义；“41%默认不跑”不等于41%没有验证。ray/sglang import stub只解决无GPU依赖导入，不证明真实GPU行为，也不应被统一描述为伪造训练。

负例关键词只识别出旧105/1612≈6.5%，不支持“测试主要是防模型伪造metadata”的总判断；具体是否可减仍以不变量和生产消费者为准。

### M06：大文件、死符号和文案可以局部减负

对应E E-5、Codex§8、B拆分骨架。`generate.py`约5001行、`bringup.py`2443行、`async_worker.py`1315行都含活消费者；大文件是阅读成本证据，不是整文件死代码。可先写清共享职责，再按phase做局部抽取，避免临训跨多个ownership边界的大拆分。

E列出`FinalizationStore`、`RuntimeQuiescenceBarrier`等Protocol／别名、`run_labels_from_env`、`_STABLE_KEYS`、`OFFSETS_WIRE_DTYPE`、`SAFE_IDENTIFIER_PATTERN`等约37行零引用，以及`SegmentStopwatch`、`migrate_v3_manifest`、`assert_payload_dereferences`、测试写出helper等候选。**目前只是旧符号搜索结果**；删前应核公共导出、字符串加载、历史工具和类型检查用途。测试专用oracle迁位与真正无消费者符号删除分开，不把约250行一揽子宣称安全可删。

### M07：16个miles patch的维护风险真实，但删除／rebase结论不足

对应F F-05–F-07/F-10/F-12/F-13、E E-8。旧F记录16patch净增3033行、触碰17文件；当时GitHub API显示上游比pin领先302commit，并拆掉`RolloutManager`，9个patch触碰旧文件。**本轮未刷新上游、未试rebase**；准确说法是这9个patch迁移时需重新映射职责，不是已经通过失败的rebase实验证明“只能重写”。

| patch主题 | 可以讨论的减负方式 | 不能直接删除的理由／还需查证 |
|---|---|---|
| 0001 sampling-mask wire、0007 pin | 保留窄兼容修补；未来检查上游是否同等覆盖 | 当前训练／复现基座仍依赖它们 |
| 0002/0003零信号与dirty publish | 分析扫描成本、扩展点和上游化机会 | 阈值已配置、零梯度反例已纠正；skip／publish属于已批语义 |
| 0004–0006事件／对拍／leaf归属 | 按实际consumer分档；研究上游after-step等hook | 把事件搬走不等于可以丢掉证据；新hook也须适配上游 |
| 0008/0009 stock Sample版本spans | 核当前formal接线之外的stock/eval/资格consumer，再决定退役范围 | RH2自行backfill使其部分路径不使用，但新上游同名功能／数据结构不同，不证明固定pin可以无损删 |
| 0010–0013关闭／owner-loop／verdict | 先统一阶段预算和故障归因；已上游dispose可作将来迁移参考 | 上游try/finally不证明有相同owner-loop、清理、首因与退出码合同 |
| 0014 consume-time／drop／no-progress | 保留唯一消费权威；非热路径重复代码可单查 | JIT drain修复真实时点问题；不可为重叠删除语义 |
| 0015多engine版本核对 | 测成本、明确publish ack与实际engine读回各证明什么 | 旧“几十ms／价值近零”未实测；ack后读回不是已证明全无价值的替代关系 |
| 0016最小冷恢复 | 明确run边界版本身份、显式rollout ID与所载checkpoint的一致性 | 改p→p+1／删跨actor核对改变恢复合同；不能以35行或“免费”免除语义论证 |

首训前没有证据要求全线rebase或迁移训练框架。固定pin＋存档patch当前可复核；未来维护应优先找上游已有能力／窄hook，而不是把上游最新README当作已迁移成功。参考S4；六篇论文都不能直接裁决本地哪一个patch可删。

### M08：关停／冷恢复的维护候选要保留已批行为

对应F F-01/F-02/F-08/F-09/F-11/F-13，详细运行语义交主清单。

- **60秒aclose与后续清理**：交叉复核缩时探针证实，初期限超时后即使后来清理成功，verdict仍失败；不证明正常结束必失败。取消并发执行，rollout容器也常在评分前已释放。去掉失败退出码会改已批B-6，不属于普通减负。
- **evidence与resource_closure**：`R/shutdown/chain.py:455–463`将evidence失败计入ok；`bringup.py:1848–1888`有resource_closure步骤；旧F指出关停时做16次fsync微基准。可以讨论移至启动／资格作业或把诊断与清理结果分列，但慢NFS造成真实假红未实测，不能直接删整个模块。估算器自身已标`unbounded_or_unknown`，它遗漏R3是容量信息缺口，不是虚假硬上界。
- **Ray同源异常**：F F-08推断RayTaskError包装让字符串全等不命中，且400字符截断可能遮住根因；该切片明确没有本机Ray复现。保留为需要真实Ray边界验证的诊断问题，不标成已证“永远不命中”。
- **SIGTERM／drain／late facts**：SIGTERM helper在非主线程安装受限，生产默认关闭；grading queue在buffer关后继续drain的价值、late-facts合并是否仍服务首因／清理账本，要逐消费者验证。不能先删除verdict再反推其依赖全部无用。
- **receipt写失败**：Codex F3是明确实现与既定清理要求不一致，且有ENOSPC故障探针；应保留fatal并仍尝试session／容器清理。它与是否保留庞大shutdown报告是独立事项，不能用外部best-effort示例覆盖本项目定案。

### M09：legacy、reference、PDF的体积不是当前训练热路径成本

对应E E-7/E-8。旧199K行legacy Python、2600余跟踪文件、2.2GB reference、650MB可移出等是旧目录统计，部分仍承载历史inspector／README证据。rh2零import只能证明运行解耦，不能证明历史文件无消费者；不得删冻结evidence。归档分支／子目录涉及历史入口、链接和用户工作方式，需要单独给出可恢复方案。

reference中的未跟踪clone不进入主仓对象库；读论文、设计与旧测试仍可能使用它们。grep零引用不等于用户不需要，目录可能含本地改动。双miles checkout目前用于pin／integration双lane；收成一个要先决定如何保留兼容回归，而不能把skip当故障。PDF有原页复核用途，新笔记还明确存在未取得图页的边界；摘要＋URL不能自动替代原始资产。git历史重写与清理磁盘不在本轮范围。

## 4. 六篇新增笔记的定点映射

以下全部是 **参考阅读，未经本轮独立原文复核**。RollArt、Polar、SAO、CompactionRL笔记声明作者自查完成、待独立复查；Agent Lightning另有PDF原图／版本核验缺口；E1明确尾页图表缺视觉复核。原始链接作为下轮复核入口列出，不表示本轮重新联网核验。页码以各笔记所载PDF物理页为准；Lightning笔记未给可靠页码，按原文章节／公式定位，不编造页数。

### S1：RollArt——用阶段关键路径解释成本，不能只看“fully async”标签

笔记：[R11_rollart.md](../../../../harness_improve/external_paper_references/reading_notes/R11_rollart.md) §3.1–3.4、§7.2–7.4、§8.2–8.3、§9.2–9.4、§12。原始来源：[RollArt v2 PDF](https://arxiv.org/pdf/2512.22560v2)，§3/Fig.3–6 pp.3–5；§7.3/Fig.11–13 p.12；Table5 p.13；§8–9/Fig.15 pp.13–14。

**对应P01/P03–P11**：同一系统正常迭代与环境失败迭代瓶颈不同，prefill／decode硬件偏好不同，异步后learner仍会等已评分样本。适合借用现有timing测CPU/环境、推理、grader、queue和训练残余等待。论文的serverless评分把本地rollout卡数4→8并加入外部资源，不能直接支持RH2把grader并发调大就快2倍；32卡异构PD与同构八卡也不同。staleness更宽可改善step time却损害后期time-to-score；冗余取消需检查消费分布。文中R3是第三项系统要求，勿与本项目MoE routing replay的R3混写。

### S2：Polar——阶段解耦与合并收益必须和真实条件、奖励权重一起看

笔记：[R0_polar.md](../../../../harness_improve/external_paper_references/reading_notes/R0_polar.md) §3.3、§4.1–4.4、§6.3–6.4、§8.3–8.6、§10。原始来源：[Polar v1 PDF](https://arxiv.org/pdf/2605.24220v1)，§3.3 p.6、§3.4/Fig.4–5 pp.7–8、builder ablation／reward hacking p.10；代码入口：[固定commit的prefix_merging.py](https://github.com/NVIDIA-NeMo/ProRL-Agent-Server/blob/6a1ead6bfac054fce6c1e62d1a77b330d96c58db/src/polar/trajectory/builder/prefix_merging.py)。

**对应P04/P05/P07/P12、M02**：INIT/READY/RUNNING/POSTRUN可用于识别初始化、评分占住运行名额；但RH2已有异步及评分队列，不能据此再建服务。局部合并消融报告189.5→35.2分钟／约5.39倍，并非等质量或梯度等价实验。原始动作token相同也不自动证明后续动作的条件前缀相同；笔记还记录现代builder提前break后剩余completion未回退逐请求、COMPLETED不等于完整覆盖。它是检查RH2 REALIGN与分支的参考问题，不是已证明的可复制修法。

### S3：SAO——组等待与critic代价是联合取舍

笔记：[R15_single_rollout_asynchronous_optimization.md](../../../../harness_improve/external_paper_references/reading_notes/R15_single_rollout_asynchronous_optimization.md) §2、§4.1–4.3、§6.1/6.4、§8.1、§10。原始来源：[SAO v1 PDF](https://arxiv.org/pdf/2607.07508v1)，Fig.2 p.3、Eq.1–3 p.4、§4.1/Table2 p.6、Appendix B p.14。

**对应P02/P09–P11**：single-rollout去掉同prompt组等待，但仍有128轨迹训练batch；不是每回一条就optimizer更新。论文同时有GRPO＋DIS对照，不能宣布必须放弃GRPO；解除组等待也新增critic、value初始化和更新成本。其学习图按step，没有GPU型号／总GPU-hour／wall-clock，不能作为八卡节约算力的证明。先测当前组等待与stale损耗，再决定是否值得独立算法对照；不要拿SAO代替当前faithful DIS的detach／分母约定。

### S4：Agent Lightning v1——复用后端，同时保留rollout与训练行边界

笔记：[agent_lightning_v1_2608.17528.md](../../../../harness_improve/external_paper_references/reading_notes/agent_lightning_v1_2608.17528.md) §3、§4.1–4.3、§5、§8.3–8.6、§11。原始来源：[v1 HTML](https://arxiv.org/html/2608.17528v1)、[PDF入口](https://arxiv.org/pdf/2608.17528)，§2.1 Eq.8–13／§2.4 Eq.17／§3 Collocated Async RL和Network Issues／Appendix A；[固定代码的rollout_adapter.py](https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/agentlightning/verl/rollout_adapter.py)。

**对应P02/P05/P09–P12、M01–M07**：精确token前缀成立才合并，否则新开训练行；同rollout各行要落同一次optimizer update。它提供比“只要抓到token”更具体的边界。约3500行是作者声明范围，不包含所有后端／harness，不能据此设RH2删行目标；约2倍端到端加速缺完整同资源质量对照，不能推出本项目必须切回colocate。控制面重试与随机生成重试不同，同prompt取最后一次也可能混淆合法子代理／重复尝试。可借鉴窄adapter与上游职责划分，但不能把最终一致性作为删当前receipt／身份约束的证据。

### S5：CompactionRL——压缩改变段结构、信用和成本，不是普通缓存优化

笔记：[R14_compaction_rl.md](../../../../harness_improve/external_paper_references/reading_notes/R14_compaction_rl.md) §4、§5.2–5.4、§6.2、§7.3–7.4、§8、§10–11。原始来源：[CompactionRL v1 PDF](https://arxiv.org/pdf/2607.05378v1)，§4.1/Fig.2 pp.4–5、§4.2 Eq.11–15 pp.5–6、Tables2–4 pp.7–9、Limitations pp.9–10。

**对应P01/P12、M04**：一次rollout可分为execution与summary多段，summary仅在真实生成且有明确loss时才是训练动作；按段计组会重复加权长执行。相同峰值窗口不等于相同累计prefill、action tokens或FLOPs。30B模型在压缩评测56.0、关压缩43.7、基线47.5的交叉差异提醒harness开关影响学习与评测。原文未给GPU数／成本，不支持八卡一定更省，也不是SAO＋compaction已披露统一配方。先核C包是否允许原生压缩、覆盖损失与段分母，再决定是否引入新的训练目标。

### S6：Harness interplay——工具面变动的收益不能归给单独模型权重

笔记：[E1_harness_interplay_posttraining.md](../../../../harness_improve/external_paper_references/reading_notes/E1_harness_interplay_posttraining.md) §3.2–3.4、§6.3–6.5、§8、§10。原始来源：[E1 v1 PDF](https://arxiv.org/pdf/2606.25447v1)，Fig.4 p.7、Tables11–12 p.20、Appendix C pp.18–19；[官方HTML](https://arxiv.org/html/2606.25447v1)可先核未完成视觉检查的尾页内容。

**对应P12、M03/M04**：在相同目标测试harness下，“训练时已有目标harness”优于只在测试时加上，但研究基于ALFWorld，非SWE／terminal吞吐实验；h-high也不是每格都第一。工具改名、参数schema、反馈信息和训练时机是不同变量。能支持固定harness／grader／任务做有限2×2对照，不能支持任意harness更新都必须重训，更不能作为删安全／状态schema的理由。笔记明确没有完整async／cache／packing／吞吐消融。

## 5. 覆盖核对与本轮停止处

| 旧来源 | 本文落点 | 保留的边界 |
|---|---|---|
| Codex F1、C1、§7–8 | P01、M01、M03–M07 | R3来源R1和训练覆盖另归语义清单；未把CPU探针升级GPU资格 |
| 交叉复核§3.2–3.3、§4、§6.2–6.4 | P02/P03/P07–P12、M04/M05/M08 | 勘误已吸收：chown成立、对拍存在、零信号阈值8、router非随机、假红非必然 |
| B F-04–F-10 | P01、P03–P07 | 操作次数／时间均区分源码与估算 |
| B F-11–F-22 | M02/M04/M06、P04–P07/P10 | 不按worker目录或检查数量直接删 |
| E E-1–E-9 | M01–M09 | 公开能力／旧模式／launcher接缝不算无条件死代码；launch正式接线由W7语义清单负责 |
| F F-01–F-13及逐patch表 | P08–P10、M07/M08 | 上游差异是历史观察；零信号、退出码、恢复版本不能按T2改 |
| G G-1–G-6及吞吐／训练效率表 | P07–P12、S1–S5 | retry、路由、in_place先测后决，不复制外部平台 |
| G G-7/G-8、广义能力横比 | 本段登记，详细接口交主清单 | OPD仍为首训后独立实验；W8 eval仍是已计划入口。无本轮材料证明必须做OPD、多环境、池化、动态GPU、prefix-tree kernel或“已超过多数实验室” |

本库存已覆盖指定旧主题与六篇定点阅读入口。余下工作是项目一主清单去重、owner按既有T0边界选定讨论顺序，以及在原定资格作业中取得明确列出的缺失证据；不以继续扩大文献搜索、全仓新审计或大规模删代码作为本轮尾项。
