# dask__dask-8801

**needs_review / static_review；优先 CPU 语义对照。** base `9634da11a5a6`。公开报告指向坏配置使 import 在合并中发生 `str.items()`，可调查，但缺实际坏文件，也未唯一规定报错/跳过政策。

| 需求／旧行为 | 验收与缺口 |
| --- | --- |
| 顶层非映射可定位诊断 | F2P 只给列表；原字符串及 import 链未测 |
| 坏 YAML 诊断 | F2P 额外锁 ValueError、repr 路径及三个英文片段，无唯一公开依据 |
| 正常配置／权限忽略 | 41 P2P 通过；另两项权限测试实际 PASS，却不计分 |

八方面已查公开题面/源码、精确材料与初态、全部新增断言及 P2P、替代实现、gold、开发需求、投影评分、用途暴露；实际 actor/消息、全仓和跨题关系未验。独立复核已完成。

baseline 账本 w01-2 第9–10行：noop 两 F2P 失败；gold 45 passed、reward1；两侧 41 P2P PASS。pytest8.3.2 正常，无需套用8597配方；grader54322不是 actor 验收。gold 能在文件边界拒绝字符串，无已证原例漏修；空输入合并效果保留，但 collect_yaml 返回及 falsy 顶层政策有变化。

同义措辞有历史局部误拒记录，**完整 RH2 候选未验**；只拒 list 的部分修复也仅为静态漏测候选。唯一优先实验先保留 path!r、异常类型、原因和逻辑，只改英文措辞；随后可做 lists-only 负对照。文件与目录权限分支分别记，fresh import 隔离全部配置搜索目录。

原题/测试/参考未改，额外排除为空。详证据见 `analysis_before_history.md`、`old_findings_delta.md`、`review.md`。仅限 development_diagnostic；已见 gold/隐藏材料的产物不得给 solver。
