# 第四组实施计划审查的窄 CPU 证据

日期：2026-09-15。角色：Falsifier / Simplifier。对象：同目录上一级 `impl_plan_20260915.md` 的 P-C / P-D。

本目录集中保存本轮 P-A / P-C / P-D 的复核探针；正式审查结论在[原实施计划 §5](../impl_plan_20260915.md#5-codex-实施前审查2026-09-15)。下表前三项由 Falsifier 提供，最后一项由 Training Semantics Reviewer 提供，四项均经主审独立运行。

三份脚本先通过 stdin 执行，再按主审要求保存正文与该次 stdout。主审独立复跑后，脚本补充了适用范围说明、整理 import，并对关键结果增加 assert；补充后再次运行并与保存的 stdout 比对。仅导入当前源码、使用进程内对象和自动清理的临时目录。未改实现或实施计划，未运行 Docker、SSH、API、模型或 GPU，未读取或影响 e1。`source_snapshot.json` 记录保存时相关源文件的摘要；工作区内容可能包含其它实施者已有改动，不能只凭 Git HEAD 重建。

| 探针 | 已观察到的结果 | 适用边界 |
| --- | --- | --- |
| [p_c_digest_probe.py](p_c_digest_probe.py) / [stdout](p_c_digest_probe.stdout.txt) | 按当前全字段 `model_dump` digest 算法，给政策增加空默认字段改变 v1 policy digest；给 manifest 增加默认零计数改变 v1 manifest digest；计数 0 → 1 再次改变身份。 | 用本地子类模拟计划新增字段；未修改生产 schema。证明计划需要明确旧格式 canonicalization 以及计数是否进入身份，未宣称新实现已经存在。 |
| [p_d_projection_probe.py](p_d_projection_probe.py) / [stdout](p_d_projection_probe.stdout.txt) | `delete config + add config/default.json` 两操作均应用时成功；若精确 official 清单包含 `config`，真实投影仅保留子路径，真实 `_apply_frozen_delta` 因 `mkdir` 遇到旧普通文件而报 infra。 | 当前 raw schema 仍拒绝父子形状；探针直接使用条目和轻量 source 对象，测试计划将放开的形状在后续真实投影/应用函数中的行为。只替换命令运输为本地临时目录执行，未调用 Docker。 |
| [p_c_cache_type_probe.py](p_c_cache_type_probe.py) / [stdout](p_c_cache_type_probe.stdout.txt) | 计划给出的名字过滤会一并省略同名普通文件、symlink 和 FIFO。若 baseline 中 `alias.pyc` 是目录软链而 post 中是目录及子文件，名字过滤隐藏 baseline 软链；真实应用函数原本拒绝该祖先，去掉该事实后会跟随软链写入。另，去掉 `.py` 后 `.pyc` 仍可独立执行。 | 名字过滤为计划表达式的局部展开，并非当前 census 实现；所有目标都在同一个自动清理的临时目录内，所谓“树外”仅指该目录内的另一个子目录。未证明选定任务已经存在这些路径，未据此判当前线上 P0。 |
| [training_semantics_probe.py](training_semantics_probe.py) / [JSON](training_semantics_probe_result.json) | 真实 pytest：基线 rc=0 且测试体执行；候选语法错误后 rc=2、测试体未执行，但当前 parser 的状态字典已有 1 项，manager 不进入零解析分支。 | 当前 binary 0 可以符合 SWE 官方参考项缺席规则；反例证明拟议 producer 覆盖有缺口，参考集合桶不等于逐项执行事实。提交用 JSON 仅替换本机路径前缀，原始日志在 JSON 引用的 git 忽略目录中。 |

在仓库根目录可用以下形式复核；将脚本名替换为上表任一文件：

```bash
PYTHONPATH=rh2/src rh2/.venv/bin/python -B docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch4_scoring_20260910/impl_plan_review_20260915/p_c_digest_probe.py
```

这些证据支持窄修订：缓存过滤保留对象类型与无法确认内容；旧政策/manifest canonicalization 显式兼容，计数放观察面；P-D 核对投影后的必要删除。它们不要求新的通用规则平台或重开已批准的方向。
