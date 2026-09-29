# dask__dask-9378 静态短卡

state=needs_review，限 development_diagnostic；base为8b95f983c232。核心疑点是ones/zeros未直接比较mask，优先级高于命名空间解释。详见[封存初判](analysis_before_history.md)和[历史差异及初判修正](old_findings_delta.md)。独立交叉复核与协调收口已完成，详见[复核](review.md)。

| 需求 | 公开依据 | 断言 | 范围 |
|---|---|---|---|
| ones/zeros保留逐元素mask | 题面明示 | assert_eq→np.ma.allclose(masked_equal=True) | 类型/值有查，mask equality缺失 |
| empty保留mask | 同上 | 比较getmaskarray | 合理不比未初始化值；返回本体dtype/惰性未测 |
| ma新入口 | 题面末段建议 | getattr(da.ma,函数名) | 有公开依据；顶层-only候选的接受性未验证 |

gold三个按块包装的默认路线合理；已有134项P2P均通过，但固定3×2不能排除硬编码或证明惰性。现有窄断言是否会漏放错mask仍待运行验证；未做mutation或完整候选评分实验。新补读derived_from后，收窄初判dtype风险：wrapper未显式列出的参数可能被文档标为不支持，不能由**kwargs反推承诺兼容。旧“缺docstring导入崩溃”被源码None处理直接反驳。

原baseline01账本11/12行：Python3.10.14、pytest8.3.2，安装RC0，noop3失败134通过，gold137通过；非维修派生镜像，实际image ID=null。已查八方面中的目标/版本、全部新断言/helper、相关P2P、gold/替代路线、开发需求、投影与单测试文件恢复；未获actual actor消息/工作树、权限资产及功能运行，不以历史grader替代。

唯一优先下一步：任务二私有CPU诊断保留shape/dtype/MaskedArray类型与正确常量值、仅改错ones/zeros的mask，检查现有断言是否漏放，并与显式mask比较对照。此处不执行或派发。actor公开开发入口仍须另取得证据。check29 actual暴露unknown，审查授权gold/隐藏测试/两份旧记录在usage；check40 unknown，不以盲读封存证明无漏检误杀。未批准正式训练/评测。

协调收口：确认ones/zeros的mask equality漏测静态疑点；收窄derived_from为依赖实际签名/doc参数行的条件性机制。empty未初始化数值不得要求随机/非固定；窄断言通过不等于完整评分通过。 原主审card/record已按完成hash归档；封存初判、delta、review未回改。
