# DVC 4166／9395：R5 公开 actor 运行原件窄核（2026-10-03）

结论：本轮未发现新增阻断。9395 v1-001 实际执行 17 个公开测试并全部通过；4166 v2-001 实际执行 29 个公开测试并全部通过。两次作业的四条公开核查命令、首请求、prepared 身份、镜像、profile 与清理记录相互一致。4166 v1-001 的失败保留为自有 helper 的启动前 clean guard 拒绝原镜像元数据，未启动 Claude Code 或公开核查命令，不记作模型或题目失败。

本核查者已读过本题私有材料、私有 CPU 诊断及前轮结论，不是 fresh 公开读者；没有重核任务私测或 6954。本轮只用 stdlib 离线读回和 SHA／轨迹核对，没有运行入口、SSH、Docker 或 pytest，没有修改材料、入口或共享文件，也没有提交 git。

## 固定范围与复用

固定请求：`reviews/actor4166_9395_runtime_review_request_20261003.json`，实际 SHA256 `2a3eea0b29dd3300fd98683f363b0634a74f1dd921e5dc73097813984687a6b5`。86／86 份清单原件存在且实际 SHA256 与固定请求完全一致。结果 JSON 只作导航；以下通过数及退出、首请求、身份与清理从归档原件自行重建。

helper 继承链、公开基线 29／17 实例静态来源及 v2 仅对 4166 已知 `setup.py` metadata 做精确 porcelain＋完整 diff SHA 例外，复用 `reviews/non_author_actor6954_and_metadata_delta_review_20261003.md`，实际 SHA256 `ace9f7daf594669ab4d1f22f21eb2f7c083c9b0a08d9d6322460b2843d366f42`；该报告引用此前 helper 静态核查。本轮不重新审入口实现。

原件根目录为 `runs/category2_repair_20260929/repository_work/swe_dvc/public_actor_evidence/`。下文 9395、4166 v2、4166 v1 分别指 `public9395_r5_actor001_v1/`、`public4166_r5_actor_v2_001_v1/`、`public4166_r5_actor001_failure_v1/`。各根下 `attempts/<完整 job ID>/` 简称 attempt 目录。

## 实际执行与逐命令结果

| 原件 job | 时间（UTC，2026-10-02） | slot／harness 退出 | 公开测试实读 | 本轮判定 |
|---|---|---|---|---|
| `dvc9395-public-actor-20261003-v1-001` | 20:53:11–20:54:58 | 0／0，returned | 17 passed in 24.69s | 公开环境运行事实支持通过 |
| `dvc4166-public-actor-20261003-v2-001` | 20:56:04–20:57:19 | 0／0，returned | 29 passed, 2 warnings in 1.91s | 公开环境运行事实支持通过 |
| `dvc4166-public-actor-20261003-v1-001` | 20:51:31–20:51:33 | 1／未启动 | 未执行 | 自有启动前 guard 失败 |

| 命令 ID | 9395 v1 实际事实／rc | 4166 v2 实际事实／rc |
|---|---|---|
| `identity` | UID 54321；testbed Python；`dvc` 来自 `/testbed/dvc/__init__.py`；`pygit2==1.14.1`／0 | 同一 UID、解释器与源码目录；`pathspec==0.8.1`、`networkx==2.3+rh2.1`／0 |
| `activation_permissions` | `RH2_BASHENV_WRITE=DENIED`／0 | `RH2_BASHENV_WRITE=DENIED`／0 |
| `public_tests` | `PYTHONPATH=/testbed python -m pytest -q tests/func/test_repro_multistage.py`／0 | `PYTHONPATH=/testbed python -m pytest -q tests/unit/test_ignore.py tests/func/test_ignore.py`／0 |
| `dependency_cli` | `python -m pip check && PYTHONPATH=/testbed python -m dvc repro --help`；`No broken requirements found.`、真实 usage／0 | `python -m pip check && PYTHONPATH=/testbed python -m dvc --help`；同样依赖核查与真实 usage／0 |

实读 `captures/public_tests.out`：9395 17 个点、4166 29 个点均达 `[100%]`，完整结尾摘要与分母 17／29 相符，没有 failed、skipped、xfailed、xpassed、error 或 deselected 汇总。9395 的 benchmark 提示及 4166 的两条 NetworkX／NumPy 弃用警告不构成 skip。公开基线实例数来源复用前轮静态核查：9395 为 13 个普通实例＋两个 bool 参数族各 2 个；4166 为 unit 15＋func 14。这里的“缺席 0”表示预期数量、完整文件选择及实际计数一致；`-q` 没有逐节点完整 ID，不能把本归档表述成另一次独立 collect-only／逐 ID 验收。

两条轨迹均完整解析，无坏 JSON 行；各有四个 Bash tool_use 和四个 tool_result，tool_use ID 一一对应，脚本输入与归档 `stub_script.json`、stub 日志一致，原命令逐字包含于 timeout 包装。四个结果的 `RH2DC_END ... rc=0` 与 captures、`commands_result` 一致；后续 requests 001–004 收到对应实际 tool_result。每次五个 message_start 与五个 stub 请求一致，最后为 `result/subtype=success/is_error=false`；Claude Code 版本 2.1.205。harness 轨迹长度与完整日志记录相符，harness／slot stderr 均空。

完整 capture 字节数分别为 9395：147／25／391／2347；4166：173／25／1623／2852（按上述四命令顺序），均低于 200000 字节截断上限且等于 recorded output_bytes。tool_result 只带各 capture 最后 1500 字节，故通过数取完整 capture；没有把轨迹中的截尾误当完整 pytest 输出。

## 首请求、prepared 与身份

两题首个 `stub/requests/messages_000.json` 的 user 文本块包含完整 prepared prompt＋两个换行＋完整公开开发说明，逐字匹配，包括原题 CRLF；public.problem_statement 的实际 SHA 与交付记录一致。9395 题面 SHA256 `60357b7feee97830da0f9866e8b7cb69c17272f8fa535cb4e2de2eb96e5c3b56`；4166 为 `80e4612c874ac1458641a93ba3f6c38889004fb352ef4872ef527f905b2ae54b`。开发说明只说明源码路径、解释器、已安装依赖、公开测试及 CLI 入口，没有私有判据、错解／正解、reward、补丁提示或新增私有测试入口。四条命令也只做这些公开开发核查。

prepared replay_summary→manifest→prompts／rollout_task_views 及 host_grading_artifact 的文件 SHA 链相符；task_count、各 jsonl count 均 1，task ID 和 public_bundle 与配置对应。私有 host grading 仅用于 SHA 链核对，轨迹未运行私有 grading。4166 v1 与 v2 的原 input、原 helper、commands、开发说明、全部 prepared 及 host-grading 文件逐字未变；slot v2 明确选用 `actor_check_v2.py --input input_v2.json`，没有误跑留下的 v1 文件。

两次配置的冻结 release 相同：`cat2-cpu-r2e078079-swe7-git-20261003-v1`，release manifest pin `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`，七份冻结代码 pin 相同且与前轮已核 R5 pin 对齐。本轮重新 SHA 核对归档 helper、输入、commands、开发说明及 prepared，没有再次读取或执行冻结实现；远端实际代码校验的 stdout 没有另存，运行符合已核 helper 的 code-pin 前置校验控制流。

| 题目 | 实际镜像 ID（sha256） | initial／sanitize before-after／prelaunch HEAD |
|---|---|---|
| 9395 | `c093861f62b8071b3c1e5b3142abd5843888421364e69dd728cb80856f621b60` | `c75a5583b3840ba90a8e800a0f42c1cb120916db`，初检 clean |
| 4166 v1／v2 | `28ed5ef69d46c326ec183f8719e426611ca848046156fa98f9f6c7f35b46ebeb` | `520e01f11305aba1994df354adef86e6d90180de`，初检 ` M setup.py\n` |

4166 v2 原件的 `initial_metadata_diff.text` 整段重新 SHA 为 `8bd072b6e35dd358d920432c24b35048d4e51a9d0bc78972ceeb18e302b8dfbf`，与 input_v2 的 `expected_initial_diff_sha256`、前轮 metadata pin 及 source_worktree_before.txt 已核 diff 完全一致；仅 `setup.py` 中 `moto==1.3.14.dev464` 改为 `moto==1.3.14`，标记 candidate_change=false。实际 porcelain 也精确为 ` M setup.py\n`。因此本次 v2 通过对应被窄核的已知原镜像 metadata，不是未知 dirty 树。source 原件／pin 对齐复用前轮报告，本轮不扩审其它 dirty 情形。

公开基线文件 SHA pin：4166 unit `67cff53e0626e13934a1b74461d5d2648c8e56859fc1aadd9fc067282b6c48ed`、func `0b11d0098c2e97b3cc1f454cba2fbccdbb3e144545b45854aff75cf0be8f9602`；9395 multistage `ca738a7a94b991881a48abdb02aa1d27565f087e5742511d1fbbd752afde99e1`、run_cache `0d9bfa7a96c4e29e178c89b96357ec1adae59bfa27027173f07b234b08504960`（9395 命令只执行 multistage）。成功作业经已核 helper 的基线存在／SHA guard、完整公开文件命令及预期实例数支持未混新私有测试；此 guard 的 stdout 没有单独归档，不能声称本轮取得了运行容器内完整测试文件快照。

## Profile、清理与旧失败保留

两次成功作业 profile_digest 均 `a0d183d13a4a099cd0bd62d9e19fca7019428f7d08f5b69522a3ead4b565c68f`。prelaunch 原件 inspect 与 cgroup 读回均为 2 CPU（200000／100000）、4 GiB 内存、swap 0、PID 512；`/tmp` tmpfs 1 GiB、agent home tmpfs 256 MiB。UID／GID 54321、有效权限零、no-new-privileges、非 privileged、binds／mounts 空；仅 relay 可连，外部 DNS／直接 upstream／forbidden 目标被拒，activation 文件 root 0:644、agent 可读不可写。prelaunch／activation violations 空。配置写入 8 GiB writable-layer quota，但 inspect storage_opt={}，不能据此认定磁盘配额已强制生效。

两次初检 image probe 删除 rc=0；最终 container_rm=0、stub_rc=0，network_failures／relay_failures 空。按 run label 查询的 labeled_containers_left、labeled_networks_left、residual_after_force 均空。post_run 原件显示 `.harness`、`/tmp/.run.sh`、`/tmp/.run.done` absent，agent 进程 0。9395 git status 行数 0；4166 为 1，仅记录行数，不能从该记录证明结束时那一行及 diff 仍逐字等于初检 metadata。newer_files 分别 335／219，示例含正常 pycache；没有声称工作区从未写入、所有文件无变化或无主机全局残留。

4166 v1 的独立失败原件：slot stderr 在冻结 devcheck.py:108 `await self.image_facts()` → actor_check.py:101 抛 `RuntimeError("actor base worktree is not clean")`；stages／timings／checks 均空，没有 harness_exit_code／commands_result，attempt 目录仅 attempt.json，没有轨迹、stub 请求或 captures。结合已核入口顺序，支持 CC／模型请求／四条公开命令均未启动。该 job 确实启动了 image-facts 探针；其原 HostConfig 是同一 2 CPU／4 GiB／PID512 原 profile、network none、无 bind，probe_cleanup_rc=0，三组 run-label 残留列表均空。没有将未启动组件写成执行失败或补造四命令退出码。失败归档及导航中历史“new runtime pending”保留原样，以本次独立 v2 原件判定当前事实。

## 证据 SHA256 与最少回读指针

以下均为本次实际读取字节的 SHA256；路径基于上文对应根，`attempt/` 表示完整 job 的 attempt 目录。其余 86 份逐文件 SHA 由固定请求唯一定位且已全部重新匹配。

| 原件相对路径 | 9395 v1 SHA256 | 4166 v2 SHA256 |
|---|---|---|
| 实际 input | `da833fcf54eb27c870f797fae067d61b1541ae8c6b62e36fff4270f1d3151c41` | `894bb5e2af530d979552d0244386cff5357df69d742515338cd9c81e15309be9` |
| 实际 helper | `91c8bb818c10f6492be45f20ada71f252fcb6884aed5c12539c109cb4fe689d0` | `f513232d19dae5c28e3a0ae8600cc9ad7cbab71aa0a7582f5abd9ceccaf7bd8d` |
| commands.json | `49c50eedd24522d54343e8c39b841745ba211755506c005ca6b2ea48551e3508` | `caeec2a908752f3b09bdd3cdc7d025ba3e185dae5f16e58203346fd9cd50f7ec` |
| public_development.md | `7323939989fe68455a468c41cecb83884eb2c9dd863cc8a98b6873c4810a8456` | `ed6994bdbefb3c3eb38ba069b7c5faebc8188f4a3d9a112f3db8a4361768826d` |
| prepared/replay_summary.json | `fca6e8f1ffb8237ad4f06ee29a394fc69442830515d9af669358a8c18367d701` | `543f65aedba1c5237680718df5e1635b12ecb171af24c819a2fe954c48c75510` |
| prepared/prepared_manifest.json | `4f9dbfc34084f1722544bf155b5f10ccabf565adfef06a0ec3e92ce1a9739f5f` | `264d871fa6b412ecf404dcb34692da5dd9d4968023f9aefc63729902c2c92f81` |
| attempt/attempt.json | `324b0ae2c3c32d213639e6290015bcfde7574d06156a9365aa11e1a330a5e453` | `8d7def502848dfe686097bceadd7c81c018a6f4f48fb5716ad6c10338215ff7d` |
| attempt/stub/requests/messages_000.json | `46adeb7fb517230bf6b811348079c7e137eec621dbee8dcee0480daa331b7d47` | `a72378988ef12cd7335e1610b2f5305a498588ec01c8004c7aca09b6953fd3ef` |
| attempt/harness/trajectory.jsonl | `7d4bda97feab24977e42127dc5500069b7debf81fc933fc0b126088bda1fa81a` | `018c6f6776cfd3618545c9c8750b131169d92180b0ab8f0dbf5de82e9d1a33dc` |
| attempt/captures/public_tests.out | `825ec61de795e419e538f64318d80aea7113ee80f3c1d3b97e5bb75da9d65c8d` | `6983f8a8d40fb3f74a45ae322a18daf487628fd6023fac773f0755dec5326072` |
| attempt/prelaunch.json | `84483c2218f14a613d97e9279fe4e0803cd482ca745b6b0b1c0f513e41911a2c` | `826c0cdffbbf226a53877b7240f316cd7736ac1ffea0756b8744fb6551535390` |
| attempt/post_run_facts_root.txt | `902fbf53087834a797d7abcfdb6f493d969c0ff0aace753de575fa851e5d22e7` | `2ee7b1b5a0447ea142e14542e3cd6f07360308d72256b40458923747fa32e9f7` |
| slot_job/status.json | `b252b1b5ec6ea1e098422b3a465e56d1f84224b37e3c40499ce51d4184bb504a` | `721a4c6f19bcdef5cd9ad08ca10eecccef97bad1395cd8bb773fd7efe43f38b5` |

| 其它证据／导航 | 实际 SHA256 |
|---|---|
| `4166 v1 attempt/attempt.json` | `34edf2871d1f34eb3786af6c7d2ea30ea56c5634a77b3c904cd6c495ce2cd84b` |
| `4166 v1 slot_job/stderr.log` | `49989896003075e7e0538d3166f096b8f8aa46bb5adcdc9344583b915eae8c9b` |
| `4166 v1 slot_job/status.json` | `abf3b1f7fc2f2f7e92509c16e32557a4bb2ab1f966cba3cfdba90905daf7ce01` |
| `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_dvc/tasks/iterative__dvc-9395/public_actor_r5_v1.json` | `2fcdd566c030d6355da155d4148ef660cd98cce72b0659bbec12aeff7c5dbfb7` |
| `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_dvc/tasks/iterative__dvc-4166/public_actor_r5_v2.json` | `2bae2139cf7a39fb5bcdd4b9d54edabff3274513795655549acea7051a60efda` |
| `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_dvc/tasks/iterative__dvc-4166/public_actor_r5_v1_failure.json` | `76ddd710d89b825dad4c410385324e24a582e149fec19b8a56dc31975f839603` |

## 用途及未验证范围

本报告只支持上述两个 R5 公开环境 actor 交付／执行核查及材料下一步：真实 Claude Code 在固定 stub 响应下执行公开命令，原件所示测试通过及清理。没有新增阻断 finding；既有 `-q` parser 导致 pytest:null 不影响本次人工原件重建，但 `actor_checks_passed` 自身不能代替 passed／skip／分母验收。

本轮未重新运行或扩审公开节点、不重核私测、候选对照、6954、冻结实现继承、metadata 源 pin、发布部署、正式 grader／reward 或真实模型解题。仅哈希检查 host-grading 字节链，不授予正式 RH2 reward、正式评分／actor 或环境／训练资格、模型探针通过或探针准入。CC 平台 tarball 字节及结果导航列出的 tar.gz 整包不在本次 86 原件范围内，未再次验证；可见运行版本及 tarball 记录不能代替其独立字节核对。
