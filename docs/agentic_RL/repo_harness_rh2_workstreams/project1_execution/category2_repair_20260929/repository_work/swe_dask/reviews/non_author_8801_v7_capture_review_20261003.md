# Dask 8801 v7 诊断采集独立窄核

2026-10-03。材料：`dask8801-behavior-semantic-v7`，最终测试 SHA `06c7d090bedc9f8c5e0afec11ae4b76195d7d7761395ff29d35c40ebdeceb816`，协议 SHA `e5ba9f2ebb71855a724813f6ea07ff8c6d5f81d6cfa6d2e4ac7ebf7515bb5557`。

**本次发现的六项具体采集／投影问题均已由题主修复，并通过有限复核；最终版本未再现这些阻断。** Python 3.9.6 的标准库小检查、协议校验、合成导入及静态材料一致性检查通过。该结论只覆盖采集实现和材料拆分，不代表 v7 已完成正式 CPU、完整 Dask、P2P、语义校准或普通探针准入。

本核为非作者审查：没有修改作者代码，没有执行远端 CPU／SSH 或真实 Dask 评分，没有另派子代理。仅写本报告与同名 JSON；临时合成模块在本机临时目录创建并清理，关闭 bytecode 写入。已看过历史 gold 和作者材料，不能充当新鲜语义裁决者；**未读取 `semantic_controls`、留出内容／标签或 judge 输出。** 本次只读取固定裁决提示本身，不对实际候选作语义裁决。

## 当前授权与目标

以[管理线程的题级裁定](../../../overnight_watch_20261003.md#dask-8801-的题级裁定)为当前依据：保留“加载失败、指名坏文件、真实解释内容问题”的公开目标，采用确定性行为、受信事实与可见诊断、新鲜非作者子代理语义裁决。缺证／不确定不默认奖励 0 或 1，也不剔除困难样本。本安排仅用于本题诊断，未授权自动训练 reward。

[revision](../tasks/dask__dask-8801/revision.json)和[矩阵](../tasks/dask__dask-8801/acceptance_matrix.json)明确保存 `raw_behavior_score_separate`、`automatic_training_reward_authorized: false`，正式 ingest／material digest 仍为空。v6 原件归档，标为已知误接受、未采用。有效题面字节与归档 v6 相同，未因拆分降低公开目标。不同消息不再作为原因正确性的替代。

## 采集和材料实际核查

1. **Python 3.9 对应性。** 使用本机 `/usr/bin/python3` 3.9.6 编译协议、构建脚本、本机检查脚本及当前有效测试。实际验证显式 cause、未抑制的隐式 context、`from None` 隐藏 context，以及 3.9 不显示手工 `__notes__`。Python 3.9 没有内建异常组；采集器通过 `getattr(builtins, "BaseExceptionGroup", ())` 安全跳过。本机 3.12.13 的附加检查验证重复引用同一异常对象的内建组保留两项。
2. **可见诊断。** 最终采集保留消息、显示类名、运行时支持的 notes、可见链和内建组成员；不附 traceback 帧、源码或 locals。`displayed_type` 与 3.9 `traceback.format_exception_only` 的显示类型一致，核过 builtins、`__main__`、其他 module 及嵌套类。[提示 v2](../tasks/dask__dask-8801/semantic_judge_prompt_v2.txt)允许描述性类名承载原因，又不因类名自动通过、不要求特定异常类。路径和原因允许位于链的不同层，没有恢复 v6 的最外层格式限制。
3. **导入 wrapper。** 当前 `IMPORT_CAPTURE_PROGRAM` 安装 hook 后直接 `import dask`；hook 先调用 `sys.__excepthook__` 保留原始 stderr，再发送消息封包，不吞异常、不把非零退出改成成功。本机 3.9 合成 `dask.py` 抛带 cause 的异常时，退出 1、原始 traceback 在场、恰一份消息封包；成功导入退出 0、无异常封包。有效测试仍断言非零退出，并保存加前缀的原始 stderr；宿主只消费独立协议行，不将源码／stderr全文送语义裁决。**合成模块不是完整 Dask 验收。**
4. **协议完整性。** 六个 fixture 的目录／直接文件入口共 12 例，完整范围另加 str 的新进程导入，共 13 例。合成完整集合得到 `complete`／13 inputs；17 种缺失、重复、损坏及深 JSON 输入均得到 `needs_evidence`，没有异常逃逸或默认 pass。超限采集也转为缺证封包。
5. **宿主事实。** `trusted_facts` 从宿主冻结的 `FIXTURES` 字节、SHA 和解析类别构造，不采纳候选消息中的“文件不存在”或候选封包中的解析结论。宿主核 schema、case 集合、before／after 的确切布尔类型、内容 SHA 和诊断 shape。before／after 是受信测试端的采集证据，不是候选给出的原因证明；实际运行的材料／测试／日志身份仍须由外层 consumer 绑定。冻结解析说明不要求求解者逐字复现参考 loader。
6. **材料一致性。** 在内存中回放当前 test patch，产物精确等于 `effective_test.py`。六个内联采集函数的 AST 与当前协议一致。相对归档 v6，34 个非目标函数 AST 完全不变，包括原权限函数；仍为 2 F2P、43 P2P。语法坏及四类非映射仍须实际抛错，空／注释／null／文档分隔符及不可读条目保持既有行为。路径和内容原因交给诊断侧裁决，不把行为分 1 称为目标通过。

## 发现、复现与修复核销

以下均先消息反馈题主，由题主修改；本审查没有替作者实施。旧版本结论保留，不回写历史原件。

| 问题 | 可复现触发与原结果 | 当前核销依据 |
| --- | --- | --- |
| 损坏字段类型 | 初版协议 `ab883549…e69fa`：`visible_predecessor.relation=[]` 抛未捕获 `TypeError`；`capture_issues=None/False/0/""` 反而被当完整 | 当前 relation 先核字符串，issues 必须精确空列表，事实字段显式核布尔类型；5 种坏 relation、6 种坏 issues、2 种整数冒充布尔均 `needs_evidence` |
| 文件别名丢失身份来源 | 旧 `alias_diagnostic` 将实际坏路径和原文仅有 `BAD_FILE` 都变成同一诊断，语义裁决无法辨别是否指名实际文件 | 当前一次 regex 扫描，原生标记转为 `UNMATCHED_LITERAL_TOKEN[hex]`；真实路径／独立 basename 才插入身份；不同目录 `a.yaml`、`mega.yaml` 不误映射 |
| 组成员重复误当循环 | 本机 3.12：`ExceptionGroup("same twice", [e, e])` 的第二项被全局 seen 丢掉，Python 实际会显示两项 | 改递归路径 stack；当前保留两项且无 issues。3.9 目标无内建组，本项是扩展运行时的采集一致性 |
| 编码超限冒作行为失败 | 17 层 cause、每层 64000 字符：采集本身无 issues，但旧 encoder 的总限额导致 `emit_diagnostic` 抛 `ValueError`，pytest 可因此失败 | 当前 emitter 将编码失败变最小缺证封包；用 18 层复核，无异常逃逸、封包含 `diagnostic_encoding_error:ValueError`，校验 `needs_evidence`。保留限额，不将缺证称为求解行为错 |
| 3.9 深 JSON 未捕获 | 协议 `bec2ed81…3ff09`：1100 层 JSON 在实际 3.9 抛 `RecursionError`；同深度在本机 3.12 没报错 | 当前 decoder 显式捕获；实际 3.9 的 3000 层独立协议行得到 `needs_evidence` |
| 描述性异常类名被删除 | 旧输入对 `ConfigurationRequiresNamedValuesError(path)` 与 `FileDoesNotExistError(path)` 完全相同；v1 提示还排除类名解释 | 当前 `displayed_type` 保留两者差异；v2 提示按全部可见诊断判断真实性。核标准 3.9 显示格式一致，未在本核代替新鲜子代理判定候选 |

关键复现方法可独立重建，均只用合成对象，不依赖留出标签：

```python
# 同消息正文、不同的实际可见类型，采集不能合并
class ConfigurationRequiresNamedValuesError(Exception): pass
class FileDoesNotExistError(Exception): pass
assert visible_exception(ConfigurationRequiresNamedValuesError(path)) != \
       visible_exception(FileDoesNotExistError(path))

# 原生占位词不能冒充真实文件路径
assert alias_diagnostic("BAD_FILE: detail", aliases) != \
       alias_diagnostic(actual_bad_path + ": detail", aliases)

# 3.9 损坏 JSON：base64 包装 {"nested": + '['*3000 + '0' + ']'*3000 + '}'
# 与完整 13 例协议行一起输入 validate_packets(..., "full_import")，应 needs_evidence。
```

同名 JSON 保存各次问题版本、实际有限检查结果及完整版本绑定。没有使用模型语义裁决来核销以上采集缺陷。

## 完成范围与剩余验收

这次可以核销已复现的采集／投影代码阻断，并继续按管理裁定开展 v7 验收。以下仍未由本报告完成：

- 原镜像／正式 consumer 的安装、实际 2 F2P／43 P2P 在场和退出状态，真实非 root 权限，以及完整 Dask 的新进程导入。原环境准备或旧测试通过不替代本次材料版本的正式验收。
- 原目标 pytest／运输是否完整保留 13 份独立封包、没有摘要截断／重复；原始运行、材料和日志 SHA 的绑定及清理。`validate_packets` 校验内容，不单独证明哪次 CPU 作业产生了它。
- 固定 v2 提示的新鲜非作者正负／留出控制校准，以及每份实际模型候选的完整独立裁决。本核不知道这些输出，不声称任何新语义通过率。
- 裁决输入 ID 与输出 ID 的确切覆盖、缺失／重复／未知结果及引用核查。`combine_diagnostic_outcome` 只合并已校验的状态／verdict，不能自行证明每个输入都有裁决；外层须先确认全覆盖，才可传入完成标志。
- 消息上限、链深上限或捕获错误保留为缺证；没有证明任意未来诊断都能采集或被正确理解。3.11+ 的组只核小组与重复成员，不声称大组显示截断等全面兼容。本机标准库检查没有加载真实 Dask／PyYAML 环境；额外尝试独立 YAML 解析因当前本机解释器无 PyYAML 未执行，不把这一点混作候选失败。

当前授权是题级诊断安排。即使未来行为与语义均通过，也不由本核授予自动训练 reward、GPU 资格或训练资格；正式用途按现行准入标准另核。没有因这些剩余项新增 CPU 执行审批。

## 最终关键版本

| 材料 | SHA-256 |
| --- | --- |
| `config_diagnostic_protocol.py` | `e5ba9f2ebb71855a724813f6ea07ff8c6d5f81d6cfa6d2e4ac7ebf7515bb5557` |
| `effective_test.py` | `06c7d090bedc9f8c5e0afec11ae4b76195d7d7761395ff29d35c40ebdeceb816` |
| `effective_test.patch` | `c808f4567abaf736189fb361badc1450e9f600975a5ec5bae40f6ed710f7e854` |

其余材料 SHA 与字节数见[同名 JSON](non_author_8801_v7_capture_review_20261003.json)。
