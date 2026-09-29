# pydantic__pydantic-8511

base `e4fa099d5add`，目标是让 Pydantic dataclass 的赋值式 `Field(repr=False)` 隐藏该字段并保留其它字段。建议 `needs_review/static_review`，用途限开发诊断；先验证具体回归嫌疑，再决定模型探针优先级。

| 需求或旧行为 | 依据与验收 | 覆盖 |
|---|---|---|
| 隐藏字段、保留普通可见字段 | 题面、Field.repr；唯一F2P的正负子串断言 | 核心覆盖 |
| stdlib对照与两种默认工厂 | repr[field]、factory[field/Field] P2P | 原始两角色均过 |
| 默认Field仍显示、空子类继承必填/工厂Field | repr默认True、继承接口 | 未直接保护 |

八方面已查：题面与精确base、全部新增修改断言及fixture、F2P与相关P2P正文、替代实现、gold、开发依赖、投影恢复、用途暴露。未逐条展开所有168个P2P体，未验正式actor、完整消息、镜像答案资产或跨题关系。

原始09-19 RH2日志哈希匹配：Python3.8派生配方 `pydantic-install-v1` 下，noop为1失败/168通过/11跳过，gold为169通过/11跳过；安装均rc0，参考无缺席。10个>=3.10的kw_only/slots用例既跳过又不在冻结参考，不能视为已保护。镜像还有pyproject/pdm.lock环境差异；grader成功不证明actor已消费该配方。

独立静态发现：gold用继承式 `getattr(cls,'__annotations__',[])` 遍历，再向当前类写字段。旧Python上，父类必填或工厂FieldInfo可能被重新写入没有本地注解的空子类，引发装饰失败。现有继承P2P只用default=1，避开此路径；尚无运行反例，不定性为已确认gold错误。另缺默认Field显示断言，错误地隐藏所有FieldInfo可能过关，亦未实际计分。

历史复核确认旧安装阻塞在所引grader条件下已过时；compare/hash/metadata不属本题公开承诺，不补成新功能要求。独立复核已完成（review.md）；G1为主审发现、第二阶段核实，审查暴露含隐藏测试、gold与两份历史记录。

唯一优先CPU实验：在同配方Python3.8中对照base、gold及只读本地annotations的窄修正版，运行“父类Field()/repr=False/工厂/显式默认值＋无本地注解子类”矩阵，并列官方得分。具体类定义、证据路径与其它未知见 [封存分析](analysis_before_history.md)；历史差异见 [复核记录](old_findings_delta.md)。

复核补充：8511较新base的Sequence实现含对应JSON/Python分支；非两题重复的证明，完整祖先/全池关系未查。
