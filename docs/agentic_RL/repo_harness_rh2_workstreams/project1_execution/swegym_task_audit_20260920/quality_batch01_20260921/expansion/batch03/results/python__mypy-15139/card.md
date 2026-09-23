# python__mypy-15139

建议 `needs_review / static_review`，仅供 `development_diagnostic`。base `16b936c15b074db858729ed218248ef623070e03`。题目要统一类对象在错误与reveal note中的显示；**官方通过只能证明赋值错误的小写分支，gold仍未修改reveal打印器。**

| 需求/旧行为 | 关键验收 | 覆盖与证据 |
|---|---|---|
| 3.9现代拼法 | `testTypeLowercaseSettingOff`要求 `type[type]` 赋值错误 | 原NL真实Type/type差异；GL通过，F2P1/P2P0 |
| 原题reveal与错误一致 | 未加入reveal断言 | gold只改messages；types.py:3188仍固定Type，原例CLI待验 |
| 大写开关/旧版本兼容 | 无评分回归 | 公开options政策、Type[Any]赋值旧用例支持窄回归；同文件8条容器测试不能保护Type分支 |

八方面已查：公开题面及选项政策；精确base/test/gold；全部新增断言和data/testcheck/helpers/default fixture链；合理替代与精确输出争议；错误/reveal/constructor/消歧调用者与公开旧例；历史安装、角色与开发需求；官方恢复、投影及计分；本题关系依据与审查暴露。未查全仓回归、真实actor、重复稳定性、可见Git/资产、模型轨迹、独立来源runner。公开包与静态prompt不是实际消息/容器验收。

历史真实RH2：install_wave1派生镜像仅COPY离线wheels与ENV，仍原spec安装；原日志证实editable安装成功。no-op/gold均执行1节点、解析1键、参考1项，无missing/skipped，reward0/1；gold rc0。grader为54322，补丁apply为54321，不能代填正式actor条件。本地wheel payload及目标机镜像可用性未验。

历史差分纠正“题面没写开关就无法从公开材料知道规则”、错误的reveal输出转述及“8条容器测试能堵Type无条件小写”。主要覆盖/gold疑点维持。没有执行反例或证实误拒；独立复核已完成，协调者已收束。恢复仅test-data/unit/check-lowercase.test，additional_exclusions=[]。

唯一优先下一步：在验证导入来源的base/gold上运行原题三行CLI，并保留同条件官方单case得分。若gold仍混用Type/type，按公开目标修订验收与参考解，另存版本。完整映射、原日志行号、开发需求及未查范围见[初稿](analysis_before_history.md)，旧结论逐项见[差分](old_findings_delta.md)。审查者已见隐藏测试/gold/历史，产物不得交solver。

协调者收束：暂不优先普通能力探针，先做原例base/gold诊断。固定grader语义对照可先于正式actor资格；含预期类型诊断的CLI非零退出不是环境失败。

独立证据与分歧见[最终复核](review.md)。后续1.4公开base含10174的关键修复排序，15184还含15139小写分支；仅证代码包含，未核完整Git谱系或实际solver可见性。
