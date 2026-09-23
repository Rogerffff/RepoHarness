# getmoto__moto-6114：旧发现差量

2026-09-21，协调者核初稿 SHA256 b26bfa9cf9bae02b53b7fa6a376335aba7ac5f86f93d39e51c027352dd693426 后显式解封。实际仅新增读取 [history refs](${REPO_ROOT}/runs/swegym_quality_batch04_20260921_v1/history/getmoto__moto-6114/refs.json) 和 [本题旧记录](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_moto_2/records/getmoto__moto-6114.json)。没有跟随旧记录中的 repo_level、master、stage1 原件或其他题引用。

初稿和 public_read.md 不回写。下表的“推翻”区分事实错误与证据不足：未复核旧环境失败是否曾真实发生；只判断其是否适用于本轮引用条件。

| 旧主张及位置 | 处置 | 本轮决定性证据与影响 |
| --- | --- | --- |
| 材料对应；base 的字典查询不能识别 ARN（旧记录:23–24） | **确认** | [base 源码](${REPO_ROOT}/runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114/base/moto/rds/models.py:1951)；[noop 原日志](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/getmoto__moto-6114/noop/eval_logs/evallog_replay-er19-iw1-getmoto__793414a1.eval.log:533) 先通过名称查询，再于 :654 报完整 ARN 的 DBClusterNotFoundFault。比只见 RESOLVED_NO 更明确地定位初态。 |
| 检查 3 pass，题面内容完整即足够（:25） | **推翻 pass 的证据充分性** | [环境说明](${REPO_ROOT}/runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114/environment_brief.md:3) 明确仅静态渲染；尚无真实 solver 消息。检查 3 改 unknown。题面另有创建 test-cluster-1、失败例写 test-cluster-0 的笔误，核心目标仍可判读。 |
| public_view 限“只改 moto/”；检查 29 因 hints 只有致谢而 pass（:15、38） | **当前输入不同；旧资产结论未核实** | [当前 bundle](${REPO_ROOT}/runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114/public_bundle.json:1) 的 public_hints 含 NON-TEST 源码、禁改测试、conda 声明等操作指令，非“只在 moto/”的同义限制。实际消息适用性、镜像可见资产和答案暴露未知；检查 29 unknown。未重新访问旧 hints 原件，不能断言其历史内容虚假。 |
| 同文件改动被列为检查 5 issue，但文字又称非派生（:27） | **不沿用** | 同文件本身不足以判关联质量问题；本轮没有读他题材料或核具体派生关系，保留未查。 |
| 离线 make init rc=2，安装配方不匹配（:28、44） | **对本轮评分条件已过时** | [gold 原日志](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/getmoto__moto-6114/gold/eval_logs/evallog_replay-er19-iw1-getmoto__356bbc61.eval.log:368) 的 make init 两次 editable 构建成功，:527–529 安装 rc=0；[noop 原日志](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/getmoto__moto-6114/noop/eval_logs/evallog_replay-er19-iw1-getmoto__793414a1.eval.log:496) 同样成功。适用 install-wave1 离线 wheels 派生镜像；不推出正式 actor 已消费此配方。 |
| 依赖/网络检查 9、11 pass，资产 7 not_applicable（:29–30、39） | **静态需要可确认；运行结论未核实** | [mock 入口](${REPO_ROOT}/runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114/base/moto/core/models.py:408) 默认进程内，但共享 TEST_SERVER_MODE 分支实际存在；[Makefile](${REPO_ROOT}/runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114/base/Makefile:17) 安装需要工具链/依赖。默认业务无真实 AWS 服务需求不等于 actor 资产已经核验。 |
| 官方只恢复一个纯测试文件；参考 ID 不涉及参数化（:31–32） | **确认至已读范围** | [test.patch](${REPO_ROOT}/runs/swegym_quality_batch04_20260921_v1/private/getmoto__moto-6114/test.patch:1)；[gold 恢复日志](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/getmoto__moto-6114/gold/eval_logs/evallog_replay-er19-iw1-getmoto__356bbc61.eval.log:191)。35 个参考 ID 与原日志逐项对齐且无缺席；不据此扩大成一般 parser/投影安全验收。 |
| F2P 与题面场景一致（:33） | **确认方向，补足限制** | [test.patch](${REPO_ROOT}/runs/swegym_quality_batch04_20260921_v1/private/getmoto__moto-6114/test.patch:23) 的 ARN 调用直接覆盖目标入口，但仅核长度，不核匹配身份。原来的“与场景一致”不能证明语义覆盖完整。 |
| 检查 24 pass，多种解析路线能过（:34） | **合理路线确认，pass 降为 unknown** | 完整 db_cluster_arn 比较、合理解析后按名称查询均不受隐藏实现形状约束；尚未运行替代解，更未证明所有合法解被接受。 |
| 缺不存在 ARN、错账户/区域/类型负例，gold 粗解被放过（:35、42、48） | **不存在 ARN 覆盖缺口确认；其余规范主张未核实** | 35 个测试完整阅读，没有不存在 ARN describe；gold 的无条件 split 可静态推出任意前缀同末段命中。但本题公开材料不足以规定那些前缀的 AWS 拒绝规则，不能把缺相应测试或 gold 行为本身定为确定错误。本轮优先用无需该规范的目标身份反例。 |
| delete/start/modify 同族接口未加 ARN，算 gold 范围偏窄/回归（:19、36、49） | **推翻作为本题未完成或回归的依据** | [公开题面](${REPO_ROOT}/runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114/user_prompt.txt:3) 只指定 describe_db_clusters；同族旧缺失不是本补丁引入的回归。不得因此强加额外实现。真正受修改方法影响的 Neptune 回退路径缺少本题评分保护，仍保留。 |
| gold 用 split；未来 master 改过滤框架可旁证粗糙（:37、43） | **代码描述确认；规范评价不沿用** | [gold.patch](${REPO_ROOT}/runs/swegym_quality_batch04_20260921_v1/private/getmoto__moto-6114/gold.patch:8) 与已读 base 足以判断正常域；[gold 原日志](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/getmoto__moto-6114/gold/eval_logs/evallog_replay-er19-iw1-getmoto__356bbc61.eval.log:539) 证明 35P。未来 master 未读取，也不能作为此 base 的额外公开规格。 |
| Neptune 侧应做窄回归（:51） | **确认建议，尚未执行** | [受影响分支](${REPO_ROOT}/runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114/base/moto/rds/models.py:1955) 与 [公开 Neptune 测试](${REPO_ROOT}/runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114/base/tests/test_neptune/test_clusters.py:60) 可定位；这批真实评分只跑 RDS cluster 文件。 |
| ready_for_probe；costs.minutes=15（:53–54） | **不沿用本轮状态或成本** | 真实 actor、消息及资产待验，目标身份漏测尚待实验；本轮按模板 needs_review/static_review，development_diagnostic。旧 15 分钟不是本轮观测，成本字段 null。 |

**相对旧记录的新发现**：ARN 输入返回第一个集群也能满足新增 length=1，而本例请求第二个。它直接违反目标身份要求，不依赖错账户/区域 ARN 的外部解释。当前证据是静态可逃逸候选，未执行，不能写成已证实 reward=1。另明确区分正式 rollout 的 public image 与历史 replay 的 derived image；评分成功不填 actor pass。

**相对封存初稿的改变**：没有改变核心判断或唯一优先下一步；补了旧结论的证据等级和过时范围。初稿表格中 S/models.py、S/test_rds_clusters.py、S/exceptions.py 是上下文简写；对应完整路径分别为 runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114/base/moto/rds/models.py、runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114/base/tests/test_rds/test_rds_clusters.py、runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114/base/moto/rds/exceptions.py。本次后稿均使用完整路径，不更改封存稿。

唯一优先下一步仍是目标身份 CPU 对照：以 gold 为正对照、Q1 错误候选为负对照，跑原 35 项 RH2 评分，并单独核返回 Identifier/ARN 等于请求目标；无新运行、无修订原题或测试。
