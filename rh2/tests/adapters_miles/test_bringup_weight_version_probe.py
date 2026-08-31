"""V3 审计移交收口：`BringupService._latest_engine_version` 双端点探测回归。

背景（router_targeting_audit.md §3 登记项）：钉死的 SGLANG_COMMIT=4e230c3d
（v0.5.18 线，integration manifest `sglang_commit`）中 `/get_weight_version`
路由仍注册但 handler **无条件抛 HTTPException(404 deprecated)**，current 版本
改由 `/model_info` 返回体的 "weight_version" 键承载——修复前的单端点探测对
钉死引擎 100% 失败：`RH2_REQUIRE_REAL_WEIGHT_VERSIONS=1` 下 finalize 必
fail-closed 崩溃（单 engine 也炸），bring-up 链则每次静默降级到历史观测。

本文件用**真实回环 HTTP server**（不是 monkeypatch requests）钉死修复后的
探测语义，形态与探测顺序对齐引擎侧 `sglang_engine.get_weight_version`
（reference/miles-rh2-integration/miles/backends/sglang_utils/
sglang_engine.py:578，先 `/model_info` 后 `/get_weight_version`）：

1. 仅新端点（钉死引擎形态：`/model_info` 200、旧端点 404 deprecated）→ 通过，
   且只发一次请求（顺序先新后旧的直接证据）；
2. 仅旧端点（未更名旧引擎形态：`/model_info` 无路由 404）→ fallback 通过；
3. 双端点全灭 + require_real=True → RuntimeError fail-closed（不许历史观测
   冒充 current）；
4. 双端点全灭 + require_real=False（bring-up 链）→ 如实降级：registry 最大
   观测值，再无则启动探针值（既有降级语义不因双端点改动漂移）。

被测方法依赖面窄（sglang_url / _require_real_weight_versions / registry /
policy_version），用最小 stub 载体绑定 BringupService 的真实方法体——完整
构造 BringupService 需要 tokenizer 缓存（见 test_bringup_vendor_only.py 的
skip 条件），与本探测语义无关。
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

# 钉死引擎 / 旧引擎的两种真实响应形态（body 摘自 sglang@4e230c3d
# http_server.py 与 FastAPI 默认 404 形态，多余键有意保留——探测只许取
# "weight_version" 键，不得依赖 body 只有一个键）。
_MODEL_INFO_OK = (200, {"model_path": "Qwen/Qwen3-4B", "weight_version": "7"})
_OLD_ENDPOINT_OK = (200, {"weight_version": "5"})
_DEPRECATED_404 = (
    404,
    {
        "detail": "Endpoint '/get_weight_version' or '/weight_version' is "
        "deprecated. Please use '/model_info' instead."
    },
)
_NO_ROUTE_404 = (404, {"detail": "Not Found"})


class _FakeEngine:
    """回环 HTTP server：path -> (status, json body)，并记录请求顺序。"""

    def __init__(self, routes: dict[str, tuple[int, dict]]) -> None:
        self.routes = routes
        self.requests_seen: list[str] = []
        fake = self

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 —— http.server 固定命名
                fake.requests_seen.append(self.path)
                status, body = fake.routes.get(self.path, _NO_ROUTE_404)
                payload = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *a) -> None:  # 静音
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


@pytest.fixture
def fake_engine():
    engines: list[_FakeEngine] = []

    def _make(routes: dict[str, tuple[int, dict]]) -> _FakeEngine:
        eng = _FakeEngine(routes)
        engines.append(eng)
        return eng

    yield _make
    for eng in engines:
        eng.close()


def _mk_probe(url: str, *, require_real: bool, registry_versions=None):
    """绑定 BringupService 真实方法体的最小载体（依赖面见模块 docstring）。"""

    import repoharness2.adapters.slime.bringup as bringup

    class _Registry:
        def snapshot_weight_versions(self):
            return dict(registry_versions or {})

    class _Probe:
        _latest_engine_version = bringup.BringupService._latest_engine_version
        _registry_max_version = bringup.BringupService._registry_max_version

    probe = _Probe()
    probe.sglang_url = url
    probe._require_real_weight_versions = require_real
    probe.registry = _Registry()
    probe.policy_version = "step_0"
    return probe


def test_probe_new_endpoint_only(fake_engine):
    """钉死引擎形态：/model_info 在场即命中，旧端点一次都不该被打。"""

    eng = fake_engine(
        {"/model_info": _MODEL_INFO_OK, "/get_weight_version": _DEPRECATED_404}
    )
    probe = _mk_probe(eng.url, require_real=True)
    assert probe._latest_engine_version() == "7"
    # 顺序证据：先新后旧（引擎侧 sglang_engine.py:578 同款）——新端点 200
    # 后不再退回旧端点
    assert eng.requests_seen == ["/model_info"]


def test_probe_old_endpoint_fallback(fake_engine):
    """未更名旧引擎形态：/model_info 无路由 404，fallback 旧端点取值。"""

    eng = fake_engine({"/get_weight_version": _OLD_ENDPOINT_OK})
    probe = _mk_probe(eng.url, require_real=True)
    assert probe._latest_engine_version() == "5"
    assert eng.requests_seen == ["/model_info", "/get_weight_version"]


def test_probe_both_missing_fail_closed_when_required(fake_engine):
    """双端点全灭 + RH2_REQUIRE_REAL_WEIGHT_VERSIONS=1：仍 fail-closed。"""

    eng = fake_engine(
        {"/model_info": _NO_ROUTE_404, "/get_weight_version": _DEPRECATED_404}
    )
    probe = _mk_probe(
        eng.url, require_real=True, registry_versions={"sid": ["3"]}
    )
    with pytest.raises(RuntimeError, match="fail-closed"):
        probe._latest_engine_version()
    # 拒绝发生在两端点都真实试过之后（不是打一个就放弃）
    assert eng.requests_seen == ["/model_info", "/get_weight_version"]


def test_probe_both_missing_degrades_in_bringup_mode(fake_engine):
    """双端点全灭 + bring-up 链：既有降级语义不漂移。

    registry 有观测 → 最大观测值；无观测 → 启动探针值（policy_version）。
    """

    eng = fake_engine({})
    with_registry = _mk_probe(
        eng.url, require_real=False, registry_versions={"sid": ["2", "3"]}
    )
    assert with_registry._latest_engine_version() == "3"

    bare = _mk_probe(eng.url, require_real=False)
    assert bare._latest_engine_version() == "step_0"
