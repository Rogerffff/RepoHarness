# 计划审查核对与今晚安排

2026-09-21 / B Codex。已逐项读源代码、冻结材料和交接路径；[另一 Codex 的四项意见](codex_plan_review_20260921.md)均成立，均采纳。无需再为这些澄清重跑整轮计划审查。

| 意见 | 本次核对与处理 |
| --- | --- |
| 旧 public_hints 混淆要求与事实 | 12 题字段完全相同；`render_user_prompt` 只渲染 issue，但 generate 仍把完整 bundle 写进公开容器路径。当前 `test_globs=()`，官方恢复由 test_patch 路径生成。公开角色卡和 v2 中性说明已要求分清需求、操作指令、待验环境声明；不把 conda/所有测试恢复当已验事实，也不自行取消禁止改测试指令。原 bundle 未改。 |
| CPU 交接不必等 12 题全部完成 | 原 S5 的措辞确有这种问题。改为第一波即交接成熟单题，余八题继续审；3–5 是目标而非开始单题运行的门槛。 |
| 零 P2P 仍需查回归 | 原始行确认 mypy-10424/16963 均为 F2P=1/P2P=0。私有卡补具体检查：F2P 内多行为断言、调用者与旧测试、未保护行为；不自动判坏题，也不称回归通过。此提示不交公开读者。 |
| history_refs.json 路径错误 | 实际是 manifest 的 history_refs 字段指向 `history/<id>/refs.json`；12 个引用存在。交接卡已修。 |

公开材料新增说明保存为 **`runs/swegym_quality_batch01_20260921_v2/`**。v1 包和 [v1 manifest](revisions/batch_manifest_v1.json)保留，当前 manifest 指向 v2。原 public/grading/validation 行、渲染 issue、base 源码、gold/test patch 与运行证据不变；变化是解释旧提示适用范围的中性说明。

## 今晚建议：先做复核，同时把 CPU / 基座入口准备具体

**暂不建议为了今晚马上运行基座而先租 GPU。** 这不是等待所有题完成或评分链重写；缺的是选中题从解题环境到基座服务的具体运行组合。

- 已有真实 RH2 replay CLI，支持 `patch-dir`、派生镜像及资格账本，评分半边可复用。
- 旧 `experiments/env_probe_20260909/cc_probe.py` 的求解端点是 DeepSeek，评分仍调用旧 swegym_probe；不是拿来就能运行的“本地候选基座→真实 RH2”入口。
- **修复镜像本身不等于修复已在 actor 生效。** Dask8597 的派生层主要 COPY wheels，pytest7.4.4 是在 revised_install 执行；Pyd8511 同样依赖离线安装包装器。需要把准备动作落实到 actor 的真实身份和工作流。Conan15422 属原环境对照范围，不应硬套派生修复。
- 当前 formal face 仍取 public image；单题可先选“独立 harness→真实 RH2 重放”的明确诊断范围，不必等正式训练加载接口。但不能用 root/grader 跑通代替 agent/54321 的开发条件验证。
- 本批模型 revision、精度、上下文、服务/tool parser、单题采样预算未固定；现有 J2 serving 默认是旧 Qwen3 的 TP2×2，不是已验单卡启动单。

执行上先按修订卡完成首批 12 题，第一波后及时整理 CPU 需求；方法校准后再按同仓小包扩展有价值的复核，不以“消耗额度”代替审查质量。剩余额度优先用于完整主审、独立复核与验证入口准备，不把 216 题一次铺开。选中题的 CPU 条件及一个模型的启动参数明确后即可租机；GPU 空等安装和输入歧义不会增加能力诊断信息。

若用户现在选择租机，也可以先在其 CPU/Docker 上完成前置、再开始 GPU 求解，但不能承诺本晚一定取得有效的基座比较。没有必要为这些环境前置租完整 8 卡。

**本次核对范围：**一个无历史上下文 sub-agent 只读核查探针就绪程度，主任务核对决定性脚本和材料；未执行历史项目代码、Docker、SSH、模型或改生产代码。审题任务的实际启动/收口另记 assignments / batch_report，不把就绪核查计入 12 题质量复核。
