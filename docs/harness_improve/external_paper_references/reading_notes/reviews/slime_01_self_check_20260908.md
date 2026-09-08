# slime 专题01：作者自查与局部语义检查

日期：**2026-09-08**。正文：[slime_01_architecture_and_recent_changes.md](../slime_01_architecture_and_recent_changes.md)。

**状态：按正文覆盖表完成首轮源码静态精读、局部Python语义检查和作者自查。没有独立审查，没有运行slime测试套件、GPU或SWE环境。** 本次从用户最新要求出发，增加独立代码专题，不把R5c预读改成博客全文完成，也不追求把两份短发布文章扩成不存在的完整训练配方。

## 1. 固定来源与边界

主代码为`THUDM/slime@4c193f1f37509cca70f0e88807a9305b70f63f4e`，2026-09-03。最新非预发布release是2026-08-28的`v0.3.2`，tag指向`3778dbf6d1a533ab478ecf5ddaa11449a47752b2`；当前main另外包含9月3日的streaming和adapter取消修复。GLM README固定`zai-org/GLM-5@008de4dbcc220032eb9b80a9a9802afad46a4053`。项目读取基线`ac0e2e64163fbe49411540e901df439aea16b6b0`；实际写入以提交前最新head为准。

已完整读取两份driver、RolloutManager主要方法、DataSource、fully-async worker、coding-agent generate、weight-updater factory、streaming generator与reproducibility文档。Sample前250行、默认rollout的250–510行、customization前260行以及GLM六层gate前部按范围记录。README主要相关段落、#2340完整diff、#2272说明与关键diff已读；没有将这些局部范围写成整库逐文件审计。

当前代码不是2026年6月或8月模型训练的已验证原始revision。release自述在GLM-5.3上的采用，与当前公开fixture和我们实际运行的检查分开保存。

两份z.ai博客本轮再次访问仍未取得可读正文；直连存在DNS问题。搜索结果中的第三方模型卡镜像未用于补写官方训练细节。官方GLM README可确认base关系，但不能代替博客正文或Flash的完整后训练方法。没有分析PDF，没有读到的图表不补数。

## 2. 局部Python检查与实际修正

检查不导入slime，使用轻量对象模拟`Sample`，只复制被审路径中的两个谓词。读者可独立运行：

```python
from types import SimpleNamespace

aborted = object()
flat = [SimpleNamespace(status=aborted, index=17)]
nested = [flat]

def has_abort(result):
    return any(getattr(s, "status", None) is aborted for s in result)

def sort_key(group):
    for s in group:
        idx = getattr(s, "index", None)
        if idx is not None:
            return int(idx)
    return 0

assert has_abort(flat)
assert not has_abort(nested)
assert sort_key(flat) == 17
try:
    sort_key(nested)
except TypeError:
    pass  # list.index is a bound method, not a sample number.
else:
    raise AssertionError("Expected int(list.index) to raise TypeError")

rewards = [1.0, 0.0, 0.0, 0.0, 0.0]
whole = [x - sum(rewards) / len(rewards) for x in rewards]
grouped = [x - sum(g) / len(g) for g in (rewards[:2], rewards[2:]) for x in g]
assert whole != grouped
print(whole, grouped)
```

本轮实际脚本使用dataclass/Enum表达同一条件，输出：平坦ABORTED为true、嵌套为false；平坦sort key为17，嵌套抛`TypeError: ... not 'builtin_function_or_method'`。中心化结果分别为`[0.8,-0.2,-0.2,-0.2,-0.2]`与`[0.5,-0.5,0,0,0]`。

**一处实际自查修正：**最初静态判断以为嵌套成员缺少index会走回退值；运行上述检查发现Python list本身存在index方法，因此会在`int(idx)`处抛错，正文已更正。这个发现提高了局部解释的准确性，不代表执行过整条训练链。

路径依据是：`generate_and_rm_group`的gather保留每次custom_generate的返回形状；coding-agent返回list[Sample]；fully-async callback/sort则按扁平成员读status/index。因此此处不是任意制造了无关输入。但custom wrapper、不同generator或其他revision可能改变条件，本文不宣称所有fully-async训练均失败。

## 3. 承重结论的自查

| 结论 | 检查与限定 |
| --- | --- |
| 默认driver、预取driver、持续worker是不同组合 | 从实际await/update顺序解释；collector返回不代表整个后台池排空 |
| 仍有同题组等待 | group内部gather与外层组完成队列分开；不把fully-async描述成SAO |
| 输出队列backpressure | 无界Queue避免阻塞event loop；补任务条件限制不是硬队列长度上界 |
| hooks是否生效 | 默认外层filter/process与group内sample/RM分开；CLI存在不证明替换外层后仍调用 |
| GRPO统计与rollout计数 | 检查先flatten/reward处理，再按rollout_id构造分母；不将ID机制当成组归一化修复 |
| remove_sample | mask清零发生在reward处理之后；不等于移出其他成员的baseline |
| SWE退出 | CLI非零仍可评diff；outer失败使用ABORTED占位；不统称模型失败 |
| streaming恢复 | 已收到的token可保留；terminal-only top-p/routing不能推定已存在 |
| #2340取消 | 发送到router workers的修复成立，但没有确认全部请求已经idle的屏障 |
| GLM数值路径 | 六层EP8专用gate、依赖与skip条件明确；参考x e-7不是所有模型/每token最大误差保证 |
| 最近release条目 | #2234明确是日志配对；未读diff的其他条目不升级成已审实现 |
| 权重更新 | 只核factory与updatable-server选择；不宣布原子发布或完整故障恢复 |
| DataSource.save | 游标状态与内存buffer、在途task、完成队列分开；未跑进程重启 |
| 真实harness token保真 | 本卷记README合同与generator入口，TrajectoryManager和最终loss保留给下一卷 |

## 4. 尚未核验及下一次最有价值的范围

尚未完整追DP调度器、per-rollout reducer、top-p实际概率消费者、teacher scoring、TrajectoryManager共享前缀、GLM alignment算子、各weight updater和恢复全链。也未逐行检查streaming新增测试或独立取得作者E2E原始日志。没有用本轮静态问题推断2025/2026旗舰训练受影响，更没有推断RepoHarness当前miles pin必然存在相同问题。

下一卷应优先检查token轨迹与训练单位：请求入口→原始token捕获→分段/分叉→reward与rollout_id→DP分片→实际loss分母。它应服务同一批样本的语义核验，而不是增加新的IR或通用治理层。

## 5. 文件自查与并行写入

检查引用式链接定义、导航anchor、相对链接、行尾空格和替换字符；执行局部Python检查并保存本地输出。只提交正文和本检查记录两个专属路径，不编辑共享README/catalog、R5b/R5c、其他并行成品或训练实现。写入前重新读取最新tree，非force快进；提交后回读和差异核查以实际工具结果为准。没有预填未来成功SHA，没有编造独立reviewer或线程元数据。
