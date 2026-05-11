from __future__ import annotations

import time

import pytest

from repo_harness.model_client.providers.common import (
    ProviderRequestError,
    read_response_text_with_deadline,
)
from repo_harness.model_client.providers.deepseek import (
    _read_error_payload as _read_deepseek_error_payload,
)


def test_deadline_transport_reads_chunked_response_before_deadline() -> None:
    response = _ChunkedResponse([b'{"ok":', b" true}"])

    text = read_response_text_with_deadline(response, timeout_seconds=1.0, chunk_size=4)

    assert text == '{"ok": true}'


def test_deadline_transport_raises_provider_timeout_after_absolute_deadline() -> None:
    response = _ChunkedResponse([b"a", b"b", b"c"], delay_per_read=0.04)

    with pytest.raises(ProviderRequestError) as exc:
        read_response_text_with_deadline(response, timeout_seconds=0.05, chunk_size=1)

    assert exc.value.info.model_error_type == "provider_timeout"
    assert exc.value.info.payload == {"deadline_exceeded": True}


def test_deadline_transport_maps_underlying_read_timeout_to_provider_timeout() -> None:
    response = _TimeoutResponse()

    with pytest.raises(ProviderRequestError) as exc:
        read_response_text_with_deadline(response, timeout_seconds=1.0, chunk_size=1)

    assert exc.value.info.model_error_type == "provider_timeout"
    assert exc.value.info.payload == {"deadline_exceeded": False}


def test_deadline_transport_reuses_deadline_after_elapsed_setup_time() -> None:
    response = _ChunkedResponse([b'{"ok": true}'], delay_per_read=0.02)
    deadline = time.monotonic() + 0.05
    time.sleep(0.04)

    with pytest.raises(ProviderRequestError) as exc:
        read_response_text_with_deadline(response, deadline_monotonic=deadline, chunk_size=16)

    assert exc.value.info.model_error_type == "provider_timeout"


def test_http_error_payload_read_is_deadline_aware() -> None:
    error_response = _SlowHttpErrorBody(delay_per_read=0.03)
    deadline = time.monotonic() + 0.02

    with pytest.raises(ProviderRequestError) as exc:
        _read_deepseek_error_payload(error_response, deadline_monotonic=deadline)  # type: ignore[arg-type]

    assert exc.value.info.model_error_type == "provider_timeout"


class _ChunkedResponse:
    def __init__(self, chunks: list[bytes], *, delay_per_read: float = 0.0) -> None:
        self.chunks = list(chunks)
        self.delay_per_read = delay_per_read

    def read(self, _size: int) -> bytes:
        if self.delay_per_read:
            time.sleep(self.delay_per_read)
        if not self.chunks:
            return b""
        return self.chunks.pop(0)


class _SlowHttpErrorBody:
    code = 429

    def __init__(self, *, delay_per_read: float) -> None:
        self.delay_per_read = delay_per_read
        self.chunks = [b'{"error": {"message": "slow"}}']

    def read(self, _size: int | None = None) -> bytes:
        time.sleep(self.delay_per_read)
        if not self.chunks:
            return b""
        return self.chunks.pop(0)


class _TimeoutResponse:
    def read(self, _size: int) -> bytes:
        raise TimeoutError("socket timed out")
