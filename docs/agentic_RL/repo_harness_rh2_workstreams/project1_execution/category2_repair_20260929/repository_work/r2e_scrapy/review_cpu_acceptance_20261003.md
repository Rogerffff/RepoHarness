# Scrapy a95a：非作者 CPU 验收核查

2026-10-03，Codex。仅核 `scrapy__a95a338eeada7275a5289cf036136610ebaf07eb`。**正式八候选矩阵、最新 R5/runtime v2 的真实 Claude Code 桩驱动开发验证，以及两种 C1 的目标环境警告列表均已通过非作者证据核查；本次未发现 CPU 验收阻断。** 两个通用 checks 的原始 false 保留并在下文解释，不能称“所有 checks 都为 true”。可按既有流程提交统一质量探针；这些证据不授予训练或留出资格，也不是模型自主求解结果。

## 核查身份、范围与上下文

本核查者不是 rev4 材料、候选或执行脚本作者，也不是新公开读者。收到题主定向提供的任务 ID、预期八候选矩阵、负例失败机制、冻结 release／材料摘要、build 与矩阵路径，以及 actor 和警告观测待补的说明；读取了 `AGENTS.md`、`remaining_workflow_20261002.md` §3/§5、审查标准和同包 `review_rev4_20261003.md`。因此本报告是带定向上下文的非作者独立证据核查，不声称盲审。

续接时又收到最新 dev 原件路径、R5 manifest、题主对 R4/R5 材料相同的判断、五命令／警告列表预期，以及两个通用 false 的调查线索；本核查独立重读冻结代码和原始轨迹，不把这些线索当成已核事实。此前槽满返回 75 的尝试（本包共 7 次）均未执行 actor／警告观测，不计通过。本报告只接受实际完成的 `scrapy-a95a-dev-b-20261002T183830Z`。

公开题面未变；冻结 public bundle 的题面摘要为 `sha256:eddf95214b7bbc41b0b1109eab8ab79319f9af065385831fcbf5eebff558bffb`，本次登记 066/067 只修改私有测试和 expected。接续既有非作者静态意见，不重做公开阅读。只读原件及冻结源码，离线重解析／重算摘要；没有 SSH、Docker、模型调用、共享 smoke 或全仓测试。唯一写入本报告。

## 证据与适用版本

以下路径均相对仓库根：

- 输入 `runs/category2_repair_20260929/r2e_scrapy_cpu_20261003/inputs/scrapy-a95a-inputs-20261002T170126Z/`。
- build `runs/category2_repair_20260929/r2e_scrapy_cpu_20261003/scrapy-a95a-build-b-20261002T175157Z/remote_evidence/`。
- 正式矩阵 `runs/category2_repair_20260929/r2e_scrapy_cpu_20261003/scrapy-a95a-matrix-b-20261002T175619Z/remote_evidence/`。每候选保留 `.jsonl`、`grade_*.command.json`、stdout/stderr、`*_logs/*.eval.log`／diagnostics 及 `*_artifacts/`。
- 执行源码 `runs/category2_repair_20260929/releases_20261003/r2e_070_077_swe6_candidate_v1/repo/`，manifest 原件在其父目录。
- 最新 dev 原件 `runs/category2_repair_20260929/r2e_scrapy_cpu_20261003/scrapy-a95a-dev-b-20261002T183830Z/remote_evidence/`；下文最新材料、actor、警告路径均相对此根。
- 最新 dev 执行源码 `runs/category2_repair_20260929/releases_20261003/r2e_078_079_swe7_git_candidate_v1/repo/`（R5），manifest 重算为 `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`。

重算 manifest SHA256 为 `621e73660ea5685b9a77c353e7f4f3664d7eefa073aed8454bae1ae3e32f388f`，与两份 binding 和作业命令一致。核对 manifest 中相关实现、parser、builder、登记／pins 与 ingest 文件共 122 项，没有字节差异。输入 inventory 的 13 项均重算相符，inventory 摘要 `ef836a12f7533611c88ae73d018ef5fd3a494f71dc35936a34bd20dc57f812ca` 与 binding 一致。

冻结 `PrivateGradingBundleR2E` 验证与重算得到：

| 身份 | 实际值 |
| --- | --- |
| 私有材料修订 | `r2e-mr-066`、`r2e-mr-067` |
| `test_1.py` SHA256 | `9c6bc43ef5eead9453128d7d40959afb7bfd0d9e85c4c068a6d17993c991abac` |
| hidden tree SHA256 | `e6f17ed8b7f80a0c0d6654f35d60e42bfd39a187f8c2442b854e388206349aeb` |
| expected SHA256 | `95f7d31faf0fa9838958db3a8121edc60a6181b7194f4801d674ef41802fe8e9` |
| grading bundle digest | `sha256:d1100b03f4ce6a712cff8d7a745231264b77b1e7ac86b453bf168db8908c39ee` |
| public bundle digest | `sha256:725ad95a6b609f2d8d8971301fbaf41384b3ddd4eff163e21482d14b015585e0` |
| `run_tests.sh` SHA256 | `8285765fcf1a4ec23ca55ad4781a064d121b58266ef5c5e22c681f6ece616aaf` |
| scripts digest | `sha256:58f8a9efa4601768a5955c451f08a56b7b84d5dad7e5e181d61b8c486b23955a` |

scripts digest 用冻结 `build_r2e_grading_spec()` 重建 trusted setup／candidate test／eval 三段，再调用 `grading_scripts_digest()` 计算，八行相同。八份原日志都直接打印匹配的 hidden tree 和入口摘要，`RH2_SETUP_OK=1`；并非只凭外层 binding 推定材料已执行。入口仍为 `PYTHONWARNINGS='ignore::UserWarning,ignore::SyntaxWarning' .venv/bin/python -W ignore -m pytest -rA r2e_tests`。

## 正式八候选：逐键重解析与机制

使用本机 `rh2/.venv/bin/python -B`，将冻结 release 的 `rh2/src` 放在 import 首位，从原始完整 eval 日志调用该 release 的 `scoring.parse_eval_log_r2e()`。expected 来自已核 SHA 的输入文件；同时用冻结 `PrivateGradingBundleR2E` 验证实际 ingest 材料。八份重算 verdict 的逐键匹配、reward 与 diagnostics／账本完全相同。

下面所有测试键都带前缀 `UtilsMiscPy3TestCase.`。每行实际解析 5 键、`reference_missing=[]`、`unexpected=[]`、段外解析数 0、`apply_ok=True`，未跳过测试。完整五键中还包含 `test_generators_return_none` 和 `test_generators_return_none_with_decorator`，这两键八次均通过。

| 候选 | 预期／实际分数 | 匹配数 | 精确 FAILED 键 | 原日志证明的失败机制 |
| --- | --- | --- | --- | --- |
| C1 | 1／1 | 5/5 | 无 | 五键全部通过。 |
| gold | 0／0 | 4/5 | `test_partial` | `test_1.py:300` 的 `partial(Callbacks().method_with_return, 1)` 真正执行后返回 False，断言失败；保留 partial 绑定方法的负对照。 |
| noop | 0／0 | 4/5 | `test_partial` | `test_1.py:286` 首个无返回值 partial 调用进入 `inspect.getsource(partial)`，抛出 TypeError。 |
| D | 0／0 | 4/5 | `test_partial` | 捕获 TypeError 后错误地返回 False，`test_1.py:292` 有返回值 partial 的断言失败。 |
| C2 | 0／0 | 2/5 | `test_generators_return_something`、`test_indentation_error`、`test_partial` | 前两键在 `:80`／`:278` 警告条数为 0 而应为 1；另在 `:300` 保留绑定方法缺陷。 |
| C2b | 0／0 | 3/5 | `test_generators_return_something`、`test_indentation_error` | C1 的解析修法仍使 partial 键通过，但警告函数开头的 `return` 关闭两类警告；两键恰好因 `len(w)=0 != 1` 失败。 |
| C3 | 0／0 | 3/5 | `test_generators_return_something`、`test_partial` | 检测函数恒返回 False，分别在 `:71` 普通生成器及 `:292` 有返回值 partial 断言失败。 |
| C1_RuntimeWarning | 1／1 | 5/5 | 无 | 相对 C1 只为两处既有 `warnings.warn` 指定 RuntimeWarning；五键全部通过。 |

这八行与同包 `acceptance_matrix.json` 的预期失败键完全相同。以上根据 traceback、断言位置、候选字节与逐键状态共同判定；总分本身没有替代语义核查。旧 rev2 九次试跑及可选 rev2 类别配对诊断不计入本次八行，也没有被改写为 rev4 通过。

## apply、投影、基线、执行与清理

八个 replay 命令退出 0。七个补丁候选 `git_apply` 成功，无 apply stderr；noop 为显式 noop。stage 均到 projection、`stage_error=null`；candidate exec exit 0、segment completed。测试 exec exit 0 表示外层执行完成；真实测试 rc 为 C1 与 RuntimeWarning 0、六个负例 1，不能把二者混同。

逐候选重算完整日志 SHA，均与 ledger 一致；七份 artifact `candidate.patch` 与冻结 input 中对应文件逐字节一致，patch SHA 也一致。FrozenPatch（冻结的文件改动集合）经当前契约模型逐条校验 base64 与内容摘要，再重算整体摘要，八份均与 projection／ledger 一致。非 noop 仅投影 `scrapy/utils/misc.py`，noop entries 为空；无 ignored／unsupported paths，无 test-like 或 conftest／fixture 改动，classification 均 `projectable`。

八份 baseline manifest 均经契约模型验证并重算到 `sha256:e15346aea12442b6d62170e65748bfcf8eed9e647513672fa243b7f57e138d67`，与各 FrozenPatch 引用一致；base HEAD 均为 `9077d0f9b490114f117c668f115240c16afccedf`，public／runtime lineage 一致。候选和 grader 两侧 git sanitize 均 verified，无 violations。快照的大 binary snapshot 未纳入传回包，因此本核查没有离线重建全树 census，也不声称重新运行 baseline 重建；正式执行记录没有 baseline 重建异常。

runner integrity 八行均 false；前后实际 runner digest 均为 `067c6080788af8288ff8c5d9cf94560b3bf62d24f37833995ec57b7ba74633e9`，导入来源 `/testbed/scrapy/__init__.py`、Scrapy 2.7.0。所有原日志为目标 Linux Python 3.9.21／pytest 8.3.4／pluggy 1.5.0，恰好 collected 5 items。

八行候选 cleanup 均 `removed=true, rm:ok`；每份 replay stdout 结尾的 manager close 均 created=removed=1、containers_open／supply_open／cleanup_failures 为空，未 halted 或 aborted，final_status 为 exit 0／reason ok。评分原件支持本批容器已收口。

## build 与镜像真实性

build 命令使用冻结 builder，重算源码 SHA256 `5af7dc214976336ea440674bc4416cfa0a805881463798e05ebbb3e33af19471` 与 manifest／command／job 一致，命令退出 0。build facts 的 `ok=true`、failures 空：原始 RepoDigest 为 `sha256:cd01a127a7c83ad8e59e0380f34dbf20e7469fe0ae4ebb051c83993dbc4d067d`；派生实际 image ID 为 `sha256:ac29555d3b7cceaf6d2ce5654eda8d04408bcea370e6373963a04565b7d05ded`，八次评分均实际使用该 ID。

配方 `r2e_derive_v1+material_v2+sysconfig_v1`／SHA `22f7c2ec0e7620445acec40a03e771081a29de50e54c8dec88ac991cc05eac0a` 与 overlay／ledger 一致；本题 env_pins 空。原层保留、git 工作树保留、解释器 relocation／sysconfig、隐藏测试 root 私有且两种非 root 身份不可读、公开位置无隐藏测试、入口与材料匹配均有 facts。builder 中仅列 066 是 hidden-test revision；expected 的 067 在 grading bundle 与 binding 中，不要求镜像改写 expected。

构建命令明确 `daemon_build_limits_verified=false`；不将 `--container-cpus 2 --container-memory 4g --container-pids-limit 512` 解释为 Docker build daemon 的资源限制已经验证。该字段不改变本题测试结果，但保留资源证据边界。

build 原件未单独传回构建容器清理／全机残留清单。冻结 builder 的 `Docker.bash()` 在 finally 逐个清理自身容器，删除后再次 inspect，不可确认清理会抛出 DockerCleanupError 并停止批次；结合本次 builder 退出 0，可支持该路径正常收口。它不等价于独立全机残留审计。

## 最新 R5 材料接收与镜像复用

`transfer_inventory.json` 列出的 56 份文件逐项核 SHA256 和字节长度，全部相符，`omitted=[]`。传输程序末尾打印本地相对路径时的 ValueError 没有使这些证据丢失，不作 actor 执行失败处理；这是 fetch 后处理异常，不改称 collector 整体退出 0。

独立在两个 Python 子进程中分别导入 R4、R5 冻结 `load_trusted_r2e_ingest_outputs()`，以各自 pins／registry 读取本题；得到 public bundle、grading bundle、066/067 完整条目完全相同，并与 `acceptance/task_material_identity.json` 完全一致。没有用 R5 的常量读取 R4 pins。R5 不改变本题题面、测试或 expected，原矩阵继续绑定 R4；旧 FrozenPatch 没有改绑到 R5。

`acceptance/prepared_r5/` 为 R5 新准备材料；manifest 与 host grading 摘要按原件重算相符，public manifest／rollout views／prompt 经 R5 原 loader 核验，host view 内容经 R5 `HostGradingView.revalidated()` 校验。复用的 facts／overlays 与原 build 原件逐字节相同；`acceptance/image_reuse_binding.json`、冻结调用程序及 actor 实际 image inspect 共同证明远端 R5 `PreparedTaskFace.load()` 和实际镜像身份核对成功。R5 actor 使用的仍是同一派生 image ID `ac29555d…`。

本地传输副本的 runtime-private 文件权限为 0644，与执行端私有加载要求不同：本核查直接调用本地 `PreparedTaskFace.load()` 时被权限检查拒绝，未改副本权限、未绕过加载策略。本核查因此只声明本地字节／内容重验和远端真实 loader 执行证明，不声称本地完整 loader 成功，也不把只读归档副本误作运行产物。

## 最新真实 CC 桩驱动开发验证

证据为 `acceptance/actor_r5/actor/attempt.json`、`prelaunch.json`、`activation_check.json`、`captures/*.out`、`harness/trajectory.jsonl`、`stub/requests/messages_000…005.json` 和 post-run facts。冻结 CC harness、bringup、sandbox、actor／devcheck 入口与 R5 manifest 的字节摘要均重算一致；实际 CC 版本 2.1.205，入口未为本题改写。

这是 CPU 桩提供固定工具调用、由真实 CC 执行的开发验证。初始用户消息是中性的 `Devcheck run: execute exactly the tool calls you are given, then stop.`，不是正式 solver 的公开题面交付。私有 C1 是本次专门注入的正对照，不把它当模型自主写出的补丁，不把桩的模拟 usage／cost 当真实模型消耗。

原始轨迹共五个 Bash tool_use、五个对应 tool_result，工具 ID 逐一匹配；每条保存的 capture 全文出现在实际 CC tool_result 中，并原样返回最终 stub 请求。不存在只从 host 捕获输出推定 CC 已看到的情况。五命令如下：

| 实际命令 | 结果 |
| --- | --- |
| 自动 R2E preflight | rc0；解释器、隐藏测试隔离、git 历史三项 ok。 |
| `env_python_scrapy` | rc0；`/testbed/.venv/bin/python 3.9.21`，Scrapy 2.7.0 从 `/testbed/scrapy/__init__.py` 导入，partial 的 generator 检查为 True。 |
| 私有 C1 apply | rc0；先核 C1 补丁 SHA，再经 agent 身份 git apply --check／apply，打印 `RH2_PRIVATE_C1_APPLIED=1`。 |
| 公开问题的文件形式复现 | rc0；打印 `is_generator_with_return_value(partial_gen) -> False`。 |
| 现有公开窄测试 | rc0；`tests/test_utils_misc/test_return_with_argument_inside_generator.py` collected 4、4 passed，四条 PASSED 均在真实消息中。 |

prelaunch 实测 UID/GID 54321、CAPEFF/CAPPRM 为 0、no-new-privileges，activation 解释器／prefix 均为 `/testbed/.venv`。HostConfig 与 cgroup 实测 2 CPU、4 GiB、512 pids、swap 0。actor 网络使用隔离网络及受控桩 relay；外部 DNS、四个 forbidden 目标和 upstream direct 均 DENIED，只有 relay CONNECTED。因此这里的“断外网”不等同于 Docker `NetworkMode=none`。

两个通用检查的原始 `false` 如实保留：

- `interpreter_in_tool_result=false`：冻结 `acceptance_startup_2.py:332–334` 只搜索 `RH2_SYS_EXECUTABLE=<prefix>/`，本题清单没有该标记；`task2_swegym_dev_20260925/devcheck.py:178` 也明确该检查依赖 PY_CHECK 命令形状。本题实际工具输出与 activation 直接给出正确解释器，因此不构成解释器失败。
- `bashenv_denied_for_agent=false`：冻结 `acceptance_startup_2.py:346` 只搜索工具结果里的 `RH2_BASHENV_WRITE=DENIED`，本题没有执行输出这一标记的命令。实际 prelaunch 用 agent 身份测得 `ACTIVATION_READ=1`、`ACTIVATION_WRITE=DENIED`、`ACTIVATION_STAT=0:644`，与冻结 `sandbox_profile.py:1916–1919` 的“可读、不可写”边界一致。此文件本来需要由 Bash 读取；检查名不能解释成应禁止读取。本报告没有将 raw false 改为 true，也不声称新增的 CC Bash 写入探针已执行。

CC result 为 success、6 turns、无 permission denial，harness exec 退出 0、log_complete=true、stderr 空；post-run agent processes=0，没有 harness dir／launcher／done marker。允许的工作区写入是 C1 与现有测试生成的 localhost key／crt。cleanup 的 container_rm=0、relay／network failures 空、stub_rc=0，自身 labeled containers／networks 和 residual_after_force 均为空。实际开发命令与收尾证据足以关闭该题 actor 缺口；外层 rc0 本身没有被当作全部 checks 成功的证据。

## 目标 Python 3.9 的逐块警告观测

`acceptance/private_warnings/{C1,C1_RuntimeWarning}.stdout.json`、`observation_summary.json` 及本地保存的两个只读诊断脚本共同限定本项范围。诊断对原始测试字节核 SHA，用继承原 `warnings.catch_warnings` 的观察包装记录既有列表，不改测试断言、过滤器语句或正式入口；通过 unittest 执行原五个测试。它是 root 私有观测，**不替代上面的 actor 或正式矩阵**。

两候选均在同一派生镜像、Python 3.9.21 下测试 5 项，无 failures/errors；每份恰好 22 个记录块：两类 none 测试各 8 块为零警告，something 的 5 块及 indentation_error 的 1 块各只有 1 条警告。C1 六条全部 UserWarning，RuntimeWarning 候选六条全部 RuntimeWarning；逐项比较，类别之外的文案、文件和行号完全相同。

六条均来自 `/rh2_private/r2e_tests/test_1.py`，行号依次 79、84、89、94、99、277，对应记录块起始行 77、82、87、92、97、275 和实际调用行；前五条分别准确包含 `NoneType.top_level_return_something`、`NoneType.f1/g1/h1/i1` 的既有生成器返回值警告，第六条是 `NoneType.top_level_return_none` 的既有缩进错误诊断。没有依赖警告混入。两份 `filters_restored=true`，块退出后恢复全局过滤器。

两次私有观测均 exit0，实测 HostConfig 2 CPU、4 GiB（MemorySwap 同为 4 GiB）、512 pids、NetworkMode=none；按容器 ID 与 run label 删除并核 residual_after_cleanup 为空。这关闭静态意见中特别保留的“扩大 Warning 范围是否混入依赖警告”待验条件。

## 用途与停止条件

本次 CPU 核查已完成，不再为旧 rev2 九次试跑或两个固定标记的 false 机械重跑矩阵。已知绑定方法漏判、关闭警告漏判和类别误拒均有正式对照及真实失败／通过机制；最新开发命令也经真实 CC actor 执行。

题主可按已授权流程提交统一质量探针，使用最新接收材料并明确沿用 R4 本题不变矩阵；由执行宿主从 R5 重新生成 prepared/private、保留私有权限，不把本地回收的路径或权限作为运行输入。模型探针须用干净公开输入，不携带本次私有 C1／反例／结论。CPU 通过只支持修订与开发环境验收，不证明模型能力、RL 信号、训练或留出资格。本报告不新增授权闸门。
