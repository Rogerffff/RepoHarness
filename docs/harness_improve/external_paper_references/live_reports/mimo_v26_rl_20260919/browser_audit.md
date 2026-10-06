# Computer-use 图像巡检记录 · 2026-09-19

使用已有 MiMo 直播浏览器标签页；原始 UI 截图保留在本任务工具记录中。目录内 figures 是根据冻结公开数值重绘的科研对照图，**不是网页原始截图文件**。

## 实际查看

| 页面/操作 | 检查目的与所见 |
| --- | --- |
| overview 顶部 | 公告、Pro s23 live / s24 进行中、Flash s30 stopped、费用、batch、训练 token |
| overview 三项 benchmark | 完整无平滑折线；新增 In-house / Automation；评测 checkpoint 落后训练 |
| overview 学习指标 | avg@n、训练 reward、entropy、pg_loss、grad norm、train/infer KL；Flash s30 联动变化 |
| overview 负载与时间 | context、turns、训练 tokens、step/outer_gen/trainer_ops；后期负载增长 |
| overview 采样指标 | zero/one 成功组、infra error；采样统计与训练 reward 的区分 |
| metrics 全部目录 | 2,077 tags、14 大类；以完整公开序列归档补足逐图浏览的覆盖边界 |
| metrics signed penalty | 8 张子图；Flash s30 负侧命中与 mass 突出跳变；scale 方向变化 |
| metrics lag 0/1/2 frac 与 KL | 六图联看；Pro s23 新鲜桶权重上升，而各桶 KL 反向变化 |
| metrics stage_credit_group | mean/max latency、end2end_success、hack_attempt、regression、renorm cap；均值与长尾分开看 |
| metrics response/context | 全局 mean/max、code/yfch、cyber、clip ratio；cyber Pro 曲线止于 s14、卡片继续显示末值 |
| metrics env/verdicts | active、total_setup、carried、expired、rejected、trained；固定 25,088 与变动样本流转 |
| overview composition → harness (trained) | Pro 表格显示 s23、harness-R=1,022；与冻结序列 s15 后缺失不一致，进一步核对前端 lastOf |
| overview composition → data source | Pro cyber=0；Pro s23 ≈1,568 的比例近似说明；来源分布已经变化 |
| about | 没有新增正式算法解释 |
| 返回 overview | 13:30 UTC+8 仍 Pro s23 / Flash s30；Pro s24 training，保留标签页供后续讨论 |

## 关键过滤器（可在 metrics 搜索框复现）

```text
/^(ctx_response_length[/](mean|max|code[/]dataset-yfch[/]mean|cyber[/]dataset-9aui[/]mean)|ctx_total_length[/](mean|clip_ratio))$/
/^(env[/](active|total_setup)|train[/]verdicts[/](carried|rejected|expired|trained))$/
/^penalty[/]stage_credit_group[/](time_total_sec_mean|time_total_sec_max|end2end_success_rate|select_hack_attempt_rate|select_regression_flagged|select_renorm_capped_rate)$/
```

metrics 使用 step 横轴、linear、smoothing off。原始页面实时费用/队列会持续更新，报告金额固定取 05:11 UTC 数据快照；未将不同时间的 live 数值混入完成 step 的分析。

## 覆盖限制

不是逐张截图审查所有 2,077 个 tag。对全部字段做数值归档、历史值比较和缺失检查；图像审查集中在整体曲线、最大结构变化与交叉验证。没有进入训练集群、查看私有轨迹或验证未公开算法，也没有把网页统计当成独立实验复现。
