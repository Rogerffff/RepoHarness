# R2E 首批 8 题静态审查与 actor 接线复核（2026-09-25）

Codex A 主审；三个独立上下文分别追踪 actor、复核两组各四题的语义与原始证据。审查对象是 Claude 本批交付，不是重新派发公开解题，也不是训练准入验收。基线 HEAD `6526839f63e71915c055309f309ec14081668d21`，含 B 线未提交实现；输入摘要见 [快照](main/input_snapshot.json)。未改业务代码、维护测试、题面、评分材料或历史运行件；未新跑容器、模型、远端或操作机器，未提交。

**结论：主要接线和这批调查证据成立，可以保留静态校准成果；有一处接线缺口、两处诊断归因需修正。没有发现推翻本批 26 条评分数值的新 P0/P1。** numpy `18b7cd9d` 与 aiohttp `61833518` 仍是附条件的诊断探针候选；不能因此宣布 R2E 正式运行、训练或留出评测已就绪。

## 1. 需处理的事项

| 编号 | 优先级 / 性质 | 最小处置与完成时点 |
| --- | --- | --- |
| R1 | P2，接线 | orange3 mr-020 必须绑定已批准的依赖配方；只检查 `+env_v2` 不充分。下次重建或运行该题前补齐 |
| R2 | P2，诊断判读 | pandas / orange3 / scrapy 的失败键组合只标“疑似规格争议”，不能直接免除能力失败。首次用这些规则汇总模型结果前修正文档 |
| R3 | P2，结论口径 | pillow P1 属于“遵循冲突示例”的候选，不能无条件计入完整合理修复被误拒。发布本批结论时单列 |
| O1 | P3，非阻塞 | overlay 校验与解析读了两次文件。可顺手改成解析同一份已校验字节；冻结输入下不阻塞本批 |
| 已登记依赖 | 非本轮新发现 | A 线 E2b root PATH 修复、真实 Qwen/adapter 与完整正式执行链核对，仍在正式 R2E 模型运行前落实 |

### R1：安装步骤名不能代表批准的 SciPy 配方

- **当前行为 / 位置**：`rh2/src/repoharness2/envpack/environment_overlay.py:35–55` 将 `r2e-mr-020` 映射到字符串 `+env_v2`；`build_r2e_derived.py:477–502` 按步骤名生成这个后缀。实际依赖内容只进入 `recipe_sha256`，而 `prepared_task_face.py:387–409` 的共同消费检查未用它核对批准配方。
- **应保持的不变量**：mr-020 将两个期望改为 PASSED，依据是该题换成了批准的 SciPy 1.5.4 环境。`env_v2.sh` 是支持旧 Python 的通用安装脚本，不代表装了什么依赖。
- **独立反例**：调用真实 `load_env_pins` / `build_one`，给 orange3 一份有效的 hypothesis wheel 配方并仍选 `env_v2.sh`。该输入通过材料 guard，到达第一条 Docker 操作；不给环境步骤的负控则在此前被拒。两者与正确 SciPy 配方的步骤名相同，内容摘要不同。**探针在 Docker 边界停止，没有实际构建错误镜像**；源码后续只核安装结果是否符合输入自身的 pins，仍不核 mr-020 要求。
- **可达性 / 影响**：`production_reachable`，入口是现有 `--env-pins` 配置，不需伪造 overlay。误配可能让新期望配上旧 SciPy，污染该题 reward；上轮已有真实旧环境日志在新期望下为 11/13、0 分。**本批 derived7 使用正确配方，现有结果不受影响。**
- **最小修法**：复用现有配方内容身份或显式批准的依赖事实，让构建、回放、actor 共用同一个真实要求；不新增运行期依赖扫描、重试或状态机。这是落实已批准材料与环境的对应关系，不需要新 T0。
- **验收**：正确现存配方通过；旧配方、`env_v2 + hypothesis`、`env_v2 + 错误 SciPy` 都不能成为该修订的有效输入；无此修订的 numpy 配方保持原行为。错误应在启动前暴露，不转成候选 reward=0。
- **证据 / 复现**：[actor 报告 §2](actor/README.md#2-finding-a1修订依赖绑定的是安装器名称不是批准的-scipy-配方p2)、[主审复跑结果](actor/probe_runs/1d3ece3029c3/probe_actor_binding.json)、[CPU 探针](actor/probe_actor_binding.py)。owner 建议仍为 B 线覆盖表生产者，A 复核共同消费点。

### R2：相同失败键，可能来自合理替代解，也可能来自错误实现

当前建议的三处自动归因：

- orange3 `9b5494e2` 的 `review.md:210`：原例能跑、`test_probability` 通过、只错 `test_auto_solver`，就归“接口不符”而非“未修复”。
- pandas `32dd55cb` 的 `card.md:60`：T1 通过、只错 T2，不计能力失败。
- scrapy `9a15fcf8` 的 `card.md:91` / `screening_record.json`：只要两键从 FAILED 翻成 PASSED、其余一致，就记“过度修复误判”。

**反例已经足以否定这个充分条件：**

1. **orange3 W1 是本批真实评分。** 它只错 `test_auto_solver`，12/13；`test_probability` 已通过。但补丁把用户指定的 `penalty='l1'` 静默换成 `l2`。主审执行原方法的参数探针也得到 l2。这是没有满足题意的错误修复，不能因为失败位置相同，就与 V1/V3 一起免责。W1 的完整 iris 示例本轮未重新拟合，“例子不会报错”是静态推断，不能冒充新实测。
2. **scrapy 的独立 CPU 反例**在 gold 表项之外把 `Headers.normvalue` 改为返回 str。七个隐藏方法都通过，正好两键与 FAILED 期望冲突；但公开 `HeadersTest.test_single_value` 的 bytes 契约失败。它只改源码，仍能命中 A′。这是原件 AST 的隔离探针，**不是新增真实 grader 行**。
3. **pandas 的静态同类反例**只给 C1 增加 `name == 'mean'` 条件：目标 mean 通过、T2 保持原失败，但题面同属数值归约的 sum 仍坏。该组合未实跑，只作遗漏路径说明。

**影响 / 可达性**：这些是建议的诊断统计规则，尚未发现已经按它们错误汇总模型能力。若直接使用，会把部分错误解移出失败分母。原始 reward 正确落账，不需要改 grader。

**最小修正与验收**：失败键模式只筛出“疑似规格 / 期望冲突”；保留 raw reward，再核公开要求、候选语义与受影响的旧行为，才给合理误拒标签。W1 必须仍为错误解；scrapy 的正常边界解码 P4 与破坏 Headers 的变体必须分开。pandas C1 的具体分析可保留，不能推广为所有 T1 过 / T2 败的补丁。同步最新题卡、结构化记录和汇总页，封存初判不回写。

证据：[语义 A §3](semantics_a/report.md#3-f1--p2失败键只能定位待复核样本不能直接免除能力失败)、[语义 B §2](semantics_b/review.md#2-两项需修正的归因)、[原方法参数探针](semantics_a/audit_results.json)、[Scrapy 隔离反例](semantics_b/semantic_probe.json)。owner：B 线静态审查协调者；在产生模型能力统计前收口。

### R3：pillow P1 证明题面冲突，不能无条件证明正确解被拒

`r2e_static_review_20260925/README.md:49,87` 与 `grader_candidates.md:85` 仍将 P1 放进“合理误拒已执行证实”的总数。虽然新版已注明 P1 只符合示例读法，主结论仍过强。

公开题面一处要求 `formats` **限制格式**，另一处要求 PNG 用 `['JPEG']` **成功打开**。P1 的“失败后再试所有格式”符合后一句，违反前一句；它也没有实现题面另一条 `show()` 警告要求。实际 54/55、0 分核对成立，但运行本身不能选定冲突规范的优先级。

最小修正：将 P1 单列为“遵循冲突示例的候选被拒”；保留题面矛盾、`needs_review`、诊断用途和 T0-3。不能靠 gold 能否做到来选择哪条公开要求有效。若保留宽口径总数，必须显式包含争议解，不能再称它们全部完整满足题面。**不需要重跑评分。** 原始题面、补丁与日志定位见 [语义 B B1](semantics_b/review.md#b1--p2pillow-p1-的合理误拒只能附带题面读法)。

审查期间作者已把早报的“8 个”改成“7 个”，排除了有争议的 V7，并注明 orange3 V1/V3 原例实测、V4/V5 静态推断。这些更正接受，不重复报为未修项；R3 是更正后仍需区分的含义。

## 2. 两道探针候选与其余题的处置

| 题 | 本次裁定 | 下一步边界 |
| --- | --- | --- |
| numpy 18b7cd9d | 附条件诊断候选成立；只特判 None、退回对象身份两种错误实现确实得 1 | 对模型补丁逐项检查 None / 普通对象 / 等值不同对象 / 不同长度比较，不因一个异常跳过后续项；不强制照 gold 返回 NotImplemented |
| aiohttp 61833518 | 附条件诊断候选成立；AP1 满分但提前终止响应的证据成立 | 首次生成后检结果前落实完整 C3；保留原始 reward 和后检结论两列 |
| pandas 32dd55cb | 公开旧报错文字与隐藏 T2 冲突成立；C1 91/92 已测 | 放宽文字与补测试是可讨论修订；新断言应覆盖非 mean 归约，不仅含 NA 的 mean。R2 自动归因撤回 |
| coveragepy 5dbbe143 | 未定义去重键造成歧义；过粗实现 CE4 满分的漏测成立 | 澄清题面或隔离；仅修题面不会补上“不同警告首次都应显示”的保护 |
| orange3 9b5494e2 | V1/V3 有较强合理误拒证据；V4/V5 评分已测、原例仍含推断；同仓快照暴露成立 | 行为级测试比把 `auto` / 私有钩子硬写进题面更能保留解法空间；保留 L1 要求，不能只检查不报错。R1/R2 先收口 |
| pillow 2b061b68 | 题面矛盾、P2 首次打开回归、P3 警告漏测均成立 | 修题面方向合理，但它消除不了 P2/P3 漏测；按 R3 收窄汇总，不直接进训练 |
| scrapy 9a15fcf8 | 旧 P4 的合理修复被死键期望惩罚成立 | B（同时删测试与对应 expected）或 D（隔离）可交用户决定；只删 expected 会留下 unexpected 键。按 R2 修诊断规则 |
| orange3 22e98f8f | 题面函数的可执行 body 与 gold 相同；不宜作为当前能力题 | 修订或移除泄漏代码后核公开产物和真实消息，不能仅凭再次 gold=1 验收题面修改 |

**aiohttp C3 的具体缺口**：当前实跑脚本只判断正文不以 `0\r\n\r\n` 开头，空正文、错误正文、缺终止块也能通过。本次直接解析已保存的 gold/AP2/AP1 输出：完整分块、唯一正确终止、解压回原载荷时 gold/AP2 通过、AP1 失败；同一压缩流合法改为 2+4 分帧仍通过。按这个语义实现后检，不能要求字节串等于 gold。README 已提出语义 C3，题卡 / JSON 尚有精确字节或旧“待运行”文字，应整理当前口径；这不是要求重写封存初判。[可复用的 CPU 反例](semantics_b/semantic_probe.py)

**方法评价**：公开阅读 → 私有初判 → 历史对照 → 独立复核 → 候选实跑的组合有用，这次同时找到了误拒、漏测、题面泄漏和记录复制错误。值得继续使用。需调整的是结论强度与诊断归因，不能从“找到了一个合理替代解”推广成“同样失败形态都合理”。已知线索 6 题与对照 2 题不是随机样本，不能用 8/8 needs_review 估算全池坏题比例。

## 3. actor 接线接受到哪一层

```text
miles rollout actor
  → BringupService 持有 PreparedTaskFace
  → prepared / host grading / overlay 载入与静态互检
  → rollout spec（派生 image ID、.venv 激活）
  → RolloutOrchestrator → lease / 容器 → ClaudeCodeDriver
  → 同一 task face 的 grading spec（同一派生 image ID）
  → GradingManager 报告 → miles 组与训练转换
```

调用链和所有权逐行追踪见 [actor 报告 §1](actor/README.md#1-正式调用链与所有权)。新配置由每个 rollout actor 进程的 service 构造时读入，未引入新执行期 owner、队列或重试。镜像按不可变 image ID 启动，缺覆盖条目在构造期拒绝，不回退到来源镜像；这恢复隐藏测试与修复提交的既有隔离边界，不是本轮过度防御。

| 跨切片不变量 | 核对结果与限制 |
| --- | --- |
| rollout 与 grader 使用同一派生环境 | 真实 PreparedTaskFace + 实际 derived7 条目的 CPU 构造通过；8 次 CC 容器均按记录的派生 ID 启动 |
| 缺记录 / 错来源 / 错隐藏树不进入候选 | 定向维护测试通过；不是 reward=0 或静默 fallback |
| mr-020 与批准依赖对应 | 旧无 env 条目现在拒绝，但 R1 仍未完整实现 |
| 新提示不改变评分材料 | 48 public 行只变 public_hints；48环境包只变 public_bundle_digest；grading/validation 文件字节相同，见[独立比较](main/hints_only_comparison.json) |
| R2E 与 SWE 的组运输维持规则 | 本轮复跑真实 manager 报告到 buffer/转换的两项维护测试；同批分组允许、混来源单组拒绝 |
| 新拒绝的分布影响 | 只拒绝缺失或不配套的运行输入，应修任务输入；不拿这类拒绝代表模型失败或题目难度 |
| 真实完整运行 | 8 次为真实 CC + 桩模型 + 正式启动组件；未经过完整 service/assignment/orchestrator，也未通过 Qwen adapter，不是正式模型求解证据 |

**运行前的已有依赖不能遗漏**：A 的 [infra 09-25 记录](../infra.md) 已将 E2b（root 可信 PATH）列为 R2E 正式运行前修。派生镜像将 agent 可写的 `.venv/bin` 放进 PATH；root census/抓取等不能从那里解析命令。这项由 A 继续处理，本轮不重复开单。随后首个真实模型小样需核实际 actor 进程取得 overlay 路径/摘要和本机 image ID、捕获完整真实题面、走通 adapter 与正式装配评分。无需为本批静态结论先跑八卡训练。

正式 `generate` 未重复 devcheck 的 R2E 三项预检，是已登记的覆盖边界；在批准镜像和可信构建产物已有证据的情况下，不要求机械加入每次相同检查。是否复用轻量预检由 A/B 按最终入口决定，不能用桩验证替代未经过的 adapter。

## 4. 独立验证与上轮收尾

本轮运行与检查：

| 项 | 结果 |
| --- | --- |
| 5 份相关维护测试文件 | **66 passed**；[输出](../../../../../runs/r2e_static_actor_review_20260925/targeted_tests.txt)。未用作者的全库计数代替独立复跑 |
| 本批评分账本、patch SHA、log SHA、当前 parser/expected 重算 | **26/26 一致**，6 题；22条人工构造候选、4条gold；16个1、10个0。账本 `kind=cc` 不表示模型生成 |
| scrapy P4 | 另核一条09-24阶段的既有证据，不混进本批26条；本批无新的scrapy评分 |
| 真实 CC 开发证据 | 8题、47条 Bash 命令（含预检）；命令均执行，镜像/解释器/身份与清理记录相符。公开测试的既有失败如实保留 |
| 激活文件权限 | 8题 prelaunch 都以agent实际写入被拒；7题另有CC Bash层复测。pandas那一字段false是未输出标记，不是可写反例 |
| 上轮材料 verify F2 | 真 CLI 的独立临时夹具：正常rc0；改内容、缺文件、多文件、变软链、缺镜像输入均rc1；**关闭** |
| 上轮环境绑定 F1 | 原始无env条目拒绝已修；绑定真实依赖的余项见R1，不能只据步骤名关闭 |
| pandas 环境记录 | 接受恢复未完成项及 **32/2/9/5** 更正。上轮机械核对只证明记录计数一致，未证明每个“已解决”标签的语义；这次题级复核发现的复制错误应保留在更正记录 |

数据与探针入口：[主审逐行重算](main/saved_evidence.json)、[verify反例](main/verify_followup.json)、[actor证据](actor/existing_evidence_audit.json)、[语义A](semantics_a/report.md)、[语义B](semantics_b/review.md)。主审复跑了R1真实构建边界、W1原方法、Scrapy原件AST和C3语义反例；没有把隔离函数探针写成Docker或数值拟合实测。R1审查脚本首次复跑因一次性prepared输出已存在停止，改用每次新目录后通过；未改业务行为。

维护测试复跑命令（`rh2/` 目录）：

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/adapters/test_r2e_actor_task_face.py \
  tests/adapters/test_r2e_replay_overlay.py \
  tests/envpack/test_build_r2e_derived_env.py \
  tests/envpack/test_ingest_r2e_subset.py \
  tests/adapters_miles/test_r2e_group_transport.py -m 'not docker'
```

**故障与资源边界**：本轮核新输入缺席/错配、材料损坏、错误候选与输出歧义；未改清理状态机，复跑的既有回放测试覆盖异常停批、迟到清理与日志保留。没有重新做crash/restart/queue-full压力、GPU超时或内存测试，也不据此核销这些子系统。这里新增逻辑在加载期，无新的热路径队列；构建与评分性能沿用已有测量，未增加性能结论。

## 5. 可递延事项、建议顺序与停止条件

**O1：overlay读取。** `load_overlays_input` 先读bytes核摘要，再按路径重新解析；子审用现有两份真实overlay做交错，能选中与外部摘要不同的那份。没有本批运行中并写的证据。主审接受为 **P3非阻塞**：正常冻结作业输入不会触发；若允许在运行启动时消费可更新的构建目录，就在此前改为直接解析已校验的bytes，不加锁/重试。详情和边界见 [actor报告§3](actor/README.md)。

建议按下面的小步推进，不再把所有工作并成一次“大验收”：

1. B 先改 R2/R3 的当前结论，补齐 aiohttp 语义 C3 与 numpy逐项后检的实际判读步骤；按当前证据同步题卡/JSON的旧状态，不改封存初判。
2. B 窄修 R1；A 继续 E2b。R1不影响两道无材料修订的候选，不需要为它重跑48题。
3. 满足已有正式入口条件后，用 numpy/aiohttp 做小规模真实模型诊断；保存完整题面、环境版本、原分与独立语义检查，不能把静态候选直接变成训练/测评分母。
4. 其余T0给用户具体修订草案。推荐先处理有明确需求依据的题面矛盾和行为测试；“改题面就能消除全部漏测”不成立。orange3直接公开内部实现接口与改行为测试是不同选择，不能替用户混为一个决定。
5. 可继续后续静态小批；新公开材料应用更新后的提示，沿用先独立判断后看历史。此次未启动余40题。修改任何评分材料后，只针对受影响题重跑能区分正误的候选。

**停止条件**：R1用正确/错误环境正反控收口，R2/R3完成有证据等级的文档更正；两道后检满足已列反例即可，不要求重复全池评分或穷举所有输入。跨题源码包含答案的事实成立，留出集优先按仓库隔离；若用时间划分，仍须核训练快照是否包含留出修复，不能只按日期排序就认定无泄漏。

审查标准复盘：命中D/F/G/H（真实配置与材料绑定）、A/E/B/M（观察结果不足以决定语义/统计标签）、I/K（局部修复、避免扩成新平台）。无本轮需要新增审查维度的遗漏。当前材料验证、启动组件验证与真实模型端到端验证分层保留；不以维护测试通过扩大验证范围。
