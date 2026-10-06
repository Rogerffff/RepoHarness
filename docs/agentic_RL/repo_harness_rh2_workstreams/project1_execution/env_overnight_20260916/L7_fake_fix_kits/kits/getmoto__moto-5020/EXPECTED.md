# getmoto__moto-5020 · 反例期望

- 仓库/版本：`getmoto/moto` @ `f8f6f6f1eeacd3fae37dd98982c6572cd9151fda`（version 3.1，python 3.12）
- 镜像：`xingyaoww/sweb.eval.x86_64.getmoto_s_moto-5020:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -n0 -rA`
- 判分面：F2P 1 条、P2P 29 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=0）

## 1. 断言来源

- 来源包：`L1_moto_1 / records/getmoto__moto-5020.json issues[1]`
- 断言编号：weak_assertion P3
- 原文摘要：构造『排序而不过滤』的 patch，跑本题 F2P+P2P，确认会被判 RESOLVED_FULL。（证据：test_patch `expected_route["Routes"][0]["DestinationCidrBlock"].should.equal(route)` 只看第一条、不断言总数；base 在 filter 未识别时返回全部路由）

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/getmoto__moto-5020.fake.diff` | 对 `route-search.exact-match` 不做过滤，只把命中的那条排到返回结果的最前面。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：唯一的 F2P `test_search_transit_gateway_routes_by_routesearch` 只断言 `Routes[0]` 的 `DestinationCidrBlock`，不断言 `len(Routes)`；把命中项排到首位就满足了。实际返回的仍然是全部路由（base 在 filter 未识别时的行为），29 条 P2P 用的是 type / state 两个已支持的 filter，不受影响。

## 4. 正确评分器应该抓到什么

`expected_route['Routes'].should.have.length_of(1)`（L1 proposed_action 原文）。

本题没有配 `diagnostic_test`（判别点要么需要重量级 fixture，要么就是下面的 blast 运行）。

## 5. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）
