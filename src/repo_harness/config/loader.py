"""RunConfig YAML 读取。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from repo_harness.config.schemas import RunConfig
from repo_harness.errors import ConfigError


def load_run_config(
    path: str | Path,
    *,
    for_batch: bool = False,
    output_dir: str | Path | None = None,
) -> RunConfig:
    """读取并校验 RunConfig。"""

    config_path = Path(path)
    try:
        raw: Any = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"无法读取运行配置：{config_path}") from exc
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ConfigError("RunConfig 文件顶层必须是 YAML mapping。")
    try:
        config = RunConfig.model_validate(raw).with_output_dir(output_dir)
    except ValidationError as exc:
        raise ConfigError(str(exc)) from exc
    if for_batch:
        config.ensure_batch_safe()
    return config
