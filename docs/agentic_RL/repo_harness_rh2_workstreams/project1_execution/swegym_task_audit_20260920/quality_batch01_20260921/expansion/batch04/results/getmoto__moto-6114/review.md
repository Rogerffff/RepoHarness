# getmoto__moto-6114 — 独立交叉复审

2026-09-21。**支持主审 `needs_review / static_review`、`development_diagnostic` 的结论。最终建议暂缓进入以原 reward 判断修复正确性的真实模型探针名单，保留为 CPU 判分校准对象。** 原因是核心“返回所请求集群”的身份要求没有被新增断言验证，存在具体错误候选；同时真实 actor 消息、环境与资产未验。不是据 ARN 边界推测拒绝题目，也未证明 gold 在正常输入域有错。

**独立性与封存。** 先独立读取授权公开/私有原件并保存 reviewer_initial.md，协调者核验 SHA-256 `808124f9b8579004f0cc727a79ed209dd5e9cc6d5238d30f730269e75100ef15` 后显式解封。本轮复核该 hash 未变；没有回写初稿。解封后完整读取本题 public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json，以及本题 history/refs.json 唯一指定的 env_overnight_20260916/L1_moto_2/records/getmoto__moto-6114.json。没有跟随旧记录的 repo_level、master、其他题或 stage1 引用。已见 gold、隐藏测试、既有运行结果和旧质量结论，不称 result blind，所有稿件均不应提供给独立 solver。

权威根为 `${REPO_ROOT}`。下文 `P` 为 `runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114`，`V` 为同批 `private/getmoto__moto-6114`，`S=P/base`；`B` 为本 review.md 所在目录；`E` 为 `runs/env_recipe_repair_20260919/install_wave1/tasks/getmoto__moto-6114`。已复核 public_read.md SHA-256 `20b97ef56a9417a75c53ce91023009da45a02abd6e824a9ba21dd20a2de5f912`、主审封存初稿 SHA-256 `b26bfa9cf9bae02b53b7fa6a376335aba7ac5f86f93d39e51c027352dd693426`。本轮只新增本文件。

**对主审关键结论的复核。**

| 主审主张 | 复审判断与决定性证据 |
| --- | --- |
| 题意为 DBClusterIdentifier 接受已有集群 ARN，保留名称路径；不要求通用 Filters 或同族操作扩展 | **支持。** P/user_prompt.txt 的有效复现明确使用 DBClusterIdentifier；S/moto/rds/responses.py:584–588 直传该参数。test-cluster-1 / test-cluster-0 是可据上下文消除的笔误。旧记录把 delete/start/modify 的既有 ARN 缺失列为本题回归，没有依据。 |
| base 故障与题意吻合，材料/参考对应 | **支持至已查范围。** 独立初稿已核 test/gold 内嵌字段、base 标识及原日志 hash。S/moto/rds/models.py:1873–1879 用短 ID 存储、:1951–1958 原样查键；E/noop/eval_logs/evallog_replay-er19-iw1-getmoto__793414a1.eval.log:544–569、654 在真实创建返回 ARN 的调用上报 not-found。它不是仅 parser 给出失败标签。 |
| Q1：新增测试只验 length=1，可能接受错误目标 | **支持，而且是最优先问题。** V/test.patch:9–15 取第二个集群 ARN，:23–25 只验长度。S/moto/rds/models.py:1333 为 OrderedDict，按 :1877 依次存储；只对 arn: 输入返回第一个现有对象，将返回 cluster-id1 而请求是 cluster-id2。S/moto/rds/responses.py:1093–1098 直接序列化返回对象，无后续身份检查。本轮补读 tests/__init__.py 与 helpers.py，未见能替该断言补上目标校验的机制。**静态覆盖缺口已成立；错误候选实际得到 RH2 reward=1 仍待实验。** |
| 合理替代解不必使用 gold 的 split；未见形状误拒 | **支持。** 完整 db_cluster_arn 属性匹配、保留旧短 ID/无参/Neptune 分支的方案不受现有断言排斥。没有特定 helper 名、Mock 形状或顺序约束；但未执行替代解，check 24 保留 unknown，不能因多条路线看似可行而全称 pass。 |
| Q2：Neptune 回退没有本题评分保护 | **支持其有限含义。** S/moto/rds/models.py:1348–1350、1955–1958 明确有当前账户/区域的 Neptune 回退和合并列表；本题真实参考仅为 RDS clusters 单文件。公开 Neptune 测试可用于未来有理由的窄回归；gold 没有删除旧路径，当前不构成“已发现 gold 回归”。 |
| gold 正常域修复可信，但 ARN 前缀边界未知 | **支持。** gold 仅在查表前取冒号末段，正常 ARN/短 ID 路径可得到正确对象；既有 gold 35P 与 noop 1F/34P 已由原日志和 ledger 交叉核对。无条件 split 的行为可静态推导，然而“某跨账号/region/service 或异常前缀输入必须如何处理”缺少本题公开规范，不能据此宣布确定 gold 错误。 |
| 历史离线 make init 失败对当前 install-wave1 评分配方已过时；grader 成功不能代填 actor | **支持。** 已核两份原日志安装 rc=0、gold 35P、noop 在目标 ARN 处失败；派生镜像加离线 wheels，grader 身份为 rh2grader/54322。此次补读 frozen_sources/baseline.tar.gz 中 prepared_task_face.py:336–349 与 replay_grade.py:294–309：正式 rollout 取 public image，replay 可显式取 derived image，确非同一消费事实。gold ledger observations 导入 /testbed/moto/__init__.py 只证明那次评分导入路径。 |
| 恢复一个官方测试文件，普通业务源码可交付 | **支持至本题观测。** V/test.patch 只改纯测试文件；gold 原日志 :191–199 记录恢复后 clean apply；gold ledger projection 只包含 moto/rds/models.py，ignored_paths=[]。保持 additional_exclusions=[] 合理；不外推所有文件、所有候选形状或一般评分安全性。 |
| checks 3/29 unknown；用途仅开发诊断 | **支持。** 静态 user_prompt 不是实际 rendered 消息，静态 base 不含 .git 不是实际 actor 无答案资产的证明；gold/noop grader 成功也不能证明 CLI 工具流程、权限或安装条件。真实模型成功率与成本仍无观测。 |

**需要收紧的表述，不改变核心证据。**

1. B/card.md:13 和 record Q3 的“非标准 ARN”不宜概括不同账号、区域或服务的所有 ARN。那些字符串可能在语法上完全有效，只是本题未规定该 endpoint/backend 应如何解析。建议统一称“本题未约定的 ARN 输入边界”；这项措辞修正不意味着新增拒绝规则，也不要求修改 gold。公开读稿末段的跨账户/区域建议同样只能保留为待规范支持的检查方向，不能升级为现有验收契约。
2. checks[23].status=issue 可以用来登记示例名称笔误，但应明确是**非阻断文本问题**；公开代码块和期望足以确定普通 ARN 成功查询目标。暂缓的主要理由是 Q1 的判分解释风险及 actor 证据缺口，不是题意无法建立。无需为了判原例而先引入新的 AWS 规格。
3. 不存在 ARN 是尚未覆盖的普通负例方向，与“合法但跨账号/区域 ARN 应如何处理”应分开。一个从未创建、末段也不对应任何存储对象的正常形状 ARN，不能支持“返回任意现有集群”；但现有公开材料仍未规定失败消息要保留完整 ARN 还是名称，不应把该文案做成新的精确要求。
4. 主审 card/record 仍写 reviewer pending，是复审前的协调状态。当前本题已完成独立初判和本次交叉审查；我不改写其稿件，由协调者收口。check 24/27/29 等事实未知不因复审完成而自动变 pass。

**对历史差量的判断。** 支持主审撤回旧记录的 ready_for_probe 直接状态，并把旧 check 3/24/29 的 pass 降为相应未证事实；“题面完整”“多种解析能过”“hints 只有致谢”分别不足以证明实际消息、所有合法解接受性、真实 actor 资产无泄漏。支持将旧安装失败限定为旧条件，不复写成该次失败从未发生。支持不沿用“改同一文件”作为跨题派生证据，也不将未来 master 的实现风格作为本 base 的规范。旧记录对 split 缺少账号/区域验证的描述可保留为行为线索，其规范性贬判没有被本地公开材料支持。

**最终有限结论。** 八方面均有证据或明确未查项；没有新发现能推翻主审正常域理解、历史运行定位、合法交付路径或所列合理替代路线。初稿与主审都独立定位了目标身份漏测，交叉后未发生实质反转。这个一致性不代替运行证据。当前保留为**待校准的静态诊断对象**，暂缓当作一般模型探针候选直接统计原 reward 的正确率；无需因未知 ARN 边界判坏题或拒绝 gold，也不批准正式训练/最终评测使用。代码层面无须本轮改题，后续是否补测试应由校准结果和原需求共同决定。

**唯一优先未来 CPU 实验：双集群目标身份与原评分对照。**

执行前由后续负责人核目标派生镜像/离线资产、可达 prepared summary、base 与当前参考 hash；本轮不准备、不下载、不运行。一次实验只比较两种候选：现有 gold，以及“仅对以 arn: 开头的输入，在 RDS 集群非空时返回第一个集群；其他分支维持 base”的错误候选。保持原 test.patch、原评分及 35 个参考 ID 不变。另用独立公开业务脚本在同一个 mock、同一个账户/区域创建 A、B，取 B 的真实 ARN 查询，验证结果 Identifier 和 ARN 是 B；也可对照同一时刻的 describe-by-name 结果。不能拿 Status=creating 的创建响应与后续 available 的查询响应做全对象相等。

| 待观察项 | gold | 错误候选 |
| --- | --- | --- |
| 独立目标身份断言 | 预期通过 | 预期返回 A，断言失败 |
| 原 35 项 RH2 评分 | 已有历史 35P；新运行仍记录实际值 | 静态预计可过，**尚无实际结果** |

若错误候选 reward=1 而目标身份断言失败，即把 Q1 从静态可逃逸候选升级为真实误收；若它未过，检查具体失败/环境原因后修正该假说，不能放宽原测试保住结论。实验只使用普通有效、实际存在的同账户同区域集群 ARN，信息增益直接落在评分是否区分正确对象，不依赖 AWS 边界争论。无须先凑第二类反例；actor 消息/资产条件仍另行保留。

本轮只读授权材料并新增 review.md；无项目 import、pytest、候选补丁、安装、容器、下载、网络、quota/reset、源码/测试/评分修改或提交推送。
