# pydantic__pydantic-9066

静态结论：needs_review / static_review，仅用于development_diagnostic。base a3b7214a1d6a；目标是IPvAnyAddress字段的IP默认值正常写入JSON Schema，不是修IP输入解析。

| 需求/旧行为 | 断言 | 结论 |
|---|---|---|
| IPv4/IPv6默认值变字符串且无目标告警 | 两参数完整schema | 有公开依据，noop失败/gold通过 |
| 非序列化值告警省略、bytes/timedelta配置、嵌套模型保持 | 已读相应P2P | 有局部正证据 |
| 标准dataclass实例作为默认值不崩溃 | 无针对断言 | gold存在具体配置冲突疑点，待证 |

gold对无自身serializer的值调用TypeAdapter(type(value),config=...)。标准dataclass也被TypeAdapter认作自带配置，会抛type-adapter-config-unused；该PydanticUserError不在gold/调用者的捕获范围。此为静态链，尚无base/gold同例运行，不能标已证回归。

旧“gold把warning升级成异常”被源码否定：PydanticSerializationError会被default_schema捕获；旧“IP类别特判即错误硬编码”也不成立，合法局部解不必采用gold通用方案。旧6126重叠主张未获跨题核验，不据此宣告实际actor泄露。

八方面已覆盖公开规格/版本初态、新断言与风险P2P、替代实现、gold调用者、开发条件、交付恢复、关联暴露。367 P2P全部核状态PASS，未逐项读全部正文。H19修订grader安装RC0，noop 2失败/380通过，gold 382通过；各另1skip/1xfail，不在expected。使用本地wheelhouse、deny_all；pdm.lock/pyproject存在准备改动。实际actor消息/初态/UID/PATH/权限/资产仍unknown，H19不替代A。

唯一优先下一步：任务二私有CPU同base/gold对照标准dataclass D(1)作为BaseModel字段默认值的model_json_schema，并带原IP例控制；核schema、warning和异常code。不跑全仓、不增非IP规格。主审出稿时未读reviewer，独立交叉复核现已完成；本轮未执行项目；审查者已见gold/hidden/旧记录，不可给solver。exclusions/revisions为空，当前成本null。


协调裁定：quality_first，ready_for_probe=false。check4收为unknown，实际actor读写提交范围未验；26/27保持unknown。唯一私有CPU提案核标准库dataclass默认实例的base/gold公共API结果并带IP控制；角色一致不增加运行证据。合法IP类别局部解可接受，不能为迫使采用TypeAdapter扩张为任意非IP新需求。
