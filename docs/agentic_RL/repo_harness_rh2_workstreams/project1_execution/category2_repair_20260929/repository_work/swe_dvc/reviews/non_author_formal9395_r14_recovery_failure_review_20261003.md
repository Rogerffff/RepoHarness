# DVC9395 R14 第二次正式失败差异窄核（非作者）

2026-10-03。新作业 `dvc9395-r14-recovery-noop-20261003-021424`，新 series `dvc9395_r14_recovery_v1`。

**结论：新独立 prepare 成功后，noop 正式运行仍为 infra_failure／failed_to_grade／reward=null，具体记录是 `grading_control_surface_protect_timeout_after_300s`。** trusted 恢复、固定测试补丁应用与自证已成功；UID54322 候选预检、安装及测试均未开始。保护-only 支持的一次 242.417s 成功没有恢复正式路径，不能将本次 noop 计为 reward0，亦不能称六控制完成。实际阻断仍是保护阶段在原 300s 分段上限内未完成；具体子步或主机原因未证实。

新失败记录、v2 支持输入的阶段分级、材料等价性、两层清理和峰值与独立读回一致，未发现新的误分级或候选／prepared 重绑。已停发的五项控制应继续保留“未运行”状态；在具体版本化修正或能区分正式／隔离路径的新阶段证据前，不支持无变化循环重试。

本核查者此前已见私有材料和运行上下文，不是 fresh 公开读者。仅用 stdlib 离线读原件、SHA、tar、JSON、日志；不访问 CPU／SSH／Docker，不运行测试，不改任何输入、共享代码、作者卡、结果或旧报告。旧源码、材料、wrapper 与第一次失败的原因边界复用[既有窄核](non_author_formal9395_r14_failure_review_20261003.md)（SHA `174d5908963aec91039cbc7d708f4a168c8bd630a5bbc6411d883ac46df2b351`），不机械重审全仓。

## 1. 固定输入与归档完整性

v2 输入所列 **43 个 pins 全部实读匹配**，其中包含 34 份新原件和旧失败／已确认支持／导航／冻结源码。另核 tar、receipt、manifest 的固定 SHA；manifest 的 34 个文件共 266,903 B，逐份 SHA 和 size 相符。tar 共 35 个 regular 成员，路径集合恰为 34 原件加 manifest；每个成员与本机原件字节相同，没有其它／特殊成员。新 tar 55,087 B 与 receipt 相符。

这不是直接采信作者 `all_manifest_files_verified=true`；本轮重新核了上述集合。三份旧冻结源码 SHA 仍匹配原报告中的版本，未再次实施源码检查或重算 1,220 release 成员；此前同 R14 release 的成员核查范围复用，completion 的 `release_files_checked=1220` 不写成本轮新做全 release 审计。

## 2. 新 prepare 与运行绑定

prepare 作业为 `dvc9395-r14-recovery-prepare-20261003-021424-a4`，经 slot0 实际 `--mode prepare` 调用封存 wrapper v2（SHA `16a78e7019827e126d0788dcbb4bf13bd0ce913a9df842b79b9c110e75dc24c0`），再调用 R14 官方 `replay_grade.py prepare`。series 的 prepared/private 输出目录均独立于旧 `dvc9395_r14_v1`；prepared_at 为 `2026-10-03T02:23:47.902646Z`。prepare process JSON 等于新 summary，process rc0／slot returncode0，stderr 空。

独立核以下 SHA 链均一致：prepare_input → prepare invocation/completion → process/summary → prepared_manifest → prompts／rollout_task_views／private host。run_input 精确钉住这个新 prepare_job_id、completion 文件 SHA 与 summary SHA；新 run invocation／completion 的 input、command、release、runtime、environment 对应，process 与 ledger SHA 匹配。run completion 的 02:24:22–02:31:08 时间和 slot 状态对应；两作业分别实际完成，没有以旧 completion 冒充新 prepare。

release 仍为 `cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1`，manifest `51b833975be2c3354be45b731552235a33070315f0039c8e6f54987de95f6ca8`；runtime_cpu_v2，PYTHONPATH 指固定 R14 source。noop 参数为 repeat1、candidate-stage900s、grading-deadline3600s、cleanup120s、image-pull1800s。run transport／wrapper／slot rc0 是正常产出失败报告，不是正式评分通过。

新原 noop FrozenPatch.entries、projection.included_entry_paths 为空，classification projectable／无原因，excluded_pathset_changed=false；stage、baseline、FP head 皆为 `c75a5583b3840ba90a8e800a0f42c1cb120916db`。新 FP 的 rollout_execution_id／physical_attempt_id 是 recovery 作业；独立重算 canonical SHA `3ee08e830ca18bbe288085e9bcfb8789939237dcb3ace5129fad18cf05521f0d` 与新 projection 和 ledger 锚相同。旧 FP SHA 是 `ee2b0b83bae3efeae49bfadcc77c20f4e8e64ffb456cc9a933c60238f687eb77`；差异包括尝试身份，**没有重绑旧 FP**。相同的 baseline canonical SHA `0c75caa0ac9790c739e0250f37125f342241d19d57bb430e6a6c7fa009acf0ec` 表示相同固定基线，并不使两次执行变成一次。

## 3. 新旧实际差异与不变项

直接比较两次正式原件，以下三文件逐字节相同：prompts.jsonl、rollout_task_views.jsonl、private host_grading_views.jsonl；五份非 noop candidate patch 也逐字节相同。新 prepare manifest 的时间及 summary 的目录／manifest SHA 改变，旧／新 job 输出与 FP 身份不同。作者导航所称 R5 等价性沿用已有公开适用范围核查；本轮只独立核新／旧 R14 的实际字节，不把整 R5/R14 prompt JSON 相同当作新事实。

| 项目 | 两次正式原件 |
| --- | --- |
| grading materials identity | 同为 `9d456666b845fd90146499033601805ce2ecdc3d88e26202f8b9855cf287f68a` |
| scripts digest | 同为 `ec5f61cf288b78aaafd469b40013bcd571e93e1ab5db7c32c8852b6a83f035f3` |
| image_id_actual／image_ref | 同为 `sha256:c093861f62b8071b3c1e5b3142abd5843888421364e69dd728cb80856f621b60` |
| expected image manifest | 两次均 null，identity 为对应 local_build，不错绑来源 manifest |
| policy 与 budgets | JSON 对象精确相同；2CPU／4GiB／PID512／UID54322／deny_all，未扩保护或资源 |
| 保护阶段归因／正式 reward | 两次均 protect300 timeout／null |
| grader_start_and_verify | 旧 44.802543s；新 46.729859s |
| grader_trusted_setup 聚合 | 旧 301.435441s；新 301.287596s |
| 实际 peak_memory_mb | 旧 509.734；新 665.844，均 available |
| OOM kill／PID 上限事件 | 两次均 container_oom_killed=false／oom_kill_events=0／pids_events_max=0 |

policy 是调用记录；新归档没有正式容器实际 HostConfig 原件，不将它自动提升为事后完整配置验收。较高峰值和启动时间差异没有证明 CPU、磁盘或宿主争用；保留这些事实但不新增根因猜测。

## 4. 完整日志和失败阶段

新 eval 10,711 B／238 行，SHA `fc4f57fb953419644b1396b2cf4fc2cc9aa9dc8b642394240a9e92647bd44aca`，与旧 eval 逐字节相同。168／172 行恢复两个 official tests；177／182 行核固定原字节 SHA；UID0 离线轮子字节检查成功；随后两文件补丁 cleanly applied，只有既有 EOF 空白 warning。226–238 行 APPLY_RC=0、RESTORED=2、EXPECTED/TEST_FILES=2、ABSENT=0、IRREGULAR 空、SETUP_OK=1，diagnostics 消费结果相同。

日志在 setup 自证处结束，没有保护子步 stdout、PROTECT_OK、UID54322 prerequisite、安装／测试 RC 或 pytest 收集／PASS／FAIL。diagnostics.control_surface、candidate_prerequisite、candidate、verdict 皆 null；ledger.install/test 为 null；grading_revision.state=not_evaluated，各参考分区 result=null。UID0 已通过不等于候选 UID54322 已通过。

ledger 的真正失败细节为 `grading_control_surface_protect_timeout_after_300s`，failure_category=infra_failure、outcome=failed_to_grade、reward=null，F2P/P2P 分子分母字段全 null，execution_failure_stage/evidence 为空。这一分级正确：尚无候选安装或测试行为可判错；不是候选0、pytest失败或外层3600s截止到期。`grader_trusted_setup=301.287596s` 仍是包含 setup、attest、保护与失败收尾的聚合段，不能当作 chown 单步时间。

同 eval 字节只证明两次留存输出都截止相同自证点；不同作业、起止时间、FP 身份、phase/peak 和报告 ID（新 `rpt_grading_a645ee12`）支持独立执行。它不证明两次保护停在同一条命令，亦不证明归档复用了同一次运行。

## 5. 与已确认保护-only 支持的边界

固定支持 receipt 明确 scope 为一次 unchanged-budget／protection-only 诊断，非 candidate/install/test/matrix；记录 `dvc9395-protect-phase-v1-20261003-07` 保护 242.4172617s、退出0、safe_closed。其宿主行到达区间为 repository chown 11.060s、prefix chown 231.108s，其余权限与自证很短；receipt 同时注明这是行到达时间、可能合并 marker，且不能解释旧300失败。

本轮核其 receipt 和题主 readback SHA，复用已经确认的支持范围；没有重新核其 62 份原件／现场 HostConfig。隔离路径这一回成功只能证明原预算在那个 fresh probe 上能够完成保护。新正式尝试失败，已直接否定“隔离成功等于正式恢复”的推断；支持 receipt 与本次作者记录本身都没有作该推断，未发现误写正式恢复或偷偷改 policy/budget。

正式两次均没有保护子步返回原件。不能把隔离 prefix chown 231s 外推为两次正式 prefix chown 卡住；不能以缺 marker 定位第一条 chown，因为超时的 stdout 未交付。具体 chown 位置、overlay copy-up、inode 数或主机争用仍须区分路径的阶段证据。

预算接线复用旧源码核查：manager 保护使用 `GradingEnvSpec.env_reset_timeout_seconds`，默认300；当前 DVC prepared face 分支只设置镜像身份，严格 DVC install recipe 未提供该字段。只升外层3600s或candidate-stage900s不会改变保护上限。若采用题级预算／consumer 或窄部署修正，须保留 ownership、official file/SHA、祖先 sticky 与 profile 判据，以新版本身份和新 prepare 表示，不能跳过保护或热改 R14；本报告不实施或承诺某个新数值即可恢复。

## 6. 清理、停止派发与阻断范围

内层 ledger.cleanup removed=true／steps=[rm:ok]／detail 空；process manager_close created_total=removed_total=1、containers_open/supply_open/cleanup_failures 空，halted/aborted null，final_status.exit_code0。外层 readback 02:31:12 按新 run_id 查 containers 和 networks，均 exit0、stdout/stderr 空、ids=[]；receipt 副本与原 readback 相同。两层清理证据完整，只代表留存时点，无本轮在线查询。

run_input 标明 stop_on_new_infra=true；失败记录 completed_valid_controls=[]，gold／c3_frozenfix／c3_missing_only／up351_port／w_swallow3 均未派发。实际归档 jobs/slots 仅包含新 prepare 和一个 noop，未含后续控制。支持“本批没有后续控制结果，控制停发与交付事实一致”；没有远端全局派发清单，不能把该归档当作全主机不存在其它作业的证明，也不宣称额外调度 helper 已独立代码验收。

唯一实际 blocking 是正式保护阶段仍未在300s内完成。需按 v2 支持范围返回可解释差异的新阶段证据或固定版本修正，再以新的真实正式控制验证；不能累计机械重试为成功概率证明。六控制有效完成数仍为0，只有两次 infra/noop 历史，五项候选的题义和得分均未由本次运行验证。

本轮未发现作者分级／差异记录遗漏足以改变结论的问题。5839 R10、6954/4166 R14 的既有有效证据不受本次失败改写；不重新批准这些题。本题 R5 actor／私有诊断不可补成正式结果；本报告不授予新模型 probe、环境／训练资格或正式矩阵通过。

## 7. 实读 SHA 与证据入口

43 个 pins 的完整清单留在 v2 输入；以下为本次决定性原件的实际文件字节 SHA。

| 原件 | 实读 SHA256 |
| --- | --- |
| [v2 固定支持输入](../requests/dvc9395_control_protect_timeout_support_input_v2.json) | `3bf174133d17334cc752c4a9775acf9782fc2017b76cd4682d5202081c1ddf57` |
| [第二次失败记录](../tasks/iterative__dvc-9395/formal_cpu_r14_recovery_failure_v1.json) | `3d330b72fb3b1fc294c7747c911ba43e078d3fe2c19ab0bea2819c8d195fb7d8` |
| [第一次失败记录](../tasks/iterative__dvc-9395/formal_cpu_r14_failure_v1.json) | `123f64e25adf8906494fa9a59c123df6f373009ac3cce611ba43c4ba3dd0fc26` |
| [已确认的保护-only 支持 receipt](../../../../../../../../runs/category2_repair_20260929/publication_cpu_takeover_20261003/support/cpu_a_control_surface_protect_v1/dvc9395_resource_support_receipt_v1.json) | `8f009c783e281db37865a6d112fb9f30ea7bd75683b08ec471b291be3374d1a0` |
| [新原件归档](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/formal_evidence/formal9395_r14_recovery_noop_021424_v1.tar.gz) | `fe3fda0dd174f56bfee92eca9a97e47ae6949231460369aa16526d1ea7984975` |
| [新归档 receipt](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/formal_evidence/formal9395_r14_recovery_noop_021424_v1.receipt.json) | `995188b76e32fed02c873a110e329b4fb4650d2aec3dd9ab6d44b989db282711` |
| [34 原件 manifest](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/formal_evidence/formal9395_r14_recovery_noop_021424_v1/manifest.json) | `35fbacbe04bfbb25941145228113c079da8d0a4174f1ed219ee9928e845cee94` |
| [新 prepare 输入](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/formal_evidence/formal9395_r14_recovery_noop_021424_v1/formal/prepare_input.json) | `cd212ec6f90983ce97e439e33bb22004102fa5f2298188e34fe763e4a486fa90` |
| [新 prepare completion](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/formal_evidence/formal9395_r14_recovery_noop_021424_v1/formal/jobs/dvc9395-r14-recovery-prepare-20261003-021424-a4/completion.json) | `21443512d3791c421c758f1550f6b414b764ad8abfbc306568730e8de597fc11` |
| [新 prepared summary](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/formal_evidence/formal9395_r14_recovery_noop_021424_v1/formal/prepared/replay_summary.json) | `4cb44fd85ba92b940b263dca5cfe93b59ecab56c0f99f05cdfd82ed743281767` |
| [新 run 输入](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/formal_evidence/formal9395_r14_recovery_noop_021424_v1/formal/run_input.json) | `1ed8cd6b84584278e89f6dfc55e61233e55b14ca62941d9a1cbf9479d624fdcd` |
| [新 run completion](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/formal_evidence/formal9395_r14_recovery_noop_021424_v1/formal/jobs/dvc9395-r14-recovery-noop-20261003-021424/completion.json) | `20d623c445047ec97b45aacc8990757c9d5f6d05075fdc7a4b0062b8854d1c4d` |
| [新实际 ledger](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/formal_evidence/formal9395_r14_recovery_noop_021424_v1/formal/jobs/dvc9395-r14-recovery-noop-20261003-021424/ledger.jsonl) | `4fa7f3f919fbc845bd5bb6d5751d5ba7ff93a5b4b8f0c28d3c9496f9c5267e7b` |
| [新 diagnostics](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/formal_evidence/formal9395_r14_recovery_noop_021424_v1/formal/jobs/dvc9395-r14-recovery-noop-20261003-021424/eval_logs/evallog_replay-dvc9395-r14-recov_a645ee12.diagnostics.json) | `3754536dae4dfd3924d15aa8deb280c9cf4ba64fb47ad08443fd8a2fce433021` |
| [新完整 eval](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/formal_evidence/formal9395_r14_recovery_noop_021424_v1/formal/jobs/dvc9395-r14-recovery-noop-20261003-021424/eval_logs/evallog_replay-dvc9395-r14-recov_a645ee12.eval.log) | `fc4f57fb953419644b1396b2cf4fc2cc9aa9dc8b642394240a9e92647bd44aca` |
| [新 process／manager close](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/formal_evidence/formal9395_r14_recovery_noop_021424_v1/formal/jobs/dvc9395-r14-recovery-noop-20261003-021424/process.log) | `64ba8e3c9d8fa58a2054478346d020bb3589d1ab379a2f81cc4a3a5f8d5b1fe9` |
| [外层清理读回](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/formal_evidence/formal9395_r14_recovery_noop_021424_v1/formal/jobs/dvc9395-r14-recovery-noop-20261003-021424/cleanup_readback.json) | `896c77932ef5e8b6b8371574021a7093cca8b67a5bfbac6682559efd6949c519` |
