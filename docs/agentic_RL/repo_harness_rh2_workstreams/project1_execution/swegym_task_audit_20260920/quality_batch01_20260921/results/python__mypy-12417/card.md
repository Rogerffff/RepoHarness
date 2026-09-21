# python__mypy-12417

**建议：needs_review / static_review；仅用于 development_diagnostic。** base `47b9f5e2…`（mypy0.950，Python3.10）的公开目标是未定义类名 `case xyz():` 不再触发内部断言。材料、配方、原始账本与日志已核；私有主审见过gold、隐藏测试和获准历史，未来solver不能接收本卡。

| 要求/旧行为 | 检查与结论 |
| --- | --- |
| 消除崩溃并保留未定义名错误 | F2P覆盖位置/关键字捕获；原例零捕获由共同入口支持，未单独实跑 |
| 无效分支的恢复输出 | F2P另要求subject/capture为Any及两条捕获附带错误；公允性待对照 |
| dataclass位置捕获与错误 | 三P2P覆盖精确字段类型、禁用match_args、init=False排除及合法后续捕获；两端均通过 |

历史真实RH2中no-op在目标断言崩溃、三P2P通过；gold四项通过，无缺席或跳过。实际Python3.10.14、pytest8.3.2、2CPU/4GiB、离线安装；派生配方仅加入setuptools72.1.0、wheel0.43.0、packaging24.1构建wheels。grader成功不证明agent/54321的激活、权限、安装或真实消息已经验证。

公开需求、版本、全部七条新增输出、runner/stub、三个P2P及dataclass插件、gold与恢复调用链已查。未知引用回退Any确有源码惯例；某些无效类模式走early_non_match跳过分支也有旧测试依据。主Name错误属于合理兼容要求，五条附带输出在原先崩溃入口没有已验证的旧契约。因此保留疑似过严约束，未认定误拒；旧报告“完全合理解已被判零”“近乎唯一实现”的口吻超过证据。未发现已证实错误解获分或gold回归。

交付侧实际恢复的只有官方`.test`文件，gold源码成功投影；其他已读同文件用例并未执行。额外排除保持空。跨题谱系、真实可见资产泄漏、重复稳定性、来源runner对照及模型能力未验；公开traceback本身不算未来答案泄漏。独立reviewer已给出意见，见下述补记。

唯一优先CPU：同配方对照base、gold、None时调用early_non_match的实现，以及保留current_type的实现，运行公开原例、隐藏两捕获输入、三P2P及两项既有无效类模式测试；同时核正常错误、分支行为与RH2得分。只有替代解保留公开/旧行为却因附带输出落败，才形成窄误拒证据。本轮未执行CPU，未修改原题。完整映射及证据见同目录前稿，历史纠正见old_findings_delta.md。

复核收口：独立review补入PatternType(current_type,current_type,{})候选，预计仅改变subject reveal；主审early_non_match预计跳过body。采纳四实现对照和后续分支观察，均未执行，不登记误拒。16963较新base含本guard的初判暴露已披露。 详细依据与处置分歧见 review.md；未回写封存前稿。
