# 8511 v2 R27 targetfix 输入增量独立核查（2026-10-04）

结论：**新 R27 固定输入在本次静态范围通过，`actual_frozen_input_review_passed=true`。** 真实新 prepare 的三份脚本恢复 `tests/test_dataclasses.py`，当前入口可继续已授权的 177 参考四候选正式 CPU 验收。R26 旧报告仍为 false，旧输入、错误命令、hold 及历史工件保留。此次通过不表示正式 CPU 或原 GPU FrozenPatch 补评分已完成。

本审查只核 R26→R27 选择器修复、实际部署、新固定入口、保存的 prepare、上传及 dispatch delta。审查者此前已读私有题材、旧 CPU/actor、原模型候选，**不是 fresh 公开读者**。仅本地标准库读/hash/JSON/AST/tar/字节比对；没有执行作者 helper、共享检查、项目 pytest、CPU、Docker、SSH、安装、模型或看板动作。复用已通过的材料和 R26 1528 基线字节核查，不重新审题义或旧矩阵。

## B1 在新版本的修复范围

R27 `spec_vendor.py` 为 16382B，SHA `9381f448821cbb8477fb37108df59c4efd7aaa29cd3dbb285d5bcdba413097cc`。相对 R26，源码全文只增加一个导入和以下分支：

```python
if isinstance(bundle, PrivateGradingBundleSWERevision):
    bundle = PrivateGradingBundleSWERevision.model_validate(bundle.model_dump(mode="python"))
    if type(bundle.revision) is SWEPyd8511FieldInfoRevision:
        return derive_eval_cmd(bundle.spec_vendor_id, bundle.repo_key_lower, bundle.version) + " " + " ".join(
            file.path for file in bundle.revision.test_files
        )
```

既有 vendor eval/python 互检仍先执行。精确类型分支位于完整私有 bundle 重验后，旧 model 的 `Literal['tests/test_dataclasses.py']` 与 test_files 长度 1 已封闭取值；重验同时保留 task/repo/base、v2 patch SHA、参考顺序、E10/镜像等固定约束。无法仅凭绕过初次构造校验的 model_copy/model_construct 任意注入其他路径。通用 `derive_test_directives` 与其余派生路径原字节保持，不增加泛型 fallback。

本次按真实前后源码全文确认这个精确变化，读取新增窄维护测试及既有绕过构造反例。publisher 保存的 25 项及 root 保存的 11 项维护检查结果作为各自已归档证据绑定；本审查没有重跑它们。维护检查不是 Pydantic 177 项目测试。

发布侧真实保存的三脚本均为旧 R26 对应脚本仅追加测试文件参数后的字节；真实前后 264 个 consumer 快照只有 8511 的三段脚本与 revision.test_command 变化，其余 263 个完整 spec/view、全部 264 公开摘要及 R2E48 快照保持。这里只比对已有静态/prepare 原件，不新增其它题的运行审查。

## 发布与新固定入口

R27 release 为 `cat2-cpu-r2e094095-swe40-pyd8511-fieldinfo-v2-test-target-20261004-v1`，manifest SHA `897cac778bce053740d7ac6dce9b2e90ac96a553a119c0bbdfe7e62b298cfe0d`，1529 成员。相对已完整核过的 R26 manifest，仅 `spec_vendor.py` 和 `SNAPSHOT_ID` 两项变化，新增 `test_pyd8511_v2_test_target.py` 一项；本次核真实三项 SHA/大小与精确目录集合，1526 个未变条目的既有绑定复用，没有再次全套重核基线。21 个 material source_members、registry、安装、原/有效补丁、全部 published bundles 逐字保持 R26。

实际出版回执为 3969B，SHA `24441835748681ace35ee5dd434c59143082988de2386499329c9008d3311298`。cpu-a 终部署 receipt 的 1529 成员传输/SHA/精确集合、trusted loader RC0/48+216 与固定 manifest/source 关联一致，未热换在途版本。df6c 准备镜像原件读回 RC0，与固定 derived_id 相同，记录没有新 build/pull/load 或任务容器；部署和 cache image inspect 不替代候选安装/真实容器身份。

新入口位于 `cpu_acceptance_20261003/8511_fieldinfo_v2_targetfix/`：

- `formal_inputs.json` SHA `88939f7d852133b2b6130f8d2e2c5a3237e9c7bdd13ed994dfa25c6782f368cd`。整个 tasks 字典、8 assets、全部四候选、源摘要、required_statuses 和 177 参考与 R26 完全相同。
- 原 173 个参考和四个新增 P2P 的序列、1 F2P + 176 P2P、noop/gold/narrow/qwen_original 及预期 0/0/1/0 均复用已核绑定；这是固定预期，尚无新四行奖励。
- 顶层仅新 R27 source/manifest/count/receipt、等字节 bundle 的新路径、runner 路径及显式 target_fix_delta 改变，其余顶层字段相同；新 delta 将旧 false 报告、错误输入、R26 回执、R27 部署/源 patch 核收逐 SHA/大小绑定。
- `run_formal.py` 22791B，SHA `b127f7309ffae3eae2bbe834c595f846104406e2f858b8073ff2182d0a2ce3c5`，与 R26/已核 R14 逐字相同，评分及执行预算没有改写。
- 原 Qwen FP/单生产源码运输等价结论按不变资产复用；此 CPU 源等价负对照不构成旧 GPU 完整 FP 的新评分。原 173/raw1/ACK 不改写。

## 题主真实新 prepare

读取 `local_prepare_8511_v2_targetfix` 全部 13 个实际普通成员及其 SHA，不以 helper stdout 或作者 passed 布尔值代替原件。prepared_manifest SHA `99188bb622d3ed4b4e7d9ca7862fabdd2800a09c9b930d3ce145bcef93d8ac0f`；private host grading artifact SHA `4ee496e588c46ae4b377a6069c01e302f85d637041fa9a2309bec524bc8bbf62`。

公开 prompts、rollout views 与 private host grading 文件分别逐字等于 R26 attempt02；单行计数、manifest 文件摘要、host artifact 摘要、来源及材料身份相符。actor_host_spec_equal=true 的保存证据与实际两侧 join 保持一致，没有重新运行 build spec。公开 actor 的复用边界没有扩大。

三份实际脚本及 revision.test_command 都精确包含以下命令：

```text
pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_dataclasses.py
```

| 实际新脚本 | SHA256 |
| --- | --- |
| eval_script | `60b34f625a04cecdf7ff4ac0b970fd6a2b391176f7e306c5b3d1fb6fee01a482` |
| candidate_test_script | `a0b1d43536fafb2f7d21d4a20717a219142ee0f0a566027b1c0f36100fde5e2a` |
| candidate_test_after_install_script | `b903596308a708d26a4807078a1023fa97a0424436fd94f33c0ce2ee8c137a6d` |

这三份全文与 R26 原件只差追加目标文件参数。trusted_setup、candidate_install、pre/post observation 四份逐字不变；实际 spec 除三 script 摘要与 revision.test_command 外完全相同，包括材料身份/摘要、177 参考分区、hygiene、reset/apply/test 300/120/1800 秒。whole budget、资源和 protection 按不变 runner 维持原约定。Python 3.8 AST 静态可解析。

状态仍为 not_evaluated，apply_ok=null，三个 partition.result=null；实际 Pydantic 导入、core/Python/UID、完整 baseline/FP 运输、候选安装、逐参考结果、账本资源与清理仍须正式 CPU 原件验收。local prepare 不证明这些事实。

## 封包、真实上传和派发保护

新 namespace 为 `formal_8511_fieldinfo_v2_targetfix`，和旧 R26 分开保存。upload_manifest SHA `21b751595d212c0ec234bf63961ffdedd63b41f53cbb58c9c691a11cb23f889c`；10 payload + manifest 共 11 个 tar 普通成员，精确路径、大小、SHA、逐成员字节均吻合，没有链接或路径越界。tar 为 24368B，SHA `5c6b89c7ea865c571d0db78836ea83f91a3d8bcb060d0544e0444caa477985eb`。

真实上传 stdout/stderr 与 owner certificate 的 hash、RC0、10 payload、manifest、exact/SHA 字段逐项吻合；本审查只读已归档远端核证，没有远端执行。题主 R27 publication/prepare delta 核收 JSON SHA `a33d244ac79583724901cbfa08fe1386b0b8383bac870d79ba4856286a04c923` 已绑定，不以其 passed 字段代替前述原件比对。

新 dispatch helper SHA `3ec7423619b2285d6d4a6ee84f8422b2e86cdcb2948fc7a1f583b3c0399b19c3`。其固定 R27 release+manifest、task=8511、唯一新 namespace；派发前要求新上传 certificate、此新报告 true 和当前 formal_inputs 裸 SHA 相等。它只调用一次 CPU slot，无自动循环或预算升级；全局 cpu_sequence_hold/cpu_infra_hold 存在仍返回 75，不删除 hold。新 local prepare/package/verify/dispatch 仅按源码及 AST 静态核，未执行。

旧 `8511_v2_test_target_hold_v1.json` 仍绑定 R26 manifest/错误输入与 CPU_started=false；旧 false 报告原 SHA、错误 prepare 原件都保留。新 R27 输入通过只解除 B1 对新固定入口的静态阻断，不改旧版本事实或清除全局 CPU hold。

## 允许范围与剩余工作

在以上 source/manifest、formal input、runner、上传及 dispatch 绑定范围内，允许继续既有授权的四行 177 参考正式 CPU；不新增评分要求或实验矩阵。旧实际 actor `pyd8511-actor-20261002234027-r14-3deca` 仍只在公开 prompt、base/image/E10/core 相同的开发与交付诊断范围有限复用，不等同新正式矩阵、typed 训练或模型能力证明。模板 status 的“四题 actor 仍待”历史文字不覆盖已核实际 actor 的这个有限范围。

截至本报告证据，新 177 CPU=未执行、原完整 GPU FP 的 v2 安装/177 参考补评分=未执行、新模型采样=0。直接四行为诊断与维护检查不能替代正式 CPU。ordinary GPU probe ready=false、训练资格=false；GPU 实际镜像兼容性、权重身份、typed 接口尚无本报告证明。后续须先由真实四行结果完成独立 CPU 验收，再接原 FP 补评分。

本次只创建新的独立 MD/JSON，未修改任何旧报告、输入、已封材料、发布、hold 或原件。JSON 保存新 delta、实际脚本/prepare/运输/保护绑定及复用边界。
