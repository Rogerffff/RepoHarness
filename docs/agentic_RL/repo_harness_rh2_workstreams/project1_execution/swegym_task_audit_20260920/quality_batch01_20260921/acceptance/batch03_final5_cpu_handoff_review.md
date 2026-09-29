# B3 最后五题 CPU 交接补审

结论：**未发现阻塞静态方案验收的设计问题**。五条队列各有可区分的假设、最小变体及判据，入口与本题历史条件一致。可按协调者选择交接少量 CPU 诊断；不表示镜像、构建环境或候选补丁已准备好，更不表示任何新实验已运行。

读取时间为 2026-09-20 22:15:35–22:18:21 UTC（本地次日 06:15–06:18）。最终队列为 `static_review_complete`，五项均为 `reviewed_static_plan_not_executed`；首次与末次快照中五条完整队列项及五份最终 `review.md` 哈希均未变化，无需等待 pending 收口。队列文件 SHA256：`f6efd80df62b3c30c32d553e90576817dcf1932387ab91fe934a9718f4bbaf6e`。

本次只检查 `expansion/batch03/cpu_queue.json` 中 Moto 6185/6408/5960、Pandas 50319/51605，结合对应最终 review/card、准确来源及入口。未重审整题或其他已验包；未运行项目、安装、测试、容器、网络或模型。

| 队列 | 最小变体与判据 | 交接判断 |
| --- | --- | --- |
| Moto 6185 | base/gold 对合法主键名 `M`、嵌套 `S=None` 的同一 SDK Put/Get 行为；保存完整返回与异常，同时保留原冻结评分。 | 不需要第三补丁。若 base/gold 均拒绝，支持 gold 覆盖不足；这仍是待运行预测。正常 SDK 校验、mock、凭据及区域条件已明确。 |
| Moto 6408 | base/gold，仅切换目的 manifest 已存在/新建；核对移动标签及独立标签的完整归属、读取结果与 failures。 | 变体有区分力。新建目的地路径预计 base/gold 均有问题，应记为既存邻近缺陷，不能称为 gold 新增回归；非代表标签扩展并非必做。 |
| Moto 5960 | base/gold/一个在 gold 复制基础上只省略 GSI KEYS_ONLY 投影的部分实现；冻结评分与公开 INCLUDE、KEYS_ONLY 的完整 items/count 分开记录。 | 第三补丁是验证误奖所需的最小对照。只有候选得原满分且公开 KEYS_ONLY 行为失败，才构成运行态误奖证据。保留存储完整性对照，无需再加去掉 deepcopy 的补丁。 |
| Pandas 50319 | base/gold/局部 `_fill_token` 的 `ValueError -> None` 通用回退；保留既有成功格式与类型校验，核对公开允许结果和唯一新增断言。 | 第三补丁用于区分合法替代实现与 gold 唯一路径，必要且可构造。旧行为通过、公开要求成立而新增 F2P 单独拒绝时，才能确认误拒；不能以全局返回 None 冒充。 |
| Pandas 51605 | base/gold，分别使用 `[]`、新建空 iterator、新建非空 iterator；核对值、dtype、shape 和异常。 | 足以检验 gold 是否把 base 可用的非空 iterator 变成 TypeError，以及空 iterator 是否仍未支持；不必加入固定返回长度等新候选。 |

入口抽查通过：

- Moto 三题均为 `install_wave1` 的归档 baseline CLI，使用各自派生镜像 ID 与 `install-wave1:<instance_id>` 身份；plan、镜像记录、ledger 对应。只有 wheel 增层，没有 `revised_install`，也没有 recipe/materials/bindings wrapper 输入。
- Pandas 50319 是原 `reference_v1/replay_with_install_recipe.py --bindings` 路由，输入为原 `reference_bindings_v1.json` 的完整 `version/decision/tasks` 结构，按 `tasks["pandas-dev__pandas-50319"]` 取一条 binding。所选条目规范化 SHA256 与队列一致；逐次输出的单题 audit JSON 不能替代原输入。无安装配方、materials 或派生镜像覆盖。
- Pandas 51605 是 `baseline01` 原镜像/default driver 条件。历史进程入口为 `campaign.py -> worker.py -> ReplayGrader.replay_one`；队列明确将归档 CLI 标为未来单题入口，没有冒充历史 launcher，也未套用 `install_wave1` 或 binding。

以下是未来执行时的精确构造与准备提醒，**不是要求修改封存稿或增加必测范围**：

- 5960 的部分候选须同时区分 GSI 与投影类型，只跳过 GSI KEYS_ONLY，保留 INCLUDE、LSI、deepcopy 及其余行为；保存真实 diff/SHA 后再运行。
- 50319 修改 `.pyx` 后须重新构建并在新进程核对实际加载扩展；旧格式对照按 62 个实际相关节点核验，不能把 58 个解析键当成节点数。唯一既有 binding 保持原版本，不借本实验扩大 parser 修订。
- 51605 每个变体重新创建 iterator；纯 Python 修改是否另需构建应依据兼容扩展与源码导入核验，不自动套用 50319 的完整重建要求。
- 目标镜像可用性、历史归档 runtime、新建以 `rh2` 结尾的 code-root、重定位 prepared/private 输入及独立输出仍待准备；本地缺失的历史 wheel/context payload 不能因 plan 可读便宣称可立即复现。

队列已把固定 grader 身份、源码及依赖核验与正式 actor 开发验收分开。上述语义诊断可以先做，不需要先全面验收 actor，也不要求五项或整批 CPU 全部通过才继续。当前静态缺口属于执行准备，未发现需先修正的命令、对照或判据阻塞。
