# Conan13403 Qwen 首臂非作者执行与运输核查（2026-10-03）

结论：**`execution_evidence_verified_with_scope_limits`**。在下述本地静态核查范围内，没有新增执行或运输阻断；原 `raw_reward=1.0 / resolved`、完整 1F0P 和退出码事实一致。本报告不判断候选是否完整解决 issue，也不签配对 ACK 或训练资格。

核查对象为 `gpu1003-conan13403-qwen36-a1`，固定请求 `swe-conan13403-r12-briefv1-20261003-v1`。仅使用本地 Python 标准库读取原件、复算 SHA/canonical digest、解析 tar/diff/SSE/JSON；未运行远端、Docker、模型、项目导入或项目测试，未修改冻结材料、共享账或题主文件。

## 原件完整性与固定输入

权威原件为 [本臂闭合快照](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1)，实际结果根是 `queue_qwen_next12_v1/results/gpu1003-conan13403-qwen36-a1`。[closed_manifest](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1/qwen_next12_closed_v1/gpu1003-conan13403-qwen36-a1/closed_manifest.json) 的 SHA 为 `f9aa51eee527e5637c5b4cce834195552cbddba2167d007097630250f6760d1e`；**160 件、14,472,896 B 全部逐件 SHA/size 匹配**，不以机械回执的布尔值替代此复算。

[本臂机械回执](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/conan13403_qwen36_execution_receipt_v2/execution_receipt.json) SHA `200a7ebcf61c9647dac5af5e5c72e0cd51affca2d7ef8dec7767e34304a8beca`；[pair 执行回执](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/swe-conan13403-r12-briefv1-20261003-v1_pair_execution_receipt_v1.json) SHA `da11eb09698c9ab49a97930189e5954c63d94a6041ee1171295bf8f2bea601a9`。机械/总回执仅作为导航和交叉对照，关键结论均来自冻结原件。

注册请求 SHA `dd2cccf14c4f458558c96e70c97f775d1a132f90fdd87ca0973dd795daba0ec2`；其 64 项输入全部本地 SHA 匹配。固定 target 的 43 项材料文件匹配，43 项材料绑定叶值与原 owner request 一致。两份原 owner request SHA 均为 `bf8eb0004261dc97ebc7a0959b77e3c1b94c4b86a8d58a89469a23c3e4c2dacb`。

prepared manifest `7905288b43fab17a3d0f0c2d8ff5e6e31d1177eb5c7b159050bdd14a51b4df25`、host grading `24a3c7495c410914a8aa341113596b11b40139a368cac73a32d5335d0dd9043f`、材料 identity `0f73cdf9d521c865ffd7d7cb070f642581e7225b5d3bfd168832c72125b3a065` 及 revision `conan13403-cloud-test-v4-gnu-v2` 一致。actor attempt 实际 image、grader diagnostics 实际 image 和资源记录实际 image 都为 `sha256:b40849e11f0b85cc14a243ede47148c2b9bd7f49a8898640879ad724dd7ff4ff`；HEAD/base 为 `55163679ad1fa933f671ddf186e53b92bf39bbdb`。依据为 [input_check](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-conan13403-qwen36-a1/input_check.json)、[attempt](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-conan13403-qwen36-a1/attempt/attempt.json) 和 [grader diagnostics](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-conan13403-qwen36-a1/grading/eval_logs/evallog_gpu1003-conan13403-qwen3_80d72cf3.diagnostics.json)。

## 完整基线、公开基线与原工件评分运输

[baseline manifest](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-conan13403-qwen36-a1/attempt/frozen/baseline_manifest.json) canonical digest 独立复算为 `sha256:025760d35c701c25f189a4303579d2e2b337d11c1af63855112075d899859077`。`baseline.tar` 为 6,584,320 B、SHA `a1383162013c2c236ce2bc9ef8a6dd97c4090d519dc13fb7100f3b494947815f`；960 项均为 regular，逐项名称、类型、Git mode 和内容 SHA 与 manifest 一致。census 所有 960 项对应 manifest，原 census 与 grader rebuild census **逐字一致**，SHA `e588c13e8cd1dae182b21d9d57ffcf7693a1972c0388fc16976ad746f555954a`。Git、harness 与可再生缓存按 `baseline_policy_v2` 处理，原记录 omitted cache 为 0。

公开 rollout 的 public 对象 canonical digest 为 `0ed07332c3b10087f669e9345772ed5eddd316cab87621a95a1e38b38464374a`；host grading 对象 canonical digest 为 `0a8aeebe928ddc6062f3bd6d0e498a0b0a2e89983bf9be4dc6ae5de9e9e16222`，均与固定材料/assignment 一致。

[FrozenPatch](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-conan13403-qwen36-a1/attempt/frozen/frozen_patch.json) canonical digest 为 `sha256:8d9fb7fd1bb2d55907d473e392e93ce5d004eacdf6fcc033cb6bff32c5915f79`，两个 modify/regular/100644 项的 base64 解码与内容 SHA 全匹配：

| 路径 | 大小 / 内容 SHA | 正式 projection |
| --- | --- | --- |
| `conan/tools/gnu/autotools.py` | 6,235 B / `460bb9505e4fe35e74be9970e997a265fea31550cff9c39d93326d11d16b8a65` | 含入 |
| `conans/test/unittests/tools/gnu/autotools_test.py` | 2,609 B / `813a19ed7a097029fdf4bdf8b5b856479fedbc854fbff023190bbbf5fd6e31a8` | 剔除 |

[完整审阅 diff](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-conan13403-qwen36-a1/attempt/candidate/conan-io__conan-13403.diff) 为 3,687 B、SHA `c3aa89a94e8b40a614a420739d4f04b6c0f3a0b451c4d1f6c47441dee9f3f9ea`。逐段逐 hunk 校验所有旧行/上下文并从原 tar 重建，两个文件新字节均精确等于 FP，未用选读段落替代完整 diff。

[projection](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-conan13403-qwen36-a1/grading/projection.json) 的 FP digest、rollout、physical attempt identity 全匹配，含入路径恰为生产文件一项。按含入项独立复算 applied-entry-set digest 为 `sha256:1b0f7d9d383fe8a8b1f7f64863a05916fceda1a5132354ecbc282c8c5d9537f1`，与 report hygiene 一致。classification 为 projectable，无 runtime-private/excluded pathset 改变。原 FP 直接评分，审阅 diff 不作为评分输入；官方测试修改不进入正式候选，trusted setup 还原 1 个正式测试文件、apply RC0。

## 与首 Coder 的比较范围

复用 [已接受的 Coder 执行报告](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/conan13403_coder_a1_execution_review_v1.json)，SHA `151decc3f1e8c9a8b771e37c662a9686ffc0f085845607e6c0762cc94e1d8409`，仅复用其执行范围。本次另外核对原 Coder manifest 所绑定的 [Coder 结果原件](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v23/results/gpu1003-conan13403-coder-a1)：完整 baseline manifest、census、rebuild census、solver/attempt prompt 与本臂逐字一致；两个 tar 的全部 960 项类型、**实际 tar mode** 和内容字节相同。Coder tar SHA 为 `18bba5cec5e5dddc7ffddd66a672bb191aafdeccacaa7816d1465836dca93dd4`，与 Qwen archive SHA 不同，因此只宣称全部成员一致，不宣称 tar archive 字节一致。prepared、host、assignment、revision、正式参考、实际镜像、公开交付和预算均同。

**本题两臂执行 snapshot 均为 code_v8**：原 Coder request/terminal 与 Qwen request/terminal 均指向同一 entry；两份 source manifest 逐字相同，SHA `09ddb8bfdeecd3ffaa38c1048a574161ef6fa6053b2855da50166e8e8677899d`，本地 code8 的 1,045 项文件逐项 SHA/size 全匹配。entry SHA `bdf806bf8da1d5ebb4970887bfc3c7738eb3e57a75e1d07215d6d68b17e574c4`、serial_dispatch SHA `cb435f7390d9aeba3bad51efabf808634668263e9dfbcffae96f50a4b8f90f10`。前两题的 Coder code7→Qwen code8 差异不适用于本题；code8 的历史来源不等于实际 Coder 跑了 code7。

模型运输仍有差别：Coder 为 code_v4 运输，Qwen 为 code_v8 运输。两臂 profile digest 分别为 `4a6435bc16d26c517b34eb1a4e40e83cdeef3ef08e813a136e9ae06ed67e22b6` 与 `c731fff97bcd8ed6be3f31ac2108980dc549f0e5a75403f9738b2b3b2537e500`；递归比较唯一 profile 字段差异是 `network.model_proxy_upstream` 的 `172.17.0.1:18081`→`172.17.0.1:18082`。本题 preparation_budget_policy 为 null、setup 300 秒。同固定输入/基线不能泛称模型运输及运行 profile 完全相同。

## 首 API 交付、预算与当前模型身份

原 issue SHA `425518836e7247e71cd3071f572b65cafafbeb041912d41af64c8e9f0b9e1585`，prepared base prompt SHA `222c816a5c59c66e0b73438842e15c9086b4507465ee5178a8575c25643f5497`，brief v1 SHA `4deeac2d97519ad9c0dfd9d2e0ba15bb6b034e0a5736d96cf2e86bfa0f1b37c5`，实际 delivered prompt SHA `88c598cd67a46643a39399f3460244f1bfc91ab15b9f066d34dfb32b3cfb1850`。按原始字节解码保留 CRLF，确认完整 issue 在 base、base 与完整 brief.strip() 在 delivered、完整 delivered 在第一条真实 HTTP messages 中。solver/attempt prompt 同字节，并与 Coder 实际交付同字节。依据为 [公开 prepared 输入](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1/prepared_new_three_code8_v1/conan13403/prepared/rollout_task_views.jsonl)、[brief v1](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1/prepared_new_three_code8_v1/conan13403/public/development_brief.md) 和 [真实请求日志](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1/services_qwen_code8_v1/qwen36/gateway/next12-v1/gpu1003-conan13403-qwen36-a1/requests.jsonl)。

统一预算核为 context 196608、输出 65536、CC 240、wall 10800 秒、gateway 1024、first-byte 1800 秒、adapter idle 14400 秒；grading whole/setup/apply/test 为 3600/300/120/1800 秒。26 条实际 HTTP 的 max_tokens 都为 65536，服务实际 Cmd/config/server readback 对应一致。CC modelUsage 的 maxOutputTokens=32000 属其自报口径，不能替代实际 HTTP/adapter 的 65536；本次未测试满 context/output 边界。

[当前服务捕获](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1/diagnostics/QUEUE_QWEN_NEXT12_V1_gpu1003-conan13403-qwen36-a1_before/capture_receipt.json) 与前后 inspect 一致：engine `5a023c27…` / PID999327 / StartedAt13:24:03.233754906Z；adapter `aff52a71…` / PID1000924 / StartedAt13:26:58.312905352Z；RestartCount 均 0，前后 inspect 逐字相同，model/code bind 只读。模型下载身份为 `Qwen/Qwen3.6-35B-A3B@995ad96eacd98c81ed38be0c5b274b04031597b0`，download manifest SHA `32bd30f61860366b3783eabc9d75bee0cd28c474d9c07de8be8d9ae60a4552ab`、chat template SHA `e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259`；37 个当前模型文件大小与下载 manifest 对应，共 71,926,788,362 B。**没有逐权重重新计算 SHA，也没有 GPU 内权重哈希见证**。

实际 SGLang 0.5.20、bf16、tp1、max_running_requests1、context_length196608、max_req_input_len196602、allow_auto_truncate=false；实际 adapter 为 qwen3_coder 工具解析/qwen3 reasoning 解析，sampling temperature1.0/top_p0.95/top_k20/max_new_tokens65536，Cmd idle14400。

## HTTP、SSE、adapter 与 CC

**26 HTTP = 26 generation SSE = 26 adapter turn**，没有 count_tokens 旁路行。seq1..26 连续；均 HTTP200、attempt1、stream_error null。逐份解析 SSE，message_start/message_delta/message_stop、content block start/stop 数量和响应 byte count 全匹配；模型别名 slime-actor、stop_reason、输入/输出 usage 与 response/adapter 全匹配。26 份 adapter parsed 的 text、thinking 和全部工具参数逐项等于 SSE；总 usage 为 input408214/output8058，usage.json 与 CC 合计一致。

SSE 和 CC assistant 共 63 个 content block，其中 62 项精确匹配；唯一差异为 request seq9 / block ordinal22 的 Edit，CC 在原参数上补 `replace_all:false`。首请求 Edit schema 明示 default false，其余字段全部一致；此差异属于 CC 工具默认值补入。

26 个工具调用与 26 个 tool_result 的 ID 集合精确对应：Bash12、Read8、Edit6，3 个 tool_result error 保留。25 个 tool_use 停止、1 个 end_turn；第1次 generation 同时含两个工具。CC num_turns=27 是不同统计口径，不能当成第27次 HTTP 或重复样本。CC2.1.205，终态 success/is_error=false/end_turn，harness RC0。原 trajectory 与 harness trajectory 逐字一致：410 行、351,383 B、SHA `319ff9c8954cb7969128b9a1d2247c160f8348f741762f329b85ceeb6dec4ac0`，stderr0，solve57.368秒。依据为 [gateway 日志根](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1/services_qwen_code8_v1/qwen36/gateway/next12-v1/gpu1003-conan13403-qwen36-a1)、[adapter turns](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1/services_qwen_code8_v1/qwen36/adapter/gpu1003-conan13403-qwen36-a1.turns.jsonl)、[原 trajectory](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-conan13403-qwen36-a1/attempt/trajectory.jsonl)。

## 完整正式参考、退出、PID 1 与清理

[完整 eval log](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-conan13403-qwen36-a1/grading/eval_logs/evallog_gpu1003-conan13403-qwen3_80d72cf3.eval.log) 为 36,752 B、SHA `d28ac963eb33e810397b8f34a1f9a0ec3b4e152c441c3a564a7f4a7da8909569`，与 report eval ref 完全一致。安装段和测试段首尾 marker 全闭合，原 RH2_INSTALL_RC0、RH2_TEST_RC0、candidate exec0；trusted prerequisite verified，runner integrity 未变。实际正式命令为 `pytest -n0 -rA conans/test/unittests/tools/gnu/autotools_test.py`，collected1/raw parsed1，唯一正式 F2P `conans/test/unittests/tools/gnu/autotools_test.py::test_source_folder_works` 为 PASSED，P2P为空，无 missing/skipped/unaccounted。原 report、grading status、result 同事实：1/1 F2P、0/0 P2P、resolved/raw1。该已注册正式分母事实不证明 issue 的整体修复语义，也不把 actor 自测数量补入正式分母。

注册原 entry RC0，结束时间14:34:42.056812Z。[精确 PID 1 原 journal](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1/diagnostics/QUEUE_QWEN_NEXT12_V1_gpu1003-conan13403-qwen36-a1_before/current_terminal_evidence_v3/journal.jsonl) SHA `925c72e9d1c81a10a2b90f8ac34d16ee9fe2c36c2100bcf3fb1b85d11db01660`，精确 UNIT `rh2-gpu1003-conan13403-qwen36-a1-qwen-next12-v1.service` 的 `_PID=1`、同 invocation 的 `unit_log_success`/`Deactivated successfully` 时间14:34:42.081002Z，确认真正终止。success.json SHA `c3704cb0ce73e49519ac5f915516348b34bc51abeb404bd21d561083cf41e655`；退役 unit `LoadState=not-found / inactive / ExecMainStatus=0` 的默认状态不单独作为退出证明。

pre-drain stop residual0，gateway revoke=true/active_requests0/drained=true 与 session_close 一致；quiescence 再次 residual0，workspace 双读 digest 稳定。actor container_rm0，剩余 container/network/relay 标签集合空且 failures 空；grader manager created/removed 总数1/1，containers_open、supply_open、cleanup_failures空，regrade0。最后资源切片无本 job 容器。两层 cleanup_ok 一致。

## 资源与结论边界

[资源原切片](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-conan13403-qwen36-a1/qwen_next12_closed_v1/gpu1003-conan13403-qwen36-a1/resources.jsonl) 共14个，范围14:31:36.449721Z至14:34:52.414178Z，最大间隔15.093062秒；actor/relay/grader各出现6个切片，记录 IDs 与实际镜像对应。采到的 memory.peak 为849,715,200 / 27,766,784 / 299,503,616 B，pids.peak25/7/8，采到 oom/oom_kill均0。grader diagnostics 的 peak_memory_mb=320.645 来自其单独测量窗口，不与切片值混作同一测量。

**采样间隙仍未知**，14切片不能证明连续完整运行树、engine/adapter cgroup、整作业峰值或效率；权重身份和预算边界限制如上。上述限制不构成本次执行/运输窄核的新增阻断，但必须随复用结论保留。七维总核、候选语义和配对 ACK 由题主另行处理。

结构化同源结果：[执行核查 JSON](non_author_13403_qwen36_a1_execution_review_20261003.json)。报告只新增本 MD/JSON，未改冻结原件或共享记录。
