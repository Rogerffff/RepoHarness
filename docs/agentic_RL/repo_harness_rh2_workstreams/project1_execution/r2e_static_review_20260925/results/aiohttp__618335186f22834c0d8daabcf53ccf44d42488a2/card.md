# aiohttp 61833518 静态审查短卡

> **2026-09-25 协调者更正（按 Codex 复核 r2e_static_actor_review_20260925/README.md）**：I1 已由执行证实：AP1（只在 _write_length_payload 跳过空块）真实评分 47/47 得 1，但 chunked 响应仍以终止块开头；AP2 得 1 且 C3 正常。card 里"断言正文精确相等"与"真实评分已安排"是旧口径，现按语义化 C3：分块格式完整、终止块恰好一个且在末尾、拼起来解压等于原载荷；允许与 gold 不同的合法分帧，不要求字节等于 gold。脚本 rh2/experiments/r2e_actor_20260925/postcheck/aiohttp_61833518_c3.py，入口 run_postcheck.py；已用 gold / AP2 通过、AP1 与 base 不通过验证。 探针结果报原始 reward 与 C3 后检两列；因还原兼容改写（client.py、client_reqrep.py）导致 import 失败而得 0 的，按环境陷阱计。 以下原文保留不改。

主审 2026-09-25，读过历史后定稿。依据：[初稿](analysis_before_history.md)、[旧主张核对](old_findings_delta.md)。

## 1. 题目与用途

- **版本**：aiohttp 0.17.0a0，base `ff3dec42`；派生镜像配方 `r2e_derive_v1`，Python 3.9.21。本题没有材料修订。
- **缺陷**：压缩过滤器遇到小输入时产出 `b''`，`HttpMessage.write()` 原样交给写出器。后果取决于写出器：
  - Content-Length 写出器：出现 `transport.write(b'')`；
  - chunked 写出器：在正文前写出 `0\r\n\r\n`，即提前发出结束块。
- **gold**：在 `write()` 的过滤器循环里加一句 `if chunk:`，丢弃空块。
- **隐藏测试**：等于公开的 `tests/test_http_protocol.py`，只在 3 个测试里各加一句 `assertTrue(all(chunks))`。期望映射共 47 键，全部 PASSED。
- **处置**：`needs_review`，理由为"静态候选待 actor 验证"；用途 `development_diagnostic`。作为探针候选的条件：每个得 1 的补丁都要加跑 C3。

## 2. 关键映射

| 需求或旧行为 | 公开依据 | 测试 / 决定性断言 | 覆盖情况 | 执行证据或下一步验证 |
| --- | --- | --- | --- | --- |
| 示例配置不产生空写入（设 Content-Length，先分块过滤器 2 字节、再 deflate） | 题面 Example / Expected | `test_write_payload_chunked_and_deflate` 的 `all(chunks)`（test_1.py:474） | 覆盖 | noop 两次都在这里失败，gold 两次通过；C2：base 为 `[b'', b'', …] False`，gold 为 `[b'KI,I\x04\x00'] True` |
| 只加压缩过滤器、设 Content-Length 时不产生空写入 | Expected Behavior 的推广 | `test_write_payload_deflate_filter`（:438） | 覆盖（推知） | 同上 |
| 压缩在最后且用 chunked 写出器时，不得提前写出 `0\r\n\r\n` | 标题、Description、Actual | 无 | **缺失（I1）** | C3 在 base 下复现，gold 修好；P1 待真实评分 |
| 压缩字节不变、分块切分不变、结束块只写一次、长度截断不变 | 公开测试 | 45 个回归键中的写出类用例 | 覆盖 | 4 次评分结果一致 |

## 3. 八方面：已查 / 未查

- **公开需求**
  - 已查：题面、示例和公开测试；R-f 渲染出的任务正文与 `user_prompt.txt` 逐字相同。
  - 未查：正式链里组装后的完整消息（提示加正文）。
- **材料与初态**：哈希、base、gold 能否应用、noop 失败位置、C2/C3 在 base 下的复现，均已查。
- **测试是否测到要求**：47 个测试的断言已全部通读；标题描述的场景没有覆盖（I1）。
- **是否误拒合理解**
  - 已查：A1、A2 经静态追踪可以通过；P2、P3 被拒有公开依据。
  - 未查：没有实际运行替代解。
- **回归与 gold**
  - 已查：追踪了调用方（web、client、wsgi、multipart）；应用 gold 后 3 个公开测试文件没有新增失败。
  - 未查：其余测试文件。
- **开发条件**
  - 已查：正式任务面的 devcheck（agent 54321）确认了导入、`python -m pytest`、没有 pip、没有出网。
  - 未查：actor 侧真实交付（编辑 → 冻结 → 投影）没有演练。
- **交付与评分**
  - 已查：隐藏测试恢复、投影、解析、与 M3 和参考日志的对账。
  - 未逐题审：根目录 `conftest.py` 等共享控制面。
- **题目关系**：同源、同仓的题目关系没有查。

## 4. 问题与证据层次

- **I1 漏测**（静态推断，把握高）
  - 现象：只在长度写出器里跳过空块的 P1 预计拿到 47/47，但 C3 失败。
  - 影响：探针和训练都会出现假阳性，一个没修好标题 bug 的补丁也得 1。
  - 缓解：对通过的补丁加跑 C3，或者出修订版补一个隐藏键。
- **I2 题面误导**（静态推断）
  - 示例断言 `all(write.mock_calls)` 按原样写恒为真，照抄示例的人会以为复现不了。
  - 示例用的是 Content-Length 写出器，不是标题描述的 chunked 路径。只修 chunked 写出器的 P2 会得 0；因为示例配置本身就是 Content-Length，判 0 有依据。
  - 这推翻了旧记录 R03 的"照写即复现"：旧复现脚本其实改用了 `c[1][0]`。
- **I3 开发陷阱**（静态推断，并有代码依据）
  - 来源镜像的兼容改写涉及 4 个文件，它们在 Claude Code 的 gitStatus 里显示为 `M`。
  - 候选如果把它们还原，这些还原会作为 delta 在评分时重放；`asyncio.async(` 在 Python 3.9 下是语法错误，结果是全部收集失败、得 0。
  - 这是对旧记录 R04 的补充。
- **环境侧条件**（历史已核，本次确认）
  - `/testbed` 必须在 sys.path 上，测试要用 `python -m pytest`；
  - venv 里没有 pip，也不能出网；
  - 兼容改写使真实客户端和服务端报 `TypeError`；
  - `test_web_response` 有 3 个与本题无关的 cookie 失败（新增记录）。
- **正式 actor 面**：改用派生镜像并使用 R2E 提示，协调者称已实施，待 A 线审查；新的提示文本我没有见到。

## 5. 候选补丁

每条都可以直接写成补丁。预期结果除 gold 外都是静态推断。C3 指 devcheck 的 `mcve_c3_chunked`。

| 候选 | 怎么改 | 预期得分 | 预期 C3 |
| --- | --- | --- | --- |
| **gold**（参照） | `HttpMessage.write()` 的过滤器循环里，把 `self.writer.send(chunk)` 改成 `if chunk: self.writer.send(chunk)` | 47/47，得 1（已执行） | 通过，正文为 `b'6\r\nKI,I\x04\x00\r\n0\r\n\r\n'`（已执行） |
| **A1**（合理替代解） | `add_compression_filter` 的非 EOF 分支，把 `yield zcomp.compress(chunk)` 改成 `data = zcomp.compress(chunk)` 加 `if data: yield data`；随后的 `chunk = yield EOL_MARKER` 与 EOF 分支都不动 | 47/47，得 1 | 通过，正文与 gold 相同 |
| **A2**（合理替代解） | `_write_chunked_payload` 在 `chunk = bytes(chunk)` 之后、`_write_length_payload` 与 `_write_eof_payload` 在 `except aiohttp.EofStream: break` 之后，各加一句 `if not chunk: continue` | 47/47，得 1 | 通过，正文与 gold 相同 |
| **P1**（部分修复，会造成假阳性） | 只在 `_write_length_payload` 的 `except … break` 之后加 `if not chunk: continue` | 47/47，得 1 | **失败**：正文仍为 `b'0\r\n\r\n6\r\nKI,I\x04\x00\r\n0\r\n\r\n'` |
| **P2**（部分修复） | 只在 `_write_chunked_payload` 的 `chunk = bytes(chunk)` 之后加 `if not chunk: continue` | 45/47，两个目标键 FAILED，得 0 | 通过 |
| **P3**（部分修复） | 只把 `filter_pipe` 最内层循环里的 `yield chunk` 改成 `if chunk: yield chunk` | 46/47，只有 `test_write_payload_deflate_filter` FAILED，得 0 | 失败：单个过滤器不经过 `filter_pipe` |

**C3 的加强建议**：真实评分时，把判据改为正文必须恰好等于 `b'6\r\nKI,I\x04\x00\r\n0\r\n\r\n'`；再加一个 gzip、分两次写入的变体。按预期，gold、A1、A2 都通过，P1 失败。

## 6. 建议与下一步

- **与历史的分歧**：I1、I2（对应旧 R03）、I3（补充旧 R04）。环境方面的结论与历史一致。独立 reviewer 尚未复核。
- **修订选项（待定）**：
  - 如果 P1 在真实评分中得 1 且 C3 失败，考虑出一个修订版：补一个隐藏键，配置为 HTTP/1.1、不设 Content-Length、只加压缩过滤器，断言正文精确相等。修订后需验证 gold、A1、A2 通过而 P1 失败。
  - 可选：把题面示例的断言改成 `c[1][0]`。
  - 对 I3，在提示里写明那 4 个 `M` 文件是环境兼容改写、不要还原（任务面决定，对应决定 E10）。
- **唯一优先下一步**：协调者已安排 P1 与 A1 的真实评分并加跑 C3，看结果能否确认 I1。
