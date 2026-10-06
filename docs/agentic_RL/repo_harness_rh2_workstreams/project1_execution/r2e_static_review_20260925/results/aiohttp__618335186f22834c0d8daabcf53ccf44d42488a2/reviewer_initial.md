# aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2：独立复核第一步（初判）

2026-09-25 · 独立复核者（静态审查，干净上下文）· 写于读主审产物、公开读者产物与历史引用之前。

路径均为仓库根下相对路径。`PUBLIC_DIR` = `runs/r2e_static_prep_20260924/v2/public/aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2`，`PRIVATE_DIR` 为 `v2/private/` 下的同名目录，`DEVCHECK` = `runs/r2e_actor_20260925/devcheck/aiohttp__618335186f22834c0d8daabcf53ccf4`。证据级别标记：【执行】指已有运行原件，【源码】指源码阅读，【推演】指静态推断且未执行。

## 0. 初判摘要

- **题目**：aiohttp 0.17.0a0，base `ff3dec42`。`HttpMessage.write()` 带 filter 时，filter 的每个产出都交给写出器（`aiohttp/protocol.py:686-690`）。raw deflate 处理小输入时，`zcomp.compress()` 返回 `b''`，写出器因此收到空块。gold 在 `aiohttp/protocol.py` 改 2 行：在 `write()` 的 filter 循环里加 `if chunk:`，跳过空块。
- **评分面**：47 个键的期望都是 PASSED。**目标键 2 个**，两次 noop 都只有这两个键不匹配：`TestHttpMessage.test_write_payload_deflate_filter` 与 `TestHttpMessage.test_write_payload_chunked_and_deflate`。其余 45 个是回归键：44 个与公开的 `tests/test_http_protocol.py` 同名且测试体相同；`test_write_payload_deflate_and_chunked` 只多一条 `all(chunks)`，而这条在 base 上已经成立。没有死键。
- **R2E 专项没有阻断项**：期望里没有非 PASSED 键；没有参数化；隐藏测试只导入 `aiohttp.hdrs` / `aiohttp.protocol`；一个文件、一个类、47 个方法名互不相同；没有材料修订。noop 目标键正好失败在新增的 `self.assertTrue(all(chunks))`（`test_1.py:438`、`:474`），与题面说的"部分块为空"一致。
- **问题 1：漏测（中）**【推演 + base/gold 执行】。标题说的是"chunked 响应提前 EOF"：没有 Content-Length（或调用了 `enable_chunked_encoding()`），走 chunked 写出器，只有 deflate、没有 chunking filter。这时 base 把 `0\r\n\r\n` 作为第一个块写出（DEVCHECK C3 实测），但**没有任何隐藏键走这条路径**：
  - 两个目标键都用 Content-Length 写出器；
  - 带 deflate 又走 chunked 写出器的只有 `deflate_and_chunked`。它的 chunking filter 排在压缩之后，会吞掉空输出，所以 base 上已经通过。

  结果是，只在 `_write_length_payload` 里跳过空块的部分修复（下称 P1）按推演能拿到 47/47，C3 却仍然提前结束。这条路径就是 web 层真实用法：`enable_compression()` 加上不带 `chunk_size` 的 `enable_chunked_encoding()`（`aiohttp/web_reqrep.py:554-563`）。
- **问题 2：题面示例缺陷（中低）**【源码 + 执行】。
  - 示例不能直接运行：`transport`、`write`、`compressed_data` 都没有定义。
  - 字面断言 `chunks = [chunk for chunk in write.mock_calls]; assert all(chunks)` **永远为真**。`mock_calls` 的元素是 `_Call`，它是 `tuple` 的子类，由 3 元组构造，没有覆盖 `__bool__` / `__len__`，所以在 base 上也不会失败。测试实际用 `c[1][0]` 取第一个位置参数。
  - 示例的配置（Content-Length + `add_chunking_filter(2)`）本身不会截断数据（DEVCHECK C2：`b''.join(...) == comp` 为 True），"premature EOF"只在 chunked 写出器下成立。

  因此题面里的"chunk"有两种读法：HTTP chunked 编码的块，或每一次 `transport.write`。测试采用后者。只修 `_write_chunked_payload` 的路线（下称 P2）会被两个目标键判 0。这个拒绝能从示例意图找到依据，但示例的字面验证信号是坏的：解题者照抄示例，会误以为已经修好。
- **开发条件**：
  - 单元级复现和公开测试，在真实 Claude Code 2.1.205 启动链（agent/54321、派生镜像）下都能跑。
  - 端到端的 server/client 复现，会被来源镜像的兼容改写挡住：`asyncio.create_task(..., loop=...)`【推演】。
  - 相邻公开测试有 3 个与本题无关的 cookie 失败。
  - 实际任务消息和 R2E 提示措辞没有被 devcheck 捕获（actor 待验）。
- **初判倾向**：可作 `development_diagnostic` 的静态候选，state 保留 needs_review，原因有两条：静态候选待 actor 验证；一条漏测待 CPU 确认。判读通过补丁时应额外核 C3。是否以标题的原需求为依据补一条断言，属于修订建议，由协调者/用户决定。
- **唯一最值得先做的下一步**：CPU 定点对照。让 P1 经 RH2 评分，并在同一补丁上跑 C3；同批加 P2 作误拒对照。

## 1. 实际读取范围与暴露

**读过：**
- **角色卡与方法文档**：
  - `roles/reviewer_r2e.md`，全文。
  - `roles/investigator_r2e.md`：Read 工具显示了全文（34 行），口径只采用"R2E 的评分口径"与"材料"两节。
  - `quality_review_protocol_20260920.md`、`r2e_environment_card.md`、`record_template.md`，全文。
  - 未读 40 项清单。
- **公开包**：
  - `user_prompt.txt`、`environment_brief.md`、`public_bundle.json`。
  - `worktree_manifest.json` 的 export / initial_diff / untracked 段。
  - worktree 中的源码：`aiohttp/protocol.py`（1–60、360–863 行）、`aiohttp/web_reqrep.py`（405–604）、`aiohttp/client_reqrep.py`（405–494）；以及 `process_aiohttp_updateasyncio.py`、`install.sh`、`run_tests.sh`。
  - `tests/test_http_protocol.py`：与隐藏测试逐行 `diff`，读全。
  - grep：`aiohttp/` 下的 filter 调用者与 `asyncio.create_task(`；`tests/` 下的 `asyncio.async(`；`CHANGES.txt` 头部；`HISTORY.rst` 与 docs 里的相关词；`setup.cfg` / `tox.ini` 的段名。
- **私有包**：
  - 读了 `hidden_tests/test_1.py`（全文）、`hidden_tests/__init__.py`（空）、`expected_output.json`、`gold.patch`、`run_tests.sh`、`revisions.json`（内容为 `[]`）、`run_refs.json`、`grading_bundle.json`、`validation_bundle.json`。
  - 本地 sha256 与 bundle / 日志里的记录一致：test_1.py `89f3cf5e…`、expected `f0423107…`、gold `ce89afa4…`、run_tests.sh `8285765f…`。
- **运行原件**（`run_refs.json` 全部 4 条 current 行，加 2 条 independent_reference）：
  - 4 个账本各自的第 5 行，全字段。
  - 4 份 `.eval.log`：R-f 的 noop / gold 读全文；环境轮复跑的两份与之做了去时间戳 diff，逐行相同。
  - 6 份日志的 sha256 全部与 `run_refs.json` 相符。
  - M3 的 `test_output.txt` a1 / a2：读头尾，并互相 diff；M3 账本第 25、73 行的前 900 字符。
- **DEVCHECK**：
  - `orig/` 下：`commands_with_preflight.json`、`stub_script.json`；`captures/*.out` 共 6 份（长输出看头尾与汇总）；`activation_check.json`、`devcheck_stdout.json`、`devcheck_stderr.log`、`prelaunch.json`、`post_run_facts_root.txt`、`bringup_artifacts/cc_version_observed.json`、`attempt.json`。
  - `stub/stub_log.json` 前 1500 字符；`stub/requests/messages_000.json` 的 system 与首条 user 消息。
  - `private_gold/private_control.json`、`private_gold/stdout.log`。
- **标准库**：本机 uv 管理的 CPython 3.12.13 中，`unittest/mock.py` 的 `class _Call(tuple)`（约 2518–2566 行）。容器是 3.9.21，未逐行核对 3.9 源码。

**未读：**
- 按指示不读的：`OUTPUT_DIR` 的其它文件、任何 `history/`、`docs/.../r2e_env_repair_20260924/`、任何 review 目录、本批 README / `assignments.json` / `actor_devcheck.md` / `grader_candidates.md`、`runs/` 下的分析与汇总。
- manifest 引用的 M3 `initial.diff` 原件没有打开。改写范围用 manifest 文件表、日志里的 porcelain 输出与 worktree 源码核对。
- DEVCHECK 的 `harness/trajectory.jsonl` 与 `messages_001–006.json`，只看了 `attempt.json` 里的摘要。
- 其它题。

**暴露**：DEVCHECK 命令的 `purpose` 字段写着"公开读者 C2 / C3 加断言"，所以我知道公开读者提过两条自检：Content-Length 写出器逐次写入、无 Content-Length 时的提前 EOF。公开读者正文没有读。问题 1 的结论来自我对隐藏键和源码的逐键推演；C3 的实测只用作 base / gold 的行为证据。

**执行**：只用 shell 列目录、读文件、diff、sha256，用 python3 解析 JSON；没有运行项目代码或容器。

## 2. 八方面

| 方面（协议编号） | 看了什么 | 初判 | 未查 / 未知 |
|---|---|---|---|
| 公开需求（3、23） | 题面、公开提示、`protocol.py` 的 filter 协议 docstring（391–436）、公开基础测试 | 目标清楚：带 deflate 时不写出空块。缺陷见问题 2：示例不能直接运行，字面断言永远为真；标题与描述（chunked 响应、提前 EOF）和示例配置（Content-Length + chunking filter，不截断）不一致。`public_hints` 的 conda / pip / "测试文件会被重置"对 R2E 不成立，环境说明已纠正 | 真实 actor 收到的任务消息与 R2E 提示措辞（devcheck 首条 user 消息是固定的"Devcheck run"） |
| 材料与初始问题（1、2、27） | base / HEAD、兼容改写范围、noop 日志、DEVCHECK C2 / C3 的 base 输出 | 材料对应：隐藏测试 = base 公开测试 + 3 条 `all(chunks)`。M3 `gold_meta` 把修复提交的改动记为 `aiohttp/protocol.py`（gold）与 `tests/test_http_protocol.py`（测试，已排除）。兼容改写只动 client / client_reqrep / server / worker 四个文件，不碰 `protocol.py`。初始问题在 base 上成立：C2 两次空写入，C3 首块为 `0\r\n\r\n`，都在 actor 链的 agent 身份下【执行】 | 没有独立核对 `ff3dec42` 是否是 `61833518` 的父提交。间接证据：gold 干净应用，测试差异最小 |
| 测试是否测到要求（18–20、25、32） | 三个带新断言的测试逐步推演（§4），以及 44 个不变键的范围 | 题面原例 = `test_write_payload_chunked_and_deflate`，已覆盖。deflate-only + Content-Length 由 `test_write_payload_deflate_filter` 覆盖，依据来自标题"Deflate Compression Sends Empty Chunks"，不在示例里。**标题说的 chunked 写出器提前 EOF 没有覆盖**（问题 1） | gzip、多次 write、无 filter 的 `write(b'')` 都没测；最后一项不在题意内 |
| 是否误拒合理解（24、28） | 六种替代实现的推演（§5） | 常见的正确路线都能通过：改在 gold 的位置、压缩 filter 不产出空块、所有写出器都跳过空块。只修 chunked 写出器（P2）会被判 0：拒绝有示例意图作依据，但与标题的读法冲突（问题 2）。精确字节断言都已在公开基础测试里，不是隐藏新增的要求 | P2 的实际得分未执行 |
| 回归与 gold 完整性（26、27） | gold diff；filter 调用者（`web_reqrep.py`、`client_reqrep.py`、`wsgi.py`、`test_utils.py`）；私有 gold 对照 | gold 修好了原例和 C3：私有对照里 C2 为 `[b'KI,I\x04\x00'] True True`，C3 为 `b'6\r\nKI,I\x04\x00\r\n0\r\n\r\n'`。没有无关改动。相邻公开测试在 gold 前后都是 68 过、3 个无关 cookie 失败【执行】 | 无 filter 时，显式 `write(b'')` 在 chunked 写出器下仍写出 `0\r\n\r\n`。这在题意之外，gold 不修，也没有键会惩罚更完整的修复 |
| agent 开发条件（6–15） | 环境说明、环境卡、DEVCHECK 全部原件 | 单元级可用；端到端受兼容改写影响（§8） | 真实模型能否解出、token / 时间成本（清单 33–36），不在静态审查范围 |
| 交付与评分边界（4、16–17、21–22、29–31） | 评分口径、账本 projection、preflight | 修复点在 `aiohttp/protocol.py`，gold 的 projection 只含这个文件。隐藏测试不依赖仓库测试辅助，候选改仓库测试不影响评分。preflight 三项 ok：隐藏测试不可读，git 里没有修复提交。`CHANGES.txt` 的 0.17.0a0 段为空，没有答案泄漏 | 候选在 `/testbed` 新建 conftest.py 或 pytest ini 段、改 `.venv` 不会被清掉。这是 R2E 共性，不是本题特有，未逐题验证 |
| 题目关系与用途（5、29–30、37–40） | 只看了本题 | 单文件 2 行的小修复。题面给出了要满足的性质（块长 > 0），没给修改位置 | 与本仓其它 R2E aiohttp 题的关系未查；上游修复提交公开可查，但容器没有外网 |

## 3. 需求与测试映射

| 公开要求 / 合理旧行为 | 公开依据 | 键 / 决定性断言 | 覆盖 | 执行证据 / 下一步验证 |
|---|---|---|---|---|
| 示例配置下不写出空块：Content-Length，先 `add_chunking_filter(2)` 后 `add_compression_filter('deflate')` | 题面示例 | `test_write_payload_chunked_and_deflate`：`assertTrue(all(chunks))`（474），正文 == `_COMPRESSED`（476–477） | 覆盖（目标键） | noop 失败于 474，gold 通过；C2 在 base 上有两次 `b''`，gold 下没有空写入 |
| 只有 deflate filter（Content-Length）时不写出空块 | 标题；不在示例里 | `test_write_payload_deflate_filter`：438，440–441 | 覆盖（目标键），依据偏间接 | noop 失败于 438，gold 通过 |
| chunked 写出器 + deflate、没有 chunking filter 时，不得提前写出终止块 | 标题"in Chunked Responses, Causing Premature EOF"、描述 | 无 | **缺失** | C3：base 首块为 `0\r\n\r\n`，gold 已修；P1 待测 |
| deflate 之后 chunking(2)、走 chunked 写出器：输出字节不变且没有空块 | 旧行为（字节断言已在公开基础测试中） | `test_write_payload_deflate_and_chunked`：455，457–459 | 覆盖（回归键，base 已通过） | noop / gold 均 PASSED |
| chunking filter 的切块与多次写入；chunked / length / eof 三种写出器；头部与连接语义 | 旧行为（公开基础测试中的 44 个同体测试） | 其余 44 键 | 覆盖（回归键） | noop / gold 均 PASSED；actor 链下公开文件 47 个全过 |

反查：三条新断言都能从题面"所有块长度 > 0"找到依据。精确字节（`_COMPRESSED`、`b'2\r\nKI\r\n2\r\n,I\r\n2\r\n\x04\x00\r\n0\r\n\r\n'`）在公开基础测试里已经存在。

## 4. 关键路径推演（base）

`write()`（`protocol.py:686-690`）先执行 `chunk = self.filter.send(chunk)`，只要结果不是 `EOF_MARKER` / `EOL_MARKER`，就 `self.writer.send(chunk)`。压缩 filter 对 `b'data'` 先 `yield zcomp.compress(chunk)`（798），raw deflate 下得到 `b''`；EOF 时 `yield zcomp.flush()`（794），得到 6 字节 `KI,I\x04\x00`。

- **`test_write_payload_deflate_filter`**：有 Content-Length，走 `_write_length_payload`。收到 `b''` 后，`if length:` 为真，`l = 0`，执行 `transport.write(b'')`（738–743）。chunks 里有 `b''`，438 失败。
- **`test_write_payload_chunked_and_deflate`**：filter 是 `filter_pipe(chunking, compression)`。chunking 先切出 `b'da'`、`b'ta'`，各自压缩成 `b''`，pipe 原样 yield（463–465），于是有两次 `transport.write(b'')`，474 失败。这与 C2 在 base 上的输出 `[b'', b'', b'KI,I\x04\x00']` 一致。
- **`test_write_payload_deflate_and_chunked`**：filter 是 `filter_pipe(compression, chunking)`。压缩产出的 `b''` 送进 chunking，`buf.extend(b'')` 后不满 2 字节，直接 `yield EOL_MARKER`（774–781），空块被吞掉。所以 base 上已通过，不是目标键。
- **C3（没有对应的键）**：没有 Content-Length、HTTP/1.1，走 `_write_chunked_payload`（631–635）。`b''` 让它依次写出 `b'0\r\n'`、`b''`、`b'\r\n'`（723–727），拼起来就是终止块，客户端在压缩数据到达之前就读到了结束。DEVCHECK C3 在 base 上实测为 `b'0\r\n\r\n6\r\nKI,I\x04\x00\r\n0\r\n\r\n'`。

gold 的 `if chunk:` 包住 `self.writer.send(chunk)`，对三种写出器同时生效，所以两个目标键和 C3 都修好了。

## 5. 替代实现与可区分反例（均为【推演】）

| 候选 | 改动 | 隐藏键推演 | 题意 | 判断 |
|---|---|---|---|---|
| A | 压缩 filter 只在 `compress()` 结果非空时 yield | 47/47 | C2、C3 都修好 | 合理替代，接受 |
| B | 三个写出器都跳过空块，或统一走一个跳过空块的写函数 | 47/47 | 修好 | 接受 |
| **P1** | 只在 `_write_length_payload` 跳过空块，例如 `if length and chunk:` | 47/47：两个目标键都走这个写出器；`test_write_payload_length`、`test_prepare_length`（写出器被 mock）不受影响 | **C3 仍然提前结束** | **漏测**：部分修复拿满分。照示例调试时，空写入正出自这里（741 行），就地补丁很自然 |
| **P2** | 只在 `_write_chunked_payload` 跳过空块 | 45/47：两个目标键仍有 `b''` 写入 | C3 修好，但示例配置下仍有空写入 | 拒绝有示例意图作依据；但照字面跑示例，在 base 和 P2 上都"通过"，解题者会误以为已修好（问题 2） |
| P3 | 只在 `filter_pipe` 跳过空块 | `deflate_filter` 失败 | 只有 deflate 时 C3 仍坏 | 拒绝正确 |
| Z | 每次 write 后调用 `Z_SYNC_FLUSH` | 精确字节键失败 | 线上格式改变 | 精确字节在公开测试中可见，不算隐藏误拒 |

## 6. R2E 专项

- **(a) 非 PASSED 期望键**：47 键全为 PASSED，没有 FAILED / ERROR 键，也没有参数化。更完整的修复（同时处理无 filter 的 `write(b'')`，或让所有写出器跳过空块）按推演不会翻转任何键。
- **(b) 题面报错是否出现在 noop 目标键**：R-f 与环境轮复跑的两次 noop，都只在 `test_1.py:438`、`:474` 失败，报 `AssertionError: False is not true`（R-f noop 日志 34–73 行）。注意这里用的是测试里的 `c[1][0]` 写法；题面的字面写法不会失败。
- **(c) 题面是否泄漏修法**：期望行为只陈述"块长 > 0"，没给修改位置。算轻度提示，不算泄漏补丁。
- **(d) 测试支撑、搬迁伪影与撞键**：隐藏测试只执行 `from aiohttp import hdrs, protocol`，不依赖仓库测试辅助、conftest 或相对路径资源。一个文件一个类，47 个方法名互不相同，没有撞键。日志没有 configfile 行，仓库 `setup.cfg` / `tox.ini` 里也没有 pytest 段。
- **(e) 时间、随机与资源敏感**：`DATE` 头只检查存在；`test_write_drain` 写 128 KiB；没有随机因素。两处硬编码的压缩字节依赖镜像里 zlib 的输出，镜像固定时稳定；`_COMPRESSED` 在类定义时现算，本身自洽。
- **(f) 修订**：没有材料修订（`revisions.json` 为 `[]`，`current_material.material_revisions` 为空）。初始工作树的兼容改写来自来源镜像，不属于修订，也不碰 `protocol.py`。

## 7. gold 检查

- **原例是否修到**：私有 gold 对照用的是同一张派生镜像 `0bf7bf28…` 的一次性容器，身份是 **root**（`private_control.json` 的 env 行显示 `uid=0`）。对照中 C2 没有空写入，C3 不再提前结束【执行】。
- **有无无关改动**：没有，gold 只改 `write()` 的 filter 分支。无 filter 分支保持原样：chunked 写出器收到显式的 `write(b'')`，仍会写出终止块。这在题意之外。web 层的 `StreamResponse.write` 已有 `if data:`（`web_reqrep.py:581`）；`wsgi` 路径会不会传空块，未查。
- **相邻公开测试**：gold 前后，`tests/test_wsgi.py tests/test_web_response.py` 都是 68 过、3 个 cookie 失败；`tests/test_http_protocol.py` 47 个全过【执行】。

## 8. 开发需求（本题）

| 项 | 事实 | 证据级别 |
|---|---|---|
| 解释器与导入 | `/testbed/.venv/bin/python`（3.9.21）；在 `/testbed` 下用 `python -c` 导入到的是 `/testbed/aiohttp/protocol.py` | 真实 actor 链实测（DEVCHECK env） |
| 测试入口 | `python -m pytest tests/test_http_protocol.py` 47 个全过；裸 `pytest` 收集会失败（环境说明） | 前者实测；后者为镜像层面实测（环境卡） |
| 依赖与网络 | 没有 pip，没有外网。修复只用到标准库 zlib / unittest.mock，不需要装包 | 实测 |
| 权限 | agent 54321 可写 `/testbed`、`/tmp`、home；`/rh2/bash_env` 拒写，这是设计如此 | 实测（prelaunch / env） |
| 复现路线 | 单元级：用 `protocol.Response` + `Mock` 的 C2 / C3 脚本能跑，并在 base 上失败 | 实测 |
| 端到端复现 | 兼容改写把 `asyncio.async(` 换成了 `asyncio.create_task(`，但保留了 `loop=` 参数（`server.py:147`、`client_reqrep.py:447`、`client.py:171`、`worker.py:31`）。3.9 的 `create_task` 不接受 `loop`，所以起真实的 server / client 会报 TypeError | 【推演】，未执行 |
| 相邻测试噪声 | `tests/test_web_response.py` 有 3 个 cookie 失败，与本题无关。`tests/` 下仍有写着 `asyncio.async(` 的文件（如 `test_connector.py:612`），在 3.9 上应当无法收集 | 前者实测；后者【推演】 |
| 提交边界 | 改 `aiohttp/protocol.py` 即可；改仓库测试既不计分，也不影响评分 | 评分口径 + 账本 projection |
| 仍待验 | ① 实际任务消息与 R2E 提示措辞：devcheck 首条 user 消息是固定的"Devcheck run"。② 镜像身份：devcheck 与私有对照用的 `0bf7bf28…`，和评分运行用的 `d58fc357…`，是同一配方（`r2e_derive_v1`、同一来源镜像 digest）的两次构建；初态 HEAD 与 porcelain 输出一致，但内容是否等价未核 | actor 待验 / 未知 |

## 9. 运行证据核对

| 行 | 条件 | 结果 | 核对 |
|---|---|---|---|
| `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:5` | 派生镜像 `d58fc357…`，配方 `r2e_derive_v1`，评分用户 54322，2 CPU / 4 GiB，网络 deny_all | 45/47，不匹配的正是两个目标键；rc=1 | 日志 sha256 相符；`RH2_SETUP_HIDDEN_TESTS_TREE=7570cfed…` 与 current 材料一致 |
| `runs/r2e_rf_20260923/remote/ledger_r2e_all_gold.jsonl:5` | 同上；gold `ce89afa4…` 用 git_apply 应用 | 47/47，reward 1 | 相符 |
| `runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl:5`、`ledger_gold.jsonl:5` | 同一镜像 ID，预算不同 | 与 R-f 相同 | 两份日志去时间戳后与 R-f 逐行相同 |
| M3 `r2e_gold_m3.jsonl:25`、`:73` | 来源镜像，独立 runner | gold 两次均 47 过 | 仅作参考 |
| DEVCHECK `orig/` | 正式启动链 + Claude Code 2.1.205 + 桩端点，agent 54321，镜像 `0bf7bf28…` | preflight 三项 ok；C2 / C3 按预期失败 | 是开发条件证据，不是评分 |
| DEVCHECK `private_gold/` | 同一镜像，一次性容器，root 身份，应用 gold | C2 / C3 通过 | gold 行为证据（root 身份） |

## 10. 疑点、未知与建议队列

1. **（优先）P1 漏测对照**：在 CPU 上让 P1（只在 `_write_length_payload` 跳过空块）经 RH2 评分，预期 reward 1；同一补丁再跑 C3，预期正文仍以 `0\r\n\r\n` 开头。如果确认，可以考虑以标题的原需求为依据补一条断言：没有 chunking filter、走 chunked 写出器、只有 deflate 时，`all(chunks)` 成立，且正文不以终止块开头。按私有对照，gold 应能通过。这是建议，未决定，需用户批准；修订前还要同时核 A / B 类替代解。
2. **P2 误拒对照**：同批跑 P2，预期 45/47，失败在两个目标键上，用来量化"照题面字面验证，误以为已修好"的风险。要不要修题面示例（补全定义、改用 `c[1][0]`）属于公开规格修订，另行决定。
3. **实际任务消息与 R2E 提示**：actor 待验。
4. **两次镜像构建是否等价**：未知。如果要把 devcheck 证据和评分证据合并引用，先核对配方 sha 或层 diff。
5. **与其它 aiohttp 题的关系**：未查。
