# S1-0 U-H 验证报告：slime patch 镜像在 Blackwell 上的 top-p / routing tape

日期：2026-07-07 UTC。

## 结论

**U-H 通过。** `slimerl/slime:latest` 当前 digest 对应的镜像可以在单卡 NVIDIA RTX PRO 6000 Blackwell 上启动 Qwen/Qwen3-30B-A3B 的 SGLang 服务，并在 `top_p=0.95`、`custom_params.return_top_p_token_ids=true`、`return_routed_experts=true` 的 slime 风格 `/generate` 请求中同时返回：

- 逐 token `output_token_logprobs`；
- `top_p_token_ids`；
- `top_p_token_offsets`；
- `routed_experts`。

这说明 S1 可以继续采用形态 B：slime 镜像内 SGLang 作为训练 rollout 主推理栈。后续实现仍必须在服务启动后运行同类探针，因为本次 control case 证明：不带 `custom_params.return_top_p_token_ids=true` 时，服务不会返回 top-p tape。

## 环境

远端机器：

```text
ssh -i ~/.ssh/vastai_ed25519 -p 19451 root@99.148.65.9
GPU: NVIDIA RTX PRO 6000 Blackwell Workstation Edition
driver: 580.95.05
host CUDA reported by nvidia-smi: 13.0
GPU memory: 97887 MiB
disk: /dev/vda1, about 776G total
```

镜像：

```text
image: slimerl/slime:latest
repo digest: slimerl/slime@sha256:a7317182c71d35712ee4edc86a5d1c313dc969efdf0026d339673299c186ea75
image id: sha256:233e8dab397af709ec4fe6a2ad2fb8221d52a6355a0eba78b8a90a2708a5dfbd
image size: 44346047831 bytes
container CUDA banner: 12.9.1
sglang: 0.5.13
slime: 0.3.0
torch: 2.11.0+cu129
transformers: 5.8.1
```

机器初始问题：Docker 已登记 `nvidia` runtime，但宿主缺少 `nvidia-container-runtime` 可执行文件，`docker run --gpus all` 与 `--runtime=nvidia` 都无法使用 GPU。已安装并配置：

```text
libnvidia-container1: 1.19.1-1
libnvidia-container-tools: 1.19.1-1
nvidia-container-toolkit-base: 1.19.1-1
nvidia-container-toolkit: 1.19.1-1
```

这属于远端实例基础设施修复，不是 RepoHarness 源码改动。

## 服务启动

启动命令要点：

```text
python -m sglang.launch_server
  --model-path Qwen/Qwen3-30B-A3B
  --host 0.0.0.0
  --port 30000
  --dtype bfloat16
  --mem-fraction-static 0.90
  --max-total-tokens 4096
  --disable-cuda-graph
  --attention-backend triton
  --sampling-backend pytorch
  --moe-runner-backend triton
  --enable-return-routed-experts
```

关键日志：

```text
Load weight end. elapsed=136.72 s, type=Qwen3MoeForCausalLM, avail mem=37.35 GB, mem usage=56.89 GB.
KV Cache is allocated. dtype: torch.bfloat16, #tokens: 4096, K size: 0.19 GB, V size: 0.19 GB
HostCache[routed_experts] allocated: shape=(4097, 48, 8), size=0.01 GB
DeviceCache[routed_experts] allocated: shape=(8192, 48, 8), size=12.00 MB
Capture piecewise CUDA graph end. Time elapsed: 48.51 s. mem usage=0.88 GB. avail mem=35.66 GB.
Application startup complete.
Uvicorn running on http://0.0.0.0:30000
```

注意：虽然启动命令传入了 `--disable-cuda-graph`，SGLang 0.5.13 仍执行了 piecewise CUDA graph capture 并成功完成。后续如果希望完全关闭这一步，需要额外评估 `--disable-piecewise-cuda-graph`；本次不阻塞 U-H。

另一个性能提示：服务使用了默认 MoE kernel config，日志提示缺少针对 `NVIDIA_RTX_PRO_6000_Blackwell_Workstation_Edition` 的专用 Triton MoE config。它影响吞吐调优，不影响本次 tape 正确性。

## 探针结果

主 case 请求：

```text
input_ids: 由 Qwen3 chat template 渲染，prompt_len = 15
max_new_tokens: 16
temperature: 1.0
top_p: 0.95
custom_params.return_top_p_token_ids: true
return_logprob: true
return_text_in_logprobs: false
logprob_start_len: 15
return_routed_experts: true
```

主 case 结果：

```text
HTTP: 200
elapsed_seconds: 0.791
completion_tokens: 16
output_token_logprobs: present, 16 entries, all finite
top_p_token_ids: present, base64 int32, 21 ids
top_p_token_offsets: present, base64 int32, 17 offsets
top_p offsets length: generated_len + 1 = 17
top_p offsets monotonic: true
top_p offsets last: 21
top_p ids cover offsets_last: true
routed_experts: present, base64 int32
routed_experts raw bytes: 46080
routed_experts int32 count: 11520
routed_experts inferred shape: [30, 48, 8]
routed_experts row semantics: prompt_len - 1 + generated_len = 15 - 1 + 16 = 30
expert id range: 0..127
overall_pass: true
```

Control case：

```text
top_p=0.95
custom_params.return_top_p_token_ids omitted
HTTP: 200
top-p related keys: absent
routed_experts: present, shape [30, 48, 8]
```

这个对照很重要：它说明 patch 镜像不会无条件返回 top-p tape，RepoHarness / slime adapter 启动时必须显式发送 `custom_params.return_top_p_token_ids=true` 的探针，不能只看服务是否能够正常生成文本。

## Evidence

```text
docs/agentic_RL/repo_harness_rh2_workstreams/s1/sglang_s1_0_topp_probe.py
  sha256 f5e95f8bbb12fbd78451c786a309706aec7918e18a49f9c9a2aa54245ae1e227

docs/agentic_RL/repo_harness_rh2_workstreams/s1/sglang_qwen3_30b_topp_probe.json
  sha256 b053bbcb66e10e54b6204fa8cfab469b703b8e3f7ab5cb430443d3b0af1b4cc0

docs/agentic_RL/repo_harness_rh2_workstreams/s1/server_info.json
  sha256 529c8f7ca2d32af6b560ed2e0be29a00058e528a7866a7c1d774a45b46d80ccb

docs/agentic_RL/repo_harness_rh2_workstreams/s1/server_key_lines.log
  sha256 3df6a3d419ee4708327768d3b935a02dba1298f766fcd30f5d6a9169e9b51ae1
```

## 对 S1 的影响

1. `U-H_slime_image_sm120` 可以关闭，状态为通过。
2. S1 可以继续以 shape B 作为训练主链路，不需要因为 top-p tape 暂时退回 `top_p=1.0`。
3. S1-1 / S1-3 的 `TrajectoryProjection` 应把 SGLang 返回的 `top_p_token_ids/top_p_token_offsets` 作为首批 `SamplingMaskRef` / backend tensor 事实接入。
4. S1-6 的启动期 hard probe 必须检查 top-p tape 和 routing tape，且必须在请求侧显式传 `custom_params.return_top_p_token_ids=true`。
5. 后续吞吐调优阶段可以单独评估 piecewise CUDA graph 是否需要显式禁用，以及是否需要为 RTX PRO 6000 Blackwell 生成 MoE Triton kernel config。
