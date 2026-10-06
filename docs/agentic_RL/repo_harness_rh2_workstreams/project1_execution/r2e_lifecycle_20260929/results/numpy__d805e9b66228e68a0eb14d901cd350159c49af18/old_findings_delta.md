# numpy d805e9b6：旧结论对照（old_findings_delta）

2026-09-29，R2E 私有主审（单题闭环试行，统一标准 v1）。本文在 `analysis_before_history.md` 封存之后写成。

- **路径约定**：
  - `PUB/`、`PRIV/`：与分析稿相同。
  - `HIST/` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/`。
  - `LIFE/` = `runs/r2e_lifecycle_20260929/`。
- **读过的历史材料**：`runs/r2e_static_prep_20260924/v3/history/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/refs.json` 列出的全部 8 项：
  - 本题的 `screening_record.json`、`findings.md`、`facts.json`；
  - `known_issues.json`、`decisions.md`、`results_20260924.md`；
  - 公开复现脚本 `repros/numpy__d805….py`；
  - `packages/p2/README.md`。
- **这些历史材料是什么**：09-24 环境审查第一轮（P2 包）的环境资格记录。它回答的是"环境能不能正确评分、能不能开发"，没有做题意和测试质量审查；按其 E03，环境资格与题目质量分开记。因此：
  - 下面多数条目的判定是"确认"；
  - 本轮的主要发现（S1）在历史里没有对应条目，不算推翻。
- **新证据**：都在新机器上，派生镜像 `sha256:c080fc6b…`，配方 `r2e_derive_v1+sysconfig_v1`。
  - 正式复验：`LIFE/env_verify/ledger_l0_noop.jsonl:6` 与 `ledger_l0_gold.jsonl:6`。
  - devcheck：`LIFE/devcheck/numpy__d805…/`，其中 `orig/attempt.json`、`orig/captures/*.out`、`private_control.json`。
  - 候选正式评分：`LIFE/inv/numpy_d805/ledger_{KDE,KDC,KDF,KA5,KA5b}.jsonl:1` 与 `logs_*/`。
  - 私有行为核对：`pcheck_*.json`。

## 1. 旧结论逐条对照

| 旧结论（出处） | 判定 | 新的决定性证据 |
| --- | --- | --- |
| 分类为 `solver_condition`，处置为 `environment_qualified`（`HIST/tasks/…/screening_record.json` 的 classification 与 disposition；`HIST/results_20260924.md:32`） | 环境层面**确认**，并已在新镜像上复验；处置在题目质量层面**被本轮取代** | 新镜像上 noop 0（228/229）、gold 1（229/229）；devcheck 13 项全部为真。本轮发现测试层 S1，处置改为 `needs_repair`。旧处置的范围本来就不含测试质量，所以不是推翻 |
| R02：noop 的 0 只来自目标键 `TestMaskedArray.test_str_repr` | 确认（第 3 次） | env_verify 的 noop：mismatched 只有这个键，原因是示例 repr 的 AssertionError |
| R03：公开复现成功（判据是 data 段的 `--` 多于 3 个，REPRO_OBSERVED=1） | 确认，但**不完整** | devcheck 的 `captures/repro_issue_repr.out` 与本审推导一致：49 个 `--`、1950…1999、没有省略号。旧判据只数 `--`，没有对照题面的 Actual 块；那段写的"31 个 `--` 后接 `..., 1997 1998 1999`"和"up to 1000 elements"都与 base 不符。本轮新增 P4 |
| R03 附注：全局提示写的是 conda testbed（E09） | **过时** | v3 起 `public_hints` 写的是 `.venv`（`PUB/public_bundle.json:15`）；devcheck 激活核对得到 `ACT_VIRTUAL_ENV=/testbed/.venv`、`RH2_BASHENV_WRITE=DENIED` |
| facts：`source.public_hints_mention_conda: true` | **过时** | 理由同上 |
| R05：`.venv` 3.7.9、pytest 7.4.4、没有 pip、就地构建、`/testbed` 必须在 sys.path 上 | 确认 | devcheck 的 `captures/env.out` 与 `import_version.out`：uid 54321、`No module named pip`、pytest 7.4.4、numpy 从 `/testbed/numpy/__init__.py` 导入 |
| R05：有 gcc / make / git | 未核实 | 本题是纯 Python 修复，不需要构建，这一条对本题没有影响 |
| R06：期望里没有 FAILED / ERROR 键 | 确认 | `PRIV/expected_output.json` 的 229 个键全是 PASSED |
| R07 / R17：权限正确、隐藏测试不可读、HEAD 没有子提交 | 确认（新镜像） | devcheck 预检的 INTERPRETER、HIDDEN_TESTS、GIT_HISTORY 都是 ok；`git_sanitize` 显示 refs 0、remotes 0、reflog 0、unreachable 0，HEAD 为 `25e3ebf4` |
| R09：公开 `numpy/ma/tests/test_core.py` 229 passed（uid 54321） | 确认 | devcheck 的 `pytest_ma_core_full`：229 passed，1.73 s；应用 gold 后同样 229 passed |
| R10：没有网络，本题也不需要下载 | 确认 | devcheck 的 `prelaunch.json` 显示 `DNS_EXTERNAL=DENIED`；全部命令都在这个条件下完成 |
| R12：峰值约 282 MB（限额 4 GiB） | 确认 | 新镜像 noop 294 MB、gold 283 MB；测试阶段 3–5 s |
| R13：同条件 noop / gold 重复结果一致 | 确认并扩展 | 旧镜像 2 次、新镜像 1 次，逐键一致；另有 M3 参考 gold 2 次 |
| R14：`candidate_test_like_paths=[]` | 确认 | 新镜像的 gold 行与 5 个候选行都是 `[]` |
| R16：目标键对应题面"一维大掩码数组的 repr 截断"，noop 的失败原因是 AssertionError | 作为环境层面的对应关系**确认**；**不足以说明测试质量** | 这个键只断言题面示例的字面值；K-DE、K-DC、K-DF 都得了 1.0（见 §2）。R16 当时只核对"键与题意对得上"，没有做退化探测 |
| R18："不需要修复配方，也不需要材料修订" | 前半句确认；"不需要材料修订"这半句**推翻**（范围不同） | 确实不需要环境配方；但测试层需要 R-c（两处断言）。旧结论只看了环境 |
| issues：`/testbed` 必须在 sys.path 上；裸 `pytest` 收集会失败（在 18b7cd9d 上实测，本题是推断） | 前半确认；后半仍是推断，**未核实** | devcheck 在 `/testbed` 下用 `python -c` 和 `python -m pytest` 全部成功；本轮没有测裸 `pytest` |
| install.sh 对解题者可见，但不含修复（R03 附注，引用 followups A） | 未核实（沿用历史结论） | 本审没有读 install.sh，它不在公开包里；devcheck 的初态确实有 `?? install.sh` |
| `known_issues.json` 的 prompt_quality_candidates 没有列本题 | **遗漏**（本轮新增 P4） | 同一条目里建议的检查思路是"题面 Actual 描述应能在 noop 的失败信息里找到"，按这个思路本题会被标出 |

## 2. 历史没有覆盖、本轮新增的结论

1. **S1（T2c，v1 第 2 步）**：唯一的核心断言就是题面示例原样（`PRIV/hidden_tests/test_1.py:454-461`）。这是静态结论，已经确定。
2. **S1（T2b，第 3 步）**：退化候选 K-DE 只把截取量写死为 750，正式评分 1.0（229/229）。私有核对显示 n=500 时显示 1000 个 token，也就是每个值出现两次（`LIFE/inv/numpy_d805/pcheck_KDE.json`）。
3. **S1（第 4 步）**：两个部分修复都得了 1.0，并在同一核心要求的其它实例上违例：
   - K-DC：n=500 仍然只显示 100 个值，静默丢掉 400 个；
   - K-DF：n=100000 只显示 100 个值，也没有省略号。
4. **S2**：
   - G1 → T3：gold 在 threshold 大于 1500 时仍然静默丢值；多维数组没有改动，属题外。
   - T3：子类打印不在评分范围内。
5. **P4**：题面的 Actual 块与 base 的实际输出不符。
6. **X1**：本题 gold 与隐藏断言出现在同仓另外 5 题的公开初态里；本题初态里含 a5ea773e 的修复。
7. **通用 E3**：隐藏测试依赖候选可以修改的 `numpy/ma/testutils.py`。

## 3. 主审对自己初判的修改

| 初判（`analysis_before_history.md`） | 现在的结论 | 理由与证据 |
| --- | --- | --- |
| K-DE、K-DC、K-DF 预计得 1【待跑】 | 确认 | 正式评分都是 1.0；私有核对结果与分析稿 §6.4 的预测逐项一致 |
| K-A5 作为合理替代解，预计得 1 | **初稿有错**，改用 K-A5b | K-A5 得 0.0（228/229）。原因是在 `numpy/ma/core.py` 模块内部，`max` 指向模块级的 `numpy.ma.max`（`core.py:6274`），于是 `max(print_width, int(threshold) + 2)` 把 1002 当成了 axis，抛出 `ValueError: 'axis' entry is out of bounds`（`logs_KA5/…eval.log:28-80`、`pcheck_KA5.json`）。这是主审补丁本身的错误，不是误拒；测试拒绝一个在 repr 里崩溃的实现，是正确行为 |
| — | 正对照改用 K-A5b：协调者修正，主审核对后认可 | 协调者只改了 `max` 那一行，改成条件表达式（`OUT/cands/numpy_d805_KA5b.patch`）。本审逐行核对：与 K-A5 只差这一行，语义等于内置 `max`，截角优化保留，在自定义 threshold 下也不丢值。它在 base 副本上 `git apply --check` 通过；正式评分 1.0（229/229）；私有核对 n500 相等、n1e5 相等 |
| 预测 gold 下 diag_sizes 为 True/7、False/500、False/500、False/1000、True/43 | 确认 | `private_control.json`；devcheck 在 base 上的输出也与公开读者的推导一致 |
| 处置 `needs_review` | 改为 `needs_repair` | 缺陷已经可以复现（三个违例候选都得了 1），修法落在 v1 预授权的 R-c 模板内，新镜像的环境条件也已验证 |
| capability_comparison 为 conditional，缺三项：devcheck、新镜像上的 noop / gold、事后审计 | 仍是 conditional，但只剩事后审计一项，另有池级的真实模型链路未验 | devcheck 与 env_verify 都已完成 |
| 唯一优先的下一步是实跑候选 | 改为：实施 R-c 并跑验收矩阵 | 候选实跑已经完成 |

## 4. 对后续的影响

- 历史的环境资格可以继续引用，但只适用于环境层面，而且应以新镜像 `c080fc6b…` 的运行证据为准；它不代表训练资格。
- 以后同类题的环境轮只核"目标键与题意对得上"是不够的；要在 v1 第 2、3 步里补示例拟合检查和退化探测。
