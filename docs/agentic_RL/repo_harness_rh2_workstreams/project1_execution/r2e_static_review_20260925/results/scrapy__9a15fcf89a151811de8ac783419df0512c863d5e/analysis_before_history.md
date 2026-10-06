<!-- 协调者注（2026-09-25）：本文由主审会话写出，宿主拒绝子会话写报告文件（"Subagents should return findings as text"），协调者从该会话记录里被拒的写入调用中原样取出保存，未改一字。 -->
# 私有主审初判（读历史前）：scrapy__9a15fcf89a151811de8ac783419df0512c863d5e

- 角色：R2E 私有主审（静态审查），2026-09-25，按 `roles/investigator_r2e.md` 第 1–7 步。
- 材料：公开包、私有包、`run_refs.json` 指向的原始账本与日志，以及 P4 诊断候选的 diff 原件（账本记录了它的 sha256，本地文件与之一致）。没有运行代码，没有开容器或远端，没有修改原件，也没有读任何历史调查（阅读范围见附录 C）。
- 证据级别：
  - **【当前实测】**：`material=current` 的真实 RH2 回放。
  - **【诊断实测】**：`diagnostic` 行，材料与派生镜像同当前。
  - **【独立参考】**：M3 在来源镜像上的独立 runner。
  - **【静态】**：读代码得出的推断。
  - **【镜像层面实测】**、**【actor 待验】**：按环境卡的定义使用。
- 路径约定：`worktree/…` 相对 `PUBLIC_DIR`；`hidden_tests/…`、`gold.patch` 相对 `PRIVATE_DIR`；日志文件用哈希后缀简称，全路径见附录 A。

## 0. 结论

**题意、材料、目标键和 gold 都没有问题。**
- 题面示例字符串正是隐藏测试新增的唯一一行（`hidden_tests/test_1.py:38`）。
- noop 恰好在这一行失败，报错与题面描述一致：`Response != TextResponse`。
- gold 在表中补一行就修好了。

**问题出在期望映射。** 7 个键中有 2 个被期望为 FAILED：`test_from_headers` 和 `test_from_args`。
- 失败原因：这版 scrapy 以 Python 2.7 为主，在 py3 下 `Headers` 返回 bytes，导致 `TypeError`。
- 这两个键不保护任何回归：两个测试方法都在第一次读取 bytes 头值时就抛错，后面的映射根本没执行。
- 它们只会惩罚一种修复：把同一函数的 py3 bytes 兼容补完整。P4 诊断中的补丁只改 `scrapy/responsetypes.py`，7 个键全部通过，reward 却是 0。

**暂定处置：** `needs_review`。理由有两条：
1. 测试标准过严：期望锁定了环境年代错配造成的失败。
2. actor 条件待验：正式链目前仍使用来源镜像。

用于诊断时可以配合判读规则使用；作为 reward 使用前，建议先修订。

## 1. 八方面覆盖

| 方面 | 已查 | 未查 / 缺项 |
| --- | --- | --- |
| 公开需求 | 题面、`public_hints`、brief、`public_read.md` 全文。题面原例能在 base 源码上推出（`worktree/scrapy/responsetypes.py:41-57`）。有两个小瑕疵，都不影响题意：一是 `responsetypes` 同时是模块名和单例名，二是把整串 content-type 叫作“MIME type”。 | 没有捕获实际渲染的消息；`user_prompt.txt` 只是静态渲染。 |
| 材料与初态 | 私有文件的哈希与摄入行、日志记录全部一致（附录 A）。初态 diff 为 0 字节。隐藏测试等于公开的 `tests/test_responsetypes.py` 加一行。M3 的 `gold_meta` 显示，上游修复提交只改了 `responsetypes.py` 和这个测试文件。noop 的失败位置与题面一致。 | — |
| 测试是否测到要求 | 7 个键逐个追到了调用路径和断言。目标键只通过 str 版 `from_content_type` 覆盖题面原例。 | 没有测试覆盖 x-json 的大小写或空白变体，也没有覆盖 `from_mimetype` 等其它入口。影响小，见 §2。 |
| 是否误拒合理解 | 发现一类误拒：补完整 py3 bytes 兼容的修复得 0【诊断实测】。另外推演了三种写法：JSON 族规则、别名归一、在 `from_content_type` 里特判，都得 1【静态】。 | “只做部分 bytes 修复仍得 1”只有静态推断，未运行。 |
| 回归与 gold | gold 只加一行，没有无关改动。7 处调用者都经 `from_args`，x-json → `TextResponse` 正是修复意图。回归键保护的范围：html、xml、xhtml、octet-stream 四类映射，以及 `from_filename`、`from_content_disposition`、`from_body`、`mime.types`。 | 同表中另外 6 个条目（如 `application/json`）和 `content_encoding` → `Response` 都没有有效保护【静态】。调用者只读了 grep 命中行，以及 `httpcompression.py` 的 15-45 行。 |
| agent 开发条件 | 环境卡、brief 和评分侧观测，详见 §5。 | actor 身份下的 import、pytest 入口，以及正式链的 PATH 和提示都是【actor 待验】。 |
| 交付与评分边界 | 合法修复只改 `scrapy/responsetypes.py`；gold 和 P4 的投影 `included_paths` 与此一致。grader 只替换 `r2e_tests/` 和 `run_tests.sh`。根目录的 `conftest.py` 和 `pytest.ini` 在评分时生效，候选也能修改。 | 没有针对本题做评分控制面的攻击，属共享机制。本题没有题目特有的 helper。 |
| 题目关系与用途 | 题面原样给出测试输入和期望类，而表中已有同类条目 `application/json`，修法几乎唯一。来源镜像里修复提交可达，`/r2e_tests` 也可读（M3 facts）。 | 没查与池内其它 scrapy 题的同文件或同族关系；预训练暴露未知。 |

**`public_read.md` 没捕获、而原件能补上的条件：**
1. 正式 actor 目前用的是**来源镜像**（环境卡 §2）。在这张镜像里，`/r2e_tests` 可读，`git` 能找到修复提交。M3 facts 为 `fix_reachable=commit`、`head_is_parent_of_fix=yes`、`commits_after_head=6821`、`r2e_tests_root=2`。
2. `.venv` 不会出现在 `git status` 里。评分日志开头只列出 `?? install.sh` 和 `?? run_tests.sh`；M3 facts 中 `status_lines=2`。
3. 环境是 pytest 8.3.4，没有装 pytest-twisted，`twisted = 1` 只产生一条警告（noop 日志 :115）。

公开读者的三个关键未知都能从私有材料回答（§3）。其 C4 预测“base 下这两个用例因 bytes 抛 `TypeError`，其余通过”与评分日志一致。

## 2. 核心映射

| 公开要求 / 合理旧行为 | 依据 | 测试 ID / 决定性断言 | 覆盖 | 运行证据 / 待做 |
| --- | --- | --- | --- | --- |
| R1：`from_content_type('application/x-json; encoding=UTF8;charset=UTF-8') is TextResponse` | `user_prompt.txt:10-14` | `test_from_content_type` 第 7 个映射（`test_1.py:38`，断言在 `:42`） | 覆盖，输入与题面原样一致 | noop 在 `:42` 抛 `AssertionError`，文字与题面一致；gold 通过【当前实测】×2【独立参考】×2 |
| R2：MIME 主体是 x-json 即可，不论参数、大小写 | `user_prompt.txt:18` | 只有 R1 这一个字面值 | 部分 | base 会先 `.lower()`，任何表驱动的修复都自然满足【静态】 |
| R3：`from_mimetype`、`from_headers`、`from_args` 对 x-json 给出同样结果 | 推知：各入口汇到 `from_mimetype` | 无。header 路径的两个测试在 py3 下是死测试 | 缺失 | 只在 `from_content_type` 里特判也能过；除直接调用 `from_mimetype` 外，行为与 gold 相同（没有扩展名映射到 x-json，也没有外部调用者直接调它）【静态】 |
| K1：html、xml、xhtml、wap、octet-stream 的映射保持不变 | `responsetypes.py:18-31`；公开测试 `:30-37` | `test_from_content_type` 前 6 个映射 | 覆盖 | 所有运行都通过 |
| K1′：`application/json`、`application/(x-)javascript`、`atom/rdf/rss+xml` 保持不变 | `responsetypes.py:20-28` | 无 | 缺失 | 反例：把 `'application/json'` 改名成 `'application/x-json'` 能得 1，却会弄坏 json【静态，未跑】 |
| K2：给了 `content_encoding` 就返回 `Response` | `responsetypes.py:54-55` | `test_from_headers` 第 3 个映射，永远执行不到 | 缺失（死断言） | noop 和 gold 都在第 1 个映射抛错（noop 日志 :50、:58） |
| K3：`from_filename`、`from_content_disposition`、`from_body`、自带 `mime.types` 保持不变 | 公开测试 | 对应 4 个键 | 覆盖 | 所有运行都通过 |
| A2（题面没要求）：py3 下接受 bytes 头值 | 无 | `test_from_headers`、`test_from_args` 期望 FAILED | **冲突**：补完整会被判 0 | P4：7 键全过，匹配 5/7，reward 0【诊断实测】 |

**反向核对（键 → 公开依据）：**
- `test_from_content_type`：依据是 R1 和 K1。
- `test_from_filename`、`test_from_content_disposition`、`test_from_body`、`test_custom_mime_types_loaded`：依据是公开测试里原有的同名用例，内容未改。
- `test_from_headers` / `test_from_args` 期望 FAILED：没有任何公开依据要求它们失败。
  - 这个状态来自 py2 时代代码在 py3 下的不兼容。
  - 上游在这个提交上把整个 `tests/test_responsetypes.py` 列进了 `tests/py3-ignores.txt:40`，经 `conftest.py:25-29` 在 py3 下不收集。
  - R2E 把文件搬到 `r2e_tests/` 后绕开了这条忽略，py3 失败于是被固化进期望。

## 3. R2E 专项

**(a) 非 PASSED 键及能否被正确修复翻转。**
- **失败机制**：`Headers.normkey/normvalue` 在 py3 下把键和值都转成 bytes（`worktree/scrapy/http/headers.py:13-36`）；`from_headers` 取到 `b'text/html; …'`，`from_content_type` 对它执行 `.split(';')`，抛出 `TypeError`（`responsetypes.py:56`）。
- **失败位置**：两个测试都死在第一个带头的映射（noop 日志 :50、:102）。
- **这两个键是死键**：测试方法里任何别的行为出错，结果仍然是 FAILED，不会改变匹配结果。
- **会被判 0 的修复**：只有当 `from_content_type` 和 `from_content_disposition`（或 `from_headers` 对这两个头）都兼容 bytes 时，这两个键才会翻成 PASSED。P4 候选就是这样：gold 加上两处 `isinstance(…, bytes)` 后用 latin-1 解码。结果 7 键全过，reward 0【诊断实测】。
- **仍得 1 的修复**：只兼容 content_type 的部分修复，会让 `TypeError` 转移到 `from_content_disposition`，发生在 `test_from_headers` 的映射 2 和 `test_from_args` 的映射 3，所以两个键仍是 FAILED【静态】。
- **结论**：得分取决于一项题外修复做得完不完整，这与题意无关。
- **诱因**：求解者照公开包的方式显式运行 `tests/test_responsetypes.py` 时，base 上就能看到这两个 `TypeError`，报错位置正是题面点名的函数，容易被引导去补。这个诱因会不会真的触发，要看真实轨迹（清单 34/35），静态审查不代答。

**(b) 题面描述的报错是否出现在 noop 目标键里：出现了。** noop 日志 :78 为 `AssertionError: application/x-json; encoding=UTF8;charset=UTF-8 ==> <class 'scrapy.http.response.Response'> != <class 'scrapy.http.response.text.TextResponse'>`，与 `user_prompt.txt:13-14` 一致；两次 current 运行结果相同。

**(c) 泄漏：**
- 题面没有给出代码，但给了原样测试输入和期望类，而表中紧邻已有 `'application/json': 'scrapy.http.TextResponse'`，修法几乎被直接指出。这影响难度，不影响评分正确性。
- 来源镜像的答案通道（`/r2e_tests` 可读、修复提交可达）在本题成立（M3 facts）。这属于共享问题，要等正式链改用派生镜像才能解决（环境卡 §2）。

**(d) base 版测试辅助 / 搬迁伪影 / 撞键：**
- 隐藏测试只导入 `scrapy.responsetypes` 和 `scrapy.http`，不依赖仓库测试模块里的辅助代码。
- 只有一个测试文件，不会撞键。
- 搬迁伪影有一个，就是 (a) 所说的：搬迁绕开了上游的 py3 忽略清单。
- 根目录的 `conftest.py` 对 `r2e_tests` 生效，其中的 `chdir` fixture 会让每个用例在 tmpdir 中运行。`pytest.ini` 同样生效，含 `--doctest-modules --assert=plain`，`python_files` 也包括 `__init__.py`。这两个文件都不会被评分重置，但合法解不需要改它们。

**(e) 时间 / 随机 / 资源敏感：没有。**
- `from_filename` 依赖 Python 3.9 内置的 mimetypes 默认表加上 `scrapy/mime.types`。`MimeTypes()` 实例不读系统的 mime 文件（按 stdlib 的静态阅读，未在本环境核对）。
- 运行情况：R-f 与中央复跑的 noop、gold 状态一致；M3 的 gold 两次一致；内存峰值 205 MB，测试约 1 s。

**(f) 材料修订：无。** `revisions.json` 为 `[]`，`env_recipe` 和 `resource_recipe` 为 null。环境卡中带 `+material_v2` 的 scrapy 题是 `cfed9b66`，不是本题。M3 用的是来源版材料，与当前材料相同，因此它可以作为同版本 runner 对照（清单 22）。

## 4. gold 检查

- gold 只在 `CLASSES` 中加一行（`gold.patch:9`），修好题面原例；在 py2 语义下，`from_mimetype` 和 header 路径也随之修好。
- **没有无关改动。** 调用者包括 `httpcompression`、`decompression`、`webclient`、`http11`、`file`、`ftp`、`httpcache`，都经 `from_args` 调用。解压后重新判型时，x-json 得到 `TextResponse`，正是修复意图。`TextResponse` 是 `Response` 的子类，已有的 `isinstance(…, Response)` 判断不受影响【静态】。
- **gold 没有处理 py3 bytes 问题**，这在题面范围之外。gold 日志中的 `TypeError` 行号从 :56 移到 :57，说明补丁确实已应用、代码路径没变。在本环境下，题面所说的“下游处理”场景（经 `Headers` 判型）即使用了 gold 也走不通。这是年代错配，不影响目标键。

## 5. 逐题开发需求

| 项 | 需求与事实 | 证据级别 |
| --- | --- | --- |
| 导入 | `python` 指向 `/testbed/.venv/bin/python`（3.9.21）；scrapy 从 `/testbed/scrapy/__init__.py` 导入，版本 `1.1.0dev1` | 解释器：【镜像层面实测】（环境卡 §2、brief）；导入路径：评分侧实测（R-f noop 账本 `observations`，uid 54322）；agent 身份下的导入：【actor 待验】 |
| 依赖 | pytest 8.3.4 已装；没有 pytest-twisted，只影响警告。修复不需要新依赖；没有 pip，不能出网 | 评分侧日志 + 【镜像层面实测】 |
| 资产 | `scrapy/mime.types` 和 `scrapy/VERSION` 都在工作树中 | 评分侧：`test_custom_mime_types_loaded` 通过 |
| 权限 | agent（uid 54321）可写 `/testbed` | brief【镜像层面实测】 |
| 网络 | 准备、解题、测试各阶段都不需要网络 | 静态；评分为 `deny_all`；M3 `egress_pypi=fail` |
| 构建 | 纯 Python，不需要构建 | 评分日志 `RH2_INSTALL_SKIPPED=1` |
| 本地验证 | 复现命令：`python -c "from scrapy.responsetypes import responsetypes as r; print(r.from_content_type('application/x-json; encoding=UTF8;charset=UTF-8'))"`。回归命令：`cd /testbed && python -m pytest -rA tests/test_responsetypes.py`，必须显式给出文件路径，否则会被 `collect_ignore` 跳过。base 下预期 5 过 2 败，失败都是 `TypeError` | 静态推断（pytest 8 对显式路径不应用 ignore）；隐藏版的同构结果为评分侧实测；公开文件本身的运行：【actor 待验】 |
| 提交边界 | 只需改 `scrapy/responsetypes.py`。改 `tests/` 不影响评分。改根目录的 `conftest.py` / `pytest.ini` 会影响评分，合法解用不到 | 投影与恢复机制：评分侧实测 |
| 资源 | 默认 2 CPU / 4 GiB / `/tmp` 1 GiB 足够 | 评分侧实测 |
| 消息与链路 | `public_hints` 中的 conda、pip 以及“重置测试文件”说法对 R2E 不成立；本题的合法解不受影响。正式链还有两个问题：使用来源镜像、`expected_interpreter_prefix` 默认为 conda | 代码事实（环境卡 §2）；实际消息为缺项 |

## 6. 缺口与建议队列（交协调者安排，未执行）

1. **【决定】如何处理这两个 FAILED 键。** 两个选项：
   - **A. 修订测试标准。** 对 `test_from_headers` 和 `test_from_args` 按 py3 条件跳过。依据是上游 `py3-ignores.txt:40`，这是把上游的忽略意图局部恢复，不是把 FAILED 改成 PASSED，改成 PASSED 会让 gold 得 0。SKIPPED 不成键，期望变为 5 个键，全部 PASSED。修订后需复验 noop=0、gold=1、P4 overfix=1、部分 bytes 修复=1。
   - **B. 不改材料，只加判读规则。** 如果得 0，而 mismatched 恰好是这两个键从 FAILED 变成 PASSED、目标键又匹配，就记为“过度修复误判”，不算失败。

   A 适合拿来当 reward；B 只够诊断用。
2. **【CPU，可选】** 用部分 bytes 修复（只解码 content_type）核对静态推断：预期仍得 1，这能证明得分确实取决于修复的完整度。
3. **【CPU，低优先】** 跑 K1′ 反例，把 `'application/json'` 改名为 `'application/x-json'`：预期得 1，但 json 会被弄坏。是否在测试里补一条 `application/json` 断言（公开依据是 `CLASSES` 表），需要另外决定；这属于扩大测试标准，不能随修订 A 一起夹带。
4. **【actor】** 等正式链改用派生镜像、修好解释器前缀后，以 agent 身份核对：显式路径跑公开测试的结果，以及 `python` / `pytest` 入口。

## 7. 暂定处置

- **状态**：`disposition.scope=static_review`，`state=needs_review`。
- **reason**：题意 / 测试争议——期望把两个 py3 既有失败锁成 FAILED，更完整的正确修复会被判 0【诊断实测】。另有 actor 条件待验，属共享问题。
- **用途**：`development_diagnostic`。如果采用 B，可以作为有条件的探针候选；如果要作 reward，建议先做 A。
- **唯一最值得先做的下一步**：由协调者或用户在 A 和 B 之间决定。若选 A，先用 CPU 复验修订版上的四个候选：noop、gold、P4 overfix、部分 bytes 修复。

---

## 附录 A：运行证据（均已核对 sha256 与 `run_refs.json` 一致）

- **R-f noop**：`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-s_49e74388.eval.log`
  - :21 为 `.F..F.F`。
  - :43-60 为 `from_args → from_headers → responsetypes.py:56 TypeError`，其中 `content_type = b'text/html; charset=utf-8'`。
  - :78 为目标断言。
  - :122-128：4 个 PASSED，3 个 FAILED。
  - 账本 `ledger_r2e_all_noop.jsonl:45`：`match 6/7`，`mismatched=[test_from_content_type]`；`observations` 中导入路径为 `/testbed/scrapy/__init__.py`；`mem_peak_mb=205.062`；`policy` 为 2 CPU、4 GiB、tmpfs 1 GiB、`deny_all`、uid 54322。
- **R-f gold**：同目录 `…all-gold-s_798f95c6.eval.log`
  - :1 为 ` M scrapy/responsetypes.py`，:22 为 `.F....F`。
  - :61、:93 显示 `TypeError` 在 `responsetypes.py:57`。
  - :103-109：5 个 PASSED（含 `test_from_content_type`），2 个 FAILED。
  - 账本 `ledger_r2e_all_gold.jsonl:45` 记为 7/7，reward 1。
- **中央复跑**：`runs/r2e_env_repair_20260924/_rerun2/eval_logs/`
  - noop `…rer_92f27267`，:122-128 与 R-f 相同。
  - gold `…rer_14d83f49`，:103-109 与 R-f 相同。
  - 两个账本各取第 45 行。
- **P4 overfix【诊断】**：
  - 日志 `runs/r2e_env_repair_20260924/p4/eval_logs/evallog_replay-r2e-envrepair-p4-_1acaf88b.eval.log`：:22 为 `.......`，:33-39 全部 PASSED，:42 为 `RC=0`。
  - 账本 `p4/ledger_overfix.jsonl:1`：reward 0.0，`mismatched=[test_from_args, test_from_headers]`，`projection.included_paths=[scrapy/responsetypes.py]`，派生镜像 ID `fe908bed…` 与 R-f 相同。
  - 候选 `p4/overfix/scrapy__…diff`（sha256 为 `81cedada…`，与账本一致）：包含 gold 那一行，另加 :16-17 与 :23-24 两处 latin-1 解码。
- **M3 独立参考**：`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl`
  - :31 与 :78 两次都是 reward 1，`expected_statuses` 为 PASSED 5 / FAILED 2。
  - 日志 `logs_r2e/scrapy/9a15fcf89a15/gold/a1|a2/test_output.txt` 的 :88-94 状态相同；两份日志除地址和耗时外完全一致。
  - facts 见 §1。
- **材料哈希**：
  - `hidden_tests/test_1.py` 为 `5a84fa9f…`，`__init__.py` 为空文件哈希，两者均等于 `grading_bundle.json` 的记录。
  - 隐藏测试树哈希 `a3f0f6e4…` 与日志中的 `RH2_SETUP_HIDDEN_TESTS_TREE` 一致。
  - `run_tests.sh` 为 `8285765f…`，等于 `RH2_SETUP_ENTRY_SHA256`。
  - `expected_output.json` 为 `2fefa8a5…`，`gold.patch` 为 `dcb13cf5…`，两者都与摄入行一致。

## 附录 B：候选键级推演

表中其余 4 个键在所有候选下都是 PASSED；Hd = `test_from_headers`，Ar = `test_from_args`。

| 候选 | `test_from_content_type` | Hd / Ar | reward | 依据 |
| --- | --- | --- | --- | --- |
| noop | FAILED | FAILED / FAILED | 0 | 【当前实测】 |
| gold（表中加一行） | PASSED | FAILED / FAILED | 1 | 【当前实测】【独立参考】 |
| 其它写法：`from_mimetype` 识别 JSON 族、别名归一、`from_content_type` 特判 | PASSED | FAILED / FAILED | 1 | 【静态】 |
| gold + 只解码 content_type | PASSED | FAILED / FAILED（`TypeError` 移到 `from_content_disposition`） | 1 | 【静态】 |
| gold + content_type 与 content_disposition 都解码（P4） | PASSED | PASSED / PASSED | **0（误拒）** | 【诊断实测】 |
| 改 `Headers` 在 py3 下存 str | PASSED | 很可能 PASSED / PASSED | 0 | 【静态】；这改变了 `Headers` 的 bytes 契约，拒绝可以接受 |
| 只改 `mime.types` | FAILED | FAILED / FAILED | 0 | 【静态】；正确拒绝 |
| 返回 `TextResponse` 的子类 | FAILED（`is` 比较不通过） | FAILED / FAILED | 0 | 【静态】；有题面依据的拒绝 |
| `application/*` 兜底为 `TextResponse` | FAILED（octet-stream 那一条） | FAILED / FAILED | 0 | 【静态】；正确拒绝 |
| 把 `'application/json'` 改名为 x-json（错误实现） | PASSED | FAILED / FAILED | 1 | 【静态】；漏测，见 K1′ |

## 附录 C：阅读范围与暴露

**已读：**
- 角色卡和四份方法文档（八方面协议、R2E 环境卡、记录模板、40 项清单）。
- `public_read.md`；公开包中的 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`，以及 `worktree_manifest.json` 的顶层字段。
- `worktree/` 中的文件：
  - 全文：`scrapy/responsetypes.py`、`scrapy/http/headers.py`、`scrapy/http/__init__.py`、`conftest.py`、`pytest.ini`、`tests/__init__.py`、`.gitignore`。
  - 片段：`CaselessDict`、`scrapy/utils/python.py` 的函数清单与 `isbinarytext`、`httpcompression.py:15-45`、`tests/py3-ignores.txt`。
  - 核对：公开 `tests/test_responsetypes.py` 与隐藏测试的 diff。
  - 全仓 grep：调用者、`json` 与 `x-json`、py3 忽略项。
- 私有包的全部文件。
- `run_refs.json` 指向的 6 个账本行、8 份日志，以及 P4 候选 diff。

**未读：**
- `OUTPUT_DIR` 中除 `public_read.md` 以外的文件（包括 `reviewer_initial.md`）。
- 任何 `history/` 目录、`docs/…/r2e_env_repair_20260924/`、任何 review 目录、`r2e_static_review_20260925/README.md`。
- `runs/` 下的分析与汇总文件。
- 账本中的 `diagnostics_ref` 所指文件。

**暴露：** 已见过 gold、隐藏测试、期望映射、P4 候选。本稿不可提供给求解模型。
