# Project-MONAI__MONAI-5932

静态候选，`needs_review/static_review`，仅供 `development_diagnostic`。base=`3c8f6c6b94ba26f8c9df5b7c96089494de6f69cb`。公开ConfigParser同式短长引用应求值4；gold按长度降序替换。允许一次完整匹配等非gold算法，没有内部实现断言。

| 需求/旧行为 | 断言与结果 | 限制 |
|---|---|---|
| A/A_B前缀引用独立 | F2P substring_reference_0，assertEqual 4；历史fail→pass | 只有短在前的两引用 |
| 相对/缺失/宏/对象/函数等旧行为 | 全14 P2P语义已读，历史均pass | 不等于多前缀边界覆盖 |
| 当前actor能开发 | 公开API与窄测试入口明确 | 实际消息/工作树/权限/导入仍unknown |

八方面均有范围记录：题意明确；静态版本绑定；全部新断言与14旧项；替代实现/误拒未运行；gold及直接调用者已查；开发资源有需求表；历史恢复/投影可核；私有暴露与用途单列。全表、源码区段和未读范围见不可改写前稿。

授权09-19 ledger3/4与原日志：`pytest -rA tests/test_config_parser.py`，15 collected；noop的SyntaxError正由短替换破坏长ID引起；gold15pass，安装最后RC0、测试RC1→0，无skip/xfail。历史grader初态有删除MetricsReloaded依赖的diff，不能称干净base；actual image ID=null。当前actor条件不由历史grader代替。

主要问题是覆盖窄：仅反转出现顺序的坏修法能过现例，却在长在前时失效；这是静态漏测推断，不是gold回归。旧记录的“无多进程”已纠正（TimedCall使用spawn/Queue）；跨题关系与skip/parser链仅为旧主张、未核；不继承ready_for_probe。未读reviewer，无reviewer结论。

唯一优先后续：任务二在真实actor记录初态/导入来源，运行公开数值复现和窄旧测试，区分目标失败、skip与环境问题。未修改题目/评分，additional_exclusions=[]、revision_refs=[]；审查者看过gold/隐藏测试及本题旧记录，材料不得交solver。
