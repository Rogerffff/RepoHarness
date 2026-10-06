# MONAI5932：新测试补丁入口的独立实施复核

2026-09-30，根线程复核。**可以进入本题的确定性 CPU 验收；尚未宣布题级修复通过。** 实现者为 `d6_monai_implementation_0930`（GPT-6.1 Sol／high），根线程没有参与这四个生产文件的编写。

## 结论依据

- 已读四个生产文件的完整差异、注册材料、增量补丁与新增测试。新操作限定 MONAI5932、`tests/test_config_parser.py` 和一个精确的新 P2P；原 mypy 操作保留。
- 正式 loader 从来源材料和两份固定 SHA 注册表重建有效材料。父摘要核对时还原原 `test_patch`，因此不能用新补丁冒作来源原件。原/有效补丁、公开身份、base 文件、参考清单和来源身份均有校验。
- 有效补丁是原补丁加一个长引用在前的行为断言；断言检查实际值为 4。依据包含公开题面、base 已支持的另一顺序以及已实测的退化，不依赖 gold 的实现细节。原方法/断言 AST、原 F2P、14 项原 P2P 和来源 pytest 文件命令保留。
- actor 和 replay 使用同一 spec builder，新增文件沿既有可信恢复/保护路径处理。材料身份进入资格与诊断；旧材料的资格和分派不能混用。评分算法、完整 baseline 比较、Git 初始化及权限边界没有变化。
- 根线程重新核对 670 个实际文件与作者清单，随后复制到独立冻结目录。作者清单的列表格式被转换成既有运行工具使用的按路径映射格式，所有 SHA/长度重新核对，不改文件内容。
- 根线程重算新版对上一版有效材料的差异：只改变 MONAI 一题的 grading/environment，另外 215 行相同；public/validation 全部相同。两道已验 mypy 的注册摘要、材料身份及评分脚本保持原样。

## 验证范围

作者最终 8 个定向测试文件共 **146 passed**，Ruff 通过。原补丁组合、真实 Git 应用、错误父摘要/补丁/文件/参考拒绝、受保护文件恢复、actor/replay 相等、旧新资格拒绝和原 mypy 兼容均有对应记录。根线程审查这些测试和原始命令/退出记录，不把本机局部脚本检查当作容器中的项目运行。

历史失败日志保留：fixture 误选联合类型、自证字段假设，以及新测试误以为 `SKIPPED` 必然判失败，均已更正。来源 SWE 规则中 `SKIPPED` 不入计分桶，本片不改变该语义；本题 CPU 验收额外要求全部 16 个精确参考真实执行、无缺席或跳过。

## 冻结和执行边界

- 代码：`runs/category2_repair_20260929/frozen_d6_monai_v1/code_v1/`，670 文件。
- 根代码清单 SHA：`cec560539ecff8778fc06f820a7f804f6e6733287c02b7d8340513321e5b5c82`。
- 新 producer manifest SHA：`657efcd6f818608c01b7665fd80bc2b72bb1ce91c11ad952456273a2bf2c55c6`。
- 新注册表 SHA：`bde280944e5913395fab30b850e53efceb12455bcc83205a9d152d3882e7d63c`。
- 新机器已逐文件核代码 670 项和本批运行输入 16 项；MONAI 镜像固定 digest 与历史 image ID 相符。

后续只占一个 actor/grader 槽，执行 noop／gold／reverse 三方评分，以及真实 CC 固定公开命令后同次原工件直评。正式测试预算维持 1800 秒、整段评分 1800 秒；准备阶段沿用已声明的 900 秒诊断上限。补充观察只保存源码、身份与保护事实，不参与判分。失败或清理未知时停止后续，不覆盖历史运行目录。

验收仍须检查实际安装子命令、完整测试退出与逐参考状态、原/新增分区、错误候选失败位置、代码实际导入位置、原工件完整 baseline 及两层清理。公共评分可信性阻塞由第1类线程负责，本次材料修订不核销该阻塞，也不代替模型或训练准入。

原件入口：`runs/category2_repair_20260929/d6_monai_implementation_v1/README.md`、`material_compatibility.json`、`validation/commands_v5.json`；根复核记录在 `frozen_d6_monai_v1/root_predeployment_review.json`。
