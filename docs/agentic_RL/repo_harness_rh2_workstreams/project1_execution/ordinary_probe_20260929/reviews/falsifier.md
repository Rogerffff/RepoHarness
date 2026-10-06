# 普通探针接缝：Falsifier / Simplifier 独立复核

日期：2026-09-29。审查范围：A 线 `root_git_boundary_fix_20260929` 的未提交公共修复，以及本批 readiness 的失败传播、冻结往返和评分信任要求。按 `review-standards.md` §10.4 分工；本报告是同模型独立分工，不冒称跨模型审查。未改生产源码、题目材料、评分算法或共享脚本；未连接远端、调用 API 或运行整池。

## 结论

**A 的公共窄修可以接受；旧探针不能仅因该修复通过就直接开跑。** 本轮独立执行屏障相关维护测试 **16 passed**，包含真实 Docker 的修前 root filter 正控和修后冻结导出。仍须迁移 SWE 自有 root Git 导出、给 R2E 传递实际 baseline policy，并关闭真实模型入口的 legacy Git 对照。

**失败传播与往返不一致是当前探针必修。** 我独立运行现有 `Matrix.main()` / `E2E.main()` 的真实控制流，将外部 I/O 换为内存桩，重现 grader fatal、清理未知及往返不等仍返回 0；matrix 还会评下一题。普通 0 分正控同样继续，所以不能用“出现非满分就停”替代修复。

**评分信任要求需要收窄，但不能取消。** readiness §3D 合理的要求是：先复验已展示的具体伪造方式在本批固定入口是否仍可达，命中后窄修或停止采信相应评分。若把它解释为“普通探针前消灭任意候选程序对同进程测试的影响”，则超出当前已批准边界，也没有有限验收条件。既有 DR4 和 I08 决定明确保留同进程风险、保留合法 testing/helper 修改；最新“明确缺陷先修”不支持把已经实测的 reward 污染隐去，也不支持顺手发明新的 reward、通用作弊 0 分或全局文件通配排除。

## 1. A 公共修复：未发现需要阻塞本片的新问题

审查了实际 `quiescence_barrier.py` / `generate.py` diff：先停止 agent、按同一 policy 两次 census、最后交现有 exporter；缓存观测计数不进入稳定性指纹。正式物化选择一次 policy，基线和 FrozenWorkspace 保存同一个对象。现有未知类型/不支持路径仍交 exporter 分类，没有在屏障提前变成新 run-fatal。

独立测试：

```text
cd rh2
.venv/bin/python -m pytest -q tests/adapters/test_quiescence_census.py tests/adapters/test_f2_2b_barrier.py
16 passed in 12.43s
```

覆盖：root clean filter 修前确实写出 uid=0；修后停止、双读、完整性回读、冻结导出不再触发标记；ignored 二进制、执行位、普通软链变化保留；agent 后台进程被停止；三种任务 policy 运输；unsupported 仍到 exporter。证据 [pytest_barrier_rh2.txt](../../../../../../runs/ordinary_probe_20260929/reviews/falsifier/pytest_barrier_rh2.txt)。首次误用了根 `.venv`，因缺 `repoharness2` / asyncio plugin 收集失败；随后改用项目 `.venv`，没有安装依赖或改测试期望。

该证据不能核销：SWE 旧 `export_candidate`、R2E legacy compare、正式 R2E 直评的基线排除区差异、任意软链字节保真、训练吞吐。现有 `readlink | tr -d '\n'` 会删除软链目标内的换行，census 与内容抓取共享该旧问题；这不是 A 修复引入的回归，不能声称已关闭。若本批出现这类候选，必须停在导出保真处，不能当正常 noop/普通软链放行；其通用修复可独立处理。

## 2. 必修：把已有失败事实送到最外层

**F1 / P1，`production_reachable`。** 实际入口是 `run_matrix.py::Matrix.one → grade → main` 和 `r2e_probe_e2e.py::main/regrade`。普通 API 批次即将启用这些入口；本次控制流反例使用内存 I/O，不标成已在实际付费批次发生。

| 本轮注入 | 当前实测结果 | 违反的不变量 |
| --- | --- | --- |
| matrix grader `driver_exit=4`、fatal | 仍调用下一题评分；无 STOP；matrix exit=0 | 评分进程未正常收口不能授权下一任务 |
| matrix grader 清理未知 | 同上 | 未确认释放资源必须停止新派发 |
| E2E baseline/patch entries 不等，载荷摘要不等，grader exit=4 | `_clean=True` 就 exit=0 | 资源清理与候选身份/往返是不同事实 |
| matrix 正常 unresolved / reward=0 | 继续、exit=0 | 这是应保留的正控 |

证据：[probe_falsifier.py](../../../../../../runs/ordinary_probe_20260929/reviews/falsifier/probe_falsifier.py)、[probe_results.json](../../../../../../runs/ordinary_probe_20260929/reviews/falsifier/probe_results.json)。

**推荐 accepted，现在修。** 对已存在的进程退出码、driver 收尾摘要、最终 manager close、候选清理和往返结果作一次显式有效性判定；失败就持久化 STOP、非零退出并禁止启动后续任务。恢复分支也消费这些事实，不能找到 ledger 末行即跳过。无需新 owner、重试器或恢复状态机；直接 fail-stop 足够。首次故障合理频率未知，但会扩大付费损耗或把无效结果混入能力统计，且修复局部、成本低。

正常 0 分不是 infra；SWE/R2E 测试命令非零也不自动等于 driver fatal；来源规则允许期望 FAILED/ERROR 的 R2E。预算终止只要候选合法且链路按声明完整收口，仍须保留该候选。driver 异常、网关断流、轨迹缺失不能仅因 `result=ran` 被包装成有效求解。原始得分与“是否可采信”分开记录，不能把无效结果改成 0 或静默移出计划分母。

并发时 STOP 只保证不再派发**尚未启动**的任务；已经启动的任务必须按自己的生命周期收口。最小验收用 concurrency=1 精确证明下一任务未启动，再检查多槽位不新起任务、在途任务仍被清理；无需添加全局瞬时杀停能力。

## 3. 冻结往返：不能把整体摘要强行设为相等

**F2 / P1，`production_reachable`，属于 F1 的候选身份子条件。** R2E 求解侧 sanitize 与回放侧不同，已知 `.git/logs/HEAD` 排除路径差异会让完整 baseline manifest 摘要不同；它不证明评分树 entry 不同。因此不得把当前所有整体摘要不等都当成新错误，也不能从该例推出其它身份字段可不核。

最小核对内容：任务/公开材料、实际镜像 ID、工作目录、policy、materialized head / task base 等身份；基线评分树的路径、对象类型、mode、文件/软链摘要；冻结 patch 的操作、路径、对象类型、mode 和载荷摘要；提交给 replay 的 diff 与 ledger 所记 diff 摘要。缺任一必要工件或比较不等就 fail-stop。仅当前已解释的排除区差异单列，不能泛化豁免全部 baseline 差异。

SWE prep 可能修改初态，渲染旧字节必须来自**prep 后、模型前的实际树**；只按镜像重建旧字节会错。必须有“prep 改一处、模型改另一处”的正控，以及 ignored 文件、模式、普通软链的完整往返。noop 也应核基线和身份，不能把 `empty=True` 当作跳过全部校验的理由。

正式原始 frozen artifact 直评的基线一致性修复，可递延到该入口启用前；本批已验证的回放运输不需等它。原始求解冻结工件须保留，不得用回放重建物替换后宣称原始直评通过。

## 4. 评分信任：必须处理的具体问题与可递延范围

本轮用真实本机 pytest、固定不变的 `assert 1 == 2` 和当前 `parse_eval_log_r2e` 做了三个对照：

| 候选行为 | pytest 退出 | 当前 parser 是否 resolved |
| --- | ---: | --- |
| 无修改 | 1 | 否 |
| conftest 的 `pytest_runtest_makereport` 把 report 改成 passed | 0 | 是 |
| `pytest_configure` 提前打印同形 first summary，真实测试仍失败 | 1 | 是 |

原始日志与结果在上述 runs 目录。这是当前库/解析器接缝的独立证据，**不是 12 题完整 manager 实测，也不是实际普通候选已经作弊的证据**。真实入口可达性仍由候选投影、该题使用的 runner、材料版本共同限定。特别是本批 pillow `3ac9396e` 使用可信 unittest 自定义 runner，不能把 pytest conftest 反例原样算到它；numpy 的 `numpy/testing/` 属于可修改库辅助代码，不能因名称把合法解答冻结。

此前真实 RH2 证据还显示：只修改 `setup.py` 即可在安装期生成 `tests/conftest.py`，静态 `candidate_touched_conftest_or_fixture=[]`、runner 摘要不变也能拿到 1。见 [M2 §7](../../env_overnight_20260916/M2/M2_report.md) 和 [9/16 审查 §5](../../batch4_scoring_20260910/implementation_review_20260916/README.md)。因此以下方案不足：仅看候选路径标记、仅恢复隐藏测试一次、仅改 XML/JUnit、仅校验 pytest 自身包摘要，或在评分后“人工看一下”。

建议按以下**有限处置**收口 §3D，顺序不能颠倒：

1. 对本批最终固定的评分配方，复用已知三类反例：直接 conftest 改报告、安装期生成 hook、源码/配置期伪造摘要或段界。先做少量来源/runner 代表入口；只有同实现、同调用关系才可复用证据，unittest 入口另列。无需对每题穷举攻击。
2. 已定位为纯评分控制面的材料，从可信固定版本恢复/保护，并核对**安装后、测试启动前**的事实；合法库辅助代码与构建输入保留。若某控制文件同时是该题合法修复面，不能静默恢复候选，停止该入口并记录冲突。该修复由既有 grading/material owner 实施，不另建通用规则平台。
3. 探针消费者增加有限的输出一致性停止：已知假段界、外层摘要歧义等不得变成有效分数。只能对已验 runner 的完整日志形态作判定；嵌套 pytest 的 captured 输出、来源多命令日志、期望 FAILED/ERROR 都要有正控。**这不是把 parser 改成“取最后一段”或改 reward；是拒绝采信已证明歧义的运输结果。**
4. 以上已知反例若仍拿到可采信的 1，则该评分路径保持停止，保留冻结候选供修后重评。不能凭测试没有报异常继续能力比较，也不能先付费扩批后再补“事后审计”。如无法在既有职责下做有限修复，最小动作是停止该受影响评分能力，而不是扩大到完整防作弊平台。

广义的“任意被测源代码可以在测试进程里改变运行器内存或输出”仍是同进程信任残余。有限反例收口不等于它消失；若要改变该边界，需另列评分架构/语义范围，不能伪称当前 A 修复或本轮 probe guard 已解决。新的正式训练样本拒绝或作弊 0 分不是本批可以顺手引入的修复。

因此我不支持 readiness 一概阻止所有普通求解，也不支持按它当前的抽象一句话放行评分。**可以并行做安全链 CPU 验收与确定材料；普通能力比较的放行对象应是“固定入口通过其适用的已知反例及合法解正控”，不是“证明所有同进程代码都可信”。** 对未通过的路径保留计划项和无效原因，不悄悄删题改善分母。

## 5. 本批停止条件

- A 窄修已达停止条件，不扩大到新扫描器、全部 LF 路径合同、全库/全池或性能总审计。
- 探针接入后只复核：无结束后 root Git；实际 policy；SWE prep 基线；正常修改/noop、ignored 二进制、mode、普通软链的往返；失败、恢复和下一任务不启动；正常 0 分和合法预算终止仍保留。
- 评分按上节有限范围处理并记录 runner 适用范围。不能把低频、未实测的任意新攻击继续追加成无期限开跑闸门；已有具体反例未处置则不能宣布对应评分可信。
- 正式 frozen 直评基线、正式训练运输、token/logprob、全池环境质量、广义同进程防作弊、大仓库并发成本均不由本报告核销。

本轮初始源码摘要：[source_hashes_initial.json](../../../../../../runs/ordinary_probe_20260929/reviews/falsifier/source_hashes_initial.json)。后续实现变化须按摘要区分；修后只复核本批新增接缝，不重复整池测试。
