# pandas-dev__pandas-48106

目标是在base `8b72297c8799`修复categorical Series扩容：追加类别外数值应得到object并保留原值。建议仅作开发诊断，状态 **needs_review/static_review**；独立复核已完成。

| 要求/旧行为 | 断言/证据 | 范围 |
| --- | --- | --- |
| 原例追加0→object | 新 `test_additional_element_to_categorical_series_loc` 完整Series比较 | 直接覆盖；其它数值组合未穷举。 |
| 已有类别、NA保留categorical | 另15 F2P：已有类别1、nullable数值类别10、NA4 | 依据公开最小dtype、赋值与concat规则；题面未逐字列出，保留推知边界。 |
| 旧扩容、dtype、tz索引行为 | 初稿读23旧方法/74 P2P引用，历史后再读2个碰撞方法/fixtures | 实际执行1045项≠冻结16+1020参考≠已读集合。 |

八方面已查公开主例/相邻契约、精确base与初态、全部新增断言、结果等价替代路线、gold与相关回归、开发需求、精确恢复及评分边界、用途/暴露。未覆盖全仓回归、实际CC消息/actor、实际镜像泄漏、真实模型表现；跨版本关系由独立复核补充。Gold仅增categorical分支，indexing侧等价实现亦合理；一律转object的部分实现会被测试拒绝。

修复后 `pandas_meta_v3` 原始两账本各第1行证实：派生镜像、grader/54322、deny_all下源码安装与pip check完成，noop16失败/reward0，gold16通过且1020 P2P成功/reward1。revised_install与3组Period绑定确实由wrapper消费；输入recipe、run审计、原冻结参考分开。旧code-root本地副本缺席，当前源码不冒作旧字节身份。

**具体剩余问题**：两组P2P截断别名仍分别合并2/4个完整tz节点，现有binding未覆盖。六节点本次均通过，故不推翻历史对照；已证身份合并，未证错分：parser按最后有效状态摘要覆盖，noop实际FAILED摘要在PASSED后，执行先后不能代替摘要顺序。唯一优先下一步是固定grader中按真实完整摘要顺序做混合状态/缺席聚合对照；未执行，不改参考或reward。

正式actor仍取公开镜像、UID54321；`apply_user`不是开发会话。actor启用前另验解释器、checkout导入、公开复现与窄旧测试，不能由上述grader成功代替。当前 `test_globs=()`，只恢复官方 `pandas/tests/indexing/test_loc.py`，源代码修复可提交；附加排除空。普通完整pytest rc1不自动置零，全局故障另判。已见gold、隐藏测试及本题历史，本上下文不得给solver。

详情见 `analysis_before_history.md` 与 `old_findings_delta.md`；前稿SHA256 `71001b1fd048f4f5b078d0f62543ab5201cb1ba27593f75c6cc82c8925d96e59` 保留。

协调裁定：独立reviewer支持核心及相邻dtype契约，采纳两组tz聚合为唯一优先诊断；合成摘要控制不等于真实候选错分。53958/56849后期base已含本题分类分支，记录关系而不自动分组。reviewer对授权环境摘要/历史路径索引的暴露已单独披露，详见[review.md](review.md)。
