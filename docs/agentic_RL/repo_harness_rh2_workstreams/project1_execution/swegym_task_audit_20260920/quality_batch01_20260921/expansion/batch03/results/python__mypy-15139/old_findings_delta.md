# python__mypy-15139 · 历史差分

时间 2026-09-20T21:23:08.119279+00:00。初稿 SHA256 `545d81096288c0b587e14606425cbb3b8f4aabf80a33c65a56a97ac25366c0e1`；父协调者 UTC 2026-09-20 21:21:19.803519 明确放行。只读 `runs/swegym_quality_batch03_20260921_v1/history/python__mypy-15139/refs.json` 指向的唯一旧记录 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_2/records/python__mypy-15139.json`。首次按 private/history 猜路径未找到，随后只定位本题 refs；没有扩读他题或聚合。封存稿未回写。

| 旧主张 | 结论 | 新决定性证据与含义 |
|---|---|---|
| 无运行证据、未实跑安装 | **过时** | 当前引用的09-19 install_wave1原 ledger第1行及 NL/GL 已有双角色安装成功、唯一case真实失败/通过、0/1奖励；不外推actor。 |
| 缺 force-uppercase 选项名意味着公开材料推不出规则 | **推翻这一强断言** | `P/base/mypy/options.py:358-364`、公开 `check-lowercase.test:2-44` 与 runner `testcheck.py:128-129` 足以发现政策；正常查源码不等于隐私信息缺失。题面OR和fullname作用域仍有歧义，保留但降为未证误拒。 |
| gold 没改 reveal，因此不完整 | **确认核心，纠正其输出描述** | gold只改messages，`types.py:3188-3189`仍硬编码 `Type[...]`；旧记录称仍输出 `builtins.type[...]`，与该精确base不符。当前静态预期为 `Type[builtins.type]`，实际原题CLI尚未执行。 |
| 仅加同文件8条Tuple/List/Dict/Set case就能直接堵无条件Type小写 | **推翻** | 八条未进入TypeType分支；旧正文自己也说它们不受影响。历史后追加定向读取 `check-classes.test:3377-3385` 的 `testTypeUsingTypeCTypeAnyMember`：`y: int=arg`要求 `Type[Any]`，才是直接回归证据。不能把reveal-only快照数量等同受影响错误formatter数量。 |
| 无条件改Type分支小写可拿满分且破坏兼容 | **确认静态机制，执行未核实** | 当前F2P只测no-force模式、P2P空；options旧版本/force模式与上述Type[Any]错误是具体旧行为。未构造候选，未复跑RH2，不记作已执行反例。 |
| 可在TypeType.__str__层处理就通过 | **未核实且路线描述不充分** | `messages.py:2519-2520`直接访问typ.item，不调用TypeType.__str__；仅改该层不足以保证赋值错误改变。合理替代是共享显示规则或修改两个真实打印入口。 |
| 新case不需要fixture/无外部依赖 | **限定后确认** | 无新增/自定义fixture及运行期服务；但runner确实使用lib-stub/builtins.pyi、typing存根、pytest及运行依赖。不能简写为不需要fixture/依赖。 |
| -k无过选、参考身份一致 | **确认并增强** | NL:847-878、GL:866-884实选1；原ledger解析键1，F2P1/P2P0，无missing/skipped。不是只凭nodeid四段或旧kscan。 |
| 把mypy/test/*与test-data/*整仓加入保护 | **不采用，尚待独立证据** | baseline归档prepared_task_face.py:305-330明示test_globs空，官方精确恢复只有check-lowercase.test；没有新运行的绕过证据，old gold不改某路径也不能证明所有合法解不需要它。additional_exclusions继续[]。 |
| 同仓messages.py热点/相邻base暗示同族 | **未核实，不据此聚类** | 本轮未读他题精确修复，旧记录也承认函数不同；当前只记录本题身份。 |
| 旧raw hints给出了公开未见的精确规则 | **来源主张未核实** | 只见唯一旧记录转述，没有获准补读原raw hints；当前public_bundle.public_hints是harness操作说明。不得把旧转述当当前模型消息或新公开规格。 |

初判没有改成pass/reject：仍 `needs_review/static_review`，优先做“原题CLI base/gold + 官方单case”的一次配对验证，确认gold是否仍混用Type/type。历史促成的是更窄的回归建议与旧断言纠错，没有回写初稿，也没有按旧needs_repair标签给当前版定性。
