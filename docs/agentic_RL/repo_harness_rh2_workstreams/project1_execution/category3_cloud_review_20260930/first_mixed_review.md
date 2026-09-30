# 分类3首批四题独立文本复核

2026-09-30 / Codex。复核快照为 `0c074dc961231d2233a5624234a3606c239ecbcc`，比摘要中的 `382b9c3` 新。本次先读原公开题面、公开源码／测试、原与修订测试、候选及原日志，再核作者 `result.md` 与两轮 `review.md`。我不是 R-f 所需的新公开读者，也没有重复运行云端实验。

**四题均同意转分类2；这只表示目标、问题和实施路径足够明确，不表示材料已正式落地或训练准入通过。DVC 的交接清单需要实质更正：两轮具体阻断已有处理，但部分已证实的评分缺口不能因“熔断”“正对照正确”或“组合少见”核销为 S2。**

依据当前 `AGENTS.md`、`task_screening_standard_v1_20260925.md` §4–§5。未执行项目或快照脚本，未 SSH、下载、启动容器、调用付费模型，也未修改快照及生产代码。

路径缩写（均相对仓库根）：

- `S`：`runs/category3_cloud_review_20260930/snapshot_0c074dc9`。
- `T`：`S/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks`。
- `E`：`S/rh2/experiments/category3_cloud_20260929`。
- `P`：`runs/r2e_static_prep_20260924/v3/public`；`D`：`runs/swegym_quality_batch01_20260921_v2/public/iterative__dvc-9395/base`。

核对四份 `evidence_manifest.json`：DVC 294、Pillow 202、coverage016 204、coverage5dbbe 10 个归档文件，大小与 SHA-256 全部匹配，无缺件。这证明归档内部一致，不把作者实验改称本次独立实跑。`rc.json`／多数 `summary.json` 是管道退出码；结论使用逐键结果及原日志。

| 题目 | 分类判断 | 分类2应接收的工作 |
| --- | --- | --- |
| dvc-9395 | 同意转2；修正交接范围 | R-b＋R-c v4有充分诊断依据；补上已知冻结输出与公开行为回归的验收，不能按v4直接核销质量问题 |
| pillow__3a61c9e9 | 同意转2 | R-c v2的74键版本；用独立核实的替代正对照验收，保留完整修法 |
| coveragepy__016af5f6 | 同意转2 | R-c v2＋仅修示例的R-f；保留跳过和转换两类解，不增加报告／告警／其它异常约束 |
| coveragepy__5dbbe143 | 同意转2 | 按已记录的A决定落题面修订；同步旧题卡与用途，验收新版本 |

## 1. dvc-9395：方向明确，v4尚不能当最终验收材料

**公开目标有依据。** 原公开题面要求拉取“all missing files”“whatever is missing and necessary for this repro”。`D/dvc/stage/__init__.py:242` 明确定义数据源包含 `dvc add` 和 `dvc import`；原 `test.patch` 也带 import 测试。因此把 import 纳入非示例实例不是从私有 gold 扩张任务目标。修改已有数据时保留修改、更新 hash，有 `D/tests/func/test_repro.py:270`、`:671` 的公开测试支撑，不能把“pull缺失数据”改成“复原用户已经修改的数据”。

**两轮具体阻断的处理真实存在。** `E/dvc9395/revised_test_v4.patch:37` 模拟确认删除、随后检查 foo/bar 内容及提交状态；`:43` 补 import；`:57` 要求无法取得缺失数据时仍报错。删除 checkout 精确计数、放宽 restore 次数有合理实现反例；并未删掉数据恢复的行为要求。`T/iterative__dvc-9395/evidence/revised_v4/grades.json` 与各 `t4_rev4.out` 一致：16个候选中 `c3_frozenfix`、`up351_port`、`c3_missing_only` 为1，其余为0，所有候选P2P均27/27；六个已知吞错候选都为0。首两轮要求的内容、交互覆盖、无法拉取仍报错、import范围，已在私有层面关闭。

**替代正对照已有足够支撑。** `c3_frozenfix.patch` SHA-256为 `94d448480d67…`。其主体经前一复核者核实，冻结条件的一行由复核者写、主审用独立场景核实，分工已记录。`evidence/semantic_v3/c3_frozenfix/d3_behavior.out` 显示冻结输出和import均恢复；`public_v2/regression_vs_base.json` 显示198项公开结果与base相同。v4原日志为30 passed，29个计分ID全过。可作分类2的主正对照，但不能据此推出评分已拒绝所有已知错误候选。

**须更正 `result.md:143` 起的T3／S2处理，保留以下具体未完成项：**

1. **冻结命令stage的必要输出。** 作者已确认 `c3_missing_only` 不恢复该输出，却在v4得1。冻结行为本身有公开测试（`D/tests/func/test_repro.py:508`）；该输出缺失且为下游必需时，属于题面一般要求的另一实例。主正对照换成 `c3_frozenfix` 没有修掉这个评分缺口，熔断也不是降级依据。分类2应把现有C1／C2场景移为窄行为验收：冻结stage的缓存与工作区输出都删掉，下游repro所需的数据能从remote恢复，且不靠执行冻结命令过关。`c3_missing_only` 应为0、`c3_frozenfix` 为1。目录“部分删除算缺失还是修改”的P5歧义与此不同，仍不直接补断言。
2. **dry的公开语义。** `D/tests/func/test_repro.py:287` 和base `StageCache.restore` 的 `not dry` 条件明确保护无副作用。现有B1／B1b／B1c已证 `up351_port` 在 `--pull --dry` 下下载／写回，而v4仍给1。这是可实施的公开回归验收：沿现成场景比对workspace、对象cache、runs目录前后状态，且不执行stage命令。主正对照已有成功证据；`up351_port` 不宜在未处理这项时继续称为满足最终验收的第二正对照。
3. **无需下载时的无remote行为，以及HTTP上已有可用的run-cache恢复。** B2／B2b和B4b已给出base成功、gold式实现失败的机制与候选对照；`c3_frozenfix` 的17场景重跑保持base行为，`up351_port` 继承部分回归。不能只凭“上游也这样”或“remote类型非主流”核销。分类2应沿这些固定场景确认所用公开能力和失败归因，再纳入相应行为断言，写明最终候选预期。无remote且确实需要下载的失败不应被改成成功。

`--no-run-cache`仍下载runs、已存在无hash的输出被误删、依赖已变且旧输出不可得时阻断可重算路径，已经有具体B5／B6／B9证据和可通过的主正对照，应保留在分类2的公开回归清单，逐项处理或给出基于公开行为的边界理由；“少见”本身不够。无需因此另查S3、SSH、`exp run`。正式配方／D6补丁接线是落地工作，不是继续留分类3的理由。

## 2. pillow__3a61c9e9：RGBA、透明索引与大小检查均有明确边界

**同意R-c v2。** 原题要求RGBA调色板恒等映射后保持相同；公开 `P/pillow__3a61c9e9…/worktree/Tests/test_image.py:612` 已规定透明索引随映射移动。两者结合支持“RGBA调色板＋整数透明索引”的核心实例，不能因gold引入 `ValueError` 而放宽。新增测试位于 `E/pillow3a61/hidden_test_1_revised_v2.py:678`，SHA-256为 `78631c73aa95…`。

断言没有要求统一内部写法或小调色板补齐策略：小图仅检查有效前8字节、像素及透明索引；满256项检查调用前快照，不能通过修改输入蒙混；没有新增精确内部palette长度要求。把透明烘成alpha=0会改变恒等映射后的调色板，A0K/A0D被拒有题面依据。RGBA渲染断言沿用公开转换的透明语义，未要求新增GIF背景规则。

原日志与 `evidence/revised_v2/grades.jsonl` 一致：C1、U11、G_del、G_cim、HYB、G_gif六种解为1，base、gold、A1u及五种错误解为0。v2的满调色板实例确实挡住首轮仍为1的G_small：原日志失败为同一 `ValueError`，不是环境／补丁应用失败。G_gif更完整的修法仍为1，未因改GIF插件被误拒。元组背景路径未被文档规定，N2–N4保留T3有范围依据。

**落地后续明确。** 保存v4→v1→v2及74键期望；正式复验noop、gold、A1u、W1–W5，以及C1、U11、G_small、HYB、G_gif。正式C1原补丁与本页重建版本未逐字核对，应固定实际使用者的摘要；U11已有独立核实和多类实现证据，故这个文件核对缺口不阻止转2。新版本需改准入卡的gold／A1u期望，不能沿用v4训练资格。

## 3. coveragepy__016af5f6：修订保护保存数据，没有扩大异常要求

**同意R-c v2与窄R-f。** 原示例在start之前执行不可编码文件名代码，base与gold都不崩；`evidence/examples_v1/` 完整归档了原例与修例对照。`E/cov016/revised_statement_v1.txt` 只补import、把原exec移进测量区间、纠正“创建文件”的注释，未泄露新增测试名、分支模式或非示例字符。

修订测试 `hidden_test_1_revised_v2.py:566`（SHA-256 `ccdd7d89bb17…`）保留原无异常要求，另测branch、另一不可编码名、排在其后的可编码非Latin-1名与独立数据读回。branch是公开运行模式；保留可编码文件的数据有公开Unicode路径测试及 `Coverage.save()` 文档依据，属于防止吞错后丢失正常数据的同一窄问题。它不断言不可编码名必须被跳过或如何转换，不要求额外告警、不要求 `report()` 成功，也没有要求吞掉所有异常或信号。后续不得以“gracefully”增加这些条件。

`evidence/revised_v2/grades.jsonl` 的14×3结果与原日志对应，键集始终15/15且unexpected为空；六种合理解（跳过四种、转换两种）在v2为1；noop及七种错误候选为0。吞flush／循环中止两个候选确在正常文件保留断言失败，原v1放过的问题已处理。`source=`未执行文件、直接CoverageData API及不可编码context没有变成题目要求；已登记basename／其它孤立代理字符的未查或边缘范围，不据此扩大本轮修订。

分类2只需按既有R2E机制登记两种替换、在正式身份／材料上复验这组候选，并由未看隐藏测试与gold的新公开读者验收修订题面。正式评分、新公开读者和actor身份未验属于明确落地项，不是未知语义。

## 4. coveragepy__5dbbe143：A决定已落盘，新公开题面与验收一致

**同意转2，但明确这是按用户选定A构建的自建版本。** 原公开材料仍支持按slug和按消息两种读法；gold的私有docstring不能消解P5。A的授权有两处落盘记录：快照 `category3_diagnosis_20260929/README.md:184` 的09-29决定，以及本题 `result.md:56`。本次没有原对话全文，不能独立逐字审计授权原句；但不能因本地旧 `probe_card.md` 仍写on_hold，就否认较新快照中的已记录决定或重新加一道审批。

`E/cov5dbbe/revised_statement_A.txt`（SHA-256 `b2a7f5fb3e3c…`）与原题只差Expected Behavior的身份说明：same slug即使message不同也只显示第一条，different slugs各显示一次。该句与已备 `revision_draft.json` 一致；没有指定列表、helper、内部状态或隐藏测试字面值。它落实A选择，而非声称原题本来只有一种读法。

**角色与验收关系足够支持转2。** 新公开读者报告 `public_read_revised_A.md:10` 声明未读gold／隐藏测试，需求表覆盖修订目标；其143项公开测试是公开兼容性证据，不是正式评分。本文独立检查 `E/cov5dbbe/hidden_test_1_v5.py:542`、`:551`：once只在两个目标测试使用，没有加入once后非once、无slug、跨实例或内部warning列表断言。读者的“隐藏只验公开目标”前提在当前材料成立。作者未另起一次全题复核，但旧P5判定、新公开读者与本次独立文本核对分别承担了不同检查，不能把它们混称三次正式验收。

五个候选原日志支持作者矩阵：gold和CE3为76 passed；CE1只失败原same-slug键，CE4只失败each-slug键，noop两键TypeError。CE系列是重建补丁，这一局限已明写；它们可支持机制判断，不能替代正式原补丁的新版本验收。

分类2应落 `statement_text_replace`、同步本地题卡／board与用途，并固定新公开题面摘要；按新版本正式复验gold、noop、原CE1／CE3／CE4。保留“once后的非once、slug=None、跨实例等没有新增判据”的边界。已有v5评分不能直接授予新题面版本资格；无需重复与A/B读法无关、已完成的R-c调查。
