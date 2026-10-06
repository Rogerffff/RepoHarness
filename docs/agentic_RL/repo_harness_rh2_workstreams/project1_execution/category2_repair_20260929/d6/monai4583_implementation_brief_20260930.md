# MONAI4583：补充三维行为验收

2026-09-30。用户已批准SWE正式评分材料修订机制，并要求两道mypy验证后逐步用于其它题。本片在该授权内推进，保留原公开题面、测试命令、原参考集合、二值奖励及安全边界。新增测试在base应失败，必须登记为新增F2P，不能冒作P2P。

## 固定输入与责任

实现基线为 `runs/category2_repair_20260929/frozen_d6_pyd8793_v1/code_v1/`，681文件库存摘要 `7ea49711ca625a089640885e9d6c9f41405654f21ce1b3abac2295bac6e9feca`。不得从不断变化的共享代码复制覆盖已验基线。隔离实现写入 `runs/category2_repair_20260929/d6_monai4583_implementation_v1/`，共享生产文件由root审查后按路径摘要守卫接入。

题级材料入口为 `swe_materials/monai4583_next/README.md`；manifest摘要 `c6948b67393da89e303403d0fffc1e70593b49029387bfb972b9b8c729ad1e04`。有效测试仅新增 `tests/test_box_transform.py::TestBoxTransform::test_sparse_3d_mask_preserves_foreground_labels_cpu`，原4F2P/5P2P顺序和身份保持，形成5F2P/5P2P。

## 实现范围

1. 增加明确的新增F2P修订类型/操作及本题固定资产登记，不能扩展成自由脚本或任意测试路径入口。按现有模型结构选最小变化，保留旧类型的序列化字节。
2. 原始test_patch、文件SHA、原参考和父grading digest均做重验；父身份恢复必须恢复原补丁及两类原参考。拒绝缺失/重复/交集/重排、错题/错pin/错基线及不匹配材料。新增材料进入正式身份与资格判断，旧资格不得复用。
3. producer从原216四类来源生成新版本。相对Pyd8793已验producer只允许本题grading/environment改变；public/validation全字节保持，其余215行不变，四道已验修订身份与脚本保持。
4. 正式actor/replay共用构造、测试恢复/保护及基线校验。沿原vendor安装与 `pytest -rA tests/test_box_transform.py`；不改parser、奖励、manager、通用评分报告或公共网络权限。
5. 私有修订诊断区分 `original_f2p`、`added_f2p`、`original_p2p`，新增F2P从F2P结果桶核对；旧修订的诊断字节不增加空分区。原新增P2P路径保持原输出。
6. 实现者做与新边界相关的类型、入库、消费、资格和原版本兼容检查；root独立核验后才冻结并执行CPU。避免测试只验证自己的固定值，负例须真正到达欲测试的校验路径。

## 运行验收（本文件批准方案，尚非结果）

root统一远端执行，使用本题原始不可变镜像；只在新目录操作。依次验证正式noop/gold/2D-only为0/1/0，十个参考真实执行且退出码、完整日志与断言原因一致。随后真实Claude Code桩端点执行公开开发操作，再将同次actor原冻结工件送独立grader，保留完整baseline和excluded census校验。解题侧不交付私有新增验收。

资源先沿历史2CPU/4GiB/PID512/shm64MiB、setup900/test1800/whole3600/candidate900/apply120/cleanup120。超时、安装或清理异常保留现场并诊断，不默认增预算或跳过。历史镜像ID、依赖和运行结果仅作期望，须新机实际回读。

最终交付为逐参考0/1/0、公开actor开发及原工件直评、代码/材料/镜像/配方身份、原件对账、独立复核和用途边界；完成后交第1类线程冻结新探针快照，不能热换其在途版本。CPU验收不等于训练资格。

## 执行前信息修正（16:28 SGT）

根线程通过已验冻结vendor读取，原测试命令准确字节为 `pytest -rA  tests/test_box_transform.py`（两个空格）。v1提案的单空格只是不准确的预期，没有改过生产命令。保留v1，正式验收输入改读 `swe_materials/monai4583_next/materials_manifest_v2.json`（SHA c3d33ec3ff65042ba423af2b2b050f65a7f73e50bd5adaae061176c17fc41aec）；只修正该信息字段与版本说明，所有测试/来源/候选资产保持原SHA。首轮单空格测试失败日志保留。
