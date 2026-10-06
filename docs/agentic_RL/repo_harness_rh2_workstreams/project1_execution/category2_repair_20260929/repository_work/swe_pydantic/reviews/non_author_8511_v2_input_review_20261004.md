# 8511 v2 R26 固定输入独立静态核查（2026-10-04）

结论：**当前 R26 输入不通过，`actual_frozen_input_review_passed=false`。** 发布字节、177 参考、候选来源、安装身份和上传运输吻合，但真实 local prepare 生成的三份测试脚本丢失 `tests/test_dataclasses.py` 参数，执行范围由受审文件扩大为全仓 pytest。这是运行前即可确定的 compatibility 缺陷；正式 CPU 应保持未启动，不能用准备过程的 identity join 成功代替输入通过。

本报告只核新增发布／固定输入／实际 prepare／上传／dispatch delta。审查者此前读过私有 8511 材料、直接行为原件、旧 CPU／actor 与模型材料，**不是 fresh 公开读者**。使用本地标准库读取、SHA/大小、JSON、AST、tar 成员比对和选择器正则重放；未导入或执行作者 helper，未启动 CPU、Docker、SSH、pytest、安装、模型、看板或新代理。材料题义与四个保护测试复用既有独立材料结论，不重做旧矩阵。

## 决定性阻断 B1：真实测试命令丢失文件选择

当前三份实际保存脚本都调用：

```text
pytest -rA --tb=short -vv -o console_output_style=classic --no-header
```

旧 R14 正式作业实际脚本调用：

```text
pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_dataclasses.py
```

| R26 实际 prepare 文件 | 行 | SHA256 |
| --- | ---: | --- |
| `local_prepare_8511_v2_attempt02/eval_script.sh` | 181 | `a62dd4c21f28f054c0386a28d75eea30262a3137b7d245193fd42738b4cbd950` |
| `local_prepare_8511_v2_attempt02/candidate_test_script.sh` | 30 | `7ebfffdbc13afadbed01413e51da4034ae190dce98ebca6715e4ed409bf9a8f5` |
| `local_prepare_8511_v2_attempt02/candidate_test_after_install_script.sh` | 17 | `1f93c485e60172921f393481c3697dbed21e530ec66a17a9129744ff32375026` |

目录前缀为 `runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/`。这些字节分别与真实 status 的七脚本摘要完全相符，不是临时草稿或错误 stdout。

R26 发布代码 `rh2/src/repoharness2/envpack/spec_vendor.py`（15987B，SHA `cc9a3a0ce53dcfc493e4140204e894d75937384e2b4361338be2f8afc020f99f`）第 136、165–192 行只按 `diff --git a/.* b/(.*)` 提取测试文件，第 267 行仍将当前有效补丁传给这条派生路径。8511 v2 补丁只有 `---/+++` 文件头，旧 v1 补丁保留 `diff --git` 头。标准库正则重放给出旧选择器 `['tests/test_dataclasses.py']`、新选择器 `[]`；实际三份脚本直接印证了后果。

补丁可正确应用、语法可解析、保护路径仍是该文件、actor/host spec 相等，均不保证测试命令维持原范围。该缺陷使未来 CPU 可能收集题外测试、遇到题外失败或耗时变化；未执行运行，因此本报告不臆测具体新增失败数或奖励。当前 177 个参考本身没有删改失配。

建议发布方为**精确 8511 v2、固定受审文件路径**恢复选择器，并核其他 263 个 spec 不漂移，封存新兼容发布；新入口需重新绑定发布、prepare、固定输入及上传。原 R26、21 个 source_members、已上传输入和本次错误脚本应保留，不热改历史。当前阻断不要求重做题义或新模型求解，亦不要求本审查者替发布方修改核心。

## 已通过的输入与运输核查

R26 release 为 `cat2-cpu-r2e094095-swe40-pyd8511-fieldinfo-v2-20261004-v1`，manifest SHA `6e20365fcc2eef0489ae259903b52664117e04796597cc4be38af23ab1663f38`。本次逐件核 1528 个真实普通文件的大小/SHA，精确集合吻合、无 symlink；相对直接父发布新增 34、变化 16，均吻合 manifest 列表。这里只核字节，不执行共享检查或宣称全局测试验收。216 个 SWE 公开记录逐字段不变；相对直接父发布只有本题 grading/environment 记录变化。其余任务运行结论未重新审查。

当前 publication_manifest 包含 21 个成员；原件及发布 `source_members` 21 份副本的大小/SHA、字节、精确集合全部吻合。包括现有 14 份材料、材料独立报告、直接行为独立报告及其核收证据，补齐了此前 draft 清单的封包条件。发布目录自己的 publication_manifest 与题内当前清单逐字相等；旧 draft、旧 result_manifest 与原 raw 分数未回写。

固定输入：

- `formal_inputs.json`：73128B，SHA `51a2937c9fdade43eb1f2a035047397837923cbcd60b9c89062cfd3ac8a99d83`，仅任务 8511，8 份资产均逐件吻合。
- `run_formal.py`：22791B，SHA `b127f7309ffae3eae2bbe834c595f846104406e2f858b8073ff2182d0a2ce3c5`，与已核 R14 runner 逐字相同。Python 3.8 AST 可解析，正式评分、清理和预算逻辑没有改写。
- 原 173 个参考序列完整保留，仅追加四个 P2P，共 1 F2P + 176 P2P = 177。顺序为 noop/gold/narrow/qwen_original，预期奖励为 0/0/1/0；这些是新矩阵的固定预期，尚无新正式运行结果。
- 四候选生产源码 SHA 与既有材料独立审查所核应用结果一致。原 Qwen 源负对照的运输补丁、原 FP 副本字节及权威 closed snapshot 原件保持相同；原 FP 单源码解码与补丁应用逐字相等结论复用既有材料报告。本次未重评旧 GPU FP。
- noop/narrow/qwen_original 的 required_statuses 覆盖全 177；gold 保持旧五个指定节点约束，runner 仍要求全 177 参考可解析、分区完整。不能把 gold 的五节点约束描述为新增四节点全部已验证。

公开 digest 保持 `sha256:edc64cdddc65f7fe20b6d9f7fdfd3c8fcfb77dacbd6457010e1a8b06c9d46165`。环境记录只有 `grading_bundle_digest` 从 `sha256:8d81ca96708a0098896c5325e76c003b1507876eaf3425710c1ee57fc3496516` 改为 `sha256:86999e0b2d3effdb5d35c310798d2b86a0ad9be2232c469ed40fa56ab7b993bd`；本次按规范化 JSON 实际重算两者并吻合。公开题面、base、E10 安装全文及资产、wheel 集、core 2.14.5、来源镜像／准备镜像保持。环境整体摘要因该链接变化而改变，不是其他环境字段被改写。

## 真实 prepare 与旧 actor 的有限复用

实际 `local_prepare_8511_v2_attempt02` 的 13 个普通成员逐件核 SHA，包括 prepared_manifest、prompt、rollout view、private host grading、replay_summary、status 与七脚本。公开 view 与发布公开行逐字段相等，private grading 与发布新 grading 逐字段相等；prompt 原值与旧 R14 实际公开 prompt 相等，environment/grading 摘要及材料分区可精确 join。prepared_manifest 声明的一行计数和 SHA、private host artifact SHA 均按原件核对。

status 记录 actor_host_spec_equal=true；本次核真实两侧材料与派生脚本一致的保存证据，没有重新运行 prepare 函数。这一相等说明两侧一致采用了当前 spec，也包含 B1 的错误命令。revision 为 not_evaluated、apply_ok=null、各 partition.result=null；没有把准备阶段伪作测试通过。预算 reset/apply/test 仍为 300/120/1800 秒，hygiene 与旧实际 spec 相等，固定资源／whole budget 仍按原 runner；容器身份、安装和资源只有后续真实 CPU 才能证明。

七脚本中 candidate_install、pre/post observation 三份与旧实际脚本逐字相同。trusted_setup/eval 内嵌有效补丁逐字等于受审 v2 patch；candidate_test、candidate_test_after_install 及 eval 另有 B1 的文件选择变化，不能声称“除补丁外七段均未变化”。

公开 prepared prompt/view 中未出现完整私有补丁、新额外测试源、Qwen 私有运输补丁或新增四个完整参考名。这是固定内容检查，非一般信息流证明。原空失败目录 `local_prepare_8511_v2` 保留；系统 Python 缺 pydantic 的首次失败没有 CPU 启动，随后既有 rh2/.venv 产生了真实 attempt02，未因此重写 frozen input。

旧实际 actor `pyd8511-actor-20261002234027-r14-3deca` 可在**公开输入、base/image/E10/core 与已核公开开发/交付诊断**范围有限复用，依据既有独立 CPU/actor 报告与本次原 prompt/source join。它不证明新 177 正式矩阵，也不为当前错误全仓测试命令背书；不外推新模型能力或 typed 训练接口。status 中“四题实际 actor 仍待”的文字是逐字复用 runner 的历史说明，本报告以旧实际 actor 证据确定这一有限复用范围，不把该模板文字当新的 actor 阻断。

## 上传与派发保护

上传清单 SHA `6b0d35b90cc1aae6e49b44e5bab9bfbbbde5c7aeec7a6593a9400cbec1a4cd1e`，namespace 为 `formal_8511_fieldinfo_v2`。本次核本地 10 个固定 payload + manifest 共 11 个 tar 普通成员：路径安全、无链接，精确集合和逐成员字节均吻合。`8511_fieldinfo_v2_inputs_v1.tar.gz` 为 23587B，SHA `90adf9de4a2720101f9063c28eacbe64432210eae3db25856dc069954efa237b`。

真实上传核读 stdout/stderr 与 owner certificate 的 SHA、RC0、10 payload、manifest、精确成员/SHA 字段吻合；这是已归档远端核读证据的本地复核，没有新远端调用。发布 receipt、cpu-a 部署 receipt、既有 df6c 准备镜像 inspect、题主 1528/21/13 成员核收均绑定于 JSON。部署／镜像 inspect／consumer 模拟检查不替代任务实际容器或 177 pytest。

私有 `dispatch_8511_v2.py` 当前 SHA `e8a58c6a11dde310561043e280504f98c0ba30bf672d7eb91c18e88a8ee419b6`。静态核其固定 task=8511、唯一新 namespace、一次 CPU slot 调用、当前固定输入 SHA 绑定，以及要求本报告顶层 `actual_frozen_input_review_passed is True` 的闸门；本报告写 false，因此当前入口会在派发前被拒绝。任何 cpu_sequence_hold/cpu_infra_hold 存在仍返回 75，未删除或清除 hold，无自动循环或预算升级。当前无本地 hold 也不使错误输入取得派发资格。package/verify/local prepare/generator 只静态读与 AST 核，未执行。

## 后续条件与不可外推范围

唯一当前输入阻断为 B1。修复发布返回后只需核受影响 consumer 与实际新脚本／发布绑定的 delta，确认文件选择恢复，并保存与封包新输入；无需重做既有材料全文、旧 GPU 轨迹或题外矩阵。

当前新 177 四行正式 CPU=未执行；原 Qwen GPU FP 的 v2 安装与 177 参考补评分=未执行；新模型采样=0。此前三变体四个直接 Python 行为诊断不是 pytest/formal 177 评分。旧 173/raw1/ACK、原 FP 与历史原件保持。ordinary GPU probe ready=false、训练资格=false；本静态报告不授予实际 GPU 镜像兼容性、权重身份、typed 接口或新模型能力证明。

本报告只创建自己的 MD/JSON；所有历史材料、R26 发布、已上传输入和错误脚本原件均未修改。JSON 附带本次真实绑定、逐 script 差异、源代码行与标准库正则重放结果，供新 delta 复核。
