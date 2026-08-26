"""R6-ext B3/B4/B6 seam 验收：真实 `train_one_step → get_batch → loss_function` 纵链。

与 test_faithful_dis_loss.py 的分工：那边直接调 loss 函数做单 microbatch
逐位对拍;**这里必须经过 miles 真实训练 seam**——integration base 的
`miles/backends/megatron_utils/model.py::train_one_step`（含 B3 patch 后的
sampling-mask key 传输）、`training_utils/data.py::get_batch/DataIterator`、
`training_utils/loss.py::loss_function` dispatcher（真实
`sum_of_sample_mean`/`rollout_mask_sums` 构造 + megatron 缩放）——batch 不许
手工构造直接喂 loss（B3 验收条款）。

CPU 可达深度（"megatron 并行组 stub 到最小"）：

- **megatron.* 全部 auto-stub**（meta path finder;`get_args`/
  `get_forward_backward_func`/`mpu.is_pipeline_last_stage` 三个运行时行为点
  在 import miles model 之前钉真实现）。forward_backward 用串行等价实现：
  每 microbatch `loss/num_microbatches` 反传——与 megatron
  forward_backward_no_pipelining 对 calculate_per_token_loss=False 的缩放
  一致;miles dispatcher 端 `loss × num_microbatches/global_batch_size ×
  intra_dp_cp.size(=1)` 不动,净效果 = Σ_e loss_e / N_exec 的梯度。
- **单进程 gloo**（world_size=1）：aggregate_train_losses 的
  reduce/broadcast 走真实 dist 调用（自归约,no-op 语义）。
- `torch.Tensor.cuda` 钳制为恒等（get_batch 的 `.cuda()` 落 CPU）;
  模型/优化器是探针级 CPU 件（TinyModel double 精度 + 真 AdamW,
  weight_decay>0 使 B6 探针对"零梯度也改参"敏感）。
- sglang/psutil/ray 为 import 占位 stub（环境噪音,与 conftest 同性质;
  本文件 fixture 自含,不改 conftest）。

对拍权威 = `repoharness2.training.faithful_dis.faithful_dis_loss_by_execution`
（不动）。三组 metamorphic（B4 验收）：

1. branch split：同一 execution 的 token 集拆成多个样本（共享前缀重放）,
   loss 与参数梯度不变;
2. sibling 跨 microbatch：同 execution 的 sibling 分到不同 microbatch,不变;
3. DP partition：两半样本各自独立跑（num_rollouts 仍为全局值）,loss 与
   梯度按和重构出全批结果（真实 DDP 的 ÷DP size 与 dispatcher 的
   ×intra_dp_cp.size 相消,此处以"和"口径模拟,进程组机制归硬件段）。

B6（spike fail-stop）：全拒 batch 在 optimizer.step 之前抛
FaithfulDisZeroAcceptedStop——参数/optimizer state/scheduler/weight version
全不前进（weight version 以 train_one_step 正常返回为代理:miles actor 只在
train 成功返回后才推进权重版本,actor.py 无 try/except,异常 = run fatal）。
已知偏差（有意,不建跨 microbatch 协议）：触发粒度是 microbatch,"部分
microbatch 全拒但全局 accepted>0" 也会停——由
test_b6_partial_zero_microbatch_known_deviation 固定并注明,正式首训前按
FA-4 §4 收敛为 skip+计数+熔断。
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import sys
import tempfile
import types
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.integration_base

VOCAB = 17
HIDDEN = 8
SEED = 1234
NUM_EXECUTIONS = 2  # rid 100 / rid 101

# 数据形状沿 test_faithful_dis_loss.py：手工支持集 + 手工 log-ratio
# （信任区间 (0.2,4.0) 开区间;in/out 位次见各 ratio 注释）
S0_TOKENS = [1, 2, 3, 4, 5, 6, 7]  # prompt [1,2,3] + resp [4,5,6,7]
S1_TOKENS = [1, 2, 8, 9, 10]  # prompt [1,2] + resp [8,9,10]
S0_SUPPORTS = [[4, 9, 10], [5, 2], [6], [7, 8]]
S1_SUPPORTS = [[8, 3], [9], [10, 11, 12]]
S0_MASK = [1, 1, 0, 1]  # 位 2 = 观察位（单例支持集）
S1_MASK = [1, 1, 1]
S0_RATIO = [0.0, 1.5, 0.3, -2.0]  # in / out-high / (mask=0) / out-low
S1_RATIO = [0.5, -1.0, 2.0]  # in / in / out-high
S0_ADV = [1.0, -0.5, 2.0, 0.7]
S1_ADV = [0.3, -1.2, 0.9]


def _csr(supports):
    ids, offsets = [], [0]
    for s in supports:
        ids.extend(s)
        offsets.append(len(ids))
    return ids, offsets


# ---------------------------------------------------------------------------
# stub 安装（module 级 fixture 自含;conftest 不改）
# ---------------------------------------------------------------------------


def _install_sglang_and_psutil_stubs():
    import pydantic

    class _StubTool(pydantic.BaseModel):
        model_config = pydantic.ConfigDict(extra="allow")

    for name in (
        "sglang",
        "sglang.srt",
        "sglang.srt.debug_utils",
        "sglang.srt.entrypoints",
        "sglang.srt.entrypoints.openai",
        "sglang.srt.entrypoints.openai.protocol",
        "sglang.srt.entrypoints.openai.encoding_dsv4",
    ):
        if name not in sys.modules:
            m = types.ModuleType(name)
            m.__path__ = []
            m.__rh2_test_stub__ = True
            sys.modules[name] = m
    proto = sys.modules["sglang.srt.entrypoints.openai.protocol"]
    if not hasattr(proto, "Tool"):
        proto.Tool = _StubTool
    if "sglang.srt.debug_utils.dumper" not in sys.modules:
        dmp = types.ModuleType("sglang.srt.debug_utils.dumper")
        dmp.__rh2_test_stub__ = True

        class DumperConfig:  # miles dumper_utils import 面;disabled 路径只用 _kv_pairs_to_dict
            @staticmethod
            def _kv_pairs_to_dict(raw):
                return dict(raw or {})

        dmp.DumperConfig = DumperConfig
        dmp._get_rank = lambda *a, **k: 0
        dmp.dumper = SimpleNamespace()
        sys.modules["sglang.srt.debug_utils.dumper"] = dmp

    if "psutil" not in sys.modules:
        _psutil = types.ModuleType("psutil")
        # transformers 用 find_spec 探测 psutil,__spec__ 必须非 None
        _psutil.__spec__ = importlib.machinery.ModuleSpec("psutil", loader=None)
        _psutil.__rh2_test_stub__ = True
        sys.modules["psutil"] = _psutil


def _auto_getattr(module: types.ModuleType):
    def getattr_impl(name: str):
        if name.startswith("__"):
            raise AttributeError(name)
        stub = type(name, (), {"__init__": lambda self, *a, **k: None})
        setattr(module, name, stub)
        return stub

    return getattr_impl


class _MegatronLoader(importlib.abc.Loader):
    def create_module(self, spec):
        m = types.ModuleType(spec.name)
        m.__path__ = []
        m.__getattr__ = _auto_getattr(m)  # PEP 562：未知符号按需产 dummy 类
        return m

    def exec_module(self, module):
        pass


class _MegatronFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "megatron" or fullname.startswith("megatron."):
            return importlib.util.spec_from_loader(fullname, _MegatronLoader(), is_package=True)
        return None


def _evict_module_prefix(prefix: str) -> None:
    for name in [n for n in sys.modules if n == prefix or n.startswith(prefix + ".")]:
        del sys.modules[name]


@pytest.fixture(scope="module")
def seam():
    """megatron auto-stub 世界 + 真实 miles train seam 的运行器。"""

    import torch
    import torch.distributed as dist

    _install_sglang_and_psutil_stubs()

    finder = _MegatronFinder()
    sys.meta_path.insert(0, finder)
    _evict_module_prefix("megatron")

    # 行为点在 import miles model 之前钉死（from-import 在 import 时绑定）
    args_holder: dict[str, Namespace] = {}
    gv = importlib.import_module("megatron.training.global_vars")
    gv.get_args = lambda: args_holder["args"]

    fbf_holder: dict[str, object] = {}
    pp_mod = importlib.import_module("megatron.core.pipeline_parallel")
    pp_mod.get_forward_backward_func = lambda: fbf_holder["fbf"]

    mpu = importlib.import_module("megatron.core.mpu")
    mpu.is_pipeline_last_stage = lambda ignore_virtual=False: True

    saved_tensor_cuda = torch.Tensor.cuda
    torch.Tensor.cuda = lambda self, *a, **k: self  # type: ignore[method-assign]

    owns_dist = not dist.is_initialized()
    if owns_dist:
        init_file = tempfile.NamedTemporaryFile(delete=False, suffix=".dist_init")
        dist.init_process_group("gloo", init_method=f"file://{init_file.name}", rank=0, world_size=1)

    from miles.backends.training_utils.parallel import ParallelState, set_parallel_state
    from miles.utils.ft_utils.process_group_utils import GroupInfo

    def world_group():
        return GroupInfo(rank=0, size=1, group=dist.group.WORLD)

    set_parallel_state(
        ParallelState(
            intra_dp=world_group(),
            intra_dp_cp=world_group(),
            cp=world_group(),
            tp=world_group(),
            pp=world_group(),
            ep=world_group(),
            etp=world_group(),
            indep_dp=world_group(),
            is_pp_last_stage=True,
        )
    )

    model_mod = importlib.import_module("miles.backends.megatron_utils.model")
    data_mod = importlib.import_module("miles.backends.training_utils.data")

    # --- 探针件 ---------------------------------------------------------

    class TinyModel(torch.nn.Module):
        """位置无关探针模型：logits[t] 只依赖 input_ids[t]（double 精度,
        使 branch split 的共享前缀重放天然给出相同逐位 current logp）。"""

        def __init__(self):
            super().__init__()
            g = torch.Generator().manual_seed(SEED)
            self.embed = torch.nn.Embedding(VOCAB, HIDDEN)
            self.head = torch.nn.Linear(HIDDEN, VOCAB)
            with torch.no_grad():
                self.embed.weight.copy_(torch.randn(VOCAB, HIDDEN, generator=g))
                self.head.weight.copy_(torch.randn(VOCAB, HIDDEN, generator=g) * 0.3)
                self.head.bias.copy_(torch.randn(VOCAB, generator=g) * 0.1)
            self.double()

        def forward(self, input_ids=None, **kwargs):
            return self.head(self.embed(input_ids))

        def zero_grad_buffer(self):  # DDP 面
            pass

    class FakeOptimizer:
        """MegatronOptimizer 探针面：step 前捕获梯度快照（train_one_step 尾部
        _zero_grads 会清梯度,不在这里捕获就取不到）。"""

        def __init__(self, model):
            self.inner = torch.optim.AdamW(model.parameters(), lr=0.05, weight_decay=0.1)
            self._model = model
            self.captured_grads = None

        def zero_grad(self):
            self.inner.zero_grad()

        def step(self):
            self.captured_grads = {
                n: p.grad.detach().clone()
                for n, p in self._model.named_parameters()
                if p.grad is not None
            }
            self.inner.step()
            return True, 0.0, 0

    class FakeScheduler:
        def __init__(self):
            self.increments = []

        def step(self, increment):
            self.increments.append(increment)

    def serial_forward_backward(
        *,
        forward_step_func,
        data_iterator,
        model,
        num_microbatches,
        seq_length,
        micro_batch_size,
        decoder_seq_length,
        forward_only,
    ):
        """megatron forward_backward_no_pipelining 的串行等价（CPU 探针）：
        calculate_per_token_loss=False 下每 microbatch loss ÷num_microbatches
        反传,收集逐 microbatch logging dict。"""
        it = data_iterator[0] if isinstance(data_iterator, (list, tuple)) else data_iterator
        chunk = model[0] if isinstance(model, (list, tuple)) else model
        losses_reduced = []
        for _ in range(num_microbatches):
            output, loss_partial = forward_step_func(it, chunk)
            loss, _num_tokens, logdict = loss_partial(output)
            (loss / num_microbatches).backward()
            losses_reduced.append(logdict)
        return losses_reduced

    fbf_holder["fbf"] = serial_forward_backward

    def mk_args(num_rollouts):
        return Namespace(
            loss_type="custom_loss",
            custom_loss_function_path=(
                "repoharness2.adapters.miles.faithful_dis_loss.faithful_dis_loss_function"
            ),
            recompute_loss_function=False,
            calculate_per_token_loss=False,
            use_dynamic_global_batch_size=False,
            global_batch_size=num_rollouts,
            data_pad_size_multiplier=4,  # 非 1：让 get_batch 的尾部 padding 真发生
            qkv_format="thd",
            allgather_cp=False,
            debug_disable_optimizer=False,
            custom_megatron_before_train_step_hook_path=None,
            multi_lora=False,
            enable_mtp_training=False,
            enable_witness=False,
            ci_test=False,
            check_for_nan_in_loss_and_grad=True,
            save_local_weight_checksum=False,
            dumper_enable=False,
            dumper_fwd_bwd=[],
            seq_length=64,
            micro_batch_size=None,
            decoder_seq_length=None,
            rollout_top_p=0.8,
            rollout_top_k=VOCAB,
            vocab_size=VOCAB,
            rollout_temperature=1.0,
            true_on_policy_mode=True,
            log_probs_chunk_size=-1,
            bf16=False,
            fp16=False,
            rollout_max_response_len=100000,
        )

    def probe_current_logps(samples):
        """初始权重下逐样本 current(support-renorm) logp（behavior/参考构造用;
        与 seam 内 forward 权重一致：optimizer.step 在全部 microbatch 之后）。"""
        from miles.backends.training_utils.loss_hub.logit_processors import (
            get_log_probs_and_entropy,
        )
        from miles.backends.training_utils.sampling_mask import get_rollout_sampling_masks

        args_holder["args"] = mk_args(NUM_EXECUTIONS)
        model = TinyModel()
        tokens = [torch.tensor(s["tokens"], dtype=torch.long) for s in samples]
        logits = torch.cat([model(t.unsqueeze(0))[0] for t in tokens], dim=0).unsqueeze(0)
        batch = {
            "rollout_sampling_mask_ids": [s["mask_ids"] for s in samples],
            "rollout_sampling_mask_offsets": [s["mask_offsets"] for s in samples],
        }
        with torch.no_grad():
            return get_log_probs_and_entropy(
                logits,
                args=args_holder["args"],
                unconcat_tokens=tokens,
                total_lengths=[len(s["tokens"]) for s in samples],
                response_lengths=[s["resp_len"] for s in samples],
                with_entropy=False,
                rollout_sampling_mask=get_rollout_sampling_masks(batch),
            )["log_probs"]

    def attach_behavior(samples, *, ratio_override=None):
        currents = probe_current_logps(samples)
        for s, cur in zip(samples, currents, strict=True):
            ratio = ratio_override if ratio_override is not None else s["ratio"]
            s["current"] = cur.clone()
            s["behavior"] = cur - torch.tensor(
                [ratio] * s["resp_len"] if isinstance(ratio, float) else ratio,
                dtype=torch.float64,
            )
        return samples

    def mk_rollout_data(samples):
        exec_sums = {}
        for s in samples:
            exec_sums[s["rid"]] = exec_sums.get(s["rid"], 0) + sum(s["mask"])
        return {
            "tokens": [torch.tensor(s["tokens"], dtype=torch.long) for s in samples],
            "loss_masks": [torch.tensor(s["mask"], dtype=torch.int32) for s in samples],
            "total_lengths": [len(s["tokens"]) for s in samples],
            "response_lengths": [s["resp_len"] for s in samples],
            "advantages": [torch.tensor(s["adv"], dtype=torch.float64) for s in samples],
            "rollout_log_probs": [s["behavior"] for s in samples],
            "rollout_sampling_mask_ids": [s["mask_ids"] for s in samples],
            "rollout_sampling_mask_offsets": [s["mask_offsets"] for s in samples],
            # 真实链 = train_data_conversion._compute_rollout_mask_sums 的
            # sibling 共享整 rollout 分母,get_rollout_data 转 float32 tensor
            "rollout_mask_sums": torch.tensor(
                [exec_sums[s["rid"]] for s in samples], dtype=torch.float32
            ),
        }

    class StepResult(SimpleNamespace):
        pass

    class StepHarness:
        """真实 seam 一步的可持有装配：异常后仍可检查 model/optimizer/scheduler
        （B6 状态探针需要）。weight version 代理 = miles actor 只在 train 正常
        返回后推进权重版本（actor.py 无 try/except,异常即 run fatal）。"""

        def __init__(self, samples, *, micro_batch_size=None, micro_batch_indices=None,
                     num_rollouts=NUM_EXECUTIONS):
            self.args = mk_args(num_rollouts)
            self.num_rollouts = num_rollouts
            self.iterator = data_mod.DataIterator(
                mk_rollout_data(samples),
                micro_batch_size=micro_batch_size,
                micro_batch_indices=micro_batch_indices,
            )
            if micro_batch_indices is not None:
                self.n_mb = len(micro_batch_indices)
            else:
                assert len(samples) % micro_batch_size == 0
                self.n_mb = len(samples) // micro_batch_size
            self.model = TinyModel()
            self.params_before = {n: p.detach().clone() for n, p in self.model.named_parameters()}
            self.optimizer = FakeOptimizer(self.model)
            self.scheduler = FakeScheduler()
            self.weight_version = 0

        def step(self) -> StepResult:
            args_holder["args"] = self.args
            loss_reduced, _grad_norm, outcome = model_mod.train_one_step(
                self.args, 0, 0, [self.iterator], [self.model], self.optimizer,
                self.scheduler, self.n_mb, self.num_rollouts, witness_info=None, attempt=0,
            )
            self.weight_version += 1
            return StepResult(
                loss_reduced=loss_reduced,
                outcome=outcome,
                grads=self.optimizer.captured_grads,
                model=self.model,
                optimizer=self.optimizer,
                scheduler=self.scheduler,
                params_before=self.params_before,
                weight_version=self.weight_version,
            )

    def run_step(samples, *, micro_batch_size=None, micro_batch_indices=None,
                 num_rollouts=NUM_EXECUTIONS):
        return StepHarness(
            samples,
            micro_batch_size=micro_batch_size,
            micro_batch_indices=micro_batch_indices,
            num_rollouts=num_rollouts,
        ).step()

    def reference(samples):
        """标量权威 by_execution + 参数梯度参考（surrogate 反传）。"""
        from repoharness2.training.faithful_dis import (
            DisTokenRecord,
            faithful_dis_loss_by_execution,
        )

        executions = {}
        for s in samples:
            executions.setdefault(str(s["rid"]), []).extend(
                DisTokenRecord(logp_current=c, logp_rollout=b, advantage=a, provenance_mask=m)
                for c, b, a, m in zip(
                    s["current"].tolist(), s["behavior"].tolist(), s["adv"], s["mask"], strict=True
                )
            )
        ref = faithful_dis_loss_by_execution(executions)

        # surrogate：Σ_i g_i·logp_i(θ) 的参数梯度 = ∂(by_execution.loss)/∂θ
        from miles.backends.training_utils.loss_hub.logit_processors import (
            get_log_probs_and_entropy,
        )
        from miles.backends.training_utils.sampling_mask import get_rollout_sampling_masks

        model = TinyModel()
        tokens = [torch.tensor(s["tokens"], dtype=torch.long) for s in samples]
        logits = torch.cat([model(t.unsqueeze(0))[0] for t in tokens], dim=0).unsqueeze(0)
        batch = {
            "rollout_sampling_mask_ids": [s["mask_ids"] for s in samples],
            "rollout_sampling_mask_offsets": [s["mask_offsets"] for s in samples],
        }
        current_list = get_log_probs_and_entropy(
            logits,
            args=args_holder["args"],
            unconcat_tokens=tokens,
            total_lengths=[len(s["tokens"]) for s in samples],
            response_lengths=[s["resp_len"] for s in samples],
            with_entropy=False,
            rollout_sampling_mask=get_rollout_sampling_masks(batch),
        )["log_probs"]
        grad_cursor: dict[str, int] = {}
        surrogate = logits.sum() * 0.0
        for s, cur in zip(samples, current_list, strict=True):
            eid = str(s["rid"])
            start = grad_cursor.get(eid, 0)
            grads = ref.per_token_grad_logp_current[eid][start : start + s["resp_len"]]
            grad_cursor[eid] = start + s["resp_len"]
            surrogate = surrogate + sum(
                g * cur[p] for p, g in enumerate(grads) if g != 0.0
            )
        surrogate.backward()
        ref_grads = {n: p.grad.detach().clone() for n, p in model.named_parameters()}
        return ref, ref_grads

    def base_samples():
        ids0, off0 = _csr(S0_SUPPORTS)
        ids1, off1 = _csr(S1_SUPPORTS)
        return [
            dict(
                tokens=S0_TOKENS, resp_len=4, mask=S0_MASK, mask_ids=ids0,
                mask_offsets=off0, ratio=S0_RATIO, adv=S0_ADV, rid=100,
            ),
            dict(
                tokens=S1_TOKENS, resp_len=3, mask=S1_MASK, mask_ids=ids1,
                mask_offsets=off1, ratio=S1_RATIO, adv=S1_ADV, rid=101,
            ),
        ]

    def split_samples():
        """branch split：s0 拆成 s0a(resp 前 2 位)+s0b(resp 后 2 位),共享前缀
        完整重放（s0b 的 prompt = s0 前 5 个 token）,同 rid=100。"""
        ids0a, off0a = _csr(S0_SUPPORTS[:2])
        ids0b, off0b = _csr(S0_SUPPORTS[2:])
        ids1, off1 = _csr(S1_SUPPORTS)
        return [
            dict(
                tokens=S0_TOKENS[:5], resp_len=2, mask=S0_MASK[:2], mask_ids=ids0a,
                mask_offsets=off0a, ratio=S0_RATIO[:2], adv=S0_ADV[:2], rid=100,
            ),
            dict(
                tokens=S0_TOKENS, resp_len=2, mask=S0_MASK[2:], mask_ids=ids0b,
                mask_offsets=off0b, ratio=S0_RATIO[2:], adv=S0_ADV[2:], rid=100,
            ),
            dict(
                tokens=S1_TOKENS, resp_len=3, mask=S1_MASK, mask_ids=ids1,
                mask_offsets=off1, ratio=S1_RATIO, adv=S1_ADV, rid=101,
            ),
        ]

    world = SimpleNamespace(
        torch=torch,
        model_mod=model_mod,
        TrainStepOutcome=model_mod.TrainStepOutcome,
        run_step=run_step,
        make_harness=StepHarness,
        reference=reference,
        attach_behavior=attach_behavior,
        base_samples=base_samples,
        split_samples=split_samples,
        miles_root=Path(importlib.import_module("miles").__file__).resolve().parents[1],
    )

    yield world

    # teardown：还原 torch/dist/megatron 世界,摘除本模块专属 miles 子树
    torch.Tensor.cuda = saved_tensor_cuda  # type: ignore[method-assign]
    if owns_dist and dist.is_initialized():
        dist.destroy_process_group()
    if finder in sys.meta_path:
        sys.meta_path.remove(finder)
    _evict_module_prefix("megatron")
    _evict_module_prefix("miles.backends.megatron_utils")
    _evict_module_prefix("miles.utils.dumper_utils")


def _assert_grads_close(torch, got: dict, want: dict, *, atol=1e-12, label=""):
    assert sorted(got) == sorted(want), (label, sorted(got), sorted(want))
    for name in want:
        assert torch.allclose(got[name], want[name], atol=atol), (
            f"{label}: 参数 {name} 梯度不一致,max diff="
            f"{(got[name] - want[name]).abs().max().item()}"
        )


# ---------------------------------------------------------------------------
# B3：mask wire 字段经真实 get_batch 抵达 custom loss
# ---------------------------------------------------------------------------


def test_b3_source_gating_no_longer_keyed_on_policy_loss(seam):
    """源码事实断言（与运行时 import 同一 checkout）：B3 patch 后 train 路径的
    mask key 传输只看 replay 开关,不看 loss_type。"""
    src = (seam.miles_root / "miles" / "backends" / "megatron_utils" / "model.py").read_text()
    assert 'args.loss_type == "policy_loss" and top_p_sampling_replay_enabled' not in src
    assert "if top_p_sampling_replay_enabled(args)" in src


def test_b3_custom_loss_receives_mask_through_real_seam(seam):
    """loss_type=custom_loss + replay 开启：真实 train_one_step 全链绿,loss
    等于 by_execution 权威——mask 字段若未被 get_batch 传输,faithful DIS 会
    以 ValueError（wire 字段缺失）当场炸,本测试不可能绿。"""
    samples = seam.attach_behavior(seam.base_samples())
    ref, ref_grads = seam.reference(samples)
    result = seam.run_step(samples, micro_batch_size=2)

    assert result.outcome == seam.TrainStepOutcome.NORMAL
    assert result.loss_reduced["loss"] == pytest.approx(ref.loss, rel=1e-9)
    # aggregate_train_losses 口径 = Σ_mb metric ÷ num_rollouts
    assert result.loss_reduced["dis_microbatch_provenance_tokens"] == pytest.approx(6 / 2)
    assert result.loss_reduced["dis_accepted_tokens"] == pytest.approx(3 / 2)
    _assert_grads_close(seam.torch, result.grads, ref_grads, label="base vs 权威")
    # 探针灵敏度：optimizer 确实走了,参数确实变了
    changed = any(
        not seam.torch.equal(p.detach(), result.params_before[n])
        for n, p in result.model.named_parameters()
    )
    assert changed and result.scheduler.increments == [NUM_EXECUTIONS]


# ---------------------------------------------------------------------------
# B4：三组 metamorphic（loss 与梯度都对拍 by_execution）
# ---------------------------------------------------------------------------


def test_metamorphic_branch_split_invariance(seam):
    """同一 execution 的 token 集拆成两个样本（共享前缀重放）：loss/梯度不变。"""
    base = seam.attach_behavior(seam.base_samples())
    ref, ref_grads = seam.reference(base)
    split = seam.attach_behavior(seam.split_samples())

    # 前置自证：split 后逐位 current 与 base 一致（共享前缀重放语义成立）
    torch = seam.torch
    assert torch.allclose(
        torch.cat([split[0]["current"], split[1]["current"]]), base[0]["current"], atol=1e-12
    )

    result = seam.run_step(split, micro_batch_indices=[[0, 1, 2]])
    assert result.loss_reduced["loss"] == pytest.approx(ref.loss, rel=1e-9)
    _assert_grads_close(torch, result.grads, ref_grads, label="branch split")


def test_metamorphic_sibling_across_microbatches_invariance(seam):
    """同 execution 的 sibling 分散到不同 microbatch（B4 核心场景：整 rollout
    分母由 sibling 共享的 rollout_mask_sums 重构）：loss/梯度不变。"""
    base = seam.attach_behavior(seam.base_samples())
    ref, ref_grads = seam.reference(base)
    split = seam.attach_behavior(seam.split_samples())

    # microbatch 0 = [s0a],microbatch 1 = [s0b, s1]——rid 100 的 sibling 跨
    # microbatch。注意分组不能让 s0b 单独成 microbatch：它仅有的 provenance 位
    # 恰好被信任区间拒绝（accepted=0）,会先触发 B6 microbatch 粒度 fail-stop
    # ——这正是 test_b6_partial_zero_microbatch_known_deviation 固定的已知偏差。
    result = seam.run_step(split, micro_batch_indices=[[0], [1, 2]])
    assert result.loss_reduced["loss"] == pytest.approx(ref.loss, rel=1e-9)
    _assert_grads_close(seam.torch, result.grads, ref_grads, label="sibling 跨 microbatch")


def test_metamorphic_dp_partition_invariance(seam):
    """DP partition：两半各自独立跑（num_rollouts 保持全局 N_exec=2）,loss 与
    梯度按和重构全批。真实 DDP 的 ÷DP size 与 dispatcher 的 ×intra_dp_cp.size
    相消,故"和"即是多卡语义的单进程等价;进程组机制归硬件段。"""
    base = seam.attach_behavior(seam.base_samples())
    ref, ref_grads = seam.reference(base)

    half_a = seam.run_step([base[0]], micro_batch_size=1, num_rollouts=NUM_EXECUTIONS)
    half_b = seam.run_step([base[1]], micro_batch_size=1, num_rollouts=NUM_EXECUTIONS)

    torch = seam.torch
    combined_loss = half_a.loss_reduced["loss"] + half_b.loss_reduced["loss"]
    assert combined_loss == pytest.approx(ref.loss, rel=1e-9)
    combined = {n: half_a.grads[n] + half_b.grads[n] for n in half_a.grads}
    _assert_grads_close(torch, combined, ref_grads, label="DP partition")


# ---------------------------------------------------------------------------
# B6：spike fail-stop（optimizer 前终止,状态全不前进）
# ---------------------------------------------------------------------------


def _assert_no_state_advance(seam, harness):
    """B6 状态验收：参数逐元素不变、AdamW state 空（从未 step,连 weight decay
    的隐式改参也没发生）、scheduler 无 increment、weight version 代理不前进。"""
    torch = seam.torch
    for n, p in harness.model.named_parameters():
        assert torch.equal(p.detach(), harness.params_before[n]), f"参数 {n} 被改动"
    assert len(harness.optimizer.inner.state) == 0  # AdamW 从未 step
    assert harness.optimizer.captured_grads is None  # optimizer.step 未被调用
    assert harness.scheduler.increments == []
    assert harness.weight_version == 0


def test_b6_all_rejected_batch_fail_stops_without_state_advance(seam):
    """全拒 batch：FaithfulDisZeroAcceptedStop 从真实 seam 无捕获抛出
    （pytest.raises 在 train_one_step 外层接到 = dispatcher/megatron 链未吞
    异常;更外层 model.train/actor.py 无 try/except 已源码核实）;参数/
    optimizer state/scheduler/weight version 全不前进。"""
    from repoharness2.adapters.miles.faithful_dis_loss import FaithfulDisZeroAcceptedStop

    samples = seam.attach_behavior(seam.base_samples(), ratio_override=10.0)  # 全部 out-of-trust
    harness = seam.make_harness(samples, micro_batch_size=2)

    with pytest.raises(FaithfulDisZeroAcceptedStop) as exc:
        harness.step()
    assert exc.value.reason_code == "dis_zero_accepted_fail_stop"
    _assert_no_state_advance(seam, harness)

    # 正控（探针灵敏度）：同一装配跑正常批,参数确实前进
    good = seam.attach_behavior(seam.base_samples())
    good_harness = seam.make_harness(good, micro_batch_size=2)
    result = good_harness.step()
    assert result.weight_version == 1
    assert len(good_harness.optimizer.inner.state) > 0
    torch = seam.torch
    assert any(
        not torch.equal(p.detach(), good_harness.params_before[n])
        for n, p in good_harness.model.named_parameters()
    )


def test_b6_partial_zero_microbatch_known_deviation(seam):
    """已知偏差固定（如实说明,不修）：microbatch 粒度 fail-stop 下,"某个
    microbatch 全拒但全局 accepted>0" 也会停——FA-4 §4 的 skip 协议会跳过该
    microbatch 继续训练,spike 版有意不建跨 microbatch 协议（宁可误停,不让
    零梯度 microbatch 静默经过 optimizer）。顺序取 [正常 mb, 全拒 mb]：正常
    mb 的 backward 已发生（梯度已累积）,仍必须在 optimizer.step 前终止且
    状态不前进。正式首训收敛为 skip 协议时,本测试的预期要翻转为"不停"。"""
    from repoharness2.adapters.miles.faithful_dis_loss import FaithfulDisZeroAcceptedStop

    base = seam.attach_behavior(seam.base_samples())
    base[0]["behavior"] = base[0]["current"] - 10.0  # s0 全拒;s1 正常（2/3 accepted）
    harness = seam.make_harness(base, micro_batch_indices=[[1], [0]])

    with pytest.raises(FaithfulDisZeroAcceptedStop):
        # microbatch 0 = [s1]（accepted=2,梯度已累积）,microbatch 1 = [s0]（全拒）
        harness.step()
    _assert_no_state_advance(seam, harness)
