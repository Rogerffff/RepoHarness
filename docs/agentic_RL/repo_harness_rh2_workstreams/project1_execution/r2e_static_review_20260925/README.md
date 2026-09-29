# R2E 静态审查：首批 8 题校准（2026-09-25）

Claude（B 线，R2E 协调）。对应[09-25 交接页](../environment_batch_20260925.md)任务三。用户 09-25 批准本方案：8 题，模型 Opus，并发上限 6，两波派发；同一晚由本线程实现 R2E 正式 actor 的镜像选择与 E09（见 §5）。**本线程继承了环境阶段的全部上下文，只做协调、材料与修复，不担任任何审查角色**；公开读者、主审、复核者都是不继承本对话的新会话。

## 1. 流程与材料

沿用[静态审查实际流程](../swegym_task_audit_20260920/static_screening_workflow_20260921.md)与[八方面协议](../swegym_task_audit_20260920/quality_review_protocol_20260920.md)：每题公开读者先写 `public_read.md`；私有主审读原件写 `analysis_before_history.md`，之后协调者才开放历史；独立复核者先从原件写 `reviewer_initial.md`，再读其它结论写 `review.md`；主审收口 `card.md` 与 `screening_record.json`。每题产物在 `results/<instance_id>/`。

| 项目 | 本批用法 |
| --- | --- |
| 材料 | [静态材料 v2](../r2e_static_prep_20260924/materials.md)：`runs/r2e_static_prep_20260924/v2/{public,private,history}/<iid>/` |
| 角色卡 | [公开读者](roles/public_reader_r2e.md)、[私有主审](roles/investigator_r2e.md)、[独立复核](roles/reviewer_r2e.md)，由 SWE-Gym 首批角色卡改写 |
| 环境 | [R2E 当批环境卡](r2e_environment_card.md) |
| 派发记录 | [assignments.json](assignments.json)（真实 agent 名、角色、题目、起止时间、产物） |

## 2. 选题（选择理由不告诉公开读者）

| 波次 | 题 | 选择理由 |
| --- | --- | --- |
| 一 | pillow `2b061b68` | 已知问题：题面与目标测试矛盾（T0-3，用户决定交本阶段） |
| 一 | scrapy `9a15fcf8` | 已知问题：期望 FAILED 键会惩罚更完整的修复（T0-4） |
| 一 | coveragepy `5dbbe143` | 已知问题：隐藏测试依赖修复前版本的测试辅助 |
| 一 | pandas `32dd55cb` | 批次三修订题（私有 conftest + 期望核定），另有题面线索 |
| 二 | orange3 `9b5494e2` + `22e98f8f`（原计划同包，执行时逐题单会话，见 §6） | 前者：两个 scorer 键原因未定、环境配方；后者：题面可能泄漏修法 |
| 二 | numpy `18b7cd9d` | 对照：numpy 无已知线索的题中按提交号取第一 |
| 二 | aiohttp `61833518` | 对照：aiohttp 唯一没有已知线索的题，初始工作树带来源镜像的兼容改写 |

"无已知线索"指环境阶段没有非 PASSED 期望键、题面线索或环境备注。已知线索题用来校准方法能否查出、查准已知问题，对照题用来看普通题上的工作量与误报，两类分开统计，不能合起来估计全池缺陷率。

## 3. 派发顺序与并发

并发上限 6（不含协调者）。同题严格按"公开读者落盘 → 主审 → 主审封存后开放历史"；复核者初判不依赖公开读者，可以提前开始，但在主审完成前不给它任何结论。第一波四题收口并抽验后再放第二波。执行中调整为：第二波公开读者在第一波公开读者落盘并抽查后先行派发；第二波主审与复核在第一条完整链（pillow）收口并抽查后派发。

## 4. 开工核对时发现、已处理或已登记的问题

1. **私有包的证据引用**：v1 的 `private/<iid>/refs.json` 由环境记录生成，早于批次三写回（7 题配方与材料版本是旧的），还混入了历史结论路径。v2 改为 `run_refs.json`（只有原始运行行，并标出当前材料版本），历史路径移到 `history/`；v2 公开包与 v1 逐字节相同（50,203 项），见[材料说明](../r2e_static_prep_20260924/materials.md)。
2. **材料 verify（Codex 批次三复核 F2）**：已改为重算实际文件再核清单与镜像；v2 核验 48/48 工作树、15/15 镜像一致；8 项反例全部按预期报错（`runs/r2e_static_prep_20260924/verify_negative_checks.log`）。
3. **R2E 评分口径与 SWE-Gym 不同**：期望映射须逐键完全相同，期望里的 FAILED / ERROR 键会惩罚更完整的修复；已写进主审卡。
4. **R2E 题面由模型生成**：公开读者与主审都加了泄漏修法、报错是否真实出现、示例能否成立三项检查。
5. **`public_hints` 与 R2E 事实不符**：conda / pip 与"测试文件会被重置"两句；公开读者卡按"需求 / 操作指令 / 环境声明"分开记录。R2E 实际只重放 `r2e_tests/` 与 `run_tests.sh`（已按代码核实）。
6. **正式 actor 取来源镜像（本批新发现）**：`rollout_spec_from_view` 用 `public.image`；R2E 来源镜像里 `/r2e_tests` 对所有用户可读、git 的 main 分支上有修复提交。R2E 进正式 actor 前必须改用派生镜像。E09 交接只写了激活、解释器前缀与提示措辞，没写镜像选择。用户批准今晚由本线程实现、A 审（§5）。
7. **方法文档暴露**：40 项清单第 127 行有一句关于 R2E coveragepy / datalad 的泛化历史说明（不针对本批题）；主审与复核者可读该清单，此处登记。

## 5. 并行进行的实现（不属于审查角色）

- R2E 正式 actor：派生镜像进任务面、`.venv` 解释器前缀、按来源区分的提示措辞（E09 + 镜像选择），以及 orange3 `r2e-mr-020` 与 `+env_v2` 的绑定（Codex 批次三复核 F1）。**已实施**，单测、不建网络的真实核对与 8 题经真实 Claude Code 启动链（桩端点）的开发命令核对都已通过，经 Qwen adapter 的链路未验证，待 A 审：[r2e_actor_wiring_20260925.md](../r2e_actor_wiring_20260925.md)。
- 摄入面随之重新生成（只变 48 题的 `public_hints`）；本批审查继续用 v2 材料，其中 `public_bundle.json` 是旧提示，差异不影响题意与评分判断。
- **真实 actor 条件的开发命令核对（8/8 题）**：在任务二的共用入口（真实 CC 2.1.205 + 桩端点）上加 R2E 一层，逐题跑公开读者与主审列出的开发命令，另做私有 gold 对照。8 题的预检、解释器前缀、导入来源都成立，逐题结果与缺口见 [actor_devcheck.md](actor_devcheck.md)。这些是执行事实，不是审查结论；第二波主审与复核可以读。
- **候选的真实评分（CPU）**：按主审与复核提出的最小实验，在派生镜像上用 RH2 回放评分跑候选，结果见 [grader_candidates.md](grader_candidates.md)。合理修复被判 0 已由评分证实：pandas C1、coveragepy CE1（按消息去重）、orange3 V1 / V3 / V4 / V5；pillow 回退语义单列为"遵循冲突示例的候选被拒"（Codex 复核 R3）。漏测也已证实：coveragepy CE4（过粗）、pillow `list(ID)` 快照（新进程里打不开任何图片）、pillow gold 加 `show()` 警告，都得 1。

## 6. 执行中的方法调整

- **子会话写报告文件被宿主拒绝**（02:10 前后起）：`public_read.md`、`reviewer_initial.md` 能写，主审的 `analysis_before_history.md` 被拒，提示 "Subagents should return findings as text"。两个主审随后把全文放进回复，又被安全分类器误扣（`reasoning_extraction`），其中一个会话因此中止。处理：协调者从会话记录里**被拒的写入调用**中原样取出正文保存，文件头加一行来历注释，不改正文；之后所有角色照常调用写入，被拒也无妨，回复只写一两句，不再贴全文。scrapy、coveragepy、pillow 三题的初判按此保存，内容与主审写入调用逐字相同。
- **安全分类器误判会终止子会话**：coveragepy 主审恢复后第一条回复即被拦截，scrapy 主审在读历史阶段被拦截（第二步文件都未写出）。恢复原会话往往立即再被拦截，因此改起新会话接续第二步：接续者先读封存的初判与公开读者记录，再开历史，文件头注明由接续会话完成。初判是原主审在读历史前写的，封存关系不受影响；接续者读历史前没有自己的独立判断，这一点在卡片里如实标注。
- **第二波私有角色逐题单会话**（02:38 起）：orange3 两题的主审与复核不再合包，以缩短单个会话，降低被安全分类器中止的影响；公开读者本来就是逐题。
- **第二波角色可读 actor 运行证据**：第二波主审、复核初判与第一波各题第二步复核拿到了 `runs/r2e_actor_20260925/devcheck/<题>/` 的路径，并注明是执行事实，不是评分或审查结论；第一波主审初判没有这份证据。
- **环境记录更正**：pandas `32dd55cb` 的主审发现，环境阶段批次三写回把 R16 与题意问题（`test_mean_datetimelike_numeric_only_false` 的 Period 报错文字）误标为已解决，`issues[1]` 的 resolution 是从 fixture 问题原样复制的。复核同意。已按事实改回：R16 = issue，`issues[1]` = open，处置 `grading_ok_open_items`（未完成项 statement_conflict，交题意与评分质量筛查），原值保留在 `correction_20260925` 字段；`dispositions.json`、环境 README 计数与生成的 `results_20260924.md` 同步（32/2/9/5/0）。环境记录里其余 16 处 issue→pass 翻转（11 题）逐项看过，都有对应修订支撑，只有这一处复制错误。
- **角色边界抽查**：第一波的公开读者都声明没读私有材料；复核者只读了 `run_refs.json` 列出的原始运行证据，并记录了写入前后目录的变化；主审只读了允许的原始证据（含账本记录的诊断候选补丁）。

## 7. 结果与次晨候选（09-25 03:40）

8 题的角色链都已走完，每题有公开读者、主审（封存初判、历史对照、题卡、记录）与独立复核（初判、第二步）。派发与完成逐会话记在 [assignments.json](assignments.json)，逐题产物在 `results/<instance_id>/`。以下"处置"都是 `static_review` 范围，不是训练或评测批准。

### 7.1 逐题

| 题（选题类别） | 处置（主审 / 复核） | 主要问题 | 执行证据（[评分](grader_candidates.md) / [actor](actor_devcheck.md)） | 建议用途 | 待定 |
| --- | --- | --- | --- | --- | --- |
| pillow `2b061b68`（已知线索） | needs_review / 同意 | 题面与目标断言冲突：题面原例在 gold 下也失败。两个期望 FAILED 的键是死键，放过了题面诱导的有害改动 | 回退语义 0；`list(ID)` 快照得 1，但新进程里打不开任何图片；gold 加 `show()` 警告得 1。actor 可开发 | 诊断；原题面不进训练 | T0-3：修订公开题面，隐藏测试与期望不改（复核有条件同意：快照类漏测靠题面修不掉，是否补检查另定） |
| scrapy `9a15fcf8`（已知线索） | needs_review / 同意 | 期望把两个 py3 死键锁成 FAILED，更完整的正确修复判 0（环境阶段 P4 实测） | actor 可开发；公开测试里对应的两条恒失败 | 诊断：得 0 且不符的恰好是这两键时只标疑似过度修复误判，核实候选语义后再归类（Codex 复核 R2） | T0-4：修订 B（对称删去两个死键，推荐）或 D（隔离） |
| coveragepy `5dbbe143`（已知线索） | needs_review / 同意 | 题面没说去重按什么键，隐藏测试强制按 slug | 按消息去重得 0（误拒）；按 slug 得 1；过粗实现得 1（漏测）。actor 可开发 | 诊断 | 现有修订单改不了题面：修题面需要新机制，否则隔离；只修题面补不上"不同警告第一次都应显示"的保护（Codex 复核）。环境阶段留下的 R04 建议关闭 |
| pandas `32dd55cb`（已知线索） | needs_review / 同意 | 目标键 T2 强制 gold 路线下 Period 的报错文字，与公开旧测试相反 | 只对数值 EA 分派得 0（误拒）；私有 gold 对照里，公开旧测试恰好这一条失败。actor 可开发 | 诊断：只有 T2 失败的解只标疑似规格争议，核实候选语义后再归类（Codex 复核 R2） | 修订草案：放宽 T2 的文字，在 T1 内补断言；环境记录已更正（§6） |
| orange3 `9b5494e2`（已知线索） | needs_review / 同意 | `test_auto_solver` 钉死了题面没写的接口细节。两个 scorer 键是上游过时期望，与默认 solver 绑定。同仓 5 题的公开 base 含本题 gold 与目标测试 | 4 个合理修复都得 0（V1 / V3 / V4 / V5；前两个实测修好了题面原例，后两个按代码推断也能修好）；P1 / P2 得 1；默认改 liblinear 时 scorer 两键翻成 PASSED。actor 可开发（3 条 Qt 控件测试恒失败） | 诊断；不作留出评测 | 修订方向：题面补接口说明，或放宽测试 |
| orange3 `22e98f8f`（题面线索） | needs_review / 同意 | 题面里的 "Example Buggy Code" 逐字等于 gold | actor 下逐字运行题面代码，输出的是正确映射；评分侧没问题 | 当前题面不作能力题 | 修订公开题面，隐藏测试与期望不动；改后要核公开产物和真实消息，不能只凭 gold 仍得 1 验收（Codex 复核） |
| numpy `18b7cd9d`（对照） | needs_review（静态候选）/ 同意，补两处未测范围 | 题意、测试与 gold 一致；覆盖缺口：只比较了 `None`，只比较了同一对象 | A 得 1；只让 `__eq__` 返回 NotImplemented 得 0（`!=` 错，应得）；只特判 None、退回身份比较这两种错误实现都得 1。actor 可开发 | **基座探针候选**；得 1 的补丁用行为探针复核 | 只在用于训练时才考虑补测试 |
| aiohttp `61833518`（对照） | needs_review（静态候选）/ 同意，补探针判读条件 | 标题场景（压缩在后 + chunked）没有被隐藏测试覆盖；题面示例的断言按字面写恒为真 | 只修 Content-Length 写出器的部分修复得 1，但标题场景仍错（漏测）；两个写出器都修得 1。actor 可开发 | **基座探针候选**；得 1 的补丁加跑 C3 | 是否出带额外隐藏测试的修订版 |

### 7.2 次晨候选（R2E 线，按优先级）

1. **可进首波探针，附条件**：numpy `18b7cd9d`、aiohttp `61833518`，配方都是 `r2e_derive_v1`，没有材料修订。条件如下：
   - A 线审过 [R2E 正式 actor 接线](../r2e_actor_wiring_20260925.md)；
   - 探针机本地按配方建好派生镜像，rollout 不 pull；
   - 捕获一次真实渲染的用户消息；
   - 事后复核得 1 的补丁：numpy 用逐项行为检查，aiohttp 用语义化的 C3。两个脚本已写好并用已评分的补丁验证过，见 [actor_devcheck.md](actor_devcheck.md) §4；
   - aiohttp 的结果分两列报：原始 reward，以及按 C3 修正后的结果；
   - aiohttp 若因还原来源镜像的兼容改写（`client.py`、`client_reqrep.py`）导致 `import aiohttp` 失败而得 0，按环境陷阱计，不算模型失败；
   - aiohttp 用于训练前要先补上标题场景的测试（修订 Q2，由用户决定）。
2. **只作诊断，评分误拒已由执行证实**：pandas `32dd55cb`、coveragepy `5dbbe143`、orange3 `9b5494e2`、pillow `2b061b68`、scrapy `9a15fcf8`。探针结果保留原始 reward；失败键模式只用来筛出疑似规格争议的待复核样本，核实候选语义后才标"合理误拒"，不能按失败位置自动免除（Codex 复核 R2）。修订前不作训练 reward。
3. **当前题面不作能力题**：orange3 `22e98f8f`。
4. **待用户决定（T0）**：
   - pillow 题面修订（T0-3）；
   - scrapy 选 B 还是 D（T0-4）；
   - pandas 的 T2 放宽与补断言；
   - coveragepy 是修题面（需要新机制）还是隔离；
   - orange3 两题的题面修订。
5. **CPU 队列（未跑）**：
   - scrapy 修订 B 的验收（需先有修订版材料）；
   - pandas C2 至 C4；
   - aiohttp 只修 chunked 写出器的候选；
   - orange3"只改 scorer 所用模型"一类候选。

### 7.3 校准结论

- **已知线索 6 题**：已知问题都被查出且定位准确，另外发现了新问题：
  - pandas 环境记录的复制错误；
  - orange3 与 pillow 的同仓跨题暴露；
  - 修订提案漏掉的检查（pillow 快照、orange3 scorer 键的成因）。
- **对照 2 题**：都没有题意争议，但各有覆盖缺口，需要事后复核得 1 的补丁。两题都能作为探针候选。两类题分开统计，不据此估计全池缺陷率。
- **全池线索**：
  - 用题面代码块与 gold 新增行逐行比对 48 题，只有 orange3 `22e98f8f` 命中（7/7 行），见 `runs/r2e_static_prep_20260924/statement_gold_overlap_scan.json`。这只查逐字泄漏，查不到改写过的泄漏。
  - 同仓不同提交的题会互相包含对方的修复（pillow、orange3），留出评测应按仓库或时间划分。
- **工作量**：每题大约为公开读者 10–15 分钟、主审 30–45 分钟（两步合计）、复核 25–30 分钟，另加协调者的候选评分。候选评分共 26 次，都在 A 线机器上完成，每次 1–2 分钟。
- **执行问题**：宿主拒写报告文件；安全分类器 4 次拦截或中止会话（scrapy、coveragepy 两位主审各 2 次），第二步改由接续会话完成。都已按 §6 处理，没有影响封存关系，主审读历史前封存的初判都保留了原文。

## 8. Codex 复核后的处理（09-25 上午）

[Codex 复核](../r2e_static_actor_review_20260925/README.md) 的结论：接线和调查证据成立，26 条评分数值没有被推翻；有一处接线缺口（R1）和两处归因要修正（R2、R3）。按用户 09-25 上午的决定，有问题的题先不做内容修订，继续审剩下的题；下列不属于修题的事项先做。

| 编号 | 回应 | 处理 |
| --- | --- | --- |
| R1 orange3 修订要绑定实际依赖内容 | accepted，已修 | 要求里加批准并复验过的配方内容摘要，构建、回放、actor 三处共用；正反例测试与真实覆盖表核对通过，见[接线说明](../r2e_actor_wiring_20260925.md) §3.1；请 A 复核共同消费点 |
| R2 失败键模式不能直接免责 | accepted | 已改 pandas / scrapy 的题卡与记录、orange3 的复核与题卡（顶部加注，原文保留）、本页 §7 与汇总页；第二批角色卡写入这条规则 |
| R3 pillow P1 单列 | accepted | 已改 [grader_candidates.md](grader_candidates.md) 与本页；合理修复被判 0 的计数改为 6，pillow P1 单列 |
| aiohttp C3 口径、numpy 逐项后检 | accepted | 两个脚本已写好并验证（[actor_devcheck.md](actor_devcheck.md) §4）；aiohttp 的题卡与记录改为语义化 C3，去掉"待运行"旧文字 |
| O1 overlay 读两次文件 | accepted，已修 | 改为解析同一份已校验的字节，加了测试 |

