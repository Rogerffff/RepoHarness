# coveragepy 016a：非作者 CPU 窄核

2026-10-03。**结论：通过。固定R6下，本题满足普通基座探针的题级CPU条件，未发现具体阻断。** 不授予训练资格，不将修订题结果报告为未注明版本的原benchmark成绩。

核查身份：Codex非作者subagent `/root/coveragepy_016a_cpu_review`，未编写本题材料。已接触本题公开、私有材料、候选、作者摘要及指定旧独立审查，**不是fresh公开读者**。共用文件仅核目标行和必要版本身份，未用其他题私有方案判定。依现行三方流程复用有效审查，本轮只补正式落地、实际CPU与公开交付。

实际操作：本机离线原件读取、SHA/size、JSON/AST、固定parser纯函数、独立摘要解析、Git binary literal内存解码。未SSH、Docker、调用模型、运行项目测试或新增实验／角色链。远端实际行为据保存的原日志、ledger和回执核查，不称核查者现场重跑。

## 固定版本与材料

固定release：`cat2-cpu-r2e080087-swe8-git-20261003-v1`。本地入口：`runs/category2_repair_20260929/releases_20261003/r2e_080_087_swe8_git_candidate_v1`。manifest SHA实算 `ab0a3a13fd65e0ea4cd60541ea3b37b01196170477e25832df246f33ea208828`；855成员的size/SHA逐文件全部一致。pins v19指向的registry、raw、rule source、image facts及source revision实际文件SHA全部核对。

从固定raw依次重放001／086／087，old唯一命中、before/after SHA相同。086与本题test_1_v2.py、087与statement_v1.txt逐字相同；001仅将MockingProtection目标键FAILED改为PASSED，expected仍15键。host grading/public目标行与release ingest相同，prepared_manifest/private实际SHA与replay_summary一致。

| 身份 | 核对值（SHA-256） |
| --- | --- |
| statement | `e654fab906c8c9b5a994aed85c7e924c2389f10842dc319d0249060d3ee7d1e1` |
| test_1.py | `ccdd7d89bb17177ab5922577be001e1f3000c0a2f53be8ec10eba2b3b849706b` |
| expected | `f353157ec8e86a79e172920a44f6cbbdc8d1bb049c77f8292f7bd70dfc713e3e` |
| prepared_manifest | `0f8e89800b5678529c5ee852657fc6bff5c95143cb192086d958de8e1df3d79f` |
| host grading文件 | `78b28860a8019d85dbc96c223eb3a90e79606511dcdc10e1d1482c5e8609c195` |
| source image digest | `71895ed487c4080a40879049ec72d6eb53daf5356c6a7abb321ba46105a05a39` |
| derived image ID | `07a8684c42e242e1f9277011780f825411a52a439bce1cd1ce2daec3df477514` |
| recipe digest | `98a6ecb6b08fc8e2e832dead72e644e3b55a7cfaa74eac59aac44ab48edb9916` |

从086独立重建material manifest.tsv，结合实际context脚本SHA计算base／sysconfig配方，结果与facts相同。原build.log记录固定源digest、086应用、隐藏树15796de8…与输出image。原integrity_base／derived中工作树文件、venv非bin文件、Git状态逐字相同；bin除shebang外摘要相同。21项facts通过。actor与矩阵原件对应同一derived image／recipe及base `5bb5da50b182583036b7808bb32f2c8c191d9d26`。

## 正式14行原件核对

从每行eval.log完整Start／End Test Output内读取首个pytest summary，固定parser与核查者独立regex解析相同，再逐键与expected、原ledger／diagnostics和作者摘要对拍。

| 候选 | 匹配／15 | reward | 实际应用路径 |
| --- | --- | --- | --- |
| base | 14/15 | 0 | NOOP |
| gold | 15/15 | 1 | `coverage/inorout.py` |
| skip_write | 15/15 | 1 | `coverage/sqldata.py` |
| convert | 15/15 | 1 | `coverage/sqldata.py` |
| lines_only | 14/15 | 0 | `coverage/sqldata.py` |
| ascii_only | 14/15 | 0 | `coverage/inorout.py` |
| catch_save | 14/15 | 0 | `coverage/control.py` |
| wr_swallow_flush | 14/15 | 0 | `coverage/collector.py` |
| wr_loop_abort | 14/15 | 0 | `coverage/sqldata.py` |
| wr_latin1 | 14/15 | 0 | `coverage/inorout.py` |
| wr_hardcode | 14/15 | 0 | `coverage/inorout.py` |
| rv_skip_write | 15/15 | 1 | `coverage/sqldata.py` |
| rv_convert | 15/15 | 1 | `coverage/sqldata.py` |
| rv_collector_warn | 15/15 | 1 | `coverage/collector.py` |

base及7错误候选均只在 `ExecTest.test_unencodable_filename` 不符；6合理路线全部15/15=1。目标测试实跑，覆盖初始坏filename、分支模式另一坏名、正常非ASCII文件及独立数据读回；不要求坏名最终表示或特定告警，skip／encode／collector warn均接受。语义界限复用已有非作者材料审查，本轮未从头重建。

13份补丁实际SHA与ledger一致，均由agent/54321以git_apply应用，路径正确；base是独立NOOP。原gold.patch、固定validation golden_patch、从固定raw parsed_commit经固定gold extractor重建的字节完全相同，SHA `fa506eaa00a0ff3d8b0873647bf2e1c070402085652b1a386a981b18b35162f2`。

14行driver_rc均0、执行退出0且测试段完整；正对照test_rc0，负对照1。没有stage_error、partial log、infra_failure_detail或runner_integrity_changed。负对照保留tests_failed。导入均为 `/testbed/coverage/__init__.py`，runner前后摘要相同。原grade.log每行创建／移除容器均1，cleanup移除成功，容器／网络label查询rc0且无残留；矩阵job自然退出0。逐行patch／log／ledger SHA与15键结果在JSON中完整保留。

## 实际公开交付与FrozenPatch往返

首messages_000.json实算SHA `3bc1587640b46536f89cf4d88f7b4002cdad3b3e2526f367e9e09d93605ebde9`，包含完整087 statement和完整rendered prompt（SHA `6fe556b077447647feba609e8731dd2ab765e3a0b1b105e0c611edfa5cf770f7`）。实际轨迹为Claude Code2.1.205对CPU桩的真实交互；agent uid54321、cwd `/testbed`、Python3.7.9／`/testbed/.venv/bin/python`、工作树导入、SQLite3.33.0、CTracer available、activation与三项预检正常。

读者四命令原件与actor计划cmd／timeout_s逐字相同，时限30／30／30／180秒。固定runner追加退出码echo及30秒Bash工具裕量（timeout60／60／60／210秒）；CC轨迹省去 `cd /testbed &&` 前缀，实际cwd和agent facts为 `/testbed`，其他正文与工具timeout同stub输入。这是执行层明确差异，不把工具时限称为读者原时限。

原CC轨迹五次Bash及实际tool_result存在：预检0、环境0、题面示例1（cov.save路径UnicodeEncodeError）、普通保存和load／第1行断言0、公开回归0（154 passed，1 skipped）。未用作者摘要或模拟文本代替实际返回。

FrozenPatch有两份新增SQLite数据，各53248字节；base64解码、content_digest与两端entries核对相同。独立base85＋zlib解码Git transport两块literal得到同样数据库字节：

- `.coverage`：`17e684ddea0db06a55980b4986239c9e82c3aecf17c9217b6dcf2bc78541caca`。
- `tests/modules/.coverage`：`a4fde0f025854630cb099fc2835a08953c3c333c6a89cdd97015a1ff0659e768`。

两端baseline完整相同；原census重建334entries与2960排除路径摘要，与manifest相同，两端census原文本相同。FrozenPatch／baseline digest、transport SHA（`f26509a500e1fab8559242c998ce15d7535f0692846867f7f2b59397679b8dbb`）与attempt／ledger相同。roundtrip身份、entries、排除证据及transport核对通过。actor／回放的excluded_pathset_changed保留true／false原值，排除路径实际证据相同，不伪造该字段相等。

公开产物正式回放14/15=0，只失败目标键，tests_failed，完整退出／清理成功，actor及grade标签无容器／网络残留。该候选是非空FrozenPatch，不能称纯NOOP；矩阵另有独立base。public_devbrief人工核对仅含公开环境及命令，没有gold／隐藏测试／私有方案泄露。

## 复用、限制及余项

首次dispatch把prepared_manifest SHA误填为replay_summary文件SHA，前置assert拒绝，job rc1、零CC／评分，command及stderr保留于dispatch_guard_failed01。后续02新job正确执行；前次失败不归为测试失败，无需重复CPU。

原值保留：setup audit before／after均300秒、test1800秒；ledger候选阶段900、cleanup120、grading总期限3600、image pull1800秒。actor wall1200秒、max_turns9、context32768、max_new_tokens4096。rollout profile digest7442237a…、grader3ec1bfa8…；2CPU／4GiB／pids512与tmp1GiB同prelaunch原件。完整profile／预算见JSON，无infra被当测试失败，无不同版本改绑。

复用[非作者材料窄核](non_author_016a_material_review_20261003.md)（SHA ad1ebc79…）与[fresh公开静态阅读](../tasks/coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae/public_reader_review_20261003.md)（SHA0ae430ec…）。前者只支持v2语义，后者只支持公开题意／调用顺序；真实CPU和交付另核本轮原件。共用builder／Git行为按冻结版本既有验证复用。

范围限制：未登录CPU宿主，远端行为依据原件；未重验Docker daemon构建限额，不从验证容器HostConfig推定。本地副本未保留context的material文件／manifest.tsv，已从正式086重建配方摘要并与build／facts／评分setup树核对；未含pre-solver baseline.tar，没有重新提取归档，已核两端baseline/census、实际归档元数据与transport数据库字节。静态检查、CPU桩和固定候选不计模型结果。

尚缺：作者按恢复授权同步题卡／results_manifest的旧暂停与待核状态，引用本审查，不因此重跑CPU。题主可固定probe_request交统一GPU执行者；实际模型运行、结果分析和后续用途判断仍缺。CPU通过不自动构成训练准入。

本轮只写本Markdown和[同名JSON](non_author_016a_cpu_review_20261003.json)，未改任务材料、共享代码、总账或历史原件。JSON记录机器检查、14行逐键结果和证据完整SHA；原件根为 `runs/category2_repair_20260929/coveragepy_owner_cpu/remaining_r6_v1/`。
