# SWE 正式材料修订入口：当前事实与第2类依赖

整理／核对：2026-09-29。核对基准：共享树 HEAD `a31cdcd0adb0fab3e681201edfb928653fdf5b3c`；同时检查未提交改动。本文只作源码与记录核对，没有修改生产代码、维护测试、正式材料或分类，没有运行容器或新评分。

**结论：D6 仍未实施。第2类28道 SWE 的当前修复目标均涉及正式测试、参考清单或题面版本；现有私有对照不能直接完成转类。可以继续做已授权的题级材料、安装／开发条件收口和独立复核。本次需交用户审阅的是共用入口的具体实施范围，不是重新审批 R-a 至 R-f 的题级模板。**

建议先接 mypy10424／17071 的已有公开测试；完整方案及成本见 [implementation_brief.md](implementation_brief.md)。该首片不自动解决其余26题，也不含训练准入。

## 授权与后续记录

| 依据 | 实际含义 |
| --- | --- |
| [统一标准 §5、§9 D4/D6](../../task_screening_standard_v1_20260925.md) | R-a 至 R-f 的窄修订模板已授权；§5 单列“SWE-Gym 修订机制的实现”为模板外事项。D6 原文为“SWE-Gym 的测试修订与题面修订先探索成本、写设计，实现前把成本与设计交用户”。 |
| [09-29 D6 成本设计](../../swegym_cpu_preprobe_20260929/d6_revision_cost_note.md) | 已完成设计，建议 MONAI5932／Conan11594 切片；明确“尚未授权实施”。这不是已经落地的版本通道。 |
| [env_data_eval.md 最后 09-29 条](../../env_data_eval.md) | 仍记“设计已完成但未实施”；最新 [infra.md 09-28／09-29 条](../../infra.md) 为网络清理复核和 miles 迁移审查，未记录 SWE 材料入口新决定／实施。 |
| [本次共用交接](../../task120_status_20260929/fork_handoff.md) | 用户要求已知问题先修，接第2类41题并分批处理；同时明确“处理模板已批准不代表公共实现自动获准”。 |

本次未找到后续明确批准该共用机制的记录，也未找到对应实现。这个结论不是仅依据旧“待做”标签：下面十个相关生产文件与本批 [frozen_code_v1](../../../../../../runs/swegym_cpu_preprobe_20260929/frozen_code_v1/rh2) 逐字节相同。共享树另有 R2E ingest 在制品，未改动也未把它当作 SWE 已实现的证据。

## 生产链核对

| 消费点 | 当前实现事实与缺口 |
| --- | --- |
| [ingest_swegym_lite.py](../../../../../../rh2/src/repoharness2/envpack/ingest_swegym_lite.py) `build_task`（133行起） | 直接从原始行构造题面、`test_patch`、F2P/P2P；无修订单参数。原 archive、镜像、vendor 来源摘要已保留。 |
| 同文件 `load_ingest_outputs`／`load_trusted_ingest_outputs`（426／554行起） | manifest 只接收固定四字段；提交记录受代码 SHA pin 约束；没有修订登记或修订材料读取分支。手改 prepared 或 grading JSON 不构成合法入口。 |
| [bundles_v2.py](../../../../../../rh2/src/repoharness2/envpack/bundles_v2.py) `PrivateGradingBundleV2`（79行起） | SWE 私有面有测试补丁与参考清单，无修订身份。`version` 是仓库／vendor 查表键；不能用它装材料版本。R2E 的 `material_revisions` 不适用于 SWE。 |
| [training_view.py](../../../../../../rh2/src/repoharness2/envpack/training_view.py)（181、334行起）／[prepared_tasks.py](../../../../../../rh2/src/repoharness2/envpack/prepared_tasks.py)（263、439行起） | Host grading 判别联合只接受 SWE v2／R2E；prepared 私有文件 SHA、公开包摘要及环境包摘要有完整复核。可复用这一运输结构，不需要让私有材料进入模型侧。 |
| [prepared_task_face.py](../../../../../../rh2/src/repoharness2/adapters/slime/prepared_task_face.py) `build_grading_spec_from_host_view`（360行起） | replay 与正式 `PreparedTaskFace.grading_spec()` 共用；SWE 解析闭包捕获传入 grading；恢复／保护清单只取 `patch_touched_paths(test_patch)`。新增公开参考若位于别的文件，当前不会自动被恢复／保护。 |
| [spec_vendor.py](../../../../../../rh2/src/repoharness2/envpack/spec_vendor.py)（183行起） | mypy 命令由来源补丁中的 `[case X]` 拼成 `-k`；其它仓库主要按补丁触及路径选测试。只新增参考清单不保证执行。`eval_cmd` 仍为固定 vendor 的信息副本，不能作为自由 shell 开口。 |
| [scoring.py](../../../../../../rh2/src/repoharness2/envpack/scoring.py)（247行起）／[contracts/grading.py](../../../../../../rh2/src/repoharness2/contracts/grading.py) | SWE 继续由 vendored parser 与原 F2P/P2P 规则判定，二值 reward 不需要改变。`EvalVerdict` 是严格模型；不能 monkeypatch 添加未声明字段。原参考与新增参考目前没有独立的材料分区诊断。 |
| [manager.py](../../../../../../rh2/src/repoharness2/grading/manager.py)（1087–1140、1862行起） | `EnvQualification` 只核镜像、脚本摘要和参考缺席数；仅 F2P/P2P 或绑定发生变化、脚本不变时，资格身份不足。已有 diagnostics sidecar 可承载材料身份和分区结果，公共 report 可继续保持原形。 |
| [replay_grade.py](../../../../../../rh2/src/repoharness2/adapters/slime/replay_grade.py)（467、858行起） | 正式 replay 已用共用 builder；资格从旧账本的 `image_identity`／`scripts_digest` 载入。运行行尚无单独的修订／有效材料摘要，应在构造 spec 后、可能早退之前记下。 |

以上十个文件相同的 SHA-256 前缀依次为：`04a22585e74543ae`、`2423fb316e3eeec2`、`a04912d56c3cbdf8`、`3541bd95ae5f7865`、`3ed840716fc3a391`、`8e0037b27c87268e`、`7c26f6a2a875aedd`、`7bd1a4d997caa502`、`0c55f4f31a219143`、`011dd5f5e22c642f`；第一项 ingest 在表中分成两行。

实际 CLI 分三层，并没有现成的 SWE 修订开关：

- [build_environment_packages.py](../../../../../../rh2/experiments/s2_1_ingestion/build_environment_packages.py) 读取固定原件、调用原 ingest、写入原产物目录后经代码 pin 回读；不是材料修订注册器。
- [trusted_prep.py](../../../../../../rh2/src/repoharness2/envpack/trusted_prep.py) 和 [scripts/replay_grade.py prepare](../../../../../../rh2/scripts/replay_grade.py) 均从 `TrustedTaskController.from_repo_root` 准备同一材料，现有选项为来源和题目子集。
- [replay_with_install_recipe.py](../../../../../../rh2/experiments/env_recipe_repair_20260919/replay_with_install_recipe.py) 是诊断 monkeypatch：`--materials` 只替换 `test_patch`，要求测试命令不变；原 parser 闭包及 `--bindings` 仍捕获原 grading。它既没有使新参考正式生效，也未接入正式 actor。`--bindings` 的 [精确映射实现](../../../../../../rh2/experiments/env_recipe_repair_20260919/reference_bindings.py) 可供后续窄接线参考，不能冒充已经统一。

## mypy 首片的执行事实

从当前冻结 [grading bundles](../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/grading_bundles_v2_v0.jsonl) 读到：

| 题 | 原命令选择 | 对新参考的影响 |
| --- | --- | --- |
| mypy10424，vendor 0.820 | `pytest -n0 -rA -k "testNarrowingUsingMetaclass"`；1个 F2P，P2P 空 | `testTypeEqualsCheckUsingIs`、`testTypeEqualsNarrowingUnionWithElse` 不在选择式内；所在 `test-data/unit/check-isinstance.test` 也不在原 patch 中，须加入 base 恢复与保护。 |
| mypy17071，vendor 1.10 | `pytest -rA -k "testTypeGuardTypeVarReturn or testTypeGuardIsBool or testTypeIsTypeVarReturn or testTypeIsUnionIn"`；2个 F2P、2个 P2P | `testUnboundTypeVar` 不在选择式内；所在 `test-data/unit/check-typevar-unbound.test` 不在原 patch 中，须加入 base 恢复与保护。 |

题级负责人已交 [材料清单](../swe_materials/first_mypy_bundle/materials_manifest.json)；本作者独立重算新增 case 所在两文件 SHA，与清单的 `709c22b24c619241…`／`d189254a51fc5352…` 相同。该包仍是准备材料，不是运行时 schema；不需新增重复测试或改题面，正式选择／收集和保护仍待实施验证。

两题安装已有 [09-19 install_wave1 可复用配方与历史验收](../swe_materials/first_mypy_bundle/installation_reuse.json)。已知失败发生于未消费该修复的原镜像：`pip install -e .` 子命令失败被后续成功命令遮蔽。下一步是恢复／绑定已验离线资产配方并补当前版本窄核，不是重新设计环境；实际镜像／wheel 当前可用性仍由执行者核实。入口接通不证明配方已交付。

## 第2类28题的依赖

范围固定为 [fork_worklists.json groups.2](../../task120_status_20260929/fork_worklists.json) 中28条 SWE；下表是对固定起始 `next_action` 的入口依赖分析，不是新题级验收或共享分类更新。**27题需要评分材料／参考版本，1题主要需要题面版本。没有一题仅凭现有入口即可核销当前全部已知修复目标。**

| 题目 | 正式入口需要承载的内容 | 入口实现前可先做的工作 |
| --- | --- | --- |
| Conan15422 | 默认 jobs、多配置生成器及所用 CMake/schema 兼容断言 | 冻结公开要求、已存漏修候选和正确修法；核工具版本。 |
| DVC4166 | 引用节点消歧、同名文件／目录断言 | 固定 pathspec/networkx 已验配方，保留只裁尾斜杠候选，核绑定。 |
| DVC5839 | 默认／4／8 的 CLI 实际数值断言 | 准备 gold、真实成功候选和硬编码8候选；其误奖尚未实测。 |
| DVC6954 | 负 float／容器负值及必要 lock 行为 | 整理已有对照；保留非法表达式不扩题的决定。 |
| mypy10174 | 同开关下不重叠比较的公开负例 | 核 gold 保留诊断及关闭全部比较的候选；不预写误奖。 |
| mypy10424 | 既有普通收窄 case 加 P2P、选择与保护 | 准备节点／来源 SHA／正确与错误对照，收口安装。 |
| mypy15184 | R-f 中性复现说明进入 `PublicTaskBundle` | 核同名类复现；让未接触私有答案的读者复核题面。 |
| mypy17071 | 真正 unbound 负例加正式参考、选择与保护 | 准备节点／来源 SHA／成功与禁用检查候选，收口安装。 |
| Moto5406 | 双地区断言 | 复用已有正确／恒 East2 退化对照。 |
| Moto5960 | INCLUDE／KEYS_ONLY 字段集合及节点身份 | 准备 gold／漏修候选；目前只有需求—断言缺口，不能称错误候选已满分。 |
| Moto6114 | Identifier／ARN 身份断言 | 固定已有对象身份对照。 |
| Moto6408 | 两镜像标签集合及对象归属断言 | 固定正确解、只改排序、误删其它标签候选；邻接旧缺陷另定范围。 |
| Pandas48106 | 两组 tz 引用绑定、独立身份／混合状态对照 | 核原日志节点绑定；历史0/1不追溯改分。 |
| Pandas50319 | 允许合理 None 路线的验收修订 | 先构造保留旧行为的 None 正对照，验证实际可接受范围。 |
| Pydantic8511 | 三类继承保护及替代正对照 | 独立核窄修与安装；保留原 gold 失败。 |
| MONAI2446 | 同输入内外行为对照 | 复用已跑行为，转换成可登记的测试。 |
| MONAI3715 | forward 的 training／梯度和退出恢复断言 | 核 actor 条件、正确／退化候选。 |
| MONAI4583 | 2D／3D 标签及 dtype 断言 | 整理已跑对照，保留 CPU／CUDA 身份适用范围。 |
| MONAI5932 | 双顺序真实解析值断言 | 将已有长名在前控制转换成独立测试；可作下一共用切片。 |
| MONAI6975 | direct／Dataset 实际像素断言 | 复用已跑矩阵及经过验证的准备预算。 |
| Conan11594 | 真实构建配置、执行 marker 与既有精确绑定 | 准备 CMake/CTest fixture，不能只验命令字符串。 |
| Conan13230 | 真实双 profile 的 Linux flags 断言 | 复用 Linux 对照，无须安装无关 SDK。 |
| Conan12397 | 完整键名下 Apple／Linux 生成结果 | 固定只修 objcpp 错解与正确对照。 |
| Dask7656 | 类型及字段值断言 | 转换已有行为控制，保留题面提示程度说明。 |
| Dask7138 | 旧 `array=` 关键字签名兼容回归 | 核兼容实现与 actor；不能只因原 gold 得1核销回归。 |
| Pydantic6283 | 非示例相等性和必要私有字段组合 | 复用对照，保留不验证构造护栏。 |
| Pydantic5662 | 一般 matcher 与 dict／object 断言 | 转换已有控制并核正对照。 |
| Pydantic8793 | 默认值与旧行为断言 | 复用已有对照及公开依据。 |

可以先验收上述工作中的环境／材料准备部分，但应写成部分完成；不能据此把整题交给普通探针。若某题的新证据证明旧缺口不存在，可按证据单独撤销依赖；本次没有获得这种新证据。R2E 的13题另有现成材料机制与负责人，不由 SWE D6 整批阻塞。

## 本次验证的边界

已核记录、实际源码、CLI、当前原始两题材料和十文件冻结字节；未运行新评分，未核28题每份底层原件，未将父线程转达的题级材料进展冒作本作者独立复跑。此轮停止在可执行设计和题级依赖清单；公共实现交按本轮分工指定的实现者，在明确 D6 范围后落地并接受独立复核。
