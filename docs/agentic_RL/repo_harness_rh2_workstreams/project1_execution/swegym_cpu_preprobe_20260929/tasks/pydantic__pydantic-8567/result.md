# Pydantic8567：CPU 最终结果

2026-09-29。**正式noop 0／gold 1均有效；gold修复公开序列化原例，却破坏普通Custom+PlainValidator的类构建。按v1，另有直接成立的S1/T2a：正式目标仅核Python输出为str，没有直接核公开JSON结果或serializer精确返回值。G1不能单独代表题目无解。**

| 正式候选 | reward；F2P；P2P | 完整原测试 | 安装rc／秒；测试rc／秒 |
| --- | --- | --- | --- |
| noop | 0；0/1；158/158 | 1 failed、164 passed | 0／4.683；1／3.497 |
| gold | 1；1/1；158/158 | 165 passed | 0／4.325；0／3.423 |

全部159个参考ID逐名在原日志出现一次。唯一F2P `test_plain_validator_plain_serializer` 的noop准确失败在 `isinstance(True, str)`；gold通过，全部158 P2P通过，另外6个非参考节点也通过，没有额外失败、skip或xfail。正式命令是原 `tests/test_validators.py` 整模块，未运行私有Custom控制或相邻serializer模块。安装后core2.15.0、pydantic2.6.0a1、/testbed导入均确认。

公开原例在actor上内部False/True不变，Python/JSON均为`{'x':'0','y':true}`，精确目标断言rc1。私有gold均修成`{'x':'0','y':'1'}`；base/gold旧validators六项与serializers六项均通过。然而默认配置下`Annotated[Custom, PlainValidator(lambda v:v)]`在base可构造、保留输入对象；gold在**class定义**抛`PydanticSchemaGenerationError`、code=`schema-for-unknown-type`，精确指向Custom。公开PlainValidator文档说明取代内部验证，gold无条件调用内层handler造成该回归；不是配置、core或异常匹配错误。

实际gold仅导出`pydantic/functional_validators.py`，23,628字节，SHA`cbdbf0cf4557b0a2012621781a6a3c6e375d6821b12e939e5f6f6cb35363a5dd`，与private捕获及公开base+输入gold全文一致；candidate.patch也与输入逐字相同。noop导出空。私有和正式观察的是同一源码候选。

严重度不靠推断Custom组合的使用频率：公开题面明确展示JSON并要求serializer生效，但来源新增测试只断言两个Python值是str，既不核JSON也不核函数的精确输出；原参考未补这个组合的决定性判据，按§4第1步为S1/T2a。Custom回归另记G1实测；未为其自动添加T2b（本批没有独立退化候选）。严格示例泛化也不因原例通过而解除。

最小R-c草案是两排列同时核内部验证值及Python/JSON精确serializer结果，再补一个不同serializer/输入的公开非示例；保留PlainValidator接管普通类型的构建控制。gold能过前者但已不能过后者，须独立核实替代正对照后再验收正式修订，不能把私有后检称为D6已修好。trusted_setup为294.625／299.456秒，内存峰值原字段821.629／805.301MiB。

## 环境、交付与收口

actor与私有已核范围沿 [actual_partial](actual_partial.md)，历史部分稿不回写。原actor已在UID54321、Python3.8.19下正常执行公开开发路径；private是UID0独立行为。原镜像身份为`sha256:abbc218b579f2221817266e312e8df981459ee1cea4e5bc4f4b120942c62cf7a`，grader为`sha256:b11ee14bd5a90957da5bcb6ef7e09d9ae4db6421b9b8ec36cfdd1b98f43299e9`。核实际13层base全部保留、仅增第14层COPY八个公开wheel；下载日志文件名/尺寸/SHA与登记清单相同，私有1021byte canary未使用。同步不含wheel载荷，本地未重新下载/重算wheel字节。该层恢复离线安装条件，不冒称修好了原actor已观测故障。

本题两份正式安装均editable构建/安装成功，并按候选pyproject读取testing/testing-extra；安装失败命令为空、完整分段标记齐全。初始锁文件/pyproject dirty保持原记录，候选只导出目标源码，不把元数据初态变化算进gold。runner摘要前后相同、测试段完整、缺参考0。实际grader UID54322、2CPU/4GiB、deny_all；预算审计setup300→900秒，test1800/whole3600不变。

本题两次candidate removed=true；原driver日志最后manager_close均创建/移除各1，open/supply/internal与外层cleanup failures均空，final exit0。checked receipt已与原日志逐字结构对齐；不只凭campaign状态认定清理。resource_facts仍null，不从峰值外推全生命周期无OOM、CPU利用率或最低内存要求。

## 当前用途与剩余项

可作问题定位；能力比较为conditional：须核实际完整公开材料交付、共同题单/预算/有效分母，并预登记对所有原reward1候选统一检查同一公开语义，原分数与语义pass/fail分列，不能仅用原分数判胜负。**当前不进训练或留出。** gold的真实回归不等于题目目标无解；不能为保住gold而放宽有公开依据的断言。需要经独立核实的修复或替代正对照，才可验收后续版本化修订。

D6正式题面/测试修订未实施，私有对照没有进入正式评分。本批未另造退化候选，不能声称额外退化实验已完成。其余真实剩余：实际题面/public_hints交付与自主模型、GPU/模型/预算、跨题关系及训练/留出划分、真实难度/成本；完整pip-check和全生命周期资源观测未覆盖。

本人已核全部本题正式参考、实际源码、安装和清理；[root冻结parser](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/pyd8567_final_v1.json)已读且与原件一致，[跨包actor/private复核](../../reviews/reserve6_pydantic_behavior_review.md)已完成，[正式原件及最终卡独立复核](../../reviews/reserve6_pydantic_final_review.md)已完成，无新增阻断。两题联合 [传输SHA对账](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_reserve_pyd_v1.json) 已完成156件／1,361,362字节、0差异，排除wheel/image载荷；当时宿主MONAI仍在运行，不能称全宿主无容器。详见 [evidence_audit.json](evidence_audit.json) 和 [result.json](result.json)。原件根：`runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-8567/reserve6_v1_20260928T205304Z-725caa`。


补充 [资源采样](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/resource_reserve_pyd_v1.json)：按真实grading report后缀匹配，noop/gold各20/20份、约15秒间隔，观察峰值分别810,450,944/725,540,864字节；采样期间未观察OOM、OOM kill或PID拒绝。它包含准备阶段，未覆盖完整生命周期，ledger resource_facts仍null；采样峰值与ledger峰值不混为同一测量。
