# Pandas 两题非作者 CPU 原件核查

2026-10-03。本次只核已完成的 CPU 证据。**固定镜像与48106离线资产恢复、48106原公开 actor 窄开发检查、50319原测试下的 root NoOp/局部 None 行为校准，均有原件支持；未发现阻断这些限定结论的具体矛盾。** 50319 新公开 actor 尚未完成，不纳入本次已证结论。两题新材料的正式登记、manager 评分与探针提交仍待，CPU 原件通过不能提升为训练资格。

核查者未参与本包材料编写或远端执行。接触上下文包括父任务交接、作者 `preparation.md`、`cpu_asset_results_20261003.json`、`cpu_calibration_50319_20261003.json`、作者 `local_reference_readback.json`、已有非作者材料报告、当批流程及所指父版本；本次并非全题盲审。作者摘要只作为待检主张，结论由接收原件、原始请求/轨迹、完整 pytest 摘要、公开 base、来源 grading 和冻结脚本独立重建。

## 适用版本与原件完整性

- [已有材料窄核](non_author_material_review_20261003.md)按版本复用。本包 manifest 所列15件材料加 generator/offline checks 共17件，重算 SHA 全部匹配；未重做断言设计审查。两题修订单所指父 grading/public/source/test/binding 文件 SHA 及 grading/public canonical digest 均匹配。来源参考逐项核对：48106 保持16 F2P/1020 P2P；50319 本次使用原1 F2P/109 P2P，原测试补丁与父 grading 的 `test_patch` 字节相等。
- 48106 已完 actor 的 `job_status.json` 明确执行首版 `cat2-cpu-r2e064065-swe5-20261003-v1`，使用 `runtime_cpu_v2`。本地冻结 tar 内 manifest SHA 为 `282021962a92b510f077385660ac56acedcd7fac1d97e63db3baa98e4dcc057f`（794文件）；不能改记为第五版。
- 50319 私有校准执行第五版 `cat2-cpu-r2e078079-swe7-git-20261003-v1`，使用 `runtime_cpu_v2`。冻结 tar 内 manifest SHA 独立重算为 `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`（837文件），与 cpu-c 发布读回一致。本次只核所用相关脚本的 manifest 摘要，未做全 release 验收。该版尚未登记 Pandas 本轮修订。
- 两版冻结 `devcheck.py`、`acceptance_startup_2.py` 的 SHA 分别为 `75399297da458697ebcd17e6ca79aad90b56e4dbdda3214a4c70f82a4b389160`、`c67194f09e202c1cd1e83a3a1fbf5df7706952d2e542f97a4b2f3882604dc5d1`；冻结 `private_behavior.py` 为 `379c4610b19aafa829fcf7967ad95d0ac9f5374c9e85f16c0b62a01a25cbb7bc`，与接收的 `frozen_private_behavior.py` 字节相等。没有把当前可变工作树的 runner 当作已完作业版本。

以下原件根目录均在 `runs/category2_repair_20260929/pandas_cpu_20261003/`；后文用短名定位文件及行号：

| 短名 | 目录与清单 | 独立重算结果 |
| --- | --- | --- |
| A | [cpu_c_assets_48106_received](../../../../../../../../runs/category2_repair_20260929/pandas_cpu_20261003/cpu_c_assets_48106_received/receipt_manifest.json) | 清单9件，字节数/SHA全部匹配 |
| B | [cpu_c_completed_assets_and_actor_received](../../../../../../../../runs/category2_repair_20260929/pandas_cpu_20261003/cpu_c_completed_assets_and_actor_received/receipt_manifest.json) | 清单16件，字节数/SHA全部匹配 |
| T | [cpu_c_48106_public_actor_trace_received](../../../../../../../../runs/category2_repair_20260929/pandas_cpu_20261003/cpu_c_48106_public_actor_trace_received/receipt_manifest.json) | 补充清单10件，字节数/SHA全部匹配 |
| C | [cpu_c_50319_private_calibration_received](../../../../../../../../runs/category2_repair_20260929/pandas_cpu_20261003/cpu_c_50319_private_calibration_received/receipt_manifest.json) | 清单31件，字节数/SHA全部匹配 |

66件是本次四份 receipt 的文件数，不是66次实验或66项资格检查。`C/local_reference_readback.json` 是作者后生成文件，不在31件远端 receipt 内；本核查从两个原 pytest 摘要自行重建110个来源状态后，才与它逐项比较，结果一致。两份命令输入 manifest（48106三件、50319七件）也重算匹配。

## 固定镜像和48106十个历史 wheel

两次真实 prepare 均退出0：48106 于2026-10-02 17:25:21 UTC结束，50319 于17:42:47 UTC结束。镜像登记摘要与原公开 bundle 相同，拉取日志确为摘要固定引用；`images.json` 记录实际 RepoDigests 包含该引用、平台为 linux/amd64。

| 题目 | 登记 manifest digest | 实际 image ID |
| --- | --- | --- |
| 48106 | `5300b53bb30e5b29f5425967f370e3a72c42b9bbffeb4c2fd1d3ba831716bdd5` | `0e706113dce17d30fade5723a2a71c162afa253d777fd7fa139c5b89cf05c4b8` |
| 50319 | `e645e4346df9200174e8b879ad8fb7a09f64f91c7375311e2569596d054ba21e` | `a3f20f616f78963bee9c87426b8a93c28fb63a6ade97d0f444115279c28f859a` |

表内均为 SHA-256 值。证据：`A/job_status.json:6`、`A/job_stdout.log:65`、`A/images.json:7`；`B/50319_job_status.json:6`、`B/50319_job_stdout.log:38`、`B/50319_images.json:7`。

48106输入的十个 wheel 的文件名、长度、SHA与历史 `runs/env_recipe_repair_20260919/pandas_meta_v3/tasks/pandas-dev__pandas-48106/assets_manifest.json` **整个数组相等**。对本次 `local_compat_wheels/` 十个实际文件独立重算，共17,476,086字节，长度及SHA逐个匹配。远端 prepare 使用 `--wheel-source`；脚本逐文件核长度/SHA、复制，再核目标SHA，作业退出0和原 `assets.json` 支持本次资产恢复。

`A/Dockerfile:1` 只有固定 `FROM` 与 `COPY compat-wheels/ /opt/rh2/compat-wheels/`。原构建日志 `A/job_stderr.log:24` 显示实际 COPY，`:30` 生成镜像 `sha256:53b17fe21e906498091df64913c28682c23c6eaad8fbc7106fffa737d170860a`。无 `RUN` 安装、源码补丁或测试执行。基础层保留由已执行脚本的 RootFS 前缀断言及退出0支持（`prepare_cpu_assets.py:95`起）；接收件没有完整的原 `docker image inspect` RootFS 数组，本轮未重新导出镜像层或远端 wheel。此处结论限于记录支持的资产恢复，不能据此称安装配方执行、正式评分或 actor 资格已经通过。48106 actor 实际使用原公开镜像，未使用这张 grader COPY 层。

## 48106 原公开 actor：四条命令确实运行

作业 `pandas48106-public-v2-a334edd8fc79` 的宿主退出0、harness退出0；前后 HEAD 均为 `8b72297c8799725e98cb2c6aee664325b752194f`。实际容器镜像为上表48106原镜像，2 CPU/4 GiB。预启动检查原件 `B/48106_actor_prelaunch.json:47`起记录 UID/GID54321、有效/允许能力为0、NNP=1、工作目录可写且属主54321、外网及直连上游被拒；`ok=true`、无 violations。激活检查 `B/48106_actor_activation.json:8`起记录 `testbed` conda 前缀、`/opt/miniconda3/envs/testbed/bin/python` 和相同 `sys.prefix`。

四条命令由输入文件、桩回复、原轨迹的 Bash `tool_use` 逐项核对，而不是只读 `commands_result`。每个工具调用 ID 与后继 `tool_result` 一致；原逐退出状态如下：

| 命令 | 实际内容和结果 | rc | 原轨迹行 |
| --- | --- | --- | --- |
| env | `id`/Python/导入来源；UID54321、Python3.8.20、解释器在testbed env、`pandas.__file__=/testbed/pandas/__init__.py`、版本对应base | 0 | 调用6，结果12 |
| mcve | categorical Series 后执行 `s.loc[3] = 0`；在原源码的 `_ensure_dtype_type` 路径抛 `TypeError: type.__new__() takes exactly 3 arguments (1 given)` | 1 | 调用17，结果21 |
| setitem | 原公开 `pandas/tests/series/indexing/test_setitem.py -k 'categor or enlarg'`；14 passed/1854 deselected，0.61秒 | 0 | 调用26，结果32 |
| tree | `git status --porcelain`无输出，HEAD仍为base | 0 | 调用37，结果41 |

实际命令保留在 `B/48106_actor_attempt.json:83`起、T的 `stub_script.json` 和 `harness/trajectory.jsonl`；完整输出是B的 `48106_actor_env.out`、`48106_actor_mcve.out`、`48106_actor_setitem.out`、`48106_actor_tree.out`。setitem管道显式 `exit ${PIPESTATUS[0]}`，没有用 `tail` 的成功退出冒充pytest成功。env命令含多个顺序子命令，整体rc不能单独证明所有中间子命令成功；本次只据实际输出确认UID、解释器和导入，没有声称缺失的build目录属主输出已通过。mcve的非零符合原未修复问题，不是解题成功；14项是公开窄开发测试，不是1036个来源参考的正式评分。

**真实桩请求/轨迹已闭合。** T的 `harness/trajectory.jsonl` 为27,377字节、50条可解析事件：10 system、30 stream_event、5 assistant、4 user、1 result；5个 `message_start`。`stub/requests/messages_000.json`至`004.json`为五个实际请求，消息数依次1/3/5/7/9；均用 `slime-actor`、stream=true，与 `stub/stub_log.json` 的请求长度和五个回复步骤一致。前四个回复驱动四个 Bash，后四次请求逐项带回前一个工具结果，与轨迹内容/ID相等；最后轨迹第50行是success结果、5 turns、`is_error=false`。这证明真实 Claude Code 桩端点开发链，不能算真实模型求解、候选质量或正式题面消息交付验收；请求初始用户消息实际为固定devcheck指令。桩脚本及全部四个实际 Bash 均无本轮私有候选/新测试交付。

**`bashenv_denied_for_agent` 原值必须保留False，解释为未请求这项通用探测。** 首版冻结 `acceptance_startup_2.py:346` 仅在工具结果出现 `RH2_BASHENV_WRITE=DENIED` 时设True；`:43`的通用写入命令是 `: >> /rh2/bash_env`。本次替换为四条公开开发命令，桩、轨迹及五个原请求都没有该命令或标记。因此不能把False写成写入成功/权限失败，也不能将“所有命令符合预期”写成“全部通用检查为True”。预启动原件另有实际 `ACTIVATION_WRITE=DENIED`（`:75`），那是另一项已执行检查。

清理原件 `B/48106_actor_attempt.json:285`起：container_rm=0，network/relay failures为空，stub_rc=0，label容器/网络为空，最终复查 `residual_after_force=[]`。冻结devcheck在查询失败时写显式失败标记（`:189`起），空数组不是查询失败默认值。工作树tracked status为0，容器内agent进程为0；`:277`仍记录353个较新的文件，符合公开测试会生成运行产物，不应声称完全没有文件写入。本核查确认作业结束时的清理记录，未重新连接宿主核当前状态。之前75为未获槽请求，不另算actor失败或reward0。

## 50319 root私有校准：真实构建、加载和原测试

作业 `pandas50319-private-none-c227640c9e15` 于2026-10-02 18:16:55 UTC启动，18:27:59 UTC结束，宿主退出0。`C/spec.json`固定原50319 image ID、2 CPU/4 GiB、testbed Python前缀；`C/frozen_private_behavior.py:58`起确以network=none串行启动两个私有容器。两份 `initial.txt:1`均为UID0(root)，`:2`均为base `1613f26ff0ec75e30828996fd9ec3f9dd5119ca6`，原始工作树无porcelain输出；所有准备步骤rc0。该入口没有manager评分调用，宿主总rc0也不表示每条行为检查成功。

| 原件命令 | NoOp rc | None rc | 正确解释 |
| --- | --- | --- | --- |
| compile | 0 | 0 | NoOp输出 `RH2_PRIVATE_NOOP_USES_ORIGINAL_COMPILED_IMAGE`，仅使用原扩展；None真实执行 `python setup.py build_ext --inplace`，640.2217秒 |
| source_identity | 0 | 0 | 两臂均由新Python进程加载`/testbed`的pandas和parsing `.so`，源码SHA符合各自输入 |
| runtime_contract | 1 | 0 | NoOp在第一个原输入猜格式时抛ValueError，尚未执行数组调用；None两个输入与数组检查通过 |
| original_parsing_module | 1 | 1 | 均收集114项、113 passed/1 failed；唯一失败原因不同，见下文 |

退出状态/时长来自 `C/summary.json:19`起及`:75`起；shell原命令在 `C/spec.json:24`起，原输出各保留stdout+stderr全量。8份命令输出的实际字节数均与原summary的stdout_bytes+stderr_bytes相等。NoOp的“compile rc0”不能称重新编译通过。None的构建门使用 `python setup.py build_ext --inplace && touch /in/build_ok`，后续命令先核marker；它没有用 `|| true` 或管道掩盖构建退出。

`C/none_fallback/compile.out:1`明确“because it changed”并Cythonize `parsing.pyx`；`:102`构建parsing扩展，`:104`编译C、`:105`链接新 `.so`、`:195`复制到`pandas/_libs/tslibs`。这些日志与真实rc0、后续独立进程加载共同支持候选构建成立，不能仅凭 `.pyx` 补丁存在作此结论。

原测试patch、候选patch与准备包及父版本字节一致。本人在内存中按候选唯一改动从所指公开base重建源码，重算出下列源码SHA，与两臂 `source_identity.out:1`严格一致：

| 身份 | NoOp | None |
| --- | --- | --- |
| `parsing.pyx` SHA | `5c8e81b9914bc6448b21a909cf13d3c2e7799e63e92d386042dd4262b6d048aa` | `54262be7b7f417a620f4f15e8703453bc703652a8e4001a0d1e8f8cca594a8ca` |
| 实际加载 `.so` SHA | `127481b230a3c52c886aea1d01b8957e61b55ab106e315f93c4a8f399ecd425c` | `20698f3e6d4a4ad47f51c2755a81ff538741778ea3cfd5cd32c328ff7591733d` |

两臂导入路径均为 `/testbed/pandas/__init__.py`、`/testbed/pandas/_libs/tslibs/parsing.cpython-38-x86_64-linux-gnu.so`，版本为 `2.0.0.dev0+940.g1613f26ff0.dirty`；dirty包含本次原测试补丁，不能仅凭版本标签推断候选已加载。此处实际源码hash、重建日志、不同 `.so` hash及行为变化共同排除了“只改源码但仍载旧扩展”的当前证据矛盾。

## 50319所有来源参考、七成员与真实调用者

我自行从两份 `original_parsing_module.out` 的short summary保留完整nodeid及状态，用原grading的109个P2P及1个F2P逐来源对应；未运行作者parser/binder或读回脚本。各摘要都有且仅有114个物理节点、无重复，113 PASSED/1 FAILED；109个P2P完整展开为113个PASSED节点，无缺席、非PASS或来源外节点。原F2P展开为唯一失败节点。109是来源键的分母，113是参数展开后的物理P2P分母，不能互换。

完整绑定三组1/2/4成员在两臂各只出现一次PASSED，成员集合没有因空白截断缩减。以下均带公共前缀 `pandas/tests/tslibs/test_parsing.py::`，表内反斜杠保持日志原样：

| 完整成员（前缀省略） | NoOp摘要行 | None摘要行 |
| --- | --- | --- |
| `test_is_iso_format[%Y\\%m\\%d %H:%M:%S-True]` | 129 | 126 |
| `test_guess_datetime_format_with_parseable_formats[2011-12-30 00:00:00-%Y-%m-%d %H:%M:%S]` | 71 | 68 |
| `test_guess_datetime_format_with_parseable_formats[2011-12-30 00:00:00.000000-%Y-%m-%d %H:%M:%S.%f]` | 95 | 92 |
| `test_guess_datetime_format_no_padding[2011-1-1 00:00:00-%Y-%d-%m %H:%M:%S-True-None]` | 124 | 121 |
| `test_guess_datetime_format_no_padding[2011-1-1 00:00:00-%Y-%m-%d %H:%M:%S-False-None]` | 123 | 120 |
| `test_guess_datetime_format_no_padding[2011-1-1 0:0:0-%Y-%d-%m %H:%M:%S-True-None]` | 120 | 117 |
| `test_guess_datetime_format_no_padding[2011-1-1 0:0:0-%Y-%m-%d %H:%M:%S-False-None]` | 119 | 116 |

原locale-sensitive三项在NoOp摘要100/101/102行、None摘要97/98/99行均为PASSED，本次没有skip/xfail替代执行。

唯一旧F2P完整节点为 `test_guess_datetime_format_with_parseable_formats[27.03.2003 14:55:00.000-%d.%m.%Y %H:%M:%S.%f]`。NoOp原日志 `C/noop/original_parsing_module.out:13`起在调用处因 `_fill_token` 的 `int('')` 抛ValueError；None原日志 `C/none_fallback/original_parsing_module.out:13`起已到相等断言，实际 `None != '%d.%m.%Y %H:%M:%S.%f'`。这证明原私有断言拒绝本次局部None路线，而不是None候选仍触发原异常。

真实调用者由 `C/check_runtime_contract.py:23`起核两个输入 `27.03.2003 14:55:00.000`、`28.04.2004 16:07:08.123456`，并实际执行 `pd.to_datetime(strings, dayfirst=True)`。`C/none_fallback/runtime_contract.out:1`记录两次guess均null，数组结果为 `2003-03-27T14:55:00`、`2004-04-28T16:07:08.123456`，`:2`是独立None-route确认；`:3`保留“each element will be parsed individually by dateutil”的UserWarning。因此真实数组调用既没有丢日期/时间/微秒，也实际承载了None回退。NoOp runtime在首次guess处停止（`C/noop/runtime_contract.out:5`起），不能声称它的数组调用也执行过。

两臂 `C/summary.json:50`起与`:106`起均记录rm_rc=0、query_rc=0、remaining=[]、stderr空；冻结helper在精确容器名查询失败或残留时停止派发（`:91`起）。本次支持两容器结束时无残留，不表示核了其它任务容器或当前宿主状态。两个前置75仅为无run槽，不是两次失败校准。

## 已证范围、未完成事项与停止条件

本次无需另加用户决策，也未改任何训练语义或准入规则。可以复用的事实为：已固定资产、48106新宿主原公开命令/非root身份、50319局部None路线的真实root构建及原109来源P2P/真实数组行为。原NoOp/gold历史reward保持原版本，本次没有新manager reward。

以下事项保持未完成，不因本报告而放行：

1. 48106完整绑定在正式不可变材料中的登记/选择/解析消费及相关正式评分；本次14项公开测试不证明新绑定已经生效。
2. 50319新有效补丁替换原补丁、1→2 F2P和完整绑定的正式登记/保护/恢复/selector/parser一致性，以及已列正负矩阵的manager评分。原113/1结果不等于新材料验收。
3. 50319新公开actor在实际非root身份下的构建、加载和受影响公开测试。当前仍未有完成原件，本次未核它的输入/运行结果，不以root校准替代actor权限；完成后只补这一项窄核。
4. 两题按既有条件提交统一探针、模型反馈及用途判断；本次不宣布probe_ready或training_qualified。

停止条件：已完成CPU原件核查和限定报告到此收口；若新actor完成或正式材料/评分带来具体差异，仅核对应新增证据。不扩到全仓、新日期语法、额外候选或全题重新审查。

本轮仅文件读取、`rg`、stdlib JSON/hash/tar及日志/字符串分析；没有运行作者生成器、parser/binder/读回脚本，没有导入pandas/项目模块、编译、pytest、安装、下载、SSH、容器或模型作业，也没有远端清理、提交或推送。T补充原件由执行者按本核查缺口取回，原三份receipt未回写；本人只核其已保存字节。唯一写入为本报告，使用排他创建，不覆盖已有作者材料、共享代码或他人结果。
