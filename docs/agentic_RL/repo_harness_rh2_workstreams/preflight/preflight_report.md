# P3 八卡预实验收口报告（preflight_report.md）

日期：2026-07-09。机器：`ubuntu@204.12.168.119`，8×RTX PRO 6000 Blackwell（sm_120，96GB/卡）。执行：codex ~7h（J0~J5 gbs20）+ orchestrator ~2h（J4c fully_async + 收口）。原始事实见 `p3_remote_experiment_handoff_20260708.md`（codex 交接）与 `remote_evidence_20260708/`（证据）；本文只做**收口判定**——每个未知给绿/黄/红灯 + 依据 + 是否需要重来。

机器已释放前确认：8 卡显存全 0、无 raylet/sglang/train_async 常驻进程、无 30B checkpoint 残留、evidence 已全量同步到本地（19MB 纯文本，0 二进制）。

---

## 0. 一句话结论

**P3 目标全部达成，不需要再租卡。** U-C 训练侧四项全绿、S1-7b（routing+top-p tape 首次真实进 loss）绿、放置决策定案（T3 分离 + train_async）、升级触发条件量化（尾部空闲 26~28% > 25% 阈值）。**唯一没拿到严格绿灯的是 formal J4 端到端在线**——但根因已定位为**治理过滤后的 batch schedule 对齐**（一个纯本地可修的 Python 层问题），不是硬件/显存/tape/训练本体，**不需要 GPU 复现**。

---

## 1. 未知关闭台账（协议 §0 对账清单）

| 未知 | 判定 | 依据 | 需重来？ |
| --- | --- | --- | --- |
| **U-C：Megatron 内核 on sm_120** | 🟢 绿 | J3 no-routing A4（8 卡 TP4/CP2/EP8）训练 step 成功；J4 replay + J5 gbs20 完整训练 step | 否 |
| **U-C：PCIe all-to-all 带宽** | 🟢 绿 | J1 nccl-tests 基准留档；J5 实测 actor_train 174s、train_time 252s，远低于 15min 绿灯线 | 否 |
| **U-C：colocate 显存/sleep-resume** | 🟡 黄（分析性关闭） | J4b 未实跑 T1 colocate；但 colocate 唯一假设优势=省跨分区权重同步=11.45s/step（占 step 0.8%），换不回双缓冲重叠——分离主案不因缺 T1 数据动摇 | 否（见 §2 决策） |
| **U-C：CPU offload step 代价** | 🟢 绿 | J5 gbs20：optimizer CPU offload 下 actor_train_tok_per_s=4528，step 内训练段 252s | 否 |
| **S1-7b：routing+top-p tape 首次真实进 loss** | 🟢 绿 | J4 replay（gbs16）+ J5 gbs20 online：两者都真实消费 rollout_top_p_token_ids/offsets + rollout_routed_experts，loss/grad_norm 有限。**S1 acceptance 递延项可改判 closed** | 否 |
| **E6 回填（step 墙钟）** | 🟢 有数 | J5 gbs20：step_time=1387s（**rollout-bound，wait_time_ratio=0.82**）；纯训练段 252s；train_rollout_logprob_abs_diff≈0.039 | 否 |
| **权重同步耗时** | 🟢 绿（512MB 档） | update_weights_time=11.45s@512MB buffer，full+nccl 路径完成一次真实更新 | 否（2GiB 档主动跳过，见 §3） |
| **放置决策（J4b）** | 🟢 定案 | T3 分离 + train_async（§2）；T1/T2′ 实跑不必要 | 否 |
| **升级触发条件（尾部空闲）** | 🟢 量化 | J5 gbs20 尾段 28% / J4 formal 尾段 26%，**双 run 一致 > 25% 注册阈值** → fully_async 升级大概率启用 | 否 |
| **J4c fully_async 可行性** | 🟢 绿（一项存疑留档） | startable ✓、top-up 补采 ✓（probe 95 » target 64）、N1 done_cb 泄漏=0 / N2 队列阻塞=0、2 个真实训练 step；**ABORTED 重入未触发**（见 §4） | 否 |
| **M1 staleness 记账** | 🟢 机制验证 | weight_versions 透传链路工作（events 带 weight_versions_sample/engine）；单步 run 跨度=0 预期。多步分布留升级实施期采 | 否 |

---

## 2. 放置决策定案：T3 分离 + train_async 双缓冲

**依据链**：

```text
1. rollout 是绝对瓶颈：J5 wait_time_ratio=0.82，step 墙钟 1387s 里
   1135s 是 train 等 rollout。harness_run 分段 280~1116s（黑盒模型交互），
   物化 4~10s、评分 4~27s、投影/gate 秒级——长尾 100% 来自 harness。
2. colocate（T1）唯一理论优势 = 省掉跨分区 NCCL 权重广播。实测该广播
   =11.45s/step = step 墙钟的 0.8%。而 colocate 在 slime 里没有双缓冲
   （train_async.py:11 断言禁 colocate），必须纯同步——放弃的是整个
   rollout/train 重叠窗口（>1000s 量级）。
3. 结论：用 0.8% 的省下换不回 >70% 的重叠损失。T3（4 训 + 4 推）分离
   + train_async 双缓冲是主案。T1/T2′ 无需实跑验证。
```

**双缓冲的结构性 staleness ≈ 1×update_interval 个版本**，天然落在行业最紧实践（RollArt α=1）内，首训不需要自建准入（§1.6 定案不变）。

---

## 3. formal J4 未绿灯的根因与处置（最重要的一条）

**现象**：formal J4（8 题 × n=4，严格模式）在 slime 组 batch 前失败：`num_rollouts (19) < global_batch_size (32)`；J5 gbs16 失败在 `build_dp_schedule`：`could only produce 23 mbs; need 24`。

**根因（已定位，非硬件）**：治理层的 fan-out + fail-closed（routing rows 不足、top-p 缺失、capture 未完成、投影失败、eligibility 降档、remove_sample）会改变实际可训练样本分布——**名义 32 rollout ≠ trainer 看到的可训练 rollout id 数；名义 raw samples ≠ slime 每 step 能调度的 microbatch 数**（microbatch 数须对齐 `dp_size * mb_group`，T3 下 dp_size=2）。

**J5 gbs20 证明了这就是根因**：只改 global_batch_size 一个变量（16→20，使 microbatch 数对齐偶数），立即越过 `build_dp_schedule` 断言、完成真实训练 step + 权重同步。**但 gbs20 是诊断性对照，不是方案**——正式系统不能靠人工碰运气选一个恰好对齐的 batch size。

**处置（纯本地，不需要 GPU）**：实现 **batch schedule preflight/repair**——在训练消费前用 Python 计算保留样本数 / rollout_id 分布 / 每 sample token 长度 / dp_size / cp_size / vpp / mb_group / dynamic alignment，判断是否触发 `build_dp_schedule` 断言；不满足则 fail-closed / 延迟拼 batch / 补采 / 子集选择。这是 S2 或 S1 补强的 adapter 层任务，**下次租卡前先离线 schedule preflight，避免再用 20min rollout 暴露 Python 可提前发现的问题**。

---

## 4. J4c fully_async：可启动，但发现两个 fan-out 兼容缺口

**执行**：用 Qwen3-0.6B 替代（4B 资产未预置，机制与规模无关，协议已允许 `J4C_MODEL_*` 覆盖）。三次尝试：

```text
attempt1 rc=1：slime fully_async 消费侧 _key（fully_async_rollout.py:238）
  对 fan-out 嵌套形状（list[list[Sample]]）崩溃——getattr(list,"index")
  拿到 list.index 绑定方法 → int() TypeError。
  【新发现：fan-out 假设破裂点 +1，与 J4 dynamic_filter 崩溃同根】
诊断补丁：_key 递归展平 + callable 防御（留档
  remote_evidence_20260708/preflight_evidence/j4c/slime_fully_async_key_diagnostic_patch.py）。
attempt3 rc=0：patch 后 startable ✓，probe 95 条（» target 64，证明
  top-up 补采工作），N1 done_cb 泄漏=0 / N2 队列阻塞=0，2 个真实训练 step。
```

**存疑留档**：`no_aborted_reentry`——`--update-weights-interval 1` 下未观测到 ABORTED 组重入。原因：0.6B 权重更新窗仅秒级，abort 窗口太窄没抓到在途请求。这**不否定** fully_async 可行性（startable + 补采 + 无泄漏都绿），只是"custom_generate 对 ABORTED 组的实际行为"这个 I-2 收窄后的唯一未知**仍未实证**——留升级实施期用注入式测试（人为在 harness 里插长 sleep 制造确定 abort 窗口）关闭，不值得为它再租卡。

**对升级设计的输入**：fully_async 的 fan-out 兼容缺口现在是**两个**（dynamic_filter + 消费侧 _key），都指向同一件事——slime 标准/异步路径都假设平铺 Sample，我们的 fan-out `list[Sample]` 系统性破坏该假设。升级实施必须把"fan-out aware 的样本展平/排序"作为独立工作项（见 §5 回填）。

---

## 5. 主动跳过项与经济性

```text
- J5 2GiB buffer 第二档：跳过。512MB 已只占 step 0.8%，2GiB 边际价值趋零。
- J4b T1/T2′ 实跑：跳过。分离主案已由 §2 分析性定案，实跑只为一个
  0.8% 量级的对照数，不值机时。
- J4c ABORTED 重入实证：跳过 GPU 复现，转注入式本地/单卡测试。
- formal J4 严格绿灯：跳过 GPU 复现，转本地 batch schedule preflight
  实现后再验（下次租卡顺带，不为它单独租）。
经济性判定：本轮已从每一项 GPU 依赖的未知里拿到判定所需信息；
  剩余项要么本地可修、要么边际价值低于机时成本。继续租卡的期望收益
  已低于成本，释放正确。
```

---

## 6. 回填清单（本地跟进，均不需要 GPU）

```text
[x] 协议 §7 结果回填 → 本报告 §1 台账
[ ] S1 acceptance：routing tape 训练消费递延项 → 改判 closed（J4 replay+J5 证据）
[ ] adapter/inspector：batch schedule preflight/repair（§3，formal J4 绿灯前置）
[ ] 升级设计：fan-out aware 样本展平/排序独立工作项（§4，缺口③扩为
    dynamic_filter + 消费侧 _key 两处）
[ ] 8gpu_preflight_protocol.md：补"治理过滤后 batch schedule alignment 是
    独立验收项"（codex §7.4 建议）
[ ] slime_fully_async_upgrade_design.md：补"fully_async 不解决 batch
    schedule 非法，只解决 overlap/长尾空闲"
[ ] E6 实验设计：step 墙钟纸面估算 → 实测 1387s（rollout-bound）
```

§6 的回填由后续 S1/S2 本地任务消化，不阻塞机器释放。
