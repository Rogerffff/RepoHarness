# coveragepy f5eb5f21 题卡（主审定稿，待独立复核）

**结论：S1，状态 `needs_repair`。**

- **测试放过了错误实现。** 在 `totals` 里硬编码 1/1 的退化候选 D0，正式评分得 1；另外两个错误实现 C2、C3 也得 1。
- **测试层修订 R-c 必做。** 草案见附录 A，可以直接实施。
- **另有一个规格争议 C1，交用户裁定。** 它不阻塞 R-c。
- **环境与解题侧开发路径没有缺口。** 已在新机器镜像上实测。

路径约定：

- `PUB/`、`PRIV/`：本题的公开包与私有包，位于 `runs/r2e_static_prep_20260924/v3/{public,private}/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/`。
- `NEW/` = `runs/r2e_lifecycle_20260929/`；`INV/` = `NEW/inv/coveragepy_f5eb/`。
- 完整分析见 `analysis_before_history.md`，旧结论对照见 `old_findings_delta.md`。

## 1. 题目与版本

- **目标。** 分支覆盖模式下，JSON 报告的 `totals` 缺 `covered_branches`、`missing_branches`，要求补上。
  - base 是 `17204597`，coverage 版本 5.0.5a0。
  - gold 只改 `coverage/jsonreport.py` 两行，取 `n_executed_branches` 与 `n_missing_branches`。
- **材料。** `r2e_gym_subset_e8b9fcbc/expected_v0`，没有材料修订（v3–v5 对本题逐字相同）。
  - 隐藏测试就是修复提交之后的 `tests/test_json.py`，共 4 个键，期望全是 PASSED。
  - 目标键只有 `JsonReportTest.test_branch_coverage`。
- **环境。** 新机器镜像 `rh2-r2e-derived/coveragepy:f5eb5f215918-r2e_derive_v1s`，配方 `r2e_derive_v1+sysconfig_v1`，ID `98b19b5a2ce4…`。在这张镜像上 noop 0、gold 1（`NEW/env_verify/ledger_l1_{noop,gold}.jsonl` 第 2 行）。旧镜像 `1a2107883a20…` 上 noop、gold 各 2 次，逐键结果相同。

## 2. 关键映射

| 需求或旧行为 | 公开依据 | 决定性断言 | 覆盖情况 | 执行证据 |
| --- | --- | --- | --- | --- |
| 分支模式下 `totals` 有两键 | 题面 `user_prompt.txt:7`、`:21`、`:24` | `test_1.py:61-71`，整字典相等 | 覆盖 | noop 0（缺键），gold 1 |
| 两值分别等于已执行 / 未执行的分支弧数 | `coverage/results.py:36`、`:201-204`；XML 用同一口径（`xmlreport.py:203-205`） | 只有一个夹具，值为 1/1，与题面 `:28` 的错误信息逐字相同 | **部分**：只测了示例 | D0（硬编码 1/1）= 1；C2（用"部分弧"计数）= 1 |
| 按数据 `has_arcs()` 门控（文档写的 CLI 流程） | `doc/branch.rst:38-40`、`:52-54`；`cmdline.py:374-388` | 无 | **缺失** | C3（按配置门控）= 1；P-2 显示 CLI 流程下缺键 |
| 行模式下不出现分支键 | `jsonreport.py:59`、`:94`；公开旧测试 | `test_1.py:75-159` | 覆盖 | noop 与 gold 都 PASSED |
| 每文件 `summary` 是否也加两键 | 题面只点名 `totals`；base 代码两处分支块对称；上游后来也在每文件加了 | `test_1.py:50-58` 要求每文件 summary 恰好 7 个键 | **争议** | C1（对称加键）= 0；差异只在 `files`，`totals` 相同 |

## 3. 八个方面的覆盖（已查 / 未查）

- **公开需求。** 已查题面、提示、文档和代码。未查：模型实际收到的消息，即 `public_hints` 有没有送到模型面前。
- **材料与初始问题。** 已查：各处摘要一致；base 是修复提交的父提交；noop 的失败位置在目标断言。没有缺口。
- **测试是否测到要求。** 已查隐藏测试全文和 4 个候选的正式评分。结论：测试只拟合了示例（S1）。
- **是否误拒合理解。** C1 = 0，属规格争议，待用户裁定。
- **回归与 gold。** gold 正确，而且只做了题面要求的改动。未测：多文件时 `totals` 的汇总、`report()` 的返回值（T3，风险低）。
- **解题侧开发条件。** devcheck 用 agent 身份、真实 CC 2.1.205 + 桩、正式启动路径，13 项检查全部为真。8 条公开命令都符合预期，总耗时约 23 秒。
  - 初态下 `repro_api_totals` 退出码 1，能复现问题。
  - `tests/test_json.py` 在 base 上 4 passed；gold 下 `test_branch_coverage` 失败，这是预期的 P6。
- **交付与评分边界。** 已查：gold 与 4 个候选都只投影 `coverage/jsonreport.py`；隔离预检和 P-1 都通过。未逐题复审：共享控制面，即根目录 conftest、测试辅助文件、`.venv` 对 agent 可写。
- **题目关系。** 发现三处同仓关系（X1），见 §4 的 I8。

## 4. 问题与证据层次

| 编号 | v1 归类 | 问题 | 证据 | 证据层次 |
| --- | --- | --- | --- | --- |
| I1 | T2c，S1 | 唯一的分支断言用的就是题面示例值 1/1 | `PRIV/hidden_tests/test_1.py:61-71` 对照 `PUB/user_prompt.txt:28`；noop 日志第 93 行 | 静态分析 + 日志 |
| I2 | T2b，S1 | 退化候选 D0（硬编码 1/1）得 1 | `INV/ledger_D0.jsonl`：4/4，`included_paths` 为 `coverage/jsonreport.py` | 当前 CPU 正式评分 |
| I3 | T2（第 4 步），S1 | C2 把"部分弧"计数当成未执行弧数，得 1 | `INV/ledger_C2.jsonl`；P-3：BRANCHY 夹具上报 6/0，正确值是 4/2（XML 给出 covered 4） | 正式评分 + 私有核对 |
| I4 | T2（第 4 步），S1 | C3 按配置 `branch` 门控，得 1 | `INV/ledger_C3.jsonl`；P-2 / P-3：文档写的 CLI 流程下、另起报告对象时都缺这两个键 | 正式评分 + 私有核对 |
| I5 | P3 / 疑似 T1 | 把两键也对称加进每文件 `summary`，判 0 | `INV/ledger_C1.jsonl`；日志第 94 行只有 `files` 不同 | 正式评分 |
| I6 | P6 | 公开 `test_branch_coverage` 与任何正确修复冲突 | `NEW/devcheck/…/private_control.json`：`public_test_json` 退出码 1 | 当前 CPU |
| I7 | P4 | 题面说的 AssertionError 在公开测试上不出现；示例代码没有给出被测代码 | 静态分析；替代复现是 `repro_api_totals` | devcheck |
| I8 | X1 | `ea6906b0` 的初态含本题答案；`97997d2c` 与本题初态逐字节相同；本题初态已含 `016af5f6`、`5dbbe143` 的修复 | gold 扫描 + 公开包核对 | 静态分析 |
| I9 | T3 | 多文件时 `totals` 的汇总、`report()` 的返回值都没有测 | 源码 | 静态分析 |

- **环境修复：不需要。** 新配方 `+sysconfig_v1` 下的 noop / gold 已经覆盖。
- **时间戳断言（E5）：未触发。** 所有键都要求报告时间在 10 秒以内；历次运行一致，没有抖动。

## 5. v1 用途结论

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | **yes** | — |
| 能力比较 | **conditional** | 公开开发路径、评分依据、本批运行条件都已核对（devcheck；env_verify）。**还差 C1 争议的用户裁定。** 按 v1 §11 口径，题意争议或误拒尚未消解的题只作问题定位，不进比较分母。裁定之后、R-c 验收之前，如果先纳入比较，得 1 的补丁必须按预先登记的三项做事后审计：① totals 的值是否随代码变化；② 未执行的分支弧是否计入 `missing_branches`；③ 是否按数据门控，即先 `coverage run --branch` 再单独 `coverage json` 时两键仍在。原始 reward 与语义结论分开记 |
| 训练候选 | **no**（当前材料） | 有未处理的 S1（I1–I4）。满足以下三项后重新评估：R-c 实施并按附录 A 验收；C1 裁定并落实；Codex 复核。正面覆盖证据已经具备：核心要求有直接断言；新镜像上 noop 0、gold 1；第 2、3 步的结果都已取得 |
| 留出评测 | **no** | 原因同训练候选；修订之后也只能作"标明版本的自建题"。X1：`ea6906b0` 的初态含本题答案，按 D3 以仓库划分时两题同侧 |

## 6. 修订与决定项

- **必做：R-c 两项**（草案见附录 A）。
  1. 非示例计数：BRANCHY 夹具，预期 num 6 / partial 0 / covered 4 / missing 2。
  2. 先保存分支数据，再另起一个不设 `branch` 的报告对象出报告，检验按数据门控。

  预期验收：gold 为 1；noop、D0、C2、C3 都为 0；C1 仍为 0（R-c 只断言 `totals`，对 C1 争议保持中立）。
- **交用户：C1 三选一。** 这一项不阻塞 R-c。
  - **R-b**：每文件 `summary` 允许出现这两个键，但出现时值必须正确。主审倾向这一项，理由是 C1 满足全部公开要求，而上游后来正是这样做的。
  - **R-f**：在题面补一句"只改 `totals`"。
  - **维持原样**：接受"只改 totals"这个读法，登记为风险。

## 7. 进探针还差什么

本批 README §3 按通用规则禁读，下表按 v1 §2 和角色卡列出，请协调者按 §3 的条目核对。

| 条件 | 状态 | 谁来补 |
| --- | --- | --- |
| 新镜像上正式评分 noop 0 / gold 1 | 已满足 | — |
| 正式启动路径的开发核对（agent 身份、公开命令） | 已满足（devcheck） | — |
| 隔离与泄漏预检 | 已满足（preflight、P-1） | — |
| 核心判据有效（没有未处理的 S1） | **未满足** | 协调者按附录 A 实施并验收 R-c；Codex 复核 |
| C1 争议 | **未满足** | 用户裁定；协调者按裁定实施 R-b 或 R-f |
| 本题的独立复核 | **未满足** | reviewer |
| 经 Qwen adapter 的链路、模型实际收到的消息 | 未验证 | A 线 |
| 如果在修订之前就进探针 | 需要先登记 §5 的三项事后审计，原始 reward 与语义结论分开记 | 协调者 / 探针分析 |

**唯一优先的下一步：** 实施 R-c，并跑附录 A 的验收矩阵（6 次正式评分）。

---

## 附录 A：R-c 可执行草案（v1 §5；Claude 实施、Codex 复核）

**1. 加进 `PRIV/hidden_tests/test_1.py` 的 `JsonReportTest` 类。** 放在 `test_context_relative` 之后。文件头已有的 `os`、`json`、`coverage` 导入可以直接用。

```python
    BRANCHY = """\
        def f(x):
            if x:
                return 1
            return 2

        def g(x):
            if x:
                return 1
            return 2

        def h(x):
            if x:
                return 1
            return 2

        f(0)
        f(1)
        g(0)
        g(1)
        """

    def _branchy_report(self, modname, report_from_saved_data=False):
        """Measure BRANCHY with branch=True and return the parsed JSON report."""
        self.make_file(modname + ".py", self.BRANCHY)
        data_file = os.path.join(self.temp_dir, modname + ".coverage")
        cov = coverage.Coverage(branch=True, data_file=data_file)
        mod = self.start_import_stop(cov, modname)
        if report_from_saved_data:
            # Like `coverage run --branch` followed by a separate `coverage json`:
            # the reporting object's own config does not set branch.
            cov.save()
            cov = coverage.Coverage(data_file=data_file)
            cov.load()
        output_path = os.path.join(self.temp_dir, modname + ".json")
        cov.json_report(mod, outfile=output_path)
        with open(output_path) as result_file:
            return json.load(result_file)

    def test_branch_totals_count_branch_arcs(self):
        # f and g take both branches of their `if`; h never runs:
        # 6 branch destinations, 4 taken, 2 never taken, no partial branch line.
        totals = self._branchy_report("branchy")['totals']
        assert totals['num_branches'] == 6
        assert totals['num_partial_branches'] == 0
        assert totals['covered_branches'] == 4
        assert totals['missing_branches'] == 2

    def test_branch_totals_from_saved_branch_data(self):
        report = self._branchy_report("branchy_saved", report_from_saved_data=True)
        assert report['meta']['branch_coverage'] is True
        assert report['totals']['covered_branches'] == 4
        assert report['totals']['missing_branches'] == 2
```

**2. 在 `PRIV/expected_output.json` 增加两个键：**

```json
"JsonReportTest.test_branch_totals_count_branch_arcs": "PASSED",
"JsonReportTest.test_branch_totals_from_saved_branch_data": "PASSED"
```

**3. 每条断言的公开依据**（不来自 gold 的输出）：

| 断言 | 公开依据 |
| --- | --- |
| 两值的口径 | `results.py:36`、`:201-204` |
| XML 报告的同一口径 | `xmlreport.py:122-123`、`:203-205` |
| 与 `covered_lines` / `missing_lines` 平行的命名 | `jsonreport.py:51-57` |
| 按数据门控 | `jsonreport.py:38`、`:59`、`:94`；`summary.py:20`；`xmlreport.py:60` |
| 文档写明的 CLI 流程 | `doc/branch.rst:38-40`、`:52-54`；`cmdline.py:374-388`、`:532-544` |

期望值来自主审的静态推导（分析附录 B），并已由 P-3 独立核对：XML 给出 `branches-valid="6" branches-covered="4"`；另起报告对象时仍是 4/2（`INV/pcheck_P3_gold.json`）。`num_branches` 与 `num_partial_branches` 是 base 已有的行为，也写进断言，用来锚定夹具。

**4. 验收矩阵**（新材料、正式评分，各 1 次；右列的预测依据是同一镜像上的 P-3 / P-2）：

| 候选 | 预期 reward | 预期失败的键 | 预测依据 |
| --- | --- | --- | --- |
| gold | 1（6/6） | 无 | P3_gold：6/0/4/2；另起报告对象 4/2 |
| noop | 0 | `test_branch_coverage` 与两个新键 | 缺键 → KeyError |
| D0 | 0 | 两个新键 | P3_D0：1/1 |
| C2 | 0 | 两个新键 | P3_C2：6/0 |
| C3 | 0 | 只有 `…from_saved_branch_data` | P3_C3：进程内 4/2，另起报告对象时缺键 |
| C1 | 0 | 只有 `test_branch_coverage`（两个新键 PASSED） | R-c 对 C1 中立 |

修订后仍受保护的公开要求：两键存在、口径（非示例实例）、行模式形状、按数据门控、示例夹具的其余输出。

保存时要记下：新版本与父版本、理由、触发反例（D0、C2、C3 的补丁与账本，见 `INV/`），并交 Codex 复核。

**5. 如果用户选 R-b（仅作说明，不在本次必做范围内）：**

- 在 `_assert_expected_json_report` 增加可选参数 `optional_summary`：每文件 summary 里如果出现这两个键，先核对它们的值，再 `pop` 掉，其余部分仍然整字典比较。
- `test_branch_coverage` 调用时传 `{'a.py': {'covered_branches': 1, 'missing_branches': 1}}`。
- R-c 第 1 项同时加一条：如果 `files['branchy.py']['summary']` 里有这两个键，值必须是 4/2。
- 验收时增加：C1 应为 1；另做一个"每文件两值对调、`totals` 正确"的候选，应为 0。

## 附录 B：证据索引

- 新镜像上的 noop / gold：`NEW/env_verify/ledger_l1_noop.jsonl:2`、`ledger_l1_gold.jsonl:2`（缺省预算、正式 profile）。
- devcheck：`NEW/devcheck/coveragepy__f5eb…/devcheck.log`、`orig/captures/*.out`、`orig/prelaunch.json`、`orig/activation_check.json`、`private_control.json`（root，gold 已应用）。
- 候选：`INV/coveragepy_f5eb_{D0,C1,C2,C3}.patch`（与 `results/…/cands/` 逐字节相同）、`INV/ledger_*.jsonl`、`INV/logs_*/`、`INV/run.sh`。
- 私有核对：`INV/pcheck_P1_agent_cwd_root.json`、`pcheck_P2_{C3,gold}.json`、`pcheck_P3_{gold,D0,C2,C3}.json`。
- 旧镜像 / 来源：`PRIV/run_refs.json` 的 4 行 RH2 与 2 行 M3（日志的 sha256 已核）。
- 历史：`runs/r2e_static_prep_20260924/v3/history/coveragepy__f5eb…/refs.json` 列出的 8 份文件，逐条对照见 `old_findings_delta.md`。
