# Dask7656：actor 与私有行为部分结果

2026-09-29。**公开开发命令已在依赖修订后的真实 actor 工具通道完成；gold 私有对照修复原例并保留类型与嵌套计算，两类错误候选均已被公开行为控制检出。正式noop/gold已在900秒CPU准备预算下完成，错误候选正式结果尚待回传，当前不是题目最终通过。**

证据根目录：`runs/swegym_cpu_preprobe_20260929/remote/results/dask__dask-7656/calibration_v1/`。原条件 actor 的先前结果保留于本目录 `actor_original_result.md`；未重复执行。本稿是题主读回新证据，仍待独立结果复核，不冒充独立验收。

## 实际修订与 actor 结果

固定 base registry digest `27d11a07…`，其实际 config ID `3e57a70d…` 与历史相同。actor 派生镜像 `607799d7…` 安装公开依赖 pandas1.3.5，并通过 conda activate.d 设置 `SETUPTOOLS_USE_DISTUTILS=stdlib`；构建记录证明底层镜像层保留、wheel SHA匹配且 `/testbed` 工作树未改。grader 为不同的 COPY-only 镜像 `e4a2cbb1…`，pandas安装与环境变量由候选安装配方落实，不把actor预安装等同grader已安装。

修订 actor 的实际工具输出为 UID54321、Python3.9.19、CC2.1.205，HEAD `07d5ad0ab1bc8903554b37453f02cc8024460f2a`，Dask从`/testbed/dask/__init__.py`导入。新增环境命令明确看到 pandas1.3.5、pytest8.3.2、stdlib distutils路径及环境变量，说明激活钩子确实到达actor shell。

5条 Bash 调用和5份结果完整对应，6个桩消息，harness log完整、无截断。原例及增强命令均因 `dask/delayed.py:112` 访问缺失 `primary_key` 抛 AttributeError；不是任意非零。旧公开选择得到3 passed、49 deselected。增强命令在第一个默认对象就失败，因此修订base的嵌套分支仍未运行，不能写成“base嵌套已验证”。prelaunch/activation通过，工作树最终清净，容器／网络／relay／stub清理成功且无残留。起止58秒，solve19.69秒；桩的token/cost不作模型开销。

完整环境的pip_check为1：distributed要求较新Dask、fastparquet/xarray要求较新pandas、chest平台支持等冲突仍在。上述目标命令和三个公开测试可运行，不等于整个镜像所有功能依赖一致。旧汇总中的解释器和BASH_ENV标识false沿用先前解释：实际身份/activation有证据，命令未产生旧探针期待的文本。

## 私有行为矩阵与精确失败点

私有对照使用同一actor派生镜像，helper以root执行，每条命令显式export stdlib；它不是actor权限证明。四个变体均有完整三命令输出，补丁准备成功，rm/query均0且remaining为空。

| 变体 | 原题简单例子 | 默认值／类型／嵌套控制 | 3项旧公开测试 |
| --- | --- | --- | --- |
| base | AttributeError primary_key | 第一个默认对象建图即同样失败，未到嵌套 | 3通过 |
| gold | `Hack works` | `ENTRY_DEFAULT_NESTED_PASS`：两个对象都完成，类型与值均保持 | 3通过 |
| opaque_dataclass | `Hack works` | 默认对象成功；第二个嵌套对象仍含Delayed，`Truth of Delayed objects is not supported` | dataclass项失败，另2通过 |
| wrong_result_type | `Hack works` | 第一个默认对象在 `isinstance(entry, Entry)` 失败；未到嵌套分支 | 3通过 |

这说明题面原例单独不足以区分正确与退化实现，三个旧测也漏掉“重建为错误类型”的候选。增强控制能区分两个错误候选，但**此时还没有本批错误候选的正式reward来断定正式参考是否同样误奖**。gold通过这组窄控制也不等于所有dataclass语义均已覆盖。

## 正式评分：noop/gold完成，错误候选待回传

首个 `calibration_v1/noop/ledger.jsonl` 是基础设施失败：`failure_category=infra_failure`、`infra_failure_detail=grading_control_surface_protect_timeout_after_300s`、reward=null。trusted setup耗时301.302秒，install/test/observations/reference均为空，不能把它记成noop的行为失败或0分。记录的mem_peak_mb=1676.48，container_oom_killed=false、oom_kill_events=0，清理removed=true；因此不是已知OOM或候选安装失败。

独立目录 `grading_setup900_v1/` 沿用相同image/code/recipe，仅把CPU准备上限env_reset改为900秒（本批统一CPU准备上限），test、整体预算、权限、生产实现不变。旧300秒证据保留，不与新条件合并。已完成原件如下：

| 正式候选 | reward与参考 | 原测试输出 | 完整性 |
| --- | --- | --- | --- |
| noop | 0；F2P0/1、P2P48项无失败 | dataclass目标1 failed，49 passed、2 xfailed | 安装与test完整、参考缺席0、清理成功 |
| gold | 1；F2P1/1、P2P48项无失败 | 50 passed、2 xfailed | 安装与test完整、参考缺席0、清理成功 |

两次apply_ok均true，源码均从`/testbed/dask/__init__.py`导入，runner前后相同，install_failed_commands为空、安装rc0。noop的非零精确来自正式dataclass目标缺失属性断言；gold正式修复该目标。测试执行数量与参考分母不同，不混为52个正式参考。trusted setup分别347.769秒和355.131秒，均超过旧300上限，支持准备预算调整的具体依据。两份resource_facts为空，不能从它们补写新的OOM统计；成功收口与首轮明确无OOM事实分开。

此快照的opaque仍在途，wrong_result_type尚无完整正式结果。不从运行中status推断完成，也不重跑actor/private。

## 当前用途和全部剩余项

当前可作为CPU开发通道、公开依赖配方和行为对照的部分证据；尚不授予正式比较／训练或GPU-ready资格。接续读取setup900的opaque/wrong_type完整安装、测试、逐参考、runner与清理，并与已核noop/gold对照，判断错误类型候选是否被正式参考遗漏；异常需继续归因。随后由独立审查者核题级结果并按既定筛选规则收束用途。

实际CC用户消息仍是Devcheck控制文本，未证明正式题面/public_hints已在解题输入中交付；没有自主模型推理。原条件和修订条件、actor与root私有行为、作者读回与独立验收保持分开；完整环境pip_check冲突、默认／嵌套短路范围及原评分超时均不隐藏。
