# 09-19 链路修复聚焦复核 / Codex A 线

**结论：大部分修复可以核销，但本轮仍不能整体验收。P-A 的原 R1、R4 各剩一个真实边界；缓存规范化新增一项 P2。** 三项都能在既有决定内窄修，无需用户重新决定 reward、反作弊或资格政策。环境/数据修复和新 A 任务的后续决策可以继续并行。

基线为 `bac7659ea70cc07a3a8c872a29e7659a894afc5a` 加当前未提交实现。相较 09-16 审查快照，有 14 个源/测试文件变化；本次核对的 77 个文件与 Claude 真机验证树一致，收尾时本地源码摘要未变。见 [source_snapshot.json](source_snapshot.json)。没有修改生产代码、维护测试、配置、旧审查工件或 Git 提交。

## 1. 已完成的独立验证

| 验证 | 结果与实际覆盖 |
| --- | --- |
| 主审本机相关套件 | **1402 passed、1 skipped、48 deselected**，ruff 通过。范围为 contracts / adapters / governance / grading / envpack 的非 Docker 测试，不是全仓或完整 miles 双 lane。唯一 skip 是未配置本机全量 parser corpus；已入库语料测试已执行，48 项 Docker 按 marker 排除。见 [verification.json](verification.json)、[pytest_cpu.log](pytest_cpu.log)。 |
| 主审真实 Docker | 本机已有 fixture 镜像的 batch4 往返 **4 passed**：普通文件变目录、按类型省略缓存、带/不带资格的语法失败、旧缓存目录变普通文件。见 [docker_batch4_local.log](docker_batch4_local.log)。远端无该 fixture 镜像，前置检查即停止，未为此安装/构建镜像。 |
| 主审旧 Python 兼容性 | 已有 SWE 镜像内 **Python 3.8.19、3.9.19、3.12.4**，以候选 uid 54321 执行实际 `render_v2_compile_probe_script`，包括 conda 激活。合法源码、坏语法、缺失文件均正确；仓库同名 json/py_compile/sitecustomize/usercustomize 与候选正文均未执行。容器无网络、只读根、使用临时测试目录，退出后无本次容器残留。见 [探针](probe_python_compat.py)、[python_compat.json](python_compat.json)。 |
| Claude 真机产物回读 | **8 条 ledger、8 份日志与 sidecar** 对账，日志摘要全部吻合：dvc-2141 noop×2 为 0、gold×2 为 1，均 P2P 失败 0；P-A 两题 gold 为 1，dvc-5822 坏语法归 candidate_execution_failed，moto-6913 坏补丁走普通 tests_failed。见 [evidence_audit.json](evidence_audit.json)。这是对已有产物的独立核验，未重跑这些 SWE 题。 |
| 三条独立子审 | [Production Tracer](production/README.md)、[Training Semantics](training/README.md)、[Falsifier](falsifier/README.md)。主审逐项回读并独立复跑关键探针，验证真实 pytest/compile、真实树/Bash、manager/编排/准入及实际 miles buffer→训练转换。CPU 探针的容器/模型 I/O 使用既有替身；不冒称整个 actor 或真实训练已运行。 |

组运输重放使用新的 `root_replay/` 输出目录：首次直接重跑遇到 prepared 工件禁止覆盖的预期检查，没有删除或覆盖旧 prepared 产物。远端只读回查和三个短编译探针未操作 B Codex 的代码、环境实验或容器；无 GPU/API、全题库重跑、内核参数或镜像标签修改。

## 2. 两项仍需修正的 P-A 边界

### CR1 / P1：普通路径提及仍会被当作语法失败的因果证据（原 R1 未完全闭合）

**例子。** collection 时执行 `load_metadata("src/unused.py")`。函数先导入一个外部依赖，该依赖缺失，因此退出；它从未读取或导入 `src/unused.py`。pytest 的真实回溯却会显示这行调用代码。候选恰好把 unused 文件写坏时，现实现将其复证出的 SyntaxError 拼到缺依赖异常上，给 `candidate_execution_failed / 0`。只把 unused 文件换成合法源码、保持同一失败日志，则结果为 None。

**根因与位置。** `rh2/src/repoharness2/grading/manager.py:1125–1139` 的 `referenced_candidate_paths` 对整个测试段搜索有左右边界的路径；`3082–3104` 再接编译结果。左右边界避免了路径子串误认，却没有区分“异常中的实际语法错误位置”与参数、源码引用或普通输出。缺依赖本身仍未由候选语法错误解释，违反已批“证据不足不归因”的规则。

**实际影响。** [真实日志与 manager 结果](training/probe_chainfix_training.json) 的 `r1_path_in_argument_not_exception_location`；主审复跑的 [训练运输](root_replay/training/group_transport_result.json) 中，坏 unused 进入 `raw_reward=[1,0]`，两个成员 loss mask 均非零；同一日志配合法 unused 则整组未进 buffer。当前带资格 replay 为 `production_reachable`，正式 actor 在流水线接资格后可达；没有声称现时真实训练已被污染。实际题库发生率未知。

**建议及验收。** `accepted`，在核销 P-A producer 前窄修：只让真实异常块中的语法错误位置与候选路径、复证结果建立正向关联；普通路径提及不足以归因。定位不足继续沿现有 None 分支。验收：本反例两种 unused 内容均不获候选归因；真实 collection/conftest 导入候选坏语法的两个正例及 dvc-5822 形态继续给 0。不新增服务、重试、状态机或防作弊政策；未覆盖的格式暂留未知是明确的首片覆盖边界。

### CR2 / P1：单测试内部 traceback 被当成整个测试启动失败（原 R4 未完全闭合）

**例子。** 测试文件字节保持不变，仅候选源码的 `label` 从 `before` 改为 `after`。参数 ID 随之变化；一个测试在 after 分支启动缺模块子进程，另一个测试通过。pytest 正常完成 **1 failed + 1 passed，rc=1**；子进程 traceback 位于 `Captured stderr call`。原参考 ID 全缺席，按来源规则应仍是 tests_failed / 0。

现实现却将其中的 `ModuleNotFoundError:` 命中为 `python_traceback_startup_error`，把结果改成 None。无需环境资格、伪造 stdout 或测试文件改动即可复现。见 [固定测试证据](root_replay/training/supplemental_r4_fixed_tests.json)。

**根因与位置。** `manager.py:1081–1083,1107–1121` 在整个测试段搜索通用 Python 异常行，未区分顶层运行器异常与单测试捕获输出；`3033–3038` 只有完全未匹配形状时才保留来源规则。有逐测试结果并完成执行的失败被误划入全局故障，违反原 R4 已澄清的授权范围。

**实际影响。** replay 和正式 actor 当前均为 `production_reachable`。主审 [组运输](root_replay/training/group_transport_result.json) 的 `r4_simple` 得到 `[1,0]` 并进训练 buffer，`r4_nested` 整组丢弃；两组均未注入资格。同一局部 traceback 日志若尚有一个参考 ID 在场则保留 0，说明差异由新分流造成。尚无真实题库损耗频率结论。

**建议及验收。** `accepted`，与 CR1 同一窄修完成：正常完成测试时，单测试捕获的 Python traceback 不能单独成为全局启动失败证据；保留来源评分。不要简单改成“解析条数 > 0 就正常”，collection 的文件级 ERROR 也会被 parser 计数。验固定测试反例仍为 0，真正 conftest 启动/collection 中断继续走既有三路，无须新建评分通道。

## 3. 缓存规范化的一项新 P2

### CR3 / P2：清缓存越过了 manifest 的排除命名空间

原 R6 的缓存目录→普通文件/软链已经能重放，8 组真实树对照与主审 Docker 正例均通过。但 `manager.py:2548–2552` 新增 `find . … -name __pycache__ … -exec rm -rf` 没有剪掉 `policy.excluded_namespaces`。

当前政策排除 `.git/` 和 `.harness/`；census 会单独记录这些区域，没有把它们当普通可省略缓存。新清理在 baseline 核验之后进入这些区域：真实 Git 反例中，合法分支 `__pycache__/probe` 的 `.git/refs/heads/__pycache__/probe` 被删，`git rev-parse --verify HEAD` 从成功变为 rc128；`.harness/__pycache__` 内文件也被删。即便候选 noop、scoreable entries 不变，排除区摘要仍改变。见 [Falsifier 报告](falsifier/README.md)、主审 [重放结果](root_replay/falsifier/probe_results.json)。

**边界。** 当前分支 HEAD 失效例对应保留该分支的 `image_embedded` 树；clone fixture 的 `checkout --detach` 不应套用该后果。只要排除区有同名目录，删除代码即可触发，但没有声称已选 SWE 镜像存在这种分支或已发生错分。探针 Git/文件操作真实执行，评分输出由替身提供，不以其 resolved 证明真实测试仍通过。

**建议及验收。** 作为本次新增实现的窄 P2 一并修：复用 manifest 现有 `excluded_namespaces`，先 prune，再只删除 scoreable 区内获批的两类目录。无需新 guard 或额外全树哈希。验排除区/HEAD 不变、普通缓存仍删除、同名普通文件/软链仍保留、原缓存反向类型变换和 v1 行为不回归。不单独阻止 B 继续环境校准。

## 4. 可以核销和仍需保留的项目

| 项 | 裁定 |
| --- | --- |
| R2 复证导入候选同名模块 | **闭合。** 本机与三个真实解释器正反例通过；不外推为安装可改运行器的已知边界全部消失。 |
| R3 必要终止事实未知仍给 0 | **闭合。** 任一必要事实未知均不再归候选。`pids.events max` 表示配额命中，可能干扰执行；文字宜称资源干扰证据，不宣称计数本身证明当前测试进程被杀。其保守排除规则不另报为缺陷。 |
| grader `--init` | 参数由正式 profile 到 manager 的运输通过；Claude dvc-2141 的 4 条真实评分产物核对一致，支持原僵尸问题的修复。不能用它宣布 Modin 并发问题也解决。 |
| R6 原缓存目录反向类型例 | **原例闭合**，另有 CR3 的排除范围修正。普通文件、软链按类型保留，没有扩成全部 `.pyc` 或 gitignore 清理。 |
| R7 结构化冲突证据 | **按原诊断目的闭合。** 普通、单双引号、反斜杠路径在清理后可从已 fsync 的 execution audit 定位双方路径/操作，receipt 保留拒绝路径与类型。完整详情在 audit，不是 receipt 含全部字段；请纠正作者这句描述，无需扩公共 receipt。 |
| 日志全文占用 | **闭合。** 完成和取消后清空 `eval_log_partial`，日志引用、摘要及事实保留。两条约 1 MiB CPU 日志对照通过。 |
| 派生镜像 inspect 取消缺行；后观测取消 partial 错误 | **闭合。** 各只落一条 ledger，后者完整日志 `partial=false`、摘要一致，取消原样传播且清理完成。 |
| 派生资格仅按 tag 绑定 | 常规重建原例**闭合**：下一次 inspect 的实际 ID 改变，旧资格失效。inspect 后并发重指 tag 的窄竞态仍可能存在；当前没有这种工作流证据，仅记非阻塞残余。 |
| 正式环境资格来源 R5 | **部分闭合、已披露待流水线。** 构造器→spec→queue/manager 已通；`PreparedTaskFace.load` 和 bringup 尚无资格记录来源。不能叫整个正式 actor 已接好；真实记录与加载点按既定流水线安排，无新 T0。 |
| 安装 ERR trap / F4 | 7 组真实 Bash 控制语义对照未见退出码、后续命令或产物变化；但 `&&`/`||` 等存在观测盲区，pipeline 文案也不证明哪个进程失败。它是诊断，**构建命令生效和候选归因 F4 仍未完成**。不要求本轮重造通用 shell 解释器。 |
| formal 缓存计数 | 仍有**非阻塞观测缺口**：两次 sink 填入 `RolloutAudit.omitted_cache_counts`，但 `bringup.write_execution_audit_record` 没有序列化该字段。原“已接观测”只能算内存部分；补既有 audit 字段即可，无新 gate。 |

## 5. 本轮不扩大的范围与交接

1. 用户已将反作弊力度留给流水线和真实基座探针。已知 stdout/hook 风险保持登记，不因本次复核自动恢复 I08、追加惩罚或阻止所有后续实验。
2. 环境资格记录是否需要不是待决策问题；记录和正式加载由 B 的流水线产生/接入。当前没有资格时保留未知，不伪造默认资格。
3. Modin 优先在 B 的既有配方实验中验证让 Ray 并发与沙箱 CPU 一致；不凭它一个题就替用户提高全局 PID 配额。切换 `MODIN_ENGINE` 与限制同一引擎并发也不是同等改动。本文不代作配方决定。
4. 来源参考键、Conan 丢信息的 parser、mypy base/gold 对不上均沿 B 数据/环境分工处理，不在此修改 parser/题单。新 A 的第五组及 I18 同样不在范围。

**交 Claude 的最小后续：** CR1、CR2 修正原归因边界；CR3 复用既有排除策略；顺手补 audit 缓存计数并校正文档状态。保留本轮已经通过的 R2/R3、取消收尾、两种 cache 类型变化正例。三项关闭后只复验这些接缝和必要回归，不重启全仓/全部 SWE 题审查。报告区分“此轮修复闭合”与“F4、正式资格供给等后续能力已完成”。

## 6. 审查覆盖与复跑说明

- **A/B/F/G**：真实 pytest 正反例→manager→准入→miles 训练转换，定位 CR1/CR2 的负反馈与丢组变化；没有 GPU 参数更新实验。
- **D/H**：原 actor load/resolver/submit AST 切片、真实 prepared/registry/queue 检查资格归属；明确手工构造器注入与真实配置加载不同。
- **C/I**：本轮无新闸门、无策略决定；未知继续原分支，已修项停止扩审，环境/反作弊/F4 后续安排不变。
- **E/N**：主审复跑维护测试、实际脚本与 Python 3.8/3.9/3.12；结合正例检查修复不是单纯改 oracle。未用新的 skip/xfail 掩盖问题。
- **J/K/L/M**：缓存遍历范围、Bash 控制语义、全文释放、取消持久化、冲突 audit 与缺失缓存计数字段；修法复用原 owner/政策，不引入新平台。

CPU 反例脚本和 JSON 位于各子目录，主审组运输及关键独立重放位于 `root_replay/`。prepared 产物一次性写入：再次运行组运输或 production 探针时，将脚本与输入 JSON 复制到新的审查输出目录，不删除旧证据。各脚本从自身文件路径向上定位仓库；固定测试探针需要同目录的 `probe_chainfix_training.py`、`old_probe_copy.py`，组运输需要其输入 `probe_chainfix_training.json`。主审重放的退出状态和预检查失败均记录在 [verification.json](verification.json)。
