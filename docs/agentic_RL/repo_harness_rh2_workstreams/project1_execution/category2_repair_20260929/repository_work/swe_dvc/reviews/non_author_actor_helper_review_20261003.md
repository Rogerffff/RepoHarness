# DVC 公开 actor 窄核入口：非作者静态复核

2026-10-03。**未发现必须阻止当前 5839／6954 入口运行的静态缺陷；本报告不是 actor 通过。** 非作者已阅读私有题目材料和此前核查结论，不称 fresh 公开读者验收。本次仅离线读取及 AST／JSON 解析，未运行入口、CPU、Docker、SSH、安装或项目维护测试，未修改入口或共有文件。

## 继承关系、profile 与清理

`public_actor_check.py:72–77` 从输入所指定 release repo 的固定路径加载 `devcheck.py`，其 `BoundedDevRunner` 只覆盖 `image_facts`；冻结 R5 的 `DevRunner:80` 继承 `acceptance_startup_2.Runner`。因此 actor 仍走冻结 Runner 的 context/spec、relay／内网、sanitize、可信初始化、激活文件、启动前与激活检查，以及 `ClaudeCodeDriver.run`（acceptance 第177–259、283–321行）；stub 的变化是 DevRunner 第89–95行把公开命令清单转换为 Bash tool_use 剧本，仍由冻结 stub 原样落盘请求体。没有把这个桩当作真实模型探针。

新 image-facts 探针使用同一 `_profile()`／`docker_run_args()`，先要求 2 CPU／4 GiB／PID512，network 为 none，明确核镜像 ID、HEAD、干净初态以及声明的基线测试存在性／SHA（helper 第78–107行）。它没有放宽正式 actor 的 profile 或启动检查。helper 不自己申请 CPU 槽，依赖文档所要求的外层 `cpu_slot` 门控；本报告没有绕过该门控，也没有核实本轮远端输入或 job 状态。

探针在 finally 中删除；所有容器带本 attempt 的 `rh2.run_id` 标签，外层 finally 调用继承的 cleanup。冻结 DevRunner 第180–195行会按该标签清理容器／网络，并重新查询；查询失败保留 `<…query_failed>`，不能当作零残留。helper 第164–169行还要求 `residual_after_force` 确为一个空列表。探针删除失败或其它抛异常路径不会进入成功打印分支。这里的 clean 只覆盖标签容器／网络，不代表已经证明宿主所有进程、卷或镜像都清理了。

## 首请求与公开命令

helper 第35–66行校验所声明 code_files、prepared summary／manifest、public bundle、开发说明及命令文件 SHA；按 task_id 读取公开题面，核题面自身 SHA，并把开发说明原 UTF-8 文本追加到准备好的 prompt。第144–163行从本次新输出目录的 `messages_000.json` 读取首个 Messages 请求的 user text；题面及开发说明均须作为逐字连续文本出现。stub 第40–49、61–82行确实在第一个 Messages 请求使用索引000原样记录请求体，因此检查对象不是构造前的 prompt 或后续请求。允许其它包装文字是这个包含判据的明确范围，不要求整个首请求只包含题面。

helper 第166行需要 runner RC=0、清理成功、首请求文本齐全、checks 非空且每值严格为 True。冻结 DevRunner 第150–178行按每条命令的独立 rc 文件判断：缺文件视为未运行，当前两题均 expect=zero，超时或非零不会满足成功。继承 checks 还要求解释器前缀、真实 harness 完整轨迹、result 事件、请求计数吻合、容器内无 launcher／harness 目录及 bash_env 对 agent 不可写。因开发测试可合法写工作区，DevRunner 只移除了 git clean／无新文件两个不适用的终态判据；这不是取消入口的初态检查。

两份命令清单都是4条公开开发命令：身份／公开依赖 pin、激活文件权限、已有基线测试、pip check 与已有 CLI 帮助。5839 的 precision 两节点存在于公开基线第133／303行；6954 的 `tests/func/params/test_show.py` 是既有功能文件，含11个实例。测试命令去除 `PYTHONPATH=/testbed` 前缀后与对应 `public_development.md` 中命令逐字相同。没有安装、下载、应用有效测试补丁、加载私有新单测／断言或执行评分。身份命令输出解释器与 CONDA 并由继承检查约束解释器前缀，另直接断言 uid54321、公开依赖版本及 DVC 从 `/testbed/` 导入。

## 非阻断限制与后续读回要求

有一个具体成功判据缺口：冻结 DevRunner 记录 `pytest_counts`（第163–166行），但 evaluate 只检查各命令 rc／expect（第175–177行），helper 也只汇总这些 checks。因此“pytest 全部 skipped、退出0”仍能满足命令成功，不能仅凭 `actor_checks_passed=true` 宣称公开测试全部实际通过。当前指定基线测试没有 skip 标记，本次未见实际 skip 原件，这不构成当前输入的静态启动阻断。实际运行后仍需读公开测试的捕获日志，区分5839预期2个、6954预期11个实例的 PASSED／skip／缺失；不修改冻结代码来扩大本轮范围。

成功判据的清理与逐字题面检查比单纯 driver RC 更严格；未发现当前成功表达式会把 missing rc、非零、清理查询失败或缺少首请求直接算通过。本次没有检查实际远端 input JSON 的字段值／code_files 完整集合、tarball、依赖镜像实态、prepared 文件实际运输、CC请求或任何运行输出，因而不验证声明 SHA 已在运行时匹配，也不授予 actor、正式 reward、环境／训练资格或模型探针通过。

## 实际读取 SHA256

本包为 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_dvc/`；R5 为 `runs/category2_repair_20260929/releases_20261003/r2e_078_079_swe7_git_candidate_v1/repo/`。以下值由本次直接读取字节计算。

| 文件 | actual SHA256 |
| --- | --- |
| 本包/public_actor_check.py | `91c8bb818c10f6492be45f20ada71f252fcb6884aed5c12539c109cb4fe689d0` |
| 本包/tasks/iterative__dvc-5839/public_actor_commands_v1.json | `bf3f03725bf9eee3cde842973f6a424049654bb6ba5044c0f20616b196dfe148` |
| 本包/tasks/iterative__dvc-6954/public_actor_commands_v1.json | `82cf057ad54730b91caabbca42df943f4f440720057ea35855ef03f3b565deb5` |
| R5/rh2/experiments/task2_swegym_dev_20260925/devcheck.py | `75399297da458697ebcd17e6ca79aad90b56e4dbdda3214a4c70f82a4b389160` |
| R5/rh2/experiments/base_probe_fixes_20260923/acceptance_startup_2.py | `c67194f09e202c1cd1e83a3a1fbf5df7706952d2e542f97a4b2f3882604dc5d1` |
| R5/rh2/experiments/base_probe_fixes_20260923/stub_anthropic_endpoint.py | `dab06b7a5ed681e9938c6033f41e3bd6947cdc19c0e333e7fc5a859d805f5138` |

辅助核对的公开开发说明：5839 `b768b8c5aa55e217660dbf6cebd4b5a53350f0d6e55af8e56aedb7804db0a8a7`，6954 `08c2eb10117973633bfb40431753064bbbf7efe1886b8db34ab350cd42c8b1da`；公开基线文件：5839 test_metrics.py `64f7af4cebece4c559b2edf1e86e38a45c2c340ff8c395510fbca09b8e19e2ca`，6954 test_show.py `b4f326a46584b7a6e4eae8462ff5018341dee1bbaf2eaef4c5dca37bbf4436eb`。
