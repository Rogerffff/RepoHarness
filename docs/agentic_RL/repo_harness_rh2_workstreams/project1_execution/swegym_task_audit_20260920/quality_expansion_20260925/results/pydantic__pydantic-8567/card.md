# pydantic__pydantic-8567 静态质量短卡（2026-09-25）

目标是PlainSerializer在PlainValidator两侧均生效，保留plain验证短路；base `8060fa1cff96`。结论 **needs_review**，仅development_diagnostic：输出断言偏弱，gold新增无条件内部schema生成有具体兼容风险。

|需求|决定性断言/源码|判断|
|---|---|---|
|两顺序得到正确序列化值|新foo/bar仅isinstance(str)|只验类型，未验'0'/'1'|
|题面JSON输出及内部bool值|新增只model_dump|缺测|
|plain短路、with-info/no-info|旧plain/typing_cache/field_name|验证覆盖，组合serializer未验|
|未知底层类型仍能由plain接管|gold新增handler(source_type)|构建异常路径待base/gold对照|

八方面：公开目标/版本；全部新增import、局部helper及两断言；唯一F2P和相关P2P；非gold信息保留路线；gold与Annotated包装/serializer调用链；Python/core/pytest与公开dump验证需求；源码投影/单测试文件恢复；授权私有暴露和用途。语义抽读plain、wrap、nested、runs_before_field_validators、typing_cache四分支、plain_field_name及评分外serialize83–146；其它P2P仅核日志。未读core实现或运行未知类型。

09-19pydantic-install-v1两安装RC0；noop bar=True导致目标失败，gold通过，158 P2P逐身份PASSED；165 collected/parsed，gold165 passed，无skip。gold只投影functional_validators.py，历史初态有pyproject/lock改动。actual actor消息、工作树、权限/import、依赖资产及image ID仍unknown。

handler委托能保留serializer，但旧plain不生成内schema；未知类型可能因此在构建时抛错。无serializer时的warning/输出变化也未测。旧记录的弱断言与调用范围发现确认；覆盖不足不能直接把check26判为已证gold回归，增强P2P也不自动准入。

唯一优先下一步：私有CPU环境对未知底层类型+PlainValidator做base/gold构建对照；此诊断不认证actor开发资格，不向solver提供gold。未执行/派发任务二。独立交叉复核与协调收口已完成，详见[复核](review.md)。完整表与条件见[初判](analysis_before_history.md)及[差异](old_findings_delta.md)。

协调收口：只验str类型未覆盖JSON和值；无条件handler(Custom)新增构建失败路径是具体待验证风险，优先私有base/gold对照，check26/27不升级已证回归。 原主审card/record按完成hash归档；封存初判、delta、review未回改。
