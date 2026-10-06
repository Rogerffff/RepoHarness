# 第二批中途抽查

2026-09-21 03:47 SGT，根任务。第二批尚未完成；本页只记录已查原件，不代替逐题独立复核或最终验收。本轮未运行项目代码、测试或容器。

| 已核事实 | 对后续审查的影响 |
| --- | --- |
| DVC3576 的旧 `stage1_offline_20260910` gold 日志含 requirements、离线依赖和构建相关错误；其 `status_map.json` 还含 `Could`、`No` 两个 ERROR 伪键。 | 旧“安装干净、无解析污染”不能保留；也不能把这些旧故障归给 09-19 `dvc_install_v1c` 已验证组合。主审已区分版本。 |
| mypy10308 的材料 wrapper 按 `materials["tasks"][instance_id]` 取输入；每次运行输出的同名 `materials/materials.json` 是审计记录。 | 复现入口必须使用 `materials_v2/materials.json` 输入表；“有一个同名文件”不足以重建运行条件。 |
| Pandas48106 的 `pandas_meta_v3` wrapper 仅在传入 `--bindings` 时启用原有参考绑定。 | 接续实验须保留当时的绑定文件及配方；这是恢复既有运行条件，本夜没有改变评分规则。 |

定位：前项日志在 `runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/iterative__dvc-3576/gold/offline/a1/`；mypy 输入/脚本在 `runs/env_recipe_repair_20260919/materials_v2/`；Pandas 入口、绑定和摘要已登记于第二批 `assignments.json` 的 `replay_entry_static_verification`、`environment_replay_inventory`。

DVC3576 的 stderr、缺失值等公开目标与测试覆盖的关系，mypy10308 的原题复现覆盖，仍由主审和独立 reviewer 分别完成；这里不提前批准题目，也不把静态反例建议写成运行失败。后续 CPU 方案必须继续区分真实 actor 开发条件、评分侧已修复环境和题目语义。

## 04:09 补查

12 份公开稿的角色登记和封存摘要一致；DVC reviewer 的三份独立初稿均在开放任一主审结论前封存，摘要未变。见 `batch02_interim_metadata_check.json`；这些记录不能证明操作系统强制隔离了读取权限。

- **DVC4166 身份碰撞成立，错误 reward 尚未实测。** 根任务直接核了 gold 原日志 `evallog_replay-er19-dv1-iterativ_ce06dec1.eval.log:980–981` 的两个前导空格参数节点，以及 `rh2/src/repoharness2/envpack/swegym_parsers.py:44–55,93`：按空白取键、同键后写覆盖。两个节点都归到 `test_match_ignore_from_file[`。现有两项均 PASS，不能写“某一项永远无效”或“已发生漏判”；混合结果及正常 pytest 的摘要顺序仍需定点验证。本次未执行 parser 或候选。
- **DVC1681 的具体替代路线有源码依据。** base `dvc/stage.py:494–579` 在 load 时设绝对 wdir，dumpd 保留绝对值，dump 写文件时转相对，checksum 仅忽略 `.`；test.patch 新增对 dumpd 内部表示的断言，另外两项通过 Mock 提供校验字典。因此“只在 checksum 输入正规化”的替代解与“把真实 wdir 一律抹成默认值”的部分实现值得分别做行为/评分对照；完整补丁和实际结果仍未验证，不能据此已经定性误拒或假阳性。

本轮没有要求修改生产 parser、题面或测试。第二批尚未验收，第三批保持只准备材料、未派发。

## Moto7584：04:11 新仓库抽查

根任务读了完整公开 prompt、gold/test.patch，以及 base `moto/sns/models.py:502–551,699–718`、响应层的 subscribe/delete_endpoint 调用路径和 endpoint ARN 构造。公开序列是**先订阅→删 endpoint→对同一 topic/endpoint 再订阅**；隐藏 F2P 删 endpoint 前没有订阅。源码删除 endpoint 不删除 subscriptions，gold 把新校验放在返回既有订阅之后，因此它没有覆盖公开序列的同一执行路径。这是静态控制流证据，原例尚未运行。

另一个已核事实是 endpoint 本身以 `arn:` 开头，gold 与精确测试又拼接 `arn{endpoint}`；公开错误例没有这段额外前缀。gold 注释和 `aws_verified` 标记声称匹配 AWS，不能替代可追溯的实际服务证据，也不能直接裁定公开题面或 gold 哪个应改。先在后续获授权 CPU 模拟环境中做“首次订阅 / 已有订阅”的原序列对照，分别核异常类型、消息和旧订阅是否返回；再决定材料处置。此处没有访问 AWS、运行候选或给未来公开读者提供私有线索。

## Pandas48106：剩余参考身份问题

根任务沿本题 `private/run_refs.json` 回读 `pandas_meta_v3` 原日志和 `recipe/pandas-dev__pandas-48106.reference.json`，并核 `reference_bindings_v1.json` 的本题条目及 `reference_bindings.py`。当前3组显式绑定覆盖7个Period节点，修订后3个missing确实消失、P2P率为1；它并未覆盖另外2组时区别名。

gold日志 `evallog_replay-er19-pandas_meta__1160016c.eval.log:5133–5134,5691–5694`、noop日志 `evallog_replay-er19-pandas_meta__67b00d26.eval.log:6112–6113,6654–6657` 给出两个 `datetimeindex_tz`、四个 `partial_slice_non_monotonicity` 完整节点，六成员均PASS。它们的名称在原parser按空格取键后分别合并，显式绑定仍未覆盖；这是参考身份缺口，不推翻这次实际全通过及既有0/1对照。

noop 的16条FAILED摘要在6968–6983行，晚于PASSED摘要。因此必须区分测试执行顺序与parser实际读到的摘要顺序，不能将“早失败、晚通过”直接当成隐藏失败反例。后续仅对这两组做符合实际摘要形式的混合结果、skip/xfail及缺席检查，再判断是否需要版本化绑定修订。本夜未运行parser或改变参考集合；Pandas整包尚待独立复核收口。
