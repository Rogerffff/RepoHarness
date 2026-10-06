# mypy15184 R10 正式 CPU 增量：非作者 Production Tracer

日期：2026-10-03。角色：按 `review-standards.md` §10.4 的 Production Tracer，追踪实际调用链、生命周期与异常传播。已见作者索引、公开题面、gold 和私有对照；不是 fresh 公开读题审查。

## 结论与适用范围

在本次冻结版本与四候选范围内，未发现实质 finding。独立回读原始 attempt、slot、launch 和归档后，正式五参考得到 `noop/gold/bad/top_only = 0/1/0/0`；每个候选均实际 collection、执行并解析精确五条参考，没有缺席、跳过或额外节点。两个新参考分别拒绝「所有有效断言也报错」和「只处理顶层同名类型」对照；gold 没有误拒。

本题 R10 正式 CPU 评分增量条件已满足，可以停止这个边界的复核，交主审与既有 actor 验收合并判断普通 GPU intake。**本报告不授予训练、留出或完整隔离资格。新版实际 CC solver 首条题面交付仍没有本作业证据**，须在下一切片核实际请求；不能把静态 prepared 或旧控制 prompt 当成已经交付。

只审 `python__mypy-15184` 新正式版本，不重审 10174、旧正式矩阵、旧私有行为矩阵或 fresh 读题。全过程只读原件、做本地哈希与文本/JSON 对账；没有 SSH、Docker、测试、模型调用，也没有执行受信 loader。唯一写入为本报告。`revised_cpu_readback_20261003.json` 只用作导航；结论取自下列原件与冻结源码。

## 原件与版本绑定

- 作业根：`runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/`。下文 `attempt/`、`slot/`、`launch/` 均相对此根。
- 归档：同级 `mypy15184-revised-r1-20261002T214419Z-e743aa.evidence.tgz`。独立用内存读取 tar 成员；55 个常规文件与本地根精确同集、同字节，无遗漏、额外文件或哈希差异。
- binding：同级 `mypy15184_r10_binding_v1.json`；其完整 JSON 与原始 `attempt/revised_matrix.json.binding` 相同，字节 SHA 与后者记录相同。
- R10 冻结源：`runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe14_preflight_v1/`；release ID 为 `cat2-cpu-r2e089092-swe14-preflight-20261003-v1`。独立核 manifest 950 个文件的普通文件形态、SHA、size 及精确集合，全符。
- 发布 receipt 与部署 receipt 的字节 SHA 与 binding、publication 索引一致；实际作业 `verify_release.log` 记录同一 release、950 文件及受信读回成功。部署服务器的实时文件状态未重新读取；这部分证据是已取回的部署回执和作业 verifier 原始输出。

| 绑定项 | 本次有效值 |
| --- | --- |
| public | `sha256:77b85678b3f20ef5689e4a9b646518ae1247407ff44b250803563c11dce3ea7e` |
| grading | `sha256:3a3c4e78c7dc1b1dce9187d36d00079c4d08621f7019140e6544e77b9f2db4bf` |
| environment | `sha256:de06cc63c20f88a4691b7037dfeaeae5f31c4dc13f09cf703161cf6df2954f1e` |
| revision | `mypy15184-nested-nominal-types-v2` |
| revision registry | `sha256:7abfdf350875e5d28c679ac196f20c8a44efdce184fa7be00ddf97cb2009740c` |
| parent grading | `sha256:4d06500507c04fe8fe2843025d01f53ea8b6854f9fc72e1656bf7781b7da9b18` |
| effective test patch | `sha256:e6d5eb0ef39aeeb08a945d3ce6aeb340a7f8b4fd56e599247dbef3b99bf4e532` |
| immutable base / 实际 HEAD | `13f35ad0915e70c2c299e2eb308968c86117132d` |
| 派生镜像实际 ID | `sha256:76b5b2646a9eb134e6349ee8e214bb84eb6030c34a234e167351acdec5dd8c54` |
| 原镜像 manifest digest | `sha256:affb925329f2dfb2173482c64a1b65648b250777b66b0d7417ee5340fce74835` |
| grading materials identity | `sha256:bf000616fc92f2d7869bdb2039ab1fe0d9167e507a5bb15e6c5987ab033d8053` |
| grading scripts digest | `sha256:eb6990fb1a94e807ee047e7e36029d27f37411fb590c4a36a33e42a6d8a68364` |

原镜像 manifest digest 与本地派生 image ID 是不同身份字段，不能要求二者相等。四 ledger 都记录本地构建身份、精确实际 ID、配方 `mypy-install-wave1-copy-wheels-20261003`。本次只追溯已有镜像准备原件的 ID、base 层保留与 COPY-wheel 配方身份，不重复镜像构建验收。

## 实际 CLI 到评分的链

1. `launch/py` 经 `cpu_slot.py --mode run --package swe_mypy` 启动 `runtime_cpu_v2/rh2/.venv/bin/python -B` 与 `revised_matrix-36012e6ed7df.py`。`slot/status.json` 为 slot 0，child 从 2026-10-02 21:44:25 UTC 至 21:55:18 UTC，状态 finished、returncode 0；wrapper receipt 于 21:55:19 UTC 写 rc 0。本地 `revised_matrix.py` 完整 SHA 与远端 worker 文件名的 SHA 前缀匹配；作业归档没有独立的远端 worker 文件，完整远端字节只能由命名约定及原始 command/state 追踪，不能声称另行取回验证了该文件。
2. worker 从 binding 校验 manifest SHA，把 `PYTHONPATH` 指向 R10 冻结 `repo/rh2/src`，按 `verify_release → material_identity → prepare → noop → gold → bad → top_only` 串行执行；原始 state 的七个 step 都 rc 0，没有 interrupted/forced_kill。每候选一次，未重试、未 regrade。
3. `prepare` 调冻结 `scripts/replay_grade.py → prepare_for_replay → TrustedTaskController.from_repo_root → load_trusted_swe_revision_outputs → prepare_tasks`。冻结 loader 验代码 pin、来源/修订单的确定性重放和输出字节；prepare 消费时重验 public/private 关系，并拒绝覆盖已有产物。实际新 prepared 时间为 21:44:38.914483 UTC、task_count 1。原件中 prompt、rollout view、private host grading view 的 SHA 与 manifest/summary 一致。
4. `run` 读取本次 summary，经 `load_context` 校验 prepared manifest、公开文件和私有文件的哈希/身份，随后 `build_grading_spec_from_host_view` 消费 `SWEMypy15184TestPatchRevision`。原 private view 的 effective patch 与冻结 revision 资产逐字相等，新增/原始 F2P/P2P 分区均吻合 binding。实际 `material_identity.log` 与四 diagnostics 绑定同一 public/grading/revision/environment。
5. `ReplayGrader.replay_one` 先开候选容器，核 checkout HEAD，sanitize，再 trusted init、baseline census；以 `agent/54321` 应用 noop 或 `git apply --check/apply`。四个原 `stage.json` 都到 projection、无 stage_error；三个候选 patch 的实际 SHA 等于 binding。投影只包含 gold/top_only 的 `mypy/messages.py`，bad 的 `mypy/checkexpr.py` 与 `mypy/messages.py`；没有测试文件、fixture/conftest、忽略路径或不支持形状。原 grader setup 中的 `git diff <base>` 再次呈现对应源码变更。
6. 先持久化 frozen artifact，并完成候选容器 `rm:ok`，然后才把冻结投影交 `SWEGradingManager.grade(workspace=None, frozen_delta=...)`。四 baseline 原件字节相同，绑定同一 public、runtime image、materialized HEAD/base；FrozenDeltaSource 有对应 baseline manifest digest。baseline 原件的 `environment_package_digest` 为 null，这是该 replay baseline 形态的事实；本次环境身份实际在 prepared/private/spec/diagnostics 中绑定，不能声称 baseline 该字段也非空。
7. grader 重新建立基线并应用冻结源码投影，root 做测试恢复/保护；以 grader candidate UID 54322 安装和执行测试，再交 `parse_eval_log_v2`。评分结果由冻结 F2P/P2P 定义产生，worker 不自定义 reward。

原件 `candidate.kind="cc"` 是 patch 输入枚举，不是本次运行过 CC solver 的证据。这里没有 Claude Code、模型请求或求解 rollout；候选是预置补丁。

## 恢复、保护、安装与实际环境

四份 eval 原日志都显示：先确认 base commit 存在、`git ls-tree` 确认登记新增 `check-assert-type-fail.test` 在 base 缺席，移除工作区同路径文件；从 immutable base 恢复 `test-data/unit/check-expressions.test`，核 SHA `f541a8781c01edf4a27209cc1569e61d1d8a4741c3d4bc381548d0b1239ce3b9`，再 apply 正式 effective patch。各 diagnostics 的 root 自证为 apply_rc 0、restored 1、expected/present 2、absent 0、irregular 空、setup_ok 1。

`prepared_task_face._v2_test_files` 把新增 P2P 所在 baseline 文件加入保护清单；两文件都保护。manager 从 root 属主自证文件取 setup 判据，随后执行控制面保护，而非把候选 diff 中的文字当成功标记。四次 control_surface 均 `RH2_PROTECT_OK=1`、protected_files 2、protected_dirs 6、missing 0、irregular 空，`TESTBED_STAT="0 1777"`，可写前缀配置完成。冻结保护脚本把 official 文件设 root:root 0644、祖先目录设 root:root 1777。这里只验本次实际恢复/保护链，不升级为完整隔离验收。

每候选都实际执行 `python -m pip install -r test-requirements.txt`，之后 `python -m pip install -e .`，安装来源 `file:///testbed`。前者输出各需求 already satisfied；typed_ast/tomli 的 marker 忽略是版本条件分支。后者 build dependencies、editable metadata、editable wheel 和卸载/安装段都 finished/done/success。四次无 `RH2_INSTALL_CMD_FAILED`，install_rc_last_command 0、install_skipped false、candidate_segment_completed true、log_partial false。每条 pip 命令没有独立数值 rc 回执，所以判据是完整输出、ERR trap 无失败记录及段收口的组合，不能只凭安装段末 rc 0。

实际测试头为 Python 3.11.9、pytest 8.3.2、pluggy 1.5.0，rootdir `/testbed`；xdist 3.6.1、forked 1.6.0、cov 5.0.0。安装 mypy 为 `1.4.0+dev.<base>`，三个源码候选带 `.dirty`；post observation 的 `RH2_OBS_PKG_VERSION` 为 `?`，本报告的版本来自实际 pip 输出，不把该未知观测改写成数字。四次 import observation 均 `/testbed/mypy/__init__.py`，与 actual source diff、editable 安装及测试 rootdir 相互印证；这些 observation 由候选身份执行，只是诊断证据。

四 ledger 的正式 grader profile 均 `rh2.grader_sandbox_profile.v1`、digest `sha256:3ec1bfa87ff800d5d2c5e53e874603f6850b64e1392baa167968b9ec31a50a94`：UID 54322、2 CPU、4 GiB、network deny_all、pids 512、shm 64 MiB、tmpfs 1 GiB，可写前缀 `/opt/miniconda3/envs/testbed`。runner digest 前后均 `bffa1d1e04c07d52b4d5db5941f0d97a8c71a68e29cca90c4bf5671ea66e1548`，runner_integrity_changed false。

## 精确五参考：collection、执行与解析

vendor metadata 原前缀仍为 `pytest -n0 -rA -k`。R10 `derive_test_command_for_bundle` 对这个固定 revision 验末尾 ` -k`，移除该未带表达式的选项，再接精确 3F2P/2P2P 的五个完整 nodeid；原日志实际 command 与该命令及 binding 相同。没有用广义 `-k testAssertType` 选开发 case。

以下所有 nodeid 的公共前缀是 `mypy/test/testcheck.py::TypeCheckSuite::`。P 表示原日志 PASSED、解析 success；F 表示原日志 FAILED、解析 failure。

| 分区与 nodeid 后缀 | noop | gold | bad | top_only |
| --- | --- | --- | --- | --- |
| 原 F2P：`check-assert-type-fail.test::testAssertTypeFail1` | F | P | P | P |
| 原 F2P：`check-assert-type-fail.test::testAssertTypeFail2` | F | P | P | P |
| 新 F2P：`check-assert-type-fail.test::testAssertTypeFailNestedNominalTypes` | F | P | P | F |
| 原 P2P：`check-assert-type-fail.test::testAssertTypeFail3` | P | P | P | P |
| 新 P2P：`check-expressions.test::testAssertType` | P | P | F | P |
| 实际 pytest rc | 1 | 0 | 1 | 1 |
| 正式 reward | 0 | 1 | 0 | 0 |

四日志均有 `collected 5 items`；`-rA` 的五条结果 nodeid 精确等于 binding 参考集合、无重复。collection 证据在正式 pytest 会话中，没有另一次独立 `--collect-only` 作业。各原 diagnostics 均 num_parsed_tests 5、outside_segment 0、reference_missing/skipped 空；原/新增四分区的 status 与逐行 pytest 结果相同，unaccounted 空。每行结果都位于实际 Start/End xtrace 标记段内。

原日志核点：noop command/collect 在 455/461 行、逐节点结果 507–511；gold 479/485、491–495；bad 493/499、529–533；top_only 490/496、516–520。bad 在新增 P2P 中产生有效断言错误，top_only 在嵌套 F2P 中仍输出 `List[C]`，不是 collection、安装或 parser 故障。三个 reward0 的 failure_category 均 tests_failed，infra_failure_detail 与 execution_failure_stage 空。

## R10 manager 增量与本题适用性

R10 manager **字节确实不同于 R6**：SHA 从 `b6b10f98bf0e1a7bbe4774ac705ece6bb2746da2b1ac4f20394673293f24bbb0` 变为 `1783533e1e3b66a57fcaa5a599a1da4f8e4e886318e24f040c6df91f294c1c1e`。独立 diff 显示新增 `candidate_prerequisite_script`、record/diagnostics 字段、启用时的脚本摘要域、profile 要求和执行分支；不能复用「manager 字节不变」论据。

本题实际不可达该执行分支。冻结 `prepared_task_face.py:487` 仅在 revision 为 `SWEDVC5839TestPatchRevision` 时填前置脚本；本题是 `SWEMypy15184TestPatchRevision`，spec 的该字段为 None，四原 diagnostics 的 candidate_prerequisite 均 null。`grading_scripts_digest` 仅非 None 时追加新域，所以没有给本题额外摘要材料。manager 条件分支位于保护后、候选观测/安装/测试前，但本次没有执行，不产生 DVC 前置条件拒绝，也没有改变本题安装/测试顺序。本报告只核本题的适用性，不对 DVC 实施结果、取消/超时路径作全审结论。

冻结 CLI、`adapters/slime/replay_grade.py` 和 `envpack/prepared_tasks.py` 相对 R6 字节相同；评分面、revision loader、spec 派生及 manager 按 R10 本次冻结字节核。正式五参考不是旧控制或私有正校准节点计数相加。

## 清理、异常传播与退出

本作业并发基数为一个串行候选；源码顺序是候选容器移除后才建该候选的 grader scope。每行 candidate cleanup `removed=true/steps=["rm:ok"]`。四 CLI 原日志分别记录 manager created_total=1、removed_total=1，containers_open、supply_open、cleanup_failures 空；halted/aborted 空，final_status exit_code 0、reason ok。总计八个本作业容器有正常清理回读（四候选、四 grader）。本作业未启受控供包，supply 为 null；没有另建 relay/stub 或需要释放的供包网络/token。它不能替代旧真实 CC 控制作业的清理证据。

候选超时/异常在 replay 内记 stage_error；取消持久化并收口后原样传播；不能确认候选移除会 ReplayHaltError 停批。baseline 契约错误会走 BaselineIntegrityError 停批；CLI finally 关闭 manager，未关闭 grader scope 会非零退出。worker 遇 CLI 非零立即停止后续候选，异常会保存 stopped_pending_diagnosis；正常运行的这些异常路径未做故障注入。实际四次 stage_error 空、candidate exec rc 0、pytest rc 单独如上，install 与日志完整；**CLI/wrapper rc0 表示正常收口，不表示该候选解题通过**。

## 新题面的证据边界与停止条件

原 `attempt/prepared/rollout_task_views.jsonl` 的题面逐字等于 R10 `effective_statement.txt`，SHA 为 `sha256:c17659095d0b4ab71caf2fab52dfaa52e9da009212381a7dc46053c015499178`；`prompts.jsonl` 包含该完整正文，metadata 绑定新 public/environment。这证明新题面进入这次真实 prepare 的公开产物。它没有证明真实 CC solver 收到同样的首条消息。R10 publication receipt 也明确要求下一步核实际 CC 初始请求；旧控制 prompt 与本次 replay 的 `kind=cc` 均不能补足。

本增量的 stop condition：冻结身份、五节点实际执行/解析、四候选结果、安装/恢复/保护、源码/镜像/profile、正常清理与退出已足以关闭 **15184 R10 正式 CPU 增量**。不为继续设想其他错解而重跑旧矩阵；四候选只覆盖已知缺口，不证明所有错解均被拒绝。

普通 GPU intake 的本题 CPU 前提可以由主审视为已满足。下一切片仍须绑定这份 release/manifest、公私材料与有效镜像，核实际 solver 首条请求和真实模型运行，区分既有控制入口证据与新版本交付。若观察到旧题面/身份漂移、gold reward0、已知 bad/top_only reward1、五参考缺席/跳过/额外节点、安装/恢复/保护失败、源路径或 image/profile 不符、日志截断或未清理 scope，保留原件并停止该切片诊断；不得把 infra failure 当有效错解 reward0。真实 GPU 求解、吞吐、训练消费和完整隔离均仍在本报告范围之外。

## 关键原件 SHA256

下列 SHA 均由本次独立回读计算；相对文件名见上文根目录。

| 原件 | SHA256 |
| --- | --- |
| evidence.tgz | `c7f4f34886a1284f185092fa8a4dd5ac702d0177e0e92240d349c5f2eecaa9e9` |
| binding | `a3d4a085a8d3f28db88f1184025d54018d3874bb95a2b37f9a6ca57495786bef` |
| R10 manifest.json | `00ac5c375629f59543f548fbc7b0cb3cbe7d1418f7a956d9deebcefab2e8a87c` |
| publication receipt | `c2c0cea5c8505339c334f3fa6a30fd4626cc6a50be1b01d6640902350db2e130` |
| deployment receipt | `4f6c3c925582450ab4a91d6534231956c7c15381c873f8d9f6564f692ae48c09` |
| 本地 revised_matrix.py | `36012e6ed7df118eef092ed0d57d4a8b453fc854963b474acd9ecaccc68cd6a0` |
| launch/py | `e8e858f1e15aad4c8990eb24029df5aa69b36f9692b20b813481605d8e3acb8d` |
| launch/receipt.json | `2d1461205e44b7dd48f8cc9a0bee67c295ce6052b5f340b02bc7024455ce876d` |
| slot/status.json | `fc1a0f85ea97eea438ec50445ae1eb0e392b3a150c02408919108fc1a4efae8b` |
| attempt/revised_matrix.json | `5d67a92483f21c4b79ae4a3c0b71b01b9182f202b26823f409ecae8a7a2a3715` |
| prepared/prepared_manifest.json | `5539ba380c92767f20d3760f3611060843da5faca8211c64d8e51fda19a7ac9a` |
| prepared/prompts.jsonl | `9956e3513a8441e5bb45e5dbf1e0cb0c7f2e9ffd601b005a84d65ceb4573c061` |
| prepared/rollout_task_views.jsonl | `f0e8a4d1fb9f1682f879174488ad6301041658c440a62dc66cfbbc61d7da382a` |
| private/host_grading_views.jsonl | `1ce37a96ae9140654e5604cc6f2570345a92928315b99131cb99b0ce6e2946ff` |
| 四候选共同 baseline_manifest.json | `22285ba7545856ab760fbc516a93af635e86bb6cf7865d79055f9e1ddcca34c0` |

| 候选 / eval 引用尾标 | ledger SHA256 | eval log SHA256 | diagnostics SHA256 |
| --- | --- | --- | --- |
| noop / `7256eb23` | `e28712d41e72b6ea9c368004fb1f1f9ec89e67302bec00ce45790bc919c214a9` | `a8cc45338123ecc600a20093f506f5d55f1ef37f6834550f2bb9296e22f28abe` | `3d3488269ac977e7508629859b5ff2764124746af3dca8cb296b49b04ef1527d` |
| gold / `233b3249` | `d8d4b047ffadcc86545ff1b7406937a1403e990ad0420cb6264fd00f78f32df8` | `17e5c4c5c153597c788d185835564d84b505a47fa7169a1af58be052e3aff35e` | `e1774951c210a4c388a4b87d405f69dc199ef16e414728f9bd2338e4150dc9cc` |
| bad / `2ea87688` | `e564ad131d0454dbad3731298bdae724e1606ed30cc3ecd7a701a9add40b1802` | `2520976bb86cb0014fc91d9a8f3b3ffd36c88220718210f8954cd93fcf3fe179` | `baaa34eef39662111c220795edfff31591d5aaf43966e3509de5a9571a2bed36` |
| top_only / `18eeed97` | `abd8d92cefba8d789b4e64d1387a0ab475aaf7658420d492daf010a49bb808cf` | `7e9189f6a48b7817441825e21293d0bfc5f2357361b28bf6ac7f75fe0e822244` | `8666d42da3e8233866f1306edfb9b031bfeaed58326e16135ab64499b1df5b9e` |

关键冻结源码 SHA：CLI `d36fa3367415e573305a7a03619f51e7cbd358627569f3844d5c203b70d66db3`；replay adapter `3bd574eed3da9372b8640eac48d5da0b1141375c21b6e492de822d494443ef66`；prepared_tasks `3b44b28cdb8dece281369cd94ef255a1687a54519415533328c76d15d08ca1fc`；revision loader `df833b33012e8a321ce9c70c87661209045a6d377da59177d37a4720287e0e4f`；manager SHA 见上文 R6/R10 比较。
