"""E5（第六组 I24 / I27 / I28 / I30）：actor 额外 logprob forward 的诊断 / 效率两份配置——只从**最终 args** 推导（纯函数）。

背景（fork ``reference/miles-rh2-integration`` HEAD 275e31eb2）：``train_actor`` 在优势计算之前的额外 forward-only
（``compute_log_prob(store_prefix="")``）只在下式为真时运行（``miles/backends/megatron_utils/actor.py`` 第 600、625–627 行）::

    compute_advantages_and_returns and not skip_actor_forward_only and (not use_rollout_logprobs or get_mismatch_metrics)

本配方（GRPO + faithful DIS + ``--kl-coef 0``，``rh2/experiments/miles_gpu_spike/launch.sh`` 的 LOSS_ARGS）只认两份配置：

- ``diagnostic``（诊断档）= 当前配方，三个开关 ``--use-rollout-logprobs`` / ``--get-mismatch-metrics`` /
  ``--skip-actor-forward-only`` 都不设：额外 forward 运行，产生同版本对拍事件 ``logprob_compare``、R3 下的
  ``replay_consume{phase=logprob_forward}``，以及 miles 指标 ``rollout/log_probs``、``perf/log_probs_time``、
  ``perf/log_probs_tflops``。G1 parity 只在这一档给结论。
- ``efficiency``（效率档）= 当前配方**只多** ``--use-rollout-logprobs``：额外 forward 不跑，上面这些观测**按配置不可用**
  （不是零，也不是缺证据）；训练 replay 的 ``replay_fill`` / ``replay_consume{phase=train_step}`` / ``replay_exhausted``
  照发，消费者照常检查。
- 其余一律 ``unsupported``（fail-closed）：``--skip-actor-forward-only`` 在本配方启动即 assert（``custom_loss`` 且每轮 2 个
  optimizer step，``miles/utils/arguments.py`` 第 3585–3647 行）；``--get-mismatch-metrics`` 只会重开 forward，mismatch / TIS
  指标只在 ``policy_loss_function`` 里产生，本配方没有消费者（还强制 ``--custom-tis-function-path``，第 3196–3199 行）。
  效率档另外拒绝所有"会读额外 forward 的输出、或让 ``--use-rollout-logprobs`` 改变语义"的开关（见 ``_efficiency_guard``）。

唯一事实来源是**最终 args**：进程内是 miles 解析、校验后的 args 对象（``derive_from_namespace``）；shell 启动器是即将提交给
``train_async.py`` 的 token 流（``derive_from_tokens``：镜像 miles 缺省值与 ``miles_validate_args`` 里改写这些键的三处）。
启动器的 profile 旋钮只决定是否追加那一个开关；启动证据写的是本模块的推导结果，旋钮字符串本身不进证据（Codex 复核 §4
第 3 条）。消费者（``run_report``、G1 judge）读回证据时用 ``interpret_recorded`` 按同一函数重算并核对，不另写一套判断。

只依赖标准库：``launch.sh`` 用系统 python3 按文件路径直接执行本文件（不经过 ``repoharness2.adapters.miles`` 的包
``__init__``，那里会拉起 canonicalize 等重依赖），G1 judge 也按文件路径加载它。
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FORWARD_PROFILE_SCHEMA_ID = "rh2.forward_profile.v1"

DIAGNOSTIC = "diagnostic"
EFFICIENCY = "efficiency"
UNSUPPORTED = "unsupported"
PROFILES: tuple[str, ...] = (DIAGNOSTIC, EFFICIENCY)

EFFICIENCY_FLAG = "--use-rollout-logprobs"
FAITHFUL_DIS_LOSS_PATH = "repoharness2.adapters.miles.faithful_dis_loss.faithful_dis_loss_function"
# 与 actor.py 第 600、625–627 行同一公式（外层 if 加上内层条件）；原文进证据，便于人工核对
FORWARD_CONDITION = (
    "compute_advantages_and_returns and not skip_actor_forward_only "
    "and (not use_rollout_logprobs or get_mismatch_metrics)"
)

# 额外 forward 关闭时按配置不可用的观测（消费者按这些名字对照；Brief §2 / 调查 §2.6）
OBS_LOGPROB_COMPARE = "rh2_event:logprob_compare"  # actor.py:664-665（只由 pp 末段 rank 发）
OBS_REPLAY_CONSUME_LOGPROB_FORWARD = "rh2_event:replay_consume{phase=logprob_forward}"  # actor.py:628-662（R3 才有）
OBS_MILES_ROLLOUT_LOG_PROBS = "miles_metric:rollout/log_probs"  # log_utils.py:224-248（actor.py:689 调用）
OBS_MILES_LOG_PROBS_TIME = "miles_metric:perf/log_probs_time"  # actor.py:388 timer
OBS_MILES_LOG_PROBS_TFLOPS = "miles_metric:perf/log_probs_tflops"  # train_metric_utils.py:35-36


class ForwardProfileError(RuntimeError):
    """配置不在两份支持档内、或启动证据与推导不一致（reason_code 机器可读）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


@dataclass(frozen=True)
class _Option:
    dest: str
    option: str
    kind: str  # store_true | store_false | str | float
    default: Any


# fork miles/utils/arguments.py 的镜像（行号 = add_argument 所在行；缺省值与 dest 由测试按 AST 逐项对照 fork 源码）。
TRACKED_OPTIONS: tuple[_Option, ...] = (
    # 三个 forward 开关
    _Option("use_rollout_logprobs", "--use-rollout-logprobs", "store_true", False),  # :1547
    _Option("get_mismatch_metrics", "--get-mismatch-metrics", "store_true", False),  # :1532
    _Option("skip_actor_forward_only", "--skip-actor-forward-only", "store_true", False),  # :1556
    # forward 条件的外层门（actor.py:600）
    _Option("compute_advantages_and_returns", "--disable-compute-advantages-and-returns", "store_false", True),  # :1467
    # 配方身份与效率档守卫
    _Option("loss_type", "--loss-type", "str", "policy_loss"),  # :1425
    _Option("custom_loss_function_path", "--custom-loss-function-path", "str", None),  # :1435
    _Option("advantage_estimator", "--advantage-estimator", "str", "grpo"),  # :1451
    _Option("kl_coef", "--kl-coef", "float", 0.0),  # :1419
    _Option("use_kl_loss", "--use-kl-loss", "store_true", False),  # :1477
    _Option("kl_loss_coef", "--kl-loss-coef", "float", 0.0),  # :1480
    _Option("normalize_advantages", "--normalize-advantages", "store_true", False),  # :1500
    _Option("use_tis", "--use-tis", "store_true", False),  # :1568
    _Option("custom_tis_function_path", "--custom-tis-function-path", "str", None),  # :1586
    _Option("use_opd", "--use-opd", "store_true", False),  # :1645
    _Option("keep_old_actor", "--keep-old-actor", "store_true", False),  # :826
    _Option("use_rollout_entropy", "--use-rollout-entropy", "store_true", False),  # :1514
    _Option("log_correct_samples", "--log-correct-samples", "store_true", False),  # :1993
    _Option("save_debug_train_data", "--save-debug-train-data", "str", None),  # :2115
    _Option("dump_details", "--dump-details", "str", None),  # :2125
    _Option("rollout_data_postprocess_path", "--rollout-data-postprocess-path", "str", None),  # :832
    _Option(
        "custom_megatron_before_log_prob_hook_path", "--custom-megatron-before-log-prob-hook-path", "str", None
    ),  # :2468
    _Option("use_routing_replay", "--use-routing-replay", "store_true", False),
    _Option("use_rollout_routing_replay", "--use-rollout-routing-replay", "store_true", False),
    _Option("use_indexer_replay", "--use-indexer-replay", "store_true", False),
    _Option("use_rollout_indexer_replay", "--use-rollout-indexer-replay", "store_true", False),
)
# use_critic 不是 CLI 开关：miles_validate_args 第 3256 行由 advantage_estimator 派生
TRACKED_DESTS: tuple[str, ...] = tuple(o.dest for o in TRACKED_OPTIONS) + ("use_critic",)
CUSTOM_CONFIG_OPTION = "--custom-config-path"  # arguments.py:2679-2685（reset_arg）；YAML 在全部校验之后逐键 setattr（第 3534–3539 行）
PSEUDO_FILE_PREFIX = "base64:"  # miles/utils/file_arg_utils.py:4-11：值可以是文件路径，也可以是内联 base64 载荷

_BOOL_DESTS = frozenset({o.dest for o in TRACKED_OPTIONS if o.kind in ("store_true", "store_false")} | {"use_critic"})
_FLOAT_DESTS = frozenset(o.dest for o in TRACKED_OPTIONS if o.kind == "float")
_STR_DESTS = frozenset(o.dest for o in TRACKED_OPTIONS if o.kind == "str")


def _reason(code: str, detail: str) -> dict[str, str]:
    return {"code": code, "detail": detail}


# ---------------------------------------------------------------------------
# 最终 args -> 追踪键的值
# ---------------------------------------------------------------------------


def _apply_miles_post_parse(values: dict[str, Any]) -> None:
    """``miles_validate_args`` 里改写追踪键的三处（token 流镜像才需要；进程内 args 已经过这一步）。"""

    if values["dump_details"] is not None:  # arguments.py:3234-3237
        values["save_debug_train_data"] = f"{values['dump_details']}/train_data/{{rollout_id}}_{{rank}}.pt"
    values["use_critic"] = values["advantage_estimator"] == "ppo"  # arguments.py:3256
    if values["use_rollout_routing_replay"]:  # arguments.py:3531-3532
        values["use_routing_replay"] = True
    if values["use_rollout_indexer_replay"]:  # arguments.py:3541-3542
        values["use_indexer_replay"] = True


def scan_custom_config_text(text: str) -> list[str]:
    """custom config YAML 里出现的追踪键（保守：非注释行里整词出现即算，不解析 YAML）。

    miles 在全部参数校验之后把 YAML 顶层键逐个 setattr 到 args（arguments.py:3534-3539），能绕过 CLI 与
    miles 自身的断言；launch.sh 的 P6b 白名单已挡住，这里是推导函数自己的第二道 fail-closed。
    """

    hits: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        body = re.split(r"\s#", raw, maxsplit=1)[0]
        for dest in TRACKED_DESTS:
            if re.search(rf"(?<![A-Za-z0-9_]){re.escape(dest)}(?![A-Za-z0-9_])", body) and dest not in hits:
                hits.append(dest)
    return hits


def _read_custom_config(value: str) -> str:
    """与 miles ``resolve_file_arg`` 同一读法（file_arg_utils.py:7-11）。"""

    if value.startswith(PSEUDO_FILE_PREFIX):
        return base64.b64decode(value[len(PSEUDO_FILE_PREFIX):], validate=True).decode()
    return Path(value).read_text(encoding="utf-8")


def parse_final_args(
    tokens: Sequence[str], *, custom_config_reader=None
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """把即将提交的 token 流解析成追踪键的值 + 输入层问题清单（非空即 unsupported）。

    只认精确选项名与 ``--opt=value``；store_true 带值、缺值、裸 ``--`` 都记为输入层问题——最终值不确定时不猜。
    同一个带值选项出现多次按 argparse 取最后一次。缩写拼写不单独识别：miles 经 Megatron ``parse_args`` 解析
    （``miles/backends/megatron_utils/arguments.py:5``），Megatron 的解析器是 ``allow_abbrev=False``（本机无 Megatron
    源码；``reference/verl/verl/workers/engine/mindspeed/utils.py:149`` 照抄的同名解析器是这一设置，属间接证据），
    缩写会在启动时报"无法识别的参数"而不是静默打开追踪开关。按前缀猜缩写会把 Megatron 的 ``--save`` 误判成
    ``--save-debug-train-data`` 的缩写，所以不做。
    ``custom_config_reader(path) -> str``：读 ``--custom-config-path`` 的 YAML（缺省与 miles 同读法：文件或 ``base64:`` 内联）。
    """

    by_option = {o.option: o for o in TRACKED_OPTIONS}
    values: dict[str, Any] = {o.dest: o.default for o in TRACKED_OPTIONS}
    reasons: list[dict[str, str]] = []
    config_paths: list[str] = []
    toks = [str(t) for t in tokens]
    i = 0
    while i < len(toks):
        tok = toks[i]
        i += 1
        if tok == "--":
            reasons.append(_reason("token_stream_end_of_options", "token 流里出现裸 '--'：其后的 token 在 argparse 里全是位置参数，最终值不确定"))
            break
        if not tok.startswith("--"):
            continue
        name, eq, inline = tok.partition("=")
        if name == CUSTOM_CONFIG_OPTION or name in by_option:
            opt = by_option.get(name)
            if opt is not None and opt.kind in ("store_true", "store_false"):
                if eq:
                    reasons.append(_reason("flag_given_value", f"{tok!r}：{name} 是开关，不接受值（miles 启动会报错）"))
                    continue
                values[opt.dest] = opt.kind == "store_true"
                continue
            if eq:
                value = inline
            elif i < len(toks) and not toks[i].startswith("--"):
                value = toks[i]
                i += 1
            else:
                reasons.append(_reason("option_missing_value", f"{name} 后面没有值（miles 启动会报错）"))
                continue
            if opt is None:
                config_paths.append(value)
            elif opt.kind == "float":
                try:
                    values[opt.dest] = float(value)
                except ValueError:
                    reasons.append(_reason("option_value_not_float", f"{name}={value!r} 不是数"))
            else:
                values[opt.dest] = value
    _apply_miles_post_parse(values)
    if config_paths:
        path = config_paths[-1]
        try:
            text = custom_config_reader(path) if custom_config_reader else _read_custom_config(path)
        except (OSError, UnicodeDecodeError, binascii.Error, ValueError) as exc:
            reasons.append(_reason("custom_config_unreadable", f"读不到 {CUSTOM_CONFIG_OPTION} {path!r}：{exc}"))
        else:
            for key in scan_custom_config_text(text):
                reasons.append(_reason(
                    "custom_config_sets_tracked_key",
                    f"custom config 设了 {key!r}：miles 在全部校验之后才逐键 setattr，最终值会被改写（arguments.py:3534-3539）",
                ))
    return values, reasons


# ---------------------------------------------------------------------------
# 推导
# ---------------------------------------------------------------------------


def _efficiency_guard(v: Mapping[str, Any]) -> list[dict[str, str]]:
    """效率档只对当前配方成立：凡是读额外 forward 的输出、或让 --use-rollout-logprobs 改变语义的开关一律拒绝。"""

    out: list[dict[str, str]] = []

    def reject(cond: bool, code: str, detail: str) -> None:
        if cond:
            out.append(_reason(code, detail))

    reject(v["loss_type"] != "custom_loss", "efficiency_requires_custom_loss",
           f"--loss-type={v['loss_type']!r}：policy_loss 下 --use-rollout-logprobs 会改用 rollout logprob 作 old baseline"
           "（losses.py），是另一种算法；效率档只对 faithful DIS 验证过")
    reject(v["custom_loss_function_path"] != FAITHFUL_DIS_LOSS_PATH, "efficiency_requires_faithful_dis",
           f"--custom-loss-function-path={v['custom_loss_function_path']!r} 不是 {FAITHFUL_DIS_LOSS_PATH}")
    reject(v["advantage_estimator"] != "grpo", "efficiency_requires_grpo",
           f"--advantage-estimator={v['advantage_estimator']!r}：等价性只对 GRPO（returns = 形状 × 训练 reward 列）成立")
    reject(bool(v["use_critic"]), "efficiency_rejects_ppo_critic", "use_critic（PPO / GAE 价值面）不在本配方")
    reject(v["kl_coef"] != 0, "efficiency_rejects_kl_reward_shaping",
           f"--kl-coef={v['kl_coef']}：KL 奖励整形会改用 rollout logprob 对 ref 求 KL（loss.py:84-99）")
    reject(bool(v["use_kl_loss"]) or v["kl_loss_coef"] != 0, "efficiency_rejects_kl_loss",
           "--use-kl-loss / --kl-loss-coef≠0：KL loss 需要 ref forward，且只在 policy_loss 里消费")
    reject(bool(v["use_opd"]), "efficiency_rejects_opd", "--use-opd：OPD 的 student logprob 会变成 rollout logprob（loss.py:111-117）")
    reject(bool(v["use_tis"]), "efficiency_rejects_tis", "--use-tis：与 --use-rollout-logprobs 互斥（arguments.py:3193-3194），且只在 policy_loss 消费")
    reject(v["custom_tis_function_path"] is not None, "efficiency_rejects_custom_tis", "--custom-tis-function-path：只在 policy_loss 的 mismatch / TIS 路径消费")
    reject(bool(v["keep_old_actor"]), "efficiency_rejects_keep_old_actor", "--keep-old-actor：为额外 forward 切换 old_actor 权重（actor.py:624），效率档无此 forward")
    reject(bool(v["normalize_advantages"]), "efficiency_rejects_normalize_advantages",
           "--normalize-advantages：不在本配方；效率档下非末级 PP stage 也会算优势并进入白化的集合通信（loss.py:119-120）")
    reject(bool(v["use_rollout_entropy"]), "efficiency_rejects_rollout_entropy", "--use-rollout-entropy：entropy 只在额外 forward 里算")
    reject(bool(v["log_correct_samples"]), "efficiency_rejects_log_correct_samples", "--log-correct-samples：读 rollout_data['log_probs']，效率档 KeyError（log_utils.py:345）")
    reject(v["save_debug_train_data"] is not None, "efficiency_rejects_debug_train_dump",
           "--save-debug-train-data / --dump-details：训练数据 dump 会静默缺 log_probs（actor.py:710）")
    reject(v["rollout_data_postprocess_path"] is not None, "efficiency_rejects_rollout_data_postprocess",
           "--rollout-data-postprocess-path：自定义代码在拿到 log_probs 之后调用（actor.py:686-687），效率档没有 log_probs")
    reject(v["custom_megatron_before_log_prob_hook_path"] is not None, "efficiency_rejects_before_log_prob_hook",
           "--custom-megatron-before-log-prob-hook-path：钩子挂在 forward-only 里（model.py:375-378），效率档不再调用")
    reject(bool(v["use_routing_replay"]) and not v["use_rollout_routing_replay"], "efficiency_rejects_record_routing_replay",
           "--use-routing-replay（非 rollout 回放）：路由由额外 forward 记录（stage=record）再给训练回放，效率档无记录")
    reject(bool(v["use_indexer_replay"]) and not v["use_rollout_indexer_replay"], "efficiency_rejects_record_indexer_replay",
           "--use-indexer-replay（非 rollout 回放）：同上")
    return out


def _derive(values: Mapping[str, Any], *, source: str, input_reasons: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    use_rollout = bool(values["use_rollout_logprobs"])
    mismatch = bool(values["get_mismatch_metrics"])
    skip = bool(values["skip_actor_forward_only"])
    compute_adv = bool(values["compute_advantages_and_returns"])
    forward = compute_adv and not skip and (not use_rollout or mismatch)

    reasons: list[dict[str, str]] = [dict(r) for r in input_reasons]
    if not compute_adv:
        reasons.append(_reason("advantages_disabled",
                               "--disable-compute-advantages-and-returns：额外 forward 与优势都不算（actor.py:600），faithful DIS 缺 advantages 列"))
    if skip:
        reasons.append(_reason("skip_actor_forward_only_incompatible",
                               "--skip-actor-forward-only 要求 loss_type=policy_loss 且每轮恰 1 个 optimizer step"
                               "（arguments.py:3585-3647）；本配方 custom_loss 且每轮 2 步，启动即 assert"))
    if mismatch:
        reasons.append(_reason("get_mismatch_metrics_no_consumer",
                               "--get-mismatch-metrics 只会重开额外 forward（actor.py:626），mismatch / TIS 指标只在 policy_loss 里产生，"
                               "本配方没有消费者，且强制 --custom-tis-function-path（arguments.py:3196-3199）"))
    if use_rollout and not skip and not mismatch:
        reasons.extend(_efficiency_guard(values))
    if reasons:
        profile = UNSUPPORTED
    else:
        profile = EFFICIENCY if use_rollout else DIAGNOSTIC

    rollout_replay = {
        "routing": bool(values["use_rollout_routing_replay"]),
        "indexer": bool(values["use_rollout_indexer_replay"]),
    }
    unavailable: list[str] = []
    if not forward:
        unavailable.append(OBS_LOGPROB_COMPARE)
        if rollout_replay["routing"] or rollout_replay["indexer"]:
            unavailable.append(OBS_REPLAY_CONSUME_LOGPROB_FORWARD)
        unavailable += [OBS_MILES_ROLLOUT_LOG_PROBS, OBS_MILES_LOG_PROBS_TIME, OBS_MILES_LOG_PROBS_TFLOPS]
    return {
        "schema_id": FORWARD_PROFILE_SCHEMA_ID,
        "source": source,
        "profile": profile,
        "extra_logprob_forward": forward,
        "switches": {
            "use_rollout_logprobs": use_rollout,
            "get_mismatch_metrics": mismatch,
            "skip_actor_forward_only": skip,
        },
        "rollout_replay": rollout_replay,
        "unavailable_observations": unavailable,
        "unsupported_reasons": reasons,
        "input_reasons": [dict(r) for r in input_reasons],
        "args": {dest: values[dest] for dest in TRACKED_DESTS},
        "forward_condition": FORWARD_CONDITION,
    }


def derive_from_tokens(tokens: Sequence[str], *, custom_config_reader=None) -> dict[str, Any]:
    """shell 启动器入口：tokens = 即将提交给 train_async.py 的完整参数（model args + 其余参数）。"""

    values, input_reasons = parse_final_args(tokens, custom_config_reader=custom_config_reader)
    return _derive(values, source="final_args_tokens", input_reasons=input_reasons)


def derive_from_namespace(args: Any) -> dict[str, Any]:
    """进程内入口：miles 解析并校验后的 args（custom config 已 setattr）。缺任一追踪键即 unsupported（不按缺省猜）。"""

    values: dict[str, Any] = {}
    input_reasons: list[dict[str, str]] = []
    defaults = {o.dest: o.default for o in TRACKED_OPTIONS}
    for dest in TRACKED_DESTS:
        if hasattr(args, dest):
            values[dest] = getattr(args, dest)
        else:
            input_reasons.append(_reason("args_attribute_missing", f"args 缺 {dest!r}：不是 miles 校验后的 args，最终值不确定"))
            values[dest] = defaults.get(dest, False)
    return _derive(values, source="args_namespace", input_reasons=input_reasons)


def require_supported(block: Mapping[str, Any], *, expect: str | None = None) -> None:
    """启动期闸：unsupported 或与旋钮期望不符即抛（旋钮只用于这一处比对，不进证据）。"""

    if block["profile"] == UNSUPPORTED:
        codes = ", ".join(r["code"] for r in block["unsupported_reasons"])
        raise ForwardProfileError("forward_profile_unsupported", f"最终 args 不在诊断 / 效率两档内：{codes}")
    if expect is not None and block["profile"] != expect:
        raise ForwardProfileError(
            "forward_profile_mismatch",
            f"旋钮期望 {expect!r}，最终 args 推导为 {block['profile']!r}（证据以最终 args 为准；参数表被旋钮以外的地方改过）",
        )


# ---------------------------------------------------------------------------
# 消费者：读回启动证据
# ---------------------------------------------------------------------------

_DERIVED_KEYS = ("profile", "extra_logprob_forward", "switches", "rollout_replay", "unavailable_observations", "unsupported_reasons")


def _check_recorded_args(args: Any) -> dict[str, Any]:
    if not isinstance(args, Mapping):
        raise ForwardProfileError("recorded_block_invalid", "forward_profile.args 不是对象")
    missing = [d for d in TRACKED_DESTS if d not in args]
    if missing:
        raise ForwardProfileError("recorded_block_invalid", f"forward_profile.args 缺 {missing}")
    for dest in TRACKED_DESTS:
        value = args[dest]
        if dest in _BOOL_DESTS and not isinstance(value, bool):
            raise ForwardProfileError("recorded_block_invalid", f"args.{dest}={value!r} 不是布尔")
        if dest in _FLOAT_DESTS and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise ForwardProfileError("recorded_block_invalid", f"args.{dest}={value!r} 不是数")
        if dest in _STR_DESTS and value is not None and not isinstance(value, str):
            raise ForwardProfileError("recorded_block_invalid", f"args.{dest}={value!r} 不是字符串或 null")
    return dict(args)


def interpret_recorded(block: Any) -> dict[str, Any]:
    """校验启动证据里的 forward_profile 块：按记录的 args 与输入层问题用同一函数重算，推导字段必须逐项相同。

    返回重算结果；块缺字段、类型不对或与重算不一致一律抛 ForwardProfileError（消费者据此 fail-closed）。
    """

    if not isinstance(block, Mapping):
        raise ForwardProfileError("recorded_block_invalid", f"forward_profile 不是对象：{type(block).__name__}")
    if block.get("schema_id") != FORWARD_PROFILE_SCHEMA_ID:
        raise ForwardProfileError("recorded_block_invalid", f"schema_id={block.get('schema_id')!r} != {FORWARD_PROFILE_SCHEMA_ID!r}")
    args = _check_recorded_args(block.get("args"))
    input_reasons = block.get("input_reasons")
    if not isinstance(input_reasons, list) or not all(
        isinstance(r, Mapping) and isinstance(r.get("code"), str) and isinstance(r.get("detail"), str) for r in input_reasons
    ):
        raise ForwardProfileError("recorded_block_invalid", "forward_profile.input_reasons 不是 {code, detail} 列表")
    source = block.get("source")
    if source not in ("final_args_tokens", "args_namespace"):
        raise ForwardProfileError("recorded_block_invalid", f"source={source!r} 未知")
    recomputed = _derive(args, source=source, input_reasons=input_reasons)
    diffs = [key for key in _DERIVED_KEYS if block.get(key) != recomputed[key]]
    if diffs:
        raise ForwardProfileError(
            "recorded_block_inconsistent",
            f"记录的推导字段 {diffs} 与按记录 args 重算的结果不一致（证据被改写或推导规则已变）",
        )
    return recomputed


# ---------------------------------------------------------------------------
# CLI（launch.sh 用系统 python3 按文件路径调用）
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="E5：从最终 train_async.py 参数推导诊断 / 效率档（stdout 输出 forward_profile 证据块 JSON）",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    derive = sub.add_parser("derive", help="derive [--expect diagnostic|efficiency] -- <最终参数 token...>")
    derive.add_argument("--expect", choices=PROFILES, default=None, help="旋钮期望的档位；与推导不符即非零退出")
    derive.add_argument("--compact", action="store_true", help="单行 JSON（shell 捕获用）")
    derive.add_argument("tokens", nargs=argparse.REMAINDER)
    ns = parser.parse_args(argv)
    tokens = list(ns.tokens)
    if tokens and tokens[0] == "--":
        tokens = tokens[1:]
    block = derive_from_tokens(tokens)
    print(json.dumps(block, ensure_ascii=False, sort_keys=True, indent=None if ns.compact else 1))
    try:
        require_supported(block, expect=ns.expect)
    except ForwardProfileError as exc:
        print(f"[forward-profile] FAIL: {exc}", file=sys.stderr)
        for r in block["unsupported_reasons"]:
            print(f"[forward-profile]   - {r['code']}: {r['detail']}", file=sys.stderr)
        return 3 if exc.reason_code == "forward_profile_mismatch" else 2
    return 0


__all__ = [
    "DIAGNOSTIC",
    "EFFICIENCY",
    "EFFICIENCY_FLAG",
    "FAITHFUL_DIS_LOSS_PATH",
    "FORWARD_CONDITION",
    "FORWARD_PROFILE_SCHEMA_ID",
    "OBS_LOGPROB_COMPARE",
    "OBS_MILES_LOG_PROBS_TFLOPS",
    "OBS_MILES_LOG_PROBS_TIME",
    "OBS_MILES_ROLLOUT_LOG_PROBS",
    "OBS_REPLAY_CONSUME_LOGPROB_FORWARD",
    "PROFILES",
    "TRACKED_DESTS",
    "TRACKED_OPTIONS",
    "UNSUPPORTED",
    "ForwardProfileError",
    "derive_from_namespace",
    "derive_from_tokens",
    "interpret_recorded",
    "parse_final_args",
    "require_supported",
    "scan_custom_config_text",
]


if __name__ == "__main__":
    raise SystemExit(main())
