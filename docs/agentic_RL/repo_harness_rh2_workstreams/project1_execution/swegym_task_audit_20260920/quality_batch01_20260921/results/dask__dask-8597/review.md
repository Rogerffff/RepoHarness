# dask__dask-8597 独立复核

复核日期：2026-09-21；角色：review_dask，未参与主审。结论：同意 `needs_review / static_review`。可保留“受限开发诊断候选”标签，但本题不列为可直接启动的模型探针；先交付下述一个定点 CPU/RH2 对照。这不是拒绝原题，也不是要求穷尽所有轴、类型或后端后才可用。

[独立初判][initial] 在第二阶段开放前已封存，SHA256 为 `cc413fb9bcbfa0929891ee828f7774b8ec31d61012799e4cd37c03317dfe2178`，本文件不替换或改写它。初判已独立读取公开材料、全部新增断言/F2P、相关旧测试与调用者、gold、原始 compat-v1 日志/账本；曾读取允许范围内的 environment_record 环境汇总，未沿其引用提前打开质量历史。随后复核 8801 原件，两题初判均封存后，协调者才开放本题 public_read、analysis_before_history、old_findings_delta、card、screening_record 与指定历史。本文所称“独立发现”指读入这些结论之前已写入初判，不表示历史上首次发现。

本轮只静态读取本地原件、既有日志与获准报告，没有执行 Dask、候选、测试、Docker 或模型。回读原始日志不称独立复现。主审/复核者均已见 gold 和隐藏测试，产物不得提供给未来 solver。

**决定性主张的复核**

| 主张 | 判定与具体依据 | 证据级别 |
| --- | --- | --- |
| 公开题意足以实施修复 | 同意。正文明确 `np.zeros((3, 0))[[0]]` 的 NumPy 结果为 `(1, 0)`；标题“0-D”和省略调用栈不使需求缺失。正常定位可从公开 MCVE 和源码取得，不需补隐藏栈。[公开题面][prompt] | 初判独立确认；公开读者后来一致 |
| 缺陷、base、gold 对应同一问题 | 同意。base `c1c88f066672c0b216fc24862a2b36a0a9fb4e22` 的 take 在 other_numel=0 时除零。历史 noop 在该行以 RuntimeWarning 失败，warnings-as-errors 可解释与题面 OverflowError 的差别。gold 只扩充零元素 guard，未发现已证回归。[take][take]、[gold][gold] | 源码推断与原始失败日志相互支持；非新运行 |
| F2P 合理且不强绑 gold 写法 | 同意。唯一新增测试直接比较公开原例，helper 实际检查 shape/dtype/计算结果及条件性的 Dask 图/块信息。不得缩写成“只看值”，也不能说所有替代实现已跑过。[测试补丁][patch]、[assert_eq][helper] | 初判独立确认 |
| 零轴所有语义都被覆盖 | 不成立。只有默认配置和一个形状/索引组合；helper 的 Dask 专有检查依赖参数已是 Array，没有显式保证切片返回 Array。因此返回类型/惰性和 zero-axis+True 仍有静态漏测线索，不是已获分错误补丁 | 初判独立发现；主审后来一致 |
| 已恢复的默认大块警告测试仍不计分 | 同意。`test_getitem_avoids_large_chunks` 与 `test_slicing_integer_no_warnings` 在 compat-v1 两侧实际 PASS，却均不在 1 F2P + 116 P2P 中。前者直接覆盖本题改动分支的默认警告。完整模块执行与参考集不可互换。[旧回归][regression]、[参考清单][grading] | 初判独立做过逐 ID 对账；历史也已有该事实 |
| True 配置 P2P 足以保证默认警告 | 不同意这一扩大解释。take 的 True 拆块测试能拦住无条件 inf；默认警告和 True 拆块在不同分支。条件式绕过阈值计算可能保住现有参考、丢掉默认警告且漏修零轴+True | 具体静态候选；没有其实际得分 |
| 既有运行证明实际 actor 可开发 | 不成立。已证的是 rh2grader/54322 执行和 agent/54321 应用候选；正式工具 shell 的解释器、PATH、pin 配方消费及权限尚未验证 | 初判与主审均明确保留 |
| 可直接采用旧 ready/probe 优先级 | 需收窄。旧历史的环境故障已更新，但这不消除参考遗漏。当前有一个可低成本区分误收风险的具体候选，应先完成它再决定模型运行 | 本 reviewer 的处置判断 |

[主审分析][analysis] 和[短卡][card] 没有把上述静态候选写成已观测的 reward=1，表述成立。[结构化记录][record] 的“实际 actor 未验、额外排除为空、未修订题目”也与原件一致；协调者补充的 `file_rules.applied_version=upstream_unchanged` 是格式补全，没有改变本复核的语义结论。

**环境与评分证据的适用边界**

原始 gold 日志显示离线安装 pytest 7.4.4、editable 安装 RC=0、Python 3.9.19、123 项实际收集，最终 119 passed / 2 skipped / 2 xfailed、RC=0。noop 为 1 failed / 118 passed / 2 skipped / 2 xfailed、RC=1。两份账本分别为 reward=1、0，P2P 均为 116 项通过、无参考缺席。它们支持本题既有环境配对，而非当前 actor、任意新候选或模型能力。[gold 原始执行][goldlog]、[noop 原始失败][nooplog]

实际派生镜像 identity 为 `sha256:065c32c154a13335b5363bd7969d0c79bd19f7dee23b9a1000b5650ac9cd78e0`；2 CPU / 4 GiB、deny_all。两侧 `runner_integrity_changed=true` 与预先声明的 pytest pin 同时存在，不能单独推成候选篡改；本文未完整审计该 digest 的覆盖范围。历史“装 pytest<7”建议无需照搬，现有原件已经是 7.4.4 成功证据。

第二阶段新增交叉核实：本 reviewer 静态读取了主审引用的当前 [scoring.py][scoring] 与 [manager.py][manager]。前者按 F2P/P2P 构造 verdict，并在 resolved 时映射 reward=1；后者还处理测试段、全局执行失败、信号终止和 hygiene。正常完整测试段的普通 RC=1 没有单独覆盖来源参考 verdict 的分支。这解释了为何“有一个非参考测试失败”不能自动等同 reward=0。文件 SHA256 与主审一致：

- scoring.py：`b6c8b9bd3e9cac604bc0d03b0b243ef9646de369e94bb6a65e60eadd3a64f5ab`
- manager.py：`eadaa64acc2e9dc358ad4c7c4f9ad3bb60d81a1c72298a41dabbdf6397ad6342`

这只是当前机制的静态证据，没有证明它与每次历史执行的代码逐字相同，也没有证明新候选的投影、执行、解析及实际 reward。CPU 对照必须同时保存完整模块退出码和 RH2 报告，不能只跑孤立 F2P 就宣布误收。

**历史对照与发现归属**

获准读取 [L1 记录][oldl1]、[pilot 记录][oldpilot] 后，支持主审 [old_findings_delta][delta] 的主要修正：截断栈不等于缺少功能要求；旧 pytest8 的两个失败已由 compat-v1 运行取代；“无条件 inf 会被 True P2P 拦下”只证明这一类候选；“只看结果数组、替代解都能过”应收窄为 helper 实际行为与静态可行性。原始 raw hints 仍未打开，不能验证其中全部内容或把它作为公开规格。旧“十四题唯一改该文件”的跨题断言没有在本次重查，不沿用为全池独立性证明。

参考遗漏、公开可定位性、gold 合理性及开发缺口均在初判独立确认；它们不是本轮首次发现。初判提出的“按 split 配置绕过阈值”与当前主审独立提出的具体候选一致，比旧“无条件 inf”更能检验现有评分边界。当前 scorer/manager 分支及其 SHA256 是第二阶段才直接核实的补充证据。

**可以成熟交付的唯一优先 CPU 对照**

交付成熟度：候选变更、环境、输入、对照和判据已足够明确，可交给获执行授权者实施；本轮没有构造候选文件或运行。沿精确 base 创建彼此独立的 noop、gold、candidate，使用本题已记录的 compat-v1 配方和冻结原参考清单。candidate 仅把 take 原 guard 改成下列条件，不叠加 gold 的零值处理：

```python
if math.isnan(other_numel) or config.get("array.slicing.split-large-chunks", None) is not True:
    warnsize = maxsize = math.inf
```

保留原 else、警告、拆块和索引代码。该错误候选有自然动机：以为只有用户启用拆块才需算阈值；其公开语义问题是默认仍应计算警告阈值，且 True 下空块也必须可切片。它不是针对测试名称/日志的评分攻击。

| 对照内容 | 静态预期；实际结果待记录 |
| --- | --- |
| 官方完整 `test_slicing.py` + 未改 F2P/P2P + 实际 RH2 报告 | noop 与 gold 先复核控制。candidate 可能通过来源参考而在默认警告旧测试失败；不得预填 reward 或完整通过数 |
| 公开原例，分别显式设 split=None、False、True | gold 三者都应匹配 NumPy 的 shape/dtype/计算结果并保留 Array；candidate 在默认/False 有望通过，True 仍走除零路径 |
| `test_getitem_avoids_large_chunks` 默认分支 | candidate 因 warnsize=inf 丢失 PerformanceWarning；这项原测试已存在，无需先发明新规范 |
| `test_take_avoids_large_chunks`、`test_take_uses_config`、out-of-order warning 旧测试 | candidate 的 True 非空拆块和独立 out-of-order 警告应保留；用于分清“无条件关闭保护”和本次条件式错误 |

以上额外语义检查应单列诊断结果，不暗中并入原参考再声称原版已拒绝候选。保存候选完整 diff/hash、base 与镜像/recipe/script/parser 版本、执行 UID、安装 RC、模块命令/RC、原始日志及逐 ID 状态、缺席/skip、F2P/P2P 计数和 reward。若 gold 控制失败，先解释环境差异，不能据此判题坏。

若 candidate 的官方 reward=1，但默认警告或 True 空轴语义失败，才可称本候选的实际误收已证；应将原奖励标为不足以判完整正确。若它被某个已有参考拒绝，则记录实际拦截项，撤回“此候选可误收”的推断，参考缺失事实仍保留。若后续要纳入默认警告旧测试或新增 True 空轴检查，必须另建参考/测试修订版本并以 gold 和该错误候选复核，不能改写原版运行证据。

**处置与剩余条件**

我保留初判中的“静态开发诊断候选”，并明确执行顺序为：上述一个 CPU/RH2 对照 → 依据结果决定原版或修订版的诊断用途 → 实际 actor 入口核对后才启动模型探针。选择先等该实验，是因为它直接影响如何解释随后模型补丁的 reward，且已有明确、局部、无需模型的验证方式；不是把所有一般性未知都变成准入门槛。

正式 actor 只需核实与本题开发相关的实际消息/工具、UID/cwd、工作区导入、Python/NumPy/pytest 版本、兼容 wheel/pin 是否生效、源文件可写和本地原例/公开测试可执行；无需外部服务或运行期公网。镜像答案暴露、全池关系和更广后端覆盖仍未知，本次不替共享验收签字。没有证据要求现在重写题面、追加源码排除或否定 gold。

[initial]: ${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/dask__dask-8597/reviewer_initial.md
[prompt]: ${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/dask__dask-8597/user_prompt.txt:1
[take]: ${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/dask__dask-8597/base/dask/array/slicing.py:638
[gold]: ${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/private/dask__dask-8597/gold.patch:1
[patch]: ${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/private/dask__dask-8597/test.patch:1
[helper]: ${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/dask__dask-8597/base/dask/array/utils.py:229
[regression]: ${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/dask__dask-8597/base/dask/array/tests/test_slicing.py:875
[grading]: ${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/private/dask__dask-8597/grading.json
[analysis]: ${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/dask__dask-8597/analysis_before_history.md
[card]: ${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/dask__dask-8597/card.md
[record]: ${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/dask__dask-8597/screening_record.json
[goldlog]: ${REPO_ROOT}/runs/env_recipe_repair_20260919/compat_v1/tasks/dask__dask-8597/gold/eval_logs/evallog_replay-er19-cv1-dask__da_cb209d73.eval.log:659
[nooplog]: ${REPO_ROOT}/runs/env_recipe_repair_20260919/compat_v1/tasks/dask__dask-8597/noop/eval_logs/evallog_replay-er19-cv1-dask__da_50713119.eval.log:777
[scoring]: ${REPO_ROOT}/rh2/src/repoharness2/envpack/scoring.py:250
[manager]: ${REPO_ROOT}/rh2/src/repoharness2/grading/manager.py:1864
[oldl1]: ${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/records/dask__dask-8597.json
[oldpilot]: ${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/dask_pilot/records/dask__dask-8597.json
[delta]: ${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/dask__dask-8597/old_findings_delta.md

