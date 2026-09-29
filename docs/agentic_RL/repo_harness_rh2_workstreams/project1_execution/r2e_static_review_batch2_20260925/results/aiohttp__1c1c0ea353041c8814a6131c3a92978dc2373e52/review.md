# aiohttp__1c1c0ea3 独立复核（review，第二步）

2026-09-25 · 独立复核者。第一步的封存稿是 `reviewer_initial.md`，本文不改它。

证据级别：
- **【实跑】**：协调者今天用正式 RH2 回放代码评分，镜像是 derived9（`bd9b7c27…`），每个候选跑 1 次，另跑了诊断脚本；
- **【日志】**：复读已有的运行原件；
- **【原始记录】**：来源数据集的执行记录；
- **【静态】**：读源码或测试推断。

我没有运行任何代码或容器。

简写：`PUB`、`PRIV` 同初判；`G` = `runs/r2e_actor_20260925/grader/`。

## 0. 结论

- **同意主审的处置**：`needs_review`，理由是“静态候选，待 actor 验证”；用途是 development_diagnostic；不需要为评分正确性改题。
- **同意主审的三项主要发现**：
  1. C3 漏测；
  2. 时序键应列为 watch；
  3. 与 `aiohttp__22a12cc2` 存在跨题包含。

  主审没有先看答案、再把隐藏要求说成“显然”：隐藏测试的观测方式——看 `loop.call_exception_handler` 有没有被调用——公开读者在没有接触隐藏材料时独立想到了（`public_read.md` 的 E2），公开测试 `tests/test_run_app.py:826-856` 用的也是同一个通道。
- **实跑确认了主审和我初判的全部候选预测**：

  | 候选 | 实跑得分 | 诊断结果 |
  | --- | --- | --- |
  | gold | 1（56/56） | 抛出 |
  | C1 | 1（56/56） | 报告 |
  | C3 | **1**（56/56） | **丢失**：错误既没被抛出，也没被报告 |
  | C5 | 0（49/56） | 报告 |

  C3 的补丁与我初判“候选 B”的主写法逐字相同；C1 等于我的候选 A，C5 等于我的候选 C（逐项对照见 §2 第 5、6 条）。
- **修改或补充以下几处**，下文都附了依据：
  1. **时序键**：采纳主审找到的“启动竞态”机制，这一点我初判漏了。但要补一条环境事实：来源数据集记录的两次失败，发生在 GCP 主机上的本地 checkout 里，**不在发布镜像内**（pytest-asyncio 版本也不同）。容器环境里这个键累计 21/21 通过。所以现有证据说明的是“换了环境可能翻转”，而不是“RH2 容器内会随机抖动”。
  2. **C3 漏测的严重度**：按用途区分。只做开发诊断时，我同意主审的“次要”。如果把本题的 reward 用于训练，应升为“中”：C3 用的是 cancel 加 `gather(return_exceptions=True)` 这种惯用写法，模型很容易写出来，而 reward 分不出它与正确解。
  3. **修订建议**：“二选一”断言本身不扩大需求，但诊断用途下建议先不改 reward，改用已有的诊断脚本做旁路检查。
  4. **几处小的事实修正**：见 §2 第 14、15 条。
- **没有实质分歧**。与历史记录在“时序族已关闭”的措辞上仍有分歧：我同意主审改为 watch。
- **最小后续实验**：在并发负载下重复评分 gold，统计 `TestShutdown.test_shutdown_handler_cancellation_suppressed` 翻转的比例（§6）。

## 1. 第二步读取范围

- **OUTPUT_DIR**：`public_read.md`、`analysis_before_history.md`、`old_findings_delta.md`、`card.md`、`screening_record.json`（全部字段）。
- **历史引用**：`v3/history/aiohttp__1c1c…/refs.json` 列出的文件。
  - 读了：本题的 `findings.md`、`screening_record.json`（issues、disposition、checks）；`known_issues.json` 中本题的两个族，以及 `expected_provenance_mixed`；`decisions.md` 的 E06、E09、E10、E18；`results_20260924.md` 的本题行；`repros/aiohttp__1c1c….py`；`packages/p1/README.md` 中涉及本题的段落。
  - `facts.json` 没有读。
- **为核实主审主张另外打开的原件**：
  - 来源原始记录 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/raw/r2e_gym_subset_48_e8b9fcbc.jsonl` 第 6 行：看了它的 `execution_result_content`（新旧两次运行的汇总、失败段、平台行）和 `expected_output_json`。
  - `PUB/worktree` 下的 `CHANGES.rst:2070-2080, 2436-2444`、`docs/web_advanced.rst:1100-1125`、`docs/web_reference.rst:2980-2990`。
  - `aiohttp__4075c653` 公开包的 `web.py:522` 和 `__init__.py:1`。
  - devcheck 的 `orig/stub/requests/messages_000.json`（只看开头）。
- **协调者今天的实跑证据**：
  - `runs/r2e_actor_20260925/grader_cands/aiohttp_1c1c_{C1,C3,C5}_*.patch` 全文；
  - `G/ledger_a1c1c_{gold,C1_skip_done_main_task,C3_gather_swallow,C5_drop_main_cancel}.jsonl`（逐行解析）；
  - 4 份对应 eval 日志：sha256 核对，看了汇总、失败行和耗时；C5 的失败段看了定位行；
  - `G/postcheck_b2/a1c1c_{base,gold,C1_…,C3_…,C5_…}.json` 全文；
  - 诊断脚本 `rh2/experiments/r2e_actor_20260925/postcheck/aiohttp_1c1c0ea3_cleanup_error.py` 全文。
- **没有读**：批次 README、`assignments.json`、`grader_candidates.md`、首批审查目录、Codex 复核目录、`runs/r2e_t0_batch2_20260924/reconcile/` 和 `provenance/` 下的汇总文件，以及同仓其它题的私有包。

## 2. 主审决定性主张逐项核对

| # | 主审主张（出处） | 核对 | 结论 |
| --- | --- | --- | --- |
| 1 | 唯一目标键是 `test_run_app_raises_exception[pyloop]`，其余 55 键与公开的 `tests/test_run_app.py` 逐字相同（card §1） | 初判里 diff 过：只有第 12 行的 import 和第 909-925 行的新增测试；conftest 完全相同 | 同意 |
| 2 | noop 7/7 次只错目标键（失败在 `test_1.py:923`），gold 7/7 次 56/56（analysis §2） | 14 份日志的 sha256 都与 `run_refs` 一致【日志】。今天在 derived9 上 gold 又是 56/56（`G/ledger_a1c1c_gold.jsonl`，补丁 `926c9558…`）。主审说过“`bd9b7c27` 上没有隐藏测试评分”，这一点现在已补上【实跑】 | 同意，并补这条证据 |
| 3 | “`call_exception_handler` 没被调用”这一观测方式有公开依据；C6 被拒不算缺陷（delta 第 7 条，check 24） | 依据是真的：base 源码里唯一的报告通道就是 `web.py:449-459`；公开测试 `:826-856` 用异常处理器观测；公开读者在只读公开材料的条件下，E2 用的正是这个通道。C6 预期得 0 是静态可确定的：mock 替换的是 loop 实例上的方法本身，任何调用都会被记下 | 同意，补充 C6 的外部效果（见 §3 第 5 条） |
| 4 | C1 是合理替代解，得 1（card §5） | `G/ledger_a1c1c_C1_skip_done_main_task.jsonl`：56/56，reward 1；补丁 `98fa33f8…` 正是 `if not main_task.done(): _cancel_tasks({main_task}, loop)`。诊断结果是 reported，与 base 相同【实跑】 | 确认 |
| 5 | C3 可能混过评分，得 1；Ctrl+C 之后 cleanup 抛出的错误会丢失（issues `untested_regression_silent_drop`） | `G/ledger_a1c1c_C3_gather_swallow.jsonl`：56/56，reward 1。诊断 `G/postcheck_b2/a1c1c_C3_gather_swallow.json`：`outcome: lost`，`handler_calls: []`，`raised: null`【实跑】。**与我初判的候选 B 相比**：C3 补丁（`b8bab2e3…`）就是 B 的主写法（`main_task.cancel()` 加 `loop.run_until_complete(asyncio.gather(main_task, return_exceptions=True))`），逐字相同。B 的另一种写法是给 `_cancel_tasks` 加 `report=False` 参数、只对 main task 传入；它的执行步骤与 C3 相同（先 cancel，再 gather 并忽略异常，最后不报告），所以在所有路径上行为等价，但没有单独实跑。主审提到的 `with suppress(BaseException): loop.run_until_complete(main_task)` 在测试和诊断下也会得到同样结果，只在“主任务本身以 KeyboardInterrupt/SystemExit 结束”这个边角上有差别，也没有实跑 | 确认；证据级别应从“静态推断”升为“当前 CPU 实跑” |
| 6 | C5（删掉先取消主任务那一行）得 0，TestShutdown 多数键失败（card §5） | 49/56，reward 0；7 个键不符。失败位置与预测的机制一致（C5 日志）：`test_task.exception()` 在 `test_1.py:993` 抛出 CancelledError，涉及 4 个经 `self.run_app` 的键；`:1121`（pending_handler_responds）和 `:1259`（cancellation_suppressed）也是 CancelledError；`:1208` 的 `client_finished` 为假。`test_shutdown_close_idle_keepalive` 没有拦下它，因为该键断言的就是 `t.cancelled()`；这和我初判的推断一致。目标键仍然 PASSED【实跑】 | 确认。拒绝有公开依据（`CHANGES.rst:2076` 的 #3805，以及 `docs/web_advanced.rst:948-967`），而且解题者本地就能跑这些测试，属于错误修复，不是规格争议 |
| 7 | gold 在 R7 上把“报告”改成了“抛出”（analysis §5） | 诊断 `a1c1c_gold.json`：`outcome: raised`（`RuntimeError: cleanup failed`），处理器 0 次；base 是 `reported`【实跑】 | 确认 |
| 8 | 时序键 `test_shutdown_handler_cancellation_suppressed`：首个请求没有预热，也不重试，与 `site.start()` 竞态；来源宿主机新旧两次都失败（delta 第 11 条） | 原始记录第 6 行【原始记录】：新提交 `1 failed, 55 passed`，旧提交 `2 failed, 54 passed`，两次都是这个键，错误为 `ConnectionRefusedError: [Errno 111] Connect call failed ('127.0.0.1', PORT)`，发生在第一个请求，该键耗时 0.51 s。0.5 s 时的 `/stop` 请求成功了（否则服务不会停下来，测试也不会在 0.51 s 结束），说明失败只发生在服务端 listen 之前——机制成立。测试代码也确认只有这个键没有预热：`:1217-1227` 的 `test_resp` 立即发请求；其它用例都先 `sleep(0.5)` 或 `sleep(1)`，或者对 ClientConnectorError 重试（`:953-966`） | 同意机制，同意 watch；补充环境事实（§3 第 1 条） |
| 9 | 历史把这个键写成“超时”，不准确（delta 第 11 条） | 原始记录里是 ConnectionRefusedError，不是超时。`known_issues.json` 的 `timing_sensitive_key_watch` 写的是“FAILED（超时）” | 同意 |
| 10 | 历史 R10 说“测试不需要网络”，措辞有误，回环是必需的（delta 第 6 条） | TestShutdown 用真实端口，`test_sigint`/`test_sigterm` 会起子进程 | 同意 |
| 11 | 跨题包含：22a12cc2 的公开工作树逐字包含本题 gold、目标测试和 changelog；“反方向不成立”（check 5） | 我初判独立核对过同样的三处位置（`web.py:519-531`、`tests/test_run_app.py:909-923`、`CHANGES.rst:190-194`）。**补充**：“反方向不成立”只对 22a12cc2 这一对成立。更老的题（4075c653、240da100、61833518）的修复是否以改写后的形式存在于本题工作树，只靠扫描的“≥80% 逐字行”规则判断，没有核实 | 同意，补范围说明 |
| 12 | 4075c653（3.9.0b0）的 base 在 `web.py:522` 仍是旧写法（analysis §8） | 核对了该题公开包的 `web.py:522` 和 `__init__.py:1` | 同意 |
| 13 | gold 的一个边角：主任务协程内部以 KeyboardInterrupt/SystemExit 结束时，gold 会在 finally 里再抛一次（analysis §5） | 静态推断成立：`run_until_complete` 对已完成的任务会重新抛出 `result()`，而 `suppress` 只压 CancelledError。触发条件大致是 `handle_signals=False` 时收到 Ctrl+C。这条路径不在任何测试里，影响小 | 同意 |
| 14 | “同一个键的耗时差不超过 0.01 s”（analysis §4(e)，check 14） | 14 次 current 运行里，TestShutdown 的大多数键确实不超过 0.01–0.02 s；但 `close_websockets` 是 1.02-1.08 s，`test_sigint` 是 0.21-0.41 s，`test_sigterm` 是 0.20-0.38 s【日志】 | **修改措辞**，不影响结论 |
| 15 | check 16：非 gold 候选的正式交付没有证据，记为 unknown | 今天 3 个非 gold 补丁都在 grader 侧经 `git_apply` 应用并投影：`classification: projectable`，`included_paths: [aiohttp/web.py]`，`ignored_paths: []`【实跑】。但这不是 actor 冻结后再投影的路径 | 部分更新：grader 侧有了证据，actor 侧仍 unknown |
| 16 | 处置把静态候选与剩余条件分开，不把环境已验当成质量合格（card §1、§5，disposition） | disposition 写明 `prior_environment_disposition` 只是环境层面的结论。actor 待验项单列：devcheck 用的是桩提示（`messages_000.json` 是 “Devcheck run: execute exactly the tool calls…”）；gold 没有在 agent 身份下跑过 | 同意 |

## 3. 反查：主审可能没想到的范围

1. **时序键失败时的环境。** 原始记录显示，来源执行在 `/home/gcpuser/buckets/local_repoeval_bucket/repos/aiohttp_1c1c…` 这个本地 checkout 里进行，用的是它自己的 `.venv`，插件为 `asyncio-0.25.0`，不在 `namanjain12/aiohttp_final` 镜像里（发布镜像中是 `/testbed`、pytest-asyncio 0.25.2）。容器环境里这个键全部通过：
   - RH2 评分 17/17：14 次 current 运行，加上今天 gold、C1、C3 各 1 次；C5 在这个键上的失败来自候选本身，失败位置 `:1259`，原因是 CancelledError；
   - M3 独立 runner 在来源镜像上 2/2；
   - devcheck 公开文件全跑 2/2。

   所以翻转风险主要来自换环境（宿主、内核、并发负载），同一 RH2 容器环境下没有观测到随机抖动。这让我更倾向于 watch，而不是修订。
2. **同一个键还有第二个静态余量，没有观测到。**
   - 时间线：handler 约 0.4 s 被取消，但吞掉了这次取消，再睡 2 s；`shutdown_timeout=2` 从约 0.5 s 起算（`web_protocol.py:263-275`）。
   - 所以 handler 必须在大约 2.5 s 前写下 `DONE`；实测耗时 2.40-2.41 s，与此吻合。
   - 这只是静态推断，但属于同一个观察对象，应一并列入 watch。
3. **C3 很自然，这放大了漏测的影响。** cancel 加 `gather(..., return_exceptions=True)` 是“取消并等待”的惯用写法。公开读者也把“第 d 类实现可能悄悄丢错”列为风险（`public_read.md` §2）。因此漏测对训练 reward 的影响比对诊断用途大（见 §0 第 2 条）。
4. **公开依据的强弱。**
   - `CHANGES.rst:2440`（#3497 “Ignore done tasks when cancels pending activities on web.run_app finalization”）是 C1 写法的公开旁证，进一步支持 C1 是合法替代解。
   - `docs/web_advanced.rst:1119` 那句 “Ensure any exceptions etc. are raised.” 是用户代码示例里的注释，对 R7“不应丢失”只是弱旁证。强依据是 base 的旧行为：base 会报告这类错误（诊断 `a1c1c_base.json` 为 reported）。
5. **C6 的外部效果。**
   - C6 的写法：临时换掉异常处理器，包住对 main task 的报告。
   - 默认处理器和用户自己装的处理器都收不到这次重复报告，所以从外部看，它与 gold 基本相同；只有覆写了 `call_exception_handler` 的 loop 子类，才会看出区别。
   - 因此判它为 0 有依据，但偏严。如果真实轨迹中出现 C6 这类写法得 0，按补充规则 1 只作“疑似规格争议”的线索，原始 reward 保留。主审的结论与此一致，这里只是把理由写全。
6. **修订设计的细节**（如果将来要修订）。
   - 新键应使用 `patched_loop` 加 `stopper`，不要用真实 socket，以免引入新的时序键。
   - 判定“被报告”时应检查 `call_args` 里的 `exception` 是否就是那个异常对象，不要用消息文本匹配，以免限制合法实现的措辞。
   - 修订后要按 gold、C1、C3、noop 复跑，预期依次是 1、1、0、0。
   - 这会改变期望映射，也会打破“隐藏测试等于上游文件”的性质，属于 T0 改动，由用户决定。
7. **不需要额外实验的静态确定项**：
   - 我初判的候选 D（删掉 `_cancel_tasks` 里的全部报告）会被 `test_run_app_cancels_failed_tasks` 的 `assert_called_with`（`:856`）拦下；公开读者也作了同样预测。
   - C6 会被目标键拦下。

   两者都不必实跑。

## 4. 失败键模式与规格争议线索（补充规则 1）

- **C5**：7 个 TestShutdown 键失败。这是违反公开文档所写停服顺序的错误修复，不是规格争议。
- **C1、C3 都得 1**：原始 reward 保留。C3 的 1 反映的是漏测，不能倒过来据此给 C3 改分。
- **误拒**：今天所有实跑中，没有“合理解被判 0”的模式，本题目前没有误拒证据。

## 5. 与我初判不同的地方

- **时序键**：初判只从 shutdown 截止时间推算出约 0.1 s 余量（静态），漏掉了启动竞态，也没有看来源原始记录。现在采纳主审的机制（有来源记录中 2 次失败为证），并补上“失败环境是非镜像宿主”这一事实。严重度从“低”调为“watch，不阻塞”。
- **候选预测**：A、B、C 的预测都被实跑确认（C1、C3、C5 分别对应 A、B、C）。附录 B 脚本的预期（base 和 A 报告、gold 抛出、B 丢失）与协调者诊断的结论一致；协调者用的是同一场景的另一份脚本（消息为 “cleanup failed”，`handle_signals` 取默认值）。
- **其余判断不变**：包括目标键与题面一致、无误拒、无非 PASSED 键、跨题包含、环境敏感键、开发摩擦（`/testbed` 之外的脚本导入失败，历史 known_issues 也有同样结论）。

## 6. 处置、分歧与最小后续实验

- **处置**：同意主审。`screening_record` 建议做三处小改：
  1. check 26 的证据级别改为当前 CPU 实跑，C3 得 1 且错误丢失；
  2. check 14 的耗时措辞按 §2 第 14 条修正；
  3. check 16 补上 grader 侧非 gold 补丁 projectable 的证据。
- **分歧**：
  - 与主审没有实质分歧，只是对 C3 漏测严重度的用途区分作了补充。
  - 与历史在“时序族已关闭”上有措辞分歧，保留为未解决：我同意主审改为 watch。历史自己也写了“训练规模并发下未测”作为残余，所以两者差别主要在标签。
- **C3 漏测的处理**：诊断用途下不改 reward，用已有诊断脚本 `aiohttp_1c1c0ea3_cleanup_error.py` 作为非 reward 的旁路检查，在探针阶段标出 C3 类解。只有要把本题用作训练 reward 时，才由用户决定是否按 §3 第 6 条修订。
- **最小后续实验（唯一优先）**：同一宿主上 4–8 路并行评分 gold，跑若干轮，统计 `TestShutdown.test_shutdown_handler_cancellation_suppressed` 的翻转率。一旦翻转，所有候选包括 gold 都判 0。这是本题剩余的主要 reward 风险。
- **仍然开放的项**：actor 真实题面消息的捕获；非 gold 候选经 actor 冻结后再投影的交付，这两项属于各题共性。
