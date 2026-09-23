# L1 · 逐题静态审查（按仓库分包）

目标：对分配给你的每道题留下"公开要求 → 代码/测试依据 → 疑点 → 最小复验"的结构化记录，并落实第四组 B 的文件边界（额外排除默认为空）。这是审查，不是盲测；顺序要求：**先只看公开材料（题面 + base 代码）写 `public_view`，再看 test_patch / gold / F2P/P2P / hints**。

## 每题步骤（目标 10–15 分钟，最多 20 分钟；超时写 unknown 转下一题）
1. 从 `public_bundles_v0.jsonl` 取 `problem_statement`；在裸克隆上 `git worktree add --detach` 到该题 `base_commit`；定位相关模块、调用者、既有测试。写 `public_view`：目标行为、约束、公开材料无法确定的点。
2. 再读 `test_patch`、`fail_to_pass`/`pass_to_pass`、`golden_patch`、`hints_text`。逐项填检查：
   - **1 材料对应**：test_patch/gold 目标文件在 base 是否存在、是否与题面同一问题；含二进制/LFS/子模块材料则注明。
   - **2 初态含问题**（静态）：base 代码是否确实有题面所述缺陷；若 base 已含修复或题面与代码不符 → issue。
   - **3 实际输入**：题面是否含外链/图片/被截断的代码块；hints 里有而题面没有的关键信息要指出（hints 不可见）。
   - **4/17 文件边界（B）**：列 `test_patch` 触碰的全部路径，标出其中**非测试源码**（会被恢复覆盖，混合职责）；判断 gold 触碰路径是否含测试样路径；给出 `additional_exclusions`（默认 `[]`，非空必须写明它如何改变判分、为何不是合法解答）。
   - **5 重复/派生**：与本仓库其它题是否同一 PR、同一修复、同一测试文件的近似改动（用 task_signals 与 grading bundles 比较）。
   - **23 要求充分/一致**：公开材料能否推出 F2P 所检查的行为；未说明的接口名、返回格式、异常类型逐条列出。
   - **24 测试是否强制唯一实现**：新 helper 名、内部调用顺序、精确字符串；举出一种合理的替代实现会不会被 F2P 拒绝。
   - **25 测试是否放过错误修复**：题面原例与关键要求是否被 F2P 覆盖；哪些部分修复/硬编码能通过。
   - **26 扩展回归建议**：按调用者/同包给出具体测试文件或 ID（`proposed_regression_tests`），说明选择理由。
   - **27 gold 正确/完整/对应**：gold 是否含与题无关的改动、是否依赖未交付的其它改动。
   - **29 静态泄漏线索**：题面/hints 是否直接给出修复代码或指向上游 PR/commit。
   - **6/7/11 静态线索**：安装/测试是否需要下载权重、数据、外部服务（grep 测试与 conftest 里的 URL、`requests.get`、`torch.hub`、`boto3` 真实端点等）；只记线索与下一实验。
3. `disposition_hint`：`ready_for_probe` / `needs_review` / `needs_repair` / `reject_revision` 之一 + 一句理由；这是建议不是裁定。
4. 落盘：`<包目录>/records/<instance_id>.json`；追加一行到 `<包目录>/summary.md` 表格（task | 主要发现 | 建议处置 | 下一实验）。移除 worktree。

## 排序
先做 `task_signals_swegym.json` 里 `in_e2` 非空、`fragile_reference_id`、stage1 gold 非 FULL、有 DeepSeek 候选的题，再做其余。

## 结束
08:30 停；`summary.md` 末尾写覆盖数、未做清单、你认为最值得用户裁定的 3 个问题。
