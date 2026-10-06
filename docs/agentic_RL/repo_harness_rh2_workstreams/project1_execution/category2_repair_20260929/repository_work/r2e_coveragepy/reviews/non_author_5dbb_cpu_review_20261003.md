# coveragepy 5dbb R5 CPU 非作者独立核查

2026-10-03。**结论：本题本轮满足提交普通基座探针所需的题级 CPU 条件，未发现阻断项。** 首条实际请求完整交付已批准的 A 题面，公开开发环境可用；正式 NOOP／CE3／CE1 分别得到 74／76、76／76、75／76 个期望匹配，关键分歧与按 slug 去重的决定一致。此结论只适用于下面固定版本的自建修订题，不授予训练资格、原 benchmark 资格，也不是模型成绩。实际模型求解与回传后的候选审计仍未完成。

核查者为非作者 Codex 子 agent，以干净任务上下文进入，随后阅读公开题面、私有材料身份、原 CE 补丁、历史诊断及本轮完整 CPU 原件；**不是 fresh 公开读者**。本轮复用已有公开读者与题面窄核，不声称再次盲读。只在本机读取证据并重算摘要、逐键结果及往返关系；未运行 Docker、SSH、安装、项目测试或模型，未修改作者产物或共享文件，未发送跨线程消息。只新增本报告及[机器核对结果](non_author_5dbb_cpu_review_20261003.json)。

## 适用身份与核查方法

题 ID 为 `coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9`。下文 `RAW/` 指 `runs/category2_repair_20260929/coveragepy_owner_cpu/5dbb_r068_r5_v1/`；`RELEASE/` 指 `runs/category2_repair_20260929/releases_20261003/r2e_078_079_swe7_git_candidate_v1/`，均为仓库相对路径。

| 项目 | 固定身份 |
| --- | --- |
| 执行发布 | `cat2-cpu-r2e078079-swe7-git-20261003-v1`；外部 manifest SHA256 `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9` |
| 执行 runtime | 两个作业的命令均指向 `runtime_cpu_v2/rh2/.venv/bin/python` |
| 材料 | 保留 `r2e-mr-038/039`，题面 `r2e-mr-068` |
| 公开 bundle | `sha256:035247de587f855155302ae06b44b1ed3c2a711b58de1e63a7b28ca9dea99146` |
| 评分 bundle | `sha256:dfbd82e6a6c312540c3054013810194ffa4d7891e20ed0c454a9e9c48b802e5e` |
| prepared manifest | 文件 SHA256 `f01f9eb32430fa12fbb160791dfe1a485f6cbd3adab75ae5eedbe62c65d8bd00` |
| 私有 host artifact | 文件 SHA256 `f2f25e6a0d8a4d5f3b4e7137fba31c040aba6f64118624a88b1dd22e24715b8b` |
| 实际 actor／三行 grader image | `sha256:5091d0c510d4dd598ad8cc54f7912b2dcd159c97c3d1de2693a81ec4d792ffc3` |
| 原镜像来源／base commit | manifest `sha256:667479086285ed01e79a15da2e7c9c18c10188d5c85f8c2256b7e0d6dceb3105`；commit `8240c58c90a0157178e9c5f6fedd9f003aab892d` |

本机重算 61 项证据关系均成立：包括外部 manifest、其列出的 837 个文件大小／摘要、配方、prepared 的文件链、公开和评分 bundle、首请求、三行逐键日志及 FrozenPatch。837 个文件校验只用于固定读取快照身份，不等于重新审查全部共享代码。共用 Git／daemon 实现验收按已有适用身份复用，本轮没有重复公共运行审查。机器结果保存逐键 expected／observed、日志／ledger 摘要和核查布尔值，可重新对照原件。

## 公开交付与真实开发条件

1. `materials/statement_A.txt` 与发布公开 bundle 的 `problem_statement` 逐字相等，SHA 为 `b2a7f5fb3e3c76a8896ac0f8afb2e9b534bcfbd28baf6ebbe647ddd0857b2415`。`RAW/public_e2e01/attempt/prompt.txt` 含完整 A；`stub/requests/messages_000.json` 第一条 user 消息的 text block 含**完整正式 prompt**，不是只含 issue 摘要。原请求 SHA 为 `1b990759cd110e348fe37a48302bdeac793e62ddf7207e6970e6c498a3b17c48`，prompt SHA 为 `7c62a45b9ede9d2f7f4070943585708137dd1e144b32d0928164989ebe0e4020`，均与交付核对表一致。
2. 在首请求及中性[公开环境说明](../tasks/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/public_devbrief_20261003.md)中，未见私有候选、expected 答案或私有新增测试提示。环境说明只给解释器、导入检查和已有公开测试命令。该说明未作为本次首请求的额外正文出现；本轮证实的是正式 prompt 交付。后续 solver 应只取得公开材料与这类中性说明。
3. `attempt/facts/agent_env_facts.txt` 与 `attempt/harness/trajectory.jsonl` 的原工具结果一致：UID/GID 54321，工作目录 `/testbed`，Python 3.7.9，`sys.executable=/testbed/.venv/bin/python`；在 `/testbed` 和 `/tmp` 均导入 `/testbed/coverage/__init__.py`，coverage `5.0.2a1`，pytest `4.6.6`，pip `19.3.1`。`/rh2/bash_env` 对 agent 写入被拒绝。原工具 preflight 的解释器、隐藏测试隔离与 Git 历史三项均为 ok；固定 Claude Code 版本原观测为 `2.1.205`。

| 公开步骤 | 原件中的子命令返回码 | 结果 |
| --- | --- | --- |
| preflight | 0 | 三项 ok |
| 环境检查 | 0 | 上述 UID、解释器、导入与版本输出齐全 |
| 原题面 MCVE | 1 | 未修复 `_warn` 抛出 unexpected keyword `once` 的 TypeError |
| 显式 PYTHONPATH MCVE | 1 | 工作树导入得到相同 TypeError |
| 公开 warn 测试 | 0 | 96 项中选择 6 项，6 passed、90 deselected |

这些返回码来自原工具 stdout 的 `RH2_STEP_RC`，不是会话摘要推定。MCVE 的 Bash 命令末尾打印 marker，因此工具 `is_error=false` 和 Claude Code `subtype=success` 不能解释成复现通过；真实子命令 rc=1 是预期的基线缺陷。preflight 会把失败写成文本，env 又是多条命令组合，因此其末尾 rc=0 也不能单独证明所有条件，以上结论结合逐项原输出作出。

## 正式评分与关键分歧

从 `RAW/private/host_grading_views.jsonl` 取得 expected 原文，重算 SHA 为 `fc64a1db6ec518a4088067d2571ad93b90acc6aca21847a3c1f54d06960e316a`，共 76 键、全为 PASSED；与固定发布的评分 bundle 完全一致。逐行解析三份 eval.log 的完整 `Start/End Test Output` 区段中的 pytest 最终状态，三个观测集都恰好 76 个唯一键，无 missing／unexpected、无区段外状态、无 skip／xfail／error。所有逐键状态与作者 per-key 文件及正式 ledger 相符。

| 正式行 | reward | 匹配／总数 | 两个 once 键 | 原测试 rc／执行 wrapper rc |
| --- | --- | --- | --- | --- |
| 公开桩导出的 NOOP | 0 | 74／76 | `test_warn_once` 与 `test_warn_once_each_slug` 均 FAILED；其余 74 键 PASSED | 1／0 |
| CE3 原补丁 | 1 | 76／76 | 两键均 PASSED；其余 74 键 PASSED | 0／0 |
| CE1 原补丁 | 0 | 75／76 | `test_warn_once` FAILED，`test_warn_once_each_slug` PASSED；其余 74 键 PASSED | 1／0 |

关键原日志位置：

- NOOP：`RAW/public_e2e01/grade_cc/eval_logs/evallog_replay-cov5dbb-r068-r5-p_a3d330d2.eval.log:30` 为 once TypeError；`:7888` 起列失败键，`:7890` 为 `2 failed, 74 passed`，`:7892` 为真实测试 rc=1。日志 SHA 为 `6a62ec0f33d745d763c440d5e395075ed881ceaa906524c3d896861426304565`。
- CE3：`RAW/formal_controls01/CE3/eval_logs/evallog_replay-cov5dbb-r068-r5-C_8d4cedd0.eval.log:7826`、`:7828` 为两键 PASSED；`:7873` 为 `76 passed`，`:7875` 为 rc=0。日志 SHA 为 `2b757f09dc37cb09f252c825074de19c1faa0077627cdcb4fc154aec5612e731`。
- CE1：`RAW/formal_controls01/CE1/eval_logs/evallog_replay-cov5dbb-r068-r5-C_7e875f72.eval.log:34` 的断言明确拒绝第二条消息：两条都带 slug `bot`，CE1 输出了第二条，`assertNotIn` 失败；`:7841` 显示不同 slug 键通过；`:7889` 为 `1 failed, 75 passed`，`:7891` 为 rc=1。日志 SHA 为 `f464461bc8df45f413e96960501c2101089c5a553fb507903641ddf1e0dfd3e0`。

CE3／CE1 ledger 的 patch SHA 分别为 `f245e0b7c491f2dc1a078b3423f6e0f480fcb3ff5ab663e8cce22804238c8246`、`a94081f7683562ec02d0e1bf53f0e174d7c101b41e537155940f8d282576aa58`；直接重算 `runs/r2e_actor_20260925/grader_cands/coveragepy_5dbb_CE3_dedupe_by_slug.patch`、`coveragepy_5dbb_CE1_dedupe_by_message.patch` 的原字节吻合。未用云端重建候选替换身份。

038 的有效测试只核同 slug 的第二条不显示、不同 slug 的两条都显示；未把 `slug=None`、跨实例或 once／非 once 混合边界增加为本轮条件。CE1 的拒绝由原断言实际执行证明，符合用户已选 A。CE3 作为独立集合实现的正对照全通过，未要求必须使用 gold 的内部结构。

三份 ledger／diagnostics 的测试区段完成、log_partial=false、真实测试 rc 齐全；trusted setup 为预期 4 个文件、实际 4 个、缺失 0、无 irregular 文件，隐藏树 SHA `6e81f8d…` 与入口 SHA `8285765f…` 与 prepared grading 相符，runner digest 前后不变。install 明确 skipped，不能把它记作一次安装验证。测试失败都被记录为 `tests_failed`，不是 infra 失败；外层 exec／driver rc=0 表示执行和报告完成。

## 镜像复用、基线、投射与清理

R4 镜像复用合理：本机独立比较 R4/R5 的 `recipe_v1.sh`、`material_v2.sh`、`sysconfig_v1.sh`、`build_r2e_derived.py`，四者字节相同；用 038 的材料 manifest 重算基础配方及 sysconfig 配方，得到记录的 `ab88e4c6bb5ad7ceb1f5c07c44f607b9fc3eed5166b9547ec2ad363b43d18334`。038 有效 test_1.py、039 expected、评分 bundle 未变；068 只改变题面。R5 重新 prepared、生成新 baseline 和 attempt，未把旧 FrozenPatch 换绑。实际 actor 的 `attempt.json.stages.image_identity` 与三份 grader ledger 记录同一 `5091d0c…` image；不是仅凭镜像 tag 推定一致。

独立重算 actor／grader baseline JSON 及排除路径 census，两份 baseline **全部字段和 334 个条目相等**，digest 为 `sha256:c3494adaa6fb72ba2aa59fc10af2e9e6ddd23f9ad2ba65c166f87975a2fe3bec`，排除路径差异为空。NOOP 的两个 FrozenPatch 都为空；其 digest 因 rollout／physical attempt ID 与排除变化标志不同而不同，不能要求整个 FrozenPatch 字节相同。CE3／CE1 仅投射 `coverage/control.py`，entry 内容摘要、FrozenPatch digest 与 projection／ledger 一致；没有测试路径或 fixture 改动。

actor 的 `excluded_pathset_changed=true`、grader 为 false，应保留这一事实；空投射不等于整个容器没有变化。政策排除 `.git/`、`.harness/`、`.venv/`，且省略可再生 cache；本次验证证明的是受支持源码条目往返与基线身份，不证明任意依赖修改都能运输。三份 diagnostics 均有 `/opt/miniconda3/envs/testbed` 的历史 writable prefix 缺失记录，实际解释器为 `.venv`，当前只改源码且无安装，不影响这三行；不得据此推导安装／依赖修复能力已验证。

`public_e2e01/job/status.json` 与 `formal_controls01/job/status.json` 均 finished、returncode=0，原 stderr 文件为空。三份 grade.log 最后一行均 exit_code=0、grader_containers_open=[]、cleanup_failures_total=0；各 ledger removed=true。actor cleanup_ok=true；公开 run 与 grader run 的 residual 表均空，CE3／CE1 的 container/network 查询 rc=0 且 left=[]；gateway／stub 停止 rc 均为 0。actor quiescence 有“进程归零＋双读稳定”原记录。本次没有重新查询远端，清理结论指**运行完成时记录的清理状态**，不代表现在宿主的全局资源状态。

## 非阻断事项与未证明范围

- **状态入口滞后，应由题主同步。** `card.md:3` 仍写“实际交付／CPU验收未完成”，`cpu_execution_plan.json` 仍写 actor running，`r5_image_reuse_check.json.runtime_validation` 仍 pending。这些是历史阶段记录，已有原件证实相应工作完成；本轮只新增审查，不改作者文件。题主应把当前题卡／结果清单更新为“本轮 CPU 已独立核查，可提交普通探针”，同时保留未运行模型的事实。该项不影响原件真实性，也不应再产生一轮 CPU 重跑。
- **本轮没有重跑 gold／CE4。** 已有 v5 对照按当前工作流的题面-only复用政策保留；本轮新宿主验证只覆盖 NOOP／CE3／CE1。038／039的有效材料 SHA 与本轮身份一致，未发现需要机械补全五行矩阵的变化。本核查没有再次审计 v5 全部历史运行原件，也不把旧 gold／CE4 记作 R5 新运行；gold 潜伏副作用仍按原诊断处理，CE3 才是本轮已验证正对照。
- 派生构建的完整层／权限比较以 `derived_r068_r4_v1.json` 留存事实为依据；此次本机没有 Docker image 或全层原字节，不能独立重建整个镜像。实际使用身份由 actor 与 grader 的运行记录互证。CPU runtime v2 的路径已核，不等于本轮另做了 host runtime 依赖审计。
- 网关控制密钥未取回，属预期私密信息，本核查不要求把它加入证据包。首请求、公开轨迹与评分原件已足够完成本题范围核查。
- 桩剧本固定执行公开命令并停止，没有真实模型求解。记录中的 `slime-actor`、usage／cost 或 Claude Code success 都不能计作基座模型成绩。普通探针仍须使用干净 solver 上下文，并保存实际模型、预算、候选、原始评分与清理回执，由原题主继续审计。
- 本轮未修改共享实现，审查重点为 A/E/F/G/H/M/N 的证据正确性、真实入口、语义与版本；训练分布、闸门翻转、长期 owner／容量等 B/C/D/K/L 不作新验收。通用测试控制保护按已授权工作流延后，不把本次源码正负对照推广成完整 anti-cheat 或正式训练安全证明。

停止条件已满足：新题面实际交付、关键开发环境、代表性正式评分、基线往返、退出和清理均有适用原件，独立机器核对无不一致。无需新增用户决定；题主可以提交固定版本普通探针请求，继续保留上述用途和证据限制。
