# S0-6 V4 报告：MoE 张量穿透 + 形态 A/B 评估（S0 最重要单一产出）

日期：2026-07-07。验证机与证据目录同 `v3_protocol_report.md`（单卡 RTX PRO 6000 Blackwell 96GB；`remote_s0_5_7_evidence/`）。

## 0. 结论先行

**V4 通过**：MoE 张量穿透在两条形态上都完成了动态验证——routing tape 两条都拿得到；top-p tape 两条都**不是**开箱即用，但缺口性质完全不同（B 有现成维护的 patch+镜像，A 是三端都缺的协议设计题）。

**推荐**：以**形态 B（SGLang + slime patch 镜像的原生 `/generate`）作为 MoE RL 训练主形态**，形态 A（verifiers 中心 + vLLM `/inference/v1/generate`）保留为协议基线与 dense/eval 路径；治理层维持中立 `TrajectoryProjection` 契约，使两条形态可切换。理由见第 6 节。

两条形态的定义（沿用执行计划 S0-6）：

| 形态 | 推理引擎与协议 | 天然消费端 |
| --- | --- | --- |
| A | vLLM 0.24.x `--tokens-only` 起 `/inference/v1/generate`，verifiers TrainClient 直连 | prime-rl（pyproject 锁 `vllm>=0.24.0`） |
| B | SGLang 原生 `/generate`（input_ids 进、meta_info 出），slime 风格请求 | slime（`custom_generate` / adapter → `Sample`） |

## 1. 证据底座（全部为真实端点动态验证，非源码推断）

| 证据文件 | 形态 | 内容 |
| --- | --- | --- |
| `trainclient_qwen3_4b_probe.json` | A | TrainClient 全链：token-in/out、logprobs 对齐、Trace token identity |
| `inspect_qwen3_30b_routing_payload.json` | A | 30B-A3B routing wire 形状（base64 `.npy`，`[20,48,8]` uint8） |
| `trace_commit_qwen3_30b_routing_shim_probe.json` | A | 薄 shim 后 `Trace.commit` 成功：`[21,48,8]`、token identity 保持 |
| `sglang_qwen3_30b_moe_generate_probe_with_routing.stdout.json` | B | 原生 `/generate`：output_ids + logprobs 对齐、routing tape `[20,48,8]` |
| `sglang_qwen3_30b_topp_probe.json` | B | **top-p 动态探针**（top_p=0.95，slime 风格请求 + 对照组） |

## 2. 维度一：token 保真

| 检查项 | 形态 A | 形态 B |
| --- | --- | --- |
| token-in（发 token ids 不发文本） | ✅ `token_ids` 请求体（TrainClient 强制） | ✅ `input_ids` 请求体 |
| token-out + 逐 token logprobs | ✅ `choices[0].token_ids` + `logprobs.content[*].logprob`，4B 8/8、30B 8/8 对齐 | ✅ `meta_info.output_token_logprobs`（`[logprob, token_id]` 对），8/8 与 16/16 对齐、全有限值 |
| 多轮 token identity / 漂移防护 | ✅ verifiers Trace 原生（commit 校验 + token drift fork，S0-2 契约 G1-G6 已固化） | ⚠️ 引擎层无此概念；slime 侧等价物是 `TrajectoryManager` 的 drift 三分类（CLEAN/REALIGN/FORK），但产物是训练 `Sample` 而非审计 Trace——若以 verifiers Trace 为事实源，需要在采集客户端层补 commit 逻辑 |
| renderer 守门（U-G） | ✅ `renderer_cls_name=Qwen3Renderer` 断言通过 | 同属客户端层职责，与引擎无关（B 下同样要做） |

小结：wire 层两条等价；**差异全部在客户端/轨迹簿记层**——A 把这层现成地放在 verifiers 里，B 需要 projection/adapter 承担（slime 已有成熟等价实现可参考）。

## 3. 维度二：MoE 张量（含 top-p 探针结果）

### 3.1 routing tape（routed_experts）

| | 形态 A（vLLM 0.24.0） | 形态 B（SGLang 0.5.9 stock） |
| --- | --- | --- |
| 服务端开关 | `--enable-return-routed-experts`（原生） | `--enable-return-routed-experts`（原生，`server_args.py:629`）＋请求侧 `return_routed_experts: true` |
| wire 形状 | base64 **`.npy` 字符串**（带 numpy 头），dtype uint8 | base64 **裸 int32** buffer（46080 字节 / 11520 元素 = 4 字节） |
| 解码后语义 | `[20,48,8]`＝(13 prompt−1+8 gen) × 48 层 × top-8 | 同一语义：`[20,48,8]`（13+8）、`[30,48,8]`（15+16），expert id 0..127 |
| 与 verifiers `RoutedExpertsPayload{data,shape,start}` 的距离 | 需薄 shim（已证明：commit 后 `[21,48,8]`、identity 保持） | 需同类 shim（int32→uint8 归一 + 补 shape/start） |

两引擎的行数规律一致（行数 = prompt−1+生成，末行由 verifiers 补齐规则处理），**S1 的 `TrajectoryProjection` 只需一个归一化转换点**（含 dtype 归一：uint8 存储足够，128 专家）。

### 3.2 top-p tape（本轮新增探针，top_p=0.95 防假阴性）

slime 的消费契约（`loss.py:35-47`）：`rollout_top_p != 1.0` 时**强制要求** `rollout_top_p_token_ids/offsets`，缺失直接 raise；生成端期望 SGLang `meta_info` 返回 `top_p_token_ids`+`top_p_token_offsets`（base64 int32，offsets 长度=生成数+1，`types.py:9-36`）。

| | 形态 A | 形态 B |
| --- | --- | --- |
| 引擎能否生成 | ❌ vLLM 0.24.0 安装树 grep 零命中 | ❌ stock SGLang 0.5.9 实测：top_p=0.95 + slime 风格 `custom_params={"return_top_p_token_ids": true}`，meta_info 13 个 key 无一含 `top_p`，请求被**静默忽略**（200，与对照组响应结构逐 key 一致） |
| 补齐路径 | 无现成方案：要自研 vLLM sampler 侧采集 + 扩展 verifiers wire（`ResponseTokens` 无此字段）+ 消费端（prime-rl 也零命中）——**三端缺口** | ✅ 有现成维护方案：slime `docker/patch/latest/sglang-top_p.patch`（929 行、17 个文件）+ 官方 docker 镜像自带；patch 后 `meta_info["top_p_token_ids"/"top_p_token_offsets"]` 即 slime 期望形状，零二次转换 |
| U-B 判定 | — | **确认**：routing 半边不需要 patch（stock 原生）；top-p 半边需要 slime patch/镜像 |
| 风险备注 | — | 静默失败模式危险：打错到 stock server 不报错，训练侧才炸——正式实现必须在启动时探针断言 tape 存在 |

附：top_p=0.95 下 routing tape 不受影响（`[30,48,8]` 正常返回），logprobs 16/16 对齐——top-p 截断与 routing/logprob 采集互不干扰。

## 4. 维度三：工程成本

| 成本项 | 形态 A | 形态 B |
| --- | --- | --- |
| 已固化的启动参数 | Blackwell 保守组合已实测（`--enforce-eager`、`VLLM_USE_FLASHINFER_SAMPLER=0`、`--moe-backend triton`、`--tokens-only`，见 v3 报告第 1 节） | stock pip 安装对 CUDA developer toolkit 路径极敏感（本轮靠借用 vLLM venv 的 cu13 toolkit 跑通）；**结论：必须用固定容器镜像**——而 slime 官方镜像恰好同时解决"环境固化"和"top-p patch"两件事 |
| routing 接通 | 薄 shim（几十行、纯格式转换，已证明） | 同级 shim（归一化点共享） |
| top-p 接通 | 三端自研 + 说服/维护 verifiers wire 扩展（上游不受控） | 用现成镜像即得；代价是绑定 slime 的 sglang fork 节奏 |
| 轨迹簿记 | 零成本（verifiers Trace 原生） | projection/adapter 工作（S1 `TrajectoryProjection` 计划内；slime `TrajectoryManager`/adapter 可作参考实现） |
| 成本性质总结 | 缺口是**跨仓库协议设计**（风险高、周期不可控） | 缺口是**运维固化 + 计划内适配层**（风险低、可预算） |

## 5. 维度四：治理接入点（都经 `TrajectoryProjection` 中立契约）

两条形态在治理层的约定相同：RepoHarness 拥有任务/评分/资格事实，训练后端只消费投影。差异在**事实采集点**与**谁天然持有治理字段**：

- **形态 A**：治理事实（分支拓扑、sampled_mask、errors、rewards、token identity）在 verifiers Trace 里是一等公民，`TrajectoryProjection` 从 Trace 出发做投影——routing shim 也放在这一层（S0-5/6 决策已定）。接入点单一、清晰。
- **形态 B**：`Sample` 是训练容器不是审计 artifact（slime 侧共识，见 `reference/slime/CLAUDE.md` 第 5/19 节）；tape 类张量在 `/generate` 响应的 meta_info 出现，**采集点必须放在调用 SGLang 的客户端层**（无论该客户端是 verifiers TrainClient 式的还是 slime adapter 式的），再由 projection 层把治理事实与张量引用一起保留。若采集点放进训练后端 adapter，治理事实会丢——这正是"shim 归 projection 层持有"决策要防的事。
- 共同要求：projection 层持有三件归一化事实——routing tape（dtype/形状/末行补齐规则）、top-p tape（ids+offsets 校验，offsets 长度=生成数+1）、token identity 状态。两条形态在这一层收敛，**切换形态不改治理契约**。

## 6. 推荐结论与理由

**主推形态 B 作为 30B-A3B（MoE）RL 训练链路的主形态；形态 A 保留为协议基线、dense 模型与 eval/调试路径。**

理由（按证据强度排序）：

1. **top-p tape 是硬分水岭**：若训练后端是 slime 且 `rollout_top_p != 1.0`（训练设计当前倾向 0.95 类值），tape 是 `loss.py:47` 的硬性要求。B 侧是"拉一个现成镜像"，A 侧是"改三个仓库（其一不受我们控制）"。本轮探针把这从推测变成了实测事实。
2. **B 的两个已知缺口共享同一个解**：CUDA 工具链敏感性与 top-p patch 都由"固定使用 slime 官方 docker 镜像"一步解决；A 的缺口没有等价的一步解。
3. **token 保真与治理不受形态选择损害**：B 缺的轨迹簿记层恰好是 S1 计划内的 `TrajectoryProjection`/采集客户端工作，且有 slime `TrajectoryManager` 作参考实现；wire 层证据显示两引擎 token/logprob/routing 语义一致，projection 归一化点唯一。
4. **不押死单边**：A 的全链已验证可用（V3 通过），Blackwell 参数已固化，作为协议对照与回退路径的持有成本接近零。若训练设计最终定为 `top_p=1.0`（tape 需求消失）或主后端定为 prime-rl，再把主形态切回 A，治理契约不变。

**随推荐落下的硬性实施要求**（防止推荐被打折执行）：

- B 的正式实现必须 pin slime 镜像（含 sglang patch）版本，并在服务启动后跑一次 top_p<1.0 探针断言 `meta_info` 含 `top_p_token_ids`（防 stock server 静默失败模式）。
- routing/top-p 两类 tape 的解码与校验只允许实现一次，落在 `TrajectoryProjection` 中立层。
- 保留 `remote_s0_5_7_evidence/` 探针脚本形态作为形态切换时的回归探针。

## 7. 本轮新增/更新的未知

- **U-H（新）**：slime patch 版 SGLang 在本机 Blackwell 环境的实际可用性未验证（本轮只验证了 stock 0.5.9 + patch 静态存在性；patch 基于的 sglang 版本与 0.5.9 的兼容性、镜像在 sm_120 上的行为，留 S1 接入时用同一探针关闭）。
- U-C 训练半边、U-D（SWE 镜像）不变，见 implementation-notes。
