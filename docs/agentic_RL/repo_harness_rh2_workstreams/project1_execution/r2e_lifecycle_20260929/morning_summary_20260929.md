# R2E 单题闭环试行：09-29 晨报（Claude B）

整理于 09-29 08:42。逐条事实与时间线在 [README §8](README.md)，逐题状态在 [status_table.md](status_table.md)（脚本生成）。下文区分**已验证 / 已实施 / 建议 / 待您决定**。

## 1. 结论

1. **可以进 GPU 基座探针的题（已验证）：19 题。**准入卡在 `results/<题>/probe_card.md`。
   - 第 1 轮 7 题：numpy `18b7`、`5e83`、`a5ea`，pillow `3a61`，scrapy `e938`、`7545`、`9a15`。
   - 第 2 轮 6 题：coveragepy `9799`、`ea69`，aiohttp `1c1c`、`22a1`、`6183`，pillow `3ac9`。
   - 第 3、4 轮 3 题：pandas `32dd`；aiohttp `240d`（今晚新审完、走完全流程的第一道题）；datalad `19f5`。
   - 第 5 轮 1 题：numpy `d805`（今晚新审）。修订后 gold 按设计为 0，正对照用经独立核实的替代解 K-A5b；以后环境复验也要用它，否则会被误报成环境回归。
   - 第 6 轮 1 题：orange3 `4014`（编译题）。今晚补做 v1 第 3 步发现 S1，做了 R-c，修订后正式评分 8/8、devcheck 通过。
   - 第 7 轮 1 题：numpy `d89b`（今晚新审）。四项修订，正式评分 10/10、devcheck 通过。
   - datalad `19f5` 与 orange3 `4014` **带链路条件**：正式评分是在评分时限放宽到 1200 s 下得到的（见第 3 条）。
   - 没进名单、需要注意的：
     - coveragepy `5dbb`、`f5eb`：P5 未决，不进探针。
     - pandas `4ec8`：修订与第 5 轮正式评分都已验收，但**我漏派了独立复核**（v1 §7.3 要求每题都做）。补做的复核提出新退化候选 D1，**在修订后的材料上正式评分仍得 1**，所以本题还有未处理的 S1。再修订受修订单机制限制，见第 3 节第 6 项。
2. **探针链路（已验证 + Codex 复核）**：R2E 题能走统一探针链路，但要换用 R2E 求解入口、评分带覆盖表；Codex 结论是**"改后可以"**。真实模型运行前必须先处理：
   - **静止屏障以 root 执行 agent 仓库里的 git**：agent 写进 `.git/config` 的程序会以 root 身份执行，正式 profile 挡不住。这是 A 线正式代码、属安全边界，**待您决定**。
   - 往返核对不一致、评分 fatal 时"停止派发"还没实现（原型与共用派发器都没有）。
3. **评分超时是链路与宿主问题，不是题目问题（已验证）**：
   - 原因：datalad、orange3 这类大环境题，评分前要 `chown -R` 整棵工作区；本机 overlay 没开 metacopy，这一步会复制整棵树。
   - 耗时：本机 152–339 s，高低取决于同时有几路评分；缺省时限是 300 s，所以并发时基本都超时、记 `infra_failure`。09-25 在另一台机器上，同一步只要 35–54 s。
   - 放宽到 1200 s 后，缺省时限下超时的 10 题（datalad 5、orange3 5）全部 noop 0、gold 1。
4. **未审 28 题（进行中）**：
   - 已进探针名单：aiohttp `240d`、numpy `d805`、numpy `d89b`。
   - 暂挂：coveragepy `f5eb`（C1 的 P5 待您定）；pandas `4ec8`（见上）；datalad `16c1`（R-b 经 Codex 判为 P5，待您定，见第 3 节第 8b 项）。
   - 第 8 轮已落材料、正式评分中：aiohttp `4075`（gold 自己把请求目标里的换行等控制字符从拒绝改成了接受，修订后 gold 按设计为 0，改用替代解作正对照）、pillow `2d01`（字节断言按位序归一；新增的等价实现在新草案得 1、旧草案得 0）。
   - 修订执行中：scrapy `a95a`（按 Codex 补绑定方法实例，正对照改用替代解）、pillow `4bc6`。
   - 主审第 2 步中：datalad `6b6f`、orange3 `50f6`。两题都已实跑坐实"一处误拒合理解（T1）+ 退化或错误候选拿满分（S1）"。
   - 其余 16 题排队。
   - 规律：主审定稿的 10 题全部判了 S1，主要是两类——核心断言只用题面示例的字面值（v1 第 2 步），或退化候选正式评分得 1（第 3 步）。datalad `6b6f`、orange3 `50f6` 的第 1 步也暂判 S1。这类题要先做 R-c 才能进探针，不修订的话只能作问题定位。

## 2. 已验证的证据

| 轮次 | 修订单 / pins | 题 | 正式评分验收 | devcheck | 准入卡 |
| --- | --- | --- | --- | --- | --- |
| 第 1 轮 | v4（`r2e-mr-021`–`033`）/ v5 | numpy ×3、pillow `3a61`、scrapy ×3 | **44/44** 与期望一致 | 7/7 全过 | 7 题 probe_ready |
| 第 2 轮 | v5（`r2e-mr-034`–`047`）/ v6 | coveragepy ×3、aiohttp ×3、pillow `3ac9` | **47/47** 与期望一致 | 7/7 全过 | 6 题 probe_ready，`5dbb` on_hold |
| 第 3 轮 | v6（`r2e-mr-048`–`050`）/ v7 | datalad `19f5`、pandas `32dd` | **13/13** 与期望一致（datalad 7 项用 1200 s 放宽时限、单独记账） | 2/2 全过 | 2 题 probe_ready（datalad 带链路条件） |
| 第 4 轮 | v7（`r2e-mr-051`–`052`）/ v8 | aiohttp `240d`（今晚新审） | **7/7** 与期望一致 | 过 | probe_ready |
| 第 5 轮 | v8（`r2e-mr-053`–`056`）/ v9 | coveragepy `f5eb`、pandas `4ec8`、numpy `d805`（今晚新审） | **20/20** 与期望一致（`d805` 用替代解 K-A5b 作主正对照，gold 按设计为 0） | 3/3 全过 | `d805` probe_ready；`f5eb`、`4ec8` 暂挂 |
| 第 6 轮 | v9（`r2e-mr-057`）/ v10 | orange3 `4014` | **8/8** 与期望一致（1200 s 放宽时限、单独记账） | 过 | probe_ready（带链路条件） |
| 第 7 轮 | v10（`r2e-mr-058`–`060`）/ v11 | numpy `d89b`（今晚新审） | **10/10** 与期望一致 | 过 | probe_ready |
| 第 8 轮 | v11（`r2e-mr-061`–`063`）/ v12 | aiohttp `4075`、pillow `2d01`（今晚新审） | 进行中 | 进行中 | — |

- 验收矩阵每题都含：noop、正对照（gold，或经独立核实的替代解）、已知错误候选、合理替代解。
  - gold 在修订后得 0、改用替代解的：`5e83` C-A、`e938` C1、`7545` K1、`d805` K-A5b，都已登记。
  - 计划与结果：`runs/r2e_lifecycle_20260929/formal_v{4..10}/{plan,status}.json`，完整评分日志在同目录 `remote/`。
- 所有修订草案都先经 Codex 复核通过再落正式材料（`codex_reviews/`）。正式修订单逐轮只追加，旧条目逐字保留；每轮只有该轮题的摄入产物变化，摄入与构建测试 73 项通过。
- 新机器上 48 题复验（缺省时限）：
  - noop 38/48 为 0、gold 37/48 为 1。没拿到分数的 10 题 noop 与 10 题 gold，全部是控制面保护超时（datalad 5、orange3 5）。
  - numpy `2f4a` gold 141/142，是已知的资源配方项。
  - 放宽时限（1200 s）复验那 10 题：全部 noop 0 / gold 1（`runs/r2e_lifecycle_20260929/budget_v5/`）。
  - 合计：48 题 noop 全为 0，gold 47/48 为 1。

## 3. 待您决定（按对后续的影响排序）

| # | 事项 | 建议 | 依据 |
| --- | --- | --- | --- |
| 1 | 静止屏障 root 执行 git（安全边界，A 线正式代码） | 按 Codex：这一阶段不再对 agent 仓库调用 git，改用可信工具的内容指纹；在正式 profile 下验证植入的配置不会执行，改完再用普通题和编译题各冒烟一次。只加 `-c core.fsmonitor=false`、`--no-ext-diff` 不够 | [review_probe_chain_20260929.md](codex_reviews/review_probe_chain_20260929.md) §1；[probe_chain_check.md](probe_chain_check.md) §3.4 |
| 2 | 探针派发的停止条件（D2 / D4） | 往返证据缺失或不一致时不采信分数；评分 fatal、清理结果不明时停止新派发；注入失败验收 | 同上 §2 |
| 3 | 大环境题的评分时限 | 由 A 线开放 `env_reset_timeout_seconds` 配置，给 R2E 大环境题显式预算，同时限制这类题的并发评分数；先在 GPU 机上实测这一步耗时再定数值。超时保持 `reward=None`，不计入模型失败 | 本批 README 03:25 行与更正行；datalad `19f5`、orange3 `4014` 的准入依赖这一项 |
| 4 | R2E 求解入口接入共用派发器（D1） | `run_matrix.py` 按题选 `r2e_solve_attempt.py`、评分带 `--image-overlays`（约 15–25 行，由共用入口的写入者改） | probe_chain_check §4 |
| 5 | 配方摘要契约（builder 与 consumer 口径不一致） | 定契约后才能落 orange3 `9b54` 的修订：它带 material 步骤后组合摘要变化，现批准集合只有旧摘要 | [review_revision_orange3.md](codex_reviews/review_revision_orange3.md) §一.3② |
| 6 | **修订单能不能对同一目标再加修订**（新增） | 复核给了四个选项：A 维持现状（默认）；B 链式追加，即同一目标多条修订按编号依次作用，后一条的"修改前摘要"等于前一条的"修改后摘要"（复核推荐）；C 新条目合并并取代旧条目；D 不改代码，新增一个"通过即跳过"的守卫测试文件（新写法，有解析脆弱点）。我倾向 B。选 A 的话，pandas `4ec8` 只能作问题定位（预登记 D1 型事后审计），coveragepy `f5eb` 也只剩"保持键集"一条路。B、C 是修订单格式与摄入代码的契约变更。Codex 正在核这四个选项 | 摄入代码现在拒绝同一题同一目标的第二条修订（`ingest_r2e_subset.py:416-417`）；`4ec8` 的 `test_1.py`、期望映射、conftest 都已有修订，新退化候选 D1 在修订后材料上得 1.0（`runs/r2e_lifecycle_20260929/inv/pandas_4ec8/ledger_D1rev_v9.jsonl`），行为对照证实它把 `lower` 插值算成 int64 `2`、应为 `2.5`；决定包在 `results/pandas__4ec8…/review.md` §7 |
| 7 | coveragepy `5dbb` 去重读法（P5） | 选 A（按 slug），理由是来源意图与改动成本；与读法无关的测试修订已落 | `results/coveragepy__5dbb…/revision_plan.md` §2 |
| 8 | coveragepy `f5eb` 的 C1（每文件 summary 多两键被判 0） | R-b / R-f / 维持原样三选一，主审未替您选；两种裁定下的恢复条件已写进准入卡。选 R-b 要先有第 6 项的机制 | `results/coveragepy__f5eb…/probe_card.md` |
| 8b | datalad `16c1` 的 R-b（P5，Codex 判定）：过滤器收到的参数里，没传的 `dataset` 可不可以以 `None` 出现 | 执行者建议选"可以"（R-b 与 R-c 同批，放宽 `sadfilter`）；选"不可以"就只落 R-c，合理解 C2 继续判 0。两份草案都已试跑，裁定后一次落，不需要第 6 项的机制。裁定前本题只作问题定位 | `results/datalad__16c1…/revision_plan.md` §7；[Codex 复核](codex_reviews/review_revision_datalad_16c1.md) §3 |
| 9 | pillow `4bc6`：非规范取值（`color=1` 存成字节 1）要不要也按 1-bit 语义反相（可选，不阻塞） | 复核推荐不要求：只登记为 S2，gold 可直接作正对照。要求的话 gold 不通过，改用替代解 A1 | `results/pillow__4bc6…/review.md` |
| 10 | numpy `2f4a` 资源配方 | 评分给 `/tmp` 6 GiB、内存 12 GiB（按题 `RH2_GRADER_*`） | README 与 probe_chain_check §4 D3 |
| 11 | `docs/.../s2_r2e/` 不在 git 跟踪（约 28 MB） | 决定是否提交；现在回退只能靠 `runs/r2e_lifecycle_20260929/backups/` | README 03:20 行 |

## 4. 还没做完的

- 第 8 轮 aiohttp `4075`、pillow `2d01` 的正式评分、devcheck 与准入卡。
- scrapy `a95a` 按 Codex 小改中；pillow `4bc6` 在 Codex 复核中。
- datalad `16c1` 等第 3 节第 8b 项裁定；两份草案已就绪。
- pandas `4ec8` 补做复核的第 2 步，会给出第 3 节第 6 项的选项与后果。
- pillow `2b06` 暂挂：需新公开读者、修正 TIFF 依据、另找替代正对照。orange3 `22e9` 的题面修订要新公开读者验收。orange3 `9b54` 等第 3 节第 5 项决定。
- 这次流程上的一处疏漏：pandas `4ec8` 在主审后直接进了修订，漏了独立复核，由准入卡撰写者按 v1 §7.3 拦下。已核对：名单上 18 题都有复核记录（`review.md`，16 题在 09-25 两批审查目录，`240d`、`d805` 在本批）。

## 5. 机器

- R2E 夜间机（vast）：磁盘用 105 GB、剩 671 GB；派生镜像 70 个 tag，镜像共约 85 GB。GPU 机要用同一批镜像时，按 probe_chain_check §4 D5 `docker save` / `load` 并核 tag→ID。
- 评分还在跑，您回来前我不暂停这台机器。如果今天不再用，暂停前我先把证据回传本地。
