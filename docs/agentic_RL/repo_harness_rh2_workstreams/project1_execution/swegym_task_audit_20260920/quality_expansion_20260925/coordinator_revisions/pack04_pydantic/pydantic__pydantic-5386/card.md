# pydantic__pydantic-5386 静态质量短卡（2026-09-25）

目标是在类定义阶段取得子类全部字段；base `6cbd8d69609b`。静态结论为 **needs_review**：隐藏测试固定了公开题面未命名的新钩子，却未在钩子内读取字段。适用 development_diagnostic，尚不作训练/正式评测批准。

|需求|决定性断言|判断|
|---|---|---|
|定义时读取当前字段及examples|MySubModel无字段，calls列表不读model_fields|核心漏测|
|普通hook及kwargs仍工作|新calls轨迹、旧custom_init_subclass_params|相关覆盖|
|新名__pydantic_init_subclass__及super协议|test.patch精确调用|公开没有唯一命名依据，存在替代接口误拒机制|

八方面已查：公开目标与语法草图；精确base；所有新增helper/断言和唯一F2P；合理替代及漏测；gold元类→字段设置→父类hook调用链；开发所需Python/core/pytest；gold源码投影及本测试文件恢复；授权私有暴露及用途。语义抽读5项P2P：custom_init_subclass_params、三项class_kwargs、field_order；其它P2P仅核身份/日志。多继承、泛型、回调读字段未运行。

09-19 `pydantic-install-v1` 原运行：两次安装RC0；noop目标失败，gold通过；106 P2P均有PASSED记录。159 collected中gold121 passed/29 skipped/9 xfailed；parser116不等于缺失expected。历史初态pyproject保留变更，gold只投影main.py。实际actor消息、HEAD/status/diff、权限/import、资产及image ID仍unknown，不以grader资格代替。

gold字段就绪路径静态合理；complete_model_class可False，不能把“fully initialized”解作一定可实例化。没有证据把未测边界判为已发生gold回归。旧记录固定命名及空字段发现确认；旧联网阻塞仅对修订grader过时，所谓无泄漏与自动同簇不采纳。

唯一优先下一步：规格维护方明确字段就绪公开接口及可接受实现范围，再处理字段断言缺失。本轮未修题、未执行/派发任务二。reviewer未读取，尚无本角色可报告的复核结论。完整双向表、执行条件和阅读范围见[初判](analysis_before_history.md)，旧主张对照见[差异](old_findings_delta.md)。
