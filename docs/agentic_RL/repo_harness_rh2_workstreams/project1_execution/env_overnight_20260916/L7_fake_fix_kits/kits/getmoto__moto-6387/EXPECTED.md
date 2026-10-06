# getmoto__moto-6387 · 反例期望

- 仓库/版本：`getmoto/moto` @ `7b4cd492ffa6768dfbd733b3ca5f55548d308d00`（version 4.1，python 3.12）
- 镜像：`xingyaoww/sweb.eval.x86_64.getmoto_s_moto-6387:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -n0 -rA`
- 判分面：F2P 1 条、P2P 3 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=2）

## 1. 断言来源

- 来源包：`L1_moto_3 / records/getmoto__moto-6387.json issues[0]`
- 断言编号：grading_scope_too_narrow P2
- 原文摘要：构造一个把 `_get_xml_body` 改成 `force_list=True`（对所有元素强制列表）的补丁，跑本题 F2P+P2P 确认满分，再跑 test_cloudfront_distributions.py 确认大面积失败——用来量化判分面窄的代价。（证据：`_get_xml_body` 三处调用点 vs 仅跑 invalidation 一个测试文件）

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/getmoto__moto-6387.fake.diff` | `_get_xml_body` 的 `force_list` 从 gold 的单键 `"Path"` 扩成 8 个键的元组。 | **full_score** |
| `fake_forcelist_true` | `patches/getmoto__moto-6387.fake_forcelist_true.diff` | L1 next_experiment 的字面版本：`force_list=True`。 | **not_full** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：F2P/P2P 共 4 条全在 `tests/test_cloudfront/test_cloudfront_invalidation.py`，只用到 `Path`；扩大 force_list 不影响它们，却改变了 `create_distribution` / `update_distribution` / `list_tags_for_resource` 的解析结果。

**`fake_forcelist_true`（预期 not_full）**：静态判读：`force_list=True` 会把 `InvalidationBatch` 自身也变成 list，`create_invalidation` 里 `self._get_xml_body()["InvalidationBatch"].get("Paths")` 直接 AttributeError，连 F2P 都过不了。保留它是为了在真机上证实/证伪 L1 的表述，并说明『断言里的假修复写法本身也需要验证』。

## 4. 正确评分器应该抓到什么

`tests/test_cloudfront/test_cloudfront_distributions.py` 与 `test_cloudfront_dist_tags.py` —— 两者都不在本题判分集合。

本题没有配 `diagnostic_test`（判别点要么需要重量级 fixture，要么就是下面的 blast 运行）。

## 5. 附加（blast）运行

只在环境变量 `RUN_BLAST=1` 时执行，不进 reward，只作为『判分面 vs 改动面』的证据：

| 运行名 | pytest 参数 | 用途 |
| --- | --- | --- |
| `blast_cloudfront` | `tests/test_cloudfront/test_cloudfront_distributions.py tests/test_cloudfront/test_cloudfront_dist_tags.py` | 量化判分面窄的代价 |

## 6. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `fake_forcelist_true` → **不满分（至少一条红）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）
