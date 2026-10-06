# Project-MONAI__MONAI-2446

静态候选，保留 `needs_review`；用途为 development_diagnostic，独立review待完成。base `05b2da61d703…`。目标是 shuffle=True 时保留调用方列表顺序，同时内部继续打乱；gold在首次shuffle前浅复制外层容器，符合列表目标。

| 要求/旧行为 | 依据与决定性验收 | 判断 |
|---|---|---|
| 外部列表不变 | 题面五数组复现；F2P test_datalist/allclose | noop失败、gold通过 |
| 内部继续shuffle | 公开P2P test_shuffle：三轮dataset[15]为18/13/5号 | 双方通过；可阻止简单取消shuffle |
| 保留缓存替换 | P2P test_update_cache比较保留段与替换段 | 双方通过；有限种子/规模 |

八方面已查：公开目标与双向映射；base/历史grader初态；全部1个F2P、2个P2P和新增helper依赖；非gold复制路线及误拒边界；gold与SmartCacheHandler调用者；依赖/临时影像/线程需求；源码投影与可信测试恢复；用途与暴露。没有运行替代解或穷举Sequence回归。

历史compat-v1已预置并安装nibabel4.0.2，原日志中noop七pass+目标一fail、gold八pass，五个shape都实际执行通过。旧报告的“仍有五个环境失败”不适用于此grader；旧文误述test_shuffle为dataset[0]比较，已纠正。它们仍非expected P2P，是否纳入是另一个评分设计问题。未证gold新增回归。

实际actor消息、HEAD/准备后status与来源差异、忽略资产、解释器、UID/HOME/PATH/权限及资源均unknown；修复后grader不等于actor合格。投影仅dataset.py，测试恢复成功，未全面审计对抗控制面。审查者见过gold、隐藏测试及本题旧记录，材料不得给独立solver；旧6975关联未跨题核实。

唯一优先下一步：核对实际actor初态与解释器/本地MONAI来源及兼容底座是否交付。无需为静态已清楚的shuffle断言重复安排CPU。完整证据、范围和运行定位见同目录analysis_before_history.md；历史纠正见old_findings_delta.md。
