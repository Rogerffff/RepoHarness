# python__mypy-10174

`needs_review / static_review`；仅 `development_diagnostic`。mypy 0.820，base `c8bae06919674b9846e3ff864b0a44592db888eb`。原题要求no-strict-optional与strict-equality并用时，Optional[Any]成员检查不误报。gold把Any判定移到去None之后，静态合理；官方通过只覆盖局部目标。

| 需求/旧行为 | 公开依据 → 决定性断言 | 覆盖/证据 |
|---|---|---|
| 原例不误报 | 题面；F2P testOverlappingAnyTypeWithoutStrictOptional要求空诊断 | 覆盖；原noop失败、gold通过 |
| 真不重叠仍报警 | strict-equality文档、旧fixed-tuple用例 | 缺失；两P2P仅保护Any/any未导入提示 |
| strict optional开启、收窄行为保持 | 题面及meet/checker调用者 | 已静态追查；无官方相关对照 |

八方面：①题意与全部新断言已对照；②F2P、2P2P及helper/fixture完整阅读；③替代实现未被绑定，未造补丁；④共享overlap调用者与公开旧行为已追，未穷尽组合；⑤依赖/安装原日志可解释，正式actor未知；⑥历史投影、恢复、parser及逐ID已核；⑦旧报告放行后逐条复核，跨题关系未核；⑧泄漏/真实求解/成本未验。独立复核已完成，协调者保留受限静态候选。

主要风险是关闭non-strict optional下全部危险比较也可能过官方1/2；这是具体静态推断，尚无错误解满分实测。2个选择词产生3节点，执行3、解析3、冻结参考3一致，无额外未评分节点。原安装成功后noop 1失败2通过→0，gold 3通过→1；不靠pytest退出码直接推reward。

09-19派生镜像仅COPY wheels+ENV，仍原spec；grader54322与apply54321不同，均不证明正式actor可用。official仅恢复check-expressions.test；additional_exclusions=[]。当前镜像/离线资产、重复与并发未验。

唯一优先实验（未执行）：核固定grader身份、解释器/源码及依赖后，对base、gold及一个non-strict关闭比较候选同时核官方得分与同开关的 `1 in ('x','y')` 负例；确认漏测再独立修订。旧全仓统计、三假补丁及整文件重建建议不直接继承。

完整证据：[封存初稿](analysis_before_history.md)、[历史差异](old_findings_delta.md)、[机器记录](screening_record.json)。记录UTC：2026-09-20T21:35:11.383597+00:00。

协调者收束：保留受限静态候选和一个过宽候选的窄校准；未执行，不把静态路线写成已证满分反例。固定grader诊断可先行，正式actor资格另属模型开发门槛。切换strict-optional对照若以后追加，须同步移除输入内相反inline配置。

独立证据与分歧见[最终复核](review.md)。后续1.4公开base含10174的关键修复排序，15184还含15139小写分支；仅证代码包含，未核完整Git谱系或实际solver可见性。
