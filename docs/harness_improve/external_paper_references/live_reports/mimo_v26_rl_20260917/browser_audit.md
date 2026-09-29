# Computer use 覆盖记录

日期：2026-09-17；入口 https://mimo.xiaomi.com/rl/；使用 Codex in-app browser 的 computer use、AX/DOM 读取和页面点击。浏览器原始画面与页面状态保存在本任务的工具会话中；永久数值证据另存公开接口快照。

## 页面覆盖

| 范围 | 操作与覆盖 |
| --- | --- |
| Overview | 阅读 Pro/Flash 状态、公告、18 个 pinned 指标入口、DeepSWE 图、两条动态采样 feed、完整来源配额表 |
| Batch composition | 分别切换 data source 与 harness (trained)，核对两个 run 的表；25 来源和 23 harness |
| About | 读取全部内容；当时仅有直播说明和官方 X 链接 |
| Metrics 总目录 | 14 大类，共 2,067 标签 |
| 全标签清单 | 在页面搜索框输入 `/.*/`，逐批点击 show more，直至最后 3 条展开；没有剩余分页 |
| actor | 读取全局优化字段与 agentic/各来源结构；lr、clip、TIS、entropy、梯度与更新状态 |
| critic | 通过筛选同时检查全局 advantages/returns/rewards/score 的 12 张卡片与曲线；全目录包含全部 324 标签 |
| ctx_prompt/response/total_length | 分别进入三个主目录，读取全局极值、均值、clip_ratio 与来源结构 |
| dynsam | 检查全局、配额、passrate、来源 step/held/carryover 结构 |
| env | 检查 active、possible_leak、error、setup 及来源结构 |
| partial | 进入主目录、0 分桶、0/train_infer_diff/new_infer；核对同版本 KL 与尾部统计；完整目录含 lag0–9 和各来源 |
| penalty | 进入 stage_credit_group，展开全部全局标签并滚动读取；另进入 select_v4、select_v4_nogold；识别 harness/routed/action/signed 子结构 |
| perf、timing_s | 分别进入并读取全部全局值 |
| train | 检查全部子结构；进入 verdicts，读取 carried/rejected/expired/trained 等 |
| train_infer_diff、training | 进入目录核对切片和优化步数 |

所有公开序列随后按页面使用的同一只读接口保存，重复切片也保留，不仅保存重点指标。

## 覆盖清单交叉校验

浏览器展开的 2,067 个标签按字典序以换行连接：94,156 字符，FNV-1a=67ad9a49。

从两个 run 的 tags/series 接口重建的并集得到完全相同的数量、长度和摘要，分组计数也相同。对应 [verification.json](verification.json)。FNV 用于清单一致性对照，原始文件完整性另用 SHA-256。

## 读数规则

- 首次截图时约 10:21；正文采用 10:24 开始冻结的数值，避免把边看边变化的费用和队列混作同一快照。
- 两 run 主曲线步数不同；每个 metric 可能还有独立缺失点。
- 前端卡片用最近非空值，因此某张卡的数字可能来自此前 step。目录明确标注 `缺失；最近 sN=…`，图不把缺失点补零或前值填充。
- 分组或路由拥有标签，不代表该功能本次实际执行；pass2 的尝试数与耗时均为零就是实例。
- 主曲线与 events 分开记录，Flash 旧 s16/s17 不混进当前 s1–15 的序列。
- 页面描述与可见指标目录分别核对：配置中有 `avg@n_no_infra`、hist9 等解释，但本次 tags 并未公开对应序列；不因配置预留说明就宣布这些数据可用。
- 全部曲线只代表当次公开数据，匿名来源和 harness 未作猜测性映射。
