"""第六组 受控依赖供应（1A + 2A）：包索引网关 `pkg_index_gateway` 的验收（Brief §2、§3、§4.5 接口清单）。

上游是本进程里的假 PEP 503 服务（记录收到的每个请求）；网关是真实 aiohttp 服务，客户端走真实 HTTP。
覆盖：页面重新生成与只签发本项目文件；文件只能走本 token 签发的 fid（已知上游文件 URL、换 dist 名、`..`、百分号编码、
大小写都绕不过 1A）；例外表只放行列出的版本；只接受 GET / HEAD、query 与请求头不到上游；撤销后 403 并中断在途下载；
释放后 404；上游故障分型；日志按 token 归 attempt 且不含 token。最后用真实 pip（系统 python3 的 pip，不在场即 skip）
经网关下载一个真 wheel，并被封禁项目拒绝。
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import shutil
import subprocess
import time
import zipfile
from pathlib import Path

import aiohttp
import pytest
from aiohttp import web

from repoharness2.adapters.slime import pkg_index_gateway as gw
from repoharness2.adapters.slime.pkg_index_gateway import GatewayConfigError, PackageIndexGateway, SupplyGrant


def _file_bytes(name: str) -> bytes:
    return b"FILE:" + name.encode()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _minimal_wheel(dist: str, version: str) -> bytes:
    """pip 能装的最小 wheel（一个空包 + dist-info 三件套）。"""

    buf = io.BytesIO()
    info = f"{dist}-{version}.dist-info"
    files = {
        f"{dist}/__init__.py": b"",
        f"{info}/METADATA": f"Metadata-Version: 2.1\nName: {dist}\nVersion: {version}\n".encode(),
        f"{info}/WHEEL": b"Wheel-Version: 1.0\nGenerator: rh2-test\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
    }
    record = "".join(f"{path},,\n" for path in files) + f"{info}/RECORD,,\n"
    with zipfile.ZipFile(buf, "w") as zf:
        for path, data in files.items():
            zf.writestr(path, data)
        zf.writestr(f"{info}/RECORD", record)
    return buf.getvalue()


DEMO_WHEEL = _minimal_wheel("rh2demo", "1.0")
DEMO_WHEEL_NAME = "rh2demo-1.0-py3-none-any.whl"

REQUESTS_PAGE = """<!DOCTYPE html><html><body>
<a href="../../packages/requests-2.31.0-py3-none-any.whl#sha256=aaaa" data-requires-python="&gt;=3.7" data-core-metadata="sha256=bbbb">requests-2.31.0-py3-none-any.whl</a><br/>
<a href="../../packages/requests-2.31.0.tar.gz#sha256=cccc" data-requires-python="&gt;=3.7">requests-2.31.0.tar.gz</a><br/>
<a href="../../packages/requests-2.0.0.tar.gz#sha256=dddd" data-yanked="broken release">requests-2.0.0.tar.gz</a><br/>
<a href="../../packages/requests-2.31.0%2Blocal-py3-none-any.whl#sha256=0101">requests-2.31.0+local-py3-none-any.whl</a><br/>
<a href="https://evil.example/requests-9.9.9-py3-none-any.whl#sha256=eeee">requests-9.9.9-py3-none-any.whl</a><br/>
<a href="../../packages/other-1.0-py3-none-any.whl#sha256=ffff">other-1.0-py3-none-any.whl</a><br/>
<a href="../../packages/requests-2.31.0.exe">requests-2.31.0.exe</a><br/>
</body></html>"""

MOTO_PAGE = """<!DOCTYPE html><html><body>
<a href="/packages/moto-4.2.0-py3-none-any.whl#sha256=4242">moto-4.2.0-py3-none-any.whl</a>
<a href="/packages/moto-4.2.0.tar.gz#sha256=4243">moto-4.2.0.tar.gz</a>
<a href="/packages/moto-5.0.0-py3-none-any.whl#sha256=5000">moto-5.0.0-py3-none-any.whl</a>
</body></html>"""


class FakeUpstream:
    """假 PEP 503 上游（扮演 devpi `root/pypi`）：记录收到的请求（方法 / 路径 / query / 头）。"""

    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.port = 0
        self._runner: web.AppRunner | None = None
        # NG1 夹具：/pause 先发 5 字节再等 resume；/stall 在发响应头之前等 headers_go
        self.pause_started = asyncio.Event()
        self.resume = asyncio.Event()
        self.headers_waiting = asyncio.Event()
        self.headers_go = asyncio.Event()

    def _record(self, request: web.Request) -> None:
        self.requests.append({"method": request.method, "path": request.path, "query": request.query_string,
                              "headers": {k.lower(): v for k, v in request.headers.items()}})

    async def _simple(self, request: web.Request) -> web.StreamResponse:
        self._record(request)
        dist = request.match_info["dist"]
        pages = {
            "requests": REQUESTS_PAGE,
            "moto": MOTO_PAGE,
            "rh2demo": f'<a href="/packages/{DEMO_WHEEL_NAME}#sha256={_sha(DEMO_WHEEL)}">{DEMO_WHEEL_NAME}</a>',
            "rh2blocked": '<a href="/packages/rh2blocked-1.0-py3-none-any.whl">rh2blocked-1.0-py3-none-any.whl</a>',
            "big": '<a href="/slow/big-1.0-py3-none-any.whl">big-1.0-py3-none-any.whl</a>',
            "pausepkg": '<a href="/pause/pausepkg-1.0-py3-none-any.whl">pausepkg-1.0-py3-none-any.whl</a>',
            "stallpkg": '<a href="/stall/stallpkg-1.0-py3-none-any.whl">stallpkg-1.0-py3-none-any.whl</a>',
        }
        if dist == "boom":
            return web.Response(status=500, text="boom")
        if dist == "notes":
            return web.Response(text="plain text", content_type="text/plain")
        if dist not in pages:
            return web.Response(status=404, text="not found")
        return web.Response(text=pages[dist], content_type="text/html")

    async def _package(self, request: web.Request) -> web.Response:
        self._record(request)
        name = request.match_info["name"]
        if name == DEMO_WHEEL_NAME:
            return web.Response(body=DEMO_WHEEL, content_type="application/octet-stream")
        if name.endswith(".metadata"):
            return web.Response(text="Metadata-Version: 2.1\nName: requests\nVersion: 2.31.0\n")
        return web.Response(body=_file_bytes(name), content_type="application/octet-stream")

    async def _slow(self, request: web.Request) -> web.StreamResponse:
        self._record(request)
        out = web.StreamResponse()  # 不带 Content-Length：分块传输
        await out.prepare(request)
        for _ in range(64):
            await out.write(b"x" * 65536)
            await asyncio.sleep(0.02)
        await out.write_eof()
        return out

    async def _pause(self, request: web.Request) -> web.StreamResponse:
        self._record(request)
        out = web.StreamResponse()
        out.content_length = 10
        await out.prepare(request)
        await out.write(b"12345")
        self.pause_started.set()
        await self.resume.wait()
        await out.write(b"67890")
        await out.write_eof()
        return out

    async def _stall(self, request: web.Request) -> web.Response:
        self._record(request)
        self.headers_waiting.set()
        await self.headers_go.wait()
        return web.Response(body=b"stalled-ok", content_type="application/octet-stream")

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/simple/{dist}/", self._simple)
        app.router.add_get("/packages/{name}", self._package)
        app.router.add_get("/slow/{name}", self._slow)
        app.router.add_get("/pause/{name}", self._pause)
        app.router.add_get("/stall/{name}", self._stall)
        self._runner = web.AppRunner(app, access_log=None)
        await self._runner.setup()
        await web.TCPSite(self._runner, "127.0.0.1", 0).start()
        self.port = int(self._runner.addresses[0][1])

    async def stop(self) -> None:
        self.resume.set()
        self.headers_go.set()
        if self._runner is not None:
            await self._runner.cleanup()

    def saw(self, path_prefix: str) -> list[dict]:
        return [r for r in self.requests if r["path"].startswith(path_prefix)]


@pytest.fixture
async def upstream():
    up = FakeUpstream()
    await up.start()
    yield up
    await up.stop()


@pytest.fixture
async def gateway(upstream, tmp_path):
    g = PackageIndexGateway(upstream_simple_url=f"http://127.0.0.1:{upstream.port}/simple/", log_path=tmp_path / "gw.jsonl")
    port = await g.start("127.0.0.1", 0)
    g.test_base = f"http://127.0.0.1:{port}"  # type: ignore[attr-defined]
    yield g
    await g.stop()


def _grant(**kw) -> SupplyGrant:
    base = {"attempt_id": "att-1", "task_id": "task-1", "plane": "rollout", "phase": "rollout", "blocked_dists": ["Moto"]}
    base.update(kw)
    return SupplyGrant.build(**base)


def _anchors(page: str) -> list[tuple[dict, str]]:
    parser = gw._AnchorParser()
    parser.feed(page)
    return parser.anchors


def _log_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


async def _get(session, url, **kw):
    async with session.get(url, **kw) as resp:
        return resp.status, await resp.read(), resp.headers


# ---- 纯函数 ---------------------------------------------------------------------------------------------------------


def test_filename_project_version_follows_pip_name_rules():
    f = gw.filename_project_version
    assert f("requests-2.31.0-py3-none-any.whl", "requests") == "2.31.0"
    assert f("zope.interface-5.4.0.tar.gz", "zope-interface") == "5.4.0"
    assert f("python-dateutil-2.8.2.tar.gz", "python-dateutil") == "2.8.2"
    assert f("scikit_learn-1.2.0-cp312-cp312-macosx_11_0_arm64.whl", "scikit-learn") == "1.2.0"
    assert f("other-1.0-py3-none-any.whl", "requests") is None  # 项目名不符
    assert f("requests-2.31.0.egg", "requests") is None and not gw.is_distribution_filename("requests-2.31.0.exe")
    assert f("requests-.tar.gz", "requests") is None


def test_grant_validation_and_policy_digest():
    grant = _grant(blocked_dists=["Moto", "moto_ext"], allowed_releases={"MOTO": ["4.2.0"]})
    assert grant.blocked_dists == frozenset({"moto", "moto-ext"}) and grant.allowed_releases == {"moto": frozenset({"4.2"})}
    assert grant.policy_digest() == _grant(blocked_dists=["moto-ext", "moto"], allowed_releases={"moto": ["4.2"]}).policy_digest()
    with pytest.raises(GatewayConfigError, match="例外只针对封禁表"):
        _grant(allowed_releases={"requests": ["2.31.0"]})
    with pytest.raises(GatewayConfigError, match="例外版本表为空"):
        _grant(allowed_releases={"moto": []})
    with pytest.raises(GatewayConfigError, match="plane"):
        _grant(plane="elsewhere")
    with pytest.raises(GatewayConfigError, match="attempt_id"):
        _grant(attempt_id="")
    with pytest.raises(GatewayConfigError, match="dist 名不合法"):
        _grant(blocked_dists=["bad name!"])
    with pytest.raises(GatewayConfigError, match="upstream_simple_url"):
        PackageIndexGateway(upstream_simple_url="ftp://x/simple/")


# ---- 页面与文件 ---------------------------------------------------------------------------------------------------------


async def test_page_is_regenerated_with_gateway_links_and_only_this_projects_files(gateway, upstream):
    token = gateway.issue(_grant())
    async with aiohttp.ClientSession() as s:
        status, body, headers = await _get(s, f"{gateway.test_base}/a/{token}/simple/requests/")
    assert status == 200 and headers["Content-Type"].startswith("text/html")
    anchors = _anchors(body.decode())
    names = [text for _attrs, text in anchors]
    assert names == ["requests-2.31.0-py3-none-any.whl", "requests-2.31.0.tar.gz", "requests-2.0.0.tar.gz",
                     "requests-2.31.0+local-py3-none-any.whl"]
    by_name = {text: attrs for attrs, text in anchors}
    whl = by_name["requests-2.31.0-py3-none-any.whl"]
    assert whl["href"].startswith(f"/a/{token}/files/") and whl["href"].endswith("/requests-2.31.0-py3-none-any.whl#sha256=aaaa")
    assert whl["data-requires-python"] == ">=3.7" and whl["data-core-metadata"] == "sha256=bbbb"
    assert "data-core-metadata" not in by_name["requests-2.31.0.tar.gz"]
    assert by_name["requests-2.0.0.tar.gz"]["data-yanked"] == "broken release"
    assert "%2B" in by_name["requests-2.31.0+local-py3-none-any.whl"]["href"]
    assert b"evil.example" not in body and b"../../packages" not in body  # 上游标记不透传
    [seen] = upstream.saw("/simple/requests/")
    assert seen["headers"]["accept"] == "text/html" and seen["query"] == ""
    [row] = [r for r in _log_rows(gateway._log_path) if r["kind"] == "simple"]
    assert row["decision"] == "served_page" and row["files_listed"] == 4
    assert row["files_dropped"] == {"foreign_origin": 1, "not_this_project": 1, "not_a_distribution": 1}


async def test_files_are_served_only_through_ids_issued_to_this_token(gateway, upstream):
    token = gateway.issue(_grant())
    other = gateway.issue(_grant(attempt_id="att-2"))
    async with aiohttp.ClientSession() as s:
        _st, body, _h = await _get(s, f"{gateway.test_base}/a/{token}/simple/requests/")
        by_name = {text: attrs["href"].split("#")[0] for attrs, text in _anchors(body.decode())}
        whl = by_name["requests-2.31.0-py3-none-any.whl"]
        status, data, headers = await _get(s, gateway.test_base + whl)
        assert status == 200 and data == _file_bytes("requests-2.31.0-py3-none-any.whl")
        assert headers["Content-Length"] == str(len(data))
        status, data, _h = await _get(s, gateway.test_base + whl + ".metadata")  # PEP 658：上游声明了才给
        assert status == 200 and data.startswith(b"Metadata-Version")
        sdist = by_name["requests-2.31.0.tar.gz"]
        assert (await _get(s, gateway.test_base + sdist + ".metadata"))[0] == 404  # 没声明元数据
        plus = by_name["requests-2.31.0+local-py3-none-any.whl"]
        status, data, _h = await _get(s, gateway.test_base + plus)
        assert status == 200 and data == _file_bytes("requests-2.31.0+local-py3-none-any.whl")
        fid = whl.split("/")[4]
        assert (await _get(s, f"{gateway.test_base}/a/{token}/files/{fid}/requests-2.0.0.tar.gz"))[0] == 404  # fid 与文件名不符
        assert (await _get(s, f"{gateway.test_base}/a/{other}/files/{fid}/requests-2.31.0-py3-none-any.whl"))[0] == 404  # fid 不跨 token
        assert (await _get(s, f"{gateway.test_base}/a/{token}/files/AAAAAAAAAAAAAAAAAAAA/requests-2.31.0.tar.gz"))[0] == 404
        # 重复取页不重新签发：同一上游文件复用 fid
        _st, body2, _h = await _get(s, f"{gateway.test_base}/a/{token}/simple/requests/")
        assert {text: attrs["href"].split("#")[0] for attrs, text in _anchors(body2.decode())} == by_name
    decisions = [r["decision"] for r in _log_rows(gateway._log_path) if r["kind"] in ("file", "metadata")]
    assert decisions.count("file_not_issued") == 2 and decisions.count("file_name_mismatch") == 2


async def test_1a_blocks_the_project_page_and_its_files_under_every_spelling(gateway, upstream):
    token = gateway.issue(_grant())
    variants = ["moto/", "MoTo/", "mo%74o/", "moto", "MOTO/", "Moto./"]
    async with aiohttp.ClientSession() as s:
        for variant in variants:
            status, _body, _h = await _get(s, f"{gateway.test_base}/a/{token}/simple/{variant}")
            assert status == 404, variant
        # 已知上游文件 URL 直接访问：网关里没有这种路由；猜 fid 也没签发过
        assert (await _get(s, f"{gateway.test_base}/packages/moto-5.0.0-py3-none-any.whl"))[0] == 404
        assert (await _get(s, f"{gateway.test_base}/a/{token}/files/AAAAAAAAAAAAAAAAAAAA/moto-5.0.0-py3-none-any.whl"))[0] == 404
        raw = aiohttp.client.URL(f"{gateway.test_base}/a/{token}/files/../../packages/moto-5.0.0-py3-none-any.whl", encoded=True)
        assert (await _get(s, raw))[0] == 404
        assert (await _get(s, f"{gateway.test_base}/a/{token}/simple/"))[0] == 404  # 不给全量项目清单
    assert upstream.saw("/simple/moto") == [] and upstream.saw("/packages/moto") == []
    rows = [r for r in _log_rows(gateway._log_path) if r["kind"] == "simple"]
    assert [r["decision"] for r in rows].count("blocked_by_policy") == 5
    assert [r["decision"] for r in rows].count("bad_dist") == 1  # "Moto." 归一成 "moto-"：不是合法名，照样 404


async def test_release_exception_serves_only_the_listed_versions(gateway, upstream):
    token = gateway.issue(_grant(allowed_releases={"moto": ["4.2.0"]}))
    async with aiohttp.ClientSession() as s:
        status, body, _h = await _get(s, f"{gateway.test_base}/a/{token}/simple/moto/")
        anchors = _anchors(body.decode())
        assert status == 200 and [text for _a, text in anchors] == ["moto-4.2.0-py3-none-any.whl", "moto-4.2.0.tar.gz"]
        status, data, _h = await _get(s, gateway.test_base + anchors[0][0]["href"].split("#")[0])
        assert status == 200 and data == _file_bytes("moto-4.2.0-py3-none-any.whl")
    [row] = [r for r in _log_rows(gateway._log_path) if r["kind"] == "simple"]
    assert row["decision"] == "served_page_with_exceptions" and row["files_dropped"] == {"blocked_version": 1}
    assert upstream.saw("/packages/moto-5.0.0") == []


async def test_only_get_and_head_and_neither_queries_nor_client_headers_reach_upstream(gateway, upstream):
    token = gateway.issue(_grant())
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{gateway.test_base}/a/{token}/simple/requests/", data=b"x") as resp:
            assert resp.status == 405
        async with s.put(f"{gateway.test_base}/a/{token}/files/AAAAAAAAAAAAAAAAAAAA/x.whl", data=b"x") as resp:
            assert resp.status == 405
        status, _b, _h = await _get(s, f"{gateway.test_base}/a/{token}/simple/requests/?leak=secret-data",
                                    headers={"X-Exfil": "secret-data", "Authorization": "Bearer secret-data"})
        assert status == 200
        async with s.head(f"{gateway.test_base}/a/{token}/simple/requests/") as resp:
            assert resp.status == 200 and int(resp.headers["Content-Length"]) > 0 and await resp.read() == b""
    for seen in upstream.requests:
        assert seen["query"] == "" and "x-exfil" not in seen["headers"] and "authorization" not in seen["headers"]
    unrouted = [r for r in _log_rows(gateway._log_path) if r["kind"] == "unrouted"]
    assert {r["decision"] for r in unrouted} == {"method_not_allowed"} and all("<token>" in r["path_redacted"] for r in unrouted)


async def test_withdraw_denies_everything_and_cuts_an_in_flight_download(gateway):
    token = gateway.issue(_grant(plane="grading", phase="install"))
    async with aiohttp.ClientSession() as s:
        _st, body, _h = await _get(s, f"{gateway.test_base}/a/{token}/simple/big/")
        href = _anchors(body.decode())[0][0]["href"]
        async with s.get(gateway.test_base + href) as resp:
            assert resp.status == 200
            first = await resp.content.readany()
            assert first
            assert gateway.withdraw(token) is True and gateway.withdraw(token) is False
            with pytest.raises(aiohttp.ClientPayloadError):  # 分块传输被掐断：客户端报错，不会拿到"完整"的半截文件
                await resp.read()
        assert (await _get(s, f"{gateway.test_base}/a/{token}/simple/requests/"))[0] == 403
        assert (await _get(s, gateway.test_base + href))[0] == 403
    summary = await gateway.release(token)
    assert summary["withdrawn_before_release"] is True and summary["attempt_id"] == "att-1" and summary["plane"] == "grading"
    assert summary["complete"] is True and summary["inflight_unfinished"] == 0
    assert summary["stats"]["decision:withdrawn_in_flight"] == 1 and summary["stats"]["decision:token_withdrawn"] == 2
    assert gateway.active_token_count() == 0 and await gateway.release(token) is None
    async with aiohttp.ClientSession() as s:
        assert (await _get(s, f"{gateway.test_base}/a/{token}/simple/requests/"))[0] == 404  # 释放后不认识
    totals = gateway.summary()["totals"]
    assert totals["tokens_issued"] == 1 and totals["tokens_withdrawn"] == 1 and totals["tokens_released"] == 1


async def test_upstream_failures_are_typed_and_never_look_like_success(gateway, tmp_path):
    token = gateway.issue(_grant())
    async with aiohttp.ClientSession() as s:
        assert (await _get(s, f"{gateway.test_base}/a/{token}/simple/missing/"))[0] == 404
        assert (await _get(s, f"{gateway.test_base}/a/{token}/simple/boom/"))[0] == 502
        assert (await _get(s, f"{gateway.test_base}/a/{token}/simple/notes/"))[0] == 502
    decisions = [r["decision"] for r in _log_rows(gateway._log_path) if r["kind"] == "simple"]
    assert decisions == ["upstream_not_found", "upstream_error", "upstream_not_html"]
    dead = PackageIndexGateway(upstream_simple_url="http://127.0.0.1:9/simple/", log_path=tmp_path / "dead.jsonl")
    port = await dead.start("127.0.0.1", 0)
    try:
        tok = dead.issue(_grant())
        async with aiohttp.ClientSession() as s:
            assert (await _get(s, f"http://127.0.0.1:{port}/a/{tok}/simple/requests/"))[0] == 502
    finally:
        await dead.stop()
    assert _log_rows(tmp_path / "dead.jsonl")[0]["decision"] == "upstream_unreachable"


async def test_log_is_attributed_by_token_and_never_contains_the_token(gateway):
    token = gateway.issue(_grant(attempt_id="att-9", task_id="task-9"))
    async with aiohttp.ClientSession() as s:
        await _get(s, f"{gateway.test_base}/a/{token}/simple/requests/")
        await _get(s, f"{gateway.test_base}/a/{token}/simple/moto/")
        await _get(s, f"{gateway.test_base}/a/{'Z' * 32}/simple/requests/")  # 未知 token
    text = gateway._log_path.read_text()
    assert token not in text
    rows = _log_rows(gateway._log_path)
    known = [r for r in rows if r.get("attempt_id")]
    assert len(known) == 2 and {r["task_id"] for r in known} == {"task-9"} and {r["plane"] for r in known} == {"rollout"}
    assert len({r["token_ref"] for r in known}) == 1 and len(known[0]["token_ref"]) == 12
    [unknown] = [r for r in rows if r["decision"] == "unknown_token"]
    assert "attempt_id" not in unknown and unknown["status"] == 404


# ---- 真实客户端：pip ---------------------------------------------------------------------------------------------------


def _system_pip() -> str | None:
    python = shutil.which("python3")
    if python is None:
        return None
    probe = subprocess.run([python, "-m", "pip", "--version"], capture_output=True, text=True, timeout=60)
    return python if probe.returncode == 0 else None


SYSTEM_PIP_PYTHON = _system_pip()


@pytest.mark.skipif(SYSTEM_PIP_PYTHON is None, reason="本机没有带 pip 的 python3（真实客户端验收需要它）")
async def test_real_pip_downloads_through_the_gateway_and_is_refused_for_a_blocked_project(gateway, upstream, tmp_path):
    token = gateway.issue(_grant(blocked_dists=["rh2blocked"]))
    index = f"{gateway.test_base}{gateway.index_path(token)}"
    env = {**os.environ, "PIP_CONFIG_FILE": os.devnull, "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_INPUT": "1"}

    async def pip_download(project: str, dest: Path) -> tuple[int, str]:
        proc = await asyncio.create_subprocess_exec(
            SYSTEM_PIP_PYTHON, "-m", "pip", "download", "--no-deps", "--no-cache-dir", "--index-url", index,
            "--dest", str(dest), project, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
        return proc.returncode, out.decode(errors="replace")

    rc, out = await pip_download("rh2demo", tmp_path / "ok")
    assert rc == 0, out
    assert (tmp_path / "ok" / DEMO_WHEEL_NAME).read_bytes() == DEMO_WHEEL  # hash 由 pip 按 #sha256 片段核对过
    rc, out = await pip_download("rh2blocked", tmp_path / "blocked")
    assert rc != 0 and "No matching distribution found" in out, out
    assert upstream.saw("/simple/rh2blocked") == []
    assert token not in gateway._log_path.read_text()


# ---- NG1（Codex review_supply_components §1）：释放 = 撤销 + 有界收齐在途请求 + 终态摘要 -------------------------------------------

_DISCONNECTED = (aiohttp.ClientPayloadError, aiohttp.ServerDisconnectedError, aiohttp.ClientConnectionError)


async def _file_href(session, gateway, token: str, dist: str) -> str:
    _status, body, _h = await _get(session, f"{gateway.test_base}/a/{token}/simple/{dist}/")
    return _anchors(body.decode())[0][0]["href"].split("#")[0]


async def test_release_mid_download_cuts_it_and_the_final_summary_includes_its_bytes(gateway, upstream):
    token = gateway.issue(_grant())
    async with aiohttp.ClientSession() as s:
        href = await _file_href(s, gateway, token, "pausepkg")
        async with s.get(gateway.test_base + href) as resp:
            assert resp.status == 200 and await resp.content.readexactly(5) == b"12345"
            await asyncio.wait_for(upstream.pause_started.wait(), 5)
            summary = await gateway.release(token, timeout=5)
            upstream.resume.set()  # 上游恢复后，剩下的 5 字节也不会再经网关送达
            with pytest.raises(_DISCONNECTED):
                await asyncio.wait_for(resp.read(), 5)
    assert summary["complete"] is True and summary["inflight_unfinished"] == 0 and summary["withdrawn_before_release"] is False
    assert summary["stats"]["decision:withdrawn_in_flight"] == 1 and summary["stats"]["bytes"] == 5  # 终态统计已收齐
    row = [r for r in _log_rows(gateway._log_path) if r["kind"] == "file"][-1]
    assert row["decision"] == "withdrawn_in_flight" and row["bytes"] == 5 and row["response_started"] is True
    assert gateway.active_token_count() == 0 and gateway.summary()["totals"].get("tokens_released_incomplete") is None


async def test_withdraw_cuts_a_stalled_download_at_once_not_at_the_next_upstream_chunk(gateway, upstream):
    token = gateway.issue(_grant(plane="grading", phase="install"))
    async with aiohttp.ClientSession() as s:
        href = await _file_href(s, gateway, token, "pausepkg")
        async with s.get(gateway.test_base + href) as resp:
            await resp.content.readexactly(5)
            await asyncio.wait_for(upstream.pause_started.wait(), 5)
            started = time.monotonic()
            assert gateway.withdraw(token) is True
            with pytest.raises(_DISCONNECTED):
                await asyncio.wait_for(resp.read(), 5)
            assert time.monotonic() - started < 2.0  # 上游仍停顿（resume 未设置）：断开来自撤销本身
    summary = await gateway.release(token, timeout=5)
    assert summary["withdrawn_before_release"] is True and summary["complete"] is True
    assert summary["stats"]["decision:withdrawn_in_flight"] == 1 and summary["stats"]["bytes"] == 5


async def test_release_cancels_a_request_still_waiting_for_upstream_headers(gateway, upstream):
    """请求还在等上游响应头时释放：网关直接关连接、一个响应字节都不发。用裸 socket 观察服务端行为，不受客户端重试策略影响
    （aiohttp 客户端会把响应头之前的断开当成可重试，见下一条）。"""
    token = gateway.issue(_grant())
    async with aiohttp.ClientSession() as s:
        href = await _file_href(s, gateway, token, "stallpkg")
    host, port = gateway.test_base.removeprefix("http://").rsplit(":", 1)
    reader, writer = await asyncio.open_connection(host, int(port))
    try:
        writer.write(f"GET {href} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n".encode())
        await writer.drain()
        await asyncio.wait_for(upstream.headers_waiting.wait(), 5)
        summary = await gateway.release(token, timeout=5)
        try:
            got = await asyncio.wait_for(reader.read(), 5)  # 读到 EOF
        except ConnectionResetError:
            got = b""
        assert got == b""  # 连接被关、零响应字节（没有状态行）
    finally:
        writer.close()
    assert summary["complete"] is True and summary["stats"]["decision:withdrawn_in_flight"] == 1
    row = [r for r in _log_rows(gateway._log_path) if r["kind"] == "file"][-1]
    assert row["decision"] == "withdrawn_in_flight" and "response_started" not in row and not row.get("bytes")


async def test_a_client_retry_after_the_header_wait_cut_is_refused_and_never_reaches_upstream(gateway, upstream):
    """真实客户端对响应头之前的断开可能重试幂等 GET（aiohttp 3.14.1 重试一次，已核对其 client 源码）。重试落在已释放的
    token 上：网关直接 404（unknown_token），不转发上游；上游之后才放行的响应也送不到客户端。不重试的客户端则直接看到断开。"""
    token = gateway.issue(_grant())
    async with aiohttp.ClientSession() as s:
        href = await _file_href(s, gateway, token, "stallpkg")
        pending = asyncio.ensure_future(_get(s, gateway.test_base + href))
        await asyncio.wait_for(upstream.headers_waiting.wait(), 5)
        await gateway.release(token, timeout=5)
        upstream.headers_go.set()  # 上游这时才发响应：已被取消的在途请求不会再转交
        try:
            status, body, _h = await asyncio.wait_for(pending, 5)
        except _DISCONNECTED:
            status, body = None, b""
    assert status in (None, 404) and b"stalled-ok" not in body
    decisions = [r["decision"] for r in _log_rows(gateway._log_path) if r["kind"] == "file"]
    assert decisions == (["withdrawn_in_flight"] if status is None else ["withdrawn_in_flight", "unknown_token"])
    assert len(upstream.saw("/stall/")) == 1  # 只有被切断的那一次到过上游；重试没有转发


async def test_release_that_cannot_collect_an_inflight_request_says_so_instead_of_faking_a_final_summary(gateway):
    """有界等待到时仍有在途请求没收尾（这里用一个吞掉取消的任务模拟）：摘要标 `complete=False` 并给数量，网关总计记一次
    未收齐释放；token 照样释放（之后 404）。"""
    token = gateway.issue(_grant())
    release_gate = asyncio.Event()

    async def stubborn() -> None:
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            await release_gate.wait()  # 不按取消收尾

    task = asyncio.ensure_future(stubborn())
    await asyncio.sleep(0)
    gateway._tokens[token].inflight.add(task)
    summary = await gateway.release(token, timeout=0.2)
    assert summary["complete"] is False and summary["inflight_unfinished"] == 1
    assert gateway.summary()["totals"]["tokens_released_incomplete"] == 1 and gateway.active_token_count() == 0
    async with aiohttp.ClientSession() as s:
        status, _body, _h = await _get(s, f"{gateway.test_base}/a/{token}/simple/requests/")
    assert status == 404
    release_gate.set()
    await asyncio.wait_for(task, 5)


async def test_overlapping_releases_yield_one_final_summary_and_count_once(gateway, upstream):
    token = gateway.issue(_grant())
    async with aiohttp.ClientSession() as s:
        href = await _file_href(s, gateway, token, "pausepkg")
        async with s.get(gateway.test_base + href) as resp:
            await resp.content.readexactly(5)
            await asyncio.wait_for(upstream.pause_started.wait(), 5)
            first, second = await asyncio.gather(gateway.release(token, timeout=5), gateway.release(token, timeout=5))
    summaries = [x for x in (first, second) if x is not None]
    assert len(summaries) == 1 and summaries[0]["complete"] is True and summaries[0]["stats"]["bytes"] == 5
    assert gateway.summary()["totals"]["tokens_released"] == 1 and await gateway.release(token) is None


async def test_gateway_stop_cuts_inflight_requests_at_once_instead_of_waiting_for_the_upstream(gateway, upstream):
    """关停网关时仍有在途请求（上游还没发响应头）：立即断开并按 `cancelled_in_flight` 记日志，不等 aiohttp 默认最长
    60 s 的优雅关停。"""
    token = gateway.issue(_grant())
    async with aiohttp.ClientSession() as s:
        href = await _file_href(s, gateway, token, "stallpkg")
    host, port = gateway.test_base.removeprefix("http://").rsplit(":", 1)
    reader, writer = await asyncio.open_connection(host, int(port))
    try:
        writer.write(f"GET {href} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n".encode())
        await writer.drain()
        await asyncio.wait_for(upstream.headers_waiting.wait(), 5)
        started = time.monotonic()
        await asyncio.wait_for(gateway.stop(), 10)
        assert time.monotonic() - started < 5.0
        try:
            got = await asyncio.wait_for(reader.read(), 5)
        except ConnectionResetError:
            got = b""
        assert got == b""
    finally:
        writer.close()
    row = [r for r in _log_rows(gateway._log_path) if r["kind"] == "file"][-1]
    assert row["decision"] == "cancelled_in_flight" and "response_started" not in row


async def test_normal_complete_download_then_release_reports_complete_final_stats(gateway):
    token = gateway.issue(_grant())
    async with aiohttp.ClientSession() as s:
        _st, body, _h = await _get(s, f"{gateway.test_base}/a/{token}/simple/requests/")
        href = {text: attrs["href"].split("#")[0] for attrs, text in _anchors(body.decode())}["requests-2.31.0-py3-none-any.whl"]
        status, data, _h = await _get(s, gateway.test_base + href)
        assert status == 200 and data == _file_bytes("requests-2.31.0-py3-none-any.whl")
    summary = await gateway.release(token)
    assert summary["complete"] is True and summary["withdrawn_before_release"] is False
    assert summary["stats"]["decision:served_page"] == 1 and summary["stats"]["decision:served_file"] == 1
    assert summary["stats"]["bytes"] == len(data)

