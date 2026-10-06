# Moto5960/6408 R18 离线矩阵与 UID 安装工具：非作者启动前窄核

日期：2026-10-03。**矩阵工具未发现静态启动阻断；追加的 UID 安装工具也未发现静态启动阻断。** 两者可在既定排队条件满足后启动。当前 7584 在途作业须自然结束，此结论不授权抢槽、取消在途作业或提前派发。这里没有新安装、CPU、actor 或训练准入结论，也没有把旧 R13 结果改成新 R18 结果。

## 读取范围与方法

审查者不是工具作者，已接触 Moto 私有参考、控制补丁和金标上下文，不是公开盲读 solver。本次只做本地标准库文本、JSON、SHA/bytes、AST 和差异核对；没有导入或运行项目、SDK、测试、Docker、CPU、模型，也没有连接远端。只新增本报告，不修改工具、冻结发布输入、共享实现、旧运行原件或既有报告。

实际读取的主要入口：

- `tools/moto_two_r18_offline_matrix_v1/` 四件，以及已审 `tools/moto_four_r13_matrix_v2/` 对照；既有静态结论见 `reviews/moto_four_r13_matrix_v2_tools_non_author_20261003.md`。
- `runs/category2_repair_20260929/releases_20261003/r2e_093_swe40_moto_offline_v1/` 的 manifest、1419 个发布成员、producer 两题 public/grading/environment 行、两份 registry/recipe、直接环境资产和实际消费源码；只读取相关 API，不重审题级测试语义。
- `runs/category2_repair_20260929/moto_cpu_20261003/local_r18_prepare_v1/` 的六份 prepare/expected 原件，及两份供应 receipt 指向的 source/derived inspect、实际 UID54321 wheel stat 和 HostConfig 原件。
- 新矩阵 launcher `runs/category2_repair_20260929/moto_cpu_20261003/launch_moto_two_r18_offline_v1.py` 的静态 AST、固定值、参数、运输校验、入槽命令和输出路径；既有本地 `host_setup_20261003/cpu-a/cpu_slot.py` 作为合作式入槽接口源码对照，不将其当作远端当前状态快照。
- 追加 `tools/moto_two_r18_offline_uid_install_v1/` 三件、已审 `tools/moto_four_r13_uid_v1/`、新 UID launcher，以及原公开 base 的两份 Makefile 和指定模块原件。

没有输出 launcher 的 host、key、SSH argv 或连接错误原文；报告也不包含这些私有连接资料。

## 固定字节

矩阵目录成员集合精确为四件，成员不是符号链接，manifest 中 SHA/bytes 全部匹配；`matrix.py` 的 `ast.parse` 成功。

| 文件 | SHA-256 | bytes |
| --- | --- | ---: |
| `matrix/manifest.json` | `58e4b113ef1b98c3f5ce3df56cb7a654b9c2f4d425bd5f6b65e8c21eb49457d0` | 649 |
| `matrix/matrix.py` | `1d316868cc1e150415785ccdc7dc55104ae355951b5d7d51ec06ecd47aabe38b` | 13462 |
| `matrix/tasks.json` | `49dc8580efafb0db22b7dacf917a1dc7c48cb8363a34ca0654762a007147b83f` | 11516 |
| `matrix/expected_runtime.json` | `461859e46648fff4f08177df46835d46960158355dc95fbca90a33e7cd8319b5` | 29010 |
| 矩阵 launcher | `e9dd80883d2b7dbabb6f20b2b1a9af84f3851a5de6b0df187d06c26f2d166c37` | 7010 |

表中 `matrix/` 指 `tools/moto_two_r18_offline_matrix_v1/`，不是新增子目录。完整代码 diff 确认，对已审 R13 v2 的 `matrix.py`，变化只有说明文字、`--instance` choices 从四题缩为 `5960/6408`、输出根目录从 `moto_r13_v1` 改为 `moto_r18_offline_v1`。正常评分 guard、候选循环、CLI 参数、预算和清理代码没有变化。

固定 release 为 `cat2-cpu-r2e093-swe40-moto-offline-20261003-v1`，manifest SHA 为 `a84bdc339618e010440df3728c982b2d1d141b1f8295f69761984386ee3a512e`。独立读取全部 1419 个 manifest 成员，合计 156284020 bytes，逐件 SHA/bytes 匹配。producer 为 `docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest_swe40_moto_offline_environment_20261003_v1`，其 manifest SHA `efdc7f639a3d312ae071d3a3dd1ccbc93eb819fedda2d9453012e5d312f22acb` 与配置及实物匹配。

## 原 public、评分材料与新 ENV 的关系

新 producer 中两题 public 行与 R13 producer 对应行完全相等。两题 grading 行除 `revision.environment` 与 `revision.registry_sha256` 外全部相等：原题面、base、原参考与顺序、effective test patch、原 patch、revision ID、parent grading digest、vendor/python/eval 字段都保留。两题 controls 和 budget 对象与已审 v2 完全相等；五份评分脚本 SHA 字典、完整 test 命令和 `context.partitions` 也完全相等。

| 题 | base | 参考 | 三个既有控制臂及 planned reward |
| --- | --- | --- | --- |
| 5960 | `d1e3f50756fdaaea498e8e47d5dcd56686e6ecdf` | 3F/155P | noop 0、gold 1、omit_keys_only 0 |
| 6408 | `1dfbeed5a72a4bd57361e44441d0d06af6a2e58a` | 1F/95P | noop 0、gold 1、reorder_only 0 |

gold/negative 控制补丁是原 bytes，已核路径、SHA 和长度：5960 gold `df2af6b800578dc24b6ef33c396677683d766702734f44d506248354147b7af9`/593B，omit `5ddf1b01fdf43ecf0bc1a18e6d20908ff20ae70737d01ea00324f3a52fb1c734`/712B；6408 gold `fa6d9adadc553b4eb713ca3749a90efe7adb572348c837fd2bbf48a3dd95d7dd`/993B，reorder `38870a10babbb10239825686c1493cefdff753bf3d7a15db83f217de8321ee8b`/290B。noop 无 patch。这些期望是待运行的对照目标，不表示本次六臂已跑，也没有据此填补旧 R5 反例未知得分。

原预算仍为 setup 300s、apply 120s、test 1800s、candidate stage 900s、whole grading 1800s、cleanup 120s、image pull 1800s。公开 source image 和原 manifest 保留，但 ENV 登记和由此形成的新 grading/environment/materials 摘要已改变，不能沿用旧身份称为同一次运行：

| 字段 | 5960 | 6408 |
| --- | --- | --- |
| registry SHA | `149b3cd74abc6c3293f9ef01527a15c621fa0f6ae7bf0ac4f36188e976c4fc7d` | `6b8864f0912219fdfd1cbfc5d5161544c5fdf57f9baa05ed53dc041c4d38a013` |
| recipe SHA | `cce02f039f9af572c88ccc22bc913180939a61bac7fb3de8846cbb360b2a2664` | `26be33584f80834e8ef039493efc1296ad29b61967d2720be1995185b2e78e07` |
| 新 grading digest（`sha256:` 省略） | `7368a4e18b0d4b6f3605e3e1ff913e4e74b650f01c75cf7ca5530e1624e02292` | `567ba1e2c71fa772cb3ac2e112ad1a7fb196056ca57ea1fa0b01a1b13a7dc0ae` |
| 新 environment digest（`sha256:` 省略） | `508c321ed4834474fcdf780e3411bf26aff718a2bde916f64fbf4e61e54f8c19` | `fc3f039787ba630fe6b8a80f5a4022fea3eb418b70219f9f57b3fe76933c8f08` |
| 新 materials identity（`sha256:` 省略） | `0fb164e025a6f9ef9298b7edcb0a013ac2260dad1fcbab71c80e5d66f592f8cc` | `7d6fc3219336eddad6b46bd7ac8d2bf4c59e9885fa87f36c3c37a1fee5453049` |

5960 registry 路径是 `s2/revisions/moto5960_offline_environment_v1`，6408 是 `s2/revisions/moto6408_offline_environment_v1`；两者均位于固定 release 的 docs workstream 根下。recipe 及每题九个直接环境资产的 SHA 均核对到实物，包含对应 request、build/root acceptance receipt、source receipt、Dockerfile、wheel manifest 和三件历史 wheel；没有把 6408 source 借给 5960。

5960 source ConfigID 为 `sha256:c67dbd356fcaa937ebff4b3fe0d78e4ea78211888233a4e5f07da95eddfe079d`，source manifest 为 `sha256:4b71766331736b51bd74bb86cdb5e4e21040a7816e01fbb5d914526d33ef8944`，本次登记 actual derived ID 为 `sha256:4bafbb6965ff41c0f6eb50a73f831e7b62c41b5beda6ffad957fbc926c2359ac`。6408 source ConfigID 为 `sha256:a0071858b0bb3a9c316e3c75dd49e9a3a2f8136f7bb4213e1210b44b7de2e689`，source manifest 为 `sha256:db52bf5253616c8662863703accf3ad9e5c20e809e63f2e5829b48fb1212f8a4`，登记 derived ID 为 `sha256:f00e022c3edf2dd23121abab802e401a64ee9e98598f07fb37a83d5c4c2012a1`。

两份 build receipt 与 root acceptance 指向的原 receipt 字节一致；独立读 source/derived inspect 后核实 source 13 层是 derived 14 层的完整前缀，派生 Config 的 `PIP_NO_INDEX=1`、`PIP_FIND_LINKS=/opt/rh2/build-wheels` 正确。原实际 UID/GID54321 stat 中 `/opt`、`/opt/rh2`、wheel 目录为 root:root 0755，三件 wheel 为 root:root 0644；它们实际读出的 SHA/bytes 与本次三件历史 wheel 相符。对应原供应用容器为 network none、2CPU/4GiB/PID512/shm64MiB。此处只确认供应身份和已有受限可读证据，不把它升级为安装或项目测试通过；receipt 自身也保留该边界。

## prepare 和 R18 实际消费源码

`local_r18_prepare_v1/expected_runtime.json` 与工具 expected 文件逐字节相等。prepared manifest SHA 为 `58c1b60353c52f232b310ea729ab2946511347a1236c091d9275ad617bc85e00`；其 prompts/rollout 两件各两行的 SHA、host grading 工件 SHA/两行数及 summary 关联均匹配。两题 public/grading prepared payload 与 R18 producer 对应行完全相等，public/grading/environment 的 canonical digest 也与 prepared 及工具 expected 相等。

原 rollout 消费仍返回公开 source image、`grading_spec=None`，没有给 actor 私有测试或答案。host grading 的 environment 是封闭模型的字段子集，与 registry 对象相等，`asset_sha256` 指向完整 recipe SHA；其余字段逐项对应工具 recipe，不能要求它包含 recipe 的附属说明字段。

固定 R18 `bundles_v2.py` 的两类 Moto Environment 已将上述 recipe/source/derived ID/三件 wheel 字节封闭登记。实际 `prepared_task_face.py` 中 `moto_fixed_revision_environment` 支持两题，`build_grading_spec_from_host_view` 接受精确 source+manifest 或登记 derived ID+None，将评分 spec 的 image、`image_local_build_id` 绑定为新 derived ID；陌生覆盖拒绝。`ReplayGrader` 按登记 derived ID inspect、比对实际 ID 后才记录 ledger 实际 ID。因此本次 CLI 的 `--derived-image` 传入两题新 actual derived ID，并附对应 recipe ID，是 R18 已登记消费路径；不再传旧 R13 的 source ConfigID，也未新增公共 overlay 契约。

原 API `prepare/export-gold/run` 参数在固定 CLI 中存在，export-gold 仍从固定 producer 导出并核原 gold SHA；输入目录 `gold_input` 与候选 `gold` 结果目录分开。仍完整运行 `make init`，测试串分别为 `pytest -n0 -rA tests/test_dynamodb/test_dynamodb.py` 和 `pytest -n0 -rA tests/test_ecr/test_ecr_boto3.py`。预算使用原生产字段并在启动 run 前比较。五份脚本摘要保持；R18 登记派生 ENV 还使既有 Moto candidate prerequisite 在 UID54322 核 pip ENV 与三件 wheel SHA/bytes，该前置检查不安装、不导入项目，不是新评分器或替代测试。

每 job 只跑一题，默认三臂串行；`--controls` 仅允许该题既有控制，未知或重复拒绝，允许 5960 先 noop 再独立 job 补 gold/omit。结果只标记待原件及独立读回，不自行授予 formal CPU。原正常评分 guard 仍要求 `stage_error=null`、非空 report、outcome 为 resolved/unresolved、failure category 为 null/tests_failed、reward 为 0/1；不能把 failed_to_grade/null reward 当普通反例。候选移除、原 CLI footer/退出和 manager cleanup failures、按自有 run label 查询容器/网络均被检查；query 非零不会当成零残留。

**安装退出码仍需实际原件检查。** R13 已证实安装 rc2 时，后续 pytest 仍可能形成正常 report/reward，CLI 包装与 pytest 退出码也不是同一含义。本工具的 guard 没有改这个原消费行为。启动后必须逐臂读安装、完整测试、逐参考、实际镜像、候选与 manager 清理以及 slot/job 终结；不能仅凭矩阵 rc0、reward 符合期望或 planned 值称为 CPU 验收通过。此限制沿用既有审查，不在这里增设评分契约。

## 矩阵 launcher

launcher 固定 R18 release ID/SHA、四件工具 manifest SHA、仓库源目录、远端工具/输出根、`runtime_cpu_v2/rh2/.venv/bin/python` 与 `PYTHONPATH=<固定R18>/repo/rh2/src`。公开参数只有 `--instance`、`--execute`、`--controls`，没有连接参数；本地四件身份先核，远端运输程序只接受缺失成员或同 pin 现存成员，拒绝额外成员/符号链接/字节冲突，运输后复核并将文件/目录设为 0444/0555。receipt 只含数量、字节校验与工具 manifest SHA。

job 使用新 UUID 的题别 `motoN-bind/cpu-<12hex>`，矩阵输出使用新 `moto_r18_offline_v1`，已有目录拒绝覆盖。执行通过原 `control/cpu_slot.py --mode run --package swe_moto --job …`，清除两项 overlay 环境变量。合作式 slot 代码对暂停、磁盘/内存不足或槽锁占用返回75，在取得非阻塞锁后才派发并保留 status/stdout/stderr，finally 释放锁；launcher 没有绕过锁、prune 或中断在途作业。

运输/连接失败的终端输出只含阶段、成员或 rc；异常输出只含类型和固定脱敏说明。实际连接 stdout/stderr 仅保存在自有忽略作业日志，未打印；invocation 保存的是 CPU 子命令，不是 SSH argv。它没有自动等待特定7584 job结束的逻辑，也没有读取远端当前槽状态来作本次静态证明，仍由题主遵守已经确定的排队顺序；本审查没有启动 launcher。

## 追加 R18 UID 安装工具

三件成员集合、非符号链接、manifest SHA/bytes 和 AST 均核对成功：

| 文件 | SHA-256 | bytes |
| --- | --- | ---: |
| `uid/manifest.json` | `7761a5da501bdc76aaf804cc6a05ac9f3b0c1e0e4193f9248670d98c0cd41560` | 508 |
| `uid/uid.py` | `309632940f15a97890ae76cd19a27784eafbc1cd443ca1cdc1ebde2108c836d1` | 10709 |
| `uid/tasks.json` | `53eda943984916cfeb0ab5bbf00ebdaed4b5a058972866786fee46af5eae469e` | 8932 |
| UID launcher | `3de61c034fc3d82c6de1244f6d987b3ce7525ac127dbb8edb6ab8141d118e6c7` | 7613 |

`uid/` 指 `tools/moto_two_r18_offline_uid_install_v1/`。对已审修后 R13 uid，代码变化为题目 choices 缩两题、新 prepared/output 根、说明/status 文句，以及在激活完成后、模块探针前追加原 `make init`。配置保留原 base/public/source face/模块身份，只改为 R18 release/ENV/package/runtime ID、限定安装 scope 和 `public_install_command`。两题 task/ENV/runtime/package 与本报告矩阵/prepare 逐项匹配。

原公开 base Makefile 的 `init` 确实只有 `pip install -e .` 与 `pip install -r requirements-dev.txt`；工具执行 `cd /testbed && PYTHONDONTWRITEBYTECODE=1 make init`，没有改命令或预装依赖。先用 R18 原 `run_git_sanitize`/`run_trusted_init`，从 `repoharness2.envpack.materialize` 正确取得 `BASH_ENV_PATH`，root 写原 spec 激活内容、0644；原 `agent_shell_env` 令 HOME 在 bash 启动前设为 `/home/agent` 并提供 BASH_ENV，原 activation helper 核解释器。接着 Docker exec 以实际 profile agent UID54321、同 HOME/BASH_ENV 环境调用公开安装，单调用上限仍300秒。正常返回的全部 stdout/stderr/exit 同时进入 Docker calls 原件和 `public_development_install`，非零退出立即失败，后面的模块探针不执行。没有运行私有测试、修改评分脚本、执行 CC/model/freeze/grade 或预装替代原安装。

安装成功后才用激活的 `python` 读取 UID/GID/cwd/HOME/解释器、Moto 与指定工作区模块、SHA、boto3/botocore 版本；模块固定 SHA 来自原公开 base，未换成控制补丁：5960 `moto/dynamodb/models/__init__.py` 为 `fba195aa3985edf3616237b965aefae6ea6845c9d2591f3d814d094dd70882fc`/29677B；6408 `moto/ecr/models.py` 为 `4df8182f9651cc5ef40ecac5defd993da7e9277e241de403b189c9b41658dc70`/40991B。本次已独立读 hash。SDK 是实际记录字段，没有固定额外版本判据；不能借6114的1.35.9跨题宣称版本已验。

profile 使用原 agent/54321、2CPU/4GiB/PID512；不访问 rollout 不存在的 `shm_size_bytes` 属性。实际 Docker inspect 再核 ShmSize=64MiB、network none、资源值和新 runtime ID。它保留公开 source spec 和 `grading_spec=None`，诊断容器显式使用已登记 COPY-only derived ID，并分别记录 source face/runtime。这个新的真实 UID 公开安装操作可以补开发环境证据，不能凭该工具授予真实 CC、全 actor 链或训练 typed-actor 资格。

finally 仅 inspect 自己命名的容器、核 run label 后删除，再按自有标签分别查询容器和网络；无全局 prune，不删镜像或别人的网络。返回调用完整记录，非零/超时/所有权不符/删除失败均不能正常通过，双 query 必须各 rc0 且空输出。继承旧工具的读回边界仍存在：超时的未返回调用可能没有完整输出/退出记录；finally 中断时也可能没有完整最终 result。`result.json` 又在末尾双 query 断言前写入，cleanup 失败时较早的 passed status 不能单独证明成功。必须核 job 实际退出、所有调用、安装退出/完整输出、identity、实际 inspect、cleanup 和正常 footer；缺件或异常按未验证处理，不把其当零残留或成功安装。这些路径失败即停，没有具体误授予成功的静态启动阻断。

新 UID launcher 固定三件工具/R18 release/SHA/runtime/new output，公开参数仅题目与 `--cpu-job`，没有连接参数。它要求同题 CPU invocation 为 execute=true，**external release manifest SHA 精确等于 R18**，且运输 receipt 字节校验成立/job rc0；从该 CPU evidence 的 prepared summary 实物计算 SHA，把对应远端 summary 路径与 SHA 传给 uid。uid 限 summary 在 `moto_r18_offline_v1` 下、核唯一 task 和原 load_context 的 manifest/private 关联，再比较新 package/public/base。因此不能静默复用旧 R13 prepared 条件。其运输、脱敏输出和原 slot 派发边界与矩阵 launcher 一致。

## 分开的结论与未完成项

1. **R18 矩阵：无本次静态启动阻断。** 原控制臂、评分、预算、public/base/refs/scripts 保留，新供应在 R18 真实 consumer 中登记并绑定实际 derived ID。可按既定顺序进行5960 noop预检，再独立补 gold/omit；6408可跑既定三臂。本次未派发任何作业。
2. **R18 UID 安装补查：无本次静态启动阻断。** 正确追加实际 UID54321 的原公开安装并绑定 R18 prepared，返回输出和失败/清理路径可供独立读回。仍须本次原件证明实际安装成功、模块/SDK来源、profile、清理及最终退出。
3. **验收尚未由本报告完成。** 三件 wheel 可读和 registry 正确不等于原 `make init` 能完全离线成功；只有新运行的完整安装、测试/参考和清理原件才能给两题 CPU 结论。UID 补查也不能替代正式评分、公开真实 CC 或训练资格。旧 R13 安装失败观察、旧 R5 未知反例得分和所有历史原件均保持原状。
