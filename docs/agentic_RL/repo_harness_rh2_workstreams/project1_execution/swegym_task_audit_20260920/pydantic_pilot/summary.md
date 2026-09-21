# Pydantic 首包复核（8 题，2026-09-20）

建议先探针 **5662、6283、8511、9134**；5386、5706、6043、8500 先准备具体修订。这里只给调查优先级，不是正式准入或剔除决定。

逐题读取了实际公开题面、test_patch、gold 和精确 base 源码，没有把 gold 当唯一合法解。环境以 20260919 的 `pydantic_v1 / pydantic-install-v1` 为准：8 题均有 noop=0 / gold=1，安装 rc=0、gold 测试 rc=0；本轮复算 16 份原日志 SHA256 均匹配。该结果证明选定 grader 配方有效，仍不等于 actor 已冻结消费或题目质量认证。

| 题 | 建议 | 本轮主要判断 | 最小下一步 |
| --- | --- | --- | --- |
| [5386](records/pydantic__pydantic-5386.json) | needs_revision | 原需求可理解，但新增 hook 名称与协议不在公开材料中；F2P 也不读取字段。 | 只澄清公开接口契约，再检查回调内字段可用；不披露 metaclass 实现。 |
| [5662](records/pydantic__pydantic-5662.json) | probe_candidate | 题面与比较协议一致，且自带方案；旧“递归坏解能全过”被现有 dict P2P 挡住。 | 低难度锚点；附自定义比较对象与 NotImplemented 对照。 |
| [5706](records/pydantic__pydantic-5706.json) | needs_revision | 已有候选 JSON 通过但破坏 range/tuple/deque；题面 JSON 成功/统一拒绝方向也有分歧。 | 澄清外部行为方向，复用 src_only 候选验证最小 Python 回归集。 |
| [6043](records/pydantic__pydantic-6043.json) | needs_revision | 撤回“散文无验收标准所以 reject”的推断；递归需求成立，已证顶层排序假修复漏检。 | 嵌套键序及 generate_definitions 诊断，保留有序数组语义。 |
| [6283](records/pydantic__pydantic-6283.json) | probe_candidate | 构造等价目标清楚；PrivateAttr+construct 组合未覆盖，但暂无已证满分坏解。 | 普通探针附私有属性默认值/相等诊断。 |
| [8500](records/pydantic__pydantic-8500.json) | needs_revision | 原需求清楚；gold/候选都漏掉构造后赋值原例，另有字母序假修复通过。 | 原例键序、非字母序及缺失必填/fields_set 护栏一起验证。 |
| [8511](records/pydantic__pydantic-8511.json) | probe_candidate | repr 是既有公开契约；旧 compare/hash/metadata 透传建议扩大了题目范围。 | 普通兼容性探针，保留 default_factory 与 stdlib 对照。 |
| [9134](records/pydantic__pydantic-9134.json) | probe_candidate | 需求和 F2P 对应；旧称多层与父子私有属性无覆盖不准确，P2P 已有相关回归。 | 普通继承缺陷探针；按候选行为决定是否补工厂调用次数诊断。 |

可复用的早期探针是 4 题，不需要先重写它们的题面或任意扩大到全仓测试。5662 单独标记 `solution_in_statement`，用作低难度和工具链锚点；其余 3 题观察正常定位、修改与验证过程。启动前确认修复配方确实进入 actor、解释器正确且保存初始工作区；这里没有替新探针做过该核验。

本轮对旧结论的主要纠正：

- **5662：** `test_model_equality_dump` 本就在 P2P 中；实际 `__eq__` 的本地协议替身证明 `return other == self` 对 dict 递归，不能声称这条坏解全绿。
- **6043：** “没有例子”不等于缺少可执行要求；题面已有递归排序目标。`prefixItems` 按位置表示 tuple 元素，不能把“不排序所有列表”直接判成漏实现一半要求。
- **5706：** 范围回归是业务代码造成的真实错误，不是改官方测试导致通过；generator 文档与基线测试还存在矛盾，优先采用 range/tuple/deque 反例。旧 M2 的字符串组在 Python 3.8 三态均 skip，不能沿用为该轮错误文本实测。
- **8500：** 原例明确包含构造后赋值，不能用“题面未区分”免责，也不宜静默把题面缩成构造期。历史上游源码/测试访问已证，但核心思路早于曝光，不能说全部工作来自复制。
- **8511 / 9134：** 前者的旧建议引入未承诺的新参数；后者已经有 7091、7293、MRO 等 P2P 护栏。两者均不因这些旧论据延后早期探针。
- **跨题关系：** 不按同文件自动建泄漏簇。5386→5662、8004→9134、6283→8500 有具体源码包含事实；模型是否实际接触、应如何划分仍需按数据和轨迹暴露判断。

证据层级与核验：

- [verification.json](verification.json) 保存 16 份环境日志校验、6043/8500 的 6 份 L7 原日志完整参考 ID 重解析、5706/8500 的旧诊断原日志及 3 组本地探针。
- L7 的 6043/8500：旧独立脚本中 noop/base 不满分，gold/fake 分别全部 304/45 个参考 ID 通过。本轮补了 fake 违反递归/声明顺序的纯 Python 反例，**没有把这些写成最新 RH2 满分复现**。
- 5706：旧独立脚本 base/gold 的 Sequence 组各 16 passed，candidate 6 failed/10 passed；8500：gold/candidate 原例诊断各 2 failed/8 passed。原 DeepSeek 轨迹也提供独立的行为观察。
- [verify_pilot.py](verify_pilot.py) 可从仓库根运行；只读共享 clone 的 `git show`，不切换工作树。第一次核验因失败行附进度尾缀漏读，已定位并修正本审计解析器，最终完整核验通过。

边界：本轮未启动 Docker、远端、模型或真实 RH2；没有修改正式题面、测试、生产代码、总入口或他人目录，没有提交。三组本地探针分别使用实际比较方法、实际排序片段和带字段替身的实际构造方法；构造探针没有模拟 serializer，完整序列化结论引用旧真实容器日志。
