# 探针候选题单（元数据准备，未经环境验证）

日期：2026-09-09。主批 24 道：两来源各 12 道。另列 24 道备用候选，便于讨论扩展；备用不代表批准运行。

所有题目都是开发候选；未拉取镜像、未执行评分、未测试模型。SWE-Gym 引用现有四面 bundle；R2E 引用原始固定版本的元数据，并核对 Prime 公布的 56 条剔除清单。未下载 Prime 全量 parquet，因此不声称已核对全量行内容一致性。

沿用既有 hydra/bokeh/tornado/pyramid 预留，不把这些仓库移入开发。正式划分仍待定；跨来源同缺陷/派生关系尚需完整核对。

完整字段见 [candidate_manifest.jsonl](candidate_manifest.jsonl)。

## 第一批 24 道

| 来源/仓库 | 任务标识 | 选择理由 |
|---|---|---|
| SWE-Gym / Project-MONAI/MONAI | `Project-MONAI__MONAI-6975` | Dataset lazy 行为与 MONAI 依赖路径 |
| SWE-Gym / conan-io/conan | `conan-io__conan-13326` | 编译器兼容性计算；核对 conan 专用环境命令 |
| SWE-Gym / dask/dask | `dask__dask-7894` | 数组边界/裁剪与 dask 专用测试命令 |
| SWE-Gym / getmoto/moto | `getmoto__moto-6913` | AWS 服务模拟的错误响应内容 |
| SWE-Gym / getmoto/moto | `getmoto__moto-6470` | 同仓库另一服务的接口执行失败 |
| SWE-Gym / iterative/dvc | `iterative__dvc-5822` | 仓库版本定位与文件 API |
| SWE-Gym / modin-project/modin | `modin-project__modin-6937` | parquet 往返与较大回归测试列表 |
| SWE-Gym / pandas-dev/pandas | `pandas-dev__pandas-48106` | Categorical 扩容回归与多个 F2P |
| SWE-Gym / pydantic/pydantic | `pydantic__pydantic-8500` | 构造/序列化顺序 |
| SWE-Gym / pydantic/pydantic | `pydantic__pydantic-9214` | 同仓库不同版本的 schema 描述缺失 |
| SWE-Gym / python/mypy | `python__mypy-12741` | TypedDict 崩溃与 case 表达式选择 |
| SWE-Gym / python/mypy | `python__mypy-11236` | 类型推断及空 P2P 的诊断覆盖；不自动判无效 |
| R2E-Gym / aiohttp | `618335186f22834c0d8daabcf53ccf44d42488a2` | HTTP 压缩/分块边界 |
| R2E-Gym / coveragepy | `f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96` | 覆盖率报告与期望输出解析 |
| R2E-Gym / datalad | `6b6fa3898546793fa3517def09f85a74d51ec4bb` | SSH URL 解析及依赖环境 |
| R2E-Gym / scrapy | `a95a338eeada7275a5289cf036136610ebaf07eb` | partial 包装函数的反射行为 |
| R2E-Gym / numpy | `5e8301c2b36097dd8be5a12e0bb4369a1df4fabb` | einsum 优化与单维度输入 |
| R2E-Gym / numpy | `d89bc4bbf541affbcf87498ff4af86b9451480cd` | 直方图参数处理；与 einsum 覆盖不同子系统 |
| R2E-Gym / orange3 | `f5026689551be7f0a43ad5f0d129e5bcfff7999c` | 跨平台路径迁移；待核 Linux 镜像能否重现 |
| R2E-Gym / orange3 | `f237f9688e06ae46fe98d195b134d01f5b38b2e0` | GUI/widget 上下文；待核无显示设备运行条件 |
| R2E-Gym / pandas | `294cbc8d1faa15ba245391c5624752ecebd7f63b` | DataFrame.info 的列标识处理 |
| R2E-Gym / pandas | `7dd34ea7a121ce4282ce095b058c5c46568f07af` | RangeIndex 差集排序与负步长 |
| R2E-Gym / pillow | `f9d3ee0f4888f7618071c0a5315c916062e78854` | 图像 pad 的取整与定位 |
| R2E-Gym / pillow | `3a61c9e95e5c0a2da5736956e2dbafa57a9ede07` | RGBA 调色板重映射 |

## 备用 24 道（尚未逐题审查）

| 来源/仓库 | 任务标识 | 选择理由 |
|---|---|---|
| SWE-Gym / Project-MONAI/MONAI | `Project-MONAI__MONAI-2454` | 预留扩展：同仓库其他任务，按参考补丁规模分散选择；尚未逐题确认能力类型/运行成本 |
| SWE-Gym / conan-io/conan | `conan-io__conan-14296` | 预留扩展：同仓库其他任务，按参考补丁规模分散选择；尚未逐题确认能力类型/运行成本 |
| SWE-Gym / dask/dask | `dask__dask-7656` | 预留扩展：同仓库其他任务，按参考补丁规模分散选择；尚未逐题确认能力类型/运行成本 |
| SWE-Gym / getmoto/moto | `getmoto__moto-5899` | 预留扩展：同仓库其他任务，按参考补丁规模分散选择；尚未逐题确认能力类型/运行成本 |
| SWE-Gym / getmoto/moto | `getmoto__moto-5701` | 预留扩展：同仓库其他任务，按参考补丁规模分散选择；尚未逐题确认能力类型/运行成本 |
| SWE-Gym / iterative/dvc | `iterative__dvc-9395` | 预留扩展：同仓库其他任务，按参考补丁规模分散选择；尚未逐题确认能力类型/运行成本 |
| SWE-Gym / modin-project/modin | `modin-project__modin-6298` | 预留扩展：同仓库其他任务，按参考补丁规模分散选择；尚未逐题确认能力类型/运行成本 |
| SWE-Gym / pandas-dev/pandas | `pandas-dev__pandas-50319` | 预留扩展：同仓库其他任务，按参考补丁规模分散选择；尚未逐题确认能力类型/运行成本 |
| SWE-Gym / pydantic/pydantic | `pydantic__pydantic-8793` | 预留扩展：同仓库其他任务，按参考补丁规模分散选择；尚未逐题确认能力类型/运行成本 |
| SWE-Gym / pydantic/pydantic | `pydantic__pydantic-5706` | 预留扩展：同仓库其他任务，按参考补丁规模分散选择；尚未逐题确认能力类型/运行成本 |
| SWE-Gym / python/mypy | `python__mypy-16869` | 预留扩展：同仓库其他任务，按参考补丁规模分散选择；尚未逐题确认能力类型/运行成本 |
| SWE-Gym / python/mypy | `python__mypy-11352` | 预留扩展：同仓库其他任务，按参考补丁规模分散选择；尚未逐题确认能力类型/运行成本 |
| R2E-Gym / aiohttp | `22a12cc2e2ef289d9e96fd87dfc17272177e52ac` | 预留扩展：同仓库不同任务及题面长度；题面长度不代表难度或运行成本，尚未逐题质量审查 |
| R2E-Gym / coveragepy | `ea6906b092d9bb09285094eee94e322d2cb413a5` | 预留扩展：同仓库不同任务及题面长度；题面长度不代表难度或运行成本，尚未逐题质量审查 |
| R2E-Gym / datalad | `9ba5de094ea326e6fd5773f21c7de1776ec0fa69` | 预留扩展：同仓库不同任务及题面长度；题面长度不代表难度或运行成本，尚未逐题质量审查 |
| R2E-Gym / numpy | `18b7cd9df7a4d960550b18faa14d5473e7d5c3d9` | 预留扩展：同仓库不同任务及题面长度；题面长度不代表难度或运行成本，尚未逐题质量审查 |
| R2E-Gym / numpy | `2f4a965019722c3c56f43433bfa4a99c4c083138` | 预留扩展：同仓库不同任务及题面长度；题面长度不代表难度或运行成本，尚未逐题质量审查 |
| R2E-Gym / orange3 | `50f6a758f1c66b8f4a18806714e3c2f4cefcab3e` | 预留扩展：同仓库不同任务及题面长度；题面长度不代表难度或运行成本，尚未逐题质量审查 |
| R2E-Gym / orange3 | `22e98f8f4cccc25f0d0217f9f4251b66d49b4237` | 预留扩展：同仓库不同任务及题面长度；题面长度不代表难度或运行成本，尚未逐题质量审查 |
| R2E-Gym / pandas | `19c5eea5db0046276bfc0eef8a67febf090eeaaf` | 预留扩展：同仓库不同任务及题面长度；题面长度不代表难度或运行成本，尚未逐题质量审查 |
| R2E-Gym / pandas | `f656217a06b31e48474702036e0a5c49f664186c` | 预留扩展：同仓库不同任务及题面长度；题面长度不代表难度或运行成本，尚未逐题质量审查 |
| R2E-Gym / pillow | `a682ceaf47abbe28dc70c6bd4aab06f8f3f4ac90` | 预留扩展：同仓库不同任务及题面长度；题面长度不代表难度或运行成本，尚未逐题质量审查 |
| R2E-Gym / pillow | `2d01f7d02243d1b9cd3f2a3c3587d87703e00f96` | 预留扩展：同仓库不同任务及题面长度；题面长度不代表难度或运行成本，尚未逐题质量审查 |
| R2E-Gym / scrapy | `cfed9b6659c90e0799361911b1d72ed127edf471` | 预留扩展：同仓库不同任务及题面长度；题面长度不代表难度或运行成本，尚未逐题质量审查 |

## 已知缺口

- 题单为人工目的抽样，不能用其均值推断整个来源的成功率；多个任务来自同仓库，也不是独立仓库样本。
- R2E 的 commit_hash 表示修复 commit；实际初始 HEAD、评分脚本、参考 patch 与 expected_output_json 尚待在来源完整记录和镜像中核对。
- Prime drop 清单 56/56 能匹配本地 4578 行元数据，候选都不在 drop 清单；这不是我们的环境稳定性验证。
- SWE-Gym 原有 eval_cmd 需要恢复官方完整执行路径，不能直接视为本题单可运行命令。
- 不基于未知模型成功率、执行时间或论文分数筛题；备用候选中若有功能请求或不合首轮范围，先标注再在题单层处理，不新增生产训练拒绝规则。
