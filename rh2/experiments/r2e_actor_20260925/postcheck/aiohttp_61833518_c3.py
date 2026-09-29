"""aiohttp 61833518 的事后复核：语义化的 C3（在应用了候选补丁的 /testbed 里、用 /testbed/.venv 的 python 运行）。

题面标题说的是"deflate 压缩 + 分块传输时发出空块、响应提前结束"，隐藏测试只走 Content-Length 写出器，没覆盖
"压缩在后 + chunked 写出器"。2026-09-25 真实评分：只在 Content-Length 写出器跳过空块的部分修复得 1，但 chunked
响应仍以终止块开头。旧 C3 只看"正文是否以 0\\r\\n\\r\\n 开头"，空正文、错误正文、缺终止块也能通过（Codex 复核）。

本脚本按语义判定，不要求字节等于 gold：
- chunked 场景（HTTP/1.1、无 Content-Length、只加 deflate 过滤器）：分块格式完整；终止块恰好一个且在末尾；
  终止块之前没有零长度块；各块数据拼起来按 raw deflate 解压后等于原载荷。同一压缩流按别的方式合法分帧也通过。
- Content-Length 场景（题面配置：content-length + chunking 过滤器 + deflate）：头之后没有空的 transport.write；
  写出的数据拼起来解压后等于原载荷。
每个场景单独 try/except。输出一行 JSON。`--selftest` 只检查分块解析器本身（不需要 aiohttp）。
"""

from __future__ import annotations

import json
import sys
import zlib

PAYLOADS = {
    "one_write": [b"data"],
    "two_writes": [b"da", b"ta"],
    "large_three_writes": [bytes(range(256)) * 16, b"x" * 3000, b"tail"],
}


def parse_chunked(body: bytes) -> tuple[bool, str, bytes]:
    """严格解析 chunked 正文：返回 (是否合法, 原因, 各块数据拼接)。零长度块只能作为最后的终止块出现。"""

    data = b""
    pos = 0
    while True:
        eol = body.find(b"\r\n", pos)
        if eol < 0:
            return False, "missing_size_line_or_terminator", data
        size_txt = body[pos:eol].split(b";", 1)[0].strip()
        try:
            size = int(size_txt, 16)
        except ValueError:
            return False, f"bad_size_line:{size_txt[:20]!r}", data
        pos = eol + 2
        if size == 0:
            if body[pos:] != b"\r\n":
                return False, "zero_chunk_not_at_end_or_bad_trailer", data
            return True, "ok", data
        chunk = body[pos:pos + size]
        if len(chunk) != size or body[pos + size:pos + size + 2] != b"\r\n":
            return False, "truncated_chunk", data
        data += chunk
        pos += size + 2


def inflate(raw: bytes) -> bytes:
    d = zlib.decompressobj(wbits=-zlib.MAX_WBITS)
    return d.decompress(raw) + d.flush()


def run_response(protocol, writes: list[bytes], *, content_length: bool):
    import unittest.mock

    transport = unittest.mock.Mock()
    write = transport.write = unittest.mock.Mock()
    msg = protocol.Response(transport, 200)
    if content_length:
        c = zlib.compressobj(wbits=-zlib.MAX_WBITS)
        comp = c.compress(b"".join(writes)) + c.flush()
        msg.add_headers(("content-length", str(len(comp))))
        msg.add_chunking_filter(2)
    msg.add_compression_filter("deflate")
    msg.send_headers()
    for w in writes:
        msg.write(w)
    msg.write_eof()
    return [call[1][0] for call in write.mock_calls]


def check(protocol) -> list[dict]:
    out = []
    for name, writes in PAYLOADS.items():
        payload = b"".join(writes)
        try:
            args = run_response(protocol, writes, content_length=False)
            raw = b"".join(bytes(a) for a in args)
            head, sep, body = raw.partition(b"\r\n\r\n")
            if not sep:
                out.append({"scenario": f"chunked:{name}", "ok": False, "reason": "no_header_terminator"})
                continue
            ok, why, data = parse_chunked(body)
            if ok:
                try:
                    ok = inflate(data) == payload
                    why = "ok" if ok else "payload_mismatch"
                except zlib.error as exc:
                    ok, why = False, f"inflate_error:{exc}"[:80]
            out.append({"scenario": f"chunked:{name}", "ok": ok, "reason": why, "body_head": repr(body[:24])})
        except Exception as exc:  # noqa: BLE001
            out.append({"scenario": f"chunked:{name}", "ok": False, "reason": f"{type(exc).__name__}: {exc}"[:160]})
        try:
            args = run_response(protocol, writes, content_length=True)
            body_args = args[1:]  # 第一条是响应头
            empty = sum(1 for a in body_args if not a)
            try:
                same = inflate(b"".join(bytes(a) for a in body_args)) == payload
            except zlib.error:
                same = False
            ok = empty == 0 and same
            out.append({"scenario": f"content_length:{name}", "ok": ok,
                        "reason": "ok" if ok else f"empty_writes={empty},payload_ok={same}"})
        except Exception as exc:  # noqa: BLE001
            out.append({"scenario": f"content_length:{name}", "ok": False, "reason": f"{type(exc).__name__}: {exc}"[:160]})
    return out


def selftest() -> int:
    c = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    comp = c.compress(b"data") + c.flush()
    cases = {
        "gold_like": (b"%x\r\n" % len(comp) + comp + b"\r\n0\r\n\r\n", True),
        "split_2_plus_rest": (b"2\r\n" + comp[:2] + b"\r\n" + b"%x\r\n" % (len(comp) - 2) + comp[2:] + b"\r\n0\r\n\r\n", True),
        "premature_terminator": (b"0\r\n\r\n" + b"%x\r\n" % len(comp) + comp + b"\r\n0\r\n\r\n", False),
        "empty_body": (b"", False),
        "missing_terminator": (b"%x\r\n" % len(comp) + comp + b"\r\n", False),
        "only_terminator": (b"0\r\n\r\n", None),  # 格式合法，但解压后不等于载荷 -> 由载荷比较判失败
    }
    bad = []
    for name, (body, want_framing) in cases.items():
        ok, why, data = parse_chunked(body)
        if want_framing is None:
            payload_ok = ok and data == b"" and inflate(data) == b"data"
            if payload_ok:
                bad.append(name)
            continue
        if ok != want_framing:
            bad.append(name)
        elif ok and inflate(data) != b"data":
            bad.append(name)
    print(json.dumps({"selftest": "pass" if not bad else "fail", "bad": bad}))
    return 0 if not bad else 1


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    sys.path.insert(0, "/testbed")
    from aiohttp import protocol

    results = check(protocol)
    failed = [r["scenario"] for r in results if not r["ok"]]
    print("RH2_POSTCHECK=" + json.dumps({"task": "aiohttp__61833518", "verdict": "pass" if not failed else "fail",
                                         "failed": failed, "items": results}, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
