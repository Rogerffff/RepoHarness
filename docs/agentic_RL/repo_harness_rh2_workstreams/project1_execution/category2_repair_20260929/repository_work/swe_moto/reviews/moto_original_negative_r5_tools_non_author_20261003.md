# Moto 5960 / 6408 原材料单反例 R5 工具非作者窄核

审查日期：2026-10-03。最终结论：**下列最终字节没有尚未修复的静态工具阻断，可按既定安排启动原材料单臂诊断。旧 reward 仍未知，本报告不授予修订 CPU 准入、actor 或训练资格。** 审查中发现的两处确定问题已由题主修复，修后状态列于下文。

## 范围与方法

本次独立核查 `tools/moto_original_negative_r5_v1/` 四文件，对照本地冻结 R5 原件 `runs/category2_repair_20260929/releases_20261003/r2e_078_079_swe7_git_candidate_v1/`。实际读取包括原 `replay_grade.py`、`ReplayGrader`、`grading/manager.py`、`training_view.py`、`swe_material_revisions.py`、`prepared_task_face.py`、`spec_vendor.py`、`sandbox_profile.py`，以及实际固定 prepare 入口的 public/private/environment 输出、vendor specs、两份反例 patch。用独立标准库读取计算 SHA、字节数、JSON canonical digest 和 AST；没有导入或执行 RH2 项目、SDK、Docker、远端、项目测试、CC 或模型。题主报告的 ruff 通过不是本次独立运行结果。

审查者已读私有评分材料及反例，**不是公开盲读者或盲 solver**。不重复判断两份反例的题级断言语义，也不把其他题、R13 修订材料或历史分数代入本次 R5 原评分。仅新增本报告；未改工具、冻结发布输入或既有报告。

## 最终输入身份

| 文件 | SHA256 | 字节数 |
| --- | --- | ---: |
| `manifest.json` | `fbf832aafaf0fa89cc2feb9a2b51bfeba77ad054cb76f846f4cfc1f645aa9a1c` | 597 |
| `original.py` | `a862e37b7402f6fd19718102c250be8dce1cf98d02fb0fbc93e708f24c64ac43` | 10564 |
| `tasks.json` | `4c3d56d631d448f5628200cfbf57baa9da21e8ff79d30bddea88708aab44a5cb` | 1672 |
| `expected_original.json` | `699b845a4be042900b536cdf206700baf621d3e8fb3c83fe7f79c6ca833ea951` | 24025 |

实际目录恰为四件；三项成员与 manifest 的 SHA/bytes 相符，均为普通文件、非符号链接。`original.py` 最终字节 AST 可解析。运行时还会拒绝文件集合、成员字节、R5 manifest、反例 patch 或解释器身份不符。manifest 自身最终 SHA 是本次外部固定身份；工具不以自列摘要代替它。

R5 release ID 为 `cat2-cpu-r2e078079-swe7-git-20261003-v1`，release manifest SHA 为 `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`。独立本地读取其 837 个 manifest 成员，合计 76211713 字节，全部 SHA/bytes 相符；`verify_release.py` 自身也与固定 manifest 相符。没有执行该校验器或重建 release。

| 题目 / 唯一控制臂 | 原 base commit | patch SHA256 / 字节数 |
| --- | --- | --- |
| 5960 / `omit_keys_only` | `d1e3f50756fdaaea498e8e47d5dcd56686e6ecdf` | `5ddf1b01fdf43ecf0bc1a18e6d20908ff20ae70737d01ea00324f3a52fb1c734` / 712 |
| 6408 / `reorder_only` | `1dfbeed5a72a4bd57361e44441d0d06af6a2e58a` | `38870a10babbb10239825686c1493cefdff753bf3d7a15db83f217de8321ee8b` / 290 |

两份 patch 的本地普通文件字节与 `tasks.json` 一致；其运输路径指向既定 preparation 包中的同一仓库相对路径。每次 `--instance` 只能选 5960 或 6408，该题只运行上述一臂、`--repeat 1`；job 名受题号及 12 位十六进制后缀约束，输出目录 `exist_ok=False`，不会覆写旧证据。

## 实际 prepare 消费者与 expected_original

不是仅按工具作者给的 `expected_original` 接受输入。原 CLI 的 `prepare` 调用 `prepare_for_replay` → `TrustedTaskController.from_repo_root` → `prepare_tasks`；原 `training_view.py:338` 的 SWE 默认入口为 `load_trusted_swe_revision_outputs(repo_root)`。R5 的 `swe_material_revisions.py:58–60` 实际固定生产目录为 `s2/ingest_mypy_monai_pyd_monai4583_moto5406_monai3715_v1`，manifest pin 为 `84e82a8219c215ce5f8711bbd7e3306d4af6217dc9c809ee1dc436bcc52352fd`；本地该目录实际 manifest 字节匹配。它不是直接挑任意最新原始 SWE 目录。

沿这个实际入口独立读取两题输出，按原 canonical JSON 规则计算 public、grading、environment digest，核 base、image/manifest、有效 test patch、完整 F2P/P2P 列表及无 revision 字段；全部与 `expected_original.json` 对应项一致。原加载器还包含固定 manifest 校验及确定性重放/输出字节比对，工具运行时由原 prepare 执行。两题在该 producer 中保持原 `rh2.private_grading_bundle.v2`，没有进入修订 grading bundle；原 `build_grading_spec_from_host_view` 因而生成 `grading_revision=None`，没有修订侧车或新评分器。

| 题目 | 原 grading / environment digest（去 `sha256:` 前缀） | 原有效 test patch SHA256 |
| --- | --- | --- |
| 5960 | `fa4ba69954e65a356d8e22967a044d0ec8902b00c07bbeeb5d9cfbf6b0184b39` / `6d84edbbd54a839d8cd1a74bdfdf1cb1ef38a29a0aedd8840a4e8c4b2ab793f7` | `dbfb73e7e49a7daa4d697ee17a0b078c2c244c6c4596a406d90f850a36dd0332` |
| 6408 | `88036280e7c4ef3f127a78b9cd8a24749221db1f1d80dd5e539295037d41348b` / `aebaf77976169369e06f4b9c1dbab5a322e1f73b64792d0267cba6f5703b802a` | `664a622eadf5a424ba3142d16546afa00b0bb896b534526260e258046fe0a853` |

另外独立核原 vendor specs 的版本选择、安装项及 eval 前缀，并按原 test patch 路径派生规则核完整命令：两题均为 `make init`；5960 为 `pytest -n0 -rA tests/test_dynamodb/test_dynamodb.py`，6408 为 `pytest -n0 -rA tests/test_ecr/test_ecr_boto3.py`。原参考列表分别为 2 F2P / 155 P2P、1 F2P / 95 P2P，完整列表逐项匹配；这些是参考列表数量，尚不是本次实际测试解析数量。没有改用 `-k`、只跑新增断言或替换参考集。

工具 `original.py:104–125` 使用原 `load_context`、原 spec 构造及安装/测试派生 API，先保存实际消费读回，再对整个 expected 字典相等校验。API 参数与 R5 定义相容；不存在借 R13 消费者替换 R5 的情况。

## CLI、source 身份、资源和预算

原 `prepare` 的 `--repo-root`、`--out-dir`、`--private-dir`、`--task-ids` 参数和原 `run` 的 prepared summary、patch candidate、repeat、预算、ledger/artifacts/eval logs 参数均存在且语义相容。工具使用 R5 自己的 CLI/代码路径，清除两项 `RH2_IMAGE_OVERLAYS_*` 环境变量；不传 `--derived-image` 或 overlay，不导出 gold。

source image 分别为 `xingyaoww/sweb.eval.x86_64.getmoto_s_moto-5960:latest`、`xingyaoww/sweb.eval.x86_64.getmoto_s_moto-6408:latest`，固定 manifest 分别为 `sha256:4b71766331736b51bd74bb86cdb5e4e21040a7816e01fbb5d914526d33ef8944`、`sha256:db52bf5253616c8662863703accf3ad9e5c20e809e63f2e5829b48fb1212f8a4`。前置只读 image inspect 同时核 manifest ref 和原 tag，二者 Config ID 必须分别等于：

- 5960：`sha256:c67dbd356fcaa937ebff4b3fe0d78e4ea78211888233a4e5f07da95eddfe079d`。
- 6408：`sha256:a0071858b0bb3a9c316e3c75dd49e9a3a2f8136f7bb4213e1210b44b7de2e689`。

这两项仅用于原来源镜像身份核对，不进入 diagnostic local override。前置 inspect 原件不等于 ledger 已记录评分运行时物理 ID；原 manager 仍按 source manifest 的 RepoDigests 路径核评分镜像。实际运行身份需读回 runtime 原件。

原 rollout/grader profile API 相容，静态检查 2 CPU、4 GiB、PID 512，grader 额外检查 shm 64 MiB；没有访问 rollout profile 不存在的 shm 字段。没有运行 rollout/CC。原 spec 内 setup/apply/test 预算为 300/120/1800 秒；CLI candidate/cleanup/image-pull 为 900/120/1800 秒。外层 grading deadline 显式传 1800 秒，工具 scope 已准确注明这是本次诊断参数，原 CLI 默认为 3600 秒；不把它表述为默认预算完全未变。超时只形成基础设施失败，不能据此推断旧 reward。

## 发现、修复与失败边界

1. **首次阻断：非空 report 仍可能不是语义评分。已关闭。** R5 `grading/manager.py:2161` 附近捕获 `GradingInfraError` 后返回 `outcome='failed_to_grade'`、`reward=None` 的 report；`ReplayGrader:672–692` 可正常接收它，留下 `stage_error=None`，原 CLI 在完整清理后也可退出 0。旧工具仅检查 stage_error 空及 report 非空，可能把此类结果写成完成的旧评分。题主已在最终 `original.py:142–145` 增加原 report 的三项筛选：outcome 只能为 resolved/unresolved，failure_category 只能为 None/tests_failed，reward 只能为 0/1。失败原件保留并非零结束，不将 infra/解析失败算作原反例得分。该 guard 不调整原 reward、参考集或评分规则。
2. **第二阻断：source 分支没有 ledger actual ID。已关闭。** R5 `ReplayGrader:508` 初始化 `image_id_actual=None`，只有 derived 分支在 544–571 行写物理 ID；本次原 source 路径不会填这个字段。旧的“actual ID 等于 source Config ID”条件会确定拒绝正常 source 评分。最终 `original.py:146–149` 改核原 image ref/manifest、`image_local_build=False`、`image_id_actual=None`、overlay/derived recipe/revision 全为 None，并配合前置双 ref physical inspect。没有为补字段而切到 R13 exact local override，没有伪称前置 ID 是 ledger runtime ID。

题主先前将 import 展开仅为格式修正，已核不改变 AST 语义；随后正常 report guard 及上述 source 分支修复形成当前最终字节。`tasks.json` 与 `expected_original.json` 字节未改变。两个 `expected_reward` 仍为 null；正常 reward 0 或 1 都只记录为观察值，均不预设“原材料反例应当通过”。

## 清理与后续原件验收

原 ReplayGrader 保留候选 finally 清理及证据，原 CLI 无论正常、异常或取消均在 finally 调用 `manager.close()`，输出包含 manager close、halted、aborted、cleanup failures、final status 的 footer。工具 require 原 CLI rc 0、唯一账本行、无 stage_error、正常 report、正确 source 账本身份、候选 `cleanup.removed=True`，再核最后 footer 的 rows=1、halted/aborted 空、final exit=0、cleanup failures 空。

工具之后仅按本次 `rh2.run_id` 查询自有容器/网络；每项要求 Docker 查询返回 0 且 stdout 为空，查询失败不会当作零残留。查询原件包含 rc/stdout/stderr。它不删除其他作业对象，不在入口失败后自动重跑；完整结果仅在这些检查后写成 `original_counterexample_completed_pending_raw_readback`。CLI rc 0 只证明入口正常收口，不能单独证明测试通过。

这些静态检查允许启动，**实际 reward、完整安装/测试输出、测试解析和原参考集结果、实际镜像/资源、patch hygiene、候选及 manager 双层清理、最终 footer 和自有资源查询仍须从本次原件验收**。未开始的入槽返回 75 不属于评分失败样本。本报告没有任何本次 CPU 运行事实，不要求机械扩大控制臂或重跑模型；只保留本次单臂诊断必需的原件读回边界。

`rollout_spec_from_view` 在此仅构造公开输入边界检查对象，不能算真实 actor。原 ReplayGrader 内部冻结候选供评分消费是既有链路行为，本工具不执行自主求解、模型调用、CC、训练或对外 FrozenPatch 导出；scope/result 明确 `formal_cpu_accepted=False`、`actor_executed=False`、`model_attempts=0`。本次观察不替代修订材料 R13 的 CPU 验收，也不授予 typed actor 或训练资格。
