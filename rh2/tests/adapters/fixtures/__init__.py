"""S1-3 手工构造的 slime 产物 fixture（离线驱动 project_from_slime，不需要 GPU）。

- moe_30b_compaction.py  30B MoE 风格：带 routing + top-p tape，一 session 两叶链
  （compaction 分叉 → branches=2），数值参照 s1/uh_probe_result.json 的形状语义。
- dense_4b.py            4B dense 风格：无 routing（not_applicable），top_p=0.95
  照带 top-p tape（A2：dense 只是没有 routing，S1-7a 同款形态）。
"""
