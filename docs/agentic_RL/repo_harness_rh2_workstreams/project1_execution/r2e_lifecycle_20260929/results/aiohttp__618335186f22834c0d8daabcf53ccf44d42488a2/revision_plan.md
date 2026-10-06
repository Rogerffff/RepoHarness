# aiohttp 61833518 修订方案（R-c：补 chunked 标题场景）

2026-09-29 · 修订执行者（Claude，单题闭环试行，统一标准 v1 §5 模板内）。

**状态：修订草案已定稿，试跑验收通过（试跑工具，不是正式评分）。** 待协调者落正式修订单与派生镜像材料、跑正式评分，再送 Codex 复核。

路径约定：
- 仓库根相对路径。`PUB` = `runs/r2e_static_prep_20260924/v3/public/aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2/`，`PRIV` = 同目录下 `private/…`。
- `trials/`、`cands/`、`revision_draft.json` 相对本目录。

## 1. 结论

| 项 | 内容 |
| --- | --- |
| 模板 | R-c：补有公开依据的核心场景断言。只针对一个窄问题：标题场景（chunked 传输编码 + 压缩在最后）没有任何隐藏断言 |
| 改动 | 在 `r2e_tests/test_1.py` 的 `TestHttpMessage` 里加 1 个解析辅助方法和 2 个测试；不删、不改任何已有测试 |
| 期望映射 | 47 键 → 49 键，新增 2 键都是 PASSED；原 47 键不变 |
| 试跑 | gold 1、noop 0、AP1 0、AP1m 0、AP2 1、A1 1；当前材料上 AP1、AP1m 都是 1，说明误判在本镜像上确实存在 |
| 边界 | 没有改题面，也没有扩到 gzip、HTTP/1.0 写出器或不经过滤器的 `write(b'')` |

## 2. 要纠正的误判

- **触发反例 AP1**（`runs/r2e_actor_20260925/grader_cands/aiohttp_6183_AP1_skip_empty_in_length_writer_only.patch`）只在 `_write_length_payload` 里跳过空块。
  - 当前材料下得 1：历史见 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/grader_candidates.md:33`，本镜像见 `trials/cur_AP1.json`（47/47）。
  - 实际没修好标题说的问题：chunked 响应正文以终止块开头，为 `0\r\n\r\n6\r\nKI,I\x04\x00\r\n0\r\n\r\n`（`runs/r2e_actor_20260925/grader/aiohttp_c2c3/AP1.json`）。
- **原因**：两个目标键都用 Content-Length 写出器（`PRIV/hidden_tests/test_1.py:427-441`、`:461-477`），没有一个键走 chunked 写出器配压缩过滤器这条路径（首批 Codex 复核 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_actor_review_20260925/README.md:62,70`）。

## 3. 公开依据

- **题面**（`PUB/user_prompt.txt`）：
  - 标题 `:4`：Deflate Compression Sends Empty Chunks in Chunked Responses, Causing Premature EOF。
  - 描述 `:7`：发送带 deflate 压缩的 chunked HTTP 响应时，会发出大小为 0 的块，导致响应提前表示结束。
  - Expected `:24`、Actual `:27`：所有块的大小都应大于 0，不能提前发出结束信号。
- **公开代码事实**（`PUB/worktree/`）：
  - `aiohttp/protocol.py:631-635`：调用 `enable_chunked_encoding()`，或 HTTP/1.1 且没有 Content-Length 时，选用 `_write_chunked_payload`。
  - `aiohttp/protocol.py:713-728`：空块照样写出 `0\r\n` + `b''` + `\r\n`，线上字节与 `:719` 的终止块相同。aiohttp 自己的解析器读到 size 0 就结束正文（`:330`）。
  - `aiohttp/protocol.py:784-799`：压缩过滤器直接 yield `zcomp.compress(chunk)`，小输入时为 `b''`。
  - `aiohttp/web_reqrep.py:554-563`：`StreamResponse` 开了压缩、又开了 chunked 但没给 `chunk_size` 时，只加压缩过滤器并走 chunked 写出器。这是真实生产路径（复核 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2/review.md:104`）。
- **公开旧测试的口径**（`PUB/worktree/tests/test_http_protocol.py`）：
  - `:340-353` 规定 chunked 正文格式 `4\r\ndata\r\n0\r\n\r\n`。
  - `:424-425` 的 `_COMPRESSED` 是 raw deflate。
  - `:441-455` 是先压缩、后分块的逐字节比较。
- **断言口径**：按首批 Codex 复核（`…/r2e_static_actor_review_20260925/README.md:70`）做语义判断，不要求字节等于 gold。新测试检查三件事：
  1. 分块格式完整；
  2. 终止块恰好一个，并且在最后；
  3. 各块数据拼起来按 raw deflate 解压后等于原载荷。

  另加 `all(chunks)`，也就是题面示例自己的判据（`PUB/user_prompt.txt:19-20`），只是把它用到标题场景上。
- **不扩大需求**：
  - 只测 deflate（标题所说），只测压缩在最后加 chunked 写出器（标题与描述所说）。
  - gzip、HTTP/1.0 的 `_write_eof_payload`、不经过滤器直接 `write(b'')`（公开读者 R9 列为未定）都不加。
  - 客户端路径不受本 bug 影响：`client_reqrep.py` 压缩时总会在后面接分块过滤器（复核 `review.md:88`）。

## 4. 具体改动

- **目标文件**：`r2e_tests/test_1.py`，即 `PRIV/hidden_tests/test_1.py`。
- **插入位置**：插在 `test_write_payload_chunked_and_deflate`（`:461-477`）之后、`test_write_drain`（`:479`）之前。
- **草案条目**：`hidden_test_text_replace`，一处 edit。`old` 是 `    def test_write_drain(self):\n`，在文件中唯一；`new` 是下面这段代码加上原来的这一行。

```python
    def _chunked_body_payload(self, body):
        """Payload carried by an HTTP/1.1 chunked body.

        The zero-size chunk ends the body, so it must come last and appear
        exactly once; a zero-size chunk before the data is a premature EOF.
        """
        payload = b''
        pos = 0
        while True:
            eol = body.find(b'\r\n', pos)
            self.assertNotEqual(-1, eol, 'chunk size line is missing')
            size = int(body[pos:eol], 16)
            pos = eol + 2
            if size == 0:
                self.assertEqual(b'\r\n', body[pos:],
                                 'data after the terminating chunk')
                return payload
            self.assertEqual(b'\r\n', body[pos + size:pos + size + 2])
            payload += body[pos:pos + size]
            pos += size + 2

    def test_write_payload_deflate_chunked_encoding(self):
        # chunked transfer encoding + deflate, no chunking filter
        write = self.transport.write = unittest.mock.Mock()
        msg = protocol.Response(self.transport, 200)
        msg.enable_chunked_encoding()
        msg.add_compression_filter('deflate')
        msg.send_headers()

        msg.write(b'data')
        msg.write_eof()

        chunks = [c[1][0] for c in list(write.mock_calls)]
        self.assertTrue(all(chunks))
        content = b''.join(chunks)
        payload = self._chunked_body_payload(
            content.split(b'\r\n\r\n', 1)[-1])
        self.assertEqual(b'data', zlib.decompress(payload, -zlib.MAX_WBITS))

    def test_write_payload_deflate_chunked_encoding_multiple_writes(self):
        # HTTP/1.1 without Content-Length selects chunked transfer encoding
        write = self.transport.write = unittest.mock.Mock()
        msg = protocol.Response(self.transport, 200)
        msg.add_compression_filter('deflate')
        msg.send_headers()

        msg.write(b'data1')
        msg.write(b'data2')
        msg.write_eof()

        chunks = [c[1][0] for c in list(write.mock_calls)]
        self.assertTrue(all(chunks))
        content = b''.join(chunks)
        payload = self._chunked_body_payload(
            content.split(b'\r\n\r\n', 1)[-1])
        self.assertEqual(b'data1data2',
                         zlib.decompress(payload, -zlib.MAX_WBITS))
```

两个测试各管一个入口：
- 第一个显式调用 `enable_chunked_encoding()`，对应 web 层的生产路径；
- 第二个不设 Content-Length，靠 HTTP/1.1 自动选 chunked，并写两次，让每次写入都产生空的压缩输出。

## 5. 期望映射逐键变化

- 原 47 键：不变，全部 PASSED。
- 新增 `TestHttpMessage.test_write_payload_deflate_chunked_encoding`：PASSED。
- 新增 `TestHttpMessage.test_write_payload_deflate_chunked_encoding_multiple_writes`：PASSED。
- 合计 49 键，完整映射见 `revision_draft.json` 的 `expected_after`。
- **版本记录**：

  | 文件 | sha256 前 8 位 |
  | --- | --- |
  | 父版本 `test_1.py` | `89f3cf5e` |
  | 父版本 `expected_output.json` | `f0423107` |
  | 修订后 `test_1.py` | `89702c7c` |
  | 试跑用 `draft.json` | `f89b2aae` |
  | 试跑用 `expected_after.json` | `290db09b` |

  父版本隐藏测试树摘要为 `7570cfed…`。全值见 `revision_draft.json` 的 `parent_material`、`trial_draft_sha256` 与 `revised_test_file_sha256`。

## 6. 验收计划与试跑结果

**试跑环境**：
- 派生镜像 `sha256:e647c9763316…`，配方 `r2e_derive_v1+sysconfig_v1`；
- 工具 `rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`，只作试跑，与正式评分的差别见其文件头；
- 各候选 `git apply` 均成功，草案均报 `RH2_TRIAL_EDITS_APPLIED=1`。

**环境确认**（当前材料）：noop 失败的正好是两个目标键（`trials/env_noop_current.json`）；gold 47/47（`trials/env_gold_current.json`）。与历史 R-f、复跑、M3 的结果一致。

**修订草案下的验收**：

| 候选 | 补丁 | 应得 | 应失败的键 | 试跑结果 |
| --- | --- | --- | --- | --- |
| gold（正对照） | `PRIV/gold.patch` | 1 | — | 1，49/49（`trials/rev_gold.json`） |
| noop | 无 | 0 | 2 个原目标键 + 2 个新键 | 0，恰好这 4 键（`trials/rev_noop.json`） |
| AP1（已知错误，触发反例） | 见 §2 | 0 | 2 个新键 | 0，恰好 2 个新键，失败在 `all(chunks)`（`trials/rev_AP1.json`）；当前材料为 1（`trials/cur_AP1.json`） |
| AP1m（构造的错误候选） | `cands/aiohttp_6183_AP1m_length_skip_plus_single_write_frames.patch`：AP1，再把 chunked 写出器的三次 write 合成一次，空块仍照发 | 0 | 2 个新键 | 0，恰好 2 个新键，失败在分帧检查 `data after the terminating chunk`（`trials/rev_AP1m.json`）；当前材料为 1（`trials/cur_AP1m.json`） |
| AP2（合理替代） | `runs/r2e_actor_20260925/grader_cands/aiohttp_6183_AP2_skip_empty_in_both_writers.patch` | 1 | — | 1，49/49（`trials/rev_AP2.json`） |
| A1（合理替代） | `cands/aiohttp_6183_A1_skip_empty_in_compression_filter.patch`：压缩过滤器不 yield 空的压缩输出 | 1 | — | 1，49/49（`trials/rev_A1.json`） |

补充说明：
- **AP1m 的作用**：证明新测试直接检测提前 EOF，而不只是检测空的 `transport.write`。只看 `all(chunks)` 的话，这种"合并写入、仍发空块"的补丁能蒙过去。
- **A1**：审查时一直未跑（复核 `review.md:146` 的未知项 1），这次补上，没有误拒。
- **本题没有误拒案例**：AP2、A1 在修订前后都应得 1，修订后实测为 1。

## 7. 修订后仍受保护的公开要求

- **R1 示例配置无空写入**（Content-Length 写出器）：原两个目标键。
- **R2 标题场景不提前 EOF**（chunked + deflate）：新增两键。
- **R3 压缩载荷完整**：原有的 `_COMPRESSED` 比较，加上新键的解压比较。
- **R4 终止块恰好一个且在末尾**：新键的分帧检查，加上原有 chunked 逐字节测试。
- **未覆盖，登记为 T3**：
  - gzip；
  - HTTP/1.0 的 `_write_eof_payload`；
  - 不经过滤器直接 `write(b'')`（R9，题面未定）；
  - 大块、多次写入中夹杂非空压缩输出的情形。后检脚本 `rh2/experiments/r2e_actor_20260925/postcheck/aiohttp_61833518_c3.py` 的 `large_three_writes` 仍可用于探针判读。

## 8. 边界与交接

- **只做 R-c**。题面示例的字面断言 `all(write.mock_calls)` 恒为真（旧 I2，P4），不在本包范围，保持登记。
- **正式修订后**，旧探针条件"每个得 1 的补丁加跑 C3 后检"的主要用途由隐藏测试接管。是否保留该后检作为补充判读，由协调者定。
- **协调者待办**：
  1. 把 `revision_draft.json` 的 `revisions` 落为正式修订单；
  2. 重建材料；
  3. 按本表至少跑 gold、noop、AP1、AP2 的正式评分；
  4. 送 Codex 复核。

  本方案没有写 `s2_r2e` 下的正式材料，也没有改生产代码。
