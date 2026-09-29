# pydantic__pydantic-8793

静态结论：needs_review / static_review，仅用于development_diagnostic。base 832225b90672；公开目标是create_model里Annotated+Field+外层省略号仍必填。三个F2P与原例、公开动静模型等价及必填定义一致。

| 需求/旧行为 | 断言 | 结论 |
|---|---|---|
| 单bar及foo/bar/baz必填、元数据保留 | 两完整schema字典 | 历史noop失败、gold通过 |
| 普通类等价必填 | a/b/c的is_required | 有公开依据，noop仅c失败 |
| 真默认/工厂与缺值验证保持 | 部分schema P2P；相关annotated/create_model旧测试未入选择器 | 覆盖有限，非已证gold回归 |

根因是fields.py单FieldInfo复制分支直接写Ellipsis，绕过构造时Undefined归一化；gold只修改该分支。合法非gold实现未运行，不能保证普遍无误拒。旧记录“只改is_required必定破坏model_construct”证据不足：该调用者也按is_required门控；_attributes_set保留Ellipsis本身也不证明gold不正确。完整映射及边界见封存analysis与old_findings_delta。

八方面均已按范围检查：公开目标/版本、原始初态、全部新断言及风险P2P、替代实现、gold与调用者、开发条件、交付/可信恢复、关联与暴露。其余P2P只核身份状态；实际actor消息、工作树、权限、解释器与资产unknown。历史修订grader在本地wheelhouse、deny_all下安装RC0，noop 3失败/377通过，gold 380通过；各另1skip/1xfail，均不在expected，364 P2P全部PASS。原先依赖安装失败主张不能沿用为此H19事实；也不能拿H19替A资格。原status已有pdm.lock/pyproject准备改动，git show不是工作树diff。

唯一优先下一步：任务二以正式actor身份核初态/导入来源，执行原例及缺值验证（Python3.8用typing_extensions.Annotated）。保留覆盖问题；不增加源码路径排除，不改题/评分。私有审查已见gold/hidden/旧记录，不可输入solver。主审出稿时未读reviewer；独立交叉复核现已完成。当前成本null。


协调裁定：有条件静态开发候选，ready_for_probe=false。check4收为unknown，保留计划NON-TEST边界和历史源码投影的正证据，实际actor可读/可改/可提交范围未验。26/27继续unknown；唯一优先项为真实actor公开原例及缺值验证。review补核test_config.py:788是test_partial_creation_with_defer_build内create_partial helper，非生产with_config调用；该旧测试未在历史选择器内，不新增必跑门。
