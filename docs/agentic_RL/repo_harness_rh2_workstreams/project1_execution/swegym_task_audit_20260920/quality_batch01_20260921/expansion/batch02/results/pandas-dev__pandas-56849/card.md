# pandas-dev__pandas-56849

恢复小写 `m` 的月末频率兼容行为。base `612823e82480`，原镜像 digest `a8a1cad9…`；建议保留为 development_diagnostic 静态候选，状态 needs_review/static_review，独立复核已完成。

| 需求/旧行为 | 核心映射 | 结论 |
| --- | --- | --- |
| m月末范围 | 题面20点；唯一F2P检查2010年1、2月末及FutureWarning | 核心覆盖；未直接检查20点、m倍数、共享to_offset入口。 |
| 弃用与规范ME | base已有M→ME及FutureWarning；新增整句regex要求小写m | 类别/替代名有公开依据；警告大小写有合理解误拒疑点。 |
| 频率属性 | expected含freq=ME，assert_index_equal不检查DatetimeIndex.freq | 具体漏测边界，尚无错误候选获分实验。 |
| 旧解析边界 | 已读全test_to_offset及日期范围相关P2P/fixture | 保护单位、非法语法、倍数、锚点和部分日期边界；未审全仓。 |

八方面已核公开需求、base路径与初态、全新增/修改断言、替代解与部分实现、相关回归/gold、开发条件、精确恢复/投影及用途暴露。正式actor、完整P2P测试体、稳定性与实际泄漏仍未知；跨版本关系由复核补充。

原始W ledger11/12和N/G日志确认：noop目标失败，gold重编offsets.pyx后426个实际测试通过。冻结参考为1 F2P+419 P2P；空格参数将10节点合为4键，故仅420评分键。现有合并节点都通过，不推翻分差，但不可称每个参数身份均独立保护。普通非参考失败不自动决定reward。

安装/测试是rh2grader/54322，candidate.apply_user=agent/54321不证明actor可开发。两官方恢复文件都是测试，gold的.pyx可提交；test_globs为空，额外排除为空。actor须能导入并重编当前checkout；业务复现无外部资产或公网依赖。

历史复核纠正“freq被断言”“warning类别完全无据”及“前缀改变必破filter”；保留小写措辞疑点与参数键合并。唯一优先实验是用保持公开语义、仅规范化已识别旧名并以M发警告的非gold实现，核公开行为后重放RH2，确认拒绝是否仅由warning断言造成。未运行新CPU或模型；证据、路径与阅读范围见封存分析及old_findings_delta。

协调裁定：独立reviewer采纳warning规范化对照为唯一优先下一步，actor的Cython开发验证保留在模型启用前。后期本题base已含48106分类分支及53958类型导出，记录版本包含关系，不当作同题或实际运行泄漏。封存稿及主审有界历史暴露披露保留，见[review.md](review.md)。
