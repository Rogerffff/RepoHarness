# L5 · 证据索引（只读）

采集时刻：**2026-09-16 04:02（本机时区 +08:00）**。生成脚本 `build_evidence_index.py`，重跑即可刷新。
本文件只做目录说明、缺件清单与口径提醒，**不下任何题目结论**；所有判定（`official_verdict` / `report.outcome` / `reward`）都从账本原样搬运。

产物：

- `evidence_index.json`（约 2.1 MB）—— 按任务的证据索引正文。
- `build_evidence_index.py` —— 生成脚本；只读输入，不写任何账本。

## 0. 一句话结论

216 个 SWE-Gym 题与 48 个 R2E 题**每一题都至少有一条证据**，合计 3290 条证据条目，来自 29 个账本/汇总文件。
但"有证据"不等于"有能用的判定"：11 题的 gold 在任何一次运行里都没到过 `RESOLVED_FULL`，5 题的 gold 在联网与离线两种条件下结论相反，192 题从未在 rh2 真实 harness 下跑过。详见 §4、§5。

## 1. 怎么用 `evidence_index.json`

顶层结构：

| 字段 | 内容 |
| --- | --- |
| `tasks` | 主表。键是 `instance_id`（SWE-Gym）或 `r2e::<commit_hash>`（R2E）。 |
| `ledgers` | 29 个账本/汇总文件的清单：路径、行数、schema、run_tag、覆盖题数、gate/candidate 种类、时间范围、日志目录与命名。 |
| `ledger_relations` | 三组副本关系（哪份是哪份的前缀/归档），避免重复计数。见 §6-C5。 |
| `signals_crosscheck` | 与 `task_signals_swegym.json` 的逐题核对结果。见 §3。 |
| `effective_coverage` | "有能用的判定"的覆盖统计与例外题清单。见 §4。 |
| `caliber_notes` | 六条口径差异（C1–C6）。见 §6。 |
| `coverage` / `missing_summary` | 覆盖计数与缺件计数。 |

每条 `tasks[*].evidence[i]` 的字段：

| 字段 | 含义 |
| --- | --- |
| `kind` | 证据类型，见 §2。 |
| `condition` | 运行条件摘要（gate / variant / network / attempt / run_tag / 执行用户 / 内存上限 / fixture 来源）。**比较任何两条证据前先读它。** |
| `ledger` + `line` | 账本文件的相对路径与 **1 基行号**；`line=null` 表示来源是 JSON 汇总而非逐行账本。 |
| `result` / `verdict` / `reward` | 原样搬运。oracle 探针用 `official_verdict`（`RESOLVED_FULL/PARTIAL/NO/UNPARSED`），rh2 用 `report.outcome`（`resolved/unresolved/failed_to_grade`）与 `report.reward`，R2E 用 `reward`（0/1）。 |
| `log_dir` | **本机**日志目录（已验证存在）。 |
| `remote_log` / `diagnostics_ref` | rh2 e1/e2 的日志在机器 1 的远端路径（`/work/replay/eval_logs/...`），本机没有同步，只记路径。 |
| `superseded_by` | 该行来自被取代的中途快照账本，统计时跳过。见 §6-C5。 |

所有路径都相对工作区根 `.`。

查一题的典型做法：

```bash
python3 -c "import json;d=json.load(open('docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L5_evidence_index/evidence_index.json'));
[print(e['kind'],'|',e['condition'],'|',e.get('verdict'),e.get('reward'),'|',e['ledger'],e.get('line')) for e in d['tasks']['Project-MONAI__MONAI-2454']['evidence']]"
```

## 2. 证据类型（`kind`）与覆盖题数

采集时刻的覆盖（SWE-Gym 满分 216，R2E 满分 48）：

| kind | 覆盖题数 | 来源账本 | 说明 |
| --- | --- | --- | --- |
| `oracle_facts` | 216 | `swegym_ledger.jsonl` gate=facts | 只采事实，`official_verdict=null`、`result=recorded` |
| `oracle_empty` | 216 | 同上 gate=empty | 空补丁对照；变体 `default` / `offline` / `offline_noinstall` |
| `oracle_gold` | 216 | 同上 gate=gold | 变体 `default` / `grader_user` / `offline` / `offline_noinstall` |
| `stage1_empty` / `stage1_gold` | 216 / 216 | `stage1_continuation_20260911/stage1_offline.jsonl` | 阶段一离线全量（`variant=offline, network=none`） |
| `probe_unrelated` / `probe_mutation` | 12 / 12 | `swegym_ledger.jsonl` | 反例探针，只做了 12 题 |
| `oracle_facts_v2` | 12 | `swegym_facts_v2.jsonl` | facts 复采 |
| `oracle_candidate` / `oracle_candidate_projected` | 24 / 24 | `cc_candidate_grading.jsonl` | DeepSeek 候选补丁的原组与投影组，见 §6-C2 |
| `deepseek_trajectory` | 24 | `cc_reference_ledger.jsonl` | 轨迹在 `logs_cc/<instance_id>/{stream.jsonl,candidate.diff,prompt.txt,stderr.txt}` |
| `monai_control` | 1 | `monai1121_{online,offline_cached,offline_uncached}_20260911/results.jsonl` | 只针对 `Project-MONAI__MONAI-1121` 的三次条件对照 |
| `rh2_e1` / `rh2_e1_artifacts` / `l0_facts_e1` | 4 / 4 / 4 | `e1/ledger_e1*.jsonl`、`e1/artifacts/`、`L0_facts_tool/facts_e1/` | rh2 真机第一批 |
| `rh2_e2_A` / `rh2_e2_B` / `rh2_e2_B_repeat` / `rh2_e2_derived` | 9 / 24 / 6 / 2 | `e2/ledger_e2_*.jsonl` | **运行中快照**，见 §6-C6 |
| `rh2_e1_review_noop` / `rh2_e1_review_forced_timeout` | 1 / 1 | `runs/swe_grading_e1_review_20260916/root/remote_pandas_noop/{ledger_pandas_noop.jsonl,forced_timeout/ledger.jsonl}` | Codex 的 e1 复核实跑：`pandas-dev__pandas-48106` 的 noop 复跑（**e1 原始两次都 `failed_to_grade`，这次跑到了测试**，`outcome=unresolved` / `reward=0.0` / F2P 0/16 / P2P 失败 3/1020）；`conan-io__conan-13326` 的人为超时注入（`grading_deadline_exhausted`）。**eval 日志与 artifacts 已同步到本机。** |
| `r2e_facts` | 24 | `r2e_ledger.jsonl` | 只有 core24 有 facts 门 |
| `r2e_noop` / `r2e_gold` | 48 / 48 | `r2e_ledger{,_v2,_v3}.jsonl` + 阶段一三份扩展账本 | 跨 runner 版本，见 §6-C1 |
| `r2e_gold_m3` | 48 | `runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl` | 今晚机器 3，48 题 × 2 次 attempt |
| `r2e_noop_m3_x2` | 48 | `runs/env_overnight_20260916/M3/noop_repeat.json` | 今晚机器 3，同容器 noop 连跑两次 |
| `m3_check_record` | 48 | `docs/.../env_overnight_20260916/M3/M3_r2e_check_records.json` | 今晚机器 3 的 40 项镜像检查记录 |

日志目录命名（本机）：

- 20260909 SWE-Gym：`runs/env_probe_20260909_final_sync/ledger/logs/<instance_id>/<gate>/<variant>/a<attempt>/{eval.sh,status_map.json,test_output.txt[,patch.diff]}`
- 20260909 DeepSeek 轨迹：`.../ledger/logs_cc/<instance_id>/{stream.jsonl,candidate.diff,prompt.txt,stderr.txt}`；候选补丁另存 `.../ledger/cc_patches/<instance_id>.diff`
- 20260909 R2E：`.../ledger/logs_r2e/<repo>/<commit12>/<gate>/a<attempt>/{status_map.json,test_output.txt[,git_gold.diff,gold.diff]}`
- 阶段一 SWE-Gym：`runs/env_probe_stage1_20260910/ledger/logs/<run_tag>/<instance_id>/<gate>/<variant>/a<attempt>/...`，**外加**续跑的 35 个 mypy 题在 `.../ledger/stage1_continuation_20260911/logs/stage1_offline_20260910/<instance_id>/...`（两个目录要一起看）
- 机器 3 R2E gold：`runs/env_overnight_20260916/M3/gold_ledger/logs_r2e/<repo>/<commit12>/gold/a<attempt>/...`；镜像事实 `runs/env_overnight_20260916/M3/facts/<commit12>/`
- rh2 e1 artifacts：`runs/swe_grading_wiring_20260915/e1/artifacts/swe_gym_lite--<instance_id>/a<attempt>-<hash>/`；eval 日志 `.../e1/eval_logs/evallog_<run_id截断>_<8位hash>.{eval.log,diagnostics.json}`（e2 的对应文件**只在机器 1**）

## 3. 与 `task_signals_swegym.json` 的交叉核对

核对基准：阶段一的**全量**账本 `runs/env_probe_stage1_20260910/ledger/stage1_continuation_20260911/stage1_offline.jsonl`（434 行 / 216 题）。

**不一致 72 条**（明细见 `evidence_index.json` → `signals_crosscheck.mismatches`）：

| 类别 | 条数 | 说明 |
| --- | --- | --- |
| `signals_missing` | 68（= 34 题 × empty/gold） | signals 表里这 34 题 `stage1` 为 `null`，但账本里有完整实跑行 |
| `verdict_differs` | 2 | `python__mypy-10401` 的 empty/gold：signals 取到 `null`，账本里有后来跑通的行 |
| `rc_install_differs` | 2 | 同上题的 `rc_install`：signals `null`，账本 `0` |

**根因**：signals 表的 `stage1` 字段是从中途快照 `runs/env_probe_stage1_20260910/ledger/stage1_offline.jsonl`（364 行 / 182 题）读的，不是从续跑后的 434 行版本读的。差的 34 题**全是 `python/mypy`**（mypy 在 216 题里共 40 题），另加 `python__mypy-10401` 只取到 `infra_failed:run_stopped` 那一行。

**这 34 题在账本里其实都跑通了**：`empty` 全部 `RESOLVED_NO`、`gold` 全部 `RESOLVED_FULL`、`result=passed`，日志在 `stage1_continuation_20260911/logs/stage1_offline_20260910/<instance_id>/`。所以把 signals 的空值读成"没跑过/跑失败"会错判 34 题。

`stage1_continuation` 账本内部另有 2 组重复行（`python__mypy-10401` 的 gold 在 363/365 行、empty 在 364/366 行）：前一行 `infra_failed:run_stopped`、`verdict=null`，后一行 `passed`、`RESOLVED_FULL/RESOLVED_NO`。按题取值应取后一行。

**核对一致的部分**：

- `in_e2`：188 题标空、15 题 `["B"]`、9 题 `["A","B"]`、4 题 `["C"]`。与采集时刻的 e2 账本无冲突；C 组 4 题在采集时刻尚未出现在任何 e2 账本里（lane C 还没跑）。
- `deepseek_candidate_oracle`：24 题与 `cc_candidate_grading.jsonl` 的 **`gate=candidate`（原组）24/24 一致**。

## 4. 已知缺件

### 4.1 按题缺件（"有行但没有能用的判定"）

- **11 题 gold（oracle 口径）在任何一次运行里都没到过 `RESOLVED_FULL`**：`getmoto__moto-5417`、`getmoto__moto-5545`、`getmoto__moto-5562`、`getmoto__moto-5701`、`getmoto__moto-6308`、`iterative__dvc-4185`、`modin-project__modin-5940`、`modin-project__modin-6780`、`pandas-dev__pandas-48106`、`pandas-dev__pandas-50319`、`pydantic__pydantic-8977`。（清单在 `effective_coverage.swegym.gold_never_RESOLVED_FULL_anywhere`；本包不判断原因。注意其中 `pandas-dev__pandas-48106` 另有一条 rh2 侧成功出判定的 noop 复跑，见 §2 的 `rh2_e1_review_noop`。）
- **5 题 gold 在联网与离线条件下结论相反**（详见 §6-C3）：`Project-MONAI__MONAI-1121`、`Project-MONAI__MONAI-3205`、`getmoto__moto-4799`、`getmoto__moto-4833`、`getmoto__moto-7105`。
- **2 个 R2E commit 的 gold 两次 attempt 都 `reward=0`**：`coveragepy 016af5f6352d`（`MockingProtectionTest.test_os_path_exists` 期望 FAILED 实得 PASSED）、`datalad 58ba5165234c`（`test_alter_interface_docs_for_cmdline` 期望 PASSED 实得 FAILED）。这两个与阶段一 `r2e_failure_repeats_20260911` 的失败**完全一致**（同 commit、同用例名、同方向），是可复现的现象而非偶发。

### 4.2 缺件最多的三类（按缺的题数排）

| 排名 | 缺的证据类型 | 缺多少题 |
| --- | --- | --- |
| 1 | `probe_unrelated` / `probe_mutation`（反例探针） | 204 / 216 |
| 2 | `oracle_candidate` + `deepseek_trajectory`（候选补丁与轨迹） | 192 / 216（只有 24 题有） |
| 3 | rh2 真实 harness 实跑（`rh2_e1` ∪ `rh2_e2`） | 192 / 216（采集时刻只有 24 题，其中 e1 4 题 ⊂ e2 24 题） |

次一级：`oracle_facts_v2` 只有 12 题；R2E 的 `r2e_facts`（20260909 facts 门）只有 core24，**`night_expansion24` 的 24 题全缺**。

### 4.3 本机没有的证据

rh2 e1/e2 的 `eval.log` 与 `diagnostics.json` 在账本里记的是机器 1 的路径（`/work/replay/eval_logs/...`）。e1 的这批已同步到 `runs/swe_grading_wiring_20260915/e1/eval_logs/`（10 个 run × 2 个文件），**e2 的没有同步**，本机只有账本行。索引里这类条目 `log_dir=null`、`remote_log` 记远端路径。

## 5. 账本盘点

29 个账本/汇总文件，其中 **25 个逐行 JSONL 账本共 3186 行**（去掉被取代的中途快照后 24 个 / 2822 行），另有 4 个非逐行来源：`L0_facts_tool/facts_e1/summary.json`（1280 条字段级事实）、`M3/noop_repeat.json`（48 题）、`M3/M3_r2e_check_records.json`（48 题）、`e1/artifacts/`（4 题目录）。
完整清单（含 schema、run_tag、gate 分布、结果分布）在 `evidence_index.json` → `ledgers`。

| 行数 | 账本 | 覆盖题数 | 时间范围（UTC） |
| --- | --- | --- | --- |
| 1661 | `runs/env_probe_20260909_final_sync/ledger/swegym_ledger.jsonl` | 216 | 09-08T19:45 ~ 09-09T04:42 |
| 12 | `.../ledger/swegym_facts_v2.jsonl` | 12 | 09-08T19:58 |
| 48 | `.../ledger/cc_candidate_grading.jsonl` | 24 | 09-08T20:04 ~ 21:47 |
| 27 | `.../ledger/cc_reference_ledger.jsonl` | 24 | 09-08T19:55 ~ 21:27 |
| 120 / 144 / 144 | `.../ledger/r2e_ledger{,_v2,_v3}.jsonl` | 24 / 24 / 24 | 09-08T19:49 ~ 20:35 |
| 6 | `runs/env_probe_stage1_20260910/ledger/stage1_preflight.jsonl` | 3 | 09-10T15:45 |
| 364 | `.../ledger/stage1_offline.jsonl`（**中途快照，已被下一行取代**） | 182 | 09-10T15:48 ~ 21:46 |
| 434 | `.../ledger/stage1_continuation_20260911/stage1_offline.jsonl` | 216 | 09-10T15:48 ~ 09-11T02:39 |
| 1 / 1 / 1 | `.../ledger/monai1121_{online,offline_uncached,offline_cached}_20260911/results.jsonl` | 1 | 09-11T02:40 ~ 02:45 |
| 6 / 42 / 8 | `.../ledger/r2e_{preflight,remainder,failure_repeats}_20260911/results.jsonl` | 3 / 21 / 2 | 09-11T02:48 ~ 02:57 |
| 8 / 2 | `runs/swe_grading_wiring_20260915/e1/ledger_e1{,_pandas}.jsonl` | 4 / 1 | 09-15T14:00 ~ 15:20 |
| 27 / 24 / 6 / 2 | `runs/swe_grading_wiring_20260915/e2/ledger_e2_{A,B,B_repeat,derived}.jsonl` | 9 / 24 / 6 / 2 | 09-15T18:37 ~ 19:21（**仍在增长**） |
| 96 | `runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl` | 48 | 09-15T19:26 ~ 19:50（**仍在增长**） |
| 48 | `runs/env_overnight_20260916/M3/noop_repeat.json` | 48 | — |
| 48 | `docs/.../env_overnight_20260916/M3/M3_r2e_check_records.json` | 48 | — |
| 1280 | `docs/.../env_overnight_20260916/L0_facts_tool/facts_e1/summary.json` | 4 | — |
| 4 | `runs/swe_grading_wiring_20260915/e1/artifacts/` | 4 | — |
| 1 / 1 | `runs/swe_grading_e1_review_20260916/root/remote_pandas_noop/{ledger_pandas_noop.jsonl,forced_timeout/ledger.jsonl}` | 1 / 1 | 09-15T16:51 / 16:57 |

**未纳入索引的副本**（避免重复计数，见 §6-C5）：`docs/.../project1_execution/env_probe_20260909/ledger/` 的 7 个文件与 `runs/env_probe_20260909_final_sync/ledger/` 的同名文件 **sha256 全部相同**；`runs/env_probe_20260909_codex_backup/ledger/` 的 6 个文件相同、`swegym_ledger.jsonl` 是 final_sync 前 1237 行的逐行前缀（20260909 夜跑到一半的快照）。codex_backup 的独有内容是 `analysis/`（含 `solvability_review` 副本、快照校验）与 `data/`（输入数据快照）。

`runs/swe_grading_e1_review_20260916/` 里只有两份是**独立实跑**，已纳入索引：`root/remote_pandas_noop/ledger_pandas_noop.jsonl` 与 `root/remote_pandas_noop/forced_timeout/ledger.jsonl`（各 1 行，日志本机可读）。其余 JSONL 是 pytest 夹具与远端快照副本（`prompts.jsonl` / `rollout_task_views.jsonl` / `host_grading_views.jsonl` 各 2 行），不是题级账本；`root/remote_replay_snapshot/ledger_e1{,_pandas}.jsonl` 与 `runs/swe_grading_wiring_20260915/e1/` 的同名文件 sha256 相同，未重复索引。

## 6. 口径差异提醒（C1–C6）

对应 `evidence_index.json` → `caliber_notes`。

**C1 · R2E 账本 v1/v2 的 gold reward 已被 v3 覆盖，不可与 v3/M3 混读。**
`r2e_probe/0.1`(v1) 与 `0.2`(v2) 的期望测试 ID 键没去 ANSI 转义（形如 `"TestFileTiff.test_4bit"`），与解析出的裸键对不上 → 8 missing + 8 extra → `reward=0`；v1 另有参数化多行用例名截断的问题（pandas `294cbc8d1faa`，5 missing / 5 extra）。`r2e_probe/0.3`(v3) 两类都修掉，**同一 commit 的 gold reward 由 0 变 1** 的有 5 个：pillow `f9d3ee0f4888` / `2d01f7d02243` / `3a61c9e95e5c` / `a682ceaf47ab`、pandas `294cbc8d1faa`。
→ 读 R2E 结论只用 v3、阶段一扩展与机器 3 的行；v1/v2 只当解析器演进史。今晚机器 3 的 `reward_details` 里已经有 `expected_keys_have_ansi` 字段，可以直接确认这一点。

**C2 · DeepSeek 候选有『原组』与『投影组』两套判定。**
`cc_candidate_grading.jsonl` 每题两行：`gate=candidate`（原补丁）与 `gate=candidate_projected`（按控制面规则投影后）。24 题里只有 `Project-MONAI__MONAI-2454` 两组不同（原组 `UNPARSED` / `result=infra_failed:test_patch_not_applied`，投影组 `RESOLVED_NO`，投影丢掉了 `tests/test_to_tensor.py`）。`task_signals_swegym.json` 的 `deepseek_candidate_oracle` 取的是**原组**。
→ 引用"DeepSeek 解没解出来"时写明取哪一组。

**C3 · 20260909 夜探针是联网（`network=default`），阶段一是离线（`variant=offline, network=none`）。**
5 题 gold 结论相反：`Project-MONAI__MONAI-1121`、`Project-MONAI__MONAI-3205`（联网 `RESOLVED_FULL` / 离线 `RESOLVED_NO`）、`getmoto__moto-4799`、`getmoto__moto-4833`（同向）、`getmoto__moto-7105`（联网 `RESOLVED_FULL` / 离线 `RESOLVED_PARTIAL`）。MONAI-1121 的三次对照实验就是为此做的：`online` 与 `offline_cached` 都 `RESOLVED_FULL`，`offline_uncached` `RESOLVED_NO`。
→ 比较任意两条 gold 证据前先看 `condition` 里的 `network` / `variant`。

**C4 · rh2（e1/e2）与 oracle 探针的执行条件系统性不同。**
`L0_facts_tool/facts_e1/reconcile.md` 列出三处：`network` `deny_all` → `none`；测试执行用户 `rh2grader` → `root`；`memory_bytes` 4 GiB → 8 GiB。判定词表也不同：rh2 是 `report.outcome`（`resolved` / `unresolved` / `failed_to_grade`）+ `report.reward`，oracle 是 `official_verdict`（`RESOLVED_FULL` / `PARTIAL` / `NO` / `UNPARSED`）。
→ rh2 与 oracle 的差异先归到条件差异，再谈判定差异；两套词表不要互相翻译。

**C5 · 账本副本会重复计数。**
三组关系（均已逐行验证）：(a) `docs/.../env_probe_20260909/ledger/` 7 个文件与 `runs/env_probe_20260909_final_sync/ledger/` sha256 全同 —— 归档副本；(b) `runs/env_probe_20260909_codex_backup/ledger/swegym_ledger.jsonl`（1237 行）是 final_sync 版（1661 行）的逐行前缀 —— 中途快照；(c) `stage1_offline.jsonl`（364 行 / 182 题）是 `stage1_continuation_20260911/stage1_offline.jsonl`（434 行 / 216 题）的逐行前缀 —— 中途快照。
→ 按题统计时 20260909 只用 `runs/env_probe_20260909_final_sync/ledger/`，阶段一只用 `stage1_continuation_20260911/` 版。索引里来自被取代账本的条目带 `superseded_by` 字段，统计时跳过。

**C6 · e2 与机器 3 的账本都是运行中快照。**
采集时刻 2026-09-16 04:02（+08:00）：`ledger_e2_A.jsonl` 27 行 / `ledger_e2_B.jsonl` 24 行 / `ledger_e2_B_repeat.jsonl` 6 行 / `ledger_e2_derived.jsonl` 2 行；机器 1 的 e2 仍在跑。机器 3 的 `r2e_gold_m3.jsonl` 在本索引第一次采集（03:47）时是 48 行（`attempt=1`），11 分钟后变成 96 行（追加了 48 行 `attempt=2`）—— 两次 attempt 的 reward 完全一致，46 题 `reward=1`、2 题 `reward=0`。
→ 引用 e2 与 M3 的数字务必带采集时刻与行数；本文件的数字在机器还在跑的期间会过期，重跑 `build_evidence_index.py` 即可刷新。
