# 同原FP CPU恢复worker独立审查（2026-10-03）

结论：最终封存worker及其本次串行派发条件未发现未闭合的静态阻断，可以交CPU owner做已有授权的验收。**本审查没有运行worker、候选、CPU/GPU评分、SSH或Docker；纯构造、信号替身与正式补评结果不在本报告已验证范围。** 105/137仍是固定参考范围，不能预先写成通过数；原infra/reward=None、7305后续资源失败原件、单个真实模型样本及另一模型缺项保留，不授训练资格。

## 适用字节与输入身份

- [worker](../tools/cpu_same_fp_regrade.py)：SHA `30db91df2afd0ad29bbe1fb296ad39e4d1df9653c774b4bb129527ec560bdbcd`，342行。
- 最终快照 `snapshot_b22c915de19b36f1`：manifest SHA `b22c915de19b36f1e619edb69e557e9af7a14369ba4955e27bd116bd9c4e11a5`，1099个固定文件 / 145,261,405B，其中1045个code8成员；本审查逐文件核SHA、大小和regular/非symlink身份，全部匹配。worker快照副本与上述源码相同。
- [本次launcher v2](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask_same_fp_cpu_c_v1/launch_cpu_recovery_v2.py)：SHA `dd278359f0d75ca60e9d513fa66cc942ff5d83fa98391d262fff6304cbab22ad`；远端采用新的owner recovery v2 namespace。
- 串行helper SHA `b4e5254555f51cba3b0dc55f66bce07f2f08ee6528a1b99e7df412df8b6a98ee`，统一CPU slot SHA `a77d0665ec15e919a341c0d7dbd18fdc6091663e372dfb1002c57d17e5753972`。完整来源与行号见[JSON证据索引](non_author_cpu_same_fp_regrade_worker_review_20261003.json)。

| 题目 | 原FP canonical SHA | 镜像实际ID预期 | 参考范围及改动 |
| --- | --- | --- | --- |
| 7305 | `5e64758cd92207d53d5ed93525a9f02d4e4e067a197a066b14e836a8974959e2` | `b4f186ca0a0139f4287b9203a666b9fd009af079ddad700bb2bf8019aede8b99` | 105；setup300→900，加已审五env caps |
| 9378 | `ed5ec645234368669128c41ad3a2b9104ecf20bf346535bd22e2f60dda49df4d` | `1e5a0ee850161b35d33d26445f73e872488a45e0e436195af239190b68574096` | 137；仅setup300→900 |

两题其他预算均保留whole3600、apply120、test1800；资源为2 CPU / 4GiB / pids512、候选UID54322。固定模板输入SHA分别为7305 `d9732ce0ef99d947deb619c72a417f792946a13af3ffe235f4fb6459c606d3bc`、9378 `88d5d43c1e127b131dbd8be1f2330ca5e98db29fe5a8132dc5c1950fb7c80922`。本审查独立读取并核了各自31/28项固定输入绑定（有共享来源，不把59当成不同文件总数），原预算只替换setup后与新预算相等；各105/137参考列表均无重复。

## 实际路径的静态核对

**code8、FP、镜像与脚本绑定。** worker L38–46在构造前验证整个快照manifest；L51将固定code8 src置入sys.path，L62–70核已加载repoharness2/slime模块路径并记录SHA。模板的controls L23–36核固定输入、原失败和FP provenance；construct（7305 L43–60、9378 L42–54）只改setup，复核原镜像声明、材料、public、reference及profile，重算原FP canonical digest并调用原manager的绑定校验。固定entry L261–278从原FrozenPatch/baseline安全构造projectable评分投影，没有重求解。code8 manager SHA为 `1783533e1e3b66a57fcaa5a599a1da4f8e4e886318e24f040c6df91f294c1c1e`，不能替换为当前工作区manager。

worker L124–127先比预期image inspect完整选定字段；L166–180在实际容器起后比实际Image ID、owner/trajectory labels、NanoCpus/Memory/PidsLimit和NetworkMode=none。先查镜像ID存在不能独立锁住mutable标签；容器起后的实际ID复核补上这条边界，身份不符不进入评分。L287–290在运行收口后重新验整个快照；L294–297要求源未变、基线重建已过且清理完整才产done。

**供给关闭，因此是single-shell。** worker L73–89分别记录单shell及two-stage完整摘要，L121要求manager supply=None且不适用supply路径；L234的diagnostics读回再次核supply和实际摘要。code8 manager L2204–2211把supply配置作为two-stage必要条件，L3590–3599在record.supply=None时执行candidate_test_script；candidate_test_after_install_script存在不改变这个选择。7305最终单shell摘要为 `a071ed0d14c576d2029f8bdb3b4d9e9f04e679be6e5dea8633c3b63607700450`，9378保持原摘要 `973844ec7101c4754a1a0d3ca73815717f75430a80a494d0dcb1d184f68bac69`。

**7305五键在本次实际测试入口被消费；native线程上限仍需现场证据。** 模板L66–83仅插入export与白名单观测；L68锁原pytest命令一次，L70–71要求conda激活与必要carry恢复已经在前。观测Python输出selected_env及Dask num_workers；worker L258–267必须读到五键的精确值与Dask配置2，并要求原processes两组在原日志及正式参考 `result.success` 中成功。五键为DASK_NUM_WORKERS=2，OPENBLAS/OMP/MKL/NUMEXPR_NUM_THREADS=1。这里没有替换scheduler、删processes项、加skip或改变显式Pool(8)。原命令有意skip的slow八池项不新增为强制正式要求；105参考范围保持。

caps读回能证候选shell的env及Dask配置值；没有逐子进程native backend/thread调用trace，不能把它当成所有库都实际启用、每线程归属已追踪或池一定只2线程的实测证明。9378模板没有注入五键，本次仅延长setup，不能沿用7305的资源故障因果结论。

**资源事实和异常清理。** worker L132–161从该容器host PID定位的cgroup读CPU/memory/pids、采样自有进程Name/Threads，并每5秒记录；monitor异常留痕且阻断done。L181–182要求fresh pids.events=max0；L187–197在cleanup前采样/inspect失败时记录错误，仍调用原manager有界cleanup。L268–272要求收口前pids max事件0、OOMKilled=false、memory.events的oom与oom_kill均0；失败保留status，不洗成候选0分。L280–297核manager容器数创建/移除恰为1、无open/supply/cleanup failures，并再查本job标签容器残留；任何未知阻断done。采样并非持续逐线程trace，累积pids/OOM事件比只看某一时刻的线程数量更能限定验收结论。

**引用会计允许候选真实失败。** worker L237–253要求安装正常收口、测试有int RC、完整候选段及非partial；L241–252逐分区核原references不变、结果唯一且完整覆盖、无missing/skipped/unaccounted，总数105或137。`failure`结果不被删掉，也不要求全部参考成功；所以候选正常失败仍可完成环境验收。infra/parse/残缺测试不算完成，cap与原processes必需项失败也停止。done的含义限于同原FP环境补评已完整收口，不能替代语义成功或训练资格。

## CPU槽与取消边界

launcher v2 L18–24固定mode=run、完整前景worker子命令、固定CPU runtime、code8 PYTHONPATH、原manifest参数和新out；L45明确 `stop_on_nonzero=True`。worker L103–114核统一wrapper字节、唯一running admission、child PID=self、parent PID=supervisor、run/package和execute参数。cpu_slot L43–61持槽flock，L89–102直到完整child.wait返回才释放；cpu_wait_for_slot L44–59只在返回75时退让，普通失败不自动重试。serial L67–73前景等待本题，本次任何非零停止下一题，避免清理未知后继续派容器。只有外层serial队列持久化，不后台裸启动grader。

统一slot L76–86会转发SIGTERM/SIGINT；worker L302–318把首个信号转换main task.cancel，之后信号只记账、不再次取消cleanup。execute L273–297保留异常并走finally/manager.close，非零退出不能进入下一题。这个修正已在最终字节中静态核实；真实信号替身和实机收口并未在本审查执行，不能写作运行通过。

## 剩余验收及最少建议

1. 按最终manifest/launcher做新namespace纯构造，再读完整binding、runtime_code_binding和scripts；只有这一步真实通过才进入评分。题主回报旧namespace曾因统一444运输触发private权限检查而拒绝，旧失败不回写、不复用其out。deploy_snapshot_v3 L39/L48–52改为目录700、只读文件400，逐SHA保持字节，但**本报告仅核部署代码，不把远端权限或新纯构造结果写成已验**。
2. 由CPU owner在统一槽内完成两题各一次同FP补评，逐项读安装/测试、实际UID、原single-shell摘要、105/137参考结果（包括真实失败）、7305原processes两组及cap读回；不重跑有效17矩阵、不增加模型样本或另一模型臆造项。
3. 读fresh及收口pids.events、oom/oom_kill/OOMKilled、自有进程采样、原manager及标签残留清理、结束snapshot SHA。遇到非零/清理不明停止串行队列并读回保留原件；不自动补跑。

本报告只新增本对文件；历史报告与运行证据未改。静态绑定确认方案范围，不证明实际补分已成功，不授训练资格。
