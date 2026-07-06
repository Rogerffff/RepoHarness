# S0-5 到 S0-7 远程 GPU 验证证据摘要

验证机器：单卡 NVIDIA RTX PRO 6000 Blackwell Workstation Edition，96GB 显存，Ubuntu 22.04，Docker 28.1.1。

## S0-5：token 协议链路

结论：部分通过，足以支撑下一步设计判断。

- vLLM 0.24.0 + Qwen3-4B + verifiers `TrainClient` 已跑通 token ids、logprobs、Trace token identity。
- vLLM 0.24.0 + Qwen3-30B-A3B 已跑通 token ids、logprobs、MoE routing payload 返回。
- vLLM 的 MoE routing wire 形状不是 verifiers 当前期望的字典，而是 base64 `.npy` 字符串；需要薄 shim 转成 `{data, shape, start}`。
- 该 shim 已用验证脚本证明可行：Trace commit 后 `branch_routed_experts_shape = [21, 48, 8]`，token identity 仍成立。

关键证据：

- `trainclient_qwen3_4b_probe.json`
- `inspect_qwen3_30b_routing_payload.json`
- `trace_commit_qwen3_30b_routing_shim_probe.json`

## S0-6：MoE 张量穿透与形态 A/B 判断

结论：通过关键可行性验证，但仍需要在正式实现中固化协议 shim。

- 形态 A（verifiers 中心 + vLLM `/inference/v1/generate`）可行，但 routing payload 需要 wire shim。
- 形态 B（SGLang / slime 侧原生 generate）可行，SGLang 在 `--enable-return-routed-experts` 和请求侧 `return_routed_experts` 打开时返回 routing tape。
- SGLang 返回 token ids 与 output token logprobs；Qwen3-30B-A3B routing tape 可解析为 `[20, 48, 8]`。
- 该机器上的 SGLang 需要正确的 CUDA developer toolkit 路径；建议后续用固定容器镜像或标准 CUDA 开发栈，避免临时软链接方案。

关键证据：

- `sglang_qwen3_4b_generate_probe.json`
- `sglang_qwen3_30b_moe_generate_probe.json`
- `sglang_qwen3_30b_moe_generate_probe_with_routing.stdout.json`

## S0-6 补充：top-p 动态探针（2026-07-07 第二轮）

目的：关闭 implementation-notes 里"top-p tape 尚未动态验证"的 New-Unknown，并按执行计划 S0-6 第 3 条要求**显式设 `top_p=0.95`**（第一轮探针全部用 `temperature=0.0, top_p=1.0`，正是计划警告的假阴性条件——top_p=1.0 不产生截断候选集，看不到 tape 不代表没有 tape）。

方法（复用既有环境，未重装任何组件）：

- 服务端：stock SGLang 0.5.9（PyPI 安装，`/workspace/s0_inference_envs/sglang`）+ Qwen3-30B-A3B，启动参数与第一轮相同（`--enable-return-routed-experts --sampling-backend pytorch --moe-runner-backend triton --attention-backend triton --disable-cuda-graph`，CUDA 13 toolkit 路径借用 vLLM 环境）。
- 请求按 slime 的真实形状发（`slime/rollout/sglang_rollout.py:108`：`rollout_top_p != 1.0` 时 `sampling_params["custom_params"] = {"return_top_p_token_ids": True}`），`temperature=1.0, top_p=0.95, max_new_tokens=16`，同时开 `return_logprob` 与 `return_routed_experts`；另发一条不带 `custom_params` 的对照请求。
- 远程脚本与产物在 `/workspace/s0_topp_probe/`（独立新目录，未动既有文件）。

结果：

- **top-p tape 在 stock SGLang 0.5.9 上不存在。**两条请求的 `meta_info` 都是同样 13 个 key（`cached_tokens/cached_tokens_details/completion_tokens/e2e_latency/finish_reason/id/input_token_logprobs/output_token_logprobs/prompt_tokens/response_sent_to_client_ts/routed_experts/total_retractions/weight_version`），不含任何名字带 `top_p` 的 key；slime `slime/utils/types.py:9-10` 期望的 `top_p_token_ids / top_p_kept_token_ids / top_p_token_offsets / top_p_kept_token_offsets` 四个 key 全部缺失。
- **静默失败模式**：带 `custom_params={"return_top_p_token_ids": True}` 的请求返回 200，与对照组响应结构完全一致——stock server 不报错、只是忽略。也就是说 slime 风格客户端打到 stock SGLang 不会当场失败，而是到训练侧才炸（`slime/backends/megatron_utils/loss.py:47` 在 `rollout_top_p != 1.0` 时强制要求这两个字段）。
- **U-B 判定（top-p 半边）确认：需要 slime 的 sglang patch/镜像。**静态佐证：远程安装树 `grep -r "top_p_token_ids"` 零命中；slime 仓库 `docker/patch/latest/sglang-top_p.patch`（929 行、改 17 个文件：sampler、logits_processor、logprob utils、tokenizer_manager、scheduler、disaggregation、eagle 等）就是该 tape 的来源，patch 后由 `meta_info["top_p_token_ids"] / meta_info["top_p_token_offsets"]`（pybase64 int32）返回。
- **U-B 判定（routing 半边）反向确认：不需要 patch。**`enable_return_routed_experts` 是 stock 0.5.9 自带 flag（`sglang/srt/server_args.py:629`）。
- **routed_experts 在 top_p=0.95 下仍正常返回**：base64 int32 tape 解析为 `[30, 48, 8]`（prompt 15 + 生成 16；行数 = prompt−1+生成 的规律与第一轮 `[20,48,8]`＝13−1+8 一致），expert id 范围 0..127（Qwen3-30B-A3B 共 128 专家）。`output_token_logprobs` 16 条与 `completion_tokens=16` 逐 token 对齐且全部有限值。
- 附带核查（形态 A 侧对照）：远程 vLLM 0.24.0 安装树、本地 `reference/verifiers`、`reference/prime-rl` 三处 `grep "top_p_token_ids|top_p_kept|return_top_p"` 全部零命中——**形态 A 若需要 top-p replay，是"引擎不生成 + wire 契约无字段 + 消费端无解析"的三端缺口**。

关键证据：

- `sglang_qwen3_30b_topp_probe.json`（含两条请求的完整 sampling_params、meta_info key 清单、tape 解码摘要、server_info）

## S0-7：SWE smoke taskset

结论：未达到原计划完整验收，只完成远程 Docker 前置验证。

原计划要求从 SWE-Bench Verified 中选择 5 到 10 个有官方 x86_64 镜像的任务，实现 `SweSmokeTaskset`，并记录每题一次成功 rollout 与评分。当前代码库尚未实现该 taskset，也没有冻结题单，因此本次不能声明 S0-7 完整通过。

本次已完成的缩小验证：

- 远程 Docker GPU runtime 可用，容器内 `nvidia-smi` 正常。
- verifiers Docker runtime 分支可运行 toy loop。
- `default` harness 在 Docker 中完成两条 toy task，均 `reward = 1.0`。
- `null` harness 在 Docker 中按预期无法完成工具任务，均 `reward = 0.0`。

关键证据：

- `s0_7/default_docker.out`
- `s0_7/null_docker.out`
- `remote_default_docker_s0_7.json`
- `remote_null_docker_s0_7.json`

## 后续必须补齐

- S0-7 若要按原计划关闭，需要先冻结 5 到 10 个 SWE-Bench Verified smoke 题单，再实现 `SweSmokeTaskset`。
- vLLM 与 SGLang 的 routing payload shim 需要进入 S1 的中立 `TrajectoryProjection` 适配层，而不是散落在训练后端 adapter 中。
- SGLang / slime 路线建议优先使用固定容器镜像，减少 CUDA 工具链布局差异带来的不稳定性。
