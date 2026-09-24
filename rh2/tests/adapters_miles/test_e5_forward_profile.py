"""E5（第六组 I24；Codex 复核 §4）：诊断 / 效率两份配置只从最终 args 推导（forward_profile.py），launch.sh 的非强制旋钮。

oracle：
- 本配方（launch.sh LOSS_ARGS：custom_loss + faithful DIS + --kl-coef 0，R3 on）三开关都不设 = diagnostic；只多
  --use-rollout-logprobs = efficiency；--skip-actor-forward-only / --get-mismatch-metrics 一律 unsupported；效率档再叠加
  PPO / OPD / KL / TIS / keep-old-actor 等一律 unsupported（fail-closed），诊断档不受这些守卫影响。
- 证据块可按记录的参数用同一函数重算；推导字段被改写即拒绝。CLI 只依赖标准库（launch.sh 用系统 python3 按路径执行）。
- integration_base：镜像的缺省值 / dest / action 与 fork arguments.py 逐项一致；fork 真实的 validate_skip_actor_forward_only
  在本配方取值下必须 assert（解析器反例）。
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

RH2 = Path(__file__).resolve().parents[2]
FORWARD_PROFILE_PY = RH2 / "src" / "repoharness2" / "adapters" / "miles" / "forward_profile.py"
LAUNCH_SH = RH2 / "experiments" / "miles_gpu_spike" / "launch.sh"
CUSTOM_CONFIG = RH2 / "experiments" / "miles_gpu_spike" / "custom_config.yaml"
FAITHFUL = "repoharness2.adapters.miles.faithful_dis_loss.faithful_dis_loss_function"


def _recipe(*, r3: bool = True) -> list[str]:
    """launch.sh LOSS_ARGS 的形状（+ --custom-config-path 指向真实 custom_config.yaml）。"""
    tokens = ["--loss-type", "custom_loss", "--custom-loss-function-path", FAITHFUL, "--kl-coef", "0.0", "--entropy-coef", "0.0",
              "--custom-config-path", str(CUSTOM_CONFIG)]
    return tokens + (["--use-rollout-routing-replay"] if r3 else [])


def _fp():
    from repoharness2.adapters.miles import forward_profile

    return forward_profile


def test_launch_recipe_derives_exactly_two_profiles_one_flag_apart():
    fp = _fp()
    diag = fp.derive_from_tokens(_recipe())
    eff = fp.derive_from_tokens([*_recipe(), "--use-rollout-logprobs"])
    assert (diag["profile"], diag["extra_logprob_forward"], diag["unavailable_observations"]) == ("diagnostic", True, [])
    assert diag["switches"] == {"use_rollout_logprobs": False, "get_mismatch_metrics": False, "skip_actor_forward_only": False}
    assert (eff["profile"], eff["extra_logprob_forward"]) == ("efficiency", False)
    assert eff["switches"] == {"use_rollout_logprobs": True, "get_mismatch_metrics": False, "skip_actor_forward_only": False}
    assert eff["unavailable_observations"] == [
        "rh2_event:logprob_compare", "rh2_event:replay_consume{phase=logprob_forward}", "miles_metric:rollout/log_probs",
        "miles_metric:perf/log_probs_time", "miles_metric:perf/log_probs_tflops",
    ]
    assert diag["unsupported_reasons"] == eff["unsupported_reasons"] == []
    # 两块只在该开关及其推导字段上不同（参数表恰差一个开关）
    assert {k for k in diag["args"] if diag["args"][k] != eff["args"][k]} == {"use_rollout_logprobs"}
    # R3 关时 logprob_forward 的 replay 消费本来就不存在，不列为"按配置不可用"
    no_r3 = fp.derive_from_tokens([*_recipe(r3=False), "--use-rollout-logprobs"])
    assert "rh2_event:replay_consume{phase=logprob_forward}" not in no_r3["unavailable_observations"]
    assert no_r3["rollout_replay"] == {"routing": False, "indexer": False}


@pytest.mark.parametrize("with_rollout_logprobs", [False, True])
def test_skip_actor_forward_only_is_unsupported_for_this_recipe(with_rollout_logprobs):
    fp = _fp()
    tokens = [*_recipe(), "--skip-actor-forward-only"] + (["--use-rollout-logprobs"] if with_rollout_logprobs else [])
    block = fp.derive_from_tokens(tokens)
    assert block["profile"] == "unsupported" and block["extra_logprob_forward"] is False
    assert "skip_actor_forward_only_incompatible" in {r["code"] for r in block["unsupported_reasons"]}
    with pytest.raises(fp.ForwardProfileError) as err:
        fp.require_supported(block)
    assert err.value.reason_code == "forward_profile_unsupported"


@pytest.mark.parametrize("with_rollout_logprobs", [False, True])
def test_get_mismatch_metrics_has_no_consumer_and_is_unsupported(with_rollout_logprobs):
    fp = _fp()
    tokens = [*_recipe(), "--get-mismatch-metrics"] + (["--use-rollout-logprobs"] if with_rollout_logprobs else [])
    block = fp.derive_from_tokens(tokens)
    assert block["profile"] == "unsupported" and block["extra_logprob_forward"] is True  # 它只会重开额外 forward
    assert {r["code"] for r in block["unsupported_reasons"]} == {"get_mismatch_metrics_no_consumer"}


EFFICIENCY_GUARD_CASES = [
    (["--loss-type", "policy_loss"], "efficiency_requires_custom_loss"),
    (["--custom-loss-function-path", "pkg.other_loss"], "efficiency_requires_faithful_dis"),
    (["--advantage-estimator", "gspo"], "efficiency_requires_grpo"),
    (["--advantage-estimator", "ppo"], "efficiency_rejects_ppo_critic"),
    (["--kl-coef", "0.05"], "efficiency_rejects_kl_reward_shaping"),
    (["--use-kl-loss"], "efficiency_rejects_kl_loss"),
    (["--kl-loss-coef", "0.01"], "efficiency_rejects_kl_loss"),
    (["--use-opd"], "efficiency_rejects_opd"),
    (["--use-tis"], "efficiency_rejects_tis"),
    (["--custom-tis-function-path", "pkg.tis"], "efficiency_rejects_custom_tis"),
    (["--keep-old-actor"], "efficiency_rejects_keep_old_actor"),
    (["--normalize-advantages"], "efficiency_rejects_normalize_advantages"),
    (["--use-rollout-entropy"], "efficiency_rejects_rollout_entropy"),
    (["--log-correct-samples"], "efficiency_rejects_log_correct_samples"),
    (["--save-debug-train-data", "/dump/{rollout_id}_{rank}.pt"], "efficiency_rejects_debug_train_dump"),
    (["--dump-details", "/dump"], "efficiency_rejects_debug_train_dump"),
    (["--rollout-data-postprocess-path", "pkg.post"], "efficiency_rejects_rollout_data_postprocess"),
    (["--custom-megatron-before-log-prob-hook-path", "pkg.hook"], "efficiency_rejects_before_log_prob_hook"),
    (["--use-indexer-replay"], "efficiency_rejects_record_indexer_replay"),
]


@pytest.mark.parametrize(("extra", "code"), EFFICIENCY_GUARD_CASES)
def test_efficiency_guard_rejects_semantics_changing_or_forward_reading_switches(extra, code):
    """效率档 fail-closed；同一开关在诊断档不改变档位（额外 forward 照跑，守卫只管 --use-rollout-logprobs 的语义）。"""
    fp = _fp()
    eff = fp.derive_from_tokens([*_recipe(), *extra, "--use-rollout-logprobs"])
    assert eff["profile"] == "unsupported" and code in {r["code"] for r in eff["unsupported_reasons"]}
    diag = fp.derive_from_tokens([*_recipe(), *extra])
    assert diag["profile"] == "diagnostic" and diag["extra_logprob_forward"] is True


def test_record_routing_replay_without_rollout_replay_is_rejected_in_efficiency():
    """非 rollout 的 routing replay 由额外 forward 记录（stage=record）再给训练回放；R3（rollout 回放）在场时 miles 自己把
    use_routing_replay 置真（arguments.py:3531-3532），不算违规。"""
    fp = _fp()
    bad = fp.derive_from_tokens([*_recipe(r3=False), "--use-routing-replay", "--use-rollout-logprobs"])
    assert "efficiency_rejects_record_routing_replay" in {r["code"] for r in bad["unsupported_reasons"]}
    ok = fp.derive_from_tokens([*_recipe(r3=True), "--use-rollout-logprobs"])
    assert ok["profile"] == "efficiency" and ok["args"]["use_routing_replay"] is True


def test_disabling_advantages_turns_the_forward_off_and_is_unsupported_in_both():
    fp = _fp()
    for extra in ([], ["--use-rollout-logprobs"]):
        block = fp.derive_from_tokens([*_recipe(), "--disable-compute-advantages-and-returns", *extra])
        assert block["profile"] == "unsupported" and block["extra_logprob_forward"] is False
        assert "advantages_disabled" in {r["code"] for r in block["unsupported_reasons"]}


def test_token_stream_parsing_follows_argparse_and_fails_closed_when_the_final_value_is_unknown():
    fp = _fp()
    values, reasons = fp.parse_final_args(["--loss-type=policy_loss", "--loss-type", "custom_loss", "--kl-coef=0.0"])
    assert values["loss_type"] == "custom_loss" and values["kl_coef"] == 0.0 and reasons == []  # 取最后一次、= 形式
    for tokens, code in (
        (["--use-rollout-logprobs=true"], "flag_given_value"),
        (["--loss-type"], "option_missing_value"),
        (["--loss-type", "--use-rollout-logprobs"], "option_missing_value"),
        (["--kl-coef", "zero"], "option_value_not_float"),
        (["--loss-type", "custom_loss", "--", "--use-rollout-logprobs"], "token_stream_end_of_options"),
    ):
        block = fp.derive_from_tokens([*_recipe(), *tokens])
        assert block["profile"] == "unsupported" and code in {r["code"] for r in block["input_reasons"]}, tokens
    # Megatron 的 --save 等真实选项恰好是追踪选项的前缀：不当作缩写（miles 经 allow_abbrev=False 的 Megatron 解析器）
    assert fp.derive_from_tokens([*_recipe(), "--save", "/ckpt", "--load", "/ckpt"])["profile"] == "diagnostic"
    # --dump-details 按 miles_validate_args 改写 save_debug_train_data；advantage_estimator=ppo 派生 use_critic
    values, _ = fp.parse_final_args(["--dump-details", "/d", "--advantage-estimator", "ppo"])
    assert values["save_debug_train_data"] == "/d/train_data/{rollout_id}_{rank}.pt" and values["use_critic"] is True


def test_custom_config_yaml_that_sets_a_tracked_key_is_refused(tmp_path):
    fp = _fp()
    assert fp.scan_custom_config_text(CUSTOM_CONFIG.read_text(encoding="utf-8")) == []  # 真实配置不碰追踪键
    sneaky = tmp_path / "custom.yaml"
    sneaky.write_text("# use_rollout_logprobs 只出现在注释里不算\nrh2_engine_sampling_mask: true\nuse_rollout_logprobs: true\n", encoding="utf-8")
    block = fp.derive_from_tokens([*_recipe(), "--custom-config-path", str(sneaky)])
    assert block["profile"] == "unsupported"
    assert [r["code"] for r in block["input_reasons"]] == ["custom_config_sets_tracked_key"]
    flow = tmp_path / "flow.yaml"
    flow.write_text("{get_mismatch_metrics: true}\n", encoding="utf-8")
    assert fp.derive_from_tokens([*_recipe(), "--custom-config-path", str(flow)])["profile"] == "unsupported"
    gone = fp.derive_from_tokens([*_recipe(), "--custom-config-path", str(tmp_path / "missing.yaml")])
    assert [r["code"] for r in gone["input_reasons"]] == ["custom_config_unreadable"]
    # miles 同读法：--custom-config-path 也可以是内联 base64 载荷（file_arg_utils.resolve_file_arg）
    import base64

    inline = "base64:" + base64.b64encode(b"use_rollout_logprobs: true\n").decode()
    assert [r["code"] for r in fp.derive_from_tokens([*_recipe(), "--custom-config-path", inline])["input_reasons"]] == [
        "custom_config_sets_tracked_key"]
    clean = "base64:" + base64.b64encode(b"moe_aux_loss_coeff: 0.0\n").decode()
    assert fp.derive_from_tokens([*_recipe(), "--custom-config-path", clean])["profile"] == "diagnostic"
    garbled = fp.derive_from_tokens([*_recipe(), "--custom-config-path", "base64:@@not-base64@@"])
    assert [r["code"] for r in garbled["input_reasons"]] == ["custom_config_unreadable"]


def test_namespace_entry_matches_token_entry_and_missing_attributes_fail_closed():
    fp = _fp()
    for extra in ([], ["--use-rollout-logprobs"], ["--use-rollout-logprobs", "--use-opd"]):
        values, reasons = fp.parse_final_args([*_recipe(), *extra])
        assert reasons == []
        from_tokens = fp.derive_from_tokens([*_recipe(), *extra])
        from_ns = fp.derive_from_namespace(NS(**values, unrelated_megatron_arg=7))
        assert {k: v for k, v in from_ns.items() if k != "source"} == {k: v for k, v in from_tokens.items() if k != "source"}
    values, _ = fp.parse_final_args(_recipe())
    del values["use_rollout_logprobs"]
    partial = fp.derive_from_namespace(NS(**values))
    assert partial["profile"] == "unsupported" and [r["code"] for r in partial["input_reasons"]] == ["args_attribute_missing"]


def test_recorded_block_round_trips_and_rewritten_derivations_are_rejected():
    fp = _fp()
    block = json.loads(json.dumps(fp.derive_from_tokens([*_recipe(), "--use-rollout-logprobs"])))
    assert fp.interpret_recorded(block)["profile"] == "efficiency"
    tampered = dict(block, profile="diagnostic", extra_logprob_forward=True, unavailable_observations=[])
    with pytest.raises(fp.ForwardProfileError) as err:
        fp.interpret_recorded(tampered)
    assert err.value.reason_code == "recorded_block_inconsistent"
    rewritten_args = json.loads(json.dumps(block))
    rewritten_args["args"]["use_rollout_logprobs"] = False  # 参数被改成诊断档，推导字段仍是效率档
    with pytest.raises(fp.ForwardProfileError, match="recorded_block_inconsistent"):
        fp.interpret_recorded(rewritten_args)
    for broken in (
        dict(block, schema_id="other"),
        dict(block, args={k: v for k, v in block["args"].items() if k != "loss_type"}),
        dict(block, args=dict(block["args"], use_rollout_logprobs=1)),
        dict(block, input_reasons="none"),
        dict(block, source="knob"),
        "efficiency",
    ):
        with pytest.raises(fp.ForwardProfileError) as err:
            fp.interpret_recorded(broken)
        assert err.value.reason_code == "recorded_block_invalid"


def test_require_supported_compares_the_knob_only_against_the_derivation():
    fp = _fp()
    eff = fp.derive_from_tokens([*_recipe(), "--use-rollout-logprobs"])
    fp.require_supported(eff, expect="efficiency")
    with pytest.raises(fp.ForwardProfileError) as err:
        fp.require_supported(eff, expect="diagnostic")
    assert err.value.reason_code == "forward_profile_mismatch"


def test_cli_runs_on_the_standard_library_alone_with_launch_exit_codes():
    """launch.sh P12 的调用形态：系统 python3 按文件路径执行（-I -S：不带 site-packages、不看 PYTHONPATH）。"""

    def run(*argv):
        return subprocess.run([sys.executable, "-I", "-S", str(FORWARD_PROFILE_PY), "derive", "--compact", *argv],
                              capture_output=True, text=True, check=False)

    ok = run("--expect", "diagnostic", "--", *_recipe())
    assert ok.returncode == 0 and json.loads(ok.stdout)["profile"] == "diagnostic" and ok.stdout.count("\n") == 1
    eff = run("--expect", "efficiency", "--", *_recipe(), "--use-rollout-logprobs")
    assert eff.returncode == 0 and json.loads(eff.stdout)["extra_logprob_forward"] is False
    mismatch = run("--expect", "diagnostic", "--", *_recipe(), "--use-rollout-logprobs")
    assert mismatch.returncode == 3 and "forward_profile_mismatch" in mismatch.stderr
    bad = run("--expect", "efficiency", "--", *_recipe(), "--use-rollout-logprobs", "--skip-actor-forward-only")
    assert bad.returncode == 2 and "skip_actor_forward_only_incompatible" in bad.stderr
    assert json.loads(bad.stdout)["profile"] == "unsupported"  # 证据块照样输出，便于操作员看原因


def test_launch_script_knob_is_optional_and_evidence_is_the_derivation_not_the_knob():
    """launch.sh 是配方参考（不是八卡正式启动方案）：旋钮缺省 diagnostic；efficiency 只多一个开关；P12 用与 ray job submit
    相同的数组推导；run_manifest.json 写推导块，旋钮字符串不进证据。真实 dry-run 两份参数表之差见 E5 CPU 探针工件。"""
    subprocess.run(["bash", "-n", str(LAUNCH_SH)], check=True)
    text = LAUNCH_SH.read_text(encoding="utf-8")
    assert 'RH2_TRAIN_FORWARD_PROFILE="${RH2_TRAIN_FORWARD_PROFILE:-diagnostic}"' in text
    block = re.search(r'if \[ "\$RH2_TRAIN_FORWARD_PROFILE" = "efficiency" \]; then\n(.*?)\nfi\n', text, re.S)
    assert block is not None
    body = [ln.strip() for ln in block.group(1).splitlines() if ln.strip() and not ln.strip().startswith("#")]
    assert body == ["LOSS_ARGS+=(--use-rollout-logprobs)"]
    assert text.count("--use-rollout-logprobs)") == 1  # 参数组里只此一处追加
    derive = re.search(r'python3 "\$FORWARD_PROFILE_PY" derive --compact --expect "\$RH2_TRAIN_FORWARD_PROFILE" -- (.*?)\)"', text)
    assert derive is not None and derive.group(1) == '"${MODEL_ARGS[@]}" "${ALL_ARGS[@]}"'
    assert '"${MODEL_ARGS[@]}" "${ALL_ARGS[@]}" 2>&1 | tee "$LOG"' in text  # ray job submit 用的同一对数组
    assert text.index("P12. E5 forward 档位闸") < text.index('say "preflight 全部通过"')
    manifest = text[text.index('python3 - "$EV/run_manifest.json" "$FORWARD_PROFILE_JSON" <<PYEOF'):]
    manifest = manifest[: manifest.index("\nPYEOF\n")]
    assert '"forward_profile": json.loads(sys.argv[2]),' in manifest and "RH2_TRAIN_FORWARD_PROFILE" not in manifest


# ---------------------------------------------------------------------------
# integration_base：与 fork 源码逐项对照 + 真实解析器反例
# ---------------------------------------------------------------------------


def _add_argument_calls(arguments_py: Path) -> dict[str, dict]:
    tree = ast.parse(arguments_py.read_text(encoding="utf-8"))
    calls: dict[str, dict] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                kwargs = {}
                for kw in node.keywords:
                    if kw.arg in ("action", "default", "dest"):
                        try:
                            kwargs[kw.arg] = ast.literal_eval(kw.value)
                        except ValueError:
                            kwargs[kw.arg] = f"<non-literal:{ast.unparse(kw.value)}>"
                    elif kw.arg == "type" and isinstance(kw.value, ast.Name):
                        kwargs["type"] = kw.value.id
                assert node.args[0].value not in calls, f"{node.args[0].value} 定义了两次"
                calls[node.args[0].value] = kwargs
    return calls


@pytest.mark.integration_base
def test_mirror_defaults_and_post_parse_rewrites_match_fork_arguments(world):
    fp = _fp()
    arguments_py = world.miles_root / "miles" / "utils" / "arguments.py"
    calls = _add_argument_calls(arguments_py)
    for opt in fp.TRACKED_OPTIONS:
        spec = calls[opt.option]
        dest = spec.get("dest", opt.option.lstrip("-").replace("-", "_"))
        assert dest == opt.dest, opt.option
        if opt.kind in ("store_true", "store_false"):
            assert spec.get("action") == opt.kind, opt.option
            assert spec.get("default", opt.kind == "store_false") == opt.default, opt.option
        else:
            assert spec.get("action") is None and spec.get("type", "str") == opt.kind, opt.option
            assert spec.get("default") == opt.default, opt.option
    source = arguments_py.read_text(encoding="utf-8")
    assert 'reset_arg(\n            parser,\n            "--custom-config-path",\n            type=str,\n            default=None,' in source
    file_arg = (world.miles_root / "miles" / "utils" / "file_arg_utils.py").read_text(encoding="utf-8")
    assert f'PSEUDO_FILE_PREFIX = "{fp.PSEUDO_FILE_PREFIX}"' in file_arg and "base64.b64decode(value[len(PSEUDO_FILE_PREFIX) :], validate=True)" in file_arg
    assert 'args.use_critic = args.advantage_estimator == "ppo"' in source
    assert "    if args.use_rollout_routing_replay:\n        args.use_routing_replay = True" in source
    assert "    if args.use_rollout_indexer_replay:\n        args.use_indexer_replay = True" in source
    assert 'args.save_debug_train_data = f"{args.dump_details}/train_data/{{rollout_id}}_{{rank}}.pt"' in source
    # custom config 在全部校验之后逐键 setattr：这是 YAML 扫描的依据
    assert re.search(r"if args\.custom_config_path:\n(?:.*\n){1,6}?\s+setattr\(args, k, v\)", source)


@pytest.mark.integration_base
def test_forward_condition_and_advantage_shape_source_match_fork(world):
    actor = (world.miles_root / "miles" / "backends" / "megatron_utils" / "actor.py").read_text(encoding="utf-8")
    body = actor[actor.index("    def train_actor("):]
    outer = body.index("            if self.args.compute_advantages_and_returns:")
    inner = body.index("                if not skip_actor_forward_only and (\n"
                       "                    not self.args.use_rollout_logprobs or self.args.get_mismatch_metrics\n"
                       "                ):")
    assert outer < inner < body.index("self._emit_logprob_compare(rollout_id, rollout_data)")
    loss = (world.miles_root / "miles" / "backends" / "training_utils" / "loss.py").read_text(encoding="utf-8")
    assert 'log_probs_key = "rollout_log_probs" if args.use_rollout_logprobs else "log_probs"' in loss


@pytest.mark.integration_base
def test_real_fork_validator_rejects_skip_actor_forward_only_on_the_launch_recipe(world):
    """解析器反例：fork 真实 validate_skip_actor_forward_only（AST 提取，避开 sglang_router 等导入）+ launch.sh 本配方取值。"""
    arguments_py = world.miles_root / "miles" / "utils" / "arguments.py"
    tree = ast.parse(arguments_py.read_text(encoding="utf-8"))
    (node,) = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "validate_skip_actor_forward_only"]
    namespace: dict = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(arguments_py), "exec"), namespace)  # noqa: S102
    validate = namespace["validate_skip_actor_forward_only"]
    text = LAUNCH_SH.read_text(encoding="utf-8")
    rollout_batch = int(re.search(r"^ROLLOUT_BATCH_SIZE=(\d+);", text, re.M).group(1))
    n_samples = int(re.search(r"N_SAMPLES_PER_PROMPT=(\d+)", text).group(1))
    gbs = int(re.search(r"^GLOBAL_BATCH_SIZE=(\d+)", text, re.M).group(1))
    assert "--loss-type custom_loss" in text and (rollout_batch * n_samples) // gbs == 2  # 本配方：custom_loss、每轮 2 步

    def args(**over):
        base = dict(
            train_backend="megatron", loss_type="custom_loss", compute_advantages_and_returns=True, keep_old_actor=False,
            kl_coef=0.0, use_opd=False, hidden_dropout=0.0, attention_dropout=0.0, lora_dropout=0.0, moe_input_jitter_eps=None,
            moe_router_force_load_balancing=False, moe_router_force_biased=None, moe_router_load_balancing_type="aux_loss",
            use_rollout_entropy=False, true_on_policy_mode=False, log_correct_samples=False, rollout_data_postprocess_path=None,
            custom_megatron_before_log_prob_hook_path=None, custom_megatron_before_train_step_hook_path=None,
            custom_model_provider_path=None, dumper_source_patcher_config_train=None, save_debug_train_data=None,
            dump_details=None, use_routing_replay=True, use_rollout_routing_replay=True, use_indexer_replay=False,
            use_rollout_indexer_replay=False, num_steps_per_rollout=None, use_dynamic_global_batch_size=False, multi_lora=None,
            rollout_batch_size=rollout_batch, n_samples_per_prompt=n_samples, global_batch_size=gbs, skip_actor_forward_only=True,
        )
        base.update(over)
        return NS(**base)

    with pytest.raises(AssertionError, match="only supports --loss-type policy_loss"):
        validate(args())
    with pytest.raises(AssertionError, match="exactly one optimizer step"):
        validate(args(loss_type="policy_loss"))  # 即使换成 policy_loss，本配方的批形状也是每轮 2 步
    validate(args(loss_type="policy_loss", global_batch_size=rollout_batch * n_samples))  # 正控：条件都满足时不 assert
