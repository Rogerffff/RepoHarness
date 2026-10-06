# datalad `19f5b450` 环境审查（P2，2026-09-24）

**结论**：分类 `solver_condition`；处置暂为 `unknown`，只差 R13（待中央复跑并入）。环境本身无缺口。

**依据**
- R01 / R02 / R08 / R15 pass：gold 19/19、reward 1、rc 0，导入 `/testbed/datalad/__init__.py`，与参考逐键一致；noop 18/19，目标键 `test_run_exit_code`，原因行 `assert 1 == 3` 与题面对应。
- 探针十项最小条件满足：`.venv` Python 3.9.21、pytest 8.3.4；pip / uv 都没有；`chown -R /testbed` 111.9 s（并发下偏高；R-f 的 setup 为 86 s）。
- **M3 标的"cwd 不在 /testbed 时导入失败"是误报**：M3 `pkgsrc.txt` 在 `/tmp` 下同样导入到 `/testbed/datalad/__init__.py`，前面多一行 DataLad 的 git 身份警告，`collate_facts.py` 取了第一行。探针 `IMPORT_FROM_TMP_RC=0`。
- 公开复现：以 agent 身份不设 git 身份时，`create` 失败（`Author identity unknown`）；只对进程设置 `GIT_AUTHOR_*` / `GIT_COMMITTER_*` 后，`datalad run --explicit 'exit 3'` 退出码为 1（期望 3）→ REPRO_OBSERVED=1。
- 相关公开测试 `datalad/cli/tests/test_main.py`：18 passed / 1 skipped（13 s）。
- 题面示例的三个导入位置不存在（`datalad.api.run_main`、`datalad.utils.create`、`datalad.support.gitrepo.chpwd`），照抄会 ImportError；文字描述清楚。属题面质量，移交后续题意筛查。

**缺口**：R13 同条件只有一次运行。

**解题侧条件**：cwd 不限；无 pip、无网络；**agent HOME 没有 git 身份**，建数据集或 `datalad run` 前要 `git config --global user.name/email`（HOME 可写）或设 `GIT_AUTHOR_*` / `GIT_COMMITTER_*`。评分不受影响：隐藏 conftest 自带临时 HOME 和 git 身份。

**建议**：中央复跑并入后转 `environment_qualified`；git 身份这一条交任务面 / A 线决定是写进解题提示，还是由 rollout 初始化写入。

先后：复现脚本在读隐藏测试 / gold 之前写成（E06）。证据：`runs/r2e_env_repair_20260924/p2/dev_probe/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb/`（REPRO_OUTPUT）、`…/p2/pubtests/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb.log`、`…/p2/followups/followups.log`（D 段）、`runs/env_overnight_20260916/M3/facts/19f5b45096ca/pkgsrc.txt`。
