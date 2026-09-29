# 实验工具与 Pydantic8793 校准：跨包独立窄审查

2026-09-29，Codex / cpu_dask_mypy_owner。结论：**Pydantic8793 的原环境公开开发校准有效；当前供应关闭时，旧 recipe wrapper 仍改到实际执行的安装段。** 私有行为工具的普通成功/异常路径有清理检查，但 SIGTERM 取消路径不收尾，需要在使用该取消路径前由外层负责清理，或窄修工具。以下不构成题目最终验收、正式评分或训练资格。

我未编写本次三个新工具，也不是 Pydantic8793 主审。先读取本题原始 captures、attempt、prelaunch、activation、CC/轨迹/收尾，再作判断，**没有读取 Pydantic8793 主审 plan**。复用当前工作上下文，非 fresh 盲审；本角色可读共享目录，不宣传操作系统隔离。未 SSH、容器、网络或历史项目执行，未改生产代码。

## 1. 可达风险与非阻塞改进

### R1：SIGTERM 不进入私有工具 finally，容器可能残留

`private_behavior.py` 的 try/finally 覆盖普通 Python 异常、KeyboardInterrupt 和内部 subprocess.TimeoutExpired；但文件没有注册 SIGTERM 处理。Python 默认收到 SIGTERM 会直接退出，不展开 finally。若外层 `timeout` 或主控主动停止该进程，已经 daemon 化的 `docker run -d ... sleep infinity` 容器不会随 Python 自动结束。root 已即时获知此点。

适用范围是**外部取消/终止路径**，不是断言正常完成也泄漏。处置可二选一：外层停止后按此次容器名/标签清理并核 `docker ps`；或工具捕获 SIGTERM 转成受控退出，在既有 finally 完成有界清理。工具当前统一标签 `rh2.cpu_preprobe=20260929` 只能用于核当批；并行时不要无差别删除其它运行中的私有容器。未清理确认的取消结果不能用于题级通过结论。

普通路径上 rm 非零但精确名称查询成功且已不存在时，状态仍可解释为“已确认不存在”；不要仅以 rm 的 RC 否定不存在证据。若 rm/ps 自身超时，脚本非零退出且可能没写完 cleanup；同样由主控补收尾，不把无字段当成功。

### R2：旧 recipe wrapper 仅兼容本夜单 shell 模式

当前可用，见 §3。若未来 supply 开启，wrapper 没有替换 `candidate_install_script`，旧安装 recipe 会被绕过；此时仍保存的 candidate_test_script.after.sh 不能代表实际运行脚本。保留供应关闭，本夜不用为尚未启用的路径新增审批。将来启用时补两段字段覆写、携带 export 验证及新资格。

### 非阻塞记录改进

- `private_behavior.py` 保存 spec SHA、实际 image ID、准备输出、完整命令输出和逐命令 RC/耗时；没有保存输入 files 的逐文件SHA，也不导出 candidate.diff。当前按本批冻结输入及另走正式导出/评分足够分工；不能只凭 spec SHA 声称所有引用文件字节被固定。
- 私有 shell 只设置 PATH，不执行 conda 激活；需要的运行环境变量必须在 spec 命令显式提供，或者确保镜像 ENV 已生效。Dask7656 spec 已显式 export SETUPTOOLS_USE_DISTUTILS=stdlib；不能以 actor 的 activate.d 钩子推断此工具也读取了它。私有使用 COPY-only grader 镜像时，也不能把“wheel 已在镜像”当“运行依赖已安装”。
- `sync_evidence.py` 的 rsync 是增量快照，不是原子完成快照；只有相应 attempt/summary 的结束、清理与输出齐全后才能验收。同步失败会记状态；旧本地成功文件仍会存在，不代表远端新作业成功。
- sync 的 `-e` SSH 字符串没有对 key 路径做 shell quoting；带空格路径会失败，当前无证据表明本批路径触发。属于健壮性改进，不是本批阻断。
- bootstrap 为本批环境准备脚本，uv 安装器和 apt 索引是运行时下载；日志/下载脚本保留实际版本，不应称为逐字可重复系统镜像构建。锁文件约束 Python 包；CC 明确2.1.205并核 npm integrity、记录SHA。未发现本批需要因此重跑已成功 actor 的理由。

## 2. Pydantic8793：先读原件得到的结论

证据目录：`runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-8793/actor_original_v1/`。

| 项目 | 观察 | 可推出的范围 |
| --- | --- | --- |
| 真实身份/解释器 | UID54321，Python3.8.19，`/opt/miniconda3/envs/testbed/bin/python`，core2.16.2，pydantic来自`/testbed/pydantic/__init__.py` | 实际actor使用正确checkout及所查解释器；fields.py可写断言已执行 |
| 初态 | HEAD `832225b90672c68e2d4067bd0ffecf834d62b48b`；镜像预检已有 pdm.lock/pyproject.toml 修改，actor仍报告同两文件，97增5删 | 这些脏路径在命令前已存在；不是干净仓库，也没有完整字节diff可证明每个改动内容 |
| 原例/必填语义 | schema.required仅foo；bar/baz is_required=False；缺值输入被接受，值是Ellipsis；两个non-serializable-default警告 | 三个目标失败均真实触发，RC1是末尾指定AssertionError，不是导入/权限/超时错误 |
| 原例其它检查 | 有效foo/bar/baz输入、schema描述与类型断言先执行；随后打印全部三项failure | 有效输入与这些保留属性正常；不是在第一个目标失败就中断 |
| 默认值 | `PUBLIC_DEFAULTS_OK`，RC0 | 默认5与工厂7及非必填标记通过 |
| 公开测试 | `72 passed / 1 skipped`，0.54秒，RC0 | 两个指定公开文件可运行；没有收集错误。日志没有跳过节点/原因，不写73全通过 |
| 装配 | prelaunch/activation均ok；激活文件root:0644、actor可读不可写；2CPU/4GiB cgroup值被读取；直连/外网探测拒绝、relay可达 | 本次实际装配检查通过；不推广为任意网络/攻击安全证明 |
| 轨迹 | CC2.1.205；4个Bash与4结果；5个message_start与5个stub请求；result=success，stderr0字节 | 完整确定性CC工具调用往返，不是自主模型求解 |
| 清理 | container_rm=0；network/relay failures空；标签残留为空；agent进程0 | 本次scope清理完成；pytest产生缓存正常，不能写“工作区没有写入” |

四份capture分别468/899/19/214字节，均与attempt记载一致且远低于200000截断线；已解析完整trajectory JSONL并核结果事件。实际CC首条消息是 `Devcheck run: execute exactly the tool calls you are given, then stop.`，没有本轮完整题面交付的证明。stub的token/金额是合成响应，不算真实模型费用。总起止39秒、solve15.034秒；逐条开发命令墙钟未记录，0.54秒仅pytest自报。

两个继承checks=false不否定已查事实：`interpreter_in_tool_result`查固定RH2_SYS_EXECUTABLE标记，本题打印PY_CHECK；`bashenv_denied_for_agent`查固定写入尝试标记，本题未运行那一命令。解释器有实际tool结果和activation探针；激活文件不可写有prelaunch探针。保持原始字段，不改成true。

`image_facts.inspect_rc=1`发生于拉取前，inspect为空；运行容器实际image ID由prelaunch和container_inspect共同给出：`sha256:e61eaef6ac2759d2f5e96f20126a3ac51121f2e17de7d43238f8237770382162`。本attempt缺RepoDigests，应由root已有镜像清单补引；不因此抹掉已知运行image ID。

当前只认可**原环境公开开发校准**。尚无本题本批gold/错误候选、正式交付/安装/参考测试与评分、本批冷恢复及最终题级独立验收，不能升成训练资格。

## 3. 安装配方为什么在当前模式仍有效

逐层静态核对如下：

1. `replay_with_install_recipe.py:36–42` 包装当前 `replay.build_grading_spec_from_host_view`，并校验题ID和原vendor安装字符串；第75–82行把`eval_script`与`candidate_test_script`中唯一原安装串换成recipe，保存before/after。源码并不替换两个新字段。
2. `prepared_task_face.py:238–243` 的candidate_test_script仍是环境前导 + vendor env + 安装 + 测试，同一个shell；`render_v2_candidate_install_script` 和 after_install 是另外两份可选字段，不替代旧字段。
3. `manager.py:770` 的config.supply默认None；`scripts/replay_grade.py:67` 建manager只传eval_log_dir/sandbox_profile，没有开启供应。`manager.py:2176–2183` 只有supply非None、profile在场及两段字段齐全才适用供应。
4. `manager.py:3371–3382` 在record.supply为None时写实际candidate_test_script；第3466–3477行单shell执行该文件。故本夜真正执行的是wrapper修改过的安装命令；SETUPTOOLS_USE_DISTUTILS等export与随后测试处于同一个shell。
5. `grading_scripts_digest` 默认单shell摘要包括trusted_setup/candidate_test/eval，因此当前recipe变更可进入实际脚本摘要；两段摘要只有启用时追加。资格仍须按实际新镜像/脚本重取，静态核对不等于安装运行成功。

没有为此运行项目或导入当前RH2。后续只须在正式日志确认实际安装命令、RC、import/加载、测试完整性与清理；不要求为了本静态核对重复一轮旧资格。材料/参考绑定覆写、environment_prefix特殊配方不是本批此次审查的授权目标，未验其任意组合。

## 4. 语法检查与精确版本

三个Python文件仅用标准库AST解析；bootstrap仅`bash -n`，全部通过。没有执行其top-level代码、安装器、rsync或Docker。

| 文件 | SHA256 |
| --- | --- |
| private_behavior.py | `3bf2e681e85c6c5596f1a46a9d398c1b3f510da04a51e7f30eb471e3e0f7bc4c` |
| bootstrap_remote.sh | `091d4b142a7a690d25a07576821fd7085e67ba73965ad381032e176d7d3374f9` |
| sync_evidence.py | `3650aa7addaadbf13b655c042dd51ef61330dea15d706af2a9355aa7b2b0b915` |
| replay_with_install_recipe.py | `fc570d892f9189292e8502e8bb69351e723d56f340f71a8298455c58ab761dc9` |

工具目录分别是`rh2/experiments/swegym_cpu_preprobe_20260929/`与`rh2/experiments/env_recipe_repair_20260919/`。同步后原件及本地当前代码可能与后续冻结版本不同，以上SHA为本次审查适用版本；修改后只复核变化影响的部分。

## 5. 校准调度与 signal 窄复核（同日追加，未运行）

`calibrator_campaign.py` SHA256 `89c4c9da095744710761b964750e06085d8d5b646975769fc980233f0464c630`；修订后 `private_behavior.py` SHA256 `379c4610b19aafa829fcf7967ad95d0ac9f5374c9e85f16c0b62a01a25cbb7bc`。两者AST解析通过。以 `runs/swegym_cpu_preprobe_20260929/frozen_code_v1/rh2` 的实际入口核CLI，未用工作树新生产字节替代冻结版本。

**当前两题正常路径没有发现阻断，可以执行并保留 executed_pending_review。** 核对包括：冻结build_derived支持compat_v1；Dask7656 grader/actor pins与COPY位置一致，actor新增conda钩子、私有命令显式export；devcheck参数存在且自动按命令数增加max-turns；replay的candidate-stage/grading-deadline、noop/gold-dir/patch格式及账本report.reward/cleanup.removed匹配；冻结wrapper仍修改供单shell执行的candidate_test_script。Pydantic复制8个已校验wheel、离线安装recipe消费候选pyproject、目标core沿原actor条件；未把COPY wheel当预装。

同步 `remote/inputs_v1/<iid>` 与本地两题输入文件逐字一致；本地私有gold与同步 `remote/gold/v1/<iid>.gold.patch` 逐字一致。prepared/v1 summary指向本批实际prepared/private目录。Dask actor只消费公开命令与公开依赖镜像；Pydantic原actor不重复；gold/错误候选只进入private_behavior与正式grader。因此没有从脚本发现将私有patch挂入actor的路径。

保留一个**误结论风险，非本轮派发阻断**：campaign只检查actor harness_exit_code和残留，没有核all_commands_ran/all_match_expect；devcheck即使一个业务命令失败也可返回0。因此compat_environment失败仍可能继续剩余实验。最终状态明确为pending_review而非通过，维持这个语义即可；读回时必须逐命令核实际输出，不能把campaign退出0当依赖已对齐或actor资格。可窄加命令运行/环境检查来提早停止，但不为此重跑已完成的校准。

signal修订注册SIGTERM/SIGINT，处理器抛SystemExit；正常送达一次信号时会沿except BaseException进入finally的rm/ps核查，原R1此路径静态修正。没有实际信号演练，不声称任意强杀、重复信号、host断电也可清理。campaign父进程本身没有signal处理；外层应对整个作业控制组停机并收齐子进程清理，不能仅kill父PID后假定其子作业也停。此处是取消使用边界，正常运行不受影响。
