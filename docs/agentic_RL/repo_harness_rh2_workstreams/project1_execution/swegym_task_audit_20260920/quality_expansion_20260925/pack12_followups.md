# pack12 后续建议（未执行、未派发）

任务二由Claude B负责；两题各保留一个当前优先步骤。历史grader和私有参考对照不替代实际actor开发资格，gold/隐藏测试/本审查资料不得进入独立solver上下文。

8793：以实际actor入口记录真实消息、HEAD/status/diff及准备阶段/RC、解释器与pydantic导入位置和必要权限，执行公开create_model的foo/bar/baz原例。Python3.8用旧公开测试已有typing_extensions.Annotated；联合检查required顺序/元数据、三个字段is_required及缺bar/baz时ValidationError，有效输入仍可接受。相邻默认值/Annotated旧约束按需要选取，不设全仓绿或内部哨兵字面量门。当前不另排is_required替代补丁或内外default歧义CPU实验。

9066：在同条件私有base/gold中，以标准库dataclasses.dataclass定义D(x:int)，BaseModel M定义d:D=D(1)，调用M.model_json_schema；另带原题IPv4默认值例控制。使用实例默认值而非default_factory，后者默认schema不会调用。保存原D是否具有__pydantic_serializer__、schema中default、warning、异常类型/code及RC，连同源码/解释器/镜像/初态身份。预期合理旧行为为default={'x':1}；只有base成功而gold抛type-adapter-config-unused，才确认26新增回归。若不成立，记录实际guard/类型生成路径以撤回或收窄推断。无需全仓、网络、GPU或模型；不新增任意非IP题目规格。
