# DVC5839 R10：真实公开 actor 原件非作者窄核（2026-10-03）

结论：本轮无新增阻断。R10 公开 actor job `dvc5839-public-actor-20261003-r10-v1-001` 实际由 Claude Code 执行四条公开环境命令，均 rc0；两个指定原公开测试实际 `2 passed in 0.17s`，没有 skip／失败／缺席计数。首请求逐字包含原 CRLF 题面与中性开发说明，UID54321、testbed 解释器、pathspec0.8.1、激活拒写、实际 actor inspect／cgroup 和清理一致。这是公开环境交付／执行事实，不是模型解题或正式评分。

核查者已读私有材料、R10 正式矩阵及此前 helper／actor 结论，不是 fresh 公开读者。只用 stdlib 读取、SHA 和轨迹解析，没有运行入口、SSH、Docker、项目／维护测试、安装或新 CPU；没有修改输入、作者结果、共享代码或旧报告。

## 固定原件与版本

固定请求 `reviews/actor5839_r10_runtime_review_request_20261003.json` 实际 SHA256 `a802e1041742f7dc4ebba1bfc70cdbb765d5c45d3b41b7627b92de3c2e0ef8f6`。39／39 输入 SHA 全匹配，包括 34 份归档原件、tar.gz、作者导航及当前 helper／公开说明／命令文件。下文原件根为 `runs/category2_repair_20260929/repository_work/swe_dvc/public_actor_evidence/public5839_r10_actor001_v1/`；attempt 表示其 `attempts/dvc5839-public-actor-20261003-r10-v1-001/`。

实际 release `cat2-cpu-r2e089092-swe14-preflight-20261003-v1`，manifest pin `00ac5c375629f59543f548fbc7b0cb3cbe7d1418f7a956d9deebcefab2e8a87c`。刚完成的正式窄核已重新验证 950 个声明成员，本轮只对照 actor 的七份代码 pin，均与该已核本地 release 字节相符。helper／归档 actor_check.py 字节同为 `91c8bb818c10f6492be45f20ada71f252fcb6884aed5c12539c109cb4fe689d0`，承继链与 known -q parser 限制复用此前 helper 静态核查。R10 prepared_task_face.py 实际 pin `a807689556df52d5b12c8ac2773722e443ee1fa4c79d232a9bdf7447be7d3b04`，不同于 R5；本次没有把它写成未变化，而以实际准备／首请求验证公开交付。

actor 单独 prepare_invocation 为官方 R10 replay_grade.py prepare、该 actor 的独立 prepared／private 目录、单题 `swe_gym_lite::iterative__dvc-5839`，exit_code=0；prepare.log 与 replay_summary 的目录／task／manifest／host 链相同。summary→manifest→prompts／rollout→host-grading 字节 SHA 完全相符，task_count 和 jsonl count 均1，public bundle `a4d44e026d6dc40e7542bc122bd8e0365c68583519f157bc48e2eb66427adba0` 与配置、实际 face 相符。私有 grading 留在 host，没有 mounts 或公开命令执行它；本报告只核其 SHA 链，不重审私测。

## 首请求与真实命令

首个 `attempt/stub/requests/messages_000.json` 的 user text block 精确等于完整 prepared prompt＋两个换行＋完整公开开发说明。原 problem_statement CRLF 保留，实际题面文本 SHA256 `3b7dc4d964bcedb5041eb4d58285c6e9cdf48fbbb7f84613bfdb5187bdb9cbee` 与 face／public_delivery 一致。开发说明只含 checkout／解释器、已安装 pathspec、原公开测试与 CLI／临时命令入口，没有新私有断言、reward、候选答案或补丁提示；首请求没有新增私有节点 `test_metrics_show_precision_real_values`。归档 commands／brief 与当前题卡对应文件逐字相同。

| 命令 ID | 真实执行及完整捕获 | rc |
|---|---|---|
| identity | `/opt/miniconda3/envs/testbed/bin/python`；CONDA=testbed；UID54321；DVC `/testbed/dvc/__init__.py`；pathspec0.8.1，命令中断言成立 | 0 |
| activation_permissions | `RH2_BASHENV_WRITE=DENIED`；`test ! -w /rh2/bash_env` | 0 |
| public_tests | `PYTHONPATH=/testbed python -m pytest -q tests/unit/command/test_metrics.py::test_metrics_show_precision tests/unit/command/test_metrics.py::test_metrics_diff_precision`；两个点 `[100%]`，`2 passed in 0.17s` | 0 |
| dependency_check | `python -m pip check && PYTHONPATH=/testbed python -m dvc metrics show --help`；`No broken requirements found.` 与真实 CLI usage／precision 默认5说明 | 0 |

四个 capture 实际字节数依次 148／25／98／1165，等于 recorded output_bytes 且都低于200000截断上限；tool_result 的 capture tail 与完整文件相同。`commands_result.public_tests.pytest=null` 是已知 `-q` 摘要解析限制，本次从完整98字节 capture 重建2 passed，未直接相信 actor_checks_passed 或作者计数。两条命令 selector 是上述原公开基线精度测试，计数与两个显式 selector 一致，无 skip／fail／error 摘要；`-q` 未打印每条完整节点 ID，这不等同于另存逐 ID collection 验收。

独立解析完整 trajectory.jsonl：四个 Bash tool_use 与四个 tool_result 的 ID 一一对应，输入与 stub_script／stub日志完全一致，包含配置原命令的精确 timeout 包装；每个 `RH2DC_END id=... rc=0` 与 captures 及 command result 一致。requests001–004 收到对应实际 tool_result；五个 message_start 与五个 stub 请求一致。最后 result/subtype=success／is_error=false；CC实际2.1.205。harness log_complete=true，轨迹字节数相符，harness／slot stderr 均空。slot 2026-10-02 UTC 21:38:46–21:39:50，真实 returncode=0；harness_exit_code=0、termination=returned。执行使用固定 stub 响应，不是一次真实模型解题能力测试。

## 实际身份、profile 与清理

原镜像 image inspect、配置、actor prelaunch image 均为 `35e6260d03d9e4792df404b498ca7800a3a633eb678e27fbed9246c0fe580147`；初始 HEAD／sanitize before-after／prelaunch HEAD 均 `daf07451f8e8f3e76a791c696b0ea175e8ed3ac1`，初检 porcelain 空，post_run git status 行数0。baseline guard 指向原 `tests/unit/command/test_metrics.py` SHA `64f7af4cebece4c559b2edf1e86e38a45c2c340ff8c395510fbca09b8e19e2ca`；已核 helper 控制流会在启动前核原文件存在／SHA、配置全部 source pins。归档没另存这两个 guard 的 stdout，也没有容器内完整基线文件快照，因此不能扩大为独立读取实际完整测试正文或远端所有源码字节。

prelaunch 实际 inspect 和 cgroup probe 均支持2 CPU（200000／100000）、4GiB内存、swap0、PID512；tmp tmpfs1GiB、home tmpfs256MiB、UID／GID54321、有效cap零、no-new-privileges、非privileged、binds／mounts空。profile_digest `a0d183d13a4a099cd0bd62d9e19fca7019428f7d08f5b69522a3ead4b565c68f`。relay连接成功，外部DNS／直接upstream／四个forbidden目标均DENIED；activation root 0:644、可读不可写，activation_check=testbed Python、violations空。effective_profile 的8GiB writable-layer quota仅配置；实际 storage_opt={}，没有证明磁盘配额强制生效。

image-facts探针 cleanup_rc0；最终 container_rm=0、stub_rc=0，network_failures／relay_failures空，按本run label的 labeled_containers_left／labeled_networks_left／residual_after_force均空。post_run 原件证实 `.harness`、`/tmp/.run.sh`、`/tmp/.run.done` absent、agent进程0。newer_files=197，示例含正常pycache，不声称从未写入工作区或全主机无其它资源。

## 实际 SHA256 与证据指针

路径基于上文归档根；其余清单原件由固定请求精确定位，39项均已匹配。

| 原件 | 实际 SHA256 |
|---|---|
| input.json | `9ec4fbddeb371e6ca52bf1eb57c167cf617f078b3b9fe1fb9ff47418e137e21f` |
| commands.json | `bf3f03725bf9eee3cde842973f6a424049654bb6ba5044c0f20616b196dfe148` |
| public_development.md | `b768b8c5aa55e217660dbf6cebd4b5a53350f0d6e55af8e56aedb7804db0a8a7` |
| prepared/replay_summary.json | `79fa9e71050c4ba1cc18406addd50a5e0ff667deac6cc81a81964ddded181947` |
| prepared/prepared_manifest.json | `300d4d5c6050fbaf7fd29316d21f8bdb87c6304e38276e6ec4d07fbecbbed33b` |
| private/host_grading_views.jsonl | `dc326026c895190e0745e4e05f84cf806a860452dfcb7958eee8fd734032364d` |
| attempt/attempt.json | `35c143c11529096e3bcb01762763f12e1672b09e8ce69841443f06b23842d287` |
| attempt/stub/requests/messages_000.json | `f64fef2ec58b9e8b88b1d847cb656aff446aa0f908d641d7dd5edd3699399855` |
| attempt/harness/trajectory.jsonl | `47755c92ad29216504afcd452d6508bacf3cc94e61668bf0769b9ce8450ceb39` |
| attempt/captures/public_tests.out | `89d3ec78cb0fbd89b7737bfe3078876ad657c2c3b955758b5a26267a44a5d86b` |
| attempt/prelaunch.json | `3438114c59913be7b4c4f6cc262aa9aa9d86051a829e850117e4790ede3d1155` |
| attempt/post_run_facts_root.txt | `fb7809a7a4cd9c4f794cbbc92232f4c53f23ae65db76a6b6a7a6e18925b516cc` |
| slot_job/status.json | `259bf4d15ab23cdb9a0304b78cdc25b9dbcc5eb559f10731ddd852db63a7e337` |
| 归档 tar.gz | `53a24c326b98571fd588007f16b2ce3e07ce80f7d70a37a7c68f386df255322e` |
| 作者导航 public_actor_r10_v1.json | `606353bcaf16daa0c0f904c9bfdb58377cce938d971e085c3c462e2e6630760a` |

## 用途与限制

只支持 R10 本次公开 actor 环境交付、四命令与两个公开基线测试的实际执行事实。当前有效23节点正式 reward0／1／0 的验收在单独 `reviews/non_author_formal5839_r10_runtime_review_20261003.md`（SHA256 `b7ca13ed796a1c532ff01904eb42e4d20c31bbd959143c6fcf7b65c6971794dc`），不能由本次2个公开测试通过替代，也不能反过来用正式 grader成功代替actor核查。

没有新CPU复跑、实际模型回答、task修复、正式RH2 reward评分、模型探针或环境／训练／留出准入验收；不授予相应资格。CCtarball字节不在本次固定输入中，只有实际版本与记录，未再次读取tarball。原基线全文／source-pin stdout缺席与8GiB仅配置限制如上，保留这些限制不要求历史矩阵重跑。
