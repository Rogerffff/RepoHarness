# 根验收：Pydantic 五题有界复核

结论：未发现推翻当前分类或唯一优先后续的技术证据。5662、8793保留有条件静态开发候选；6043、8316、9066保留quality_first。五题actual actor仍unknown、ready_for_probe=false。本轮只读原题、完整gold/test patch、下述决定性源码、最终短卡/pack报告和定向原日志；未import/运行项目、测试或新实验，未核全量P2P、配方哈希仪式或actor环境。

路径约定：`P<ID>`为`runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-<ID>/base/`，`G<ID>`为同批`private/pydantic__pydantic-<ID>/`；`L<ID>`为`runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-<ID>/`。均为仓库相对路径。题面来自各public目录的user_prompt.txt。

- **5662：候选成立，比较协议验证需保留一般matcher真/假。** `P5662/pydantic/main.py:540–561`原非模型直接False；gold只将该分支变NotImplemented，模型origin/type、字段、private检查保持。反射比较应把原模型交给对方的`__eq__`；一般matcher返回False时也不能被强制转True。唯一新增`test_equality_delegation`只验ANY，故ANY特判可漏检；这证明覆盖缺口，不证明gold错误。`P5662/tests/test_main.py:120–124,1985–1991`已有dict不等，1965–2052有模型/private/generic护栏，不能再称全是模型之间比较。保持actual actor公开ANY、真/假matcher、dict/object验证为同一步；若观察不等操作，区分`__ne__`与`__eq__`，不把`m != ANY`结果未经执行写成事实。
- **6043：公开契约分歧有原件支持，但不能据此宣告gold违规。** `P6043/docs/usage/models.md:958–966`明确schema保字段序；`tests/test_json_schema.py:101–118`原ApplePie声明Snap在Crackle前并显式验序。新题面要求best-effort递归排序，test patch反转该断言。gold递归所有dict，list只递归元素不重排，符合避免改变tuple/default数组语义的合理边界。`pydantic/json_schema.py:1594–1601`与`pydantic/type_adapter.py:366–374`批量wrapper后追加$defs/title/description；非字典序不等于不确定。先定properties及最终wrapper范围合理；唯一一层验序不足以验证递归，但不能靠隐藏新断言替代公开契约裁决。
- **8316：A1变化是静态事实；旧key工作流与兼容要求分开。** `P8316/pydantic/alias_generators.py:42–44`在大写/数字间加下划线；gold只保小写/数字规则，A1由a_1变a1可直接推出。`pydantic/_internal/_generate_schema.py:946–973`把生成值写入validation_alias/serialization_alias；`pydantic/config.py:319–325`亦公开说明两端作用。故风险有明确调用链，不只是缺测试。尚无同例base/gold公共API运行，且数字兼容承诺未裁决，仍不能记为已证违规回归。`config.py:131–134`的populate_by_name只接受原字段名及实际别名，题面HTTPResponseCode附注不支持任意key归一化。维持一个私有A1别名入参/导出对照加HTTPResponse控制；不与独立actor资格混同。
- **8793：必填根因及候选分类成立；不要把局部修复扩写为所有default优先级已证。** `P8793/pydantic/fields.py:184–188`构造时将Ellipsis归一Undefined，375进入merge，401–407单FieldInfo复制分支却直接覆盖default；519据Undefined且无factory判断必填。`_internal/_generate_schema.py:1077–1078,2077–2084`据此包默认值，因此schema之外的缺值ValidationError是有因果依据的公开验收。gold对Ellipsis丢弃该override，保留复制对象原default；原题Field无具体默认值时解决根因，但并非把任何内层真实default重置为Undefined。已有`tests/test_annotated.py:152–176`约束default_factory与复用，却不在历史json_schema单文件selector。保持原例+is_required+缺值/有效值的actual actor一步；未测组合不升级成gold已错。
- **9066：dataclass配置异常链成立，但仍需私有对照确认回归。** gold的serializer短路之后，普通dataclass实例走`TypeAdapter(type(dft), config=config.config_dict)`。`P9066/pydantic/type_adapter.py:101–104,193–204`对dataclass且config非None抛直接PydanticUserError(code=type-adapter-config-unused)；`_internal/_config.py:87–91,268–278`正常空配置仍为dict。`errors.py:87,131`说明SchemaGenerationError是该异常的子类，gold的子类catch捕不到父类；`json_schema.py:1011–1019`也仅捕SerializationError。`_internal/_generate_schema.py:1474–1564`生成普通dataclass schema未给原类安装serializer，未见能消除此路径的本地guard。基线`json_schema.py:1996–2001`直接交core转换，本轮未运行/读取core Rust证明基线D(1)成功，故保留“具体未运行风险”。`json_schema.py:999–1009`解释为何提案必须用实例default而非default_factory。维持D(1)私有base/gold对照、带原IPv4控制；合法IP类型局部修复不必照搬gold通用方案。

原日志抽查支持已有局部正证据（以下文件均在L<ID>/<kind>/eval_logs/；只核指定失败/通过与RC，不将其当actor认证）：

| ID | no-op日志及行 | gold日志及行 |
| --- | --- | --- |
| 5662 | `evallog_replay-er19-pyd1-pydanti_65d41641.eval.log:3107–3114,3131` ANY失败、RC1 | `evallog_replay-er19-pyd1-pydanti_982ff19d.eval.log:3158,3167` ANY通过、RC0 |
| 6043 | `evallog_replay-er19-pyd1-pydanti_c5499389.eval.log:2975,3285–3286,3309` by_alias失败、RC1 | `evallog_replay-er19-pyd1-pydanti_1041cb4c.eval.log:3017,3332` 通过、RC0 |
| 8316 | `evallog_replay-er19-pyd1-pydanti_02c87450.eval.log:985,1027` CAMELToSnake失败、RC1 | `evallog_replay-er19-pyd1-pydanti_16828e54.eval.log:1005,1029` 通过、RC0 |
| 8793 | `evallog_replay-er19-pyd1-pydanti_8fa63264.eval.log:1071–1076,1250` 三新增失败、RC1 | `evallog_replay-er19-pyd1-pydanti_cec5f167.eval.log:1090–1092,1105` 三新增通过、RC0 |
| 9066 | `evallog_replay-er19-pyd1-pydanti_a93f65ea.eval.log:1065–1068,1234` 两IP默认值失败、RC1 | `evallog_replay-er19-pyd1-pydanti_3ef85fd4.eval.log:1101–1102,1115` 两参数通过、RC0 |

未发现需要回改协调者卡片/record的阻断项；上述8793措辞限界和5662假matcher均已被当前后续覆盖或明确保留为边界。
