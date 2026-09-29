# Project-MONAI__MONAI-5686 公开静态审阅

## 范围与证据性质

本报告仅依据本题 `PUBLIC_DIR` 与指定 `roles/public_reader.md`，没有访问网络、私有材料、历史、gold、隐藏测试或其他角色报告，没有执行或导入项目、运行测试、修题或派生 agent。以下路径除角色卡和输出路径外，均相对于：

`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-5686`

`public_bundle.json:1` 声明 base commit 为 `25130db17751bb709e841b9727f34936a84f9093`，工作目录为 `/testbed`。`environment_brief.md:2-10` 明确 base 是静态导出，实际 actor 初始源码、HEAD/status/diff、消息交付、依赖、权限和资源均未核验。本报告不将这些声明当成运行证据，也不宣称 OS 隔离或未受预训练污染。

## 先依据题面形成的目标、约束与疑义

- 目标：在题面 `y.requires_grad_(True)` 的用例中，`SSIMLoss(spatial_dims=2)(x, y, data_range)` 应保留对输入的梯度依赖，`loss.requires_grad` 应为 `True`（`user_prompt.txt:3-23`）。实际训练用途还要求反向传播能够到达输入；仅对输出强行设置 `requires_grad` 不足以修复问题。
- 合理旧行为：继续计算 SSIM 对应的损失，而非改成另一种损失；不因修复梯度而改变相同图像的前向数值或调用方式。题面没有要求外部数据、模型训练或网络服务。
- 公开提示约束：只修改非测试源码，测试改动不计入修复，验证保持单文件/模块规模（`public_bundle.json:1` 的 `public_hints`）。这些是公开计划输入，实际是否交付仍为 unknown。本角色自身只静态审阅，连建议验证命令也未执行。
- 待读源码消解：截断来自损失还是指标；是否存在多通道的第二次截断；2D/3D、批次和通道接口如何约定；旧测试是否覆盖梯度；CPU 是否足以验证。

## 公开源码、文档和旧测试所能消解的疑义

1. **直接根因可静态定位。** `base/monai/losses/ssim_loss.py:83-90` 通过 `SSIMMetric(...)(x, y)` 计算损失；该类继承 `RegressionMetric`（`base/monai/metrics/regression.py:241`），后者继承 `CumulativeIterationMetric`（同文件 `:27`）。`base/monai/metrics/metric.py:313-336` 的调用进入父类，`IterationMetric.__call__` 在 `:69-71` 对两个张量执行 `detach()`，随后才调用计算函数。这条路径足以解释题面用例丢失对 `y` 的梯度依赖；结论来自代码推导，未声称已复现。

2. **只绕过损失最外层的指标入口未必足够。** `SSIMMetric._compute_metric` 在多通道分支再次调用 `SSIMMetric(...)(...)`（`base/monai/metrics/regression.py:329-345`），重新经过同一 `detach()` 入口。损失文档明确给出 `C=5` 的 pseudo-3D 用例（`base/monai/losses/ssim_loss.py:69-74`），所以保持多通道可微属于有公开依据的合理范围。单通道的卷积、乘除和均值位于 `regression.py:289-307,347-355`，没有在这些计算段显式截断输入。

3. **指标入口断开梯度是现有通用机制。** `IterationMetric` 的张量与列表路径均 detach（`base/monai/metrics/metric.py:65-91`），供模型评估使用（`:23-26`）。修复 `SSIMLoss` 不需要全局移除该机制；这样做会影响所有指标的计算图和缓存行为，范围明显超过题面。`RegressionMetric._compute_tensor` 在 `regression.py:78-82` 还有类型及形状检查，绕过入口时需要审视这些检查是否仍有效。

4. **前向接口和数值基线有公开依据。** 构造参数为 `win_size=7, k1=0.01, k2=0.03, spatial_dims=2`；`forward(x, y, data_range)` 返回标量 `1 - ssim_value.mean()`（`base/monai/losses/ssim_loss.py:33-55,99-101`）。文档约定 2D 为批次、通道加二维空间，3D 增加一维空间（`:39,49-51`）。`base/docs/source/losses.rst:94-100` 与 `metrics.rst:139-141` 均直接引用这些类，没有额外梯度语义。窗口文字称 gaussian，但实现实际是均匀权重（`regression.py:261,287`）；这不是题面所要求的公式变更。

5. **公开旧测试不能证明梯度已修好。** `base/tests/test_ssim_loss.py:19-49` 只用单批次、单通道的相同常量/零图像，检查 `1-loss` 接近 1/0（误差小于 0.001），覆盖 2D/3D 及可用时的 CUDA；未启用输入梯度或调用 backward。`base/tests/test_ssim_metric.py:19-61` 检查单通道数值及 `aggregate()`；`:63-68` 的多批次多通道用例仅断言结果类型和 contrast 数值，没有梯度断言，也没有完整验证 SSIM 数值。因此只通过两份旧测试不等于完成题面。

6. **CPU 可作为最低验证条件。** 最小复现仅依赖本地合成张量；损失旧测试在无 CUDA 时明确使用 `[None, "cpu"]`（`base/tests/test_ssim_loss.py:24,33`）。公开包要求 `torch>=1.8`、`numpy>=1.17`，最小测试依赖包含 `parameterized`（`base/requirements.txt:1-2`，`requirements-min.txt:1-5`）。不需要数据集、权重或 GPU 来验证核心问题；实际解释器、库版本和导入路径仍为 unknown。

## 合理实现范围与仍未规定的选择

- 核心要求是让输入到损失的整个 SSIM 计算可微，并保留既有数值及签名。相同图像的梯度可以为零；不能把“每个位置梯度必须非零”当成题意。至少对题面中的第二个输入可反传；公式对两个输入均有依赖，合理实现也应允许第一个输入单独或两个输入同时需要梯度。
- 可选择复用不 detach 的底层计算并处理多通道递归，或抽出纯张量计算供 loss/metric 共用。另写损失计算也可能符合功能，但会重复公式并增加同步维护成本。这些是公开证据允许的方案比较，未见 gold，也不推定唯一正确补丁。
- 在最终输出上调用 `requires_grad_()` 只会制造与原输入断开的可求导叶子，不能作为真正修复。全局取消 `IterationMetric` 的 detach 也不是必要改动。
- 题面没有精确定义空批次、非法维度、`data_range` 的每批次向量语义、NaN/零动态范围或半精度行为。保留既有受支持输入行为即可，不应把扩展支持这些边界当成明确验收要求。
- 静态还可见批次/通道聚合的独立脆弱处：损失批循环用 `ssim_value.view(1)` 重新拼接（`ssim_loss.py:85-94`），对累计多个结果或每样本多通道结果并不普遍成立；指标使用 `view(ssim_value.shape[1], -1)`（`regression.py:353`）的形状依赖也需谨慎。它们不是本轮实测故障，也不能据此扩大为必须重写全部批处理语义。若重构涉及这些路径，应补充探索性验证并明确行为选择。

## 开发需求与最小公开验证计划（均未运行）

下列命令供后续获授权的实际 actor 在确认工作树后执行，不是在静态 base 上执行的记录。

| 需要操作/资产 | 公开依据 | 实际证据或未知 | 最小命令与预期 |
| --- | --- | --- | --- |
| 确认实际源码和仅修改非测试文件的权限 | `user_prompt.txt:1`；`public_bundle.json:1` | 只有公开静态源码；实际 HEAD、初始差异和写权限 unknown | 在实际仓库执行 `git rev-parse HEAD`、`git status --short`；预期与公开 base/既定初始化相符，差异需先识别来源 |
| 正确 Python、MONAI 导入、PyTorch 与测试依赖 | `requirements.txt:1-2`；`requirements-min.txt:1-5`；公开 hints | 依赖声明已读；conda 激活、安装版本、导入路径 unknown | `python -c 'import sys, torch, monai, parameterized; print(sys.executable, torch.__version__, monai.__file__)'`；预期导入待修改仓库和已准备解释器 |
| 对非测试源码做可微路径修复 | `ssim_loss.py:83-101`；`metric.py:69-71`；`regression.py:329-345` | 根因是静态证据；修复尚未实现 | 命令 A 检查复现和反向传播；预期输出 `gradient checks passed` |
| 保留前向数值与指标汇总 | 两份 SSIM 旧测试 | 文件已读，结果 unknown | `python -m unittest tests.test_ssim_loss tests.test_ssim_metric`；预期旧测试通过，但不能独自证明梯度正确 |
| 2D/3D 和多通道可微 | loss 文档 `:39,69-81` | 有接口依据，无运行证据 | 命令 A 的扩展用例覆盖 `C=1/3`、2D/3D；预期输入梯度存在且有限 |
| GPU、外部资产 | 旧测试 CUDA 条件分支；题面只用合成张量 | 实际 GPU/外部资产 unknown | 最小验证不需要；若实际有 CUDA，再运行现有损失模块以覆盖其 CUDA 分支 |

命令 A（仅建议；无需写入或修改测试文件）：

```bash
python - <<'PYCODE'
import torch
from monai.losses.ssim_loss import SSIMLoss

# 原题复现；相同图像允许梯度为零。
x = torch.ones([1, 1, 10, 10]) / 2
y = torch.ones([1, 1, 10, 10]) / 2
y.requires_grad_(True)
loss = SSIMLoss(spatial_dims=2)(x, y, x.max().unsqueeze(0))
assert loss.requires_grad
loss.backward()
assert y.grad is not None and torch.isfinite(y.grad).all()

# 分别验证两端输入，使用不相同的合成图像检查真实梯度连接。
for dims in (2, 3):
    for channels in (1, 3):
        for target in (0, 1):
            shape = (1, channels) + (10,) * dims
            x = torch.full(shape, 0.5, requires_grad=(target == 0))
            y = torch.full(shape, 0.25, requires_grad=(target == 1))
            z = (x, y)[target]
            loss = SSIMLoss(spatial_dims=dims)(x, y, torch.tensor([1.0]))
            assert loss.requires_grad and loss.ndim == 0
            loss.backward()
            assert z.grad is not None and torch.isfinite(z.grad).all()
            assert z.grad.abs().sum() > 0
print('gradient checks passed')
PYCODE
```

命令 A 是最低复现与有公开文档依据的扩展检查，不是已存在的官方测试。更改多批次实现时可另用非恒定张量检查每个样本梯度和均值约定；其精确定义仍需根据修改范围确定，不能把未运行的预期写成结果。

## 实际已读与未读

已读：角色卡全文；`user_prompt.txt:1-38`；`environment_brief.md:1-10`；`public_bundle.json:1`；`base/monai/losses/ssim_loss.py:1-101`；`base/monai/metrics/regression.py:1-90,241-396`；`base/monai/metrics/metric.py:1-180,290-336`；`base/tests/test_ssim_loss.py:1-53`；`base/tests/test_ssim_metric.py:1-72`；`base/requirements.txt:1-2`；`base/requirements-min.txt:1-5`；`base/docs/source/losses.rst:90-106`；`base/docs/source/metrics.rst:133-148`。

另外执行过公开目录的 `rg --files` 路径枚举（输出截断，未把枚举视为内容阅读），以及定向 `rg`：上述 SSIM 文件、文档和 requirements 文件；`base/setup.py`、`base/runtests.sh`、`base/CONTRIBUTING.md`、`base/monai/metrics/metric.py`、`base/monai/losses/__init__.py` 的关键词命中行。实际看到额外命中包括 `metric.py:278` 的缓冲 detach、`losses/__init__.py:35` 的导出、`CONTRIBUTING.md:116,209` 和 `runtests.sh` 的 unittest 相关行；未通读这些文件。对猜测路径 `base/tests/test_regression_metrics.py` 的 rg 返回该静态路径不存在，仅说明这次导出内没有该路径，不代表实际镜像缺失。

未读：`base_identity.json`、其他源文件/测试的正文、其他文档及完整测试工具配置；未追踪 `convert_to_dst_type` 实现；未跟随代码中的外部链接。未取得实际 actor 消息、初态、工具权限或任何运行结果。报告仅作静态需求和证据判断，不作成功率或训练资格判断。
