# 储备 Conan 首包：三题静态复核完成

11560、12397、13403完成三类独立角色和协调收口，21份逐题产物与9份封存初判齐全。三题均优先处理质量问题；needs_review/static_review、development_diagnostic，ready_for_probe=false。[输出校验](pack06_output_verification.json)及[六份修订来源校验](pack06_revision_provenance_verification.json)单列。

| 题目 | 决定性结论 | 唯一优先下一步，未执行或派发 |
| --- | --- | --- |
| [11560](results/conan-io__conan-11560/card.md) | 四F2P强制小写保序注释，却无同包互依赖双静态库或链接行为。alwayslink是用户建议，不能仅因gold未采用就判错误。 | 补清原失败流程及重排序条件，确定行为验收；目前先不排CPU。 |
| [12397](results/conan-io__conan-12397/card.md) | 无键首约束的cpp_link_args子串可命中objcpp_link_args；仅修后者可能骗过断言，Linux native也未覆盖。gold局部方向正确。 | 私有CPU配置键诊断，比较base/gold/仅修objcpp错误候选的Apple与Linux生成物。 |
| [13403](results/conan-io__conan-13403/card.md) | gold把新目录参数放到旧args之前，旧非空位置列表被交给os.path.join，破坏合理API调用。mock还只查工厂调用，未观察cwd。 | 同一私有Python行为诊断，核位置参数、目录、run时cwd及恢复。 |

11560的check27从issue收窄为unknown，纠正前稿把建议属性当硬契约的措辞；强制精确注释与核心行为缺口仍在23/24/25。两断言锁空白，另两项容忍空白，不能统称逐字符。历史pilot引用Buildifier源码支持保序机制，但本轮未读外部原件或证实它参与用户流程；不说注释必然无效、不把alwayslink与保序当等价。base本已保留库输入顺序，简单检查lib在transitive前无法成为充分新验收。

12397的后缀匹配由公开读者和主审独立指出，reviewer在cross-review后承认初稿遗漏并回源码确认，时序保留。旧cpp_args断言可匹配添加libcxx前复制的objcpp_args，所以不能断言旧测试必失败。其他c/objc键也应精确区分；不同flags顺序是否等价仍未知。root补check32，并将27局部pass收窄为整体完整性unknown；26未发现新增回归。conan new -s在此base是--sources，不能当settings使用，但公开根因仍清楚。P2P被test.patch改写不自动使其失效。

13403的26/27 issue基于具体签名与类型推导，尚无本轮CPU实测；非空位置列表、空列表、无参及args=分开。P2P虽为0，唯一F2P仍包含旧configure和默认autoreconf断言，不能说零回归保护。真实chdir首参未用，固定对象/位置形状可误拒等价调用；工厂被调用也不等于进入context，错误候选未运行。gold在Linux可接受绝对build目录；原abspath反例不成立。

历史原命令分别为三个指定文件的pytest -n0 -rA：11560 noop4fail/3pass→gold7pass；12397 1fail/2pass→3pass；13403 1fail→1pass。所选expected无missing/skip/xfail，安装末命令RC0、test RC1→0，actual image ID均null。root直接核目标失败和逐ID汇总；两独立角色还核原账本/投影/恢复及完整新增断言、全部所选P2P。生成文件/mock测试通过不证明真实Bazel/Meson/Autoreconf工具链可用；原资源字段不换算actor成本。阅读范围见[协调记录](reserve20_coordinator_read_notes.md)。

六份主审card/record先核交付SHA并归档，见[修订链](coordinator_revisions/pack06_conan/revision_log.json)，初判/delta/review及原件未改。五角色均显式gpt-6-astra/high/fork_turns=none；不声称后端验真或OS隔离。三题旧conftest_user线索缺当前投影/恢复/权限证明，31unknown、additional_exclusions=[]。actual actor各项仍unknown，私有审查暴露单列，29与40不因流程封存变pass。

[后续提案](pack06_followups.md)只有一项契约澄清、两项有具体判别目标的私有CPU诊断，均未执行或派发；任务二由Claude B负责。至此新增6/20、累计18/32完成静态收口，继续剩余冻结任务，中期在新增8–12题完成后汇报。
