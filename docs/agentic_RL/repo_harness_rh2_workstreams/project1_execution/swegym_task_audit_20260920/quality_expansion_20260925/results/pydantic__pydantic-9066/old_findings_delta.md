# pydantic__pydantic-9066 — 旧发现对照

root 已明确释放本题history/refs.json。前稿SHA256=212281deb809c58b20d14d57dbc104c7710d07612cace57d37dc13d25e1fa305，本阶段核对未改写。仅新增读取refs.sources[0]：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_pydantic/records/pydantic__pydantic-9066.json，SHA256=14510c774ad525bdb17c054d9555b438572bde42f6e221464b2c0c22f8bc5713，授权hash一致。未跟随该记录的其他题/R2/R4/R8/summary链接；未读reviewer/根结果，未执行项目。

S=本轮静态证据；H19=前稿已核本题09-19真实RH2原件；O16=当前获准旧JSON，不等于其引述实验已重新核验。

| O16旧主张 | 处理 | 决定性证据与当前结论 |
|---|---|---|
| 目标为IP默认值JSON Schema编码 | 确认 | P原例和networks.py:511–575支持；IPv6是IPvAnyAddress公开支持的同类扩展，非新增任意用户类型规格。 |
| core“返回不可JSON序列化的值，随后被warning” | 纠正机制措辞 | H19 noop trace :1071–1075/:1142–1146显示to_jsonable_python直接抛PydanticSerializationError，default_schema:1011–1019捕获后告警/省略default，不是返回错误值。 |
| check3输入完整/pass | 收窄 | 原例计划文本完整归规格23；实际模型消息/hints/工具呈现未捕获，3 unknown。旧hints定位链接是否实际可见不从摘要推断。 |
| 单测试文件/单源码gold，exclusions空 | 确认 | Q全文、H19投影/可信测试恢复，actual actor交付仍待核。 |
| 6126 gold 3/3行在本base，故跨题答案泄露，强制同侧 | 未核且收窄定性 | 本阶段只获准本题旧记录，不访问6126。只能保留“O16曾提出此关系，待获授权精确核对”；即使未来修复存在于后续基线，也需要结合具体split时间/使用角色证明泄露，不能用行重叠单独宣布A收到私有答案。本包8793修复存在本base的关系已独立核到，但不是O16的6126证据。 |
| install rc2且需要网络 | 旧条件未核；不能用于本次H19 | O16 stage1日志未读；H19 pydantic-install-v1、editable pip+候选testing/testing-extra、PIP_NO_INDEX wheelhouse、deny_all下两安装RC0，目标测试确实执行。环境修订非题目规格修订；A入口/UID/权限/PATH/资产依旧unknown。 |
| 资产无问题、无本题CC轨迹 | 收窄/保持缺证据 | H19有grader依赖与收集执行事实，不能证明A资产/开发条件；当前仍没有实际actor验证。 |
| 不强制唯一实现 | 确认有限S观察 | 两完整schema断言没有TypeAdapter或内部路径限制，但没有替代解执行证据，24 unknown而非全称pass。 |
| “只特判ipaddress”是oracle_accepts_hardcoded_fix，需添加非IP类型 | 纠正 | 若按IPv4/IPv6类别正确编码而保留旧行为，是与公开问题相符的合理局部实现；不采用gold通用TypeAdapter并不自动错误。只有对测试地址字面量/字段名硬编码才是明显不完整。不能为拒绝合法局部解机械加入自定义类型或Path新需求。 |
| 新except分支零覆盖，hasattr两侧无断言 | 收窄，部分纠正 | 已读P2P test_non_serializable_default两参数，尤其lambda默认值；type(lambda)是函数类而非函数实例，_typing_extra.py:81–82与_generate_schema.py:745–830显示它不等于typing.Callable、也不是函数实例分支，默认配置下走_unknown_type_schema:398–407，触发gold转换；default_schema把它转回原告警。该路径为S推断，H19相应P2P确PASS，但无分支插桩不能称动态分支覆盖率已测。BaseModel默认P2P走有serializer分支，IP F2P走TypeAdapter分支，因此“完全没有两侧行为断言”过强；普通dataclass交界仍是具体遗漏。 |
| 所有默认值都新建TypeAdapter | 纠正量词 | gold有hasattr(__pydantic_serializer__)短路，不是每一个默认值；其余值新增适配器构建开销属S风险，没有耗时/副作用实测，不定为性能回归。 |
| gold把warning升级成异常、行为收紧 | 推翻一般性主张 | gold新增PydanticSerializationError仍被default_schema:1013捕获，发同样non-serializable-default warning，现有P2P验证警告与省略default。pytest filterwarnings=error在base/gold都适用，不能把测试告警转异常归因gold。不同的PydanticUserError仍可能逃逸，正是前稿标准dataclass疑点，应单独保留。 |
| object()无法生成schema，应用它验证新except，且应抛PydanticSerializationError | 纠正示例与公共预期 | _generate_schema.py:768–769明确object类型生成any_schema，不是验证该新except的合适例子；即使编码器抛serialization error，公共model_json_schema的旧约定也是捕获告警/省略default，不能直接把内部异常设成用户API验收标准。 |
| check26=issue，因为所有默认值共用出口 | 纠正分类 | 通用影响只证明需要回归审查，归25；没有base/gold失败对照不能称26已证回归。前稿dataclass异常链仍为unconfirmed，26 unknown。 |
| bytes/timedelta/int/str等完全没有护栏 | 纠正 | 已读P2P model/dataclass/typeddict default_bytes/default_timedelta、list/dict/enum、model/nested default等原断言与H19 PASS。覆盖有范围，不能以未覆盖一类对象否定这些已有回归正证据。 |
| check29零leak/pass、check31 R4 issue | 均未核当前事实 | 未获得实际actor可见材料或R4细节；29、31 unknown。审查者当前见gold/hidden/O16是授权私有暴露，另列usage。 |
| ready_for_probe，15分钟 | 不沿用 | 本批state=needs_review/scope=static_review，intended_use=development_diagnostic；成本不是本轮观测，均null。 |

对封存初判的影响：旧记录没有提供标准dataclass对照结果，也不推翻前稿的具体异常链。前稿已把普通serializer错误的上层捕获与TypeAdapter配置异常区分，结论保持；本阶段补读_generate_schema:386–407,745–832，_typing_extra:81–82和errors:80–108，进一步排除旧“warning普遍升级”与“except零覆盖”推断。没有把旧label当作当前判断。

唯一优先下一步不变：任务二在独立私有CPU条件对同base/gold执行标准库dataclass默认实例的BaseModel.model_json_schema公共API，并以原IP例为目标控制。记录base/gold schema default、warning、异常code；只有base可用/gold抛type-adapter-config-unused才能把26标为已证回归。无需全仓/GPU，不为拒绝合法IP局部修复扩张规格。A输入/环境未核仍独立保留，不会被私有对照成功取代。
