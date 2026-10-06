# F1 真实actor工件→fresh grader反例独立复核

2026-09-29。**F1已由正式评分路径真实复现，继续阻塞actor接缝核销和两题转类。** 10424原actor noop工件进入 `SWEGradingManager.grade` 后，在完整baseline重建阶段抛 `BaselineIntegrityError(reason_code="baseline_digest_mismatch")`，进程退出20；没有运行候选应用、安装或测试，不能把这次结果写成reward0。容器及本run网络清理完成。

只读证据根：`runs/category2_repair_20260929/remote/d6/actor_to_grader_v1/python__mypy-10424/`。独立核其recordmanifest中的46份文件SHA/字节数，全部一致；未修改原件、生产代码或执行远端。工具审查见 [单条runner审查](d6_actor_to_grader_runner_review.md)，先前静态可达性与actor子链见 [actor证据审查](d6_actor_evidence_review.md)。

## 从原始census重算，而非引用自动状态

真实run `d6a2g-v1-10424` 于08:55:08.077–08:55:12.585 UTC结束。runner SHA `4f3cd3cfe9f76a1dd0934600f3fc772f6ab4d996b34276a61978816ab6b44685`、生产清单SHA `43186d0d85f1eb4e7d28e51b92a9a2c82bf1d4ff178d785d8d4846795300460e` 均为已审版本；原actor工件、baseline、prepared、材料、镜像及预算保持原值。

`docker_calls/0011/` 是实际baseline重建调用：退出0，stdout为175040字节，SHA-256 `224634c203ad8a4be3a5ce86404eb34fb7bf85fb80506e9c98a4b2131125daaa`。独立将call中完整执行脚本与冻结 `build_census_script(actor.workdir, actor.policy)` 比较，逐字相等；再用冻结生产 `parse_census_output` 解析该stdout，复制正式manager所用的actor血缘参数。

重建后的 **1491个entries与原actor逐字相等**，policy、task、public、image、base/head和workdir也都相等。全部manifest字段比较只有一项差异：

| 摘要 | 原actor | 真实fresh grader重建 |
| --- | --- | --- |
| excluded census | `sha256:e782008a729129ee7cce7f35a9532ad75ed434dafbd6fe2306ea35c9cd976cbe` | `sha256:f94ee70142a34093ce6e0dddecf516840896cf45fd8aab5d2264c79c52cb111e` |
| 完整baseline | `sha256:e9d53030cc4462454733473159ddbc4c9044150847e9c3ff2039e3f865f8bfb7` | `sha256:cac65636ebf441ae4cb4900f6f80ef6614f2d8a568a13e31227712cf01d37c03` |

此外，fresh重建manifest与已通过六行矩阵的10424 replay noop baseline **整个对象完全相等**。这直接确认先前跨路径比较推导；没有换baseline、删字段或在验收程序里合成census。

原始traceback走过生产 `manager.grade:1801` → `_grade_within_deadline:2027` → `_verify_baseline_rebuild:3111`。唯一grade调用次数为1。这里的fatal不是解析失败：census执行与解析都成功，两个完整manifest的严格摘要比较失败。记录无report、eval_log、candidate delta apply或test段，与实际停点一致。

## 路径定位及证据边界

实际census的25条 `EXCL` 全部位于 `.git/`；没有 `.harness/` 路径。源码按这些路径排序、换行连接取hash，独立重算为上述fresh排除区摘要。原始清单明确包含：

- `.git/ORIG_HEAD`
- `.git/logs/HEAD`
- `.git/logs/refs/heads/master`

actor在baseline前执行的冻结sanitize脚本明确删除ORIG_HEAD和整个logs目录，其已保存成功记录也显示reflog为0。这三条是可定位的准备顺序差异。fresh另含旧pack的 `.idx/.pack` 两个文件、refs/packed-refs等路径；sanitize还做ref删除、repack及prune。

**不能声称完整差集只有三条。** 对fresh路径清单只去掉上述三条后，摘要为 `999d7c1c4d33d5bffe64b42e63e452b027035b5022021504b8c7803504de61fe`，仍不等于actor排除区摘要。因此还存在其他路径差异，repack/ref变化是源码支持的原因，但原actor未保存EXCL全文，不能凭摘要还原具体新pack文件名或列全差集。已确认的唯一manifest字段差异与fatal因果足够成立，不需猜出完整路径差集才能认定阻塞。

## 清理与下一步

原始 `docker_calls/0012` 为同一grader容器的 `rm -f`，退出0；0013/0014分别使用精确 `label=rh2.run_id=d6a2g-v1-10424` 查询容器/网络，均退出0、stdout和stderr为空。manager close记录创建1／移除1、open0、supply_open0、cleanup_failures0，grade退出20未被清理失败覆盖。没有清理同台其它run资源。

本证据关闭的是“是否真实可达”的待核项，**不是修复关闭**。后续实现应使受信准备初态一致并保持完整manifest严格核对；新版本仍需原actor工件→fresh grader的真实验收，不能用修订后的replay自洽代替这条跨路径接缝。现有六行D6材料评分结论与公开CC子链结论均保留，首片整体仍未完成。
