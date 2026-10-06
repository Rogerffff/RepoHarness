# Conan14177 Qwen3.6 首次执行与评分运输：非作者独立窄核

日期：2026-10-03。审查角色：非作者；依据当前 `coordination_workflow_20261003.md` 的第⑥步，以及 `review-standards.md` §5、§10.1、§10.5。对象仅为 `gpu1003-conan14177-qwen36-a1`，固定请求 `swe-conan14177-r11-briefv2-20261003-v1`。

**结论：本次执行、评分运输及已保存生命周期证据可接受；未发现具体阻断或新增 P0/P1/P2 finding。** 原评分为 reward=1，F2P 2/2、P2P 11/11 全部通过。独立重算原件身份、基线归档与重建、FrozenPatch 和评分投影，并核当前模型实际 HTTP、完整参考段、退出、清理及 drain。此结论只核运输；候选语义另见 [Qwen 语义独立报告](non_author_14177_qwen36_a1_semantic_review_20261003.md)，训练资格未建立。

审查只读本地原件，以标准库完成 JSON、SHA/大小、tar 和文本内容核对；没有运行项目模块、pytest、CPU/GPU 作业、Docker、模型或远端命令。仅新增本报告与 [独立对账 JSON](non_author_14177_qwen36_a1_execution_review_20261003.json)，不回写共享题卡、总账、冻结证据或题主文件。

## 1. 权威原件、完整性及复用范围

以下别名均为仓库相对路径：

- `B = runs/ordinary_gpu_probe_20261002/`。
- `S = B/closed_snapshots/gpu1003-conan14177-qwen36-a1/`，是本次权威封包。
- `R = S/queue_qwen_first10_v1/results/gpu1003-conan14177-qwen36-a1/`。
- `D = S/diagnostics/QUEUE_QWEN_FIRST10_V1_gpu1003-conan14177-qwen36-a1_before/`。
- `P = S/prepared_conan14177_briefv2_code7_q19_v1/conan14177/`。
- `G = S/services_qwen_code8_v1/qwen36/gateway/first10-v1/gpu1003-conan14177-qwen36-a1/`。

独立逐件读取 closed manifest 的 **137 件、10,757,623 B**，SHA256 与大小全符。manifest 自身为 30,909 B，SHA `83d06378d93b4b285575a13ab06e50611f729c5889ba9e3ef3441af5eaf52137`；其成员计数不含 manifest 自身与外层 sync receipt。同步回执 SHA `6782995f4c0c74fea08c9e2cfeb38ed68c9f1575164d3a2e448f7d25258ccbfd`。

机械回执 `B/migration_20261003/gpu1003-conan14177-qwen36-a1_execution_receipt_v1/execution_receipt.json`（55,717 B，SHA `46402b654d2f010d9c6e25323b6c1fa1bc8ea399d12ce26d1d905d4a37772ab4`）只作导航；下文结论来自原件复对，没有将它的“完整”声明当作验证。

本次固定请求与 `P/host_evidence/owner_request.json` 字节相等，SHA `478ba02b7ead3aabda7a6493694434c350a694c1600e0f71851eabef5d8ffff7`。first10 input manifest 的本题 **22 个材料输入**逐一重算匹配；code8 source manifest 所列 **1,045 件、118,460,058 B**按各自 origin 本地文件逐件 SHA/size 匹配。source manifest SHA `09ddb8bfdeecd3ffaa38c1048a574161ef6fa6053b2855da50166e8e8677899d`。

复用的既有证据明确限于：

| 既有独立报告 | 本次复用的内容 | 本次不由它代替的内容 |
| --- | --- | --- |
| `B/reviews/conan14177_coder_a1_execution_review_v1.json`，SHA `07240bbef092bb44cbdf597c1e841573fd13832e403152df7f01a1499dd17369` | 同固定请求下 Coder 首臂已结束、原参考与生命周期边界 | 当前 Qwen 原件、模型身份、候选、HTTP 或退出 |
| 本目录 `non_author_14177_r11_cpu_runtime_review_20261003.md`，SHA `89d8117ff968aee3c4e9971e366d552942ca399f614f307600708c9d1cde4749` | 相同 R11 材料/consumer 的已验来源与正式链边界 | 不重新验收历史 15 候选矩阵，不把它算成本次动态证据 |
| 本目录 `non_author_14177_r11_cpu_scope_review_20261003.md`，SHA `afc99e9ae96f5684b9a4356ff1689e130018476c0ec53d25e8cd61b8e440a238` | 2F/11P 迁移与 mock 测试的既有接受范围 | 当前候选语义由另一报告独立判断 |

## 2. 固定输入与实际 actor / grader

固定 task 为 `swe_gym_lite::conan-io__conan-14177`；base commit `b43eb83956f053a47cc3897cfdd57b9da13a16e6`。prepared identity、rollout view、host grading view、input check 与实际 attempt 对齐：

| 身份 | 当前值 |
| --- | --- |
| revision | `conan14177-cloud-test-v2-regroup-v1` |
| public bundle | `sha256:05af9bfee3a1a190b43e1bdeb7b473800206bde44c583f5c1144743f3381776a` |
| environment package | `sha256:5a047601494efe2b4c4532ce0f48b74f9a2d72731c815c6fe66ed2a914eef6da` |
| grading bundle | `sha256:5c2724e58c3273ea2fa1ce509b6e2082e5338d45d58642997370e8943f426413` |
| grading materials identity | `sha256:926d6baa95fad4532d8a85387c6fc9dbf0b05fc6b53d7ff4e7a8565428fe94a4` |
| effective test patch | `ee614041a0b3579f99b561daf33a763a3fe567cd90bc64cb3df0bca6131d2d8c` |
| registry | `cd218a8784db849d63bac185b529348795e23477e65b18893cdecfdcf0346ec3` |
| 来源 image manifest | `sha256:e83f64f4a2761078dbd377548ff8be3f9402e65c3b3ef5a6117e4fcb6d841db8` |
| 当前 actor 与 grader config ID | `sha256:4ca5aeae4e588c89008e6ca335500ffa71aea77bd6eab0b7491d514534696bb0` |

actor 为原公开镜像 `xingyaoww/sweb.eval.x86_64.conan-io_s_conan-14177:latest`，`image_override=false`。实际 `container_image_id` 与 RepoDigest、image identity 检查吻合；当前 resource 原件也分别保存 actor/grader 的同一 config ID，不能仅凭 tag 判同镜像。grader 诊断保留固定 manifest identity 与 verified sanitize，无身份异常。

actor materialize HEAD 等于 base；sanitize 前后历史计数均 7,639，删除 65 refs、保留 256，remote/reflog/unreachable 为0。UID54321 的实际环境位于 `/testbed`、Python3.10.14 / conda `testbed`；activation 与 prelaunch 检查无 violation。实际环境前缀不可由 actor 写；pip freeze 前后未变。baseline 的 `environment_package_digest=null` 是原件值，不能静默填成上表的 assignment digest，也不据此推断训练资格。

## 3. 全基线、FrozenPatch 与评分投影

`R/attempt/frozen/baseline.tar` 为 6,881,280 B，SHA `2e41fdc5cf7092cb8bd3e6468cf83a74ccb3ea7c74c0fed1d1b4326bee9daaa9`。逐一核 **973 个唯一成员**与完整 baseline manifest 的路径、regular 类型、100644/100755 mode 和内容散列；无缺件、多件、重复路径或类型不符。973 项亦与原公开 base 文件内容逐一一致。manifest 使用 `baseline_policy_v2`；973 个 census 项与 manifest 相等，24 个排除路径的排序摘要重算相等；grader rebuild census 与 actor baseline census **字节相等**。

依固定 canonical JSON 规则重算：

- baseline digest：`sha256:6fdad6e91c67e236fae68334aaa479344f4669406564d26b032f9c5b466497a3`。
- FrozenPatch digest：`sha256:c7bd035d8a2bb831118b06a90eb756c29439c0c71f4ef20161fcd1542da75eac`。
- 实际应用 entry 子集 digest：`sha256:a93ec9bbf6a896fc6eb2fce937e62a1217be9fdf488e89e3e8d517b503511b17`，其语义是 `applied_entry_set`，不与完整 FrozenPatch digest 混装。

FP 唯一 entry 为 `conan/tools/files/patches.py`，modify / regular / 100644；解码完整内容 SHA `5123502132daf78dd906f0c1ab2f8b75c786bd770451d95c6a65d05f49f1e8e9`。完整 1,822 B 候选 diff（三个 hunk）在内存按基线内容应用后与 FP 解码全文相等；diff SHA `e56a787281b6ba1dbc58c716607fbbb940f5c82aca800a101ba338661d89772c`。没有测试、conftest、fixture 或额外 demo 文件进入 FP。classification 为 projectable，excluded_pathset_changed=false。

FP、baseline、projection 的 task/public/image/head 与当前 rollout ID、物理 attempt `gpu1003-conan14177-qwen36-a1#p1` 均一致；projection 精确引用唯一 production 路径，重算应用子集与报告 hygiene 相等。静态核冻结 entry.py 的 `source_from_original` → trusted projection → `FrozenDeltaSource` → `SWEGradingManager.grade`：评分直接消费原 FrozenPatch，审阅 diff 不作为替代评分输入；report/status/result 内 report 完全相等。

## 4. 完整安装、真实测试与参考状态

独立读完整 `R/grading/eval_logs/evallog_gpu1003-conan14177-qwen3_d941d29e.eval.log`，29,945 B，SHA `6b4410d72934942da8821c0cde5e0c7073418f21029c0d474ef4dd748094b238`。真实安装段依次执行三个 requirements 的 `python -m pip install -r`；未跳过、无失败命令，install rc0，起止完整，1.114秒。实际 pytest 段为 `pytest -n0 -rA conans/test/unittests/tools/files/test_patches.py`；test rc0，起止与 footer 完整，13 passed in0.27s，测试段0.551秒，candidate exec rc0；log_partial=false、segment completed=true。

trusted setup 从固定 base 恢复唯一评分测试文件，base SHA `a5721c3f31609fca591c2d90e7b944a337cd93f1ec411118d56f6eee472f18c0`，受信有效测试补丁应用 rc0；expected/present/restored 均1，absent0、irregular 空。测试文件保护通过，6个目录受保护。正式实际导入为 `/testbed/conans/__init__.py`，version2.1.0-dev，prefix owner54322；runner 前后 digest 相同，runner_integrity_changed=false。

以下 node 均带完整前缀 `conans/test/unittests/tools/files/test_patches.py::`。从 **Start/End Test Output 之间的 raw summary**逐项提取，与 host view 和 diagnostics 的三个 partition 精确相等；段外 parsed0，missing/skipped/unaccounted 空。

| 分组 | exact node 后缀 | raw |
| --- | --- | --- |
| F2P | `test_multiple_with_version` | PASSED |
| F2P | `test_multiple_no_version` | PASSED |
| 原 P2P | `test_single_patch_arguments` | PASSED |
| 原 P2P | `test_single_apply_fail` | PASSED |
| 原 P2P | `test_single_patch_type` | PASSED |
| 原 P2P | `test_single_patch_file_from_forced_build` | PASSED |
| 原 P2P | `test_base_path` | PASSED |
| 原 P2P | `test_single_patch_string` | PASSED |
| 原 P2P | `test_single_patch_extra_fields` | PASSED |
| 原 P2P | `test_single_patch_file` | PASSED |
| 原 P2P | `test_apply_in_build_from_patch_in_source` | PASSED |
| 原 P2P | `test_single_no_patchset` | PASSED |
| 迁移 P2P | `test_single_patch_description` | PASSED |

迁移节点仍是原集合中的一项，2F+10原P+1迁移P=13，不是新增参考。report reward1 / resolved 与 2/2F通过、0/11P失败一致；grading total94.183秒，env reset16.072秒，test stage2.162秒。测试可证明的功能范围由语义报告说明，不能把13P自动解释为真实磁盘补丁应用或候选全行为正确。

## 5. 第一请求交付、模型、预算及全部 HTTP

完整 issue SHA `e4440f3251e4f7a3cb5949e8d70c7ef2aaba7ab8ad0d61ea27d9e8bcf243ad48`；brief v2 文件 988 B，SHA `da4b3670c36a87e03a441055e4a18c39c6d0aa1f2f2b06f5f11dabc5710957e8`。实际 solver prompt 与 attempt/prompt 字节相等，2,054 B，SHA `afff730a0f16d7adac65375ddbb0620f0ac4e30859d80b7a20f04e2c5d37dae3`；此完整串出现在 `G/requests.jsonl` **首请求的 user content**。issue 完整保留；brief 仅按冻结 entry 的 `notes.strip()` 去掉首尾空白，正文完整，明确替代旧 development hints。不能只凭配置的 brief path 判实际交付。

当前 capture UTC13:53:14.940166–13:53:15.085044，在 job UTC13:53:15.189697 开始前完成；不是把事后 service 配置冒称 job 时实测。engine/adapter 前后实际 inspect 的 ID、启动时刻、PID、Cmd 和 restart count 相同：engine PID999327，adapter PID1000924，restart0、running、无 OOM，model mount 只读。绑定历史下载 manifest 的 repo `Qwen/Qwen3.6-35B-A3B`、revision `995ad96eacd98c81ed38be0c5b274b04031597b0`。当前文件大小清单与下载清单真实数组 **37件、71,926,788,362 B、26 weight shards**相等；下载 metadata 的 files_count40 保留为历史字段，不冒充当前37件。

实际 HTTP server readback：SGLang0.5.20、/model model与tokenizer、bfloat16、TP1、context196608、max_req_input_len196602、max_running_requests1、mem_fraction_static0.9、ready。actual adapter 配置与 service 配置字节相等，qwen3_coder tool parser / qwen3 reasoning parser，sampling1.0 /0.95 /20 /65536；实际 class 为 RH2 AnthropicAdapter subclass，count_tokens/parse_wire/terminal publisher/overflow wrappers 存在。原 input_check 中 config_only=true、runtime_verified=false 仍保留；本次 actual 证据另行补足服务读回范围，未改写原件。

probe-wide-v1 为 context196608、每请求输出65536、CC max-turns240、wall10800秒、gateway requests1024、first byte1800秒、adapter idle14400秒；grading whole/setup/apply/test 为3600/300/120/1800秒。实际 request 全部 max_tokens65536；gateway 剥除请求采样键，由上述 adapter defaults 消费。gateway retry0。

逐一核 **15请求 /15响应 /15adapter turns**：seq1–15唯一连续，当前 session全部对应；HTTP200、attempt1、stream_error=null；15份 SSE 大小与 response记账相等，message_start→message_delta→message_stop完整，usage与stop逐项对应；前14次 tool_use、最后 end_turn。14个 parsed tool调用及显式参数与 CC轨迹逐项对应，最后 adapter content与CC final字节内容相等。累计输入169,819、输出5,028，adapter、SSE/response及CC一致。此数量不是41条assistant事件或14次工具数。

CC observed、trajectory init、User-Agent 均为2.1.205；training guard max retries0、disable nonstreaming fallback1、unattended retry0。CC result 的 display maxOutputTokens32000与实际15请求65536分开保留，不能以display字段替代实际预算。harness stdout与attempt trajectory字节相等（187,118 B、255事件），stderr0 B；41assistant事件、8Bash/5Read/1Edit，1次工具结果错误。错误是模型自测，不是运输丢失或正式评分失败；具体内容见语义报告。

## 6. 退出、双层清理、drain 与资源事实

当前 terminal snapshot 记录 dispatcher child exit0，UTC13:56:11.198617结束；attempt ran、harness exit0、termination=completed，solve36.81秒。harness exec inspect 为 Running=false /ExitCode0 /Pid1043680，stdout完整、stream_error=null。pre-drain与quiescence residual0，无timeout，agent_processes_zero且workspace digest稳定双读；FP在此后冻结。

`D/current_terminal_evidence_v3/journal.jsonl` 中 **PID1** 对精确 unit `rh2-gpu1003-conan14177-qwen36-a1-qwen-first10-v1.service` 的启动与成功消息使用同一 invocation `0b054bb8b2a548fbb194b4e7c044e770`；unit_log_success 时间 `1791035771224578`（UTC13:56:11.224578）。退役 unit 的 LoadState=not-found /默认 ExecMainStatus0 未当作完成证明；旁存 dispatch v2 的其它 job journal亦未冒充当前 job。

actor container_rm0、container_left空，relay/network failures空，精确标签下残余container/network均空；grader manager created1/removed1、containers_open/supply_open/cleanup_failures空，regrade0。gateway的当前session_close与attempt drain：revoked=true、active_requests0、drained=true，ts1791035674.4739864。

resource原件共 **13个时间样本**，UTC13:53:09.939548–13:56:10.761359：

| 对象 | 有该对象的样本数 | 所见 memory.peak 最大值（B） | pids.peak 最大值 |
| --- | ---: | ---: | ---: |
| actor | 5 | 848,257,024 | 21 |
| relay | 5 | 27,590,656 | 7 |
| grader | 6 | 256,544,768 | 8 |

所见对象的 oom_kill、pids max事件、cpu throttled_usec均0。manager另记录 grader peak328.594MiB；它与稀疏sample的244.660MiB不是同一观测口径或时刻，不能以其中一值覆盖另一值。声明 actor profile为2CPU/4GiB/pids512，grader环境声明2CPU/4GiB/UID54322；**完整 actual HostConfig 与 memory.max/cpu.max/pids.max 未保留**，diagnostics.resource_facts=null、monitor gaps unknown，因而未声称完整配额、全期间无瞬时异常或资源隔离全验收。

## 7. pair 当前状态、维度与停止条件

pair receipt SHA `3ad116601fa17ecc48259eaa3b098388198871e3ed0eac76485906b43be6c17a`，UTC14:08:41.376581；本地总账当前该请求为 returned /revision4，updated_at UTC14:09:15.261025，链接此same-SHA回执。它确认两模型各一次完整交付，new repeat samples0。本次原 closed snapshot 的 paired_request_closed=false是更早单臂快照；后续pair闭合不回写原件。

same frozen task materials 不表示相同 runtime/profile：Coder code7 entry SHA `a1efff44dc2cbedfc81d93b2da8d84a92f6c9c88b15c2a10bf96db2026a4e82c`，Qwen code8 entry SHA `bdf806bf8da1d5ebb4970887bfc3c7738eb3e57a75e1d07215d6d68b17e574c4`；共享 solve_attempt SHA相同。Coder profile `4a6435bc16d26c517b34eb1a4e40e83cdeef3ef08e813a136e9ae06ed67e22b6` 的gateway upstream18081，Qwen profile `c731fff97bcd8ed6be3f31ac2108980dc549f0e5a75403f9738b2b3b2537e500` 为18082，保留差异。模型服务与候选本来不同；旧Coder“Qwen未执行”字段只代表旧时间，不当作当前待办。

A/E/G核身份、归档/投影、原真实测试和退出链；D/F/H/N核实际配置、版本来源、唯一FP输入、两模型差异；L/M核已记录预算、HTTP/工具守恒、资源及生命周期。I按当前事实收口。J/K不另作通用代码质量或架构扩审，本轮没有实现修改；B/C正式训练分布、训练挡板和训前资格均N/A，因为独立探针没有miles receipt/训练消费，未变更该边界。

仍未知：权重文件本次未逐件重hash、GPU内存加载身份未attest；CC平台tgz payload未在本地封包，仅有版本观测及运行记录SHA `d3dadfa9cde294ac82c755eb6d889291228849180bac5d677ad1a4027aca1bc4`；stdout/fixture通用可伪造边界未由窄核解决；baseline环境digest空与env_qualification=absent保持原值。上述均是限定主张的证据边界，不造当前运输缺陷。

**最小处置：保留本次原评分与固定材料，无需补跑、重分、修共享consumer或新增guard。** 如未来要作更强资源、权重或训练主张，再由相应授权作业保存所需原件；本轮不因未知扩大执行。无finding需现在修；候选语义与训练资格不能由pair returned或reward1代替。

**停止条件已满足：当前job的固定身份、完整baseline/archive/rebuild、FP投影、真实安装/完整参考段、实际模型/预算HTTP、退出/清理/drain已闭合，并显式保留未保存范围；保存报告后停止。**
