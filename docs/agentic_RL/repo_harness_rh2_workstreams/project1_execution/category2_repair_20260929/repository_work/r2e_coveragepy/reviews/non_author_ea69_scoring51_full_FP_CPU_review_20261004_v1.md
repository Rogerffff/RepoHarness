# EA69 R28：完整原 FrozenPatch 的 51 键 CPU 补评分独立核查

日期：2026-10-04。身份：已有本题私有材料接触上下文的非作者核查者，不是 fresh public reader。本轮只读本地闭批原件、冻结材料及相关消费函数；没有启动 CPU/GPU、SSH、容器、模型、安装或项目测试。只新增本报告和同名 JSON。

**结论：本轮受影响评分路径通过独立核查，无评分阻断。** 新 51 键由可信 host 消费者实际恢复并在精确旧评分镜像中执行；安全正控制 51/51、两份未经修改的完整模型 FrozenPatch 各 50/51、真正空补丁 41/51，均与完整原日志、固定 parser、typed report 和作者逐键读回一致。可据此关闭这条 R28 CPU 路径中已知的两项评分覆盖缺口。它不证明公开目标所有边界均已穷尽，不授予未来 actor 环境、GPU 新请求或训练资格。

## 实际结果与失败范围

| 输入臂 | 新评分 | 原 49 键匹配 | 新失败 | pytest RC | 作业 RC |
| --- | --- | --- | --- | --- | --- |
| safe_append（host 正控制） | 51/51，raw 1 | 49/49 | 无 | 0 | 0 |
| original_coder | 50/51，raw 0 | 49/49 | `test_generated_extra_css_literal_names_are_ignored` | 1 | 0 |
| original_qwen | 50/51，raw 0 | 49/49 | `test_existing_patterns_do_not_skip_report_ignore` | 1 | 0 |
| noop（空 FrozenPatch） | 41/51，raw 0 | 41/49 | 原 8 键及新增 2 键 | 1 | 0 |

四份 `eval.log` 均有唯一完整 Start/End 测试段，51 个 observed keys 无缺项、额外键或 skip。独立使用冻结发布版 parser 的纯解析函数重放原段，逐键对拍 expected、作者 `actual_expected_51`、typed report 及 diagnostics；全部一致。安全正控制为 resolved，其余为 `tests_failed`，没有 infra failure。旧 49 键 expected 值保持不变，两模型旧键全部通过；R17 原 GPU raw 1/49-of-49 及原报告不回写，新 raw 0 是新材料下的补评分结果。

Coder 失败停在 `!custom.css` 第一轮生成，其报告产物 `report_css_1/!custom.css` 的真实 Git ignore 查询返回 1。Qwen 失败停在首个已有内容输入（注释含 `/*`）的第一轮，`report_rules_0/coverage_html.js` 查询返回 1。方法会在首错处早停，不能声称本次失败方法的所有后续子场景均执行；此前完整边界 CPU 的真实 Git 证据按范围复用。本轮新增的是“所有生成文件被 Git 忽略”的行为验收，没有新增逐字节保存、文本幂等或空行/CRLF 格式约束。

## 冻结发布与可信恢复

固定 release 为 `runs/category2_repair_20260929/releases_20261004/r2e_096097_swe40_coverage_ea69_scoring51_v1`，材料修订集合为 073/093/096/097。独立核 trusted prepare 的 11 个回收 payload，以及其 1542 项 SHA/bytes 映射与固定 release manifest 的一致性；没有重复全套共享源码逐文件审查。17 个受影响 binding 目标的实际本地冻结字节及回收 prepare 身份另行核对。

公开面 digest 保持 `53deb1de7539fb7dfb1150fbe52957a29ee0f69d35f68f9796a53aa787ebdcc0`。新 private grading digest 为 `f7a65179e75079ec0de30f55683ac2ecce3fe23f331633bc0b413b00a29abd10`，新 hidden tree 为 `f60525728e5ab5a1583e3d65121e366132a63d1f27f97a00910ebb195a40c9e3`。私有评分变化使 environment package digest 变化，不将它写成整个 package 身份未变。

实际消费函数 `_coverage_ea69_scoring51_restore_lines` 重新验证完整 private bundle、精确题 ID、修订集合和 grading digest，读取固定 release 中 `test_2.py` 正文并核 SHA。可信 root setup 先复制镜像 private 测试树，再恢复新正文；随后核全树和旧 runner。四臂 setup 的 base64 正文独立解码后都精确匹配冻结新 `test_2.py`；原日志均记录新树 f605、旧 runner SHA 828576、`RH2_SETUP_OK=1`。保护面为 4 文件/7 目录，missing=0。

新正文 SHA 为 `6fa2ecfd00f917a12867d75b2c855875b88446411a7f35dc5ed429829d1998fa`，expected SHA 为 `d766068e50bbeb338cd8a63e80b0c0e97ea9cfc83dde44b5f6e59fc6647e6b2a`。旧 runner SHA 为 `8285765fcf1a4ec23ca55ad4781a064d121b58266ef5c5e22c681f6ece616aaf`，命令正文未改。发布时回执中的“尚未实际评分”字段保留为当时事实，由本轮新证据补充，而非改写历史回执。

## 完整补丁、基线及镜像边界

评分沿真实 `FrozenDeltaSource`、`BaselineWorkspaceManifest` 和 `SWEGradingManager` 路径。没有从 diff 重建候选或删除候选条目。四臂 360 个基线 regular 路径的内容摘要与 Git mode 逐项一致，canonical baseline digest 均为 `7d9fea8c8926ccc665aa1d9f71cf316338ed712d0277d46efdaf75c2a285385e`；4850 个排除路径摘要一致。mode 契约为 Git 100644/100755，不冒称原 tar 的 POSIX 权限逐位相同。

| 原模型 | FrozenPatch 文件 SHA | canonical digest | 完整条目 |
| --- | --- | --- | --- |
| Coder | `85c2211228edd88e9012924fc118c7e3cc1e814859a6b3ac2cda26d86367e388` | `591da512f8615d902fda2f8337bd0d56c9ae4bcc1c19abd6d82d01120d5fa877` | `coverage/html.py` |
| Qwen | `ae3ae46f8abc45f85acacfc1784babf8c9aaddf333ce535d8c6699a325f2f25c` | `a237757b19cee92e4226ec84cdb60104f11622ef13b125823dec2e2636715381` | `coverage/html.py` 与 53248 B `.coverage` |

逐条解码、内容 SHA/mode 和完整投影均匹配原 FP，独立重算的应用条目摘要匹配 typed patch hygiene。manager 的可信应用代码及实际 clean/replay 摘要支持完整运输；本轮没有做应用后每个文件的额外容器读回。Qwen `.coverage` 未被剥离，也不据此推断每条数据库记录都被评分读取，不重开 DB 专项或作作弊判断。safe 为明确的 host 私有正控制，noop 确认 `entries=[]`，均不是新模型样本。

四臂实际 OCI image 均为 `sha256:e23fbbed8b6f809347e38ee9684699314fda0e14a948a06b9d368e29c8db38d2`，通过显式 grader override 使用，不是 public 默认镜像字段变化。实际限制为 2 CPU、4 GiB、512 PID、network none、无 bind/mount。trusted setup 使用 root，candidate 执行 UID 为 54322，两者不混称。没有新 build/pull/load。

历史 overlay 原 SHA `3cc861b3264535edad987b36406d49074b8955c4d734ba0eb2e1737feaae35e1` 及旧 private tree 事实保持。新正文由 host 恢复，不能声称它已烘焙进旧 e23 镜像，也不能把旧 overlay 当作新 51 版 actor 资格。实际回收记录的 `env_qualification=absent`、`grading_materials_identity=null` 如实保留；本轮评分成功不替代未来 actor 的身份验收。

## 退出、预算与清理

四臂安装均明确 skipped，`install_rc_last_command=null`、安装秒数 null；没有将 skipped 写成安装 RC 0。candidate shell 末尾记录 pytest RC 后正常退出，所以 candidate exec RC 0 和外层 job RC 0 不等于测试通过。三份负结果的 pytest RC 1、完整测试段和 `tests_failed` 分类一致，未将异常或未执行评分强制记成 reward 0。

wrapper 最终 SHA 为 `b3423f674b7f337d520ac0a54b15833edbb830f8b012ff0039414c708aca7ff5`。whole budget 3600 s、外层 wait 3900 s、close 300 s、launcher timeout 4200 s/kill-after 300 s；API 与既有实际消费路径一致。一次性 SIGINT/SIGTERM handler 和异常清理路径做了静态核查，未做信号故障注入。实际自然结束时，各 manager created/removed 总数均为 1，open containers/supply、cleanup failures 和 regrade 为空/0；实际 own-label 查询为空，四 job 均 finished/RC 0。prepare job 亦 finished/RC 0。

## 原件完整性及计数勘误

独立核五批清单中的 **103 个 payload 项、3392547 B**，全部 SHA/bytes 一致；另核 5 份 `archive_manifest` 和五份 tgz。未执行归档内容，逐成员字节与闭批文件对拍一致。五个 tar 的物理成员数为 **12+24+24+24+24=108**。作者固定报告把 `physical_archive_members` 写成 103，实际为不含清单的 payload 项数；这是名称/分母勘误，不影响运输或评分，父线程已采纳在新摘要注明，原作者快照不改。

作者固定报告全部引用的 path/SHA/bytes 及各 owner readback 固定引用独立核对一致。核心作者结论、逐键实值和退出分类一致，只有上述计数名称需更正。

| 固定证据 | SHA256 |
| --- | --- |
| R28 publication receipt | `06dc12935bd4d413608db5dd931d12423f2a095f892475236196cf7110095a24` |
| release manifest | `fabc9e1f9996e4a998c503350b9618595ea7990f263d11f6779cb05945c837e4` |
| frozen publication/prepare binding | `a5cb24c68a4afe0508d489c863762e39760fb26ab68c3a2b2ad5ce13a873771f` |
| 作者 CPU closeout JSON | `64394ffb14450ec7065f64e0719995075ae50d49d5927c8fa0b46789387c56fc` |
| 作者补充分析 MD | `9e79c1754144de84e03a6affaf181097af18761144d083ec8216568124f5f078` |

[同名 JSON](non_author_ea69_scoring51_full_FP_CPU_review_20261004_v1.json) 保存全部 146 项证据 refs、103 项 payload 校验、五批 manifest/tgz SHA、四臂完整 51 键映射、typed report、镜像/补丁/清理实值。其 SHA256：`67167e6b48d318d30d8413694355f3e3d7893358cb611d28887f6c853ef3994f`。

复用边界：公开题面未变，沿用既有公开交付、源/recipe 和专项边界审查；不重做旧矩阵、旧 GPU 七维或 fresh reader。两模型仅是原单次候选补评分，不能据此作稳定能力结论；没有新模型执行，没有改公共材料、原 49 评分、旧报告或总账。
