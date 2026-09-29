# dask__dask-7138：旧发现逐项差异

root明确release后仅读本题L1_dask记录，SHA与refs吻合；未沿旧链接读取raw hints/早期日志/全仓汇总/其它题/reviewer。

| 旧主张/位置 | 结论 | 决定性依据与边界 |
|---|---|---|
| checks1/2/4/17：材料匹配，base直接reshape失败，源码修复可投影 | 确认局部 | base/patch/candidate字节一致，本次noop在0标量第一条AttributeError；gold仅routines.py，测试恢复成功。不替代actor输入/初态 |
| check3 pass：题面完整且无hints独有信息 | 收窄 | 已读计划公开文本完整；raw hints为空仅旧转述未另核，实际actor收到何内容unknown。规格23与输入3分开 |
| check23：标量/list/tuple/nested与Array返回类型合理 | 确认 | 完整test.patch8断言及asanyarray公开返回Dask文档；返回类型未逐字写在issue不使它成为任意私有要求 |
| check24：多个替代实现“都能过” | 收窄为静态可行，未证普遍接受 | 不锁具体helper；保留array形参并转换是合理替代。asarray与asanyarray对子类chunks不等价；未实际实现/跑完整替代解，不能宣称全部都能过 |
| check25：F2P/P2P判别力完整 | 纠正过强结论 | 新非Dask输入全是零，未验证非零顺序/保真、空输入；array=旧调用缺测。旧Dask随机数据P2P不补列表路径；完整覆盖不能由468个状态推出 |
| check25/proposed_regression_tests：test_ravel_1D_no_op保证零拷贝、会拦复制 | 纠正 | 980–986只有assert_eq已知/未知长度结果，无is身份、内存共享或复制次数断言。test_ravel有图长度约束是另一项局部证据，仍非任意零拷贝保证 |
| checks26/27：gold无回归、两行均无问题 | 纠正/收窄 | 完整签名由array改array_like；derived_from正常分支只设置docstring再返回函数，因此原array=调用会绑定失败。这是静态明确兼容性差异，未运行；转换主体对所读输入有正证据，不代表完整无回归 |
| check29：公开题面自带修复，不适合作定位能力指标 | 确认材料属性、收窄推论 | 题面提供近乎修法的代码但含asasanyarray笔误；记录statement_contains_fix。属于公开引导程度，不证明私有泄漏、实际actor已见或真实能力/成功率；不能直接批准训练 |
| checks6/11：pytest8导致92恒FAILED、应降到pytest<7 | 对本次条件过时并纠正必要版本上界 | 本次引用dask7138-pytest-v1 pair：Python3.8.15/pytest7.4.4，gold561pass、92warnings，testRC0；noop只新增标量F2P失败。pytest<7并非此次恢复必要条件；旧92失败原件未再读，不反向否认早期运行 |
| checks7/8/9：本地依赖、P2P468通过、“同族ravel_multi_index” | 确认运行局部/收窄语义 | expected逐ID均PASSED；只有test_ravel/test_ravel_1D_no_op本次语义核读直接覆盖受改ravel。函数名相似的ravel_multi_index/unravel_index不能自动算同调用路径 |
| proposed union1d/append集成 | 部分支持、未核 | 已读union1d确用ar.ravel方法；未读/运行完整append，不能把“若同一路径”升级已证集成。旧测试建议不是实测 |
| check5包内唯一、ready_for_probe、可用于训练、minutes18 | 未核或不继承 | 未扩读关系prescan；actual actor仍unknown，且新发现关键字回归。当前needs_review/static_review、development_diagnostic，成本null |

封存初判保持：转换目标基本明确，历史grader判别成立；参数更名回归须单列check26，漏测单列25，gold局部正证据与完整性分开。history只增加旧过度覆盖/零拷贝承诺的纠正与旧环境问题时效记录。唯一优先下一步仍是由维护者明确保留旧array=兼容并处理gold参考，不为确定签名差异机械安排CPU。实际actor资格另由任务二核验。


封存初稿：[analysis_before_history.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-7138/analysis_before_history.md)（SHA256 `171bac649f1b83fbfe7eeab666ac4b5f6b608d273a9f516d37f9166b1a21a097`）。

本次release后历史读取仅：

- [dask__dask-7138.json](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/records/dask__dask-7138.json)；SHA256 `ea6f61ecb906af265925354e43bc1ba97b06e416cdb90fceef0e166945345cc5`。
