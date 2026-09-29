# T0-1 / T0-2 与 numpy43：独立证据复核

2026-09-24，Codex 独立证据审。结论：**本轮三题共 12 次真实评分的证据账目成立，批准的两处材料修订与日志实际使用的版本一致；numpy43 已恢复相关公开测试的常规收集和运行。** 未发现新的运行证据 P0/P1/P2。当前 33 + 2 + 2 + 8 + 3 处置计数与逐题未完成项一致。剩余问题是少数汇总文字未同步，见 §5；无需为此重跑题目。

本审只读共享工作树与已有回传证据；新增产物只在本目录。未调用远端、Docker、作者 `reconcile_r2e.py` / `collate_facts.py`，未修改生产代码、输入材料或历史证据，未做 T0-3…7 新实验。

复现（仓库根）：

```bash
python3 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_t0_review_20260924/evidence_agent/audit_evidence.py
```

[summary.json](summary.json) 的 `issues=[]`。脚本只 AST 提取并执行固定 SHA `b928139e…` 的来源 vendor parser、去 ANSI 函数和 gold 提取函数，独立实现映射比较与并集计分；它没有使用被审对账器的结论作为 oracle。检查对象的 SHA 留在 [file_hashes.json](file_hashes.json)。这是离线证据重建，不等于本审又执行了三题。

## 1. 12 行原始证据与重复性

| 题 | noop ×2 | gold ×2 | 本轮实际镜像 / 材料 |
| --- | --- | --- | --- |
| coveragepy `016af5f6` | 0，14/15，只有 `ExecTest.test_unencodable_filename` 不符 | 1，15/15 | `565a8f36…`；`r2e_derive_v1`；expected 只应用 `r2e-mr-001` |
| datalad `58ba5165` | 0，2/4，api 与 cmdline 不符 | 1，4/4 | `a5d5a8c2…`；`r2e_derive_v1+material_v1`；测试树 `86561f1a…` |
| numpy `43e333e2` | 0，87/88，只有 `TestAverage.test_masked_weights` 不符 | 1，88/88 | `b8f6f112…`；`r2e_derive_v1+env_v1`；隐藏测试树未变 |

逐行结果见 [rows.json](rows.json)：12 个不同 report ID、日志与执行记录；每题每种候选的 attempt 为 1、2。日志 SHA、sidecar 的任务/镜像/脚本/判分/候选字段均与账本相符；完整测试分段只有一对、无 partial、无 stage error、清理成功。独立解析得到的完整观测映射、匹配/缺失/额外/不匹配集合与 reward 全部吻合。两次重复的完整映射、overlay、候选、脚本摘要、期限一致，期限均 1800/1800。

评分日志直接记下的 `RH2_SETUP_HIDDEN_TESTS_TREE` 和 `RH2_SETUP_ENTRY_SHA256` 与修订后评分面一致；账本 `image_id_actual` 与本轮 overlay 相同，source image manifest 与环境包相同。gold 补丁从原始 `parsed_commit_content` 独立提取，和账本及实际保存的补丁 SHA 一致。三个任务均导入 `/testbed` 中的目标包。noop 的内部测试 rc=1 是预期失败，不能把“wrapper/driver exit 0”写成 noop 测试全通过。

## 2. 原始材料、修订材料与独立对照的边界

五项输入 pin、历史和当前 manifest 的四个文件 SHA/count 均核对通过。原始行与镜像文件清单独立重建隐藏测试文件摘要、树摘要。详见 [revision_checks.json](revision_checks.json)、[material_diffs.json](material_diffs.json)。

- `r2e-mr-001`：原 expected 的 `MockingProtectionTest.test_os_path_exists` 由 FAILED 改 PASSED，原/新字节 SHA 都吻合；只有这一处替换。
- `r2e-mr-002`：`test_1.py` 的一行导入由 `datalad.interface.tests.test_docs` 改为 `.test_2`；原/新文件 SHA 都吻合，expected 和其它隐藏文件不变。日志里的测试树确为修订后 `86561f1a…`。
- 全 48 题评分面新增了 `material_revisions` 字段，因此 48 个 grading digest 及环境包中的引用摘要都改变；这是元数据变化。语义字段变化仅上述两题，公共包与 gold/validation 包逐字节不变。本轮保存的 48 个 host grading view 与当前评分输入完全一致。

独立参考直接读取 M3 原始日志，未读取作者 reconcile 结果：coveragepy/numpy 各四行完整映射均与参考相同。coveragepy 参考日志按来源 expected 计分仍为 gold 14/15；按修订 expected 是 15/15。两个版本的 expected 不能混用来指责旧 M3 账本矛盾。

datalad 新 noop 与旧 M3 相同，新 gold 仅 `test_alter_interface_docs_for_cmdline` 从 FAILED 变 PASSED。旧 M3 没有本次相对导入修订，**不构成修订后同版本的独立 runner**。已有 B1 沙盒 dry-run 保存的四键状态行与本轮 noop/gold 各两次一致；它是独立于 RH2 grader 的直接 pytest 路径，但仍由实施方执行，不冒充第二名审查者的新运行。本轮验收已写明这一限制，未把 datalad 四行计入 8/8 同版本对账。

## 3. numpy43 公开开发验证及剩余十项

[numpy_public.json](numpy_public.json) 保存本审从原始仓库测试源码得到的类、方法、首条语句与调用名称，以及实际 129 个 venv 路径差异。

已核证据：

- `agent_pubtest.sh` 使用 `docker exec -u 54321 -w /testbed`，执行常规 `python -m pytest -q numpy/ma/tests/test_extras.py` 和 `::TestAverage`，没有忽略警告或禁用 conftest。保存输出为 hypothesis 6.24.1、pytest 8.3.4、模块 78 passed / 10 failed、TestAverage rc 0 / 6 passed。
- 相同派生镜像的开发探针有容器 inspect 与完整 agent 日志：镜像 `b8f6f112…`、uid 54321、base HEAD `1798a7d4…`；公开入口 `numpy/tests/test__all__.py` 收集 rc 0、运行 rc 0。相关 TestAverage 的独立摘要文件本身没有记录镜像 ID/uid，执行身份由保存的脚本说明，不能把它描述成具有和 grader 账本同等完整的身份记录。
- 原始与派生完整性文件独立对比：仓库文件和 git 状态相同；venv 非 bin 区差异恰为 129 个 hypothesis 路径，全部命中登记 glob；本地 wheel 的 SHA 与配方 pin 一致。构建日志记录 `RH2_ENV_PINNED=hypothesis:6.124.1->6.24.1`。
- 失败摘要确为 TestCov ×4、TestCorrcoef ×6。原始源码十个方法均先读取 `self.data`，两个类用旧式 `setup(self)` 创建该属性；方法测试 `cov` / `corrcoef`，没有调用 `average`。新摘要保留缺少 `data` 的异常，旧同失败集诊断明确计数 4 + 6。hypothesis 6.24.1 + pytest 6.2.5 的对照为 88 passed，也支持剩余失败来自 pytest 对旧式 setup 的兼容性。

因此，“相关 average 开发验证不再被收集错误阻断”成立；“整个公开模块或整个 numpy 开发环境全绿”不成立。六个 base 公开用例通过本身不是修复完成的证据；修复区分由本轮隐藏目标键 noop FAILED / gold PASSED 提供。保留 pytest 8、将这十个无关类失败记为已知开发噪声，与上轮“不要求全仓公开测试全绿”的验收范围相符。

## 4. 新处置与上轮更正

[records.json](records.json) 独立统计为 33 `environment_qualified`、2 `qualified_with_recipe`、2 `qualified_with_revision`、8 `grading_ok_open_items`、3 `needs_decision`。前 37 题没有 `open_items`；后 11 题全部保留明确未完成项。

八题为 pandas ×7 的 fixture 支撑缺口与 orange3 `9b5494e2` 的待定依赖/评分风险；三题为 pillow `2b061b68`、scrapy `9a15fcf8` / `cfed9b66`。没有把 T0-3…7 待修项计入 37 题环境合格。`state_if_r13_passes` 在部分旧记录仍保留，但主审已另行验证有非空 open_items 时不会提升；本审不据此报资格回归。

最新 decisions 已纠正上轮 T0-5…7 的三处证据边界：scrapy 同 FAILED 的前后异常不同；pandas4ec87 两个新增用例不在 base 公开文件；orange3 四键同因/所有正确解恒 FAILED 尚未证明。README 最新统计明确区分来源 **20 题 / 93 键（34 FAILED + 59 ERROR）** 与修订后 **19 题 / 92 键（33 FAILED + 59 ERROR）**，与本审原始数据重算相同。

## 5. 可递延的文字同步项（P3）

**当前行为 / 不变量：** 最新 decisions 的更正已落，但 `dispositions.json:2,58` 仍写“未修改…摄入面”以及 scrapy cfed 的“3 个…死键”；`known_issues.json:159` 的总族摘要仍保留“至此 16 题”、pandas“原位…全 PASSED”、scrapy“三个死键”。这与同文件详细族及最新决定不一致。

**证据 / 影响：** 上述行可直接读取；本审 raw 重算为来源 20、修订后 19 题，最新 decisions T0-5/6 已明确反例。处置 state/open_items 没错，本轮评分证据也不受影响；风险是只读总族摘要的后续交接者继续采用已撤回的依据。

**分期 / 复现 / 验收：** 作为本轮文档收口或下次编辑顺手同步，不新增运行门槛。复现可用 `rg -n '16 题|3 个.*死键|未修改正式题池或摄入面|原位公开测试同名用例全 PASSED'` 搜索上述两文件；将当前摘要同步到现有修订与决定，或明确标为历史描述。保留历史原日志，不新增 T0-3…7 实验。
