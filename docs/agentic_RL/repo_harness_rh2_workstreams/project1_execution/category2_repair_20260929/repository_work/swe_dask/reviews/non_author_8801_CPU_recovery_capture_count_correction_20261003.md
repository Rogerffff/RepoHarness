# 8801 CPU恢复审查marker统计更正（首次追加，2026-10-03）

仅更正[原JSON报告](non_author_8801_original_fp_CPU_environment_recovery_review_20261003.json)的`behavior_results.captured_raw_marker_counts.compatibility_packets`：**应为10，原记0错误**。审查者用了不存在的`RH2_DASK8801_COMPAT_V1`查询前缀；[固定protocol L13](../tools/config_diagnostic_protocol.py#L13)实际为`RH2_DASK8801_FALSY_COMPAT_V1:`。按正确前缀独立复算原完整日志，匹配10行；完整计数为23 diagnostic、10 compatibility、1 raw import exception。

原JSON SHA `0748ccd3c1a7e5a388b4851cf994a5a7942c588c9dbe51d2b69e62d71191aff1`与MD SHA `121e056e003e02a9d6a3d30207df81991f44c8098d99dd56a75d7f756ece0485`保持，不回写。41原件/45参考全通过、actual image/UID/code8/scripts、资源及清理验收结论均不改变。此处只纠正附加运输统计，不执行capture/judge，不产生fresh语义裁决或训练资格。

完整日志SHA `00a7add8d1be082684d8ad9dffab1cdadb86bd3d50a428cf9cbb61d684897968`；protocol SHA `7886a70ac59d051eca4459c6e32d94b77159c6890341183041dc73df03d1292a`。对应行号见同名JSON。有效审查应同时读取主报告与本更正。
