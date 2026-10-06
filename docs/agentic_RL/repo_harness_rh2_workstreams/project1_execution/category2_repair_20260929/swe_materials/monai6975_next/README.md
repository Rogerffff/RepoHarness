# MONAI6975 下一片材料

2026-09-30。材料已静态准备，等待 root 审查；没有实现生产、登记新版本、运行新增节点或正式 CPU 复验。本题仍为第2类。原正式 4F2P+59P2P 的 CPU18 恢复结果是 noop/gold/丢返回值候选 0/1/1；新增普通像素节点拟放 P2P，变为 4F2P+60P2P、64 参考，下一正式矩阵预期 0/1/0，尚未执行。

[提案与公开依据](proposal.md)解释为什么检查 Dataset 返回图像，以及 P2P 归属；[消费者扩展清单](consumer_extension_plan.md)列两文件的窄守卫；[续接检查](resume_check_20260930.md)区分可复用证据、1800 setup 范围与待验事项。固定字节及 SHA 在 [materials_manifest.json](materials_manifest.json)，完整物理包清单在 [pack_inventory.json](pack_inventory.json)。大材料位于 `runs/category2_repair_20260929/swe_materials/monai6975_next/`，包含原/新增/有效补丁、base 文件、两份原测试 AST 保持证明、正确/漏修控制和 CPU18 原件；不是新的运行产物。

新增 `tests/test_dataset.py::TestDataset::test_dataset_lazy_dict_returns_transformed_pixels_cpu` 使用 dict+MetaTensor 的 1×3×4 CPU float32 图像和两次确定性 Flipd，直接核返回像素为双轴翻转的11…0，容差沿既有 CPU 矩阵的 atol1e-6/rtol0。它不 mock resample、不计调用、不检查日志、不使用 gold 算法作规范。已有六行原件表明 base/gold 该路径的像素正确，丢返回图候选虽执行过真实 resample 却给原图，故像素节点应是 P2P。原4个 F2P 政策节点完整保留，整套参考仍要求政策和输出都对。新方法未执行，不能把已有同路径行为证据写成新节点已通过。

原 `test_patch` 已包含 Compose 与 Dataset 两文件。增量只加 Dataset 的普通方法；有效补丁完整保留两个原 hunk，Compose 原补丁后文件逐字不变，移除新增方法后两文件 AST 与原补丁后版本相同。当前 D6 的单文件 allowlist/max_length=1 不能消费本包，不得只登记 Dataset 或丢掉 Compose 补丁。下一实施须独立授权/冻结，不能与 Moto5406 在同一 consumer 基线上热改。

环境继续用原 manifest `sha256:0a529471d25c944c76e598474d7a665b20edc2ee95b1a2f30bf9c36fd8db6055`；历史 config ID `sha256:789cb5d10d9b343a2e8b656581697a7127b56a0d467b1cc5b8779a79a0ff0727`。本包只有历史 inspect，缺本地可执行镜像层/daemon 状态；后续 root 按固定 digest 恢复并实际 inspect 核 ID/linux-amd64。无新 wheel、数据、模型、CUDA或派生安装要求。原 vendor install 保持，测试命令精确为 `pytest -rA  tests/test_compose.py tests/test_dataset.py`（双空格）。历史镜像初态 requirements-dev.txt 已删 MetricsReloaded Git 依赖；保留实际 status/diff，不称干净 base。

预算沿已验 CPU29-R3 恢复：setup1800、test1800、whole3600、candidate900、cleanup120，2CPU/4GiB/PID512，后续工具按正式 profile 核 shm64MiB。旧 setup900 在 control_surface_protect 超时，安装/测试未开始、reward null，不是正常 noop0。1800 恢复有完整成功证据，但负载与并发也变过，不能声称1800修复了根因或900必然不足。whole3600始终限制总流程；两阶段1800相加不另给开销时间。历史达到4GiB上限及有限采样无OOM的边界继续保留。

作者本轮仅标准库、隔离 `git apply --check/apply`、AST和既有原件 SHA/JSON提取；未项目 import/测试/安装/下载/SSH/Docker/新 CPU。5项 patch check 和全部 apply rc0，新有效两文件等于 base+原patch+增量；控制整文件 SHA 与已有 CPU18 frozen源码一致。`preparation_record.json` 与 `author_static_validation.json` 保存精确命令、退出及自查结果；作者自查不是独立验收，也不授予训练/holdout资格。
