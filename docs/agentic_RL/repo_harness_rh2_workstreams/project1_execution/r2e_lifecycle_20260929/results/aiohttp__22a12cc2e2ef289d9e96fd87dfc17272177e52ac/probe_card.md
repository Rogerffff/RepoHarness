# aiohttp `22a12cc2` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`F` = `runs/r2e_lifecycle_20260929/formal_v5`（完整评分日志在 `F/remote/<槽位>_logs/`），`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v5/aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac`，`C` = `runs/r2e_actor_20260925/grader_cands`，`B2` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac`。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：probe_ready**。五条都满足：正式评分 8 行全部与期望一致（正对照 gold）；devcheck 13 项全真；测试层的 S1（K3、K4 误收，K2、RC 误拒）已按 R-e 加请求级 R-c 修订，经 Codex 复核与正式评分验收；Codex 点名"仍属源码推断"的 noop、K3、K4 失败原因已由完整日志确认；预检通过。**训练用途另差一项未跑的第 4 步候选**（见用途表），题面问题按 P4 登记、未修。
- **材料**：修订单 v5 的 `r2e-mr-042`（`hidden_test_text_replace`，三处 edit，`test_1.py` `987f9118…` → `ff4bf0d8…`：重写目标测试 `test_https_connect_fingerprint_mismatch`，键名不变；新增网络替身与 3 个测试）与 `r2e-mr-043`（`expected_file_replace`，`351982fc…` → `13eaeeea…`，18 → 21 键，新增 `TestProxy.test_https_connect_fingerprint_match`、`…_match_request_ssl`、`…_mismatch_request_ssl`）；pins v6 `9a24b8693020…`，v6 逐字保留。派生镜像 `858d5d343c80`（`rh2-r2e-derived/aiohttp:22a12cc2e2ef-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `182e8eaea9b3…`）。
- **题目版本**：标明版本的自建修订题（原题 + `r2e-mr-042/043`），不当原 benchmark 报。

## 准入五条（README §3）

1. **正式评分**（`F/ledgers/` gold / noop / s1 / s2 / s3 第 5 行，s4 第 4 行，s5 第 2 行，s6 第 1 行；`F/status.json` 本题 8 行 `match=true`；日志头 `RH2_SETUP_HIDDEN_TESTS_TREE=72d7941d…` 等于 v5 评分包摘要）：

   | 候选 | 角色 | 期望 | 实得 | 不符键与失败断言（正式日志） |
   | --- | --- | --- | --- | --- |
   | gold | 正对照 | 1 | 1（21/21） | — |
   | K1：在 `_create_proxy_connection` 里校验 TLS transport | 合理替代解 | 1 | 1（21/21） | — |
   | K2：不经 `_get_fingerprint` 取指纹 | 原误拒，已纠正（原版 0） | 1 | 1（21/21） | — |
   | RC：不匹配时 `abort()` | 原误拒，已纠正（原版 0） | 1 | 1（21/21） | — |
   | IC：`if not is_closing(): close()` | 替代写法 | 1 | 1（21/21） | — |
   | noop | — | 0 | 0（19/21） | 两个反例键：`ServerFingerprintMismatch not raised`（`test_1.py:524`、`:538`） |
   | K3：校验连到代理的原始 TCP transport | 触发反例，兼 §4 第 3 步退化探测（作用在无关对象上，原版 1） | 0 | 0（19/21） | 同 noop 的两键；两个正例键通过 |
   | K4：配了指纹一律拒绝 | 触发反例，兼退化探测（与输入无关的固定结果，原版 1） | 0 | 0（17/21） | 两个正例键抛 `ServerFingerprintMismatch: (b'', b'', 'www.python.org', 443)`；两个反例键在 `expected` 断言失败（`b''` ≠ 配置的指纹，`:527`、`:542`） |

   各行 `git_apply` 成功、测试段完整、日志不截断、键集相等；补丁是试跑用过的同一份远端副本，账本补丁摘要与本地副本一致（IC 在 `L/results/<本题>/cands/`，其余在 `C/`），失败键与试跑逐一相同。
   - **noop、K3、K4 的失败原因已由完整日志确认**（Codex `L/codex_reviews/review_revision_aiohttp.md` 第 40 行要求）：noop `F/remote/noop_logs/…_fb7574d7.eval.log` 第 65、83 行；K3 `s1_logs/…_452bf119` 第 66、84 行——正例键通过、反例键不抛异常，与"对明文代理 transport 调 `check` 是空操作"的源码推断一致；K4 `s2_logs/…_648aaffe` 第 156、273、298、317 行。与试跑的推断一致。
2. **devcheck**：`D/orig/attempt.json` 13 项 checks 全真；9 条命令都符合预期。agent 身份下：题面原例构造时即 `ValueError: fingerprint has invalid length`（pr2_2，原例在 base 不复现）；真实握手对照 pr4_7 显示直连错指纹已抛 `ServerFingerprintMismatch`，经代理的错指纹（连接器级与请求级）仍 `CONNECTED 200`——缺陷复现；公开 fingerprint / connector / proxy / functional 测试在 base 上 12、10、17、2 passed。私有 gold 对照（root）全部 rc=0，经代理错指纹抛异常且 `got` 是证书摘要，与 09-25 相同。
3. **S1 处理**：R-e 为主、请求级一对是第 2 步要求的非示例实例（revision_plan §1–§4，第 11–262 行）：指纹只经公开 `ssl=` 配置、用真实 `Fingerprint.check`，只替换网络；正例、反例各两例，请求级覆盖连接器默认值。Codex 通过（第 17–25 行），**限定**：这是网络替身下的真实校验行为测试，不是完整 TLS 握手；入口仍是原来的 `_create_connection()`（第 21 行）；原题面非法指纹示例、漏写代理触发条件的问题仍未修，本次通过不核销（第 25 行）。
4. **公开包干净**：devcheck `r2e_preflight_ok`（三项 ok）；修订只动评分包，本题公开包行（`public_bundles_v0.jsonl` 第 2 行）在材料 v3、v4、v5 与当前摄入里哈希相同。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛 |
| 能力比较 | yes | 开发路径与评分依据已核；按 `r2e-mr-042/043` 标明版本报告。题面问题按 P4 登记（见剩余事项），分析时把"判断无需修改""去改构造器"的轨迹单列（`B2/card.md` 第 73 行）。批次运行条件属链路 |
| 训练候选 | conditional | 已有：核心断言齐（revision_plan §7 第 316–322 行），当前版本 noop 0、gold 1，§4 第 2 步（请求级实例）与第 3 步（K3、K4）已做，T3 与 X1 已登记。**差**：§4 第 4 步里一个审查已构造的候选没有评分证据——"为让题面示例成立而放宽 `Fingerprint` 构造器、同时修好代理路径"，静态推断得 1，但破坏公开构造契约（`tests/test_client_fingerprint.py`、`tests/test_client_request.py::test_bad_fingerprint`；`B2/analysis_before_history.md` 第 111 行、`B2/review.md` 第 69、122 行）。v5 隐藏集仍不含构造契约测试，而题面示例恰好诱导这种改法。需跑一次该候选的正式评分与上述公开测试：得 1 且破坏契约即为 S1，可按 R-c 把公开构造契约测试纳入隐藏集 |
| 留出评测候选 | conditional | 差：① 训练候选的上述条件；② D3 仓库划分未定，本题初态含 `1c1c0ea3` 的修复及 `4075c653`、`240da100` 的测试名（X1），只能整仓同侧；③ 若探针结果用于选模型、调提示或调配方即不再符合；④ 只能作标明版本的自建评测 |

## 剩余事项（已登记，不阻塞探针）

- **题面（P4，未修）**：示例是直连，用 21 字符的 `str` 作已弃用的 `fingerprint=`，构造时即 `ValueError`；直连本来就会校验；真实缺陷在 HTTP 代理 CONNECT 之后的 TLS 升级，题面没提（`B2/card.md` 第 36 行；devcheck pr2_2、pr4_7）。公开读者把示例的字面要求列为与公开构造契约冲突的"多解"（`B2/public_read.md` 第 37、87 行），代理路径"可推知为最可能的候选"（`B2/review.md` 第 44 行）。v1 §11 按 R-e 处置、未列 R-f，本卡据此按 P4 登记；若改判 P2，按 v1 §3 在 R-f 前只作问题定位。是否另出 R-f 由协调者定（revision_plan 第 332 行）。
- **T3 / 未覆盖**（revision_plan 第 323–327 行）：不匹配后是否关闭或登记 transport；HTTPS 代理那一跳；`_wrap_existing_connection`；不同 TLS 实现下的真实握手。
- **沿用的入口约束**：测试直接调 `connector._create_connection()`，把校验放到更上层 `connect()` 的实现测不到（revision_plan 第 258 行，原测试同样如此）。
- **后检**：得 1 的补丁加跑公开 `tests/test_client_fingerprint.py`、`tests/test_client_request.py -k fingerprint`（`B2/review.md` 第 122 行）与私有真实握手脚本 devcheck `pr4_7_cmd`（revision_plan 第 327 行），结果与原始 reward 分列；按 v1 §8 先写明判读规则。
- **解题侧**：`/testbed` 须在 sys.path，测试用 `python -m pytest`（`B2/screening_record.json` issue `aio22-solver-condition-sys-path`）；不联网，复现要自建回环 HTTPS 源站与 CONNECT 代理。
- **共享控制面**：`aiohttp.pytest_plugin` 这类候选可改的包代码是同仓共有通道，未验证（`B2/card.md` 第 31 行）。
- **初态**：源镜像带 ` M Makefile` 与未跟踪的 `process_aiohttp_updateasyncio.py`，census 基线已按初态处理。
- **链路**（`L/probe_chain_check.md` §0 第 9–20 行、§4 第 99–108 行；Codex `L/codex_reviews/review_probe_chain_20260929.md` 第 1–3 行"改后可以"）：
  - 求解入口换 `rh2/experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py`，`run_matrix.py` 按题选入口、评分带 `--image-overlays`（待改）；评分沿用 `replay_grade run` + 覆盖表（v5 正式评分即此口径）。
  - 接真实模型前先收口 Codex 的两项 P1：去掉静止屏障里以 root 执行的 git（第 9–31 行）；往返核对不一致、评分 fatal、清理未知时停止派发（第 33–41 行）。正式链直评的基线摘要问题可递延（第 43–51 行）。
  - GPU 机须载入同一 image ID（按 tag→ID 核对），否则本卡评分资格重出。账本 `env_qualification=absent`，能力统计前补接资格账本或单列（Codex 第 78 行）。
  - 模型实际收到的题面消息未对本题捕获。本机开销：rollout 从起容器到可信初始化完成约 110 s；评分 trusted setup 63–125 s（该步 300 s 硬时限）；测试段 12–15 s。

## 证据索引

- 旧卡：`B2/{card.md,screening_record.json,review.md,public_read.md,analysis_before_history.md}`（旧 usage 只有 `intended_use`）
- 修订：`L/results/aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac/{revision_plan.md,revision_draft.json,trials/,cands/}`；正式条目 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v5.json` 的 `r2e-mr-042`、`r2e-mr-043`
- Codex：`L/codex_reviews/review_revision_aiohttp.md` 第 17–25、37–41 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/ledger_*.jsonl`（行号见第 1 条）、`F/remote/*_logs/`
- devcheck：`D/orig/attempt.json`、`D/orig/captures/`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v5/summary.json`
