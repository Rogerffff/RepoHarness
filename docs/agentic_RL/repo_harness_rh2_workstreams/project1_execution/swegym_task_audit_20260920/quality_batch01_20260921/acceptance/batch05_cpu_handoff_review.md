# B5 CPU 交接补审

结论：**当前两项具体方案未发现实质设计阻塞。** 各有一个明确的主实验，能够产生所需的有限证据，没有机械增加第二反例，也没有要求整批 CPU 实验全部先于 actor 或模型诊断完成。这是当前快照的交接审查，尚非对最终逐题复审收口的验收。

读取 `expansion/batch05/cpu_queue.json` 的时间为 2026-09-20 23:31:36 与 23:32:36 UTC（本地次日 07:31–07:32）；两次 SHA256 均为 `c5ddb1f7ac0b74d69de3cb88618f05c1a4663ac8f0c214d736f20611c25b9446`。队列为 `concrete_plans_pending_independent_review`，两项均为 `planned_pending_review_and_separate_execution_authorization`。两个 `results/<instance_id>/review.md` 当时均不存在，card 仍注明 reviewer 待复审；本报告未把 pending 当成设计阻塞。根任务在最终收口后核对本快照差异。

| 题目 | 主实验是否回答问题 | 判据与必要边界 |
| --- | --- | --- |
| mypy 11707 | 原四个普通 `.py` 文件的 base/gold × `Y as W`/`X as W` 四格矩阵，逐格只变源码版本或指定导入行，能核实 gold 消除不一致的方向。静态预测为 base 的 Y 拒绝/X 接受，gold 两者拒绝；仍须由输出确认。 | 原命令为 `--strict --no-implicit-reexport`，队列未误用题面标题中的参数笔误。矩阵回答普通 `.py` 行为，不直接裁决题面与公开旧文档哪一方应保留，也不能证明所有按题面实现的解都会因 `.pyi` 隐藏验收得零。冻结两项 stub 评分只是可选独立控制；不需新增反例才能开始该实验。 |
| Moto 5406 | 同一精确 base 上的 noop、gold、只改 `_generate_arn` 地区常量为 East2 的候选，分别跑原 27 项及已有公开 East1 节点，能区分正确地区传递与常量替换。 | 仅在错误候选原评分 reward=1 且公开 East1 ARN 失败时，才形成实测误收反例。公开 `test_create_table_standard` 的完整旧测试体保留；关键断言位于 `test_dynamodb_create_table.py:43–45`。base/gold 是对照，不等于要求另造两个反例；无需扩到第三地区、stream、CFN 全矩阵。 |

入口与原件的有界核验通过：两题归档成员哈希、CLI 参数、gold/grading 路径可定位；mypy build plan 条目哈希和 Moto 原 worker 两条 job 的选择及哈希相符。归档 CLI 支持队列列出的 `noop`、`patch:<file>`、`gold-dir:<dir>`；执行时选其中一项并替换占位路径，不把整段选择说明传成一个候选。未运行任何项目入口。

- mypy 使用 `install_wave1` 派生镜像及其明确 ID，归档 baseline CLI 直达，只有离线 wheel 增层；没有 recipe/bindings/materials，也没有 `revised_install`。两侧共同保留 `test-requirements.txt` 的 `types-typing-extensions==3.7.3` 未提交预改。原日志 `git show` 中的 typeshed 差分是 base 提交展示，不是另一项共享预改。
- Moto 使用原 `baseline01`、原 make init/spec；历史 `campaign.py -> worker.py -> ReplayGrader.replay_one` 与未来单题 CLI 已分清。两条原 ledger 的 `image_id_actual` 都为 null；期望 manifest digest 不能代填实际 ID，未来核身份时另记新观测，不追加 `install_wave1` 或 derived-image 参数。noop 原 `git status` clean 且显式 `git diff` 为空，ThreadedMotoServer 差分来自 `git show`。
- Moto 官方 patch 对原测试名称的调整不抹掉旧测试体的有限回归意义；不能把 26 P2P 一概说成没有保护。缺口是它们未提供这个 East1 ARN 对照，队列因此引用另一个现成公开节点，仍保持原评分版本。

实施提醒均属未来准备：mypy 四例使用独立 case/cache/config 状态并核 `/testbed` 实际候选导入，保留任务 Python 3.9/源码条件与报告者 Python 3.10/mypy 0.910 的区别；Moto 公开节点在同镜像、安装、身份和源码的独立诊断副本中运行，不依赖已被 grader 清理的容器。目标镜像、归档 Python runtime、重定位 prepared/private 输入、候选 diff/SHA 及 mypy 缺失的原 wheel/context 载荷仍待准备，构建审计不等于可执行输入。

没有新增实质必修项。正式 actor 的消息、依赖、导入、权限和可见资产另验，固定 grader 语义诊断无需等待全面 actor 验收。所有新实验仍未执行；本次只读必要 card/原件与元数据，只新增本报告。未完边界仅为尚不存在的两份最终 review 及其可能带来的后续队列变化。

根最终收口补核（2026-09-21T07:41:58.882011+08:00）：已读两份最终review，回读最终两项问题、变体、诊断步骤、判据、原环境与公开节点；最终队列SHA256为`d5075da9befce58330d4a6c78054b6bebad340f276a4e562dd986a3df6d82fae`，已与协调者18份输出摘要核验一致。最终仍为四文件base/gold×Y/X和Moto三候选×原评分/公开East1，没有增加主实验；独立review的状态/范围修订已进入record。根另直接核East1公共测试12–50行。mypy采用显式PYTHONPATH/python -m入口属于未来诊断选择，不是题面逐字命令；其成功不能单独证明editable安装被消费。未发现需要退回的交接问题，所有实验继续未执行。
