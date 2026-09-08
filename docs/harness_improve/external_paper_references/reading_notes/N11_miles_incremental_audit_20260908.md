# N11 增量：miles 最新上游与 RepoHarness 集成差异审读

**结论：不建议把当前 main 直接替换正式 GPU 候选，也不建议继续原封不动扩大自有补丁栈。** 上游已把逐调用、逐 token 的版本区间做成原生数据结构，并重构 rollout 控制面与权重传输；这些变化有复用价值。但当前 main 仍未合并完整 top-p support replay，且现有 rh2 适配器会遇到“字段名不变、值类型已变”的不兼容。新增缺 reward 过滤还会先于 rh2 组校验执行。本文以实际 SWE 入口为主线，区分可复用能力、仍需保留的项目语义和待验证迁移风险；对五份固定源码运行了 **15 项隔离 CPU 检查**，不代表全链或 GPU 验证。

导航：[版本与范围](#scope) · [实际执行路径](#path) · [主要增量](#deltas) · [16 个补丁取舍](#patches) · [检查结果](#probes) · [优化与 PR 候选](#actions)

<a id="scope"></a>
## 1. 来源、版本和本轮到底读了什么

类型：**版本化源码增量专题**，不是论文、性能复现或依赖升级。阅读日期 **2026-09-08**。承接 [N11 原始专题](N11_miles_agentic_rollout.md)，不重新展开其中的 TITO、Harbor、OPD 和 fully-async 基础介绍。原始专题中的版本结论继续按其 U/I/W 快照理解。

### 1.1 五个不能混淆的版本

| 代号 | 仓库 / 版本 | 本轮用途 |
| --- | --- | --- |
| **P** | `Rogerffff/RepoHarness@32b615c4e4f869b448174e5974e7a8d29fc4612c`，`miles-migration` | 本轮项目读取快照；2026-09-08 发布 Envs-FORGE 阅读补充的提交，不是 miles 实现升级 |
| **U** | `radixark/miles@f2b7c79298a53c53861514d099f7def73bd29f4a` | 项目基础 pin，2026-08-24 |
| **I** | 本地集成 `rh2-integration-v3`，manifest 指向 `98a0272e4158b2c20e3a34d210c79b50159af0f6` | U + 四项上游选材 + 0001–0016 项目补丁；本轮从存档和项目消费点分析，没有重新构建完整 checkout |
| **W** | `radixark/miles@d2fc97ce581577e255e494801d7568747d5a10d7` | 原 N11 于 09-07 定点查看的在线版本；并不表示此前已审读它的整个代码树 |
| **H** | `radixark/miles@3de96596f16b9e6d23ba550c4c47de3479c9f14c` | 本轮固定 main；提交时间 2026-09-08 06:10:32Z |

[U→H 比较][compare-u]显示 ahead=309、behind=0；[W→H 比较][compare-w]为 ahead=7、behind=0。**309 是相对项目基础 pin，不是“上次阅读之后又更新了309个提交”。** U→H 的 API 文件列表很大，不能把返回的有限列表当作全仓文件覆盖证明。

I 的[集成 manifest][manifest]记录：expected tree=`c8687c9b33968c31e13becc4e3d249d97aec717a`；source tree digest=`3c47f80ff15f684fccc63de722a26eb65a293cf0911f2379181a93ab1d837912`。这是项目的重建目标，不是本轮重新算得的结果。其四项上游选材包括：

- 已合并的采样支持集传输 `29c2c3aee4be0c6d426ca0695880819899b1a2e6`（#2595）；
- top-p replay 当时的 PR head `3ac3adce3e1aef0a2e2bce7c3381c5d063937c62`（#2596）；
- SGLang 0.5.18 矩阵 `cd464a1c4c91546ea43abb2233b97bc1bc90eb97`；
- FLA 0.5.2 `dbbab1566ae438f7202fff653eae938e07b1d4b6`。

PR #2596 仍 open，最新 head 已是 **`d17f5716d92b936c6ac585fa6b6f318ba7dda8f8`**，基于 W，而不是 I 采用的旧 head。**main、未合并 PR、项目 cherry-pick 版本三者不能合并成一个“最新 miles”。** [PR2595][pr2595] / [PR2596][pr2596]

### 1.2 读取覆盖和边界

| 主题 | 实际阅读 | 深度与对应章节 |
| --- | --- | --- |
| 既有认识与项目约定 | N11、当前简报、manifest、patch README、根 CLAUDE、笔记模板 | 承接既有专题；状态简报为导航，不替代实施定案 |
| 项目实际入口 | `generate_fn.py` 全文；`canonicalize.py` 字段及构造/版本片段；`group_admission.py` 入口、成员检查及结尾；`faithful_dis_loss.py` 合同段 | §2、§3、§5；没有复审整个 rh2 或 faithful DIS 全部实现 |
| 新版数据与过滤 | H `types.py`、`base_types.py`、`common_filters.py`、`fully_async_data_buffer.py`、`weight_version.py` 全文 | §3；五文件镜像与 GitHub blob SHA 一致，用于实际 CPU 检查 |
| producer/driver/control | H `fully_async_rollout.py`、`train_async.py`、`rollout_executor.py` 全文 | §2、§3；以调用顺序和所有权审读，未运行 Ray |
| session 和训练消费 | H session `samples/merge.py` 全文；`train_data_conversion.py` 前260行；Megatron `model.py` 400–660 | §2–4；检查表示、wire、分母入口与 optimizer 边界，不宣称所有 reducer 数值已复核 |
| 发布与恢复 | H `weight_update/updater.py`、`session.py` 全文；executor save/load | §3；不涵盖所有 transfer protocol、容错模式或 LoRA 分支 |
| 补丁 | 全量 manifest/说明；0001全文；0002核心定义与梯度扫描；0014合同、异常/no-progress与driver diff | §4 的证据强度明确区分；其余补丁语义以存档说明及 H 对应消费点核对，不声称逐行审读所有16份 diff |
| 最近更新与测试 | W→H 七提交及文件差异；`tests/fast/rollout/test_filters.py`全文；PR2595/2596元数据和最新PR的custom-loss门控 | §3、§5；没有运行整个上游测试套件 |
| 依赖 | H `docker/Dockerfile` 1–100；项目 manifest 的依赖 pin | §4；未构建镜像、未核验 sm_120 kernel 和 wheel |

本轮容器联网存在 DNS 失败，未 clone 上游或执行整个 I 的 `git am` 重建。通过 GitHub connector 取得源码，在本地转存五个完整文件，并核对其 Git blob SHA 后运行隔离检查。**这避免把手写近似实现作为原源码实验，但仍不等于完整仓库可运行。** 具体替换的外围依赖和命令见 §5。没有新增 PDF 任务，也没有借用附件中的历史调查补写当前代码事实。

### 1.3 真正新增的七个提交

| 提交 / PR | 变化 | 对本项目的判断 |
| --- | --- | --- |
| `51853a16` / #3095 | `DynamicFilterOutput` 主名改为 `FilterOutput` | 保留同类型别名，当前 rh2 import 不会仅因改名失效 |
| `5185f133` / #3094 | common group filters 集中 | 可复用，但调用顺序也是语义，不能只看重构命名 |
| `4a58e4e1` / #2814 | 缺 reward 的组预先丢弃 | 新增绕过 custom filter 的路径，必须与 formal 完整性检查对齐 |
| `78747f69` / #3134 | CI 文档移入 developer | 更新引用即可，无须当作运行时创新 |
| `91e40b54` / #3125 | advantage 的 PP stage 来源改为 parallel state | 候选兼容修复；本轮没有执行 PP>1，不声明会改善当前配置 |
| `db3d6b56` / #3124 | SGLang image 0.5.19 | 不能绕过项目已冻结 commit、架构和 GPU 资格检查直接升级 |
| `3de96596` / #3141 | debug train dump 按 DP/CP shard 而非每 rank | 可能减少重复调试输出；不是已测得的训练提速 |

详细 commit 和完整差异用[固定 compare 入口][compare-w]追溯。版本区间和控制面重构在 W 已存在；本轮是深入补查这些未充分审计的变化，不把它们错误标成这七个提交的新功能。

<a id="path"></a>
## 2. 两条实际路径：项目 I 与 H 不只是文件名不同

### 2.1 项目当前 SWE 路径

依据 P 的[`Rh2MilesGenerateFn.__call__`][p-generate]，正式执行依次为：

```text
miles prompt group / Sample
  → Rh2MilesGenerateFn
  → BringupService（首次启动；确认 formal group filter 接线）
  → 铸造本次 attempt 身份并绑定 prepared task 分派
  → rh2_custom_generate / vendored slime agent 层
  → Claude Code 交互、模型调用捕获、产物冻结、fresh grader
  → canonicalize_group：slime Sample → miles Sample
  → 回填并核对 attempt / task / admission / termination 身份
  → GenerateFnOutput
  → miles buffer 的组过滤
  → rh2_group_admission_filter
  → consume-time staleness
  → 训练转换与 faithful DIS
  → optimizer / publish / 下一次消费
```

这条链复用 vendored adapter，但环境、评分和项目身份由 rh2 拥有。不能因为 H 的原生 session API 更完整，就说可以直接用官方 `agentic_tool_call` 替换整条链。它们的任务材料、评分与生命周期所有权并不相同。

`canonicalize` 仍有必要处理两种 Python Sample 类及 Status 枚举不相等的问题；其存在并不只是历史冗余。是否能删除这个转换层，要以执行层真正改用同一原生 Sample 为前提，而不是以字段名称相似为前提。[P canonicalize][p-canon]

### 2.2 H 的控制面和权重路径

H 的[`train_async.py`][h-driver]使用 `create_rollout_components` 返回 inference controller 与 RolloutExecutor，而不再由旧 RolloutManager 单点承担所有职责。所读路径为：

```text
async driver
  → inference_controller.prepare_rollout
  → RolloutExecutor.get
  → asyncio.to_thread(call_rollout_function, RolloutFnTrainInput)
  → FullyAsyncRolloutFn / 后台 group worker
  → DataBuffer.put / get
  → postprocess_rollout_data
  → assert_samples_weight_version_sane
  → convert_samples_to_train_data
  → DP 分发 / trainer
  → backend-neutral WeightUpdater
  → transfer protocol + engine session
  → 版本通知 RolloutExecutor
```

新[`WeightUpdater`][h-updater]把 HF 权重迭代、传输协议和 engine 更新 session 分离。它是值得学习的职责拆分：模型后端提供权重，protocol 决定传输布局，session 负责引擎暂停、更新和恢复。不需要 RepoHarness 再实现第四种传输后端。

但这也使旧补丁机械重放不可靠：0010–0013 的关闭位置、0015 的 engine 访问方式、0016 的版本计数器位置都变化了。**同名机制仍需要，并不意味着旧 diff 仍能正确应用。**

### 2.3 算法单位仍须贯穿 wire，而不是在 adapter 处停止

H [`train_data_conversion.py`][h-convert]继续使用 `rollout_ids` 和 `rollout_mask_sums`；后者聚合同一逻辑 rollout 全部 sibling 的 action mask 数。P 的 faithful DIS 将这一总数作为 execution 分母：DIS 拒绝的 token 自身梯度为零，但仍留在 provenance 分母里，再按 execution 等权归约。[P faithful DIS 合同][p-loss]

本轮没有发现足以把该项目目标替换为另一种 upstream 默认 loss 的证据。新上游携带更多数据，不代表现有自定义 loss 已自动与新 PP/CP、dynamic batch 和 reducer 调用对齐。**升级候选必须用同一批逻辑轨迹、不同切段/分片的参考计算复核，不能只比较 dataclass 能否 import。**

<a id="deltas"></a>
## 3. 承重增量与具体风险

### 3.1 原生版本区间已经到位：0008 的部分职责确实可以让回上游

上游提交 `b518b48f…`（#1891）把 `Sample.weight_versions` 从字符串列表改为：

```text
list[WeightVersionsPerCall]
  └── spans: list[WeightVersionSpan(version, abs_start, abs_end)]
```

`from_meta_info` 根据当前调用的输出 logprob 数和 `output_end`，把引擎返回的相对区间锚定到 Sample 的绝对 token 位置；`strip_last_output_tokens` 会同步裁剪区间；序列化使用 `to_dicts/from_dicts`。H 的训练 wire 还增加 `weight_versions` 的 `msgpack_ragged` 运输。[H types][h-types] / [H converter][h-convert]

原 N11 指出的“session merge 仅读单数版本”也已变化：H 的[`_compute_sample_from_openai_record`][h-session]直接调用 `WeightVersionsPerCall.from_meta_info`，且在 trim 前建立区间、由统一裁剪方法更新。这是真正值得复用的增量，不应继续维护一份只有 flat versions 的平行版本账。

**但上游表示更完整，不等于已经实现项目的全部校验。** H parser 对 plural `None` 回退到单数；plural `[]` 产生空区间；仅检查部分上界，并通过 `assert` 和后续 `Sample.validate()` 检查排序及边界。项目 0009 则把显式 null/空列表、非字符串版本、轮内不连续等视为真实异常，覆盖末端等于本次 generated token 数的检查又由 rh2 parser 完成。两者判定前提不同。

迁移时应将**可信引擎输出先校验，再构造上游区间对象**。轮与轮之间存在 observation 间隙是合法的，不能把“单次生成内部连续”错误推广为整条 Sample 的所有版本区间必须无缝相连。

### 3.2 同字段名、不同值类型：现有 schema guard 不能发现这一类漂移

P 的 canonicalize 允许 I 的30个 dataclass字段；H 仍是同一集合。因此字段集合检查会通过。但旧构造代码仍执行：

```python
weight_versions=list(s.weight_versions or [])
```

其元素是字符串，而 H 的 `oldest_weight_version` 经 `all_weight_version_spans` 访问 `call.spans`，训练 converter 则调用 `call.to_dicts()`。**直接构造 dataclass 不会按类型注解自动转换。** 这会在后续消费者产生 `AttributeError`；不能靠给允许集再加一个字段解决。[P canonicalize][p-canon] / [H types][h-types]

CPU P01 确认：字段集合相同，`Sample(weight_versions=["3","4"]).oldest_weight_version` 仍报错。P02/P03 同时确认新结构正常往返和尾部裁剪。这是**升级组合的兼容性反例**，不是当前 I 已经运行错误的证据。

H `Sample.from_dict` 对旧 dump 的支持也不能代替实时桥接：它把旧字符串放到 `legacy_weight_versions`，清空 active spans，而不是猜测 token 区间。P14 确认恢复对象的 `oldest_weight_version=None`。这是诚实的旧格式保留策略，不是已恢复训练所需的 provenance。

P `_apply_weight_version_facts` 与其他消费点还会对元素 `str(v)`。只修 constructor，后续对账仍可能失败。应按值类型及所有生产/消费点做窄迁移，不要维护一个同时接受“任意字符串和任意对象”的宽松兼容层。

### 3.3 top-p：传输已合并，捕获与 actor replay 仍未合并

[PR2595][pr2595]已合并，只拥有 CSR 表示与传输。[PR2596][pr2596]仍 open；最新 head 改造了 SessionServerConfig、actor-only forward 等接缝，并要求使用 miles router 保留 native sampling-mask 扩展。因此，**main 有 `rollout_sampling_mask` 字段，不代表 main 已具有 I 当前启用的完整 support-normalized 训练行为。**

最新 PR 的[`model.py`][pr-model]仍有：

```python
sampling_mask_keys = (...) if top_p_sampling_replay_enabled(args) and args.loss_type == "policy_loss" else ()
```

P 0001 正是为了让 `custom_loss` 也能取得 support wire fields，去掉其中的 `policy_loss` 条件。**这项差异在最新 PR head 仍存在，不应把它标为“新版已经吸收”。** 但这里也不能简单全放开所有 forward：reference/teacher/value scoring 与 actor 的支持集语义不同，修复应限定实际需要的 actor custom-loss 消费路径。[P patch0001][patch1]

PR正文报告557项CPU检查及旧head的2×H200实验，并说明重基后的CI应重跑；本文没有复跑，也不把旧head成绩作为新head验收。当前没有在原生 main 上看到激活闭环，不用本篇推定任何 GPU parity 数值。

### 3.4 缺 reward 预过滤：更安全的数据入口，也可能隐藏 formal 接线错误

H `DefaultDataBuffer._preput_filter` 顺序为：

```text
ABORTED → missing reward → custom dynamic filter
```

missing reward 分支按整组丢弃、计数，不调用 unused handler，不重试该原组，也不调用 custom filter。合法 `0.0` 不属于缺失；reward dict 缺少选定key则传播 KeyError，而不是一律归入 missing。[H buffer][h-buffer] / [H filters][h-filters]

P 的 `rh2_group_admission_filter` 不仅决定是否值得训练，还检查身份、分派、termination 与 admission 是否一致。全员声称 KEEP_FULL 却没有 reward，会触发 `keep_full_without_reward`；若组还同时存在身份矛盾，也应让该矛盾可见。[P group gate][p-group]

直接升级后，`reward=None` 可能使这些检查不再执行。**结果不是无效 reward 混入训练，而是原应报错的完整性故障降为普通丢弃、持续补后续任务。** P05/P06 用会抛错的 custom filter 验证了这一调用顺序，并保留正常零分对照。上游自己的 `test_preput_missing_reward_wins_before_dynamic_filter` 也明确测试该行为，故不能称为未知的上游 bug。[H tests][h-filter-tests]

迁移时需要决定 formal 完整性检查放在哪里：生成交付前完成必要验证；或通过现有 custom buffer/hook 合并顺序。应优先最小改动，不增加一个通用规则引擎。改变失败处置的方案是项目语义决定，本轮不实施。

**正向兼容事实：** `DynamicFilterOutput = FilterOutput`，P 的旧 import 仍有效，P07已验证。不要因改名制造不必要迁移。

### 3.5 consume-time 并未因 helper 重构自动成为“实际训练时点”

H `group_staleness` 取可解析的最老版本，再用传入 current version 相减；缺版本成员被忽略、全缺失返回None、负lag直接返回。默认 buffer 对None不判定，对负值不因 `lag>N` 而拒绝。P08/P09实际确认这些分支；上游测试也将负lag作为 helper 的合法返回值。这说明**helper做算术，不承担项目 formal 不变量**，不是仅改函数名就消除了0014的职责。[H filters][h-filters]

更关键的是 H driver：下一批 `prepare_and_generate` 在当前批训练前启动；publish前先等下一批返回；然后发布权重；下一轮才训练已取出的数据。因此 buffer.get 的版本可以早于真实训练时点。[H driver][h-driver]

一个明确的时序例子：

```text
已发布10 → 下一批取出行为版本8，账面lag=2
         → 本批训练结束并发布11
         → 使用已经取出的下一批，按已发布版本计实际lag=3
```

这只是从调用顺序构造的例子，**不是测得的事故频率，也不是“所有场景都恰差1”**。它说明，若项目的N约束定义在实际训练消费，则“在get里算lag”本身还不充分。

I 0014 对 fully_async 路径实行上一轮publish后才JIT drain；后台producer继续生成，并非改回同步rollout。这个差异在H仍存在。[P patch0014 driver][patch14-driver]

P10还复核了原N11已发现的指标问题：先扫描并丢lag=5的组，再接收lag=1的组，`avg_staleness=3`，不是accepted-only的1。**这是旧发现的当前版本复核，不是本轮首次发现。** 若保留扫描口径，应明确命名；若报告消费口径，应只统计最终接收组。不要用该平均数直接校准N。

### 3.6 零梯度跳更新与“发布方存活守卫”会产生新的组合问题

I 0002在全局梯度归约后检测精确零信号，跳过optimizer/scheduler；0003据此跳过权重发布。这个行为是项目明确选择，**不是所有Adam训练都应自动如此**：即使新梯度为零，动量和weight decay仍可能有合法更新语义。上游H没有等价的精确零全局梯度分支，仍按valid_step调用optimizer。[P patch0002][patch2] / [H model][h-model]

H的新保护是：`RolloutExecutor.get`每次增加“距上次set_weight_version的次数”；阈值为 `max(3, update_weights_interval+1)`。超过阈值将assert失败，防止发布版本信息永久停在旧值。[H executor][h-executor] / [H version guard][h-version]

若将0002/0003迁入H，但有意连续零信号跳发布，interval=1时第4次get会触发该守卫，即使权重确实没有变。P13只运行守卫函数，验证3次允许、4次拒绝、通知后计数清零；**未运行带这些补丁的H driver**。

正确问题是区分“发布方仍有响应”和“真的产生了新权重版本”。可以讨论同版本通知、独立的更新结果通知等窄方案；**不能为了满足守卫而虚增版本号或强行执行本来决定跳过的optimizer**。现有I没有这个新守卫，本篇不把组合风险误写成它当前必然失败。

### 3.7 新控制面仍没有覆盖项目的完整关停合同

H `FullyAsyncRolloutFn`仍持有长寿命worker，active group在worker局部变量中；DataBuffer没有aclose。`RolloutExecutor.dispose()`关闭数据源、分析/指标和特定checkpoint eval对象，但未调用生成worker的统一关闭入口。`train_async`只在正常末尾依次dispose；外层finally执行的是tracking收尾，不是训练资源全体释放。[H fully_async][h-fa] / [H executor][h-executor] / [H driver][h-driver]

因此0010–0013仍有实际职责，但旧RolloutManager位置不能机械保留。H仍经`asyncio.to_thread(call_rollout_function, ...)`进入rollout调用链，原项目关于owner loop的经验有参考意义；具体关闭应根据新版实际event loop归属复核，不能在actor loop直接await另一个loop上的Condition/Task。

代码搜索也能找到其他组件自己的aclose，例如session HTTP client、multi-LoRA client和FT controller。**“某些组件有关闭方法”不等于“fully-async生产者、阻塞消费者和rh2环境资源有完整关闭链”；反过来，本篇也没有断言整个上游所有退出方式都会泄漏。**

generic generation close协议、有限取消等待、blocked put/get唤醒，可能是有价值的窄上游讨论；项目特有的首因格式、residue与BringupService收尾不应全部硬塞给上游。

### 3.8 写版本、读回收敛和参数正确，是三种证据

H updater把更新拆为protocol和session，对选定clients执行pause、transfer、end、set version、resume，并等待相关RPC。`end_weight_update`会检查显式失败。所读通用路径没有0015那样在发布后逐engine GET并比较版本的逻辑。[H updater][h-updater] / [H session RPC][h-weight-session]

因此这只能部分替代旧的协调代码，不能自动替代项目的多engine收敛检查。另一方面，**即使所有版本标签相同，也不能证明所有权重张量、routing replay或logprob完全相同**；已有checksum／sample parity属于不同测试面。

I0016只做最小冷恢复：续接已发布计数，不恢复pending轨迹，也不是joint commit。H executor的save/load调用data source与rollout函数保存；新WeightUpdater构造时从0开始。所读这条通用路径没有等价的项目已发布版本状态恢复，不能把`Sample.from_dict`支持旧dump误认成运行恢复。

迁移0016时应找到新controller/updater的权威计数位置，重新验证bootstrap和首次真实更新；不扩展成WAL、exactly-once重放或分布式checkpoint平台。

<a id="patches"></a>
## 4. 16个补丁怎么分类：不是“全保留”或“全删除”

下表是**迁移评估**，不是patch application测试。编号、目标与重建关系来自[P patch README][patch-readme]和[manifest][manifest]；标为“说明级”的条目没有本轮逐行重新审查完整diff。归类中的“保留语义”不表示必须保留原代码位置。

| Patch | 项目职责 | H中的对应事实与建议 | 证据深度 |
| --- | --- | --- | --- |
| 0001 | custom_loss下运输sampling mask | main只有被动运输；新PR2596仍限制policy_loss。**保留必要差异，针对actor custom loss做窄测试** | 原patch全文 + 新PR实际门控 |
| 0002 | 全局精确零梯度跳optimizer/scheduler | H无等价skip。保留项目选定语义；不能当通用默认bugfix | patch核心与H真实optimizer边界 |
| 0003 | 按聚合weights_dirty门控publish | H通常按interval发布。保留语义，但必须处理新“未通知”守卫 | manifest/说明 + H driver/guard |
| 0004 | G1事件和集成树身份 | H有audit设施，不等于同一实验记录。**项目特定，可评估以hook替代侵入点** | 说明级 + H入口 |
| 0005 | 验收证据、运行身份与parity等补充 | 不从H功能名推定同字段同分母；按仍在使用的验收读取点决定保留量 | 说明级 |
| 0006 | leaf身份wire、rank/engine事实 | H有sample_indices/rollout_ids，未见本项目叶身份列等价替换。避免把raw metadata误送trainer | 说明级 + H wire清单 |
| 0007 | 固定SGLang/Megatron提交 | H Dockerfile默认commit仍为空，release可显式传入。保留可复现构建目标，但新候选应钉新的兼容版本，而不是永久守旧 | manifest + H Dockerfile |
| 0008 | per-token版本计账 | **可部分由原生WeightVersionsPerCall替代**，包括session和裁剪；不可照抄旧flat列表 | H类型/session/wire全文或相关段 + P桥接 |
| 0009 | 严格校验版本区间 | H的null/空表/类型/覆盖检查不等价。保留有效输入检查，适配新结构 | manifest具体合同 + H parser + CPU检查 |
| 0010 | rollout/buffer关闭、try/finally | H未给该路径统一关闭。保留职责，迁往新executor与driver边界 | 说明级 + H整条关闭路径 |
| 0011 | 回owner loop、有界关闭 | H仍有跨线程调用，不能从async命名推定同loop。迁移时以实际owner为准 | 说明级 + H to_thread调用 |
| 0012 | 关停残留成为非成功结果 | H正常dispose不提供同等结构化verdict；保留必要失败可见性，不扩大通用平台 | 说明级 + H dispose |
| 0013 | 首因同源严格判定 | 项目关停报告语义，无证据说已上游化；可随关闭重构合并维护 | 说明级 |
| 0014 | 实际消费时staleness、no-progress、事件 | H仍预取、允许缺失/负lag、仅warning。**保留目标并重定位**；注意新增missing-reward过滤顺序 | patch关键diff + H driver/buffer + CPU检查 |
| 0015 | 发布后逐engine版本核对 | H写每个client≠读回收敛；保留目标，替换旧engine actor访问方式 | 说明级 + H updater/session |
| 0016 | 最小冷恢复版本续接 | 新updater与executor所有权变化；未见等价自动替代 | 说明级 + H构造/save/load |

**明确可以不重复做的事：**新main已有#2595的通用CSR表示；新原生版本区间已有裁剪、序列化和session生成路径。若建立新候选，应复用它们，不再维护同义结构。**不能直接删的事：**自定义loss激活、formal完整性、实际消费时点和关闭/恢复的项目约定。二者并不矛盾。

H镜像基底为SGLang v0.5.19，但`SGLANG_COMMIT`和`MEGATRON_COMMIT`默认空，开发构建可随分支移动，release构建可固定。这个设计不等于上游不能复现；只说明**本项目必须记录实际构建输入，而不能仅记录image tag或Dockerfile SHA**。本轮没有验证新版wheel、retract/R3组合或sm_120性能。[H Dockerfile][h-docker]

<a id="probes"></a>
## 5. 实际检查：15项隔离CPU探针，结果与解释

附件：[可运行检查脚本](sources/N11_miles_incremental_20260908/probe_semantics.py) / [本轮JSON结果](sources/N11_miles_incremental_20260908/probe_results.json)。

脚本需要一个H checkout，但不import整个miles。它核对5个被测源文件的blob SHA，再用AST保留原函数、类和常量执行。替换范围只有：`load_function`对本次callable/None直接返回；LoRA检查固定False；未使用的sampling-mask类型占位。真实使用CPU torch、numpy、asyncio、dataclass。**不测试动态import、Ray、SGLang、Megatron、NCCL、分布式梯度或真实工具环境。**

本轮环境：Python3.13.5、torch2.10.0+cpu、numpy2.3.5。结果 **15/15符合所记录预期**；其中多项预期是“暴露不兼容／边界”，不能称作上游15项质量测试全绿。

| ID | 检查与实际结果 | 证据解释 |
| --- | --- | --- |
| P01 | 30字段集合相同；旧flat版本触发AttributeError | 同名schema值类型漂移的可运行反例 |
| P02 | 两个原生span往返后oldest=3 | 正向控制，不是所有版本处理都错误 |
| P03 | 裁去一token后末span终点正确缩为3 | 原生裁剪可复用 |
| P04 | plural null回退，空list无span | 不等价于项目严格入口合同 |
| P05 | 缺reward时custom filter和unused handler均调用0次 | 新过滤顺序确实会抢先处理 |
| P06 | reward=0.0会进入custom filter并传播探针异常 | 不把普通失败reward误当missing |
| P07 | 新旧FilterOutput名是同一类型 | 当前import兼容 |
| P08 | 一成员缺版本仍按其他成员算；全缺返回None | 不能由group lag反推每叶provenance完整 |
| P09 | current10/behavior12，max0，buffer返回lag=-2 | 阈值不承担负lag完整性检查 |
| P10 | lag5被丢、lag1被收；报告avg3 | 扫描口径与消费口径不同，旧发现重验 |
| P11 | 容量1时第二put阻塞，get后唤醒 | 正向验证已有背压，没有建议重写队列 |
| P12 | 空版本列表通过sane guard；default标签触发assert | 该guard检查已有span，不验证覆盖存在 |
| P13 | interval1下未通知3次允许，4次assert | 只验证守卫函数；与零更新skip的组合尚未全链运行 |
| P14 | 旧dump保留legacy字段，active spans空、oldestNone | dump兼容不等于实时版本适配 |
| P15 | DataBuffer/DefaultDataBuffer无aclose | 仅API检查，不是运行泄漏或关停超时复现 |

复核命令（使用已有固定checkout，不要求安装完整miles）：

```bash
python docs/harness_improve/external_paper_references/reading_notes/sources/N11_miles_incremental_20260908/probe_semantics.py \
  --miles-root /path/to/miles-at-3de96596 \
  --output /tmp/miles-incremental-probes.json
```

不要使用`python -O/-OO`，因为本次明确检查assert的普通执行语义。源文件内容检查只服务本阅读实验的可重复性，**不是新增RepoHarness训练闸门**。本轮五文件转存与GitHub blob逐字一致；第三方源码副本没有提交入本库，脚本从使用者的checkout读取。

### 5.1 没有执行的检查

未构建I、未试验16patch对H的git-apply兼容性、未运行rh2两lane完整测试、未运行上游pytest全套、未做GPU或多engine RPC实验。driver时序例子、新旧补丁组合、全局零梯度行为和关停风险属于**源码静态分析或待验证组合**，不冒称上述15项CPU探针已经验证。

上游`test_filters.py`包含缺reward抢先、旧名兼容、负lag和缺版本等测试，说明这些是明确实现行为。没有执行它的完整pytest模块；本篇运行的是附带的新隔离脚本。[H tests][h-filter-tests]

<a id="actions"></a>
## 6. 对项目一、优化和上游贡献的具体建议

### 6.1 当前选择：保留正式候选，另行界定迁移切片

**现在不升级、不改已定算法、不把最新main称为“更可靠正式基座”。** 不是否认上游进步，而是H并不包含I全部激活能力，且存在接口与语义迁移成本。先用当前候选完成所需资格验证，与另建升级候选是可分开的事。

如果后续决定迁移，最小顺序应是：

1. 固定H与要选用的PR head，先恢复support capture/scoring与custom_loss运输；不要只以字段存在判完成。
2. 把版本桥接改为原生区间对象，重新检查entry、group gate、wire、日志与裁剪；删除能够由原生结构承担的平行表示。
3. 再适配控制面：JIT消费、无更新通知、关闭owner loop、engine核对、最小冷恢复。
4. 最后进行同样本CPU/数值对照、现有lane测试与匹配GPU资格作业。未过前，不替换依赖pin或第一轮训练配置。

这是待选择的迁移方案，不是本轮批准。迁移成功也不自动构成模型提升，更不能用“少了几个patch”替代实际正确性和性能结果。

### 6.2 最值得形成窄PR或复用改动的候选

| 候选 | 为什么有价值 | 最小交付 | 不应扩大成什么 |
| --- | --- | --- | --- |
| #2596 的actor custom-loss支持集运输 | P0001的必要差异仍存在 | 一个custom_loss收到/未收到mask的回归测试，限定actor路径的修补 | 不为teacher/reference强制同一截断分布；不重复提交整套top-p实现 |
| staleness指标的分母澄清 | P10可直接重现扫描/消费差别，易影响调参 | 确认文档目标后改名或拆指标，保留旧指标兼容与一个两组测试 | 不改staleness阈值或样本策略来“修日志” |
| 可关闭的class-based rollout/buffer协议 | 真实长寿命worker和阻塞wait需要有界关闭 | owner-loop下的close、blocked put/get取消/唤醒和driver异常测试 | 不把rh2所有首因/审批/事件体系带进上游 |
| 原生版本区间的严格解析/覆盖测试 | H已提供结构，适合补精确边界 | 先明确哪些是引擎不变量，再测空/错类型/越界及裁剪 | 不把合法observation间隙判成损坏，不猜旧dump的token位置 |

本轮查询了相关代码、PR2595/2596和部分提交记录；**没有穷尽所有open issues/PR，也没有向外部仓库发评论、issue或PR**。正式贡献前仍应按最新head检查重复工作。负lag、missing reward排序等有上游明确设计测试，不能先当bug提报。

### 6.3 性能优化：优先度量真实浪费，不从重构推断加速

这次没有测出新的性能提升。H的debug dump去重、通用权重传输、原生span运输都可能降低维护或诊断成本，但不能据此给八卡配置预测百分比。

对当前项目更有价值的观测是：每组从生成完成到实际消费的版本变化；零信号步与发布次数；各类drop分母；有效逻辑execution数；关停和恢复是否重复/遗漏任务。**这些是用来选优化点的必要事实，不是要再建监控平台。** 可从现有事件和短脚本提取。

只有在某项改动不改变采样分布、信息可见性、loss与版本处置时，才可以主要用同样本正确性加系统性能证明它。missing reward排序、JIT取数、零梯度跳步都触及消费或更新语义，需要更谨慎的学习／分布对照，不能只看GPU利用率。

### 6.4 简历价值的准确归属

可描述的当前能力是：**对成熟上游进行版本化源码审读，沿真实agent路径发现语义兼容断点，并提供可运行反例及窄迁移方案。** 本轮不能宣称已经实现“训推一致性提高”“GPU吞吐提升”或“上游接受了PR”。

如果后续把一个候选做成真实修复、独立回归测试和匹配运行结果，它才成为实质工程成果。无需为了显得复杂继续增加框架功能，也无需把上游原生span结构算作自己的发明。

## 7. 修正了哪些旧认识，保留哪些限制

**本轮可以修正的版本结论：**H的session不再只读取单数版本；新Sample采用绝对区间并支持裁剪；控制面已拆为executor/controller，权重更新已通用化。这些修正只适用于H，不回写成旧U/I的事实。

**本轮确认仍存在的差异：**custom_loss支持集运输在PR最新head仍需适配；默认buffer仍不严格处理负lag/空版本；driver仍可能提前取下一批；消费指标仍含被拒组；所读关闭/恢复路径不等价于项目补丁。

**本轮新增的组合风险：**同字段名值类型漂移；missing reward预过滤抢先于formal校验；零更新跳发布与新通知守卫冲突。三者都要放在“升级组合”条件下，不标为当前I已发生事故。

未知项集中保留：完整I可重建性；16patch机械兼容；所有transfer protocols与实际SGLang RPC语义；retract/R3在冻结引擎版本上的状态；sm_120 kernel/依赖矩阵；真实训练偏差和吞吐；上游独立复现或采纳。本篇静态范围不覆盖这些问题，不借旧报告补答案。

## 8. 交付、自查与维护

本篇为N11的**增量伴随笔记**，不覆盖旧稿，也不批量修改共享README的数量和其他线程状态。审查记录：[作者自查](reviews/N11_miles_incremental_self_check_20260908.md)。本轮没有独立reviewer，不沿用此前其他论文的独立审查通过标签。

仅交付阅读正文、作者自查、隔离探针脚本和实测JSON。未修改训练实现、Sample公共schema、reward/loss定义、N阈值、数据集、pin、镜像、恢复或安全边界。执行这些候选前涉及的T0决定仍由用户选择。

## 一手来源与固定定位

[compare-u]: https://github.com/radixark/miles/compare/f2b7c79298a53c53861514d099f7def73bd29f4a...3de96596f16b9e6d23ba550c4c47de3479c9f14c
[compare-w]: https://github.com/radixark/miles/compare/d2fc97ce581577e255e494801d7568747d5a10d7...3de96596f16b9e6d23ba550c4c47de3479c9f14c
[manifest]: https://github.com/Rogerffff/RepoHarness/blob/32b615c4e4f869b448174e5974e7a8d29fc4612c/docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/integration_base_manifest.json
[patch-readme]: https://github.com/Rogerffff/RepoHarness/blob/32b615c4e4f869b448174e5974e7a8d29fc4612c/docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/patches/README.md
[patch1]: https://github.com/Rogerffff/RepoHarness/blob/32b615c4e4f869b448174e5974e7a8d29fc4612c/docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/patches/0001-rh2-integration-transport-sampling-mask-wire-fields-.patch
[patch2]: https://github.com/Rogerffff/RepoHarness/blob/32b615c4e4f869b448174e5974e7a8d29fc4612c/docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/patches/0002-rh2-integration-skip-optimizer-step-on-exactly-zero-.patch
[patch14-driver]: https://github.com/Rogerffff/RepoHarness/blob/32b615c4e4f869b448174e5974e7a8d29fc4612c/docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/patches/0014-rh2-integration-consume-time-staleness-as-the-single.patch#L560-L626
[p-generate]: https://github.com/Rogerffff/RepoHarness/blob/32b615c4e4f869b448174e5974e7a8d29fc4612c/rh2/src/repoharness2/adapters/miles/generate_fn.py
[p-canon]: https://github.com/Rogerffff/RepoHarness/blob/32b615c4e4f869b448174e5974e7a8d29fc4612c/rh2/src/repoharness2/adapters/miles/canonicalize.py
[p-group]: https://github.com/Rogerffff/RepoHarness/blob/32b615c4e4f869b448174e5974e7a8d29fc4612c/rh2/src/repoharness2/adapters/miles/group_admission.py
[p-loss]: https://github.com/Rogerffff/RepoHarness/blob/32b615c4e4f869b448174e5974e7a8d29fc4612c/rh2/src/repoharness2/adapters/miles/faithful_dis_loss.py
[pr2595]: https://github.com/radixark/miles/pull/2595
[pr2596]: https://github.com/radixark/miles/pull/2596
[pr-model]: https://github.com/nanjiangwill/miles/blob/d17f5716d92b936c6ac585fa6b6f318ba7dda8f8/miles/backends/megatron_utils/model.py#L486-L541
[h-types]: https://github.com/radixark/miles/blob/3de96596f16b9e6d23ba550c4c47de3479c9f14c/miles/utils/types.py
[h-session]: https://github.com/radixark/miles/blob/3de96596f16b9e6d23ba550c4c47de3479c9f14c/miles/rollout/session/samples/merge.py
[h-convert]: https://github.com/radixark/miles/blob/3de96596f16b9e6d23ba550c4c47de3479c9f14c/miles/ray/rollout/train_data_conversion.py
[h-driver]: https://github.com/radixark/miles/blob/3de96596f16b9e6d23ba550c4c47de3479c9f14c/train_async.py
[h-fa]: https://github.com/radixark/miles/blob/3de96596f16b9e6d23ba550c4c47de3479c9f14c/miles/rollout/fully_async_rollout.py
[h-buffer]: https://github.com/radixark/miles/blob/3de96596f16b9e6d23ba550c4c47de3479c9f14c/miles/rollout/fully_async_data_buffer.py
[h-filters]: https://github.com/radixark/miles/blob/3de96596f16b9e6d23ba550c4c47de3479c9f14c/miles/rollout/filter_hub/common_filters.py
[h-filter-tests]: https://github.com/radixark/miles/blob/3de96596f16b9e6d23ba550c4c47de3479c9f14c/tests/fast/rollout/test_filters.py
[h-version]: https://github.com/radixark/miles/blob/3de96596f16b9e6d23ba550c4c47de3479c9f14c/miles/utils/weight_version.py
[h-executor]: https://github.com/radixark/miles/blob/3de96596f16b9e6d23ba550c4c47de3479c9f14c/miles/ray/rollout/rollout_executor.py
[h-updater]: https://github.com/radixark/miles/blob/3de96596f16b9e6d23ba550c4c47de3479c9f14c/miles/backends/training_utils/weight_update/updater.py
[h-weight-session]: https://github.com/radixark/miles/blob/3de96596f16b9e6d23ba550c4c47de3479c9f14c/miles/backends/training_utils/weight_update/session.py
[h-model]: https://github.com/radixark/miles/blob/3de96596f16b9e6d23ba550c4c47de3479c9f14c/miles/backends/megatron_utils/model.py#L408-L660
[h-docker]: https://github.com/radixark/miles/blob/3de96596f16b9e6d23ba550c4c47de3479c9f14c/docker/Dockerfile#L1-L100
