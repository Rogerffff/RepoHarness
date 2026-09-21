# 19:00增量：长评分被清扫、PID上限与处置

2026-09-19 / B Codex。仅实验配方、运行隔离与证据处理；未修改Claude拥有的生产代码。

## 1. 真正的RH2链路问题

`SWEGradingManager.startup()`按共享`rh2.grading.owner`标签扫描，把属于其它manager且创建超过3600秒的容器删除，没有检查其owner是否仍活跃。代码中的“一小时后必是孤儿”假设被本批长测试推翻。

- MONAI763 v1e gold从17:25持续运行，18:53:11收到Docker signal9、退出137，18:53:14被删除；同一时间Modin5940的下一条gold启动manager。最后采样仍在计算、约13.4GiB峰值，未见OOM事件。Docker事件没有对应OOM事件。
- 用**独占标签**的活跃sleep容器做反例：只把创建时间标签写成两小时前，同命名空间的新manager确实删掉它；换命名空间后存活。两个探针容器均已清理。实际源文件摘要及结果见`runs/env_recipe_repair_20260919/namespace_probe_1909.json`。
- 被删MONAI的报告变成`official_bad_codes_after_successful_replay`、reward None；完整测试未完成。sidecar却写`log_partial=false`，测试退出码缺失、峰值不可读；driver最后还写有`containers_open`及清理错误，但CLI返回0，原实验runner只看候选容器清理，因此已自动启动noop。这些都不能当环境失败或验收通过。

**给A/Claude的修复建议：** 跨manager清理须验证所有权/存活状态，不能用容器年龄代替；按本run收口仍保留。CLI应核对grader收口结果并暴露中断事实，不能仅凭候选清理成功继续派发。此处已有反例与事件证据，无需重跑216题。

## 2. 本批如何继续

- E24：后续诊断通过已有`GradingManagerConfig.label_prefix`使用各批独立命名空间；不关掉自己的清理、不抬“孤儿年龄”来掩盖生产问题。`numeric_v1f`只补被中断的gold，复用同一不可变镜像、源码、配方、预算与资源，等待v1e noop结束。原noop只有完整通过预期检查，并核对镜像/脚本/资源/预算逐项相同后才可配对。
- 后续runner同时审查driver末尾的manager收口记录；分析脚本另查真实测试结束标记，不盲信`log_partial=false`。已回查先前163题的326条driver收口记录，没有发现同类遗漏，见`driver_close_audit_1909.json`。
- 旧S3 v1父派发器已暂挂，**当前noop子进程继续到有界收口**，避免再启动共享标签manager误删活跃MONAI。`retire_superseded_s3.py`仅在driver退出、无残留及清理记录正常后结束该父进程，写`superseded.json`与明确的未执行题目。不要手动恢复其旧派发。

## 3. Modin的新资源证据

6937恢复Moto4和4GiB临时盘后，在512个进程/线程处触发cgroup拒绝。宿主内核也记录了该容器的fork拒绝。Moto服务自身121线程，pytest73线程，加上Ray worker与服务线程合计达到上限；当时临时盘仍有约2GiB、未见OOM。因此这次卡住不能再归因于临时盘。

E25：`modin_s3_compat_v2`对两题试验**PID1024**，其它2CPU/8GiB/4GiB临时盘、Moto4、测试和参考不变，并采用上述独立命名空间。这只是本题服务配方的有界对照，须观察实际峰值，未设为全池默认。原材料403/404、过时xfail的隔离条件仍保留。

旧S3 v1剩余三个case由v2替代，不反复跑已明确缺少PID容量的版本；旧结果与未完成事实完整保留。仍须审阅旧noop及v2完整两侧，不能用“隔离”核销组件诊断。


## 20:10更正：PID拒绝是后果，6937的上游故障是日志管道阻塞

PID1024没有完成6937测试。来源fixture将Moto stderr接到不消费的PIPE；现场一个服务线程卡在`pipe_write`，其余线程等锁。独立断网/UID54322探针在1078请求后复现，排空65263字节日志即恢复同一服务；改文件输出后4096请求及S3对象读写成功。因此E25的容量假设已被进一步证据修正，不能把1024定为正常需求。新v3仅修6937服务日志、回到PID512完整复验；原测试与参考不动，日志保留为候选诊断输出。5940原fixture使用DEVNULL，不套用该根因。细节与探针限制见E26；其S3材料隔离仍未解除。
