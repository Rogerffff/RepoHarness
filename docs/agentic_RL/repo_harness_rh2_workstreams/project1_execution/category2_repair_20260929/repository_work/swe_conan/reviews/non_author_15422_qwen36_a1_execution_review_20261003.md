# Conan15422 Qwen 首臂：非作者执行／运输窄核

2026-10-03。审查者 `conan11594_qwen_execution_recover`，独立于封包、候选与执行回执作者。作业 `gpu1003-conan15422-qwen36-a1`；原请求 `swe-conan15422-r12-briefv1-20261003-v1`。

**结论：`execution_evidence_verified_with_scope_limits`，本 scope 未发现新增 blocker。** 本次 Qwen 首臂执行、公开材料交付、baseline/原 FrozenPatch 评分运输、正式参考覆盖与作业清理可核销；原评分 `reward=1 / resolved` 有完整原日志支撑。17 个有限资源切片、权重未重复全量散列及运行版本差异继续保留。报告只审执行，不授予候选语义、题级准入或训练资格，不替题主执行整项 ACK。

遵循现行分类二协作规则；只用本地 Python 标准库读原件，没有导入项目模块、执行项目代码、跑项目测试、CPU/GPU/模型、Docker 或远端操作。新增内容仅此报告及[结构化核对结果](non_author_15422_qwen36_a1_execution_review_20261003.json)；冻结原件、共享记录与题主文件未改，未向其他 Codex 线程发消息。

## 原件身份及完整性

权威依据为[本 job closed snapshot](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1)。逐件重算[closed manifest](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1/qwen_first10_closed_v1/gpu1003-conan15422-qwen36-a1/closed_manifest.json)中的全部成员 size/SHA：**178/178 件、18,631,732 字节一致**。以下 SHA 均为本次读取后重算，机械回执的 `true` 未作为替代证据。

| 入口 | SHA-256 |
| --- | --- |
| closed manifest | `216482c3996d5111c40bbf0aecde197b2fc29c518b2c5c3658f0067da7c11024` |
| [Qwen 机械执行回执](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/gpu1003-conan15422-qwen36-a1_execution_receipt_v1/execution_receipt.json) | `454ea90054460b6a14c68a0e7bc52f5709638b86e97c5751848350e25c5bde0a` |
| [配对执行回执](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/swe-conan15422-r12-briefv1-20261003-v1_pair_execution_receipt_v1.json) | `b7f007238f09e0db190b10e6d908a799cc85d090b30f4b8300c9ca400c1983aa` |
| 原题主 request | `c7062edcbdb67ecaa7085099394865578407e83fb8be279969e0d5534ba7da09` |

派发 request 本身 SHA `24d843fa1b9838a661b0253b56224729a5847315f78aeb39f8cac8672812ad6f`，与 terminal 注册记录一致；它与原题主 request 是不同对象。

## baseline 和两项 FP 的运输

[baseline manifest](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-conan15422-qwen36-a1/attempt/frozen/baseline_manifest.json) canonical digest 重算为 `sha256:c041d7fad2f908302f448cbda2ab81b95557b0018b7efe5cdea4b87d51ca50af`。[baseline.tar](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-conan15422-qwen36-a1/attempt/frozen/baseline.tar) 7,311,360 字节、1,002 项，全部 regular；逐项按路径、对象类型、Git mode 执行位和内容 SHA 对照 manifest，无差异、缺项或重复项。tar SHA 为 `c0e9588ca0e5ad5130d954c634764db03b48349ce7237fafbe437e1f2916c9c6`。

[原 census](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-conan15422-qwen36-a1/attempt/frozen/baseline_census.txt)有 1,002 条 regular，重建的 entries 与 manifest 一致；policy `baseline_policy_v2` digest 重算正确。[grader rebuild census](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-conan15422-qwen36-a1/grading/baseline_rebuild_census.txt)与原 census 逐字节相同，共同 SHA `02afd6caba22b3c0cecf5d1e985627def65d576b4501940718488645ebb8a9c7`，与原记录 `baseline_rebuild_passed=true` 支撑同一重建事实。本审查未新启动容器重建。

[原 FP](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-conan15422-qwen36-a1/attempt/frozen/frozen_patch.json) canonical digest 重算为 `sha256:7c2ecd3456098c228d9b82189252fbb0d3f5187f944c8aa1f69b7b18669ef31c`。task/job、physical attempt `#p1`、baseline、public bundle、实际镜像及 base HEAD `f08b9924712cf0c2f27b93cbb5206d56d0d824d8` 均相接，两个 base64 内容 digest 均正确：

| 原 FP 修改项 | 完整内容及评分投影 |
| --- | --- |
| `conan/tools/cmake/presets.py` | regular/100644，16,247 字节，SHA `e46cebac1c4982bf03b3e629ff9731d5cbc0f19ac501d45f327d01142fb70c51`；正式含入 |
| `conans/test/integration/toolchains/cmake/test_cmaketoolchain.py` | regular/100644，49,237 字节，SHA `47d955bcfbc5f35df792801332decbbbe95c13255786ee498c6a047094ddea1f`；官方测试修改剔除 |

[完整 diff](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-conan15422-qwen36-a1/attempt/candidate/conan-io__conan-15422.diff) 3,165 字节、2 个文件段、SHA `9ab2e85632b10b03923efa531995133756e419258eadcb41d39ade627a60a506`；从 baseline 原字节按全部 hunk 的旧行、上下文与行数重建，两文件均与 FP 完整内容相同。[projection](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-conan15422-qwen36-a1/grading/projection.json)只保留 `presets.py`，FP/job/physical attempt identity 正确。重算生产项 entry-set digest `sha256:d0b32a48b47f0066f19df242ddcf055d83e40743e33fe4b7ad9b82569a78f694`，与 report hygiene 相同。

因此 report 的 `test_files_modified=false` 是**实际评分应用集**的属性，不能解释成原 FP 没有测试修改。宿主 trusted setup 后记录恢复了 1 个官方测试文件、正式 private patch apply RC0、保护文件存在，与投影边界一致。

## 固定材料、镜像与 code/profile 的适用范围

[实际派发 request](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1/queue_qwen_first10_v1/requests/gpu1003-conan15422-qwen36-a1.json)的 48 个输入 SHA 全部匹配本地原件。[first10 fixed inputs](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1/config_qwen_first10_v1/fixed_inputs_manifest.json)本题 target 的 38 项 material map（含共用封包）与实际 request 相同，task config 完全一致。实际 input_check 的 prepared manifest、host grading artifact、grading materials identity、grading revision、公开交付、assignment、baseline policy、spec overrides 与预算均与冻结 expected record 相同。

与旧 Coder 原件相比，以下身份相同：prepared manifest `f054e0923e3c9b56b8191ddfec9d4ad9b8a219b9462044e788256ec511d33059`、host grading `a1a3b4d02aeac573ca8ff4ba62ec892604e7af075db8137792f6db6300c38f58`、grading materials `sha256:90aad16e26a29c327e6735755eee37125a885b4051dc5f27a6a9ba1d456f0927`、公开 issue/brief/prompt、baseline 和评分预算。actor `container_image_id`、grader diagnostics `local_build` 均为 `sha256:a27936515e625ace25f5d76dcef25566079c7ac355b51bdfc5c3408c26a07ead`；本 job 资源切片实际看到 actor 9 次、grader 6 次且镜像 ID 同，超过 purecheck 配置层声明。沿用已 prepare 材料，不宣称 fresh prepare。

Coder executor 是 code7，Qwen executor 是 code8。两 source manifest SHA 分别 `be705a777484c70af2afe9a34b6dd288bd85c2b1f536c6d57bd59aecb4eb0352` 和 `09ddb8bfdeecd3ffaa38c1048a574161ef6fa6053b2855da50166e8e8677899d`；985→1,045 项，**5 修改、60 新增、0 删除**。修改为 `entry.py`、`prepared_task_face.py`、`bundles_v2.py`、`swe_material_revisions.py`、`material_revision.py`。快照实际 entry/dispatcher SHA 与 code8 manifest 一致；`solve_attempt.py`、`grading/manager.py`、`grading/trusted_projection.py` 三项运输源码 SHA 声明相同。本题新 preparation policy 的实际记录为 `null`，准备预算仍为 300 秒；据实际消费记录可以确认本题材料一致，不能延伸成整个 code8 所有分支审查或全代码相同。远端整个源码树未由本轮重新散列。

两 profile 只在 `model_proxy_upstream` 有差异：Coder `172.17.0.1:18081`，Qwen `172.17.0.1:18082`；profile digest 分别 `4a6435bc…`／`c731fff9…`。整个 runtime/profile 不能写成相同。

旧 Coder 首臂仅复用[已接受执行审查](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/conan15422_coder_a1_execution_review_v1.json)，本轮重算 SHA `387975f1e1f6dfd92c23500bd207b629b209191cbd62c83f22fa76b108f71ea5`，状态 `execution_evidence_consistent_complete_test_failure`，原 reward0。复用范围是完整执行和评分失败运输，不能借此得到 Coder 候选语义成功。结合本次 Qwen，可以支持配对回执“各模型首轮一次已执行”的事实；本报告不代替 owner 整项收口。

## 首 API 的完整 issue 和 brief

public view 完整 issue 为 1,375 字符，重算 SHA `de837ef1541eb6d79d9d596483b3f85afdcdca99502b57854935c2d59993dd8e`；base prompt SHA `a41bbc56b0c4926e0baaa875e9e5d8561935b7a5b090c88da2cfe0fbb184b87f`，brief v1 SHA `7d82590d898dda57d0b281eb07e12e154f2f4e66dcb88f026dc3d1d576b47054`。

[solver prompt](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-conan15422-qwen36-a1/solver_prompt.txt)、attempt prompt 和[首 API 请求](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1/services_qwen_code8_v1/qwen36/gateway/first10-v1/gpu1003-conan15422-qwen36-a1/requests.jsonl)实际任务 text 按原字节完全一致，SHA `475fff849ec5f2d04441bcfd4a9b0de9bd5f707a6888c63df36293cc77e6fc92`。完整 issue、base prompt 和 brief 正文均在其中；brief 首尾空白剥去，其正文及替代旧开发提示的交付标记保留。它说明使用当前工具入口、固定 CMake3.23.5，并要求实际配置/构建有成功证据。这里核交付事实，不新作公开读者审查。

## 45 个正式参考和 3 个非参考 skip

[原 eval log](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-conan15422-qwen36-a1/grading/eval_logs/evallog_gpu1003-conan15422-qwen3_f5085a01.eval.log) 52,302 字节、SHA `deedb927b5f3a652183ffe9fed169bcda16ec37e2529b32542c0788592749c51`。完整安装/测试 start/end 时间标记按顺序存在；裸 `RH2_INSTALL_RC=0`、`RH2_TEST_RC=0` 各一次，diagnostics outer candidate exec RC0、install 非 skipped、log 非 partial 相符。

实际评分命令 `pytest -n0 -rA conans/test/integration/toolchains/cmake/test_cmaketoolchain.py`。逐完整节点精确匹配 **45/45 个正式参考全部 PASSED**：原 F2P1＋新增 F2P4＝5/5，P2P40/40；无 missing、skipped 或 unaccounted 参考。原 footer `45 passed, 3 skipped in 3.77s` 的三个 skip 均为非参考：

- 同测试文件第355行：Only OSX。
- 同测试文件第382行：Only OSX。
- 同测试文件第816行：Only Windows。

diagnostics `num_parsed_tests=46` 保留原口径：部署 parser 取摘要第二个 token 为键，45 个 PASSED 完整键加上 3 条 SKIPPED 共同的 `[1]` 键，得到 46。它不是正式参考分母，也不是只剩 46 个真实测试。段外解析0、runner integrity 未改变；实际 UID54322 的 CMake console prerequisite verified/RC0，有成功标记。原评分 `resolved/reward1` 的执行和运输支撑成立，候选功能语义另审。

## 46 HTTP、45 模型响应、46 工具和 CC47

[gateway 原请求](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1/services_qwen_code8_v1/qwen36/gateway/first10-v1/gpu1003-conan15422-qwen36-a1/requests.jsonl)及[响应原记录](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1/services_qwen_code8_v1/qwen36/gateway/first10-v1/gpu1003-conan15422-qwen36-a1/responses.jsonl)各46行；**第13行是一次 `/v1/messages/count_tokens?beta=true`**，stream=false、无 generation seq；JSON 返回 HTTP200/attempt1、23字节、`input_tokens=18274`。其余45次为模型生成，seq恰为1–45，有45份完整 SSE 和45条 adapter turn。count_tokens 不属于模型采样，也未加入生成 usage 总量。

45 次生成全为 HTTP200/attempt1，无 stream error；44 个 tool_use stop、末次 end_turn。逐 SSE 核 bytes、完整 message_start/message_delta/message_stop、model、stop reason 和 usage，与 response 相同；adapter parsed 的 text/thinking/tool names/arguments 重建后与全部 SSE 一致。45 次总输入1,761,359、输出9,008，与 gateway usage 和 CC result 相同；本次最大 prompt62,926、output948 tokens。

模型 SSE 含46个 tool_use，seq1、seq10各有两个工具；CC46个 tool_use 与46个 tool_result 的 ID 集合一致，Bash29/Read13/Edit4，其中2个 error result 如实保留。**CC 自报 num_turns47，与45模型响应或46 HTTP不是同一计数。** 这是同一首臂内部调用，不能当成46次／47次独立样本。

进一步逐块核 SSE→CC 共110块：108块字段相同，另外两处实际 CC 工具参数规范化明确记录：

| 模型 seq | 原 SSE → CC 记录 | 证据解释 |
| --- | --- | --- |
| 14，Edit | 补 `replace_all=false` | 首 API 工具 schema 的 default 明确为 false；字符串与路径未变 |
| 43，Bash | `cd /testbed && git diff --stat` → `git diff --stat` | CC init cwd为 `/testbed`；没有宣称所有工具参数字节不变 |

两份 trajectory 字节相同，719行、749,269字节；harness stderr0、log_complete=true，CC2.1.205 success/end_turn、实际 solve92.61秒。

预算采用统一实际口径：context196608、request/adapter输出65536、CC turns240、solver10800秒、gateway1024 requests、首字节timeout1800秒、adapter idle14400秒；grading whole/setup/apply/test＝3600/300/120/1800秒。45次生成 request max_tokens全部65536；actual adapter采样temperature1.0/top_p0.95/top_k20/max_new_tokens65536。CC modelUsage自报maxOutputTokens32000不替换实际HTTP/adapter值；本次低于输出上限，未验证65536边界容量。

## 当前服务身份、退出与清理

实际 engine/adapter 的 before/after inspect完全相同：container ID/PID/StartedAt/RestartCount未变、model mount只读；adapter code mount绑定code8。SGLang0.5.20 readback context196608、max_req_input_len196602、max_running_requests1、tp1、bf16相符。模型下载 manifest固定 `Qwen/Qwen3.6-35B-A3B@995ad96eacd98c81ed38be0c5b274b04031597b0`；37个 runtime 文件大小与下载清单一致，总71,926,788,362字节，实际chat template SHA相符。保留 capture 原限制：**未重复全部权重SHA，也无GPU内存权重SHA证明**，不能由显示名独自推出更强权重身份。

[terminal snapshot](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1/qwen_first10_closed_v1/gpu1003-conan15422-qwen36-a1/terminal_snapshot.json)记录entry RC0；[当前原 PID1 journal](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1/diagnostics/QUEUE_QWEN_FIRST10_V1_gpu1003-conan15422-qwen36-a1_before/current_terminal_evidence_v3/journal.jsonl)在本次起止窗口内有 exact UNIT 的 `_PID=1 / SYSLOG_IDENTIFIER=systemd` Started 和 `Deactivated successfully`。registered ended为 `13:52:53.169340Z`，PID1成功为 `13:52:53.195115Z`，journal query RC0、SHA `932dd5bfbd2501582293be8afb180635c7e42a81787e148715c5f896dec1e1a7`。退役unit的 `LoadState=not-found/ExecMainStatus=0` 没有当成真实退出证明。

actor cleanup：container_rm0、container_left空，network/relay failures、labeled containers/networks均空，cleanup_ok=true；pre-drain stop及quiescence residual0、未超时。独立session_close与attempt drain相同：revoked=true、active_requests0、drained=true。grader manager close created1/removed1、containers_open/supply_open/cleanup_failures空、regrade0；最后资源切片job容器空。本job和session闭合；共享模型服务继续运行不是本job遗留。

## 有限资源与停止条件

[17个资源切片](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan15422-qwen36-a1/qwen_first10_closed_v1/gpu1003-conan15422-qwen36-a1/resources.jsonl)覆盖 `13:48:53.732855Z`–`13:52:54.874402Z`，最大间隔15.080041秒；actor/relay/grader分别被采到9/9/6次。采到的memory.peak最大为998,592,512／27,344,896／264,310,784字节，pids.peak25/7/8；采到的OOM/OOM kill/pids.max event均0。grader diagnostics peak344.938MiB为另一路观测口径，不与切片最大值合并为新全程峰值。

**这些不是连续资源观察，未完整覆盖容器终点计数或engine/adapter服务cgroup；不能据此推出完整资源峰值、总体CPU/GPU吞吐、容量或跨模型效率。** 限制约束后续效率分析，不否定已闭合执行及评分运输。

审查适用A/D/E/F/G/H/L/M/N的运行证据维度；B/C训练分布与闸门、J/K全面源码质量与演进审查不在本对象内。I通过明确scope与残余证据限制控制分期。没有T0决策、实现或挡板变动；本轮没有推翻旧Coder执行结论。保存本报告和JSON、返回SHA后停止，不执行追加采样或共享记录写入。结构化核对结果SHA：`fdb9b96a536a6b48b26fca7a73ca2b4da4e586393ea603e480b9dd055b870ef2`。
