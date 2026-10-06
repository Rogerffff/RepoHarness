# Dask9378 R15 v2 六行正式 CPU 独立验收

依据日期：2026-10-03。结论：`dask9378-mask-route-b-v1` 的实际矩阵 **noop0 / gold1 / toplevel_only1 / ma_mask_none0 / ma_mask_invert0 / wrong_values_seven0** 与用户选 B 的语义相符；本窄核未发现阻断。只确认固定 R15/source050 的六行 CPU 评分，不确认 GPU 部署、模型解题或训练资格，不新增通用准入闸门。

我未参与作者修改或远端运行；已接触私有 gold/旧报告，因此是非作者复核，不是公开盲审。本轮仅本机原件读回、SHA/大小、冻结代码静态追溯、纯模型/spec重建和内存diff校验；未执行SSH、Docker、题目CPU测试或模型推理。仅写此文与[同名 JSON](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_dask/reviews/non_author_9378_formal_cpu_r15_review_20261003.json)，历史审查/作者材料不回写。

## 原件与实际评分

[terminal原件清单](/Users/roger/Desktop/claude-code-verl-stage0h/runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask9378-formal-cpu-c-20261003-v2/remote/readback_manifest.json)的76成员全部逐SHA/大小匹配，合计1,625,734字节，无排除。清单SHA `d4e365a1b8d170fd7f0355d3f6b3f4d6996c32df9394e4be7cc3bce7a25bf2f6`；[固定作者读回](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_dask/tasks/dask__dask-9378/formal_cpu_readback_r15_20261003.json) SHA `ef33eca14921c8e7405654016d1f8e17d9b734469f7af08f6a9297d9a286472f`。以下结果来自原件，不以作者摘要代替解析。

每份eval恰一对Start/End，只解析区间内137个 `-rA` 节点，精确覆盖3F134P，无重复、缺失、跳过或未计入。所有行134旧P2P均通过，分区结果与原ledger相等。JSON保留各行137参考、失败原文、安装/退出/清理、所有原件SHA。

| 候选 | reward / test rc | F2P / 旧P2P | 完整模块 | 实际失败 |
|---|---|---|---|---|
| noop | 0 / 1 | 0/3；134/134 | 3failed,134passed；12.11s | 三项mask全False，预期含True |
| gold | 1 / 0 | 3/3；134/134 | 137passed；11.62s | 无 |
| toplevel_only | 1 / 0 | 3/3；134/134 | 137passed；13.14s | 无 |
| ma_mask_none | 0 / 1 | 1/3；134/134 | 2failed,135passed；12.28s | ones/zeros丢mask；empty通过 |
| ma_mask_invert | 0 / 1 | 1/3；134/134 | 2failed,135passed；11.56s | ones/zeros mask取反；empty通过 |
| wrong_values_seven | 0 / 1 | 1/3；134/134 | 2failed,135passed；11.61s | mask正确，但有效值7而非1/0；empty通过 |

测试按用户B逐函数选择：ma入口存在就验它，缺失才选顶层。三项逐元素比较mask；ones/zeros再比较有效值；**不验empty_like未初始化数值**。noop/丢mask/反转mask在mask断言失败，不能说这些失败用例继续执行了值断言。值7候选已通过mask断言，真实失败于后续值比较；它是本轮新构造，不冒称历史 `invert_values7`。

gold新增ma三个函数，以asanyarray/map_blocks调用numpy.ma；顶层正对照只改creation.py，保持ma入口缺失，条件测试正确接受顶层路线。当前覆盖默认shape/chunks和指定非平凡mask/值，不等于穷尽所有shape/chunks/kwargs，不强制某种修法或新API。原题面已有ma/map_blocks修法建议，保持原文，后续模型探针须披露已有引导。

## source050快照与镜像证据

本机读取[v2冻结archive](/Users/roger/Desktop/claude-code-verl-stage0h/runs/category2_repair_20260929/swe_dask/batch_runs/dask-source-formal-r15-cpu-c-20261003-v2/input_snapshot.tar.gz)，28成员逐SHA/大小与input_manifest相符；这是archive结构/字节核算，未审其它题目语义。snapshot `c58d4ad6fd35eab8`，archiveSHA `891fcaa7f11730934d7a8dd78293f52998fc250020a715e4a97e3f3b7147bcf5`。冻结相对文件名仍 `tools/cpu_formal_matrix.py`，字节SHA **`05080362f74eeba0cfacee4a51c2002a1806d2a387ee571bfb69ca695140e962`**，与当前[独立v2 alias](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_dask/tools/cpu_formal_matrix_source_identity_v2.py)完全相等。本轮config调用此snapshot路径；status保存verify/prepare/六grade均rc0及完整六行，确认新source分支实际运行。

工作区旧 `tools/cpu_formal_matrix.py` 仍SHA `208430d5b5a87121c8473cb209858f95089e2716613325919028dcfa9d55c85d`，没有声称它已修复。旧v1真实noop0/137参考已跑后，被旧208错误config-ID断言中止的历史保留；[旧单行adapter review](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_dask/reviews/non_author_source_image_matrix_adapter_r15_review_20261003.json)只验旧noop且明确当时新050未CPU运行。此新增结论只归本轮v2，不改旧报告。

[source_image_inspect原始JSON](/Users/roger/Desktop/claude-code-verl-stage0h/runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask9378-formal-cpu-c-20261003-v2/remote/run/source_image_inspect.json)恰一项：初始Id `sha256:1e5a0ee850161b35d33d26445f73e872488a45e0e436195af239190b68574096`，RepoDigests `xingyaoww/sweb.eval.x86_64.dask_s_dask-9378@sha256:d59dc8d2aa23abc26c301754af4623f7bbad5d798713a6c5caa2d2113b6691b1`，与expected/spec相符。source helper要求初始Id/manifest组合；逐行要求manifest精确相等、local_build=false、**image_id_actual=null**；六ledger确如此。local_build分支保留严格configID检查。

**初始image inspect不是每个运行中容器configID。** R15 manager逐评分容器先inspect容器`.Image`，再针对实际ID取RepoDigests；缺证/错误manifest/查询失败抛infra错误，调用在setup/安装/测试之前。六行无infra且完成评分，支持这条受信运行期校验通过；这是根据冻结强制路径作出的推断。给定原件没有逐容器`.Image`/RepoDigests raw stdout，不能声称独立取得每个configID或它们均等于初始1e5。binding image_id/source_config_id_inspected仅指初始期望/inspect身份，不回填ledger null。

## consumer、producer与材料

R15 release manifest `2b788d1ce84228a27894e04886ade347e91993f48ddc9bdeeb8f92de4aa92917`；远端verify记录1305成员，本机独立核31相关资产（12题级、producer+3输出、15consumer/契约），未扩大整release审查。producer manifest SHA `9f56ab144ff9a6c8a811a406ab8f799270c5e7981a9fd388ca518165e822692e`；9378 public/grading与实际prepared/host view精确相等。

registry SHA `0bff171663a71176b75371d4e68dcdb1deec3fe520f60c69554d7a3b40b5e1d5`，replace_test_patch_preserve_refs，原3F134P及顺序保持，无新增P。输入revision/matrix/test.patch与archive、release、当前包相等；完整有效测试与release/当前包相等，另由snapshot绑定patch内存应用到固定base测试后精确重建。完整测试文件不作为独立archive成员，不能声称核了不存在的成员。

- base `8b95f983c232c1bd628e9cba0695d3ef229d290b`；revisionSHA `2020dc58319e23c27b289cd68b6b7e147b6de736015876e2f16ea53ed8dbf9d5`；matrix `3274063f9713d20982c84ce0f69a72f3fac6dd589c2b7070c92e8589bb58e9d6`。
- test.patch `9fc1a9d5ae885d9cc30388a875ab7ed629081de7ba7bdcc8571f3aca604a248a`；完整有效测试 `c834df1a5aeb1596ff637ab7bcf79f9001d8b5d347023ca1a60f74d1ec3190e9`；base test `f8cfe68f10e9a71bf12d6fccdf51a8eadedc736b431aac3d9f282f59aa4348b0`。
- grading bundle `sha256:26ae813940ea2b3f8654ba39ecdfc9a5a73c4e7bbe519844321d78fbe132d8e7`；environment package `sha256:ed78bee0067cd35dfd7db0160a60bd195e1ebd0fb464e38e8413759c4d524986`；public `sha256:1c2541744ca463d35e97a1fdd86df8c512787953f5b410a43de3a92d5dfba242`。
- material identity `sha256:2823a332c83a6a37ce56e3cb1816fa7d267788b4616b28f76be8c4896fc915c4`；scripts digest `sha256:973844ec7101c4754a1a0d3ca73815717f75430a80a494d0dcb1d184f68bac69`。

冻结R15模型/spec本机重建与六ledger/binding相符；setup仍原vendor **300秒**，候选安装仍 `python -m pip install --no-deps -e .`，无兼容wheel或新prerequisite。本机未执行安装/pytest。

六份FrozenPatch/baseline的canonical digest精确重算；public/source manifest/base HEAD/projection匹配。五份真实candidate.patch与snapshot字节相等，gold另与source gold相等；每份完整正文逆应用patch回到baseline内容SHA，再应用精确恢复候选正文。ma.py baseSHA `676aeee5df3b1fb270baf3a2bf9db8d57845a61c47394bf59ae86861c1459346`；creation.py `24fd1ff65bbc167461d4cc5202dddee904cfe0b8b030e825638dc126fd22565f`。无测试路径修改，noop无delta。

## 非root、运行与清理范围

六行candidate apply_user为agent/54321，git_sanitize成功/准确HEAD；冻结candidate路径用数字UID，真实patch/artifact相符。policy为54322，冻结manager按其运行安装/测试，prefix owner观测54322。**没有本轮独立id-u/prelaunch，prerequisite=null，没有直接geteuid断言。** 这是ledger/policy+冻结路径及观测证据，不能升级为新运行期UID捕获，历史actor探针不能替代。

root做可信物化/sanitize/权限/官方测试恢复及保护；六setup预期测试1/恢复1/apply0/setupOK1。候选安装/测试沿非root路径；真实安装dask成功、未skip、failed_commands空、install rc0/外层exec0，安装和测试起止标记齐全、segment_completed=true、partial=false；test rc1/0/0/1/1/1，无stage_error/infra/execution_failure_decision。

实际Linux Python3.10.14/pytest8.3.2/pluggy1.5.0；`/testbed/dask`导入/2022.8.0+12.g8b95f983.dirty为观测。六行runner=false/前后摘要相等，是候选身份pytest/_pytest/pluggy诊断hash，不是通用安全证明。policy2CPU/4GiB/pids512/network deny；峰值观测4096/2418.414/2382.582/2351.449/2391.895/2379.352MB，resource_facts=null，不声称新独立cgroup证明或内存余量。

六candidate cleanup均removed=true/rm:ok；每grade manager_close created1/removed1，无open containers/supply/cleanup failures，regrade0，final_status rc0。作业已终止；六行是本轮正式consumer的实际reward，不是旧root私有行为诊断。

## 公开actor与未完成事项

复用旧非作者报告并重新核22公开actor相关原件：历史source config1e5/base8b95/UID54321，Python3.10.14/numpy1.26.4/scipy1.14.1/pytest8.3.2，CC2.1.205；首请求public_hints+problem_statement与当前public字节相等，另一个日期system-reminder保留。公开ones_like原例丢mask/rc1；masked134pass+选取creation-like320pass共454项，后者394deselected，不说完整creation模块全跑；退出/容器/网络/stub清理完成。

历史是同源真实CC配合5个脚本stub请求，没有模型推理；不代表新GPU部署或本轮正式actor。candidate.kind=cc是replay补丁来源标签，不证明模型生成。当前旧revision/card/matrix的pending字段是冻结行政记录，新CPU结论依据terminal原件，不回写历史。

接探针仍需目标GPU/rollout部署image/config/激活/profile与release/public/material绑定，以及真实模型推理轨迹、FrozenPatch和正式评分关联原件，保留题面已有引导披露。六行env_qualification仍absent；训练消费/资格沿主链已有授权处理，本报告不授GPU/训练资格，也不新增泛化闸门。
