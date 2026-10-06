# DVC9395 R14 首次 noop 基础设施失败窄核（非作者，2026-10-03）

结论：原件支持 **failed_to_grade／reward=null**。trusted 测试恢复、固定补丁应用与自证已成功；其后 `control_surface_protect` 使用默认 300 秒分段预算超时，UID54322 候选预检、安装、pytest 尚未开始。这不是 noop 的行为失败或正式 reward0，也不能视为六候选矩阵完成。当前保护阶段超时是推进正式矩阵的实际阻断；具体保护子步骤或宿主争用尚未证实。

本审查者已见私有上下文与旧材料／wrapper／R5 actor／R14 适用范围结论，不是 fresh 公开读者。此次只读固定原件及三份冻结源码，用 stdlib 核 SHA／JSON／完整日志；未运行 CPU、SSH、Docker、pytest 或项目测试，未修改任何输入、共享代码或旧报告。支持请求中的线上诊断建议不是本报告已实施的行为。

## 输入与真实调用

支持输入实读 SHA256：`ae8b8edd86fcd9bfbd8fe65752f1a8a262448172f6b145e560999571a66a0300`；失败记录：`123f64e25adf8906494fa9a59c123df6f373009ac3cce611ba43c4ba3dd0fc26`。支持输入列明 37 文件（34 原件、3 冻结源码）SHA 全匹配；另核 tar、receipt、manifest 的固定 SHA。manifest 所列 34 原件 SHA/size 全匹配；tar 35 个普通成员与本机归档逐字节相同，额外一份为 manifest。作者失败摘要与 ledger／diagnostics／process 原件吻合，未将摘要当作独立证据。

release 为 `cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1`，固定 manifest `51b833975be2c3354be45b731552235a33070315f0039c8e6f54987de95f6ca8`。当前 archived wrapper v2 SHA `16a78e7019827e126d0788dcbb4bf13bd0ce913a9df842b79b9c110e75dc24c0`，调用该固定 release 的官方 `rh2/scripts/replay_grade.py`。completion 记录 release_files_checked=1220；同一 manifest 全成员 SHA 已在本审查者此前 6954/4166 R14 原件核查中独立读回，此处复用该固定范围，不把 completion 数字当作本轮又一次全成员核对。

prepare 作业 `dvc9395-r14-prepare-20261003-002355` 的 slot 调用 wrapper `--mode prepare`；官方 prepare 使用新 series `dvc9395_r14_v1` 的 prepared/private 目录、`--task-ids swe_gym_lite::iterative__dvc-9395` 和 R14 repo-root。prepare 输入 `86aebbab63ebbcdb45c5d87af75b57ad34fa8b9b476d1727c041eac61583ce70`、completion `27b2a5466151bd252ef5b930f9a1504dd5522f288f8b40d7d597a5268f3e771b`、summary `2fd261a153a36bb21a1b23d571d1f21a1b7c55a1545a289141ffa20dbd6f31fb` 及公开 files/manifest/host SHA 链均匹配。prepare process.log JSON 等于实际 summary，process rc0、slot rc0。

run 作业 `dvc9395-r14-noop-20261003-002355` 输入 `f1ce04dd61efeb4dea0e9582d89a9cc753887fbc25b6cabb7b3fc3f2b4f54daf`，固定上述同题 prepare completion／summary。invocation 与 completion 的命令、输入、release/runner、runtime 路径、环境一致；runtime 为 `runtime_cpu_v2/rh2/.venv/bin/python`，PYTHONPATH 指向固定 R14 source。命令选 `--candidate noop --repeat 1`，candidate-stage 900s、grading-deadline 3600s、cleanup 120s、image-pull 1800s。run process／slot rc0 表示失败报告正常运输，不表示评分成功。

原 noop FrozenPatch.entries、projection.included_entry_paths 都为空，classification projectable／reason_codes 空；stage/head、baseline、FrozenPatch materialized_head 均为 `c75a5583b3840ba90a8e800a0f42c1cb120916db`。baseline canonical SHA `0c75caa0ac9790c739e0250f37125f342241d19d57bb430e6a6c7fa009acf0ec` 与 FrozenPatch 锚、FrozenPatch canonical SHA 与 projection 均独立重算匹配。git sanitize rc0、HEAD before/after 不变、violations 空。

实际 grader ref/ID 为 `sha256:c093861f62b8071b3c1e5b3142abd5843888421364e69dd728cb80856f621b60`，baseline/FrozenPatch 和 host 固定 installation 一致；ledger expected image manifest=null、identity 为 local_build:<ID>，没有将来源 manifest 错配给该派生镜像。其余候选 patch 虽随归档保存，本次没有执行，也没有据此评价候选行为。

## 已完成、超时和未开始的步骤

完整 eval.log 为 238 行。168/172 行从 immutable base 恢复 `tests/func/test_repro_multistage.py` 和 `tests/func/test_run_cache.py`；177/182 行核其原字节 SHA 分别为 `ca738a7a94b991881a48abdb02aa1d27565f087e5742511d1fbbd752afde99e1`／`0d9bfa7a96c4e29e178c89b96357ec1adae59bfa27027173f07b234b08504960`。随后 UID0 固定离线 wheel 字节检查返回 OK，两份 fixed test patch cleanly applied（仅一行 EOF 空白 warning）。226–238 行真实自证：APPLY_RC=0、RESTORED=2、EXPECTED/TEST_FILES=2、ABSENT=0、IRREGULAR 空、SETUP_OK=1。

manager 并非只信 setup 输出标记：3416–3434 行读 root 自证文件、核返回与覆盖面后才进入保护步骤；diagnostics.trusted_setup 已保存这些事实。故已完成恢复／应用／自证的结论有日志和实际消费记录支持。两测试文件完整 after-apply 字节未另存，本报告不补造其完整源码 SHA 验收。

原始 ledger report 为：failure_category=infra_failure、infra_failure_detail=`grading_control_surface_protect_timeout_after_300s`、outcome=failed_to_grade、reward=null，F2P/P2P 数值字段全 null；diagnostics.grading_revision.state=not_evaluated、各分区 result=null、verdict=null。没有 pytest collection/PASSED/FAILED 或 install/test RC 标记；candidate_prerequisite、candidate install、test、control_surface 均为 null。

源码顺序明确：成功 trusted setup／attest → 保护脚本 → 核保护返回／自证 → 候选 UID54322 prerequisite → 观测／安装／测试。超时发生在保护 exec 尚未返回的位置，尚未创建候选 prerequisite 结果。这既由空字段与缺少标记证明，也符合冻结执行路径。UID0 成功检查不能冒充 UID54322 已验；不存在可以打分的候选测试段。

`grader_trusted_setup=301.435441s` 是 manager 从 setup_started 起计、包含 trusted setup、attest、保护及失败收尾的聚合阶段时间，不等于 chown 单步耗时；实际 timeout 细节是保护 exec 300 秒。`test=null`，不是某个测试耗时超限。

## 原因边界与现有预算接线

三份实际读取的冻结 source SHA：

| 文件（固定 release repo 内） | SHA256 | 精确位置 |
| --- | --- | --- |
| `rh2/src/repoharness2/grading/manager.py` | `1783533e1e3b66a57fcaa5a599a1da4f8e4e886318e24f040c6df91f294c1c1e` | GradingEnvSpec 默认647；timeout归因2809–2844；保护3436–3447；候选预检3453以后 |
| `rh2/src/repoharness2/adapters/slime/sandbox_profile.py` | `313bfd7691c5dca775aa0e9992f13561e20936f062ddfa3d269892b6bf4895ee` | 保护脚本1634–1721 |
| `rh2/src/repoharness2/adapters/slime/prepared_task_face.py` | `22bf13dd0fc6c7b7d8ab7155c0afcef547b71acf5ff0d919c7a6c57160f7d012` | DVC环境709–714；邻近Dask接线715–722；构造776–777 |

`_exec_bash_checked` 通过 asyncio.wait_for 做分段限时。若剩余 grading deadline 更短，源码输出另一种 deadline-exhausted 归因；本次输出明确为 phase timeout_after_300s。因此已证 300 秒的保护阶段分段上限被触发，不能改写成 3600 秒评分总期限到期。

保护脚本先递归 chown `/testbed`，再递归 chown candidate writable prefix `/opt/miniconda3/envs/testbed`，然后把 official tests 设 root:root/0644、各祖先目录设 root:root/1777，核 stat／缺失／不规则文件／覆盖数，最后才输出 PROTECT_OK。代码存在这些可能昂贵的 ownership 操作；但本次保护 exec 没有返回，manager 只保留 setup_log，control_surface=null，没有保护 stdout／stderr 或子步时序。不能从“没有 PREFIX_DONE marker”推断第一步 chown 已卡住，因为超时前的 stdout 根本没有交付留存。也没有宿主 CPU/I/O、overlay copy-up、inode 数或争用测量。递归 ownership 成本是支持方可检验的假设，不是已证根因。

可用的既有**题目范围**参数是 `GradingEnvSpec.env_reset_timeout_seconds`，默认300；保护 exec 用该参数。prepared face 将 `environment` 的 kwargs 传给每题 GradingEnvSpec；Dask7656 已从其注册 install 身份读取该值。DVC 分支当前只设置 local-build 镜像身份，实际 host DVC installation 也没有该预算字段，因此没有已存在的 DVC9395 budget 配置可直接由本次输入开启。只提高外层 grading deadline 或 candidate-stage 参数不会改变这里的 300 秒上限。

这份现有 spec 参数还用于 trusted setup、git/environment reset、候选预检、前后观测等；它不是只给 chown 的专用参数。支持方若采用现有接线，应提供仅绑定该固定 task/revision 的版本化预算／consumer 身份，保留默认其它题行为、固定镜像和全部保护判据；需要新 release/material/prepare 链来表示变更，不热改冻结 R14。邻近 Dask 只是接线例子，不能不经 schema／身份约束照搬。具体安全预算值与是否有更窄部署修正尚无测量，本报告不给“提高到某值即可通过”的承诺，也未实施任何修改。

## 峰值、清理与阻断范围

原始 ledger／diagnostics 保留 `peak_memory_mb=509.734`、peak_unavailable=false；resource_facts 为 container_oom_killed=false、oom_kill_events=0、pids_events_max=0。这支持留存计数中没有 OOM kill／PID 上限事件；不能由此证明完全没有内存压力、宿主争用，或全部实际资源设置已验。policy 记录 2CPU／4GiB／PID512／UID54322／deny_all、64MiB shm／1GiB tmpfs及唯一 candidate writable prefix；没有另存实际 HostConfig，不把 policy 当作完整配置验收。

内层 ledger.cleanup removed=true、rm:ok、detail 空；process manager_close created_total=removed_total=1，containers_open/supply_open/cleanup_failures 空，halted/aborted null、final_status rc0。外层 cleanup_readback 按本次 run_id 标签查询 containers/networks 均 rc0、stdout/stderr 空、ids=[]，receipt 中副本一致。没有当前标签残留的归档时间点证据完整；本次未进行新在线查询。

失败记录的 reward null、未启动候选段、OOM/峰值和清理结论与独立读回一致，无新增报告矛盾。实际阻断是“保护阶段不能在原预算内完成”；保护是否已经完成部分权限修改不明，容器已清理，不能将中间态当成成功保护。支持完成版本化修复／预算绑定后，仍需新的真实正式控制原件验证；现有失败历史须保留。

本次不重审测试语义、不评价未运行候选、不宣称 9395 正式矩阵完成；旧私有诊断 reward 或 R5 公开 actor 17 passed 不能补成此次正式 reward0。也不授予模型 probe、训练 actor 接入或环境／训练资格。

## 最少原件指针与实读 SHA

原件根为请求指定的 `formal_evidence/formal9395_r14_noop_002355_v1/`；以下 job 文件均位于 `formal/jobs/dvc9395-r14-noop-20261003-002355/`。完整 eval.log 结尾自证及 diagnostics 空字段、ledger report 是阶段／结论依据，process 与外层 readback 是退出／清理依据。

| 文件 | 实读 SHA256 |
| --- | --- |
| `tar` | `e2d3a1cfb6cc30ba7f4dd24c93cf1cf9745521c2a8dd101fea017a013d075df9` |
| `receipt` | `69dc47c5be41b237a47d3e9474f743d56f2de1b8b190826c3848e8c8ec33a094` |
| `manifest` | `37d596be112697382ede0dfd717a466d8a245eb3f5428c407ff12366c2804579` |
| `eval_logs/evallog_replay-dvc9395-r14-noop-_0de0e7b2.eval.log` | `fc4f57fb953419644b1396b2cf4fc2cc9aa9dc8b642394240a9e92647bd44aca` |
| `eval_logs/evallog_replay-dvc9395-r14-noop-_0de0e7b2.diagnostics.json` | `f69b8cd090959bd8fae559ad120da87bf231c1c34dcf84ab01a7104b4a0bfa42` |
| `ledger.jsonl` | `e0ac84979c9f1926c30f69d4270797e270597fa889c4e678fe5e7c14a81c4b7d` |
| `invocation.json` | `123dea9ce9ab3d09e7926db5813ed920b770dd25a0cf655362d0a7d5e7049286` |
| `completion.json` | `3cebdd3a720d6dc1a4dfa355058d8c1148c170d4b0cf9d06855713aad7e30c29` |
| `process.log` | `da8b259603f92e4d052a87330ab8197add399697c4ee3e4fc621447734caca17` |
| `cleanup_readback.json` | `bad3283a619991cc3cabedd4519173f85c9688e2413b174ac48831f129a9146c` |
| `prepare invocation` | `a403ce8d95e0b845e9114aa7b6527768e8ed8db8f1925d887383bde49b3aabf4` |
| `prepare process` | `d9e779cacbc91f13f9198425d697024e6668e78d7ebb030ad2ca8a4076da03ce` |
| `prepared manifest` | `90ddcddd49d2c64e145d1f4e93efc062102839c16680843bbe0da017be9ac6ce` |
| `private host` | `21198a8ee0f8b99e693b93110834b00d4445f5de4755a933c4a7708da51ab34e` |
