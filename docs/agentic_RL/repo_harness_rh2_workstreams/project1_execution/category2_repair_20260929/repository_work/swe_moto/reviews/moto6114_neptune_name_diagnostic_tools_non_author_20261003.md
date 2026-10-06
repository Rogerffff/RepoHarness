# Moto6114 Neptune name 诊断工具非作者静态窄核

2026-10-03。结论：**按完整运行包交付时，未发现需要改工具源码的静态阻断；两条既有名称路径、实际观察保存及最终比较边界相容。** 运行前须将 ignored candidate payload 一并放入运行时工具目录，不能仅复制当前四件跟踪文件。未运行本工具，不能把预期异常、两处回归确认或本次 CPU 结果写成已经实测。

## 范围与最终字节

仅读 `tools/moto6114_neptune_name_diagnostic_v1/` 的 manifest/config/diagnostic/probe 和指定 ignored payload，固定 R7 的相关 helper/API，既有 R7 prepared/image 原件，以及实际 GPU FrozenPatch/review diff 的身份与内容。标准库用于读取、哈希、base64 解码、canonical JSON、AST；没有运行项目、SDK、Docker、CPU、模型、远端，没有修改原件、共享代码或既有报告，仅新增本报告。题主报告的 ruff 通过不是本次独立运行结果。审查者已接触私有上下文，非盲 solver；不重复实际 GPU 补丁的完整语义审查。

| 输入 | SHA256 | 字节数 |
| --- | --- | ---: |
| `manifest.json` | `2772408eec3de9501ee20f355bdc154e864a99d1edcb4c9aec955aa0f7e3a2f0` | 667 |
| `config.json` | `65ab13124aa3385583a722fb1ee09cdde11998a04ab5e1853cc0e2e93d5f23b7` | 2243 |
| `diagnostic.py` | `8519ec7f7cf48b793641974b3a892c8776cdd78e36640317ae9f494491af4c6d` | 10792 |
| `probe.py` | `08c81ddbe02ff670980db0ce79301b37ed0bad762ba6aec056b4d22cfa5e1e9f` | 1861 |
| ignored `candidate_rds_models.py` | `05e9b6a1d3f57caaeba1a616fa3a1a9529ffa6f6aa6d91be9a5963a239b5171d` | 161961 |

所有成员实际 SHA/bytes 与 manifest 相符，均为普通、非符号链接文件；三份 Python 字节 AST 可解析。payload 的本地实际来源为 `runs/category2_repair_20260929/moto_cpu_20261003/moto6114_neptune_name_diagnostic_inputs_v1/candidate_rds_models.py`，与 config 的 `candidate_payload_local` 一致，不需要将其加入 Git。

**确定的部署前条件：** `diagnostic.py:28–31` 的目录集合检查和 106 行的 payload 读取均使用运行时 `HERE/candidate_rds_models.py`。故运行包须有 manifest 加四个成员，共五文件，且不能多带 launcher/其他文件；当前跟踪工具目录仅有 manifest/config/diagnostic/probe，单独复制它会在目录断言处失败。把上述已固定 payload 以该文件名一同组装到远端 HERE 就与代码相容。本次没有读到完成的运输原件，不能宣称这一步已经交付；这是已有 manifest 的组装要求，不是要求回写跟踪目录或新增审批。

## R7 与原公开 source 绑定

config 固定 release 为 `cat2-cpu-r2e088-swe12-git-20261003-v1`，本地对应 `runs/category2_repair_20260929/releases_20261003/r2e_088_swe12_git_candidate_v1/` 的 manifest 实际 SHA 为 `f9dfcd16c9c88e4f514512e61781856b7d6f1a71a20b64cd1843d20546c5009b`，相符。

prepared summary 指向既有 `moto6114-cpu-0661259fc3d1/prepared/replay_summary.json`，其回收原件实际 SHA 为 `44ad39c1802736c0080c93849cfefedb4ba6b01dd118f2a938b797ff803f6e3d`；唯一 task 是 `swe_gym_lite::getmoto__moto-6114`。summary 内 prepared manifest pin 与 config 及实际文件均为 `113c26abe818b5ca1a8c738536f76a450ad2cd0ff745f58ec47b6c3d6a5d188b`，host grading artifact 也由这个原 manifest 绑定。运行代码读取固定 summary SHA，再由原 `load_context` 校 prepared rollout/private 文件身份，不重新 prepare 或挑新的消费者。

rollout view 的 public digest 为 `sha256:6c8f45da003f8e8d1e065d1801afa4659c43cbb212e319a5d07a84922af5f0f2`，公开 base 为 `f01709f9ba656e7cf4399bcd1a0a07fd134b0aec`、workdir `/testbed`、source image face 为原 Moto6114 镜像和 manifest。构造 spec 的 `grading_spec=None`；构造这个 spec 不算执行了 actor。

runtime 镜像固定为已 CPU 核过的 `sha256:1d8dded2ee5bbe9275514fdc603116ac9f36da5e30c19b2d4ffcba4d4a9f27d5`。本次只读既有 R7 image inspect 与 gold/wrong_first 的 actual ID 确认 config 引用一致，不机械重读全部 CPU 证据；原独立报告 [moto6114_final_cpu_non_author_20261003.md](moto6114_final_cpu_non_author_20261003.md) SHA 仍为 `338ad830102d02b7241533843ec928032a37bbf07d7f6d0aa3ac725e37d45bcc`。

原 source Config ID 为 `sha256:fefec492f58ed0f8385a7e72234d296bd84d295031ce7e019f63fc33973ec249`，source manifest ref 为 `xingyaoww/sweb.eval.x86_64.getmoto_s_moto-6114@sha256:cb35f7e131f8e46c8a6865e8fb618c09032ce5ee27f1122f79010a7cfae8ef9a`。既有 source 13 层、runtime 14 层，runtime 去末层后逐项等于 source。新工具运行前再独立 inspect 两镜像并核同样的 Config ID/RepoDigests/层前缀和 linux/amd64，随后每臂 inspect 实际容器 Image；没有只用 tag 名推断实际镜像。

## 实际 GPU 单 entry 的绑定和重放边界

config 引用原 `gpu1003-moto6114-qwen36-a1/attempt/frozen/frozen_patch.json`，实际原件 SHA/bytes 为 `6acc1b2d3de238b08780adfb493883abe617aa1c0e1983fdbda9a0bd2fc8405c` / 216817B。独立 canonical digest 为 `sha256:68557bc28b72fb3f45912e70d585b7c296ec1a7d1ec7a6e9eec57ce82f5f40d8`，与 config 相符；GPU job、task、public digest、HEAD 均对应本题。原 baseline manifest 的 canonical digest 为 `sha256:e6a98e5c9c5d41ce34b16b4590f279509977505dacace4bfd4ccc387844ef12f`，与 FrozenPatch 的 baseline 绑定一致。

FrozenPatch 实际只有一个 entry：modify、regular、100644 的 `moto/rds/models.py`。解码 content_b64 后，与 ignored payload **逐字相同**，不是题主重写的近似补丁。原 review diff SHA `bb5eab97577260270def73fc06f8a0aa4917727cb9348afbe871f5905b2eb747` / 6463B 仍匹配；payload 的 Git blob 是该 diff 新 blob `d7ce78554bab93a17b9d784ea8f8e03d012e6e9f`。此前 [Qwen 语义报告](moto6114_qwen_a1_semantics_non_author_20261003.md) SHA `eb30f25349feac4b04d76087e270e76faf318d071647fcdd5a9fd23f7d40c13f` 已核整份 diff hunk 和实际轨迹 Edit 的最终字节，本次不重复该语义审查。

两臂初始化后，工具均先核未改 RDS/Neptune source SHA 分别为 `a614a137f21dce20445cad98611e578b435d4f09a592ced584d887d9edb9250c` / `c5bf4a50b5676592daf8df02dbaef2978019b6d04cbbfdceb0387c6acbcfe906`。candidate 臂仅在自己的新容器中以 stdin 写入上述完整 RDS entry 内容；probe 再读取实际模块路径和源码 SHA，分别要求 base hash / candidate hash、Neptune hash 不变。没有改测试或其他 source entry，也不改共享工作区。

原 GPU FrozenPatch 的 runtime identity 仍是 `sha256:43f685f4308354a90d8d88d3a2fd31dcc01bdd41fff3f04210d2668281716e20`，与本诊断 R7 runtime ID **不同**。本工具做的是相同 CPU 条件下的原源码/候选源码行为对照，不能称为原 FrozenPatch 原环境重 grade 或给原 FP 改绑环境。原 raw reward、FP 元数据、reference、原结果均不回写；诊断每臂 `raw_reward=None` 表示没有评分器，不是把原 GPU reward1 改成 None/0。

## API、UID、profile 与两个 probe

R7 原 `rollout_spec_from_view`、`load_context`、profile factory、`default_docker_runner(input_bytes=...)`、`run_git_sanitize`、`rollout_trusted_init_script`/`run_trusted_init`、`agent_shell_env`、`run_rollout_activation_check(...expected_interpreter_prefix=...)` 与 `PrelaunchReport.to_dict()` 参数/属性均存在且相容。BASH_ENV_PATH 从正确的 `repoharness2.envpack.materialize` 导入。没有访问 rollout profile 不存在的 shm 属性。

工具使用原 production sanitize 和 trusted user/workspace init，将本 prepared view 的激活脚本写入原 BASH_ENV 路径且只读，按原 helper 以 agent 身份核激活/解释器。两臂均在同一个固定 R7 image 上各启动新容器、network none；profile 静态要求2CPU/4GiB/PID512，并从实际容器 HostConfig 核 NanoCpus=2000000000、Memory=4294967296、PidsLimit=512、ShmSize=67108864、NetworkMode=none。probe 本身用 profile.agent_uid 的 docker exec 和 `/home/agent` HOME，回包必须是实际 UID/GID54321、cwd `/testbed`、testbed python 绝对路径、工作区 Moto/RDS/Neptune 模块及固定 SHA。每个 docker 调用有300秒上限；原 helper 自己的 profile 超时保留，但外层调用会把单次等待截到300秒，这是一条诊断期限，不能称为重跑正式评分预算。

`probe.py:13–28` 在原 RDS backend 的同 account/region `123456789012/us-east-1` 通过其 Neptune backend 正常创建独立名称对象，明确 `storage_encrypted='false'`，再调用 **RDS façade** 的原名称路径：

| probe | 初态与操作 | base 预期 / candidate 预期（尚未实测） |
| --- | --- | --- |
| start | 新建 `moto6114-neptune-start`，记录 available/存在，RDS `start_db_cluster(name)` | base 返回 started、对象保留；candidate 抛 InvalidDBClusterStateFault、对象保留 |
| delete | 另建 `moto6114-neptune-delete`，记录 available/存在，RDS `delete_db_cluster(name)`，无 snapshot | base 返回对象并移除；candidate 抛 AttributeError、对象保留 |

两条调用分别使用不同对象，每个新容器里独立 import/backend 初始化；不是单独 Neptune 客户端的未改路径。没有 ARN 扩展、AWS 外部调用、模型、make init、FrozenPatch 导出、grader 或训练操作。init 指原 trusted init helper，不能把它表述为本次重新完成了项目 `make init`。本诊断只借既有 R7 环境验证做这两个定向行为对照。

## 观察、失败与清理判定

probe 捕获目标调用的实际 `Exception`，记录 returned identifier/status 或真实 exception type/message、操作前状态/是否存在、操作后是否存在/存储状态。它没有先断言预期异常或把预期字符串当调用结果。容器外先保存完整 docker 调用 stdout/stderr/exit 和 arm observed data，再检查 UID、模块来源等前置事实。

base/candidate 容器名以唯一 job 加臂名分别生成，job regex 约束为 `moto6114-neptune-` 加12位 hex，输出目录 `exist_ok=False`。每臂 finally 先 inspect 同名对象，**确认 `rh2.run_id` 等于本 job 后才 rm -f**；不删除标签不符的对象。不论 body 成功还是失败都会进入 finally。之后查询本 job 标签的容器和网络，要求两项 query RC 都为0、stdout 都为空；查询失败不当零残留。每个 arm JSON 保存状态、实际 probe、remove RC 和 cleanup 查询，全部 docker 调用另存 full calls。

全部两臂结束并清理之后，工具才写 `observations.json` 并比较实际两条 base/candidate 行为；所有前置状态、原返回、候选异常类型和对象保留条件满足后，才写最终 `two_original_name_delegation_regressions_confirmed`。没有与预期相符就预写 confirmed 的路径。意外创建/导入失败、UID/模块/profile 不符、probe 非0、行为不符或清理问题都会非零结束且不产生成功 result，不自动重跑。

单个 arm 的 `observations_returned` 在 finally 之前赋值；若随后清理失败，该 arm 文件可仍带此状态。实际验收必须同时核 job exit、最终 result、完整 calls、两臂 cleanup 和真实 observed cases，不能仅以 arm 状态或文件存在判断 confirmed。失败分支如 ownership inspect 找不到对象，仍需成功的自有双查询才能确认无残留；本报告不凭未来日志缺项推断清理成功。

## 启动结论与未完成项

源码/API、固定来源、payload/FP 内容、两条原名称条件、两容器隔离、先观察后比较、只清理自有对象及无重 grade 边界均未发现需要修代码才能启动的问题。**完整五件运行包的运输组装仍是确定启动前条件**；source/release/prepared 运行时再次校验、profile/UID/模块来源及两条真实行为、完整清理仍待本次 CPU 原件。

目前只有静态检查，没有本工具 CPU confirmed 结果。后续报告应把这两个实际诊断观察与原 GPU raw1/安装修复重 grade 分别记录；不新增公共参考/评分器、不改原 FP 身份、不授予新的 actor、typed actor 或训练资格。既有 R7 CPU 报告和 GPU 语义报告保持原件，本报告没有展开其他功能回归或增加审批流程。
