# Moto6114 R19 UID安装工具：非作者增量静态窄核

日期：2026-10-03。结论：**首次发现的 launcher 回执路径冲突已按唯一文件名改动修复；最终所核字节无尚存启动前静态阻断，可以进入既定 CPU 槽位执行。** 本工具尚未运输／运行；CPU `1d8dd…a9f27d5` 中真实开发 UID54321 能否成功执行原 `make init`，仍须本次实际原件证明。旧 candidate安装0、旧UID import成功、public未改和镜像身份相同，都不能替代这个新安装补查。

## 范围和字节身份

只用本地标准库文本、JSON、SHA-256、AST、逐字段和源码diff核对。未执行／导入项目、SDK、测试、Docker、CPU、CC、模型或SSH；未读其它在途作业。仅新增本报告，不改工具、旧报告、固定输入、发布或证据。审查者已接触私有材料／gold，不是公开盲读 solver。

增量对照已审 `tools/moto_two_r18_offline_uid_install_v1/uid.py` 和 launcher；R18 helper范围引用 [既有R18工具报告](moto_two_r18_offline_tools_non_author_20261003.md)。R19 release、默认prepare、new37 consumer和CPU供应身份引用并核对本次已固定 [R19四臂工具报告](moto6114_r19_matrix_tools_non_author_20261003.md)，不重复题级测试语义或旧运行结果审查。

| 文件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| `tools/moto6114_r19_uid_install_v1/manifest.json` | 425 | `991c15feb5f8e4145f04c38b12bc82c0cf8566aefa6f4505319373582909ec28` |
| `uid.py` | 10692 | `f32a8df126bda05584e6fd8cb8fdb24f88d5e135a9cbd1657bd1452c7021f0b9` |
| `tasks.json` | 2731 | `7f414f603f4ebcee9fe439f7baa8edc311a1759ca62c889e0009ff18ff5bfb22` |
| 最终 ignored `launch_moto6114_r19_uid_install_v1.py` | 7573 | `13f017e3805e16d63d54f229fb034cabaaaf42739176046fc36278f76a84f73f` |

目录精确三件，manifest列举两成员SHA／bytes匹配且非symlink；uid／最终launcher AST可解析。再次核工具三件未因修launcher发生变化。

## 首次阻断及最小修复核验

首次 launcher7581B、SHA `a8ca5bf75ce1f927d1eac16b900579e954e448be256d023c4a136cacbc38f980` 仍使用 `LOCAL / 'moto_two_r18_offline_uid_install_tools_transport_receipt.json'`。其逻辑在该文件已存在时要求旧JSON等于新运输receipt。本地该旧回执已存在，151B、SHA `fb99433aed9d3919bc837e82d9de53f36e75751d0a4af75de43cd565bf2faa8f`，其中tools manifest是旧R18 `7761a5da501bdc76aaf804cc6a05ac9f3b0c1e0e4193f9248670d98c0cd41560`；与新R19 `991c15…90ec28` 不同。因此原launcher会在运输核验后、起UID作业前确定assert失败。这是具体编排阻断，不是UID安装失败样本。

题主只将新launcher回执名改为 `moto6114_r19_uid_install_tools_transport_receipt.json`。独立核最终SHA／7573B，只有一次新文件名字节；把它反向换回旧名字得到7581B及上述首次SHA，证明唯一差异为这8B缩短。旧回执SHA／151B未变，新回执当前尚不存在。**该静态阻断已关闭，未通过删除／改写历史回执规避问题。**

## 增量、R19 prepare 和供应身份

uid.py相对已审R18版本只改标题、单6114 choices、R19 prepared／输出根和结果状态文字；安装、identity代码、production helpers、资源限额、Docker调用捕获和finally清理完全保持。新tasks固定release `cat2-cpu-r2e093-swe40-pyd6283-moto6114-20261003-v1`、manifest `2cfdd9b4f1134c0915346b727b729665482c4c1121b550764833f16f2982402e`、TID `swe_gym_lite::getmoto__moto-6114`。

base `f01709f9ba656e7cf4399bcd1a0a07fd134b0aec`、public `sha256:6c8f45da003f8e8d1e065d1801afa4659c43cbb212e319a5d07a84922af5f0f2`、新ENV `sha256:941bebb539b3974ff894822f9920fdd07227f6a8cf08eaa5c31173f90ea206b2` 均与R19 matrix expected实际字段相同。原public actor image仍 `xingyaoww/sweb.eval.x86_64.getmoto_s_moto-6114:latest`；工具构造原rollout spec，要求其原source／base／public／ENV及 `grading_spec is None`，随后仅在实际容器供应上使用明确CPU ID。

tasks环境的runtime／derived `sha256:1d8dded2ee5bbe9275514fdc603116ac9f36da5e30c19b2d4ffcba4d4a9f27d5`、source ConfigID `sha256:fefec492f58ed0f8385a7e72234d296bd84d295031ce7e019f63fc33973ec249`、source manifest `cb35f7…e8ef9a`、recipe `moto6114_install_wave1_copy_only_20261003`、三件wheel SHA／bytes及两个收据SHA，逐字段与已审CPU image_recipe_binding相同。source receipt SHA `07d55cf5cbe3061449ad69794ddd9735ce743a7479b5294e48001892f539fff0`、derived receipt SHA `497c0736359dd7964b6db8abaaa26fd4716f366868001ab298459b6da4c8cf47` 沿用真实CPU供应，不混GPU43f／613。

运行前uid工具将inspect固定source manifest和CPU actual ID，要求来源ID／RepoDigest正确、derived actualID与task一致、amd64/linux、来源层前缀全部保留且仅多1层，以及原离线PIP ENV。tasks三wheel在本工具中是供应身份元数据，uid.py不单独遍历wheel或stat每个文件；这里的必要证明是**真实UID下原make init实际执行结果**，不是再把元数据写成UID可读／安装成功。

原公开RDS源码 `runs/swegym_quality_batch04_20260921_v1/public/getmoto__moto-6114/base/moto/rds/models.py` 为160973B、SHA `a614a137f21dce20445cad98611e578b435d4f09a592ced584d887d9edb9250c`，与tasks module pin匹配。原base Makefile init第17–19行确实为 `pip install -e .` 和 `pip install -r requirements-dev.txt`；原public_dev_brief也保留 `make init`。没有引入私有新37测试或替代项目安装命令。

summary必须位于R19 matrix输出 `moto6114_r19_v1` 下、SHA等于launcher从闭合原件计算的值、单题TID相同；load_context再核manifest／public／private绑定。不会复用旧R7／R18 prepared的ENV条件，尽管base及公开功能未改。输出另建 `moto6114_r19_uid_install_v1/<job>`，`exist_ok=False`，保留旧证据。

## 原 helper、真实UID安装和捕获

已对照固定R19实际源码：`BASH_ENV_PATH` 正确来自 `repoharness2.envpack.materialize`（`/rh2/bash_env`）；`rollout_spec_from_view`、`load_context`、profile、agent_shell_env、sanitize/init/activation helpers及 default_docker_runner 的签名与调用相容。没有恢复历史错误import或访问rollout不存在的shm属性。

实际流程为受限network-none新容器→production Git sanitize且HEAD等于本base→原trusted init/chown→写入原激活文件0644→原agent activation检查→**UID54321、HOME/BASH_ENV及激活后的shell执行 `cd /testbed && PYTHONDONTWRITEBYTECODE=1 make init`**→工作区module/import/SDK身份→实际container inspect。profile固定agent/54321，无agent UID/user环境旋钮；工具没有以root安装或用candidate54322代替开发用户。资源仍2CPU/4GiB/PID512，单Docker调用300秒上限；最终inspect明确要求shm64MiB、network none和CPU actual ID。

原公开make init从任务字段精确要求，不改pip参数、不注入私有测试、不预先安装、不修改评分脚本／testpatch／预算。每个已返回Docker调用都完整保存argv、stdout、stderr、exit_code至 `docker_calls.json`，安装同样另存 `public_development_install` 的实际rc／全stdout/stderr／UID字段，只有安装0才继续后续身份成功检查。

随后真实agent import／hash检查uid=gid=54321、cwd `/testbed`、HOME `/home/agent`、python位于原expected testbed前缀、Moto来自工作区、RDS实际module精确路径 `/testbed/moto/rds/models.py`及上述原base SHA；同时记录boto3/botocore版本。SDK版本在这里是实际记录而非自动assert1.35.9，验收时仍须读实际输出。状态 `r19_identity_activation_import_and_public_install_passed_pending_independent_review` 仅在上述检查完成后设置；静态不把该字面状态当实际运行事实。

异常保留类型／failed并重新抛出，仍进入finally。若单次调用超时，外层wait_for可能没有返回完整调用结果，不能将缺少stdout伪写为空输出／成功；须保留父job、错误／现有docker_calls和清理原件。若安装返回非零，其完整返回输出先保存在calls及record，由finally落result；不通过只读import或旧安装记录绕过失败。

## 自有清理和安全launcher

finally重新inspect本次唯一容器名，存在时先核 `rh2.run_id` 等于本job，再删除并要求rm0；不碰其它归属对象。inspect失败另记rc，之后按本job标签独立查询容器／网络，将两次rc／列表保存result；两个查询必须rc0且stdout空，失败不算零残留。本流程没有新增relay/network服务，也没有全局清理。未确认归属时不会删除，rm或query失败会阻止正常收口；实际所有返回调用及最终清理仍须原件核验。

修后launcher的release／工具manifest／路径／解释器／输出目录与工具一致。要求闭合CPUjob的instance匹配、execute=true、cpu_inv的external release SHA精确等于R19、transport receipt全SHA／bytes匹配且父job0；从本地该CPU原件计算prepared summary SHA，再使用其remote_output派生路径。它只借用已闭合prepared条件，不把CPU report或旧candidate安装当UID安装证明。

运输前本地三文件集合／SHA／bytes核对；远端错字节不覆盖，落地逐文件非symlink／SHA／bytes并chmod文件0444目录0555；**修后独占R19 transport receipt**存在才要求同内容。经既有 `cpu_slot.py --mode run --package swe_moto` 起新uid job、固定R19PYTHONPATH并清除overlay。连接输出capture，运行stdout/stderr写本地自有文件；用户只收到中性job/运输receipt/rc或异常类型，不打印host/key/SSHargv/raw连接错误。未执行launcher。

## 最终结论与未完成项

唯一已证实静态阻断是首次launcher复用旧R18回执路径，已按最终SHA关闭；UID脚本和修后launcher无尚存启动前静态阻断。可启动此次实际UID安装补查，不需再次题级语义审查或新审批。

仍须独立运输／原件读回：R19 prepared／CPU actualID、sanitize/init/activation事实、真实UID/GID和模块SHA／SDK、**make init完整stdout/stderr及真实退出0**、实际资源/networknone、finally归属核验/rm0/两次查询0空、父job终局。若GPU wheel权限问题或本CPU开发UID权限仍导致安装失败，应如实记录环境缺项，不能基于旧raw／candidate得分推广模型失败。

本工具无CC／模型／FrozenPatch／grader，`actor_executed=false`、model_attempts0；不授予真实CC开发证明或typed训练资格，更不代表新37四臂已评分／通过。后续验收只补这里缺失的实际安装/身份证据，保留已固定旧证据和结论。
