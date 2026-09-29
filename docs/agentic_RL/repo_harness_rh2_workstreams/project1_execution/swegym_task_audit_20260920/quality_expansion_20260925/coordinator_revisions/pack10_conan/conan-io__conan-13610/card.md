# conan-io__conan-13610

静态建议：**needs_review / static_review；仅 development_diagnostic**。base `0c1624d2dd3b0278c1cf6f66f8dcc7bd1aa9ec48`（Conan2.0）；题面要求规范日志却未定义裸`-v`，且末句未完成。旧源码/测试将裸`-v`视为verbose；隐藏测试改为status语义。该选择无法由公开材料唯一确定。

| 需求/旧行为 | 断言与结论 |
| --- | --- |
| 缺省、verbose/debug/trace/status/notice/warning/error矩阵 | 完整F2P函数均检查，不能只计算一处改断言 |
| 裸`-v`不显示verbose | 原noop第44行失败，gold通过；新语义缺公开明确依据 |
| 帮助与行为一致 | gold仍保留“-v or -vverbose”，两者实际已不等价；验收漏测 |
| 非法参数 | P2P要求命令报错，但文本assert恒真；quiet/其他CLI入口未覆盖 |

完整静态审查见 [初判](analysis_before_history.md) §§1–9：公开目标/版本已核；全部1F2P+1P2P、GenConanfile/TestClient与共享parser/输出调用者已读；合理const/参数规范化替代实现未执行；gold唯一映射改动及帮助回归已核；开发需本地Python/缓存，当前actor权限/消息/工作树/资产unknown；已核历史可信测试恢复和候选投影；重复/泄漏/控制面只作有限判断。

原RH2 ledger `baseline01/workers/w01-0/ledger.jsonl:15,16`：同一`pytest -n0 -rA .../test_output_level.py`收集2，noop 1失败1通过、RC1；gold 2通过、RC0；两次安装末命令RC0，无skip/xfail。原image tag/expected digest已有定位，actual image ID=null；此证据不是当前actor资格。

历史复核纠正“各级别完全未测”、用少P2P证明回归、用文字零命中证明无泄漏和“奖励不可学”等过强结论。历史后补核可选`conftest_user.py`导入及default_profiles影响，当前ignored-file交付链未证，保持check31 unknown，不新增排除。未读reviewer、reviewer意见未取得。

**唯一优先下一步：明确公开的缺省/bare-v/显式verbose和帮助契约。** CPU重跑现有两项不能解决该规格选择。前稿SHA `472675f1627fb7447d36f0255664daf0692d015848ff9a0bcfdf059a0e48ce05`未改；旧主张逐项处置见[差异](old_findings_delta.md)。没有项目执行或训练/正式评测批准。
