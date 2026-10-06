# Moto6114 历史公开开发路径复用非作者窄核

2026-10-03。审查者：Codex 非作者 subagent。只读本题历史真实 CC 原件、当前供应对照和所需固定源码，不运行远端、项目、SDK、测试或 Docker。已接触私有修订及对照材料，**不是公开盲读者**；本轮不重审新断言语义。仅新增本报告，不修改题主材料或既有静态报告。

**结论：历史三条公开开发命令有完整、相互对应的真实 CC 执行证据，可以在本次公开内容、base、来源镜像及 COPY-only 供应条件相同且新宿主 UID／激活／导入补查实际通过后，按下述范围复用。无需机械重跑三条命令。** 新 UID smoke 尚未运行，当前只能认定历史证据有效和复用条件明确，不能记作本次 actor 开发验收已完成。两项历史 false 标志仍保留为 false；它们不否定三条命令的实际结果，也不构成全套 CC 安全检查全通过的依据。

该复用只覆盖“真实 CC 能执行这三条公开命令，历史 base 的目标现象可复现、原公开测试可运行”。历史 CC 使用桩返回指定 Bash 调用，首个实际请求是 `Devcheck run: execute exactly the tool calls you are given, then stop.`，并非基座模型自主求解或公开题面理解测试；旧 devcheck 没有冻结导出。不能称本次 fresh CC actor、公开题面渲染／模型理解、候选冻结或 actor→grader（a2g）通过。

## 原件对账

历史根目录：`runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-6114/mixed-v1/actor_revised/`。`actor_revised` 是历史目录名称，不能从该名称推断本次修订私有测试曾进入 actor。

- `attempt.json` SHA `33d42995eec21a7ee06bfaaa7a899f7c7c1ac621dc38e02565593142fb714856` 与 [条件记录](moto6114_historical_actor_conditions_20261003.json) 相符；`public_commands.json` SHA `c102412f815fea5a87c99dc8b686eddbe32c1d63bef7925939c7a0ec5416539a` 也相符。命令清单与 attempt 内清单逐项相等。
- 三个实际 `assistant` Bash 调用与 `stub_script.json` 的工具输入逐项相等；按 shell 引号规则拆开外层包装，三条 `timeout -k 10 240 bash -c <命令>` 内的命令分别与原清单逐字相同。三个 CC `tool_result` 的 ID 逐个对应其 `tool_use`，rc 标记为 0／1／0。
- 原 trajectory 为 26,020 字节，与 attempt 和 host harness 日志长度一致，JSONL 全部可解析；包含 3 次 Bash、3 个对应结果、4 次 message_start 和 1 个最终 success result，harness rc0、stderr 为空。4 次 message_start 与保存的桩请求数一致。真实 CC 版本原件为 `2.1.205 (Claude Code)`。
- 三份完整 capture 长度为 177／766／2,879 字节，均等于 attempt 的 `output_bytes`，均小于 200,000 字节截留上限，没有因该上限丢尾。CC 对公开测试只回传尾部，完整 collection 与汇总以 capture 为准。

| 公开命令 | 完整原件中的实际结果 | 可复用结论及限制 |
| --- | --- | --- |
| identity | rc0；`PY_CHECK /opt/miniconda3/envs/testbed/bin/python`，`IDENTITY 54321 /testbed /home/agent`，boto3／botocore 均 `1.35.9`，Moto 从 `/testbed/moto/__init__.py` 导入，HEAD 为 `f01709f9ba656e7cf4399bcd1a0a07fd134b0aec`。这些关键内容也实际出现在 CC tool_result。 | 历史 CC 的实际工具进程使用预期 UID、HOME、工作区、解释器及本地源码，不只是宿主预检成功。新宿主相同条件仍待本次原件补查。 |
| target_identity | rc1；已经创建 A／B 两个集群，B 的实际 ARN 为查询参数；名称查询的数量检查已完成，打印 `EXPECTED_TARGET cpu-cluster-b ...` 后，在 `describe_db_clusters(DBClusterIdentifier=target['DBClusterArn'])` 抛 `DBClusterNotFoundFault`。 | 这是预期的 base 功能失败，不是 SDK／导入／超时错误；ARN 查询没有返回到后续身份断言，因此不能称 ARN 身份断言已通过。无需在不变 base 上机械再次复现相同失败。 |
| public_existing | rc0；完整命令为 `python -m pytest -n0 -rA tests/test_rds/test_rds_clusters.py -k 'describe_db_cluster'`（保留原测试环境变量）。collection 35 项，选中 4、未选中 31；4 条全部通过，21 warnings。 | 四条为 initial、fails_for_non_existent_cluster、after_creation、snapshots。这里运行的是 actor 的公开 base 测试，不是本次私有有效测试补丁或完整评分选集；4 通过不能替代新版 35 参考验收。 |

`post_run_facts_root.txt` 与 attempt 都记录 Git status 0 行、agent 进程 0、harness／launcher／done marker 不在容器。另记录 172 个较新的文件／目录，展示内容包含 Python `__pycache__`；本次不把它解释成“运行无任何副作用”。清理记录中的 container_rm=0、network／relay failures 为空、自有容器和网络列表及 `residual_after_force` 均为空；历史 collector 对查询失败会写 `<...query_failed>`，此处没有该占位符。以上只证明历史作业按原记录收口。

## 两个 false 标志的准确边界

以下依据历史固定工具 `runs/swegym_cpu_preprobe_20260929/frozen_code_v1/rh2/experiments/`，未运行这些工具。

**`interpreter_in_tool_result=false`：通用模板的标记匹配未命中，不能解释成历史解释器错误。** `base_probe_fixes_20260923/acceptance_startup_2.py:330`–`:334` 只搜索 `RH2_SYS_EXECUTABLE=<prefix>/`。本题 identity 命令打印 `PY_CHECK <sys.executable>`，实际 capture 和 CC tool_result 都是正确 conda 路径，三份结果没有 `RH2_SYS_EXECUTABLE=` 字样。`task2_swegym_dev_20260925/devcheck.py:178` 只是保留父类该布尔值，注释提到 PY_CHECK 并没有实现另一种匹配。记录必须保留 false，并以本题实际 identity 原件解释其含义；不能静默改 true。

**`bashenv_denied_for_agent=false`：本题三条公开命令没有在 CC 通道执行那项写拒绝检查。** 通用模板 `acceptance_startup_2.py:346` 寻找 `RH2_BASHENV_WRITE=DENIED`；三条命令和实际 CC 结果均无该标记。它不表示尝试写入成功，也不证明 CC 通道已实际测试写拒绝。

独立原 `prelaunch.json` 提供另一阶段的事实：UID／GID 为 54321，`ACTIVATION_READ=1`、`ACTIVATION_WRITE=DENIED`、`ACTIVATION_STAT=0:644`，隐藏 `/root` 为 DENIED；attempt 的激活写入阶段记录文件／目录属主权限 `0:644`／`0:755`。`activation_check.json` 为 ok、无 violations，解释器和 prefix 都是 conda testbed。这些支持**历史启动预检阶段**的可读／不可写及激活条件；不能改称“历史 CC tool_result 内的写拒绝标记已通过”，更不能用来证明本次全部安全边界。

## 供应相同与物理镜像不同

[供应读回](moto6114_historical_actor_supply_readback_20261003.json) SHA `ef9c3aba51c2a2eae237e8d098d106effd3924904009d3a4427be51b4b08679b` 与条件记录引用相符。它列出的 7 件原件 SHA／长度全部重新核对匹配；本轮进一步读取来源／派生 inspect、Dockerfile、wheel manifest 和当前两份供应 receipt，而非只接受 `all_supply_conditions_match=true`。

| 条件 | 本轮具体核对 |
| --- | --- |
| 公开内容与 base | 历史 `remote/prepared/v1/rollout_task_views.jsonl` 的本题 `public` 与固定 R7 producer 的本题 public 作为解码 JSON 对象完全相同；public digest 均为 `sha256:6c8f45da003f8e8d1e065d1801afa4659c43cbb212e319a5d07a84922af5f0f2`。base 及来源 manifest 与历史 attempt、当前 expected 一致。 |
| 来源镜像 | 历史 original_image、历史 build 的 base、当前 source receipt 和当前 derived receipt 都指向 base ID `sha256:fefec492f58ed0f8385a7e72234d296bd84d295031ce7e019f63fc33973ec249`；历史 RepoDigests 包含当前固定来源引用，其 manifest 为 `sha256:cb35f7e131f8e46c8a6865e8fb618c09032ce5ee27f1122f79010a7cfae8ef9a`。 |
| COPY-only 配方 | 历史实际 Dockerfile SHA 与当前 receipt 相同：`352caaf2eae8dc6fdb3291e9afaf85281a0b0199d6b3ee091d9e3d3247d44993`。仅复制 wheels 到 `/opt/rh2/build-wheels/` 并设置离线 pip 环境，无 RUN；历史 inspect 保留全部 base 层并只多一层，离线 ENV 相符。 |
| wheel 供应 | 旧 manifest SHA `660fa7aa83d8c3cedeb5e188ef7a4de0621e6011a37be48958813a6c50425a55` 等于当前 receipt；packaging 24.1、wheel 0.43.0、setuptools 72.1.0 的名字、SHA、长度逐项相同。本轮核的是保存的清单和回执，没有宣称重新读取远端 wheel 二进制。 |
| CC 与资源 | 历史 CC tarball SHA 为 `d3dadfa9cde294ac82c755eb6d889291228849180bac5d677ad1a4027aca1bc4`；当前共享资产的只读原件回执 `actor5406_assets_readiness_v1.json` 所记 expected／actual SHA 一致，npm integrity 匹配。这只是读取复用的供应资产，不复审其它题 actor。历史实际 prelaunch 限额为 2 CPU／4 GiB／512 PIDs，与本次普通 profile 一致。 |

历史派生实际 ID 为 `sha256:aaf97ca9107336dc68a964386be07361bf363f3a4684998d3727d704c20cd5a0`；本次为 `sha256:1d8dded2ee5bbe9275514fdc603116ac9f36da5e30c19b2d4ffcba4d4a9f27d5`，**两个物理派生镜像不同**。来源和配方相同支持本题公开功能路径的条件复用，不证明两个镜像对象相同，也不允许重绑旧 FrozenPatch；旧 devcheck 本就没有 FrozenPatch。

## 本次最小补查与停止条件

对于上述有限复用，现有修后 UID smoke 的**实际原件**足以完成必要的新宿主条件补查，无需增加一轮完整 CC 三命令重跑。读回应确认：本次 prepared/public/base 和实际 image ID 相符，生产同形激活成功；agent 为 UID54321、cwd=/testbed、解释器为 `/opt/miniconda3/envs/testbed/bin/python`；Moto 从工作区导入、RDS 文件路径与预定 base 摘要相符；保存的 boto3／botocore 版本与历史 `1.35.9` 对上，实际资源限额及本 job 清理成功。脚本会记录 SDK 版本，版本相等仍须读回，不能仅看成功标签。

目前 smoke 尚未运行，因此本项仍是**最小必须补查**，未被本报告核销。两个 legacy false 不要求再加相同旧标记：解释器已有本题历史 CC 原件；激活文件写拒绝只按历史 prelaunch 的实际范围保留，不扩大成新宿主或 CC 通道验证结论。

若 smoke 显示 SDK／解释器／源码／image 与既定条件不一致，先定向修复并核该差异，不能继续沿“供应相同”复用结论。若后续要求新增“本次 CC launcher 已正确运输 HOME／BASH_ENV”的结论，UID smoke 是直接 Docker exec，不能代替 CC；最小新增验证是**本次真实 CC 执行一条 identity 命令**并读回实际 tool_result，而不是机械重跑功能失败和四条旧公开测试。若要求新增冻结／a2g 结论，则需要相应真实导出和独立评分证据，历史目录没有该证据。

本轮没有发现必须重跑三条历史公开命令的具体证据缺口，也没有把任何 false 标志或未运行的 smoke 写成通过。最少原件索引：trajectory SHA `ff32f80a5c1239138117d14922c48eaf132cece1618ad14e86403c9f477708b9`；identity／target_identity／public_existing capture SHA 分别为 `a9d026122d51b0dad2d99fc0240e637d85226515afd2fa7d628ff66c40b82155`、`d1354935e9b591296af0cf3cded38c71388663342f5f4518dad1d0ebd8d11153`、`cd3046f74187f3701226ca227efc2cbcffe491de706ec37350e482437049d3df`。
