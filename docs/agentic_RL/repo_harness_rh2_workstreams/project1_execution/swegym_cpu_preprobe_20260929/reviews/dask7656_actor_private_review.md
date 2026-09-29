# Dask 7656 修订 actor／私有行为独立复核

日期：2026-09-29。审查者：Pydantic 题负责人。仅只读本机回传原件；未执行远端、容器或历史项目。本次不重复脚本静态初审，也不提前认定尚待复核的 900 秒准备预算正式评分。

**结论：本次 actor 配方修订及四组私有行为证据可采纳，没有发现阻断后续正式校准的问题。两个退化候选均有具体语义缺陷；是否获得正式误奖仍须逐份核对正式账本、测试输出与实际候选导出。**

## 修订 actor 的实际结果

证据根目录：`runs/swegym_cpu_preprobe_20260929/remote/results/dask__dask-7656/calibration_v1/`。

- `actor_build/cpu29_actor_dask_dask_7656_v1/image.json` 与 Dockerfile：固定上游 digest `27d11a070a6af9472f390a39258cfafd3ddcd0a768963a4bc903c797c9d7b601`；基础镜像 ID `3e57a70d57e3691a4f53908d694b7e4a78055ef05a176ef63a5853bd56514d72`，原层保留；唯一 wheel 是 pandas 1.3.5，SHA256 `2c21778a688d3712d35710501f8001cdbf96eb70a7c587a3d5613573299fdca6`。另加 conda 激活钩子 `SETUPTOOLS_USE_DISTUTILS=stdlib`。没有将参考测试或候选补丁写入 actor 层。
- 实际 actor 镜像 ID `607799d7926bec7ab9fed4d09d0c51a691efd558b2d2290d8ecfd96e3cbe4c0b`，base `07d5ad0ab1bc8903554b37453f02cc8024460f2a`。初始和结束 Git 工作区均干净。UID/GID 54321，源码从 `/testbed/dask/__init__.py` 导入；Python 3.9.19 来自 testbed 前缀，pytest 8.3.2。
- `captures/compat_environment.out` 确认 pandas 1.3.5、stdlib distutils 路径和激活变量实际生效；`activation_check.json`、`prelaunch.json` 都无 violation。这验证正式 BASH_ENV 路径下的钩子，而非仅 root 手工 export。
- 五条公开命令完整运行：身份 0；原例 1，准确触发 `Entry.primary_key` 缺失的 AttributeError；默认／嵌套检查 1，同一缺失属性（base 在第一条默认实例已失败，不能声称执行到第二条嵌套实例）；三个现有窄测试全部通过，49 deselected；兼容环境 0。每条完整 capture 均低于 200000 字节，没有截断或超时证据。
- 独立逐 ID 核对 `harness/trajectory.jsonl`：5 个 Bash 调用对应 5 个同 ID 返回（`9012654ec00af0a6`、`416a94551faf44b6`、`26b678c6803f2c9c`、`d9112302a20b67ae`、`e869de8cf86cb5d6`，共同前缀 `toolu_`）；6 个 stub 请求，成功终止、日志完整、无 permission denial。
- 实際消息仍是 “Devcheck run: execute exactly the tool calls you are given, then stop.”，不能据此声称真实模型已收到正式题面。旧汇总字段 `interpreter_in_tool_result=false`、`bashenv_denied_for_agent=false` 不覆盖实际身份／激活探针：本次公开命令未输出该旧检查要求的标记；只读激活边界在 prelaunch 中实际为 denied-write。
- 配额实测为 2 CPU、4 GiB、swap 0、512 pids；没有 CPU 利用率或整机容量结论。清理 `container_rm=0`、stub rc 0，网络／relay failure 为空，labeled 与 force 后残留均为空；结束时 agent 进程 0。

环境边界：构建 `pip check` 仍报 distributed 与旧 Dask、fastparquet／xarray 与 pandas，以及 chest 的兼容问题。本轮公开及私有命令均完成相关导入与执行；这些报告不构成本轮已运行窄路径的失败证据，也不能将环境扩大称为全库依赖已一致。

## 私有行为：逐个非零归因

`private_behavior_spec.json` 固定同一 actor image；四个独立 root 容器均从同一 base 开始，各候选 git apply rc 0。私有 helper 不走 actor 激活，所以各命令显式 export stdlib distutils。此处证明行为，不能替代 actor 或正式 grader 身份验证。

| 变体 | 题面原例 | 默认／嵌套实例 | 三个现有窄测试 | 解释 |
| --- | --- | --- | --- | --- |
| base | 缺失 primary_key | 第一条即同异常 | 3 pass | 原 bug 确实复现 |
| gold | `Hack works` | `ENTRY_DEFAULT_NESTED_PASS` | 3 pass | 修复原例并保留默认、类型、嵌套求值 |
| opaque_dataclass | `Hack works` | 第二条嵌套 Delayed 未求值，比较时 TypeError | 1 fail / 2 pass | 直接返回原 dataclass 绕开遍历，真实回归；现有 test_delayed_with_dataclass 同样失败 |
| wrong_result_type | `Hack works` | 第一条 `isinstance(entry, Entry)` AssertionError | 3 pass | 重建为 SimpleNamespace，类型丢失；现有三个窄测试未抓住 |

已读失败完整 traceback，不把任意非零当作预期语义失败。`wrong_result_type` 首条断言失败后未到嵌套检查，不能声称它已验证第二条。四组 cleanup 均 `rm_rc=0/query_rc=0/remaining=[]`，没有准备失败、收集失败或超时。

补丁只在私有 spec 的 `/in` 文件映射及独立容器中使用；actor 请求及五条命令没有携带它们。补丁本身解释与输出相符。但私有 helper 的 summary 没有独立记录容器内补丁内容哈希，正式结论仍应以 formal frozen_patch 的实际源码导出绑定候选，不能只拿本地补丁名字推断。

## 剩余项及适用边界

- 原 300 秒控制面准备超时的 noop 不产生有效 reward；其清理应按该账本记载。新 `grading_setup900_v1/` 是单独预算版本，不能与原运行混称同条件。
- 等待正式 noop／gold／两个退化候选完成，再核安装、完整测试分段、逐参考 ID、runner 清单变化、候选导出、资源观察、manager_close 和冻结 parser 重放；目前不作最终用途准入判断。
- 不将新增私有行为后检表述为正式参考已经修好，不因本次窄路径通过而宣称真实模型输入或全库依赖已验证。

最小原件指纹（SHA256）：

- actor `attempt.json`：`b1740c893d09a0f7836c742fe3c6a2ad1fa358825f40afebf3b988c8904b12f8`
- actor `harness/trajectory.jsonl`：`dd1d33ad01edc13765075442ff44d555465e2dc66d8c7c18d5c8f08a9c4e64c2`
- `private_behavior_spec.json`：`916f664847bec2bc94d18697d60e355cdac6f2d68473d5876b482158ca3f42ec`，与 summary 内 spec_sha256 一致。
- `private_behavior/summary.json`：`4c496fab4374f328b68543912594adee72c4574350029c8f341cca9b380fc09d`
