# dask__dask-8801：历史差量

2026-09-21，主审 investigate_dask。独立前稿先封存：SHA256 `17565f2cd330aeac81970ee2634cfeb17551a6b8f4ea8d7545b1becea9f68a52`，22437 bytes，mtime_ns `1789926332853483906`。协调者登记后才开放本题历史。本文件不回改前稿，也不读取 reviewer 产物。

路径均相对 `.`。历史入口是 `runs/swegym_quality_batch01_20260921_v2/history/dask__dask-8801/refs.json`，按其只读：

- **H1**：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/records/dask__dask-8801.json`。
- **H2**：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/dask_pilot/records/dask__dask-8801.json`。
- **H3**：H2 明确引用的 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/dask_pilot/probe_8801_wording.json`。它是历史局部函数实验记录，不是 RH2 评分或本轮重跑。

本轮决定性原件位置及 N/G/L/P/B/V 缩写见 `analysis_before_history.md`“证据索引”。本轮已直接核对原日志哈希、noop/gold 两行 ledger、45 个实际执行 ID 与 43 个参考 ID。没有为历史判断重跑项目。

| 旧主张 | 处理 | 本轮证据与边界 |
| --- | --- | --- |
| H1：题面“完全没有任务”，只有不可见 hints 才能定位，应直接 reject | **推翻绝对表述；确认 H2 的修正** | P/user_prompt:1 明确要求修复；145–163 的公开堆栈定位 config 的 collect/merge/update；B/config.py:114,150–188,412–438 可见非映射穿透路径。公开信息不足以唯一规定错误处理策略，但可调查性不是缺失。报告者实际坏文件仍缺失 |
| H1：隐藏 hints 中维护者说过某具体方案、用户已自行解决；据此推断当前可见性 | **未核实该来源细节，且不作为规格** | 本轮没有读取 raw hints。当前 P/public_bundle.public_hints 只有通用工程指令和环境声明；维护者背景不自动成为 solver 可见要求。H2 同样已区分 public bundle 与 raw 私有背景 |
| H1/H2：三个英文词组固化为验收，题面没有相应约定 | **确认，证据由静态增加到历史局部实验记录** | V/test.patch 两 F2P 的逐条 substring 断言；公开源码/文档未找到相应接口约定。H3 记录 gold 两函数 passed，同义措辞版本两函数 AssertionError；两者均 ValueError、包含文件与原因，正常 mapping 保持。H3 是抽取源函数及官方测试函数实验，有源内容哈希，未附可重放命令、运行环境或完整候选源码，故不当成本轮 CPU 或完整 RH2 假拒证据 |
| H1：权限目录/文件测试在当前容器“因 root 恒失败” | **过时，确认 H2 修正** | L:9/10 明确 grader 为 rh2grader/54322；N:1354–1355 与 G:1409–1410 两参数均 PASSED，G:1503 全45 passed。H1 的旧 root 脚本失败不能描述当前非root评分，也不能外推“恒” |
| H1/H2：这两个权限测试没进参考集 | **确认** | V/grading 的 41 个 P2P 不含两个 ID；本轮逐执行 ID 对账：45执行=2F2P+41P2P+这两个额外测试。它们当前执行通过，评分覆盖缺口仍在，不能重复请求修root环境 |
| H1：去掉 OSError 忽略的候选仍“能拿满分” | **机制风险成立，候选得分未核实** | 修改分支确实有未评分的现有回归；当前 scoring.py:250–268,302–308 以参考集判分，manager 保留普通完成测试的 verdict。但 H1/H2/H3 未给该候选的完整 RH2 结果，本轮也未执行，所以不把可构造性写成实测 reward1 |
| H1：gold 行为完整、无无关修改 | **确认已查范围，收窄“完整”** | V/gold 与 G:1066–1114 只有config.py helper/调用改动；所有非dict顶层都被拒、OSError被忽略，N/G正常配置P2P与完整模块结果可靠。报告者实际坏文件未知、空/null列表形状变化和falsy非映射边界未单测，不能从gold分数证明全行为完整 |
| H1：安装/依赖可用；H2：原基线 no known environment issue | **确认 grader 范围** | L:9/10、N:1316–1347、G:1371–1402 均安装RC0/完整收集；Python3.9.19/pytest8.3.2，本题无需pytest兼容修复。actual image ID为null、无派生配方，actor激活/权限/工具/消息未验，不能扩成完整解题环境pass |
| H1：必须删除长conda回显后才可用，模型3次定位预期极低 | **未证实；不作过滤依据** | 大量包列表是可精简噪声，但有准确堆栈。没有本题真实模型数据；是否精简是版本化材料选择，不能推断基座成功率或把删回显当先决条件。H2也已保留该主张未解决 |
| H1：本包唯一修改 config.py，因此题目关系通过 | **未核实全包关系** | 本轮没有读取全包 prescan 或其他未分配题，不以同文件/不同文件证明独立性。保持跨题关系未知，不向前题卡片追加本题结论 |
| H2：应考虑独立修订版，先完整RH2验证措辞候选 | **方向一致，机器状态继续 needs_review/static_review** | 当前有明确格式争议和局部反例记录，原始reward保留。正式修订前做窄CPU对照；是否修改题面、oracle、P2P分别说明依据，不能把gold文字直接写入题面以维持它通过 |

本轮相对两份旧记录的实质增量：

1. **原例类型缺失**：题面是 `str.items()`，新增顶层测试只给 `[1234]`。完整旧测试与全部 P2P 没有顶层坏字符串的 collect/refresh/import 样本。提出“只拒list+包装语法错误”的一般部分实现；它仍可保留字符串原bug。这是静态候选，完整reward未知，不能称新运行反例。
2. **路径引号也是独立约束**：两 F2P 都要求 `repr(fil_path)`，不仅是英文同义词。H3只描述“wording_only”，不能推断曾隔离检验路径引号；本轮候选可把此边界记录清楚。
3. **诊断内容覆盖有限**：语法测试要求文字 `original error message`，却不核实真正包含parser原因。适当修订应保护有用诊断语义，不能简单删掉所有内容检查。
4. **空输入语义区分**：gold跳过None，base追加空dict；合并结果等价。falsy非mapping由旧吞掉变成拒绝；记录边界而不凭差异宣布gold回归。
5. **适用环境与投影落实**：给出具体L行号、真实身份/镜像/scripts digest、完整测试结束/安装RC、官测恢复和config.py投影；actor的未知单列，避免当前环境和历史root实验混用。

历史是否改变初判：**处置不变，误拒证据更强一层**。前稿的措辞反例从“本轮静态预测”获得 H3 所记历史局部执行支撑，但缺完整RH2和可重放候选原件；权限环境问题在前稿就已正确判定为当前通过，历史确认它早已被修正。不能宣称本轮首次发现这两项旧问题。字符串漏测是本轮新增线索。

唯一优先下一步仍为精确base/原始配方中的同语义、不同措辞候选与gold控制，先公开语义检查再真实RH2评分，按失败断言定位误拒；不重复只做抽取函数试验。之后用lists-only负例检验拟修订断言的检出性，再由协调者决定版本化修订及是否进入基座探针。所有新运行均未执行，费用/耗时不从H1自报22分钟推算。
