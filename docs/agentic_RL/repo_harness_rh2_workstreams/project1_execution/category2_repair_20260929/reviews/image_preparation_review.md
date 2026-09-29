# 两道 mypy 的已验资产层重建：独立静态核对

2026-09-29，修后窄复核。**当前采用文末核对的 v2：固定 `repo@digest` 作为 FROM 输入、独占 v2 标签，并核派生层继承；在单一执行者使用新的输出目录、无他人并发占用本批标签的条件下，可以执行两题已验资产层重建。** 下文 v1 记录保留，本次不涉及 D6 实施，不 SSH、不下载、不构建、不运行项目／评分，没有修改脚本或维护测试。

核对对象：[prepare_images_v1.py](../../../../../../runs/category2_repair_20260929/tools/prepare_images_v1.py)、[mypy_images_v1.json](../../../../../../runs/category2_repair_20260929/tools/mypy_images_v1.json)、[首包安装复用清单](../swe_materials/first_mypy_bundle/installation_reuse.json)。最终脚本 SHA-256 为 `9c7841d0773682e9674116e2ad86253e51cac452edbc7a2a29637c1c4a23b51f`；镜像清单 SHA-256 为 `eb8daf5fdc4e36f87c33acb99d8a12e48944af1bf16830e11a3645f6a0e5c34f`。以下结论仅适用于这两份字节。

## 已核实

- Python AST 可解析；没有执行脚本。清单中的 `source_manifest_sha256` 与当前题级材料文件相符。
- 两题的固定 registry digest、base image ID、历史派生 ID、recipe ID 和 Dockerfile 与安装复用清单逐项相同。11个 wheel 的发行包、版本、文件名、SHA-256、字节数完全一致，总计 **2,413,682 bytes**。
- Dockerfile 只有 `ARG`／`FROM`／`COPY`／`ENV`，没有项目安装或测试命令；构建使用已核 base ID、`--network=none`，并核 Linux/amd64 及离线 pip 环境。
- PyPI 元数据按包名／版本获取，轮子必须唯一匹配文件名和历史 SHA；下载 URL 限 HTTPS 的 `files.pythonhosted.org`，落盘前再次核精确长度及实际 SHA。单个读取最多16 MiB，当前清单每项均小于该限制。
- 输出根要求不存在；没有删除原镜像／旧结果的代码。采用本批独立标签，检查成功发现同名标签时明确拒绝。
- pull/build 的 Docker 客户端命令各有1800秒 timeout，inspect 30秒，HTTP 请求配置60／120秒 socket timeout；命令非0、下载或内容校验失败均记录失败并抛异常，不能输出成功的 `done.json`。
- 成功记录保存新 `image_id`、历史 `historical_derived_image_id`、base ID、Dockerfile SHA、实际下载 wheel 摘要及完整 image inspect。**重建后的 image ID 不必等于历史 ID**；等价性依据是固定基线＋相同COPY内容＋相同ENV，不能为追求旧ID修改历史记录。

## 两处修后结论

**IP1／P2 已关闭。** 原脚本把 `docker image inspect <tag>` 的所有非0当成“不存在”，会将 daemon／权限错误误放行。最终脚本92–97行保留 stdout/stderr：返回0拒绝同名标签，非0只有 stderr 同时含 `No such image:` 和本次准确 tag 才继续，其它错误停止。正常不存在仍能进入 build；Docker 的其它错误不会再被静默当成不存在。本批由单一执行者占用这些标签，不新增并发锁机制。

**仅 COPY／ENV 的范围前提已落实。** 最终脚本63–64行在读取并核验基镜像身份后拒绝非空 `Config.OnBuild`，因此不会在 FROM 时默默触发基镜像留下的构建指令。该检查仍需执行时读真实元数据，本次没有声称真实镜像已通过。

修后再次 AST 解析通过；将这两处改动逆向还原，重算得到原审查脚本 SHA `ec2ceb4dbaac63048add9dc5cb6f0cfea1d0df0285120b453ead32118a47c3f7`，确认没有混入其它脚本改动；镜像清单 SHA 未变。只作静态复核，没有新测试或运行证据。

## 运行记录的适用边界与停止条件

HTTP timeout 是 socket 等待上限，不是整个下载的严格墙钟期限；Docker timeout 停止的是客户端，不证明 daemon 中的拉取／构建已取消。超时应保持失败状态，由执行者只读核本次是否仍在运行，不据 `failed.json` 宣称后台已清理；本脚本本来也没有删除构建缓存或镜像的动作。

上述静态停止条件已满足，可以按现有授权在 SWE 机执行两题资产层准备。只有实际下载／构建／inspect 结果才能确认机器和产物状态；本报告没有证明机器在线、镜像已存在或 wheel 已可下载。准备完成仍只记 `images_prepared_no_execution`，不算安装复验、正式评分、D6接线或题目转类。至此停止扩大本次审查。

## v2：固定 digest 的 FROM 输入与层继承（同日追加）

主线程报告 v1 实际构建失败：BuildKit 将 `FROM sha256:<本地image ID>` 解释成 `docker.io/library/sha256` 引用，拉取被拒；旧结果已保存，未创建容器或新镜像。本作者未连接机器核原日志，这部分标为主线程运行事实；前轮静态复核没有验证 BuildKit 对本地 image ID 的 FROM 解析，不能将它称为已验证可构建。

已独立核 [prepare_images_v2.py](../../../../../../runs/category2_repair_20260929/tools/prepare_images_v2.py) 的 SHA-256 为 `89eb540abaa477d78aa7cc411af7c34ab86de1d495115b9cb623dd89eb36101f`，AST 可解析；与上述最终 v1 的完整文本差异只有三处：

1. `BASE_IMAGE` 改用清单内固定 `repo@sha256`。此前仍先 pull 同一 digest、inspect 并核固定 image ID／Linux/amd64／空 ONBUILD；没有退回可变 tag，也没有改来源 pins。
2. 输出 image tag 改为独占 `20260929-v2`；既有标签拒绝及标签探测错误停止逻辑原样保留。新输出根仍由调用方提供，并通过 `exist_ok=False` 防覆盖；v1 文件和失败结果不回写。
3. 构建后要求 base 的 `RootFS.Layers` 非空，且派生镜像 layers 的对应前缀逐项相同，否则停止。新 image ID 仍单独记录，无须等于历史派生 ID；下载 SHA、Dockerfile 和离线 ENV 的既有核对保持。

**v2 静态复核通过，可以继续本轮已授权的镜像准备。** 固定 digest 的镜像解析仍可能需要 registry 访问，`docker build --network=none` 限制的是构建步骤网络，并不承诺镜像解析完全离线。实际是否构建成功以 v2 新目录的最终记录为准；不包含安装复验／评分，亦不解除 D6 待决定状态。停止扩大审查。
