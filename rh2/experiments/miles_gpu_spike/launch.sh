#!/usr/bin/env bash
# miles GPU spike 可执行 launch 闭包（F3/P0-4 收口；launch_args.md 占位清单的可执行升级）。
#
# 背景与事实源：
#   - finding：tmp/codex_miles_local_spike_closure_review_20260826.md §5（F3：GPU
#     runtime env 未闭包——RH2_MODEL_ID/tarball/execution mode/守卫/MoE 期望/Ray
#     worker 环境全部缺）。
#   - 范围：tmp/codex_miles_gpu_spike_scope_recommendation_20260826.md §4 P0-4、§5 G0~G3。
#   - 要素清单（参数语义解释）：同目录 launch_args.md；本脚本是"这些要素如何真正
#     进入进程环境"的唯一可执行事实源，两者冲突以本脚本为准并回改文档。
#   - runtime-env 复用：rh2/experiments/p3_preflight/j4_full_step.sh:185-205（P3 已在
#     同类 sm_120 八卡机上验证过的 Ray worker env 事实：PYTHONPATH/PATH(docker CLI)/
#     adapter host/artifact dir/CC tarball/MoE 期望）。
#
# 用法：
#   bash launch.sh preflight   # 不起任何 GPU 作业：断言环境闭包（env 齐全、tarball
#                              # 在场、manifest 校验过、模型拓扑一致、custom_config
#                              # 键在位且顶层键收白名单（P6b，防 P11 后置覆写）、
#                              # R3 显式选择合法）。本机可跑（用桩 asset）。
#   bash launch.sh dry-run     # preflight + 打印完整 ray job submit 命令与
#                              # runtime-env JSON，不提交。
#   bash launch.sh run         # preflight + 真实 ray job submit（租期 GPU 机上执行）。
#
# 必须显式给出（无默认值，防"依赖环境默认"）：
#   RH2_GPU_SPIKE_R3=on|off    # R3 routing replay 是显式选择（范围建议 §2）。
#                              # on  = 追加 --use-rollout-routing-replay + MoE tape 全链；
#                              #       preflight 会先断言 P0-3（F4 canonicalize 硬拒
#                              #       rollout_routed_experts）已在本仓关闭，未关闭则
#                              #       直接红——不许上卡撞已知 CPU 断点。
#                              # off = 不带该 flag；只验证基础运输链，结果不得记作
#                              #       Migration-Go 的 R3 项（范围建议 §2.1）。
#
# 租期机型校准位（有默认值，但 preflight 会打印+落盘实际取值）：
#   RH2_MEGATRON_PATH（默认 /root/Megatron-LM）、RH2_HF_CHECKPOINT、RH2_REF_LOAD、
#   RH2_RENDERERS_PATH、RH2_DOCKER_CLI_DIR、SLIME_AGENT_CC_PLATFORM_TARBALL、
#   RH2_SPIKE_RUN_ROOT（run 基目录；每次 run 在其下建唯一 RH2_SPIKE_RUN_ID 子
#   目录，已存在即拒绝——P0-1 run 隔离）、拓扑组（见 §topo）。
#
# 硬钉死（本脚本内不可被环境覆盖——覆盖 = 换实验，应改脚本并留痕）：
#   RH2_MODEL_ID=Qwen/Qwen3-30B-A3B；RH2_EXECUTION_MODE=s1_compat（pre-formal，见下）；
#   RH2_REQUIRE_REAL_WEIGHT_VERSIONS=1、RH2_REJECT_CONTEXT_SHRINK=1、
#   RH2_REJECT_NONZERO_HARNESS_EXIT=1；RH2_EXPECT_MOE_ROUTING=1、
#   RH2_MOE_NUM_LAYERS=48、RH2_MOE_ROUTER_TOPK=8（HF config 核实：num_hidden_layers=48、
#   num_experts_per_tok=8、decoder_sparse_step=1 且 mlp_only_layers=[] ⇒ 48 层全 MoE；
#   与 miles scripts/models/qwen3-30B-A3B.py、slime scripts/models/qwen3-30B-A3B.sh 一致）；
#   MILES_EXPERIMENTAL_FT_TRAINER 必须不设（B6 锁定：实验 FT trainer 的 retry/部分失败
#   继续语义会吞掉 faithful DIS 的 fail-stop；loss 侧已 fail-closed，这里在启动层就不设）；
#   --use-miles-router（V3 vendor refresh：#2596 最新 fail-closed 要求 top_p<1 必须走
#   MilesRouter）。engine 拓扑**不再钉死**（W10 / 决策包 D2+B v2 B-5b，2026-09-04）：
#   per-engine 卡数是普通启动配置 RH2_SPIKE_ROLLOUT_GPUS_PER_ENGINE（默认 2），engine 数
#   = rollout 卡数 / per-engine；preflight 只做整除与资源合法性检查。多 engine 下的
#   abort 错发 / 版本随机探测两处正确性缺口已由 W10 关闭（abort 改为 rid 级全 worker 广播、
#   版本探测删除，见 router_targeting_audit.md §5 状态）；首训 engine 数由 GPU 上同
#   rollout 卡数的 matched comparison（1×TP4 vs 2×TP2）决定，见 topo 注释。
#
# execution mode 说明（F3 §5.1，防"把 s1_compat 误称 formal FA"）：
#   s1_compat = pre-formal 硬件算法探针模式。fa_audit_only 返回 abort 样本不交训练；
#   fa_formal 当前 bringup.py 启动即拒绝（开闸前置未清）。本脚本钉 s1_compat，
#   **不翻转任何正式闸门**：rh2_s2_signal_trusted 与 rh2_formal_training_allowed
#   保持 false，本次运行结果只用于 Migration-Go 判定，不得表述为正式 FA 验证。
set -euo pipefail

MODE="${1:-}"
case "$MODE" in preflight|dry-run|run) ;; *)
  echo "用法: bash launch.sh preflight|dry-run|run" >&2; exit 2 ;;
esac

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"          # 仓库根（rh2 的上一级）
RH2="$ROOT/rh2"

FAIL=0
say()  { echo "[gpu-spike] $*"; }
fail() { echo "[gpu-spike] FAIL: $*" >&2; FAIL=1; }
die()  { echo "[gpu-spike] FAIL: $*" >&2; exit 1; }

# ---------------------------------------------------------------- 硬钉死组
export RH2_MODEL_ID="Qwen/Qwen3-30B-A3B"
export RH2_EXECUTION_MODE="s1_compat"               # pre-formal；见文件头说明
export RH2_REQUIRE_REAL_WEIGHT_VERSIONS="1"         # parse_bool_env_flag 严格 "0"/"1"
export RH2_REJECT_CONTEXT_SHRINK="1"
export RH2_REJECT_NONZERO_HARNESS_EXIT="1"
export RH2_EXPECT_MOE_ROUTING="1"
export RH2_MOE_NUM_LAYERS="48"
export RH2_MOE_ROUTER_TOPK="8"
# 必须不设。先记录父环境原值再 unset：unset 保证本进程链干净，P2 的断言用
# 原值把"父环境注入过"这一事实变成显式 FAIL（否则静默吞掉，操作员不知道
# 自己的环境偏离了钉死组）。truthy 判据对齐 miles environ.py
# enable_experimental_ft_trainer（"1"/"true"/"on"/"yes"；"0"/未设 = 关）。
MILES_FT_TRAINER_PARENT_VALUE="${MILES_EXPERIMENTAL_FT_TRAINER:-}"
unset MILES_EXPERIMENTAL_FT_TRAINER

# ---------------------------------------------------------------- 显式选择组
RH2_GPU_SPIKE_R3="${RH2_GPU_SPIKE_R3:-}"
case "$RH2_GPU_SPIKE_R3" in
  on|off) ;;
  *) die "RH2_GPU_SPIKE_R3 必须显式设为 on 或 off（当前='${RH2_GPU_SPIKE_R3}'）。R3 是显式选择，不依赖默认值。" ;;
esac

# ---------------------------------------------------------------- 租期校准位
MILES_ROOT="${RH2_MILES_ROOT:-$ROOT/reference/miles-rh2-integration}"
MEGATRON_PATH="${RH2_MEGATRON_PATH:-/root/Megatron-LM}"
RENDERERS_PATH="${RH2_RENDERERS_PATH:-/workspace/renderers}"
HF_CHECKPOINT="${RH2_HF_CHECKPOINT:-/root/models/Qwen3-30B-A3B}"
REF_LOAD="${RH2_REF_LOAD:-/root/Qwen3-30B-A3B_torch_dist}"
DOCKER_CLI_DIR="${RH2_DOCKER_CLI_DIR:-/root/tarballs/docker-cli}"
CC_PLATFORM_TARBALL="${SLIME_AGENT_CC_PLATFORM_TARBALL:-/root/tarballs/claude-code-linux-x64.tgz}"
export SLIME_AGENT_CC_PLATFORM_TARBALL="$CC_PLATFORM_TARBALL"
CC_EXTRA_ARGS="${SLIME_AGENT_CC_EXTRA_ARGS:---disallowedTools Task WebFetch WebSearch}"
ADAPTER_PUBLIC_HOST="${ADAPTER_PUBLIC_HOST:-172.17.0.1}"
ADAPTER_PORT="${ADAPTER_PORT:-18001}"
# P0-1（租前审查）：run 隔离。RH2_SPIKE_RUN_ROOT 是**基目录**，每次 run 在其下
# 创建唯一 run_id 子目录；固定复用同一目录会让旧 evidence/checkpoint 洗绿新
# run（append 型事件 + collector 全读 + --load 旧 ckpt 三路污染）。run 模式在
# 启动 Ray 前断言 run root 不存在；RUN_ID 经 runtime env（MILES_RH2_RUN_ID）
# 印入每条事件，collect --run-id 校验，judge 用 run_manifest.json 反向核对。
RUN_BASE="${RH2_SPIKE_RUN_ROOT:-/root/miles_gpu_spike}"
RUN_ID="${RH2_SPIKE_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-p$$-r$RANDOM}"
RUN_ROOT="$RUN_BASE/$RUN_ID"
EV="$RUN_ROOT/evidence"                              # 证据输出（g1_acceptance.py 输入）
EVENTS_DIR="$EV/events"                              # miles 结构化事件（rh2_event_log jsonl）
ARTIFACTS="$RUN_ROOT/artifacts"                      # rh2 bringup artifacts
CKPT="$RUN_ROOT/ckpt"                                # checkpoint（G1：存/读验证一次后删除）
DUMPS="$RUN_ROOT/rollout_dumps"
PROMPT_DATA="$SCRIPT_DIR/data/gpu_spike_prompts.jsonl"
PROMPT_DATA_SHA_EXPECTED="009b34e547f41e3be4053620d1d73c0967bfb41ee9c2ae02fe9191422c04cdc6"  # P0-5 预注册
EVAL_SMOKE_DATA="$SCRIPT_DIR/data/eval_smoke_prompts.jsonl"  # G1 eval 冒烟（spike 数据首条，1 prompt）
EVAL_SMOKE_SHA_EXPECTED="77e736d12fd3cf638c148ae9fa50361b5b01e03ecb1aa4cb6e01e3f791e41de0"

# topo（默认 G1 的 6+2；G2 换 4+4 时经环境覆盖，cp 恒为 1——faithful_dis CP>1 fail-closed）
ACTOR_GPUS="${RH2_SPIKE_ACTOR_GPUS:-6}"
ROLLOUT_GPUS="${RH2_SPIKE_ROLLOUT_GPUS:-2}"
# engine 拓扑（W10 / B-5b，2026-09-04 恢复为普通启动配置）：per-engine 卡数由
# RH2_SPIKE_ROLLOUT_GPUS_PER_ENGINE 决定，默认 2（= P3 J4 正式链的 2×TP2 形态；G1 默认
# 6+2 下得到 1 engine × TP2，与此前钉死时的实际拓扑相同；G2 的 4+4 下得到 2 engine × TP2）。
# miles 事实：engine 数 = rollout_num_gpus // rollout_num_gpus_per_engine
# （miles/ray/rollout/rollout_server.py:49 实际按此建 engine；
# update_weight_from_distributed/p2p_transfer_utils.py:64 同式）；sglang 推理 TP =
# per-engine 卡数（miles/backends/sglang_utils/arguments.py:184 sglang_tp_size =
# rollout_num_gpus_per_engine）。同 rollout 卡数的两种切法（如 4 卡：1×TP4 vs 2×TP2）
# 吞吐口径不可直接对比，首训 engine 数按 GPU matched comparison 决定（W10 报告 GPU 清单）。
# 此前"engine 数钉死 1"是绕开 MilesRouter 忽略 X-SMG-Routing-Key（abort/版本探测错发）
# 的临时限制，B-5b 裁定不得转为正式资格语义；两处缺口已由 W10 关闭：rh2 abort 改为
# `/list_workers` 全 worker 广播同一 rid（engine_router_client.py），经 router 随机探测
# 版本的路径删除（bringup.py `_observed_current_version`），publish 后版本收敛经 engine
# actor 逐台核对（integration tree RolloutManager.set_weight_version）。
ROLLOUT_GPUS_PER_ENGINE="${RH2_SPIKE_ROLLOUT_GPUS_PER_ENGINE:-2}"
TP="${RH2_SPIKE_TP:-1}"; PP="${RH2_SPIKE_PP:-3}"; EP="${RH2_SPIKE_EP:-2}"
CP=1                                                  # 不提供覆盖位：CP>1 直接换实验
NUM_ROLLOUT="${RH2_SPIKE_NUM_ROLLOUT:-3}"             # G1 最小：≥3 轮 rollout
ROLLOUT_BATCH_SIZE=8; N_SAMPLES_PER_PROMPT=8          # 与正式首训预注册组形态一致（n=8）
GLOBAL_BATCH_SIZE=32                                  # 64 样本/轮 ⇒ 每轮 2 optimizer step
MAX_TOKENS_PER_GPU="${RH2_MAX_TOKENS_PER_GPU:-16384}" # 机型校准
ROLLOUT_TOP_P="0.8"                                   # <1.0 = sampling-support replay 严格开关
ROLLOUT_TOP_K="${RH2_SPIKE_ROLLOUT_TOP_K:-151936}"    # T0-A：有效 vocab size 作 spike 配置

# ---------------------------------------------------------------- preflight
say "== preflight（mode=$MODE, R3=${RH2_GPU_SPIKE_R3}）=="

# P1. manifest 前置（integration tree/干净工作树/patch digest/pin）——复用 lanes 脚本，
#     不复制断言。注意 --checks-only ≠ lane 资格；租期开机前须完整跑一次双 lane。
if ! bash "$RH2/scripts/miles_integration_lanes.sh" --checks-only; then
  fail "miles_integration_lanes.sh --checks-only 未通过（integration tree/patch digest/pin 漂移）"
fi

# P2. MILES_EXPERIMENTAL_FT_TRAINER 断言：父环境 truthy 注入 = 显式 FAIL
#     （本进程已 unset 兜底，但操作员环境偏离钉死组必须看得见，不静默吞）
case "$(printf '%s' "$MILES_FT_TRAINER_PARENT_VALUE" | tr '[:upper:]' '[:lower:]')" in
  ""|0) ;;  # 未设或显式 0 = 合规（launch_args.md §0：必须不设或设 0）
  *) fail "父环境设置了 MILES_EXPERIMENTAL_FT_TRAINER='$MILES_FT_TRAINER_PARENT_VALUE'（B6 锁定要求必须不设；本脚本已 unset，但请先清理环境再跑——环境偏离不静默放行）" ;;
esac

# P3. 模型拓扑一致性：miles model-args 脚本推导值必须与 RH2_MOE_* 钉死值一致
#     （事实复用：shell_safe_model_args 正是 CI execute_train 拼进命令行的同一函数）
MODEL_ARGS_STR="$(PYTHONPATH="$MILES_ROOT" python3 -c \
  "from miles.utils.external_utils.model_args_utils import shell_safe_model_args; print(shell_safe_model_args('qwen3-30B-A3B'))")" \
  || die "无法从 $MILES_ROOT 推导 qwen3-30B-A3B model args（MILES_ROOT 是否正确？）"
# shlex.quote 产出的是 shell 语法字符串（如 --moe-layer-freq '[1,...]'），必须经
# eval 让 bash 真正解析引号，直接不加引号展开会把引号字符原样传给进程。
eval "MODEL_ARGS=($MODEL_ARGS_STR)"
echo "$MODEL_ARGS_STR" | grep -qE -- "--num-layers $RH2_MOE_NUM_LAYERS( |\$)" \
  || fail "miles model args 的 --num-layers 与 RH2_MOE_NUM_LAYERS=$RH2_MOE_NUM_LAYERS 不一致"
echo "$MODEL_ARGS_STR" | grep -qE -- "--moe-router-topk $RH2_MOE_ROUTER_TOPK( |\$)" \
  || fail "miles model args 的 --moe-router-topk 与 RH2_MOE_ROUTER_TOPK=$RH2_MOE_ROUTER_TOPK 不一致"
echo "$MODEL_ARGS_STR" | grep -qE -- "--moe-aux-loss-coeff 0( |\$)" \
  || fail "miles model args 未显式携带 --moe-aux-loss-coeff 0（训练目标单一化前提，launch_args.md §3.1）"

# P4. HF checkpoint 拓扑一致性（模型 id 一致 = config 事实一致，不看目录名）：
#     Qwen/Qwen3-30B-A3B 官方 config：model_type=qwen3_moe、num_hidden_layers=48、
#     num_experts_per_tok=8、num_experts=128、vocab_size=151936。
if [ -f "$HF_CHECKPOINT/config.json" ]; then
  python3 - "$HF_CHECKPOINT/config.json" "$RH2_MOE_NUM_LAYERS" "$RH2_MOE_ROUTER_TOPK" <<'PYEOF' || FAIL=1
import json, sys
cfg, layers, topk = json.load(open(sys.argv[1])), int(sys.argv[2]), int(sys.argv[3])
errs = []
if cfg.get("model_type") != "qwen3_moe":
    errs.append(f"model_type={cfg.get('model_type')!r} != 'qwen3_moe'")
if cfg.get("num_hidden_layers") != layers:
    errs.append(f"num_hidden_layers={cfg.get('num_hidden_layers')} != {layers}")
if cfg.get("num_experts_per_tok") != topk:
    errs.append(f"num_experts_per_tok={cfg.get('num_experts_per_tok')} != {topk}")
if cfg.get("num_experts") != 128:
    errs.append(f"num_experts={cfg.get('num_experts')} != 128")
if cfg.get("vocab_size") != 151936:
    errs.append(f"vocab_size={cfg.get('vocab_size')} != 151936")
# mlp_only_layers 非空或 decoder_sparse_step>1 时 MoE 层数 != num_hidden_layers
if cfg.get("mlp_only_layers") or cfg.get("decoder_sparse_step", 1) != 1:
    errs.append("存在 dense-only 层（mlp_only_layers/decoder_sparse_step）——RH2_MOE_NUM_LAYERS=48 的口径失效")
if errs:
    print("[gpu-spike] FAIL: HF checkpoint config 与 Qwen3-30B-A3B 钉死拓扑不一致: " + "; ".join(errs), file=sys.stderr)
    sys.exit(1)
print("[gpu-spike] HF checkpoint config 拓扑核对通过（qwen3_moe/48层/topk8/128专家/vocab151936）")
PYEOF
else
  fail "HF checkpoint 缺 config.json：${HF_CHECKPOINT}（RH2_HF_CHECKPOINT 未就位）"
fi

# P5. Claude Code 平台 tarball 在场且含自包含二进制（bringup ClaudeCodeDriver 硬读取
#     SLIME_AGENT_CC_PLATFORM_TARBALL，解包安装 package/claude；容器内版本比对在启动期）
if [ -f "$CC_PLATFORM_TARBALL" ]; then
  if tar -tzf "$CC_PLATFORM_TARBALL" 2>/dev/null | grep -q "^package/claude$"; then
    say "CC 平台 tarball 校验通过：${CC_PLATFORM_TARBALL}（含 package/claude）"
  else
    fail "CC 平台 tarball 不含 package/claude：${CC_PLATFORM_TARBALL}（不是 @anthropic-ai/claude-code-linux-x64 平台包？）"
  fi
else
  fail "CC 平台 tarball 不存在：${CC_PLATFORM_TARBALL}（SLIME_AGENT_CC_PLATFORM_TARBALL）"
fi

# P6. custom_config.yaml 三键在场（语义级断言在 tests/adapters_miles/
#     test_gpu_spike_custom_config.py——按 miles 真实 loader 逐 key 验证；这里是
#     启动闭包级的存在性把关，故意用无依赖的逐行匹配）
CUSTOM_CONFIG="$SCRIPT_DIR/custom_config.yaml"
[ -f "$CUSTOM_CONFIG" ] || fail "custom_config.yaml 不存在：$CUSTOM_CONFIG"
grep -qE '^rh2_engine_sampling_mask: true$' "$CUSTOM_CONFIG" \
  || fail "custom_config.yaml 缺 'rh2_engine_sampling_mask: true'（B2 生产绑定）"
grep -qE '^moe_aux_loss_coeff: 0\.0$' "$CUSTOM_CONFIG" \
  || fail "custom_config.yaml 缺 'moe_aux_loss_coeff: 0.0'（F2 训练目标单一化）"
grep -qE '^max_consecutive_zero_signal_steps: [0-9]+$' "$CUSTOM_CONFIG" \
  || fail "custom_config.yaml 缺 'max_consecutive_zero_signal_steps: <N>'（F2 熔断）"

# P6b. custom_config.yaml 顶层键白名单（vendor refresh 复核 P2 #2：P11 后置
#      覆写防护）。miles 事实：miles_validate_args 在**全部参数校验之后**才把
#      YAML 逐键 setattr 到 args（integration arguments.py:3521 附近），即 YAML
#      里的 use_miles_router/拓扑/PD/qkv 类键可以在 P11 与 miles 自身校验都跑完
#      后静默改写 effective args——CLI token 检查（P11）对这条后门无感。收法 =
#      白名单而非黑名单（fail-closed）：只放行现有三个安全键的**精确钉死行**
#      （与 P6 同一形态），其余任何顶层行（未知键、带引号键、`---` 文档分隔、
#      flow mapping、同键重复出现等一切形态）一律 preflight 红。新键必须先过
#      评审加进本白名单，并同步 test_gpu_spike_custom_config.py 的整 dict 断言。
#      注意缩进行放行的边界：miles 只 setattr 顶层键，缩进行只能是白名单键的
#      嵌套值——而三个白名单行都是钉死的标量形态，不会有合法缩进从属行，故
#      任何缩进行意味着顶层行已先违规或文件被改坏，仍由顶层行检出。
CC_KEY_VIOLATIONS="$(awk '
  /^[[:space:]]*#/ { next }                       # 注释行
  /^[[:space:]]*$/ { next }                       # 空行
  /^[[:space:]]/   { next }                       # 缩进行（见上方边界说明）
  /^rh2_engine_sampling_mask: true$/              { if (++seen_mask  > 1) print NR": 重复键 rh2_engine_sampling_mask（yaml 取末次赋值,重复=改值后门）"; next }
  /^max_consecutive_zero_signal_steps: [0-9]+$/   { if (++seen_fuse  > 1) print NR": 重复键 max_consecutive_zero_signal_steps（yaml 取末次赋值,重复=改值后门）"; next }
  /^moe_aux_loss_coeff: 0\.0$/                    { if (++seen_coeff > 1) print NR": 重复键 moe_aux_loss_coeff（yaml 取末次赋值,重复=改值后门）"; next }
  { print NR": "$0 }
' "$CUSTOM_CONFIG")"
if [ -n "$CC_KEY_VIOLATIONS" ]; then
  fail "custom_config.yaml 存在白名单外的顶层行（miles 会在校验后逐键 setattr——P11 语义可被后置覆写,fail-closed 拒绝;违规行如下）：
$CC_KEY_VIOLATIONS"
fi

# P7. R3 显式选择的可行性闸：on 要求 P0-3（F4）本地 adapter 已关闭。当前判据 =
#     canonicalize.py 的 _REJECTED_SLIME_FIELDS 仍把 rollout_routed_experts 钉为
#     必须 None（"torch->numpy 转换语义未定义"）。该拒绝面在场 ⇒ R3-on 样本在进
#     Miles buffer 前确定失败，禁止上卡。
CANON="$RH2/src/repoharness2/adapters/miles/canonicalize.py"
if [ "$RH2_GPU_SPIKE_R3" = "on" ]; then
  if grep -q 'routing tape 的 torch->numpy 形状/dtype 转换语义未定义' "$CANON"; then
    fail "RH2_GPU_SPIKE_R3=on 但 P0-3 未关闭：canonicalize 仍硬拒 rollout_routed_experts（finding F4）。先关本地 adapter 再上卡。"
  else
    say "R3=on：canonicalize 硬拒面已移除（P0-3 判据通过）"
  fi
else
  say "R3=off：不带 --use-rollout-routing-replay；结果不得记作 Migration-Go 的 R3 项"
fi

# P8. P0-5 预注册 prompt 数据在场且未被改动（组构成见 positive_control.md；
#     数据与 s1_7a make_prompt_data.py 同源可复生成）
if [ -f "$PROMPT_DATA" ]; then
  PROMPT_SHA_ACTUAL="$(shasum -a 256 "$PROMPT_DATA" | awk '{print $1}')"
  if [ "$PROMPT_SHA_ACTUAL" != "$PROMPT_DATA_SHA_EXPECTED" ]; then
    fail "预注册 prompt 数据 sha256 漂移 expected=$PROMPT_DATA_SHA_EXPECTED actual=${PROMPT_SHA_ACTUAL}（P0-5 组构成不得现场改）"
  else
    say "预注册 prompt 数据校验通过：$PROMPT_DATA"
  fi
else
  fail "预注册 prompt 数据不存在：$PROMPT_DATA"
fi
if [ -f "$EVAL_SMOKE_DATA" ]; then
  EVAL_SHA_ACTUAL="$(shasum -a 256 "$EVAL_SMOKE_DATA" | awk '{print $1}')"
  [ "$EVAL_SHA_ACTUAL" = "$EVAL_SMOKE_SHA_EXPECTED" ] \
    || fail "eval 冒烟数据 sha256 漂移 expected=$EVAL_SMOKE_SHA_EXPECTED actual=$EVAL_SHA_ACTUAL"
else
  fail "eval 冒烟数据不存在：${EVAL_SMOKE_DATA}（G1 eval 路径冒烟依赖）"
fi

# P9. 其余路径闭包（Ray worker 将经 runtime-env 继承这些路径）
[ -d "$MEGATRON_PATH" ]   || fail "Megatron 路径不存在：${MEGATRON_PATH}（RH2_MEGATRON_PATH）"
[ -f "$RENDERERS_PATH/renderers/__init__.py" ] \
  || fail "renderers 包不在场：$RENDERERS_PATH/renderers/__init__.py（RH2_RENDERERS_PATH 应指向含 renderers/ 包的仓库根；bringup 'from renderers import ...' 依赖）"
[ -x "$DOCKER_CLI_DIR/docker" ] || fail "docker CLI 不可执行：$DOCKER_CLI_DIR/docker（RH2_DOCKER_CLI_DIR，沙箱驱动依赖）"
[ -f "$MILES_ROOT/train_async.py" ] || fail "miles train_async.py 不存在：$MILES_ROOT/train_async.py"

# P9b. reference checkpoint（--ref-load）tracker 存在性：坏 REF_LOAD 必须在
#      preflight 红，不许拖到 Ray/Miles 启动阶段才失败（B4）。Megatron dist
#      checkpoint 目录判据 = latest_checkpointed_iteration.txt tracker，或
#      至少一个 iter_*/release 迭代目录。
if [ -d "$REF_LOAD" ]; then
  if [ -f "$REF_LOAD/latest_checkpointed_iteration.txt" ]; then
    say "REF_LOAD tracker 校验通过：$REF_LOAD/latest_checkpointed_iteration.txt = $(cat "$REF_LOAD/latest_checkpointed_iteration.txt")"
  elif compgen -G "$REF_LOAD/iter_*" >/dev/null || [ -d "$REF_LOAD/release" ]; then
    say "REF_LOAD 无 tracker 但存在迭代目录（release/iter_*），按可加载处理：$REF_LOAD"
  else
    fail "REF_LOAD 不是可加载的 Megatron checkpoint：$REF_LOAD 缺 latest_checkpointed_iteration.txt 且无 iter_*/release 目录（RH2_REF_LOAD）"
  fi
else
  fail "REF_LOAD 目录不存在：${REF_LOAD}（RH2_REF_LOAD）"
fi

# P9c. integration tree digest（B3 + 租前审查 P0-4）：用与 miles worker 完全
#      相同的函数（miles.utils.rh2_event_log.miles_tree_digest，patch 0004）
#      预计算钉死值。该值经 runtime-env 下发（RH2_EXPECTED_MILES_TREE_DIGEST），
#      每类 Ray actor 启动时自证一致，不一致当场 raise 停机。
#      **去自我背书**：expected 值不再只由"运行目标自己算出"背书——必须与
#      integration_base_manifest.json 的 miles_source_tree_digest（审计 manifest
#      单事实源）一致，且 $MILES_ROOT 的 git HEAD^{tree} == manifest expected_tree
#      且工作树干净。RH2_MILES_ROOT 指到另一棵树时这里在 Ray 前直接红。
LANES_MANIFEST="$ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/integration_base_manifest.json"
MILES_TREE_DIGEST="$(PYTHONPATH="$MILES_ROOT" python3 -c \
  "from miles.utils.rh2_event_log import miles_tree_digest; print(miles_tree_digest())")" \
  || die "无法从 $MILES_ROOT 计算 miles tree digest（integration tree 缺 patch 0004 的 rh2_event_log 模块？）"
MANIFEST_SOURCE_DIGEST="$(python3 -c \
  "import json;print(json.load(open('$LANES_MANIFEST')).get('miles_source_tree_digest',''))")" \
  || die "无法读取 manifest：$LANES_MANIFEST"
MANIFEST_EXPECTED_TREE="$(python3 -c \
  "import json;print(json.load(open('$LANES_MANIFEST'))['expected_tree'])")"
if [ -z "$MANIFEST_SOURCE_DIGEST" ]; then
  fail "manifest 缺 miles_source_tree_digest 字段（P0-4：expected digest 必须来自审计 manifest，不许运行目标自我背书）"
elif [ "$MILES_TREE_DIGEST" != "$MANIFEST_SOURCE_DIGEST" ]; then
  fail "MILES_ROOT=$MILES_ROOT 的 source digest=$MILES_TREE_DIGEST != manifest 钉死值 ${MANIFEST_SOURCE_DIGEST}（运行目标不是审计过的 integration tree）"
fi
MILES_GIT_TREE="$(git -C "$MILES_ROOT" rev-parse 'HEAD^{tree}' 2>/dev/null || echo MISSING)"
[ "$MILES_GIT_TREE" = "$MANIFEST_EXPECTED_TREE" ] \
  || fail "MILES_ROOT git HEAD^{tree}=$MILES_GIT_TREE != manifest expected_tree=$MANIFEST_EXPECTED_TREE"
[ -z "$(git -C "$MILES_ROOT" status --porcelain 2>/dev/null)" ] \
  || fail "MILES_ROOT 工作树不干净——实际运行代码 != 审计过的树"
say "miles tree digest（manifest 钉死）：$MILES_TREE_DIGEST"

# P10. 阈值/验收面在场（P0-6：不在租卡现场临时决定什么算通过）
[ -f "$SCRIPT_DIR/thresholds.md" ]    || fail "thresholds.md 不存在（P0-6 判定阈值单页）"
python3 "$SCRIPT_DIR/g1_acceptance.py" --self-test >/dev/null 2>&1 \
  || fail "g1_acceptance.py --self-test 未通过（验收判定器自身故障）"

if [ "$FAIL" -ne 0 ]; then
  die "preflight 未通过（见上方 FAIL 各行）——不满足 GPU 启动闭包"
fi
# 注意：这里**不**宣告 preflight 通过——P11 语义闸（参数组装后的 token 流断言）
# 也是 preflight 闭包的一部分，"preflight 全部通过"移到 P11 之后输出（vendor
# refresh 复核 P2 #2：防止 P11 红之前已经打出全绿字样误导操作员/日志判读）。

# ---------------------------------------------------------------- 参数组装
# Ray worker runtime env（F3 核心：这些必须真实抵达 Ray actor，而不只在 driver shell。
# 布局与取值参照 j4_full_step.sh:185-205 的已验证事实 + 本次 F3 增补的 RH2_* 钉死组。
# B3：$MILES_ROOT 置于 PYTHONPATH **首位**——Ray worker 反序列化 miles.* actor 类
# 时按 sys.path 顺序解析，首位保证加载 integration tree 而非镜像内 stock miles；
# 每类 actor 再用 RH2_EXPECTED_MILES_TREE_DIGEST 自证（不一致 raise 停机）。）
RUNTIME_ENV_JSON="{
  \"env_vars\": {
    \"PYTHONPATH\": \"${MILES_ROOT}:${MEGATRON_PATH}:${RH2}/src:${RH2}/experiments:${RENDERERS_PATH}\",
    \"MILES_RH2_EVENT_DIR\": \"${EVENTS_DIR}\",
    \"MILES_RH2_RUN_ID\": \"${RUN_ID}\",
    \"RH2_EXPECTED_MILES_TREE_DIGEST\": \"${MILES_TREE_DIGEST}\",
    \"PYTHONUNBUFFERED\": \"1\",
    \"CUDA_DEVICE_MAX_CONNECTIONS\": \"1\",
    \"NCCL_NVLS_ENABLE\": \"${NCCL_NVLS_ENABLE:-0}\",
    \"PATH\": \"${DOCKER_CLI_DIR}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\",
    \"ADAPTER_PUBLIC_HOST\": \"${ADAPTER_PUBLIC_HOST}\",
    \"ADAPTER_PORT\": \"${ADAPTER_PORT}\",
    \"RH2_MODEL_ID\": \"${RH2_MODEL_ID}\",
    \"RH2_EXECUTION_MODE\": \"${RH2_EXECUTION_MODE}\",
    \"RH2_REQUIRE_REAL_WEIGHT_VERSIONS\": \"${RH2_REQUIRE_REAL_WEIGHT_VERSIONS}\",
    \"RH2_REJECT_CONTEXT_SHRINK\": \"${RH2_REJECT_CONTEXT_SHRINK}\",
    \"RH2_REJECT_NONZERO_HARNESS_EXIT\": \"${RH2_REJECT_NONZERO_HARNESS_EXIT}\",
    \"RH2_EXPECT_MOE_ROUTING\": \"${RH2_EXPECT_MOE_ROUTING}\",
    \"RH2_MOE_NUM_LAYERS\": \"${RH2_MOE_NUM_LAYERS}\",
    \"RH2_MOE_ROUTER_TOPK\": \"${RH2_MOE_ROUTER_TOPK}\",
    \"RH2_BRINGUP_ARTIFACT_DIR\": \"${ARTIFACTS}\",
    \"RH2_BRINGUP_HARNESS\": \"${RH2_BRINGUP_HARNESS:-claude_code}\",
    \"SWE_AGENT_TIME_BUDGET_SEC\": \"${SWE_AGENT_TIME_BUDGET_SEC:-600}\",
    \"RH2_MAX_TURNS_PER_SID\": \"${RH2_MAX_TURNS_PER_SID:-25}\",
    \"SLIME_AGENT_CC_PLATFORM_TARBALL\": \"${CC_PLATFORM_TARBALL}\",
    \"SLIME_AGENT_CC_EXTRA_ARGS\": \"${CC_EXTRA_ARGS}\"
  }
}"
# 注意：MILES_EXPERIMENTAL_FT_TRAINER 有意不出现在 runtime env（必须不设）。

CKPT_ARGS=(
  --hf-checkpoint "$HF_CHECKPOINT"
  --ref-load "$REF_LOAD"
  --load "$CKPT"
  --save "$CKPT"
  --save-interval 1
)
ROLLOUT_ARGS=(
  --prompt-data "$PROMPT_DATA"
  --input-key prompt
  --label-key label
  --metadata-key metadata
  --num-rollout "$NUM_ROLLOUT"
  --rollout-batch-size "$ROLLOUT_BATCH_SIZE"
  --n-samples-per-prompt "$N_SAMPLES_PER_PROMPT"
  --rollout-max-response-len "${RH2_MAX_RESPONSE_LEN:-8192}"
  --rollout-max-context-len "${RH2_MAX_CONTEXT_LEN:-32768}"
  --rollout-temperature 1
  --rollout-top-p "$ROLLOUT_TOP_P"
  --rollout-top-k "$ROLLOUT_TOP_K"
  --global-batch-size "$GLOBAL_BATCH_SIZE"
  --custom-config-path "$CUSTOM_CONFIG"
  --custom-generate-function-path repoharness2.adapters.miles.generate_fn.Rh2MilesGenerateFn
  --dynamic-sampling-filter-path miles.rollout.filter_hub.dynamic_sampling_filters.check_reward_nonzero_std
  --save-debug-rollout-data "$DUMPS/rollout_{rollout_id}.pt"
  # G1 eval 冒烟（B4）：eval-interval=NUM_ROLLOUT ⇒ 只在末轮（train+publish 之后）
  # 触发一次共享引擎 eval；1 prompt × 1 样本走完整 eval 路径并产出 eval_smoke 事件。
  --eval-interval "$NUM_ROLLOUT"
  --eval-prompt-data smoke "$EVAL_SMOKE_DATA"
  --n-samples-per-eval-prompt 1
)
LOSS_ARGS=(
  --loss-type custom_loss
  --custom-loss-function-path repoharness2.adapters.miles.faithful_dis_loss.faithful_dis_loss_function
  # F2 训练目标单一化（launch_args.md §3.1）：faithful DIS 是唯一目标。
  # 有意不带：--use-kl-loss / --use-opd / --enable-mtp-training / GSPO/TIS 组。
  --kl-coef 0.0
  --entropy-coef 0.0
)
if [ "$RH2_GPU_SPIKE_R3" = "on" ]; then
  LOSS_ARGS+=(--use-rollout-routing-replay)
fi
OPTIMIZER_ARGS=(
  --optimizer adam
  --lr 1e-6
  --lr-decay-style constant
  --weight-decay 0.1
  --adam-beta1 0.9
  --adam-beta2 0.98
)
PERF_ARGS=(
  --tensor-model-parallel-size "$TP"
  --sequence-parallel
  --pipeline-model-parallel-size "$PP"
  --context-parallel-size "$CP"
  --expert-model-parallel-size "$EP"
  --expert-tensor-parallel-size 1
  --recompute-granularity full
  --recompute-method uniform
  --recompute-num-layers 1
  --use-dynamic-batch-size
  --max-tokens-per-gpu "$MAX_TOKENS_PER_GPU"
)
SGLANG_ARGS=(
  # V3：显式启用 MilesRouter。这是 miles 一等 CLI 旗标（miles/utils/arguments.py
  # add_router_arguments，store_true 默认 False——所以必须显式带，custom_config
  # 不承载有一等旗标的键）。消费链：miles/ray/rollout/router_manager.py:40
  # start_router 据此起 MilesRouter（而非 sgl-router），engine 起动后向其
  # POST /add_worker 自注册（sglang_engine.py:317），rh2 adapter 的 sglang_url
  # 就是该 router 地址（rh2 bringup.py:662）。为什么必须：#2596 最新 fail-closed
  # ——rollout_top_p<1（本脚本 0.8）时 miles_validate_args 直接 ValueError
  # （arguments.py:2942-2948），理由是 SGLang model gateway 不转发
  # return_sampling_mask，sampling-support replay 的 mask 会被静默丢掉；PD 模式
  # 亦已撤销 mask 支持。MilesRouter 的 catch-all 代理按原始 body 转发
  # （router.py do_proxy content=body），顶层 return_sampling_mask 旗标可完整
  # 抵达引擎。
  --use-miles-router
  --rollout-num-gpus-per-engine "$ROLLOUT_GPUS_PER_ENGINE"
  --sglang-mem-fraction-static "${RH2_SGLANG_MEM_FRACTION:-0.7}"
  --sglang-max-running-requests 512
)
TOPO_ARGS=(
  --fully-async
  --actor-num-nodes 1
  --actor-num-gpus-per-node "$ACTOR_GPUS"
  --rollout-num-gpus "$ROLLOUT_GPUS"
  --update-weight-transfer-mode broadcast
  --moe-token-dispatcher-type alltoall
)
MISC_ARGS=(
  --attention-dropout 0.0
  --hidden-dropout 0.0
  --accumulate-allreduce-grads-in-fp32
  --attention-softmax-in-fp32
  --attention-backend flash
  --bf16
)

ALL_ARGS=("${CKPT_ARGS[@]}" "${ROLLOUT_ARGS[@]}" "${LOSS_ARGS[@]}" "${OPTIMIZER_ARGS[@]}"
  "${PERF_ARGS[@]}" "${SGLANG_ARGS[@]}" "${TOPO_ARGS[@]}" "${MISC_ARGS[@]}")

# 自检：禁带 flag 不得混入（训练目标单一化 + R3-off 语义 + CP=1）
FORBIDDEN=(--use-kl-loss --use-opd --enable-mtp-training --use-tis --advantage-estimator --eps-clip)
if [ "$RH2_GPU_SPIKE_R3" = "off" ]; then FORBIDDEN+=(--use-rollout-routing-replay --use-routing-replay); fi
for tok in "${ALL_ARGS[@]}"; do
  for bad in "${FORBIDDEN[@]}"; do
    [ "$tok" = "$bad" ] && die "禁带 flag 混入参数组：$bad"
  done
done
[ "$CP" = "1" ] || die "CP 必须为 1（faithful_dis CP>1 fail-closed）"

# P11. V3 router/replay/PD/engine 语义闸（对最终提交的 token 流断言，三模式都
#      执行——top_p<1 而 router 缺失这类组合在这里就红，不等 Ray/miles 启动）。
#      判据 = integration tree miles/utils/arguments.py miles_validate_args 同
#      判据（行号逐条注明）。不直接调用该函数：其 import 链需要 sglang_router
#      （arguments.py:8），本机 preflight venv 无此依赖；同判据镜像检查 + 行号
#      锚点是"本机可跑"约束下的替代，锚点漂移由 lanes 树 digest 钉住。
has_tok() { local t; for t in "${MODEL_ARGS[@]}" "${ALL_ARGS[@]}"; do [ "$t" = "$1" ] && return 0; done; return 1; }
# (a) sampling-support replay ⇒ 必须 MilesRouter + 正有限 top-k + 无 prefill 复算。
#     replay 开关 = rollout_top_p < 1.0（miles/utils/sampling.py:4，严格小于）；
#     三条 fail-closed 见 arguments.py:2931-2948（#2596 最新语义）。
if awk "BEGIN{exit !($ROLLOUT_TOP_P < 1.0)}"; then
  has_tok "--use-miles-router" \
    || die "rollout_top_p=$ROLLOUT_TOP_P <1.0 但参数组缺 --use-miles-router：#2596 fail-closed（SGLang model gateway 不转发 return_sampling_mask，arguments.py:2942-2948 启动时必 ValueError）——preflight 提前红"
  [ "$ROLLOUT_TOP_K" -ge 1 ] 2>/dev/null \
    || die "rollout_top_p=$ROLLOUT_TOP_P <1.0 要求正的 --rollout-top-k 以约束支持集（当前='$ROLLOUT_TOP_K'；arguments.py:2932-2936）"
  if has_tok "--recompute-logprobs-via-prefill"; then
    die "sampling-support replay 与 --recompute-logprobs-via-prefill 互斥（prefill 复算不保留 rollout 采样支持集；arguments.py:2937-2941）"
  fi
fi
# (b) qkv_format 必须 thd（防御断言）：launch 不带该旗标 = miles 默认 thd
#     （arguments.py:271-276 choices thd/bshd default thd）。#2798（BSHD 下
#     B>1 时 R3 tape token 排序错）未吸收，THD 是 R3 tape 语义前提——bshd
#     出现属换实验，先吸收该修复再谈。
QKV_SEEN=""
_prev=""
for tok in "${MODEL_ARGS[@]}" "${ALL_ARGS[@]}"; do
  case "$tok" in --qkv-format=*) QKV_SEEN="${tok#--qkv-format=}" ;; esac
  [ "$_prev" = "--qkv-format" ] && QKV_SEEN="$tok"
  _prev="$tok"
done
if [ -n "$QKV_SEEN" ] && [ "$QKV_SEEN" != "thd" ]; then
  die "qkv_format='$QKV_SEEN' ≠ thd：#2798 BSHD B>1 R3 tape 排序修复未吸收，THD 前提钉死（launch 缺省即 thd，谁显式改谁先补修复）"
fi
# (c) PD（prefill/decode 分离）必须关闭：#2596 已撤销 PD 的 sampling-mask
#     支持，且 MilesRouter 本身 assert 不支持 PD（router_manager.py:41）。
#     PD 的两个入口都不许出现：--prefill-num-servers（legacy 旗标，
#     sglang_config.py:170 from_prefill_num_servers）与 --sglang-config
#     （YAML server_groups 可声明 prefill/decode worker，sglang_config.py:95）。
for tok in "${MODEL_ARGS[@]}" "${ALL_ARGS[@]}"; do
  case "$tok" in
    --prefill-num-servers|--prefill-num-servers=*)
      die "参数组混入 --prefill-num-servers：PD 模式已撤销 sampling-mask 支持（#2596），MilesRouter 亦不支持 PD（router_manager.py:41）" ;;
    --sglang-config|--sglang-config=*)
      die "参数组混入 --sglang-config：server_groups 可引入 PD/多模型 worker（sglang_config.py:95），首训钉死单模型 regular worker（engine 数只由 --rollout-num-gpus-per-engine 决定），禁用该入口" ;;
  esac
done
# (d) engine 拓扑合法性（W10 起只做整除与资源合法性，不再限制 engine 数）：
#     engine 数 = rollout_num_gpus // rollout_num_gpus_per_engine（rollout_server.py:49，
#     整数除法会静默丢余数卡）；per-engine 必须是正整数、不超过 rollout 卡数（单节点
#     拓扑，多节点 engine 不在首训范围）。
case "$ROLLOUT_GPUS_PER_ENGINE" in
  ''|*[!0-9]*) die "RH2_SPIKE_ROLLOUT_GPUS_PER_ENGINE='$ROLLOUT_GPUS_PER_ENGINE' 不是正整数" ;;
esac
[ "$ROLLOUT_GPUS_PER_ENGINE" -ge 1 ] \
  || die "per-engine 卡数必须 ≥ 1（当前 $ROLLOUT_GPUS_PER_ENGINE）"
[ "$ROLLOUT_GPUS_PER_ENGINE" -le "$ROLLOUT_GPUS" ] \
  || die "per-engine 卡数 $ROLLOUT_GPUS_PER_ENGINE 超过 rollout 卡数 $ROLLOUT_GPUS（单节点拓扑，一个 engine 不能跨出 rollout 卡集）"
[ $((ROLLOUT_GPUS % ROLLOUT_GPUS_PER_ENGINE)) -eq 0 ] \
  || die "rollout 卡数 $ROLLOUT_GPUS 不能被 per-engine $ROLLOUT_GPUS_PER_ENGINE 整除（miles 会静默丢余数卡或建错 engine 数）"
ENGINE_COUNT=$((ROLLOUT_GPUS / ROLLOUT_GPUS_PER_ENGINE))
[ "$ENGINE_COUNT" -ge 1 ] \
  || die "engine 数=$ENGINE_COUNT 不合法"

# P11 是 preflight 闭包的最后一段，成功宣告必须在它之后（P2 #2 排序修复）。
say "preflight 全部通过"

# ---------------------------------------------------------------- 输出/执行
if [ "$MODE" = "preflight" ]; then
  say "preflight 完成（未组装 GPU 作业）。dry-run 可查看完整命令。"
  exit 0
fi

TOTAL_GPUS=$((ACTOR_GPUS + ROLLOUT_GPUS))
if [ "$MODE" = "dry-run" ]; then
  say "== dry-run：完整启动命令（不提交）=="
  echo "ray job submit --address=http://127.0.0.1:8265 \\"
  echo "  --runtime-env-json='$RUNTIME_ENV_JSON' \\"
  echo "  -- python3 $MILES_ROOT/train_async.py \\"
  echo "  $MODEL_ARGS_STR \\"
  printf '  %s\n' "${ALL_ARGS[@]}"
  say "（model args 共 ${#MODEL_ARGS[@]} 个 token，经 eval 解析后按数组传给进程）"
  say "拓扑：${ACTOR_GPUS} train + ${ROLLOUT_GPUS} rollout（TP${TP}/PP${PP}/CP${CP}/EP${EP}；engine 数=${ENGINE_COUNT}，per-engine=${ROLLOUT_GPUS_PER_ENGINE} 卡 ⇒ sglang TP${ROLLOUT_GPUS_PER_ENGINE}；router=miles）"
  say "run 模式训练结束后将自动执行 post-run 闭环（identity 核对/checkpoint 存读删/shutdown 探针/collect/judge），退出码逐步记录在 $EV/postrun_status.json"
  exit 0
fi

# ---------------------------------------------------------------- run + post-run
# B4：launch 自身完成证据闭环——训练结束后自动执行 identity 核对、checkpoint
# 存/读/digest/删、shutdown/actor 探针、dmon 停止、collect、judge，并把每一步
# 退出码写入 postrun_status.json；不再打印人工步骤。
# P0-1：run root 必须是全新目录（unique run_id）。已存在（哪怕为空）即拒绝——
# 旧 evidence/checkpoint 与新 run 不得共享任何路径；失败重试 = 换新 run_id。
if [ -e "$RUN_ROOT" ]; then
  die "run root 已存在：${RUN_ROOT}——一个 run root 只绑定一次 run（P0-1）。重试请换 RH2_SPIKE_RUN_ID 或让脚本自动生成。"
fi
mkdir -p "$EV" "$EVENTS_DIR" "$ARTIFACTS" "$CKPT" "$DUMPS"
LOG="$EV/train.log"
{
  echo "mode=run run_id=$RUN_ID r3=$RH2_GPU_SPIKE_R3 topo=${ACTOR_GPUS}+${ROLLOUT_GPUS} tp=$TP pp=$PP cp=$CP ep=$EP engines=$ENGINE_COUNT per_engine=$ROLLOUT_GPUS_PER_ENGINE router=miles"
  echo "model_id=$RH2_MODEL_ID execution_mode=$RH2_EXECUTION_MODE (pre-formal,不翻闸门)"
  echo "prompt_data_sha256=$PROMPT_DATA_SHA_EXPECTED"
  echo "miles_tree_digest=$MILES_TREE_DIGEST"
  date -u +"started_utc=%Y-%m-%dT%H:%M:%SZ"
} | tee "$EV/launch_facts.txt"
printf '%s\n' "$MODEL_ARGS_STR" "${ALL_ARGS[@]}" > "$EV/launch_args_resolved.txt"
echo "$RUNTIME_ENV_JSON" > "$EV/runtime_env.json"

# P0-1：run manifest（Ray 启动前落盘）——verdict 绑定的不可变 run 事实：run_id、
# 本轮代码可确定的 root commit、miles tree（git tree + source digest，二者已在
# preflight 与审计 manifest 对齐）、阈值页 digest、关键运行参数。远程资产字段
# （镜像/wheel/模型 checkpoint 身份）按审查 §6 D6 留待下一轮随启动 profile 补充。
python3 - "$EV/run_manifest.json" <<PYEOF
import hashlib, json, subprocess, sys
manifest = {
    "run_id": "$RUN_ID",
    "root_commit": subprocess.run(
        ["git", "-C", "$ROOT", "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip() or None,
    "miles_root": "$MILES_ROOT",
    "miles_git_tree": "$MILES_GIT_TREE",
    "miles_source_tree_digest": "$MILES_TREE_DIGEST",
    "thresholds_sha256": hashlib.sha256(open("$SCRIPT_DIR/thresholds.md", "rb").read()).hexdigest(),
    "prompt_data_sha256": "$PROMPT_DATA_SHA_EXPECTED",
    "eval_smoke_sha256": "$EVAL_SMOKE_SHA_EXPECTED",
    "r3": "$RH2_GPU_SPIKE_R3",
    "execution_mode": "$RH2_EXECUTION_MODE",
    "topology": {"actor_gpus": $ACTOR_GPUS, "rollout_gpus": $ROLLOUT_GPUS,
                 "rollout_gpus_per_engine": $ROLLOUT_GPUS_PER_ENGINE,
                 "rollout_engines": $ENGINE_COUNT, "use_miles_router": True,
                 "tp": $TP, "pp": $PP, "cp": $CP, "ep": $EP,
                 "num_rollout": $NUM_ROLLOUT, "global_batch_size": $GLOBAL_BATCH_SIZE},
}
json.dump(manifest, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
PYEOF

# dmon 资源采样（后台；作业结束后停止）。无 nvidia-smi 时留缺口（judge 记 MISSING）。
DMON_PID=""
GPU_MEM_TOTAL_MB=""
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi dmon -s mu -d 5 -o T > "$EV/dmon.csv" 2>/dev/null &
  DMON_PID=$!
  GPU_MEM_TOTAL_MB="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' ')"
else
  say "WARN: 无 nvidia-smi，dmon 显存证据缺失（judge 将记 MISSING_EVIDENCE）"
fi

T0=$(date +%s)
set +e
ray job submit --address="http://127.0.0.1:8265" \
  --runtime-env-json="$RUNTIME_ENV_JSON" \
  -- python3 "$MILES_ROOT/train_async.py" \
  "${MODEL_ARGS[@]}" "${ALL_ARGS[@]}" 2>&1 | tee "$LOG"
RC=$?
set -e
T1=$(date +%s)
echo "wall_seconds=$((T1 - T0)) rc=$RC total_gpus=$TOTAL_GPUS" | tee -a "$EV/launch_facts.txt"

POSTRUN_STATUS="$EV/postrun_status.json"
echo "{\"train_rc\": $RC" > "$POSTRUN_STATUS.tmp"
postrun_step() { # $1=步骤名 $2...=命令；退出码记入 postrun_status.json，不中断后续步骤
  local name="$1"; shift
  local rc=0
  set +e
  "$@"
  rc=$?
  set -e
  echo ", \"$name\": $rc" >> "$POSTRUN_STATUS.tmp"
  say "post-run [$name] rc=$rc"
  return 0
}

# 1) dmon 停止
if [ -n "$DMON_PID" ]; then
  postrun_step dmon_stop kill "$DMON_PID"
fi

# 2) checkpoint 存/读/digest/删 探针（G1：save 由训练期 --save-interval 1 完成；
#    P0-2：DCP metadata 用 FileSystemReader 结构化反序列化——torch.load 读
#    .metadata 是确定性假红，已废弃。逻辑在 postrun_probes.py（可 pytest）。
postrun_step checkpoint_probe python3 "$SCRIPT_DIR/postrun_probes.py" checkpoint \
  --ckpt "$CKPT" --out "$EV/checkpoint_probe.json"

# 3) shutdown/actor 探针（P0-3B：查询失败显式非零，不冒充零孤儿；docker 用
#    preflight 验证过的二进制；s1_compat finalization 如实 not_applicable；
#    聚焦修复批 #4：rollout+grading 容器都查，--run-id 按本 run owner label
#    rh2.run_id=<RUN_ID> 精确归属）
postrun_step shutdown_probe python3 "$SCRIPT_DIR/postrun_probes.py" shutdown \
  --artifacts "$ARTIFACTS" --out "$EV/shutdown_probe.json" \
  --docker-bin "$DOCKER_CLI_DIR/docker" --execution-mode "$RH2_EXECUTION_MODE" \
  --run-id "$RUN_ID"

# 4) collect：结构化事件 -> 归一化证据（P0-1：--run-id 校验事件归属；输出到
#    collected/ 子目录，先写 .tmp 再原子发布——collect 失败不产出可判证据）
COLLECT_ARGS=(--events-dir "$EVENTS_DIR" --run-id "$RUN_ID" --out-dir "$EV/collected")
if [ -s "$EV/dmon.csv" ] && [ -n "$GPU_MEM_TOTAL_MB" ]; then
  COLLECT_ARGS+=(--dmon-csv "$EV/dmon.csv" --gpu-mem-total-mb "$GPU_MEM_TOTAL_MB")
fi
postrun_step collect python3 "$SCRIPT_DIR/g1_acceptance.py" collect "${COLLECT_ARGS[@]}"

# 5) judge：机器判定（PASS/FAIL/INCOMPLETE；run_identity/identity 一致性在内）
postrun_step judge python3 "$SCRIPT_DIR/g1_acceptance.py" judge \
  --evidence-dir "$EV" --thresholds "$SCRIPT_DIR/thresholds.md" \
  --r3 "$RH2_GPU_SPIKE_R3" --custom-config "$CUSTOM_CONFIG" --out "$EV/g1_verdict.json"

echo "}" >> "$POSTRUN_STATUS.tmp"
mv "$POSTRUN_STATUS.tmp" "$POSTRUN_STATUS"
say "post-run 完成；各步退出码：$(cat "$POSTRUN_STATUS")"
say "判定：$EV/g1_verdict.json；证据目录：$EV"
# P0-1 fail-closed：训练非零、或任一必需 post-run 步骤非零，整次 launch 非零退出
# （dmon_stop 是尽力步骤，不计入必需集合）。
FINAL_RC=$(python3 - "$POSTRUN_STATUS" "$RC" <<'PYEOF'
import json, sys
status = json.load(open(sys.argv[1]))
train_rc = int(sys.argv[2])
if train_rc != 0:
    print(train_rc)
elif any(status.get(step, 1) != 0 for step in ("checkpoint_probe", "shutdown_probe", "collect", "judge")):
    print(1)
else:
    print(0)
PYEOF
)
exit "$FINAL_RC"
