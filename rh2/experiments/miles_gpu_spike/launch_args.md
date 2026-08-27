# miles GPU spike 最小启动参数清单（占位,租期校准）

> **状态：硬件段占位。** 本清单只保证"要素齐"——rh2 侧必须绑定的参数一个不少、
> 与 CPU 侧已验证语义一一对应;硬件相关数值（并行切分、显存参数、路径）在
> 租期开机后按实际机型校准,不承诺本文件可直接跑通。
> 背景：docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/spike-log.md
> （硬件段清单一节）;GPU 前最小收口 B2 项（scratchpad/codex_bfix_recheck.md）。

## 0. 代码与环境前置

| 项 | 值 | 说明 |
|---|---|---|
| miles checkout | `reference/miles-rh2-integration`,分支 `rh2-integration-v2`,HEAD `f6aab6542`,tree `9d7617bf5294d11918c9f7495fe7285ed80a35d5` | 开机前先跑 `rh2/scripts/miles_integration_lanes.sh`（C5 双 lane gate：树哈希/干净工作树/pin/patch digest/精确计数全过才算资格） |
| 训练脚本 | `train_async.py` | fully-async 专用（CI `_common.py` execute 同款选择） |
| 环境变量 | `MILES_EXPERIMENTAL_FT_TRAINER` **必须不设**（或设 0） | B6 锁定：实验 FT trainer 会捕获 cell 异常重试最多 30 次并允许部分 cell 失败继续（miles/ray/train/group.py train→retry 链）,吞掉 faithful DIS 的 fail-stop 语义。`faithful_dis_loss_function` 已 fail-closed（reason_code `experimental_ft_trainer_locked`）,设了也会拒绝,但应在启动层就不设 |
| 镜像 | sm_120 路径 (b)：官方镜像 + 重编 kernel wheel 清单 | spike-log S3;BF16-only |

## 1. rh2 绑定项（本次收口的核心,缺一即语义错误）

```
--custom-config-path <repo>/rh2/experiments/miles_gpu_spike/custom_config.yaml
    # 注入 rh2_engine_sampling_mask: true（B2 生产绑定;CPU 测试
    # test_gpu_spike_custom_config.py 已验证 miles 解析后为 bool True）

--custom-generate-function-path repoharness2.adapters.miles.generate_fn.Rh2MilesGenerateFn
    # CC 链入口;B1 惰性 bootstrap（ensure_fa_started）在首个样本时自动接通

--loss-type custom_loss
--custom-loss-function-path repoharness2.adapters.miles.faithful_dis_loss.faithful_dis_loss_function
    # faithful DIS（B3/B4 已修的归约链;fail-closed 面见该模块 docstring）

--rollout-top-p 0.8            # <1.0 = miles sampling-support replay 严格开关
                               # （canonicalize/conversion 强制逐样本 mask 的闸）
--rollout-top-k <有效 vocab size 占位,Qwen3 系 151936>
    # T0-A 拍板选项 1：top_k := 有效 vocab size 作硬件 spike 实验配置,
    # 实测 mask 体积/显存/吞吐后再定正式值。引擎硬约束:mask 开启必须有限
    # top_k（top_p-only 直接 abort）。对照上游 #2596 E2E 用 top_p=0.8+top_k=32
    # ——若首开机想先复刻上游小支持集形态,可临时用 32,但正式 spike 记录以
    # T0-A 口径为准。

--dynamic-sampling-filter-path miles.rollout.filter_hub.dynamic_sampling_filters.check_reward_nonzero_std
    # F2 零信号语义第 1 处接线：reward 全相等（组内零方差 ⇒ GRPO advantage
    # 全 0）的组在 DefaultDataBuffer.put 处丢弃,不进训练 buffer;fully-async
    # 持续 producer 自然补足 batch,**不需要** over_sampling_batch_size。
    # 漏网的全零 advantage 组由 trainer 侧全局零梯度判定兜底
    # （SKIPPED_ZERO_SIGNAL,见下"训练目标单一化"与 custom_config.yaml 熔断）。
```

PYTHONPATH 须含 `<repo>/rh2/src`（repoharness2 + vendor slime 同一源树）。

## 2. 拓扑与并行（对照 miles 30B fully-async CI,硬件段校准）

对照源：`reference/miles/tests/e2e/megatron/test_qwen3_30B_A3B/test_fully_async.py`
（8 卡 H100 = 6 train + 2 rollout,disaggregated,`use_r3=False`）与 `_common.py`。

```
--fully-async                          # 必选(worker 常驻;colocate 被断言拒绝)
--actor-num-nodes 1
--actor-num-gpus-per-node 6            # 占位:先复现 6+2,再收 4+4(spike 目标)
--rollout-num-gpus 2
--rollout-num-gpus-per-engine 2
--tensor-model-parallel-size 1
--sequence-parallel
--pipeline-model-parallel-size 3       # 占位:4+4 下需重切(如 pp2)
--context-parallel-size 1              # ⚠️ 与 CI 的 cp2 有意不同:
                                       # faithful_dis_loss CP>1 fail-closed
                                       # (cp_not_supported,归硬件段验证),
                                       # spike 首配必须 cp=1
--expert-model-parallel-size 2
--expert-tensor-parallel-size 1
--moe-token-dispatcher-type alltoall   # CI 非 deepep 分支同款
--update-weight-transfer-mode broadcast
```

## 3. 模型/数据/优化器（CI 同款骨架,路径与规模占位）

```
--hf-checkpoint /root/models/Qwen3-30B-A3B          # 占位:实际租期路径
--ref-load <megatron ckpt 占位>
--prompt-data <rh2 SWE 任务数据占位>                 # CI 用 dapo-math;rh2 换
--input-key prompt --label-key label                 #   SWE task spec 数据面
--num-rollout 3                                      # 占位:冷启+warm drain+跨权重更新
--rollout-batch-size 8 --n-samples-per-prompt 8 --global-batch-size 32
--rollout-max-response-len 8192 --rollout-temperature 1
--use-dynamic-batch-size --max-tokens-per-gpu <机型校准>
    # 注意:qkv_format=thd 路径;faithful_dis 拒绝 calculate_per_token_loss
--optimizer adam --lr 1e-6 --lr-decay-style constant --weight-decay 0.1
--adam-beta1 0.9 --adam-beta2 0.98
--attention-dropout 0.0 --hidden-dropout 0.0
--accumulate-allreduce-grads-in-fp32 --attention-softmax-in-fp32
--attention-backend flash
--recompute-granularity full --recompute-method uniform --recompute-num-layers 1
--bf16                                               # sm_120 低精度全线不可用(S3)
--sglang-mem-fraction-static 0.7 --sglang-max-running-requests 512
```

有意不带（与 CI 差异,防语义混入）：`--advantage-estimator gspo/--use-tis/
--eps-clip`（CI 的 GSPO/TIS 配置,与 custom_loss 冲突面未审,首 spike 不混用）、
`--use-routing-replay`（R3 语义归租期五项之一,单独开）、eval 参数组（首 spike
不跑 eval lane）。

## 3.1 训练目标单一化（F2 零信号判定的前提,显式锁死）

trainer 侧 SKIPPED_ZERO_SIGNAL 的判定对象是 **total gradient**（optimizer 前
的完整累计梯度）。只有当 faithful DIS policy loss 是**唯一**训练目标时,
"total gradient 精确为零 ⇔ policy signal 为零"才成立;混入任何辅助目标
（MTP/OPD/KL/entropy/MoE aux loss）后,零 advantage 批也会因辅助梯度非零而
被误判 NORMAL 并照常 optimizer.step。因此下列目标必须显式关死（多数即默认
值,仍显式写出并在启动自检核对,防 CI 模板抄写混入）：

```
（不带 --enable-mtp-training）        # MTP 训练关（store_true 默认 False）
（不带 --use-opd）                    # OPD 蒸馏关（store_true 默认 False）
（不带 --use-kl-loss）                # GRPO KL loss 关（store_true 默认 False）
--kl-coef 0.0                         # reward 端 KL penalty 系数显式 0（默认已 0）
--entropy-coef 0.0                    # entropy bonus 显式 0（默认已 0）
moe_aux_loss_coeff: 0.0               # 经 custom_config.yaml 注入（miles 无同名
                                      #   CLI 旗标;model_provider 在该 key 非
                                      #   None 时覆写 provider 值——provider 缺省
                                      #   来自 HF config 转换,不保证为 0,必须
                                      #   显式置 0）
```

零信号连续跳过熔断（F2 语义配套,阈值可配）同样经 custom_config.yaml 注入
`max_consecutive_zero_signal_steps`（见该文件注释;miles 尚无一等 CLI 旗标,
custom-config setattr 是既有官方注入面）。

## 4. 开机自检顺序（要素级,非脚本）

1. `rh2/scripts/miles_integration_lanes.sh` 全绿（资格 gate）。
2. 启动后看 startup 探针日志:mask 分支断言（`rh2_engine_sampling_mask` 生效、
   请求带顶层 `return_sampling_mask`、旧 `custom_params` tape 约定关闭）。
3. 首个 microbatch:faithful_dis metrics（`dis_accepted_tokens`>0、
   `dis_microbatch_provenance_tokens` 合账）;任何 `FaithfulDisLossError`
   reason_code 都是发现即停项。
