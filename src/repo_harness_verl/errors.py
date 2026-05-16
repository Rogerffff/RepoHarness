"""Stage 11 verl adapter errors."""

from __future__ import annotations


class RepoHarnessVerlAdapterError(ValueError):
    """表示 RepoHarness 的 verl adapter 无法安全完成当前样本。"""


class RepoHarnessVerlRequestMappingError(RepoHarnessVerlAdapterError):
    """表示 verl kwargs 无法安全映射为 RepoHarnessEpisodeRequest。"""


class RepoHarnessVerlGatewayError(RepoHarnessVerlAdapterError):
    """表示 verl LLMServerClient 输出无法安全映射为 LLMGatewayResponse。"""
