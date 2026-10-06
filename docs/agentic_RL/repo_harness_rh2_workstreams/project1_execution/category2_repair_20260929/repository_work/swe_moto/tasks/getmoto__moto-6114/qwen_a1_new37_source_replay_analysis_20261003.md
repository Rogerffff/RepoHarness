# Moto6114：旧 Qwen 源码在新37参考下的独立重放观察

2026-10-03。这是固定候选源码的 **新 CPU 尝试**，不是新的自主模型样本，也不回写旧35评分或原 GPU FrozenPatch。

原候选将 RDS 名称与 ARN 查找统一，并让该 helper 同时返回 Neptune 对象。新测试证明它能通过原35项（包括多集群身份断言），但它把两条原有 Neptune 名称路径改成 RDS 的对象处理方式，出现两处行为回退：

- `start_db_cluster` 对初始状态 `available` 的 Neptune 对象套用 RDS 的 `stopped` 状态要求，抛出 `InvalidDBClusterStateFault`。新增保持项在测试第833行、候选代码第2018行失败。
- `delete_db_cluster` 读取 Neptune 对象不存在的 `deletion_protection`，抛出 `AttributeError`。新增保持项在测试第848行、候选代码第2003行失败。

新 R21 作业 `moto6114-cpu-9b1ef9d10723` 完成原 `make init`（退出0），37项全部收集与解析，原35项全部通过，仅上述两项失败。因此实际报告为 `unresolved/tests_failed/reward=0`。安装10.652秒、测试8.414秒；实际准备/reset预算900，仍为2CPU／4GiB／PID512与原其它预算。该次实际可信准备151.281秒，只能说明本次完成，不能据一个样本称扩大上限提升效率或完全消除了超时。

此前 R19 对同源码的尝试在保护300秒超时，安装与测试未执行，仍保留 `failed_to_grade/infra_failure/reward=null`。R19已有效的 noop0／gold1／wrong_first0 保留其300秒准备/reset条件；本次900与它们不是完全相同的预算条件。旧模型首轮raw1、安装2、原35材料及旧物理镜像、冻结工件也各自保持原身份。

新 CPU 固定diff为6463B、SHA256 `bb5eab97577260270def73fc06f8a0aa4917727cb9348afbe871f5905b2eb747`。新 FP 只有一个100644源码修改，完整内容161961B、SHA256 `05e9b6a1d3f57caaeba1a616fa3a1a9529ffa6f6aa6d91be9a5963a239b5171d`，与原未评分候选逐字相同，但使用新的 physical attempt；这不是旧FP改绑。

这次检查支持两条既有行为保持测试的区分力，也再次证实旧候选存在具体回退。不能扩大成“所有 ARN 写操作都应支持”或“整个 Neptune 题目完全覆盖”的结论。新37最终普通探针资格仍由独立 CPU 报告判断；后续应生成本材料下的两个新基座首轮，再读其真实定位、修改和验证轨迹。CPU 的精确镜像900政策不能自动应用到 GPU 的不同物理镜像。

证据：[作者完整读回](../../reviews/moto6114_r21_exact_cpu_owner_readback_20261003.json)、[R19部分独立读回](../../reviews/moto6114_r19_partial_cpu_non_author_20261003.md)。运行原件位于 `runs/category2_repair_20260929/moto_cpu_20261003/moto6114-cpu-9b1ef9d10723_evidence/`；完整日志SHA256 `d4e00f53d8dc699e9c5b441adf7722a8ba0244ce02efb51f8bc2959d1aa28ad9`。
