# getmoto__moto-5960 — 精确历史对照

独立初稿 SHA256 `661f583b8a2b7537079e300826f6d5f08ba62b63250c6c1412f92eab5ea7d801`，mtime 2026-09-20T21:47:42.892063Z；协调者于 21:48:04.328918Z（2026-09-21 05:48:04.328918 SGT）核SHA、封存并开放历史。初稿没有回写。

只读取本题 `runs/swegym_quality_batch03_20260921_v1/history/getmoto__moto-5960/refs.json` 所列 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_moto_2/records/getmoto__moto-5960.json`，SHA256 `c513f621fac79a758ea04bf1dd4663de0871e9f663b20b15835580ce28ed4b5a`。未跟随其 repo_level、其他题或216题材料引用，也未读旧聚合/reviewer。下文 ROOT/P/Q/E 含义同初稿。

| 旧主张 | 本次判定 | 决定性原件与范围 |
|---|---|---|
| query 已 copy/project，scan 没有；方向可由公开源码推出 | 确认 | P/base/moto/dynamodb/models/table.py:39–59,747–766,802–858；helper 和旧 query 都公开。路线合理，不强制“照抄”其实现 |
| 只可改 moto/ | 限定/不照搬 | 本次 public_hints 写的是 NON-TEST source files，hygiene 是官方精确文件加保留路径；未发现一条普遍 moto/ 路径白名单。当前合理修复位于 moto/ 不等于只有该路径合法 |
| 题面完整，所以实际输入检查 pass | 部分确认 | 本次 public_bundle 的 issue 完整；实际 actor 消息/工具初始状态没有捕获，不能由 JSON 推出真实交付无丢失 |
| F2P 的 LSI 与 GSI 差异实践上“不构成额外要求” | 降为有依据的范围解释，未裁定 | 公开问题两例均 GSI；LSI F2P 是额外对象。共享 SecondaryIndex.project 文档和旧 LSI query 支持泛化，却不能据 gold 便利性排除 GSI-only 合法路线争议 |
| 漏 deepcopy 会永久裁剪原 Item | 确认副作用；“判分全绿”保留预测 | Item.filter:395–411 原地 pop；Table.scan 收集存储对象；F2P scan 后无复读。旧记录 by=static，next_experiment 自己仍提议真实 grader 验证，未提供执行过该候选的记录。不能将“能全绿”升级为已观测 reward1 |
| 155 P2P 各自建表、因此全部不足以检出，216题/全目录都无复读 | 不扩大确认 | 本次完整读 155 节点名单，但只展开相关函数；主文件直接 indexed scan 基线只有 invalid index 与 ALL+ProjectionExpression。支持当前具体缺口，不证明所有目录/全池均无相关测试 |
| 测试弱点主要是漏 deepcopy | 新增独立缺口 | 公开第二用例明确 GSI KEYS_ONLY **scan**；同名 P2P 只有 query，新增另一 F2P 是 LSI scan。I1 是直接需求缺失，不依赖历史弱点才能发现 |
| gold 正确且最小；copy大表有性能代价 | 核心路径与已有运行支持，保留未穷举 | gold 复制后逐项 project，保留键与原存储；install_wave1 gold 实际2 F2P、155 P2P全通过。没有新资源失败证据，不能因copy推性能阻塞，也不证明所有过滤/分页组合 |
| 离线 make init rc2 是当前障碍 | 对本次引用条件已过时 | E/image.json 增层COPY/ENV只是离线准备；gold日志414–570、noop392–548实际make init与安装成功，ledger install_skipped=false、install_rc_last_command=0。原spec未跳过，不能把旧失败带入新配方 |
| 参数ID两条塌缩成一键，均pass、当前无误判 | 独立确认 | gold日志756–757、noop1009–1010两个完整[use …]均pass；158执行节点→157解析键→2+155冻结引用。noop-rA PASSED先FAILED后，不主张泛化mixed失败被遮蔽 |
| hints仅维护者致谢，因而无泄漏 | 不适用于本次实际提示材料 | public_bundle.public_hints 是通用工程/harness说明，不是致谢。冻结公开render路径可读，但正式actor可见Git/缓存/挂载/网络未验证，故不能给全面无泄漏pass |
| proposed `test_dynamodb.py::test_scan_pagination` | 修正引用 | 本次公开该主文件无此函数；真正读到的 `test_scan_pagination` 在 `tests/test_dynamodb/test_dynamodb_table_without_range_key.py:505–524`，也不在唯一正式命令中。带range文件的scan_by_index为ALL，不能视为KEYS_ONLY扫描覆盖 |
| ready_for_probe；旧cost18分钟 | 不承袭处置/成本 | 本轮统一needs_review/static_review，目标是development_diagnostic；无真实actor或候选实验。旧minutes不当成本次observed成本，未知值null |

封存后新增的只读逐引用对账：两个真实日志按冻结 parser 的空白取键规则做 stdlib 文本对照（未导入/执行 parser）。gold F2P2/P2P155全部PASSED；noop仅两个F2P FAILED、155 P2P PASSED；两侧missing和parsed-extra均空。该对账支持已观测评分解释，不弥补测试充分性。

封存后单位限定：初稿环境表第一峰值曾写“252.594MiB（原字段MB）”。原件只提供字段 `mem_peak_mb`，本轮未核实其单位定义或做任何换算。最终 card/record 仅记录原字段名及值252.594（gold）、297.359（noop）；不把它们标成已确认的MiB。初稿字节保持不变。

历史没有改变主优先级：先验证公开 GSI KEYS_ONLY scan 的缺口是否容许不完整修复获原满分；漏复制副作用作为独立覆盖风险保留，LSI范围与解析身份分别评审。所有增测、候选、parser/参考迁移仅建议，未实施。
