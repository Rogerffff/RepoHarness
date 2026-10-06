# DVC9395 原 Coder FP 的 CPU 补评分：非作者执行前窄核

日期：2026-10-03。结论：当前未发现阻止按固定 q01 命令执行一次原 FP 正式补评分的实现或输入绑定缺陷。此结论只覆盖执行前身份、构造、运输权限修复及 runner 的静态执行边界；尚无本次候选执行、正式 reward、40 个参考结果或清理验收。旧 GPU 首臂的 entry RC1、cleanup=false、reward=null 保留，不能由本报告改写成候选失败或已恢复。

本审查者已读私有材料与旧诊断、R20 校准和三 Coder 首臂报告，属于获授权的非作者复核，不是 fresh 公开读者。仅用本机标准库读取、SHA256、tar/JSON 和 AST 对照；未运行 runner、候选、评分、模型、SSH、Docker 或项目测试。唯一写入为本报告，未改原件、作者结果或共享代码。

## 冻结来源与候选

本报告用 `P` 指本包，`R` 指 `runs/category2_repair_20260929/repository_work/swe_dvc/dvc9395_same_original_fp_cpu_recovery_20261003_v1`。快照是 `R/snapshot_7c8c9bccd699a74f`；下文路径均为仓库相对证据指针。

- 独立逐项核快照 manifest 的 1092 个成员：所有文件 SHA/大小一致，总计 124663739 字节；tar 有 1093 个普通文件，恰为该成员集合加 manifest 本身，无多项、缺项或内容差异。不是只相信 build_receipt 的总数。
- `source/frozen_code_v8/source_manifest.json` 的 1045 个源码/资产逐项 SHA/size 一致。旧封包没有随附的完整成员来自既有 frozen_code_v8，当前快照对齐同一个 source_manifest，不导入当前工作树源码。这项是源身份校验，不是重审全仓实现。
- 原 FP 文件仍为完整三项：`dvc/stage/__init__.py`、`test_comprehensive.py`、`test_pull_fix.py`。按冻结契约的 sort_keys / ensure_ascii=False / 紧凑 JSON 规则独立重算 canonical digest 为 `sha256:1cad35171d386f0d905859d0232d29d7df9a398872d62e6e71e98ffc8d0cd456`。baseline 同样重算为 `sha256:0c75caa0ac9790c739e0250f37125f342241d19d57bb430e6a6c7fa009acf0ec`；不是仅业务源码 diff。
- baseline.tar 的 SHA 仍为 `6fb7167266118587a8fe0afbce99308f984d5acbca7f088cd4e7c1043d883a61`，FP 文件 SHA 为 `28766ba0af8a312357685ae9ce0206ce318a7d623354e35bf745add478fd9461`，baseline_manifest 文件 SHA 为 `b41f4a530df5841ab7bc6f9c9f9344f4e3bc271649dc50f3345d5a444178d6d1`。原闭合包 manifest SHA 为 `dd3c2b3f578b86c54ea59a8654987dba41befd09028b9e0a7840b238a46b877d`。
- 旧 `failure.json` 与 cleanup recovery 原件仍在快照，SHA 分别为 `18b8cd84ec40427cd5742cce96576715c8f778da9326bf6563fc2c1fd47d5a26`、`c0c5ca097db66ccdcd255987584a346722c2a619ee771fdfbfc57e7a48499c6f`。已有语义意见复用 `P/reviews/non_author_dvc_three_coder_a1_semantic_review_20261003.md`，本次不重新判题、不重采 solve，也不预判补分为 0 或 1。

## 纯构造与运输修复

worker 的 construct（第50—130行）先核固定快照，导入该快照的 frozen code8 entry；任务和 summary 使用深拷贝，只有 `prepared_summary`、`public_notes`、`prepared_dir`、`private_dir` 作物理路径重定位。回退后与旧对象相等是强制条件；拒绝继承任何 `RH2_` 环境覆盖。随后调用原 entry.load_inputs、source_from_original 和原 manager._verify_frozen_delta_binding，不重新导出或改造 FP。

独立对照旧 `source/remote/queue_v27/results/gpu1003-dvc9395-coder-a1/input_check.json` 与 `R/pure_v2/input_check.json`：task/source/solver/budget/public_delivery/assignment/baseline_policy、prepared_manifest、host grading artifact、materials、grading revision、preparation budget policy、grading budgets、runner 和 spec overrides 全部相同。路径重定位使 tasks_config 和 prepared_summary 输入文件 SHA 变化；不声称整个 input_check JSON 相同。模型/服务配置仅供原 entry 构造读取，没有服务调用，service_readback 的 config_only 与 runtime 未验证边界仍保留。

第一次纯构造 exit1，堆栈明确停在 prepared_tasks 的 `_check_private_permissions`：解包后的 host_grading_views.jsonl 是 0644，group/other 可读，被私有 guard 拒绝；未进入 execute，也未创建候选容器。`pure_remote.stderr` 与 completion 均保留。修复脚本只 chmod 冻结清单文件：私有文件 0400、其父目录 0700、其他源文件 0444；每项重算 SHA，manifest/worker/材料/FP 字节不变。运输回执列出的 9 个私有文件（含冻结资产中的其他 private 路径）逐个与快照 manifest SHA 对齐；没有因此扩大本次 grading 的任务范围。0400 满足 guard 的禁止 group/other 访问条件，未绕过或放宽 guard。

pure_v2 命令仍无 `--execute`，真实 completion exit0、stderr 空。pure_check_done 为 identity_constructed_only=true、candidate_executed=false。71 个实际已加载 repoharness2/slime 模块路径均落在该冻结 code8，并逐项与本机冻结文件 SHA 相同；entry SHA 是 `bdf806bf8da1d5ebb4970887bfc3c7738eb3e57a75e1d07215d6d68b17e574c4`，worker SHA 见下表。没有把 CPU runtime 的未冻结依赖包也说成这71个成员已证明。

pure binding 维持材料 `sha256:9d456666b845fd90146499033601805ce2ecdc3d88e26202f8b9855cf287f68a`、revision `dvc9395-behavior-v2-draft`，以及 whole/setup/apply/test = 3600/900/120/1800 秒。镜像为本地构建 `sha256:c093861f62b8071b3c1e5b3142abd5843888421364e69dd728cb80856f621b60`，image_manifest_digest=None；不能填成虚构 registry manifest。预算900来自原精确任务/revision/grading/testpatch/image/requestinput policy，未默认退回300或增加新宽泛豁免。

五条完整脚本分别重算后与 binding 的 SHA 相同：trusted setup `1091fc42bfd9f6933e3433593392ccba5b195da8a7d205e3f324f72f31d0f9aa`；single-shell candidate test `15c9492506cef85542e581bfd03e5ec98a09bf692095dd607f689931a723f177`；install `6f396945330f9c6da69f7dab3a3db681c527ed88390ec77b90d5472aae0f2488`；after-install test `492b2425f83c69243862606873f7090bf8bb98530a4e6fae9dbee1d5adbe0a8d`；eval `3e2ac108748a8a8b5243ffcd3a526afc64a5e4b1291272910738719d48e47c06`。预期实际模式为 single_shell_deny_all_no_supply，digest `sha256:ec5f61cf288b78aaafd469b40013bcd571e93e1ab5db7c32c8852b6a83f035f3`；two-stage digest 只是另一构造身份，不是本次执行模式。完整脚本包括官方测试 restore/base SHA、离线轮子预检及原 pytest 两文件命令；实际 restore/apply、预检与安装尚未发生。

纯构造本机目前回收5份 JSON；worker 还写了 projection.json、tasks.json、summary.json，但它们尚未随此次5份回收包到本机。已依据固定原 FP、baseline、原 source_from_original 与构造断言核绑定；建议实际运行归档同时回收这3份直接产物，便于后续逐项读回投影和路径。这是证据完整性补项，不构成本次执行前阻断，也不能据此声称已验实际 applied projection。

## 静态执行边界与实际预检

新 worker 没有调用 solver 或改评分计算。execute 只新建 manager，给原 grade_submission 传入原 frozen source；supplies=None，固定单壳模式。wrapper 针对本任务观测并加验收 guard，官方 manager/脚本/解析与参考分区不被替换。

复用 Dask 的范围已具体核：本机当前 `swe_dask/tools/cpu_same_fp_regrade.py` SHA 为 `3086fb2e63fdd6c984baf717c1525ce2bdf7f8693ca9954d8cc815cb817f4312`；新 worker 的 resource_snapshot、monitor、start、close、verify、logged 六个内部函数，与该文件 AST（忽略行号）逐一相同。已有 Dask 静态报告 SHA `51dd5d3a651476fb8aaf28c9063ba97c81644151cca172d3a94565b2dde47550` 绑定的旧 worker SHA 是 `30db91df2afd0ad29bbe1fb296ad39e4d1df9653c774b4bb129527ec560bdbcd`，不误称当前 Dask 字节等于旧报告审查版本；新 DVC 构造和任务 guard 已另核。

- 运行必须是 root 且输出位于固定 CPU 包路径，新输出目录排他创建。slot wrapper SHA 精确核对，并要求 running job、child PID=self、supervisor PID=parent、mode=run/package=swe_dvc/command 含 --execute；只认一次唯一 admission。
- 执行前核实际 Docker image 的 Id/Architecture/Os/RootFS/Config 与固定输入相同，并拒绝本 job 已有 owned 容器。启动后再次核 owner/trajectory label、实际 c093、NanoCpus=2000000000、memory=4294967296、PidsLimit=512、NetworkMode=none。pure profile 同样是2CPU/4GiB/PID512、candidate UID54322；Config.User 空值是镜像默认 root，不等于候选以root执行。candidate test exec 另强制 user=54322并运行 id -u 检查。
- 资源观测从实际容器 host PID 的 cgroup v2 路径读取，启动、周期、关闭前采样；对 pids.events max、OOMKilled、memory.events 的 OOM/OOM-kill 保留 guard。不能把纯构造 profile 或本次预检当成候选全程资源实测；5秒样本也不能证明所有瞬时峰值，实际结论必须依据后续 raw。
- wrapper 记录真实 stdout/stderr/phase/user，保留官方 report/diagnostics；normal candidate test失败可以得到0而不自动变成infra。验收另要求 install rc0、test rc为真实整数、非partial、非failed_to_grade/infra/parse问题；四分区的参考列表须与原 input_check 完全一致，结果合计40且不重复，无skip/missing/unaccounted。本次构造是2+1个F、27+10个P参考；完整执行还应另核未计分import节点，不能只看40参考。
- 原 manager 注册容器记录在创建前完成；新 start 的后置 inspect guard 失败仍由外层 manager.close 回收。finally 保存状态、取消资源monitor、bounded close、精确本job label残留查询，并要求 created=removed=1、无open/supply/cleanup failure、固定源末次 SHA 不变。TERM/INT首次取消保留finally；这些异常路径本次只是静态核，未做信号演练。

`R/cpu_preflight.json` 的真实读回显示 dispatch未paused、running_slots为空，slot SHA匹配，实际 c093镜像的不可变Id与RootFS/Config匹配。这是执行前时点事实；正式 admission还需worker运行时重验。handoff receipt记录无同FP评分in-flight/无newsolve，属于授权与协调记录，本审查未访问远端再次探测GPU。

拟执行 launch 脚本固定单次 cpu_slot run/q01、该快照/worker、独立新 grade_v1 输出和 --execute；不循环盲重试。exit75只代表槽忙，不能当候选成绩。它要求本报告存在并记录读到的报告SHA；没有解析报告结论，所以执行者仍须完整读取本报告，而非把“报告存在”当通过判据。

## 读回身份

以下均为本机实际 SHA256，不省略：

|证据|SHA256|
|---|---|
|P/tools/cpu_grade_dvc9395_original_fp_v1.py|46b35703dda5a24441d9548a54e0705287700b4aab6f4cdb019c5a602e2aa664|
|R/snapshot_7c8c9bccd699a74f/snapshot_manifest.json|7c8c9bccd699a74f58041f6e990707e79f07979c712fbbd81c0d6ec731155351|
|R/snapshot_7c8c9bccd699a74f.tar.gz|c4b36aea729a54194bd101e87a0e9f62ad8fc3915b9b50d178a4c3ef94ea9ae4|
|snapshot source/frozen_code_v8/source_manifest.json|09ddb8bfdeecd3ffaa38c1048a574161ef6fa6053b2855da50166e8e8677899d|
|R/build_receipt_v1.json|c969523e38ca34a1cd41fcccfc4533df4393fcb702e80976d22bd24837a40475|
|R/inputs.json|bbf0e27757562e01327c0b9361ae8c2291821fd4f173f6d07cbfee9b42f29818|
|R/cpu_preflight.json|941c7085baf7adb809f771a83d6e7605a254bb875b564709d34bbd1294c4546b|
|R/deploy_receipt_v1.json|7faab0e565082286e22346d7e7c8c8da55f1737b8cdbf091a39502803ce15930|
|R/pure_remote.stderr（首次失败）|22b6ba83253d2d7618b915eaa1a96e49305d5d42144563a68a77e742f672ae8d|
|R/pure_remote_completion.json（首次exit1）|255f4ff381cf3b21ed999e79c9c0da52f5938ed1b0a03ab55c5347e89dce9e8d|
|R/repair_transport_modes_and_pure_v2.py|46a7fc002657c3e5200a4f8514da6adad1c6f67d9e26052221e0821876d5fef1|
|R/transport_modes_receipt_v2.json|ee1cd5b598d379c88dcfe3bb012101eaab7925a7c731eac2164c88b734f54b60|
|R/pure_remote_completion_v2.json|3f9bf162fa5eb212f1e754349e0c35cccc3a7d059fe7b0ab1d820f7c8738fa0b|
|R/pure_remote_v2.stderr（空）|e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855|
|R/pure_v2/binding.json|9408ce22e6c2303be3658298ab4bb1b9350e50f73de105cd9fc7ca42fa2bb260|
|R/pure_v2/input_check.json|ebe41679a498eb8adf9e3d62d0f06ad7da56062ceb2374a12367c9237ab3e521|
|R/pure_v2/complete_scripts.json|210935ae01e26aa630209fe03073f2a6ab8b5924416595910bb369bcad5591b0|
|R/pure_v2/runtime_code_binding.json|4511d9a43e6fafa10c8b1afc511628a6276169bb33498eafa6740fdf882268f6|
|R/pure_v2/pure_check_done.json|b40fc18e9636aead5761df78c95cb023318b5a472aa99d464f161e0e6af02ba9|
|R/launch_formal_cpu_grade_v1.py|ef739c9bfb31d373233162fd5c236ebe6b3a9a72b5185f3cca00ed2af2ef3656|
|R/pre_execute_readback_manifest_v1.json（11指针逐项SHA/size匹配）|065f59fb3f6d4e3fdb31f80289ad94dd9d23200dcb5b75375ab1b1658a435eba|
|R/handoff_gpu_duplicate_check_receipt_v1.json|b7d92eadf2ca5909114cd64d17f836a5d0e1bb9ae8719a0c046d9b979fbb23c2|

本次没有待修的执行前阻断。待实际新run到齐后另写不可覆盖的运行审查，独立重建所有pytest节点/40参考、失败堆栈、真实安装和测试退出、实际UID/镜像/资源与两层清理。当前不授予候选正式评分验收、模型能力结论、训练资格、稳定性或双模型收口。
