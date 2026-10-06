# Moto 四题 R13 UID 工具：非作者静态窄核

日期：2026-10-03。结论：**原固定版本有一处确定的启动阻断；题主最小修复后，静态阻断已关闭，当前固定字节可启动 UID 补查。** 本报告不宣称运行通过。UID 工具尚无本次运行原件可验，也不执行 CC、模型、freeze 或 grader，不能授予训练的 typed-actor 资格。

## 范围与字节

审查者不是工具作者；已接触 Moto 私有审查上下文，不是公开材料盲读 solver。本次只读取 `tools/moto_four_r13_uid_v1/{uid.py,tasks.json,manifest.json}`、固定 R13 的对应 helper 源码和 manifest、既已审的四题矩阵输入身份，以及原公开 bundle、base identity、指定模块原件。只做本地文本、标准库 JSON/哈希和 AST 静态核查，没有导入/运行项目、SDK、Docker、测试或模型，没有连接远端。只新增本报告，不改工具、共享实现、冻结输入、旧报告或固定请求。

首次读取的 manifest SHA 是 `1cc14497702917868a87f0ede17968e2dc333f9c452b02326dbe0087e2715d83`，`uid.py` SHA 是 `25d8cd2c19782c123fb25807fb896754e66573597f2da8c7c04e18ab1185bbeb`（10122 bytes）。首次三件的 SHA/bytes 与 manifest 全部相符，问题在源码 API 使用，不能由字节匹配免除。

题主修复后独立读回的当前固定字节如下；目录文件集合精确匹配、成员不是符号链接、manifest 成员 SHA/bytes 相符，`ast.parse` 成功：

| 文件 | SHA-256 | bytes |
| --- | --- | ---: |
| `manifest.json` | `c4b77468ff9d75e273499de6e88e4ff67519627b7a0042f7c590190fce0c310c` | 436 |
| `uid.py` | `976cd4a07ca4e12ce8d57bf16fb2e81d634bb514b7094078d47c5c1b64ea460c` | 10079 |
| `tasks.json` | `bbd51c3771231ac087348aaee96ccd306ebe52ffe0bbdca8ee5959715108eda8` | 10107 |

本结论只适用于上表修后字节。题主告知 UID 包尚未运输/执行；本审查也没有其运行证据。

## 已关闭的启动阻断

首次 `uid.py:60` 在调用 `rollout_profile_from_env` 后比较 `profile.shm_size_bytes == 64 * 1024**2`。固定 R13 `sandbox_profile.py:319` 的 `RolloutSandboxProfile` 没有该字段、属性、方法或父类；`shm_size_bytes` 是另一类 `GraderSandboxProfile` 的字段。这会在正常 2 CPU/4 GiB/PID 512 profile 下报 `AttributeError`，发生在 `load_context` 和 Docker 创建之前。已向题主具体反馈，未代其修改。

最小修复只删除资源断言末尾的 ` and profile.shm_size_bytes == 64 * 1024**2`，保留 rollout profile 的 CPU、memory、PID 比较，以及后文实际容器 `HostConfig.ShmSize == 64 MiB` 的检查。用当前文件恢复这唯一 43 bytes 的删除后，重算 SHA 恰好等于首次固定的 `25d8cd…5bbeb`；源码 unified diff 只有这一行。将当前 manifest 的 uid SHA/bytes 恢复为初值后，其 SHA 也恰好等于原固定的 `1cc144…15d83`，`tasks.json` 字节未变。因此确定这是唯一源码修改及对应 manifest 更新，不涉及 R13 profile 或公共契约。**该静态阻断现已关闭；不等于容器 shm 实测通过。**

## 固定 R13 与四题公开来源

配置绑定 `cat2-cpu-r2e089092-swe27-pandas-moto-20261003-v1`，release manifest SHA `3fad18daff8db219294e10cbf08d4424d68cf7000d008bb983cba4bdc427b641` 与本地固定原件相符。对应 `sandbox_profile.py`、`prepared_task_face.py`、`replay_grade.py`、`envpack/materialize.py` 的字节仍与该 release manifest 相符。完整矩阵消费身份及 exact local override 来源参见既有 `reviews/moto_four_r13_matrix_tools_non_author_20261003.md`，本次没有重审断言语义。

四题 task ID、base、public digest、environment package digest、original actor image、runtime image ID 和 recipe 均等于既已审的 R13 矩阵输入。原 public bundle 的 canonical digest 与 UID 配置相符，原 public 和 `base_identity.json` 的 instance/base 与该题配置相符。模块原件来自三题 batch03 和 7584 的 batch02 **公开 base**，不是私有修复或控制臂；下表 SHA/bytes 已独立读取计算：

| 题 | 原公开 base 模块 | SHA-256 | bytes |
| --- | --- | --- | ---: |
| 5960 | `moto/dynamodb/models/__init__.py` | `fba195aa3985edf3616237b965aefae6ea6845c9d2591f3d814d094dd70882fc` | 29677 |
| 6408 | `moto/ecr/models.py` | `4df8182f9651cc5ef40ecac5defd993da7e9277e241de403b189c9b41658dc70` | 40991 |
| 6185 | `moto/dynamodb/models/__init__.py` | `740a35208924fc2a99ab809f2734ef0b258664bbf571a5fdacd0277b379bf74e` | 29890 |
| 7584 | `moto/sns/models.py` | `8d74faa42da7fe740e62c650b43259afda89ccf29a964852846bba1fa9e84fe2` | 44621 |

5960/6408/6185 的 `module_source_ref` 是 `runs/swegym_quality_batch03_20260921_v1/public/getmoto__moto-N/base/` 下对应路径；7584 是 `runs/swegym_quality_batch02_20260921_v1/public/getmoto__moto-7584/base/` 下对应路径。模块 import 名与上述文件布局一致。

prepared summary 必须位于本包 `packages/swe_moto/moto_r13_v1` 的目录范围，且等于调用方提供的 summary SHA；其中 task IDs 必须只含当前一题。原 `load_context` 校验 prepared manifest 及 public/host private 工件关联摘要；随后工具核 base、public digest、environment digest、source actor image 和 `grading_spec is None`。这些比较把本次诊断绑定到固定 R13 的该题新输入，不能用另一题或旧 environment package 顶替。summary 与运输字节、实际 prepared 目录需在运行原件中对账，本次没有伪造或运行 prepared。

## 原 helper、资源与 image override

`BASH_ENV_PATH` 正确从固定 `repoharness2.envpack.materialize` 导入，定义为 `/rh2/bash_env`。`rollout_spec_from_view`、`load_context`、`agent_shell_env`、`default_docker_runner`、`rollout_trusted_init_script`、`run_git_sanitize`、`run_trusted_init`、`run_rollout_activation_check` 和 `PrelaunchReport.to_dict` 在固定 R13 中存在，参数和返回属性与本工具调用相符。

工具构造原 rollout profile（agent/54321），核 2 CPU、4 GiB、PID 512；原 `docker_run_args` 提供实际资源参数、可信初始化 capabilities、no-new-privileges、tmpfs 等。容器以 **network none** 创建，原 root sanitize 检查 Git 自证并核 HEAD_AFTER 为该题 base；原 trusted init 建立 UID/GID、工作区和 `/rh2` 目录；root 写原 spec 激活脚本并 chmod 0644，然后用原 agent shell env 和原 activation helper 核解释器前缀。

工作区 import 以 UID 54321 和 HOME `/home/agent` 起非交互 bash，`cd /testbed` 后用激活的 `python` 导入 Moto、boto3、botocore 和指定模块。工具要求 UID/GID 54321、cwd `/testbed`、HOME 正确、解释器在原 spec 声明前缀内、Moto 在 `/testbed/`、指定模块精确来自 `/testbed/<module_rel>`，并核文件 SHA 为公开 base 的固定值。它记录 `sys.prefix` 和 SDK 版本，但没有额外固定 boto3/botocore 版本断言，不能跨题称为 6114 的 SDK 1.35.9 已验。实际 inspect 继续核 NanoCpus=2e9、Memory=4 GiB、PidsLimit=512、ShmSize=64 MiB、NetworkMode=none 及容器 Image ID。

镜像诊断 override 明确为：5960 使用 source config ID `sha256:c67dbd356fcaa937ebff4b3fe0d78e4ea78211888233a4e5f07da95eddfe079d`；6408 使用 source config ID `sha256:a0071858b0bb3a9c316e3c75dd49e9a3a2f8136f7bb4213e1210b44b7de2e689`；6185 使用登记 COPY-only derived ID `sha256:79d39d611186289b10956c2f845af1272218a1f4cf8fc00382c7c6ab4eced35d`；7584 使用登记 COPY-only derived ID `sha256:990e0e91a190f85426e6900828cf758c30f389c927f6c1d0cd1ed8c68b902f96`。工具 inspect source manifest 引用并核 source config ID/RepoDigests、actual ID/amd64/linux；派生题另核登记 ID、来源层加一层及离线 wheel 环境，来源题要求 actual ID 等于 source ID。

public source face 保持原样：构造的 spec 仍是原 source image，没有 overlay 或私有 grading spec；实际 UID 容器显式使用已登记的诊断 ID，并同时记录 `original_actor_image` 和 `runtime_image_id`。这是限定的 UID/激活/import 补查，尤其 6185/7584 的 COPY-only 诊断容器结果不能直接冒充真实 source actor 全链路结果。代码不启动代理或模型服务，不做 CC、baseline census、freeze、grader 或 a2g，明确 `actor_executed=false`、`model_attempts=0`。`time_budget_seconds=300` 构造 spec 也不表示运行了 300 秒 actor；docker 包装调用每次最多 300 秒，生产 sanitize/init/activation helper 原有 timeout 仍按 API 传入，实际较长 helper 调用会受该外层上限约束。

## 所有权、失败与验收边界

job 限定为该题 `motoN-uid-<12hex>`，结果目录拒绝复用已存在路径，容器名字及唯一 owner label 由该 job 派生。finally 先 inspect 该名字并核 `Config.Labels.rh2.run_id == job`，只有匹配才 `rm -f`，不会对标签不匹配的对象删除；没有全局 prune，也不删 source/derived image 或外部网络。工具没有创建网络，最后仅按自有 label 查询容器与网络。两项 query 退出码必须均为 0 且 stdout 均为空；非零 query 不会被当成零残留。

失败会保留已返回 Docker 调用的 argv/exit/stdout/stderr，并抛错退出；ownership inspect 不成功时记录其 rc，不冒称 remove 成功。超时、标签不匹配或删除失败也不能得到正常终结。一个需要验收读回的细节是：`result.json` 在最终双 query 断言前写入，cleanup 失败时可能仍保留较早的 `status=...passed_pending_independent_review`，但其 query rc/残留字段失败且进程随后非零、终结 footer 不会正常打印。**必须合并进程退出码、原调用、footer 和 cleanup 字段判断，不能只接收 status 字符串。** 这是当前代码已 fail closed 的读回边界，本次不要求改状态协议。

修后未发现其他具体工具阻断，可以启动固定 UID 包。实际 UID、激活、模块来源/版本、HostConfig、删除和自有双资源零残留，仍须本次运行原件证明；静态 API 相容不表示这些检查已通过。按交接，6408 三次入槽均返回 75 且未开始，当前没有该题 CPU 结果可验，不计为题目失败样本，也不能写作通过。四题真实 actor、正式 CPU 及训练资格仍按原范围另验；本工具不会替它们授予 typed-actor 资格。
