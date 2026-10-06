# L0 · 只读汇总工具 `screening_facts` 实施与 e1 验收

日期：2026-09-16 夜（本机时间 02:10–02:40）。执行：Claude（Opus 5），未派生 sub-agent。
定位：`environment_screening_definition_20260915.md` §6 的"下一实施片只有一个小工具"。

**状态分级**：本页"已实施"= 代码已写并跑通；"已验证"= 有本机命令输出或文件可核对；
"发现"= 从 e1 证据读出的事实（含与既有报告的出入），**不是**对环境或任务的处置结论。

---

## 1. 产物

| 类型 | 路径 |
| --- | --- |
| 工具 | `rh2/scripts/screening_facts.py`（新增，只读；未改 rh2 其它文件） |
| 测试 | `rh2/tests/test_screening_facts.py`（新增，15 项；缺 e1 证据时自动 skip） |
| e1 每题事实（紧凑） | `docs/.../env_overnight_20260916/L0_facts_tool/facts_e1/<instance_id>/facts.json`（4 题，共 344 KB） |
| e1 来源对账 | `docs/.../L0_facts_tool/facts_e1/reconcile.md` |
| e1 可观测率汇总 | `docs/.../L0_facts_tool/facts_e1/summary.json` |
| e1 完整逐 ID 状态表 | `runs/env_overnight_20260916/L0_facts_tool/facts_e1_full/`（`--full-status-maps`，3.1 MB，不放文档目录） |

复现命令（从 `rh2/` 跑，`R` = 仓库根）：

```
.venv/bin/python scripts/screening_facts.py \
  --ledger $R/runs/swe_grading_wiring_20260915/e1/ledger_e1.jsonl \
  --ledger $R/runs/swe_grading_wiring_20260915/e1/ledger_e1_pandas.jsonl \
  --eval-log-dir $R/runs/swe_grading_wiring_20260915/e1/eval_logs \
  --artifacts-dir $R/runs/swe_grading_wiring_20260915/e1/artifacts \
  --grading-bundles $R/docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/grading_bundles_v2_v0.jsonl \
  --oracle-ledger $R/runs/env_probe_stage1_20260910/ledger/stage1_offline.jsonl \
  --oracle-ledger $R/runs/env_probe_stage1_20260910/ledger/stage1_continuation_20260911/stage1_offline.jsonl \
  --out-dir <out>          # 加 --full-status-maps 得完整逐 ID 表
```

**已验证**：`rh2/.venv/bin/ruff check scripts/screening_facts.py tests/test_screening_facts.py` → All checks passed；
`rh2/.venv/bin/python -m pytest tests/test_screening_facts.py -q` → **15 passed**。
证据目录改名后的 skip 行为另做了一次探针（把 `_E1` 指向不存在路径跑同一份测试）：**5 passed, 7 skipped**（纯函数层照跑，e1 层整层跳过）。
只读性：跑工具前后对 `runs/swe_grading_wiring_20260915/e1/` 与 `runs/env_probe_stage1_20260910/ledger/`
全部文件做 (路径, 大小, mtime) 快照比对，**完全相同**；测试里也有同一断言（`test_e1_inputs_are_not_modified`）。

## 2. 工具的三条关键口径

1. **逐 ID 状态只能离线重解析出来。** sidecar（`rh2.grading_diagnostics.v1`）只有计数与缺席/跳过清单，
   没有逐 ID 状态映射。工具用 `repoharness2.envpack.scoring.parse_eval_log_v2(grading_bundle, log_text)`
   重解析 eval 日志，来源标 `parser_derived`；oracle 侧直接读 `status_map.json`，来源标 `oracle`。
   两侧都按官方口径（swebench 4.1.0 `test_passed`）规约成 `passed / failed / skipped / missing`：
   PASSED/XFAIL → passed，SKIPPED 不进桶，缺席单独标 missing（官方计失败，但成因要保留）。
   工具**不改任何既有判定**，只并排放。

2. **每个值都带 `source` 与 `status`。** `source ∈ host_observation / candidate_output / parser_derived / static / oracle`；
   `status ∈ observed / missing / not_applicable`。两条容易被忽略的划分：
   - 候选段事实（`install_rc` / 秒数 / `test_rc`）与 `RH2_OBS_*` 观测都标 **`candidate_output`**，
     因为观测脚本是以**候选身份**执行的（`rh2/src/repoharness2/grading/manager.py:2731-2737`，注释原文：
     「观测输出不是可信证据，只进诊断」）。`runner_integrity_changed` 由 manager 比对前后两次
     候选身份观测得到，同样归 `candidate_output`。
   - **键缺席 ≠ 值为 null**：账本/ sidecar 里没有这个键 → `missing`（产出方版本更旧）；
     键在场但为 null → `not_applicable`（本次确实没有这个事实）。不做这个区分，缺项清单就没有意义。

3. **对 `repoharness2` 的依赖是可选的（2026-09-16 按协调者提示加固）。** 工具的绝大多数字段只需要读 JSON。
   工作树里别的会话在改 `rh2/src` 时，`import repoharness2.envpack` 可能临时抛 `SyntaxError`
   （本夜实际发生过一次，见 §6.4）。这种情况下工具**降级而不是崩**：账本 / sidecar / 工件 / oracle 侧事实
   照常产出，参考清单走不做 schema 校验的降级视图（`RawGradingBundle`），只把离线重解析与逐 ID 对账标成
   `parser_unavailable` 并把导入异常原文写进 note；`summary.json` 记 `parser_available` 与
   `parser_unavailable_reason`，stderr 另有一行警告。修好 `rh2/src` 后重跑即可补齐。
   **已验证**：`test_e1_degrades_gracefully_when_repoharness2_import_fails` 在 e1 真实数据上跑降级路径——
   10 行账本照常汇总、216 条参考清单照常读出、`scoring` / `log.sha256_verified` /
   `candidate_segment.install_segment_last_command` 等字段在场，`per_id_status` 明确标不可用（不冒充"无差异"）。

## 3. 字段可观测率（e1，10 次运行、1280 个 run 级事实）

总体 **observed 83.6%**（`summary.json` 的 `run_level_observed_rate`；加 `--full-status-maps` 时 84.0%，
差别只来自多出的三张完整状态表）。

| 来源 | observed / 总 | 率 |
| --- | --- | --- |
| `oracle` | 20 / 20 | 1.00 |
| `parser_derived` | 214 / 220 | 0.97 |
| `static` | 290 / 300 | 0.97 |
| `host_observation` | 440 / 580 | 0.76 |
| `candidate_output` | 106 / 160 | 0.66 |

| 字段组 | observed / 总 | missing | n/a |
| --- | --- | --- | --- |
| `log`、`per_id_status`、`resource` | 80/80、90/90、20/20 | 0 | 0 |
| `parser` | 174 / 180 | 6 | 0 |
| `phases_seconds` | 67 / 70 | 3 | 0 |
| `run_ref` | 95 / 100 | 0 | 5 |
| `conditions` | 160 / 180 | 0 | 20 |
| `scoring` | 85 / 110 | 0 | 25 |
| `attestations` | 46 / 60 | 8 | 6 |
| `candidate_segment` | 71 / 100 | 24 | 5 |
| `candidate` | 140 / 200 | 30 | 30 |
| `observation` | 42 / 90 | 35 | 13 |

**缺项全部可归因，没有"不明缺失"**：

- **10/10 次缺**（账本里根本没有这个键，见 §4 发现 1）：`candidate.baseline_policy_version`、
  `candidate.omitted_cache_count`、`candidate.unsupported_shape_reasons`、
  `observation.candidate_test_like_paths`、`observation.candidate_touched_conftest_or_fixture`。
- **3/10 次缺**：3 次 infra 失败的运行（pandas 主批 noop/gold + metacopy 前 noop 复跑）压根没跑到候选段，
  所以 `candidate_segment.*`、`observation.*`（导入路径/版本串/运行器摘要）、`phases_seconds.test`、
  `parser.matches_*` 没有值。
- **2/10 次缺** `attestations.setup_ok`：pandas 主批两次可信 setup 在写 `RH2_SETUP_OK=1` 之前就退出（自证为 `{}`）；
  第三次（控制面 chown 超时）写了这一行，所以只缺 2 次不是 3 次。

## 4. 与 e1 报告数字的核对

核对对象：[`e1_report_20260915.md`](../../swe_grading_wiring_20260915/e1_report_20260915.md)、
[`e1_codex_review_20260916.md`](../../swe_grading_wiring_20260915/e1_codex_review_20260916.md)。

### 4.1 全部对上的项（**已验证**）

| 项 | 报告 | 工具重算 |
| --- | --- | --- |
| mypy-12741 noop / gold F2P | 0/1、1/1 | 一致；reward 0.0 / 1.0 一致 |
| conan-13326 noop / gold F2P；解析条数 | 0/3、3/3；70（含 67 P2P） | 一致 |
| dvc-5822 noop / gold F2P；解析条数 | 0/1、1/1；50 | 一致 |
| pandas-48106 gold（metacopy 后） | F2P 16/16、P2P 失败 3/1020、解析 1037、参考缺席 3 | 全部一致 |
| pandas 三个缺席 ID | `…test_contains_raise_error_if_period_index_is_in_multi_index[Period\('2017',` 等 | 一致（三条都在 `parser.reference_missing`） |
| pandas gold 版本串 | `1.5.0.dev0+1299.g8b72297c87.dirty` | 一致 |
| mypy 安装段末命令 | codex 勘误 §4.2：实际是 `hash -r` | **一致**（工具新抽的 `install_segment_last_command` 直接给出 `hash -r`；日志 `evallog_…_39357d6f.eval.log:417-420`） |
| 逐参考状态与 oracle | 「原七次 + pandas 补跑均无 oracle 差异」 | 一致：**7 次跑到测试的运行逐 ID 差异均为 0**（含 pandas gold：两侧同缺同三个 P2P ID） |
| `runner_integrity_changed` 全 false | 是 | 一致（7 次有值的全为 false） |

另有三项**离线复核通过**，是这次新加的自检：7 次有报告的运行中，离线重解析与当时 grader 写的
sidecar 诊断逐字段一致（`matches_sidecar_verdict=true`）、与账本 `report` 四计数一致
（`matches_ledger_report_counts=true`）、eval 日志本机 sha256 与账本声明一致（10/10 `sha256_verified=true`）。

### 4.2 与报告不一致或报告未覆盖的（**发现**，不是处置结论）

1. **P2 · 账本 schema 漂移，`schema_id` 没升。** e1 两份账本的 `schema_id` 都是 `rh2.replay_grade_ledger.v1`，
   但当前 `rh2/src/repoharness2/adapters/slime/replay_grade.py` 会写而 e1 账本**一行都没有**的键有 9 个：
   `baseline_policy_version`、`omitted_cache_count`、`candidate_test_like_paths`、
   `candidate_touched_conftest_or_fixture`、`execution_failure_decision`、`image_identity`、
   `reference_missing_count`、`resource_facts`、`scripts_digest`（后几项是本机源码当前状态，其中一部分
   看起来是本夜其它会话正在加的，见 §6）。`projection` 子对象同样缺 `unsupported_shape_reasons`。
   消费方按 `schema_id` 判断字段可用性会静默拿到 None。
   工具的处置：键缺席记 `missing` + note「产出账本的 driver 版本比当前源码旧」，键为 null 记 `not_applicable`；
   每行还记 `run_ref.ledger_row_keys`（实际键集），跨账本可直接 diff。
   建议（未决定）：字段集变更时升 `schema_id` 次版本，或在账本行里记 producer 版本串。
2. **P2 · dvc-5822 的安装段和 mypy 一样是假成功，e1 报告只点了 mypy。** 报告 §4.2 写「三题
   `RH2_INSTALL_RC=0` 但 **mypy** 的 `pip install -e .` 因 build isolation 失败」。工具新抽的
   `install_segment_error_lines` 显示 dvc 安装段有 **4 条** `ERROR:`：
   `tests/requirements.txt` 与 `test-requirements.txt` 两个 requirements 文件不存在，
   以及 `pip install -e '.[tests,dev,all_remotes,all,testing]'` 因离线取不到 `setuptools>=40.8.0` 失败
   （`evallog_…_e2151710.eval.log:385-406`）；段末命令是 `python -m pip install 'pytest<8'`，所以 rc=0
   （同文件 `:419-429`）。conan-13326 是 4 题里唯一安装段 0 条 ERROR 的。
   含义：`install_rc_last_command` 在 4 题里有 3 题反映的是**收尾命令**（mypy `hash -r`、dvc `pytest<8`、
   pandas gold `pip uninstall pytest-qt -y`），不能当安装成功的证据。
3. **P3 · dvc-5822 的 `num_parsed_outside_segment=1`，e1 报告表格没有这一列。** 两次 dvc 运行都是段外 1 条
   （pandas gold 也是 1）。不影响判定（v2 入口不回退解析段外），但筛查时值得留意"测试样输出出现在标记段之外"。
4. **P3 · 账本 `reference` 字段是死字段。** driver 初始化 `row["reference"] = None` 之后再没赋过值
   （`replay_grade.py` 里没有 `row["reference"] = …`），10 行全为 null。工具不消费它。
5. **P3 · `candidate.apply_stderr_tail` 空与未采集不可分。** driver 写的是 `stage.apply_stderr_tail or None`，
   空字符串被写成 null。工具按"键在场"判 `not_applicable` 并在 note 里写明这一点。

### 4.3 条件差异（rh2 e1 vs 阶段一 oracle，逐次列在 `reconcile.md`）

10 次运行一律三项差异，且**在所有跑到测试的运行里都没有造成逐 ID 判定差异**：
`network` deny_all → none；测试执行用户 `rh2grader`(54322) → `root`；内存上限 4 GiB → 8 GiB。
镜像 ref 与 expected digest 两侧相同。这只是并排记录，不下因果结论。

## 5. 与筛查记录形状的关系

`COMMON.md` §记录形状（40 项检查、`checks{}`、`disposition_hint` 等）是**题级筛查记录**的形状；
本包产出的是它的**事实底座**：`facts.json` 只填"观测到了什么、来源是谁、缺什么"，
不写 `checks.status`、不写 `disposition_hint`、不写 `file_rules`。把 facts 翻成 `checks{}` 是下一片的活
（需要先有 40 项检查到字段的映射表，本轮没有做，记 `not_checked`）。

## 6. 未完成项与风险

1. **只在 e1 十行账本上验收过。** e2 账本"以后同形"未经验证；真跑 e2 时若键集再变，
   `run_ref.ledger_row_keys` 会把差异显示出来，但字段映射可能要补。
2. **没有把 facts 映射到 40 项检查编号**（见 §5），也没有生成 `disposition_hint`。
3. **`install_segment_*` 是启发式**：从候选段 `set -x` 回显里读最后一条命令与 `ERROR:` 行，
   fact 的 note 已写明「只作筛查线索，不作判据」。它不是安装成功的判据，也不覆盖非 pip 安装形态。
4. **没跑 rh2 全套测试**，只跑了本包新增的 `tests/test_screening_facts.py` 与两份新文件的 ruff。
   原因：本夜其它会话正在改 `rh2/src`——02:14 左右 `rh2/src/repoharness2/contracts/grading.py` 一次导入
   报 `SyntaxError: invalid syntax`（第 317 行；几秒后同一文件 `py_compile` 通过，协调者也单独提示过这一点），
   `adapters/slime/replay_grade.py` 在本会话中途多出 `EnvQualification` / `grading_image_identity` /
   `grading_scripts_digest` 等导入。在这种并发写入下跑全套，结果无法归因给本包。
   **建议由协调者在源码静止后再跑一次全套。** 本包的 15 项测试与两次 e1 实跑都是在
   `repoharness2` 可导入的时刻完成的（`summary.json` 里 `parser_available=true`）；
   工具本身对这种并发已按 §2.3 加固。
5. **`--full-status-maps` 的完整表放在 `runs/`**（3.1 MB），文档目录只放紧凑版（长列表截断到 50 条，
   计数字段始终是完整值，note 里标了截断）。两份的 `run_level_observed_rate` 因此差 0.4 个百分点（83.6% vs 84.0%）。
6. **oracle 覆盖不完整不是本工具的问题但要记住**：`runs/env_probe_stage1_20260910/ledger/stage1_offline.jsonl`
   只有 182 题，216 题齐全的是 `stage1_continuation_20260911/stage1_offline.jsonl`（mypy-12741 只在后者）。
   两份都传时后者覆盖前者；只传前者会让 mypy 的逐 ID 对账变成"oracle 缺席"。
