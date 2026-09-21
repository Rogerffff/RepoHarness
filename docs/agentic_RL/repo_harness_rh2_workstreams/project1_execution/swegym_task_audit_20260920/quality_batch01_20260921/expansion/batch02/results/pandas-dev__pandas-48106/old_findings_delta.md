# pandas-dev__pandas-48106：历史差异

独立初稿封存SHA256：`71001b1fd048f4f5b078d0f62543ab5201cb1ba27593f75c6cc82c8925d96e59`。协调者确认后，才读 `runs/swegym_quality_batch02_20260921_v2/history/pandas-dev__pandas-48106/refs.json` 及其唯一记录 `env_overnight_20260916/L1_modin_pandas/records/pandas-dev__pandas-48106.json`。未改封存稿，未读reviewer/批次聚合。后续只追本题精确raw行与已有本题原始日志/源码。

| 旧主张 | 结论 | 决定性依据与当前含义 |
| --- | --- | --- |
| 原例明确、base含缺陷、gold/测试路径分离 | 确认 | 本轮自行读调用链与全部新增断言；pandas_meta_v3 noop实际在题面TypeError及dtype断言失败，gold完整通过。 |
| 15/16 F2P无法从公开信息推出，且与“扩容转object”方向冲突 | 部分确认、推翻其确定性处置 | 确认标题/原例没有逐字列出已有类别和NA保留。不能只截取括号句泛化为所有扩容强制object：公开最小dtype契约、categorical赋值/concat文档、已有set-into测试支持保留dtype。语义仍有推知边界，但不足以认定必须改题面或删除测试。旧记录把nullable-EA数量写成12，实际fixture为10；其它15节点=已有类别1+EA10+NA4。全部16在noop失败，直接把其中若干改成P2P也不符合P2P应保护初态已通过行为的含义。保留reviewer判断，不为使gold过而补写全套隐藏标准。 |
| 不限定gold内部实现；结果断言能挡住一律object/一律category | 确认（静态范围） | 可在indexing调用方处理categorical；新增断言仅看值/dtype/index，无helper或Mock要求。未运行替代实现，不能称已证所有合理解可过。 |
| 三个P2P参考永远missing，gold恒reward0 | 对原parser缺陷确认；对当前配方已过时 | 两run `.reference.json` 的original确有missing3，revised为missing0且P2P1020/1020。输入bindings3组→7完整Period节点，all-members语义已消费，原始日志各成员都PASSED。旧建议直接剔除参考没有必要，也没有执行。 |
| 还有两组截断别名采用后写覆盖 | 确认，补充初稿遗漏 | 当前pandas_meta_v3日志仍存在下述2组→6完整node，现有bindings仅修Period组。当前parser的 `test_status_map[test_case[1]] = test_case[0]` 仍以最后有效摘要行覆盖同别名；六成员本次全PASSED，因此不改变此次0/1对照。已证身份合并，未证错误reward，需按完整摘要顺序验证混合状态。 |
| 安装必须联网；约779秒是rollout固定成本 | 对当前条件过时/证据越界 | 修复后真实grader deny_all完成预置wheel、editable源码安装与pip check，约708秒。旧安装命令不等于必须在解题/测试时联网；这些是grader历史安装时间，不是actor固定成本或模型费用。 |
| hints含first bad commit与PR47342，必然泄漏 | 原文存在确认；泄漏定性缩窄 | 精确raw `s2/raw/swe_gym_lite_full_f70b1a29.jsonl:166` 的本题hints确有坏提交和PR47342、maybe_promote最小例。它是肇因定位线索，不能未经内容核对就称提供本题未来gold。当前实际public bundle的public_hints是harness说明，不含这段raw hints；题面traceback的旧源码行也不是新增gold。实际镜像/公网取答案条件仍未知。 |
| stdout伪状态风险 | 结构性风险确认，未验证实际可得分 | pyproject设置capture=no、parser仍识别状态行；没有本轮候选攻击实验。旧建议只筛“属于参考集”的状态行不解决伪造同一参考ID，不据此声称完成加固。作为共享评分控制面限制保留，不自行改本题文件规则。 |
| 无跨题重复、回归全部pass、实际blind solver可用 | 未核实/不外推 | 本轮没有访问其他题内容来认证关系；读过相关P2P与共享函数旧测试但未全仓执行。历史记录提出的额外回归命令不是通过证据。实际actor与模型端尚无本题证据。 |

## 新核实的两组碰撞

1. 冻结别名以 `TestLocBaseIndependent::test_loc_setitem_datetimeindex_tz[datetime.timezone(datetime.timedelta(days=-1,` 截断，完整节点分别以 `seconds=82800), 'foo')-var]` 和 `...-idxer1]` 结束。gold日志5133–5134、noop6112–6113均PASSED。
2. 别名以 `TestPartialStringSlicing::test_loc_getitem_partial_slice_non_monotonicity[datetime.timezone(datetime.timedelta(days=-1,` 截断，四成员为DataFrame/Series × None/`2020-01-02 23:59:59.999999999`。gold5691–5694、noop6654–6657均PASSED。

后续补读base `test_loc.py:1430–1440,2239–2273`：第一项检验float DataFrame对标量/列表列选择的tz赋值；第二项检验非单调DatetimeIndex下普通切片和loc切片，两次结果比较。并读conftest `frame_or_series:445`、`TIMEZONES/tz_naive_fixture/tz_aware_fixture:1195–1243`：tz对象repr确实包含空格，构成截断来源。它们保护既有可观察行为，不是无关ID装饰。初稿的实际已读23旧方法/74冻结P2P范围保留原时点；此处新增2方法及其fixture。

## 相对初判的变化

不改变原题/测试/gold与历史修复后真实0/1结果的判断；保留 `needs_review/static_review`。但初稿“没有具体oracle疑点、唯一下一步actor验证”现在需收窄：**优先在固定grader的当前解析/绑定入口，对本题两个碰撞组做遵循真实完整pytest -rA摘要顺序的混合状态聚合对照，比较别名结果与完整节点的原参考要求。** 同时保留PASSED/FAILED/XFAIL/SKIPPED及成员缺席的精确位置，不能只在原PASSED位置替换FAILED并假定那就是pytest实际输出。只改变诊断输入、不修改生产测试/参考；若验证到错分，再提出两组显式all-members绑定的版本化接线修复，并复证现有noop/gold与触发对照。该CPU尚未执行，目前是身份合并及结果顺序依赖，不是已观察到真实候选假阳性。

此评分身份验证与正式actor UID54321开发启用前验证分开；任何一个通过都不代替另一个。当前 `parse_log_pytest` 只读行首状态词摘要，不读普通verbose执行行；reference_bindings只覆盖显式三组别名。本题noop原日志先列PASSED，再于6968–6983列FAILED摘要，故测试执行先失败、后通过不意味着最后有效摘要为PASSED，FAILED可能最终覆盖回来。普通pytest rc1不自动reward0，但也不能据此假定该两组一定漏判失败。当前ROOT/rh2源码与旧run plan的resources_v1 code-root未证明同字节，继续明确两层证据。
