# S1 执行计划补充建议汇总

本文整合了两个复核线程对 `03-s1-execution-plan.md` 的建议。目标是给 S1 执行 agent 使用：在不改变 S1 总方向的前提下，补齐容易导致阶段语义误读、训练数据污染、审计事实丢失、评分信号不可信的关键条款。

总体结论：S1 可以开始推进，尤其 S1-0 作为硬阻塞可以先跑；但在进入 S1-1 之后，建议把下列条款补进执行计划、验收报告或 evidence 产物中。

---

## 一、执行前必须补进计划的建议

### A1. S1-7a 的训练 step 必须定义为调试训练传输，不是正式在线强化学习

必要性：必须补。

当前计划一方面写“合格样本进一个真实训练 step”，另一方面又写 S1 阶段最高只发 `offline_or_sft_candidate`。这两句话如果不解释清楚，会破坏 fail-closed 资格门的可信度。

建议补充：

```text
S1-7a 的 training step 是 debug training transport step，
只用于验证 custom_generate -> projection -> gate -> slime trainer 的数据传输链路。
它不表示 online_rl_candidate 已开放，也不表示 rh2_formal_training_allowed=true。
```

同时，因为 S1 的 8 道 smoke 题来自 SWE-bench Verified 仓库，S1-7a 如果真的执行了 optimizer step，必须加“checkpoint 即弃”硬条款：

```text
1. S1-7a 产生的 checkpoint 用后即弃。
2. 该 checkpoint 不得作为任何后续训练、评测、warm-start、debug baseline 的初始权重。
3. `s1_acceptance_summary.json` 必须记录该声明。
4. `rh2_formal_training_allowed` 仍保持 false。
```

原因：Verified 已经被实验设计降为外部参考面，如果 S1-7a 的 checkpoint 被后续复用，会污染项目自己的评测叙事。

### A2. S1-7a 必须真实验证 top-p tape 消费，并处理 n=2 与动态采样的冲突

必要性：必须补。

S1-7a 使用 Qwen3-4B dense 验证数据链路是合理的，但 dense 只是不需要 routing tape，不代表不需要 top-p tape。只要训练配置使用 `top_p=0.95`，S1-7a 就应该在真实 slime 循环里验证 top-p tape 的生产、投影和消费。

建议补充：

```text
1. S1-7a 使用 S1-0 验证通过的 slime patch 镜像。
2. S1-7a 明确使用 top_p=0.95。
3. S1-7a 必须检查 top_p_token_ids / top_p_token_offsets 在真实循环中存在且对齐。
4. dense 模型无 routing tape 时，projection 必须显式标注 routing_not_applicable_dense_model，不能静默成功。
```

同时，当前计划写 `n=2`，而实验设计 E2 已经把动态采样升级为首训默认开。动态采样会过滤零方差组；`n=2` 在 8 道可解 smoke 题上很容易全对或全错，导致 batch 被过滤空，误报为链路故障。

建议二选一：

```text
推荐：S1-7a 把 n 从 2 提到 4，尽量沿用 E2 的生产配置。
备选：保留 n=2，但显式关闭动态采样，并在 report 中标注这是 bring-up 偏离，不代表生产配置。
```

其他 flags 建议尽量沿用 E2：

```text
disable-grpo-std-normalization
clip low/high = 0.2 / 0.28
top_p = 0.95
```

### A3. S1 acceptance 必须明确不关闭 30B-A3B MoE 全要素训练风险

必要性：必须补。

S1-7a 用 Qwen3-4B dense 跑真实训练传输 step；S1-7b 把 30B-A3B 全要素训练 step 推迟到 S4 前 8 卡预实验。因此 S1 通过后不能写成“30B MoE 主训练闭环完成”。

建议 `s1_acceptance_summary.json` 与 `bringup_7a_report.md` 明确写：

```text
S1 关闭的是 slime 形态 B 的数据链路闭环。
S1-7a 使用 Qwen3-4B dense 验证 custom_generate / projection / gate / trainer step。
30B-A3B 的 top-p/routing 服务端能力由 S1-0 探针验证。
30B-A3B 全要素训练 step、多卡训练侧、routing tape 训练消费、显存与通信风险递延到 S4 前预实验。
```

### A4. S1-3 不能只依赖 slime Sample，必须增加原始生成捕获 sidecar

必要性：必须补。

slime `Sample` 是训练容器，不是完整审计事实源。top-p tape、routing tape、logprob provenance、sampling 参数和后端版本等事实应该在 SGLang 客户端响应层捕获，再进入中立投影。

建议在 S1-1 contracts 或 S1-3 adapter 中新增对象，例如：

```text
GenerationCaptureRecord
```

至少记录：

```text
request_id / turn_id / trajectory_id
model_name / backend_name / backend_version
sampling_params，例如 top_p、temperature、max_tokens
renderer_cls_name / tokenizer_name / template_hash
prompt_token_ids_hash 或 prompt_token_ids_ref
response_token_ids_ref
raw_meta_info_ref 或 raw_meta_info_digest
logprobs_ref
top_p_token_ids_ref / top_p_token_offsets_ref
routed_experts_ref
capture_status / alignment_status
```

`TrajectoryProjection` 应引用该 sidecar，而不是从训练后的 `Sample` 反推全部审计事实。

### A5. S1-6 前必须定义 sandbox ownership handshake

必要性：必须补。

slime Claude Code harness 可能假设自己拥有 Sandbox Protocol；RepoHarness envpack 又要负责 `/testbed` 物化、public/private bundle、评分边界和后续清理。两边如果没有握手契约，S1-6 很容易变成临时胶水。

建议新增或明确以下对象：

```text
SandboxLease
WorkspaceHandle
HarnessLaunchSpec
ModelProxyEndpoint
CleanupPolicy
```

至少说明：

```text
谁创建容器。
谁物化 /testbed。
Claude Code harness 的 workdir 如何传入。
模型代理地址如何注入。
网络策略和权限策略由谁拥有。
public task bundle 与 private grading bundle 如何挂载，private bundle 不得进入 rollout 容器。
失败后谁负责清理容器、临时目录和挂载。
清理失败如何写入 FailureCategory 或 runtime finding。
```

### A6. S1-2 必须显式拆分 public task bundle 与 private grading bundle

必要性：必须补。

SWE 数据天然包含评分私有信息，例如：

```text
golden patch
test_patch
FAIL_TO_PASS
PASS_TO_PASS
official parser config
hidden test / grader-only asset
```

这些字段可以给评分器，但不能给模型、不能进入 public projection、不能进入 SFT/export 数据。

建议 S1-2 验收增加：

```text
1. public task bundle 只包含模型可见题面、repo/base_commit、镜像 digest、允许工具、公开环境提示等。
2. private grading bundle 单独存放 test_patch、F2P/P2P、official parser 配置、golden 相关信息。
3. 两个 bundle 分别有 digest。
4. public bundle 泄漏扫描覆盖 golden_patch、test_patch、FAIL_TO_PASS、PASS_TO_PASS、hidden_verifier、grader_only 等字段名。
```

### A7. S1-4 必须包含最小 patch hygiene，不能全部推迟到 S2

必要性：必须补。

完整 anti-cheat 可以留到 S2，但 S1-4 已经要产生 reward，因此必须保证 reward 来自 clean grading checkout，而不是污染的 agent workspace。

S1 最小要求：

```text
1. 从 agent workspace 导出 cleaned final patch。
2. 在 fresh grading sandbox / clean checkout 上应用该 patch。
3. 拒绝或降级测试文件篡改。
4. 拒绝或降级题面文件、运行时私有文件、grader-only 文件污染。
5. 再运行官方 parser。
6. patch_apply_failed、tests_failed、infra_failure 必须区分。
7. infra_failure 绝不能落成 reward=0。
```

### A8. S1-1 contracts 完成时同步编写对象开发文档

必要性：建议作为 S1-1 验收产物。

建议新增：

```text
docs/agentic_RL/repo_harness_rh2_workstreams/s1/contracts_object_guide.md
```

文档必须按对象生命周期讲，不要只列字段表。至少覆盖：

```text
slime 原始响应 / GenerationCaptureRecord
-> project_from_slime
-> TrajectoryProjection
-> GradingResult / RewardFacts
-> EligibilityReport
-> TrainingExportRecord / slime debug training transport
```

每个对象说明：

```text
职责
创建者
消费者
关键字段
是否训练安全关键字段
非法时如何 fail-closed
禁止出现在 public projection 的字段
最小合法样例
非法样例
```

### A9. F5 评分并发参数建议调整为更保守的默认值

必要性：建议补。

当前计划推荐评分并发 8、队列 16。S1 规模只有 8 题 x n=2 或 n=4，一开始并发 8 可能制造 Docker、CPU、内存、磁盘抖动，反而增加排障成本。

建议：

```text
首版默认评分并发 = 4
队列大小 = 2 x 并发 = 8
并发数必须可配置
evidence 记录容器峰值、队列等待、评分耗时、prep/test/env_reset/image_pull 分段耗时
如果实测稳定，再升到 8
```

### A10. F6 slime pin 必须包含机器可读探针结果

必要性：建议补。

S1-0 通过后，除了写 `uh_probe_report.md`，建议同时写机器可读结果：

```text
docs/agentic_RL/repo_harness_rh2_workstreams/s1/uh_probe_result.json
```

至少包含：

```text
slime commit
slime image digest
SGLang version
CUDA / GPU 信息
model name
sampling params
top_p_token_ids / top_p_token_offsets presence
routed_experts presence
output_ids / logprobs / top-p offsets / routing shape 对齐结果
```

`inspect-rh2-s1` 应读取该 JSON，而不是只读自然语言报告。

---

## 二、有必要排期，但不阻塞 S1-0 的建议

### B1. GPU pass-rate 预筛与 pre-RL 行为诊断需要明确归属

必要性：必须排期，但不阻塞 S1-0。

实验设计 E3/E4 已经定了：

```text
GPU pass-rate 预筛 [0.1, 0.8]
pre-RL 行为诊断硬门
两者合并为同一批 rollout
```

当前 S1 计划的 F3 只安排了 SWE-Gym Lite 静态预筛，没有安排 GPU pass-rate 预筛和 pre-RL 诊断。该步骤需要目标模型推理端点，但不需要 8 卡训练；单卡 30B 推理即可。

建议在后续计划中显式新增：

```text
S2 末或 S3-0：单卡 30B GPU pass-rate 预筛 + pre-RL 行为诊断
```

F4 GPU 租用策略从三段式改为四段式：

```text
1. S1-0 单卡短租：U-H 验证。
2. S1-7a 单/双卡短租：dense 数据链路 bring-up。
3. S2 末或 S3-0 单卡短租：30B pass-rate 预筛 + pre-RL 诊断。
4. S4 前 8 卡整机：30B-A3B 全要素训练 step + U-C + 吞吐画像。
```

---

## 三、低风险但建议收口时修正的文档与验收语义

### C1. S1-8 parity 建议拆成 parity-core 与 parity-cross

必要性：建议补，避免误读。

当前 S1-8 把 parity 写在一句里，语义基本正确，但容易混淆两类一致性。

建议拆成：

```text
parity-core：
  比较 slime 在线训练消费路径与 offline export。
  同 renderer / 同 projection。
  token 可以逐位一致。
  这是 E8 解耦证据本体。

parity-cross：
  比较 verifiers 路径与 slime 路径。
  只比较治理事实、RewardFacts、eligibility、logprob_source、provenance。
  token 不强求逐位一致，除非 renderer/tokenizer/template 完全相同。
```

### C2. 8 题冻结状态文档需要同步

必要性：建议补。

当前状态存在文档不一致：

```text
03-s1-execution-plan.md 写：8 题题单已冻结。
s0/swe_smoke_report.md 仍写：初选 8 题，待用户过目后长期冻结。
```

如果用户已经确认题单冻结，应更新 `s0/swe_smoke_report.md` 的状态行。若尚未确认，则 S1-2 必须包含人工确认步骤。

### C3. S1 acceptance summary 应显式记录递延风险

必要性：建议补。

`s1_acceptance_summary.json` 不应只记录 pass/fail，还应记录递延风险：

```text
30B-A3B full-feature training step deferred_to_s4_pre_8card
U-C_multiGPU_training_side still_open
routing tape training consumption not closed by S1-7a dense run
S1-7a checkpoint_discarded=true
rh2_formal_training_allowed=false
```

---

## 四、执行 agent 可按此优先级处理

```text
可以先做：
  S1-0 U-H 验证。该任务与本文大部分修改不冲突。

进入 S1-1 前必须吸收：
  GenerationCaptureRecord
  contracts_object_guide.md
  Eligibility / Grading / Timing 等 schema 的 fail-closed 语义

进入 S1-2 前必须吸收：
  public task bundle / private grading bundle 拆分
  8 题冻结状态同步

进入 S1-4 前必须吸收：
  clean final patch replay
  最小 patch hygiene
  P1~P11 对照矩阵

进入 S1-6 前必须吸收：
  sandbox ownership handshake

进入 S1-7a 前必须吸收：
  checkpoint 即弃
  debug training transport 命名
  top_p=0.95 + top-p tape 消费验证
  n=4 或显式关闭动态采样并记录偏离

S1-8 / S1-9 收口时必须吸收：
  parity-core / parity-cross 拆分
  acceptance summary 明确 30B MoE 全要素风险递延
```
