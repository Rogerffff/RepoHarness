# Pydantic9066：CPU 最终结果

2026-09-29。**正式noop 0／gold 1均有效；gold修好IP默认值，却使标准dataclass默认实例的schema生成报错。同一gold完整源码获1并破坏有文档的普通模型组合，按v1 §4第4步记S1/T2；G1不是“题目无解”的结论。**

| 正式候选 | reward；F2P；P2P | 完整原测试 | 安装rc／秒；测试rc／秒 |
| --- | --- | --- | --- |
| noop | 0；0/2；367/367 | 2 failed、380 passed、1 skipped、1 xfailed | 0／4.927；1／7.150 |
| gold | 1；2/2；367/367 | 382 passed、1 skipped、1 xfailed | 0／4.620；0／6.218 |

全部369个来源参考逐ID在原日志出现一次。两个F2P为`test_default_value_encoding[IPvAnyAddress-default_value0-expected_schema0]`及`[IPvAnyAddress-default_value1-expected_schema1]`；noop分别遇IPv4/IPv6无法编码，题面non-serializable-default警告在测试警告配置下成为失败，位置准确。gold两项过、367 P2P过。完整原日志384节点与冻结parser计数376分列，不拿总数替代参考；1skip是Python3.8的`test_literal_types`，1xfail是既有`test_get_pydantic_core_schema_calls`，均非来源参考，其余非参考13项PASS，无额外失败。安装后core2.16.3、pydantic2.7.0a1和/testbed导入确认。

actor原例实际缺default并捕获精确警告，随后目标断言rc1，旧IP九项过。私有gold生成`default:'127.0.0.1'`且不再警告，旧九项仍过。普通标准库dataclass `D(x=1)`作为`Model.data`默认值、配置固定`{}`：base正常生成`default:{'x':1}`、D定义/引用且无警告；gold在**model_json_schema调用**抛`PydanticUserError`、code=`type-adapter-config-unused`。模型默认实例在此前已可构建，不能把失败归到类型注解或实例创建。

公开`docs/concepts/dataclasses.md`“Use of stdlib dataclasses with BaseModel”明确支持该组合，`json_schema.py`的encode_default公开职责是编码字段默认值。这里是单字段、标准类型、合法默认值和默认配置，不需要罕见配置、非法输入或内部mock。gold新增TypeAdapter并传非None配置触发已有禁用条件，却未捕获此类错误，导致整个schema失败。因此把G1转为§4第4步S1/T2有具体公共行为与真实得1候选依据，不只是“gold有bug”。新增IPv6是相对原IPv4的非示例，本题不因只测原例记T2c。

实际gold仅导出`pydantic/json_schema.py`，103,620字节，SHA`1dcdfe4f2143ae0b089030c5bc98332f99fd0d686cffa23a9cbeb2ce51126c80`，与private捕获及公开base+输入gold全文一致，candidate.patch也逐字相同；noop导出空。原正式JSON schema模块未覆盖这种标准dataclass默认实例，因此私有回归与正式满分并不冲突。

最小R-c草案保留IPv4/IPv6与不可序列化默认值既有护栏，加标准dataclass默认实例的schema/default控制；不要求内部实现必须用TypeAdapter。gold已不能过新增公开行为，需经独立核实的修复/替代正对照再做版本化正式复验，不据此宣布目标无解或将私有测试直接接入。trusted_setup为296.099／300.853秒，内存峰值原字段824.445／811.203MiB。

## 环境、交付与收口

actor与私有已核范围沿 [actual_partial](actual_partial.md)，历史部分稿不回写。原actor已在UID54321、Python3.8.19下正常执行公开开发路径；private是UID0独立行为。原镜像身份为`sha256:5a05759a5549cc7d65c471fb5d57d8fc554485b6c178a389a1fd373111ff3f4d`，grader为`sha256:53b96f8194676b2732552c3196debd32c02984797a90cb1cfe4a78fbd0c414f0`。核实际13层base全部保留、仅增第14层COPY八个公开wheel；下载日志文件名/尺寸/SHA与登记清单相同，私有1021byte canary未使用。同步不含wheel载荷，本地未重新下载/重算wheel字节。该层恢复离线安装条件，不冒称修好了原actor已观测故障。

本题两份正式安装均editable构建/安装成功，并按候选pyproject读取testing/testing-extra；安装失败命令为空、完整分段标记齐全。初始锁文件/pyproject dirty保持原记录，候选只导出目标源码，不把元数据初态变化算进gold。runner摘要前后相同、测试段完整、缺参考0。实际grader UID54322、2CPU/4GiB、deny_all；预算审计setup300→900秒，test1800/whole3600不变。

本题两次candidate removed=true；原driver日志最后manager_close均创建/移除各1，open/supply/internal与外层cleanup failures均空，final exit0。checked receipt已与原日志逐字结构对齐；不只凭campaign状态认定清理。resource_facts仍null，不从峰值外推全生命周期无OOM、CPU利用率或最低内存要求。

## 当前用途与剩余项

可作问题定位；能力比较为conditional：须核实际完整公开材料交付、共同题单/预算/有效分母，并预登记对所有原reward1候选统一检查同一公开语义，原分数与语义pass/fail分列，不能仅用原分数判胜负。**当前不进训练或留出。** gold的真实回归不等于题目目标无解；不能为保住gold而放宽有公开依据的断言。需要经独立核实的修复或替代正对照，才可验收后续版本化修订。

D6正式题面/测试修订未实施，私有对照没有进入正式评分。本批未另造退化候选，不能声称额外退化实验已完成。其余真实剩余：实际题面/public_hints交付与自主模型、GPU/模型/预算、跨题关系及训练/留出划分、真实难度/成本；完整pip-check和全生命周期资源观测未覆盖。

本人已核全部本题正式参考、实际源码、安装和清理；[root冻结parser](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/pyd9066_final_v1.json)已读且与原件一致，[跨包actor/private复核](../../reviews/reserve6_pydantic_behavior_review.md)已完成，[正式原件及最终卡独立复核](../../reviews/reserve6_pydantic_final_review.md)已完成，无新增阻断。两题联合 [传输SHA对账](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_reserve_pyd_v1.json) 已完成156件／1,361,362字节、0差异，排除wheel/image载荷；当时宿主MONAI仍在运行，不能称全宿主无容器。详见 [evidence_audit.json](evidence_audit.json) 和 [result.json](result.json)。原件根：`runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-9066/reserve6_v1_20260928T205304Z-4f3c46`。


补充 [资源采样](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/resource_reserve_pyd_v1.json)：按真实grading report后缀匹配，noop/gold各21/21份、约15秒间隔，观察峰值分别864,493,568/850,608,128字节；采样期间未观察OOM、OOM kill或PID拒绝。它包含准备阶段，未覆盖完整生命周期，ledger resource_facts仍null；采样峰值与ledger峰值不混为同一测量。
