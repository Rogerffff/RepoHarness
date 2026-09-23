# e1 独立复核 / Codex / 2026-09-16

**补齐两项验收后，e1 评分接线可以收口。可以继续已批准的 P-B，再做 e2；不能把本次结论扩大为环境池或训练链验收。** 新发现一项真实存储兼容性问题，已修订运行手册；没有修改生产代码、内核设置、Docker daemon，没有启动 P-B/e2 或提交。

## 1. 验证结果

原报告的四题矩阵缺少最终条件下的 pandas noop，§6.6.10 要求的候选段人为超时也未做。本轮各补一条，均使用远端真实 driver、冻结/投影和正式 grader profile。

| 题 | noop | gold | 核对 |
| --- | --- | --- | --- |
| mypy-12741 | F2P 0/1，reward 0 | F2P 1/1，reward 1 | 原两次逐参考状态与 oracle 一致 |
| conan-13326 | F2P 0/3，reward 0 | F2P 3/3，reward 1 | 同上 |
| dvc-5822 | F2P 0/1，reward 0 | F2P 1/1，reward 1 | 同上；gold 测试 RC=1 来自非参考测试失败，不能改写 reward |
| pandas-48106 | **本轮补跑：F2P 0/16，reward 0** | F2P 16/16，reward 0 | 两侧均缺同三个 P2P ID，逐参考状态与 oracle 一致；gold 的 NO 是既知来源例外 |

pandas noop 安装 **592.13 s**、测试 **13.88 s**、整个 trusted setup **9.62 s**，运行器摘要未变，完整日志与工件可查。这与原 gold 的重编译/测试形成有效对照。前三题是原执行条件，pandas 是去掉 `-u`、开启 metacopy 后的结果；不是四题在同一最终机器配置下重复多次的性能实验。

另用 conan gold 加入函数内 `sleep(120)`，施加 **90 s 保护性评分期限**：安装 RC=0、测试开始与收集标记保留，`log.partial=true`，`reward=None`，候选及 grader 清理完成。它验证期限收口，不验证候选可归因超时给 0 的新 producer。该次内存读数标为不可用，不能把字段中的 0 当实际用量。

原 10 行账本/日志/工件核对通过；原七次测试及新增 pandas 的参考状态均无 oracle 差异。本轮主审相关测试 **82 passed / 1 skipped**，S1 正式接线 CPU 探针 **5 passed**。远端最后快照无容器残留，实例保持运行。

## 2. 一个需要立即修正文档的真机问题

**M1 / P1，`production_observed`：当前 overlay2/metacopy/native-diff 组合会损坏 `docker commit` 的文件内容。** 本机内核参数为 Y，实际 upper 文件也有 `trusted.overlay.metacopy`；Docker 28.1.1 却显示 `Using metacopy=false`、`Native Overlay Diff=true`。主审临时文件对照：

- 新建 32 字节文件，第一次 commit 后内容正常；只改属主后，容器 merged 视图仍读到原内容。
- 第二次 commit，再开新容器：长度仍为 32 字节，内容变成**全 0**，摘要与 upper 层零内容一致。
- 同样改属主后完整写回原内容，metacopy 属性消失，再 commit 的摘要保持不变。所有临时容器/镜像已清理。

这不推翻从 merged 视图执行、没有 commit 的 e1。它阻止的是把“直接写 metacopy=Y”当作可无条件复制的机器前置，以及在当前组合下使用这条导层路径制作派生镜像。**不能外推所有构建器都受影响，也没有证明重启 daemon 就能修复。** 已修订 [runbook §0.5](runbook_s1e.md#05-d3-权限准备与存储驱动2026-09-16-主审修正)；D4 前由实施者验证具体构建路径或使用兼容配置，普通 e2 仍可使用已验证的原镜像。

Docker 的 metacopy 状态在初始化时检测并保存，native-diff 路径直接打包 upper/diff 目录；源码支持上述机制，但“只有热切换才出错”没有被本实验验证。[Moby 28.1.1 overlay2](https://github.com/moby/moby/blob/v28.1.1/daemon/graphdriver/overlay2/overlay.go)、[metacopy 检测](https://github.com/moby/moby/blob/v28.1.1/daemon/graphdriver/overlay2/check.go)、[Linux 6.8 说明](https://www.kernel.org/doc/html/v6.8/filesystems/overlayfs.html#metadata-only-copy-up)。

## 3. S1 修正的准确含义

真实 prepared → `Rh2MilesGenerateFn` → fa_formal → integration `DefaultDataBuffer` 的 CPU 对照确认：file→dir、dir→file 不再 run-fatal，但该成员不评分，**整组被 DROP，连同已有可信评分的兄弟成员**；普通修改对照正常进入 buffer。不能把 completed 写成“候选已评分/可训练”。

旧 [A-prime §4/§8](../../fa/pending_t0_frozen_patch_artifact.md) 已批准尚不支持的父子冲突走 unsafe，06 的 A2 已批准对应整组 DROP，**无需重开这项授权**。但用户新批准的普通 file→dir 支持仍未完成：S1 是过渡止血，P-D 仍须实现正常冻结/重放往返。

随 P-D 处理两个局部余项，不另立 e1 阻塞：

- **P2，`production_reachable`：拒绝详情丢失。** exporter 的结构错误没有填 `object_path/type`，正式 receipt/audit 最后只剩 `unsupported_delta_shape:?:unknown`，工件未保存且 workspace 已清理。driver 能记文本错误，不代表 rollout 也保留了它；应复用现有审计出口保留具体冲突路径/原因。
- **P2，反例为 `test_only`：catch 范围过宽。** 包住整个 `FrozenPatchArtifactV1` 的 `ValidationError` 会把注入的 exporter 排序 bug 也归为 unsafe。当前没有证据证明生产已产生这种排序错误；非法 entry 的另一对照仍 fatal，不能说“所有内部错误都被吞”。P-D 时只转换明确支持范围外的形状错误，其它内部矛盾保留原分级。

## 4. 报告勘误与下一步

1. pandas 三个缺席 key 是**单/双反斜杠差异叠加空格截断**；当前 parser 也截断。三个 key 对应 2、2、3 条完整案例，不能称为“一一对应 ID 映射”。本轮不改参考表，留环境流水线处理。
2. mypy 安装段末命令实际为 `hash -r`；`pip install -e .` 失败而段末 RC=0。观测本身从 `/testbed` import，CWD 即可解释路径，不能据此证明可编辑安装。本题 gold/noop 差异证明所测修复被消费，不证明所有纯 Python 候选都不受安装影响。
3. 原十次运行整体内存峰值 **2406 MB**；≤1097 MB 只适用于原七次进入测试的运行。trusted setup 包含多项操作，不等于单独 chown 计时；原 180→11 s 等单项数字在原交付目录缺少直接对照记录，不外推未来吞吐。

**建议：**按已审范围推进 P-B，然后同步当前源码再跑 e2；远端 exporter/generate 尚是 S1 前版本，其他本轮核对的评分核心文件与本机一致。P-D 与上述审计余项一并兑现；[§14.2 的既有三项余项](../swe_grading_wiring_20260915.md#142-三项余项不阻塞-e1)仍按原分期处理，不重开已定 reward/准入语义。

[可共享证据摘要](e1_codex_review_evidence_20260916.json)保存源码摘要、补测、ID 反例及存储对照。原始下载/复跑位于 `runs/swe_grading_e1_review_20260916/`（忽略提交）；历史 e1 证据未改写。停止条件已满足，本轮没有扩大题池或安排新训练实验。
