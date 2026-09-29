# datalad `58ba5165` 环境审查（P2，2026-09-24）

> **当前状态（2026-09-24 更新）**：`qualified_with_revision`。用户批准 T0-2 方案 B1，实施为封板修订单 `r2e-mr-002`（`test_1.py` 一行导入改为 `from .test_2 import (`）+ 派生配方 `r2e_derive_v1+material_v1`。A 线机器真实 grader：noop 0（2/4：api、cmdline）×2、gold 1（4/4）×2，与下文沙盒 B1 逐键相同。修订后没有同版本的独立 runner，对账把这 4 行单列。证据 `runs/r2e_t0_revisions_20260924/`。以下是修订前的审查原文。

**结论**：分类 `material`；处置 `held_material`。环境本身无缺口；gold 到不了来源定义，原因在材料：隐藏测试依赖缺失的测试支撑材料。提案见 `material_revisions/datalad__58ba5165234cb16de0e8463ee75097362099835f.md`（推荐 B1；用户决定前先隔离）。

**依据**
- gold 3/4（R-f 两次、两个参考 runner 都是 0）：`r2e_tests/test_1.py::test_alter_interface_docs_for_cmdline` 断言 `"multiline cli-only with [ brackets\n[] ]" in alt` 失败。日志里的 `second=` 是修复前 `demo_doc` 的处理结果。
- 隐藏 `test_1.py` 从**仓库内** `datalad.interface.tests.test_docs` 导入 `demo_doc` / `demo_paramdoc` / `demo_argdoc`。上游修复提交同时改了这个模块（加入方括号示例），但 gold 按 `is_gold_excluded_test_path` 排除测试路径；R2E 只把新版本放进了 `r2e_tests/test_2.py`。
- 字节对照：隐藏 `test_2.py` 与上游修复后 `test_docs.py` 的 sha256 都是 `2a3a29f7…`；工作区 `test_docs.py` 是 `b2903652…`，即修复前。三个 `demo_*` 常量逐一对上。
- 沙盒 dry-run（一次性容器，不是正式评分）：原样 noop 2/4、gold 3/4（复现 R-f）。B1（`from .test_2 import …`）与 A（评分前恢复修复后的 `test_docs.py`）下都是 noop 2/4、gold 4/4。
- R16：目标键（noop − gold）只剩 `test_alter_interface_docs_for_api`，而题面示例恰恰是 cmdline 函数。R04：要让 cmdline 键通过，只能去改 `r2e_tests` 以外的测试夹具。
- 探针十项最小条件满足：`.venv` Python 3.9.21、pytest 8.3.4、无 pip；**`/tmp` 下可导入**，M3 的"需 cwd"是误报（git 身份警告被当成导入结果）。公开复现 REPRO_OBSERVED=1（PY 段内容残留、标记残留）。公开 `test_interface.py` / `test_docs.py` 各 2 passed：base 上的 `demo_doc` 不含方括号示例，所以不暴露该缺陷。R13 pass（两次一致；两次的镜像 ID 不同，重建只改了 index 摘要）。

**缺口**：材料问题待用户决定（T0）。本轮没有改任何材料。

**解题侧条件**：cwd 不限；无 pip、无网络；agent HOME 没有 git 身份（本题不涉及 git 操作）。

**建议**：先按 C2 隔离；用户若采纳 B1，需出新材料版本（pins）并重建该题派生镜像，再做正式 noop / gold 各 ≥ 2 次验收。

先后：复现脚本在读隐藏测试 / gold 之前写成；本题分析读了私有隐藏测试与来源原始行（E06，validation_only，只用于分析）。证据：`runs/r2e_env_repair_20260924/p2/dryrun_58ba/`、`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-gold-d_d14560df.eval.log`、`runs/r2e_env_repair_20260924/p2/dev_probe/datalad__58ba5165234cb16de0e8463ee75097362099835f/`。
