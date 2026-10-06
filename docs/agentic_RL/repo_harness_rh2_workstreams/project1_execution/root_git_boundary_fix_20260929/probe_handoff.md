# 给普通基座探针线程：root Git 修复的接入与验收

日期：2026-09-29。用户已分工：A Codex 修公共屏障；探针线程负责 SWE/R2E 脚本接入。此文是交接材料，落盘不代表已通知对方。

公共实现已在共享工作树、本机验收通过，未提交；证据与已知范围见 [README](README.md)。本片另观察到全目录回归的注册表测试与其他在制 SWE revision schema 未同步（1 项失败），应由对应 schema owner 核对，不要通过跳过测试处理。

## 公共接口

`DockerQuiescenceBarrier.establish(workspace=..., audit=...)` 签名、返回联合类型与失败码不变。当前实现先停止 agent 进程，再用可信 census 双读，最后返回 `FrozenWorkspace`；不再调用候选 Git。

`RolloutContainerWorkspace` 新增内部字段 `census_policy`。正式 RH2 物化时按 task_id 选择一次，baseline 与 barrier 共用。探针已有 baseline，应直接传它：

```python
ws = RolloutContainerWorkspace(
    docker=self.docker,
    container_name=self.container,
    testbed_path=spec.workdir,
    census_policy=self.baseline.policy,
)
q = await DockerQuiescenceBarrier(spec.workdir).establish(workspace=ws, audit=audit)
# 仅 QuiescenceConfirmed 才交 export_frozen_patch(q.frozen_grading_workspace, self.baseline, ...)
```

R2E `r2e_solve_attempt.py` 在生成基线和结束后导出时分别构造 workspace。**导出时那一处也必须传 policy**；R2E 不能依赖默认 v1，否则会把 `.venv` 当作评分内容全量扫描。`FrozenWorkspace.verify_integrity()` 也使用保存下来的同一 policy，但正式链不需要恢复“评分后回读旧容器”。

指纹现在包含评分树的路径、类型、执行位、内容与普通软链目标摘要；`.gitignore` 不影响它。排除区仍只按既有路径集合语义，`CACHE_OMITTED_*` 计数不参与稳定性判定。snapshot_ref 的值会随算法改变，它是 attempt 内的运行时证据，不是旧 Git diff 的可比较摘要；原始历史证据不回写。

## SWE 需要实际替换的入口

`base_probe_20260922/solve_attempt.py::Attempt.export_candidate` 自己 kill 后用 root 执行 status/add/diff，**完全绕过公共屏障**。不要只换 PATH、追加 Git 配置开关、或者在原导出之前调用一次新屏障；后续 root Git 仍可重新启动候选程序。

使用现有的 `generate_baseline_manifest` → 公共屏障 → `export_frozen_patch` → 宿主受控渲染。R2E `render_git_patch` 的宿主临时裸仓库可作为复用入口：只接收冻结字节，关闭系统/全局 Git 配置，并以 `--no-filters` 写对象，不读候选 `.git`。

SWE 有可选准备步骤，可能让初态文件已经 dirty。基线清单必须在这些步骤结束后、模型启动前生成，且渲染所需的旧字节必须对应**该实际基线**。不能无条件照搬 R2E 的“另起同镜像取旧字节”，否则会漏掉 prep 产生的修改或摘要不匹配。宿主 `.diff` 只是回放运输载体，必须核对冻结工件与回放结果。

R2E `--legacy-gitdiff-compare` 仍会重新执行候选 Git，不属于安全接入路径。真实模型入口应移除该调用；历史反例证据保留。`s1_compat` / manager 旧文本导出也不是本次已修路径。

## 接入后最少核验

| 场景 | 应看到的结果 |
|---|---|
| 模型留下 `.git/config` 执行标记（filter/fsmonitor/textconv 等） | 整个停止、导出与诊断流程均未执行标记；没有结束后的 root Git 回读 |
| 含 ignored `.so`、untracked 普通文件、模式变化、普通软链 | 冻结工件保留这些变化，渲染和回放不丢失 |
| SWE 的 prep 已修改跟踪文件，模型再改另一处 | 候选只表达相对实际基线的变化，旧字节与基线摘要一致 |
| R2E `.venv` 与 SWE 缓存 | 使用各自 baseline.policy；缓存计数不变成拒绝条件 |
| 屏障拒绝 / 导出失败 / unsupported | 不送成空补丁评分；保留原有 infra / unsafe 区分和清理事实 |
| 正常修改与 noop | 正常冻结、渲染、回放仍可完成，失败状态不会被外层返回 0 掩盖 |

这里最后一项与探针原有失败传播工作相交，由探针线程一并核对。本公共修复不核销 readiness 的评分信任问题、R2E 基线排除区摘要问题或完整训练验收。

已知独立旧缺陷：census 的 `readlink | tr -d '\n'` 会删除软链目标中的换行；本轮没有更改该表示合同，也不宣称任意软链字节已完整支持。
