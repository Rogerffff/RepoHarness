# pack12 Pydantic 静态审查

8793保留为有条件静态开发候选；9066归quality_first。两题ready_for_probe=false，26/27均unknown：核心修复有静态及历史正证据，完整性未证；9066另有具体未运行参考回归风险。当前actor和训练/正式评测资格未验。

| 题目 | 原件支持的判断 | 唯一优先下一步 |
| --- | --- | --- |
| 8793 | 单FieldInfo合并把外层Ellipsis保留为实际default，导致Annotated字段不必填；gold在该分支归一化。三F2P对应原例及公开动静模型等价。 | 实际actor公开create_model原例，联合检查required、is_required及缺值ValidationError，保存初态/导入来源。 |
| 9066 | IP默认对象不能写入JSON Schema；gold用实际类型的TypeAdapter序列化。普通dataclass无serializer时，非None config触发PydanticUserError，gold及上层都不捕获该父类异常。 | 私有base/gold的标准dataclass实例默认值model_json_schema对照，带题面IP控制，保存schema/warning/异常code。 |

8793新增仅检查schema和is_required，未针对runtime缺值、Annotated真实默认值/工厂与复用组合。旧“只改is_required必导致model_construct或默认schema错误”推论不成立：两条调用链都受is_required门控；未运行替代方案，不能宣称其必错、完整正确或必过367项。_attributes_set保留原Ellipsis本身也不证明gold错误。内层具体default与外层...的优先级存在文档/旧测试疑义，保留边界，不为此增设CPU。review补核test_config.py:788属于test_partial_creation_with_defer_build的create_partial局部helper，提供default=None/原模型稳定性旧约束，不是生产with_config调用，且不在历史单文件selector内。

9066的原问题是默认值schema编码，不是IP输入解析；IPv6属于IPvAnyAddress公开支持。旧“所有默认值都建TypeAdapter”忽略serializer短路；旧“warning普遍升级异常”忽略default_schema捕获PydanticSerializationError。旧不可序列化lambda、BaseModel默认值等P2P已有行为护栏，不能称新两侧完全零覆盖，但没有动态分支插桩证明。具体dataclass异常是另一种PydanticUserError；catch其子类PydanticSchemaGenerationError不能捕获父类本身。该路径静态明确，base是否可用及gold是否实际崩溃仍待对照。按IP类型实现合法局部修复不等于写死测试值，不能为了逼近gold通用方案新增非IP规格。

| 历史原件 | no-op | gold | 版本/身份 |
| --- | --- | --- | --- |
| 8793，382 collected | 3failed/377passed，RC1 | 380passed，RC0 | base832225b90672、core2.16.2；derived ID 3ed9b0685fbbd4dbbefcee77ac6c80f3f58b41d8e0722f54bc58c98267c5b0ed |
| 9066，384 collected | 2failed/380passed，RC1 | 382passed，RC0 | basea3b7214a1d6a、core2.16.3；derived ID b12b48fbea360dc19ca0537495ef0b5d3e9a33f62712e561f570f5a63b84b5a1 |

两题都用pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_json_schema.py，历史Python3.8/pytest7.4.4，安装RC均0；各另有1skip/1xfail，均不在expected。367/369 expected逐ID完整，P2P语义只风险抽查。parser374/376与pytest382/384不同，非expected解析未全面审计。历史pydantic-install-v1只改离线安装入口，测试补丁和selector未改；协调者核过before/after配方、image/build身份。原status已有pdm.lock/pyproject准备差异，git show不是工作树diff。原例Python3.8需用typing_extensions.Annotated，这与目标缺陷不同。

两题check4按完整“可读/可改/可提交范围”问题收为unknown，保留预定NON-TEST和历史仅源码投影的正证据。没有据角色数量裁定，也不回扫其他已封存包的局部pass；任何历史pass必须携带其scope。旧R4、轨迹、6126等未授权原件不追读，旧零泄露或ready结论不继承。本包9066基线已含8793字段修复与三测试，协调者直接核到这一版本关系，不能由此推出正式split重复或实际泄露。

两名公开角色、一名主审、一名复核均显式请求Astra/high/fork_turns=none；六份初稿封存后才释放历史/交叉，后端/OS隔离未认证。协调者读全部新patch、决定性源码、角色技术正文、两份完整review及选定record/旧记录字段，不冒认全部P2P正文或core Rust实读。四份main原card/record归档。见[后续](pack12_followups.md)、[修订来源](coordinator_revisions/pack12_pydantic/revision_log.json)、[阅读边界](reserve20_coordinator_read_notes.md)。未新执行项目或派发任务二。
