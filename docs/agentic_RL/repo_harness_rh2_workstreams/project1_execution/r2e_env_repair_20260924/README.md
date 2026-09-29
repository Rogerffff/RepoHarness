# R2E 48 题：环境审查与修复（第一轮，2026-09-24）

Claude（B 线）。用户 09-24 指示：R-f 通过后，先对这批 R2E 做完整的环境修复（对应 SWE-Gym 216 题的第一步），先设计流程，再把逐题工作派给 sub-agent，由 Claude 验收。Codex 09-24 的范围建议（保留机器、48 题全覆盖、五项范围、R2E 不套 SWE 的"gold 全 PASSED / rc 0"判据）已并入。本页是流程与状态入口；检查项见 [checks_r2e.md](checks_r2e.md)，决定见 [decisions.md](decisions.md)，逐题事实在 `tasks/<instance_id>/`。

## 0. 状态（09-24 收口；晚间按 Codex 复核更正、实施 T0-1 / T0-2；夜间批次二、批次三）

| 阶段 | 状态 | 证据 / 入口 |
| --- | --- | --- |
| 证据汇总（48/48 `facts.json`，含 09-24 中央复跑） | **已实施、已核对** | [facts_summary.md](facts_summary.md)；生成器 `rh2/scripts/r2e_env/collate_facts.py` |
| 开发条件探针 | **已实施、48/48 通过十项最小条件**（四包）+ 8 题由我独立重跑，统一用解析器 v3 从原始日志重算后逐字段一致（当时保存的文件里只有 3/8 完全相同，另 5 份只差旧解析器把 `No module named pip` 判成有 pip 的 `pip_ok`；Codex R3） | `rh2/scripts/r2e_env/run_dev_probe.py`；证据 `runs/r2e_env_repair_20260924/{p1,p2,p3,p4,_accept,smoke}/` |
| 中央复跑（48 × noop + gold） | **已验证**：R13 48/48 与 R-f 一致（reward 与差异集合逐条相同）；与独立 runner 对账 94/96（仅 numpy `2f4a9650` 默认 profile 两行，同 R-f） | `runs/r2e_env_repair_20260924/_rerun2/`、`reconcile_rerun2/` |
| numpy `2f4a9650` 资源配方复验 | **已验证**（09-23、09-24 各一次 noop/gold） | [recipes/task_resources_v1.json](recipes/task_resources_v1.json) |
| 四包逐题审查 | **已实施、已验收**（记录 48/48 通过机械核对） | [acceptance_20260924.md](acceptance_20260924.md)；`packages/p*/README.md` |
| 当前环境侧状态（不等于入池） | **environment_qualified 32、qualified_with_recipe 2、qualified_with_revision 9、grading_ok_open_items 5、needs_decision 0**（09-25 更正：批次三写回把 pandas `32dd55cb` 的题意问题误标为已解决，改回 grading_ok_open_items；09-24 夜批次三后的 32/2/10/4/0、最初的 42/1/2/3、晚间的 33/2/2/8/3 与批次二后的 32/2/4/10/0 已被取代）。在静态筛查、基座探针和后续可能的修复之前，没有筛选好的环境池 | [results_20260924.md](results_20260924.md)（由记录生成）；[dispositions.json](dispositions.json) |
| T0-1 / T0-2 材料修订、numpy `43e333e2` 环境配方 | **已实施、已验证**（A 线机器，真实 grader，noop / gold 各 2 次；对账计入行 8/8 一致） | [acceptance §Codex 复核更正与 T0 实施](acceptance_20260924.md)；`runs/r2e_t0_revisions_20260924/` |
| 批次二：T0-5 修复、T0-6 代表修复、T0-7 诊断、全池补查 | **已实施、已验证**（修订单 v2 + `material_v2`；pandas `4ec87eb9`、scrapy `cfed9b66` 正式 noop / gold 各 2 次；SciPy 诊断；支撑扫描、三方比对、时序键复核；Codex 修订轮复核的两个工具 P2 已修，E19） | [acceptance §批次二与复核回应](acceptance_20260924.md)；[静态筛查准备](static_screening_prep.md)；`runs/r2e_t0_batch2_20260924/` |
| 批次三：T0-6 第二步、T0-7 方案 B、Codex 批次二复核回应 | **已实施、已验证**（用户 09-24 夜按双方一致建议决定）：pandas 另 6 题补私有 conftest、期望按修复后 gold 重新核定；orange3 `9b5494e2` 用 SciPy 1.5.4 环境配方（新环境步骤 `env_v2`）并修订两个恢复键；修订单 v3、pins v4；7 题正式 noop / gold 各 2 次、28 行与试跑逐键相同。回应复核：两个 CLI 测试与未跟踪的 `tests/test_screening_facts.py` 的导入路径污染已修（撤回"交 A 线"的错误归因），静态筛查公开包改为实际解题工作树 | [decisions E20–E24](decisions.md)；[acceptance §批次三](acceptance_20260924.md)；`runs/r2e_t0_batch3_20260924/` |
| 静态筛查固定材料 | **已准备**：48 题公开包（含实际解题工作树）、私有包、历史包；15 张镜像逐文件比对一致；33 题缺 `install.sh` 等只在镜像里的文件，逐题写明 | [r2e_static_prep_20260924/materials.md](../r2e_static_prep_20260924/materials.md)；`runs/r2e_static_prep_20260924/v1/` |
| 待用户决定 | 环境阶段无。T0-3、T0-4、coveragepy `5dbbe143` 与 orange3 `9b5494e2` 的两个 scorer 键交后续题意与评分质量筛查；静态筛查何时开工、是否派审查 sub-agent 由用户定 | [decisions.md](decisions.md)；[静态筛查准备](static_screening_prep.md) |

## 1. 目标与边界

**目标**：为 48 题各形成一条可核对的环境资格结论——在派生镜像（`r2e_derive_v1`）+ 真实 RH2 grader + 真实解题身份（agent/54321）条件下，环境层面是否支持解题与判分；缺口按类别给出**版本化**修复配方，或（涉及 expected / 隐藏测试 / gold 的）材料修订**提案**。

**不做**：不改 expected、gold、隐藏测试（只出提案，走既有决策流程，用户决定）；不改全局默认 profile；不重建派生镜像（配方 v1 不变，除非发现镜像层缺陷）；不接正式 actor（D4=B 归 A 线，本轮只给 CPU 侧证据）；不判题意质量、反作弊或训练价值（那是后续筛查环节）。

**与 SWE-Gym 轮的三点差别**：R2E 没有安装段（镜像预装，账本 `install_skipped=true`）；期望映射可含 FAILED / ERROR（20 题，gold 的入口 rc 可为 1）；隐藏测试由 root 私有目录在评分时恢复。所以 SWE 轮的"安装全成功 / gold 全 PASSED / gold 退出码 0"三条判据不适用，这里的通过条件是：R01 身份一致、R02 noop 的 0 来自目标测试、R08 gold 达到来源定义（或差异已归因）、R15 与独立 runner 逐键一致、R13 重复一致、探针最小开发条件满足。

## 2. 证据来源（既有，不重跑）

| 来源 | 内容 | 位置（本地） |
| --- | --- | --- |
| 可信摄入面 | 48 题身份、期望映射、入口脚本、隐藏测试清单、题面（pins 三级校验） | `docs/…/s2_r2e/`（经 `load_trusted_r2e_ingest_outputs`） |
| R-f 真机账本 / 日志 / sidecar | 48 noop + 48 gold + 代表题 12 + 再资格 2 + numpy 放大资源 2；含 `expected_match` 逐键差异、`RH2_OBS_IMPORT_PATH`、六段耗时、峰值内存 | `runs/r2e_rf_20260923/remote/` |
| 派生镜像复核 | 逐题 21 项（导层完整性、隐藏测试树、入口 sha、HEAD、git 清理、两种 uid 的解释器 / 私有目录、driver 预检） | `runs/r2e_rf_20260923/remote/r2e_derived/<iid>/facts.json` |
| 逐键对账 | RH2 vs M3 / 09-09 独立 runner：94/96 agree，2 行 numpy `2f4a9650`（资源） | `runs/r2e_rf_20260923/reconcile_all/` |
| M3 来源镜像事实（09-16） | Python 版本、来源解释器路径、导入方式（editable finder / 路径项）、cwd 不在 /testbed 时能否导入 | `runs/env_overnight_20260916/M3/facts/<commit12>/` |
| Codex R-f 复核 | 通过判定与三处更正、numpy 资源结论 | [r2e_rf_review_20260924/README.md](../r2e_rf_review_20260924/README.md) |

汇总后的逐题事实：`tasks/<iid>/facts.json`（schema `rh2.r2e_env_facts.v1`），总表 [facts_summary.md](facts_summary.md)。汇总器只归纳，不裁定。

**汇总后已知的全池事实（09-24）**：48/48 派生镜像复核通过、R01 一致；noop 48 个 0 且全部来自目标测试的 mismatched（R02 pass）；gold 45 个 1；grader 侧导入路径 48/48 在 `/testbed`；对账 94/96 行 = 47/48 题一致（只有 numpy `2f4a9650` 的 noop/gold 两行因默认资源不一致；原写"46 题"，Codex R3 更正）。gold=0 的三题：coveragepy `016af5f6`（期望 FAILED、实测 PASSED 的参考状态问题）、datalad `58ba5165`（隐藏测试依赖 gold 未带的仓库测试模块）、numpy `2f4a9650`（默认 1 GiB `/tmp` 不够；6 GiB `/tmp` + 12 GiB 内存下 gold=1）。汇总器标出的待人工项：期望含非 PASSED 键 20 题（09-24 晚更正：原写 16）、M3 显示"cwd 不在 /testbed 时导入失败"14 题（aiohttp ×5、datalad ×2、numpy ×7）、orange3 两题峰值内存超限额 60%、dirty tree > 2 行 19 题（aiohttp / orange3 / pandas 的来源镜像自带改动）、R13 重复一致性 40 题只有一次运行（中央复跑补）。

## 3. 检查项

R2E 适配版 R01–R20（对应 40 项清单的第 1–4、6–15、19–20、29、37–39 项），每项写明判定依据、自动 / 人工、证据形态与状态语义：[checks_r2e.md](checks_r2e.md)。汇总器自动填 R01、R02、R08、R12、R13、R15、R16；探针填 R05、R07、R09、R10、R17 的事实；其余由 sub-agent 读证据判定。状态词汇沿用 `pass / issue / unknown / not_applicable / not_checked`，缺失不填 0，未报错不自动 pass。

## 4. 工具与命令

```bash
# 1) 只读汇总（本地；证据已回传）
rh2/.venv/bin/python rh2/scripts/r2e_env/collate_facts.py --repo-root . \
  --evidence-root runs/r2e_rf_20260923 --m3-root runs/env_overnight_20260916/M3 \
  --out-dir docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/tasks \
  --summary-md docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/facts_summary.md \
  [--extra-evidence runs/r2e_env_repair_20260924/_rerun2=/work/envrepair/_rerun2/]   # 中央复跑回传后并入（R13）

# 1b) 验收：逐题记录的机械核对（schema、R01–R20 覆盖、状态词、证据引用存在、分类 / 处置词汇）
rh2/.venv/bin/python rh2/scripts/r2e_env/check_records.py --repo-root . \
  --tasks-dir docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/tasks

# 2) 开发条件探针（机器；派生镜像；agent/54321；rollout 资源与能力；无网络）
/work/code/rh2/.venv/bin/python /work/code/rh2/scripts/r2e_env/run_dev_probe.py --repo-root /work/code \
  --overlays /work/r2e_derived/overlays.jsonl --task-ids <iid,…> --out-dir /work/envrepair/<pkg>/dev_probe \
  [--repro-dir /work/envrepair/<pkg>/repros] [--activation none|r2e_venv|swe_conda]

# 3) 真实 RH2 复跑（机器；R-f 冻结代码快照；noop / gold 分账本；numpy 资源配方用 RH2_GRADER_* 环境变量）
#    命令形态见 ../r2e_grading_wiring_20260920/runbook_rf.md §3；本轮输出只写 /work/envrepair/<pkg>/ 或 /work/envrepair/_rerun2/
```

探针做什么（`run_dev_probe.py` 模块说明有全文）：按 `rollout_trusted_init_script` 的步骤建 agent 用户、`chown -R /home/agent` 与 `/testbed`、建 `/rh2`；再以 `docker exec -u 54321 -w /testbed -e HOME=/home/agent` 运行 `dev_probe_agent.sh`：解释器与 `python` 解析、pytest、包从 `/testbed` 与 `/tmp` 两处导入、pip / `pip check`、各目录可写性、cgroup 限额、git 状态 / 子提交 / 引用 / reflog / 远端、隐藏测试私有目录不可读、`run_tests.sh` 可见性、残留补丁文件、仓库自带公开测试的收集与限量运行、可选公开复现脚本、出网被拒。输出 `dev_probe.json`（`derived.min_dev_conditions_ok` 是十项最小条件的合取）。 09-24 P1 指出旧解析器丢掉 `WHICH_*` 行（键名含小写）：解析器改为 v2 并加 `--reparse`，各包本地的 `dev_probe.json` 都按原始 `agent_probe.log` 重建（`parser_version=2`，derived 字段不变、补回 WHICH_*）；远端副本保持原样。

**试跑结果（5 题，本地 `runs/r2e_env_repair_20260924/smoke/`）**：coveragepy `016af5f6`、pillow `3ac9396e`、orange3 `22e98f8f`、numpy `18b7cd9d`、datalad `58ba5165` 最小条件全部满足；`chown -R /testbed` 11 s（coveragepy）/ 15 s（pillow）/ 12 s（numpy）/ 53 s（datalad）/ 100 s（orange3），探针本体 2–13 s。已看到的解题侧事实：numpy 从 `/tmp` 导入失败（`ModuleNotFoundError`；准确说法是 `/testbed` 必须在 sys.path 上——就地构建、没装进 venv，P2 更正：脚本放在 /testbed 之外时即使在 /testbed 下运行也导入失败）；numpy / pillow / datalad 的 venv **没有 pip**；orange3 顶层 `Orange/tests/sql/*` 全 skip（需要 postgres，探针已改为先取顶层 `test_*.py`）；coveragepy 的 `setup.cfg` 带 `--failed-first`，禁用 cache 插件会让 pytest 用法错误（探针已改为把 cache 目录指到 `/tmp`）；`docker exec` 继承镜像 ENV（`PATH` 首项 `/testbed/.venv/bin`、`VIRTUAL_ENV`），所以 `--activation r2e_venv` 与 `swe_conda`（当前 `materialize.BASH_ENV_CONTENT`）在 CPU 侧结果相同——但正式链 `RolloutTaskSpec.expected_interpreter_prefix` 默认仍是 conda 前缀，R2E 任务面未给 `.venv`，启动前解释器核对会把 R2E 判成 `rollout_activation_check_failed`；这是 A 线接缝（见 decisions E09）。

## 5. 每题流程

1. **汇总**（已完成）：`facts.json` 给出身份、期望、环境、派生镜像、全部 RH2 运行、对账与自动检查。
2. **读证据**（sub-agent）：核自动检查；期望里每个非 PASSED 键读 gold 日志里的原因行（`rh2_runs[].non_passed_reasons`）并分类：上游该提交本来就失败 / 缺可选依赖或 fixture / 需要网络或外部服务 / 资源 / 顺序依赖 / 不明；noop 的 mismatched 键与题面对得上（R16）。
3. **探针 + 公开复现**：只据公开题面写 `repros/<iid>.py`（见 [repros/README.md](repros/README.md)），探针带 `--repro-dir` 运行；探针结果回传本地 `runs/r2e_env_repair_20260924/<pkg>/dev_probe/`。
4. **分类**：`env_ok`（环境无缺口）/ `resource`（需逐题资源配方）/ `material`（expected / 隐藏测试 / gold 的问题，只出提案）/ `solver_condition`（解题侧条件需要在题包或系统提示里声明，如 cwd、无 pip、无网络）/ `unknown`（证据不足，写清缺什么）。
5. **修复**：资源配方进 `recipes/task_resources_v1.json`（逐题 `RH2_GRADER_*` 值 + 证据）；材料修订写 `material_revisions/<iid>.md`（问题、证据、两到三个选项、推荐、长期代价、以后还能改什么）；解题侧条件写进 `screening_record.json` 的 `solver_conditions`。不改 `s2_r2e/`、不改生产代码、不重建镜像。
6. **定向复跑**：只对改变了条件的题跑 fresh noop + gold（同一账本目录、独立 run_id），保留原条件结果作对照；不改条件的题用中央复跑的第二次结果。
7. **记录**：`tasks/<iid>/screening_record.json`（形状见 checks_r2e.md §3）+ `tasks/<iid>/findings.md`（≤ 30 行：结论、依据、缺口、建议）。
8. **验收**（Claude，§8）。

## 6. 分工

| 包 | 题（instance_id 前缀） | 已知焦点 | 远端目录 | 本地证据目录 |
| --- | --- | --- | --- | --- |
| P1 | aiohttp ×5、coveragepy ×5 | coveragepy `016af5f6` 参考状态；aiohttp 5 题"导入需 cwd=/testbed"、dirty tree 4–7 行；期望 FAILED 键 3 题 | `/work/envrepair/p1/` | `runs/r2e_env_repair_20260924/p1/` |
| P2 | datalad ×5、numpy ×7 | datalad `58ba5165` 测试材料；numpy `2f4a9650` 资源配方；numpy ×7 / datalad ×2 导入需 cwd；venv 无 pip；期望 FAILED 键 3 题 | `/work/envrepair/p2/` | `…/p2/` |
| P3 | orange3 ×7、pandas ×7 | xvfb / Qt、`chown` 100–175 s、`c3fb72ba` `f5026689` 峰值内存 ≥ 60% 限额；pandas 7 题期望 ERROR 键（1–17 个）、dirty tree 6 行 | `/work/envrepair/p3/` | `…/p3/` |
| P4 | pillow ×7、scrapy ×5 | pillow `3ac9396e` 自定义 unittest runner、venv 无 pip；期望 FAILED 键 5 题 | `/work/envrepair/p4/` | `…/p4/` |

派发方式：四个 sub-agent 并行（Agent 工具，Opus），各自只写自己包的 `packages/<pkg>/README.md`、`tasks/<iid>/{screening_record.json,findings.md}`、`repros/<iid>.py`、`material_revisions/<iid>.md`，以及远端 `/work/envrepair/<pkg>/`。共享文件（本页、decisions.md、known_issues.json、dispositions.json、recipes/）由 Claude 单一写入，sub-agent 的提案写在包 README 里。

## 7. 远端约定

机器地址与密钥只在 `CLAUDE.local.md`（"R2E R-f 对账机"一节），不写入本目录。规则：一律绝对路径；超过一分钟的任务用 `systemd-run --unit=… --collect --working-directory=/work/code/rh2 -p StandardOutput=append:<log> -p StandardError=append:<log>`，等待用 `systemctl is-active`；只写 `/work/envrepair/<pkg>/`；不改 `/work/replay`、`/work/r2e_derived`、`/work/code`（代码是 R-f 冻结快照，`r2e_snapshot.sha256` + `r2e_env_tools.sha256` 可核）；不构建 / 删除镜像，不 `docker system prune`；每个包同一时刻最多一个探针进程和一个复跑进程；跑前看 `df -h /`（09-24 起步 46 GB 可用，每个容器的 `chown -R /testbed` 会临时涨 0.35–2.3 GB）；结束时 `docker ps -a` 不得残留自己起的 `rh2-devprobe-*` / `rh2-*` 容器。spot 机器可能被回收：每题结束就把账本 / 日志 / 探针结果 rsync 回本地。

## 8. 验收标准（Claude）

对每个包：① 每题都有 `screening_record.json`，`checks` 覆盖 R01–R20（不适用写理由），每条 `issue` 与关键 `pass` 都有可打开的证据引用（相对仓库根；`check_records.py` 机械核对）；② 抽 1–2 题在机器上重跑探针并与记录对照；③ 复跑账本行与 R-f 结果一致或差异已归因（跑 `collate_facts.py` 把新账本并入，看 R13）；④ 远端无残留容器，`/work/replay`、`/work/r2e_derived`、`/work/code` 的清单核对通过；⑤ 仓库里 `s2_r2e/`、`rh2/src`、`rh2/scripts`（本轮工具除外）无改动；⑥ 材料修订只有提案，资源配方有版本与证据；⑦ 包 README 区分建议 / 已决定 / 已实施 / 已验证。验收结果与逐题处置汇总到本页 §0 与 [decisions.md](decisions.md)，并登记到 [environment_pipeline.md](../environment_pipeline.md) §6。

## 9. 已知三题的具体要求

- **numpy `2f4a9650`**（P2）：不找最小配置；把已验证的 `/tmp` 6 GiB + 内存 12 GiB 作为该题的逐题资源配方 v1（`recipes/task_resources_v1.json`），用中央复跑里的 `numpy_bigtmp` 两行再确认一次；不改全局默认。写清 `_savez` 两个副本合计略大于 4 GiB、峰值约 4.3 GiB 的依据（Codex 09-24）。
- **coveragepy `016af5f6`**（P1）：期望 `MockingProtectionTest.test_os_path_exists=FAILED`，RH2 与 M3 独立 runner 都实测 PASSED（noop 与 gold 都如此；09-09 runner 没跑过这题——P1 更正）。这是参考状态问题：查该测试在该提交下为何被记成 FAILED（来源 runner 的环境差异？平台？），给材料修订提案（例如 expected 该键改 PASSED = 修订版 expected，或该键剔除），不改环境。
- **datalad `58ba5165`**（P2）：gold 后仍有 1 键不符；查隐藏测试对仓库测试模块（gold 未带、按 `is_gold_excluded_test_path` 排除的路径）的依赖，区分"缺测试支撑材料（应作为私有材料补进评分面）"与"属于模型该做的改动"；给提案。

三题的任何 expected / 测试 / gold 变更都只是提案（T0），由用户按既有决策流程决定；本轮不改摄入面。

## 10. 记录去向

`decisions.md`（E 编号，T1 决定与 T0 提案）、`known_issues.json`（按族：题号、证据、状态）、`dispositions.json`（隔离 / 待恢复条件）、`recipes/`（版本化资源配方）、`material_revisions/`（提案）、`repros/`（公开复现脚本）、`packages/<pkg>/README.md`（包报告）、`tasks/<iid>/`（facts / dev_probe 摘要 / screening_record / findings）。原始账本、日志、探针输出在本地 `runs/r2e_env_repair_20260924/`（git-ignore）。

## 11. 结果与收口（2026-09-24）

**环境资格结论（48 题；09-24 晚按 Codex R1 更正）**：~~环境层面 48/48 支持解题与判分~~。已验证的是来源评分的复现与解题侧最小条件——派生镜像与身份一致（R01）、noop 的 0 全来自目标测试（R02）、两次真实 RH2 运行逐题一致（R13，R-f + 09-24 中央复跑）、与独立 runner 逐键一致（R15，两轮各 94/96，差异只在 numpy `2f4a9650` 默认 profile 的资源假阴性，配方下 4/4 一致）、真实解题身份下十项最小开发条件 48/48 满足、公开复现脚本 48 个（46 个在 base 上复现题面问题，2 个复现不出的是题面问题）。gold=1 的 45 题 + 配方下的 numpy 共 46 题可判分；coveragepy `016af5f6`、datalad `58ba5165` 的 gold=0 都不是环境缺口，而是材料问题（提案）。**09-24 晚**：这两题按用户批准的修订实施后 gold=1（各 2 次），48 题在各自当前材料与配方下 gold 都是 1；但"可判分"不等于"环境合格"，合格的是下表前三行（09-24 夜批次三后共 44 题；批次二后是 38 题，更早写的 37 题已过时）。

| 环境侧状态（09-24 夜批次三后，不等于入池） | 数 | 说明 |
| --- | --- | --- |
| `environment_qualified` | 32 | 探针十项满足、R01/R02/R08/R13/R15 pass、无未完成项 |
| `qualified_with_recipe` | 2 | numpy `2f4a9650`（资源配方：`/tmp` 6 GiB + 内存 12 GiB）、numpy `43e333e2`（环境配方 `env_pins_v1`：hypothesis 6.24.1，E15） |
| `qualified_with_revision` | 10 | coveragepy `016af5f6`（`r2e-mr-001`，T0-1）、datalad `58ba5165`（`r2e-mr-002` + `material_v1`，T0-2）、scrapy `cfed9b66`（`r2e-mr-003`…`005` + `material_v2`，T0-5）、pandas `4ec87eb9`（`r2e-mr-006`、`007` + `material_v2`，T0-6 代表题）、pandas 另 6 题（`r2e-mr-008`…`019` + `material_v2`，T0-6 第二步） |
| `grading_ok_open_items` | 4 | orange3 `9b5494e2`（T0-7 方案 B 已实施：`env_pins_v2` + `r2e-mr-020`；两个 scorer 键原因未定位，保持未完成项）、pillow `2b061b68` 与 scrapy `9a15fcf8`（T0-3 / T0-4，用户决定交质量筛查）、coveragepy `5dbbe143`（扫描发现的旧测试辅助，交质量筛查）；评分可复现 |
| `needs_decision` | 0 | — |
| 分类 | — | solver_condition 25、material 14、env_ok 8、resource 1（口径 E11；分类记根因，修好后不改） |

**解题侧条件（全池，写进各题记录，是否进题面由任务面定）**：无网络（loopback 可用）48/48；venv 无 pip 27/48（有 pip 的是 aiohttp `1c1c0ea3` `22a12cc2` `4075c653`、coveragepy ×4、orange3 ×7、pandas ×7）；`/testbed` 须在 sys.path 上且跑测试用 `python -m pytest` 12 题（aiohttp ×5、numpy ×7）；orange3 widget 测试须带入口的 xvfb 前缀；datalad 需要 git 身份；13 题的仓库公开测试有与本题无关的失败或收集问题；公开提示的 conda / pip 措辞对 R2E 不成立（E09，交 A 线）。

**期望非 PASSED 键（20 题、93 键；原写 16 题，09-24 晚更正；T0-1 实施后 coveragepy `016af5f6` 的 1 键改为 PASSED；09-24 夜 T0-5 / T0-6 代表题修订后 scrapy `cfed9b66` 3 键、pandas `4ec87eb9` 2 键也消失，按当前材料是 17 题、87 键；09-24 夜批次三后 pandas 另 6 题的 56 键消失、orange3 `9b5494e2` 两个恢复键改为 PASSED，按当前材料是 11 题、29 键）都有原因记录；没有一个是缺依赖 / 缺资产 / 需网络 / 资源，但"死键不会被合法修复翻转"多数是推断，orange3 四键同源的推断已被 09-24 夜的诊断否定——两键是 SciPy 不兼容，两个 scorer 键另有原因（E17）**：pandas 58 键 fixture 不可达（隐藏测试搬到 `r2e_tests/` 后 conftest 不可达）、datalad 10 键 fixture 冲突 + 1 键 `quote` 行为、aiohttp 5 键（旧代码在 3.9 上本就失败 ×2、C 扩展未构建 ×3）、pillow 4 键 `pytest.warns(None)`、scrapy 2 键 `-W ignore` + 3 键搬迁伪影 + **2 键可被合法修复翻转**（`9a15fcf8`，实测 over-fix 判 0）、orange3 4 键 sklearn/SciPy 不兼容 + 3 键上游伪影、coveragepy 1 键参考环境差异。族级记录在 [known_issues.json](known_issues.json)。

**资源**：只有 numpy `2f4a9650` 需要逐题配方；orange3 峰值是 `chown -R` 的页缓存，2 GiB 限额下 gold 仍 1（E12），不设档位。

**待用户决定（T0）**：见 [decisions.md](decisions.md) 表；T0-1 / T0-2 / T0-5 已批准、已实施、已验证，T0-6（代表题与第二步）与 T0-7 方案 B 也已实施并验证；T0-3、T0-4 按用户决定交后续质量筛查。环境阶段已无待决定事项。~~本轮没有改 `s2_r2e/`、expected、隐藏测试、gold、生产代码或镜像。~~ 09-24 晚按用户批准改了：`s2_r2e/` 新增封板修订单与 pins v2 / manifest v2，两题的期望或隐藏测试经修订单重放；生产代码（ingest 重放修订、评分面 `material_revisions` 字段、消费期校验）；派生配方新增 `material_v1` 与 `env_v1` 两步；受影响的三题重建派生镜像。gold 补丁与其余 45 题的材料未改。

**工具改动（本轮已落；09-24 夜又加修订单 v2、`material_v2.sh`、`scan_hidden_support.py` 支撑缺口扫描、`expected_provenance.py` 期望来源三方比对、`render_results.py` 结果表生成）**：探针解析器 v3（`WHICH_*` 键、`pip_ok`）+ `--reparse`；汇总器去 ANSI、M3 导入判断看整段、支持额外证据根、R12 提示语；新增 `check_records.py`（记录机械核对）、`apply_r13.py`（复跑结果写回记录；09-24 晚去掉兜底提升）。09-24 晚又改：`build_r2e_derived.py` 支持材料步骤与 `--env-pins` 环境步骤（复合配方身份、完整性只放行登记路径）；`reconcile_r2e.py` 认修订（期望修订两侧按修订后期望比较、M3 账本用倒放出的来源期望互核；隐藏测试修订行单列）；新增 `render_results.py`（由记录生成结果表）。09-24 夜批次三又加：环境步骤 `env_v2.sh`（Python 3.7 可用的读版本方式，配方条目用 `env_step` 选）；`extract_fixtures.py` 的 `requested_fixtures`（从隐藏测试原文一次算全缺失 fixture）；`check_records.py` 未完成项词表加 `grading_keys_unexplained`；静态筛查固定材料工具 `r2e_static_prep_20260924/prepare_materials_r2e.py`。**下一轮待办**：探针加裸 `pytest` 检查与 git 身份 / hypothesis / pytest 版本、公开测试由审查者指定或按隐藏测试定位、`PUBLIC_*_TAIL` 记根因行、复现脚本经 stdin 运行、前缀带解释器参数、`summary.json` 按批命名；汇总器三方比对期望来源（期望 / 宿主机记录 / 镜像 gold）、从 FAILURES 段抽首条 `E` 行；摄入期静态检查（隐藏测试导入被 gold 排除的仓库测试模块、搬迁伪影、题面报错文本 vs noop 原因）。

**交 A 线**：E09（R2E 任务面的 `.venv` 激活与解释器前缀、公开提示措辞）；grader 记 `memory.stat` / `memory.events`（R12 判据）；`chown -R` 成本与两侧 uid 统一（派生配方预置属主）；~~候选在 `/testbed` 根目录新建 conftest 可翻转 pandas ERROR 键（hygiene / 反作弊面，只记录）~~（pandas 7 题的期望已无 ERROR 键，这条路径随 T0-6 修订消失；候选改测试支撑文件的一般性问题仍归 hygiene 面）；datalad 类任务的 git 身份由 rollout 初始化还是提示提供。

**机器**：R-f 机器远端 0 容器、代码快照核对通过、`/work/envrepair/` 全量回传本地（`runs/r2e_env_repair_20260924/`）；09-24 晚该机 SSH 报主机密钥变化，未绕过校验，按不可用处理。T0 验证、批次二、批次三与静态筛查材料的镜像核对都在用户借给的 A 线机器上的独立目录 `/work/b_r2e/` 完成：0 容器、无运行中的 unit，证据回传 `runs/r2e_t0_revisions_20260924/`、`runs/r2e_t0_batch2_20260924/`、`runs/r2e_t0_batch3_20260924/`、`runs/r2e_static_prep_20260924/`；B 线在该机留有 15 张来源镜像（含批次三为核对脏树新拉的 aiohttp `240da100`、`61833518`）、23 张派生镜像、约 19 GB 构建缓存和 `/work/b_r2e/`（约 5.3 GB），A 线自己的文件与镜像未动，清理由用户决定（命令记在本机不跟踪的 CLAUDE.local.md）。
