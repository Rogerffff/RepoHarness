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
| 2026-08-25 | **T0-C1 承载形态调整为 A′**（用户指示"核实成立即调整",已核实成立）：C1 不再自建 plumbing——上游 stacked PR #2595（transport,已获 code-owner approval）/#2596（bounded top-p capture+actor replay,待评审+E2E CI）已覆盖接线表 ④→⑪ 全部。integration base = pin f2b7c7929 + cherry-pick 两 PR commit + rh2 最小 downstream delta（faithful DIS custom loss/双 logprob provenance/Eligibility/ledger/CC capture/治理语义）。**不提交竞争 PR** | 用户指示 + tmp/miles迁移spike.md + 本线程核实 |

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

### 2026-08-26 R6-ext：C1 完整审查（spike-first 收敛版,tmp/codex_miles_c1_review_spike_first_20260826.md）+ 本线程核实
用户简化原则生效：优先接通链路与首训进度,防治理过度设计。六条 finding 全部核实成立：
- **B1**（bootstrap 缺失,细化:bringup ensure_fa_started 存在但 miles 路径无人调用）→ 修复=Rh2MilesGenerateFn 惰性复用现有 bringup,不建新抽象。
- **B2**（mask 未跨 capture→leaf→projection,装配件零生产调用,grep 实证）→ 修复=orchestrator 按引擎选新旧约定、commit 后保留逐轮 support、装配结果同写 Sample 与投影;验收=禁手工 attach 的组合链测试（两轮+观察位单例+掉落轮,不扩环境）。
- **B3**（model.py mask 字段条件 `loss_type=="policy_loss"` 排除 custom_loss,源码实证）→ 修复=integration 分支最小 miles commit。**规则修订（T1）**：rh2-integration 分支从"只承载上游原样 commit"改为"允许最小可审计 rh2 commit,逐个登记 SHA"。
- **B4（真算法 bug,本线程裁决 codex 正确）**：C1′-b 把"D 成员语义（provenance_tokens v1）"与"归约层次"混为一谈——标量权威 `faithful_dis_loss_by_execution`（faithful_dis.py:198-229,branch 分子→execution 级 provenance 分母→batch execution 等权,对接 FA-3 rollout_loss_denominator）才是正式层次;miles `rollout_mask_sums+sum_of_sample_mean` 即其现成实现。修复=逐 token 分子交 miles reducer,不自建 DP/CP 归约;验收=三组 metamorphic（branch split/sibling 跨 microbatch/DP partition 不变）对拍 by_execution。
- **B5**（CSR 钉 CPU vs CUDA target 跨设备比较,MPS 复现）→ CPU 侧完成检查或最小张量同设备。
- **B6**（全零有效 token 仍走 optimizer,AdamW weight decay 改参）→ spike 级 fail-stop（optimizer 前显式终止,权重/optimizer/scheduler/weight version 全不前进）;正式首训前收敛为 FA-4 §4 的 skip+计数+熔断。
**§2 范围收缩接受（推翻 R4/R5 部分排序,记录在案）**：C3/C7 ledger/governed buffer 保留为未接线原型,其内部 finding（_recycle_watch/reap_expired/seal_batch/无持久化）不修;首轮 GPU 用 stock DefaultDataBuffer + run-fatal;后续无明确收益可删。C5 定形=双 lane（pin 兼容 63+95skip / integration 资格 158 零 skip）+ 可复跑 manifest（base SHA+两 PR SHA+tree digest）。§5 递延清单接受（含 vendor LICENSE 整理推迟到公开 push 前）。

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

- [x] **C0 Sample canonicalization 边界 + C4 扩大** ✅ 2026-08-25（miles-migration 分支）：vendor 落库 `rh2/src/slime/`（19 文件 3816 行,取 pin blob 字节级零修补——注意 reference/slime 工作树 common.py 有 30 行本地注释标注,vendor 不携带;sha256 表在 VENDOR_README.md）;`adapters/miles/canonicalize.py`（30 字段全覆盖映射表,PENDING 拒绝、`COMPLETED+metadata["truncated"]` 显式升级 TRUNCATED、中止语义优先、未知字段 fail-closed、模块加载时两侧 dataclass 字段集核对——任一侧加字段当场炸;双形态输入:slime 转换/miles 直通）+ `generate_fn.py`（Rh2MilesGenerateFn 新签名类）;测试 39 个全绿:B1 三症状按文档化断言复现且 canonicalize 后全消、纵切**实际到达 convert_samples_to_train_data**（sglang 只卡 base_types 链;真实缺口是 ray,conftest 用 4 符号最小 stub）、真实 BringupService 在无 reference/slime path 条件下构造成功（B8 闭包补齐验证）。全仓 1133 passed,既有 321 逐数不变。agent 的 8 条 T1 决策记录在会话报告（要点:vendor 取 blob 非工作树、pillow 进 dev 组、remove_sample 纳入复制面、rollout_routed_experts 非 None 拒绝留 C1 显式接、测试 module 级装卸 vendor 世界防混跑遮蔽）。
### 2026-08-25 S5：上游 stacked PR 发现与 integration base 构建（T0-C1 调整依据）
外部调查（tmp/miles迁移spike.md）发现并经本线程逐项核实：radixark/miles 存在 stacked PR 系列 #2200（已合并,在 pin 内）→ #2595"Represent and transport rollout sampling support"（12 文件 +295/-15,1 APPROVED）→ #2596"Enable bounded top-p sampling-support replay"（38 文件 +1217/-60,待评审,E2E 已在 2×H200 验证但 miles CI 未跑）。文件清单核实覆盖接线表 ④→⑪ 全部（含 session v2、FSDP/Megatron 双 actor、E2E 测试）。
**语义对齐核实（PR 描述逐条 vs 我方已定结论）**：有限 top_k 作 hard support bound = T0-A 选项 1;SGLang 返回 support-normalized rollout logprob、actor 同支持集归一化 = T0-B 正式分母;**强制工具/环境 token 用单例支持集 = 我方零宽 span 候选 (b)（上游独立同选）**;不可忠实 replay 请求直接拒绝（unbounded top-p/温度不匹配/support 不完整）= fail-closed;熵/reference/teacher 路径不动 = P0-3 parity 结论;致谢 slime #2102（两栈收敛上游明文确认）。
**integration base 已建**：`reference/miles-rh2-integration`（radixark/miles 全新 clone,与只读 pin 区分）分支 `rh2-integration-v2` = pin f2b7c7929 + cherry-pick 9b6579a12(#2595)+ee648b17d(#2596),**零冲突**（本地 SHA f8fafa571/8378acad5,30 文件 +950/-73）。⚠️ 构造注意：PR 栈基于 f0499c46e（pin 的祖先）,直接用 PR head 会丢 pin 内两个 sampling-mask 存储重构 commit——必须 cherry-pick 构造。风险登记：#2596 无 approval,评审可能改动;对策 = 锁 SHA,上游合并后 rebase 重对齐（我方 CPU 测试面作漂移探测器）。上游 fast 测试在 CPU venv 需扩 sglang stub（>4 符号,超 spike 两符号面）,归 C1′ 验证。

- [x] **C1′-a 上游 base 验证 + gap 分析** ✅ 2026-08-25：63 测试 schema 信号如设计触发（唯一新字段 rollout_sampling_mask,探针确认后 63/63 绿——上游未改变 buffer/postprocess/conversion/治理行为）;p03 parity 23/23 双 base 零漂移;上游 focused fast 测试 266 passed 0 真失败（sglang stub 扩到 12 项,记录在 stub 文件;E2E 归硬件段——上游 2×H200 配置 top_p=0.8+top_k=32）。gap 结论：(a) target-in-support 上游有**三层 rollout 侧**校验（请求 should_return_sampling_mask 严校验/解析层逐 token sampled∈support/装配层缺 mask 即 ValueError）,loss 层无——C2 收窄为 faithful_dis 内一行断言;(b) 上游 Sample 单列 logprob=support-normalized（=T0-B 正式分母）,全词表诊断列经 rh2 raw_response 捕获零上游改动留存;(c) 单例支持集上游已实现（append_forced_sampling_tokens/merge_sampling_masks/concatenate 可复刻对照）;(d) top-k 校验**无上界**,vocab-size K 实测可过,T0-A 兼容;replay 开关=top_p<1.0 严格（边界事实登记）;(e) rh2 capture 路径 delta 六项清单+投影新枚举 sampler_support_token_ids 设计（offsets dtype 按上游 wire 是 int64）已出。conftest 增 RH2_MILES_PATH 切换;无新 T0。
- [x] **C1′-b rh2 downstream delta 实现** ✅ 2026-08-26（两个执行线程接力：前线程留半成品,本线程审计补完+写 loss+测试）：delta 六项全落地——① `sampling_mask_assembly.py`（请求前置校验/响应解析 sampled∈support/跨轮装配:观察位单例+offsets 重基,复用 `_mask1_runs/_match_turns_to_runs` 同一锚定实现防两套账）;② capture_wire 冻结面例外改动（+55:旗标顶层化+前置校验 fail-closed 不发 HTTP+响应解析+TurnRecord logprob 列切换 support-normalized+capture_params 补记 top_k;审计后补 `configured_top_k` 上界核对=上游 request<=configured 同款,请求 body 不得静默放大硬上界）;③ `faithful_dis_loss.py`（miles LossFunction 签名,--custom-loss-function-path 可加载;**denominator 预注册 = provenance_tokens,与标量权威 DENOMINATOR_SEMANTICS_V1 同源 import 非复制**;f(r) 整体 detach 区间外梯度精确为零;C2 gather 前 target∈support 断言;current=miles masked 路径 support-renorm,behavior=rollout_log_probs support-normalized;sum_of_sample_mean 有意不用——per-sample-mean 口径≠预注册全局 token 分母;CP>1 fail-closed 归硬件段）;④ canonicalize 扩表（双 base 允许集分流 MILES_HAS_SAMPLING_MASK_FIELD,rollout_top_p<1 无 mask 拒绝,附加属性→RolloutSamplingMask ids int32/offsets int64）;⑤ SamplingMaskRef 新枚举 sampler_support_token_ids（top_k 必填/kept>=response 无零宽下界/旧三态不得携带 top_k）+ LogprobProvenance.normalization 三态 + `projection_ext.py`（ids int32/offsets **int64** wire 打包,支持集宽度<=top_k 上界闸）;⑥ conftest base 探测（types.py 静态文本探测 rollout_sampling_mask,pin base 新测试自动 skip）。测试 95 新增（a 捕获 wire 真函数+fake 引擎/b 装配/c canonicalize/d loss 对拍:标量参考逐位梯度链式展开一致+区间外精确零+单例支持集梯度恰零的正确性固定/e 契约+投影）:integration base 158 全绿,默认 pin 63+95 skip,321 逐数不变,全仓 1157+95 skip（integration 全仓 1252）,ruff 过。审计发现：前线程半成品语义全部成立,仅 3 处补强（projection_ext 空 mask max() 崩溃前置拦截、top_k 上界核对、contracts 导出 RolloutLogprobNormalization）。红线核对：faithful_dis.py/tests/training 零改动,两 reference checkout 干净,未 commit。**完成即停,待外部 codex 审查。**
- [x] **R6-ext B3+B4+B5+B6 修复** ✅ 2026-08-26（本线程;B1/B2 由并行线程负责）：
  **B3**=integration 分支最小 miles commit **`f6aab6542`**（`rh2-integration-v2`,+4/-1,仅 `megatron_utils/model.py`：train 路径 mask key 传输从 `loss_type=="policy_loss" and replay` 放宽为 replay-only;forward_only 路径本就调用方参数驱动不动;按修订登记规则记 SHA）。
  **B4**=`faithful_dis_loss.py` 归约重写：删除 microbatch 扁平 `provenance.sum()` 分母,逐 token 分子交 miles `sum_of_sample_mean`（`rollout_mask_sums` per-execution 分母;dispatcher `num_rollouts` 缩放完成 execution 等权）——已核实该链恰为标量权威 `faithful_dis_loss_by_execution` 三层归约（execution=rollout,sibling 共享整 rollout 分母跨 microbatch 重构 loss_e）;新增 fail-closed：`rollout_mask_sums` 缺失/矛盾/零 provenance、`calculate_per_token_loss`（reducer 退化为 token 扁平和=B4 原 bug 口径）。
  **B5**=target∈support 检查整体落 CPU（CSR 构造器钉 CPU,response tokens `.to("cpu")` 小整型搬运;比把 CSR 搬 GPU 便宜）;加速器测试：单元级 CPU/MPS 双设备 + 全 loss MPS 布局（列在设备上/CSR 在 CPU,合法通过、损坏 target 抛结构化 `target_not_in_support`,本机 MPS 实跑）。
  **B6**=spike fail-stop：accepted=0 抛 `FaithfulDisZeroAcceptedStop`（reducer 前;传播链 losses.py→loss.py→fbf→train_one_step→train→actor.py 全程无 try/except,源码核实,optimizer.step 不可达）;CPU 探针验证参数/AdamW state/scheduler/weight-version 代理全不前进。**已知偏差（有意）**：触发粒度=microbatch,"部分 microbatch 全拒但全局非零"也会停（不建跨 microbatch 协议,宁可误停;专项测试固定,正式首训前按 FA-4 §4 收敛为 skip+熔断——彼时该测试预期翻转）。
  **B3/B4 验收 seam**：新 `test_train_seam_metamorphic.py`——真实 `train_one_step→get_batch→loss_function` 纵链（megatron auto-stub+单进程 gloo+`Tensor.cuda` 钳制,batch 不手工构造）;三组 metamorphic（branch split/sibling 跨 microbatch/DP partition 求和重构）loss+参数梯度全部逐位对拍 `faithful_dis_loss_by_execution`（atol 1e-12,double）。metric 更名 `dis_denominator`→`dis_microbatch_provenance_tokens`、`dis_zero_grad_step` 删除（被 fail-stop 取代）——测试 oracle 改动,T1。
  回归：integration base 全仓 1269 passed（含并行线程 B1/B2 新测试）,默认 pin 1159+110 skip,321 逐数不变,ruff 过;标量权威/`tests/training`/pin checkout 零改动,rh2 侧未 commit。发现即停项：sibling metamorphic 首版分组把"仅剩一个被信任区间拒绝的 provenance 位"的 sibling 单独成 microbatch,先触发 B6 fail-stop——正是 B6 已知偏差的真实体现,已在测试注释中互相引用。
- [x] **R6-ext B1+B2 修复** ✅ 2026-08-26（并行线程,主线程回写）：
  **B1**=`Rh2MilesGenerateFn.__call__` 缺 orchestrator 时惰性 `await ensure_fa_started(args)`（复用 BringupService 单例,幂等+sticky FAILED 原样,零新抽象;关闭 hook 留进程退出,注释指向 R5 B5 硬件段）。验收测试 `test_b1_real_bootstrap.py`：miles load_generate_function 起步、真实 BringupService（真 tokenizer/adapter 线程/探针打 fake 引擎）、无手工 fake orchestrator,附"必须复用 ensure_fa_started"源码哨兵。
  **B2**=真实纵链接通：args 显式开关 `rh2_engine_sampling_mask`（缺省 False=旧 slime 链逐字不变）——True 时请求走新 `return_sampling_mask` 且旧 tape 约定关闭;`_turn_support` 经 PendingTurn 随 commit 落 TurnTape.sampling_supports（wire 传已解析对象/直调路径同一 parse 函数重建,一份实现）;step5 用与 top-p 回填**同一份** `_mask1_runs/_match_turns_to_runs` 锚定调装配（掉落轮跳过/观察位单例/回链轮缺 tape 抛 `sampling_mask_tape_missing_in_assembly` 收口 abort）;投影经 `project_group_with_sampler_support` 借道冻结面校验后逐分支替换为 `sampler_support_token_ids`+`behavior_support_normalized`（冻结面 projection.py 零改动）;startup 探针 mask 分支断言（U-H 同款）。**隐藏缺口修复**：mask 链 abort/eval 占位不再写 slime 零宽 tape 字段（miles Sample 无此字段,canonicalize 必炸）。验收测试 `test_b2_mask_chain.py`：单条组合链零手工 attach 零 `_pop_staged`,两轮+工具位单例+掉落轮,打到 convert_samples_to_train_data 断言 int32/int64 逐值。测试 oracle 改动升 T1：`test_generate_fn.py` orchestrator-missing 用例改为 bootstrap 语义(fail-closed 性质保留)。
  **联合抽验（主线程,两批汇合后）**：integration base adapters_miles **175 passed**;默认 pin **65+321=386 passed + 110 skipped**;ruff 全过;miles 侧唯一 commit `f6aab6542` 在位;projection.py/faithful_dis.py 冻结面零 diff。协作提示留档：并行期间一线程做过 `git stash push/pop`（确认干净弹回）,后续并行批避免 stash 类操作。
- [ ] ~~**C1 目标 Megatron 路径 sampling-mask 完整 CPU 纵切 + faithful DIS custom loss**~~（由 C1′ 取代,自建 plumbing 部分作废）（接线缺口 ④⑤⑥⑦⑨⑩⑪ + rh2 faithful DIS 成为 miles --custom-loss-function-path 真实 loss;验收含 mask 对齐/target fail-closed/provenance/detach/拒绝 token 零梯度/branch 不进分母/execution 归约对拍/全零 step;修改范围= miles 数据 plumbing 可审计 integration patch,**触碰 worker/scheduler/staleness/权重更新语义即停并重评**;只覆盖 Megatron/30B 路径,不为 FSDP/VPP/CP 扩门）。
- [x] C2 ✅（并入 C1′-b:faithful_dis_loss gather 前断言 + B5 设备修正）。
- [x] **C3 dynamic-filter 逐 attempt 记账** ✅ 2026-08-25：`governed_buffer.py`（260 行,实现 DataBuffer ABC 内包真 DefaultDataBuffer）——filter verdict 治理层单点执行（自调 miles 官方 call_dynamic_filter,inner filter 置空+装配自检防双跑）,REJECTED_FILTERED 终态,验收探针全过（不在 inventory/inner 空/守恒/reason metrics）。注入模式=`args.rh2_governance`（miles buffer 构造签名固定,沿 rh2_orchestrator 先例）。挡板提示：构造时只读自检 miles 私有属性 `_inner._dynamic_filter`（语义漂移哨兵,升 pin 若重构测试当场红）。
- [x] **C7 trainer-success 回执 + close/dispose seam** ✅ 2026-08-25：`attempt_ledger.py`（394 行,零 miles import）状态机 9 态——**隐式版本 ACK 全删**（含 hasattr 回归绊线）,FINALIZED 唯一入口 = seal_batch + after_train_success 显式回执;UNCERTAIN_TRAINED 承接回执窗口崩溃（at-least-once,迟到回执只留痕不翻终态）;presence 不变量账本内部强制（bind_buffer 前置核对+release 统一清账+全量对账兜底）;put 背压 cancel 记账下沉治理层。`lifecycle.py`（131 行）shutdown = 停新 submission→cancel await 在飞→三类扫账（DISPATCHED→CRASHED_BEFORE_PUT/ADMITTED→RETIRED/HANDED_OFF→UNCERTAIN_TRAINED）→close hooks→幂等。反测试固定 R5 §4.1 场景（HANDED_OFF@v5 在 get(v6) 后仍非 FINALIZED）+ train_async 预取真顺序源码断言 + 连续两批 drain 调度测试。测试 63（39+24）全绿,全仓 1157,既有 321 逐数不变。
- [x] **C5 双 lane 验证** ✅ 2026-08-26（R6 定形替代原 fast-test CI 表述）：`rh2/scripts/miles_integration_lanes.sh`——前置 integration base 树哈希校验（manifest=miles_spike/integration_base_manifest.json,含 rebuild 步骤+rh2 patch 存档 patches/0001;树 9d7617bf）;lane A pin 兼容（无失败+skip 全为 integration_base 豁免,-m 反选证明）;lane B integration 资格（无失败+**零 skip**——C1 测试真实执行,绿色才有效力）。实跑通过:A=65+110skip,B=175。
- [x] C6 两个 T0 已拍板（见决策表;top_k 正式配置留待硬件实测后定）。
- [ ] P1 vendor 闭包/许可证清点;LegacyGenerateFnAdapter 移除风险哨兵。

## 硬件段清单（并入下次合并短租）

原五项：sm_120 镜像 bringup（路径 b）→ 复现 6+2 → 目标 4+4 → 权重更新语义（retract/in_place+增量 R3）→ 逐 token logprob/tape parity。
R4 增补：形态甲真实全链（CC 多轮 HTTP/capture/drain/receipt/buffer admission）;生命周期故障矩阵（满 buffer cancel、graceful shutdown、Ray actor kill、put 各时点、get 后 finalize 前）;关停与 dispose 验证（miles stock FullyAsyncRolloutFn 无显式 close 面,须证退出无孤儿 worker 无账外组）;mask 分布式 parity（TP/CP/VPP、BF16、观察位单例、target 损坏注入）;双 logprob 对拍（同权重下 support-current/behavior-support ratio≈1）;top_k 非绑定证明（有效 vocab 边界、mask 体积、吞吐显存）;spec decode 显式关闭（引擎硬约束）。
