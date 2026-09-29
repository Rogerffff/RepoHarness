# 材料修订提案：pandas `4ec87eb9` 期望里的 ERROR 键来自 fixture 不可达

> **当前状态（2026-09-24 夜）**：用户批准先在本题做代表修复（方案 B）；已实施为 `r2e-mr-006`（私有 `r2e_tests/conftest.py`，原样摘出 base 提交 `baa10328` 的 `pandas/conftest.py` 里两个 fixture）与 `r2e-mr-007`（期望删 2 个 ERROR 键、加 13 个参数化键），真实 grader noop 0（233/237）×2、gold 1（237/237）×2，与试跑逐键相同；题面场景 `NA_float[Float32/Float64]` 成为活的 F2P 键。同族其余 6 题已按 T0-6 第二步照做（09-24 夜，`r2e-mr-008`…`019`，见 E21）。见 [decisions E16](../decisions.md)。以下是提案原文。

2026-09-24 / P3 sub-agent（B 线环境审查）。状态：**提案**（T0，未实施；本轮不改 `s2_r2e/`、expected、隐藏测试或镜像）。同族 7 题（pandas ×7）共用本分析，逐题数字不同；族级汇总见 [packages/p3/README.md](../packages/p3/README.md)。

## 问题

- 期望映射里有 **2/226** 个键是 `ERROR`。gold 日志逐键看原因：全部是测试 setup 阶段 `E fixture '<名>' not found`，没有缺可选依赖、需要网络或资源类原因。
- 缺的 fixture：`any_float_dtype`×1、`any_int_ea_dtype`×1（`pandas/conftest.py`）。
- 机制：隐藏测试在评分时被恢复到 `/testbed/r2e_tests/test_*.py`，pytest 只加载 rootdir（`/testbed`）到测试文件目录这条路径上的 `conftest.py`（`/testbed/conftest.py`、`/testbed/r2e_tests/conftest.py`，两者都不存在），`pandas/` 下的 conftest 不在这条路径上，所以这些 fixture 不可达。noop、gold 与参考 runner 都是 ERROR，R-f 对账逐键一致——这是来源（R2E-Gym 把测试文件移出原目录）的确定性伪影，不是 RH2 环境缺口。
- 被掩盖的测试：**F2P 性质**：`test_groupby_quantile_NA_float` 正是题面场景（Float 扩展 dtype、组内部分 NA → 中位数忽略 NA），`test_groupby_quantile_NA_int` 覆盖 Int 扩展 dtype（事后读私有测试代码得知，写复现脚本之后）。本题 F2P：`test_groupby_quantile_allNA_column[Float32]`、`[Float64]`（2 键：整列全 NA → 结果 NaN）。
- fixture 可达时的状态（同一派生镜像、base 代码、仓库原位置 `pandas/tests/groupby/test_quantile.py`）：这两个测试是修复提交新增的（base 版公开文件里没有，原位核对为 not_found）；整文件 222 passed / 2 skipped。

影响比其余 6 题大：题面给的例子（`[2.5, pd.NA]` → 2.5）没有任何正常运行的键在检查；现有 F2P 只覆盖“整列全 NA”。noop 下只有 allNA 两键不符，说明其余正常运行的键都不经过“部分 NA”这条出错路径；所以按现行 expected，只修好全 NA、没修好部分 NA 的候选理论上也能拿 1（推断，未构造这样的候选实测）。

## 证据

- gold / noop 日志：`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-gold-p_bb99de50.eval.log`、`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-p_e47e4f78.eval.log`（`grep "fixture '"` 的计数 = ERROR 键数）。
- fixture 定义位置与原位运行结果：`runs/r2e_env_repair_20260924/p3/fixture_check/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/result.txt`（脚本 `runs/r2e_env_repair_20260924/p3/fixture_check/{run.sh,inner.sh}`，一次性容器、无网络、root，只读公开工作区）。
- 口径：`rh2/src/repoharness2/envpack/scoring.py::expected_map_matches` 要求观测键集与期望键集相等且逐键相等。

## 影响

1. 这些键对任何候选恒为 ERROR，不提供回归信号（P2P 覆盖变弱）。
2. 脆弱性：候选若在 `/testbed` 根目录新增 `conftest.py`（或改 pytest 配置）让 pandas fixture 可达，这些键会从 ERROR 变成 PASSED → 与 expected 不符 → 正确解也得 0（假阴性）。`r2e_tests/` 下新建的 conftest 会被可信 setup 清掉，但根目录 conftest 不清（`rh2/src/repoharness2/adapters/slime/r2e_grading_scripts.py` 模块说明第 1 条与“不处理的边界”；sidecar 只记 `candidate_touched_conftest_or_fixture`，不改判定）。概率低，公开提示也没有提到。
3. 若以后“修好”这一点，expected 会变：这些键从 ERROR 变为 PASSED，且带 fixture 参数化的测试会展开成多个键（键集合变化，不只是状态变化）。

## 选项

- **A. 维持现状**：记录为已知的来源伪影，expected_v0 不动。代价：零；信号弱与脆弱性保留；与 R2E-Gym 公开结果可比。
- **B. 私有材料补 fixture（expected_v1）**：在隐藏测试目录旁加一份私有 `conftest.py`（如 `from pandas.conftest import *` 加上相关子目录 conftest 的 fixture），用 gold / noop 重新生成期望映射，隐藏测试树摘要随之变化 → 重建派生镜像、升级摄入面 pins、重跑对账。代价：7 题重新资格化；与 R2E-Gym 原始分数不再可比。收益：P2P 覆盖恢复、去掉 conftest 脆弱性；本题还会让题面场景的两个测试成为真正的 F2P。
- **C. 隐藏测试放回原目录**（如 `pandas/tests/.../test_r2e_1.py`）：conftest 自然可达；但入口脚本与 hygiene 的测试路径都要改，改动面比 B 大，同样要重算 expected。
- （不推荐）从 expected 删除 ERROR 键：RH2 口径要求键集相等，删除后这些 ERROR 观测会成为 `unexpected`，必须同时改评分口径。

## 推荐

族内其余 6 题本轮 **A**。本题建议在进入正式题池前做 **B**（或至少在题目筛查环节标注“F2P 未覆盖题面场景”并降级），因为被掩盖的正是题面场景的测试；这属于题目质量 / 判分强度问题，不影响本轮的环境资格结论。

## 长期代价与以后还能改什么

A 保留来源定义，随时可以升级到 B（B 只增加私有材料，可版本化为 `expected_v1` 并保留 v0 对照行）；B / C 一旦用于训练或评测，分数与 v0 不可混比，需在题包里带版本号。无论选哪项，都不改 gold。
