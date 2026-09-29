# iterative__dvc-3576：旧发现对照

2026-09-21。协调者在核对并登记历史前稿 SHA 后明确开放本题 history refs。本阶段只读其指向的本题旧记录及本题原件，不回写 `analysis_before_history.md`。封存摘要仍为 `16e22c073636a729b4ea9f8adec6149724344842f588fcba53e13d76bc3e1bbd`。

证据根沿封存稿的 ROOT、P、B、V、R、G、N 定义。旧记录 H 为 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_1/records/iterative__dvc-3576.json`，SHA-256 `883b71f64bffe5ba0e0a21248f7163e4b70cc15f601a1d6c87618dcb3b233538`。H 中的“旧实验建议”没有运行工件引用，不能记成已经实施的反例。

## 按精确引用补查的历史原件

H 指定的 stage1 路径均实际存在，没有用新实验代替历史原件检索。共同前缀 `S=runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/iterative__dvc-3576`。

| 原件 | SHA-256 | 这次实际读到的决定性证据 |
| --- | --- | --- |
| S/gold/offline/a1/test_output.txt（472 行） | `747494847a1b2d006e45d34f2cd5a3c1ab63d5d59da5bf9b97a4547df1b8db7a` | 341–400 安装 PyYAML、Git 依赖、requirements、editable 构建均有错误；414–415 末条命令仍记录 install rc=0；431–466 执行 7 项且全过。 |
| S/empty/offline/a1/test_output.txt（467 行） | `a93c651041841013fb1d72c6beffc15572e0d8e9b01e0e46c9cda63c8f33b218` | 327–386 有同类安装错误；400–401 install rc=0；417–461 运行 7 项，空结果 helper 断言失败，另6项通过。 |
| S/gold/offline/a1/status_map.json | `37282ce11e2eff5b5d51f011f4dc4560cb353fc3e066c2036df8084f53192400` | 全文11行；第2–3行额外含 `"Could": "ERROR:"`、`"No": "ERROR:"`，另7个正确测试ID。 |
| S/empty/offline/a1/status_map.json | `70137308f0ce8d87543b9c1914c02406e997bb6cd9829a5c63ace2c20ebddb1d` | 同样两污染键；F2P FAILED、6个P2P PASSED。 |

另读取 H 明确引用的原始来源中本题一行：`docs/agentic_RL/repo_harness_rh2_workstreams/s2/raw/swe_gym_lite_full_f70b1a29.jsonl:137`，该行含换行的字节 SHA 为 `d167742b5388e4f3edb5ef0bb1b8b55399921b9a2924b187f5dca62bd948ac2c`。只显示本题 `hints_text` 和身份元数据。讨论确有“偏好空输出”“移到 stderr”“考虑 print”等意见，未形成新增的当前公开指令；P/public_bundle.json 的 public_hints 是 harness 操作提示，没有这些讨论。不能用这份私有历史讨论替公开 issue 改规格。

## 旧主张核对

| H 的主张 | 结论 | 决定性新核对与影响 |
| --- | --- | --- |
| 题面要求 stderr，但 gold 仅将空 helper 返回改为 `""`；完整 CLI 流向未测 | 确认核心事实，缩小措辞 | 封存稿§2–4；metrics.py:108–158、logger.py:105–111,164–183；test.patch 只改 helper 断言。gold 没有输出 stderr 状态。空行是源码推断，未新增 CLI 运行。 |
| “评分要求取消消息”，与 stderr 要求绝对互斥 | 推翻过强解释 | F2P 只要求 helper 空返回；候选仍可同时在 caller 输出 stderr 状态，二者并非逻辑互斥。真正问题是测试限制 helper 返回约定，可能拒绝另一种正确命令层路线；以及它放过 gold 的部分交付。 |
| “gold 另外三项一项没做”意味着三个功能都未交付 | 推翻该推论，保留 diff 事实 | gold 确实未改数据层，但 base diff.py:78–100 已有缺侧容错，func:978–989 已期待 old=None。原 KeyError 在本 base 未实证。不能用 gold diff 缺行来判已有行为缺失；仍确定的展示差异是 `diff not supported` 与题面 `-`。 |
| check24 pass，因为不锁内部写法 | 推翻 blanket pass | 保留 helper 旧返回、由 caller 分流的合理路线会静态触发 F2P 失败；“只锁一个返回值”仍可能约束未公开的内部接口。未运行候选，保留静态误拒假设。 |
| “6条P2P全是逐字表格；helper恒空会让6条全挂” | 部分确认、纠正计数与测试内容 | unit test_metrics.py:41–85 有5个非空 formatter 断言；:5–38 的第6个 P2P 是参数解析、Mock调用、退出0，并且走 --show-json，不调用 helper。恒空预计破坏5条，仍有实质保护力。 |
| `test_metrics_diff` 逐字比表格；func `-k diff` 测 stdout；show_json_diff 接近真实 JSON缺old验收 | 推翻覆盖归因 | 前者只核转发且 Mock 掉数据层；func:882–1007 调用 repo.metrics.diff 并比字典，没有 CLI 流捕获；show_json_diff 喂 old=1,new=2,diff=3 给 formatter，是表格展示测试，不是序列化/计算测试。 |
| stage1 “安装正常、环境干净”；check6 pass | 推翻历史事实；新配方另列已改善 | 上表旧日志明确有安装错误，且 root pip 警告。不能凭7 passed宣布安装完整。09-19 G/N 原件已证明修订入口正常退出、七项如预期运行；这不补写旧运行成功，也不证明 actor。 |
| stage1 “status_map无污染键”；check19 pass | 推翻历史事实；当前版本已另核 | 两旧 status_map 第2–3行直接反例。当前09-19 ledger/diagnostics 为7 parsed、outside=0、missing/skip空，逐ID与G/N一致。旧污染不能当当前 parser 未修；新结果也不能替旧摘要洗白。 |
| base空helper旧值、stage1 empty失败、gold7通过 | 确认有限执行范围 | 旧原件实际有7项测试与断言；新G/N又支持同一分差。stage1不是当前受限 actor 工作流，不能混作正式新资格重复验收。 |
| 材料全在、官方恢复仅unit文件、gold不碰测试 | 确认 | S2指定行与当前包逐字段相等；G:188–228、N:174–214明确恢复/apply/存在性；gold投影只含业务文件。 |
| “渲染完整”、check3 pass | 缩小到静态文件 | 当前 user_prompt.txt 能看到完整 issue；未捕获真实模型消息及 public_hints 进入CLI的位置，所以实际输入仍unknown。 |
| 与3620/2141不存在同PR或代码关系 | 未核实，不采用标签 | H 引用跨题 prescan；本次未读跨题报告/其他题原件。单独同version或路径不重合也不能证明无派生关系。 |
| 题面无补丁链接，因此check29 pass | 缩小为题面检查 | 题面确无修复补丁/PR链接；真实 actor Git、缓存、包、挂载可见性未验，不等于无泄漏。 |
| “裁成无差异零输出即可可用”、needs_repair | 不采纳自动修订建议 | 裁题面改变任务范围，且会把 stderr保留和缺侧展示目标去掉；需有依据的独立修订与复核。现有题保留 needs_review/static_review，原件和reward不改。 |

## 对本主审初判的影响

历史没有改变封存稿的核心暂定处置。新增确定事实是：旧“干净安装/无污染键”说法与其原始工件不符；来源私有讨论确有多种输出偏好，但不能作为当前公开要求。封存稿已独立指出 base 的既有容错、5个formatter加1个Mock测试的真实范围及合理命令层替代路线，因此继续保持其区分，不向旧“裁题面即可”收敛。

唯一优先实验仍是封存稿所述 base/gold/命令层替代解同场景 CLI+原参考对照；未执行。须先固定实际 actor配方/导入，再记录输出和原RH2得分。独立reviewer尚未给结果，不能称复核一致。新增阅读暴露仅为 H、两个历史日志/两个status_map和本题raw行；大日志首轮输出被工具截断，随后补看精确错误/安装/测试命中行并重新计算摘要，没有将未展开的重复激活行称全文审读。
