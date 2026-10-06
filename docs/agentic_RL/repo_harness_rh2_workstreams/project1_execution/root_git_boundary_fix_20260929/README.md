# 模型结束后的 root Git：公共屏障窄修

日期：2026-09-29。Owner：本线程 Codex（用户明确授权实现）；状态：公共窄修已实施、本机验收与分工复核通过，未提交。探针消费仍由另一线程接入。来源：[探针 readiness §3A](../ordinary_probe_20260929/readiness_review.md)。

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

| 验证 | 结果与边界 |
|---|---|
| 新增维护测试 | 8 项通过：三种 task policy 的正式编排运输、缓存计数对照、4 个真实 Docker 参数化用例 |
| 公共边界 + 原屏障/预算/PATH/导出回归 | 82 passed，含真实 Docker，见 `runs/root_git_boundary_fix_20260929/pytest_targeted.txt` |
| 五目录非 Docker 快照 | 1856 passed、3 skipped、96 deselected、1 failed。唯一失败为共享工作区新增 `rh2.private_grading_bundle.swe_revision.v1` 后，`tests/contracts/test_full_registry.py` 的预期集合未同步；差异位于其他在制 `registry.py` / bundles，不是本片改动，未替其它 owner 修改 |
| 风格与 diff | 本片 ruff、`git diff --check` 通过 |
| 同模型分工复核 | Production Tracer 逐条核接线/出口；Falsifier 独立跑屏障/census 16 项、期限边界 1 项通过（与上表重叠，不累计成新覆盖） |
| 清理 | 本片一次性容器与 internal 网络均已删除；未登录远端，未跑 GPU / CC / 付费模型 |

Docker 反例使用现有 aiohttp 派生镜像，在正式 profile 的能力/资源参数及 internal 网络下构造小仓库。修前 root Git 触发候选 clean filter 写出 uid=0；删除标记后，修后停止/双读/调试回读/冻结导出全程不再产生标记。它不是全条正式 CC 链验收，也不是宿主逃逸证明。

旧屏障替身的匹配从 `git status` 改为 `RH2_QUIESCENCE_CENSUS`；预算测试仍将指纹读取放到停止确认以后再跨期限，原预期未翻转。snapshot_ref 改为 census 内容指纹，历史运行的 Git 指纹不回写或混作同一算法。

成本仅作范围说明：独立探针的 aiohttp 小树（58 条评分内容）单次 census 0.295–0.362 s；1 万个 1 KiB 文件的合成树 0.862–0.954 s。屏障现在执行两次 census；没有把 exporter 的后续扫描删掉。大仓库、训练并发下的开销需由现有成本观测记录，不把本机数字外推为吞吐收益。

证据位于 `runs/root_git_boundary_fix_20260929/`：`falsifier_results.json`、`falsifier_fix_review.md`、两份 pytest 日志、`verification.json`。同模型的分工复核不冒充独立跨模型审查；后续 Claude 可直接复核本片 diff，但无需为此重复申请已授权的修复。

公共切片停止条件已满足。交探针 owner 的具体接口与验收见 [probe_handoff.md](probe_handoff.md)。旧 SWE/R2E legacy Git 导出和本次发现的 LF 软链字节问题分别保留记录，本片未静默认定已修。
