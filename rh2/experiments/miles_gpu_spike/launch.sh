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
#                              # 键在位、R3 显式选择合法）。本机可跑（用桩 asset）。
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
#   RH2_SPIKE_RUN_ROOT（证据/checkpoint 输出根）、拓扑组（见 §topo）。
#
# 硬钉死（本脚本内不可被环境覆盖——覆盖 = 换实验，应改脚本并留痕）：
#   RH2_MODEL_ID=Qwen/Qwen3-30B-A3B；RH2_EXECUTION_MODE=s1_compat（pre-formal，见下）；
#   RH2_REQUIRE_REAL_WEIGHT_VERSIONS=1、RH2_REJECT_CONTEXT_SHRINK=1、
#   RH2_REJECT_NONZERO_HARNESS_EXIT=1；RH2_EXPECT_MOE_ROUTING=1、
#   RH2_MOE_NUM_LAYERS=48、RH2_MOE_ROUTER_TOPK=8（HF config 核实：num_hidden_layers=48、
#   num_experts_per_tok=8、decoder_sparse_step=1 且 mlp_only_layers=[] ⇒ 48 层全 MoE；
#   与 miles scripts/models/qwen3-30B-A3B.py、slime scripts/models/qwen3-30B-A3B.sh 一致）；
#   MILES_EXPERIMENTAL_FT_TRAINER 必须不设（B6 锁定：实验 FT trainer 的 retry/部分失败
#   继续语义会吞掉 faithful DIS 的 fail-stop；loss 侧已 fail-closed，这里在启动层就不设）。
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
RUN_ROOT="${RH2_SPIKE_RUN_ROOT:-/root/miles_gpu_spike}"
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
  fail "eval 冒烟数据不存在：$EVAL_SMOKE_DATA（G1 eval 路径冒烟依赖）"
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

# P9c. integration tree digest（B3）：用与 miles worker 完全相同的函数
#      （miles.utils.rh2_event_log.miles_tree_digest，patch 0004）预计算钉死值。
#      该值经 runtime-env 下发（RH2_EXPECTED_MILES_TREE_DIGEST），每类 Ray actor
#      启动时自证一致，不一致当场 raise 停机；事件文件再由 post-run 汇总核对。
#      这里同时证明 $MILES_ROOT 树里确实带 rh2_event_log 模块（旧树立即红）。
MILES_TREE_DIGEST="$(PYTHONPATH="$MILES_ROOT" python3 -c \
  "from miles.utils.rh2_event_log import miles_tree_digest; print(miles_tree_digest())")" \
  || die "无法从 $MILES_ROOT 计算 miles tree digest（integration tree 缺 patch 0004 的 rh2_event_log 模块？）"
say "miles tree digest（钉死值）：$MILES_TREE_DIGEST"

# P10. 阈值/验收面在场（P0-6：不在租卡现场临时决定什么算通过）
[ -f "$SCRIPT_DIR/thresholds.md" ]    || fail "thresholds.md 不存在（P0-6 判定阈值单页）"
python3 "$SCRIPT_DIR/g1_acceptance.py" --self-test >/dev/null 2>&1 \
  || fail "g1_acceptance.py --self-test 未通过（验收判定器自身故障）"

if [ "$FAIL" -ne 0 ]; then
  die "preflight 未通过（见上方 FAIL 各行）——不满足 GPU 启动闭包"
fi
say "preflight 全部通过"

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
  say "拓扑：${ACTOR_GPUS} train + ${ROLLOUT_GPUS} rollout（TP${TP}/PP${PP}/CP${CP}/EP${EP}，engine=${ROLLOUT_GPUS_PER_ENGINE}）"
  say "run 模式训练结束后将自动执行 post-run 闭环（identity 核对/checkpoint 存读删/shutdown 探针/collect/judge），退出码逐步记录在 $EV/postrun_status.json"
  exit 0
fi

# ---------------------------------------------------------------- run + post-run
# B4：launch 自身完成证据闭环——训练结束后自动执行 identity 核对、checkpoint
# 存/读/digest/删、shutdown/actor 探针、dmon 停止、collect、judge，并把每一步
# 退出码写入 postrun_status.json；不再打印人工步骤。
mkdir -p "$EV" "$EVENTS_DIR" "$ARTIFACTS" "$CKPT" "$DUMPS"
LOG="$EV/train.log"
{
  echo "mode=run r3=$RH2_GPU_SPIKE_R3 topo=${ACTOR_GPUS}+${ROLLOUT_GPUS} tp=$TP pp=$PP cp=$CP ep=$EP"
  echo "model_id=$RH2_MODEL_ID execution_mode=$RH2_EXECUTION_MODE (pre-formal,不翻闸门)"
  echo "prompt_data_sha256=$PROMPT_DATA_SHA_EXPECTED"
  echo "miles_tree_digest=$MILES_TREE_DIGEST"
  date -u +"started_utc=%Y-%m-%dT%H:%M:%SZ"
} | tee "$EV/launch_facts.txt"
printf '%s\n' "$MODEL_ARGS_STR" "${ALL_ARGS[@]}" > "$EV/launch_args_resolved.txt"
echo "$RUNTIME_ENV_JSON" > "$EV/runtime_env.json"

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
#    这里做结构化 reload（读 tracker + 迭代目录清单 + torch dist-ckpt metadata
#    反序列化）、digest 记录，然后删除——探针 checkpoint 不作任何后续起点）
postrun_step checkpoint_probe python3 - "$CKPT" "$EV/checkpoint_probe.json" <<'PYEOF'
import hashlib, json, sys
from pathlib import Path

ckpt, out = Path(sys.argv[1]), Path(sys.argv[2])
probe = {"saved": False, "reloaded": False, "deleted": False,
         "reload_mode": "tracker+file-manifest+dist_ckpt_metadata", "digest": None, "note": None}
tracker = ckpt / "latest_checkpointed_iteration.txt"
iters = sorted(p for p in ckpt.glob("iter_*") if p.is_dir())
if tracker.is_file() and iters:
    probe["saved"] = True
    latest = iters[-1]
    files = sorted(p for p in latest.rglob("*") if p.is_file())
    digest = hashlib.sha256()
    digest.update(tracker.read_bytes())
    for p in files:
        digest.update(str(p.relative_to(ckpt)).encode())
        digest.update(str(p.stat().st_size).encode())
    probe["digest"] = digest.hexdigest()
    probe["num_files"] = len(files)
    meta = latest / ".metadata"
    try:
        if meta.is_file():
            import torch  # noqa: PLC0415 - GPU 机在场；结构化反序列化验证可读性
            torch.load(meta, map_location="cpu", weights_only=False)
            probe["reloaded"] = True
        else:
            # 非 torch_dist 布局：以 common.pt / 首个 .pt 可反序列化为 reload 判据
            cand = next((p for p in files if p.suffix == ".pt"), None)
            if cand is not None:
                import torch  # noqa: PLC0415
                torch.load(cand, map_location="cpu", weights_only=False)
                probe["reloaded"] = True
            else:
                probe["note"] = "未找到 .metadata/.pt，无法结构化 reload"
    except Exception as exc:  # noqa: BLE001 - 探针如实记录失败，不吞
        probe["note"] = f"reload 失败: {exc!r}"
else:
    probe["note"] = f"tracker={tracker.is_file()} iter_dirs={len(iters)}"
if probe["saved"] and probe["reloaded"]:
    import shutil
    shutil.rmtree(ckpt)
    probe["deleted"] = not ckpt.exists()
out.write_text(json.dumps(probe, ensure_ascii=False, indent=1))
print(json.dumps(probe, ensure_ascii=False))
sys.exit(0 if (probe["saved"] and probe["reloaded"] and probe["deleted"]) else 1)
PYEOF

# 3) shutdown/actor 探针：孤儿 rollout 容器 + 存活 ray actor + 未终结交付
postrun_step shutdown_probe python3 - "$ARTIFACTS" "$EV/shutdown_probe.json" <<'PYEOF'
import json, subprocess, sys
from pathlib import Path

artifacts, out = Path(sys.argv[1]), Path(sys.argv[2])
probe = {"orphan_workers": 0, "unfinalized_deliveries": 0, "detail": {}}

# 孤儿 sandbox 容器（rh2 DockerSandbox 容器名前缀 rh2-rollout）
try:
    r = subprocess.run(["docker", "ps", "--filter", "name=rh2-rollout", "--format", "{{.Names}}"],
                       capture_output=True, text=True, timeout=30)
    names = [x for x in r.stdout.splitlines() if x.strip()]
    probe["orphan_workers"] += len(names)
    probe["detail"]["docker_containers"] = names
except Exception as exc:  # noqa: BLE001
    probe["detail"]["docker_error"] = repr(exc)

# 作业结束后仍存活的 miles Ray actor（ray CLI 在场时）
try:
    r = subprocess.run(["ray", "list", "actors", "--filter", "state=ALIVE", "--format", "json"],
                       capture_output=True, text=True, timeout=60)
    if r.returncode == 0:
        alive = [a.get("class_name") for a in json.loads(r.stdout or "[]")]
        miles_alive = [c for c in alive if c and ("Train" in c or "Rollout" in c or "SGLang" in c)]
        probe["orphan_workers"] += len(miles_alive)
        probe["detail"]["ray_actors_alive"] = miles_alive
    else:
        probe["detail"]["ray_list_rc"] = r.returncode
except Exception as exc:  # noqa: BLE001
    probe["detail"]["ray_error"] = repr(exc)

# 未终结交付：bringup FileFinalizationStore 布局 attempts/<key>/receipt.json
attempts = artifacts / "finalization" / "attempts"
if attempts.is_dir():
    unfinalized = [p.name for p in attempts.iterdir() if p.is_dir() and not (p / "receipt.json").is_file()]
    probe["unfinalized_deliveries"] = len(unfinalized)
    probe["detail"]["unfinalized_attempts"] = unfinalized[:20]
else:
    probe["detail"]["finalization_store"] = "absent"
out.write_text(json.dumps(probe, ensure_ascii=False, indent=1))
print(json.dumps(probe, ensure_ascii=False))
sys.exit(0 if probe["orphan_workers"] == 0 and probe["unfinalized_deliveries"] == 0 else 1)
PYEOF

# 4) collect：结构化事件 -> 归一化证据（含 identity 汇总核对：actor_identity.json）
COLLECT_ARGS=(--events-dir "$EVENTS_DIR" --out-dir "$EV")
if [ -s "$EV/dmon.csv" ] && [ -n "$GPU_MEM_TOTAL_MB" ]; then
  COLLECT_ARGS+=(--dmon-csv "$EV/dmon.csv" --gpu-mem-total-mb "$GPU_MEM_TOTAL_MB")
fi
postrun_step collect python3 "$SCRIPT_DIR/g1_acceptance.py" collect "${COLLECT_ARGS[@]}"

# 5) judge：机器判定（PASS/FAIL/INCOMPLETE；identity 一致性是其中一项检查）
postrun_step judge python3 "$SCRIPT_DIR/g1_acceptance.py" judge \
  --evidence-dir "$EV" --thresholds "$SCRIPT_DIR/thresholds.md" \
  --r3 "$RH2_GPU_SPIKE_R3" --custom-config "$CUSTOM_CONFIG" --out "$EV/g1_verdict.json"

echo "}" >> "$POSTRUN_STATUS.tmp"
mv "$POSTRUN_STATUS.tmp" "$POSTRUN_STATUS"
say "post-run 完成；各步退出码：$(cat "$POSTRUN_STATUS")"
say "判定：$EV/g1_verdict.json；证据目录：$EV"
if [ "$RC" -ne 0 ]; then
  exit "$RC"
fi
JUDGE_RC=$(python3 -c "import json;print(json.load(open('$POSTRUN_STATUS')).get('judge', 1))")
exit "$JUDGE_RC"
