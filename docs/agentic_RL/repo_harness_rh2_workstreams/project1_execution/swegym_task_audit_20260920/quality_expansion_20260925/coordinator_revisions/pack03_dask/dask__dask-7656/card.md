# dask__dask-7656 静态短卡

建议作为范围明确的 development_diagnostic 候选，state=needs_review。base为07d5ad0ab1bc；目标是缺失init=False字段不阻断delayed建图与求值。题面自带修复方向，可观察应用公开线索的能力，不能当纯独立定位指标。完整证据见[初判](analysis_before_history.md)和[历史差异](old_findings_delta.md)；未读reviewer输出。

| 需求 | 公开依据 | 决定性断言 | 范围 |
|---|---|---|---|
| 缺失非初始化字段不报错 | Entry题例 | 新b=field(init=False)，compute()==3 | 目标F2P直接覆盖 |
| 嵌套字段正常求值 | 公开旧同名测试 | a=delayed(3)与return_nested | 防止整体不透明处理 |
| to_task_dask/base遍历兼容 | 相邻公开实现 | 旧P2P不含dataclass；base测试非expected | 边界覆盖缺口，非必修范围证明 |

gold过滤缺失属性，仍把已有init=False字段当构造kwargs；这不等于正确恢复状态。旧记录建议“post_init例子gold必过、if f.init必丢值”缺乏依据，构造器可能反而拒绝gold。未核旧候选/oracle原件，不沿链接扩读。既有邻接遗漏不冒称gold新回归，未执行替代解不声称普遍无误拒。

原compat_v2b使用Python3.9.19、pytest8.3.2、离线pandas1.3.5及stdlib distutils；noop1失败49通过2xfail，gold50通过2xfail，F2P1/P2P48均吻合。安装、源码单文件投影及可信测试恢复只证明这些grader条件。八方面已查静态目标/版本、全部修改fixture与helper、风险相关P2P、gold/调用者、开发需求和交付边界；actual actor消息、初始工作树、依赖资产/权限及真实开发路径仍unknown。

唯一优先下一步：任务二在实际actor执行公开Entry→delayed→compute，并检查默认字段和嵌套求值，保存身份、初态、导入及RC；本审查未执行或派发。无需SQL服务、GPU或外部数据。check29实际答案暴露unknown，授权私有材料放usage；check40 unknown。静态封存与旧grader成功均非正式训练/评测资格。
