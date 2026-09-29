# 首批 CPU 队列有界交接审查

2026-09-21。审查范围：`batch_report.md`、`cpu_queue.json`、`probe_candidates.json`、`acceptance/cpu_entry_plan.md`；按具体疑点追读配方、现行入口源码、少量逐题 review 与公开源码。未重新完成十二题质量审查，未重新核验历史得分。

**结论：没有发现阻塞选择性交接的实质问题。** 14 条可作为后续实施和运行任务派发；`mature_for_cpu_handoff` 只能表示方案已收敛，不能解释为命令已全部实例化、actor 入口已实现或运行已通过。当前文件已经明确这一区别。

## 实质必修

无。本轮没有发现必须修改原题、测试、gold、评分参考、生产实现或队列才能交接的问题。

以下已披露的执行前提仍然有效，不是本审查新增闸门：CPU/Docker 与镜像可用性、薄入口实现、实际 actor 的安装/启动环境，以及每次执行的路径和补丁冻结。未具备这些条件时可以交接实施，不能签发 actor 运行验收。

## 已核对的关键边界

| 项目 | 有界核对结果 |
| --- | --- |
| 14 条与候选映射 | 14 个 queue ID 唯一；5 个候选及 7 个未优先题的队列引用均存在且任务一致；所有逐题 review 和配方引用存在。 |
| 已运行与计划 | 四份入口文件均将本轮标为静态、未执行；历史 grader 结果与待做 actor/语义 CPU 分开。没有拿派生镜像存在或 agent 应用补丁冒充 actor 开发已验。 |
| actor 与 grader | 薄入口复用 `run_agent → exec_and_wait → DockerSandbox.exec`，明确 agent、HOME、工作目录和 shell；源码与所述调用链相符。`_candidate_stage` 被明确排除为 actor 替代品；原启动条件与诊断环境分开留证。 |
| actor 入口状态 | 尚未实现的薄编排、无模型 HTTP/tool-use fixture，以及真实 CC Bash 工具验证的剩余边界均有明示；没有冒称完整 generate 或真实 CC 工具已经运行。 |
| 当前 replay CLI | `rh2/scripts/replay_grade.py:121–136` 支持队列所用 flags 和裸 instance_id；`adapters/slime/replay_grade.py:708–724` 对 `patch-dir:` 读取 `<instance_id>.diff`。Dask8597 的带来源 task_id 不妨碍裸 ID 唯一解析。 |
| revised_install | 六份 Dask/Pydantic/DVC 安装 recipe 确有 `original_install/revised_install`；wrapper 必填 `--code-root`，队列中显式 wrapper 命令和入口单均已给出。仅传派生镜像不足以消费这些安装替换的说明正确。 |
| mypy install_wave1 | 三个 `image.json` 都只有 COPY wheel 与离线 pip ENV，没有 `revised_install`；三条队列均明确使用原 replay 与冻结 derived-image。10424 的原镜像初态、额外 types-typing-extensions 要求、三个 wheel 不是完整锁定的限制也已保留。 |
| 退出与评分 | 队列要求逐题 outcome/reward/stage_error、测试身份和清理共同对账；不把进程 rc、额外测试失败或 final_status 单独当作 reward，符合现入口的收口语义。 |

上述 `adapters/` 前缀为 `rh2/src/repoharness2/`。没有启动源码中的入口；仅静态读取。

## 实验是否有区分力、是否过度设门

- Conan15422、DVC5839 优先解决真实 actor 和公开行为；有限开发诊断没有被附加全仓或私有错误候选必过门。
- Dask8597 的配置部分修复、Pydantic8511 的 base/gold/窄修正版、mypy10424 的关闭收窄候选，各自检验具体未决假设；其语义结果与后续 actor 条件分列。没有要求其他十一条先全部完成。
- Conan14177 的公开接口替代解，以及 Dask8801 的仅文案变体/仅列表变体，分别控制接受性和漏测，不是同一实验的重复表述；文案首轮保留 `path!r`，不会把路径格式与措辞混为单一变量。
- Pydantic5706 明确只核现配方、投影和当前 RH2 适用性；不要求重跑旧脚本来重证 09-16 已回读的矩阵。同一新配方下保留 base/gold/候选是必要对照。
- DVC9395 保留 dry/非 dry × base/gold 四组独立初态，非 dry 是操作能否到达目标的正对照；没有把 checkout 次数或全部 remote 分支增成必修。
- DVC3620 优先数据丢失错误控制，symlink-only 只是范围量化备选；CPU 不替代 hardlink 公开义务的需求判断。
- mypy16963 先做完整公开原例的 base/gold，未预先扩张成多种变体；mypy12417 的 P/E 恢复候选区分 subject 类型变化与整个 body 跳过，四组具有不同解释价值。

未发现必须删掉的无区分力重复实验，也未发现遗漏会使上述首轮问题无法判别的关键正负对照。

## 可选改善

1. **DVC5839 的导入证据注明注入条件。** 临时目录 CLI 草案显式设置 `PYTHONPATH=/testbed`，因此其成功证明该条件下源码可执行，不能单独证明 editable 关联已正确安装。共同条件已经另要求配方消费/导入证据；执行记录只需保留这个区别。若要直接验证临时目录的默认关联，可加一次不注入 PYTHONPATH 的导入，不必另开整组实验。
2. **DVC3620 冻结负对照时给出明确块替换。** 精确 base 的 `dvc/remote/local.py:412–424` 是 `copyfile → remove → rename`，不是已有 `os.unlink` 插入点。队列的“链接分支只 unlink 后 return、跳过复制/rename”意图清楚；生成实际 diff 时应明确用 `os.unlink(path); return` 替换该分支操作，避免误在既有复制之后插入，改变预定最小候选。

两项是实施记录和补丁冻结的精度改善，不阻塞现方案交接，也不增加全批必过实验。

## 本轮验证范围

自行编写的只读元数据脚本检查了 JSON、队列引用、配方字段、草案中 Python heredoc 的语法，以及显式 pytest 目标文件存在性；另直接读取当前 CLI/wrapper、物化与 launcher 代码，抽核 Conan/Dask/DVC 具体调用点。未导入或执行历史项目代码，未运行 pytest、安装、容器、SSH、模型或历史实验脚本；未验证节点实际收集、镜像当前可用性或运行行为。只新增本审查文件。
