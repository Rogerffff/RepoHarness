# 模型结束后的 root Git：公共屏障窄修

日期：2026-09-29。Owner：本线程 Codex（用户明确授权实现）；状态：实施中，未提交。来源：[探针 readiness §3A](../ordinary_probe_20260929/readiness_review.md)。

## 范围与决定

需要在真实候选继续经过该路径前修复。`env -i` 与可信 `PATH` 不能阻止系统 Git 读取候选 `.git/config` 后启动 filter、textconv、fsmonitor 等程序。已有证据限于容器内 uid=0 执行，不是宿主逃逸证据。

本片恢复已批准的“root 不执行候选程序”边界，不改 reward、loss、组准入或终止规则，无新 T0。保留停止 agent 进程、有界核零、双读、FrozenWorkspace 和原有失败码。双读改用现有可信 census；不增加一套扫描器或 Git 配置黑名单。

policy 随 `RolloutContainerWorkspace` 运输：正式物化按 task_id 选择一次，基线与屏障消费同一对象；冻结包装保存同一 policy。双读保留文件路径、类型、模式、内容摘要、软链目标摘要与排除区路径集合；不把 `CACHE_OMITTED_*` 纯观测计数变成拒绝条件。不在屏障解析候选路径/特殊对象，继续由 exporter 判 typed unsafe。

公共源码范围：`adapters/slime/quiescence_barrier.py`、`generate.py`。不修改 B 的 ingest、派生镜像、题单和评分规则。

## 探针接入边界

用户已确认：本线程完成公共修复、提供接口与验收要求；旧 SWE 探针由探针线程完成接入。本线程不并发修改其在制探针脚本。

- R2E 冻结导出调用公共屏障，会消费修复；重建 workspace 时需传 `census_policy=self.baseline.policy`，不能把 R2E `.venv/` 政策退回默认 v1。
- SWE 旧 `solve_attempt.export_candidate` 自行以 root 调用 status/add/diff，绕过公共屏障。本片不能据公共修复宣称它安全；需由探针 owner 切到现有 frozen exporter 与宿主受控渲染。其准备阶段可能产生 dirty 文件，基线必须来自实际物化后的树，不能盲用新起同镜像的字节。
- R2E `--legacy-gitdiff-compare` 同样执行候选 Git，不得用于真实模型。`s1_compat` 的旧文本导出不是当前 fa_formal 冻结路径，不在本片迁移范围内。
- 本片不代表整份探针 readiness 通过；评分信任、往返对账与运行器失败传播仍按原 owner 处理。

## 验收与停止条件

1. 本机一次性真实 Docker 中，修前 Git 执行标记证实 uid=0；修后同一候选配置不执行程序。无外网或付费模型调用。
2. ignored/untracked 文件内容、模式与普通软链目标变化会改变指纹；后台 agent 进程先停止；读取失败与双读漂移仍走原失败码。
3. 三种政策一致运输，缓存计数不影响指纹；不支持候选仍由 exporter 收口，不误升 run-fatal。
4. 正式编排 CPU 正控、预算归因测试和相关 Docker/导出回归通过。审查代理只检查本边界，不扩大为新的安全平台。

既有 census 对软链目标中的换行会删除换行字节，是独立的旧字节保真缺陷；本片不宣称修复所有软链表示问题。两次 census 会增加实际读文件量，成本证据需注明本机小树/合成树，不能外推训练吞吐。

## 验证记录

待实现后填写。同模型的分工复核不替代以后可安排的独立跨模型审查。
