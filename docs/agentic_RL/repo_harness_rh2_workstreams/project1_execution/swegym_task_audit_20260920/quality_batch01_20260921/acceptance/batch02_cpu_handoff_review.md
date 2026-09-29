# B2 CPU 交接补审

2026-09-21。有界静态审查，仅针对 `expansion/batch02/{cpu_queue.json,probe_candidates.json,batch_report.md}`、Moto7584/5752/5134、pandas56849/48106/53958 的具体交接引用及必要源码。DVC/mypy 六题仅核队列映射，沿用总协调既有验收，未重新审题。

**结论：未发现阻塞选择性交接的设计问题。** 12 个队列 ID 唯一，与 10 个受限候选、2 个不优先题完整对应；全部标记未执行。当前交付可以用于安排实施与受控诊断，不能当作 actor 已验、模型启用或新候选已经获分的证明。

## 六题具体核对

| 任务 | 可实施性与判断边界 |
| --- | --- |
| Moto7584 | base/gold/重复订阅早返回前校验的候选，以及两种操作顺序、有效 endpoint 控制、完整 ARN 文案判据清楚。`install_wave1/tasks/getmoto__moto-7584/image.json` 可定位，派生 ID 与指定账本一致；配方只有 wheel COPY/离线 ENV，原 replay 的 derived-image 入口合适。队列明确仅作规范冲突诊断，不列能力候选。 |
| Moto5752 | “未匹配返回 False、匹配继续外层过滤器”的最小变体可在公开 `_match_filters` 中定位；有标签顺序、普通字段组合、多 Values OR 控制，`w/world` 区分前缀行为。没有把仅改 hints 拼写当完整候选，也没有把得 0 自动解释为不公平。原公共镜像 digest 和账本可定位。 |
| Moto5134 | 唯一优先方向为真实 public-image actor 的存在性与本地 Events→Logs 开发检查，不额外制造语义反例。公开脚本、dummy 凭据、区域、关闭 server mode 和窄测试均可定位；没有要求未 mock 的 AWS 对照。可选 grader 的 sqs_v1 输入 recipe、wrapper 与派生 ID 齐备，明确不替 actor 资格。 |
| pandas56849 | 只对非 Period、已识别旧 alias 做规范化并发 M warning 的变体足够具体；保留 MS/ms、倍数、非法输入与公开月末行为，先验语义再判断误拒。Cython 重编和实际扩展加载来源被明确要求，没有把 Python 源文件变更自动当候选生效。固定 grader 可先做，不强求先验整个 actor。 |
| pandas48106 | 优先检查剩余两组 tz alias（2+4 个完整节点）的真实摘要次序、混合状态和成员缺席。现有输入 `pandas_meta_v3/reference_bindings_v1.json` 确实仅含本题 3 组 Period→7 节点，没有把所有 parser identity 问题说成已修。当前 parser/binding 源码可读；合成控制可先离线做，不必等 actor 或 pandas 重编。合成结果与真实候选错分分开，保留历史六节点全 PASS 和原 0/1。 |
| pandas53958 | gold 与把 NA/NaT 单例误导出为类型的候选，直接检验“不是真实类型仍可过名称列表”的具体假设。公开导出路径可定位；两个 `is type(pd.NA/NaT)` 判据独立于命名空间争议。`_libs` 真类方案保留为可选后续，没有叠加为第二必测。 |

## 可定位的修订输入与尚待准备事项

- 48106 的 `--recipe <this task input recipe>` 可沿最终 review 定位到 `runs/env_recipe_repair_20260919/pandas_meta_v3/recipes/pandas-dev__pandas-48106.json`；该输入与 `reference_bindings_v1.json`、逐运行 `recipe/` 审计输出已明确区分。可在派发命令时直接填入输入路径，不应拿审计输出或其 hash 替代输入身份。
- 5134 的输入为 `runs/env_recipe_repair_20260919/sqs_v1/recipes/getmoto__moto-5134.json`；已静态核 wrapper 支持所列 `--code-root/--recipe`。48106 wrapper 同时支持 `--bindings`。两者的 code-root 指向含 `src/` 和 `scripts/` 的 RH2 根。
- 各题 prepared-summary 实际部署路径、当前可用镜像、候选 diff/SHA、实际导入与构建证据尚待执行者落实；5134 的正式 actor 入口也尚未提供运行验收。这些是已披露的未来准备，不是隐藏的设计阻塞。
- 48106 历史 `resources_v1/code/rh2` 的精确字节副本未在本地认证。可以固定当前源码做新诊断；不能据此声称复现了历史全部 parser/manager 字节或推翻历史分数。队列已保留此界限。

## 两处非阻塞文字收紧

1. 5134 `diagnostic_steps` 把双 detail 的 Logs 复现称为 **C3**；对应 `public_read.md` 实际为 **C4**，C3 是旧窄测试。`actor_entry.public_checks_ref` 已列 C2/C3/C4，操作描述也正确，执行者可定位；派发时修正编号即可。
2. 53958 冻结错误候选时宜明确“保留 gold 的完整导出名单及新增 `__all__` 两项，只把两名字绑定成单例”。队列“preserve … __all__”若被理解为原 base 的名单，会额外混入漏填 `typing.__all__`；最终 review:61 已明确要求名单齐全。按该处冻结 diff 即可，无需增加实验。

## 全批边界与本轮证据

没有把 12 条设为全批必过门；DVC3576 为备选，53958 的第二路线可选，5134 无争议不强造反例。固定 grader 语义/解析诊断与正式 actor 开发条件分列，历史 grader/54322 和 apply_user/54321 没有被混称。未见“静态候选”被升级成正式训练、评测或模型能力已通过。

本轮自行只读脚本核了 JSON、12 条映射、六题精确历史账本行及所列镜像身份、review/入口/配方路径；直接读取相关候选作用点、两份 wrapper、绑定输入和 parser。未导入或执行项目代码，未运行测试、安装、容器、SSH、模型或新 CPU 实验；只新增本审查文件，未改协调产物或历史证据。
