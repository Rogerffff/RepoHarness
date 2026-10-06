# Moto5406：R5 工具附件窄核

2026-10-03。允许题主使用本附件开始新 CPU 尝试。它不是远端验收结论。

附件：`runs/category2_repair_20260929/release_work_20261003/moto5406_acceptance_tools_v3_git/`；`tools_manifest.json` SHA256 `09f7b6de626c00fba904137b763c8c4c66777cbe1551fbd41812dbce46d2c86c`。绑定第五版 `cat2-cpu-r2e078079-swe7-git-20261003-v1`，外部 manifest SHA `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`、837 个成员。

根复核逐字校验了 9 个附件成员。与已审 v2 相比，四份执行／检查 Python 和公开命令完全相同；common.py 唯一变化是 SWE7 producer 固定摘要。完整 diff 中没有放宽 guard、超时、清理或评分路径。Moto 公开、评分、环境、材料及脚本身份保持，producer 使用 `ingest_mypy_monai_pyd_monai4583_moto5406_monai3715_v1`，manifest SHA `84e82a8219c215ce5f8711bbd7e3306d4af6217dc9c809ee1dc436bcc52352fd`。

已读作者本地 default prepare 和绑定检查：actor/replay 同 spec，真实 producer／材料绑定成立，混用新旧 repo、manifest 或 SWE6 producer 均拒绝；prepare 后清单未变。这些是本地工具兼容证据，没有 SSH、Docker 或题目评分。

题主沿用已核的远端材料、runtime 和公开输入，只换工具、R5 code-root、外部 manifest、SWE7 producer，以及新 run/attempt/output。旧 BaselineIntegrityError 原件保留，旧 FrozenPatch 不改绑；从 R5 基线新产生工件并核实际评分和清理。本地 fixed_inputs_local.json 不是远端供应证据。R5 Git 四文件修复的共同验证由协调者维护，不重复测试整个共享机制。
