# M3 · 机器 3：R2E 48 题镜像事实采集（2026-09-16 夜，两片）

在**机器 3**上对 `r2e_images_48.txt` 的 48 个 R2E 镜像做事实采集与受控实验。第一片是只读事实采集（检查编号沿用 L4 的
[`machine_checks.md`](../L4_r2e/machine_checks.md)，M-01…M-13）；第二片是候选身份修法、gold 重复稳定性、`probe_unrelated` 三组实验。全部容器 `envscreen-m3-*` 前缀、
`--network none`、并发 ≤ 3、用完即删，未 `docker commit`，未改 `rh2/src`、`rh2/tests`、`rh2/experiments`。

| 产物 | 内容 |
| --- | --- |
| `M3_report.md` | 48 题事实表、风险分层、接入 rh2（方案 A）前必须处理的环境问题、与 L4 静态结论的核对、机器残留检查 |
| `M3_r2e_check_records.json` | 逐题记录（COMMON.md §1 形状）：`checks{M-01…M-13}`、`issues`、`file_rules`、`disposition_hint`、`costs` |
| `M3_key_collisions.json` | 48 题按来源入口实跑摘要算出的 Prime 折键碰撞核对（M-11） |
| `M3_uid_fix_probe.json` | **候选身份（uid 54322）最小权限布置实测**：布置 b 覆盖全部 48 题 × noop/gold（96 次），布置 a/c 各 5 个代表镜像 × noop/gold（各 10 次），共 116 次实跑的成本、判分一致性、可写面，外加 4 次「能否替换评分面」的替换攻击实验（2 镜像 × 布置 a/c，每次 6 项动作） |
| `M3_gold_repeat.json` | 48 题 gold gate 两次独立运行的逐键比对（键集、状态、SKIPPED/XFAIL 漂移、耗时） |
| `M3_leak_path_probe.json` | 48 题的泄漏路径实测：HEAD 是否游离、`git rev-list --children --all` 列出的 HEAD 子提交里修复提交排第几 |
| `M3_gold_after_scrub.json` | 48 题在 **git 清理后**打 gold 补丁并评分的结果：`git apply` 是否成功、reward 是否与未清理一致 |
| `M3_git_scrub_probe.json` | **48 题**的 git 清理实验：分离 HEAD + 删全部 ref/tag/remote + expire reflog + `gc --prune=now` 之后，修复提交对象与 noop 评分的变化 |
| `build_image_facts.py` | 把机器采回的原始观测目录聚合成 `runs/.../M3/r2e_image_facts.json` |
| `analyze_noop_x2.py` | 解析同容器连跑两次 `run_tests.sh` 的输出，产出 `runs/.../M3/noop_repeat.json`（parser 规则复刻 `r2e_probe.py`） |
| `analyze_uid_fix.py` | 汇总 uid 布置实测，产出 `M3_uid_fix_probe.json` |
| `analyze_gold_repeat.py` | 比对 gold 两次运行，产出 `M3_gold_repeat.json` |
| `build_check_records.py` | 由上面两份聚合结果 + gold 账本 + 清理实验生成 `M3_r2e_check_records.json` |

大文件在 `runs/env_overnight_20260916/M3/`（51M）：

- `facts/<commit12>/` —— 逐题原始观测：`facts/*.txt`（M-01…M-13 的命令输出）、`r2e_tests/`（隐藏测试原文）、`initial.diff`、`asuser.txt` / `asuser_exec.txt` / `interp.txt`（候选身份探针）、`pkgsrc.txt`（包来源）、`collect.txt`、`noop_x2/`（两次 noop 日志）、`git_scrub/`（清理实验前后）、`gold_after_scrub/`、`leak_path/`、`uidfix/{a,b,c}_{noop,gold}` 与 `uidfix/attack_{a,c}`
- `r2e_image_facts.json` / `noop_repeat.json` —— 聚合结果
- `gold_ledger/` —— gold gate 账本 `r2e_gold_m3.jsonl`（96 行 = 两次各 48）与逐题日志 `logs_r2e/<repo>/<commit12>/gold/a{1,2}/{gold.diff,test_output.txt,status_map.json}`
- `unrelated_ledger/` —— `probe_unrelated` gate 账本 `r2e_unrelated_m3.jsonl`（10 行）与同形状的逐题日志
- `bin/` —— 在机器上跑的采集脚本原件，含 `r2e_probe_m3.py`（`rh2/experiments/env_probe_20260909/r2e_probe.py` 的副本，**只改容器名前缀**以满足本包机器纪律，解析与判分逻辑逐字不动）
- `probe_data/` —— 喂给 probe 的 48 题输入；`logs/` —— 各轮批处理日志

早上先看 `M3_report.md` §3（风险分层）、§4（接入前必须处理的问题）与 **§8（候选身份修法定案，含 §8.4 的「文件权限挡不住替换」实测）**。
