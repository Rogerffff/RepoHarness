# conan-io__conan-11560 初判（封存：只读了题面与 base 代码，尚未读 gold、测试与历史材料）

2026-09-30 / Sonnet 5.5 审计者。写完不再修改。

1. **公开要求（事实）**：题面标题是“bazel generator 对含多个库的包（如 openssl）不可用”。症状是 libcurl 依赖 openssl 时，`libcrypto.a`、`libssl.a` 在链接行里顺序不对。要求的行为是：BazelDeps 生成的 BUILD 能让多静态库的包在 bazel 里链接成功。
2. **建议实现（推断，不是要求）**：题面作者建议给 `cc_import` 加 `alwayslink = True`。这是他自己的方案，题面对其它方案没有禁止；`visibility` 一项，作者自己写了“可能是另一个问题”，不应成为要求。
3. **base 现状**：`bazeldeps.py::_get_dependency_buildfile_content` 的 Jinja 模板有两处 `cc_import`：`libs`（`static_library` 或 `shared_library`）与 `shared_with_interface_libs`（`interface_library`＋`shared_library`）。`alwayslink` 只对静态库有链接意义。
4. **盲写 N1**：只在 `libs` 块每个 `cc_import` 加 `alwayslink = True,`（补 `filepath` 后的逗号），`shared_with_interface_libs` 不动。补丁 `rh2/experiments/category3_cloud_20260929/conan11560/n1.patch`，sha256 `f3a938dd…7285`。
5. **预期风险（读测试前的猜测）**：隐藏测试多半比对生成的 BUILD 文本。可能的问题有：精确文案或属性顺序（T1）；只查字符串出现，放过“只给部分库、或加在错误目标上”的写法（T2）；以及 `alwayslink` 对 `shared_with_interface_libs` 是否有要求。本容器没有 bazel，无法真实链接，只能用 gcc＋`ar` 类比“顺序问题与整档链接”的机制，不能代替 bazel 行为。
6. **初判倾向**：待读测试后定；倾向“问题和修法已明确”一类，但取决于测试是否真的把 `alwayslink` 的位置或格式当成要求。
