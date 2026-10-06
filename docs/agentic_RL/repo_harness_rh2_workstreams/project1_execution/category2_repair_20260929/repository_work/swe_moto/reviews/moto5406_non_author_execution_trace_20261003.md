# Moto5406 固定 CPU 交付：非作者 Production Tracer

依据日期：2026-10-03。审查角色：本批非作者 Production Tracer。结论范围仅为本题固定 CPU 交付能否提交已有版本化 GPU 基座诊断流程。

**本轮原件追踪未发现该范围内的阻断。** 三控制候选、真实 Claude Code 公开操作及原 actor FrozenPatch 的 fresh grade，具有连续且可核对的固定身份；实际结果分别为 `0 / 1 / 0` 和 actor `0`。此结论不是基座模型成绩，也不是训练或留出资格。真实 CC 的输出来自四步直连桩，模型探针次数为 0。

本报告读取公开、私有、gold、作者导航及已保存运行原件，不是 fresh 公开读者审查。遵循根 AGENTS 和审查标准 §10.4/§10.5：仅本地只读及 Python stdlib 离线重算；没有 SSH、Docker、安装、项目测试或模型调用。没有修改代码、材料、原作业或任务卡。独立重算脚本及逐参考摘要在 `runs/category2_repair_20260929/moto_cpu_20261003/non_author_trace_20261003/`；作者 `owner_readback` 仅核指针 SHA，不作为独立结论证据。

## 固定版本与归档身份

请求为 `moto5406_cpu_actor_review_request_20261003.json`。请求绑定的交付报告、三个 owner readback、工具清单、材料清单及公开开发说明的 SHA 均与当前原件相同。没有复审先前已独立核过的材料语义、公开读者、consumer/tools 增量或公共 Git 机制；本轮仅核精确版本及实际调用。

- 实际 release：`cat2-cpu-r2e078079-swe7-git-20261003-v1`；外部 manifest SHA `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`。其本地封板 `manifest.json` 及 837 件代码/数据文件逐项 SHA、长度匹配。
- 工具 v3 manifest SHA：`09f7b6de626c00fba904137b763c8c4c66777cbe1551fbd41812dbce46d2c86c`；9 件附件逐项匹配。运行 recordmanifest 中的 `replay_acceptance.py`、`actor_acceptance.py`、`actor_to_grader.py`、`common.py` SHA 与该工具版本相同。
- 材料 manifest SHA：`d5ca5786f42ef1a25463b28e89ba101a7e2062229294fc3e143fe22459f5fb83`；105 件冻结来源和 6 件生成材料共 111 件逐项匹配。
- 三阶段 job command/输入核对记录都指向该 release；矩阵与 actor 的 producer SHA 为 `84e82a8219c215ce5f8711bbd7e3306d4af6217dc9c809ee1dc436bcc52352fd`。fresh grade 的 origin/execution release SHA 相同，且消费原 actor manifest，未重新 prepare 或重新制造 candidate。

| 阶段／原 job | 清单原件数 | 运输 manifest SHA | job exit |
| --- | ---: | --- | ---: |
| 矩阵 `moto5406-cpu-3e222da9e511` | 410 | `f0971033bbdbe2d0c588ca584c929629e3f86743a16f7bb315215e981963c6ec` | 0 |
| actor `moto5406-actor-6cd339dc49b2` | 37 | `8403f4718088821687857a8b36f23a368121530f3fdbd5a41ce2fa7c21642e56` | 0 |
| fresh grade `moto5406-a2g-386b9ed209c1` | 100 | `f8f9e4bbb63e63678a846ff2b4bac7cb7a8b0a38725af8e54a393d716a4f911b` | 0 |

这里的 547 件为三清单中的 `files` 成员总和；另有各自 transport manifest 本身，因此三 tar 的 regular-file 成员分别为 411／38／101。本轮独立重算全部 547 件本地原件、对应 tar 成员的 SHA／长度，以及三个 tar 的外层 SHA／长度，均匹配 receipt；不是照抄 receipt 的布尔值。

## 实际 prepare → 控制候选 → 评分

原件根为 `runs/category2_repair_20260929/moto_cpu_20261003/moto5406-cpu-3e222da9e511_evidence/`。`job/status.json` 实际命令带 `--execute`，调用 v3 `replay_acceptance.py`；工具调用 `prepare_for_replay` → `PreparedTaskFace`/host view，同次核 actor/replay spec 相等。`prepared/replay_summary.json` 指向的 prepared manifest、prompts、rollout views、private host grading 的 SHA 均经本轮重算匹配。

公开身份为 `sha256:1b128b3d708c1a29956bf4e846b81248ec77bd4ecd710f83b9f7a3ab6ca1e39e`；环境身份为 `sha256:2750caacc4c7dd242b0681bb787aac3a4c392a1e6f53e6354a8f183411207dcd`；评分身份为 `sha256:c50ae6995399541699c041b82e91e55b08a7236e14d820b64c1ddad106687032`。原 base commit 为 `87683a786f0d3a0280c92ea01fecce8a3dd4b0fd`。

v3 顺序执行 noop、gold、constant_east2，每次调用 `ReplayGrader.replay_one`：原镜像 materialize → Git sanitize/可信初始化 → baseline census →（非 noop）`git apply --check` 和 apply → export FrozenPatch → classify/projection → 持久化和释放候选容器 → `SWEGradingManager.grade(workspace=None, frozen_delta=source)`。manager 进入 fresh 镜像/clean checkout、exact baseline rebuild、冻结增量应用、恢复原测试并应用正式 test patch、保护测试、以 grader 用户安装/测试、官方 parser、报告及容器 finally 清理。

三候选的 baseline digest 均为 `sha256:743774379d1fca2bb95a9a4b3f1888fc5c4923c9a64a098745f1b92c0450a46f`。noop 无 entry；gold、constant_east2 均只有 `moto/dynamodb/models/__init__.py`。本轮解码 entry 内容重算 SHA，分别为 `2fd7febd19be90e561f79b324508cc934b05922fc32c8daab7f5097d25234b5c`、`4bd4d6450546ba4a497c938023bea94b7bd81c774e089c0a0db690c461c66253`，与 grader 实际导入该路径的观察相符。noop 实际导入基线 SHA `87a558769bc0786464aeaca26fc29217c718971f447d6ddfc4ced9a3977d4f23`。

| 实际候选 | 原 East2 F2P（1 条） | 原 P2P（26 条） | 新 East1 P2P（1 条） | pytest exit／reward |
| --- | --- | --- | --- | --- |
| noop | FAILED | 26 PASSED | PASSED | 1／0 |
| gold | PASSED | 26 PASSED | PASSED | 0／1 |
| constant_east2 | PASSED | 26 PASSED | FAILED | 1／0 |

独立解析三份全文 `.eval.log` 的 `-rA` 逐节点状态，集合与原 diagnostics 的三个参考分区完全相等：每份 28 条、没有额外节点、missing、skipped 或 collection error；全文 SHA／长度与 report 引用相符。constant_east2 的完整断言中实际 ARN 为 East2、期望 East1，两侧均为 `table/messages`，故失败直接来自地区错误。gold 完整通过 28 条，新增节点没有误拒该正确修复。

正式安装入口仍为 `make init`；三份全文有实际安装 `RH2_INSTALL_RC=0`、测试结束和 RC 标记，diagnostics 中 `install_failed_commands=[]`、`candidate_segment_completed=true`、`log_partial=false`。shell 执行 exit 为 0，而失败候选内部 pytest exit 为 1；报告把它们归为 `tests_failed`，没有混为 infra failure。trusted setup 明确恢复两份测试、apply RC 0；`RH2_PROTECT_OK=1`。补充原件中的两测试均 root-owned、不可写，SHA 分别为 `d612bbf8e1eaa92109f63c85b4c704dcaa76350e31ca1c76c22145f8342cc456` 和 `a0543ad19335b4d87b717263e797055ab9876481d469808554be9ec1d6ca6292`。辅助题面示例 pytest 在 `rf_examples/` 单独保存，不在正式 28 节点 reward 内。

## 真实 CC、静止屏障与原工件 fresh grade

actor 根为 `moto5406-actor-6cd339dc49b2_evidence/output/`。轨迹实际初始化为 CC `2.1.205`、cwd `/testbed`、模型名 `slime-actor`，有 4 个 assistant 回合及正常 result。四个 stub request 与四步 stub script 相符；三条 `Bash` 的实际 input 与 stub script **逐字相同**，对应 tool_use/tool_result ID 一致。tool result 分别为 `public_identity rc=0`、`public_example rc=1`、`public_existing_tests rc=0`。完整 capture 的 SHA／字节数与原记录相同，未截断。

本轮从首个真实 request 独立抽取 user text，与同次 prepared prompt 逐字相等，SHA `03414c3f4ad5a7ec28d8b5e4989a3552ac13a33a68b7dcac2ca25b59d677baf2`。公开复现完整收集 1 条 pytest，失败为 `test_table` 的实际 East1／期望 East2；公开已有 East1 建表节点完整通过 1 条。identity 原 capture 确认 UID 54321、testbed conda Python 和 `/testbed/moto/` 基线导入，控制路径 root-owned 且不可写。这个过程没有基座推理：桩决定命令，真实 CC 执行命令。

actor 的 `quiescence.json` 为 `QuiescenceConfirmed`：kill 后 residual 0，无超时，workspace 双读稳定；其明确限定的 session scope 是直连桩和唯一 relay 关闭，不是训练 capture/session drain receipt。实际 runner 顺序为关闭消息源 → 生产 `DockerQuiescenceBarrier.establish` → export → durable 保存 `frozen_patch.json` → `rm -f` actor → 只读绑定核对。原 attempt 的释放 RC 0，cleanup 无 errors，空容器/网络查询，assignment 已释放；旧 assignment 再解析得到 `AttemptAssignmentError`。actor 没有完整 Docker call 逐调用运输，生命周期事实来自原 runner 的 quiescence/attempt/container inspect/trajectory 原件，本轮没有独立远端观察。

原 actor FrozenPatch 文件 SHA `34ca1b7abfcdea7d61d8bbf673e3dfe60276ff6d3cf50b89fdcd2af230995869`；baseline 文件 SHA `613703e30492753f3a7b458fc2c27fe15e81e2c41ff16806c656e2235c9a08fd`；本轮 stdlib 重算 FrozenPatch canonical digest 为 `sha256:6db18cb77ebdf6fb1ef0852e4bfb73ff28388126fb3f276fc0edd2635fa6ee58`。entry 和 projection 路径都为空；dispatch、frozen_material_join、fresh grade input_check 的 assignment 相等，physical attempt `miles_g0_m0#p1-c34887ab` 与 artifact 相符。

fresh grade 根为 `moto5406-a2g-386b9ed209c1_evidence/output/`。原 `input_check.json` 的 33 件 actor 工件、actor recordmanifest SHA `2de05ad295fee56d1968e5b29a49191e53a61aa4a6015d4d2c51b0bb199e07f9`、三件 CPU spec/profile/summary均独立重算相同。实际代码 `load_inputs` 重读原件，构造 `FrozenDeltaSource`；`execute` 只调用一次 manager grade，参数 `workspace=None`，没有新 baseline、新 candidate 或旧 registry 复活。原 status 为 baseline rebuild passed，grade_invocations 1。

fresh 正式日志 SHA `f6a99346d702eb0607708311e9d2aa8ba65e36a553c9e56f321a4fa1c1d0e0a5`、55,815 bytes，经本轮重算相符。逐节点 28 条与参考分区完全相等：F2P 0／1，原 P2P 26／26、新 P2P 1／1，reward 0；唯一失败为原 East2 建表 ARN。安装、恢复/保护、基线源码观察均完整，非 infra failure。

## 并发、资源、异常与历史边界

矩阵三个控制候选顺序执行，原 raw Docker calls 确认每个候选容器移除后才启动对应 grader；每个 grader 移除后才进入下一候选，未观察到同题候选/grader叠加。grader 共创建并移除 3 个；fresh grade 创建并移除 1 个，没有 regrade。raw calls 的四个 grader 都是 network none，2 CPU、4 GiB、PID 512、共享内存 64 MiB。峰值分别 782.727／784.402／763.953／768.215 MiB；未经历 timeout、OOM 或 cleanup failure。actor inspect 同样为 2 CPU、4 GiB、PID 512、64 MiB，使用单独 relay 网络且无 bind mount。没有据此估计 GPU 阶段或大规模并发成本。

矩阵 raw calls `0013/0035`、`0048/0070`、`0083/0105` 分别确认候选/grader移除；`0106/0107` 查询本 run 容器和网络为空。fresh grade `0026` 移除 grader，`0027/0028` 查询为空。manager close 没有开放容器、supply 或 cleanup failure。异常传播在固定代码中保持 run-fatal：baseline mismatch 从 manager 经 ReplayGrader 重抛；外层 finally 保存原失败与清理。正常 pytest failure产生二值 0，不被替换成 missing/rejected。

原 R3 失败 `moto5406-cpu-74541fbf7460` 单独保留 104 件原件，tar 外层 SHA `ec9f65ed0f989a4164e9bb59c2473ff239c29d78acc40649d0ea9c5bb4a2814c` 及内部成员经本轮重算匹配。其实际 code manifest 是 `40ca2914da2be665754175954defe4bbecfdb31efc1ad394153c09acfb5f9f15`（`cat2-cpu-r2e069-swe6-20261003-v1`），工具 common SHA `de8915641c7feaeb7d8af62435aee5e02ecf9e7f21d347d1af85c3d5f0ef1549`；新 R5 common SHA为 `3bedde899b4b6968099040129061debaef6ef2a281c599e773b6fcd702ea3547`。R3 noop FrozenPatch 文件 SHA `4a6027c9e8206b605490759ae71112dbf9dcec0c2e7e9568a3fce19b0c81458b`，baseline digest `sha256:206ea7686514f2171b28470daa7f3b432dc8bc0127f750c4f5e1451bee31a6d1`，fresh rebuild 为 `sha256:cbad706e0aaa2cecfcce0f142c8a603ee8776ed4148cff3f5b6740691881808e`。原 ledger 为 `baseline_integrity:baseline_digest_mismatch`、report null、rows 空，job exit 1；旧 grader/candidate 已清理。它不是 reward 0，也不是新 R5 已成功的旧工件。新 R5 另有 physical attempt、baseline和 FrozenPatch，未回写或重绑 R3。

## 处置与停止条件

事实：固定 R5 CPU 切片的调用链、冻结身份、安装/逐参考评分和清理证据足够；原 R3 run-fatal 保持历史事实。本轮没有需要修复的当前生产阻断 finding。

选项与推荐：将这个固定版本及三阶段原件提交已有版本化 GPU 基座诊断流程；无需重跑本轮 CPU。理由是本轮限定的 CPU 前置链已经真实执行且原件身份闭合，继续穷举未计划能力不改变该判断。代价是进入下一诊断切片的既定 GPU 成本，不由本报告新增预算或审批。

仍未知／未覆盖：基座模型是否会修好本题、GPU与训练 adapter/capture 的实际表现、异常注入下的 timeout/取消/OOM/清理失败路径、大规模并发吞吐。上述不是本轮 CPU 交付的新增门槛，按已有诊断流程获取；训练或留出资格仍未授予。完成一轮固定原件追踪即停止，不以“还能构造反例”延长审查。
