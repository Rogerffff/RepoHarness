# miles 迁移 spike 日志（活文档）

目的：为"rh2 训练后端是否从 slime pin 迁移到 miles"收集 Go/No-Go 证据。闸门定义与预注册见 `../tmp/miles_migration_gate_and_spike_plan_20260824.md`（G-M1~G-M7）；决策背景见 `../tmp/fa_vs_miles_architecture_review_brief_20260823.md`。本文件是 spike 的唯一进度与结论权威，按批追加，不重写历史条目。

约定：每条记录 = 做了什么 / 产物在哪 / 结论。产物中 scratchpad 指本机会话目录（`/private/tmp/claude-501/.../scratchpad/`，机器重启可能丢失——关键结论必须回写本文件）。

## 已定决策

| 日期 | 决策 | 依据 |
|---|---|---|
| 2026-08-24 | 用户批准：F2-4 前停,插入 miles 迁移闸门;过门则整体迁移(miles 管通用异步层,rh2 留治理层,适当耦合可接受,红线=不 fork miles 核心语义);不过门回退现链路;verifiers 环境扩展独立推进;slime 链路冻结为回退面直到 miles 等价闸门绿 | 本线程用户确认 |
| 2026-08-25 | 中期判定 Conditional Go(我方+codex 独立一致):继续本地纵切,硬件段并入下次合并短租;最终 Migration-Go 等租期五项全绿(sm_120 镜像/4+4/R3-on/权重更新语义/逐 token logprob parity) | 下方 S1~S4 + codex R2/R3 |
| 2026-08-25 | CC 接入形态**定选形态甲**:vendor slime agent 层(~1800 行)做冻结兼容包 + miles legacy custom_generate,保留 stage/commit、capability、poison、drain 纪律。形态乙(miles session server TITO)降为远期备选,理由:TITO mismatch 只记 metadata 不阻断、并发关闭时"已交付不记账"、session id 明文 URL 无认证——三条均违反 rh2 fail-closed 纪律 | S2 映射 + codex R3 §3 |
| 2026-08-25 | 用户批准执行 P0-1 vendor 纵切;要求维护本 spike 日志 | 本线程用户确认 |
| 2026-08-25 | **T0-A 拍板**：暂取选项 1（top_k := 有效 vocab size 作为硬件 spike 实验配置）,实测 mask 体积/显存/吞吐后再定正式实验配置——现在不锁定 | 用户决策 |
| 2026-08-25 | **T0-B 拍板**：双 logprob 列（behavior_support_logprob 作 DIS/TIS 正式分母 + model_full_vocab_logprob 仅诊断,带 provenance 枚举） | 用户决策 |
| 2026-08-25 | T1：暂保留 vendor 的 openai.py/codex.py 不裁剪 | 用户决策 |
| 2026-08-25 | 用户批准：新建迁移分支,执行 GPU 前 CPU/CI 前置;新 T0 或需外部 codex 检查时停下汇报 | 用户决策 |

## Spike 记录

### 2026-08-25 S1：top-p tape 解剖（G-M3）
做了什么：解剖 slime `docker/patch/latest/sglang-top_p.patch`（929 行/17 文件）全链（patch 面→slime 消费链→rh2 契约依赖→miles 空位）；将 patch 对 sglang-miles HEAD 做 fuzzy dry-run（scratchpad/sglang-miles-checkout，46 hunk 中 25 failed + 6 ignored，核心文件 layers/utils/logprob.py 已不存在）。
关键事实：tape 实为 top-k∪top-p∪min-p 联合保留集；开 tape 会改写 rollout_log_probs 为 nucleus 重归一化值；force-keep sampled token 是引擎/训练**双端不变量**；rh2 契约层 schema 级硬依赖（top_p<1.0 无 tape 不可表示）；faithful_dis.py 代码零 top_p 依赖但 FA-4 预注册项"top-p replay 是否参与 current logprob"未定案。
结论：旧 patch 移植 = 实质性三层工程 →（被 S1b 推翻成本模型，见下）。

### 2026-08-25 S1b：miles 原生 sampling-mask primitive 发现（G-M3 成本坍缩）
做了什么：codex R3 发现 + 本线程源码验证:miles HEAD f2b7c7929（2026-08-24,用户当日刷新 checkout）已合入 `f0499c46e` "[RL] Add sampling-support log-prob primitives (#2200)"。
证据：`miles/utils/sampling_mask.py` RolloutSamplingMask（CSR ids+offsets,即 tape 形状）；`loss_hub/math_utils.py:289,304-316` 融合核前 masked_fill(-inf)；`tests/fast/utils/test_sampling_mask.py`；codex 核实 sglang-miles 已有 output_token_sampling_mask 出站。
结论：G-M3 从"移植 929 行旧 patch+自写训练 softmax"降为"中间接线（请求开关→Sample/codec/merge/DP conversion）+ 校验"。缺口两条：(1) miles 只查支持集非空,无 **target-in-support** 校验（slime 双端 force-keep 的等价物,候选首个上游 patch）；(2) RolloutSamplingMask offsets 要求严格递增（禁零宽 span）vs slime 对观察 token 的零宽 pad——response token 覆盖范围定义需对账。rh2 契约侧对策（codex 纠正我方底稿）：新增严格枚举 mask_kind（如 sampler_support_token_ids）,fail-closed 完整保留,不是放弃。

补充（同日,零宽 span 疑点收口）：miles 消费端 `logit_processors.py:224-229` 强制 `len(sampling_mask) == response_length` 且构造器拒绝空支持集——当前 primitive 假设 response 全部是采样 token（单轮 RL 形状）,与多轮 agentic 轨迹（response 含 loss_mask=0 的观察 token）不兼容。接线层两个候选：(a) 上游 patch 允许非采样位置零宽 span（与 target-in-support 并列为候选上游贡献）;(b) 接线层给观察位置填单例支持集 {该 token 本身}（loss_mask=0 不进 loss,需验证无熵计算副作用）。归 P0-3 定案。

### 2026-08-25 S2：CC harness 接入映射（G-M5）
做了什么：逐模块盘点 rh2 slime adapter 链的职责与耦合等级；查清 CC→模型真实协议链（CC 说 Anthropic Messages,协议转换由 slime AnthropicAdapter 承担,rh2 只在两端加中间件+替换 call_sglang_generate）；映射 miles 对应面（session server 三相流/agentic_tool_call/legacy 兼容层/abort hook）。
关键事实：六个治理件（async_worker/session_capability/quiescence_barrier/baseline_census/patch_exporter/outcome_producer）**零 slime import 可原样保留**；深绑定仅 capture_wire（monkeypatch slime_common）、bringup（借 AnthropicAdapter+ClaudeCodeHarness）、docker_sandbox；`rh2_custom_generate` 旧签名可被 miles `LegacyGenerateFnAdapter` 原封加载；**miles 全栈无 Anthropic Messages 协议面**；miles 侧 404 真实存在（SessionNotFoundError=404,errors.py 已确认）,rh2 的 404→503 中间件必须带过去。
结论：形态甲/乙对照表见会话报告,定选甲（见决策表）。vendor 清单：slime/agent/adapters/{anthropic,common,aiohttp_threaded}、trajectory.py、harness/{common,claude_code}.py、sandbox.py ≈ 1800 行。

### 2026-08-25 S3：sm_120 部署栈侦察（G-M1）
做了什么：查 miles docker 构建链、miles-wheels arch list、Megatron 分支版本、上游 issue、CI 硬件面;对照 P3 绿灯来源。
关键事实：miles 官方支持矩阵+CI 均无任何 Blackwell/sm_120;官方镜像训练侧几乎必挂（FA2/apex/int4_qat wheels arch list 无 12.0 无 PTX）;TE 2.17 核心库含 120;sgl-kernel/flashinfer 基础面覆盖 sm_120;已有 issue #364（RTX PRO 6000 上 update_weights_from_tensor CUDA-IPC 权限坑,--privileged 可绕）;sm_120 上低精度全线不可用只剩 BF16（与 P3 现状一致,非新损失）。
结论：三条部署路径中 (b)"官方镜像+重编 kernel wheel 清单"负担最小,与 P3 绿灯的 slime 镜像做法同构;(a) 直接用官方镜像大概率失败;(c) sglang 降级 v0.5.13 自建负担最大（miles 对 sglang-miles 分支是硬 API 依赖）。

### 2026-08-25 S4：本地可运行原型（G-M7 / L1）
做了什么：scratchpad 建 CPU venv（miles-spike-venv,Python 3.12,torch/ray/httpx/transformers 5.12.1 等）,确认 miles 核心数据模块可 CPU 导入（base_types 因 DataSource→chat_template_utils→sglang 链条不可导,已绕开）;写 `test_miles_spike_shapes.py` 10 个测试打 miles 真函数。
结论：**10/10 通过**。rh2 嵌套 fan-out 形状（branch 共享 rollout_id）原样通过 DefaultDataBuffer put/get、stock dynamic filter（嵌套感知）、staleness 双时点过滤、validate_compact_rollout_ids（断言即 rh2 Branch 语义）;DataBuffer ABC 三方法足以承载 rh2 准入原型（FA-2B 缩减路径可行）。**迁移约束：组内不得混用裸 Sample 与 list[Sample]**（flatten 残留嵌套,测试已固定）。附 codex 提醒：ABC 面足够承载"准入",但 drain receipt/exactly-once finalization 不属于该 ABC,归 P0-2 验证。
另：miles wire codec（SAMPLES_VALUE_SPEC 静态表）只影响形态乙;形态甲 Sample 在进程内,tape 可暂走 metadata,待验证"训练侧 batch 是否透传 metadata"。

### 2026-08-25 codex 复核记录
- R2（架构方案评审,scratchpad/codex_arch_review.md）：提出方案 E（F2-4 前闸门）;修正"官方 30B fully-async 需 16 卡"——miles 有 8 卡 6+2 CI（tests/e2e/megatron/test_qwen3_30B_A3B/test_fully_async.py,H100/MI350,use_r3=False,本线程已源码验证）;指出 F2-4 是新增 slime 耦合最重件。
- R3（spike 中期发现对抗复核,scratchpad/codex_spike_review.md）：发现 S1b;定选形态甲;预判 Conditional Go（与我方一致）;重排剩余本地项;纠正我方两点（mask_kind 枚举不等于放弃 fail-closed;patch dry-run 统计口径不作主证据）。
- R4（本地段收口终审,scratchpad/codex_local_phase_closure.md,2026-08-25）：**裁决 = spike 工作完成,迁移闸门未收口;可进迁移分支与 CI,不可立即进硬件执行**。要点：(1) R3 四前提逐条判定——sampling-mask 纵切因④~⑪未接线判未满足;形态甲"大部分满足但非集成闭环"（缺同一链 Miles→vendor→CC HTTP→stage/commit→drain 的集成测试）;治理"可行性层满足,生产闭环未接";fast-test 有条件接受推迟,**条件 = CI 绑定 pin f2b7c7929 且在首个付费 GPU 作业前变绿**。(2) 抽验修正两处过宽表述（已回写至 P0-2/P0-3 条目）。(3) **新 finding（P1/conditional_future,进硬件前修）**：P0-2 原型经 unused_handler 计数判准入会把 dynamic-filter drop 误记 ADMITTED（miles drop 直接 return 不走回调,fully_async_data_buffer.py:131）——违反"ADMITTED 必在 buffer/reservation"不变量;最小修复 = rh2 custom buffer 外层自调 call_dynamic_filter、关闭 inner filter,verdict 只执行一次可逐 attempt 记账。(4) 两个 T0 候选均 confirmed T0,推荐意见已并入决策包（见下）。(5) 硬件段清单增补七项（形态甲真实全链/故障矩阵/关停 dispose——miles stock FullyAsyncRolloutFn 无 close 面/mask 分布式 parity/双 logprob 对拍/top_k 非绑定证明/spec decode 显式关）。

### 2026-08-25 P0-1：形态甲 vendor 纵切 —— ✅ 通过
做了什么：vendor 闭包清点→机械 vendor（零修补,18 文件字节级等同 pin）→闭包自证→rh2 零改动对接→miles legacy 加载→rh2 现有测试面重定向到 vendor 的强等价验证。未改 rh2/reference 任何文件。
关键事实：
- 闭包 = **18 文件 / 3684 行**（比 S2 估算多 ~1900 行：`__init__.py` re-export 拉入 openai.py+codex.py 464 行、parsing.py、slime.utils 三件 941 行）;重依赖（sglang/ray/e2b/megatron）全部是函数内 import,不进闭包。
- rh2 对接面比预期更窄：generate.py 模块级零 slime import,capture_wire 的 slime import 全在 `install_capture_wire` 函数内;安装后 monkeypatch 与 404→503 注入点验证通过,幂等。
- `load_generate_function("...rh2_custom_generate")` 返回 LegacyGenerateFnAdapter,evaluation 参数被正确识别;vendor slime 与 miles 同进程共存。miles 加载链需 stub sglang 两个符号（protocol.Tool、encoding_dsv4——CPU spike 专用,真实训练环境有真 sglang,判为环境噪音）。
- **强等价**：rh2 `tests/adapters/ + tests/contract_slime_async/` 基线 321 passed;vendor 重定向 314 passed + 6 failed + 1 skipped,7 个差异**全部**是"vendor 有意不含 slime.rollout.*/dp_schedule"（训练批次侧,形态甲下由 miles 件替代,S4 已验）;**零真实不兼容**。真实 AnthropicAdapter drain-before-freeze CPU 测试、test_project_from_slime 均在 vendor 上同绿。模块审计：12 个已加载 slime\* 模块全部来自 vendor,零泄漏。
产物：scratchpad/`vendor_slime/`、`p01_step3/4/5_*.py`、`vendor_redirect_plugin.py`。
遗留待拍板（小 T1）：正式落库时是否砍 openai.py/codex.py（减 464 行维护面,代价是破坏零修补需改两个 `__init__.py`）。
边界：本步证明 import/接线/加载三层连通 + CPU 测试等价;真实 HTTP 往返与 drain exactly-once 归 P0-2/硬件段。

### 2026-08-25 P0-2：治理生命周期故障注入 —— ✅ 通过
做了什么：`test_miles_spike_p02_faults.py` 13/13（三连跑稳定）。架构 = `Rh2AttemptLedger`（receipt 账本,attempt 状态机 DISPATCHED→ADMITTED→HANDED_OFF→FINALIZED + 旁路终态）+ `Rh2GovernedBuffer`（实现 miles DataBuffer ABC,内部包**真** DefaultDataBuffer）。六场景全过：put 前 crash 可区分记账、在飞组可盘点、重复 finalize 幂等留痕、撤销后晚响应两入口拦截、get 后消费方崩溃经 lease 超时回收无双账、背压 cancel 后 Condition 健康。
关键判定：**rh2 治理语义可完全挂在 miles core 之外**。ABC 面够承载 reservation/lease/metrics;不够的三处（put 无准入回执、无 ack 通道、无枚举面）**除 dynamic-filter 逐 attempt receipt 外**原型已验证主要替代（lease 超时/版本前进隐式 ack/显式 finalize、影子清单）。〔R4 修正：原型经 unused_handler 计数判准入会把 dynamic-filter drop 误记 ADMITTED——修复归 C3〕
**两个必须记住的 miles 真实行为**：(1) put 在背压等待中被 cancel → 组无痕消失（不进 buffer 不走 unused_handler）——rh2 put 调用方必须自己在 CancelledError 路径记账/重派（miles 自有 driver 顺序 await 故无碍）;(2) `Sample.reset_for_retry()` 保留 metadata——attempt id 必须在 dispatch 时刻重盖章。
留给 F2-4-on-miles：put 前 crash 记账/cancel 补救/盖章归 rollout function 层;默认显式 finalize,版本前进隐式 ack 只作兜底（多消费者/版本回退下不成立——推断）。真实 drain exactly-once 归硬件段。
产物：scratchpad/test_miles_spike_p02_faults.py。

### 2026-08-25 P0-3：sampling mask 语义 parity —— ✅ 通过（23/23）
做了什么：`test_miles_spike_p03_mask.py` 打 miles+slime 真函数（发现 miles true-on-policy 路径与 slime vocab-parallel 路径都可 CPU 直调,parity 断言打的是真实消费路径）;并产出 SGLang→训练侧 12 层接线缺口表。
关键结论：
- **CSR 同构成立**：slime tape（含多轮 merge 重基）↔ RolloutSamplingMask round-trip 无损;支持集内 logprob 两栈数值一致（atol 1e-5）。
- **target-in-support 缺口机制修正**：不是 NaN——primitive 层 target ∉ 支持集时 logprob 为 -inf 且局部梯度有限但方向错误（masked_fill backward 吞掉 +δ 项,坏行梯度和为 -1）。〔R4 收窄：最终训练路径表现取决于接入的 loss——stock policy loss 会把 ppo_kl ±inf 先转 0,rh2 faithful_dis 会直接拒绝非有限 logprob;不能声称 stock loss 必然收到错向梯度。训练端 fail-closed 校验仍必须（防传输错位/artifact 损坏）,归 C2〕**但 sglang-miles 引擎侧已有出站 force-include**（sampler 把 sampled token 强制并入 mask）——双端不变量缺的只是训练端（slime 双保险 vs miles 单保险）,缺口降级为"数据损坏/错位时的防御深度"。
- **零宽 span 定案证据**：候选 (b)（观察位填单例支持集 {该 token}）是 slime 零宽语义的**精确等价物**（logprob 恰为 0,与 slime force-keep 后全序列 allclose）;**熵两条路径都不受影响**（true-on-policy 显式用未掩蔽 logits;fused 路径 mask 打在私有副本上,源码核实）;引擎 greedy 路径本就出站单例 mask。候选 (a)（上游允许零宽）需动构造器+消费端两闸。两者不互斥：(b) 先走通,(a) 作上游贡献并行提。〔R4 限定："精确等价"限于 logprob/梯度语义/全词表熵三项,TP/CP/VPP 与 BF16 fused kernel 的 bitwise 等价归硬件段对拍〕
- **接线缺口 12 层表**（完整表见会话报告,要点）：引擎侧①②③**全部已有**（请求开关 return_sampling_mask、联合保留集+force-include、meta_info 出站+流式增量账）,但带三条硬约束:**要求有限 top_k（top_p-only 直接 abort）**、不支持 spec decode、disaggregation 需环境变量;miles 侧④⑤⑥⑦⑨⑩⑪缺失（均有 R3 先例可循）;消费端⑫完整。**`rollout_sampling_mask` 在 miles HEAD 零生产调用方——primitive 已合入但未接线**,与"接线即工作量"的成本模型一致。
- **两个否定性发现**：(1) 逐样本 metadata 不在 `_package_shards` 白名单,默认不透传训练侧——"tape 暂走 metadata"路线**不可行**,必须一等字段+白名单;(2) 引擎不改写主 logprob 字段（renormalized 值在独立字段）——`rollout_log_probs` 选源（全词表 vs renormalized）是显式语义选择。
**新增 T0 候选（进决策包,待用户拍板）**：(a) top_k 必须有限——现行采样参数策略要变,触碰训练样本准入判据;(b) rollout_log_probs 选源——直接影响 DIS/TIS ratio 语义。
产物：scratchpad/test_miles_spike_p03_mask.py。

### 2026-08-25 R5-ext：外部 codex 阻塞复核（用户安排,tmp/codex_miles_local_spike_blockers_20260825.md）+ 本线程逐条源码核实
五个阻塞主张**全部核实成立且真实可达**：
- **B1 Sample 类型边界（已复现,最重）**：vendor `TrajectoryManager.to_sample()`（trajectory.py:248）无条件构造 slime Sample;两个 Sample 类不同、Status enum 互不相等（实测 `SS.Status.ABORTED == MS.Status.ABORTED → False`）、slime Sample 缺 `oldest_weight_version`。后果链：ABORTED 漏过 miles buffer 过滤→get_metrics AttributeError→validate_compact_rollout_ids 断言炸→train conversion 缺字段。**P0-1 结论正式修正为"加载面通过,运行纵切未通过"**——等价测试只覆盖 rh2 面向 slime 一侧,未覆盖返回 miles 一侧。修复 = `Rh2MilesGenerateFn` 显式 canonicalize（status 按字符串值映射、保留 miles 输入侧字段、递归 nested、为 mask 字段预留位）。
- **B2 版本前进隐式 ACK 证伪**：train_async.py:79-81 在训练当前批**之前**发起下一轮 generate——get 看到新版本不代表 HANDED_OFF 批已训练。**删除该路径（含 fallback 用法）**,改为训练入口 `after_train_success` 显式回执;崩溃窗口落 `uncertain_trained`（与决策包 v4 at-least-once 语义一致,不新增承诺）。P0-2 条目该推断作废。
- **B3 C1 验收边界扩大**：mask 接线只解决归一化,不自动实现 faithful DIS;C1 必须到"miles custom loss 调用 rh2 faithful DIS"为止,否则硬件段验证的是另一套算法。接受。
- **B4 C4 终点太早**：原终点 drain 之后正好漏掉 B1;扩至 stock FullyAsyncRolloutFn→…→canonicalize→governed buffer→postprocess→reward normalization→train conversion,含真实 SWE task、连续 drain 两批、nested 形状与 GBS 计数断言。接受。
- **B5 关闭面缺失**：rollout_manager.dispose()（:131-140 实测）不关 fully-async worker;CPU 段先定义最小 close/dispose seam（幂等、分类记账、dispose 触发）。
- **B8 闭包漏项**：bringup.py:574 函数内 `from slime.utils.processing_utils import load_tokenizer` 不在 18 文件闭包——C4 必须在"无完整 slime 安装"条件下构造真实 BringupService 防路径掩盖。
- §10 为两个 T0 列的证据缺口清单（top_k 实测分布/安全边界、双 logprob 逐 token ratio 对拍）并入硬件段验收;§12"本轮不要求"清单接受（无 exactly-once、无大抽象层、vendor 不裁剪）。

## 待办

本地 spike P0-1/2/3 的调查与原型目标完成;R5-ext 修正后,**首个付费 GPU 作业前**的 CPU/CI 前置（迁移分支执行,按 R5 §11 最短顺序）：

- [ ] **C0 Sample canonicalization 边界 + C4 扩大**（先做,已复现的直接崩溃,工作面最小）：`Rh2MilesGenerateFn` 递归转换器 + 纵切测试到 train conversion,覆盖 COMPLETED/TRUNCATED/ABORTED/remove_sample 与 nested fan-out;真实 BringupService 构造（无 slime 安装环境,闭包补 processing_utils 或改接自有 tokenizer loader）。
- [ ] **C1 目标 Megatron 路径 sampling-mask 完整 CPU 纵切 + faithful DIS custom loss**（接线缺口 ④⑤⑥⑦⑨⑩⑪ + rh2 faithful DIS 成为 miles --custom-loss-function-path 真实 loss;验收含 mask 对齐/target fail-closed/provenance/detach/拒绝 token 零梯度/branch 不进分母/execution 归约对拍/全零 step;修改范围= miles 数据 plumbing 可审计 integration patch,**触碰 worker/scheduler/staleness/权重更新语义即停并重评**;只覆盖 Megatron/30B 路径,不为 FSDP/VPP/CP 扩门）。
- [ ] **C2 target-in-support 训练端 fail-closed**（并入 C1）。
- [ ] **C3 dynamic-filter 逐 attempt 记账**（rh2 custom buffer 外层唯一 verdict,关 inner filter;验收探针=拒绝终态+不在 inventory+守恒）。
- [ ] **C7 trainer-success 回执 + close/dispose seam**（B2/B5 修复;连续 drain 两批的 CPU 调度测试固定预取真顺序;HANDED_OFF 重启/恢复探针;seam 幂等两次调用）。
- [ ] **C5 miles fast-test 子集 CI**,绑定 pin f2b7c7929,GPU 作业前变绿（不要求全量 suite）。
- [x] C6 两个 T0 已拍板（见决策表;top_k 正式配置留待硬件实测后定）。
- [ ] P1 vendor 闭包/许可证清点;LegacyGenerateFnAdapter 移除风险哨兵。

## 硬件段清单（并入下次合并短租）

原五项：sm_120 镜像 bringup（路径 b）→ 复现 6+2 → 目标 4+4 → 权重更新语义（retract/in_place+增量 R3）→ 逐 token logprob/tape parity。
R4 增补：形态甲真实全链（CC 多轮 HTTP/capture/drain/receipt/buffer admission）;生命周期故障矩阵（满 buffer cancel、graceful shutdown、Ray actor kill、put 各时点、get 后 finalize 前）;关停与 dispose 验证（miles stock FullyAsyncRolloutFn 无显式 close 面,须证退出无孤儿 worker 无账外组）;mask 分布式 parity（TP/CP/VPP、BF16、观察位单例、target 损坏注入）;双 logprob 对拍（同权重下 support-current/behavior-support ratio≈1）;top_k 非绑定证明（有效 vocab 边界、mask 体积、吞吐显存）;spec decode 显式关闭（引擎硬约束）。
