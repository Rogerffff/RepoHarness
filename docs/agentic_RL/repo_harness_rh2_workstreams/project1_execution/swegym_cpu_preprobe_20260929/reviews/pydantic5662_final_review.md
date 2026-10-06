# Pydantic5662：完整CPU结果跨包独立复核

2026-09-29。**支持题主的S1误奖结论：any_only正式得1分，但题面明确要求的一般自定义比较委托仍失败。** 未发现足以推翻本次误奖归因的公共依据、补丁身份、执行收口或清理缺口。该结论不依赖“gold能过新断言，所以新断言就是需求”。D6未实施，后检不是正式评分修订，也不授予训练／模型资格。

审查顺序：先读本批actor/private/正式原件及导出patch，再核原公开user_prompt、base源码和文档，随后对root冻结parser逐参考输出查找原日志状态，最后读题主result.md。本审查者未编写该题输入与题主结果；复用当前上下文和此前脚本窄审，不称新盲审或OS隔离证明。未执行远端、容器或项目。

## 公共依据是否足够

原公开材料根：`runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-5662/`。`user_prompt.txt`不仅给ANY例子，还明确要求兼容自定义比较类、不调换比较左右顺序，并解释对方`__eq__`应能处理BaseModel；side note反对先转dict后使对方收不到模型。故普通返回True的Matcher是该明确一般要求的最小实例，any_only将它判False已足以证实欠修。无需把示例类名、具体内部代码形状或gold作为唯一标准。

base `pydantic/main.py:540–561`的非模型分支直接False，同时保留模型类型、值、私有属性与泛型origin规则；`docs/migration.md:38`明确模型不等于字典，既有`test_comparing`及`test_model_equality_dump`也直接约束这点。因此all_nonmodels_equal破坏dict行为有独立公开依据。

本次诊断还检查三个Matcher被调用一次且收到原对象，以及False/NotImplemented结果。这些有正常反向比较协议的上下文，但**误奖结论只需题面直接支持的true matcher不应被阻止**，不靠对“精确一次”等更窄实现观察加码成立。题目不强制具体重排代码，也没有新增性能阈值；本次未据gold输出扩展这些要求。

## 四候选原件对照

证据根：`runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-5662/followup_20260928T182457Z-a73f19/`。

| 候选 | 私有执行的公开比较／旧测 | 正式F2P / P2P | reward与完整测试输出 |
| --- | --- | --- | --- |
| base/noop | ANY及true matcher均false，七旧测过 | 0/1；127项过 | 0；1 failed/141 passed/26 skipped |
| gold | ANY/true为true，false/unknown/dict/object为false，三个matcher收到原模型，七旧测过 | 1/1；127项过 | 1；142 passed/26 skipped |
| all_nonmodels_equal | 六项全true，dict/object护栏失败，旧测2失败5过 | 1/1；125过2失败 | 0；2 failed/140 passed/26 skipped |
| any_only | ANY为true，但true matcher仍false；matcher均未调用，七旧测过 | 1/1；127项过 | 1；142 passed/26 skipped |

正式F2P只有`tests/test_main.py::test_equality_delegation`，noop的完整failure显示只在`MyModel(foo='bar') == ANY`失败。any_only恰好把非模型分支改成`return other is ANY`，因此命中该例而未修一般委托。all_nonmodels_equal则被两个P2P（`test_comparing`、`test_model_equality_dump`）拒绝；它得0不能否定另一个示例特判的误奖。

四份ledger安装rc0、install_failed_commands为空、test段完整，test rc依次1/0/1/0；原日志均有editable构建和pydantic2.0a3安装完成，core0.27.0、导入`/testbed/pydantic/__init__.py`，runner前后摘要相同。逐候选四组128参考状态均在完整原日志找到对应状态；缺席和参考外失败为0，26个skip不在正式参考内。测试输出总数和parser规范化节点数不能代替128参考分母。所有eval日志SHA与ledger相符；候选清理removed=true，四份grade日志manager_close无open容器或cleanup failures。

## 候选真实字节与私有收口

gold、all_nonmodels_equal、any_only正式`candidate.patch`逐字等于对应task_inputs；SHA256依次为 `ce7da319f8273e96339afb5f8bce3bc6076d8f3f9f41741c5860aeb2b6a8c2fc`、`cf14e5bafc662cf37eb2b4d227db0b20e21eb41ba5274ab6a880279390d107a8`、`f889a2d5f579b5e3237c1702f8774355251dda97bac32f5f3bda0cfa598fa05f`。

另用纯文本hunk重建检查（不导入项目）核验三份`frozen_patch.json`解码的完整`pydantic/main.py`，都逐字等于公开base加对应patch，且仅该文件被导出；noop entries为空。any_only导出源码SHA为`9d0025db2036e6163f6e5543bbfbccb7eebbe4adf3a3a2d0219c12d6bc77479b`，证实不是只拿输入文件名推测实际候选。

四个私有变体身份/core与prep、collect-only均通过；matrix完整记录两命令的begin/end、实际行为RC和variant complete，rm/query=0且remaining空。matrix本身rc0代表预期对照完整，不代表每条业务断言都通过；any_only的public_comparison实际rc1且有明确delegation失败marker。私有root权限不能代替actor身份验收。

actor原件显示UID54321、CC2.1.205、Python3.8.19、同base0346ddb6…与core0.27.0，三工具命令完整，原比较精确复现、七旧测过；已有pdm.lock/pyproject.toml改动保留为镜像初态，未混作候选补丁。实际Devcheck控制消息仍不能证明完整题面/public_hints交付。

## 对题主结论及后续处置的复核

读完原件后对照`tasks/pydantic__pydantic-5662/result.md`，主要事实与限制一致。支持保留当前原reward，并把私有一般matcher审计另列；不将any_only称完整解。现有`task_inputs/pydantic__pydantic-5662/public_commands.json`的`public_comparison`及`public_existing_tests`可复用为窄修订草案，其中普通true matcher直接有题面依据，dict/模型护栏有base契约依据。正式接入属于尚未实施的D6，不能把本次诊断当作它已落地。

本次独立结果复核已完成；题主文档中“跨包独立复核/root重放尚未完成”是出稿时状态，应由题主收束。其余保留项包括正式输入交付、用途与受限比较预登记、训练/留出划分和模型/GPU授权，不在本次证据范围。无需为了证明任意比较对象都正确而追加全仓或无界验证。

冻结parser依据：`runs/swegym_cpu_preprobe_20260929/analysis/pydantic5662_followup_v1.json`。本稿独立核过其逐参考状态对应原日志，不重新执行parser或历史项目；本批资源ledger峰值约682–686，resource_facts缺失不补零。
