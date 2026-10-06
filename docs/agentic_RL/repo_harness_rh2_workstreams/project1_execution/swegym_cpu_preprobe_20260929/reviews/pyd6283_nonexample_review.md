# Pydantic 6283 非示例补充独立复核

2026-09-29，`nonexample_v1`。审查者：MONAI/Conan/Moto 题负责人。只读公开依据、此次输入与已同步完整原件，未重做旧静态审查、执行项目或操作远端；未改题主卡、旧输入、生产或正式评分。

**确认 `TextRoot('another')` 非示例控制的实际结果为 base 相等性失败、gold 通过、validate_construct 通过。它补齐这条 R-c 断言的正负对照，不区分合法字符串上的错误验证构造策略；不解除既有 S1/T2c，不完成 D6，也不增加 actor 权限证明。** 本次输出已经齐全，无需等待或重跑。

## 公开依据

[公开题面](../../../../../../runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-6283/user_prompt.txt) 明确要求：同一合法且类型正确的值，经 `RootModel.__init__` 和 `RootModel.model_construct` 创建的实例应相等。42是示例，不是限定值或限定类型。此次 [nonexample.py](../../../../../../runs/swegym_cpu_preprobe_20260929/inputs_extra/6283_nonexample_v1/nonexample.py) 定义显式 `class TextRoot(RootModel): root: str`，两侧输入同一合法字符串 `'another'`，先核实例类型及 root 值，再核对象相等。该断言直接来自公开要求，没有从 gold 的内部实现反推需求，也没有断言 `__dict__`、extra/private 属性的具体形状。

公开 [root_model.py](../../../../../../runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-6283/base/pydantic/root_model.py) 的 `model_construct` 转调基类；[main.py](../../../../../../runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-6283/base/pydantic/main.py) 第179—183行明确 trusted/pre-validated 数据不再验证。validate_construct 补丁改为调用正常构造器，本条输入本身合法，故其通过不检验也不恢复“不再验证”契约。既有正式0/1/0及两项无验证构造护栏的拒绝结果沿用原记录，本次没有重跑或重新认定它们。

## 身份、准备与精确结果

[summary 原件](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-6283/nonexample_v1/summary.json) 的实际 image 为 `sha256:24e9c51fedb7dc930796362c90f72e8e7a9c47d9362fa72414c6c6ff8a1a2882`，与预登记一致。每组 initial 均为 UID0、base `a29286609e79c79b2ecd71bc7272eea43ed9fccd`；`pdm.lock`、`pyproject.toml` 初始已修改，不冒称干净 checkout。身份准备均确认 testbed Python、`/testbed/pydantic/__init__.py` 和 core0.42.0。base 一个准备步骤、另两组各两个准备步骤，全5项RC0；未在准备失败后继续。

本地输入四文件及远端镜像副本 SHA 均与 manifest 相同；summary 的 spec SHA为 `7409b61ad097cdff07f86c59f22976358ee027f4d087b7130184463dae0ae4a0`。远端镜像中的 helper SHA与 manifest 的 `379c4610b19aafa829fcf7967ad95d0ac9f5374c9e85f16c0b62a01a25cbb7bc` 一致。gold/退化的 git apply RC0已确认，但本补充没有 apply 后整文件 SHA或正式 frozen export，不把 Exit0 写成源码整文件字节验收；身份、准备和实际区别性输出支持下列窄行为结论。

| 变体 | 完整输出关键事实 | 实际退出 | 耗时 |
| --- | --- | --- | --- |
| base | `value: "another", equal: false`；在第16行 `assert same` 抛 `AssertionError: TEXT_ROOT_NONEXAMPLE_EQUALITY_FAILED` | 1 | 0.429秒 |
| gold | `value: "another", equal: true`，随后 `TEXT_ROOT_NONEXAMPLE_PASS` | 0 | 0.409秒 |
| validate_construct | `value: "another", equal: true`，随后 `TEXT_ROOT_NONEXAMPLE_PASS` | 0 | 0.436秒 |

实际命令均为 `python -u /in/nonexample.py`，60秒预算。base 已通过前置的实例类型和 root 值断言，准确失败在目标相等性；不是导入、依赖、准备、超时或其它断言失败。gold与退化没有stderr。输出文件字节数分别251、83、83，逐份等于summary的stdout+stderr计数；未见输出截断。执行器整体0不被当作业务全部0。

## 清理、用途与剩余项

三组独立 root 容器的 rm_rc/query_rc均0，remaining=[]，结束时间齐全；资源配置2CPU/4GiB、network none，未安装依赖或构建新层。root 的 [实际解释记录](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/6283_nonexample_actual_v1.json) 与本次独立读取一致；[远端/本地对账](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_6283_nonexample_v1.json) 12份/5,249字节、0差异，并记录04:33 SGT actual_containers=[]、unit ExecMainStatus=0/inactive/dead。这里没有全生命周期资源事件采样，不外推无OOM或容量结论。

可以将“非42合法字符串的 base负对照/gold正对照已实测”记为已完成。单条新控制不是所有合法类型和值的覆盖证明，且本次在私有 root 容器运行，未成为正式评分测试，未证明 actor 可以执行新增命令或正式模型已收到其内容。validate_construct 仍须保留既有不再验证护栏；其此处通过不能冲销原正式拒绝或把退化重新判为正确。

S1/T2c、D6未实施及训练/留出用途限制保持。若后续获准实施版本化正式修订，应在保留原参考与无验证构造护栏的条件下加入该控制，确认新增断言实际被正式命令选中，并重新完成三方评分与独立验收。本补充只推进断言的行为依据，不替代该步骤。

[小型机器复核记录](pyd6283_nonexample_review.json)保存实际输出、准备RC、清理、范围限制及本地原件SHA。准备时的 manifest/README `prepared_not_executed` 是冻结历史输入状态，未回写为执行结果；实际结论以本次summary和审查记录为准。
