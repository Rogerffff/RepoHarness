# scrapy__9a15fcf8 独立复核·第二步（公开读者、主审产物与历史开放后）

2026-09-25 · 独立复核者（静态）。

- 本步读了：公开读者稿、封存初判、接续会话的三份产物、`refs.json` 所列的历史文件及其引用的原始证据。
- 没有运行代码或容器，没有改任何原件。
- `reviewer_initial.md` 是封存稿，未改动。
- 路径均相对仓库根。缩写：`P4=runs/r2e_env_repair_20260924/p4`，`HIST=docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924`，`IID=scrapy__9a15fcf89a151811de8ac783419df0512c863d5e`。

## 0. 结论

### 同意（事实层面全部复核成立）

1. **目标键与运行稳定性。**
   - 唯一目标键是 `test_from_content_type`。
   - noop 与 gold 在两组 current 运行中结果一致，M3 的 noop ×2、gold ×2 也一致。
   - 题面描述的报错确实出现在 noop 目标键上。
2. **`test_from_headers`、`test_from_args` 是只会拒绝正确行为的死键。**
   - 它们的状态只有在整个测试方法全部通过时才会改变。
   - 而全部通过要求每一组断言都拿到正确的类。
   - 所以这两个键拒不掉任何错误实现，只会拒绝正确的 Py3 修复。
3. **根因是搬迁绕开了 `tests/py3-ignores.txt:40`。**
   - 封存初判和我的初判在读历史之前各自独立发现了这一点。
   - `refs.json` 所列的历史文件里没有出现 `py3-ignores` 或 `collect_ignore`（grep 为空）。
4. **"P4 候选经真实评分 7/7 通过但 reward 为 0"对应的就是当前材料。**
   - 运行身份见 §2 C4。
   - 需要补标：这是单次运行，候选是构造出来的诊断补丁。
5. **只删期望键无效，必须两侧对称去掉。** 生产代码和离线重算都支持这一点。
6. **处置建议。**
   - 推荐 B：删掉两个测试方法，期望同步删两键。
   - D 作为退路。
   - A′ 只用于修订前的诊断判读。
   - K1′ 不夹带进 B。
   - 处置 `needs_review`，用途 `development_diagnostic`。

### 修改（card / record 需要改的地方）

1. **"正式 actor 用来源镜像"已过时。**
   - 依据有两条：一是协调者 09-25 的事实更新；二是工作树里的 `rh2/src/repoharness2/adapters/slime/prepared_task_face.py:443,447`，R2E 已改用 `overlay.derived_image_id` 和 `R2E_INTERPRETER_PREFIX`。这是未提交改动，我只做了静态阅读，没有审查。
   - 需要改的位置：card §1 "建议用途"最后一条、card §4.4、record `recipe_ref.formal_actor_image_note`、`checks.29`、issue `shared_formal_chain_source_image`。
   - 应改为："代码已切到派生镜像与 `.venv` 前缀，待 A 线审查；本题在 actor 条件下的开发命令证据还在排队。"
   - `checks.29` 从 issue 改为 unknown（待审）；`checks.8`、`checks.10` 维持 unknown。
2. **P4 证据的标签要写全：** "历史真实 RH2 评分；当前材料；**单次**；构造的诊断补丁（账本 `candidate.kind="cc"` 只是标签，不是模型产物）；期望版本由不符模式推定（账本没有记期望摘要）"。
3. **四处措辞需要收紧，都不改变结论：**
   - "恢复上游 py3 忽略意图"改为"与上游在 py3 下不评估该文件的做法同向，范围更窄"。上游忽略的是整个文件，B 只去掉在 py3 下必然失败的两个方法。
   - "修法几乎唯一"改为"修改位置集中，题面几乎点明方向"。公开读者列出了三种等价写法（表项、JSON 族规则、别名归一），实现并不唯一。
   - card §3 的"两次独立探针"改为"同一探针工具在同一派生镜像上的两次运行"（`P4/dev_probe/…` 与 `_accept/p4/dev_probe/…`）。
   - record `checks.2` 的"R-f、中央复跑和 M3 各有 2 份日志"：前两组各是 noop 1 份、gold 1 份，M3 才是 noop ×2、gold ×2。
4. **A′ 判读规则要补两个前提，防止把控制面改动当成"过度修复"：**
   - 账本的 `candidate_touched_conftest_or_fixture` 为空；
   - 投影 `included_paths` 只含库源码。
   - 另外要写明：A′ 只能事后解读账本，改变不了 reward 本身，所以不能用于训练奖励。
5. **B 的验收补上 E16 的期望核定方法**（`HIST/decisions.md:20`）。
   - 先在一次性容器里按 grader 顺序试跑，确认用原材料能由 gold 日志逐字重现来源期望；
   - 再用修订后材料跑 gold 两次，断言修订后期望与两次试跑逐键相同。
   - 接续会话列的"四候选各 2 次，键集剩 5 个"保留，但不能替代上面这一步。

### 保留（未决，或需要真实轨迹才能判断）

1. **B 与 D 之间的选择是用户的 T0 决定。**
   - 事实只能说明 B 的工具链已经现成（§4），不能替用户权衡"为一道低难度题重建镜像"值不值。
   - 我与接续会话一样倾向 B；D 也合理。
2. **B 之后仍有一处盲区（低优先）。**
   - 一个候选如果把 `Headers` 在 py3 下改成存 str，会破坏 bytes 契约，这是题外的有害改动。
   - 这种候选现在会被死键拒掉，但只是巧合：拒掉的同时也拒掉了正确的 bytes 兼容修复。B 之后它能拿 1 分。
   - 这不构成反对 B 的理由：该契约现在也没有任何有效测试保护。
3. **模型会不会被引向会被判 0 的修复，未知（清单 34/35）。**
   - 显式运行公开 `tests/test_responsetypes.py` 时能看到两个 `TypeError`，这可能引导模型去做更完整的修复。
   - 静态审查不能代答，需要真实轨迹。

### 最小后续实验

- **若 B 获批**：在修订后材料上做 E16 的试跑核定，然后 noop、gold、P4 over-fix、只解码 content_type 的部分修复各跑 2 次，并核对键集只剩 5 个。预期依次为 0 / 1 / 1 / 1。
- **若暂不修订、又要用 A′ 判读探针**：先在当前材料上单跑一次"只解码 content_type"的候选，预期得 1，用来确认翻转边界的静态推断。
- **actor 侧**：等派生镜像链路通过 A 线审查后，以 agent 身份跑本题的开发命令。协调者说明这一项已在排队。

## 1. 本步读取范围

**本批 `OUTPUT_DIR` 内：**
- `public_read.md`、`analysis_before_history.md`；
- `old_findings_delta.md`、`card.md`、`screening_record.json` 全文。

**历史（`refs.json` 全部条目）：**
- `HIST/tasks/IID/{findings.md, screening_record.json}`：读关键字段；
- `HIST/material_revisions/IID.md`、`HIST/repros/IID.py` 全文；
- `HIST/packages/p4/README.md` 全文；
- `HIST/decisions.md`：E13、E16、E24、T0-4、T0-5、T0-6 行；
- `HIST/known_issues.json` 中 `refs.json` 点名的三个族；
- `HIST/results_20260924.md:56`。
- 未读 `HIST/tasks/IID/facts.json`。

**历史引用的原始证据：**
- `P4/overfix/IID.diff`：全文，并核对 sha256；
- `P4/ledger_overfix.jsonl:1`：全字段，与 current 两个 gold 行逐字段比对；
- `P4/eval_logs/…p4-_1acaf88b.eval.log`；
- `P4/rerun_overfix_1848.log`、`P4/offline_rescore_9a15fcf8.json`；
- `P4/targeted_public_tests/IID/{agent_probe.log, container.json}`；
- `P4/dev_probe/IID/agent_probe.log`、`P4/targeted2_cmds/IID/agent_probe.log`；
- `P4/tools/targeted/dev_probe_agent.sh`、`lists/IID.txt`；
- `runs/r2e_env_repair_20260924/_accept/p4/dev_probe/IID/{agent_probe.log, container.json}`；
- `runs/env_overnight_20260916/M3/facts/9a15fcf89a15/noop_x2/out{1,2}.txt` 的状态段；
- `runs/r2e_rf_20260923/reconcile_all/reconcile.json` 第 44、92 项。

**代码与封板输入（只做静态阅读）：**
- `rh2/src/repoharness2/envpack/r2e_parsers.py:90-140`；
- `rh2/src/repoharness2/envpack/scoring.py:60-76, 339-405, 463-476`；
- 以上两个文件的 sha256 与 `runs/r2e_snapshot_20260923.sha256:107-108` 一致；
- `rh2/src/repoharness2/adapters/slime/prepared_task_face.py:412-451`：工作树里的未提交版本；
- `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v{1,2,3}.json`：只 grep 本题，均无条目；
- `s2_r2e/t1_input_pins_r2e_v4.json` 头部：指向修订单 v3。

**没读：**
- 本批 README 与 `assignments.json`；
- `HIST` 的 README、acceptance、dispositions（接续会话读过其中的 grep 行，并已自行披露）；
- 40 项清单：record 里 `checks` 各编号的语义我不作核对；
- 其它题的记录；
- 各次运行的 `diagnostics.json`。

## 2. 主审决定性主张逐项核对

| # | 主张（出处） | 我核对的原件 | 结论 |
| --- | --- | --- | --- |
| C1 | 目标键唯一；noop 的报错与题面一致；noop 和 gold 在两组 current 运行中各自一致（封存 §0、§3(b)；接续 H1–H4） | 初判已核对四个账本行与日志；本步补读 M3 noop ×2（`out1/out2.txt:107-115`） | **成立** |
| C2 | 两键在第一个带头映射处抛 `TypeError`，后面的断言不执行（封存 §3(a)；card §2） | noop 日志 `:50`、`:58`、`:102-112`；`test_from_args` 的第 1 组（url → csv）先执行并通过，第 2 组才抛错 | **成立**。补充：已执行的那一组即使出错也还是 FAILED，所以两键不提供任何保护 |
| C3 | 根因是 `py3-ignores` 搬迁伪影（封存 §2 反向核对；接续 H6） | `worktree/tests/py3-ignores.txt:40`、`conftest.py:25-29`；历史文件 grep 为空 | **成立**，而且是读历史前独立得出的 |
| C4 | P4 over-fix 经真实评分 7/7 PASSED、reward 0（封存 §3(a)；接续 H7；card §2） | 见下表 | **成立**，但要按 §0 修改第 2 条补标签 |
| C5 | 只删期望键时 gold 也会得 0；两侧对称去掉后 noop 0 / gold 1 / over-fix 1（接续 H8） | `scoring.py:463-476`：`unexpected = obs − exp`；`:64-76`：只有键集相等且全部匹配才算 resolved；`r2e_parsers.py:135` 要求两侧键数相等；`P4/offline_rescore_9a15fcf8.json` 的 9 行结果 | **成立**。证据级别是**离线重算**，即在现有日志上模拟去键，不是在修订后材料上真实评分 |
| C6 | parser 按子串识别状态；用 skip 时理由里不能出现 `PASSED`、`FAILED`、`ERROR`（接续 §2.2） | `r2e_parsers.py:102-110`：某行只要含这三个大写词之一就成键，SKIPPED 行本身不成键 | **成立**。删方法最简单；用 skip 也可行，但理由措辞要受限 |
| C7 | D 的成本论据已部分过时：E16 的 `material_v2` 已支持改隐藏测试和改期望，cfed9b66 已按它修订（接续 H19） | `decisions.md:20`（E16：`edits` 与 `expected_file_replace`，逐键声明增删）、`:42`（T0-5 验证 noop 0 / gold 1 各 2 次）、`:43`（`r2e-mr-007` 期望"删 2 键加 13 键"，说明删键已经用过）、`:28`（E24：修订单 v3 / pins v4）；修订单 v1–v3 均无本题条目 | **成立** |
| C8 | 以下为镜像层面实测（接续 H9–H13）：公开测试 5 过 2 败、`cwd=/tmp` 也能导入、没有 pip、site-packages 可写、私有目录拒绝访问 | `P4/targeted_public_tests/IID/agent_probe.log:2-5, 79-81`，容器为 `fe908bed…`、`NetworkMode=none`；`P4/dev_probe/IID/agent_probe.log:5, 11, 14, 26, 28, 34-35, 64, 66, 123, 126` | **成立**。补充：probe 的 `BASH_ENV_VAR` 为空（`:7`），没有经过 `/rh2/bash_env`，所以仍只是镜像层面 |
| C9 | 历史说的"两个独立 runner"其实是 M3 一个 runner 的两份日志（接续 H5） | `reconcile.json` 第 44、92 项：每项两组比较的 `source` 都是 `m3` | **成立** |
| C10 | 正式 actor 用来源镜像（card、record、封存 §7） | 协调者 09-25 更新；`prepared_task_face.py:443, 447`（工作树未提交） | **已过时**，见 §0 修改第 1 条 |
| C11 | "全池只此一题属可翻转键"（历史提案 `:21`、`decisions.md:41`） | 未核对 | 同意接续会话标"未核实"；只影响 C 值不值得做，不影响本题 |
| C12 | 静态阅读的生产代码与 R-f 运行时的代码快照相同（接续附录 A） | 本机 sha256 为 `7c26f6a2…` / `339b7c80…`，等于快照 `:107-108` | **成立** |

**C4：P4 over-fix 用的是哪次运行、哪个材料版本。**

| 项 | 值 | 与 current 四行的关系 |
| --- | --- | --- |
| 运行 | run_id `r2e-envrepair-p4-overfix`，unit `r2e-p4-rerun-1848`；`started_at_utc` 2026-09-23T18:48:15Z；**只跑了 1 次**（`HIST/packages/p4/README.md:94, 107`；`P4/rerun_overfix_1848.log` 为 1 行，exit 0） | 与中央复跑同属环境轮 |
| 账本 / 日志 | `P4/ledger_overfix.jsonl:1`；`P4/eval_logs/evallog_replay-r2e-envrepair-p4-_1acaf88b.eval.log` | — |
| 隐藏测试 / 入口 | 日志 `:4-5`：`a3f0f6e4…` / `8285765f…` | 与 current 相同 |
| 期望 | 账本没有记期望摘要。观测 7 键全部 PASSED，不符的恰好是期望为 FAILED 的两键，只能由当前期望（`2fefa8a5…`）得出；本题 `material_revisions=[]`，修订单 v1–v3 无本题条目，当时不存在其它版本 | 推定相同 |
| 镜像 / 配方 | `fe908bed…`，`r2e_derive_v1`（`0da821a1…`） | 相同 |
| grader | `scripts_digest 40c81112…`，`grader_profile_digest 1bb8e0cf…`，`grader_version r2e-gym-subset@e8b9fcbc+parser:prime-envs@c4d04dfe`，`RH2_OBS_RUNNER_DIGEST 067c6080…`，`baseline_policy_r2e_v1` | 逐字段相同（只有期限不同：900/3600，与中央复跑一致；R-f 为 1800/1800，不影响判分） |
| 用户 | 以 agent/54321 通过 `git_apply` 应用补丁；评分用户 rh2grader/54322；`deny_all`；2 CPU / 4 GiB | 相同 |
| 候选 | `P4/overfix/IID.diff`（sha256 `81cedada…`，与账本一致），内容为 gold 那一行，加上 `from_content_type`、`from_content_disposition` 各一处 `isinstance(…, bytes)` 后按 latin-1 解码 | 构造的诊断补丁，不是模型产物 |

## 3. 反查：主审可能没想到的范围

1. **把 0 分辩护为"范围纪律"不成立。**
   - 有人可能认为：R2E 精确匹配本来就要惩罚题外改动，over-fix 得 0 是可辩护的。
   - 但这两个键编码的不是"不要改无关代码"，而是"py3 下 header 路径必须继续崩溃"。
   - 这一点在任何公开材料里都没有依据。公开读者 A2 和关键未知 2 独立指出，公开材料无法判断 bytes 兼容是否被期望。
   - 如果真想要"最小改动"信号，应当作为显式的设计决定，而不是依赖一个 py3 伪影。
   - 所以我同意主审把它定为误拒。
2. **主审有没有先看答案、再把隐藏要求说成"显然"。** 没有发现实质问题。
   - 目标要求 R1 的依据是公开题面。
   - R3（其它入口）主审标的是"缺失"，而不是"显然"。
   - "修法几乎唯一"是轻度夸大，见 §0 修改第 3 条；它的方向（难度低、题面强烈暗示）与公开读者 §3.1 的独立判断一致。
3. **公开读者的疑义分两类。**
   - 可以消除的：
     - 只在 `from_content_type` 特判能否被接受：能，因为隐藏测试只测这个入口；
     - `import scrapy` 能否成功：能，镜像层面已实测；
     - `.venv` 会不会出现在 `git status`：不会，日志只列出两行未跟踪文件。
   - 不能从公开材料消除的：A2（bytes 兼容是否被期望）。这条恰好被 P4 证实为评分陷阱，所以它不只是一个疑义，而是有私有证据支撑的问题。
4. **接续会话在读历史之前没有独立判断。**
   - 本题的核心结论另有三个读历史前的独立来源：封存初判、我的初判、公开读者（它独立指出了 py3-ignores 和 bytes 风险）。
   - 接续会话在读历史后新增的内容，我都在原件上核对过：C5 的代码部分、C6、C7、C9。
   - "B 优于只加判读规则"的倾向，早在封存初判 §6 和我的初判里就有了，不是被历史带出来的。
   - 所以接续会话缺少独立判断，并不削弱结论。
5. **全池扫描规则可以补一个优先对象**（超出本题，未核实）。
   - `HIST/known_issues.json` 的 `expected_non_passed_keys` 族记有 aiohttp `240da100` 的 2 键，原因是"上游在 Python 3.9 上本就失败"。这与本题同属年代错配。
   - 建议把接续会话提出的"原文件在 collect_ignore / py3-ignores 中"规则，与 P4 README §7.5 的"traceback 落在库代码里"规则合用，并先查这一题。
6. **site-packages 与 `.venv/bin` 对 agent 可写**（`dev_probe/…:34-35`）。
   - 候选对它们的改动会不会进入评分，取决于共享的 delta 捕获机制。P4 README §4 和接续 H13 都已登记为共享面。
   - 本题的合法解用不到它们，不单独处理。

## 4. 修订 B：依据、范围与实施

- **依据。** 有四条，均已核对：
  - 死键：日志证据；
  - P4：单次真实评分；
  - 上游在 py3 下不评估该文件（`py3-ignores.txt:40`）；
  - 现成工具链：E16 / `material_v2`，删键已在 pandas `r2e-mr-007` 用过。
- **是否扩大原需求：不扩大。** B 不新增任何断言。K1′（`application/json` 断言）属于扩大测试标准，需要单独决定——同意主审的处理。
- **是否缩小原需求：不缩小。**
  - 目标键和 4 个回归键不变。
  - 被删的两个键目前不保护任何行为（C2），它们唯一的作用是施加一条没有公开依据的隐含要求："py3 下 header 路径必须继续崩溃"。
  - B 移除的就是这条要求。
  - 修订后，`content_encoding → Response` 和整条 header 路径没有测试覆盖。这和现状实质相同：现在它们只出现在死键里。
- **实施。**
  - 私有 `test_1.py` 用 2 条 `edits` 删掉两个方法。每条 `edits` 必须在原文中恰好命中一处，这两个方法块都是唯一的。
  - 期望用 `expected_file_replace`，并在 `expected_change` 中声明删除这两个键。
  - 不改 `run_tests.sh`，同意接续会话的理由：它在公开工作树中可见，改了会同时改变公开材料和入口摘要。
  - 用 skip 也可以，但理由措辞要避开三个大写词。
- **代价。**
  - 要重建本题的派生镜像，并升级修订单 v4、pins v5。
  - 与 M3 的同版本对照就此失去，对账时本题要单列。按环境卡 §1，改用一次性容器试跑逐键对照。
  - 还有 §0 "保留"第 2 条所说的 `Headers` 契约盲区。

## 5. "可探针"：静态候选与剩余条件分开写

card 与 record 已经把"题意 / 测试争议"和"actor 待验"分开写了，但剩余条件没有逐项列出，而且其中一条已经过时。建议按下表改：

| 类别 | 条目 | 状态 |
| --- | --- | --- |
| 已满足：静态 / 评分侧 | 题意清楚；目标键与题面一致；gold 与 noop 在当前材料下稳定，并与 M3 逐键一致；合法解只需改 `scrapy/responsetypes.py` | 已核对 |
| 已满足：镜像层面 | 解释器 `.venv` 3.9.21；pytest 可用；没有 pip，也不需要；显式路径运行公开测试 5 过 2 败；复现成立 | 历史镜像层面实测，本步已复读原件 |
| 剩余：材料 | T0-4 选 B、D，还是 A′ | 待用户决定。作 reward 前必须完成 B；修订前只能按 A′ 做诊断判读 |
| 剩余：正式链 | 派生镜像、`.venv` 前缀、R2E 提示措辞 | 代码已改（工作树未提交），待 A 线审查 |
| 剩余：actor 条件 | 经 Claude Code 非交互 shell 与 `/rh2/bash_env` 启动后的开发命令 | 排队中，协调者另行汇总 |
| 不属于准入条件 | 模型会不会被引向会判 0 的修复（清单 34/35） | 需要真实轨迹 |

主审没有把"环境已验"当成质量合格：历史里"环境无缺口"的说法，接续会话已明确限定为派生镜像。

## 6. 与我初判的差异

- **一致的部分**：主问题、py3-ignores 根因、修订方向（删两键）、K1′ 漏测反例、唯一优先下一步（用户就修订拍板）。
- **本步补上、更新或确认的部分**：
  - P4 diff 的内容：初判没有读，当时只是从结果反推它两处都处理了，现已由原件证实；
  - M3 noop ×2 这份证据；
  - 正式链状态：初判引用的环境卡说法已过时；
  - 显式路径运行公开测试和 `cwd=/tmp` 导入：由静态推断升为镜像层面实测；
  - E16 工具链已经就绪，B 的成本比环境阶段估计的低。
- **初判中的内容，本步没有推翻**：`candidate_touched_conftest_or_fixture` 是否参与判定，我仍然没有核对。在 §0 修改第 4 条里，我把它写成 A′ 的一个前提，而不是去断言它参与了判定。

## 7. 未解决的分歧（显式保留）

- **B 与 D 之间。** 事实层面没有分歧，这是价值取舍，由用户按 T0 决定。
- **其余。** §0 "修改"各条都是补标签或收紧措辞，不涉及结论。主审与复核在事实和处置方向上没有未解决的分歧。

## 附录：关键定位

- **P4 over-fix**
  - 账本 `P4/ledger_overfix.jsonl:1`；
  - 日志 `P4/eval_logs/evallog_replay-r2e-envrepair-p4-_1acaf88b.eval.log` 的 `:4-5` 与 `:33-39`（全部 PASSED），`:42` 为 `RH2_TEST_RC=0`；
  - diff `P4/overfix/IID.diff`；
  - 单次运行：`HIST/packages/p4/README.md:94, 107`。
- **离线重算**：`P4/offline_rescore_9a15fcf8.json`，共 9 行：
  - v0 期望：noop 0、gold 1、over-fix 0；
  - 只删期望键：三者都是 0，其中 gold 的两键记为 unexpected；
  - 对称去掉两键：noop 0、gold 1、over-fix 1。
- **评分口径代码**：
  - `rh2/src/repoharness2/envpack/scoring.py:64-76`（`resolved` 的定义）、`:381`（只解析 Start / End 段）、`:463-476`（并集口径）；
  - `rh2/src/repoharness2/envpack/r2e_parsers.py:102-110`（按子串识别状态）、`:135`（两侧键数必须相等）。
- **镜像层面**：
  - `P4/targeted_public_tests/IID/agent_probe.log:2-5, 79-81`；
  - `P4/dev_probe/IID/agent_probe.log:5, 7, 11, 14, 26, 28, 34-35, 64, 66, 123, 126`；
  - `_accept/p4/dev_probe/IID/agent_probe.log:2-3, 121-123`（容器 `fe908bed…`，2026-09-23T19:04Z）。
- **历史决定**：
  - `HIST/decisions.md:20`（E16）、`:28`（E24）、`:41`（T0-4：用户 09-24 晚决定留给质量筛查）、`:42`（T0-5）、`:43`（T0-6）；
  - 提案 `HIST/material_revisions/IID.md:34` 推荐 D。
- **正式链代码**：`rh2/src/repoharness2/adapters/slime/prepared_task_face.py:443`（`image=overlay.derived_image_id`）、`:447`（`R2E_INTERPRETER_PREFIX`）、`:451`（非 R2E 来源仍用 `public.image`）。均为工作树未提交版本，未审查。
