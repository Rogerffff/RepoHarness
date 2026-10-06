# Moto 四题 R13 矩阵工具：非作者静态窄核

日期：2026-10-03。结论：**本次静态核查未发现启动阻断，可按现有授权启动固定工具。** 这只确认编排入口与固定 R13 消费者相容；四题实际 CPU、真实 actor 与准入结果仍待各自原件验收。本报告不修改公共契约，不新增审批步骤。

## 范围与实际读取

审查者不是工具作者；此前已接触 Moto 私有断言、对照补丁及金标，本次也读取了私有 producer、registry 和候选补丁以核身份，**不是公开材料盲读者或 blind solver**。没有重新评判四题全部断言语义，没有运行模型、自主求解或测试。

本次逐字读取 `tools/moto_four_r13_matrix_v1/` 的 `matrix.py`、`tasks.json`、`expected_runtime.json`、`manifest.json`，并对照固定发布目录 `runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe27_pandas_moto_v1/` 下的原 CLI、ReplayGrader、prepared face、vendor 命令派生、sandbox profile、manager 及 revision diagnostics 源码。读取发布 manifest、四题 producer 四类 JSONL、四份 material registry 与 environment recipe，以及候选文件进行静态 SHA/bytes 读回；发布 `checks/material_consumption.json`、`checks/resolve_moto.json` 仅作结构导航，其作者结论未代替源码和原件核查。

实际操作只有本地文本读取、标准库 JSON/哈希计算与 `ast.parse(matrix.py)`。没有导入或运行项目、SDK、模型、测试、Docker、`verify_release.py`，没有连接远端。只新增本报告，未改共享实现、冻结输入、既有报告或固定 probe 请求。

## 固定字节与消费身份

四件工具文件集合精确匹配 manifest，成员不是符号链接，SHA/bytes 均匹配：

| 文件 | SHA-256 | bytes |
| --- | --- | ---: |
| `manifest.json` | `a72d5d57e6c85f12105642ac1ef91e1aa18e618afb39ddd93133184850b7ef99` | 624 |
| `matrix.py` | `e721d4bf7a44fc50011ac89d46a435fe765e15bd3fd79e71161d46c3cb5e6ea2` | 13170 |
| `tasks.json` | `b6e01cb20aeca3c6a77b930f1e5630194f636583aa376111046c9d4dbcd07117` | 26490 |
| `expected_runtime.json` | `276b9091302e587eefe6530a412793b481e1fd86cf223fbb3d77ddffe421d189` | 40272 |

固定 R13 release ID 为 `cat2-cpu-r2e089092-swe27-pandas-moto-20261003-v1`；manifest SHA 为 `3fad18daff8db219294e10cbf08d4424d68cf7000d008bb983cba4bdc427b641`。独立本地读回其 1094 个 manifest 成员，共 125080983 bytes，全部 SHA/size 相符且无符号链接；`verify_release.py` 本身也与 manifest 的单独 pin 相符。这是本地文件完整性核查，不宣称执行了发布验证程序。

producer 为 `s2/ingest_swe27_pandas_moto_combined_20261003_v1`，其 manifest SHA `81b82a7083b8348f0c385f1c9b774b4917eb584bf3f93e75c9c04d4a1df16079` 与工具相符。四题 registry、recipe 文件 pin 与实际字节相符，`tasks.json.environment` 等于固定 recipe。按固定 `contracts/_base.py` 的 canonical JSON 定义，用标准库重算四题 public、grading、environment 三类 digest，全部等于 `expected_runtime.json`；金标内容 SHA、有效 test patch SHA 也分别与 validation 和 registry 原件相符。35 份非 noop 补丁的本地对应原件全部 SHA/bytes 相符。远端候选路径是固定 preparation 根下的仓库相对布局；本次只核本地对应字节，远端到货事实须由运输及执行原件证明。

每题 expected 的 base、source image/manifest、revision ID、parent grading digest、registry SHA、参考分区与实际 producer/registry 一致。分区合并后逐项等于 producer 的 F2P/P2P 清单；`materials_identity` 按原定义重算相符，`state=not_evaluated`、各分区 `result=null`，没有把静态材料当成评分结果。工具在执行前调用固定 `load_context` 和 `build_grading_spec_from_host_view`，读回完整 13 项输入并与 expected 整体相等比较，包含五种生产脚本 SHA。静态审查核了这些 API、属性及脚本生成路径；**未执行生成器来独立重算五种脚本**，实际消费者和脚本 SHA 相等仍由启动前的原入口读回及后续原件核实。

## 原 CLI、完整测试和预算

`matrix.py` 使用固定发布的 `rh2/scripts/replay_grade.py` 执行原 `prepare`、`export-gold`、`run`，参数名与原 CLI 一致。每个 job 只准备一个 `swe_gym_lite::getmoto__moto-N`，每个选择臂单独 `run --repeat 1`。`gold_input` 专用于导出的输入，臂结果写 `gold/`，不存在此前 6114 v3 的同名目录冲突。

四题均保留原 vendor 安装 `make init`。原 `spec_vendor.py` 对这四种 Moto revision 没有安装替换或测试选择器缩减；完整命令由原 eval 前缀与有效补丁文件派生，expected 与原件一致：

| 题 | 完整测试命令 | F2P / P2P | 控制臂数 |
| --- | --- | ---: | ---: |
| 5960 | `pytest -n0 -rA tests/test_dynamodb/test_dynamodb.py` | 3 / 155 | 3 |
| 6408 | `pytest -n0 -rA tests/test_ecr/test_ecr_boto3.py` | 1 / 95 | 3 |
| 6185 | `pytest -n0 -rA tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py` | 1 / 34 | 22 |
| 7584 | `pytest -n0 -rA tests/test_sns/test_application_boto3.py` | 1 / 19 | 11 |

合计 39 臂，各题名称无重复。`--controls` 只能选择该题已固定的臂，拒绝未知和重复名字，默认全部；结果明确保存实际选择，不能把子集结果写成 39 臂全验。

生产 spec 的 setup/apply/test 预算仍为 300/120/1800 秒，等于固定 manager 默认且有运行前比较；本工具保留候选 staging 900 秒、外层 grading 1800 秒、cleanup 120 秒、image inspect/pull 1800 秒的显式 CPU 编排预算。这里的外层 1800 秒是 `--grading-deadline-seconds` 显式参数，**原 CLI 该参数默认值为 3600 秒**，不能写成“原 CLI 默认就是 1800 秒”。这没有改 R13 内部预算或评分代码。profile 仍从原 API 构造并核 2 CPU、4 GiB、PID 512、grader shm 64 MiB；实际 HostConfig 及阶段耗时须运行后验收。

原 `prepared_task_face.py` 保留 trusted setup、candidate install/test、拆段交接和 Start/End 标记；原 manager 继续承担真实安装、测试和包供应的断网收口。工具没有提供替代测试、替代 parser、替代评分器或自行算 reward。仅凭工具退出 0 或 `matches_expected_reward` 仍不能确认安装完整或每条参考真实解析。

## source ID 与 COPY-only ID 的既有精确 override

| 题 | `run --derived-image` 的实际参数 | 含义 |
| --- | --- | --- |
| 5960 | `sha256:c67dbd356fcaa937ebff4b3fe0d78e4ea78211888233a4e5f07da95eddfe079d` | 登记 recipe 的 **source_config_id**；不是新派生镜像 |
| 6408 | `sha256:a0071858b0bb3a9c316e3c75dd49e9a3a2f8136f7bb4213e1210b44b7de2e689` | 登记 recipe 的 **source_config_id**；不是新派生镜像 |
| 6185 | `sha256:79d39d611186289b10956c2f845af1272218a1f4cf8fc00382c7c6ab4eced35d` | 登记 COPY-only 配方的 **actual derived ID** |
| 7584 | `sha256:990e0e91a190f85426e6900828cf758c30f389c927f6c1d0cd1ed8c68b902f96` | 登记 COPY-only 配方的 **actual derived ID** |

固定 `prepared_task_face.py:652` 起的 Moto 分支仅接受登记 source ref/manifest 与对应 local ID；无 derived ID 的题允许登记 source config ID，存在 derived ID 的题固定转到该 derived ID。固定 `adapters/slime/replay_grade.py:523` 起的分支，将显式 override 与 `derived_image_id or source_config_id` 精确比较，陌生 override 走 `explicit_override_not_registered`；随后按本地镜像身份进行 inspect、实际 ID 对账及 candidate/grader staging。这正是既有 R13 诊断路径，`--derived-image` 参数名不意味着 5960/6408 的镜像物理上已派生，不需要扩展公共契约。

工具在 prepare 前 inspect source manifest ref 并核 source config ID、RepoDigests、amd64/linux；6185/7584 另核 actual derived ID、来源层加一层及已登记的离线 wheel 环境。固定 actual ID 与 recipe 的完整字节绑定共同限制此路径。没有在本次实际 inspect 镜像，因此不把这些将执行的检查宣称为新宿主镜像已验。

构造的 `rollout_spec_from_view(..., time_budget_seconds=1800)` 只检查 source actor image 和 `grading_spec is None`，不执行真实 actor。工具保留 source actor 的公开镜像身份，并写 `actor_executed=false`、`model_attempts=0`。通过 grader/candidate 的 local override 验证，不能推出 source actor 的 UID、激活、安装或模型调用已通过；文件 patch 控制臂也不能因 CLI 的候选 kind 而称为真实 CC。

## 控制臂预期及清理

5960 的 `noop/gold/omit_keys_only` 预期为 `0/1/0`，6408 的 `noop/gold/reorder_only` 为 `0/1/0`。6185、7584 的 gold 明确是 `gold_known_incomplete`，预期 raw reward **0**；不能要求这些旧金标变成 1，也不能用其 0 直接认定环境失效。它们仍必须正常安装、执行完整测试并对账具体失败，基础设施失败不能冒充已知不完整金标的预期 0。

6185 的 `ctx/parity` 为预期 1 的正例，`ctx_list` 为预期 1 的 `alternative_compatibility`；`rv_dynamotype` 单独标注 **`observation_not_positive`，预期 raw reward 1**。工具在每行结果保留 `role`，没有把该观察臂重标为语义正例。7584 的 `stmt/stmt_arnmsg` 为预期 1，其他既定错误控制臂预期 0。上述角色与预期是固定诊断输入，实际奖励及失败依据要读原件，本次不重新审查其全套断言语义。

每臂要求 CLI rc 0、单一 ledger 行、`stage_error=null`、非空 report、actual image ID 相等、candidate `cleanup.removed=true`，原 CLI 最后摘要须 rows=1、halted/aborted 为空、final exit 0 且 cleanup failures 空。固定 ReplayGrader 的 finally 持久化候选工件并清理 candidate；原 CLI 的 finally 调用 manager.close，原 `final_exit_status` 对尚未确认关闭的评分容器给非零退出。编排随后按该臂唯一 `rh2.run_id` 同时查询自有容器和网络，要求查询成功且 stdout 空；查询失败不会被当成零残留。没有替换生产清理实现。包供应及 manager 的完整收口仍须在原件中检查；仅看 candidate removed 不够。

## 启动与后续验收边界

没有需要现在修复的具体阻断；固定工具可以启动。此结论不把其他题或 6114 的 CPU/UID 证据跨题继承，也不表示四题已完成正式 CPU 验收。启动会按原入口做发布材料及消费者核查；本地静态身份成立不代替远端运输、镜像 inspect 或实际调用记录。

后续按现有 CPU/actor 验收范围读回原件即可，无须增加新评分器或重复机械重跑：核实际选择与臂数、真实 CLI 命令/退出、完整安装文本及阶段交接、完整测试 Start/End/RC、参考解析和逐分区结果、对应具体断言的预期失败、运行镜像和资源限额、candidate 与 manager/supply 清理，以及自有双资源零残留。`result.json` 自身已写 `selected_controls_completed_pending_raw_and_independent_review` 和 `formal_cpu_accepted=false`。6185 的观察臂 raw 1、两题 gold raw 0、正常题目 reward 0 和 infrastructure failure 必须分别呈现；真实 actor 证据另行核实。

本报告为静态工具审查终稿；不承接 CPU 运行结果，不回写已固定的 Moto6114 报告或请求。
