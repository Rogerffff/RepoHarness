# A 线状态（当前阅读入口）

更新：2026-09-28 / Codex：`a31cdcd0` 的 AR1 / AR2 / O1 聚焦复核通过，无新增阻塞项。[修后报告与证据](batch6_efficiency_20260921/review_a_remainder_fix_20260928/README.md)。

前轮问题与反例保留在[四提交复核报告](batch6_efficiency_20260921/review_a_remainder_20260928/README.md)；当前状态以下表为准。

本页汇总 A 线（链路正确性与运行效率）的**当前**状态，供 agent 读取和直接编辑。事实来源仍是 [infra.md](infra.md) 与各批次 Brief；本页不替代它们，冲突时以来源记录为准并回头改本页。给用户看的同内容页面是 [a_line_status.html](a_line_status.html)。

## 0. 编辑约定

- **状态词**只用这几个：`reviewed`（已实施、本机验证、经 Codex 复核）、`done`（已实施、本机验证、未复核）、`todo`（可以开始）、`blocked`（写明卡在什么上）、`not_started`（依赖前序阶段）。GPU 相关的一律没有验证过。
- **改动方式**：按条目 ID 原位改状态、证据与"更新"日期；关闭的条目保留原行，状态改为 `reviewed` 或 `done` 并补证据链接。新条目沿用对应前缀续编号。
- **同步 HTML**：改完本页后同步 [a_line_status.html](a_line_status.html)；来不及同步时，在 HTML 顶部说明以本页为准。
- 不写本机绝对路径、机器地址或凭据；建议、已决定、已实施、已验证分开写。

## 1. 一句话状态

主要链路已实施；同名中转误删（A-N4）与供应取消收尾、最终事实落盘（A-N5）已修并通过独立复核。可继续已授权的包供应正式接线（A-B1）；它仍默认关闭。目标机 census 对账、代表题与 GPU 验收仍未做。本轮无新决策，不需要为修复复核租机。

## 2. 需要用户决定或知道的

| ID | 事项 | 为什么需要 | 建议 | 阻塞什么 |
| --- | --- | --- | --- | --- |
| U1 | 八卡试运行的方案与时间：训练条件数值、I18（MoE 路由来源）的处理 | I18 是训练语义决定，一直未定；GPU 验收要在真实作业里做 | 可以先按"试运行里写明路由假设、产物用途"起步，正式语义另议（第三组与第六组 §8.3 的既有口径） | A-G1、A-G2 |
| U2 | B 下次租 x86 CPU 机时，给 A 借用约 1–2 小时 | E2a 需要在真实 x86 镜像上对账 | 与 B 共用一台，不单独租 | A-C1 |
| U3 | 受控依赖供应（1A+2A）何时启用 | 政策已批；启用是单独一步 | 现在不用决定，等 A-B1、A-C2 完成后再提 | 正式启用 |

## 3. 阶段

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| 决策与设计 | `reviewed` | 第 1–6 组已定（[分组决策入口](decision_batches_20260908.md)）；只剩 I18 路由来源未定 |
| 本地实现与 CPU 验证 | `todo`（正式供应接线） | 已交付切片及 AR1/AR2/O1 修复均已复核；A-B1 供应正式接线仍未做 |
| 真机 CPU 验证 | 部分完成（当前位置） | 基座探针链路已在真机验过；E2a 对账（A-C1）、依赖供应代表题（A-C2）未做 |
| 八卡试运行与 GPU 验收 | `not_started` | 等 U1 与机器 |
| 正式训练 | `not_started` | 与 B 的题池、资格共同决定 |

## 4. 已实施分项与复核状态

| 主题 | 内容 | 状态 | 证据 |
| --- | --- | --- | --- |
| 基座探针链路问题 | A 负责的 #1–#6、#8–#10 都已处理；#4 的结论是维持 I01 B，发生率随下一轮真实流量观测；#7、#11 属 B | `reviewed` | [交接包 §13](base_model_probe_20260922_aline_handoff.md)；infra.md 09-23 至 09-25 条目 |
| 第六组 E1 初始化去重 | 同容器消除重复初始化 | `reviewed` | [第六组入口 §9–§10](batch6_efficiency_20260921/README.md) |
| 第六组 E3 路由记录紧凑化 | 无损紧凑表示 | `reviewed` | 同上 §7 与 E3 实施复核 |
| 第六组 E5 两档配置 | 诊断 / 效率配置的无 GPU 部分、评分摘要运输 | `reviewed` | 同上 §10–§11 |
| 第六组 E2b 可信执行前缀 | rollout 与正式评分中候选执行后的 root 操作使用可信前缀；保留 Brief 明列的前置 setup / legacy 例外，不扩大安全承诺 | `reviewed` | [本轮报告 §2](batch6_efficiency_20260921/review_a_remainder_20260928/README.md)；E2/E4 Brief §6–§7 |
| 第六组 E4a + CR1 | 离线历史裁剪与日志保留通过；供应模式未完成资源保留 owner，完成后可正常裁剪 | `reviewed`（本机） | [修后报告 §3](batch6_efficiency_20260921/review_a_remainder_fix_20260928/README.md)；E2/E4 Brief §10–§11 |
| 第六组 E2a | 批量摘要、整批回退和特殊路径本机差分通过；真实 x86 镜像与持久基线对账仍在 A-C1 | `reviewed`（本机） | [本轮报告 §2、§6](batch6_efficiency_20260921/review_a_remainder_20260928/README.md)；E2/E4 Brief §9 |
| 评分安全修补 | G1 /tmp 与 HOME 可执行 `83760b15`；控制字符文件名不停批 `9c59a1f6` | `reviewed` | infra.md 09-25 条目 |
| 受控依赖供应组件 | 正常两段评分与 AR1/AR2/O1 修复已通过；失败保留资源句柄并报告未完成，最终诊断可回读。正式接线未完成，默认关闭 | `reviewed`（组件） | [修后报告](batch6_efficiency_20260921/review_a_remainder_fix_20260928/README.md)；网络供应 Brief §16 |
| 评测、恢复与报告 | 训练中评测、独立 checkpoint 评测、冷恢复、run 报告的本地部分 | `reviewed` | [八卡核验清单](batch5_launch_eval_20260919/gpu_verification_checklist_20260920.md) 列出剩余真机项 |

## 5. 剩余工作

前缀：N = 不需要机器；B = 等 B 交付；C = 需要 x86 CPU 机；G = 需要八卡 GPU。

| ID | 事项 | 状态 | 前提 / 阻塞 | 负责 | 验收要点 | 入口 |
| --- | --- | --- | --- | --- | --- | --- |
| A-N1 | 四个提交的独立复核 | `reviewed`（修后已收口） | 无 | Codex A | 前轮 127 项检查与独立反例发现 AR1/AR2；修后 A-N4/A-N5 通过，正式供应接线仍单列 | [本轮报告](batch6_efficiency_20260921/review_a_remainder_20260928/README.md) |
| A-N2 | 向 B 转达四项交接 | `todo` | 需经用户或 B 任务送达（写留言板不等于已送达） | A / 用户 | ①重放 driver 的 `DockerExecWorkspace` 可复用 `grading.manager.TRUSTED_ROOT_EXEC_PREFIX`；②`prepared_task_face.py` 新增两段脚本与 spec 两个字段，B 接 `supply_policy` 时在此基础上改；③反斜线文件名现可正常导出；④启用两段执行后环境资格要重取 | infra.md 09-25 晚条目"对 B 的影响" |
| A-N3 | 可选收尾：E4b 队列事件按轨迹索引、E4c audits 内存先测量、第七组维护清理 | `todo` | 不阻塞首训 | A | E4b 只加索引与累计数、不删事件；E4c 先测后决定 | E2/E4 Brief §2.4；[分组决策入口](decision_batches_20260908.md) 第 7 组 |
| A-N4 | AR1：同名中转启动失败不得删除已有活容器 | `reviewed` | 已闭合 | Claude A 实施，Codex 复核 | 两入口真实 Docker 撞名保留已有 relay；本次 Created/readiness 取消仍回收 | `a31cdcd0`；[修后报告 §2](batch6_efficiency_20260921/review_a_remainder_fix_20260928/README.md) |
| A-N5 | AR2/O1：供应取消收尾与最终事实落盘 | `reviewed`（组件） | 已闭合；正式消费属 A-B1 | Claude A 实施，Codex 复核 | 三个取消位置与正控闭合；持续拆网失败报告 open，恢复后 close 清零；最终 sidecar 状态正确 | `a31cdcd0`；[修后报告 §3–§4](batch6_efficiency_20260921/review_a_remainder_fix_20260928/README.md) |
| A-B1 | 依赖供应接线：bringup 起停网关与供应中转（网关与 manager 同一事件循环）、run evidence 的政策字段、rollout 注入 `PIP_INDEX_URL` 等、安装后以候选 UID 观测 `pip list` | `blocked` | B 交付：评分面 `supply_policy`（1A 字段）、逐题封禁表 / 例外表、派生镜像 pip / uv 可用性、代表题 | A（B 写字段、A 审） | 默认仍关闭；消费 supply_open、核整段关停预算；启用路径有端到端用例 | 网络 Brief §6、§13.5 |
| A-B2 | B 探针入口接入 A 的生产修复 | `blocked` | B 任务二负责；A 按需支持 | B（A 支持） | 不直接复跑旧探针脚本 | [环境总入口 §4](environment_pipeline.md) |
| A-C1 | E2a 目标机对账：最大真实镜像（SWE-Gym pandas、R2E numpy）上新旧 census 对账，并与已落盘基线清单摘要比对；记空闲 / 4 路并发的 exec 次数与耗时 | `blocked` | x86 CPU 机（U2） | A | 新旧 stdout 逐字节相同（只允许转义前缀差别）；与已落盘清单摘要一致；记录耗时 | E2/E4 Brief §9"未做" |
| A-C2 | 依赖供应代表题冷 / 热安装验证 | `blocked` | A-B1 与 x86 CPU 机 | A | 缓存冷 / 热各一次；agent 与 grader 两种用户安装成功；封禁项目 404；测试段无网络；超时 / 取消后网络、中转、容器都清理 | 网络 Brief §5 |
| A-G1 | 八卡 GPU 验收清单：训练中评测 E1–E11、独立评测 A1–A6、冷恢复 R1–R4、效率档 F1–F8，及完整八卡项（CP>1、多引擎、终止广播、预算拒绝下的 Claude Code 行为等） | `not_started` | U1 与八卡机器 | A（与 B 合并作业） | 按清单逐项回写"核验记录"列；不通过项回 A 线修 | [八卡核验清单](batch5_launch_eval_20260919/gpu_verification_checklist_20260920.md) |
| A-G2 | E1+ 目标存储模式下的初始化耗时；I27 / I28 / I30 按瓶颈实测 | `not_started` | 同 A-G1 | A | 不用 CPU 机数字外推 | [第六组入口](batch6_efficiency_20260921/README.md) |

## 6. 机器需求（A 线视角）

| 机器 | 用途 | 时机 | 规格 |
| --- | --- | --- | --- |
| x86 CPU 机（与 B 共用） | A-C1；之后 A-C2 | B 下次租 CPU 机时 | x86_64、Docker、约 16 vCPU、盘 ≥200 GB；能拉 SWE-Gym 镜像、按 B 的配方重建 R2E 派生镜像 |
| 八卡 GPU 机 | A-G1、A-G2 | U1 定了以后 | 按作业方案；不为 A 单独提前租 |

新机器需重新准备 Claude Code 安装包、镜像与派生镜像；按既有版本和配方重建。本轮未访问公共下载源，实际可用性在机器准备时核对。

## 7. 风险与注意

- AR1、AR2/O1 已在 `a31cdcd0` 修复并通过聚焦复核。供应仍默认关闭，A-B1 须消费 `supply_open` 并核整段关停预算：现有上限约束单条清理，不是整个 manager 的总关停时限。AR2/O1 不影响 B 的默认离线环境处理。
- 受控依赖供应默认关闭；启用后评分改为两段执行，单 shell 下取得的环境资格不能直接沿用（`grading_scripts_digest(two_stage=True)` 不同）。
- Spheron 实例只能销毁、不能暂停；控制台里还在的实例仍在计费。任务二 CPU 机 09-25 傍晚 SSH 报主机密钥已变，当时未登录。
- B 在评估第三个来源 MiMo-V2.6-RL-oss（[来源评估](mimo_rl_oss_20260926/README.md)），目前是建议。若采用，它按测试退出码评分，没有 F2P/P2P 清单，需要 A 新做评分接入并判断是否涉及公共契约。

## 8. 最近提交索引

| 提交 | 日期 | 内容 | 复核 |
| --- | --- | --- | --- |
| `a31cdcd0` | 09-28 | AR1 同名归属、AR2 取消收尾、O1 最终诊断 | [聚焦复核通过](batch6_efficiency_20260921/review_a_remainder_fix_20260928/README.md)；组件尚未启用 |
| `23f5586d` | 09-25 | E2a 批量 census；反斜线 / 回车文件名停批修复 | 09-28 本机通过；A-C1 待做 |
| `8f31caee` | 09-25 | 评分两段执行与网络策略迁移（默认关闭） | 主顺序通过；AR2/O1 已由 a31cdcd0 修复并复核 |
| `5b00a091` | 09-25 | 评分侧可信执行前缀；E4a 容器历史有界；CR1 | 通过；供应退役修正随 a31cdcd0 复核 |
| `0adac07d` | 09-25 | 网关释放收齐在途请求；中转启动取消回收（NG1 / NG2 / PC1） | 原反例通过；AR1/AR2 已由 a31cdcd0 修复并复核 |
| `83760b15` | 09-25 | G1：/tmp 与 HOME 可执行 | 用户确认复核通过 |
| `69ea494f` | 09-25 | 包索引网关与供应中转 | 已复核（提出 NG1 / NG2） |

`0adac07d` 之后的三个提交各自跑过全量五目录与两条集成 lane（`0adac07d` 本身也跑过，1847 passed / 1 skipped）：最后一次五目录 1902 passed / 1 skipped（本机缺 SWE-Gym 解析语料），lane A 530p/346s、lane B 876p。

09-28 Codex 首次复核独立复跑 127 项聚焦检查（含本机 Docker），全部通过；另有两项独立取消/重复启动反例成立，详见本轮报告。未复跑作者的全库、双 lane 或 GPU，不能把前述历史总数算成本轮验证。

`a31cdcd0`（Claude，09-28）：五目录 1920 passed / 1 skipped（Docker 在线），lane A 530p/346s、B 876p；新增 / 改动 42 例，修前 / 修后反证见网络 Brief §15.4。

`a31cdcd0`（Codex 修后复核）：85 项聚焦测试通过、无 skip，ruff 通过；独立 HTTP、Docker、取消与重复 close 对照通过。未重跑全库、双 lane、远端或 GPU。[本轮证据](batch6_efficiency_20260921/review_a_remainder_fix_20260928/README.md)。
