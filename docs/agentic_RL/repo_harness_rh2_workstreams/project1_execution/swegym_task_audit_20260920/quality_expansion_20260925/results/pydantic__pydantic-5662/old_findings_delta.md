# 5662 历史差异复核

root 明确 release 后，只读本题 history/refs.json 所列两份记录，SHA 均与 refs 一致。L1 指 2026-09-16 L1_pydantic 记录；pilot 指 2026-09-20 pydantic_pilot 记录。未扩读其中指向的 verification.json、旧脚本、其他题或汇总；因此旧实验只能作为“记录声称”的二级证据，不能冒称本次核验了其原运行。

| 旧主张 | 本次处置 | 决定性证据与边界 |
|---|---|---|
| 题面、base、ANY F2P、gold 对应；可以只改早返回 | 确认 | 封存前稿已完整核 main.py:540–561、test.patch 和 prompt；原09-19 noop目标断言失败/gold PASS。possible solution 不是唯一控制流形状。 |
| L1 check3 以题面完整判 actual input pass | 收窄/纠正 | 静态计划题面可用归check23；actual actor消息、system/hints交付、工具呈现未捕获，check3 unknown。 |
| L1 127个P2P都是模型间比较，dict不等未测，`return other == self`能通过全部128项 | 反驳；确认pilot的纠正方向 | tests/test_main.py:120–124的test_comparing和1985附近test_model_equality_dump明确有dict不等，且在expected并见原日志PASS。这个递归候选不能被当作已成立满分反例。pilot所述协议替身结果只读到转述，没有复跑或读其verification原件。 |
| L1 泛称__ne__/非模型全部未测；pilot整体标refuted | 收窄 | 普通dict的!=已有P2P；`m != ANY`、一般matcher返回True/False/NotImplemented仍无直接覆盖。不能把dict护栏推为一般回退完整覆盖。保持封存前稿的check25问题。 |
| 核心方法跨文件使用，因此gold已造成回归（L1 check26） | 纠正证据级别 | 跨文件影响范围只说明未测风险；gold模型分支逻辑保持、相关P2P有局部正证据。未证gold新增回归，check26 unknown，check27仅目标局部正确。 |
| 题面带方案，因此难度极低/几乎无训练信号 | 事实部分确认、价值判断未核 | solution_in_statement可直接从prompt确认；训练收益、成功率、模型成本没有观测。pilot将收益未知保留是合理的。不能据旧minutes=14填本轮成本。 |
| 与5386/6283同文件/主题，必须同侧；pilot对它们的修复关系作更细判断 | 未核具体关系；反对仅以主题推出必然同侧 | 本轮未获准读这些题，也未读其源码/轨迹；旧记录中的关系只作为待核引用。当前check5 unknown，不把pilot跨题断言当已独立验证。 |
| install rc=2、安装必须联网，是当前阻断 | 被本题后续grader原件替代；旧错误本身未核 | 09-19 install-v1两次install RC0、deny_all离线wheels、源码导入路径已核。旧R2不在本次开放原件内，未确认旧失败位置。替代范围只及该历史grader配方，actual actor仍unknown。 |
| 资产无缺失/文件恢复安全、控制面残余R4 | 局部确认/其余未核 | test恢复1文件、gold投影main.py、expected均执行为历史局部正证据；真实actor资产/权限不明，R4与全部攻击面未核。 |
| ready_for_probe、最低难度锚点正式可用 | 不继承准入标签 | 保持needs_review/static_review、development_diagnostic；需actual actor公开API验证和一般matcher覆盖核验。 |

与前稿的关系：本次不改初判、不改封存文件。新增历史上下文是明确撤回L1“递归坏解已能满分”的错误论据，并承认pilot已指出dict P2P；本次独立的ANY特判漏测和actor证据缺口仍成立。唯一优先下一步保持前稿：actual actor的小脚本验证ANY与一般matcher、dict/object护栏，并保存实际初态/解释器；没有本轮实验。


已读历史原件（仅以下路径，均核SHA）：
- `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_pydantic/records/pydantic__pydantic-5662.json` — `dcf38e3c95ffd74ad098e0aabb5aa637e72f3c727686c32478ffb32bdea2e3d4`
- `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/pydantic_pilot/records/pydantic__pydantic-5662.json` — `eeed1f17bc54d8e73966af6a8ef3e51a66e72558d5a7b58a390942100a58cabd`

封存前稿SHA256：`52020f450387949f9ca6ab48e185e4bfe86787e26240deec9889daccbfc24797`。前稿未改；无新项目执行。全部证据定位以本题analysis_before_history.md的PUBLIC/PRIVATE与原日志附录为准。
