# MONAI 2446／3715 非作者静态材料窄核

日期：2026-10-03。审查者：Codex 非材料作者；已经阅读私有测试补丁、gold、错修对照和历史审查，**不是 fresh 盲审**。范围限定为本包 `preparation.md`、`materials/2446/`、`materials/3715/`，并沿材料列出的公开原件、base 源码及必要历史指针核对。未审 6975，未重做两题全量审计。

**结论：本轮未发现具体误拒、漏检、语义或调用错误，不要求修改新增测试或机械增加候选。两题材料可以进入已授权的登记与 CPU 运行验收；本报告不证明新节点 collection、CPU 通过、正式 reward 或训练资格。** `preparation.md` 和修订单把新节点及对照结果明确标为未执行，口径准确。

## 2446：内部随机与缓存

- 公开原件 `runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-2446/user_prompt.txt` 要求只在 SmartCacheDataset 内部打乱 datalist，原例正是五个 ndarray 的 list。公开 base `monai/data/dataset.py:664`、`:681`、`:712` 规定 shuffle、seed 和 `self.R.shuffle`；原 `tests/test_smartcachedataset.py:102` 也按 seed=123 验既定缓存值。因此新测试的随机期望有公开契约依据，并非从 gold 凭空追加。
- 新 `materials/2446/effective_test.py:39` 使用同一数组列表，`:40` 在构造前保存值，`:42` 按 seed=0 得出内部顺序，`:55` 验实际 `dataset.data`，`:57`–`:58` 从 `dataset[i]` 取实际缓存并验前两项；shuffle=False 分支保留原顺序。缓存数 2 与 base `cache_num = min(int(cache_num), int(len(data) * cache_rate), len(data))` 和 SmartCacheDataset 的 `__len__` 相符。`:60` 的 shutdown 在未 start 时由 base 正常返回。
- 已证 `controls/array_no_shuffle.patch` 在非空 ndarray list 上跳过 randomize，会保留 0,1,2,3,4，因而违反新增内部顺序／缓存断言；历史 CPU 独立复核记录的正确顺序为 2,0,1,3,4、缓存为 2,0。这是对新增断言的静态区分力推导，未冒称新节点实测失败。
- 调用者列表不变继续由原 F2P `test_datalist` 验；原两个 P2P 不变。新 P2P 不要求 `copy.copy`、深复制、元素隔离或容器身份。gold 的浅复制、`controls/alternative_list_copy.patch` 的外层 `list(data)` 均与所读断言相容；新节点对 noop 预期通过也与 base 原有内部 shuffle 相容。
- 历史依据：`../../../../swegym_cpu_preprobe_20260929/reviews/monai2446_result_review.md`。其中旧正式 0／1／1 与新正式矩阵预期必须分开；本轮未重新读取全部历史日志或运行环境。

## 3715：真实 run、梯度与恢复

- 公开 `runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-3715/user_prompt.txt` 明确提出字符串 train 及 Saliency 推理动机。base `monai/engines/evaluator.py:117` 错把规范化结果赋到 `self.mode`，之后仍用原局部字符串与普通 Enum 比较；`:260` 的真实 SupervisedEvaluator forward 使用 `with self.mode(self.network)`。base `monai/networks/utils.py:294`–`:357` 的 train/eval 上下文分别控制模型模式、梯度开关并恢复进入前状态。
- 新 `materials/3715/effective_test.py:38`–`:46` 覆盖字符串／枚举 train/eval，以及四种进入前模型／梯度组合，共 16 个子场景。`:53`–`:62` 经 CPU 非空单批 `SupervisedEvaluator.run()`；`epoch_length=1` 避免原空数据 P2P 的直接返回，`decollate=False` 保留张量预测。已核 `PrepareBatchDefault.__call__`、默认 prepare_batch、`SimpleInferer` 和 Workflow 调用链；此处没有直接调用内部 helper 代替真实 run。
- `:35` 记录 forward 当时的 `training` 和 `is_grad_enabled`，`:63` 验实际 forward；`:64`–`:65` 验退出后模型及梯度状态；`:66`–`:72` 同时验预测值、`requires_grad` 和实际对输入求导的梯度 2；`:73` 再验梯度开关恢复。小网络不含参数，但输入梯度正对应题面 Saliency 的必要行为，无需扩大为 optimizer、训练 loss 或完整 Saliency 算法测试。
- base `tests/utils.py:86`–`:92` 直接 `.cpu().numpy()`。新增数值比较先 detach 可避免 helper 对需梯度张量报错；原 `prediction` 仍供 requires_grad 与 `torch.autograd.grad` 使用，`:70` 临时 enable_grad 也使初始梯度关闭的 train 场景能执行 `prediction.sum()`，未丢弃图。
- `eval_only.patch` 在第一个字符串 train 构造处仍失败；`always_eval.patch` 会在 train 的 forward 状态／梯度断言失败。gold 与 `alternative_local_mode.patch` 都规范化局部 mode 后选择对应上下文，与这组行为断言相容。测试没有上下文函数身份比较，允许局部变量规范化及等效上下文实现；不要求实现形式与 gold 一致。
- 历史依据：`../../../../swegym_task_audit_20260920/quality_expansion_20260925/results/Project-MONAI__MONAI-3715/review.md`。本轮修订补上其中提出的 train 行为缺口，未把历史 eval／空数据结果换写成 train 实测。

## 本轮实际完成的静态核对

仅执行标准库文本／JSON／哈希／AST 检查，没有导入 MONAI／Torch／NumPy，未执行项目代码或测试、安装、网络、SSH、容器或修改生产／题主材料。

| 核对 | 2446 | 3715 |
| --- | --- | --- |
| 修订单列出的 source_assets、四项材料与 controls 的 SHA／字节数 | 12 项匹配 | 17 项匹配 |
| base + original + extra 与 base + effective、effective_test.py 文本一致 | 一致 | 一致 |
| 从 effective AST 仅删除新增方法后与原测试 AST 一致 | 一致 | 一致 |
| 原 F2P／P2P 顺序保留，effective = original + added | 1 F2P＋3 P2P | 2 F2P＋1 P2P |
| 所有 controls 文本应用后源码 SHA 与修订单一致、AST 可解析 | 匹配 | 匹配 |
| 新节点及对照 CPU 执行 | 未执行 | 未执行 |

有效测试补丁 SHA256：2446 为 `c413f2b150eec668aee425cf1171faedaf7fdbb8c9a3bae171328a741231b7e7`；3715 为 `1e38b2d6a5dcfa2e2de5622c4db601a446da4e68ef1bd642d9c8100c3415565e`。本轮自行按统一 diff 的上下文逐行重建并核哈希，没有复运行作者 `static_prepare.py`，也没有把作者 git-apply 记录当作本人执行。

停止条件：本轮两个指定问题已有明确静态答案，未发现必须先修的材料问题。下一切片沿现有准备单完成登记和实际 CPU collection／完整评分；所列 noop／gold／错修／合理替代矩阵仍只是待验预期。运行失败后再按具体失败证据定位，不追加未授权目标。本轮唯一新增文件是本报告，未覆盖既有文件。
