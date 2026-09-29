# aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2：独立复核第二步

2026-09-25 · 独立复核者。我的封存初判是 `reviewer_initial.md`，本文不改它。路径均为仓库根下相对路径。本次没有运行项目代码或容器，也没有修改任何原件。

证据标签：
- 【执行】已有运行原件。
- 【合同】读了生产代码或契约定义，没有运行。
- 【推演】静态推断。

## 0. 结论摘要

- **总体意见**：同意主审的处置：`development_diagnostic`，`needs_review`，作为附条件的探针候选。主审对材料、目标键、R2E 专项、gold 与环境层的核对，和我的独立初判逐项一致；公开读者没有看过答案，也独立得出了同样的两处题面问题。
- **I1（漏测）已被执行证据确认，需要改记**：
  - 协调者的 AP1 就是我初判里的 P1、主审的 P1：只在 `_write_length_payload` 里跳过空块。它的 RH2 reward 为 1（47/47），但 C3 仍以 `0\r\n\r\n` 开头【执行】。
  - `screening_record.json` 里 I1 的证据级别应从"静态推断"改为"当前 CPU 执行"，status 从 `open` 改为 confirmed。
  - `disposition.reason` / `next_step` 和 `card.md` §6 里"已安排 P1 与 A1 的真实评分"已经过时：实际跑的是 AP1 和 AP2，A1 没有跑。
- **I2（题面误导）同意**：示例的字面断言恒真（静态，未执行）；示例配置（Content-Length）与标题（chunked 写出器下提前 EOF）不是同一条路径。只修 chunked 写出器的补丁（P2）判 0，有公开依据。
- **I3（还原兼容改写会得 0）同意，但要补一处精确化**：机制得到契约支持，但只有 `client.py` 和 `client_reqrep.py` 在 `import aiohttp` 的导入链上；只还原 `server.py` 或 `worker.py` 不影响隐藏测试（§3 第 4 行）。这是我初判漏掉的一条。
- **修订建议 Q2 没有扩大原需求**：标题和描述都明说了 chunked 响应提前 EOF，gold 与 AP2 已经满足。我建议断言用语义口径，或至少与精确字节并列（§4.3）。是否修订是 T0 决定，由用户拍板；修订会让本题与上游 R2E 的判分口径不再一致。
- **建议给探针条件补三条**（§4.4）：
  1. C3 用语义检查；
  2. 原始 reward 与经 C3 校正后的结果分开报告；
  3. 得 0 且日志显示 `asyncio.async(` 语法错误时，归因为 I3，而不是模型能力。

  另外，训练用途须以 I1 解决为前提。
- **最小后续实验**：
  - 如果用户批准 Q2：按修订版对 noop / gold / AP1 / AP2 各跑 2 次。预期 reward 依次为 0 / 1 / 0 / 1，原 47 键不变，新键在 gold 与 AP2 下为 PASSED、在 AP1 与 noop 下为 FAILED。
  - 如果不批准：不需要新实验。把 C3 语义检查固定为探针判读步骤即可，已有的 gold / AP1 / AP2 的 C3 结果就是它的正反对照。

## 1. 本步读取范围

- **本题产物**（全文）：`public_read.md`、`analysis_before_history.md`、`old_findings_delta.md`、`card.md`、`screening_record.json`。
- **历史引用**（`history/.../refs.json` 共 8 项）：
  - 全文：`findings.md`、历史 `screening_record.json`、`repros/aiohttp__6183….py`；
  - 按字段摘要：`facts.json`；
  - `known_issues.json`：只看本题所属的 4 个族；
  - `decisions.md`：只看开头几行与 E06 / E09 / E10；
  - `results_20260924.md`：只看本题那一行；
  - `packages/p1/README.md`：只看与本题有关的行（grep）。
- **新执行证据**（`runs/r2e_actor_20260925/grader/`）：
  - `ledger_aio_{gold,AP1,AP2}.jsonl` 全字段；
  - 3 份 `eval_logs/evallog_replay-*-aioh_*.eval.log`：setup 行与结果行，并核对 sha256；
  - 两份 `cands/aiohttp_6183_*.patch`；
  - `run_grader_aiohttp.sh`；
  - `aiohttp_c2c3/{gold,AP1,AP2}.{json,log}`。
- **为核对主张而打开的原件**：
  - `runs/env_overnight_20260916/M3/facts/618335186f22/facts/initial.diff`（sha256 `46bd9947…`，与工作树清单一致）；
  - `runs/r2e_rf_20260923/remote/prepared_r2e/prompts.jsonl:5`；
  - posthoc2 / posthoc3 的 `dev_probe.json`（只 grep 根因行）；
  - `rh2/src/repoharness2/grading/manager.py:360-400`；
  - `rh2/src/repoharness2/contracts/frozen_patch.py:97-140`；
  - 工作树中的 `aiohttp/__init__.py`、`aiohttp/client.py` 与 `aiohttp/connector.py` 的导入行、`aiohttp/client_reqrep.py:200-324`、`Makefile`。
- **未读**：
  - 批次协调文件：README、assignments.json、actor_devcheck.md、grader_candidates.md；
  - `runs/r2e_rf_20260923/reconcile_all/reconcile.json`：只用了 `facts.json` 里的 reconcile 摘要；
  - 其它题的 grader 证据。

## 2. 新执行证据核对（AP1 / AP2 / gold）

| 候选 | 改动 | 账本 | 结果 | C2 / C3（一次性私有容器） |
|---|---|---|---|---|
| gold | `write()` 的过滤器循环里加 `if chunk:` | `ledger_aio_gold.jsonl:1`；日志 `…1962eb69d9c1-aioh_e96221bf`，sha256 `bdb5caf5…` 与账本一致 | 47/47，reward 1 | C2 `[b'KI,I\x04\x00'] True True`；C3 `b'6\r\nKI,I\x04\x00\r\n0\r\n\r\n'` |
| AP1 | 只在 `_write_length_payload` 的 `except … break` 之后加 `if not chunk: continue`（patch sha256 `62fb5c2c…`） | `ledger_aio_AP1.jsonl:1`；日志 `…07cba56b766f-aioh_61773c65`，`ce8fd041…` 一致 | **47/47，reward 1** | C2 通过；**C3 rc=1，`b'0\r\n\r\n6\r\nKI,I\x04\x00\r\n0\r\n\r\n'`，报 `AssertionError: premature terminating chunk`** |
| AP2 | chunked 与 length 两个写出器各加 `if not chunk: continue`，**没有改 `_write_eof_payload`**（`0548e104…`） | `ledger_aio_AP2.jsonl:1`；日志 `…32d05cc85433-aioh_569d50ec`，`c961cc35…` 一致 | 47/47，reward 1 | C2、C3 都通过 |

证据条件的核对：
- **材料**：三份日志的 `RH2_SETUP_HIDDEN_TESTS_TREE=7570cfed…` 与 `RH2_SETUP_ENTRY_SHA256=8285765f…` 都是当前材料。
- **评分条件**：评分用户 54322，2 CPU / 4 GiB，`grader_version` 与 `scripts_digest` `60c7a8fe…` 都与 R-f 相同。
- **应用基准**：两个候选 patch 的 `index 4309496…` 与 gold 的 `43094961` 是同一个 base blob。
- **镜像**：用的是 `0bf7bf28…`，经 `derived8` 覆盖表，也就是 devcheck 那次构建。账本记录的 `overlay.recipe_sha256` 为 `0da821a1…`，与 R-f / 复跑评分用的 `d58fc357…` 的配方 sha 相同。我初判第 10 条"两次构建是否等价未知"因此缩小为"配方与评分脚本相同，逐层内容未对账"。
- **次数**：每个候选只跑 1 次。noop / gold 此前已在两次构建上共跑 6 次（R-f 与复跑各 1 次 noop、1 次 gold，本批 gold 1 次，外加 M3）且结果一致，单次足够。
- **C2 / C3 的运行身份**：这批输出里没有记录运行身份（devcheck 私有对照是 root）。C2 / C3 是纯计算，结果与身份无关。
- **AP2 与主审 A2 的差别**：AP2 没改 eof 写出器，但隐藏测试不会让 eof 写出器在压缩下收到空块，所以对评分等价。
- **没有跑的候选**：A1（在压缩过滤器处修）和 P2（只修 chunked 写出器）。

## 3. 逐项核对主审的决定性主张

| # | 主审主张（出处） | 我的核对 | 结论 |
|---|---|---|---|
| 1 | 材料彼此对应；隐藏测试 = 公开测试 + 3 条 `all(chunks)`；47 键全为 PASSED；目标键 2 个；noop 失败在 :474 与 :438（初稿 §1） | 与我初判的独立核对逐项相同（哈希、diff、两次 noop 日志） | 同意 |
| 2 | I1：标题场景无键覆盖，P1 预计得 1（初稿 I1、card I1） | AP1 实测 47/47 且 C3 失败【执行】 | **同意，改记为已执行确认** |
| 3 | I2：示例断言恒真；示例与标题不是同一路径；P2 判 0 有依据 | 恒真：CPython 3.12 源码中 `_Call(tuple)` 没有覆盖 `__bool__` / `__len__`（初判 §1）；公开读者在不看答案的情况下给出同样推断（`public_read.md:73`）；历史复现第 35 行自己改用了 `c[1][0]`。路径差异见 `send_headers()`（`protocol.py:631-641`）。P2 判 0：公开读者从公开材料独立推出"只改 chunked 写出器不满足 R1"（`public_read.md:49`） | 同意。"恒真"仍是源码级证据，没有照字面执行过 |
| 4 | I3：还原兼容改写后得 0；delta 相对基线（delta #8、card I3） | 【合同】`FrozenPatchArtifactV1.baseline_manifest_digest` 的说明是"delta 的锚"（`contracts/frozen_patch.py`），`FrozenDeltaSource` 的说明是"应用 = 直接文件写入"（`manager.py:383`），所以还原的文件会成为 delta 条目并在评分时重放。注意 `manager.py:360-370` 的 `EXPORT_PATCH_SCRIPT` 是相对 `HEAD` 求 diff 的，不是这条正式评分输入。**精确化**：`aiohttp/__init__.py:8-9` 导入 `.connector` 与 `.client`，`connector.py:18` 又 `from .client import`，`client.py:14` 再 `from .client_reqrep import`，所以还原 `client.py` 或 `client_reqrep.py` 就足以让 `import aiohttp` 报 SyntaxError，隐藏测试收集失败、得 0。`server.py` 只被 `web.py` 导入，`worker.py` 没有被导入，只还原这两个不影响隐藏测试 | 同意机制，**修改表述**。发生概率低到中；典型触发是 `git checkout -- .` / `git stash` 撤销实验。未执行 |
| 5 | 旧 R03"照写即复现"被部分推翻（delta #4） | `repros/…6183….py:35` 用的是 `[c[1][0] for c in write.mock_calls]`；B 段（39–54 行）不设 Content-Length，是另写的配置 | 同意 |
| 6 | 环境层结论：导入须 `/testbed` 在 sys.path 上、裸 `pytest` 收集失败、无 pip、无出网、`create_task(loop=)` 报 TypeError、`make .develop` 目标名不匹配（delta #9–#12） | posthoc2 根因行 `TypeError: create_task() got an unexpected keyword argument 'loop'`；posthoc3 `[bare pytest] rc=2 … ImportError while importing test module`；`Makefile:10` 只有 `develop` 目标 | 同意。"目标名不匹配"对另外 4 张 aiohttp 镜像的解释力未核 |
| 7 | S3 缩小：R-f 渲染出的正文与 `user_prompt.txt` 逐字相同 | `prompts.jsonl:5` 的 metadata 是本题，`prompt` 1248 字符，与 `user_prompt.txt` 完全相等 | 同意。组装后的完整消息（提示加正文）仍未知 |
| 8 | S1 / S2"已实施、待 A 审"；清单 29 由 issue 改为 pass（delta #22、§2） | 只有协调者的陈述与 devcheck 路径的证据；接线代码未经 A 线审查 | 保留为有条件的 pass：29 的 pass 只对 devcheck 路径成立，`disposition.conditions` 第 2 条必须保留 |
| 9 | 客户端路径不触发本 bug（初稿 §6） | `client_reqrep.py:219,224`：压缩一定会设 `chunked = True`；`:315` 把它转成块大小；`send()` 在 429–434 行把分块过滤器接在压缩之后，空块被吸收 | 同意 |
| 10 | gold 没有引入回归（初稿 §6，清单 26） | 私有对照中相邻 3 个公开文件没有新增失败（初判 §7） | 同意，但范围只到这 3 个文件 |
| 11 | A1、A2 会被接受；P2、P3 判 0 有依据（清单 24） | A2 的近似版 AP2 已执行得 1。A1 仍只有静态推演，我与主审各自推演一致。P2、P3 未执行，推演一致 | 同意。清单 24 的 note 应补上 AP2 的执行证据 |
| 12 | 证据边界："两次构建，没看到 devcheck 那次构建的 recipe_sha256"（初稿 §1） | 新账本给出 `0bf7bf28…` 的 recipe_sha256 为 `0da821a1…`，与 `d58fc357…` 相同 | 修改：边界缩小（见 §2） |

## 4. 反查

### 4.1 有没有"先看答案再说显然"

没有发现。
- T2（`deflate_filter`）的依据，主审明确标成"由 Expected Behavior 推广"。
- P2 判 0 的依据来自示例配置。公开读者没看过答案，也独立推出了这一点。
- 主审还把示例几乎逐字暴露目标测试形状记成了一条题面问题。

### 4.2 替代实现、调用者与非默认值

- **真实生产路径**：`StreamResponse.enable_compression()` 加上不带 `chunk_size` 的 `enable_chunked_encoding()`（`web_reqrep.py:554-563`），正是 C3 场景。所以 AP1 这类补丁得 1 时，真实的 web 压缩响应仍会被截断。I1 的影响不只停留在测试层面。
- **gzip 与多次写入**：隐藏测试没有覆盖。gold、AP2、A1 按推演都能处理，不存在误拒；只能靠 C3 的加强变体检查。主审已经建议加 gzip、分两次写入的变体，我同意。
- **不经过滤器直接 `write(b'')`（公开读者 R9）**：在题意之外。更完整的修复不会翻转任何键（推演）。

### 4.3 修订建议（Q2 / Q3）是否扩大原需求

- **Q2（补一个隐藏键）不扩大需求。** 标题和描述明说了"chunked 响应提前 EOF"，gold 与 AP2 已经满足。
  - **断言口径**：主审建议"正文精确等于 `6\r\nKI,I\x04\x00\r\n0\r\n\r\n`"。在本镜像里 deflate 输出是确定的，现有公开测试（`deflate_and_chunked`）也用逐字节比较，所以可以接受。但我更推荐语义口径，或者两者并列：`all(chunks)`；块长序列里 0 只出现在最后；去掉分块帧后等于 `_COMPRESSED`。可以直接复用历史复现脚本 B 段的解析逻辑（`repros/…6183….py:45-53`）。这样对"合法但分帧不同"的实现更稳。
  - **验证**：修订后要验证 noop 与 AP1 判 0、gold 与 AP2 判 1（有条件再加 A1），原 47 键不变，各跑 2 次。
  - **代价与决定权**：修订会让本题与上游 R2E 的判分口径不再一致，外部结果不能直接对比。按 E05，这需要用户决定。
- **Q3（改示例断言为 `c[1][0]`）不改变判分。** 它只消除字面误导，是公开规格修订，优先级低。

### 4.4 "可探针"的条件是否与静态候选分开

主审已经分开：`state=needs_review`，`suggested_list` 是附条件的 `probe_candidates`，没有冒用 `ready_for_probe`。建议补三条判读规则：
1. **C3 口径**：用 §4.3 的语义检查，或"精确相等 + 语义检查"并列，避免把分帧不同的合法补丁误判为失败。
2. **分开报告**：原始 RH2 reward 与经 C3 校正后的结果分开报告，不把评测口径的变化混进模型表现。
3. **I3 归因**：reward 为 0，且评分日志在 `client.py` / `client_reqrep.py` 报 `asyncio.async(` 语法错误时，归因为 I3（环境陷阱），不计为能力失败。

另外，**训练用途**要以 I1 解决（Q2 修订或奖励校正）为前提；当前处置只限诊断用途，这一点应写进 `disposition.conditions`。

### 4.5 没有把环境已验当成质量合格，也不只是在核对旧结论

- delta #23 明确区分了 `environment_qualified` 与测试能否区分修复。
- I1、I2、I3 都是历史环境审查没有触及的新问题。

### 4.6 记录一致性（小项）

- **I1**：`issues[I1]` 的 status 与 evidence_level 应随 AP1 的执行结果更新。
- **清单 10 与 I3**：清单 10 记为 `pass`，但 I3 引用了 10。建议二选一：把 10 改为 `issue`，或者让 I3 只挂在 16 上。
- **下一步**：`disposition.next_step` 与 `card.md` §6 应改为"P1（AP1）已确认；A1 未跑；待用户决定是否修订"。

## 5. 与我初判的差异

- **I3**：我初判没有发现；核对后同意，并补充了导入链的精确化。
- **I1**：我初判把 P1 列为漏测的静态候选；现在已由 AP1 执行确认。结论不变，证据级别上升。
- **两次构建是否等价**：由"未知"缩小为"配方 sha 与评分脚本相同，逐层内容未对账"。
- **P2**：我初判把它列为误拒对照，这次没有跑。公开读者、主审和我三方推演一致，而且它不影响处置，所以降为可选。
- **其余**：R2E 专项、gold 检查、开发条件等都与主审一致，没有新的分歧。

## 6. 保留的未知与可选实验

1. **A1 是否会被接受**（在压缩过滤器处修）：未执行。可选：跑 1 次，并加跑 C2 / C3。
2. **示例字面断言是否恒真**：没有照字面执行。可选：在 base 上跑一次，补上题面缺失的定义后直接用 `mock_calls`，预期不失败。
3. **P2 是否判 0**：未执行。可选。
4. **组装后的完整消息（提示加正文）与正式链接线**：待 A 线审查后捕获，是 actor 待验项。
5. **两次构建的逐层等价**：只有在需要把 devcheck 证据与 R-f 评分证据合并引用时，才需要核对。
6. **是否出修订版（Q2 / Q3）**：由用户决定。未决定前，I1 按探针条件（C3 后检）处理。
