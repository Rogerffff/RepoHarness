# Pydantic8793：正式误奖关键事实独立复核

2026-09-29。结论：`forced_required` 的正式 reward=1 是有效完成原参考得到的结果，但候选破坏真实默认值，并被两个既有公开测试检出。本次证据支持“当前正式参考漏检该退化”，不支持将其视为正确修复或授予题目无条件训练／比较资格。

本稿是跨包独立核验：审查者未编写该题输入或主审结果。先读取本批 ledger、eval 原日志、私有 captures/spec、候选补丁与 cleanup，再查看题主 plan；后者此时仍是原 actor 阶段记录。本次复用既有上下文，不称全套新盲审或 OS 隔离验收；未运行远端、容器或项目。

## 直接事实

证据根目录：`runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-8793/calibration_v1/`。

| 候选 | 正式参考 F2P / P2P | reward | 原公开必填行为 | 公开真实默认控制 | 旧公开测试 |
| --- | --- | --- | --- | --- | --- |
| noop / private base | 0/3；364项无失败 | 0 | schema/字段必填/缺值验证三项精确失败 | 通过 | 72 passed、1 skipped |
| gold | 3/3；364项无失败 | 1 | 全部通过 | 通过 | 72 passed、1 skipped |
| forced_required | 3/3；364项无失败 | 1 | 全部通过 | `Defaults.x` missing ValidationError | 2 failed、70 passed、1 skipped |

正式三次 ledger 的 stage_error 均为空；安装完成、install_failed_commands 空、test segment 完整；参考缺席0、apply_ok=true、runner digest 前后相同、cleanup removed=true。正式 eval 原件确实执行 `tests/test_json_schema.py`：noop 为3 failed/377 passed，gold 与 forced_required 均380 passed，三者另有1 skipped/1 xfailed。上述总执行数与正式参考数分母不同，不互换。原日志存在 test 终止 marker 与对应rc，误奖不能归因于没跑测试或 patch 未应用。

`forced_required/artifacts/.../candidate.patch` 与输入 `private_degenerate_force_required.patch` 字节相同，SHA256 `248e5947705576b7b12499d96bb2ad327a09c1edb3561e72af19b4b125e6185f`。它仅在 `pydantic/fields.py` 的 overrides 循环中把所有 `default` 改为 `PydanticUndefined`，没有修改测试、评分或安装。正式与私有对照使用的是同一候选逻辑。

私有 `public_defaults.out` 的失败不是普通非零：`create_model('Defaults', x=(Annotated[int, Field(description='x')], 5))` 后，`M()` 精确报 x 为 missing。base 和 gold 均输出 `PUBLIC_DEFAULTS_OK`。该命令先计算 `M().x==5`，因此 forced_required 在这里短路，**不能据此声称同一命令已单独验证其 default_factory 是否也被破坏**。

另外，私有 `public_existing_tests.out` 在 `tests/test_annotated.py:90` 的两个已有参数例中，从预期 `required=False, default=5` 变成 `required=True`，是具体行为回归，非导入／收集失败。其失败文件不在本次正式选择的 `test_json_schema.py` 中，直接解释了这个候选为何能获1分。

私有 boundary 是观察项而非成败断言：base 输出 `Ellipsis, False`，gold 输出 `3, False`，forced_required 输出 `PydanticUndefined, True` 并捕获 missing ValidationError。该命令自身rc0只说明观察执行，不应记成 forced_required 通过边界要求。

## 身份、清理与用途限制

私有 summary 的实际 base image 为 `sha256:e61eaef6ac2759d2f5e96f20126a3ac51121f2e17de7d43238f8237770382162`；三个变体准备命令和四条行为命令均完成，逐容器rm/query为0、remaining为空。正式三次使用同一 wheelhouse 派生镜像 `sha256:039bc9c34cdf14c690f6ec0c955fee93bdaed598eda3253dd76b895b173f671e`，源码导入均 `/testbed/pydantic/__init__.py`，版本2.7.0a1；安装日志确有本地 editable 构建/安装完成。两个环境身份不同但用途明确：私有行为为root诊断，正式为原评分流程，不能用私有权限代替actor验证。

这使本题可作为“正式参考漏检默认值退化”的已实证诊断样本。应保留错误候选和公开控制，交由既定题目筛选规则决定用途；本稿不改原题、评分或正式测试。完整题面/public_hints真实交付、镜像初始pdm.lock/pyproject.toml差异和单skip归因等既有边界仍由题主处理，本次不将它们静默改成已完成。

## 原件摘要索引

- `noop/ledger.jsonl`：`8fb75b7d40b1c894d7421b99d9e10fe6ef0c39d80ae96e73de8238fde9694c39`。
- `gold/ledger.jsonl`：`d32d35b4c6c95fac493ee6622ed5db3a6e547cf31efa24e967b08e35e7a89fc1`。
- `forced_required/ledger.jsonl`：`f725a31df9aca22eeed234bfa5ef4db9ddad387396ea61d4cae38dbaa6c7ffd0`。
- `private_behavior/base/public_required.out`：`5cf1efae1a4e210608a764e041721c51187b8652a17392bd57844e9a310698c0`。
- `private_behavior/base/public_defaults.out`：`beb773756a4f540e9505fae3d90e0ce71ad4c0742349348cd9a5bb24a56122af`。
- `private_behavior/base/public_existing_tests.out`：`3008d20fd826ac33c33837cf1693557ddeebb8ea9877cb198fd6e9e1d696a91d`。
- `private_behavior/base/private_ellipsis_boundary.out`：`da91977445092d80bc203c84b92002578f8bbd8fb7fb6e624371045f380eeaf0`。
- `private_behavior/gold/public_required.out`：`dd0e5c7cebfe984038dc4153076f8b50383c51471bbf6a506944b7058600e98f`。
- `private_behavior/gold/public_defaults.out`：`beb773756a4f540e9505fae3d90e0ce71ad4c0742349348cd9a5bb24a56122af`。
- `private_behavior/gold/public_existing_tests.out`：`973799a08d47ab4edbafd624cee31eab5afa00f7310dd460706f4976f2474154`。
- `private_behavior/gold/private_ellipsis_boundary.out`：`7c30c4949f28e415efb05c3d09ff9a7d2e495b0e2611bae27628e8b7dd51c65c`。
- `private_behavior/forced_required/public_required.out`：`dd0e5c7cebfe984038dc4153076f8b50383c51471bbf6a506944b7058600e98f`。
- `private_behavior/forced_required/public_defaults.out`：`754f289d5cd80c5d30a902a998de95291332f5cdef392b093de0be267e72580c`。
- `private_behavior/forced_required/public_existing_tests.out`：`ec298d217ffe11e2ead9e272b57769ff36692c7e646c3c70fa98e14c433ef96d`。
- `private_behavior/forced_required/private_ellipsis_boundary.out`：`dd6ce4920b52dd1c34df0720b5ba45b478aca3d61d606d1349019027c6b20136`。
- `private_behavior/summary.json`：`1a4a45e6224fdebacc531be927c9c93361b086c2d8b82f51f3f02366ff68d624`。
- `private_behavior_spec.json`：`2f107ec3aff9f87eb0e72f75f12857c00e8c26c8612867bac7243519f5d3c39f`。
