# SWE 评分接线与第四组夜间实施：独立审查

日期：2026-09-16。主审：Codex A 线；独立切片：Production Tracer、Falsifier、Training Semantics。审查对象为 `bac7659ea70cc07a3a8c872a29e7659a894afc5a` 上的未提交实现，不是只审计划。

**结论：不能将本轮整体标为验收通过。** 来源接线、P-B、普通 file→dir 和多数真机对账成立；P-A 的候选失败归因仍有三项 P1。另有一处将正常完成的测试改判为 None 的范围问题，正式 actor 的资格入口及构建归因尚未完成。P-C/P-D 各有一个窄边界余项。以下将新缺陷、已披露缺口和需要用户决定的反作弊策略分别登记，不撤销已经批准的 A–D。

## 1. 已独立核实的成果与证据边界

| 检查 | 结果及能证明的范围 |
| --- | --- |
| 本机相关套件 | `uv run pytest tests/contracts tests/adapters tests/governance tests/grading tests/envpack -m 'not docker' -q`：**1392 passed / 1 skipped / 47 deselected**。`ruff check src tests scripts` 通过。不是完整 miles 双 lane 或全仓所有测试。见 [verification.json](verification.json)。 |
| Linux 新增容器往返 | 主审独立运行 `tests/grading/test_batch4_docker.py`：**3 passed / 0 skipped，24.36 秒**。普通 file→dir、按类型省略缓存、候选 uid 下的语法复证正例均通过。结束时无运行容器，metacopy 仍为 Y，未改内核或构建新镜像。见 [remote_batch4_docker.log](remote_batch4_docker.log)。 |
| 源码对应 | 本次涉及的 77 个变动/新增源码、脚本、测试文件，远端 `rh2_next` 与本地摘要全部一致；旧 e2 树仅 48 个一致。支持作者披露的“两份代码、两批证据”，不能用全部 78 行宣称 P-A/C/D 均已逐题验证。见 [source_snapshot.json](source_snapshot.json)。 |
| e2 与回归账本 | **78 + 25 = 103 行**；其中 92 行有评分报告，其余是严格应用失败。92 份评分日志均存在且 SHA-256 与账本一致，diagnostics 引用全部存在。未将 apply_failed 冒充 reward 0。见 [独立核对脚本](audit_e2_evidence.py)、[结果](ledger_verification.json)。 |
| B 组对账 | 24 个不同候选中 **15 个可比，15/15 与投影组 oracle 一致**；其余 7 个 apply_failed、2 个 modin infra。不是“24/24 通过”。7 个 fuzz 才能应用的候选继续不评分，符合既定决定。 |
| 新旧版本回归 | 7 题 gold/noop/候选共 21 行，与 e2 的 outcome、reward、F2P/P2P 计数和类别无变化；其中 1 条候选本来就 apply_failed。另 4 行人为坏语法及有/无资格对照，构成作者的 25 行回归。 |
| 新反例 | 主审逐一复跑三个子审的探针：真实本机 pytest/compile 输出，真实 manager/编排/gate/准入，容器与模型为已有维护测试替身；P-B/C/D 反证测试 **6 passed**。再复跑实际 miles integration buffer→训练数据转换，见 [root_probe_verification.json](root_probe_verification.json)、[组运输结果](production/group_transport_result.json)。错误行为被成功复现，不表示修复通过。 |

测试、日志核验与摘要校验各有用途，不以数量代替评分正确性。没有新跑全部 SWE 题、八卡训练、模型 API 或真实 OOM 注入。e1 沿用 B 线已有独立收口结果，没有重跑整套 e1。

## 2. 必须修正的 P-A 归因

### R1 / P1：无关文件的语法错误被用来证明本次测试失败由候选造成

**事实与例子：** 测试因候选目录之外的依赖缺失而在 collection 阶段失败；测试从未导入 `src/unused.py`，错误日志也没有它。候选碰巧把这个 unused 文件写成坏语法，manager 就给 `candidate_execution_failed / 0`。把 unused 文件修成合法语法而保持同一份失败日志，结果变成 None。

**原因：** `grading/manager.py:2977–2998` 编译所有候选 `.py`，只要任一 `error_paths` 非空就归因成功；`classify_execution_failure_shape` 只确认通用错误形状，没有将实际错误位置与复证位置连接。它证明了“存在一个坏文件”，没有证明“这个坏文件造成这次测试失败”。违反当批 A 的“明确由模型修复造成”和计划 §7/§8 的正向归因要求。

**证据与可达性：** [training 反例](training/probe_training_semantics.json) 的 `unrelated_syntax` 是真实 pytest 和内存 compile；[production 反例](production/production_probe_result.json) 的 `unrelated_error_transport` 进一步得到 clean gate、`KEEP_FULL`。当前带资格的 replay driver 为 `production_reachable`；正式 actor 需接入资格才走到新 0 分分支，属于 `conditional_future`，没有证据表明真实训练已经受污染。

**推荐：accepted，P-A producer 验收前修。** 只复证实际测试失败指向的候选源码，并要求正向异常证据对应，不能任意拼接 collection 错误和另一文件的 SyntaxError。定位不足保持未知。真实导入候选坏语法的 startup/collection 两类正例仍给 0，未导入坏文件不影响本次判分。不要新增通用异常分类服务、重跑所有 gold 或遇到正常候选错误就停整个 run。

实际频率未知；错误会污染负样本且现有 gate 会信任它。局部关联修正的成本低于恢复机制；完全删除 producer 会保留原负样本遗漏。窄修可能让目前不能定位的失败暂时留在未知集合，应在现有 decision sidecar 留原因，不扩大正常评分的拒绝范围。

### R2 / P1：编译复证器仍会导入候选的 `json.py`

**事实与例子：** 目标 `src/thing.py` 语法完全合法。仓库根新增一个同样语法合法的 `json.py`，它在导入时打印伪 `RH2_COMPILE_ERROR`。实际执行生产 renderer 后，候选模块被执行，脚本退出 0，并同时输出目标文件的 ERROR 和 OK；manager 接受伪错误，最终候选 0、`KEEP_FULL`。另一个对照中，同名模块抛异常，把真正的语法失败变成 None。

**原因：** `grading/manager.py:1015–1018` 从工作目录执行 `python -`，接着 `import json, sys`。当前目录参与模块查找；去掉 `py_compile` 没有消除同名模块遮蔽。这违反 §8 F3 已明确的“不执行仓库模块”要求，不需要先解决整个运行器可写风险才能修。

**证据与可达性：** [实际 shell 与运输反例](production/production_probe_result.json) 的 `compile_local_json_shadow`、`json_shadow_transport`；[独立异常对照](training/probe_training_semantics.json) 的 `compile_probe_imports_candidate_json`。driver 当前可达，formal 的条件与 R1 相同；没有提权或逃逸。

**推荐：accepted，P-A producer 验收前修。** 保留目标解释器、候选 uid 和现有超时，但消除复证辅助代码从仓库导入的机会，例如不依赖该 JSON 导入、隔离模块搜索及自动 site 加载；具体最小实现由作者选择。不要将候选源码交给 root 执行。验收真实 SyntaxError、合法源码、根 `json.py`/`py_compile.py`、缓存路径冲突；同名候选模块不得在复证中运行。这里修的是复证器自己的导入错误，不能因此宣称 D3 可写解释器的全部风险已经解决。

普通同名模块频率未知，主动构造稳定可复现；局部修改不应新增样本拒绝或常驻组件。只给输出再加一个字符串校验不能解决同进程候选模块已执行的根因。

### R3 / P1：必要终止事实未知时，仍按已排除资源问题给 0

**事实：** cgroup OOM 计数、Docker OOM 状态读取均失败而返回 None，甚至同时没有测试退出码，P-A 仍产候选 0，`missing=[]`。源码已有 CLI 非零/读取超时返回未知的分支，不依赖新功能。主审复跑 CPU 运输：注入资格后，未知资源的 0 分成员和正常 1 分成员进入实际 miles buffer、转换出 `raw_reward=[1,0]`，两者 loss mask 均非零；无资格对照整组丢弃。

**原因与位置：** `manager.py:2944–2957` 用 `(None or 0)`、布尔判断和缺失退出码的 false，只做“有没有观察到资源终止”的否决，没有区分“已经排除”和“事实未知”。§8 F2 要求待归因全局失败所需事实不足时仍无 reward；这项尚未落实。

**证据、分歧与范围：** [production_probe_result.json](production/production_probe_result.json) 的两组 unknown 案、[group_transport_result.json](production/group_transport_result.json)。Training Reviewer 提醒不能把任一可选内存指标缺失变成全局 gate；主审同意，因此仅保留**归因分支必要终止事实全部未知仍无条件放行**这一窄问题。没有实测真实 OOM 被误判，也不知道观测失败频率；不把 CPU I/O 故障替身描述成真机事故。driver `production_reachable`，formal 条件同 R1。

**推荐：accepted，随 R1/R2 修既有 F2。** 明确这个候选失败规则需要哪些终止事实，无法取得时具名记录未知并保持 None；正常已有可信测试结果不依赖这些附加观测，`memory.peak` 不成为必填。用正常已知、已证资源终止、必要事实未知三组验最终报告与运输。只需要现有来源和分支，不新增重试、后台 owner 或资源监控平台。因必要事实缺失而损失的样本比例未知；这是已选择的未知归因政策的代价，不应隐含变成新的广泛闸门。

## 3. 语义范围和正式接线不能遗漏

### R4 / 高优先级范围项：正常跑完测试，仅参考 ID 改变也被丢弃

真实 pytest 完成 **1 failed + 1 passed，退出 1**，没有 startup/collection 失败。测试的参数化 ID 来自普通源码，候选把 label 从 `before` 改成 `after`，两条参考 ID 因而都缺席。来源规则仍是 `tests_failed / 0`；当前 `execution_failure_trigger`（`manager.py:1108–1118`）仅凭全部参考缺席进入 P-A，随后因 `shape_undetermined` 覆盖成 `test_log_parse_failed / None`，有无资格都一样。该路径当前正式 actor 也可达。见 [真实反例](training/probe_training_semantics.json) 的 `all_reference_missing_completed_tests`。

**推荐按既有 A 的窄范围处理：** 三路归因用于真实全局执行失败；正常产出测试状态时继续按来源缺席规则计分，不能将所有 ID 缺席直接等同全局故障。实际 per-case 状态及参考缺席分别保留，避免伪造“这些参考测试都实际执行失败”。

授权上有文档歧义：§8 F2 明确“有可信实际测试结果时仍遵循来源规则”；作者 §9 又称用户确认了“参考全部缺席一律 None”。本次提供的用户原话没有单独批准正常完成场景，主审不能据作者事后登记替用户扩大范围，也不能证明其它任务里不存在更明确批准。**请作者先对齐具体授权与范围，不需要重新讨论整个 reward 算法。** 若确有明确的全缺席排除决定，保留为已批准取舍并登记本反例的样本选择影响，不能同时声称完全沿用 SWE 缺席计失败。实际发生比例尚未测定；修正限定范围比新增拒绝计数器或另一套评分平台更直接。

### R5 / 已披露未完成：正式 actor 没有环境资格来源

`PreparedTaskFace.grading_spec()`（`prepared_task_face.py:457–461`）没有把资格传给 helper；只有 replay driver 的 `--qualification-ledger` 能注入。维护运输测试人工构造资格，不能证明正式配置已经可用。当前 formal 全局失败都走未知/None，原本希望保留的负样本依然损失。[组运输对照](production/group_transport_result.json)已验证这个影响。

**推荐：deferred_with_owner_and_gate，B 实施者补齐，使用正式 P-A 结果前完成。** 复用筛查得到的每题、实际镜像、配方及报告记录，经既有 host-private/prepared 入口传入；无资格继续如实未知，不能用一个布尔默认放行。存储位置是实施选择，不是重开 A 或要求用户批准新 reward。先修 R1–R3，再启用正式资格。

同处补一项 P2：派生镜像的资格键目前是 `local_build:<tag>`（`manager.py:972`），driver 已拿到 `.Id` 却未用于资格（`replay_grade.py:443–455`）。同 tag 重建可能沿用旧资格。建议复用已经取得的实际 image ID，无需新哈希系统。原 RepoDigest 路径不受影响；本轮仅源码核对，没有改变 tag 或重建镜像实测。

**构建归因 F4 也未完成。** 安装段末 RC 与资格基线一致，包括 2，只能说明“最后一条命令没偏离”，不能证明所有安装/重编译成功。合法 gold/noop 在现有镜像能评分是有用证据，但不能保证改了编译产物的候选实际生效。按原分片补关键构建命令的真实结果、产物生效与候选归因；不用现在重做整条环境流水线。将当前 A 写成“startup/collection 语法失败首片”，不能核销全部已批模型编译/执行失败问题。候选确定性测试超时 producer 仍是既有待办，也没有因本轮自动实现。

## 4. P-C/P-D 两个窄余项

### R6 / P2：被省略的既有缓存目录改成文件后，落入 infra

基线已有 `.pytest_cache/old`，v2 将整个目录省略。候选把目录替换为同名普通文件，exporter 只看见 `add .pytest_cache`，分类与投影都通过；fresh grader 却仍有旧目录，真实 apply shell 报 `add_target_exists`，manager 返回 infra/None。无旧目录的普通文件 add 对照正常。见 [Falsifier F2](falsifier/README.md)。当前 formal/driver 均 `production_reachable`；真实 e2 频率未知。

**推荐：accepted，组合切片收口前窄修。** 保留类型变化所需事实，按既有 unsupported/unsafe 通道处理尚不支持的目录→文件/软链，或明确已省略缓存在重放前的一致规范化。无需新增通用反向转换支持；也不能把任意 add 冲突都降成 unsafe，掩盖内部错误。验原本不存在/原本普通文件、普通 file→dir 和缓存反向类型变化。两类既定不支持情况都丢组，但错误分类会影响诊断及重试决策，不能记成 Docker 损耗。

### R7 / P2：拒绝路径仍依赖解析错误文案，引号路径丢证据

`patch_exporter.py:279` 只解析单引号形式的 `repr(path)`；合法路径 `config'quote` 的 repr 使用双引号，清理后 receipt 的路径成为 null，只剩 `unsupported_delta_shape:?:prefix_conflict`。普通名字也未完整保留祖先/子路径与双方操作。真实编排→receipt→清理→准入的 CPU 反例仍正确 DROP_GROUP，未发现 reward 错判。见 [Falsifier F1](falsifier/README.md)。

**推荐：accepted，补完 §8.3 已登记证据余项。** 复用结构化冲突信息和既有 audit/receipt，不从展示字符串反解路径；不新增第二套事件系统。普通名、单双引号等合法路径在清理后可定位；内部排序/身份错误继续 fatal。该项不单独阻止普通题的小批校准。

另一个非阻塞观测差异：driver 记录 baseline/post 缓存计数，formal 导出没有接 `omitted_sink`，grader sidecar 的计数实际只反映 fresh baseline。可接通既有 sink 或标清字段来源，不以此新增训练拒绝。

## 5. stdout / hook 伪造：已确认风险，但建议方案还不能叫根治

作者及 B 线已给真实 RH2 证据：conftest hook，或只改 setup.py、在安装时写出 hook，都能令未修复候选获得 1 分；源码 stdout 也能伪造 parser 状态。主审核对了 B 的 [M2 §7](../../env_overnight_20260916/M2/M2_report.md) 与本地账本，不将其重复计算为本轮新发现，也没有再次跑机器 2。

**需要修正 §9.6 的建议强度：** 安装后 root 恢复已知控制文件可以阻断已展示的安装期写入路径，但不是所有候选执行的信任隔离。把输出改成 JUnit XML 也不自动可信。主审实际运行官方 pytest JUnit plugin：同一个 `assert 1 == 2`，无 hook 时 exit=1/XML failures=1；加同进程 report hook 后 exit=0/XML failures=0，断言源码完全没变。见 [探针](probe_junit_channel.py)、[结果](junit_channel_result.json)。本探针没有模拟 root 文件权限，证明的是结果在写文件之前就能被改，而不是受保护文件可被任意覆写。

root 拥有 plugin 文件不能保证加载它的候选进程内数据可信；候选不可写输出目录时，普通候选进程中的 plugin 也不能直接写它。若引入可信收集进程或文件描述符，还需说清接收的是谁生成的事实，不能仅凭“来自 XML”或“root 注入”接受 passed。

**这是仍需用户决定的范围，不在本审查中替用户恢复 I08、判作弊 0 分或统一 unsafe。** 推荐先定义项目一首版防哪些可达篡改方式，复用这几条真实失败修复反例比较最小控制面方案，再决定逐题规则、动态保护与仍接受的同进程风险。候选对普通源码、构建脚本和必要测试辅助代码的合法修改必须有正对照；不因一个名字相似就重新全局剔除。保留受控诊断/环境分析，正式训练前明确这个已实测 reward 污染面的处置或接受范围，无需先造通用抗作弊平台。

## 6. 旧余项、e2 解释与推进顺序

**接线页 §14.2 的三个旧余项仍在代码中，不能被“夜间全部完成”覆盖。** 本轮源码核对，沿用原证据与分期，不重复报新回归：

| 旧余项 | 当前处理要求 |
| --- | --- |
| manager `_records` 留完整 `eval_log_partial` | 正常持久化后释放全文临时缓存，保留引用；B 在长批/正式训练前完成。当前小批进程退出可释放，不推翻 e2 分数。 |
| 派生 `.Id` inspect 在 row 建立前，取消缺账本 | 原定 e2 D4 前完成但仍遗漏；顺手接现有取消落账，不新增重试。夜间该分支没有取消，因此不能由成功 e2 核销。 |
| 后观测取消把完整日志硬写为 `partial=True` | 读已有候选事实；汇总取消数据前修正，不需重跑题库。 |

e2 的几个结论需保持限定：A 组是 **7/9 题达标**；pandas 参考 ID 和 modin 仍未通过环境资格。耗时统计 §5 是晚到 shm/OOM 行之前的 77 行子集，其中 67 行有评分；最终 78 行包含峰值 4096 MiB 的反例，不能把“4 GiB 未触顶”推广到整个批次。安装 900 秒 + 测试 1800 秒只是建议，当前仍共用一次 test exec 预算。`MODIN_CPUS=2` 的 root 探针支持候选修法，但仍应在正式 UID/profile、实际 RH2 gold/noop/候选下复核；不据它宣布 modin 已恢复。metacopy=N 构建、Y 评分的证据不能外推为所有机器都适用。

**推荐实施顺序：**

1. 当前 B 实施者集中修改 R1–R3，避免 A/B 同时改 manager；同时按 §8 的原范围收窄/对齐 R4。它们是已有决定的落实，不需要再问三次“能否给 0”。
2. 接正式资格入口，补实际派生镜像身份；R6/R7 和三个旧余项属于小范围修正，可同批分提交处理。F4 明列后续切片与正式使用前的条件，不藏在“全部完成”里。
3. 用本轮正反例、正式 prepared→评分→组消费运输，以及必要的少量真实 SWE 例复核；已对上的 78 行不必机械全跑。未知资源探针是分流验证，不要求立刻做高成本真实 OOM 矩阵。
4. 反作弊策略单独形成具体可比较的方案，由用户决定；环境盘点、离线依赖修复与受控小批诊断可以继续。规模筛查不得把未确定/丢组静默当成任务通过，正式训练也不能以当前“全部完成”标签放行。

**停止条件：** R1–R3 的原反例闭合且正向样本仍正常；R4 明确范围；正式使用 P-A 时资格真实注入；P-C/P-D 与取消/内存余项按上述分期收口。随后只复核对应接缝，不再扩成全仓或全部环境审计。当前没有提出新的正式实验数值、模型选择或奖励公式。

本轮仅新增审查文档与 CPU/真机验证证据、追加导航/账本。未修改生产源码、维护测试、配置、旧运行 evidence 或提交；未替用户发送其它任务消息或处置远端机器。
