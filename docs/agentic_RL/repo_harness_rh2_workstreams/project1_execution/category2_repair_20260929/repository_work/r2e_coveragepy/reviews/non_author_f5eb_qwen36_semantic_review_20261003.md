# F5EB Qwen3.6 首臂：非作者候选语义窄核

2026-10-03。**结论：候选语义通过，质量为正确、局部的源码修复；公开测试改动是合理同步预期。未发现新材料阻断，无必须追加的题级 CPU 实验。** 原正式 reward=1、8/8 保留；本结论另由完整源码、公开测试改动与已验 CPU 正路线的字节身份支持，不以绿色结果代替语义判断。

任务 `coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96`，job `gpu1003-coveragef5eb-qwen36-a1`，模型 Qwen3.6-35B-A3B。非作者 Codex subagent `/root/coveragepy_f5eb_cpu_review` 已接触本题私有 rb3h、候选与 CPU 核查，**不是 fresh 公开读者**。本輪仅读本地 baseline.tar、原 FrozenPatch、完整改动、轨迹和既有执行/CPU证据，做 SHA、AST与文本核对；未运行候选、项目测试、SSH、Docker、安装或模型。完整七维、效率和总账由父线程承担。

## 原件与实际范围

原件根 `runs/ordinary_gpu_probe_20261002/remote/queue_v11/results/gpu1003-coveragef5eb-qwen36-a1/`。复用 [执行独立核查](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/coveragepyf5eb_qwen36_a1_execution_review.md) 的首请求、GPU环境、运输、完整评分与清理闭环；不将 CPU image ID 改写为 GPU 身份。

实际交付是原公开题面加中性 devbrief（末尾空白按交付公式裁去），prompt SHA `c10fd285b3fc598e74574e3345413778acd43ab8674489988fd518bed5a6a649`。题面要求 totals covered/missing；已决定 A／最终 rb3h 允许每文件 summary 也增加这两键，但必须成对正确。当前评分材料为076/077，未重开这个边界。devbrief明确原公开 JSON 测试使用旧完整字典，新增题面字段后需结合题面判断预期同步；没有提供私有候选或断言。

baseline.tar SHA `9a8eee2ed0c5b5008e1036a2879894079be4a7c5aab9dbd9ba10685ac53faf8b`。本轮独立从原tar读两份文件，与baseline对应摘要匹配；原FP的两份base64全文实算SHA匹配，实际projection也是这两条路径：

| 文件 | baseline SHA-256 | 候选 SHA-256 |
| --- | --- | --- |
| coverage/jsonreport.py | `82f4f4d9dc940d0b1be6d027e66ed8c103314847d901f0281aec04d8ab34c6f3` | `3d9564ae29756141de41273b0123635b17c429d9cc5997a8db6572e9336b830d` |
| tests/test_json.py | `70116b13adea657318148c8a1aaae40d29e66cca8660611190bf4d839db36e54` | `c58d781b68969f1e3115978aae4b387c8a2c42ea6e2755a44625986b9cd93602` |

FrozenPatch digest `1ceb40539f6c6edc572a652503052559e4d228a3ddcce617e751382ad13550dc`。源码完整字节与固定 R6 正对照 C1 完全相同，非仅相似或同reward。C1 的原正式8/8与本轮 GPU8/8是两份各自版本身份明确的事实。

## 修复语义与质量

生产改动只有四个字典项：totals加入 `self.total.n_executed_branches`、`self.total.n_missing_branches`；每文件 summary 加入自身 `nums` 的同两项。移除这四个新增字典项后，整个源码 AST 与baseline相同。没有硬编码、按测试名分支、最后文件取值、异常吞掉或改动测量逻辑。

| 要求 | 候选实际处理与依据 | 判断 |
| --- | --- | --- |
| 总计与多文件 | report_one_file仍逐报告文件 `self.total += nums`；Numbers.__add__累计n_branches与n_missing_branches。新totals取总值。 | 正确 |
| 可选每文件成对 | 同一has_arcs块内加入两键，值取该文件nums，不取累计total。 | 符合已定A |
| 保存后报告 | 门控是测量数据 `coverage_data.has_arcs()`，没有改成report对象的config.branch。 | 正确 |
| 测量子集 | get_analysis_to_report按morfs及include/omit筛选，只有实际报告分析进入total；Coverage.json_report每次创建新JsonReporter，避免上次总计残留。 | 正确 |
| 零分支 | has_arcs真时照常输出两键，条件不依赖n_branches非零。无分支时为0/0。 | 正确 |
| 目的地分支弧计数 | baseline results.py总计exit destinations，missing按缺失branch arcs累加；n_executed_branches为total destinations减missing。未错用partial行数。 | 正确 |
| 原行模式/上下文 | 新键仍只在has_arcs时出现；原字段、上下文与报告返回行为未改。 | 本次范围内保持 |

上述源码依据从本臂tar中的 results.py、control.py、report.py核对；[既有非作者 CPU 核查](non_author_f5eb_cpu_review_20261003.md) 已在相同 C1 全文和最终rb3h条件下核保存、多文件、子集、零分支与分支弧计数。本轮没有发现新的漏判、误拒或需要CPU判清的歧义。写法短、沿用已有Numbers属性及报告累加流程，质量足以支持本版普通修复能力诊断。未做全仓回归，不外推所有报告路径。

## 公开测试修改与评分污染

完整 tests/test_json.py 的差异只有四个期望字典项：branch测试的每文件summary和totals分别加covered=1、missing=1。fixture执行一个目的地、另一目的地缺失，数值正确。原四个测试、helper、完整字典等式、既有所有字段和值、上下文与行模式断言都保留；删除这四个新增项后，完整测试AST与baseline相同。没有删除断言、跳过测试、改fixture、改测试入口或强制通过。

原轨迹先改源码，再运行未同步的原公开测试，出现branch一项失败、其余三项通过；错误内容是原字典缺新键。模型随后同步上述两份字典，公开测试4 passed，最终再验证4 passed。这一顺序和完整改动支持“合理同步预期”，不构成测试作弊；公开测试绿色本身不证明总计正确，语义结论由前述源码、C1同字节与完整私有8键另支持。

最终 rb3h 从 `tests.coveragetest` 导入测试helper，不从 `tests.test_json` 导入被修改的测试；helper文件未变。FP只含两份公开文件，未包含私有r2e_tests、expected map、runner、conftest或fixture，也没有测试模块顶层副作用。未发现候选对隐藏评分的污染。

原report的 `patch_hygiene.test_files_modified=false` 必须保留为原字段，**不能解释为公开测试未修改**；FrozenPatch/projection及诊断已明确 tests/test_json.py 被改。该字段的表现不改变本候选实际改动范围，也不能据此将合理同步改判为作弊。

轨迹还有两个核查边界：一次示例误把file对象传给outfile，报TypeError，后续改正，最终源码未新增绕过；一次扩测请求tests/test_report.py不存在、0 collected，不能称额外回归通过。模型最后概述把每文件字段也写成issue缺失项，严格说题面要求是totals、已定A允许每文件扩展；表述略宽，实现仍在许可范围内。

## 用途、材料阻断与CPU需求

本臂可用于带076/077、A／最终rb3h版本标注的普通基座修复诊断及必要能力比较。没有新材料阻断，JSON blockers与new_material_blockers均为空。**本轮不要求追加CPU**：生产全文就是已验C1，公开测试仅正确新增期望、无断言弱化或helper污染，本次正式GPU8键亦全部匹配；为同字节增加重复CPU没有新的判别价值。

这不授训练资格，不支持未注明修订版本的原benchmark成绩，也不把Qwen首臂等同于两模型配对完成。完整执行、效率、GPU服务/预算与总账由父线程核定。若后续出现具体遗漏或污染证据，再按受影响范围聚焦复验。

仅新增本Markdown与 [同名JSON](non_author_f5eb_qwen36_semantic_review_20261003.json)。JSON保留完整两文件diff、前后SHA、逐语义判断、CPU复用、具体限制和18个证据摘要；未改原件、共享代码、任务材料或board。
