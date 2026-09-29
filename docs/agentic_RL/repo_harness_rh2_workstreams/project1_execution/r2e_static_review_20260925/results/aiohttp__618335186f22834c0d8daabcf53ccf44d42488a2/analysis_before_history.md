<!-- 协调者注（2026-09-25）：宿主不允许子会话写报告文件（"Subagents should return findings as text"），本文由协调者从该会话被拒的写入调用中原样取出保存，未改一字。 -->
# 私有主审分析（读历史前）：aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2

- 角色：R2E 私有主审（静态审查），2026-09-25。在读任何历史调查之前保存本稿。
- 方法依据：角色卡 `roles/investigator_r2e.md`、八方面协议、R2E 当批环境卡、记录模板、40 项清单（编号只用于 §9 的预览）。
- 本次没有运行项目代码，没有开容器或登录远端，没有修改任何原件。只读了 `run_refs.json` 指向的账本行和 eval log，以及协调者给出的 devcheck 目录。完整阅读范围见附录 C。
- 证据标签：
  - 【评分侧执行】：`run_refs.json` 中 `material=current` 的 4 行账本及其日志。派生镜像 `d58fc357…`，评分用户 54322。
  - 【actor 实验层执行】：devcheck `orig/`。走正式启动路径，用真实 Claude Code 2.1.205，模型换成桩端点；agent 身份 54321；派生镜像 `0bf7bf28…`；R2E 层是实验入口 `experiments/r2e_actor_20260925/r2e_devcheck.py`。
  - 【私有对照】：devcheck `private_gold/`。同一镜像，root 身份，不联网，先应用 gold 再跑同一批公开命令。
  - 【独立参考】：M3 独立 runner 在来源镜像上跑 gold 的日志。
  - 【静态】：读代码推断，没有执行。

## 0. 暂定结论

**题目目标。** 压缩过滤器遇到小输入时，`zcomp.compress()` 返回 `b''`。`HttpMessage.write()` 会把这个空块原样交给写出器，后果取决于写出器：
- Content-Length 写出器：产生 `transport.write(b'')`；
- chunked 写出器：写出 `0\r\n\r\n`，即在正文结束前提前发出结束块。

**已核实的事实。**
- 材料彼此对应。初态确有此 bug。noop 与 gold 的分差来自目标行为。三点都有执行证据（§1）。
- 隐藏测试等于公开的 `tests/test_http_protocol.py` 在 3 个测试里各加一句 `assertTrue(all(chunks))`。期望映射共 47 键，全部是 PASSED，没有需要"继续失败"的键。

**暂定处置。** 静态候选，用途为 `development_diagnostic`；`state` 保留 `needs_review`，reason 写"静态候选待 actor 验证"。附带条件：用于探针时，每个得 1 的补丁还要加跑 C3。原因见下面的 I1。

**本题问题（都不阻塞诊断用途）：**
- **I1 漏测**（静态推断，把握较高，待 CPU 反例确认）：两个目标键只在 Content-Length 写出器下检查"没有空的 `transport.write`"。标题描述的场景没有任何隐藏键覆盖；这个场景是压缩过滤器排在最后、使用 chunked 写出器，结果提前写出 `0\r\n\r\n`。因此，一个只在 `_write_length_payload` 里跳过空块的部分修复（下称 P1），预计能拿到 47/47；可是 C3 仍然会复现提前出现的结束块。
- **I2 题面误导**（静态推断）：
  - 示例断言 `all(write.mock_calls)` 按字面写恒为真，照抄示例的人会以为复现不了。
  - 示例用的是 Content-Length 写出器，标题说的"提前 EOF"只会在 chunked 写出器下发生，两者不是同一条路径。
  - 后果：只修 chunked 写出器的解（下称 P2）会得 0。示例本身就是这个配置，所以判 0 有依据，但被题面误导走到这一步的风险是真实的。
- **I3 开发陷阱**（静态推断）：来源镜像的兼容改写以"未提交修改"的形式出现在 Claude Code 的 gitStatus 里。如果候选把这些改动还原，`import aiohttp` 在 Python 3.9 下会报语法错误，隐藏测试全部收集失败，结果是 0。

**R2E 共享问题（不是本题特有，按环境卡处理）：**
- **S1**：正式 actor 目前仍取来源镜像。来源镜像里 `/r2e_tests` 对所有用户可读，git 上也能到达修复提交。
- **S2**：提示里写的是 conda / pip（环境卡编号 E09），与本镜像不符。
- **S3**：实际渲染给模型的题面消息没有被捕获。

**唯一优先的下一步。** 做一次 CPU 定点对照（§11 的 Q1）：在同一配方的派生镜像里，分别应用 P1 和一个合理替代解 A1，各跑隐藏测试和 C3。

## 1. 材料与初态核对（清单 1、2、20）

| 项 | 事实 | 证据 |
| --- | --- | --- |
| base | `ff3dec422bd18b5e9078b5f29be1c9a6a1373f5a`。devcheck 里 `GIT_HEAD` 同值，HEAD 没有子提交，refs、remotes、reflog 都是 0 | `worktree_manifest.json`；`orig/prelaunch.json` 的 probe_facts；`orig/attempt.json` 的 git_sanitize |
| 隐藏测试 | `test_1.py` 的 sha256 为 `89f3cf5e…`，与 `grading_bundle.json` 一致；`__init__.py` 为空文件。整棵目录的哈希 `7570cfed…` 与评分日志里的 `RH2_SETUP_HIDDEN_TESTS_TREE` 一致 | 本地 shasum；评分日志 |
| 与公开测试的差异 | 只有 3 处。`test_write_payload_deflate_filter`、`test_write_payload_deflate_and_chunked`、`test_write_payload_chunked_and_deflate` 各把 `content = b''.join([...])` 改成先取 `chunks = [c[1][0] for c in list(write.mock_calls)]`，再 `self.assertTrue(all(chunks))`（test_1.py:437-439、454-456、473-475） | 与 `worktree/tests/test_http_protocol.py` 的 `diff -u` |
| 期望映射 | 47 键，与 47 个测试方法一一对应，全部 PASSED。只有一个类 `TestHttpMessage`，没有重名 | `expected_output.json`；逐名比对 |
| gold | 只改 `aiohttp/protocol.py` 中 `HttpMessage.write()` 的过滤器循环：`if chunk: self.writer.send(chunk)` | `gold.patch:5-12` |
| 评分入口 | `PYTHONWARNINGS=… .venv/bin/python -W ignore -m pytest -rA r2e_tests`；`revisions.json` 为 `[]` | `run_tests.sh` |

**运行证据**

- 【评分侧执行】noop 共两次（09-23 的 R-f 全池一次，09-24 的环境轮中央复跑一次）：
  - 两次都是 45/47，不匹配的正好是两个目标键。
  - 失败都发生在 `self.assertTrue(all(chunks))`，位置 `r2e_tests/test_1.py:474` 与 `:438`，报错 `AssertionError: False is not true`。
  - 两份日志去掉时间戳后逐字相同。
- 【评分侧执行】gold 两次：都是 47/47，`RESOLVED_FULL`，`projection.included_paths=["aiohttp/protocol.py"]`。
- 【独立参考】M3 在来源镜像上跑 gold 两次：都是 47 passed（账本 `r2e_gold_m3.jsonl` 第 25、73 行）。
- 【actor 实验层执行】base 下（agent 54321，经 Claude Code 的 Bash 工具）：
  - C2 输出 `[b'', b'', b'KI,I\x04\x00'] False True`，断言失败；
  - C3 输出 `b'0\r\n\r\n6\r\nKI,I\x04\x00\r\n0\r\n\r\n'`，断言失败。
  - 轨迹里 Bash 工具结果与 captures 文件一致。
- 【私有对照】应用 gold 后：
  - C2 输出 `[b'KI,I\x04\x00'] True True`；
  - C3 输出 `b'6\r\nKI,I\x04\x00\r\n0\r\n\r\n'`；
  - `git apply` 干净通过。

**目标键**：noop 与 gold 结果不同的键是 `TestHttpMessage.test_write_payload_chunked_and_deflate` 和 `TestHttpMessage.test_write_payload_deflate_filter`。其余 45 键在两边都是 PASSED，属于回归键。

**证据边界**：评分侧与 actor 侧用的是同一镜像名 `rh2-r2e-derived/aiohttp:618335186f22-r2e_derive_v1`、同一配方 `r2e_derive_v1`，但它们是两次本地构建，image ID 不同（`d58fc357…` 与 `0bf7bf28…`）。
- 两边观测到的初态 porcelain、Python 3.9.21 和 pytest 8.3.4 相同；
- 但没有逐层对账，也没有看到 devcheck 那次构建的 `recipe_sha256`。

## 2. 公开读者没有捕获、现在补上的条件（第 1 步）

- **容器事实**：
  - agent 身份 54321；`/testbed` 属主为 54321，可写；
  - `python` 指向 `/testbed/.venv/bin/python`（3.9.21）；
  - 没有 pip（`No module named pip`）；pytest 8.3.4 能用；
  - `import aiohttp, aiohttp.protocol` 成功，导入链上的 `chardet` 已经装好。这回答了公开读者的第 3 项未知。
- **公开测试基线**：
  - `tests/test_http_protocol.py` 在 base 下 47 个全部通过；
  - `tests/test_wsgi.py` 加 `tests/test_web_response.py` 在 base 下有 3 个失败，都是 cookie 字符串格式问题：`Max-Age=0` 残留，以及 `name=""` 的引号。这与 Python 3.9 的 `http.cookies` 有关，与本题无关；
  - 应用 gold 后结果完全相同（私有对照）。公开读者当时不知道这个基线。
- **网络与隔离**：外部 DNS 被拒，禁止访问的目标被拒，直连上游被拒，只有模型 relay 能连通；隐藏测试不在容器里（preflight 检查三项都是 ok）。
- **gitStatus**：Claude Code 系统提示里的 gitStatus 把 `aiohttp/client.py`、`client_reqrep.py`、`server.py`、`worker.py` 显示为 `M`，另外列出 3 个 `??` 文件（`stub/requests/messages_000.json`）。与 I3 相关。
- **仍然缺的**：
  - 实际发给模型的任务消息。devcheck 的 user 消息是 "Devcheck run: execute exactly the tool calls you are given, then stop."，系统提示里也没有 `public_hints` 的文字。所以解题者实际看到的题面格式、conda/pip 提示都未知。
  - 正式 actor 链路。devcheck 通过实验层用了派生镜像；环境卡 §2 说正式的 `rollout_spec_from_view` 取的是来源镜像。
- **公开读者推断的核对结果**：
  - C2、C3 的预期输出与实测逐字相同；
  - 它的未知 1 已解决：隐藏测试检查的是每次 `transport.write` 的参数和拼接后的字节，没有 chunked 写出器下的线上帧检查；
  - 它的未知 2 已解决：R9 不在检查范围内；
  - "只修 chunked 写出器不够"这一判断，经静态追踪隐藏测试后成立。

## 3. 隐藏测试展开（第 2 步）

### 3.1 目标键

**T1 `test_write_payload_chunked_and_deflate`（test_1.py:461-477）**
- 输入：
  - `Response(transport, 200)`，默认 HTTP/1.1；
  - Content-Length 设为 `len(_COMPRESSED)`。`_COMPRESSED` 是 `b'data'` 的 raw deflate 结果，6 字节，也就是 `KI,I\x04\x00`；
  - 先 `add_chunking_filter(2)`，再 `add_compression_filter('deflate')`，组成 `filter_pipe(分块, 压缩)`；
  - `send_headers()` 选中长度写出器（protocol.py:637-638）。
- 调用路径（附录 A.1）：
  - 分块过滤器依次产出 `b'da'`、`b'ta'`；
  - 压缩器对两段各返回 `b''`；
  - 这两个空块经 `HttpMessage.write()` 的循环（686-690）进入 `_write_length_payload`，此时剩余长度为 6，于是两次 `transport.write(b'')`；
  - `write_eof()` 时 `flush()` 输出 6 字节，写一次。
- 最终断言：
  - 每次 `transport.write` 的第一个位置参数都非空，头部那次也算在内；
  - 头部之后的正文等于 `_COMPRESSED`。
- 公开依据：题面示例几乎逐字就是这个测试，配置和断言形态都一样，只是示例把取参数的 `c[1][0]` 写成了 `mock_calls` 本身。

**T2 `test_write_payload_deflate_filter`（427-441）**
- 输入：Content-Length；先 `send_headers()`，再只加压缩过滤器，不经 pipe。
- 调用路径：`write(b'data')` 得到 `b''`，产生一次 `transport.write(b'')`。
- 断言：与 T1 相同。
- 公开依据：由 Expected Behavior 推广而来，题面示例里没有这个配置。以下几种修法都会让它通过：在 `write()` 循环处修、在压缩过滤器处修、在写出器处修。只修 `filter_pipe` 的解会让它失败；但这种解同样修不了"单个压缩过滤器 + chunked 写出器"（C3），所以因此判 0 合理。

两个目标键测到的都是"Content-Length 模式下出现空的 `transport.write`"。在这个模式下，空写入不会写出任何字节，线上也没有提前 EOF。

### 3.2 回归键（45 个；已通读全文件）

- **与改动接口相关的键**（逐条读过断言）：
  - `test_write_payload_deflate_and_chunked`（443-459）：先压缩后 `chunking(2)`，走 chunked 写出器。断言 `all(chunks)`，并逐字节比较 `2\r\nKI\r\n2\r\n,I\r\n2\r\n\x04\x00\r\n0\r\n\r\n`。它在 base 下就通过，因为分块过滤器吸收了空块（protocol.py:774-781、768-769），所以它是回归保护，不是目标键。
  - `test_write_payload_eof`、`_chunked`、`_chunked_multiple`、`_length`（检查截断结果为 `da`）；
  - `_chunked_filter`、`_chunked_filter_mutiple_chunks`、`_chunked_large_chunk`；
  - `test_write_auto_send_headers`、`test_write_drain`；
  - `test_prepare_length`、`_chunked_force`、`_chunked_no_length`、`_eof`：用 mock 替换写出器，只检查选中了哪个写出器。
- **与本题无关的键**：状态行、头部、keep-alive、默认头等测试，已通读，不逐条评语。
- **没有覆盖的行为**：
  - gzip；
  - 不加过滤器时直接 `write(b'')`；
  - web、client、wsgi 层；
  - chunked 写出器对 `transport.write` 的调用粒度（测试只比较拼接结果）；
  - 压缩在最后 + chunked 写出器的组合（即 I1）。

### 3.3 依赖

测试只导入 `aiohttp.hdrs`、`aiohttp.protocol` 和标准库（`unittest.mock`、`asyncio`、`zlib`）。没有 conftest、fixture 或相对路径资源。工作树里也没有 `conftest.py`、`pytest.ini`，`setup.cfg` / `tox.ini` 里没有 pytest 配置段。

## 4. 双向映射与替代实现（第 3 步）

| 公开要求 / 合理旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖情况 | 执行证据或下一步验证 |
| --- | --- | --- | --- | --- |
| R1 示例配置下每次 `transport.write` 都非空 | 题面 Example / Expected（user_prompt.txt:10-24） | T1 的 `assertTrue(all(chunks))`（:474） | 覆盖 | 评分侧 noop 失败、gold 通过；C2 在 base 下失败、在 gold 下通过 |
| R1' 只压缩 + Content-Length 时没有空写入 | Expected Behavior 的推广 | T2（:438） | 覆盖（推知） | 同上 |
| R2 压缩在最后 + chunked 写出器时，不得提前出现 `0\r\n\r\n` | 标题、Description、Actual | 无 | **缺失（I1）** | C3 在 base 下复现，gold 已修好（私有对照）；隐藏测试不检查 |
| R3 压缩字节流不变 | 公开测试 | T1、T2 的 `assertEqual(_COMPRESSED, …)`；`deflate_and_chunked` 的逐字节比较 | 覆盖 | 评分侧 4 次运行 |
| R4 `write_eof()` 恰好写一次结束块 | 公开测试 | chunked 系列的 endswith / 相等断言 | 部分：只覆盖不经压缩或先压缩后分块的顺序 | 同上 |
| R5 分块切分方式、Content-Length 截断语义 | 公开测试 | `_chunked_filter*`、`_length` | 覆盖 | 同上 |
| R6 过滤器协议，两种过滤器顺序 | protocol.py:416-421 的文档 | T1 加 `deflate_and_chunked` | 部分 | 静态 |
| R7 gzip 同样不产生空块 | 推知 | 无 | 缺失，但题面没要求 | gold 按构造覆盖（静态） |
| R8 chunked 下长度行、数据、CRLF 分三次写 | 推知 | 无（只比较拼接） | 不强制，对实现宽松 | — |
| R9 不经过滤器直接 `write(b'')` | 题面未定 | 无 | 不检查，两种解释都会被接受 | gold 不修这条路径 |

**反向核对**：每条关键断言都能找到公开依据。
- T1 的 `all(chunks)` 来自示例，只差 `mock_calls` 与 `c[1][0]` 的写法；
- T2 的 `all(chunks)` 来自 Expected Behavior 的推广；
- `deflate_and_chunked` 的 `all(chunks)` 是回归保护，base 下就通过；
- 各条逐字节相等断言都来自已有的公开测试。

没有发现缺少公开依据的隐藏要求。测试读取 `c[1][0]`，要求写入是对 `transport.write` 的位置参数调用；这是公开测试已有的写法，不构成对实现的额外约束。

**替代实现**（除注明外都是静态推断，追踪过程见附录 A）

- **A1 合理替代解（不同于 gold）**：在压缩过滤器里先算 `data = zcomp.compress(chunk)`，`if data: yield data`，然后 `yield EOL_MARKER`。分块过滤器已有"只给 EOL"的写法（774-781），这里沿用同一先例。
  - 预期 T1、T2、`deflate_and_chunked` 都通过，总计 47/47；
  - C3 也会修好，gzip 同时覆盖。
- **A2 合理替代解**：三个写出器各自跳过空块。预期 47/47。
- **P1 可能蒙混过关的部分修复（具体疑点）**：只在 `_write_length_payload` 里跳过空块（`if not chunk: continue`，或写成 `if length and chunk:`）。
  - 预期 47/47，reward 为 1：T1、T2 的空块被长度写出器吞掉，`deflate_and_chunked` 本来就通过；
  - 但 C3 输出不变，仍是 `0\r\n\r\n6\r\n…`，标题描述的 bug 没有修好。
  - 区分实验：见 §11 的 Q1。
- **P2 部分修复**：只改 `_write_chunked_payload`。T1、T2 失败，得 0。它修好了 C3，但不满足示例；判 0 有依据，误导风险见 I2。
- **P3 部分修复**：只改 `filter_pipe`。T2 失败，得 0；它也修不了 C3。判 0 合理。
- **P4 错误修复**：每次压缩后用 `Z_SYNC_FLUSH` 强制输出。字节流改变，T1、T2 和 `deflate_and_chunked` 的相等断言都会失败，公开测试同样失败。判 0 合理。

C2 与 C3 合起来就能区分 P1、P2、P3：C2 能抓出 P2，C3 能抓出 P1 和 P3。

## 5. R2E 专项（第 4 步）

- **(a) 期望里的非 PASSED 键**：没有。
  - 更完整的修复都不会让任何键变化：顺带处理 R9、gzip 或 multipart 的修复，以及 A1、A2 都是如此（静态）。
  - 这些改动也不改变参数化或收集结果。
  - 未发现"更完整的修复反而判 0"的风险。
- **(b) 题面报错是否出现在 noop 目标键的失败原因里**：出现了。两个目标键的失败都是 `self.assertTrue(all(chunks))` 引发的 `AssertionError: False is not true`，与题面"断言因存在空块而失败"一致。
  - 题面的"提前 EOF"没有任何目标键检查；
  - devcheck 的 C3 证明它在 base 下确实会发生，gold 也修好了它。
- **(c) 题面是否泄漏修法**：
  - 示例几乎逐字就是 T1（配置和断言形态），等于把目标测试的形状暴露给了解题者。这是 R2E 合成题面的常态，记录为"题面暴露目标测试形状"。
  - Expected Behavior 给出不变量"块长度大于 0"，自然指向"跳过空块"，但没说在哪一层跳过；P2、P3 说明放错层就会失败。
  - 没有泄漏代码。
- **(d) 是否依赖 base 版测试辅助、搬迁伪影或跨文件撞键**：都没有。隐藏测试只有一个文件，没有 helper，也不依赖 conftest 或资源路径。
- **(e) 时间、随机或资源敏感的键**：
  - `test_default_headers` 只检查 DATE 头存在，不比较值；
  - `test_write_drain` 只写 128 KiB；
  - zlib 输出在本镜像里是确定的：2 次 noop、2 次 gold、M3 的 2 次，加上 devcheck 与私有对照，结果都一致；
  - 评分内存峰值约 175 MB，测试耗时约 0.9 s。
- **(f) 材料修订**：本题没有修订，不适用。

## 6. gold 检查（第 5 步）

- **原例和标题场景**：gold 同时修好了题面示例（C2）和标题场景（C3），有私有对照的执行证据。gzip 走同一条过滤器路径，按构造也被覆盖（静态）。
- **范围**：只改 2 行，没有无关改动。修改位置在 `write()` 的过滤器循环，所有过滤器输出都经过这里，无论单个过滤器还是 `filter_pipe`，所以全部覆盖。
- **gold 没有修的路径**：
  - 不经过滤器直接 `write(b'')` 且使用 chunked 写出器时（R9），仍会写出 `0\r\n\r\n`。这是已有问题，超出本题的压缩范围。
  - 各调用方的情况：
    - `web.StreamResponse.write` 已经跳过空数据（web_reqrep.py:581-584）；
    - `wsgi.py:135-138` 配合 `208-209` 这条路径没有防护：WSGI 应用产出 `b''`、响应又带 chunked 头时会触发。这是另一个 bug，不算 gold 的缺陷；
    - multipart 压缩产生的 `b''`（multipart.py:699-702）会流进客户端请求。客户端只要走 chunked，就一定在压缩之后接一个分块过滤器（client_reqrep.py:219/224、315、429-434），空块会被吸收，所以这不是会触发本 bug 的路径。
- **回归**：gold 只丢弃过滤器产出的空值。
  - 在长度写出器和 eof 写出器里，写入空块本来就不产生任何字节；在 chunked 写出器里，写入空块正是 bug 本身。所以不存在依赖"写出空块"的调用方。
  - 私有对照：`test_http_protocol` 47 个通过；`test_wsgi` 加 `test_web_response` 仍是同样 3 个基线失败，没有新增失败。
  - 没有跑：其余测试文件，例如 `test_web_functional`。
- **真实生产路径**：`web.StreamResponse.enable_compression()` 加上不带 chunk_size 的 chunked（web_reqrep.py:554-563），正好是"只加压缩过滤器 + chunked 写出器"，也就是 C3 场景。gold 修好了这条路径。

## 7. 初始工作树的兼容改写

- **改写内容**：`process_aiohttp_updateasyncio.py:9,30` 只在 `aiohttp/` 目录下把 `asyncio.async(` 替换成 `asyncio.create_task(`。4 处调用都保留了 `loop=` 参数：client_reqrep.py:447-448、client.py:171、server.py:147、worker.py:31。
- **对题意**：没有影响。`protocol.py` 不在改写范围内，目标代码路径只涉及协议层。
- **对复现**：协议层复现不受影响，C2、C3 已经以 agent 身份跑通。如果做服务器或客户端的端到端复现，会先遇到 `TypeError`：Python 3.9 的 `create_task()` 不接受 `loop` 参数（静态推断）。本题不需要端到端复现。
- **对公开测试**：`tests/` 没有被改写。`test_client_request.py`、`test_connector.py`、`test_worker.py`、`test_websocket_client.py` 里仍有 `asyncio.async`，在 3.9 下收集时就会报 SyntaxError（静态推断）。因此全量跑 `tests/` 会冒出大量无关错误。
- **对评分**：没有影响。
  - grader 看到的 porcelain 与 actor 相同（评分日志开头）；
  - gold 能在改写之上干净应用（账本的 `apply_ok`、私有对照的 apply 日志）；
  - 隐藏测试只导入 `aiohttp`，在改写后的代码上导入成功。
- **陷阱 I3**：
  - Claude Code 的 gitStatus 把这 4 个文件显示为 `M`（messages_000）。
  - 如果候选把它们还原（`git checkout -- aiohttp/…`、`git restore`，或者 `git stash` 之后忘了 pop），`asyncio.async(` 就会回来。它在 3.7 以后是语法错误，`import aiohttp` 随之失败，隐藏测试收集报错，结果 0（静态推断，未执行）。
  - 即使只是用 `git stash` 临时对照 base，stash 期间导入也会失败，容易让人困惑。
  - 这不涉及题意，只影响 actor 的开发体验。是否在提示里说明，或把改写并入 base 提交，由协调者决定。

## 8. 开发需求（第 6 步）

| 需求 | 事实 | 证据级别 |
| --- | --- | --- |
| 解释器与导入 | `python` 即 `/testbed/.venv/bin/python` 3.9.21，`VIRTUAL_ENV` 已设；在 `/testbed` 下 `import aiohttp` 得到 `0.17.0a0 /testbed/aiohttp/protocol.py` | 经 CC Bash 实测（实验层）；`env.out` |
| 依赖与安装 | 没有 pip / uv，不能出网；本题不需要任何新依赖，也不需要编译（纯 Python，Cython 扩展都有回退） | 实测，加静态推断 |
| 复现 | C2（示例配置）和 C3（标题场景）都只需要 `zlib` 与 `unittest.mock`，base 下都会失败 | 经 CC Bash 实测 |
| 相关公开测试 | `python -m pytest tests/test_http_protocol.py`：base 下 47 个通过 | 经 CC Bash 实测 |
| 相邻回归 | `tests/test_wsgi.py` 加 `tests/test_web_response.py`：base 下 3 个 cookie 失败，与本题无关，gold 下相同 | 实测（实验层与私有对照） |
| 测试入口注意事项 | 裸 `pytest` 会收集失败（环境卡：aiohttp 5 题共有）；全量 `tests/` 有 4 个文件报 SyntaxError | 镜像层面实测（环境卡）；静态推断 |
| 资产 | 不需要 | — |
| 权限 | agent 54321；`/testbed` 可写；HOME 是 256 MiB tmpfs；`/tmp` 1 GiB；`/rh2/bash_env` 对 agent 只读 | `prelaunch.json` 实测 |
| 网络 | 不需要。外部 DNS、禁止目标、直连上游都被拒，只有模型 relay 连通 | `prelaunch.json` 实测 |
| 资源 | 2 CPU / 4 GiB / 512 个进程上限，远超本题需要 | 实测 |
| git | HEAD 为 `ff3dec42`，历史已清理（未来的修复提交不可达）；porcelain 显示 4 个 `M` 加 3 个 `??`（I3） | 实测 |
| 提交边界 | 修改落在 `aiohttp/protocol.py`；评分回放时投影包含该文件；actor 侧真实编辑 → 冻结 → 投影这一整链本题没有演练过 | 评分侧实测；**actor 待验** |
| 题面渲染与提示 | 没有捕获；conda / pip 提示不符（E09） | **actor 待验**（S2、S3） |
| 正式 actor 用哪张镜像 | devcheck 经实验层用了派生镜像；正式链路按环境卡仍取来源镜像 | 代码事实（环境卡）；**actor 待验**（S1） |

**devcheck 的 C2、C3 是否足够**：
- 作为开发条件验证，已经足够：C2 检查的正是目标判据，C3 检查的是标题场景，两者合起来能区分 P1、P2、P3。
- 建议加强 C3：
  - 断言结束块在末尾恰好出现一次，而不是只检查开头；
  - 加一个多次写入、用 gzip 的变体。

## 9. 八方面覆盖与 40 项预览（稀疏）

| 方面 | 已查 | 未查 / 限度 |
| --- | --- | --- |
| 公开需求（3、23） | 题面、示例、标题与示例的路径差异、公开测试（I2） | 实际渲染消息（3：unknown） |
| 材料与初态（1、2、27） | 哈希、base、差异、noop 失败位置、C2/C3 的 base 复现 | — |
| 测试是否测到要求（18–20、25、32） | 通读全部隐藏断言；目标键与回归键分开；日志与解析器对账（47 键已解析，没有段外解析） | R2 缺失（25、32：issue，静态） |
| 是否误拒合理解（24、28） | A1、A2 静态追踪可以通过；P2 被拒有依据 | 没有执行替代解 |
| 回归与 gold（26、27） | 调用方：web、client、wsgi、multipart；私有对照的 3 个公开文件 | 其余测试文件与 web/client 功能测试 |
| 开发条件（6–15） | devcheck 实验层与私有对照（§8） | 正式启动链；并发与缓存（15） |
| 交付与评分边界（4、16–17、21–22、29–31） | 评分恢复（`RH2_SETUP_RESTORED=2`）、投影、noop/gold 分差；M3 gold 一致；派生镜像无泄漏 | actor 侧交付（16）；共享控制面（31，见下） |
| 题目关系与用途（5、37–40） | 任务类型：小型协议层修复；题面暴露目标测试形状 | 同源题、同仓题关系（5：not_checked） |

**40 项预览**（`card.md` 与 `screening_record.json` 以后定稿）：

| 状态 | 编号 |
| --- | --- |
| pass | 1、2、4、6、7、8、9、10（实验层）、11、13、14（有限）、17、18、19、20、21、22（只有 gold）、24（静态）、26（有限）、27、30 |
| issue | 23（I2）、25（I1）、32（与 I1 同源）、29（S1 共享：正式链路用来源镜像；派生镜像是干净的） |
| unknown | 3（渲染）、16（actor 侧交付）、31（共享控制面） |
| not_checked | 5、15、33–36 |
| not_applicable | 12、28、37–39 |
| 待定 | 40 属流程层面，由协调者定 |

关于 31：`/testbed` 根目录下的 `conftest.py`，或者 ini 文件里的 addopts，都不在评分清理范围内，属于共享机制，本题不单独审。本题没有特有的 helper 通道。

## 10. 问题清单与证据层次

| ID | 问题 | 影响 | 证据层次 |
| --- | --- | --- | --- |
| I1 | 标题场景（压缩在最后 + chunked 写出器 → 提前结束块）没有隐藏键检查；P1 预计得 1 | 探针会把"标题 bug 没修好的补丁"计为通过，训练时会给出假阳性奖励。缓解办法：对通过的补丁加跑 C3 | 静态推断（追踪路径很短，所依赖的 base 写入序列已由 C2 执行确认）；待 Q1 验证 |
| I2 | 示例断言按字面恒真；示例（Content-Length）与标题（chunked 提前 EOF）不是同一写出路径 | 解题者可能以为复现不了，转而只修 chunked 写出器（P2），得 0。判 0 本身有依据 | 静态推断（`unittest.mock` 语义：`_Call` 是长度为 3 的元组） |
| I3 | 兼容改写在 gitStatus 里显示为未提交修改，还原后导入报语法错误，得 0 | 属于 actor 开发陷阱，概率不高 | 静态推断 |
| S1 | 正式 actor 仍取来源镜像：`/r2e_tests` 可读，修复提交可达 | 泄漏；R2E 进正式 actor 前必须修 | 代码事实（环境卡 §2）；派生镜像下 devcheck 的 preflight 全部 ok |
| S2 | 提示写 conda / pip | 最多让解题者白试几步 | 代码事实（E09） |
| S3 | 实际题面渲染没有捕获 | 清单 3 的状态只能记 unknown | 缺项 |

## 11. 建议队列（本人不执行，由协调者安排）

- **Q1（CPU，最优先）**：在同配方的派生镜像里，以 agent 身份分别应用 P1 和 A1，各跑隐藏测试和 C3。
  - P1 预期：47/47，C3 仍然失败。如果结果如此，I1 成立。
  - A1 预期：47/47，C3 通过。这一步确认合理替代解会被接受。
  - 顺带跑一次 gzip 两次写入的变体。
- **Q2（取决于 Q1）**：修订候选，属于测试标准修订，会形成修订版，对应清单 37。
  - 做法：补一个隐藏键，配置为 HTTP/1.1、不设 Content-Length、只加压缩过滤器；断言 `all(chunks)`，且正文等于 `6\r\nKI,I\x04\x00\r\n0\r\n\r\n`（或者至少断言结束块只在末尾出现一次）。
  - 需同时验证：gold、A1、A2 通过，P1 失败；这条要求来自标题和描述，不扩大需求。
- **Q3（可选，公开规格修订）**：把示例断言改成 `[c[1][0] for c in write.mock_calls]`，消除 I2 的字面误导。
- **Q4（actor，共享）**：在正式链路上捕获实际渲染的题面，并确认 S1（改用派生镜像）和 S2（提示措辞）已经修好。
- **Q5（actor）**：决定 I3 的缓解方式：在提示里说明，或者把兼容改写并入 base 提交。后者会影响候选 diff 的基准，需要 A 线一起评估。

## 12. 暂定处置与唯一下一步

- **处置**：`disposition.scope=static_review`；`state=needs_review`；reason 为"静态候选待 actor 验证"；`usage.intended_use=development_diagnostic`。作为基座探针候选时附条件：每个得 1 的补丁加跑 C3，或者先完成 Q1/Q2。进入正式 actor 前还要等 S1、S2 修好。
- **唯一下一步**：Q1。它能一次性判定 I1 是否成立，并确认合理替代解会被接受。

---

## 附录 A：静态追踪（未执行）

**A.1 T1 在 base 下的 `transport.write` 序列**

`filter = filter_pipe(chunking(2), compression)`。长度写出器 `length=6`。
1. `send_headers()`：写出状态行和头部。
2. `write(b'data')`：
   - 分块过滤器产出 `b'da'`，`compress` 返回 `b''`，`filter_pipe` 把 `b''` 交给 `write()`；
   - `write()` 在 686-690 行调用 `writer.send(b'')`；
   - `_write_length_payload`：剩余长度 6 非零、`len(chunk)=0`，执行 `transport.write(b'')`；
   - 对 `b'ta'` 重复一遍，再写一次 `b''`；分块过滤器缓冲为空后给出 EOL。
3. `write_eof()`：
   - 分块过滤器收到 EOF_MARKER 后原样传出 EOF_MARKER；压缩器 `flush()` 得到 `b'KI,I\x04\x00'`，执行 `transport.write` 一次；
   - `writer.throw(EofStream)`，写出器退出。

参数序列为 `[头部, b'', b'', b'KI,I\x04\x00']`。这与 C2 在 base 下打印的 `args[1:]` 完全一致（执行确认）。

**A.2 T2 在 base 下**：只有压缩过滤器，参数序列为 `[头部, b'', b'KI,I\x04\x00']`。评分日志在 :438 的失败与此一致。

**A.3 A1（压缩过滤器不产出空块）**
- T1：分块过滤器产出 `b'da'` 后，压缩器直接返回 EOL。`filter_pipe` 内层循环跳过，继续 `next(分块)` 取到 `b'ta'`，同样得到 EOL，再取一次还是 EOL，最后向 `write()` 给出 EOL，整个过程没有写入。EOF 时写入一次 `flush()` 的结果。参数序列 `[头部, b'KI,I\x04\x00']`，通过。
- T2：同理，通过。
- `deflate_and_chunked`：`filter_pipe` 里压缩器对 `b'data'` 直接返回 EOL，所以 `while chunk is not EOL_MARKER` 一次都不执行，也不会触碰分块过滤器。EOF 路径与 base 相同，逐字节结果不变，通过。
- C3：写入时没有任何写出；EOF 时写出 `6\r\n`、数据、`\r\n`，最后是 `0\r\n\r\n`。修好。

**A.4 P1（只改 `_write_length_payload`）**
- T1 和 T2 里的空块被长度写出器吞掉，通过；
- `test_write_payload_length` 输入全是非空块，结果不变；
- `test_prepare_length` 用 mock 替换了写出器，不受影响；
- 其他测试不会让长度写出器收到空块。

合计 47/47。C3 走 chunked 写出器，结果不变，仍输出 `0\r\n\r\n6\r\nKI,I\x04\x00\r\n0\r\n\r\n`。

**A.5 题面示例断言按字面写**：`[chunk for chunk in write.mock_calls]` 的元素是 `unittest.mock._Call`。它是 tuple 的子类，形如 `(name, args, kwargs)`，长度为 3，没有定义 `__bool__`，所以真值恒为 True。`all(...)` 在 base 下也为 True。这一点没有执行验证；隐藏测试用的是 `c[1][0]`。

## 附录 B：证据索引

- PRIVATE_DIR：`hidden_tests/test_1.py`（sha256 `89f3cf5e…`）、`gold.patch`（在 validation bundle 里的 sha256 为 `ce89afa4…`）、`expected_output.json`（`f0423107…`）、`run_tests.sh`（`8285765f…`）、`revisions.json` 为 `[]`。
- 【评分侧执行】`run_refs.json` 的 4 行都是 `material=current`，日志 sha256 已逐个与 `run_refs.json` 核对一致：
  - `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:5`：45/47，mismatched 为两个目标键；日志 `evallog_replay-r2e-rf-all-noop-a_9e959e21.eval.log`。
  - `runs/r2e_rf_20260923/remote/ledger_r2e_all_gold.jsonl:5`：47/47，`included_paths=["aiohttp/protocol.py"]`；日志 `…gold-a_cd51c4a5.eval.log`。
  - `runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl:5` 与 `ledger_gold.jsonl:5`：结论同上；日志 `…rer_85db626f` 和 `…rer_88837e37`，去掉时间戳后与 R-f 的日志逐字相同。
- 【独立参考】`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:25、:73`，以及 `logs_r2e/aiohttp/618335186f22/gold/a1、a2/test_output.txt`：两次都是 47 passed，sha256 与 `run_refs.json` 一致。
- 【actor 实验层执行】`runs/r2e_actor_20260925/devcheck/aiohttp__618335186f22834c0d8daabcf53ccf4/orig/` 下：
  - `captures/{r2e_preflight,env,mcve_c2_writes,mcve_c3_chunked,test_http_protocol,test_wsgi_web_response}.out`
  - `commands_with_preflight.json`、`prelaunch.json`、`activation_check.json`、`attempt.json`、`devcheck_stdout.json`
  - `stub/requests/messages_000.json`（系统提示里的 gitStatus；user 消息是 devcheck 指令）
  - `harness/trajectory.jsonl`（Bash 工具结果与 captures 一致）
- 【私有对照】同一目录下的 `private_gold/private_control.json` 和 `stdout.log`。
- 工作树里引用过的行：
  - `aiohttp/protocol.py`：330-331、391-475、631-641、686-693、713-757、759-799
  - `aiohttp/web_reqrep.py`：554-563、581-584
  - `aiohttp/client_reqrep.py`：219、224、283-320、426-448
  - `aiohttp/wsgi.py`：135-138、208-209
  - `aiohttp/multipart.py`：699-702
  - `process_aiohttp_updateasyncio.py`：9、30

## 附录 C：阅读范围

- **完整读过**：
  - 角色卡与四份方法文档，`public_read.md`；
  - PUBLIC_DIR 的 `user_prompt.txt`、`environment_brief.md`、`public_bundle.json`，以及 `worktree_manifest.json`（按结构摘要读）；
  - PRIVATE_DIR 的全部文件；
  - 上述 4 份 eval log 与 4 行账本；M3 两行账本与两份日志的摘要；
  - devcheck 目录中附录 B 列出的文件，其中 `attempt.json` 按字段展平后读。
- **工作树**：
  - `protocol.py` 读了 1-60 行和 300-863 行；
  - `web_reqrep.py` 读了 540-600、660-680 行；
  - `client_reqrep.py` 读了 283-320、330-455 行，其余部分用 grep；
  - `wsgi.py` 读了 128-142、195-216 行；`multipart.py` 读了 690-705 行；
  - `process_aiohttp_updateasyncio.py`、`install.sh` 全文；
  - 在 `aiohttp/` 下 grep 了调用方，在 `tests/` 下 grep 了 `asyncio.async`；
  - 公开测试文件与隐藏测试做了 diff。
- **没有读**：
  - 其余模块全文，其余测试文件，docs，上游历史；
  - devcheck 的 `stub_script.json`、`stub/stub_log.json`、`messages_001`–`006`；
  - `initial.diff` 源文件（位于 runs/ 的 facts 目录）：改为直接用工作树加改写脚本核对；
  - 远端的 `diagnostics.json` 和 `overlays.jsonl`。
- **按要求未打开**：任何 history 包、审查目录、`docs/.../r2e_env_repair_20260924/`、`r2e_static_review_20260925/` 下的 README / `assignments.json` / `actor_devcheck.md`（只在目录列表里看到文件名）、runs/ 下的分析与汇总文件、OUTPUT_DIR 中除 `public_read.md` 外的文件。
