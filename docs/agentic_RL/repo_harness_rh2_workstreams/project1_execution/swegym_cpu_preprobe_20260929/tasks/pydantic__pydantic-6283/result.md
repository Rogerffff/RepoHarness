# Pydantic 6283：CPU 结果（2026-09-29）

**正式校准为noop 0／gold 1／validate_construct 0，退化候选被现有无验证构造护栏正确拒绝，本次未发现其误奖。** 这不解除严格示例拟合S1/T2c：新增核心相等断言仍只覆盖42示例。当前可作诊断，独立结果复核及root冻结parser重放已完成；受限能力比较仍须实际题面交付/预算核验及预登记语义审计；不进训练或留出评测。

| 正式候选 | reward；F2P；P2P | 完整raw测试 | 失败的实际含义 |
| --- | --- | --- | --- |
| noop | 0；0/1；38/38 | 1 failed / 40 passed / 3 xfailed | `RootModel[int](42)` 与 model_construct(42) 不等，准确复现 |
| gold | 1；1/1；38/38 | 41 passed / 3 xfailed | 本轮参考全部满足 |
| validate_construct | 0；1/1；36/38 | 2 failed / 39 passed / 3 xfailed | 相等原例已修，但 test_construct/test_construct_nested 重新验证可信Base64字符串，真实ValidationError |

三份正式原件逐一核过全部39个参考ID（1 F2P + 38 P2P）、每个实际状态与日志SHA；失败均在正式参考内，没有以pytest总数替代参考分母。gold和退化candidate实际导出都仅main.py，完整字节等于精确公开base加输入patch，patch SHA也对应；noop导出为空。gold只避免给RootModel写入extra/private占位属性；退化则调用正常构造器并执行验证。正式失败直接满足公开model_construct文档“no other validation”的违例判据，不是仅凭reward 0归因。

actor以UID54321完成4个逐ID配对Bash调用。Python3.8.19/core0.42.0，源码从/testbed加载，base `a29286609e79c79b2ecd71bc7272eea43ed9fccd`；初始pdm.lock/pyproject.toml修改已原样记录。显式RootModel子类的原例打印`ROOT_EQUAL False`后准确触发`PUBLIC_ROOT_CONSTRUCTION_EQUALITY_FAILED`；旧root测试41通过3xfail，共享construction测试44通过。原始capture完整，prelaunch/activation通过，actor容器/网络/relay/stub清理均正常。devcheck控制消息不能证明正式题面/public_hints交付。

| 私有变体 | 原例 | RootModel旧测试 | BaseModel共享构造 | 无验证行为 |
| --- | --- | --- | --- | --- |
| base | 失败 | 41 pass / 3 xfail | 44 pass | 保留字符串not-an-int，通过 |
| gold | 通过 | 41 pass / 3 xfail | 44 pass | 通过 |
| validate_construct | 通过 | **2 fail / 39 pass / 3 xfail** | 44 pass | **ValidationError** |

退化补丁将RootModel的model_construct转成`cls(values['root'])`，违反公开docstring“no other validation”。两项原有失败是`test_construct`和`test_construct_nested`：原本可信Base64字符串被重新验证，出现解码ValidationError。私有非整数字符串控制独立触发int_parsing错误。正式结果已核实同两项构造失败；私有非整数字符串控制进一步说明违例来自重新验证，不外推未执行的其它路径。三组独立root容器准备全0、矩阵完成标记齐、rm/query为0且无残留。

固定原镜像ID `24e9c51fedb7dc930796362c90f72e8e7a9c47d9362fa72414c6c6ff8a1a2882`，上游digest `7ddf3102f76c8d212da706eb4aed63f72af60775635b8595e9c88fa4c12b857f`。8公开wheel grader层已构建为`8ad3035c23fbc152383e6cd6f3c96c6e2e30c228b05c0227786fd0db4708f92d`，未使用1021byte canary。actor配额2CPU/4GiB；私有root行为不替正式grader身份和配方验收。

三次安装均成功构建并安装editable pydantic 2.0b3，core0.42.0与/testbed导入已观察，失败命令为空；测试分段完整，runner前后摘要一致。candidate清理removed=true，manager_close没有open容器、supply或cleanup failure。三方2CPU/4GiB、UID54322、deny_all；准备预算审计300→900秒，测试1800秒、全评分3600秒不变。安装分别4.732/4.525/4.548秒，测试1.849/1.850/1.885秒，trusted_setup222.465/167.383/196.993秒。内存峰值原字段687.758/681.199/679.707MB，resource_facts为空；不据此推断CPU利用率或整机容量，没有preown优化层。

## 窄修订草案、用途与剩余项

公开题面要求“同一合法、类型正确的值”经RootModel正常构造与model_construct产生相等实例。R-c草案仅补一个非42实例，例如显式`class TextRoot(RootModel): root: str`，检查`TextRoot('another') == TextRoot.model_construct('another')`；保留已有两项无验证构造护栏。该新实例已在独立私有补充 `nonexample_v1` 实测：base 打印 equal=false，准确失败于 `TEXT_ROOT_NONEXAMPLE_EQUALITY_FAILED`（rc1／0.429秒）；gold 和 validate_construct 均 equal=true 并到达 PASS 标记（rc0／0.409、0.436秒）。固定原镜像、base、core0.42.0及/testbed导入均核对；5项准备均0，三组独立 root 容器 rm/query0且无残留。12件5,249字节原件逐SHA核对无差异。该合法输入不能揭示退化的重新验证问题，因此原有无验证护栏必须保留。它不要求内部__dict__形状，不把所有内部属性相等变成新规范。

D6正式SWE修订入口本夜未获实施授权，本记录未修改题面、测试或评分。公开非示例的 base 负对照和 gold 正对照现已完成；授权后仍须在版本化正式参考下复验noop0/gold1/validate_construct0，核新增断言实际执行、原参考保持、安装和清理，并独立验收。

若后续作受限能力比较，预登记对所有原reward1候选统一核同一构造相等要求的非示例、model_construct不重新验证的公开行为；原reward保留，语义pass/fail/unverified分列。共同题单、预算及有效分母另明确。当前未发现本退化误奖，不代表不存在其它示例特判，也不解除S1。

已完成：[跨包独立结果复核](../../reviews/pydantic6283_final_review.md)与[root冻结parser重放](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/pydantic6283_followup_v1.json)。两者支持本次0/1/0及正确拒绝的归因。非示例补充也已完成 [跨包独立复核](../../reviews/pyd6283_nonexample_review.md)；[实际结果](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/6283_nonexample_actual_v1.json) 与 [SHA对账](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_6283_nonexample_v1.json) 齐全。它只证实这一条非42控制的正负对照，不解除S1/T2c，不等于正式评分已纳入，也不证明新增actor权限；没有全生命周期资源采样。私有补充记录固定patch绑定和apply成功，未捕获apply后完整源码SHA，不能称作整文件字节验收。

剩余：D6入口成本/实施授权及授权后的版本化R-c正式CPU复验；实际题面/public_hints交付、GPU入口/模型/预算；跨题关联和训练/留出划分、真实难度/成本；准备效率另版本观察。已完成actor/private/formal不重复记待办。

证据根：`runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-6283/followup_20260928T184018Z-6ec4ba/`。本目录`evidence_audit.json`包含三方全部参考状态、原件路径/SHA、实际源码字节核对、预算/资源/清理，另保留既核actor/private。重点`grade_validate_construct/ledger.jsonl`及对应eval.log/frozen_patch，与`private_validate_construct/validate_construct/private_matrix.out`对照。历史卡不回写。
