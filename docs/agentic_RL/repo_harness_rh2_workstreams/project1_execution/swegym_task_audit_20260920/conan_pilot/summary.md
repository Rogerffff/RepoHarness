# Conan 首包逐题复核（2026-09-20）

完成 8 题的真实题面、test_patch、精确 base 相关实现与测试、旧结论及当前环境证据核对。下面是本轮调查建议，不是正式训练准入或剔题决定。

| 题号 | 本轮建议 | 主要依据与下一步 |
| --- | --- | --- |
| [11560](records/conan-io__conan-11560.json) | needs_counterexample | 保序注释有功能；先验证只改指令大小写的等价解被拒，再对照真正的链接行为。不能直接认定 gold 无效或 alwayslink 等价。 |
| [11594](records/conan-io__conan-11594.json) | probe_candidate，优先 | 题面明确；reference_v1 已绑定两个完整 Ninja nodeid。检查候选是否仍保留 Multi-Config 的 `--config`，防止通过误改全局分类来凑目标名。 |
| [12397](records/conan-io__conan-12397.json) | probe_candidate，补充 | 题面和共用 `_context` 可推导修复；官方只测 Apple cross，补 Linux native Clang 的生成物检查，防 Apple-only 假修复。 |
| [13230](records/conan-io__conan-13230.json) | probe_candidate，优先 | 核心是非 Apple host 的 flags 泄漏；基线本来已读 host settings。补题面 Linux/gcc 路径与最终 flags 检查。 |
| [13403](records/conan-io__conan-13403.json) | needs_counterexample | Mock 确实固定调用形状，并未证明进入目录；验证等价 keyword 调用被拒、只创建 context 而不进入是否被放过。 |
| [13721](records/conan-io__conan-13721.json) | probe_candidate，补充 | 实际文件名与 include 上下文可从仓库推导；保留扩展名并非毫无依据。补题面真正需要的 symlink 共用模板行为。 |
| [14177](records/conan-io__conan-14177.json) | needs_revision | 题面显式 `verbose=False`、True 时输出，测试却要求默认输出并改变直接 `patch()` 的类型标签；这是行为契约冲突。 |
| [15422](records/conan-io__conan-15422.json) | probe_candidate，优先 | `build_jobs` 是现有约定；不因 CPU 默认值变化重复资源实验。补无 conf 的默认并行度与第二配置值，防仅处理显式 jobs。 |

本包最值得保留的校准：

- **11560 的旧关键前提需撤回。** Buildifier 5.1.0 的 `doNotSort` 按大小写不敏感方式识别指令，首项注释可阻止列表排序。基线又已保留 `cpp_info.libs` 次序，因此“注释无功能、gold 必然无效”没有成立。4 个 F2P 仍都要求小写文字，但只有 2 个严格钉空白；另外两个分别使用正则及删除空白后的比较。[官方固定源码](https://github.com/bazelbuild/buildtools/blob/c802c3b06ba674e8a76d04c0677d153ab9f660c9/build/rewrite.go#L109)
- **不能直接把 alwayslink 当等价修复。** 它会纳入静态归档的全部对象，和保持依赖顺序并非同一语义。真实 libcurl/OpenSSL 失败、是否经过 Buildifier，均未在本轮运行复现。最小格式反例可先改为 `# DO NOT SORT`，其正式 F2P/Bazel/Buildifier 对照尚未运行。[Bazel 5.3.0 定义](https://github.com/bazelbuild/bazel/blob/5.3.0/src/main/java/com/google/devtools/build/lib/rules/cpp/CcImportRule.java#L88)
- **13403 的“回归保护为零”不成立。** P2P 虽为空，同一个 F2P 仍保留 `configure` 断言，并检查默认 `autoreconf` 的目录及参数。真正问题是 Mock 的调用形状和实际 cwd 脱节；旧文提出 `abspath` 会失败也不成立，测试输入已经是规范绝对路径。
- **13230 不能把标题当另一个隐藏需求。** 可见代码已用 host settings 选择 flags/compiler；错误集中在只检查 build OS 的 Apple 分支。F2P 的 min_version 空串断言在 base 对该输入也成立，不能据三条断言声称三个新修复出口都得到验证。
- **缺题面原句不等于缺规格。** 13721 的文件名和逐 profile 渲染、15422 的并行度来源都有基线约定；仍分别保留 symlink 和默认 jobs 覆盖缺口。14177 则存在明确的 opt-in/default 冲突，不能用“通常沿仓库习惯”抹去。

环境与证据边界：11594 使用 [repair_catalog](../../env_recipe_repair_20260919/repair_catalog.json) 选定的 `reference_v1`，其余 7 题均在 `runs/env_recipe_repair_20260919/scope_reconciliation_20260920.json#outside_repair_ids`，属于已验原始对照，不是未知或未修。已核对 16 份所引日志 SHA256：各题 noop reward=0/test rc=1，gold reward=1/test rc=0；这些证据分别来自原始基线与修订实验配方，不能拼成新的统一训练资格。

题目质量结论是静态复核；所有新增正确/错误候选及行为诊断都明确标为未运行。没有运行 Docker、远端、模型或重复安装/资源实验，没有修改正式代码、题面、测试或参考集。旧 `conftest_user.py` 控制面线索在每题保留为 unresolved，沿统一评分安全边界调查，未借此给题目机械降级；已遵照 [09-16 独立核查](../../env_overnight_20260916/CODEX_REVIEW_20260916.md) 区分历史归因与已证事实。
