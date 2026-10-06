# Moto 四题 R13 matrix v2 非作者差异窄核

日期：2026-10-03。结论：**v1 的关联风险判断准确；v2 对该路径的停止检查已静态核实，没有新增静态启动阻断。** 可将下列固定 v2 用于后续既定控制臂，不能据此声称 CPU 结果或 actor 已验收。运行中的 6408 v1 和其原件保持原样，其实际是否出现该风险仍须按原件判断。

## 审查范围与最终字节

仅读取 `tools/moto_four_r13_matrix_v1/`、新 `tools/moto_four_r13_matrix_v2/` 四文件及固定 R13 原 CLI、ReplayGrader、manager、GradingReport 契约的相关分支。未运行 Docker、远端、项目、SDK、测试、模型或 CC；标准库只用于本地 SHA/bytes、逐字差异及 AST 检查。题主所述 ruff 通过不是本次独立运行结果。没有修改 v1、运行原件、冻结发布输入、既有审查报告或已固定请求；仅新增本报告。审查者已接触私有评分和反例上下文，非盲 solver。

| v2 文件 | SHA256 | 字节数 |
| --- | --- | ---: |
| `manifest.json` | `6cd02683d46370adf553531064f29d99a1e9da47ebf9f3c909f1bc6fdb9d1fd3` | 791 |
| `matrix.py` | `4f29e1364ce58897beac25407b5fd4f4db5bd2c13d3e19aa9f331436f32addd7` | 13457 |
| `tasks.json` | `b6e01cb20aeca3c6a77b930f1e5630194f636583aa376111046c9d4dbcd07117` | 26490 |
| `expected_runtime.json` | `276b9091302e587eefe6530a412793b481e1fd86cf223fbb3d77ddffe421d189` | 40272 |

实际目录恰为四文件，成员均为普通文件、非符号链接，manifest 列出的 SHA/bytes 全部匹配。v2 manifest 明确派生自 v1 manifest `a72d5d57e6c85f12105642ac1ef91e1aa18e618afb39ddd93133184850b7ef99`。独立读回 v1 manifest 仍为此 SHA；v1 `matrix.py` 仍为 `e721d4bf7a44fc50011ac89d46a435fe765e15bd3fd79e71161d46c3cb5e6ea2` / 13170 字节，没有覆盖。

`tasks.json` 与 `expected_runtime.json` 均与 v1 **逐字相同**。v2 matrix 的完整 diff 只有 185–188 行新增的四行、287 字节：

```python
        report = row['report']
        require(report['outcome'] in ('resolved', 'unresolved') and
                report['failure_category'] in (None, 'tests_failed') and report['reward'] in (0, 1),
                '评分基础设施/解析失败；停止后续候选，保留原件')
```

从 v2 删除这段唯一出现的字节，完整文件即逐字恢复 v1；v2 AST 可解析。因此 CLI、consumer、候选及数量、选择规则、安装/测试、预算、镜像、资源、输出路径、结果格式和清理实现均未发生其他改动。manifest 的 schema/scope/派生说明及 matrix 成员摘要随版本改变。

本次复用[此前 R13 v1 静态报告](moto_four_r13_matrix_tools_non_author_20261003.md)对其余工具项的核查，原报告 SHA 为 `988d7b579248efdcd47effd7a0d4b4749eb6954dd660c3fa6c788f16c319ac1f`；这里补充该报告当时未识别的 report 形状风险，不回写历史报告。固定 release 仍为 `cat2-cpu-r2e089092-swe27-pandas-moto-20261003-v1`，本地 release manifest SHA 再次读回为 `3fad18daff8db219294e10cbf08d4424d68cf7000d008bb983cba4bdc427b641`，与 tasks config 一致。

## v1 关联风险的实际代码依据

以下行号均为 `runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe27_pandas_moto_v1/repo/rh2/` 下原文件：

- `src/repoharness2/grading/manager.py:2161–2190`：捕获 `GradingInfraError`，构造并返回 `outcome='failed_to_grade'`、`failure_category=exc.category`、`reward=None` 的非空 report；finally 仍执行原 grader scope 清理。
- `src/repoharness2/contracts/grading.py:247–267`：这个 report 是原契约允许的基础设施/日志解析失败，必须无 reward、无测试计数，并保留失败说明；不能当 reward 0。
- `src/repoharness2/adapters/slime/replay_grade.py:705–725`：manager 正常返回 report 时进入 `_fill_from_report`，不必设置 `stage_error`。其 780–794 行按原 report 直接把 outcome、failure_category、reward、失败说明和计数写入 ledger，不会将 None 改成 0。
- `scripts/replay_grade.py:108–115`：finally 调用 `manager.close()`，最终退出码判断入口/清理是否正常结束。一次 failed_to_grade report 在已清理、未 halted/aborted 的条件下可以对应 CLI rc 0；退出 0 不代表语义评分成功。

因而 v1 仅要求 `stage_error is None` 与 `report is not None`，不足以排除上述报告。如果镜像、候选清理、footer 和自有残留查询也满足其条件，v1 会把 `reward=None` 追加到 completed rows，与 0/1 expected reward 比较为不匹配，并继续后续控制臂，最后整体 rc 1。四题所有 expected reward 实际都是 0/1，不存在将 None 比较为通过的臂；v1 的结果字段也保留 `formal_cpu_accepted=False`。问题是继续调度及错误地把这次动作纳入“控制臂已完成”汇总，不能把它表述为自动给基础设施失败授予 CPU 准入。

这是确定存在的代码路径，**不是对运行中 6408 已触发该路径的判断**。本次没有读取该 job 的结果，不宣称任何控制臂完成或失败。既有 v1 原件应逐臂读真实 report 与安装/测试/清理证据；不能用整体 rc 1 推断是普通候选语义不匹配，也不要求因此机械重跑所有正常臂。

## v2 的行为与适用边界

新增 guard 位于原 CLI 返回、唯一 ledger 行及 stage_error/report 基础检查之后，位于镜像/清理/footer/残留验收、expected reward 比较、`completed_controls.json` 追加和下一臂启动之前。`require` 失败直接抛异常，顶层没有吞掉或自动重试该异常，因此 failed_to_grade / None 会非零结束并保留已写 CLI stdout/stderr、exit、ledger、artifacts；不产生当前臂的完成行，也不启动后续臂。这是在当前 CLI 已收口之后停止编排，不是中途改变 grader 判分或取消正在运行的测试。

原 R13 report 契约和 manager 对普通完整测试结果生成 resolved / None / 1 或 unresolved / tests_failed / 0，三项均有真实键且类型与 guard 相容；不存在读取不存在的 report 属性。0.0/1.0 与这里的二值比较相容。guard 不改原 score，不改 expected reward 或参考列表，不建立新的公共 report 契约。

**该 whitelist 比“仅排除基础设施失败”更窄。** 原契约还允许 `patch_apply_failed`、`candidate_execution_failed`、`test_execution_timeout` 等 unresolved/reward0 类别，manager 也有前两类生产分支；它们会被 v2 的 failure_category 条件拒绝。对此应保留原归因，不把它们一律改判为基础设施失败。新增错误文句将所有被拒情况统称“评分基础设施/解析失败”，在这些类别下描述不够准确；本报告明确其真实边界。在要求这些固定控制臂形成完整安装/测试对照的工具范围内，停止并保留原件可接受，未发现必须先修工具才能启动的问题。它不意味着这几类合法 reward0 被原评分契约撤销或失去训练负样本资格。

正常 report 通过新增 guard 后，镜像、候选移除、manager footer、自有资源查询及 expected reward 比较仍走原代码。v2 拒绝当前臂时，后面的额外 Docker 残留查询不会执行；因此失败分支只能保留原 CLI 清理证据待读回，不能声称已完成那些查询或已独立确认零残留。实际清理仍由原 CLI finally/manager 完成，原件验收不得只看 guard 文句。

## 未变化的诊断身份与后续验收

逐字不变的配置仍为 5960/6408/6185/7584 共 3/3/22/11 臂，完整选择集共 39 臂；本次不扩大或重复运行。5960/6408 使用注册 recipe 的 source Config ID 走原 R13 exact local override 诊断路径，6185/7584 使用注册 COPY-only actual ID；原 public source face 保留。R5 原 source 分支缺 ledger actual ID 的问题不能机械套用到此 R13 derived 路径。

6185/7584 的 gold 仍为 `gold_known_incomplete`、expected reward 0；6185 `rv_dynamotype` 仍为 expected raw reward 1、role=`observation_not_positive`。新增 guard 不把这些身份改为完整正例或语义正确补丁。正常 reward 与 expected reward 相符后，结果依然标为 `selected_controls_completed_pending_raw_and_independent_review`，`formal_cpu_accepted=False`、`actor_executed=False`，不会授予 actor、typed actor、模型或训练资格。

可启动结论仅覆盖上述固定新字节和四行修正。实际 CPU 验收仍需按各 job 原件读回完整安装/测试、report 归因与计数、实际镜像/资源、候选及 manager 清理、footer、自有资源查询，并区分停止、未执行与正常测试不匹配。v2 尚无本次审查确认的执行结果；不覆盖或修改在途 v1，不从入槽 75 推断评分失败。
