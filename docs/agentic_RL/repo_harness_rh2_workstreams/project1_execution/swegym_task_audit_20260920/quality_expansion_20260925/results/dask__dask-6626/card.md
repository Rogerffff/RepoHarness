# dask__dask-6626 静态短卡

建议保留为 development_diagnostic 候选，state=needs_review；公开目标是 set_index 后已知空类别元数据与计算结果一致。base为56cd4597630f。八方面、双向全表与精确日志见[封存初判](analysis_before_history.md)，历史逐项比较见[差异记录](old_findings_delta.md)。独立交叉复核与协调收口已完成，详见[复核](review.md)。

| 需求 | 公开依据 | 决定性断言 | 范围 |
|---|---|---|---|
| 空类别不凭空变a/b | 题面、categorical元数据文档 | K的dtype相等及categories长度0 | helper直接覆盖；noop先在K dtype失败 |
| set_index两条路径一致 | 题面两例 | 无端到端断言 | 集成缺口 |
| 保留正常/未知类别和类型 | 旧utils测试 | A/J、O/f8/M8[ns]类型/ordered/name | 有P2P，空Index类别长度未测 |

gold只修Series空类别构造，默认目标有证据；CategoricalIndex邻接遗漏不是新增回归。测试不锁代码写法，调用侧局部修复的接受边界保留，未执行合法替代解。历史“pytest8导致sparse恒失败”对当前引用条件过时：compat_v1离线pytest7.4.4，gold16通过，noop1失败15通过；F2P1/P2P14且额外sparse两侧通过。runner digest发生变化，尚未核字节差异，不能泛称完整性通过。

已查目标/版本、新增fixture/assert、gold/调用者、相关P2P、单文件投影与可信恢复；未查实际actor输入、HEAD/status/diff、资产、用户权限、解释器及公开功能运行。Git导出不代表镜像初态；历史rh2grader也不代表actor。当前无需外部数据/服务/GPU的最小例子有公开依据，开发命令和资产权限仍待验。

唯一优先下一步：任务二在实际actor入口运行题面两条set_index流程，保存初态、身份、导入位置、RC与类别/计算结果。本文未执行或派发。check29实际泄漏unknown；主审合法看到gold/隐藏测试和指定旧记录只计入usage。check40 unknown；封存不证明无漏检误杀。未批准训练或正式评测。

协调收口：确认helper dtype目标、两条公开set_index流程覆盖缺口与runner digest未解；清除跨题模板残句，不把历史sparse问题继续作为当前阻塞。 原主审card/record已按完成hash归档；封存初判、delta、review未回改。
