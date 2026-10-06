# 零分审查：MONAI、Dask、pandas

2026-09-19，Codex 独立切片。仅复用已完成实验的原日志、账本、诊断、宿主采样和原始 gold/test patch；没有重新运行、改评分或修改历史证据。

审查了 **45 题、57 条 reward=0**：主批 49 条（45 noop＋4 gold），以及 Dask-7894 的校准/并发重复 7 条、MONAI-763 资源变体 1 条。每条均读具体失败 traceback 与同条件 gold；默认 MONAI-763 的 gold 中断，另读已完成资源变体对照。

| 分类 | 主批 | 其它实验 | 含义 |
| --- | ---: | ---: | --- |
| 目标任务失败成立 | 27 | 7 | 实际执行的 F2P 失败与题目/gold 修改对应，gold 转为通过；不等于所有安装步骤、可选依赖已验证 |
| 目标失败成立，同时有其它异常 | 17 | 1 | F2P 有正常失败证据，但并存参考外测试、依赖、资源或参考 ID 问题 |
| 本次零分来自环境/参考问题 | 5 | 0 | MONAI-3205 noop/gold、MONAI-1121 gold、pandas-48106/50319 gold |
| 不能解释本次零分 | 0 | 0 | 上述范围内均找到了有日志支持的解释；部分额外异常的底层根因仍未证实 |

**45 个主批 noop 中，44 个已有目标缺陷的具体失败证据。** 例外是 MONAI-3205：唯一 F2P 虽进入测试，先在下载 MSD 数据时 DNS 失败，未测到各 fold 的 transform 行为，gold 同因失败。因此不能把它当作有效“未修复”负样本证据。

## 会使 gold 得 0 的问题

- **MONAI-1121**：唯一 F2P 在 noop 中因 TorchScript 把 float 属性赋整数而失败，gold 通过；但 8 个参考 P2P 都在下载预训练权重时失败，足以解释 gold0。另有 4 个 NumPy `np.int` 兼容失败和 6 个 helper 被错误收集的 fixture 错误，属于参考集外。
- **MONAI-3205**：noop/gold 的 F2P 都先在 `msd-for-monai.s3-us-west-2.amazonaws.com` 下载失败，环境资产遮蔽了题目行为。
- **pandas-48106/50319**：gold 分别 16/16、1/1 F2P 通过，测试主体无失败；P2P 参考 ID 的单反斜杠与日志双反斜杠表示不一致，并涉及空格截断。原日志同类参数用例有 `PASSED`，parser 仍记 3/1 个参考键 `MISSING`。这不能解释成测试没运行，也没有授权修改来源参考口径。

## 新确认：gold1 仍有参考集外失败

主批 **13 题**的 gold1 并非整个 pytest 命令全绿。下表计数来自完整 pytest 失败/错误行，避免生产 parser 按空格截参数 ID 后合并键造成少计。

| 题目 | gold 中的参考外失败/错误 | 实际原因与结论 |
| --- | ---: | --- |
| MONAI-2446 | 5 | NiBabel 拒绝未指定 dtype/header 的 int64 NIfTI；目标 datalist 原地修改则已被 gold 修复 |
| MONAI-3566 | 5 | 旧 MONAI endianness 处理不识别 `itkMatrixF44`；目标 DICOM metadata 用例0→1。具体兼容 pin 尚未复验 |
| MONAI-4109、6775 | 各1 | 导入的 `test_script_save` helper 被 pytest 收集，缺 `net` fixture；目标脚本化/损失值用例已通过 |
| Dask-6626、8597 | 1、2 | 当前 pytest 不接受 `pytest.warns(None)` |
| Dask-6801 | 7 | 5 个 pandas `_mgr` 缺失；2 个 fastparquet 导入 `BaseMaskedDtype` 失败引发 pytest 警告错误 |
| Dask-6818 | 2 | pandas `_mgr` 缺失；目标不同 blocksize 图命名已修复 |
| Dask-7138 | 92 | cov/isin/einsum 用例中的 `pytest.warns(None)` 不兼容；目标 ravel 输入转换单独0→1 |
| Dask-7656、8820 | 各1 | 导入 Dask dataframe 时分别缺 pandas `Int64Index`、`StringMethods` |
| Dask-8792 | 11 | 4 个 pandas `_data` 弃用警告、7 个 `pytest.warns(None)` 错误 |
| Dask-9212 | 10 | 4 个 pandas `_data` 弃用警告、6 个 emscripten 用例在入口导入 dataframe 时缺 `StringMethods`，未进入调度器行为 |

这些异常在 noop/gold 都存在，**不是目标0的必要原因**，但会妨碍 agent 在仓库里使用更广的测试反馈。应进入环境整理清单，不能因 gold1 忽略，也不能直接改成参考 P2P 或否定现有目标失败证据。

MONAI-763 默认 noop 同时具有参考内滑窗数值断言失败和参考外 DataLoader Bus error；资源变体消除了 Bus error，目标仍0→1。变体还留下参考外 segmentation3d 的固定数值偏差，noop/gold 的实际数组相同。它的底层原因未确定，**不能把这个偏差称为已证环境/内存故障**。

## 安装与解析的边界

**Dask-10972** 的 noop/gold 安装均 rc1：构建隔离在断网时取不到 `setuptools>=62.6`。但后续实际导入候选工作区，两个 UTF-16 F2P 的编码错误被 gold 修复。故当前证据支持“目标失败成立＋安装故障并存”，不支持“安装故障造成这次0”。其后依赖/构建修改型候选仍需专门验证。

pandas-48106/53958 虽有 pip resolver 的 `ERROR` 提示，随后明确 `Successfully built/installed`、安装末命令0，目标 gold 也改善；没有把文字 `ERROR` 机械当作安装失败。MONAI-3690 的 Gloo hostname fallback、MONAI-3547 的 cudnn 冻结错误也逐 traceback 区分：前者不是致因，后者正是题目要求修复的行为。

本切片 57 条零分的 F2P 均有日志状态，没有 F2P 缺席/跳过；但 **FAILED 仍须看 traceback 才能判断是否测到目标逻辑**，MONAI-3205 是反例。逐参考状态重放与原账本一致；宿主采样和 `resource_facts=null` 的边界分别保留，不用零采样推断不存在所有资源事件。

逐条结果：`runs/full216_rh2_diagnostic_20260919/zero_audit/numeric/audit.jsonl`。含每次实验键、分类、F2P/P2P 状态、完整原失败行、具体原因、同条件 gold、安装解释、原日志行号与证据缺口。`build_audit.py` 保存人工解释与合并过程；统一状态表是同目录上级 `parsed_facts.jsonl`，宿主采样为 `resource_facts.json`。
