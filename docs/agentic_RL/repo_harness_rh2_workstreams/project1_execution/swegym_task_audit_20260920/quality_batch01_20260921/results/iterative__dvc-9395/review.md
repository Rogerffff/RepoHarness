# iterative__dvc-9395 独立 reviewer 复核

2026-09-21，统一开放后的第二阶段。封存初判 `reviewer_initial.md` 的 SHA-256 为 `45fb4fc0c670dbed66d51fffd0ca69ddd8ea9ec64c22acd7eb176fa6af04e6ef`，未修改。此次只读取原件和核文件元数据，没有执行 DVC、pytest、安装、容器、SSH、模型或新 CPU 实验。

路径：`R=${REPO_ROOT}`；`P=R/runs/swegym_quality_batch01_20260921_v2/public/iterative__dvc-9395`；`Q=同材料根/private/iterative__dvc-9395`；`E=R/runs/env_recipe_repair_20260919/dvc_tail_v1/tasks/iterative__dvc-9395`；源码行号相对 `P/base`。`GL=E/gold/eval_logs/evallog_replay-er19-dvc_tail_v1-_66688534.eval.log`；`NL=E/noop/eval_logs/evallog_replay-er19-dvc_tail_v1-_d7bf896d.eval.log`。`O` 为本报告目录。

## 结论

同意主审 `needs_review / static_review`，限 `development_diagnostic`。核心需求和非测试源码修复路径清楚；09-19 修复配方下 gold 的真实 30 项通过，数据源与运行缓存两条 F2P 都失败转通过。不过 gold 新增 pull 路径没有 dry 保护，并在本地完整、无需恢复时也强制读取 remote；这两个控制流疑点比构造新错误补丁更值得先做 CPU 对照。不能用参考全绿抹去这些兼容性问题，也不能把静态预测写成已执行回归。

旧报告的关键归因不成立：旧候选的 `test_restore_pull` 实際失败发生在 reproduce 内的 `OutputDoesNotExistError: output 'bar' does not exist`，还没执行到 `mock_checkout.call_count == 3`。旧 PARTIAL 是真实运行结果，但不是“只因调用次数不同而拒绝合理解”的实证。精确三次 checkout 的结构耦合仍是独立、尚未执行验证的疑点。

## 第二阶段读到什么

完整读取本题 O/public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json，及 history/refs.json 唯一指定的 `H=R/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_1/records/iterative__dvc-9395.json`。仅按 H 的本题引用进一步读：

- `C=R/runs/env_probe_20260909_final_sync/ledger/logs_cc/iterative__dvc-9395/candidate.diff`，全文。
- `CL=R/runs/env_probe_20260909_final_sync/ledger/logs/iterative__dvc-9395/candidate/default/a1/test_output.txt`，目标失败栈 1195–1443、测试终态 4052–4083，以及相关检索命中；没有读完整模型轨迹或全日志。
- `CB=R/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_probe_20260909/ledger/cc_candidate_grading.jsonl`，严格只读本题第 17、40 行；第 40 行对应的 candidate_projected 原始日志未打开。
- `S=R/runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/iterative__dvc-9395` 的 gold/empty `offline/a1/status_map.json` 全文，gold `test_output.txt` 的 pygit2 错误和末尾测试摘要片段。
- 本轮另定位 GL/NL 的收集、实际 summary、退出码及 gold 无 hash 的 checkout 警告，以校正下述引用。

没有跟随 H 的跨题 prescan/5822/全批报告，没有读 acceptance 聚合、其他题结论或未来 Git 对象。原件的完整初判阅读范围、2 F2P/27 P2P 和 helper/fixture 均在初判列明。主审额外核的 S2 原行 146 与 recipe 审计文件校验是其工作；本轮没有将该报告当作独立重复验证。environment_record 的先前特权暴露已在初判登记。

## 旧候选失败的独立原始证据

CL 全文件 SHA-256=`aed853c7b1b95aafe3842a43381467e7948d51f18a6950edf0cca0bb8273639d`，与 CB:17 的 log_sha256 精确相等。该账本是 2026-09-08、root、default network、source image `sha256:479c3af753c367bfe088c4879524980c8f4ba0e67958c38db3ba6c5d2c4e0c0e` 的历史候选运行，不能混同 09-19 rh2grader/deny_all 的派生环境。

| 原件位置 | 实际事实 | 能支持的判断 |
| --- | --- | --- |
| C 的 Stage.run 和新增 pull_missing_outputs | 仅在非 dry 的数据源/frozen 验证分支，找不存在的 out，聚合 get_used_objs 后 cloud.pull，再 out.checkout；另改 CLI 帮助 | 这是按缺失源恢复的真实替代路线，有 dry 防护；没有恢复丢失的远端 run-cache 记录这一补充 |
| CL:1313–1328 | 测试 push(run_cache=True)，Mock cmd_run，删除 bar、lock、输出缓存和本地 runs | 要在禁止命令运行的条件恢复 bar，需要可用的运行缓存记录，而不仅是数据源输出 |
| CL:1277–1300 | Stage.reproduce→run→save→save_outs→out.save；output.py:659 因 bar 不存在抛 OutputDoesNotExistError | 运行未成功产生/恢复 bar，失败发生在业务调用内 |
| CL:1330–1332、1440–1443 | 测试箭头是 `(stage,) = dvc.reproduce("copy-foo-bar", pull=True)`，最终包装为 ReproductionError | 后面的 restore/不运行命令/checkout 次数/产物断言都尚未到达；不能用后置次数断言解释实际失败 |
| CL:4070、4081–4083；CB:17 | 数据源 F2P 通过，restore_pull F2P 失败，额外 import 失败；28 通过/2 失败；RESOLVED_PARTIAL，P2P 27 无失败 | 仅确认该候选在该历史条件部分通过。CB:40 的投影运行亦记同一 F2P 分布、projected_dropped=[]，但本轮未独立核该第二日志错误栈 |

因此同意主审 old_findings_delta 撤回 H check 24/issues 的“已有次数误拒反例”。也不反向推断次数断言没有问题：需要一个先满足数据源、远端 run-cache 恢复、产物/lock 与无重算行为的候选，实际跑到该断言并只因计数失败，才构成这种误拒证据。直接将断言改成 `>=2`，或仅凭旧 PARTIAL 判原题需修，都缺决定性支持。

## 与公开审查、主审及历史的比较

| 主题 | 独立复核裁定 | 决定性依据/限度 |
| --- | --- | --- |
| 公开要求与可解性 | 同意公开审查/主审：自动恢复本次所需缺失源，保留现有运行缓存能力，满足既有 dry/选图/用户修改约束 | prompt:9–11、commands/repro.py:129–145、Stage.run 和公开旧测试。H 说必须知道未公开最终内部设计才能修复，不成立；未读旧 hints 正文，不断言其实际注入 |
| 新 test_restore_pull 的功能要求 | 保留“所需 run-cache 记录缺本地时也能恢复并避免重算”的公开依据解释，不等同必须顶层拉全远端 runs | 测试只造一个所需记录，检查产物、lock、cmd_run 未调用；H 把它推成强制 gold 的时机/全量同步是过度推论。题面未穷举索引机制，仍需明确功能与内部策略之分 |
| checkout 三次 | 与独立初判及主审一致：公开目标不规定该数量，可能拒绝按需恢复等价解 | Q/test.patch:81；GL:2388/2422 显示无 hash 的 bar 预先 checkout 不创建文件，随后正常 restore/commit 完成。该额外调用存在，但是否有满足完整功能而仅计数不符的实际候选未知 |
| dry 回归 | 独立和主审在历史前分别发现，属于高置信静态疑点 | gold 两处新增 pull 不看 dry；StageCache.pull→transfer 会取 runs，repo.pull→fetch→checkout 会写缓存/工作区，而旧 StageCache.restore:201–213 有 not dry 保护。参考 dry 用例不带 pull |
| 不必要 remote 依赖 | 独立和主审在历史前分别发现；支持后续窄核 | 顶层 if pull 即 stage_cache.pull(None)，先走 get_remote_odb/get_remote；本地不变阶段原可跳过。预计无 remote 时新增 NoRemoteError，HTTP run-cache 亦有显式不支持路径，均未执行 |
| 用户修改/旧输出缓存 | 主审保留用户修改风险；初判另外提出“依赖已变、旧输出缓存未上传时，先 fetch 旧 hash 可阻断本可重算的阶段” | stage.changed 包括变化，不只缺失；repo.pull 的 allow_missing 给 checkout，fetch 的 DownloadError 仍可能先抛。第三方 checkout 的覆盖/交互细节未核，不能宣布已证数据覆盖；暂不扩成首要实验 |
| import 环境 | 旧故障真实，但“永久失败”已被当前 grader 原件推翻 | S/gold/test_output:598–601 为 GIT_OBJ_COMMIT ImportError；当前固定 pygit2==1.14.1 且 GL:2452 import 通过。旧建议 `<1.14` 不是当前应继续执行的修复；actor 是否消费此配方仍未知 |
| import 参考缺席 | 独立、主审均确认实际执行 30 与来源参考 29 不同 | import 在 GL/NL 实际 F→P，却不在 2 F2P/27 P2P 中。H 说为藏环境失败才移除，没有数据集生成因果证据。也未执行只损坏 import 的候选，不能断言它一定 reward=1 |
| intermediate_out 的 P2P | 不同意 H 把 base 已通过称无效条目 | P2P 就用于保护既有能力；测试不禁止 echo 重算，故只能限定其覆盖强度，不能要求每个新增测试都必须 F→P |
| 运行计数/parser | 主审正确区分 29 个参考、30 个执行、31 个 parser 条目 | 旧 status_map 的 Could/日志伪键确实存在；本轮不审共享 parser，也不据旧键自动确定当前多余那一键的身份。当前全部参考 ID 状态均对账 |
| 提交恢复/题族 | 同意无新增路径排除；不同版本或文件不交集也不足以保证无派生关系 | 当前只恢复两个官方测试文件，gold 源码可投影；H 引别题测试丢弃不能代替本题证据。本包三题关系见末节 |

## 引用校正与独立初判遗漏

主审描述的 09-19 通过/失败事实可由原件确认，但 analysis_before_history.md 和 old_findings_delta.md 的多处 GL/NL 行号并不对应它们声明的日志。为保证可复查，本报告采用独立 `nl -ba`/检索核出的实际位置：

| 事实 | 本题 09-19 指定原件的正确位置 |
| --- | --- |
| gold 收集 30、全部通过、退出 0 | GL:650；GL:2434–2464；GL:2465–2468 |
| noop 收集 30、27 过/3 失败、退出 1 | NL:610；NL:2950–2980；NL:2981–2984 |
| gold import 和 intermediate 通过 | GL:2452–2453 |
| gold test_restore_pull 对无 hash 的 bar 预先 checkout | GL:2388、2422，不能引用 GL:3607/3614 |
| noop restore_pull 缺 bar 的原始异常 | NL:1344–1349 |

主审所写 GL:3626–3660、NL:4046–4080 等范围超出这里的实际日志长度。报告不据此否定它有真实运行证据，但这些引用需要以后非封存增量中纠正；本轮只在 review.md 明确标注，不改其封存分析。旧 CL 的 4 千余行是另一条件的另一日志，不能与 GL/NL 混用。

独立初判未充分强调一个 actor 验证陷阱：公开 base 的 `test_restore_pull` 仍断言 checkout 两次（tests/func/test_run_cache.py:182），私有 patch 改为三次。因此直接把 public_read 的“这些旧测试修复前后预计均通过”当作 gold 开发验收标准会误导。即使功能达到本题私有正例，gold 仍可能因旧公开次数断言失败。这属于公开/私有 oracle 变更，需查看具体断言并用行为复现判断；不能告诉 solver 隐藏测试要求三次，也不宜把旧测试改绿当作功能正确的唯一证据。本点是第二阶段新增说明，未回写初判。

## 八方面收口与有界用途

1. **公开要求**：缺失所需源的自动恢复可从公开题面和代码定位；不是要求强制全仓/全 remote 同步。缺失和已修改、dry 与普通执行需区分；目录部分缺失与修改混合规则未穷举。
2. **材料/初态**：base `c75a5583b3840ba90a8e800a0f42c1cb120916db`、补丁、指定日志 hash 独立相符；noop 原始错误位置与缺陷链一致。未重建 tree、未核所有上游对象或真实 actor 初态。
3. **测试命中**：全部新增/修改断言和 2 F2P/27 P2P 已逐条读，local_remote、run_copy、erepo/Git fixture 与脚本已追；新增 import 是已执行额外项。成功返回和存在性不足以替代完整字节/目录/修改保护。
4. **合理实现接受**：真实本地文件正例有行为意义，但 restore 恰一次及 checkout 三次有耦合；旧候选不能证成次数误拒。合理按需 source + 远端 run-cache 恢复路线仍应保留。
5. **gold/回归**：gold 修复当前两个 F2P，历史 30 绿；dry/no-remote 是具体新增静态疑点，现有 P2P 没有组合保护。CLI/exp 共用参数与 executor 的调用点读过，完整实验队列/外部依赖未审。
6. **开发条件**：09-19 grader 为 derived image `sha256:e64191bff363b956d9f4fc6f2abde42eecbcc21cbf4fe47a01b7404f942f457b`、pygit2 1.14.1、Python 3.9.19/pytest 7.4.4、rh2grader/54322、deny_all、2 CPU/4 GiB；已离线安装。actor 的解释器、可写目录、包来源和配方消费不能由此填入。
7. **交付/评分**：repo/reproduce.py 是合法可交普通源码，两个官方测试单独恢复；不增排除。不按 dvc/testing 名称把 fixture 源码统一当不可提交文件。真实模型消息、镜像 Git/缓存/mount 与控制面隔离未验。
8. **关系/用途**：在本包第三题独立初判中已记到本题 base/dvc/utils/fs.py:55–72 含 3620 gold 的 `_unlink` 结构，形成顺序答案暴露渠道；不是同一缺陷。审核员已见三题私有材料及本题历史候选，不可作为未暴露 solver、成功率或训练价值证据。

当前可用范围是已知 local default remote、普通非 dry 的缺失源及运行缓存恢复开发诊断，结果须标注上述未覆盖分支。不能据此宣称普遍 `repro --pull` 质量已验收，也不继续沿用旧 needs_repair 的“永久依赖失败/已证次数误拒”理由。无本轮任务修订、评分引用改写或新执行结论。

## 最小后续动作（均未执行）

采用主审的一个优先 CPU 对照，并收紧输入说明：在真实统一 actor 入口先核 UID、sys.executable、dvc.__file__、本地 tmp/cache/remote 可写和实际 recipe；构造本地 foo 数据源与 cp 消费者，将内容 push 到本地 remote，然后在各 fresh 复本移走 foo 和对应本地对象。若要同时观察 runs 下载，可先生成并 push 一个确定相关运行缓存记录，再在每份初态删除本地 runs，保持远端内容相同。记录 foo/bar、cache/runs、lock 的存在性和内容。

对 base/gold 分别调用 `reproduce(pull=True,dry=True)`；判据是工作区和数据缓存不被下载/检出改变，而非日志格式或内部调用次数。再在另两个同初态复本调用 dry=False 作正对照，应看到 base 缺源失败而 gold 恢复完成。该对照将把目前控制流推断转成可复核副作用证据，并把环境失败与行为失败分开。无需私自执行更多组合或模型任务。

只有这一优先核完成后，再决定是否值得用“已完整且不变的本地 pipeline、没有 remote、pull=True”的最小 base/gold 对照核 NoRemoteError，或构造业务完全等价的按需恢复候选核次数误拒。后续若修订次数 oracle，应保留产物/lock、内容和无重算的公开行为要求；不为匹配 gold 随意放宽成 `>=2`。上述 CPU、actor 和修订全部尚未执行。
