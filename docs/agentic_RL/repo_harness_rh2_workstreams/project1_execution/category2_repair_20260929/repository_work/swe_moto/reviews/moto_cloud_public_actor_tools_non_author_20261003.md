# Moto 6185/7584 R13 公开命令工具：非作者静态窄核

日期：2026-10-03。结论：**本次未发现确定的工具启动阻断，可按现有授权启动固定工具。** 这只确认真实 CC 加确定性 stub 的公开命令诊断入口；没有运行证据，不宣称 CPU 或 actor 结果通过，不授予 typed-actor 或训练资格。

## 范围与固定字节

审查者不是工具作者；已接触 Moto 私有上下文，不是公开材料盲读 solver。本次只读取五件工具、原公开读者命令文件、原 public bundle/prompt/module 来源、固定 R13 的 DevRunner/acceptance/stub、profile、prepared face、driver 和相关 root 执行前缀源码，以及对应 manifest。没有重审全题断言语义，没有导入或运行项目、Docker、测试、SDK、CC 或模型，没有连接远端。只新增本报告，未改任何工具、冻结输入或既有报告/请求。

`tools/moto_cloud_public_actor_r13_v1/` 文件集合精确等于 manifest 声明加 manifest 本身，成员不是符号链接，SHA/bytes 相符，`ast.parse(actor.py)` 成功：

| 文件 | SHA-256 | bytes |
| --- | --- | ---: |
| `manifest.json` | `1017b31d7c57eb2e0a4541fda03714d8992b246154a1df73e711e2695481dd46` | 762 |
| `actor.py` | `98849759086c322aeefacc76a0af6ceedb4fa96e7d70d7981ab808535b41a2fb` | 11711 |
| `tasks.json` | `c173e11523747d265afff908cb677b8bdc0c656f71d34b59e9673f619491143d` | 8215 |
| `commands_6185.json` | `09fa195d04a6b4b37115423f4b2917a3354ce9a7ddead0f519f7ca8bc32a4a76` | 3438 |
| `commands_7584.json` | `17a735aef7b5eea6fc78b970915af169eb6cc1e3fdef5c5309fc18eb0d20193a` | 2938 |

release 为 `cat2-cpu-r2e089092-swe27-pandas-moto-20261003-v1`，manifest SHA `3fad18daff8db219294e10cbf08d4424d68cf7000d008bb983cba4bdc427b641`，等于本地固定发布原件。工具独立 pin 的两个原入口均与 R13 manifest 和实际字节相符：`rh2/experiments/task2_swegym_dev_20260925/devcheck.py` 为 `75399297da458697ebcd17e6ca79aad90b56e4dbdda3214a4c70f82a4b389160`；`rh2/experiments/base_probe_fixes_20260923/acceptance_startup_2.py` 为 `c67194f09e202c1cd1e83a3a1fbf5df7706952d2e542f97a4b2f3882604dc5d1`。相关固定 stub、bringup、sandbox profile、manager、prepared face 源码也与 release manifest 相符。

两题 task/base/public/environment digest、original source image、runtime ID、recipe 与既已审的 R13 matrix/UID 输入一致。按原 canonical JSON 定义重算固定 producer 的 public/environment digest，相符；公开模块 SHA 与原 base 文件相符。这里的模块字段沿用 UID 配置，**actor.py 没有以它们执行 live module SHA 断言**，不能把这些静态字段称为本次 CC 工作区模块已验；单独 UID 补查与命令完整输出仍是对应运行证据入口。

## 原公开命令及输出边界

两份新 command JSON 分别与 `tasks/getmoto__moto-6185/public_commands_old_reader_v1.json`、`tasks/getmoto__moto-7584/public_commands_old_reader_v1.json` **全文件原始字节相同**，不只是 JSON 值相同。`id/cmd/timeout_s/expect/purpose` 均未变；每题四条、ID 无重复、timeout 均为 240 秒。

| 题 | 原命令顺序及用途 | 预期退出 |
| --- | --- | --- |
| 6185 | C1 公开解释器/模块导入；C2 原公开 put/get 例子及控制；C3 原两条公开异常节点；C4 原五条公开开发节点 | C1/C3/C4 为 0，C2 为非零 |
| 7584 | A 公开解释器/模块导入；B 原公开删除 endpoint 例子；C1 原 subscriptions 文件；C2 原 application 文件 | A/C1/C2 为 0，B 为非零 |

工具没有应用私有测试补丁或控制臂、没有添加私有节点、没有重新导出金标，也没有改命令内的 AWS/mock 环境开关。新 wrapper 只将同一 `cmd` 逐字放入 shell 引号保护，使用 `timeout -k 10 240 /bin/bash -c` 执行；保留真实命令 rc 和 stdout/stderr 合并的完整 `.full`，记录字节数。wrapper 自身 `exit 0` 是让 CC 完成所有预定调用，**不代表各命令成功**。随后工具按独立 `.rc` 判定，且只接受 0/1，124/137 等超时不会冒充预期非零。

`collect` 的 metadata 与 `.full` 都以 agent 取回，读取 rc/byte count，要求读取成功且返回文本重新编码后的长度等于容器记录字节数，保存完整 UTF-8 文本与 SHA，`output_truncated_to=null`；不再使用旧 200000 bytes 尾截取。默认 Docker runner 对 stdout/stderr 全量捕获，没有另加截尾。此完整性路径面向这些文本型命令输出，未宣称它是任意二进制输出的无损运输协议。

原 `pytest_counts` 只是从摘要文本提取计数，quiet 输出未匹配时可以返回 null，不证明节点收集或解析完整。自动条件主要核 rc/执行完成；C2/B 的预期非零也可能是其他故障。因此具体公开行为、实际错误、C3/C4 节点和两份文件的真实收集结果，必须读完整 `.full`，不能只据 `matches_expect=true` 通过。工具结果已明确 `pending_behavior_and_independent_review`。

## 原 DevRunner、CC 与公开实际 request

子类只覆盖 `start_stub`、`sh`、`image_facts`、`collect`，并替换原 `wrap`；其余沿原固定 DevRunner/acceptance 的容器、relay、attempt network、sanitize、trusted init、activation 文件、prelaunch/activation helper、`ClaudeCodeDriver.run`、轨迹捕获和 cleanup。动态模块导入调用形态与固定源码相容，原 DevRunner 类/函数没有需要额外模块注册的 dataclass 装饰器。`module.DevRunner` 和 `module.wrap` 的替换会被原 `main/build_script` 实际使用，没有另写 driver 或评分器。

CC 平台 tarball 配置 pin 为 `d3dadfa9cde294ac82c755eb6d889291228849180bac5d677ad1a4027aca1bc4`，运行前会与实际环境路径的文件 SHA 比较；原 driver 另保留 native CC 安装和版本核查。静态审查没有读取或运行远端 tarball，不宣称版本已实测。四次 Bash tool_use 加最后文本由原 stub 发出，DevRunner 设置原 `--max-turns 7`、wall 1800 秒。**这是待实际验证的真实 CC 执行确定命令，不是自主模型求解**；stub 不产生自主修法，也不调用外部模型。

工具在 monkeypatch 前从原 prepared public view 构造 `rollout_spec_from_view`，核 `grading_spec is None` 和 source image/base/public/environment digest。原 `render_user_prompt` 只从 public repo/workdir/base 与原功能 statement 渲染，未拼入私有 assertion、gold、counterexample 或新 brief。用标准库按原函数复算的 UTF-8 字节与原公开 `user_prompt.txt` 原始字节完全相同，包括 statement 原有 CRLF：6185 为 2550 bytes，SHA `416f16088cd1d3725ba9d657713dbc9580026c5add8446ea142fff3d6811c37b`；7584 为 1524 bytes，SHA `ff9355e8a86fd1a91febf0537f6e0a3f8c28e8bee83110f763c0581c05b67fdd`。

原 `main` 接收 `--prompt spec.prompt`，原 Runner 把 `ns.prompt` 传给 `ClaudeCodeDriver.run`，driver 原样传给正式 launch。新工具运行后读取原 stub 保存的 `stub/requests/messages_000.json`，要求 user text 中完整 `spec.prompt` 恰好出现一次，并保存实际 request SHA 和 prompt SHA。这是实际请求的运行后检查，强于只检查构造的 spec；本次没有此 request 原件，**不能声称检查已通过**。

旧 `interpreter_in_tool_result` 查 trajectory 的 `RH2_SYS_EXECUTABLE=` 形状；新 wrapper 的 tool result 只回显结束摘要，真实解释器文本在完整 capture，因而该 flag 可能为 false。旧 `bashenv_denied_for_agent` 查两条 acceptance 命令的写拒绝文本，本次四条原公开命令没有执行那条写探针，可能也是 false。原 DevRunner 本来就移除 `all_expected_ok`，本工具只要求适用的日志/请求/执行完成字段；没有静默把上述 legacy flags 改成 true。激活及 bashenv 边界应由原 prelaunch/activation 原件和实际导入输出核实。

## 镜像、资源与真实执行角色

6185 runtime 为登记 COPY-only ID `sha256:79d39d611186289b10956c2f845af1272218a1f4cf8fc00382c7c6ab4eced35d`；7584 为 `sha256:990e0e91a190f85426e6900828cf758c30f389c927f6c1d0cd1ed8c68b902f96`。新 `image_facts` 核 source manifest/config ID、RepoDigests、actual derived ID、来源层加一层和登记离线 wheel 环境。该 ID 与 recipe 身份此前已静态核过，具体镜像存在与 inspect 结果仍待运行。DevRunner 的既有 `--image` 诊断 override 仅替换实际运行镜像；public source image、功能 statement 和本次 prompt 保持原样，不能把 COPY-only supply 诊断结果扩为正式 source typed-actor 契约。

一次性初态探针显式使用 network none、2 CPU、4 GiB、PID 512、shm 64 MiB 和本 attempt label，`--rm`；读取固定来源初态的 HEAD/porcelain，要求目标 base 和 porcelain rc 0，完整初态文本保留。**工具记录 porcelain，没有自动要求其为空**，dirty 初态是否符合本题来源需实际原件读回。该探针发生在 CC 介入前，不是 root 在候选改动后读 Git。

正式 CC 容器仍走原 rollout profile（2 CPU/4 GiB/PID 512、UID 54321、tmpfs、capability/security、init 和独立 attempt network），原 prelaunch 实际核 limits/网络/用户等；`container_inspect` 另与 exact image ID/NanoCpus/Memory 比较。rollout profile 没有 shm 字段，本工具也没有再次读取不存在的属性；正式容器 shm 在原 prelaunch inspect facts 中只记录，不能由一次性 probe 的显式 shm 参数替它宣称已验。

子类 `sh` 对 root 使用原 `grading.manager.TRUSTED_ROOT_EXEC_PREFIX`，即 `/usr/bin/env -i`、系统 PATH、HOME=/root、`/bin/bash --noprofile --norc -c`，避免继承候选可写 PATH/BASH_ENV。原 production sanitize/init helper 在 CC 前按其既有 API 执行，本工具没有重写它们。

旧 post-run 事实脚本包含 `RH2_GIT_STATUS_LINES=` 与 `git status --porcelain`，子类对该**整段**改为 `user=agent`，保存 `post_run_fact_actual_role=agent_uid_54321`。`post_run_facts_root.txt` 原文件名保留用于兼容，不再证明 root 可见性；其中 harness/launcher/进程/find/Git 等事实都来自这次 agent 执行。完整 capture 也以 agent 取回，避免 root 读取候选控制的 Git 或输出文件。其他确需 root 的受信操作继续用前缀；没有把有 Git 的后置事实段仅部分留给 root。

## stub 所有权、清理与最终边界

固定 stub 端口为宿主 bridge 的 18193，relay gateway 为 18192，后者要求环境变量精确匹配。启动前先 bind 检查 stub 端口未被占用，再启动原 stub 并核本次 child 尚存活。bind probe 会关闭后再启动服务，不能把它写成全生命周期持有的端口锁；实际 own stub PID、健康响应、当前目录 requests/stub log 和轨迹计数相符仍要读回。固定任务用新 job/output 目录执行，原 Runner 的目录创建是 `exist_ok=true`，工具没有自动拒绝复用输出目录；应保留本次 job 原件，不能拿旧文件补缺。

原 DevRunner 在 signal/cancel/异常的 finally 走清理：移除本次容器、teardown 本次 network/relay、终止自己启动的 stub child，再按本 attempt 的 `rh2.run_id` 查询、必要时 force remove 自有容器/网络并复查。没有全局 prune、没有扫描或删除其他 job，也没有删除镜像。原最后双 query 非零会写 `<container_query_failed>`/`<network_query_failed>` 到 `residual_after_force`，不会当零残留；原 main 因非空 residual 非零退出。新 wrapper 还要求 residual 为空、network/relay failures 为空。容器创建回包失败的残留也由本 attempt label 路径回收，不靠仅登记成功的主容器名。stub 的实际 terminate/wait/kill 及 returncode 仍须原记录读回，不能只用 Docker 零残留代替 host child 清理证据。

新 summary 只有在原 main rc 0、harness rc 0、termination returned、适用日志/trajectory/result/all_commands 字段成立、四命令真实 rc/预期匹配、实际 image/资源及清理相符、实际 request 的 prompt 精确检查成立后才写。它仍标 `formal_cpu_accepted=false`、`model_attempts=0`、`frozen_patch_exported=false`、待行为与独立审查。这里的原轨迹捕获不等于训练消费或 FrozenPatch 导出；构造 public spec、真实 CC scripted 操作和 typed-actor 准入三者须区分。

本次无需要现在修复的具体阻断。后续只需原件读回：两题四命令 full capture/实际错误与节点、真实 CC/version/轨迹、原公开 prompt 的实际 request、prelaunch/activation/实际 profile、agent post-run 角色、stub 所有权，以及容器/network/relay/stub 的收口。当前入槽 75 是未开始，不能算公开命令失败或 CPU 失败样本；本报告没有任何已执行 CPU/actor 结论。
