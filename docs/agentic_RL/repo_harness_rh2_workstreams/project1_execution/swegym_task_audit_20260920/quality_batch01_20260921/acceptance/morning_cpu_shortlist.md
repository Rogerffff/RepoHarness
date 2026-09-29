# 早晨 CPU 小批建议：先落实三个跨仓开发入口

2026-09-21。依据根已验收的 [B1](batch01_final_review.md)、[B2](batch02_final_review.md)、[B3](batch03_final_review.md)：35题静态交付、37条选择性CPU方案，**没有本轮CPU或模型结果**。建议先取下表1–3；入口实施期间，可独立准备第6项。4–5按余力选择，不要求六项全做，不按本表新增准入门。这里的actor开发检查是以真实解题用户身份执行确定性命令，不需要先调用模型。尚未读取B4初稿，收口后只留一个追加/替换槽，不自动扩量。

## 最多六项，分别回答不同问题

| 顺序 / 类型 | 选择及队列ID | 最小实验与区分力 | 本次运行应沿用的条件 |
| --- | --- | --- | --- |
| **1 · actor开发** | **Conan15422**；B1 `actor-conan15422` | agent生成并读取CMake预设；检查显式jobs=2/7与未配置。区分“能生成，但base缺目标字段”和导入/权限/fixture失败。无需先编译真实工程，也不先造更多坏解。 | 原public镜像，无已知必须派生的环境修复；默认jobs与该actor的`build_jobs`比较，不固定机器核数。 |
| **2 · actor开发** | **DVC5839**；B1 `actor-dvc5839` | 同一YAML的默认/4/8精度及Markdown/JSON；base/gold独立副本。直接补足原F2P只看Mock实参、没有真实CLI输出的缺口，同时验安装配方是否被actor消费。 | `dvc_install_v1c`的本题recipe；原草案显式`PYTHONPATH=/testbed`，其成功不能证明editable安装。另记不注入时的导入来源；按数值契约判精度，不要求字符串或所有输出两两不同。 |
| **3 · actor开发** | **Moto5134**；B2 `moto5134-public-actor-development` | 当前checkout的null/缺键/普通值矩阵和本地mock Events→Logs双detail复现；只有base即可先验开发条件。该题没有具体已证语义冲突，不为凑对照制造坏解。 | **public-image actor**；公开稿C2/C4（队列双detail处旧写C3已被补审纠正），dummy凭据、本地区域与mock，禁止未mock的AWS对照。历史`sqs_v1`是另一套grader条件。 |
| **4 · 固定grader语义** | **mypy17071**；B2 `mypy17071-typeguard-unbound` | 先仅base/gold：补齐公开例必要imports/T声明，比较合法TypeGuard返回；增加“回调只含U、外层返回另一T”的真正未绑定负例。检验局部修复是否保留负面约束，不先造关闭检查候选。 | `install_wave1`派生镜像、原direct replay，只有wheel增层，无安装wrapper。固定实际桩、解释器和CLI；TypeIs有公开依据，分数不能独自裁决其范围。此项不验actor。 |
| **5 · actor开发，第二个DVC可延后** | **DVC6954**；B3 `dvc6954-public-param-workflow` | base/gold公开run/repro→lock→不变跳过→改值重跑，以-1和-0.5对照。补足原参考主要验证解析helper的边界，覆盖较5839更完整的项目工作流。无需先造整数专用部分修复。 | 本题`dvc_install_v1c/recipes/iterative__dvc-6954.json`；不能借5839的recipe/镜像身份。评分对照按B3冻结DVC代码归档与重定位summary，`RH2_DVC_REPAIR_ROOT`不能落回旧默认`dvc_install_v1`。 |
| **6 · 固定解析/评分控制，可独立先做** | **Pandas48106**；B2 `pandas48106-remaining-reference-aliases` | 对仍合并2/4个完整节点的两组tz别名，按真实-rA摘要次序比较全PASS、混合状态、缺成员。**先离线合成控制，无需pandas重编/容器**；区分“身份合并”与“实际错聚合”，不是候选能力成绩。 | 冻结本次parser/binding源码与原日志；保留现3组Period绑定。旧`resources_v1/code/rh2`精确本地副本未认证，当前代码诊断不能冒称历史字节重放。确需真实grader确认时才用本题`pandas_meta_v3` recipe＋bindings＋派生镜像。 |

完整命令草案、输入身份和判据沿 [B1队列](../cpu_queue.json)、[B2队列](../expansion/batch02/cpu_queue.json)、[B3队列](../expansion/batch03/cpu_queue.json) 的上述ID取用；本页不生成新CLI。3批候选依据分别见 [B1](../probe_candidates.json)、[B2](../expansion/batch02/probe_candidates.json)、[B3](../expansion/batch03/probe_candidates.json)。

## 暂定模型能力探针：四个主候选，一个同仓备选

仅按当前静态证据和最低准备负担排序，**均未准备就绪、未正式准入，也未选模型**：

1. **Conan15422**：公开字段目标清楚，原环境对照明确，先作范围有限的预设生成探针；默认与多配置覆盖仍有限。
2. **Moto5134**：公开null存在性和实际投递相符，暂未发现具体误拒/误收或gold回归，增加服务模拟类任务覆盖；先过实际actor开发检查。
3. **DVC5839**：明确的CLI参数传递任务，公开输出可廉价核验；能力解释限字典指标精度，不概括全部指标API。
4. **mypy17071**：增加类型分析/遍历任务，正负义务可区分；先收第4项结果，再验实际actor，保留TypeIs范围说明。
5. **DVC6954（备选）**：没有必须先修订的现证，完整参数工作流有价值；若只取3–4题，优先保留跨仓覆盖，延后第二道DVC。

Dask8597、Pydantic8511、mypy10424仍可随后考虑，但各自已指定语义对照尚未完成，不因旧“优先候选”顺序绕过新结论。Moto7584、Pandas50319/51605等明确规范冲突或gold边界题留作诊断，不先拿分数比较模型能力；未选不等于淘汰。

## 共同执行边界

沿 [CPU入口单](cpu_entry_plan.md) 和已验 [B1交接](cpu_queue_handoff_review.md)、[B2交接](batch02_cpu_handoff_review.md)、[B3交接](batch03_mypy_cpu_handoff_review.md) 的身份边界：薄actor入口尚待实现，需留实际agent/54321的HOME/cwd/shell/PATH、源码导入、可写/安装消费、候选生效和清理证据。grader/54322、补丁apply_user=54321或COPY wheels成功都不能替代它；BASH_ENV声明也不自动证明CC工具激活。固定grader/解析实验可先验本次有效条件，不必等待actor全面验收。

每次先明确复用历史冻结入口还是固定当前代码做新诊断，记录差异；旧`/work`路径、镜像/wheel可用性、实际code-root及补丁仍待落实。模型只读本题公开材料；本清单、审查笔记、gold/隐藏测试和CPU私有对照不交solver。运行后逐题决定下一步，不把时间或费用写成未实测估计。

本次只读三批最终交付、必要短卡及已验CPU交接，新增本页；未执行项目/测试/安装/网络/容器/SSH/模型，未兑换额度、改题或生产代码。

根于06:33 SGT回读并核对六个队列ID、关键变体/判据及13个文档链接，接受为待用户选择的后续建议；这次接受没有启动实验、批准模型或新增全跑要求。Moto5134仍按补审指定公开C4定位双detail示例，保留原队列C3笔误的更正说明，不回写已验历史文件。
