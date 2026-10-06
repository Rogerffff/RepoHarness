# MONAI4583 reserve6 CPU计划

2026-09-29，仅本地静态就绪，未执行。沿既有静态结论推进，正式评分不改。

- 输入：`runs/swegym_cpu_preprobe_20260929/task_inputs_reserve6_v1/Project-MONAI__MONAI-4583/`，远端对应 `inputs_reserve6_v1/<IID>/`。公开只有 `public_commands.json`；gold、只修2D候选、行为预期与参考在 `private/`，不挂载到actor。
- 原镜像固定 manifest `79bf18ecd969a2e68a113b6d29b3d9e77ed977e37bd02666f17eef51930824d5`，base `9c4710199b80178ad11f7dd74925eee3ae921863`。09-19 baseline01已noop0/gold1；没有已登记题级依赖修复，先原镜像、不预建新层。仅远端pull immutable来源，再将同一image ID设为冻结grader所需的本地公开tag别名，记录别名和ID，不拉可变latest。
- 无新增wheel/图像数据。公开探针是内存NumPy/Torch CPU小数组；历史依赖已知Python3.8.20、torch1.13.1、NumPy1.24.4、pytest8.3.3、NiBabel5.2.1仅作恢复诊断线索，不提前锁改原镜像。当前身份/资产/依赖未知；pull/import/collection失败即停，另版修复后再验，不套2446配方。
- 公开开发：身份/初态full diff；反对角2D与同机制稀疏3D，两个通道标签0/7，每项覆盖NumPy和Torch CPU、默认float32/int64与显式float64/int32；输出实际box/label/dtype/device。原base预计两项都只在标签失败，box应为两份`[0…0,2…2]`、标签误为`[-1,-1]`。另跑公开5项矩形box旧测，预计全部通过。前景类别来自同通道实际前景，3D与dtype依据base API，未要求内部实现。
- 私有三个独立root变体：base预计2D/3D均失败；gold两者通过；只修2D预计2D通过、3D仍失败，旧测三者均过。必须看到完整结构化输出与指定断言，ImportError/超时/其它失败不算目标复现。先验base整文件SHA，check/apply后再验整文件SHA；私有不证明actor权限。
- 正式：新条件下noop/gold/只修2D三方，冻结原4 F2P+5 P2P。前两者预期0/1；只修2D的分数未知，预计可用于检验3D覆盖缺口，不提前定误奖。实际frozen源码、日志SHA、每参考状态、完整测试RC和两层清理后才能解释。

入口：`rh2/experiments/swegym_cpu_preprobe_20260929/monai_reserve_followups_v1.py --task Project-MONAI__MONAI-4583`，默认新attempt `reserve6-v1`。仅root远端执行，读取 `prepared/private/gold/reserve6_v1`。复用已审mixed运行/私有函数，校验父文件与helper摘要；正式devcheck桩端口18109，2CPU/4GiB；actor wall1800、公开单命令120/180/180/300秒；私有总3600秒；正式setup900/test原1800/whole3600，每题串行三候选。外部中断由父运行器发进程组TERM并等待清理，未确认清理/infra即停止本题，不派后项。

本地只做JSON/嵌入Python AST、统一diff逐行纯文本应用与整文件SHA检查，未导入项目、pull或运行历史源码。`input_manifest.json`固化输入；实际环境及三方行为仍未验证。已知静态限制、D6、真实模型题面交付、GPU/训练资格不由本次准备解除。
