# Dask 包：三题静态复核完成

三题均完成公开读者、主审、独立reviewer和协调收口，21份逐题文件、9份封存初判齐全。[结构、阶段、请求配置与hash校验](pack03_output_verification.json)通过。6626、7656保留为有条件的开发候选；9378先做私有质量诊断。三题均为needs_review/static_review，仅供development_diagnostic，实际actor与探针资格未验。五名审查角色显式请求gpt-6-astra/high/fork_turns=none，不声称后端独立验真或OS隔离。

| 题目 | 决定性结论 | 唯一优先下一步（未执行或派发） |
| --- | --- | --- |
| [6626](results/dask__dask-6626/card.md) | 新K fixture扩展已有dtype断言，noop先在该断言失败；gold修复已知空类别Series。两条公开set_index流程未直接测，空CategoricalIndex是邻接旧边界。compat_v1下sparse两侧已通过；runner digest变化原因尚未完全核清。 | 实际actor运行题面两条set_index流程，记录初态、身份、导入位置、RC、类别元数据与compute结果。 |
| [7656](results/dask__dask-7656/card.md) | 缺失init=False字段目标与F2P一致；最终a==3未约束完整dataclass返回状态。旧“gold保留所有已有字段、过滤init必丢post_init值”的oracle没有源码支持，已撤回。 | 实际actor运行公开Entry→delayed fun→compute及默认字段、嵌套求值，保留现存非init字段语义边界。 |
| [9378](results/dask__dask-9378/card.md) | ones/zeros走assert_eq→np.ma.allclose(masked_equal=True)，无直接mask equality；empty另有显式mask断言。错mask漏放是静态疑点，尚无错误候选完整得分证据。 | 一项私有CPU诊断只改ones/zeros的mask，保留类型、shape、dtype、常量值及Dask包装；对比窄官方断言与显式mask比较。 |

原运行按原条件核对：6626 compat_v1为1 failed/15 passed→16 passed，expected为1 F2P/14 P2P，额外sparse两侧通过；7656 compat_v2b为1 failed/49 passed/2 xfailed→50 passed/2 xfailed，expected为1 F2P/48 P2P，不能称52项全通过；9378 baseline01/w01-1账本11/12行为3 failed/134 passed→137 passed，noop实败于ma新入口缺失，不能说已重跑题面顶层mask复现。主审与reviewer核对选中原ledger、命令、逐项状态、diagnostics与投影/恢复边界；本轮没有新增项目运行。

9378的另两项收窄保留在最终card/record：derived_from能否标记dtype不支持，依赖目标NumPy的可识别显式签名和doc参数行，本轮未读取它们，不能断言实际标记存在；empty未初始化值不应要求具体数值或随机/非固定。公开读稿、主审与reviewer初判均保留封存版本，后续限定见delta、review与协调裁定。旧“缺docstring就导入崩溃”被本base的None处理直接反驳。

协调者清理6626/7656的recipe及check2/23/27/40跨题模板残句，补录7656完整返回状态覆盖边界，未改变核心分类。六份主审card/record原版先匹配完成hash再归档；当前hash和修改理由见[修订链](coordinator_revisions/pack03_dask/revision_log.json)。所有初判、delta、review及历史原件未回改。

actual actor消息、初始工作树、忽略资产、身份/权限、工具环境和答案可见性仍unknown；历史grader成功不能替代这些事实。source digest和actual image ID分开记录，9378实际ID缺失不补猜测。check29实际暴露与usage授权私有阅读分开，check40保持unknown。未证gold新增回归，也未证明一般正确性、无误拒或无漏检。

具体后续需求见[定向提案](pack03_followups.md)。私有窄断言诊断不等于完整RH2候选评分，也不能认证actor资格。任务二仍由Claude B负责，本任务不执行或派发。累计九题静态交付为六项有条件开发候选、三项优先质量处理；首12尚余Pydantic包，储备20题保持待命。
