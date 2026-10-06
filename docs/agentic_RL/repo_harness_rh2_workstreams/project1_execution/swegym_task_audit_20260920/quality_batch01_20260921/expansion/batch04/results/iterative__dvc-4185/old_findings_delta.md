# iterative__dvc-4185：旧结论差分与封存后补充

2026-09-21；协调者确认初稿 SHA256 `46933a127ba240a729f8fbcd230c21fb3e37f012e17c58795eba6e30b44d88cf` 后，明确解封本题 history/refs.json 及其唯一目标。只读该 refs 和 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_1/records/iterative__dvc-4185.json`（下称 H）。未沿 H 引用打开旧阶段日志、raw hints、prescan、其他题或旧聚合。封存初稿及 public_read 未回写。

P/V/E/B 路径约定沿 analysis_before_history.md；G=`E/tasks/iterative__dvc-4185/gold/eval_logs/evallog_replay-er19-dv1-iterativ_24d09737.eval.log`；N=同题 noop 的 `evallog_replay-er19-dv1-iterativ_92136cb3.eval.log`。日志行号均按物理换行，用 nl/sed 定位，不用 Python splitlines 拆进度回车。

| H 主张 | 判断 | 新原件及理由 |
| --- | --- | --- |
| 真值过滤使假值参数一直 new；empty 七 F2P 失败 | 确认当前机制 | param.py:L43-L77；N:L924-L1184 七项实际断言得到 new；G:L2007-L2013 七项通过。空文本 YAML 项解析为 null，H 所称“空串”不能当带引号空字符串覆盖。 |
| ID 反斜杠不一致使 gold 参考缺席 | 机制确认；当前阻塞过时 | 本题 reference audit 修正前确实缺单反斜杠 P2P；G:L1980 对应完整转义 node PASSED。reference-bindings-v1 显式绑定同一 node，当前两 ledger 的 reference_missing_count=0、P2P=22/22；不需要未经校准的全局 unescape。H 的“题目和 gold 都没问题”不能由 parser 问题推得，I1 仍成立。 |
| 安装失败被吞、networkx/Python 3.9 导致相关 run 测试失败 | 对 09-19 条件已过时；旧期精确失败数未重核 | 新 recipe 安装 networkx=2.3+rh2.1，再离线 editable all/tests，保留 RC；N:L903/G:L920 安装为 0，G:L1986-L1988 三个参数 run 测试都 PASSED，全体 49 passed/2 skipped。原参考仍只有 22 P2P，执行成功并没有自动把这些恢复的测试加进参考集。H 的升到 2.5/降 Python 建议不是本次已验路线。 |
| 两个题面目标、gold 只修第二个 | 确认并强化 | 新初稿已在读 H 前独立定位 commit→Stage.changed_entries→继承 BaseOutput.changed_checksum 的 None 与文件 MD5 比较。原题目标没有“只修第二个”的依据；不能直接裁题来迎合 gold。优先做 base/gold 公共最小例，尚未执行。 |
| 无条件 values.get 写 None 会让 new 永远不出现；当前文件缺键应报 new | 部分合理疑点；具体语义推翻 | param.py:L65-L68 先检查当前文件：缺当前键是 deleted；new 是当前键存在但记录中无键。若保留 `if not values:return`，空/None 的 lock 输入还会保留未记录状态，所以“永久压掉 new”过强。正确反例：跟踪 p，非空 lock 映射只有别的键，当前文件有 `p: null`；无条件 get 会伪造已记录 None，返回干净，预期 new。当前 p=1 则会把 new 错判 modified。这是静态候选，未执行/未证 RH2 满分。 |
| test_save_info_missing_param 可保护 fill_values 的 None 行为 | 推翻覆盖推论 | 该 P2P 直接调用 save_info，未调用 fill_values，不能保护“lock 缺键但当前有键”。公开 test_fill_from_lock_params 的缺 foobar 断言相关，但不在本次执行两文件或参考中。 |
| F2P 不锁内部实现，合法替代解 pass | 局部观察确认，广泛 pass 降为 unknown | 断言没有强制 gold 补丁形状；哨兵/投影路线合理。没有执行替代解，不能证明所有符合公开语义的完整解被接受。check 24 unknown。 |
| 题面完整，因此真实消息通过；同包唯一版本/文件可判关系通过 | 未核实或证据不足 | 静态题面可读不等于真实 solver rendered messages，check 3 unknown。未读本包其他题，不以版本/文件唯一性证明无派生关系。 |
| raw hints 含代码；当前答案泄漏 | H 的旧 raw 描述未核实；当前 actor 资产未知 | 当前 P/public_bundle 的 public_hints 是操作说明，未见 H 引述的原 raw hints；未获准打开 raw 原件。正式 actor 镜像文件、refs、祖先历史、预装资产未验，check 29 unknown，不能从导出干净推为无泄漏。 |
| 远端要求妨碍本题；test.patch 无外部资产可填环境不适用 | 分层限定 | 核心七 F2P 为本地参数文件；已验 grader 中远端扩展测试有 gs/hdfs 两 skip，均非计分参考。fixture 导入依赖仍存在，真实 actor 的依赖/资产不能因此填 pass 或一概 not_applicable。 |

封存后的两项更正/补充来自协调者新原件核对，不是 H 的质量结论：

1. 初稿将 ledger `mem_peak_mb` 换写成 MiB，缺少单位实现核证。后稿只保留原字段和值：gold `mem_peak_mb=386.82`、noop `mem_peak_mb=482.152`，不换单位、不推导 actor 预算。初稿不回写，以上为明确更正。
2. N:L132-L139 显示 setup.py 已修改；N:L482-L495 的 diff 是 `moto==1.3.14.dev464`→`moto==1.3.14`。本次另核 G:L138、L500-L509，同样含该预改。故两次历史运行条件是指定 base 加共享 moto 依赖预改、离线配方/networkx backport；gold 侧另有 gold 补丁。不能称 pristine base。未来 CPU 的 base/gold 对照须把同一预改固定在两边并记录初态差异；这不修改本题 gold 内容，也不把环境预改归到 solver 修复。

本次没有改变初稿的静态主结论：needs_review/static_review；I1 commit 漏修仍为强静态推断，I2 恒空状态候选仍为未执行漏测疑点。新增的是旧“缺当前键应 new”的纠正、当前 recipe/binding 的适用边界及两项元数据补充。唯一优先下一步仍是原题两个症状的 base/gold 公开小例对照；不执行旧报告提出的全量扫描、联网升级或裁题。无新模型/CPU 实验成本观测，不继承 H 的 minutes=30。
