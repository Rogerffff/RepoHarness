# 216 题真实 RH2 评分：运行记录

2026-09-19 / B Codex，时间均为新加坡时间。按[执行单](full216_diagnostic_plan_20260919.md)运行；本页记录实际执行，持续更新。地址与连接配置只放本地忽略目录。

## 当前状态

- 新机器已接通：KVM、Ubuntu 22.04、11 vCPU、约 49 GiB RAM、800 GiB 虚拟盘（启动时空闲 767 GiB）、Docker 28.1.1/overlay2、cgroup v2。与租用截图不同，按实际资源采用 4 路与镜像分波处理。
- 当前生产源码/输入 196 个文件与同步前快照逐文件一致；锁文件安装完成，环境/parser 自检 26 passed / 1 skipped，prepare 与 gold 导出均为 216。生产实现和评分语义未改。
- **本轮诊断已收口：432 次主批，加校准、持续运行、并发及全部资源补测，合计 532 次尝试、530 份日志。** 4787 个证据文件已回传并逐文件核验，四个 systemd 作业均正常结束，远端没有残留容器。[结果报告](full216_results_20260919.md)汇总发现与待处理项；生产问题并未因此核销。
- 本轮新增两个实验外壳：`rh2/experiments/full216_diagnostic_20260919/{worker,campaign}.py`。真实评分仍调用现有 replay/manager；外壳只负责派发、计时、资源观测、证据和异常停发。两名独立 reviewer 检查过调用与清理边界；主审复现了磁盘写入失败/inspect 超时仍清理的监督探针。

## 已验证的校准

| 题目 | noop / gold | 参考缺席 | grader 内存峰值 MiB |
| --- | --- | --- | --- |
| mypy-12741 | 0 / 1 | 0 / 0 | 112.7 / 104.3 |
| dask-7894 | 0 / 1 | 0 / 0 | 268.2 / 238.7 |
| conan-13326 | 0 / 1 | 0 / 0 | 65.1 / 63.9 |

6 份日志摘要一致，运行器摘要未变，候选与 grader 容器均已清理。旁路采样实际读到了 14 次容器 cgroup 数据。条件为 UID 54322、2 CPU、4 GiB、shm 64 MiB、tmpfs 1 GiB、`deny_all`、无 P-A 资格；安装/测试仍共用现有预算。安装返回码只描述段末命令，不能单凭它证明所有安装步骤成功。

新机存储对照复现旧问题：metacopy=N 时，容器内与 commit 后内容都正确；Y 时容器内正确，commit 后 34 字节变为 34 个零字节。现主批用 Y 加原镜像的 merged 视图评分，**本配置下不构建派生镜像**；需要派生时在无作业期间切回兼容条件并重新核验。

## 夜间顺序与停止处理

1. `baseline01`：216 题各 noop/gold 一次，共 432 个固定计划键；4 个 worker，每波至多 32 题。下载在各波评分前完成，单独记时。
2. 主批正常收口后，`soak01`：16 道 mypy、一个 manager 连续执行 32 次尝试，记录 RSS/PSS、记录数及保留日志字符数；实际进入 grader 的次数另计。这只支持该长度/题型的持续运行结论。
3. 随后 `perf1/2/4`：固定 mypy/dask/conan/dvc 四题，各 noop/gold 重复两次，对比 1/2/4 路。新机共享宿主与后台证据同步属于实验条件，不外推为训练吞吐保证。

每个已派发尝试先写 started，再落生产账本与 finished；未完成计划项一直保留。普通逐题失败继续；未知评分异常、契约矛盾、清理不确定或资源不足会停发并留证。监督器退出也会终止所属 worker 并按精确 run label 回查/清理。worker 不自动替换，下一波启动前确认无活动容器，避免现有 startup GC 误扫其他 owner。

远端路径：`/work/full216_20260919/`，其下 `replay/` 为各批结果，`evidence/` 为校准与机器事实，`logs/night.log` 为串行调度日志，`ops/night.sh` 为阶段顺序。`replay/<批次>/HALT.json` 和 `evidence/night_done.json` 是巡检入口。必要资源/依赖对照在读取主批结果后另起目录，不自动替换主批成绩。

## 巡检与本地证据

- 原自动化 `9-11` 复用并改名为“RH2 216题夜间巡检”，归属本任务。改用短间隔首检，去掉上次引起 UTC 分支问题的固定多时刻/有限次数组合。
- 首次基准排期 **01:41** 已核对时区，启动任务持续运行期间顺延；**02:05:01 实际收到自动巡检，数据库 `last_run_at` 同时更新，首次唤醒验证通过。** 已改为每两小时并回读下一次为 **04:07:07**；完成后暂停，最晚不超过 09-20 中午。
- 本机接 AC，使用有界的 12 小时防空闲休眠，不阻止显示器休眠；[官方说明](https://learn.chatgpt.com/docs/automations?surface=app)要求本地任务的电脑与应用保持运行。远端主作业独立于 Codex/SSH。
- 独立本地收集器每 3 分钟增量同步 `evidence/logs/ops/replay`，每次启动最多运行 12 小时；08:11 巡检中为覆盖最后的进程归因补测重启。需 `night_done`、`dvc_pids_done`、`resource_variants_done`、`dvc_procscan_done` 四标记均落盘后才收口。凭据、Docker 镜像和运行 venv 不回传。
- 本地证据根为 `runs/full216_rh2_diagnostic_20260919/`，远端备份位于其 `remote/`。若作业中断后另起续跑，保留旧结果，检查收集器是否已因旧 `night_done` 停止，再恢复同步。

已知 P-A 归因、参考缺席与 stdout/hook 可信性问题继续保留，本轮不核销这些审查项，也不批准正式训练池。实例保持运行；没有提交、推送或通知其他任务。

## 02:05 首次自动巡检

- 第一波 32 题完成 64 次尝试：noop 32 个 0；gold 31 个 1、1 个 `apply_failed`，该条没有评分报告或 reward。无 HALT，主批继续后续波次；当时可用内存约 47 GiB、空闲磁盘 749 GiB，没有宿主资源压力。
- 新确认 **mypy-11352 的来源 gold 上下文与声明 base 不一致**：补丁上下文写 `from mypy.plugins import ctypes`，镜像同一行实际为 `ctypes, singledispatch`。原始冻结数据的 patch 与导出 gold 逐字相同；镜像 HEAD 等于声明 base，目标文件等于 HEAD 的 Git blob。因此不是导出过程改坏补丁，也不是该文件在镜像里有未提交修改。
- 在独立临时目录只做 `git apply --check`：原补丁失败，仅更新上述上下文行后检查通过；**没有应用、重评或替换 gold**。这与 e2 同题 DeepSeek 候选的 `test-requirements.txt` 冲突不同，保留为来源工件适配问题，不计作模型失败。证据已回本地 `remote/evidence/gold_apply_mypy11352/`，原始行对照为 `raw_gold11352_crosscheck.json`。
- 唤醒实证、两小时排期与回传记录分别为本地 `automation_first_trigger.json`、`automation_two_hour_schedule.json`、`collector.jsonl`。远端主作业未重启，生产代码/资源默认值未修改。

## 04:07 第二次自动巡检

- 自动触发再次确认；下一次回读排期为 **06:08:33**。04:14 回传快照已完成 **365/432** 次：noop 183 个 0；gold 170 个 1、11 个 0、1 个应用失败。364 份评分日志摘要一致；全部无资格注入、候选清理确认，无 HALT。主机快照约 47 GiB 可用内存、544 GiB 空闲磁盘；不能据此排除单容器配额问题。
- **新资源反例：dvc-2141 的 noop/gold 都在 `fork_exec` 出现 `BlockingIOError: Resource temporarily unavailable`，被记为 `tests_failed`、reward 0。** 主机旁路采样见 noop 的 `pids.current=512`、gold 最高 509，内存峰值仅 203/197 MiB、采样 OOM 事件为 0。与进程配额耗尽一致，具体累积机制尚待对照；源码中 rollout 有 `--init`，grader 没有，也将检查是否存在未回收子进程。证据：`dvc2141_baseline_resource.json` 及原日志，未改分类/分数。
- moto-4799/4833 的失败日志指向 EC2 域名不可达，与此前离线发现一致；脆弱参考 ID 继续单列。其余题尚在运行，不提前汇总为全池结论。
- 已排独立 systemd 作业 `rh2-full216-dvc-pids`：仅在原主批、soak、perf 全部正常完成后启动，dvc-2141 在 **512/2048 进程配额**下各跑 noop/gold ×2（共 8 次），其他正式条件不变，仍无资格；额外只读采样 `pids.events`、进程状态及 OOM。结果另存 `replay/dvc2141_pids512/`、`dvc2141_pids2048/`，完成标记 `evidence/dvc_pids_done.json`。这是已授权资源诊断，不修改生产默认值；原作业 fatal 时不会自动越过继续。
- 本地本次核验为 `heartbeat_0407_local_review.json`、`automation_second_trigger.json`；远端快照为 `evidence/heartbeat_0407.json`，排队配方为 `evidence/dvc_pids_queued.json`。新增脚本位于本地忽略目录 `ops_followup/`，已语法检查、同步并确认排队服务运行；此时对照尚未执行。

## 06:09 第三次自动巡检

- 06:14 回传快照 **422/432** 次：noop 207 个 0、5 个无奖励；gold 192 个 1、13 个 0、4 个无奖励、1 个应用失败。421 份日志摘要一致、无资格、候选清理确认，无 HALT。全部 216 个镜像已下载；末波尚在评分，故 `summary.json` 的上一波 384 不是实时完成数。主机仍有约 44 GiB 可用内存、366 GiB 空闲磁盘。
- **MONAI-763**：noop 的部分测试与 gold 的 pytest 内部报错均明确出现 DataLoader `Bus error`；gold 零解析被记为 None。**Modin**：三个活动容器 `pids.events max` 为 9/9/17，`pids.current` 为 503/502/468，采样 OOM 为 0；多个尝试撞到 1800 秒测试期限。这里配额计入线程，不能由少量进程行数判断没有耗尽；旧 e2“与 pids 无关”不能跨条件套用。现场保存在 `evidence/heartbeat_0609.json`。
- 已排 `rh2-full216-resource-variants`，在原夜间批次及 DVC 对照正常收口后才运行：MONAI-763 用 **8 GiB 内存 + 1 GiB shm** 各 noop/gold 一次（联合档位，不分别归因）；Modin-6298 只把 **pids 512→2048**，各一次。使用现有 profile 环境变量，其他条件不变、无资格、不改生产代码。结果分别为 `replay/monai763_mem8_shm1/`、`modin6298_pids2048/`，完成标记 `evidence/resource_variants_done.json`。此时仅确认排队，尚未执行。
- 本地核验为 `heartbeat_0609_local_review.json`，配方为 `evidence/resource_variants_queued.json`；收集器已覆盖追加批次并成功同步。第三次唤醒已实证，下次实际排期 **08:10:42**；持续运行、并发和资源对照均需后续核验，不能把 `night_done` 当作全部审阅结束。

## 08:11 第四次自动巡检

- **主批 432/432，主作业正常结束，无 HALT。** noop 为 211 个 0 / 5 个 None；gold 为 194 个 1 / 15 个 0 / 6 个 None / 1 个应用失败。全部计划键、账本与 started/finished 事件对上，431 份日志摘要一致。soak、perf1/2/4、DVC 两组也逐键核对；含校准合计 **526 次尝试、524 份日志**。统计及逐题表为 `analysis_0811b/`，断言记录为 `heartbeat_0811_verification.json`。
- **DVC 配额因果已复现**：512 时 gold 0/0，2048 时 gold 1/1，noop 均为 0；提高配额后 P2P 全部恢复。2048 时观测 PID 计数最高 742–775，配额拒绝事件为 0。现有 `docker top` 列表与计数差距很大，不能据此排除僵尸或直接认定线程膨胀；追加原条件 noop/gold 一次，按 `/proc` cgroup 归属区分进程状态与线程数，尚不改 `--init` 或生产默认值。
- 新排队作业 `rh2-full216-dvc-procscan` 仅在此前资源补测正常收口后启动；结果目录 `replay/dvc2141_procscan/`，观测 `evidence/dvc2141_procscan.jsonl`，结束标记 `evidence/dvc_procscan_done.json`。实验脚本已语法检查，源码/配方摘要为 `evidence/dvc_procscan_queued.json`。
- 同 manager 31 次实际评分结束 RSS 197.0 MiB；1/2/4 路固定对照为 643/417/324 秒，分数一致，解释范围见阶段报告。MONAI 较大资源档的 noop 已跑到完整测试结束（1599 秒、峰值约 6497 MiB），gold 尚在执行；Modin 资源对照随后运行。不能把中途失败/通过当作最终资源包决定。
- 第四次自动触发已核实，下次排期 **10:11:14**。实例保持运行，补测和证据同步继续；未提交、推送、改生产评分或通知其他任务。

## 10:11 第五次自动巡检与收口

- **11 个批次均正常结束，无 HALT；532 条计划、账本和 started/finished 事件逐键一致，530 份评分日志摘要一致。** 两个无评分日志的尝试是主批/soak 中同一 mypy-11352 gold 应用失败。最终远端清单的 4787 个文件（约 236 MiB）全部与本地匹配；196 个源码/输入文件在本地与远端均未偏离启动快照。统计为 `analysis_final_1011/`，断言记录为 `heartbeat_1011_verification.json`。
- **DVC 进程机制已定位**：最后的默认条件 noop/gold 再次均为 0；按 cgroup 扫描 `/proc`，最多 507/496 个僵尸进程全部由容器 PID 1 的 `sleep` 收养，配额达到 512、拒绝事件 38/37。当前 grader 无 `--init`，与 rollout 不同。证据支持先验证回收机制，不能只提高配额便视为修复；本轮未改变 grader 启动参数。
- **Modin-6298**：只提高 PID 上限到 2048 后，noop/gold 恢复 0/1，测试 34/31 秒、无参考缺席；未扩展到其余 Modin。**MONAI-763**：8 GiB 内存+1 GiB shm 条件恢复 0/1，峰值 6497/6328 MiB；gold 仍有参考集外断言失败。两个单题变体不修改主批计数或正式默认值。
- 四个远端服务 `ExecMainStatus=0`，`docker ps -a` 为空；空闲磁盘约 366 GiB、可用内存约 47.6 GiB。本地收集器在四个结束标记与成功同步后正常退出，本次再做了最终同步与清单核验。现场为 `remote/evidence/closure_1011.json`，实例继续保留。
- 第五次唤醒实证为 **10:11:33**。收口后通过官方 `automation_update` 暂停 `9-11`，回读 TOML/数据库均为 `PAUSED`、`next_run_at=null`，任务归属未变；记录为 `automation_fifth_trigger_and_pause.json`。同时仅停止本任务创建的有界防空闲休眠进程。没有关机、另租、提交、推送或通知其他任务。
