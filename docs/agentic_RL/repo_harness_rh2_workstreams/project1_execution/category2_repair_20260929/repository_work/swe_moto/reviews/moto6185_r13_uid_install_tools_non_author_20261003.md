# Moto6185 R13 UID 原安装工具非作者静态窄核

日期：2026-10-03。对象为 tools/moto6185_r13_uid_install_v1 的 uid.py、tasks.json、manifest.json，以及 ignored 证据根中的 launch_moto6185_r13_uid_install_v1.py。审查者不是这些工具的作者，已接触本批私有材料／参考，非公开盲读 solver。

## 结论

**未发现新增工具的确定启动阻断。** 新 UID core 与已审 R18 UID-install core 的执行差异只有固定 R13／单题6185、prepared/output 目录与状态文字；真实 UID54321 的生产 sanitize、init、BASH_ENV 激活、原公开 make init、模块来源检查、完整输出保存和 finally 清理逻辑保持。任务与固定 R13 原消费者、public/base、ENV、registered COPY-only recipe 相容。新的 launcher 使用独立运输回执名，没有此前跨版本回执碰撞。

这是**静态可启动结论，仍须满足原 launcher 的同题 R13 CPU 回收入口**。当前本地指定证据根未见 moto6185-cpu-* 的闭合 invocation／transport receipt／prepared evidence；题主当前 tasks/getmoto__moto-6185/results.json 也仍记 R13 矩阵 pending。本次不能证明这个入口已经具备，不能以旧 prep image 作业、R18 别题、旧 import-only UID 或未来计划替代它。这是工具已有数据条件，不是新增审批闸门。

本工具尚未运行，**没有验证实际 UID 安装成功**，没有新 CC、模型、FrozenPatch、正式评分或 typed-actor／训练资格。COPY 镜像历史构建收据的 image_preparation_only 与 formal_cpu_accepted=false 保留；实际 wheel 对 UID54321 的读取与原 make init 成败，必须在真实运行原件中判断。

## 1. 实际读取与固定字节

仅用本地标准库读／hash／JSON／AST／diff；未导入项目，未执行 Docker、SDK、项目测试、CPU、SSH、远端或模型，未读取在途6114，也未打开私有连接输入。launcher 的连接表达式在静态读回输出中作了遮盖，没有输出 host、key、SSH argv 或原始连接错误。唯一新增文件是本报告，原工具、发布输入、旧报告与证据未改。

| 文件 | 字节 | SHA256 |
| --- | --- | --- |
| manifest.json | 420 | 3b0aecda073d4265a6bfa9e5b264ef677d7b7b0e2863e8144f22337215ce98d7 |
| uid.py | 10688 | ac2cd2a3d8f12183889b2c1f3f57a47bef56ed680e90b16ebbd8dba7a4248ba9 |
| tasks.json | 3698 | c4d46026043fb7440a737774fe7325209a57c78b7abeb41a8f8e3547d263038c |
| launch_moto6185_r13_uid_install_v1.py | 7571 | 8e6467553ea4aa2011661af1323bdeb25d2a9efbdde26214ef76d87fb5531c11 |

三件目录恰好是 manifest 声明集合，两个成员 SHA/bytes 与 manifest 相同。uid.py 和 launcher 均静态 AST 解析成功；本审查没有重新运行 ruff 或工具本身。

对照文件为已审 tools/moto_two_r18_offline_uid_install_v1/uid.py 和 ignored launch_moto_two_r18_offline_uid_install_v1.py。uid.py 差异仅文档头、prepared root 从 moto_r18_offline_v1 切为 moto_r13_v1、独立输出 root、r13 成功状态名、instance choices 缩为6185。launcher 差异仅 fixed release/tool/source SHA和目录、单题 choices、独立 receipt 名、schema/output 名。运输、cpu_slot、摘要捕获、退出／异常处理结构未改。

新 tasks 的6185条目与已审 moto_four_r13_uid_v1/tasks.json 的原6185身份相比，仅 scope 文字及新增 public_install_command='make init' 不同；base/public/ENV/镜像/recipe/模块 pin 均保持。

## 2. R13 来源、原公开安装和必要成员

固定本地 R13 根为 runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe27_pandas_moto_v1，release ID 为 cat2-cpu-r2e089092-swe27-pandas-moto-20261003-v1。实际 manifest 232537字节，SHA256 **3fad18daff8db219294e10cbf08d4424d68cf7000d008bb983cba4bdc427b641**，与 tasks 和 launcher 常量相同。沿用已有 R13 消费审查，只增量核了17件直接相关发布成员的 SHA／size：四个调用模块、bundles_v2/swe_material_revisions、两份 ingest JSONL，以及 recipe/base_identity 和七件环境供应文件；全部与该 manifest 相同，不虚称本轮重审全部发布成员。

| 任务身份 | 固定值 |
| --- | --- |
| task_id | swe_gym_lite::getmoto__moto-6185 |
| public base | dc460a325839bc6797084a54afc297a2c9d87e63 |
| workdir | /testbed |
| public bundle | sha256:2a2ae08fcef35f245257572088bc8f79d3eb0827f8025f358e93764c085e5a15 |
| ENV bundle | sha256:161da515114764dd74ff279cbe8a7aff39dc647b1de2748c6ec85f9f473772b4 |
| 原 public source face | xingyaoww/sweb.eval.x86_64.getmoto_s_moto-6185:latest |
| source manifest | sha256:ade7d85a8ef82a6d87940dd9c8d486e50b27dcc33e968e55f50421adf6864eda |
| source ConfigID | sha256:47443b04543c5fa25c85bb4e86c871f1f98ea0df9e254b2ca8fac9f9bdb19325 |
| 诊断实际 COPY-only ConfigID | sha256:79d39d611186289b10956c2f845af1272218a1f4cf8fc00382c7c6ab4eced35d |
| registered recipe | moto6185-fixed-environment-v1 |

独立对 ingest 的6185 public 和 environment 对象作 canonical JSON SHA256，分别与上述 public／ENV digest 相同。任务声明 environment 对象与固定 environment_recipe.json 完全相同。public 的功能 statement 与 hints 仍是原 DynamoDB issue、/testbed 与 testbed 环境；没有将 derived ID 写回 public face。

原公开 base 的 Makefile 2631字节、SHA256 **6a91d45d9be5d2b15d04c2a48fe2bab6ebc4208e4bb4947a2b4688e47971975c**，init 目标逐行是 pip install -e . 与 pip install -r requirements-dev.txt。新工具调用原 make init，没有改成仅 import、跳过安装、先预装或执行私有测试。现有 public_dev_brief 也沿原公开 testbed 环境使用 python，写原项目安装入口为 make init。

固定模块 moto.dynamodb.models 对应 /testbed/moto/dynamodb/models/__init__.py；其公开 base 原件29890字节，SHA256 **740a35208924fc2a99ab809f2734ef0b258664bbf571a5fdacd0277b379bf74e**，与 tasks.module_source_ref/module_sha256 相同。这是真实原 base 的固定字节，不是候选或测试补丁内容。

## 3. 环境供应及 exact local override

读回固定 source_image_receipt、derived_image_receipt、Dockerfile、wheel_manifest 和三件 wheel 的全部 pin。recipe 的文件摘要、wheel 摘要与长度均匹配；source receipt 实际 source ID、manifest及derived receipt 的 base ID、derived ID与 tasks相同。历史构建 returncode0是供应构建事实，未升级成新开发 UID 安装证明。

| 固定供应文件 | 字节 | SHA256 |
| --- | --- | --- |
| source_image_receipt.json | 765 | a6f559fcd2dc580dc894b0046e6a125416becc2f5d8fe2630831a274382323e0 |
| derived_image_receipt.json | 1439 | 1a187dafc8e123c0573a68b76b8718eda4f9145502d0cd5a957f41d46980fcf1 |
| environment/Dockerfile | 126 | 352caaf2eae8dc6fdb3291e9afaf85281a0b0199d6b3ee091d9e3d3247d44993 |
| environment/wheel_manifest.json | 477 | 660fa7aa83d8c3cedeb5e188ef7a4de0621e6011a37be48958813a6c50425a55 |
| packaging-24.1-py3-none-any.whl | 53985 | 5b8f2217dbdbd2f7f384c41c628544e6d52f2d0f53c6d0c3ea61aa5d1d7ff124 |
| wheel-0.43.0-py3-none-any.whl | 65775 | 55c570405f142630c6b9f72fe09d9b67cf1477fcf543ae5b8dcb1f5b7377da81 |
| setuptools-72.1.0-py3-none-any.whl | 2337965 | 5a03e1860cf56bb6ef48ce186b0e557fdba433237481a9a625176c2831be15d1 |

Dockerfile 只有原 BASE_IMAGE、COPY wheels/ 到 **/opt/rh2/build-wheels/** 和 PIP_NO_INDEX=1/PIP_FIND_LINKS=/opt/rh2/build-wheels，没有 RUN、项目层改动或安装替换。

生产 rollout_spec_from_view 对 SWE public face 返回原 source image、grading_spec=None；本工具先断言这一事实，再独立 image inspect source manifest ref 与 registered actual79d…，检查 source ConfigID/RepoDigests、实际 amd64/linux、derived ID、source层为derived[:-1]、离线ENV。只有真实容器初态 image 使用固定79d…诊断override；没有 source face、公共契约或训练环境登记变更，也没有换用别题79d以外镜像或新R18 release。

本工具不重新构建镜像或 chmod wheel。实际 COPY 文件的 UID可读性必须由运行时原 make init 完整输出判定；静态镜像收据不含新的54321安装结果。若真实安装失败，应保留失败原件并具体定位，不能把已有 root/grader安装或历史 import 通过当代证。

## 4. 原 helper API、身份和资源

实际核的四个发布调用模块摘要如下，与固定 release manifest 相符：

| 模块 | SHA256 |
| --- | --- |
| adapters/slime/prepared_task_face.py | 4bd029be7034ff96dd3d5b7203dac926ad868171ff5b2ce562ef4705558fd799 |
| adapters/slime/replay_grade.py | 67e37a79b0f9feddfcf43a0dff3a8262444b21ac6b2f6a67cc0be2256157b553 |
| adapters/slime/sandbox_profile.py | 313bfd7691c5dca775aa0e9992f13561e20936f062ddfa3d269892b6bf4895ee |
| envpack/materialize.py | 96e7ddf7ad77d1d2b07f2bec234131e5dea22343d4d98a94f80f6a998afd33bc |

AST和必要函数正文表明 load_context、rollout_spec_from_view、default_docker_runner、rollout/grader_profile_from_env、run_git_sanitize、run_trusted_init、run_rollout_activation_check、agent_shell_env 的关键字／返回结构与新调用一致。BASH_ENV_PATH 从 **repoharness2.envpack.materialize** 导入，其实际定义为 /rh2/bash_env，没有此前6114的错误导入路径或不存在的 rollout shm_size_bytes 属性。

profile固定 agent/54321；工具断言2CPU、4GiB、PID512，沿原profile生成run参数、tmpfs/no-new-privileges/init与memory-swap。启动网络明确 none，不运行model relay；用于profile构造的dummy upstream不表示发生模型连接。shm64MiB不是伪读profile不存在字段，工具在真实 inspect中要求 ShmSize=67108864，并连同 NanoCpus=2000000000、Memory=4294967296、PidsLimit=512、NetworkMode=none 和 container.Image记录并精确比较。

顺序是 source/actual inspect→新自有容器→生产 git sanitize核HEAD→生产可信init→原activation脚本写入/root0644→agent_shell_env供HOME与BASH_ENV→生产agent激活检查→实际agent54321原 make init→模块身份导入→实际HostConfig检查。make init 和 identity 的 exec 都显式 user54321、HOME=/home/agent、BASH_ENV=/rh2/bash_env；不是可信root安装。cwd为/testbed；安装后要求UID/GID54321、HOME、解释器在声明prefix下、moto来自/testbed、模块精确路径及740a…模块SHA。

单次 docker 调用的 asyncio timeout仍300秒，安装不是新增长预算或重试。sanitize/init helper各自原timeout参数保留，但外层docker wrapper仍有300秒上限；这只是既有诊断工具边界，不是原grader预算改动。若触及timeout，异常不能视为成功；须以实际运行退出与保留下来的完整调用判断。

## 5. 输出、失败和自有清理

default_docker_runner用communicate读取完整stdout/stderr，无工具自设截断。每次已返回的调用都把argv、真实exit_code、stdout/stderr追加并立即保存到docker_calls.json；安装再把原命令、UID、全输出及RC放入public_development_install。install.exit_code必须0后才进入identity及通过状态。SDK boto3/botocore版本实际捕获，但代码没有把它们硬编码为通过断言；后续原件验收仍必须核实际两者1.35.9，不能把有字段当版本正确。

try内任何异常将status写为failed并重新抛出；finally再核自有容器label为同job后才rm -f，不做全局删除。容器与网络absence均按本job label查询，并保存query RC和实际ID列表；只有两次查询RC0且两类实际列表空才允许最终完成，查询失败不会被当零残留。ownership inspect失败本身被记录；最终absence查询和作业退出仍必须实际检查，不能因记录中有cleanup键就接受。异常或timeout导致的未返回调用不具有完整communicate记录，后续不得声称所有调用闭合或安装已通过。

成功状态明确为r13_identity_activation_import_and_public_install_passed_pending_independent_review，record还写actor_executed=false/model_attempts=0。工具未创建CC、模型请求、FrozenPatch、候选评分或新参考；load_context仅消费固定prepared/private文件，不向模型公开私有字段。

## 6. Launcher条件与验收读回要求

安全launcher先核精确三件工具及本地manifestSHA，tasks release ID/SHA必须同常量；transport阶段远端同名文件只能是这三件，已存在成员必须SHA/bytes相同，最终写444/目录555，禁止覆盖不同字节。独占回执名为 **moto6185_r13_uid_install_tools_transport_receipt.json**；不会回写R18或6114UID工具的回执。

cpu入口要求instance为6185、execute=true、external_release_manifest_sha256同上述R13、该cpu transport回执all_sha256_and_length_match=true、job_returncode=0；从该题闭合CPU原件prepared/replay_summary.json算本地SHA，再传原remote_output对应summary路径。工具再次要求summary处于原moto_r13_v1 package、SHA一致、task_ids仅本题；load_context验证prepared/private与prepared_manifest绑定，再核base/public/ENV和原source face。不能借旧R18已闭合CPU条件启动。

CPU由既有control/cpu_slot.py的run模式、swe_moto package派发，不绕过同仓槽；生成独立moto6185-uid-12hex job及独占output root，output.mkdir(exist_ok=False)，拒绝覆盖旧运行。清除overlay相关环境变量，固定runtime_cpu_v2 Python与R13 PYTHONPATH；invocation写release/tools/summary摘要和安全command，无额外连接参数。运输错误只输出状态／returncode，顶层异常只输出error_type，连接执行输出进入ignored捕获文件，终端不打印host/key/SSHargv或raw连接错误。新的launcher AST与已审R18其余结构一致。

本轮没有可独立读回的6185新闭合CPU prepared入口，也没有该UID-install运行。待同R13入口具备后，该工具静态可启动；正式读回至少核：实际job parent/退出、13次或真实异常分支的调用完整性、原make init全stdout/stderr/RC、生产sanitize/init/activation、实际54321/GID/HOME/cwd/解释器、740a…模块原SHA、SDK1.35.9、实际79d…镜像与HostConfig、删除和两次RC0空absence。之后才可评价本次实际开发安装；这些验收要求不等于额外审批或新的题目断言。

