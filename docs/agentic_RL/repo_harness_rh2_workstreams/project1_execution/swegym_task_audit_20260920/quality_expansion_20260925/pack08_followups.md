# Pydantic 定向后续提案

全部仅提案；未运行、未派发、未改原题/测试/gold/评分。任务二Claude B负责运行。私有gold、隐藏断言和审查结论不得进入独立solver。

## 5662：actual actor公开比较协议

在真实actor入口采集实际消息、HEAD/status及RC、解释器、pydantic/core版本和源码路径，再用公开API验证模型左侧ANY，以及返回True/False的一般matcher并记录对方收到原模型。普通object/dict不等和公开equality窄选择作为同一验证的护栏。无需为静态已明确的ANY特判漏测另设私有CPU坏解实验，也不扩大全仓或性能指标。验证开发可用性不自动改变正式验收或证明训练收益。

## 6043：先定排序契约

规格维护者决定properties是否继续保留字段声明序，以及递归排序是否包括models_json_schema/TypeAdapter.json_schemas的最终外层。保序与变更旧约定均应在公开要求明确，不能让唯一隐藏断言代替决策。之后设计根、嵌套、$defs、list内映射及批量入口的键序观察，禁止用json.dumps(sort_keys=True)掩盖结果；保留prefixItems与默认数据数组的语义。当前不修改评分、不先排CPU，运行不能决定契约优先级。

## 8316：单一私有数字别名对照

匹配base/core条件的私有CPU副本中对照base/gold，直接to_snake观察HTTPResponse与一个代表A1，并定义使用alias_generator=to_snake且含A1字段的模型，核旧a_1 key能否填充及model_dump(by_alias=True)输出。记录源码、解释器、候选身份、实际结果与预期，区分API输出变化和用户工作流影响。无需再堆API2/HTTP2同类输入；若旧key受损，由维护者裁定是否应保兼容。此私有对照不混入solver上下文、不认证actual actor；未来actor公开入口另采。无全仓/网络/模型/GPU需求。
