# S1-1 contracts 对象开发指南（按 9 步生命周期讲）

> 本文是补充条款 A8 要求的对象开发文档：**按对象的生命周期讲，不是字段表**。
> schema 源码在 `rh2/src/repoharness2/contracts/`，字段级说明都写在各字段的
> `Field(description=...)` 里；本文回答的是"这个对象在链路的哪一步出生、
> 谁生产、谁消费、哪些字段是训练安全关键、非法时怎么 fail-closed"。
> 所有样例的数值都来自真实探针：prompt 15 token、生成 16 token、
> top-p offsets 长 17、routing 形状 [30, 48, 8]（`s1/uh_probe_result.json`）。

---

## 0. 一张地图：9 步生命周期 × 契约对象

02 文档 §8 定义了形态 B 下一条轨迹的 9 步生命周期。每个契约对象都能定位到
"在哪一步被谁创建、在哪几步被谁消费"：

```text
步骤（[]为组件归属）                          在这一步出生的契约对象
1. slime 触发 custom_generate                 （无——入口参数）
2. [RepoHarness 库] 环境包物化 + 血缘校验      SandboxLease / CleanupPolicy /
                                              WorkspaceHandle（含 BundleMount）
3. [slime 现成] Claude Code harness 启动       HarnessLaunchSpec / ModelProxyEndpoint
4. [slime 现成] adapter -> SGLang /generate    GenerationCaptureRecord（每轮一条）
5. [slime 现成] TrajectoryManager 归并分支     （无 rh2 对象；产出 slime Sample）
6. [RepoHarness 库] GradingManager 评分        GradingReport（内含 PatchHygieneResult
                                              + GradingTimingRecord）
   （2~6 横切）反作弊防线                      AntiHackEvent / AntiCheatFinding /
                                              TrajectoryQualityFinding
7. [RepoHarness] project_from_slime 投影       TrajectoryProjection（含 BranchProjection、
                                              TokenSpan、LossMaskSpan、LogprobProvenance、
                                              RoutingTensorRef、SamplingMaskRef、
                                              RewardFacts、CompactedSubTraceLineage）
8. [RepoHarness] EligibilityGate 定资格        EligibilityReport（七维事实 + 三档结论）
9. 合格样本交接训练后端 / 离线导出             BackendHandshake（含 GroupSignal）
```

公共机制（不属于某一步）：`constants.py` 的 `FORBIDDEN_PUBLIC_MARKERS` 泄漏扫描、
`inspect-rh2-artifact` 校验命令、`SCHEMA_REGISTRY`（schema_id -> 模型类）。

所有对象共享四条"宪法"级约定（`_base.py`）：

1. `extra="forbid"`：未知字段一律拒收。谁想偷偷塞一个新 key 进 evidence，
   校验直接失败，而不是静默透传。
2. `frozen=True`：构造完成即不可变。evidence 不允许事后改字段。
3. `allow_inf_nan=False`（S1-1b 补）：全部 float 字段拒收 NaN/±inf，基类一处
   生效覆盖 14 个 schema。为什么必须在基类拦：`reward=float("nan")` 能穿过
   `reward <= 0.0` 这类比较校验器（NaN 与任何数比较都是 False），一路流进
   训练 batch 会把整个 loss 变成 NaN。数值缺失的唯一合法表示是 `null` +
   相应语义字段（如 `reward_scope="none"`），绝不是 NaN。
4. 大对象只存 `ArtifactRef`（opaque 引用 + 可选 sha256）：契约对象本身
   永不内嵌 token 数组、tape 张量、日志正文。

---

## 1. 步骤 2：环境包物化 —— sandbox 握手对象（A5 八问）

### 1.1 SandboxLease（`sandbox.py`）

- **职责**：一次容器租约的完整事实——谁建的（A5-Q1）、干什么用（rollout 还是
  grading）、网络/权限策略归谁（A5-Q5）、怎么清理（内嵌 CleanupPolicy，A5-Q7/Q8）。
- **创建者**：`repoharness_envpack` 库层（S1-6 编排调用它起容器时写出）。
- **消费者**：S1-6 编排（把 lease 传给 harness 与评分）、清理逻辑、审计。
- **训练安全关键字段**：`purpose`（评分容器与 rollout 容器永不混用）、
  `network_policy`（评分容器必须 `deny_all`，P9）。
- **fail-closed 行为**：`host_open` 直接不可表示（verifiers docker 的宿主网络
  旧形态在本契约下必须先收紧）；`purpose="grading"` 而网络不是 `deny_all` 拒收；
  `allowlist` 不写理由拒收。

最小合法样例（关键字段）：

```json
{"schema_id": "rh2.sandbox_lease.v1", "lease_id": "lease_0001",
 "container_id": "rh2_rollout_traj_0001", "image_digest": "sha256:ee…(64hex)",
 "purpose": "rollout", "created_by": "repoharness_envpack",
 "network_policy_owner": "repoharness_envpack", "network_policy": "deny_all",
 "permission_policy_owner": "repoharness_envpack", "run_as_user": "root",
 "cleanup": {…见 1.3…}, "created_at_utc": "2026-07-07T09:30:25Z"}
```

非法样例（拒收原因）：

```json
{"purpose": "grading", "network_policy": "allowlist", …}
→ ValidationError: 评分容器必须全断网（P9）
```

### 1.2 WorkspaceHandle（`sandbox.py`）

- **职责**：一个已物化工作区的句柄：/testbed 血缘已验证（A5-Q2）+ bundle
  挂载清单（A5-Q6）。
- **创建者**：`repoharness_envpack`（物化 + 血缘校验通过后签发）。
- **消费者**：HarnessLaunchSpec（workdir 指向它）、GradingManager（评分工作区）。
- **训练安全关键字段**：`mounted_bundles`（rollout 工作区禁挂 private bundle，
  这是 A6 泄漏防线的物理落点）、`lineage_check`。
- **fail-closed 行为**：三层。
  1. `lineage_check` 只有两个"通过"取值（`head_equals_base` /
     `head_parent_equals_base`）——**血缘校验失败的工作区根本构造不出句柄**，
     不存在 "lineage_failed" 值；
  2. 声明 `head_equals_base` 但 head != base 拒收（反之亦然）；
  3. `role="rollout_workspace"` 且挂了 `private_grading_bundle` 拒收。

具体数值例（django-11099 真实血缘）：官方镜像 HEAD=`2a2861e0…` 不是
base=`d26b2424…`，但 HEAD^==base，所以填 `"lineage_check": "head_parent_equals_base"`。

非法样例：

```json
{"role": "rollout_workspace",
 "mounted_bundles": [{"bundle_kind": "private_grading_bundle", …}]}
→ ValidationError: rollout_workspace 禁止挂载 private_grading_bundle（A6）
```

### 1.3 CleanupPolicy（`sandbox.py`）

- **职责**：A5-Q7/Q8——失败后谁清理、清理哪些东西、清理失败怎么记录。
- **创建者**：编排层（随 lease 一起声明）。**消费者**：清理执行方与审计。
- **fail-closed 行为**：`on_cleanup_failure` 只有两个取值
  （`record_runtime_finding_and_infra_failure` / `record_finding_and_escalate_abort`），
  **都包含"先记录"义务**——"清理失败但不留痕"不可表示；steps 空/重复拒收。

```json
{"schema_id": "rh2.cleanup_policy.v1", "owner": "repoharness_envpack",
 "steps": ["remove_container", "remove_temp_dirs", "release_lease"],
 "on_cleanup_failure": "record_runtime_finding_and_infra_failure",
 "timeout_seconds": 120}
```

---

## 2. 步骤 3：harness 启动 —— HarnessLaunchSpec / ModelProxyEndpoint

### 2.1 ModelProxyEndpoint（`sandbox.py`）

- **职责**：A5-Q4——黑盒 harness 的模型请求如何被 slime adapter 接管：
  代理地址、wire 协议、session_id（兼作 auth token 与路由键）。
- **创建者**：slime adapter 侧（S1-6 起代理端点时写出）。
- **消费者**：HarnessLaunchSpec（内嵌）、GenerationCaptureRecord 的上游。
- **fail-closed 行为**：wire 协议与注入环境变量名强制配对——
  `anthropic_messages` 必须配 `ANTHROPIC_BASE_URL`，`openai_chat` 必须配
  `OPENAI_BASE_URL`。防止"Claude Code 指到 OpenAI 端点"这类静默错配。

```json
{"schema_id": "rh2.model_proxy_endpoint.v1", "base_url": "http://10.0.0.5:8200",
 "wire_protocol": "anthropic_messages", "session_id": "sess_traj_0001",
 "inject_env_var": "ANTHROPIC_BASE_URL"}
```

非法样例：`{"wire_protocol": "anthropic_messages", "inject_env_var": "OPENAI_BASE_URL"}`
→ 拒收（协议错配）。

### 2.2 HarnessLaunchSpec（`sandbox.py`）

- **职责**：A5-Q3/Q4 的合成点——在哪个工作区、workdir 是什么、连哪个代理、
  注入哪些环境变量、时间预算多少。
- **创建者**：S1-6 编排。**消费者**：slime Claude Code harness 启动逻辑。
- **训练安全关键字段**：`env_injections`——**这是模型可见面**。harness 环境里
  的每个 key/value 都会过 forbidden marker 扫描。
- **fail-closed 行为**：workdir 必须绝对路径；env key 必须大写标识符；
  env key/value 命中 marker（例如把 `/rh2/private/test_patch.diff` 注进环境）
  直接拒收。

非法样例：

```json
{"env_injections": {"RH2_HINT": "/rh2/private/test_patch.diff"}, …}
→ ValidationError: env_injections 变量值命中 forbidden marker 'test_patch'
```

---

## 3. 步骤 4：SGLang 生成 —— GenerationCaptureRecord（A4）

- **职责**：**原始生成事实的唯一权威来源**。slime `Sample` 是训练容器不是审计
  事实源；每次 `/generate` 响应到达 adapter 的那一刻，就要把"模型真实看到/
  真实采出什么、服务端是谁、tape 有没有回来"固化成一条本记录。
- **创建者**：S1-6 在 slime Anthropic adapter 里注入的捕获钩子（每轮一条）。
- **消费者**：`project_from_slime`（步骤 7 回链）、`inspect-rh2-artifact`、
  S1-8 parity 校验、U-H 回归排查。
- **训练安全关键字段**：`capture_status` / `alignment_status`（gate 的
  token_provenance 维度直接看它们）、三组 tape 引用。
- **fail-closed 行为（最重要的一条是防"镜像静默降级"）**：
  - 请求了 top-p tape（`top_p<1.0` 且 `return_top_p_token_ids=true`）而响应
    没带 → **禁止自称 `complete`**。stock SGLang 0.5.9 对 tape 请求就是
    200 返回但字段缺席（S0-6 分水岭证据），这种轮次必须落 `partial`+`mismatch`；
  - `complete` 必须同时满足：有 output ids 引用、有 logprobs 引用、
    `alignment_status="aligned"`、请求过的 tape 都在场；
  - top-p 的 ids/offsets 引用必须成对（slime 同款约束）；
  - prompt 至少给 hash 或 ref 之一；raw meta_info 至少给 digest 或 ref 之一
    （meta_info 一条在 `capture_status="failed"` 时豁免——请求失败可能根本
    没拿到 meta_info，强求会逼生产者伪造 digest）；
  - `response_token_count > 0` ⇒ `response_token_ids_ref` 必填（S1-1b 收紧：
    partial/failed 也不豁免——声称生成了 16 个 token 却指不出 ids 在哪，
    这个计数就无凭据）；
  - `capture_status="failed"` ⇒ `capture_failure_reason` 必填（失败不可无因，
    如 `request_timeout` / `response_parse_error`）；complete/partial 携带
    该字段反向拒收。

最小合法样例（真实形状，S1-0 探针）：

```json
{"schema_id": "rh2.generation_capture_record.v1", "record_id": "cap_0001",
 "request_id": "68ecd97a303343fdb0d984cd8e86e011", "turn_id": "turn_0",
 "trajectory_id": "traj_0001", "model_name": "Qwen/Qwen3-30B-A3B",
 "backend_name": "sglang", "backend_version": "0.5.9",
 "sampling_params": {"temperature": 1.0, "top_p": 0.95, "max_new_tokens": 16,
                     "return_top_p_token_ids": true, "return_routed_experts": true},
 "renderer_cls_name": "Qwen3Renderer", "tokenizer_name": "Qwen/Qwen3-30B-A3B",
 "template_hash": "sha256:aa…", "prompt_token_count": 15, "response_token_count": 16,
 "prompt_token_ids_sha256": "sha256:bb…", "prompt_token_ids_ref": {"ref_id": "prompt_ids_0001"},
 "response_token_ids_ref": {"ref_id": "output_ids_0001"},
 "raw_meta_info_digest": "sha256:cc…", "logprobs_ref": {"ref_id": "logprobs_0001"},
 "top_p_token_ids_ref": {"ref_id": "topp_ids_0001"},
 "top_p_token_offsets_ref": {"ref_id": "topp_offsets_0001"},
 "routed_experts_ref": {"ref_id": "routing_tape_0001"},
 "capture_status": "complete", "alignment_status": "aligned",
 "captured_at_utc": "2026-07-07T09:30:25Z"}
```

非法 vs 合法对比（同一个"tape 没回来"事实的两种写法）：

```text
非法：top_p_token_ids_ref=null + capture_status="complete"
      → 拒收（静默降级不许自称完整）
合法：top_p_token_ids_ref=null + capture_status="partial" + alignment_status="mismatch"
      → 通过（事实要可记录，但 gate 会把它挡在 online 档外）
```

dense 模型（S1-7a 的 Qwen3-4B）注意：请求方传 `return_routed_experts=false`，
`routed_experts_ref=null` 也能 `complete`——"没请求"与"请求了没给"是两回事。

---

## 4. 步骤 6：评分 —— GradingReport / PatchHygieneResult / GradingTimingRecord

### 4.1 GradingReport（`grading.py`）

- **职责**：一次评分动作的完整结论：三态 outcome、失败归因三分、reward、
  F2P/P2P 计数、hygiene 结果、计时。
- **创建者**：SWEGradingManager（S1-4；在 custom_generate 编排之内，
  不是"返回后再打分"）。
- **消费者**：RewardFacts（`reward_event_refs` 指向它）、gate 的 clean_grading
  维度、S1-4 故障注入测试、F5 吞吐画像。
- **训练安全关键字段**：`failure_category` 与 `reward` 的互锁 +
  `reward_scale_version` 二值锁。
- **fail-closed 行为（互锁表，S1-1b 收紧版）**：

```text
outcome           允许的 failure_category            reward        测试计数
resolved          （必须无）                          恰为 1.0      四个计数齐全，且
                                                                  f2p_pass==f2p_total、p2p_fail==0
unresolved        patch_apply_failed                 恰为 0.0      必须全 null（测试未运行）
                  tests_failed                       恰为 0.0      四个计数必须齐全
failed_to_grade   infra_failure|test_log_parse_failed 必须为 null   必须全 null，且必须写
                  （infra 族）                                      infra_failure_detail
```

**reward 二值锁（S1-1b，`reward_scale_version="binary_v1"`）**：S1 的 reward
语义是严格二值，schema 把它锁死——不是"resolved 时 > 0"，而是"恰为 1.0"。
未来引入连续 reward（部分分、process 分量并入等）必须新增
`reward_scale_version` 枚举值并同步改校验器，不允许在 binary_v1 下静默放宽。
最小正反样例（R1/R3 回归）：

```text
非法：{"outcome": "unresolved", "failure_category": "tests_failed", "reward": 1.0, …}
      → 拒收（R1：负样本携带满分 reward，训练信号直接反转）
非法：{"outcome": "resolved", "reward": 0.5, …}
      → 拒收（R3：binary_v1 下不存在中间值，0.5 必须先升版才可表示）
合法：{"outcome": "resolved", "reward": 1.0, "reward_scale_version": "binary_v1", …}
合法：{"outcome": "unresolved", "failure_category": "tests_failed", "reward": 0.0,
       "f2p_pass_count": 1, "f2p_total_count": 3, "p2p_fail_count": 0, "p2p_total_count": 52, …}
```

**infra 族有两个成员（S1-1b 新增 `test_log_parse_failed`）**：
"测试跑了但官方 parser 从日志里解析不出结果"（标记缺失、输出截断）是评分
链路的问题，不是模型的负样本，与 `infra_failure` 同族、同样强制 reward=null。
由此 `tests_failed` 的边界收紧为"测试跑了**且日志解析成功**"——所以它必须
带全四个计数（R4 回归：tests_failed + 四计数全空即拒收，解析不出计数就该
归因 test_log_parse_failed 而不是伪装成负样本）。

**点名非法样例（本阶段最重要的一条）**：

```json
{"outcome": "failed_to_grade", "failure_category": "infra_failure", "reward": 0.0}
→ ValidationError: infra 族归因时 reward 必须为 None
   （基建故障绝不允许伪装成 reward=0 的负样本——否则模型会被评分容器 OOM "教育"）
```

对应合法写法：`"reward": null` + `"infra_failure_detail": "grading_container_killed_oom"`；
日志解析失败同形态：`"failure_category": "test_log_parse_failed"` +
`"infra_failure_detail": "test_output_markers_missing"`。

### 4.2 PatchHygieneResult（内嵌于 GradingReport）

- **职责**：A7 最小 patch hygiene 的结论：cleaned patch 的 digest、是否在
  clean checkout 重放、是否篡改测试、是否污染禁区文件。
- **fail-closed 行为**：verdict 与布尔事实互锁（`test_files_modified=true`
  时 verdict 必须是 `rejected_test_tampering`；`verdict="clean"` 时两个布尔
  必须都是 false；`forbidden_paths` 非空 ⇔ `forbidden_path_touched=true`）。
  另外在 GradingReport 层：**hygiene 被拒的 patch 不允许 outcome="resolved"**。

### 4.3 GradingTimingRecord（`timing.py`）

- **职责**：F5 的五类计时 + 资源画像。五类 =
  `image_pull / env_reset / prep / test / total_grading`，
  外加 `queue_wait_seconds`（P11 有界队列）与 `container_peak_memory_mb`。
- **创建者**：GradingManager 的计时埋点。**消费者**：F5 升并发决策
  （4→8 要看实测）、s1 acceptance evidence。
- **fail-closed 行为**：全部必填（"忘了测"不可表示）；时长非负；
  `total >= test`（总时长小于分段是明显记录错误）。

具体数值例（S0-7 八题均值 53.4s 的拆分形态）：

```json
{"image_pull_seconds": 0.0, "env_reset_seconds": 3.2, "prep_seconds": 2.1,
 "test_seconds": 41.7, "total_grading_seconds": 53.4,
 "queue_wait_seconds": 1.3, "container_peak_memory_mb": 2048.0}
```

---

## 5. 横切（步骤 2~6）：反作弊三件套

### 5.1 AntiHackEvent（`anti_hack.py`）——在线拦截事件

- **职责**：一次"block + dummy 观测 + rollout 继续"拦截的完整存证（§5.3 定案）。
- **创建者**：运行期命令过滤/网络拦截层（**S2 才接 filter，S1-1 只落 schema**）。
- **消费者**：AntiCheatFinding（attempted 必须回链它）、gate、红队回放。
- **训练安全关键字段**：`blocked_tool_call_ref`（拦了什么，runtime-private）与
  `dummy_observation_ref`（**给模型看了什么**——治理层必须能核对模型上下文里
  实际注入的观测不含泄漏内容）。两者都必填："拦了但没存证"不可表示。

```json
{"schema_id": "rh2.anti_hack_event.v1", "event_id": "antihack_0001",
 "trajectory_id": "traj_0001", "turn_id": "turn_3", "rule_id": "block_remote_git",
 "channel": "network_egress",
 "blocked_tool_call_ref": {"ref_id": "blocked_call_0001"},
 "dummy_observation_ref": {"ref_id": "dummy_obs_0001"},
 "rollout_continued": true, "occurred_at_utc": "2026-07-07T09:31:02Z"}
```

### 5.2 AntiCheatFinding（`findings.py`）——attempted|executed 的分水岭

- **职责**：一条反作弊事实结论，是 gate `security_and_leakage` 维度的证据单元。
- **attempted vs executed（资格后果完全不同）**：

```text
attempted_blocked：作弊被拦，泄漏内容没进模型上下文。
  → 轨迹仍可训练（"此路不通"本身是训练信号），可选 process penalty。
  → 必须回链 anti_hack_event_ref（没有拦截存证的 attempted 不可表示，
    防止把 executed 谎报成 attempted 逃过降级）。
executed：作弊实际发生（内容已进上下文/篡改已落盘）。
  → gate 的 security 维度失败 → 结论强制 audit_only_or_rejected（见 §7）。
```

- **fail-closed 行为**：attempted 无 `anti_hack_event_ref` 拒收；
  `judge_precision` 只许配 `detection_layer="llm_judge_review"`（LLM judge
  是异步复核，不阻塞 rollout，结果回写这一个字段）。

### 5.3 TrajectoryQualityFinding（`findings.py`）

- **职责**：过程质量事实（unfinished/timeout/max_turns/malformed_tool_call/
  谎报成功 claim 无证据/空 patch…）。按 §16.11 末段：过程问题走 finding 与
  reward 分量，**不反向修改 loss_mask**。
- **消费者**：warm-start/SFT 过滤、process reward 分量、审计。

注意：这三件套 + GradingReport 是 **runtime-private 审计资产**——它们的内容
天然要提到 test_patch、私有路径等词（描述作弊就得说清楚拦了什么），所以
`inspect-rh2-artifact` 默认对它们豁免 marker 扫描（`--force-marker-scan`
可强制）。但它们**永远不得进入 public projection**——public 侧的扫描不看豁免表。

---

## 6. 步骤 7：中立投影 —— TrajectoryProjection 全家

这是治理层解耦的核心：gate 与所有下游 adapter **只消费本对象**，
投影完成后治理层看不出样本来自 slime 还是 verifiers。tape 解码只允许在
投影层做一次（S0 结论 5）。

### 6.1 token 座标系（先读这个，其他都建立在它上面）

一条分支的完整 token 序列 = prompt 段 + response 段，0 起下标。
具体数值例（贯穿全文的真实形状）：prompt 15 个 token、生成 16 个 →
total=31；TokenSpan 平铺 `[0,31)`；LossMaskSpan 平铺 response 段 `[15,31)`
（对齐 slime `loss_mask` 长度==response_length 的语义）。

### 6.2 TokenSpan / LossMaskSpan —— H4 的 schema 落点

- **TokenSpan**：每段 token 的来源归属。7 种来源里只有 `sampled_assistant`
  可被训练。**校验器强制所有 span 无缝无重叠平铺 [0,total)**——"没人认领"
  的 token 直接让整个对象拒收。
- **LossMaskSpan**：mask 值 + 理由码。**mask=1 ⇔ reason="sampled_assistant_trainable"**，
  且每个 mask=1 的 span 必须完全落在 sampled_assistant 区间内。

正例/反例对比（多轮场景，tool 输出夹在两段生成中间）：

```text
token_spans:  [0,15) prompt_context | [15,23) sampled_assistant | [23,31) tool_result
合法 loss_mask_spans: [15,23) mask=1 sampled_assistant_trainable
                      [23,31) mask=0 tool_or_env_context
非法 loss_mask_spans: [15,31) mask=1 sampled_assistant_trainable
→ 拒收：mask=1 的 [15,31) 没有完全落在 sampled_assistant 区间（[23,31) 是工具输出，
  参训即污染——这正是 H4 拦的事故形态）
```

**mask=0 的 reason 也要与来源互检（S1-1b，N-3）**：sampled_assistant 来源的
token 若不参训，reason 只允许降级类（`replayed_sibling_response` /
`retokenization_drift_downgraded`）——标成 `prompt_context` /
`tool_or_env_context` 这类"本来就是上下文"的理由等于抹掉降级事实，审计线索
就断了。反向不受影响：真在 tool_result 来源上的 mask=0 照常标
tool_or_env_context。

```text
token_spans:  [0,15) prompt_context | [15,31) sampled_assistant
非法 loss_mask_spans: [15,23) mask=1 sampled_assistant_trainable
                      [23,31) mask=0 tool_or_env_context
→ 拒收：[23,31) 是模型采样段，"不训练"必须给降级理由，不得伪装成工具输出
合法改法：[23,31) mask=0 retokenization_drift_downgraded
```

### 6.3 LogprobProvenance —— M4 logprob_source

- **职责**：logprob 是"谁、哪个版本、什么精度"算的：
  `engine_name`（sglang|vllm，封闭枚举）、`engine_version`（"0.5.9"）、
  `precision`（bfloat16）、`sampling_backend`（"pytorch"——Blackwell 关
  FLASHINFER 的事实要可审计）、`weight_version`。
- **为什么必须有**：透传无损是必要非充分——同权重下推理引擎与训练引擎分布
  仍系统性不同（ROME），训练侧要做 IS/TIS 校正（归后端 H10），校正的前提是
  知道 logprob 出处。

### 6.4 RoutingTensorRef —— 引擎对齐约定必须显式（S1-0 New-Unknown 的落点）

两引擎行数约定**不同构**（实测）：

```text
SGLang: 行数 = prompt_len - 1 + generated_len   （15-1+16 = 30，S1-0 探针）
vLLM:   行数 = prompt_len + generated_len       （13+8   = 21，S0-5 探针）
```

- **fail-closed 行为**（逐条）：
  1. `alignment` 必填 → "tensor 在场但没说约定"**不可表示**（点名非法样例）；
  2. dense 声明（`not_applicable_dense_model`）与任何 tensor 字段互斥——
     A2 要求 dense 缺 routing 必须显式声明，不得静默成功；
  3. 引擎值时七个 tensor 字段必须齐全，且 `num_rows` 精确满足该引擎公式，
     差一行拒收（把 vLLM 的 31 行填给 SGLang 约定 → 拒收）。

```json
{"alignment": "sglang_prompt_minus1_plus_gen",
 "tensor_ref": {"ref_id": "routing_tape_0001"},
 "num_rows": 30, "num_layers": 48, "router_topk": 8, "dtype": "int32",
 "prompt_token_count": 15, "generated_token_count": 16}
```

### 6.5 SamplingMaskRef —— top-p tape（E2 top_p=0.95 硬依赖）

语义对齐 slime：response 第 i 个 token 的保留核集合是
`ids[offsets[i]:offsets[i+1]]`；offsets 长度 = response_token_count + 1
（生成 16 → 长 17，`uh_probe_result.json` 的 `offsets_eq_genlen_plus_1`）。

- **fail-closed 行为**：`top_p<1.0` 缺 tape **不可表示**（stock SGLang 静默
  忽略形态被 schema 挡死）；`top_p=1.0` 必须显式 `not_applicable_top_p_1`；
  `offsets_len != response+1` 拒收；`kept_token_count < response_token_count`
  拒收（S1-1b，N-4：top-p 对每个 response token 至少保留 1 个核 token，
  16 个 token 的 tape 总保留数不可能低于 16——低了说明 tape 记录不完整）。

### 6.6 RewardFacts —— §16.11 的落点 + fan-out 建模定案

- **职责**：raw reward + components + 组信号。归一化/advantage 归训练后端。
- **fail-closed 行为**：
  - `reward_scope="none"` ⇒ `raw_reward` 必须 null（infra 场景禁止携带 0.0，
    与 GradingReport 的规则首尾呼应）；NaN/inf 由基类 `allow_inf_nan=False`
    拒收（R5 回归：NaN 能穿过所有数值比较校验器）；
  - `trace_level` ⇒ `reward_event_refs` 至少一条（reward must 有出处）；
  - `group_level` ⇒ `group_id/parent_rollout_id/segment_count/
    rollout_loss_denominator` 四件齐全（防 compaction fan-out 重复放大，
    `rollout_loss_denominator` 即 slime `rollout_mask_sums` 语义）。

**fan-out 建模定案（S1-1b）：单投影多 branches 为权威**。一个 rollout/session
产一个 TrajectoryProjection，compaction/fan-out 的全部分段作为它的 branches，
不拆成多个投影对象。由此两条硬规则：

1. `segment_count`（在场时）必须 == 所属投影的 `len(branches)`——投影层校验器
   互检（R6 回归）；多分支投影必须申报 segment_count，否则 fan-out 的 loss
   账目（防重复放大）无从核对；
2. `parent_rollout_id` **只用于跨 rollout 的 GRPO 同题兄弟组**（同一 prompt 的
   n 条 rollout 共享），**不用于 rollout 内分段**——rollout 内分段就是 branches。

最小正反样例（一个 rollout 被 compaction 拆成两段）：

```text
合法：TrajectoryProjection.branches = [b0, b1]（两段并列为分支）
      + reward_facts.segment_count = 2
非法：branches = [b0, b1] + segment_count = 5
→ 拒收（R6：账目对不上——分段被拆去了别的投影，或申报数被凭空放大）
非法：branches = [b0, b1] + segment_count = null
→ 拒收（多分支必须申报分段账目）
合法：branches = [b0]（无 fan-out）+ segment_count = null（隐含 1 段）
```

### 6.7 CompactedSubTraceLineage —— compaction 血缘

- **职责**：GLM-5.2"所有 compaction sub-trace 皆可训练"的前提事实：父轨迹/
  父分支、分叉事件、分叉点下标、分叉类型（压缩续写/子 agent/token 漂移 FORK）。
- **fail-closed 行为**：`replay_prefix_loss_masked` 必须为 true——重放的父
  前缀若不全为 mask=0，同段输出会被重复训练，schema 层直接拒收。

### 6.8 BranchProjection / TrajectoryProjection —— 装配层

BranchProjection 把上面所有事实装配成一条可训练分支，并做六组互检
（span 平铺、mask 落点、capture 回链、logprob 状态、routing 计数、tape 计数）。
其中容易忽略的两条：

- 有 mask=1 的 span 就必须有 `capture_record_refs`（A4：审计事实回链原始捕获，
  不从训练后的 Sample 反推）；
- `routing.prompt_token_count` 必须等于分支 `prompt_token_count`（tape 是
  给这条分支的，计数对不上说明解码接错了对象）。

TrajectoryProjection 层再加：branch_id 唯一、`renderer_cls_name`（U-G 断言
事实）、`created_at_utc` 必须带时区、`reward_facts.segment_count ==
len(branches)` 的 fan-out 账目互检（S1-1b，见 6.6 的正反样例）。

---

## 7. 步骤 8：资格门 —— EligibilityReport（七维 × 三档）

### 7.1 七维事实从哪来（映射表）

§16.1 有 8 条硬门槛，S1 口径合并成七维（条 5+条 7 同属安全面）：

```text
维度                  事实来源（生命周期步骤）
1 token_provenance    GenerationCaptureRecord（步骤 4）+ BranchProjection 回链
2 logprob_alignment   capture 的 logprobs_ref + branch 的 logprob_alignment_status
3 loss_mask_integrity BranchProjection 的 span 校验结论（步骤 7）
4 reward_scope        RewardFacts（步骤 7）
5 security_and_leakage AntiCheatFinding（executed 级）+ 投影 marker 扫描（横切）
6 clean_grading       GradingReport（步骤 6：outcome + hygiene verdict）
7 policy_staleness    BackendHandshake（步骤 9 的事实回填）
```

### 7.2 三档结论与强制降级规则

```text
online_policy_loss_eligible   七维全过才可能（schema 强制）
offline_or_sft_candidate      S1 全程的上限档（安全加固未完成，默认封顶）
audit_only_or_rejected        security 维失败时的强制档
```

- **fail-closed 行为**（五连锁）：
  1. `facts_digest` 必须等于 `compute_facts_digest(facts)` 重算值——事实被
     事后改动即拒收（inspector 四步范式的 digest 步在 schema 内自带）；
  2. 结论 online 但任一维 `ok=false` → 拒收（七维合取）;
  3. `security_and_leakage.ok=false` 而结论不是 audit → 拒收（**从严取舍**：
     executed 级泄漏内容已进上下文，做 SFT 候选同样污染数据）；
  4. 非 online 结论必须有 `reason_codes`——S1 默认封顶也要显式写
     `s1_default_ceiling_offline`，不存在"静默降级"；
  5. 派生视图互检：`derived_view_report_ref == report_id`、
     `derived_view_class == eligibility_class`。宿主（Trace.info/Sample.metadata）
     只许写这两个白名单键，inspector 拿本报告对照宿主，两边不一致即 fail。
- **每维 DimensionFact 自身**：`ok=false` 必须带 reason_codes（无理由失败
  不可表示）。

gate 侧建议用 `EligibilityReport.finalize(...)` 构造（自动算 digest、填派生
视图）；但校验器对手工构造的对象执行完全相同的检查，没有旁路。

非法样例（点名场景）：

```json
{"facts": {…七维全 ok…}, "eligibility_class": "online_policy_loss_eligible",
 "facts_digest": "sha256:000…0"}
→ ValidationError: facts_digest 与重算值不符（谁改了事实或想伪造结论）
```

---

## 8. 步骤 9：后端交接 —— BackendHandshake / GroupSignal

- **职责**：样本进训练 batch 前的最后一次握手：policy 版本、staleness、
  组信号、后端是否接受。staleness 的**使用**归后端（H10），RepoHarness 只记事实。
- **创建者**：训练后端 adapter（slime 绑定 / 离线导出）。
- **消费者**：gate 的 policy_staleness 维度、审计（拒收原因分布）。
- **accepted 语义定案（S1-1b）**：`accepted` 仅表示**后端物理接收**了这份
  样本；可训练性的唯一权威是 EligibilityReport（policy_staleness 维度消费
  本对象的 staleness 事实）。契约刻意不新增第二个"可训练"字段（R2 单一权威
  原则：两个字段各说各话时下游无所适从）。最小正反样例：

```text
合法：{"staleness_steps": 6, "staleness_threshold": 4,
       "staleness_within_threshold": false, "accepted": true, …}
      → 后端有权按自己的算法策略接收过期样本（H10），账实相符即可表示；
        但 gate 的 policy_staleness 维度照样 ok=false，online 档不可表示
        ——accepted=true 救不回资格（test_accepted_is_physical_receipt_not_trainability）
非法：{"staleness_steps": 6, "staleness_threshold": 4,
       "staleness_within_threshold": true, …}
      → 拒收（账实不符：6 > 4 却声明在阈值内，见下面第 1 条）
```
- **fail-closed 行为**：
  1. `staleness_within_threshold` 是派生结论，校验器强制它等于
     `staleness_steps <= staleness_threshold` 的重算值（6 > 4 却声明 within=true
     → 拒收，账实不符）；
  2. `accepted` 与 `backend_rejection_reason` 互斥互补（拒收不可无因）；
  3. `weight_versions_seen` 至少一个（slime `Sample.weight_versions` 语义，
     跨版本条目是 mid-rollout 权重更新的证据）；
  4. GroupSignal：`delivered + degraded <= expected_group_size`（组账目）、
     `degrade_visible_before_assembly` 必须 true（S1-5：降级必须在组装配前
     对后端可见，否则后端在残缺组上做组内归一化）。
- **算法无关**：`group_signal` 可为 null——`num_samples=1` 的 PPO 形态一等可用。

```json
{"schema_id": "rh2.backend_handshake.v1", "handshake_id": "hs_0001",
 "trajectory_id": "traj_0001", "backend_name": "slime",
 "policy_version": "step_120", "weight_versions_seen": ["default"],
 "staleness_steps": 1, "staleness_threshold": 4, "staleness_within_threshold": true,
 "group_signal": {"group_id": "group_task42", "expected_group_size": 4,
                  "delivered_sample_count": 3, "degraded_sample_count": 1,
                  "degrade_visible_before_assembly": true},
 "accepted": true, "handshaked_at_utc": "2026-07-07T09:32:11Z"}
```

---

## 9. 公共机制：marker 扫描与 inspect-rh2-artifact

### 9.1 FORBIDDEN_PUBLIC_MARKERS（`constants.py`）

名单 = A6 六项（golden_patch/test_patch/fail_to_pass/pass_to_pass/
hidden_verifier/grader_only）+ 旧 L4 evaluator-only 名单（gold_patch/
provider_secret/hidden_test_patch/…）+ 旧 batch 私有 key（run_dir/audit_ref/…），
共 23 项。匹配做两层：归一化子串（"FAIL TO PASS"→fail_to_pass）+ 紧凑子串
（"TestPatch"→testpatch）。名单按**字典序**遍历（S1-1b）：一段文本命中多个
marker 时（如 "hidden_test_patch" 同时含 hidden_test / test_patch）返回值
跨进程确定——否则不同 PYTHONHASHSEED 下 frozenset 迭代序不同，同一份输入
两次扫描报出不同 marker，evidence 无法逐字节复现比对。

**已知误报形态（有意的 fail-closed 取舍）**："latest_patches" 紧凑后含
"testpatch" 会命中。误报走人工豁免，漏报会直接污染训练数据，宁误报不漏报。
`test_compact_matching_is_fail_closed_by_design` 把这个取舍钉成回归锚点。

### 9.2 inspect-rh2-artifact（`repoharness2/cli.py`）

```text
uv run inspect-rh2-artifact <file.json> [--expect-schema ID]
                            [--force-marker-scan] [--skip-marker-scan]

流程：读 JSON → 按顶层 schema_id 查 SCHEMA_REGISTRY → pydantic 严格校验
      → marker 扫描（grading_report / 两类 finding / anti_hack_event 默认豁免）

退出码：0 通过 | 2 schema_id 缺失/未注册/不符 | 3 校验失败 | 4 marker 命中 | 5 IO/JSON 错误
```

S1-9 的 `inspect-rh2-s1` 在此之上补齐四步范式的另外两步（digest 重算对照
sidecar 关联、白名单核对）并读取 `uh_probe_result.json`（A10）。

---

## 10. 快速自查清单（写新生产者代码前过一遍）

```text
1. 我要写的对象在生命周期第几步？创建者是不是表里的那个组件？
2. 大 payload 是不是都换成了 ArtifactRef？有没有把 token 数组/日志正文内嵌？
3. dense / top_p=1.0 这类"缺席"场景，是不是用显式 not_applicable_* 声明的？
4. 失败/降级路径有没有 reason code 或 detail？（无理由的失败都会被拒收）
5. reward 缺失时是不是 null + scope=none？（绝不允许 0.0 或 NaN 顶替；
   有值时 binary_v1 下只有 1.0/0.0 两个合法取值）
6. 模型可见面的字符串（env、公开题面）有没有过 find_forbidden_marker？
7. 写完先 model_validate 自己的样例，再跑 inspect-rh2-artifact 看退出码。
```
