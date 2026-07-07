"""训练后端 adapter 层（S1-3 起）。

依赖方向纪律：adapters -> contracts（单向）。adapter 负责把某个训练框架的
产物投影成 contracts 里的中立对象（TrajectoryProjection 等）；治理层
（gate / 投影扫描）只消费中立对象，看不见框架细节。

- adapters/slime/           slime 主线：projection.py（S1-3）+ generate.py（S1-6 编排胶水）
- adapters/verifiers_projection.py  verifiers Trace dict -> 投影（S1-8，评测/导出线；
                            EvalClient 文本中继按显式降级标注投影，绝不伪装 token-faithful）
- adapters/offline_export/  gate 之后的 FinalizedRollout -> TrainingExportRecord（S1-8；
                            audit 档双道防线拒收，records.jsonl + digest 清单落盘）
"""
