# iterative__dvc-4166

**优先保留为受限静态候选**，状态 `needs_review / static_review`，仅供 `development_diagnostic`。base `520e01f11305`；目标是修复 `.dvcignore` 的目录规则与否定匹配。封存分析及历史差异见同目录文件，独立[复核](review.md)已完成。

| 需求/旧行为 | 依据与断言 | 覆盖及证据 |
|---|---|---|
| 尾 `/` 的目录规则 | 公开 `!/scripts/` 等；F2P `test_ignore_file_in_parent_path[data_struct2-pattern_list2-result_set2]` 断言 `subdir/` 排除父目录后文件集合为空 | repaired gold 通过、noop 失败；未直接复现七组公开写法。 |
| 目录与同名普通文件应有区别 | 公开目录模式、历史本题 raw hints 的 file/dir 对照 | 缺普通文件对照；`test_ignore_directory` 只查空目录的文件集合，不能证明目录已排除。 |
| 原有规则与遍历 | 全部 41 个匹配参数、默认目录过滤及功能 P2P | 实际 63 案例、解析 62、参考 59（F2P 1/P2P 58）。两条前导空格节点合并为一个截断键。 |

复核纠正：parent参数0的根规则 `subdir/*` 不匹配实际 `dir/subdir/not_ignore`；该用例仅证明文件可见，不能证明先排除再重新包含。封存分析保留原文，最终判断以此修正为准。

八方面已查：公开目标与 base；全部修改断言/fixture/Mock；合理替代与一个自然部分实现假设；gold、WorkingTree/GitTree/CleanTree 调用者与相关回归；具体依赖/本地 Git/权限需求；两文件官方恢复和本次候选投影；有限祖先关系；材料暴露。未跑替代解、扩展回归或真实 actor；未检验实际镜像泄漏、重复稳定性和完整跨题关系。

当前 parser `swegym_parsers.py:44–55,93` 确实按空白截断并逐行覆盖；当前日志两项均 PASS，不能宣称已发生错误 reward，旧“patterns5 永远失效”表述过强。旧 Stage1 三项依赖失败及安装中途错误已找到原件；当前配方固定 pathspec 0.8.1、networkx 2.3+rh2.1，三项恢复通过。两次安装 RC 0，gold 63 PASS、noop 62 PASS/1 FAIL，属于 rh2grader/54322，actor/54321 的消息、依赖、权限与导入仍未知。

唯一优先行为实验建议：固定配方，比较 base/gold/“仅去掉正向规则尾 `/`”候选的官方结果与文件/目录成对矩阵，核验其是否错误排除普通文件。尚未执行；不改题目、测试或 reward，`additional_exclusions=[]`。正常祖先含 #4066 修复不足以直接判重复或强制同侧。私有 gold、测试、raw hints 与历史已暴露给主审，不回流公开角色。

关键原件：`R/{gold,noop}/ledger.jsonl:1`（R 见封存稿）；当前日志 SHA 分别 `6a9ef505…f06ab7a`、`7689ee1d…99affd7`。完整 SHA/行号与历史对照保存在分析和 delta；封存稿 SHA `cd9e2abcd3d44083df019a88124f095fcb2c0ac8d1a0febce6bb0a37e2db54ce`。
