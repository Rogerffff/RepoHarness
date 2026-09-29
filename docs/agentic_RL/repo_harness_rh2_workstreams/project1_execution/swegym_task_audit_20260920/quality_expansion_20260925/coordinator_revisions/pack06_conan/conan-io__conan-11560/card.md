# conan-io__conan-11560

目标是让 Bazel 多静态库包可链接；base 为 `345be91a038e`。gold 只加尾逗号与 `# do not sort`，没有题面提出的 alwayslink。四个 F2P 都要求小写注释，其中两项还钉空白；另两项容忍空白。历史 noop 4失败/3通过，gold 7通过，安装末命令 RC0、测试 RC1→0。分差确认的是生成文本，未运行 Bazel、Buildifier 或双静态库链接。

| 需求/旧行为 | 决定性验收 | 判断 |
|---|---|---|
| 题面 cc_import alwayslink、多库链接 | 四F2P均无此属性/真实链接断言 | 规格错位与漏测 |
| 包级依赖/传递引用 | 精确小写注释与单库依赖 | 注释约束可误拒按题面实现 |
| 头文件/主BUILD/build依赖 | 三P2P均读且两端通过 | 局部旧行为保护 |

八方面均见封存分析：完整模板、全部断言/fixture、组件聚合与关联生成调用、合理替代解和 gold、开发需求、交付恢复、身份和暴露边界。gold 的实际链接正确性未知；不能把三P2P通过写成无回归。旧 pilot 为 Buildifier 功能指令提供外部引用，本轮只读该历史主张，未核外部原件；不沿用“注释必然无效”。格式或行为等价性也未运行证明。

当前 actor 消息/工作树/权限/资产/PATH unknown，actual image ID=null。历史仅证明所列 grader 窄命令可执行；最小生成可用假库文件，真实链接还需工具及有效档案。只改非测试生成器可合法交付；conftest_user 导入是静态边界线索，是否穿过当前投影/恢复未知，不加排除规则。

建议用途仅development_diagnostic，状态needs_review/static_review。唯一优先下一步：先由题目维护方裁定公开契约：保留 alwayslink，或为防排序方案提供公开依据；据此设计行为验收，当前不优先机械 CPU/模型/全仓运行。

完整双向表、全部阅读范围与原命令/逐ID状态见 [封存分析](analysis_before_history.md)，历史逐项复核见 [delta](old_findings_delta.md)。reviewer未读，未作一致性结论；未知token/费用为null，无新增排除/修订。
