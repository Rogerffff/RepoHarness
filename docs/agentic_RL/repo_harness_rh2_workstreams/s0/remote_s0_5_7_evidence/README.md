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
