# Conan 正式 CPU 对照输入准备

2026-10-03。**六题共54个对照入口已固定：6个noop及48份完整原候选补丁。** 48份补丁均核原SHA，在隔离临时目录按各自公开base通过`git apply --check`和实际应用；应用后的Python文件通过AST解析。此检查没有导入项目、运行测试、导出FrozenPatch或评分。当前等待正式consumer和部署回执，不以静态检查代替CPU验收。

| 题号 | 完整矩阵 | 用于接续 |
| --- | ---: | --- |
| [13230](tasks/conan-io__conan-13230/card.md) | 3 | `publish-swe-conan13230-20261003-v1` |
| [14177](tasks/conan-io__conan-14177/card.md) | 15 | `publish-swe-conan14177-20261003-v1` |
| [13403](tasks/conan-io__conan-13403/card.md) | 21 | `publish-swe-conan13403-20261003-v1` |
| [11594](tasks/conan-io__conan-11594/card.md) | 3 | `publish-swe-conan11594-20261003-v1` |
| [15422](tasks/conan-io__conan-15422/card.md) | 8 | `publish-swe-conan15422-20261003-v1` |
| [12397](tasks/conan-io__conan-12397/card.md) | 4 | `publish-swe-conan12397-20261003-v1` |

完整输入及逐候选静态回执保存在忽略目录`runs/category2_repair_20260929/conan_cpu_20261003/formal_candidate_preflight_20261003_v1/`，原件未修改。逐题公开base、完整F/P和预期reward以已提交`publication_request_20261003_v1.json`中的固定修订单为准。现有历史运行只在相同材料及范围内复用，不将54个静态入口计作54次CPU通过。

正式交付后使用同一发布代码的`rh2/scripts/replay_grade.py prepare/run`，每个新组合fresh prepare，候选经真实FrozenPatch导出、可信评分投影与SWEGradingManager评分。所有Docker经cpu-a作业槽，每作业内串行；不热改release、不重绑旧prepared或旧FrozenPatch。回执先核实际材料／代码／部署身份，再ack及清本题活动请求；题级缺口不会因此自动清空。

15422需特别核三份完整候选与此前源码投影的差异：coder_a3还改README、非官方测试及诊断脚本；deepseek_a1还改非官方测试；deepseek_a4还改本题官方测试文件。正式入口保留完整原patch，不能直接拿私有诊断的presets.py投影冒作完整评分。当前FA契约由可信投影排除官方测试文件改动，并在ignored entries留证；不能沿用legacy hygiene逻辑推断为自动reward0。其余非官方文件是否实际重放、测试收集是否受影响，仍核正式artifact／projection／日志，静态检查未证明。

CPU结果核新增节点、分组、参考完整性、正负对照、候选／grader镜像和脚本身份、完整日志与清理。13403、14177各候选覆盖不同根因或替代正确修法；如后续缩减矩阵，须说明等价覆盖依据，不只挑最容易的三项。15422保留CMake消费兼容性边界，分开记录完整原候选reward与源码语义。完成对应非作者窄核后才向GPU交接该题；不等待整仓六题齐备。
