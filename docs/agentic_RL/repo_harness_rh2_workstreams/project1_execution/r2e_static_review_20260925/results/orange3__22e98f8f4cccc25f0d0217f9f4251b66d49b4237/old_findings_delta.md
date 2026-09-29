# orange3__22e98f8f4cccc25f0d0217f9f4251b66d49b4237：旧主张核对（old_findings_delta）

- 角色：R2E 私有主审；日期 2026-09-25。`analysis_before_history.md` 封存之后才打开历史。
- **历史来源**（`history/…/refs.json` 所列）：环境审查第一轮 P3 包中本题的 `findings.md`、`screening_record.json`、`facts.json`；`known_issues.json`（`prompt_quality_candidates` 族）；`decisions.md`；`results_20260924.md`；复现脚本；`packages/p3/README.md`。
- **为核对旧主张另开的原件**（均为上述文件所引用）：
  - `runs/r2e_env_repair_20260924/p3/dev_probe/…/` 下的 `agent_probe.log`、`dev_probe.json`、`root_init.log`；
  - `runs/r2e_rf_20260923/reconcile_all/reconcile.json` 中本题的两条；
  - M3 与 09-09 旧探针的 noop 参考日志，共 3 份，只看了失败行；
  - `runs/r2e_rf_20260923/remote/prepared_r2e/prompts.jsonl` 第 23 行；
  - `rh2/scripts/r2e_env/dev_probe_agent.sh`，用来确认复现脚本当时是怎样调用的。
- **协调者 09-25 的事实更新**（我没有独立复核，按协调者说明引用）：
  - 正式 actor 已改用派生镜像，`.venv` 前缀和 R2E 提示措辞同步修改，待 A 线审查；DEVCHECK 就是按这条正式任务面跑的。
  - 模型实际收到的题面由 prepared 任务面渲染，与 `user_prompt.txt` 同源；真实消息的捕获留到探针阶段。

## 1. 总判

历史是**环境资格**审查，其 scope 明写"不含题目质量 / 训练准入"。结论是 `env_ok` / `environment_qualified`，并把题面泄漏记为一条 open issue，留给后续筛查。本轮复核后：

- **事实层面**：旧主张基本得到确认，没有需要推翻的核心结论。
- **主要分歧在处置的轻重**：历史的判断是泄漏"不影响环境资格，但让题的训练价值打折"。本稿认为，在当前题面下，本题不宜用于能力测量，也不宜作探针候选，因此处置为 `needs_review`，建议修订公开题面（隐藏测试与 expected 不动）。
- **历史没有记录、本稿新增**：同批 3 道 orange3 题的初态已含本题修复（影响数据划分）；隐藏测试依赖仓库内可改的 `Orange/widgets/tests/base.py`（这是 R2E 通用机制在本题的适用点）。
- **历史证据有两处需要更新**：公开测试选的是与本题无关的 `Orange/tests/test__orange.py`，已被更相关的新证据取代；"本题复现是纯函数调用、不需要 Qt 前缀"没有经过不带前缀的运行验证。

## 2. 逐条核对

| # | 旧主张（出处） | 判定 | 新的决定性证据 |
| --- | --- | --- | --- |
| H1 | 题面 "Example Buggy Code" 逐行等于 gold，按字面执行得到期望值（findings；record R03、issues[0]；known_issues） | 确认，且影响更重 | 函数体 9 行与 gold 新写的函数体逐字节相同（本稿文本比对）。DEVCHECK 在正式任务面上以 agent 身份运行这段代码，`mcve_statement_code.out` 输出 `Mapping: [0, 1, 2]`。09-23 的 prepared 题面（`prompts.jsonl` 第 23 行）与 `user_prompt.txt` 逐字节相同，也含这段代码，所以模型会收到这份泄漏（按协调者说明两者同源渲染；实际消息尚未捕获）。 |
| H2 | 泄漏"不影响环境资格，但会让这题对训练的价值打折"；"题面改写或降级交题目筛查决定"（findings；issues[0].proposed_action） | 确认其范围划分；本轮给出具体处置 | 建议修订公开题面：把该代码块换成仓库真实实现（L155–157），或直接删去；测试与 expected 不动。若不修订，标注"题面给修法"，不用于能力测量或留出评测。处置 `needs_review`，等用户决定。 |
| H3 | noop 0 分，只差目标键；gold 1 分（23/23，从 `/testbed/Orange/__init__.py` 导入）（R02、R08、R16） | 确认，并补上失败原因行 | RH2 的 3 次 noop 都在 `r2e_tests/test_1.py:94` 失败，`x: array([2, 0, 1])`；3 次 gold 都是 23/23；ledger 记录 `RH2_OBS_IMPORT_PATH=/testbed/Orange/__init__.py`。 |
| H4 | 与独立 runner 逐键一致（R15：reconcile 两行 agree） | 确认 | `reconcile.json` 中本题 noop、gold 两条都是 `observed_maps_equal=true`。我直接看了 M3 的 2 份 noop 和 09-09 旧探针 noop a1，都在 L94 以同一数值失败；M3 的 2 份 gold 测试段与 RH2 gold 逐行相同。 |
| H5 | R13：同条件重复运行结果一致（record 写 2 次，facts 写 3 次） | 确认（noop、gold 各 3 次） | 三份 noop 日志除时间外逐行相同，三份 gold 日志也是；跨两个派生镜像构建（`24840fed…`、`a0135227…`）结果相同。 |
| H6 | 期望里没有非 PASSED 键（R06） | 确认 | `expected_output.json` 的 23 键全是 PASSED。 |
| H7 | 资源：gold 内存峰值 2148 MB（占限额 52%），可信 setup 136 s，测试 3.4 s（R12） | 确认 | `ledger_r2e_all_gold.jsonl:23`：`mem_peak_mb=2148.305`、`grader_trusted_setup=135.7`、`test_seconds=3.368`。P3 memprobe 得出"峰值主体是 chown 产生的页缓存"，测的是 c3fb72ba 和 f5026689，本题没单独测；按同仓推论接受，记为未核实。 |
| H8 | 探针里 `chown -R /testbed` 用了 192.60 s；"rollout 初始化里要 1.5–4 分钟"（R12；solver_conditions.notes） | 过时，只作当时的观测 | `root_init.log` 确实是 192.60 s，但当时 4 个包并行，还与中央复跑争 CPU（P3 README 自述）。正式链路现在"同一执行内只做一次整树 chown"（DEVCHECK 中 `agent_user_init_*` 为 `mode=reused`）；DEVCHECK 单次从容器启动到初始化完成约 68 s（不同机器，不能作校准）。 |
| H9 | 探针十项最小条件满足：python 指向 `.venv` 3.7.9、pytest 7.4.4、有 pip、不能出网（R05、R07、R10） | 确认，且有了更强的证据 | DEVCHECK（正式启动路径 + 真实 Claude Code）测得同样结果：`VIRTUAL_ENV=/testbed/.venv`、pytest 7.4.4、pip 24.0、`DNS_EXTERNAL=DENIED`。历史探针走的是 `docker exec` 独立诊断入口，只能说明环境卡 §2 所说的"镜像层面"。 |
| H10 | 在 cwd=/tmp 也能导入 `/testbed/Orange`（R05；solver_conditions.cwd_required=否） | 确认（只有历史证据） | `agent_probe.log`：`IMPORT_FROM_TMP=/testbed/Orange/__init__.py`。DEVCHECK 没有复测。 |
| H11 | 公开测试 `Orange/tests/test__orange.py` 收集与运行 rc=0（R09；solver_conditions.public_tests） | 过时，已被更相关的证据取代 | 这个文件只有 1 个 `_valuecount` 用例，与本题无关。DEVCHECK 以 agent 身份跑了相关文件 `Orange/widgets/data/tests/test_owcreateclass.py`：helper 用例 1 passed，整个文件 23 passed / 3 skipped（1.42 s）。 |
| H12 | 复现脚本 REPRO_OBSERVED=1，mapping 为 `[2, 0, 1]`（R09） | 确认 | `agent_probe.log` 第 135–137 行。DEVCHECK 的 `mcve_repo_function.out` 得到同样数值，另外测的 `('b','c','a')` 也是 `[2, 0, 1]`。 |
| H13 | "本题函数可直接调用"；xvfb 一项写"纯库调用不需要（本题复现是纯函数调用…）"（findings 建议；solver_conditions.xvfb） | 未核实，且表述有误导 | `dev_probe_agent.sh:90` 用 `env $PREFIX python "$REPRO"` 运行复现，`PREFIX` 就是含 xvfb 的入口前缀；DEVCHECK 也带了前缀。复现脚本导入的是 widget 模块（模块顶部导入 AnyQt 和 widget 框架），不是纯库。不带前缀能否导入，没有运行证据。 |
| H14 | 泄漏与工作区：HEAD 没有子提交，没有 remote、reflog 或残留补丁；工作区只有 `?? datasets`（软链，指向 `Orange/tests/datasets/`）、`?? install.sh`、`?? run_tests.sh`（R17、findings） | 确认 | DEVCHECK 预检 `RH2_PREFLIGHT_GIT_HISTORY=ok`，`git_sanitize` 的 refs、remotes、reflog 都为 0，porcelain 输出同样是这三行；这在新构建的派生镜像 `50fd6e31…` 上也成立。软链见 `agent_probe.log` 的 `TESTBED_LS`。"`install.sh` 不含修复"一条我没读该文件，未核实。 |
| H15 | test_files 为 `r2e_tests/{__init__.py,test_1.py}` 加 `run_tests.sh`；解题不需要改 r2e_tests 以外的测试辅助（R04） | 确认，补一条适用性说明 | 日志有 `RH2_SETUP_EXPECTED_TEST_FILES=3`。补充：隐藏测试导入仓库内 base 版的 `Orange/widgets/tests/base.py`，候选可以改它，评分时不重置（环境卡 §3 所说的通用机制）；合法修法不需要碰它。 |
| H16 | R11：`Orange/tests/sql/*` 需要 postgres，整体 skip | 未核实（与本题无关） | 隐藏测试不含 sql 用例；本稿没有查 sql 测试。 |
| H17 | known_issues 建议加一项自动检查："题面 Actual Behavior 的报错文本应出现在 noop 目标键的失败原因行里" | 对本题成立，但有局限 | 本题 L94 的 `x: array([2, 0, 1])` 与题面数值一致，这项检查会通过，却发现不了泄漏。建议流水线另加一项：把题面代码块与 gold 新增行做比对（已记入 `screening_record.json` 的 issues）。 |
| H18 | 处置 `environment_qualified`（scope：环境资格） | 确认（在其范围内） | 与本稿的 `needs_review`（scope：static_review，关于题目质量）不冲突：环境与评分可用，题面需要用户决定。 |

## 3. 本稿自身的更正与判断变化

1. **更正**：初判写了"M3 没有 noop 参考"，这是因为 `run_refs.json` 只列了 M3 的 gold。历史引用的 `reconcile.json` 显示，独立 noop 参考共有 5 份：M3 的 `facts/22e98f8f4ccc/noop_x2/out{1,2}.txt`，以及 09-09 旧探针的 `noop/a1–a3`。我直接核了其中 3 份，都在 `test_1.py:94` 以 `[2, 0, 1]` 失败。所以第 22 项由"只有 gold 有独立参考"改为 noop 和 gold 都有独立参考，第 14 项的证据也更强了。
2. **未知项更新**：
   - 初判列出的"正式 rollout 是否用派生镜像"，按协调者说明已经实施（待 A 线审查），DEVCHECK 就是在这条任务面上跑的。
   - "正式链路下的实际消息"仍记为未知，留到探针阶段；不过 09-23 的 prepared 题面与 `user_prompt.txt` 逐字节相同，泄漏会进入模型输入。
3. **处置不变**：仍为 `needs_review`（题面泄漏修法，待用户决定是否修订）。历史里没有能推翻本稿评分侧判断的证据，也没有能改变泄漏判断的证据。
4. **历史未记录的新增发现**：同批 3 道 orange3 题（`50f6a758…`、`c3fb72ba…`、`f5026689…`）的初态已含本题修复。P3 包审查过这 3 题，但没有记录这层关系。
