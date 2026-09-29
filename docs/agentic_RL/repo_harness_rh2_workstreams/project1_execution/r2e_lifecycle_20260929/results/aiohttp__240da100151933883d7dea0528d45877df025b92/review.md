# aiohttp__240da100 独立复核（第二步）

独立复核者，R2E 单题闭环试行，2026-09-29。第一步初判保存在同目录的 `reviewer_initial.md`，本文在读过公开读者产物、主审产物、历史引用和今晚新机器的实跑后写成。全程没有运行项目代码或容器；文中写"执行证据"的都来自协调者已有的运行原件，写"静态"的是源码推断。

路径缩写（都相对仓库根）：

- `LIFE` = `runs/r2e_lifecycle_20260929`；`INV` = `LIFE/inv/aiohttp_240d`；`DC` = `LIFE/devcheck/aiohttp__240da100151933883d7dea0528d45877df025b92`
- `HT` = `runs/r2e_static_prep_20260924/v3/private/aiohttp__240da100151933883d7dea0528d45877df025b92/hidden_tests/test_1.py`
- `W` = `runs/r2e_static_prep_20260924/v3/public/aiohttp__240da100151933883d7dea0528d45877df025b92/worktree`
- 主审产物：`ABH` = `analysis_before_history.md`，`OFD` = `old_findings_delta.md`，`CARD` = `card.md`，`SR` = `screening_record.json`（都在本目录）

## 0. 结论

- **同意**：处置 `needs_repair`；严重度 S1，三条根因是 T2c（静态）、T2b（DG1 实跑 1.0）和 v1 §4 第 4 步（WR1 实跑 1.0）。R-c 两项必做，R-a 可选；T5、P4、X1 的登记也都同意；v1 四项用途同意主审（训练和留出评测对当前版本都是 no）。
- **修改**：只有两处小改，都不改变结论：
  1. WR1 判 S1，稳固的依据是"破坏了有文档的常用行为"：`pcheck_WR1.json` 实测直连目标变成 `('localhost:1234', 1234)`。主审另一条理由"https CONNECT 显式端口属于同一核心要求的另一个实例"至今只是源码推断，要等 R-c 第 2 项验收时拿 WR1 实跑才能坐实。
  2. 主审用"能同时挡住 WR2"来说明为什么选 CONNECT 断言而不选 `test_host_port`，但 WR2 本身没有跑过。建议把 WR2 加进验收批次（见 §5）。
- **保留（与主审一致，不另加）**：R-a 不并入本轮修订；`test_host_port` 不作为必做项，只作可选补充。
- **修订可以按主审 `ABH` §10 / `CARD` §6 开做**：R-c 两项合并成一轮，键集为 35；验收批在主审所列候选之外加跑 WR2。
- 没有发现新的高影响问题。

## 1. 主审决定性主张逐项核对

| # | 主审主张 | 我核对的原件 | 引用是否支持；证据是否对应本题、当前材料和对应身份 | 结论 |
| --- | --- | --- | --- | --- |
| 1 | T2c：唯一的目标断言就是题面示例的字面值 | `HT:570-584`，题面 `user_prompt.txt:18-24, 29-31` | 支持。这是纯静态判定，与我初判 §5 一致 | 同意 |
| 2 | T2b：DG1 正式评分 1.0 | `INV/ledger_DG1.jsonl:1`：`apply_ok=true`，投影为 `aiohttp/connector.py`，33 个键全部解析，reward 1.0；`INV/logs_DG1/…_4f82b581.eval.log:10,16,213`：APPLY_RC=0，目标键 PASSED；`INV/pcheck_DG1.json`：两个 8080 端口的用例报 BAD | 支持。补丁确实交付、目标测试确实执行、结果完整。镜像是 `a6dee334…`（配方 `r2e_derive_v1+sysconfig_v1`），grader profile 是 `3ec1bfa8…`，材料 v3（隐藏测试树 `b74735a5…`），都对应当前环境。`INV/aiohttp_240d_DG1.patch` 与本目录 `cands/` 下的同名补丁 sha256 相同（`efa10536…`） | 同意 |
| 3 | 第 4 步：WR1 正式评分 1.0，判 S1 | `INV/ledger_WR1.jsonl:1`：投影为 `aiohttp/client.py`，reward 1.0，33 个键；`INV/pcheck_WR1.json`：三个带端口的 URL 因 host 报 BAD，直连目标 `('localhost:1234', 1234)` 报 BAD | 支持"破坏直连显式端口和 host/port 语义"。https CONNECT 的部分仍是推断，`pcheck` 没有测 https；主审在 `OFD` §2 里如实写明了 | 同意 S1，理由按 §0 第 1 点收紧 |
| 4 | T5：两个死键；SC1 得 1，说明最可能出现的顺手改动不受罚 | `INV/logs_SC1/…_68d7cf9a.eval.log:34-94, 250-252`：`test_tcp_connector` 的失败点从 `connector.py:290` 的 TypeError 变成 `protocol.py:650` 的 AttributeError，状态仍是 FAILED；reward 1.0 | 支持。这正是我初判里 C2 的预测 | 同意 |
| 5 | P4：题面示例原样跑不起来 | `DC/orig/captures/literal_example_probe.out`：先 ImportError，后 TypeError，`req.path` 仍是 `'/path'`；`repro_port_mocked.out` 在 base 上 rc 1，`DC/private_control.log` 里 gold 下 rc 0 | 支持。这是 actor 身份（`env.out`：uid 54321）走正式启动路径得到的结果 | 同意 |
| 6 | 环境不是阻塞项 | `LIFE/env_verify/ledger_noop.jsonl:3`：0.0，32/33，只差目标键；`ledger_gold.jsonl:3`：1.0，33/33；`DC/devcheck.log`：13 项检查全为真，预检三项 ok；`DC/orig/attempt.json` 的 `stages.sanitize_and_init.git_sanitize`：REFS_REMAINING、REMOTES、REFLOG_ENTRIES、UNREACHABLE_OBJECTS 都是 0 | 支持。`env_verify` 下其它账本（ledger4、l0、l1、l2）里没有本题的行 | 同意 |
| 7 | 旧的 `environment_qualified` 只是环境层结论；处置改为 `needs_repair` | 历史 `r2e_env_repair_20260924/tasks/aiohttp__240da100…/findings.md:3,12` 与该处 `screening_record.json`：旧审查只做了环境核对 | 支持。主审没有把"环境已验"当成质量合格 | 同意 |
| 8 | 证据分层 | `pcheck` 以 root 在一次性容器里运行（`kind=private_behavior_check_not_grading`），主审只把它当违例证据；旧机器的 3+3 次运行记作 superseded（`SR.recipe_ref.superseded_environment`）；M3 记作独立 runner | 没有把私有对照、独立 runner、评分容器和真实 actor 混用。`pcheck_try1/` 按协调者说明作废，我没有使用 | 同意 |

## 2. 协调者指定的三个重点

### 2.1 X1（本题 gold 与新测试逐字出现在 aiohttp `61833518` 的公开初态）

- **已登记**：`SR.issues` 的 I7（`scope=repo:aiohttp`）、`SR.checks["5"]=issue`、`CARD` §3 与 §4。主审引用的行号与我第一步核对的一致：`61833518` 公开工作树的 `aiohttp/connector.py:597-600` 和 `tests/test_connector.py:1063-1080`。
- **影响的用途**：
  - **留出评测**：已写进 `SR.usage.v1.heldout_candidate`，要求与 `61833518` 等同仓题分在同一组。按 D3 按仓库划分，这一点自动满足。如果将来改按时间划分，`61833518` 若进训练集，其初态就含本题答案，违反 v1 §2 "训练集初态不含其答案"。
  - **训练**：I7 的去向"训练时控制重复采样"已写。
  - **能力比较（小补充）**：若参与比较的某个模型训练时用过 `61833518`（或其它 aiohttp 题），本题的结果就不再是独立证据，比较报告要标注或剔除。主审的 `capability_comparison` 条件里没提这一点，建议补一句。
  - **问题定位**：不受影响。
- **反向命中**（扫描称 `61833518` 的 gold 唯一新增行出现在本题工作树）：主审和我都没有核，因为要读 `61833518` 的私有 gold。它不影响本题，属于 `61833518` 自己的 X1 登记，应由该题的主审或复核核对。
- **3.x 后继测试**（`1c1c0ea3`、`22a12cc2`、`4075c653`）：同意主审"弱关联，登记即可"。它们换了 API，不是本 base 的现成答案。

### 2.2 R-a 与两个 FAILED 死键（T5）

我与主审一致：记 T5，R-a 可选，本轮不并入。依据如下：

- **执行证据**：SC1 是我初判里的 C2，即 gold 加上给 `TCPConnector._create_connection` 补的 `@asyncio.coroutine`。它得 1.0，死键仍是 FAILED。这是解题者照题面示例用真实循环跑时最可能顺手做的改动，已证明不会受罚。要让死键翻成 PASSED，还得同时修 `parsers.py:246` 的 StreamWriter 兼容和 `client.py:512` 的 `create_task(loop=)`，属于越界移植。
- **先例区别**：我初判引 scrapy `9a15fcf8` 作 R-a 先例，这里收窄。历史 `known_issues.json` 的 `expected_non_passed_keys` 族写明：那两个键"可被更完整的修复翻成 PASSED——实测 over-fix 候选 7/7 PASSED 却 reward 0"，是题内修复会被误拒，所以 R-a 必做。本题没有这种题内翻转，不满足同样的前提。v1 §5 也写了"没有误拒案例的修订，不必专门造一个"。
- **触发条件**：主审设的"真实候选让死键翻转时改为必做"（`SR.revision_proposals[2].trigger_to_required`）是合适的。
- **将来若做 R-a**：按主审方案删掉 `HT:247-289` 与 `HT:17` 的导入，顺带去掉对 base 测试辅助的依赖（I9）；验收时 SC1 仍须为 1。

### 2.3 R-c 两项能否同时挡住 DG1、WR1，且不误拒 AL1、SC1

两条新断言见 `CARD` 附录 A：

- 第 1 项：`test_request_port_other_url`，经 `connect()` 请求 `http://www.python.org:8080/some/path`，断言 `req.path`。
- 第 2 项：`test_https_connect_port`，经 `_create_connection()` 请求 `https://www.python.org:8443`，断言 CONNECT 目标是 `'www.python.org:8443'`。

各候选的预期结果：

| 候选 | 当前材料 | 第 1 项新键 | 第 2 项新键 | 合并后得分 |
| --- | --- | --- | --- | --- |
| noop | 0（执行） | FAILED。`pcheck_none` 对同一 URL 实测得到 `'http://www.python.org/some/path'` | PASSED（静态）。base 的 CONNECT 公式 `connector.py:361` 本来就对；现有 `test_https_connect` 在 noop 下 PASSED | 0 |
| gold | 1（执行） | PASSED（`pcheck_gold` 同 URL） | PASSED（静态） | 1 |
| DG1 | 1（执行） | **FAILED**（`pcheck_DG1` 同 URL 丢了端口） | PASSED（DG1 不碰 CONNECT） | **0** |
| WR1 | 1（执行） | PASSED（`pcheck_WR1` 的 path 正确） | **FAILED**（静态：得到 `'www.python.org:8443:8443'`，走到断言才失败，状态是 FAILED 而不是 ERROR） | **0**（待验收实跑） |
| WR2：在 `_create_connection` 里先做 `req.host = req.netloc` | 1（静态） | PASSED | FAILED（静态，同 WR1） | 0（**未跑，建议补**） |
| AL1 | 1（执行） | PASSED（`pcheck_AL1`；8080 不是默认端口） | PASSED（CONNECT 不变） | 1 |
| SC1 | 1（执行） | PASSED（`pcheck_SC1`。隐藏测试用 `_fake_coroutine` 普通生成器；SC1 下同样写法的 14 个 ProxyConnectorTests 全部 PASSED，见 `logs_SC1` 的 summary） | PASSED（SC1 下现有 `test_https_connect` PASSED） | 1 |
| AL2：gold 加 `if not req.ssl:` | — | PASSED | PASSED | 1（静态） |
| gold 加上在 `client.__all__` 导出 `ClientRequest`（让题面 import 能用，即公开读者的 U4） | — | PASSED | PASSED | 1（静态，无副作用） |
| WR3 / WR4（用 Host 头，或用 `urlsplit(req.url).netloc`） | 1 | PASSED | PASSED | 1。只在边缘输入上错，记 T3（I6），合理 |
| 总是补端口 | 0（旧键挡住） | — | — | 0。旧的公开测试已挡住 |

结论：

- **两项合起来足以挡住 DG1 与 WR1**：第 1 项挡 DG1，第 2 项挡 WR1 和 WR2。
- **对 AL1、SC1、AL2 都不构成误拒**。第 1 项同时覆盖了 `connect()` 与 `_create_connection()` 两个入口（原键走后者），不会误拒改写仍放在 `_create_connection` 里的实现。
- **第 2 项没有扩大需求**：它断言的是 base 已有、公开 `test_https_connect` 已测过（默认端口）的 `host:port` 公式，只换成非默认端口；noop 在这个键上也会通过。
- **测试代码核对**：`HT:14` 已导入 `ClientResponse`，两个新键名在 `HT` 里不撞键；https 用例的第二次 `create_connection`（升级 TLS）也由 `_fake_coroutine` 接住，写法与公开 `test_https_connect` 相同。

## 3. 反查：主审可能没想到的范围

- **公开测试挡不住 WR1**：`W/tests/test_client.py` 在本环境一收集就 SyntaxError（`W/tests/test_client.py:647` 的 `asyncio.async(`；`DC/orig/captures/public_client_file_collect.out` 实测，rc 2）。所以 WR1 这类改动在解题者能跑的公开测试里完全看不出来：`ProxyConnectorTests` 的 13 项照样全过。R-c 第 2 项是唯一的保护。主审在 `ABH` §3.1 的 R8 行和 `CARD` §2 都写了"在 3.9 下不能收集"，这一点只是加重了第 2 项的必要性。
- **公开读者的疑义都已消除或被刻意保留**：
  - U4（题面从顶层导入 `ClientRequest`）：不影响评分，因为 `HT:14` 从 `aiohttp.client` 导入。
  - U1（显式默认端口）、U2（https 的 `req.path`）、U3（CONNECT 的 Host 头）：隐藏测试都没断言，R-c 也刻意不测。
  - 这些疑义都没有被当作题目有问题的证据。
- **没有"先看答案再说成显然"的情形**。主审说"修法几乎直接给出、只需改一个词"（`ABH` §4(c)），这是对难度的判断，并没有拿它论证任何隐藏要求；它另写了"训练价值另评"，是恰当的。
- **"可探针"的条件与静态候选分开写了**（`CARD` §7）；**环境已验没有被当成质量合格**（`OFD` §1 第 1 条）。
- **历史旧结论"无影响判分的缺口"**（历史 `findings.md:12`）：主审按 v1 推翻了它，理由是旧审查只查环境、没评测试强度。我同意。

## 4. 我初判的更正，以及被实跑证实的部分

- **证实**：初判的四个静态预测全部命中。
  - C4 即 DG1：1.0；C3 即 WR1：1.0；C1 即 AL1：1.0。
  - C2 即 SC1：1.0，且失败点正如预测移到了 `protocol.py:650`。
  - P4 的 ImportError → TypeError 链由 devcheck 实测。
- **更正 1（事实错误）**：初判 §9 写"`python -m pytest tests/test_connector.py -q` 预期 31 passed、2 failed"，这是错的。公开文件只有 32 项，隐藏文件多出的正是目标键；实测是 30 passed、2 failed（`DC/orig/captures/public_connector_file.out:279-281`）。
- **更正 2（补充限定）**：初判说 C3 "破坏公开旧测试 `test_host_port`"。这个公开依据成立，但该文件在本环境跑不起来（见 §3），解题者无法靠它发现问题。
- **更正 3（改采主审方案）**：
  - R-c 第 2 项改用主审的 CONNECT 显式端口断言，因为它还能挡 WR2；我原提的 `test_host_port` 降为可选补充，不建议必做。
  - R-c 第 1 项采用主审版本（URL 为 `/some/path`，走 `connect()`）。它与我的实例等价，且同一 URL 已在 `pcheck` 里对 6 种情况实跑过。
- **更正 4（用途口径）**：训练候选和留出评测，初判写的是 conditional；现在同意主审，对当前版本写 no，修订验收后再重判。当前版本有已证实、未处理的 S1，写 no 比写 conditional 更准确。

## 5. 修订开做的补充事项与最小后续实验

1. **按 `CARD` §6 实施 R-c 两项，合并为一轮**。键集为 35；期望映射新增两键，都是 PASSED。
2. **验收批**：主审已列 gold、noop、DG1、WR1、AL1、SC1；**补跑 WR2**。WR2 的补丁描述：在 `aiohttp/connector.py` 的 `ProxyConnector._create_connection` 里、第 342 行 `req.path = …` 之前插入一行 `req.host = req.netloc`，第 343 行仍用 `host=req.host`。预期：当前材料得 1；修订版得 0，不符的键是 `ProxyConnectorTests.test_https_connect_port`，CONNECT 目标变成 `'www.python.org:8443:8443'`。这一跑是为了坐实"选 CONNECT 断言而不选 `test_host_port`"的理由，并把 WR1 的 CONNECT 破坏从推断变成执行证据。
3. **验收判读**，沿用主审的合并验收：
   - gold 与 AL1 为 1；SC1 为 1。
   - noop 为 0，不符的键恰好是 `test_request_port` 与 `test_request_port_other_url`。
   - DG1 为 0，只差 `test_request_port_other_url`；WR1 与 WR2 为 0，只差 `test_https_connect_port`。
   - 没有 missing 或 unexpected 键。
   - 每次都核对补丁已应用、投影正确、35 个键全部解析。
4. **R-a 不并入本轮**，保留主审的触发条件。
5. **登记与交接**：
   - X1 由协调者在划分登记里把 aiohttp 五题绑在同一侧；
   - 能力比较条件补上 §2.1 的一句；
   - 反向命中交给 `61833518` 的审查者核对。
6. **Codex 复核修订**：修订版本只作为"标明版本的自建评测"。

探针就绪差距同意 `CARD` §7。当前未满足的是：R-c 实施与验收（协调者）、Codex 复核、X1 的划分登记（协调者）、真实题面渲染与真实模型求解（批次共性）。环境、devcheck、答案不可达都已满足（§1 第 6 条）。

## 附录：本步实际读取范围

- **本目录**：`public_read.md`、`commands.json`、`analysis_before_history.md`、`old_findings_delta.md`、`card.md`、`screening_record.json`（全部字段）；`cands/` 下 4 个补丁（与 `INV` 下同名补丁比对了 sha256）。
- **历史**：
  - `runs/r2e_static_prep_20260924/v3/history/aiohttp__240da100…/refs.json`；
  - `r2e_env_repair_20260924/tasks/aiohttp__240da100…/findings.md` 与 `screening_record.json`；
  - `known_issues.json` 中 refs 所列 5 族，另加 `expected_provenance_mixed`；
  - `decisions.md`、`results_20260924.md`、`packages/p1/README.md` 的相关行（grep）；
  - `repros/aiohttp__240da100….py` 前 45 行。
- **新机器运行原件**：
  - `LIFE/env_verify/`：`ledger_{noop,gold}.jsonl` 第 3 行；其余 env_verify 账本只查了是否含本题的行（都不含）。
  - `INV`：`ledger_{DG1,WR1,AL1,SC1}.jsonl` 第 1 行；四份 eval 日志（grep，SC1 另读第 34–121 行）；`pcheck_{none,gold,DG1,WR1,AL1,SC1}.json`；`private_check_9_2.py`；`run.sh`。
  - `DC`：`devcheck.log`、`private_control.log`；`orig/captures/` 下的 `env`、`import_version`、`literal_example_probe`、`repro_port_mocked`、`r2e_preflight`，以及 `public_proxy_tests` 结尾、`public_connector_file` 的 grep、`public_client_file_collect` 结尾；`orig/attempt.json` 的 image、overlay、image_facts、git_sanitize；`orig/stub/requests/messages_000.json` 的首条用户消息。
- **公开包复核**：`W/tests/test_client.py:640-650`。
- **未读**：`pcheck_try1/`、`_old_noenv_*`、各 `*.diagnostics.json`、`trajectory.jsonl`、`private_control.json` 正文、`run.log`、`private_check.py`、`61833518` 的私有包。
