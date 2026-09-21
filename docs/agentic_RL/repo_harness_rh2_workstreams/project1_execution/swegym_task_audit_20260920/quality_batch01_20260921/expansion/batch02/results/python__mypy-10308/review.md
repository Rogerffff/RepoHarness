# python__mypy-10308 — 独立复核

2026-09-21；独立 reviewer。三题独立初判均已保存并由协调者封存后，才开放主审、公开阅读与历史。本题 `reviewer_initial.md` SHA256 为 `1772dc877c85bd90bab21814d4c125319a268afe047734c9bde0430f76e269f7`，保持原字节。

**同意保留 needs_review / static_review / development_diagnostic，additional_exclusions=[]。** 原始测试材料确有缺件，既存 materials-v2 对照有可解释的目标分差；二者不能互相替代。没有证据支持“只接受 gold”“P2P 为零所以坏题”或“gold 已证明破坏增量依赖”。修改的是后续实验排序：固定 grader 的语义对照可以先做，正式 actor 验收另作启用条件。此修正也适用于本人初判中把二者绑定的建议，不回写封存稿。

## 引用范围与决定性复核

下列相对路径均以 `.` 为根。U=`runs/swegym_quality_batch02_20260921_v2/public/python__mypy-10308`，P 为同层 private 本题目录；M=`runs/env_recipe_repair_20260919/materials_v2`；G/N=`M/runs/python__mypy-10308-{gold,noop}`。主审文件均为本目录文件，本文只补写 review。

| 主张 | 独立复核与影响 |
| --- | --- |
| 公开目标与冻结 F2P 对应 | 题面要求 Vector/Matrix 协议组合不触发内部异常，不是保证所有普通类型诊断消失。基线 `1567e36165b00d532f232cb3d33d1faf04aaf63d` 的递归假定与 `constraints.py:437` 缺成员断言形成可读链条。F2P 用协变、简化 P1/P2 代替题面的默认不变、有上界和显式 self；是同机制回归，不是原样 CLI 复现。原例尚未直接执行，保持未知。 |
| 全部断言与三种范围 | 唯一 F2P 的四次赋值要求两次合法、P2→P1 缺 b、反向签名冲突；`[out]` 是九行，裸 `# E` 不是独立期待。新增 `testHashable` 确实执行，但不在冻结引用；带 `-skip` 的上下文名字没有成为第三个运行 item。当前 G/N 均实际两项，gold 两过、noop 两失败；冻结只对一项 F2P 计分，P2P=[]。阅读过的旧协议用例不冒充已执行保护。 |
| 既存修订究竟修改什么 | 原 test.patch SHA=`17e5df4826ca8f10bc17381a85a2f539c6001eee5a959dab39bd13c45423a42f`；修订 SHA=`e139b55e06645736212fa707a276588537373d6b01be3d16d45532155d6c90ed`。保留原 case 断言，补 object_hashable/typing-full 两 fixture，绑定 types-typing-extensions==3.7.3。原 grading=`sha256:868b96a8cb7abe13a644884c99dcb33fb85f893865968526b64ad4520f6fb221`；修订=`sha256:6fe0fad6693159c8f245f5627888efa35053e56843240729e971f9640fd331d4`。这些已在独立初判中从实际补丁/字节核过，不是沿用 decision 摘要。 |
| 真正生效入口 | `M/replay_with_install_recipe.py:42–60` 消费带 tasks 映射的 `M/materials.json`，校验原摘要、替换 grading.test_patch，并同步可信恢复/评测/卫生配置；`M/run_material_cases.py:27–54` 提供本题镜像及 wrapper 路由。G/N 下同名 `materials/materials.json` 是审计输出，不能给 --materials 代替映射输入。旧 runid 的 mat1、derived_recipe 的 materials-v1 标签不能推翻实际输入与 digest。原 prepared 公共任务未因这对运行自动重冻结。 |
| gold 与替代路线 | gold 在递归 assuming 前检查协议成员集合，仍先调用 `TypeState.record_protocol_subtype_check`。新增核读 `subtypes.py:523–529`、`typestate.py:151–158`：记录完整右协议成员在先，故“提前退出直接漏记成员依赖”的旧因果论证不成立；这不证明所有增量路径无回归。两阶段成员存在性检查等合理路线仍开放，没有实现/重放来证明其必然过或不过。 |
| 精确消息是否锁定 gold | 新核读 `checker.py:4563–4565`、`messages.py:1360–1405,1903–1934`：不兼容诊断路径重新查缺成员及冲突签名，不由 gold 的特定返回位置携带 b 消息。因此推翻“看到缺 b 文案就强制 gold”的旧结论。精确文字可约束其它实现，但尚无正确替代被拒的实证。 |
| 漏测与自然部分实现 | 原例和 F2P 的泛型形状不同，确实值得直接复现。主审的“只对协变变量启用检查”候选是静态假设，未实现/评分；不能因此直接宣布满分错误修复，也不把该人为分支设为准入必测。相关有效递归、成员缺失和方法兼容旧例用于定位边界，P2P 零不是零语义保护。 |

## 历史必须追到原件

本次独立核读 `runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/python__mypy-10308/{gold,empty}/offline/a1/`（Sg/Se）的完整 eval.sh/status_map、指定 test_output 段、gold patch 字节。不是只接受旧报告或主审 delta：

- Sg `test_output.txt:480–490,784–793,1073–1082` 显示两项被选中，目标 PASSED，Hashable 缺 `/testbed/test-data/unit/fixtures/object_hashable.pyi`，setup 和 teardown 均 ERROR。Se `:441–451,1190–1249` 同样选中 Hashable，目标因 constraints.py:437 的 AssertionError 失败。旧“Hashable 未被选中”应推翻；不能从旧 kcheck 的 selectors=1 推断真实命令。
- 两侧 eval.sh:14–15 用分号串联安装，最后 hash -r 后取 RC；Sg `:423–464`、Se `:384–425` 明确 editable build dependencies 安装失败、找不到 setuptools>=40.6.2，随后记录 install rc=0。该 rc 不能证明安装成功。stage1 的目标状态仍有原日志支持，但整套运行不是干净通过；也不能用这些非引用 ERROR 和 rc1 直接推出当前 RH2 reward=0。
- Sg/Se 日志 SHA256 分别 `53ac81d8db4d6e50a769a83afbacdeae63168ea3afe4f8f7ebda88c75555f0d2`、`7157b65d9d2ee9d454f60fca427617c63e3edacd25872f67455bc1d8567e8632`；Sg patch 与本题 gold 相同，SHA=`4d9843b52d969a2d73a05a4a00e6c5639a4d49706add7f11a6a2aa1321a3672e`。
- 仅抽 `runs/env_overnight_20260916/L1_mypy_1/dupidx.txt:4,66`、`kcheck_all.txt:32–35`。共享 subtypes.py 既不证明重复，也不证明非重复。原始 S2 raw `docs/agentic_RL/repo_harness_rh2_workstreams/s2/raw/swe_gym_lite_full_f70b1a29.jsonl:193` 的 id/base/version 对应本题；全文 hints 为 1898 字符，描述简化和成员顺序触发条件，是调试线索。公开材料在看 hints 前已足以调查，不把 hints 提升为隐含验收规范。

## 环境、交付与用途边界

修订后的 G/N `ledger.jsonl:1` 及其 `eval_logs/evallog_replay-er19-mat1-python__{e8bba825,4cc880f8}.eval.log` 才是当前引用对照：同派生镜像 `sha256:9acbdc2f996afc47c0f85a9b3f6cb67d62055a22bf1545d29f26e44ee1a8b51d`、材料与评分策略，reward=1/0，真实 editable 安装成功。初判已经独立读安装过程、模块来源、恢复及完整目标输出，不以末尾 RC 单独判断。Python3.9.19/pytest6.1.2/typing_extensions4.12.2 与 stub pin 是不同事实；install_wave1 Dockerfile 放入离线轮子，不意味着把列出的轮子全部实际安装。

该证据属于派生 grader/rh2grader/54322。candidate.apply_user=agent/54321 仅是补丁应用身份；formal actor 仍是公共镜像与 agent/54321。actor 的 shell、实际算法模块来源、可写空间及所需资产尚未验，不能填 actor ready。这里需要的开发活动是普通 Python 类型检查和窄单测；没有已知 GPU、外部服务或额外联网前提。

当前 `prepared_task_face.py:312–338` 为 test_globs=()，原版仅恢复 check-protocols.test；修订版按修订补丁再保护两 fixture 和 test-requirements.txt。源码 gold 仍可投影，不新增排除。`scoring.py` 的冻结引用与 vendor 选择器分开；`manager.py:1197–1249` 区分普通完整 pytest rc0/1 和全局故障。正常非引用失败不自动覆盖参考分数，具体全局故障另查。

静态公开包未见 gold 不等于真实 actor 无泄漏；未做镜像/缓存/mount/工具可见性验证。本包三个版本的共享源码和已有祖先修复是交叉暴露，不将其合并为同题；没有全池家族或训练划分审计。所有报告为特权审查材料，不交 solver；真实盲解、训练收益、重复稳定性与成本未知，不能把既有运行耗时当本次解题成本。

## 唯一优先下一实验与分歧

**固定已核的派生 grader 和明确 materials-v2 输入，对公开 Vector/Matrix 原例做一次 base/gold 窄语义对照。** 沿用既有冻结 0/1 对照作评分锚，记录实际解释器及加载的 subtypes/constraints 来源；判断 base 是否出现同类内部异常、gold 是否消除内部异常，同时保留正常不兼容诊断。不要把 gold 必须零诊断偷偷加入要求；不先扩大 P2P 或改 oracle。

这项诊断只需固定 grader 的身份、代码/输入和依赖可解释，不需要先完成正式 actor 的全部 shell、开发权限、工具与泄漏验收。后者是启用真实 solver/正式任务的必要独立条件，可以另轨完成，不能用于阻塞当前 oracle 问题的窄验证。若原例不能区分或暴露具体偏差，再按结果选替代/部分实现；不预先排满所有假想覆盖缺口。本轮没有执行上述实验，也未把候选写成 ready_for_probe。

## 暴露与阅读增量

封存前暴露见初判：环境记录只看键名；10308 获准 materials 条目含 decision 摘要和修订材料，已披露且独立核证。统一开门后读本题公开阅读的需求/路线/关键开发段、完整主审 analysis/delta/card、screening 的状态/问题/规则/修订/处置及相关证据；未宣称逐行读完所有重复引用。随后按 I2/history 本题 refs 读旧记录及上述精确原件。三题历史均在开门后读取；无其它题/包或 B1/B2 聚合阅读。本次工具仅静态阅读、JSON/哈希与写 review，未运行项目、测试、安装、Docker、联网、SSH 或模型；未改任何初稿、源码、测试、gold、reward 或主审文件。
