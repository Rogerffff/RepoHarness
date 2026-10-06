# conan-io__conan-11560

公开目标是修复Bazel多静态库链接；alwayslink是用户建议路线，不能升格为唯一硬要求。base 345be91a038e。gold只增加逗号和小写 # do not sort；四F2P均要求该注释，其中两项锁空白、正则与shared项容忍空白。历史noop4fail/3pass、gold7pass仅验证生成文本，没有运行Bazel、Buildifier或互依赖双静态库。

| 需求 | 已见验收 | 边界 |
| --- | --- | --- |
| 多库正确链接 | 单库/空档案生成文本 | 核心行为漏测 |
| 顺序保持 | 强制小写保序注释 | 外部重排序条件未证，等价写法未运行 |
| 旧header/主BUILD/build依赖 | 三P2P原断言 | 局部保护，非全域无回归 |

check23/24/25保留具体契约及覆盖问题；27从issue收窄为unknown：未采用alwayslink不能证明gold错误，历史Buildifier源码主张未由本轮外部原件验证。也不能断言该注释在所有流程无效、所有合理替代必被拒，或把本已满足的lib→transitive顺序作为充分新验收。

唯一优先下一步：补清真实失败流程、是否经过重排序及工具版本，再确定行为验收与同条件对照。独立reviewer已完成；封存public_read/初判/delta保留原措辞，最终范围在本卡与record纠正。完整八方面和原件范围见analysis/review。

needs_review/static_review；优先质量处理、ready_for_probe=false，仅development_diagnostic。actual actor输入/初态/权限/导入/资产未知，actual image ID=null。conftest_user只有静态线索，当前可达性未证，不新增排除。没有本轮项目运行或后续执行派发。
