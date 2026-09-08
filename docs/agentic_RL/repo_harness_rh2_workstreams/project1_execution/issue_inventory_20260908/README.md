# 项目一 A：链路问题完整导读与讨论清单

日期：2026-09-08。用途：把既有 Codex、Claude 与交叉复核结论合并成 owner 可以逐项理解、讨论的清单。**本轮没有修改训练实现、测试、配置或既有定案，没有启动 GPU/Docker 作业。以下不是修复批准单，也不是训前验收。**

我们把旧报告合并为 **36 个讨论主题**；主题不等于 36 个已经证实的 bug。有些主题含多个重复或相邻发现，有些属于已知接线前置、需实测的风险或维护候选。末尾逐一映射 Claude 七份切片的 96 个编号条目，以及 Codex 的原始发现，避免只保留几个大问题而遗失小项。

**后续状态：I01 已由用户确定首版 B，C 暂缓，不排专门 B/C 对比实验；实现待办。I02–I36 的后续讨论改按 [七组决策清单](../decision_batches_20260908.md)推进。** 本文是问题与证据底稿，不能把旧候选措辞作为最新决定，也不把分组视为其它修法已获批准。

## 1. 当前证据与阅读方式

主仓库已从本轮开始时的 `5b6e1262` 快进到 `17d9899c6d4b61938f74bd9121da8dee9b621a8d`，分支 `miles-migration`。本次新拉回六篇正文及六份作者自查：E11 Nemotron-Cascade 2、E1 Harness Interplay、E3 Envs Forge、N06 Hardening Agent Benchmarks、R0 Polar、R5b GLM-5.2。此次 incoming diff 只新增 Markdown；本地原有 manifest/index/catalog 修改与其他未跟踪资料均保留。

收尾时共享工作目录又已快进到 `ac0e2e64163fbe49411540e901df439aea16b6b0`，仅再新增 R5c GLM-5.3 **预读记录**与自查；该文明确官方博客全文获取受阻，不能计为完成精读。本导读与三个角色的实质核查以 `17d9899c` 为阅读快照；收尾再次检查 `rh2` 源码未变。并行同步不影响以下源码结论。

从原审查基线 `ce2009f879cf38071d7898a1387e01d4e27741d6` 到当前 HEAD，`rh2` 跟踪源码没有变化。miles 集成仍为 `98a0272e4158b2c20e3a34d210c79b50159af0f6`。这使旧定位仍可复用，但不意味着所有旧断言都正确。

尤其要注意：[Claude 总报告](../../tmp/external_review_20260905/00_FINAL_REVIEW.md) 已追加 **2026-09-07 勘误**；与旧正文、切片冲突时，以勘误及 [Codex 交叉复核](../../miles_spike/external_infra_review_crosscheck_20260906.md) 为准。本导读不再次沿用“全部多轮掉首轮”“无限静默跳过零梯度”“所有评分失败给 0”“三分之一可以直接删”等已纠正或未证明的说法。

本轮分工：主审整合、核评分关键边界并重跑轻量证据；独立 Production Tracer 追运行路径；Falsifier 尝试推翻过强结论；性能审查者核开销与相关阅读线索。详细报告见 [运行追踪](runtime_tracer.md)、[反证与边界](claims_falsifier.md)、[性能与资料](performance_and_sources.md)。主审没有把子报告多数意见当作事实证明。

证据标记：

- **已证实行为**：当前源码与定点探针足以证明机制；出现频率可能仍未知。
- **已知前置**：启用 formal/eval/恢复前必须完成，不能当作已经完成后发生的新回归。
- **待实测/待决**：触发路径存在，但收益、发生率或允许的语义还没有证据。
- **维护候选**：结构重复或当前无消费者，不等于可以立即删除。

下文 `R/` 指 `rh2/src/repoharness2/`；`S/` 指 `rh2/src/slime/`；`M/` 指 `reference/miles-rh2-integration/miles/`。行号定位当前代码，范围用于说明相邻逻辑。原始证据与更完整的锚点见三个配套报告。

理解整条链路可以先看这个顺序：

```text
任务与镜像准备
  → Claude Code 在 rollout 容器内行动
  → adapter 翻译消息、向 SGLang 请求、捕获 token/logprob/路由
  → 合并多轮与分支、停止在飞操作、冻结文件变化
  → fresh grader 重放文件变化并评分
  → 装配 member、完整组准入、buffer 等待
  → 消费时检查版本、生成 advantage、计算 loss、更新权重
  → checkpoint / eval / 关停与清理
```

最重要的三种损失要分开：**动作被移出 loss、整条执行/整组被丢、执行仍被消费但没有有效梯度**。它们需要不同的证据，也不能用同一个“有效样本数”概括。

## 2. 生成、预算与异常：动作如何进入训练

### I01　消息重渲染后，旧轮动作可能整轮失去 loss

**状态：已证实；应先讨论。位置：** `S/agent/trajectory.py:180–224,370–426`；实际 tokenizer 入口 `R/adapters/slime/bringup.py:828,861`。

Claude Code 的历史消息会经过 Anthropic 消息翻译和 HF chat template，再次 tokenize。重渲染不一定保留第一次采样时的 token：例如 system-reminder 被翻成独立 user 消息后，模板可能不再保留前轮 thinking；工具参数 JSON 的顺序变化也能造成漂移。为了使新 prompt 与当前 token 序列一致，上游合并器有 REALIGN 路径：它把旧响应所在区间改成新 prompt，并把那段 mask/logprob 归零。另一个 rewrite merge 路径会直接删除旧 TurnRecord；这不是同一条 if。

**本轮重跑例子：** 首轮 27 token、次轮 2 token。普通工具往返保留 `29/29`；增加特定 reminder 后变成 `2/29`。首轮长达 1125 token、次轮仍为 2 时，也只保留 `2/1127`。REALIGN 判据看的是**新输出是否短于 1024**；相同场景把新输出改为 1024 会 FORK，两条 Sample 合计保留 `1051/1051`（token FORK 不一定增加消息树叶）。rewrite merge 的 1024 判据则看旧输出，不可混淆。

**2026-09-08 后续定案：** 已补查 1024 的上游历史、阈值 0 的真实 manager/身份回填探针，以及相关外部实现；补核 miles TITO 与 run8 成本后，用户确认首版 B（精确前缀合并、漂移保留旧行），C 暂缓，不排专门 B/C 实验。详见 [I01 方案讨论](../i01_options_20260908/README.md)与 [用户决定](../infra.md#6-用户决定)。实现与接入验证待办。

为什么严重：模型第一轮选择查什么、如何定位问题，这些动作即使决定最终成功，也可能拿不到训练信号；剩余 token 的对齐、DIS 分母和梯度公式都正确，仍不能补回被删除的动作。当前也缺逐轮 generated/trained/dropped 覆盖统计。

**范围：** 不是所有多轮必掉首轮。历史 run8 汇总报告称 60 条分支均缺首轮，本地完整 raw projection 只复核过一条；那条漂移点落在工具 JSON 尾部，不能断定全是 thinking。当前 HF 模板不读 `clear_thinking`，只加 `False` 无效。下一步讨论的是允许的真实 harness 历史改写、动作覆盖目标与表示选择，不能先把任意新 prompt 当作原始采样 token。

### I02　25 次模型请求上限没有形成明确的训练终止事实

**状态：上限与 429 已证实，真实 CC 后续行为未证。位置：** `S/agent/adapters/common.py:285–306` 的 `_check_turn_cap`；`R/adapters/slime/bringup.py:229` 的 `MAX_TURNS_PER_SID`，可由环境参数 `RH2_MAX_TURNS_PER_SID` 配置。详见运行追踪 RT-3。

同 SID 第 26 次请求返回 HTTP 429；本轮探针前 25 次通过，之后为 429。它数的是模型 API 请求，**不是工具调用数**；一次请求可以输出多个工具调用。仓库没有实际生成 `max_turns_exhausted` 终止事实的 producer。

例：模型已经花 24 轮定位，准备第 26 轮验证时，得到的是一个看似服务限流的错误，而非“本题策略预算耗尽”。CC 是否重试、何时退出、最后被记作什么，需要当前 CLI 的真实请求验证；不能把旧报告“必然 harness_crash”当已测事实。需要决定预算单位、重生成/子 agent 是否计数，并将实际终止和训练处置接起来。

### I03　多套计时的归因不统一，而且排队可能越过 deadline

**状态：排队缺口已证实，其余需按路径区分。位置：** `R/adapters/slime/async_worker.py:735–756`；harness hard wall、session drain 入口见运行追踪 RT-4。

当前有 attempt 墙钟、模型代理 deadline/单请求 timeout、session drain 等不同预算。代理在等信号量**之前**算剩余 timeout，等待不受同一 deadline 包围，获得名额后仍用旧 timeout。探针 deadline 20ms，排队约 41ms 才发请求，约 47ms 成功返回：本应过期的请求仍可消耗推理资源。

墙钟到了以后，harness、proxy 和 drain 也可能先后给出不同事实；drain 超时不能证明所有模型请求已经停止。这里的问题是同一执行的预算与终止事实没有完整对齐，不能仅比较“600/900/30 秒”常量就推断每条执行都会跑满更大值。后续应先还原请求/排队/取消时间线，再决定哪些是合法截断、哪些是真实停止失败。

另一条实际出口也应单列：proxy 从首次模型调用起表，剩余不足默认 5 秒时会产生 `episode_deadline_exhausted`，poison 会话并取消 harness，最后可按 `api_failure/model_proxy_failure` 形成 missing。它可能早于 harness 墙钟被观察到，从而把预算结束变成 API 故障；两只钟起点、CLI 启动时间和轮询粒度不同，触发先后与频率尚未在真实 CC 作业测定。见 `async_worker.py:827–829,853–860`、`generate.py:2734–2747`。

### I04　截断策略有接口，生产入口还没有注入

**状态：已知 C/W7 前置。位置：** `R/governance/admission.py:611–647`、`R/adapters/miles/group_admission.py:515–554`。

`DispositionPolicy` 的相关槽缺省为 None，当前没有生产构造/注入点。成员进入 formal 准入、形成可处理的 `present_truncated`、没有先被其它条件丢弃时，才因缺显式策略抛 `DispositionNotInjectedError`。不是任何超时都会走到这里，也不是今天已有正式作业跑到一半的新事故。

例：600 秒到了，文件冻结与评分都成功，但不知道该保留这条有 reward 的截断轨迹还是丢组；系统按既有决定拒绝替 owner 选择。这个空位必须在正式入口启用前填上。四槽是否合并一槽属于训练语义设计；更早验证必填配置则是入口可靠性问题。没有 producer 的 policy-horizon/security/owner-cancel 槽，也要区分“当前 profile 不支持”与“宣称支持却没接通”。

### I05　内部装配错误可能被包装成 ABORTED，再用补采掩盖

**状态：已证实的异常分流问题。位置：** `R/adapters/slime/generate.py:806–829,2883–2889,3445–3449,3511–3516`，`capture_wire.py:737–750`，`M/rollout/fully_async_data_buffer.py:239–256`。

有些异常只代表程序/协议自相矛盾，却被宽泛捕获后当作成员 missing/ABORTED。miles 在完整组 admission 之前就丢掉含 ABORTED 的组，继续生产新组；因此后面的严格校验没机会替它报出内部错误。

具体例子：模型响应 token、logprob、版本都有，却缺 `meta_info.id`。capture hook 记录失败，registry 仍返回可绑定引用；backfill 找不到对应 TurnTape，最终成为 `capture_record_unknown_in_backfill`→ABORTED→整组丢弃。旧定点故障注入已通过真实 registry/hook/orchestrator 验证；真实 SGLang 是否频繁产生这种响应未知。

后果是系统性协议 bug 可以表现为“补采多、训练慢”；如果只影响某类长轨迹或分支，还会选择性改变训练分布。并非完全没有事件：缺的是足以暴露具体原因与比例的聚合，以及正确的异常分流。也不能反向把所有 timeout/capture failure 都提升 fatal；应区分可归因的任务局部失败和内部矛盾，避免再叠一个通用熔断平台。

## 3. 文件与评分：什么结果被当成 reward

具体任务适配由 B 主责；通用执行、错误归因和运输由 A 参与。以下保留旧审查中的评分问题，不表示本轮已经审完数据/环境。

### I06　SWE-Gym parser/spec 覆盖仍未接齐

**状态：已知 T2-d/任务适配前置。位置：** `R/envpack/scoring.py:121–128`、`R/grading/manager.py:2007–2013`。

已安装 swebench 4.1.0 的对应 parser/spec 表未覆盖旧 SWE-Gym 清单中的 11 个 repo；已有命令表并不等于实际 parser/spec 接通。若用未支持的任务进入这个入口，查表或解析异常会变成 `failed_to_grade`，随后按 infra 损耗丢组。

例：同一个缺失 parser 的 repo 重跑一百次也不会恢复，它是确定的配置不支持，不能与一次 Docker 抖动同样解释。应在选定任务适配器后尽早暴露支持范围。旧报告“216 题实际已连续 100% 静默损耗”超出运行证据；未来数据清单也尚未最终确定。

### I07　模型失败与环境失败在超时、空解析处被混在一起

**状态：分类行为已证实；改判条件待明确。位置：** `R/grading/manager.py:1449–1473,2004–2027`、`R/contracts/grading.py:41–47`。

test/setup 超时目前都抛 `GradingInfraError`；零解析测试也统一归 infra。已有 `test_execution_timeout` 负样本类别，但生产分类尚未实现。后果可能是模型引入死循环或 SyntaxError 后，失败样本被丢掉，模型收不到负反馈。

但“全改 reward 0”也会出错。本轮真实 parser＋合成日志探针：候选 SyntaxError 与环境中 `python: command not found` 都得到空 status map；官方当前 PASS_AND_FAIL 调用都判未解决，RH2 都判 parse infra。前者可能应教模型失败，后者不应。旧“零解析必官方 silent-success”的注释只对某些其它口径/空测试集合可能成立，不能概括当前非空 F2P 调用。

已批超时记 0 的规则包含：clean grader 正常、预算确定、超时可归责 agent patch。**phase=test 不能替代第三条。** 后续需要 B 提供可信环境与失败反例，A 保留退出码、阶段和资源事实；最后才决定归因与 reward。

### I08　测试路径 glob 可能把正常可修源码排除出评分

**状态：路径分类已证实，具体题目误判频率未知。位置：** `R/adapters/slime/prepared_task_face.py:201–206`、`R/grading/trusted_projection.py:79–89`、`R/grading/manager.py:536`。

默认 `*tests/*`、`*testing/*` 按 fnmatch 匹配，`*` 会跨 `/`。因此 `pandas/_testing/_io.py`、`numpy/testing/_private/utils.py` 均会被判为 test_glob，本轮已调用真实分类函数确认。这些目录可以是随包发布的测试辅助代码，也可能正是 issue 要求修复的内容。

例：模型正确修了辅助函数，冻结产物有该变化，但可信投影把它当评分控制面改动、不重放；fresh grader 测的是旧函数，正确候选可能拿 0。不是每次命中都必然 reward 0，还取决于题目和其它改动。

需要按任务区分“允许求解的文件”和“可信评分控制文件”。仅改 exact official 文件列表也不自动覆盖 conftest/plugin 等攻击面；这应由 B 的任务适配声明与 A 的投影实现共同闭合。

### I09　评分防护有未闭合边界，不能据此整删现有 F2

**状态：已有保护与剩余边界均存在；设计待决。位置：** `R/grading/manager.py:1936–2000`、`R/adapters/slime/sandbox_profile.py:1260–1304`；当前简报 §5 的 Wave3 边界。

这里 F2 指“官方测试文件归 root、候选代码非 root、目录保护与读回”，不是本导读 I05 的 Codex F2。它能阻断候选 import 时改写后续将执行的官方测试。与此同时，stdout 假测试结果、插件/解释器/辅助控制文件影响等不能仅靠官方文件只读解决；哪些面实际开放仍须按最终 adapter 实测。

因此“旁边还有漏洞，现有防线无价值”推论不成立。要同时比较误杀正常解、阻断哪些攻击、运行成本，才决定缩到哪一层。对 official patch 删除/改名后缺失路径，当前保护会拒绝；旧 216 题没有此类删除/改名，不是已观测的大面积丢题。

### I10　文件冻结范围与表示可能放大产物，并限制某些合法重构

**状态：实现范围已确认，成本与任务影响待测。位置：** `R/adapters/slime/baseline_census.py:61–78`、`R/contracts/frozen_patch.py:129–134`、`R/grading/manager.py:1795–1808`。

census 会把未排除的缓存/构建文件算进文件变化。新 `.pyc`、`.pytest_cache` 等可变成 inline base64 条目；grader 逐项 `docker exec` 重放。如果一次测试留下 500 个新文件，就可能多出 500 次条目重放——这是条件例子，不是本项目已经测得每题都有 500 个。不能为 SWE 一概删掉所有构建产物，因为某些 terminal 任务的答案本来就是产物文件。

另一处是父子路径冲突校验：合法的“删除文件 `config`，新增 `config/default.json`”被拒绝，虽然 apply 逻辑已经先删后写。旧报告给的 `module.py`→`module/__init__.py` **不构成父子路径冲突**，例子应纠正。是否扩展这一产物契约，要看任务面；当前不知实际影响题数。

### I11　grader 的资源终止可能被误读为模型测试失败

**状态：可达的归因风险，未测实际 OOM 率。位置：** `R/adapters/slime/sandbox_profile.py:492`、`prepared_task_face.py:85–92`、`R/grading/manager.py:1993–2002`。

默认 grader 4GiB；候选测试脚本不因任意非零命令立即终止，manager 最后主要看日志，丢掉了候选 result 的退出码。若子进程因 cgroup 内存限制被杀，但容器/shell 仍活着，可能留下部分测试日志并被判 tests_failed 或零解析。

例：修复本来正确，测试峰值需要 5GiB；4GiB 限制杀死测试，不等于修复错了。反过来，候选引入无限内存增长也不能无条件宽恕。需要结合 exit code、cgroup OOM 事实、可信基线与预算判断；137 单独也不能证明 OOM。旧建议“所有 grader 改 16GiB”不是无成本修法，会改变同机并发和任务预算。

## 4. 生命周期与取样：失败后发生了什么

### I12　receipt 写失败会跳过尚未释放的容器清理

**状态：已证实、与现行 A4 要求冲突。位置：** `R/adapters/slime/generate.py:3598–3620,3646–3652,3767–3775`。

receipt 是交付前的执行记录。旧实现选择“写不出证据就保留现场”：非 S1 路径 receipt 失败时跳过 session drop 和 container cleanup。现行计划要求关键记录失败要 fatal，**同时继续清理**。

旧故障注入例：harness 在冻结前失败，随后写 receipt 遇到 ENOSPC，结果没有交付、也报 fatal，但容器被 quarantine，正常清理未执行。不是每次 receipt 失败都留容器：成功冻结后容器已提前释放的路径不受同样影响；服务关停也可能随后撤销 session。问题是这个特定旧分支及锁住旧行为的测试 oracle，不能只靠“测试通过”判断符合现合同。

### I13　关停期限、最终清理和 run 成功被合成一个 verdict

**状态：机制已证实；是否修改属于合同取舍。位置：** `M/rollout/fully_async_rollout.py:297–308`、`M/utils/rh2_shutdown.py:228,295–296`、`R/shutdown/chain.py:333–334,434–463`。

miles 第一阶段取消等待默认 60 秒；RH2 后续还有自己的清理预算。第一阶段超时会留下失败，即使稍后清理完成，最终仍 `ok=false`。本轮缩时探针同时复现了期限内成功和“10ms 超时、60ms 清完仍失败”对照。

这不是“所有正常结束都会失败”；并发取消通常不必跑满每个上限。也不是当前合同 bug：B-6 已批非 ok 非零退出。需要讨论究竟要区分 trainer 完成、期限履约、实际残留，还是保留合成结果。evidence 写失败不阻止后续 cleanup，但仍影响 ok，也符合现设计。

相邻维护项包括：非主线程 signal handler 接线不可用；buffer 关闭后是否还要 drain grader；late facts 合并是否必要；Ray 包装后的异常按文本比同源可能失效、截断 traceback 可能遮住根因。它们应逐条核实际 owner 和记录用途，不能一起称为“2600 行都可删”。真实 Ray 例子的频率本轮未验证。

### I14　Python 等待超时不等于 Docker 内的工作已经停止

**状态：当前取消实现有缺口，残留窗口未量化。位置：** `R/grading/manager.py:95–109,1463–1470`。

`asyncio.wait_for` 取消等待时，`run_docker` 没有主动终止/回收宿主上的 docker CLI。容器内测试通常要到后续 `finally rm -f` 才被终结。例：Python 已宣布测试超时，测试进程仍暂时消耗 CPU/内存，会影响后续并发。

应明确取消、宿主子进程回收、容器内进程停止的责任。单加 `proc.kill()` 只能针对 CLI，不能凭此宣称容器内测试也停止；需要验证最终容器清理。旧“约 8 行统一”不是完整生命周期证明。

### I15　完整组丢弃和异步 staleness 可能改变训练分布

**状态：选择机制已存在，实际偏差待测。位置：** `M/rollout/fully_async_data_buffer.py:235–330,407–447`、`R/adapters/miles/drop_events.py`。

当前要求固定 n 个 member 全部合格；一个缺员可以丢整组。假设每个 member 独立有 2% infra 失败，n=8 时完整组存活率是 `0.98^8≈85%`，并非 98%。这是帮助理解的独立性模型，实际故障通常相关，不能拿它当实测。

fully async 先拿到完成结果、消费时按版本 lag 丢旧组，可能更常保留快/短任务。对已完成样本按 index 排序，并不能恢复那些尚未完成或已被丢掉的任务。compaction、预算和评分失败还会叠加选择面。

现有 drop 事件有原因和身份，但缺足够的轮数、长度、耗时和详细终止归因，无法回答“丢弃的是不是长/难轨迹”。需要比较生成→完成→消费各阶段的分布。N=2、全员 KEEP_FULL 是已定框架/候选取值，不因可能偏置就自动换成部分组或 FIFO；阈值和策略收益要用数据决定。

### I16　缺少对已归因瞬态 infra 故障的有界重试

**状态：能力取舍，非遗漏现成的已批实现。位置：** 06 计划 A2、`M/rollout/fully_async_data_buffer.py` 的 ABORTED/drop 处理。

当前一次真实暂态失败可让整组被弃用。例：7 个成员都完成，第 8 个评分遇到一次短暂 Docker 服务错误；完整组策略会浪费前 7 个成员的产出。若故障确为暂态，一次有限重试可能更便宜。

但不存在“凡 infra 都值得重试”：镜像名错、parser 缺失、权限配置错误不会被重试治好。重试还涉及 attempt identity、剩余预算、是否重新采样及 stop 行为，可能影响分布。先测按原因损耗，再决定是否加入；不直接采用旧报告“80 行、不引入状态、5% 阈值”的估计作为定案。

## 5. 数值与动作来源：计入 loss 是否代表学到了

### I17　DIS accepted 不等于有训练信号，零梯度也不只一种原因

**状态：数学与当前实现均已确认；监控缺口。位置：** `R/adapters/miles/faithful_dis_loss.py`，miles 零信号 patch 0002/0003，`rh2/experiments/miles_gpu_spike/custom_config.yaml:27`。

采样支持集只有一个 token 时，支持集内归一化概率永远是 1，logprob=0、ratio=1，会被 DIS 接受，但这项对 logits 的梯度为 0。本轮真实 CPU loss 探针得到 accepted=2、rejected=0、loss=0、最大梯度=0，现有 zero-contribution metric 却为 0。因此 accepted 只是通过裁剪判据，不能当作有效更新 token 数。

支持集大于 1、advantage 非零也不保证最终参数梯度非零：多个样本梯度可以相互抵消。这是数学反例，不是断言真实大模型频繁精确抵消。

旧“无限静默跳过”已纠正：候选配置已设连续零信号熔断 8 步。仍需观察 singleton 占比、skip 和最终有效更新；若想把扫描替换为 `grad_norm==0`，必须证明分布式归约时点和数值等价，不能凭一个标量名字删除已批行为。

### I18　R3 路由形状对齐，不等于仍来自原始采样 forward

**状态：来源选择已证实，GPU 数值后果待定。位置：** `R/adapters/slime/generate.py:1427–1508`、`capture_wire.py:1060–1066`；SGLang pin 证据见运行追踪 RT-8。

R3 保存 MoE token 选中的专家并在训练重放。当前多轮叶链取最后一轮的整段 tape，早轮 logprob/version 却仍保留最初采样的值。旧真实装配探针设第一轮 route=1、第二轮 route=7，最终早轮 token 的 replay route 变成 7，旧行为 logprob 仍为 −0.1/−0.2。

跨 publish/retract 或下一轮落到冷 engine 时，历史 token 会重新 prefill；最后整段 tape 可能记录这次重算的路由。因此不能仅用行数与 token 对齐证明行为路由一致。这里与 I01 不同：即使训练覆盖完整，路由来源仍可能不同。

要决定接受最后整段重算近似，还是要求更强的行为来源保真，并实测 route agreement、logprob/ratio 与训练影响。逐轮拆分不解决**单次请求内部 retract**；拼旧行也不自动恢复一致的 KV/隐状态因果路径。当前没有证据可以直接宣布 DIS 公式错误，或宣布某个简单拼接修法已成立。

### I19　上下文收缩有既定拒绝面，压缩不能透明接入

**状态：已知 profile 限制，实际频率待测。位置：** `R/adapters/slime/generate.py:1100–1134,2862–2868,2894–2905`。

启用 `reject_context_shrink` 后，同一叶链后轮 prompt 小于此前最大值的 60% 会被拒绝。例如 20k→10k，低于 12k 阈值，可成为 capture_incomplete/missing，继而丢组。session 级全局收缩只作 audit，避免把新子 agent 的独立短历史直接当异常。

这与 REALIGN 不同：一个是旧动作被清 mask，一个是整条执行失去训练资格。它是已批 compaction 兜底，不能直接列为“应删的 bug”。首训要明确真实 CC 历史压缩是否允许；支持压缩、分支或多 harness 都需要确定训练视图和来源，不能只把 threshold 关掉。

### I20　在线诊断不够完整，也还没有可靠汇总到作业结论

**状态：已有能力与缺口并存。位置：** `M/backends/megatron_utils/actor.py:483–521,625–665`、`R/adapters/miles/faithful_dis_loss.py:778–789`、`R/adapters/miles/drop_events.py`。

已有 `logprob_compare`，不是“在线训推对拍全无”。但 custom loss 的主要统计还是 accepted/rejected 等，缺支持集大小、ratio 两侧拒绝、长度维度覆盖、详细 drop 原因与可靠 collector 消费。`bringup.generate()` 没被 miles 调到，不等于 execution audit/shutdown 也都没事件；需按实际 producer→文件→汇总器逐条看。

例：DIS 拒绝率从 5% 升到 50%，可能是策略更新正常移动，也可能是版本或数值失配。跨版本 log-ratio 混合这两种影响，直接命名为 mismatch KL 不能把它们分离。需要同版本对拍和跨版本策略移动诊断各有口径。下一阶段要的是能帮助定位/选参数的少量指标，而不是新增一套无人消费的事件。

### I21　W8 真实 eval 运输与 checkpoint 绑定尚未闭合

**状态：已知正式评测前置。位置：** `R/adapters/miles/generate_fn.py:142–176`、06 计划 W8。

当前 formal 身份铸造仍假设训练组的 index/slot/n_samples 关系；stock eval 不遵循同一算术，直接照搬会失败。共享引擎 eval 还要处理 producer、grading 和权重更新的停稳，以及明确评的是哪个 checkpoint。

例：名义“after checkpoint 20”，实际有题在更新前开始、有题在更新后开始，即使最终平均分能打印，也不能把它归给一个确定模型。只加 `if evaluation` 绕过训练身份校验，不能证明任务/模型绑定和失败传播正确。A 负责实际运输、停稳与结果绑定；B 负责题目、协议、预算及统计。基座诊断可以先用经说明的窄入口，不必等所有训练优化完成。

### I22　W7 launch/恢复仍是前置；显式恢复编号存在错配风险

**状态：草案接线未完＋条件性恢复绑定风险。位置：** 06 计划 W7、`R/adapters/miles/generate_fn.py:80–95`、`M/utils/rh2_recovery.py:227–232`、`M/backends/megatron_utils/actor.py:205–220`。

目前实验 launch 是待重生成草案：模式/filter、disposition、外部清理 trap、resume/run_id、no-progress 数值、事件 collector/judge 都应从最终 C 范围接齐。把默认 s1_compat 改 formal、换一个 filter 并不能完成 W7，也不是纯文案修复。checkpoint 每步保存适合 spike 还是正式长 run，也需按成本选择。

冷恢复另有具体条件风险：实际加载 checkpoint 10，却显式指定 `start-rollout-id=21`；若目录里有 rollout 20 的状态，trainer 与 RolloutManager 都可按 20 读状态、互相一致，却没有与权重 10 配对。没有显式 override 或相应状态缺失时不走同样结果。本轮是源码证明，未跑真实恢复；最终 launcher 是否开放该 override 尚未定。

与此分开，当前恢复 bootstrap 标旧 p、后续更新 p+1 是 B-3 已批合同；旧在飞组/buffer 全丢，跨 run 看版本必须带 run_id。改成另一个编号不属于“免费修 bug”，也不自动实现跨任意回滚的全局唯一版本。checkpoint 保存与恢复状态文件不具通用原子联合提交；缺 sidecar 时停止是已知最小恢复边界，不是已承诺透明恢复后失效。

## 6. 吞吐与容量：哪些工作正在重复做

性能项的排序应以**当前合格组/GPU-hour、时间到目标分数、资源占用**为依据。旧 P3 的 23 分钟 step 可以说明旧作业 rollout-bound，不能直接证明当前路径哪个环节占比最大。以下都没有本轮 GPU 加速数字。

### I23　R3 捕获在 adapter 事件循环上做大张量转换，并逐轮双份保留

**状态：正常热路径与历史 CPU 成本已证实。位置：** `R/adapters/slime/capture_wire.py:737`、`projection.py:140–171`、`generate.py:950–990,4732–4735`。

全前缀 routing 从 base64/int32 变 Python list，再 pack 回 bytes，同时保留 tuple 与工件。同步处理发生在 adapter 的事件循环里，其它请求与取消也要等。历史真实 capture 探针 8K/16K/32K 行约 86/172/346ms；不是旧切片估计的“已经实测每轮 3–6 秒”。

数值例子：32K token×48 层×8 路由项，原始 int32 是 48MiB，base64 是 64MiB；tuple 指针＋packed bytes 常驻下限约 144MiB，尚未算临时副本。多轮并发会继续累积。50 轮、平均 16K、32 个存活执行的下限估算可到 112.5GiB，但这**不是实际 RSS/OOM**。

这是很明确的紧凑表示/减少转换候选。不能只保留 session 最后一条 tape：不同叶可能各自需要末轮数据；也不能把表示优化和 I18 的行为路由来源决定混在一起。移线程还需保证 commit 顺序、生命周期与真实 loop 延迟收益。

### I24　当前 custom loss 配方下存在额外 actor forward 优化空间

**状态：控制流与限定 CPU 等价已核，GPU 收益待测。位置：** `M/backends/megatron_utils/actor.py:625–666`。

当前零 KL GRPO/faithful DIS 不靠预先计算的 actor logprob 数值形成目标，训练 forward 又会重算 current logprob；优势侧部分消费只是 shape。但预先的 forward 同时生产 I20 的对拍证据，所以不能叫“完全无用”。

`use_rollout_logprobs=true`、`get_mismatch_metrics=false` 可跳过；同时打开 mismatch 则仍运行。后续可以比较普通训练与诊断时如何保留对拍。旧 CPU probe 支持限定配方中优势/loss/梯度一致，不能推广到 PPO、OPD、reference KL，也不能据此声称端到端节省 20–30%。

### I25　每次执行重复安装、改权限、建连接、轮询和操作网络

**状态：重复路径存在；真实耗时待测。位置：** `R/adapters/slime/bringup.py:304–315,355–362`、`sandbox_profile.py:736–796,965–968`、`capture_wire.py:1084,1121`、`S/agent/sandbox.py:63–77,375–384`。

已可信初始化权限后，还会执行两处类似 `id agent || useradd ... && chown -R ...`。shell 将它视为 `(A || B) && C`；已有用户也会做 C。本轮无副作用 shell 替身再次确认 CHOWN/GIT 被调用。因此注释中的“幂等短路不再扫描”不成立。

另有每容器上传/解压/安装 CC、每请求新建 HTTP session、5 秒一次 docker done-marker 轮询、每 attempt 创建/接入/拆除网络。600 秒最多约 120 次轮询，不代表每题都发生 120 次；Claude 的“约 53 次固定 Docker 调用”是指定路径估算，异常/文件数会改变次数。

这里有摊销空间，但镜像预装、只读共享安装、连接池、持续等待、网络复用各自改变不同边界。先测安装/权限/网络/poll 分段耗时，再选窄修法。尤其 fresh grader 的独立权限初始化不能算作 rollout 同一操作的重复而顺手删除。

### I26　census、摘要与持久化重复付费，但并非每次检查都等价

**状态：重复工作可定位；等价简化待证明。位置：** `R/adapters/slime/baseline_census.py:61–78`、`generate.py:2671,4687–4735`、`patch_exporter.py:140`、`R/grading/manager.py:1541–1739`、`bringup.py:180–201`。

基线、运行后、fresh grader 都有 census；每文件 shell 调 `sha256sum|cut`。大树既重复读内容又频繁起进程。相同对象也会多次 JSON/Pydantic 往返、重算 digest；baseline、patch、receipt 等分别 fsync/目录 fsync，突发完成可能拖慢 owner loop。

例如同一不可变镜像的基线可考虑按内容复用，但 fresh grader 的实际树、容器挂载/权限不能只由镜像名字保证。缓存一个摘要后再比较摘要，也不再检测对象是否被改。可讨论批量 hash、不可变对象、减少反序列化、共享持久化基线；必须保留“必要记录落稳后才交付”与实际重放集合的绑定。没有证据支持把全部 hash/inspect 一刀切掉。

后端还有另一组开销，不能漏计也不能与 capture 重复相加：rollout manager 与训练 rank 会对 routing tape 做 `tobytes/sha256`，事件同步 open/write/close；零信号判定还扫描梯度并同步标志。它们是为了消费归属、对拍与更新判定存在的，部分可讨论诊断分档/移动到扩展点，但尚无真实耗时证据。旧“每步 hash 十几 GB、浪费几十秒”是条件估算，不能据此删掉唯一证据 producer。详见性能报告 P10。

### I27　多 engine 前缀局部性、retract 与 JIT drain 有性能取舍

**状态：机制存在，拓扑收益待 GPU 比较。位置：** `M/router/router.py:134–162,215–230`、`M/backends/megatron_utils/update_weight/update_weight_from_distributed/mixin.py:309–331`、集成根 `train_async.py:119–121`。

adapter 发 session routing key，但 router 按最少活跃请求选 engine，没按该 key 路由。连续轮换 engine 可能损失前缀缓存；单 engine 没这层问题。最小负载不是均匀随机，**不能推出命中率=1/N**；另一个 engine 也可能缓存了更早前缀。

publish 的 retract 可导致历史上下文重 prefill；in_place 的数值/版本/R3 边界又需要单独资格验证。JIT drain 让 staleness 在正确消费时点判断，代价是部分 convert/drain 不再与前一训练步重叠；producer 仍持续并发。

比较 1×TP4/2×TP2 时，应测 cache、prefill/decode、排队与实际合格产出。不能为了缓存直接批准 hash 路由，也不能为了重叠撤掉消费时版本权威。旧“35 秒/6–12%”等都是假设计算，不能写成项目优化结果。

### I28　并发额度、评分队列与镜像供给还没有按实测容量定档

**状态：配置可核，瓶颈尚未测定。位置：** `R/adapters/slime/bringup.py:608,1001–1007`、`R/grading/queue.py:153–203`、`R/grading/manager.py:1273–1289`。

model_call 默认 32、候选 miles 在飞 member 64、grader 4、等待槽 8，单位不同。执行还会等工具和评分，所以 `32<64` 不证明模型限流必拖慢 GPU；`4<64` 也不证明 grader 必是瓶颈。

条件例子：每秒完成 0.1 条 rollout，评分平均 60 秒，稳定负载约需 6 个忙碌评分位；4 个就会积压。若平均只需 5 秒，则可能充足。评分完成前仍占 miles 执行名额，队满有背压。再加首批镜像懒拉取，网络/磁盘可出现冷启动尖峰。

按 stage service time、queue wait、CPU/RAM/I/O 与镜像冷热定参数；选择任务后可先预拉镜像。不能直接把并发与内存各调四倍，也不应为尚未测出的瓶颈建设环境池服务。

### I29　长 run 的历史对象、日志和工件缺少完整容量边界

**状态：部分历史记录列表无裁剪已确认，实际内存增长待测。位置：** `R/grading/manager.py:873,1253–1263,1360–1367,1949–1976`、`R/grading/queue.py:117`、`R/shutdown/resource_closure.py`。

manager records、leases、queue events 等可长期累积，记录包含 inspect、setup/partial log 等；其中一些列表没有按完成生命周期释放。计时 deque 有上限，不代表所有历史状态都有上限。R3 多轮数据另见 I23；磁盘工件与可写层配额也不能由 buffer 容量推导。

例：若每条历史记录实际 100KiB，2 万条就是约 1.9GiB；这是条件估算，不能称已测 RSS。资源估算器已经标注部分 unknown/unbounded，并非假称有硬上限，但没有充分计入 R3。后续要区分还用于清理的活状态和可以落盘/裁剪的历史记录，并记录峰值；删除诊断估算器不会解决容量问题。

### I30　训练侧 dense logits/support 与分支前缀重复计算

**状态：上游表示成本与当前继承面；收益待测。位置：** `M/backends/training_utils/loss_hub/` 的支持集处理、`R/adapters/miles/faithful_dis_loss.py`；Claude A F-11、G 训练效率表。

训练侧支持集掩码和 fp32 logits 可能占显存；词表×token 的 dense 张量即使最终很多 mask=0，也要先生成。多叶 fan-out 共享前缀只计一次 loss，可以避免重复计权，**不自动避免前向计算重复**。

例：一个 10k 前缀展开 4 个叶，梯度权重可正确只计一次，但某些表示仍计算多份前缀。不能用“减少到一条长序列”就宣称梯度语义等价：不同条件历史、共享动作、execution 分母、optimizer 更新边界都要保留。先测 TP/CP 分片后的显存峰值、重复 token/FLOPs 和内核成本，再决定是否值得改上游表示。

## 7. 维护与文档：哪些复杂度可以真正拿掉

### I31　身份、结果和终止事实有多份表示，单一所有者不够清晰

**状态：维护/架构候选。位置：** `R/contracts/fa_runtime.py:102–143`、`R/envpack/termination_facts.py:217–373`、`R/governance/admission.py:198,334–525`、`R/adapters/miles/generate_fn.py:52–78,167–214`。

身份字段被复制进多个 payload；outcome、admission、termination facts、派生视图之间反复转换/对账。一次加字段可能改五处，容易出现“全部自检通过但语义理解不一致”，也让 agent 为每个副本加更多 guard。

可以考虑不可变 execution context、组合身份、集中构造与边界消费，但目前不是完全同义副本：termination facts 还带 receipt/静止/冻结事实；assignment registry 跨整个 await 生命周期，并被任务和评分材料解析使用。删 registry 前要给状态一个明确 owner；合并 payload 也要保留持久化先于交付。只运输 verdict 不足以绑定实际 Sample。

### I32　重复防御需要按边界收敛，不能按“防自己 bug”统一删除

**状态：局部简化候选，旧删除比例未证。位置：** `R/adapters/miles/group_admission.py:304–338,415–476`、`faithful_dis_loss.py`、`canonicalize.py`、`R/envpack/prepared_tasks.py` 与评分/shutdown helper。

候选包括：每 microbatch 重复检查静态配置、同对象反复 schema 重验、字段集断言、同源 digest 重算、drain callable/latch 互检、停进程后的双读指纹、重复版本 span 校验、实例已确认后再验相同不变量。

但真实组边界不能只保留 slot。例：8 个 slot 齐，slot 3 的一片叶却属于另一题，或 reward/version 不一致；仅 slot 校验仍会放行。publish ack 与 engine 实际读回也不是同一证据；读回标签本身又不能证明权重张量已正确同步。

后续逐处回答：事实是否不可变、跨了哪个异步/运输/所有权边界、哪个唯一消费者负责验证、失败是否正确暴露。19 个静态检查位置不等于每 execution 固定查 19 次，130 个拒绝点中“不到 10% 真实”也不是生产统计。I05 要求内部 bug 暴露，与此处要求合并冗余检查并不矛盾。

### I33　未接线原型、旧模式和测试需要分开清理

**状态：部分窄清理证据强；大范围删除未批准。位置：** `R/adapters/miles/attempt_ledger.py`、`governed_buffer.py`、`R/adapters/slime/async_worker.py` 及专用测试。

最明确的原型面是 attempt_ledger 394 行＋governed_buffer 260 行，专用测试 572＋252 行；当前候选配置用 dynamic filter，没有接这个自定义 buffer。可以独立讨论删除/移出并同步清理导出，收益是维护面而非吞吐。

其它必须分类：旧 FA worker 不等于仍活跃的 ModelCallProxy；s1_compat/旧 diff/离线导出/CLI/历史 inspector 有各自消费者；`adapters/slime` 正是当前 miles 共用执行层，不能因目录名就删。`GroupRepairSignal` 等不参与 miles 准入，也不等于所有 telemetry/旧入口无消费。

测试同样三类：测将退役能力的测试随能力处置；重复 fixture 可合并；锁住错误旧语义的 oracle 要按新合同改。零 import、测试只调 helper、7.1K/4.2K 行估计都不能自动证明测试没有价值。不得把减少覆盖或跳过资格用例包装为通过。

### I34　legacy/reference 体积与 miles fork 是维护负担，不能混为训练瓶颈

**状态：仓库组织/依赖维护候选。位置：** 旧 `src/repo_harness/`、`reference/`、miles integration patches/manifest；详见性能报告 M07/M09。

旧报告统计约 199K 行 legacy、2.2GB reference，描述的是当时目录快照。有些承担历史复核和论文原页证据；未跟踪 clone 不进入主仓对象库，且可能有本地改动。归档可以改善导航，但不能据“rh2 零依赖”删冻结 evidence 或重写历史。

miles 的 16 个 patch 中，事件、零信号、shutdown、消费时版本、恢复等扩大了维护面。旧“上游领先 302 commit、9/16 难 rebase”是 9 月 5 日快照，本轮没有重新比较最新上游，也未执行 rebase。当前 pin 上不用某条 stock 路径，不证明整 patch 无消费者；新上游同名能力不证明相同合同。首训前没有由这些证据推出必须迁框架的结论。

### I35　文档、默认值与局部兜底制造错误的可用性印象

**状态：文案漂移、可达性与前移验证候选。位置：** `R/grading/manager.py:1506–1539`、`R/contracts/eligibility.py:98–100`、`R/adapters/slime/generate.py:4183–4216`、`projection.py:694–700`。

需要登记的具体小项：`_clean_checkout` 在 image_embedded 路径主要探 lineage，真正清洁来自 fresh 容器＋不可变镜像；旧 docstring 仍描述提前 staleness gate；`calculate_per_token_loss` 文案混淆 microbatch 平均与全局 token-mean；“无 trainable token 在 admission DROP”之前可能已被 projection 异常转 ABORTED；缺 filter 等配置错误有的到首个 dispatch 才发现。

`seen or [current_version]` 兜底也应改进事实措辞，但**不能报成已证 formal 版本绕过**：正常 formal 入口先强制真实数值版本，每叶 backfill 缺版本先拒，成功后 seen 非空，才到 handshake。给 helper 人工塞空输入能触发，不等于生产可达。security/policy-horizon 等预留槽无 producer 要明示支持范围；不是没有任何 sandbox 安全措施。

本主题的风险在于新人照旧文档调错入口、误判某项已实现或重复加门。应保持一份明确的当前能力说明；不为每个过时句子另建 inspector。

### I36　尚缺真实 GPU 与完整实验闭环证据；未来能力按需要加入

**状态：已知资格/项目交付前置。位置：** 06 计划 W8→C→W7→GPU，原审查 §7、当前简报。

已有局部 CPU/离线算术与故障探针不能代替目标 GPU 上的 CP/TP、MoE replay、版本发布、kill/watchdog、checkpoint 恢复、长 run 容量与真实 eval。当前没有完整同数据/同预算 before/after、性能消融、故障损耗与学习结果的联合证据；这是项目一说服力最终要补齐的部分。

OPD 在 miles 有能力，但 RH2 的 teacher 对齐/打分还不是已跑通产品；多 harness 当前主要是 CC 与 mock，不能写成已经验证所有 harness。暂时不接 OPD、多 teacher、通用压缩训练、serverless 或第二后端不等于首训 bug。应先把项目一的 SWE/terminal 窄闭环做成，再按瓶颈或研究假设补能力，而不是把论文功能表逐格实现。

## 8. 哪些旧结论不应继续按 bug 使用

| 旧表达 | 本轮准确结论 |
|---|---|
| 训练核心算术都对，所以训练语义正确 | 给定 mask/样本下的算术验证有价值；不能证明动作覆盖、失败选择和真实 GPU 路由来源。I01/I05/I18 仍重要。 |
| 每条多轮都丢首轮，只要 clear_thinking=False 就能修 | 有 CLEAN 与 FORK 对照；实际模板不读这个开关。 |
| custom loss 完全没有在线对拍，额外 forward 毫无消费者 | 对拍存在，额外 forward 正是它的 producer 之一。 |
| 零方差过滤后梯度不可能为零，当前无限跳过 | singleton 和梯度抵消均为反例；候选已配连续 8 步熔断。 |
| 600 秒超时必立即触发未注入 disposition | 需先形成可处理的 truncated，之前可能已 DROP；这是已知 C/W7 前置。 |
| timeout / 零解析全改 0 | 先归因；环境缺失也会同样失败。 |
| 有 stdout 攻击面，F2 因此没价值 | 不同攻击面；删除会重新打开已阻断的官方文件改写路径。 |
| 60 秒比后续清理预算短，所以正常结束必失败 | 只证明早期期限超时可保留失败；有正常成功对照；是否改退出码属合同选择。 |
| 同源、同进程检查一律冗余 | 跨 await、组汇合、可变对象和运行实体仍是实际边界；可以集中验证。 |
| seen fallback 已经让 formal 无版本样本入训 | 正常 formal producer 在前面就建立版本或拒绝；helper 可触发不等于正式可达。 |
| N engine 缓存命中必为 1/N，grader=4 必是瓶颈 | 都需要真实路由/队列/服务时间测量。 |
| 约三分之一代码测试可以直接删 | 只是旧候选规模，混有公共能力、已批语义与历史复核；窄原型清理证据更明确。 |

## 9. 新资料只作为相关问题的定点参考

本轮同步了远端内容，**没有把 Pro 作者自查升级为独立审查通过**。只定点看与上述问题相关的笔记；没有重读全库或重新核实这些论文的全部实验数字。以下是后续方案验证入口，不是论文替本项目批准设计。

| 笔记 | 与本清单的联系 | 不能由此推出 |
|---|---|---|
| [RollArt](../../../../harness_improve/external_paper_references/reading_notes/R11_rollart.md) | I15/I23–29：按环境、推理、评分、训练关键路径测有效吞吐。 | 其资源和异构拓扑不同，不能搬用加速倍数。 |
| [Polar](../../../../harness_improve/external_paper_references/reading_notes/R0_polar.md) | I01/I28/I30：阶段解耦、前缀合并需同时看动作覆盖和计权。 | token/时间减少自动意味着同样训练目标。 |
| [Agent Lightning](../../../../harness_improve/external_paper_references/reading_notes/agent_lightning_v1_2608.17528.md) | I01/I31/I34：精确前缀边界、同次更新与窄 adapter 分工。 | 可以不检查上下文条件就把多轮合并，或按其行数设删除目标。 |
| [SAO](../../../../harness_improve/external_paper_references/reading_notes/R15_single_rollout_asynchronous_optimization.md) | I15/I24/I27：去组等待与新增 critic 成本需要一起比较。 | single-rollout 等于每收到一条就更新，或本项目必须放弃 GRPO。 |
| [CompactionRL](../../../../harness_improve/external_paper_references/reading_notes/R14_compaction_rl.md) | I01/I19/I30：压缩改变段结构、动作和成本，不只是缓存。 | 关掉收缩拒绝就实现了正确压缩训练。 |
| [Harness Interplay](../../../../harness_improve/external_paper_references/reading_notes/E1_harness_interplay_posttraining.md) | I21/I36：模型和 harness 更改应分开归因。 | 非 SWE 实验的结论直接保证本项目工具改动有收益。 |
| [Hardening Agent Benchmarks](../../../../harness_improve/external_paper_references/reading_notes/N06_hardening_agent_benchmarks.md) | I08/I09：检查防护时同时重放合法解，避免只优化攻击拦截。 | 新增越多防御越好，或已有 fresh grader 必须重做论文全部防线。 |

精确章节、原始来源与未核范围详见性能报告 §4；N06 本轮主要参考其 §9–10 的边界说明，没有把表中数字作为本项目证据。

## 10. 建议的讨论顺序与双方接口

这只是讨论顺序，不批准任何具体修法：

1. **I01＋I18＋I19：真实动作与上下文来源。** 先说明 CC 会怎样改消息、哪些动作必须训练、允许什么压缩/R3 近似。I01 是最明确的优先项，直接影响是否学到前序决策。
2. **I02–05＋I12–14：预算、异常分流、receipt、取消与关停。** 将已证局部 bug 与需 owner 决定的终止/退出策略拆开，避免所有问题都用新增 fatal/重试处理。
3. **I06–11：与 B 联合闭合评分归因与允许的文件变化。** B 给参考修复、错误修复、空补丁和环境故障例子；A 提供可追踪的退出/资源/投影事实。
4. **I15–17＋I20：让损耗和有效更新可以解释。** 这些数据才足以选 staleness、重试、预算和并发。
5. **I21–22：完成真实 eval 与作业/恢复接线。** 与 B 的窄基座诊断并行准备，不必等所有清理候选做完。
6. **I23–30：以测量选性能改动；I31–35 独立窄清理。** 避免先大删/重构导致原始瓶颈基线消失。I36 最终用真实训练和评测闭环验证。

本任务后续记录在 [A 留言板](../infra.md)；任务适配/评分协议的共同决定同时给 [B](../env_data_eval.md) 留可引用条目。本轮未向其它用户任务发送消息，也未代表 B 接受交付承诺。

## 11. 本轮验证与材料

主审复用旧探针脚本，以现有 `rh2/.venv/bin/python` 运行，不安装依赖、不改标准测试。四项均退出 0，表示**再次复现现状/反例，不是问题已经修复**：

| 探针 | 本轮输出 | 范围 |
|---|---|---|
| realign_probe.py | [realign.log](probes/realign.log) | 已缓存 tokenizer、真实消息翻译/manager、合成消息；非实际 CC 请求录制。 |
| runtime_probe.py | [runtime.log](probes/runtime.log) | 真实 proxy/cap/关闭逻辑配替身、毫秒预算；日志 ERROR 是刻意故障注入，非真实训练停机。 |
| singleton_signal_probe.py | [singleton_signal.log](probes/singleton_signal.log) | 真实 CPU loss、简化样本；非分布式参数梯度普查。 |
| grading_classification_probe.py | [grading_classification.log](probes/grading_classification.log) | swebench 4.1.0 parser、合成日志/超时；无真实 Docker/题目成功率统计。 |

脚本与原始运行说明见 [旧探针说明](../../miles_spike/external_infra_review_crosscheck_20260906/README.md)。另外主审定点调用真实 HygieneRules，确认 I08 中的路径匹配；I10 路径例子对照真实 `/` 前缀校验纠正。其它性能数字标作历史 CPU 或条件估算。本轮没有重跑整个 pytest 集，也没有把旧通过数加作本轮验收覆盖。

## 12. 旧报告逐条覆盖表

这里的“覆盖”指每条旧主张都找到讨论落点，**不表示重新证明每条、接受原严重度或批准修法**。A/B 切片用 F-xx 编号，下面加切片前缀以免与 Codex F1/F2/F3 混淆；E/G 保留其不补零的编号。

### 12.1 Codex 原报告与交叉复核

| 原条目 | 本文落点 |
|---|---|
| Codex F1：capture 同步与 R3 驻留 | I23、I29 |
| Codex F2：内部错误变 ABORTED | I05 |
| Codex F3：receipt 失败跳清理 | I12 |
| Codex R1：最终 tape 路由来源 | I18 |
| Codex C1：未接线 ledger/buffer | I33 |
| 原报告 §7–8 的组保留代价、诊断/性能/维护边界 | I15–17、I20、I23–36 |
| 交叉复核 §2：训练覆盖 | I01 |
| 交叉复核 §3：cap、排队与 chown | I02、I03、I25 |
| 交叉复核 §4：forward、mismatch、singleton、zero fuse | I17、I20、I24 |
| 交叉复核 §5：评分归因 | I06–11 |
| 交叉复核 §6–7：前置、shutdown、简化边界与顺序 | I04、I13、I21–22、I27–36 |

### 12.2 Claude A：训练语义（11 条）

| 旧 ID | 内容简记 | 本文落点/修正 |
|---|---|---|
| A-F-01 | 前序轮丢 loss | I01；限定触发，纠正 thinking 唯一根因。 |
| A-F-02 | staleness 丢长组 | I15、I20；偏差率待测。 |
| A-F-03 | singleton | I17。 |
| A-F-04 | zero-grad 跳过 | I17；已配阈值 8，替代判据待证。 |
| A-F-05 | 额外 actor forward | I24；保留对拍消费者。 |
| A-F-06 | disposition/cap | I02–04。 |
| A-F-07 | loss 守卫重复 | I32。 |
| A-F-08 | 两套 version spans | I32、I34；按真实消费者退役。 |
| A-F-09 | canonicalize 字段集与拒绝表 | I32、I35。 |
| A-F-10 | per-token loss 文案 | I35；非分母算术 bug。 |
| A-F-11 | dense support/fp32 显存 | I30。 |

### 12.3 Claude B：运行路径（22 条）

| 旧 ID | 内容简记 | 本文落点/修正 |
|---|---|---|
| B-F-01 | 多预算分流 | I03–04；不把所有墙钟结果等同 ABORTED。 |
| B-F-02 | 25 次上限 | I02；模型请求不是工具调用。 |
| B-F-03 | assemble 异常丢组 | I05。 |
| B-F-04 | 多轮 routing 重复保存 | I18、I23；多叶不能只留 session 最后 tape。 |
| B-F-05 | 三处 census/逐文件 hash | I26。 |
| B-F-06 | CLI 重装 | I25。 |
| B-F-07 | chown 与 shell 短路 | I25。 |
| B-F-08 | model-call 限流 | I03、I28；并发数不能单独证明瓶颈。 |
| B-F-09 | grader 并发/排队 | I28。 |
| B-F-10 | digest/census 重算 | I26、I32。 |
| B-F-11 | 旧 worker/notifier | I33；保留活 proxy。 |
| B-F-12 | outcome/termination/admission 副本 | I31。 |
| B-F-13 | drain owner/latch | I13、I32。 |
| B-F-14 | kill 后双读指纹 | I32；须证替代静止事实。 |
| B-F-15 | 每容器多次 image inspect | I26、I32；实例事实不能全按 image 缓存。 |
| B-F-16 | 控制流自洽 fatal | I05、I32。 |
| B-F-17 | fsync/每次 baseline 副本 | I26、I29。 |
| B-F-18 | 每 generate 新 HTTP session | I25。 |
| B-F-19 | done marker 轮询 | I25。 |
| B-F-20 | private bundle 反复 Pydantic 验证 | I26、I31–32。 |
| B-F-21 | 每 attempt 网络操作 | I25、I28；串行化时延须测。 |
| B-F-22 | bringup record_event/capture_stats | I20、I35；别推成整条链无事件。 |

B 非编号的 context-shrink 拒绝面另外落 I19。

### 12.4 Claude C：准入与治理（15 条）

| 旧 ID | 内容简记 | 本文落点/修正 |
|---|---|---|
| C-01 | disposition 未注入 | I04。 |
| C-02 | eval 身份 | I21。 |
| C-03 | security/violation/horizon 等槽 | I04、I09、I35；创建期安全≠执行违规 producer。 |
| C-04 | TerminationFacts 副本 | I31；还带 receipt/静止/冻结事实。 |
| C-05 | 多次身份/事实检查 | I31–32。 |
| C-06 | AttemptAssignmentRegistry | I31；跨 await，不是纯同栈查回。 |
| C-07 | GroupRepairSignal/GateOutcome/FinalizedRollout | I33；区分 miles 与历史/telemetry 消费。 |
| C-08 | handshake/seen fallback | I35；正常 formal 空 seen 臂未证可达。 |
| C-09 | identity 历史格式 | I32；格式也不能证明真实历史。 |
| C-10 | derived view keys 副本 | I31、I33；离线导出仍有消费者。 |
| C-11 | AdmissionWiringError 太晚 | I22、I35。 |
| C-12 | post-finalize fatal | I12、I13、I32；有 A4 记录合同，不能当无语义降级。 |
| C-13 | trusted controller/prepared face 防篡改 | I31–32；同进程不等于不可变。 |
| C-14 | no_trainable_tokens 到不了 admission | I01、I05、I35。 |
| C-15 | staleness 文案漂移 | I35；不是现存双重 age 过滤。 |

### 12.5 Claude D：评分（18 条）

| 旧 ID | 内容简记 | 本文落点/修正 |
|---|---|---|
| D-01 | SWE-Gym parser/spec 缺口 | I06。 |
| D-02 | test timeout 分类 | I07。 |
| D-03 | 零解析与 silent-success | I07；归因不能由空 map 决定。 |
| D-04 | cache/build 进入 delta | I10、I26。 |
| D-05 | test glob 误分源码 | I08。 |
| D-06 | F2 代价/其它攻击面 | I09；不能直接删非 root/official 保护。 |
| D-07 | failed_to_grade 大桶、无重试 | I05–07、I16、I20。 |
| D-08 | grader 重复检查 | I26、I32。 |
| D-09 | records/leases 无界 | I29。 |
| D-10 | grader 4/queue 8 | I28；瓶颈未证。 |
| D-11 | grader OOM/退出码 | I11；不是已测系统性 0 分。 |
| D-12 | frozen binding/projection 重验 | I26、I32。 |
| D-13 | SandboxLease/CleanupPolicy 旧路径 | I29、I33；局部消费者清理。 |
| D-14 | clean_checkout 名称误导 | I35；fresh 隔离仍存在。 |
| D-15 | self probes/quota 未强制 | I29、I32、I36；删探针不能补配额。 |
| D-16 | docker exec 取消 | I14。 |
| D-17 | 父子路径限制 | I10；纠正 module.py 例子。 |
| D-18 | S1 diff 兼容路径 | I33；未证 diff parser bug，退役另议。 |

### 12.6 Claude E：臃肿与测试（9 条）

| 旧 ID | 内容简记 | 本文落点/修正 |
|---|---|---|
| E-1 | 4549 行整模块候选 | I33；不用作已证明删除量。 |
| E-2 | worker 部分未使用 | I33；380 与 B 的 900 是不同范围，不能相加。 |
| E-3 | s1/审计/v1 旧模式 | I33；能力退役。 |
| E-4 | 重复抽象 | I31–33。 |
| E-5 | 死符号、测试 helper、大文件 | I33、I35；导出/类型/历史调用需再核。 |
| E-6 | 旧能力测试与重复 fixture | I33。 |
| E-7 | legacy 199K 行 | I34。 |
| E-8 | reference 体积 | I34。 |
| E-9 | launch stock filter | I22；W7 草案接线。 |

### 12.7 Claude F：fork/关停/恢复（13 条）

| 旧 ID | 内容简记 | 本文落点/修正 |
|---|---|---|
| F-01 | 早期超时、最终判失败 | I13。 |
| F-02 | evidence/资源报告影响 verdict | I13、I29、I32。 |
| F-03 | zero-grad skip/publish | I17、I34；熔断已配。 |
| F-04 | 多 engine router | I27。 |
| F-05 | 0008/0009 stock spans | I32–34；不能仅凭主入口未调就整删。 |
| F-06 | 0004–0006 事件/tape digest/梯度扫描 | I20、I23–24、I29、I32、I34；性能报告 P10 详列后端成本。 |
| F-07 | 302 commit/9 patch 迁移 | I34；历史快照，非本轮 rebase 失败。 |
| F-08 | Ray 异常同源/截断 | I13、I20；真实 Ray 待验。 |
| F-09 | signal/drain/late facts | I13、I33。 |
| F-10 | publish 后逐 engine 读回 | I32、I36；ack 与实际读回不等价于张量正确。 |
| F-11 | 冷恢复/显式 start | I22；已批版本命名与错配风险分开。 |
| F-12 | JIT/负 lag/no-progress | I15、I22、I27、I32；保消费时权威。 |
| F-13 | 重复事件/身份/dispose 小项 | I13、I20、I32、I34；sys.exc_info 不是 bug。 |

F 末尾 B1–B8 是上述条目的二次汇总，没有另算 8 个问题；逐 patch 表在性能报告 M07 逐组保留。

### 12.8 Claude G：能力缺口（8 条及横比表）

| 旧 ID | 内容简记 | 本文落点/修正 |
|---|---|---|
| G-1 | 在线 mismatch/ratio | I20；已有 logprob_compare。 |
| G-2 | drop 长度/归因 | I15、I20。 |
| G-3 | 瞬态重试 | I16。 |
| G-4 | session 局部性 | I27。 |
| G-5 | retract/in_place | I18、I27。 |
| G-6 | image prefetch | I28。 |
| G-7 | OPD | I36；未来独立实验，不是首训现成故障。 |
| G-8 | before/after eval | I21、I36。 |

横比表中的环境池/缓存、动态资源分配、训练 prefix-tree、checkpoint/恢复、数值对拍、评分隔离、多 harness/teacher 等分别归 I09、I18、I20–22、I27–30、I34–36；“数据工程只列不审”仍由 B 的新任务定义推进。本轮没有将横比表每个外部功能转成应实现需求，也没有确认“已超过多数前沿实验室”的比较性结论。
