# Dask 8801 v7-compat1 非作者增量材料与宿主接线复核

2026-10-03。适用材料为 `dask8801-behavior-semantic-v7-compat1`，以本页末尾 SHA 和[同名 JSON](non_author_8801_v7_compatibility_review_20261003.json)中的完整身份为准。

**本次有限复核未发现阻断：06:18 SGT 裁定的两种假值处理均保留，10 个兼容分支必须在场，拒绝分支才增加独立诊断；宿主能够接收完整的 13–23 项诊断。** 106 项静态、局部 API 和合成协议／宿主检查通过。可以核销本次增量的材料与接线审查；这不是正式 CPU、实际候选语义通过或自动训练 reward 资格。

审查依据为[06:18 SGT 空值边界裁定](../../../overnight_watch_20261003.md#dask-8801-的题级裁定)、原 public bundle／base config、历史 `ok_falsy_empty.patch`、当前 revision／公开题面／测试／矩阵、r9 原始 API 记录和兼容宿主检查原件，以及指定的四个工具。仅以[兼容修订前归档](../tasks/dask__dask-8801/history/dask8801-v7-before-falsy-compatibility_20261003/manifest.json)核固定差异；旧宿主审查的 adapter `99bb626d…f8d54`／validator `4880feba…e196b` 不被当作当前 adapter 的验收。

本核没有修改作者材料，没有调用真实 CPU、Docker、SSH、网络或语义裁决者。只写本报告和同名 JSON；局部检查使用 `rh2/.venv/bin/python`，实际为 Python 3.12.13／Darwin／非 root。临时文件在本机临时目录创建并清理，关闭 bytecode 写入。未读取任何 `semantic_controls/*expected*`、`*bindings_private*`、calibration／heldout verdict 或作者期待标签文件；配置读取仅限已授权的两个 v3 配置及 prompt 字节 SHA。本核接触过作者材料，不充当新鲜语义裁决者。

## 材料与公开边界

- 用 `read_bytes()` 读取有效题面，再与 public bundle 的 `problem_statement.encode("utf-8")` 比较：前 7,784 字节逐字一致，原 162 个 CRLF 全部保留。不是经 `read_text()` 换行归一化后的相等。新增公开补充明确空文档、仅注释、`null`、空映射合法；其他假值非映射允许空配置或准确诊断失败，不贡献设置且不能错因失败。
- 在临时目录以原 base test 文件实际执行 `git apply --check` 和 `git apply`。产物与当前 `effective_test.py` 字节精确相等。相对原文件的 34 个非目标函数 AST 不变；相对固定 v7 归档，仅 `test_collect_yaml_no_top_level_dict` 的函数 AST 改变。六个内联采集 helper AST 与当前协议一致。
- revision 仍保留 2 个 F2P、43 个 P2P 的节点清单；有效 P2P 精确等于原清单加原有的两个权限参数化节点。这里核的是材料／AST／清单，不声称本轮已跑过全部节点。
- 公开题面没有要求求解者输出新字段或固定诊断措辞。兼容／诊断封包由私有测试输出，输入仍只保留受信事实和实际可见诊断。该结构不将存在异常、文件名或某个关键词自动视为真实原因。

## 两种合理分支的局部重算

没有读取新的候选补丁。第一组实际将已授权的历史 `ok_falsy_empty.patch` 应用到原 base config，提取相关配置函数执行当前测试的 API 部分；第二组在本机临时代码中只将其 `yaml.safe_load(...) or {}` 改成 `None` 才转空映射，用于构造另一种合理处理。两组均未执行完整 Dask 的导入部分。

| 本机重算 | 五类假值的目录／文件入口 | API 诊断输入 | 当前测试结果 |
| --- | --- | --- | --- |
| 历史 `ok_falsy_empty` | 10 个 `empty_configuration` 记录 | 12 个必需 API 诊断，无额外假值诊断 | 两个目标 API 测试通过，协议 complete |
| 合成仅豁免 `None` 的严格分支 | 10 个 `diagnostic_failure` 记录 | 12 个必需 API 诊断，加 10 个假值诊断 | 两个目标 API 测试通过，协议 complete |

另对空文档、仅注释、`null`、文档分隔符、`{}` 五种合法空形式分别直接调用目录及文件 API，两组每组 10 次结果均不贡献设置。接受假值时向结果注入额外配置项，当前私有测试的断言真实失败；不存在“接受分支完全跳过行为检查”。拒绝分支的消息进入独立语义输入；本核只验证其在场和投影，不替裁决者判断内容。

作者 r9 原始记录共 29 行，其中 22 行局部 API 行为通过、23 行 API 采集 complete；两者分母及含义不同。`ok_falsy_empty` 实际记录为 10 个空配置分支及 12 个 API 诊断；`gold` 实际记录为 10 个拒绝分支及 22 个 API 诊断。29 行的 `full_import` 全部为 `not_run`，正式行为分和语义裁决均为 null，因此没有从作者期待标签或局部通过数推论正式结论。

## 协议与宿主增量

构造 11 组完整封包，拒绝的假值分支数依次为 0–10。协议和宿主 prepare 每组均要求全部 10 个兼容记录，诊断数对应为 13–23；固定的第 13 项是坏字符串导入诊断。合成 finish 在 13、18、23 项完整输入上可完成结构合格的裁决。本表中的 verdict 仅为检查夹具，不是实际候选语义。

| 具体故障或状态 | 实际局部／合成结果 |
| --- | --- |
| 漏掉一个接受分支记录；漏掉一个拒绝分支诊断 | 协议为 `needs_evidence`；接受分支漏记录也使宿主 prepare 缺证 |
| 重复兼容记录／诊断；损坏 base64；非法 branch／before／after；整数冒充布尔；错误内容 SHA | 均为 `needs_evidence`，没有异常逃逸或默认通过 |
| 接受分支仍附拒绝诊断；诊断带额外 source 字段／非法 capture_issues | 为 `needs_evidence`，没有把多余材料或非法 shape 送去裁决 |
| 缺少／重复／未知裁决 ID，裁决 results 非列表 | 宿主 finish 为 `needs_review`，保留原行为分 1 |
| 缺少裁决输出文件；一项 `uncertain` | 为 `needs_review`，保留所需数量及原行为分 1，没有降成 0 或通过 |
| 一项结构合格的合成 fail | 为 `fail_diagnostic_semantics`，不改原行为分 |
| 身份不匹配／执行未完成；已完成且行为分 0 | 前两项 `needs_evidence`；后者 `fail_behavior`，不混作缺证 |
| awaiting 的所需数量为 12、24、True、null 或字符串 | 为 `needs_evidence`；合法范围为精确整数 13–23 |

合成 `dask.py` 对坏字符串抛异常，运行当前 `IMPORT_CAPTURE_PROGRAM` 得到真实非零退出、原始 traceback 和一份独立异常封包。有效测试本身仍断言导入进程非零，并保存原始 stderr。这个检查只核 wrapper 没有吞异常，**没有证明原镜像中的完整 Dask 导入已完成正式验证**。

缓存仍按以下六项计算，13 个合成输入的 payload SHA、cache key 和不透明 ID 与公式逐项相等：

```text
SHA256([formal_material_identity, ledger_sha256, eval_log_sha256,
        judge_config_sha256, judge_prompt_sha256, payload_sha256])
```

相同字节的新输出目录复现相同 ID；单独改变材料身份、账本 `run_id`、配置、提示、日志，或可见 payload 均改变 ID。账本／日志 SHA 将实际运行和兼容分支绑定进去；不是仅按候选名缓存。盲输入只有 schema、ID 和语义 payload，合成候选补丁身份与 run ID 没有漏入。validator 与固定旧归档字节相同，本次只重新核与可变数量有关的必要结构故障，没有扩审未变全链。

`judge_config_v3.json` 的陈旧 `prompt_path` 与 `judge_config_v3_bound.json` 的校正路径确实是二者唯一内容差异；模型选择、effort、上下文、版本和 prompt SHA 均相同。两者声明的 SHA 都与显式 v3 prompt 字节 `9d49671b…19c1` 相等。adapter 的实际参数独立提供 prompt 路径，校验实际文件 SHA。本核只核元数据等价；未读取两次实际新鲜裁决的输出或独立证明其运行 provenance，也没有把陈旧历史配置路径当作新增阻断。

作者兼容宿主检查的九项 actual 与其记录相符，其原件绑定当前 adapter／validator／protocol 和 r9 采集 SHA。新独立检查也绑定同一组 SHA。收尾重新读取并核全部已列源文件，字节身份未在本核期间变化。

## 结论的适用范围

本报告完成 v7-compat1 的增量材料及必要宿主接线复核，未发现本范围内需要题主修改的阻断。正式 CPU 仍须验证本次版本在原镜像中的安装、实际 2 F2P／43 P2P、真实非 root 权限、完整 Dask 导入、正式日志运输／身份／清理；实际候选仍须逐 ID 的独立语义裁决和引用核查。合成输入的 pass 只验证结构和状态流转，不能核销这些事项。

本核不证明所有未来诊断措辞均鲁棒，也不授予普通探针、训练资格或自动训练 reward。后端模型／effort 的精确快照仍不由这两个配置文件证明；当前安排保持题级诊断范围。

| 当前材料 | SHA-256 |
| --- | --- |
| revision | `fc74c26b426fdfbdb1924a3ac25d254eb7378b300df672d74e749a6ff8f1121b` |
| effective test | `8257cf66bb3a65181f165cd9ef040b828a0084cf1ca76e9181d6968053a332e7` |
| effective patch | `a0d2794fb43dc920f7dbc00078975b9334a3040d873aa56971256f04f3dd360c` |
| effective statement | `0b3ffb734d5e9f1eac09848d407b0f040913075359563f7717d5f3efb1ce166c` |
| protocol | `7886a70ac59d051eca4459c6e32d94b77159c6890341183041dc73df03d1292a` |
| host adapter | `1a4c9a97470b026772961b9f7981a6f910d9f142e41e5ffbf8ff8c7486a51d12` |
| verdict validator | `4880feba7ace4e133475a8ceeb4d3b23b7d38fff764065e5d69bb59baa1e196b` |
| v3 prompt | `9d49671b56ae155f9183d8a0280ff7e779959de2697cdf3887ba4f558f2c19c1` |

JSON 保存 106 项实际检查、局部 API 观察、29 行原始结果的有限摘要、配置和其他材料完整 SHA、历史适用版本及未覆盖范围；没有保存或推断受禁标签。
