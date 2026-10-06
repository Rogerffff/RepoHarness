# D6 两题真实 CPU 证据独立复核

2026-09-29。当前已独立复核 **10424 v1 三行＋17071 v2 三行及两题最终清理，正式 CPU 验收矩阵6/6行通过**。17071 v1 noop的正式评分完成、补充观察器失败历史保留，不计入这六行。真实 actor 开发／冻结证据另行复核。只读本地同步原件，不执行远端、不重跑评分，不以 `review.json` 的自动结论替代审查。

## 当前结论

**两题的修订评分链均已验证 `noop/gold/C1 = 0/1/0`。** 新增公开 case 在 base 和正确修法下通过，在对应已知错误补丁下确实失败；旧参考在错误补丁下仍全部通过，因此两题C1的零分直接来自新增回归约束。原始失败均为完整类型检查输出不匹配，无安装、导入或收集失败。

这支持两题材料修订的 CPU 评分验收，不等于两题整体完成，也不是训练授权。17071 v1 noop的联合0来自原始语义缺陷，停批来自后置观察器，二者分别保留。v2恢复只改独立观察工具，全部生产spec文件逐字与v1相同；两题真实 actor 开发／冻结接线窄核仍须单独收口。

| 题目／候选 | 原F2P | 原P2P | 新增P2P | reward／测试RC | 独立复核状态 |
| --- | --- | --- | --- | --- | --- |
| 10424 noop | 0/1通过 | 0项 | 2/2通过 | 0／1 | 原始日志、工件、安装、身份、保护、最终清理已核 |
| 10424 gold | 1/1通过 | 0项 | 2/2通过 | 1／0 | 同上 |
| 10424 C1 | 1/1通过 | 0项 | 0/2通过 | 0／1 | 同上；新增两例阻止原评分漏判 |
| 17071 noop v1（历史尝试） | 0/2通过 | 2/2通过 | 1/1通过 | 0／1 | 评分与清理已核；观察验收失败，不能充作完整通过 |
| 17071 noop v2 | 0/2通过 | 2/2通过 | 1/1通过 | 0／1 | 原始日志、工件、安装、身份、保护、最终清理已核 |
| 17071 gold v2 | 2/2通过 | 2/2通过 | 1/1通过 | 1／0 | 同上 |
| 17071 C1 v2 | 2/2通过 | 2/2通过 | 0/1通过 | 0／1 | 同上；新增例阻止原评分漏判 |

分母是本次有效参考清单，不是整个 mypy 测试集；0项不记作通过率。10424每行的实际收集均为 `9493 items / 9490 deselected / 3 selected`，三个精确 nodeid 与有效参考集合完全一致，无 missing／skip／额外运行节点。

## 证据位置与适用版本

本地根为 `runs/category2_repair_20260929/remote/d6/cpu_acceptance_v1/`（10424及历史17071 noop）与 `cpu_acceptance_v2/`（17071续跑）；原始 JSON 内的远端路径前缀 `/work/category2_repair_20260929/d6/` 仅用于定位同步后的 `remote/d6/`，未改写原件。

- 本次 run 为 `d6-mypy-cpu01`，10424子 run 为 `d6-mypy-cpu01-10424`。
- 冻结代码清单 SHA-256：`43186d0d85f1eb4e7d28e51b92a9a2c82bf1d4ff178d785d8d4846795300460e`，已在实现复核中确认659文件匹配。验收工具 SHA 为 `f22865a56e68b35a52bb694c1fef63bf59ff54c6f08bd8fafeb9285fac78a538`，运行记录相同。
- prepared manifest 的外部 SHA：`90803909b82249c9a8336632de7a99e9ad707a3750c25ad2ea66b2720095a251`；host grading 文件 SHA：`300fc3b53369a32d6a20f476c293adc32ef91e56698a8518ea67f812fbd5e517`。独立经正式 loader 重验，并将两题 host view 与冻结代码从原件重放的 controller 输出精确比较，均一致。
- 10424修订 `swe-mr-mypy-10424-p2p-v1`，有效材料身份 `sha256:087c7e478009b03857ca0d241f04400dadbe596ef93e37843190024c0564da0b`；环境包 `sha256:08cd08062a42162062423f7d2b3fc500eabb917a6db0871ab11b4a8b23b80c0b`。镜像为 `sha256:64472be326bc6cb14d3fb3beea3bd6ac8f71bab29c159c6e92538adcbe55c27f`，三行均与冻结 baseline／artifact／账本相同；资格来源 `absent`，没有复用旧材料资格。

## 10424逐候选事实与语义

三项完整节点共同前缀为 `mypy/test/testcheck.py::TypeCheckSuite::`。

**noop：原缺陷仍存在，公开回归保持。** [原始日志](../../../../../../runs/category2_repair_20260929/remote/d6/cpu_acceptance_v1/python__mypy-10424/eval_logs/evallog_replay-d6-mypy-cpu01-104_6a6d6f60.eval.log) SHA 为 `a745a9ea9a7c80c46a53aca2c699bb74a003ecad38aea84faf12f7cf10a972f0`。日志502行记录3 selected，507–538行显示原 `testNarrowingUsingMetaclass` 在 main:11／17应保持 `Type[__main__.C]`，实际变成 `<nothing>`；新增 `testTypeEqualsCheckUsingIs` 与 `testTypeEqualsNarrowingUnionWithElse` 均通过。已对照原官方 test patch：它要求 Type[C] 与元类相交时保留可表达的声明类型。这是题目目标的真实失败。冻结工件 `entries=[]`，没有借noop替换代码。

**gold：只补元类相交分支，原有收窄保持。** [原始日志](../../../../../../runs/category2_repair_20260929/remote/d6/cpu_acceptance_v1/python__mypy-10424/eval_logs/evallog_replay-d6-mypy-cpu01-104_7075bf20.eval.log) SHA 为 `9f7a131cd4756080f9e6f65988ff2bb615d3b04ed28c28055996ea8247fe555d`，3 selected／3 passed、测试RC0。候选 patch SHA `0bc6c39bdd85a3ddd99913d868e153bcf3a3292f90ac35e577b4bcc2712bba23` 与材料包相同；冻结只含 `mypy/meet.py`，直接解码核到77–81行的新分支：声明是 `TypeType`、收窄对象是元类 `Instance` 时返回 declared。实际导入该文件 SHA 为 `4200e1b0e1975cb327b4aaefb252ee6c44f48d7ccb22890854a80182d17d93b0`，与冻结内容重算一致；checker保持base内容。

**C1：错误补丁绕过旧F2P，但被新增case准确挡下。** [原始日志](../../../../../../runs/category2_repair_20260929/remote/d6/cpu_acceptance_v1/python__mypy-10424/eval_logs/evallog_replay-d6-mypy-cpu01-104_f3cfdacd.eval.log) SHA 为 `e354f6f462b760b2241241133d94bbadc3d926db3f9cc988eb67021252ffa964`。候选 patch SHA `cbbed6af1263fa5c95eedca4b6a5126f4f0687f53aa9abd6b0cc9ec7b19e5ef7` 与材料包相同；冻结只含 `mypy/checker.py`，3969行提前 `return {}, {}`，确实关闭整个对应收窄函数。实际导入内容 SHA `3a6349a32b8514aab163cf7b15fa6a44f3acae7ff319fa8fa17f745ceef17890` 与冻结工件相同。原F2P通过，而新增case的完整诊断分别是：

- `testTypeEqualsCheckUsingIs`：应将 `Any` 收窄为 `builtins.int`，实际仍为 `Any`。
- `testTypeEqualsNarrowingUnionWithElse`：真分支应为 `builtins.int`，实际仍为 `Union[builtins.int, builtins.str]`；else分支本来就应保持该Union，实际也保持。失败集中在丢失应有的真分支收窄。

已直接读登记的原公开 `.test` 文件2594–2609行，断言与日志完全一致；不是新测试名存在但测试体未执行，也不是改变parser后制造失败。两例都落到 `assert_string_arrays_equal` 的诊断内容比较。

## 安装、生效、文件保护与清理

10424三行均逐段查看原始安装日志：`python -m pip install -r test-requirements.txt` 的依赖已满足；`python -m pip install -e .` 的隔离build依赖、editable metadata／wheel构建和安装均完成；`pip install pytest pytest-xdist` 返回依赖已满足，最后 `hash -r`。三行没有 `RH2_INSTALL_CMD_FAILED`，安装未skip，最终RC0。安装耗时分别5.339／5.552／5.548秒；不是只以最后一个 `hash -r` 的RC认定安装成功。执行环境为 Python3.9.19／pytest6.1.2，使用离线 wheel 目录。

补充观察显示解释器为 `/opt/miniconda3/envs/testbed/bin/python`，checker／meet均从 `/testbed/mypy/*.py` 导入。独立重算 baseline 文件摘要加冻结修改后的实际内容，与观察摘要完全一致；三种候选产生不同、符合预期的源码与测试行为，排除了仅看版本字符串导致的安装生效误判。观察由候选UID54322运行，仅作为本次固定候选的辅助证据，不声明具有对任意恶意候选的证明能力。

三行root setup均从base `4518b55663bc689646280a0ab2247c4a724bf3c0` 恢复 `check-isinstance.test` 和 `check-narrowing.test`，前者SHA为 `709c22b24c619241824568302229ec5a4222747071146ac0094b3c7ae5c2b2ed`；随后原test patch成功应用。attestation为2个测试文件全部存在、restore2、applyRC0；控制面为protected2、missing0。测试之后新增文件仍为该SHA、root属主、0644且候选不可写。实际参考文件与注册器一致。

三行候选容器均 `rm:ok`，正常评分收尾均有 `grader_cleanup`。10424的 [manager_close.json](../../../../../../runs/category2_repair_20260929/remote/d6/cpu_acceptance_v1/python__mypy-10424/manager_close.json) 记录 grader创建3／移除3、open0、cleanup_failures0、supply_open0；按该子run精确标签查询退出0且无输出。至此10424两层容器清理闭合。日志是完整日志；测试RC为1／0／1而外层exec均0，是脚本在记录测试RC后正常收口，不能混淆两个RC。

## 17071 v1 noop：正式评分完成，补充观察失败

[原始评分日志](../../../../../../runs/category2_repair_20260929/remote/d6/cpu_acceptance_v1/python__mypy-17071/eval_logs/evallog_replay-d6-mypy-cpu01-170_843a350c.eval.log) SHA 为 `ff538df7f8d94438bebebfd50d126365aee9c9c292978b009ab9ab49f37e11c3`。正式命令为登记的 `pytest -rA -k` 五case并集，日志列出五个精确参考，两个TypeGuard／TypeIs原F2P失败，两个原P2P和新增 `testUnboundTypeVar` 通过。失败来自main:5多出“A function returning TypeVar should receive at least one argument containing the same TypeVar”诊断；main:9推断str仍正确。已对照原test patch：T出现在参数回调的 `TypeGuard[T]`／`TypeIs[T]` 中，应被识别为已绑定；该多余诊断正是原缺陷。联合reward0、`tests_failed`、测试RC1，非infra。

原始安装日志中 requirements、隔离editable构建与安装完成，mypy版本为 `1.10.0+dev.4310586460e0af07fa8994a0b4f03cb323e352f0.dirty`；无安装子命令失败，RC0，安装4.578秒。冻结工件entries为空。root setup恢复3文件，新增 `check-typevar-unbound.test` 的SHA为 `d189254a51fc53527373fd55afb07f69a6a081c3d9d8b9d9c71efd7ced0d8d0f`，原patch apply成功；sidecar保护3／缺失0。材料／prepared／sidecar／工件摘要已独立重算核对，未发现错配。

**观察失败必须保留。** [supplemental_observation.json](../../../../../../runs/category2_repair_20260929/remote/d6/cpu_acceptance_v1/python__mypy-17071/noop/supplemental_observation.json) 退出1、stdout空：`typetraverser.py:7` 先导入types，而 `types.py:3136` 回引尚未定义的 `TypeTraverserVisitor`。直接读来源base两文件可复证该导入环，不是根据自动review推断。失败发生于独立新Python进程的后置观察；正式pytest已完整完成，不能把这条ImportError写成候选测试导入失败。由于JSON尚未输出，**本行没有最终源码导入摘要及测试后不可写观察**，不可补写为已确认。

停批后的 [manager_close.json](../../../../../../runs/category2_repair_20260929/remote/d6/cpu_acceptance_v1/python__mypy-17071/manager_close.json) 为 grader创建1／移除1／open0、cleanup_failures0，候选rm成功，精确run残留查询0且空。批次exit4的reason是验收检查失败，不是容器收口失败。

恢复边界审查：在**新工具版本和新输出目录**中，让观察器先经正常 `mypy.build` 导入初始化，再观察目标模块，是足够小的修正；须先单独证实该导入顺序可用。17071应同时观察 `mypy.typetraverser` 与 `mypy.checker`：gold修改前者，C1关闭 `checker.check_unbound_return_typevar`，只观察前者不能覆盖C1实际源码。此修改不应改冻结生产代码、spec、parser、镜像或评分命令。10424三行不需重跑；v1旧行、旧观察脚本及停批记录保留，v2 noop是新尝试，不能静默替换旧结果。该恢复只补验收证据，不放宽判分规则。

**v2工具静态补核已完成。** `tools/d6_acceptance_v2/run_acceptance.py` SHA-256为 `ea5ec52ce2d7f54f46d9f5673839213b987dbcfac5eb3ce208aecfcd9238e95f`。与v1逐行diff仅涉及：观察前导入`mypy.build`、17071多观察checker、明确`--only-task`派发范围、相应3／6行数量和状态记录。`validate_row`未放宽，生产spec／parser／预算／镜像／材料未变。准备阶段仍核两题，仅执行所选题，最终3行检查不会把单题续跑标成六行完成。恢复记录见 [cpu_observation_recovery.md](../d6/cpu_observation_recovery.md)。

独立已读 `probe_mypy_import_v3.py` 源码及随后同步的三份 `remote/d6/import_order_probe_v{1,2,3}/record.json` 原件。三个版本的direct均以真实循环导入退出1；v1/v2的standard均因未复现正式Git配置条件，以dubious ownership／`git rev-parse HEAD`退出128导致Python退出1。v3使用相同固定17071镜像、UID54322、断网、临时HOME，在容器内写与正式候选脚本相同的`safe.directory=/testbed`，standard退出0、stderr空，实际导入`/testbed/mypy/typetraverser.py`，SHA为`e555090299fa8325083a3d8d5be3ad4aca5fc4af5861a0781fb770905f1f0219`。六个小容器均rm/query退出0且残留为空。小探针恢复已独立验证，旧失败保留；其作用只定位观察器，不能替代17071 v2正式评分及源码生效证据。

效率事实单列：17071原命令按宿主发现 **38 workers运行5项**，pytest阶段99.58秒，候选事实测试100.2秒，manager记录测试106.849秒／总评分180.501秒、内存峰值3028.914MiB；本次CPU额度为2。此为原命令并发与有效资源不匹配的观测，不是D6选题／判分错误；本片不顺便改命令或预算，后续效率工作可引用该证据。

## 17071 v2：三行正式矩阵完成

本次子run为 `d6-mypy-cpu02-17071`。新prepared manifest SHA为 `270a6a984de27b6a39d99d8fa56df751d8f9a07dfda6f61061da2d8a9e01983b`，与v1 manifest唯一不同字段为准备时间；host grading字节SHA仍为 `300fc3b53369a32d6a20f476c293adc32ef91e56698a8518ea67f812fbd5e517`。独立经loader核验，并与冻结controller重放输出完全相等。spec目录全部生产脚本及join文件与v1逐字一致。

三行均使用镜像 `sha256:0111b5f8ac2ce898b81259d9dedc5aad1aa4059ac0f69a446073c2c3e8deffba`、base `4310586460e0af07fa8994a0b4f03cb323e352f0`，材料身份 `sha256:8eedaba78b0b93dabfa3f2618bec38be69514907724a579c44dab8d8959de90a`，环境包 `sha256:ac1884f7c4c6bd9fa174b6e1ee8d75e4fde70a0a284b005ab970c476dfdfa8a0`；旧资格来源均 `absent`。实际运行节点精确为原2 F2P、原2 P2P、新1 P2P，无missing/skip/额外节点。

**noop保持原缺陷。** [原始日志](../../../../../../runs/category2_repair_20260929/remote/d6/cpu_acceptance_v2/python__mypy-17071/eval_logs/evallog_replay-d6-mypy-cpu02-170_88dd8eee.eval.log) SHA `de2a71b3780c29bb1b8d4c996fada8b52328372c053ba016429982908caa59aa`：2失败3通过。两个TypeGuard/TypeIs F2P仍多出main:5的unbound TypeVar诊断，与v1语义一致；新增case通过。冻结entries为空，checker及typetraverser均与baseline内容摘要相同。

**gold恢复应有遍历且保持unbound检查。** [原始日志](../../../../../../runs/category2_repair_20260929/remote/d6/cpu_acceptance_v2/python__mypy-17071/eval_logs/evallog_replay-d6-mypy-cpu02-170_6d2bbd10.eval.log) SHA `de2516f9500c424248ca319af427a1ea25d6340e008616b92ad2073cc665553c`：5通过。候选patch SHA `fcc697876239908bf4070a03921326432d564c54da43073587fec909aae0467b` 与材料包一致。独立解码冻结内容，唯一改动文件 `mypy/typetraverser.py` 的89–93行在callable访问中遍历非空 `type_guard` 与 `type_is`；实际导入SHA `b7be216425043ada1ca5eeda039b22699de86e8704868730f87fb247094ad0eb` 与冻结内容一致。checker仍为base SHA `ee8085a65c17cf5893b703df7360b12d83de356cd16c2c7d3cb5f84dd3908e55`。

**C1关闭全部检查，被新增case准确挡下。** [原始日志](../../../../../../runs/category2_repair_20260929/remote/d6/cpu_acceptance_v2/python__mypy-17071/eval_logs/evallog_replay-d6-mypy-cpu02-170_1cf6b79e.eval.log) SHA `b5682a2a42226680de6a79614df6506b072f815c43b0165743f7c78d801c90ef`：原4项通过，新增 `testUnboundTypeVar` 失败。候选patch SHA `0a36e66ee5f736314e299c53897fd8371b6552a03879e1549a111ef036442b08` 与材料包一致；独立解码冻结 `checker.py`，1424行在 `check_unbound_return_typevar` 开头直接return。实际导入SHA为 `308ff0607a7a251717e99dc38a4d608765fc821dfa6656e24d4e0040d3b864b2`，与冻结内容一致；typetraverser保持base。

已直接读原公开case第1–19行与base检查函数：无参数的 `f()->T`、`g()->U`（U bound=int）、`h()->V`（V约束为int/str）都应诊断返回TypeVar没有参数绑定，g另有使用上界int的建议。C1日志Expected明确列出main:5、11、16三条error和main:11一条note，Actual完全为空。该失败由检查整体被禁造成，不能归为收集/安装异常；新参考实际覆盖原评分漏掉的退化。

三行requirements依赖满足，editable隔离build依赖、metadata、wheel构建、旧包卸载和新包安装均在原日志中完整完成，最后hash刷新，未skip、无失败子命令，安装分别4.638／4.693／5.120秒。Python3.12.4、pytest8.1.1；三行仍按原命令38 workers运行5项，pytest分别96.38／98.13／105.15秒。本次没有改该效率问题。

三次后置观察均在UID54322以标准build初始化后退出0、stderr空，解释器正确；checker和typetraverser都来自 `/testbed/mypy/*.py`，摘要由baseline加冻结内容独立重算匹配。新增测试文件SHA仍为 `d189254a51fc53527373fd55afb07f69a6a081c3d9d8b9d9c71efd7ced0d8d0f`，root属主、0644、候选不可写。三行sidecar均保护3文件、缺失0；材料、原/新增参考分区与身份一致。

候选三次均已移除，grader各自完成cleanup。[manager_close.json](../../../../../../runs/category2_repair_20260929/remote/d6/cpu_acceptance_v2/python__mypy-17071/manager_close.json) 创建3／移除3、open0、cleanup_failures0、supply_open0；该子run精确标签查询退出0且空，最终退出0。未把同台其他线程的容器算成本批残留，也未操作它们。有效矩阵是10424 v1三行与17071 v2三行的并集，不重复计算历史v1 noop。

## 独立核对方法与剩余门槛

辅助只读探针 [d6_cpu_evidence_probe.py](d6_cpu_evidence_probe.py) 不读取自动 `review.json`，从原始log自行提取精确状态，重算日志字节／SHA、baseline／frozen／projection摘要，核来源controller→prepared→host→spec→ledger／sidecar身份、每个参考分区和实际源码观察。分别指向v1、v2目录核验，两题有效六行均通过；单目录内不存在的另一批行只是未在该目录执行，不是联合矩阵缺项。17071 v1 noop仍记录 `supplemental_observation_complete=false` 和批次exit4，不把观察缺失吞成通过。人工另读了原始安装文本、失败栈、公开case与候选解码内容；不能以该探针替代语义审查。

剩余事项：真实actor到fresh grader接缝。后续两题公开开发／冻结子链已独立核实，但发现共同初态不一致的F1阻塞，见 [actor证据审查](d6_actor_evidence_review.md)。这不推翻本报告的六行CPU材料结论，也不允许先转类。actor工具的只读入口审查无阻塞，见 [actor工具审查](d6_actor_runner_review.md)，只代表可执行。当前未为MONAI、题面或参考绑定等其他修订能力做实施／验收声明。无需增加批准闸门，也无需机械重跑已核对的六行。
