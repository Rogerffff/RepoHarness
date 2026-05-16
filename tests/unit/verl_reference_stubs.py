"""轻量依赖桩，用于加载 reference/verl 的真实 agent_loop.py。"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any


class FakeTensor:
    def __init__(self, data: Any, dtype: Any = None) -> None:
        self.data = _to_plain_data(data)
        self.dtype = dtype

    @property
    def shape(self) -> tuple[int, ...]:
        return _shape(self.data)

    def dim(self) -> int:
        return len(self.shape)

    def size(self, dim: int | None = None):
        return self.shape if dim is None else self.shape[dim]

    def unsqueeze(self, dim: int) -> "FakeTensor":
        if dim in {0, -len(self.shape) - 1}:
            return FakeTensor([self.data], dtype=self.dtype)
        if dim == 1 and self.dim() == 1:
            return FakeTensor([[item] for item in self.data], dtype=self.dtype)
        raise NotImplementedError(f"FakeTensor.unsqueeze({dim}) is not implemented")

    def squeeze(self, dim: int | None = None) -> "FakeTensor":
        if dim in {None, 0} and isinstance(self.data, list) and len(self.data) == 1:
            return FakeTensor(self.data[0], dtype=self.dtype)
        return self

    def sum(self, dim: int | None = None) -> "FakeTensor":
        if dim is None:
            return FakeTensor(_sum_nested(self.data), dtype=self.dtype)
        if dim == 1:
            return FakeTensor([sum(row) for row in self.data], dtype=self.dtype)
        if dim == 0:
            return FakeTensor([sum(row[index] for row in self.data) for index in range(len(self.data[0]))])
        raise NotImplementedError(f"FakeTensor.sum(dim={dim}) is not implemented")

    def tolist(self):
        return _to_plain_data(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self):
        return iter(self.data)

    def __getitem__(self, key):
        if isinstance(key, tuple):
            rows, cols = key
            selected_rows = _select(self.data, rows)
            if selected_rows and not isinstance(selected_rows[0], list):
                selected_rows = [selected_rows]
            return FakeTensor([_select(row, cols) for row in selected_rows], dtype=self.dtype)
        return self.data[key]

    def __setitem__(self, key, value) -> None:
        value_data = _to_plain_data(value)
        if isinstance(key, tuple):
            rows, cols = key
            row_indices = _indices(rows, len(self.data))
            col_indices = _to_plain_data(cols)
            if not isinstance(col_indices, list):
                col_indices = [col_indices] * len(row_indices)
            if not isinstance(value_data, list):
                value_data = [value_data] * len(row_indices)
            for row, col, item in zip(row_indices, col_indices, value_data, strict=True):
                self.data[row][col] = item
            return
        self.data[key] = value_data

    def __mul__(self, other: Any) -> "FakeTensor":
        return FakeTensor(_binary_op(self.data, _to_plain_data(other), lambda a, b: a * b), dtype=self.dtype)

    def __sub__(self, other: Any) -> "FakeTensor":
        return FakeTensor(_binary_op(self.data, _to_plain_data(other), lambda a, b: a - b), dtype=self.dtype)

    def __repr__(self) -> str:
        return f"FakeTensor({self.data!r})"


class FakeArray(list):
    @property
    def shape(self) -> tuple[int, ...]:
        return _shape(list(self))

    def tolist(self):
        return list(self)


class TensorDict(dict):
    def __init__(self, data: dict[str, Any], batch_size: int | None = None) -> None:
        super().__init__(data)
        self.batch_size = batch_size


class DataProto:
    def __init__(self, batch: Any = None, non_tensor_batch: dict | None = None, meta_info: dict | None = None) -> None:
        self.batch = batch
        self.non_tensor_batch = non_tensor_batch or {}
        self.meta_info = meta_info or {}


class FakeTokenizer:
    pad_token_id = 0

    def __init__(self) -> None:
        self.padding_side = "right"

    def pad(
        self,
        inputs: dict[str, list[int]],
        *,
        padding: str,
        max_length: int,
        return_tensors: str,
        return_attention_mask: bool,
    ) -> dict[str, FakeTensor]:
        ids = list(inputs["input_ids"])
        pad_size = max_length - len(ids)
        if pad_size < 0:
            raise ValueError("input longer than max_length")
        if self.padding_side == "left":
            padded = [self.pad_token_id] * pad_size + ids
            attention = [0] * pad_size + [1] * len(ids)
        else:
            padded = ids + [self.pad_token_id] * pad_size
            attention = [1] * len(ids) + [0] * pad_size
        result = {"input_ids": FakeTensor(padded)}
        if return_attention_mask:
            result["attention_mask"] = FakeTensor(attention)
        return result

    def decode(self, ids: Any, skip_special_tokens: bool = True) -> str:
        return " ".join(str(item) for item in _to_plain_data(ids))


class RolloutConfig:
    def __init__(self, prompt_length: int, response_length: int) -> None:
        self.prompt_length = prompt_length
        self.response_length = response_length


def install_reference_verl_stubs(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    reference_root = repo_root / "reference" / "verl"
    monkeypatch.syspath_prepend(str(reference_root))
    _install_verl_namespace_packages(monkeypatch, reference_root)

    _install_numpy(monkeypatch)
    _install_torch(monkeypatch)
    _install_simple_modules(monkeypatch)

    for module_name in list(sys.modules):
        if module_name.startswith("verl.experimental.agent_loop.agent_loop"):
            monkeypatch.delitem(sys.modules, module_name, raising=False)


def _install_verl_namespace_packages(monkeypatch, reference_root: Path) -> None:
    verl_module = types.ModuleType("verl")
    verl_module.__path__ = [str(reference_root / "verl")]
    experimental_module = types.ModuleType("verl.experimental")
    experimental_module.__path__ = [str(reference_root / "verl" / "experimental")]
    agent_loop_module = types.ModuleType("verl.experimental.agent_loop")
    agent_loop_module.__path__ = [str(reference_root / "verl" / "experimental" / "agent_loop")]
    monkeypatch.setitem(sys.modules, "verl", verl_module)
    monkeypatch.setitem(sys.modules, "verl.experimental", experimental_module)
    monkeypatch.setitem(sys.modules, "verl.experimental.agent_loop", agent_loop_module)


def _install_numpy(monkeypatch) -> None:
    numpy_module = types.ModuleType("numpy")
    numpy_module.ndarray = FakeArray
    numpy_module.int32 = int
    numpy_module.array = lambda value, dtype=None: FakeArray(_to_plain_data(value))
    numpy_module.empty = lambda size, dtype=None: FakeArray([None] * size)
    monkeypatch.setitem(sys.modules, "numpy", numpy_module)


def _install_torch(monkeypatch) -> None:
    torch_module = types.ModuleType("torch")
    torch_module.int64 = "int64"
    torch_module.float32 = "float32"
    torch_module.long = "long"
    torch_module.Tensor = FakeTensor
    torch_module.tensor = lambda value, dtype=None: FakeTensor(value, dtype=dtype)
    torch_module.zeros_like = lambda value, dtype=None: FakeTensor(_zeros_like(_to_plain_data(value)), dtype=dtype)
    torch_module.ones_like = lambda value, dtype=None: FakeTensor(_ones_like(_to_plain_data(value)), dtype=dtype)
    torch_module.zeros = lambda *shape, dtype=None: FakeTensor(_zeros_for_shape(shape), dtype=dtype)
    torch_module.arange = lambda size: FakeTensor(list(range(size)))
    torch_module.cat = _torch_cat
    torch_module.from_numpy = lambda value: FakeTensor(value)
    monkeypatch.setitem(sys.modules, "torch", torch_module)


def _install_simple_modules(monkeypatch) -> None:
    hydra_module = types.ModuleType("hydra")
    hydra_utils_module = types.ModuleType("hydra.utils")
    hydra_utils_module.instantiate = lambda *args, **kwargs: None
    hydra_module.utils = hydra_utils_module
    monkeypatch.setitem(sys.modules, "hydra", hydra_module)
    monkeypatch.setitem(sys.modules, "hydra.utils", hydra_utils_module)

    ray_module = types.ModuleType("ray")
    ray_module.actor = types.SimpleNamespace(ActorHandle=object)
    monkeypatch.setitem(sys.modules, "ray", ray_module)

    omegaconf_module = types.ModuleType("omegaconf")
    omegaconf_module.DictConfig = dict
    omegaconf_module.OmegaConf = types.SimpleNamespace(to_container=lambda value, **kwargs: value)
    monkeypatch.setitem(sys.modules, "omegaconf", omegaconf_module)

    pil_module = types.ModuleType("PIL")
    pil_image_module = types.ModuleType("PIL.Image")
    pil_image_module.Image = type("Image", (), {})
    pil_module.Image = pil_image_module
    monkeypatch.setitem(sys.modules, "PIL", pil_module)
    monkeypatch.setitem(sys.modules, "PIL.Image", pil_image_module)

    transformers_module = types.ModuleType("transformers")
    transformers_module.AutoProcessor = object
    transformers_module.AutoTokenizer = object
    monkeypatch.setitem(sys.modules, "transformers", transformers_module)

    tensordict_module = types.ModuleType("tensordict")
    tensordict_module.TensorDict = TensorDict
    monkeypatch.setitem(sys.modules, "tensordict", tensordict_module)

    _module(monkeypatch, "verl.experimental.agent_loop.utils", resolve_config_path=lambda *args, **kwargs: None)
    _module(monkeypatch, "verl.protocol", DataProto=DataProto)
    _module(monkeypatch, "verl.trainer.distillation", is_distillation_enabled=lambda *args, **kwargs: False)
    _module(
        monkeypatch,
        "verl.utils.chat_template",
        apply_chat_template=lambda *args, **kwargs: None,
        initialize_system_prompt=lambda *args, **kwargs: None,
    )
    _module(monkeypatch, "verl.utils.config", omega_conf_to_dataclass=lambda *args, **kwargs: None)
    _module(
        monkeypatch,
        "verl.utils.dataset.rl_dataset",
        RLHFDataset=object,
        get_dataset_class=lambda *args, **kwargs: object,
    )
    _module(monkeypatch, "verl.utils.model", compute_position_id_with_mask=_compute_position_id_with_mask)
    _module(monkeypatch, "verl.utils.profiler", simple_timer=lambda *args, **kwargs: _NullTimer())
    _module(
        monkeypatch,
        "verl.utils.ray_utils",
        auto_await=lambda value: value,
        get_event_loop=lambda: None,
    )
    _module(
        monkeypatch,
        "verl.utils.rollout_trace",
        RolloutTraceConfig=object,
        rollout_trace_attr=lambda *args, **kwargs: _NullTimer(),
    )
    _module(monkeypatch, "verl.utils.tokenizer", normalize_token_ids=lambda value: value)
    _module(monkeypatch, "verl.workers.config", HFModelConfig=object, RolloutConfig=object)
    _module(monkeypatch, "verl.workers.rollout.llm_server", LLMServerClient=object)


def _module(monkeypatch, name: str, **attrs: Any) -> types.ModuleType:
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)
    return module


class _NullTimer:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None


def _compute_position_id_with_mask(attention_mask: FakeTensor) -> FakeTensor:
    rows = []
    for row in attention_mask.tolist():
        position = 0
        output_row = []
        for mask in row:
            output_row.append(position if mask else 0)
            if mask:
                position += 1
        rows.append(output_row)
    return FakeTensor(rows)


def _torch_cat(values: list[FakeTensor], dim: int = 0) -> FakeTensor:
    datas = [_to_plain_data(value) for value in values]
    if not datas:
        return FakeTensor([])
    if dim == 0:
        output = []
        for data in datas:
            if data and isinstance(data[0], list):
                output.extend(data)
            else:
                output.extend(data)
        return FakeTensor(output)
    if dim == 1:
        return FakeTensor([sum((list(data[row]) for data in datas), []) for row in range(len(datas[0]))])
    raise NotImplementedError(f"torch.cat(dim={dim}) is not implemented")


def _to_plain_data(value: Any) -> Any:
    if isinstance(value, FakeTensor):
        return _to_plain_data(value.data)
    if isinstance(value, FakeArray):
        return [_to_plain_data(item) for item in value]
    if isinstance(value, list):
        return [_to_plain_data(item) for item in value]
    if isinstance(value, tuple):
        return [_to_plain_data(item) for item in value]
    return value


def _shape(data: Any) -> tuple[int, ...]:
    if isinstance(data, list):
        if not data:
            return (0,)
        return (len(data), *_shape(data[0]))
    return ()


def _select(data: list, key: Any):
    if isinstance(key, slice):
        return data[key]
    if isinstance(key, FakeTensor):
        return [data[index] for index in key.tolist()]
    if isinstance(key, list):
        return [data[index] for index in key]
    return data[key]


def _indices(key: Any, length: int) -> list[int]:
    if isinstance(key, slice):
        return list(range(length))[key]
    if isinstance(key, FakeTensor):
        return key.tolist()
    if isinstance(key, list):
        return key
    return [key]


def _binary_op(left: Any, right: Any, op):
    if isinstance(left, list) and isinstance(right, list):
        return [_binary_op(l_item, r_item, op) for l_item, r_item in zip(left, right, strict=True)]
    if isinstance(left, list):
        return [_binary_op(item, right, op) for item in left]
    if isinstance(right, list):
        return [_binary_op(left, item, op) for item in right]
    return op(left, right)


def _sum_nested(data: Any) -> int | float:
    if isinstance(data, list):
        return sum(_sum_nested(item) for item in data)
    return data


def _zeros_like(data: Any):
    if isinstance(data, list):
        return [_zeros_like(item) for item in data]
    return 0


def _ones_like(data: Any):
    if isinstance(data, list):
        return [_ones_like(item) for item in data]
    return 1


def _zeros_for_shape(shape: tuple[int, ...]):
    if not shape:
        return 0
    size, *rest = shape
    return [_zeros_for_shape(tuple(rest)) for _ in range(size)]
