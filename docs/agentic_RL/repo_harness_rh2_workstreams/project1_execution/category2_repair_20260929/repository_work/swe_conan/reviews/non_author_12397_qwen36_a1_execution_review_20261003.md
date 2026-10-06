# Conan12397 Qwen3.6 首次：非作者执行／评分运输窄核

日期：2026-10-03。对象：`gpu1003-conan12397-qwen36-a1`；固定请求：`swe-conan12397-r12-briefv1-20261003-v1`。按现行 `coordination_workflow_20261003.md`、`review-standards.md` §5／§10.4／§10.5，以非作者独立上下文读取本地冻结证据。本轮只执行 stdlib 文件读取、JSON、hash、base64、tar 和文本核对；未导入项目模块，未运行 CPU／GPU 作业、远端、Docker、模型或项目测试，未修改共享材料、冻结原件或题主文件。

**结论：本轮执行与评分运输在留存范围内通过，未发现当前阻断。** 原始 `reward=1.0 / resolved` 与真实安装、测试段、2F2P 四个完整参考、原 FrozenPatch 到可信投影、基线重建及收尾一致。此结论不判断候选语义、模型的验证陈述，也不授予训练或留出资格。最小处置是保留原评分与证据，题主继续独立语义分析；无需补跑、重分或修改共享 consumer。

## 原件完整性与版本

以下路径均相对仓库根。证据前缀：

- `S = runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan12397-qwen36-a1/`
- `R = S/queue_qwen_first10_v1/results/gpu1003-conan12397-qwen36-a1/`
- `D = S/diagnostics/QUEUE_QWEN_FIRST10_V1_gpu1003-conan12397-qwen36-a1_before/`
- `G = S/services_qwen_code8_v1/qwen36/gateway/first10-v1/gpu1003-conan12397-qwen36-a1/`

独立逐件核 `S/qwen_first10_closed_v1/gpu1003-conan12397-qwen36-a1/closed_manifest.json` 的 **158 件、16,883,378 字节**：均为普通非软链文件，SHA256／size 全符，无缺件。目录另有 manifest 自身与本地 `sync_receipt_v4.json`，合计160个文件；两者不混入158成员的分母。登记请求的48个输入 SHA 全部与本次封包原件相符。题主请求原件与封包 `host_evidence/owner_request.json` 字节相同。

| 核查锚点 | SHA256 |
| --- | --- |
| 权威 `closed_manifest.json` | `009143e697040cc5d28796d7360f3e268ebee3578a1b81ef99815ad4d0781d48` |
| 题主固定 `probe_request_20261003_r12_v1.json` | `4a572b10c29cb121f241fd6b5b4313044745144d54222cfeb5527f977439ca3a` |
| Qwen 机械 `execution_receipt.json` | `bb9e4651f3669f0aaf6c70792a67d78daab1d91d34969ecbc2667d542a1c6a93` |
| 后续两模型 `pair_execution_receipt_v1.json` | `61651ec6bb95e53264ea5d2b05b92e877faac4ef0fa5646a66339a72f37df2a9` |
| `S/code_v8/source_manifest.json` | `09ddb8bfdeecd3ffaa38c1048a574161ef6fa6053b2855da50166e8e8677899d` |
| `R/grading/...2882163a.eval.log` | `a80002e8ff7f2b3f8ade3e5371c631d975064f8e5682f2aedc23d1e05871116a` |

机械回执只作对账对象，本报告未用其中的 `execution_evidence_complete=true` 代替原件核查。正式 R12 CPU 两份非作者报告分别核 SHA `fd952c9d...`／`365d2269...`，按相同材料范围复用既有4候选、16参考状态和旧 actor 有限验证，不新增CPU通过次数。Coder旧执行报告 SHA `50dcfde7ea30ba413df03a3ec2ed9e0596df7170c8d4b3b0a53dfa803f691d56` 只复用已完成首次及共享材料事实，不替代本次Qwen的动态证据。

## 基线、FrozenPatch 与实际评分消费

对 `baseline_manifest.json`／`frozen_patch.json` 按冻结契约的 `sort_keys=True, ensure_ascii=False, separators=(",", ":")` 重算 canonical SHA，得到：

- baseline：`sha256:54e0d120ee80d3dff3e0419ede9716e6c49a0e2b0e6f10b030b95d028bf47f63`。
- FrozenPatch：`sha256:e5cbcae06ca055418b45b1f11de5258f58e79f054037beb36099545d59da7edd`。
- 实际应用 entry 子集：`sha256:de19c1087a3bade30fc29a39c00f27da2aa5eddc17a5cb03983dd61bcf9c40f8`。

`baseline.tar` 的1,258对象全部为 regular，逐路径核 mode 和内容 SHA，与 manifest **全量一致**；无多件、缺件或重名。原 census 的1,258条对象记录与 manifest 全符；24条排除路径重算摘要 `4fe5d657...` 全符。评分 `baseline_rebuild_census.txt` 与原 census **逐字节一致**，两者文件 SHA 均为 `7ac9ddac...`。因此 `baseline_rebuild_passed` 有原始重建材料支持。

原 FP 只有 `conan/tools/meson/toolchain.py` 一个 `modify / regular / 100644` entry；base64内容重算 SHA 为 `9158959e91179f270568345c614a589d71fc064bc675b3f256ab88cde7f8bae6`。`projection.json` 完整包含该路径，raw digest、任务、`rollout_execution_id` 与 `physical_attempt_id=...#p1` 一致；FP、baseline、attempt 的公开 bundle、实际 runtime image 与 base/head 身份对应。`classification=projectable`，未排除任何FP entry，没有测试文件或 forbidden path 改动。

实际 code8 `entry.py:281` 的 `grade_original` 从原 FP／baseline 构造 `FrozenDeltaSource`，经 `_verify_frozen_delta_binding → SWEGradingManager.grade` 评分，留存投影与重建 census；它不以审阅用 `candidate/*.diff` 重建候选。按 `manager.py:443` 的 entry 集格式重算应用摘要，与 report 的 `digest_kind=applied_entry_set` 相符。`report.json`、`status.json.report`、`result.json.report` 完整对象一致，日志 SHA／25,465字节与报告引用一致。

## 安装、测试与参考完整性

原日志实际恢复并校验正式测试文件base SHA，应用固定私有修订，可信 setup/protect 事实无缺失或 irregular。安装段真实执行三份 `requirements` 的 `python -m pip install`，均未出现 `RH2_INSTALL_CMD_FAILED`；`install_skipped=false`，完整开始／结束时间戳和 `RH2_INSTALL_RC=0` 保留。测试实际命令为 `pytest -n0 -rA conans/test/integration/toolchains/meson/test_mesontoolchain.py`，完整 Start／End 段与 `RH2_TEST_RC=0` 及末尾时间戳保留；candidate exec rc0、segment completed、`log_partial=false`。

安装段1.085秒、测试命令段0.891秒；pytest原输出为 `collected 4 items / 4 passed, 3 warnings in 0.53s`。分段时间、pytest报告时间和整体grader时间含义不同，不相互代替。

全部完整 nodeid 位于 `conans/test/integration/toolchains/meson/test_mesontoolchain.py`，前缀加 `::` 后如下：

| 分区 | 函数名 | 原测试段状态 |
| --- | --- | --- |
| 原F2P | `test_apple_meson_keep_user_custom_flags` | PASSED |
| 新增F2P | `test_linux_native_clang_libcxx_link_args` | PASSED |
| 原P2P | `test_correct_quotes` | PASSED |
| 原P2P | `test_extra_flags_via_conf` | PASSED |

四状态与固定请求、host grading view、分区diagnostics和report逐项一致；参考无缺席、skip、unaccounted或段外命中。原评分为2／2 F2P、0／2 P2P失败、raw1；未将driver退出0单独当评分通过。此材料测试配置生成，完整编译／链接验证仍由题主按实际执行证据另述。

## 完整题面、实际actor／grader与模型运输

实际 actor 与 grader 的 config ID 均为 `sha256:d0b6f915791c8c4597dffc2642093dfdc864a90f122544b23561e09ad6ba90a1`。actor attempt 的实际镜像检查为 repo digest 匹配，来源manifest为 `sha256:b3192aee6c3565730fece66f36212dc2fd77f13271bb632cbb1be2ba0bb6bd55`；`resources.jsonl`分别保留actor PID1024520和grader PID1028602各7次实际镜像ID读回。actor在原base `883eff8961d6e0d96652f78e3d7d3884479e769e` 物化，UID54321，正式conda激活及prelaunch均无violations。

首 gateway 请求的用户文本包含完整原 issue，issue SHA `e39b565f...` 全符；包含完整公开 brief v1，文件 SHA `1cedfa3b...` 全符。入口 `entry.py:58` 对 brief 使用 `notes.strip()`，仅去掉其末尾换行；正文完整一致。交付prompt SHA `4105551e93906661a73c351074dbbe4c06f147e45cc8ba07d2fc0ac37c66f322` 与实际首请求中的整段文本、`solver_prompt.txt`／`attempt/prompt.txt`一致。旧通用禁改测试提示未进入首请求。本轮独立读取首请求内容确认交付，未用CPU开发探针或 `gateway_audit.prompt_delivered` 声明代替。

登记命令、PID1启动journal、entry SHA `bdf806bf...`、实际adapter只读code8 mount均对应 `code_v8`。封包source manifest与本地 `frozen_code_v8/source_manifest.json` 字节相同；其1,045个来源成员共118,460,058字节，独立逐件SHA／size全符。机械回执列出的68个源码成员也与该manifest和本地源码全符；该集合不是远端进程完整模块加载追踪。Coder仍为code7，本次Qwen为code8，不把二者写成同运行代码。

本次启动前 `D` 的现场capture在13:45:20 UTC完成，早于job启动；没有把后续采样伪称运行时历史。实际engine／adapter的ID、StartedAt、PID、RestartCount0、before/after capture一致，`/model`为只读mount。下载清单绑定 `Qwen/Qwen3.6-35B-A3B@995ad96eacd98c81ed38be0c5b274b04031597b0`；当前37条文件大小含26个权重分片与清单全符，总71,926,788,362字节。清单历史 `files_count=40` 与完成后的37条成员分母不同，本报告只核并使用37条已列成员。

实际HTTP server读回：SGLang0.5.20，`ready`、bfloat16、tp1、context196608、`max_req_input_len=196602`、max-running1、mem-fraction0.90；实际adapter为RH2 subclass，qwen3_coder工具解析／qwen3 reasoning解析，sampling `temperature=1.0 / top_p=0.95 / top_k=20 / max_new_tokens=65536`。模型路径与tokenizer均为 `/model`。

| 实际预算口径 | 证据结果 |
| --- | --- |
| context／response输出 | 196608／65536，实际30个请求均 `max_tokens=65536` |
| CC turn／solver wall | 240／10800秒；本次CC报告30turn，正常完成 |
| gateway请求／首字节超时 | 1024／1800秒；配置与登记一致 |
| adapter idle | 实际容器命令 `--idle-drop-seconds 14400`；config本身未提供TTL字段 |
| grading whole／setup／apply／test | 3600／300／120／1800秒，固定输入及实际入口一致 |

30次gateway请求、30条响应和30条adapter turn按seq完整对齐；均HTTP200、attempt1、无stream error；30个SSE文件实际size匹配并以`message_stop`结束，29次`tool_use`后末次`end_turn`。adapter token合计718,386 input／7,123 output，与gateway usage和CC原result一致；最大单次input36,401。响应`model_reported=slime-actor`为接口别名，真实gateway发送`Qwen3.6-35B-A3B`，不从别名推断checkpoint。

CC observed／trajectory init／首请求User-Agent均为2.1.205；两份trajectory357,724字节相同，445事件、一个末尾success result、`terminal_reason=completed`。CC `modelUsage.maxOutputTokens=32000`为CLI显示口径；实际请求及adapter为65536，不能用32000显示字段声称实际输出预算被截为32000。

## 退出、清理、drain与资源边界

job 13:45:20.356661 UTC开始、13:48:40.591175结束，登记exit0；harness实际exec exited／Running=false／ExitCode0、log complete、stderr0字节；attempt termination completed。actor解算59.949秒，完整grader96.905秒，保留各自原口径。

已退休unit的systemd读回为 `not-found / inactive / MainPID0 / ExecMainStatus0`，**默认0不作退出证明**。另核原journal精确unit `rh2-gpu1003-conan12397-qwen36-a1-qwen-first10-v1.service`、`_PID=1`、systemd `_EXE`、同一INVOCATION_ID；有13:45:20.321744的启动和13:48:40.617133的 `Deactivated successfully.`，与登记收尾及完整artifact一致。journal SHA `25b89e2be03d442bcfb3e2938d608958cb0be91de385885aec4f062fcdc2b186` 全符。

actor `container_rm=0`，container left、network／relay failures、精确标签container／network leftovers均空。grader manager创建1／删除1，containers_open、supply_open、cleanup_failures为空，无regrade。gateway原 `session_close` 与attempt drain对象相同：session精确、revoked=true、active_requests0、drained=true。16份资源样本末次没有本job容器；此结论限本作业标记资源，不扩作主机全局清理证明。

资源声明为actor／grader2CPU、4GiB及既定profile，actual限额完整读回未保存：diagnostics `resource_facts=null`，没有memory.max／cpu.max／pids.max或全量HostConfig。本轮可核16次间隔采样（13:45:07.669782—13:48:53.732855 UTC），actor保留peak最大885,678,080B／pids23，grader369,356,800B／pids8；两者采样中oom_kill、pids.max事件和CPU throttled_usec均0。grader peak按1024²为352.246，符合原报告；间隔样本与声明不证明完整配额、持续峰值或并行度，观测空窗保持未知。

## 未验证事项、收口与停止条件

| 边界 | 当前处置 |
| --- | --- |
| 实际资源限额完整读回 | 未保留；无需为本次有效评分重跑。如未来结论依赖配额或容量，由GPU在新授权作业内保存精确容器HostConfig及cgroup限额。 |
| 当前每个权重文件SHA、GPU内存已加载权重 | 本轮未复验；身份结论止于历史下载SHA清单、当前文件大小、只读mount、实际服务／HTTP绑定，不声称权重内存attestation。 |
| CC平台tgz payload | 当前本地封包无payload；保留observed2.1.205及原运行记录的tar SHA，不声称重hash安装包。 |
| stdout通用可伪造边界 | 本地一致性核查未解决该边界；原保护／runner digest无变化，当前FP无测试控制面改动。未做对抗注入。 |
| `baseline.environment_package_digest=null`、`env_qualification=absent` | 原值如实保留；普通诊断成功不代替正式typed actor租约及训练接线。 |
| 候选语义、完整编译链接、模型验证陈述 | 本轮不裁决，由题主另核。 |

原closed manifest的`paired_request_closed=false`是13:48封包时事实；后续pair回执13:59:49明确两模型各一次完成。当前总账该请求为`returned`、revision4、updated_at `2026-10-03T14:05:34.902076+00:00`，receipt SHA与pair全符。两者属于不同时间，未回写历史封包；`returned`只表示本轮交付收口，pair中题主语义审查字段不替代Qwen语义验收。

适用性：A／E／G核真实FP消费、安装测试、参考及退出；D／F／H／N核请求／材料／代码／镜像／服务／预算的一致性与唯一原件；L／M核观测与清理并明确未留存限额。I采用最小处置并在本边界停止。B／C不进行训练分布或准入裁决，原空缺不改写；J／K无实现改动，因此不做代码质量或演进成本重审。本轮未发现需要按§4新增八要素finding的运行缺陷，也未新增guard、owner、retry或fallback。

**停止条件已满足：** 原件身份、完整baseline归档／rebuild、FP投影、真实安装／测试四参考、实际模型／预算HTTP、退出／清理／drain全部闭合，未知边界已列明。只有原件身份变化、正式消费具体差异或新运行反证时按受影响范围再核；本轮到此停止。

独立机械核查结果与完整核心原件SHA见[同名JSON](non_author_12397_qwen36_a1_execution_review_20261003.json)，SHA256：`84f9dd915c78f54631bc00374711a99642ca7e8d798a4cf3d8cc7630173fe51e`。
