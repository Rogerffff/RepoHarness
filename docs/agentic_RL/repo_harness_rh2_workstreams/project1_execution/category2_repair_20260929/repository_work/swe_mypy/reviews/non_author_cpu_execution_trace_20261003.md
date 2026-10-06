# mypy CPU 执行证据核查：Production Tracer

整理日期：2026-10-03。状态：已有 CPU 原件及 10174 第六版新正式矩阵均已核，已达到本角色停止条件。

## 已核事实

- 原正式矩阵：10174 的 noop/gold/bad 为 **0/1/1**；15184 的 noop/gold/bad/top_only 为 **0/1/1/1**。每个候选均真实执行、解析原三个参考；不是把包装器退出 0 当题目通过。
- 10174 第六版新正式矩阵：noop/gold/bad 为 **0/1/0**；四参考均真实选择、执行和解析，缺席/跳过/未对账均为 0。bad 只在新增 P2P 漏掉预期不重叠诊断，原三个参考仍通过；不是安装、保护或补丁应用失败造成的拒绝。
- 私有行为：10174 新不重叠诊断 case 在 base/gold 通过、bad 失败；15184 有效断言小组在 base/gold/top_only 五项通过，bad 三项失败、两项通过。15184 嵌套 case 的有效第二版在 base/top_only 失败、gold/bad 通过。单个失败断言不能替代正式 reward。
- 真实 actor：两题均经过 CC 2.1.205 的五次 Bash 调用，公开命令退出码均为 **0/1/0/0/0**；UID 54321，2 CPU、4 GiB，无宿主 bind/mount，实际解释器和 mypy 源码路径正确，捕获输出未截断，容器、网络、relay、stub 清理完成。
- 本地冻结 release 的 manifest 和其中源码/材料字节已直接核 SHA/size：首版 794 文件、第五版 837 文件、第六版 855 文件，均无不匹配。原矩阵和私有控制用首版；本轮 actor 用第五版。各运行不能合并成一次新版本验收。

## 发现的问题与证据限制

1. **原评分能接受已证实有行为错误的源码候选。** 10174 bad 关闭非 strict-optional 的比较，原三个参考全通过；私有新增 case 真实失败，Expected 为 `Non-overlapping container check`，Actual 为空。15184 bad 把有效断言也变成错误、top_only 只限定顶层名字，原三个参考均通过；私有有效断言/嵌套 case 分别揭示遗漏。这是本包已登记问题的执行确认，不是新发现的修复回归。原材料不能因 CPU 安装通过而被宣称具有充分评分区分度。
2. **嵌套首版不能算有效负候选拒绝。** 首版所有候选失败，包括 gold；gold 原日志实际显示 `List[a.C]/List[b.C]`，首版期望却是小写 `list`。第二版只把新增 case 的期望诊断改为 `List`，原三个 case 正文不变；第二版的 base/top_only 失败是实际内部名字仍为 `List[C]/List[C]`。
3. **actor 的 `bashenv_denied_for_agent=False` 必须保留并解释。** 原轨迹和命令清单没有执行产生 `RH2_BASHENV_WRITE=DENIED` 的写入命令；冻结 normal 场景把“轨迹中未出现该标记”计为 False。prelaunch 另有 `ACTIVATION_WRITE=DENIED`，实际激活检查也通过。因此本轮五项公开命令证据成立，但不能写成所有 checks 全绿，不能据此声称全面完成角色隔离审查。
4. **原评分的版本观测有局部缺口。** ledger 的 `RH2_OBS_PKG_VERSION` 是 `?`，不是已测版本号。该缺口由实际 pip 安装日志和本轮 actor 的 `importlib.metadata` 输出补充：10174 是 `0.820+dev.c8bae…dirty`，15184 base 是 `1.4.0+dev.13f35…`，非 noop 的评分候选正常带 `dirty`。不能把 `?` 本身当版本证明。
5. **安装没有逐成功子命令的单独数字回执。** 原件有全量 pip 输出、每个简单命令失败的 ERR trap，以及段末 rc；我逐步核了 requirements 的 `Requirement already satisfied`、editable 安装的 `Successfully installed`、10174 额外 pytest/xdist 的已满足输出，七个运行均无真实 `RH2_INSTALL_CMD_FAILED` 或 `ERROR:`，段末 0。现有证据足以确认本批简单命令安装成功，但报告不虚构“各子步骤成功 rc 均单独保存”。

## 未完成与未知项

- 15184 新正式五参考矩阵和最终 solver 新题面实际交付：本报告未收到对应 release/prepare/评分/模型探针链的原件，故未验收。公开开发控制 prompt 和旧 public bundle 不能代替这些证据。
- 本轮没有新的 Docker、SSH、评分或测试执行；没有 GPU/真实模型求解。没有审查训练消费、训练/留出资格、全系统隔离、故障注入和扩展性能。
- 原评分 ledger `env_qualification=absent`，环境包 digest 为 null；这些原诊断运行不构成 qualification 闸门解除。

## 适用版本与上下文披露

角色为非作者 Production Tracer，依据 `review-standards.md` §10.4，范围限定为本包真实调用、执行身份、节点、异常及生命周期原件核查。审查者已见作者 CPU 清单、私有 grading/spec、gold、负候选、有效测试补丁和冻结材料 registry；不是 fresh 公开题面审查。未依据作者回读 JSON 替代原始逐项日志。此报告也不授予训练或留出资格。

下文的路径别名只用于缩短证据索引；均为仓库相对路径，无凭据或本机私有目录：

- `R` = `runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/`（ignored 运行原件）。
- `F` = `runs/category2_repair_20260929/releases_20261003/`（冻结 release 原件）。
- `P` = 本报告的上一级 `swe_mypy/` 包目录。

| 证据批次 | release / manifest SHA256 | runtime | 状态 |
| --- | --- | --- | --- |
| 10174 原正式矩阵 | `cat2-cpu-r2e064065-swe5-20261003-v1` / `282021962a92b510f077385660ac56acedcd7fac1d97e63db3baa98e4dcc057f` | `runtime/rh2/.venv/bin/python` | 原三个参考已核 |
| 15184 原正式矩阵、两题私有行为、嵌套 r1/r2 | 同首版 | `runtime_cpu_v2/rh2/.venv/bin/python` | 已核，各 spec 分开解释 |
| 两题 actor | `cat2-cpu-r2e078079-swe7-git-20261003-v1` / `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9` | `runtime_cpu_v2/rh2/.venv/bin/python` | 五项公开命令已核 |
| 10174 新正式矩阵 | `cat2-cpu-r2e080087-swe8-git-20261003-v1` / `ab0a3a13fd65e0ea4cd60541ea3b37b01196170477e25832df246f33ea208828` | `runtime_cpu_v2/rh2/.venv/bin/python` | 新四参考已核，0/1/0 |

首版原件在 `F/r2e_064_065_candidate_v1/`；第五版在 `F/r2e_078_079_swe7_git_candidate_v1/`；第六版在 `F/r2e_080_087_swe8_git_candidate_v1/`。对三份 `manifest.json` 重新计算 SHA，并直接核其 `files` 字节和大小，计 794/837/855 项均零差异。

冻结关键入口：三个版本的 CLI `rh2/scripts/replay_grade.py` SHA 均为 `d36fa3367415e573305a7a03619f51e7cbd358627569f3844d5c203b70d66db3`；adapter `replay_grade.py` 均为 `3bd574eed3da9372b8640eac48d5da0b1141375c21b6e492de822d494443ef66`；grader `manager.py` 均为 `b6b10f98bf0e1a7bbe4774ac705ece6bb2746da2b1ac4f20394673293f24bbb0`；`private_behavior.py` 均为 `379c4610b19aafa829fcf7967ad95d0ac9f5374c9e85f16c0b62a01a25cbb7bc`；`devcheck.py` 均为 `75399297da458697ebcd17e6ca79aad90b56e4dbdda3214a4c70f82a4b389160`。未以当前共享工作树代码代替冻结源码。

## 原正式矩阵：逐参考与源码候选

原件入口：`R/mypy10174-original-r2-20261002T171442Z-f5b43f/`，以及 `R/mypy15184-original-r1-20261002T174349Z-51ce62/attempt/`。各候选均核 `ledger.jsonl`、`eval_logs/*.eval.log`、`*.diagnostics.json`、artifact 的 `baseline_manifest.json` 与 `candidate.patch`、候选 `.log`。七份 eval.log 的 SHA 均与 ledger 一致。

10174 原 public/grading canonical digest：`e1cc57aeabbf0261482d0d06da3c08509d54f12c32fc06b4cc6e8eedf8b9e41c` / `d2108a22f00a069d4fcec84b28a5aef244a222fd8945f4017345b30faef012bb`。15184：`9c0679c9ca5b06fa6ab36fa3c35ca418477ba85fd25b39feda9309eff0e6cab2` / `4d06500507c04fe8fe2843025d01f53ea8b6854f9fc72e1656bf7781b7da9b18`。重新 canonical hash `R/input_v1/original/*` 与每题 `baseline_identity.log` 一致；运行日志 `verify_release.log` 亦为首版 794 文件、trusted 48/216。

10174 节点在 mypy 0.820 不含 `.test` 文件层，以下全称均以 `mypy/test/testcheck.py::TypeCheckSuite::` 开头。

| 原参考 | noop | gold | bad |
| --- | --- | --- | --- |
| F2P `testOverlappingAnyTypeWithoutStrictOptional` | FAILED | PASSED | PASSED |
| P2P `testUnimportedHintAnyLower` | PASSED | PASSED | PASSED |
| P2P `testUnimportedHintAny` | PASSED | PASSED | PASSED |
| reward | 0 | 1 | 1 |

每项真实选择 3/9422 个 pytest 节点；原始短摘要逐个列出上述状态（noop eval.log 524–526 行，gold 536–538，bad 523–525）。parser 解析 3 个，segment 外 0，reference missing/skipped 均空，F2P 总数 1、P2P 总数 2。这里没有新增 P2P，也没有额外评分节点。

15184 节点在 mypy 1.4 含 `.test` 文件层，全称前缀为 `mypy/test/testcheck.py::TypeCheckSuite::check-assert-type-fail.test::`。

| 原参考 | noop | gold | bad | top_only |
| --- | --- | --- | --- | --- |
| F2P `testAssertTypeFail1` | FAILED | PASSED | PASSED | PASSED |
| F2P `testAssertTypeFail2` | FAILED | PASSED | PASSED | PASSED |
| P2P `testAssertTypeFail3` | PASSED | PASSED | PASSED | PASSED |
| reward | 0 | 1 | 1 | 1 |

每项真实选择 3/11322 个 pytest 节点；原始短摘要逐个列出状态（noop eval.log 477–479，gold 474–476，bad 488–490，top_only 485–487）。parser 解析 3 个，segment 外 0，reference missing/skipped 均空，F2P 总数 2、P2P 总数 1。新拟参考和其它开发 case 不加入这些数。

| 候选 | 原 patch SHA256 | frozen 源码路径 |
| --- | --- | --- |
| 10174 gold | `7f94c5b71301dbbf5ccce1af8b274444ab5c0de5010f92109e11549154066f6c` | `mypy/meet.py`，在非 strict-optional 简化后判断 Any 重叠 |
| 10174 bad | `07b2dc85c76973364ca1ee5d28304a40796402c7d6d4558c87964bf656187c30` | `mypy/checkexpr.py`，非 strict-optional 直接返回 False |
| 15184 gold | `365adadcf2ad3dbed4dc98bf30ebda81f9c788a8ced939ff2a2abd8bfef1a280` | `mypy/messages.py`，使用 `format_type_distinctly` |
| 15184 bad | `8e5df3cb5e3d52c5223551809cca394418ba3a5c3ee56afa1c41d27a5e5c2846` | gold + `mypy/checkexpr.py` 把 `not is_same_type` 改成 `if True` |
| 15184 top_only | `707f1748338159b53465ead34075d0ae7a84c1123b576c457fc42df8fbee66ad` | `mypy/messages.py`，只比较顶层 Instance 名称 |

原 patch、ledger patch SHA、stage apply 和导出的 `candidate.patch` 修改路径逐项相符；所有非 noop 都 `git_apply` 成功、`classification=projectable`，没有触碰测试/fixture 的候选路径；不存在用 apply/infra 失败冒充错误候选被拒的情形。

## 安装、源码、保护与清理

| 项目 | 10174 | 15184 |
| --- | --- | --- |
| base 镜像 digest | `ede92a3c5637b159fa7bbcf7f2ea29e44bd774435fcefd6b5845fdce81f691a6` | `affb925329f2dfb2173482c64a1b65648b250777b66b0d7417ee5340fce74835` |
| 本轮精确派生 image ID | `9d63f1ddcbd277fa62d49e10d800908cfec54544e890fc5fe741d2101ca8eb7e` | `76b5b2646a9eb134e6349ee8e214bb84eb6030c34a234e167351acdec5dd8c54` |
| HEAD / base_commit | `c8bae06919674b9846e3ff864b0a44592db888eb` | `13f35ad0915e70c2c299e2eb308968c86117132d` |
| 原初态 | `test-requirements.txt` 已修改 | 干净 |
| runner 前后 digest | `2f4655b6933a219bb88c823bdc724ed84e84c89a2a23b39c1f399cb1da2b61c4` | `bffa1d1e04c07d52b4d5db5941f0d97a8c71a68e29cca90c4bf5671ea66e1548` |

镜像原件：`R/mypy10174-image-r2-20261002T170715Z-9fed27/` 和 `R/mypy15184-image-r1-20261002T170855Z-d21f39/` 的 build.log、image_prepare.json、base_image.json、derived_image.json。pull/build 均 0；实际 Dockerfile 只 `COPY wheels/` 并设置离线 pip 环境，两张派生镜像保留原 base 全部 layers，只追加一层。10174 的 requirements 初态变化不是此次 COPY 或 actor 命令新增。`R/input_v1/input_manifest.json` 43 项 SHA/size 全部一致；三 wheel / 九 wheel 原件各匹配 image_plan，去重共有十一份。

七份评分日志逐步骤检查：10174 的 requirements（32 条已满足）、editable 安装（mypy 成功安装）、pytest/xdist（11 条已满足）；15184 requirements（34 条已满足）、editable 安装（mypy 成功安装）。冻结 `prepared_task_face.py` 190–205 行为每条失败简单命令记录 ERR trap；这些运行均没有真实失败标记，没有 pip ERROR，安装 segment 完整且非跳过。段末 0 本身不是判断依据。

评分 diagnostics 的源码观测均是 `/testbed/mypy/__init__.py`；prefix owner 是 grader UID 54322。control surface 均 `RH2_PROTECT_OK=1`、expected/protected test file 1、missing 0、irregular 0、protected dirs 3、writable prefix complete。trusted test patch apply rc 0、setup OK 1。10174 恢复已有测试文件；15184 原新增测试文件没有需恢复的旧文件，因此 `RH2_SETUP_RESTORED=0` 不表示应用失败。各 `baseline_manifest.json` 的 HEAD 和 runtime image 与上表一致；runner 完整性未变化。

每候选 ledger 显示候选容器 `removed=true`、`rm:ok`。候选 `.log` 另有 manager 收尾原件：七次均 grader created 1 / removed 1、containers_open/supply_open 空、cleanup_failures 空、无 halted/aborted/regrade。这同时核了候选与 grader 的生命周期，不只引用包装器最终 0。

## 私有行为与嵌套 case

私有原件为 `R/mypy-private-controls-r3-20261002T173657Z-cdd6d3/`。spec SHA 与 `P/*/private/cpu_private_diagnostic_spec_v1.json` 原件相同：10174 `6eb23a31e667167079f0ad60ac6eba5107453c75ce0ea01a8701b0ac4acea79b`，15184 `71aa5d756f484d7cfef07994f237266bffafbf99da36b2e1ce476692cabdfa48`。summary、collect.out、case.out、identity.out、initial.txt、prep 输出分别核对；输出字节数全匹配，无截断。

这些容器实际是 root，使用 `--network none`、2 CPU/4 GiB、精确 image ID；它们只证明行为，不证明 actor 权限。每个 patch 的 `--check` 和 apply rc 单独为 0；源码分别来自 `/testbed/mypy/messages.py` 与 `/testbed/mypy/checkexpr.py`，解释器为 testbed conda。全部 7 个 variant 的 rm/query rc 0、remaining 空。

10174 单个新增 case collect 1/5138，base/gold PASSED，bad FAILED；bad 日志明确是“不重叠比较的预期诊断消失”，不是环境异常。节点为 `mypy/test/testcheck.py::TypeCheckSuite::testStrictEqualityWithFixedLengthTupleInCheckWithoutStrictOptional`。

15184 private `-k 'testAssertType'` 选出 **五项**：`testAssertType`、`testAssertTypeGeneric`、两种 unchecked function、`testAssertTypeNoPromoteUnion`。base/gold/top_only 五项全 PASSED；bad 的 `testAssertType`、Generic、NoPromoteUnion FAILED，两种 unchecked PASSED。bad 的有效 int/int、Literal/Literal 和 Gen/Gen 均真实多出错误。拟新增正式 P2P 只登记 `testAssertType`，不把其余四项自动计为评分参考。

私有 nominal/generic 命令均是直接 mypy 退出码 **1**：base nominal 是 C/C、generic 是 list[C]/list[C]；gold/bad 是 a.C/b.C 和 list[a.C]/list[b.C]；top_only nominal 已限定、generic 仍不限定。普通源码运行与 pytest fixture 的 list/List 展示格式不同，应按各自原件解释。

嵌套原件：`R/mypy15184-nested-r1-20261002T175423Z-e27fcb/attempt/` 与 `R/mypy15184-nested-r2-20261002T175739Z-090d84/attempt/`。spec SHA 分别为 `160f783e…0d0a6` 与 `79e566fe…1b3aabb`，与包内原 spec 原字节一致。有效第二版 test patch SHA `e6d5eb0ef39aeeb08a945d3ce6aeb340a7f8b4fd56e599247dbef3b99bf4e532`，上传核字节回执同值。

| 嵌套版本 | base | gold | bad | top_only | 用途 |
| --- | --- | --- | --- | --- | --- |
| r1，小写 list 期望 | FAILED | FAILED | FAILED | FAILED | 保留失败尝试，不能验收 |
| r2，suite 实际 List 期望 | FAILED | PASSED | PASSED | FAILED | 区分内部名字消歧；还需正向 P2P 拒绝 bad |

每个 variant collect 单个 `check-assert-type-fail.test::testAssertTypeFailNestedNominalTypes`，1/6373；四者在两版均 patch 成功、真实执行，无跳过或缺席，rm/query 0、remaining 空。对 v1/v2 effective patch 做直接文本差异，只新增 case 的那行诊断 `list→List`；原三 case 连同 fixtures 未变。本报告不替代材料审查对公开 suite 依据的评估。

## 真实 CC actor 与生命周期

原件入口 `R/mypy-actor-r1-20261002T180207Z-3a9dcf/attempt/`，逐题读取 `attempt.json`、prelaunch/activation JSON、captures、原始 `harness/trajectory.jsonl`、bringup CC 版本、stub/script/计数、post-run facts。worker 的运行与 package 上传 hash 对齐，公开命令 JSON SHA 分别为 `cd32d407…249ad57`、`fcc47ed7…92b94`。

原始轨迹各有 5 个 Bash tool_use、5 个 tool_result、6 次 message_start、1 个 success result；stub 请求数各为 6。轨迹真实字节数是 27964 / 28783，与 host harness_log 和文件一致；stderr 均空、log_complete true。命令 wrapper 在 mypy/pytest 后立即保存 rc，然后裁剪输出，未用 tail/grep 的 0 覆盖目标返回码。

| 命令 | 10174 原件 | 15184 原件 |
| --- | --- | --- |
| identity | rc 0；UID 54321；testbed python；`/testbed/mypy/__init__.py` | 同样 rc 0、正确身份和源码 |
| public_repro | rc 1；Optional[Any] 的不重叠误报 | rc 1；C/C 不可读诊断 |
| public_collect | rc 0；现有 `testStrictEqualityWithFixedLengthTupleInCheck` 一项 | rc 0；六项，含 `check-selftype.test::testTypingSelfAssertType` |
| public_regression | rc 0；1 passed | rc 0；6 passed |
| tree | rc 0；base HEAD，已有 requirements dirty | rc 0；base HEAD，干净 |

每份 captures 字节数与 command `output_bytes` 相同，且远低于 200000 裁剪上限；两题分别 317/177/112/141/66 和 310/113/603/141/41 字节。15184 actor 的 `-k 'AssertType'` 含 Self，和 private 的小写前缀 `-k 'testAssertType'` 选出的五项不同；不能把两组测试或原三参考相加作为新正式参考数。

prelaunch 原件表明 cap effective/permitted 为 0，no-new-privileges 1，UID/GID 54321，actual nano_cpus 2000000000、memory 4294967296；binds/mounts 空，仅 tmpfs home/tmp。派生 image 与上表逐题一致。激活文件 root:644，prelaunch `ACTIVATION_WRITE=DENIED`；activation_check 指向 `/opt/miniconda3/envs/testbed/bin/python`、正确 sys.prefix、CONDA_DEFAULT_ENV=testbed。actual CC `2.1.205 (Claude Code)`，tarball SHA `d3dadfa9cde294ac82c755eb6d889291228849180bac5d677ad1a4027aca1bc4`。

post-run agent procs 0；10174 dirty 只保留初态 requirements；15184 git status lines 0。新 cache/pyc 文件存在（103/110），属于命令实际执行副产物，不把它们说成没有写文件。清理原件两题均 container_rm 0、network_failures/relay_failures 空、stub_rc 0、labeled containers/networks 空；继承 cleanup 后再查 `residual_after_force=[]`。

实际 owner 与顺序：CPU 槽监督 worker → worker 顺序跑两题/候选；formal CLI 在一个 asyncio loop 内顺序调用 ReplayGrader。候选容器以 agent 应用补丁、冻结源码差异并清理，然后新的 grader 容器以 UID 54322 安装、执行受保护测试、解析、finally 收尾。私有 runner 每次一只 root 容器，逐 variant finally rm/query。actor worker 每题一只 rollout 容器和自己的 network/relay/stub，经 `DevRunner → acceptance_startup_2.Runner → ClaudeCodeDriver.run`，命令经真实 CC 工具调度，随后清理后才开始下一题。这里没有训练 owner 或后台训练消费。

## 10174 第六版新正式矩阵：增量独立核查

已核 `R/mypy10174_swe8_binding_final_v1.json` 与第六版冻结 `s2/ingest_mypy10174_swe8_v1/` JSONL/registry：public digest 仍 `e1cc57ae…f8b9e41c`；grading digest `b24e783218afdcf37c4717cf2702ad195e999e120683483269ac94de10802255`；environment digest `a79297ff3b78edb32dde4c39a1bb698e4bd4f4fae43590bf17359176f151651d`；effective test SHA `91ea4e972129deaf770ef9e72aa26d11d9bafca85229eae6931f2b22568322cf`。registry 为 `mypy10174-strict-equality-v1`，parent grading `d2108a22…ef012bb`，原 F2P1/P2P2 保留并新增 P2P1，合计四参考；版本仍 0.820 的无 `.test` 节点形状。

随后取得并只核新增正式运行 `R/mypy10174-revised-r3-20261002T182535Z-f641d8/`（含 attempt/、slot/、launch/）。原 archive SHA256 直接计算为 `fdf053f08922562526074eacb659d5132b017b167e1a49d9f0c3ed45a9e7e955`；45 个 archive 文件与取回目录逐字节相同。以下结论来自此原件，不来自作者奖励回读。

**运行身份。** slot 原件显示 runtime_cpu_v2、worker `revised_matrix-36012e6ed7df.py`、第六版 binding；该 worker SHA `36012e6ed7df118eef092ed0d57d4a8b453fc854963b474acd9ecaccc68cd6a0` 与包内源码、上传核字节回执相同。运行 binding SHA `e00b74789c7b7588a17e3f1d4d06bd87ff03db7d26588c55558de7b9cf8a9c02` 与本地 final binding 相同。`verify_release.log` 实际核第六版 855 文件、trusted 48/216；`material_identity.log` 实际通过冻结 loader 得到相同 public/grading digest 和四参考，worker 还核 effective test SHA 和候选 patch SHA。driver/slot 均 0；这些退出码仅证明编排完成。

**正式准备与材料身份。** 直接核 `attempt/prepared/prepared_manifest.json` SHA `54ddb36d25290e1daa12a0dfc8e5f58e71ce3b6c3ce8af9f14ca0c5831aa0ffe`，其引用的 prompts/rollout view 文件 SHA 均相同；`private/host_grading_views.jsonl` SHA `a9e4d375a3f127a53944f92b4badb48d9a1834e5bd455ac36ff8416ea61f5ea8` 与 prepare/replay summary/manifest 相同。重新 canonical hash public 与 private grading，分别得到前述 `e1cc57ae…` / `b24e7832…`；test patch SHA 为 `91ea4e97…`。公开 bundle 与原 bundle 全字段相同，新公开 prompt 未包含新增私有 case、负候选/gold 路径或评分参考字段。

三个 ledger 和 diagnostics 均绑定 `mypy10174-strict-equality-v1`、registry SHA `a49edd0750cd45c880344bdda762bd757d8bdfddd09689c69cf2e46e316e3cf6`、原 parent grading 和新 environment/public/grading digest；materials identity 为 `dca86b80c83f2e2e9c4eee8c4375952adef834008ad4cb7006ac60abeca58065`。按冻结 `material_revision.py` 定义，以 grading digest / parser version / binding_version(null) 重新 canonical hash，三次均得到相同值。`grading_revision.state=parsed`、apply_ok true；不是旧空 revision 记录。

**逐参考执行与解析。** 真实命令为 `pytest -n0 -rA -k "testOverlappingAnyTypeWithoutStrictOptional or testStrictEqualityWithFixedLengthTupleInCheckWithoutStrictOptional or testUnimportedHintAny"`。`testUnimportedHintAny` 子串会同时选择 Any/AnyLower；每次实际 4/9423 selected，只有下面四个参考，没有额外被当成评分参考的节点。节点均不含 `.test` 层。

| 正式参考（前缀同 10174 原矩阵） | noop | gold | bad |
| --- | --- | --- | --- |
| 原 F2P `testOverlappingAnyTypeWithoutStrictOptional` | FAILED | PASSED | PASSED |
| 原 P2P `testUnimportedHintAnyLower` | PASSED | PASSED | PASSED |
| 原 P2P `testUnimportedHintAny` | PASSED | PASSED | PASSED |
| 新 P2P `testStrictEqualityWithFixedLengthTupleInCheckWithoutStrictOptional` | PASSED | PASSED | FAILED |
| pytest / test rc | 1 | 0 | 1 |
| reward | 0 | 1 | 0 |

原日志短摘要在 noop 529–532 行、gold 541–544、bad 544–547 行逐个标明真实 PASSED/FAILED；parser num_parsed_tests=4、outside_segment=0、reference_missing/skipped 空；三个 revision partitions 的 missing/skipped/unaccounted 均空，结果逐参考与原日志一致。F2P1/P2P3，bad p2p_fail=1；bad eval.log 536–541 行 Expected 是 int/str 不重叠诊断，Actual 为空。因此拒绝针对真实漏诊断，不是未执行或基础设施故障。gold 四项均 PASSED，没有 XFAIL/XPASS/skip 混成通过。

**安装、源码、保护和清理。** 三份日志安装段均真实运行 requirements、editable mypy、pytest/xdist；逐步输出分别 32/6/11 条已满足信息，editable 都明确安装 `mypy-0.820+dev.c8bae…dirty`；无 `ERROR:` 和真实失败 ERR 标记、段末 0、segment 完整，test rc 如表。日志 SHA 各与 ledger 相同、log_partial false。三者实际 import 都来自 `/testbed/mypy/__init__.py`，runner 前后 SHA 都为 `2f4655b6…`，未变化；版本观测 `?` 的限制仍保留。

trusted setup 实际核原测试文件 base SHA `faf0a2a1512eba689901ec6a4df57bc1be9183d2616f6846c8dc9ada181884ec`，restore/apply rc 0、setup OK 1；missing/irregular 0，protection OK 1、test file 1、protected dirs 3、writable prefix完整。grade profile 是 UID54322、2CPU/4GiB、deny_all，与原安装诊断相同。三份 baseline manifest 都是精确派生 image `9d63f1dd…` 和 base HEAD `c8bae069…`，gold 导出只改 meet.py，bad 只改 checkexpr.py；候选 patch SHA 与绑定一致，projectable、无测试或 fixture 变更。

候选容器均 `removed=true/rm:ok`；各候选 `.log` 的 manager_close 均 created1/removed1、open/supply/cleanup_failures 空，无 halted/aborted/regrade。故三次 candidate 与三次 grader 都清理完成。新的 scripts_digest 为 `f111e77dbc1a70b7d469cdb656034aa59c701e9ead3b2ef31e7fa0bd3a45d4ed`，反映新测试材料生成脚本，不能沿用旧矩阵的脚本身份。

**普通 GPU 观察的限定结论。** 从本角色执行证据看，10174 已具备按本次第六版绑定进入普通 GPU 观察的 CPU 证据，未发现新的执行阻塞；主审合并材料/语义核查后可沿已有授权提交统一探针。需要携带第六版 immutable release、public/grading/effective test/revision/materials identity 和精确 image ID；公开 solver 输入沿上述 public bundle，私有测试、gold、负候选留在评分/审计面。此次变化只增私有 P2P，public 和镜像未变；第五/第六版的 devcheck、acceptance_startup_2、bringup、sandbox profile、Git sanitize、prepared_tasks 文件 SHA 相同，可复用这里核过的 actor 五项命令范围。bundles/材料 loader 在第六版有改动，已由本次实际 loader/prepare/grade 证据补核，不能概括为整个 release 无变化。

这项结论不等于 GPU 已运行、模型能解题、题目修复完成、全面隔离资格或训练/留出准入；`env_qualification=absent` 和 activation 写入标记未在 CC 清单里测试的限制仍在。实际 GPU 若换 release/镜像/actor 条件，须按改变的身份补证据，不自动继承本报告。

## 审查适用性和停止条件

A/D/E/F/G/H/M/N 在本范围适用：证据身份、候选真实执行、原参考状态、版本与运行关系、源码/入口、唯一原件、失败分类、外部 CLI 版本均已聚焦核查。B 仅确认既有 reward 与错误行为的实际差异；新增评分准则由材料/语义审查裁决。C/I 通过未完成项与资格边界说明。J/K 无共享代码变更，不给代码重构建议。L 只核本批资源与顺序，不作吞吐/最坏情况推断。

停止条件已满足：已有证据及第六版 10174 三候选四参考完整原件已核足；本角色在此停止，不扩全系统、不追加重跑、不把未知判通过。15184 新正式矩阵和实际 solver 新题面交付由主审登记为后续资格条件。
