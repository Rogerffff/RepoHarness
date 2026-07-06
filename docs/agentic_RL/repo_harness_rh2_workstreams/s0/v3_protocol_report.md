# S0-5 V3 报告：token 协议链路（vLLM `/inference/v1/generate` 直连全链）

日期：2026-07-07。验证机：单卡 NVIDIA RTX PRO 6000 Blackwell Workstation Edition（96GB，sm_120），Ubuntu 22.04，Python 3.12.13。证据目录：`remote_s0_5_7_evidence/`。

## 0. 判定结论

**V3 通过**：形态 A 的推理侧路径存在——vLLM 0.24.0 + verifiers `TrainClient` + Qwen3Renderer 的直连全链在真实端点上做到了 token-in/token-out、逐 token logprobs 对齐、Trace token identity 成立。MoE routing payload 能拿到但**不是零 shim 可用**（wire 形状差异见第 4 节，薄 shim 已用验证脚本证明可行）。

| 判定项 | 结果 | 证据 |
| --- | --- | --- |
| U-A：vLLM 0.24.x 在租机环境可安装可起服 | 消除（0.24.0 成功，未需更新版本） | `/workspace/s0_vllm024_install.log`、`implementation-notes.md` S0-5 条目 |
| `vllm.entrypoints.serve.disagg` 体系 / `/inference/v1/generate` 路由 | 存在且可用（`--tokens-only` 起服） | `trainclient_qwen3_4b_probe.json` |
| TrainClient 全链 token 保真（Qwen3-4B，dense） | 通过 | 同上 |
| 30B-A3B（MoE）重复验证 + routing payload | 通过（token/logprobs 对齐；routing 需 shim） | `inspect_qwen3_30b_routing_payload.json` |
| routing wire 薄 shim 可行性 | 已证明（commit 后形状与 token identity 均正确） | `trace_commit_qwen3_30b_routing_shim_probe.json` |

## 1. Blackwell 上的稳定参数组合（U-A 的实质内容）

vLLM 0.24.0 在这张 Blackwell 卡上**默认参数不可用**：Qwen3-4B 默认启动卡在 CUDA graph 捕获；改 eager 后 FlashInfer sampler 与 CUDA header 不匹配；Qwen3-30B-A3B 默认 MoE 后端走 FlashInfer CUTLASS 编译失败。实测稳定组合（后续 runbook 应把它当默认而不是当补丁）：

```bash
# 环境变量
VLLM_USE_FLASHINFER_SAMPLER=0
# CUDA 13 toolkit 路径指向 vllm venv 内的 nvidia/cu13（该机无系统级 CUDA 开发栈）
CUDA_HOME=/workspace/s0_inference_envs/vllm024/lib/python3.12/site-packages/nvidia/cu13

# 30B-A3B 实际启动命令（4B 相同但不需要 --moe-backend）
vllm serve Qwen/Qwen3-30B-A3B \
  --tokens-only \            # 没有它就没有 /inference/v1/generate
  --dtype bfloat16 --max-model-len 4096 --gpu-memory-utilization 0.92 \
  --max-logprobs 5 \
  --enforce-eager \          # 绕开 CUDA graph 捕获失败
  --enable-return-routed-experts \
  --moe-backend triton       # 绕开 FlashInfer CUTLASS MoE 编译失败（仅 MoE 模型需要）
```

显存参考：30B-A3B bf16 单卡加载后约 60GB 量级（96GB 卡余量充足，无需量化），喂给 U-C 推理侧结论。

## 2. TrainClient 全链结果

链路：verifiers `TrainClient`（renderer 渲染 prompt ids）→ POST `/inference/v1/generate`（token-in）→ 响应解析 token ids + logprobs → `Trace.commit`（token identity 校验）。

Qwen3-4B（`trainclient_qwen3_4b_probe.json`）：

| 检查项 | 值 |
| --- | --- |
| renderer 守门（U-G 防线：断言拿到的是 `Qwen3Renderer` 而非 DefaultRenderer） | 通过（`renderer_cls_name=Qwen3Renderer`） |
| prompt/completion token 数 | 13 / 8 |
| completion logprobs | 8 条，与 completion_ids 逐位对应（如首 token 151667=`<think>` logprob≈-1.5e-05） |
| Trace token identity（分支拼接 == prompt_ids + completion_ids） | 通过（`trace_token_identity=true`，`sampled_true_count=8`） |
| 时延 | 0.317s（max_tokens=8） |

Qwen3-30B-A3B（`inspect_qwen3_30b_routing_payload.json`）：同链路重复通过——prompt 13 / completion 8、`completion_logprob_count=8`、renderer 守门通过，且响应扩展字段带回了 MoE routing payload（见第 4 节）。

## 3. 端点与 logprobs 的 wire 形状（contract_baseline 发现 5/6 的动态确认）

这两条是 S0-2 静态契约里最容易踩坑的形状约定，S0-5 在真实端点上都得到了确认，**任何 shim（C4 的 SGLang 转译层）必须按这个形状实现**：

1. **端点挂在服务根，不在 `/v1` 前缀下**（`contract_baseline.md` 发现 5）：`renderers.client.generate` 用 `base_url.rstrip("/").removesuffix("/v1")` 拼出 `POST {root}/inference/v1/generate`；请求前还会 `GET /v1/models` 预检 `max_model_len`（拿不到则静默禁用预检）。shim 若只实现 `/v1/...` 路由会 404。请求体是 `{"model", "token_ids", "sampling_params"}`，不含文本 messages；`sampling_params` 中 `stop_token_ids`（取自 renderer）与 `logprobs=1` 被强制覆写。
2. **logprobs 的 wire 形状是 ChatCompletionLogProbs 展平形状**（发现 6）：`choices[0].token_ids` → `completion_ids`；`choices[0].logprobs.content[*].logprob` → `completion_logprobs`，不是裸浮点数组。本轮 4B 与 30B 的响应都按此形状解析成功且长度逐 token 对齐。

## 4. vLLM routing wire 与 verifiers 期望的差异 + 薄 shim 可行性证明

**差异**（这是"V3 通过"里唯一带星号的地方）：

| 侧 | routing 的形状 |
| --- | --- |
| vLLM 0.24.0 实际返回 | base64 编码的 **`.npy` 文件字符串**（含 numpy 头），解码后 `[20, 48, 8]` uint8（20 = prompt 13 − 1 + completion 8；48 层 × top-8 专家） |
| verifiers 期望（`verifiers/types.py:201-205` `RoutedExpertsPayload`） | TypedDict `{data: <base64 的裸 uint8 buffer，无 npy 头>, shape: list[int], start: int}`；`graph.py:_attribute_routed_experts` 用 `binascii.a2b_base64(payload["data"])` + `np.frombuffer(...).reshape(shape)` 解码，再按节点切片归属 |

**薄 shim 证明**（`trace_commit_qwen3_30b_routing_shim_probe.json`）：验证脚本把 base64-`.npy` 字符串解出 ndarray，重打包成 `{data: b64(raw_bytes), shape: [20,48,8], start: 0}` 后走真实 `Trace.commit`：

- `token_identity=true`（shim 不破坏 token 保真）；
- `branch_routed_experts_shape=[21,48,8]`、dtype uint8——21 = 13+8 全分支 token 数。20 行原始 tape 变 21 行是 verifiers 自身的规范行为：引擎不对最后一个生成 token 做 forward，`_attribute_routed_experts` 检测到 `end == needed == arr.shape[0]+1` 时复制末行补齐（`graph.py:419-424`），不是 shim 的副作用。

**结论**：转换是纯格式层的（解 npy 头 → 重编码 + 补 `shape/start` 元数据），几十行代码量级，无数值变换。归属决策：该 shim 进入 S1 的中立 `TrajectoryProjection` 适配层持有，不散落在训练后端 adapter 中（已记入 implementation-notes S0-5/6 决策条目）。

## 5. 残余与边界（诚实记录）

- **top-p tape 不在 V3 范围内但影响形态判断**：verifiers 的 `ResponseTokens` wire（`types.py:208-224`）只有 `prompt_ids/prompt_mask/completion_ids/completion_mask/completion_logprobs/routed_experts/...`，**没有 top-p 候选集字段**；且远程 vLLM 0.24.0 安装树与本地 `reference/prime-rl` grep `top_p_token_ids|return_top_p` 均零命中。即形态 A 若要支持 slime 式 top-p replay，是引擎、wire 契约、消费端三端都要新增的缺口。详见 `topology_ab_report.md` 维度二。
- C4 的 SGLang→`/inference/v1/generate` 转译 shim 原型**本轮未实现**（形态 B 改为直接探 SGLang 原生 `/generate`，见 topology 报告；若形态定案后仍需要该转译层，其形状约束就是本报告第 3 节两条）。
- 单卡只证明推理侧；训练侧（多卡通信、权重同步）仍留 S4 前专项预实验（U-C 训练半边未动）。
- U-E 动态半边（thinking 剥离对多轮 bridge 的影响）本轮只覆盖到单轮 commit 的 token identity；多轮 bridge 在真端点上的复验随 S1 全链再关。
