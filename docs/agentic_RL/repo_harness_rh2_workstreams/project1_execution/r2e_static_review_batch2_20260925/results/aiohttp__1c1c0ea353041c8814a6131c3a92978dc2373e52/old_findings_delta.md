# 旧主张核对：aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52

2026-09-25 · R2E 私有主审（静态）。本文件在 `analysis_before_history.md` 保存之后才写。

## 读了什么

**历史引用**：`v3/history/…/refs.json` 列出的全部文件，即：

- `r2e_env_repair_20260924/tasks/aiohttp__1c1c…/{findings.md, screening_record.json, facts.json}`
- `known_issues.json`：只看了本题所在的两个族，外加 `expected_provenance_mixed`
- `decisions.md`：E06、E09、E10、E18
- `results_20260924.md` 中本题所在的行
- `repros/aiohttp__1c1c….py`
- `packages/p1/README.md`

**为核实旧主张另外打开的原件**：

- 来源原始记录 `s2_r2e/raw/r2e_gym_subset_48_e8b9fcbc.jsonl` 中本题的 `execution_result_content`
- 历史探针 `runs/r2e_env_repair_20260924/p1/dev_probe/aiohttp__1c1c…/dev_probe.json`
- M3 `status_map.json`
- `runs/r2e_t0_batch2_20260924/reconcile/reconcile.json`

**仍然没读**：首批审查目录、Codex 复核目录、本批 README 与 `assignments.json`。

**历史的性质**：历史记录是环境审查，处置为 `environment_qualified`。它只回答环境与评分条件，没有做题意、测试覆盖和 gold 完整性审查。因此下文的"新增"项不算推翻历史。

## 逐条核对

| # | 旧主张（出处） | 判定 | 新的决定性证据 |
|---|---|---|---|
| 1 | 环境支持解题与判分；noop 只错目标键，gold 56/56，与 M3 逐键一致（findings "结论/依据"，R02/R08/R15） | 确认 | 共 7 次 noop，都是 55/56，只错 `test_run_app_raises_exception[pyloop]`，失败在 `test_1.py:923`。共 7 次 gold，都是 56/56（运行来源见表后）。M3 `status_map.json` 与当前 `expected_output.json` 逐键相等（56/56）。`reconcile.json` 中本题 10 行全部 `agree: true` |
| 2 | 公开复现按题面原样运行时，抛出 RuntimeError，且 asyncio 记 1 次 ERROR（`REPRO_OBSERVED=1`） | 确认 | devcheck 以 agent 身份运行，pr1 得 1 条 `asyncio` 记录，pr2 得 1 次处理器调用，pr3 在 stderr 上得 2 个 traceback。私有 gold 对照下三项依次变为 0、0、1 |
| 3 | 包没装进 venv，`/testbed` 必须在 `sys.path` 上；`/tmp` 下 `import aiohttp` 报 ModuleNotFoundError；裸 `pytest` 收集即 ImportError（issue 1，solver_condition） | 部分确认，部分未核实 | 确认的部分：devcheck `env.out` 显示，在 cwd=/testbed 下导入的是 `/testbed/aiohttp/__init__.py`，`python -m pytest` 正常。未核实的部分："/tmp 下失败"与"裸 pytest 失败"本次没有复测，只能沿用历史 `dev_probe.json` 的 `IMPORT_FROM_TMP_RC=1` 和 posthoc3 |
| 4 | 开发条件证据是公开测试 `tests/test_base_protocol.py` 20/20（R09，`solver_conditions.public_tests`） | 过时 | 该文件是按字母序取的第一个，与本题无关（P1 README §4 也承认这个限制）。新证据：devcheck 以 agent 身份跑本题相关的 `tests/test_run_app.py`，窄测 4 passed，全文件 55 passed，用时 26.9 s |
| 5 | `public_hints` 的 conda 措辞是全局问题，不计入本题（R03，E09） | 过时 | v3 的 `public_hints` 已改为 R2E 措辞（`.venv`、不联网、用 `python -m pytest`）。仍有一处小摩擦："`python` and the repo's test tools already point at it" 与"裸 `pytest` 收集失败"同时成立，可能诱导解题者用裸 `pytest`。影响低，照提示做不会出错 |
| 6 | "run_app 在 startup 阶段就抛异常，不绑定端口；题面与测试都不需要网络"（R10） | 部分推翻（措辞） | 目标测试确实不绑定端口，外网也确实不需要。但隐藏测试中 TestShutdown 的 8 个键要绑定真实回环端口，并用 `ClientSession` 访问 `localhost`；`test_sigint`/`test_sigterm` 还要起子进程并发信号。所以回环是必需的。当前 actor 与 grader 都有回环：devcheck 全文件 55 passed，评分时 56 键全部执行 |
| 7 | 目标键 ↔ 题面"应抛出但不记日志"，即"断言不应有日志记录"（R16） | 确认并细化 | 断言本身是：`run_app` 期间 `loop.call_exception_handler`（autospec mock）没有被调用，同时 `pytest.raises(RuntimeError, match="foo")`。它比"没有日志记录"更严：只压日志、仍调用异常处理器的写法会被拒（见 card 的 C6 说明）。这个要求有公开依据，不算误拒 |
| 8 | git 卫生：无 remote/refs/reflog；脏树 4 行，无修复痕迹（R17） | 确认，并补充一项 | devcheck probe facts 中 `GIT_REMOTES`、`GIT_REFLOG`、`GIT_REFS` 都是 0，预检 `GIT_HISTORY=ok`，初态 4 行。补充：工作树里没有本修复的 changelog（grep `6807`、`raised regardless` 都没有结果） |
| 9 | 脏改动属于基线，不会被卷进候选补丁（R04；原文注明"代码阅读，未经真实 rollout 验证"） | 未核实 | 本次证据里仍然没有非 gold 候选经冻结 / 投影的真实交付，属 actor 待验。能确认的只有一点：跑完测试后 `git status` 仍是 4 行（`.coverage`、`__pycache__` 被忽略） |
| 10 | 资源：峰值约 513 MB / 4 GiB，setup 45 s，test 32 s（R12） | 确认 | 加跑账本记录的峰值是 494–511 MB，测试段 28–29 s；R-f 测试段 31.7 s |
| 11 | 时序敏感键 `TestShutdown.test_shutdown_handler_cancellation_suppressed`（issue 2，族 `timing_sensitive_key_watch`）：来源宿主机新旧提交都 FAILED（"0.4 s 超时下 ConnectionRefusedError"）；RH2 加跑 10/10、累计 14/14 PASSED，按稳定处理，族关闭 | 数据确认；机制细化；"关闭"保留分歧 | 见下节 |
| 12 | `expected_provenance_mixed`：本题期望与来源宿主机记录差 1 键 | 确认 | 原始记录里，新提交运行 1 failed / 55 passed，失败的正是上面那个键；旧提交运行 2 failed，即目标键加上这个键。期望把它记为 PASSED |

第 1 条中 noop 与 gold 各 7 次运行的来源：R-f 1 次，环境轮中央复跑 1 次，加跑 5 次。

## 第 11 条详述（与历史的主要分歧）

**确认的事实**：

- 来源原始记录里，新旧两次运行中该键都失败，错误都是 `ClientConnectorError: Cannot connect to host localhost:PORT … [Connect call failed ('127.0.0.1', PORT)]`。
- 失败发生在 `ClientTimeout(total=0.4)` 的那次请求里。
- 在 RH2 评分中该键 14/14 PASSED，在 M3 独立 runner 上 2/2，在 devcheck 公开文件全跑中 2/2。

**机制（历史写成"超时"，不准确）**：

1. 失败不是超时，而是连接被拒：服务端还没有开始 listen。
2. 该测试的 `test()` 在 cleanup_ctx 启动时就被创建，而这发生在 `runner.setup()` 内部、`site.start()` 之前。
3. `test_resp` 发出第一个请求前没有任何预热等待（隐藏 `test_1.py:1217-1227`）。于是客户端的 `getaddrinfo` 和 connect 与服务端的 `create_server` 同时在事件循环里推进，形成竞态。
4. 对照：其它 TestShutdown 用例都先 `sleep(0.5)` 或 `sleep(1)`；经 `self.run_app` 的用例还会对 `ClientConnectorError` 重试 5 次（`:952-966`）。只有这个键没有保护。

**判断**：

- 不算阻塞问题。在 RH2 当前的派生镜像和负载下，这个键稳定通过。
- 但不应把族当作已关闭：这个竞态机制明确，并且在另一台宿主机上连续出现过两次。
- 它一旦翻转，对所有候选都一样，gold 也会得 0，也就是假阴性。
- 建议状态从"关闭"改为 **watch**：探针和训练期间单独统计该键；如果 RH2 里出现翻转，按环境抖动归因。只有真出现翻转时，才考虑提材料修订（给该测试补上与其它用例相同的等待 / 重试），而修订需要用户决定。
- 训练规模并发下仍然没有测过，这一点与历史残余一致。

## 我对初判的改动

- **上调时序风险**：初判把 TestShutdown 当作一组"余量 0.1–1 s 的计时器"泛泛看待，只提到"0.4 s 客户端超时先于 0.5 s PRESTOP"这种计时顺序，漏了启动竞态这一具体机制。读了历史和来源原始记录后，把这个键提升为本题最主要的环境残余风险，但仍不阻塞。依据见上节。
- **不变的部分**：以下都是历史没有覆盖的内容，保持初判：
  - C3 漏测：Ctrl+C 之后 cleanup 抛出的异常被静默吞掉，仍可得 1。
  - R3 路径只执行、不断言。
  - gold 在 R7 上改为抛出。
  - 与 `aiohttp__22a12cc2…` 的包含关系。
  - 目标断言的口径（C6）。
  - 环境敏感键（`::1`、抽象套接字）。
  - 开发条件结论。
- **处置不变**：`needs_review`，理由是"静态候选，待 actor 验证"；不属于题意或测试争议。历史的 `environment_qualified` 是环境层面的结论，与本处置不冲突。
