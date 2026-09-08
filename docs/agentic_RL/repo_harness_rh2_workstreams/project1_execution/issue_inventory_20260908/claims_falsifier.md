# 项目一 A：旧主张反证与简化边界盘点

日期：2026-09-08。角色：Falsifier / Simplifier。目的：解释旧审查哪些结论成立、成立到哪里、哪些已经更正，以及哪些删除建议仍要决策；本轮不修代码、不批准训练，也不扩成全仓审计。

基线实查：主仓 `17d9899c6d4b61938f74bd9121da8dee9b621a8d`；`git diff --name-only ce2009f879cf38071d7898a1387e01d4e27741d6 HEAD -- rh2` 无输出；miles 集成 HEAD 为 `98a0272e4158b2c20e3a34d210c79b50159af0f6`。因此旧审查的 rh2 源码锚点仍适用。当前主线与前置以 `06-first-training-local-execution-plan.md`、D2/B 与当前状态简报为准，不能据未审 launch 草案认定 formal 作业已经就绪。

本轮证据：阅读指定两份 Codex 报告、Claude 总报告与 C/D/F 切片，定点读源码和配置，核对旧探针的报告结论；**没有重跑旧 CPU 探针、pytest、GPU 或 Docker**。下面的历史数值均显式标为旧证据。本文件不是新一轮独立运行验收。Codex F1/F2/F3/R1 的原始记录见 [2026-09-05 审查](../../miles_spike/external_infra_review_20260905.md)。

## 1. 先固定版本：Claude 已经纠正了哪些说法

[Claude 总报告](../../tmp/external_review_20260905/00_FINAL_REVIEW.md) 顶部的 **2026-09-07 勘误** 明说：与正文及切片冲突时，以勘误和 [2026-09-06 交叉复核](../../miles_spike/external_infra_review_crosscheck_20260906.md) 为准。它已采纳以下纠正，不能继续把旧切片原文当 Claude 的当前立场：

- REALIGN 可损失前序训练信号，但“所有多轮必掉首轮”不成立；当前生产模板不读 `clear_thinking`，直接关它不能修好问题；真实 CC 漂移根因仍待定。
- 连续零梯度熔断已通过 YAML 配成 8；在线 `logprob_compare` 已存在；额外 actor forward 同时产对拍证据，20–30% 加速没有本项目实测。
- 晚清理成功仍保留早期超时的机制存在，但“正常结束必失败”不成立；退出码忽略关停失败属于 B-6 改判。
- 超时、零解析一律 reward 0 缺少“可归责 agent patch”的前提。
- `DispositionPolicy` 无生产注入是 C/W7 已计划接线缺口；四槽改一槽不能先替 A5 决定。
- “约三分之一可删”只是方案预算；所谓第一批无语义改动混入了 formal 默认值、filter、eval、退出码与资源变更。

因此这里保留旧 P0/C/D/F 编号供追溯，**不再把 P0 标签当作已经证实的严重度**。一个事项可以是“启用正式入口前必须闭合”，同时并非“现成正式作业发生的 P0 回归”。缺口已经登记不等于可以忽略；它只改变问题类型和安排位置。

## 2. 十个核心纠正及源码锚点

下文源码简称：`R/` = `rh2/src/repoharness2/`；`S/` = `rh2/src/slime/`；`M/` = `reference/miles-rh2-integration/miles/`。所有行号均为当前基线，不是外部上游 main。

### 2.1 截断无 disposition：有条件的配置缺口，不是每个超时必停

`R/governance/admission.py:611–647` 的顺序是先判断事实矛盾、合法不合格，再对可保留的 `present_truncated` 读显式处置；`R/adapters/miles/group_admission.py:515–523` 缺配置时返回四槽全 None；filter 在 `:544–554` 通知 fatal 并重抛。因此准确触发条件是：**进入 formal 准入、成员形成 present、此前未因其它理由 DROP/FATAL、截断需要的槽未注入**。不是任意超时，也不是第一条样本。

例：同样 600 秒结束，若评分失败已产生 DROP，根本走不到缺处置分支；若评分成功、capture 完整，确为 `present_truncated`，且槽为空，才触发 `DispositionNotInjectedError`。KEEP_FULL 与 DROP_GROUP 均有接口，不存在偷偷替 owner 选 KEEP 的默认答案。

缺口必须在 C/W7 接线时消掉，并可将缺配置拒绝前移到启动期。`06` 的 A5/§4 D1 明确“处置归 C，先 fail-fast + 双注入中立”；这解释了当前状态，不构成继续空配上线的理由。把 policy horizon（如模型调用预算）与基础设施墙钟合并一槽，则改变归因选择，仍是待决设计。

### 2.2 所有评分失败改 reward 0：会把机器坏了教成模型错了

事实缺口成立：`R/grading/manager.py:1463–1470` 对 setup/test 的超时都抛 infra；`:2007–2027` 把 parser 异常与零解析统一判 `test_log_parse_failed`；`R/contracts/grading.py:41–47` 的 `test_execution_timeout` 生产分类器明确尚未实现。

但已批规则不是“测试阶段超时都为 0”。`fa/fa2a_decision_package.md:148–161` 与同一契约要求三项全真：clean grader 正常启动、预算确定、超时可归责 agent patch。真实例子是候选引入死循环；反例是机器缺 Python、容器被资源压力杀死、原始任务在同预算下也跑不完。它们发生在 test 阶段仍不代表模型修复错了。

历史交叉复核的 `grading_classification_probe.py` 表明：候选源码 SyntaxError 与环境缺 Python，在当前官方 PASS_AND_FAIL parser 下都可得到“标记齐、status map 空、reward 0”；RH2 都判 parse infra。它既推翻旧“空日志必 silent-success”的注释，也推翻“空解析足以归责模型”。**计数相同不等于原因相同**。准备期 empty-patch 门能支持归因，但不是运行期永不发生 infra 故障的证明。

应先把确定性 parser/spec 不支持作为输入配置问题暴露，再明确什么候选失败可以可靠地记 0；真正暂态 infra 仍需保持 reward unavailable。新增重试、同 task 连续 N 次熔断、或一律 0 都改变样本/资源语义，不是十几行代码就自动免决策。

### 2.3 accepted、singleton、非零 advantage 与非零梯度是四回事

singleton 指某 token 的采样支持集只有一个候选。重归一化后该候选概率恒为 1，logprob 恒为 0，所以即便 DIS ratio=1、被计为 accepted，它也没有该目标的局部 logits 梯度。这是已选目标的数学性质；不是凭此发现 loss 公式算错。

历史 `singleton_signal_probe.py` 的真实 dispatcher 结果为 accepted=2、loss=0、梯度=0。支持集大于 1 也不能证明总参数梯度非零：两份相同模型输入产生相反梯度 `+g` 与 `−g`，加总正好为 0。历史两组 n=8 的探针给出 16 个 accepted、支持集均为 2、advantage 均非零而最终抵消的例子。这只证明逻辑反例，不说明 30B 真实训练频繁抵消。

明确误报：`rh2/experiments/miles_gpu_spike/custom_config.yaml:20–27` 已设 `max_consecutive_zero_signal_steps: 8`；`launch.sh:233–240` 检查文件，`:424` 传 `--custom-config-path`。库缺省为 0 和候选 profile 已配置为 8 可以同时为真。最终阈值仍归 C；“无限静默跳过”不是这份候选配置事实。

因此可以增加支持集分布、有效 token 与 skip 诊断；不能仅据非零 advantage 删除已批 patch 0002/0003。用 `grad_norm == 0` 代替现扫描，还需证明归约时点、数值精度和 optimizer 调用顺序等价。

### 2.4 60/180 秒关停：先分清期限失败和清理结果

`M/rollout/fully_async_rollout.py:59` 默认 60 秒是 worker/group 取消等待预算；`:297–308` 并发 cancel 所有剩余 group，再记 unfinished。`R/shutdown/chain.py:333–334` 的 30+150 秒是后续 RH2 宽限/取消等待，两者不是每个容器串行各耗 180 秒。

`M/utils/rh2_shutdown.py:228` 在第一段后记 failure，`:295–296` 最终仍要求它为空。因此“60 秒内没结束，90 秒时后续清理完成，最后仍失败”确实可发生。历史缩时探针已证明此机制，也有期限内正常成功的对照。`D2/B:90–92` 的 B-6 已规定不 ok 即非零退出；保留早期期限违约并不违反这个合同。

“正常 fully async 结束必有满额容器且必超时”不成立：取消可并发，完成组和评分前提前释放的容器不再需要删，120 秒只是某清理操作上限。可以决定统一总预算或保留分段预算；让退出码只反映 trainer 成功属于 T0 改判。F-02 的“evidence 失败不阻断 cleanup”和“evidence 失败让整体 ok=false”也不矛盾：`chain.py:434–463` 明确同时保留这两件事。

这与 Codex F3 不同：F3 是 receipt 写失败**直接跳过**本应执行的清理，不是清理晚了一点。

### 2.5 F2 官方文件保护：另一攻击面开放，不推出已有边界无用

此处 F2 指 grader 文件保护，勿与零梯度 F2 混淆。`R/grading/manager.py:1936–2000` 顺序为 root trusted setup、独立读回自证、保护文件、非 root 候选测试。`R/adapters/slime/sandbox_profile.py:1260–1304` 将 official 文件设为 root:root 0644、祖先设 sticky，并拒绝无法保护的缺失/非普通路径。候选 import 期间改写稍后收集的官方测试，是这层确实阻断的路径。

stdout 伪造、插件和 `conftest.py` 等其它路径尚待 environment adapter 定义，这是已登记的边界不完整，不证明“候选改 official 文件”不存在。把候选改为 root 会重新打开已封闭路径。重复全树 chown、逐文件复核是否能合并可以按收益讨论，不能借此把非 root 与官方文件不可改一起无条件删掉。

缺失路径的限制也必须如实说：当前冻结 216 题的 official patch 统计是新增 8/删除 0/改名 0；不是已观测这批题因官方删除/改名大量损耗。D-06 提到的未来 task 适用性问题成立，当前出现频率和整组损耗量未实测。

### 2.6 “同一进程”不是“同一事实一生不会变化”

`R/adapters/miles/generate_fn.py:167–177` bind 后跨整个 `await rh2_custom_generate(...)`，到 `:212–214` 才 release。`R/adapters/slime/bringup.py:1545,1557` 在任务解析与评分材料解析阶段各用 assignment。C-06 的“同一调用栈”省略了这个长时间异步生命周期；样本 metadata 是可变对象，不是编译器保证的不变量。

真实组约束也不只有槽集合：`R/adapters/miles/group_admission.py:304–338` 核叶版本与 outcome 的子集/上界，`:415–452` 核 fan-out 叶身份、reward 与形状，`:455–476` 核同组同题和身份唯一。例：8 个 slot 都齐，但 slot 3 的一片叶来自另一题、reward=1 或版本 999，单看 slot 仍会放行。这个例子说明删除方案缺少的保护条件，**不是声称生产已发生串样**。

可以用不可变 execution context、集中一次构造与边界消费减少重复校验；删前须证明这些绑定仍由哪个消费者承接。只运输 `verdict=KEEP_FULL`、保留 slot 完整，不能自动等价于现有实际 Sample 的绑定。C-05 的 19 处静态位置也不等于每个 execution 恰执行 19 次；“不到 10%”是作者分类判断，不是故障发生概率。

`TerminationFactsPayloadV1` 确实重复很多字段，但 `R/envpack/termination_facts.py:222,227–228` 还含 receipt、quiescent、frozen patch 事实；`generate.py:3621–3633` 只有 receipt 写成功才派生。故“整个模块是 outcome 完整副本、整删零语义损失”过强。合并时须保留先落 receipt 再交付的顺序及必要锚点。

### 2.7 W8、W7、readiness：小 bypass 不能替代整个前置

formal 的 eval 身份问题成立：`generate_fn.py:142–150` 按模式铸造，不区分 `input.evaluation`；当前 stock eval 样本不满足 train group 算术。W8 正是尚待完成的正式 eval 运输，不是完成后退化的入口。

`06:144` 对 W8 还要求：同环境解析器、train/eval 身份分离、producer/grading/update 停止、两个显式 checkpoint digest、skip/failure 不洗成成功。故“if evaluation 直通”只是候选局部方案，不能据 15 行估计宣告 W8 已闭合。`06:145` 规定 W7 从最终范围重生成 launch/collector/judge/thresholds，明确不继承未审草案。

同理，草案 `s1_compat` + stock filter 说明它不是 formal 作业模板；如果只改 mode、不改 filter，才会按 `generate_fn.py:80–95` 拒绝。缺 disposition、trap、`run_restarted` / `engine_versions_after_publish` 消费、no-progress 数值仍必须在各自入口启用前完成。它们是已知 readiness 阻塞，不是一组现在就应大规模重构的运行事故。

### 2.8 未发现 mismatch 与多余 forward：同一条证据被两处说反了

`M/backends/megatron_utils/actor.py:483–520` 定义并发射 `logprob_compare`，`:625–665` 将额外 actor logprob forward 与事件连接。关闭该 pass 同时失去这份对拍证据；`use_rollout_logprobs=true` 且 `get_mismatch_metrics=true` 又会保留 pass。因此“在线完全缺失”与“现有 forward 毫无用处”不能同时成立。

当前零 KL GRPO/custom loss profile 可将它作为优化候选，历史 CPU 探针支持数值不变，但未证明真实 GPU 节省 20–30%，也不能推广到 PPO/OPD/KL。准确缺口是 custom loss 的 ratio、支持集与拒绝原因指标还不够丰富，以及最终 collector/judge 尚待接线。跨版本 log-ratio 同时含策略改变与数值差，改名 mismatch KL 不会自动分离两者。

### 2.9 C-08 handshake：方法在 formal 调用，不等于空 seen 分支可达

`R/adapters/slime/generate.py:3346` 确实调用 `_build_handshake`，`:4213` 也确实写 `seen or [current_version]`。但正常正式 producer 的前置是：`:1648–1678` 强制 require_real 与非空数值 policy_version；`:2869–2873` 拒绝空 samples；`:2910–2918` 对每个叶做 backfill；`:1496–1501` 在入训 tape 缺真实版本时提前抛错；成功后 `:1507–1508` 写入非空 `sample.weight_versions`。甚至 used 为空时也会先写非空 policy_version，而这种零可训 token 叶后续会被 `projection.py:694–700` 拒绝。

所以 **正常 formal producer 产出的叶，到 handshake 时 seen 不应为空**。直接给 helper 空版本叶可以触发 fallback，但那是构造输入反例，不能当成生产会用 current 冒充真实 seen 的证明。除非再证明 backfill 之后字段被改坏、旁路替代 producer 或其它配置路径，否则 C-08 应定位为 helper 兜底与事实措辞的简化候选，不是已证版本资格绕过；连“直到 filter 才挡”的时序也不能笼统沿用旧说法。

### 2.10 F-11 冷恢复：两个版本问题要分开

第一项是已批命名语义：B-3（`decision_package_D2_B.md:75–78`）明确恢复时 bootstrap 标 p，真实更新标 p+1；`M/utils/rh2_recovery.py:214–217,257–262` 的 p−1 和首次 publish=p 正是在落实该决定。旧在飞/buffer 全丢，跨 run 裸 version 不具全局唯一意义；观测需按新 run_id 区分。将 p−1 改 p 会改变已定重启版本标签及验收，不是“代码一行、语义零成本”。它也不能让任意多次回到旧 checkpoint 的全部未来版本号天然全局唯一。

第二项是**显式覆盖 start-rollout-id 与实际载入 checkpoint 的绑定风险**，不能用第一项的已批语义替它开脱。Megatron `actor.py:205–220` 从 checkpoint 得到 `loaded_rollout_id=k`，而 `rh2_recovery.py:227–232` 在显式 `args.start_rollout_id=N` 存在时直接取 N−1，不核 k；`M/ray/placement_group.py:188–196` 也保留显式 N，在 `rollout_global_dataset` 启用时让 RolloutManager 读 N−1 的 data source 状态。

例：实际权重载入 checkpoint 10，却显式填 start=21；目录又同时有 rollout 20 的状态文件。trainer 与 RolloutManager 都可能读到 20 的版本/游标，两侧互比通过，仍没证明这些状态与权重 10 配对。若 20 状态文件缺失则会提前报错；若没有显式 override，则默认 k+1 路径不存在这个偏移。本轮只有源码链证明，未执行恢复或 GPU；最终 W7 launcher 是否开放此 override 也未定。该事项应与裸版本跨 run 重用分成两项，保留作恢复入口启用前的具体绑定检查。

## 3. 旧 ID 逐条映射

标记：**保留** = 核心事实成立但不自动采纳原严重度/方案；**收窄** = 原文超出证据；**已纠正** = 2026-09-07 已采纳纠正；**已知前置** = 启用相应入口前必须完成；**设计候选** = 需保留不变量后再决定。对非核心条目沿用旧源码锚点作定位，不声称本轮已复现其生产影响。

### 3.1 总报告与前轮 Codex

| 旧 ID | 当前解释与成立条件 | 锚点 / 后续归属 |
|---|---|---|
| Claude P0-1 | 保留训练覆盖缺口，已纠正“所有多轮必掉首轮”和 thinking 开关修法。阈值看新输出；rewrite merge 另看旧输出。 | `S/agent/trajectory.py:169–224,411–426`；先决定 harness 训练覆盖语义。 |
| Claude P0-2 | 已知 C/W7 接线缺口；只有进入可保留 truncated 分支才缺处置 fatal。25 次 cap、proxy/deadline/drain 是独立运行归因问题，不能全用一个 disposition 修掉。 | `R/governance/admission.py:611–647`；C/A5 + 预算 producer。 |
| Claude P0-3 | 通用 grader 归因面保留；parser 缺口是 T2-d 已知前置；所有失败记 0 的推荐已纠正。 | `R/grading/manager.py:1463–1470,2007–2027`；T2-d/环境归因。 |
| Claude P0-4 / Codex F2 | 结构异常被 ABORTED 收口的核心保留；不能把所有 drain/capture 超时都当结构矛盾，也不能把未证实缓存返回/子 agent 假设直接算事故。 | `R/adapters/slime/generate.py:3409–3449`；以缺 response id → failed record 无 tape → backfill ABORTED 的旧生产形状注入为具体证据。 |
| Claude P0-5 | 已知 W8/W7 前置；切 mode 后仍挂 stock filter 会被挡，非当前草案已经运行 formal 出错。 | `generate_fn.py:80–95,142–150`；`06:144–145`。 |
| Codex F1 / Claude T1 | R3 转换/持有成本保留；历史 CPU 测量不等于 GPU 吞吐损失。“按 session 只留最后一轮”不能覆盖 fan-out 多叶需要。 | `R/adapters/slime/generate.py:869–988,1427–1468`；局部表示优化，先保叶覆盖。 |
| Codex F3 | 保留现合同与旧清理分支冲突；仅在 receipt 失败且容器尚未提前释放时留容器，不是所有 receipt 失败都留容器，也不是 session 永不撤销。 | `generate.py:3598–3619,3646–3652,3767–3775`；既有 ENOSPC 探针，按现 A4 修复边界。 |
| Codex R1 | 多轮 leaf 采用最后整段路由而早轮 logprob/version 仍按原轮，来源替换保留；不等于已证明 DIS 梯度公式错误。 | `generate.py:1427–1468`；C 决定近似/拆 turn/缩 profile，GPU 内容对拍。 |
| Claude §2.3 singleton / zero-grad | accepted 高估有效局部信号保留；“全局零只能全 DIS 拒或 singleton/bug”被抵消反例推翻；8 步 fuse 已配。 | 本文 §2.3；不据此直接删 0002/0003。 |
| Claude §2.3、§5 mismatch / T2 forward | 在线完全缺失已纠正；forward 优化与诊断保留要同时决策，收益未实测。 | 本文 §2.8。 |
| Claude §3–4、§7–8 删除总计划 | 约 1/3、12–14K 等只是估算，非无语义删除量；默认 formal、改 filter、eval bypass、降保护、改退出码不能混作 T2。 | 总报告勘误 9–10；逐项 owner/契约/生产消费者再分期。 |

### 3.2 Claude C-01 至 C-15

| 旧 ID | 判定与反例 / 限制 | 源码定位与最小决策面 |
|---|---|---|
| C-01 | 已知前置；无生产注入成立，“生产必炸”必须补 formal + 合格 truncated 条件；四槽改单槽未定。 | `admission.py:635–647`、`group_admission.py:515–523`；见 §2.1。 |
| C-02 | 已知 W8 前置；train 身份假设不适配 eval 成立，直接 bypass 不能替代 checkpoint/环境/失败传播要求。 | `generate_fn.py:142–176`、`M/rollout/inference_rollout/inference_rollout_eval.py:76–83`；见 §2.7。 |
| C-03 | 当前缺 anti-cheat/policy_horizon producer、formal security 无执行违规证据可产生失败的事实保留；不等于 sandbox 没有防护，也不自动授权删公共槽位。 | `generate.py:4470`、`gate.py:389–432`；执行级事实与创建期 profile 是不同层。 |
| C-04 | 重复运输是合并候选；“完整副本、零语义整删”收窄，receipt/quiescent/frozen 信息不能凭空消失。 | `termination_facts.py:222–231`、`generate.py:3621–3633`；见 §2.6。 |
| C-05 | 重复自检维护成本保留；19 静态位置≠19 次真实执行，<10% 不是生产概率；slot 不能替代叶/reward/version/同题绑定。 | `group_admission.py:304–338,415–476`。 |
| C-06 | registry 可以以不可变 context 替代；“刚写后立即查回、没有状态边界”收窄：bind 跨 await 生命周期，到 finally release。 | `generate_fn.py:167–214`、`bringup.py:1545,1557`。 |
| C-07 | GroupRepairSignal 在 miles 准入没有决策消费者、仍有 telemetry/S1 消费；局部收缩候选，不是全仓无消费者。 | `generate.py:4491–4536`、`bringup.py:1144–1146`；保留冻结 S1/历史协议时不能直接全删。 |
| C-08 | helper 有 fallback，但正常 formal 叶先经 backfill 写非空版本；空 seen 臂未证生产可达，不应报成 formal 伪造版本后到 filter 才挡。 | `generate.py:1648–1678,2869–2918,1496–1508,3346,4213`；见 §2.9。 |
| C-09 | ID 格式检查可简化，“对手不存在所以删全部历史”证据不足；格式匹配也不能证明这段历史真的发生过。 | `identity.py:194–254`；若禁止 retry，可缩对应支持面；否则保留 fresh/retry/单调计数语义。 |
| C-10 | miles 载荷与派生键重复保留为候选；offline export 有消费者，删除公共 derived 字段不是零语义清理。 | `generate.py:4655–4658`、`R/contracts/eligibility.py:212–222`、`R/contracts/export.py`。 |
| C-11 | 配置错误前移启动合理；formal filter 核对本身保留，草案 stock filter 属 W7 重生成。 | `generate_fn.py:80–95`、`bringup.py:1700–1725`。 |
| C-12 | 降 sidecar 失败为继续训练不采纳为“显然 bug 修复”；现 A4 对核心 admission 记录要求 run-fatal 且继续 cleanup。 | `generate.py:4512–4528`、`06` A4；若更改记录角色需 owner 决定。 |
| C-13 | 启动 digest/权限/可见面保护保留；重复 revalidate/deepcopy 可以查收益，不能只因同进程删后继续信 mutable 对象。外部 SHA 不只是防 owner，可识别错用 prep。 | `R/envpack/prepared_tasks.py:380–503`、`R/envpack/training_view.py:246–273,375–395`。 |
| C-14 | `branch_without_trainable_tokens` 先于 gate 的 no_trainable_tokens 路径保留为语义不一致；不得直接接受“ABORTED 也合理”，先看是否 generated 信号被装配丢光。未知 reason 改 DROP 会新增拒绝。 | `R/adapters/slime/projection.py:694–700`、`generate.py:3445–3449`、`admission.py:594–612`。 |
| C-15 | 文档漂移保留；当前 staleness age 只有 consume-time 阈值，不能据旧 docstring 重报双重过滤。 | `R/contracts/eligibility.py:98–100`、`generate.py:4198–4216`；文案清理可独立。 |

### 3.3 Claude D-01 至 D-18

| 旧 ID | 判定与反例 / 限制 | 源码定位与最小决策面 |
|---|---|---|
| D-01 | parser/spec 零覆盖是 T2-d 已知前置；若错误上线会持续 drop 的风险保留，“100% 静默永不停止”须限定是否启用 no-progress、事件及任务混合。 | `R/envpack/scoring.py:121–128`、`manager.py:2007–2013`；选定 adapter 后准备期预检。 |
| D-02 | timeout→infra、负样本 producer 未实现保留；改 0 须满足三条件，phase=test 不够。 | 本文 §2.2。 |
| D-03 | silent-success 注释不符当前 PASS_AND_FAIL 调用的纠正保留；零解析可能是候选 SyntaxError，也可能缺 Python；不能全改 0。 | `manager.py:2021–2027`；本文 §2.2。 |
| D-04 | cache/build 产物可进入 census/delta 的成本候选保留；“跑一次测试必产成百上千 entry”不是测量，取决于环境/配置。排除区改变冻结契约。 | `R/adapters/slime/baseline_census.py:61–78`、`manager.py:1795–1808`；先量占比。 |
| D-05 | glob 可能把随包源码误分控制面成立；`*testing/*` 也能匹配 `_testing/`。“排除即 reward 0”过强，最终 reward 仍取决于其它修复；这些路径是否属于最终 taskset 需数据证据。 | `manager.py:243–244,538–545`、`R/grading/trusted_projection.py:79–88`；exact-only 会收窄已定控制面。 |
| D-06 | 不因 stdout/plugin 未闭合就删 F2；保护 official 文件是实际不同边界，root 候选方案降低安全。缺失路径目前拒绝，216 题实际损耗未证。 | 本文 §2.5。 |
| D-07 | 细故障成因在粗聚合桶坍缩值得补；detail/evidence 已存在，故非全无可观测性。一次重试/连续 N 停机是方案，不是既有定案。 | `gate.py:451–454`、`R/adapters/miles/drop_events.py:156–160`；按真实归因拆码。 |
| D-08 | 重复 image/baseline 验证是摊销候选；每容器运行参数/cgroup 事实并非仅由 image ID 决定，缓存不能替代所有 prelaunch。17→4 次含删 F2，不能算纯优化。 | `manager.py:1372–1418,1475–1503,1662–1739`；拆不可变镜像事实与实例事实。 |
| D-09 | records/leases/events 生命周期未裁剪的风险保留；20k×50–500KB=1–10GB 是估算，非测得 RSS。 | `manager.py:873,1253–1263,1360–1367,1949–1976`、`R/grading/queue.py:117`；先保清理在飞事实再裁历史。 |
| D-10 | 并发 4、队列 8 可调；“几乎必然瓶颈”无负载测量，主机核数和每题 3min 是假设；并发加 16 会加内存/I/O 争用。 | `bringup.py:1001–1007`、`queue.py:153–201`；C profile 按 wait/utilization 定。 |
| D-11 | 4GiB OOM 可能影响评分且需诊断；“这些 repo 系统性判 0”未实测。137 也不独证 OOM；16GiB 不是无条件 T1 小改。 | `R/adapters/slime/sandbox_profile.py:492`、`R/adapters/slime/prepared_task_face.py:85–92`、`manager.py:1471–1473,1993–2002`。 |
| D-12 | producer/grader 重算可合并部分工作；“程序错误所以检查是死代码”不成立。至少保实际重放集合、HEAD、baseline 与身份绑定。 | `manager.py:1541–1739`、`trusted_projection.py:25–28`。 |
| D-13 | formal profile 下 lease 派生 network 参数不再主导，列表无消费是局部清理候选；legacy 仍消费，不能笼统删类型及全部路径。 | `manager.py:1303–1367`。 |
| D-14 | 命名漂移保留：image_embedded fresh 容器路径主要做 lineage probe，不能把没 git clean 当成未隔离评分。 | `manager.py:1506–1539`；可独立改名/文案。 |
| D-15 | 部分自测探针可迁测试；不能笼统叫所有 quota 探针无价值。可写层预算未强制本就登记 R1，删除探针也不会解决它。 | `sandbox_profile.py:1079–1155,1776–1960`；保真实 profile 取数。 |
| D-16 | 超时未主动 kill docker exec 客户端的生命周期问题保留；后续 finally rm 容器限制其存活，不能声称测试会永远继续。 | `manager.py:66–80,1463–1470`；退出资源证据再定修法。 |
| D-17 | 原例 `delete module.py + add module/__init__.py` **不触发**按 `/` 的父子前缀检查；有效例应为 `delete config + add config/default.json`。泛化限制可保留，影响题数未知。 | `R/contracts/frozen_patch.py:129–134`；`manager.py:1795–1806` 已先 delete 后写。 |
| D-18 | formal 不走的 S1 diff 路径是冻结兼容能力，非坏代码；原报告本已不主张现在删。 | `manager.py` legacy 分支与 `build_swe_grading_spec`；待显式退役。 |

### 3.4 Claude F-01 至 F-13

| 旧 ID | 判定与反例 / 限制 | 源码定位与最小决策面 |
|---|---|---|
| F-01 / B1 | 超时后晚清理成功仍失败机制保留；“正常结束必失败”已纠正；忽略 shutdown 失败是 B-6 改判。 | 本文 §2.4。 |
| F-02 / B2 | evidence 失败使 ok=false 是当前实现和 H9 定义，不与“不阻断 cleanup”矛盾；删除资源证据/退出影响是设计取舍。 | `R/shutdown/chain.py:434–463`；`06` W5a 承接一次资源闭包取数。 |
| F-03 / B6 / B7 | fuse 未配置已纠正；全局零梯度推断不完备；distributed optimizer 梯度视图/扫描时点的具体等价性仍需专门证明，不能据“方向安全”省掉验收。 | `M/backends/megatron_utils/model.py:424–513`、候选 YAML:27；本文 §2.3。 |
| F-04 | router 不读 session key 保留；最小负载不是均匀独立随机，不能直接算 1/N 命中率或 10× 成本。单 engine 无该分流问题。 | `M/router/router.py:134–162,215–230`；亲和策略/TP 拓扑由 C matched comparison 决定。 |
| F-05 | RH2 自己 backfill 不调用 stock `update_from_meta_info` 的路径事实保留为维护候选；0008/0009 含 Sample/事件兼容面，不能据默认路径未调就整 patch 零语义删。上游已取代是旧快照描述。 | `M/utils/types.py:384`、`generate.py:505–590`；先列 pin 上具体消费者。 |
| F-06 | tape digest/事件成本值得量，judge-only 不等于无价值；首训资格正需要守恒/R3/同版本证据。只保四类事件或移 hook 要先保验收覆盖。 | `M/ray/rollout/rollout_manager.py:295`、actor.py:561、`06:145`；耗时为估计，非实测。 |
| F-07 | fork 随上游结构变化的维护风险保留；302 commit、9/16 rebase 困难是 09-05 调查快照，本轮未重查外网。不能用此证明立即删 0002/0003/0012 语义等价。 | 原 F-07、integration manifest；首训 pin 保持，缩面另开设计。 |
| F-08 / B3 | Ray 包装可能使文本同源识别失效是合理待验主张；旧报告自己声明未跑 Ray，不能把“恒 false”当运行实测；还要区分其它关闭触发源。 | `M/utils/rh2_shutdown.py:162–176`；真实 Ray 错误包装补验再决定。 |
| F-09 / B4 / B5 | 后台 loop 无法装主线程 signal handler 的 topology 限制保留；drain 后不交付 buffer 不等于评分结果/receipt 没有生命周期用途。晚到事实合并也有 filter fatal→dispose 的真实顺序。 | `bringup.py:1758–1769,2026–2129,2250–2265`；删等候/合并须先改变其合同。 |
| F-10 | publish ack 与逐 engine 实际读回是不同证据，缺陷/漏发不是“对手不存在”；读回只证明标签，不证明权重张量正确。价值和成本可以测，不凭同进程措辞删 W10 最小正确性。 | `M/ray/rollout/rollout_manager.py:577–592`；已批 B-5/W10。 |
| F-11 / B8 | p−1 是已批冷恢复标签语义，改 p 并非免费修 bug；另有显式 start=N 忽略实际 loaded=k、两侧同读错误 N−1 的绑定风险，应分两项。 | `M/utils/rh2_recovery.py:214–245,257–262`、`M/ray/placement_group.py:188–196`；见 §2.10。 |
| F-12 | consume-time 唯一权威/JIT drain 保留；负 lag 与缺版本 raise 抓的是账实矛盾，不因自洽检查就无用。no-progress 缺最终阈值归 C/W7，和 fuse=8 的已配状态不同。 | `M/rollout/fully_async_data_buffer.py:407–447`、`06:156`。 |
| F-13 | 重复事件/身份断言为局部候选；`sys.exc_info()` 旧报告已核非 bug。900s 上限内的清理边界不等于有 GPU/进程外残留实测。 | `reference/miles-rh2-integration/train_async.py:213–225`；F-13 原文范围保留。 |

## 4. 如何保留简化收益，而不把结论改坏

可先按当前消费者证明清理原型，例如 Codex 已给出的 `adapters/miles/attempt_ledger.py` / `governed_buffer.py` 及专用测试维护面；这个范围不推出其它公开 CLI、历史 inspector、offline exporter 或 schema 都可删除。老报告估算的 1478 行也只是明确维护面，不是加速比例。

需要重设计而非直接删除的集中点有四个：准入载荷与终止事实合并；跨 await assignment 改不可变 context；timeout/失败归因；shutdown 的期限与退出码。每个方案至少说明保留什么生产绑定、删除什么能力、真实失败如何暴露，以及哪条已有定案被改变。不应为它们新增 ledger、WAL、通用规则引擎或第二个恢复服务。

“检查只防自己 bug”不足以删检查；“检查很多”也不足以证明这些检查有用。正确反证方法是：找真实 owner/运输/异步边界；证明事实不可变或有替代消费者；用成立条件严格的反例检查简化后是否还拦得住。相同原则同时适用于主链 catch、group admission、grading 与关停，不能在主链要求内部 bug 必须暴露，到了准入就把防内部错接一律说成官僚。

本轮停在旧主张映射与核心纠正，未改变已定三终态、全员 KEEP_FULL、faithful DIS 分母、consume-time 唯一 staleness、F2 安全边界或冷恢复语义。后续项目一 A 逐项决策应优先围绕真实训练覆盖、已证异常分流、receipt 清理以及尚缺生产证据的算法/资源取舍展开。
