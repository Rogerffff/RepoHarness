# 9 月 11 日白天补跑与归因记录

> **11:03 执行收口**：原 SWE-Gym 216 题已跑齐；MONAI-1121 三条件对照已完成；新增 R2E 24 题共 48 次和两道反例的 8 次追加复测已完成。原始证据均已回传。远端无运行或残留评分容器，实例保持开机；当前缓存 49 个镜像，磁盘约 660 GiB 可用。原过期自动化已暂停。本页下方时间记录按实际发生顺序保留，最后两节为最终结果和边界。

## 范围与当前状态

用户 10:20 指出夜间回查未触发，并授权继续完成；凌晨关于 CPU 探针扩展、保留实例、回传证据的授权仍有效。以下仅修改实验 runner 和记录，不改变 rh2 生产代码、参考测试、题面、gold 或训练集选择。

10:23 已启动阶段一余下 70 次。原主批在六小时预算内留下 364 条记录，其中 362 条完成、2 条截止中断，68 条尚未启动；原退出码为 2（partial），没有残留容器。续跑复制已封口账本到独立目录，保留原始中断记录；新日志与原日志隔离。完成后应核验 **432 个唯一任务键**，不能把包含重试的总行数当作完成数。

同机 MONAI-1121 的在线／离线无预置／离线预置权重三项 fresh gold 对照已排在续跑之后。R2E 新 24 题完整材料已准备；aiohttp、coveragepy、pillow 各一题的镜像已在远端拉取，先审查 runner 与执行六项预检，再决定扩批。当前不能称这些新题已通过。

## 定时回查为何没有执行

对象为自动化 `9-11`。已安装应用 `26.903.71938` 对此次“每日多个小时 + 有限四次”规则使用通用 UTC 分支，03:00 被计算成新加坡 11:00；再加 119 秒调度延迟，得到数据库中的 **11:01:59**。原 `last_run_at=null`，不是四次 SSH 均失败。使用应用的纯日期函数及原创建时刻精确复现；没有修改应用代码或账号设置。

Codex 上一轮只回读了创建成功与规则，未核验实际下次触发时刻，这是执行疏漏。过期自动化已暂停，不再在白天意外唤起。局部证据位于 `runs/env_probe_stage1_20260910/automation_failure_20260911.md`、原配置元数据与排期复现 JSON／脚本；其中没有访问凭据。以后不能只用“创建成功”宣称排期验证完成。

本地收集器约 03:59 出现 SSH 不可达；远端仍运行至 05:47。两件事与本次排期偏移分别记录，不将回查失效归因于未经证明的电脑休眠。

## 续跑和产物位置

- 续跑会话：`stage1_continuation`；启动记录、退出码和日志前缀：`/work/logs/stage1_continuation`。
- 合并账本：`/work/ledger/stage1_continuation_20260911/stage1_offline.jsonl`；run tag 沿用 `stage1_offline_20260910`。
- 条件仍为断网、root、3 CPU、8 GiB、64 MiB shm，官方安装和测试脚本保留；每题 2,400 秒，续跑整批最多三小时。
- 本地证据根：`runs/env_probe_stage1_20260910/`。已于上午回传原主批全部原始产物；新增日志继续增量回传。
- 预置权重包装器：`rh2/experiments/env_probe_20260909/swegym_resnet_control.py`；仅在新实验容器启动后预置已校验的公开 ResNet 权重，调用原 runner 的评分与清理逻辑。

## 初次回传的差异，尚非最终结果

原主批 362 个可比完成项中，356 项最终判定相同、6 项改变；另有 70 项待续跑。gold 变化为 MONAI-1121、MONAI-3205、moto-4799、moto-4833、moto-7105、modin-6937。逐参考测试状态改变 30 项，但状态相同仍可能掩盖失败原因改变，需读原始日志。

独立核查已确认的诊断方向：MONAI 两题分别依赖权重和 Hippocampus 测试数据下载；moto-4799／4833 的网络测试在 mock 停止期间真实访问 EC2，断网改变异常类型；moto-7105 存在两侧都有的 Docker 缺失与作业时序问题，尚不能归因断网。DVC 的 `Killed` 子串计数命中源码异常类名，不能当作进程被杀。安装阶段的返回码也必须与最终评分分列，不能只报 FULL／NO。

## 10:43 原 216 题已跑齐并回传

续跑退出 0，70/70 余项执行完成，耗时 993.7 秒，无新基建失败或清理失败。合并账本 434 行含两条已被新尝试替代的预算中断历史，最新 **432 个唯一任务**无缺项或额外项。

| 条件 | empty | gold |
|---|---|---|
| 旧默认首轮，216 题 | 216 NO | 204 FULL、12 NO |
| 本次断网，216 题 | 216 NO | 200 FULL、15 NO、1 PARTIAL |

新增 70 项未新增参考状态或最终判定变化；全池仍为 6 个 gold 判定变化、30 个参考 case 状态变化。432 份最新日志摘要匹配，镜像摘要匹配固定清单，资源峰值无缺失、无 OOM、无最新尝试超时，已确认主批标签无残留容器。脚本与 status_map 仍按原目录关联，未把这种关联提升为独立的执行证明。

116 次安装失败具体为 moto 74 次、Pydantic 40 次、dask 2 次；它们随后仍执行测试。gold 非 FULL 的 16 题包括原有 10 题 ID 缺失、modin-5940 的 S3 相关失败，以及 MONAI 两题、moto 三题的新差异。modin-6937 在断网下 FULL，不等于成功读取 S3 数据。

最终执行统计已保存于 [阶段一摘要](ledger/stage1_offline_20260911_summary.json)。原始账本、脚本、日志和逐测试对照已在本地；两个 reviewer 分别核查运行／包装器与实际差异。当前正在执行的 MONAI 对照和随后 R2E 预检另计，不能与本表合并选择最好一次来提高通过率。

## 10:49 MONAI-1121 同机对照完成

三次均为 fresh 容器、同一镜像摘要、同一 gold、同一官方脚本，沿 3 CPU／8 GiB／64 MiB shm／root 条件串行运行。三次退出正常、镜像和日志摘要可核验、容器已清理；运行同时另有远端镜像拉取，**不据此比较纯性能**。

| 条件 | 目标 F2P | 35 个 P2P | 官方结果 |
|---|---|---|---|
| 默认网络，无人工预置 | 1 PASSED | 35 PASSED | FULL |
| 断网，无人工预置 | 1 PASSED | 27 PASSED、8 FAILED | NO |
| 断网，预置指定 ResNet 权重 | 1 PASSED | 35 PASSED | FULL |

在线与预置离线的**完整已解析状态映射相同**；无预置离线到预置离线恰好是原先 8 个 P2P 从 FAILED 恢复 PASSED。已有参考集外 6 ERROR／4 FAILED 仍保留，不把 FULL 解释成执行到的所有测试都成功。

预置文件由执行机从公开 PyTorch 资产地址下载，102,530,333 字节；SHA256 为 `0676ba61b6795bbe1773cffd859882e5e297624d384b6993f7c9e683e722fb8a`，注入容器默认 torch 缓存，并在容器内再次校验。测试时保持断网，没有修改测试、题面、参考集合或评分逻辑。完整摘要见 [三组对照 JSON](ledger/monai1121_controls_20260911.json)。

结论：**预置该测试依赖足以在本机恢复 MONAI-1121 这 8 个参考回归测试**，支持将其记为可缓存的环境资产，不能因为原离线 gold NO 就直接判坏题。仅一次三条件对照，不推广到全部 MONAI、其他测试数据下载或真实模型候选；正式环境构建如何纳入资产仍与后续配置一起定案。主批 200 FULL 的原统计保持不变，不用本次恢复结果替换原记录。

## R2E 扩展进度

新 24 题来自固定 Subset revision，覆盖旧 8 仓，每仓按 expected 测试数量取三个位置，与原 24 无重合。本次实际预检选择 aiohttp／coveragepy／pillow **各仓中位位置**，不是审查报告举例的首个样本：完整 commit 分别为 `1c1c0ea353041c8814a6131c3a92978dc2373e52`、`97997d2cd6801d0335e3fa162b719d6f8c160266`、`4bc6483564ae1a254911e98280b9a501f047a2e0`。

三题六次于 10:48:57 开始，使用 `r2e_observed_probe.py` 对原 0.3 runner 加旁路观测。没有重建评分器；新增完整测试脚本、setup 后测试目录差异、测试前工作区 diff、实际容器配置、cgroup 峰值和清理原始输出。代码与远端部署摘要一致，并完成独立替身核验。新 24 中 10 题的 expected 含 FAILED／ERROR，继续按原状态映射比较。

其余 21 个镜像随后全部在执行机下载成功；预检经真实日志、实际补丁和清理核对后，于 10:53:08 启动其余 42 次评分，10:56:41 正常退出。

## 新增 R2E 24 题与两道反例

| 批次 | 结果 | 验证口径 |
|---|---|---|
| 新 24 题各一次 noop/gold，共 48 次 | noop 24 个 reward 0；gold 22 个 reward 1、2 个 reward 0 | 按来源 expected 精确匹配；不要求所有 expected 都是 PASSED |
| 两道反例各追加两次 noop/gold，共 8 次 | 两题各三次 gold 均出现原来的同一不匹配 | 与首轮目录分开，不覆盖首次结果或挑最好一次 |

48 个计划键完整、48 个初次容器 ID 各不相同；初次记录没有 missing/extra 测试项，每个 noop 至少有一个 expected PASSED 的 case 实际 FAILED／ERROR。原 runner 与固定 Prime 的首三题评分经独立重算一致。测试前真实生产文件 diff 与原 gold 分别应用到来源 old content，**24/24 题的纳入文件最终内容相同**，排除了这批 gold 被 stash/pop 弄丢或漏应用的解释。摘要见 [R2E 扩题结果](ledger/r2e_expansion_20260911_summary.json)。

旁路观察也记录了来源镜像的已有改动：aiohttp 的 Makefile 在 noop/gold 都有相同的 pip→uv 调整，不能假设每个镜像等于干净 Git checkout。coveragepy 的 xdist 日志虽没有字面 `collected`，实际状态映射完整，不能单凭 `tests_collected=false` 判失败。单纯数 diff 增删行出现的两个提示，已用最终文件内容对拍解释：coveragepy 的相同引号行增删互相抵消；orange3 沿原 `git apply --whitespace=fix` 去掉 EOF 空行。没有为消除提示改动 runner 或参考补丁。

### coveragepy：历史依赖不可见被写进 expected

题目 `016af5f6352d69206ac8f7537c2b18828767bcae`：来源 expected 为 14 PASSED + `MockingProtectionTest.test_os_path_exists` FAILED。当前 gold 实际 15 PASSED、1 SKIPPED；按原规则得到 reward 0。该 case 在当前 noop 也通过，**不是 gold 额外修好了一个预期失败**。

来源冻结的 old/new 执行日志中，该 case 的失败都是 `coverage run bug416.py` 子进程无法导入 `mock`；setup 记录却曾列出安装 `mock==3.0.5`。因此准确事实是**历史子进程的依赖不可见**，尚不足以断言整个环境没安装 mock 或确定历史 PATH／解释器根因。真正目标 `ExecTest.test_unencodable_filename` 在当前 noop 失败、gold 恢复。当前三次 fresh gold 都复现“15 PASSED 但 reward 0”。

这是一条 expected 含环境相关失败的具体证据，不能外推为所有 mixed-status 题都无效；本轮保留原 reward，不自动改 expected 或排题。

### datalad：新断言引用旧仓库测试 fixture

题目 `58ba5165234cb16de0e8463ee75097362099835f`：noop 两个目标 case 失败；gold 修复 API case，但 `test_alter_interface_docs_for_cmdline` 仍失败。gold 的两个生产文件已正确应用。

冻结的测试代码和实际镜像中的 `r2e_tests/test_1.py` 都从 `datalad.interface.tests.test_docs` 导入 `demo_doc` 等示例文本；修复提交同时改过该仓库测试文件，但现行 gold 重建排除测试文件，因此运行时仍读取旧文本。新 CLI 断言要求的 multiline brackets 文本不在旧 fixture 中；另一个 API 测试则在 `test_2.py` 内自带新文本，可以随生产代码修复恢复。

独立 stdlib 对拍复现“新函数 + 旧 fixture”在同一断言失败、“新函数 + 新 fixture”通过；它是隔离诊断，不改变原始评分试验。实际被导入的 `test_docs.py` 也已从镜像补取：3,077 字节，逐字等于来源 old、不同于来源 new。当前三次 fresh gold 都在同一 CLI 断言失败。该事实支持测试材料对原仓库 fixture 的依赖未被完整移植，不能称为模型不会写正确代码，也不在本轮直接批准把测试文件加入候选补丁。

## 证据、实例与后续边界

- 所有新账本、测试日志、状态表、脚本、镜像和资源事实位于本地 `runs/env_probe_stage1_20260910/`；主要原始目录为 `ledger/stage1_continuation_20260911`、三个 `ledger/monai1121_*_20260911`、`ledger/r2e_preflight_20260911`、`ledger/r2e_remainder_20260911`、`ledger/r2e_failure_repeats_20260911`。
- 从 24 个实际镜像额外导出了测试文本与 `run_tests.sh`，没有启动模型或镜像进程；快照和逐文件摘要保留在 `ledger/r2e_fixture_snapshots_20260911`。测试 fixture 的后续静态审查不必重新租机才能开始。原始 parquet 和 Docker 镜像仍留远端，镜像从未经本机中转。
- 独立核查位于本地 `local_checks/`：主批 362 条、续跑 70 条、MONAI 三对照、R2E runner／旁路包装器、首三题实际结果及两道反例分别留证。历史的 `log_bytes` 字段实际用字符数，日志完整性核验依赖实际 UTF-8 文件 SHA，而非该字段。
- 11:03 的机器检查：tmux 已无探针会话，Docker 容器 0，缓存镜像 49 个、Docker 报告约 106.9 GB；磁盘已用约 116 GiB、可用约 660 GiB。这是当前工作集占用，不能外推成全部 SWE-Gym／R2E 镜像容量。机器保持开机，没有释放、另租或调用付费模型。
- 原自动化 `9-11` 已回读确认 PAUSED，不继续声称夜间定时已执行，也没有创建未经实际时刻核验的新排期。

这次完成的是阶段一原批、必要归因和一组扩题探索；**没有执行正式 rh2 grader 集成对账，也没有改变评分规则、训练资格、数据划分或题面**。后续有证据可讨论的事项是测试资产如何预置、安装阶段如何固化、网络服务依赖如何处置、导入型测试 fixture 如何完整提供，以及对含历史环境失败的 expected 如何处理。它们应进入对应阶段的具体设计与决策，不能把本次 gold 统计直接当成正式训练环境通过数。
