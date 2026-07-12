# S2 implementation-notes（三节制）

范围：S2 各任务执行期的设计决策 / 偏离 / 权衡 / 开放问题。S2-1 的任务级规格见 `s2_1_data_ingestion_execution_plan.md`（已含 codex 轮次 4 审查修订与 O-1~O-4 定案）；本文只记执行中新产生的重要事项。

## 1. 设计决策与偏离

- **[S2-1 T0, 2026-07-12]** 无偏离。两项自检全 PASS（`s2_1_t0_selfcheck.md`）。唯一值得留痕的执行细节：重跑 `assert_repo_disjoint.py` 会原地重写 `meta/repo_disjoint_report.json`——本次重写结果与冻结版逐字节一致所以 digest 复验仍过；**后续任何人重跑该脚本后必须确认报告未漂移**（漂移即数据面变动信号，不是脚本问题）。codex 轮次 5 补充：该脚本的 `train_pool ∩ heldout` 检查是同义反复，survivor 级 D5 已在 T1a 变成真实机器断言（T0 报告已补注）。
- **[S2-1 T1, 2026-07-12] 镜像命名规则勘误：`_s_` 替换之外还必须小写化**。Docker 仓库名强制小写，`Project-MONAI__MONAI-*` 的正确镜像名是 `project-monai_s_monai-*`；data_freeze 的 image_manifest.md 只记录了 `_s_` 替换。fail-closed 映射校验首跑即拦截（"规则只作校验、清单为身份来源"的设计目的达成）。**待回写**：image_manifest.md 勘误 + 实验设计附录 B 的 P5 勘误清单再 +1。
- **[S2-1 T1, 2026-07-12] 任务身份 vs 环境身份的语义定案（T2 落实）**：216 题里发现两对同 `(repo, base_commit)` 不同 issue 的任务（moto-6469/6470、mypy-11824/11857，镜像 digest 相同）。`(repo, base_commit)` 是环境身份（物化/缓存可去重），不是任务身份；跨源去重的正确键 = `(repo, base_commit, F2P 集合)` 或标记人工复核，**禁止按 (repo, base_commit) 盲目去重**（会错杀这两对里各一题）。
- **[S2-1 T1, 2026-07-12] platform 字段的诚实口径**：216 镜像全部是单架构 v2 manifest（非 manifest list），架构信息在 config blob（未展开抓取，避免逐镜像计费 GET）；platform 按命名约定记 x86_64 + 抽样 GET 证实 manifest 形态。若 T4/T5 在 x86 实例上拉取失败再升级为逐镜像实证。

- **[S2-1 T1-followup, 2026-07-13] resolver v1 的续跑 fail-open 是真实缺陷**（codex 轮次 6 反例证明），v2 全面修复（严格校验/原子写/幂等 header/完成断言）。教训沉淀：**任何"断点续跑"工具的旧状态都必须先过 fail-closed 校验再信任**——与账本纪律同源。
- **[S2-1 T1-followup, 2026-07-13] 去重键再收严**：`(repo, base_commit, F2P 集合)` 也不作自动去重主键；正式方案 = source-qualified task_id + 题面/test_patch/F2P/P2P/gold patch 多 digest 构成 duplicate cluster，规则或人工判定，不自动删除（T2 落实，T1 报告有细节）。

- **[S2-1 T1-followup2, 2026-07-13] resolver v3：引用完整性 + 双文件事务**（codex 轮次 7）。教训沉淀两条：① "存在一个非空 ref 字符串"不是引用完整性——被引用物必须存在且逐字段一致才算数；② 双文件产物必须定义**提交记录**（本例 = manifest header 内嵌 evidence digest），否则两次原子写之间仍是撕裂窗口。状态机已抽成可单测模块（13 项无网络测试），这是"数据脚本必须可单测"纪律的第一个正式实例。
- **[S2-1 T1-followup2, 2026-07-13] legacy 升级通道的限额工程**：blob GET 不计 Docker Hub pull 限额——183 条 v2 条目全部零限额补验 config blob 哈希；manifest GET 限额窗口比预想恢复慢（1 天后余量仍 7），剩余 32 条继续等待窗口。

- **[S2-1 T1-followup3, 2026-07-13] 事务恢复必须回验提交记录**（codex 轮次 8）：恢复路径里"删掉多余行"不等于"恢复到已提交状态"——必须把已提交集合按写入同规则重序列化并回验 SHA，否则已提交行的非关键字段（如 fetched_at）可被静默篡改。配套：重复 id 显式拒绝、header 机器账目（count/evidence_line_count/enriched_count+reverify_count 标记）对账。v3.0→v3.1 的口径迁移用"新标记字段在场才启用严格对账"处理，避免把旧文件误判为篡改。

- **[S2-1 T1-followup4, 2026-07-13] 严格性必须绑定 schema 版本，不能挂在可选字段上**（codex 轮次 9）：v3.1 用"新字段在场才启用严格对账"处理迁移，结果等于给了"删字段即降级"的关闭开关——正确做法是显式升版（v4 全字段必填必验）+ 旧产物只走 digest 锁定的一次性显式迁移。教训与 gate 的 GATE_VERSION 升版纪律同源：**宽松路径必须是显式、可审计、一次性的，绝不能是隐式默认**。

- **[S2-1 T1-followup5, 2026-07-13] 无损往返是账本工具的基本性质**（codex 轮次 10）：writer 能写出、loader 却静默丢数据的状态 = 完整性漏洞。修复模式 = 写盘前守卫（拒绝写出非法状态）+ 加载全量消费断言（evidence 集合 == 文件行集合），"允许丢弃"只存在于显式迁移路径且必须计数。T1b 至此收满 216/216，store 定型（43 项单测），可供 T2 EnvValidationReport 与 S2-8 inspector 复用。

- **[S2-1 T1 关闭, 2026-07-13]** 用户确认关闭。最终交付：raw archive（230×11 列，冻结 revision，双向 strip_spec 覆盖 + survivor 级 D5 + 与冻结 meta 逐字节一致）+ 键控镜像清单 v4（216/216 digest + manifest/config 双哈希实证 + 平台 linux/amd64 + evidence 交叉核对）+ image_manifest_store（44 项单测，写盘对称守卫/事务提交记录/双 pin 迁移）。六轮 codex 审查（轮次 6~11）全部消化，存档 codex_reviews.md。

- **[S2-1 T2-a, 2026-07-13] 风险 F 关闭 + spec 表 vendor 决策**：官方 swebench 4.1.0 对 SWE-Gym 仓库零覆盖；SWE-Gym fork constants（commit pin 242429c1）覆盖 216/216，逐字节 vendor + provenance 旁证（不改内容、importlib 按路径消费、不在运行期拉 GitHub）。fork 末行把 spec 表重绑定为小写键——与 T1 镜像名小写化是同一坑的第二次出现，repo 身份的大小写归一化写入 T2 身份定案（内部原始大小写权威 + 小写投影用于 registry/spec 查表）。

- **[S2-1 T2-c, 2026-07-13] strip_spec 家族映射的"常量 + digest pin + 等价测试"三保险**：运行库不依赖 pyyaml（常量驱动），冻结 yaml 的 digest pin 让文件与常量脱节先红灯，语义等价测试（importorskip yaml）保证两者内容一致。单一事实源仍是冻结 yaml，常量是它的受锚定投影。
- **[S2-1 T2-c, 2026-07-13] 真实 216 题构造结果**：duplicate cluster 恰为 T1 实测的两簇且全部 distinct（0 suspected）——去重语义定案（任务身份≠环境身份）在真实数据上零误伤。消费期重验（verify_package_relations）作为可调用函数交付，T2-d/e 与未来 rollout 物化必须调用（登记义务的实现落点）。

## 2. 权衡取舍

- **[T1b] digest 解析用 registry HEAD 而非 `docker manifest inspect`**：HEAD 不计 Docker Hub pull 限额，匿名可安全跑 216 个（实跑零 429、约 4 分钟）。~~代价是拿不到 platform 详情~~ followup 已按计划完整口径补平台实证（manifest GET + config blob），GET 计 pull 限额 → 限额感知优雅停车 + 续跑（183/216 后停车，余 33 待窗口重置）。

## 3. 开放问题

- **[登记给 S2-8/inspect-rh2-s2]**（codex 轮次 5 证据工程建议）：① inspector 对互斥断言的复验必须**只读重算或临时输出**，不得原地重写自己正在检查的 evidence；② T0 自检收编为机器可重算项（记录 manifest 自身 digest、24 项通过数、脚本 digest、survivor 级 D5、报告前后 digest）；③ T2 起正式数据身份用规范化完整 repo identity（`owner/name`），不再用 basename。
