# 50319 原公开 actor 补充窄核

2026-10-03。只核新完成作业 `pandas50319-public-v5-83037b3703d8`。**原公开base在UID54321下的九条开发命令、真实源码构建、新进程加载、原公开八节点与作业清理均有原件支持；本次未发现具体阻断。** 该结论补足原公开 actor 的开发证据，仍不代表真实模型求解、新材料正式评分或训练资格。

沿用[已有材料窄核](non_author_material_review_20261003.md)和[已完成CPU核查](non_author_cpu_evidence_review_20261003.md)，不重做全题静态审查、原NoOp/None私有校准或旧66件CPU核查。旧CPU报告保持字节不变，SHA-256为 `4fe58964c2191990ee4cd387f3f284fc1f5801c48242338f33bd9efcb1ea67e6`；其中“50319新公开actor待完成”是当时事实，本报告是后续证据，未回写旧判断。

核查者未参与本包材料编写或作业执行。接触上下文包括原父任务交接、此前两份本人非作者报告及当时作者摘要、本次父任务补充的作业版本和mtime线索；不是全题盲审。下文结果由本次44件原件、原父grading/public与冻结R5脚本独立核得，未用新增作者摘要替代原件。

## 接收完整性和版本身份

原件根目录为 `runs/category2_repair_20260929/pandas_cpu_20261003/cpu_c_50319_public_actor_v5_received/`，以下简称 **R**。本次[receipt](../../../../../../../../runs/category2_repair_20260929/pandas_cpu_20261003/cpu_c_50319_public_actor_v5_received/receipt_manifest.json)所列44文件，字节数和SHA独立重算全部匹配；`R/inputs/input_manifest.json`所列五个输入也全部匹配。44是文件数，不是44次实验。

- `R/job/status.json:9`起实际使用 `cat2-cpu-r2e078079-swe7-git-20261003-v1` 和 `runtime_cpu_v2`，2 CPU/4 GiB。作业于2026-10-02 18:47:53 UTC启动，19:03:26 UTC结束，宿主rc0；`actor_cli_exit.json`为0，`actor/attempt.json:175`记录harness rc0。
- R5本地冻结tar内manifest重新重算为 `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`（837文件）。`R/inputs/run_public_actor.py:5`在真实prepare前校验同一digest，`:9`从该冻结repo的受信入口prepare，`:15`用正式host reader读回。所用冻结devcheck/acceptance两个文件重新核对manifest摘要匹配，未按当前可变runner解释旧作业。
- `R/inputs/expected_parent.json`的base、1个旧F2P、109个P2P与父grading逐项相等；父grading/public canonical digest独立重算分别为 `sha256:d37caa1d070ef67c1487e31485f8a5463d81761393acd88294aeaf99cc9ee17d`、`sha256:5c94214a75aca9417902ae115febdacf58f52a1a9a5f553631234c67832a7d27`，与 `R/input_identity_check.json:3`起相等。helper在devcheck前逐项断言两个digest和完整参考数组相等（`:18`起）。prepared summary与身份读回共同引用manifest `745296395bc175b7565c44994a14b85e10a5970ab61b2a112a200f0bec944fdd`。本次receipt不含远端prepared manifest/公开包/host grading的完整原字节；此处独立核父来源与真实受信读回，不冒称重新hash了未接收的远端文件。
- 实际容器为原公开固定镜像 `xingyaoww/sweb.eval.x86_64.pandas-dev_s_pandas-50319@sha256:e645e4346df9200174e8b879ad8fb7a09f64f91c7375311e2569596d054ba21e`，实际image ID为 `sha256:a3f20f616f78963bee9c87426b8a93c28fb63a6ade97d0f444115279c28f859a`。初始镜像检查rc0、原工作树无porcelain输出；sanitize前后HEAD和最终HEAD均为base `1613f26ff0ec75e30828996fd9ec3f9dd5119ca6`。

本次使用原父材料；没有把50319两个新F2P、None候选或其它私有候选交付actor。R5未登记本轮Pandas修订的边界沿用旧报告。

## 非root身份、激活和九条实际命令

`R/actor/prelaunch.json:47`起记录UID/GID54321、CAPPRM/CAPEFF=0、NNP=1、工作目录可写且属主54321、外网及直连上游DENIED；`ok=true`、violations为空。该容器无bind/mount私有调查材料。`R/actor/activation_check.json:8`起记录testbed conda前缀、实际Python及sys.prefix均一致。实际Bash的 `R/actor/captures/env.out:1`再打印UID54321，`:2`打印 `/opt/miniconda3/envs/testbed/bin/python`；`:3`确认pandas和parsing扩展均从 `/testbed` 导入，原base版本为 `2.0.0.dev0+940.g1613f26ff0`。

九条命令以 `R/inputs/commands.json` 为原输入。我核对每个原轨迹Bash输入与 `R/actor/stub_script.json` 的回复步骤完全相等，并核对包装器内的 `bash -c` 实际命令就是输入的精确shell内容；未仅依赖 `commands_result`。九个tool ID互不重复，每个都与后继tool_result及下一实际请求携带的结果ID对应。下表行号均指 `R/actor/harness/trajectory.jsonl`：

| 命令 | 实际rc | 实际结果 | 调用/结果行 |
| --- | --- | --- | --- |
| env | 0 | 非root身份、解释器/checkout导入和base HEAD确认 | 6/12 |
| mcve | 1 | 原 `27.03.2003 14:55:00.000` 在 `_fill_token` 抛ValueError | 17/21 |
| build_start | 0 | 输出 `RH2_PUBLIC_BUILD_STARTED`，只说明有界后台构建已启动 | 26/30 |
| build_wait1 | 0 | 输出 `RH2_PUBLIC_BUILD_STILL_RUNNING`，此时尚无构建退出文件 | 35/41 |
| build_wait2 | 0 | 输出 `RH2_PUBLIC_BUILD_FINISHED`及实际build.rc内容0 | 46/52 |
| build_wait3 | 0 | 同样读到已结束/0，未启动第二次构建 | 57/61 |
| build_verify | 0 | 核真实build.rc=0，再以新Python进程核源/扩展路径及mtime | 66/70 |
| caller_public | 0 | 原公开 `TestGuessDatetimeFormat` 收集并通过全部8节点 | 75/81 |
| tree | 0 | HEAD仍为base，tracked工作树无porcelain输出 | 86/90 |

各工具结果的BEGIN/END标记和rc均与表一致；九份captures的实际字节数与attempt记录逐项相等，工具结果中的输出尾部也与相应capture相等。env使用多个顺序子命令，整体rc0本身不能证明每个中间命令成功；此处所需Python断言在JSON打印前执行，JSON及实际UID输出是额外原件支持。

mcve非零是在原公开示例上的预期未修复行为：`R/actor/captures/mcve.out:3`起到 `parsing.pyx:965`、`_fill_token:1023`，`:7`为 `ValueError: invalid literal for int() with base 10: ''`。本次没有在构建后再执行第二次mcve，不能声称后测修复成功；原源码没有候选改动。

## 构建退出与新进程加载

等待命令的rc0只表示等待脚本正常返回。特别是第一次等待明确“仍在运行”，不能算构建通过。第二、三次等待读取build.rc=0；真正的成功门是 `R/inputs/commands.json:49` 所列build_verify，先要求退出文件存在，再读真实rc并在非零时退出，最后启动新Python进程。不会仅因打印“FINISHED”就将非零构建冒称通过。

后台实际运行命令是 `timeout -k 10 1500 python setup.py build_ext --inplace`，退出状态通过 `rc=$?`写入 `build.rc`（`R/inputs/commands.json:21`）。源码仅被 `touch` 强制触发重建，没有修改源码字节；脚本和桩中没有切换为root执行这项构建。

`R/actor/captures/build_verify.out`保留123,566字节，小于命令的190,000字节日志上限和capture的200,000字节上限。本次日志未被这些上限截断。关键原件为：

- 第1/2行确实因pyx更新而编译并Cythonize `pandas/_libs/tslibs/parsing.pyx`。
- 第254行构建 `pandas._libs.tslibs.parsing`，第256行实际编译 `parsing.c`，第261行实际链接 `.so`，第395行复制到目标源码目录。
- 第412行是之后新Python进程的JSON：pandas加载 `/testbed/pandas/__init__.py`，parsing加载 `/testbed/pandas/_libs/tslibs/parsing.cpython-38-x86_64-linux-gnu.so`；mtime为 **1790967668.0**，晚于build_started **1790967066**，差602秒。build_verify的实际rc0和JSON打印前源码/路径/mtime断言相互支持。

新进程验证的公开原源码SHA为 `5c8e81b9914bc6448b21a909cf13d3c2e7799e63e92d386042dd4262b6d048aa`，与父公开base独立重算一致。其加载扩展SHA为 `127481b230a3c52c886aea1d01b8957e61b55ab106e315f93c4a8f399ecd425c`，**与env命令所载原镜像扩展相同**。本次是原源码重建，不能声称扩展SHA变了，也不能仅靠相同SHA否定重建。编译/链接/复制日志、真实rc0、新进程路径和较新的mtime共同构成重建证据。本核查没有导出或重新运行该二进制。

## 原公开八节点、轨迹和清理

`R/actor/captures/caller_public.out:7`收集8项，`:17`至`:24`恰有8个唯一PASSED摘要，无缺席、重复、额外节点或skip/xfail；`:25`为8 passed/0.41秒。它们是：

- `pandas/tests/tools/test_to_datetime.py::TestGuessDatetimeFormat::test_guess_datetime_format_for_array[test_list0]`至`[test_list6]`，共七个参数节点。
- 同类 `test_guess_datetime_format_for_array_all_nans`，一个节点。

成员与所指原公开base的 `test_to_datetime.py:2294`起类定义相等：七组既有数组输入及all-nans；原有locale装饰的all-nans本次实际PASSED。原pytest_asyncio警告照常保留。这不是109来源P2P、新两日期F2P或旧私有None调用者测试，不能把八项通过用作那些评分断言的分母。

完整轨迹为56,576字节、99个可解析事件：19 system、60 stream_event、10 assistant、9 user、1 result；10个message_start。`R/actor/stub/requests/messages_000.json`至`009.json`为十个真实请求，消息数依次1/3/5/7/9/11/13/15/17/19，都为stream=true、`slime-actor`；实际文件长度、请求索引和十个回复步骤与原stub_log逐项相等。后九个请求各带回前一工具结果，内容及tool_use_id与原轨迹完全相同。第99行是success结果事件、10 turns、`is_error=false`、无permission_denials。

请求初始用户消息实际为固定 `Devcheck run: execute exactly the tool calls you are given, then stop.`，十个桩回复依次给九条固定Bash和结束文本。这证明真实Claude Code桩端点开发执行链；没有真实模型求解，也未验正式题面/修订材料消息交付。

`R/actor/attempt.json:78`的 **`bashenv_denied_for_agent=False`保留原值**。九条实际命令、原轨迹和十个请求没有请求通用 `RH2_BASHENV_WRITE` 操作/标记；冻结acceptance只在工具结果存在 `RH2_BASHENV_WRITE=DENIED` 时设True。本次该项未执行，不能写成权限失败或“所有通用检查通过”。预启动`:75`另有实际 `ACTIVATION_WRITE=DENIED`，须区分两项。

`R/actor/captures/tree.out:1`只有base HEAD，tree命令显式检查无porcelain输出后rc0。`R/actor/post_run_facts_root.txt:4`起记录tracked status=0、agent进程=0，但新文件计数为514，含编译扩展和test-data.xml；不能将tracked干净写成“完全没有文件写入”。

`R/actor/attempt.json:382`起清理记录为container_rm=0、network/relay failures为空、stub_rc=0、label容器/网络为空、最终 `residual_after_force=[]`；沿用已核冻结devcheck的查询失败显式标记语义。这支持作业结束时的本次零残留，未核当前远端宿主或其它任务状态。`R/inputs/attempts.jsonl:1`至`:7`的前七次75为未获槽请求，最后一项才是本次已完作业，不能计成七次actor失败或0分。

## 当前用途和停止条件

原公开base下非root构建/导入/公开窄测试的补证完成，无需新增用户决策。建议题主据本报告补记已完成的actor开发事实，继续既有正式材料发布/manager验收流程；本报告未改作者状态文件或共享登记。

尚未证明的事项仍保持旧范围：新有效测试补丁及1→2 F2P/完整绑定正式消费、正负候选矩阵的manager reward、统一探针提交/真实模型反馈和训练用途。已核root None候选行为按旧报告复用，本次原公开源码重建不能提升为None候选的正式actor求解或新评分结果。

停止条件：本次只补这项完成原件，到此收口；仅在相应正式材料/评分带来具体差异时接续。未联网、SSH、Docker、运行新实验、安装、编译、pytest、模型或远端清理；未执行作者helper/生成器，未导入项目模块。只执行文件读取、stdlib JSON/hash/tar/AST及日志/字符串核对；唯一写入为本报告，使用排他创建，未覆盖旧报告或作者结果。
