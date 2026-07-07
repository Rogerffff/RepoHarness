# S1-7a bring-up 报告：远程 GPU 批处理（T1 递延回归 + T2 debug training transport step）

- 日期：2026-07-08（远程机时区 UTC）
- 远程机：vast.ai 单卡 RTX PRO 6000 Blackwell Workstation Edition 96GB（sm_120），
  Ubuntu VM，docker 29.x（classic overlay2 镜像存储），/root/claude-code-verl-stage0h
- slime pin 镜像：`slimerl/slime@sha256:a7317182c71d35712ee4edc86a5d1c313dc969efdf0026d339673299c186ea75`
  （S1-0 冻结 digest 逐字节一致；镜像内 slime commit `474861aa`、sglang 0.5.13、
  Megatron-LM 在 /root/Megatron-LM）
- 本报告的机器可读证据在 `s1/7a_artifacts/`（key 扫描后回传）。

## 0. 环境同步与测试基线（步骤 0）

- rsync 增量同步 rh2/（排除 .venv/__pycache__）与 docs/.../repo_harness_rh2_workstreams/ 到远端。
- 远端 `uv sync --group swe`：swebench 4.1.0 装入 rh2/.venv（Python 3.12.13）。
- **首跑基线**：`uv run pytest -q` = **554 passed**；`uv run pytest -m docker -v` = **15 passed**
  （与本机前置修复后的基线逐数一致）。
- 本批三处库层修复（§1.2 导出排除 +1 测试、§2.3 假设 3/7 修复 +5 测试、§2.7 N-4
  契约座标 ±0）后，收口态本机与远端全套 **560 passed** + docker **15 passed**。
- **RepoDigests 行为差异实测（本机 containerd vs 远端 classic 存储）**：远端 overlay2
  存储下本地构建镜像 `rh2-s14-grading-fixture:v1` 的 RepoDigests 为空 `[]`
  （`docker image inspect -f '{{.RepoDigests}}'` 实测）——与本机 containerd 存储
  （本地构建镜像也带 RepoDigests）相反。也就是说"缺 RepoDigests 且无豁免即拒"
  分支在远端是**真实可达**的，`test_rollout_image_digest_fixture_image_real`
  在两种 daemon 上分别落进两种拒绝形态且都通过（前置修复时预告的行为差异，
  实测证实，无需改代码）。

## 1. T1 递延回归批处理

### 1.1 S1-2 薄壳等价：2 题 verifiers 绑定 smoke（deepseek）

key 经 ssh stdin 注入进程环境（不落盘/不回显/不进 argv）；`s0_swe_smoke.py` 原样执行；
dump 落盘前走 scrub + assert 双重剔除，回传前再做 `sk-` 扫描（0 命中）。

| instance | 本次（远端实跑） | S0-7 记录 | 判定 |
| --- | --- | --- | --- |
| django__django-11099 | RESOLVED_FULL / reward 1.0 / apply_ok / digest_match，12 turns，wall 44.7s | RESOLVED_FULL / 1.0 | 一致（链路 + 结论态） |
| psf__requests-2931 | RESOLVED_NO / reward 0.0 / apply_ok / digest_match，30 turns（max_turns 停），wall 104.9s | RESOLVED_NO / 0.0 | 一致（P2P 回归态复现） |

判据按 envpack_freeze_v1 §5：物化/评分链路跑通 + parser 结论与库层一致；reward 数值
受 deepseek 采样影响本不作硬判据，实跑两题连 resolution 态都与 S0-7 相同。
dump 存 `7a_artifacts/django__django-11099.json` / `psf__requests-2931.json`。

### 1.2 S1-4 评分回归：8 题冻结集经 GradingManager（image_embedded）

方法：每题起 workspace 容器（官方镜像）→ 应用 S0-7 落盘的模型 agent_diff →
`SWEGradingManager.grade` 全链（导出→hygiene→fresh 容器 clean checkout→重放→官方
测试→官方 parser）→ 逐题对照 S0-7 的 resolution/apply_ok/reward。脚本
`rh2/experiments/s1_7a_t1_regression.py`。

**第一跑 7/8 一致，抓出一个真实导出层回归（这正是递延回归的目的）**：

- `psf__requests-1142`：S0-7 = RESOLVED_FULL/1.0，第一跑 = unresolved/patch_apply_failed。
- 根因：该官方镜像 /testbed **base 状态自带 872KB 未跟踪构建残留**（`build/lib/**`），
  S1-7a 前置修复的 `git add -N .`（codex#3，为了不漏 agent 新建文件）把这些**非 agent
  产物**也卷进导出 patch；clean checkout 上同样存在这些未跟踪文件，重放
  `git apply` 报 "already exists in working directory" 整体失败。S0-7 直评不经
  add -N 导出通道所以未命中。
- 修复（fail-closed 语义保持）：物化侧在 harness 动工前存基线未跟踪清单
  （`git ls-files --others --exclude-standard`，与 add -N 取数集合一致）到容器
  `/rh2/base_untracked.txt`；导出脚本对清单路径逐条 `:(exclude,literal)`。清单
  缺席时行为与旧版逐字节一致（fixture 兼容）。改动：`grading/manager.py`
  （`BASE_UNTRACKED_MANIFEST` / `BASE_UNTRACKED_SNAPSHOT_SCRIPT` /
  `build_export_patch_script`）+ `adapters/slime/generate.py` 物化步骤 +
  回归脚本；新增单测 `test_export_excludes_preexisting_untracked_baseline`。
  已知边界（记录进代码注释）：agent 若**修改**基线未跟踪文件，该改动被排除出
  patch——这些文件本就不在被评分的源码树内。
- **修复后重跑：8/8 全部一致**（7 resolved + 1 unresolved，与 S0-7 逐题相同）。
  两跑报告都保留：`t1_regression_report.json`（修复后）/
  `t1_regression_report_prefix_run1.json`（第一跑，含失败证据）。

### 1.3 镜像 digest 比对实机验证（前置修复 codex#1 的真实第一跑）

8 题官方镜像 `docker image inspect` 的 RepoDigests 逐题对照 frozen_v1 冻结
`image_manifest_digest`：**8/8 digest_check_ok=true**（同一判定函数
`materialize.evaluate_image_digest`，与运行期 rollout/评分容器比对共用）。
T2 训练 rollout 的运行期比对同样走真了（32 个 rollout 容器全部经过启动后
digest 校验，见 §2）。

### 1.4 TESTS_ERROR / apply_ok=false 频率统计（codex#4）

| 来源 | 评分次数 | verdict.apply_ok=false（坏码族） | test_log_parse_failed | infra_failure |
| --- | --- | --- | --- | --- |
| T1 8 题回归（修复后） | 8 | 0 | 0 | 0 |
| T1 2 题 smoke | 2 | 0 | 0 | 0 |
| T2 run6/7/8 评分合计 | 63（10+21+32） | 仅注入 2 | 仅注入 2（run7/run8 各 1 次人为注入） | 0 |

**自然发生率 0/73**：codex#4 关心的"TESTS_ERROR/apply_ok=false 被保守归 infra"
在本批 73 次真实评分中零自然出现（出现的 2 次全部是本报告的人为注入且行为
正确）。维持保守归类，无数据支撑拆分；S2 大规模 ingestion 时继续统计。

## 2. T2 debug training transport step（A1/A2/A3）

### 2.1 配置（执行计划 §S1-7 条款逐项）

- 模型：Qwen/Qwen3-4B（dense），HF 权重经 `tools/convert_hf_to_torch_dist.py`
  转 torch_dist（7.5G）作 `--ref-load`。
- 训练栈：slime pin 镜像容器（`--net host --gpus all` + docker.sock 挂载），
  Ray 单节点单卡 colocate；SGLang serving 沿用 S1-0 同卡验证过的三件套
  `--sglang-attention-backend triton --sglang-sampling-backend pytorch
  --sglang-disable-cuda-graph`，mem-fraction 0.6。
- 数据：8 题冻结集 JSONL（metadata.instance_id 反查冻结 BundlePair，防漂移
  校验开启）× **n=4**（E2 生产配置）= 32 rollout；`--global-batch-size 32`
  ⇒ 恰好 **1 个 optimizer step**；`--num-rollout 1`。
- 采样：**top_p=0.95**、temperature 1.0、per-turn max_new_tokens 2048、
  multi-turn 上下文预算 32768。
- E2 flags：`--disable-grpo-std-normalization --eps-clip 0.2 --eps-clip-high 0.28`
  （grpo 优势估计，kl_loss_coef 0）。
- 接线：`--custom-generate-function-path s1_7a_bringup.glue.generate` →
  `rh2_custom_generate`（`args.rh2_orchestrator` 显式挂点）；capture 接线 =
  替换模块级 `slime.agent.adapters.common.call_sglang_generate` + 包装
  `TrajectoryManager.record_turn`（flush 后提交，见假设 1/3 核对）。
- harness：**真实 slime ClaudeCodeHarness**（Claude Code CLI 2.1.202，
  linux-x64 平台包原生二进制直装进 rollout 容器；沙箱 = rh2 物化的官方镜像
  容器经 `DockerSandbox` 适配 slime Sandbox 协议）；agent 时间预算 600s、
  每会话 25 轮封顶（bring-up 范围控制）；`--disallowedTools Task WebFetch
  WebSearch`（禁 subagent 派发，压制多叶链——假设 2 的默认单叶推导范围）。
- infra 注入：`RH2_INJECT_INFRA_INSTANCE=django__django-11133` 的第一条
  rollout 评分脚本被换成产不出官方标记的噪声脚本（gate 拒绝路径实证）。

### 2.2 startup_checks 真实执行（A2/U-G/U-H，`startup_evidence.json`）

探针走生产同一 wire 路径（替换后的 call_sglang_generate + 真实 router）：

```json
{"renderer_cls_name": "Qwen3Renderer", "prompt_token_count": 9,
 "generated_token_count": 16, "logprobs_entries": 16,
 "top_p_token_offsets_len": 17, "top_p_kept_token_count": 28,
 "engine_weight_version": "1"}
```

- U-G：renderer 显式 `Qwen3RendererConfig` 构造 + 类名断言通过（本地路径
  加载必须显式配置，否则静默回落 DefaultRenderer——v2 报告的规避写法首次在
  训练容器内实跑）。
- U-H：top-p tape 请求了就必须在场——offsets 长度 17 == 生成 16+1，首尾
  合法；dense 声明下 routing tape 未请求且未出现（A2：dense 只是没有 routing）。
- 引擎 weight_version="1"（slime update_weights 后的真实版本号）成为
  config.policy_version 的事实源（假设 4）。

### 2.3 运行序列与真实 optimizer step（A1）

四次全栈运行（每次都是 `--ref-load` 原始权重冷启，绝无 checkpoint 复用）：

| run | 结果 | 修复产出 |
| --- | --- | --- |
| run4/5 | 启动期失败 | 服务单例锁 import 期创建（并发首调多实例抢端口）；探针改走生产 wire 路径（router 对手搓体 400：`rid` 必填 + transformers `apply_chat_template` 新版默认 `return_dict=True` 会把键名字符串当 input_ids 发出） |
| run6 | 32/32 rollout 完成、10 条交付、**训练 step 在 top-p replay loss 路径 OOM** | 假设 3 证伪（REALIGN 整轮掉落 3vs4）→ token 锚定回填；django 8/8 灭于 `ensure_agent_user` 60s 超时 → 预跑修复；multi-leaf 10 命中 fail-closed；`--log-probs-chunk-size 1024` |
| run7 | **Job SUCCEEDED：真实 optimizer step @ iteration 0 + checkpoint 53GB 保存**；32/32 rollout，21 评分（20 unresolved + 1 注入 infra），27 条样本交付进 train batch | 契约 N-4 座标错误曝光（多轮轨迹全被误拒 11 条）→ 契约修复 |
| run8 | 契约修复后的收口验证跑（数字见 §2.7） | — |

run7 step 0 指标：`train/loss=0.0, pg_loss=0.0, entropy_loss=0.1079, pg_clipfrac=0.0, ppo_kl=0.0`
——8 组奖励全 0（Qwen3-4B 无解题）+ GRPO 组内零方差 ⇒ 零优势，诚实结果；
top-p replay 的 loss 消费路径真实执行（run6 恰在该路径 OOM 反证其运行）。

**checkpoint 用后即弃（A1 删除证据，`7a_artifacts/ckpt_discard_run7.log`）**：
删除前 `ls -la`（iter_0000000/ 含 28GB distcp 分片 + latest_checkpointed_iteration.txt）
+ `du -sh` = 53G；`rm -rf` 后 `ls` = "No such file or directory"。run8 启动在删除
**之后**，`--load` 目录为空、从 `--ref-load` 原始 torch_dist 冷启（日志可证）。
`rh2_formal_training_allowed` 维持 false。

### 2.4 A2 top-p tape 全链（生产→capture→回填→投影→消费）逐位实证

`verify_transport.py` 把**训练侧** rollout dump（`--save-debug-rollout-data` 的
rollout_0.pt，即 trainer 实际吃进的数据）与**治理侧** sidecar（投影 + capture
tape 字节流）逐位对账，run7 交付 **27/27 全过**（`transport_verify.json`）：

1. token 逐位：dump tokens 的 mask=1 位 == capture 原始 output_ids（按入训轮序拼接）；
2. rollout logprob 逐位：dump rollout_log_probs == capture float64 tape；
3. loss mask 逐位：投影 loss_mask_spans 展开 == dump loss_mask（H4 语义传导无损）；
4. top-p tape 逐位：投影 SamplingMaskRef 指向的 artifact 字节流 == dump
   rollout_top_p_token_ids/offsets，且 len(offsets)==response_length+1。

覆盖形态：单轮 ×18、多轮（工具上下文夹层 + 零宽 pad）×9、fan-out 多叶（同一
trajectory 2~4 条 dump 样本按 token 身份各自对上自己的分支）。消费端：megatron
loss 的 top-p replay 分支（`rollout_top_p!=1` 强制断言 + masked_fill）真实执行。

**dense 无 routing 的 not_applicable 实证**：27/27 投影
`routing.alignment="not_applicable_dense_model"` 显式在场（禁止静默省略字段），
探针侧 dense 声明下未请求也未出现 routed_experts（请求了才必须在场的 U-H 对偶）。

### 2.5 gate 拒绝路径真实触发 + GroupRepairSignal 透传（P4）

注入：`RH2_INJECT_INFRA_INSTANCE=django__django-11133` 的第一条到达评分的
rollout，其 eval 脚本被换成产不出官方标记的噪声（marker 文件保证恰好一次，
`infra_injection_fired.marker` 记录中招 trajectory）。实测链路：官方 parser
解析失败 → `GradingReport(outcome=failed_to_grade, failure_category=
test_log_parse_failed, reward=None)`（P4 红线：infra 绝不伪装 reward=0）→
gate `reward_scope` + `clean_grading` 双维失败 → `EligibilityReport
(audit_only_or_rejected)` → `GroupRepairSignal(degraded=true, failed_dimensions=
[reward_scope, clean_grading])` 经 sink 在返回前透传 → 样本以 slime abort 形状
剔除（loss_mask 清零仍占位，batch 计数不破）。**同组其余 3 条正常交付——
"degraded 1 / 可交付 3" 的组修复账目与 S1-5 定案完全一致**（signals jsonl）。

### 2.6 计时埋点（F5 五段 + 峰值内存，run7 21 次评分）

| 段 | mean | max |
| --- | --- | --- |
| image_pull_seconds | 0.0（8 镜像预拉取命中） | 0.0 |
| env_reset_seconds | 0.79 | 1.10 |
| prep_seconds | 0.92 | 3.73 |
| test_seconds | 6.10 | ~15 |
| total_grading_seconds | ~8 | ~16 |
| queue_wait_seconds | 0.0（并发 4 未打满，无反压事件） | 0.0 |

容器峰值内存 max 156.5MB（cgroup v2 memory.peak）；rollout 全链 wall mean
~118s / max ~317s（含 CC 安装 + agent 600s 预算内实际用时 + 评分）。

### 2.7 run8/run9（契约修复后收口跑）

**run8（rollout 面满分）**：32/32 rollout **零故障记录**（假设 3 命中 0、多叶拒绝 0、
N-4 误拒 0——三项修复在全量上验证），**61 条样本返回 = 60 交付 + 1 注入降级**
（fan-out 多叶交付真实发生）；评分 32 次 = **5 resolved（reward 1.0，Qwen3-4B
真实解题：django-11099/11133 各 1 + 16139 ×3）** + 26 unresolved + 1 注入 infra。
`verify_transport.py` 对 run8 训练 dump **60/60 全部逐位通过**。训练 step 在
microbatch 52/60 的 lm-head fp32 logits 转换上 OOM（单样本上下文逼近 32768 cap，
151936 vocab × ~30k token × 4B ≈ 17GB > 剩余 14GB）——单卡容量边界，非链路问题；
run9 以 `RH2_MAX_CONTEXT_LEN=20480` 收口完整 step（结果见下）。

**假设 3 的真实驱动源（run8 数据定位）**：Claude Code 按 Anthropic 协议在后续
请求中**剥离历史 thinking 块**，Qwen3 thinking 输出的重渲染必然 token 漂移 →
TrajectoryManager REALIGN 把上一轮**整轮**降为 mask=0 上下文。实测每条 CC 轨迹
的第 1 轮（t0）都被掉落（run8 全部 60 条交付分支的 capture 回链均不含 t0）。
token 锚定回填正确处理该形态（60/60 逐位过）。

**S1-8 导出器边界（喂 S1-9 的真实发现）**：`offline_export` 的线性追加式 token
重建假设 "分支首轮 prompt == 分支 prompt"，在 t0 掉落的真实 CC 形态下**全部
拒绝**（`token_reconstruction_mismatch`，fail-closed 正确工作、绝不静默导出
错位 token）——但这意味着当前导出器**导不出任何真实 CC（thinking 模型）轨迹**。
升级路径（S1-9/S2）：重建器改从叶链自身 tokens + used-refs 锚定（与
verify_transport 同法）或引入树侧前缀血缘。**导出记录样本**改由 run6 的
单轮交付轨迹产出：`texp_16f847ff…`（psf__requests-2931，token 重建 + 逐轮
前缀校验 + digest 全过，`7a_artifacts/export_sample/`）。

**run9（RH2_MAX_CONTEXT_LEN=20480，收口跑，Job SUCCEEDED）**：32 rollout →
66 样本 = **65 交付 + 1 注入降级**；评分 31 次 = 1 resolved + 29 unresolved +
1 注入 infra；1 条 `adapter_session_empty` 诚实 abort（该会话全部轮次被
REALIGN 掉落/上下文封顶，无叶链可产）。`verify_transport` **65/65 逐位通过**。
**完整 optimizer step（组间奖励有方差）**：

```text
train/loss = train/pg_loss = 0.01073   （非零策略梯度）
train/grad_norm = 0.2935
train/train_rollout_logprob_abs_diff = 0.0115（megatron 重算 vs rollout 引擎
    逐 token logprob 平均绝对差——训练侧与采样侧的一致性旁证）
train/pg_clipfrac = 0.0, ppo_kl = 0.0, entropy = 0.1446
```

checkpoint（53GB，iter_0000000）保存后随即删除留证
（`7a_artifacts/ckpt_discard_run9.log`）。对比 run7（奖励全 0 ⇒ loss 恒 0），
run9 的非零 pg_loss 证明 reward → advantage → clipped surrogate → 梯度的
训练消费面真实走通。

## 3. 10 条 mock 差异假设逐条核对（8 符合 + 2 证伪已修）

| # | 假设（S1-6 清单） | 实机证据 | 结论 |
| --- | --- | --- | --- |
| 1 | capture 接线点 = 替换 `call_sglang_generate`；tape flag 键名待核 | monkeypatch 生效（模块名解析）；flag 位置实测 = `sampling_params.custom_params.return_top_p_token_ids` + 请求体顶层 `return_routed_experts`（与 slime GenerateState 自有注入/S1-0 探针同形）；**提交时点必须挂 `record_turn`**（响应 flush 后，flush 失败的轮不入轨迹也不入捕获） | **符合**（键名/时点补充确认） |
| 2 | 树侧事实无现成 API，多叶不注入提取器即 fail-closed | 证实无 API；真实 CC 产生 FORK 多叶（run6 10/32 命中拒绝路径）；bring-up 以"候选=全部轮 + token 锚定裁决"放行（库层默认不变） | **符合**（多叶正式化递延 S1-9/S2） |
| 3 | mask=1 段与轮次一一对应且等长 | **证伪**：REALIGN 整轮掉落（3 段 vs 4 轮，django-16139）+ 相邻轮平铺两形态实测 | **证伪→已修**（token 同一性锚定回填 + 3 单测；修后 32 rollout 命中 0） |
| 4 | weight_versions 填充机制待核 | 引擎每轮 meta_info.`weight_version`（update_weights 后 = "1"）；119 轮引擎值 vs 28 条样本回填值 0 错位；probe 值作 config.policy_version 事实源 | **符合**（事实源=引擎 meta_info） |
| 5 | reward 回写时点：finish(0.0) 后回写不被覆盖 | 镜像内 `generate_and_rm` 仅在 `sample.reward is None` 时调 rm（源码 + 实跑：dump 中评分 reward 原样在场） | **符合** |
| 6 | truncated 只进 metadata、status 恒 COMPLETED | 实测 metadata.truncated True/False 都出现（per-turn length 截断叶链 = True），status 恒 completed | **符合** |
| 7 | abort/eval 占位形状逐字段照抄例程即可 | **证伪**（top-p 配置下）：`rollout_top_p!=1` 时 slime 对**每条**样本断言 top-p 双字段（含 remove_sample） | **证伪→已修**（top_p<1 补零宽 tape；top_p=1 保持原形；2 单测） |
| 8 | sid 唯一性、重试须换 sid | 成立 + 新事实：slime 在 custom_generate 前就按样本 `session_id=uuid4()`（generate_and_rm_group:311），编排兜底路径不触发 | **符合** |
| 9 | mock 响应键名与真实 wire 一致 | 全部命中；真实响应多带 weight_version/cached_tokens/reasoning_tokens/e2e_latency 等，hook 只取所需、raw meta 全量进 digest | **符合** |
| 10 | group_index = 组编号、同组共享 | 源码（data_source:112）+ 真实 batch（8 组 × 4 条、组内 instance 唯一、index 全局唯一）双证；降级组账目 1/3 正确 | **符合** |

首日排它两条（F1②）：假设 3 证伪已修、假设 10 证实——均闭环。

## 4. 结论与递延

1. **S1-7 7a 验收条款达成**：custom_generate→capture→回填→projection→gate→
   trainer 数据链路在真实栈（slime pin 容器 + SGLang patch 引擎 + Claude Code
   2.1.202 + 官方 SWE 镜像沙箱 + GradingManager）上闭环；**2 个真实 optimizer
   step**（run7 零方差 loss=0 + run9 有方差 pg_loss=0.0107/grad_norm=0.294），
   两个 checkpoint 均用后即弃留证；loss mask/logprob/token/top-p tape 逐位
   核对 run7 27/27 + run8 60/60 + run9 65/65；gate 拒绝路径与 GroupRepairSignal
   透传实证（run7/8/9 各一次注入全部走正确链路）；dense 的 routing
   not_applicable 显式标注全量在场。**A1 语义**：本步只证数据传输链路，
   checkpoint 已删除、不作任何后续初始权重，`rh2_formal_training_allowed=false`。
2. **A3 递延措辞维持**：30B 全要素训练 step、多卡训练侧、routing tape 训练
   消费（dense run 未关闭）、U-C —— 全部按 C3 进 S1-9 acceptance summary
   的递延清单。
3. **本批落库的真实修复**（本机+远端全套 560 passed + docker 15）：
   requests-1142 基线未跟踪导出排除、token 锚定回填、top-p abort 占位形状、
   N-4 契约座标、（bring-up 层）ensure_agent_user 预跑 / CC 平台包直装 /
   探针走生产 wire 路径。
4. **喂 S1-9/S2 的开放项**：多叶链回链正式化（bring-up 的 token 锚定裁决是否
   升级为库层默认）；slime `ensure_agent_user` 60s 超时上游修复建议；
   GroupSignal 跨 n 条聚合与动态采样表示（S1-6 递延项维持）；TESTS_ERROR
   自然发生率为 0（10+21 次评分），codex#4 的"拆分解析器失败 vs 合法失败"
   暂无数据支撑，维持保守 infra 归类、继续在 S2 统计。
5. **TESTS_ERROR/apply_ok=false 频率（codex#4 收口数字）**：T1 10 次评分 0 次；
   T2 全部评分自然 0 次 + 人为注入 1 次（注入样本走 test_log_parse_failed →
   failed_to_grade → gate 降级，全链行为正确）。
