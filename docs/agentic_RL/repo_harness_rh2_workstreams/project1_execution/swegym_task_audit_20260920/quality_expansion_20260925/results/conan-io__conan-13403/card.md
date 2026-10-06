# conan-io__conan-13403

目标是显式选择 autoreconf 所在目录，尤其 build_folder；base `55163679ad1f`。gold新增目录参数并相对source_folder解析，缺省行为方向合理，但把新参数放到旧args之前。合法旧调用 `autoreconf(['--install'])` 会将列表传给os.path.join而在run前失败：这是静态签名/类型推导，尚无CPU复验。

| 需求/旧行为 | 唯一F2P的断言 | 判断 |
|---|---|---|
| 自定义及默认目录 | mock.assert_called_with(autotools,path) | 只核内部调用，未核实际cwd/build绝对路径 |
| configure旧路径、默认命令 | 原configure断言及autoreconf命令 | 有有限保护，0P2P不等于零保护 |
| 旧位置args兼容 | 无断言 | gold静态回归；需独立核验 |

历史noop 1失败，gold 1通过，安装末命令RC0、测试RC1→0；失败为不支持build_script_folder关键字。没有真实GNU工具执行。八方面见封存稿：完整Autotools、唯一测试/helper、旧无参与args=功能调用者、替代实现/兼容边界、开发资产、投影恢复、身份及暴露。内部chdir的对象和位置调用形状无公开依据，等价关键字/recipe参数实现可能被拒；工厂被调用却不进入context也可能漏检。两类反例均未跑。旧abspath反例不成立，测试路径本来已规范。

actor实际消息、初态、权限/PATH/资产unknown，actual image ID=null；历史单测不证明系统autoreconf链可用。合法源码修复可只改autotools.py；conftest_user静态导入线索尚未证明能穿越当前恢复，不添加排除。

建议用途仅development_diagnostic，状态needs_review/static_review。唯一优先下一步：以同一最小私有行为探针对比 base/gold/保留 args 首位的兼容实现，记录位置参数、新目录、实际run时cwd及恢复；优先验证gold兼容性，无需系统autoreconf或全仓。

完整双向表、全部阅读范围与原命令/逐ID状态见 [封存分析](analysis_before_history.md)，历史逐项复核见 [delta](old_findings_delta.md)。独立reviewer已完成，最终分歧裁定见本包报告；未知token/费用为null，无新增排除/修订。

协调限定：回归例是旧非空位置列表；空列表、无参和args=不能概括为全部失败。check26/27 issue基于具体签名与类型推导，非P2P为零或新增运行。质量处理优先，ready_for_probe=false。
