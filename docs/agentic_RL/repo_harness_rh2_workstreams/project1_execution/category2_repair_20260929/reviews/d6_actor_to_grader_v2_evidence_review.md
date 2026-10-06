# D6 原 actor 工件直评 v2 独立证据审查

2026-09-29。**10424、17071 两题原 actor → fresh grader 接缝均已真实通过，2/2 独立复核完成。新 replay 六行矩阵仍待复核，整批 F1 暂不关闭。** 这里的通过是原工件经完整 baseline 重建与真实测试后的正常 noop 0 分，不是纯 binding 或自动 review 的状态推断。

只读证据根为 `runs/category2_repair_20260929/remote/d6/actor_to_grader_v2/`。未改生产、原工件、raw evidence，也未启动任何远端执行。独立核对程序为 [d6_actor_to_grader_v2_evidence_probe.py](d6_actor_to_grader_v2_evidence_probe.py)，读取 raw census／脚本 stdin／完整日志／正式代码，不读取自动 review.json 的结论。版本与工具前置结论见 [候选修法审查](runtime_init_fix_review.md)、[v2 工具审查](d6_actor_to_grader_v2_runner_review.md)。

## 代码、来源与强比较

执行代码清单 SHA-256 `4110b196c8df1f0e8d51595b525eed17f6487977d83e59e2fddd68f5f11d965b`，660 个文件逐件 SHA／字节核对通过。原 actor 仍来自旧代码清单 `43186d0d85f1eb4e7d28e51b92a9a2c82bf1d4ff178d785d8d4846795300460e`；两身份分列。runner SHA 为已审 `c19ef71b55ad52dfd37dd817b50583db38aec7eb6a9c39ca142d222deae56c0f`。

独立比较旧／新 `SWEGradingManager._verify_baseline_rebuild` 的整个 AST，完全相等；`baseline_census.py` 与 `contracts/baseline_manifest.py` 逐字节相同。该方法仍先拒绝实际 checkout HEAD 不符，再执行原 census 并计算完整 canonical digest，任何差异抛 baseline_digest_mismatch。runner 只在 super 返回后置 baseline_passed，没有替换该比较或返回值。

## 10424：原始重建与原工件完全相等

run `d6a2g-v2-10424`，09:06:52.991–09:08:41.548 UTC，一次 grade。新证据清单的 **88 份文件** SHA／字节均通过；旧 actor **28 份原件**再核相同，input_check 记载的原文件表与原 recordmanifest 完全相等。baseline、frozen、projection 没有改写；仍是旧 actor 的空 delta。

`docker_calls/0010` 实际 probe 的 HEAD 为 `4518b55663bc689646280a0ab2247c4a724bf3c0`，base object 存在，符合原 actor materialized_head。0011 真正执行共用 sanitizer，完整脚本与冻结生成器结果逐字相同，使用已审 clean-env 前缀。退出0，HEAD 前后不变，history 9488→9488，refs 删除79、保留16，remote/reflog/unreachable 均0；约8.055秒。该事实给出当前10424镜像下原 actor 继承环境与新 grader 清环境结果相容的实证，不推广到其它镜像。

0012 为正式 baseline census，退出0；原始 stdout **175016字节**，SHA-256 `1b7dfeb2d53a96f4488d4361425abc8099b171dd92e88173e54b665868eb4efd`。实际脚本与 `build_census_script(original.workdir, original.policy)` 逐字相等。独立用冻结生产 parser 重建结果，再逐字段比较原 actor：

| 项目 | 独立结果 |
| --- | --- |
| 全部 manifest 字段 | 完全相等，包括 policy、task/public/image/base/head/workdir |
| scoreable entries | 1491 个，路径／类型／mode／内容摘要全部相等 |
| 排除区普通文件路径 | 原始 census 共24条；摘要 `sha256:e782008a729129ee7cce7f35a9532ad75ed434dafbd6fe2306ea35c9cd976cbe`，等于原 actor |
| 完整 baseline digest | `sha256:e9d53030cc4462454733473159ddbc4c9044150847e9c3ff2039e3f865f8bfb7`，等于原 actor 和原 frozen 锚 |

随后原始调用继续进入 cache normalization、trusted setup、保护、安装和测试，符合生产强比较成功返回的实际顺序。因此不仅是状态标记变成 true，也不是用新 replay 的 baseline 替代原 actor。

与 v1 失败的 raw census 对比，新排除路径集删除 ORIG_HEAD、两条 logs 文件和旧 pack `1f76ee99…` 的 idx/pack；增加 `.git/info/refs`、`.git/objects/info/packs` 及新 pack `45426caa…` 的 idx/pack，25条变24条。这补足了旧报告“只有三条路径可直接定位，完整差集尚不知”的证据边界；新路径集摘要现已与原 actor 相等，不需要猜测剩余差异。

## 10424：材料、测试及清理

同次 prepared host view 经冻结 TrustedTaskController 再加载，材料身份仍为 `sha256:087c7e478009b03857ca0d241f04400dadbe596ef93e37843190024c0564da0b`。实际传入容器的 trusted setup 与 candidate test 脚本 stdin，逐字节等于正式 spec；脚本总摘要、材料六项身份、分区、原镜像与三项预算保持原值。保护自证为 EXPECTED_FILES=2、PROTECTED_FILES=2、MISSING_FILES_COUNT=0、RH2_PROTECT_OK=1。

完整 eval.log **28277字节**，SHA-256 `6e00a4bdc00c94a4b31d5a2dca2ae664c3f9f2207a84cb68249412a51a31dfca`，匹配正式 report 引用。原文显示 requirements 安装、editable 安装、pytest/xdist 安装三条都执行完成，没有 RH2_INSTALL_CMD_FAILED，安装RC0；实际 pytest 3 selected，test RC1：

| 真实节点 | 结果 |
| --- | --- |
| testNarrowingUsingMetaclass，原 F2P | FAILED |
| testTypeEqualsCheckUsingIs，新增 P2P | PASSED |
| testTypeEqualsNarrowingUnionWithElse，新增 P2P | PASSED |

原 F2P 的 expected 为 Type[C]、actual 在两个位置为 `<nothing>`，与原基线缺陷一致；不属于安装、缺节点或新材料失败。正式 parser 的3参考与各分区无 missing/skipped/unaccounted，report 为 unresolved/tests_failed/reward0。新增 sanitizer 没有绕过或减少参考测试。

0024 对本 grader 容器 rm -f 退出0；0025／0026 精确按 `rh2.run_id=d6a2g-v2-10424` 查询容器／网络，均退出0、输出为空。manager created1／removed1、open0、supply_open0、cleanup_failures0，最终退出0。未清其它 run。

## 17071：原工件完整相等，实际5参考正常 noop

run `d6a2g-v2-17071`，09:09:32.040–09:13:04.436 UTC，一次 grade。独立再核新证据88文件和原 actor28文件，SHA／长度与原清单一致。执行代码、runner、强比较及材料构建方法与10424相同；实际 trusted setup／candidate test 的 stdin 同样逐字匹配正式 spec。

0010 probe HEAD 为 `4310586460e0af07fa8994a0b4f03cb323e352f0`；0011 共用 sanitizer 实际执行成功，HEAD不变，history 11783→11783，refs删除79／保留16，remote/reflog/unreachable均0。脚本内记录9.61475秒，执行先于0012 census。

0012 stdout **172654字节**，SHA-256 `608c7544a077bfbe74c700e8a594cf3084ad6c1cfa583c3f6e343c6c408d721b`。脚本与正式生成器相等；用正式 parser 重建得到的 **1480 entries 和全部 manifest 字段等于原 actor**。24条排除区路径的摘要为 `sha256:f75f79280f62024b614d4434c515bd04130607b59563fbe542ff3250fdd4d7ed`；完整baseline为 `sha256:d6f2ffc85b9caf4e2fbe0031e0e41a66afd0bca695b44e372c5a4be1f41378b0`，都正是原工件的锚。

材料身份仍为 `sha256:8eedaba78b0b93dabfa3f2618bec38be69514907724a579c44dab8d8959de90a`。原日志显示新增保护文件 `check-typevar-unbound.test` 从base恢复，SHA为 `d189254a51fc53527373fd55afb07f69a6a081c3d9d8b9d9c71efd7ced0d8d0f`；EXPECTED_FILES／PROTECTED_FILES均3、missing0、protect成功。实际 requirements和editable两条安装都完成、无失败标记、安装RC0。17071的原recipe通过requirements安装pytest／xdist，没有10424额外的第三条安装命令；按实际正式脚本核对，没有强加另一题的命令。

完整 eval.log **28125字节**，SHA-256 `d37f53a721713861714cfe3e669d98acaffe0e628b2d903b16f6e92172e9d5e3`，匹配report引用。实际38 workers只收集5项，test RC1；保留原命令，未顺便修改效率策略。节点结果为：

| 真实节点 | 结果 |
| --- | --- |
| testTypeGuardTypeVarReturn，原 F2P | FAILED |
| testTypeIsTypeVarReturn，原 F2P | FAILED |
| testTypeGuardIsBool，原 P2P | PASSED |
| testTypeIsUnionIn，原 P2P | PASSED |
| testUnboundTypeVar，新增 P2P | PASSED |

两个失败均是期望仅显示str，却额外报“A function returning TypeVar should receive…”的原基线缺陷。新增节点实际通过；正式分区与独立日志解析均无missing/skipped/unaccounted，报告为正常 unresolved/tests_failed/reward0。候选测试记录约105.683秒，安装4.304秒；该worker开销仍是已知效率事实，不是本次评分失败。

原始末三次调用为同一grader容器rm-f退出0，以及精确本run标签的容器／网络查询退出0且空；manager created1／removed1、open0、supply_open0、cleanup_failures0，最终退出0。两题真实直评至此分别证明原actor继承镜像环境与新clean-env sanitizer在当前两个镜像上得到可接受的完整基线，不外推其它题或clone形态。

## 当前核销边界

- 10424 原 actor 工件接缝：已独立通过。
- 17071 原 actor 工件接缝：已独立通过。
- 新代码 replay 两题 noop／gold／C1：待真实矩阵复核；旧六行材料矩阵不被覆盖。

[v1 真实 fatal](d6_actor_to_grader_failure_review.md) 保持历史事实，不回写成通过。待以上项齐全后再判定整批 F1 及首片能否核销；本报告不授权或暗示正式训练准入。
