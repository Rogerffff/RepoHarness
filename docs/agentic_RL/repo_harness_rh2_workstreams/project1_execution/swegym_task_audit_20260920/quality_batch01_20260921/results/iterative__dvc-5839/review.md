# iterative__dvc-5839 独立 reviewer 复核

2026-09-21，第二阶段。独立初判 `reviewer_initial.md` 已在本包三题任何其他角色结论开放前封存，SHA-256=`d2115e440248378aa79eaa3b529ea77f1a5ca39593a64315dfffbe06f5242357`；本轮不修改初判。本报告只增加开放后的比较和处置建议。没有运行 DVC、pytest、安装、Docker、SSH、模型或新 CPU 对照。

沿用初判路径：`R=.`；`P=R/runs/swegym_quality_batch01_20260921_v2/public/iterative__dvc-5839`；`Q=同材料根/private/iterative__dvc-5839`；`E=R/runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-5839`；源码行号相对 `P/base`。`O` 是本报告所在目录。`H=R/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_2/records/iterative__dvc-5839.json`。

## 结论和使用边界

同意主审最终 `needs_review / static_review`，保留为范围明确的 `development_diagnostic` 候选。公开帮助与旧数值测试已经说明 precision 是小数点后的位数；gold 补传参数，静态符合题面字典型原例。历史 repaired grader 中 noop 1 失败/21 通过、gold 22 通过，证明指定条件下选定参考能够区分这一个参数遗漏。没有发现应据以拒绝本题的已执行反例，也没有理由把旧报告的语义质疑继续作为 gold 不正确的证据。

这不等于完整端到端精度能力已被评分验证。F2P 只在空数据 Mock 下检查传入 8；命令层固定传 8 的错误实现预计能满足全部参考，真实 actor 与公开 CLI 原例尚未验证。该疑点适合作为窄校准，不应仅因一个参数样本就强制阻断参数传递诊断。若要声称覆盖所有 metrics 类型，还必须处理已有 scalar float 跳过舍入的范围问题。

## 本轮实际阅读与证据分层

第二阶段完整阅读 O/public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json；读取本题 history/refs.json 和其唯一 H 原件。没有沿 H 跟随跨题 prescan、4124、3677、全批汇总或仓库未来对象；没有读 acceptance 聚合。第一阶段逐条原件阅读、全部 1 F2P/21 P2P、helper/fixture、调用者、gold、日志及身份校验范围详见封存初判，本轮没有把主审的阅读清单冒充自己的原始阅读。

独立检查与主审增量分开：初判自行核了 base 元数据一致、补丁字符串一致、gold 和指定日志 SHA-256，并读了两个 ledger 和 recipe.json；主审另外核了三份 S2 原行 142 及两角色十个 recipe 文件。后两项本轮只读其报告，没有独立重做。没有重新构建 Git tree。H 的旧 stage1 执行汇总只作为旧报告主张；本轮用于运行结论的原始证据仍是 E 中已经独立读过的 09-19 日志和 ledger。

| 证据层 | 此次可以确认的内容 | 不能推出的内容 |
| --- | --- | --- |
| 公开/私有静态原件 | base `daf07451f8e8f3e76a791c696b0ea175e8ed3ac1`；run 漏传参数、helper 具有舍入实现；test/gold 内容相符 | 当前 actor 已导入该源码；实际模型收到的消息与 hints 注入方式 |
| 冻结参考 | 1 F2P、21 P2P；新增 Mock 调用约束和旧 helper 数值断言 | 科学计数法 YAML 经过真实 CLI 的结果；任意 n 均有效 |
| 历史实际运行 | E/gold/...0842b89c.eval.log:630–685 的 22 项通过；E/noop/...5507cf1b.eval.log:613–623,840–904 的唯一调用断言失败 | 当前重新执行、actor 权限和配方消费、全仓回归均通过 |
| 新 CPU / actor | 全部为下文建议，未执行 | 不能写成已证漏判、已证误拒或 ready_for_probe |

两份历史运行属于 derived image `sha256:9830786d461222987397d06799bb88a5e895c9af93cb94cfaec8bec30f5d7f3b`、dvc-install-v1、本地离线 wheelhouse、rh2grader/54322、deny_all、2 CPU/4 GiB。candidate 的 apply_user=agent/54321 不是 actor 执行证明。

## 与公开审查、主审和历史的逐项比较

| 问题 | 独立初判与公开/主审 | 对旧 H 的裁定及依据 |
| --- | --- | --- |
| precision 的语义与原例 | 三者一致：metrics.py:250–258 的帮助和旧 test_metrics_show_precision:303–333 已约定普通小数位；gold 在 run:92–98 补值 | 推翻 H check 23 的关键推论。`5.0172572763074186e-09` 舍入 8 位应约为 `1e-08`，并非仍为 0.0；题面 `0.001e-09` 与另一个示例不等值，不作为数值 oracle。这是静态算术/源码判断，尚无真实 CLI 原例运行 |
| 能否公开定位根因 | 独立及公开审查均能从 parser→run→helper 定位；缺一个实参无需额外私有资料 | H 把“只能读代码发现”列为材料无法确定项不成立。公开源码本来就是开发材料；不应把修复位置写入题面来补足所谓缺失 |
| 全部新增断言 | test.patch 新增 `--precision 8`、Mock `_show_metrics`、run=0、原 repo 参数保持、helper 恰一次 precision=8。mocker spec 按签名归一化 | 确认 H 所说的内部结构耦合，拒绝将其扩大为只接受 keyword；gold 全位置参数历史已通过。将舍入移到底层或事后处理 table 未证明能保留精度、JSON 与默认兼容，不能直接称合法误拒证据 |
| 数值测试覆盖 | 独立和主审均读到 show precision 默认/4/7 的 P2P，不只是 diff precision | 推翻 H check 25 的“helper 忽略 precision 仍能满分”；它会触碰已有 show P2P。确认真实 CLI 数值连通仍未覆盖，尤其 F2P 完全 Mock 空数据 |
| 可区分错误实现 | 独立与主审分别在历史前提出“只在命令层固定 8”，helper 不改，预计仍过参考却破坏默认/其他 n | 这不是 H 的“helper 忽略 precision”。是更精确的静态漏测候选，未执行，不把预计 reward 当事实 |
| gold 范围与标量 | 同意主审 gold 无已确认新增缺陷；初判单列 scalar float 分支 helper:54–57 直接 str(metric)，repo/metrics/show.py:48–50 和公开功能测试承认标量合法 | 它是 base 已有边界，题面为字典。不能因此判原例没修，也不应把当前评分概括成对一切 metric 数值的精度验证 |
| 回归覆盖强度 | 21 P2P 确实覆盖 helper 表格/diff 多种输入；show_json_diff 实际是 diff 表格测试 | H 的“json/markdown/precision 全保护”须按入口缩限：show JSON 原值、Markdown+自定义 n 均无真实 CLI 断言。gold 分支结构支持兼容推断，不能代替执行 |
| 环境与 parser | 当前原始日志安装 rc=0、22 项全出现，参考 missing/skipped 为空；recipe 修复范围仅 grader | H 的“仍需网络”“无依赖问题”“Could 伪键”均不能直接套用这次条件。没有读旧 parser 原始运行，故不推翻其旧条件发生性；当前独立证据未见同现象 |
| 题族/泄漏 | 同文件不足以证明同缺陷；本包具体暴露关系见下文 | H 将 4124 与本题按同测试文件直接归同族，证据不足；未读 4124 原件，不替其建立精确祖先关系。旧 hints 为空或题面无代码也不能证明当前真实镜像无答案暴露 |

没有实质分歧需要主审改判。初判比主审最终卡更突出 scalar float 范围，主审详细分析也已说明；这是用途边界的强调差异。初判建议默认/3/8，主审默认/4/8，二者都可区分硬编码 8，无需为这点增加第二组实验；本轮采用主审的默认/4/8 统一输入。

本轮补记初判未充分展开的限制：根 conftest 会导入 remotes，最窄 Mock 测试也需要收集依赖，不能简化为“纯内存即无需依赖准备”。public_read 与主审列出的 moto/WsgiDAV 等顶层导入是合理环境提醒；独立初判只读了根 conftest 与部分 fixture，没有逐个复核这些第三方实现。此处不把该提醒写成实际 actor 缺包。

## 八方面收口

1. **公开要求**：支持按既有小数位约定修复字典指标的表格精度；未知实际 CC 消息和注入的 hints。无需要求新科学记法选项。
2. **材料/初态**：精确 base、test/gold 与指定日志身份独立相符；缺陷调用链和历史 noop 失败相符。未复现 YAML，未独立重建整个 tree 或上游 PR。
3. **测试命中**：1 F2P 和 21 P2P 及所有变更断言均已逐条核；F2P 只查空数据时传 8，旧数值 P2P 直接调 helper。默认和多个 n 的 CLI 连通是具体缺口。
4. **合理实现接受性**：positional/keyword 传参均接受；helper 改名/重组存在静态耦合风险，但没有经过行为合格审查并实际被拒的替代补丁。
5. **gold/回归**：一行传参保留 helper 默认、JSON 旁路、diff 和 repro/experiments 调用者；scalar float 是旧缺口。历史参考全过不证明所有兼容路径。
6. **开发条件**：本地 YAML 和源码即可构造原例，无业务联网或云服务需求；真实 agent 的 Python、依赖、导入、可写空间和 repaired recipe 消费未知。旧 helper 测试修复前也会绿。
7. **交付/评分边界**：唯一官方恢复文件为 tests/unit/command/test_metrics.py；gold 源文件被投影、没有新增排除依据。未审真实镜像 Git/缓存/mount 或控制面隔离；public 无 .git 不是镜像无泄漏证明。
8. **关系/用途**：只用于已暴露的开发诊断审核，不作为未暴露 solver 成功或学习价值证据。第三题独立初判封存前已核到本题 base 的 dvc/utils/fs.py:123–140 与 3620 gold 的 `_unlink` 结构一致；这给顺序暴露提供具体渠道，但三个问题并非同一 bug。未据此读取额外任务或改写前两份初判。

## 最小后续动作（未执行）

优先通过真实统一 actor 入口确认 `id`、解释器、`dvc.__file__` 指向当前 /testbed、依赖可导入，以及本地 YAML 可写；保留实际消息和配方身份。这一步解决开发条件，不向未暴露 solver 提供私有断言或 gold。

质量校准只需一次固定输入的 CPU 比较：在已确认身份和同一 recipe 下，对 base / gold / 命令层固定 precision=8 的候选运行官方 22 项；再以 `mae: 1.4832495253358502e-05`、`mse: 5.0172572763074186e-09`、`ordinary: 1.098765366365355` 的同一 YAML 比较默认/4/8 的普通表格与 Markdown，并核 JSON 保留原值。若候选参考全过而默认/4 行为错误，才记录真实漏判；gold 应遵守每个 n。不要仅断言每两个输出必须不同，要按输入数值和现有舍入契约判断。可在同轮把 scalar YAML 作为范围观察，但不追加成原题必修条件。

不建议先做大规模 formatter 重构来制造误拒，也不要求全仓远端测试或模型求解。若上述 actor 与公开 CLI 验证成立，可用于参数传递的窄开发诊断；扩大成端到端精度评估前，须按结果补可见数值连通覆盖。当前没有新增 revision、文件排除或已执行 CPU 结论。
