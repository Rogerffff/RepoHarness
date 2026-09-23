# Training Semantics 独立审查（2026-09-16）

范围：第四组 P-A 的正向归因、R2E-A 契约与助手。读取当批 README §0/§6.5、计划 §7–§9、R2E-A 决定及相关生产源码和维护测试。只写本目录证据；未修改生产源码、维护测试或旧 evidence，未运行 SSH、Docker、GPU、API。

结论：**复现两项实现缺陷（T1、T3），另有一项必须准确呈现的范围/来源语义变化（T2）。** T2 的最终授权判定由主审依据用户原话裁决，不能只据作者 §9 的事后登记断言“未获批准”。R2E 正常助手的并集计数保持精确映射二值口径；手工非法计数能穿过校验，但正常助手不会产出该形状，列为非阻断观察。资格正式注入及构建归因是已登记的未完成切片，不把它们伪装成已实现，也不重开已批 reward 算法。

验证：两组维护测试共 **96 passed、0 skipped**；本轮 CPU 探针退出 0。复现命令与测试输出见 [verification.md](verification.md)。探针源码及全部事实见 [probe_training_semantics.py](probe_training_semantics.py)、[probe_training_semantics.json](probe_training_semantics.json)。源码 SHA-256 已记录在 JSON；文中的源码行号以本轮工作区为准。

## T1 · P1 / 实现缺陷：无关候选文件的坏语法被当成测试失败原因

- **当前行为与位置**：`grading/manager.py:2977–2998` 编译所有候选 `.py`，只要 `probe["error_paths"]` 非空就判 `candidate_execution_failed`。`classify_execution_failure_shape`（1079–1105）只返回一个通用形状和匹配行；没有把实际失败的文件/异常与复证的文件联系起来。
- **违反的不变量**：README §0/§3 A 要求“已明确由模型修复造成”；计划 §7 R2 要求 collection 路径或回溯末帧定位到候选，再作语法复证；§8 F3 改进复证方法，没有删除这个因果条件。单独存在语法错误，只能证明这个文件无法编译，不能证明它造成当前测试入口失败。
- **证据**：JSON `unrelated_syntax` 先真实运行两条测试通过；随后让候选目录之外的依赖不可用，pytest 因 `ModuleNotFoundError: qualified_external_fixture` 返回 2。测试完全不导入 `src/unused.py`，日志也没有该路径。只要把该未导入文件写成坏语法，生产 `SWEGradingManager.grade()` 就产出 `candidate_execution_failed / 0`；同一份失败日志配合法的 unused 文件，则为 `test_log_parse_failed / None`。这是单变量对照，不是根据源码猜测。
- **影响**：将真实环境/安装故障藏成可训练负样本；同时会系统性惩罚碰到语法样例、暂不用的模块或 Python 版本专用文件的候选。另一独立 Production Tracer 用真实 orchestrator → manager → gate → admission 验证同根反例最终 `KEEP_FULL`，见 [production_probe_result.json](../production/production_probe_result.json) 的 `unrelated_error_transport`。
- **分期与验收**：producer 启用前修，属于落实已批 A 的实现修正。至少要求实际测试失败的源码位置与候选复证失败位置一致，并保留正向失败证据；不能把任意 collection/import 错误加任意坏 `.py` 拼成因果链。验收：本反例保持未知、无 reward；真实导入候选坏语法的启动/收集两类日志仍产出 0；验证最终报告和运输结果。

## T2 · P1 / 范围与来源语义：正常完成的测试也可能因参考 ID 全缺席而从 0 变 None

- **当前行为与位置**：`grading/manager.py:1108–1118` 仅按 `num_parsed_tests == 0` 或 `bucketed - missing <= 0` 触发；`1680–1708` 随后覆盖来源评分，无匹配形状也转 `test_log_parse_failed / None`。这里把“参考 ID 全缺席”直接等同“候选测试段全局失败”。
- **证据**：JSON `all_reference_missing_completed_tests` 用真实 pytest。官方测试的参数 ID 来自候选正常源码 `src/id_source.py`；候选将 `label="before"` 改成 `"after"`，测试正常完成 **1 failed + 1 passed，退出 1**，没有 collection/startup 失败。两个状态被 parser 正确解析，但参考 ID 都含旧 `[before]`，故全部缺席。`grading_outcome_fields` 给出来源规则的 `tests_failed / 0`；当前 manager 无论有无资格都改为 `None`。有资格时唯一缺条件为 `shape_undetermined`，根本没有发起编译复证。
- **规则与授权边界**：`envpack/scoring.py:189–202,268` 明确 SWE 缺席计失败。计划 §7 R2 仍保留不能归因的 ImportError 等 `tests_failed`；§8.2 F2 将三路处理限定为“这类待归因的全局失败”，并明确“有可信实际测试结果时仍遵循来源规则”。但作者 §9.4 F2 / §9.6 又明确登记“参考清单全部缺席样本 0→None，按用户 09-16 确认”。现有文件只引用用户“确认，可以开始执行”，没有更具体的用户原话，因此本报告**不将此项直接定性为未经授权的实现 bug**。
- **影响**：若按 §8 的窄范围验收，这是超出全局执行失败集合的拒绝路径；若用户确实明确接受全部参考缺席一律 None，这就是已实施的来源语义取舍，必须登记会排除参数化 ID 随源码改变、只运行出非参考 ID 等候选，不能仅称“未知全局失败不进训练”。其它实际结果仍留 sidecar，但训练侧失去这类原本的 0。
- **分期与验收**：主审先以当批授权原话裁定范围，不重开新 reward 算法。若按 §8 落实，正常完成反例应遵循来源缺席规则，已证资源终止及真正未知全局失败仍 None；若已批扩大范围，则把此真实反例、对应数量和分布影响写入验收，不能宣称仍完全沿用 SWE 来源评分。两种情况下都保留此反例作为回归证据。

## T3 · P1 / 实现缺陷：内存编译复证仍会导入候选根目录的 json.py

- **当前行为与位置**：`grading/manager.py:1016–1021` 从 `/testbed` 启动 `python -`，首行 `import json, sys`。此时仓库根目录在模块搜索路径中；`json` 并不保证来自标准库。`prepared_task_face.py:292–296` 只增加 conda 激活，没有隔离该导入。
- **违反的不变量**：计划 §8 F3 明确要求复证不执行仓库模块，避免同名模块遮蔽。用 `compile()` 替代 `py_compile` 已消除落盘缓存问题，但仍没有满足独立复证模块的这一条件。
- **证据**：本轮真实执行生产 renderer，候选根目录 `json.py` 先打印 `CANDIDATE_JSON_EXECUTED=1` 再抛异常，脚本返回 1；同一已证语法错误转为 `compile_probe_exit=1 / None`，见 JSON `compile_probe_imports_candidate_json`。Production Tracer 的进一步单变量对照中，目标源文件语法合法，根 `json.py` 却打印伪 `RH2_COMPILE_ERROR`，manager 接受它并最终 `KEEP_FULL / 0`，见 [production_probe_result.json](../production/production_probe_result.json) 的 `compile_local_json_shadow`、`json_shadow_transport`。
- **影响**：候选代码直接成为复证器的一部分，既能丢掉本应获得负反馈的语法失败，也能制造并不存在的语法证据。这不需要安装段改写解释器，故不能只用已登记的 D3 安装期运行器变化代价解释；没有 root 提权或 sandbox escape，本报告也不提出新通用防作弊平台。
- **分期与验收**：producer 启用前修，是既有 F3 的窄实现修正。保持同一解释器和候选权限，但避免复证辅助模块被候选目录遮蔽。验收至少覆盖合法/非法源码、根 `json.py`、根 `py_compile.py`、缓存路径冲突；候选同名模块不执行，伪造输出不成为编译事实，真实语法错误仍可复证。

## 已核实的边界与未完成项

1. **R2E-A 正常 producer 助手**：`expected_map_matches` 的 `total_count = |expected ∪ observed|`，多出 observed key 时 match < total；不同状态、缺键、多键均 reward 0，相等的 `FAILED/ERROR/SKIPPED` 期望也能匹配为 1。本轮矩阵验证这些行为。`GradingReport` 的 `expected_total_count` 字段说明仍写“期望映射键数”，应随既定并集口径校正文案；这不是新 reward 决定。
2. **R2E 低优先级契约观察**：`contracts/grading.py:302` 只在 `total > 0` 时拒绝 `match >= total`，所以手工输入 `match=7,total=0,tests_failed` 能通过（JSON `r2e_impossible_counts_accepted`）。**正常 `expected_map_matches` 不会产生此形状，当前 R2E producer 尚未接入**；本项不阻塞 SWE 验收，也不建议为此新增运行挡板。后续维护现有契约矩阵时补齐计数自洽即可。
3. **资格与安装基线**：源码确实按 gold/noop、resolved/tests_failed、reference_missing_count=0、镜像身份及脚本摘要筛资格；旧缺 digest 账本、cc 和 infra 行不会入资格。安装段末 RC 与资格基线相同（包括 rc=2）时不阻止归因，这符合最新 §9.4 的实现说明；它只能作为偏离检查，不能替代 T1 缺失的正向因果证明。当前段末 RC 也不等于每条构建命令成功。
4. **正式 actor 与构建切片**：`PreparedTaskFace.grading_spec()` 在 `prepared_task_face.py:457–461` 没传资格，故真实 formal actor 仍不会产出新候选失败类别；driver 的资格路径已接通。构建/安装归因仍未实施。这两项是已登记的计划未完成；不能把运输替身通过写成生产资格接线完成，不能无依据把其余已批归因重新称为必须用户选择的新 T0。
5. **资源事实**：三种已知终止输入在维护测试中都产出 infra/None，先于候选归因；没有扩大成所有正常测试必须具备内存观测。额外组合探针表明 test_rc、oom_kill、OOMKilled 全为 None 时仍能产出 0，缺失列表为空。该事实需要实现者说明哪些终止事实是本规则的必要证据；本轮没有真实容器缺 marker/读资源失败的可达性证据，因此未将它单独升级为正式 finding，也不主张“任一可选内存指标缺失即拒绝正常评分”。

本轮最相关的审查维度为 B（丢失/污染哪些训练样本）、F（批准边界和来源语义）、G（真实生产 manager 与最终运输）、E（维护测试漏掉的反例）、H/M（来源计数与归因证据）、N（R2E 兼容默认值）。没有扩为全仓审计或新评分平台。
