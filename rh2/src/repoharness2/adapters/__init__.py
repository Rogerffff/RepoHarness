"""训练后端 adapter 层（S1-3 起）。

依赖方向纪律：adapters -> contracts（单向）。adapter 负责把某个训练框架的
产物投影成 contracts 里的中立对象（TrajectoryProjection 等）；治理层
（gate / 投影扫描 / 离线导出）只消费中立对象，看不见框架细节。

- adapters/slime/     slime 主线：projection.py（S1-3）+ generate.py（S1-6 编排胶水，未来）
- adapters/offline_export/（S1-8，未来）
"""
