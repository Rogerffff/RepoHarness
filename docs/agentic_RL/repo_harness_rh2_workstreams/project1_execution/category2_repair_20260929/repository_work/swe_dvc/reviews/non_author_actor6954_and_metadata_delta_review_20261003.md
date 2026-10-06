# 6954 公开 actor 原件与 4166 元数据 guard 窄核

2026-10-03。**6954 本轮 R5 公开 actor 的运输、四条公开开发命令、11 个公开测试及有界清理均有原件支持；4166 v2 未见受影响静态阻断。** 4166／9395 的新命令只核公开开发环境，29／17 是公开基线的静态实例数，尚非这两题的真实 actor 结果。

核查者已见私有题目材料及此前核查，不是 fresh 公开读者。冻结继承链、首请求判据和清理行为复用 [既有入口静态报告](non_author_actor_helper_review_20261003.md)，actual SHA256 `c0c2bb87e00ba6a6450d152e42dbef872ffc7b45a788f188b2ff7581c2e1e7c2`；本次只核实际新原件和 v2 差异。没有运行入口、CPU、SSH、Docker、安装、项目／维护测试，也未改材料、入口或共享文件。

固定请求 actual SHA256 `8c688f340f5190cbca6926604cdc8d2095acc9fcca00ed811e522737f301f302`；所列38份材料／原件全部逐字 SHA 匹配。下述运行事实来自 `public6954_r5_actor003_v1`，不以 helper 的单个成功布尔值代替原件。

## 6954：实际公开 actor 读回

- 输入、运行和代码绑定一致：job `dvc6954-public-actor-20261003-v1-003`，R5 release `cat2-cpu-r2e078079-swe7-git-20261003-v1`。input 的 helper SHA 与归档 actor_check.py、本包 v1 helper 均为 `91c8bb818c10f6492be45f20ada71f252fcb6884aed5c12539c109cb4fe689d0`；input 的七个冻结 code_files SHA 逐一与本地冻结 R5 对应文件一致。prepared summary／manifest／prompts／rollout view／host grading 的身份链完整；host grading 留的是原测试补丁，逐字等于本题 original_test.patch，没有换成本轮有效私有修订。
- 首个真实 Messages 请求 `messages_000.json` 的 user text 逐字包含准备好的 prompt 加中性开发说明。题面实际 SHA `8bdefbf0d354af44abd512469a37c9c9173e8d4cbff4e3e100ea9efbf610b44f`，原有 CRLF 保留；开发说明实际 SHA `08c2eb10117973633bfb40431753064bbbf7efe1886b8db34ab350cd42c8b1da`。开发说明只提供 checkout／解释器／pygit2 pin、已有公开测试和 CLI／临时仓库用法，未出现私有新增测试、候选或修法提示。
- 四个 Bash 调用与归档 commands、stub_script／stub_log 一致；从真实 trajectory 和后续 Messages 的 tool_result 各自重建 `RH2DC_END id=… rc=0`，不存在仅靠总退出码推断各命令运行。捕获大小147／25／1755／5349字节，均小于200000字节截尾上限，public_tests 完整捕获没有被截断。

| 公开命令 | 真实 RC | 捕获读回 |
| --- | --- | --- |
| identity | 0 | uid54321；`/opt/miniconda3/envs/testbed/bin/python`；CONDA=testbed；DVC导入自`/testbed/dvc/__init__.py`；pygit21.14.1 |
| activation_permissions | 0 | `RH2_BASHENV_WRITE=DENIED` |
| public_tests | 0 | `........... [100%]`；`11 passed, 46 warnings in 4.05s`；无skip／failed／error／deselected／xfailed／xpassed |
| dependency_cli | 0 | `No broken requirements found.`；dvc run／repro 已有帮助输出 |

公开 test_show.py 基线 actual SHA `b4f326a46584b7a6e4eae8462ff5018341dee1bbaf2eaef4c5dca37bbf4436eb`；AST 展开为9个无参数实例＋test_log_errors的2个参数实例，共11。helper 输入要求该文件与这份基线 SHA 一致，同时要求私有新建 test_python.py 不存在；v1 helper 沿成功控制流完成这些先决保护后才启动CC。原件没有逐项记录 baseline 的 sha256sum 命令 stdout，故这里以校验过的 helper 控制流、实际退出及公开选择器／11个实例数量交叉支持身份，不冒称保存了容器内完整测试文件快照。实际命令只选公开基线 test_show.py；prelaunch 的 binds／mounts 均为空，未挂载 host private。host 端原 grading 文件存在不等于把它交给 actor 或执行评分。

实际环境：image inspect、actor container_inspect、prelaunch均为 `sha256:083832998996245f4f49eaab3f5f9314fe9fe23bafda7fc9641ae8cec6803c30`；HEAD／sanitize前后均为`28dd39a1a0d710585ff21bf66199208b1b83cbde`。image-facts初态干净，探针NetworkMode=none；探针HostConfig和actor prelaunch均为2 CPU／4 GiB／PID512。actor实测cgroup为`200000 100000`／4294967296／512，uid54321、NNP=1、有效cap为0，privileged=false，cap-drop=ALL；只连接attempt内网relay，外部DNS／直接upstream均DENIED。tmp1GiB、home256MiB，激活文件root:644、agent可读不可写，解释器激活核查无violation。writable-layer quota的8GiB是配置值；prelaunch storage_opt为空，本报告不把它写成已实测生效的磁盘限额。

真实CC版本为2.1.205；trajectory有5个message_start与5个stub Messages原件对应，4个工具结果、1个success result，terminal_reason=completed，无permission_denials。harness返回0／log_complete=true／stderr零字节；slot_job status为finished、returncode=0。清理原件记录探针rm返回0，actor rm返回0，network／relay失败列表为空，stub_rc=0，标签容器／网络及二次residual_after_force均为空；post_run_facts agent进程为0，容器内.harness／launcher／done marker均ABSENT。该清理结论覆盖本attempt结束时的原件，不是此刻远端普查。开发测试产生291个较新的路径（可见pycache），属于已授权开发命令写入，未被错误声称工作区毫无写入；git status原件为0行。

非阻断记录：冻结 devcheck 的 pytest_counts 对这次 `-q` 无等号装饰终行未解析，attempt 的public_tests.pytest为null；并且passed／skip数量仍未进入helper成功谓词。这次已直接读完整捕获确认11实际通过，因此不影响本轮结论，未改冻结parser，也未把便捷字段补成新的原件。

## 4166／9395：新公开命令的静态范围

两份命令都是身份／既有激活文件权限／已有公开基线测试／pip check＋CLI帮助；4条均expect=zero。4166只核公开pathspec0.8.1、NetworkX2.3+rh2.1和原ignore两文件；9395只核公开pygit21.14.1及原multistage文件。测试命令去掉PYTHONPATH前缀后与各自public_development.md逐字一致，没有应用测试补丁、安装／联网、私有新断言或评分命令。

| 题目与公开基线 | actual SHA256 | 静态实例来源 |
| --- | --- | --- |
| 4166 unit/test_ignore.py | `67cff53e0626e13934a1b74461d5d2648c8e56859fc1aadd9fc067282b6c48ed` | 2个普通实例＋match参数10个＋默认忽略目录参数3个＝15 |
| 4166 func/test_ignore.py | `0b11d0098c2e97b3cc1f454cba2fbccdbb3e144545b45854aff75cf0be8f9602` | 12个普通实例＋collecting_dvcignores参数2个＝14 |
| 9395 func/test_repro_multistage.py | `ca738a7a94b991881a48abdb02aa1d27565f087e5742511d1fbbd752afde99e1` | 13个普通实例＋两个multiline布尔参数族各2个＝17 |

因此4166是15＋14＝29，9395是17；这些来自公开基线，不是带原私有补丁后的63／30个执行节点，更不是新有效断言的66／41个节点。本次只做AST展开，未来真实运行仍须按捕获核实际passed、skip和缺席，不能把静态数量当collection验收。

## 4166 v2：精确接受已知元数据差异

相对v1，v2只有开头说明及image-facts的初态guard差异，原继承／profile／公开运输／运行／清理／最终判据未改。已知原件 `source_worktree_before.txt` actual SHA `2125b1b2b78f998d3142b6cb8d61ebaf624e282d8e9fa0d4b2a6c6671e0041fc`，首行HEAD为`520e01f11305aba1994df354adef86e6d90180de`，随后恰是` M setup.py\n`及完整diff。pin中的porcelain、diff原文及两项SHA均与原件逐字相同；唯一源码树差异是setup.py测试依赖元数据将moto1.3.14.dev464换为1.3.14，不是候选改动。

v2第100–117行只有在task_id恰为`swe_gym_lite::iterative__dvc-4166`、expected_initial_porcelain恰为` M setup.py\n`、expected_initial_diff_sha256恰为硬编码`sha256:8bd072b6e35dd358d920432c24b35048d4e51a9d0bc78972ceeb18e302b8dfbf`时才允许例外，并重新读完整`git diff --binary`，要求RC=0和整个stdout SHA一致。最终probe还必须具有`PORCELAIN_BEGIN\n`＋精确porcelain＋`PORCELAIN_RC=0`的连续片段。多一个dirty／untracked／staged路径、setup.py另一种改动、其它task或另一个diff SHA都不能满足这组条件；默认空expected仍要求干净树。因此未见泛化接受其它dirty树的静态阻断。actual v2 helper SHA和pin.helper_sha完全相同。

本次没有4166 v2的运行原件，不称运行验收。4166 v1在自有clean guard停止／未启动CC的完整失败及清理归档正在另行补齐，不在本固定38文件范围内，本报告不代替它的失败／清理读回，也不把后续attempt预判为成功。

## 限制与真实 SHA

结论分别是6954公开actor环境与运输的运行读回、4166／9395公开命令静态核查、4166 v2 guard静态核查。没有正式RH2评分／逐键reward运输、候选补丁求解、actor训练消费、环境或训练用途资格、真实模型探针的验证。中性说明是首次请求运输事实，不是fresh公开读者审查。

以下为请求38文件的actual SHA，逐项重新读取而非抄作者摘要。`运行根/`指请求中的public6954_r5_actor003_v1；`本包/`指swe_dvc本包。原件哈希并不能独立证明日志记录以外的远端状态。

| 文件 | actual SHA256 |
| --- | --- |
| 运行根/actor_check.py | `91c8bb818c10f6492be45f20ada71f252fcb6884aed5c12539c109cb4fe689d0` |
| 运行根/attempts/dvc6954-public-actor-20261003-v1-003/activation_check.json | `1ec05db66391f9ff3837e518a1bd7620c4c37b6f3693f846ae73a98a61321f9c` |
| 运行根/attempts/dvc6954-public-actor-20261003-v1-003/attempt.json | `42df02ea4ca20adad9ebc18e14a862025bcf3cf1c28e2911ae18af3fd89f47d4` |
| 运行根/attempts/dvc6954-public-actor-20261003-v1-003/bringup_artifacts/cc_version_observed.json | `c2b9bcf966c47d9a00227877026cb90b76afed482fd0df4e0ac12caab786bacb` |
| 运行根/attempts/dvc6954-public-actor-20261003-v1-003/captures/activation_permissions.out | `a704c582aef5faf7a700561b8e0e1b687b3977f8e1aed514fb8a4845b58af0db` |
| 运行根/attempts/dvc6954-public-actor-20261003-v1-003/captures/dependency_cli.out | `702a03ace7ed8641e3a152df46d844ccbd8c8c1cda43de5769563bc46cd92ec7` |
| 运行根/attempts/dvc6954-public-actor-20261003-v1-003/captures/identity.out | `a9e0004f363d5bb50efef3771ec4a4051c127756f1581e16fc4dadea9e0a1704` |
| 运行根/attempts/dvc6954-public-actor-20261003-v1-003/captures/public_tests.out | `5aa6f55f2605bd00400f538b42ab886274ef5e2f8319d8d665701708fe674954` |
| 运行根/attempts/dvc6954-public-actor-20261003-v1-003/harness/stderr.log | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| 运行根/attempts/dvc6954-public-actor-20261003-v1-003/harness/trajectory.jsonl | `f34d2ded4f46e831b0ce4e93ca81a6c6e70a98a0c0d08935d9cb51dfc9f5a5ea` |
| 运行根/attempts/dvc6954-public-actor-20261003-v1-003/post_run_facts_root.txt | `8073034b33c2c14480a74caf9376f0690ddda43062f28ffd246ab484d7a065b1` |
| 运行根/attempts/dvc6954-public-actor-20261003-v1-003/prelaunch.json | `1030c7f51134a3008a19eb34e924241add56d8b7393d46f39074679c142435d4` |
| 运行根/attempts/dvc6954-public-actor-20261003-v1-003/stub/requests/messages_000.json | `89b9fe99079ba7b15f96a4efc10edb657076eb491e2aaa69844dc15ef8143d60` |
| 运行根/attempts/dvc6954-public-actor-20261003-v1-003/stub/requests/messages_001.json | `328771c30bd2c89c285f5629652aa8e25065cd665093e5af0169d23dd158184a` |
| 运行根/attempts/dvc6954-public-actor-20261003-v1-003/stub/requests/messages_002.json | `977a98d1aeec68b3e656203623200dfa6bab6f9f84466b450f1e4563e40ec37b` |
| 运行根/attempts/dvc6954-public-actor-20261003-v1-003/stub/requests/messages_003.json | `2abdc941f53b5bd9a8e5d7e8c8630aba684d9ab48d89c31d9536c22d8bb213ca` |
| 运行根/attempts/dvc6954-public-actor-20261003-v1-003/stub/requests/messages_004.json | `e95209d919defd611bd0c0bc6235d0ca637c9e7a833c909181532c74a0570a04` |
| 运行根/attempts/dvc6954-public-actor-20261003-v1-003/stub/stub_log.json | `a2b5c37b44dedb9a66e2e4b3cb60ee25046cf7aafbfca184e81535d759b61fcf` |
| 运行根/attempts/dvc6954-public-actor-20261003-v1-003/stub_script.json | `680d8def53154c72613c8cb60b24aff53d50f15ada53bc32b7a91e5d53e14b14` |
| 运行根/attempts/dvc6954-public-actor-20261003-v1-003/stub_stdout.log | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| 运行根/commands.json | `82cf057ad54730b91caabbca42df943f4f440720057ea35855ef03f3b565deb5` |
| 运行根/input.json | `899436a707c966db0495149531a5ad55eb77670d3e8b8485cc9cec87a68eb2ed` |
| 运行根/prepare.log | `79e29f023d067a4c8ca5f598b212d81a18ee1190c2b2e232d6fb0c2a00940ab1` |
| 运行根/prepare_invocation.json | `e98aafbfd80b72b261c95bd22307c848279dd7d9c8d6161131127f4cd7a019b9` |
| 运行根/prepared/prepared_manifest.json | `31c44ce924086abc289b47a05ff317643e7c8e332eb3639c3f43eb1edb78e22f` |
| 运行根/prepared/prompts.jsonl | `d3b07a47402be7ca3629fbe94682a4a516293beea6491bcfbf064e1b08678188` |
| 运行根/prepared/replay_summary.json | `f84b0049f0842372c679b110e8bd41c5aa45396be27b5b6ed8e5d7d5140f7482` |
| 运行根/prepared/rollout_task_views.jsonl | `e4fffa52214b9e8e140225eeedc47ac4f4bdb215b1bbe4a8b90ae80c6f56d65a` |
| 运行根/private/host_grading_views.jsonl | `6f7d79e25094f8a4af0f6ca1b5d52a034b26b8008ec6e664f058af7c8268ce24` |
| 运行根/public_development.md | `08c2eb10117973633bfb40431753064bbbf7efe1886b8db34ab350cd42c8b1da` |
| 运行根/seed.json | `cc637ed4fac2833456c7a4f158fa6a375c8403350ce799df30e1035026a29a97` |
| 运行根/slot_job/status.json | `4568ef2ad29d8462b524fb8c6e3d8fce684946a6757542c0c76e6ed1ebb56ad6` |
| 运行根/slot_job/stderr.log | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| 运行根/slot_job/stdout.log | `de7637add8024bb5ccbef7c49f1e7a84b5a5d98e17cb29ab7c760b274a1742d4` |
| 本包/public_actor_check_v2.py | `f513232d19dae5c28e3a0ae8600cc9ad7cbab71aa0a7582f5abd9ceccaf7bd8d` |
| 本包/tasks/iterative__dvc-4166/original_image_metadata_pin_v1.json | `0289b52e960d2b75f72e15f91a1223e2ab3700c486125f5d27a8f805fb315fd6` |
| 本包/tasks/iterative__dvc-4166/public_actor_commands_v1.json | `caeec2a908752f3b09bdd3cdc7d025ba3e185dae5f16e58203346fd9cd50f7ec` |
| 本包/tasks/iterative__dvc-9395/public_actor_commands_v1.json | `49c50eedd24522d54343e8c39b841745ba211755506c005ca6b2ea48551e3508` |
