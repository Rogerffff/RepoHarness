# pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8：环境审查结论（P4，2026-09-24）

**结论**：分类 `material`；处置 `needs_decision`；R13 待中央复跑并入。环境与评分可用；公开题面与目标测试矛盾，并把 pytest 8 伪影写成缺陷，已写材料提案（推荐本轮隔离）。

**依据**
- 评分：R01 pass；noop 0（mismatched ['TestImage.test_open_formats']）、gold 1（55/55，rc 1）；对账 agree（R15）；R13 unknown。
- 探针（agent/54321、--network none、2 CPU / 4 GiB / /tmp 1 GiB）：最小条件 10/10；/testbed/.venv/bin/python 3.9.21（PATH 首项；docker exec 继承镜像 ENV）；pytest 8.3.4；pip 缺失；cwd=/tmp 也能导入；/testbed 可写、/usr/local 不可写；无出网；chown 29.22 s。
- 公开测试：Tests/test_000_sanity.py：collect rc 0 / run rc 0（1 passed）；Tests/test_image.py：2 failed（pytest.warns(None)）/ 52 passed。
- 公开复现：REPRO_OBSERVED=0：题面所述 Warning/NoneType TypeError 不可复现；可观测 `Image.open(..., formats=[...])` → TypeError: unexpected keyword argument 'formats'。
- 期望 / 键：期望 2 个 FAILED 键（test_no_resource_warning_on_save / test_show_deprecation）：测试里的 `pytest.warns(None)` 在 pytest 8.3.4 下抛 TypeError，死键，不改。
- 泄漏：派生镜像 fix_present=no、私有目录 700；HEAD 无子提交、无 refs / remote / reflog、无补丁残留；install.sh 是通用安装脚本（uv venv + uv pip），不含修复。

**缺口**
- 题面称 `Image.open('hopper.png', formats=['JPEG'])` 应成功，目标测试要求 UnidentifiedImageError，另要求 formats=123 → TypeError（题面未提）。
- 题面 Actual Behavior 的 Warning/NoneType TypeError 在库里不存在（复现 REPRO_OBSERVED=0）；base 上 Image.open 无 formats 参数。
- 公开 Tests/test_image.py 有 2 个预存失败（同上死键），求解者会看到。

**建议**
- T0 提案：material_revisions/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8.md（推荐 C：本轮隔离，题面修订留给统一的题意筛查）。
- 解题侧条件：无 pip、无网络、公开测试预存失败（E10 记录，不进题面）。

**先后（E06）**：复现脚本写于读取隐藏测试片段、gold 补丁与评分日志正文之前；写前已读 facts.json（含目标键名、gold 触碰路径、原因行摘要）。

证据：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/tasks/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8/screening_record.json`、`runs/r2e_env_repair_20260924/p4/dev_probe/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8/`、`runs/r2e_env_repair_20260924/p4/targeted_public_tests/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8/`、`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/repros/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8.py`。
