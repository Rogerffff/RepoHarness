# iterative__dvc-3576 — 独立复核收口

2026-09-21。结论范围为 `needs_review / static_review`、`development_diagnostic`。**保留为受限诊断备选，本小包不优先列入静态候选。** 理由是唯一冻结 F2P 直接规定 formatter 的空返回，而公开可行的命令层分流路线存在具体误拒疑点；同时满分与缺旧数值的题面展示尚未形成行为级对应。不是因为测试少、没有新 CPU 或 actor 未验就判题坏，也不以“gold 没有发 stderr”单独认定 gold 必错。

协调者已先封存全部三题 reviewer_initial，再统一开放本题公开读稿、主审稿、历史差异、短卡和结构化记录。本稿据此对照，未回写任何封存稿或他人文件。初稿 SHA-256 为 `c4b6aa56fec872b6ea46de7ecd69a45e2f7e63ee04cd0fb9ed411cb4a948ecef`。收到协调者关于“沉默是否合理”的疑问是在封存后；以下解释保留独立判断，不把该疑问当作新的公开需求。

## 证据定位

权威根 `ROOT=${REPO_ROOT}`。下文 `I=ROOT/runs/swegym_quality_batch02_20260921_v2`，`P=I/public/iterative__dvc-3576`，`V=I/private/iterative__dvc-3576`，`B=P/base`；`O` 为本报告所在目录。`R=ROOT/runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-3576`。

- `G=R/gold/eval_logs/evallog_replay-er19-dv1-iterativ_4d6e3c69.eval.log`，SHA-256 `fdb62b21f6a3b8434cff8f3a35d3344e443328c8e6819e0eb879ca6ef3fdb3c4`。
- `N=R/noop/eval_logs/evallog_replay-er19-dv1-iterativ_9ae4a68d.eval.log`，SHA-256 `58381050676ad1ea34df0c0247a7289790acb78e1212332af26584b7258828e5`。
- `H=ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_1/records/iterative__dvc-3576.json`，由本题 history/refs.json 精确授权。
- `S=ROOT/runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/iterative__dvc-3576`；旧 `LG=S/gold/offline/a1/test_output.txt` SHA `747494847a1b2d006e45d34f2cd5a3c1ab63d5d59da5bf9b97a4547df1b8db7a`，`LE=S/empty/offline/a1/test_output.txt` SHA `a93c651041841013fb1d72c6beffc15572e0d8e9b01e0e46c9cda63c8f33b218`。旧 LG/LE 与修复配方 G/N 行号不可互换。

第一阶段已核 S2 第123行 public/grading/validation 与本地材料一致，base `a338fad036bd9ac8bdd79ecec964f8c5558609c4`，gold/test 文本及实际候选、恢复、安装、日志身份。既有材料完整性不再逐 blob 重复。

## 决定性主张的复核

| 主审主张与引用 | 复核结果 |
| --- | --- |
| base 已具缺侧容错，gold 未改数据层不代表另外三项功能全不存在（analysis §1、delta:26） | 同意。`B/dvc/repo/metrics/diff.py:78–100` 用 `.get(...,{})` 并捕获 NoMetricsError；旧值为 None 的路径与公开功能测试已存在。原始 KeyError 在当前 base 未被实际重现。 |
| F2P 为 `_show_diff({}) == ""`，六个 P2P 是五项 formatter 加一项 Mock 命令转发（analysis:38–62） | 同意。全部七个测试体与新增的一行断言已独立展开。`test_metrics_show_json_diff` 输入 old=1/new=2/diff=3，检查表格而非计算或 JSON；`test_metrics_diff` 使用 --show-json 并 Mock 数据层，不捕获流。不得写成六项表格或真实缺旧 JSON 验收。 |
| gold 只删除空结果 helper 的文本；caller 仍 logger.info（analysis:59,70，card:7） | 代码事实同意，但“因此未完成 stderr 要求”须按下节收窄。`V/gold.patch` 只改 command/metrics.py:112；`B/dvc/command/metrics.py:147–152` 和 logger.py:105–111,164–183 不产生非空 stderr 状态，预计 stdout 仍有换行；后者只是源码推断。 |
| numeric 缺旧示例的 Change 为 `-`，gold 仍使用 `diff not supported`（card:8） | 同意为可定位的字面展示差异。command/metrics.py:128 未改；缺 old 的数值无法形成 diff。尚无该原例的 CLI 字节实证，不扩大为缺侧比较整体失败。字符串缺侧 P2P 固定旧文案，不能据此称所有满足数字示例的解均被拒。 |
| 保留 helper、在 caller 分流的路线可能被拒（analysis:66–68） | 同意为具体静态疑点。私有 helper 的返回值不是题面指定的外部接口；可在空 diff 分支把状态写 stderr、跳过 stdout 调用，非空渲染另保留旧语义。完整替代候选及其 reward 未执行，不称已证误拒。 |
| gold=1、noop=0 是可解释的真实分差（analysis §5） | 同意，限历史修复配方 grader。G:579,602–613 为7收集/7过/RC0；N:565,573–575,604–608 为1个 helper 失败、6过/RC1；ledger F2P1/P2P6 全命中。不是当前 CPU 或 actor 结果。 |
| 旧安装与 status_map 干净的说法错误（delta:30–31） | 同意，已查原件。LG:347–390 有 PyYAML、Git/requirements、setuptools 失败，414–415 仍记最终 RC0；LE:333–376 同类失败，400–401 RC0。两份旧 status_map:2–3 直接含 Could/No 的 ERROR 键。当前 G/N 的成功与7个干净身份另有原件，不移植旧故障为当前故障。 |

### stderr 的字面要求与合理解释

`P/user_prompt.txt:36` 明示“only the table”进入 stdout，其他消息（例举 No changes）应去 stderr。这明确约束**发出消息时的通道**，也可以自然读成“把现有提示搬去 stderr”。后一种读法下，gold 没有交付保留提示的行为。

但题面没有独立规定“无变化必须发出非空状态消息”。若把此段理解为结果流不混入状态文本，并允许无变化时沉默，删除可选提示是合理实现。故**没有 stderr 文本不等于在所有合理解释下 gold 必错**。空 stdout 换行的严格字节意义同样没有公开明确规定，不作为主要拒绝理由。JSON 的 `old:null` 与省略 old 字段也不在此复核中被强行裁成唯一合法形式。

主审 analysis:5,59,70 与 disposition 中的 partial-gold 应加上这个解释条件；card:7 的代码陈述本身准确，但不宜让读者自动推导“必须保留 No changes”。delta:25 已正确排除另一种过强主张：helper 返回空与 caller 发 stderr 并不互斥。测试允许两者同时发生，也允许沉默；它实际限制的是 helper 本身的返回约定。

即使采用“允许沉默”，CLI 层合理路线的误拒疑点仍然成立；采用“必须保留提示”时，该路线更直接满足题面。这两件事不互相抵消。隐藏 raw 讨论中双方偏好只能说明历史解释分歧，不能用后来读到的讨论覆盖公开文本。

## 八方面边界与阶段区分

| 方面 | 独立核对及本次收口 |
| --- | --- |
| 公开目标/初态 | 四项目标与已有缺侧逻辑分开；数字占位符差异保留，stderr 是否必须非空保留解释余地。公开材料足以调查，无需先给解题者隐藏讨论。 |
| 需求—断言双向映射 | 第一阶段完整展开1个修改断言、F2P1/P2P6、fixture/Mock及功能测试调用；本次确认主审表。真实 Git 比较、JSON输出、CLI流并非已冻结保护。 |
| 合法替代/自然部分实现 | caller 分流路线是具体候选，未执行；gold 的宽需求覆盖不能由7分证明。没有另造恶意硬编码解，也不把沉默天然判错。 |
| gold/调用者/回归 | gold一行业务变更；生产 helper caller只有CmdMetricsDiff。func metrics:882–1007 的读取/计算/新增/删除/坏JSON已选读，不是本次执行。没有发现gold新造数据层回归，不等于全面证明。 |
| 开发条件 | 本地Git、少量JSON、临时目录及兼容Python依赖即可做语义检查。moto dev→release 是既有环境基线差异，不是gold修复；conftest导入remote包不意味着需要SSH/云服务。 |
| 投影/恢复/评分控制 | 实际gold只投影command/metrics.py，noop为空；恢复仅official test.patch的一份unit文件。当前RH2 `test_globs=()`，不沿用“所有测试修改都会恢复”。未发现本题需新增排除，维持空。 |
| 版本/关系 | S2身份及本题两期run各自清楚。H对3620/2141的关系标签未沿跨题聚合验证，不采纳同侧/无关系结论。 |
| 暴露/用途 | 初稿前已见允许的environment_record原始环境摘要；门禁后又读本题公开/主审/旧报告及raw讨论。审查者已暴露gold和隐藏验收，不可充当盲解者或把本报告交给solver。 |

修复配方只证明 rh2grader/54322、派生镜像、可写解释器前缀与 deny_all 条件下的安装/7项结果；正式 public image 与 actor/54321 的shell、消息、工具、权限及激活仍未知。apply_user=agent/54321 只是应用补丁，不是 actor 会话。env_qualification=absent/resource_facts=null 不得补成通过。当前控制面与历史镜像二进制也不做字节等同声明。

## 唯一优先后续实验

**固定已引用修复 grader 配方，做 base/gold/CLI层替代候选的一组三方对照。** 在隔离临时Git仓库内准备有效父revision、缺旧文件/缺旧stage的数值指标、正常比较和无变化；保留原7项及原reward，额外分别捕获文本与JSON的 stdout/stderr/退出码。替代候选保留旧 `_show_diff({})`，从 caller 处理空结果流向，并完成数字缺侧的题面展示，保持字符串/删除等既有行为。

先判断候选在外置行为探针上是否完整，再判断是否仅因 helper 断言失败；否则撤回“合法替代”推断。对gold同时报告实际字节和两种stderr解释，不用运行结果代替规范解释裁决。此为一个有限语义实验，不要求先修完所有一般覆盖空白、跑全仓或获得模型会话。

这里收窄主审 card:15、analysis:137–139、delta:43 的顺序要求：**CPU grader语义实验可先使用固定grader配方；实际actor配方核验是后续启用模型开发前的独立条件。** 没有理由为只检验oracle而先要求actor会话；同样不能把前者成功记成后者通过。实验未运行，候选未写入，原题、gold、测试、冻结奖励均未改。

## 本次新增阅读与未决

已读 O 五份开放产物；H正文；S两份status_map及上述旧日志的安装/摘要/失败精确段；raw `swe_gym_lite_full_f70b1a29.jsonl` 第137行本题 hints（行SHA `d167742b5388e4f3edb5ef0bb1b8b55399921b9a2924b187f5dca62bd948ac2c`）；重新核所引公开prompt、command/logger关键段。旧日志hash读取全字节不等于全文人工阅读。未读其他题、批次聚合/manifest/CPU队列、未执行项目、pytest、安装、容器、SSH、联网或模型；当前只新增此review.md。证据强度保持“源码静态推断 + 两期历史运行原件”，没有当前CPU、真实actor或已证错误候选分数。
