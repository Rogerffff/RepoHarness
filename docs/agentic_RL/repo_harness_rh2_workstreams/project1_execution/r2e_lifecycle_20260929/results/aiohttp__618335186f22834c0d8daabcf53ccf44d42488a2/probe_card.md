# aiohttp `61833518` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`F` = `runs/r2e_lifecycle_20260929/formal_v5`（完整评分日志在 `F/remote/<槽位>_logs/`），`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v5/aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2`，`C` = `runs/r2e_actor_20260925/grader_cands`，`B1` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2`。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：probe_ready**。五条都满足：正式评分 6 行全部与期望一致（正对照 gold）；devcheck 13 项全真；S1 已按 R-c 修订，经 Codex 复核与正式评分验收（含 Codex 要求必须纳入的 AP1m）；预检通过。
- **材料**：修订单 v5 的 `r2e-mr-044`（`hidden_test_text_replace`，`test_1.py` `89f3cf5e…` → `89702c7c…`）与 `r2e-mr-045`（`expected_file_replace`，`f0423107…` → `3390e85f…`，47 → 49 键，新增 `TestHttpMessage.test_write_payload_deflate_chunked_encoding`、`…_multiple_writes`）；pins v6 `9a24b8693020…`，v6 逐字保留。派生镜像 `b93c5d43ab28`（`rh2-r2e-derived/aiohttp:618335186f22-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `70ceace9f6ab…`）。
- **题目版本**：标明版本的自建修订题（原题 + `r2e-mr-044/045`），不当原 benchmark 报。

## 准入五条（README §3）

1. **正式评分**（`F/ledgers/` gold / noop / s1 / s2 / s3 第 6 行，s4 第 5 行；`F/status.json` 本题 6 行 `match=true`；日志头 `RH2_SETUP_HIDDEN_TESTS_TREE=23b524a8…` 等于 v5 评分包摘要）：

   | 候选 | 角色 | 期望 | 实得 | 不符键与失败断言（正式日志） |
   | --- | --- | --- | --- | --- |
   | gold | 正对照 | 1 | 1（49/49） | — |
   | AP2：两个写出器都跳过空块 | 合理替代解 | 1 | 1（49/49） | — |
   | A1：压缩过滤器不产出空输出 | 合理替代解（审查期未跑，本轮补上） | 1 | 1（49/49） | — |
   | noop | — | 0 | 0（45/49） | 原 2 个目标键 + 2 个新键：`all(chunks)` 为假 |
   | AP1：只在长度写出器跳过空块 | 触发反例，兼 §4 第 3 步退化探测（抑制症状，原版 1） | 0 | 0（47/49） | 两个新键：`all(chunks)` 为假（`test_1.py:512`、`:530`） |
   | AP1m：AP1 + chunked 写出器合成一次 write，空块照发 | 构造的已知错误（原版 1） | 0 | 0（47/49） | 两个新键在分帧检查失败：`data after the terminating chunk`（`:493`），即终止块提前 |

   各行 `git_apply` 成功、测试段完整、日志不截断、键集相等；补丁是试跑用过的同一份远端副本，账本补丁摘要与本地副本一致（AP1m、A1 在 `L/results/<本题>/cands/`，其余在 `C/`），失败键与试跑逐一相同。出处（`F/remote/`）：noop `noop_logs/…_c57ce380.eval.log` 第 52、72、92、111 行；AP1 `s1_logs/…_2e66414d` 第 52、72 行；AP1m `s2_logs/…_e0668041` 第 60、86 行。Codex 要求正式矩阵包含 AP1m（`L/codex_reviews/review_revision_aiohttp.md` 第 35 行）：已包含，且正式日志与试跑一样显示它通过了 `all(chunks)`、失败在提前终止的分帧上，说明新测试查的是提前 EOF，不只是空写入。
2. **devcheck**：`D/orig/attempt.json` 13 项 checks 全真；6 条命令都符合预期。agent 身份下复现两种症状：示例配置出现空写入 `[b'', b'', b'KI,I\x04\x00']`（mcve_c2_writes，rc=1，预期非零）；无 Content-Length 时正文以 `0\r\n\r\n` 开头（mcve_c3_chunked，rc=1，预期非零）。公开 `tests/test_http_protocol.py` 47 passed；`tests/test_wsgi.py` + `tests/test_web_response.py` 有 3 个 cookie 用例失败（68 passed），agent base 与私有 gold 对照完全相同，与本题无关（`B1/card.md` 第 65 行），与 09-25 相同。私有 gold 下正文为 `6\r\nKI,I\x04\x00\r\n0\r\n\r\n`。
3. **S1 处理**：R-c 一处（revision_plan §1–§4，第 11–122 行）：补标题场景（chunked 传输 + deflate 在最后），用语义判定——分块格式完整、终止块恰好一个且在末尾、各块拼起来解压等于原载荷——再加题面自己的 `all(chunks)`；不要求字节等于 gold，不扩到 gzip 与 HTTP/1.0。Codex 通过（第 27–35 行）：范围合适，AP1m 是有效的已知错误候选，新断言不要求压缩字节或写入布局等于 gold。
4. **公开包干净**：devcheck `r2e_preflight_ok`（三项 ok）；修订只动评分包，本题公开包行（`public_bundles_v0.jsonl` 第 5 行）在材料 v3、v4、v5 与当前摄入里哈希相同。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛 |
| 能力比较 | yes | 开发路径与评分依据已核；按 `r2e-mr-044/045` 标明版本报告。批次运行条件属链路 |
| 训练候选 | yes | 核心要求有直接断言（revision_plan §7 第 169–172 行：示例配置无空写入、标题场景不提前 EOF、载荷完整、终止块唯一且在末尾）；当前版本 noop 0、gold 1；§4 第 2 步（标题场景不同于示例的 Content-Length 配置）与第 3 步（AP1、AP1m）已做；T3、X1 已登记。训练价值另看：题面几乎逐字给出原目标测试的配置与断言形态（`B1/screening_record.json` 的 `usage.exposure_notes`），新增两键不在题面里 |
| 留出评测候选 | conditional | 差：① D3 仓库划分未定，同仓关系旧审查未查、只有机械扫描命中（X1），只能整仓同侧；② 若探针结果用于选模型、调提示或调配方即不再符合；③ 只能作标明版本的自建评测 |

## 剩余事项（已登记，不阻塞探针）

- **T3 / 未覆盖**（revision_plan 第 173–177 行）：gzip；HTTP/1.0 的 `_write_eof_payload`；不经过滤器直接 `write(b'')`（题面未定）；大块、多次写入夹杂非空压缩输出。后检 `rh2/experiments/r2e_actor_20260925/postcheck/aiohttp_61833518_c3.py` 的 `large_three_writes` 可作补充判读；旧的"每个得 1 的补丁都加跑 C3"主要用途已由新隐藏测试接管，是否保留由协调者定（revision_plan 第 182 行）。
- **题面（P4，旧 I2）**：示例断言 `all(write.mock_calls)` 恒为真；示例用 Content-Length 写出器，不是标题说的 chunked 路径；只修 chunked 写出器的补丁得 0 有依据（`B1/card.md` 第 53–56 行；revision_plan 第 181 行）。
- **开发陷阱（旧 I3）**：源镜像把 4 个文件里的 `asyncio.async(` 改成了兼容写法，`git status` 显示为 `M`；候选若还原 `client.py` 或 `client_reqrep.py`，评分时 `import aiohttp` 语法错误、全部收集失败得 0，按环境陷阱计（`B1/card.md` 第 3、57–60 行）。census 基线只导出 agent 自己的改动（`L/probe_chain_check.md` 第 60 行）。
- **解题侧**：`/testbed` 须在 sys.path，测试用 `python -m pytest`；无 pip、不联网；兼容改写使真实客户端与服务端报 `TypeError`（`B1/card.md` 第 61–65 行）。
- **X1**：机械扫描与 `aiohttp__240da100…` 互相命中 1 行（本题 gold 只加 1 行），未逐行核实（`runs/r2e_static_prep_20260924/cross_task_gold_scan.json`）；同仓题目关系旧审查未查（`B1/card.md` 第 45 行）。
- **链路**（`L/probe_chain_check.md` §0 第 9–20 行、§4 第 99–108 行；Codex `L/codex_reviews/review_probe_chain_20260929.md` 第 1–3 行"改后可以"）：
  - 本题已在链路检查里用真实 CC + 网关 + 桩跑通求解、冻结导出与回放往返（`L/probe_chain_check.md` 第 55–62 行），但用的是 v5 之前的镜像 `e647c9763316`（47 键材料）；v5 镜像 `b93c5d43ab28` 由本卡的 devcheck 与正式评分覆盖。
  - 求解入口换 `rh2/experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py`，`run_matrix.py` 按题选入口、评分带 `--image-overlays`（待改）；评分沿用 `replay_grade run` + 覆盖表（v5 正式评分即此口径）。
  - 接真实模型前先收口 Codex 的两项 P1：去掉静止屏障里以 root 执行的 git（第 9–31 行）；往返核对不一致、评分 fatal、清理未知时停止派发（第 33–41 行）。正式链直评的基线摘要问题可递延（第 43–51 行，本题正是该问题的复现题）。
  - GPU 机须载入同一 image ID（按 tag→ID 核对），否则本卡评分资格重出。账本 `env_qualification=absent`，能力统计前补接资格账本或单列（Codex 第 78 行）。
  - 模型实际收到的题面消息未对本题捕获。本机开销：rollout 从起容器到可信初始化完成约 14 s；评分 trusted setup 13–20 s；测试段约 2 s。

## 证据索引

- 旧卡：`B1/{card.md,screening_record.json,review.md}`（旧 usage 只有 `intended_use`）；Codex 首批复核 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_actor_review_20260925/README.md` 第 62、70 行
- 修订：`L/results/aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2/{revision_plan.md,revision_draft.json,trials/,cands/}`；正式条目 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v5.json` 的 `r2e-mr-044`、`r2e-mr-045`
- Codex：`L/codex_reviews/review_revision_aiohttp.md` 第 27–35、37–41 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/ledger_*.jsonl`（行号见第 1 条）、`F/remote/*_logs/`
- devcheck：`D/orig/attempt.json`、`D/orig/captures/`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v5/summary.json`
