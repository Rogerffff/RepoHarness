"""第六组 受控依赖供应（1A + 2A；Brief `network_supply_brief_20260924.md` §2–§5）：RH2 包索引网关。

宿主侧、run 级的 aiohttp 服务，挡在 devpi（`root/pypi` 镜像缓存）或任何 PEP 503 上游前面。容器经 relay 只能到它：

- **路径只有两种**：`/a/<token>/simple/<dist>/` 与 `/a/<token>/files/<fid>/<filename>[.metadata]`。`<token>` 由宿主为每个
  attempt / 每次评分签发（`issue`），绑定 attempt / task / 平面 / 阶段与 1A 封禁表——日志按 token 归 attempt，不信任候选自报
  身份；候选不知道别的 attempt 的 token，也就冒用不了。
- **1A**：封禁表里的 dist（PEP 503 归一名）页面与文件都 404；例外表只放行列出的版本（逐题单列的固定发行包）。第三方包不按
  题目日期截断。
- **文件只能走本 token 签发过的 fid**：fid 只出现在网关自己生成的简单页里，所以已知上游文件 URL 直接访问、换 dist 名、`..`、
  百分号编码、大小写都绕不过封禁；fid 不跨 token。页面里项目名与所请求 dist 不符的文件（pip 本来也会跳过）一律不签发。
- **只接受 GET / HEAD**；丢弃 query string 与候选的请求头；上游页面解析后**重新生成**最小 PEP 503 HTML（只保留 href、hash、
  requires-python、yanked、PEP 658 元数据标记），不透传上游标记。这是缩小出站信息通道，不是"没有出站信息"的承诺（Brief §4.3）。
- **撤销与释放**：token 已接纳的每个请求都登记为它的在途请求（唯一 owner = 该 token）。`withdraw` 之后新请求一律 403，并
  **立即取消**在途请求——正在流式下载的、上游停顿的、还在等上游响应头的都会断开（客户端报错，不会拿到"完整"的半截文件）；
  `release` = 撤销 + 有界等待在途请求收尾（它们各自记下实际进度的日志行）+ 给出终态摘要 + 释放签发表（之后 404）。摘要里
  `complete` 说明在途请求是否都已收齐——没收齐（超时）就明说，不把快照冒充终态。撤销与释放都必须在网关所在的事件循环里
  调用。网关关停（`stop`）同样先取消全部在途请求（记 `cancelled_in_flight`），不等 aiohttp 的优雅关停。纵深之外真正的
  隔离仍是 grader 断网（宿主 disconnect + inspect），不由 token 状态代替。
- **日志**：逐请求一行 JSONL（`log_path`），字段是 attempt / task / 平面 / 阶段 / dist / 文件名 / 判定 / 上游状态 / 字节 / 耗时；
  **不写 token 本身**（只写 `token_ref` = token 的 sha256 前 12 位，区分同一 attempt 的多次签发）。GET 日志只证明取过什么，
  不证明装进了哪个解释器（Brief §5.3 / Codex 方向复核 §5.3）。

不做：上传 / 管理接口、日期过滤、JSON 简单页（PEP 691；网关总是向上游要 HTML、给客户端 HTML，pip / uv 都接受）、跨 attempt
缓存（缓存是 devpi 的事）。缓存不是冻结：逐 attempt 的实际版本由安装后观测记录（Brief §3、§5）。
"""

from __future__ import annotations

import asyncio
import hashlib
import html
import json
import re
import secrets
import time
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit

from aiohttp import ClientError, ClientSession, ClientTimeout, TCPConnector, web

GATEWAY_SCHEMA_ID = "rh2.pkg_index_gateway.v1"
REQUEST_LOG_SCHEMA_ID = "rh2.pkg_index_gateway.request.v1"
PLANES: tuple[str, ...] = ("rollout", "grading")
TOKEN_ACTIVE = "active"
TOKEN_WITHDRAWN = "withdrawn"

_DIST_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{24,64}$")
_FID_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
_HASH_RE = re.compile(r"^(md5|sha1|sha224|sha256|sha384|sha512)=[0-9a-fA-F]+$")
_METADATA_RE = re.compile(r"^(true|(md5|sha1|sha224|sha256|sha384|sha512)=[0-9a-fA-F]+)$")
_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+!~-]*$")  # 不含 '/'、空白、引号、'%'
# pip 能直接使用的分发格式（egg / exe / msi 等 pip 本来就不用，一律不签发）
SDIST_EXTENSIONS: tuple[str, ...] = (".tar.gz", ".tgz", ".zip", ".tar.bz2", ".tbz", ".tar.xz", ".txz", ".tar")
_CHUNK = 64 * 1024
# 关停时 aiohttp 对仍未结束的请求的等待上限（默认 60 s）。在途请求在 on_shutdown 里已被取消，这里只兜底取消后仍不收尾的
_SHUTDOWN_GRACE_SECONDS = 5.0
# 本请求已被某个路由处理器记过日志（未路由的 404/405 由中间件补记）；aiohttp 新版推荐 RequestKey，旧版退回字符串键
_LOGGED_KEY: Any = web.RequestKey("rh2_logged", bool) if hasattr(web, "RequestKey") else "rh2_logged"
# 本请求登记在哪个 token 的在途集合里：(token 状态, 日志条目, 请求任务)；中间件据此收尾
_TRACK_KEY: Any = web.RequestKey("rh2_tracked", tuple) if hasattr(web, "RequestKey") else "rh2_tracked"


class GatewayConfigError(ValueError):
    """签发参数或网关配置不合法（调用方的接线错误，不是候选行为）。"""


def normalize_dist(name: str) -> str:
    """PEP 503 归一名。"""

    return re.sub(r"[-_.]+", "-", str(name)).lower()


def canonical_version(version: str) -> str:
    """版本比较用的规范形（`packaging` 在场时按 PEP 440 规范化，否则去空白小写）。"""

    text = str(version).strip()
    try:
        from packaging.utils import canonicalize_version
    except ImportError:  # pragma: no cover - rh2 环境里 packaging 在场
        return text.lower()
    try:
        return str(canonicalize_version(text))
    except Exception:  # noqa: BLE001 - 非 PEP 440 版本按原文比较
        return text.lower()


def is_distribution_filename(filename: str) -> bool:
    return filename.endswith(".whl") or any(filename.endswith(ext) for ext in SDIST_EXTENSIONS)


def filename_project_version(filename: str, dist: str) -> str | None:
    """文件名 → 版本；文件名里的项目名归一后必须等于 `dist`，否则（或不是 pip 能用的分发格式）返回 None。

    wheel：`{name}-{ver}(-{build})?-{py}-{abi}-{plat}.whl`；sdist：与 pip 相同的做法——从左到右试每个 '-'，前缀归一后等于
    项目名即分出版本（`python-dateutil-2.8.2.tar.gz` → `2.8.2`）。"""

    if filename.endswith(".whl"):
        parts = filename[: -len(".whl")].split("-")
        if len(parts) not in (5, 6) or not parts[1]:
            return None
        return parts[1] if normalize_dist(parts[0]) == dist else None
    for ext in SDIST_EXTENSIONS:
        if filename.endswith(ext):
            stem = filename[: -len(ext)]
            break
    else:
        return None
    for index, char in enumerate(stem):
        if char == "-" and stem[index + 1 :] and normalize_dist(stem[:index]) == dist:
            return stem[index + 1 :]
    return None


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}"


# ---------------------------------------------------------------------------
# 签发
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SupplyGrant:
    """宿主签发给一次 attempt / 一次评分的包供应授权（token 绑定的全部政策事实）。用 `SupplyGrant.build` 构造。"""

    attempt_id: str
    task_id: str
    plane: str  # rollout | grading
    phase: str  # 例如 rollout / install
    blocked_dists: frozenset[str] = frozenset()
    # 归一 dist → 放行版本（canonical_version）；只允许出现在 blocked_dists 里（例外只针对被测项目自身的发行包）
    allowed_releases: Mapping[str, frozenset[str]] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        attempt_id: str,
        task_id: str,
        plane: str,
        phase: str,
        blocked_dists: Iterable[str] = (),
        allowed_releases: Mapping[str, Iterable[str]] | None = None,
    ) -> SupplyGrant:
        for label, value in (("attempt_id", attempt_id), ("task_id", task_id), ("phase", phase)):
            if not isinstance(value, str) or not value.strip():
                raise GatewayConfigError(f"{label} 必须是非空字符串：{value!r}")
        if plane not in PLANES:
            raise GatewayConfigError(f"plane={plane!r} 不在 {PLANES}")
        blocked: set[str] = set()
        for name in blocked_dists:
            norm = normalize_dist(name)
            if not _DIST_RE.match(norm):
                raise GatewayConfigError(f"封禁表里的 dist 名不合法：{name!r}")
            blocked.add(norm)
        allowed: dict[str, frozenset[str]] = {}
        for name, versions in (allowed_releases or {}).items():
            norm = normalize_dist(name)
            if norm not in blocked:
                raise GatewayConfigError(f"例外只针对封禁表里的 dist（1A）：{name!r} 不在封禁表 {sorted(blocked)}")
            canon = frozenset(canonical_version(v) for v in versions if str(v).strip())
            if not canon:
                raise GatewayConfigError(f"{name!r} 的例外版本表为空")
            allowed[norm] = canon
        return cls(
            attempt_id=attempt_id, task_id=task_id, plane=plane, phase=phase,
            blocked_dists=frozenset(blocked), allowed_releases=allowed,
        )

    def policy_digest(self) -> str:
        """封禁表 + 例外表的摘要（进 run evidence；不含身份字段）。"""

        payload = {
            "blocked_dists": sorted(self.blocked_dists),
            "allowed_releases": {k: sorted(v) for k, v in sorted(self.allowed_releases.items())},
        }
        return "sha256:" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class _IssuedFile:
    url: str  # 上游文件 URL（无 query / fragment）
    filename: str
    dist: str
    metadata: bool  # 上游页面声明了 PEP 658 元数据（才允许取 `<file>.metadata`）


@dataclass
class _TokenState:
    grant: SupplyGrant
    token_ref: str
    issued_at: float
    state: str = TOKEN_ACTIVE
    issued: dict[str, _IssuedFile] = field(default_factory=dict)
    fid_by_url: dict[str, str] = field(default_factory=dict)  # 同一 token 内同一上游文件复用 fid（重复取页不增长）
    stats: Counter = field(default_factory=Counter)
    inflight: set = field(default_factory=set)  # 本 token 已接纳、尚未结束的请求任务（撤销时取消，释放时收齐）
    releasing: bool = False  # 已有一次 release 在收尾：重叠的 release 不再出摘要、不重复计数


@dataclass(frozen=True)
class _Anchor:
    fid: str
    filename: str
    hash: str | None
    requires_python: str | None
    core_metadata: str | None
    yanked: str | None


class _AnchorParser(HTMLParser):
    """PEP 503 简单页里的 `<a>`：属性（实体已解码）+ 文本。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list[tuple[dict[str, str | None], str]] = []
        self._current: tuple[dict[str, str | None], list[str]] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._current = (dict(attrs), [])

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._current[1].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current is not None:
            attrs, text = self._current
            self.anchors.append((attrs, "".join(text)))
            self._current = None


def _render_page(dist: str, token: str, anchors: list[_Anchor]) -> bytes:
    lines = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        '<meta name="pypi:repository-version" content="1.0">',
        f"<title>Links for {html.escape(dist)}</title>",
        "</head>",
        "<body>",
        f"<h1>Links for {html.escape(dist)}</h1>",
    ]
    for anchor in anchors:
        href = f"/a/{token}/files/{anchor.fid}/{quote(anchor.filename)}"
        if anchor.hash:
            href += f"#{anchor.hash}"
        attrs = [f'href="{html.escape(href, quote=True)}"']
        if anchor.requires_python is not None:
            attrs.append(f'data-requires-python="{html.escape(anchor.requires_python, quote=True)}"')
        if anchor.core_metadata is not None:
            attrs.append(f'data-core-metadata="{anchor.core_metadata}"')
            attrs.append(f'data-dist-info-metadata="{anchor.core_metadata}"')  # 旧名，pip 旧版本读它
        if anchor.yanked is not None:
            attrs.append(f'data-yanked="{html.escape(anchor.yanked, quote=True)}"')
        lines.append(f"<a {' '.join(attrs)}>{html.escape(anchor.filename)}</a><br/>")
    lines += ["</body>", "</html>", ""]
    return "\n".join(lines).encode("utf-8")


# ---------------------------------------------------------------------------
# 网关
# ---------------------------------------------------------------------------


class PackageIndexGateway:
    """见模块说明。一个 run 一个实例；`issue` / `withdraw` / `release` 是宿主侧的唯一控制面（同一进程内调用）。"""

    def __init__(
        self,
        *,
        upstream_simple_url: str,
        file_origins: Iterable[str] = (),
        log_path: Path | str | None = None,
        page_timeout_seconds: float = 60.0,
        file_sock_read_timeout_seconds: float = 120.0,
        max_page_bytes: int = 64 * 1024 * 1024,
    ) -> None:
        base = upstream_simple_url if upstream_simple_url.endswith("/") else upstream_simple_url + "/"
        parts = urlsplit(base)
        if parts.scheme not in ("http", "https") or not parts.netloc or parts.query or parts.fragment:
            raise GatewayConfigError(f"upstream_simple_url 必须是不带 query / fragment 的 http(s) URL：{upstream_simple_url!r}")
        origins = {_origin(base)}
        for origin in file_origins:
            op = urlsplit(origin)
            if op.scheme not in ("http", "https") or not op.netloc:
                raise GatewayConfigError(f"file_origins 里的来源不合法：{origin!r}")
            origins.add(_origin(origin))
        self.upstream_simple_url = base
        self.file_origins = frozenset(origins)
        self.page_timeout = ClientTimeout(total=page_timeout_seconds)
        self.file_timeout = ClientTimeout(total=None, sock_connect=30.0, sock_read=file_sock_read_timeout_seconds)
        self.max_page_bytes = int(max_page_bytes)
        self._log_path = Path(log_path) if log_path is not None else None
        self._log_fh = None
        self._tokens: dict[str, _TokenState] = {}
        self._totals: Counter = Counter()
        self._session: ClientSession | None = None
        self._runner: web.AppRunner | None = None

    # ---- 宿主控制面 ---------------------------------------------------------------------------------------------------

    def issue(self, grant: SupplyGrant) -> str:
        if not isinstance(grant, SupplyGrant):
            raise GatewayConfigError("issue 需要 SupplyGrant（用 SupplyGrant.build 构造）")
        token = secrets.token_urlsafe(24)
        while token in self._tokens:  # pragma: no cover - 192 位随机数
            token = secrets.token_urlsafe(24)
        ref = hashlib.sha256(token.encode()).hexdigest()[:12]
        self._tokens[token] = _TokenState(grant=grant, token_ref=ref, issued_at=time.time())
        self._totals["tokens_issued"] += 1
        return token

    def withdraw(self, token: str) -> bool:
        """撤销：之后新请求 403，并立即取消本 token 的在途请求（上游停顿、等响应头的也断开）。不等它们收尾（收尾由
        `release` 负责）。返回是否从 active 变为 withdrawn。必须在网关所在的事件循环里调用。"""

        state = self._tokens.get(token)
        if state is None or state.state != TOKEN_ACTIVE:
            return False
        state.state = TOKEN_WITHDRAWN
        self._totals["tokens_withdrawn"] += 1
        current = asyncio.current_task()
        for task in list(state.inflight):
            if task is not current and not task.done():
                task.cancel()
        return True

    async def release(self, token: str, *, timeout: float = 10.0) -> dict[str, Any] | None:
        """结束本 token：撤销（停新请求 + 取消在途）→ 有界等在途请求收尾（各自按实际进度记一行日志、计入统计）→
        释放签发表（之后 404）→ 返回终态摘要（调用方写进 attempt / 评分事实）。`complete=False` 表示超时仍有在途请求
        没收齐，摘要不是终态（`inflight_unfinished` 给数量），调用方如实记录。未知 token，或同一 token 已有一次
        release 在进行（重叠调用，例如取消清理与正常结束各调一次）→ None：终态摘要只出一份。

        AR2（Codex review_a_remainder_20260928）：调用方在等在途请求收尾时被取消（或等待本身出错），签发表照样移除这枚
        token（在途请求已由撤销取消），网关总计记一次被打断的释放，异常照常上抛——调用方拿不到摘要，但不会留下
        "正在释放"却永远不移除、之后每次 release 都返回 None 的 token。"""

        state = self._tokens.get(token)
        if state is None or state.releasing:
            return None
        state.releasing = True
        withdrawn_before = state.state != TOKEN_ACTIVE
        self.withdraw(token)
        current = asyncio.current_task()
        pending = {t for t in state.inflight if t is not current and not t.done()}
        unfinished = 0
        interrupted = False
        try:
            if pending:
                _done, still = await asyncio.wait(pending, timeout=timeout)
                unfinished = len(still)
        except BaseException:
            interrupted = True
            unfinished = sum(1 for t in pending if not t.done())
            raise
        finally:
            self._tokens.pop(token, None)
            self._totals["tokens_released"] += 1
            if unfinished or interrupted:
                self._totals["tokens_released_incomplete"] += 1
            if interrupted:
                self._totals["tokens_release_interrupted"] += 1
        return {
            "token_ref": state.token_ref,
            "attempt_id": state.grant.attempt_id,
            "task_id": state.grant.task_id,
            "plane": state.grant.plane,
            "phase": state.grant.phase,
            "policy_digest": state.grant.policy_digest(),
            "withdrawn_before_release": withdrawn_before,
            "complete": unfinished == 0,
            "inflight_unfinished": unfinished,
            "files_issued": len(state.issued),
            "stats": dict(state.stats),
        }

    def is_issued(self, token: str) -> bool:
        """签发表里是否还有这枚 token（撤销但未释放的也算）。调用方据此判断释放是否已真正生效。"""

        return token in self._tokens

    def active_token_count(self) -> int:
        return len(self._tokens)

    @staticmethod
    def index_path(token: str) -> str:
        return f"/a/{token}/simple/"

    def summary(self) -> dict[str, Any]:
        """run evidence 用：上游、文件来源与累计计数（不含任何 token）。"""

        return {
            "schema_id": GATEWAY_SCHEMA_ID,
            "upstream_simple_url": self.upstream_simple_url,
            "file_origins": sorted(self.file_origins),
            "active_tokens": len(self._tokens),
            "totals": dict(self._totals),
        }

    # ---- 服务生命周期 -------------------------------------------------------------------------------------------------

    def build_app(self) -> web.Application:
        app = web.Application(middlewares=[self._unrouted_middleware])
        app.router.add_get("/healthz", self._healthz)
        app.router.add_get("/a/{token}/simple/", self._simple_root)
        app.router.add_get("/a/{token}/simple/{dist}/", self._simple)
        app.router.add_get("/a/{token}/simple/{dist}", self._simple)
        app.router.add_get("/a/{token}/files/{fid}/{filename}", self._file)
        app.on_startup.append(self._on_startup)
        app.on_shutdown.append(self._on_shutdown)
        app.on_cleanup.append(self._on_cleanup)
        return app

    async def start(self, host: str, port: int) -> int:
        """起服务；返回实际监听端口（port=0 时由系统分配）。"""

        if self._runner is not None:
            raise GatewayConfigError("网关已经在运行")
        self._runner = web.AppRunner(self.build_app(), access_log=None, shutdown_timeout=_SHUTDOWN_GRACE_SECONDS)
        await self._runner.setup()
        site = web.TCPSite(self._runner, host, port)
        await site.start()
        return int(self._runner.addresses[0][1])

    async def stop(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
        if self._log_fh is not None:
            self._log_fh.close()
            self._log_fh = None

    async def _on_startup(self, _app: web.Application) -> None:
        self._session = ClientSession(connector=TCPConnector(limit=64), auto_decompress=True)
        if self._log_path is not None and self._log_fh is None:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            self._log_fh = self._log_path.open("a", encoding="utf-8")

    async def _on_shutdown(self, _app: web.Application) -> None:
        # 关停 = 所有 token 的服务结束：监听已停、已到达的请求已开始处理之后，取消全部在途请求（各自按
        # `cancelled_in_flight` 记日志），不让上游停顿的请求把关停拖到 aiohttp 的优雅等待上限，也不让下载在关停后继续。
        for state in self._tokens.values():
            for task in list(state.inflight):
                if not task.done():
                    task.cancel()

    async def _on_cleanup(self, _app: web.Application) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    # ---- 日志 ------------------------------------------------------------------------------------------------------

    def _entry(self, request: web.Request, kind: str) -> dict[str, Any]:
        request[_LOGGED_KEY] = True
        return {"kind": kind, "method": request.method, "started": time.monotonic()}

    def _write_log(self, entry: dict[str, Any], state: _TokenState | None) -> None:
        started = entry.pop("started", None)
        row = {"schema_id": REQUEST_LOG_SCHEMA_ID, "ts": time.time()}
        if state is not None:
            row.update(
                token_ref=state.token_ref, attempt_id=state.grant.attempt_id, task_id=state.grant.task_id,
                plane=state.grant.plane, phase=state.grant.phase,
            )
            state.stats["requests"] += 1
            state.stats[f"decision:{entry.get('decision')}"] += 1
            state.stats["bytes"] += int(entry.get("bytes") or 0)
        row.update({k: v for k, v in entry.items() if not k.startswith("_")})
        entry["_logged"] = True  # 同一请求只记一行（取消收尾时据此判断是否已记过）
        if started is not None:
            row["elapsed_seconds"] = round(time.monotonic() - started, 4)
        self._totals["requests"] += 1
        self._totals[f"decision:{entry.get('decision')}"] += 1
        if self._log_fh is not None:
            self._log_fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            self._log_fh.flush()

    def _deny(self, entry: dict[str, Any], state: _TokenState | None, status: int, decision: str) -> web.Response:
        entry.update(status=status, decision=decision)
        self._write_log(entry, state)
        return web.Response(status=status, text=f"{decision}\n", headers={"Cache-Control": "no-store"})

    @web.middleware
    async def _unrouted_middleware(self, request: web.Request, handler):
        try:
            return await handler(request)
        except asyncio.CancelledError:
            tracked = request.get(_TRACK_KEY)
            if tracked is not None:
                state, entry, _task = tracked
                if not entry.get("_logged"):
                    entry.update(decision="withdrawn_in_flight" if state.state != TOKEN_ACTIVE else "cancelled_in_flight")
                    entry.setdefault("status", None)
                    self._write_log(entry, state)
            raise
        except web.HTTPException as exc:
            if exc.status in (404, 405) and not request.get(_LOGGED_KEY):
                entry = self._entry(request, "unrouted")
                entry.update(
                    status=exc.status, decision="method_not_allowed" if exc.status == 405 else "no_route",
                    path_redacted=re.sub(r"^/a/[^/]*", "/a/<token>", request.path),
                )
                self._write_log(entry, None)
            raise
        finally:
            tracked = request.get(_TRACK_KEY)
            if tracked is not None:
                tracked[0].inflight.discard(tracked[2])

    def _authorize(self, request: web.Request, entry: dict[str, Any]) -> tuple[str, _TokenState | None, web.Response | None]:
        token = request.match_info.get("token", "")
        state = self._tokens.get(token) if _TOKEN_RE.match(token) else None
        if state is None:
            return token, None, self._deny(entry, None, 404, "unknown_token")
        if state.state != TOKEN_ACTIVE:
            return token, state, self._deny(entry, state, 403, "token_withdrawn")
        task = asyncio.current_task()
        if task is not None:  # 接纳 = 登记为本 token 的在途请求（中间件在请求结束时摘除）
            state.inflight.add(task)
            request[_TRACK_KEY] = (state, entry, task)
        return token, state, None

    # ---- 路由 ------------------------------------------------------------------------------------------------------

    async def _healthz(self, _request: web.Request) -> web.Response:
        return web.json_response({"ok": True, "schema_id": GATEWAY_SCHEMA_ID})

    async def _simple_root(self, request: web.Request) -> web.Response:
        entry = self._entry(request, "simple_root")
        _token, state, denied = self._authorize(request, entry)
        if denied is not None:
            return denied
        return self._deny(entry, state, 404, "no_root_index")  # pip 只按项目取页，不给全量项目清单

    async def _simple(self, request: web.Request) -> web.Response:
        entry = self._entry(request, "simple")
        token, state, denied = self._authorize(request, entry)
        if denied is not None:
            return denied
        assert state is not None
        dist = normalize_dist(request.match_info.get("dist", ""))
        entry["dist"] = dist
        if not _DIST_RE.match(dist):
            return self._deny(entry, state, 404, "bad_dist")
        allowed_versions: frozenset[str] | None = None
        if dist in state.grant.blocked_dists:
            allowed_versions = state.grant.allowed_releases.get(dist)
            if not allowed_versions:
                return self._deny(entry, state, 404, "blocked_by_policy")
        assert self._session is not None
        try:
            async with self._session.get(
                self.upstream_simple_url + quote(dist) + "/", headers={"Accept": "text/html"}, timeout=self.page_timeout,
            ) as resp:
                entry["upstream_status"] = resp.status
                if resp.status == 404:
                    return self._deny(entry, state, 404, "upstream_not_found")
                if resp.status != 200:
                    return self._deny(entry, state, 502, "upstream_error")
                if "html" not in resp.headers.get("Content-Type", "").lower():
                    return self._deny(entry, state, 502, "upstream_not_html")
                chunks: list[bytes] = []
                size = 0
                async for chunk in resp.content.iter_chunked(_CHUNK):
                    size += len(chunk)
                    if size > self.max_page_bytes:
                        return self._deny(entry, state, 502, "upstream_page_too_large")
                    chunks.append(chunk)
                body = b"".join(chunks)
                page_url = str(resp.url)
                charset = resp.charset or "utf-8"
        except asyncio.TimeoutError:
            return self._deny(entry, state, 504, "upstream_timeout")
        except ClientError:
            return self._deny(entry, state, 502, "upstream_unreachable")
        parser = _AnchorParser()
        parser.feed(body.decode(charset, errors="replace"))
        parser.close()
        anchors: list[_Anchor] = []
        dropped: Counter = Counter()
        for attrs, text in parser.anchors:
            href = attrs.get("href")
            if not href:
                dropped["no_href"] += 1
                continue
            parts = urlsplit(urljoin(page_url, href))
            if parts.scheme not in ("http", "https"):
                dropped["bad_scheme"] += 1
                continue
            if _origin(urlunsplit((parts.scheme, parts.netloc, "", "", ""))) not in self.file_origins:
                dropped["foreign_origin"] += 1
                continue
            filename = unquote(parts.path.rsplit("/", 1)[-1])
            if not _FILENAME_RE.match(filename):
                dropped["bad_filename"] += 1
                continue
            if not is_distribution_filename(filename):
                dropped["not_a_distribution"] += 1  # egg / exe / msi 等 pip 不用的格式
                continue
            version = filename_project_version(filename, dist)
            if version is None:
                dropped["not_this_project"] += 1
                continue
            if allowed_versions is not None and canonical_version(version) not in allowed_versions:
                dropped["blocked_version"] += 1
                continue
            fragment = parts.fragment
            file_hash = fragment if _HASH_RE.match(fragment or "") else None
            if fragment and file_hash is None:
                dropped["hash_fragment_unrecognized"] += 1  # 仍签发，只是不带 hash
            metadata_attr = attrs.get("data-core-metadata", attrs.get("data-dist-info-metadata"))
            core_metadata = metadata_attr if isinstance(metadata_attr, str) and _METADATA_RE.match(metadata_attr) else None
            yanked = attrs.get("data-yanked", False)
            file_url = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
            fid = state.fid_by_url.get(file_url)
            if fid is None:
                fid = secrets.token_urlsafe(12)
                state.fid_by_url[file_url] = fid
            state.issued[fid] = _IssuedFile(url=file_url, filename=filename, dist=dist, metadata=core_metadata is not None)
            anchors.append(_Anchor(
                fid=fid, filename=filename, hash=file_hash,
                requires_python=attrs.get("data-requires-python"),
                core_metadata=core_metadata,
                yanked=None if yanked is False else (yanked or ""),
            ))
        page = _render_page(dist, token, anchors)
        entry.update(status=200, decision="served_page" if allowed_versions is None else "served_page_with_exceptions",
                     files_listed=len(anchors), files_dropped=dict(dropped))
        self._write_log(entry, state)
        headers = {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}
        if request.method == "HEAD":
            headers["Content-Length"] = str(len(page))
            return web.Response(status=200, headers=headers)
        return web.Response(status=200, body=page, headers=headers)

    async def _file(self, request: web.Request) -> web.StreamResponse:
        entry = self._entry(request, "file")
        _token, state, denied = self._authorize(request, entry)
        if denied is not None:
            return denied
        assert state is not None
        fid = request.match_info.get("fid", "")
        name = request.match_info.get("filename", "")
        issued = state.issued.get(fid) if _FID_RE.match(fid) else None
        if issued is None:
            return self._deny(entry, state, 404, "file_not_issued")
        entry.update(dist=issued.dist, filename=issued.filename)
        if name == issued.filename:
            upstream = issued.url
        elif name == issued.filename + ".metadata" and issued.metadata:
            upstream = issued.url + ".metadata"
            entry["kind"] = "metadata"
        else:
            return self._deny(entry, state, 404, "file_name_mismatch")
        assert self._session is not None
        try:
            resp = await self._session.request(
                "HEAD" if request.method == "HEAD" else "GET", upstream, timeout=self.file_timeout, allow_redirects=True,
                headers={"Accept-Encoding": "identity"},  # 文件字节原样转发：不让中间层解压后长度 / hash 对不上
            )
        except asyncio.TimeoutError:
            return self._deny(entry, state, 504, "upstream_timeout")
        except ClientError:
            return self._deny(entry, state, 502, "upstream_unreachable")
        async with resp:
            entry["upstream_status"] = resp.status
            if any(_origin(str(hop.url)) not in self.file_origins for hop in (*resp.history, resp)):
                return self._deny(entry, state, 502, "upstream_redirect_foreign")
            if resp.status == 404:
                return self._deny(entry, state, 404, "upstream_not_found")
            if resp.status != 200:
                return self._deny(entry, state, 502, "upstream_error")
            out = web.StreamResponse(status=200, headers={
                "Content-Type": resp.headers.get("Content-Type", "application/octet-stream"), "Cache-Control": "no-store",
            })
            length = resp.headers.get("Content-Length")
            encoded = resp.headers.get("Content-Encoding", "identity").lower() not in ("", "identity")
            if length is not None and length.isdigit() and not encoded:
                out.content_length = int(length)
            await out.prepare(request)
            entry.update(status=200, response_started=True, bytes=0)
            sent = 0
            decision = "served_file" if entry["kind"] == "file" else "served_metadata"
            if request.method != "HEAD":
                try:
                    async for chunk in resp.content.iter_chunked(_CHUNK):
                        if state.state != TOKEN_ACTIVE:
                            decision = "withdrawn_in_flight"
                            break
                        await out.write(chunk)
                        sent += len(chunk)
                        entry["bytes"] = sent  # 被取消时的日志按实际已发字节记
                except (ConnectionResetError, ConnectionError):
                    decision = "client_disconnected"
                except (asyncio.TimeoutError, ClientError):
                    decision = "upstream_stream_error"
            entry.update(status=200, decision=decision, bytes=sent)
            self._write_log(entry, state)
            if decision in ("served_file", "served_metadata"):
                await out.write_eof()
            elif request.transport is not None:
                # 在途中断：不发正常结尾，直接断开——带 Content-Length 的是短读，分块传输缺终止块，客户端都会报错而不会把
                # 半截文件当完整
                request.transport.abort()
            return out
