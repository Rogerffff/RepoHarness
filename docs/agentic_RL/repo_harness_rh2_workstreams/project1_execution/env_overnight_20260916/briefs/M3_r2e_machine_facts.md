# M3 · 机器 3：R2E 48 题镜像事实采集

机器 3 只归本包使用（协调者派发消息给出 SSH 命令；不写进文件）。布局同机器 2；48 个镜像清单 `/work/envscreen/M3/images.txt`（协调者后台拉取，`/work/envscreen/M3/pull.log` 出现 `PULLS_DONE` 即完成；未完成先做已拉到的）。任务清单与静态事实来自本机 L4 包（`docs/.../env_overnight_20260916/L4_r2e/`，协调者会 rsync 到 `/work/envscreen/M3/L4/`），未到时按 `r2e_images_48.txt` 与 `docs/.../env_probe_20260909/ledger/r2e_ledger_v3.jsonl`、`runs/env_probe_stage1_20260910/r2e_expansion_preparation/candidate_manifest.jsonl`（协调者已 rsync 到 `/work/envscreen/M3/inputs/`）自行组织。

## 机器纪律
同 M2：容器名前缀 `envscreen-m3-`，`--network none`，用完即删，并发 ≤ 3，绝不 `docker commit`，不写主机地址进文件。

## 每镜像采集（全部只读，产出 `/work/envscreen/M3/facts/<repo>_<commit>.json`，同步到本机 `runs/env_overnight_20260916/M3/`）
- 镜像 digest 与 ID；`/testbed` HEAD、HEAD^ 是否等于修复提交、`git log --all --oneline | head -5`、`git rev-list --all --count`、修复提交是否可达（`git cat-file -e <fix>`）、tags/remotes、reflog 行数、`git status --porcelain`（脏工作区文件清单与行数）。
- `/r2e_tests` 目录树（文件名、大小、sha256）、`run_tests.sh` 原文（或等价入口）、测试运行命令、是否引用仓库内测试 helper/fixture（grep import 语句，与 gold 改动的测试模块对照：`modified_files` 来自 candidate_manifest / v3 账本）。
- venv：`/testbed/.venv` 属主、候选用户（uid 54322）能否写、python 版本、`pip freeze` 摘要（前 50 行）、目标包安装位置（可编辑/site-packages）。
- expected 映射：从 `/r2e_tests` 或镜像内任何 expected 文件（若有）读取；与账本里 expected 状态计数对照；记录含 ANSI/空格的键数量。
- 资源：镜像大小、`/testbed` 文件数、预计 chown 成本（`find /testbed | wc -l`）。
- 若时间允许：对 24 题新增批各跑一次 `run_tests.sh`（noop，`--network none`），记录 parsed 状态数与 expected 差异（用 `rh2/experiments/env_probe_20260909/r2e_probe.py` 同一解析规则，只读不改）。

## 报告 `M3_report.md`
48 题事实表（泄漏通道、fixture 依赖、venv 属主、expected 特征）、按风险分层、接入 rh2（方案 A）前必须处理的环境问题、机器残留检查。到本机时间 08:30 停。
