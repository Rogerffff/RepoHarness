# R2E 13题：本地证据续接清单

整理：2026-09-29。**本轮不直接转类**：4075 评分修订可验收，但公开复现仍需窄修；22e98 待 fresh 公开阅读与正式交付；其余按已知缺口继续。旧 probe_ready、S2 标签和后检许可均不作为豁免。

本轮未 SSH、未启动容器、未运行模型；现有 R2E 机器连接已由主线程确认不可用。下列矩阵是待验收目标，已有运行事实另列。全部来源 SHA256、当前材料身份、选定正式账本与 actor 开发结果见 [JSON](r2e_inventory.json)。常规题基于既有独立意见和当前作者卡续接，不冒称 fresh 初审；4075 的完整日志专项重算与 scrapy rev2 的 observed 重算已单列。

| 次序 | 题目 | 当前需完成 |
|---|---|---|
| 1 | aiohttp__4075c653 | 评分修订独立验收通过；明确仍需改正题面 bytes 插入 f-string 的错误复现。 |
| 2 | orange3__22e98f8f | 明确：采用已通过独立审查的 R-f 草案；公开包已准备。 |
| 3 | pillow__2d01f7d0 | 明确：处置 pytest.warns(None) 开发兼容；复用已完成 v11 九方评分。 |
| 4 | scrapy__a95a338e | 明确：采用已完成试跑的第2版，C1 替代 gold，恢复警告两键并覆盖 partial 绑定方法。 |
| 5 | aiohttp__1c1c0ea3 | 明确：将既有 cleanup 错误后检变为正式行为断言，允许抛出或报告任一合理路线。 |
| 6 | coveragepy__ea6906b0 | 明确：补已有 .gitignore 内容保留与实际忽略效果；核 open 替身接受 encoding 的合理写法。 |
| 7 | numpy__d805e9b6 | 明确：补 n=3000/threshold=2000 的摘要保值对照；改正 Actual 说明。 |
| 8 | orange3__4014f248 | 明确：加入已有小量级分割回归，拒绝以 round(p,10) 合并不同值的 C3。 |
| 9 | aiohttp__61833518 | 明确：中性改正 all(write.mock_calls) 恒真复现，给出已验证的有效断言；恢复目标相关客户端/服务端兼容或交付等效公开路径。 |
| 10 | aiohttp__240da100 | 明确：采用已有 mock 等效公开复现；处置两项兼容死键并验 SC1。 |
| 11 | datalad__6b6fa389 | 明确：字段直查避开 __eq__、非示例 host:path、合理分类放宽但保留按字段重建原串。 |
| 12 | orange3__50f6a758 | 明确：R-b 放宽名单格式、R-c 覆盖加载数据/混合文件/numeric 与已匹配定义仍生效。 |
| 13 | orange3__9b5494e2 | 明确：A+B′ 加 G1 多分类默认模型回归断言，并绑定最终内容的环境配方摘要。 |

## 1. aiohttp__4075c653

评分修订独立验收通过；明确仍需改正题面 bytes 插入 f-string 的错误复现。

- v11 七方、完整日志、136 键映射、替代正对照和 actor 七命令均可收口。
- 当前公开题面原例 1 在 base 已抛 InvalidHeader；旧卡所谓可选 R-f 不再适用当前严格口径。
- 三个 C 扩展 expected FAILED 键已解释；当前离线纯 Python 路径不会因合理源码修复翻转，不能据其存在要求全 PASS。

**依赖：**窄 R-f、fresh 公开读者和实际题面交付核对；如以后开放 C 扩展构建路径，先重定 expected/开发范围。

**最小验收矩阵（预期）：**不重跑 v11 七方。复用 ALT2 主正对照、ALT1 备选；原 gold/noop/DG1=0，ALT1–ALT4=1；新公开复现 base 失败、ALT2 通过并核实际消息。

**当前材料：**修订 ['r2e-mr-061', 'r2e-mr-062']；expected 136 键。非 PASSED 状态必须按 JSON 精确映射解释，不强迫全 PASS。

**原件：**[card.md](../../r2e_lifecycle_20260929/results/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/card.md)；[review.md](../../r2e_lifecycle_20260929/results/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/review.md)；[revision_plan.md](../../r2e_lifecycle_20260929/results/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/revision_plan.md)

## 2. orange3__22e98f8f

明确：采用已通过独立审查的 R-f 草案；公开包已准备。

- 新公开读者未完成；正式 ingest 仍为含答案的旧题面。
- 最终实际消息尚未捕获，当前 consumer/准备预算须核对。
- DG 正式评分已完成且为 0，不再是待跑项。

**依赖：**fresh 公开读者；主线程正式 R-f/pins/ingest 落地与 consumer 核查；采用已验证 1200 秒准备预算并记录实际生效值。

**最小验收矩阵（预期）：**复用原材料 noop=0、gold=1、DG=0（DG 20/23，setup 303.30s）。新读者独立读需求；核正式消息 hash 等于修订后 f8701d3a…，不重复不变评分矩阵。

**当前材料：**修订 []；expected 23 键。非 PASSED 状态必须按 JSON 精确映射解释，不强迫全 PASS。

**原件：**[revision_plan.md](../../r2e_lifecycle_20260929/results/orange3__22e98f8f4cccc25f0d0217f9f4251b66d49b4237/revision_plan.md)

## 3. pillow__2d01f7d0

明确：处置 pytest.warns(None) 开发兼容；复用已完成 v11 九方评分。

- actor 8命令均执行，但 public_tiff_tests 两个 pytest 8 兼容错误，all_match_expect=false；不能写全过。
- 评分修订含 FillOrder 误拒解除已具9方正式证据，尚需完整题级收口审查。

**依赖：**窄 R-d 或公开等效命令；兼容处理若影响正式 expected，需联动重标版本并定向复验。

**最小验收矩阵（预期）：**复用 gold/C1/C1FO2=1，noop/D/C3/C2/A/B=0；agent 跑修订后的公开 TIFF 开发路径，base 保持原题失败，正确解修好且相关回归不新增。

**当前材料：**修订 ['r2e-mr-063']；expected 62 键。非 PASSED 状态必须按 JSON 精确映射解释，不强迫全 PASS。

**原件：**[card.md](../../r2e_lifecycle_20260929/results/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/card.md)；[review.md](../../r2e_lifecycle_20260929/results/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/review.md)；[revision_plan.md](../../r2e_lifecycle_20260929/results/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/revision_plan.md)

## 4. scrapy__a95a338e

明确：采用已完成试跑的第2版，C1 替代 gold，恢复警告两键并覆盖 partial 绑定方法。

- 新版 rev2 9次试跑已齐，重算 observed 与 expected 一致；此前中断摘要已过时。
- 最终新版独立复核、正式材料/镜像、正式矩阵仍缺。
- 新 setUp 只恢复 UserWarning；其它 warning 类别是否为合理修复相关需按公开要求核，不以改类别属于题外直接豁免。

**依赖：**第2版定向独立审查；主线程落正式 material/expected 与镜像；C1 正对照元数据绑定。

**最小验收矩阵（预期）：**C1×2=1、noop×2=0、gold/D/C2/C2b/C3=0；5键，复活两键 PASSED；完整日志区分 partial 与警告失败原因。试跑不再重复。

**当前材料：**修订 []；expected 5 键。非 PASSED 状态必须按 JSON 精确映射解释，不强迫全 PASS。

**原件：**[card.md](../../r2e_lifecycle_20260929/results/scrapy__a95a338eeada7275a5289cf036136610ebaf07eb/card.md)；[review.md](../../r2e_lifecycle_20260929/results/scrapy__a95a338eeada7275a5289cf036136610ebaf07eb/review.md)；[revision_plan.md](../../r2e_lifecycle_20260929/results/scrapy__a95a338eeada7275a5289cf036136610ebaf07eb/revision_plan.md)

## 5. aiohttp__1c1c0ea3

明确：将既有 cleanup 错误后检变为正式行为断言，允许抛出或报告任一合理路线。

- C3 取消后 gather(return_exceptions=True) 会吞掉 cleanup 错误，v5 仍得 1；旧 S2/后检不能豁免。

**依赖：**题级 R-c 版本落地。

**最小验收矩阵（预期）：**gold=1、C1=1、C3=0；noop/F1/C5 仍=0。核 cleanup 错误可观察且既有关闭顺序不退化。

**当前材料：**修订 ['r2e-mr-040', 'r2e-mr-041']；expected 57 键。非 PASSED 状态必须按 JSON 精确映射解释，不强迫全 PASS。

**原件：**[probe_card.md](../../r2e_lifecycle_20260929/results/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/probe_card.md)；[revision_plan.md](../../r2e_lifecycle_20260929/results/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/revision_plan.md)

## 6. coveragepy__ea6906b0

明确：补已有 .gitignore 内容保留与实际忽略效果；核 open 替身接受 encoding 的合理写法。

- gold 无条件覆盖用户已有 .gitignore。
- C-C 添加 encoding 后因公开测试替身签名得 0；不能仅以公开测试同样失败认定无误拒。

**依赖：**题级 R-b/R-c；参考正对照需为安全合并实现。

**最小验收矩阵（预期）：**安全合并正确解=1、encoding 合理解=1；覆盖已有内容的 gold 类候选=0、空文件 C-B=0、提前写目录 RE=0、noop=0。核已有规则保留与新报告实际被 git 忽略。

**当前材料：**修订 ['r2e-mr-036', 'r2e-mr-037']；expected 48 键。非 PASSED 状态必须按 JSON 精确映射解释，不强迫全 PASS。

**原件：**[probe_card.md](../../r2e_lifecycle_20260929/results/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/probe_card.md)；[revision_plan.md](../../r2e_lifecycle_20260929/results/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/revision_plan.md)

## 7. numpy__d805e9b6

明确：补 n=3000/threshold=2000 的摘要保值对照；改正 Actual 说明。

- n>threshold>=1500 的混合截断路线可通过现有断言但静默丢值（目前为静态推导，不冒称已评分）。
- K-A5b 的大 edgeitems>=501 同族丢省略号风险已有具体推导，不能因旧 S2 标签自动豁免；需核影响并用可涵盖声明范围的正对照。
- 二维窄轴题外，不并入本题修复。

**依赖：**题级 R-c/R-f；大 edgeitems 的最小辨别控制与正对照边界。

**最小验收矩阵（预期）：**至少 K-A5b 在 n=3000,t=2000 应为1，混合截断=0；gold/noop/K-DE/K-DC/K-DF/DG-e/DG-g 保持0。另核 edgeitems 具体反例，必要时窄修正对照，不能先放行再后检。

**当前材料：**修订 ['r2e-mr-056']；expected 229 键。非 PASSED 状态必须按 JSON 精确映射解释，不强迫全 PASS。

**原件：**[probe_card.md](../../r2e_lifecycle_20260929/results/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/probe_card.md)；[card.md](../../r2e_lifecycle_20260929/results/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/card.md)；[review.md](../../r2e_lifecycle_20260929/results/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/review.md)；[revision_plan.md](../../r2e_lifecycle_20260929/results/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/revision_plan.md)

## 8. orange3__4014f248

明确：加入已有小量级分割回归，拒绝以 round(p,10) 合并不同值的 C3。

- C3 v9=1，但 arange(100)*1e-12、n=4 全部落一个区间；属于已知可修行为回归。
- 最终入口的 agent 真重编与 pyx_only 配对、准备预算仍需定向验收。

**依赖：**题级 R-c；最终构建/导出/加载入口；1200 秒准备预算；源 R2E 机当前不可用。

**最小验收矩阵（预期）：**gold、C1、pyx_build=1；C3、DG、C4、pyx_only、noop=0。核小量级有有效分割；agent 改 .pyx 后真重编、导出二进制并由新 grader 加载。

**当前材料：**修订 ['r2e-mr-057']；expected 27 键。非 PASSED 状态必须按 JSON 精确映射解释，不强迫全 PASS。

**原件：**[probe_card.md](../../r2e_lifecycle_20260929/results/orange3__4014f2483e3bab0621c9ae0f994947c008183253/probe_card.md)；[revision_plan.md](../../r2e_lifecycle_20260929/results/orange3__4014f2483e3bab0621c9ae0f994947c008183253/revision_plan.md)

## 9. aiohttp__61833518

明确：中性改正 all(write.mock_calls) 恒真复现，给出已验证的有效断言；恢复目标相关客户端/服务端兼容或交付等效公开路径。

- 旧题面复现断言恒真；真实 client/server 的 asyncio 兼容改写导致 TypeError。
- 公开 protocol 层已可验证核心目标，需明确它能覆盖所声明的目标，不以无关 cookie 旧测全过为条件。

**依赖：**R-f 公开材料与 R-d/等效开发路径版本；相关开发兼容范围核定。

**最小验收矩阵（预期）：**gold/AP2/A1=1；noop/AP1/AP1m=0。最终公开复现由 agent 执行，压缩与 chunked 分帧、解压载荷及 EOF 均核对。

**当前材料：**修订 ['r2e-mr-044', 'r2e-mr-045']；expected 49 键。非 PASSED 状态必须按 JSON 精确映射解释，不强迫全 PASS。

**原件：**[probe_card.md](../../r2e_lifecycle_20260929/results/aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2/probe_card.md)；[revision_plan.md](../../r2e_lifecycle_20260929/results/aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2/revision_plan.md)

## 10. aiohttp__240da100

明确：采用已有 mock 等效公开复现；处置两项兼容死键并验 SC1。

- 题面顶层 ClientRequest 导入无效、真实协程路径 TypeError；部分公开文件不能收集。
- TCP/Unix 两个 expected FAILED 死键需移除或恢复有效的明确方案，不等待候选偶然翻转。

**依赖：**R-f 与 R-a/R-d 版本；不扩默认端口/Host 等未定范围。

**最小验收矩阵（预期）：**gold、AL1、SC1=1；noop/DG1/WR1/WR2=0；agent 执行新 mock 复现及相关开发命令，核两死键处置前后精确键集。

**当前材料：**修订 ['r2e-mr-051', 'r2e-mr-052']；expected 35 键。非 PASSED 状态必须按 JSON 精确映射解释，不强迫全 PASS。

**原件：**[probe_card.md](../../r2e_lifecycle_20260929/results/aiohttp__240da100151933883d7dea0528d45877df025b92/probe_card.md)；[card.md](../../r2e_lifecycle_20260929/results/aiohttp__240da100151933883d7dea0528d45877df025b92/card.md)；[review.md](../../r2e_lifecycle_20260929/results/aiohttp__240da100151933883d7dea0528d45877df025b92/review.md)；[revision_plan.md](../../r2e_lifecycle_20260929/results/aiohttp__240da100151933883d7dea0528d45877df025b92/revision_plan.md)

## 11. datalad__6b6fa389

明确：字段直查避开 __eq__、非示例 host:path、合理分类放宽但保留按字段重建原串。

- C-A 合理解=0，D-eq 绕过解析=1；需独立复核终稿与 R-b/R-c 落地。
- 不能以 str(URL(url)) 等于 url 作为重建验收：构造器保存原串会使其恒真。

**依赖：**独立修订审查；1200 秒准备预算；新的 material 镜像和 actor 预检。

**最小验收矩阵（预期）：**gold/C-A=1；noop/C-B/D-eq/D-eq-minus/D-hard=0。gold/noop 各2，其余各1（原计划）；17 键 exact expected，保留已声明 FAILED 键解释。

**当前材料：**修订 []；expected 17 键。非 PASSED 状态必须按 JSON 精确映射解释，不强迫全 PASS。

**原件：**[card.md](../../r2e_lifecycle_20260929/results/datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb/card.md)

## 12. orange3__50f6a758

明确：R-b 放宽名单格式、R-c 覆盖加载数据/混合文件/numeric 与已匹配定义仍生效。

- K1 全列变量名=0，K2/K3/K4 错解=1；独立复核终稿及正式修订矩阵未完成。
- C-deg 补丁存在，本地未找到正式 ledger/私有 probe 结果；不能写已回传。
- TypeError 题面伪影及旧公开不警告断言冲突需要按当前规则处置，不能仅记可选。

**依赖：**独立修订审查；1200 秒准备预算；R-f 与公开旧断言冲突的窄处置。

**最小验收矩阵（预期）：**gold/K1=1；noop/K2/K3/K4/C-deg=0；加不点名 K5=0。核警告实际点名、已匹配定义继续生效、新公开说明与开发路径。

**当前材料：**修订 []；expected 48 键。非 PASSED 状态必须按 JSON 精确映射解释，不强迫全 PASS。

**原件：**[card.md](../../r2e_lifecycle_20260929/results/orange3__50f6a758f1c66b8f4a18806714e3c2f4cefcab3e/card.md)

## 13. orange3__9b5494e2

明确：A+B′ 加 G1 多分类默认模型回归断言，并绑定最终内容的环境配方摘要。

- 旧方案 A/B′ 仍放行 G1（默认 multinomial 改 OvR）。
- 当前 environment_overlay.py 批准集合仍仅含旧 512277… 摘要，加入 material 后的配方未获绑定。

**依赖：**主线程/公共实现负责人处理最终配方内容身份；SciPy 1.5.4 / +env_v2 不可省略。

**最小验收矩阵（预期）：**gold、V1/V3/V4/V5=1；noop/W1/V7/P1/G1=0；先证 base/gold 的默认与显式 multinomial 行为关系，不能照抄 gold 数值。保留 13 键 expected 精确状态口径。

**当前材料：**修订 ['r2e-mr-020']；expected 13 键。非 PASSED 状态必须按 JSON 精确映射解释，不强迫全 PASS。

**原件：**[revision_plan.md](../../r2e_lifecycle_20260929/results/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040/revision_plan.md)

## 首批执行建议

1. 先派 22e98 fresh 公开读者；包与提示已就绪，主线程接管正式 R-f 落地和实际消息核对。DG 已正式为0，不重复评分。
2. 4075 采用 [专项结论](aiohttp4075_acceptance.md) 收掉 v11 评分验收；只对错误公开复现做 R-f 与交付验证。C 扩展死键不得等同为必须全 PASS。
3. Pillow 2d01 只补公开开发兼容的窄验证，复用 v11 九方；Scrapy a95a 先定向复核第2版后跑正式矩阵，复用9次试跑。
4. 第一批需新 CPU 运行的题优先 1c1 cleanup、coverage 已有 .gitignore、numpy 自定义阈值。所有远端运行由主线程唯一调度，先核可迁移镜像与 consumer，再启动容器。
5. orange3 9b54 等待共用配方身份支持；不得绕过摘要检查。公共控制面、网络/捕获/停止与清理、代码版本、模型与预算是共用前提，不在这13份题卡中重复授予。

这里只给普通探针前的题级续接建议；不授予训练/留出资格，跨题答案关联与仓库划分沿用已有登记。历史评分与题卡未覆盖，未改生产源码或共享看板。
