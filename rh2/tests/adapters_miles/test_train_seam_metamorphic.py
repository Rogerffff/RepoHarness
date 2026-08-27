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

F2（全局零信号语义,取代 B6 spike fail-stop;规格 = tmp/F2修复建议.md 与
codex 零信号建议 §5-§7）：per-microbatch accepted=0 不再抛异常（loss 层只记
dis_zero_contribution_microbatch 指标,返回带 autograd 图的精确零贡献）;
"零梯度不得静默走 AdamW"改由 miles train_one_step（rh2-integration-v2,
commit 620aa6924）在**全部 microbatch 与梯度归约完成后、optimizer 之前**
判定：累计梯度全局精确为零 → SKIPPED_ZERO_SIGNAL（不 optimizer.step/不
scheduler.step/batch 已消费/连续跳过熔断可配）,非零有限 → NORMAL,非有限
→ 既有错误路径（数据损坏仍 fail-stop,不降级）。本文件 F2 区段按规格 §7
用例 A~F 经真实 train_one_step seam 验收,主验收 = momentum-state:先正常
AdamW 更新形成 exp_avg/exp_avg_sq,再注入全局零梯度 step,参数/optimizer
state/scheduler/weight version 全不变,下一非零 step 继续正常。weight
version 代理 = F2 后 driver（train_async.py commit 51e3cd969）只在
weights_dirty 时 publish——harness 仅在 NORMAL outcome 后推进版本号。
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
        _zero_grads 会清梯度,不在这里捕获就取不到）。step_calls 计数供 F2
        断言"skip 步没有触碰 optimizer.step"。"""

        def __init__(self, model):
            self.inner = torch.optim.AdamW(model.parameters(), lr=0.05, weight_decay=0.1)
            self._model = model
            self.captured_grads = None
            self.step_calls = 0

        def zero_grad(self):
            self.inner.zero_grad()

        def step(self):
            self.step_calls += 1
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
        """真实 seam 的可持有装配：异常后仍可检查 model/optimizer/scheduler
        （状态探针需要）。支持连续多次 step（F2 momentum-state 主验收:每次
        step 重建 DataIterator,model/optimizer/scheduler 持续存活）。

        weight version 代理（F2 语义）：miles driver（train_async.py commit
        51e3cd969）只在 weights_dirty=True 时 publish/递增 weight_version,
        单 optimizer-step 情形 weights_dirty ⇔ outcome==NORMAL——因此 harness
        仅在 NORMAL 后推进版本号;SKIPPED_ZERO_SIGNAL 与异常都不推进。"""

        def __init__(self, samples, *, micro_batch_size=None, micro_batch_indices=None,
                     num_rollouts=NUM_EXECUTIONS, args_extra=None):
            self.args = mk_args(num_rollouts)
            for k, v in (args_extra or {}).items():
                setattr(self.args, k, v)
            self.num_rollouts = num_rollouts
            self._default_layout = (samples, micro_batch_size, micro_batch_indices)
            self.model = TinyModel()
            self.params_before = {n: p.detach().clone() for n, p in self.model.named_parameters()}
            self.optimizer = FakeOptimizer(self.model)
            self.scheduler = FakeScheduler()
            self.weight_version = 0

        @staticmethod
        def _mk_iterator(samples, micro_batch_size, micro_batch_indices, rollout_data_mutator=None):
            rollout_data = mk_rollout_data(samples)
            if rollout_data_mutator is not None:
                rollout_data_mutator(rollout_data)  # 用例 E:注入列级缺失/损坏
            iterator = data_mod.DataIterator(
                rollout_data,
                micro_batch_size=micro_batch_size,
                micro_batch_indices=micro_batch_indices,
            )
            if micro_batch_indices is not None:
                n_mb = len(micro_batch_indices)
            else:
                assert len(samples) % micro_batch_size == 0
                n_mb = len(samples) // micro_batch_size
            return iterator, n_mb

        def step(self, samples=None, *, micro_batch_size=None, micro_batch_indices=None,
                 rollout_data_mutator=None) -> StepResult:
            """跑一个真实 train_one_step。不带参数 = 用构造时的批;带 samples
            = 换新批（momentum 验收在同一 model/optimizer 上交替喂正常批与
            零信号批）;rollout_data_mutator 在 DataIterator 构造前改
            rollout_data（用例 E 的字段缺失注入）。"""
            if samples is None:
                samples, micro_batch_size, micro_batch_indices = self._default_layout
            iterator, n_mb = self._mk_iterator(
                samples, micro_batch_size, micro_batch_indices, rollout_data_mutator
            )
            args_holder["args"] = self.args
            loss_reduced, _grad_norm, outcome = model_mod.train_one_step(
                self.args, 0, 0, [iterator], [self.model], self.optimizer,
                self.scheduler, n_mb, self.num_rollouts, witness_info=None, attempt=0,
            )
            if outcome == model_mod.TrainStepOutcome.NORMAL:
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
    # microbatch。（历史注：B6 时代这里不能让 s0b 单独成 microbatch,否则
    # per-microbatch fail-stop 误停;F2 后零贡献 microbatch 合法继续,分组
    # 约束已消失——见下方 test_f2_case_a_*。本测试保持原分组,只验归约不变性。）
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
# F2：全局零信号语义（规格 §7 用例 A~F + momentum-state 主验收,经真实 seam）
# ---------------------------------------------------------------------------


def _assert_fresh_no_state_advance(seam, harness):
    """从未成功 step 的装配：参数逐元素不变、AdamW state 空（连 weight decay
    的隐式改参也没发生）、optimizer.step 零调用、scheduler 无 increment、
    weight version 代理不前进。"""
    torch = seam.torch
    for n, p in harness.model.named_parameters():
        assert torch.equal(p.detach(), harness.params_before[n]), f"参数 {n} 被改动"
    assert len(harness.optimizer.inner.state) == 0  # AdamW 从未 step
    assert harness.optimizer.step_calls == 0  # optimizer.step 未被调用
    assert harness.scheduler.increments == []
    assert harness.weight_version == 0


def _state_snapshot(seam, harness):
    """momentum 验收用全量状态快照：参数、AdamW state（exp_avg/exp_avg_sq/
    step 计数,逐参数名索引）、scheduler increments、weight version、step 调用数。"""
    torch = seam.torch
    opt_state = {}
    for n, p in harness.model.named_parameters():
        state = harness.optimizer.inner.state.get(p)
        if state:
            opt_state[n] = {
                k: (v.clone() if torch.is_tensor(v) else v) for k, v in state.items()
            }
    return dict(
        params={n: p.detach().clone() for n, p in harness.model.named_parameters()},
        opt_state=opt_state,
        sched=list(harness.scheduler.increments),
        weight_version=harness.weight_version,
        step_calls=harness.optimizer.step_calls,
    )


def _assert_state_equals_snapshot(seam, harness, snap):
    torch = seam.torch
    for n, p in harness.model.named_parameters():
        assert torch.equal(p.detach(), snap["params"][n]), f"参数 {n} 在 skip 步被改动"
    current = _state_snapshot(seam, harness)["opt_state"]
    assert sorted(current) == sorted(snap["opt_state"])
    for n, state in snap["opt_state"].items():
        assert sorted(current[n]) == sorted(state), n
        for k, v in state.items():
            if torch.is_tensor(v):
                assert torch.equal(current[n][k], v), f"optimizer state {n}.{k} 在 skip 步被改动"
            else:
                assert current[n][k] == v, f"optimizer state {n}.{k} 在 skip 步被改动"
    assert harness.scheduler.increments == snap["sched"]
    assert harness.weight_version == snap["weight_version"]
    assert harness.optimizer.step_calls == snap["step_calls"]


def _zero_advantage_samples(seam):
    """规格用例 B 的 trainer 防御形态：reward 全相等的组 → GRPO advantage 全
    0。绕过 rollout filter 直喂 trainer,DIS 信任判定照常（部分 token
    accepted）,但 advantage 全零 ⇒ 累计梯度精确为零。"""
    samples = seam.base_samples()
    for s in samples:
        s["adv"] = [0.0] * len(s["adv"])
    return seam.attach_behavior(samples)


def test_f2_case_a_partial_zero_microbatch_does_not_stop(seam):
    """规格 §7 用例 A：microbatch 0 零贡献 + microbatch 1 非零有限梯度 →
    作业不停止,optimizer/scheduler 各执行一次,参数变化,weight version +1。
    （原 test_b6_partial_zero_microbatch_known_deviation 的预期翻转:F2 语义
    下 per-microbatch 全拒不再停机。）"""
    torch = seam.torch
    base = seam.attach_behavior(seam.base_samples())
    base[0]["behavior"] = base[0]["current"] - 10.0  # s0 全拒;s1 正常（2/3 accepted）
    ref, ref_grads = seam.reference(base)

    harness = seam.make_harness(base, micro_batch_indices=[[1], [0]])
    # microbatch 0 = [s1]（有效梯度）,microbatch 1 = [s0]（全拒,零贡献）
    result = harness.step()

    assert result.outcome == seam.TrainStepOutcome.NORMAL
    assert result.weight_version == 1
    assert harness.optimizer.step_calls == 1
    assert harness.scheduler.increments == [NUM_EXECUTIONS]
    # 全拒 microbatch 只有零贡献,整步 loss/梯度仍与权威一致（s0 全拒 ⇒ 其
    # execution 部分和为 0）
    assert result.loss_reduced["loss"] == pytest.approx(ref.loss, rel=1e-9)
    _assert_grads_close(torch, result.grads, ref_grads, label="case A")
    # 零贡献 microbatch 计入指标：1 个零贡献 mb,聚合口径 Σ/num_rollouts = 1/2
    assert result.loss_reduced["dis_zero_contribution_microbatch"] == pytest.approx(0.5)
    assert any(
        not torch.equal(p.detach(), harness.params_before[n])
        for n, p in harness.model.named_parameters()
    )


def test_f2_case_b_zero_advantage_batch_skipped_at_optimizer_boundary(seam):
    """规格 §7 用例 B（trainer 防御半场;filter 丢弃半场见
    test_zero_signal_semantics.py）：绕过 rollout filter 的全零 advantage 组
    → 全部 microbatch 零梯度 → 整步 SKIPPED_ZERO_SIGNAL,optimizer/
    scheduler/weight version 全不动;batch 已消费,随后正常批继续可训。"""
    harness = seam.make_harness(_zero_advantage_samples(seam), micro_batch_size=2)
    result = harness.step()

    assert result.outcome == seam.TrainStepOutcome.SKIPPED_ZERO_SIGNAL
    assert result.loss_reduced == {}  # skip 步不出 loss 指标（miles 既有约定:非 NORMAL 返回空 dict）
    _assert_fresh_no_state_advance(seam, harness)

    # 恢复性正控：同一装配继续喂正常批,立即恢复正常更新（skip 没留脏状态）
    good = harness.step(seam.attach_behavior(seam.base_samples()), micro_batch_size=2)
    assert good.outcome == seam.TrainStepOutcome.NORMAL
    assert good.weight_version == 1


def test_f2_case_c_accepted_tokens_with_null_signal_skipped(seam):
    """规格 §7 用例 C：advantage 形如 [-1, 0, +1] 的组,非零 advantage 的
    token 全部落在 DIS 信任区间外,仅 advantage=0 的 token 在区间内——
    accepted>0（本构造 accepted=1,由 ratio 手工钉死:信任区间 (0.2,4.0) 开
    区间 ⇔ log 界约 (-1.609,1.386),ratio 取 [2.0, 0.0, -2.0] ⇒ out/in/out）,
    但真实累计梯度为零 ⇒ 仍准确 SKIPPED_ZERO_SIGNAL。逐 token 指标级的
    对拍（dis_accepted_tokens==1、逐位零梯度）在
    test_faithful_dis_loss.py::test_accepted_token_with_zero_advantage_no_gradient。"""
    ids, offsets = _csr([[8, 3], [9, 2], [10, 11, 12]])  # 全部多元素支持集
    samples = seam.attach_behavior([
        dict(
            tokens=[1, 2, 8, 9, 10], resp_len=3, mask=[1, 1, 1], mask_ids=ids,
            mask_offsets=offsets, ratio=[2.0, 0.0, -2.0], adv=[-1.0, 0.0, 1.0], rid=100,
        )
    ])
    harness = seam.make_harness(samples, micro_batch_size=1, num_rollouts=1)
    result = harness.step()

    assert result.outcome == seam.TrainStepOutcome.SKIPPED_ZERO_SIGNAL
    _assert_fresh_no_state_advance(seam, harness)


def test_f2_case_d_all_singleton_support_skipped(seam):
    """规格 §7 用例 D：全部 trainable token 的采样支持集都是单例——
    support-renormalized logprob 恒 0,ratio 恒 1（在信任区间内,accepted=全部）,
    但 logprob 对 logits 的梯度严格为零 ⇒ 累计梯度为零 ⇒ SKIPPED。不需要
    先建 rollout 侧 support filter,全局零梯度判定统一兜底。"""
    ids, offsets = _csr([[4], [5], [6], [7]])
    samples = seam.attach_behavior(
        [
            dict(
                tokens=[1, 2, 3, 4, 5, 6, 7], resp_len=4, mask=[1, 1, 1, 1], mask_ids=ids,
                mask_offsets=offsets, ratio=None, adv=[1.0, -0.5, 2.0, 0.7], rid=100,
            )
        ],
        ratio_override=0.0,  # 单例支持集下 current=behavior=0,ratio 恒 1
    )
    harness = seam.make_harness(samples, micro_batch_size=1, num_rollouts=1)
    result = harness.step()

    assert result.outcome == seam.TrainStepOutcome.SKIPPED_ZERO_SIGNAL
    _assert_fresh_no_state_advance(seam, harness)


def test_f2_case_e_corruption_still_fail_stops(seam):
    """规格 §7 用例 E：数据损坏不得降级成 SKIPPED_ZERO_SIGNAL——非有限
    logp、target∉support、mask 长度错位、缺 wire 字段,全部仍在 optimizer 前
    显式失败（异常沿真实 seam 无捕获传播）,且状态全不前进。"""
    from repoharness2.adapters.miles.faithful_dis_loss import FaithfulDisLossError

    torch = seam.torch

    # e1: 非有限 behavior logp
    bad = seam.attach_behavior(seam.base_samples())
    bad[0]["behavior"][1] = float("inf")
    harness = seam.make_harness(bad, micro_batch_size=2)
    with pytest.raises(FaithfulDisLossError) as exc:
        harness.step()
    assert exc.value.reason_code == "non_finite_input"
    _assert_fresh_no_state_advance(seam, harness)

    # e2: target ∉ support（传输错位/损坏）
    bad = seam.attach_behavior(seam.base_samples())
    ids, offsets = _csr([[4, 9, 10], [2, 3], [6], [7, 8]])  # 位 1 的 target 5 被换掉
    bad[0]["mask_ids"], bad[0]["mask_offsets"] = ids, offsets
    harness = seam.make_harness(bad, micro_batch_size=2)
    with pytest.raises(FaithfulDisLossError) as exc:
        harness.step()
    assert exc.value.reason_code == "target_not_in_support"
    _assert_fresh_no_state_advance(seam, harness)

    # e3: mask 覆盖长度错位（只盖 3 个 token,response 有 4）
    bad = seam.attach_behavior(seam.base_samples())
    ids, offsets = _csr([[4, 9, 10], [5, 2], [6]])
    bad[0]["mask_ids"], bad[0]["mask_offsets"] = ids, offsets
    harness = seam.make_harness(bad, micro_batch_size=2)
    with pytest.raises(FaithfulDisLossError) as exc:
        harness.step()
    assert exc.value.reason_code == "sampling_mask_length_mismatch"
    _assert_fresh_no_state_advance(seam, harness)

    # e4: 缺必要 wire 字段（rollout_log_probs 整列缺失）
    bad = seam.attach_behavior(seam.base_samples())
    harness = seam.make_harness(bad, micro_batch_size=2)
    with pytest.raises(FaithfulDisLossError) as exc:
        harness.step(rollout_data_mutator=lambda d: d.pop("rollout_log_probs"))
    assert exc.value.reason_code == "batch_column_missing"
    _assert_fresh_no_state_advance(seam, harness)
    del torch  # 仅为对齐其余用例的取用形态


def test_f2_case_f_consecutive_skip_fuse(seam):
    """规格 §7 用例 F：连续 zero-signal step 熔断,阈值可配
    （args.max_consecutive_zero_signal_steps,经 --custom-config-path 注入）。
    少于阈值继续;NORMAL step 重置计数;达到阈值抛 RuntimeError 且此前所有
    skip 都未改变权重版本。"""
    zero = _zero_advantage_samples(seam)
    harness = seam.make_harness(
        zero, micro_batch_size=2, args_extra={"max_consecutive_zero_signal_steps": 3}
    )

    # 两次 skip：未达阈值,不熔断
    for _ in range(2):
        assert harness.step().outcome == seam.TrainStepOutcome.SKIPPED_ZERO_SIGNAL
    # NORMAL step 重置连续计数
    good = harness.step(seam.attach_behavior(seam.base_samples()), micro_batch_size=2)
    assert good.outcome == seam.TrainStepOutcome.NORMAL
    snap = _state_snapshot(seam, harness)
    # 重新累计：两次 skip 仍未达阈值
    for _ in range(2):
        assert (
            harness.step(_zero_advantage_samples(seam), micro_batch_size=2).outcome
            == seam.TrainStepOutcome.SKIPPED_ZERO_SIGNAL
        )
    # 第三次连续 skip：熔断,带诊断信息;全部 skip 未改变任何状态
    with pytest.raises(RuntimeError, match="zero-signal fuse tripped"):
        harness.step(_zero_advantage_samples(seam), micro_batch_size=2)
    _assert_state_equals_snapshot(seam, harness, snap)
    assert harness.weight_version == 1  # 唯一一次 NORMAL


def test_f2_main_acceptance_momentum_state_frozen_across_zero_signal_step(seam):
    """F2 主验收（规格明示"最重要的验收不是首次空 optimizer"）：
    ① 正常 AdamW 更新一次,形成 momentum state（exp_avg/exp_avg_sq 非空）;
    ② 注入全局零梯度 step → SKIPPED_ZERO_SIGNAL,参数/exp_avg/exp_avg_sq/
       AdamW step 计数/scheduler/weight_version **全部逐元素不变**（AdamW
       weight decay 与 momentum 在零梯度下也会改参,必须证明 optimizer.step
       根本没被调用）;
    ③ 下一个非零 step 正常继续更新（参数变化、scheduler 前进、版本 +1）。"""
    torch = seam.torch
    harness = seam.make_harness(seam.attach_behavior(seam.base_samples()), micro_batch_size=2)

    # ① 正常更新形成 momentum state
    first = harness.step()
    assert first.outcome == seam.TrainStepOutcome.NORMAL
    assert first.weight_version == 1
    snap = _state_snapshot(seam, harness)
    assert snap["opt_state"], "AdamW momentum state 应已形成"
    assert any("exp_avg" in s for s in snap["opt_state"].values())
    assert any("exp_avg_sq" in s for s in snap["opt_state"].values())

    # ② 全局零梯度 step：状态全量冻结
    skipped = harness.step(_zero_advantage_samples(seam), micro_batch_size=2)
    assert skipped.outcome == seam.TrainStepOutcome.SKIPPED_ZERO_SIGNAL
    _assert_state_equals_snapshot(seam, harness, snap)

    # ③ 下一非零 step 正常继续
    third = harness.step(seam.attach_behavior(seam.base_samples()), micro_batch_size=2)
    assert third.outcome == seam.TrainStepOutcome.NORMAL
    assert third.weight_version == 2
    assert harness.optimizer.step_calls == 2
    assert len(harness.scheduler.increments) == 2
    assert any(
        not torch.equal(p.detach(), snap["params"][n])
        for n, p in harness.model.named_parameters()
    ), "非零 step 后参数应继续前进"
    # AdamW step 计数确实前进（skip 步没有偷偷推进）
    stepped = _state_snapshot(seam, harness)["opt_state"]
    for n, state in stepped.items():
        before = snap["opt_state"][n]["step"]
        after = state["step"]
        before_v = before.item() if torch.is_tensor(before) else before
        after_v = after.item() if torch.is_tensor(after) else after
        assert after_v == before_v + 1, f"{n} 的 AdamW step 计数应恰好 +1"
