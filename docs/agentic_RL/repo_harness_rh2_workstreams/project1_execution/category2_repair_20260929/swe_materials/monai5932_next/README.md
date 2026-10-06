# MONAI5932 下一切片：补长引用在前的数值断言

2026-09-29。**材料已准备，未接线、未激活、未执行新测试。** 等首两道 mypy 的冻结版验收收口后，再按已授权 D6 下一切片实施；本目录不改变这两题的任何输入，也不需要重新申请同一修订机制授权。

最小方案是在原 `tests/test_config_parser.py::TestConfigParser` 中新增一个普通 `unittest` 方法 `test_substring_reference_long_first`，断言长引用先出现的表达式实际得到 **4**。保留原短引用在前的 F2P，以及全部 14 个原 P2P；新增节点列入 P2P，共 **1 F2P＋15 P2P**。使用同文件现有的 `ConfigParser(config=...)`、`get_parsed_content` 和 `self.assertEqual` 风格，无新依赖、mock 或私有 shell 后检。

## 依据和断言

| 问题／依据 | 本次处理 | 状态 |
| --- | --- | --- |
| 公开题面要求同一表达式中的同前缀引用正确解析，没有限制引用出现顺序。 | 保留原短引用 F2P；补长引用 P2P。 | 公开题面及原参考已核。 |
| base 的配置语法说明 `@` 指向对应配置值、`#` 表示子结构、`$` 按 Python 表达式求值。这里两个整数值为 1、2，另加 1，因此长名先出现也应为 4。 | `{"training": {"num_epochs": 1, "num_epochs_per_validation": 2}, "total_iters": "$@training#num_epochs_per_validation + @training#num_epochs + 1"}`，断言返回值等于 4。 | 期望来自公开 API 语义；不是复制 gold 的内部状态或输出。 |
| 09-29 CPU 原材料正式评分为 noop/gold/reverse＝0/1/1；私有同源码行为显示长名在前为 base/gold＝4、reverse＝目标 SyntaxError。 | 冻结原正对照和已证误对照的精确补丁，供新材料验收。 | 历史事实已由题主和跨包复核确认，适用旧材料；不是本候选测试的执行结果。 |

公开依据存于本批 [base 配置语法](../../../../../../../runs/category2_repair_20260929/swe_materials/monai5932_next/source/base/docs/source/config_syntax.md)（76–105 行）、[`ConfigExpression.evaluate`](../../../../../../../runs/category2_repair_20260929/swe_materials/monai5932_next/source/base/monai/bundle/config_item.py)（350 行起）及[原公开题面](../../../../../../../runs/category2_repair_20260929/swe_materials/monai5932_next/source/original_public.json)。新测试没有检查 `sort`、`reverse`、`findall`、私有 helper、异常文案或中间替换字符串；一次性完整匹配等其它正确算法也可通过。范围只覆盖已证的两个整数加法顺序，不宣称任意表达式、重复引用或更多嵌套都已验。

修订依据为 [统一标准 §5 R-c](../../../task_screening_standard_v1_20260925.md) 与 [D6 下一切片](../../d6/implementation_brief.md)。已有事实复用 [09-29 最终卡](../../../swegym_cpu_preprobe_20260929/tasks/Project-MONAI__MONAI-5932/result.md)及[独立复核](../../../swegym_cpu_preprobe_20260929/reviews/monai5932_result_review.md)，没有重新审查全题。

## 材料与身份

完整路径、字节数和 SHA256 见 [materials_manifest.json](materials_manifest.json)。它是准备清单，**不是当前注册器可消费的配置**。

| 文件 | 用途 |
| --- | --- |
| [extra_tests.patch](../../../../../../../runs/category2_repair_20260929/swe_materials/monai5932_next/extra_tests.patch) | 人工审查增量；应用前提是 base 已应用原 `test_patch`。 |
| [effective_test.patch](../../../../../../../runs/category2_repair_20260929/swe_materials/monai5932_next/effective_test.patch) | 将来登记的完整有效测试补丁候选；直接应用到 immutable base。保留原补丁引入的常量、方法和断言。 |
| [original_test.patch](../../../../../../../runs/category2_repair_20260929/swe_materials/monai5932_next/original_test.patch) | 原件的逐字节冻结副本；不覆盖历史材料。 |
| [references_candidate.json](../../../../../../../runs/category2_repair_20260929/swe_materials/monai5932_next/references_candidate.json) | 原／新增／有效参考分别保存。新增精确候选为 `tests/test_config_parser.py::TestConfigParser::test_substring_reference_long_first`。普通方法无参数展开；真实 collection 仍待核。 |
| [gold.patch](../../../../../../../runs/category2_repair_20260929/swe_materials/monai5932_next/controls/gold.patch)、[reverse_order.patch](../../../../../../../runs/category2_repair_20260929/swe_materials/monai5932_next/controls/degenerate_reverse_order.patch)、[noop.patch](../../../../../../../runs/category2_repair_20260929/swe_materials/monai5932_next/controls/noop.patch) | 原正对照、已证错误候选及空候选。gold 与原 validation 的 `golden_patch` 字节相同。 |
| [static_checks.json](../../../../../../../runs/category2_repair_20260929/swe_materials/monai5932_next/static_checks.json) | 本轮已完成的身份、静态语法和补丁应用核对。`inspection/` 留有隔离副本。 |

绑定 base 为 `3c8f6c6b94ba26f8c9df5b7c96089494de6f69cb`，base tree 为 `20622b7558fea650c1224a972c03931f77a93836`；来源是 `s2/ingest` 四份材料的同一题第 20 行。原 grading digest 为 `sha256:508b6df307c19f490e821ee64bdf8d91c4395515dd9e42aa3255a4b09f56cddc`，public digest 为 `sha256:7d5c7b60d95cd817adc0cf8930c0ee99ab6d542ac6a7f6642db8b9518e066958`。镜像 manifest 为 `sha256:84a4d4afe3f663633da40359ddb8ff5c0e951144e103bed27b907481f9cee6f4`，沿用原环境，不新增配方。

本轮已核：source 公共／评分对象等于现有来源行；原测试、两份控制补丁 SHA 一致；5 次 `git apply --check` 及隔离副本应用均成功；完整有效补丁的结果等于“原补丁＋新增补丁”；原有测试 AST（语法树）保持不变；新增方法唯一，候选参考无重复或交集。**没有导入 MONAI、收集 pytest、运行项目测试或执行评分。**

## 当前接缝与下一步

代码快照 SHA 在材料清单中。当前 `SWERevisionRecord`、`SWEMaterialRevision`、`PrivateGradingBundleSWERevision` 只接受 mypy `append_mypy_p2p`；不能把本清单投入当前入口后声称 extra-test 已支持。后续最窄实现是：

1. 在同一受信注册器增加本切片所需的完整有效测试补丁类型，验证原 grading/public/base、原／有效补丁 SHA 和受测 base 文件 SHA；从原件重放生成新材料。现有“只恢复原参考就能还原 parent digest”的校验必须按新操作还原**原 test_patch**，不能拿有效补丁充当父版本。
2. `derive_test_command_for_bundle` 目前对所有修订包直接走 mypy 分支，须按操作分派。MONAI 沿用已有通用文件派生命令 `pytest -rA tests/test_config_parser.py`；无需自由 shell、额外选择器或 parser alias 绑定。
3. `prepared_task_face.py` 的文件保护、基线 SHA 检查和新增参考投影目前读取 `added_mypy_cases`，须消费本切片的受信文件及新增 P2P。文件仍只有 `tests/test_config_parser.py`，包含在有效补丁路径里；原／有效测试恢复、候选隔离和 grader 保护须覆盖这个完整文件。
4. 复用已实现的材料身份、诊断分区和资格失效机制；actor/replay 仍从同一 builder 消费。新材料资格不可沿用原材料资格。首两题冻结产物保持原样，MONAI 后续产物另存新版本。

这些是待实现接缝，不是本轮代码变更。完成接线后至少执行三次完整 CPU 评分，预期如下；**下表全部是待验证结果**：

| 候选 | 原 F2P | 原 14 P2P | 新长名在前 P2P | 联合 reward／完整测试 |
| --- | --- | --- | --- | --- |
| noop | 失败 | 通过 | 通过 | 0；1 failed、15 passed |
| gold | 通过 | 通过 | 通过 | 1；16 passed |
| reverse_order | 通过 | 通过 | 失败 | 0；1 failed、15 passed |

验收核真实 collection 的 16 个精确节点、两分区执行状态、完整退出码及无缺失／skip；核候选实际导出源码 SHA、恢复后测试文件 SHA、原安装命令及导入对象、清理结果、actor/replay 材料身份与资格失效。新节点失败必须是已知长引用解析回归，不能把缺包、安装失败或 collection failure 当作误候选被拒绝。

成本可复用的历史范围：原三次均 2 CPU／4 GiB；trusted setup 约 477–722 秒、安装约 10 秒、测试约 27–34 秒。原镜像已有 `requirements-dev.txt` 修改，不能称 pristine；历史使用 setup/reset 900 秒，不能回称 300 秒通过。4 GiB 峰值包含准备阶段缓存／copy-up 压力，历史 `resource_facts=null` 的限制保留。新切片至少三次评分及一次独立复核，不能用旧私有行为矩阵替代。完成后再交题级转类；当前材料不授予训练资格。
