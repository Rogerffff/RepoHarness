# mypy-10174 新 GPU 镜像原 FP 重评分：非作者反证增量审查

日期：2026-10-03。按 `review-standards.md §10.4` 担任 Falsifier / Simplifier。已见 gold、私有及既有候选上下文，**非 fresh 公开读者**。只核本次新 GPU 的原候选重评分，不重做原模型轨迹、CPU 矩阵或已验未变源码的全审。

本次仅只读本地原件、计算 SHA、解码 FP、静态读取 worker／冻结 consumer、比较 census／材料并解析日志。未 SSH、运行 CPU、容器、模型、测试或项目代码。唯一写入为本报告，旧报告、raw、request 和验收均未修改。

## 结论与有限用途

**没有可证实的新 finding；支持本次原候选在指定新 GPU 镜像上的安装及四参考重评分完成。** 原 FP、完整 baseline 和 50 路径投影含 49 cache 保持；实际 editable 安装成功，正式四参考在 Test Output 段真实通过。结论不由 status 布尔、最后安装 RC0、done 或 systemd not-found 的默认 RC0 单独推导。

本次 job 为 `gpu1003-mypy10174-qwen36-originalfp-80418df-regrade-a1`，重用原 `gpu1003-mypy10174-qwen36-a1#p1` 候选；**不是新的模型生成或 Qwen 样本**。它补充原候选在新 GPU 权限镜像上的实际安装证据，保留原 GPU editable RC1 和 CPU r16 的不同身份、条件及历史边界，不回填旧 raw1。

已验的候选语义与四参考含义按 [原安装反证报告](non_author_10174_gpu_install_falsifier_20261003.md) 复用。此次未发现材料／代码行为矛盾需要修题、扩 CPU、重模型或新增准入条件；最低处理是登记下述身份和证据范围后停止。

## 闭包、handoff 与执行侧输入

固定入口：[新 GPU 闭包 manifest](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/mypy10174_original_fp_newimage_regrade_v1_closed_manifest.json)，SHA 独立重算为 `89d51f9ee836c2d594ab2ffe6909f4dbdfa09ec113db3667d4ebe2dadf9f26b2`。其列出的 **79/79 文件** SHA／size 全匹配，合计 281,562 bytes；实际证据根为 `runs/ordinary_gpu_probe_20261002/remote/mypy10174_original_fp_newimage_regrade_v1/`。

期望来自 [题主 handoff](../python__mypy-10174/gpu_original_regrade_handoff_20261003.json)，文件 SHA 为 `438ed2b1a98d59812ccadbc62fa37793e276aeb6a6f618ee0e6ee60ea8dbf3ae`。其原 FP、baseline manifest／tar、projection、prepared manifest、host grading、prompts、rollout views、原 input_check 九项 SHA／size 本次均独立匹配。

`plan.input_sha256=fcb6d2…` 的定义也已核清：它绑定 [执行侧 inputs JSON](../../../../../../../../runs/ordinary_gpu_probe_20261002/tools/regrade_mypy10174_original_fp_newimage_v1_inputs.json)，完整 SHA 为 `fcb6d2abdce3fd4e9fbebfa0c8faeda3abe7422916c48b0013a4ecab920840a7`，不是 handoff 文件 SHA。该对象嵌入的完整 handoff 与题主对象相等，`handoff_ref` 另行绑定上述 handoff 文件 SHA／size。其 22 件固定输入均核 SHA／size 匹配；code8 项按 worker 的 `physical()` 规则读取本地 frozen 对应，未称为本审重新核验 GPU 全部署树。

[worker](../../../../../../../../runs/ordinary_gpu_probe_20261002/tools/regrade_mypy10174_original_fp_newimage_v1.py) SHA 为 `a357d87fd8697438d149b70c5bfd944efa42a8f5805172d08ca1ba6ae7bc3c80`。`controls()` 固定 inputs SHA、任务／runtime、原候选、供应文件、镜像和投影；`construct()` 只更换 grader image，比较其他输入字段、脚本 digest 和原 frozen binding，然后调用正式 manager.grade，未调用 actor／模型入口。日志 hook 先保存收到的 exec 结果，再委托原 callback；未修改结果或强制参考 PASS。

## 原 FP、完整 baseline 与 49 cache 真正保持

| 对象 | 本次独立核对 |
| --- | --- |
| 原 FP | 文件 SHA `d72699b958fc0f688d5e6c4d4fd5e93006bd18c4a4ea86a2f76c998a4bbeae07`；规范化 digest `5772af211384a9828c83dd61c60c96a6447475e34c4b2bfb891f584ac4304664`；51 项内容解码 SHA 全匹配，含 49 cache、`mypy/meet.py` 和候选测试改动 |
| 完整 baseline | manifest 规范化 digest `337be5fc6ed9a5013249a17bcfb9e48cf7dce2aa3ca27cb4b8b9fd9f0efb7172`；tar SHA `714753b01aff10c04468da922f8e9e6bccb3e02223de96209cd9f532d7688437`；1,472/1,472 条目内容和规范化可执行 mode 匹配，无额外 tar 路径 |
| 新旧 projection | 字节完全相同，SHA `8d61762ccbf5de9a0a3667d7e1cac48cd81d686b0246298843118d4133f8c77d`；50 项全部保留，其中 49 cache、1 个 `mypy/meet.py`，原候选测试文件排除 |
| 重建原件 | exec 003 的实际 baseline census stdout 与原 `baseline_census.txt` 字节相同；exec 005–054 恰好 50 个 delta_write，全部实际 exit_code 0。未清掉 49 cache 或把 50 项改为只评分一个源码文件 |
| 候选源码身份 | 静态 FP／baseline 的 `meet.py` SHA 为 `fda3ae751b225a484400198ff560bbaab9ec56d0dc5f54e3b2846a85c103a0a7`；build／checkexpr SHA 分别为 `24b5aa12e8f65e38f386af201f7cb4aaa4844e9dcbdd409048b6dea6dd938f4e`、`7489e688d1168dfde2c522a0cc70ccaf52c744f3f80940f081e2dd2217b76321`，均与 handoff 期望匹配 |

exec 004 的 cache normalization 发生在 candidate delta 前，随后 50 次写入；不能把此阶段标记解释成候选 cache 已被删。formal 普通四 case 的非 incremental／临时 cwd／cache `/dev/null` 条件及既有 cache 影响判断按未变 baseline 和原审查复用，不因 cache 数量重开审查。

exec 056 原件实际显示候选 meet 的同一四行改动；可信 setup 恢复 base `check-expressions.test`，SHA `faf0a2a1512eba689901ec6a4df57bc1be9183d2616f6846c8dc9ada181884ec`，随后干净应用在用私有 patch。exec 057／058 回执为恢复／预期／实际测试文件 1/1/1，apply RC0、无缺失／不规则，保护 1 文件与 3 目录。候选自己的测试修改没有替代正式 oracle。

## code4 → code8：树不同，本题行为未见改变

对照保存的 code4 与 code8 source manifest：声明文件数从 529 到 1,045，共有路径中 12 件 SHA 变化，包括 manager、若干 consumer 和普通入口。**不是同棵 runtime，也不能把全部差异描述为只改 metadata。** 本审没有复审所有新增任务 consumer。

本题四件材料的声明 SHA 在两树相同，且 code8 本地冻结实字节逐项匹配：effective patch `91ea4e97…`、registry `a49edd07…`、original patch `342a257b…`、可信公开测试 base `faf0a2a1…`。相关 code8 manager／spec_vendor／swe_material_revisions／material_revision／entry 五件实字节亦与 source manifest 匹配。保存的 code8 manifest SHA 为 `09ddb8bfdeecd3ffaa38c1048a574161ef6fa6053b2855da50166e8e8677899d`。

本题实际 [input_check](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/mypy10174_original_fp_newimage_regrade_v1/input_check.json) 与新旧 diagnostics 的 **完整 grading_revision 对象相等**，含材料 identity `dca86b80c83f2e2e9c4eee8c4375952adef834008ad4cb7006ac60abeca58065`、三个分区、四参考、parser、command、状态及逐参考结果。实际 generated scripts digest 仍为 `f111e77dbc1a70b7d469cdb656034aa59c701e9ead3b2ef31e7fa0bd3a45d4ed`；worker 在供给 manager 前也验证该 digest。`candidate_prerequisite=null`，没有借其他题新增条件拒绝本候选。

独立递归比较新旧 tasks 配置，唯一字段差异是本题 `grader.derived_image`：原 `32f313c82fd4f065517b8fd1faff22b79a8c1c8e108200c85c8de8188191baad` 改为 handoff 指定的 `80418df01e0544855bbba9d858a53e45089320ed650bc4b1eb05e91bbf33880f`。actor 仍记录原镜像是来源配置，不能据此认为新 grader 用了旧镜像或新起 Qwen；preflight image inspect 与 diagnostics 实际 image 均为新 80418df 镜像。

以上支持本题行为相同的限定解释；本次 runtime 全树兼容、其他题语义及部署逐文件验证不由此推出。

## 真实安装与正式四参考

[原始 eval](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/mypy10174_original_fp_newimage_regrade_v1/eval_logs/evallog_gpu1003-mypy10174-qwen36_62794c38.eval.log) SHA 独立匹配 `e63a6bb3b5d32a6c714e8df02fa8eb02253aed4e7d94c31d4d2c3288d2a7ecc4`。candidate 完整 stdout 同时保存在 [exec 061](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/mypy10174_original_fp_newimage_regrade_v1/exec_logs/061.json)，其实际 exit_code 为 0，stdout 是 eval 的完整对应片段。

- eval 426、462、491 行实际执行 handoff 的三条原 vendor 安装命令。requirements 与 pytest 安装输出完整；editable 安装真实完成 build dependencies、metadata、构建 wheel、卸载与安装，490 行有 `Successfully installed mypy-0.820+dev...dirty`。ERR trap 在三命令间有效，没有 `RH2_INSTALL_CMD_FAILED` 记录，也没有 Permission denied。三条成功命令未独立输出数值 RC，不能冒称新 GPU 拥有 CPU r16 那种逐命令 RC 回执；这里依据完整成功正文、无失败 trap 与安装段完成。
- 实际测试 command 与旧版相同：`pytest -n0 -rA -k` 后接在用三个选择项，其中 `testUnimportedHintAny` 同时选择其 Lower 变体。原件收集 9,423 项、取消 9,419 项、实际选择 **4 项**，不是执行全套 9,423 项。
- 530–534 行恰列四个不同 PASSED，summary `4 passed`；535–538 行测试 RC0。独立解析 Test Output 段得到节点集合恰等于 handoff 四参考；FAILED、missing、skipped、额外节点为 0，不能只从宽选择器名称推断覆盖。

| 完整节点后缀（前缀均为 `mypy/test/testcheck.py::TypeCheckSuite::`） | 正式分区 | 原始结果 |
| --- | --- | --- |
| `testOverlappingAnyTypeWithoutStrictOptional` | 原 F2P | PASSED |
| `testUnimportedHintAnyLower` | 原 P2P | PASSED |
| `testUnimportedHintAny` | 原 P2P | PASSED |
| `testStrictEqualityWithFixedLengthTupleInCheckWithoutStrictOptional` | 新 P2P | PASSED |

[diagnostics](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/mypy10174_original_fp_newimage_regrade_v1/eval_logs/evallog_gpu1003-mypy10174-qwen36_62794c38.diagnostics.json) 的四分区结果、parsed=4、outside=0、缺席／跳过空与独立日志解析一致。runner 前后 SHA 均为 `2f4655b6933a219bb88c823bdc724ed84e84c89a2a23b39c1f399cb1da2b61c4`。包入口观测为 `/testbed/mypy/__init__.py`、版本观测 `?`；安装正文另提供具体版本。新包没有 pytest 进程内目标模块 loader 探针，不把静态候选 SHA 或旧 CPU 独立 Python probe 写成新 GPU 该采样已存在。

## not-found、journal 与成功范围

闭包保存的终态为 `LoadState=not-found`、`ActiveState=inactive`、`MainPID=0`、`ExecMainStatus=0`。**已收集的 transient unit 的默认 0 不构成本次进程成功退出的独立证明。** `journal_invocation="-- No entries --"` 也不构成按 invocation ID 核验成功。

保存的 unit journal 明确记录 08:52:21 UTC 启动本次 `regrade_mypy10174_original_fp_newimage_v1.py --execute`，08:53:57 UTC `Deactivated successfully`；与 report 的 08:53:56 UTC 完成时间相邻，支持这个 unit 时间窗内执行流程正常结束。journal 的 6.904s CPU time／92.8M memory peak 是服务统计，不是候选容器或 GPU 全程资源统计。

成功范围还须收窄：worker 的 `actual_test_completed` 只要求测试 RC 是整数，并不要求为 0；reference accounting 只要求四参考都有结果且无缺席／重复／跳过，不要求全部 PASS；退出条件也未强制 reward1。因此 **journal 成功和 done 只证重评分流程完整结束，不能替代测试成功证据**。本次四 PASS 来自上节原 eval／exec，非由 worker 的成功标签反推。

manager 回执创建／移除各 1，open／supply／cleanup_failures 均空。preflight 04 按本次 label 查询剩余容器为空，05／06 与执行前保存的两既有 Coder 服务、默认三网络场景相同。这支持本次所有资源的清理范围，不表示整台机器没有其他服务。`resource_facts=null`、`env_qualification=absent` 原样保留，不新造 HostConfig、训练或留出资格结论。

## 旧证据分别保留与停止条件

| 记录 | 实际身份与可复用范围 |
| --- | --- |
| 原 GPU raw1 | `gpu1003-mypy10174-qwen36-a1`，原镜像 32f313…；editable RC1／Permission denied，后续安装导致最后 RC0，但原四参考通过。此次再读原 diagnostics 仍明确记录该失败，原 result 和固定输入 SHA 匹配，未回填安装全过 |
| CPU r16 | `mypy10174-gpu-original-regrade-r16-20261003T003832Z-5650b3`，CPU 镜像 `9d63f1ddcbd277fa62d49e10d800908cfec54544e890fc5fe741d2101ca8eb7e`；前置三 install RC0后正式脚本再安装，有预热，独立 Python probe非 pytest in-process。原 [CPU 验收](../python__mypy-10174/gpu_install_revalidation_acceptance_20261003.json) 的这些边界继续保留 |
| 本次新 GPU | 原 FP／原 baseline／原投影，grader 新镜像 80418df…、runtime code8，完整实际安装和四参考成功；本包未插入 CPU r16 那组三条前置预验安装。没有新 solver 轨迹或模型样本，不重写原 FP 的 runtime 来源身份 |

停止条件已满足：闭包和固定输入匹配、50 项供应及完整基线、同一候选和材料／脚本、真实三安装正文、四参考、可信恢复／保护／runner、服务成功范围与双层清理均有相应原件。**最低接续是题主登记这一窄重评分结果及边界；本角色不提出追加运行或准入要求。** 将来只有实际发现输入身份、材料、参考或行为矛盾，才按其具体影响复核。
