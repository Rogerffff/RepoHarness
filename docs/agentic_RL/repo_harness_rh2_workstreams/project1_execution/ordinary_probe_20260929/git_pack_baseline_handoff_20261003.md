# 首条 GPU 候选的 Git 压缩包基线差异

更新：2026-10-03 01:12 SGT。给公共初始化链维护者的窄交接；不修改既有评分契约，不把以下诊断当作模型成绩。

## 已确认的影响

Moto5134 的 Coder 实际求解155秒、43回合、正常结束，非空原 FrozenPatch 已保存。清理异常现场确认恢复后，以原工件、原配置另建 `recovery_moto_a2_grade_v1` 评分。在候选应用前，完整 baseline 对账失败，因此安装和测试尚未开始，没有0/1成绩。原 attempt 的 cleanup=false 和旧队列 attention 保留。恢复评分的容器已正常移除。

冻结实现已包含两侧共享的 `git_sanitize_script`，并非尚未接上那次修复。完整 manifest 的差异仅来自排除区普查摘要：`.git/objects/pack/`下两个压缩包文件名不同。1613个评分文件的路径、类型、模式、内容摘要完全一致，无增删；HEAD也相同。

## 不调用模型的真实复现

根执行者在原 actor / grader 的两个 pristine 镜像容器中，分别运行冻结的清理脚本和普查两次。网络为none，无候选、无测试、无镜像构建。沿用实际执行方式：actor继承镜像ENV，grader使用可信env -i。两侧实际Git都是`/usr/bin/git` 2.34.1，HEAD相同，历史6758个commit，CPU限制均2核；实际PATH仍不同，不能仅凭这一点归因。

| 观测 | 实际结果 |
| --- | --- |
| 首次清理前 | 两镜像的pack名称、大小和SHA均一致。 |
| Actor第1次／Grader第1次 | 精确复现原求解baseline `5d2975…` 和评分重建 `60717d…`。 |
| Actor第2次／Grader第2次 | 各自变为`87cd508…`和`6f8fd316…`；同一容器再次清理也不稳定。 |
| 四次评分文件普查 | 1613个条目均与原baseline相等，仅`excluded_census_digest`不同。 |
| 四次Git对象集合 | 按对象ID、类型、大小排序的摘要都为`0ef63fc1ad6d7b7ef4293357510b9b835103438da6d2c0b5a992194a57e834e4`。 |
| 收尾 | 28条Docker操作均退出0；两个诊断容器已移除，原attempt和baseline SHA不变。 |

这证明重复Git清理会改变压缩包的存储表示，而当前完整基线比较包含该表示的文件名。尚未证明究竟是repack的哪项参数、并行行为或其他实现细节造成，不能直接写成PATH或线程数根因。

## 接续建议与边界

1. 公共维护者先定位并使可信初态准备可重复；用同源双容器和同容器重复执行验证。只构建一个预清理镜像不够，正式初始化还会再运行清理。
2. 不在探针脚本中忽略excluded摘要，不改写原baseline，不复制候选Git到评分容器，也不靠反复重试碰到相同包名。
3. 若修复需要改变完整manifest的比较语义，明确列为公共契约变更，沿既有决策程序处理。保留排除区原始审计，不由本线程暗改。
4. 修后先确定性验收，再冻结新的执行版本。原155秒求解的轨迹与补丁仍可语义审查；是否可以按新版本消费原工件须另有明确的适用性证明，不能把新baseline绑定到旧工件冒作原直评。

本线程暂缓新的模型题目派发，避免继续生成同类未能评分的候选。R2E尚未做本次非空直评，不能直接推定已发生同一故障；确认共享实现影响范围后再恢复相应入口。不阻塞题主的CPU工作或材料准备。

## 原件

- 冻结源码：`runs/ordinary_gpu_probe_20261002/runtime_stage/`；远端运行`code_v2`仅含已记录的队列模块改名，公共源码字节不变。
- 原候选：`runs/ordinary_gpu_probe_20261002/remote/queue_v3/results/gpu1002-moto5134-coder-a2/`。
- 恢复评分：`runs/ordinary_gpu_probe_20261002/remote/recovery_moto_a2_grade_v1/`。
- 小实验原件：`runs/ordinary_gpu_probe_20261002/remote/diagnostics/git_pack_v1/`，含脚本、完整命令与输出、四份普查/manifest、比较和清理。
- 脚本：`runs/ordinary_gpu_probe_20261002/diagnose_git_pack_v1.py`，SHA256 `cde64e1d4fa0420cdb28c0a35287900a8516f875e589d44c05cd07bbd6ed21f1`。
- 独立复核：`runs/ordinary_gpu_probe_20261002/reviews/moto5134_baseline_mismatch_review.md`。root执行、非执行者复核；不是另一轮盲静态审查。

外挂卷挂载已经解决，与本问题分开：使用Spheron ES virtiofs，`/mnt/volume1`可读写并已配置fstab，未重建卷或重启VM。
