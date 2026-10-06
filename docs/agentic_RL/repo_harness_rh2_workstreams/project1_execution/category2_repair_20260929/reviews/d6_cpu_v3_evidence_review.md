# D6 修复后 replay 矩阵独立证据审查

2026-09-29，最终复核。**两题新版 replay 六行全部独立通过，各为 noop0／gold1／C1=0；结合原 actor 两工件直接 fresh-grade 2/2 通过，F1 在当前两题、两镜像、正式 sandbox profile 路径内核销。D6 首片 CPU 题级验收通过，无剩余阻塞。** 原 actor 接缝证据见 [v2 直评审查](d6_actor_to_grader_v2_evidence_review.md)。此结论不扩展到其它题、任意 clone／无 profile API 组合、真实模型修题质量或训练资格。

只读证据根 `runs/category2_repair_20260929/remote/d6/cpu_acceptance_v3`。独立程序 [d6_cpu_v3_evidence_probe.py](d6_cpu_v3_evidence_probe.py) 从 prepared／baseline／frozen／projection／完整 eval.log／supplemental 原始输出和侧车重建结论，不使用自动 review.json 的通过结论。两题分别在整题 manager_close 到齐后复核；最终轮只继续17071三行，没有重复10424或历史实验，未启动远端或修改原件。批次记录起止为09:13:58.715–09:31:30.288 UTC。

## 执行身份与准备一致性

执行为冻结 v2 清单 SHA `4110b196c8df1f0e8d51595b525eed17f6487977d83e59e2fddd68f5f11d965b`，660文件独立再核。工具继续用已审 `d6_acceptance_v2/run_acceptance.py`，SHA `ea5ec52ce2d7f54f46d9f5673839213b987dbcfac5eb3ce208aecfcd9238e95f`；材料、原镜像、正式脚本和预算未改，未复用旧材料资格。prepared host view 与当前冻结 TrustedTaskController 生成结果相等。

10424 run为 `d6-mypy-cpu03-10424`。三份保存的候选 baseline **全部字段均等于原真实 actor baseline**：1491 entries、相同 HEAD `4518b55663bc689646280a0ab2247c4a724bf3c0`，完整摘要 `sha256:e9d53030cc4462454733473159ddbc4c9044150847e9c3ff2039e3f865f8bfb7`、排除区摘要 `sha256:e782008a729129ee7cce7f35a9532ad75ed434dafbd6fe2306ea35c9cd976cbe`。

每行候选 stage.json／ledger 的 sanitizer 事实相等，与独立生成的共用脚本 SHA `sha256:7f258e10b13cc730047bc865cd87af08a2df193a3a7a81a807191b80cc5b69a0` 一致。候选侧和 grader 侧共6次 sanitizer 都 verified，HEAD前后相同，history9488不变，remote/reflog/unreachable均0。候选3次约8.051／7.899／7.665秒，grader3次约7.865／7.887／7.577秒。

**证据形态边界**：本矩阵保存的是生产 baseline 对象、sanitizer facts 与正式 grader 诊断，没有每次 Docker census stdout 全文；不冒称逐条重放了原始 stdout。原 actor 直评的 raw census 全文已独立重建相等，当前冻结强比较方法未改；矩阵三份保存的 baseline、正式评分完成、非空源码实际加载共同支持这里的接缝结论。

## 10424：非空候选确实应用，新增材料拒绝错误候选

三行 frozen digest 重算正确，原 baseline/public/image身份一致；用生产 `build_trusted_scoring_projection` 从冻结内容重新生成投影，与保存对象相等。gold／C1 的候选patch及 frozen.entries 与旧矩阵已审输入逐字相等，阶段为 git_apply、投影包含全部源码变更且无ignored；noop为空。正式report均注明在clean checkout重放。

| 候选 | 实际源码与投影 | 原F2P | 新增两项P2P | reward |
| --- | --- | --- | --- | --- |
| noop | 空delta，checker／meet保持base | 失败 | 全通过 | 0 |
| gold | 仅 `mypy/meet.py`，TypeType遇metaclass时返回declared；导入源码SHA `4200e1b0e1975cb327b4aaefb252ee6c44f48d7ccb22890854a80182d17d93b0` | 通过 | 全通过 | 1 |
| C1 | 仅 `mypy/checker.py`，比较窄化入口提前 `return {}, {}`；导入源码SHA `3a6349a32b8514aab163cf7b15fa6a44f3acae7ff319fa8fa17f745ceef17890` | 通过 | 全失败 | 0 |

三次补充观察都是正式grader用户54322，实际模块路径 `/testbed/mypy/...`；从原 baseline加冻结内容独立算出的源码hash与运行时观察逐个相等。base checker SHA为 `5a03d003f506dd5a37b556476c8df163443960b437181072866f540395cb955e`，base meet为 `8dc7439fa523716ff916e7a24fce4ae77946d1144681a3198d74041bc6eebc77`。gold和C1并非补丁只出现在元数据但没被评分器执行。

C1全文实际失败为：testTypeEqualsCheckUsingIs期望int却得到Any，testTypeEqualsNarrowingUnionWithElse期望int却得到Union[int,str]。原testNarrowingUsingMetaclass通过。因此是追加的两个正式P2P阻止了关闭全部窄化的错误候选，不是安装失败或节点漏跑产生0分。

## 10424：完整安装、参考、保护及清理

每行完整日志均实际3 selected，独立从测试段短摘要抽取的节点集合恰好等正式3参考，所有分区无missing/skipped/unaccounted。三行安装未跳过，requirements、editable和pytest／xdist安装完成，无子命令失败标记，安装RC0；test RC依次1／0／1，候选段完整。日志SHA匹配正式report及ledger：

| 行 | 完整 eval.log SHA-256 |
| --- | --- |
| noop | `e09df71d692a15e792ddff8ec683eb2f0027e2446a72fa74fe9e83ffa62052f5` |
| gold | `0d6f5a008184bcc2bbd8a253c3f8a9a2f4553bdd2c2347daa8f72b0db7026d17` |
| C1 | `67a19e1fb6c1561f6bd083276150bd54a9ea1654819ac6b1eb112a017c54c820` |

材料身份仍为 `sha256:087c7e478009b03857ca0d241f04400dadbe596ef93e37843190024c0564da0b`。新增case所在 `check-isinstance.test` 的实际hash均等注册的base SHA、uid0且grader不可写。两份源码补丁都不触碰测试控制面。

每行候选容器清理为removed=true／rm:ok，grader cleanup阶段存在；整题manager创建3／移除3，open0、supply_open0、cleanup_failures0。精确本run查询退出0、stdout为空，整题final_status=ok／exit0。两层清理均已收口，未消费或清理其它run。

## 17071：相同 baseline 与非空补丁实际生效

run `d6-mypy-cpu03-17071` 的三份候选 baseline 全字段等于原 actor，1480 entries，HEAD为 `4310586460e0af07fa8994a0b4f03cb323e352f0`，完整摘要 `sha256:d6f2ffc85b9caf4e2fbe0031e0e41a66afd0bca695b44e372c5a4be1f41378b0`，排除区摘要 `sha256:f75f79280f62024b614d4434c515bd04130607b59563fbe542ff3250fdd4d7ed`。candidate与grader两侧各3次sanitizer均为verified、共用脚本SHA相等、前后HEAD相同且通过自证。候选耗时约9.947／10.280／10.329秒，grader约10.223／9.790／10.204秒。

三行frozen、原baseline锚和投影重新计算正确，投影无忽略项／不支持形态。gold与C1的原patch、冻结entries与旧已审输入逐字相同，在candidate侧真实git_apply，运行时模块经54322用户从 `/testbed/mypy/` 导入；hash等于从baseline加冻结内容独立算出的结果：

| 候选 | 实际源码与投影 | 原2 F2P | 原2 P2P | 新增 P2P | reward |
| --- | --- | --- | --- | --- | --- |
| noop | 空delta，保留base源码 | 全失败 | 全通过 | 通过 | 0 |
| gold | 仅 `mypy/typetraverser.py`，遍历 callable 的 type_guard／type_is；源码SHA `b7be216425043ada1ca5eeda039b22699de86e8704868730f87fb247094ad0eb` | 全通过 | 全通过 | 通过 | 1 |
| C1 | 仅 `mypy/checker.py`，check_unbound_return_typevar开头return；源码SHA `308ff0607a7a251717e99dc38a4d608765fc821dfa6656e24d4e0040d3b864b2` | 全通过 | 全通过 | 失败 | 0 |

base typetraverser SHA为 `e555090299fa8325083a3d8d5be3ad4aca5fc4af5861a0781fb770905f1f0219`；base checker为 `ee8085a65c17cf5893b703df7360b12d83de356cd16c2c7d3cb5f84dd3908e55`。未改的模块也核相同，不只检查发生变化的一个文件。

完整日志中noop两个原F2P分别为testTypeGuardTypeVarReturn／testTypeIsTypeVarReturn：expected仅str，actual多报unbound错误，与原缺陷一致。gold实际5项全过。C1实际原4项全过；新增testUnboundTypeVar期望main:5／11／16三处真实unbound错误及main:11一条“使用upper bound int”的建议，Actual为空。因此新增P2P实际拒绝了关闭整个检查的错误补丁，不是缺节点或环境失败造成0分。

## 17071：安装、完整参考、保护与两层清理

三行原命令均实际启动38 workers并收集5 items。两条正式安装子命令requirements／editable都执行成功，无失败标记、未跳过，安装RC0；测试RC依次1／0／1，完整测试段无missing/skipped/unaccounted，独立抽取的5节点集合及状态恰好等于正式分区。pytest／xdist由此题requirements提供，没有套用10424额外的第三条安装命令。

| 行 | 完整 eval.log SHA-256 |
| --- | --- |
| noop | `807f025ffa377778afb6f477a48189b020f2ae41f040d2d1bcfc7b754ad420aa` |
| gold | `ac17497c2c7efe988850af53873c923bd3e4c01a343638b80d83e8a51c12fb40` |
| C1 | `85b23cb37b5cd2b94fe9089ec3174c913cf31da40da58761ea139439ea49ccd3` |

以上全文SHA及字节数都匹配report/ledger。材料身份保持 `sha256:8eedaba78b0b93dabfa3f2618bec38be69514907724a579c44dab8d8959de90a`；七项正式脚本／修订身份与prepared源相符。新增 `check-typevar-unbound.test` 三次实际SHA均为 `d189254a51fc53527373fd55afb07f69a6a081c3d9d8b9d9c71efd7ced0d8d0f`，等于注册base，uid0、0644、grader不可写；补充观察全部完整成功。

三份候选容器均removed=true／rm:ok，grader cleanup阶段均存在；整题manager创建3／移除3、open0、supply_open0、cleanup_failures0。精确本run查询退出0且空，final_status=ok／exit0。与10424合计，候选清理6/6、grader创建6／移除6、两个整题run无已知残留。此处依据两题已同步记录；全批远端／本地最终文件清单的运输对账由root另记，不冒充审查者重新查询了远端。

测试耗时约101.433／103.004／105.632秒，安装4.267／4.696／4.469秒。38 workers只运行5项的效率问题继续登记，未改命令、并发或预算换取通过；不是评分正确性阻塞。

## F1 最终核销与首片边界

| 验收项 | 独立结论 |
| --- | --- |
| 两题修订材料与来源／identity／保护 | 已通过；本轮仍使用原定两份修订和同一材料身份。 |
| 修复后replay：noop／gold／C1 | 6/6通过，各0／1／0；两题错误候选均由新增P2P拒绝。 |
| 原actor baseline/frozen/projection不改，交给新版fresh grader | 2/2通过；raw census逐字段相等，严格比较未改，实际安装和noop测试完成。 |
| 真实CC公开命令→quiescence→frozen | 此前两题子链已独立通过；新直评完成此前漏验的fresh重建接缝，详见原actor与v2报告。 |
| 本范围容器／manager清理 | 全部完成；未清其它run。 |
| F1处分 | accepted，修法及真实验收完成；在已验两题／两镜像／profile路径内closed。 |

**首片可以按上述CPU题级范围验收和移交，已审四文件可由root按来源SHA守卫合入共享树；本报告没有执行或验证这次合入。** CPU材料评分通过，不等于正式训练资格。公开链路证据来自真实Claude Code运行、受控本地模型stub给出的固定公开命令，证明该窄调用／轨迹／静止／冻结／身份／评分接缝；它没有证明真实模型能解决题目，没有GPU训练、线上模型质量或全公共链路故障覆盖的结论。

其它SWE修订未由本片实施或验证；不能把两题通过外推到216题。无profile manager的直接API混配与任意clone/image差异仍在 [实现审查](runtime_init_fix_review.md) 的范围边界内，不通过放宽摘要解决，当前正式消费者明确传profile。本次没有提升任何训练准入开关、重新定义奖励或改变材料政策。

## 历史保留与审查复盘

本报告是先完成10424、待17071整题结束后补齐的最终版本。早期“pending”表示当时未完成，最终6/6不是重跑或覆盖旧记录；原工具status保留其自动检查后的pending-independent-review标签，独立核销以本报告为准。

旧v1观察器失败、旧10424原actor直评的baseline fatal及旧六行材料矩阵均保留原件；本报告仅新增修复版的运行事实。首次发现F1属于生产接缝／测试有效性维度，原先纯binding与恒定FakeDocker census没覆盖fresh重建，这个缺口现由真实原工件直评和新replay复验补齐，不需改审查标准或放宽T0。
