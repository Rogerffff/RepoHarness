# S1 最终汇总复核记录（2026-07-08）

复核方式说明：独立复核 agent 执行中途被用户停止（其最后动作是认为秘密扫描的管道 exit code 不可靠、准备重跑），未产出报告。剩余复核项由 orchestrator 以更可靠的方式（无管道、直接计数）补齐完成。此前 orchestrator 已在每任务完成时做过独立复核（各 commit message 有记录）。

## 重跑与抽查结果（全部通过）

```text
1. 全套测试            605 passed（orchestrator 独立重跑）
2. docker 真容器套      15 passed 实跑
3. inspect-rh2-s1      exit 0：21 evidence + 51 code digest 全命中，
                       白名单/结构化对照/A10 探针/frozen_v1 重算/marker 扫描全过
4. 契约测试重跑         inspect-rh2-s1 --run-contract-tests：303 全绿（S1-9 agent 实跑）
5. parity 脚本         core/cross/dump 三项 true（S1-9 后复跑确认未破）
6. 秘密扫描            key 形态命中 0 文件（s1 evidence + rh2 src/experiments，
                       无管道直接计数）；deepseek_api.md 仍未被 git 追踪
7. 高危面 a（blockers 无淡化）  s2_blockers.md 与 implementation-notes 均含
                       "分叉感知重建"升级路径；summary.blockers=1 且被 inspector 结构化锁定
8. 高危面 b（H-1 只记录不准入）  weight_versions/staleness 相关 22 测试全绿
9. 高危面 c（工作树边界）  除另一线程的实验设计评审文档（不入本 commit）外无越界修改
```

## 判定

**通过。** `rh2_s1_closed_loop = true` 随本 commit 落账；AGENTS.md 保留
"pending checkpoint-2 confirmation" 注记，待用户检查点 2 确认后由一个
单行 commit 摘除——闸门的最终确认权在项目所有者。

递延与阻塞（均已在 s1_acceptance_summary.json 结构化登记）：30B 全要素
训练 step / U-C 多卡训练侧 → S4 前 8 卡预实验（preflight 协议 P3）；
S1-8 导出器分叉感知重建 → S2 显式阻塞项（E3 warm-start 回退的前置依赖）。

**[P3 收口 2026-07-09 回填]**：上面第一组递延项已由 P3 八卡预实验关闭
——30B 全要素训练 step（J4 replay + J5 gbs20 真实训练 step + 权重同步）、
U-C 训练侧四项（Megatron on sm_120 / PCIe all-to-all / CPU offload 实测绿；
colocate 显存水位以 T3 分离放置定案的方式关闭）、routing tape 训练侧
消费（首次真实进 loss）。acceptance summary 中对应三条已改判
`closed_by_p3_20260708`；判定依据与实测数值见
`../preflight/preflight_report.md`。S1-8 导出器阻塞项不受 P3 影响，
仍留 S2。P3 新增的独立验收项（治理过滤后 batch schedule alignment）
登记在 preflight 协议 J4 判据第 0 项，不改本判定。
