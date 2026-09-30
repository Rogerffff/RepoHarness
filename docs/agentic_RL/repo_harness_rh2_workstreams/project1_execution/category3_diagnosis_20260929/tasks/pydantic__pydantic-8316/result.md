# pydantic__pydantic-8316：第3类诊断状态（未完成）

2026-09-30 / Claude（云端，第3类负责人）。原分类：第3类“已有具体疑点，缺辨别实验”（alias 与数字边界）。第二批波次 2。

**状态：作者诊断未完成，还没有结论。** 按三种结论，本题目前属于“仍有具体问题”：缺全部运行证据，下一步命令见下文。

09-30 云端额度不足、第二批暂停时，作者子代理已完成两件事：构造候选、起草修订测试。它的私有矩阵与正式评分输出只在被 git 忽略的 `runs/` 中，容器重置后丢失，**没有归档**。本目录因此没有 `evidence/`，也没有可核对的分数。

## 已入库的材料

材料都在 `rh2/experiments/category3_cloud_20260929/pydantic8316/`。

| 文件 | 内容 |
| --- | --- |
| `make_candidates.py` 与 13 个候选补丁 | 每个候选只替换 base `pydantic/alias_generators.py` 中 `to_snake` 的函数体 |
| `behavior.py`、`semantic_spec*.json` | 私有行为矩阵脚本与规格 |
| `original_test.patch` | 原 test_patch，sha256 `9d47a611…fc18` |
| `revised_test_v1.patch`、`materials_revised_v1.json` | 修订草案 v1（`f98096e9…d1e3`），由 `_edit_revised_test.py` 生成 |
| `run_formal.sh`、`run_all.sh`、`run_extra.sh`、`summarize_formal.py` | 正式评分驱动与汇总 |

原测试只在 `test_camel2snake` 的参数表里加了一条：`('CAMELToSnake', 'camel_to_snake')`。

候选分组（取自 `make_candidates.py` 的说明）：

| 类别 | 候选 |
| --- | --- |
| 合理的替代实现，用来查误拒 | `keep_digit`、`lookaround`、`scan`、`upstream_main`、`normalize` |
| 错误候选，用来查漏判 | `lead_only`（只拆开头的缩写）、`first_only`（只替换第一处）、`acr3`（只认 3 个及以上大写字母）、`literal`（只认一张缩写表）、`lower_or_start`、`no_lower_upper`、`acr_max4`、`only_if_no_us` |

修订草案 v1 在同一个 F2P 测试体里追加非示例实例，测试 ID 不变：`HTTPResponse`、`getHTTPResponseCode`、`userIDToken`、`XMLToJSONConverter`。

## 作者起草时的判断（未经核对）

`materials_revised_v1.json` 的 `reason` 字段记录了作者当时的判断：
- 原 F2P 只断言了一个位于开头、3 个及以上字母的缩写，输入形态与题面示例相同；
- `lead_only`、`first_only`、`acr3` 这类部分修复会得 1（S1／T2，v1 §4 第 2、4 步）；
- v1 加入非开头、两字母和重复出现的缩写实例；
- 大写字母与数字之间是否断开，两种读法都有依据，所以 v1 不做断言。

这些判断依据的运行结果已丢失。**在重跑之前，它们只是待验证的假设**，不能作为结论引用。

## 下一步

1. 按[作者须知](../../batch2_author_brief.md) §4 用 `rebuild_wheel_layer.py --kind build` 重建 pydantic_v1 等效派生镜像。`run_formal.sh` 从 `runs/…/pydantic8316/derived_image.json` 读派生 ID。
2. 重做 `prepare` 与 `export-gold`。
3. 用 `behavior.py` 跑私有矩阵，确认 base 与 gold 在题面示例、非开头缩写、两字母缩写和数字边界上的行为。
4. 跑原材料与修订 v1 的正式评分：先 `run_all.sh`（noop、gold 与第一组 8 个候选），再 `run_extra.sh`（第二组中的 `normalize`、`lower_or_start`、`no_lower_upper`）。`acr_max4`、`only_if_no_us` 只在私有矩阵规格 `semantic_spec_group2.json` 中，需要时另跑正式评分。
5. 用 `archive_evidence.py` 归档，写出完整结论页，再请独立复核。

## 未做

- 公开要求整理、私有矩阵、正式评分、判定、修法验收：结果都未归档，等于未做。
- 独立复核、真实 actor 开发条件、模型求解：未做。
