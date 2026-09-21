# 首批12题静态质量审查完成

2026-09-21。固定12题的公开阅读、历史前主审、历史对照、独立初判、交叉复核、短卡和结构化记录已全部完成。共84份必需文件，另有mypy10424配方封存附录；角色、时间、开放顺序和哈希见 [assignments.json](assignments.json)。每题均保持 `needs_review / static_review`，仅用于 `development_diagnostic`。静态审查完成不表示actor或评分质量已通过运行验收。

| 任务 | 收口判断 | 优先后续 |
| --- | --- | --- |
| [Conan15422](results/conan-io__conan-15422/card.md) | 有限jobs字段传递候选；默认、多配置和实际构建覆盖有限 | 真实actor公开开发验收 |
| [Conan14177](results/conan-io__conan-14177/card.md) | 公开verbose开关与默认日志验收不一致；gold未交付该接口 | 公开契约替代解与gold对照 |
| [Dask8597](results/dask__dask-8597/card.md) | 受限候选；两项实际通过旧测试未入P2P，具体条件式错误修复可能漏收 | 指定配置CPU/RH2，再核actor |
| [Dask8801](results/dask__dask-8801/card.md) | 错误措辞约束、原字符串路径漏测；权限测试的执行与参考不同 | 先保持path!r的同义措辞，再测lists-only候选 |
| [Pydantic8511](results/pydantic__pydantic-8511/card.md) | 受限候选；gold对无本地annotations子类的继承有静态疑点 | 固定Python3.8的窄继承对照 |
| [Pydantic5706](results/pydantic__pydantic-5706/card.md) | 成功/拒绝方向未定；历史source-only覆盖缺口已有原日志支持 | 核现配方/投影/真实RH2适用性 |
| [DVC5839](results/iterative__dvc-5839/card.md) | 字典指标参数传递候选；真实CLI连通与单一Mock值覆盖有限 | actor下固定YAML默认/4/8、表格/Markdown/JSON |
| [DVC9395](results/iterative__dvc-9395/card.md) | gold新增dry和无remote路径有静态疑点；旧PARTIAL不是次数误拒证据 | 本地remote的pull+dry文件快照及非dry正对照 |
| [DVC3620](results/iterative__dvc-3620/card.md) | symlink主例成立；hardlink推广解释有分歧，输出数据后置条件缺保护 | 优先数据丢失错误控制的评分校准；范围对照可选 |
| [mypy10424](results/python__mypy-10424/card.md) | 受限候选；普通type比较收窄有具体漏测候选 | base/gold/禁用收窄，对照两个已有Any/Union case |
| [mypy16963](results/python__mypy-16963/card.md) | F2P正负约束有实义；返回值、Union及Boat完整原例未验证 | 先base/gold跑全部公开原例 |
| [mypy12417](results/python__mypy-12417/card.md) | 主崩溃与三P2P可解释；恢复输出可能过严，尚未证实误拒 | base/gold/保留current_type/early_non_match四实现 |

[probe_candidates.json](probe_candidates.json) 保留5个受限静态候选：Conan15422、DVC5839、Dask8597、Pydantic8511、mypy10424。前两题先核真实actor和公开行为；后三题先做指定窄语义对照再决定评分用途，均不得直接标为ready_for_probe。另7题保留具体未决问题，并非自动淘汰。

[cpu_queue.json](cpu_queue.json) 有14个已复核的选择性后续条目，包含actor验收与语义校准。**本轮没有运行任何CPU、历史项目、容器、SSH或模型；这些均为未执行方案。** 不要求14项全部完成才推进成熟单题。实际actor入口、消息、agent/54321的解释器与权限，以及修复配方是否被消费，仍须真实证据。mypy的install_wave1只是离线wheel增层，应使用原replay/derived-image条件，不套其他配方的revised_install wrapper。

复核带来的实质增量已保留出处与分歧。8511继承疑点是主审发现、reviewer第二阶段补核，不能算独立重发现。9395旧候选失败在缺bar，未到checkout计数；主稿中混用的日志行号已由review校正，封存稿原字节保留。3620采用reviewer的数据后置条件负对照优先，主审的symlink-only范围对照仍保留为可选；CPU不能裁定hardlink公开义务。12417加入reviewer的较窄current_type候选，避免将body跳过和subject类型变化混为一个问题。

5706的有界补证已由原reviewer完成：12份09-16矩阵原日志显示base/gold旧Sequence各16过，source-only候选6败10过；gold/候选官方完整文件均277过1xfail。09-09完整候选满分另有两条账本与原日志支持。独立脚本、旧root计分、现配方grader和正式actor四层证据不合并；矩阵pytest日志本身没有UID/网络启动表头，条件声明与直接计数分层。旧review正文和初判保持不变，新结论仅追加。无需重跑旧脚本以重证同一历史事实，不扩大generator/string结论。

最终只读核验通过：12份结构化记录、12个独立公开上下文、37份封存文件、角色开放顺序和所有85份逐题产物；3个来源文件、36个来源行、9,791个base文件字节/可执行位、24份noop/gold日志引用与关键RH2源码身份无失配。核验见 `runs/swegym_quality_batch01_20260921_coordination/final_record_check.json` 与 `final_input_identity_check.json`。Dask8597使用合法source-qualified task_id，已修正校验器的无前缀假设，未改已验收记录。

本批由6道已知校准题和6道固定抽样题组成，不能据此估计全216题缺陷率。实际费用/运行量未观测则保留null；题目、test/gold、评分参考、生产实现和文件排除规则均未改。首波四题沿已验收结论收口，未重开。下一固定小批等待总协调者明确派发，不自行扩到216题。
