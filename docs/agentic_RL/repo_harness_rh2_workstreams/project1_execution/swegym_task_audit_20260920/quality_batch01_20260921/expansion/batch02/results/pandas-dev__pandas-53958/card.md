# pandas-dev__pandas-53958

base `1186ee0080a4`，目标是给类型注解提供一致的NaTType/NAType入口。建议 **needs_review/static_review**，仅开发诊断；独立复核已完成。主要问题是公开选择与验收范围，历史grader可以正常评分。

| 需求/行为 | 实际断言 | 判断 |
| --- | --- | --- |
| `_libs` 或 `api.typing` 统一导出 | 唯一F2P精确检查typing的18个名字 | 题面明确保留两方案，测试只接受typing；有合法替代误拒疑点。 |
| 新名字是真实类型，可用于注解 | 新断言只比dir字符串 | 不查对象身份、from-import或typing.__all__；误导出singleton的部分实现可能漏检，未做实际假补丁评分。 |
| 保留已有API | 10 P2P全部读完 | 主要查旧名称与顶层pd.__all__；弃用测试的列表为空，不夸大覆盖。 |

八方面已查题面/base、全部11测试/helper/fixture、替代与部分实现、gold/旧类型调用者、原运行环境、精确投影/恢复、用途与暴露。执行11项、冻结1+10参考、已读全部测试体分开登记；旧scalar测试另读但本次未运行。未覆盖全仓行为、实际actor/CC输入、镜像泄漏、模型难度；跨版本关系由独立复核补充。

Gold重导出既有真类并补__all__，不改原入口或单例。w06-2 ledger第11/12行及原日志证实noop0/gold1、F2P0/1→1/1、P2P10/10，原镜像、grader54322、deny_all下editable安装成功。安装段有xarray/dev版本元数据告警；不能称全环境依赖完全一致。Meson增量安装8–9秒不是actor冷构建或完整任务成本。

历史认为旧import示例与gold重合即严重泄漏，本轮不采纳：这是说明旧入口所需的信息；题面给方向、补丁小不等于答案污染或低训练价值。raw hints的typing赞同句没有进入当前公开包，不能补足actor实际已知选择。旧精确命名空间规则在公开base可见，也不是隐藏的新实现限制。

唯一优先下一步采用独立reviewer建议：固定grader比较gold与把NA/NaT单例误导出成NAType/NaTType的自然错误候选，名单及__all__齐全；同时直接核真实类型身份与原官方得分。若身份错误却获分，才能确认具体误收。主审原先优先_libs真类路线的分歧保留为可选后续；运行分数不能裁决命名空间规范，不并列成第二个必测。正式actor/54321的导入、build写权限和窄验证另待核；apply_user不证明开发会话。当前test_globs为空，只恢复 `pandas/tests/api/test_api.py`；source解可提交，附加排除空。已见gold/隐藏测试/历史，不给solver。

详情见封存 `analysis_before_history.md`（SHA256 `f2da3107461dcacece34bdbdddeb0e22d38a4a25cdcc42d1f2856dd7bacbcc8e`）及 `old_findings_delta.md`。

协调裁定：保留受限静态候选，但两个验收疑点未消除。优先对象身份因为它直接检验公开的“类型”目标，不依赖两命名空间哪一个应被接受；尚未构造或运行候选。本题base含48106修法，56849后期base含本题导出。独立复核及保留分歧见[review.md](review.md)。
