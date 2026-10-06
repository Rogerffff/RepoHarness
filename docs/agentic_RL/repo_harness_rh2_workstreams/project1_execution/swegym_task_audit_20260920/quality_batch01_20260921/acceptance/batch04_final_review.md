# 第四批三题根验收

2026-09-21。**接受本批静态交付：3条完整角色链，1个受限候选、2个先诊断项，3项CPU方案未执行。** 逐题仍是 `needs_review / static_review / development_diagnostic`，不代表正式模型探针或训练准入。

| 任务 | 根核对后的处置 |
| --- | --- |
| DVC4185 | 先诊断。题面明确要求解决未变真值参数的commit误报和false的status误报；gold只改fill_values。根已追完整继承及commit/checksum路径，支持前一症状仍未修复的强静态推断。先base/gold重开Repo的双症状对照，不删题面要求迎合gold。 |
| mypy16869 | 受限静态候选。gold修StarExpr打印，原六项确有2失败→6通过；公开`_Ts`的默认私有过滤是既有行为，不能直接称crash未修。Unpack等价输出可能被精确文本拒绝，需先证明候选导入、类型参数语义与旧行为正确，再归因拒绝；不能仅凭pyi可解析。 |
| Moto6114 | 先校准评分。新增ARN调用只验结果数量，未验目标身份；根核了对象插入顺序与直接序列化链，支持“返回首个对象”的具体错误候选。尚未运行它，不能称已得满分。用同账户/区域的真实已存在ARN即可，不武断扩大未知ARN输入契约。 |

根直接读三份最终review、全部原题/gold/test以及上述关键源码；DVC此前核查见[中期记录](batch04_interim_review.md)。另抽核六条历史日志：DVC51实际节点，gold49P/2skip、noop7F/42P/2skip；mypy六项、11 workers，无本次skip；Moto35项，gold全过、noop仅目标失败。DVC两侧setup.py均有Moto pin预改，已确认并列为共享环境条件，不能称pristine base。

[元数据检查](batch04_final_metadata_check.json)通过：21份逐题文件、9份封存、6个放行顺序、3份最终review、6份历史日志身份；1+2分组与3条未执行队列一致。记录的顺序和摘要支持流程一致性，不证明OS访问隔离。初稿资源单位等表述的更正保留在最终review，封存稿未改。

[独立CPU交接补审](batch04_cpu_handoff_review.md)无设计阻塞。DVC保留recipe、tasks-key bindings、NetworkX兼容wheel和共享Moto pin；另外两题是各自install_wave1原CLI。固定grader诊断与正式actor开发验收分开，镜像/载荷、归档runtime及/work重定位仍是未来准备。

四批累计38题完成静态角色链、21个受限候选、40条选择性未执行CPU方案。第四批不改变[早晨优先清单](morning_cpu_shortlist.md)的前三个开发入口建议；mypy16869可作后备，DVC4185/Moto6114先作语义或评分诊断。未运行任何新项目/测试/模型，未修改原题、生产、评分或历史运行证据，未提交推送。
