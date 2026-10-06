# 1c1：新增取消清理P2P的实际五行核收

2026-10-03。题主已读回实际原件，非作者执行窄核已完成并[核收](review_acceptance_five_rows_20261003.json)。本批只增加一个已批准的 P2P（保留已有正常行为的测试），题面、runner、旧58键及两种合理清理错误上报方式不变。

**新判据能检出完整原 Coder 候选的资源收尾回归，同时保留基线、gold、C1、完整原 Qwen 的取消清理行为。** 每行均实际收集并评分同一组59个精确键；相对各自原适用结果，旧58键逐项不变。详见[固定parser读回](results_five_rows_20261003_v2.json)。

| 原候选／对照 | 新版匹配数 | 新增P2P | 本批诊断reward | 旧58键 |
| --- | --- | --- | --- | --- |
| 原baseline | 57/59 | PASSED | 0 | 原两个F2P失败保留 |
| gold | 59/59 | PASSED | 1 | 全匹配 |
| C1 | 59/59 | PASSED | 1 | 全匹配 |
| 完整原Coder（7条Frozen） | 58/59 | FAILED | 0 | 全匹配 |
| 完整原Qwen（2条Frozen） | 59/59 | PASSED | 1 | 全匹配 |

基线的两个失败仍为 `test_run_app_raises_exception[pyloop]` 和 `test_run_app_raises_exception_on_server_start_failure[pyloop]`，新增P2P不要求基线解决原问题。Coder只在 `test_run_app_cancelled_coroutine_cleans_resources[pyloop]` 失败，没有缺席或额外键。

## 实际资源状态与判据

五行 main done/cancelled 均为 true；它们仅是诊断，不是评分条件。baseline、gold、C1和Qwen的快照均在观察者补清理前显示：worker 已 done/cancelled，worker及generator的 finally 均已执行，generator和loop已关闭，pending为0。

Coder在同一时点显示：worker未done/未cancelled，generator及loop未关闭，pending为1，events只有两项started，没有cleanup事件。实际失败是补清理前的 `assert worker.done()`，同一测试中的其余资源状态也已打印。测试finally之后的任务repr或events可能已受补清理影响，不能用它们反推库成功清理；本批依据的是先复制的快照。之前的[公开取消归因](../followup_1c1_cancelled_main_20261003/results_public_cancelled_main_20261003.json)按精确原源码解释该分支，本批没有重复做归因或新增模型采样。

## 固定输入与完整消费

R22的094/095替换080/081，没有叠加同一目标。题主核对发布回执和1491个成员的SHA/bytes，hidden/expected与材料窄核的文件逐字一致。新grader为 `sha256:ea62d2733e1dded64b4e11c174f02de8bb7c1a7f69c19ae7c9d2bb7d8f3e01a8`；实际配方为 `r2e_derive_v1+material_v2+sysconfig_v1`，无aiohttp依赖pin新增。旧exact00ad仅作为actor供给证据，未冒充新hidden grader。

准备阶段38个、五行阶段75个归档成员逐一核SHA/bytes。沿固定 `replay_grade.py run` 入口，完整git binary patch保留coverage及helper；每行307条baseline与原baseline完全相同，Coder7条及Qwen2条新导出Frozen entries逐字节／模式与原Frozen相同，projection全部保留。Coder的 `comprehensive_test.py`、`test_exception_handling.py` 仍如实标记为test-like；未删减或美化这些标记。

五行结束标记完整，runner前后摘要相同，参考缺席0；正式评分配置为UID54322、2CPU、4GiB、512pids、deny_all，候选apply记录为agent/54321。各行manager清理均为 `rm:ok`，结束后本批builder及五行标签下实际容器／网络均为空，镜像实际inspect为linux/amd64。总时限未触发，不能据此宣称信号超时路径已完成daemon清理。

通用spec／账本的 `grading_materials_identity`、`derived_image_recipe` 和 `resource_facts` 仍为null；本批没有独立保存五行的cgroup/prelaunch原件。policy是配置证据，未改manager验证路径的既有审查可按精确版本复用，但不升级为本批新增资源资格。实际材料消费由固定发布、prepared私有view、日志hidden/runner和实际overlay交叉绑定，不伪造typed training binding。

## 当前用途与停止条件

材料[Falsifier窄核](reviews/non_author_cancelled_P2P_material_20261003.md)已核收，实际五行已由同一批[ProductionTracer](reviews/non_author_cancelled_P2P_execution_20261003.md)完成执行窄核并核收；不增加第三个审查者，不重做未改reader或旧全矩阵。

本批CPU重评分单列为原候选在新材料上的诊断，原两份raw1/58、原Frozen和历史报告保持原样。旧binding仍阻断后续使用；新材料消费通过也不自动签发GPU新binding或训练／留出资格。普通模型重复继续服从统一队列暂停策略，本批不提出新的模型任务。非作者实际核收已完成且无本批阻塞发现，本次材料修订结束；发现新具体问题才按其证据处理，不为预期结果改oracle。
