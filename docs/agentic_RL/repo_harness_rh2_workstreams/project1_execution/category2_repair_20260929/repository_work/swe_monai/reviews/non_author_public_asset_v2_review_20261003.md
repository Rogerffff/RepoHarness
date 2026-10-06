# MONAI6975 资产准备 v2：非作者增量核查

2026-10-03 / Codex（GPT-6.1 Sol / high，非脚本作者）。仅核v1已发生失败的归因，以及v2拆分身份探针／清理状态的增量；不重查不变的资产来源、旧3715或6975原公开actor。上下文已包括v1报告、作者说明及实际准备日志，不是fresh公开读者。

**结论：v1是准备探针的Git所有权检查失败，没有任务评分失败或资产损坏证据；v2增量静态核查未发现阻断本次准备复验的问题。** v2实际结果尚未到达，不能认定派生准备成功、actor开发通过或6975可进入探针。本轮只读本地，未SSH、Docker、运行CPU/GPU或修改共用文件；仅新增本报告。

## 1. 保留版本与实际失败

[旧资产报告](non_author_public_asset_review_20261003.md)原件SHA仍为 `9c4f60693ace670ef80406e72b2dea4e98a16b51e7cd4e21185342d65a9c3ea9`；[3715报告](non_author_cpu_review_20261003.md)原件SHA仍为 `e3d0000d81bc147a8a7acf490e821615a5f162470bf3651cd41f8dbf83534913`，未覆盖。旧报告对“第一次busy75未执行”的判断继续属于那次申请；以下是随后独立执行作业，不回写旧状态。

v1运行作业 `monai-6975-public-asset-image-20261003-8e8b9cff` 的 [preparation原件](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-public-asset-image-20261003-8e8b9cff/preparation.json) SHA为 `f8dc87e5315b0f35a8b26d4b0f697f6c3fabd4935e1adf051902dbf08893822d`。本人核其六步日志SHA全部一致，并直接读build／source_identity／base和派生inspect／container inspect／cleanup日志：

| 层级 | 原件事实 | 判断 |
| --- | --- | --- |
| build | RC0；[build.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-public-asset-image-20261003-8e8b9cff/build.log)只有固定FROM和唯一COPY；新增image ID `61e92c506f476f55bce4cf09085e38d9aced51906cacd648ebe60568f333143c` | COPY已实际完成，不是build失败 |
| 源层／配置 | 派生13个源层前缀相同，仅多1层；Config只差Labels及Image字段 | 与未修改代码／依赖／运行配置的COPY配方相符；不把镜像初态当pristine Git base |
| 身份容器 | 实际inspect为UID54321:54321、2CPU／4GiB／PID512、network none，实际image为该派生ID | 失败发生在非root准备探针中，尚未经过正式actor初始化 |
| source_identity | Docker启动命令RC1；其内部Git命令RC128 | 原始输出不是pytest／MONAI功能失败，详下 |
| cleanup | rm_rc0／query_rc0／remaining空，query日志空 | 已正常删除身份容器；派生image留作产物，不声称Docker image已删除 |
| 外层 | [完成snapshot](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-public-asset-image-20261003-8e8b9cff.snapshot-1785c953.json)为finished／returncode1／launcher exit1 | 失败如实保留，没有误记准备成功 |

[source_identity.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_monai/cpu_c_20261003/monai-6975-public-asset-image-20261003-8e8b9cff/source_identity.log) SHA为 `1a0f34167228d8d617cf4c4c5e54ba006ef39e2b2d72425ab8d692d8f401ad76`，明确出现：

```text
fatal: detected dubious ownership in repository at '/testbed'
subprocess.CalledProcessError: Command '['git', '-c', 'safe.directory=/testbed', 'rev-parse', 'HEAD']' returned non-zero exit status 128.
```

因此可证的直接原因是**该镜像在非root准备probe中拒绝这次Git所有权检查，命令行safe.directory设置未使它通过**。原件没有Git版本输出，本轮不把具体版本原因或“选项语法不支持”当成已证事实。准备probe不是正式actor：没有可信初始化修改Git树归属，不能用这次RC128否定原actor的已有Git开发能力。

v1在构造打印JSON时才执行Git；表达式求值顺序可推知此前资产读字节与NiBabel载图没有抛异常，但整份身份JSON未输出，故不把这个推导替代完整非root资产／13源码SHA验收。`status=stopped_needs_diagnosis`、actor_verified／formal_acceptance_passed仍false，没有新ledger或任务reward；没有给6975记一次任务失败分。

## 2. v2实际修改与不变范围

[新脚本](../cpu_prepare_6975_public_asset_v2.py) SHA为 `b7084603b80986049bedd35ed5173f9e4c242409e6b351d3eb81afaea9701955`。本人读v1→v2完整diff及v2全文，用AST仅核语法；未导入或运行脚本。

不变部分逐文本核过：资产SHA、固定source manifest、base commit、真实原actor缺图触发、base／actor receipt身份、唯一COPY Dockerfile、build标签及网络参数、原关键13文件SHA集合与候选未验收声明保持。没有增加资产下载、RUN、pip／conda、Git配置写入、chown/chmod源码或源码／题面补丁；输出仍限制在本包新outputs目录。

身份探针分成两条：

- **独立root Git身份**：新增 `repository_git_identity`，同一派生image ID，显式root0:0、network none、2CPU／4GiB／PID512、唯一`-git`名称和同job标签，Python `-I -B`，120s普通命令期限。只运行`git rev-parse HEAD`和`git status --porcelain`，核UID0、固定base HEAD及原镜像porcelain，不写safe.directory例外，不改变镜像权限。Git status可能刷新临时容器内index；没有卷挂载或commit该容器，不会回写派生image／原source。此探针不证明actor开发能力。
- **独立非root文件身份**：保留UID54321:54321，删除Git调用，仅核解释器实际路径、资产可读／SHA／NiBabel形状及13关键文件SHA；实际container inspect继续核image、User、2CPU／4GiB／PID512／network。启动期限仍600s，不额外安装任何包。

这两条在同一固定派生ID上互补，不把root可读替代非root可读；与“保持原Git HEAD／已有requirements-dev初态、恢复公开图像”目标一致。source/root Git凭据不是solver材料，实际公开开发命令仍需经过正式actor初始化后补验。此阶段只能说探针有界配置已实现，新增root容器的实际HostConfig尚无运行原件；build daemon本身未增加CPU／内存上限，旧报告的资源边界保留。

## 3. 清理与状态增量

v1曾在finally之前写prepared；v2只有身份全部核过才写 `image_identity_verified_cleanup_pending`，**仅在清理全成功之后转为** `image_prepared_not_task_accepted`。

finally先按`rh2.run_id=本job`查询所有容器，覆盖root `-git`容器及非root身份容器；初次查询非零即明确unknown。容器ID需符合12–64位十六进制，rm只针对这次查询的ID；然后再查询同job标签，要求rm／queryRC全0且无残留。root容器正常`--rm`后已不在列表时，脚本构造一个“无对象需rm”的RC0记录；这不是实际删除命令已执行的证据，但随后的实查询仍必须成功并为空。

清理子命令抛异常／timeout或残留会置 `stopped_needs_diagnosis`、保存cleanup_error并抛出外层非零；没有完成查询时cleanup为 `confirmed=false, remaining=null`，不把未知空列表化。若已有实际查询结果但它非零，字段仍保留真实RC，再以status/error说明失败。最终保存finished_at。这个增量关闭旧报告关于**正常进入cleanup后**“超时可能无最终记录、status仍prepared”的具体问题；磁盘保存失败或stop_child自身异常等未实测分支不被称为全面故障注入验收。

两个容器都有本job标签，名称独立，不按共享包名批量删除；新image／build cache继续保留为产物。构建期间无网络／模型调用，清理范围未扩大到其它作业。正常结果的后续consumer仍须合看outer RC0、prepared状态、cleanup.rm_rc／query_rc0、remaining空及日志，不能放宽为“有status就通过”。本轮没有实际清理异常测试或真实v2清理记录，以上是源码控制流核查。

## 4. 本次结论与后续核查边界

v2处理的是**准备probe的Git调用身份与失败归档**，没有改变公开图像内容、任务源码／测试／依赖语义或原有Git安全政策，未发现需先修的增量阻断。允许继续既有授权的v2准备复验；本报告不代替它的实测结果。

待实际v2输出到达，只补新root Git身份、非root读图与13SHA、派生ID／单COPY层、两个容器清理及外层退出。然后按旧报告保留的缺口继续原公开LoadImaged／RandAffined直调与Dataset、环境材料版本和正式参考验收。既有资产SHA／原actor缺图与3715验收按适用版本复用，不要求重跑；旧v1失败原件保留，不能静默改成v2通过。
