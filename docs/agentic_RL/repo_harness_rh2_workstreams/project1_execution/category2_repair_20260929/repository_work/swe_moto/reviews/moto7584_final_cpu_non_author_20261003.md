# Moto7584：固定 R13 CPU、UID 与公开 CC 开发操作的非作者验收

日期：2026-10-03。**本题固定 R13 的普通 CPU 诊断验收通过，未发现阻断后续普通探针的本题缺项。** 已核十一臂原评分结果、实际 UID/激活/模块补查，以及真实 CC 执行四条原公开开发命令的闭合原件。历史 gold 已知不完整，本次实际 raw0；两条 stmt 正对照 raw1。此结论不授予训练 typed-actor 资格，不证明模型自主求解、a2g 或训练捕获链已通过，也不改写历史分数、FrozenPatch 或参考。

## 范围与独立性

审查者不是材料、工具或运行作者；已接触本题私有完整金标、参考和控制补丁，**不是公开盲读 solver**。本次仅做本地标准库读/hash/JSON/AST、归档成员比对、原日志与 trajectory 读回，以及在内存中严格应用 patch 比较冻结源码。没有启动 SSH、Docker、CPU、测试、SDK 或模型，没有导入/执行项目，也没有读取或归档在途 actor。公开 actor 在题主确认自然闭合并运输之后才读取。

只新增本报告，未改原件、工具、冻结输入、共享代码或既有报告。本次不重复题级断言语义和工具静态全审；相应入口为 `reviews/non_author_new_tests_review_20261003.md`、`reviews/moto_four_r13_matrix_tools_non_author_20261003.md`、`reviews/moto_four_r13_matrix_v2_tools_non_author_20261003.md`、`reviews/moto_four_r13_uid_tools_non_author_20261003.md`、`reviews/moto_cloud_public_actor_tools_non_author_20261003.md`。作者 `tasks/getmoto__moto-7584/cpu_matrix_owner_readback_r13_20261003.md`（SHA `46ffd81701b2ec3fc82e9487521e8d3d742f54a90602338b909fd2c7b6468161`，2929B）和两份 `author_raw_readback_v2.json` 只作导航；以下结论来自原件，不接收其 checks 布尔值替代检查。

## 运输与退出身份

所有 evidence 根均在 `runs/category2_repair_20260929/moto_cpu_20261003/<job>_evidence/`；同级 `<job>_transport_receipt.json` 与 `<job>.transport.tar.gz` 保留。独立核 manifest SHA、每个原件 SHA/bytes、成员集合和非符号链接，归档 SHA/长度及归档内每个文件与落盘实物逐字节相等。以下文件数不含各自运输 manifest；四组共246个原件，8459284 bytes。

| job | 原件数 / bytes | transport manifest SHA | archive SHA / bytes |
| --- | ---: | --- | --- |
| `moto7584-cpu-a9dd947080c8` | 45 / 728348 | `98c38af9736ae5f23fe2eabb7a8480e325a416e70884ae151a97d4467ee027bd` | `bd6ca3c48188f6b3c2dc3696812cef81e4aeb14421dfd833ac91a0e5155d9091` / 140891 |
| `moto7584-cpu-0121b210ce7a` | 172 / 7536265 | `7125015062adc6b2f18a2fb8d9747064f79de2a9206276db6fae08e4318c1760` | `2d3329686fa5b599787d76da9b82e5df607168f905356dba0b5ac252cfcae7a3` / 1470422 |
| `moto7584-uid-ef396ea52123` | 6 / 51497 | `38c155692adbaa73cbea1bcef19b2ec54cb3d02c3c81c6e253a83980ae4294a9` | `741841c603e317923fbae5baf03c479b839830bbc904c27ac32f1754800afb02` / 10693 |
| `moto7584-actor-a50e7789d81a` | 23 / 143174 | `5206209478ac13faaf8ba349e85be3d134ff9d4428ccd92d2efd5e541d9c5fd0` | `492970733d118a21190ca7fd92c9dcf8e56d21988366609934c4965f462ce0b8` / 22411 |

四份 slot `job/status.json` 均为 finished/returncode0，存在正常起止时间和对应唯一子进程。十臂 job 的本地 launcher `_exit.json` 保留 SSH255；远端原 status 则从 `2026-10-03T01:24:03Z` 至 `02:22:38Z` 正常闭合，十次 CLI 与 footer 也齐。**SSH255不等于该远端 job 的结果，也不能覆盖其 parent0；本报告没有将 SSH 返回改成0。** 原 job 与物理 attempt 身份保持，未生成替代运行。

此前 `moto7584-uid-1f6cf47cd641_exit.json` 为75。它没有本次开始/执行结果，不计为失败样本，不与已闭合 UID 合并成一次执行。

## 固定 R13、noop 复用及真实 CLI

R13 release 是 `cat2-cpu-r2e089092-swe27-pandas-moto-20261003-v1`，本地根 `runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe27_pandas_moto_v1/`。manifest SHA `3fad18daff8db219294e10cbf08d4424d68cf7000d008bb983cba4bdc427b641` 与本次 runtime 相符；1094个固定发布成员（125080983B）逐 SHA/size 相符。本次两个矩阵使用已审 matrix v2，scope 中工具 manifest SHA 为 `6cd02683d46370adf553531064f29d99a1e9da47ebf9f3c909f1bc6fdb9d1fd3`。

两 job 的 `runtime_inputs.json` **逐字节相等**，均4858B、SHA `021ef1b9ff910baea846c50f0ee6d1dccc9409420dc24285c2757ddd793e8bc7`；两个 `consumer_readback_before_checks.json` 与固定工具 expected 对象相等。各 prepare 的 manifest、单题 prompts/rollout、private host grading、summary 关联 SHA/行数均核对；effective patch SHA 从实际 private 内容重算，等于 `sha256:58875207adea3feddb71bb0b04bfd47423f0663ac79b9be54f402e815f144fd3`。两者 base、public、材料、ENV、五份脚本 SHA、预算和完整测试串相同，因此保留先前 noop 原件与后续十臂组成同条件矩阵，证据不要求机械重跑 noop。

- base：`cc1193076090f9daf90970db286b6b41581dd8bc`；public digest：`sha256:976e9bbcb91bb027e9fc4888e0d3b21db02695c6639a75174f3a326c36e269b8`。
- grading digest：`sha256:128f5a11e84f86d1420ab4f330a0a2fb3c8f64fc0ebd3675a34fb74bbac1e4f3`；environment digest：`sha256:3a31e517d345dfd7452b6bcf387332e49ca1ecfa65147a607cd9ca945a447b0b`。
- registry：`sha256:06f37a85ebffa1ae3441919c1ff1a7a8618eaaccc8b676eb1e492b46921b62b2`；revision：`moto7584-endpoint-v3`；materials identity：`sha256:8a1c534a3ce5f8f7e36619300a874707a25c9455edfc727ea0b813383ab77d72`。
- source ConfigID：`sha256:437ec771611180d48f01985f1faaac352bae045c7f3db7c3582298b937252f5d`；source manifest：`sha256:3b263c0c4745d890400b7beaf08c10b5413f86ae7983dd4bf14d93e43cd2fbf9`；实际登记 COPY-only ID：`sha256:990e0e91a190f85426e6900828cf758c30f389c927f6c1d0cd1ed8c68b902f96`，recipe `moto7584-fixed-environment-v1`。

实际 command 原件包含原 `prepare/export-gold/run`，调用固定 release 的 `replay_grade.py`、repeat1、正确 task、登记 derived ID/recipe 和原 run_id。预算为 setup300/apply120/test1800/candidate-stage900/whole-grading1800/cleanup120/image-pull1800秒，未改评分或限额。安装仍 `make init`，测试仍 `pytest -n0 -rA tests/test_sns/test_application_boto3.py`。export gold SHA 与原固定 gold相符；gold_input 与候选输出目录分开，没有覆写输入。

每臂 ledger 的 image_ref/image_id_actual 都是上述990e ID，image_local_build=true、expected manifest=null、overlay=null；原公开 source face保留。全部实际脚本综合 digest 一致为 `sha256:3998d720d54335395c78356144290314ecc73b08f398a182e6461c4171094db3`，ledger 与 diagnostics 一致；声明 grader profile 为 UID54322、2CPU/4GiB/PID512/shm64MiB、deny_all网络。这里实际资源 inspect 的独立原件来自后述 UID/actor；矩阵资源事实没有另附完整 HostConfig JSON，不能把 ledger 的 policy 声明写成额外独立 Docker inspect。

## 十一臂实际评分与具体失败

逐臂读完整 eval log，重新提取短摘要的 PASSED/FAILED 节点，并与 actual grading revision 的两个参考分区、parser diagnostics 和作者 reference_statuses 对照。每臂收集20、短摘要20唯一节点、parser20，精确覆盖1F+19P；没有缺失、skip、XFAIL、合键、分区未记账或段外解析。所有 report 为正常 resolved/unresolved、reward0/1，stage_error=null；失败类只是 tests_failed，没有把基础设施或 failed_to_grade 当成反例。

| 控制 | 实际 raw | make init | pytest | 包装 exec | 参考结果 |
| --- | ---: | ---: | ---: | ---: | --- |
| noop | 0 | 0 | 1 | 0 | 1F失败、19P通过 |
| gold（known_incomplete） | 0 | 0 | 1 | 0 | 1F失败、19P通过 |
| all_protocols | 0 | 0 | 1 | 0 | 1F失败、19P通过 |
| arn_form | 0 | 0 | 1 | 0 | 1F失败、19P通过 |
| deleted_set | 0 | 0 | 1 | 0 | 1F失败、19P通过 |
| gold_order_stmtmsg | 0 | 0 | 1 | 0 | 1F失败、19P通过 |
| reject_all_application | 0 | 0 | 1 | 0 | 1F失败、19P通过 |
| reject_all_arnmsg | 0 | 0 | 1 | 0 | 1F失败、19P通过 |
| stmt | 1 | 0 | 0 | 0 | 20通过 |
| stmt_arnmsg | 1 | 0 | 0 | 0 | 20通过 |
| wrong_code | 0 | 0 | 1 | 0 | 1F失败、19P通过 |

十一臂有九个raw0；后一个十臂 job 单独有八个raw0。失败均为 `test_publish_to_deleted_platform_endpoint`，不是按文件名或 reward 推测。完整 trace 中可定位：

- noop在测试475行，对已删除、从未订阅的 endpoint 执行 application subscribe，`pytest.raises(ClientError)` 实际未抛。
- gold与gold_order_stmtmsg在494行，对曾订阅后被删除的 endpoint再次订阅，实际未抛。原 gold 已知不完整，不能因名字称为正对照或预设1。
- deleted_set在504行，对从未创建的随机 endpoint ARN应拒绝而实际未抛。
- all_protocols在513行把合法 `Protocol="email"`、`someone@example.com` 拒绝成 InvalidParameter；arn_form在519行把合法 `Protocol="sqs"`、queue ARN同样拒绝。
- reject_all_application与reject_all_arnmsg在488行，将刚创建且仍存在的 application endpoint 的合法订阅拒绝；后者完整异常还保留其 `arnarn:` message。两者并非只靠错误消息匹配而判断失败。
- wrong_code在 `_assert_endpoint_does_not_exist` 的444行实际 `'NotFound' != 'InvalidParameter'`，trace从481行调用进入；这是具体 Error.Code 错误。

两个 stmt正对照目标F与全部19P均为实际PASSED。各安装完整 marker 为 install rc0、没有失败命令/skip/partial；test结束 marker和pytest0/1与ledger相符，candidate segment completed。**包装 exec0说明原 shell正常收口，不能把它误写成每臂pytest全过。** 两份作者 raw readback 的 report/install/test及分区 reference_statuses与独立原件提取相同，未依赖其 checks=true。

## 冻结输入、保护与两层清理

每臂 baseline manifest canonical digest 独立重算为 `sha256:a5528bdb5a61e699b7f7542beded25e5532dabd7f2fadc364ed69c11d925ad28`，与该臂 FrozenPatch锚一致。每份 FrozenPatch canonical digest也重算到实际projection/ledger，HEAD/public/runtime身份正确；classification均projectable，没有reason code、excluded pathset变化、private pathset变化或unsupported shape。

noop entry为空。其余十臂各仅一个 `moto/sns/models.py` modify/regular/100644 entry，无测试、conftest或fixture改动。实际candidate.patch SHA与对应原控制/gold pin相符；entry base64严格解码后的内容digest正确。将对应patch严格应用于原公开 base `moto/sns/models.py`（SHA `8d74faa42da7fe740e62c650b43259afda89ccf29a964852846bba1fa9e84fe2`，44621B），内存产物与实际冻结entry **逐字节相等**。这是实际评分消费的控制输入核对，没有导出新patch，也没有把人工控制变成真实solver产物。CLI `candidate.kind="cc"` 在这些臂只是patch输入枚举，不是真实CC。

各 stage 的原sanitize verified/exit0、HEAD保持、remotes/reflog/unreachable为0，真实apply/projection正常完成。各 diagnostics 中 trusted test文件restore/apply/setup成功、control surface保护成功且没有缺失；candidate prerequisite为UID54322、verified/exit0；实际Moto import来自 `/testbed/moto/__init__.py`，前后runner digest相等，runner_integrity_changed=false。

全部十一臂 candidate cleanup removed=true。每次原CLI末尾footer rows1、halted/aborted=null、final_status.exit_code0，manager containers_open/supply_open/cleanup_failures为空，created_total=removed_total=1；各自CLI exit原件为0。每臂 `residual_<name>.json` 的自有容器/网络查询各rc0且stdout为空，查询失败没有作为空结果接收。slot最终正常闭合，未全局prune或删除他人资源。

## 新宿主 UID、激活与模块原件

闭合 UID job引用十臂R13 prepared summary，SHA `7ab9439fbbbd0b70a83e8f2b69551e60c891f1eb89fd41247f710eceff812cb4` 与实际summary匹配；工具manifest为已审修后 `c4b77468ff9d75e273499de6e88e4ff67519627b7a0042f7c590190fce0c310c`。

`docker_calls.json` 的12次实际调用全部exit0、stderr空。原source/derived inspect与矩阵原件相同，来源层前缀和离线ENV保持。实际run容器ID与两次inspect一致，Image是990e，self run label相符。原production sanitize/init/activation输出与result逐字段一致，Git HEAD/历史保持、remotes/reflog/unreachable为0；activation为testbed，解释器 `/opt/miniconda3/envs/testbed/bin/python`。

原UID exec完整stdout是 UID/GID54321、cwd `/testbed`、HOME `/home/agent`，Moto及SNS模块来自工作区；指定模块SHA与上面的原公开base一致。boto3/botocore实际均1.35.9。实际HostConfig为NanoCpus2e9、Memory4294967296、PidsLimit512、ShmSize67108864、NetworkMode=none。原finally先核label，再rm0，最终自有容器和网络两查询均rc0/空stdout；正常footer、slot0和运输身份一致。

这份UID工具不运行公开安装或私有测试；其作用是宿主UID/激活/import补查。十一臂真实make init由矩阵原件另外证明，不能把UID smoke自己写成安装验收或真实CC。

## 真实 CC 与四条原公开开发命令

公开actor使用已审工具manifest `1017b31d7c57eb2e0a4541fda03714d8992b246154a1df73e711e2695481dd46`、原R13 DevRunner/ClaudeCodeDriver和CC2.1.205。实际CC tarball SHA记录为 `sha256:d3dadfa9cde294ac82c755eb6d889291228849180bac5d677ad1a4027aca1bc4`，与固定工具pin一致；bringup实测版本2.1.205。它使用990e COPY-only诊断override，原source public face/prompt保持；没有自主模型调用，只有确定性stub发四条Bash tool_use再end_turn。

首真实 `messages_000.json` SHA为 `666523ae2545aa0b45d7cfd70fd95ddac2bbd2adf962c1a190f0b6d0f6fd0a2f`。读取实际request中的所有user text，并与已运输prepared prompt逐字节比较：公开题面prompt恰出现一次，SHA `ff9355e8a86fd1a91febf0537f6e0a3f8c28e8bee83110f763c0581c05b67fdd`；另有CC日期提示，没有以私有测试、修法、反例或金标替换题面。五个真实request与五次stub响应、48行完整trajectory对应，包含5次message_start、4次Bash、4个匹配tool_use ID的rc标记和正常success/end_turn结果；完整harness stdout22945B、stderr0，exec exited0、log_complete=true、无stream error。

四条内层命令从实际trajectory的shell引用中解析回原字符串，与 `public_commands_old_reader_v1.json` 及固定 `commands_7584.json` 的id/cmd/timeout/expect相等；command文件SHA `17a735aef7b5eea6fc78b970915af169eb6cc1e3fdef5c5309fc18eb0d20193a`。外层只负责限时、保存full/rc/bytes并返回标记。完整输出由agent身份取回；捕获实物SHA/bytes与attempt/summary一致，未截断：

| 命令 | 实际rc | 完整输出 / SHA | 内容核实 |
| --- | ---: | --- | --- |
| A | 0 | 167B / `a06650257cf01dbdff3cb838a51c5a4b5aabe8392387e305202124d4a03c3017` | Python3.12.4、testbed解释器、Moto `/testbed/`，boto3/botocore1.35.9、pytest8.3.2 |
| B | 1 | 132B / `3fe35f07ac297c43ef2872b5d440e0640c7316663e5707e17d571034c4fb97e6` | 唯一异常为公开脚本末尾line31 `AssertionError: Deleted application endpoint was accepted` |
| C1 | 0 | 1993B / `6878cd5234cd1fb9ebbec8e9cd60852ef69d42a88e7c3895f81f672622bbb4cc` | 原公开subscriptions文件实际19 passed |
| C2 | 0 | 651B / `2081e1502e1789f3b29293e56b5c6b65d440dd852d7d122ce7b8e5313c2b5675` | 原公开application文件实际19 passed |

B末尾异常证明前面的首次订阅、重复订阅相同SubscriptionArn断言和delete均已走过；没有把任意nonzero当作预期bug。这里原bug仍存在是正确的公开开发起点，不能称已经修好。C1/C2没有failed/error/skip/deselected，完整输出各19点和19 passed；它们的原公开base文件各19个test函数，均不含私有目标 `test_publish_to_deleted_platform_endpoint`。`-q`没有打印全套逐节点ID，因此本报告不虚构公开actor逐节点census；两份公开19不能混成上面正式评分的20参考，也没有重跑来补名册。summary的pytest字段null是旧带等号摘要parser对`-q`输出未取到，完整实物本身已明确19 passed。

实际prelaunch检查记录agent UID/GID54321、无effective/permitted capabilities、NNP1、cgroup2CPU/4GiB/PID512/swap0、实际shm64MiB和990e Image。actor使用自有受限网络/relay访问stub；外部DNS、禁止目标、直达upstream均DENIED，relay CONNECTED，不能写成actor本身network none。network none是前述UID/grader诊断条件。activation文件为root:644且agent可读不可写，工作区归UID54321、激活testbed核查成功。

必须保留两个false legacy flags，不能改成“全部检查通过”：

- `interpreter_in_tool_result=false`：原 `acceptance_startup_2.py` 只在trajectory tool_result中寻找 `RH2_SYS_EXECUTABLE=<prefix>/`。本次四条原公开命令不含该旧标记，tool_result按完整输出封装只返回rc标记；解释器由实际A完整文件、prelaunch/activation及独立UID原件证明，不是由该false字段证明。
- `bashenv_denied_for_agent=false`：旧检测器只寻找tool_result内 `RH2_BASHENV_WRITE=DENIED`，本次四条公开命令没有那条旧写探针。原实际prelaunch已记录 `ACTIVATION_WRITE=DENIED`、`ACTIVATION_STAT=0:644`，写权限边界有独立运行原件；没有新增命令或把旧flag静默改true。

`post_run_facts_root.txt` 旧文件名保留，但attempt实际明确 `post_run_fact_actual_role=agent_uid_54321`；固定工具将带Git的整个事实段切到agent执行。因此Git status0、无`.harness`/launcher/done marker只按真实角色解释，不当成root证明。该段初读RH2_AGENT_PROCS=4、RH2_NEWER_FILES=121；原自有容器内后续清理记录 `RH2_AGENT_PROCS_AFTER=0`，不能省略初值伪称一直为0。开发命令合法产生缓存，不能据新文件数推成篡改或模型修改。

attempt最终harness0/termination returned，container_rm0、stub_rc0、relay/network failure列表空，labeled containers/networks以及residual_after_force全空。原DevRunner源码将最终query非零记为`<*_query_failed>`，不会作为空结果；本次没有该标记。公开actor未另附逐Docker调用全集，清理判断按固定源码语义及这份实际attempt原件，不虚构额外query日志。正常slot/CC终结、完整trajectory和全部23运输原件共同闭合本次开发操作。

## 最终用途与不适用项

十一臂完成原真实评分路径并且安装、参考、保护、投影、candidate/manager清理齐全；新宿主UID补查和真实CC原公开开发命令也已闭合。此固定R13材料/990e供应条件下的普通CPU诊断没有待补的本题验收阻断，可支撑既定普通探针准备。已知不完整gold的raw0、公开B的预期末尾rc1均按具体行为解释，没有降成环境失败或冒充修复通过。

本报告不适用于：自主模型成功率、公开盲解、真实AWS一致性全域、正式训练typed-actor资格、训练轨迹捕获、FrozenPatch/a2g全链或旧材料重grade。人工矩阵的FrozenPatch是控制输入；公开CC开发操作则明确没有export FrozenPatch、model_attempts=0。所有原raw和历史身份保留。两legacy false、公开`-q`不提供完整节点ID、actor没有独立Docker调用全集的证据边界均如实列出，不另设审批或机械全重跑要求。
