# MONAI2446/6975 R15 正式 CPU 编排：非作者静态核查

日期：2026-10-03。审查者：GPT-6.1 Sol / high，非材料作者。

## 结论与范围

在本次固定版本的静态范围内，未发现会确定阻断正式矩阵、把旧 FrozenPatch 换身份重评分、修改测试预算，或按其它作业标签读取/清理容器的错误。可按已授权共享 CPU 槽方案继续准备与正式矩阵。该结论不是准备成功、正式运行通过、GPU 放行或训练/留出资格。

本次不是 fresh 公开读者盲审。审查者已接触两题私有修订、controls、6975 原 actor 与 COPY 恢复原件，并已有 3715 和 6975 非作者报告。接续这些上下文，只核新脚本和 R15 材料/正式消费路径；未重做未变私有 oracle 语义审查、未重审 3715。本次只读本地文件及 SHA/JSON/AST，无 SSH、Docker、CPU/GPU 作业、模块 import 或测试执行；仅新增此报告，不修改其它原件。

## 固定身份

- 本包编排脚本：`cpu_formal_r15.py`，SHA256 `7dbc9b7b108b816c6da65ed5c8bd01ebb913fc91cf26b995c81d422a3539f63c`。本地 AST 解析成功。
- R15：`runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe39_dask_monai_v1/`，manifest SHA256 `2b788d1ce84228a27894e04886ade347e91993f48ddc9bdeeb8f92de4aa92917`；独立核 1,305 个登记文件的字节数与 SHA，全匹配。
- R15 两题 registry：`repo/docs/agentic_RL/repo_harness_rh2_workstreams/s2/revisions/monai2446_6975_fixed_v1/material_revisions.json`，SHA256 `4e8ab1f132a4546a53c32ee2845fedc372e837164dd9b41ebeba497d77ef074d`，与 consumer pin 匹配。
- 沿用 CPU 输入包 `inputs-cpu-c-20261003-84df00d5/input_manifest.json`，SHA256 `902e402a20724488b95df81d2d4ffbb198d8609f7bbccbd0db50b7a43673db77`；独立核 174 个输入的字节数与 SHA，全匹配。controls 是原补丁正文输入，不是旧导出的 FrozenPatch。

| 题目 | 固定有效测试 patch SHA256 | 正式参考 | 固定本地 grader / replay image ID |
| --- | --- | --- | --- |
| 2446 | `c413f2b150eec668aee425cf1171faedaf7fdbb8c9a3bae171328a741231b7e7` | 1 F2P + 3 P2P | `sha256:28959a332c8a17ebfb2db681d3afaf79f8fd6e845ba51406fc7772f32453bcdd` |
| 6975 | `b45d702474e07849816f2540af31513a1c0ef2fa94a0aea9d841fe7a4c00eb97` | 4 F2P + 60 P2P | `sha256:fbfdddc4edda1f0ea4c1b76a572bd95045be4bbd202b197a94e8d8ee14a73fd6` |

独立重算完整材料 canonical JSON SHA，2446 为 `fd41c82513d5fff6a56d1fdfe569a561d7fc0608684636b6658a5107fecf4497`，6975 为 `9c51fc8c8506cb8ee2414f7d417f8f70b0e97c1fffdd51a7547dd9358f87e792`，均与 `monai_fixed_revision.py::MONAI_FIXED` 匹配。原/有效 patch 正文 SHA 均匹配；环境绑定文件正文等于 registry 中的绑定，其文件 SHA 分别为 `357ad4df90fb4ed2886402f0a069205dea6f3c18bfbed9493936ef2f38cb8c01`、`cd5a58a4be3acd202757606e3f0f2614718599d9f481acc7083ab539db474a56`，均匹配。

## 材料、安装与身份接线

R15 `swe_material_revisions.py` 对 registry、环境绑定、fixed_request、原/有效测试 patch、登记 base 测试、Dockerfile、2446 wheel/配方/补充/准备资产，以及 6975 官方资产/环境复用资产核固定 SHA；对来源 public/grading/base/parent digest 作配对检查。`PrivateGradingBundleSWERevision` 再要求有效 patch 和完整参考精确相等，并恢复原评分面检查 parent digest。没有从自由目录接受任意新环境配方的路径。

2446 runtime install 先以 `--no-index --find-links=/opt/rh2/compat-wheels --no-deps` 安装 NiBabel 4.0.2，非零立即 return；前后输出版本，再执行保留的 vendor 原安装串并返回其末命令 RC。6975 的 revised_install 与 original_install 逐字相同。本轮未新增依赖改变或 COPY 配方改变。

`prepared_task_face.py` 将两题绑定到登记的本地派生 image ID，并标为 local_build。只接受精确 source ref/manifest 配对、原来源 tag/manifest 配对或登记 ID/None，错误覆盖拒绝。replay 的 `registered_grader_image_id` 路径先 inspect 实际 ID 并与固定 ID 比较，candidate 暂存和 grader 用该 ID；正常 ledger 会记录 actual ID，区别于旧 3715 vendor ledger 的 null。脚本要求每行 actual ID 等于启动前固定 ID，因此这里的检查适用，不能据此回写旧 ledger。

trusted root 和 candidate UID 54322 各自执行固定 prerequisite：UID 必须正确，资产必须以 `O_NOFOLLOW` 打开、为普通文件且 SHA 精确相等。2446 还核 NiBabel 4.0.2 和固定 wheel SHA；6975 核官方 NIfTI 资产 SHA。这里 candidate UID 是正式 grader 的 54322，之前公开 actor 的 54321 是另一个角色。manager 在控制面保护后、候选安装/测试前执行 candidate prerequisite；非零走 `GradingInfraError`，先保留原 stdout/stderr/RC，再记 failed，不算任务目标测试失败。

原安装串内有分号；最后一个命令 RC0 不证明前面 pip 均成功。正式渲染器保留 `RH2_INSTALL_CMD_FAILED` ERR trap 和阶段 RC/时间戳。2446 wrapper 也保留原串这种语义，未替换成任意成功掩码。本轮不能证明实际 install 成功；运行核查须读完整安装正文、失败 marker、实际版本与前后观测，不只信 campaign reward/段末 RC。

## 矩阵、FrozenPatch 与预算

脚本固定 2446 `noop/gold/array_no_shuffle/alternative_list_copy = 0/1/0/1`，6975 `noop/gold/degenerate_discard_dict_output = 0/1/0`。每个 patch 从已核输入 manifest 取 SHA，缺件/不匹配会停止。七个控制 patch SHA 分别为：

| 题目/控制 | SHA256 |
| --- | --- |
| 2446 noop；6975 noop | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| 2446 gold | `0c0e9e07a3d8195c75cebdac933cb628fef3425e2721f99087fea2ced6fc9f1a` |
| 2446 array_no_shuffle | `91bcb98b33149e93606f2e42d48de5a08fd735a4e4e1c54da0f84d04933024e0` |
| 2446 alternative_list_copy | `f4571b4a1fd55f8047fe5a0f28384f276c2fbefaeb25a34c1cde27a9d77104c4` |
| 6975 gold | `fdd419570d9b18f8b9ce762d0112ab2cfc5a8c3f527c03f198b98bfae6800c3d` |
| 6975 degenerate_discard_dict_output | `326d8624ed445a99281ff33d02b99670e1cc364b827fd26593b745da7ff09118` |

正式入口是冻结 R15 `replay_with_cpu_budget_v2.py --mode direct` → `scripts/replay_grade.py run`。每行新建 candidate 容器、新做 baseline census、按原 patch `git apply --check`/apply、重新 export FrozenPatch 和 projection，然后交 manager.grade。没有读旧 FrozenPatch 再修改其 image/material 身份的动作。旧 controls 可以复用，新导出身份和真实评分必须重新核。

后续控制只用本轮 noop ledger 作环境资格输入。资格 loader 要求 noop/gold、有效测试 outcome、参考缺席数0和身份/脚本摘要；manager 另核镜像、脚本、材料三者一致，旧或不同材料资格不能仅因同 task_id 接受。该资格只供评分失败归因，不授予训练或留出用途。

预算：candidate stage 900s，grading deadline 3600s，cleanup 120s，image pull/inspect 1800s，单行外层6600s。2446 setup 900s，6975 setup 1800s；6975 1800 亦登记在绑定。CPU budget wrapper 只替换 env_reset_timeout，记录 before/after/test_seconds_unchanged，不修改原 test_timeout、评分、保护脚本；这些是可追溯的准备预算覆写，不应写成所有时间预算未变。sandbox/grader 环境均设2CPU/4GiB；实际 HostConfig/cgroup/峰值尚无本轮运行证明。

## 自身观察、异常与验收边界

run_id 为经校验 job ID 加固定控制名，传 `MILES_RH2_RUN_ID`；replay 和 manager 用相同精确 `rh2.run_id` 标签。观察只按本行标签 `docker ps -a`，inspect 后再次断言标签一致；不会扫全机容器或按宽泛名称清理。观察函数只读，未直接 rm；正常行的自身残留查询亦按相同标签。

runner RC 非零、stage_error、reward 缺失、candidate cleanup 未确认、参考缺席、runner final 缺失/非零、自身残留查询非零/非空、实际 image ID 不符、F/P 总数不符，都会中止为诊断。期望 reward 不符最终状态为 expectation_mismatch/RC2。只有全行期望匹配且前述条件满足才标 `executed_pending_non_author_review`，其字面保留“待非作者复核”。异常原样抛出，状态写 stopped_needs_diagnosis；SIGTERM/INT 先停子进程组，180s后 forced kill 会记 cleanup_unconfirmed_after_forced_kill，不能据此说清理成功。

正常 final_status 来自冻结 replay 的 manager.close，外层再核 candidate cleanup 与自身容器残留。这是两层检查的静态安排；外层残留查询只覆盖容器，网络/relay 清理仍须实际读 manager.close 完整结果。异常/强杀分支不保证外层再次完成 residual query，必须保留失败原件、人工核清理，不能仅凭 campaign 状态或 launcher 退出说清理已确认。

只读观察存在正常竞争窗口：容器可能在 ps 后已被删除，inspect 非零记 observation_errors 并继续；首次成功 inspect 后不会重复采样。观察调用超时/结构错误则停止诊断。自动成功条件不要求 observation_errors 空或一定存在成功 inspect，因此自动摘要不能代替独立核实际 HostConfig、容器角色和 image ID，也不证明资源峰值、cgroup峰值或磁盘配额。这是观测范围限制，当前没有实际缺证行可据此判运行阻断。

准备申请 `monai-r15-prepared-20261003-516a5244` 的 `.launch.json` 指向 R15 与两题 fresh prepare；`snapshot-14a67658.json` 为 status/prep/unit null、exit RC75、原 log “All CPU slots busy; retry later”。它没有入槽、没有 prepare 结果。本脚本先核 prepared launcher 的 R15 SHA 与 exit RC0；不能把这个 RC75 当成功输入。下一次应核真正成功的新 prepared summary、public 保持、private 修订/安装/资产绑定，再核完整七行。没有要求机械重做已有效的 6975 COPY 与公开 actor 证据。

## 后续运行核查必需材料

实际正式 launcher 须绑定本次脚本 SHA、R15 manifest 和固定输入包；准备 summary SHA 本脚本会记录，但仍需读取其具体 prepared/private 身份。每行需完整 ledger、eval.log、install/test/UID prerequisite 原输出、FP/baseline/projection、预算审计、container inspect、runner final/cleanup、外层退出；参考应逐项核无 skip/异常冒充目标失败，不能只比 4 或 64 个计数。generic scripted actor 首 prompt 不证明正式题面已实际交付；此前两个通用 marker false 也不因 R15 自动转 true。

旧非作者报告未改。已回核旧 SHA：3715 CPU `e3d0000d81bc147a8a7acf490e821615a5f162470bf3651cd41f8dbf83534913`；6975 静态资产 `9c4f60693ace670ef80406e72b2dea4e98a16b51e7cd4e21185342d65a9c3ea9`；v2 增量 `c5660c49fd7c55180e6ec7c6dd313c9f892bbd798ff4ebf0e556c022103c48d7`；COPY/actor runtime `af91e9e87da3678430a17d709403dc2e032f341de3fb1255698a01cd5256d09f`。
