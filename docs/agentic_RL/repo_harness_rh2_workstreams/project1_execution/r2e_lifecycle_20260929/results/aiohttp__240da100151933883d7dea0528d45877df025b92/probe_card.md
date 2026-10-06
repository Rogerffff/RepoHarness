# aiohttp `240da100` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`R` = `L/results/aiohttp__240da100151933883d7dea0528d45877df025b92`（本题全部审查产物；没有旧审查卡），`F` = `runs/r2e_lifecycle_20260929/formal_v7`（账本 `F/ledgers/ledger_{gold,noop,s1,s2,s3,s4,s5}.jsonl` 各 1 行，完整日志在 `F/remote/<槽位>_logs/`），`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v7/aiohttp__240da100151933883d7dea0528d45877df025b92`（v7 镜像），`D0` = `runs/r2e_lifecycle_20260929/devcheck/aiohttp__240da100151933883d7dea0528d45877df025b92`（修订前 v3 镜像），`INV` = `runs/r2e_lifecycle_20260929/inv/aiohttp_240d`（协调者实跑）。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：probe_ready**。今晚新审题里第一道走完全流程的题（公开读 → 主审 → 协调者实跑 → 独立复核 → 修订 → Codex 复核 → 正式落地）。五条都满足：正式评分 7 行全部与期望一致（正对照 gold，缺省预算）；两次 devcheck（修订前 v3 镜像、v7 镜像）各 13 项全真；三条 S1（唯一目标断言只用题面示例、退化候选 DG1 得 1、破坏 host/port 语义的 WR1 得 1）按 R-c 两项修订，经独立复核、Codex 复核与正式评分验收；复核要求坐实的"WR1 / WR2 把 CONNECT 目标改坏"已由正式日志确认；预检通过。
- **材料**：修订单 v7 的 `r2e-mr-051`（`hidden_test_text_replace`，`test_1.py` `530b4631…` → `5ad37c35…`，在 `ProxyConnectorTests` 末尾加两个测试）、`r2e-mr-052`（`expected_file_replace`，`5444ee2a…` → `28da8c15…`，33 → 35 键，新增 `ProxyConnectorTests.test_request_port_other_url`、`ProxyConnectorTests.test_https_connect_port`，均 PASSED；两个期望 FAILED 的键不变）；pins v8 `eaa084e8c3b8…`；评分日志头 `RH2_SETUP_HIDDEN_TESTS_TREE=0ca24119…` 等于当前评分包摘要。派生镜像 `a86015aadba7`（`rh2-r2e-derived/aiohttp:240da1001519-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `c075da357402…`）。
- **题目版本**：标明版本的自建修订题（原题 + `r2e-mr-051/052`），不当原 benchmark 报；gold 在修订版上仍为 1。本题此前没有材料修订。

## 准入五条（README §3）

1. **正式评分**（`F/status.json` 本题 7 行 `match=true`）：

   | 候选 | 角色 | 期望 | 实得 | 不符键与失败断言（正式日志） |
   | --- | --- | --- | --- | --- |
   | gold（`connector.py:343` 的 `host=req.host` 改为 `host=req.netloc`） | 正对照 | 1 | 1（35/35） | — |
   | AL1：只在端口不是默认值时补端口 | 合理替代解 | 1 | 1（35/35） | — |
   | SC1：gold 加顺手补的 `@asyncio.coroutine` | 最可能的顺手改动 | 1 | 1（35/35） | 两个死键仍是期望的 FAILED（`test_tcp_connector` 的失败原因变为 AttributeError） |
   | noop | — | 0 | 0（33/35） | `test_request_port`：`'http://localhost/path' != 'http://localhost:1234/path'`（`test_1.py:584`）；`…_other_url`（`:602`） |
   | DG1：只在端口为 1234 时补 `:1234` | 触发反例，兼 §4 第 3 步退化探测（特判示例值，原版 1） | 0 | 0（34/35） | `…_other_url`：`'http://www.python.org/some/path' != 'http://www.python.org:8080/some/path'`（`:602`） |
   | WR1：让 `ClientRequest.host` 带上端口（改 `client.py`） | 触发反例（第 4 步，原版 1） | 0 | 0（34/35） | `…_https_connect_port`：`'www.python.org:8443:8443' != 'www.python.org:8443'`（`:629`） |
   | WR2：在 `_create_connection` 里就地 `req.host = req.netloc` | 触发反例（第 4 步，原版试跑 1） | 0 | 0（34/35） | 同 WR1（`:629`） |

   "原版"指修订前材料上的协调者正式评分（`INV/ledger_{DG1,WR1,AL1,SC1}.jsonl` 第 1 行，均 1.0、33/33，镜像 `a6dee334`）；WR2 原版只有试跑（`R/trials/cur_WR2.json`）。各行 `git_apply` 成功、投影只含候选改的文件、测试段完整、日志不截断、键集相等（无 missing / unexpected）；补丁摘要等于 `R/cands/` 本地副本（`F/remote/slots_manifest.json`）。**35/35 指期望匹配，不是全部测试 PASSED**：两个死键仍是期望的 FAILED（Codex 第 27 行）。账本 `phases.grader_trusted_setup` 11–18 s，测试段 3–4 s。
2. **devcheck**：v7 镜像（`D/orig/attempt.json`，`a86015aa…`）13 项 checks 全真，8 条命令都符合预期；修订前 v3 镜像（`D0/orig/attempt.json`，`a6dee334…`）同一组命令同样全过（修订只动评分包，开发侧不受影响）。agent 身份下：`repro_port_mocked` 在 base 上经 `connect()` 与 `_create_connection()` 都得 `'http://localhost/path'`（rc 1，预期内）；题面示例原样跑先 ImportError、再 TypeError（P4）；公开 `ProxyConnectorTests` 13 passed；整个 `tests/test_connector.py` 30 passed / 2 failed（两个走真实 socket 的死键用例）；`tests/test_client.py` 一收集就 SyntaxError（rc 2）。私有 gold 对照（root、断网）：`repro_port_mocked` rc 0；另两个非零（`public_connector_file` rc 1、`public_client_file_collect` rc 2）与 base 同因，预期内。
3. **S1 处理**：R-c 两项合并一轮（`R/revision_plan.md` §1–§3，第 12–118 行）：①`test_request_port_other_url` 换主机、端口、路径，走公开 `connect()` 入口（§4 第 2 步的非示例实例，堵 DG1）；②`test_https_connect_port` 把公开 `test_https_connect` 的默认 443 换成显式 8443，断言 CONNECT 目标只带一次端口（§4 第 4 步，堵 WR1 / WR2；是回归断言，noop 也通过）。独立复核同意，并要求加跑 WR2（`R/review.md` 第 12–20、114 行）。Codex 通过（`L/codex_reviews/review_revision_aiohttp_240d.md`），**限定**：①第 2 项的"唯一保护"只指当前验收集里拦截 WR1 / WR2 的唯一键（第 12 行）；公开 `test_host_port` 在 3.9 下收集不了，解题者自己看不到这类破坏；②WR3 / WR4 等 T3 范围未实跑，不能宣称所有错误都已拦截（第 29 行）；③正式评分完成前不授予资格（第 43 行）：今晚 7 项正式矩阵已完成，补丁投影、测试树摘要、严格键集按第 31 行核对通过。
4. **公开包干净**：两次 devcheck `r2e_preflight_ok`（三项 ok）；git sanitize 后 refs / remotes / reflog / 不可达对象都为 0；修订只动评分包，本题公开包行（`docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/public_bundles_v0.jsonl` 第 3 行）在 09-29 起各次摄入里逐字相同；两个新测试名与新 URL 在 v3 的 5 个 aiohttp 公开工作树里都没有命中（revision_plan 第 208 行）；题面与 gold 无逐行重叠（`runs/r2e_static_prep_20260924/statement_gold_overlap_scan.json`）。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛 |
| 能力比较 | yes | 开发路径与评分依据已核（目标键、两个死键都已解释）；按 `r2e-mr-051/052` 标明版本报告。若参与比较的模型训练时用过 `61833518`（或其它 aiohttp 题），本题结果不再是独立证据，报告要标注或剔除（`R/review.md` 第 43 行）。批次运行条件属链路 |
| 训练候选 | yes | 核心要求有直接断言：示例与非示例两个实例的 `req.path` 保留端口，另有无端口不补 `:80`、失败不改请求、认证头迁移、CONNECT 目标（默认与显式端口）回归键（revision_plan 第 192–199 行）；当前版本 noop 0、gold 1；§4 第 2 步（other_url）、第 3 步（DG1）、第 4 步（WR1、WR2）已做；T3、T5、X1 已登记。训练价值另看：修法只改一个词，难度低（`R/analysis_before_history.md` 第 159–164 行）；X1 要求控制同源重复采样 |
| 留出评测候选 | conditional | 差：① D3 仓库划分未定；`61833518` 初态含本题修复核心行与原目标测试的后继版本，`1c1c0ea3`、`22a12cc2`、`4075c653` 初态含目标测试名（X1），aiohttp 五题须整仓同侧，实际划分登记仍待落实（Codex 第 37 行）；② 若探针结果用于选模型、调提示或调配方即不再符合；③ 只能作标明版本的自建评测 |

## 剩余事项（已登记，不阻塞探针）

- **T5 死键（R-a 可选，本轮不做）**：`HttpClientConnectorTests.test_tcp_connector` / `test_unix_connector` 期望 FAILED，原因是 2014 年的代码与 py3.9 不兼容；SC1 证明最可能的顺手改动不受罚。若真实候选把死键翻成 PASSED（需越界移植），R-a 改为必做（`R/review.md` 第 48–55 行）。
- **T3 / 未覆盖**（revision_plan 第 201–208 行）：查询串、目标 URL 里的 `user:pass@`、自定义 Host 头；直连 `TCPConnector` 的显式端口目标、TLS `server_hostname` 没有直接断言（只改直连路径、不碰 CONNECT 的候选目前没有具体实例）。刻意不测：U1 显式默认端口（gold 保留、AL1 省略，两种都合理）、U2 https 的 `req.path`、U3 代理请求的 Host 头。
- **题面（P4）**：示例从顶层导入 `ClientRequest`（base 不导出），并用真实事件循环调 `_create_connection`，在 3.9 上报 TypeError；公开读者的 mock 复现能区分修复前后（devcheck `repro_port_mocked`）。
- **共享控制面**：隐藏测试导入 base 版 `tests.test_client_functional.Functional`，`tearDown` 调 `aiohttp.test_utils.run_briefly`；这两个文件评分时不重置，候选改坏会改变键状态（`R/screening_record.json` issue I9）。
- **解题侧**：无 pip、不联网；要在 `/testbed` 下用 `python -m pytest`；真实 socket 客户端 / 服务端在 3.9 不可用；`tests/test_client.py`、`tests/test_worker.py` 不能收集；初态脏树（来源镜像的 3.9 兼容改写：`aiohttp/{client,server,worker}.py` 已改、未跟踪的 `process_aiohttp_updateasyncio.py`）不能回退，census 基线已按初态处理（issue I8）。
- **X1**（issue I7；`runs/r2e_static_prep_20260924/cross_task_{gold,test}_scan.json`）：本题 gold 的唯一新增行出现在 `61833518` 初态；按 Codex 校正，那里是同一修复核心行及原目标测试的后继版本，不是整段逐字相同，也不含本轮新增的两个测试（第 39 行）。反向的单行命中（`61833518` 的 gold 行出现在本题初态）未核，归 `61833518` 自己登记。
- **后检（可选）**：私有行为对照 `INV/private_check_9_2.py`（从标准输入在 `/testbed` 运行；退出码 0 且无 BAD 行才算语义通过，`R/card.md` 第 177–191 行），可对得 1 的补丁抽查，结果与原始 reward 分列。
- **链路（共同项）**（`L/probe_chain_check.md` §0 第 9–20 行、§4 第 99–108 行；Codex `L/codex_reviews/review_probe_chain_20260929.md` 第 1–3 行"改后可以"）：
  - 求解入口换 `rh2/experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py`，`run_matrix.py` 按题选入口、评分带 `--image-overlays`（待改）；评分沿用 `replay_grade run` + 覆盖表（v7 正式评分即此口径）。
  - 接真实模型前先收口 Codex 的两项 P1：去掉静止屏障里以 root 执行的 git（第 9–31 行）；往返核对不一致、评分 fatal、清理未知时停止派发（第 33–41 行）。正式链直评的基线摘要问题可递延（第 43–51 行）。
  - GPU 机须载入同一 image ID（按 tag→ID 核对），否则本卡评分资格重出；账本 `env_qualification=absent`，能力统计前补接资格账本或单列（Codex 第 78 行）。
  - 模型实际收到的题面消息未对本题捕获。本机开销：rollout 从起容器到可信初始化完成约 18 s（devcheck `stages`）；评分可信 setup + 保护 11–18 s、测试段 3–4 s。

## 证据索引

- 本题审查产物：`R/{public_read.md,commands.json,analysis_before_history.md,old_findings_delta.md,card.md,screening_record.json,reviewer_initial.md,review.md}`（`card.md` 与 `screening_record.json` 的 v1 用途是修订前结论，已由本卡取代）
- 修订：`R/{revision_plan.md,revision_draft.json,trials/,cands/}`；正式条目 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v7.json` 的 `r2e-mr-051`、`r2e-mr-052`
- Codex：`L/codex_reviews/review_revision_aiohttp_240d.md` 第 1–43 行
- 修订前实跑：`INV/ledger_{DG1,WR1,AL1,SC1}.jsonl`、`INV/pcheck_*.json`；`runs/r2e_lifecycle_20260929/env_verify/ledger_{noop,gold}.jsonl` 第 3 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/`、`F/remote/*_logs/`、`F/remote/slots_manifest.json`
- devcheck：`D/orig/attempt.json`、`D/orig/captures/`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v7/summary.json`；`D0/`（修订前镜像）
