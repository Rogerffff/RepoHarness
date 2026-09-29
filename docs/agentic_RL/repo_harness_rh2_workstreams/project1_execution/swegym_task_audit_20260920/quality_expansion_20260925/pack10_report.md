# pack10 Conan 静态审查

13610、13788均归quality_first，ready_for_probe=false。13610优先明确验收契约；13788优先一项能改变判断的私有CPU对照。分类表示具体问题的处理优先级，不是要求所有题先过CPU或模型门槛。当前actor条件均未知，没有训练或正式评测准入。

| 题目 | 原件支持的判断 | 唯一优先下一步 |
| --- | --- | --- |
| 13610 | 公开日志规范请求末句未完，旧裸-v为verbose，隐藏断言改成status。gold只改None映射，帮助仍把-v与-vverbose写成等价，新增说明不一致可静态证明。 | 明确无参数、裸-v、显式verbose及帮助契约；CPU不能决定该语义选择。 |
| 13788 | 同名host/build锁索引的局部修复有效；普通Requirement.build_require_context=None，而build工具的普通子节点继承Node.context=build，gold却默认查host，有具体回归疑点。 | 私有base/gold root→build T→普通D双profile锁重放，保存实际上下文和失败位置；尚未运行。 |

13610的check26=issue仅限静态帮助回归，其他功能回归unknown；13788的26/27均unknown。不能把缺少测试直接当作gold已回归。13610完整F2P函数已测大部分日志级别矩阵，quiet/help/其他入口才是缺口；非法参数P2P的常量字符串assert无判别力，但TestClient仍要求非零返回码。13788新测试只查tool4.0输出，未直接核tool3.0及锁边；所有选定tool均缺普通依赖，现有9 P2P不覆盖上述风险。

13788用户询问是否禁止同名版本，不构成全局禁止规格；公开双context、不同消费者版本和profile覆盖均有旧代码/测试依据。没有实现形状断言，合理非gold路线保留，未证明普遍无误拒。主审不可变delta的Requirement.context=None简称不准确，review已纠正为Requirement.build_require_context；可变card同步纠正。

| 历史原件 | no-op | gold | 身份边界 |
| --- | --- | --- | --- |
| 13610：pytest -n0 -rA conans/test/integration/command_v2/test_output_level.py | 1failed/1passed，RC1，失败于裸-v首断言 | 2passed，RC0，完整级别矩阵执行 | base0c1624d2dd3b，Conan2.0.3；actual image ID=null |
| 13788：pytest -n0 -rA conans/test/integration/graph_lock/graph_lock_build_requires_test.py | 1failed/9passed，RC1；第二次install成功后缺tool4.0输出 | 10passed，RC0 | basec1b3978914dd，Conan1.60.0-dev；actual image ID=null |

两题历史Python3.10.14/pytest6.2.5，各次安装最后命令RC0，expected无skip/xfail/缺项。历史已知候选的投影/可信恢复及局部分差，不证明任意候选或实际actor资格。git show的base提交内容不是初态未提交差异。未重新运行任何项目。

旧控制面说法均收窄：13610有conftest_user/default_profiles可选入口；13788只有本题已读的tools_locations入口，不能复制2.x的default_profiles结论。实际ignored-file投影、导入及可利用性未知，31保持unknown，additional_exclusions=[]。未沿旧hints、模型或跨题扫描链接扩读。旧“奖励不可学”、P2P数量证明完整性等推论不继承。

独立角色均显式请求gpt-6-astra/high/fork_turns=none；六份初稿封存后才释放历史与交叉材料，后端和OS隔离未独立认证。协调者读两题全部新补丁、关键调用链、角色技术正文、完整review及决定性record字段；不冒称全文复核所有记录附录或所有P2P语义。四份main card/record原稿已归档。见[后续](pack10_followups.md)、[修订来源](coordinator_revisions/pack10_conan/revision_log.json)、[阅读边界](reserve20_coordinator_read_notes.md)。结构/来源校验不认证语义完整性。
