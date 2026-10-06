# D6：SWE 来源测试修订的有界成本设计

2026-09-29。**现有执行链足以承载补充测试；尚缺正式、版本化的材料入口及其身份、参考分列和资格绑定。建议先用 MONAI5932、Conan11594 做仅追加测试的两题切片，继续使用现有 SWE F2P/P2P 二值评分。** 本文只读本地源码与已验材料，没有实施、执行项目或容器，也没有改变正式题目、测试、契约或奖励。

依据是本批实际使用的 [frozen_code_v1](../../../../../runs/swegym_cpu_preprobe_20260929/frozen_code_v1/rh2)。逐字节比较确认，下文涉及的 `bundles_v2`、SWE ingest、prepared_tasks、training_view、spec_vendor、scoring、prepared_task_face、replay_grade、manager、contracts/grading 十个生产文件，以及诊断 `replay_with_install_recipe.py`，当前共享树均与冻结版本一致。R2E 当前材料注册表/pins 已前移，不能把其新材料版本当作本批运行证据；只借鉴其版本登记方式。

## 现有能力与实际缺口

| 接缝 | 已有能力 | 最小需要处理的部分 |
| --- | --- | --- |
| [私有材料](../../../../../rh2/src/repoharness2/envpack/bundles_v2.py) | `PrivateGradingBundleV2` 已有 `test_patch`、`fail_to_pass`、`pass_to_pass`，不含 gold；材料摘要进入 `EnvironmentPackageV1.grading_bundle_digest` | SWE 没有材料修订编号。`version` 是仓库/vendor 查表键，不能挪作修订号；`spec_vendor_id` 也不能随意替换。建议新增修订版私有模型/判别版本，仅修订任务使用，旧 v2 序列化及摘要不变。保留原材料摘要、修订 ID、原参考集合及新增参考集合 |
| [可信 ingest](../../../../../rh2/src/repoharness2/envpack/ingest_swegym_lite.py)、[host view](../../../../../rh2/src/repoharness2/envpack/training_view.py)、[prepared](../../../../../rh2/src/repoharness2/envpack/prepared_tasks.py) | ingest manifest 固定 pin，包关系及私有产物哈希复核；prepared/dispatch 再核环境包身份 | 新增钉住摘要的私有修订登记：题目/base、原补丁及参考摘要、修订补丁摘要、公开依据、增加的精确 nodeid、正负对照证据。先验证原件，再构造有效材料，重新生成 ingest/prepared 身份和必要指纹。原 archive/vendor provenance 保留，不能手改 prepared JSON 绕过 manifest；同一道来源题继续保留原 task_id，版本由包/修订身份及独立运行目录区分 |
| [共用 spec 构造](../../../../../rh2/src/repoharness2/adapters/slime/prepared_task_face.py) | `build_grading_spec_from_host_view` 同时供 replay 和 `PreparedTaskFace.grading_spec` 使用；可信 setup 恢复受保护测试再 apply；hygiene 从补丁路径派生 | 在这一共同入口消费修订后材料，解析闭包也使用同一有效参考清单。不能只接 replay。新测试文件必须进入恢复、保护及执行范围；保留 actor 的公共投影边界，私有断言、gold 和修订登记不进入解题提示或解题容器工作区。评分容器仍须按既有可信 setup 放入并执行私有测试 |
| [命令派生](../../../../../rh2/src/repoharness2/envpack/spec_vendor.py) | 测试命令由 vendor 与补丁触及的测试路径派生；mypy 另按 case 名派生 | 两个首例均可在现有受测文件追加独立命名测试，无须自由命令入口。`eval_cmd` 是需互检的信息副本，不能用它偷偷扩大命令。以后“只加入 P2P”仍须证明原命令确实执行该 nodeid；未覆盖的其它模块不在这次设计切片内 |
| [诊断 recipe/materials](../../../../../rh2/experiments/env_recipe_repair_20260919/replay_with_install_recipe.py) | `--materials` 已核原补丁 SHA、替换测试资产、更新 hygiene/版本及审计；`--recipe` 可覆写安装；`--bindings` 可恢复精确参考映射 | 现有 materials 要求测试命令不变，只改 `test_patch`，原解析闭包及 bindings 仍使用原 `grading`，不能把新增测试自动变成正式参考；且只 monkeypatch replay。可复用检查思路，不能直接宣称机制已完成。安装配方、材料修订、参考绑定各自保留身份；本批供应关闭，生产接入仍须由同一有效材料生成普通及两段脚本，避免另一分支留下旧测试 |

推荐修订记录只允许追加有依据的测试及参考，首版不开放任意 eval shell、题面替换或 gold 修改。联合 F2P/P2P 仍按现有 `parse_eval_log_v2` 和 manager 判分，不加入行为加权、部分分或新的奖励算法。登记必须校验去重、F2P/P2P 不重叠、补丁路径/前后摘要；同一题多个修订的顺序和最终摘要必须唯一可复现。更新有效材料指纹时保留来源题和原重复簇血缘，不借修订重新分配数据划分。

## 两个首例应怎样落到测试

| 题目 | 公开依据与已证控制 | 最小测试修订及预期 |
| --- | --- | --- |
| [MONAI5932](tasks/Project-MONAI__MONAI-5932/result.md) | 题面描述同前缀引用，没有限定出现顺序；base 已能计算长名在前的整数加法。私有两方向独立运行，base 为败/过、gold 过/过、reverse 过/败 | 保留原短名在前测试和全部参考；在 `tests/test_config_parser.py` 追加单独命名的长名在前数值断言，按已测 base 行为登记为新增 P2P。正式化后重新验证，不能由本次私有 root 运行替代正式身份验收。范围限这两个顺序，不宣称任意表达式已覆盖 |
| [Conan11594](tasks/conan-io__conan-11594/result.md) | 题面失败命令明确请求 Release；公开 base 的 `test→_build` 保留 `build_config`。gold 实际执行 Release 并写 marker；drop_config 实际改为 Debug 且测试失败 | 保留原六个 generator 测试，追加独立命名测试检验配置传递；建议同时把已有真实 CMake/CTest 的 Release marker 控制移成测试函数，避免仅验证命令字符串。完整真实运行在 base 因原 RUN_TESTS 目标失败，故应登记新增 F2P；若拆出 base 已通过的配置透传断言，可另登记 P2P，但须实际验证，不能只因称作“回归”就归 P2P |

可复用的可执行输入：[MONAI 两顺序控制](../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs/Project-MONAI__MONAI-5932/private/behavior_commands.json)、[Conan Release 控制](../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs/conan-io__conan-11594/private/behavior_commands.json)。其 shell heredoc/独立临时目录需转换为来源测试的 fixture/函数，期望数值和 Release marker 保留；不能把 `expect:any` 直接当通过判据。Conan 使用已验 Ninja/CMake 环境与配方；工具缺失、安装/收集失败不等于目标失败。

Conan 原参考有两个 Ninja 参数成员的 [精确绑定](../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs/conan-io__conan-11594/private/reference_bindings.json)。当前绑定在诊断 wrapper，若要正式接入该首例，须把这个已验映射及版本一起放入共用可信解析入口，而不是新建另一个 replay 特例。新增测试用无歧义名称；原绑定修复不替代 Release 语义断言。

## 版本、报告和资格边界

1. **版本身份贯穿早期失败。** 复用 `GradingReport.grader_version` 标记 parser、材料修订和参考绑定版本；在构造 spec 时确定，安装失败、超时等分支也带标识。私有登记保存原/有效 grading digest，prepared 与运行账本绑定有效包摘要；不把历史 `0/1/1` 回写为新版本结果。`reward_scale_version=binary_v1`、`grading_semantics=swe_f2p_p2p` 保持不变。
2. **原参考与增强参考分列。** 原参考状态、新增参考状态及联合结论分别输出；原参考缺席/skip、安装与完整 test RC 继续记录。现有 report 只有一组聚合计数，`EvalVerdict` 也是严格模型，不能凭空挂字段。最小方案在共用解析/manager 的私有 diagnostics 接缝增加有类型的修订诊断，report 仍只承载有效联合结果；不要在解析闭包中临时写文件，漏掉正式消费者。若追加测试保留旧测试身份，可从同一日志做“原参考投影”，但它不等于旧环境的完整原始评分。修改旧断言或执行范围时尤其不能这样宣称；原始评分仍指向原版本已验账本，必要时做成对重放。
3. **资格必须随材料失效。** [当前 `EnvQualification`](../../../../../rh2/src/repoharness2/grading/manager.py) 比较 image、scripts digest 与参考缺席数。改补丁会改变脚本摘要，已有机制可使旧资格失效；但只改 F2P/P2P、parser 或 bindings 未必改脚本，因此不能宣称已覆盖。建议给修订 spec/qualification 加材料与解析身份摘要并共同校验；旧资格只能服务旧材料，修订任务缺这项即未取得新资格。gold 在新参考完整执行后的环境资格证据只服务该材料/解析/镜像/脚本组合，不授予模型、训练或整题无限范围资格。

## 最小验证矩阵与工作块

| 工作块 | 最小验收 | 主要成本来源 |
| --- | --- | --- |
| 材料登记与两题测试 | 原补丁 hash 错、任务/base 错、重复/重叠参考、越界路径均拒绝；追加补丁能从 immutable base 重建；原测试及 nodeid 保持；两题公开依据逐项可追溯 | 测试 fixture 转换，Conan 真实工具链及绑定；不重审其它已闭题 |
| ingest/prepared/消费者接线 | 未修订任务序列化摘要及评分不变；修订包摘要变化、私有产物篡改拒绝；replay 和正式 actor 路由得到相同材料/spec；actor 公共内容不增加私有数据 | 新修订模型、可信 registry/pin、host/prepared 类型及共同 builder，避免只改实验入口 |
| 身份与诊断 | 原/新增/联合参考可核对；早期失败仍带版本；仅参考或 bindings 变化也拒用旧资格；新文件恢复/保护；普通脚本及供应关闭的实际路径一致，两段字段静态验证无陈旧材料 | 共用解析、私有 diagnostics、qualification 的窄改；无需新奖励算法 |
| 修订版正式 CPU 验证 | 每题 noop/gold/已证退化各一次完整运行，预期联合 `0/1/0`；逐参考、真实候选 bytes、安装/完整测试 RC、缺席/skip、资源归因及两层清理可核 | 至少 2×3 个新版本完整评分；不能只看 reward 或调度 completed。原版本原件可复用为历史对照；若身份/配方不相同须明确差异，不能冒充成对实验 |

代码层用有针对性的静态/单元接线检查覆盖 replay 与正式 actor 共用入口，再用上述真实评分闭环验证；不要求为这项机制跑自主模型或全仓项目测试。正式 actor 的私有边界和派发身份必须验证，但本次 CPU 控制并不等于已完成模型能力评测。

工作量主要分为四块：两题测试材料、可信版本摄入、共用身份/诊断/资格、完整 CPU 验收。前三块相互依赖，Conan 的 bindings 和真实 CTest 比 MONAI 追加数值断言多一个接缝。已有测试保护、投影、执行和清理可复用，不需要重建整个流水线；但把诊断脚本复制到正式目录也不足以完成。暂不承诺工时：补丁转换尚未实做，准备阶段已有触及内存上限和耗时的实证，运行成本须沿用已验证预算而不能只按测试秒数估算。

## 已授权与待决定

[筛选标准 D4/D6](../task_screening_standard_v1_20260925.md)及[本批边界](README.md)已授权 R-c 窄修订的依据和验收模板、本次成本设计及私有行为对照；本轮不需要新增审批。**SWE 正式测试修订机制的实施尚未授权。** 用户后续需决定是否按这个仅追加测试的范围实施，以及上述私有模型版本、报告分列和资格绑定方案；这些是实施范围的决定，不是重新审批已经确认的两题题义。题面修订、其它来源、供应策略、模型/GPU预算和训练准入均不纳入此切片。实现并通过独立验收前，两题仍按现有 S1 限制使用。

根任务复核（本次巡检）：已对照实际材料 wrapper、共用 builder、资格比较及 D6 原授权；上面的三个关键接缝属实。修订模型形状是设计建议，尚非唯一实现要求；实施时先证明未修订材料兼容、有效版本可追溯、所有消费者一致，再选择最小结构。可先完成 MONAI 数值断言切片，再接 Conan 工具链与绑定，不要求一次迁移本批所有题。仅作设计复核，未运行新版本评分。
