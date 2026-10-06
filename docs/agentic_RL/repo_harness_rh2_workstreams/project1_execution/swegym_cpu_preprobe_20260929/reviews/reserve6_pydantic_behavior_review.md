# Reserve6 Pydantic8567／9066 actor 与私有行为独立复核

2026-09-29。跨包独立复核，非 fresh-blind：复核者已知本批实验方向，但本次先读公开题面、base 与 actor/private 原件，再读题主 `actual_partial.md`。两题部分卡与原件一致，未发现阻断这两段行为结论的证据缺口。**两题均准确复现公开症状；gold 修复各自原例，却各自引入已定位的兼容回归。此结论不包含正式评分、最终质量等级或训练资格。**

## 8567：原例修复与 PlainValidator 回归均为实际行为

运行目录：[reserve6_v1_20260928T205304Z-725caa](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-8567/reserve6_v1_20260928T205304Z-725caa)。公开题面要求 PlainSerializer／PlainValidator 两种排列产生相同序列化。actor 原例内部值为 `[false,true]`，Python dump 与 JSON 解码均为 `{"x":"0","y":true}`，仅在 `PUBLIC_SERIALIZER_ORDERS_FAILED` 断言处 rc1；没有导入、collection 或安装错误伪装成目标失败。公开旧测 validators 6 passed／158 deselected，serializers 6 passed／70 deselected。

私有 base 重现相同症状；gold 两种 dump 均为 `{"x":"0","y":"1"}`，内部 bool 不变，原例 rc0。两方相同旧测均各 6+6 通过。私有普通 `class Custom: pass`、`Annotated[Custom, PlainValidator(lambda v:v)]` 控制中，base 在默认配置 `{}` 下完成模型类定义和实例验证，并保留输入对象身份；gold 在**模型类定义阶段**抛 `PydanticSchemaGenerationError`，code=`schema-for-unknown-type`，消息以 `Unable to generate pydantic-core schema for <class '__main__.Custom'>.` 开始。探针捕获并输出该错误后 rc0，只说明诊断完成，绝不代表 gold 行为通过。[base 完整输出](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-8567/reserve6_v1_20260928T205304Z-725caa/private_base/base/private_matrix.out)；[gold 完整输出](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-8567/reserve6_v1_20260928T205304Z-725caa/private_gold/gold/private_matrix.out)。

公开依据不是 gold 输出：base `functional_validators.py:132` 明确 PlainValidator 替代内部验证；`docs/concepts/validators.md:66–70` 明确不再调用内部验证。原实现直接创建 plain schema；gold 新增无条件 `handler(source_type)`，在普通 Custom 上重新要求生成内层 schema，与观察到的异常阶段吻合。因此可确认这一具体兼容回归；不能外推所有自定义类型都失败，也不能把旧 12 项通过当作此路径覆盖。[公开 base API](../../../../../../runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-8567/base/pydantic/functional_validators.py)；[公开验证说明](../../../../../../runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-8567/base/docs/concepts/validators.md)。

## 9066：IP 修复与 dataclass 默认值回归均为实际行为

运行目录：[reserve6_v1_20260928T205304Z-4f3c46](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-9066/reserve6_v1_20260928T205304Z-4f3c46)。actor 的 `IPvAnyAddress=IPv4Address('127.0.0.1')` schema 保留 `format=ipvanyaddress`、`type=string`，但缺 default，出现精确 `PydanticJsonSchemaWarning`：`Default value 127.0.0.1 is not JSON serializable; excluding default from JSON schema [non-serializable-default]`。随后目标断言 `PUBLIC_IP_DEFAULT_FAILED` rc1；旧 IP schema 九项实际全过／373 deselected。

私有 base 重现原例；gold schema 的 IP default 为字符串 `127.0.0.1` 且无警告，原例 rc0；双方旧九项全过。标准库 `@dataclass class D: x:int`、`Model.data: D = D(1)` 的控制固定默认配置 `{}`，在调用 schema 前已确认模型默认实例可构造。base `model_json_schema()` 成功返回 D 定义与引用，`properties.data.default={"x":1}`、warnings 空；gold 在 **model_json_schema 调用阶段**抛 `PydanticUserError`，code=`type-adapter-config-unused`，消息明确不允许给 BaseModel、dataclass 或 TypedDict 的 TypeAdapter 传 config，warnings 仍空。这里 rc0 同样是错误已被准确捕获、报告和核验。[base 完整输出](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-9066/reserve6_v1_20260928T205304Z-4f3c46/private_base/base/private_matrix.out)；[gold 完整输出](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-9066/reserve6_v1_20260928T205304Z-4f3c46/private_gold/gold/private_matrix.out)。

base 的 `encode_default` 公共说明是将字段默认值编码为 JSON 可序列化值，旧测试也有标准 dataclass schema 支持；本次 base 真实成功补足了具体默认实例控制。gold 新增 `TypeAdapter(type(dft), config=config.config_dict)`，空字典仍非 None，触发原有 `type_adapter.py:196–204` 的 dataclass 配置禁用条件；gold 只捕获另一类 SchemaGenerationError，实际错误未被吞掉。该控制检测保留已有公开能力，不要求 gold 特有的内部结构；旧九项为无 default 的 IP schema，不能替代 dataclass 默认实例覆盖。[base 默认值编码](../../../../../../runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-9066/base/pydantic/json_schema.py)；[TypeAdapter 条件](../../../../../../runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-9066/base/pydantic/type_adapter.py)；[旧 schema 测试](../../../../../../runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-9066/base/tests/test_json_schema.py)。

## 身份、源码、完整性与清理

两题 actor 均为原镜像、真实 CC 2.1.205 的固定 devcheck 命令执行，UID54321、Python3.8.19、解释器 `/opt/miniconda3/envs/testbed/bin/python`，导入 `/testbed/pydantic/__init__.py`；private 为独立 UID0 容器，不能替代 actor 权限证据。8567 core2.15.0／HEAD8060fa1cff965850e5e08a67ca73d5272dcdcf9f，实际 image `abbc218b579f2221817266e312e8df981459ee1cea4e5bc4f4b120942c62cf7a`；9066 core2.16.3／HEADa3b7214a1d6ac8e32c29e9d4436ea6a9e253ead7，image `5a05759a5549cc7d65c471fb5d57d8fc554485b6c178a389a1fd373111ff3f4d`。对应 private 实际 image 与 actor 相同。初始 `pdm.lock`、`pyproject.toml` 两行 dirty 已保留，不能称全树干净。

逐条核 actor 原始 tool_result、captures、attempt 的 ID／退出状态／字节长度一致；8567 四条、9066 三条全部完成，trajectory 文件分别 26,596／21,993 字节，与记录一致，result success，stderr 空。prelaunch 与 activation 通过，实际身份输出足以确认 interpreter；attempt 的通用 `interpreter_in_tool_result=false` 与 `bashenv_denied_for_agent=false` 仍保留，不将所有 checks 概括为 true。`all_match_expect=true` 包含原例预期 rc1，不等于题目已修复。两题原 actor 已可开发，后续 COPY wheelhouse 的 grader 准备不能改称已观测到的 actor 环境修复。

私有 base／gold 准备步骤分别为 8567 的4／5步、9066的3／4步，全部 rc0；先收集非空旧测，再执行完整矩阵，所有子命令与变体尾标记齐全。两题输入 gold 与 `remote/gold/reserve6_v1` 正式生成补丁逐字节一致。独立纯文本逐 hunk 重建（未执行项目源码）后，实际私有目标文件 SHA 与 base／base+gold 全文匹配，避免只凭 apply rc0 判断补丁生效：

| 题目／源文件 | base SHA-256 | gold SHA-256 |
| --- | --- | --- |
| 8567 `functional_validators.py` | `15003cbbd1349882a64ce994671c223b90259cb791e6b620d97bd4ab1024113b`（23,387 B） | `cbdbf0cf4557b0a2012621781a6a3c6e375d6821b12e939e5f6f6cb35363a5dd`（23,628 B） |
| 9066 `json_schema.py` | `f5b675891b23ab3ce275db9d30f9a871bb01691bd0f4ce60912e14c71950f16e`（103,160 B） | `1dcdfe4f2143ae0b089030c5bc98332f99fd0d686cffa23a9cbeb2ce51126c80`（103,620 B） |

四份 private spec 的实际 SHA 均与 summary 相等，四个完整矩阵输出字节数均匹配记录（8567 base/gold 991／1,545 B；9066 1,190／1,179 B）。该核验覆盖目标源码，不宣称全仓库或全部依赖字节闭环。

actor 清理均 container_rm0、stub_rc0，network／relay failures、labeled container／network leftovers、residual_after_force 均空，结束 agent 进程0。四个 private 变体均 rm_rc0、query_rc0、remaining空、stderr空。这里分别确认 actor 段与 private 段收口；**不借此声称正式 grader 的两层清理已验收**。actor 实际配额2CPU／4GiB，private 规格同值；未核全生命周期资源事件，不给无OOM或最低内存需求结论。

## 与题主卡的对照及剩余范围

最后对照 [8567 partial](../tasks/pydantic__pydantic-8567/actual_partial.md) 与 [9066 partial](../tasks/pydantic__pydantic-9066/actual_partial.md)，核心行为、异常发生阶段、身份、SHA、清理与用途边界一致，G1 从静态疑点转为本次实测的表述成立。G1 本身不自动决定 S1／S2，仍需按标准结合正式评分及公开行为范围归类。

本次没有读在途正式评分并推断分数，也没有改题主材料、执行远端或更改输入。正式完整日志、安装后 core、逐参考状态、实际导出与私有源码跨阶段对账、grader 内外层清理和传输 SHA 总账仍由随后正式结果复核收口。未证明自主模型求解或完整题面交付；不授予比较、训练、留出资格，D6 未实施。
