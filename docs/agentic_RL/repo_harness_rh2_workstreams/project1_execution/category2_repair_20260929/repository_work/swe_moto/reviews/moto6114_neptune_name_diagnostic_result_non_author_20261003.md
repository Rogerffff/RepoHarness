# Moto6114 两容器 Neptune 名称回退诊断：非作者运行原件窄核

2026-10-03。结论：**本次实际代码行为对照证实两处回归。** 在同一固定 CPU 供应镜像、两个独立新容器、agent UID／GID54321 下，原 base 的两项既有名称调用都正常返回；实际 Qwen 候选内容的 start 抛出 `InvalidDBClusterStateFault`，delete 抛出缺少 `deletion_protection` 的 `AttributeError`。运输、模块内容、隔离条件、完整观察输出与清理证据未发现阻断。

结论只适用于这两项原名称路径的代码行为对照。CPU actual `1d8dd…a9f27d5` 与旧 GPU actual `43f685…716e20` 不同；没有执行正式 grader、新 37 参考或模型，不是原 FrozenPatch 的重评分，不能覆盖旧 raw1。本题两条 P2P 范围已获裁定批准，无需重复审批；新版材料发布和 37 参考 CPU 准入仍未由本次诊断完成。

本次仅使用标准库读回、JSON、SHA256、tar 成员读取和文本核对，没有启动 Docker、CPU、远端、测试、SDK 或模型，也没有执行作者脚本。只新增本报告，不改原件、固定材料或已有报告。我已接触实际候选和私有评分上下文，不是公开盲读 solver。材料／工具静态结论分别沿用[材料窄核报告](moto6114_neptune_preservation_v2_materials_non_author_20261003.md)和[工具窄核报告](moto6114_neptune_name_diagnostic_tools_non_author_20261003.md)，不重复全面语义审查。

## 运输身份与 job 终态

原件目录：`runs/category2_repair_20260929/moto_cpu_20261003/moto6114-neptune-2a7e2a72a7c6_evidence/`。独立重算 **9 件运行原件／98163B** 的全部 SHA256 和长度，匹配 manifest；目录文件集合与 manifest 加自身一致。归档全部文件成员与本地原件逐字相同。

- archive：14895B／`166fd611c6c69a22d1a4e340e11091d179a550d95aba6b766a3d6a8aff8ce0d7`。
- transport manifest：1594B／`4612e200abad0b97074d48fe1a56ca14333f0f9d51a54da6f1c7f07944e66120`。
- transport receipt：559B／`52b16fa8fe4774403ed02b1a32d90915b6257c69298aae07ca8ec6a099a37899`。

| 原件 | 字节 | SHA256 |
| --- | ---: | --- |
| `job/status.json` | 797 | `3f9b1c8cd81236f7e2682fd86e8723d8ff538d19e189d0e282b3dacb731377ae` |
| `job/stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `job/stdout.log` | 108 | `0075c4bfd2209c3b853acc3ff5b4b84fcfc6738a755f6abb3dbf5df34f2761b6` |
| `output/base.json` | 2938 | `21b214dffea8db4e6a44d6d914aa9195e03b4ec5cad87fcfc5b35610d86de8b8` |
| `output/candidate.json` | 3276 | `8e3918cd14786e7b400d33d858889a0cfc685f4647942b0789feba37a1e2e4da` |
| `output/docker_calls.json` | 75306 | `03379d1e832197f113a3d1bc03976b76275d6e89d3e72a3f4ddaeb181f78446a` |
| `output/image_inspect.json` | 8136 | `ceacbff8df010be40ae5cd78a2bf1e3f5ceca9111739faa250a17f6d77469656` |
| `output/observations.json` | 7330 | `7fc04735b6df83a96738b1fbd48012f8d219d777f8bc8f798f2152792599a04a` |
| `output/result.json` | 272 | `2dc4ee47db1dc5ef474daa1bcff389825b097afb3c58850c5bb81c34d14d7a3a` |

正式 slot 的 `job/status.json` 为本题 job、mode run、slot0、status finished、returncode0，实际起止为 00:48:11–00:49:47 UTC。命令固定 R7 `PYTHONPATH`，运行 `diagnostic.py --job moto6114-neptune-2a7e2a72a7c6`；不是未开始的 75。job stderr 空，stdout 和 result 均为 `two_original_name_delegation_regressions_confirmed`。该总状态与下述原始输出一致，未仅据 parent0 接受行为或清理。

## 26 次 Docker 调用和两容器清理

`docker_calls.json` 是 26 个按执行顺序保留的记录，每个都有完整 `argv`、`exit_code`、`stdout`、`stderr`。独立读取所有字符串和退出码，**26 项均 exit0、stderr 空**。下表索引从 0 起，对应原 JSON 数组；root 可信初始化与 agent 行为调用分别核对。

| 步骤 | base 索引 | candidate 索引 | 实读证据 |
| --- | ---: | ---: | --- |
| 新容器 run | 1 | 13 | 不同 name／container ID、同 actual image、资源及自有 label |
| production Git sanitize | 2 | 14 | root exec，完整 HEAD／history／sanitize facts，exit0 |
| production trusted init | 3 | 15 | root exec，WORKDIR_PRESENT=1／RH2_INIT_OK=1／AGENT_UID54321 |
| 写 activation 文件 | 4 | 16 | `/rh2/bash_env` 写入、0644，exit0 |
| agent activation probe | 5 | 17 | UID54321 exec，testbed prefix／Python／conda facts 完整 |
| 原 RDS／Neptune 字节检查 | 6 | 18 | 两臂修改前两模块 SHA 一致 |
| 写实际候选 RDS 内容 | 无 | 19 | 只写 `/testbed/moto/rds/models.py`、0644，probe 再验内容 SHA |
| probe 前实际 container inspect | 7 | 20 | image／HostConfig／label 的真实原始 JSON |
| 同一 agent probe | 8 | 21 | 全部观察 JSON，exit0；两条行为异常也保留 |
| finally ownership inspect | 9 | 22 | 与前次 inspect 相同容器，归属 label 正确 |
| finally rm | 10 | 23 | 只删除各自名称，exit0，stdout 为正确容器名 |
| 自有容器终态查询 | 11 | 24 | ps -a 的本 job label 查询，exit0／输出空 |
| 自有网络终态查询 | 12 | 25 | network ls 的本 job label 查询，exit0／输出空 |

第 0 项是 source 与 actual image 的联合 inspect，其完整 stdout 与 `image_inspect.json` 中 source／actual 对象一致。其余步骤数量与两臂路径相符，没有漏掉 candidate 的唯一源码写入或第二次清理。

两个真实容器 ID 为 base `bf3b2fe089d1785eb99fb363d6591e2531d438c4bc002ba6156286677494128a`、candidate `23e97e36bf9c83c2872276a73c82d36f179ba248126b8850346a51d7b860e18d`，互不相同。finally 先 inspect 核 `rh2.run_id=moto6114-neptune-2a7e2a72a7c6`，再分别 rm；两次 containers／networks 查询均有独立 returncode0 和空 stdout／stderr。`base.json`／`candidate.json` 的 remove_rc／cleanup 与调用原件相符。没有把查询失败当零残留，也没有删除共享对象。observations 中两行与单臂文件逐字段一致；固定入口在完成两臂 finally 后才比较行为并输出 result，job 最终0和清理证据各自成立。

## 固定 R7、实际模块和隔离条件

本次 result 绑定工具 manifest `2772408eec3de9501ee20f355bdc154e864a99d1edcb4c9aec955aa0f7e3a2f0`。固定 config／diagnostic／probe／候选 payload 仍与该 manifest 的 SHA／bytes 相符；候选 payload 已实际到达运行包，否则原入口的完整目录集合和文件 pin 检查不能通过。这里只连接运行身份，不重做工具设计审查。

config 使用 R7 release `cat2-cpu-r2e088-swe12-git-20261003-v1`，manifest `f9dfcd16c9c88e4f514512e61781856b7d6f1a71a20b64cd1843d20546c5009b`，原公开 base `f01709f9ba656e7cf4399bcd1a0a07fd134b0aec`、public digest `sha256:6c8f45da003f8e8d1e065d1801afa4659c43cbb212e319a5d07a84922af5f0f2`。它指向已固定 `moto6114-cpu-0661259fc3d1` prepared summary；本次重新只读对应运输原件，summary SHA `44ad39c1802736c0080c93849cfefedb4ba6b01dd118f2a938b797ff803f6e3d`、prepared manifest SHA `113c26abe818b5ca1a8c738536f76a450ad2cd0ff745f58ec47b6c3d6a5d188b`、唯一 task／public digest／base 均匹配。当前 9 件运行原件没有重新运输整套 prepared；实际入口以这些固定 pin 加原 `load_context` 核对后继续执行，本报告未将其写成新 prepared 或新消费者发布。

实际 source ConfigID 为 `sha256:fefec492f58ed0f8385a7e72234d296bd84d295031ce7e019f63fc33973ec249`，RepoDigest 是本题 source manifest `sha256:cb35f7e131f8e46c8a6865e8fb618c09032ce5ee27f1122f79010a7cfae8ef9a`。actual CPU 镜像是 `sha256:1d8dded2ee5bbe9275514fdc603116ac9f36da5e30c19b2d4ffcba4d4a9f27d5`，source13层与 actual14层去掉末层后的序列逐项相同，实际平台 amd64／linux；两个容器 inspect 的 Image 均为该 actual ID。

两臂真实 HostConfig 与 run argv 一致：NanoCpus2000000000（2CPU）、Memory／MemorySwap4294967296（4GiB）、PidsLimit512、ShmSize67108864（64MiB）、NetworkMode none、no-new-privileges、CapDrop ALL及固定初始化能力；`/tmp` tmpfs1GiB、agent home tmpfs256MiB／UID-GID54321。主容器 Config.User 为空，root 负责可信初始化；行为 probe 的真实 exec argv 明确 `--user 54321`，其内部 `os.getuid/getgid` 同为54321。没有仅凭主容器 User 把 root 初始化说成 agent 操作，或把 agent 操作说成 root。

两次 Git sanitize 的原始 stdout 与单臂 sanitize facts 一致：HEAD 前后为固定 base、history7454保持、REMOTES0／REFLOG0／UNREACHABLE0、RH2_GIT_SANITIZE_OK=1。原始 trusted init／activation stdout 也与单臂记录逐项一致，activation 无 violations，testbed Python／sys.prefix／CONDA_DEFAULT_ENV 符合固定环境。这里 `RH2_INIT_OK` 是 production 容器初始化，不代表本次运行过项目 `make init` 或正式测试。

修改前，两臂实际 `sha256sum` 均得到原 RDS `a614a137f21dce20445cad98611e578b435d4f09a592ced584d887d9edb9250c` 和原 Neptune `c5bf4a50b5676592daf8df02dbaef2978019b6d04cbbfdceb0387c6acbcfe906`。base probe 继续加载原 RDS SHA；candidate probe 加载 `05e9b6a1d3f57caaeba1a616fa3a1a9529ffa6f6aa6d91be9a5963a239b5171d`，Neptune SHA 两臂不变。实际路径分别为 `/testbed/moto/rds/models.py`、`/testbed/moto/neptune/models.py`，Moto路径 `/testbed/moto/__init__.py`，cwd `/testbed`、home `/home/agent`、Python `/opt/miniconda3/envs/testbed/bin/python`。没有把系统安装的其它 Moto 模块当工作区源码。

原 GPU FrozenPatch 文件仍为 216817B／`6acc1b2d3de238b08780adfb493883abe617aa1c0e1983fdbda9a0bd2fc8405c`；canonical digest 重算为 `sha256:68557bc28b72fb3f45912e70d585b7c296ec1a7d1ec7a6e9eec57ce82f5f40d8`。唯一 entry 是 regular／100644 的 `moto/rds/models.py` modify，完整 base64 解码 **161961B／上述 candidate SHA**，与固定 payload 逐字一致。Docker 调用记录未保存 stdin 内容本身；候选写入后实际导入模块 SHA、原 entry 解码及固定 payload 三者一致，构成内容身份依据。本次没有重写原 FrozenPatch 的 runtime 绑定。

## 两项实际行为与结论范围

两次 agent probe 的内联命令均逐字等于固定 `probe.py` 文本加同一执行前缀。原始 Docker stdout 解析后分别与 `base.json`／`candidate.json` 的 observed 全部相同；probe 捕获调用异常作为真实观察输出，随后入口才比较预期。这不是只接受人工摘要或运行前静态预测。

每臂对 start／delete 分别创建不同的原 Neptune 名称；四项观察都 present_before=true、before_status=available。实际结果为：

| 原名称调用 | base 真实观察 | candidate 真实观察 |
| --- | --- | --- |
| `start_db_cluster("moto6114-neptune-start")` | 返回同 identifier、status started；对象保留，stored status available | `InvalidDBClusterStateFault`，信息为不在 stopped 状态；对象保留，stored status available |
| `delete_db_cluster("moto6114-neptune-delete")` | 返回同 identifier、status available；对象已移除 | `AttributeError`：`'DBCluster' object has no attribute 'deletion_protection'`；对象保留，stored status available |

两次 probe exec 都退出0，表示观察程序完整返回，不表示候选行为通过；两臂 raw_reward 都为 null，result raw_reward_override=null、formal_cpu_accepted=false，observations grading_executed=false、model_attempts0、reference_list_changed=false。这一轮支持“原两条行为正常、精确候选内容在相同条件下分别出现对应异常”的代码行为结论，没有产生正式37参考得分或自主 actor 能力证据。

作者报告 `neptune_name_diagnostic_readback_20261003.md` 实读4261B／`5509ad35aef093c0f3f5ba386d45533ae7ba2f3bc60eb05bd18c92d0b47b95b4`，其行为、模块、UID、镜像、调用数和清理陈述与上述原件一致。旧 GPU FrozenPatch runtime 是 `sha256:43f685f4308354a90d8d88d3a2fd31dcc01bdd41fff3f04210d2668281716e20`，与本次 CPU actual 不同，因此不能称为旧 GPU 原 FP 重grade、覆写旧 raw1或其训练身份。

本次已满足批准范围内的最小 base／实际候选代码行为对照与独立原件读回。它不替代新增材料正式发布、独立绑定身份，以及新版 1F／36P 的必要 noop／gold／wrong_first／实际 Qwen 对照验收；这些剩余事项按已批准范围继续，无新增审批要求。
