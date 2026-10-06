# Conan 定向后续提案

全部为静态审查的证据请求，未执行、未派发、未改原题/测试/gold/评分。运行与环境工作由任务二Claude B负责。私有gold及隐藏验收不得进入独立solver上下文，也不能借此认证实际actor、训练或正式评测资格。

## 11560：先补清链接和排序流程

公开行为目标是同包多个静态库可正确链接，alwayslink为建议路径。先定位真实失败如何触发：生成后是否经过外部排序、具体工具版本及库符号依赖是什么。不能从gold注释倒推Buildifier一定参与，也不能要求solver只采用用户建议方案。

在条件明确后，行为验收才可比较base/gold/建议方案是否恢复链接，以及精确注释要求是否误拒等价行为。现有单库与空档案不足以支持该结论；base本已满足lib在transitive前，单独检查这一顺序没有判别力。当前不排新的CPU、盲解或全仓任务，不追未授权外部源码，也不修改公开题面。

## 12397：一项私有配置键诊断

在匹配base依赖的私有CPU副本中，比较base、gold和仅向objcpp_link_args添加libcxx的错误候选。使用原Apple cross配置以及公开Linux Clang14/libc++ native配置，各自生成Meson配置文件；按section和完整键读取c_args、cpp_args、c_link_args、cpp_link_args，并明确与objc/objcpp区分，记录实际值和候选身份。

分别观察原隐藏断言和正确键断言是否接受错误候选；不要把静态预期写成已取得正式分数。该候选可能满足原cpp子串，却让真实C++链接键缺flag，这是具体待证机制。旧cpp_args断言曾可借objcpp_args匹配，不应把旧断言未含stdlib当真实cpp输出证据。ABI宏保持编译用途，不能把所有cpp_args机械复制到链接；不为未证等价的flag重排增加硬要求。

生成物诊断不要求安装Meson/Clang或真正链接，无需下载/模型/GPU/全仓。真实公开package/test_package链接及actor依赖仍为后续未决项；若在实际actor入口做公开生成验证，必须另采消息、初态、权限、解释器/导入和RC，不能混用私有候选来认证solver。

## 13403：一项私有API与cwd诊断

在真实临时source/sub和绝对build目录中使用匹配base的Autotools，令recipe.run只记录命令与os.getcwd()以代替系统autoreconf。比较base、gold与保持args首位/新增目录keyword的兼容实现，记录旧非空位置列表autoreconf(['--install'])、args=关键字、无参、相对子目录及绝对build目录，验证run时cwd和退出后的恢复。

预期base不支持新目录keyword，gold把旧非空位置列表当路径并在join阶段失败；实际结果和预期分列，不能归为环境失败。空列表和默认调用不能泛称全部破坏。只调用chdir工厂却不进入context的错误行为可由同一cwd记录识别；内部首参身份或位置调用形状本身不构成公开目标。

该诊断可验证签名兼容性和上下文行为，不证明GNU工具生成configure成功；无需完整GNU工具链或全仓。P2P=0也不能抹去唯一F2P内已有configure/default断言。更广make/install、异常恢复及当前控制面完整性继续保留未核范围，不机械扩仓或新增排除。
